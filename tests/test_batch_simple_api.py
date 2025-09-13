#!/usr/bin/env python3
"""
Tests for batch simple API module.
"""

import pytest
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import UploadFile

from src.batch.simple_api import (
    SimpleJobResponse, SimpleBatchProcessor, simple_router,
    create_simple_batch_job, get_simple_job_status, download_simple_result
)


class TestSimpleJobResponse:
    """Test SimpleJobResponse model."""
    
    def test_simple_job_response_creation(self):
        """Test basic response creation."""
        response = SimpleJobResponse(
            job_id="test-123",
            status="completed",
            message="Job completed successfully",
            total_files=5,
            result={"converted_files": 5}
        )
        
        assert response.job_id == "test-123"
        assert response.status == "completed"
        assert response.message == "Job completed successfully"
        assert response.total_files == 5
        assert response.result["converted_files"] == 5
    
    def test_simple_job_response_defaults(self):
        """Test response with default values."""
        response = SimpleJobResponse(
            job_id="test-456",
            message="Processing files",
            total_files=3
        )
        
        assert response.status == "completed"  # Default value
        assert response.result is None  # Default value
    
    def test_simple_job_response_validation(self):
        """Test response validation."""
        # Valid response
        response = SimpleJobResponse(
            job_id="valid-id",
            message="Valid message",
            total_files=1
        )
        
        assert len(response.job_id) > 0
        assert len(response.message) > 0
        assert response.total_files > 0


class TestSimpleBatchProcessor:
    """Test SimpleBatchProcessor functionality."""
    
    @pytest.fixture
    def processor(self):
        """Create SimpleBatchProcessor instance."""
        return SimpleBatchProcessor()
    
    def test_processor_initialization(self, processor):
        """Test processor initialization."""
        assert processor.temp_dir is not None
        assert processor.completed_jobs == {}
        assert processor.job_results == {}
    
    def test_create_temp_directory(self, processor):
        """Test temporary directory creation."""
        temp_dir = processor._create_temp_directory("test-job")
        
        assert temp_dir.exists()
        assert temp_dir.is_dir()
        assert "test-job" in str(temp_dir)
    
    def test_process_svg_files_sync(self, processor):
        """Test synchronous SVG file processing."""
        # Create test SVG content
        test_svg = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <rect x="10" y="10" width="80" height="80" fill="red"/>
