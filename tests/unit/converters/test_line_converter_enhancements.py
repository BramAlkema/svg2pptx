#!/usr/bin/env python3
"""
Enhanced unit tests for LineConverter improvements.

Tests the enhanced LineConverter functionality including:
- Universal utilities integration (UnitConverter, ViewportResolver) 
- Connection shape optimization
- Line markers integration
- Edge cases and error handling
- Coordinate system improvements
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.converters.shapes import LineConverter
from src.converters.base import ConversionContext


class TestLineConverterEnhancements:
    """Test enhanced LineConverter functionality with universal utilities integration."""
    
    @pytest.fixture
    def converter(self):
        """Create LineConverter instance for testing."""
        return LineConverter()
    
    @pytest.fixture
    def mock_context(self):
        """Create mock ConversionContext with universal utilities."""
        context = Mock(spec=ConversionContext)
        
        # Mock coordinate system
        coord_system = Mock()
        coord_system.svg_to_emu.return_value = (0, 0)
        coord_system.svg_length_to_emu.return_value = 914400  # 100px in EMUs
        context.coordinate_system = coord_system
        
        # Mock universal utilities integration
        context.get_next_shape_id.return_value = 1001
        
        return context

    def test_unit_converter_integration(self, converter, mock_context):
        """Test LineConverter integration with UnitConverter for various units."""
        element = ET.fromstring('<line x1="10mm" y1="0.5in" x2="50pt" y2="100px"/>')
        
        # Mock UnitConverter responses for different units
        mock_context.coordinate_system.svg_length_to_emu.side_effect = [
            365760,   # ~10mm in EMUs  
            457200    # ~50pt in EMUs
        ]
        mock_context.coordinate_system.svg_to_emu.return_value = (365760, 457200)
        
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, mock_context)
        
        # Verify UnitConverter was used for coordinate conversion
        assert mock_context.coordinate_system.svg_to_emu.called
        assert mock_context.coordinate_system.svg_length_to_emu.called
        
        # Check that coordinates are properly converted
        assert '<a:off x="365760" y="457200"/>' in result
        assert '<a:ext cx="365760" cy="457200"/>' in result

    def test_viewport_resolver_integration(self, converter, mock_context):
        """Test LineConverter integration with ViewportResolver for coordinate mapping."""
        element = ET.fromstring('<line x1="0" y1="0" x2="100" y2="100"/>')
        
        # Mock ViewportResolver integration through context
        viewport_mapping = Mock()
        viewport_mapping.svg_to_emu.return_value = (914400, 914400)  # Mapped coordinates
        mock_context.viewport_mapping = viewport_mapping
        
        # Update converter to use ViewportResolver if available
        with patch.object(converter, '_convert_svg_to_drawingml_coords') as mock_convert:
            mock_convert.return_value = (914400, 914400)
            converter.generate_stroke = Mock(return_value='<stroke-mock/>')
            
            result = converter.convert(element, mock_context)
            
            # Verify viewport-aware coordinate conversion was attempted
            mock_convert.assert_called()

    def test_connection_shape_vs_regular_shape(self, converter, mock_context):
        """Test LineConverter choosing between connection shape and regular shape."""
        
        # Test connection shape generation (default behavior)
        element = ET.fromstring('<line x1="0" y1="0" x2="100" y2="100"/>')
        mock_context.coordinate_system.svg_length_to_emu.side_effect = [914400, 914400]
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, mock_context)
        
        # Should generate connection shape for lines
        assert '<p:cxnSp>' in result
        assert '<p:nvCxnSpPr>' in result
        assert '<p:cNvCxnSpPr/>' in result
        
        # Should not generate regular shape
        assert '<p:sp>' not in result
        assert '<p:nvSpPr>' not in result

    def test_line_direction_detection(self, converter, mock_context):
        """Test line direction detection for path generation."""
        test_cases = [
            # (x1, y1, x2, y2, expected_start, expected_end)
            (0, 0, 100, 100, (0, 0), (21600, 21600)),        # Top-left to bottom-right
            (100, 0, 0, 100, (21600, 0), (0, 21600)),        # Top-right to bottom-left  
            (0, 100, 100, 0, (0, 21600), (21600, 0)),        # Bottom-left to top-right
            (100, 100, 0, 0, (21600, 21600), (0, 0)),        # Bottom-right to top-left
        ]
        
        for x1, y1, x2, y2, expected_start, expected_end in test_cases:
            element = ET.fromstring(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
            
            mock_context.coordinate_system.svg_length_to_emu.side_effect = [914400, 914400]
            mock_context.get_next_shape_id.return_value = 1001
            converter.generate_stroke = Mock(return_value='<stroke-mock/>')
            
            result = converter.convert(element, mock_context)
            
            # Check path contains correct start and end points
            assert f'<a:pt x="{expected_start[0]}" y="{expected_start[1]}"/>' in result
            assert f'<a:pt x="{expected_end[0]}" y="{expected_end[1]}"/>' in result

    def test_line_markers_integration(self, converter, mock_context):
        """Test LineConverter integration with line markers (arrows)."""
        element = ET.fromstring('''
            <line x1="0" y1="0" x2="100" y2="100" 
                  marker-start="url(#arrow-start)" 
                  marker-end="url(#arrow-end)"/>
        ''')
        
        mock_context.coordinate_system.svg_length_to_emu.side_effect = [914400, 914400]
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        # Mock marker processing (would be handled by markers converter integration)
        with patch.object(converter, 'get_attribute_with_style') as mock_get_attr:
            mock_get_attr.side_effect = lambda elem, attr, default: {
                'stroke': 'black',
                'stroke-width': '1',
                'opacity': '1',
                'stroke-opacity': '1',
                'marker-start': 'url(#arrow-start)',
                'marker-end': 'url(#arrow-end)'
            }.get(attr, default)
            
            result = converter.convert(element, mock_context)
            
            # Verify stroke generation was called (markers would be added by stroke processing)
            converter.generate_stroke.assert_called_once_with('black', '1', '1', mock_context)

    def test_edge_case_zero_width_line(self, converter, mock_context):
        """Test handling of zero-width line (vertical line)."""
        element = ET.fromstring('<line x1="50" y1="0" x2="50" y2="100"/>')
        
        # Width is 0, height is 100
        mock_context.coordinate_system.svg_to_emu.return_value = (457200, 0)  # x=50px, y=0
        # Height conversion should be called only once since width=0 doesn't call svg_length_to_emu
        mock_context.coordinate_system.svg_length_to_emu.return_value = 914400  # height=100px
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, mock_context)
        
        # Should handle zero width by using minimum value of 1, but preserve height
        assert '<a:ext cx="1" cy="914400"/>' in result
        assert '<p:cxnSp>' in result

    def test_edge_case_zero_height_line(self, converter, mock_context):
        """Test handling of zero-height line (horizontal line).""" 
        element = ET.fromstring('<line x1="0" y1="50" x2="100" y2="50"/>')
        
        # Width is 100, height is 0
        mock_context.coordinate_system.svg_to_emu.return_value = (0, 457200)  # x=0, y=50px
        mock_context.coordinate_system.svg_length_to_emu.side_effect = [914400, 1]  # width=100px, height=0->1
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, mock_context)
        
        # Should handle zero height by using minimum value of 1
        assert '<a:ext cx="914400" cy="1"/>' in result
        assert '<p:cxnSp>' in result

    def test_edge_case_negative_coordinates(self, converter, mock_context):
        """Test handling of negative coordinates."""
        element = ET.fromstring('<line x1="-50" y1="-25" x2="50" y2="75"/>')
        
        # Bounding box: x=-50, y=-25, width=100, height=100
        mock_context.coordinate_system.svg_to_emu.return_value = (-457200, -228600)
        mock_context.coordinate_system.svg_length_to_emu.side_effect = [914400, 914400]
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, mock_context)
        
        # Should handle negative coordinates properly
        assert '<a:off x="-457200" y="-228600"/>' in result
        assert '<a:ext cx="914400" cy="914400"/>' in result

    def test_edge_case_extreme_coordinates(self, converter, mock_context):
        """Test handling of extremely large coordinates."""
        element = ET.fromstring('<line x1="0" y1="0" x2="10000" y2="10000"/>')
        
        large_emu = 91440000  # 10000px in EMUs
        mock_context.coordinate_system.svg_to_emu.return_value = (0, 0)
        mock_context.coordinate_system.svg_length_to_emu.side_effect = [large_emu, large_emu]
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, mock_context)
        
        # Should handle large coordinates without error
        assert f'<a:ext cx="{large_emu}" cy="{large_emu}"/>' in result
        assert 'Line 1001' in result

    def test_edge_case_invalid_coordinates(self, converter, mock_context):
        """Test handling of invalid/missing coordinates.""" 
        element = ET.fromstring('<line x2="100" y2="100"/>')  # Missing x1, y1
        
        mock_context.coordinate_system.svg_to_emu.return_value = (0, 0)
        mock_context.coordinate_system.svg_length_to_emu.side_effect = [914400, 914400]
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, mock_context)
        
        # Should use default values (0) for missing coordinates
        assert '<a:off x="0" y="0"/>' in result
        assert 'Line 1001' in result

    def test_performance_with_complex_styling(self, converter, mock_context):
        """Test performance with complex styling attributes."""
        element = ET.fromstring('''
            <line x1="0" y1="0" x2="100" y2="100"
                  stroke="rgb(255,128,64)" 
                  stroke-width="5px"
                  stroke-dasharray="10,5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  opacity="0.8"
                  transform="rotate(45 50 50) scale(2)"
                  style="stroke-opacity:0.5"/>
        ''')
        
        mock_context.coordinate_system.svg_length_to_emu.side_effect = [914400, 914400]
        converter.generate_stroke = Mock(return_value='<complex-stroke/>')
        
        result = converter.convert(element, mock_context)
        
        # Should handle complex styling without performance issues
        assert 'Line 1001' in result
        assert '<complex-stroke/>' in result
        
        # Verify stroke generation was called with proper opacity handling
        converter.generate_stroke.assert_called_once()

    def test_error_handling_malformed_element(self, converter, mock_context):
        """Test error handling with malformed line element."""
        element = ET.fromstring('<line x1="invalid" y1="0" x2="100" y2="not-a-number"/>')
        
        # Should handle parse errors gracefully
        mock_context.coordinate_system.svg_to_emu.return_value = (0, 0)
        mock_context.coordinate_system.svg_length_to_emu.side_effect = [914400, 0]
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        # Should not raise exception
        result = converter.convert(element, mock_context)
        assert 'Line 1001' in result

    def test_universal_utilities_method_integration(self, converter):
        """Test that LineConverter properly inherits universal utilities from BaseConverter."""
        # These methods should be available from BaseConverter
        assert hasattr(converter, 'unit_converter')
        assert hasattr(converter, 'color_parser')
        assert hasattr(converter, 'transform_parser')
        assert hasattr(converter, 'viewport_resolver')
        
        # Should be able to access utility methods
        assert hasattr(converter, 'parse_length')
        assert hasattr(converter, 'get_attribute_with_style')
        assert hasattr(converter, 'generate_stroke')

    def test_backward_compatibility(self, converter, mock_context):
        """Test that enhancements maintain backward compatibility."""
        # Test with same basic line from original test suite
        element = ET.fromstring('<line x1="0" y1="0" x2="100" y2="50"/>')
        
        mock_context.coordinate_system.svg_to_emu.return_value = (0, 0)
        mock_context.coordinate_system.svg_length_to_emu.side_effect = [914400, 457200]
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, mock_context)
        
        # Should maintain same basic structure as original implementation
        assert '<p:cxnSp>' in result
        assert '<p:nvCxnSpPr>' in result
        assert 'id="1001"' in result
        assert 'name="Line 1001"' in result
        assert '<a:custGeom>' in result
        assert '<a:pathLst>' in result
        assert '<a:moveTo>' in result
        assert '<a:lnTo>' in result


class TestLineConverterCoordinateSystem:
    """Test LineConverter coordinate system handling improvements."""
    
    def test_coordinate_system_consistency(self):
        """Test coordinate system consistency with other converters."""
        converter = LineConverter()
        element = ET.fromstring('<line x1="0" y1="0" x2="100" y2="100"/>')
        
        context = Mock(spec=ConversionContext)
        coord_system = Mock()
        coord_system.svg_to_emu.return_value = (0, 0)
        coord_system.svg_length_to_emu.side_effect = [914400, 914400]
        context.coordinate_system = coord_system
        context.get_next_shape_id.return_value = 2001
        
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, context)
        
        # Verify coordinate system methods called correctly
        coord_system.svg_to_emu.assert_called_once_with(0, 0)  # min_x, min_y
        assert coord_system.svg_length_to_emu.call_count == 2  # width and height

    def test_bounding_box_calculation_accuracy(self):
        """Test accurate bounding box calculation for various line orientations."""
        converter = LineConverter()
        
        test_cases = [
            # (x1, y1, x2, y2, expected_min_x, expected_min_y, expected_width, expected_height)
            (0, 0, 100, 100, 0, 0, 100, 100),
            (100, 0, 0, 100, 0, 0, 100, 100),
            (50, 25, 150, 75, 50, 25, 100, 50),
            (200, 300, 100, 200, 100, 200, 100, 100),
        ]
        
        for x1, y1, x2, y2, exp_min_x, exp_min_y, exp_width, exp_height in test_cases:
            element = ET.fromstring(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
            
            context = Mock(spec=ConversionContext)
            coord_system = Mock()
            coord_system.svg_to_emu.return_value = (exp_min_x * 9144, exp_min_y * 9144)  # Mock EMU conversion
            coord_system.svg_length_to_emu.side_effect = [exp_width * 9144, exp_height * 9144]
            context.coordinate_system = coord_system
            context.get_next_shape_id.return_value = 3001
            
            converter.generate_stroke = Mock(return_value='<stroke-mock/>')
            
            result = converter.convert(element, context)
            
            # Verify correct bounding box calculation
            coord_system.svg_to_emu.assert_called_with(exp_min_x, exp_min_y)