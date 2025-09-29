#!/usr/bin/env python3
"""
Comprehensive error handling and malformed input tests.

This module tests how the system handles various error conditions and malformed
inputs to ensure robustness and graceful degradation.
"""

import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET
from pathlib import Path
import sys

# Import centralized fixtures
from tests.fixtures.common import *
from tests.fixtures.mock_objects import *
from tests.fixtures.svg_content import *

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.converters.shapes import RectangleConverter, CircleConverter, PolygonConverter, LineConverter
from src.converters.text import TextConverter
from src.converters.base import ConversionContext


@pytest.mark.unit
@pytest.mark.validation
class TestMalformedSVGHandling:
    """Test handling of malformed SVG inputs."""

    def test_invalid_xml_structure(self):
        """Test handling of invalid XML structure."""
        converters = [RectangleConverter(), CircleConverter(), TextConverter()]

        # Test with various malformed XML
        malformed_cases = [
            '<rect>',  # Unclosed tag
            '<rect x="10" y="abc"/>',  # Invalid attribute value
            '<rect x="10" y="20" width="-50"/>',  # Negative dimension
            '<rect x="" y="20"/>',  # Empty attribute
        ]

        for xml_str in malformed_cases:
            try:
                element = ET.fromstring(xml_str + '</rect>' if not xml_str.endswith('>') else xml_str)
            except ET.ParseError:
                # Should handle XML parse errors gracefully
                continue

            context = Mock(spec=ConversionContext)
            context.coordinate_system = Mock()
            context.coordinate_system.svg_to_emu.return_value = (0, 0)
            context.coordinate_system.svg_length_to_emu.return_value = 0
            context.get_next_shape_id.return_value = 1001

            for converter in converters:
                if converter.can_convert(element):
                    # Mock helper methods for text converter
                    if isinstance(converter, TextConverter):
                        converter._extract_text_content = Mock(return_value='Test')
                        converter._get_font_family = Mock(return_value='Arial')
                        converter._get_font_size = Mock(return_value=12)
                        converter._get_font_weight = Mock(return_value='normal')
                        converter._get_font_style = Mock(return_value='normal')
                        converter._get_text_anchor = Mock(return_value='l')
                        converter._get_text_decoration = Mock(return_value='')
                        converter._get_fill_color = Mock(return_value='<fill/>')
                        converter.to_emu = Mock(return_value=91440)

                    # Should handle malformed input gracefully
                    try:
                        result = converter.convert(element, context)
                        assert isinstance(result, str)  # Should return some string result
                    except Exception as e:
                        # If an exception is raised, it should be a controlled one
                        assert not isinstance(e, (KeyError, AttributeError)), f"Unexpected error type: {type(e)}"

    def test_missing_required_attributes(self):
        """Test handling when required attributes are missing."""
        rect_converter = RectangleConverter()
        circle_converter = CircleConverter()

        # Rectangle without width/height
        rect_element = ET.fromstring('<rect x="10" y="10"/>')  # Missing width, height

        # Circle without radius
        circle_element = ET.fromstring('<circle cx="50" cy="50"/>')  # Missing r

        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.return_value = (9144, 9144)
        context.coordinate_system.svg_length_to_emu.return_value = 0
        context.get_next_shape_id.return_value = 1001

        # Mock style methods
        rect_converter.generate_fill = Mock(return_value='<fill/>')
        rect_converter.generate_stroke = Mock(return_value='<stroke/>')
        circle_converter.generate_fill = Mock(return_value='<fill/>')
        circle_converter.generate_stroke = Mock(return_value='<stroke/>')

        # Should handle missing attributes by using defaults
        rect_result = rect_converter.convert(rect_element, context)
        circle_result = circle_converter.convert(circle_element, context)

        assert isinstance(rect_result, str)
        assert isinstance(circle_result, str)
        # Should contain default dimensions (0)
        assert 'cx="0"' in rect_result or 'cy="0"' in rect_result
        assert 'cx="0"' in circle_result or 'cy="0"' in circle_result

    def test_extreme_coordinate_values(self):
        """Test handling of extreme coordinate values."""
        rect_converter = RectangleConverter()

        extreme_cases = [
            ('<rect x="999999999" y="999999999" width="100" height="50"/>', 'Very large coordinates'),
            ('<rect x="-999999999" y="-999999999" width="100" height="50"/>', 'Very negative coordinates'),
            ('<rect x="0" y="0" width="999999999" height="999999999"/>', 'Extreme dimensions'),
            ('<rect x="0.000000001" y="0.000000001" width="0.1" height="0.1"/>', 'Very small values'),
        ]

        for xml_str, description in extreme_cases:
            element = ET.fromstring(xml_str)

            context = Mock(spec=ConversionContext)
            context.coordinate_system = Mock()
            context.coordinate_system.svg_to_emu.side_effect = lambda x, y: (int(x * 914.4), int(y * 914.4))
            context.coordinate_system.svg_length_to_emu.side_effect = lambda val, direction: int(val * 914.4)
            context.get_next_shape_id.return_value = 1001

            rect_converter.generate_fill = Mock(return_value='<fill/>')
            rect_converter.generate_stroke = Mock(return_value='<stroke/>')

            # Should handle extreme values without crashing
            result = rect_converter.convert(element, context)
            assert isinstance(result, str), f"Failed for {description}"
            assert len(result) > 0, f"Empty result for {description}"

    def test_invalid_color_values(self):
        """Test handling of invalid color values."""
        rect_converter = RectangleConverter()

        invalid_color_cases = [
            '<rect x="0" y="0" width="100" height="50" fill="invalid_color"/>',
            '<rect x="0" y="0" width="100" height="50" fill="#gggggg"/>',  # Invalid hex
            '<rect x="0" y="0" width="100" height="50" stroke="rgb(300,300,300)"/>',  # Out of range
            '<rect x="0" y="0" width="100" height="50" fill="rgba(255,0,0,2.0)"/>',  # Alpha > 1
        ]

        for xml_str in invalid_color_cases:
            element = ET.fromstring(xml_str)

            context = Mock(spec=ConversionContext)
            context.coordinate_system = Mock()
            context.coordinate_system.svg_to_emu.return_value = (0, 0)
            context.coordinate_system.svg_length_to_emu.return_value = 91440
            context.get_next_shape_id.return_value = 1001

            # Mock style methods to handle invalid colors
            rect_converter.generate_fill = Mock(return_value='<fill/>')
            rect_converter.generate_stroke = Mock(return_value='<stroke/>')

            # Should handle invalid colors gracefully
            result = rect_converter.convert(element, context)
            assert isinstance(result, str)
            assert '<p:sp>' in result


