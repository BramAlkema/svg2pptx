#!/usr/bin/env python3
"""
Google Slides integration for CLI visual reporting.

Provides drop-in functionality to:
- Run OAuth (stores token at ~/.svg2pptx/google_token.json)
- Upload + convert PPTX to Google Slides
- Set "anyone with link can view" permissions
- Return edit/present/preview/export URLs (closest to "pub")
"""

import os
import pathlib
import json
from typing import Dict, Optional

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_APIS_AVAILABLE = True
except ImportError:
    GOOGLE_APIS_AVAILABLE = False

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",   # create/manage files you create
    "https://www.googleapis.com/auth/presentations" # slides ops (future-proof)
]

def _cred_paths():
    """Get paths for credentials and token storage."""
    home = pathlib.Path.home()
    appdir = home / ".svg2pptx"
    appdir.mkdir(parents=True, exist_ok=True)
    return {
        "client_secret": pathlib.Path("credentials/google_client_secret.json"),
        "token": appdir / "google_token.json"
    }

def _load_credentials() -> Credentials:
    """Load and refresh Google OAuth credentials."""
    paths = _cred_paths()
    creds: Optional[Credentials] = None

    if paths["token"].exists():
        creds = Credentials.from_authorized_user_file(str(paths["token"]), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not paths["client_secret"].exists():
                raise FileNotFoundError(
                    f"Missing OAuth client secret at {paths['client_secret']}. "
                    f"Download JSON from Google Cloud Console (OAuth client ID for Desktop app)."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(paths["client_secret"]), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(paths["token"], "w") as f:
            f.write(creds.to_json())

    return creds

def upload_pptx_convert_to_slides(pptx_path: str, name: Optional[str] = None) -> str:
    """
    Upload a PPTX and convert it to Google Slides.

    Args:
        pptx_path: Path to PPTX file to upload
        name: Optional custom name for the Slides file

    Returns:
        Google Slides file ID
    """
    creds = _load_credentials()
    drive = build("drive", "v3", credentials=creds)

    file_name = name or pathlib.Path(pptx_path).stem
    media = MediaFileUpload(
        pptx_path,
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        resumable=True
    )

    # Set mimeType to Google Slides to force server-side conversion
    file_metadata = {
        "name": f"{file_name}",
        "mimeType": "application/vnd.google-apps.presentation"
    }

    result = drive.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    return result["id"]

def make_anyone_reader(file_id: str) -> None:
    """
    Set sharing to: Anyone with the link can view.

    Args:
        file_id: Google Drive file ID
    """
    creds = _load_credentials()
    drive = build("drive", "v3", credentials=creds)
    drive.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
        fields="id"
    ).execute()

def slides_urls(file_id: str) -> Dict[str, str]:
    """
    Generate all useful URLs for a Google Slides presentation.

    Args:
        file_id: Google Slides file ID

    Returns:
        Dictionary with edit, present, preview, and export URLs
    """
    base = f"https://docs.google.com/presentation/d/{file_id}"
    return {
        "edit":     f"{base}/edit",
        "present":  f"{base}/present",   # full-screen player; good "pub" stand-in
        "preview":  f"{base}/preview",   # minimal chrome embed/iframe-friendly
        "export_pdf":  f"{base}/export/pdf",
        "export_pptx": f"{base}/export/pptx"
    }

def integrate_google_slides(pptx_path: str, make_public: bool = True, custom_name: Optional[str] = None) -> Dict[str, str]:
    """
    End-to-end Google Slides integration:
    - Authenticate with OAuth
    - Upload & convert PPTX to Slides
    - Optionally set 'anyone with link can view'
    - Return all useful URLs

    Args:
        pptx_path: Path to PPTX file
        make_public: Whether to set public sharing permissions
        custom_name: Custom name for the Slides file

    Returns:
        Dictionary with all Google Slides URLs
    """
    if not GOOGLE_APIS_AVAILABLE:
        raise ImportError("Google APIs not available. Install with: pip install google-api-python-client google-auth-oauthlib")

    file_id = upload_pptx_convert_to_slides(pptx_path, name=custom_name)
    if make_public:
        make_anyone_reader(file_id)
    return slides_urls(file_id)

def check_google_auth_status() -> tuple[bool, str]:
    """
    Check Google authentication status without triggering auth flow.

    Returns:
        Tuple of (is_authenticated, status_message)
    """
    if not GOOGLE_APIS_AVAILABLE:
        return False, "Google APIs not installed"

    paths = _cred_paths()

    if not paths["client_secret"].exists():
        return False, f"OAuth credentials not found at {paths['client_secret']}"

    if not paths["token"].exists():
        return False, "Authentication required"

    try:
        creds = Credentials.from_authorized_user_file(str(paths["token"]), SCOPES)
        if creds and creds.valid:
            return True, "Authenticated and ready"
        elif creds and creds.expired and creds.refresh_token:
            return True, "Credentials need refresh (will happen automatically)"
        else:
            return False, "Authentication expired"
    except Exception as e:
        return False, f"Authentication error: {str(e)}"

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Upload PPTX to Google Slides with sharing")
    ap.add_argument("pptx", help="Path to the PPTX to upload/convert")
    ap.add_argument("--public", action="store_true", help="Set sharing to 'anyone with link: viewer'")
    ap.add_argument("--name", help="Custom name for the Slides file")
    args = ap.parse_args()

    try:
        urls = integrate_google_slides(args.pptx, make_public=args.public, custom_name=args.name)
        print(json.dumps(urls, indent=2))
    except Exception as e:
        print(f"Error: {e}")
        exit(1)