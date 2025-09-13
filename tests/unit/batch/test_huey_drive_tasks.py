#!/usr/bin/env python3
"""
Comprehensive tests for Huey async Drive upload tasks and job coordination.

Tests all aspects of asynchronous Google Drive upload functionality including
task execution, error recovery, status tracking, and coordination with batch jobs.
"""

import pytest
import tempfile
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock, call
from pathlib import Path

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.batch.huey_app import huey
from src.batch.models import BatchJob, BatchDriveMetadata, BatchFileDriveMetadata


class TestHueyDriveTaskExecution:
    """Test basic Huey task execution for Drive uploads."""
    
    def setup_method(self):
        """Set up test environment."""
        self.test_db_path = tempfile.NamedTemporaryFile(suffix='.db').name
        
        # Setup test database
        from src.batch.models import init_database
        init_database(self.test_db_path)
        
        # Mock database path in models
        self.db_path_patcher = patch('src.batch.models.DEFAULT_DB_PATH', self.test_db_path)
        self.db_path_patcher.start()
        
        # Use immediate mode for testing
        self.immediate_patcher = patch.object(huey, 'immediate', True)
        self.immediate_patcher.start()
    
    def teardown_method(self):
        """Clean up after each test."""
        self.db_path_patcher.stop()
        self.immediate_patcher.stop()
    
    def test_huey_app_configuration(self):
        """Test Huey app is properly configured."""
        assert huey.name == 'svg2pptx'
        assert huey.results is True
        assert huey.store_none is False
        assert huey.utc is True
    
    def test_task_decorator_registration(self):
        """Test that task decorators register properly."""
        from src.batch.drive_tasks import upload_batch_files_to_drive
        
        # Task should be registered in Huey
        assert 'upload_batch_files_to_drive' in huey._registry
        
        # Task should be callable
        assert callable(upload_batch_files_to_drive)
    
    def test_task_execution_immediate_mode(self):
        """Test task execution in immediate mode."""
        from src.batch.drive_tasks import test_drive_connection
        
        # Execute task immediately (synchronous)
        result = test_drive_connection()
        
        # Should return result directly in immediate mode
        assert isinstance(result, dict)
        assert 'status' in result


