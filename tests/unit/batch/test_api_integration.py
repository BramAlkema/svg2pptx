#!/usr/bin/env python3
"""
Tests for integrated batch API with dual-mode functionality.
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
import tempfile
import zipfile
import os
from pathlib import Path
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Configure Huey for testing (immediate mode)
os.environ['HUEY_IMMEDIATE'] = 'true'

from src.batch.api import create_batch_router


@pytest.fixture
def sample_svg_content():
    """Sample SVG content for testing."""
    return b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>'


@pytest.fixture
def batch_app():
    """Create FastAPI app with batch router for testing."""
    app = FastAPI()
    app.include_router(create_batch_router())
    return app


@pytest.fixture
def client(batch_app):
    """Create test client."""
    return TestClient(batch_app)


class TestBatchModeEndpoints:
    """Test batch mode endpoints (Huey-based processing)."""
    
    def test_convert_files_batch_mode(self, client, sample_svg_content):
        """Test batch mode convert files endpoint."""
        files = [
            ("files", ("test1.svg", sample_svg_content, "image/svg+xml")),
            ("files", ("test2.svg", sample_svg_content, "image/svg+xml"))
        ]
        
        data = {
            "slide_width": 10.0,
            "slide_height": 7.5,
            "output_format": "single_pptx",
            "quality": "high"
        }
        
        response = client.post("/batch/convert-files", files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "PENDING"
        assert result["total_files"] == 2
        assert "batch_id" in result
        assert result["message"] == "Batch processing started"
    
    def test_convert_zip_batch_mode(self, client, sample_svg_content):
        """Test batch mode convert ZIP endpoint."""
        # Create a ZIP file with SVG content
        with tempfile.NamedTemporaryFile(suffix='.zip') as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w') as zip_file:
                zip_file.writestr('file1.svg', sample_svg_content)
                zip_file.writestr('file2.svg', sample_svg_content)
            
            temp_zip.seek(0)
            zip_content = temp_zip.read()
        
        files = [("zip_file", ("test.zip", zip_content, "application/zip"))]
        data = {"output_format": "zip_archive"}
        
        response = client.post("/batch/convert-zip", files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "PENDING"
        assert result["message"] == "ZIP processing started"
        assert "batch_id" in result
    
    @patch('src.batch.api.huey')
    def test_status_endpoint_batch_mode(self, mock_huey, client):
        """Test batch mode status endpoint."""
        # Mock Huey task
        mock_task = Mock()
        mock_task.is_complete.return_value = True
        mock_task.is_revoked.return_value = False
        mock_task.return_value = {
            'success': True,
            'individual_results': [
                {'success': True},
                {'success': True}
            ]
        }
        mock_huey.get.return_value = mock_task
        
        batch_id = "test-batch-123"
        response = client.get(f"/batch/status/{batch_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert result["batch_id"] == batch_id
        assert result["status"] == "SUCCESS"
        assert result["progress"] == 100.0
        assert result["completed_files"] == 2
        assert result["failed_files"] == 0
    
    @patch('src.batch.api.huey')
    def test_status_endpoint_not_found(self, mock_huey, client):
        """Test batch mode status endpoint with non-existent job."""
        mock_huey.get.return_value = None
        
        batch_id = "nonexistent-batch"
        response = client.get(f"/batch/status/{batch_id}")
        
        assert response.status_code == 404
        assert "Batch job not found" in response.json()["detail"]
    
    @patch('src.batch.api.huey')
    def test_status_endpoint_pending(self, mock_huey, client):
        """Test batch mode status endpoint with pending job."""
        mock_task = Mock()
        mock_task.is_complete.return_value = False
        mock_task.is_revoked.return_value = False
        mock_huey.get.return_value = mock_task
        
        batch_id = "pending-batch"
        response = client.get(f"/batch/status/{batch_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "PENDING"
        assert result["progress"] == 0.0
        assert result["current_step"] == "processing"
    
    @patch('src.batch.api.huey')
    def test_status_endpoint_failed(self, mock_huey, client):
        """Test batch mode status endpoint with failed job."""
        mock_task = Mock()
        mock_task.is_complete.return_value = True
        mock_task.is_revoked.return_value = False
        mock_task.return_value = {
            'success': False,
            'error_message': 'Test error'
        }
        mock_huey.get.return_value = mock_task
        
        batch_id = "failed-batch"
        response = client.get(f"/batch/status/{batch_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "FAILURE"
        assert result["error_message"] == "Test error"
    
    @patch('src.batch.api.huey')
    def test_download_endpoint_batch_mode(self, mock_huey, client):
        """Test batch mode download endpoint."""
        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
            temp_file.write(b"mock pptx content")
            temp_path = temp_file.name
        
        try:
            mock_task = Mock()
            mock_task.is_complete.return_value = True
            mock_task.return_value = {
                'success': True,
                'output_path': temp_path,
                'individual_results': []
            }
            mock_huey.get.return_value = mock_task
            
            batch_id = "test-batch-download"
            response = client.get(f"/batch/download/{batch_id}")
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @patch('src.batch.api.huey')
    def test_download_endpoint_not_complete(self, mock_huey, client):
        """Test batch mode download endpoint with incomplete job."""
        mock_task = Mock()
        mock_task.is_complete.return_value = False
        mock_huey.get.return_value = mock_task
        
        batch_id = "incomplete-batch"
        response = client.get(f"/batch/download/{batch_id}")
        
        assert response.status_code == 400
        assert "Batch job not completed yet" in response.json()["detail"]
    
    @patch('src.batch.api.huey')
    def test_cancel_endpoint_batch_mode(self, mock_huey, client):
        """Test batch mode cancel endpoint."""
        mock_task = Mock()
        mock_task.is_complete.return_value = False
        mock_task.revoke = Mock()
        mock_huey.get.return_value = mock_task
        
        batch_id = "test-batch-cancel"
        response = client.delete(f"/batch/cancel/{batch_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert "cancelled" in result["message"]
        mock_task.revoke.assert_called_once()
    
    @patch('src.batch.api.huey')
    def test_cancel_endpoint_already_complete(self, mock_huey, client):
        """Test batch mode cancel endpoint with already completed job."""
        mock_task = Mock()
        mock_task.is_complete.return_value = True
        mock_huey.get.return_value = mock_task
        
        batch_id = "completed-batch"
        response = client.delete(f"/batch/cancel/{batch_id}")
        
        assert response.status_code == 400
        assert "Cannot cancel completed job" in response.json()["detail"]


class TestSimpleModeEndpoints:
    """Test simple mode endpoints (synchronous processing)."""
    
    def test_convert_files_simple_mode(self, client, sample_svg_content):
        """Test simple mode convert files endpoint."""
        files = [
            ("files", ("test1.svg", sample_svg_content, "image/svg+xml")),
            ("files", ("test2.svg", sample_svg_content, "image/svg+xml"))
        ]
        
        data = {
            "slide_width": 10.0,
            "slide_height": 7.5,
            "output_format": "single_pptx",
            "quality": "high"
        }
        
        response = client.post("/batch/simple/convert-files", files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "completed"
        assert result["total_files"] == 2
        assert result["mode"] == "simple"
        assert "job_id" in result
        assert "result" in result
    
    def test_simple_status_endpoint(self, client):
        """Test simple mode status endpoint."""
        job_id = "simple-test-job"
        
        response = client.get(f"/batch/simple/status/{job_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert result["job_id"] == job_id
        assert result["status"] == "completed"
        assert result["progress"] == 100.0
        assert result["mode"] == "simple"
    
    def test_simple_download_not_found(self, client):
        """Test simple mode download endpoint with non-existent job."""
        job_id = "nonexistent-simple-job"
        
        response = client.get(f"/batch/simple/download/{job_id}")
        
        assert response.status_code == 404
        assert "Job result not found" in response.json()["detail"]


class TestHealthAndWorkerStatus:
    """Test health and worker status endpoints."""
    
    def test_health_endpoint(self, client):
        """Test health endpoint showing both modes."""
        response = client.get("/batch/health")
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "healthy"
        assert "modes" in result
        assert "batch" in result["modes"]
        assert "simple" in result["modes"]
        assert "endpoints" in result
    
    @patch('src.batch.api.DB_PATH')
    @patch('sqlite3.connect')
    def test_worker_status_endpoint(self, mock_connect, mock_db_path, client):
        """Test worker status endpoint."""
        # Mock database path and connection
        mock_db_path.exists.return_value = True
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [('task',)]
        mock_cursor.fetchone.side_effect = [(10,), (5,)]  # total_tasks, pending_tasks
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        response = client.get("/batch/worker-status")
        
        assert response.status_code == 200
        result = response.json()
        assert "huey_stats" in result
        assert result["huey_stats"]["total_tasks"] == 10
        assert result["huey_stats"]["pending_tasks"] == 5


class TestFileValidation:
    """Test file validation across both modes."""
    
    def test_batch_mode_file_limits(self, client, sample_svg_content):
        """Test batch mode file limits."""
        # Test maximum files (50)
        files = [
            ("files", (f"test{i}.svg", sample_svg_content, "image/svg+xml"))
            for i in range(51)  # Exceeds limit
        ]
        
        response = client.post("/batch/convert-files", files=files)
        
        assert response.status_code == 400
        assert "Too many files" in response.json()["detail"]
    
    def test_simple_mode_file_limits(self, client, sample_svg_content):
        """Test simple mode file limits (lower than batch mode)."""
        # Test maximum files (20)
        files = [
            ("files", (f"test{i}.svg", sample_svg_content, "image/svg+xml"))
            for i in range(21)  # Exceeds simple mode limit
        ]
        
        response = client.post("/batch/simple/convert-files", files=files)
        
        assert response.status_code == 400
        assert "Too many files for synchronous processing" in response.json()["detail"]
    
    def test_batch_mode_size_limits(self, client):
        """Test batch mode size limits."""
        # Create file just over batch mode limit (100MB)
        large_content = b"x" * (101 * 1024 * 1024)
        files = [("files", ("test.svg", large_content, "image/svg+xml"))]
        
        response = client.post("/batch/convert-files", files=files)
        
        assert response.status_code == 400
        assert "Total upload size too large" in response.json()["detail"]
    
    def test_simple_mode_size_limits(self, client):
        """Test simple mode size limits (lower than batch mode)."""
        # Create file just over simple mode limit (50MB)
        large_content = b"x" * (51 * 1024 * 1024)
        files = [("files", ("test.svg", large_content, "image/svg+xml"))]
        
        response = client.post("/batch/simple/convert-files", files=files)
        
        assert response.status_code == 400
        assert "Total upload size too large for synchronous processing" in response.json()["detail"]


class TestErrorHandling:
    """Test error handling across both modes."""
    
    def test_batch_mode_invalid_file_type(self, client):
        """Test batch mode with invalid file type."""
        files = [("files", ("test.txt", b"not svg", "text/plain"))]
        
        response = client.post("/batch/convert-files", files=files)
        
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]
    
    def test_simple_mode_invalid_file_type(self, client):
        """Test simple mode with invalid file type."""
        files = [("files", ("test.txt", b"not svg", "text/plain"))]
        
        response = client.post("/batch/simple/convert-files", files=files)
        
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]
    
    def test_batch_mode_empty_files(self, client):
        """Test batch mode with empty files."""
        files = [("files", ("test.svg", b"", "image/svg+xml"))]
        
        response = client.post("/batch/convert-files", files=files)
        
        assert response.status_code == 400
        assert "Empty file" in response.json()["detail"]
    
    def test_simple_mode_empty_files(self, client):
        """Test simple mode with empty files."""
        files = [("files", ("test.svg", b"", "image/svg+xml"))]
        
        response = client.post("/batch/simple/convert-files", files=files)
        
        assert response.status_code == 400
        assert "Empty file" in response.json()["detail"]


class TestModeCompatibility:
    """Test API compatibility between modes."""
    
    def test_same_response_structure(self, client, sample_svg_content):
        """Test that both modes return compatible response structures."""
        files = [("files", ("test.svg", sample_svg_content, "image/svg+xml"))]
        data = {"output_format": "single_pptx"}
        
        # Test batch mode response structure
        batch_response = client.post("/batch/convert-files", files=files, data=data)
        batch_result = batch_response.json()
        
        # Test simple mode response structure
        simple_response = client.post("/batch/simple/convert-files", files=files, data=data)
        simple_result = simple_response.json()
        
        # Both should have these common fields
        common_fields = ["status", "total_files"]
        for field in common_fields:
            assert field in batch_result
            assert field in simple_result
        
        # Both should have job/batch ID (different field names but same purpose)
        assert "batch_id" in batch_result or "job_id" in batch_result
        assert "job_id" in simple_result or "batch_id" in simple_result
    
    def test_status_endpoint_compatibility(self, client):
        """Test that status endpoints return compatible structures."""
        job_id = "test-compatibility"
        
        # Simple mode status (always returns completed)
        simple_response = client.get(f"/batch/simple/status/{job_id}")
        simple_result = simple_response.json()
        
        # Both should have these fields
        required_fields = ["status", "progress", "job_id"]
        for field in required_fields:
            assert field in simple_result
        
        assert simple_result["status"] == "completed"
        assert simple_result["progress"] == 100.0