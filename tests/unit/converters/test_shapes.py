#!/usr/bin/env python3
"""
Unit tests for shape converter classes.

Tests the shape converter functionality including Rectangle, Circle, Ellipse, 
Polygon, Polyline, and Line converters.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from lxml import etree as ET
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
from core.services.conversion_services import ConversionServices


class TestRectangleConverter:
    """Test RectangleConverter functionality."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for converter testing."""
        services = Mock(spec=ConversionServices)

        # Mock unit converter to return actual numbers
        services.unit_converter = Mock()
        services.unit_converter.to_emu = Mock(return_value=914400)  # 1 inch in EMU

        # Mock color parser to return proper color info with numeric attributes
        services.color_parser = Mock()
        mock_color_info = Mock()
        mock_color_info.red = 255
        mock_color_info.green = 0
        mock_color_info.blue = 0
        services.color_parser.parse = Mock(return_value=mock_color_info)

        services.viewport_handler = Mock()
        services.viewport_handler = Mock()
        services.font_service = Mock()
        services.gradient_service = Mock()
        services.pattern_service = Mock()
        services.clip_service = Mock()
        return services

    def test_can_convert_rect(self, mock_services):
        """Test that converter recognizes rect elements."""
        converter = RectangleConverter(services=mock_services)
        
        element = ET.fromstring('<rect width="100" height="50"/>')
        assert converter.can_convert(element) is True
        
        # Test with namespace
        element = ET.fromstring('<svg:rect xmlns:svg="http://www.w3.org/2000/svg" width="100" height="50"/>')
        assert converter.can_convert(element) is True
    
    def test_can_convert_other_elements(self, mock_services):
        """Test that converter rejects non-rect elements."""
        converter = RectangleConverter(services=mock_services)
        
        element = ET.fromstring('<circle r="50"/>')
        assert converter.can_convert(element) is False
        
        element = ET.fromstring('<path d="M0,0 L100,100"/>')
        assert converter.can_convert(element) is False
    
    def test_convert_basic_rectangle(self, mock_services):
        """Test converting basic rectangle with minimal attributes."""
        converter = RectangleConverter(services=mock_services)
        element = ET.fromstring('<rect x="10" y="20" width="100" height="50"/>')
        
        # Create converter instance to access standardized tools
        from src.converters.base import BaseConverter
        class MockConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""
        mock_converter = MockConverter(services=mock_services)
        
        # Use UnitConverter for EMU calculations
        x_emu = mock_converter.unit_converter.to_emu('10px')
        y_emu = mock_converter.unit_converter.to_emu('20px') 
        width_emu = mock_converter.unit_converter.to_emu('100px')
        height_emu = mock_converter.unit_converter.to_emu('50px')
        
        # Mock context
        context = Mock(spec=ConversionContext)
        context.batch_convert_to_emu.return_value = {
            'x': x_emu,
            'y': y_emu,
            'width': width_emu,
            'height': height_emu,
            'rx': 0,
            'ry': 0
        }
        context.get_next_shape_id.return_value = 1001
        
        # Mock coordinate system for svg_to_emu conversion
        mock_coord_system = Mock()
        mock_coord_system.svg_to_emu.return_value = (x_emu, y_emu)
        # Use the actual unit converter for consistent EMU conversions
        mock_coord_system.svg_length_to_emu.side_effect = lambda value, direction: mock_converter.unit_converter.to_emu(f'{value}px')
        context.coordinate_system = mock_coord_system
        
        result = converter.convert(element, context)
        
        # Check basic structure
        assert '<p:sp>' in result
        assert '<p:nvSpPr>' in result
        assert 'id="1001"' in result
        assert 'name="Rectangle 1001"' in result
        
        # Check coordinates using tool-calculated values
        assert f'<a:off x="{x_emu}" y="{y_emu}"/>' in result
        assert f'<a:ext cx="{width_emu}" cy="{height_emu}"/>' in result
        
        # Check shape preset (regular rectangle)
        assert '<a:prstGeom prst="rect">' in result
        
        # Verify context method calls
        context.get_next_shape_id.assert_called_once()
    
    def test_convert_rectangle_with_defaults(self, mock_services):
        """Test converting rectangle with default values."""
        converter = RectangleConverter(services=mock_services)
        element = ET.fromstring('<rect/>')  # No attributes
        
        context = Mock(spec=ConversionContext)
        context.batch_convert_to_emu.return_value = {
            'x': 0, 'y': 0, 'width': 0, 'height': 0, 'rx': 0, 'ry': 0
        }
        context.get_next_shape_id.return_value = 1002
        
        # Mock coordinate system for svg_to_emu conversion  
        mock_coord_system = Mock()
        mock_coord_system.svg_to_emu.return_value = (0, 0)
        # Use the actual unit converter for consistent EMU conversions
        from src.converters.base import BaseConverter
        class MockConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""
        mock_converter = MockConverter(services=mock_services)
        mock_coord_system.svg_length_to_emu.side_effect = lambda value, direction: mock_converter.unit_converter.to_emu(f'{value}px')
        context.coordinate_system = mock_coord_system
        
        result = converter.convert(element, context)
        
        # Should handle defaults gracefully
        assert '<a:off x="0" y="0"/>' in result
        # Width and height should be converted to EMU (914400 = 1 inch in EMU)
        assert '<a:ext cx="914400" cy="914400"/>' in result
        assert 'Rectangle 1002' in result
    
    def test_convert_rectangle_with_styles(self, mock_services):
        """Test converting rectangle with style attributes."""
        converter = RectangleConverter(services=mock_services)
        element = ET.fromstring('''
            <rect x="0" y="0" width="100" height="100" 
                  fill="red" stroke="blue" stroke-width="2" opacity="0.8"/>
        ''')
        
        # Use UnitConverter for EMU calculation  
        from src.converters.base import BaseConverter
        class MockConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""
        mock_converter = MockConverter(services=mock_services)
        size_emu = mock_converter.unit_converter.to_emu('100px')
        
        context = Mock(spec=ConversionContext)
        context.batch_convert_to_emu.return_value = {
            'x': 0, 'y': 0, 'width': size_emu, 'height': size_emu, 'rx': 0, 'ry': 0
        }
        context.get_next_shape_id.return_value = 1003
        
        # Mock coordinate system for svg_to_emu conversion
        mock_coord_system = Mock()
        mock_coord_system.svg_to_emu.return_value = (0, 0)
        # Use the actual unit converter for consistent EMU conversions
        mock_coord_system.svg_length_to_emu.side_effect = lambda value, direction: mock_converter.unit_converter.to_emu(f'{value}px')
        context.coordinate_system = mock_coord_system
        
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
    
    def test_convert_rounded_rectangle(self, mock_services):
        """Test converting rectangle with rounded corners."""
        converter = RectangleConverter(services=mock_services)
        element = ET.fromstring('<rect x="0" y="0" width="100" height="50" rx="10" ry="5"/>')
        
        # Use UnitConverter for EMU calculations
        from src.converters.base import BaseConverter
        class MockConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""
        mock_converter = MockConverter(services=mock_services)
        width_emu = mock_converter.unit_converter.to_emu('100px')
        height_emu = mock_converter.unit_converter.to_emu('50px')
        rx_emu = mock_converter.unit_converter.to_emu('10px')
        ry_emu = mock_converter.unit_converter.to_emu('5px')
        
        context = Mock(spec=ConversionContext)
        context.batch_convert_to_emu.return_value = {
            'x': 0, 'y': 0, 'width': width_emu, 'height': height_emu, 'rx': rx_emu, 'ry': ry_emu
        }
        context.get_next_shape_id.return_value = 1004
        
        # Mock coordinate system for svg_to_emu conversion
        mock_coord_system = Mock()
        mock_coord_system.svg_to_emu.return_value = (0, 0)
        # Use the actual unit converter for consistent EMU conversions
        mock_coord_system.svg_length_to_emu.side_effect = lambda value, direction: mock_converter.unit_converter.to_emu(f'{value}px')
        context.coordinate_system = mock_coord_system
        
        result = converter.convert(element, context)
        
        # Should use rounded rectangle preset
        assert '<a:prstGeom prst="roundRect">' in result
        assert '<a:avLst>' in result
        assert '<a:gd name="adj"' in result


