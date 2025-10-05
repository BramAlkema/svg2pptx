#!/usr/bin/env python3
"""
Clean Slate Batch Coordinator

Coordinates complete batch workflow: SVG conversion + Drive upload.
Integrates Clean Slate tasks with existing Drive infrastructure.
"""

import logging
import sys
from pathlib import Path
from typing import Any

# Import Huey instance from tasks
from .tasks import convert_multiple_svgs_clean_slate, huey

# Import Clean Slate batch job model
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.batch.models import CleanSlateBatchJob

# Import Drive upload tasks (reuse existing infrastructure)
try:
    from src.batch.drive_tasks import upload_batch_files_to_drive
    DRIVE_AVAILABLE = True
except ImportError:
    DRIVE_AVAILABLE = False
    logging.warning("Drive tasks not available - Drive integration disabled")

logger = logging.getLogger(__name__)


class CoordinatorError(Exception):
    """Exception raised when batch coordination fails"""
    pass


@huey.task()
def coordinate_batch_workflow_clean_slate(
    job_id: str,
    file_paths: list[str],
    conversion_options: dict[str, Any] = None,
) -> dict[str, Any]:
    """
    Coordinate complete batch workflow using Clean Slate architecture.

    Flow:
    1. Get BatchJob from database
    2. Convert multiple SVGs using Clean Slate (with E2E tracing)
    3. Upload to Drive (if enabled)
    4. Aggregate and store trace data
    5. Update job status

    Args:
        job_id: Batch job identifier
        file_paths: List of SVG file paths to convert
        conversion_options: Optional conversion parameters including:
            - enable_debug: bool (default True for batch)
            - quality: str (fast/balanced/high)
            - generate_previews: bool (for Drive upload)

    Returns:
        Dictionary with complete workflow result including:
            - success: bool
            - job_id: str
            - conversion: Dict (conversion result with traces)
            - upload: Dict (Drive upload result, if enabled)
            - architecture: str ('clean_slate')
    """
    try:
        logger.info(f"🚀 Clean Slate batch workflow starting for job {job_id}")

        # Step 1: Get batch job from in-memory store
        batch_job = CleanSlateBatchJob.get_by_id(job_id)
        if not batch_job:
            error_msg = f"BatchJob {job_id} not found in memory"
            logger.error(error_msg)
            return {
                'success': False,
                'job_id': job_id,
                'error_message': error_msg,
                'error_type': 'job_not_found',
                'architecture': 'clean_slate',
            }

        # Step 2: Update status to processing
        batch_job.status = "processing"
        batch_job.save()
        logger.info(f"Job {job_id} status updated to 'processing'")

        # Step 3: Convert SVGs using Clean Slate
        options = conversion_options or {}

        # Create output path for batch
        output_dir = Path("/tmp/batch_output")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / f"{job_id}.pptx")

        logger.info(f"Converting {len(file_paths)} SVG files to {output_path}")

        # Call Clean Slate conversion task
        conversion_result = convert_multiple_svgs_clean_slate(
            file_paths=file_paths,
            output_path=output_path,
            conversion_options={
                'enable_debug': True,  # Always enable tracing for batch jobs
                'quality': options.get('quality', 'high'),
            },
        )

        # Handle Huey Result wrapper (in immediate mode, it's callable)
        if hasattr(conversion_result, '__call__'):
            conversion_result = conversion_result()

        # Check conversion success
        if not conversion_result.get('success'):
            batch_job.status = "failed"
            batch_job.save()
            logger.error(f"Conversion failed for job {job_id}: {conversion_result.get('error_message')}")
            return conversion_result

        logger.info(f"✅ Conversion succeeded: {conversion_result['page_count']} pages, "
                   f"{conversion_result['output_size_bytes']} bytes")

        # Step 4: Upload to Drive if enabled
        if batch_job.drive_integration_enabled and DRIVE_AVAILABLE:
            logger.info("Drive integration enabled, uploading to Drive")

            batch_job.status = "uploading"
            batch_job.drive_upload_status = "in_progress"
            batch_job.save()

            # Prepare files for Drive upload
            files = [{
                'path': output_path,
                'original_name': f'{job_id}.pptx',
                'converted_name': f'{job_id}.pptx',
            }]

            # Call Drive upload task
            try:
                upload_result = upload_batch_files_to_drive(
                    job_id=job_id,
                    files=files,
                    folder_pattern=batch_job.drive_folder_pattern,
                    generate_previews=options.get('generate_previews', True),
                )

                # Handle Huey Result wrapper
                if hasattr(upload_result, '__call__'):
                    upload_result = upload_result()

                # Check upload success
                if upload_result.get('success'):
                    batch_job.status = "completed"
                    batch_job.drive_upload_status = "completed"
                    logger.info(f"✅ Drive upload completed for job {job_id}")
                else:
                    batch_job.status = "failed"
                    batch_job.drive_upload_status = "failed"
                    logger.error(f"Drive upload failed: {upload_result.get('error_message')}")

                # Store trace data in job
                if conversion_result.get('debug_trace'):
                    batch_job.trace_data = {
                        'architecture': 'clean_slate',
                        'page_count': conversion_result.get('page_count', 0),
                        'workflow': 'conversion_and_drive',
                        'debug_trace': conversion_result['debug_trace'],
                    }

                batch_job.save()

                return {
                    'success': True,
                    'job_id': job_id,
                    'conversion': conversion_result,
                    'upload': upload_result,
                    'architecture': 'clean_slate',
                    'workflow': 'conversion_and_drive',
                }

            except Exception as upload_error:
                logger.error(f"Drive upload error for job {job_id}: {upload_error}")
                batch_job.status = "completed_upload_failed"
                batch_job.drive_upload_status = "failed"
                batch_job.save()

                return {
                    'success': True,  # Conversion succeeded
                    'job_id': job_id,
                    'conversion': conversion_result,
                    'upload': {
                        'success': False,
                        'error_message': str(upload_error),
                    },
                    'architecture': 'clean_slate',
                    'workflow': 'conversion_only_upload_failed',
                }

        else:
            # No Drive upload requested or available
            batch_job.status = "completed"

            # Store trace data in job
            if conversion_result.get('debug_trace'):
                batch_job.trace_data = {
                    'architecture': 'clean_slate',
                    'page_count': conversion_result.get('page_count', 0),
                    'workflow': 'conversion_only',
                    'debug_trace': conversion_result['debug_trace'],
                }

            batch_job.save()
            logger.info(f"✅ Batch job {job_id} completed (no Drive upload)")

            return {
                'success': True,
                'job_id': job_id,
                'conversion': conversion_result,
                'architecture': 'clean_slate',
                'workflow': 'conversion_only',
            }

    except Exception as e:
        logger.error(f"❌ Batch workflow error for job {job_id}: {e}", exc_info=True)

        # Update job status to failed
        try:
            batch_job = CleanSlateBatchJob.get_by_id(job_id)
            if batch_job:
                batch_job.status = "failed"
                batch_job.save()
        except Exception as update_error:
            logger.error(f"Failed to update job status: {update_error}")

        return {
            'success': False,
            'job_id': job_id,
            'error_message': str(e),
            'error_type': type(e).__name__,
            'architecture': 'clean_slate',
        }


def get_coordinator_info() -> dict[str, Any]:
    """
    Get information about the batch coordinator.

    Returns:
        Dictionary with coordinator capabilities and status
    """
    return {
        'coordinator': 'clean_slate_batch',
        'version': '1.0.0',
        'architecture': 'clean_slate',
        'capabilities': {
            'multi_svg_conversion': True,
            'e2e_tracing': True,
            'drive_integration': DRIVE_AVAILABLE,
            'status_tracking': True,
            'error_recovery': True,
        },
        'workflow_stages': [
            'job_retrieval',
            'status_update_processing',
            'svg_conversion',
            'drive_upload (optional)',
            'status_update_completed',
            'trace_aggregation',
        ],
        'trace_data_available': [
            'parse_result',
            'analysis_result',
            'mapper_results',
            'embedder_result',
            'package_debug_data',
        ],
    }
