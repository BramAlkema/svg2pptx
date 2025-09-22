#!/usr/bin/env python3
"""
Google Slides Converter Module

Converts PPTX files to Google Slides by uploading to Google Drive and
using the Google Slides API to convert and manage presentations.
"""

import os
import io
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

# Google API imports
try:
    from googleapiclient.http import MediaIoBaseUpload, MediaFileUpload
    from googleapiclient.errors import HttpError
    GOOGLE_APIS_AVAILABLE = True
except ImportError:
    GOOGLE_APIS_AVAILABLE = False

from .authenticator import GoogleSlidesAuthenticator

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """Result of PPTX to Google Slides conversion."""
    success: bool
    presentation_id: Optional[str] = None
    drive_file_id: Optional[str] = None
    presentation_url: Optional[str] = None
    error_message: Optional[str] = None
    conversion_time: float = 0.0
    file_size: int = 0
    slide_count: Optional[int] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SlidesConverter:
    """Convert PPTX files to Google Slides."""

    def __init__(self, auth: GoogleSlidesAuthenticator):
        """
        Initialize converter.

        Args:
            auth: Authenticated GoogleSlidesAuthenticator instance
        """
        if not GOOGLE_APIS_AVAILABLE:
            raise ImportError("Google API libraries not available")

        if not auth.is_authenticated:
            raise ValueError("Authenticator must be authenticated before use")

        self.auth = auth
        self.drive_service = auth.get_drive_service()
        self.slides_service = auth.get_slides_service()

        logger.info("SlidesConverter initialized")

    def upload_pptx_to_drive(self, pptx_path: Path, folder_id: Optional[str] = None,
                           custom_name: Optional[str] = None) -> str:
        """
        Upload PPTX to Google Drive.

        Args:
            pptx_path: Path to PPTX file
            folder_id: Optional Drive folder ID for organization
            custom_name: Optional custom name for uploaded file

        Returns:
            Google Drive file ID

        Raises:
            FileNotFoundError: If PPTX file doesn't exist
            HttpError: If upload fails
        """
        if not pptx_path.exists():
            raise FileNotFoundError(f"PPTX file not found: {pptx_path}")

        try:
            # Prepare file metadata
            file_name = custom_name or pptx_path.name
            file_metadata = {
                'name': file_name,
                'description': f'SVG2PPTX upload - {datetime.now().isoformat()}'
            }

            if folder_id:
                file_metadata['parents'] = [folder_id]

            # Upload file
            media = MediaFileUpload(
                str(pptx_path),
                mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'
            )

            request = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,size,webViewLink'
            )

            result = request.execute()
            file_id = result.get('id')

            logger.info(f"PPTX uploaded to Drive: {file_id} ({file_name})")
            return file_id

        except HttpError as e:
            logger.error(f"Drive upload failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected upload error: {e}")
            raise

    def convert_to_slides(self, drive_file_id: str, delete_original: bool = True) -> str:
        """
        Convert uploaded PPTX to Google Slides.

        Args:
            drive_file_id: Google Drive file ID of PPTX
            delete_original: Whether to delete original PPTX after conversion

        Returns:
            Presentation ID of converted Google Slides

        Raises:
            HttpError: If conversion fails
        """
        try:
            # Get original file info
            original_file = self.drive_service.files().get(fileId=drive_file_id).execute()
            original_name = original_file.get('name', 'Converted Presentation')

            # Create a copy and convert to Google Slides format
            slides_name = f"{original_name.replace('.pptx', '')} - Google Slides"
            copy_metadata = {
                'name': slides_name,
                'description': f'SVG2PPTX Google Slides conversion - {datetime.now().isoformat()}'
            }

            # Create copy request
            copy_request = self.drive_service.files().copy(
                fileId=drive_file_id,
                body=copy_metadata,
                fields='id,name,webViewLink,mimeType'
            )

            # Execute copy - this triggers conversion to Google Slides format
            slides_file = copy_request.execute()
            presentation_id = slides_file.get('id')

            # Wait for conversion to complete
            self._wait_for_conversion(presentation_id)

            # Delete original PPTX if requested
            if delete_original:
                try:
                    self.drive_service.files().delete(fileId=drive_file_id).execute()
                    logger.info(f"Original PPTX deleted: {drive_file_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete original PPTX: {e}")

            logger.info(f"PPTX converted to Google Slides: {presentation_id}")
            return presentation_id

        except HttpError as e:
            logger.error(f"Slides conversion failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected conversion error: {e}")
            raise

    def get_presentation_url(self, presentation_id: str) -> str:
        """
        Get viewable URL for presentation.

        Args:
            presentation_id: Google Slides presentation ID

        Returns:
            Public viewing URL
        """
        try:
            file_info = self.drive_service.files().get(
                fileId=presentation_id,
                fields='webViewLink'
            ).execute()

            url = file_info.get('webViewLink')
            if not url:
                # Fallback URL construction
                url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"

            logger.info(f"Presentation URL retrieved: {presentation_id}")
            return url

        except HttpError as e:
            logger.error(f"Failed to get presentation URL: {e}")
            # Return fallback URL
            return f"https://docs.google.com/presentation/d/{presentation_id}/edit"

    def get_presentation_info(self, presentation_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a presentation.

        Args:
            presentation_id: Google Slides presentation ID

        Returns:
            Dictionary with presentation details
        """
        try:
            # Get file metadata from Drive
            file_info = self.drive_service.files().get(
                fileId=presentation_id,
                fields='id,name,size,createdTime,modifiedTime,webViewLink,mimeType'
            ).execute()

            # Get presentation structure from Slides API
            presentation = self.slides_service.presentations().get(
                presentationId=presentation_id
            ).execute()

            info = {
                'presentation_id': presentation_id,
                'title': presentation.get('title', 'Untitled'),
                'slide_count': len(presentation.get('slides', [])),
                'size': file_info.get('size'),
                'created_time': file_info.get('createdTime'),
                'modified_time': file_info.get('modifiedTime'),
                'web_view_link': file_info.get('webViewLink'),
                'mime_type': file_info.get('mimeType'),
                'page_size': presentation.get('pageSize', {}),
                'master_count': len(presentation.get('masters', [])),
                'layout_count': len(presentation.get('layouts', []))
            }

            logger.info(f"Presentation info retrieved: {presentation_id}")
            return info

        except HttpError as e:
            logger.error(f"Failed to get presentation info: {e}")
            return {'error': str(e)}
        except Exception as e:
            logger.error(f"Unexpected error getting presentation info: {e}")
            return {'error': str(e)}

    def convert_pptx_full_workflow(self, pptx_path: Path, folder_id: Optional[str] = None,
                                 custom_name: Optional[str] = None,
                                 delete_original_pptx: bool = True) -> ConversionResult:
        """
        Complete workflow: upload PPTX, convert to Slides, return results.

        Args:
            pptx_path: Path to PPTX file
            folder_id: Optional Drive folder for organization
            custom_name: Optional custom name for files
            delete_original_pptx: Whether to delete uploaded PPTX after conversion

        Returns:
            ConversionResult with complete conversion details
        """
        start_time = time.time()
        result = ConversionResult(success=False)

        try:
            # Validate input
            if not pptx_path.exists():
                result.error_message = f"PPTX file not found: {pptx_path}"
                return result

            result.file_size = pptx_path.stat().st_size

            # Step 1: Upload PPTX to Drive
            logger.info(f"Starting PPTX conversion workflow: {pptx_path}")
            drive_file_id = self.upload_pptx_to_drive(pptx_path, folder_id, custom_name)
            result.drive_file_id = drive_file_id

            # Step 2: Convert to Google Slides
            presentation_id = self.convert_to_slides(drive_file_id, delete_original_pptx)
            result.presentation_id = presentation_id

            # Step 3: Get presentation URL
            presentation_url = self.get_presentation_url(presentation_id)
            result.presentation_url = presentation_url

            # Step 4: Get presentation details
            presentation_info = self.get_presentation_info(presentation_id)
            result.slide_count = presentation_info.get('slide_count')
            result.metadata = presentation_info

            # Mark as successful
            result.success = True
            result.conversion_time = time.time() - start_time

            logger.info(f"PPTX conversion completed successfully in {result.conversion_time:.2f}s")
            return result

        except Exception as e:
            result.error_message = str(e)
            result.conversion_time = time.time() - start_time
            logger.error(f"PPTX conversion failed: {e}")
            return result

    def batch_convert_pptx(self, pptx_files: List[Path], folder_id: Optional[str] = None,
                         progress_callback: Optional[callable] = None) -> List[ConversionResult]:
        """
        Convert multiple PPTX files to Google Slides.

        Args:
            pptx_files: List of PPTX file paths
            folder_id: Optional Drive folder for organization
            progress_callback: Optional callback function for progress updates

        Returns:
            List of ConversionResult objects
        """
        results = []
        total_files = len(pptx_files)

        logger.info(f"Starting batch conversion of {total_files} PPTX files")

        for i, pptx_path in enumerate(pptx_files):
            try:
                if progress_callback:
                    progress_callback(i, total_files, str(pptx_path))

                result = self.convert_pptx_full_workflow(pptx_path, folder_id)
                results.append(result)

                if result.success:
                    logger.info(f"Batch {i+1}/{total_files}: SUCCESS - {pptx_path.name}")
                else:
                    logger.warning(f"Batch {i+1}/{total_files}: FAILED - {pptx_path.name}: {result.error_message}")

            except Exception as e:
                error_result = ConversionResult(
                    success=False,
                    error_message=str(e),
                    file_size=pptx_path.stat().st_size if pptx_path.exists() else 0
                )
                results.append(error_result)
                logger.error(f"Batch {i+1}/{total_files}: ERROR - {pptx_path.name}: {e}")

        successful = sum(1 for r in results if r.success)
        logger.info(f"Batch conversion completed: {successful}/{total_files} successful")

        return results

    def delete_presentation(self, presentation_id: str) -> bool:
        """
        Delete a Google Slides presentation.

        Args:
            presentation_id: Presentation ID to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            self.drive_service.files().delete(fileId=presentation_id).execute()
            logger.info(f"Presentation deleted: {presentation_id}")
            return True

        except HttpError as e:
            logger.error(f"Failed to delete presentation {presentation_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting presentation {presentation_id}: {e}")
            return False

    def _wait_for_conversion(self, presentation_id: str, max_wait_time: int = 60,
                           check_interval: float = 2.0) -> bool:
        """
        Wait for PPTX to Google Slides conversion to complete.

        Args:
            presentation_id: Presentation ID to monitor
            max_wait_time: Maximum time to wait in seconds
            check_interval: Time between checks in seconds

        Returns:
            True if conversion completed, False if timeout
        """
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            try:
                # Check if presentation is accessible via Slides API
                presentation = self.slides_service.presentations().get(
                    presentationId=presentation_id
                ).execute()

                # If we can access slides, conversion is complete
                if presentation.get('slides'):
                    logger.info(f"Conversion completed for {presentation_id}")
                    return True

            except HttpError as e:
                # Conversion might still be in progress
                if e.resp.status == 404:
                    logger.debug(f"Conversion still in progress for {presentation_id}")
                else:
                    logger.warning(f"Error checking conversion status: {e}")

            time.sleep(check_interval)

        logger.warning(f"Conversion timeout for {presentation_id}")
        return False

    def create_test_folder(self, folder_name: str = "SVG2PPTX Visual Tests") -> str:
        """
        Create a folder in Google Drive for organizing test presentations.

        Args:
            folder_name: Name for the test folder

        Returns:
            Folder ID

        Raises:
            HttpError: If folder creation fails
        """
        try:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'description': f'SVG2PPTX Visual Testing - Created {datetime.now().isoformat()}'
            }

            folder = self.drive_service.files().create(
                body=folder_metadata,
                fields='id,name,webViewLink'
            ).execute()

            folder_id = folder.get('id')
            logger.info(f"Test folder created: {folder_name} ({folder_id})")
            return folder_id

        except HttpError as e:
            logger.error(f"Failed to create test folder: {e}")
            raise