#!/usr/bin/env python3
"""
Google OAuth authentication service for browser-based authentication.
"""

import os
import json
import webbrowser
from typing import Optional, Dict, Any
import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ..config import get_settings

logger = logging.getLogger(__name__)


class GoogleOAuthError(Exception):
    """Custom exception for OAuth operations."""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class GoogleOAuthService:
    """
    Google OAuth service for browser-based authentication.
    
    Handles OAuth flow, token storage, and refresh.
    """
    
    # Scopes for Google Drive and Slides access
    SCOPES = [
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive.metadata',
        'https://www.googleapis.com/auth/presentations.readonly'
    ]
    
    def __init__(self):
        """Initialize OAuth service."""
        self.settings = get_settings()
        self.token_file = self.settings.google_drive_token_file
        self.credentials = None
        self._ensure_credentials_dir()
    
    def _ensure_credentials_dir(self):
        """Ensure credentials directory exists."""
        token_dir = os.path.dirname(self.token_file)
        os.makedirs(token_dir, exist_ok=True)
    
    def get_credentials(self) -> Credentials:
        """
        Get valid Google credentials, handling OAuth flow if needed.
        
        Returns:
            Valid Google credentials
        """
        try:
            # Try to load existing token
            if os.path.exists(self.token_file):
                logger.info("Loading existing OAuth token")
                self.credentials = Credentials.from_authorized_user_file(
                    self.token_file, 
                    self.SCOPES
                )
            
            # Check if credentials are valid
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    logger.info("Refreshing expired OAuth token")
                    self.credentials.refresh(Request())
                else:
                    logger.info("Starting OAuth flow")
                    self.credentials = self._run_oauth_flow()
                
                # Save credentials for next run
                self._save_token()
            
            logger.info("OAuth credentials obtained successfully")
            return self.credentials
            
        except Exception as e:
            logger.error(f"Failed to get OAuth credentials: {e}")
            raise GoogleOAuthError(f"OAuth authentication failed: {e}")
    
    def _run_oauth_flow(self) -> Credentials:
        """Run OAuth flow with browser authentication."""
        try:
            # Check if client credentials are configured
            if not self.settings.google_drive_client_id or not self.settings.google_drive_client_secret:
                raise GoogleOAuthError(
                    "OAuth client ID and secret must be configured. "
                    "Set GOOGLE_DRIVE_CLIENT_ID and GOOGLE_DRIVE_CLIENT_SECRET in your .env file."
                )
            
            # Create OAuth client configuration
            client_config = {
                "web": {
                    "client_id": self.settings.google_drive_client_id,
                    "client_secret": self.settings.google_drive_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost:8080"]
                }
            }
            
            # Create flow
            flow = InstalledAppFlow.from_client_config(
                client_config, 
                self.SCOPES
            )
            
            # Run local server flow
            logger.info("Opening browser for OAuth authentication...")
            credentials = flow.run_local_server(
                port=8080,
                prompt='select_account',
                access_type='offline'
            )
            
            logger.info("OAuth flow completed successfully")
            return credentials
            
        except Exception as e:
            logger.error(f"OAuth flow failed: {e}")
            raise GoogleOAuthError(f"OAuth flow failed: {e}")
    
    def _save_token(self):
        """Save credentials to token file."""
        try:
            with open(self.token_file, 'w') as token:
                token.write(self.credentials.to_json())
            logger.info(f"OAuth token saved to {self.token_file}")
        except Exception as e:
            logger.warning(f"Could not save OAuth token: {e}")
    
    def revoke_token(self):
        """Revoke current OAuth token."""
        try:
            if self.credentials and hasattr(self.credentials, 'revoke'):
                self.credentials.revoke(Request())
            
            # Remove token file
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
            
            self.credentials = None
            logger.info("OAuth token revoked successfully")
            
        except Exception as e:
            logger.warning(f"Could not revoke OAuth token: {e}")
    
    def test_credentials(self) -> bool:
        """
        Test if current credentials work with Google Drive API.
        
        Returns:
            True if credentials are valid and working
        """
        try:
            credentials = self.get_credentials()
            
            # Test with a simple API call
            service = build('drive', 'v3', credentials=credentials)
            service.about().get(fields="user").execute()
            
            logger.info("OAuth credentials test successful")
            return True
            
        except Exception as e:
            logger.error(f"OAuth credentials test failed: {e}")
            return False
    
    def get_user_info(self) -> Dict[str, Any]:
        """
        Get information about the authenticated user.
        
        Returns:
            Dictionary with user information
        """
        try:
            credentials = self.get_credentials()
            service = build('drive', 'v3', credentials=credentials)
            
            about = service.about().get(fields="user").execute()
            user = about.get('user', {})
            
            return {
                'authenticated': True,
                'displayName': user.get('displayName'),
                'emailAddress': user.get('emailAddress'),
                'photoLink': user.get('photoLink')
            }
            
        except Exception as e:
            logger.error(f"Could not get user info: {e}")
            return {
                'authenticated': False,
                'error': str(e)
            }


