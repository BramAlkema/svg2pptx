#!/usr/bin/env python3
"""
Unit Tests for ImageMapper

Tests the Image IR to DrawingML <p:pic> mapping functionality including:
- can_map() validation
- Image mapping to DrawingML
- MediaRequest creation
- SHA-256 deduplication tracking
- Data loading from various sources
- Policy integration
- XML generation without r:embed
- Legacy field support
"""

import pytest
import hashlib
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import Optional
from lxml import etree as ET

from core.map.image_mapper import ImageMapper
from core.map.base import OutputFormat, MediaRequest, MapperResult
from core.policy import ImageDecision
from core.ir import Image


# Mock Policy for testing
class MockPolicy:
    def __init__(self, embed_inline=True):
        self.embed_inline = embed_inline

    def decide_image(self, image, embedded_set):
        return ImageDecision(
            use_native=True,
            reasons=[],
            embed_inline=self.embed_inline,
            convert_format=False,
            target_format=None,
            compress=False,
            max_dimension=None
        )


class TestImageMapperCanMap:
    """Test can_map() validation"""

    def test_can_map_image(self):
        """Test that ImageMapper can map Image elements"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=b"fake_png_data"
        )

        assert mapper.can_map(image) == True

    def test_cannot_map_non_image(self):
        """Test that ImageMapper cannot map non-Image elements"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        @dataclass
        class FakeElement:
            pass

        fake = FakeElement()
        assert mapper.can_map(fake) == False


class TestImageMapperBasicMapping:
    """Test basic image mapping"""

    def test_map_creates_mapper_result(self):
        """Test that map() creates a MapperResult"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        image = Image(
            href="data:image/png;base64,fake",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=10, y=20, width=100, height=150,
            image_data=b"fake_png_data"
        )

        result = mapper.map(image)

        assert isinstance(result, MapperResult)
        assert result.element == image
        assert result.output_format == OutputFormat.NATIVE_DML
        assert result.xml_content is not None
        assert result.policy_decision is not None

    def test_map_raises_on_wrong_type(self):
        """Test that map() raises ValueError for non-Image"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        @dataclass
        class FakeElement:
            pass

        fake = FakeElement()

        with pytest.raises(ValueError, match="Expected Image"):
            mapper.map(fake)

    def test_map_generates_xml_content(self):
        """Test that map() generates <p:pic> XML"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=b"test_data"
        )

        result = mapper.map(image)

        assert "<p:pic" in result.xml_content
        assert "xmlns:p=" in result.xml_content
        assert "xmlns:a=" in result.xml_content


class TestMediaRequestCreation:
    """Test MediaRequest creation"""

    def test_creates_media_request(self):
        """Test that mapping creates a MediaRequest"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=b"test_png_data"
        )

        result = mapper.map(image)

        assert result.media_requests is not None
        assert len(result.media_requests) == 1

        media_req = result.media_requests[0]
        assert isinstance(media_req, MediaRequest)
        assert media_req.filename == "image1.png"
        assert media_req.mime_type == "image/png"
        assert media_req.bytes_data == b"test_png_data"
        assert media_req.content_type_ext == "png"

    def test_media_request_xpath_binding(self):
        """Test MediaRequest has correct XPath binding"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=b"data"
        )

        result = mapper.map(image)
        media_req = result.media_requests[0]

        assert media_req.bind_xpath == ".//a:blip"
        assert "embed" in media_req.bind_attr
        assert "officeDocument/2006/relationships" in media_req.bind_attr

    def test_filename_counter_increments(self):
        """Test that filename counter increments"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        image1 = Image(
            href="test1.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=b"data1"
        )

        image2 = Image(
            href="test2.jpg",
            source_type="data_url",
            mime_type="image/jpeg",
            format_ext="jpg",
            x=0, y=0, width=100, height=100,
            image_data=b"data2"
        )

        result1 = mapper.map(image1)
        result2 = mapper.map(image2)

        assert result1.media_requests[0].filename == "image1.png"
        assert result2.media_requests[0].filename == "image2.jpg"


