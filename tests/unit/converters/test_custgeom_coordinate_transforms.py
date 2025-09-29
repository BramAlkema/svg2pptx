#!/usr/bin/env python3
"""
Unit tests for CustGeomGenerator coordinate transformation functionality.

Tests the proper handling of clipPathUnits, coordinate system transformations,
and integration with existing CTM system.
"""

import pytest
from unittest.mock import Mock, MagicMock
from lxml import etree as ET

from src.converters.custgeom_generator import CustGeomGenerator, CoordinateContext
from src.converters.clippath_types import ClipPathDefinition, ClippingType
from src.converters.base import ConversionContext
from src.services.conversion_services import ConversionServices
from tests.fixtures.clippath_fixtures import create_svg_element


class TestCustGeomCoordinateTransforms:
    """Test coordinate transformation functionality in CustGeomGenerator."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock services
        self.mock_services = Mock(spec=ConversionServices)
        self.generator = CustGeomGenerator(self.mock_services)

        # Create mock context
        self.context = Mock(spec=ConversionContext)
        self.context.get_next_shape_id = Mock(return_value="12345")
        self.context.viewbox_width = 200
        self.context.viewbox_height = 150

    def test_create_coordinate_context_userspaceonuse(self):
        """Test coordinate context creation for userSpaceOnUse."""
        clip_def = ClipPathDefinition(
            id='user_space_clip',
            units='userSpaceOnUse',
            clip_rule='nonzero',
            path_data='M 0 0 L 100 100 Z',
            clipping_type=ClippingType.PATH_BASED
        )

        coord_context = self.generator._create_coordinate_context(clip_def, self.context)

        assert coord_context.units == 'userSpaceOnUse'
        assert coord_context.scale_x == 21600 / 200  # 21600 / viewbox_width
        assert coord_context.scale_y == 21600 / 150  # 21600 / viewbox_height
        assert coord_context.offset_x == 0
        assert coord_context.offset_y == 0
        assert coord_context.base_context == self.context

    def test_create_coordinate_context_objectboundingbox(self):
        """Test coordinate context creation for objectBoundingBox."""
        clip_def = ClipPathDefinition(
            id='bbox_clip',
            units='objectBoundingBox',
            clip_rule='nonzero',
            path_data='M 0 0 L 1 1 Z',
            clipping_type=ClippingType.PATH_BASED
        )

        coord_context = self.generator._create_coordinate_context(clip_def, self.context)

        assert coord_context.units == 'objectBoundingBox'
        assert coord_context.scale_x == 21600  # Full range for 0-1 coords
        assert coord_context.scale_y == 21600
        assert coord_context.offset_x == 0
        assert coord_context.offset_y == 0
        assert coord_context.base_context == self.context

    def test_calculate_custgeom_bounds_userspaceonuse(self):
        """Test custGeom bounds calculation for userSpaceOnUse."""
        coord_context = CoordinateContext(
            units='userSpaceOnUse',
            scale_x=108,  # 21600 / 200
            scale_y=144,  # 21600 / 150
            offset_x=0,
            offset_y=0,
            base_context=self.context
        )

        bounds = self.generator._calculate_custgeom_bounds(coord_context)

        assert bounds['width'] == 10800  # scale_x * 100
        assert bounds['height'] == 14400  # scale_y * 100

    def test_calculate_custgeom_bounds_objectboundingbox(self):
        """Test custGeom bounds calculation for objectBoundingBox."""
        coord_context = CoordinateContext(
            units='objectBoundingBox',
            scale_x=21600,
            scale_y=21600,
            offset_x=0,
            offset_y=0,
            base_context=self.context
        )

        bounds = self.generator._calculate_custgeom_bounds(coord_context)

        assert bounds['width'] == 21600
        assert bounds['height'] == 21600

    def test_scale_coordinates_with_context(self):
        """Test coordinate scaling using CoordinateContext."""
        coord_context = CoordinateContext(
            units='userSpaceOnUse',
            scale_x=100,
            scale_y=200,
            offset_x=10,
            offset_y=20,
            base_context=self.context
        )

        x, y = self.generator._scale_coordinates_with_context(50, 30, coord_context)

        assert x == 6000  # (50 + 10) * 100
        assert y == 10000  # (30 + 20) * 200

    def test_scale_coordinates_smart_with_coordinate_context(self):
        """Test smart coordinate scaling with CoordinateContext."""
        coord_context = CoordinateContext(
            units='objectBoundingBox',
            scale_x=21600,
            scale_y=21600,
            offset_x=0,
            offset_y=0,
            base_context=self.context
        )

        x, y = self.generator._scale_coordinates_smart(0.5, 0.25, coord_context)

        assert x == 10800  # 0.5 * 21600
        assert y == 5400   # 0.25 * 21600

    def test_scale_coordinates_smart_with_conversion_context(self):
        """Test smart coordinate scaling fallback with ConversionContext."""
        x, y = self.generator._scale_coordinates_smart(50, 75, self.context)

        # Should use fallback _scale_coordinates method
        assert x == 10800  # 50% of 21600
        assert y == 16200  # 75% of 21600

    def test_handle_clippath_units_objectboundingbox(self):
        """Test clipPathUnits handling for objectBoundingBox."""
        clip_def = ClipPathDefinition(
            id='bbox_clip',
            units='objectBoundingBox',
            clip_rule='nonzero',
            clipping_type=ClippingType.PATH_BASED
        )

        element_bounds = (100, 50, 200, 150)  # x, y, width, height
        result = self.generator.handle_clippath_units(clip_def, element_bounds)

        assert result == (0.0, 0.0, 200, 150)  # Should use element dimensions

    def test_handle_clippath_units_userspaceonuse(self):
        """Test clipPathUnits handling for userSpaceOnUse."""
        clip_def = ClipPathDefinition(
            id='user_clip',
            units='userSpaceOnUse',
            clip_rule='nonzero',
            clipping_type=ClippingType.PATH_BASED
        )

        element_bounds = (100, 50, 200, 150)
        result = self.generator.handle_clippath_units(clip_def, element_bounds)

        assert result == element_bounds  # Should return unchanged

    def test_apply_clippath_transform(self):
        """Test clipPath transform application (currently logs only)."""
        coord_context = CoordinateContext(
            units='userSpaceOnUse',
            scale_x=100,
            scale_y=100,
            offset_x=0,
            offset_y=0,
            base_context=self.context
        )

        path_data = '<a:moveTo><a:pt x="1000" y="2000"/></a:moveTo>'
        transform = 'rotate(45) scale(1.5)'

        # Should log and return unchanged (for now)
        result = self.generator._apply_clippath_transform(path_data, transform, coord_context)
        assert result == path_data

    def test_generate_custgeom_with_objectboundingbox(self):
        """Test full custGeom generation with objectBoundingBox coordinates."""
        clip_def = ClipPathDefinition(
            id='bbox_clip',
            units='objectBoundingBox',
            clip_rule='nonzero',
            path_data='M 0 0 L 1 0 L 1 1 L 0 1 Z',  # Full bounding box
            clipping_type=ClippingType.PATH_BASED
        )

        result = self.generator.generate_custgeom_xml(clip_def, self.context)

        assert '<a:custGeom>' in result
        assert 'w="21600" h="21600"' in result  # Should use full range
        assert '<a:moveTo><a:pt x="0" y="0"/></a:moveTo>' in result
        assert '<a:lnTo><a:pt x="21600" y="0"/></a:lnTo>' in result

    def test_generate_custgeom_with_userspaceonuse(self):
        """Test full custGeom generation with userSpaceOnUse coordinates."""
        clip_def = ClipPathDefinition(
            id='user_clip',
            units='userSpaceOnUse',
            clip_rule='nonzero',
            path_data='M 0 0 L 100 100 Z',
            clipping_type=ClippingType.PATH_BASED
        )

        result = self.generator.generate_custgeom_xml(clip_def, self.context)

        assert '<a:custGeom>' in result
        assert 'w="10800" h="14400"' in result  # Should use scaled viewport
        assert '<a:moveTo><a:pt x="0" y="0"/></a:moveTo>' in result

    def test_generate_custgeom_with_clippath_transform(self):
        """Test custGeom generation with clipPath transform."""
        clip_def = ClipPathDefinition(
            id='transform_clip',
            units='userSpaceOnUse',
            clip_rule='nonzero',
            path_data='M 0 0 L 50 50 Z',
            transform='scale(2)',
            clipping_type=ClippingType.PATH_BASED
        )

        result = self.generator.generate_custgeom_xml(clip_def, self.context)

        assert '<a:custGeom>' in result
        # Transform should be applied (currently just logged)
        assert '<a:moveTo>' in result

    def test_rect_conversion_with_coordinate_context(self):
        """Test rectangle conversion with coordinate context."""
        rect = create_svg_element('rect', x=10, y=20, width=100, height=50)

        coord_context = CoordinateContext(
            units='userSpaceOnUse',
            scale_x=100,
            scale_y=100,
            offset_x=0,
            offset_y=0,
            base_context=self.context
        )

        result = self.generator._convert_rect_to_path(rect, coord_context)

        assert '<a:moveTo><a:pt x="1000" y="2000"/></a:moveTo>' in result  # 10*100, 20*100
        assert '<a:lnTo><a:pt x="11000" y="7000"/></a:lnTo>' in result    # (10+100)*100, (20+50)*100

    def test_coordinate_validation_edge_cases(self):
        """Test coordinate handling with edge cases."""
        # Test zero dimensions
        coord_context = CoordinateContext(
            units='objectBoundingBox',
            scale_x=21600,
            scale_y=21600,
            offset_x=0,
            offset_y=0,
            base_context=self.context
        )

        x, y = self.generator._scale_coordinates_with_context(0, 0, coord_context)
        assert x == 0
        assert y == 0

        # Test negative coordinates
        x, y = self.generator._scale_coordinates_with_context(-0.5, -0.25, coord_context)
        assert x == -10800
        assert y == -5400

    def test_coordinate_context_dataclass(self):
        """Test CoordinateContext dataclass functionality."""
        coord_context = CoordinateContext(
            units='userSpaceOnUse',
            scale_x=100,
            scale_y=200,
            offset_x=10,
            offset_y=20,
            base_context=self.context
        )

        assert coord_context.units == 'userSpaceOnUse'
        assert coord_context.scale_x == 100
        assert coord_context.scale_y == 200
        assert coord_context.offset_x == 10
        assert coord_context.offset_y == 20
        assert coord_context.base_context == self.context


if __name__ == '__main__':
    pytest.main([__file__, '-v'])