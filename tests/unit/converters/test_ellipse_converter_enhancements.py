"""
Comprehensive test suite for EllipseConverter enhancements.
Tests ViewportResolver integration, universal utilities, and edge cases.
"""

import pytest
from unittest.mock import Mock, MagicMock
import xml.etree.ElementTree as ET
import math

from src.converters.shapes import EllipseConverter
from src.converters.base import ConversionContext


class TestEllipseConverterEnhancements:
    """Test suite for enhanced EllipseConverter functionality."""
    
    @pytest.fixture
    def converter(self):
        """Create an EllipseConverter instance."""
        return EllipseConverter()
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock ConversionContext with necessary attributes."""
        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu = Mock(return_value=(914400, 914400))
        context.coordinate_system.svg_length_to_emu = Mock(side_effect=lambda v, axis: 914400 if axis == 'x' else 457200)
        context.get_next_shape_id = Mock(return_value=1)
        context.current_color = 'black'
        return context
    
    def test_viewport_resolver_integration(self, converter, mock_context):
        """Test EllipseConverter integration with ViewportResolver for coordinate mapping."""
        element = ET.fromstring('<ellipse cx="50" cy="50" rx="40" ry="20"/>')
        
        # Mock ViewportResolver integration through context
        viewport_mapping = Mock()
        viewport_mapping.svg_to_emu = Mock(return_value=(914400, 914400))
        mock_context.viewport_mapping = viewport_mapping
        
        result = converter.convert(element, mock_context)
        
        # Verify ViewportResolver was used for coordinate conversion
        viewport_mapping.svg_to_emu.assert_called_once_with(10.0, 30.0)  # cx-rx, cy-ry
        assert '<a:off x="914400" y="914400"/>' in result
    
    def test_viewport_resolver_fallback(self, converter, mock_context):
        """Test fallback to standard coordinate system when ViewportResolver not available."""
        element = ET.fromstring('<ellipse cx="50" cy="50" rx="40" ry="20"/>')
        
        # No ViewportResolver in context
        mock_context.viewport_mapping = None
        
        result = converter.convert(element, mock_context)
        
        # Should fall back to standard coordinate system
        mock_context.coordinate_system.svg_to_emu.assert_called_once_with(10.0, 30.0)
        assert '<p:sp>' in result
    
    def test_unit_handling_improvements(self, converter, mock_context):
        """Test improved unit handling for ellipse attributes."""
        test_cases = [
            ('<ellipse cx="10px" cy="20px" rx="5px" ry="3px"/>', "Pixel units"),
            ('<ellipse cx="1em" cy="2em" rx="0.5em" ry="0.3em"/>', "Em units"),
            ('<ellipse cx="10%" cy="20%" rx="5%" ry="3%"/>', "Percentage units"),
            ('<ellipse cx="1in" cy="2in" rx="0.5in" ry="0.3in"/>', "Inch units"),
            ('<ellipse cx="10mm" cy="20mm" rx="5mm" ry="3mm"/>', "Millimeter units"),
        ]
        
        for svg_str, description in test_cases:
            element = ET.fromstring(svg_str)
            result = converter.convert(element, mock_context)
            assert '<p:sp>' in result, f"Failed for {description}"
            assert '<a:prstGeom prst="ellipse">' in result
    
    def test_edge_case_zero_radii(self, converter, mock_context):
        """Test handling of ellipse with zero radii."""
        test_cases = [
            '<ellipse cx="50" cy="50" rx="0" ry="0"/>',  # Both zero
            '<ellipse cx="50" cy="50" rx="30" ry="0"/>',  # Only ry zero
            '<ellipse cx="50" cy="50" rx="0" ry="20"/>',  # Only rx zero
        ]
        
        for svg_str in test_cases:
            element = ET.fromstring(svg_str)
            result = converter.convert(element, mock_context)
            
            # Should still generate valid shape with zero dimensions
            assert '<p:sp>' in result
            assert '<a:prstGeom prst="ellipse">' in result
    
    def test_edge_case_negative_radii(self, converter, mock_context):
        """Test handling of ellipse with negative radii (should be treated as 0)."""
        element = ET.fromstring('<ellipse cx="50" cy="50" rx="-40" ry="-20"/>')
        
        # Mock parse_length to handle negative values
        converter.parse_length = Mock(side_effect=lambda x: max(0, float(x.replace('px', '').replace('em', '').replace('%', '').replace('in', '').replace('mm', ''))))
        
        result = converter.convert(element, mock_context)
        
        # Should generate valid shape treating negative as zero
        assert '<p:sp>' in result
        assert '<a:prstGeom prst="ellipse">' in result
    
    def test_edge_case_missing_attributes(self, converter, mock_context):
        """Test handling of ellipse with missing attributes (should use defaults)."""
        element = ET.fromstring('<ellipse/>')
        
        result = converter.convert(element, mock_context)
        
        # Should use default values (cx=0, cy=0, rx=0, ry=0)
        assert '<p:sp>' in result
        mock_context.coordinate_system.svg_to_emu.assert_called_once_with(0, 0)
    
    def test_style_attributes_with_viewport(self, converter, mock_context):
        """Test style attribute handling with ViewportResolver active."""
        element = ET.fromstring('''
            <ellipse cx="50" cy="50" rx="40" ry="20" 
                     fill="green" stroke="purple" stroke-width="3"
                     opacity="0.9" fill-opacity="0.7" stroke-opacity="0.8"/>
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
        converter.generate_fill.assert_called_once_with('green', '0.7', mock_context)
        converter.generate_stroke.assert_called_once_with('purple', '3', '0.8', mock_context)
    
    def test_transform_aware_positioning(self, converter, mock_context):
        """Test that EllipseConverter properly positions ellipses with transform awareness."""
        element = ET.fromstring('<ellipse cx="100" cy="100" rx="60" ry="40" transform="rotate(45 100 100)"/>')
        
        # Add ViewportResolver with transform support
        viewport_mapping = Mock()
        viewport_mapping.svg_to_emu = Mock(return_value=(1828800, 1828800))  # Transformed position
        mock_context.viewport_mapping = viewport_mapping
        
        result = converter.convert(element, mock_context)
        
        # Should apply transform-aware positioning
        assert '<a:off x="1828800" y="1828800"/>' in result
    
    def test_aspect_ratio_preservation(self, converter, mock_context):
        """Test that ellipse aspect ratio is preserved correctly."""
        element = ET.fromstring('<ellipse cx="50" cy="50" rx="40" ry="20"/>')
        
        # Mock different EMU values for width and height
        mock_context.coordinate_system.svg_length_to_emu = Mock(
            side_effect=lambda v, axis: 1463040 if v == 80 else 731520  # 2:1 aspect ratio
        )
        
        result = converter.convert(element, mock_context)
        
        # Should preserve aspect ratio in dimensions
        assert '<a:ext cx="1463040" cy="731520"/>' in result
    
    def test_large_radii_handling(self, converter, mock_context):
        """Test handling of ellipses with very large radius values."""
        element = ET.fromstring('<ellipse cx="500" cy="500" rx="1000" ry="800"/>')
        
        # Mock large EMU values
        mock_context.coordinate_system.svg_to_emu = Mock(return_value=(-4572000, -2743200))  # cx-rx, cy-ry
        mock_context.coordinate_system.svg_length_to_emu = Mock(
            side_effect=lambda v, axis: 18288000 if v == 2000 else 14630400
        )
        
        result = converter.convert(element, mock_context)
        
        # Should handle large values correctly
        assert '<a:off x="-4572000" y="-2743200"/>' in result
    
    def test_precision_handling(self, converter, mock_context):
        """Test handling of high-precision floating point values."""
        element = ET.fromstring('<ellipse cx="33.33333" cy="66.66666" rx="12.34567" ry="8.76543"/>')
        
        result = converter.convert(element, mock_context)
        
        # Should handle precise float values
        assert '<p:sp>' in result
        # Verify the values were processed
        mock_context.coordinate_system.svg_to_emu.assert_called()
    
    def test_shape_id_generation(self, converter, mock_context):
        """Test proper shape ID generation for ellipses."""
        element = ET.fromstring('<ellipse cx="50" cy="50" rx="40" ry="20"/>')
        
        # Test with different shape IDs
        for shape_id in [1, 100, 999]:
            mock_context.get_next_shape_id = Mock(return_value=shape_id)
            result = converter.convert(element, mock_context)
            assert f'<p:cNvPr id="{shape_id}" name="Ellipse {shape_id}"/>' in result
    
    def test_universal_color_parser_integration(self, converter, mock_context):
        """Test integration with universal ColorParser for fill/stroke colors."""
        element = ET.fromstring('<ellipse cx="50" cy="50" rx="40" ry="20" fill="rgb(128, 0, 255)"/>')
        
        # Mock ColorParser integration
        converter.generate_fill = Mock(return_value='<a:solidFill><a:srgbClr val="8000FF"/></a:solidFill>')
        
        result = converter.convert(element, mock_context)
        
        converter.generate_fill.assert_called_once_with('rgb(128, 0, 255)', '1', mock_context)
        assert '<a:solidFill><a:srgbClr val="8000FF"/></a:solidFill>' in result
    
    def test_performance_with_complex_styles(self, converter, mock_context):
        """Test performance with complex style combinations."""
        element = ET.fromstring('''
            <ellipse cx="100" cy="100" rx="60" ry="40"
                     fill="url(#radialGradient1)" stroke="url(#linearGradient1)"
                     stroke-width="4" stroke-dasharray="10,5,2,5"
                     filter="url(#dropShadow)" mask="url(#ellipseMask)"
                     clip-path="url(#clipPath1)" opacity="0.85"/>
        ''')
        
        # Mock complex style handling
        converter.generate_fill = Mock(return_value='<a:gradFill/>')
        converter.generate_stroke = Mock(return_value='<a:ln><a:gradFill/></a:ln>')
        
        result = converter.convert(element, mock_context)
        
        # Should handle complex styles without errors
        assert '<p:sp>' in result
        converter.generate_fill.assert_called_once()
        converter.generate_stroke.assert_called_once()
    
    def test_bounding_box_calculation_accuracy(self, converter, mock_context):
        """Test accurate bounding box calculation for ellipses."""
        test_cases = [
            (50, 50, 40, 20, 10, 30, 80, 40),  # cx, cy, rx, ry, expected x, y, width, height
            (0, 0, 10, 5, -10, -5, 20, 10),
            (100, 200, 60, 30, 40, 170, 120, 60),
        ]
        
        for cx, cy, rx, ry, exp_x, exp_y, exp_w, exp_h in test_cases:
            element = ET.fromstring(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}"/>')
            
            # Reset mock to track calls per test case
            mock_context.coordinate_system.svg_to_emu.reset_mock()
            mock_context.coordinate_system.svg_length_to_emu.reset_mock()
            
            result = converter.convert(element, mock_context)
            
            # Verify bounding box calculation
            mock_context.coordinate_system.svg_to_emu.assert_called_with(exp_x, exp_y)
            
            # Check width and height conversions
            calls = mock_context.coordinate_system.svg_length_to_emu.call_args_list
            assert any(call[0][0] == exp_w for call in calls), f"Width {exp_w} not converted"
            assert any(call[0][0] == exp_h for call in calls), f"Height {exp_h} not converted"
    
    def test_viewport_coordinate_scaling(self, converter, mock_context):
        """Test that ViewportResolver properly scales ellipse dimensions."""
        element = ET.fromstring('<ellipse cx="50" cy="50" rx="40" ry="20"/>')
        
        # Mock ViewportResolver with scaling
        viewport_mapping = Mock()
        viewport_mapping.svg_to_emu = Mock(return_value=(1828800, 1828800))  # 2x scale
        viewport_mapping.scale_factor = 2.0
        mock_context.viewport_mapping = viewport_mapping
        mock_context.coordinate_system.svg_length_to_emu = Mock(
            side_effect=lambda v, axis: 1463040 if v == 80 else 731520  # Scaled dimensions
        )
        
        result = converter.convert(element, mock_context)
        
        # Should use scaled coordinates and dimensions
        assert '<a:off x="1828800" y="1828800"/>' in result
        assert '<a:ext cx="1463040" cy="731520"/>' in result
    
    def test_circle_as_ellipse_special_case(self, converter, mock_context):
        """Test ellipse with equal radii (essentially a circle)."""
        element = ET.fromstring('<ellipse cx="50" cy="50" rx="30" ry="30"/>')
        
        mock_context.coordinate_system.svg_length_to_emu = Mock(return_value=1097280)  # Same for both dimensions
        
        result = converter.convert(element, mock_context)
        
        # Should generate ellipse geometry even when dimensions are equal
        assert '<a:prstGeom prst="ellipse">' in result
        assert '<a:ext cx="1097280" cy="1097280"/>' in result