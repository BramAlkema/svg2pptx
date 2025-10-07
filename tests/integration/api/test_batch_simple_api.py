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

from core.batch.simple_api import (
    SimpleJobResponse, SimpleStatusResponse, ConversionError,
    convert_single_svg_sync, merge_presentations_sync, create_simple_router
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


class TestConversionFunctions:
    """Test core conversion functions."""
    
    def test_convert_single_svg_sync_success(self):
        """Test successful SVG conversion."""
        file_data = {
            'filename': 'test.svg',
            'content': b'<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'
        }
        
        result = convert_single_svg_sync(file_data)
        
        assert result['success'] is True
        assert result['input_filename'] == 'test.svg'
        assert result['output_filename'] == 'test.pptx'
        assert 'output_path' in result
        assert 'completed_at' in result
    
    def test_convert_single_svg_invalid_file_type(self):
        """Test conversion with invalid file type."""
        file_data = {
            'filename': 'test.txt',
            'content': b'not svg content'
        }
        
        result = convert_single_svg_sync(file_data)
        
        assert result['success'] is False
        assert result['error_type'] == 'conversion_error'
        assert 'Invalid file type' in result['error_message']
    
    def test_convert_single_svg_empty_file(self):
        """Test conversion with empty file."""
        file_data = {
            'filename': 'empty.svg',
            'content': b''
        }
        
        result = convert_single_svg_sync(file_data)
        
        assert result['success'] is False
        assert result['error_type'] == 'conversion_error'
        assert 'Empty file' in result['error_message']
    
    def test_convert_single_svg_with_options(self):
        """Test conversion with custom options."""
        file_data = {
            'filename': 'custom.svg',
            'content': b'<svg xmlns="http://www.w3.org/2000/svg"><circle/></svg>'
        }
        
        options = {
            'slide_width': 8.5,
            'slide_height': 11.0,
            'quality': 'medium'
        }
        
        result = convert_single_svg_sync(file_data, options)
        
        assert result['success'] is True
        assert result['conversion_options'] == options
    
    def test_merge_presentations_sync_single_pptx(self):
        """Test merging presentations into single PPTX."""
        conversion_results = [
            {
                'success': True,
                'input_filename': 'test1.svg',
                'output_filename': 'test1.pptx',
                'output_path': '/tmp/test1.pptx',
                'input_size': 100
            },
            {
                'success': True,
                'input_filename': 'test2.svg',
                'output_filename': 'test2.pptx',
                'output_path': '/tmp/test2.pptx',
                'input_size': 150
            }
        ]
        
        # Create mock files
        with tempfile.TemporaryDirectory() as temp_dir:
            for result in conversion_results:
                mock_file = Path(temp_dir) / result['output_filename']
                mock_file.write_text(f"Mock PPTX content for {result['input_filename']}")
                result['output_path'] = str(mock_file)
            
            merge_result = merge_presentations_sync(conversion_results, 'single_pptx')
        
        assert merge_result['success'] is True
        assert merge_result['output_format'] == 'single_pptx'
        assert merge_result['total_files_processed'] == 2
        assert merge_result['failed_files'] == 0
    
    def test_merge_presentations_sync_zip_archive(self):
        """Test merging presentations into ZIP archive."""
        conversion_results = [
            {
                'success': True,
                'input_filename': 'test1.svg',
                'output_filename': 'test1.pptx',
                'output_path': '/tmp/test1.pptx',
                'input_size': 100
            }
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file = Path(temp_dir) / 'test1.pptx'
            mock_file.write_text("Mock PPTX content")
            conversion_results[0]['output_path'] = str(mock_file)
            
            merge_result = merge_presentations_sync(conversion_results, 'zip_archive')
        
        assert merge_result['success'] is True
        assert merge_result['output_format'] == 'zip_archive'
        assert Path(merge_result['output_path']).suffix == '.zip'


class TestSimpleAPIRouter:
    """Test Simple API router creation and endpoints."""
    
    @pytest.fixture
    def test_client(self):
        """Create FastAPI test client."""
        from fastapi import FastAPI
        
        app = FastAPI()
        router = create_simple_router()
        app.include_router(router)
        
        return TestClient(app)
    
    def test_health_endpoint(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/simple/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["mode"] == "simple_processing"
    
    def test_status_endpoint_compatibility(self, test_client):
        """Test status endpoint for API compatibility."""
        job_id = "test-job-123"
        
        response = test_client.get(f"/simple/status/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "completed"
        assert data["progress"] == 100.0
    
    def test_convert_files_endpoint_validation(self, test_client):
        """Test file conversion endpoint validation."""
        # Test with no files
        response = test_client.post("/simple/convert-files", files=[])
        assert response.status_code == 400
        assert "No files provided" in response.json()["detail"]
        
        # Test with invalid file type
        invalid_files = [
            ("files", ("test.txt", "not svg content", "text/plain"))
        ]
        response = test_client.post("/simple/convert-files", files=invalid_files)
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]
    
    def test_convert_zip_endpoint_validation(self, test_client):
        """Test ZIP conversion endpoint validation."""
        # Test with non-ZIP file
        non_zip_file = ("zip_file", ("test.txt", "not zip content", "text/plain"))
        response = test_client.post("/simple/convert-zip", files=[non_zip_file])
        assert response.status_code == 400
        assert "ZIP archive" in response.json()["detail"]


class TestSimpleAPIIntegration:
    """Integration tests for Simple API functions."""
    
    def test_end_to_end_single_conversion(self):
        """Test end-to-end single file conversion."""
        file_data = {
            'filename': 'integration_test.svg',
            'content': b"""<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
    <circle cx="100" cy="100" r="50" fill="blue"/>
</svg>"""
        }
        
        result = convert_single_svg_sync(file_data)
        
        assert result['success'] is True
        assert result['input_filename'] == 'integration_test.svg'
        assert result['output_filename'] == 'integration_test.pptx'
        assert Path(result['output_path']).exists()
    
    def test_conversion_with_merge_workflow(self):
        """Test conversion followed by merge workflow."""
        # Create multiple test files
        file_list = []
        conversion_results = []
        
        for i in range(3):
            file_data = {
                'filename': f'test_{i}.svg',
                'content': f"""<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg">
    <rect x="{i*20}" y="{i*20}" width="50" height="50" fill="red"/>
</svg>""".encode()
            }
            
            result = convert_single_svg_sync(file_data)
            assert result['success'] is True
            conversion_results.append(result)
        
        # Test merging
        merge_result = merge_presentations_sync(conversion_results, 'zip_archive')
        
        assert merge_result['success'] is True
        assert merge_result['total_files_processed'] == 3
        assert Path(merge_result['output_path']).exists()
        assert merge_result['output_path'].endswith('.zip')
    
    def test_error_handling_workflow(self):
        """Test error handling in conversion workflow."""
        # Mix of valid and invalid files
        test_files = [
            {'filename': 'valid.svg', 'content': b'<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'},
            {'filename': 'invalid.txt', 'content': b'not svg content'},
            {'filename': 'empty.svg', 'content': b''}
        ]
        
        results = []
        for file_data in test_files:
            result = convert_single_svg_sync(file_data)
            results.append(result)
        
        # Check results
        assert results[0]['success'] is True  # valid.svg
        assert results[1]['success'] is False  # invalid.txt
        assert results[2]['success'] is False  # empty.svg
        
        # Test merge with mixed results
        merge_result = merge_presentations_sync(results, 'single_pptx')
        
        assert merge_result['success'] is True
        assert merge_result['total_files_processed'] == 1  # Only successful ones
        assert merge_result['failed_files'] == 2


@pytest.mark.benchmark
class TestSimpleAPIPerformance:
    """Performance tests for Simple API functions."""

    def test_single_conversion_performance(self, benchmark):
        """Benchmark single file conversion performance."""
        file_data = {
            'filename': 'perf_test.svg',
            'content': b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="50"/></svg>'
        }

        def convert_file():
            return convert_single_svg_sync(file_data)

        result = benchmark(convert_file)
        assert result['success'] is True

    def test_merge_performance(self, benchmark):
        """Benchmark merge operation performance."""
        # Create mock conversion results
        conversion_results = []
        with tempfile.TemporaryDirectory() as temp_dir:
            for i in range(10):
                mock_file = Path(temp_dir) / f"result_{i}.pptx"
                mock_file.write_text(f"Mock PPTX content {i}" * 50)
                
                conversion_results.append({
                    'success': True,
                    'input_filename': f'test_{i}.svg',
                    'output_filename': f'result_{i}.pptx',
                    'output_path': str(mock_file),
                    'input_size': 100 * i
                })
            
            def merge_files():
                return merge_presentations_sync(conversion_results, 'zip_archive')
            
            result = benchmark(merge_files)
            assert result['success'] is True