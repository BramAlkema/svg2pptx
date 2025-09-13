#!/usr/bin/env python3
"""
Unit tests for BatchDriveController and Google Drive folder management.

Tests the Google Drive integration for batch processing including folder creation,
file uploads, preview generation, and error handling.
"""

import pytest
import tempfile
import uuid
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, call
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.batch.drive_controller import (
    BatchDriveController, BatchDriveError, DriveOperationResult,
    FolderStructure, FileUploadResult
)
from src.batch.models import BatchJob, BatchDriveMetadata, BatchFileDriveMetadata


class TestBatchDriveController:
    """Test the BatchDriveController initialization and configuration."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.mock_drive_service = Mock()
        self.mock_slides_service = Mock()
        self.test_db_path = tempfile.NamedTemporaryFile(suffix='.db').name
        
        # Initialize test database
        from src.batch.models import init_database
        init_database(self.test_db_path)
    
    def teardown_method(self):
        """Clean up after each test."""
        Path(self.test_db_path).unlink(missing_ok=True)
    
    def test_controller_initialization(self):
        """Test BatchDriveController initialization."""
        controller = BatchDriveController(
            drive_service=self.mock_drive_service,
            slides_service=self.mock_slides_service,
            db_path=self.test_db_path
        )
        
        assert controller.drive_service == self.mock_drive_service
        assert controller.slides_service == self.mock_slides_service
        assert controller.db_path == self.test_db_path
    
    def test_controller_initialization_with_defaults(self):
        """Test controller initialization with default services."""
        with patch('src.batch.drive_controller.GoogleDriveService') as mock_drive, \
             patch('src.batch.drive_controller.GoogleSlidesService') as mock_slides:
            
            controller = BatchDriveController(db_path=self.test_db_path)
            
            mock_drive.assert_called_once()
            mock_slides.assert_called_once()
            assert controller.db_path == self.test_db_path


class TestFolderCreation:
    """Test Google Drive folder creation and organization."""
    
    def setup_method(self):
        """Set up test environment."""
        self.mock_drive_service = Mock()
        self.mock_slides_service = Mock()
        self.test_db_path = tempfile.NamedTemporaryFile(suffix='.db').name
        
        from src.batch.models import init_database
        init_database(self.test_db_path)
        
        self.controller = BatchDriveController(
            drive_service=self.mock_drive_service,
            slides_service=self.mock_slides_service,
            db_path=self.test_db_path
        )
    
    def teardown_method(self):
        """Clean up after each test."""
        Path(self.test_db_path).unlink(missing_ok=True)
    
    def test_create_batch_folder_default_pattern(self):
        """Test creating batch folder with default naming pattern."""
        batch_job_id = "batch_test_123"
        
        # Create required BatchJob first
        from src.batch.models import BatchJob
        batch_job = BatchJob(
            job_id=batch_job_id,
            status="processing",
            total_files=1,
            drive_integration_enabled=True
        )
        batch_job.save(self.test_db_path)
        
        # Mock Drive API response
        self.mock_drive_service.create_folder.return_value = {
            'success': True,
            'folderId': '1BATCH_FOLDER_ID',
            'folderUrl': 'https://drive.google.com/drive/folders/1BATCH_FOLDER_ID',
            'folderName': 'SVG2PPTX-Batches'
        }
        
        result = self.controller.create_batch_folder(batch_job_id)
        
        assert result.success is True
        assert result.folder_id == '1BATCH_FOLDER_ID'
        assert result.folder_url == 'https://drive.google.com/drive/folders/1BATCH_FOLDER_ID'
        
        # Verify folder creation was called multiple times for hierarchy
        assert self.mock_drive_service.create_folder.call_count == 3
        
        # Verify calls were made for folder hierarchy
        calls = self.mock_drive_service.create_folder.call_args_list
        assert calls[0][0][0] == 'SVG2PPTX-Batches'  # Root folder
        assert calls[1][0][0] == '2025-09-12'  # Date folder  
        assert calls[2][0][0] == 'batch-batch_test_123'  # Batch folder
        
        # Check that folder structure was saved to database
        metadata = BatchDriveMetadata.get_by_job_id(self.test_db_path, batch_job_id)
        assert metadata is not None
        assert metadata.drive_folder_id == '1BATCH_FOLDER_ID'
        assert metadata.drive_folder_url == 'https://drive.google.com/drive/folders/1BATCH_FOLDER_ID'
    
    def test_create_batch_folder_custom_pattern(self):
        """Test creating batch folder with custom naming pattern."""
        batch_job_id = "batch_custom_456"
        custom_pattern = "Client-Assets/{date}/Project-{job_id}/"
        
        # Create required BatchJob first
        from src.batch.models import BatchJob
        batch_job = BatchJob(
            job_id=batch_job_id,
            status="processing",
            total_files=1,
            drive_integration_enabled=True
        )
        batch_job.save(self.test_db_path)
        
        self.mock_drive_service.create_folder.return_value = {
            'success': True,
            'folderId': '1CUSTOM_FOLDER_ID',
            'folderUrl': 'https://drive.google.com/drive/folders/1CUSTOM_FOLDER_ID',
            'folderName': 'Client-Assets'
        }
        
        result = self.controller.create_batch_folder(
            batch_job_id, 
            folder_pattern=custom_pattern
        )
        
        assert result.success is True
        # Should call create_folder 3 times for hierarchy: Client-Assets -> 2025-09-12 -> Project-batch_custom_456
        assert self.mock_drive_service.create_folder.call_count == 3
    
    def test_create_batch_folder_hierarchy(self):
        """Test creating nested folder hierarchy."""
        batch_job_id = "batch_nested_789"
        
        # Create required BatchJob first
        from src.batch.models import BatchJob
        batch_job = BatchJob(
            job_id=batch_job_id,
            status="processing",
            total_files=1,
            drive_integration_enabled=True
        )
        batch_job.save(self.test_db_path)
        
        # Mock multiple folder creation calls for hierarchy
        folder_responses = [
            {'success': True, 'folderId': '1ROOT_FOLDER', 'folderName': 'SVG2PPTX-Batches'},
            {'success': True, 'folderId': '1DATE_FOLDER', 'folderName': '2025-09-12'},
            {'success': True, 'folderId': '1BATCH_FOLDER', 'folderName': 'batch-batch_nested_789'}
        ]
        
        self.mock_drive_service.create_folder.side_effect = folder_responses
        
        result = self.controller.create_batch_folder(batch_job_id)
        
        assert result.success is True
        assert self.mock_drive_service.create_folder.call_count == 3
    
    def test_create_batch_folder_drive_api_error(self):
        """Test handling Drive API errors during folder creation."""
        batch_job_id = "batch_error_999"
        
        self.mock_drive_service.create_folder.side_effect = Exception("Drive API quota exceeded")
        
        with pytest.raises(BatchDriveError, match="Failed to create batch folder"):
            self.controller.create_batch_folder(batch_job_id)


class TestFileUpload:
    """Test batch file upload functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.mock_drive_service = Mock()
        self.mock_slides_service = Mock()
        self.test_db_path = tempfile.NamedTemporaryFile(suffix='.db').name
        
        from src.batch.models import init_database
        init_database(self.test_db_path)
        
        self.controller = BatchDriveController(
            drive_service=self.mock_drive_service,
            slides_service=self.mock_slides_service,
            db_path=self.test_db_path
        )
        
        # Create test batch job
        self.batch_job = BatchJob(
            job_id="batch_upload_test",
            status="processing",
            total_files=2,
            drive_integration_enabled=True
        )
        self.batch_job.save(self.test_db_path)
        
        # Create temporary test files
        self.test_files = []
        for i in range(2):
            tmp_file = tempfile.NamedTemporaryFile(
                suffix='.pptx', 
                delete=False,
                prefix=f'test_file_{i}_'
            )
            tmp_file.write(b'Mock PowerPoint content')
            tmp_file.close()
            self.test_files.append({
                'path': tmp_file.name,
                'original_name': f'design_{i+1}.svg',
                'converted_name': f'design_{i+1}.pptx'
            })
    
    def teardown_method(self):
        """Clean up after each test."""
        Path(self.test_db_path).unlink(missing_ok=True)
        for file_info in self.test_files:
            Path(file_info['path']).unlink(missing_ok=True)
    
    def test_upload_batch_files_success(self):
        """Test successful batch file upload."""
        folder_id = "1BATCH_FOLDER_ID"
        
        # Mock successful Drive uploads
        upload_responses = [
            {
                'success': True,
                'fileId': '1FILE_1_ID',
                'fileName': 'design_1.pptx',
                'shareableLink': 'https://docs.google.com/presentation/d/1FILE_1_ID',
                'webViewLink': 'https://docs.google.com/presentation/d/1FILE_1_ID'
            },
            {
                'success': True,
                'fileId': '1FILE_2_ID',
                'fileName': 'design_2.pptx',
                'shareableLink': 'https://docs.google.com/presentation/d/1FILE_2_ID',
                'webViewLink': 'https://docs.google.com/presentation/d/1FILE_2_ID'
            }
        ]
        
        self.mock_drive_service.upload_file.side_effect = upload_responses
        
        # Upload files
        results = self.controller.upload_batch_files(
            self.batch_job.job_id,
            self.test_files,
            folder_id
        )
        
        assert len(results) == 2
        assert all(result.success for result in results)
        assert results[0].file_id == '1FILE_1_ID'
        assert results[1].file_id == '1FILE_2_ID'
        
        # Verify database was updated
        file_metadata = BatchFileDriveMetadata.get_by_job_id(
            self.test_db_path, 
            self.batch_job.job_id
        )
        assert len(file_metadata) == 2
        assert file_metadata[0].upload_status == "completed"
        assert file_metadata[1].upload_status == "completed"
    
    def test_upload_batch_files_partial_failure(self):
        """Test batch upload with some files failing."""
        folder_id = "1BATCH_FOLDER_ID"
        
        # Mock mixed success/failure responses
        def upload_side_effect(file_path, file_name, folder_id):
            if 'test_file_0_' in file_path:
                return {
                    'success': True,
                    'fileId': '1FILE_SUCCESS_ID',
                    'fileName': file_name,
                    'shareableLink': f'https://docs.google.com/presentation/d/1FILE_SUCCESS_ID'
                }
            else:
                raise Exception("Upload quota exceeded")
        
        self.mock_drive_service.upload_file.side_effect = upload_side_effect
        
        results = self.controller.upload_batch_files(
            self.batch_job.job_id,
            self.test_files,
            folder_id
        )
        
        # Check results
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        assert "Upload quota exceeded" in results[1].error_message
        
        # Verify database reflects mixed results
        file_metadata = BatchFileDriveMetadata.get_by_job_id(
            self.test_db_path, 
            self.batch_job.job_id
        )
        
        success_files = [f for f in file_metadata if f.upload_status == "completed"]
        failed_files = [f for f in file_metadata if f.upload_status == "failed"]
        
        assert len(success_files) == 1
        assert len(failed_files) == 1
        assert failed_files[0].upload_error == "Upload quota exceeded"
    
    def test_parallel_upload_processing(self):
        """Test parallel upload processing for large batches."""
        folder_id = "1BATCH_FOLDER_ID"
        
        # Create larger batch for parallel processing test
        large_batch = []
        for i in range(5):
            tmp_file = tempfile.NamedTemporaryFile(suffix='.pptx', delete=False)
            tmp_file.write(b'Mock content')
            tmp_file.close()
            large_batch.append({
                'path': tmp_file.name,
                'original_name': f'file_{i}.svg',
                'converted_name': f'file_{i}.pptx'
            })
        
        # Mock successful uploads with processing time simulation
        def upload_with_delay(file_path, file_name, folder_id):
            import time
            time.sleep(0.1)  # Simulate upload time
            file_id = f"1FILE_{file_name.replace('.', '_')}_ID"
            return {
                'success': True,
                'fileId': file_id,
                'fileName': file_name,
                'shareableLink': f'https://docs.google.com/presentation/d/{file_id}'
            }
        
        self.mock_drive_service.upload_file.side_effect = upload_with_delay
        
        # Test parallel upload
        with patch('src.batch.drive_controller.concurrent.futures') as mock_futures:
            mock_executor = Mock()
            mock_futures.ThreadPoolExecutor.return_value.__enter__.return_value = mock_executor
            mock_executor.submit.side_effect = lambda fn, *args: Mock(result=lambda: fn(*args))
            
            results = self.controller.upload_batch_files_parallel(
                self.batch_job.job_id,
                large_batch,
                folder_id,
                max_workers=3
            )
        
        # Clean up temporary files
        for file_info in large_batch:
            Path(file_info['path']).unlink(missing_ok=True)


