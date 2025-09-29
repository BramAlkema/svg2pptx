#!/usr/bin/env python3
"""
Unit tests for CustGeomGenerator.

Tests the conversion of simple SVG clipPath elements to native DrawingML custGeom elements.
"""

import pytest
from unittest.mock import Mock, MagicMock
from lxml import etree as ET

from src.converters.custgeom_generator import CustGeomGenerator, CustGeomGenerationError
from src.converters.clippath_types import ClipPathDefinition, ClippingType
from src.converters.base import ConversionContext
from core.services.conversion_services import ConversionServices
from tests.fixtures.clippath_fixtures import (
    create_svg_element, create_simple_rect_clippath,
    create_simple_path_clippath, create_complex_path_clippath
)


class TestCustGeomGenerator:
    """Test CustGeomGenerator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock services
        self.mock_services = Mock(spec=ConversionServices)
        self.generator = CustGeomGenerator(self.mock_services)

        # Create mock context
        self.context = Mock(spec=ConversionContext)
        self.context.get_next_shape_id = Mock(return_value="12345")

    def test_initialization(self):
        """Test that CustGeomGenerator initializes correctly."""
        assert self.generator.services == self.mock_services
        assert self.generator._coordinate_scale == 914400

    def test_can_generate_custgeom_simple_rect(self):
        """Test custGeom capability detection for simple rectangle."""
        rect_clip = create_simple_rect_clippath()
        assert self.generator.can_generate_custgeom(rect_clip) == True

    def test_can_generate_custgeom_simple_path(self):
        """Test custGeom capability detection for simple path."""
        path_clip = create_simple_path_clippath()
        assert self.generator.can_generate_custgeom(path_clip) == True

    def test_can_generate_custgeom_complex_path(self):
        """Test custGeom capability detection for complex path."""
        complex_clip = create_complex_path_clippath()
        # Complex path with curves should still be possible for custGeom
        assert self.generator.can_generate_custgeom(complex_clip) == True

    def test_cannot_generate_custgeom_no_data(self):
        """Test custGeom capability detection fails for empty clipPath."""
        empty_clip = ClipPathDefinition(
            id='empty',
            units='userSpaceOnUse',
            clip_rule='nonzero',
            clipping_type=ClippingType.PATH_BASED
        )
        assert self.generator.can_generate_custgeom(empty_clip) == False

    def test_generate_custgeom_xml_with_rect_shape(self):
        """Test custGeom XML generation for rectangle shape."""
        rect_clip = create_simple_rect_clippath()
        result = self.generator.generate_custgeom_xml(rect_clip, self.context)

        assert '<a:custGeom>' in result
        assert '<a:pathLst>' in result
        assert '<a:moveTo>' in result
        assert '<a:lnTo>' in result
        assert '<a:close/>' in result

    def test_generate_custgeom_xml_with_path_data(self):
        """Test custGeom XML generation for path data."""
        path_clip = create_simple_path_clippath()
        result = self.generator.generate_custgeom_xml(path_clip, self.context)

        assert '<a:custGeom>' in result
        assert '<a:pathLst>' in result
        assert '<a:path w="21600" h="21600">' in result

    def test_convert_svg_path_to_drawingml_simple(self):
        """Test conversion of simple SVG path to DrawingML."""
        svg_path = "M 0 0 L 100 0 L 100 100 L 0 100 Z"
        result = self.generator.convert_svg_path_to_drawingml(svg_path, self.context)

        assert '<a:moveTo>' in result
        assert '<a:lnTo>' in result
        assert '<a:close/>' in result

    def test_convert_svg_path_with_curves(self):
        """Test conversion of SVG path with cubic curves."""
        svg_path = "M 50 0 C 77.6 0 100 22.4 100 50 Z"
        result = self.generator.convert_svg_path_to_drawingml(svg_path, self.context)

        assert '<a:moveTo>' in result
        assert '<a:cubicBezTo>' in result
        assert '<a:close/>' in result

    def test_handle_basic_shapes_rect(self):
        """Test conversion of rectangle element."""
        rect = create_svg_element('rect', x=10, y=20, width=100, height=50)
        result = self.generator.handle_basic_shapes(rect, self.context)

        assert '<a:moveTo>' in result
        assert '<a:lnTo>' in result
        assert '<a:close/>' in result

    def test_handle_basic_shapes_circle(self):
        """Test conversion of circle element."""
        circle = create_svg_element('circle', cx=50, cy=50, r=25)
        result = self.generator.handle_basic_shapes(circle, self.context)

        # Circle is approximated as rectangle for now
        assert '<a:moveTo>' in result
        assert '<a:lnTo>' in result
        assert '<a:close/>' in result

    def test_handle_basic_shapes_polygon(self):
        """Test conversion of polygon element."""
        polygon = create_svg_element('polygon', points="0,0 100,0 50,100")
        result = self.generator.handle_basic_shapes(polygon, self.context)

        assert '<a:moveTo>' in result
        assert '<a:lnTo>' in result
        assert '<a:close/>' in result

    def test_handle_basic_shapes_polyline(self):
        """Test conversion of polyline element."""
        polyline = create_svg_element('polyline', points="0,0 100,0 50,100")
        result = self.generator.handle_basic_shapes(polyline, self.context)

        assert '<a:moveTo>' in result
        assert '<a:lnTo>' in result
        # Polyline should not have close
        assert '<a:close/>' not in result

    def test_handle_unsupported_shape(self):
        """Test handling of unsupported shape types."""
        unsupported = create_svg_element('path', d="M 0 0")  # path element not supported in handle_basic_shapes

        with pytest.raises(CustGeomGenerationError):
            self.generator.handle_basic_shapes(unsupported, self.context)

    def test_coordinate_scaling(self):
        """Test coordinate scaling to DrawingML system."""
        x_scaled, y_scaled = self.generator._scale_coordinates(50, 75)

        # Coordinates should be scaled to 21600 system
        assert x_scaled == 10800  # 50% of 21600
        assert y_scaled == 16200  # 75% of 21600

    def test_parse_svg_path_simple(self):
        """Test parsing of simple SVG path commands."""
        path_data = "M 10 20 L 30 40 Z"
        commands = self.generator._parse_svg_path(path_data)

        assert len(commands) == 3
        assert commands[0] == ('M', [10.0, 20.0])
        assert commands[1] == ('L', [30.0, 40.0])
        assert commands[2] == ('Z', [])

    def test_parse_svg_path_with_curves(self):
        """Test parsing of SVG path with curves."""
        path_data = "M 0 0 C 10 10 20 20 30 30"
        commands = self.generator._parse_svg_path(path_data)

        assert len(commands) == 2
        assert commands[0] == ('M', [0.0, 0.0])
        assert commands[1] == ('C', [10.0, 10.0, 20.0, 20.0, 30.0, 30.0])

    def test_is_simple_path_detection(self):
        """Test detection of simple vs complex paths."""
        simple_path = "M 0 0 L 100 100 Z"
        complex_path = "M 0 0 Q 50 50 100 100"  # Quadratic curves not fully supported

        assert self.generator._is_simple_path(simple_path) == True
        # For now, we allow Q commands in simple paths
        assert self.generator._is_simple_path(complex_path) == True

    def test_is_basic_shape_detection(self):
        """Test detection of basic shape elements."""
        rect = create_svg_element('rect')
        circle = create_svg_element('circle')
        path = create_svg_element('path')

        assert self.generator._is_basic_shape(rect) == True
        assert self.generator._is_basic_shape(circle) == True
        assert self.generator._is_basic_shape(path) == False

    def test_polygon_with_invalid_points(self):
        """Test polygon conversion with invalid points attribute."""
        polygon = create_svg_element('polygon', points="")

        with pytest.raises(CustGeomGenerationError):
            self.generator.handle_basic_shapes(polygon, self.context)

    def test_error_handling_in_can_generate(self):
        """Test error handling in can_generate_custgeom."""
        # Create a malformed clipPath definition
        malformed_clip = ClipPathDefinition(
            id='malformed',
            units='userSpaceOnUse',
            clip_rule='nonzero',
            shapes=[None],  # This will cause an error
            clipping_type=ClippingType.SHAPE_BASED
        )

        # Should return False instead of raising exception
        assert self.generator.can_generate_custgeom(malformed_clip) == False

    def test_custgeom_generation_failure(self):
        """Test custGeom generation failure handling."""
        # Create a clipPath that will fail generation
        failing_clip = ClipPathDefinition(
            id='failing',
            units='userSpaceOnUse',
            clip_rule='nonzero',
            clipping_type=ClippingType.PATH_BASED
            # No path_data or shapes - will cause failure
        )

        with pytest.raises(CustGeomGenerationError):
            self.generator.generate_custgeom_xml(failing_clip, self.context)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])