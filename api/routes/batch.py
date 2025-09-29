#!/usr/bin/env python3
"""
Batch processing API routes for SVG2PPTX with Google Drive integration.

Provides endpoints for creating batch jobs, monitoring status, and managing
Drive uploads with folder organization and preview generation.
"""

import logging
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

# Add path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ..auth import get_current_user
from src.batch.models import BatchJob, BatchDriveMetadata, BatchFileDriveMetadata, DEFAULT_DB_PATH
from src.batch.drive_controller import BatchDriveController, BatchDriveError
from src.batch.file_manager import get_default_file_manager, ConvertedFile
from ..services.conversion_service import ConversionService, ConversionError

logger = logging.getLogger(__name__)

# Create APIRouter
router = APIRouter(prefix="/batch", tags=["batch"])


# Pydantic models for request/response schemas
class BatchJobCreate(BaseModel):
    """Request model for creating a new batch job."""
    urls: List[str] = Field(..., min_items=1, max_items=50, description="List of SVG URLs to process (1-50)")
    drive_integration_enabled: bool = Field(default=True, description="Enable Google Drive integration")
    drive_folder_pattern: Optional[str] = Field(default=None, description="Custom folder naming pattern")
    preprocessing_preset: Optional[str] = Field(default="default", description="Preprocessing preset: minimal, default, aggressive")
    generate_previews: bool = Field(default=True, description="Generate PNG previews for uploaded files")
    use_clean_slate: Optional[bool] = Field(default=None, description="Enable clean slate architecture (experimental)")


class BatchJobStatus(BaseModel):
    """Response model for batch job status."""
    job_id: str
    status: str
    total_files: int
    completed_files: int
    failed_files: int
    drive_integration_enabled: bool
    drive_folder_id: Optional[str] = None
    drive_folder_url: Optional[str] = None
    drive_upload_status: Optional[str] = None
    drive_upload_progress: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    estimated_completion_time: Optional[datetime] = None
    errors: List[str] = []


class BatchDriveInfo(BaseModel):
    """Response model for batch Drive information."""
    job_id: str
    drive_folder_id: Optional[str] = None
    drive_folder_url: Optional[str] = None
    uploaded_files: List[Dict[str, Any]] = []
    preview_urls: List[Dict[str, Any]] = []
    upload_summary: Dict[str, Any] = {}


class BatchJobResponse(BaseModel):
    """Response model for created batch job."""
    success: bool
    job_id: str
    message: str
    status: str
    total_files: int
    drive_integration_enabled: bool
    estimated_processing_time: Optional[str] = None


class DriveUploadRequest(BaseModel):
    """Request model for Drive upload."""
    folder_pattern: Optional[str] = Field(default=None, description="Custom folder naming pattern")
    generate_previews: bool = Field(default=True, description="Generate PNG previews")
    parallel_uploads: bool = Field(default=True, description="Use parallel uploading")
    max_workers: int = Field(default=3, ge=1, le=10, description="Max parallel workers (1-10)")