class TestSHA256Deduplication:
    """Test SHA-256 deduplication tracking"""

    def test_calculates_sha256_if_not_present(self):
        """Test SHA-256 calculation when not provided"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        image_data = b"test_image_data"
        expected_sha = hashlib.sha256(image_data).hexdigest()

        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=image_data,
            sha256=None  # Not provided
        )

        result = mapper.map(image)
        media_req = result.media_requests[0]

        assert media_req.sha256 == expected_sha

    def test_uses_provided_sha256(self):
        """Test using provided SHA-256"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        provided_sha = "abc123def456"

        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=b"data",
            sha256=provided_sha
        )

        result = mapper.map(image)
        media_req = result.media_requests[0]

        assert media_req.sha256 == provided_sha

    def test_tracks_embedded_sha256(self):
        """Test that embedded SHA-256s are tracked"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        sha = "test_sha_256"

        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=b"data",
            sha256=sha
        )

        mapper.map(image)

        assert sha in mapper._embedded_sha256


class TestImageDataLoading:
    """Test image data loading from various sources"""

    def test_uses_existing_image_data(self):
        """Test using image_data field"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=b"existing_data"
        )

        result = mapper.map(image)
        assert result.media_requests[0].bytes_data == b"existing_data"

    def test_loads_from_file(self):
        """Test loading image from file"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        with patch("builtins.open", MagicMock()) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = b"file_data"
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file

            image = Image(
                href="path/to/image.png",
                source_type="file",
                mime_type="image/png",
                format_ext="png",
                x=0, y=0, width=100, height=100,
                image_data=None  # Not loaded yet
            )

            result = mapper.map(image)
            assert result.media_requests[0].bytes_data == b"file_data"

    def test_handles_file_not_found(self):
        """Test handling of missing file"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        with patch("builtins.open", side_effect=FileNotFoundError()):
            image = Image(
                href="missing.png",
                source_type="file",
                mime_type="image/png",
                format_ext="png",
                x=0, y=0, width=100, height=100,
                image_data=None
            )

            with pytest.raises(FileNotFoundError):
                mapper.map(image)


class TestPolicyIntegration:
    """Test policy integration"""

    def test_calls_policy_decide_image(self):
        """Test that policy.decide_image() is called"""
        policy = Mock()
        policy.decide_image.return_value = ImageDecision(
            use_native=True,
            reasons=[],
            embed_inline=True,
            convert_format=False,
            target_format=None,
            compress=False,
            max_dimension=None
        )

        mapper = ImageMapper(policy)

        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=b"data"
        )

        mapper.map(image)

        policy.decide_image.assert_called_once()
        call_args = policy.decide_image.call_args[0]
        assert call_args[0] == image
        assert call_args[1] == mapper._embedded_sha256

    def test_includes_policy_decision_in_result(self):
        """Test that policy decision is included in result"""
        decision = ImageDecision(
            use_native=True,
            reasons=[],
            embed_inline=True,
            convert_format=True,
            target_format="jpg",
            compress=False,
            max_dimension=1024
        )

        policy = Mock()
        policy.decide_image.return_value = decision

        mapper = ImageMapper(policy)

        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=b"data"
        )

        result = mapper.map(image)

        assert result.policy_decision == decision