class TestPreviewGeneration:
    """Test Google Slides API preview generation."""
    
    def setup_method(self):
        """Set up test environment."""
        self.mock_drive_service = Mock()
        self.mock_slides_service = Mock()
        self.test_db_path = tempfile.NamedTemporaryFile(suffix='.db').name
        
        from src.batch.models import init_database
        init_database(self.test_db_path)
        
        self.controller = BatchDriveController(
            drive_service=self.mock_drive_service,
            slides_service=self.mock_slides_service,
            db_path=self.test_db_path
        )
    
    def teardown_method(self):
        """Clean up after each test."""
        Path(self.test_db_path).unlink(missing_ok=True)
    
    def test_generate_batch_previews_success(self):
        """Test successful batch preview generation."""
        batch_job_id = "batch_preview_test"
        file_ids = ["1FILE_1_ID", "1FILE_2_ID"]
        
        # Mock Slides API responses
        preview_responses = [
            {
                'success': True,
                'fileId': '1FILE_1_ID',
                'previewUrl': 'https://drive.google.com/thumbnail?id=1FILE_1_ID',
                'thumbnailUrl': 'https://lh3.googleusercontent.com/thumbnail1'
            },
            {
                'success': True,
                'fileId': '1FILE_2_ID', 
                'previewUrl': 'https://drive.google.com/thumbnail?id=1FILE_2_ID',
                'thumbnailUrl': 'https://lh3.googleusercontent.com/thumbnail2'
            }
        ]
        
        self.mock_slides_service.generate_preview.side_effect = preview_responses
        
        results = self.controller.generate_batch_previews(batch_job_id, file_ids)
        
        assert len(results) == 2
        assert all(result.success for result in results)
        assert results[0].preview_url == 'https://drive.google.com/thumbnail?id=1FILE_1_ID'
        assert results[1].preview_url == 'https://drive.google.com/thumbnail?id=1FILE_2_ID'
    
    def test_generate_batch_previews_api_error(self):
        """Test handling Slides API errors during preview generation."""
        batch_job_id = "batch_preview_error"
        file_ids = ["1FILE_ERROR_ID"]
        
        self.mock_slides_service.generate_preview.side_effect = Exception("Slides API rate limit")
        
        results = self.controller.generate_batch_previews(batch_job_id, file_ids)
        
        assert len(results) == 1
        assert results[0].success is False
        assert "Slides API rate limit" in results[0].error_message


