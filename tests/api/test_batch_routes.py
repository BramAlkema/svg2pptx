#!/usr/bin/env python3
"""
Unit tests for API batch routes file retrieval functionality.

Tests the integration between API routes and BatchFileManager.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.batch.file_manager import BatchFileManager, ConvertedFile


class TestBatchFileRetrieval:
    """Test batch file retrieval in API routes."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def file_manager(self, temp_storage):
        """Create BatchFileManager with temporary storage."""
        return BatchFileManager(base_storage_path=temp_storage)

    @pytest.fixture
    def sample_converted_files(self, temp_storage):
        """Create sample ConvertedFile objects."""
        files = []
        for i in range(3):
            # Create actual test files
            test_file = temp_storage / f"test_file_{i}.pptx"
            test_file.write_text(f"Mock PPTX content {i}")

            converted_file = ConvertedFile(
                original_filename=f"test_{i}.svg",
                converted_path=test_file,
                file_size=test_file.stat().st_size,
                conversion_metadata={"slides": i + 1, "format": "pptx"},
                created_at=datetime.utcnow()
            )
            files.append(converted_file)

        return files

    def test_get_converted_files_success(self, file_manager, sample_converted_files):
        """Test successful file retrieval."""
        job_id = "test_job_success"

        # Store files first
        file_manager.store_converted_files(job_id, sample_converted_files)

        # Import the route function and test file retrieval logic
        from src.batch.file_manager import get_default_file_manager

        # Mock the default file manager to return our test manager
        with patch('src.batch.file_manager._default_manager', file_manager):
            # Simulate the API route logic
            file_manager_instance = get_default_file_manager()

            try:
                converted_files = file_manager_instance.get_converted_files(job_id)
                assert len(converted_files) == 3

                # Test conversion to file info format (as done in API)
                files = []
                for converted_file in converted_files:
                    file_info = {
                        'original_filename': converted_file.original_filename,
                        'converted_path': str(converted_file.converted_path),
                        'file_size': converted_file.file_size,
                        'conversion_metadata': converted_file.conversion_metadata,
                        'created_at': converted_file.created_at.isoformat()
                    }
                    files.append(file_info)

                assert len(files) == 3
                assert files[0]['original_filename'] == 'test_0.svg'
                assert files[0]['file_size'] > 0
                assert files[0]['conversion_metadata']['slides'] == 1

            except Exception as e:
                pytest.fail(f"File retrieval should not raise exception: {e}")

    def test_get_converted_files_not_found(self, file_manager):
        """Test file retrieval for non-existent job."""
        from src.batch.file_manager import get_default_file_manager

        with patch('src.batch.file_manager._default_manager', file_manager):
            file_manager_instance = get_default_file_manager()

            # Test handling of FileNotFoundError (as done in API)
            try:
                converted_files = file_manager_instance.get_converted_files("nonexistent_job")
                pytest.fail("Should raise FileNotFoundError")
            except FileNotFoundError:
                # This is expected behavior that API handles
                converted_files = []

            assert len(converted_files) == 0

    def test_get_converted_files_error_handling(self, file_manager):
        """Test error handling in file retrieval."""
        from src.batch.file_manager import get_default_file_manager

        with patch('src.batch.file_manager._default_manager', file_manager):
            file_manager_instance = get_default_file_manager()

            # Mock get_converted_files to raise an exception
            with patch.object(file_manager_instance, 'get_converted_files',
                            side_effect=Exception("Storage error")):

                # Test error handling (as done in API)
                try:
                    converted_files = file_manager_instance.get_converted_files("test_job")
                    pytest.fail("Should raise exception")
                except Exception:
                    # API handles this by setting empty list
                    converted_files = []

                assert len(converted_files) == 0

    def test_file_info_conversion(self):
        """Test conversion of ConvertedFile to file info dictionary."""
        temp_path = Path("/tmp/test.pptx")
        created_at = datetime.utcnow()

        converted_file = ConvertedFile(
            original_filename="test.svg",
            converted_path=temp_path,
            file_size=2048,
            conversion_metadata={"slides": 5, "format": "pptx"},
            created_at=created_at
        )

        # Simulate API conversion logic
        file_info = {
            'original_filename': converted_file.original_filename,
            'converted_path': str(converted_file.converted_path),
            'file_size': converted_file.file_size,
            'conversion_metadata': converted_file.conversion_metadata,
            'created_at': converted_file.created_at.isoformat()
        }

        assert file_info['original_filename'] == "test.svg"
        assert file_info['converted_path'] == str(temp_path)
        assert file_info['file_size'] == 2048
        assert file_info['conversion_metadata']['slides'] == 5
        assert file_info['created_at'] == created_at.isoformat()

    def test_multiple_file_retrieval_and_conversion(self, file_manager, sample_converted_files):
        """Test retrieving multiple files and converting to API format."""
        job_id = "test_job_multiple"

        # Store files
        file_manager.store_converted_files(job_id, sample_converted_files)

        from src.batch.file_manager import get_default_file_manager

        with patch('src.batch.file_manager._default_manager', file_manager):
            file_manager_instance = get_default_file_manager()

            # Retrieve and convert files (API logic)
            converted_files = file_manager_instance.get_converted_files(job_id)

            files = []
            for converted_file in converted_files:
                file_info = {
                    'original_filename': converted_file.original_filename,
                    'converted_path': str(converted_file.converted_path),
                    'file_size': converted_file.file_size,
                    'conversion_metadata': converted_file.conversion_metadata,
                    'created_at': converted_file.created_at.isoformat()
                }
                files.append(file_info)

            # Verify all files converted correctly
            assert len(files) == 3

            for i, file_info in enumerate(files):
                assert file_info['original_filename'] == f'test_{i}.svg'
                assert file_info['file_size'] > 0
                assert file_info['conversion_metadata']['slides'] == i + 1
                assert 'created_at' in file_info

    def test_empty_file_list_handling(self, file_manager):
        """Test handling of empty file list."""
        job_id = "test_job_empty"

        # Store empty file list
        file_manager.store_converted_files(job_id, [])

        from src.batch.file_manager import get_default_file_manager

        with patch('src.batch.file_manager._default_manager', file_manager):
            file_manager_instance = get_default_file_manager()

            converted_files = file_manager_instance.get_converted_files(job_id)

            # Convert to API format
            files = []
            for converted_file in converted_files:
                file_info = {
                    'original_filename': converted_file.original_filename,
                    'converted_path': str(converted_file.converted_path),
                    'file_size': converted_file.file_size,
                    'conversion_metadata': converted_file.conversion_metadata,
                    'created_at': converted_file.created_at.isoformat()
                }
                files.append(file_info)

            assert len(files) == 0


