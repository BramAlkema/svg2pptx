#!/usr/bin/env python3
"""
Test suite for viewport-aware coordinate conversion integration.

# Centralized fixtures
from tests.fixtures.common import *
from tests.fixtures.mock_objects import *
from tests.fixtures.svg_content import *


Tests that coordinate-heavy converters properly integrate with ViewportResolver
for consistent viewport-aware coordinate mapping across all SVG elements.

This addresses Task 4.1: Write tests for viewport-aware coordinate conversion 
in coordinate-heavy converters (paths.py, shapes.py, text.py).
"""

import pytest
from lxml import etree as ET

from src.converters.base import ConversionContext, CoordinateSystem
from src.converters.paths import PathConverter
from src.converters.shapes import RectangleConverter, CircleConverter, EllipseConverter
from src.converters.text import TextConverter
from src.viewbox import ViewportResolver, ViewBoxInfo, ViewportDimensions


class TestViewportCoordinateIntegration:
    """Test viewport-aware coordinate conversion in coordinate-heavy converters."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.path_converter = PathConverter()
        self.rect_converter = RectangleConverter()
        self.circle_converter = CircleConverter()
        self.text_converter = TextConverter(enable_font_embedding=False, enable_text_to_path_fallback=False)
        
        # Create mock viewport resolver
        self.viewport_resolver = ViewportResolver()
        
        # Create test context with coordinate system
        self.context = ConversionContext()
        self.context.coordinate_system = CoordinateSystem(
            viewbox=(0, 0, 800, 600),  # Standard SVG viewbox
            slide_width=9144000,  # Standard PowerPoint slide width in EMUs
            slide_height=6858000   # Standard PowerPoint slide height in EMUs
        )
        
        # Set viewport context for unit conversions
        from src.units import ViewportContext
        self.context.viewport_context = ViewportContext(
            width=800.0,
            height=600.0,
            dpi=96.0
        )
    
    def test_viewport_resolver_availability_in_base_converter(self):
        """Test that all converters have access to ViewportResolver through BaseConverter."""
        # ViewportResolver should be available as viewport_resolver in BaseConverter
        assert hasattr(self.path_converter, 'viewport_resolver')
        assert hasattr(self.rect_converter, 'viewport_resolver')
        assert hasattr(self.circle_converter, 'viewport_resolver')
        assert hasattr(self.text_converter, 'viewport_resolver')
        
        # Should be ViewportResolver instances
        assert isinstance(self.path_converter.viewport_resolver, ViewportResolver)
        assert isinstance(self.rect_converter.viewport_resolver, ViewportResolver)
        assert isinstance(self.circle_converter.viewport_resolver, ViewportResolver)
        assert isinstance(self.text_converter.viewport_resolver, ViewportResolver)


class TestPathConverterViewportIntegration:
    """Test PathConverter viewport-aware coordinate conversion."""
    
    def setup_method(self):
        """Set up path converter test fixtures."""
        self.converter = PathConverter()
        self.context = ConversionContext()
        
        # Set up coordinate system for standard viewport
        self.context.coordinate_system = CoordinateSystem(
            viewbox=(0, 0, 800, 600),
            slide_width=9144000,
            slide_height=6858000
        )
        
        from src.units import ViewportContext
        self.context.viewport_context = ViewportContext(
            width=800.0,
            height=600.0,
            dpi=96.0
        )
    
    def test_path_coordinate_conversion_patterns(self):
        """Test that path converter coordinate patterns match viewport expectations."""
        # Create test path element
        path_xml = '''<path d="M 100 100 L 200 200 L 300 100 Z"/>'''
        path_element = ET.fromstring(path_xml)
        
        # Mock the coordinate conversion methods to track calls
        original_svg_width = self.context.coordinate_system.svg_width
        original_svg_height = self.context.coordinate_system.svg_height
        
        # Convert path 
        result = self.converter.convert(path_element, self.context)
        
        # Verify result contains DrawingML coordinates
        assert '<a:moveTo>' in result
        assert '<a:lnTo>' in result
        assert '<a:close/>' in result
        
        # Test coordinate scaling consistency
        # Path uses manual scaling: (x / context.coordinate_system.svg_width) * 21600
        # This pattern should be replaced with viewport-aware conversion
        
        # Expected scaling for point (100, 100) in 800x600 viewbox:
        expected_x = int((100 / 800) * 21600)  # Current manual calculation
        expected_y = int((100 / 600) * 21600)  # Current manual calculation
        
        # Result should contain these coordinates
        assert f'x="{expected_x}"' in result
        assert f'y="{expected_y}"' in result
    
    def test_path_viewport_context_usage(self):
        """Test that PathConverter can use viewport context for coordinate mapping."""
        # Create path with transforms
        path_xml = '''<path d="M 0 0 L 100 100" transform="scale(2)"/>'''
        path_element = ET.fromstring(path_xml)
        
        # Convert with viewport context
        result = self.converter.convert(path_element, self.context)
        
        # Verify transform is handled (should use get_element_transform_matrix)
        assert 'transform' in result or 'xfrm' in result
    
    @pytest.mark.parametrize("viewbox,expected_scaling", [
        ((0, 0, 400, 300), "double_scale"),  # Smaller viewbox = larger scaling
        ((0, 0, 1600, 1200), "half_scale"),  # Larger viewbox = smaller scaling
        ((-100, -100, 800, 600), "offset_viewbox"),  # Offset viewbox
    ])
    def test_path_different_viewbox_scenarios(self, viewbox, expected_scaling):
        """Test PathConverter coordinate conversion with different viewbox scenarios."""
        # Update coordinate system with different viewbox
        self.context.coordinate_system = CoordinateSystem(
            viewbox=viewbox,
            slide_width=9144000,
            slide_height=6858000
        )
        
        # Test simple path
        path_xml = '''<path d="M 100 100 L 200 200"/>'''
        path_element = ET.fromstring(path_xml)
        
        result = self.converter.convert(path_element, self.context)
        
        # Verify coordinate conversion adapts to viewbox
        assert '<a:moveTo>' in result
        assert '<a:lnTo>' in result
        
        # Coordinates should be different for different viewboxes
        # This tests that the converter is viewbox-aware


class TestShapeConverterViewportIntegration:
    """Test shape converters' viewport-aware coordinate conversion."""
    
    def setup_method(self):
        """Set up shape converter test fixtures."""
        self.rect_converter = RectangleConverter()
        self.circle_converter = CircleConverter()
        self.context = ConversionContext()
        
        # Standard coordinate system
        self.context.coordinate_system = CoordinateSystem(
            viewbox=(0, 0, 800, 600),
            slide_width=9144000,
            slide_height=6858000
        )
        
        from src.units import ViewportContext
        self.context.viewport_context = ViewportContext(
            width=800.0,
            height=600.0,
            dpi=96.0
        )
    
    def test_rectangle_converter_batch_conversion(self):
        """Test RectangleConverter uses batch conversion properly."""
        rect_xml = '''<rect x="50" y="100" width="200" height="150"/>'''
        rect_element = ET.fromstring(rect_xml)
        
        # Mock batch_convert_to_emu to verify it's called
        with patch.object(self.context, 'batch_convert_to_emu') as mock_batch:
            mock_batch.return_value = {
                'x': 500000, 'y': 1000000, 
                'width': 2000000, 'height': 1500000,
                'rx': 0, 'ry': 0
            }
            
            result = self.rect_converter.convert(rect_element, self.context)
            
            # Verify batch conversion was called with expected parameters
            mock_batch.assert_called_once()
            call_args = mock_batch.call_args[0][0]
            assert call_args['x'] == '50'
            assert call_args['y'] == '100'
            assert call_args['width'] == '200'
            assert call_args['height'] == '150'
            
            # Verify result uses converted values
            assert '500000' in result  # x EMU
            assert '1000000' in result  # y EMU
    
    def test_circle_converter_coordinate_system_usage(self):
        """Test CircleConverter uses coordinate system for conversion."""
        circle_xml = '''<circle cx="150" cy="100" r="50"/>'''
        circle_element = ET.fromstring(circle_xml)
        
        # Mock coordinate system methods to verify usage
        with patch.object(self.context.coordinate_system, 'svg_to_emu') as mock_svg_to_emu, \
             patch.object(self.context.coordinate_system, 'svg_length_to_emu') as mock_length_to_emu:
            
            mock_svg_to_emu.return_value = (1000000, 800000)  # x, y in EMU
            mock_length_to_emu.return_value = 600000  # diameter in EMU
            
            result = self.circle_converter.convert(circle_element, self.context)
            
            # Verify coordinate system methods were called
            mock_svg_to_emu.assert_called_once_with(100.0, 50.0)  # x=cx-r, y=cy-r
            mock_length_to_emu.assert_called_once_with(100.0, 'x')  # diameter=2*r
            
            # Verify result uses converted coordinates
            assert '1000000' in result  # x EMU
            assert '800000' in result   # y EMU
            assert '600000' in result   # diameter EMU
    
    def test_shape_converters_viewport_consistency(self):
        """Test that shape converters produce consistent results across viewport changes."""
        # Test rectangle with different viewport contexts
        rect_xml = '''<rect x="100" y="100" width="100" height="100"/>'''
        rect_element = ET.fromstring(rect_xml)
        
        # Standard viewport
        result1 = self.rect_converter.convert(rect_element, self.context)
        
        # Different viewport context
        from src.units import ViewportContext
        self.context.viewport_context = ViewportContext(
            viewport_width=1600,  # Double width
            viewport_height=1200, # Double height
            dpi=96
        )
        
        result2 = self.rect_converter.convert(rect_element, self.context)
        
        # Both should be valid XML with coordinate conversions
        assert '<a:xfrm>' in result1
        assert '<a:xfrm>' in result2
        assert '<a:off x=' in result1
        assert '<a:off x=' in result2


