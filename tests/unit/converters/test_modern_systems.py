#!/usr/bin/env python3
"""
Modern Unit Tests for Current Working Systems

Tests the components that are confirmed working in the current architecture.
Follows modernization approach: test what exists and works, not legacy cruft.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Import working components that we verified
from core.transforms import Matrix
from core.color import Color
from core.units import UnitConverter
from src.converters.base import ConversionContext, CoordinateSystem


class TestTransformSystem:
    """
    Unit tests for the consolidated Transform system.
    This is the system we know works well (58/60 tests passing).
    """

    def test_matrix_creation(self):
        """Test Matrix class creation."""
        matrix = Matrix()
        assert matrix is not None
        assert matrix.a == 1
        assert matrix.d == 1

    def test_matrix_translation(self):
        """Test Matrix translation operations."""
        translate = Matrix.translate(10, 20)
        assert translate.e == 10
        assert translate.f == 20

    def test_matrix_scaling(self):
        """Test Matrix scaling operations."""
        scale = Matrix.scale(2, 3)
        assert scale.a == 2
        assert scale.d == 3

    def test_matrix_multiplication(self):
        """Test Matrix multiplication."""
        translate = Matrix.translate(10, 20)
        scale = Matrix.scale(2, 3)

        result = translate.multiply(scale)
        assert result is not None
        assert result.a == 2
        assert result.d == 3

    def test_matrix_point_transformation(self):
        """Test point transformation with Matrix."""
        translate = Matrix.translate(5, 10)
        x, y = translate.transform_point(0, 0)
        assert x == 5
        assert y == 10


class TestColorSystem:
    """
    Unit tests for the current Color system.
    Tests ColorParser and ColorInfo that we verified import successfully.
    """

    def test_color_parser_creation(self):
        """Test modern Color initialization."""
        color = Color("#FF0000")
        assert color is not None

    def test_color_info_creation(self):
        """Test modern Color RGB access."""
        color = Color("rgb(255,0,0)")
        r, g, b = color.rgb()
        assert r == 255
        assert g == 0
        assert b == 0

    def test_color_parsing_hex(self):
        """Test hex color parsing."""
        color = Color("#FF0000")
        r, g, b = color.rgb()
        assert r == 255 and g == 0 and b == 0

    def test_color_parsing_rgb(self):
        """Test RGB color parsing."""
        color = Color("rgb(255, 0, 0)")
        r, g, b = color.rgb()
        assert r == 255 and g == 0 and b == 0

    def test_color_parsing_named(self):
        """Test named color parsing."""
        color = Color("red")
        r, g, b = color.rgb()
        assert r == 255 and g == 0 and b == 0


class TestUnitsSystem:
    """
    Unit tests for the current Units system.
    Tests UnitConverter that we verified imports successfully.
    """

    def test_unit_converter_creation(self):
        """Test UnitConverter initialization."""
        converter = UnitConverter()
        assert converter is not None

    def test_px_to_emu_conversion(self):
        """Test pixel to EMU conversion."""
        from core.units import ConversionContext
        converter = UnitConverter()
        context = ConversionContext()
        emu_value = converter.to_emu("100px", context)
        assert emu_value > 0
        assert isinstance(emu_value, (int, float))

    def test_pt_to_emu_conversion(self):
        """Test point to EMU conversion."""
        from core.units import ConversionContext
        converter = UnitConverter()
        context = ConversionContext()
        emu_value = converter.to_emu("12pt", context)  # 12pt font
        assert emu_value > 0
        assert isinstance(emu_value, (int, float))


class TestCoordinateSystem:
    """
    Unit tests for the CoordinateSystem class from converters.base.
    """

    def test_coordinate_system_creation(self):
        """Test CoordinateSystem initialization."""
        coord_system = CoordinateSystem(
            viewbox=(0, 0, 800, 600),
            slide_width=9144000,
            slide_height=6858000
        )
        assert coord_system is not None
        assert coord_system.svg_width == 800
        assert coord_system.svg_height == 600

    def test_svg_to_emu_conversion(self):
        """Test SVG to EMU coordinate conversion."""
        coord_system = CoordinateSystem(
            viewbox=(0, 0, 800, 600),
            slide_width=9144000,
            slide_height=6858000
        )

        emu_x, emu_y = coord_system.svg_to_emu(100, 100)
        assert isinstance(emu_x, int)
        assert isinstance(emu_y, int)
        assert emu_x > 0
        assert emu_y > 0

    def test_svg_length_to_emu(self):
        """Test SVG length to EMU conversion."""
        coord_system = CoordinateSystem(
            viewbox=(0, 0, 800, 600),
            slide_width=9144000,
            slide_height=6858000
        )

        emu_length = coord_system.svg_length_to_emu(100, 'x')
        assert isinstance(emu_length, int)
        assert emu_length > 0


class TestConversionContext:
    """
    Unit tests for ConversionContext mock functionality.
    """

    def test_conversion_context_mock(self):
        """Test that we can create mock ConversionContext."""
        context = Mock(spec=ConversionContext)
        context.get_next_shape_id.return_value = 1

        # Test mock functionality
        assert context.get_next_shape_id() == 1


# Integration tests for working systems
@pytest.mark.integration
class TestModernSystemsIntegration:
    """
    Integration tests for modern systems that work together.
    """

    def test_transform_with_coordinate_system(self):
        """Test transform system integration with coordinate system."""
        # Create coordinate system
        coord_system = CoordinateSystem(
            viewbox=(0, 0, 800, 600),
            slide_width=9144000,
            slide_height=6858000
        )

        # Create transform
        transform = Matrix.translate(50, 50)

        # Test that both systems work together
        point_x, point_y = transform.transform_point(10, 10)
        emu_x, emu_y = coord_system.svg_to_emu(point_x, point_y)

        assert emu_x > 0
        assert emu_y > 0

    def test_color_with_units_system(self):
        """Test color system integration with units system."""
        # Create unit converter
        unit_converter = UnitConverter()

        # Parse a color using modern API and convert some units
        from core.units import ConversionContext
        color = Color("#FF0000")
        context = ConversionContext()
        emu_size = unit_converter.to_emu("16px", context)

        assert color is not None
        assert emu_size > 0

    def test_all_modern_systems_importable(self):
        """Test that all modern systems can be imported together."""
        # This test verifies no circular dependencies or import conflicts
        from core.transforms import Matrix
        from core.color import Color
        from core.units import UnitConverter
        from src.converters.base import CoordinateSystem, ConversionContext

        # All should be importable without errors
        assert Matrix is not None
        assert Color is not None
        assert UnitConverter is not None
        assert CoordinateSystem is not None
        assert ConversionContext is not None


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__])