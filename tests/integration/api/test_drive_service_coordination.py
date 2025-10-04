#!/usr/bin/env python3
"""
Unit integration tests for Drive service coordination.

Tests the integration patterns between batch processing, database models,
Google Drive service, and Huey task coordination.
"""

import pytest
import tempfile
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import sqlite3

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.batch.models import BatchJob, BatchDriveMetadata, BatchFileDriveMetadata, init_database
from core.batch.drive_controller import BatchDriveController, DriveOperationResult, FileUploadResult, BatchWorkflowResult
from api.services.google_drive import GoogleDriveService, GoogleDriveError
from api.services.google_slides import GoogleSlidesService, GoogleSlidesError


class TestDriveServiceCoordination:
    """Test Drive service coordination patterns."""
    
    @pytest.fixture
    def test_db_path(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        init_database(db_path)
        yield db_path
        
        # Cleanup
        Path(db_path).unlink(missing_ok=True)
    
    @pytest.fixture
    def mock_drive_service(self):
        """Mock Google Drive service."""
        service = Mock(spec=GoogleDriveService)
        service.create_folder.return_value = {
            'success': True,
            'folderId': 'folder_123',
            'folderName': 'test-folder',
            'folderUrl': 'https://drive.google.com/drive/folders/folder_123'
        }
        service.upload_file.return_value = {
            'success': True,
            'fileId': 'file_456',
            'fileName': 'test-file.pptx',
            'fileUrl': 'https://drive.google.com/file/d/file_456/view',
            'downloadUrl': 'https://drive.google.com/uc?id=file_456'
        }
        return service
    
    @pytest.fixture
    def mock_slides_service(self):
        """Mock Google Slides service."""
        service = Mock(spec=GoogleSlidesService)
        service.generate_preview.return_value = {
            'presentationId': 'slides_789',
            'webViewLink': 'https://docs.google.com/presentation/d/slides_789/edit'
        }
        return service
    
    @pytest.fixture
    def drive_controller(self, mock_drive_service, mock_slides_service, test_db_path):
        """Create BatchDriveController with mocked services."""
        return BatchDriveController(
            drive_service=mock_drive_service,
            slides_service=mock_slides_service,
            db_path=test_db_path
        )
    
    def test_batch_job_drive_metadata_coordination(self, test_db_path):
        """Test coordination between BatchJob and BatchDriveMetadata."""
        # Create batch job
        job_id = "coord_test_001"
        batch_job = BatchJob(
            job_id=job_id,
            status="processing",
            total_files=3,
            drive_integration_enabled=True,
            drive_upload_status="pending"
        )
        batch_job.save(test_db_path)
        
        # Create Drive metadata
        drive_metadata = BatchDriveMetadata(
            batch_job_id=job_id,
            drive_folder_id="folder_coord_123",
            drive_folder_url="https://drive.google.com/drive/folders/folder_coord_123"
        )
        drive_metadata.save(test_db_path)
        
        # Verify coordination
        retrieved_job = BatchJob.get_by_id(test_db_path, job_id)
        assert retrieved_job.drive_integration_enabled is True
        
        retrieved_metadata = BatchDriveMetadata.get_by_job_id(test_db_path, job_id)
        assert retrieved_metadata.batch_job_id == job_id
        assert retrieved_metadata.drive_folder_id == "folder_coord_123"
    
    def test_batch_file_drive_metadata_coordination(self, test_db_path):
        """Test coordination between batch files and Drive metadata."""
        job_id = "file_coord_test"
        
        # Create batch job
        batch_job = BatchJob(
            job_id=job_id,
            status="uploading",
            total_files=2,
            drive_integration_enabled=True
        )
        batch_job.save(test_db_path)
        
        # Create file metadata for multiple files
        test_files = [
            ("file1.svg", "drive_file_001", "completed"),
            ("file2.svg", "drive_file_002", "uploading")
        ]
        
        for filename, file_id, status in test_files:
            file_metadata = BatchFileDriveMetadata(
                batch_job_id=job_id,
                original_filename=filename,
                drive_file_id=file_id,
                drive_file_url=f"https://drive.google.com/file/d/{file_id}/view",
                upload_status=status
            )
            file_metadata.save(test_db_path)
        
        # Verify coordination
        file_metadata_list = BatchFileDriveMetadata.get_by_job_id(test_db_path, job_id)
        assert len(file_metadata_list) == 2
        
        completed_files = [f for f in file_metadata_list if f.upload_status == "completed"]
        uploading_files = [f for f in file_metadata_list if f.upload_status == "uploading"]
        
        assert len(completed_files) == 1
        assert len(uploading_files) == 1
    
    def test_drive_controller_database_integration(self, drive_controller, mock_drive_service, test_db_path):
        """Test Drive controller integration with database operations."""
        job_id = "controller_db_test"
        
        # Create batch job
        batch_job = BatchJob(
            job_id=job_id,
            status="processing",
            total_files=1,
            drive_integration_enabled=True
        )
        batch_job.save(test_db_path)
        
        # Test folder creation with database persistence
        result = drive_controller.create_batch_folder(
            batch_job_id=job_id,
            folder_pattern="Test-Batches/test-{job_id}/"
        )
        
        assert result.success is True
        assert result.folder_id == "folder_123"  # This should be the batch_folder_id
        
        # Verify database was updated
        drive_metadata = BatchDriveMetadata.get_by_job_id(test_db_path, job_id)
        assert drive_metadata is not None
        assert drive_metadata.drive_folder_id == "folder_123"
    
    def test_file_upload_coordination_with_status_tracking(self, drive_controller, mock_drive_service, test_db_path):
        """Test file upload coordination with status tracking."""
        job_id = "upload_coord_test"
        
        # Setup batch job and Drive metadata
        batch_job = BatchJob(
            job_id=job_id,
            status="uploading",
            total_files=2,
            drive_integration_enabled=True
        )
        batch_job.save(test_db_path)
        
        drive_metadata = BatchDriveMetadata(
            batch_job_id=job_id,
            drive_folder_id="upload_folder_123"
        )
        drive_metadata.save(test_db_path)
        
        # Create temporary files for upload
        with tempfile.TemporaryDirectory() as temp_dir:
            file1_path = Path(temp_dir) / "test1.pptx"
            file2_path = Path(temp_dir) / "test2.pptx"
            
            file1_path.write_bytes(b"mock pptx content 1")
            file2_path.write_bytes(b"mock pptx content 2")
            
            files = [
                {"file_path": str(file1_path), "original_filename": "test1.svg"},
                {"file_path": str(file2_path), "original_filename": "test2.svg"}
            ]
            
            # Test coordinated upload
            with patch('src.batch.drive_controller.DEFAULT_DB_PATH', test_db_path):
                results = drive_controller.upload_batch_files(
                    batch_job_id=job_id,
                    files=files,
                    folder_id="upload_folder_123"
                )
                
                assert len(results) == 2
                assert all(r.success for r in results)
                
                # Verify database status tracking
                file_metadata_list = BatchFileDriveMetadata.get_by_job_id(test_db_path, job_id)
                assert len(file_metadata_list) == 2
                assert all(f.upload_status == "completed" for f in file_metadata_list)
    
    def test_error_recovery_coordination(self, drive_controller, mock_drive_service, test_db_path):
        """Test error recovery coordination between services and database."""
        job_id = "error_recovery_test"
        
        # Setup failing Drive service
        mock_drive_service.upload_file.side_effect = GoogleDriveError("Upload failed")
        
        # Create batch job
        batch_job = BatchJob(
            job_id=job_id,
            status="uploading",
            total_files=1,
            drive_integration_enabled=True
        )
        batch_job.save(test_db_path)
        
        drive_metadata = BatchDriveMetadata(
            batch_job_id=job_id,
            drive_folder_id="error_folder_123"
        )
        drive_metadata.save(test_db_path)
        
        # Test error handling and database coordination
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.pptx"
            file_path.write_bytes(b"mock content")
            
            with patch('src.batch.drive_controller.DEFAULT_DB_PATH', test_db_path):
                results = drive_controller.upload_batch_files(
                    batch_job_id=job_id,
                    files=[{"file_path": str(file_path), "original_filename": "test.svg"}],
                    folder_id="error_folder_123"
                )
                
                assert len(results) == 1
                assert results[0].success is False
                assert "Upload failed" in results[0].error_message
                
                # Verify error status in database
                file_metadata_list = BatchFileDriveMetadata.get_by_job_id(test_db_path, job_id)
                assert len(file_metadata_list) == 1
                assert file_metadata_list[0].upload_status == "failed"
                assert file_metadata_list[0].upload_error is not None
    
    def test_preview_generation_coordination(self, drive_controller, mock_slides_service, test_db_path):
        """Test preview generation coordination with database updates."""
        job_id = "preview_coord_test"
        
        # Setup batch job with uploaded files
        batch_job = BatchJob(
            job_id=job_id,
            status="generating_previews",
            total_files=1,
            drive_integration_enabled=True
        )
        batch_job.save(test_db_path)
        
        file_metadata = BatchFileDriveMetadata(
            batch_job_id=job_id,
            original_filename="test.svg",
            drive_file_id="file_preview_123",
            drive_file_url="https://drive.google.com/file/d/file_preview_123/view",
            upload_status="completed"
        )
        file_metadata.save(test_db_path)
        
        # Test preview generation
        with patch('src.batch.drive_controller.DEFAULT_DB_PATH', test_db_path):
            file_ids = ['file_preview_123']
            
            results = drive_controller.generate_batch_previews(
                batch_job_id=job_id,
                file_ids=file_ids
            )
            
            assert len(results) == 1
            assert results[0].success is True
            assert results[0].preview_url is not None
            
            # Verify database was updated with preview URL
            updated_metadata = BatchFileDriveMetadata.get_by_job_id(test_db_path, job_id)
            assert len(updated_metadata) == 1
            assert updated_metadata[0].preview_url is not None


class TestBatchWorkflowIntegration:
    """Test complete batch workflow integration."""
    
    @pytest.fixture
    def test_db_path(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        init_database(db_path)
        yield db_path
        
        Path(db_path).unlink(missing_ok=True)
    
    @pytest.fixture
    def mock_services(self):
        """Create all mocked services."""
        drive_service = Mock(spec=GoogleDriveService)
        slides_service = Mock(spec=GoogleSlidesService)
        
        # Setup successful responses
        drive_service.create_folder.return_value = {
            'success': True,
            'folderId': 'workflow_folder_123',
            'folderName': 'workflow-folder',
            'folderUrl': 'https://drive.google.com/drive/folders/workflow_folder_123'
        }
        
        drive_service.upload_file.return_value = {
            'success': True,
            'fileId': 'workflow_file_456',
            'fileName': 'workflow-file.pptx',
            'fileUrl': 'https://drive.google.com/file/d/workflow_file_456/view',
            'downloadUrl': 'https://drive.google.com/uc?id=workflow_file_456'
        }
        
        slides_service.generate_preview.return_value = {
            'presentationId': 'workflow_slides_789',
            'webViewLink': 'https://docs.google.com/presentation/d/workflow_slides_789/edit'
        }
        
        return drive_service, slides_service
    
    def test_complete_batch_workflow_integration(self, mock_services, test_db_path):
        """Test complete workflow from job creation to Drive upload completion."""
        drive_service, slides_service = mock_services
        controller = BatchDriveController(
            drive_service=drive_service,
            slides_service=slides_service
        )
        
        job_id = "complete_workflow_test"
        
        # Step 1: Create batch job
        batch_job = BatchJob(
            job_id=job_id,
            status="pending",
            total_files=2,
            drive_integration_enabled=True
        )
        batch_job.save(test_db_path)
        
        # Step 2: Create folder and update database
        with patch('src.batch.drive_controller.DEFAULT_DB_PATH', test_db_path):
            folder_result = controller.create_batch_folder(
                batch_job_id=job_id,
                folder_pattern="Complete-Test-{job_id}/"
            )
            
            assert folder_result.success is True
            
            # Step 3: Update job status to processing
            batch_job.status = "processing"
            batch_job.save(test_db_path)
            
            # Step 4: Upload files
            with tempfile.TemporaryDirectory() as temp_dir:
                file1_path = Path(temp_dir) / "file1.pptx"
                file2_path = Path(temp_dir) / "file2.pptx"
                
                file1_path.write_bytes(b"content 1")
                file2_path.write_bytes(b"content 2")
                
                files = [
                    {"file_path": str(file1_path), "original_filename": "file1.svg"},
                    {"file_path": str(file2_path), "original_filename": "file2.svg"}
                ]
                
                upload_results = controller.upload_batch_files(
                    batch_job_id=job_id,
                    files=files,
                    folder_id=folder_result.folder_id
                )
                
                assert len(upload_results) == 2
                assert all(r.success for r in upload_results)
                
                # Step 5: Generate previews
                file_ids = [r.file_id for r in upload_results]
                
                preview_results = controller.generate_batch_previews(
                    batch_job_id=job_id,
                    file_ids=file_ids
                )
                
                assert len(preview_results) == 2
                assert all(r.success for r in preview_results)
                
                # Step 6: Update job status to completed
                batch_job.status = "completed"
                batch_job.drive_upload_status = "completed"
                batch_job.save(test_db_path)
        
        # Verify complete workflow state
        final_job = BatchJob.get_by_id(test_db_path, job_id)
        assert final_job.status == "completed"
        assert final_job.drive_upload_status == "completed"
        
        drive_metadata = BatchDriveMetadata.get_by_job_id(test_db_path, job_id)
        assert drive_metadata.drive_folder_id == "workflow_folder_123"
        
        file_metadata_list = BatchFileDriveMetadata.get_by_job_id(test_db_path, job_id)
        assert len(file_metadata_list) == 2
        assert all(f.upload_status == "completed" for f in file_metadata_list)
        assert all(f.preview_url is not None for f in file_metadata_list)
    
    def test_workflow_state_transitions(self, test_db_path):
        """Test proper state transitions throughout workflow."""
        job_id = "state_transition_test"
        
        # Test state progression
        states = ["pending", "processing", "uploading", "generating_previews", "completed"]
        
        batch_job = BatchJob(
            job_id=job_id,
            status="pending",
            total_files=1,
            drive_integration_enabled=True
        )
        batch_job.save(test_db_path)
        
        for state in states:
            batch_job.status = state
            batch_job.save(test_db_path)
            
            retrieved_job = BatchJob.get_by_id(test_db_path, job_id)
            assert retrieved_job.status == state
            assert retrieved_job.updated_at > retrieved_job.created_at
    
    def test_workflow_rollback_on_failure(self, mock_services, test_db_path):
        """Test workflow rollback and cleanup on failure."""
        drive_service, slides_service = mock_services
        
        # Setup Drive service to fail on upload
        drive_service.upload_file.side_effect = GoogleDriveError("Network error")
        
        controller = BatchDriveController(
            drive_service=drive_service,
            slides_service=slides_service
        )
        
        job_id = "rollback_test"
        
        batch_job = BatchJob(
            job_id=job_id,
            status="uploading",
            total_files=1,
            drive_integration_enabled=True
        )
        batch_job.save(test_db_path)
        
        drive_metadata = BatchDriveMetadata(
            batch_job_id=job_id,
            drive_folder_id="rollback_folder_123"
        )
        drive_metadata.save(test_db_path)
        
        # Test failure handling
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.pptx"
            file_path.write_bytes(b"content")
            
            with patch('src.batch.drive_controller.DEFAULT_DB_PATH', test_db_path):
                results = controller.upload_batch_files(
                    batch_job_id=job_id,
                    files=[{"file_path": str(file_path), "original_filename": "test.svg"}],
                    folder_id="rollback_folder_123"
                )
                
                assert len(results) == 1
                assert results[0].success is False
                
                # Verify proper error state in database
                file_metadata = BatchFileDriveMetadata.get_by_job_id(test_db_path, job_id)
                assert len(file_metadata) == 1
                assert file_metadata[0].upload_status == "failed"
                assert "Network error" in file_metadata[0].upload_error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])