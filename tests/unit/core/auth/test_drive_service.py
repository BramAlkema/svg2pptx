#!/usr/bin/env python3
"""
Unit tests for GoogleDriveService (core.auth.drive_service).

Tests PPTX to Slides conversion, file uploading, and error handling.
"""

from unittest.mock import Mock, patch, MagicMock, call
from io import BytesIO

import pytest
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from core.auth.drive_service import GoogleDriveService, DriveError


@pytest.fixture
def mock_credentials():
    """Mock Google OAuth2 credentials."""
    creds = Mock(spec=Credentials)
    creds.valid = True
    creds.expired = False
    return creds


@pytest.fixture
def mock_drive_service(mock_credentials):
    """Mock Google Drive service."""
    with patch('googleapiclient.discovery.build') as mock_build:
        mock_service = Mock()
        mock_build.return_value = mock_service

        drive_service = GoogleDriveService(mock_credentials)

        return drive_service, mock_service


class TestDriveServiceInitialization:
    """Test GoogleDriveService initialization."""

    @patch('googleapiclient.discovery.build')
    def test_initialization_with_valid_credentials(self, mock_build, mock_credentials):
        """Service initializes with valid credentials."""
        service = GoogleDriveService(mock_credentials)

        # Verify Drive API service built
        mock_build.assert_called_once_with('drive', 'v3', credentials=mock_credentials)

    def test_initialization_without_credentials_raises_error(self):
        """Initialization without credentials raises ValueError."""
        with pytest.raises(ValueError, match="credentials are required"):
            GoogleDriveService(None)

    @patch('googleapiclient.discovery.build')
    def test_initialization_with_invalid_credentials_raises_error(self, mock_build):
        """Initialization with invalid credentials raises error."""
        invalid_creds = Mock(spec=Credentials)
        invalid_creds.valid = False
        invalid_creds.expired = True

        with pytest.raises(DriveError, match="Invalid or expired credentials"):
            GoogleDriveService(invalid_creds)


class TestSlidesConversion:
    """Test PPTX to Google Slides conversion."""

    def test_upload_and_convert_to_slides_success(self, mock_drive_service):
        """upload_and_convert_to_slides successfully converts PPTX to Slides."""
        drive_service, mock_service = mock_drive_service

        # Mock Drive API response
        mock_files = mock_service.files.return_value
        mock_create = mock_files.create.return_value
        mock_create.execute.return_value = {
            'id': 'slides_presentation_id_123',
            'webViewLink': 'https://docs.google.com/presentation/d/slides_presentation_id_123/edit',
            'mimeType': 'application/vnd.google-apps.presentation'
        }

        # Call method
        pptx_bytes = b'fake_pptx_content'
        result = drive_service.upload_and_convert_to_slides(
            pptx_bytes=pptx_bytes,
            title="Test Presentation"
        )

        # Verify result
        assert result['slides_id'] == 'slides_presentation_id_123'
        assert result['slides_url'] == 'https://docs.google.com/presentation/d/slides_presentation_id_123/edit'
        assert result['web_view_link'] == 'https://docs.google.com/presentation/d/slides_presentation_id_123/edit'

        # Verify API call
        mock_create.execute.assert_called_once()

    def test_upload_with_mime_type_conversion(self, mock_drive_service):
        """upload_and_convert_to_slides uses correct mimeType for conversion."""
        drive_service, mock_service = mock_drive_service

        mock_files = mock_service.files.return_value
        mock_create = mock_files.create.return_value
        mock_create.execute.return_value = {
            'id': 'id',
            'webViewLink': 'https://link',
            'mimeType': 'application/vnd.google-apps.presentation'
        }

        # Call method
        pptx_bytes = b'pptx_data'
        drive_service.upload_and_convert_to_slides(pptx_bytes, "Title")

        # Verify body parameter
        call_args = mock_create.call_args
        body = call_args[1]['body']
        assert body['name'] == "Title"
        assert body['mimeType'] == 'application/vnd.google-apps.presentation'

        # Verify media upload
        media_body = call_args[1]['media_body']
        assert media_body._mimetype == 'application/vnd.openxmlformats-officedocument.presentationml.presentation'

    def test_upload_with_parent_folder(self, mock_drive_service):
        """upload_and_convert_to_slides supports parent folder."""
        drive_service, mock_service = mock_drive_service

        mock_files = mock_service.files.return_value
        mock_create = mock_files.create.return_value
        mock_create.execute.return_value = {
            'id': 'id',
            'webViewLink': 'https://link',
            'mimeType': 'application/vnd.google-apps.presentation'
        }

        # Call with parent folder
        pptx_bytes = b'data'
        drive_service.upload_and_convert_to_slides(
            pptx_bytes,
            "Title",
            parent_folder_id="folder_abc_123"
        )

        # Verify parent in body
        call_args = mock_create.call_args
        body = call_args[1]['body']
        assert 'parents' in body
        assert body['parents'] == ['folder_abc_123']

    def test_upload_with_resumable_upload(self, mock_drive_service):
        """upload_and_convert_to_slides uses resumable upload for large files."""
        drive_service, mock_service = mock_drive_service

        mock_files = mock_service.files.return_value
        mock_create = mock_files.create.return_value
        mock_create.execute.return_value = {
            'id': 'id',
            'webViewLink': 'https://link',
            'mimeType': 'application/vnd.google-apps.presentation'
        }

        # Large PPTX (> 5MB)
        large_pptx = b'x' * (6 * 1024 * 1024)
        drive_service.upload_and_convert_to_slides(large_pptx, "Title")

        # Verify resumable=True for large files
        call_args = mock_create.call_args
        media_body = call_args[1]['media_body']
        assert media_body._resumable is True


