#!/usr/bin/env python3
"""
Unit tests for SVG Color Profile Adapter.

Tests the SVG <color-profile> element parsing and integration
with the known profiles system.
"""

import pytest
from lxml import etree as ET
from tests.helpers.color_asserts import approx_eq, assert_rgb_close

from core.color.svg_profile_adapter import (
    SVGColorProfileRegistry,
    resolve_profile_for_paint,
    parse_color_function,
    convert_color_to_srgb,
    register_css_color_profile,
    ColorProfileContext
)


class TestSVGColorProfileRegistry:
    """Test SVG color profile registry functionality."""

    def test_empty_registry_initialization(self):
        """Test registry initializes with sRGB default."""
        registry = SVGColorProfileRegistry()

        # Should have sRGB by default
        assert 'srgb' in registry.by_name
        srgb_profile = registry.resolve('srgb')
        assert srgb_profile.name == 'srgb'

    def test_parse_color_profile_elements(self):
        """Test parsing <color-profile> elements from SVG."""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <color-profile name="display-p3"/>
                <color-profile name="adobe-rgb"/>
                <color-profile id="rec2020"/>
            </defs>
        </svg>
        """

        root = ET.fromstring(svg_content)
        registry = SVGColorProfileRegistry()
        registry.parse_color_profiles(root)

        # Should resolve known profiles
        assert registry.resolve('display-p3').name == 'display-p3'
        assert registry.resolve('adobe-rgb').name == 'adobe-rgb'
        assert registry.resolve('rec2020').name == 'rec2020'

    def test_parse_color_profile_without_namespace(self):
        """Test parsing color-profile elements without SVG namespace."""
        svg_content = """
        <svg>
            <defs>
                <color-profile name="display-p3"/>
            </defs>
        </svg>
        """

        root = ET.fromstring(svg_content)
        registry = SVGColorProfileRegistry()
        registry.parse_color_profiles(root)

        assert registry.resolve('display-p3').name == 'display-p3'

    def test_profile_name_patterns(self):
        """Test profile name pattern matching."""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <color-profile name="P3"/>
                <color-profile name="bt2020"/>
                <color-profile name="adobergb"/>
                <color-profile name="prophoto"/>
                <color-profile name="romm-rgb"/>
            </defs>
        </svg>
        """

        root = ET.fromstring(svg_content)
        registry = SVGColorProfileRegistry()
        registry.parse_color_profiles(root)

        # Should match patterns to known profiles
        assert registry.resolve('P3').name == 'display-p3'
        assert registry.resolve('bt2020').name == 'rec2020'
        assert registry.resolve('adobergb').name == 'adobe-rgb'
        assert registry.resolve('prophoto').name == 'prophoto-rgb'
        assert registry.resolve('romm-rgb').name == 'prophoto-rgb'

    def test_unknown_profile_fallback(self):
        """Test unknown profiles fall back to sRGB."""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <color-profile name="unknown-profile"/>
            </defs>
        </svg>
        """

        root = ET.fromstring(svg_content)
        registry = SVGColorProfileRegistry()
        registry.parse_color_profiles(root)

        # Unknown profile should fall back to sRGB
        profile = registry.resolve('unknown-profile')
        assert profile.name == 'srgb'

    def test_resolve_none_profile(self):
        """Test resolving None profile returns sRGB."""
        registry = SVGColorProfileRegistry()
        profile = registry.resolve(None)
        assert profile.name == 'srgb'

    def test_list_profiles(self):
        """Test getting list of registered profiles."""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <color-profile name="display-p3"/>
                <color-profile name="adobe-rgb"/>
            </defs>
        </svg>
        """

        root = ET.fromstring(svg_content)
        registry = SVGColorProfileRegistry()
        registry.parse_color_profiles(root)

        profiles = registry.list_profiles()

        assert 'srgb' in profiles
        assert 'display-p3' in profiles
        assert 'adobe-rgb' in profiles
        assert isinstance(profiles['srgb'], str)  # Should be description