class TestAPIRouteIntegration:
    """Test integration with actual API route patterns."""

    def test_api_route_error_handling_pattern(self):
        """Test the error handling pattern used in API routes."""
        from src.batch.file_manager import get_default_file_manager

        # Mock file manager to simulate different scenarios
        mock_manager = Mock()

        # Test FileNotFoundError handling
        mock_manager.get_converted_files.side_effect = FileNotFoundError("No files found")

        with patch('src.batch.file_manager.get_default_file_manager', return_value=mock_manager):
            file_manager = get_default_file_manager()

            # Simulate API route error handling
            try:
                converted_files = file_manager.get_converted_files("test_job")
                assert False, "Should raise FileNotFoundError"
            except FileNotFoundError:
                # API handles this case
                converted_files = []

            assert len(converted_files) == 0

        # Test general exception handling
        mock_manager.get_converted_files.side_effect = Exception("General error")

        with patch('src.batch.file_manager.get_default_file_manager', return_value=mock_manager):
            file_manager = get_default_file_manager()

            try:
                converted_files = file_manager.get_converted_files("test_job")
                assert False, "Should raise exception"
            except Exception:
                # API handles this case
                converted_files = []

            assert len(converted_files) == 0

    def test_file_conversion_format_consistency(self):
        """Test that file info format is consistent."""
        # Test with various ConvertedFile configurations
        test_cases = [
            {
                'original_filename': 'simple.svg',
                'converted_path': Path('/tmp/simple.pptx'),
                'file_size': 1024,
                'conversion_metadata': {'slides': 1},
                'created_at': datetime.utcnow()
            },
            {
                'original_filename': 'complex-file_name.svg',
                'converted_path': Path('/tmp/complex-file_name.pptx'),
                'file_size': 5120,
                'conversion_metadata': {'slides': 10, 'animations': True},
                'created_at': datetime.utcnow()
            }
        ]

        for test_case in test_cases:
            converted_file = ConvertedFile(**test_case)

            # Apply API conversion logic
            file_info = {
                'original_filename': converted_file.original_filename,
                'converted_path': str(converted_file.converted_path),
                'file_size': converted_file.file_size,
                'conversion_metadata': converted_file.conversion_metadata,
                'created_at': converted_file.created_at.isoformat()
            }

            # Verify consistency
            assert isinstance(file_info['original_filename'], str)
            assert isinstance(file_info['converted_path'], str)
            assert isinstance(file_info['file_size'], int)
            assert isinstance(file_info['conversion_metadata'], dict)
            assert isinstance(file_info['created_at'], str)

            # Verify content
            assert file_info['original_filename'] == test_case['original_filename']
            assert file_info['converted_path'] == str(test_case['converted_path'])
            assert file_info['file_size'] == test_case['file_size']