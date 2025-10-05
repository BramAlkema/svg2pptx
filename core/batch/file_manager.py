#!/usr/bin/env python3
"""
Batch File Management System

Provides robust file storage, retrieval, and cleanup for batch processing operations.
Handles job-specific temporary directories with thread-safe operations and automatic cleanup.
"""

import logging
import shutil
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class ConvertedFile:
    """Represents a converted file in the batch processing system."""
    original_filename: str
    converted_path: Path
    file_size: int
    conversion_metadata: dict[str, any]
    created_at: datetime

    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary for serialization."""
        return {
            'original_filename': self.original_filename,
            'converted_path': str(self.converted_path),
            'file_size': self.file_size,
            'conversion_metadata': self.conversion_metadata,
            'created_at': self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, any]) -> 'ConvertedFile':
        """Create from dictionary for deserialization."""
        return cls(
            original_filename=data['original_filename'],
            converted_path=Path(data['converted_path']),
            file_size=data['file_size'],
            conversion_metadata=data['conversion_metadata'],
            created_at=datetime.fromisoformat(data['created_at']),
        )


class BatchFileManager:
    """
    Manages temporary file storage and retrieval for batch operations.

    Provides thread-safe operations with job-specific directory structure,
    automatic cleanup mechanisms, and comprehensive error handling.
    """

    def __init__(self, base_storage_path: str | Path | None = None,
                 retention_hours: int = 24):
        """
        Initialize BatchFileManager.

        Args:
            base_storage_path: Base directory for file storage (defaults to data/batch_files)
            retention_hours: Hours to retain files before cleanup (default: 24)
        """
        if base_storage_path is None:
            base_storage_path = Path(__file__).parent.parent.parent / "data" / "batch_files"

        self.base_storage_path = Path(base_storage_path)
        self.retention_hours = retention_hours
        self._lock = threading.RLock()  # Reentrant lock for nested operations

        # Ensure base storage directory exists
        self.base_storage_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"BatchFileManager initialized with storage: {self.base_storage_path}")

    def get_job_directory(self, job_id: str) -> Path:
        """Get the directory path for a specific job."""
        return self.base_storage_path / f"job_{job_id}"

    def store_converted_files(self, job_id: str, files: list[ConvertedFile]) -> None:
        """
        Store converted files for a batch job.

        Args:
            job_id: Batch job identifier
            files: List of ConvertedFile objects to store

        Raises:
            OSError: If file operations fail
            ValueError: If job_id is invalid
        """
        if not job_id or not job_id.strip():
            raise ValueError("job_id cannot be empty")

        with self._lock:
            job_dir = self.get_job_directory(job_id)

            try:
                # Create job directory if it doesn't exist
                job_dir.mkdir(parents=True, exist_ok=True)

                # Store each file and create metadata
                stored_files = []
                for file_obj in files:
                    # Copy file to job directory if not already there
                    target_path = job_dir / file_obj.original_filename

                    if file_obj.converted_path != target_path:
                        # Copy file to job directory
                        shutil.copy2(file_obj.converted_path, target_path)

                        # Update file object with new path
                        file_obj.converted_path = target_path
                        file_obj.file_size = target_path.stat().st_size

                    stored_files.append(file_obj)

                # Save metadata file
                metadata_path = job_dir / "file_metadata.json"
                import json

                metadata = {
                    'job_id': job_id,
                    'stored_at': datetime.utcnow().isoformat(),
                    'files': [f.to_dict() for f in stored_files],
                }

                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)

                logger.info(f"Stored {len(files)} files for job {job_id}")

            except Exception as e:
                logger.error(f"Failed to store files for job {job_id}: {e}")
                # Cleanup partial files on failure
                if job_dir.exists():
                    shutil.rmtree(job_dir, ignore_errors=True)
                raise OSError(f"Failed to store files: {e}") from e

    def get_converted_files(self, job_id: str) -> list[ConvertedFile]:
        """
        Retrieve all converted files for a batch job.

        Args:
            job_id: Batch job identifier

        Returns:
            List of ConvertedFile objects

        Raises:
            FileNotFoundError: If job directory or metadata doesn't exist
            ValueError: If job_id is invalid or metadata is corrupted
        """
        if not job_id or not job_id.strip():
            raise ValueError("job_id cannot be empty")

        with self._lock:
            job_dir = self.get_job_directory(job_id)
            metadata_path = job_dir / "file_metadata.json"

            if not job_dir.exists():
                raise FileNotFoundError(f"No files found for job {job_id}")

            if not metadata_path.exists():
                raise FileNotFoundError(f"Metadata not found for job {job_id}")

            try:
                import json

                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)

                # Validate metadata structure
                if 'files' not in metadata:
                    raise ValueError(f"Invalid metadata format for job {job_id}")

                # Convert to ConvertedFile objects and validate file existence
                converted_files = []
                for file_data in metadata['files']:
                    converted_file = ConvertedFile.from_dict(file_data)

                    # Verify file still exists
                    if not converted_file.converted_path.exists():
                        logger.warning(f"File missing: {converted_file.converted_path}")
                        continue

                    # Update file size if changed
                    current_size = converted_file.converted_path.stat().st_size
                    if current_size != converted_file.file_size:
                        logger.info(f"File size updated for {converted_file.original_filename}")
                        converted_file.file_size = current_size

                    converted_files.append(converted_file)

                logger.info(f"Retrieved {len(converted_files)} files for job {job_id}")
                return converted_files

            except (json.JSONDecodeError, KeyError) as e:
                raise ValueError(f"Corrupted metadata for job {job_id}: {e}") from e
            except Exception as e:
                logger.error(f"Failed to retrieve files for job {job_id}: {e}")
                raise

    def cleanup_job_files(self, job_id: str) -> bool:
        """
        Clean up all files for a completed job.

        Args:
            job_id: Batch job identifier

        Returns:
            True if cleanup successful, False otherwise
        """
        if not job_id or not job_id.strip():
            logger.warning("Cannot cleanup: empty job_id")
            return False

        with self._lock:
            job_dir = self.get_job_directory(job_id)

            if not job_dir.exists():
                logger.info(f"No files to cleanup for job {job_id}")
                return True

            try:
                shutil.rmtree(job_dir)
                logger.info(f"Cleaned up files for job {job_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to cleanup files for job {job_id}: {e}")
                return False

    def cleanup_expired_files(self) -> int:
        """
        Clean up files older than retention period.

        Returns:
            Number of jobs cleaned up
        """
        if not self.base_storage_path.exists():
            return 0

        cleanup_count = 0
        cutoff_time = datetime.utcnow() - timedelta(hours=self.retention_hours)

        with self._lock:
            try:
                for job_dir in self.base_storage_path.iterdir():
                    if not job_dir.is_dir() or not job_dir.name.startswith('job_'):
                        continue

                    # Check directory modification time
                    dir_mtime = datetime.fromtimestamp(job_dir.stat().st_mtime)

                    if dir_mtime < cutoff_time:
                        try:
                            job_id = job_dir.name[4:]  # Remove 'job_' prefix
                            if self.cleanup_job_files(job_id):
                                cleanup_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to cleanup expired job {job_dir}: {e}")

                if cleanup_count > 0:
                    logger.info(f"Cleaned up {cleanup_count} expired job directories")

            except Exception as e:
                logger.error(f"Error during expired file cleanup: {e}")

        return cleanup_count

    def get_storage_stats(self) -> dict[str, any]:
        """
        Get storage statistics for monitoring.

        Returns:
            Dictionary with storage metrics
        """
        stats = {
            'total_jobs': 0,
            'total_files': 0,
            'total_size_bytes': 0,
            'oldest_job': None,
            'newest_job': None,
        }

        if not self.base_storage_path.exists():
            return stats

        with self._lock:
            try:
                oldest_time = None
                newest_time = None

                for job_dir in self.base_storage_path.iterdir():
                    if not job_dir.is_dir() or not job_dir.name.startswith('job_'):
                        continue

                    stats['total_jobs'] += 1

                    # Count files and calculate size
                    for file_path in job_dir.rglob('*'):
                        if file_path.is_file():
                            stats['total_files'] += 1
                            stats['total_size_bytes'] += file_path.stat().st_size

                    # Track oldest and newest
                    dir_mtime = datetime.fromtimestamp(job_dir.stat().st_mtime)
                    if oldest_time is None or dir_mtime < oldest_time:
                        oldest_time = dir_mtime
                        stats['oldest_job'] = job_dir.name[4:]
                    if newest_time is None or dir_mtime > newest_time:
                        newest_time = dir_mtime
                        stats['newest_job'] = job_dir.name[4:]

            except Exception as e:
                logger.error(f"Error calculating storage stats: {e}")

        return stats

    @contextmanager
    def temporary_job_context(self, job_id: str):
        """
        Context manager for temporary job operations with automatic cleanup.

        Args:
            job_id: Batch job identifier

        Yields:
            Path to job directory
        """
        job_dir = self.get_job_directory(job_id)

        try:
            job_dir.mkdir(parents=True, exist_ok=True)
            yield job_dir
        finally:
            # Cleanup on exit (success or failure)
            self.cleanup_job_files(job_id)

    def extract_zip_with_structure(self, job_id: str, zip_file_path: str | Path,
                                  preserve_structure: bool = True) -> dict[str, list[str]]:
        """
        Extract ZIP file and return file structure information.

        Args:
            job_id: Batch job identifier
            zip_file_path: Path to ZIP file to extract
            preserve_structure: Whether to preserve folder structure

        Returns:
            Dictionary with 'files' list and 'structure' information

        Raises:
            ValueError: If ZIP file is invalid or job_id is empty
            FileNotFoundError: If ZIP file doesn't exist
        """
        import json
        import zipfile

        if not job_id or not job_id.strip():
            raise ValueError("job_id cannot be empty")

        zip_path = Path(zip_file_path)
        if not zip_path.exists():
            raise FileNotFoundError(f"ZIP file not found: {zip_file_path}")

        with self._lock:
            job_dir = self.get_job_directory(job_id)
            job_dir.mkdir(parents=True, exist_ok=True)

            extracted_files = []
            folder_structure = {}

            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Get ZIP file information
                    zip_info_list = zip_ref.infolist()

                    for zip_info in zip_info_list:
                        # Skip directories
                        if zip_info.is_dir():
                            continue

                        # Extract file
                        source_path = zip_info.filename

                        if preserve_structure:
                            # Preserve folder structure
                            extract_path = job_dir / source_path
                            extract_path.parent.mkdir(parents=True, exist_ok=True)
                        else:
                            # Flatten structure - extract to job root
                            filename = Path(source_path).name
                            extract_path = job_dir / filename

                        # Extract the file
                        with zip_ref.open(zip_info) as source, open(extract_path, 'wb') as target:
                            shutil.copyfileobj(source, target)

                        # Record file information
                        file_info = {
                            'original_path': source_path,
                            'extracted_path': str(extract_path.relative_to(job_dir)),
                            'file_size': zip_info.file_size,
                            'folder_path': str(Path(source_path).parent) if Path(source_path).parent != Path('.') else '',
                        }
                        extracted_files.append(file_info)

                        # Build folder structure
                        folder_path = str(Path(source_path).parent)
                        if folder_path and folder_path != '.':
                            if folder_path not in folder_structure:
                                folder_structure[folder_path] = []
                            folder_structure[folder_path].append(Path(source_path).name)

                # Save ZIP metadata
                zip_metadata = {
                    'zip_file_path': str(zip_path),
                    'extraction_time': datetime.now().isoformat(),
                    'preserve_structure': preserve_structure,
                    'total_files': len(extracted_files),
                    'folder_structure': folder_structure,
                    'extracted_files': extracted_files,
                }

                metadata_path = job_dir / "zip_metadata.json"
                with open(metadata_path, 'w') as f:
                    json.dump(zip_metadata, f, indent=2)

                logger.info(f"Extracted {len(extracted_files)} files from ZIP for job {job_id}")

                return {
                    'files': extracted_files,
                    'structure': folder_structure,
                    'metadata': zip_metadata,
                }

            except zipfile.BadZipFile:
                raise ValueError(f"Invalid ZIP file: {zip_file_path}")
            except Exception as e:
                logger.error(f"Failed to extract ZIP file: {e}")
                raise

    def get_zip_structure_info(self, job_id: str) -> dict[str, any] | None:
        """
        Get ZIP structure information for a job.

        Args:
            job_id: Batch job identifier

        Returns:
            ZIP metadata dictionary or None if not found
        """
        if not job_id or not job_id.strip():
            return None

        with self._lock:
            job_dir = self.get_job_directory(job_id)
            metadata_path = job_dir / "zip_metadata.json"

            if not metadata_path.exists():
                return None

            try:
                import json
                with open(metadata_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read ZIP metadata for job {job_id}: {e}")
                return None

    def create_zip_from_converted_files(self, job_id: str, output_path: str | Path,
                                      preserve_structure: bool = True) -> bool:
        """
        Create ZIP file from converted files, optionally preserving folder structure.

        Args:
            job_id: Batch job identifier
            output_path: Path for output ZIP file
            preserve_structure: Whether to preserve original folder structure

        Returns:
            True if successful, False otherwise
        """
        import zipfile

        if not job_id or not job_id.strip():
            return False

        try:
            with self._lock:
                job_dir = self.get_job_directory(job_id)
                if not job_dir.exists():
                    logger.warning(f"No files found for job {job_id}")
                    return False

                # Get ZIP structure info if available
                zip_info = self.get_zip_structure_info(job_id)
                converted_files = self.get_converted_files(job_id)

                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
                    for converted_file in converted_files:
                        file_path = converted_file.converted_path

                        if preserve_structure and zip_info:
                            # Try to preserve original structure
                            original_folder = None
                            for file_info in zip_info.get('extracted_files', []):
                                if Path(file_info['extracted_path']).name == file_path.name:
                                    original_folder = file_info.get('folder_path', '')
                                    break

                            if original_folder:
                                archive_name = f"{original_folder}/{file_path.name}"
                            else:
                                archive_name = file_path.name
                        else:
                            # Flat structure
                            archive_name = file_path.name

                        zip_ref.write(file_path, archive_name)

                logger.info(f"Created ZIP file with {len(converted_files)} files: {output_path}")
                return True

        except Exception as e:
            logger.error(f"Failed to create ZIP file: {e}")
            return False


# Global instance for convenience
_default_manager = None

def get_default_file_manager() -> BatchFileManager:
    """Get the default BatchFileManager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = BatchFileManager()
    return _default_manager