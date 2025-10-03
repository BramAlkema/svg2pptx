"""
Tests for CSS Color 4 Parser

Tests parsing and conversion of CSS Color 4 features including:
- color() function with various color spaces
- @color-profile rules
- lab(), lch(), oklab(), oklch() functions
- Integration with existing color system
"""

import pytest
from unittest.mock import Mock, patch
import numpy as np

from core.color.css_color4_parser import (
    parse_css_color4_function,
    CSSColor,
    ColorProfileRule,
    CSSColor4Parser,
    CSSColor4Converter,
    _parse_color_function,
    _parse_lab_lch
)


class TestCSSColor4Function:
    """Test CSS Color 4 function parsing"""

    def test_parse_color_display_p3(self):
        """Test parsing color(display-p3 ...) function"""
        result = parse_css_color4_function("color(display-p3 0.8 0.5 0.2)")

        assert result is not None
        assert result.space == "display_p3"
        assert result.coords == (0.8, 0.5, 0.2)
        assert result.alpha == 1.0

    def test_parse_color_with_alpha(self):
        """Test parsing color() function with alpha"""
        result = parse_css_color4_function("color(rec2020 0.7 0.3 0.9 / 0.5)")

        assert result is not None
        assert result.space == "rec2020"
        assert result.coords == (0.7, 0.3, 0.9)
        assert result.alpha == 0.5

    def test_parse_color_prophoto_rgb(self):
        """Test parsing color(prophoto-rgb ...) function"""
        result = parse_css_color4_function("color(prophoto-rgb 0.6 0.4 0.8)")

        assert result is not None
        assert result.space == "prophoto_rgb"
        assert result.coords == (0.6, 0.4, 0.8)
        assert result.alpha == 1.0

    def test_parse_color_a98_rgb(self):
        """Test parsing color(a98-rgb ...) function"""
        result = parse_css_color4_function("color(a98-rgb 0.9 0.1 0.3)")

        assert result is not None
        assert result.space == "adobe_rgb"
        assert result.coords == (0.9, 0.1, 0.3)
        assert result.alpha == 1.0

    def test_parse_color_srgb(self):
        """Test parsing color(srgb ...) function"""
        result = parse_css_color4_function("color(srgb 1.0 0.0 0.0)")

        assert result is not None
        assert result.space == "srgb"
        assert result.coords == (1.0, 0.0, 0.0)
        assert result.alpha == 1.0

    def test_parse_lab_function(self):
        """Test parsing lab() function"""
        result = parse_css_color4_function("lab(50% 20 -10)")

        assert result is not None
        assert result.space == "lab"
        assert result.coords == (0.5, 20.0, -10.0)
        assert result.alpha == 1.0

    def test_parse_lab_with_alpha(self):
        """Test parsing lab() function with alpha"""
        result = parse_css_color4_function("lab(70% 30 -20 / 0.8)")

        assert result is not None
        assert result.space == "lab"
        assert result.coords == (0.7, 30.0, -20.0)
        assert result.alpha == 0.8

    def test_parse_lch_function(self):
        """Test parsing lch() function"""
        result = parse_css_color4_function("lch(60% 40 120)")

        assert result is not None
        assert result.space == "lch"
        assert result.coords == (0.6, 40.0, 120.0)
        assert result.alpha == 1.0

    def test_parse_oklab_function(self):
        """Test parsing oklab() function"""
        result = parse_css_color4_function("oklab(0.7 0.1 -0.05)")

        assert result is not None
        assert result.space == "oklab"
        assert result.coords == (0.7, 0.1, -0.05)
        assert result.alpha == 1.0

    def test_parse_oklch_function(self):
        """Test parsing oklch() function"""
        result = parse_css_color4_function("oklch(0.8 0.15 180)")

        assert result is not None
        assert result.space == "oklch"
        assert result.coords == (0.8, 0.15, 180.0)
        assert result.alpha == 1.0

    def test_parse_invalid_function(self):
        """Test parsing invalid functions returns None"""
        assert parse_css_color4_function("rgb(255, 0, 0)") is None
        assert parse_css_color4_function("#ff0000") is None
        assert parse_css_color4_function("red") is None
        assert parse_css_color4_function("invalid(1, 2, 3)") is None

    def test_parse_malformed_color_function(self):
        """Test parsing malformed color() functions"""
        assert parse_css_color4_function("color(") is None
        assert parse_css_color4_function("color(display-p3)") is None
        assert parse_css_color4_function("color(invalid-space 0.5)") is not None  # Still parses


