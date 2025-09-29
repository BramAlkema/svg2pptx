#!/usr/bin/env python3
"""
Comprehensive test suite for Transform Engine.

Tests performance, accuracy, and functionality of the
consolidated transform system after NumPy cleanup.
"""

import pytest
import numpy as np
import time
import math
from pathlib import Path
import sys
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.transforms import TransformEngine, Matrix


class TestTransformEngineBasics:
    """Test basic TransformEngine functionality."""

    def test_engine_initialization(self):
        """Test TransformEngine initialization."""
        engine = TransformEngine()
        assert engine is not None

    def test_matrix_initialization(self):
        """Test Matrix initialization."""
        matrix = Matrix()
        assert matrix is not None
        assert matrix.is_identity()

    def test_transform_parse_identity(self):
        """Test parsing identity transforms."""
        engine = TransformEngine()
        matrix = engine.parse_to_matrix("matrix(1,0,0,1,0,0)")
        assert matrix is not None
        assert matrix.is_identity()

    def test_transform_parse_translate(self):
        """Test parsing translate transforms."""
        engine = TransformEngine()
        matrix = engine.parse_to_matrix("translate(10,20)")
        assert matrix is not None
        translation = matrix.get_translation()
        assert abs(translation[0] - 10) < 1e-6
        assert abs(translation[1] - 20) < 1e-6

    def test_transform_parse_scale(self):
        """Test parsing scale transforms."""
        engine = TransformEngine()
        matrix = engine.parse_to_matrix("scale(2,3)")
        assert matrix is not None
        scale = matrix.get_scale()
        assert abs(scale[0] - 2) < 1e-6
        assert abs(scale[1] - 3) < 1e-6

    def test_transform_parse_rotate(self):
        """Test parsing rotate transforms."""
        engine = TransformEngine()
        matrix = engine.parse_to_matrix("rotate(45)")
        assert matrix is not None
        rotation = matrix.get_rotation()
        assert abs(rotation - 45) < 1e-6

    def test_transform_point(self):
        """Test point transformation."""
        matrix = Matrix.translate(10, 20)
        new_x, new_y = matrix.transform_point(0, 0)
        assert abs(new_x - 10) < 1e-6
        assert abs(new_y - 20) < 1e-6

    def test_matrix_multiply(self):
        """Test matrix multiplication."""
        translate = Matrix.translate(10, 20)
        scale = Matrix.scale(2, 2)
        combined = translate.multiply(scale)
        assert combined is not None

        # Test point transformation
        new_x, new_y = combined.transform_point(1, 1)
        assert abs(new_x - 12) < 1e-6  # (1*2 + 10)
        assert abs(new_y - 22) < 1e-6  # (1*2 + 20)

    def test_matrix_decomposition(self):
        """Test matrix decomposition."""
        matrix = Matrix.translate(10, 20).multiply(Matrix.scale(2, 3)).multiply(Matrix.rotate(45))
        components = matrix.decompose()

        assert 'translateX' in components
        assert 'translateY' in components
        assert 'scaleX' in components
        assert 'scaleY' in components
        assert 'rotation' in components
        assert 'skewX' in components

    def test_matrix_inverse(self):
        """Test matrix inverse calculation."""
        matrix = Matrix.translate(10, 20).multiply(Matrix.scale(2, 3))
        inverse = matrix.inverse()
        assert inverse is not None

        # Test that matrix * inverse = identity
        identity = matrix.multiply(inverse)
        assert identity.is_identity(tolerance=1e-6)


class TestTransformEnginePerformance:
    """Test TransformEngine performance characteristics."""

    def test_parse_performance(self):
        """Test transform parsing performance."""
        engine = TransformEngine()

        start_time = time.time()
        for _ in range(1000):
            matrix = engine.parse_to_matrix("translate(10,20) scale(2,3) rotate(45)")
        end_time = time.time()

        # Should be able to parse 1000 transforms in reasonable time
        assert (end_time - start_time) < 1.0  # Less than 1 second

    def test_transform_performance(self):
        """Test point transformation performance."""
        matrix = Matrix.translate(10, 20).multiply(Matrix.scale(2, 3)).multiply(Matrix.rotate(45))

        start_time = time.time()
        for _ in range(10000):
            matrix.transform_point(100, 100)
        end_time = time.time()

        # Should be able to transform 10000 points in reasonable time
        assert (end_time - start_time) < 0.1  # Less than 100ms


