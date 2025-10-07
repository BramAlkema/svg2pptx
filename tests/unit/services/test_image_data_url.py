#!/usr/bin/env python3
"""
Tests for ImageService data URL processing.

Ensures the public process_data_url() API works correctly and maintains
backward compatibility.
"""

import base64
import pytest
from core.services.image_service import ImageService


@pytest.fixture
def image_service():
    """Create ImageService instance for tests"""
    return ImageService(enable_caching=False)


@pytest.fixture
def valid_png_data_url():
    """Create a valid 1x1 PNG data URL"""
    # 1x1 red pixel PNG
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    )
    b64_data = base64.b64encode(png_bytes).decode('utf-8')
    return f"data:image/png;base64,{b64_data}"


@pytest.fixture
def valid_svg_data_url():
    """Create a valid SVG data URL"""
    svg_content = '<svg width="50" height="50"><rect width="50" height="50" fill="#333"/></svg>'
    b64_data = base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')
    return f"data:image/svg+xml;base64,{b64_data}"


class TestProcessDataURLPublicAPI:
    """Test the public process_data_url() method"""

    def test_process_data_url_accepts_valid_png(self, image_service, valid_png_data_url):
        """Test processing valid PNG data URL"""
        result = image_service.process_data_url(valid_png_data_url)

        assert result is not None
        assert result.width > 0
        assert result.height > 0
        assert result.format == 'PNG'
        assert len(result.content) > 0

    def test_process_data_url_accepts_valid_svg(self, image_service, valid_svg_data_url):
        """Test processing valid SVG data URL"""
        result = image_service.process_data_url(valid_svg_data_url)

        assert result is not None
        assert result.format == 'SVG'
        assert len(result.content) > 0

    def test_process_data_url_rejects_non_data_url(self, image_service):
        """Test that non-data URLs are rejected"""
        with pytest.raises(ValueError, match="process_data_url expects a data: URL"):
            image_service.process_data_url("https://example.com/image.png")

    def test_process_data_url_rejects_none(self, image_service):
        """Test that None is rejected"""
        with pytest.raises(ValueError, match="process_data_url expects a data: URL"):
            image_service.process_data_url(None)

    def test_process_data_url_rejects_non_string(self, image_service):
        """Test that non-string types are rejected"""
        with pytest.raises(ValueError, match="process_data_url expects a data: URL"):
            image_service.process_data_url(12345)

    def test_process_data_url_rejects_file_path(self, image_service):
        """Test that file paths are rejected"""
        with pytest.raises(ValueError, match="process_data_url expects a data: URL"):
            image_service.process_data_url("/path/to/image.png")


class TestProcessImageSourceUnifiedAPI:
    """Test that process_image_source() handles data URLs"""

    def test_process_image_source_handles_data_url(self, image_service, valid_png_data_url):
        """Test that process_image_source can handle data URLs"""
        result = image_service.process_image_source(valid_png_data_url)

        assert result is not None
        assert result.format == 'PNG'

    def test_process_image_source_same_result_as_process_data_url(
        self, image_service, valid_png_data_url
    ):
        """Test that both methods produce equivalent results"""
        result1 = image_service.process_data_url(valid_png_data_url)
        result2 = image_service.process_image_source(valid_png_data_url)

        assert result1.format == result2.format
        assert result1.width == result2.width
        assert result1.height == result2.height
        assert result1.content == result2.content


class TestBackwardCompatibility:
    """Test backward compatibility with existing code"""

    def test_old_code_using_process_data_url_still_works(self, image_service, valid_png_data_url):
        """Test that legacy code calling process_data_url() still works"""
        # Simulate old code that used to call image_service.process_data_url()
        image_info = image_service.process_data_url(valid_png_data_url)

        assert image_info is not None
        assert hasattr(image_info, 'width')
        assert hasattr(image_info, 'height')
        assert hasattr(image_info, 'format')
        assert hasattr(image_info, 'content')

    def test_new_code_using_process_image_source_works(self, image_service, valid_png_data_url):
        """Test that new code using process_image_source() works"""
        # Simulate new code using the unified API
        image_info = image_service.process_image_source(valid_png_data_url)

        assert image_info is not None
        assert hasattr(image_info, 'width')
        assert hasattr(image_info, 'height')
        assert hasattr(image_info, 'format')
        assert hasattr(image_info, 'content')


class TestImageAdapterIntegration:
    """Test integration with image_adapter usage patterns"""

    def test_image_adapter_pattern_data_url(self, image_service, valid_svg_data_url):
        """Test the pattern used in image_adapter._process_data_url()"""
        # This simulates how image_adapter now calls the service
        try:
            result = image_service.process_image_source(valid_svg_data_url, base_path=None)
            assert result is not None
        except Exception as e:
            pytest.fail(f"Image adapter pattern should work: {e}")

    def test_image_adapter_fallback_to_process_data_url(self, image_service, valid_svg_data_url):
        """Test that direct process_data_url() calls also work (backward compat)"""
        # Some adapters might still use the direct method
        try:
            result = image_service.process_data_url(valid_svg_data_url)
            assert result is not None
        except Exception as e:
            pytest.fail(f"Direct process_data_url() should work: {e}")


class TestDataURLEdgeCases:
    """Test edge cases in data URL processing"""

    def test_data_url_without_base64_encoding(self, image_service):
        """Test data URL without base64 encoding is handled"""
        # URL-encoded data URL (not base64)
        data_url = "data:image/svg+xml,%3Csvg%3E%3C/svg%3E"
        result = image_service.process_data_url(data_url)

        # Should return None for unsupported format (only base64 is supported)
        assert result is None

    def test_malformed_data_url(self, image_service):
        """Test malformed data URL is handled gracefully"""
        data_url = "data:image/png;base64,INVALID_BASE64!!!"
        result = image_service.process_data_url(data_url)

        # Should return None for invalid base64
        assert result is None

    def test_empty_data_url(self, image_service):
        """Test empty data URL"""
        with pytest.raises(ValueError):
            image_service.process_data_url("")

    def test_data_url_with_whitespace(self, image_service, valid_png_data_url):
        """Test data URL with leading/trailing whitespace"""
        # Add whitespace
        data_url_with_space = f"  {valid_png_data_url}  "

        with pytest.raises(ValueError):
            # Whitespace makes it not start with 'data:'
            image_service.process_data_url(data_url_with_space)