class TestColorProfileRules:
    """Test @color-profile rule parsing"""

    def test_parse_simple_color_profile(self):
        """Test parsing basic @color-profile rule"""
        css = '''
        @color-profile --my-profile {
            src: url("profile.icc");
        }
        '''

        parser = CSSColor4Parser()
        profiles = parser.parse_color_profile_rule(css)

        assert len(profiles) == 1
        profile = profiles[0]
        assert profile.name == "--my-profile"
        assert profile.src == "profile.icc"
        assert profile.rendering_intent == "relative-colorimetric"

    def test_parse_color_profile_with_intent(self):
        """Test parsing @color-profile rule with rendering intent"""
        css = '''
        @color-profile --display-p3 {
            src: url("display-p3.icc");
            rendering-intent: perceptual;
        }
        '''

        parser = CSSColor4Parser()
        profiles = parser.parse_color_profile_rule(css)

        assert len(profiles) == 1
        profile = profiles[0]
        assert profile.name == "--display-p3"
        assert profile.src == "display-p3.icc"
        assert profile.rendering_intent == "perceptual"

    def test_parse_multiple_color_profiles(self):
        """Test parsing multiple @color-profile rules"""
        css = '''
        @color-profile --profile1 {
            src: url("profile1.icc");
        }
        @color-profile --profile2 {
            src: url("profile2.icc");
            rendering-intent: saturation;
        }
        '''

        parser = CSSColor4Parser()
        profiles = parser.parse_color_profile_rule(css)

        assert len(profiles) == 2
        assert profiles[0].name == "--profile1"
        assert profiles[1].name == "--profile2"
        assert profiles[1].rendering_intent == "saturation"

    def test_extract_url_variants(self):
        """Test URL extraction with different quote styles"""
        parser = CSSColor4Parser()

        assert parser._extract_url('url("file.icc")') == "file.icc"
        assert parser._extract_url("url('file.icc')") == "file.icc"
        assert parser._extract_url('url(file.icc)') == "file.icc"
        assert parser._extract_url('"direct.icc"') == "direct.icc"

    def test_get_color_profile(self):
        """Test retrieving parsed color profiles"""
        css = '@color-profile --test { src: url("test.icc"); }'

        parser = CSSColor4Parser()
        parser.parse_color_profile_rule(css)

        profile = parser.get_color_profile("--test")
        assert profile is not None
        assert profile.name == "--test"
        assert profile.src == "test.icc"

        assert parser.get_color_profile("--nonexistent") is None


