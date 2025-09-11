#!/usr/bin/env python3
"""
Tests for simple synchronous API endpoints.
"""

import pytest
from unittest.mock import patch, Mock
import tempfile
import zipfile
from pathlib import Path
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.batch.simple_api import (
    create_simple_router,
    convert_single_svg_sync,
    merge_presentations_sync,
    ConversionError
)


@pytest.fixture
def sample_svg_content():
    """Sample SVG content for testing."""
    return b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>'


@pytest.fixture
def sample_svg_file(sample_svg_content):
    """Create a temporary SVG file."""
    with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as f:
        f.write(sample_svg_content)
        f.flush()
        yield f.name
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def simple_app():
    """Create FastAPI app with simple router for testing."""
    app = FastAPI()
    app.include_router(create_simple_router())
    return app


@pytest.fixture
def client(simple_app):
    """Create test client."""
    return TestClient(simple_app)


class TestConvertSingleSvgSync:
    """Test synchronous SVG conversion function."""
    
    def test_successful_conversion(self, sample_svg_content):
        """Test successful SVG conversion."""
        file_data = {
            'filename': 'test.svg',
            'content': sample_svg_content
        }
        
        result = convert_single_svg_sync(file_data)
        
        assert result['success'] is True
        assert result['input_filename'] == 'test.svg'
        assert result['output_filename'] == 'test.pptx'
        assert 'output_path' in result
        assert 'completed_at' in result
        assert result['input_size'] == len(sample_svg_content)
    
    def test_conversion_with_options(self, sample_svg_content):
        """Test conversion with custom options."""
        file_data = {
            'filename': 'test.svg',
            'content': sample_svg_content
        }
        
        options = {
            'slide_width': 12.0,
            'slide_height': 9.0,
            'quality': 'medium'
        }
        
        result = convert_single_svg_sync(file_data, options)
        
        assert result['success'] is True
        assert result['conversion_options']['slide_width'] == 12.0
        assert result['conversion_options']['slide_height'] == 9.0
        assert result['conversion_options']['quality'] == 'medium'
    
    def test_invalid_file_type(self):
        """Test conversion with invalid file type."""
        file_data = {
            'filename': 'test.txt',
            'content': b'not an svg'
        }
        
        result = convert_single_svg_sync(file_data)
        
        assert result['success'] is False
        assert result['error_type'] == 'conversion_error'
        assert 'Invalid file type' in result['error_message']
    
    def test_empty_file(self):
        """Test conversion with empty file."""
        file_data = {
            'filename': 'test.svg',
            'content': b''
        }
        
        result = convert_single_svg_sync(file_data)
        
        assert result['success'] is False
        assert result['error_type'] == 'conversion_error'
        assert 'Empty file' in result['error_message']
    
    def test_file_too_large(self):
        """Test conversion with file too large."""
        large_content = b'x' * (11 * 1024 * 1024)  # 11MB
        file_data = {
            'filename': 'test.svg',
            'content': large_content
        }
        
        result = convert_single_svg_sync(file_data)
        
        assert result['success'] is False
        assert result['error_type'] == 'conversion_error'
        assert 'File too large' in result['error_message']