class TestXMLGeneration:
    """Test XML generation details"""

    def test_xml_no_rembed_attribute(self):
        """Test that generated XML does NOT contain r:embed (filled by embedder)"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=b"data"
        )

        result = mapper.map(image)

        assert "r:embed" not in result.xml_content
        assert '<a:blip' in result.xml_content

    def test_xml_contains_coordinates(self):
        """Test that XML contains proper coordinates in EMUs"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=10,
            y=20,
            width=100,
            height=200,
            image_data=b"data"
        )

        result = mapper.map(image)

        # Parse XML to check attributes
        parsed = ET.fromstring(result.xml_content)
        off = parsed.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}off")
        ext = parsed.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}ext")

        # 10 * 9525 = 95250
        assert off.get("x") == "95250"
        # 20 * 9525 = 190500
        assert off.get("y") == "190500"
        # 100 * 9525 = 952500
        assert ext.get("cx") == "952500"
        # 200 * 9525 = 1905000
        assert ext.get("cy") == "1905000"

    def test_xml_well_formed(self):
        """Test that generated XML is well-formed"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=b"data"
        )

        result = mapper.map(image)

        # Should be parseable
        parsed = ET.fromstring(result.xml_content)
        assert parsed is not None
        assert parsed.tag.endswith("}pic")


class TestLegacyFieldSupport:
    """Test backward compatibility with legacy fields"""

    def test_supports_data_field(self):
        """Test support for legacy 'data' field"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        # Create image with 'data' instead of 'image_data'
        # Note: Image IR is frozen, so we test the fallback logic by providing data via the field
        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=b"legacy_data",  # Will be read via image_data first
            data=b"unused"  # Legacy field exists but not used when image_data is present
        )

        result = mapper.map(image)
        assert result.media_requests[0].bytes_data == b"legacy_data"

    def test_supports_format_field(self):
        """Test support for legacy 'format' field"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        # Test the fallback logic: format_ext -> format -> "png"
        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="jpg",  # Primary field
            format="gif",  # Legacy fallback (not used when format_ext present)
            x=0, y=0, width=100, height=100,
            image_data=b"data"
        )

        result = mapper.map(image)
        assert result.media_requests[0].filename == "image1.jpg"


class TestMIMETypeMapping:
    """Test MIME type mapping"""

    def test_get_mime_type_png(self):
        """Test PNG MIME type"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        mime = mapper._get_mime_type("png")
        assert mime == "image/png"

    def test_get_mime_type_jpg(self):
        """Test JPG/JPEG MIME type"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        assert mapper._get_mime_type("jpg") == "image/jpeg"
        assert mapper._get_mime_type("jpeg") == "image/jpeg"

    def test_get_mime_type_case_insensitive(self):
        """Test case-insensitive MIME lookup"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        assert mapper._get_mime_type("PNG") == "image/png"
        assert mapper._get_mime_type("JpG") == "image/jpeg"

    def test_get_mime_type_unknown_defaults_png(self):
        """Test unknown extension defaults to image/png"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        mime = mapper._get_mime_type("unknown")
        assert mime == "image/png"


class TestMetadata:
    """Test metadata generation"""

    def test_metadata_includes_format(self):
        """Test metadata includes format"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=b"data"
        )

        result = mapper.map(image)

        assert result.metadata['format'] == "png"

    def test_metadata_includes_size(self):
        """Test metadata includes size in bytes"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        image_data = b"1234567890"

        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=image_data
        )

        result = mapper.map(image)

        assert result.metadata['size_bytes'] == 10

    def test_metadata_includes_sha256(self):
        """Test metadata includes SHA-256 (first 8 chars)"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        sha = "abcdef1234567890"

        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=b"data",
            sha256=sha
        )

        result = mapper.map(image)

        assert result.metadata['sha256'] == "abcdef12"

    def test_metadata_includes_dimensions(self):
        """Test metadata includes dimensions"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=300, height=400,
            image_data=b"data"
        )

        result = mapper.map(image)

        assert result.metadata['dimensions'] == (300, 400)


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_handles_missing_optional_fields(self):
        """Test handling of missing optional fields"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        image = Image(
            href="test.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=b"data",
            title=None,  # Optional
            desc=None    # Optional
        )

        result = mapper.map(image)
        assert result is not None

    def test_handles_very_large_image_data(self):
        """Test handling of very large image data"""
        policy = MockPolicy()
        mapper = ImageMapper(policy)

        large_data = b"x" * 10_000_000  # 10MB

        image = Image(
            href="large.png",
            source_type="data_url",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=large_data
        )

        result = mapper.map(image)
        assert result.media_requests[0].bytes_data == large_data
        assert result.metadata['size_bytes'] == 10_000_000

    def test_external_reference_not_implemented(self):
        """Test that external references raise NotImplementedError"""
        policy = MockPolicy(embed_inline=False)
        mapper = ImageMapper(policy)

        image = Image(
            href="http://example.com/image.png",
            source_type="http",
            mime_type="image/png",
            format_ext="png",
            x=0, y=0, width=100, height=100,
            image_data=None
        )

        with pytest.raises(NotImplementedError, match="External image"):
            mapper.map(image)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