class TestCSSColor4Converter:
    """Test CSS Color 4 conversion to sRGB"""

    def test_convert_srgb_passthrough(self):
        """Test sRGB colors pass through unchanged"""
        converter = CSSColor4Converter()
        css_color = CSSColor("srgb", (1.0, 0.0, 0.0), 0.8)

        result = converter.convert_css_color(css_color)

        assert result == (1.0, 0.0, 0.0, 0.8)

    def test_convert_with_known_profiles(self):
        """Test conversion using known profiles"""
        mock_known_profiles = Mock()
        mock_known_profiles.convert_to_srgb.return_value = np.array([[0.9, 0.1, 0.2]])

        converter = CSSColor4Converter(known_profiles=mock_known_profiles)
        css_color = CSSColor("display_p3", (0.8, 0.5, 0.3), 1.0)

        result = converter.convert_css_color(css_color)

        assert result == (0.9, 0.1, 0.2, 1.0)
        mock_known_profiles.convert_to_srgb.assert_called_once()

    def test_convert_with_icc_converter(self):
        """Test conversion using ICC converter"""
        mock_icc_converter = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.color = (0.7, 0.8, 0.9)
        mock_icc_converter.convert_to_srgb.return_value = mock_result

        converter = CSSColor4Converter(icc_converter=mock_icc_converter)
        css_color = CSSColor("prophoto_rgb", (0.6, 0.4, 0.8), 0.5)

        result = converter.convert_css_color(css_color)

        assert result == (0.7, 0.8, 0.9, 0.5)
        mock_icc_converter.convert_to_srgb.assert_called_once_with(
            (0.6, 0.4, 0.8), "prophoto_rgb"
        )

    def test_convert_fallback_chain(self):
        """Test fallback from known profiles to ICC converter"""
        mock_known_profiles = Mock()
        mock_known_profiles.convert_to_srgb.return_value = None  # Fail

        mock_icc_converter = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.color = (0.5, 0.6, 0.7)
        mock_icc_converter.convert_to_srgb.return_value = mock_result

        converter = CSSColor4Converter(
            known_profiles=mock_known_profiles,
            icc_converter=mock_icc_converter
        )
        css_color = CSSColor("rec2020", (0.4, 0.3, 0.2), 1.0)

        result = converter.convert_css_color(css_color)

        assert result == (0.5, 0.6, 0.7, 1.0)
        mock_known_profiles.convert_to_srgb.assert_called_once()
        mock_icc_converter.convert_to_srgb.assert_called_once()

    def test_convert_ultimate_fallback(self):
        """Test ultimate fallback when all converters fail"""
        converter = CSSColor4Converter()  # No converters
        css_color = CSSColor("unknown_space", (0.1, 0.2, 0.3), 1.0)

        result = converter.convert_css_color(css_color)

        # Returns as-is with warning
        assert result == (0.1, 0.2, 0.3, 1.0)

    @patch('core.color.safe_lab.convert_lab_to_srgb_safe')
    def test_convert_lab_color_space(self, mock_lab_convert):
        """Test LAB color space conversion"""
        mock_lab_convert.return_value = (0.8, 0.1, 0.3)

        converter = CSSColor4Converter()
        css_color = CSSColor("lab", (50.0, 20.0, -10.0), 0.9)

        result = converter.convert_css_color(css_color)

        assert result == (0.8, 0.1, 0.3, 0.9)
        mock_lab_convert.assert_called_once_with((50.0, 20.0, -10.0))

    def test_convert_unsupported_perceptual_space(self):
        """Test unsupported perceptual color spaces"""
        converter = CSSColor4Converter()
        css_color = CSSColor("oklch", (0.7, 0.15, 180.0), 1.0)

        result = converter.convert_css_color(css_color)

        # Returns fallback color
        assert result == (0.5, 0.5, 0.5, 1.0)

    def test_convert_xyz_color_space(self):
        """Test XYZ color space (not yet implemented)"""
        converter = CSSColor4Converter()
        css_color = CSSColor("xyz", (0.3, 0.4, 0.5), 1.0)

        result = converter.convert_css_color(css_color)

        # Returns fallback color
        assert result == (0.5, 0.5, 0.5, 1.0)

    def test_resolve_color_success(self):
        """Test successful color resolution"""
        converter = CSSColor4Converter()

        result = converter.resolve_color("color(srgb 1.0 0.5 0.0)")

        assert result == (1.0, 0.5, 0.0, 1.0)

    def test_resolve_color_invalid(self):
        """Test color resolution with invalid input"""
        converter = CSSColor4Converter()

        with pytest.raises(ValueError, match="Not a CSS Color 4 function"):
            converter.resolve_color("rgb(255, 0, 0)")


