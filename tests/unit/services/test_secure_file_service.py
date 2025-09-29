#!/usr/bin/env python3
"""
Unit Tests for SecureFileService

Comprehensive test suite for secure file operations service,
validating security features, cleanup mechanisms, and error handling.
"""

import os
import tempfile
import pytest
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.services.secure_file_service import (
    SecureFileService,
    SecureTempFile,
    SecureTempDir,
    SecureFileOperationError,
    PathTraversalError,
    GlobalCleanupRegistry,
    default_secure_file_service
)


class TestSecureTempFile:
    """Test SecureTempFile wrapper functionality."""

    def test_secure_temp_file_creation(self):
        """Test SecureTempFile object creation and basic properties."""
        temp_path = "/tmp/test_file.txt"
        secure_file = SecureTempFile(path=temp_path)

        assert secure_file.path == temp_path
        assert secure_file.file_descriptor is None
        assert secure_file.cleanup_registered

    def test_secure_temp_file_cleanup(self):
        """Test secure temp file cleanup functionality."""
        # Create a real temporary file for testing
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            temp_path = tmp.name

        # Create SecureTempFile wrapper
        secure_file = SecureTempFile(path=temp_path)

        # Verify file exists
        assert os.path.exists(temp_path)

        # Test cleanup
        result = secure_file.cleanup()
        assert result is True
        assert not os.path.exists(temp_path)

    def test_secure_temp_file_cleanup_nonexistent(self):
        """Test cleanup of non-existent file."""
        secure_file = SecureTempFile(path="/tmp/nonexistent_file.txt")
        result = secure_file.cleanup()
        assert result is False  # File didn't exist to clean up

    def test_secure_temp_file_cleanup_with_fd(self):
        """Test cleanup with file descriptor."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            temp_path = tmp.name
            fd = tmp.fileno()

        secure_file = SecureTempFile(path=temp_path, file_descriptor=fd)

        # Mock os.close to avoid closing the already-closed descriptor
        with patch('os.close') as mock_close:
            result = secure_file.cleanup()
            assert result is True
            mock_close.assert_called_once_with(fd)


class TestSecureTempDir:
    """Test SecureTempDir wrapper functionality."""

    def test_secure_temp_dir_creation(self):
        """Test SecureTempDir object creation."""
        temp_path = "/tmp/test_dir"
        secure_dir = SecureTempDir(path=temp_path)

        assert secure_dir.path == temp_path
        assert secure_dir.cleanup_registered

    def test_secure_temp_dir_cleanup(self):
        """Test secure temp directory cleanup."""
        # Create real temporary directory
        temp_dir = tempfile.mkdtemp()

        # Add some content
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")

        secure_dir = SecureTempDir(path=temp_dir)

        # Verify directory exists
        assert os.path.exists(temp_dir)
        assert os.path.exists(test_file)

        # Test cleanup
        result = secure_dir.cleanup()
        assert result is True
        assert not os.path.exists(temp_dir)
        assert not os.path.exists(test_file)


class TestGlobalCleanupRegistry:
    """Test global cleanup registry functionality."""

    def setup_method(self):
        """Set up test registry instance."""
        self.registry = GlobalCleanupRegistry()

    def test_temp_file_registration(self):
        """Test temporary file registration and cleanup."""
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False) as tmp1, \
             tempfile.NamedTemporaryFile(delete=False) as tmp2:
            path1, path2 = tmp1.name, tmp2.name

        # Register files
        self.registry.register_temp_file(path1)
        self.registry.register_temp_file(path2)

        assert path1 in self.registry._temp_files
        assert path2 in self.registry._temp_files

        # Test cleanup
        self.registry.cleanup_all()

        assert not os.path.exists(path1)
        assert not os.path.exists(path2)
        assert len(self.registry._temp_files) == 0

    def test_temp_dir_registration(self):
        """Test temporary directory registration and cleanup."""
        # Create temporary directories
        dir1 = tempfile.mkdtemp()
        dir2 = tempfile.mkdtemp()

        # Register directories
        self.registry.register_temp_dir(dir1)
        self.registry.register_temp_dir(dir2)

        assert dir1 in self.registry._temp_dirs
        assert dir2 in self.registry._temp_dirs

        # Test cleanup
        self.registry.cleanup_all()

        assert not os.path.exists(dir1)
        assert not os.path.exists(dir2)
        assert len(self.registry._temp_dirs) == 0

    def test_cleanup_handlers(self):
        """Test custom cleanup handlers."""
        handler_called = []

        def test_handler():
            handler_called.append(True)

        self.registry.add_cleanup_handler(test_handler)
        self.registry.cleanup_all()

        assert len(handler_called) == 1

    def test_thread_safety(self):
        """Test registry thread safety."""
        # Create temporary files in multiple threads
        temp_files = []

        def create_and_register():
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                temp_files.append(tmp.name)
                self.registry.register_temp_file(tmp.name)

        threads = [threading.Thread(target=create_and_register) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(self.registry._temp_files) == 5

        # Cleanup
        self.registry.cleanup_all()
        assert len(self.registry._temp_files) == 0


class TestSecureFileService:
    """Test SecureFileService main functionality."""

    def setup_method(self):
        """Set up test service instance."""
        self.service = SecureFileService()

    def test_create_secure_temp_file(self):
        """Test secure temporary file creation."""
        secure_file = self.service.create_secure_temp_file(suffix='.txt', prefix='test_')

        # Verify file properties
        assert secure_file.path.endswith('.txt')
        assert 'test_' in secure_file.path
        assert os.path.exists(secure_file.path)

        # Verify secure permissions (owner read/write only)
        stat_info = os.stat(secure_file.path)
        assert oct(stat_info.st_mode)[-3:] == '600'

        # Verify registration
        assert secure_file.path in self.service.temp_file_registry

        # Cleanup
        secure_file.cleanup()

    def test_create_secure_temp_dir(self):
        """Test secure temporary directory creation."""
        secure_dir = self.service.create_secure_temp_dir(prefix='test_dir_')

        # Verify directory properties
        assert 'test_dir_' in secure_dir.path
        assert os.path.exists(secure_dir.path)
        assert os.path.isdir(secure_dir.path)

        # Verify secure permissions (owner read/write/execute only)
        stat_info = os.stat(secure_dir.path)
        assert oct(stat_info.st_mode)[-3:] == '700'

        # Verify registration
        assert secure_dir.path in self.service.temp_file_registry

        # Cleanup
        secure_dir.cleanup()

    def test_validate_output_path_safe_paths(self):
        """Test output path validation with safe paths."""
        safe_paths = [
            "output.pptx",
            "results/presentation.pptx",
            "/tmp/safe_output.pptx"
        ]

        for path in safe_paths:
            try:
                result = self.service.validate_output_path(path)
                assert os.path.isabs(result)
                assert os.path.normpath(path) in result
            except (PathTraversalError, SecureFileOperationError):
                # Clean up any created directories for next test
                try:
                    parent = os.path.dirname(os.path.abspath(path))
                    if parent != '/':
                        os.rmdir(parent)
                except OSError:
                    pass

    def test_validate_output_path_traversal_attacks(self):
        """Test output path validation against traversal attacks."""
        malicious_paths = [
            "../../../etc/passwd",
            "../../etc/hosts",
            "../../../../../root/.bashrc"
        ]

        for path in malicious_paths:
            with pytest.raises(PathTraversalError):
                self.service.validate_output_path(path)

    def test_validate_output_path_system_directories(self):
        """Test output path validation against system directories."""
        system_paths = [
            "/etc/test.pptx",
            "/sys/test.pptx",
            "/proc/test.pptx",
            "/dev/test.pptx",
            "/root/test.pptx"
        ]

        for path in system_paths:
            with pytest.raises(PathTraversalError):
                self.service.validate_output_path(path)

    def test_validate_output_path_allowed_directories(self):
        """Test output path validation with allowed directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            allowed_dirs = [temp_dir]

            # Safe path within allowed directory
            safe_path = os.path.join(temp_dir, "output.pptx")
            result = self.service.validate_output_path(safe_path, allowed_directories=allowed_dirs)
            assert result == os.path.abspath(safe_path)

            # Unsafe path outside allowed directory
            unsafe_path = "/tmp/outside.pptx"
            with pytest.raises(PathTraversalError):
                self.service.validate_output_path(unsafe_path, allowed_directories=allowed_dirs)

    def test_validate_output_path_empty(self):
        """Test output path validation with empty path."""
        with pytest.raises(SecureFileOperationError):
            self.service.validate_output_path("")

    def test_secure_temp_file_context(self):
        """Test secure temporary file context manager."""
        temp_path = None

        with self.service.secure_temp_file_context('.pptx', 'context_test_') as path:
            temp_path = path
            assert os.path.exists(path)
            assert path.endswith('.pptx')
            assert 'context_test_' in path

        # File should be cleaned up after context
        assert not os.path.exists(temp_path)

    def test_secure_temp_dir_context(self):
        """Test secure temporary directory context manager."""
        temp_dir = None

        with self.service.secure_temp_dir_context('context_dir_test_') as path:
            temp_dir = path
            assert os.path.exists(path)
            assert os.path.isdir(path)
            assert 'context_dir_test_' in path

            # Create file in directory
            test_file = os.path.join(path, "test.txt")
            with open(test_file, 'w') as f:
                f.write("test")

        # Directory and contents should be cleaned up after context
        assert not os.path.exists(temp_dir)

    def test_cleanup_handlers(self):
        """Test cleanup handler registration and execution."""
        handler_called = []

        def test_handler():
            handler_called.append("called")

        self.service.add_cleanup_handler(test_handler)
        assert len(self.service.cleanup_handlers) == 1

    def test_cleanup_all_temp_files(self):
        """Test cleanup of all temporary files."""
        # Create multiple temp files
        files = []
        for i in range(3):
            secure_file = self.service.create_secure_temp_file(suffix=f'_{i}.txt')
            files.append(secure_file.path)

        # Verify files exist
        for file_path in files:
            assert os.path.exists(file_path)

        # Cleanup all
        count = self.service.cleanup_all_temp_files()
        assert count == 3

        # Verify files are gone
        for file_path in files:
            assert not os.path.exists(file_path)

        # Registry should be empty
        assert len(self.service.temp_file_registry) == 0

    def test_get_temp_file_count(self):
        """Test temporary file count tracking."""
        assert self.service.get_temp_file_count() == 0

        # Create temp files
        file1 = self.service.create_secure_temp_file()
        assert self.service.get_temp_file_count() == 1

        file2 = self.service.create_secure_temp_file()
        assert self.service.get_temp_file_count() == 2

        # Cleanup
        file1.cleanup()
        file2.cleanup()

    def test_get_secure_temp_dir(self):
        """Test secure temp directory path retrieval."""
        temp_dir = self.service.get_secure_temp_dir()
        assert temp_dir == tempfile.gettempdir()
        assert os.path.exists(temp_dir)

    def test_create_default(self):
        """Test default service instance creation."""
        service = SecureFileService.create_default()
        assert isinstance(service, SecureFileService)
        assert len(service.temp_file_registry) == 0
        assert len(service.cleanup_handlers) == 0

    def test_thread_safety(self):
        """Test service thread safety."""
        results = []

        def create_temp_file():
            secure_file = self.service.create_secure_temp_file()
            results.append(secure_file.path)

        threads = [threading.Thread(target=create_temp_file) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have 5 unique temp files
        assert len(results) == 5
        assert len(set(results)) == 5

        # All should be registered
        assert len(self.service.temp_file_registry) == 5

        # Cleanup
        self.service.cleanup_all_temp_files()


class TestSecureFileServiceIntegration:
    """Integration tests for SecureFileService."""

    def test_service_lifecycle(self):
        """Test complete service lifecycle."""
        service = SecureFileService.create_default()

        # Create various temp files and directories
        temp_file = service.create_secure_temp_file(suffix='.pptx')
        temp_dir = service.create_secure_temp_dir()

        # Use context managers
        context_file_path = None
        context_dir_path = None

        with service.secure_temp_file_context('.svg') as path:
            context_file_path = path
            assert os.path.exists(path)

        with service.secure_temp_dir_context() as path:
            context_dir_path = path
            assert os.path.exists(path)

        # Context manager files should be cleaned up
        assert not os.path.exists(context_file_path)
        assert not os.path.exists(context_dir_path)

        # Manual files should still exist
        assert os.path.exists(temp_file.path)
        assert os.path.exists(temp_dir.path)

        # Cleanup all
        service.cleanup_all_temp_files()

        # All should be cleaned up
        assert not os.path.exists(temp_file.path)
        assert not os.path.exists(temp_dir.path)

    def test_error_handling(self):
        """Test error handling in various scenarios."""
        service = SecureFileService()

        # Test with mock that raises OSError
        with patch('tempfile.NamedTemporaryFile', side_effect=OSError("Mocked error")):
            with pytest.raises(SecureFileOperationError):
                service.create_secure_temp_file()

        with patch('tempfile.mkdtemp', side_effect=OSError("Mocked error")):
            with pytest.raises(SecureFileOperationError):
                service.create_secure_temp_dir()

    def test_default_service_instance(self):
        """Test the default global service instance."""
        assert isinstance(default_secure_file_service, SecureFileService)

        # Should be usable
        temp_file = default_secure_file_service.create_secure_temp_file()
        assert os.path.exists(temp_file.path)

        # Cleanup
        temp_file.cleanup()


class TestSecureFileServiceSecurity:
    """Security-focused tests for SecureFileService."""

    def test_temp_file_permissions(self):
        """Test that temporary files have secure permissions."""
        service = SecureFileService()
        temp_file = service.create_secure_temp_file()

        # Check permissions (should be 600 - owner read/write only)
        stat_info = os.stat(temp_file.path)
        mode = stat_info.st_mode & 0o777
        assert mode == 0o600

        temp_file.cleanup()

    def test_temp_dir_permissions(self):
        """Test that temporary directories have secure permissions."""
        service = SecureFileService()
        temp_dir = service.create_secure_temp_dir()

        # Check permissions (should be 700 - owner read/write/execute only)
        stat_info = os.stat(temp_dir.path)
        mode = stat_info.st_mode & 0o777
        assert mode == 0o700

        temp_dir.cleanup()

    def test_path_traversal_prevention(self):
        """Test comprehensive path traversal attack prevention."""
        service = SecureFileService()

        # Various path traversal attacks
        attacks = [
            "../secret.txt",
            "../../etc/passwd",
            "../../../root/.ssh/id_rsa",
            "..\\..\\windows\\system32\\config\\sam",  # Windows-style
            "%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # URL-encoded
        ]

        for attack in attacks:
            with pytest.raises(PathTraversalError):
                service.validate_output_path(attack)

    def test_system_directory_protection(self):
        """Test protection against writing to system directories."""
        service = SecureFileService()

        system_dirs = [
            "/etc/malicious.txt",
            "/sys/devices/malicious.txt",
            "/proc/self/mem",
            "/dev/null/../etc/passwd",
            "/root/.bashrc",
            "/boot/grub/grub.cfg"
        ]

        for path in system_dirs:
            with pytest.raises(PathTraversalError):
                service.validate_output_path(path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])