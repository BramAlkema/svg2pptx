#!/usr/bin/env python3
"""
End-to-End tests for Batch Drive Integration.

Tests the complete batch workflow with Google Drive integration:
- Multi-file batch creation with Drive upload
- Folder organization and structure preservation  
- Preview generation pipeline
- Error handling and recovery scenarios
- Performance testing for large batches
"""

import pytest
import tempfile
import os
import json
import asyncio
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional, List
import httpx
from fastapi.testclient import TestClient

# Import the FastAPI app and dependencies
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from api.main import app
from api.auth import get_current_user
from api.config import get_settings
from src.batch.models import BatchJob, BatchDriveMetadata, BatchFileDriveMetadata, init_database


class BatchDriveE2EFixtures:
    """Shared fixtures and utilities for batch Drive E2E testing."""
    
    @pytest.fixture
    def client(self):
        """Create FastAPI test client with proper setup."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user for testing."""
        return {
            "user_id": "e2e_test_user",
            "email": "e2e@test.com",
            "name": "E2E Test User",
            "api_key": "e2e_test_key"
        }
    
    @pytest.fixture
    def test_db_path(self):
        """Create temporary database for E2E testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        # Initialize test database
        init_database(db_path)
        yield db_path
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def sample_svg_urls(self):
        """Sample SVG URLs for batch testing."""
        return [
            "https://example.com/icons/home.svg",
            "https://example.com/icons/user.svg", 
            "https://example.com/icons/settings.svg",
            "https://example.com/diagrams/workflow.svg",
            "https://example.com/logos/company.svg"
        ]
    
    @pytest.fixture
    def mock_drive_service(self):
        """Mock Google Drive service for E2E testing."""
        mock_service = Mock()
        
        # Mock folder creation
        mock_service.create_batch_folder.return_value = {
            'folder_id': 'test_batch_folder_123',
            'folder_url': 'https://drive.google.com/drive/folders/test_batch_folder_123'
        }
        
        # Mock file uploads
        def mock_upload(file_path, folder_id, filename):
            return {
                'file_id': f'file_{filename.replace(".", "_")}_{hash(file_path) % 10000}',
                'file_url': f'https://drive.google.com/file/d/file_{filename}_{hash(file_path) % 10000}/view',
                'download_url': f'https://drive.google.com/uc?id=file_{filename}_{hash(file_path) % 10000}'
            }
        
        mock_service.upload_file.side_effect = mock_upload
        
        # Mock preview generation
        mock_service.generate_preview.return_value = {
            'preview_url': 'https://drive.google.com/file/d/preview_123/view',
            'thumbnail_url': 'https://drive.google.com/thumbnail?id=preview_123'
        }
        
        return mock_service
    
    @pytest.fixture
    def mock_conversion_service(self):
        """Mock conversion service for E2E testing."""
        mock_service = Mock()
        
        def mock_convert(svg_url, output_path):
            # Simulate conversion by creating a dummy PPTX file
            with open(output_path, 'wb') as f:
                f.write(b'Mock PPTX content for ' + svg_url.encode())
            return True
        
        mock_service.convert_svg_to_pptx.side_effect = mock_convert
        return mock_service


class TestBatchDriveE2EInfrastructure(BatchDriveE2EFixtures):
    """Test the E2E infrastructure and basic batch Drive workflow."""
    
    def setup_method(self):
        """Set up test environment."""
        # Override auth dependency
        async def override_auth():
            return {
                'api_key': 'e2e_test_key', 
                'user_id': 'e2e_test_user'
            }
        
        app.dependency_overrides[get_current_user] = override_auth
    
    def teardown_method(self):
        """Clean up after tests."""
        app.dependency_overrides.clear()
    
    def test_e2e_infrastructure_setup(self, client, mock_user, test_db_path):
        """Test that E2E infrastructure is properly set up."""
        # Test client is available
        assert client is not None
        
        # Test user mock works
        assert mock_user["user_id"] == "e2e_test_user"
        
        # Test database is initialized
        assert os.path.exists(test_db_path)
        
        # Test API is accessible
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_batch_job_creation_e2e(self, client, sample_svg_urls, test_db_path):
        """Test end-to-end batch job creation."""
        # Patch database path
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            with patch('src.batch.drive_tasks.coordinate_batch_workflow') as mock_task:
                request_data = {
                    "urls": sample_svg_urls[:3],
                    "drive_integration_enabled": True,
                    "drive_folder_pattern": "E2E-Test-{job_id}",
                    "preprocessing_preset": "default",
                    "generate_previews": True
                }
                
                response = client.post("/batch/jobs", json=request_data)
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "job_id" in data
                assert data["total_files"] == 3
                assert data["drive_integration_enabled"] is True
                
                # Verify Huey task was scheduled
                mock_task.assert_called_once()
    
    def test_batch_status_tracking_e2e(self, client, sample_svg_urls, test_db_path):
        """Test end-to-end batch status tracking with Drive integration."""
        # Create a batch job first
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            with patch('src.batch.drive_tasks.coordinate_batch_workflow'):
                # Create job
                request_data = {
                    "urls": sample_svg_urls[:2],
                    "drive_integration_enabled": True
                }
                
                create_response = client.post("/batch/jobs", json=request_data)
                job_id = create_response.json()["job_id"]
                
                # Check status
                status_response = client.get(f"/batch/jobs/{job_id}")
                
                assert status_response.status_code == 200
                status_data = status_response.json()
                assert status_data["job_id"] == job_id
                assert status_data["drive_integration_enabled"] is True
                assert status_data["total_files"] == 2


class TestBatchDriveWorkflowValidation(BatchDriveE2EFixtures):
    """Validate core batch Drive workflows work end-to-end."""
    
    def setup_method(self):
        """Set up test environment."""
        async def override_auth():
            return {'api_key': 'e2e_test_key', 'user_id': 'e2e_test_user'}
        
        app.dependency_overrides[get_current_user] = override_auth
    
    def teardown_method(self):
        """Clean up after tests."""
        app.dependency_overrides.clear()
    
    def test_drive_upload_initiation_e2e(self, client, test_db_path):
        """Test Drive upload initiation workflow."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            # Create a completed batch job
            from src.batch.models import BatchJob
            job_id = "e2e_upload_test"
            batch_job = BatchJob(
                job_id=job_id,
                status="completed",
                total_files=2,
                drive_integration_enabled=False  # Will be enabled by upload request
            )
            batch_job.save(test_db_path)
            
            with patch('src.batch.drive_tasks.coordinate_upload_only_workflow') as mock_upload:
                request_data = {
                    "folder_pattern": "E2E-Test/{date}/{job_id}",
                    "generate_previews": True,
                    "parallel_uploads": True,
                    "max_workers": 3
                }
                
                response = client.post(f"/batch/jobs/{job_id}/upload-to-drive", json=request_data)
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["status"] == "uploading"
                
                # Verify upload task was scheduled
                mock_upload.assert_called_once()
    
    def test_drive_info_retrieval_e2e(self, client, test_db_path):
        """Test Drive information retrieval workflow."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            # Create batch with Drive metadata
            from src.batch.models import BatchJob, BatchDriveMetadata, BatchFileDriveMetadata
            
            job_id = "e2e_info_test"
            batch_job = BatchJob(
                job_id=job_id,
                status="completed",
                total_files=2,
                drive_integration_enabled=True
            )
            batch_job.save(test_db_path)
            
            # Add Drive metadata
            drive_metadata = BatchDriveMetadata(
                batch_job_id=job_id,
                drive_folder_id="test_folder_e2e",
                drive_folder_url="https://drive.google.com/drive/folders/test_folder_e2e"
            )
            drive_metadata.save(test_db_path)
            
            # Add file metadata
            file_metadata = BatchFileDriveMetadata(
                batch_job_id=job_id,
                original_filename="test.svg",
                drive_file_id="test_file_e2e",
                upload_status="completed"
            )
            file_metadata.save(test_db_path)
            
            # Test info retrieval
            response = client.get(f"/batch/jobs/{job_id}/drive-info")
            
            assert response.status_code == 200
            data = response.json()
            assert data["drive_folder_id"] == "test_folder_e2e"
            assert len(data["files"]) == 1
            assert data["files"][0]["original_filename"] == "test.svg"


class TestBatchDriveErrorScenarios(BatchDriveE2EFixtures):
    """Test error scenarios and recovery in batch Drive workflows."""
    
    def setup_method(self):
        """Set up test environment."""
        async def override_auth():
            return {'api_key': 'e2e_test_key', 'user_id': 'e2e_test_user'}
        
        app.dependency_overrides[get_current_user] = override_auth
    
    def teardown_method(self):
        """Clean up after tests."""
        app.dependency_overrides.clear()
    
    def test_job_not_found_error_e2e(self, client):
        """Test error handling for non-existent jobs."""
        response = client.get("/batch/jobs/nonexistent_job_e2e")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["message"]
    
    def test_upload_not_ready_error_e2e(self, client, test_db_path):
        """Test error handling for jobs not ready for upload."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            # Create a processing job
            from src.batch.models import BatchJob
            job_id = "e2e_not_ready"
            batch_job = BatchJob(
                job_id=job_id,
                status="processing",  # Not completed yet
                total_files=1,
                drive_integration_enabled=True
            )
            batch_job.save(test_db_path)
            
            request_data = {"folder_pattern": "test"}
            response = client.post(f"/batch/jobs/{job_id}/upload-to-drive", json=request_data)
            
            assert response.status_code == 400
            data = response.json()
            assert "not ready for upload" in data["message"]
    
    def test_drive_info_no_integration_error_e2e(self, client, test_db_path):
        """Test error handling for jobs without Drive integration."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            # Create job without Drive integration
            from src.batch.models import BatchJob
            job_id = "e2e_no_drive"
            batch_job = BatchJob(
                job_id=job_id,
                status="completed",
                total_files=1,
                drive_integration_enabled=False  # No Drive integration
            )
            batch_job.save(test_db_path)
            
            response = client.get(f"/batch/jobs/{job_id}/drive-info")
            
            assert response.status_code == 400
            data = response.json()
            assert "Drive integration is not enabled" in data["message"]


class TestBatchDrivePerformanceBaseline(BatchDriveE2EFixtures):
    """Baseline performance tests for batch Drive workflows."""
    
    def setup_method(self):
        """Set up test environment."""
        async def override_auth():
            return {'api_key': 'e2e_test_key', 'user_id': 'e2e_test_user'}
        
        app.dependency_overrides[get_current_user] = override_auth
    
    def teardown_method(self):
        """Clean up after tests."""
        app.dependency_overrides.clear()
    
    def test_batch_creation_performance_baseline(self, client, test_db_path):
        """Test batch job creation performance baseline."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            with patch('src.batch.drive_tasks.coordinate_batch_workflow'):
                # Generate URLs for medium batch
                urls = [f"https://example.com/test_{i}.svg" for i in range(10)]
                
                request_data = {
                    "urls": urls,
                    "drive_integration_enabled": True,
                    "preprocessing_preset": "default"
                }
                
                start_time = time.time()
                response = client.post("/batch/jobs", json=request_data)
                end_time = time.time()
                
                # Performance assertions
                assert response.status_code == 200
                response_time = end_time - start_time
                assert response_time < 2.0, f"Batch creation took {response_time:.2f}s, expected < 2.0s"
    
    def test_status_check_performance_baseline(self, client, test_db_path):
        """Test batch status check performance baseline."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            # Create a job first
            from src.batch.models import BatchJob
            job_id = "e2e_perf_test"
            batch_job = BatchJob(
                job_id=job_id,
                status="completed",
                total_files=10,
                drive_integration_enabled=True
            )
            batch_job.save(test_db_path)
            
            start_time = time.time()
            response = client.get(f"/batch/jobs/{job_id}")
            end_time = time.time()
            
            # Performance assertions
            assert response.status_code == 200
            response_time = end_time - start_time
            assert response_time < 0.5, f"Status check took {response_time:.2f}s, expected < 0.5s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])