@pytest.mark.unit
@pytest.mark.validation
class TestPolygonMalformedInputs:
    """Test polygon converter with malformed point data."""

    def test_invalid_points_format(self):
        """Test polygon with various invalid points formats."""
        converter = PolygonConverter()

        invalid_points_cases = [
            ('', 'Empty points'),
            ('10', 'Single coordinate'),
            ('10,20,30', 'Odd number of coordinates'),
            ('abc,def', 'Non-numeric coordinates'),
            ('10,20 ,30', 'Missing coordinate'),
            ('10,20 30,', 'Trailing comma'),
            ('10,20 NaN,30', 'NaN values'),
            ('10,20 Infinity,30', 'Infinity values'),
            ('10,,20 30,40', 'Double comma'),
        ]

        for points_str, description in invalid_points_cases:
            element = ET.fromstring(f'<polygon points="{points_str}"/>')

            context = Mock(spec=ConversionContext)
            context.coordinate_system = Mock()
            context.coordinate_system.svg_to_emu.return_value = (0, 0)
            context.coordinate_system.svg_length_to_emu.side_effect = [91440, 91440]
            context.get_next_shape_id.return_value = 2001

            converter.generate_fill = Mock(return_value='<fill/>')
            converter.generate_stroke = Mock(return_value='<stroke/>')

            # Should handle invalid points gracefully
            result = converter.convert(element, context)
            assert isinstance(result, str), f"Failed for {description}"

            if not points_str or len(points_str.split()) < 2:
                # Should return comment for insufficient data
                assert ('Empty' in result or 'Insufficient' in result), f"Should handle {description}"
            else:
                # Should attempt conversion even with some invalid points
                assert len(result) > 0

    def test_polygon_edge_cases(self):
        """Test polygon edge cases."""
        converter = PolygonConverter()

        edge_cases = [
            ('0,0 0,0 0,0', 'All same point'),
            ('0,0 1000000,1000000', 'Extreme coordinate range'),
            ('0.1,0.1 0.2,0.2', 'Very small coordinates'),
            (' 10,20  30,40  50,60 ', 'Extra whitespace'),
            ('10,20;30,40', 'Semicolon separator'),
        ]

        for points_str, description in edge_cases:
            element = ET.fromstring(f'<polygon points="{points_str}"/>')

            context = Mock(spec=ConversionContext)
            context.coordinate_system = Mock()
            context.coordinate_system.svg_to_emu.return_value = (0, 0)
            context.coordinate_system.svg_length_to_emu.side_effect = [91440, 91440]
            context.get_next_shape_id.return_value = 2002

            converter.generate_fill = Mock(return_value='<fill/>')
            converter.generate_stroke = Mock(return_value='<stroke/>')

            result = converter.convert(element, context)
            assert isinstance(result, str), f"Failed for {description}"