class TestErrorHandling:
    """Test comprehensive error handling scenarios."""
    
    def setup_method(self):
        """Set up test environment."""
        self.mock_drive_service = Mock()
        self.mock_slides_service = Mock()
        self.test_db_path = tempfile.NamedTemporaryFile(suffix='.db').name
        
        from src.batch.models import init_database
        init_database(self.test_db_path)
        
        self.controller = BatchDriveController(
            drive_service=self.mock_drive_service,
            slides_service=self.mock_slides_service,
            db_path=self.test_db_path
        )
    
    def teardown_method(self):
        """Clean up after each test."""
        Path(self.test_db_path).unlink(missing_ok=True)
    
    def test_drive_quota_exceeded_error(self):
        """Test handling Google Drive quota exceeded errors."""
        batch_job_id = "batch_quota_test"
        
        self.mock_drive_service.create_folder.side_effect = Exception(
            "The user's Drive quota has been exceeded"
        )
        
        with pytest.raises(BatchDriveError, match="Drive quota"):
            self.controller.create_batch_folder(batch_job_id)
    
    def test_authentication_error_handling(self):
        """Test handling authentication errors."""
        batch_job_id = "batch_auth_test"
        
        self.mock_drive_service.create_folder.side_effect = Exception(
            "Request had invalid authentication credentials"
        )
        
        with pytest.raises(BatchDriveError, match="authentication"):
            self.controller.create_batch_folder(batch_job_id)
    
    def test_network_timeout_recovery(self):
        """Test recovery from network timeouts."""
        batch_job_id = "batch_timeout_test"
        
        # Create required BatchJob first
        from src.batch.models import BatchJob
        batch_job = BatchJob(
            job_id=batch_job_id,
            status="processing",
            total_files=1,
            drive_integration_enabled=True
        )
        batch_job.save(self.test_db_path)
        
        # First attempt: first folder creation fails, second attempt: all 3 folders succeed
        self.mock_drive_service.create_folder.side_effect = [
            Exception("Request timeout"),  # First attempt, first folder fails
            # Second attempt: all 3 folders succeed
            {
                'success': True,
                'folderId': '1RETRY_ROOT_ID',
                'folderUrl': 'https://drive.google.com/drive/folders/1RETRY_ROOT_ID',
                'folderName': 'SVG2PPTX-Batches'
            },
            {
                'success': True,
                'folderId': '1RETRY_DATE_ID', 
                'folderUrl': 'https://drive.google.com/drive/folders/1RETRY_DATE_ID',
                'folderName': '2025-09-12'
            },
            {
                'success': True,
                'folderId': '1RETRY_BATCH_ID',
                'folderUrl': 'https://drive.google.com/drive/folders/1RETRY_BATCH_ID',
                'folderName': 'batch-batch_timeout_test'
            }
        ]
        
        result = self.controller.create_batch_folder_with_retry(
            batch_job_id, 
            max_retries=2
        )
        
        assert result.success is True
        assert result.folder_id == '1RETRY_BATCH_ID'  # Final batch folder ID


