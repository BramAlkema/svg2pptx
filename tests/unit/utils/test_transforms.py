#!/usr/bin/env python3
"""
Unit Tests for Transforms Module

Comprehensive tests for SVG transform parsing and matrix operations
including translate, scale, rotate, skew, and matrix transformations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from pathlib import Path
import sys
from lxml import etree as ET
import math

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.transforms import TransformParser, parse_transform, Matrix

class TestTransformParser:
    """Test cases for TransformParser class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.parser = TransformParser()

    # Initialization Tests
    def test_initialization(self):
        """Test TransformParser initialization."""
        parser = TransformParser()
        assert parser is not None

    # Translate Transform Tests
    def test_translate_single_value(self):
        """Test translate transform with single value."""
        result = self.parser.parse("translate(10)")
        expected = Matrix()
        expected.translate(10, 0)
        assert self._matrices_equal(result, expected)

    def test_translate_two_values(self):
        """Test translate transform with x and y values."""
        result = self.parser.parse("translate(10, 20)")
        expected = Matrix()
        expected.translate(10, 20)
        assert self._matrices_equal(result, expected)

    def test_translate_negative_values(self):
        """Test translate transform with negative values."""
        result = self.parser.parse("translate(-10, -20)")
        expected = Matrix()
        expected.translate(-10, -20)
        assert self._matrices_equal(result, expected)

    def test_translate_float_values(self):
        """Test translate transform with float values."""
        result = self.parser.parse("translate(10.5, 20.7)")
        expected = Matrix()
        expected.translate(10.5, 20.7)
        assert self._matrices_equal(result, expected)

    # Scale Transform Tests
    def test_scale_single_value(self):
        """Test scale transform with single value."""
        result = self.parser.parse("scale(2)")
        expected = Matrix()
        expected.scale(2, 2)
        assert self._matrices_equal(result, expected)

    def test_scale_two_values(self):
        """Test scale transform with x and y scale factors."""
        result = self.parser.parse("scale(2, 3)")
        expected = Matrix()
        expected.scale(2, 3)
        assert self._matrices_equal(result, expected)

    def test_scale_fractional_values(self):
        """Test scale transform with fractional values."""
        result = self.parser.parse("scale(0.5, 1.5)")
        expected = Matrix()
        expected.scale(0.5, 1.5)
        assert self._matrices_equal(result, expected)

    def test_scale_negative_values(self):
        """Test scale transform with negative values (flip)."""
        result = self.parser.parse("scale(-1, 1)")
        expected = Matrix()
        expected.scale(-1, 1)
        assert self._matrices_equal(result, expected)

    # Rotate Transform Tests
    def test_rotate_angle_only(self):
        """Test rotate transform with angle only."""
        result = self.parser.parse("rotate(45)")
        expected = Matrix()
        expected.rotate(math.radians(45))
        assert self._matrices_equal(result, expected)

    def test_rotate_with_center_point(self):
        """Test rotate transform with center point."""
        result = self.parser.parse("rotate(45, 100, 100)")
        expected = Matrix()
        expected.translate(100, 100)
        expected.rotate(math.radians(45))
        expected.translate(-100, -100)
        assert self._matrices_equal(result, expected)

    def test_rotate_negative_angle(self):
        """Test rotate transform with negative angle."""
        result = self.parser.parse("rotate(-90)")
        expected = Matrix()
        expected.rotate(math.radians(-90))
        assert self._matrices_equal(result, expected)

    def test_rotate_float_angle(self):
        """Test rotate transform with float angle."""
        result = self.parser.parse("rotate(45.5)")
        expected = Matrix()
        expected.rotate(math.radians(45.5))
        assert self._matrices_equal(result, expected)

    # Skew Transform Tests
    def test_skewX_transform(self):
        """Test skewX transform."""
        result = self.parser.parse("skewX(30)")
        expected = Matrix()
        expected.skew_x(math.radians(30))
        assert self._matrices_equal(result, expected)

    def test_skewY_transform(self):
        """Test skewY transform."""
        result = self.parser.parse("skewY(30)")
        expected = Matrix()
        expected.skew_y(math.radians(30))
        assert self._matrices_equal(result, expected)

    def test_skew_negative_angles(self):
        """Test skew transforms with negative angles."""
        result_x = self.parser.parse("skewX(-15)")
        result_y = self.parser.parse("skewY(-15)")

        expected_x = Matrix()
        expected_x.skew_x(math.radians(-15))
        expected_y = Matrix()
        expected_y.skew_y(math.radians(-15))

        assert self._matrices_equal(result_x, expected_x)
        assert self._matrices_equal(result_y, expected_y)

    # Matrix Transform Tests
    def test_matrix_transform(self):
        """Test matrix transform with all six values."""
        result = self.parser.parse("matrix(1, 0, 0, 1, 10, 20)")
        expected = Matrix(1, 0, 0, 1, 10, 20)
        assert self._matrices_equal(result, expected)

    def test_matrix_transform_scaling(self):
        """Test matrix transform for scaling."""
        result = self.parser.parse("matrix(2, 0, 0, 3, 0, 0)")
        expected = Matrix(2, 0, 0, 3, 0, 0)
        assert self._matrices_equal(result, expected)

    def test_matrix_transform_complex(self):
        """Test complex matrix transform."""
        result = self.parser.parse("matrix(1.5, 0.5, -0.5, 1.5, 100, 200)")
        expected = Matrix(1.5, 0.5, -0.5, 1.5, 100, 200)
        assert self._matrices_equal(result, expected)

    # Multiple Transform Tests
    def test_multiple_transforms_translate_scale(self):
        """Test multiple transforms: translate then scale."""
        result = self.parser.parse("translate(10, 20) scale(2)")
        expected = Matrix()
        expected.translate(10, 20)
        expected.scale(2, 2)
        assert self._matrices_equal(result, expected)

    def test_multiple_transforms_scale_rotate(self):
        """Test multiple transforms: scale then rotate."""
        result = self.parser.parse("scale(2) rotate(45)")
        expected = Matrix()
        expected.scale(2, 2)
        expected.rotate(math.radians(45))
        assert self._matrices_equal(result, expected)

    def test_multiple_transforms_complex(self):
        """Test complex multiple transforms."""
        result = self.parser.parse("translate(100, 100) rotate(45) scale(0.5) translate(-50, -50)")
        expected = Matrix()
        expected.translate(100, 100)
        expected.rotate(math.radians(45))
        expected.scale(0.5, 0.5)
        expected.translate(-50, -50)
        assert self._matrices_equal(result, expected)

    # Edge Cases
    def test_empty_transform_string(self):
        """Test parsing empty transform string."""
        result = self.parser.parse("")
        expected = Matrix()  # Identity matrix
        assert self._matrices_equal(result, expected)

    def test_none_transform_string(self):
        """Test parsing None transform string."""
        result = self.parser.parse(None)
        expected = Matrix()  # Identity matrix
        assert self._matrices_equal(result, expected)

    def test_whitespace_in_transforms(self):
        """Test parsing transforms with extra whitespace."""
        result = self.parser.parse("  translate( 10 , 20 )  scale( 2 )  ")
        expected = Matrix()
        expected.translate(10, 20)
        expected.scale(2, 2)
        assert self._matrices_equal(result, expected)

    def test_comma_separated_values(self):
        """Test parsing transforms with comma-separated values."""
        result = self.parser.parse("translate(10,20) scale(2,3)")
        expected = Matrix()
        expected.translate(10, 20)
        expected.scale(2, 3)
        assert self._matrices_equal(result, expected)

    # Error Handling
    def test_invalid_transform_name(self):
        """Test parsing invalid transform name."""
        with pytest.raises(ValueError):
            self.parser.parse("invalid(10, 20)")

    def test_invalid_parameter_count(self):
        """Test parsing transform with wrong parameter count."""
        with pytest.raises(ValueError):
            self.parser.parse("matrix(1, 0, 0)")  # Matrix needs 6 parameters

    def test_invalid_numeric_values(self):
        """Test parsing transform with invalid numeric values."""
        with pytest.raises(ValueError):
            self.parser.parse("translate(invalid, 20)")

    def test_unclosed_parentheses(self):
        """Test parsing transform with unclosed parentheses."""
        with pytest.raises(ValueError):
            self.parser.parse("translate(10, 20")

    def test_missing_parameters(self):
        """Test parsing transform with missing parameters."""
        with pytest.raises(ValueError):
            self.parser.parse("translate()")

    # Helper method
    def _matrices_equal(self, matrix1, matrix2, tolerance=1e-10):
        """Check if two matrices are approximately equal."""
        return (abs(matrix1.a - matrix2.a) < tolerance and
                abs(matrix1.b - matrix2.b) < tolerance and
                abs(matrix1.c - matrix2.c) < tolerance and
                abs(matrix1.d - matrix2.d) < tolerance and
                abs(matrix1.e - matrix2.e) < tolerance and
                abs(matrix1.f - matrix2.f) < tolerance)


