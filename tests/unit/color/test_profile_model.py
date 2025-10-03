#!/usr/bin/env python3
"""
Unit tests for color profile data models.

Tests comprehensive validation, edge cases, and API functionality
for ColorProfileRef, ProfiledColor, and RenderingIntent.
"""

import pytest
from core.color.profile_model import (
    RenderingIntent,
    ColorProfileRef,
    ProfiledColor,
    normalize_profile_reference,
    validate_color_channels
)


class TestRenderingIntent:
    """Test RenderingIntent enum and string parsing."""

    def test_enum_values(self):
        """Test all enum values are correctly defined."""
        assert RenderingIntent.AUTO.value == "auto"
        assert RenderingIntent.PERCEPTUAL.value == "perceptual"
        assert RenderingIntent.RELATIVE_COLORIMETRIC.value == "relative-colorimetric"
        assert RenderingIntent.SATURATION.value == "saturation"
        assert RenderingIntent.ABSOLUTE_COLORIMETRIC.value == "absolute-colorimetric"

    def test_from_string_valid_values(self):
        """Test parsing valid intent strings."""
        assert RenderingIntent.from_string("auto") == RenderingIntent.AUTO
        assert RenderingIntent.from_string("perceptual") == RenderingIntent.PERCEPTUAL
        assert RenderingIntent.from_string("relative-colorimetric") == RenderingIntent.RELATIVE_COLORIMETRIC
        assert RenderingIntent.from_string("saturation") == RenderingIntent.SATURATION
        assert RenderingIntent.from_string("absolute-colorimetric") == RenderingIntent.ABSOLUTE_COLORIMETRIC

    def test_from_string_case_insensitive(self):
        """Test case-insensitive parsing."""
        assert RenderingIntent.from_string("AUTO") == RenderingIntent.AUTO
        assert RenderingIntent.from_string("Perceptual") == RenderingIntent.PERCEPTUAL
        assert RenderingIntent.from_string("RELATIVE-COLORIMETRIC") == RenderingIntent.RELATIVE_COLORIMETRIC

    def test_from_string_underscore_normalization(self):
        """Test underscore to hyphen normalization."""
        assert RenderingIntent.from_string("relative_colorimetric") == RenderingIntent.RELATIVE_COLORIMETRIC
        assert RenderingIntent.from_string("absolute_colorimetric") == RenderingIntent.ABSOLUTE_COLORIMETRIC

    def test_from_string_abbreviations(self):
        """Test common abbreviations."""
        assert RenderingIntent.from_string("relative") == RenderingIntent.RELATIVE_COLORIMETRIC
        assert RenderingIntent.from_string("absolute") == RenderingIntent.ABSOLUTE_COLORIMETRIC

    def test_from_string_invalid_defaults_to_auto(self):
        """Test invalid strings default to AUTO."""
        assert RenderingIntent.from_string("invalid") == RenderingIntent.AUTO
        assert RenderingIntent.from_string("") == RenderingIntent.AUTO
        assert RenderingIntent.from_string(None) == RenderingIntent.AUTO
        assert RenderingIntent.from_string("   ") == RenderingIntent.AUTO