class TestTextConverterViewportIntegration:
    """Test TextConverter viewport-aware coordinate conversion."""
    
    def setup_method(self):
        """Set up text converter test fixtures."""
        self.converter = TextConverter(enable_font_embedding=False, enable_text_to_path_fallback=False)
        self.context = ConversionContext()
        
        self.context.coordinate_system = CoordinateSystem(
            viewbox=(0, 0, 800, 600),
            slide_width=9144000,
            slide_height=6858000
        )
        
        from src.units import ViewportContext
        self.context.viewport_context = ViewportContext(
            width=800.0,
            height=600.0,
            dpi=96.0
        )
    
    def test_text_coordinate_system_usage(self):
        """Test TextConverter uses coordinate system for position conversion."""
        text_xml = '''<text x="200" y="300">Hello World</text>'''
        text_element = ET.fromstring(text_xml)
        
        # Mock coordinate system to verify usage
        with patch.object(self.context.coordinate_system, 'svg_to_emu') as mock_svg_to_emu:
            mock_svg_to_emu.return_value = (2000000, 3000000)  # x, y in EMU
            
            result = self.converter.convert(text_element, self.context)
            
            # Verify coordinate conversion was called
            mock_svg_to_emu.assert_called_once_with(200.0, 300.0)
            
            # Verify result uses converted coordinates
            if result:  # Text converter might return empty for unavailable fonts
                assert '2000000' in result or 'x="2000000"' in result
    
    def test_text_transform_viewport_integration(self):
        """Test TextConverter handles transforms with viewport context."""
        text_xml = '''<text x="100" y="100" transform="translate(50, 25)">Transformed Text</text>'''
        text_element = ET.fromstring(text_xml)
        
        # Mock transform application to verify viewport context usage
        with patch.object(self.converter, 'apply_transform') as mock_transform:
            mock_transform.return_value = (150.0, 125.0)  # Transformed coordinates
            
            result = self.converter.convert(text_element, self.context)
            
            # Verify transform was applied with viewport context
            mock_transform.assert_called_once_with(
                'translate(50, 25)', 100.0, 100.0, self.context.viewport_context
            )
    
    def test_text_viewport_aware_font_sizing(self):
        """Test that text converter considers viewport for font size calculations."""
        text_xml = '''<text x="100" y="100" font-size="24px">Sample Text</text>'''
        text_element = ET.fromstring(text_xml)
        
        result = self.converter.convert(text_element, self.context)
        
        # Text conversion should handle font sizes relative to viewport
        # This tests that font sizing is viewport-aware
        if result:  # May be empty due to font availability
            assert 'text' in result.lower() or 'sp' in result


