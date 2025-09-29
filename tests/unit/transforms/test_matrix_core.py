#!/usr/bin/env python3
"""
Comprehensive test suite for core Matrix implementation.

Tests all Matrix functionality including:
- Creation and initialization
- Classmethods (identity, translate, scale, rotate, skew)
- Matrix operations (multiply, inverse, transform)
- Analysis methods (is_identity, has_rotation, etc.)
- Decomposition and component extraction
"""

import pytest
import math
from typing import Tuple, List

from src.transforms.core import Matrix


class TestMatrixCreation:
    """Test Matrix creation and initialization."""

    def test_default_initialization(self):
        """Test default Matrix constructor creates identity matrix."""
        m = Matrix()
        assert m.a == 1
        assert m.b == 0
        assert m.c == 0
        assert m.d == 1
        assert m.e == 0
        assert m.f == 0

    def test_custom_initialization(self):
        """Test Matrix constructor with custom values."""
        m = Matrix(2, 3, 4, 5, 6, 7)
        assert m.a == 2
        assert m.b == 3
        assert m.c == 4
        assert m.d == 5
        assert m.e == 6
        assert m.f == 7

    def test_identity_classmethod(self):
        """Test Matrix.identity() creates proper identity matrix."""
        m = Matrix.identity()
        assert m.a == 1
        assert m.b == 0
        assert m.c == 0
        assert m.d == 1
        assert m.e == 0
        assert m.f == 0


class TestMatrixClassmethods:
    """Test Matrix classmethod constructors."""

    def test_translate(self):
        """Test Matrix.translate() creates correct translation matrix."""
        # Test with both x and y
        m = Matrix.translate(10, 20)
        assert m.a == 1
        assert m.b == 0
        assert m.c == 0
        assert m.d == 1
        assert m.e == 10
        assert m.f == 20

        # Test with only x (y defaults to 0)
        m = Matrix.translate(15)
        assert m.e == 15
        assert m.f == 0

    def test_scale(self):
        """Test Matrix.scale() creates correct scale matrix."""
        # Test with both sx and sy
        m = Matrix.scale(2, 3)
        assert m.a == 2
        assert m.b == 0
        assert m.c == 0
        assert m.d == 3
        assert m.e == 0
        assert m.f == 0

        # Test with only sx (uniform scaling)
        m = Matrix.scale(2.5)
        assert m.a == 2.5
        assert m.d == 2.5

    def test_rotate(self):
        """Test Matrix.rotate() creates correct rotation matrix."""
        # Test 90 degree rotation
        m = Matrix.rotate(90)
        assert abs(m.a - 0) < 1e-10  # cos(90°) = 0
        assert abs(m.b - 1) < 1e-10  # sin(90°) = 1
        assert abs(m.c - (-1)) < 1e-10  # -sin(90°) = -1
        assert abs(m.d - 0) < 1e-10  # cos(90°) = 0

        # Test 45 degree rotation
        m = Matrix.rotate(45)
        sqrt2_half = math.sqrt(2) / 2
        assert abs(m.a - sqrt2_half) < 1e-10
        assert abs(m.b - sqrt2_half) < 1e-10
        assert abs(m.c - (-sqrt2_half)) < 1e-10
        assert abs(m.d - sqrt2_half) < 1e-10

    def test_skew_x(self):
        """Test Matrix.skew_x() creates correct X-axis skew matrix."""
        m = Matrix.skew_x(30)
        tan_30 = math.tan(math.radians(30))
        assert m.a == 1
        assert m.b == 0
        assert abs(m.c - tan_30) < 1e-10
        assert m.d == 1
        assert m.e == 0
        assert m.f == 0

    def test_skew_y(self):
        """Test Matrix.skew_y() creates correct Y-axis skew matrix."""
        m = Matrix.skew_y(45)
        tan_45 = math.tan(math.radians(45))
        assert m.a == 1
        assert abs(m.b - tan_45) < 1e-10
        assert m.c == 0
        assert m.d == 1
        assert m.e == 0
        assert m.f == 0


