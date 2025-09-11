#!/usr/bin/env python3
"""
Tests for Huey-based batch processing tasks.
"""

import pytest
from unittest.mock import patch, Mock
import tempfile
import zipfile
from pathlib import Path
import os

# Configure Huey for testing (immediate mode)
os.environ['HUEY_IMMEDIATE'] = 'true'

from src.batch.tasks import (
    convert_single_svg,
    merge_presentations,
    cleanup_temp_files,
    process_svg_batch,
    extract_and_process_zip
)


@pytest.fixture
def sample_svg_content():
    """Sample SVG content for testing."""
    return b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>'


@pytest.fixture
def sample_file_data(sample_svg_content):
    """Sample file data dictionary."""
    return {
        'filename': 'test.svg',
        'content': sample_svg_content
    }


@pytest.fixture
def sample_conversion_options():
    """Sample conversion options."""
    return {
        'slide_width': 10.0,
        'slide_height': 7.5,
        'quality': 'high'
    }


class TestConvertSingleSvg:
    """Test single SVG conversion task."""
    
    def test_successful_conversion(self, sample_file_data, sample_conversion_options):
        """Test successful SVG conversion."""
        result = convert_single_svg(sample_file_data, sample_conversion_options)
        
        assert result['success'] is True
        assert result['input_filename'] == 'test.svg'
        assert result['output_filename'] == 'test.pptx'
        assert 'output_path' in result
        assert 'processing_time' in result
        assert 'completed_at' in result
    
    def test_invalid_file_type(self):
        """Test conversion with invalid file type."""
        file_data = {
            'filename': 'test.txt',
            'content': b'not an svg'
        }
        
        with pytest.raises(Exception):  # Should raise ConversionError
            convert_single_svg(file_data)
    
    def test_empty_file(self):
        """Test conversion with empty file."""
        file_data = {
            'filename': 'test.svg',
            'content': b''
        }
        
        with pytest.raises(Exception):  # Should raise ConversionError
            convert_single_svg(file_data)
    
    def test_conversion_with_default_options(self, sample_file_data):
        """Test conversion with default options."""
        result = convert_single_svg(sample_file_data)
        
        assert result['success'] is True
        assert result['conversion_options']['slide_width'] == 10.0
        assert result['conversion_options']['slide_height'] == 7.5


class TestMergePresentations:
    """Test presentation merging task."""
    
    def test_successful_merge_single_pptx(self):
        """Test successful merging to single PPTX."""
        conversion_results = [
            {
                'success': True,
                'input_filename': 'file1.svg',
                'output_filename': 'file1.pptx',
                'output_path': '/tmp/file1.pptx',
                'input_size': 1000,
                'processing_time': 1.0
            },
            {
                'success': True,
                'input_filename': 'file2.svg',
                'output_filename': 'file2.pptx',
                'output_path': '/tmp/file2.pptx',
                'input_size': 2000,
                'processing_time': 2.0
            }
        ]
        
        # Mock file existence
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat.return_value.st_size = 5000
            result = merge_presentations(conversion_results, 'single_pptx')
        
        assert result['success'] is True
        assert result['output_format'] == 'single_pptx'
        assert result['total_files_processed'] == 2
        assert result['failed_files'] == 0
        assert result['total_input_size'] == 3000
        assert result['total_processing_time'] == 3.0
    
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
            result = merge_presentations(conversion_results, 'zip_archive')
        
        assert result['success'] is True
        assert result['output_format'] == 'zip_archive'
        assert result['total_files_processed'] == 1
    
    def test_merge_with_failures(self):
        """Test merging with some failed conversions."""
        conversion_results = [
            {'success': True, 'input_filename': 'file1.svg', 'output_path': '/tmp/file1.pptx'},
            {'success': False, 'input_filename': 'file2.svg', 'error_message': 'Failed'},
            {'success': True, 'input_filename': 'file3.svg', 'output_path': '/tmp/file3.pptx'}
        ]
        
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat.return_value.st_size = 3000
            result = merge_presentations(conversion_results, 'single_pptx')
        
        assert result['success'] is True
        assert result['total_files_processed'] == 2
        assert result['failed_files'] == 1
    
    def test_merge_no_successful_conversions(self):
        """Test merging when all conversions failed."""
        conversion_results = [
            {'success': False, 'error_message': 'Failed 1'},
            {'success': False, 'error_message': 'Failed 2'}
        ]
        
        result = merge_presentations(conversion_results)
        
        assert result['success'] is False
        assert 'error_message' in result