</svg>"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            f.write(test_svg)
            f.flush()
            
            svg_files = [Path(f.name)]
            
            with patch('src.batch.simple_api.convert_svg_to_pptx') as mock_convert:
                mock_convert.return_value = {"status": "success", "output_file": "test.pptx"}
                
                results = processor.process_svg_files(svg_files, job_id="test-sync")
        
        assert len(results) == 1
        assert results[0]["status"] == "success"
        mock_convert.assert_called_once()
    
    def test_zip_results(self, processor):
        """Test zipping conversion results."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test result files
            result_files = []
            for i in range(3):
                test_file = temp_path / f"result_{i}.pptx"
                test_file.write_text(f"Test PPTX content {i}")
                result_files.append(test_file)
            
            zip_path = processor._zip_results(result_files, "test-zip-job")
            
            assert zip_path.exists()
            assert zip_path.suffix == '.zip'
            
            # Verify zip contents
            with zipfile.ZipFile(zip_path, 'r') as zf:
                assert len(zf.namelist()) == 3
                assert all(name.endswith('.pptx') for name in zf.namelist())
    
    def test_cleanup_job_files(self, processor):
        """Test cleanup of job files."""
        job_id = "cleanup-test"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            job_dir = Path(temp_dir) / job_id
            job_dir.mkdir()
            
            # Create some files
            test_file = job_dir / "test.txt"
            test_file.write_text("test content")
            
            processor._cleanup_job_files(job_id, job_dir)
            
            assert not test_file.exists()
    
    def test_job_status_tracking(self, processor):
        """Test job status tracking."""
        job_id = "status-test"
        
        # Job should not exist initially
        assert processor.get_job_status(job_id) is None
        
        # Mark job as completed
        processor._mark_job_completed(job_id, {
            "total_files": 5,
            "successful": 4,
            "failed": 1,
            "zip_file": "results.zip"
        })
        
        status = processor.get_job_status(job_id)
        assert status is not None
        assert status["status"] == "completed"
        assert status["total_files"] == 5
    
    def test_result_retrieval(self, processor):
        """Test result file retrieval."""
        job_id = "result-test"
        
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
            temp_zip.write(b"fake zip content")
            temp_zip.flush()
            
            processor.job_results[job_id] = {
                "zip_file": Path(temp_zip.name),
                "status": "completed"
            }
            
            result_file = processor.get_result_file(job_id)
            assert result_file is not None
            assert result_file.exists()


class TestSimpleAPIEndpoints:
    """Test Simple API endpoints."""
    
    @pytest.fixture
    def mock_processor(self):
        """Create mock processor for API tests."""
        processor = Mock(spec=SimpleBatchProcessor)
        processor.process_svg_files.return_value = [
            {"status": "success", "file": "test1.pptx"},
            {"status": "success", "file": "test2.pptx"}
        ]
        processor.get_job_status.return_value = {
            "status": "completed",
            "total_files": 2,
            "successful": 2,
            "failed": 0
        }
        processor.get_result_file.return_value = Path("/fake/path/results.zip")
        return processor
    
    @pytest.fixture
    def test_client(self, mock_processor):
        """Create FastAPI test client."""
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(simple_router)
        
        # Override dependency
        app.dependency_overrides[SimpleBatchProcessor] = lambda: mock_processor
        
        return TestClient(app)
    
    def test_create_batch_job_endpoint(self, test_client, mock_processor):
        """Test batch job creation endpoint."""
        # Create test SVG files
        test_files = []
        for i in range(2):
            content = f"""<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg">
    <rect x="{i*10}" y="{i*10}" width="50" height="50"/>
