#!/usr/bin/env python3
"""
Huey async tasks for Google Drive integration in batch processing.

Provides asynchronous Google Drive upload, folder creation, preview generation,
and job coordination tasks using the Huey task queue system.

DEPRECATION NOTICE:
==================
The legacy batch workflow in this module is deprecated and will be removed in Q4 2025.

Please migrate to the Clean Slate batch architecture:
- Module: core.batch
- Coordinator: core.batch.coordinator.coordinate_batch_workflow_clean_slate()
- URL Downloader: core.batch.url_downloader.download_svgs_to_temp()

Migration Guide: docs/guides/batch-migration-guide.md
API Documentation: docs/api/batch-clean-slate.md

Timeline:
- Q2 2025: Clean Slate becomes default
- Q3 2025: Legacy marked deprecated (warnings added)
- Q4 2025: Legacy code removed

For new projects, use:
    from core.batch.coordinator import coordinate_batch_workflow_clean_slate
    from core.batch.url_downloader import download_svgs_to_temp
"""

import logging
import sys
import time
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# Add path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.services.google_drive import GoogleDriveError, GoogleDriveService
from api.services.google_slides import GoogleSlidesService

from .drive_controller import BatchDriveController, BatchDriveError
from .huey_app import huey
from .models import DEFAULT_DB_PATH, BatchFileDriveMetadata, BatchJob

logger = logging.getLogger(__name__)


# Core Drive Upload Tasks