class TestDriveUploadTasks:
    """Test Google Drive upload task implementations."""
    
    def setup_method(self):
        """Set up test environment."""
        self.test_db_path = tempfile.NamedTemporaryFile(suffix='.db').name
        
        # Setup test database
        from src.batch.models import init_database
        init_database(self.test_db_path)
        
        # Mock database path
        self.db_path_patcher = patch('src.batch.models.DEFAULT_DB_PATH', self.test_db_path)
        self.db_path_patcher.start()
        
        # Mock Drive services
        self.drive_patcher = patch('src.batch.drive_tasks.BatchDriveController')
        self.mock_drive_controller = self.drive_patcher.start()
        
        # Mock immediate mode
        self.immediate_patcher = patch.object(huey, 'immediate', True)
        self.immediate_patcher.start()
    
    def teardown_method(self):
        """Clean up after each test."""
        self.db_path_patcher.stop()
        self.drive_patcher.stop()
        self.immediate_patcher.stop()
    
    def test_upload_batch_files_to_drive_success(self):
        """Test successful batch file upload to Drive."""
        from src.batch.drive_tasks import upload_batch_files_to_drive
        
        # Create test job
        job_id = "test_batch_upload"
        batch_job = BatchJob(
            job_id=job_id,
            status="processing",
            total_files=2,
            drive_integration_enabled=True
        )
        batch_job.save(self.test_db_path)
        
        # Mock successful Drive workflow
        mock_controller_instance = Mock()
        mock_workflow_result = Mock()
        mock_workflow_result.success = True
        mock_workflow_result.folder_id = "test_folder_123"
        mock_workflow_result.uploaded_files = [
            Mock(success=True, file_id="file_1", original_filename="test1.pptx"),
            Mock(success=True, file_id="file_2", original_filename="test2.pptx")
        ]
        
        mock_controller_instance.execute_complete_batch_workflow.return_value = mock_workflow_result
        self.mock_drive_controller.return_value = mock_controller_instance
        
        # Execute task
        files = [
            {'path': '/tmp/test1.pptx', 'original_name': 'test1.svg', 'converted_name': 'test1.pptx'},
            {'path': '/tmp/test2.pptx', 'original_name': 'test2.svg', 'converted_name': 'test2.pptx'}
        ]
        
        result = upload_batch_files_to_drive(job_id, files, None, True)
        
        # Verify result
        assert result['success'] is True
        assert result['folder_id'] == "test_folder_123"
        assert result['uploaded_files'] == 2
        assert result['failed_files'] == 0
        
        # Verify Drive controller was called
        mock_controller_instance.execute_complete_batch_workflow.assert_called_once()
    
    def test_upload_batch_files_partial_failure(self):
        """Test batch upload with partial file failures."""
        from src.batch.drive_tasks import upload_batch_files_to_drive
        
        # Create test job
        job_id = "test_partial_fail"
        batch_job = BatchJob(
            job_id=job_id,
            status="processing",
            total_files=3,
            drive_integration_enabled=True
        )
        batch_job.save(self.test_db_path)
        
        # Mock partial failure workflow
        mock_controller_instance = Mock()
        mock_workflow_result = Mock()
        mock_workflow_result.success = True
        mock_workflow_result.folder_id = "test_folder_456"
        mock_workflow_result.uploaded_files = [
            Mock(success=True, file_id="file_1", original_filename="test1.pptx"),
            Mock(success=False, error_message="Network timeout", original_filename="test2.pptx"),
            Mock(success=True, file_id="file_3", original_filename="test3.pptx")
        ]
        
        mock_controller_instance.execute_complete_batch_workflow.return_value = mock_workflow_result
        self.mock_drive_controller.return_value = mock_controller_instance
        
        # Execute task
        files = [
            {'path': '/tmp/test1.pptx', 'original_name': 'test1.svg', 'converted_name': 'test1.pptx'},
            {'path': '/tmp/test2.pptx', 'original_name': 'test2.svg', 'converted_name': 'test2.pptx'},
            {'path': '/tmp/test3.pptx', 'original_name': 'test3.svg', 'converted_name': 'test3.pptx'}
        ]
        
        result = upload_batch_files_to_drive(job_id, files, None, True)
        
        # Verify result
        assert result['success'] is True
        assert result['uploaded_files'] == 2
        assert result['failed_files'] == 1
        assert len(result['errors']) == 1
        assert "Network timeout" in result['errors'][0]
    
    def test_upload_batch_drive_integration_disabled(self):
        """Test batch upload when Drive integration is disabled."""
        from src.batch.drive_tasks import upload_batch_files_to_drive
        
        # Create test job without Drive integration
        job_id = "test_no_drive"
        batch_job = BatchJob(
            job_id=job_id,
            status="processing",
            total_files=1,
            drive_integration_enabled=False
        )
        batch_job.save(self.test_db_path)
        
        # Execute task
        files = [{'path': '/tmp/test.pptx', 'original_name': 'test.svg', 'converted_name': 'test.pptx'}]
        
        result = upload_batch_files_to_drive(job_id, files, None, True)
        
        # Verify result
        assert result['success'] is False
        assert 'Drive integration is not enabled' in result['error_message']
        
        # Drive controller should not be called
        self.mock_drive_controller.assert_not_called()
    
    def test_create_batch_drive_folder_success(self):
        """Test Drive folder creation task."""
        from src.batch.drive_tasks import create_batch_drive_folder
        
        # Create test job
        job_id = "test_folder_creation"
        batch_job = BatchJob(
            job_id=job_id,
            status="processing",
            total_files=1,
            drive_integration_enabled=True
        )
        batch_job.save(self.test_db_path)
        
        # Mock successful folder creation
        mock_controller_instance = Mock()
        mock_folder_result = Mock()
        mock_folder_result.success = True
        mock_folder_result.folder_id = "created_folder_123"
        mock_folder_result.folder_url = "https://drive.google.com/drive/folders/created_folder_123"
        
        mock_controller_instance.create_batch_folder.return_value = mock_folder_result
        self.mock_drive_controller.return_value = mock_controller_instance
        
        # Execute task
        result = create_batch_drive_folder(job_id, None)
        
        # Verify result
        assert result['success'] is True
        assert result['folder_id'] == "created_folder_123"
        assert result['folder_url'] == "https://drive.google.com/drive/folders/created_folder_123"
        
        # Verify Drive controller was called
        mock_controller_instance.create_batch_folder.assert_called_once_with(job_id, None)
    
    def test_generate_batch_previews_success(self):
        """Test preview generation task."""
        from src.batch.drive_tasks import generate_batch_previews
        
        # Create test job
        job_id = "test_preview_gen"
        batch_job = BatchJob(
            job_id=job_id,
            status="processing",
            total_files=2,
            drive_integration_enabled=True
        )
        batch_job.save(self.test_db_path)
        
        # Mock successful preview generation
        mock_controller_instance = Mock()
        mock_preview_results = [
            Mock(success=True, file_id="file_1", preview_url="https://drive.google.com/thumbnail?id=file_1"),
            Mock(success=True, file_id="file_2", preview_url="https://drive.google.com/thumbnail?id=file_2")
        ]
        
        mock_controller_instance.generate_batch_previews.return_value = mock_preview_results
        self.mock_drive_controller.return_value = mock_controller_instance
        
        # Execute task
        file_ids = ["file_1", "file_2"]
        result = generate_batch_previews(job_id, file_ids)
        
        # Verify result
        assert result['success'] is True
        assert result['generated_previews'] == 2
        assert result['failed_previews'] == 0
        assert len(result['preview_urls']) == 2
        
        # Verify Drive controller was called
        mock_controller_instance.generate_batch_previews.assert_called_once_with(job_id, file_ids)