class TestMergePresentationsSync:
    """Test synchronous presentation merging function."""
    
    def test_successful_merge_single_pptx(self):
        """Test successful merging to single PPTX."""
        conversion_results = [
            {
                'success': True,
                'input_filename': 'file1.svg',
                'output_filename': 'file1.pptx',
                'output_path': '/tmp/file1.pptx',
                'input_size': 1000
            },
            {
                'success': True,
                'input_filename': 'file2.svg',
                'output_filename': 'file2.pptx',
                'output_path': '/tmp/file2.pptx',
                'input_size': 2000
            }
        ]
        
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat.return_value.st_size = 5000
            result = merge_presentations_sync(conversion_results, 'single_pptx')
        
        assert result['success'] is True
        assert result['output_format'] == 'single_pptx'
        assert result['total_files_processed'] == 2
        assert result['failed_files'] == 0
        assert result['total_input_size'] == 3000
        assert 'job_id' in result
    
    def test_successful_merge_zip_archive(self):
        """Test successful merging to ZIP archive."""
        conversion_results = [
            {
                'success': True,
                'input_filename': 'file1.svg',
                'output_filename': 'file1.pptx',
                'output_path': '/tmp/file1.pptx',
                'input_size': 1000
            }
        ]
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.stat') as mock_stat, \
             patch('zipfile.ZipFile'):
            mock_stat.return_value.st_size = 2000
            result = merge_presentations_sync(conversion_results, 'zip_archive')
        
        assert result['success'] is True
        assert result['output_format'] == 'zip_archive'
        assert result['total_files_processed'] == 1
    
    def test_merge_with_failures(self):
        """Test merging with some failed conversions."""
        conversion_results = [
            {'success': True, 'input_filename': 'file1.svg', 'output_path': '/tmp/file1.pptx', 'input_size': 1000},
            {'success': False, 'input_filename': 'file2.svg', 'error_message': 'Failed'},
            {'success': True, 'input_filename': 'file3.svg', 'output_path': '/tmp/file3.pptx', 'input_size': 2000}
        ]
        
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat.return_value.st_size = 3000
            result = merge_presentations_sync(conversion_results, 'single_pptx')
        
        assert result['success'] is True
        assert result['total_files_processed'] == 2
        assert result['failed_files'] == 1
    
    def test_merge_no_successful_conversions(self):
        """Test merging when all conversions failed."""
        conversion_results = [
            {'success': False, 'error_message': 'Failed 1'},
            {'success': False, 'error_message': 'Failed 2'}
        ]
        
        result = merge_presentations_sync(conversion_results)
        
        assert result['success'] is False
        assert 'error_message' in result
    
    def test_merge_unsupported_format(self):
        """Test merging with unsupported output format."""
        conversion_results = [
            {'success': True, 'input_filename': 'file1.svg', 'output_path': '/tmp/file1.pptx'}
        ]
        
        result = merge_presentations_sync(conversion_results, 'invalid_format')
        
        assert result['success'] is False
        assert 'Unsupported output format' in result['error_message']