@huey.task(retries=3, retry_delay=60)
def upload_batch_files_to_drive(
    job_id: str, 
    files: list[dict[str, str]], 
    folder_pattern: str | None = None,
    generate_previews: bool = True,
) -> dict[str, Any]:
    """
    Upload batch of converted files to Google Drive.
    
    Args:
        job_id: Batch job identifier
        files: List of file info dictionaries with path, original_name, converted_name
        folder_pattern: Optional custom folder pattern
        generate_previews: Whether to generate previews
        
    Returns:
        Dictionary with upload results and metadata
    """
    try:
        logger.info(f"Starting Drive upload for batch job {job_id} with {len(files)} files")
        
        # Verify job exists and has Drive integration enabled
        batch_job = BatchJob.get_by_id(job_id, DEFAULT_DB_PATH)
        if not batch_job:
            return {
                'success': False,
                'error_message': f'Batch job {job_id} not found',
                'error_type': 'job_not_found',
            }
        
        if not batch_job.drive_integration_enabled:
            return {
                'success': False,
                'error_message': f'Drive integration is not enabled for job {job_id}',
                'error_type': 'drive_not_enabled',
            }
        
        # Update job status
        batch_job.status = "uploading"
        batch_job.drive_upload_status = "in_progress"
        batch_job.save(DEFAULT_DB_PATH)
        
        # Initialize Drive controller
        drive_controller = BatchDriveController()
        
        # Execute complete Drive workflow
        workflow_result = drive_controller.execute_complete_batch_workflow(
            job_id,
            files,
            folder_pattern,
            generate_previews,
        )
        
        # Process results
        if workflow_result.success:
            successful_uploads = len([f for f in workflow_result.uploaded_files if f.success])
            failed_uploads = len([f for f in workflow_result.uploaded_files if not f.success])
            
            # Update job status
            batch_job.drive_upload_status = "completed"
            if batch_job.status != "failed":
                batch_job.status = "completed"
            batch_job.save(DEFAULT_DB_PATH)
            
            # Collect error messages
            errors = [f.error_message for f in workflow_result.uploaded_files if not f.success and f.error_message]
            
            result = {
                'success': True,
                'job_id': job_id,
                'folder_id': workflow_result.folder_id,
                'folder_url': workflow_result.folder_url,
                'uploaded_files': successful_uploads,
                'failed_files': failed_uploads,
                'total_files': len(files),
                'errors': errors[:5],  # Limit to 5 errors
                'completed_at': datetime.utcnow().isoformat(),
            }
            
            logger.info(f"Drive upload completed for job {job_id}: {successful_uploads}/{len(files)} files uploaded")
            return result
        else:
            # Workflow failed
            batch_job.drive_upload_status = "failed"
            batch_job.save(DEFAULT_DB_PATH)
            
            return {
                'success': False,
                'job_id': job_id,
                'error_message': workflow_result.error_message or "Drive upload workflow failed",
                'error_type': 'workflow_error',
                'failed_at': datetime.utcnow().isoformat(),
            }
            
    except BatchDriveError as e:
        logger.error(f"Drive error in batch upload {job_id}: {e}")
        
        # Update job status
        try:
            batch_job = BatchJob.get_by_id(job_id, DEFAULT_DB_PATH)
            if batch_job:
                batch_job.drive_upload_status = "failed"
                batch_job.save(DEFAULT_DB_PATH)
        except Exception:
            pass
        
        return {
            'success': False,
            'job_id': job_id,
            'error_message': str(e),
            'error_type': 'drive_service_error',
            'error_code': getattr(e, 'error_code', None),
            'failed_at': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in batch upload {job_id}: {e}")
        
        # Update job status
        try:
            batch_job = BatchJob.get_by_id(job_id, DEFAULT_DB_PATH)
            if batch_job:
                batch_job.drive_upload_status = "failed"
                batch_job.save(DEFAULT_DB_PATH)
        except Exception:
            pass
        
        # Determine error type
        error_type = 'network_error' if isinstance(e, (requests.exceptions.RequestException,)) else 'unexpected_error'
        
        return {
            'success': False,
            'job_id': job_id,
            'error_message': str(e),
            'error_type': error_type,
            'failed_at': datetime.utcnow().isoformat(),
        }


@huey.task(retries=2, retry_delay=30)
def create_batch_drive_folder(
    job_id: str, 
    folder_pattern: str | None = None,
) -> dict[str, Any]:
    """
    Create Google Drive folder structure for batch job.
    
    Args:
        job_id: Batch job identifier
        folder_pattern: Optional custom folder pattern
        
    Returns:
        Dictionary with folder creation results
    """
    try:
        logger.info(f"Creating Drive folder for batch job {job_id}")
        
        # Initialize Drive controller
        drive_controller = BatchDriveController()
        
        # Create folder with retry logic
        folder_result = drive_controller.create_batch_folder_with_retry(
            job_id, 
            folder_pattern,
            max_retries=2,
        )
        
        if folder_result.success:
            return {
                'success': True,
                'job_id': job_id,
                'folder_id': folder_result.folder_id,
                'folder_url': folder_result.folder_url,
                'created_at': datetime.utcnow().isoformat(),
            }
        else:
            return {
                'success': False,
                'job_id': job_id,
                'error_message': folder_result.error_message,
                'error_type': 'folder_creation_error',
                'failed_at': datetime.utcnow().isoformat(),
            }
            
    except Exception as e:
        logger.error(f"Error creating Drive folder for job {job_id}: {e}")
        
        return {
            'success': False,
            'job_id': job_id,
            'error_message': str(e),
            'error_type': 'unexpected_error',
            'failed_at': datetime.utcnow().isoformat(),
        }


@huey.task(retries=2, retry_delay=45)
def generate_batch_previews(
    job_id: str, 
    file_ids: list[str],
) -> dict[str, Any]:
    """
    Generate PNG previews for batch of PowerPoint files.
    
    Args:
        job_id: Batch job identifier
        file_ids: List of Google Drive file IDs
        
    Returns:
        Dictionary with preview generation results
    """
    try:
        logger.info(f"Generating previews for batch job {job_id} with {len(file_ids)} files")
        
        # Initialize Drive controller
        drive_controller = BatchDriveController()
        
        # Generate previews
        preview_results = drive_controller.generate_batch_previews(job_id, file_ids)
        
        # Process results
        successful_previews = len([p for p in preview_results if p.success])
        failed_previews = len([p for p in preview_results if not p.success])
        
        # Collect preview URLs
        preview_urls = []
        for result in preview_results:
            if result.success:
                preview_urls.append({
                    'file_id': result.file_id,
                    'preview_url': result.preview_url,
                    'thumbnail_url': result.thumbnail_url,
                })
        
        # Collect errors
        errors = [r.error_message for r in preview_results if not r.success and r.error_message]
        
        result_data = {
            'success': True,
            'job_id': job_id,
            'generated_previews': successful_previews,
            'failed_previews': failed_previews,
            'total_files': len(file_ids),
            'preview_urls': preview_urls,
            'errors': errors[:3],  # Limit to 3 errors
            'completed_at': datetime.utcnow().isoformat(),
        }
        
        logger.info(f"Preview generation completed for job {job_id}: {successful_previews}/{len(file_ids)} previews generated")
        return result_data
        
    except Exception as e:
        logger.error(f"Error generating previews for job {job_id}: {e}")
        
        return {
            'success': False,
            'job_id': job_id,
            'error_message': str(e),
            'error_type': 'preview_generation_error',
            'failed_at': datetime.utcnow().isoformat(),
        }


# Job Coordination Tasks

@huey.task()
def coordinate_batch_workflow(
    job_id: str,
    svg_urls: list[str],
    conversion_options: dict[str, Any] = None,
) -> dict[str, Any]:
    """
    Coordinate complete batch workflow: conversion + Drive upload.

    DEPRECATED: This function is deprecated and will be removed in Q4 2025.
    Please migrate to core.batch.coordinator.coordinate_batch_workflow_clean_slate().

    See migration guide: docs/guides/batch-migration-guide.md

    Args:
        job_id: Batch job identifier
        svg_urls: List of SVG URLs to convert
        conversion_options: Optional conversion parameters

    Returns:
        Dictionary with workflow results
    """
    # Issue deprecation warning
    warnings.warn(
        "coordinate_batch_workflow() is deprecated and will be removed in Q4 2025. "
        "Please migrate to core.batch.coordinator.coordinate_batch_workflow_clean_slate(). "
        "See migration guide: docs/guides/batch-migration-guide.md",
        DeprecationWarning,
        stacklevel=2,
    )

    try:
        logger.info(f"Starting coordinated batch workflow for job {job_id} (LEGACY)")
        
        # Step 1: Convert SVG files
        conversion_result = convert_svg_batch(job_id, svg_urls, conversion_options or {})
        
        if not conversion_result.get('success'):
            return {
                'success': False,
                'job_id': job_id,
                'conversion_success': False,
                'error_message': conversion_result.get('error_message', 'SVG conversion failed'),
                'error_type': 'conversion_error',
                'failed_at': datetime.utcnow().isoformat(),
            }
        
        # Step 2: Upload to Drive (if integration enabled)
        batch_job = BatchJob.get_by_id(job_id, DEFAULT_DB_PATH)
        if batch_job and batch_job.drive_integration_enabled:
            
            converted_files = conversion_result.get('converted_files', [])
            if converted_files:
                upload_result = upload_batch_files_to_drive(job_id, converted_files, None, True)
                
                return {
                    'success': upload_result.get('success', False),
                    'job_id': job_id,
                    'conversion_success': True,
                    'upload_success': upload_result.get('success', False),
                    'converted_files': len(converted_files),
                    'uploaded_files': upload_result.get('uploaded_files', 0),
                    'folder_url': upload_result.get('folder_url'),
                    'completed_at': datetime.utcnow().isoformat(),
                }
        
        # No Drive integration or no converted files
        return {
            'success': True,
            'job_id': job_id,
            'conversion_success': True,
            'upload_success': None,  # No upload attempted
            'converted_files': len(conversion_result.get('converted_files', [])),
            'completed_at': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error in coordinated workflow for job {job_id}: {e}")
        
        return {
            'success': False,
            'job_id': job_id,
            'error_message': str(e),
            'error_type': 'workflow_coordination_error',
            'failed_at': datetime.utcnow().isoformat(),
        }


@huey.task()
def coordinate_upload_only_workflow(
    job_id: str, 
    converted_files: list[dict[str, str]], 
    folder_pattern: str | None = None,
    generate_previews: bool = True,
) -> dict[str, Any]:
    """
    Coordinate upload-only workflow for pre-converted files.
    
    Args:
        job_id: Batch job identifier
        converted_files: List of already converted file info
        folder_pattern: Optional custom folder pattern
        generate_previews: Whether to generate previews
        
    Returns:
        Dictionary with upload workflow results
    """
    try:
        logger.info(f"Starting upload-only workflow for job {job_id} with {len(converted_files)} files")
        
        # Execute upload
        upload_result = upload_batch_files_to_drive(job_id, converted_files, folder_pattern, generate_previews)
        
        return {
            'success': upload_result.get('success', False),
            'job_id': job_id,
            'upload_success': upload_result.get('success', False),
            'uploaded_files': upload_result.get('uploaded_files', 0),
            'failed_files': upload_result.get('failed_files', 0),
            'folder_url': upload_result.get('folder_url'),
            'completed_at': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error in upload-only workflow for job {job_id}: {e}")
        
        return {
            'success': False,
            'job_id': job_id,
            'error_message': str(e),
            'error_type': 'upload_workflow_error',
            'failed_at': datetime.utcnow().isoformat(),
        }


# Status Tracking and Monitoring Tasks

@huey.task()
def update_batch_job_status(
    job_id: str, 
    status: str, 
    drive_upload_status: str | None = None,
) -> dict[str, Any]:
    """
    Update batch job status in database.
    
    Args:
        job_id: Batch job identifier
        status: New job status
        drive_upload_status: Optional Drive upload status
        
    Returns:
        Dictionary with update results
    """
    try:
        batch_job = BatchJob.get_by_id(job_id, DEFAULT_DB_PATH)
        if not batch_job:
            return {
                'success': False,
                'error_message': f'Job {job_id} not found',
            }
        
        batch_job.status = status
        if drive_upload_status:
            batch_job.drive_upload_status = drive_upload_status
        
        batch_job.save(DEFAULT_DB_PATH)
        
        return {
            'success': True,
            'job_id': job_id,
            'status': status,
            'drive_upload_status': drive_upload_status,
            'updated_at': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error updating job status for {job_id}: {e}")
        
        return {
            'success': False,
            'job_id': job_id,
            'error_message': str(e),
        }


@huey.task()
def track_upload_progress(job_id: str) -> dict[str, Any]:
    """
    Track upload progress for a batch job.
    
    Args:
        job_id: Batch job identifier
        
    Returns:
        Dictionary with progress information
    """
    try:
        # Get file metadata
        file_metadata_list = BatchFileDriveMetadata.get_by_job_id(DEFAULT_DB_PATH, job_id)
        
        if not file_metadata_list:
            return {
                'job_id': job_id,
                'total_files': 0,
                'uploaded_files': 0,
                'pending_files': 0,
                'failed_files': 0,
                'progress_percentage': 0.0,
            }
        
        total_files = len(file_metadata_list)
        uploaded_files = len([f for f in file_metadata_list if f.upload_status == "completed"])
        pending_files = len([f for f in file_metadata_list if f.upload_status == "pending"])
        failed_files = len([f for f in file_metadata_list if f.upload_status == "failed"])
        
        progress_percentage = (uploaded_files / total_files * 100) if total_files > 0 else 0.0
        
        return {
            'job_id': job_id,
            'total_files': total_files,
            'uploaded_files': uploaded_files,
            'pending_files': pending_files,
            'failed_files': failed_files,
            'progress_percentage': round(progress_percentage, 2),
        }
        
    except Exception as e:
        logger.error(f"Error tracking progress for job {job_id}: {e}")
        
        return {
            'job_id': job_id,
            'error_message': str(e),
        }


@huey.task()
def get_task_status(task_id: str) -> dict[str, Any]:
    """
    Get status of a Huey task.
    
    Args:
        task_id: Huey task identifier
        
    Returns:
        Dictionary with task status information
    """
    try:
        # In immediate mode, this is less relevant
        # But we can provide a basic status check
        return {
            'task_id': task_id,
            'status': 'completed',  # In immediate mode
            'checked_at': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error getting task status for {task_id}: {e}")
        
        return {
            'task_id': task_id,
            'status': 'error',
            'error_message': str(e),
        }


# Error Recovery and Retry Logic

@huey.task(retries=2, retry_delay=120)  # Longer delay for retry operations
def retry_failed_drive_uploads(job_id: str) -> dict[str, Any]:
    """
    Retry failed Drive uploads for a batch job.
    
    Identifies files that failed to upload and attempts to re-upload them
    with exponential backoff and different error handling strategies.
    
    Args:
        job_id: Batch job identifier
        
    Returns:
        Dictionary with retry results
    """
    try:
        logger.info(f"Starting retry operation for failed uploads in job {job_id}")
        
        # Get failed file uploads
        file_metadata_list = BatchFileDriveMetadata.get_by_job_id(DEFAULT_DB_PATH, job_id)
        failed_files = [f for f in file_metadata_list if f.upload_status == "failed"]
        
        if not failed_files:
            return {
                'success': True,
                'job_id': job_id,
                'message': 'No failed uploads to retry',
                'retried_files': 0,
                'completed_at': datetime.utcnow().isoformat(),
            }
        
        logger.info(f"Found {len(failed_files)} failed uploads to retry for job {job_id}")
        
        # Initialize Drive controller with retry-specific settings
        drive_controller = BatchDriveController()
        
        retry_results = []
        successful_retries = 0
        
        # Retry each failed file individually
        for file_meta in failed_files:
            try:
                # Reconstruct file info for retry
                file_info = {
                    'path': f'/tmp/{job_id}_{file_meta.original_filename}.pptx',  # Reconstructed path
                    'original_name': file_meta.original_filename,
                    'converted_name': f'{job_id}_{file_meta.original_filename}.pptx',
                }
                
                # Attempt single file upload with increased timeout
                single_file_result = _retry_single_file_upload(file_meta, file_info, drive_controller)
                
                if single_file_result['success']:
                    # Update file metadata
                    file_meta.upload_status = "completed"
                    file_meta.drive_file_id = single_file_result['file_id']
                    file_meta.drive_file_url = single_file_result['file_url']
                    file_meta.upload_error = None
                    file_meta.save(DEFAULT_DB_PATH)
                    
                    successful_retries += 1
                    logger.info(f"Successfully retried upload for {file_meta.original_filename}")
                else:
                    # Update error message
                    file_meta.upload_error = f"Retry failed: {single_file_result['error_message']}"
                    file_meta.save(DEFAULT_DB_PATH)
                    logger.warning(f"Retry failed for {file_meta.original_filename}: {single_file_result['error_message']}")
                
                retry_results.append({
                    'filename': file_meta.original_filename,
                    'success': single_file_result['success'],
                    'error_message': single_file_result.get('error_message'),
                })
                
                # Add delay between retries to avoid rate limiting
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Exception during retry for {file_meta.original_filename}: {e}")
                
                # Update error in database
                file_meta.upload_error = f"Retry exception: {str(e)}"
                file_meta.save(DEFAULT_DB_PATH)
                
                retry_results.append({
                    'filename': file_meta.original_filename,
                    'success': False,
                    'error_message': str(e),
                })
        
        # Update job status if all files are now uploaded
        remaining_failed = len([r for r in retry_results if not r['success']])
        if remaining_failed == 0:
            batch_job = BatchJob.get_by_id(job_id, DEFAULT_DB_PATH)
            if batch_job:
                batch_job.drive_upload_status = "completed"
                if batch_job.status == "failed":
                    batch_job.status = "completed"
                batch_job.save(DEFAULT_DB_PATH)
        
        return {
            'success': True,
            'job_id': job_id,
            'total_retried': len(failed_files),
            'successful_retries': successful_retries,
            'remaining_failures': remaining_failed,
            'retry_results': retry_results,
            'completed_at': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error in retry operation for job {job_id}: {e}")
        
        return {
            'success': False,
            'job_id': job_id,
            'error_message': str(e),
            'error_type': 'retry_operation_error',
            'failed_at': datetime.utcnow().isoformat(),
        }


def _retry_single_file_upload(
    file_meta: BatchFileDriveMetadata, 
    file_info: dict[str, str], 
    drive_controller: BatchDriveController,
) -> dict[str, Any]:
    """
    Retry upload for a single file with adaptive error handling.
    
    Args:
        file_meta: File metadata from database
        file_info: File information dictionary
        drive_controller: Drive controller instance
        
    Returns:
        Dictionary with retry result
    """
    max_attempts = 3
    base_delay = 5  # seconds
    
    for attempt in range(max_attempts):
        try:
            # Different strategies based on previous error
            if file_meta.upload_error and 'quota' in file_meta.upload_error.lower():
                # Quota error - wait longer
                if attempt > 0:
                    delay = base_delay * (2 ** attempt) * 2  # Longer backoff for quota
                    time.sleep(delay)
            elif file_meta.upload_error and 'network' in file_meta.upload_error.lower():
                # Network error - shorter delay
                if attempt > 0:
                    time.sleep(base_delay * attempt)
            else:
                # Generic error - standard backoff
                if attempt > 0:
                    time.sleep(base_delay * (2 ** attempt))
            
            logger.info(f"Retry attempt {attempt + 1}/{max_attempts} for {file_meta.original_filename}")
            
            # Use Drive controller for single file upload
            # This is a simplified approach - in reality you'd call the Drive service directly
            single_upload_result = drive_controller.upload_batch_files(
                file_meta.batch_job_id, 
                [file_info], 
                None,  # Use existing folder
            )
            
            if single_upload_result and len(single_upload_result) > 0 and single_upload_result[0].success:
                return {
                    'success': True,
                    'file_id': single_upload_result[0].file_id,
                    'file_url': single_upload_result[0].file_url,
                    'attempt': attempt + 1,
                }
                
        except Exception as e:
            logger.warning(f"Retry attempt {attempt + 1} failed for {file_meta.original_filename}: {e}")
            
            if attempt == max_attempts - 1:  # Last attempt
                return {
                    'success': False,
                    'error_message': f"All {max_attempts} retry attempts failed: {str(e)}",
                    'final_attempt': True,
                }
    
    return {
        'success': False,
        'error_message': f"Exhausted {max_attempts} retry attempts",
        'exhausted': True,
    }


@huey.task()
def recover_batch_job_from_failure(job_id: str) -> dict[str, Any]:
    """
    Attempt to recover a failed batch job by analyzing and fixing issues.
    
    Args:
        job_id: Batch job identifier
        
    Returns:
        Dictionary with recovery results
    """
    try:
        logger.info(f"Starting recovery operation for failed job {job_id}")
        
        batch_job = BatchJob.get_by_id(job_id, DEFAULT_DB_PATH)
        if not batch_job:
            return {
                'success': False,
                'error_message': f'Job {job_id} not found',
            }
        
        if batch_job.status != "failed":
            return {
                'success': False,
                'error_message': f'Job {job_id} is not in failed state (current: {batch_job.status})',
            }
        
        recovery_actions = []
        
        # 1. Check for Drive authentication issues
        try:
            connection_test = test_drive_connection()
            if not connection_test.get('success'):
                recovery_actions.append({
                    'action': 'drive_connection_test',
                    'success': False,
                    'message': 'Drive connection failed - authentication may need renewal',
                })
                
                # Can't proceed with Drive recovery if connection is bad
                return {
                    'success': False,
                    'job_id': job_id,
                    'error_message': 'Drive connection test failed during recovery',
                    'recovery_actions': recovery_actions,
                }
            else:
                recovery_actions.append({
                    'action': 'drive_connection_test',
                    'success': True,
                    'message': 'Drive connection is healthy',
                })
        except Exception as e:
            recovery_actions.append({
                'action': 'drive_connection_test',
                'success': False,
                'message': f'Connection test failed: {e}',
            })
        
        # 2. Retry failed uploads if any
        if batch_job.drive_integration_enabled:
            try:
                retry_result = retry_failed_drive_uploads(job_id)
                recovery_actions.append({
                    'action': 'retry_failed_uploads',
                    'success': retry_result.get('success', False),
                    'message': f"Retried {retry_result.get('total_retried', 0)} files, {retry_result.get('successful_retries', 0)} succeeded",
                })
            except Exception as e:
                recovery_actions.append({
                    'action': 'retry_failed_uploads',
                    'success': False,
                    'message': f'Upload retry failed: {e}',
                })
        
        # 3. Update job status if recovery was successful
        successful_actions = [a for a in recovery_actions if a['success']]
        if len(successful_actions) >= len(recovery_actions) - 1:  # Allow one failure
            batch_job.status = "processing"  # Reset to processing state
            batch_job.save(DEFAULT_DB_PATH)
            
            recovery_actions.append({
                'action': 'job_status_update',
                'success': True,
                'message': 'Job status reset to processing',
            })
            
            recovery_success = True
        else:
            recovery_success = False
        
        return {
            'success': recovery_success,
            'job_id': job_id,
            'recovery_actions': recovery_actions,
            'recovered_at': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error during recovery operation for job {job_id}: {e}")
        
        return {
            'success': False,
            'job_id': job_id,
            'error_message': str(e),
            'error_type': 'recovery_operation_error',
            'failed_at': datetime.utcnow().isoformat(),
        }


@huey.task()
def handle_drive_quota_exceeded(job_id: str, wait_minutes: int = 60) -> dict[str, Any]:
    """
    Handle Drive quota exceeded errors with intelligent waiting and retry.
    
    Args:
        job_id: Batch job identifier
        wait_minutes: Minutes to wait before retrying
        
    Returns:
        Dictionary with quota handling results
    """
    try:
        logger.info(f"Handling quota exceeded for job {job_id}, waiting {wait_minutes} minutes")
        
        # Update job status to indicate quota wait
        batch_job = BatchJob.get_by_id(job_id, DEFAULT_DB_PATH)
        if batch_job:
            batch_job.drive_upload_status = "quota_wait"
            batch_job.save(DEFAULT_DB_PATH)
        
        # Wait for specified time (in production, this would be handled by scheduling)
        # For testing/immediate mode, we'll just log the wait time
        wait_seconds = wait_minutes * 60
        logger.info(f"Would wait {wait_seconds} seconds for quota reset")
        
        # In a real implementation, this task would reschedule itself
        # For now, we'll just return success and indicate the wait time
        return {
            'success': True,
            'job_id': job_id,
            'action': 'quota_wait_scheduled',
            'wait_minutes': wait_minutes,
            'scheduled_retry_at': (datetime.utcnow() + timedelta(minutes=wait_minutes)).isoformat(),
            'message': f'Quota wait scheduled for {wait_minutes} minutes',
        }
        
    except Exception as e:
        logger.error(f"Error handling quota exceeded for job {job_id}: {e}")
        
        return {
            'success': False,
            'job_id': job_id,
            'error_message': str(e),
            'error_type': 'quota_handling_error',
        }


# Rate Limiting and Quota Management Tasks

@huey.task()
def initialize_rate_limiter(job_id: str, max_requests_per_minute: int = 100, 
                           max_concurrent_uploads: int = 10) -> dict[str, Any]:
    """
    Initialize rate limiting configuration for a batch job.
    
    Args:
        job_id: Batch job identifier
        max_requests_per_minute: Maximum API requests per minute
        max_concurrent_uploads: Maximum concurrent file uploads
        
    Returns:
        Dictionary with rate limiter initialization results
    """
    try:
        import json
        from datetime import datetime
        
        # Rate limiter state
        rate_limiter_config = {
            'job_id': job_id,
            'max_requests_per_minute': max_requests_per_minute,
            'max_concurrent_uploads': max_concurrent_uploads,
            'request_timestamps': [],
            'active_uploads': [],
            'quota_reset_time': None,
            'quota_exceeded': False,
            'last_updated': datetime.utcnow().isoformat(),
        }
        
        # Store in job metadata
        batch_job = BatchJob.get_by_id(job_id, DEFAULT_DB_PATH)
        if batch_job:
            # Add rate limiter config to job metadata
            metadata = json.loads(batch_job.metadata) if batch_job.metadata else {}
            metadata['rate_limiter'] = rate_limiter_config
            batch_job.metadata = json.dumps(metadata)
            batch_job.save(DEFAULT_DB_PATH)
            
            logger.info(f"Rate limiter initialized for job {job_id}: "
                       f"{max_requests_per_minute} req/min, "
                       f"{max_concurrent_uploads} concurrent uploads")
            
            return {
                'success': True,
                'job_id': job_id,
                'rate_limiter_config': rate_limiter_config,
                'status': 'rate_limiter_initialized',
            }
        else:
            raise ValueError(f"Batch job {job_id} not found")
            
    except Exception as e:
        logger.error(f"Error initializing rate limiter for job {job_id}: {e}")
        
        return {
            'success': False,
            'job_id': job_id,
            'error_message': str(e),
            'error_type': 'rate_limiter_init_error',
        }


@huey.task()
def check_rate_limit(job_id: str, operation_type: str = 'upload') -> dict[str, Any]:
    """
    Check if current operation can proceed based on rate limits.
    
    Args:
        job_id: Batch job identifier
        operation_type: Type of operation ('upload', 'create_folder', 'preview')
        
    Returns:
        Dictionary with rate limit check results
    """
    try:
        import json
        from datetime import datetime, timedelta
        
        batch_job = BatchJob.get_by_id(job_id, DEFAULT_DB_PATH)
        if not batch_job:
            raise ValueError(f"Batch job {job_id} not found")
        
        metadata = json.loads(batch_job.metadata) if batch_job.metadata else {}
        rate_limiter = metadata.get('rate_limiter', {})
        
        if not rate_limiter:
            # Initialize rate limiter if not exists
            init_result = initialize_rate_limiter(job_id)
            if not init_result['success']:
                return init_result
            rate_limiter = init_result['rate_limiter_config']
        
        current_time = datetime.utcnow()
        
        # Check quota exceeded status
        if rate_limiter.get('quota_exceeded'):
            quota_reset_time = rate_limiter.get('quota_reset_time')
            if quota_reset_time and current_time < datetime.fromisoformat(quota_reset_time):
                return {
                    'success': False,
                    'job_id': job_id,
                    'can_proceed': False,
                    'reason': 'quota_exceeded',
                    'wait_until': quota_reset_time,
                    'error_type': 'quota_wait_required',
                }
            else:
                # Reset quota exceeded flag
                rate_limiter['quota_exceeded'] = False
                rate_limiter['quota_reset_time'] = None
        
        # Clean up old request timestamps (older than 1 minute)
        one_minute_ago = current_time - timedelta(minutes=1)
        request_timestamps = [
            ts for ts in rate_limiter.get('request_timestamps', [])
            if datetime.fromisoformat(ts) > one_minute_ago
        ]
        
        # Check requests per minute limit
        max_requests = rate_limiter.get('max_requests_per_minute', 100)
        if len(request_timestamps) >= max_requests:
            return {
                'success': False,
                'job_id': job_id,
                'can_proceed': False,
                'reason': 'rate_limit_exceeded',
                'current_requests': len(request_timestamps),
                'max_requests_per_minute': max_requests,
                'error_type': 'rate_limit_wait_required',
            }
        
        # Check concurrent uploads limit
        active_uploads = rate_limiter.get('active_uploads', [])
        max_concurrent = rate_limiter.get('max_concurrent_uploads', 10)
        if operation_type == 'upload' and len(active_uploads) >= max_concurrent:
            return {
                'success': False,
                'job_id': job_id,
                'can_proceed': False,
                'reason': 'concurrent_limit_exceeded',
                'active_uploads': len(active_uploads),
                'max_concurrent_uploads': max_concurrent,
                'error_type': 'concurrent_wait_required',
            }
        
        # Update rate limiter state
        request_timestamps.append(current_time.isoformat())
        if operation_type == 'upload':
            active_uploads.append({
                'started_at': current_time.isoformat(),
                'operation_id': f"{job_id}_{current_time.timestamp()}",
            })
        
        rate_limiter['request_timestamps'] = request_timestamps
        rate_limiter['active_uploads'] = active_uploads
        rate_limiter['last_updated'] = current_time.isoformat()
        
        # Save updated state
        metadata['rate_limiter'] = rate_limiter
        batch_job.metadata = json.dumps(metadata)
        batch_job.save(DEFAULT_DB_PATH)
        
        return {
            'success': True,
            'job_id': job_id,
            'can_proceed': True,
            'current_requests': len(request_timestamps),
            'active_uploads': len(active_uploads),
            'status': 'rate_limit_ok',
        }
        
    except Exception as e:
        logger.error(f"Error checking rate limit for job {job_id}: {e}")
        
        return {
            'success': False,
            'job_id': job_id,
            'can_proceed': False,
            'error_message': str(e),
            'error_type': 'rate_limit_check_error',
        }


@huey.task()
def release_rate_limit_slot(job_id: str, operation_type: str = 'upload', 
                           operation_id: str = None) -> dict[str, Any]:
    """
    Release a rate limit slot after operation completion.
    
    Args:
        job_id: Batch job identifier
        operation_type: Type of operation that completed
        operation_id: Specific operation identifier to release
        
    Returns:
        Dictionary with slot release results
    """
    try:
        import json
        from datetime import datetime
        
        batch_job = BatchJob.get_by_id(job_id, DEFAULT_DB_PATH)
        if not batch_job:
            raise ValueError(f"Batch job {job_id} not found")
        
        metadata = json.loads(batch_job.metadata) if batch_job.metadata else {}
        rate_limiter = metadata.get('rate_limiter', {})
        
        if not rate_limiter:
            return {
                'success': True,
                'job_id': job_id,
                'message': 'No rate limiter found, nothing to release',
            }
        
        # Release upload slot
        if operation_type == 'upload':
            active_uploads = rate_limiter.get('active_uploads', [])
            if operation_id:
                # Remove specific operation
                active_uploads = [
                    upload for upload in active_uploads
                    if upload.get('operation_id') != operation_id
                ]
            else:
                # Remove oldest upload if no specific ID
                if active_uploads:
                    active_uploads.pop(0)
            
            rate_limiter['active_uploads'] = active_uploads
        
        rate_limiter['last_updated'] = datetime.utcnow().isoformat()
        
        # Save updated state
        metadata['rate_limiter'] = rate_limiter
        batch_job.metadata = json.dumps(metadata)
        batch_job.save(DEFAULT_DB_PATH)
        
        return {
            'success': True,
            'job_id': job_id,
            'operation_type': operation_type,
            'remaining_active_uploads': len(rate_limiter.get('active_uploads', [])),
            'status': 'rate_limit_slot_released',
        }
        
    except Exception as e:
        logger.error(f"Error releasing rate limit slot for job {job_id}: {e}")
        
        return {
            'success': False,
            'job_id': job_id,
            'error_message': str(e),
            'error_type': 'rate_limit_release_error',
        }


@huey.task()
def handle_quota_exceeded_with_backoff(job_id: str, error_details: dict[str, Any] = None) -> dict[str, Any]:
    """
    Handle Drive API quota exceeded with intelligent backoff.
    
    Args:
        job_id: Batch job identifier
        error_details: Details about the quota error
        
    Returns:
        Dictionary with quota handling results
    """
    try:
        import json
        from datetime import datetime, timedelta
        
        batch_job = BatchJob.get_by_id(job_id, DEFAULT_DB_PATH)
        if not batch_job:
            raise ValueError(f"Batch job {job_id} not found")
        
        metadata = json.loads(batch_job.metadata) if batch_job.metadata else {}
        rate_limiter = metadata.get('rate_limiter', {})
        
        # Determine backoff time based on quota type
        error_reason = error_details.get('reason', 'unknown') if error_details else 'unknown'
        
        if error_reason in ['dailyLimitExceeded', 'quotaExceeded']:
            # Daily quota exceeded - wait until next day
            backoff_hours = 24
        elif error_reason in ['rateLimitExceeded', 'userRateLimitExceeded']:
            # Rate limit exceeded - exponential backoff
            previous_backoffs = metadata.get('quota_backoff_count', 0)
            backoff_minutes = min(60 * (2 ** previous_backoffs), 480)  # Max 8 hours
            backoff_hours = backoff_minutes / 60
            metadata['quota_backoff_count'] = previous_backoffs + 1
        else:
            # Unknown quota error - conservative 2-hour wait
            backoff_hours = 2
        
        # Calculate reset time
        reset_time = datetime.utcnow() + timedelta(hours=backoff_hours)
        
        # Update rate limiter state
        rate_limiter['quota_exceeded'] = True
        rate_limiter['quota_reset_time'] = reset_time.isoformat()
        rate_limiter['quota_error_reason'] = error_reason
        rate_limiter['last_quota_error'] = datetime.utcnow().isoformat()
        
        # Clear active operations
        rate_limiter['active_uploads'] = []
        rate_limiter['request_timestamps'] = []
        
        # Update job status
        batch_job.drive_upload_status = f"quota_exceeded_{error_reason}"
        
        # Save updated state
        metadata['rate_limiter'] = rate_limiter
        batch_job.metadata = json.dumps(metadata)
        batch_job.save(DEFAULT_DB_PATH)
        
        logger.warning(f"Quota exceeded for job {job_id} (reason: {error_reason}). "
                      f"Will retry after {reset_time.isoformat()}")
        
        # Schedule retry task
        retry_failed_drive_uploads.schedule(args=(job_id,), delay=int(backoff_hours * 3600))
        
        return {
            'success': True,
            'job_id': job_id,
            'quota_exceeded': True,
            'error_reason': error_reason,
            'backoff_hours': backoff_hours,
            'reset_time': reset_time.isoformat(),
            'retry_scheduled': True,
            'status': 'quota_backoff_applied',
        }
        
    except Exception as e:
        logger.error(f"Error handling quota exceeded for job {job_id}: {e}")
        
        return {
            'success': False,
            'job_id': job_id,
            'error_message': str(e),
            'error_type': 'quota_backoff_error',
        }


@huey.task()
def monitor_drive_api_usage(job_id: str) -> dict[str, Any]:
    """
    Monitor Drive API usage and adjust rate limits dynamically.
    
    Args:
        job_id: Batch job identifier
        
    Returns:
        Dictionary with usage monitoring results
    """
    try:
        import json
        from datetime import datetime, timedelta
        
        batch_job = BatchJob.get_by_id(job_id, DEFAULT_DB_PATH)
        if not batch_job:
            raise ValueError(f"Batch job {job_id} not found")
        
        metadata = json.loads(batch_job.metadata) if batch_job.metadata else {}
        rate_limiter = metadata.get('rate_limiter', {})
        
        current_time = datetime.utcnow()
        
        # Calculate usage metrics
        recent_requests = len([
            ts for ts in rate_limiter.get('request_timestamps', [])
            if datetime.fromisoformat(ts) > current_time - timedelta(minutes=5)
        ])
        
        active_uploads = len(rate_limiter.get('active_uploads', []))
        max_concurrent = rate_limiter.get('max_concurrent_uploads', 10)
        max_requests = rate_limiter.get('max_requests_per_minute', 100)
        
        # Calculate utilization percentages
        concurrent_utilization = (active_uploads / max_concurrent) * 100 if max_concurrent > 0 else 0
        request_utilization = (recent_requests / (max_requests / 12)) * 100  # 5 min = 1/12 of hour
        
        # Dynamic rate limit adjustment
        adjustment_needed = False
        new_limits = {}
        
        # Reduce limits if high utilization and no recent errors
        if (concurrent_utilization > 80 or request_utilization > 80) and \
           not rate_limiter.get('quota_exceeded', False):
            new_concurrent = max(1, int(max_concurrent * 0.8))
            new_requests = max(10, int(max_requests * 0.8))
            adjustment_needed = True
            new_limits = {
                'max_concurrent_uploads': new_concurrent,
                'max_requests_per_minute': new_requests,
            }
        
        # Increase limits if low utilization and good performance
        elif concurrent_utilization < 40 and request_utilization < 40 and \
             not metadata.get('recent_quota_errors', False):
            new_concurrent = min(20, int(max_concurrent * 1.2))
            new_requests = min(150, int(max_requests * 1.1))
            adjustment_needed = True
            new_limits = {
                'max_concurrent_uploads': new_concurrent,
                'max_requests_per_minute': new_requests,
            }
        
        # Apply adjustments
        if adjustment_needed:
            rate_limiter.update(new_limits)
            logger.info(f"Adjusted rate limits for job {job_id}: {new_limits}")
        
        # Update monitoring data
        monitoring_data = {
            'timestamp': current_time.isoformat(),
            'recent_requests_5min': recent_requests,
            'active_uploads': active_uploads,
            'concurrent_utilization_pct': round(concurrent_utilization, 1),
            'request_utilization_pct': round(request_utilization, 1),
            'current_limits': {
                'max_concurrent_uploads': rate_limiter.get('max_concurrent_uploads', 10),
                'max_requests_per_minute': rate_limiter.get('max_requests_per_minute', 100),
            },
            'adjustment_applied': adjustment_needed,
            'new_limits': new_limits if adjustment_needed else None,
        }
        
        # Store monitoring history (keep last 24 hours)
        monitoring_history = metadata.get('usage_monitoring', [])
        cutoff_time = current_time - timedelta(hours=24)
        monitoring_history = [
            entry for entry in monitoring_history
            if datetime.fromisoformat(entry['timestamp']) > cutoff_time
        ]
        monitoring_history.append(monitoring_data)
        metadata['usage_monitoring'] = monitoring_history
        
        # Save updated state
        rate_limiter['last_updated'] = current_time.isoformat()
        metadata['rate_limiter'] = rate_limiter
        batch_job.metadata = json.dumps(metadata)
        batch_job.save(DEFAULT_DB_PATH)
        
        return {
            'success': True,
            'job_id': job_id,
            'monitoring_data': monitoring_data,
            'status': 'usage_monitored',
        }
        
    except Exception as e:
        logger.error(f"Error monitoring Drive API usage for job {job_id}: {e}")
        
        return {
            'success': False,
            'job_id': job_id,
            'error_message': str(e),
            'error_type': 'usage_monitoring_error',
        }


# Pipeline Coordination Tasks

@huey.task()
def coordinate_conversion_and_upload(job_id: str, files: list[dict[str, str]], 
                                   conversion_options: dict[str, Any] = None,
                                   upload_options: dict[str, Any] = None) -> dict[str, Any]:
    """
    Coordinate SVG conversion and Drive upload in a single pipeline.
    
    Args:
        job_id: Batch job identifier
        files: List of file information dictionaries
        conversion_options: Options for SVG conversion
        upload_options: Options for Drive upload
        
    Returns:
        Dictionary with pipeline coordination results
    """
    try:
        from src.batch.job_manager import BatchJobManager
        
        logger.info(f"Starting coordinated conversion and upload pipeline for job {job_id}")
        
        # Initialize conversion options
        conversion_options = conversion_options or {}
        upload_options = upload_options or {
            'folder_pattern': None,
            'generate_previews': True,
        }
        
        # Verify job exists
        batch_job = BatchJob.get_by_id(job_id, DEFAULT_DB_PATH)
        if not batch_job:
            return {
                'success': False,
                'error_message': f'Batch job {job_id} not found',
                'error_type': 'job_not_found',
            }
        
        # Check rate limits before starting
        rate_check = check_rate_limit(job_id, 'upload')
        if not rate_check.get('can_proceed', True):
            logger.info(f"Rate limit reached for job {job_id}, scheduling for later")
            # Schedule for later
            coordinate_conversion_and_upload.schedule(
                args=(job_id, files, conversion_options, upload_options),
                delay=300,  # 5 minutes
            )
            return {
                'success': True,
                'job_id': job_id,
                'status': 'scheduled_for_later',
                'reason': rate_check.get('reason', 'rate_limit'),
            }
        
        # Update job status
        batch_job.status = "processing"
        batch_job.drive_upload_status = "waiting_for_conversion"
        batch_job.save(DEFAULT_DB_PATH)
        
        # Initialize job manager for conversion
        job_manager = BatchJobManager()
        
        # Process conversions first
        conversion_results = []
        converted_files = []
        
        for file_info in files:
            try:
                # Check if file already exists
                input_path = file_info.get('input_path', '')
                output_path = file_info.get('output_path', '')
                
                if not input_path or not output_path:
                    logger.error(f"Missing paths for file: {file_info}")
                    continue
                
                # Perform conversion using existing job manager
                # Note: This assumes the BatchJobManager has conversion capabilities
                # In a real implementation, this might call a separate conversion service
                convert_result = job_manager.process_single_file(
                    job_id, input_path, output_path, conversion_options,
                )
                
                conversion_results.append(convert_result)
                
                # If conversion successful, prepare for upload
                if convert_result.get('success', False):
                    converted_files.append({
                        'input_path': input_path,
                        'output_path': output_path,
                        'file_size': convert_result.get('file_size', 0),
                        'conversion_time': convert_result.get('processing_time', 0),
                    })
                
            except Exception as e:
                logger.error(f"Error converting file {file_info}: {e}")
                conversion_results.append({
                    'success': False,
                    'input_path': file_info.get('input_path', ''),
                    'error_message': str(e),
                })
        
        # Update job status after conversion
        successful_conversions = len([r for r in conversion_results if r.get('success', False)])
        if successful_conversions == 0:
            batch_job.status = "failed"
            batch_job.drive_upload_status = "conversion_failed"
            batch_job.save(DEFAULT_DB_PATH)
            
            return {
                'success': False,
                'job_id': job_id,
                'error_message': 'All conversions failed',
                'error_type': 'conversion_failure',
                'conversion_results': conversion_results[:5],  # Limit results
            }
        
        # Proceed with Drive upload if we have successful conversions
        if converted_files and batch_job.drive_integration_enabled:
            batch_job.drive_upload_status = "uploading"
            batch_job.save(DEFAULT_DB_PATH)
            
            # Schedule Drive upload task
            upload_result = upload_batch_files_to_drive.schedule(
                args=(job_id, converted_files, 
                      upload_options.get('folder_pattern'),
                      upload_options.get('generate_previews', True)),
            )
            
            return {
                'success': True,
                'job_id': job_id,
                'conversion_results': {
                    'successful': successful_conversions,
                    'failed': len(conversion_results) - successful_conversions,
                    'total': len(conversion_results),
                },
                'upload_scheduled': True,
                'upload_task_id': str(upload_result) if upload_result else None,
                'status': 'conversion_complete_upload_scheduled',
            }
        else:
            # No Drive upload needed or enabled
            batch_job.status = "completed" if successful_conversions > 0 else "partial"
            batch_job.save(DEFAULT_DB_PATH)
            
            return {
                'success': True,
                'job_id': job_id,
                'conversion_results': {
                    'successful': successful_conversions,
                    'failed': len(conversion_results) - successful_conversions,
                    'total': len(conversion_results),
                },
                'upload_scheduled': False,
                'status': 'conversion_complete_no_upload',
            }
        
    except Exception as e:
        logger.error(f"Error coordinating pipeline for job {job_id}: {e}")
        
        # Update job status
        try:
            batch_job = BatchJob.get_by_id(job_id, DEFAULT_DB_PATH)
            if batch_job:
                batch_job.status = "failed"
                batch_job.drive_upload_status = "pipeline_error"
                batch_job.save(DEFAULT_DB_PATH)
        except Exception:
            pass
        
        return {
            'success': False,
            'job_id': job_id,
            'error_message': str(e),
            'error_type': 'pipeline_coordination_error',
        }


@huey.task()
def monitor_pipeline_progress(job_id: str) -> dict[str, Any]:
    """
    Monitor progress of conversion and upload pipeline.
    
    Args:
        job_id: Batch job identifier
        
    Returns:
        Dictionary with pipeline progress information
    """
    try:
        import json
        from datetime import datetime
        
        batch_job = BatchJob.get_by_id(job_id, DEFAULT_DB_PATH)
        if not batch_job:
            return {
                'success': False,
                'error_message': f'Batch job {job_id} not found',
                'error_type': 'job_not_found',
            }
        
        # Get job metadata
        metadata = json.loads(batch_job.metadata) if batch_job.metadata else {}
        
        # Get Drive metadata if available
        drive_metadata = None
        try:
            from src.batch.models import BatchDriveMetadata
            drive_metadata = BatchDriveMetadata.get_by_job_id(job_id, DEFAULT_DB_PATH)
        except Exception:
            pass
        
        # Calculate overall progress
        total_files = metadata.get('total_files', 0)
        if total_files == 0:
            total_files = len(metadata.get('files', []))
        
        # Conversion progress
        conversion_progress = {
            'completed': metadata.get('completed_conversions', 0),
            'failed': metadata.get('failed_conversions', 0),
            'total': total_files,
            'percentage': 0,
        }
        
        if total_files > 0:
            conversion_progress['percentage'] = round(
                (conversion_progress['completed'] / total_files) * 100, 1,
            )
        
        # Upload progress
        upload_progress = {
            'completed': 0,
            'failed': 0,
            'total': conversion_progress['completed'],
            'percentage': 0,
        }
        
        if drive_metadata:
            # Get file upload status from drive metadata
            file_metadata_list = drive_metadata.get_file_metadata_list(DEFAULT_DB_PATH)
            upload_progress['completed'] = len([f for f in file_metadata_list if f.upload_status == 'completed'])
            upload_progress['failed'] = len([f for f in file_metadata_list if f.upload_status == 'failed'])
            
            if upload_progress['total'] > 0:
                upload_progress['percentage'] = round(
                    (upload_progress['completed'] / upload_progress['total']) * 100, 1,
                )
        
        # Overall pipeline progress
        pipeline_stages = ['conversion', 'upload'] if batch_job.drive_integration_enabled else ['conversion']
        completed_stages = 0
        
        if conversion_progress['percentage'] >= 100:
            completed_stages += 1
        
        if batch_job.drive_integration_enabled and upload_progress['percentage'] >= 100:
            completed_stages += 1
        
        overall_percentage = round((completed_stages / len(pipeline_stages)) * 100, 1)
        
        # Determine current status
        current_stage = 'completed'
        if batch_job.status in ['processing', 'uploading']:
            if batch_job.drive_upload_status in ['waiting_for_conversion', 'not_started']:
                current_stage = 'conversion'
            elif batch_job.drive_upload_status in ['in_progress', 'uploading']:
                current_stage = 'upload'
        elif batch_job.status in ['failed']:
            current_stage = 'failed'
        
        # Estimate completion time
        estimated_completion = None
        if batch_job.created_at and overall_percentage > 0 and overall_percentage < 100:
            from datetime import datetime, timedelta
            start_time = datetime.fromisoformat(batch_job.created_at)
            elapsed_seconds = (datetime.utcnow() - start_time).total_seconds()
            
            if elapsed_seconds > 0:
                estimated_total_seconds = (elapsed_seconds / overall_percentage) * 100
                estimated_completion = start_time + timedelta(seconds=estimated_total_seconds)
        
        return {
            'success': True,
            'job_id': job_id,
            'pipeline_progress': {
                'overall_percentage': overall_percentage,
                'current_stage': current_stage,
                'stages': pipeline_stages,
                'completed_stages': completed_stages,
            },
            'conversion_progress': conversion_progress,
            'upload_progress': upload_progress,
            'job_status': batch_job.status,
            'drive_upload_status': batch_job.drive_upload_status,
            'estimated_completion': estimated_completion.isoformat() if estimated_completion else None,
            'last_updated': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error monitoring pipeline progress for job {job_id}: {e}")
        
        return {
            'success': False,
            'job_id': job_id,
            'error_message': str(e),
            'error_type': 'progress_monitoring_error',
        }


@huey.task()
def cleanup_completed_pipeline(job_id: str, cleanup_options: dict[str, Any] = None) -> dict[str, Any]:
    """
    Clean up resources after pipeline completion.
    
    Args:
        job_id: Batch job identifier
        cleanup_options: Options for cleanup (temp files, logs, etc.)
        
    Returns:
        Dictionary with cleanup results
    """
    try:
        import json
        import os
        import shutil
        
        cleanup_options = cleanup_options or {
            'remove_temp_files': True,
            'keep_logs': True,
            'archive_metadata': True,
        }
        
        batch_job = BatchJob.get_by_id(job_id, DEFAULT_DB_PATH)
        if not batch_job:
            return {
                'success': False,
                'error_message': f'Batch job {job_id} not found',
                'error_type': 'job_not_found',
            }
        
        cleanup_results = {
            'temp_files_removed': 0,
            'temp_dirs_removed': 0,
            'logs_archived': False,
            'metadata_archived': False,
        }
        
        # Get job metadata to find temp paths
        metadata = json.loads(batch_job.metadata) if batch_job.metadata else {}
        
        # Clean up temporary files
        if cleanup_options.get('remove_temp_files', True):
            temp_paths = metadata.get('temp_paths', [])
            for temp_path in temp_paths:
                try:
                    if os.path.exists(temp_path):
                        if os.path.isfile(temp_path):
                            os.unlink(temp_path)
                            cleanup_results['temp_files_removed'] += 1
                        elif os.path.isdir(temp_path):
                            shutil.rmtree(temp_path)
                            cleanup_results['temp_dirs_removed'] += 1
                except Exception as e:
                    logger.warning(f"Could not remove temp path {temp_path}: {e}")
        
        # Archive logs if requested
        if cleanup_options.get('keep_logs', True):
            try:
                log_data = {
                    'job_id': job_id,
                    'completed_at': datetime.utcnow().isoformat(),
                    'final_status': batch_job.status,
                    'drive_status': batch_job.drive_upload_status,
                    'metadata': metadata,
                }
                
                # Store in archived logs (implementation depends on log storage system)
                # This is a placeholder for actual log archiving
                cleanup_results['logs_archived'] = True
                
            except Exception as e:
                logger.error(f"Error archiving logs for job {job_id}: {e}")
        
        # Archive metadata if requested
        if cleanup_options.get('archive_metadata', True):
            try:
                # Update job with archival information
                metadata['archived_at'] = datetime.utcnow().isoformat()
                metadata['cleanup_completed'] = True
                batch_job.metadata = json.dumps(metadata)
                batch_job.save(DEFAULT_DB_PATH)
                
                cleanup_results['metadata_archived'] = True
                
            except Exception as e:
                logger.error(f"Error archiving metadata for job {job_id}: {e}")
        
        # Update job status
        if batch_job.status not in ['failed', 'error']:
            batch_job.status = 'archived'
        batch_job.save(DEFAULT_DB_PATH)
        
        logger.info(f"Pipeline cleanup completed for job {job_id}: {cleanup_results}")
        
        return {
            'success': True,
            'job_id': job_id,
            'cleanup_results': cleanup_results,
            'status': 'cleanup_completed',
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up pipeline for job {job_id}: {e}")
        
        return {
            'success': False,
            'job_id': job_id,
            'error_message': str(e),
            'error_type': 'cleanup_error',
        }


# Utility and Testing Tasks

@huey.task()
def test_drive_connection() -> dict[str, Any]:
    """
    Test Google Drive connection and authentication.
    
    Returns:
        Dictionary with connection test results
    """
    try:
        # Test Drive service
        drive_service = GoogleDriveService()
        drive_connection = drive_service.test_connection()
        
        # Test Slides service
        slides_service = GoogleSlidesService()
        # Note: GoogleSlidesService doesn't have a test_connection method
        # We'll just check if we can initialize it
        slides_connection = True
        
        return {
            'success': True,
            'drive_connection': drive_connection,
            'slides_connection': slides_connection,
            'status': 'connected',
            'tested_at': datetime.utcnow().isoformat(),
        }
        
    except GoogleDriveError as e:
        logger.error(f"Drive connection test failed: {e}")
        
        return {
            'success': False,
            'error_message': str(e),
            'error_type': 'authentication_error',
            'error_code': getattr(e, 'error_code', None),
            'status': 'disconnected',
            'tested_at': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Connection test error: {e}")
        
        return {
            'success': False,
            'error_message': str(e),
            'error_type': 'connection_error',
            'status': 'error',
            'tested_at': datetime.utcnow().isoformat(),
        }


@huey.periodic_task(cron_str='0 2 * * *', validate_datetime=True)  # Run daily at 2 AM
def cleanup_old_batch_data():
    """
    Periodic cleanup of old batch data and temporary files.
    
    Returns:
        Dictionary with cleanup results
    """
    try:
        logger.info("Starting periodic cleanup of old batch data")
        
        # Define cleanup thresholds
        old_data_threshold = datetime.utcnow() - timedelta(days=7)  # 7 days old
        
        cleaned_jobs = 0
        cleaned_files = 0
        
        # This would typically clean up old job records and temporary files
        # Implementation depends on specific cleanup requirements
        
        logger.info(f"Cleanup completed: {cleaned_jobs} jobs, {cleaned_files} files")
        
        return {
            'success': True,
            'cleaned_jobs': cleaned_jobs,
            'cleaned_files': cleaned_files,
            'cleanup_threshold': old_data_threshold.isoformat(),
            'completed_at': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error during periodic cleanup: {e}")
        
        return {
            'success': False,
            'error_message': str(e),
            'failed_at': datetime.utcnow().isoformat(),
        }


# Placeholder for SVG conversion task (would be implemented separately)
def convert_svg_batch(job_id: str, svg_urls: list[str], options: dict[str, Any]) -> dict[str, Any]:
    """
    Placeholder for SVG batch conversion task.
    
    This would typically be implemented as a separate Huey task that handles
    the actual SVG to PowerPoint conversion process.
    
    Args:
        job_id: Batch job identifier
        svg_urls: List of SVG URLs to convert
        options: Conversion options
        
    Returns:
        Dictionary with conversion results
    """
    # Placeholder implementation
    logger.info(f"Converting {len(svg_urls)} SVG files for job {job_id}")
    
    # In a real implementation, this would:
    # 1. Download SVG files from URLs
    # 2. Convert each to PowerPoint
    # 3. Store temporary files
    # 4. Return file info for Drive upload
    
    converted_files = []
    for i, url in enumerate(svg_urls):
        converted_files.append({
            'path': f'/tmp/{job_id}_file_{i+1}.pptx',
            'original_name': f'file_{i+1}.svg',
            'converted_name': f'{job_id}_file_{i+1}.pptx',
        })
    
    return {
        'success': True,
        'job_id': job_id,
        'converted_files': converted_files,
        'conversion_time': 5.0,  # Mock conversion time
        'completed_at': datetime.utcnow().isoformat(),
    }