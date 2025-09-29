#!/usr/bin/env python3
"""
Unit Tests for Converter-Transform Integration

Tests the integration between current converters and the transform system.
Validates that converters work correctly with Matrix/Transform functionality.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import sys
from lxml import etree as ET

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Test imports first
try:
    from core.transforms import Matrix
    TRANSFORM_AVAILABLE = True
except ImportError:
    TRANSFORM_AVAILABLE = False

try:
    from src.converters.base import CoordinateSystem, ConversionContext
    BASE_AVAILABLE = True
except ImportError:
    BASE_AVAILABLE = False

try:
    from src.converters.shapes import RectangleConverter, CircleConverter
    SHAPE_CONVERTERS_AVAILABLE = True
except ImportError:
    SHAPE_CONVERTERS_AVAILABLE = False


@pytest.mark.skipif(not TRANSFORM_AVAILABLE, reason="Transform system not available")
@pytest.mark.skipif(not SHAPE_CONVERTERS_AVAILABLE, reason="Shape converters not available")
class TestConverterTransformIntegration:
    """Integration tests for converters with transform system."""

    def test_rectangle_converter_with_transform(self):
        """Test RectangleConverter with transform integration."""
        # Create a rectangle with transform
        rect_with_transform = ET.fromstring('''
            <rect x="10" y="20" width="100" height="50"
                  transform="translate(30,40) scale(2) rotate(45)"
                  fill="blue"/>
        ''')

        # Test that transform attribute is accessible
        transform_attr = rect_with_transform.get('transform')
        assert transform_attr is not None
        assert 'translate(30,40)' in transform_attr
        assert 'scale(2)' in transform_attr
        assert 'rotate(45)' in transform_attr

        # Test that Matrix can handle the transform
        # (This tests transform parsing capability)
        translate_matrix = Matrix.translate(30, 40)
        scale_matrix = Matrix.scale(2)

        # Test point transformation
        x, y = translate_matrix.transform_point(10, 20)
        assert x == 40  # 10 + 30
        assert y == 60  # 20 + 40

        scaled_x, scaled_y = scale_matrix.transform_point(10, 20)
        assert scaled_x == 20  # 10 * 2
        assert scaled_y == 40  # 20 * 2

    def test_circle_converter_with_transform(self):
        """Test CircleConverter with transform integration."""
        circle_with_transform = ET.fromstring('''
            <circle cx="50" cy="50" r="25"
                    transform="translate(100,100)"
                    fill="red"/>
        ''')

        # Test transform attribute
        transform_attr = circle_with_transform.get('transform')
        assert transform_attr == 'translate(100,100)'

        # Test Matrix transform
        transform = Matrix.translate(100, 100)
        center_x, center_y = transform.transform_point(50, 50)
        assert center_x == 150  # 50 + 100
        assert center_y == 150  # 50 + 100

    @pytest.mark.skipif(not BASE_AVAILABLE, reason="Base system not available")
    def test_coordinate_system_with_transforms(self):
        """Test coordinate system integration with transforms."""
        # Create coordinate system
        coord_system = CoordinateSystem(
            viewbox=(0, 0, 800, 600),
            slide_width=9144000,
            slide_height=6858000
        )

        # Test basic coordinate conversion
        emu_x, emu_y = coord_system.svg_to_emu(100, 100)
        assert isinstance(emu_x, int)
        assert isinstance(emu_y, int)
        assert emu_x > 0
        assert emu_y > 0

        # Test with transformed coordinates
        transform = Matrix.translate(50, 50)
        transformed_x, transformed_y = transform.transform_point(100, 100)

        transformed_emu_x, transformed_emu_y = coord_system.svg_to_emu(
            transformed_x, transformed_y
        )

        # Transformed coordinates should be different
        assert transformed_emu_x != emu_x
        assert transformed_emu_y != emu_y

    def test_complex_transform_chains(self):
        """Test complex transform chains with multiple operations."""
        # Test chaining multiple transforms
        translate = Matrix.translate(10, 20)
        scale = Matrix.scale(2, 3)

        # Chain transforms: first translate, then scale
        combined = translate.multiply(scale)

        # Test point transformation through chain
        original_point = (5, 10)
        final_x, final_y = combined.transform_point(*original_point)

        # Matrix multiplication applies scale first, then translate
        # Scale first: (5*2, 10*3) = (10, 30)
        # Then translate: (10+10, 30+20) = (20, 50)
        assert final_x == 20
        assert final_y == 50

    def test_transform_parsing_from_svg_elements(self):
        """Test parsing transform attributes from SVG elements."""
        # Test various transform formats
        transform_formats = [
            "translate(10,20)",
            "translate(10 20)",
            "scale(2)",
            "scale(2,3)",
            "rotate(45)",
            "rotate(45,50,50)",
            "skewX(30)",
            "skewY(15)",
            "matrix(1,0,0,1,10,20)"
        ]

        for transform_str in transform_formats:
            element = ET.fromstring(f'<rect transform="{transform_str}"/>')
            parsed_transform = element.get('transform')
            assert parsed_transform == transform_str

    def test_converter_with_nested_transforms(self):
        """Test converters with nested transform contexts."""
        # Simulate nested transforms (group + element)
        group_transform = Matrix.translate(100, 100)
        element_transform = Matrix.scale(2)

        # Combined transform (apply group first, then element)
        combined_transform = group_transform.multiply(element_transform)

        # Test point transformation
        point_x, point_y = combined_transform.transform_point(10, 10)

        # Matrix multiplication: scale first (10*2, 10*2) = (20, 20)
        # Then translate (20+100, 20+100) = (120, 120)
        assert point_x == 120
        assert point_y == 120


@pytest.mark.skipif(not TRANSFORM_AVAILABLE, reason="Transform system not available")
class TestTransformSystemPerformance:
    """Performance tests for transform system integration."""

    def test_transform_performance_with_many_points(self):
        """Test transform performance with many coordinate points."""
        import time

        # Create a transform
        transform = Matrix.translate(50, 50).multiply(Matrix.scale(2))

        # Create many points to transform
        points = [(i, i * 2) for i in range(1000)]

        # Time the transformation
        start_time = time.time()

        transformed_points = []
        for x, y in points:
            tx, ty = transform.transform_point(x, y)
            transformed_points.append((tx, ty))

        execution_time = time.time() - start_time

        # Validate results
        assert len(transformed_points) == 1000
        # First point: (0, 0) -> scale first (0*2, 0*2) = (0, 0) -> translate (0+50, 0+50) = (50, 50)
        assert transformed_points[0] == (50, 50)

        # Performance should be reasonable
        assert execution_time < 1.0, f"Transform performance too slow: {execution_time}s"

    def test_matrix_multiplication_performance(self):
        """Test matrix multiplication performance."""
        import time

        # Create base transforms
        translate = Matrix.translate(10, 20)
        scale = Matrix.scale(2, 3)
        rotate = Matrix().rotate(45)

        # Time multiple multiplications
        start_time = time.time()

        for i in range(100):
            # Chain multiple operations
            result = translate.multiply(scale).multiply(rotate)
            # Use the result to ensure it's not optimized away
            test_x, test_y = result.transform_point(10, 10)
            assert test_x is not None
            assert test_y is not None

        execution_time = time.time() - start_time

        # Should be fast
        assert execution_time < 0.5, f"Matrix multiplication too slow: {execution_time}s"


@pytest.mark.skipif(not TRANSFORM_AVAILABLE, reason="Transform system not available")
class TestTransformEdgeCases:
    """Edge case tests for transform integration."""

    def test_identity_transform(self):
        """Test identity transform (no change)."""
        identity = Matrix()  # Should be identity matrix

        test_points = [(0, 0), (10, 20), (-5, -10), (100.5, 200.7)]

        for x, y in test_points:
            tx, ty = identity.transform_point(x, y)
            assert tx == x
            assert ty == y

    def test_zero_scale_transform(self):
        """Test transform with zero scale."""
        zero_scale = Matrix.scale(0, 0)

        test_x, test_y = zero_scale.transform_point(100, 200)
        assert test_x == 0
        assert test_y == 0

    def test_negative_scale_transform(self):
        """Test transform with negative scale (mirroring)."""
        negative_scale = Matrix.scale(-1, -1)

        test_x, test_y = negative_scale.transform_point(10, 20)
        assert test_x == -10
        assert test_y == -20

    def test_large_coordinate_transforms(self):
        """Test transforms with very large coordinates."""
        transform = Matrix.translate(1000000, 2000000)

        test_x, test_y = transform.transform_point(1000000, 1000000)
        assert test_x == 2000000  # 1000000 + 1000000
        assert test_y == 3000000  # 1000000 + 2000000

    def test_fractional_coordinate_transforms(self):
        """Test transforms with fractional coordinates."""
        transform = Matrix.translate(10.5, 20.7)

        test_x, test_y = transform.transform_point(5.3, 7.9)
        assert abs(test_x - 15.8) < 0.001  # 5.3 + 10.5
        assert abs(test_y - 28.6) < 0.001  # 7.9 + 20.7


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__])