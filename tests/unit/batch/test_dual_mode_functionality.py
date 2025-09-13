#!/usr/bin/env python3
"""
Tests for dual-mode functionality and mode switching capabilities.
"""

import pytest
from unittest.mock import patch, Mock
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Configure Huey for testing (immediate mode)
os.environ['HUEY_IMMEDIATE'] = 'true'

from src.batch.api import create_batch_router


# Note: sample_svg_content fixture is imported from tests.fixtures.svg_content
# This returns a byte string for compatibility
@pytest.fixture
def sample_svg_content_bytes():
    """Sample SVG content as bytes for testing."""
    return b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>'


@pytest.fixture
def dual_mode_app():
    """Create FastAPI app with dual-mode batch router."""
    app = FastAPI()
    app.include_router(create_batch_router())
    return app


@pytest.fixture
def client(dual_mode_app):
    """Create test client for dual-mode testing."""
    return TestClient(dual_mode_app)


class TestDualModeConfiguration:
    """Test dual-mode configuration and detection."""
    
    def test_health_endpoint_shows_both_modes(self, client):
        """Test that health endpoint shows both batch and simple modes."""
        response = client.get("/batch/health")
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["status"] == "healthy"
        assert "modes" in result
        assert "batch" in result["modes"]
        assert "simple" in result["modes"]
        
        # Check that endpoints are documented
        assert "endpoints" in result
        assert "batch_mode" in result["endpoints"]
        assert "simple_mode" in result["endpoints"]
    
    @patch('src.batch.api.DB_PATH')
    def test_huey_availability_detection(self, mock_db_path, client):
        """Test Huey availability detection in health check."""
        # Test when Huey database is available
        mock_db_path.exists.return_value = True
        mock_db_path.parent.exists.return_value = True
        
        response = client.get("/batch/health")
        result = response.json()
        
        assert "huey_available" in result
        assert result["huey_available"] is True
        
        # Test when Huey database is not available
        mock_db_path.exists.return_value = False
        mock_db_path.parent.exists.return_value = False
        
        response = client.get("/batch/health")
        result = response.json()
        
        assert result["huey_available"] is False


class TestModeSpecificBehavior:
    """Test mode-specific behavior differences."""
    
    def test_batch_mode_creates_task(self, client, sample_svg_content):
        """Test that batch mode creates background tasks."""
        files = [("files", ("test.svg", sample_svg_content, "image/svg+xml"))]
        
        response = client.post("/batch/convert-files", files=files)
        
        assert response.status_code == 200
        result = response.json()
        
        # Batch mode should return PENDING status initially
        assert result["status"] == "PENDING"
        assert "batch_id" in result
        assert result["message"] == "Batch processing started"
    
    def test_simple_mode_immediate_completion(self, client, sample_svg_content):
        """Test that simple mode completes immediately."""
        files = [("files", ("test.svg", sample_svg_content, "image/svg+xml"))]
        
        response = client.post("/batch/simple/convert-files", files=files)
        
        assert response.status_code == 200
        result = response.json()
        
        # Simple mode should return completed status immediately
        assert result["status"] == "completed"
        assert result["mode"] == "simple"
        assert "job_id" in result
        assert "result" in result  # Should include actual result data
    
    def test_mode_specific_file_limits(self, client, sample_svg_content):
        """Test that modes have different file limits."""
        # Create 25 files (exceeds simple mode limit of 20, within batch limit of 50)
        files = [
            ("files", (f"test{i}.svg", sample_svg_content, "image/svg+xml"))
            for i in range(25)
        ]
        
        # Batch mode should accept 25 files
        batch_response = client.post("/batch/convert-files", files=files)
        assert batch_response.status_code == 200
        
        # Simple mode should reject 25 files
        simple_response = client.post("/batch/simple/convert-files", files=files)
        assert simple_response.status_code == 400
        assert "Too many files for synchronous processing" in simple_response.json()["detail"]
    
    def test_mode_specific_size_limits(self, client):
        """Test that modes have different size limits."""
        # Create content just over simple mode limit (50MB) but under batch limit (100MB)
        large_content = b"x" * (60 * 1024 * 1024)  # 60MB
        files = [("files", ("test.svg", large_content, "image/svg+xml"))]
        
        # Batch mode should accept 60MB
        batch_response = client.post("/batch/convert-files", files=files)
        assert batch_response.status_code == 200
        
        # Simple mode should reject 60MB
        simple_response = client.post("/batch/simple/convert-files", files=files)
        assert simple_response.status_code == 400
        assert "Total upload size too large for synchronous processing" in simple_response.json()["detail"]


