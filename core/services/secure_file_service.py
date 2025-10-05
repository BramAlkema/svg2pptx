#!/usr/bin/env python3
"""
Secure File Operations Service

Provides secure temporary file and directory operations with automatic cleanup,
permission controls, and path traversal protection.

This service replaces insecure patterns like tempfile.mkstemp and tempfile.mkdtemp
that are vulnerable to race conditions and security exploits.
"""

import os
import tempfile
import threading
import atexit
from typing import Set, List, Callable, Optional, ContextManager
from dataclasses import dataclass, field
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class SecureFileOperationError(Exception):
    """Exception raised for secure file operation errors."""
    pass


class PathTraversalError(SecureFileOperationError):
    """Exception raised for path traversal attempts."""
    pass


@dataclass
class SecureTempFile:
    """Secure temporary file wrapper with automatic cleanup."""
    path: str
    file_descriptor: Optional[int] = None
    cleanup_registered: bool = False

    def __post_init__(self):
        if self.path and not self.cleanup_registered:
            # Register for cleanup with the global service
            _global_cleanup_registry.register_temp_file(self.path)
            self.cleanup_registered = True

    def cleanup(self) -> bool:
        """Clean up the temporary file."""
        try:
            if self.file_descriptor is not None:
                try:
                    os.close(self.file_descriptor)
                except OSError:
                    pass  # Already closed
                self.file_descriptor = None

            if os.path.exists(self.path):
                os.unlink(self.path)
                logger.debug(f"Cleaned up secure temp file: {self.path}")
                return True
        except OSError as e:
            logger.warning(f"Failed to cleanup temp file {self.path}: {e}")
        return False


@dataclass
class SecureTempDir:
    """Secure temporary directory wrapper with automatic cleanup."""
    path: str
    cleanup_registered: bool = False

    def __post_init__(self):
        if self.path and not self.cleanup_registered:
            # Register for cleanup with the global service
            _global_cleanup_registry.register_temp_dir(self.path)
            self.cleanup_registered = True

    def cleanup(self) -> bool:
        """Clean up the temporary directory and all contents."""
        try:
            import shutil
            if os.path.exists(self.path):
                shutil.rmtree(self.path, ignore_errors=True)
                logger.debug(f"Cleaned up secure temp dir: {self.path}")
                return True
        except OSError as e:
            logger.warning(f"Failed to cleanup temp dir {self.path}: {e}")
        return False


class GlobalCleanupRegistry:
    """Global registry for temporary file cleanup on process exit."""

    def __init__(self):
        self._temp_files: Set[str] = set()
        self._temp_dirs: Set[str] = set()
        self._lock = threading.Lock()
        self._cleanup_handlers: List[Callable] = []
        self._registered_atexit = False

    def register_temp_file(self, path: str):
        """Register a temporary file for cleanup."""
        with self._lock:
            self._temp_files.add(path)
            self._ensure_atexit_registered()

    def register_temp_dir(self, path: str):
        """Register a temporary directory for cleanup."""
        with self._lock:
            self._temp_dirs.add(path)
            self._ensure_atexit_registered()

    def unregister_temp_file(self, path: str):
        """Unregister a temporary file (already cleaned up)."""
        with self._lock:
            self._temp_files.discard(path)

    def unregister_temp_dir(self, path: str):
        """Unregister a temporary directory (already cleaned up)."""
        with self._lock:
            self._temp_dirs.discard(path)

    def add_cleanup_handler(self, handler: Callable):
        """Add a cleanup handler to be called on exit."""
        with self._lock:
            self._cleanup_handlers.append(handler)
            self._ensure_atexit_registered()

    def cleanup_all(self):
        """Clean up all registered temporary files and directories."""
        import shutil

        with self._lock:
            # Run custom cleanup handlers first
            for handler in self._cleanup_handlers:
                try:
                    handler()
                except Exception as e:
                    logger.warning(f"Cleanup handler failed: {e}")

            # Clean up temporary files
            for temp_file in list(self._temp_files):
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                        logger.debug(f"Cleaned up temp file: {temp_file}")
                except OSError as e:
                    logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")

            # Clean up temporary directories
            for temp_dir in list(self._temp_dirs):
                try:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        logger.debug(f"Cleaned up temp dir: {temp_dir}")
                except OSError as e:
                    logger.warning(f"Failed to cleanup temp dir {temp_dir}: {e}")

            # Clear the registries
            self._temp_files.clear()
            self._temp_dirs.clear()
            self._cleanup_handlers.clear()

    def _ensure_atexit_registered(self):
        """Ensure atexit cleanup is registered (thread-safe)."""
        if not self._registered_atexit:
            atexit.register(self.cleanup_all)
            self._registered_atexit = True


