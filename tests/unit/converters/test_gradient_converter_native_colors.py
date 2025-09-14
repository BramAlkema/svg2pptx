#!/usr/bin/env python3
"""
Comprehensive test suite for gradient converter using native color API.

Tests the refactored gradient converter that uses the centralized color system
instead of external dependencies like spectra. Covers:
- Linear gradients with native color parsing
- Radial gradients with LAB space interpolation
- Gradient stops using native color system
- SVG gradient stop parsing
- Named CSS colors support
- Error handling for color parsing failures
- Performance optimizations
"""

import pytest
import math
from pathlib import Path
import sys
from lxml import etree as ET
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.converters.gradients import GradientConverter
from src.converters.base import ConversionContext
from src.colors import ColorParser, ColorInfo, ColorFormat


@pytest.mark.unit
@pytest.mark.converter
class TestGradientConverterNativeColors:
    """Test suite for gradient converter with native color system integration"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = GradientConverter()
        self.context = Mock(spec=ConversionContext)

        # Create mock SVG root with defs section
        self.svg_root = ET.Element("svg", nsmap={'svg': 'http://www.w3.org/2000/svg'})
        self.defs = ET.SubElement(self.svg_root, "defs")
        self.context.svg_root = self.svg_root

    def assert_color_in_range(self, color_hex: str):
        """Assert color hex is valid format"""
        assert isinstance(color_hex, str)
        assert len(color_hex) == 6  # RRGGBB format
        # Verify it's valid hex
        int(color_hex, 16)

    def test_initialization_with_native_color_system(self):
        """Test converter initialization includes color parser"""
        converter = GradientConverter()
        assert hasattr(converter, 'color_parser')
        assert isinstance(converter.color_parser, ColorParser)
        assert hasattr(converter, 'gradients')

    def test_native_hex_color_parsing(self):
        """Test native hex color parsing in gradient stops"""
        # Create gradient with hex colors
        gradient = ET.fromstring('''
        <linearGradient xmlns="http://www.w3.org/2000/svg" id="grad1">
            <stop offset="0%" stop-color="#FF0000"/>
            <stop offset="50%" stop-color="#00FF00"/>
            <stop offset="100%" stop-color="#0000FF"/>
        </linearGradient>
        ''')

        stops = self.converter._get_gradient_stops(gradient)
        assert len(stops) == 3

        # Check stop colors are properly parsed
        assert stops[0][1] == "FF0000"  # Red
        assert stops[1][1] == "00FF00"  # Green
        assert stops[2][1] == "0000FF"  # Blue

    def test_native_rgb_color_parsing(self):
        """Test native RGB color parsing in gradient stops"""
        gradient = ET.fromstring('''
        <linearGradient xmlns="http://www.w3.org/2000/svg" id="grad1">
            <stop offset="0%" stop-color="rgb(255, 0, 0)"/>
            <stop offset="100%" stop-color="rgb(0, 0, 255)"/>
        </linearGradient>
        ''')

        stops = self.converter._get_gradient_stops(gradient)
        assert len(stops) == 2

        # Check RGB colors are properly converted to hex
        assert stops[0][1] == "FF0000"  # Red
        assert stops[1][1] == "0000FF"  # Blue

    def test_native_hsl_color_parsing(self):
        """Test native HSL color parsing without spectra dependency"""
        gradient = ET.fromstring('''
        <linearGradient xmlns="http://www.w3.org/2000/svg" id="grad1">
            <stop offset="0%" stop-color="hsl(0, 100%, 50%)"/>
            <stop offset="100%" stop-color="hsl(240, 100%, 50%)"/>
        </linearGradient>
        ''')

        stops = self.converter._get_gradient_stops(gradient)
        assert len(stops) == 2

        # Check HSL colors are converted to hex
        self.assert_color_in_range(stops[0][1])  # Should be valid hex
        self.assert_color_in_range(stops[1][1])  # Should be valid hex

    def test_named_css_colors_support(self):
        """Test support for named CSS colors without external dependencies"""
        gradient = ET.fromstring('''
        <linearGradient xmlns="http://www.w3.org/2000/svg" id="grad1">
            <stop offset="0%" stop-color="red"/>
            <stop offset="25%" stop-color="green"/>
            <stop offset="50%" stop-color="blue"/>
            <stop offset="75%" stop-color="white"/>
            <stop offset="100%" stop-color="black"/>
        </linearGradient>
        ''')

        stops = self.converter._get_gradient_stops(gradient)
        assert len(stops) == 5

        # Verify named colors are converted correctly
        for position, color, opacity in stops:
            self.assert_color_in_range(color)
            assert 0.0 <= position <= 1.0
            assert 0.0 <= opacity <= 1.0

    def test_linear_gradient_with_lab_interpolation(self):
        """Test linear gradient conversion using LAB space for smoother transitions"""
        gradient = ET.fromstring('''
        <linearGradient xmlns="http://www.w3.org/2000/svg" id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#FF0000"/>
            <stop offset="100%" stop-color="#0000FF"/>
        </linearGradient>
        ''')
        self.defs.append(gradient)

        result = self.converter.convert(gradient, self.context)

        # Verify DrawingML structure
        assert '<a:gradFill' in result
        assert '<a:gsLst>' in result
        assert '<a:lin ang=' in result
        assert 'FF0000' in result  # Red color
        assert '0000FF' in result  # Blue color

    def test_radial_gradient_with_native_colors(self):
        """Test radial gradient conversion with native color parsing"""
        gradient = ET.fromstring('''
        <radialGradient xmlns="http://www.w3.org/2000/svg" id="grad1" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="white"/>
            <stop offset="100%" stop-color="black"/>
        </radialGradient>
        ''')
        self.defs.append(gradient)

        result = self.converter.convert(gradient, self.context)

        # Verify radial gradient structure
        assert '<a:gradFill' in result
        assert '<a:gsLst>' in result
        assert '<a:path path="circle">' in result
        assert 'FFFFFF' in result  # White
        assert '000000' in result  # Black

    def test_gradient_stops_with_opacity(self):
        """Test gradient stops with alpha/opacity support"""
        gradient = ET.fromstring('''
        <linearGradient xmlns="http://www.w3.org/2000/svg" id="grad1">
            <stop offset="0%" stop-color="red" stop-opacity="1.0"/>
            <stop offset="50%" stop-color="green" stop-opacity="0.5"/>
            <stop offset="100%" stop-color="blue" stop-opacity="0.0"/>
        </linearGradient>
        ''')

        stops = self.converter._get_gradient_stops(gradient)
        assert len(stops) == 3

        # Check opacity values
        assert stops[0][2] == 1.0  # Full opacity
        assert stops[1][2] == 0.5  # Half opacity
        assert stops[2][2] == 0.0  # Transparent

    def test_gradient_stops_with_style_attribute(self):
        """Test gradient stops using style attribute for colors"""
        gradient = ET.fromstring('''
        <linearGradient xmlns="http://www.w3.org/2000/svg" id="grad1">
            <stop offset="0%" style="stop-color: #FF0000; stop-opacity: 0.8"/>
            <stop offset="100%" style="stop-color: rgb(0, 255, 0); stop-opacity: 0.6"/>
        </linearGradient>
        ''')

        stops = self.converter._get_gradient_stops(gradient)
        assert len(stops) == 2

        # Check style-based color parsing
        assert stops[0][1] == "FF0000"  # Red from style
        assert stops[0][2] == 0.8       # Opacity from style
        assert stops[1][1] == "00FF00"  # Green from style
        assert stops[1][2] == 0.6       # Opacity from style

    def test_url_reference_resolution(self):
        """Test gradient URL reference resolution (url(#id))"""
        gradient = ET.fromstring('''
        <linearGradient xmlns="http://www.w3.org/2000/svg" id="myGrad">
            <stop offset="0%" stop-color="red"/>
            <stop offset="100%" stop-color="blue"/>
        </linearGradient>
        ''')
        self.defs.append(gradient)

        # Test URL resolution
        result = self.converter.get_fill_from_url('url(#myGrad)', self.context)

        assert result  # Should return DrawingML
        assert '<a:gradFill' in result
        assert 'FF0000' in result  # Red
        assert '0000FF' in result  # Blue

    def test_invalid_url_reference_handling(self):
        """Test handling of invalid URL references"""
        # Test malformed URL - should return empty string
        result = self.converter.get_fill_from_url('invalid_url', self.context)
        assert result == ""

        # Test non-existent gradient ID - should return fallback gradient
        result = self.converter.get_fill_from_url('url(#nonexistent)', self.context)
        assert '<a:solidFill><a:srgbClr val="808080"/></a:solidFill>' in result

    def test_color_parsing_error_handling(self):
        """Test robust error handling for invalid colors"""
        gradient = ET.fromstring('''
        <linearGradient xmlns="http://www.w3.org/2000/svg" id="grad1">
            <stop offset="0%" stop-color="invalid_color"/>
            <stop offset="50%" stop-color=""/>
            <stop offset="100%" stop-color="red"/>
        </linearGradient>
        ''')

        stops = self.converter._get_gradient_stops(gradient)

        # Should handle invalid colors gracefully
        assert len(stops) >= 1  # At least the valid 'red' stop should be processed

        # Find the valid red stop
        red_stop = next((stop for stop in stops if stop[1] == "FF0000"), None)
        assert red_stop is not None

    def test_gradient_transform_parsing(self):
        """Test gradient transform attribute handling"""
        gradient = ET.fromstring('''
        <linearGradient xmlns="http://www.w3.org/2000/svg" id="grad1"
                        x1="0%" y1="0%" x2="100%" y2="0%"
                        gradientTransform="matrix(1.5, 0, 0, 1.5, 10, 20)">
            <stop offset="0%" stop-color="red"/>
            <stop offset="100%" stop-color="blue"/>
        </linearGradient>
        ''')

        result = self.converter.convert(gradient, self.context)

        # Should not crash with transform attribute
        assert '<a:gradFill' in result
        assert result != ""

    def test_per_mille_precision_positioning(self):
        """Test per-mille precision for gradient stop positioning"""
        # Test fractional positions
        assert self.converter._to_per_mille_precision(0.0) == "0"
        assert self.converter._to_per_mille_precision(0.5) == "500"
        assert self.converter._to_per_mille_precision(1.0) == "1000"
        assert self.converter._to_per_mille_precision(0.333) == "333"
        assert self.converter._to_per_mille_precision(0.6667) == "666.7"

    def test_gradient_caching_system(self):
        """Test gradient caching for performance optimization"""
        gradient = ET.fromstring('''
        <linearGradient xmlns="http://www.w3.org/2000/svg" id="grad1">
            <stop offset="0%" stop-color="red"/>
            <stop offset="100%" stop-color="blue"/>
        </linearGradient>
        ''')

        # First conversion should create cache entry
        result1 = self.converter.convert(gradient, self.context)

        # Second conversion should use cached result
        result2 = self.converter.convert(gradient, self.context)

        assert result1 == result2
        assert len(self.converter.gradients) > 0  # Cache should have entry

    def test_complex_gradient_with_multiple_stops(self):
        """Test complex gradients with multiple color stops"""
        gradient = ET.fromstring('''
        <linearGradient xmlns="http://www.w3.org/2000/svg" id="complex">
            <stop offset="0%" stop-color="#FF0000"/>
            <stop offset="20%" stop-color="#FF8000"/>
            <stop offset="40%" stop-color="#FFFF00"/>
            <stop offset="60%" stop-color="#80FF00"/>
            <stop offset="80%" stop-color="#00FF00"/>
            <stop offset="100%" stop-color="#0000FF"/>
        </linearGradient>
        ''')

        result = self.converter.convert(gradient, self.context)
        stops = self.converter._get_gradient_stops(gradient)

        assert len(stops) == 6  # All stops should be processed
        assert '<a:gradFill' in result

        # Verify all colors are present in result
        expected_colors = ["FF0000", "FF8000", "FFFF00", "80FF00", "00FF00", "0000FF"]
        for color in expected_colors:
            assert color in result

    def test_mesh_gradient_without_spectra(self):
        """Test mesh gradient conversion without spectra dependency"""
        mesh = ET.fromstring('''
        <meshgradient xmlns="http://www.w3.org/2000/svg" id="mesh1">
            <meshrow>
                <meshpatch>
                    <stop stop-color="red"/>
                    <stop stop-color="green"/>
                    <stop stop-color="blue"/>
                    <stop stop-color="yellow"/>
                </meshpatch>
            </meshrow>
        </meshgradient>
        ''')

        result = self.converter.convert(mesh, self.context)

        # Should not crash and return valid DrawingML
        assert result != ""
        # Should fallback to simpler gradient representation
        assert any(xml_tag in result for xml_tag in ['<a:gradFill', '<a:solidFill'])

    def test_pattern_fill_conversion(self):
        """Test pattern fill conversion with native colors"""
        pattern = ET.fromstring('''
        <pattern xmlns="http://www.w3.org/2000/svg" id="pattern1" width="20" height="20">
            <rect width="10" height="10" fill="red"/>
            <rect x="10" y="10" width="10" height="10" fill="blue"/>
        </pattern>
        ''')

        result = self.converter.convert(pattern, self.context)

        # Should convert to some PowerPoint fill format
        assert result != ""
        assert any(fill_type in result for fill_type in ['<a:solidFill', '<a:pattFill'])

    def test_color_interpolation_accuracy(self):
        """Test color interpolation accuracy with RGB calculations"""
        # Test interpolation method directly
        start_color = (255, 0, 0)    # Red
        end_color = (0, 0, 255)      # Blue
        mid_color = self.converter._interpolate_gradient_colors(
            0.0, start_color, 1.0, end_color, 0.5
        )

        # Midpoint should be purple-ish (LAB interpolation produces different results than RGB)
        r, g, b = mid_color
        # LAB-based interpolation creates perceptually uniform gradients
        assert 120 <= r <= 220  # LAB interpolation between red and blue
        assert 0 <= g <= 50     # Minimal green in LAB space red-blue mix
        assert 120 <= b <= 220  # LAB interpolation produces different blue values

    def test_hsl_to_rgb_conversion_precision(self):
        """Test HSL to RGB conversion without spectra"""
        # Test precise HSL conversion
        r, g, b = self.converter._hsl_to_rgb_precise(0, 100, 50)    # Pure red
        assert abs(r - 255) <= 1
        assert abs(g - 0) <= 1
        assert abs(b - 0) <= 1

        r, g, b = self.converter._hsl_to_rgb_precise(240, 100, 50)  # Pure blue
        assert abs(r - 0) <= 1
        assert abs(g - 0) <= 1
        assert abs(b - 255) <= 1

    def test_gradient_angle_calculation(self):
        """Test gradient angle calculation for DrawingML"""
        gradient = ET.fromstring('''
        <linearGradient xmlns="http://www.w3.org/2000/svg" id="grad1"
                        x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="red"/>
            <stop offset="100%" stop-color="blue"/>
        </linearGradient>
        ''')

        result = self.converter.convert(gradient, self.context)

        # Should calculate angle for diagonal gradient
        assert '<a:lin ang=' in result
        # Extract angle value - should be reasonable for diagonal
        import re
        angle_match = re.search(r'<a:lin ang="(\d+)"', result)
        if angle_match:
            angle = int(angle_match.group(1))
            # Angle should be within valid range for DrawingML (0-21600000)
            assert 0 <= angle <= 21600000

    def test_empty_gradient_handling(self):
        """Test handling of gradients with no stops"""
        gradient = ET.fromstring('''
        <linearGradient xmlns="http://www.w3.org/2000/svg" id="empty">
        </linearGradient>
        ''')

        result = self.converter.convert(gradient, self.context)
        # Should return a fallback gradient instead of empty string (improved error handling)
        assert "<a:gradFill" in result and "000000" in result and "FFFFFF" in result

    def test_single_stop_gradient_handling(self):
        """Test handling of gradients with only one stop"""
        gradient = ET.fromstring('''
        <linearGradient xmlns="http://www.w3.org/2000/svg" id="single">
            <stop offset="50%" stop-color="red"/>
        </linearGradient>
        ''')

        stops = self.converter._get_gradient_stops(gradient)
        # Improved behavior: automatically creates complementary stop for single-stop gradients
        assert len(stops) >= 1  # Should have at least the original stop
        assert stops[0][1] == "FF0000" or stops[1][1] == "FF0000"  # Should preserve the original red color

    @pytest.mark.performance
    def test_gradient_conversion_performance(self):
        """Test gradient conversion performance with large number of stops"""
        import time

        # Create gradient with many stops
        gradient_xml = '''<linearGradient xmlns="http://www.w3.org/2000/svg" id="perf">'''
        for i in range(20):  # 20 stops
            offset = i * 5  # 0%, 5%, 10%, ... 95%
            hue = i * 18    # Vary hue across spectrum
            gradient_xml += f'<stop offset="{offset}%" stop-color="hsl({hue}, 100%, 50%)"/>'
        gradient_xml += '</linearGradient>'

        gradient = ET.fromstring(gradient_xml)

        start_time = time.time()
        result = self.converter.convert(gradient, self.context)
        end_time = time.time()

        # Should convert in reasonable time (< 1 second)
        conversion_time = end_time - start_time
        assert conversion_time < 1.0
        assert result != ""
        assert '<a:gradFill' in result


if __name__ == "__main__":
    # Run with: python -m pytest tests/unit/converters/test_gradient_converter_native_colors.py -v
    pytest.main([__file__, "-v"])