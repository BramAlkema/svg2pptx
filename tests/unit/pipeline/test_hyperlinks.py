#!/usr/bin/env python3
"""
Unit tests for HyperlinkSpec and related hyperlink functionality.

Tests cover all aspects of hyperlink specification, validation,
and conversion for PowerPoint integration.
"""

import pytest
from dataclasses import FrozenInstanceError

from core.pipeline.hyperlinks import (
    HyperlinkSpec,
    HyperlinkType,
    create_hyperlink_spec,
    parse_svg_href
)


class TestHyperlinkSpec:
    """Test HyperlinkSpec dataclass functionality."""

    def test_basic_initialization(self):
        """Test basic HyperlinkSpec creation."""
        spec = HyperlinkSpec(href="https://example.com")
        assert spec.href == "https://example.com"
        assert spec.tooltip is None
        assert spec.visited is True

    def test_initialization_with_all_fields(self):
        """Test HyperlinkSpec creation with all fields."""
        spec = HyperlinkSpec(
            href="https://example.com",
            tooltip="Visit our website",
            visited=False
        )
        assert spec.href == "https://example.com"
        assert spec.tooltip == "Visit our website"
        assert spec.visited is False

    def test_empty_href_raises_error(self):
        """Test that empty href raises ValueError."""
        with pytest.raises(ValueError, match="href cannot be empty"):
            HyperlinkSpec(href="")

        with pytest.raises(ValueError, match="href cannot be empty"):
            HyperlinkSpec(href="   ")

    def test_href_normalization(self):
        """Test that href is normalized during initialization."""
        spec = HyperlinkSpec(href="  https://example.com  ")
        assert spec.href == "https://example.com"

    def test_tooltip_normalization(self):
        """Test that tooltip is normalized during initialization."""
        # Non-empty tooltip
        spec1 = HyperlinkSpec(href="https://example.com", tooltip="  Visit us  ")
        assert spec1.tooltip == "Visit us"

        # Empty tooltip becomes None
        spec2 = HyperlinkSpec(href="https://example.com", tooltip="   ")
        assert spec2.tooltip is None

        # None tooltip stays None
        spec3 = HyperlinkSpec(href="https://example.com", tooltip=None)
        assert spec3.tooltip is None


