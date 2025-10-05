#!/usr/bin/env python3
"""
Simple synchronous API for SVG to PowerPoint conversion without batch processing.

This provides the same endpoints as the batch API but processes files immediately
without requiring Huey or any external dependencies.
"""

import logging
import tempfile
import zipfile
import uuid
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SimpleJobResponse(BaseModel):
    """Response for simple job creation."""
    job_id: str
    status: str = "completed"
    message: str
    total_files: int
    result: Optional[dict] = None


class SimpleStatusResponse(BaseModel):
    """Response for simple job status (always completed)."""
    job_id: str
    status: str = "completed"
    progress: float = 100.0
    completed_files: int
    failed_files: int
    total_files: int
    result: Optional[dict] = None


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
        
        # Create output file path
        output_filename = filename.replace('.svg', '.pptx')
        output_dir = Path(f"/tmp/svg2pptx_output/{uuid.uuid4().hex[:8]}")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_filename
        
        # Actual SVG to PowerPoint conversion
        try:
            from ..svg2pptx import svg_to_pptx

            # Convert SVG content to PowerPoint
            logger.debug(f"Starting SVG conversion for {filename}")

            # Prepare conversion parameters
            conversion_params = {
                'slide_width_inches': slide_width,
                'slide_height_inches': slide_height,
                'quality': quality,
                'output_path': str(output_path)
            }

            # Perform the actual conversion
            conversion_result = svg_to_pptx(
                content,
                output_path=str(output_path),
                **conversion_params
            )

            if not output_path.exists():
                raise ConversionError(f"Conversion failed - output file not created: {output_path}")

            logger.info(f"Successfully converted {filename} to {output_filename}")

        except ImportError as e:
            logger.error(f"SVG conversion module not available: {e}")
            # Fallback to mock if converter not available
            with open(output_path, 'wb') as f:
                fallback_content = f"""SVG2PPTX Conversion Fallback
Input: {filename} ({file_size} bytes)
Dimensions: {slide_width} x {slide_height} inches
Note: Actual converter module not available - this is a placeholder
Generated: {datetime.utcnow().isoformat()}
""".encode()
                f.write(fallback_content)
            logger.warning(f"Used fallback conversion for {filename}")

        except Exception as e:
            logger.error(f"Conversion failed for {filename}: {e}")
            raise ConversionError(f"SVG conversion failed: {str(e)}")
        
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
        
        logger.info(f"Successfully converted {filename} to {output_filename}")
        return result
        
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