class TestErrorHandling:
    """Test error handling in Drive operations."""

    def test_upload_with_empty_pptx_raises_error(self, mock_drive_service):
        """Empty PPTX bytes raises ValueError."""
        drive_service, _ = mock_drive_service

        with pytest.raises(ValueError, match="pptx_bytes cannot be empty"):
            drive_service.upload_and_convert_to_slides(b'', "Title")

    def test_upload_with_empty_title_raises_error(self, mock_drive_service):
        """Empty title raises ValueError."""
        drive_service, _ = mock_drive_service

        with pytest.raises(ValueError, match="title cannot be empty"):
            drive_service.upload_and_convert_to_slides(b'data', "")

    def test_upload_api_error_raises_drive_service_error(self, mock_drive_service):
        """Drive API errors are wrapped in DriveServiceError."""
        drive_service, mock_service = mock_drive_service

        # Mock API error
        http_error = HttpError(
            resp=Mock(status=403),
            content=b'Permission denied'
        )
        mock_files = mock_service.files.return_value
        mock_create = mock_files.create.return_value
        mock_create.execute.side_effect = http_error

        with pytest.raises(DriveError, match="Failed to upload"):
            drive_service.upload_and_convert_to_slides(b'data', "Title")

    def test_upload_with_invalid_folder_id(self, mock_drive_service):
        """Invalid parent folder ID raises error."""
        drive_service, mock_service = mock_drive_service

        # Mock folder not found error
        http_error = HttpError(
            resp=Mock(status=404),
            content=b'Folder not found'
        )
        mock_files = mock_service.files.return_value
        mock_create = mock_files.create.return_value
        mock_create.execute.side_effect = http_error

        with pytest.raises(DriveError):
            drive_service.upload_and_convert_to_slides(
                b'data',
                "Title",
                parent_folder_id="invalid_folder"
            )


class TestMediaUpload:
    """Test media upload configuration."""

    @patch('googleapiclient.http.MediaIoBaseUpload')
    def test_media_upload_uses_correct_mime_type(self, mock_media_upload, mock_drive_service):
        """MediaIoBaseUpload uses correct PPTX MIME type."""
        drive_service, mock_service = mock_drive_service

        mock_files = mock_service.files.return_value
        mock_create = mock_files.create.return_value
        mock_create.execute.return_value = {
            'id': 'id',
            'webViewLink': 'link',
            'mimeType': 'application/vnd.google-apps.presentation'
        }

        pptx_bytes = b'pptx_data'
        drive_service.upload_and_convert_to_slides(pptx_bytes, "Title")

        # Verify MediaIoBaseUpload call
        mock_media_upload.assert_called_once()
        call_args = mock_media_upload.call_args

        # Check MIME type
        assert call_args[1]['mimetype'] == 'application/vnd.openxmlformats-officedocument.presentationml.presentation'

        # Check resumable flag
        assert 'resumable' in call_args[1]

    def test_media_upload_chunk_size_for_large_files(self, mock_drive_service):
        """Large files use appropriate chunk size."""
        drive_service, mock_service = mock_drive_service

        mock_files = mock_service.files.return_value
        mock_create = mock_files.create.return_value
        mock_create.execute.return_value = {
            'id': 'id',
            'webViewLink': 'link',
            'mimeType': 'application/vnd.google-apps.presentation'
        }

        # Large file (20 MB)
        large_pptx = b'x' * (20 * 1024 * 1024)
        drive_service.upload_and_convert_to_slides(large_pptx, "Title")

        # Verify resumable upload configured
        call_args = mock_create.call_args
        media_body = call_args[1]['media_body']
        assert media_body._resumable is True


class TestResponseParsing:
    """Test parsing of Drive API responses."""

    def test_parse_response_with_all_fields(self, mock_drive_service):
        """Response parser handles all fields correctly."""
        drive_service, mock_service = mock_drive_service

        mock_files = mock_service.files.return_value
        mock_create = mock_files.create.return_value
        mock_create.execute.return_value = {
            'id': 'presentation_123',
            'webViewLink': 'https://docs.google.com/presentation/d/presentation_123/edit',
            'mimeType': 'application/vnd.google-apps.presentation',
            'name': 'Test Presentation'
        }

        result = drive_service.upload_and_convert_to_slides(b'data', "Test Presentation")

        assert result['slides_id'] == 'presentation_123'
        assert 'presentation_123' in result['slides_url']
        assert result['web_view_link'] == 'https://docs.google.com/presentation/d/presentation_123/edit'

    def test_parse_response_missing_fields(self, mock_drive_service):
        """Response parser handles missing optional fields."""
        drive_service, mock_service = mock_drive_service

        mock_files = mock_service.files.return_value
        mock_create = mock_files.create.return_value
        # Missing webViewLink
        mock_create.execute.return_value = {
            'id': 'id_123',
            'mimeType': 'application/vnd.google-apps.presentation'
        }

        result = drive_service.upload_and_convert_to_slides(b'data', "Title")

        # Should construct URL from ID
        assert result['slides_id'] == 'id_123'
        assert 'id_123' in result['slides_url']


