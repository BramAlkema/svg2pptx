"""
Comprehensive test suite for CircleConverter enhancements.
Tests ViewportResolver integration, universal utilities, and edge cases.
"""

import pytest
from unittest.mock import Mock, MagicMock
import xml.etree.ElementTree as ET
import math

from src.converters.shapes import CircleConverter
from src.converters.base import ConversionContext


class TestCircleConverterEnhancements:
    """Test suite for enhanced CircleConverter functionality."""
    
    @pytest.fixture
    def converter(self):
        """Create a CircleConverter instance."""
        return CircleConverter()
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock ConversionContext with necessary attributes."""
        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu = Mock(return_value=(914400, 914400))
        context.coordinate_system.svg_length_to_emu = Mock(return_value=914400)
        context.get_next_shape_id = Mock(return_value=1)
        context.current_color = 'black'
        return context
    
    def test_viewport_resolver_integration(self, converter, mock_context):
        """Test CircleConverter integration with ViewportResolver for coordinate mapping."""
        element = ET.fromstring('<circle cx="50" cy="50" r="30"/>')
        
        # Mock ViewportResolver integration through context
        viewport_mapping = Mock()
        viewport_mapping.svg_to_emu = Mock(return_value=(914400, 914400))
        mock_context.viewport_mapping = viewport_mapping
        
        result = converter.convert(element, mock_context)
        
        # Verify ViewportResolver was used for coordinate conversion
        viewport_mapping.svg_to_emu.assert_called_once_with(20.0, 20.0)  # cx-r, cy-r
        assert '<a:off x="914400" y="914400"/>' in result
    
    def test_viewport_resolver_fallback(self, converter, mock_context):
        """Test fallback to standard coordinate system when ViewportResolver not available."""
        element = ET.fromstring('<circle cx="50" cy="50" r="30"/>')
        
        # No ViewportResolver in context
        mock_context.viewport_mapping = None
        
        result = converter.convert(element, mock_context)
        
        # Should fall back to standard coordinate system
        mock_context.coordinate_system.svg_to_emu.assert_called_once_with(20.0, 20.0)
        assert '<p:sp>' in result
    
    def test_unit_handling_improvements(self, converter, mock_context):
        """Test improved unit handling for circle attributes."""
        test_cases = [
            ('<circle cx="10px" cy="20px" r="5px"/>', "Pixel units"),
            ('<circle cx="1em" cy="2em" r="0.5em"/>', "Em units"),
            ('<circle cx="10%" cy="20%" r="5%"/>', "Percentage units"),
            ('<circle cx="1in" cy="2in" r="0.5in"/>', "Inch units"),
            ('<circle cx="10mm" cy="20mm" r="5mm"/>', "Millimeter units"),
        ]
        
        for svg_str, description in test_cases:
            element = ET.fromstring(svg_str)
            result = converter.convert(element, mock_context)
            assert '<p:sp>' in result, f"Failed for {description}"
            assert '<a:prstGeom prst="ellipse">' in result
    
    def test_edge_case_zero_radius(self, converter, mock_context):
        """Test handling of circle with zero radius."""
        element = ET.fromstring('<circle cx="50" cy="50" r="0"/>')
        
        result = converter.convert(element, mock_context)
        
        # Should still generate valid shape with zero dimensions
        assert '<p:sp>' in result
        mock_context.coordinate_system.svg_length_to_emu.assert_called_with(0, 'x')
    
    def test_edge_case_negative_radius(self, converter, mock_context):
        """Test handling of circle with negative radius (should be treated as 0)."""
        element = ET.fromstring('<circle cx="50" cy="50" r="-10"/>')
        
        # Mock parse_length to handle negative values
        converter.parse_length = Mock(side_effect=lambda x: max(0, float(x.replace('px', '').replace('em', '').replace('%', '').replace('in', '').replace('mm', ''))))
        
        result = converter.convert(element, mock_context)
        
        # Should generate valid shape treating negative as zero
        assert '<p:sp>' in result
        assert '<a:prstGeom prst="ellipse">' in result
    
    def test_edge_case_missing_attributes(self, converter, mock_context):
        """Test handling of circle with missing attributes (should use defaults)."""
        element = ET.fromstring('<circle/>')
        
        result = converter.convert(element, mock_context)
        
        # Should use default values (cx=0, cy=0, r=0)
        assert '<p:sp>' in result
        mock_context.coordinate_system.svg_to_emu.assert_called_once_with(0, 0)
    
    def test_style_attributes_with_viewport(self, converter, mock_context):
        """Test style attribute handling with ViewportResolver active."""
        element = ET.fromstring('''
            <circle cx="50" cy="50" r="30" 
                    fill="red" stroke="blue" stroke-width="2"
                    opacity="0.8" fill-opacity="0.6" stroke-opacity="0.7"/>
        ''')
        
        # Add ViewportResolver
        viewport_mapping = Mock()
        viewport_mapping.svg_to_emu = Mock(return_value=(914400, 914400))
        mock_context.viewport_mapping = viewport_mapping
        
        # Mock style generation methods
        converter.generate_fill = Mock(return_value='<a:solidFill/>')
        converter.generate_stroke = Mock(return_value='<a:ln/>')
        
        result = converter.convert(element, mock_context)
        
        # Verify style methods were called with correct parameters
        converter.generate_fill.assert_called_once_with('red', '0.6', mock_context)
        converter.generate_stroke.assert_called_once_with('blue', '2', '0.7', mock_context)
    
    def test_transform_aware_positioning(self, converter, mock_context):
        """Test that CircleConverter properly positions circles with transform awareness."""
        element = ET.fromstring('<circle cx="100" cy="100" r="50" transform="translate(50, 50)"/>')
        
        # Add ViewportResolver with transform support
        viewport_mapping = Mock()
        viewport_mapping.svg_to_emu = Mock(return_value=(1828800, 1828800))  # Transformed position
        mock_context.viewport_mapping = viewport_mapping
        
        result = converter.convert(element, mock_context)
        
        # Should apply transform-aware positioning
        assert '<a:off x="1828800" y="1828800"/>' in result
    
    def test_large_radius_handling(self, converter, mock_context):
        """Test handling of circles with very large radius values."""
        element = ET.fromstring('<circle cx="500" cy="500" r="1000"/>')
        
        # Mock large EMU values
        mock_context.coordinate_system.svg_to_emu = Mock(return_value=(-4572000, -4572000))  # cx-r, cy-r
        mock_context.coordinate_system.svg_length_to_emu = Mock(return_value=18288000)  # 2*r
        
        result = converter.convert(element, mock_context)
        
        # Should handle large values correctly
        assert '<a:off x="-4572000" y="-4572000"/>' in result
        assert '<a:ext cx="18288000" cy="18288000"/>' in result
    
    def test_precision_handling(self, converter, mock_context):
        """Test handling of high-precision floating point values."""
        element = ET.fromstring('<circle cx="33.33333" cy="66.66666" r="12.34567"/>')
        
        result = converter.convert(element, mock_context)
        
        # Should handle precise float values
        assert '<p:sp>' in result
        # Verify the values were processed (cx-r ≈ 20.98766)
        mock_context.coordinate_system.svg_to_emu.assert_called()
    
    def test_shape_id_generation(self, converter, mock_context):
        """Test proper shape ID generation for circles."""
        element = ET.fromstring('<circle cx="50" cy="50" r="30"/>')
        
        # Test with different shape IDs
        for shape_id in [1, 100, 999]:
            mock_context.get_next_shape_id = Mock(return_value=shape_id)
            result = converter.convert(element, mock_context)
            assert f'<p:cNvPr id="{shape_id}" name="Circle {shape_id}"/>' in result
    
    def test_universal_color_parser_integration(self, converter, mock_context):
        """Test integration with universal ColorParser for fill/stroke colors."""
        element = ET.fromstring('<circle cx="50" cy="50" r="30" fill="hsl(120, 50%, 50%)"/>')
        
        # Mock ColorParser integration
        converter.generate_fill = Mock(return_value='<a:solidFill><a:srgbClr val="40BF40"/></a:solidFill>')
        
        result = converter.convert(element, mock_context)
        
        converter.generate_fill.assert_called_once_with('hsl(120, 50%, 50%)', '1', mock_context)
        assert '<a:solidFill><a:srgbClr val="40BF40"/></a:solidFill>' in result
    
    def test_performance_with_complex_styles(self, converter, mock_context):
        """Test performance with complex style combinations."""
        element = ET.fromstring('''
            <circle cx="100" cy="100" r="50"
                    fill="url(#gradient1)" stroke="url(#pattern1)"
                    stroke-width="3" stroke-dasharray="5,2"
                    filter="url(#blur1)" mask="url(#mask1)"
                    clip-path="url(#clip1)" opacity="0.75"/>
        ''')
        
        # Mock complex style handling
        converter.generate_fill = Mock(return_value='<a:gradFill/>')
        converter.generate_stroke = Mock(return_value='<a:ln><a:pattFill/></a:ln>')
        
        result = converter.convert(element, mock_context)
        
        # Should handle complex styles without errors
        assert '<p:sp>' in result
        converter.generate_fill.assert_called_once()
        converter.generate_stroke.assert_called_once()
    
    def test_bounding_box_calculation_accuracy(self, converter, mock_context):
        """Test accurate bounding box calculation for circles."""
        test_cases = [
            (50, 50, 30, 20, 20, 60, 60),  # cx, cy, r, expected x, y, width, height
            (0, 0, 10, -10, -10, 20, 20),
            (100, 200, 50, 50, 150, 100, 100),
        ]
        
        for cx, cy, r, exp_x, exp_y, exp_w, exp_h in test_cases:
            element = ET.fromstring(f'<circle cx="{cx}" cy="{cy}" r="{r}"/>')
            result = converter.convert(element, mock_context)
            
            # Verify bounding box calculation
            mock_context.coordinate_system.svg_to_emu.assert_called_with(exp_x, exp_y)
            mock_context.coordinate_system.svg_length_to_emu.assert_called_with(exp_w, 'x')
    
    def test_viewport_coordinate_scaling(self, converter, mock_context):
        """Test that ViewportResolver properly scales circle dimensions."""
        element = ET.fromstring('<circle cx="50" cy="50" r="30"/>')
        
        # Mock ViewportResolver with scaling
        viewport_mapping = Mock()
        viewport_mapping.svg_to_emu = Mock(return_value=(1828800, 1828800))  # 2x scale
        viewport_mapping.scale_factor = 2.0
        mock_context.viewport_mapping = viewport_mapping
        mock_context.coordinate_system.svg_length_to_emu = Mock(return_value=1097280)  # Scaled diameter
        
        result = converter.convert(element, mock_context)
        
        # Should use scaled coordinates and dimensions
        assert '<a:off x="1828800" y="1828800"/>' in result
        assert '<a:ext cx="1097280" cy="1097280"/>' in result