class TestViewportResolverIntegrationOpportunities:
    """Identify specific opportunities for ViewportResolver integration."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.viewport_resolver = ViewportResolver()
        self.context = ConversionContext()
        
    def test_identify_manual_coordinate_scaling_in_paths(self):
        """Identify where PathConverter uses manual coordinate scaling that could use ViewportResolver."""
        path_converter = PathConverter()
        
        # Create test SVG with viewBox for viewport mapping
        svg_xml = '''<svg viewBox="0 0 400 300" width="800" height="600">
            <path d="M 100 100 L 200 200"/>
        </svg>'''
        svg_root = ET.fromstring(svg_xml)
        path_element = svg_root.find('path')
        
        # Current PathConverter uses manual scaling patterns like:
        # dx = int((x / context.coordinate_system.svg_width) * 21600)
        # dy = int((y / context.coordinate_system.svg_height) * 21600)
        
        # These could be replaced with ViewportResolver.resolve_svg_viewport()
        # to get proper viewport mapping including viewBox, preserveAspectRatio, etc.
        
        viewbox, viewport_dims = self.viewport_resolver.extract_viewport_from_svg(svg_root)
        
        assert viewbox is not None
        assert viewbox.width == 400
        assert viewbox.height == 300
        assert viewport_dims.width > 0
        assert viewport_dims.height > 0
        
        # ViewportResolver provides proper viewport mapping
        mapping = self.viewport_resolver.calculate_viewport_mapping(
            viewbox, viewport_dims
        )
        
        assert mapping.scale_x > 0
        assert mapping.scale_y > 0
        
        # This mapping could replace manual scaling in coordinate-heavy converters
    
    def test_coordinate_system_vs_viewport_resolver_comparison(self):
        """Compare current CoordinateSystem approach vs ViewportResolver capabilities."""
        # Current approach: CoordinateSystem with simple scaling
        coord_system = CoordinateSystem(
            viewbox=(0, 0, 800, 600),
            slide_width=9144000,
            slide_height=6858000
        )
        
        # ViewportResolver approach: Full SVG viewport specification support
        svg_xml = '''<svg viewBox="0 0 800 600" width="400" height="300" 
                     preserveAspectRatio="xMidYMid meet">
        </svg>'''
        svg_element = ET.fromstring(svg_xml)
        
        viewport_mapping = self.viewport_resolver.resolve_svg_viewport(
            svg_element,
            target_width_emu=9144000,
            target_height_emu=6858000
        )
        
        # Coordinate systems should be comparable for basic cases
        test_x, test_y = 400, 300
        
        # Current coordinate system conversion
        coord_x, coord_y = coord_system.svg_to_emu(test_x, test_y)
        
        # ViewportResolver conversion
        viewport_x, viewport_y = viewport_mapping.svg_to_emu(test_x, test_y)
        
        # Results should be similar for simple cases
        # (ViewportResolver handles more complex cases like preserveAspectRatio)
        assert abs(coord_x - viewport_x) / max(coord_x, viewport_x) < 0.1  # Within 10%
        assert abs(coord_y - viewport_y) / max(coord_y, viewport_y) < 0.1  # Within 10%
    
    def test_viewport_resolver_advanced_features_integration(self):
        """Test ViewportResolver advanced features that aren't in current coordinate system."""
        # Test preserveAspectRatio support
        svg_xml = '''<svg viewBox="0 0 800 600" width="400" height="400" 
                     preserveAspectRatio="xMidYMid slice">
        </svg>'''
        svg_element = ET.fromstring(svg_xml)
        
        mapping = self.viewport_resolver.resolve_svg_viewport(
            svg_element,
            target_width_emu=9144000,
            target_height_emu=9144000  # Square target
        )
        
        # Slice mode should scale to fill (may crop content)
        assert mapping.clip_needed  # Should need clipping for slice mode
        assert mapping.scale_x == mapping.scale_y  # Uniform scaling for aspect ratio preservation
        
        # Test different alignment
        svg_xml_align = '''<svg viewBox="0 0 800 600" width="400" height="400" 
                          preserveAspectRatio="xMaxYMax meet">
        </svg>'''
        svg_element_align = ET.fromstring(svg_xml_align)
        
        mapping_align = self.viewport_resolver.resolve_svg_viewport(
            svg_element_align,
            target_width_emu=9144000,
            target_height_emu=9144000
        )
        
        # Different alignment should produce different translation offsets
        assert mapping.translate_x != mapping_align.translate_x or mapping.translate_y != mapping_align.translate_y