class TestCrossModalCompatibility:
    """Test compatibility between modes."""
    
    def test_status_endpoint_response_format(self, client):
        """Test that status endpoints return compatible response formats."""
        job_id = "test-status-format"
        
        # Get simple mode status (always completed)
        simple_response = client.get(f"/batch/simple/status/{job_id}")
        simple_result = simple_response.json()
        
        # Check required fields are present
        required_fields = ["job_id", "status", "progress"]
        for field in required_fields:
            assert field in simple_result
        
        assert simple_result["job_id"] == job_id
        assert simple_result["status"] == "completed"
        assert simple_result["progress"] == 100.0
        assert simple_result["mode"] == "simple"
    
    @patch('src.batch.api.huey')
    def test_download_endpoint_compatibility(self, mock_huey, client):
        """Test that download endpoints work for both modes."""
        # Create temporary files for testing
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
            temp_file.write(b"mock pptx content")
            temp_path = temp_file.name
        
        try:
            # Test batch mode download
            mock_task = Mock()
            mock_task.is_complete.return_value = True
            mock_task.return_value = {
                'success': True,
                'output_path': temp_path,
                'individual_results': []
            }
            mock_huey.get.return_value = mock_task
            
            batch_response = client.get("/batch/download/test-batch")
            assert batch_response.status_code == 200
            
            # Simple mode download with non-existent job should return 404
            simple_response = client.get("/batch/simple/download/nonexistent")
            assert simple_response.status_code == 404
            
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestModeSpecificErrorHandling:
    """Test error handling specific to each mode."""
    
    def test_batch_mode_task_not_found(self, client):
        """Test batch mode with non-existent task."""
        with patch('src.batch.api.huey') as mock_huey:
            mock_huey.get.return_value = None
            
            response = client.get("/batch/status/nonexistent")
            
            assert response.status_code == 404
            assert "Batch job not found" in response.json()["detail"]
    
    def test_simple_mode_always_completed(self, client):
        """Test that simple mode status always returns completed."""
        # Any job ID should return completed status in simple mode
        random_job_ids = ["abc123", "xyz789", "nonexistent"]
        
        for job_id in random_job_ids:
            response = client.get(f"/batch/simple/status/{job_id}")
            
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "completed"
            assert result["progress"] == 100.0
    
    @patch('src.batch.api.huey')
    def test_batch_mode_task_failure_handling(self, mock_huey, client):
        """Test batch mode handling of failed tasks."""
        mock_task = Mock()
        mock_task.is_complete.return_value = True
        mock_task.is_revoked.return_value = False
        mock_task.return_value = {
            'success': False,
            'error_message': 'Conversion failed'
        }
        mock_huey.get.return_value = mock_task
        
        response = client.get("/batch/status/failed-task")
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "FAILURE"
        assert result["error_message"] == "Conversion failed"
    
    def test_simple_mode_conversion_error_handling(self, client):
        """Test simple mode handling of conversion errors."""
        # Test with invalid file type (should return error immediately)
        files = [("files", ("test.txt", b"not svg", "text/plain"))]
        
        response = client.post("/batch/simple/convert-files", files=files)
        
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]


class TestModeSpecificFeatures:
    """Test features specific to each mode."""
    
    @patch('src.batch.api.huey')
    def test_batch_mode_cancellation(self, mock_huey, client):
        """Test batch mode task cancellation (not available in simple mode)."""
        mock_task = Mock()
        mock_task.is_complete.return_value = False
        mock_task.revoke = Mock()
        mock_huey.get.return_value = mock_task
        
        response = client.delete("/batch/cancel/test-batch")
        
        assert response.status_code == 200
        result = response.json()
        assert "cancelled" in result["message"]
        mock_task.revoke.assert_called_once()
    
    def test_simple_mode_no_cancellation(self, client):
        """Test that simple mode doesn't have cancellation endpoint."""
        # Simple mode doesn't have a cancel endpoint
        response = client.delete("/batch/simple/cancel/test-job")
        
        assert response.status_code == 404  # Not Found
    
    @patch('src.batch.api.huey')
    def test_batch_mode_progress_tracking(self, mock_huey, client):
        """Test batch mode progress tracking (not available in simple mode)."""
        # Test pending task
        mock_task = Mock()
        mock_task.is_complete.return_value = False
        mock_task.is_revoked.return_value = False
        mock_huey.get.return_value = mock_task
        
        response = client.get("/batch/status/pending-task")
        result = response.json()
        
        assert result["status"] == "PENDING"
        assert result["progress"] == 0.0
        assert result["current_step"] == "processing"
    
    def test_simple_mode_immediate_results(self, client, sample_svg_content):
        """Test that simple mode returns immediate results."""
        files = [("files", ("test.svg", sample_svg_content, "image/svg+xml"))]
        
        response = client.post("/batch/simple/convert-files", files=files)
        result = response.json()
        
        # Simple mode should include the actual result in the response
        assert "result" in result
        assert result["result"]["success"] is True
        assert "job_id" in result["result"]