class TestCircleConverter:
    @pytest.fixture
    def mock_services(self):
        """Create mock services for converter testing."""
        services = Mock(spec=ConversionServices)

        # Mock unit converter to return actual numbers
        services.unit_converter = Mock()
        services.unit_converter.to_emu = Mock(return_value=914400)  # 1 inch in EMU

        # Mock color parser to return proper color info with numeric attributes
        services.color_parser = Mock()
        mock_color_info = Mock()
        mock_color_info.red = 255
        mock_color_info.green = 0
        mock_color_info.blue = 0
        services.color_parser.parse = Mock(return_value=mock_color_info)

        services.viewport_handler = Mock()
        return services
    """Test CircleConverter functionality."""
    
    def test_can_convert_circle(self, mock_services):
        """Test that converter recognizes circle elements."""
        converter = CircleConverter(services=mock_services)
        
        element = ET.fromstring('<circle r="50"/>')
        assert converter.can_convert(element) is True
        
        # Test with namespace
        element = ET.fromstring('<svg:circle xmlns:svg="http://www.w3.org/2000/svg" r="50"/>')
        assert converter.can_convert(element) is True
    
    def test_can_convert_other_elements(self, mock_services):
        """Test that converter rejects non-circle elements."""
        converter = CircleConverter(services=mock_services)
        
        element = ET.fromstring('<rect width="100" height="50"/>')
        assert converter.can_convert(element) is False
        
        element = ET.fromstring('<ellipse rx="50" ry="30"/>')
        assert converter.can_convert(element) is False
    
    def test_convert_basic_circle(self, mock_services):
        """Test converting basic circle."""
        converter = CircleConverter(services=mock_services)
        element = ET.fromstring('<circle cx="50" cy="50" r="25"/>')
        
        # Use UnitConverter for EMU calculations
        from src.converters.base import BaseConverter
        class MockConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""
        mock_converter = MockConverter(services=mock_services)
        center_offset_emu = mock_converter.unit_converter.to_emu('25px')
        diameter_emu = mock_converter.unit_converter.to_emu('50px')
        
        # Mock context and coordinate system
        context = Mock(spec=ConversionContext)
        coord_system = Mock()
        coord_system.svg_to_emu.return_value = (center_offset_emu, center_offset_emu)
        coord_system.svg_length_to_emu.return_value = diameter_emu
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
        assert f'<a:off x="{center_offset_emu}" y="{center_offset_emu}"/>' in result
        assert f'<a:ext cx="{diameter_emu}" cy="{diameter_emu}"/>' in result  # diameter x diameter
        
        # Check shape preset (ellipse for circle)
        assert '<a:prstGeom prst="ellipse">' in result
        
        # Verify coordinate system calls
        coord_system.svg_to_emu.assert_called_once_with(25, 25)  # cx-r, cy-r
        coord_system.svg_length_to_emu.assert_called_once_with(50, 'x')  # diameter
    
    def test_convert_circle_with_defaults(self, mock_services):
        """Test converting circle with default values."""
        converter = CircleConverter(services=mock_services)
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
    @pytest.fixture
    def mock_services(self):
        """Create mock services for converter testing."""
        services = Mock(spec=ConversionServices)

        # Mock unit converter to return actual numbers
        services.unit_converter = Mock()
        services.unit_converter.to_emu = Mock(return_value=914400)  # 1 inch in EMU

        # Mock color parser to return proper color info with numeric attributes
        services.color_parser = Mock()
        mock_color_info = Mock()
        mock_color_info.red = 255
        mock_color_info.green = 0
        mock_color_info.blue = 0
        services.color_parser.parse = Mock(return_value=mock_color_info)

        services.viewport_handler = Mock()
        return services
    """Test EllipseConverter functionality."""
    
    def test_can_convert_ellipse(self, mock_services):
        """Test that converter recognizes ellipse elements."""
        converter = EllipseConverter(services=mock_services)
        
        element = ET.fromstring('<ellipse rx="50" ry="30"/>')
        assert converter.can_convert(element) is True
    
    def test_can_convert_other_elements(self, mock_services):
        """Test that converter rejects non-ellipse elements."""
        converter = EllipseConverter(services=mock_services)
        
        element = ET.fromstring('<circle r="50"/>')
        assert converter.can_convert(element) is False
        
        element = ET.fromstring('<rect width="100" height="50"/>')
        assert converter.can_convert(element) is False
    
    def test_convert_basic_ellipse(self, mock_services):
        """Test converting basic ellipse."""
        converter = EllipseConverter(services=mock_services)
        element = ET.fromstring('<ellipse cx="100" cy="50" rx="60" ry="30"/>')
        
        # Use UnitConverter for EMU calculations
        from src.converters.base import BaseConverter
        class MockConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""
        mock_converter = MockConverter(services=mock_services)
        x_offset_emu = mock_converter.unit_converter.to_emu('40px')  # cx-rx = 100-60 = 40
        y_offset_emu = mock_converter.unit_converter.to_emu('20px')  # cy-ry = 50-30 = 20
        width_emu = mock_converter.unit_converter.to_emu('120px')    # 2*rx = 2*60 = 120
        height_emu = mock_converter.unit_converter.to_emu('60px')    # 2*ry = 2*30 = 60
        
        # Mock context and coordinate system
        context = Mock(spec=ConversionContext)
        coord_system = Mock()
        coord_system.svg_to_emu.return_value = (x_offset_emu, y_offset_emu)
        coord_system.svg_length_to_emu.side_effect = [width_emu, height_emu]
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
        assert f'<a:off x="{x_offset_emu}" y="{y_offset_emu}"/>' in result
        assert f'<a:ext cx="{width_emu}" cy="{height_emu}"/>' in result  # width x height
        
        # Check shape preset
        assert '<a:prstGeom prst="ellipse">' in result
        
        # Verify coordinate system calls
        coord_system.svg_to_emu.assert_called_once_with(40, 20)  # cx-rx, cy-ry


