#!/usr/bin/env python3
"""
Google Drive service wrapper for file operations.
"""

import os
import json
from typing import Dict, Optional, Any
from pathlib import Path
import logging

from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as OAuthCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from ..config import get_settings
from .google_oauth import GoogleOAuthService, GoogleOAuthError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleDriveError(Exception):
    """Custom exception for Google Drive operations."""
    
    def __init__(self, message: str, error_code: Optional[int] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class GoogleDriveService:
    """
    Google Drive API service wrapper.
    
    Handles file upload, update, sharing, and metadata operations.
    """
    
    # Required scopes for Google Drive and Slides operations
    SCOPES = [
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive.metadata',
        'https://www.googleapis.com/auth/presentations.readonly'
    ]
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Google Drive service.
        
        Args:
            credentials_path: Path to service account JSON file
        """
        self.settings = get_settings()
        self.credentials_path = credentials_path or self.settings.google_drive_credentials_path
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Drive API service."""
        try:
            # Choose authentication method
            if self.settings.google_drive_auth_method == "oauth":
                logger.info("Using OAuth authentication")
                credentials = self._get_oauth_credentials()
            else:
                logger.info("Using service account authentication")
                credentials = self._get_service_account_credentials()
            
            # Build service
            self.service = build('drive', 'v3', credentials=credentials)
            logger.info("Google Drive service initialized successfully")
            
        except Exception as e:
            raise GoogleDriveError(f"Failed to initialize Google Drive service: {e}")
    
    def _get_oauth_credentials(self):
        """Get OAuth credentials."""
        try:
            oauth_service = GoogleOAuthService()
            return oauth_service.get_credentials()
        except GoogleOAuthError as e:
            raise GoogleDriveError(f"OAuth authentication failed: {e.message}")
    
    def _get_service_account_credentials(self):
        """Get service account credentials."""
        try:
            # Validate credentials file exists
            if not os.path.exists(self.credentials_path):
                raise GoogleDriveError(
                    f"Google Drive credentials file not found: {self.credentials_path}"
                )
            
            # Load and validate credentials
            with open(self.credentials_path, 'r') as f:
                cred_data = json.load(f)
            
            # Validate required fields
            required_fields = ['type', 'project_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if field not in cred_data]
            if missing_fields:
                raise GoogleDriveError(
                    f"Missing required fields in credentials: {missing_fields}"
                )
            
            # Create credentials
            credentials = ServiceAccountCredentials.from_service_account_file(
                self.credentials_path,
                scopes=self.SCOPES
            )
            
            return credentials
            
        except json.JSONDecodeError as e:
            raise GoogleDriveError(f"Invalid JSON in credentials file: {e}")
        except Exception as e:
            raise GoogleDriveError(f"Service account authentication failed: {e}")
    
    def test_connection(self) -> bool:
        """
        Test Google Drive API connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Simple API call to test connection
            self.service.about().get(fields="user").execute()
            logger.info("Google Drive connection test successful")
            return True
        except Exception as e:
            logger.error(f"Google Drive connection test failed: {e}")
            return False
    
    def upload_file(self, file_path: str, file_name: str, 
                   folder_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload file to Google Drive.
        
        Args:
            file_path: Local path to file to upload
            file_name: Name for the file in Google Drive
            folder_id: Optional folder ID to upload to
            
        Returns:
            Dictionary with file information
        """
        try:
            if not os.path.exists(file_path):
                raise GoogleDriveError(f"File not found: {file_path}")
            
            # Prepare file metadata
            file_metadata = {
                'name': file_name,
                'parents': [folder_id] if folder_id else []
            }
            
            # Determine MIME type
            mime_type = self._get_mime_type(file_name)
            
            # Create media upload
            media = MediaFileUpload(
                file_path,
                mimetype=mime_type,
                resumable=True
            )
            
            # Upload file
            logger.info(f"Uploading file: {file_name}")
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink,size'
            ).execute()
            
            # Make file publicly accessible
            self.make_file_public(file['id'])
            
            # Get shareable link
            shareable_link = self.get_shareable_link(file['id'])
            
            result = {
                'success': True,
                'fileId': file['id'],
                'fileName': file['name'],
                'shareableLink': shareable_link,
                'fileSize': int(file.get('size', 0)),
                'webViewLink': file.get('webViewLink')
            }
            
            logger.info(f"File uploaded successfully: {file['id']}")
            return result
            
        except HttpError as e:
            error_msg = self._extract_error_message(e)
            logger.error(f"HTTP error during file upload: {error_msg}")
            raise GoogleDriveError(f"Upload failed: {error_msg}", e.resp.status)
        except Exception as e:
            logger.error(f"Unexpected error during file upload: {e}")
            raise GoogleDriveError(f"Upload failed: {e}")
    
    def update_file(self, file_id: str, file_path: str, 
                   file_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Update existing file in Google Drive.
        
        Args:
            file_id: Google Drive file ID to update
            file_path: Local path to replacement file
            file_name: Optional new name for the file
            
        Returns:
            Dictionary with updated file information
        """
        try:
            if not os.path.exists(file_path):
                raise GoogleDriveError(f"File not found: {file_path}")
            
            # Prepare file metadata (only if name is being changed)
            file_metadata = {}
            if file_name:
                file_metadata['name'] = file_name
            
            # Determine MIME type
            mime_type = self._get_mime_type(file_name or file_path)
            
            # Create media upload
            media = MediaFileUpload(
                file_path,
                mimetype=mime_type,
                resumable=True
            )
            
            # Update file
            logger.info(f"Updating file: {file_id}")
            file = self.service.files().update(
                fileId=file_id,
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink,size'
            ).execute()
            
            # Ensure file is publicly accessible
            self.make_file_public(file['id'])
            
            # Get shareable link
            shareable_link = self.get_shareable_link(file['id'])
            
            result = {
                'success': True,
                'fileId': file['id'],
                'fileName': file['name'],
                'shareableLink': shareable_link,
                'fileSize': int(file.get('size', 0)),
                'webViewLink': file.get('webViewLink'),
                'updated': True
            }
            
            logger.info(f"File updated successfully: {file['id']}")
            return result
            
        except HttpError as e:
            error_msg = self._extract_error_message(e)
            logger.error(f"HTTP error during file update: {error_msg}")
            raise GoogleDriveError(f"Update failed: {error_msg}", e.resp.status)
        except Exception as e:
            logger.error(f"Unexpected error during file update: {e}")
            raise GoogleDriveError(f"Update failed: {e}")
    
    def make_file_public(self, file_id: str) -> bool:
        """
        Make file publicly readable.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            True if successful
        """
        try:
            permission = {
                'role': 'reader',
                'type': 'anyone'
            }
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            
            logger.info(f"File made public: {file_id}")
            return True
            
        except HttpError as e:
            logger.warning(f"Could not make file public: {self._extract_error_message(e)}")
            return False
        except Exception as e:
            logger.warning(f"Could not make file public: {e}")
            return False
    
    def get_shareable_link(self, file_id: str) -> str:
        """
        Get shareable link for file.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            Shareable link URL
        """
        try:
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields='webViewLink,webContentLink'
            ).execute()
            
            # Prefer webViewLink for presentations
            link = file_metadata.get('webViewLink') or file_metadata.get('webContentLink')
            
            if not link:
                # Fallback to constructed link
                link = f"https://drive.google.com/file/d/{file_id}/view"
            
            return link
            
        except Exception as e:
            logger.warning(f"Could not get shareable link: {e}")
            # Return fallback link
            return f"https://drive.google.com/file/d/{file_id}/view"
    
    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Get file metadata from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            File metadata dictionary
        """
        try:
            metadata = self.service.files().get(
                fileId=file_id,
                fields='id,name,size,mimeType,createdTime,modifiedTime,webViewLink'
            ).execute()
            
            return metadata
            
        except HttpError as e:
            error_msg = self._extract_error_message(e)
            raise GoogleDriveError(f"Could not get file metadata: {error_msg}", e.resp.status)
    
    def _get_mime_type(self, file_name: str) -> str:
        """
        Get MIME type for file based on extension.
        
        Args:
            file_name: Name of the file
            
        Returns:
            MIME type string
        """
        extension = Path(file_name).suffix.lower()
        
        mime_types = {
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.svg': 'image/svg+xml'
        }
        
        return mime_types.get(extension, 'application/octet-stream')
    
    def _extract_error_message(self, error: HttpError) -> str:
        """
        Extract readable error message from HttpError.
        
        Args:
            error: HttpError from Google API
            
        Returns:
            Human-readable error message
        """
        try:
            if hasattr(error, 'content'):
                error_content = json.loads(error.content.decode('utf-8'))
                return error_content.get('error', {}).get('message', str(error))
        except:
            pass
        
        return str(error)
    
    def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a folder in Google Drive.
        
        Args:
            folder_name: Name of the folder to create
            parent_id: Optional parent folder ID
            
        Returns:
            Dictionary with folder information
        """
        try:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                folder_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id,name,webViewLink'
            ).execute()
            
            logger.info(f"Created folder '{folder_name}' with ID: {folder['id']}")
            
            return {
                'success': True,
                'folderId': folder['id'],
                'folderName': folder['name'],
                'folderUrl': folder.get('webViewLink', f"https://drive.google.com/drive/folders/{folder['id']}")
            }
            
        except HttpError as e:
            error_msg = self._extract_error_message(e)
            logger.error(f"HTTP error during folder creation: {error_msg}")
            raise GoogleDriveError(f"Folder creation failed: {error_msg}", e.resp.status)
        
        except Exception as e:
            logger.error(f"Unexpected error during folder creation: {e}")
            raise GoogleDriveError(f"Folder creation failed: {e}")


# Convenience function for quick testing
def test_google_drive_setup():
    """Test Google Drive setup and connection."""
    try:
        drive_service = GoogleDriveService()
        if drive_service.test_connection():
            print("✅ Google Drive service is properly configured and connected")
            return True
        else:
            print("❌ Google Drive connection failed")
            return False
    except GoogleDriveError as e:
        print(f"❌ Google Drive setup error: {e.message}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    # Test the Google Drive service
    test_google_drive_setup()