class TestPaintResolver:
    """Test paint value resolution."""

    def setup_method(self):
        """Set up test registry."""
        self.registry = SVGColorProfileRegistry()

        # Add some profiles
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <color-profile name="display-p3"/>
                <color-profile name="adobe-rgb"/>
            </defs>
        </svg>
        """
        root = ET.fromstring(svg_content)
        self.registry.parse_color_profiles(root)

    def test_resolve_color_function(self):
        """Test resolving color() function syntax."""
        # Test various color() function formats
        test_cases = [
            ("color(display-p3 1 0 0)", "display-p3"),
            ("color(adobe-rgb 0.5 0.6 0.7)", "adobe-rgb"),
            ("COLOR(sRGB 1 1 1)", "srgb"),
            ("color( display-p3  1  0  0 )", "display-p3"),  # Extra spaces
        ]

        for paint_value, expected_profile in test_cases:
            profile = resolve_profile_for_paint(paint_value, self.registry)
            assert profile.name == expected_profile

    def test_resolve_non_color_function(self):
        """Test resolving non-color() paint values."""
        # Regular colors should fall back to sRGB
        test_cases = [
            "#ff0000",
            "red",
            "rgb(255, 0, 0)",
            "hsl(0, 100%, 50%)",
            "",
            None,
        ]

        for paint_value in test_cases:
            profile = resolve_profile_for_paint(paint_value, self.registry)
            assert profile.name == 'srgb'

    def test_resolve_profile_reference(self):
        """Test resolving direct profile references."""
        # Test cases where profile name appears in paint value
        paint_value = "some-paint-with-display-p3-reference"
        profile = resolve_profile_for_paint(paint_value, self.registry)
        assert profile.name == 'display-p3'


class TestColorFunctionParsing:
    """Test color() function parsing."""

    def test_parse_valid_color_function(self):
        """Test parsing valid color() functions."""
        test_cases = [
            ("color(display-p3 1 0 0)", ("display-p3", (1.0, 0.0, 0.0))),
            ("color(srgb 0.5 0.6 0.7)", ("srgb", (0.5, 0.6, 0.7))),
            ("COLOR(adobe-rgb 0.2 0.8 0.4)", ("adobe-rgb", (0.2, 0.8, 0.4))),
            ("color( rec2020  1.0  0.5  0.0 )", ("rec2020", (1.0, 0.5, 0.0))),
        ]

        for color_string, expected in test_cases:
            result = parse_color_function(color_string)
            assert result is not None
            profile_name, (r, g, b) = result
            expected_profile, (er, eg, eb) = expected

            assert profile_name == expected_profile
            assert approx_eq((r, g, b), (er, eg, eb), tol=1e-6)

    def test_parse_invalid_color_function(self):
        """Test parsing invalid color() functions."""
        test_cases = [
            "color(srgb 1 0)",  # Too few values
            "color(srgb)",      # No values
            "color()",          # Empty
            "rgb(255, 0, 0)",   # Not color() function
            "#ff0000",          # Hex color
            "",                 # Empty string
            None,               # None
        ]

        for color_string in test_cases:
            result = parse_color_function(color_string)
            assert result is None

    def test_parse_color_function_clamping(self):
        """Test that color values are clamped to [0, 1]."""
        test_cases = [
            ("color(srgb 1.5 -0.5 0.5)", (1.0, 0.0, 0.5)),
            ("color(srgb 2.0 2.0 2.0)", (1.0, 1.0, 1.0)),
            ("color(srgb -1.0 -1.0 -1.0)", (0.0, 0.0, 0.0)),
        ]

        for color_string, expected_rgb in test_cases:
            result = parse_color_function(color_string)
            assert result is not None
            _, rgb = result
            assert approx_eq(rgb, expected_rgb, tol=1e-6)


class TestColorConversion:
    """Test color conversion functionality."""

    def setup_method(self):
        """Set up test registry."""
        self.registry = SVGColorProfileRegistry()

        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <color-profile name="display-p3"/>
                <color-profile name="adobe-rgb"/>
            </defs>
        </svg>
        """
        root = ET.fromstring(svg_content)
        self.registry.parse_color_profiles(root)

    def test_convert_color_function_to_srgb(self):
        """Test converting color() functions to sRGB."""
        # Test sRGB identity
        srgb_result = convert_color_to_srgb("color(srgb 1 0 0)", self.registry)
        assert srgb_result is not None
        assert_rgb_close(srgb_result, (1.0, 0.0, 0.0), tolerance=1e-6)

        # Test Display P3 conversion
        p3_result = convert_color_to_srgb("color(display-p3 1 0 0)", self.registry)
        assert p3_result is not None
        assert len(p3_result) == 3
        assert all(0.0 <= c <= 1.0 for c in p3_result)

        # Test Adobe RGB conversion
        adobe_result = convert_color_to_srgb("color(adobe-rgb 0.5 0.6 0.7)", self.registry)
        assert adobe_result is not None
        assert len(adobe_result) == 3
        assert all(0.0 <= c <= 1.0 for c in adobe_result)

    def test_convert_non_color_function(self):
        """Test handling of non-color() functions."""
        # Non-color() functions should return None
        result = convert_color_to_srgb("#ff0000", self.registry)
        assert result is None

        result = convert_color_to_srgb("red", self.registry)
        assert result is None

        result = convert_color_to_srgb("", self.registry)
        assert result is None

    def test_convert_invalid_color_function(self):
        """Test handling of invalid color() functions."""
        # Invalid functions should return None
        result = convert_color_to_srgb("color(invalid)", self.registry)
        assert result is None

        result = convert_color_to_srgb("color(srgb)", self.registry)
        assert result is None


