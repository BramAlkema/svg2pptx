#!/usr/bin/env python3
"""
Unit Tests for SVG URL Downloader

Tests the URL downloader helper for batch processing.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import requests

from core.batch.url_downloader import (
    download_svgs_to_temp,
    cleanup_temp_directory,
    get_downloader_info,
    DownloadError,
    DownloadResult,
    _is_svg_content_type,
    _is_valid_svg_content,
    _get_safe_filename
)


# Sample SVG content
VALID_SVG = b'''<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <rect x="10" y="10" width="80" height="80" fill="blue"/>
</svg>'''

VALID_SVG_NO_XML_DECL = b'''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <rect x="10" y="10" width="80" height="80" fill="red"/>
</svg>'''

INVALID_CONTENT = b'''<html>
<body>Not an SVG</body>
</html>'''


@pytest.fixture
def mock_response():
    """Create mock HTTP response"""
    response = Mock()
    response.status_code = 200
    response.headers = {'Content-Type': 'image/svg+xml'}
    response.iter_content = Mock(return_value=[VALID_SVG])
    response.raise_for_status = Mock()
    return response


class TestDownloaderInfo:
    """Test downloader information"""

    def test_get_downloader_info(self):
        """Test downloader info returns correct structure"""
        info = get_downloader_info()

        assert info['downloader'] == 'svg_url_downloader'
        assert 'capabilities' in info
        assert 'defaults' in info
        assert 'supported_content_types' in info

    def test_downloader_capabilities(self):
        """Test downloader capabilities are correct"""
        info = get_downloader_info()
        caps = info['capabilities']

        assert caps['http_download'] is True
        assert caps['https_download'] is True
        assert caps['content_validation'] is True
        assert caps['size_limiting'] is True
        assert caps['batch_download'] is True


class TestContentValidation:
    """Test SVG content validation"""

    def test_is_svg_content_type_image_svg_xml(self):
        """Test image/svg+xml content type"""
        assert _is_svg_content_type('image/svg+xml')
        assert _is_svg_content_type('image/svg+xml; charset=utf-8')

    def test_is_svg_content_type_text_xml(self):
        """Test text/xml content type"""
        assert _is_svg_content_type('text/xml')
        assert _is_svg_content_type('application/xml')

    def test_is_svg_content_type_text_plain(self):
        """Test text/plain content type (some servers send this)"""
        assert _is_svg_content_type('text/plain')

    def test_is_svg_content_type_invalid(self):
        """Test non-SVG content types"""
        assert not _is_svg_content_type('text/html')
        assert not _is_svg_content_type('application/json')
        assert not _is_svg_content_type('image/png')

    def test_is_valid_svg_content_with_xml_declaration(self):
        """Test valid SVG with XML declaration"""
        assert _is_valid_svg_content(VALID_SVG)

    def test_is_valid_svg_content_without_xml_declaration(self):
        """Test valid SVG without XML declaration"""
        assert _is_valid_svg_content(VALID_SVG_NO_XML_DECL)

    def test_is_valid_svg_content_with_doctype(self):
        """Test valid SVG with DOCTYPE"""
        svg = b'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"><svg></svg>'
        assert _is_valid_svg_content(svg)

    def test_is_valid_svg_content_invalid(self):
        """Test invalid content"""
        assert not _is_valid_svg_content(INVALID_CONTENT)

    def test_is_valid_svg_content_empty(self):
        """Test empty content"""
        assert not _is_valid_svg_content(b'')


class TestFilenameGeneration:
    """Test safe filename generation"""

    def test_get_safe_filename_from_url(self):
        """Test filename extraction from URL"""
        filename = _get_safe_filename('https://example.com/logo.svg', 0)
        assert 'logo' in filename
        assert filename.endswith('_0.svg')

    def test_get_safe_filename_sanitization(self):
        """Test filename sanitization"""
        filename = _get_safe_filename('https://example.com/my logo!@#.svg', 1)
        assert filename.endswith('_1.svg')
        # Should sanitize special characters
        assert '!' not in filename
        assert '@' not in filename

    def test_get_safe_filename_no_extension(self):
        """Test filename from URL without .svg extension"""
        filename = _get_safe_filename('https://example.com/icon', 2)
        assert filename.endswith('_2.svg')

    def test_get_safe_filename_fallback(self):
        """Test fallback filename for invalid URLs"""
        filename = _get_safe_filename('', 3)
        # Filename includes index in both stem and suffix position
        assert filename == 'file_3_3.svg'


class TestSuccessfulDownload:
    """Test successful download scenarios"""

    @patch('core.batch.url_downloader.requests.get')
    def test_download_single_svg(self, mock_get, mock_response):
        """Test downloading single SVG file"""
        # Setup mock (use real temp directory)
        mock_get.return_value = mock_response

        # Execute
        result = download_svgs_to_temp(['https://example.com/test.svg'])

        try:
            # Verify
            assert result.success is True
            assert len(result.file_paths) == 1
            assert len(result.errors) == 0
            assert result.temp_dir is not None

            # Verify file was created
            file_path = Path(result.file_paths[0])
            assert file_path.exists()
            assert file_path.suffix == '.svg'

        finally:
            cleanup_temp_directory(result.temp_dir)

    @patch('core.batch.url_downloader.requests.get')
    def test_download_multiple_svgs(self, mock_get):
        """Test downloading multiple SVG files"""
        # Create different responses for each URL
        def create_response(content):
            resp = Mock()
            resp.status_code = 200
            resp.headers = {'Content-Type': 'image/svg+xml'}
            resp.iter_content = Mock(return_value=[content])
            resp.raise_for_status = Mock()
            return resp

        mock_get.side_effect = [
            create_response(VALID_SVG),
            create_response(VALID_SVG_NO_XML_DECL)
        ]

        # Execute
        urls = [
            'https://example.com/file1.svg',
            'https://example.com/file2.svg'
        ]
        result = download_svgs_to_temp(urls)

        try:
            # Verify
            assert result.success is True
            assert len(result.file_paths) == 2
            assert len(result.errors) == 0

            # Verify files were created
            for path in result.file_paths:
                assert Path(path).exists()

        finally:
            cleanup_temp_directory(result.temp_dir)

    @patch('core.batch.url_downloader.requests.get')
    @patch('core.batch.url_downloader.tempfile.mkdtemp')
    def test_download_with_job_id(self, mock_mkdtemp, mock_get, mock_response):
        """Test download with job_id in temp directory name"""
        temp_dir = tempfile.mkdtemp()
        mock_mkdtemp.return_value = temp_dir
        mock_get.return_value = mock_response

        try:
            result = download_svgs_to_temp(
                ['https://example.com/test.svg'],
                job_id='batch_123'
            )

            # Verify temp dir was created
            assert mock_mkdtemp.called
            # Check prefix includes job_id
            call_kwargs = mock_mkdtemp.call_args[1]
            assert 'batch_123' in call_kwargs['prefix']

        finally:
            cleanup_temp_directory(temp_dir)


class TestErrorHandling:
    """Test error handling scenarios"""

    @patch('core.batch.url_downloader.requests.get')
    @patch('core.batch.url_downloader.tempfile.mkdtemp')
    def test_http_404_error(self, mock_mkdtemp, mock_get):
        """Test handling of HTTP 404 error"""
        temp_dir = tempfile.mkdtemp()
        mock_mkdtemp.return_value = temp_dir

        # Mock 404 error
        mock_get.side_effect = requests.HTTPError("404 Not Found")

        # Execute
        result = download_svgs_to_temp(['https://example.com/notfound.svg'])

        # Verify
        assert result.success is False
        assert len(result.file_paths) == 0
        assert len(result.errors) == 1
        assert result.errors[0]['error_type'] == 'http_error'

        # Temp dir should be cleaned up on complete failure
        # (cleanup happens in the function)

    @patch('core.batch.url_downloader.requests.get')
    @patch('core.batch.url_downloader.tempfile.mkdtemp')
    def test_timeout_error(self, mock_mkdtemp, mock_get):
        """Test handling of timeout error"""
        temp_dir = tempfile.mkdtemp()
        mock_mkdtemp.return_value = temp_dir

        # Mock timeout
        mock_get.side_effect = requests.Timeout("Connection timed out")

        # Execute
        result = download_svgs_to_temp(['https://example.com/slow.svg'])

        # Verify
        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0]['error_type'] == 'http_error'

    @patch('core.batch.url_downloader.requests.get')
    @patch('core.batch.url_downloader.tempfile.mkdtemp')
    def test_invalid_svg_content(self, mock_mkdtemp, mock_get):
        """Test handling of invalid SVG content"""
        temp_dir = tempfile.mkdtemp()
        mock_mkdtemp.return_value = temp_dir

        # Mock response with invalid content
        response = Mock()
        response.status_code = 200
        response.headers = {'Content-Type': 'text/html'}
        response.iter_content = Mock(return_value=[INVALID_CONTENT])
        response.raise_for_status = Mock()
        mock_get.return_value = response

        # Execute
        result = download_svgs_to_temp(['https://example.com/invalid.svg'])

        # Verify
        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0]['error_type'] == 'download_error'

    @patch('core.batch.url_downloader.requests.get')
    @patch('core.batch.url_downloader.tempfile.mkdtemp')
    def test_file_size_limit_exceeded(self, mock_mkdtemp, mock_get):
        """Test handling of file size limit"""
        temp_dir = tempfile.mkdtemp()
        mock_mkdtemp.return_value = temp_dir

        # Mock response with large content
        large_content = b'x' * (11 * 1024 * 1024)  # 11MB
        response = Mock()
        response.status_code = 200
        response.headers = {'Content-Type': 'image/svg+xml'}
        response.iter_content = Mock(return_value=[large_content])
        response.raise_for_status = Mock()
        mock_get.return_value = response

        # Execute with 10MB limit
        result = download_svgs_to_temp(
            ['https://example.com/huge.svg'],
            max_size_mb=10
        )

        # Verify
        assert result.success is False
        assert len(result.errors) == 1
        assert 'limit' in result.errors[0]['error_message'].lower()


class TestPartialSuccess:
    """Test scenarios where some downloads succeed and some fail"""

    @patch('core.batch.url_downloader.requests.get')
    def test_partial_download_success(self, mock_get):
        """Test some downloads succeed, some fail"""
        # First URL succeeds, second fails
        success_response = Mock()
        success_response.status_code = 200
        success_response.headers = {'Content-Type': 'image/svg+xml'}
        success_response.iter_content = Mock(return_value=[VALID_SVG])
        success_response.raise_for_status = Mock()

        mock_get.side_effect = [
            success_response,
            requests.HTTPError("404 Not Found")
        ]

        # Execute
        urls = [
            'https://example.com/good.svg',
            'https://example.com/bad.svg'
        ]
        result = download_svgs_to_temp(urls)

        try:
            # Verify - partial success
            assert result.success is True  # At least one succeeded
            assert len(result.file_paths) == 1
            assert len(result.errors) == 1

        finally:
            cleanup_temp_directory(result.temp_dir)


class TestCleanup:
    """Test temp directory cleanup"""

    def test_cleanup_existing_directory(self):
        """Test cleanup of existing temp directory"""
        # Create temp directory with file
        temp_dir = tempfile.mkdtemp()
        test_file = Path(temp_dir) / 'test.txt'
        test_file.write_text('test')

        # Cleanup
        cleanup_temp_directory(temp_dir)

        # Verify
        assert not Path(temp_dir).exists()

    def test_cleanup_nonexistent_directory(self):
        """Test cleanup of non-existent directory (should not error)"""
        cleanup_temp_directory('/nonexistent/path/12345')
        # Should not raise exception

    def test_cleanup_none(self):
        """Test cleanup with None (should not error)"""
        cleanup_temp_directory(None)
        # Should not raise exception


class TestDownloadOptions:
    """Test download configuration options"""

    @patch('core.batch.url_downloader.requests.get')
    @patch('core.batch.url_downloader.tempfile.mkdtemp')
    def test_custom_timeout(self, mock_mkdtemp, mock_get, mock_response):
        """Test custom timeout option"""
        temp_dir = tempfile.mkdtemp()
        mock_mkdtemp.return_value = temp_dir
        mock_get.return_value = mock_response

        try:
            # Execute with custom timeout
            result = download_svgs_to_temp(
                ['https://example.com/test.svg'],
                timeout=60
            )

            # Verify timeout was passed to requests
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs['timeout'] == 60

        finally:
            cleanup_temp_directory(temp_dir)

    @patch('core.batch.url_downloader.requests.get')
    @patch('core.batch.url_downloader.tempfile.mkdtemp')
    def test_user_agent_header(self, mock_mkdtemp, mock_get, mock_response):
        """Test User-Agent header is set"""
        temp_dir = tempfile.mkdtemp()
        mock_mkdtemp.return_value = temp_dir
        mock_get.return_value = mock_response

        try:
            result = download_svgs_to_temp(['https://example.com/test.svg'])

            # Verify User-Agent header
            call_kwargs = mock_get.call_args[1]
            assert 'headers' in call_kwargs
            assert 'User-Agent' in call_kwargs['headers']
            assert 'svg2pptx' in call_kwargs['headers']['User-Agent']

        finally:
            cleanup_temp_directory(temp_dir)