class TestMatrix:
    """Test cases for Matrix class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.matrix = Matrix()

    # Initialization Tests
    def test_identity_matrix_initialization(self):
        """Test Matrix initialization as identity matrix."""
        matrix = Matrix()
        assert matrix.a == 1 and matrix.b == 0
        assert matrix.c == 0 and matrix.d == 1
        assert matrix.e == 0 and matrix.f == 0

    def test_custom_matrix_initialization(self):
        """Test Matrix initialization with custom values."""
        matrix = Matrix(2, 0.5, -0.5, 2, 100, 200)
        assert matrix.a == 2 and matrix.b == 0.5
        assert matrix.c == -0.5 and matrix.d == 2
        assert matrix.e == 100 and matrix.f == 200

    # Translation Tests
    def test_translate_positive_values(self):
        """Test matrix translation with positive values."""
        self.matrix.translate(10, 20)
        assert self.matrix.e == 10
        assert self.matrix.f == 20

    def test_translate_negative_values(self):
        """Test matrix translation with negative values."""
        self.matrix.translate(-10, -20)
        assert self.matrix.e == -10
        assert self.matrix.f == -20

    def test_multiple_translations(self):
        """Test multiple matrix translations."""
        self.matrix.translate(10, 20)
        self.matrix.translate(5, 15)
        assert self.matrix.e == 15
        assert self.matrix.f == 35

    # Scaling Tests
    def test_scale_uniform(self):
        """Test uniform matrix scaling."""
        self.matrix.scale(2, 2)
        assert self.matrix.a == 2
        assert self.matrix.d == 2

    def test_scale_non_uniform(self):
        """Test non-uniform matrix scaling."""
        self.matrix.scale(2, 3)
        assert self.matrix.a == 2
        assert self.matrix.d == 3

    def test_scale_fractional(self):
        """Test fractional matrix scaling."""
        self.matrix.scale(0.5, 1.5)
        assert self.matrix.a == 0.5
        assert self.matrix.d == 1.5

    # Rotation Tests
    def test_rotate_90_degrees(self):
        """Test 90-degree rotation."""
        self.matrix.rotate(math.pi / 2)  # 90 degrees in radians
        assert abs(self.matrix.a - 0) < 1e-10
        assert abs(self.matrix.b - 1) < 1e-10
        assert abs(self.matrix.c - (-1)) < 1e-10
        assert abs(self.matrix.d - 0) < 1e-10

    def test_rotate_45_degrees(self):
        """Test 45-degree rotation."""
        self.matrix.rotate(math.pi / 4)  # 45 degrees in radians
        sqrt2_half = math.sqrt(2) / 2
        assert abs(self.matrix.a - sqrt2_half) < 1e-10
        assert abs(self.matrix.b - sqrt2_half) < 1e-10
        assert abs(self.matrix.c - (-sqrt2_half)) < 1e-10
        assert abs(self.matrix.d - sqrt2_half) < 1e-10

    # Skew Tests
    def test_skew_x(self):
        """Test X-axis skew transformation."""
        self.matrix.skew_x(math.pi / 6)  # 30 degrees
        expected_c = math.tan(math.pi / 6)
        assert abs(self.matrix.c - expected_c) < 1e-10
        assert self.matrix.a == 1 and self.matrix.d == 1

    def test_skew_y(self):
        """Test Y-axis skew transformation."""
        self.matrix.skew_y(math.pi / 6)  # 30 degrees
        expected_b = math.tan(math.pi / 6)
        assert abs(self.matrix.b - expected_b) < 1e-10
        assert self.matrix.a == 1 and self.matrix.d == 1

    # Matrix Multiplication Tests
    def test_multiply_identity(self):
        """Test multiplying with identity matrix."""
        original = Matrix(2, 0, 0, 2, 10, 20)
        identity = Matrix()
        result = original.multiply(identity)

        assert result.a == 2 and result.d == 2
        assert result.e == 10 and result.f == 20

    def test_multiply_translation_scaling(self):
        """Test multiplying translation and scaling matrices."""
        translate = Matrix(1, 0, 0, 1, 10, 20)
        scale = Matrix(2, 0, 0, 2, 0, 0)
        result = translate.multiply(scale)

        assert result.a == 2 and result.d == 2
        assert result.e == 10 and result.f == 20

    # Point Transformation Tests
    def test_transform_point_identity(self):
        """Test transforming point with identity matrix."""
        point = (10, 20)
        result = self.matrix.transform_point(point)
        assert result == (10, 20)

    def test_transform_point_translation(self):
        """Test transforming point with translation."""
        self.matrix.translate(5, 10)
        point = (10, 20)
        result = self.matrix.transform_point(point)
        assert result == (15, 30)

    def test_transform_point_scaling(self):
        """Test transforming point with scaling."""
        self.matrix.scale(2, 3)
        point = (10, 20)
        result = self.matrix.transform_point(point)
        assert result == (20, 60)

    def test_transform_point_rotation(self):
        """Test transforming point with rotation."""
        self.matrix.rotate(math.pi / 2)  # 90 degrees
        point = (10, 0)
        result = self.matrix.transform_point(point)
        assert abs(result[0] - 0) < 1e-10
        assert abs(result[1] - 10) < 1e-10


class TestParseTransform:
    """Test cases for parse_transform utility function."""

    def test_parse_single_transform(self):
        """Test parsing single transform string."""
        result = parse_transform("translate(10, 20)")
        assert result is not None

    def test_parse_multiple_transforms(self):
        """Test parsing multiple transform string."""
        result = parse_transform("translate(10, 20) scale(2) rotate(45)")
        assert result is not None

    def test_parse_matrix_transform(self):
        """Test parsing matrix transform string."""
        result = parse_transform("matrix(1, 0, 0, 1, 10, 20)")
        assert result is not None

    def test_parse_empty_string(self):
        """Test parsing empty transform string."""
        result = parse_transform("")
        assert result is not None

    def test_parse_none_string(self):
        """Test parsing None transform string."""
        result = parse_transform(None)
        # May return None or identity matrix

    def test_parse_with_whitespace(self):
        """Test parsing transform string with extra whitespace."""
        result = parse_transform("  translate( 10 , 20 )  ")
        assert result is not None


# Integration Tests
class TestTransformIntegration:
    """Integration tests for transform parsing with SVG elements."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.parser = TransformParser()

    def test_svg_element_transform_parsing(self):
        """Test parsing transforms from SVG element."""
        svg = ET.fromstring('<rect transform="translate(10, 20) scale(2)" />')
        transform_str = svg.get('transform')
        result = self.parser.parse(transform_str)

        # Should have combined translation and scaling
        assert result.e == 10  # Translation X
        assert result.f == 20  # Translation Y
        assert result.a == 2   # Scale X
        assert result.d == 2   # Scale Y

    def test_nested_svg_transforms(self):
        """Test parsing transforms from nested SVG elements."""
        svg = ET.fromstring('''
            <g transform="translate(100, 100)">
                <rect transform="scale(2) rotate(45)" />
            </g>
        ''')

        group_transform = self.parser.parse(svg.get('transform'))
        rect_transform = self.parser.parse(svg.find('rect').get('transform'))

        # Combine transforms (group then rect)
        combined = group_transform.multiply(rect_transform)

        # Should have translation from group plus scale/rotate from rect
        assert combined.e == 100  # Translation from group
        assert combined.f == 100  # Translation from group
        # Scale and rotation would modify a, b, c, d values


# Performance Tests
class TestTransformPerformance:
    """Performance tests for transform parsing."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.parser = TransformParser()

    @pytest.mark.performance
    def test_simple_transform_performance(self):
        """Test performance of simple transform parsing."""
        import time

        transform_str = "translate(10, 20)"
        iterations = 1000

        start_time = time.time()
        for _ in range(iterations):
            self.parser.parse(transform_str)
        end_time = time.time()

        duration = end_time - start_time
        assert duration < 1.0  # Should complete 1000 parses in less than 1 second

    @pytest.mark.performance
    def test_complex_transform_performance(self):
        """Test performance of complex transform parsing."""
        import time

        transform_str = "translate(100, 100) rotate(45) scale(0.5) skewX(15)"
        iterations = 500

        start_time = time.time()
        for _ in range(iterations):
            self.parser.parse(transform_str)
        end_time = time.time()

        duration = end_time - start_time
        assert duration < 2.0  # Should complete 500 complex parses in less than 2 seconds


if __name__ == "__main__":
    pytest.main([__file__, "-v"])