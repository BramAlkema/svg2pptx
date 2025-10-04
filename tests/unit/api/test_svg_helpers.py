"""
Unit tests for SVG helper functions.

Tests extract_svg_content() with various input sources and error conditions.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import HTTPException
from pydantic import BaseModel
from api.utils.svg_helpers import extract_svg_content


class MockRequest(BaseModel):
    """Mock request model for testing."""
    svg_content: str = None
    svg_url: str = None


class TestExtractSvgContentFromFile:
    """Test extraction from file upload."""

    @pytest.mark.asyncio
    async def test_extract_from_file_upload(self):
        """Test successful extraction from uploaded file."""
        # Create mock file with SVG content
        svg_data = "<svg>test</svg>"
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=svg_data.encode('utf-8'))

        result = await extract_svg_content(None, mock_file)

        assert result == svg_data
        mock_file.read.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_upload_takes_precedence_over_request(self):
        """Test that file upload has priority over request content."""
        file_content = "<svg>from file</svg>"
        request_content = "<svg>from request</svg>"

        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=file_content.encode('utf-8'))

        request = MockRequest(svg_content=request_content)

        result = await extract_svg_content(request, mock_file)

        assert result == file_content
        assert result != request_content

    @pytest.mark.asyncio
    async def test_file_invalid_utf8_encoding(self):
        """Test error handling for non-UTF-8 encoded files."""
        # Create file with invalid UTF-8
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=b'\xff\xfe invalid utf-8')

        with pytest.raises(HTTPException) as exc_info:
            await extract_svg_content(None, mock_file)

        assert exc_info.value.status_code == 400
        assert "encoding" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_file_read_error(self):
        """Test error handling when file read fails."""
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(side_effect=Exception("Read error"))

        with pytest.raises(HTTPException) as exc_info:
            await extract_svg_content(None, mock_file)

        assert exc_info.value.status_code == 400
        assert "failed to read" in exc_info.value.detail.lower()


class TestExtractSvgContentFromRequest:
    """Test extraction from request body."""

    @pytest.mark.asyncio
    async def test_extract_from_request_svg_content(self):
        """Test successful extraction from request.svg_content."""
        svg_data = "<svg>test request</svg>"
        request = MockRequest(svg_content=svg_data)

        result = await extract_svg_content(request, None)

        assert result == svg_data

    @pytest.mark.asyncio
    async def test_extract_from_request_with_empty_svg_content(self):
        """Test that empty svg_content is treated as no input."""
        request = MockRequest(svg_content="")

        with pytest.raises(HTTPException) as exc_info:
            await extract_svg_content(request, None)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_svg_url_not_implemented(self):
        """Test that svg_url raises 501 Not Implemented."""
        request = MockRequest(svg_url="https://example.com/file.svg")

        with pytest.raises(HTTPException) as exc_info:
            await extract_svg_content(request, None)

        assert exc_info.value.status_code == 501
        assert "not yet implemented" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_svg_url_with_content_prefers_content(self):
        """Test that svg_content takes precedence over svg_url."""
        svg_data = "<svg>content</svg>"
        request = MockRequest(
            svg_content=svg_data,
            svg_url="https://example.com/file.svg"
        )

        result = await extract_svg_content(request, None)

        # Should use svg_content, not raise 501 for URL
        assert result == svg_data


class TestExtractSvgContentSizeValidation:
    """Test size validation."""

    @pytest.mark.asyncio
    async def test_content_within_size_limit(self):
        """Test that content within limit is accepted."""
        svg_data = "<svg>" + ("x" * 1000) + "</svg>"  # ~1KB
        request = MockRequest(svg_content=svg_data)

        result = await extract_svg_content(request, None, max_size_mb=1)

        assert result == svg_data

    @pytest.mark.asyncio
    async def test_content_exceeds_size_limit(self):
        """Test that oversized content raises 413."""
        # Create 11MB of content
        svg_data = "<svg>" + ("x" * (11 * 1024 * 1024)) + "</svg>"
        request = MockRequest(svg_content=svg_data)

        with pytest.raises(HTTPException) as exc_info:
            await extract_svg_content(request, None, max_size_mb=10)

        assert exc_info.value.status_code == 413
        assert "too large" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_custom_size_limit(self):
        """Test custom size limit."""
        # Create 6MB content
        svg_data = "<svg>" + ("x" * (6 * 1024 * 1024)) + "</svg>"
        request = MockRequest(svg_content=svg_data)

        # Should fail with 5MB limit
        with pytest.raises(HTTPException) as exc_info:
            await extract_svg_content(request, None, max_size_mb=5)

        assert exc_info.value.status_code == 413

        # Should succeed with 10MB limit
        result = await extract_svg_content(request, None, max_size_mb=10)
        assert result == svg_data

    @pytest.mark.asyncio
    async def test_size_error_message_includes_sizes(self):
        """Test that size error message includes actual and max sizes."""
        svg_data = "<svg>" + ("x" * (11 * 1024 * 1024)) + "</svg>"
        request = MockRequest(svg_content=svg_data)

        with pytest.raises(HTTPException) as exc_info:
            await extract_svg_content(request, None, max_size_mb=10)

        detail = exc_info.value.detail
        assert "10" in detail  # Max size
        assert "MB" in detail


class TestExtractSvgContentErrorCases:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_no_input_provided(self):
        """Test that no input raises 400."""
        with pytest.raises(HTTPException) as exc_info:
            await extract_svg_content(None, None)

        assert exc_info.value.status_code == 400
        assert "must provide" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_request_without_svg_fields(self):
        """Test request without svg_content or svg_url."""
        # Create empty request (no svg_content, no svg_url)
        request = MockRequest()

        with pytest.raises(HTTPException) as exc_info:
            await extract_svg_content(request, None)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_none_request_and_file(self):
        """Test explicit None for both parameters."""
        with pytest.raises(HTTPException) as exc_info:
            await extract_svg_content(None, None)

        assert exc_info.value.status_code == 400


class TestExtractSvgContentIntegration:
    """Integration tests with realistic scenarios."""

    @pytest.mark.asyncio
    async def test_realistic_svg_from_request(self):
        """Test with realistic SVG content."""
        svg_data = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <rect x="10" y="10" width="80" height="80" fill="blue" />
            <circle cx="50" cy="50" r="30" fill="red" />
        </svg>
        """
        request = MockRequest(svg_content=svg_data)

        result = await extract_svg_content(request, None)

        assert result == svg_data
        assert "<svg" in result
        assert "viewBox" in result

    @pytest.mark.asyncio
    async def test_realistic_svg_from_file(self):
        """Test with realistic SVG file upload."""
        svg_data = """<?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <path d="M10 10 L90 90" stroke="black" />
        </svg>
        """
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=svg_data.encode('utf-8'))

        result = await extract_svg_content(None, mock_file)

        assert result == svg_data
        assert "<?xml" in result

    @pytest.mark.asyncio
    async def test_minified_svg(self):
        """Test with minified SVG (no whitespace)."""
        svg_data = '<svg xmlns="http://www.w3.org/2000/svg"><rect x="0" y="0"/></svg>'
        request = MockRequest(svg_content=svg_data)

        result = await extract_svg_content(request, None)

        assert result == svg_data

    @pytest.mark.asyncio
    async def test_svg_with_special_characters(self):
        """Test SVG with special characters."""
        svg_data = '<svg><text>Test & "quotes" \'apostrophe\'</text></svg>'
        request = MockRequest(svg_content=svg_data)

        result = await extract_svg_content(request, None)

        assert result == svg_data
        assert "&" in result
        assert '"' in result