class TestPolygonConverter:
    @pytest.fixture
    def mock_services(self):
        """Create mock services for converter testing."""
        services = Mock(spec=ConversionServices)

        # Mock unit converter to return actual numbers
        services.unit_converter = Mock()
        services.unit_converter.to_emu = Mock(return_value=914400)  # 1 inch in EMU

        # Mock color parser to return proper color info with numeric attributes
        services.color_parser = Mock()
        mock_color_info = Mock()
        mock_color_info.red = 255
        mock_color_info.green = 0
        mock_color_info.blue = 0
        services.color_parser.parse = Mock(return_value=mock_color_info)

        services.viewport_handler = Mock()
        return services
    """Test PolygonConverter functionality."""
    
    def test_can_convert_polygon_and_polyline(self, mock_services):
        """Test that converter recognizes polygon and polyline elements."""
        converter = PolygonConverter(services=mock_services)
        
        element = ET.fromstring('<polygon points="0,0 100,0 50,100"/>')
        assert converter.can_convert(element) is True
        
        element = ET.fromstring('<polyline points="0,0 50,50 100,0"/>')
        assert converter.can_convert(element) is True
    
    def test_can_convert_other_elements(self, mock_services):
        """Test that converter rejects other elements."""
        converter = PolygonConverter(services=mock_services)
        
        element = ET.fromstring('<rect width="100" height="50"/>')
        assert converter.can_convert(element) is False
        
        element = ET.fromstring('<circle r="50"/>')
        assert converter.can_convert(element) is False
    
    
    def test_convert_empty_polygon(self, mock_services):
        """Test converting polygon with no points."""
        converter = PolygonConverter(services=mock_services)
        element = ET.fromstring('<polygon points=""/>')
        context = Mock(spec=ConversionContext)
        
        result = converter.convert(element, context)
        assert "Invalid polygon: insufficient points" in result
    
    def test_convert_insufficient_points(self, mock_services):
        """Test converting polygon with insufficient points."""
        converter = PolygonConverter(services=mock_services)
        element = ET.fromstring('<polygon points="0,0"/>')
        context = Mock(spec=ConversionContext)
        
        result = converter.convert(element, context)
        assert "Invalid polygon: insufficient points" in result
    
    def test_convert_basic_polygon(self, mock_services):
        """Test converting basic polygon."""
        converter = PolygonConverter(services=mock_services)
        element = ET.fromstring('<polygon points="0,0 100,0 50,100"/>')
        
        # Use UnitConverter for EMU calculations
        from src.converters.base import BaseConverter
        class MockConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""
        mock_converter = MockConverter(services=mock_services)
        size_emu = mock_converter.unit_converter.to_emu('100px')
        
        # Mock context
        context = Mock(spec=ConversionContext)
        coord_system = Mock()
        coord_system.svg_to_emu.return_value = (0, 0)
        coord_system.svg_length_to_emu.side_effect = [size_emu, size_emu]
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
    
    def test_convert_basic_polyline(self, mock_services):
        """Test converting basic polyline."""
        converter = PolygonConverter(services=mock_services)
        element = ET.fromstring('<polyline points="0,0 50,50 100,0"/>')
        
        # Use UnitConverter for EMU calculations
        from src.converters.base import BaseConverter
        class MockConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""
        mock_converter = MockConverter(services=mock_services)
        width_emu = mock_converter.unit_converter.to_emu('100px')
        height_emu = mock_converter.unit_converter.to_emu('50px')
        
        context = Mock(spec=ConversionContext)
        coord_system = Mock()
        coord_system.svg_to_emu.return_value = (0, 0)
        coord_system.svg_length_to_emu.side_effect = [width_emu, height_emu]
        context.coordinate_system = coord_system
        context.get_next_shape_id.return_value = 4002
        
        converter.generate_fill = Mock(return_value='<fill-mock/>')
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, context)
        
        # Check basic structure
        assert 'name="Polyline 4002"' in result
        
        # Check that path is NOT closed for polyline
        assert '<a:close/>' not in result
    
    # Note: test_generate_path removed as _generate_path is an internal implementation detail
    # that has been refactored in the enhanced converter. Tests now focus on public interface.


