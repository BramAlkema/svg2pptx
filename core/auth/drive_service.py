#!/usr/bin/env python3
"""
Google Drive service for file uploads and Slides conversion.
"""

import io
import logging
from typing import Dict

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

logger = logging.getLogger(__name__)


class DriveError(Exception):
    """Drive-related errors."""
    pass


class GoogleDriveService:
    """Google Drive API service for file operations."""

    def __init__(self, credentials: Credentials):
        """
        Initialize Drive service.

        Args:
            credentials: Valid Google OAuth credentials
        """
        self.credentials = credentials
        self.service = build('drive', 'v3', credentials=credentials)

    def upload_and_convert_to_slides(
        self,
        pptx_bytes: bytes,
        title: str,
        parent_folder_id: str = None,
    ) -> Dict[str, str]:
        """
        Upload PPTX and auto-convert to Google Slides in one call.

        Args:
            pptx_bytes: PPTX file bytes
            title: Presentation title
            parent_folder_id: Optional Google Drive folder ID

        Returns:
            {
                'slides_id': str,
                'slides_url': str,
                'web_view_link': str,
            }

        Raises:
            DriveError: If upload or conversion fails
        """
        try:
            # Create media upload
            media = MediaIoBaseUpload(
                io.BytesIO(pptx_bytes),
                mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation',
                resumable=True,
            )

            # Prepare metadata
            body = {
                'name': title,
                'mimeType': 'application/vnd.google-apps.presentation',  # Triggers conversion
            }

            if parent_folder_id:
                body['parents'] = [parent_folder_id]

            # Upload and convert
            result = self.service.files().create(
                body=body,
                media_body=media,
                fields='id,webViewLink,mimeType'
            ).execute()

            slides_id = result['id']

            logger.info(
                f"Successfully uploaded and converted to Slides: {title} (ID: {slides_id})"
            )

            return {
                'slides_id': slides_id,
                'slides_url': f'https://docs.google.com/presentation/d/{slides_id}/edit',
                'web_view_link': result.get('webViewLink', ''),
            }

        except Exception as e:
            logger.error(f"Failed to upload and convert to Slides: {e}")
            raise DriveError(f"Upload failed: {e}")

    def create_folder(self, name: str, parent_folder_id: str = None) -> str:
        """
        Create a folder in Google Drive.

        Args:
            name: Folder name
            parent_folder_id: Optional parent folder ID

        Returns:
            Created folder ID
        """
        try:
            body = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder',
            }

            if parent_folder_id:
                body['parents'] = [parent_folder_id]

            result = self.service.files().create(
                body=body,
                fields='id'
            ).execute()

            return result['id']

        except Exception as e:
            logger.error(f"Failed to create folder: {e}")
            raise DriveError(f"Folder creation failed: {e}")