class TestJobCoordination:
    """Test coordination between Drive tasks and batch jobs."""
    
    def setup_method(self):
        """Set up test environment."""
        self.test_db_path = tempfile.NamedTemporaryFile(suffix='.db').name
        
        # Setup test database
        from src.batch.models import init_database
        init_database(self.test_db_path)
        
        # Mock database path
        self.db_path_patcher = patch('src.batch.models.DEFAULT_DB_PATH', self.test_db_path)
        self.db_path_patcher.start()
        
        # Mock immediate mode
        self.immediate_patcher = patch.object(huey, 'immediate', True)
        self.immediate_patcher.start()
    
    def teardown_method(self):
        """Clean up after each test."""
        self.db_path_patcher.stop()
        self.immediate_patcher.stop()
    
    def test_coordinate_batch_conversion_and_upload(self):
        """Test coordination between conversion and Drive upload tasks."""
        from src.batch.drive_tasks import coordinate_batch_workflow
        
        # Create test job
        job_id = "test_coordination"
        batch_job = BatchJob(
            job_id=job_id,
            status="created",
            total_files=2,
            drive_integration_enabled=True
        )
        batch_job.save(self.test_db_path)
        
        with patch('src.batch.drive_tasks.convert_svg_batch') as mock_convert, \
             patch('src.batch.drive_tasks.upload_batch_files_to_drive') as mock_upload:
            
            # Mock conversion results
            mock_convert.return_value = {
                'success': True,
                'converted_files': [
                    {'path': '/tmp/file1.pptx', 'original_name': 'file1.svg', 'converted_name': 'file1.pptx'},
                    {'path': '/tmp/file2.pptx', 'original_name': 'file2.svg', 'converted_name': 'file2.pptx'}
                ]
            }
            
            # Mock upload results
            mock_upload.return_value = {
                'success': True,
                'uploaded_files': 2,
                'failed_files': 0
            }
            
            # Execute coordination task
            svg_urls = ["https://example.com/file1.svg", "https://example.com/file2.svg"]
            result = coordinate_batch_workflow(job_id, svg_urls, {'preprocessing': 'default'})
            
            # Verify result
            assert result['success'] is True
            assert result['conversion_success'] is True
            assert result['upload_success'] is True
            
            # Verify both tasks were called
            mock_convert.assert_called_once()
            mock_upload.assert_called_once()
    
    def test_coordinate_conversion_failure_skips_upload(self):
        """Test that upload is skipped if conversion fails."""
        from src.batch.drive_tasks import coordinate_batch_workflow
        
        # Create test job
        job_id = "test_conversion_fail"
        batch_job = BatchJob(
            job_id=job_id,
            status="created",
            total_files=1,
            drive_integration_enabled=True
        )
        batch_job.save(self.test_db_path)
        
        with patch('src.batch.drive_tasks.convert_svg_batch') as mock_convert, \
             patch('src.batch.drive_tasks.upload_batch_files_to_drive') as mock_upload:
            
            # Mock conversion failure
            mock_convert.return_value = {
                'success': False,
                'error_message': 'Invalid SVG format'
            }
            
            # Execute coordination task
            svg_urls = ["https://example.com/invalid.svg"]
            result = coordinate_batch_workflow(job_id, svg_urls, {})
            
            # Verify result
            assert result['success'] is False
            assert result['conversion_success'] is False
            assert 'upload_success' not in result
            
            # Verify conversion was called but upload was not
            mock_convert.assert_called_once()
            mock_upload.assert_not_called()
    
    def test_coordinate_upload_only_workflow(self):
        """Test coordination for upload-only workflow (files already converted)."""
        from src.batch.drive_tasks import coordinate_upload_only_workflow
        
        # Create test job
        job_id = "test_upload_only"
        batch_job = BatchJob(
            job_id=job_id,
            status="processing",
            total_files=2,
            drive_integration_enabled=True
        )
        batch_job.save(self.test_db_path)
        
        with patch('src.batch.drive_tasks.upload_batch_files_to_drive') as mock_upload:
            
            # Mock successful upload
            mock_upload.return_value = {
                'success': True,
                'uploaded_files': 2,
                'failed_files': 0
            }
            
            # Execute upload-only task
            converted_files = [
                {'path': '/tmp/file1.pptx', 'original_name': 'file1.svg', 'converted_name': 'file1.pptx'},
                {'path': '/tmp/file2.pptx', 'original_name': 'file2.svg', 'converted_name': 'file2.pptx'}
            ]
            
            result = coordinate_upload_only_workflow(job_id, converted_files, None, True)
            
            # Verify result
            assert result['success'] is True
            assert result['upload_success'] is True
            
            # Verify upload was called
            mock_upload.assert_called_once_with(job_id, converted_files, None, True)