@pytest.mark.unit
@pytest.mark.validation
class TestLineConverterErrorHandling:
    """Test line converter error handling."""

    def test_invalid_line_coordinates(self):
        """Test line with invalid coordinate values."""
        converter = LineConverter()

        invalid_cases = [
            ('<line x1="abc" y1="def" x2="ghi" y2="jkl"/>', 'All invalid coordinates'),
            ('<line x1="" y1="" x2="" y2=""/>', 'Empty coordinates'),
            ('<line x1="10" y1="20"/>', 'Missing x2, y2'),
            ('<line x1="10" y1="20" x2="10" y2="20"/>', 'Zero-length line'),
            ('<line x1="NaN" y1="20" x2="30" y2="40"/>', 'NaN coordinate'),
        ]

        for xml_str, description in invalid_cases:
            element = ET.fromstring(xml_str)

            context = Mock(spec=ConversionContext)
            context.coordinate_system = Mock()
            context.coordinate_system.svg_to_emu.return_value = (0, 0)
            context.coordinate_system.svg_length_to_emu.side_effect = [1, 1]
            context.get_next_shape_id.return_value = 3001

            converter.generate_stroke = Mock(return_value='<stroke/>')

            # Mock parse_length to return 0 for invalid inputs
            converter.parse_length = Mock(side_effect=lambda x: 0.0 if not x.replace('.', '').replace('-', '').isdigit() else float(x))

            result = converter.convert(element, context)
            assert isinstance(result, str), f"Failed for {description}"

            if 'Zero-length' in description:
                assert 'Zero-length line' in result
            else:
                # Should produce some output even with invalid coordinates
                assert len(result) > 0