class TestHyperlinkTypeDetermination:
    """Test hyperlink type classification."""

    def test_external_http_links(self):
        """Test HTTP/HTTPS link detection."""
        spec1 = HyperlinkSpec(href="http://example.com")
        assert spec1.get_link_type() == HyperlinkType.EXTERNAL_HTTP
        assert spec1.is_external_link() is True
        assert spec1.is_internal_slide_link() is False

        spec2 = HyperlinkSpec(href="https://secure.example.com/path?param=value")
        assert spec2.get_link_type() == HyperlinkType.EXTERNAL_HTTP
        assert spec2.is_external_link() is True

        # Case insensitive
        spec3 = HyperlinkSpec(href="HTTPS://EXAMPLE.COM")
        assert spec3.get_link_type() == HyperlinkType.EXTERNAL_HTTP

    def test_external_mailto_links(self):
        """Test mailto link detection."""
        spec1 = HyperlinkSpec(href="mailto:contact@example.com")
        assert spec1.get_link_type() == HyperlinkType.EXTERNAL_MAILTO
        assert spec1.is_external_link() is True
        assert spec1.is_internal_slide_link() is False

        spec2 = HyperlinkSpec(href="mailto:user@domain.org?subject=Hello")
        assert spec2.get_link_type() == HyperlinkType.EXTERNAL_MAILTO

        # Case insensitive
        spec3 = HyperlinkSpec(href="MAILTO:TEST@EXAMPLE.COM")
        assert spec3.get_link_type() == HyperlinkType.EXTERNAL_MAILTO

    def test_external_tel_links(self):
        """Test telephone link detection."""
        spec1 = HyperlinkSpec(href="tel:+1-555-0123")
        assert spec1.get_link_type() == HyperlinkType.EXTERNAL_TEL
        assert spec1.is_external_link() is True
        assert spec1.is_internal_slide_link() is False

        spec2 = HyperlinkSpec(href="tel:5550123")
        assert spec2.get_link_type() == HyperlinkType.EXTERNAL_TEL

        # Case insensitive
        spec3 = HyperlinkSpec(href="TEL:+15550123")
        assert spec3.get_link_type() == HyperlinkType.EXTERNAL_TEL

    def test_external_file_links(self):
        """Test file link detection."""
        spec1 = HyperlinkSpec(href="file:///path/to/document.pdf")
        assert spec1.get_link_type() == HyperlinkType.EXTERNAL_FILE
        assert spec1.is_external_link() is True
        assert spec1.is_internal_slide_link() is False

        spec2 = HyperlinkSpec(href="file://server/share/file.doc")
        assert spec2.get_link_type() == HyperlinkType.EXTERNAL_FILE

        # Case insensitive
        spec3 = HyperlinkSpec(href="FILE:///C:/Documents/file.txt")
        assert spec3.get_link_type() == HyperlinkType.EXTERNAL_FILE

    def test_internal_slide_links(self):
        """Test internal slide link detection."""
        # slide:N format
        spec1 = HyperlinkSpec(href="slide:3")
        assert spec1.get_link_type() == HyperlinkType.INTERNAL_SLIDE
        assert spec1.is_external_link() is False
        assert spec1.is_internal_slide_link() is True

        # #slide-N format
        spec2 = HyperlinkSpec(href="#slide-5")
        assert spec2.get_link_type() == HyperlinkType.INTERNAL_SLIDE
        assert spec2.is_internal_slide_link() is True

        # Case insensitive
        spec3 = HyperlinkSpec(href="SLIDE:10")
        assert spec3.get_link_type() == HyperlinkType.INTERNAL_SLIDE

        spec4 = HyperlinkSpec(href="#SLIDE-2")
        assert spec4.get_link_type() == HyperlinkType.INTERNAL_SLIDE

    def test_unknown_link_types(self):
        """Test handling of unknown link types."""
        spec1 = HyperlinkSpec(href="ftp://example.com")
        assert spec1.get_link_type() == HyperlinkType.UNKNOWN
        assert spec1.is_external_link() is False
        assert spec1.is_internal_slide_link() is False

        spec2 = HyperlinkSpec(href="javascript:alert('hello')")
        assert spec2.get_link_type() == HyperlinkType.UNKNOWN

        spec3 = HyperlinkSpec(href="custom-protocol://data")
        assert spec3.get_link_type() == HyperlinkType.UNKNOWN


class TestSlideNumberExtraction:
    """Test slide number extraction from internal links."""

    def test_slide_colon_format(self):
        """Test slide:N format parsing."""
        spec1 = HyperlinkSpec(href="slide:1")
        assert spec1.get_slide_number() == 1

        spec2 = HyperlinkSpec(href="slide:42")
        assert spec2.get_slide_number() == 42

        spec3 = HyperlinkSpec(href="SLIDE:99")
        assert spec3.get_slide_number() == 99

    def test_slide_hash_format(self):
        """Test #slide-N format parsing."""
        spec1 = HyperlinkSpec(href="#slide-1")
        assert spec1.get_slide_number() == 1

        spec2 = HyperlinkSpec(href="#slide-15")
        assert spec2.get_slide_number() == 15

        spec3 = HyperlinkSpec(href="#SLIDE-8")
        assert spec3.get_slide_number() == 8

    def test_invalid_slide_numbers(self):
        """Test handling of invalid slide number formats."""
        spec1 = HyperlinkSpec(href="slide:abc")
        assert spec1.get_slide_number() is None

        spec2 = HyperlinkSpec(href="#slide-")
        assert spec2.get_slide_number() is None

        spec3 = HyperlinkSpec(href="slide:")
        assert spec3.get_slide_number() is None

    def test_non_slide_links_return_none(self):
        """Test that non-slide links return None for slide number."""
        spec1 = HyperlinkSpec(href="https://example.com")
        assert spec1.get_slide_number() is None

        spec2 = HyperlinkSpec(href="mailto:test@example.com")
        assert spec2.get_slide_number() is None