class TestColorProfileRef:
    """Test ColorProfileRef dataclass validation and properties."""

    def test_basic_creation(self):
        """Test basic profile reference creation."""
        profile = ColorProfileRef(name="srgb")
        assert profile.name == "srgb"
        assert profile.href is None
        assert profile.local is True
        assert profile.rendering_intent == RenderingIntent.AUTO

    def test_full_creation(self):
        """Test profile reference with all parameters."""
        profile = ColorProfileRef(
            name="display-p3",
            href="data:application/icc-profile,base64data",
            local=False,
            rendering_intent=RenderingIntent.PERCEPTUAL
        )
        assert profile.name == "display-p3"
        assert profile.href == "data:application/icc-profile,base64data"
        assert profile.local is False
        assert profile.rendering_intent == RenderingIntent.PERCEPTUAL

    def test_name_validation_empty(self):
        """Test name validation rejects empty strings."""
        with pytest.raises(ValueError, match="Profile name must be non-empty string"):
            ColorProfileRef(name="")

        with pytest.raises(ValueError, match="Profile name cannot be whitespace-only"):
            ColorProfileRef(name="   ")

    def test_name_validation_type(self):
        """Test name validation requires string type."""
        with pytest.raises(ValueError, match="Profile name must be non-empty string"):
            ColorProfileRef(name=None)

        with pytest.raises(ValueError, match="Profile name must be non-empty string"):
            ColorProfileRef(name=123)

    def test_name_validation_characters(self):
        """Test name validation allows only safe characters."""
        # Valid names
        ColorProfileRef(name="srgb")
        ColorProfileRef(name="display-p3")
        ColorProfileRef(name="adobe_rgb")
        ColorProfileRef(name="profile123")

        # Invalid names
        with pytest.raises(ValueError, match="Profile name contains invalid characters"):
            ColorProfileRef(name="profile with spaces")

        with pytest.raises(ValueError, match="Profile name contains invalid characters"):
            ColorProfileRef(name="profile/slash")

        with pytest.raises(ValueError, match="Profile name contains invalid characters"):
            ColorProfileRef(name="profile@symbol")

    def test_href_validation(self):
        """Test href validation."""
        # Valid hrefs
        ColorProfileRef(name="test", href="data:application/icc-profile,data")
        ColorProfileRef(name="test", href="https://example.com/profile.icc")
        ColorProfileRef(name="test", href="/path/to/profile.icc")

        # Invalid hrefs
        with pytest.raises(ValueError, match="Profile href must be string or None"):
            ColorProfileRef(name="test", href=123)

        with pytest.raises(ValueError, match="Profile href cannot be empty string"):
            ColorProfileRef(name="test", href="")

    def test_is_data_url_property(self):
        """Test data URL detection."""
        data_profile = ColorProfileRef(name="test", href="data:application/icc-profile,data")
        assert data_profile.is_data_url is True

        file_profile = ColorProfileRef(name="test", href="/path/to/profile.icc")
        assert file_profile.is_data_url is False

        no_href_profile = ColorProfileRef(name="test")
        assert no_href_profile.is_data_url is False

    def test_is_remote_property(self):
        """Test remote URL detection."""
        http_profile = ColorProfileRef(name="test", href="http://example.com/profile.icc")
        assert http_profile.is_remote is True

        https_profile = ColorProfileRef(name="test", href="https://example.com/profile.icc")
        assert https_profile.is_remote is True

        local_profile = ColorProfileRef(name="test", href="/path/to/profile.icc")
        assert local_profile.is_remote is False

        data_profile = ColorProfileRef(name="test", href="data:application/icc-profile,data")
        assert data_profile.is_remote is False

    def test_safe_name_property(self):
        """Test safe name generation for file system use."""
        profile = ColorProfileRef(name="display-p3")
        assert profile.safe_name == "display-p3"

        profile = ColorProfileRef(name="adobe_rgb")
        assert profile.safe_name == "adobe_rgb"

        profile = ColorProfileRef(name="sRGB-2014")
        assert profile.safe_name == "sRGB-2014"

    def test_immutability(self):
        """Test that ColorProfileRef is immutable."""
        profile = ColorProfileRef(name="test")
        with pytest.raises(AttributeError):
            profile.name = "changed"


