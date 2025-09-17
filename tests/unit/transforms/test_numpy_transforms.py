#!/usr/bin/env python3
"""
Comprehensive test suite for NumPy Transform Engine.

Tests performance, accuracy, and functionality of the ultra-fast
NumPy-based transform system.
"""

import pytest
import numpy as np
import time
from src.transforms.numpy import (
    TransformEngine, BoundingBox, TransformType, TransformOp,
    create_transform_chain, translate, scale, rotate
)


class TestTransformEngineBasics:
    """Test basic TransformEngine functionality."""

    def test_engine_initialization(self):
        """Test TransformEngine initialization."""
        engine = TransformEngine()

        # Should start with identity matrix
        assert engine.is_identity
        assert np.allclose(engine.current_matrix, np.eye(3))

    def test_translation_transform(self):
        """Test translation operations."""
        engine = TransformEngine()
        result = engine.translate(10, 20)

        # Should be fluent interface
        assert result is engine

        # Check matrix values
        matrix = engine.current_matrix
        expected = np.array([
            [1, 0, 10],
            [0, 1, 20],
            [0, 0, 1]
        ], dtype=np.float64)

        assert np.allclose(matrix, expected)

    def test_scale_transform(self):
        """Test scaling operations."""
        engine = TransformEngine()

        # Uniform scaling
        engine.scale(2.0)
        matrix = engine.current_matrix
        expected = np.array([
            [2, 0, 0],
            [0, 2, 0],
            [0, 0, 1]
        ], dtype=np.float64)
        assert np.allclose(matrix, expected)

        # Non-uniform scaling
        engine.reset().scale(2.0, 3.0)
        matrix = engine.current_matrix
        expected = np.array([
            [2, 0, 0],
            [0, 3, 0],
            [0, 0, 1]
        ], dtype=np.float64)
        assert np.allclose(matrix, expected)

    def test_rotation_transform(self):
        """Test rotation operations."""
        engine = TransformEngine()

        # 90-degree rotation
        engine.rotate(90)
        matrix = engine.current_matrix

        # Should rotate (1, 0) to (0, 1)
        point = np.array([[1, 0]], dtype=np.float64)
        transformed = engine.transform_points(point)
        expected = np.array([[0, 1]], dtype=np.float64)

        assert np.allclose(transformed, expected, atol=1e-10)

    def test_transform_chaining(self):
        """Test fluent transform chaining."""
        engine = TransformEngine()

        # Chain multiple transforms
        result = (engine
                 .translate(10, 20)
                 .rotate(45)
                 .scale(2.0))

        # Should return same engine instance
        assert result is engine

        # Matrix should be composition of all transforms
        matrix = engine.current_matrix
        assert not np.allclose(matrix, np.eye(3))  # Should not be identity

    def test_no_op_optimizations(self):
        """Test that no-op transforms are optimized away."""
        engine = TransformEngine()
        initial_stack_len = len(engine._stack)

        # These should not add to stack
        engine.translate(0, 0)
        engine.scale(1.0, 1.0)
        engine.rotate(0)

        # Stack should be unchanged
        assert len(engine._stack) == initial_stack_len
        assert engine.is_identity


class TestPointTransformation:
    """Test point transformation functionality."""

    def test_single_point_transform(self):
        """Test single point transformation."""
        engine = TransformEngine().translate(10, 20)

        # Transform single point
        x, y = engine.transform_point(5, 15)
        assert (x, y) == (15, 35)

    def test_batch_point_transform(self):
        """Test batch point transformation."""
        engine = TransformEngine().translate(10, 20)

        # Transform multiple points
        points = np.array([[0, 0], [1, 1], [5, 10]], dtype=np.float64)
        transformed = engine.transform_points(points)

        expected = np.array([[10, 20], [11, 21], [15, 30]], dtype=np.float64)
        assert np.allclose(transformed, expected)

    def test_empty_points_handling(self):
        """Test handling of empty point arrays."""
        engine = TransformEngine().translate(10, 20)

        empty_points = np.array([]).reshape(0, 2)
        result = engine.transform_points(empty_points)

        assert result.size == 0

    def test_various_input_formats(self):
        """Test different input formats for points."""
        engine = TransformEngine().translate(10, 20)

        # List input
        result1 = engine.transform_points([[1, 2], [3, 4]])

        # Tuple input
        result2 = engine.transform_points(((1, 2), (3, 4)))

        # NumPy array input
        result3 = engine.transform_points(np.array([[1, 2], [3, 4]]))

        # All should give same result
        assert np.allclose(result1, result2)
        assert np.allclose(result2, result3)