class TestCSSColorProfile:
    """Test CSS @color-profile rule registration."""

    def test_register_css_color_profile(self):
        """Test registering CSS color profiles."""
        registry = SVGColorProfileRegistry()

        # Register known profiles
        assert register_css_color_profile("display-p3", registry=registry) is True
        assert register_css_color_profile("adobe-rgb", registry=registry) is True

        # Verify registration
        assert registry.resolve("display-p3").name == "display-p3"
        assert registry.resolve("adobe-rgb").name == "adobe-rgb"

    def test_register_unknown_css_profile(self):
        """Test registering unknown CSS profiles."""
        registry = SVGColorProfileRegistry()

        # Unknown profiles should fail to register
        assert register_css_color_profile("unknown-profile", registry=registry) is False

    def test_register_css_profile_without_registry(self):
        """Test registering CSS profiles without providing registry."""
        # Should create new registry internally
        result = register_css_color_profile("display-p3")
        assert result is True


class TestColorProfileContext:
    """Test ColorProfileContext context manager."""

    def test_context_without_svg(self):
        """Test context manager without SVG root."""
        with ColorProfileContext() as ctx:
            # Should have default sRGB profile
            profile = ctx.resolve_profile("srgb")
            assert profile.name == "srgb"

            # Should return None for non-color() functions
            result = ctx.convert_color("#ff0000")
            assert result is None

    def test_context_with_svg(self):
        """Test context manager with SVG root."""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <color-profile name="display-p3"/>
            </defs>
        </svg>
        """
        root = ET.fromstring(svg_content)

        with ColorProfileContext(root) as ctx:
            # Should have parsed profiles
            profile = ctx.resolve_profile("display-p3")
            assert profile.name == "display-p3"

            # Should convert color() functions
            result = ctx.convert_color("color(display-p3 1 0 0)")
            assert result is not None
            assert len(result) == 3

    def test_context_conversion_methods(self):
        """Test context manager conversion methods."""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <color-profile name="display-p3"/>
            </defs>
        </svg>
        """
        root = ET.fromstring(svg_content)

        with ColorProfileContext(root) as ctx:
            # Test convert_color method
            result = ctx.convert_color("color(srgb 1 0 0)")
            assert_rgb_close(result, (1.0, 0.0, 0.0), tolerance=1e-6)

            # Test resolve_profile method
            profile = ctx.resolve_profile("display-p3")
            assert profile.name == "display-p3"

            # Test with unknown profile (should fall back to sRGB)
            unknown_profile = ctx.resolve_profile("unknown")
            assert unknown_profile.name == "srgb"


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""

    def test_svg_with_multiple_profiles(self):
        """Test SVG with multiple color profile definitions."""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <defs>
                <color-profile name="display-p3"/>
                <color-profile name="adobe-rgb"/>
                <color-profile name="rec2020"/>
            </defs>
            <rect fill="color(display-p3 1 0 0)" width="50" height="50"/>
            <circle fill="color(adobe-rgb 0 1 0)" cx="75" cy="75" r="20"/>
        </svg>
        """

        root = ET.fromstring(svg_content)
        registry = SVGColorProfileRegistry()
        registry.parse_color_profiles(root)

        # Should parse all profiles
        assert registry.resolve("display-p3").name == "display-p3"
        assert registry.resolve("adobe-rgb").name == "adobe-rgb"
        assert registry.resolve("rec2020").name == "rec2020"

        # Should convert colors correctly
        p3_red = convert_color_to_srgb("color(display-p3 1 0 0)", registry)
        adobe_green = convert_color_to_srgb("color(adobe-rgb 0 1 0)", registry)

        assert p3_red is not None
        assert adobe_green is not None

    def test_nested_defs_profiles(self):
        """Test color profiles in nested defs elements."""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <g>
                    <defs>
                        <color-profile name="display-p3"/>
                    </defs>
                </g>
                <color-profile name="adobe-rgb"/>
            </defs>
        </svg>
        """

        root = ET.fromstring(svg_content)
        registry = SVGColorProfileRegistry()
        registry.parse_color_profiles(root)

        # Should find profiles at any level
        assert registry.resolve("display-p3").name == "display-p3"
        assert registry.resolve("adobe-rgb").name == "adobe-rgb"

    def test_case_insensitive_profile_names(self):
        """Test case-insensitive profile name handling."""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <color-profile name="Display-P3"/>
                <color-profile name="ADOBE-RGB"/>
            </defs>
        </svg>
        """

        root = ET.fromstring(svg_content)
        registry = SVGColorProfileRegistry()
        registry.parse_color_profiles(root)

        # Should resolve case-insensitively
        assert registry.resolve("display-p3").name == "display-p3"
        assert registry.resolve("adobe-rgb").name == "adobe-rgb"
        assert registry.resolve("DISPLAY-P3").name == "display-p3"
        assert registry.resolve("Adobe-RGB").name == "adobe-rgb"