@router.post("/jobs", response_model=BatchJobResponse)
async def create_batch_job(
    job_request: BatchJobCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new batch processing job.
    
    Creates a batch job to process multiple SVG files. If Drive integration is enabled,
    the job will automatically upload results to Google Drive in organized folders.
    
    Args:
        job_request: Batch job configuration
        background_tasks: FastAPI background tasks for async processing
        current_user: Authenticated user information
        
    Returns:
        BatchJobResponse with job details
    """
    try:
        # Validate URLs
        if not job_request.urls:
            raise HTTPException(status_code=400, detail="At least one URL is required")
        
        # Basic URL validation
        import urllib.parse
        for url in job_request.urls:
            if not url or not url.strip():
                raise HTTPException(status_code=400, detail="URLs cannot be empty")
            
            try:
                parsed = urllib.parse.urlparse(url.strip())
                if not parsed.scheme or not parsed.netloc:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid URL format: {url}"
                    )
                if parsed.scheme.lower() not in ['http', 'https']:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Only HTTP and HTTPS URLs are supported: {url}"
                    )
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid URL format: {url}"
                )
        
        # Create batch job
        from uuid import uuid4
        job_id = f"batch_{uuid4().hex[:12]}"
        
        batch_job = BatchJob(
            job_id=job_id,
            status="created",
            total_files=len(job_request.urls),
            drive_integration_enabled=job_request.drive_integration_enabled,
            drive_folder_pattern=job_request.drive_folder_pattern
        )
        
        # Save to database
        batch_job.save(DEFAULT_DB_PATH)
        
        logger.info(f"Created batch job {job_id} with {len(job_request.urls)} files for user {current_user.get('api_key', 'unknown')}")
        
        # Add background task to process the batch using Huey
        try:
            from src.batch.drive_tasks import coordinate_batch_workflow
            
            # Schedule Huey task for complete workflow
            conversion_options = {
                'preprocessing_preset': job_request.preprocessing_preset,
                'generate_previews': job_request.generate_previews,
                'use_clean_slate': job_request.use_clean_slate
            }
            
            task = coordinate_batch_workflow(job_id, job_request.urls, conversion_options)
            
            logger.info(f"Scheduled Huey batch workflow task for job {job_id}")
            
        except Exception as e:
            logger.warning(f"Failed to schedule Huey task, using fallback: {e}")
            # Fallback to FastAPI background task
            background_tasks.add_task(
                _process_batch_job,
                job_id,
                job_request.urls,
                job_request.preprocessing_preset,
                job_request.drive_integration_enabled,
                job_request.drive_folder_pattern,
                job_request.generate_previews,
                job_request.use_clean_slate
            )
        
        # Estimate processing time (rough calculation: 3 seconds per file)
        estimated_time = f"{len(job_request.urls) * 3} seconds"
        
        return BatchJobResponse(
            success=True,
            job_id=job_id,
            message=f"Batch job created successfully with {len(job_request.urls)} files",
            status="created",
            total_files=len(job_request.urls),
            drive_integration_enabled=job_request.drive_integration_enabled,
            estimated_processing_time=estimated_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating batch job: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error creating batch job"
        )


@router.get("/jobs/{job_id}", response_model=BatchJobStatus)
async def get_batch_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get batch job status and progress information.
    
    Retrieves current status, progress, and Drive integration details for a batch job.
    
    Args:
        job_id: Batch job identifier
        current_user: Authenticated user information
        
    Returns:
        BatchJobStatus with current job information
    """
    try:
        # Retrieve job from database
        batch_job = BatchJob.get_by_id(DEFAULT_DB_PATH, job_id)
        if not batch_job:
            raise HTTPException(
                status_code=404,
                detail=f"Batch job {job_id} not found"
            )
        
        # Get Drive metadata if available
        drive_info = BatchDriveMetadata.get_by_job_id(DEFAULT_DB_PATH, job_id)
        drive_folder_id = drive_info.drive_folder_id if drive_info else None
        drive_folder_url = drive_info.drive_folder_url if drive_info else None
        
        # Calculate progress
        file_metadata_list = BatchFileDriveMetadata.get_by_job_id(DEFAULT_DB_PATH, job_id)
        completed_files = len([f for f in file_metadata_list if f.upload_status == "completed"])
        failed_files = len([f for f in file_metadata_list if f.upload_status == "failed"])
        pending_files = len([f for f in file_metadata_list if f.upload_status == "pending"])
        
        # Create Drive upload progress info
        drive_upload_progress = None
        if batch_job.drive_integration_enabled and file_metadata_list:
            total_drive_files = len(file_metadata_list)
            uploaded_files = completed_files
            progress_percentage = (uploaded_files / total_drive_files * 100) if total_drive_files > 0 else 0.0
            
            drive_upload_progress = {
                'total_files': total_drive_files,
                'uploaded_files': uploaded_files,
                'failed_files': failed_files,
                'pending_files': pending_files,
                'progress_percentage': round(progress_percentage, 2),
                'upload_status': batch_job.drive_upload_status or 'not_started'
            }
        
        # Collect errors
        errors = [f.upload_error for f in file_metadata_list if f.upload_error]
        
        # Estimate completion time if still processing
        estimated_completion = None
        if batch_job.status in ["processing", "uploading"]:
            remaining_files = batch_job.total_files - completed_files - failed_files
            if remaining_files > 0:
                from datetime import timedelta
                estimated_completion = datetime.utcnow() + timedelta(seconds=remaining_files * 3)
        
        logger.info(f"Retrieved status for batch job {job_id}: {batch_job.status}")
        
        return BatchJobStatus(
            job_id=job_id,
            status=batch_job.status,
            total_files=batch_job.total_files,
            completed_files=completed_files,
            failed_files=failed_files,
            drive_integration_enabled=batch_job.drive_integration_enabled,
            drive_folder_id=drive_folder_id,
            drive_folder_url=drive_folder_url,
            drive_upload_status=batch_job.drive_upload_status,
            drive_upload_progress=drive_upload_progress,
            created_at=batch_job.created_at,
            updated_at=batch_job.updated_at,
            estimated_completion_time=estimated_completion,
            errors=errors[:10]  # Limit to 10 most recent errors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch job status {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving job status"
        )


@router.post("/jobs/{job_id}/upload-to-drive")
async def upload_batch_to_drive(
    job_id: str,
    upload_request: DriveUploadRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Upload batch processing results to Google Drive.
    
    Uploads all processed files from a batch job to Google Drive in organized folders
    with optional PNG preview generation.
    
    Args:
        job_id: Batch job identifier
        upload_request: Drive upload configuration
        background_tasks: FastAPI background tasks
        current_user: Authenticated user information
        
    Returns:
        JSON response with upload status
    """
    try:
        # Verify job exists
        batch_job = BatchJob.get_by_id(DEFAULT_DB_PATH, job_id)
        if not batch_job:
            raise HTTPException(
                status_code=404,
                detail=f"Batch job {job_id} not found"
            )
        
        # Check if job is ready for upload
        if batch_job.status not in ["completed", "processing"]:
            raise HTTPException(
                status_code=400,
                detail=f"Batch job {job_id} is not ready for upload (status: {batch_job.status})"
            )
        
        # Enable Drive integration if not already enabled
        if not batch_job.drive_integration_enabled:
            batch_job.drive_integration_enabled = True
            batch_job.drive_folder_pattern = upload_request.folder_pattern
            batch_job.save(DEFAULT_DB_PATH)
        
        logger.info(f"Starting Drive upload for batch job {job_id}")
        
        # Add background task for Drive upload using Huey
        try:
            from src.batch.drive_tasks import coordinate_upload_only_workflow
            
            # Retrieve actual converted files from storage
            file_manager = get_default_file_manager()
            try:
                converted_files = file_manager.get_converted_files(job_id)
                logger.info(f"Retrieved {len(converted_files)} files for batch job {job_id}")
            except FileNotFoundError:
                logger.warning(f"No converted files found for batch job {job_id}")
                converted_files = []
            except Exception as e:
                logger.error(f"Failed to retrieve converted files for job {job_id}: {e}")
                converted_files = []
            
            # Schedule Huey task for Drive upload
            task = coordinate_upload_only_workflow(
                job_id,
                converted_files,
                upload_request.folder_pattern,
                upload_request.generate_previews
            )
            
            logger.info(f"Scheduled Huey Drive upload task for job {job_id}")
            
        except Exception as e:
            logger.warning(f"Failed to schedule Huey task, using fallback: {e}")
            # Fallback to FastAPI background task
            background_tasks.add_task(
                _upload_batch_to_drive,
                job_id,
                upload_request.folder_pattern,
                upload_request.generate_previews,
                upload_request.parallel_uploads,
                upload_request.max_workers
            )
        
        # Update job status
        batch_job.status = "uploading"
        batch_job.drive_upload_status = "in_progress"
        batch_job.save(DEFAULT_DB_PATH)
        
        return JSONResponse(
            content={
                "success": True,
                "job_id": job_id,
                "message": "Drive upload initiated successfully",
                "status": "uploading"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating Drive upload for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error initiating Drive upload"
        )


@router.get("/jobs/{job_id}/progress")
async def get_batch_upload_progress(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get real-time upload progress for a batch job.
    
    Provides detailed progress information for Drive uploads including
    file-level status, transfer rates, and estimated completion times.
    
    Args:
        job_id: Batch job identifier
        current_user: Authenticated user information
        
    Returns:
        JSON response with detailed progress information
    """
    try:
        # Import the Drive task for progress tracking
        from src.batch.drive_tasks import track_upload_progress
        
        # Get progress information
        progress = track_upload_progress(job_id)
        
        # Get additional job information
        batch_job = BatchJob.get_by_id(DEFAULT_DB_PATH, job_id)
        if not batch_job:
            raise HTTPException(
                status_code=404,
                detail=f"Batch job {job_id} not found"
            )
        
        # Add job context to progress
        progress.update({
            'job_status': batch_job.status,
            'drive_upload_status': batch_job.drive_upload_status or 'not_started',
            'drive_integration_enabled': batch_job.drive_integration_enabled,
            'last_updated': batch_job.updated_at.isoformat()
        })
        
        # Get Drive folder info if available
        drive_info = BatchDriveMetadata.get_by_job_id(DEFAULT_DB_PATH, job_id)
        if drive_info:
            progress.update({
                'drive_folder_id': drive_info.drive_folder_id,
                'drive_folder_url': drive_info.drive_folder_url
            })
        
        return JSONResponse(content=progress)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting upload progress for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving upload progress"
        )


@router.get("/jobs/{job_id}/drive-info", response_model=BatchDriveInfo)
async def get_batch_drive_info(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get Google Drive integration information for a batch job.
    
    Retrieves Drive folder information, uploaded files, and preview URLs
    for a batch job with Drive integration.
    
    Args:
        job_id: Batch job identifier
        current_user: Authenticated user information
        
    Returns:
        BatchDriveInfo with Drive integration details
    """
    try:
        # Verify job exists
        batch_job = BatchJob.get_by_id(DEFAULT_DB_PATH, job_id)
        if not batch_job:
            raise HTTPException(
                status_code=404,
                detail=f"Batch job {job_id} not found"
            )
        
        # Check if Drive integration is enabled
        if not batch_job.drive_integration_enabled:
            raise HTTPException(
                status_code=400,
                detail=f"Drive integration is not enabled for batch job {job_id}"
            )
        
        # Get Drive metadata
        drive_metadata = BatchDriveMetadata.get_by_job_id(DEFAULT_DB_PATH, job_id)
        drive_folder_id = drive_metadata.drive_folder_id if drive_metadata else None
        drive_folder_url = drive_metadata.drive_folder_url if drive_metadata else None
        
        # Get file metadata
        file_metadata_list = BatchFileDriveMetadata.get_by_job_id(DEFAULT_DB_PATH, job_id)
        
        # Format uploaded files
        uploaded_files = []
        preview_urls = []
        
        for file_meta in file_metadata_list:
            if file_meta.upload_status == "completed":
                file_info = {
                    "original_filename": file_meta.original_filename,
                    "drive_file_id": file_meta.drive_file_id,
                    "drive_file_url": file_meta.drive_file_url,
                    "uploaded_at": file_meta.created_at.isoformat(),
                    "upload_status": file_meta.upload_status
                }
                uploaded_files.append(file_info)
                
                # Add preview info if available
                if file_meta.preview_url:
                    preview_info = {
                        "filename": file_meta.original_filename,
                        "file_id": file_meta.drive_file_id,
                        "preview_url": file_meta.preview_url
                    }
                    preview_urls.append(preview_info)
        
        # Create upload summary
        total_files = len(file_metadata_list)
        successful_uploads = len([f for f in file_metadata_list if f.upload_status == "completed"])
        failed_uploads = len([f for f in file_metadata_list if f.upload_status == "failed"])
        
        upload_summary = {
            "total_files": total_files,
            "successful_uploads": successful_uploads,
            "failed_uploads": failed_uploads,
            "success_rate": f"{(successful_uploads / total_files * 100):.1f}%" if total_files > 0 else "0%",
            "upload_status": batch_job.drive_upload_status
        }
        
        logger.info(f"Retrieved Drive info for batch job {job_id}: {successful_uploads}/{total_files} files uploaded")
        
        return BatchDriveInfo(
            job_id=job_id,
            drive_folder_id=drive_folder_id,
            drive_folder_url=drive_folder_url,
            uploaded_files=uploaded_files,
            preview_urls=preview_urls,
            upload_summary=upload_summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Drive info for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving Drive information"
        )


# Background task functions

async def _process_batch_job(
    job_id: str,
    urls: List[str],
    preprocessing_preset: str,
    drive_integration_enabled: bool,
    drive_folder_pattern: Optional[str],
    generate_previews: bool,
    use_clean_slate: Optional[bool] = None
):
    """
    Background task to process batch job.
    
    Args:
        job_id: Batch job identifier
        urls: List of SVG URLs to process
        preprocessing_preset: Preprocessing preset to use
        drive_integration_enabled: Whether Drive integration is enabled
        drive_folder_pattern: Custom folder pattern
        generate_previews: Whether to generate previews
    """
    try:
        logger.info(f"Starting background processing for batch job {job_id}")
        
        # Update job status
        batch_job = BatchJob.get_by_id(DEFAULT_DB_PATH, job_id)
        if batch_job:
            batch_job.status = "processing"
            batch_job.save(DEFAULT_DB_PATH)
        
        # Initialize conversion service
        conversion_service = ConversionService()
        if preprocessing_preset:
            conversion_service.settings.svg_preprocessing_preset = preprocessing_preset
        
        # Process each URL
        processed_files = []
        for i, url in enumerate(urls):
            try:
                logger.info(f"Processing file {i + 1}/{len(urls)}: {url}")
                
                # Convert SVG to PPTX (without Drive upload for now)
                result = conversion_service.convert_svg_to_pptx(url)
                
                if result.get('success'):
                    processed_files.append({
                        'path': result.get('temp_pptx_path'),
                        'original_name': f"converted_{i + 1}.pptx",
                        'converted_name': f"batch_{job_id}_file_{i + 1}.pptx"
                    })
                
            except Exception as e:
                logger.error(f"Error processing URL {url}: {e}")
                continue
        
        # Update job status
        if batch_job:
            batch_job.status = "completed" if processed_files else "failed"
            batch_job.save(DEFAULT_DB_PATH)
        
        # If Drive integration is enabled, upload files
        if drive_integration_enabled and processed_files:
            await _upload_batch_to_drive(
                job_id,
                drive_folder_pattern,
                generate_previews,
                True,  # parallel_uploads
                3      # max_workers
            )
        
        logger.info(f"Completed background processing for batch job {job_id}: {len(processed_files)} files processed")
        
    except Exception as e:
        logger.error(f"Error in background processing for job {job_id}: {e}")
        
        # Update job status to failed
        batch_job = BatchJob.get_by_id(DEFAULT_DB_PATH, job_id)
        if batch_job:
            batch_job.status = "failed"
            batch_job.save(DEFAULT_DB_PATH)


async def _upload_batch_to_drive(
    job_id: str,
    folder_pattern: Optional[str],
    generate_previews: bool,
    parallel_uploads: bool,
    max_workers: int
):
    """
    Background task to upload batch results to Drive.
    
    Args:
        job_id: Batch job identifier
        folder_pattern: Custom folder pattern
        generate_previews: Whether to generate previews
        parallel_uploads: Use parallel uploading
        max_workers: Maximum parallel workers
    """
    try:
        logger.info(f"Starting Drive upload for batch job {job_id}")
        
        # Initialize Drive controller
        drive_controller = BatchDriveController()
        
        # Get processed files from temporary storage
        file_manager = get_default_file_manager()
        try:
            converted_files = file_manager.get_converted_files(job_id)

            # Convert ConvertedFile objects to file info for Drive controller
            files = []
            for converted_file in converted_files:
                file_info = {
                    'original_filename': converted_file.original_filename,
                    'converted_path': str(converted_file.converted_path),
                    'file_size': converted_file.file_size,
                    'conversion_metadata': converted_file.conversion_metadata,
                    'created_at': converted_file.created_at.isoformat()
                }
                files.append(file_info)

            logger.info(f"Retrieved {len(files)} processed files for batch job {job_id}")

        except FileNotFoundError:
            logger.warning(f"No processed files found for batch job {job_id}")
            files = []
        except Exception as e:
            logger.error(f"Failed to retrieve processed files for job {job_id}: {e}")
            files = []
        
        # Execute complete Drive workflow
        workflow_result = drive_controller.execute_complete_batch_workflow(
            job_id,
            files,
            folder_pattern,
            generate_previews
        )
        
        # Update job status
        batch_job = BatchJob.get_by_id(DEFAULT_DB_PATH, job_id)
        if batch_job:
            if workflow_result.success:
                batch_job.drive_upload_status = "completed"
                if batch_job.status != "failed":
                    batch_job.status = "completed"
            else:
                batch_job.drive_upload_status = "failed"
            
            batch_job.save(DEFAULT_DB_PATH)
        
        logger.info(f"Completed Drive upload for batch job {job_id}: success={workflow_result.success}")
        
    except Exception as e:
        logger.error(f"Error uploading batch {job_id} to Drive: {e}")
        
        # Update job status to failed
        batch_job = BatchJob.get_by_id(DEFAULT_DB_PATH, job_id)
        if batch_job:
            batch_job.drive_upload_status = "failed"
            batch_job.save(DEFAULT_DB_PATH)