</svg>"""
            test_files.append(("files", (f"test_{i}.svg", content, "image/svg+xml")))
        
        response = test_client.post("/simple/batch", files=test_files)
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "completed"
        assert data["total_files"] == 2
    
    def test_get_job_status_endpoint(self, test_client, mock_processor):
        """Test job status endpoint."""
        job_id = "test-job-123"
        
        response = test_client.get(f"/simple/status/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["total_files"] == 2
    
    def test_download_result_endpoint(self, test_client, mock_processor):
        """Test result download endpoint."""
        job_id = "download-test"
        
        with patch('src.batch.simple_api.FileResponse') as mock_response:
            mock_response.return_value = Mock()
            
            response = test_client.get(f"/simple/download/{job_id}")
            
            # FileResponse should be created
            mock_response.assert_called_once()
    
    def test_job_not_found_error(self, test_client, mock_processor):
        """Test job not found error handling."""
        mock_processor.get_job_status.return_value = None
        
        response = test_client.get("/simple/status/nonexistent-job")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_no_files_uploaded_error(self, test_client):
        """Test error when no files are uploaded."""
        response = test_client.post("/simple/batch", files=[])
        
        assert response.status_code == 400
        assert "no files" in response.json()["detail"].lower()
    
    def test_invalid_file_type_error(self, test_client):
        """Test error for invalid file types."""
        invalid_files = [
            ("files", ("test.txt", "not svg content", "text/plain"))
        ]
        
        response = test_client.post("/simple/batch", files=invalid_files)
        
        # Should either reject or filter out non-SVG files
        assert response.status_code in [200, 400]  # Depends on implementation


class TestSimpleAPIIntegration:
    """Integration tests for Simple API."""
    
    def test_end_to_end_conversion(self):
        """Test end-to-end conversion workflow."""
        processor = SimpleBatchProcessor()
        
        # Create test SVG content
        test_svg = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
    <circle cx="100" cy="100" r="50" fill="blue"/>
</svg>"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            f.write(test_svg)
            f.flush()
            
            svg_files = [Path(f.name)]
            job_id = "e2e-test"
            
            with patch('src.batch.simple_api.convert_svg_to_pptx') as mock_convert:
                mock_convert.return_value = {
                    "status": "success",
                    "output_file": "converted.pptx",
                    "message": "Conversion successful"
                }
                
                results = processor.process_svg_files(svg_files, job_id)
        
        assert len(results) == 1
        assert results[0]["status"] == "success"
        
        # Check job status
        status = processor.get_job_status(job_id)
        assert status["status"] == "completed"
    
    def test_batch_with_mixed_results(self):
        """Test batch processing with mixed success/failure results."""
        processor = SimpleBatchProcessor()
        
        # Create multiple test files
        svg_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
                f.write(f"<svg xmlns='http://www.w3.org/2000/svg'><rect x='{i*20}'/></svg>")
                f.flush()
                svg_files.append(Path(f.name))
        
        def mock_convert_mixed(svg_file, output_file):
            """Mock converter with mixed results."""
            if "0" in str(svg_file):
                return {"status": "success", "output_file": output_file}
            else:
                return {"status": "error", "message": "Conversion failed"}
        
        with patch('src.batch.simple_api.convert_svg_to_pptx', side_effect=mock_convert_mixed):
            results = processor.process_svg_files(svg_files, "mixed-test")
        
        assert len(results) == 3
        success_count = sum(1 for r in results if r["status"] == "success")
        error_count = sum(1 for r in results if r["status"] == "error")
        
        assert success_count == 1
        assert error_count == 2
    
    def test_large_batch_processing(self):
        """Test processing of larger batches."""
        processor = SimpleBatchProcessor()
        
        # Create many small SVG files
        svg_files = []
        batch_size = 10
        
        for i in range(batch_size):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
                f.write(f"""<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg">
    <rect x="{i*5}" y="{i*5}" width="20" height="20" fill="green"/>
</svg>""")
                f.flush()
                svg_files.append(Path(f.name))
        
        with patch('src.batch.simple_api.convert_svg_to_pptx') as mock_convert:
            mock_convert.return_value = {"status": "success", "output_file": "test.pptx"}
            
            results = processor.process_svg_files(svg_files, "large-batch")
        
        assert len(results) == batch_size
        assert all(r["status"] == "success" for r in results)
        assert mock_convert.call_count == batch_size


@pytest.mark.performance
class TestSimpleAPIPerformance:
    """Performance tests for Simple API."""
    
    def test_batch_processing_performance(self, benchmark):
        """Benchmark batch processing performance."""
        processor = SimpleBatchProcessor()
        
        # Create test files
        svg_files = []
        for i in range(5):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
                f.write(f"<svg xmlns='http://www.w3.org/2000/svg'><circle r='{10+i}'/></svg>")
                f.flush()
                svg_files.append(Path(f.name))
        
        def process_batch():
            with patch('src.batch.simple_api.convert_svg_to_pptx') as mock_convert:
                mock_convert.return_value = {"status": "success", "output_file": "test.pptx"}
                return processor.process_svg_files(svg_files, "perf-test")
        
        results = benchmark(process_batch)
        assert len(results) == 5
    
    def test_zip_creation_performance(self, benchmark):
        """Benchmark ZIP file creation performance."""
        processor = SimpleBatchProcessor()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test result files
            result_files = []
            for i in range(20):
                test_file = temp_path / f"result_{i}.pptx"
                test_file.write_text(f"Test PPTX content {i}" * 100)  # Make files larger
                result_files.append(test_file)
            
            def create_zip():
                return processor._zip_results(result_files, "perf-zip")
            
            zip_path = benchmark(create_zip)
            assert zip_path.exists()