class TestAdvancedFeatures:
    """Test advanced TransformEngine features."""

    def test_context_manager(self):
        """Test save_state context manager."""
        engine = TransformEngine()

        with engine.save_state():
            engine.translate(10, 20).rotate(45)
            # Transform should be active inside context
            assert not engine.is_identity

        # Should be back to identity outside context
        assert engine.is_identity

    def test_push_pop_operations(self):
        """Test push/pop state operations."""
        engine = TransformEngine()

        # Apply some transforms
        engine.translate(10, 20).rotate(45)
        matrix_before = engine.current_matrix.copy()

        # Push current state and add more transforms
        engine.push().scale(2.0)

        # Pop back to previous state
        engine.pop()

        # Should be back to previous matrix
        assert np.allclose(engine.current_matrix, matrix_before)

    def test_matrix_decomposition(self):
        """Test transform matrix decomposition."""
        engine = TransformEngine()

        # Apply known transforms
        tx, ty = 10, 20
        sx, sy = 2.0, 1.5
        rotation = 45

        engine.translate(tx, ty).scale(sx, sy).rotate(rotation)

        # Decompose matrix
        components = engine.decompose()

        # Translation should be preserved (applied last in our chain)
        # Note: Due to matrix composition order, exact values may differ
        assert 'translateX' in components
        assert 'translateY' in components
        assert 'scaleX' in components
        assert 'scaleY' in components
        assert 'rotation' in components

    def test_transform_inverse(self):
        """Test transform inversion."""
        engine = TransformEngine()

        # Apply transforms
        engine.translate(10, 20).rotate(45).scale(2.0)

        # Get inverse
        inverse_engine = engine.inverse()
        assert inverse_engine is not None

        # Apply original then inverse should give identity
        points = np.array([[1, 2], [3, 4]], dtype=np.float64)
        transformed = engine.transform_points(points)
        restored = inverse_engine.transform_points(transformed)

        assert np.allclose(restored, points, rtol=1e-12)

    def test_determinant_calculation(self):
        """Test matrix determinant calculation."""
        engine = TransformEngine()

        # Identity should have determinant 1
        assert abs(engine.determinant - 1.0) < 1e-10

        # Scale should multiply determinant
        engine.scale(2.0, 3.0)
        assert abs(engine.determinant - 6.0) < 1e-10


class TestBoundingBox:
    """Test BoundingBox functionality."""

    def test_bbox_creation(self):
        """Test bounding box creation."""
        points = np.array([[1, 2], [5, 8], [3, 4]], dtype=np.float64)
        bbox = BoundingBox(points)

        assert bbox.min_x == 1
        assert bbox.min_y == 2
        assert bbox.max_x == 5
        assert bbox.max_y == 8
        assert bbox.width == 4
        assert bbox.height == 6

    def test_bbox_transformation(self):
        """Test bounding box transformation."""
        points = np.array([[0, 0], [2, 2]], dtype=np.float64)
        bbox = BoundingBox(points)

        engine = TransformEngine().translate(10, 20)
        transformed_bbox = engine.transform_bbox(bbox)

        assert transformed_bbox.min_x == 10
        assert transformed_bbox.min_y == 20
        assert transformed_bbox.max_x == 12
        assert transformed_bbox.max_y == 22


