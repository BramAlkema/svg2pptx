#!/usr/bin/env python3
"""
Unit tests for text converter functionality.

Tests the TextConverter class which handles SVG text and tspan elements,
including font properties, styling, positioning, and text content extraction.
"""

import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.converters.text import TextConverter
from src.converters.base import ConversionContext, CoordinateSystem
from core.units import UnitConverter
from core.color import Color
from core.services.conversion_services import ConversionServices


class TestTextConverter:
    """Test TextConverter functionality."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for text converter testing."""
        services = Mock(spec=ConversionServices)
        services.unit_converter = Mock(spec=UnitConverter)
        services.color_parser = Mock()
        services.viewport_handler = Mock()
        services.font_service = Mock()
        services.gradient_service = Mock()
        services.pattern_service = Mock()
        services.clip_service = Mock()

        # Mock color parser to return proper color info
        mock_color_info = Mock()
        mock_color_info.red = 255
        mock_color_info.green = 0
        mock_color_info.blue = 0
        services.color_parser.parse.return_value = mock_color_info

        return services

    def test_supported_elements(self, mock_services):
        """Test supported element types."""
        converter = TextConverter(services=mock_services)
        
        assert 'text' in converter.supported_elements
        assert 'tspan' in converter.supported_elements
    
    def test_font_weights_mapping(self, mock_services):
        """Test font weight mapping constants."""
        converter = TextConverter(services=mock_services)
        
        assert converter.FONT_WEIGHTS['normal'] == '400'
        assert converter.FONT_WEIGHTS['bold'] == '700'
        assert converter.FONT_WEIGHTS['bolder'] == '800'
        assert converter.FONT_WEIGHTS['lighter'] == '200'
        assert converter.FONT_WEIGHTS['100'] == '100'
        assert converter.FONT_WEIGHTS['900'] == '900'
    
    def test_text_anchors_mapping(self, mock_services):
        """Test text anchor mapping constants."""
        converter = TextConverter(services=mock_services)
        
        assert converter.TEXT_ANCHORS['start'] == 'l'
        assert converter.TEXT_ANCHORS['middle'] == 'ctr'
        assert converter.TEXT_ANCHORS['end'] == 'r'
    
    def test_extract_text_content_simple(self, mock_services):
        """Test extracting simple text content."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text>Hello World</text>')
        
        result = converter._extract_text_content(element)
        assert result == 'Hello World'
    
    def test_extract_text_content_with_tspan(self, mock_services):
        """Test extracting text content with tspan elements."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('''
            <text>Start <tspan>middle</tspan> end</text>
        ''')
        
        result = converter._extract_text_content(element)
        assert 'Start' in result
        assert 'middle' in result
        assert 'end' in result
    
    def test_extract_text_content_empty(self, mock_services):
        """Test extracting content from empty text element."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text></text>')
        
        result = converter._extract_text_content(element)
        assert result == ''
    
    def test_get_font_family_direct_attribute(self, mock_services):
        """Test getting font family from direct attribute."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text font-family="Arial">Test</text>')
        
        result = converter._get_font_family(element)
        assert result == 'Arial'
    
    def test_get_font_family_with_quotes(self, mock_services):
        """Test getting font family with quotes and multiple fonts."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text font-family="\'Times New Roman\', serif">Test</text>')
        
        result = converter._get_font_family(element)
        assert result == 'Times New Roman'
    
    def test_get_font_family_from_style(self, mock_services):
        """Test getting font family from style attribute."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text style="font-family: Helvetica; color: red;">Test</text>')
        
        result = converter._get_font_family(element)
        assert result == 'Helvetica'
    
    def test_get_font_family_default(self, mock_services):
        """Test default font family when none specified."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text>Test</text>')
        
        result = converter._get_font_family(element)
        assert result == 'Arial'
    
    def test_get_font_size_direct_attribute(self, mock_services):
        """Test getting font size from direct attribute."""
        converter = TextConverter(services=mock_services)
        context = Mock(spec=ConversionContext)
        element = ET.fromstring('<text font-size="16">Test</text>')
        
        with patch.object(converter, '_parse_font_size', return_value=16):
            result = converter._get_font_size(element, context)
            assert result == 16
    
    def test_get_font_size_from_style(self, mock_services):
        """Test getting font size from style attribute."""
        converter = TextConverter(services=mock_services)
        context = Mock(spec=ConversionContext)
        element = ET.fromstring('<text style="font-size: 14pt; color: blue;">Test</text>')
        
        with patch.object(converter, '_parse_font_size', return_value=14):
            result = converter._get_font_size(element, context)
            assert result == 14
    
    def test_get_font_size_default(self, mock_services):
        """Test default font size when none specified."""
        converter = TextConverter(services=mock_services)
        context = Mock(spec=ConversionContext)
        element = ET.fromstring('<text>Test</text>')
        
        result = converter._get_font_size(element, context)
        assert result == 12
    
    def test_parse_font_size_with_units(self, mock_services):
        """Test parsing font size with different units."""
        converter = TextConverter(services=mock_services)
        context = Mock(spec=ConversionContext)
        
        # Mock the parse_length method from base converter
        with patch.object(converter, 'parse_length', return_value=16.0):
            result = converter._parse_font_size('12pt', context)
            # 16 pixels * 72 dpi / 96 dpi = 12 points
            assert result == 12
    
    def test_parse_font_size_error_handling(self, mock_services):
        """Test font size parsing error handling."""
        converter = TextConverter(services=mock_services)
        context = Mock(spec=ConversionContext)
        
        # Mock parse_length to raise an exception
        with patch.object(converter, 'parse_length', side_effect=Exception("Invalid unit")):
            result = converter._parse_font_size('invalid', context)
            assert result == 12  # Default value
    
    def test_get_font_weight_direct_attribute(self, mock_services):
        """Test getting font weight from direct attribute."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text font-weight="bold">Test</text>')
        
        result = converter._get_font_weight(element)
        assert result == '700'
    
    def test_get_font_weight_numeric(self, mock_services):
        """Test getting numeric font weight."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text font-weight="600">Test</text>')
        
        result = converter._get_font_weight(element)
        assert result == '600'
    
    def test_get_font_weight_from_style(self, mock_services):
        """Test getting font weight from style attribute."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text style="font-weight: bolder; color: red;">Test</text>')
        
        result = converter._get_font_weight(element)
        assert result == '800'
    
    def test_get_font_weight_default(self, mock_services):
        """Test default font weight when none specified."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text>Test</text>')
        
        result = converter._get_font_weight(element)
        assert result == '400'
    
    def test_get_font_style_italic(self, mock_services):
        """Test getting italic font style."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text font-style="italic">Test</text>')
        
        result = converter._get_font_style(element)
        assert result == 'italic'
    
    def test_get_font_style_oblique(self, mock_services):
        """Test getting oblique font style (treated as italic)."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text font-style="oblique">Test</text>')
        
        result = converter._get_font_style(element)
        assert result == 'italic'
    
    def test_get_font_style_from_style(self, mock_services):
        """Test getting font style from style attribute."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text style="font-style: italic; color: blue;">Test</text>')
        
        result = converter._get_font_style(element)
        assert result == 'italic'
    
    def test_get_font_style_default(self, mock_services):
        """Test default font style when none specified."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text>Test</text>')
        
        result = converter._get_font_style(element)
        assert result == 'normal'
    
    def test_get_text_anchor_start(self, mock_services):
        """Test text anchor start (left alignment)."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text text-anchor="start">Test</text>')
        
        result = converter._get_text_anchor(element)
        assert result == 'l'
    
    def test_get_text_anchor_middle(self, mock_services):
        """Test text anchor middle (center alignment)."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text text-anchor="middle">Test</text>')
        
        result = converter._get_text_anchor(element)
        assert result == 'ctr'
    
    def test_get_text_anchor_end(self, mock_services):
        """Test text anchor end (right alignment)."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text text-anchor="end">Test</text>')
        
        result = converter._get_text_anchor(element)
        assert result == 'r'
    
    def test_get_text_anchor_default(self, mock_services):
        """Test default text anchor when none specified."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text>Test</text>')
        
        result = converter._get_text_anchor(element)
        assert result == 'l'
    
    def test_get_text_decoration_underline(self, mock_services):
        """Test getting underline text decoration."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text text-decoration="underline">Test</text>')
        
        result = converter._get_text_decoration(element)
        assert 'underline' in result
    
    def test_get_text_decoration_line_through(self, mock_services):
        """Test getting line-through text decoration."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text text-decoration="line-through">Test</text>')
        
        result = converter._get_text_decoration(element)
        assert 'line-through' in result
    
    def test_get_text_decoration_multiple(self, mock_services):
        """Test getting multiple text decorations."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text text-decoration="underline line-through">Test</text>')
        
        result = converter._get_text_decoration(element)
        assert 'underline' in result
        assert 'line-through' in result
    
    def test_get_text_decoration_from_style(self, mock_services):
        """Test getting text decoration from style attribute."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text style="text-decoration: underline; color: red;">Test</text>')
        
        result = converter._get_text_decoration(element)
        assert 'underline' in result
    
    def test_get_text_decoration_empty(self, mock_services):
        """Test getting text decoration when none specified."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text>Test</text>')
        
        result = converter._get_text_decoration(element)
        assert result == []
    
    def test_get_fill_color_direct_attribute(self, mock_services):
        """Test getting fill color from direct attribute."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text fill="red">Test</text>')
        
        # Use modern Color API to get expected hex value
        color = Color('red')
        expected_red_hex = color.hex().replace('#', '').upper()
        with patch.object(converter, 'parse_color', return_value=expected_red_hex):
            result = converter._get_fill_color(element)
            assert f'<a:solidFill><a:srgbClr val="{expected_red_hex}"/></a:solidFill>' == result
    
    def test_get_fill_color_from_style(self, mock_services):
        """Test getting fill color from style attribute."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text style="fill: blue; font-size: 14px;">Test</text>')
        
        # Use modern Color API to get expected hex value
        color = Color('blue')
        expected_blue_hex = color.hex().replace('#', '').upper()
        with patch.object(converter, 'parse_color', return_value=expected_blue_hex):
            result = converter._get_fill_color(element)
            assert f'<a:solidFill><a:srgbClr val="{expected_blue_hex}"/></a:solidFill>' == result
    
    def test_get_fill_color_none(self, mock_services):
        """Test getting fill color when set to none."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text fill="none">Test</text>')
        
        result = converter._get_fill_color(element)
        assert result == '<a:solidFill><a:srgbClr val="000000"/></a:solidFill>'  # Default black
    
    def test_get_fill_color_default(self, mock_services):
        """Test default fill color when none specified."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text>Test</text>')
        
        result = converter._get_fill_color(element)
        assert result == '<a:solidFill><a:srgbClr val="000000"/></a:solidFill>'
    
    # Color parsing is tested in the base converter tests since we use the inherited method
    
    def test_escape_xml_special_chars(self, mock_services):
        """Test XML special character escaping."""
        converter = TextConverter(services=mock_services)
        
        assert converter._escape_xml('Hello & World') == 'Hello &amp; World'
        assert converter._escape_xml('A < B > C') == 'A &lt; B &gt; C'
        assert converter._escape_xml('Say "Hello"') == 'Say &quot;Hello&quot;'
        assert converter._escape_xml("It's working") == 'It&apos;s working'
    
    def test_escape_xml_no_special_chars(self, mock_services):
        """Test XML escaping with no special characters."""
        converter = TextConverter(services=mock_services)
        
        assert converter._escape_xml('Hello World') == 'Hello World'
        assert converter._escape_xml('12345') == '12345'


class TestTextConverterIntegration:
    """Integration tests for TextConverter with full context."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for text converter testing."""
        services = Mock(spec=ConversionServices)
        services.unit_converter = Mock(spec=UnitConverter)
        services.color_parser = Mock()
        services.viewport_handler = Mock()
        services.font_service = Mock()
        services.gradient_service = Mock()
        services.pattern_service = Mock()
        services.clip_service = Mock()

        # Mock color parser to return proper color info
        mock_color_info = Mock()
        mock_color_info.red = 255
        mock_color_info.green = 0
        mock_color_info.blue = 0
        services.color_parser.parse.return_value = mock_color_info

        return services

    def test_convert_simple_text(self, mock_services):
        """Test converting simple text element."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text x="10" y="20">Hello World</text>')

        # Mock the to_emu method on the converter
        converter.to_emu = Mock(return_value=914400)  # 1 inch in EMU

        # Mock context with coordinate system
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock(spec=CoordinateSystem)
        # Use UnitConverter to calculate proper EMU values
        unit_converter = UnitConverter()
        emu_10pt = unit_converter.to_emu('10pt')
        emu_20pt = unit_converter.to_emu('20pt')
        mock_coord_system.svg_to_emu.return_value = (emu_10pt, emu_20pt)  # (10 * 12700, 20 * 12700)
        context.coordinate_system = mock_coord_system
        context.get_next_shape_id.return_value = 1001

        result = converter.convert(element, context)

        assert '<a:sp>' in result
        assert 'Hello World' in result
    
    def test_convert_empty_text(self, mock_services):
        """Test converting text element with no content."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('<text x="10" y="20"></text>')
        
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock(spec=CoordinateSystem)
        # Use UnitConverter to calculate proper EMU values
        unit_converter = UnitConverter()
        emu_10pt = unit_converter.to_emu('10pt')
        emu_20pt = unit_converter.to_emu('20pt')
        mock_coord_system.svg_to_emu.return_value = (emu_10pt, emu_20pt)
        context.coordinate_system = mock_coord_system
        
        result = converter.convert(element, context)
        assert result == ""
    
    def test_convert_text_with_styling(self, mock_services):
        """Test converting text with font styling."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('''
            <text x="10" y="20" font-family="Arial" font-size="14" font-weight="bold"
                  font-style="italic" fill="red" text-decoration="underline">
                Styled Text
            </text>
        ''')

        # Mock the to_emu method on the converter
        converter.to_emu = Mock(return_value=914400)  # 1 inch in EMU
        converter.parse_color = Mock(return_value="FF0000")  # Red color

        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock(spec=CoordinateSystem)
        # Use UnitConverter to calculate proper EMU values
        unit_converter = UnitConverter()
        emu_10pt = unit_converter.to_emu('10pt')
        emu_20pt = unit_converter.to_emu('20pt')
        mock_coord_system.svg_to_emu.return_value = (emu_10pt, emu_20pt)
        context.coordinate_system = mock_coord_system
        context.get_next_shape_id.return_value = 1002

        result = converter.convert(element, context)

        assert 'typeface="Arial"' in result
        assert 'b="1"' in result  # Bold
        assert 'i="1"' in result  # Italic
        assert 'u="sng"' in result  # Underline
        assert 'Styled Text' in result
    
    def test_convert_text_with_tspan(self, mock_services):
        """Test converting text with tspan elements."""
        converter = TextConverter(services=mock_services)
        element = ET.fromstring('''
            <text x="10" y="20">Start <tspan>middle</tspan> end</text>
        ''')

        # Mock the to_emu method on the converter
        converter.to_emu = Mock(return_value=914400)  # 1 inch in EMU

        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock(spec=CoordinateSystem)
        # Use UnitConverter to calculate proper EMU values
        unit_converter = UnitConverter()
        emu_10pt = unit_converter.to_emu('10pt')
        emu_20pt = unit_converter.to_emu('20pt')
        mock_coord_system.svg_to_emu.return_value = (emu_10pt, emu_20pt)
        context.coordinate_system = mock_coord_system
        context.get_next_shape_id.return_value = 1003

        result = converter.convert(element, context)

        # Should combine all text content
        assert 'Start middle end' in result or ('Start' in result and 'middle' in result and 'end' in result)
    
    def test_text_anchor_positioning(self, mock_services):
        """Test text positioning based on text-anchor."""
        converter = TextConverter(services=mock_services)

        # Test center anchoring
        element = ET.fromstring('<text x="100" y="50" text-anchor="middle">Center Text</text>')

        # Mock the to_emu method on the converter
        converter.to_emu = Mock(return_value=914400)  # 1 inch in EMU

        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock(spec=CoordinateSystem)
        # Use UnitConverter to calculate proper EMU values
        unit_converter = UnitConverter()
        emu_100pt = unit_converter.to_emu('100pt')
        emu_50pt = unit_converter.to_emu('50pt')
        mock_coord_system.svg_to_emu.return_value = (emu_100pt, emu_50pt)
        context.coordinate_system = mock_coord_system
        context.get_next_shape_id.return_value = 1004

        result = converter.convert(element, context)

        assert 'algn="ctr"' in result  # Center alignment in DrawingML
    
    def test_inheritance_from_base_converter(self, mock_services):
        """Test that TextConverter properly inherits from BaseConverter."""
        converter = TextConverter(services=mock_services)
        
        # Should have BaseConverter methods
        assert hasattr(converter, 'get_element_tag')
        assert hasattr(converter, 'parse_style_attribute')
        assert hasattr(converter, 'get_attribute_with_style')
        assert hasattr(converter, 'parse_length')
        assert hasattr(converter, 'generate_fill')
        assert hasattr(converter, 'generate_stroke')
    
    def test_can_convert_method(self, mock_services):
        """Test that converter can identify supported elements."""
        converter = TextConverter(services=mock_services)
        
        # Create test elements
        text_element = ET.fromstring('<text>Test</text>')
        tspan_element = ET.fromstring('<tspan>Test</tspan>')
        rect_element = ET.fromstring('<rect width="10" height="10"/>')
        
        # Should have can_convert method (inherited from BaseConverter)
        # Since TextConverter doesn't override can_convert, it uses the base implementation
        # which checks against supported_elements
        assert hasattr(converter, 'supported_elements')
        assert 'text' in converter.supported_elements
        assert 'tspan' in converter.supported_elements