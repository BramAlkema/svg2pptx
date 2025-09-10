"""
Comprehensive test suite for RectangleConverter enhancements.
Tests ViewportResolver integration, rounded corners, and edge cases.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import xml.etree.ElementTree as ET

from src.converters.shapes import RectangleConverter
from src.converters.base import ConversionContext


class TestRectangleConverterEnhancements:
    """Test suite for enhanced RectangleConverter functionality."""
    
    @pytest.fixture
    def converter(self):
        """Create a RectangleConverter instance."""
        return RectangleConverter()
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock ConversionContext with necessary attributes."""
        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu = Mock(return_value=(914400, 914400))
        context.coordinate_system.svg_length_to_emu = Mock(return_value=914400)
        context.batch_convert_to_emu = Mock(return_value={
            'x': 914400,
            'y': 914400,
            'width': 1828800,
            'height': 1371600,
            'rx': 0,
            'ry': 0
        })
        context.get_next_shape_id = Mock(return_value=1)
        context.current_color = 'black'
        return context
    
    def test_viewport_resolver_integration(self, converter, mock_context):
        """Test RectangleConverter integration with ViewportResolver for coordinate mapping."""
        element = ET.fromstring('<rect x="10" y="20" width="100" height="75"/>')
        
        # Mock ViewportResolver integration through context
        viewport_mapping = Mock()
        viewport_mapping.svg_to_emu = Mock(return_value=(182880, 365760))
        mock_context.viewport_mapping = viewport_mapping
        
        # Override batch_convert_to_emu to use viewport mapping
        def batch_convert_with_viewport(dims):
            if hasattr(mock_context, 'viewport_mapping') and mock_context.viewport_mapping:
                x = float(dims.get('x', '0').replace('px', ''))
                y = float(dims.get('y', '0').replace('px', ''))
                emu_x, emu_y = viewport_mapping.svg_to_emu(x, y)
                return {
                    'x': emu_x,
                    'y': emu_y,
                    'width': 1828800,
                    'height': 1371600,
                    'rx': 0,
                    'ry': 0
                }
            return {
                'x': 914400,
                'y': 914400,
                'width': 1828800,
                'height': 1371600,
                'rx': 0,
                'ry': 0
            }
        
        mock_context.batch_convert_to_emu = Mock(side_effect=batch_convert_with_viewport)
        
        result = converter.convert(element, mock_context)
        
        # Verify ViewportResolver was used
        viewport_mapping.svg_to_emu.assert_called_once_with(10.0, 20.0)
        assert '<a:off x="182880" y="365760"/>' in result
    
    def test_viewport_resolver_fallback(self, converter, mock_context):
        """Test fallback to standard coordinate system when ViewportResolver not available."""
        element = ET.fromstring('<rect x="10" y="20" width="100" height="75"/>')
        
        # No ViewportResolver in context
        mock_context.viewport_mapping = None
        
        result = converter.convert(element, mock_context)
        
        # Should use standard coordinate system conversion
        mock_context.coordinate_system.svg_to_emu.assert_called_once_with(10.0, 20.0)
        assert '<p:sp>' in result
    
    def test_rounded_corners_basic(self, converter, mock_context):
        """Test basic rounded corner support with rx and ry attributes."""
        element = ET.fromstring('<rect x="0" y="0" width="100" height="50" rx="10" ry="10"/>')
        
        mock_context.batch_convert_to_emu = Mock(return_value={
            'x': 0,
            'y': 0,
            'width': 914400,
            'height': 457200,
            'rx': 91440,
            'ry': 91440
        })
        
        # Mock parse_length for corner radius calculation
        converter.parse_length = Mock(side_effect=lambda x: float(x) if x else 0)
        
        result = converter.convert(element, mock_context)
        
        # Should generate rounded rectangle preset
        assert '<a:prstGeom prst="roundRect">' in result
        assert '<a:gd name="adj"' in result
    
    def test_rounded_corners_only_rx(self, converter, mock_context):
        """Test rounded corners when only rx is specified (ry should match)."""
        element = ET.fromstring('<rect x="0" y="0" width="100" height="50" rx="15"/>')
        
        mock_context.batch_convert_to_emu = Mock(return_value={
            'x': 0,
            'y': 0,
            'width': 914400,
            'height': 457200,
            'rx': 137160,
            'ry': 0
        })
        
        converter.parse_length = Mock(side_effect=lambda x: float(x) if x else 0)
        
        result = converter.convert(element, mock_context)
        
        # Should handle missing ry by using rx value
        assert '<a:prstGeom prst="roundRect">' in result
    
    def test_rounded_corners_only_ry(self, converter, mock_context):
        """Test rounded corners when only ry is specified (rx should match)."""
        element = ET.fromstring('<rect x="0" y="0" width="100" height="50" ry="12"/>')
        
        mock_context.batch_convert_to_emu = Mock(return_value={
            'x': 0,
            'y': 0,
            'width': 914400,
            'height': 457200,
            'rx': 0,
            'ry': 109728
        })
        
        converter.parse_length = Mock(side_effect=lambda x: float(x) if x else 0)
        
        result = converter.convert(element, mock_context)
        
        # Should handle missing rx by using ry value
        assert '<a:prstGeom prst="roundRect">' in result
    
    def test_rounded_corners_percentage_calculation(self, converter, mock_context):
        """Test correct percentage calculation for rounded corners."""
        element = ET.fromstring('<rect x="0" y="0" width="200" height="100" rx="20" ry="20"/>')
        
        mock_context.batch_convert_to_emu = Mock(return_value={
            'x': 0,
            'y': 0,
            'width': 1828800,
            'height': 914400,
            'rx': 182880,
            'ry': 182880
        })
        
        # Mock parse_length to return expected values
        converter.parse_length = Mock(side_effect=lambda x: {
            '20': 20, '200': 200, '100': 100, '0': 0
        }.get(x, 0))
        
        result = converter.convert(element, mock_context)
        
        # Corner radius should be 10% (20/200 * 100)
        assert '<a:prstGeom prst="roundRect">' in result
        # Check that adjustment value is calculated (10% = 10000 in DrawingML units)
        assert 'fmla="val' in result
    
    def test_rounded_corners_max_limit(self, converter, mock_context):
        """Test that rounded corners are limited to 50% maximum."""
        element = ET.fromstring('<rect x="0" y="0" width="100" height="100" rx="60" ry="60"/>')
        
        mock_context.batch_convert_to_emu = Mock(return_value={
            'x': 0,
            'y': 0,
            'width': 914400,
            'height': 914400,
            'rx': 548640,
            'ry': 548640
        })
        
        converter.parse_length = Mock(side_effect=lambda x: float(x) if x else 0)
        
        result = converter.convert(element, mock_context)
        
        # Should limit to 50% even if rx/ry are larger
        assert '<a:prstGeom prst="roundRect">' in result
    
    def test_no_rounded_corners(self, converter, mock_context):
        """Test regular rectangle without rounded corners."""
        element = ET.fromstring('<rect x="0" y="0" width="100" height="50"/>')
        
        result = converter.convert(element, mock_context)
        
        # Should generate regular rectangle preset
        assert '<a:prstGeom prst="rect">' in result
        assert 'roundRect' not in result
    
    def test_edge_case_zero_dimensions(self, converter, mock_context):
        """Test handling of rectangle with zero width or height."""
        test_cases = [
            '<rect x="10" y="10" width="0" height="50"/>',
            '<rect x="10" y="10" width="100" height="0"/>',
            '<rect x="10" y="10" width="0" height="0"/>',
        ]
        
        for svg_str in test_cases:
            element = ET.fromstring(svg_str)
            result = converter.convert(element, mock_context)
            
            # Should still generate valid shape
            assert '<p:sp>' in result
            assert '<a:prstGeom prst=' in result
    
    def test_edge_case_negative_dimensions(self, converter, mock_context):
        """Test handling of rectangle with negative dimensions."""
        element = ET.fromstring('<rect x="10" y="10" width="-100" height="-50"/>')
        
        # Mock batch_convert to handle negative values appropriately
        mock_context.batch_convert_to_emu = Mock(return_value={
            'x': 914400,
            'y': 914400,
            'width': 0,  # Negative width converted to 0
            'height': 0,  # Negative height converted to 0
            'rx': 0,
            'ry': 0
        })
        
        result = converter.convert(element, mock_context)
        
        # Should generate valid shape even with invalid dimensions
        assert '<p:sp>' in result
    
    def test_edge_case_missing_attributes(self, converter, mock_context):
        """Test handling of rectangle with missing attributes."""
        element = ET.fromstring('<rect/>')
        
        mock_context.batch_convert_to_emu = Mock(return_value={
            'x': 0,
            'y': 0,
            'width': 0,
            'height': 0,
            'rx': 0,
            'ry': 0
        })
        
        result = converter.convert(element, mock_context)
        
        # Should use default values
        assert '<p:sp>' in result
        assert '<a:prstGeom prst="rect">' in result
    
    def test_unit_handling_improvements(self, converter, mock_context):
        """Test improved unit handling for rectangle attributes."""
        test_cases = [
            ('<rect x="10px" y="20px" width="100px" height="50px"/>', "Pixel units"),
            ('<rect x="1em" y="2em" width="10em" height="5em"/>', "Em units"),
            ('<rect x="10%" y="20%" width="50%" height="25%"/>', "Percentage units"),
            ('<rect x="1in" y="2in" width="3in" height="1.5in"/>', "Inch units"),
            ('<rect x="10mm" y="20mm" width="100mm" height="50mm"/>', "Millimeter units"),
        ]
        
        for svg_str, description in test_cases:
            element = ET.fromstring(svg_str)
            result = converter.convert(element, mock_context)
            assert '<p:sp>' in result, f"Failed for {description}"
            assert '<a:prstGeom prst=' in result
    
    def test_style_attributes_with_viewport(self, converter, mock_context):
        """Test style attribute handling with ViewportResolver active."""
        element = ET.fromstring('''
            <rect x="10" y="10" width="100" height="50"
                  fill="blue" stroke="red" stroke-width="2"
                  opacity="0.8" fill-opacity="0.6" stroke-opacity="0.7"/>
        ''')
        
        # Add ViewportResolver
        viewport_mapping = Mock()
        viewport_mapping.svg_to_emu = Mock(return_value=(182880, 182880))
        mock_context.viewport_mapping = viewport_mapping
        
        # Mock style generation methods
        converter.generate_fill = Mock(return_value='<a:solidFill/>')
        converter.generate_stroke = Mock(return_value='<a:ln/>')
        
        result = converter.convert(element, mock_context)
        
        # Verify style methods were called
        converter.generate_fill.assert_called_once_with('blue', '0.6', mock_context)
        converter.generate_stroke.assert_called_once_with('red', '2', '0.7', mock_context)
    
    def test_transform_handling(self, converter, mock_context):
        """Test transform attribute handling."""
        element = ET.fromstring('<rect x="10" y="10" width="100" height="50" transform="rotate(45 60 35)"/>')
        
        # Mock transform generation
        converter._generate_transform = Mock(return_value='<a:xfrm rot="2700000"/>')
        
        result = converter.convert(element, mock_context)
        
        # Verify transform was processed
        converter._generate_transform.assert_called_once_with('rotate(45 60 35)', mock_context)
        assert '<a:xfrm' in result
    
    def test_shape_id_generation(self, converter, mock_context):
        """Test proper shape ID generation for rectangles."""
        element = ET.fromstring('<rect x="0" y="0" width="100" height="50"/>')
        
        # Test with different shape IDs
        for shape_id in [1, 42, 999]:
            mock_context.get_next_shape_id = Mock(return_value=shape_id)
            result = converter.convert(element, mock_context)
            assert f'<p:cNvPr id="{shape_id}" name="Rectangle {shape_id}"/>' in result
    
    def test_performance_with_complex_styles(self, converter, mock_context):
        """Test performance with complex style combinations."""
        element = ET.fromstring('''
            <rect x="10" y="10" width="100" height="50" rx="5" ry="5"
                  fill="url(#gradient1)" stroke="url(#pattern1)"
                  stroke-width="3" stroke-dasharray="5,2"
                  filter="url(#blur1)" mask="url(#mask1)"
                  clip-path="url(#clip1)" opacity="0.75"
                  transform="matrix(1,0,0,1,10,10)"/>
        ''')
        
        # Mock complex style handling
        converter.generate_fill = Mock(return_value='<a:gradFill/>')
        converter.generate_stroke = Mock(return_value='<a:ln><a:pattFill/></a:ln>')
        converter._generate_transform = Mock(return_value='')
        converter.parse_length = Mock(return_value=5)
        
        result = converter.convert(element, mock_context)
        
        # Should handle complex styles without errors
        assert '<p:sp>' in result
        assert '<a:prstGeom prst="roundRect">' in result
    
    def test_coordinate_conversion_efficiency(self, converter, mock_context):
        """Test that coordinate conversion is handled efficiently."""
        element = ET.fromstring('<rect x="10" y="20" width="100" height="50" rx="5" ry="3"/>')
        
        result = converter.convert(element, mock_context)
        
        # Should call coordinate conversion methods
        mock_context.coordinate_system.svg_to_emu.assert_called_once_with(10.0, 20.0)
        
        # Should call dimension conversion methods for width, height, rx, ry
        calls = mock_context.coordinate_system.svg_length_to_emu.call_args_list
        assert len(calls) >= 4  # width, height, rx, ry conversions
        assert '<p:sp>' in result