class TestPerformanceCharacteristics:
    """Test performance characteristics of each mode."""
    
    def test_simple_mode_synchronous_behavior(self, client, sample_svg_content):
        """Test that simple mode processes synchronously."""
        files = [("files", ("test.svg", sample_svg_content, "image/svg+xml"))]
        
        # Make request and verify immediate completion
        response = client.post("/batch/simple/convert-files", files=files)
        
        assert response.status_code == 200
        result = response.json()
        
        # Should be completed immediately
        assert result["status"] == "completed"
        assert "result" in result  # Result should be available immediately
    
    def test_batch_mode_asynchronous_behavior(self, client, sample_svg_content):
        """Test that batch mode processes asynchronously."""
        files = [("files", ("test.svg", sample_svg_content, "image/svg+xml"))]
        
        # Make request and verify it starts asynchronously
        response = client.post("/batch/convert-files", files=files)
        
        assert response.status_code == 200
        result = response.json()
        
        # Should be pending initially (even in immediate mode for testing)
        assert result["status"] == "PENDING"
        assert "batch_id" in result
        assert result["message"] == "Batch processing started"


class TestModeDocumentation:
    """Test that modes are properly documented through API."""
    
    def test_endpoint_documentation_in_health(self, client):
        """Test that health endpoint documents available endpoints."""
        response = client.get("/batch/health")
        result = response.json()
        
        assert "endpoints" in result
        endpoints_info = result["endpoints"]
        
        # Should document batch mode endpoints
        assert "batch_mode" in endpoints_info
        batch_endpoints = endpoints_info["batch_mode"]
        assert "/batch/convert-files" in batch_endpoints
        assert "/batch/status/" in batch_endpoints
        assert "/batch/download/" in batch_endpoints
        
        # Should document simple mode endpoints
        assert "simple_mode" in endpoints_info
        simple_endpoints = endpoints_info["simple_mode"]
        assert "/batch/simple/convert-files" in simple_endpoints
        assert "/batch/simple/status/" in simple_endpoints
        assert "/batch/simple/download/" in simple_endpoints
    
    def test_mode_descriptions_in_health(self, client):
        """Test that health endpoint provides mode descriptions."""
        response = client.get("/batch/health")
        result = response.json()
        
        assert "modes" in result
        modes = result["modes"]
        
        # Should describe batch mode
        assert "batch" in modes
        batch_desc = modes["batch"]
        assert "Huey" in batch_desc or "background" in batch_desc.lower()
        
        # Should describe simple mode
        assert "simple" in modes
        simple_desc = modes["simple"]
        assert "synchronous" in simple_desc.lower() or "immediate" in simple_desc.lower()


class TestModeSelectionGuidance:
    """Test guidance for selecting appropriate mode."""
    
    def test_simple_mode_use_case_validation(self, client, sample_svg_content):
        """Test that simple mode is suitable for small files and immediate results."""
        # Small file should work in simple mode
        small_content = sample_svg_content  # Small SVG
        files = [("files", ("small.svg", small_content, "image/svg+xml"))]
        
        response = client.post("/batch/simple/convert-files", files=files)
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "completed"
        assert result["mode"] == "simple"
    
    def test_batch_mode_use_case_validation(self, client, sample_svg_content):
        """Test that batch mode is suitable for larger workloads."""
        # Create multiple files (within batch limits)
        files = [
            ("files", (f"file{i}.svg", sample_svg_content, "image/svg+xml"))
            for i in range(30)  # More than simple mode can handle
        ]
        
        response = client.post("/batch/convert-files", files=files)
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "PENDING"  # Background processing
        assert result["total_files"] == 30