class TestLineConverter:
    @pytest.fixture
    def mock_services(self):
        """Create mock services for converter testing."""
        services = Mock(spec=ConversionServices)

        # Mock unit converter to return actual numbers
        services.unit_converter = Mock()
        services.unit_converter.to_emu = Mock(return_value=914400)  # 1 inch in EMU

        # Mock color parser to return proper color info with numeric attributes
        services.color_parser = Mock()
        mock_color_info = Mock()
        mock_color_info.red = 255
        mock_color_info.green = 0
        mock_color_info.blue = 0
        services.color_parser.parse = Mock(return_value=mock_color_info)

        services.viewport_handler = Mock()
        return services
    """Test LineConverter functionality."""
    
    def test_can_convert_line(self, mock_services):
        """Test that converter recognizes line elements."""
        converter = LineConverter(services=mock_services)
        
        element = ET.fromstring('<line x1="0" y1="0" x2="100" y2="100"/>')
        assert converter.can_convert(element) is True
    
    def test_can_convert_other_elements(self, mock_services):
        """Test that converter rejects non-line elements."""
        converter = LineConverter(services=mock_services)
        
        element = ET.fromstring('<rect width="100" height="50"/>')
        assert converter.can_convert(element) is False
        
        element = ET.fromstring('<polyline points="0,0 100,100"/>')
        assert converter.can_convert(element) is False
    
    def test_convert_zero_length_line(self, mock_services):
        """Test converting zero-length line produces valid DrawingML."""
        converter = LineConverter(services=mock_services)
        element = ET.fromstring('<line x1="50" y1="50" x2="50" y2="50"/>')
        context = Mock(spec=ConversionContext)
        context.get_next_shape_id = Mock(return_value=1002)

        # Mock coordinate system
        mock_coord_system = Mock()
        mock_coord_system.svg_to_emu.return_value = (0, 0)
        mock_coord_system.svg_length_to_emu.return_value = Mock()
        context.coordinate_system = mock_coord_system

        result = converter.convert(element, context)
        # Should generate valid DrawingML even for zero-length lines
        assert '<p:cxnSp>' in result
        assert isinstance(result, str)
    
    def test_convert_basic_line(self, mock_services):
        """Test converting basic line."""
        converter = LineConverter(services=mock_services)
        element = ET.fromstring('<line x1="0" y1="0" x2="100" y2="50"/>')
        
        # Use UnitConverter for EMU calculations
        from src.converters.base import BaseConverter
        class MockConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""
        mock_converter = MockConverter(services=mock_services)
        width_emu = mock_converter.unit_converter.to_emu('100px')
        height_emu = mock_converter.unit_converter.to_emu('50px')
        
        # Mock context
        context = Mock(spec=ConversionContext)
        coord_system = Mock()
        coord_system.svg_to_emu.return_value = (0, 0)
        coord_system.svg_length_to_emu.side_effect = [width_emu, height_emu]
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
        assert f'<a:ext cx="{width_emu}" cy="{height_emu}"/>' in result
        
        # Check custom geometry with path
        assert '<a:custGeom>' in result
        assert '<a:pathLst>' in result
        assert '<a:moveTo>' in result
        assert '<a:lnTo>' in result
        
        # Line should have stroke but no fill
        converter.generate_stroke.assert_called_once()
    
    def test_convert_vertical_line(self, mock_services):
        """Test converting vertical line."""
        converter = LineConverter(services=mock_services)
        element = ET.fromstring('<line x1="50" y1="0" x2="50" y2="100"/>')
        
        # Use UnitConverter for EMU calculations
        from src.converters.base import BaseConverter
        class MockConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""
        mock_converter = MockConverter(services=mock_services)
        x_emu = mock_converter.unit_converter.to_emu('50px')
        
        context = Mock(spec=ConversionContext)
        coord_system = Mock()
        coord_system.svg_to_emu.return_value = (x_emu, 0)
        coord_system.svg_length_to_emu.side_effect = [1, 1]  # Both width and height become 1 (min values)
        context.coordinate_system = coord_system
        context.get_next_shape_id.return_value = 5002
        
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, context)
        
        # Both dimensions use minimum of 1 when zero
        assert '<a:ext cx="1" cy="1"/>' in result
    
    def test_convert_horizontal_line(self, mock_services):
        """Test converting horizontal line."""
        converter = LineConverter(services=mock_services)
        element = ET.fromstring('<line x1="0" y1="50" x2="100" y2="50"/>')
        
        # Use UnitConverter for EMU calculations
        from src.converters.base import BaseConverter
        class MockConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""
        mock_converter = MockConverter(services=mock_services)
        y_emu = mock_converter.unit_converter.to_emu('50px')
        width_emu = mock_converter.unit_converter.to_emu('100px')
        
        context = Mock(spec=ConversionContext)
        coord_system = Mock()
        coord_system.svg_to_emu.return_value = (0, y_emu)
        coord_system.svg_length_to_emu.side_effect = [width_emu, 1]  # width=100, height=0->1
        context.coordinate_system = coord_system
        context.get_next_shape_id.return_value = 5003
        
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, context)
        
        # Should handle zero height by using minimum of 1
        assert f'<a:ext cx="{width_emu}" cy="1"/>' in result