@pytest.mark.unit
@pytest.mark.validation
class TestTextConverterErrorHandling:
    """Test text converter error handling."""

    def test_malformed_text_content(self):
        """Test text with malformed content."""
        converter = TextConverter()

        malformed_cases = [
            ('<text></text>', 'Empty text'),
            ('<text>   </text>', 'Whitespace only'),
            ('<text><tspan></tspan></text>', 'Empty tspan'),
            ('<text><tspan><tspan></tspan></tspan></text>', 'Nested empty tspans'),
        ]

        for xml_str, description in malformed_cases:
            element = ET.fromstring(xml_str)

            context = Mock(spec=ConversionContext)
            context.coordinate_system = Mock()
            context.coordinate_system.svg_to_emu.return_value = (0, 0)
            context.get_next_shape_id.return_value = 4001

            result = converter.convert(element, context)

            if 'Empty' in description or 'Whitespace' in description:
                # Should return empty string for empty content
                assert result == ""
            else:
                assert isinstance(result, str)

    def test_invalid_font_attributes(self):
        """Test text with invalid font attributes."""
        converter = TextConverter()

        invalid_font_cases = [
            ('<text font-size="invalid">Test</text>', 'Invalid font size'),
            ('<text font-family="">Test</text>', 'Empty font family'),
            ('<text font-weight="999">Test</text>', 'Invalid font weight'),
            ('<text x="invalid" y="invalid">Test</text>', 'Invalid coordinates'),
        ]

        for xml_str, description in invalid_font_cases:
            element = ET.fromstring(xml_str)

            context = Mock(spec=ConversionContext)
            context.coordinate_system = Mock()
            context.coordinate_system.svg_to_emu.return_value = (0, 0)
            context.get_next_shape_id.return_value = 4002

            # Mock helper methods
            converter._get_font_family = Mock(return_value='Arial')  # Default fallback
            converter._get_font_size = Mock(return_value=12)  # Default fallback
            converter._get_font_weight = Mock(return_value='normal')
            converter._get_font_style = Mock(return_value='normal')
            converter._get_text_anchor = Mock(return_value='l')
            converter._get_text_decoration = Mock(return_value='')
            converter._get_fill_color = Mock(return_value='<fill/>')
            converter.to_emu = Mock(return_value=91440)

            result = converter.convert(element, context)
            assert isinstance(result, str), f"Failed for {description}"
            assert len(result) > 0, f"Empty result for {description}"


@pytest.mark.unit
@pytest.mark.validation
class TestContextErrorHandling:
    """Test error handling when context is invalid or missing."""

    def test_missing_context_attributes(self):
        """Test converter behavior when context is missing attributes."""
        converter = RectangleConverter()
        element = ET.fromstring('<rect x="10" y="10" width="100" height="50"/>')

        # Test with minimal/invalid context
        invalid_contexts = [
            None,
            Mock(),  # Empty mock
            Mock(spec=ConversionContext)  # Mock without required methods
        ]

        for context in invalid_contexts:
            try:
                result = converter.convert(element, context)
                # If it doesn't crash, that's good defensive programming
                assert isinstance(result, str)
            except AttributeError:
                # Expected for invalid context - should be handled gracefully
                pass
            except Exception as e:
                # Other exceptions might indicate poor error handling
                pytest.fail(f"Unexpected exception type: {type(e)} - {e}")

    def test_coordinate_system_errors(self):
        """Test handling of coordinate system conversion errors."""
        converter = RectangleConverter()
        element = ET.fromstring('<rect x="10" y="10" width="100" height="50"/>')

        context = Mock(spec=ConversionContext)
        context.get_next_shape_id.return_value = 1001

        # Mock coordinate system that raises errors
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.side_effect = ValueError("Invalid coordinate")
        context.coordinate_system.svg_length_to_emu.side_effect = ValueError("Invalid length")

        converter.generate_fill = Mock(return_value='<fill/>')
        converter.generate_stroke = Mock(return_value='<stroke/>')

        try:
            result = converter.convert(element, context)
            # If handled gracefully, should get some result
            assert isinstance(result, str)
        except ValueError:
            # Expected if coordinate system errors aren't handled
            pass


