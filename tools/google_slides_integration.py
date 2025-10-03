#!/usr/bin/env python3
"""
Google Slides Integration for Visual Comparison

Automatically uploads PPTX to Google Drive, converts to Google Slides,
publishes it, and provides embeddable URLs for side-by-side comparison.
"""

import os
import time
import io
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

# Google API imports
try:
    from google.oauth2.credentials import Credentials
    from google.oauth2 import service_account
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    from googleapiclient.errors import HttpError
    import pickle
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    print("⚠️  Google API libraries not available. Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")


# Scopes required for Drive and Slides operations
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/presentations.readonly',
]


@dataclass
class SlidesInfo:
    """Information about uploaded Google Slides presentation."""
    file_id: str
    name: str
    web_view_link: str
    published_url: str
    embed_url: str
    thumbnail_link: Optional[str] = None
    slide_count: int = 0


class GoogleSlidesUploader:
    """Upload PPTX to Google Drive and convert to Google Slides."""

    def __init__(self, credentials_path: Optional[Path] = None):
        """
        Initialize Google Slides uploader.

        Args:
            credentials_path: Path to credentials.json or token.pickle
        """
        if not GOOGLE_AVAILABLE:
            raise ImportError("Google API libraries not installed")

        self.credentials_path = credentials_path or Path.home() / '.svg2pptx' / 'credentials.json'
        self.token_path = Path.home() / '.svg2pptx' / 'token.pickle'
        self.creds = None
        self.drive_service = None
        self.slides_service = None

    def authenticate(self) -> bool:
        """
        Authenticate with Google APIs.

        Returns:
            Success status
        """
        print("🔐 Authenticating with Google APIs...")

        # Check for saved token
        if self.token_path.exists():
            with open(self.token_path, 'rb') as token:
                self.creds = pickle.load(token)

        # If no valid credentials, get new ones
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                print("🔄 Refreshing expired credentials...")
                self.creds.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    print(f"❌ Credentials file not found: {self.credentials_path}")
                    print("\n📝 To enable Google Slides integration:")
                    print("1. Go to https://console.cloud.google.com/")
                    print("2. Create a project and enable Drive & Slides APIs")
                    print("3. Create OAuth 2.0 credentials (Desktop app)")
                    print(f"4. Download and save as: {self.credentials_path}")
                    return False

                print("🌐 Opening browser for authentication...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            # Save credentials for future use
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_path, 'wb') as token:
                pickle.dump(self.creds, token)

        # Build services
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        self.slides_service = build('slides', 'v1', credentials=self.creds)

        print("✅ Authentication successful")
        return True

    def upload_and_convert(self, pptx_path: Path, folder_id: Optional[str] = None) -> Optional[SlidesInfo]:
        """
        Upload PPTX to Google Drive and convert to Google Slides.

        Args:
            pptx_path: Path to PPTX file
            folder_id: Optional Google Drive folder ID

        Returns:
            SlidesInfo if successful, None otherwise
        """
        if not self.drive_service:
            if not self.authenticate():
                return None

        print(f"📤 Uploading {pptx_path.name} to Google Drive...")

        try:
            # File metadata
            file_metadata = {
                'name': pptx_path.stem,
                'mimeType': 'application/vnd.google-apps.presentation',  # Convert to Slides
            }

            if folder_id:
                file_metadata['parents'] = [folder_id]

            # Upload file
            media = MediaFileUpload(
                str(pptx_path),
                mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation',
                resumable=True
            )

            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink,thumbnailLink'
            ).execute()

            file_id = file.get('id')
            print(f"✅ Uploaded as Google Slides: {file_id}")

            # Make file publicly readable
            print("🌐 Publishing presentation...")
            self.drive_service.permissions().create(
                fileId=file_id,
                body={
                    'type': 'anyone',
                    'role': 'reader'
                }
            ).execute()

            # Get presentation details
            presentation = self.slides_service.presentations().get(
                presentationId=file_id
            ).execute()

            slide_count = len(presentation.get('slides', []))

            # Build URLs
            web_view_link = file.get('webViewLink')
            published_url = f"https://docs.google.com/presentation/d/{file_id}/pub"
            embed_url = f"https://docs.google.com/presentation/d/{file_id}/embed"

            slides_info = SlidesInfo(
                file_id=file_id,
                name=file.get('name'),
                web_view_link=web_view_link,
                published_url=published_url,
                embed_url=embed_url,
                thumbnail_link=file.get('thumbnailLink'),
                slide_count=slide_count
            )

            print(f"✅ Published presentation with {slide_count} slides")
            print(f"🔗 View: {web_view_link}")
            print(f"📊 Embed: {embed_url}")

            return slides_info

        except HttpError as error:
            print(f"❌ Upload failed: {error}")
            return None

    def get_slide_thumbnail(self, file_id: str, slide_index: int = 0,
                           output_path: Optional[Path] = None) -> Optional[Path]:
        """
        Download thumbnail for a specific slide.

        Args:
            file_id: Google Slides file ID
            slide_index: Slide index (0-based)
            output_path: Where to save thumbnail

        Returns:
            Path to saved thumbnail
        """
        if not self.slides_service:
            if not self.authenticate():
                return None

        try:
            # Get presentation
            presentation = self.slides_service.presentations().get(
                presentationId=file_id
            ).execute()

            slides = presentation.get('slides', [])
            if slide_index >= len(slides):
                print(f"❌ Slide index {slide_index} out of range (max: {len(slides)-1})")
                return None

            slide_id = slides[slide_index]['objectId']

            # Get thumbnail via Drive API
            # Note: Google Slides doesn't have direct thumbnail API per slide,
            # so we'll get the presentation thumbnail
            thumbnail_link = self.drive_service.files().get(
                fileId=file_id,
                fields='thumbnailLink'
            ).execute().get('thumbnailLink')

            if not thumbnail_link:
                print("⚠️  No thumbnail available")
                return None

            # Download thumbnail
            import requests
            # Increase thumbnail size in URL
            thumbnail_link = thumbnail_link.replace('=s220', '=s1600')

            response = requests.get(thumbnail_link)
            if response.status_code == 200:
                if not output_path:
                    output_path = Path(f"slide_{file_id}_{slide_index}.png")

                with open(output_path, 'wb') as f:
                    f.write(response.content)

                print(f"✅ Thumbnail saved: {output_path}")
                return output_path

        except HttpError as error:
            print(f"❌ Thumbnail download failed: {error}")

        return None

    def delete_presentation(self, file_id: str) -> bool:
        """
        Delete a presentation from Google Drive.

        Args:
            file_id: File ID to delete

        Returns:
            Success status
        """
        if not self.drive_service:
            if not self.authenticate():
                return False

        try:
            self.drive_service.files().delete(fileId=file_id).execute()
            print(f"✅ Deleted presentation: {file_id}")
            return True

        except HttpError as error:
            print(f"❌ Delete failed: {error}")
            return False

    def list_presentations(self, max_results: int = 10) -> list:
        """
        List recent Google Slides presentations.

        Args:
            max_results: Maximum number of results

        Returns:
            List of file metadata
        """
        if not self.drive_service:
            if not self.authenticate():
                return []

        try:
            results = self.drive_service.files().list(
                q="mimeType='application/vnd.google-apps.presentation'",
                pageSize=max_results,
                fields="files(id, name, createdTime, modifiedTime, webViewLink)"
            ).execute()

            return results.get('files', [])

        except HttpError as error:
            print(f"❌ List failed: {error}")
            return []