class TestShapeConverterIntegration:
    @pytest.fixture
    def mock_services(self):
        """Create mock services for converter testing."""
        services = Mock(spec=ConversionServices)

        # Mock unit converter to return actual numbers
        services.unit_converter = Mock()
        services.unit_converter.to_emu = Mock(return_value=914400)  # 1 inch in EMU

        # Mock color parser to return proper color info with numeric attributes
        services.color_parser = Mock()
        mock_color_info = Mock()
        mock_color_info.red = 255
        mock_color_info.green = 0
        mock_color_info.blue = 0
        services.color_parser.parse = Mock(return_value=mock_color_info)

        services.viewport_handler = Mock()
        return services
    """Test integration between shape converters and base converter functionality."""
    
    def test_rectangle_converter_supported_elements(self, mock_services):
        """Test that RectangleConverter properly declares supported elements."""
        converter = RectangleConverter(services=mock_services)
        assert converter.supported_elements == ['rect']
    
    def test_all_shape_converters_inherit_from_base(self, mock_services):
        """Test that all shape converters inherit from BaseConverter."""
        from src.converters.base import BaseConverter
        
        assert issubclass(RectangleConverter, BaseConverter)
        assert issubclass(CircleConverter, BaseConverter)
        assert issubclass(EllipseConverter, BaseConverter)
        assert issubclass(PolygonConverter, BaseConverter)
        assert issubclass(LineConverter, BaseConverter)
    
    def test_supported_elements_completeness(self, mock_services):
        """Test that all converters declare their supported elements."""
        converters = [
            (RectangleConverter(services=mock_services), ['rect']),
            (CircleConverter(services=mock_services), ['circle']),
            (EllipseConverter(services=mock_services), ['ellipse']),
            (PolygonConverter(services=mock_services), ['polygon', 'polyline']),
            (LineConverter(services=mock_services), ['line'])
        ]
        
        for converter, expected_elements in converters:
            assert converter.supported_elements == expected_elements