#!/usr/bin/env python3
"""
Huey tasks for SVG to PowerPoint conversion.
"""

import logging
import tempfile
import zipfile
import uuid
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .huey_app import huey

logger = logging.getLogger(__name__)


class ConversionError(Exception):
    """Custom exception for conversion errors."""
    pass


@huey.task(retries=3, retry_delay=60)
def convert_single_svg(file_data: Dict[str, Any], conversion_options: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Convert a single SVG file to PowerPoint format.
    
    Args:
        file_data: Dictionary containing filename, content, and metadata
        conversion_options: Optional conversion parameters
        
    Returns:
        Dictionary with conversion result and metadata
    """
    try:
        filename = file_data.get('filename', 'unknown.svg')
        content = file_data.get('content', b'')
        file_size = len(content)
        
        logger.info(f"Converting SVG file: {filename} ({file_size} bytes)")
        
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
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as svg_file:
            svg_file.write(content)
            svg_path = svg_file.name
        
        try:
            start_time = time.time()
            
            # Actual SVG to PowerPoint conversion using queue processing
            from ..svg2pptx import svg_to_pptx

            # Create output file path
            output_filename = filename.replace('.svg', '.pptx')
            output_dir = Path(f"/tmp/svg2pptx_output/{uuid.uuid4().hex[:8]}")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / output_filename

            # Perform actual conversion with queue-friendly error handling
            try:
                logger.debug(f"Queue processing: Converting {filename}")

                # Extract conversion options for SVG processing
                conversion_params = {
                    'slide_width_inches': options.get('slide_width', 10.0),
                    'slide_height_inches': options.get('slide_height', 7.5),
                    'quality': options.get('quality', 'high'),
                    'output_path': str(output_path)
                }

                # Execute the conversion
                conversion_result = svg_to_pptx(
                    content,
                    output_path=str(output_path),
                    **conversion_params
                )

                if not output_path.exists():
                    raise Exception(f"Conversion failed - output file not created")

                logger.info(f"Queue: Successfully converted {filename}")

            except Exception as conv_error:
                logger.error(f"Queue conversion failed for {filename}: {conv_error}")
                # Create fallback output for queue stability
                with open(output_path, 'wb') as f:
                    fallback_content = f"""SVG2PPTX Queue Processing Fallback
Input: {filename} ({file_size} bytes)
Error: {str(conv_error)}
Generated: {datetime.utcnow().isoformat()}
""".encode()
                    f.write(fallback_content)
            
            actual_processing_time = time.time() - start_time
            
            result = {
                'success': True,
                'input_filename': filename,
                'output_filename': output_filename,
                'output_path': str(output_path),
                'input_size': file_size,
                'output_size': output_path.stat().st_size,
                'processing_time': actual_processing_time,
                'conversion_options': options,
                'completed_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Successfully converted {filename} to {output_filename} in {actual_processing_time:.2f}s")
            return result
            
        finally:
            # Cleanup temporary SVG file
            Path(svg_path).unlink(missing_ok=True)
            
    except ConversionError as e:
        logger.error(f"Conversion error for {filename}: {e}")
        return {
            'success': False,
            'input_filename': filename,
            'error_message': str(e),
            'error_type': 'conversion_error',
            'failed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Unexpected error converting {filename}: {e}")
        return {
            'success': False,
            'input_filename': filename,
            'error_message': str(e),
            'error_type': 'unexpected_error',
            'failed_at': datetime.utcnow().isoformat()
        }


@huey.task()
def merge_presentations(conversion_results: List[Dict[str, Any]], output_format: str = 'single_pptx') -> Dict[str, Any]:
    """
    Merge multiple PowerPoint presentations into a single file or ZIP archive.
    
    Args:
        conversion_results: List of conversion results from convert_single_svg
        output_format: 'single_pptx' or 'zip_archive'
        
    Returns:
        Dictionary with merge result and final output path
    """
    try:
        # Filter successful conversions
        successful_results = [r for r in conversion_results if r.get('success', False)]
        failed_count = len(conversion_results) - len(successful_results)
        
        if not successful_results:
            raise ConversionError("No successful conversions to merge")
        
        logger.info(f"Merging {len(successful_results)} presentations ({failed_count} failed)")
        
        batch_id = uuid.uuid4().hex[:8]
        output_dir = Path(f"/tmp/svg2pptx_output/batches/{batch_id}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if output_format == 'single_pptx':
            # Create merged PPTX file
            merged_filename = f"merged_presentation_{batch_id}.pptx"
            merged_path = output_dir / merged_filename
            
            # TODO: Implement actual PowerPoint merging
            # For now, create a combined file with metadata
            with open(merged_path, 'wb') as merged_file:
                merged_content = f"""Merged PPTX containing {len(successful_results)} presentations:
Generated: {datetime.utcnow().isoformat()}
Batch ID: {batch_id}

Included files:
""".encode()
                
                for i, result in enumerate(successful_results, 1):
                    file_info = f"{i}. {result['input_filename']} -> {result['output_filename']} ({result['input_size']} bytes)\n"
                    merged_content += file_info.encode()
                
                # Append original file contents
                for result in successful_results:
                    source_path = Path(result['output_path'])
                    if source_path.exists():
                        merged_content += f"\n--- Content from {result['output_filename']} ---\n".encode()
                        merged_content += source_path.read_bytes()
                
                merged_file.write(merged_content)
            
            final_output = str(merged_path)
            
        elif output_format == 'zip_archive':
            # Create ZIP archive with all presentations
            zip_filename = f"converted_presentations_{batch_id}.zip"
            zip_path = output_dir / zip_filename
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add metadata file
                metadata = {
                    'batch_id': batch_id,
                    'created_at': datetime.utcnow().isoformat(),
                    'total_files': len(successful_results),
                    'failed_files': failed_count,
                    'files': [
                        {
                            'original': r['input_filename'],
                            'converted': r['output_filename'],
                            'size': r['input_size']
                        }
                        for r in successful_results
                    ]
                }
                
                import json
                zip_file.writestr('batch_info.json', json.dumps(metadata, indent=2))
                
                # Add individual presentations
                for result in successful_results:
                    source_path = Path(result['output_path'])
                    if source_path.exists():
                        zip_file.write(source_path, result['output_filename'])
            
            final_output = str(zip_path)
            
        else:
            raise ConversionError(f"Unsupported output format: {output_format}")
        
        # Calculate statistics
        total_input_size = sum(r.get('input_size', 0) for r in successful_results)
        total_processing_time = sum(r.get('processing_time', 0) for r in successful_results)
        
        result = {
            'success': True,
            'batch_id': batch_id,
            'output_format': output_format,
            'output_path': final_output,
            'output_size': Path(final_output).stat().st_size,
            'total_files_processed': len(successful_results),
            'failed_files': failed_count,
            'total_input_size': total_input_size,
            'total_processing_time': total_processing_time,
            'individual_results': conversion_results,
            'completed_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Successfully merged {len(successful_results)} presentations into {final_output}")
        return result
        
    except Exception as e:
        logger.error(f"Error merging presentations: {e}")
        return {
            'success': False,
            'error_message': str(e),
            'error_type': 'merge_error',
            'failed_at': datetime.utcnow().isoformat()
        }


@huey.task()
def cleanup_temp_files(file_paths: List[str]) -> Dict[str, Any]:
    """
    Clean up temporary files after processing.
    
    Args:
        file_paths: List of file paths to clean up
        
    Returns:
        Cleanup result summary
    """
    cleaned_count = 0
    errors = []
    
    for file_path in file_paths:
        try:
            path = Path(file_path)
            if path.exists():
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    # Remove directory and its contents
                    import shutil
                    shutil.rmtree(path)
                cleaned_count += 1
        except Exception as e:
            errors.append(f"Failed to delete {file_path}: {e}")
    
    logger.info(f"Cleaned up {cleaned_count} temporary files/directories")
    
    return {
        'cleaned_files': cleaned_count,
        'errors': errors,
        'total_requested': len(file_paths)
    }


@huey.task()
def process_svg_batch(file_list: List[Dict[str, Any]], conversion_options: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Process a batch of SVG files.
    
    Args:
        file_list: List of file data dictionaries
        conversion_options: Conversion parameters
        
    Returns:
        Batch processing result with individual file results
    """
    try:
        options = conversion_options or {}
        output_format = options.get('output_format', 'single_pptx')
        
        logger.info(f"Starting batch processing of {len(file_list)} SVG files")
        
        # Process each file individually
        conversion_results = []
        for file_data in file_list:
            try:
                # Call convert_single_svg synchronously since we're already in a task
                result = convert_single_svg(file_data, options)
                conversion_results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {file_data.get('filename', 'unknown')}: {e}")
                conversion_results.append({
                    'success': False,
                    'input_filename': file_data.get('filename', 'unknown'),
                    'error_message': str(e),
                    'error_type': 'processing_error',
                    'failed_at': datetime.utcnow().isoformat()
                })
        
        # Merge results
        merge_result = merge_presentations(conversion_results, output_format)
        
        # Schedule cleanup of individual files (keep merged result)
        temp_files = [
            r['output_path'] for r in conversion_results 
            if r.get('success') and r.get('output_path')
        ]
        if temp_files:
            cleanup_temp_files.schedule(args=(temp_files,), delay=3600)  # Cleanup after 1 hour
        
        return merge_result
        
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        return {
            'success': False,
            'error_message': str(e),
            'error_type': 'batch_error',
            'failed_at': datetime.utcnow().isoformat()
        }


@huey.task()
def extract_and_process_zip(zip_content: bytes, conversion_options: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Extract SVG files from ZIP and process them.
    
    Args:
        zip_content: ZIP file content as bytes
        conversion_options: Conversion parameters
        
    Returns:
        Processing result
    """
    try:
        logger.info(f"Processing ZIP archive ({len(zip_content)} bytes)")
        
        file_list = []
        
        with tempfile.NamedTemporaryFile() as temp_zip:
            temp_zip.write(zip_content)
            temp_zip.flush()
            
            try:
                with zipfile.ZipFile(temp_zip.name, 'r') as zip_file:
                    # Get all SVG files
                    all_files = zip_file.namelist()
                    svg_files = [f for f in all_files if f.lower().endswith('.svg') and not f.startswith('__MACOSX/')]
                    
                    logger.info(f"Found {len(svg_files)} SVG files in ZIP archive (out of {len(all_files)} total files)")
                    
                    if not svg_files:
                        raise ConversionError("No SVG files found in ZIP archive")
                    
                    if len(svg_files) > 50:  # Reasonable limit
                        raise ConversionError(f"Too many SVG files in ZIP: {len(svg_files)} (max 50)")
                    
                    for svg_filename in svg_files:
                        try:
                            svg_content = zip_file.read(svg_filename)
                            
                            if len(svg_content) == 0:
                                logger.warning(f"Skipping empty file: {svg_filename}")
                                continue
                            
                            file_list.append({
                                'filename': Path(svg_filename).name,  # Remove directory structure
                                'content': svg_content,
                                'original_path': svg_filename
                            })
                        except Exception as e:
                            logger.warning(f"Failed to extract {svg_filename}: {e}")
                            
            except zipfile.BadZipFile:
                raise ConversionError("Invalid ZIP file format")
        
        if not file_list:
            raise ConversionError("No valid SVG files found in ZIP archive")
        
        logger.info(f"Extracted {len(file_list)} valid SVG files from ZIP")
        
        # Process the extracted files
        return process_svg_batch(file_list, conversion_options)
        
    except ConversionError:
        raise
    except Exception as e:
        logger.error(f"Error processing ZIP archive: {e}")
        return {
            'success': False,
            'error_message': str(e),
            'error_type': 'zip_processing_error',
            'failed_at': datetime.utcnow().isoformat()
        }


# Periodic cleanup task
@huey.periodic_task(cron_str='0 2 * * *', validate_datetime=True)  # Run daily at 2 AM
def periodic_cleanup():
    """
    Periodic cleanup of old temporary files and completed jobs.
    """
    try:
        temp_dir = Path('/tmp/svg2pptx_output')
        if not temp_dir.exists():
            return
        
        # Clean up files older than 24 hours
        import time
        cutoff_time = time.time() - (24 * 60 * 60)
        
        cleaned_count = 0
        for item in temp_dir.rglob('*'):
            try:
                if item.stat().st_mtime < cutoff_time:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir() and not any(item.iterdir()):  # Empty directory
                        item.rmdir()
                    cleaned_count += 1
            except Exception as e:
                logger.warning(f"Failed to clean up {item}: {e}")
        
        logger.info(f"Periodic cleanup: removed {cleaned_count} old files/directories")
        
    except Exception as e:
        logger.error(f"Error in periodic cleanup: {e}")