#!/usr/bin/env python3
"""
Unit tests for base converter classes and functionality.

Tests the core converter infrastructure including CoordinateSystem, 
ConversionContext, BaseConverter abstract class, and ConverterRegistry.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

# Import with correct module path
import src.converters.base as base
from src.converters.base import (
    CoordinateSystem, 
    ConversionContext, 
    BaseConverter, 
    ConverterRegistry
)


class TestCoordinateSystem:
    """Test CoordinateSystem coordinate transformations."""
    
    def test_init_with_default_slide_size(self):
        """Test coordinate system initialization with default slide dimensions."""
        viewbox = (0, 0, 100, 100)
        coord_sys = CoordinateSystem(viewbox)
        
        assert coord_sys.viewbox == viewbox
        assert coord_sys.slide_width == 9144000  # Default PowerPoint width
        assert coord_sys.slide_height == 6858000  # Default PowerPoint height
        assert coord_sys.preserve_aspect_ratio is True
    
    def test_init_with_custom_slide_size(self):
        """Test coordinate system initialization with custom dimensions."""
        viewbox = (0, 0, 200, 100)
        width, height = 5000000, 4000000
        coord_sys = CoordinateSystem(viewbox, width, height)
        
        assert coord_sys.slide_width == width
        assert coord_sys.slide_height == height
    
    def test_scale_calculation_preserve_aspect_ratio(self):
        """Test scale calculation when preserving aspect ratio."""
        viewbox = (0, 0, 200, 100)  # 2:1 aspect ratio
        slide_width, slide_height = 4000000, 4000000  # 1:1 aspect ratio
        
        coord_sys = CoordinateSystem(viewbox, slide_width, slide_height)
        
        # Should use minimum scale to preserve aspect ratio
        expected_scale = min(slide_width/200, slide_height/100)  # 40000 (height constraint)
        assert coord_sys.scale_x == expected_scale
        assert coord_sys.scale_y == expected_scale
        
        # Should calculate centering offsets
        # Since height is the constraint, there should be vertical centering
        assert coord_sys.offset_x == 0  # No horizontal centering needed
        assert coord_sys.offset_y > 0   # Vertical centering
    
    def test_svg_to_emu_conversion(self):
        """Test SVG coordinate to EMU conversion."""
        viewbox = (10, 20, 100, 100)  # Offset viewbox
        coord_sys = CoordinateSystem(viewbox, 10000, 10000)
        
        # Test point conversion
        x, y = coord_sys.svg_to_emu(60, 70)  # Point in middle of viewbox
        
        # Should subtract viewbox offset, then scale
        expected_x = (60 - 10) * coord_sys.scale_x + coord_sys.offset_x
        expected_y = (70 - 20) * coord_sys.scale_y + coord_sys.offset_y
        
        assert x == int(expected_x)
        assert y == int(expected_y)
    
    def test_svg_length_to_emu(self):
        """Test SVG length conversion to EMUs."""
        viewbox = (0, 0, 100, 200)
        coord_sys = CoordinateSystem(viewbox, 10000, 10000)
        
        # Test horizontal length
        length_x = coord_sys.svg_length_to_emu(50, 'x')
        expected_x = int(50 * coord_sys.scale_x)
        assert length_x == expected_x
        
        # Test vertical length
        length_y = coord_sys.svg_length_to_emu(50, 'y')
        expected_y = int(50 * coord_sys.scale_y)
        assert length_y == expected_y
    
    def test_apply_transform_translate(self):
        """Test applying translate transform."""
        coord_sys = CoordinateSystem((0, 0, 100, 100))
        
        # Test translate with both x and y
        x, y = coord_sys.apply_transform('translate(10,20)', 0, 0)
        assert x == 10
        assert y == 20
        
        # Test translate with only x value
        x, y = coord_sys.apply_transform('translate(15)', 5, 10)
        assert x == 20  # 5 + 15
        assert y == 10  # No change
    
    def test_apply_transform_scale(self):
        """Test applying scale transform."""
        coord_sys = CoordinateSystem((0, 0, 100, 100))
        
        # Test scale with both x and y
        x, y = coord_sys.apply_transform('scale(2,3)', 10, 20)
        assert x == 20  # 10 * 2
        assert y == 60  # 20 * 3
        
        # Test scale with single value (uniform scaling)
        x, y = coord_sys.apply_transform('scale(2)', 10, 20)
        assert x == 20  # 10 * 2
        assert y == 40  # 20 * 2


class TestConversionContext:
    """Test ConversionContext functionality."""
    
    def test_init_without_svg_root(self):
        """Test context initialization without SVG root element."""
        context = ConversionContext()
        
        assert context.coordinate_system is None
        assert isinstance(context.gradients, dict)
        assert isinstance(context.patterns, dict)
        assert isinstance(context.clips, dict)
        assert isinstance(context.fonts, dict)
        assert context.shape_id_counter == 1000
        assert isinstance(context.group_stack, list)
        assert context.current_transform is None
        assert isinstance(context.style_stack, list)
        assert context.unit_converter is not None
        assert context.viewport_handler is not None
    
    def test_init_with_svg_root(self):
        """Test context initialization with SVG root element."""
        svg_root = ET.fromstring('<svg width="100" height="100"></svg>')
        context = ConversionContext(svg_root)
        
        # Context should be initialized
        assert context.viewport_context is None  # Simplified for now
    
    def test_get_next_shape_id(self):
        """Test shape ID generation."""
        context = ConversionContext()
        
        first_id = context.get_next_shape_id()
        second_id = context.get_next_shape_id()
        
        assert first_id == 1000
        assert second_id == 1001
        assert context.shape_id_counter == 1002
    
    def test_group_stack_management(self):
        """Test group stack push/pop operations."""
        context = ConversionContext()
        
        assert len(context.group_stack) == 0
        
        # Push group attributes
        attrs1 = {'fill': 'red', 'stroke': 'blue'}
        context.push_group(attrs1)
        assert len(context.group_stack) == 1
        assert context.group_stack[-1] == attrs1
        
        # Push another group
        attrs2 = {'opacity': '0.5'}
        context.push_group(attrs2)
        assert len(context.group_stack) == 2
        
        # Pop groups
        context.pop_group()
        assert len(context.group_stack) == 1
        assert context.group_stack[-1] == attrs1
        
        context.pop_group()
        assert len(context.group_stack) == 0
    
    def test_get_inherited_style(self):
        """Test inherited style merging from group stack."""
        context = ConversionContext()
        
        # Empty stack should return empty dict
        assert context.get_inherited_style() == {}
        
        # Add groups with different styles
        context.push_group({'fill': 'red', 'stroke-width': '2'})
        context.push_group({'stroke': 'blue', 'opacity': '0.8'})
        context.push_group({'fill': 'green'})  # Should override red fill
        
        merged = context.get_inherited_style()
        expected = {
            'fill': 'green',  # Overridden by last group
            'stroke-width': '2',
            'stroke': 'blue',
            'opacity': '0.8'
        }
        assert merged == expected


class MockConverter(BaseConverter):
    """Mock converter for testing BaseConverter functionality."""
    
    supported_elements = ['rect', 'circle']
    
    def can_convert(self, element):
        tag = self.get_element_tag(element)
        return tag in self.supported_elements
    
    def convert(self, element, context):
        return f"<mock-output>{element.tag}</mock-output>"


class TestBaseConverter:
    """Test BaseConverter abstract class functionality."""
    
    def test_get_element_tag_without_namespace(self):
        """Test extracting tag name without namespace."""
        converter = MockConverter()
        
        # Element without namespace
        element = ET.fromstring('<rect x="10" y="10" width="50" height="30"/>')
        assert converter.get_element_tag(element) == 'rect'
    
    def test_get_element_tag_with_namespace(self):
        """Test extracting tag name with namespace."""
        converter = MockConverter()
        
        # Element with namespace
        element = ET.fromstring('<svg:rect xmlns:svg="http://www.w3.org/2000/svg" x="10" y="10" width="50" height="30"/>')
        assert converter.get_element_tag(element) == 'rect'
    
    def test_parse_style_attribute_empty(self):
        """Test parsing empty or None style attribute."""
        converter = MockConverter()
        
        assert converter.parse_style_attribute(None) == {}
        assert converter.parse_style_attribute('') == {}
        assert converter.parse_style_attribute('   ') == {}
    
    def test_parse_style_attribute_valid(self):
        """Test parsing valid style attribute."""
        converter = MockConverter()
        
        style = 'fill:red; stroke: blue ; stroke-width:2'
        result = converter.parse_style_attribute(style)
        
        expected = {
            'fill': 'red',
            'stroke': 'blue',
            'stroke-width': '2'
        }
        assert result == expected
    
    def test_get_attribute_with_style_direct_attribute(self):
        """Test getting attribute directly from element."""
        converter = MockConverter()
        element = ET.fromstring('<rect fill="red" style="fill:blue;stroke:green"/>')
        
        # Direct attribute should take priority
        result = converter.get_attribute_with_style(element, 'fill')
        assert result == 'red'
    
    def test_get_attribute_with_style_from_style(self):
        """Test getting attribute from style when not in direct attributes."""
        converter = MockConverter()
        element = ET.fromstring('<rect style="fill:blue;stroke:green"/>')
        
        # Should get from style attribute
        result = converter.get_attribute_with_style(element, 'stroke')
        assert result == 'green'
    
    def test_parse_color_hex(self):
        """Test parsing hexadecimal color values."""
        converter = MockConverter()
        
        # 6-digit hex
        assert converter.parse_color('#FF0000') == 'FF0000'
        assert converter.parse_color('#ff0000') == 'FF0000'
        
        # 3-digit hex (should expand)
        assert converter.parse_color('#F00') == 'FF0000'
        assert converter.parse_color('#f00') == 'FF0000'
    
    def test_parse_color_rgb(self):
        """Test parsing RGB color values."""
        converter = MockConverter()
        
        # rgb() format
        assert converter.parse_color('rgb(255, 0, 0)') == 'FF0000'
        assert converter.parse_color('rgb(128, 128, 128)') == '808080'
        
        # rgba() format (ignores alpha for now)
        assert converter.parse_color('rgba(255, 0, 0, 0.5)') == 'FF0000'
    
    def test_parse_color_named(self):
        """Test parsing named color values."""
        converter = MockConverter()
        
        # Common named colors
        assert converter.parse_color('red') == 'FF0000'
        assert converter.parse_color('blue') == '0000FF'
        assert converter.parse_color('green') == '008000'
    
    def test_parse_length_no_units(self):
        """Test parsing length values without units."""
        converter = MockConverter()
        
        assert converter.parse_length('100') == 100.0
        assert converter.parse_length('0') == 0.0
        assert converter.parse_length('50.5') == 50.5
    
    def test_parse_length_with_units(self):
        """Test parsing length values with various units."""
        converter = MockConverter()
        
        # Pixels
        assert converter.parse_length('100px') == 100.0
        
        # Points (1pt = 1.33333px)
        assert abs(converter.parse_length('72pt') - 96.0) < 0.1
        
        # Inches (1in = 96px)
        assert converter.parse_length('1in') == 96.0
    
    def test_generate_fill_solid_color(self):
        """Test generating solid color fill."""
        converter = MockConverter()
        
        result = converter.generate_fill('red')
        assert '<a:solidFill>' in result
        assert '<a:srgbClr val="FF0000"' in result
    
    def test_generate_stroke_basic(self):
        """Test generating basic stroke."""
        converter = MockConverter()
        
        result = converter.generate_stroke('blue', '2')
        assert '<a:ln w="25400">' in result  # 2px * 12700 EMU/px
        assert '<a:srgbClr val="0000FF"' in result


class TestConverterRegistry:
    """Test ConverterRegistry functionality."""
    
    def test_init(self):
        """Test registry initialization."""
        registry = ConverterRegistry()
        
        assert isinstance(registry.converters, list)
        assert len(registry.converters) == 0
        assert isinstance(registry.element_map, dict)
        assert len(registry.element_map) == 0
    
    def test_register_converter_instance(self):
        """Test registering converter instance."""
        registry = ConverterRegistry()
        converter = MockConverter()
        
        registry.register(converter)
        
        assert len(registry.converters) == 1
        assert registry.converters[0] == converter
        
        # Check element mapping
        assert 'rect' in registry.element_map
        assert 'circle' in registry.element_map
        assert converter in registry.element_map['rect']
        assert converter in registry.element_map['circle']
    
    def test_get_converter_by_element_map(self):
        """Test getting converter using element map."""
        registry = ConverterRegistry()
        converter = MockConverter()
        registry.register(converter)
        
        element = ET.fromstring('<rect x="10" y="10" width="50" height="30"/>')
        result = registry.get_converter(element)
        
        assert result == converter
    
    def test_convert_element_success(self):
        """Test successful element conversion."""
        registry = ConverterRegistry()
        converter = MockConverter()
        registry.register(converter)
        
        element = ET.fromstring('<rect x="10" y="10" width="50" height="30"/>')
        context = ConversionContext()
        
        result = registry.convert_element(element, context)
        
        assert result == "<mock-output>rect</mock-output>"
    
    def test_convert_element_no_converter(self):
        """Test element conversion when no converter found."""
        registry = ConverterRegistry()
        
        element = ET.fromstring('<unsupported-element/>')
        context = ConversionContext()
        
        result = registry.convert_element(element, context)
        
        assert result is None