class TestPowerPointTargets:
    """Test PowerPoint target generation for relationships."""

    def test_external_link_targets(self):
        """Test target generation for external links."""
        spec1 = HyperlinkSpec(href="https://example.com")
        assert spec1.get_powerpoint_target() == "https://example.com"

        spec2 = HyperlinkSpec(href="mailto:test@example.com")
        assert spec2.get_powerpoint_target() == "mailto:test@example.com"

        spec3 = HyperlinkSpec(href="tel:+1-555-0123")
        assert spec3.get_powerpoint_target() == "tel:+1-555-0123"

    def test_internal_slide_targets(self):
        """Test target generation for internal slide links."""
        spec1 = HyperlinkSpec(href="slide:3")
        assert spec1.get_powerpoint_target() == "../slides/slide3.xml"

        spec2 = HyperlinkSpec(href="#slide-10")
        assert spec2.get_powerpoint_target() == "../slides/slide10.xml"

    def test_malformed_slide_targets(self):
        """Test fallback for malformed slide references."""
        spec1 = HyperlinkSpec(href="slide:abc")
        assert spec1.get_powerpoint_target() == "../slides/slide1.xml"

        spec2 = HyperlinkSpec(href="#slide-")
        assert spec2.get_powerpoint_target() == "../slides/slide1.xml"

    def test_relationship_types(self):
        """Test relationship type determination."""
        # External links use hyperlink relationship
        spec1 = HyperlinkSpec(href="https://example.com")
        assert spec1.get_relationship_type() == "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"

        # Internal slides use slide relationship
        spec2 = HyperlinkSpec(href="slide:3")
        assert spec2.get_relationship_type() == "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"

    def test_external_relationship_marking(self):
        """Test external relationship flag."""
        spec1 = HyperlinkSpec(href="https://example.com")
        assert spec1.is_external_for_relationship() is True

        spec2 = HyperlinkSpec(href="slide:3")
        assert spec2.is_external_for_relationship() is False


class TestValidation:
    """Test hyperlink validation functionality."""

    def test_valid_hyperlinks_pass_validation(self):
        """Test that valid hyperlinks pass validation."""
        valid_specs = [
            HyperlinkSpec(href="https://example.com"),
            HyperlinkSpec(href="mailto:test@example.com"),
            HyperlinkSpec(href="tel:+1-555-0123"),
            HyperlinkSpec(href="slide:1"),
            HyperlinkSpec(href="#slide-5"),
            HyperlinkSpec(href="file:///path/to/file.pdf"),
        ]

        for spec in valid_specs:
            assert spec.validate() is True

    def test_invalid_slide_references_fail_validation(self):
        """Test that invalid slide references fail validation."""
        with pytest.raises(ValueError, match="Invalid slide reference"):
            spec = HyperlinkSpec(href="slide:0")
            spec.validate()

        with pytest.raises(ValueError, match="Invalid slide reference"):
            spec = HyperlinkSpec(href="slide:-1")
            spec.validate()

        with pytest.raises(ValueError, match="Invalid slide reference"):
            spec = HyperlinkSpec(href="slide:abc")
            spec.validate()

    def test_empty_href_fails_validation(self):
        """Test that empty href fails validation."""
        with pytest.raises(ValueError, match="href cannot be empty"):
            spec = HyperlinkSpec(href="")
            spec.validate()


class TestStringRepresentation:
    """Test string representation methods."""

    def test_str_representation(self):
        """Test __str__ method."""
        spec1 = HyperlinkSpec(href="https://example.com")
        assert str(spec1) == "HyperlinkSpec(href='https://example.com', visited=True)"

        spec2 = HyperlinkSpec(href="https://example.com", tooltip="Visit us", visited=False)
        assert str(spec2) == "HyperlinkSpec(href='https://example.com', tooltip='Visit us', visited=False)"

    def test_repr_representation(self):
        """Test __repr__ method."""
        spec = HyperlinkSpec(href="slide:3", tooltip="Go to slide 3")
        repr_str = repr(spec)
        assert "HyperlinkSpec" in repr_str
        assert "href='slide:3'" in repr_str
        assert "tooltip='Go to slide 3'" in repr_str
        assert "type=internal_slide" in repr_str