class TestMatrixOperations:
    """Test Matrix mathematical operations."""

    def test_multiply_identity(self):
        """Test multiplying by identity matrix."""
        m1 = Matrix(2, 3, 4, 5, 6, 7)
        identity = Matrix.identity()

        result = m1.multiply(identity)
        assert result.a == m1.a
        assert result.b == m1.b
        assert result.c == m1.c
        assert result.d == m1.d
        assert result.e == m1.e
        assert result.f == m1.f

    def test_multiply_translation(self):
        """Test multiplying with translation matrix."""
        translate = Matrix.translate(10, 20)
        scale = Matrix.scale(2, 3)

        # Translate then scale
        result = translate.multiply(scale)
        # Translation should be preserved, scaling applied
        assert result.a == 2
        assert result.d == 3
        assert result.e == 10
        assert result.f == 20

    def test_inverse_identity(self):
        """Test inverse of identity matrix."""
        identity = Matrix.identity()
        inverse = identity.inverse()
        assert inverse is not None
        assert inverse.is_identity()

    def test_inverse_translation(self):
        """Test inverse of translation matrix."""
        translate = Matrix.translate(10, 20)
        inverse = translate.inverse()
        assert inverse is not None
        assert abs(inverse.e - (-10)) < 1e-10
        assert abs(inverse.f - (-20)) < 1e-10

    def test_inverse_non_invertible(self):
        """Test inverse of non-invertible matrix."""
        # Create matrix with zero determinant
        m = Matrix(1, 2, 2, 4, 0, 0)  # a*d - b*c = 1*4 - 2*2 = 0
        inverse = m.inverse()
        assert inverse is None

    def test_transform_point(self):
        """Test point transformation."""
        # Test identity transformation
        identity = Matrix.identity()
        x, y = identity.transform_point(5, 10)
        assert x == 5
        assert y == 10

        # Test translation
        translate = Matrix.translate(3, 4)
        x, y = translate.transform_point(5, 10)
        assert x == 8
        assert y == 14

        # Test scaling
        scale = Matrix.scale(2, 3)
        x, y = scale.transform_point(5, 10)
        assert x == 10
        assert y == 30

    def test_transform_points(self):
        """Test multiple point transformation."""
        translate = Matrix.translate(1, 2)
        points = [(0, 0), (1, 1), (2, 3)]
        result = translate.transform_points(points)

        expected = [(1, 2), (2, 3), (3, 5)]
        assert result == expected


class TestMatrixAnalysis:
    """Test Matrix analysis methods."""

    def test_is_identity(self):
        """Test identity matrix detection."""
        identity = Matrix.identity()
        assert identity.is_identity()

        non_identity = Matrix.translate(1, 0)
        assert not non_identity.is_identity()

        # Test with tolerance
        almost_identity = Matrix(1.0001, 0, 0, 1, 0, 0)
        assert not almost_identity.is_identity(1e-6)
        assert almost_identity.is_identity(1e-3)

    def test_is_translation_only(self):
        """Test pure translation detection."""
        translate = Matrix.translate(5, 10)
        assert translate.is_translation_only()

        scale = Matrix.scale(2)
        assert not scale.is_translation_only()

        identity = Matrix.identity()
        assert identity.is_translation_only()

    def test_has_rotation(self):
        """Test rotation detection."""
        rotate = Matrix.rotate(45)
        assert rotate.has_rotation()

        translate = Matrix.translate(5, 10)
        assert not translate.has_rotation()

        skew = Matrix.skew_x(30)
        assert skew.has_rotation()

    def test_has_scale(self):
        """Test scaling detection."""
        scale = Matrix.scale(2)
        assert scale.has_scale()

        translate = Matrix.translate(5, 10)
        assert not translate.has_scale()

        identity = Matrix.identity()
        assert not identity.has_scale()


class TestMatrixDecomposition:
    """Test Matrix decomposition and component extraction."""

    def test_get_translation(self):
        """Test translation component extraction."""
        m = Matrix(2, 0, 0, 3, 10, 20)
        tx, ty = m.get_translation()
        assert tx == 10
        assert ty == 20

    def test_get_scale(self):
        """Test scale component extraction."""
        scale = Matrix.scale(2, 3)
        sx, sy = scale.get_scale()
        assert abs(sx - 2) < 1e-10
        assert abs(sy - 3) < 1e-10

    def test_get_rotation(self):
        """Test rotation component extraction."""
        rotate = Matrix.rotate(45)
        angle = rotate.get_rotation()
        assert abs(angle - 45) < 1e-10

    def test_decompose_simple(self):
        """Test matrix decomposition for simple transformations."""
        # Test pure translation
        translate = Matrix.translate(10, 20)
        components = translate.decompose()
        assert abs(components['translateX'] - 10) < 1e-10
        assert abs(components['translateY'] - 20) < 1e-10
        assert abs(components['scaleX'] - 1) < 1e-10
        assert abs(components['scaleY'] - 1) < 1e-10

        # Test pure scaling
        scale = Matrix.scale(2, 3)
        components = scale.decompose()
        assert abs(components['scaleX'] - 2) < 1e-10
        assert abs(components['scaleY'] - 3) < 1e-10
        assert abs(components['translateX']) < 1e-10
        assert abs(components['translateY']) < 1e-10