class TestProfiledColor:
    """Test ProfiledColor dataclass validation and properties."""

    def test_basic_creation(self):
        """Test basic profiled color creation."""
        color = ProfiledColor(profile="srgb", channels=(0.5, 0.7, 0.9))
        assert color.profile == "srgb"
        assert color.channels == (0.5, 0.7, 0.9)
        assert color.alpha == 1.0

    def test_full_creation(self):
        """Test profiled color with all parameters."""
        color = ProfiledColor(
            profile="display-p3",
            channels=(0.1, 0.2, 0.3, 0.4),
            alpha=0.8
        )
        assert color.profile == "display-p3"
        assert color.channels == (0.1, 0.2, 0.3, 0.4)
        assert color.alpha == 0.8

    def test_profile_validation(self):
        """Test profile name validation."""
        with pytest.raises(ValueError, match="Profile name must be non-empty string"):
            ProfiledColor(profile="", channels=(1.0, 0.0, 0.0))

        with pytest.raises(ValueError, match="Profile name cannot be whitespace-only"):
            ProfiledColor(profile="   ", channels=(1.0, 0.0, 0.0))

        with pytest.raises(ValueError, match="Profile name must be non-empty string"):
            ProfiledColor(profile=None, channels=(1.0, 0.0, 0.0))

    def test_channels_validation_type(self):
        """Test channels must be tuple."""
        with pytest.raises(ValueError, match="Channels must be tuple"):
            ProfiledColor(profile="test", channels=[1.0, 0.0, 0.0])

        with pytest.raises(ValueError, match="Channels must be tuple"):
            ProfiledColor(profile="test", channels="rgb")

    def test_channels_validation_empty(self):
        """Test channels cannot be empty."""
        with pytest.raises(ValueError, match="Channels tuple cannot be empty"):
            ProfiledColor(profile="test", channels=())

    def test_channels_validation_too_many(self):
        """Test channels count limit."""
        too_many = tuple(range(15))  # 15 channels
        with pytest.raises(ValueError, match="Too many channels"):
            ProfiledColor(profile="test", channels=too_many)

    def test_channels_validation_numeric(self):
        """Test channels must be numeric."""
        with pytest.raises(ValueError, match="Channel 1 must be numeric"):
            ProfiledColor(profile="test", channels=(1.0, "invalid", 0.0))

    def test_channels_validation_range(self):
        """Test channels reasonable range validation."""
        with pytest.raises(ValueError, match="Channel 0 value.*outside reasonable range"):
            ProfiledColor(profile="test", channels=(2000.0, 0.0, 0.0))

        with pytest.raises(ValueError, match="Channel 2 value.*outside reasonable range"):
            ProfiledColor(profile="test", channels=(0.0, 0.0, -2000.0))

    def test_alpha_validation_type(self):
        """Test alpha must be numeric."""
        with pytest.raises(ValueError, match="Alpha must be numeric"):
            ProfiledColor(profile="test", channels=(1.0, 0.0, 0.0), alpha="invalid")

    def test_alpha_validation_range(self):
        """Test alpha range validation."""
        with pytest.raises(ValueError, match="Alpha must be in range"):
            ProfiledColor(profile="test", channels=(1.0, 0.0, 0.0), alpha=-0.1)

        with pytest.raises(ValueError, match="Alpha must be in range"):
            ProfiledColor(profile="test", channels=(1.0, 0.0, 0.0), alpha=1.1)

    def test_is_rgb_property(self):
        """Test RGB detection."""
        rgb_color = ProfiledColor(profile="srgb", channels=(1.0, 0.0, 0.0))
        assert rgb_color.is_rgb is True

        cmyk_color = ProfiledColor(profile="cmyk", channels=(0.0, 1.0, 1.0, 0.0))
        assert cmyk_color.is_rgb is False

    def test_is_cmyk_property(self):
        """Test CMYK detection."""
        cmyk_color = ProfiledColor(profile="cmyk", channels=(0.0, 1.0, 1.0, 0.0))
        assert cmyk_color.is_cmyk is True

        rgb_color = ProfiledColor(profile="srgb", channels=(1.0, 0.0, 0.0))
        assert rgb_color.is_cmyk is False

    def test_opacity_properties(self):
        """Test opacity detection properties."""
        opaque_color = ProfiledColor(profile="test", channels=(1.0, 0.0, 0.0), alpha=1.0)
        assert opaque_color.is_opaque is True
        assert opaque_color.is_transparent is False

        transparent_color = ProfiledColor(profile="test", channels=(1.0, 0.0, 0.0), alpha=0.0)
        assert transparent_color.is_opaque is False
        assert transparent_color.is_transparent is True

        semi_transparent = ProfiledColor(profile="test", channels=(1.0, 0.0, 0.0), alpha=0.5)
        assert semi_transparent.is_opaque is False
        assert semi_transparent.is_transparent is False

    def test_with_alpha_method(self):
        """Test creating new color with different alpha."""
        original = ProfiledColor(profile="test", channels=(1.0, 0.0, 0.0), alpha=1.0)
        new_color = original.with_alpha(0.5)

        assert new_color.profile == "test"
        assert new_color.channels == (1.0, 0.0, 0.0)
        assert new_color.alpha == 0.5
        assert original.alpha == 1.0  # Original unchanged

    def test_with_channels_method(self):
        """Test creating new color with different channels."""
        original = ProfiledColor(profile="test", channels=(1.0, 0.0, 0.0), alpha=0.8)
        new_color = original.with_channels((0.0, 1.0, 0.0))

        assert new_color.profile == "test"
        assert new_color.channels == (0.0, 1.0, 0.0)
        assert new_color.alpha == 0.8
        assert original.channels == (1.0, 0.0, 0.0)  # Original unchanged

    def test_immutability(self):
        """Test that ProfiledColor is immutable."""
        color = ProfiledColor(profile="test", channels=(1.0, 0.0, 0.0))
        with pytest.raises(AttributeError):
            color.profile = "changed"


class TestUtilityFunctions:
    """Test utility functions for profile handling."""

    def test_normalize_profile_reference_string(self):
        """Test normalizing string to ColorProfileRef."""
        ref = normalize_profile_reference("srgb")
        assert isinstance(ref, ColorProfileRef)
        assert ref.name == "srgb"
        assert ref.href is None

    def test_normalize_profile_reference_object(self):
        """Test normalizing ColorProfileRef to itself."""
        original = ColorProfileRef(name="test", href="data:test")
        ref = normalize_profile_reference(original)
        assert ref is original

    def test_normalize_profile_reference_invalid(self):
        """Test error handling for invalid reference types."""
        with pytest.raises(ValueError, match="Invalid profile reference type"):
            normalize_profile_reference(123)

        with pytest.raises(ValueError, match="Invalid profile reference type"):
            normalize_profile_reference(None)

    def test_validate_color_channels_basic(self):
        """Test basic channel validation."""
        validate_color_channels((1.0, 0.0, 0.0))  # Should not raise

    def test_validate_color_channels_expected_count(self):
        """Test channel count validation."""
        validate_color_channels((1.0, 0.0, 0.0), expected_count=3)  # Should not raise

        with pytest.raises(ValueError, match="Expected 3 channels, got 4"):
            validate_color_channels((1.0, 0.0, 0.0, 1.0), expected_count=3)

    def test_validate_color_channels_type(self):
        """Test channel type validation."""
        with pytest.raises(ValueError, match="Channels must be tuple"):
            validate_color_channels([1.0, 0.0, 0.0])

    def test_validate_color_channels_numeric(self):
        """Test channel numeric validation."""
        with pytest.raises(ValueError, match="Channel 1 must be numeric"):
            validate_color_channels((1.0, "invalid", 0.0))