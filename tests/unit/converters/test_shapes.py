#!/usr/bin/env python3
"""
Unit tests for shape converter classes.

Tests the shape converter functionality including Rectangle, Circle, Ellipse, 
Polygon, Polyline, and Line converters.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

# Import with correct module path
import src.converters.shapes as shapes
from src.converters.shapes import (
    RectangleConverter,
    CircleConverter, 
    EllipseConverter,
    PolygonConverter,
    LineConverter
)
from src.converters.base import ConversionContext


class TestRectangleConverter:
    """Test RectangleConverter functionality."""
    
    def test_can_convert_rect(self):
        """Test that converter recognizes rect elements."""
        converter = RectangleConverter()
        
        element = ET.fromstring('<rect width="100" height="50"/>')
        assert converter.can_convert(element) is True
        
        # Test with namespace
        element = ET.fromstring('<svg:rect xmlns:svg="http://www.w3.org/2000/svg" width="100" height="50"/>')
        assert converter.can_convert(element) is True
    
    def test_can_convert_other_elements(self):
        """Test that converter rejects non-rect elements."""
        converter = RectangleConverter()
        
        element = ET.fromstring('<circle r="50"/>')
        assert converter.can_convert(element) is False
        
        element = ET.fromstring('<path d="M0,0 L100,100"/>')
        assert converter.can_convert(element) is False
    
    def test_convert_basic_rectangle(self):
        """Test converting basic rectangle with minimal attributes."""
        converter = RectangleConverter()
        element = ET.fromstring('<rect x="10" y="20" width="100" height="50"/>')
        
        # Mock context
        context = Mock(spec=ConversionContext)
        context.batch_convert_to_emu.return_value = {
            'x': 914400,    # 10 * 91440 (approximate EMU conversion)
            'y': 1828800,   # 20 * 91440
            'width': 9144000,   # 100 * 91440  
            'height': 4572000,  # 50 * 91440
            'rx': 0,
            'ry': 0
        }
        context.get_next_shape_id.return_value = 1001
        
        result = converter.convert(element, context)
        
        # Check basic structure
        assert '<p:sp>' in result
        assert '<p:nvSpPr>' in result
        assert 'id="1001"' in result
        assert 'name="Rectangle 1001"' in result
        
        # Check coordinates
        assert '<a:off x="914400" y="1828800"/>' in result
        assert '<a:ext cx="9144000" cy="4572000"/>' in result
        
        # Check shape preset (regular rectangle)
        assert '<a:prstGeom prst="rect">' in result
        
        # Verify context method calls
        context.batch_convert_to_emu.assert_called_once()
        context.get_next_shape_id.assert_called_once()
    
    def test_convert_rectangle_with_defaults(self):
        """Test converting rectangle with default values."""
        converter = RectangleConverter()
        element = ET.fromstring('<rect/>')  # No attributes
        
        context = Mock(spec=ConversionContext)
        context.batch_convert_to_emu.return_value = {
            'x': 0, 'y': 0, 'width': 0, 'height': 0, 'rx': 0, 'ry': 0
        }
        context.get_next_shape_id.return_value = 1002
        
        result = converter.convert(element, context)
        
        # Should handle defaults gracefully
        assert '<a:off x="0" y="0"/>' in result
        assert '<a:ext cx="0" cy="0"/>' in result
        assert 'Rectangle 1002' in result
    
    def test_convert_rectangle_with_styles(self):
        """Test converting rectangle with style attributes."""
        converter = RectangleConverter()
        element = ET.fromstring('''
            <rect x="0" y="0" width="100" height="100" 
                  fill="red" stroke="blue" stroke-width="2" opacity="0.8"/>
        ''')
        
        context = Mock(spec=ConversionContext)
        context.batch_convert_to_emu.return_value = {
            'x': 0, 'y': 0, 'width': 9144000, 'height': 9144000, 'rx': 0, 'ry': 0
        }
        context.get_next_shape_id.return_value = 1003
        
        # Mock the style generation methods
        converter.generate_fill = Mock(return_value='<mock-fill/>')
        converter.generate_stroke = Mock(return_value='<mock-stroke/>')
        
        result = converter.convert(element, context)
        
        # Check that style methods were called with correct parameters
        converter.generate_fill.assert_called_once_with('red', '0.8', context)
        converter.generate_stroke.assert_called_once_with('blue', '2', '0.8', context)
        
        # Check that style elements are included
        assert '<mock-fill/>' in result
        assert '<mock-stroke/>' in result
    
    def test_convert_rounded_rectangle(self):
        """Test converting rectangle with rounded corners."""
        converter = RectangleConverter()
        element = ET.fromstring('<rect x="0" y="0" width="100" height="50" rx="10" ry="5"/>')
        
        context = Mock(spec=ConversionContext)
        context.batch_convert_to_emu.return_value = {
            'x': 0, 'y': 0, 'width': 9144000, 'height': 4572000, 'rx': 914400, 'ry': 457200
        }
        context.get_next_shape_id.return_value = 1004
        
        result = converter.convert(element, context)
        
        # Should use rounded rectangle preset
        assert '<a:prstGeom prst="roundRect">' in result
        assert '<a:avLst>' in result
        assert '<a:gd name="adj"' in result


class TestCircleConverter:
    """Test CircleConverter functionality."""
    
    def test_can_convert_circle(self):
        """Test that converter recognizes circle elements."""
        converter = CircleConverter()
        
        element = ET.fromstring('<circle r="50"/>')
        assert converter.can_convert(element) is True
        
        # Test with namespace
        element = ET.fromstring('<svg:circle xmlns:svg="http://www.w3.org/2000/svg" r="50"/>')
        assert converter.can_convert(element) is True
    
    def test_can_convert_other_elements(self):
        """Test that converter rejects non-circle elements."""
        converter = CircleConverter()
        
        element = ET.fromstring('<rect width="100" height="50"/>')
        assert converter.can_convert(element) is False
        
        element = ET.fromstring('<ellipse rx="50" ry="30"/>')
        assert converter.can_convert(element) is False
    
    def test_convert_basic_circle(self):
        """Test converting basic circle."""
        converter = CircleConverter()
        element = ET.fromstring('<circle cx="50" cy="50" r="25"/>')
        
        # Mock context and coordinate system
        context = Mock(spec=ConversionContext)
        coord_system = Mock()
        coord_system.svg_to_emu.return_value = (2286000, 2286000)  # (25, 25) in EMU
        coord_system.svg_length_to_emu.return_value = 4572000  # 50 diameter in EMU
        context.coordinate_system = coord_system
        context.get_next_shape_id.return_value = 2001
        
        # Mock style generation
        converter.generate_fill = Mock(return_value='<fill-mock/>')
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, context)
        
        # Check basic structure
        assert '<p:sp>' in result
        assert 'id="2001"' in result
        assert 'name="Circle 2001"' in result
        
        # Check coordinates (should be bounding box: cx-r, cy-r)
        assert '<a:off x="2286000" y="2286000"/>' in result
        assert '<a:ext cx="4572000" cy="4572000"/>' in result  # diameter x diameter
        
        # Check shape preset (ellipse for circle)
        assert '<a:prstGeom prst="ellipse">' in result
        
        # Verify coordinate system calls
        coord_system.svg_to_emu.assert_called_once_with(25, 25)  # cx-r, cy-r
        coord_system.svg_length_to_emu.assert_called_once_with(50, 'x')  # diameter
    
    def test_convert_circle_with_defaults(self):
        """Test converting circle with default values."""
        converter = CircleConverter()
        element = ET.fromstring('<circle/>')  # No attributes
        
        context = Mock(spec=ConversionContext)
        coord_system = Mock()
        coord_system.svg_to_emu.return_value = (0, 0)
        coord_system.svg_length_to_emu.return_value = 0
        context.coordinate_system = coord_system
        context.get_next_shape_id.return_value = 2002
        
        converter.generate_fill = Mock(return_value='')
        converter.generate_stroke = Mock(return_value='')
        
        result = converter.convert(element, context)
        
        # Should handle defaults (cx=0, cy=0, r=0)
        assert '<a:off x="0" y="0"/>' in result
        assert '<a:ext cx="0" cy="0"/>' in result
        assert 'Circle 2002' in result


class TestEllipseConverter:
    """Test EllipseConverter functionality."""
    
    def test_can_convert_ellipse(self):
        """Test that converter recognizes ellipse elements."""
        converter = EllipseConverter()
        
        element = ET.fromstring('<ellipse rx="50" ry="30"/>')
        assert converter.can_convert(element) is True
    
    def test_can_convert_other_elements(self):
        """Test that converter rejects non-ellipse elements."""
        converter = EllipseConverter()
        
        element = ET.fromstring('<circle r="50"/>')
        assert converter.can_convert(element) is False
        
        element = ET.fromstring('<rect width="100" height="50"/>')
        assert converter.can_convert(element) is False
    
    def test_convert_basic_ellipse(self):
        """Test converting basic ellipse."""
        converter = EllipseConverter()
        element = ET.fromstring('<ellipse cx="100" cy="50" rx="60" ry="30"/>')
        
        # Mock context and coordinate system
        context = Mock(spec=ConversionContext)
        coord_system = Mock()
        coord_system.svg_to_emu.return_value = (3657600, 1828800)  # (40, 20) in EMU
        coord_system.svg_length_to_emu.side_effect = [10972800, 5486400]  # width=120, height=60 in EMU
        context.coordinate_system = coord_system
        context.get_next_shape_id.return_value = 3001
        
        converter.generate_fill = Mock(return_value='<fill-mock/>')
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, context)
        
        # Check basic structure
        assert '<p:sp>' in result
        assert 'id="3001"' in result
        assert 'name="Ellipse 3001"' in result
        
        # Check coordinates (should be bounding box: cx-rx, cy-ry)
        assert '<a:off x="3657600" y="1828800"/>' in result
        assert '<a:ext cx="10972800" cy="5486400"/>' in result  # width x height
        
        # Check shape preset
        assert '<a:prstGeom prst="ellipse">' in result
        
        # Verify coordinate system calls
        coord_system.svg_to_emu.assert_called_once_with(40, 20)  # cx-rx, cy-ry


class TestPolygonConverter:
    """Test PolygonConverter functionality."""
    
    def test_can_convert_polygon_and_polyline(self):
        """Test that converter recognizes polygon and polyline elements."""
        converter = PolygonConverter()
        
        element = ET.fromstring('<polygon points="0,0 100,0 50,100"/>')
        assert converter.can_convert(element) is True
        
        element = ET.fromstring('<polyline points="0,0 50,50 100,0"/>')
        assert converter.can_convert(element) is True
    
    def test_can_convert_other_elements(self):
        """Test that converter rejects other elements."""
        converter = PolygonConverter()
        
        element = ET.fromstring('<rect width="100" height="50"/>')
        assert converter.can_convert(element) is False
        
        element = ET.fromstring('<circle r="50"/>')
        assert converter.can_convert(element) is False
    
    def test_parse_points_comma_separated(self):
        """Test parsing comma-separated points."""
        converter = PolygonConverter()
        
        points = converter._parse_points("0,0 100,50 50,100")
        expected = [(0.0, 0.0), (100.0, 50.0), (50.0, 100.0)]
        assert points == expected
    
    def test_parse_points_space_separated(self):
        """Test parsing space-separated points."""
        converter = PolygonConverter()
        
        points = converter._parse_points("0 0 100 50 50 100")
        expected = [(0.0, 0.0), (100.0, 50.0), (50.0, 100.0)]
        assert points == expected
    
    def test_parse_points_mixed_separators(self):
        """Test parsing points with mixed separators."""
        converter = PolygonConverter()
        
        points = converter._parse_points("0,0 100 50,50,100")
        expected = [(0.0, 0.0), (100.0, 50.0), (50.0, 100.0)]
        assert points == expected
    
    def test_parse_points_invalid(self):
        """Test parsing invalid points."""
        converter = PolygonConverter()
        
        points = converter._parse_points("0,0 invalid 100,50")
        # When invalid coordinate is encountered, parsing stops
        expected = [(0.0, 0.0)]  
        assert points == expected
    
    def test_convert_empty_polygon(self):
        """Test converting polygon with no points."""
        converter = PolygonConverter()
        element = ET.fromstring('<polygon points=""/>')
        context = Mock(spec=ConversionContext)
        
        result = converter.convert(element, context)
        assert "Empty polygon/polyline" in result
    
    def test_convert_insufficient_points(self):
        """Test converting polygon with insufficient points."""
        converter = PolygonConverter()
        element = ET.fromstring('<polygon points="0,0"/>')
        context = Mock(spec=ConversionContext)
        
        result = converter.convert(element, context)
        assert "Insufficient points" in result
    
    def test_convert_basic_polygon(self):
        """Test converting basic polygon."""
        converter = PolygonConverter()
        element = ET.fromstring('<polygon points="0,0 100,0 50,100"/>')
        
        # Mock context
        context = Mock(spec=ConversionContext)
        coord_system = Mock()
        coord_system.svg_to_emu.return_value = (0, 0)
        coord_system.svg_length_to_emu.side_effect = [9144000, 9144000]  # width=100, height=100
        context.coordinate_system = coord_system
        context.get_next_shape_id.return_value = 4001
        
        converter.generate_fill = Mock(return_value='<fill-mock/>')
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, context)
        
        # Check basic structure
        assert '<p:sp>' in result
        assert 'id="4001"' in result
        assert 'name="Polygon 4001"' in result
        
        # Check custom geometry
        assert '<a:custGeom>' in result
        assert '<a:pathLst>' in result
        assert '<a:moveTo>' in result
        assert '<a:lnTo>' in result
        assert '<a:close/>' in result  # Polygon should be closed
    
    def test_convert_basic_polyline(self):
        """Test converting basic polyline."""
        converter = PolygonConverter()
        element = ET.fromstring('<polyline points="0,0 50,50 100,0"/>')
        
        context = Mock(spec=ConversionContext)
        coord_system = Mock()
        coord_system.svg_to_emu.return_value = (0, 0)
        coord_system.svg_length_to_emu.side_effect = [9144000, 4572000]
        context.coordinate_system = coord_system
        context.get_next_shape_id.return_value = 4002
        
        converter.generate_fill = Mock(return_value='<fill-mock/>')
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, context)
        
        # Check basic structure
        assert 'name="Polyline 4002"' in result
        
        # Check that path is NOT closed for polyline
        assert '<a:close/>' not in result
    
    def test_generate_path(self):
        """Test path generation from points."""
        converter = PolygonConverter()
        
        points = [(0, 0), (100, 0), (50, 100)]
        min_x, min_y = 0, 0
        width, height = 100, 100
        
        path_xml = converter._generate_path(points, min_x, min_y, width, height, True)
        
        # Check path structure
        assert '<a:path w="21600" h="21600">' in path_xml
        assert '<a:moveTo>' in path_xml
        assert '<a:lnTo>' in path_xml
        assert '<a:close/>' in path_xml
        
        # Check that points are scaled to 21600 coordinate system
        assert '<a:pt x="0" y="0"/>' in path_xml  # First point
        assert '<a:pt x="21600" y="0"/>' in path_xml  # (100,0) scaled
        assert '<a:pt x="10800" y="21600"/>' in path_xml  # (50,100) scaled


class TestLineConverter:
    """Test LineConverter functionality."""
    
    def test_can_convert_line(self):
        """Test that converter recognizes line elements."""
        converter = LineConverter()
        
        element = ET.fromstring('<line x1="0" y1="0" x2="100" y2="100"/>')
        assert converter.can_convert(element) is True
    
    def test_can_convert_other_elements(self):
        """Test that converter rejects non-line elements."""
        converter = LineConverter()
        
        element = ET.fromstring('<rect width="100" height="50"/>')
        assert converter.can_convert(element) is False
        
        element = ET.fromstring('<polyline points="0,0 100,100"/>')
        assert converter.can_convert(element) is False
    
    def test_convert_zero_length_line(self):
        """Test converting zero-length line."""
        converter = LineConverter()
        element = ET.fromstring('<line x1="50" y1="50" x2="50" y2="50"/>')
        context = Mock(spec=ConversionContext)
        
        result = converter.convert(element, context)
        assert "Zero-length line" in result
    
    def test_convert_basic_line(self):
        """Test converting basic line."""
        converter = LineConverter()
        element = ET.fromstring('<line x1="0" y1="0" x2="100" y2="50"/>')
        
        # Mock context
        context = Mock(spec=ConversionContext)
        coord_system = Mock()
        coord_system.svg_to_emu.return_value = (0, 0)
        coord_system.svg_length_to_emu.side_effect = [9144000, 4572000]  # width=100, height=50
        context.coordinate_system = coord_system
        context.get_next_shape_id.return_value = 5001
        
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, context)
        
        # Check basic structure (connection shape for line)
        assert '<p:cxnSp>' in result
        assert '<p:nvCxnSpPr>' in result
        assert 'id="5001"' in result
        assert 'name="Line 5001"' in result
        
        # Check coordinates
        assert '<a:off x="0" y="0"/>' in result
        assert '<a:ext cx="9144000" cy="4572000"/>' in result
        
        # Check custom geometry with path
        assert '<a:custGeom>' in result
        assert '<a:pathLst>' in result
        assert '<a:moveTo>' in result
        assert '<a:lnTo>' in result
        
        # Line should have stroke but no fill
        converter.generate_stroke.assert_called_once()
    
    def test_convert_vertical_line(self):
        """Test converting vertical line."""
        converter = LineConverter()
        element = ET.fromstring('<line x1="50" y1="0" x2="50" y2="100"/>')
        
        context = Mock(spec=ConversionContext)
        coord_system = Mock()
        coord_system.svg_to_emu.return_value = (4572000, 0)  # x=50
        coord_system.svg_length_to_emu.side_effect = [1, 1]  # Both width and height become 1 (min values)
        context.coordinate_system = coord_system
        context.get_next_shape_id.return_value = 5002
        
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, context)
        
        # Both dimensions use minimum of 1 when zero
        assert '<a:ext cx="1" cy="1"/>' in result
    
    def test_convert_horizontal_line(self):
        """Test converting horizontal line."""
        converter = LineConverter()
        element = ET.fromstring('<line x1="0" y1="50" x2="100" y2="50"/>')
        
        context = Mock(spec=ConversionContext)
        coord_system = Mock()
        coord_system.svg_to_emu.return_value = (0, 4572000)  # y=50
        coord_system.svg_length_to_emu.side_effect = [9144000, 1]  # width=100, height=0->1
        context.coordinate_system = coord_system
        context.get_next_shape_id.return_value = 5003
        
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, context)
        
        # Should handle zero height by using minimum of 1
        assert '<a:ext cx="9144000" cy="1"/>' in result


class TestShapeConverterIntegration:
    """Test integration between shape converters and base converter functionality."""
    
    def test_rectangle_converter_supported_elements(self):
        """Test that RectangleConverter properly declares supported elements."""
        converter = RectangleConverter()
        assert converter.supported_elements == ['rect']
    
    def test_all_shape_converters_inherit_from_base(self):
        """Test that all shape converters inherit from BaseConverter."""
        from src.converters.base import BaseConverter
        
        assert issubclass(RectangleConverter, BaseConverter)
        assert issubclass(CircleConverter, BaseConverter)
        assert issubclass(EllipseConverter, BaseConverter)
        assert issubclass(PolygonConverter, BaseConverter)
        assert issubclass(LineConverter, BaseConverter)
    
    def test_supported_elements_completeness(self):
        """Test that all converters declare their supported elements."""
        converters = [
            (RectangleConverter(), ['rect']),
            (CircleConverter(), ['circle']),
            (EllipseConverter(), ['ellipse']),
            (PolygonConverter(), ['polygon', 'polyline']),
            (LineConverter(), ['line'])
        ]
        
        for converter, expected_elements in converters:
            assert converter.supported_elements == expected_elements