class TestMatrixStringRepresentation:
    """Test Matrix string representations."""

    def test_str(self):
        """Test __str__ method."""
        m = Matrix(1, 2, 3, 4, 5, 6)
        s = str(m)
        assert "matrix(1, 2, 3, 4, 5, 6)" == s

    def test_repr(self):
        """Test __repr__ method."""
        m = Matrix(1, 2, 3, 4, 5, 6)
        r = repr(m)
        assert "matrix(1, 2, 3, 4, 5, 6)" == r


class TestMatrixEquality:
    """Test Matrix equality comparison."""

    def test_equality_same(self):
        """Test equality for identical matrices."""
        m1 = Matrix(1, 2, 3, 4, 5, 6)
        m2 = Matrix(1, 2, 3, 4, 5, 6)
        assert m1 == m2

    def test_equality_different(self):
        """Test inequality for different matrices."""
        m1 = Matrix(1, 2, 3, 4, 5, 6)
        m2 = Matrix(1, 2, 3, 4, 5, 7)  # Different f value
        assert m1 != m2

    def test_equality_non_matrix(self):
        """Test equality with non-Matrix objects."""
        m = Matrix(1, 2, 3, 4, 5, 6)
        assert m != "not a matrix"
        assert m != 42
        assert m != None


class TestMatrixEdgeCases:
    """Test Matrix edge cases and error conditions."""

    def test_zero_scale(self):
        """Test matrix with zero scaling."""
        zero_scale = Matrix.scale(0, 1)
        assert zero_scale.a == 0
        assert zero_scale.d == 1

        # Should be non-invertible
        inverse = zero_scale.inverse()
        assert inverse is None

    def test_negative_scale(self):
        """Test matrix with negative scaling."""
        neg_scale = Matrix.scale(-1, 2)
        assert neg_scale.a == -1
        assert neg_scale.d == 2

        # Should still be invertible
        inverse = neg_scale.inverse()
        assert inverse is not None

    def test_large_values(self):
        """Test matrix with large values."""
        large = Matrix(1e6, 0, 0, 1e6, 1e6, 1e6)
        point = large.transform_point(1, 1)
        assert point[0] == 2e6  # 1e6 * 1 + 1e6
        assert point[1] == 2e6  # 1e6 * 1 + 1e6

    def test_very_small_values(self):
        """Test matrix with very small values."""
        small = Matrix(1e-10, 0, 0, 1e-10, 0, 0)
        point = small.transform_point(1, 1)
        assert abs(point[0] - 1e-10) < 1e-15
        assert abs(point[1] - 1e-10) < 1e-15


class TestMatrixMathematicalProperties:
    """Test mathematical properties of Matrix operations."""

    def test_multiplication_associativity(self):
        """Test that matrix multiplication is associative: (A*B)*C = A*(B*C)."""
        a = Matrix.translate(1, 2)
        b = Matrix.scale(2, 3)
        c = Matrix.rotate(45)

        # (A*B)*C
        ab = a.multiply(b)
        abc1 = ab.multiply(c)

        # A*(B*C)
        bc = b.multiply(c)
        abc2 = a.multiply(bc)

        # Results should be equal (within numerical tolerance)
        tolerance = 1e-10
        assert abs(abc1.a - abc2.a) < tolerance
        assert abs(abc1.b - abc2.b) < tolerance
        assert abs(abc1.c - abc2.c) < tolerance
        assert abs(abc1.d - abc2.d) < tolerance
        assert abs(abc1.e - abc2.e) < tolerance
        assert abs(abc1.f - abc2.f) < tolerance

    def test_identity_multiplication(self):
        """Test that multiplying by identity matrix preserves original matrix."""
        original = Matrix(2, 3, 4, 5, 6, 7)
        identity = Matrix.identity()

        # Test both orders
        result1 = original.multiply(identity)
        result2 = identity.multiply(original)

        assert original == result1
        assert original == result2

    def test_inverse_multiplication(self):
        """Test that matrix multiplied by its inverse gives identity."""
        # Use a simple invertible matrix
        m = Matrix.translate(5, 10)
        inverse = m.inverse()
        assert inverse is not None

        # m * m^(-1) should give identity
        result = m.multiply(inverse)
        assert result.is_identity(tolerance=1e-10)

        # m^(-1) * m should also give identity
        result2 = inverse.multiply(m)
        assert result2.is_identity(tolerance=1e-10)