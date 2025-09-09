#!/usr/bin/env python3
"""
Unit tests for colors module functionality.

Tests the Universal Color Parser including color format parsing, DrawingML
conversion, color space transformations, and contrast calculations.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import sys
import math

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.colors import (
    ColorParser, ColorInfo, ColorFormat, NAMED_COLORS,
    rgb_to_hsl, hsl_to_rgb, parse_color, to_drawingml, create_solid_fill
)


class TestColorFormat:
    """Test ColorFormat enum."""
    
    def test_color_format_values(self):
        """Test color format enum values."""
        assert ColorFormat.HEX.value == "hex"
        assert ColorFormat.RGB.value == "rgb"
        assert ColorFormat.RGBA.value == "rgba"
        assert ColorFormat.HSL.value == "hsl"
        assert ColorFormat.HSLA.value == "hsla"
        assert ColorFormat.NAMED.value == "named"
        assert ColorFormat.TRANSPARENT.value == "transparent"
        assert ColorFormat.CURRENT_COLOR.value == "currentColor"
        assert ColorFormat.INHERIT.value == "inherit"


class TestColorInfo:
    """Test ColorInfo dataclass and properties."""
    
    def test_color_info_creation(self):
        """Test ColorInfo creation."""
        color = ColorInfo(255, 128, 64, 0.8, ColorFormat.RGB, "rgb(255,128,64)")
        
        assert color.red == 255
        assert color.green == 128
        assert color.blue == 64
        assert color.alpha == 0.8
        assert color.format == ColorFormat.RGB
        assert color.original == "rgb(255,128,64)"
    
    def test_hex_property(self):
        """Test hex property conversion."""
        color = ColorInfo(255, 0, 0, 1.0, ColorFormat.RGB, "red")
        assert color.hex == "FF0000"
        
        color = ColorInfo(128, 255, 64, 1.0, ColorFormat.RGB, "green-ish")
        assert color.hex == "80FF40"
    
    def test_hex_alpha_property(self):
        """Test hex with alpha property."""
        color = ColorInfo(255, 0, 0, 0.5, ColorFormat.RGBA, "rgba(255,0,0,0.5)")
        assert color.hex_alpha == "FF00007F"  # 0.5 * 255 = 127.5 -> 127 = 0x7F
        
        color = ColorInfo(255, 0, 0, 1.0, ColorFormat.RGB, "red")
        assert color.hex_alpha == "FF0000FF"
    
    def test_rgb_tuple_property(self):
        """Test RGB tuple property."""
        color = ColorInfo(255, 128, 64, 0.8, ColorFormat.RGB, "test")
        assert color.rgb_tuple == (255, 128, 64)
    
    def test_rgba_tuple_property(self):
        """Test RGBA tuple property."""
        color = ColorInfo(255, 128, 64, 0.8, ColorFormat.RGB, "test")
        assert color.rgba_tuple == (255, 128, 64, 0.8)
    
    def test_hsl_property(self):
        """Test HSL conversion property."""
        # Red color
        color = ColorInfo(255, 0, 0, 1.0, ColorFormat.RGB, "red")
        h, s, l = color.hsl
        assert abs(h - 0) < 1  # Red is at 0 degrees
        assert s == 100  # Full saturation
        assert l == 50   # 50% lightness
        
        # White color  
        color = ColorInfo(255, 255, 255, 1.0, ColorFormat.RGB, "white")
        h, s, l = color.hsl
        assert s == 0    # No saturation
        assert l == 100  # Full lightness
    
    def test_luminance_calculation(self):
        """Test relative luminance calculation."""
        # Black
        color = ColorInfo(0, 0, 0, 1.0, ColorFormat.RGB, "black")
        assert color.luminance == 0.0
        
        # White
        color = ColorInfo(255, 255, 255, 1.0, ColorFormat.RGB, "white")
        assert color.luminance == 1.0
        
        # Gray (middle luminance)
        color = ColorInfo(128, 128, 128, 1.0, ColorFormat.RGB, "gray")
        assert 0.2 < color.luminance < 0.25  # Approximate middle luminance
    
    def test_is_dark_method(self):
        """Test dark color detection."""
        # Black is dark
        color = ColorInfo(0, 0, 0, 1.0, ColorFormat.RGB, "black")
        assert color.is_dark() is True
        
        # White is not dark
        color = ColorInfo(255, 255, 255, 1.0, ColorFormat.RGB, "white")
        assert color.is_dark() is False
        
        # Custom threshold
        color = ColorInfo(100, 100, 100, 1.0, ColorFormat.RGB, "dark gray")
        assert color.is_dark(threshold=0.3) is True
        assert color.is_dark(threshold=0.1) is False
    
    def test_contrast_ratio(self):
        """Test contrast ratio calculation."""
        black = ColorInfo(0, 0, 0, 1.0, ColorFormat.RGB, "black")
        white = ColorInfo(255, 255, 255, 1.0, ColorFormat.RGB, "white")
        
        # Black vs white should have maximum contrast (21:1)
        ratio = black.contrast_ratio(white)
        assert abs(ratio - 21.0) < 0.1
        
        # Same colors should have 1:1 contrast
        ratio = black.contrast_ratio(black)
        assert ratio == 1.0


class TestColorParser:
    """Test ColorParser functionality."""
    
    def test_parser_initialization(self):
        """Test parser initialization."""
        parser = ColorParser()
        
        assert parser.hex_pattern is not None
        assert parser.rgb_pattern is not None
        assert parser.hsl_pattern is not None
        assert parser.current_color is None
    
    def test_parse_hex_6_digit(self):
        """Test parsing 6-digit hex colors."""
        parser = ColorParser()
        
        color = parser.parse("#FF0000")
        assert color.red == 255
        assert color.green == 0
        assert color.blue == 0
        assert color.alpha == 1.0
        assert color.format == ColorFormat.HEX
        
        # Lowercase
        color = parser.parse("#ff0000")
        assert color.red == 255
        assert color.green == 0
        assert color.blue == 0
    
    def test_parse_hex_3_digit(self):
        """Test parsing 3-digit hex colors (should expand)."""
        parser = ColorParser()
        
        color = parser.parse("#F00")
        assert color.red == 255
        assert color.green == 0
        assert color.blue == 0
        
        color = parser.parse("#ABC")
        assert color.red == 170  # AA
        assert color.green == 187  # BB
        assert color.blue == 204  # CC
    
    def test_parse_hex_8_digit(self):
        """Test parsing 8-digit hex colors with alpha."""
        parser = ColorParser()
        
        color = parser.parse("#FF000080")
        assert color.red == 255
        assert color.green == 0
        assert color.blue == 0
        assert abs(color.alpha - 0.502) < 0.01  # 0x80 = 128, 128/255 ≈ 0.502
    
    def test_parse_rgb(self):
        """Test parsing RGB colors."""
        parser = ColorParser()
        
        color = parser.parse("rgb(255, 0, 0)")
        assert color.red == 255
        assert color.green == 0
        assert color.blue == 0
        assert color.alpha == 1.0
        assert color.format == ColorFormat.RGB
        
        # With spaces and different formatting
        color = parser.parse("rgb(128,64,32)")
        assert color.red == 128
        assert color.green == 64
        assert color.blue == 32
    
    def test_parse_rgba(self):
        """Test parsing RGBA colors."""
        parser = ColorParser()
        
        color = parser.parse("rgba(255, 0, 0, 0.5)")
        assert color.red == 255
        assert color.green == 0
        assert color.blue == 0
        assert color.alpha == 0.5
        assert color.format == ColorFormat.RGBA
        
        # Alpha as percentage
        color = parser.parse("rgba(255, 0, 0, 50%)")
        assert color.alpha == 0.5
    
    def test_parse_rgb_percentage(self):
        """Test parsing RGB with percentage values."""
        parser = ColorParser()
        
        color = parser.parse("rgb(100%, 0%, 50%)")
        assert color.red == 255
        assert color.green == 0
        assert color.blue == 127  # 50% of 255 = 127.5 -> 127
    
    def test_parse_hsl(self):
        """Test parsing HSL colors."""
        parser = ColorParser()
        
        # Red color: hue=0, sat=100%, light=50%
        color = parser.parse("hsl(0, 100%, 50%)")
        assert color is not None
        assert color.red == 255
        assert color.green == 0
        assert color.blue == 0
        assert color.format == ColorFormat.HSL
        
        # Blue color: hue=240, sat=100%, light=50%
        color = parser.parse("hsl(240, 100%, 50%)")
        assert color is not None
        assert color.red == 0
        assert color.green == 0
        assert color.blue == 255
    
    def test_parse_hsla(self):
        """Test parsing HSLA colors."""
        parser = ColorParser()
        
        color = parser.parse("hsla(0, 100%, 50%, 0.7)")
        assert color is not None
        assert color.red == 255
        assert color.green == 0
        assert color.blue == 0
        assert color.alpha == 0.7
        assert color.format == ColorFormat.HSLA
        
        # Alpha as percentage
        color = parser.parse("hsla(0, 100%, 50%, 70%)")
        assert color is not None
        assert color.alpha == 0.7
    
    def test_parse_named_colors(self):
        """Test parsing named colors."""
        parser = ColorParser()
        
        color = parser.parse("red")
        assert color.red == 255
        assert color.green == 0
        assert color.blue == 0
        assert color.format == ColorFormat.NAMED
        
        color = parser.parse("blue")
        assert color.red == 0
        assert color.green == 0
        assert color.blue == 255
        
        color = parser.parse("white")
        assert color.red == 255
        assert color.green == 255
        assert color.blue == 255
        
        # Test case insensitive
        color = parser.parse("RED")
        assert color.red == 255
        assert color.green == 0
        assert color.blue == 0
    
    def test_parse_special_values(self):
        """Test parsing special color values."""
        parser = ColorParser()
        
        # Transparent
        color = parser.parse("transparent")
        assert color.format == ColorFormat.TRANSPARENT
        assert color.alpha == 0.0
        
        # None
        color = parser.parse("none")
        assert color.format == ColorFormat.TRANSPARENT
        assert color.alpha == 0.0
        
        # currentColor without context
        color = parser.parse("currentColor")
        assert color.format == ColorFormat.CURRENT_COLOR
        
        # currentColor with context
        context_color = ColorInfo(128, 64, 32, 0.8, ColorFormat.RGB, "context")
        color = parser.parse("currentColor", context_color)
        assert color.red == 128
        assert color.green == 64
        assert color.blue == 32
        assert color.alpha == 0.8
        assert color.format == ColorFormat.CURRENT_COLOR
        
        # Inherit
        color = parser.parse("inherit")
        assert color.format == ColorFormat.INHERIT
    
    def test_parse_invalid_colors(self):
        """Test parsing invalid color values."""
        parser = ColorParser()
        
        assert parser.parse("") is None
        assert parser.parse("invalid") is None
        assert parser.parse("rgb(300, 400, 500)") is not None  # Should clamp values
        assert parser.parse("#ZZZ") is None
        assert parser.parse("rgb(a, b, c)") is None
        assert parser.parse(None) is None
        assert parser.parse(123) is None
    
    def test_rgb_value_clamping(self):
        """Test RGB value clamping for out-of-range values."""
        parser = ColorParser()
        
        color = parser.parse("rgb(300, -50, 400)")
        assert color.red == 255   # Clamped to 255
        assert color.green == 0   # Clamped to 0
        assert color.blue == 255  # Clamped to 255
    
    def test_alpha_value_clamping(self):
        """Test alpha value clamping."""
        parser = ColorParser()
        
        color = parser.parse("rgba(255, 0, 0, 1.5)")
        assert color.alpha == 1.0  # Clamped to 1.0
        
        color = parser.parse("rgba(255, 0, 0, -0.5)")
        assert color.alpha == 0.0  # Clamped to 0.0
    
    def test_to_drawingml_basic(self):
        """Test basic DrawingML conversion."""
        parser = ColorParser()
        color = ColorInfo(255, 0, 0, 1.0, ColorFormat.RGB, "red")
        
        xml = parser.to_drawingml(color)
        assert xml == '<a:srgbClr val="FF0000"/>'
    
    def test_to_drawingml_with_alpha(self):
        """Test DrawingML conversion with alpha."""
        parser = ColorParser()
        color = ColorInfo(255, 0, 0, 0.5, ColorFormat.RGBA, "rgba(255,0,0,0.5)")
        
        xml = parser.to_drawingml(color)
        assert '<a:srgbClr val="FF0000">' in xml
        assert '<a:alpha val="50000"/>' in xml  # 0.5 * 100000 = 50000
        assert xml.endswith('</a:srgbClr>')
    
    def test_to_drawingml_transparent(self):
        """Test DrawingML conversion for transparent colors."""
        parser = ColorParser()
        color = ColorInfo(0, 0, 0, 0.0, ColorFormat.TRANSPARENT, "transparent")
        
        xml = parser.to_drawingml(color)
        assert xml == '<a:noFill/>'
    
    def test_to_drawingml_custom_element(self):
        """Test DrawingML conversion with custom element name."""
        parser = ColorParser()
        color = ColorInfo(255, 0, 0, 1.0, ColorFormat.RGB, "red")
        
        xml = parser.to_drawingml(color, "schemeClr")
        assert xml == '<a:schemeClr val="FF0000"/>'
    
    def test_create_solid_fill(self):
        """Test solid fill element creation."""
        parser = ColorParser()
        color = ColorInfo(255, 0, 0, 1.0, ColorFormat.RGB, "red")
        
        xml = parser.create_solid_fill(color)
        assert xml == '<a:solidFill><a:srgbClr val="FF0000"/></a:solidFill>'
        
        # Transparent color
        color = ColorInfo(0, 0, 0, 0.0, ColorFormat.TRANSPARENT, "transparent")
        xml = parser.create_solid_fill(color)
        assert xml == '<a:noFill/>'
    
    def test_batch_parse(self):
        """Test batch color parsing."""
        parser = ColorParser()
        
        color_dict = {
            'primary': '#FF0000',
            'secondary': 'blue',
            'accent': 'rgba(128, 64, 32, 0.8)',
            'invalid': 'not-a-color'
        }
        
        result = parser.batch_parse(color_dict)
        
        assert result['primary'].hex == 'FF0000'
        assert result['secondary'].hex == '0000FF'
        assert result['accent'].red == 128
        assert result['accent'].alpha == 0.8
        assert result['invalid'] is None
    
    def test_extract_colors_from_gradient_stops(self):
        """Test extracting colors from gradient stops."""
        parser = ColorParser()
        
        stops = [
            (0.0, '#FF0000', 1.0),
            (0.5, 'rgba(0, 255, 0, 0.8)', 1.0),
            (1.0, 'blue', 0.5)
        ]
        
        colors = parser.extract_colors_from_gradient_stops(stops)
        
        assert len(colors) == 3
        assert colors[0].hex == 'FF0000'
        assert colors[0].alpha == 1.0
        assert colors[1].hex == '00FF00'
        assert colors[1].alpha == 0.8
        assert colors[2].hex == '0000FF'
        assert colors[2].alpha == 0.5  # Applied stop opacity
    
    def test_get_contrast_color(self):
        """Test getting contrasting colors."""
        parser = ColorParser()
        
        # Dark background should get light text
        dark_bg = ColorInfo(0, 0, 0, 1.0, ColorFormat.RGB, "black")
        contrast = parser.get_contrast_color(dark_bg)
        assert contrast.hex == 'FFFFFF'  # White
        
        # Light background should get dark text
        light_bg = ColorInfo(255, 255, 255, 1.0, ColorFormat.RGB, "white")
        contrast = parser.get_contrast_color(light_bg)
        assert contrast.hex == '000000'  # Black
        
        # Custom light and dark colors
        custom_light = ColorInfo(255, 255, 0, 1.0, ColorFormat.RGB, "yellow")
        custom_dark = ColorInfo(0, 0, 128, 1.0, ColorFormat.RGB, "navy")
        contrast = parser.get_contrast_color(dark_bg, custom_light, custom_dark)
        assert contrast.hex == 'FFFF00'  # Yellow (better contrast on black)
    
    def test_debug_color_info(self):
        """Test debug color information."""
        parser = ColorParser()
        
        debug = parser.debug_color_info("#FF8040")
        
        assert debug['valid'] is True
        assert debug['input'] == "#FF8040"
        assert debug['format'] == "hex"
        assert debug['rgb'] == (255, 128, 64)
        assert debug['rgba'] == (255, 128, 64, 1.0)
        assert debug['hex'] == "#FF8040"
        assert debug['hex_alpha'] == "#FF8040FF"
        assert 'hsl' in debug
        assert 'luminance' in debug
        assert 'is_dark' in debug
        assert 'drawingml' in debug
        assert 'solid_fill' in debug
        
        # Invalid color
        debug = parser.debug_color_info("invalid")
        assert debug['valid'] is False
        assert debug['input'] == "invalid"


class TestColorSpaceConversions:
    """Test color space conversion functions."""
    
    def test_rgb_to_hsl_primary_colors(self):
        """Test RGB to HSL conversion for primary colors."""
        # Red
        h, s, l = rgb_to_hsl(255, 0, 0)
        assert abs(h - 0) < 1
        assert s == 100
        assert l == 50
        
        # Green
        h, s, l = rgb_to_hsl(0, 255, 0)
        assert abs(h - 120) < 1
        assert s == 100
        assert l == 50
        
        # Blue
        h, s, l = rgb_to_hsl(0, 0, 255)
        assert abs(h - 240) < 1
        assert s == 100
        assert l == 50
    
    def test_rgb_to_hsl_grayscale(self):
        """Test RGB to HSL conversion for grayscale colors."""
        # Black
        h, s, l = rgb_to_hsl(0, 0, 0)
        assert s == 0
        assert l == 0
        
        # White
        h, s, l = rgb_to_hsl(255, 255, 255)
        assert s == 0
        assert l == 100
        
        # Gray
        h, s, l = rgb_to_hsl(128, 128, 128)
        assert s == 0
        assert abs(l - 50.2) < 1  # Approximately 50%
    
    def test_hsl_to_rgb_primary_colors(self):
        """Test HSL to RGB conversion for primary colors."""
        # Red
        r, g, b = hsl_to_rgb(0, 100, 50)
        assert r == 255
        assert g == 0
        assert b == 0
        
        # Green
        r, g, b = hsl_to_rgb(120, 100, 50)
        assert r == 0
        assert g == 255
        assert b == 0
        
        # Blue
        r, g, b = hsl_to_rgb(240, 100, 50)
        assert r == 0
        assert g == 0
        assert b == 255
    
    def test_hsl_to_rgb_grayscale(self):
        """Test HSL to RGB conversion for grayscale colors."""
        # Black
        r, g, b = hsl_to_rgb(0, 0, 0)
        assert r == 0
        assert g == 0
        assert b == 0
        
        # White
        r, g, b = hsl_to_rgb(0, 0, 100)
        assert r == 255
        assert g == 255
        assert b == 255
        
        # Gray
        r, g, b = hsl_to_rgb(0, 0, 50)
        assert abs(r - 128) <= 1
        assert abs(g - 128) <= 1
        assert abs(b - 128) <= 1
    
    def test_roundtrip_conversion(self):
        """Test roundtrip RGB->HSL->RGB conversion."""
        test_colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green  
            (0, 0, 255),    # Blue
            (255, 255, 255), # White
            (0, 0, 0),      # Black
            (128, 64, 192), # Purple-ish
            (200, 150, 100) # Brown-ish
        ]
        
        for r_orig, g_orig, b_orig in test_colors:
            h, s, l = rgb_to_hsl(r_orig, g_orig, b_orig)
            r_new, g_new, b_new = hsl_to_rgb(h, s, l)
            
            # Allow small rounding errors
            assert abs(r_orig - r_new) <= 1
            assert abs(g_orig - g_new) <= 1
            assert abs(b_orig - b_new) <= 1
    
    def test_hsl_edge_cases(self):
        """Test HSL edge cases and boundary conditions."""
        # Hue > 360 should wrap
        r, g, b = hsl_to_rgb(480, 100, 50)  # Same as 120 degrees
        assert r == 0
        assert g == 255
        assert b == 0
        
        # Negative hue should wrap  
        r, g, b = hsl_to_rgb(-120, 100, 50)  # Same as 240 degrees
        assert r == 0
        assert g == 0
        assert b == 255
        
        # Values outside 0-100 range should be clamped
        r, g, b = hsl_to_rgb(0, 150, 50)  # Saturation > 100
        assert 0 <= r <= 255
        assert 0 <= g <= 255
        assert 0 <= b <= 255


class TestConvenienceFunctions:
    """Test global convenience functions."""
    
    def test_parse_color_function(self):
        """Test global parse_color function."""
        color = parse_color("#FF0000")
        assert color.hex == "FF0000"
        assert color.format == ColorFormat.HEX
    
    def test_to_drawingml_function(self):
        """Test global to_drawingml function."""
        xml = to_drawingml("#FF0000")
        assert xml == '<a:srgbClr val="FF0000"/>'
        
        # Invalid color should fallback to black
        xml = to_drawingml("invalid")
        assert xml == '<a:srgbClr val="000000"/>'
    
    def test_create_solid_fill_function(self):
        """Test global create_solid_fill function."""
        xml = create_solid_fill("#FF0000")
        assert xml == '<a:solidFill><a:srgbClr val="FF0000"/></a:solidFill>'
        
        # Invalid color should fallback to no fill
        xml = create_solid_fill("invalid")
        assert xml == '<a:noFill/>'


class TestNamedColorsDatabase:
    """Test named colors database."""
    
    def test_named_colors_coverage(self):
        """Test that common named colors are included."""
        assert 'red' in NAMED_COLORS
        assert 'green' in NAMED_COLORS
        assert 'blue' in NAMED_COLORS
        assert 'black' in NAMED_COLORS
        assert 'white' in NAMED_COLORS
        assert 'yellow' in NAMED_COLORS
        assert 'cyan' in NAMED_COLORS
        assert 'magenta' in NAMED_COLORS
        
        # Extended colors
        assert 'lightblue' in NAMED_COLORS
        assert 'darkred' in NAMED_COLORS
        assert 'forestgreen' in NAMED_COLORS
    
    def test_named_colors_format(self):
        """Test that named colors are in correct hex format."""
        for name, hex_val in NAMED_COLORS.items():
            assert hex_val.startswith('#')
            assert len(hex_val) == 7  # #RRGGBB format
            # Should be valid hex
            try:
                int(hex_val[1:], 16)
            except ValueError:
                pytest.fail(f"Invalid hex color for '{name}': {hex_val}")
    
    def test_color_variations(self):
        """Test color name variations (gray vs grey)."""
        assert 'gray' in NAMED_COLORS
        assert 'grey' in NAMED_COLORS
        assert NAMED_COLORS['gray'] == NAMED_COLORS['grey']
        
        assert 'darkgray' in NAMED_COLORS
        assert 'darkgrey' in NAMED_COLORS
        assert NAMED_COLORS['darkgray'] == NAMED_COLORS['darkgrey']


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling."""
    
    def test_whitespace_handling(self):
        """Test handling of whitespace in color strings."""
        parser = ColorParser()
        
        color = parser.parse("  #FF0000  ")
        assert color.hex == "FF0000"
        
        color = parser.parse(" rgb( 255 , 0 , 0 ) ")
        assert color.red == 255
        assert color.green == 0
        assert color.blue == 0
    
    def test_case_insensitive_parsing(self):
        """Test case insensitive color parsing."""
        parser = ColorParser()
        
        # Hex colors
        color1 = parser.parse("#FF0000")
        color2 = parser.parse("#ff0000")
        assert color1.hex == color2.hex
        
        # Function colors
        color1 = parser.parse("RGB(255, 0, 0)")
        color2 = parser.parse("rgb(255, 0, 0)")
        assert color1.red == color2.red
        
        # Named colors
        color1 = parser.parse("RED")
        color2 = parser.parse("red")
        assert color1.hex == color2.hex
    
    def test_unusual_but_valid_formats(self):
        """Test unusual but valid color formats."""
        parser = ColorParser()
        
        # RGB with mixed integer/float values
        color = parser.parse("rgb(255.0, 0, 0)")
        assert color.red == 255
        
        # HSL with various units
        color = parser.parse("hsl(0deg, 100%, 50%)")
        assert color is not None
        assert color.red == 255
        assert color.green == 0
        assert color.blue == 0
    
    def test_error_recovery(self):
        """Test parser error recovery."""
        parser = ColorParser()
        
        # Malformed but partially parseable
        color = parser.parse("rgb(255, 0)")  # Missing blue component
        assert color is None
        
        # Wrong number of parameters
        color = parser.parse("rgb(255, 0, 0, 0, 0)")
        assert color is None
        
        # Invalid alpha values should be handled gracefully
        color = parser.parse("rgba(255, 0, 0, invalid)")
        assert color is None