class TestIntegration:
    """Test complete batch Drive integration workflows."""
    
    def setup_method(self):
        """Set up test environment."""
        self.mock_drive_service = Mock()
        self.mock_slides_service = Mock()
        self.test_db_path = tempfile.NamedTemporaryFile(suffix='.db').name
        
        from src.batch.models import init_database
        init_database(self.test_db_path)
        
        self.controller = BatchDriveController(
            drive_service=self.mock_drive_service,
            slides_service=self.mock_slides_service,
            db_path=self.test_db_path
        )
    
    def teardown_method(self):
        """Clean up after each test."""
        Path(self.test_db_path).unlink(missing_ok=True)
    
    def test_complete_batch_drive_workflow(self):
        """Test complete end-to-end batch Drive workflow."""
        batch_job_id = "batch_e2e_test"
        
        # Create test batch job
        batch_job = BatchJob(
            job_id=batch_job_id,
            status="processing",
            total_files=2,
            drive_integration_enabled=True
        )
        batch_job.save(self.test_db_path)
        
        # Mock successful folder creation
        self.mock_drive_service.create_folder.return_value = {
            'success': True,
            'folderId': '1E2E_FOLDER_ID',
            'folderUrl': 'https://drive.google.com/drive/folders/1E2E_FOLDER_ID'
        }
        
        # Mock successful file uploads
        self.mock_drive_service.upload_file.side_effect = [
            {
                'success': True,
                'fileId': '1E2E_FILE_1_ID',
                'fileName': 'design_1.pptx',
                'shareableLink': 'https://docs.google.com/presentation/d/1E2E_FILE_1_ID'
            },
            {
                'success': True,
                'fileId': '1E2E_FILE_2_ID',
                'fileName': 'design_2.pptx',
                'shareableLink': 'https://docs.google.com/presentation/d/1E2E_FILE_2_ID'
            }
        ]
        
        # Mock successful preview generation
        self.mock_slides_service.generate_preview.side_effect = [
            {
                'success': True,
                'previewUrl': 'https://drive.google.com/thumbnail?id=1E2E_FILE_1_ID'
            },
            {
                'success': True,
                'previewUrl': 'https://drive.google.com/thumbnail?id=1E2E_FILE_2_ID'
            }
        ]
        
        # Create mock files
        test_files = [
            {'path': '/tmp/design_1.pptx', 'original_name': 'design_1.svg', 'converted_name': 'design_1.pptx'},
            {'path': '/tmp/design_2.pptx', 'original_name': 'design_2.svg', 'converted_name': 'design_2.pptx'}
        ]
        
        # Execute complete workflow
        result = self.controller.execute_complete_batch_workflow(
            batch_job_id,
            test_files
        )
        
        assert result.success is True
        assert result.folder_id == '1E2E_FOLDER_ID'
        assert len(result.uploaded_files) == 2
        assert len(result.generated_previews) == 2
        
        # Verify database state
        drive_metadata = BatchDriveMetadata.get_by_job_id(self.test_db_path, batch_job_id)
        assert drive_metadata.drive_folder_id == '1E2E_FOLDER_ID'
        
        file_metadata = BatchFileDriveMetadata.get_by_job_id(self.test_db_path, batch_job_id)
        assert len(file_metadata) == 2
        assert all(f.upload_status == "completed" for f in file_metadata)
        assert all(f.preview_url is not None for f in file_metadata)