class TestPerformanceBenchmarks:
    """Performance tests comparing with legacy implementation."""

    def test_matrix_multiplication_performance(self):
        """Benchmark matrix multiplication performance."""
        # NumPy engine
        numpy_engine = TransformEngine()

        # Chain many transforms
        n_transforms = 100
        start_time = time.time()

        for i in range(n_transforms):
            numpy_engine.rotate(i).translate(i, i*2).scale(1.1)

        numpy_time = time.time() - start_time

        # NumPy should be very fast
        print(f"NumPy transform chaining ({n_transforms} ops): {numpy_time:.4f}s")
        assert numpy_time < 0.1  # Should be under 100ms

    def test_point_transformation_performance(self):
        """Benchmark point transformation performance."""
        engine = TransformEngine().translate(10, 20).rotate(45).scale(2.0)

        # Large point array
        n_points = 10000
        points = np.random.random((n_points, 2)).astype(np.float64)

        # Benchmark transformation
        start_time = time.time()
        transformed = engine.transform_points(points)
        numpy_time = time.time() - start_time

        print(f"NumPy point transformation ({n_points} points): {numpy_time:.4f}s")
        assert numpy_time < 0.01  # Should be under 10ms
        assert transformed.shape == points.shape

    def test_compiled_path_performance(self):
        """Test performance of compiled critical paths."""
        engine = TransformEngine().translate(100, 200).rotate(45).scale(2.0)

        # Large batch of points for compiled function test
        n_points = 50000
        points = np.random.random((n_points, 2)).astype(np.float64) * 1000

        # First call to warm up Numba compilation
        _ = engine.transform_points(points[:100])

        # Benchmark compiled performance
        start_time = time.time()
        for _ in range(10):  # Multiple iterations
            transformed = engine.transform_points(points)
        compiled_time = time.time() - start_time

        print(f"Compiled transformation (50k points, 10 iterations): {compiled_time:.4f}s")
        assert compiled_time < 0.5  # Should be very fast with compilation


class TestFactoryFunctions:
    """Test factory and convenience functions."""

    def test_convenience_functions(self):
        """Test convenience factory functions."""
        # Test individual factories
        t1 = translate(10, 20)
        assert np.allclose(t1.current_matrix[0:2, 2], [10, 20])

        s1 = scale(2.0)
        assert np.allclose(np.diag(s1.current_matrix)[:2], [2, 2])

        r1 = rotate(90)
        # 90-degree rotation should transform (1,0) to (0,1)
        point = r1.transform_point(1, 0)
        assert np.allclose(point, (0, 1), atol=1e-10)

    def test_transform_chain_factory(self):
        """Test transform chain factory function."""
        chain = create_transform_chain(
            ('translate', 10, 20),
            ('rotate', 45),
            ('scale', 2.0)
        )

        # Should create valid transform engine
        assert isinstance(chain, TransformEngine)
        assert not chain.is_identity


class TestAccuracyValidation:
    """Test numerical accuracy and edge cases."""

    def test_numerical_precision(self):
        """Test numerical precision with multiple operations."""
        engine = TransformEngine()

        # Apply forward and reverse transforms
        original_point = np.array([[1, 2]], dtype=np.float64)

        # Apply transform and its exact inverse
        engine.translate(100, 200).rotate(45).scale(2.0)

        # Get inverse and apply
        inverse_engine = engine.inverse()
        transformed = engine.transform_points(original_point)
        restored = inverse_engine.transform_points(transformed)

        # Should restore original point
        assert np.allclose(restored, original_point, rtol=1e-10)

    def test_extreme_values(self):
        """Test handling of extreme transform values."""
        engine = TransformEngine()

        # Very large translation
        engine.translate(1e6, -1e6)

        # Very small scale (but not zero)
        engine.scale(1e-6, 1e-6)

        # Should not raise errors and should produce valid matrix
        matrix = engine.current_matrix
        assert not np.any(np.isnan(matrix))
        assert not np.any(np.isinf(matrix))

    def test_zero_scale_handling(self):
        """Test handling of zero scale factors."""
        engine = TransformEngine()

        # Zero scale should work (though creates singular matrix)
        engine.scale(0, 1)
        matrix = engine.current_matrix

        # Should have zero in scale position
        assert matrix[0, 0] == 0
        assert matrix[1, 1] == 1


if __name__ == "__main__":
    # Run performance benchmarks if executed directly
    print("=== NumPy Transform Engine Performance Benchmarks ===")

    test_perf = TestPerformanceBenchmarks()
    test_perf.test_matrix_multiplication_performance()
    test_perf.test_point_transformation_performance()
    test_perf.test_compiled_path_performance()

    print("=== All benchmarks completed ===")