class TestSimpleAPIEndpoints:
    """Test simple API endpoints."""
    
    def test_convert_files_endpoint(self, client, sample_svg_content):
        """Test convert files endpoint."""
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
        
        response = client.post("/simple/convert-files", files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "completed"
        assert result["total_files"] == 2
        assert "job_id" in result
        assert "result" in result
    
    def test_convert_files_no_files(self, client):
        """Test convert files endpoint with no files."""
        response = client.post("/simple/convert-files", files=[])
        
        assert response.status_code == 422  # Validation error
    
    def test_convert_files_invalid_type(self, client):
        """Test convert files endpoint with invalid file type."""
        files = [("files", ("test.txt", b"not svg", "text/plain"))]
        
        response = client.post("/simple/convert-files", files=files)
        
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]
    
    def test_convert_files_empty_file(self, client):
        """Test convert files endpoint with empty file."""
        files = [("files", ("test.svg", b"", "image/svg+xml"))]
        
        response = client.post("/simple/convert-files", files=files)
        
        assert response.status_code == 400
        assert "Empty file" in response.json()["detail"]
    
    def test_convert_files_too_many(self, client, sample_svg_content):
        """Test convert files endpoint with too many files."""
        files = [
            ("files", (f"test{i}.svg", sample_svg_content, "image/svg+xml"))
            for i in range(25)  # Exceeds limit of 20
        ]
        
        response = client.post("/simple/convert-files", files=files)
        
        assert response.status_code == 400
        assert "Too many files" in response.json()["detail"]
    
    def test_convert_files_file_too_large(self, client):
        """Test convert files endpoint with file too large."""
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        files = [("files", ("test.svg", large_content, "image/svg+xml"))]
        
        response = client.post("/simple/convert-files", files=files)
        
        assert response.status_code == 400
        assert "File too large" in response.json()["detail"]
    
    def test_convert_files_total_too_large(self, client):
        """Test convert files endpoint with total size too large."""
        # Create files that total more than 50MB
        large_content = b"x" * (30 * 1024 * 1024)  # 30MB each
        files = [
            ("files", ("test1.svg", large_content, "image/svg+xml")),
            ("files", ("test2.svg", large_content, "image/svg+xml"))
        ]
        
        response = client.post("/simple/convert-files", files=files)
        
        assert response.status_code == 400
        assert "Total upload size too large" in response.json()["detail"]
    
    def test_status_endpoint(self, client):
        """Test status endpoint."""
        job_id = "test-job-123"
        
        response = client.get(f"/simple/status/{job_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert result["job_id"] == job_id
        assert result["status"] == "completed"
        assert result["progress"] == 100.0
    
    def test_download_endpoint_not_found(self, client):
        """Test download endpoint with non-existent job."""
        job_id = "nonexistent-job"
        
        response = client.get(f"/simple/download/{job_id}")
        
        assert response.status_code == 404
        assert "Job result not found" in response.json()["detail"]
    
    def test_health_endpoint(self, client):
        """Test health endpoint."""
        response = client.get("/simple/health")
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "healthy"
        assert result["mode"] == "simple_processing"


class TestZipProcessing:
    """Test ZIP file processing in simple mode."""
    
    def test_convert_zip_endpoint(self, client, sample_svg_content):
        """Test convert ZIP endpoint."""
        # Create a ZIP file with SVG content
        with tempfile.NamedTemporaryFile(suffix='.zip') as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w') as zip_file:
                zip_file.writestr('file1.svg', sample_svg_content)
                zip_file.writestr('file2.svg', sample_svg_content)
            
            temp_zip.seek(0)
            zip_content = temp_zip.read()
        
        files = [("zip_file", ("test.zip", zip_content, "application/zip"))]
        data = {"output_format": "zip_archive"}
        
        response = client.post("/simple/convert-zip", files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "completed"
        assert "job_id" in result
    
    def test_convert_zip_invalid_type(self, client):
        """Test convert ZIP endpoint with invalid file type."""
        files = [("zip_file", ("test.txt", b"not zip", "text/plain"))]
        
        response = client.post("/simple/convert-zip", files=files)
        
        assert response.status_code == 400
        assert "File must be a ZIP archive" in response.json()["detail"]
    
    def test_convert_zip_empty(self, client):
        """Test convert ZIP endpoint with empty file."""
        files = [("zip_file", ("test.zip", b"", "application/zip"))]
        
        response = client.post("/simple/convert-zip", files=files)
        
        assert response.status_code == 400
        assert "Empty ZIP file" in response.json()["detail"]
    
    def test_convert_zip_too_large(self, client):
        """Test convert ZIP endpoint with file too large."""
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        files = [("zip_file", ("test.zip", large_content, "application/zip"))]
        
        response = client.post("/simple/convert-zip", files=files)
        
        assert response.status_code == 400
        assert "ZIP file too large" in response.json()["detail"]
    
    def test_convert_zip_no_svg_files(self, client):
        """Test convert ZIP endpoint with no SVG files."""
        # Create ZIP with no SVG files
        with tempfile.NamedTemporaryFile(suffix='.zip') as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w') as zip_file:
                zip_file.writestr('readme.txt', b'No SVG files here')
            
            temp_zip.seek(0)
            zip_content = temp_zip.read()
        
        files = [("zip_file", ("test.zip", zip_content, "application/zip"))]
        
        response = client.post("/simple/convert-zip", files=files)
        
        assert response.status_code == 400
        assert "No SVG files found" in response.json()["detail"]
    
    def test_convert_zip_too_many_files(self, client, sample_svg_content):
        """Test convert ZIP endpoint with too many SVG files."""
        # Create ZIP with more than 15 SVG files
        with tempfile.NamedTemporaryFile(suffix='.zip') as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w') as zip_file:
                for i in range(20):  # Exceeds limit of 15
                    zip_file.writestr(f'file{i}.svg', sample_svg_content)
            
            temp_zip.seek(0)
            zip_content = temp_zip.read()
        
        files = [("zip_file", ("test.zip", zip_content, "application/zip"))]
        
        response = client.post("/simple/convert-zip", files=files)
        
        assert response.status_code == 400
        assert "Too many SVG files" in response.json()["detail"]
    
    def test_convert_zip_invalid_format(self, client):
        """Test convert ZIP endpoint with invalid ZIP format."""
        files = [("zip_file", ("test.zip", b"invalid zip content", "application/zip"))]
        
        response = client.post("/simple/convert-zip", files=files)
        
        assert response.status_code == 400
        assert "Invalid ZIP file format" in response.json()["detail"]