@pytest.mark.unit
@pytest.mark.validation
class TestUnicodeAndSpecialCharacters:
    """Test handling of Unicode and special characters."""

    def test_unicode_text_content(self):
        """Test text with various Unicode characters."""
        converter = TextConverter()

        unicode_cases = [
            'Hello 世界',  # Mixed scripts
            '🎉✨💫🌟',    # Emojis
            'Café résumé naïve',  # Accented characters
            'العربية',     # RTL text
            '\\n\\t\\r',   # Escape sequences
            '<>&"\'',      # XML special characters
        ]

        for unicode_text in unicode_cases:
            element = ET.fromstring(f'<text>{unicode_text}</text>')

            context = Mock(spec=ConversionContext)
            context.coordinate_system = Mock()
            context.coordinate_system.svg_to_emu.return_value = (0, 0)
            context.get_next_shape_id.return_value = 5001

            # Mock helper methods
            converter._get_font_family = Mock(return_value='Arial')
            converter._get_font_size = Mock(return_value=12)
            converter._get_font_weight = Mock(return_value='normal')
            converter._get_font_style = Mock(return_value='normal')
            converter._get_text_anchor = Mock(return_value='l')
            converter._get_text_decoration = Mock(return_value='')
            converter._get_fill_color = Mock(return_value='<fill/>')
            converter.to_emu = Mock(return_value=91440)

            result = converter.convert(element, context)
            assert isinstance(result, str)
            assert len(result) > 0

            # Text should be properly escaped or handled
            if '<' in unicode_text or '>' in unicode_text or '&' in unicode_text:
                # Special characters should be handled appropriately
                assert result != ""

    def test_xml_injection_prevention(self):
        """Test prevention of XML injection through text content."""
        converter = TextConverter()

        malicious_cases = [
            '<script>alert("xss")</script>',
            ']]></text><script>evil</script><text>',
            '<![CDATA[malicious]]>',
        ]

        for malicious_text in malicious_cases:
            # Create text element with potentially malicious content
            try:
                element = ET.fromstring(f'<text>{malicious_text}</text>')
            except ET.ParseError:
                # If XML parsing fails, that's actually good - prevents injection
                continue

            context = Mock(spec=ConversionContext)
            context.coordinate_system = Mock()
            context.coordinate_system.svg_to_emu.return_value = (0, 0)
            context.get_next_shape_id.return_value = 5002

            converter._get_font_family = Mock(return_value='Arial')
            converter._get_font_size = Mock(return_value=12)
            converter._get_font_weight = Mock(return_value='normal')
            converter._get_font_style = Mock(return_value='normal')
            converter._get_text_anchor = Mock(return_value='l')
            converter._get_text_decoration = Mock(return_value='')
            converter._get_fill_color = Mock(return_value='<fill/>')
            converter.to_emu = Mock(return_value=91440)

            result = converter.convert(element, context)

            # Should not contain unescaped malicious content
            assert '<script>' not in result
            assert 'alert(' not in result
            assert isinstance(result, str)


@pytest.mark.unit
@pytest.mark.validation
class TestMemoryAndPerformanceErrorConditions:
    """Test error conditions related to memory and performance limits."""

    def test_extremely_large_polygon(self):
        """Test handling of extremely large polygons."""
        converter = PolygonConverter()

        # Create polygon with many points (but not so many as to crash the test)
        import math
        points = []
        for i in range(500):  # Large but manageable
            angle = 2 * math.pi * i / 500
            x = 50 + 40 * math.cos(angle)
            y = 50 + 40 * math.sin(angle)
            points.append(f"{x:.6f},{y:.6f}")

        points_str = " ".join(points)

        # This creates a very long string - test memory handling
        element = ET.fromstring(f'<polygon points="{points_str}"/>')

        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.return_value = (9144, 9144)
        context.coordinate_system.svg_length_to_emu.side_effect = [73152, 73152]
        context.get_next_shape_id.return_value = 6001

        converter.generate_fill = Mock(return_value='<fill/>')
        converter.generate_stroke = Mock(return_value='<stroke/>')

        # Should handle large polygons without running out of memory
        result = converter.convert(element, context)
        assert isinstance(result, str)
        assert len(result) > 0
        assert '<a:custGeom>' in result

    def test_deeply_nested_tspan(self):
        """Test handling of deeply nested tspan elements."""
        converter = TextConverter()

        # Create deeply nested structure (but not infinite)
        nested_xml = '<text>Root'
        for i in range(20):  # 20 levels should be manageable
            nested_xml += f'<tspan>Level {i}'

        nested_xml += 'Deep'

        for i in range(20):
            nested_xml += '</tspan>'

        nested_xml += '</text>'

        element = ET.fromstring(nested_xml)

        # Should handle deep nesting without stack overflow
        result = converter._extract_text_content(element)

        assert isinstance(result, str)
        assert 'Root' in result
        assert 'Deep' in result
        assert len(result) > 0