class TestColorFunctionDetection:
    """Test detection of color functions in text"""

    def test_detect_single_color_function(self):
        """Test detecting single color() function in text"""
        parser = CSSColor4Parser()
        text = "fill: color(display-p3 0.8 0.5 0.2);"

        results = parser.detect_color_functions(text)

        assert len(results) == 1
        original, parsed = results[0]
        assert original == "color(display-p3 0.8 0.5 0.2)"
        assert parsed.space == "display_p3"
        assert parsed.coords == (0.8, 0.5, 0.2)

    def test_detect_multiple_color_functions(self):
        """Test detecting multiple color() functions in text"""
        parser = CSSColor4Parser()
        text = '''
        .class1 { fill: color(rec2020 0.7 0.3 0.9); }
        .class2 { stroke: color(srgb 1.0 0.0 0.0 / 0.5); }
        '''

        results = parser.detect_color_functions(text)

        assert len(results) == 2
        assert results[0][1].space == "rec2020"
        assert results[1][1].space == "srgb"
        assert results[1][1].alpha == 0.5

    def test_detect_no_color_functions(self):
        """Test text with no color() functions"""
        parser = CSSColor4Parser()
        text = "fill: #ff0000; stroke: rgb(0, 255, 0);"

        results = parser.detect_color_functions(text)

        assert len(results) == 0


class TestHelperFunctions:
    """Test individual helper functions"""

    def test_parse_color_function_direct(self):
        """Test _parse_color_function directly"""
        result = _parse_color_function("color(display-p3 0.8 0.5 0.2)")

        assert result is not None
        assert result.space == "display_p3"
        assert result.coords == (0.8, 0.5, 0.2)
        assert result.alpha == 1.0

    def test_parse_color_function_invalid(self):
        """Test _parse_color_function with invalid input"""
        assert _parse_color_function("invalid") is None
        assert _parse_color_function("color(") is None

    def test_parse_lab_lch_direct(self):
        """Test _parse_lab_lch directly"""
        result = _parse_lab_lch("lab(50% 20 -10)", "lab")

        assert result is not None
        assert result.space == "lab"
        assert result.coords == (0.5, 20.0, -10.0)
        assert result.alpha == 1.0

    def test_parse_lab_lch_with_alpha(self):
        """Test _parse_lab_lch with alpha"""
        result = _parse_lab_lch("lch(60% 40 120 / 0.7)", "lch")

        assert result is not None
        assert result.space == "lch"
        assert result.coords == (0.6, 40.0, 120.0)
        assert result.alpha == 0.7


class TestIntegrationScenarios:
    """Test integration scenarios"""

    def test_full_workflow_display_p3(self):
        """Test full workflow from CSS to sRGB conversion"""
        # Mock known profiles for Display P3 conversion
        mock_known_profiles = Mock()
        mock_known_profiles.convert_to_srgb.return_value = np.array([[0.95, 0.2, 0.1]])

        converter = CSSColor4Converter(known_profiles=mock_known_profiles)

        # Parse and convert Display P3 color
        result = converter.resolve_color("color(display-p3 0.9 0.3 0.2 / 0.8)")

        assert result == (0.95, 0.2, 0.1, 0.8)

    def test_css_profile_integration(self):
        """Test CSS @color-profile integration with color functions"""
        css = '''
        @color-profile --my-p3 {
            src: url("display-p3.icc");
            rendering-intent: perceptual;
        }

        .element {
            fill: color(display-p3 0.8 0.5 0.2);
        }
        '''

        parser = CSSColor4Parser()

        # Parse profiles
        profiles = parser.parse_color_profile_rule(css)
        assert len(profiles) == 1
        assert profiles[0].name == "--my-p3"

        # Detect color functions
        colors = parser.detect_color_functions(css)
        assert len(colors) == 1
        assert colors[0][1].space == "display_p3"

    def test_error_handling_robustness(self):
        """Test error handling in various scenarios"""
        converter = CSSColor4Converter()

        # None input
        result = converter.convert_css_color(None)
        assert result == (0.0, 0.0, 0.0, 1.0)

        # Invalid parsing
        with pytest.raises(ValueError):
            converter.resolve_color("invalid-color")

        # Malformed functions should still work with parser
        parsed = parse_css_color4_function("color(unknown-space 0.5 0.5 0.5)")
        assert parsed is not None
        assert parsed.space == "unknown-space"