class TestIntegration:
    """Test integration scenarios."""

    def test_complete_conversion_workflow(self, mock_drive_service):
        """Complete workflow: bytes → upload → Slides URL."""
        drive_service, mock_service = mock_drive_service

        # Mock successful upload
        mock_files = mock_service.files.return_value
        mock_create = mock_files.create.return_value
        mock_create.execute.return_value = {
            'id': 'final_presentation_id',
            'webViewLink': 'https://docs.google.com/presentation/d/final_presentation_id/edit',
            'mimeType': 'application/vnd.google-apps.presentation'
        }

        # Simulate real PPTX bytes (header)
        pptx_bytes = b'PK\x03\x04' + b'x' * 1000  # ZIP header + data

        result = drive_service.upload_and_convert_to_slides(
            pptx_bytes=pptx_bytes,
            title="Integration Test Presentation",
            parent_folder_id="folder_xyz"
        )

        # Verify complete result
        assert 'slides_id' in result
        assert 'slides_url' in result
        assert 'web_view_link' in result
        assert result['slides_id'] == 'final_presentation_id'
        assert 'edit' in result['slides_url']

    @patch('googleapiclient.http.MediaIoBaseUpload')
    def test_batch_upload_multiple_presentations(self, mock_media_upload, mock_drive_service):
        """Service can handle multiple sequential uploads."""
        drive_service, mock_service = mock_drive_service

        mock_files = mock_service.files.return_value
        mock_create = mock_files.create.return_value

        # Mock responses for multiple uploads
        mock_create.execute.side_effect = [
            {'id': 'pres1', 'webViewLink': 'link1', 'mimeType': 'application/vnd.google-apps.presentation'},
            {'id': 'pres2', 'webViewLink': 'link2', 'mimeType': 'application/vnd.google-apps.presentation'},
            {'id': 'pres3', 'webViewLink': 'link3', 'mimeType': 'application/vnd.google-apps.presentation'},
        ]

        # Upload multiple presentations
        results = []
        for i in range(3):
            result = drive_service.upload_and_convert_to_slides(
                pptx_bytes=f'pptx_data_{i}'.encode(),
                title=f"Presentation {i+1}"
            )
            results.append(result)

        # Verify all succeeded
        assert len(results) == 3
        assert results[0]['slides_id'] == 'pres1'
        assert results[1]['slides_id'] == 'pres2'
        assert results[2]['slides_id'] == 'pres3'


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_large_pptx_file(self, mock_drive_service):
        """Service handles very large PPTX files."""
        drive_service, mock_service = mock_drive_service

        mock_files = mock_service.files.return_value
        mock_create = mock_files.create.return_value
        mock_create.execute.return_value = {
            'id': 'large_file_id',
            'webViewLink': 'link',
            'mimeType': 'application/vnd.google-apps.presentation'
        }

        # 100 MB file
        very_large_pptx = b'x' * (100 * 1024 * 1024)

        result = drive_service.upload_and_convert_to_slides(very_large_pptx, "Large Presentation")

        # Should succeed
        assert result['slides_id'] == 'large_file_id'

        # Verify resumable upload was used
        call_args = mock_create.call_args
        media_body = call_args[1]['media_body']
        assert media_body._resumable is True

    def test_unicode_characters_in_title(self, mock_drive_service):
        """Service handles Unicode characters in title."""
        drive_service, mock_service = mock_drive_service

        mock_files = mock_service.files.return_value
        mock_create = mock_files.create.return_value
        mock_create.execute.return_value = {
            'id': 'unicode_id',
            'webViewLink': 'link',
            'mimeType': 'application/vnd.google-apps.presentation'
        }

        # Unicode title
        unicode_title = "プレゼンテーション 📊 Présentation"

        result = drive_service.upload_and_convert_to_slides(b'data', unicode_title)

        # Verify title passed correctly
        call_args = mock_create.call_args
        body = call_args[1]['body']
        assert body['name'] == unicode_title

    def test_special_characters_in_title(self, mock_drive_service):
        """Service handles special characters in title."""
        drive_service, mock_service = mock_drive_service

        mock_files = mock_service.files.return_value
        mock_create = mock_files.create.return_value
        mock_create.execute.return_value = {
            'id': 'special_id',
            'webViewLink': 'link',
            'mimeType': 'application/vnd.google-apps.presentation'
        }

        # Special characters
        special_title = "Test / Presentation: <Important> [Final] {v2.0}"

        result = drive_service.upload_and_convert_to_slides(b'data', special_title)

        assert result['slides_id'] == 'special_id'