class TestCleanupTempFiles:
    """Test temporary file cleanup task."""
    
    def test_successful_cleanup(self):
        """Test successful file cleanup."""
        # Create temporary files
        temp_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(delete=False) as f:
                temp_files.append(f.name)
        
        try:
            result = cleanup_temp_files(temp_files)
            
            assert result['cleaned_files'] == 3
            assert result['total_requested'] == 3
            assert len(result['errors']) == 0
            
            # Verify files were deleted
            for file_path in temp_files:
                assert not Path(file_path).exists()
                
        finally:
            # Cleanup any remaining files
            for file_path in temp_files:
                Path(file_path).unlink(missing_ok=True)
    
    def test_cleanup_nonexistent_files(self):
        """Test cleanup of non-existent files."""
        fake_files = ['/nonexistent/file1.txt', '/nonexistent/file2.txt']
        
        result = cleanup_temp_files(fake_files)
        
        assert result['cleaned_files'] == 0
        assert result['total_requested'] == 2
        assert len(result['errors']) == 0  # Non-existent files don't cause errors


class TestProcessSvgBatch:
    """Test batch processing workflow."""
    
    def test_batch_processing_workflow(self, sample_svg_content):
        """Test complete batch processing workflow."""
        file_list = [
            {'filename': 'file1.svg', 'content': sample_svg_content},
            {'filename': 'file2.svg', 'content': sample_svg_content}
        ]
        
        conversion_options = {
            'slide_width': 12.0,
            'slide_height': 9.0,
            'output_format': 'single_pptx'
        }
        
        # Since we're using immediate mode, this will execute synchronously
        result = process_svg_batch(file_list, conversion_options)
        
        # In immediate mode, we get the actual result
        assert result is not None
        assert isinstance(result, dict)


class TestExtractAndProcessZip:
    """Test ZIP extraction and processing."""
    
    def test_zip_extraction_and_processing(self, sample_svg_content):
        """Test ZIP file extraction and batch processing."""
        # Create a ZIP file with SVG content
        with tempfile.NamedTemporaryFile() as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w') as zip_file:
                zip_file.writestr('file1.svg', sample_svg_content)
                zip_file.writestr('file2.svg', sample_svg_content)
                zip_file.writestr('readme.txt', b'This should be ignored')
            
            # Read the ZIP content
            temp_zip.seek(0)
            zip_content = temp_zip.read()
        
        conversion_options = {'output_format': 'zip_archive'}
        
        # Process the ZIP (immediate mode returns actual result)
        result = extract_and_process_zip(zip_content, conversion_options)
        
        assert result is not None
        assert isinstance(result, dict)
    
    def test_empty_zip_processing(self):
        """Test processing of ZIP with no SVG files."""
        # Create empty ZIP
        with tempfile.NamedTemporaryFile() as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w') as zip_file:
                zip_file.writestr('readme.txt', b'No SVG files here')
            
            temp_zip.seek(0)
            zip_content = temp_zip.read()
        
        # Should return error result
        result = extract_and_process_zip(zip_content)
        assert result['success'] is False
        assert 'error_message' in result


class TestTaskIntegration:
    """Test task integration and error handling."""
    
    def test_task_error_handling(self, sample_file_data):
        """Test task error handling."""
        # Test with invalid file data
        invalid_data = {'filename': 'test.txt', 'content': b'not svg'}
        
        result = convert_single_svg(invalid_data)
        assert result['success'] is False
        assert 'error_message' in result
    
    def test_task_success_result(self, sample_file_data):
        """Test successful task execution."""
        result = convert_single_svg(sample_file_data)
        
        # Check that final state is success
        assert result['success'] is True
        assert 'output_path' in result
        assert 'processing_time' in result