def main():
    """Test Google Slides integration."""
    import argparse

    parser = argparse.ArgumentParser(description='Upload PPTX to Google Slides')
    parser.add_argument('pptx_file', type=Path, nargs='?', help='PPTX file to upload')
    parser.add_argument('--list', action='store_true', help='List recent presentations')
    parser.add_argument('--delete', type=str, help='Delete presentation by ID')
    parser.add_argument('--credentials', type=Path, help='Path to credentials.json')

    args = parser.parse_args()

    uploader = GoogleSlidesUploader(credentials_path=args.credentials)

    if args.list:
        print("📋 Recent Google Slides presentations:")
        presentations = uploader.list_presentations()
        for i, pres in enumerate(presentations, 1):
            print(f"\n{i}. {pres['name']}")
            print(f"   ID: {pres['id']}")
            print(f"   Link: {pres['webViewLink']}")
        return

    if args.delete:
        uploader.delete_presentation(args.delete)
        return

    if not args.pptx_file:
        print("❌ Please provide a PPTX file to upload")
        parser.print_help()
        return

    if not args.pptx_file.exists():
        print(f"❌ File not found: {args.pptx_file}")
        return

    # Upload and convert
    slides_info = uploader.upload_and_convert(args.pptx_file)

    if slides_info:
        print("\n🎉 Success! Presentation uploaded and published")
        print(f"\n📊 Presentation Details:")
        print(f"Name: {slides_info.name}")
        print(f"Slides: {slides_info.slide_count}")
        print(f"File ID: {slides_info.file_id}")
        print(f"\n🔗 URLs:")
        print(f"View: {slides_info.web_view_link}")
        print(f"Published: {slides_info.published_url}")
        print(f"Embed: {slides_info.embed_url}")

        print(f"\n📝 HTML Embed Code:")
        print(f'<iframe src="{slides_info.embed_url}?start=false&loop=false&delayms=3000" '
              f'frameborder="0" width="960" height="569" allowfullscreen="true" '
              f'mozallowfullscreen="true" webkitallowfullscreen="true"></iframe>')


if __name__ == "__main__":
    main()