class TestTaskStatusTracking:
    """Test status tracking and progress monitoring for Drive tasks."""
    
    def setup_method(self):
        """Set up test environment."""
        self.test_db_path = tempfile.NamedTemporaryFile(suffix='.db').name
        
        # Setup test database
        from src.batch.models import init_database
        init_database(self.test_db_path)
        
        # Mock database path
        self.db_path_patcher = patch('src.batch.models.DEFAULT_DB_PATH', self.test_db_path)
        self.db_path_patcher.start()
    
    def teardown_method(self):
        """Clean up after each test."""
        self.db_path_patcher.stop()
    
    def test_update_job_status_during_upload(self):
        """Test that job status is updated during upload process."""
        from src.batch.drive_tasks import update_batch_job_status
        
        # Create test job
        job_id = "test_status_update"
        batch_job = BatchJob(
            job_id=job_id,
            status="processing",
            total_files=1,
            drive_integration_enabled=True
        )
        batch_job.save(self.test_db_path)
        
        # Update status
        result = update_batch_job_status(job_id, "uploading", drive_upload_status="in_progress")
        
        # Verify result
        assert result['success'] is True
        
        # Verify job was updated
        updated_job = BatchJob.get_by_id(job_id, self.test_db_path)
        assert updated_job.status == "uploading"
        assert updated_job.drive_upload_status == "in_progress"
    
    def test_track_upload_progress(self):
        """Test upload progress tracking."""
        from src.batch.drive_tasks import track_upload_progress
        
        # Create test job
        job_id = "test_progress_track"
        batch_job = BatchJob(
            job_id=job_id,
            status="uploading",
            total_files=3,
            drive_integration_enabled=True
        )
        batch_job.save(self.test_db_path)
        
        # Create file metadata
        for i in range(3):
            file_meta = BatchFileDriveMetadata(
                batch_job_id=job_id,
                original_filename=f"test{i+1}.svg",
                drive_file_id=f"file_{i+1}" if i < 2 else None,  # First 2 uploaded
                upload_status="completed" if i < 2 else "pending"
            )
            file_meta.save(self.test_db_path)
        
        # Get progress
        progress = track_upload_progress(job_id)
        
        # Verify progress
        assert progress['total_files'] == 3
        assert progress['uploaded_files'] == 2
        assert progress['pending_files'] == 1
        assert progress['progress_percentage'] == 66.67
    
    def test_get_task_execution_status(self):
        """Test getting task execution status."""
        from src.batch.drive_tasks import get_task_status
        
        # This would typically check Huey task status
        # In immediate mode, tasks complete immediately
        task_id = "test_task_123"
        
        status = get_task_status(task_id)
        
        # In immediate mode, status checking isn't as relevant
        # But we should have a mechanism to check task status
        assert isinstance(status, dict)
        assert 'status' in status