# Global cleanup registry instance
_global_cleanup_registry = GlobalCleanupRegistry()


@dataclass
class SecureFileService:
    """
    Centralized secure file operations service.

    Provides secure temporary file and directory creation with automatic cleanup,
    permission controls, and path traversal protection.

    This service replaces insecure patterns throughout the codebase.
    """
    temp_file_registry: Set[str] = field(default_factory=set)
    cleanup_handlers: List[Callable] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def create_secure_temp_file(self, suffix: str = '', prefix: str = 'svg2pptx_') -> SecureTempFile:
        """
        Create secure temporary file with automatic cleanup.

        Uses NamedTemporaryFile pattern to avoid race conditions present in mkstemp.

        Args:
            suffix: File suffix (e.g., '.pptx', '.svg')
            prefix: File prefix for identification

        Returns:
            SecureTempFile object with path and cleanup capabilities

        Raises:
            SecureFileOperationError: If temporary file creation fails
        """
        try:
            # Use NamedTemporaryFile with delete=False for secure creation
            with tempfile.NamedTemporaryFile(suffix=suffix, prefix=prefix, delete=False) as tmp:
                temp_path = tmp.name
                file_descriptor = tmp.fileno()

            # Set secure permissions (owner read/write only)
            os.chmod(temp_path, 0o600)

            secure_file = SecureTempFile(path=temp_path, file_descriptor=None)

            with self._lock:
                self.temp_file_registry.add(temp_path)

            logger.debug(f"Created secure temp file: {temp_path}")
            return secure_file

        except (OSError, IOError) as e:
            raise SecureFileOperationError(f"Failed to create secure temp file: {e}")

    def create_secure_temp_dir(self, prefix: str = 'svg2pptx_dir_') -> SecureTempDir:
        """
        Create secure temporary directory with permissions control.

        Uses mkdtemp with immediate permission setting to minimize race window.

        Args:
            prefix: Directory prefix for identification

        Returns:
            SecureTempDir object with path and cleanup capabilities

        Raises:
            SecureFileOperationError: If temporary directory creation fails
        """
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix=prefix)

            # Set secure permissions immediately (owner read/write/execute only)
            os.chmod(temp_dir, 0o700)

            secure_dir = SecureTempDir(path=temp_dir)

            with self._lock:
                self.temp_file_registry.add(temp_dir)

            logger.debug(f"Created secure temp dir: {temp_dir}")
            return secure_dir

        except (OSError, IOError) as e:
            raise SecureFileOperationError(f"Failed to create secure temp dir: {e}")

    def validate_output_path(self, path: str, allowed_directories: Optional[List[str]] = None) -> str:
        """
        Validate and sanitize output paths against traversal attacks.

        Prevents path traversal attacks like ../../../etc/passwd or absolute paths
        to system directories.

        Args:
            path: Output path to validate
            allowed_directories: Optional list of allowed base directories

        Returns:
            Sanitized absolute path

        Raises:
            PathTraversalError: If path contains traversal attempts or is unsafe
            SecureFileOperationError: If path validation fails
        """
        if not path:
            raise SecureFileOperationError("Output path cannot be empty")

        try:
            # URL decode the path to catch encoded traversal attempts
            import urllib.parse
            decoded_path = urllib.parse.unquote(path)

            # Check for path traversal attempts in both original and decoded paths
            for check_path in [path, decoded_path]:
                if '..' in check_path:
                    raise PathTraversalError(f"Path contains traversal elements: {path}")

            # Resolve to absolute path and normalize
            abs_path = os.path.abspath(os.path.normpath(decoded_path))

            # Additional check: ensure the resolved path doesn't go above current working directory
            # unless it's an absolute path that was explicitly provided
            if not path.startswith('/') and not os.path.abspath(os.getcwd()) in abs_path:
                # Check if resolved path went outside current directory tree
                cwd_abs = os.path.abspath(os.getcwd())
                try:
                    os.path.relpath(abs_path, cwd_abs)
                    if abs_path.startswith('..'):
                        raise PathTraversalError(f"Path resolves outside current directory: {path}")
                except ValueError:
                    # Different drives on Windows, check if it's a system path
                    pass

            # Validate against system directories
            system_dirs = ['/etc', '/sys', '/proc', '/dev', '/root', '/boot']
            for system_dir in system_dirs:
                if abs_path.startswith(system_dir):
                    raise PathTraversalError(f"Path targets system directory: {abs_path}")

            # If allowed directories specified, validate against them
            if allowed_directories:
                allowed = False
                for allowed_dir in allowed_directories:
                    allowed_abs = os.path.abspath(allowed_dir)
                    if abs_path.startswith(allowed_abs):
                        allowed = True
                        break

                if not allowed:
                    raise PathTraversalError(f"Path not in allowed directories: {abs_path}")

            # Ensure parent directory exists or can be created
            parent_dir = os.path.dirname(abs_path)
            if not os.path.exists(parent_dir):
                try:
                    os.makedirs(parent_dir, mode=0o755, exist_ok=True)
                except OSError as e:
                    raise SecureFileOperationError(f"Cannot create parent directory {parent_dir}: {e}")

            logger.debug(f"Validated output path: {abs_path}")
            return abs_path

        except (OSError, IOError) as e:
            raise SecureFileOperationError(f"Path validation failed for {path}: {e}")

    @contextmanager
    def secure_temp_file_context(self, suffix: str = '', prefix: str = 'svg2pptx_') -> ContextManager[str]:
        """
        Context manager for secure temporary file operations.

        Automatically cleans up the temporary file when exiting the context.

        Args:
            suffix: File suffix
            prefix: File prefix

        Yields:
            Temporary file path

        Example:
            with service.secure_temp_file_context('.pptx') as temp_path:
                # Use temp_path for operations
                create_pptx(temp_path)
            # File is automatically cleaned up here
        """
        secure_file = self.create_secure_temp_file(suffix=suffix, prefix=prefix)
        try:
            yield secure_file.path
        finally:
            secure_file.cleanup()
            with self._lock:
                self.temp_file_registry.discard(secure_file.path)

    @contextmanager
    def secure_temp_dir_context(self, prefix: str = 'svg2pptx_dir_') -> ContextManager[str]:
        """
        Context manager for secure temporary directory operations.

        Automatically cleans up the temporary directory when exiting the context.

        Args:
            prefix: Directory prefix

        Yields:
            Temporary directory path
        """
        secure_dir = self.create_secure_temp_dir(prefix=prefix)
        try:
            yield secure_dir.path
        finally:
            secure_dir.cleanup()
            with self._lock:
                self.temp_file_registry.discard(secure_dir.path)

    def add_cleanup_handler(self, handler: Callable):
        """
        Add cleanup handler to be called when service is cleaned up.

        Args:
            handler: Callable to be executed during cleanup
        """
        with self._lock:
            self.cleanup_handlers.append(handler)
        _global_cleanup_registry.add_cleanup_handler(handler)

    def cleanup_all_temp_files(self) -> int:
        """
        Clean up all temporary files created by this service.

        Returns:
            Number of files successfully cleaned up
        """
        cleanup_count = 0

        with self._lock:
            temp_files_copy = list(self.temp_file_registry)

        for temp_file in temp_files_copy:
            try:
                if os.path.isfile(temp_file):
                    os.unlink(temp_file)
                    cleanup_count += 1
                elif os.path.isdir(temp_file):
                    import shutil
                    shutil.rmtree(temp_file, ignore_errors=True)
                    cleanup_count += 1

            except OSError as e:
                logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")

        with self._lock:
            self.temp_file_registry.clear()

        logger.info(f"Cleaned up {cleanup_count} temporary files")
        return cleanup_count

    def get_temp_file_count(self) -> int:
        """Get the current number of registered temporary files."""
        with self._lock:
            return len(self.temp_file_registry)

    def get_secure_temp_dir(self) -> str:
        """Get a secure temporary directory path for manual operations."""
        return tempfile.gettempdir()

    @classmethod
    def create_default(cls) -> 'SecureFileService':
        """Create a default SecureFileService instance."""
        return cls()


# Default global instance for convenience
default_secure_file_service = SecureFileService.create_default()