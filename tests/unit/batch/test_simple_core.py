#!/usr/bin/env python3
"""
Tests for simple mode core functionality without external dependencies.
"""

import pytest
import tempfile
import uuid
from pathlib import Path
from datetime import datetime


class ConversionError(Exception):
    """Custom exception for conversion errors."""
    pass


def convert_single_svg_sync(file_data: dict, conversion_options: dict = None) -> dict:
    """
    Convert a single SVG file synchronously (mock implementation).
    
    Args:
        file_data: Dictionary containing filename, content, and metadata
        conversion_options: Optional conversion parameters
        
    Returns:
        Dictionary with conversion result
    """
    try:
        filename = file_data.get('filename', 'unknown.svg')
        content = file_data.get('content', b'')
        file_size = len(content)
        
        # Validate input
        if not filename.lower().endswith('.svg'):
            raise ConversionError(f"Invalid file type: {filename}")
        
        if file_size == 0:
            raise ConversionError(f"Empty file: {filename}")
        
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            raise ConversionError(f"File too large: {filename}")
        
        # Set default conversion options
        options = conversion_options or {}
        slide_width = options.get('slide_width', 10.0)
        slide_height = options.get('slide_height', 7.5)
        quality = options.get('quality', 'high')
        
        # Create output file path
        output_filename = filename.replace('.svg', '.pptx')
        output_dir = Path(f"/tmp/svg2pptx_output/{uuid.uuid4().hex[:8]}")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_filename
        
        # Create a mock PPTX file
        with open(output_path, 'wb') as f:
            mock_content = f"""Mock PPTX for {filename}
Original size: {file_size} bytes
Conversion options: {options}
Generated at: {datetime.utcnow().isoformat()}
Slide dimensions: {slide_width} x {slide_height} inches
Quality: {quality}
""".encode()
            f.write(mock_content)
        
        result = {
            'success': True,
            'input_filename': filename,
            'output_filename': output_filename,
            'output_path': str(output_path),
            'input_size': file_size,
            'output_size': output_path.stat().st_size,
            'conversion_options': options,
            'completed_at': datetime.utcnow().isoformat()
        }
        
        return result
        
    except ConversionError as e:
        return {
            'success': False,
            'input_filename': filename,
            'error_message': str(e),
            'error_type': 'conversion_error',
            'failed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'input_filename': filename,
            'error_message': str(e),
            'error_type': 'unexpected_error',
            'failed_at': datetime.utcnow().isoformat()
        }


def merge_presentations_sync(conversion_results: list, output_format: str = 'single_pptx') -> dict:
    """
    Merge multiple PowerPoint presentations synchronously.
    
    Args:
        conversion_results: List of conversion results
        output_format: 'single_pptx' or 'zip_archive'
        
    Returns:
        Dictionary with merge result
    """
    try:
        # Filter successful conversions
        successful_results = [r for r in conversion_results if r.get('success', False)]
        failed_count = len(conversion_results) - len(successful_results)
        
        if not successful_results:
            raise ConversionError("No successful conversions to merge")
        
        job_id = uuid.uuid4().hex[:8]
        output_dir = Path(f"/tmp/svg2pptx_output/simple/{job_id}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if output_format == 'single_pptx':
            # Create merged PPTX file
            merged_filename = f"merged_presentation_{job_id}.pptx"
            merged_path = output_dir / merged_filename
            
            with open(merged_path, 'wb') as merged_file:
                merged_content = f"""Merged PPTX containing {len(successful_results)} presentations:
Generated: {datetime.utcnow().isoformat()}
Job ID: {job_id}

Included files:
""".encode()
                
                for i, result in enumerate(successful_results, 1):
                    file_info = f"{i}. {result['input_filename']} -> {result['output_filename']} ({result['input_size']} bytes)\n"
                    merged_content += file_info.encode()
                
                merged_file.write(merged_content)
            
            final_output = str(merged_path)
            
        else:
            raise ConversionError(f"Unsupported output format: {output_format}")
        
        # Calculate statistics
        total_input_size = sum(r.get('input_size', 0) for r in successful_results)
        
        result = {
            'success': True,
            'job_id': job_id,
            'output_format': output_format,
            'output_path': final_output,
            'output_size': Path(final_output).stat().st_size,
            'total_files_processed': len(successful_results),
            'failed_files': failed_count,
            'total_input_size': total_input_size,
            'individual_results': conversion_results,
            'completed_at': datetime.utcnow().isoformat()
        }
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error_message': str(e),
            'error_type': 'merge_error',
            'failed_at': datetime.utcnow().isoformat()
        }