def setup_oauth_credentials():
    """Interactive setup for OAuth credentials."""
    print("🔐 Google Drive OAuth Setup")
    print("=" * 40)
    
    print("\n1. Go to Google Cloud Console: https://console.cloud.google.com/")
    print("2. Create a new project or select existing one")
    print("3. Enable Google Drive API:")
    print("   - APIs & Services → Library")
    print("   - Search 'Google Drive API' → Enable")
    print("4. Create OAuth credentials:")
    print("   - APIs & Services → Credentials")
    print("   - Create Credentials → OAuth client ID")
    print("   - Application type: Desktop application")
    print("   - Name: 'SVG2PPTX Desktop Client'")
    print("   - Download JSON or copy Client ID and Secret")
    
    print("\n5. Enter your OAuth credentials:")
    
    client_id = input("Client ID: ").strip()
    if not client_id:
        print("❌ Client ID is required")
        return False
    
    client_secret = input("Client Secret: ").strip()
    if not client_secret:
        print("❌ Client Secret is required")
        return False
    
    # Update .env file
    env_file = ".env"
    env_lines = []
    
    # Read existing .env
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_lines = f.readlines()
    
    # Update or add OAuth settings
    updated_lines = []
    oauth_settings = {
        'GOOGLE_DRIVE_AUTH_METHOD': 'oauth',
        'GOOGLE_DRIVE_CLIENT_ID': client_id,
        'GOOGLE_DRIVE_CLIENT_SECRET': client_secret
    }
    
    # Track which settings we've updated
    updated_keys = set()
    
    for line in env_lines:
        line = line.strip()
        if '=' in line:
            key = line.split('=', 1)[0]
            if key in oauth_settings:
                updated_lines.append(f"{key}={oauth_settings[key]}\n")
                updated_keys.add(key)
            else:
                updated_lines.append(line + '\n')
        else:
            updated_lines.append(line + '\n')
    
    # Add new settings that weren't in the file
    for key, value in oauth_settings.items():
        if key not in updated_keys:
            updated_lines.append(f"{key}={value}\n")
    
    # Write updated .env
    with open(env_file, 'w') as f:
        f.writelines(updated_lines)
    
    print(f"\n✅ OAuth credentials saved to {env_file}")
    print("\n6. Test the setup:")
    print("   python -c \"from api.services.google_oauth import test_oauth_setup; test_oauth_setup()\"")
    
    return True


def test_oauth_setup():
    """Test OAuth setup with user authentication."""
    print("🧪 Testing Google OAuth Setup")
    print("=" * 35)
    
    try:
        oauth_service = GoogleOAuthService()
        
        # Test credentials
        if oauth_service.test_credentials():
            print("✅ OAuth authentication successful!")
            
            # Get user info
            user_info = oauth_service.get_user_info()
            if user_info.get('authenticated'):
                print(f"👤 Authenticated as: {user_info.get('displayName')} ({user_info.get('emailAddress')})")
            
            return True
        else:
            print("❌ OAuth authentication failed")
            return False
            
    except GoogleOAuthError as e:
        print(f"❌ OAuth error: {e.message}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup_oauth_credentials()
    else:
        test_oauth_setup()