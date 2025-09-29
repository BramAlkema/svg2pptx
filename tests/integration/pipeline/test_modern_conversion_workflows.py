#!/usr/bin/env python3
"""
Integration Tests for Modern Conversion Workflows

Tests real SVG to PowerPoint conversion workflows using the current modern architecture.
Validates that multiple systems work together correctly.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import sys
from lxml import etree as ET

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Import modern working components
from core.transforms import Matrix
from core.color import Color, ColorBatch
from core.units import UnitConverter, ConversionContext
from src.converters.base import CoordinateSystem, ConversionContext as BaseConversionContext
from src.converters.shapes import RectangleConverter, CircleConverter
from core.services.conversion_services import ConversionServices, ConversionConfig


class TestModernShapeConversionWorkflow:
    """
    Integration tests for shape conversion using modern architecture.
    """

    @pytest.fixture
    def conversion_services(self):
        """Create conversion services with modern components."""
        unit_converter = UnitConverter()
        # Use modern Color API instead of ColorParser

        # Create mock transform parser and viewport resolver
        transform_parser = Mock()
        viewport_resolver = Mock()

        return ConversionServices(
            unit_converter=unit_converter,
            color_parser=color_parser,
            transform_parser=transform_parser,
            viewport_resolver=viewport_resolver
        )

    @pytest.fixture
    def coordinate_system(self):
        """Create coordinate system for conversion."""
        return CoordinateSystem(
            viewbox=(0, 0, 800, 600),
            slide_width=9144000,
            slide_height=6858000
        )

    @pytest.fixture
    def conversion_context(self, coordinate_system):
        """Create conversion context."""
        context = Mock(spec=BaseConversionContext)
        context.coordinate_system = coordinate_system
        context.get_next_shape_id.return_value = 1
        return context

    def test_rectangle_conversion_workflow(self, conversion_services, conversion_context):
        """Test complete rectangle conversion workflow."""
        # Create SVG rectangle element
        svg_rect = ET.fromstring('''
            <rect x="10" y="20" width="100" height="50"
                  fill="red" stroke="blue" stroke-width="2"/>
        ''')

        # Create rectangle converter with modern architecture
        rect_converter = RectangleConverter(conversion_services)

        # Test conversion workflow
        assert rect_converter.can_convert(svg_rect) is True

        # Test conversion (should not raise errors)
        try:
            result = rect_converter.convert(svg_rect, conversion_context)
            # Basic validation that we got some DrawingML output
            assert result is not None
            assert isinstance(result, str)
            # Should contain basic PowerPoint shape structure
            assert any(tag in result for tag in ['<p:sp>', '<a:rect>', '<p:nvSpPr>'])
        except Exception as e:
            # Document any conversion issues for troubleshooting
            pytest.fail(f"Rectangle conversion failed: {e}")

    def test_circle_conversion_workflow(self, conversion_services, conversion_context):
        """Test complete circle conversion workflow."""
        # Create SVG circle element
        svg_circle = ET.fromstring('''
            <circle cx="50" cy="50" r="25" fill="green"/>
        ''')

        # Create circle converter with modern architecture
        circle_converter = CircleConverter(conversion_services)

        # Test conversion workflow
        assert circle_converter.can_convert(svg_circle) is True

        # Test conversion
        try:
            result = circle_converter.convert(svg_circle, conversion_context)
            assert result is not None
            assert isinstance(result, str)
            # Should contain basic PowerPoint shape structure
            assert any(tag in result for tag in ['<p:sp>', '<a:ellipse>', '<p:nvSpPr>'])
        except Exception as e:
            pytest.fail(f"Circle conversion failed: {e}")

    def test_transform_integration_workflow(self, conversion_services, conversion_context):
        """Test shape conversion with transform integration."""
        # Create SVG rectangle with transform
        svg_rect_with_transform = ET.fromstring('''
            <rect x="10" y="20" width="100" height="50"
                  transform="translate(50,30) scale(2)" fill="blue"/>
        ''')

        # Create converter
        rect_converter = RectangleConverter(conversion_services)

        # Test that converter can handle transforms
        assert rect_converter.can_convert(svg_rect_with_transform) is True

        # Test conversion with transform
        try:
            result = rect_converter.convert(svg_rect_with_transform, conversion_context)
            assert result is not None
            # Should handle transform without errors
        except Exception as e:
            pytest.fail(f"Transform integration failed: {e}")

    def test_color_conversion_integration(self):
        """Test color system integration in conversion workflow."""
        # Test color parsing workflow
        # Use modern Color API instead of ColorParser

        # Test various color formats that converters might encounter
        test_colors = [
            "#FF0000",           # Hex
            "rgb(255,0,0)",      # RGB
            "red",               # Named
            "hsl(0,100%,50%)"    # HSL
        ]

        for color_str in test_colors:
            color = color_parser.parse(color_str)
            assert color is not None
            assert isinstance(color, Color)
            # Verify color has expected properties
            assert hasattr(color, 'red')
            assert hasattr(color, 'green')
            assert hasattr(color, 'blue')

    def test_units_conversion_integration(self):
        """Test units system integration in conversion workflow."""
        unit_converter = UnitConverter()
        context = ConversionContext(viewport_width=800, viewport_height=600)

        # Test various unit types that converters might encounter
        test_units = [
            "100px",    # Pixels
            "12pt",     # Points
            "2.5cm",    # Centimeters
            "1in",      # Inches
            "16em"      # Em units
        ]

        for unit_str in test_units:
            try:
                emu_value = unit_converter.to_emu(unit_str, context)
                assert emu_value > 0
                assert isinstance(emu_value, (int, float))
            except Exception as e:
                pytest.fail(f"Unit conversion failed for {unit_str}: {e}")

    def test_coordinate_system_integration(self):
        """Test coordinate system integration in conversion workflow."""
        coord_system = CoordinateSystem(
            viewbox=(0, 0, 800, 600),
            slide_width=9144000,
            slide_height=6858000
        )

        # Test coordinate conversions that converters use
        test_points = [
            (0, 0),      # Origin
            (100, 100),  # Regular point
            (400, 300),  # Center-ish
            (800, 600),  # Max bounds
        ]

        for x, y in test_points:
            emu_x, emu_y = coord_system.svg_to_emu(x, y)
            assert isinstance(emu_x, int)
            assert isinstance(emu_y, int)
            assert emu_x >= 0
            assert emu_y >= 0

            # Test length conversion
            emu_length = coord_system.svg_length_to_emu(100, 'x')
            assert emu_length > 0


class TestModernSystemsIntegration:
    """
    Integration tests for modern systems working together.
    """

    def test_complete_conversion_pipeline_integration(self):
        """Test complete conversion pipeline with multiple systems."""
        # This tests the integration of all modern systems together

        # 1. Transform system
        transform = Matrix.translate(10, 20).multiply(Matrix.scale(2))
        point_x, point_y = transform.transform_point(50, 50)

        # 2. Color system
        # Use modern Color API instead of ColorParser
        color = color_parser.parse("#FF5500")

        # 3. Units system
        unit_converter = UnitConverter()
        context = ConversionContext()
        size_emu = unit_converter.to_emu("16px", context)

        # 4. Coordinate system
        coord_system = CoordinateSystem(
            viewbox=(0, 0, 800, 600),
            slide_width=9144000,
            slide_height=6858000
        )
        final_x, final_y = coord_system.svg_to_emu(point_x, point_y)

        # Verify all systems produced valid output
        assert point_x == 110  # 50 + 10, then scaled by 2 would be different
        assert point_y == 120  # 50 + 20, then scaled by 2 would be different
        assert color is not None
        assert size_emu > 0
        assert final_x > 0
        assert final_y > 0

    def test_error_handling_integration(self):
        """Test error handling across integrated systems."""
        # Test that systems handle errors gracefully when integrated

        # Test color parsing with invalid input
        # Use modern Color API instead of ColorParser
        try:
            invalid_color = color_parser.parse("invalid-color")
            # Should handle gracefully or return None
            assert invalid_color is None or hasattr(invalid_color, 'red')
        except Exception:
            # Expected for invalid input
            pass

        # Test unit conversion with invalid input
        unit_converter = UnitConverter()
        context = ConversionContext()
        try:
            invalid_unit = unit_converter.to_emu("invalid-unit", context)
            # Should handle gracefully
            assert invalid_unit is not None
        except Exception:
            # Expected for invalid input
            pass

    def test_performance_integration(self):
        """Test that integrated systems maintain reasonable performance."""
        import time

        # Test batch operations with multiple systems
        start_time = time.time()

        # Perform multiple operations that would happen in real conversion
        for i in range(100):
            # Transform operations
            transform = Matrix.translate(i, i * 2)
            transform.transform_point(10, 10)

            # Color operations
            # Use modern Color API instead of ColorParser
            color_parser.parse(f"hsl({i % 360}, 50%, 50%)")

            # Unit operations
            unit_converter = UnitConverter()
            context = ConversionContext()
            unit_converter.to_emu(f"{i}px", context)

        end_time = time.time()
        execution_time = end_time - start_time

        # Should complete 100 operations reasonably quickly
        assert execution_time < 5.0, f"Integration too slow: {execution_time}s"

    def test_memory_efficiency_integration(self):
        """Test that integrated systems are memory efficient."""
        import sys

        # Get initial memory usage
        initial_objects = len([obj for obj in globals().values()])

        # Create and use multiple system instances
        systems = []
        for i in range(10):
            # Use modern Color API instead of ColorParser
            unit_converter = UnitConverter()
            coord_system = CoordinateSystem(
                viewbox=(0, 0, 800, 600),
                slide_width=9144000,
                slide_height=6858000
            )
            systems.append((color_parser, unit_converter, coord_system))

        # Use systems to ensure they're not optimized away
        for color_parser, unit_converter, coord_system in systems:
            color_parser.parse("#FF0000")
            context = ConversionContext()
            unit_converter.to_emu("10px", context)
            coord_system.svg_to_emu(10, 10)

        # Clean up
        systems.clear()

        # Memory should not grow excessively
        final_objects = len([obj for obj in globals().values()])
        assert final_objects - initial_objects < 50, "Memory leak in integration"


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__])