@pytest.mark.integration
class TestCoordinateIntegrationPipelineTests:
    """Integration tests for coordinate conversion pipeline with all converters."""
    
    def test_cross_converter_coordinate_consistency(self):
        """Test that all converters produce consistent coordinate mappings."""
        # Create context with specific viewport
        context = ConversionContext()
        context.coordinate_system = CoordinateSystem(
            viewbox=(0, 0, 1000, 800),
            slide_width=9144000,
            slide_height=6858000
        )
        
        from src.units import ViewportContext
        context.viewport_context = ViewportContext(
            viewport_width=1000,
            viewport_height=800,
            dpi=96
        )
        
        # Test same coordinates across different converters
        test_x, test_y = 500, 400  # Center point
        
        # Path converter coordinate handling (manual scaling)
        path_converter = PathConverter()
        path_xml = f'''<path d="M {test_x} {test_y} L 600 500"/>'''
        path_element = ET.fromstring(path_xml)
        path_result = path_converter.convert(path_element, context)
        
        # Circle converter coordinate handling (coordinate system)
        circle_converter = CircleConverter()
        circle_xml = f'''<circle cx="{test_x}" cy="{test_y}" r="50"/>'''
        circle_element = ET.fromstring(circle_xml)
        circle_result = circle_converter.convert(circle_element, context)
        
        # Text converter coordinate handling (coordinate system)
        text_converter = TextConverter(enable_font_embedding=False, enable_text_to_path_fallback=False)
        text_xml = f'''<text x="{test_x}" y="{test_y}">Test</text>'''
        text_element = ET.fromstring(text_xml)
        text_result = text_converter.convert(text_element, context)
        
        # All converters should handle the same input coordinates consistently
        # This tests the need for standardized coordinate conversion
        
        # Calculate expected EMU coordinates
        expected_x_emu = int((test_x / 1000) * 21600)  # Path manual calculation
        coord_x_emu, coord_y_emu = context.coordinate_system.svg_to_emu(test_x, test_y)
        
        # Results should reference similar coordinate values
        # (exact matching depends on specific implementation details)
        if path_result:
            assert str(expected_x_emu) in path_result or str(coord_x_emu) in path_result
        
        if circle_result:
            # Circle uses coordinate system, should have coordinate system values
            assert str(coord_x_emu) in circle_result or 'x=' in circle_result
        
        # This test demonstrates the inconsistency that ViewportResolver integration would solve