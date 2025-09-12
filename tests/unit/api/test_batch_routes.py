#!/usr/bin/env python3
"""
Comprehensive tests for batch processing API routes.

Tests all batch endpoints including job creation, status monitoring,
Drive uploads, and error handling scenarios.
"""

import pytest
import tempfile
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from api.main import app
from src.batch.models import BatchJob, BatchDriveMetadata, BatchFileDriveMetadata


class TestBatchRoutes:
    """Test batch API routes with comprehensive coverage."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        # Mock authentication dependency override
        async def override_get_current_user():
            return {'api_key': 'test_key', 'user_id': 'test_user'}
        
        from api.auth import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        self.client = TestClient(app)
        self.test_db_path = tempfile.NamedTemporaryFile(suffix='.db').name
        
        # Setup test database
        from src.batch.models import init_database
        init_database(self.test_db_path)
        
        # Mock database path in models
        self.db_path_patcher = patch('src.batch.models.DEFAULT_DB_PATH', self.test_db_path)
        self.db_path_patcher.start()
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clean up dependency overrides
        app.dependency_overrides.clear()
        self.db_path_patcher.stop()
    
    def test_create_batch_job_success(self):
        """Test successful batch job creation."""
        request_data = {
            "urls": [
                "https://example.com/test1.svg",
                "https://example.com/test2.svg"
            ],
            "drive_integration_enabled": True,
            "preprocessing_preset": "default",
            "generate_previews": True
        }
        
        with patch('api.routes.batch.BackgroundTasks.add_task') as mock_bg_task:
            response = self.client.post("/batch/jobs", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "job_id" in data
        assert data["status"] == "created"
        assert data["total_files"] == 2
        assert data["drive_integration_enabled"] is True
        
        # Verify background task was added
        mock_bg_task.assert_called_once()
    
    def test_create_batch_job_invalid_urls(self):
        """Test batch job creation with invalid URLs."""
        request_data = {
            "urls": [
                "invalid-url",
                "https://example.com/test.svg"
            ]
        }
        
        response = self.client.post("/batch/jobs", json=request_data)
        
        assert response.status_code == 400
        response_data = response.json()
        # Check if it's the custom error format or direct detail
        if "detail" in response_data:
            assert "Invalid URL format" in response_data["detail"]
        elif "message" in response_data:
            assert "Invalid URL format" in response_data["message"]
        else:
            assert False, f"Unexpected error response format: {response_data}"
    
    def test_create_batch_job_empty_urls(self):
        """Test batch job creation with empty URL list."""
        request_data = {
            "urls": []
        }
        
        response = self.client.post("/batch/jobs", json=request_data)
        
        assert response.status_code == 422  # Validation error for min_items
    
    def test_create_batch_job_too_many_urls(self):
        """Test batch job creation with too many URLs."""
        request_data = {
            "urls": [f"https://example.com/test{i}.svg" for i in range(51)]
        }
        
        response = self.client.post("/batch/jobs", json=request_data)
        
        assert response.status_code == 422  # Validation error for max_items
    
    def test_get_batch_job_status_success(self):
        """Test successful batch job status retrieval."""
        # Create test job
        job_id = "test_job_123"
        batch_job = BatchJob(
            job_id=job_id,
            status="processing",
            total_files=3,
            drive_integration_enabled=True
        )
        batch_job.save(self.test_db_path)
        
        # Create Drive metadata
        drive_metadata = BatchDriveMetadata(
            batch_job_id=job_id,
            drive_folder_id="test_folder_id",
            drive_folder_url="https://drive.google.com/drive/folders/test_folder_id"
        )
        drive_metadata.save(self.test_db_path)
        
        # Create some file metadata
        file_metadata = BatchFileDriveMetadata(
            batch_job_id=job_id,
            original_filename="test.svg",
            drive_file_id="file_123",
            upload_status="completed"
        )
        file_metadata.save(self.test_db_path)
        
        response = self.client.get(f"/batch/jobs/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "processing"
        assert data["total_files"] == 3
        assert data["completed_files"] == 1
        assert data["drive_integration_enabled"] is True
        assert data["drive_folder_id"] == "test_folder_id"
    
    def test_get_batch_job_status_not_found(self):
        """Test batch job status for non-existent job."""
        response = self.client.get("/batch/jobs/non_existent_job")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_upload_batch_to_drive_success(self):
        """Test successful Drive upload initiation."""
        # Create test job
        job_id = "test_upload_job"
        batch_job = BatchJob(
            job_id=job_id,
            status="completed",
            total_files=2,
            drive_integration_enabled=False
        )
        batch_job.save(self.test_db_path)
        
        request_data = {
            "folder_pattern": "Custom/{date}/Test-{job_id}/",
            "generate_previews": True,
            "parallel_uploads": True,
            "max_workers": 5
        }
        
        with patch('api.routes.batch.BackgroundTasks.add_task') as mock_bg_task:
            response = self.client.post(f"/batch/jobs/{job_id}/upload-to-drive", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "uploading"
        
        # Verify background task was added
        mock_bg_task.assert_called_once()
        
        # Verify job was updated
        updated_job = BatchJob.get_by_id(job_id, self.test_db_path)
        assert updated_job.drive_integration_enabled is True
    
    def test_upload_batch_to_drive_job_not_ready(self):
        """Test Drive upload for job that's not ready."""
        # Create test job in wrong status
        job_id = "test_not_ready"
        batch_job = BatchJob(
            job_id=job_id,
            status="failed",
            total_files=1
        )
        batch_job.save(self.test_db_path)
        
        request_data = {"generate_previews": True}
        
        response = self.client.post(f"/batch/jobs/{job_id}/upload-to-drive", json=request_data)
        
        assert response.status_code == 400
        assert "not ready for upload" in response.json()["detail"]
    
    def test_upload_batch_to_drive_job_not_found(self):
        """Test Drive upload for non-existent job."""
        request_data = {"generate_previews": True}
        
        response = self.client.post("/batch/jobs/non_existent/upload-to-drive", json=request_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_get_batch_drive_info_success(self):
        """Test successful Drive info retrieval."""
        # Create test job with Drive integration
        job_id = "test_drive_info"
        batch_job = BatchJob(
            job_id=job_id,
            status="completed",
            total_files=2,
            drive_integration_enabled=True
        )
        batch_job.save(self.test_db_path)
        
        # Create Drive metadata
        drive_metadata = BatchDriveMetadata(
            batch_job_id=job_id,
            drive_folder_id="drive_folder_123",
            drive_folder_url="https://drive.google.com/drive/folders/drive_folder_123"
        )
        drive_metadata.save(self.test_db_path)
        
        # Create file metadata
        file_metadata1 = BatchFileDriveMetadata(
            batch_job_id=job_id,
            original_filename="file1.svg",
            drive_file_id="file_id_1",
            drive_file_url="https://drive.google.com/file/d/file_id_1/view",
            upload_status="completed",
            preview_url="https://drive.google.com/thumbnail?id=file_id_1"
        )
        file_metadata1.save(self.test_db_path)
        
        file_metadata2 = BatchFileDriveMetadata(
            batch_job_id=job_id,
            original_filename="file2.svg",
            drive_file_id="file_id_2",
            upload_status="failed",
            upload_error="Network timeout"
        )
        file_metadata2.save(self.test_db_path)
        
        response = self.client.get(f"/batch/jobs/{job_id}/drive-info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["drive_folder_id"] == "drive_folder_123"
        assert len(data["uploaded_files"]) == 1
        assert len(data["preview_urls"]) == 1
        assert data["upload_summary"]["successful_uploads"] == 1
        assert data["upload_summary"]["failed_uploads"] == 1
        assert data["upload_summary"]["success_rate"] == "50.0%"
    
    def test_get_batch_drive_info_no_drive_integration(self):
        """Test Drive info for job without Drive integration."""
        # Create test job without Drive integration
        job_id = "test_no_drive"
        batch_job = BatchJob(
            job_id=job_id,
            status="completed",
            total_files=1,
            drive_integration_enabled=False
        )
        batch_job.save(self.test_db_path)
        
        response = self.client.get(f"/batch/jobs/{job_id}/drive-info")
        
        assert response.status_code == 400
        assert "Drive integration is not enabled" in response.json()["detail"]
    
    def test_get_batch_drive_info_job_not_found(self):
        """Test Drive info for non-existent job."""
        response = self.client.get("/batch/jobs/non_existent/drive-info")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestBatchRouteValidation:
    """Test input validation for batch routes."""
    
    def setup_method(self):
        """Set up test environment."""
        # Mock authentication dependency override
        async def override_get_current_user():
            return {'api_key': 'test_key'}
        
        from api.auth import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        self.client = TestClient(app)
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clean up dependency overrides
        app.dependency_overrides.clear()
    
    def test_batch_job_create_validation(self):
        """Test various validation scenarios for batch job creation."""
        # Missing URLs
        response = self.client.post("/batch/jobs", json={})
        assert response.status_code == 422
        
        # Invalid URL scheme
        request_data = {"urls": ["ftp://example.com/test.svg"]}
        response = self.client.post("/batch/jobs", json=request_data)
        assert response.status_code == 400
        
        # Empty URL string
        request_data = {"urls": [""]}
        response = self.client.post("/batch/jobs", json=request_data)
        assert response.status_code == 400
        
        # Invalid preprocessing preset
        request_data = {
            "urls": ["https://example.com/test.svg"],
            "preprocessing_preset": "invalid_preset"
        }
        response = self.client.post("/batch/jobs", json=request_data)
        assert response.status_code == 200  # Should use default if invalid
    
    def test_drive_upload_request_validation(self):
        """Test validation for Drive upload requests."""
        # Invalid max_workers (too high)
        request_data = {"max_workers": 15}
        
        with patch('api.routes.batch.BatchJob.get_by_id') as mock_get_job:
            mock_job = Mock()
            mock_job.status = "completed"
            mock_get_job.return_value = mock_job
            
            response = self.client.post("/batch/jobs/test/upload-to-drive", json=request_data)
        
        assert response.status_code == 422  # Validation error
        
        # Invalid max_workers (too low)
        request_data = {"max_workers": 0}
        
        with patch('api.routes.batch.BatchJob.get_by_id') as mock_get_job:
            mock_job = Mock()
            mock_job.status = "completed"
            mock_get_job.return_value = mock_job
            
            response = self.client.post("/batch/jobs/test/upload-to-drive", json=request_data)
        
        assert response.status_code == 422  # Validation error


class TestBatchBackgroundTasks:
    """Test background task functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.test_db_path = tempfile.NamedTemporaryFile(suffix='.db').name
        
        # Setup test database
        from src.batch.models import init_database
        init_database(self.test_db_path)
    
    @pytest.mark.asyncio
    async def test_process_batch_job(self):
        """Test batch job processing background task."""
        from api.routes.batch import _process_batch_job
        
        job_id = "test_process_job"
        urls = ["https://example.com/test1.svg", "https://example.com/test2.svg"]
        
        # Create test job
        batch_job = BatchJob(
            job_id=job_id,
            status="created",
            total_files=len(urls)
        )
        batch_job.save(self.test_db_path)
        
        with patch('api.routes.batch.ConversionService') as mock_conversion:
            # Mock successful conversion
            mock_service = Mock()
            mock_service.convert_svg_to_pptx.return_value = {
                'success': True,
                'temp_pptx_path': '/tmp/test.pptx'
            }
            mock_conversion.return_value = mock_service
            
            await _process_batch_job(
                job_id=job_id,
                urls=urls,
                preprocessing_preset="default",
                drive_integration_enabled=False,
                drive_folder_pattern=None,
                generate_previews=True
            )
        
        # Verify job status was updated
        updated_job = BatchJob.get_by_id(job_id, self.test_db_path)
        assert updated_job.status == "completed"
    
    @pytest.mark.asyncio
    async def test_upload_batch_to_drive(self):
        """Test Drive upload background task."""
        from api.routes.batch import _upload_batch_to_drive
        
        job_id = "test_upload_task"
        
        # Create test job
        batch_job = BatchJob(
            job_id=job_id,
            status="processing",
            total_files=1
        )
        batch_job.save(self.test_db_path)
        
        with patch('api.routes.batch.BatchDriveController') as mock_controller:
            # Mock successful upload
            mock_drive_controller = Mock()
            mock_workflow_result = Mock()
            mock_workflow_result.success = True
            mock_drive_controller.execute_complete_batch_workflow.return_value = mock_workflow_result
            mock_controller.return_value = mock_drive_controller
            
            await _upload_batch_to_drive(
                job_id=job_id,
                folder_pattern=None,
                generate_previews=True,
                parallel_uploads=True,
                max_workers=3
            )
        
        # Verify job status was updated
        updated_job = BatchJob.get_by_id(job_id, self.test_db_path)
        assert updated_job.drive_upload_status == "completed"


class TestBatchErrorHandling:
    """Test error handling scenarios for batch routes."""
    
    def setup_method(self):
        """Set up test environment."""
        # Mock authentication dependency override
        async def override_get_current_user():
            return {'api_key': 'test_key'}
        
        from api.auth import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        self.client = TestClient(app)
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clean up dependency overrides
        app.dependency_overrides.clear()
    
    def test_database_error_handling(self):
        """Test handling of database errors."""
        with patch('api.routes.batch.BatchJob') as mock_batch_job:
            mock_batch_job.side_effect = Exception("Database connection error")
            
            request_data = {"urls": ["https://example.com/test.svg"]}
            response = self.client.post("/batch/jobs", json=request_data)
        
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]
    
    def test_conversion_service_error(self):
        """Test handling of conversion service errors."""
        with patch('api.routes.batch.ConversionService') as mock_service:
            mock_service.side_effect = Exception("Service initialization error")
            
            request_data = {"urls": ["https://example.com/test.svg"]}
            
            with patch('api.routes.batch.BackgroundTasks.add_task'):
                response = self.client.post("/batch/jobs", json=request_data)
        
        # Should still create job successfully (error handling is in background task)
        assert response.status_code == 200
    
    def test_drive_controller_error_handling(self):
        """Test handling of Drive controller errors."""
        with patch('api.routes.batch.BatchJob.get_by_id') as mock_get_job:
            mock_get_job.return_value = None  # Job not found
            
            request_data = {"generate_previews": True}
            response = self.client.post("/batch/jobs/invalid_job/upload-to-drive", json=request_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])