@pytest.mark.integration
class TestSimpleCoreConversion:
    """Test core conversion functionality without external dependencies."""
    
    def test_successful_conversion(self):
        """Test successful SVG conversion."""
        file_data = {
            'filename': 'test.svg',
            'content': b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>'
        }
        
        result = convert_single_svg_sync(file_data)
        
        assert result['success'] is True
        assert result['input_filename'] == 'test.svg'
        assert result['output_filename'] == 'test.pptx'
        assert 'output_path' in result
        assert 'completed_at' in result
        assert result['input_size'] == len(file_data['content'])
        
        # Verify output file was created
        output_path = Path(result['output_path'])
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        
        # Cleanup
        output_path.unlink(missing_ok=True)
        output_path.parent.rmdir()
    
    def test_conversion_with_options(self):
        """Test conversion with custom options."""
        file_data = {
            'filename': 'test.svg',
            'content': b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>'
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
        
        # Cleanup
        output_path = Path(result['output_path'])
        output_path.unlink(missing_ok=True)
        output_path.parent.rmdir()
    
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


@pytest.mark.integration
class TestSimpleCoreMerging:
    """Test core merging functionality without external dependencies."""
    
    def test_successful_merge(self):
        """Test successful merging of presentations."""
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
        
        result = merge_presentations_sync(conversion_results, 'single_pptx')
        
        assert result['success'] is True
        assert result['output_format'] == 'single_pptx'
        assert result['total_files_processed'] == 2
        assert result['failed_files'] == 0
        assert result['total_input_size'] == 3000
        assert 'job_id' in result
        
        # Verify output file was created
        output_path = Path(result['output_path'])
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        
        # Cleanup
        output_path.unlink(missing_ok=True)
        output_path.parent.rmdir()
    
    def test_merge_with_failures(self):
        """Test merging with some failed conversions."""
        conversion_results = [
            {'success': True, 'input_filename': 'file1.svg', 'output_filename': 'file1.pptx', 'output_path': '/tmp/file1.pptx', 'input_size': 1000},
            {'success': False, 'input_filename': 'file2.svg', 'error_message': 'Failed'},
            {'success': True, 'input_filename': 'file3.svg', 'output_filename': 'file3.pptx', 'output_path': '/tmp/file3.pptx', 'input_size': 2000}
        ]
        
        result = merge_presentations_sync(conversion_results, 'single_pptx')
        
        assert result['success'] is True
        assert result['total_files_processed'] == 2
        assert result['failed_files'] == 1
        
        # Cleanup
        output_path = Path(result['output_path'])
        output_path.unlink(missing_ok=True)
        output_path.parent.rmdir()
    
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
            {'success': True, 'input_filename': 'file1.svg', 'output_filename': 'file1.pptx', 'output_path': '/tmp/file1.pptx', 'input_size': 1000}
        ]
        
        result = merge_presentations_sync(conversion_results, 'invalid_format')
        
        assert result['success'] is False
        assert 'Unsupported output format' in result['error_message']


@pytest.mark.integration
class TestWorkflowIntegration:
    """Test complete workflow integration."""
    
    def test_conversion_and_merge_workflow(self):
        """Test complete conversion and merge workflow."""
        # Step 1: Convert multiple files
        file_list = [
            {'filename': 'file1.svg', 'content': b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>'},
            {'filename': 'file2.svg', 'content': b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="50"/></svg>'}
        ]
        
        conversion_results = []
        for file_data in file_list:
            result = convert_single_svg_sync(file_data)
            conversion_results.append(result)
        
        # Verify all conversions succeeded
        assert all(r['success'] for r in conversion_results)
        assert len(conversion_results) == 2
        
        # Step 2: Merge results
        merge_result = merge_presentations_sync(conversion_results, 'single_pptx')
        
        assert merge_result['success'] is True
        assert merge_result['total_files_processed'] == 2
        assert merge_result['failed_files'] == 0
        
        # Verify final output
        final_output = Path(merge_result['output_path'])
        assert final_output.exists()
        assert final_output.stat().st_size > 0
        
        # Cleanup
        for result in conversion_results:
            if result['success']:
                Path(result['output_path']).unlink(missing_ok=True)
                Path(result['output_path']).parent.rmdir()
        
        final_output.unlink(missing_ok=True)
        final_output.parent.rmdir()
    
    def test_partial_failure_workflow(self):
        """Test workflow with partial failures."""
        # Include one invalid file
        file_list = [
            {'filename': 'valid.svg', 'content': b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>'},
            {'filename': 'invalid.txt', 'content': b'not svg content'}
        ]
        
        conversion_results = []
        for file_data in file_list:
            result = convert_single_svg_sync(file_data)
            conversion_results.append(result)
        
        # Verify mixed results
        assert conversion_results[0]['success'] is True
        assert conversion_results[1]['success'] is False
        
        # Merge should still work with partial failures
        merge_result = merge_presentations_sync(conversion_results, 'single_pptx')
        
        assert merge_result['success'] is True
        assert merge_result['total_files_processed'] == 1
        assert merge_result['failed_files'] == 1
        
        # Cleanup successful conversion
        if conversion_results[0]['success']:
            output_path = Path(conversion_results[0]['output_path'])
            output_path.unlink(missing_ok=True)
            output_path.parent.rmdir()
        
        # Cleanup merge result
        final_output = Path(merge_result['output_path'])
        final_output.unlink(missing_ok=True)
        final_output.parent.rmdir()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])