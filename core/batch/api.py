#!/usr/bin/env python3
"""
FastAPI endpoints for Huey-based batch SVG to PowerPoint conversion.
"""

import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .huey_app import huey
from .simple_api import convert_single_svg_sync, merge_presentations_sync
from .tasks import cleanup_temp_files, extract_and_process_zip, process_svg_batch

logger = logging.getLogger(__name__)


class BatchJobResponse(BaseModel):
    """Response for batch job creation."""
    batch_id: str
    status: str
    message: str
    total_files: int


class JobStatusResponse(BaseModel):
    """Response for job status queries."""
    batch_id: str
    status: str
    progress: float
    current_step: str | None = None
    completed_files: int = 0
    failed_files: int = 0
    total_files: int = 0
    result: dict | None = None
    error_message: str | None = None


class ConversionOptions(BaseModel):
    """Options for SVG to PowerPoint conversion."""
    slide_width: float = Field(default=10.0, ge=1.0, le=50.0)
    slide_height: float = Field(default=7.5, ge=1.0, le=50.0)
    output_format: str = Field(default="single_pptx", pattern="^(single_pptx|zip_archive)$")
    quality: str = Field(default="high", pattern="^(low|medium|high)$")


def create_batch_router() -> APIRouter:
    """Create FastAPI router for batch processing endpoints."""
    router = APIRouter(prefix="/batch", tags=["batch_processing"])

    # Add simple mode endpoints (synchronous processing without Huey)
    @router.post("/simple/convert-files")
    async def simple_convert_files(
        files: list[UploadFile] = File(...),
        slide_width: float = Form(10.0),
        slide_height: float = Form(7.5),
        output_format: str = Form("single_pptx"),
        quality: str = Form("high"),
    ):
        """Convert multiple SVG files synchronously (no queueing)."""
        try:
            # Validate files (similar to batch but with lower limits for sync processing)
            if not files:
                raise HTTPException(status_code=400, detail="No files provided")
            
            if len(files) > 20:  # Lower limit for synchronous processing
                raise HTTPException(status_code=400, detail="Too many files for synchronous processing (max 20)")
            
            # Prepare file data
            file_list = []
            total_size = 0
            
            for uploaded_file in files:
                if not uploaded_file.filename.lower().endswith('.svg'):
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid file type: {uploaded_file.filename}",
                    )
                
                content = await uploaded_file.read()
                file_size = len(content)
                
                if file_size == 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Empty file: {uploaded_file.filename}",
                    )
                
                if file_size > 10 * 1024 * 1024:  # 10MB limit per file
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large: {uploaded_file.filename} (max 10MB)",
                    )
                
                total_size += file_size
                
                file_list.append({
                    'filename': uploaded_file.filename,
                    'content': content,
                })
            
            if total_size > 50 * 1024 * 1024:  # 50MB total limit for sync processing
                raise HTTPException(
                    status_code=400,
                    detail="Total upload size too large for synchronous processing (max 50MB)",
                )
            
            # Prepare conversion options
            conversion_options = {
                'slide_width': slide_width,
                'slide_height': slide_height,
                'output_format': output_format,
                'quality': quality,
            }
            
            # Process files immediately (synchronously)
            conversion_results = []
            for file_data in file_list:
                result = convert_single_svg_sync(file_data, conversion_options)
                conversion_results.append(result)
            
            # Merge results
            final_result = merge_presentations_sync(conversion_results, output_format)
            
            import uuid
            job_id = final_result.get('job_id', uuid.uuid4().hex[:8])
            
            logger.info(f"Completed synchronous conversion {job_id} for {len(file_list)} files")
            
            return {
                "job_id": job_id,
                "status": "completed",
                "message": "Files processed successfully",
                "total_files": len(file_list),
                "result": final_result,
                "mode": "simple",
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in synchronous conversion: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @router.get("/simple/status/{job_id}")
    async def simple_job_status(job_id: str):
        """Get job status (always completed for simple processing)."""
        # In simple mode, jobs are always completed immediately
        # This endpoint is provided for API compatibility
        return {
            "job_id": job_id,
            "status": "completed",
            "progress": 100.0,
            "completed_files": 0,  # Unknown in simple mode
            "failed_files": 0,     # Unknown in simple mode
            "total_files": 0,      # Unknown in simple mode
            "result": {"message": "Job completed synchronously"},
            "mode": "simple",
        }

    @router.get("/simple/download/{job_id}")
    async def simple_download_result(job_id: str):
        """Download result by job ID (simple mode)."""
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
                filename=output_file.name,
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error downloading result: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @router.get("/health")
    async def health_check():
        """Health check endpoint showing both modes."""
        health_info = {
            "status": "healthy",
            "modes": {
                "batch": "Available (requires Huey worker)",
                "simple": "Available (synchronous processing)",
            },
            "endpoints": {
                "batch_mode": "/batch/convert-files, /batch/status/{id}, /batch/download/{id}",
                "simple_mode": "/batch/simple/convert-files, /batch/simple/status/{id}, /batch/simple/download/{id}",
            },
        }
        
        # Check Huey status
        try:
            from .huey_app import DB_PATH
            health_info["huey_database"] = str(DB_PATH)
            health_info["huey_available"] = DB_PATH.parent.exists()
        except Exception as e:
            health_info["huey_error"] = str(e)
        
        return health_info

    @router.post("/convert-files", response_model=BatchJobResponse)
    async def convert_multiple_files(
        files: list[UploadFile] = File(...),
        slide_width: float = Form(10.0),
        slide_height: float = Form(7.5),
        output_format: str = Form("single_pptx"),
        quality: str = Form("high"),
    ):
        """
        Convert multiple SVG files to PowerPoint.
        """
        try:
            # Validate files
            if not files:
                raise HTTPException(status_code=400, detail="No files provided")
            
            if len(files) > 50:  # Reasonable limit
                raise HTTPException(status_code=400, detail="Too many files (max 50)")
            
            # Prepare file data
            file_list = []
            total_size = 0
            
            for uploaded_file in files:
                if not uploaded_file.filename.lower().endswith('.svg'):
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid file type: {uploaded_file.filename}",
                    )
                
                content = await uploaded_file.read()
                file_size = len(content)
                
                if file_size == 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Empty file: {uploaded_file.filename}",
                    )
                
                if file_size > 10 * 1024 * 1024:  # 10MB limit per file
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large: {uploaded_file.filename} (max 10MB)",
                    )
                
                total_size += file_size
                
                file_list.append({
                    'filename': uploaded_file.filename,
                    'content': content,
                })
            
            if total_size > 100 * 1024 * 1024:  # 100MB total limit
                raise HTTPException(
                    status_code=400,
                    detail="Total upload size too large (max 100MB)",
                )
            
            # Prepare conversion options
            conversion_options = {
                'slide_width': slide_width,
                'slide_height': slide_height,
                'output_format': output_format,
                'quality': quality,
            }
            
            # Start batch processing with Huey
            task = process_svg_batch(file_list, conversion_options)
            batch_id = task.id
            
            logger.info(f"Started batch conversion {batch_id} for {len(file_list)} files")
            
            return BatchJobResponse(
                batch_id=batch_id,
                status="PENDING",
                message="Batch processing started",
                total_files=len(file_list),
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error starting batch conversion: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @router.post("/convert-zip", response_model=BatchJobResponse)
    async def convert_zip_archive(
        zip_file: UploadFile = File(...),
        slide_width: float = Form(10.0),
        slide_height: float = Form(7.5),
        output_format: str = Form("single_pptx"),
        quality: str = Form("high"),
    ):
        """
        Convert SVG files from a ZIP archive to PowerPoint.
        """
        try:
            if not zip_file.filename.lower().endswith('.zip'):
                raise HTTPException(status_code=400, detail="File must be a ZIP archive")
            
            zip_content = await zip_file.read()
            
            if len(zip_content) == 0:
                raise HTTPException(status_code=400, detail="Empty ZIP file")
            
            if len(zip_content) > 100 * 1024 * 1024:  # 100MB limit
                raise HTTPException(status_code=400, detail="ZIP file too large (max 100MB)")
            
            # Prepare conversion options
            conversion_options = {
                'slide_width': slide_width,
                'slide_height': slide_height,
                'output_format': output_format,
                'quality': quality,
            }
            
            # Start ZIP processing with Huey
            task = extract_and_process_zip(zip_content, conversion_options)
            batch_id = task.id
            
            logger.info(f"Started ZIP batch conversion {batch_id}")
            
            return BatchJobResponse(
                batch_id=batch_id,
                status="PENDING",
                message="ZIP processing started",
                total_files=0,  # Will be determined after extraction
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing ZIP upload: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @router.get("/status/{batch_id}", response_model=JobStatusResponse)
    async def get_batch_status(batch_id: str):
        """
        Get the status of a batch processing job.
        """
        try:
            # Get task from Huey
            task = huey.get(batch_id)
            
            if task is None:
                raise HTTPException(status_code=404, detail="Batch job not found")
            
            # Get basic status
            if task.is_complete():
                status = 'SUCCESS'
                progress = 100.0
                current_step = "completed"
                result_data = task()  # Get the result
                error_message = None
                
                # Extract statistics from result
                completed_files = 0
                failed_files = 0
                total_files = 0
                
                if isinstance(result_data, dict):
                    if result_data.get('success', False):
                        if 'individual_results' in result_data:
                            individual_results = result_data['individual_results']
                            total_files = len(individual_results)
                            completed_files = sum(1 for r in individual_results if r.get('success', False))
                            failed_files = total_files - completed_files
                        else:
                            # Single successful result
                            total_files = 1
                            completed_files = 1
                            failed_files = 0
                    else:
                        # Failed result
                        total_files = 1
                        completed_files = 0
                        failed_files = 1
                        error_message = result_data.get('error_message', 'Unknown error')
                        status = 'FAILURE'
                        progress = 0.0
                        current_step = "failed"
                        
            elif task.is_revoked():
                status = 'REVOKED'
                progress = 0.0
                current_step = "cancelled"
                completed_files = 0
                failed_files = 0
                total_files = 0
                error_message = "Task was cancelled"
                result_data = None
                
            else:
                # Task is still running or queued
                status = 'PENDING'
                progress = 0.0
                current_step = "processing"
                completed_files = 0
                failed_files = 0
                total_files = 0
                error_message = None
                result_data = None
                
            return JobStatusResponse(
                batch_id=batch_id,
                status=status,
                progress=progress,
                current_step=current_step,
                completed_files=completed_files,
                failed_files=failed_files,
                total_files=total_files,
                result=result_data,
                error_message=error_message,
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting batch status: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @router.get("/download/{batch_id}")
    async def download_result(batch_id: str, background_tasks: BackgroundTasks):
        """
        Download the result of a completed batch job.
        """
        try:
            # Get task from Huey
            task = huey.get(batch_id)
            
            if task is None:
                raise HTTPException(status_code=404, detail="Batch job not found")
                
            if not task.is_complete():
                raise HTTPException(
                    status_code=400, 
                    detail="Batch job not completed yet",
                )
            
            result_data = task()  # Get the result
            if not result_data or not result_data.get('success', False):
                raise HTTPException(
                    status_code=400,
                    detail="Batch job failed or has no result",
                )
            
            output_path = result_data.get('output_path')
            if not output_path or not Path(output_path).exists():
                raise HTTPException(
                    status_code=404,
                    detail="Output file not found",
                )
            
            # Determine media type and filename
            output_file = Path(output_path)
            if output_file.suffix.lower() == '.pptx':
                media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            elif output_file.suffix.lower() == '.zip':
                media_type = "application/zip"
            else:
                media_type = "application/octet-stream"
            
            # Schedule cleanup of temporary files after download
            temp_files = []
            if 'individual_results' in result_data:
                for individual_result in result_data['individual_results']:
                    if individual_result.get('output_path'):
                        temp_files.append(individual_result['output_path'])
            
            if temp_files:
                cleanup_temp_files(temp_files)  # Schedule cleanup task
            
            return FileResponse(
                path=output_path,
                media_type=media_type,
                filename=output_file.name,
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error downloading result: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @router.delete("/cancel/{batch_id}")
    async def cancel_batch(batch_id: str):
        """
        Cancel a running batch job.
        """
        try:
            # Get task from Huey
            task = huey.get(batch_id)
            
            if task is None:
                raise HTTPException(status_code=404, detail="Batch job not found")
            
            if task.is_complete():
                raise HTTPException(
                    status_code=400,
                    detail="Cannot cancel completed job",
                )
            
            # Revoke the task
            task.revoke()
            
            logger.info(f"Cancelled batch job {batch_id}")
            
            return {"message": f"Batch job {batch_id} cancelled"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error cancelling batch: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @router.get("/worker-status")
    async def get_worker_status():
        """
        Get Celery worker status information.
        """
        try:
            # Get Huey stats (simpler than Celery)
            # Note: Huey doesn't have built-in worker introspection like Celery
            # We'll provide basic information about the database
            
            import sqlite3

            from .huey_app import DB_PATH
            
            stats = {
                "database_path": str(DB_PATH),
                "database_exists": DB_PATH.exists(),
                "total_tasks": 0,
                "pending_tasks": 0,
            }
            
            if DB_PATH.exists():
                try:
                    conn = sqlite3.connect(str(DB_PATH))
                    cursor = conn.cursor()
                    
                    # Get task counts from Huey's tables
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    if 'task' in tables:
                        cursor.execute("SELECT COUNT(*) FROM task")
                        stats["total_tasks"] = cursor.fetchone()[0]
                        
                        cursor.execute("SELECT COUNT(*) FROM task WHERE revoked = 0")
                        stats["pending_tasks"] = cursor.fetchone()[0]
                    
                    conn.close()
                    
                except Exception as e:
                    stats["database_error"] = str(e)
            
            return {
                "huey_stats": stats,
                "message": "Huey uses SQLite backend - no separate workers to inspect",
            }
            
        except Exception as e:
            logger.error(f"Error getting worker status: {e}")
            return {
                "workers_online": 0,
                "active_tasks": 0,
                "error": str(e),
            }

    return router