class TestErrorHandling:
    """Test error handling in Drive tasks."""
    
    def setup_method(self):
        """Set up test environment."""
        self.test_db_path = tempfile.NamedTemporaryFile(suffix='.db').name
        
        # Setup test database
        from src.batch.models import init_database
        init_database(self.test_db_path)
        
        # Mock database path
        self.db_path_patcher = patch('src.batch.models.DEFAULT_DB_PATH', self.test_db_path)
        self.db_path_patcher.start()
        
        # Mock immediate mode
        self.immediate_patcher = patch.object(huey, 'immediate', True)
        self.immediate_patcher.start()
    
    def teardown_method(self):
        """Clean up after each test."""
        self.db_path_patcher.stop()
        self.immediate_patcher.stop()
    
    def test_handle_drive_service_error(self):
        """Test handling of Drive service errors."""
        from src.batch.drive_tasks import upload_batch_files_to_drive
        
        # Create test job
        job_id = "test_service_error"
        batch_job = BatchJob(
            job_id=job_id,
            status="processing",
            total_files=1,
            drive_integration_enabled=True
        )
        batch_job.save(self.test_db_path)
        
        with patch('src.batch.drive_tasks.BatchDriveController') as mock_controller:
            # Mock Drive service error
            mock_controller.side_effect = Exception("Drive API quota exceeded")
            
            # Execute task
            files = [{'path': '/tmp/test.pptx', 'original_name': 'test.svg', 'converted_name': 'test.pptx'}]
            result = upload_batch_files_to_drive(job_id, files, None, True)
            
            # Verify error handling
            assert result['success'] is False
            assert "Drive API quota exceeded" in result['error_message']
            assert result['error_type'] == 'drive_service_error'
    
    def test_handle_authentication_error(self):
        """Test handling of authentication errors."""
        from src.batch.drive_tasks import test_drive_connection
        
        with patch('src.batch.drive_tasks.GoogleDriveService') as mock_service:
            # Mock authentication error
            from api.services.google_drive import GoogleDriveError
            mock_service.side_effect = GoogleDriveError("Authentication failed", 401)
            
            # Execute task
            result = test_drive_connection()
            
            # Verify error handling
            assert result['success'] is False
            assert result['error_type'] == 'authentication_error'
            assert result['error_code'] == 401
    
    def test_handle_network_timeout_error(self):
        """Test handling of network timeout errors."""
        from src.batch.drive_tasks import upload_batch_files_to_drive
        
        # Create test job
        job_id = "test_network_error"
        batch_job = BatchJob(
            job_id=job_id,
            status="processing",
            total_files=1,
            drive_integration_enabled=True
        )
        batch_job.save(self.test_db_path)
        
        with patch('src.batch.drive_tasks.BatchDriveController') as mock_controller:
            # Mock network timeout
            import requests
            mock_controller.side_effect = requests.exceptions.Timeout("Request timeout")
            
            # Execute task
            files = [{'path': '/tmp/test.pptx', 'original_name': 'test.svg', 'converted_name': 'test.pptx'}]
            result = upload_batch_files_to_drive(job_id, files, None, True)
            
            # Verify error handling
            assert result['success'] is False
            assert result['error_type'] == 'network_error'
            assert "Request timeout" in result['error_message']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])