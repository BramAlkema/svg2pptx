#!/usr/bin/env python3
"""
Google Slides Authentication Module

Handles Google Slides API authentication using both OAuth2 and Service Account methods.
Provides cached credentials and authenticated service factories for Google Drive and Slides APIs.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta

# Google API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_APIS_AVAILABLE = True
except ImportError:
    GOOGLE_APIS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class AuthConfig:
    """Configuration for Google API authentication."""
    method: str = 'service_account'  # 'oauth2' or 'service_account'
    credentials_path: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    project_id: Optional[str] = None
    redirect_uri: str = 'http://localhost:8080'
    scopes: list = None
    token_cache_path: Optional[str] = None

    def __post_init__(self):
        if self.scopes is None:
            self.scopes = [
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/presentations',
                'https://www.googleapis.com/auth/drive.file'
            ]


class GoogleSlidesAuthenticator:
    """Handle Google Slides API authentication."""

    def __init__(self, auth_method: str = 'service_account'):
        """
        Initialize authenticator.

        Args:
            auth_method: Authentication method ('oauth2' or 'service_account')
        """
        if not GOOGLE_APIS_AVAILABLE:
            raise ImportError(
                "Google API libraries not available. Install with: "
                "pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2"
            )

        self.auth_method = auth_method
        self.credentials = None
        self.slides_service = None
        self.drive_service = None
        self.config = None
        self._authenticated = False

        logger.info(f"GoogleSlidesAuthenticator initialized with method: {auth_method}")

    def configure(self, config: Union[AuthConfig, Dict[str, Any]]) -> None:
        """
        Configure authentication parameters.

        Args:
            config: AuthConfig object or dictionary with configuration
        """
        if isinstance(config, dict):
            self.config = AuthConfig(**config)
        else:
            self.config = config

        self.auth_method = self.config.method
        logger.info(f"Authentication configured for method: {self.auth_method}")

    def authenticate(self, credentials_path: Optional[str] = None) -> bool:
        """
        Authenticate with Google APIs.

        Args:
            credentials_path: Path to credentials file (overrides config)

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            if credentials_path:
                creds_path = credentials_path
            elif self.config and self.config.credentials_path:
                creds_path = self.config.credentials_path
            else:
                creds_path = self._get_default_credentials_path()

            if self.auth_method == 'service_account':
                success = self._authenticate_service_account(creds_path)
            elif self.auth_method == 'oauth2':
                success = self._authenticate_oauth2(creds_path)
            else:
                logger.error(f"Unsupported authentication method: {self.auth_method}")
                return False

            if success:
                self._authenticated = True
                logger.info("Authentication successful")
            else:
                logger.error("Authentication failed")

            return success

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    def _authenticate_service_account(self, credentials_path: str) -> bool:
        """Authenticate using service account."""
        try:
            if not os.path.exists(credentials_path):
                logger.error(f"Service account file not found: {credentials_path}")
                return False

            scopes = self.config.scopes if self.config else [
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/presentations'
            ]

            self.credentials = ServiceAccountCredentials.from_service_account_file(
                credentials_path, scopes=scopes
            )

            logger.info("Service account authentication successful")
            return True

        except Exception as e:
            logger.error(f"Service account authentication failed: {e}")
            return False

    def _authenticate_oauth2(self, credentials_path: str) -> bool:
        """Authenticate using OAuth2 flow."""
        try:
            scopes = self.config.scopes if self.config else [
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/presentations'
            ]

            # Try to load existing token
            token_path = self._get_token_cache_path()
            if os.path.exists(token_path):
                self.credentials = Credentials.from_authorized_user_file(token_path, scopes)

            # If no valid credentials, initiate OAuth flow
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    if not os.path.exists(credentials_path):
                        logger.error(f"OAuth2 credentials file not found: {credentials_path}")
                        return False

                    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)
                    self.credentials = flow.run_local_server(port=0)

                # Save credentials for next run
                with open(token_path, 'w') as token:
                    token.write(self.credentials.to_json())

            logger.info("OAuth2 authentication successful")
            return True

        except Exception as e:
            logger.error(f"OAuth2 authentication failed: {e}")
            return False

    def get_slides_service(self):
        """Get authenticated Slides API service."""
        if not self._authenticated or not self.credentials:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        if self.slides_service is None:
            try:
                self.slides_service = build('slides', 'v1', credentials=self.credentials)
                logger.info("Slides service created successfully")
            except Exception as e:
                logger.error(f"Failed to create Slides service: {e}")
                raise

        return self.slides_service

    def get_drive_service(self):
        """Get authenticated Drive API service."""
        if not self._authenticated or not self.credentials:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        if self.drive_service is None:
            try:
                self.drive_service = build('drive', 'v3', credentials=self.credentials)
                logger.info("Drive service created successfully")
            except Exception as e:
                logger.error(f"Failed to create Drive service: {e}")
                raise

        return self.drive_service

    def test_authentication(self) -> Dict[str, Any]:
        """
        Test authentication by making simple API calls.

        Returns:
            Dictionary with test results
        """
        if not self._authenticated:
            return {
                'authenticated': False,
                'error': 'Not authenticated'
            }

        results = {
            'authenticated': True,
            'drive_access': False,
            'slides_access': False,
            'errors': []
        }

        # Test Drive API access
        try:
            drive_service = self.get_drive_service()
            about = drive_service.about().get(fields="user").execute()
            results['drive_access'] = True
            results['user_email'] = about.get('user', {}).get('emailAddress', 'Unknown')
            logger.info("Drive API access confirmed")
        except Exception as e:
            results['errors'].append(f"Drive API error: {e}")
            logger.error(f"Drive API test failed: {e}")

        # Test Slides API access
        try:
            slides_service = self.get_slides_service()
            # Create a minimal test presentation to verify write access
            test_presentation = {
                'title': 'SVG2PPTX Authentication Test - ' + datetime.now().strftime('%Y%m%d_%H%M%S')
            }
            presentation = slides_service.presentations().create(body=test_presentation).execute()

            # Clean up test presentation
            drive_service = self.get_drive_service()
            drive_service.files().delete(fileId=presentation['presentationId']).execute()

            results['slides_access'] = True
            logger.info("Slides API access confirmed")
        except Exception as e:
            results['errors'].append(f"Slides API error: {e}")
            logger.error(f"Slides API test failed: {e}")

        return results

    def get_user_info(self) -> Dict[str, Any]:
        """Get authenticated user information."""
        if not self._authenticated:
            return {'error': 'Not authenticated'}

        try:
            drive_service = self.get_drive_service()
            about = drive_service.about().get(fields="user,storageQuota").execute()

            user_info = {
                'email': about.get('user', {}).get('emailAddress', 'Unknown'),
                'display_name': about.get('user', {}).get('displayName', 'Unknown'),
                'photo_link': about.get('user', {}).get('photoLink'),
                'storage_quota': about.get('storageQuota', {})
            }

            return user_info

        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return {'error': str(e)}

    def _get_default_credentials_path(self) -> str:
        """Get default credentials file path."""
        home_dir = Path.home()
        config_dir = home_dir / '.config' / 'svg2pptx'
        config_dir.mkdir(parents=True, exist_ok=True)

        if self.auth_method == 'service_account':
            return str(config_dir / 'google_service_account.json')
        else:
            return str(config_dir / 'google_oauth_credentials.json')

    def _get_token_cache_path(self) -> str:
        """Get OAuth2 token cache file path."""
        if self.config and self.config.token_cache_path:
            return self.config.token_cache_path

        home_dir = Path.home()
        config_dir = home_dir / '.config' / 'svg2pptx'
        config_dir.mkdir(parents=True, exist_ok=True)
        return str(config_dir / 'google_oauth_token.json')

    def revoke_credentials(self) -> bool:
        """Revoke stored credentials."""
        try:
            # Remove token cache for OAuth2
            if self.auth_method == 'oauth2':
                token_path = self._get_token_cache_path()
                if os.path.exists(token_path):
                    os.remove(token_path)
                    logger.info("OAuth2 token cache removed")

            # Reset internal state
            self.credentials = None
            self.slides_service = None
            self.drive_service = None
            self._authenticated = False

            logger.info("Credentials revoked successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke credentials: {e}")
            return False

    @property
    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        return self._authenticated and self.credentials is not None

    @property
    def auth_info(self) -> Dict[str, Any]:
        """Get authentication status information."""
        return {
            'method': self.auth_method,
            'authenticated': self.is_authenticated,
            'has_slides_service': self.slides_service is not None,
            'has_drive_service': self.drive_service is not None,
            'credentials_valid': self.credentials is not None and (
                not hasattr(self.credentials, 'valid') or self.credentials.valid
            )
        }