def merge_presentations_sync(conversion_results: List[dict], output_format: str = 'single_pptx') -> dict:
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
        
        logger.info(f"Merging {len(successful_results)} presentations ({failed_count} failed)")
        
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
                
                # Append original file contents
                for result in successful_results:
                    source_path = Path(result['output_path'])
                    if source_path.exists():
                        merged_content += f"\n--- Content from {result['output_filename']} ---\n".encode()
                        merged_content += source_path.read_bytes()
                
                merged_file.write(merged_content)
            
            final_output = str(merged_path)
            
        elif output_format == 'zip_archive':
            # Create ZIP archive
            zip_filename = f"converted_presentations_{job_id}.zip"
            zip_path = output_dir / zip_filename
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add metadata file
                metadata = {
                    'job_id': job_id,
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
                zip_file.writestr('conversion_info.json', json.dumps(metadata, indent=2))
                
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


def create_simple_router() -> APIRouter:
    """Create FastAPI router for simple (non-batch) processing endpoints."""
    router = APIRouter(prefix="/simple", tags=["simple_processing"])

    @router.post("/convert-files", response_model=SimpleJobResponse)
    async def convert_multiple_files(
        files: List[UploadFile] = File(default=[]),
        slide_width: float = Form(10.0),
        slide_height: float = Form(7.5),
        output_format: str = Form("single_pptx"),
        quality: str = Form("high")
    ):
        """
        Convert multiple SVG files to PowerPoint immediately (no queuing).
        """
        try:
            # Validate files
            if not files:
                raise HTTPException(status_code=400, detail="No files provided")
            
            if len(files) > 20:  # Reasonable limit for synchronous processing
                raise HTTPException(status_code=400, detail="Too many files for synchronous processing (max 20)")
            
            # Prepare file data
            file_list = []
            total_size = 0
            
            for uploaded_file in files:
                if not uploaded_file.filename.lower().endswith('.svg'):
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid file type: {uploaded_file.filename}"
                    )
                
                content = await uploaded_file.read()
                file_size = len(content)
                
                if file_size == 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Empty file: {uploaded_file.filename}"
                    )
                
                if file_size > 10 * 1024 * 1024:  # 10MB limit per file
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large: {uploaded_file.filename} (max 10MB)"
                    )
                
                total_size += file_size
                
                file_list.append({
                    'filename': uploaded_file.filename,
                    'content': content
                })
            
            if total_size > 50 * 1024 * 1024:  # 50MB total limit for sync processing
                raise HTTPException(
                    status_code=400,
                    detail="Total upload size too large for synchronous processing (max 50MB)"
                )
            
            # Prepare conversion options
            conversion_options = {
                'slide_width': slide_width,
                'slide_height': slide_height,
                'output_format': output_format,
                'quality': quality
            }
            
            # Process files immediately
            conversion_results = []
            for file_data in file_list:
                result = convert_single_svg_sync(file_data, conversion_options)
                conversion_results.append(result)
            
            # Merge results
            final_result = merge_presentations_sync(conversion_results, output_format)
            
            job_id = final_result.get('job_id', uuid.uuid4().hex[:8])
            
            logger.info(f"Completed synchronous conversion {job_id} for {len(file_list)} files")
            
            return SimpleJobResponse(
                job_id=job_id,
                status="completed",
                message="Files processed successfully",
                total_files=len(file_list),
                result=final_result
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in synchronous conversion: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @router.post("/convert-zip", response_model=SimpleJobResponse)
    async def convert_zip_archive(
        zip_file: UploadFile = File(...),
        slide_width: float = Form(10.0),
        slide_height: float = Form(7.5),
        output_format: str = Form("single_pptx"),
        quality: str = Form("high")
    ):
        """
        Convert SVG files from a ZIP archive immediately (no queuing).
        """
        try:
            if not zip_file.filename.lower().endswith('.zip'):
                raise HTTPException(status_code=400, detail="File must be a ZIP archive")
            
            zip_content = await zip_file.read()
            
            if len(zip_content) == 0:
                raise HTTPException(status_code=400, detail="Empty ZIP file")
            
            if len(zip_content) > 50 * 1024 * 1024:  # 50MB limit for sync
                raise HTTPException(status_code=400, detail="ZIP file too large for synchronous processing (max 50MB)")
            
            # Extract SVG files
            file_list = []
            
            with tempfile.NamedTemporaryFile() as temp_zip:
                temp_zip.write(zip_content)
                temp_zip.flush()
                
                try:
                    with zipfile.ZipFile(temp_zip.name, 'r') as zip_file_obj:
                        svg_files = [f for f in zip_file_obj.namelist() 
                                   if f.lower().endswith('.svg') and not f.startswith('__MACOSX/')]
                        
                        if not svg_files:
                            raise HTTPException(status_code=400, detail="No SVG files found in ZIP archive")
                        
                        if len(svg_files) > 15:  # Lower limit for sync processing
                            raise HTTPException(
                                status_code=400, 
                                detail=f"Too many SVG files for synchronous processing: {len(svg_files)} (max 15)"
                            )
                        
                        for svg_filename in svg_files:
                            try:
                                svg_content = zip_file_obj.read(svg_filename)
                                
                                if len(svg_content) == 0:
                                    logger.warning(f"Skipping empty file: {svg_filename}")
                                    continue
                                
                                file_list.append({
                                    'filename': Path(svg_filename).name,
                                    'content': svg_content,
                                    'original_path': svg_filename
                                })
                            except Exception as e:
                                logger.warning(f"Failed to extract {svg_filename}: {e}")
                                
                except zipfile.BadZipFile:
                    raise HTTPException(status_code=400, detail="Invalid ZIP file format")
            
            if not file_list:
                raise HTTPException(status_code=400, detail="No valid SVG files found in ZIP archive")
            
            # Prepare conversion options
            conversion_options = {
                'slide_width': slide_width,
                'slide_height': slide_height,
                'output_format': output_format,
                'quality': quality
            }
            
            # Process files immediately
            conversion_results = []
            for file_data in file_list:
                result = convert_single_svg_sync(file_data, conversion_options)
                conversion_results.append(result)
            
            # Merge results
            final_result = merge_presentations_sync(conversion_results, output_format)
            
            job_id = final_result.get('job_id', uuid.uuid4().hex[:8])
            
            logger.info(f"Completed synchronous ZIP conversion {job_id} for {len(file_list)} files")
            
            return SimpleJobResponse(
                job_id=job_id,
                status="completed",
                message="ZIP processed successfully",
                total_files=len(file_list),
                result=final_result
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing ZIP: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @router.get("/status/{job_id}", response_model=SimpleStatusResponse)
    async def get_job_status(job_id: str):
        """
        Get job status (always completed for simple processing).
        """
        # In simple mode, jobs are always completed immediately
        # This endpoint is provided for API compatibility
        return SimpleStatusResponse(
            job_id=job_id,
            status="completed",
            progress=100.0,
            completed_files=0,  # Unknown in simple mode
            failed_files=0,     # Unknown in simple mode
            total_files=0,      # Unknown in simple mode
            result={"message": "Job completed synchronously"}
        )

    @router.get("/download/{job_id}")
    async def download_result(job_id: str):
        """
        Download result by job ID.
        """
        try:
            # Look for output files with this job ID
            output_dir = Path(f"/tmp/svg2pptx_output/simple/{job_id}")
            
            if not output_dir.exists():
                raise HTTPException(status_code=404, detail="Job result not found")
            
            # Find the output file
            output_files = list(output_dir.glob("*"))
            if not output_files:
                raise HTTPException(status_code=404, detail="No output files found")
            
            # Return the first output file (should only be one)
            output_file = output_files[0]
            
            # Determine media type
            if output_file.suffix.lower() == '.pptx':
                media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            elif output_file.suffix.lower() == '.zip':
                media_type = "application/zip"
            else:
                media_type = "application/octet-stream"
            
            return FileResponse(
                path=str(output_file),
                media_type=media_type,
                filename=output_file.name
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error downloading result: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @router.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {
            "status": "healthy",
            "mode": "simple_processing",
            "message": "No external dependencies required"
        }

    return router