class TestFactoryFunction:
    """Test create_hyperlink_spec factory function."""

    def test_successful_creation(self):
        """Test successful hyperlink creation."""
        spec = create_hyperlink_spec(
            href="https://example.com",
            tooltip="Visit us",
            visited=False
        )
        assert spec.href == "https://example.com"
        assert spec.tooltip == "Visit us"
        assert spec.visited is False

    def test_validation_during_creation(self):
        """Test that validation occurs during factory creation."""
        with pytest.raises(ValueError):
            create_hyperlink_spec(href="")

        with pytest.raises(ValueError):
            create_hyperlink_spec(href="slide:0")

    def test_default_parameters(self):
        """Test factory function default parameters."""
        spec = create_hyperlink_spec(href="https://example.com")
        assert spec.tooltip is None
        assert spec.visited is True


class TestSVGHrefParsing:
    """Test parse_svg_href utility function."""

    def test_valid_svg_href_parsing(self):
        """Test parsing valid SVG href attributes."""
        # Basic HTTP link
        spec1 = parse_svg_href("https://example.com")
        assert spec1 is not None
        assert spec1.href == "https://example.com"
        assert spec1.tooltip is None

        # With title text
        spec2 = parse_svg_href("mailto:test@example.com", title_text="Send email")
        assert spec2 is not None
        assert spec2.href == "mailto:test@example.com"
        assert spec2.tooltip == "Send email"

        # Internal slide link
        spec3 = parse_svg_href("slide:5", title_text="  Go to slide 5  ")
        assert spec3 is not None
        assert spec3.href == "slide:5"
        assert spec3.tooltip == "Go to slide 5"

    def test_empty_svg_href_returns_none(self):
        """Test that empty href returns None."""
        assert parse_svg_href("") is None
        assert parse_svg_href("   ") is None
        assert parse_svg_href(None) is None

    def test_invalid_svg_href_returns_none(self):
        """Test that invalid href returns None instead of raising."""
        # This should return None rather than raising ValueError
        result = parse_svg_href("slide:0")  # Invalid slide number
        assert result is None

    def test_title_text_normalization(self):
        """Test title text normalization in SVG parsing."""
        spec = parse_svg_href("https://example.com", title_text="  \n  Visit us  \n  ")
        assert spec is not None
        assert spec.tooltip == "Visit us"

        # Empty title becomes None
        spec2 = parse_svg_href("https://example.com", title_text="   ")
        assert spec2 is not None
        assert spec2.tooltip is None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_href(self):
        """Test handling of very long href values."""
        long_href = "https://example.com/" + "a" * 1000
        spec = HyperlinkSpec(href=long_href)
        assert spec.href == long_href
        assert spec.validate() is True

    def test_unicode_in_href(self):
        """Test handling of Unicode characters in href."""
        unicode_href = "https://example.com/文档"
        spec = HyperlinkSpec(href=unicode_href)
        assert spec.href == unicode_href

    def test_special_characters_in_tooltip(self):
        """Test handling of special characters in tooltip."""
        special_tooltip = "Visit us: <click here> & enjoy!"
        spec = HyperlinkSpec(href="https://example.com", tooltip=special_tooltip)
        assert spec.tooltip == special_tooltip

    def test_case_sensitivity_in_slide_numbers(self):
        """Test case sensitivity in slide number extraction."""
        # Both should work
        spec1 = HyperlinkSpec(href="slide:5")
        spec2 = HyperlinkSpec(href="SLIDE:5")
        spec3 = HyperlinkSpec(href="#slide-5")
        spec4 = HyperlinkSpec(href="#SLIDE-5")

        assert spec1.get_slide_number() == 5
        assert spec2.get_slide_number() == 5
        assert spec3.get_slide_number() == 5
        assert spec4.get_slide_number() == 5

    def test_large_slide_numbers(self):
        """Test handling of large slide numbers."""
        spec = HyperlinkSpec(href="slide:9999")
        assert spec.get_slide_number() == 9999
        assert spec.get_powerpoint_target() == "../slides/slide9999.xml"
        assert spec.validate() is True