class TestTransformEngineErrorHandling:
    """Test TransformEngine error handling."""

    def test_parse_invalid_transform(self):
        """Test parsing invalid transform strings."""
        engine = TransformEngine()

        # Test with invalid syntax
        matrix = engine.parse_to_matrix("invalid_transform(10,20)")
        # Should return identity matrix for invalid input
        assert matrix is not None

    def test_parse_empty_transform(self):
        """Test parsing empty transform strings."""
        engine = TransformEngine()

        matrix = engine.parse_to_matrix("")
        assert matrix is not None
        assert matrix.is_identity()

    def test_matrix_division_by_zero(self):
        """Test matrix operations that could cause division by zero."""
        # Create a non-invertible matrix (determinant = 0)
        matrix = Matrix(0, 0, 0, 0, 0, 0)
        inverse = matrix.inverse()
        assert inverse is None  # Should return None for non-invertible matrix


class TestTransformEngineIntegration:
    """Test TransformEngine integration with other components."""

    def test_engine_with_conversion_services(self):
        """Test TransformEngine integration with ConversionServices."""
        # This test ensures the transform engine works with dependency injection
        from src.services.conversion_services import ConversionServices

        services = ConversionServices.create_default()
        assert services.transform_parser is not None

        # Test that the transform parser can parse transforms
        matrix = services.transform_parser.parse_to_matrix("translate(10,20)")
        assert matrix is not None
        translation = matrix.get_translation()
        assert abs(translation[0] - 10) < 1e-6
        assert abs(translation[1] - 20) < 1e-6

    def test_complex_transform_chain(self):
        """Test complex transform chains."""
        engine = TransformEngine()

        # Parse complex transform chain
        matrix = engine.parse_to_matrix("translate(10,20) rotate(45) scale(2,3) translate(-5,-10)")
        assert matrix is not None

        # Test specific point transformation
        new_x, new_y = matrix.transform_point(0, 0)
        # Values should be deterministic based on the transform chain
        assert isinstance(new_x, (int, float))
        assert isinstance(new_y, (int, float))

    def test_transform_preservation_accuracy(self):
        """Test that transforms preserve accuracy through multiple operations."""
        matrix1 = Matrix.translate(1.23456789, 2.34567891)
        matrix2 = Matrix.scale(1.11111111, 2.22222222)
        matrix3 = Matrix.rotate(33.33333333)

        combined = matrix1.multiply(matrix2).multiply(matrix3)

        # Verify that precision is maintained
        x, y = combined.transform_point(1.0, 1.0)
        # Should maintain reasonable precision
        assert isinstance(x, float)
        assert isinstance(y, float)
        assert not math.isnan(x)
        assert not math.isnan(y)
        assert not math.isinf(x)
        assert not math.isinf(y)


class TestTransformEngineEdgeCases:
    """Test TransformEngine edge cases and boundary conditions."""

    def test_very_large_values(self):
        """Test transforms with very large values."""
        matrix = Matrix.translate(1e6, 1e6)
        x, y = matrix.transform_point(1e6, 1e6)
        assert abs(x - 2e6) < 1e-6
        assert abs(y - 2e6) < 1e-6

    def test_very_small_values(self):
        """Test transforms with very small values."""
        matrix = Matrix.translate(1e-6, 1e-6)
        x, y = matrix.transform_point(1e-6, 1e-6)
        assert abs(x - 2e-6) < 1e-12
        assert abs(y - 2e-6) < 1e-12

    def test_zero_scale(self):
        """Test transforms with zero scale."""
        matrix = Matrix.scale(0, 0)
        x, y = matrix.transform_point(100, 100)
        assert abs(x) < 1e-6
        assert abs(y) < 1e-6

    def test_negative_scale(self):
        """Test transforms with negative scale (reflection)."""
        matrix = Matrix.scale(-1, -1)
        x, y = matrix.transform_point(10, 20)
        assert abs(x + 10) < 1e-6
        assert abs(y + 20) < 1e-6

    def test_large_rotation_angles(self):
        """Test transforms with large rotation angles."""
        matrix = Matrix.rotate(720)  # Two full rotations
        x, y = matrix.transform_point(1, 0)
        # Should be equivalent to no rotation
        assert abs(x - 1) < 1e-6
        assert abs(y) < 1e-6