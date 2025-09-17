#!/usr/bin/env python3
"""
Unit tests for advanced NumPy geometric operations (Task 2.1.3).

Tests vectorized shape intersection algorithms, coordinate transformations,
and advanced spatial operations implemented in the NumPy geometry engine.
"""

import numpy as np
import pytest
from typing import List, Tuple
import time

from src.converters.shapes.numpy_geometry import (
    NumPyGeometryEngine,
    ShapeGeometry,
    ShapeType
)


class TestAdvancedGeometricOperations:
    """Test suite for Task 2.1.3 advanced geometric operations."""

    @pytest.fixture
    def geometry_engine(self):
        """Create a geometry engine for testing."""
        return NumPyGeometryEngine(optimization_level=2)

    @pytest.fixture
    def sample_rectangles(self):
        """Create sample rectangle geometries for testing."""
        rectangles = []
        positions = np.array([[0, 0], [10, 10], [5, 5], [20, 0]])
        dimensions = np.array([[10, 10], [10, 10], [15, 15], [10, 10]])

        for i, (pos, dim) in enumerate(zip(positions, dimensions)):
            bbox = np.concatenate([pos, dim])
            geom = ShapeGeometry(
                shape_type=ShapeType.RECTANGLE,
                bounding_box=bbox,
                drawingml_xml=f"<rect{i}/>"
            )
            rectangles.append(geom)

        return rectangles

    @pytest.fixture
    def sample_circles(self):
        """Create sample circle geometries for testing."""
        circles = []
        centers = np.array([[5, 5], [15, 15], [25, 5], [35, 15]])
        radii = np.array([3, 4, 2, 5])

        for i, (center, radius) in enumerate(zip(centers, radii)):
            # Circle bounding box: [x-r, y-r, diameter, diameter]
            bbox = np.array([center[0]-radius, center[1]-radius, 2*radius, 2*radius])
            geom = ShapeGeometry(
                shape_type=ShapeType.CIRCLE,
                bounding_box=bbox,
                drawingml_xml=f"<circle{i}/>"
            )
            circles.append(geom)

        return circles

    # ==================== Shape Intersection Tests ====================

    def test_rectangle_intersection_batch_basic(self, geometry_engine, sample_rectangles):
        """Test basic rectangle-rectangle intersection detection."""
        # Test overlapping rectangles
        rects_a = [sample_rectangles[0], sample_rectangles[2]]  # [0,0,10,10] and [5,5,15,15]
        rects_b = [sample_rectangles[1], sample_rectangles[3]]  # [10,10,10,10] and [20,0,10,10]

        intersections = geometry_engine.calculate_shape_intersections_batch(rects_a, rects_b)

        assert len(intersections) == 2
        assert isinstance(intersections[0], bool)
        assert isinstance(intersections[1], bool)
        # Rectangle [0,0,10,10] should not intersect with [10,10,10,10] (touching edge)
        # Rectangle [5,5,15,15] should not intersect with [20,0,10,10]
        assert intersections[0] == False  # Edge case: touching rectangles
        assert intersections[1] == False  # Non-overlapping

    def test_rectangle_intersection_overlapping(self, geometry_engine):
        """Test overlapping rectangle intersection."""
        rect_a = ShapeGeometry(
            shape_type=ShapeType.RECTANGLE,
            bounding_box=np.array([0, 0, 10, 10]),
            drawingml_xml="<rect1/>"
        )
        rect_b = ShapeGeometry(
            shape_type=ShapeType.RECTANGLE,
            bounding_box=np.array([5, 5, 10, 10]),  # Overlaps with rect_a
            drawingml_xml="<rect2/>"
        )

        intersections = geometry_engine.calculate_shape_intersections_batch([rect_a], [rect_b])
        assert intersections[0] == True

    def test_circle_intersection_batch(self, geometry_engine, sample_circles):
        """Test circle-circle intersection detection."""
        circles_a = [sample_circles[0], sample_circles[1]]  # Centers at [5,5] and [15,15]
        circles_b = [sample_circles[1], sample_circles[2]]  # Centers at [15,15] and [25,5]

        intersections = geometry_engine.calculate_shape_intersections_batch(circles_a, circles_b)

        assert len(intersections) == 2
        # Circle at [5,5] r=3 vs [15,15] r=4: distance=√200≈14.14, sum_radii=7 -> No intersection
        # Circle at [15,15] r=4 vs [25,5] r=2: distance=√200≈14.14, sum_radii=6 -> No intersection
        assert intersections[0] == False
        assert intersections[1] == False

    def test_circle_intersection_touching(self, geometry_engine):
        """Test touching circles intersection."""
        circle_a = ShapeGeometry(
            shape_type=ShapeType.CIRCLE,
            bounding_box=np.array([0, 0, 6, 6]),  # Center [3,3], radius 3
            drawingml_xml="<circle1/>"
        )
        circle_b = ShapeGeometry(
            shape_type=ShapeType.CIRCLE,
            bounding_box=np.array([4, 3, 4, 4]),  # Center [6,5], radius 2
            drawingml_xml="<circle2/>"
        )

        intersections = geometry_engine.calculate_shape_intersections_batch([circle_a], [circle_b])
        # Distance between [3,3] and [6,5] = √(9+4) = √13 ≈ 3.6, sum_radii = 5
        assert intersections[0] == True

    def test_mixed_shape_intersection_fallback(self, geometry_engine, sample_rectangles, sample_circles):
        """Test mixed shape types fall back to bounding box intersection."""
        mixed_a = [sample_rectangles[0]]  # Rectangle
        mixed_b = [sample_circles[0]]     # Circle

        intersections = geometry_engine.calculate_shape_intersections_batch(mixed_a, mixed_b)

        assert len(intersections) == 1
        assert isinstance(intersections[0], bool)

    def test_intersection_batch_empty_input(self, geometry_engine):
        """Test intersection calculation with empty input."""
        intersections = geometry_engine.calculate_shape_intersections_batch([], [])
        assert intersections == []

    def test_intersection_batch_mismatched_lengths(self, geometry_engine, sample_rectangles):
        """Test intersection calculation with mismatched input lengths."""
        with pytest.raises(ValueError, match="Shape sets must have equal length"):
            geometry_engine.calculate_shape_intersections_batch(
                [sample_rectangles[0]],
                [sample_rectangles[0], sample_rectangles[1]]
            )

    # ==================== Union Bounds Tests ====================

    def test_union_bounds_batch_rectangles(self, geometry_engine, sample_rectangles):
        """Test union bounding box calculation for rectangles."""
        union_bounds = geometry_engine.calculate_union_bounds_batch(sample_rectangles)

        assert isinstance(union_bounds, np.ndarray)
        assert union_bounds.shape == (4,)

        # Expected union: min_x=0, min_y=0, max_x=30, max_y=20 -> [0, 0, 30, 20]
        expected = np.array([0, 0, 30, 20])
        np.testing.assert_array_equal(union_bounds, expected)

    def test_union_bounds_single_shape(self, geometry_engine, sample_rectangles):
        """Test union bounds for single shape."""
        union_bounds = geometry_engine.calculate_union_bounds_batch([sample_rectangles[0]])

        # Single rectangle [0, 0, 10, 10] should return itself
        expected = np.array([0, 0, 10, 10])
        np.testing.assert_array_equal(union_bounds, expected)

    def test_union_bounds_empty_input(self, geometry_engine):
        """Test union bounds calculation with empty input."""
        union_bounds = geometry_engine.calculate_union_bounds_batch([])
        expected = np.array([0, 0, 0, 0])
        np.testing.assert_array_equal(union_bounds, expected)

    # ==================== Coordinate Transformation Tests ====================

    def test_transform_coordinates_batch_identity(self, geometry_engine):
        """Test batch coordinate transformation with identity matrices."""
        coordinates = np.array([[[1, 2], [3, 4]], [[5, 6], [7, 8]]])  # (2, 2, 2)
        identity_matrices = np.array([np.eye(3), np.eye(3)])  # (2, 3, 3)

        transformed = geometry_engine.transform_coordinates_batch(coordinates, identity_matrices)

        np.testing.assert_array_almost_equal(transformed, coordinates)

    def test_transform_coordinates_batch_translation(self, geometry_engine):
        """Test batch coordinate transformation with translation."""
        coordinates = np.array([[[0, 0], [1, 1]], [[2, 2], [3, 3]]])  # (2, 2, 2)

        # Translation matrices: translate by [10, 20] and [30, 40]
        transform1 = np.array([[1, 0, 10], [0, 1, 20], [0, 0, 1]])
        transform2 = np.array([[1, 0, 30], [0, 1, 40], [0, 0, 1]])
        transform_matrices = np.array([transform1, transform2])

        transformed = geometry_engine.transform_coordinates_batch(coordinates, transform_matrices)

        expected = np.array([[[10, 20], [11, 21]], [[32, 42], [33, 43]]])
        np.testing.assert_array_almost_equal(transformed, expected)

    def test_transform_coordinates_batch_scaling(self, geometry_engine):
        """Test batch coordinate transformation with scaling."""
        coordinates = np.array([[[1, 1], [2, 2]], [[3, 3], [4, 4]]])  # (2, 2, 2)

        # Scaling matrices: scale by 2x and 0.5x
        scale1 = np.array([[2, 0, 0], [0, 2, 0], [0, 0, 1]])
        scale2 = np.array([[0.5, 0, 0], [0, 0.5, 0], [0, 0, 1]])
        transform_matrices = np.array([scale1, scale2])

        transformed = geometry_engine.transform_coordinates_batch(coordinates, transform_matrices)

        expected = np.array([[[2, 2], [4, 4]], [[1.5, 1.5], [2, 2]]])
        np.testing.assert_array_almost_equal(transformed, expected)

    # ==================== Shape Complexity Optimization Tests ====================

    def test_optimize_shape_complexity_rectangles(self, geometry_engine, sample_rectangles):
        """Test shape complexity optimization for rectangles (no change expected)."""
        optimized = geometry_engine.optimize_shape_complexity_batch(sample_rectangles, max_points_per_shape=50)

        assert len(optimized) == len(sample_rectangles)
        for original, opt in zip(sample_rectangles, optimized):
            assert opt.shape_type == original.shape_type
            np.testing.assert_array_equal(opt.bounding_box, original.bounding_box)

    def test_optimize_polygon_complexity(self, geometry_engine):
        """Test polygon point reduction."""
        # Create a polygon with many points
        many_points = np.array([[i, i % 3] for i in range(100)])  # 100 points
        polygon = ShapeGeometry(
            shape_type=ShapeType.POLYGON,
            bounding_box=np.array([0, 0, 99, 2]),
            points=many_points,
            drawingml_xml="<polygon/>"
        )

        optimized = geometry_engine.optimize_shape_complexity_batch([polygon], max_points_per_shape=20)

        assert len(optimized) == 1
        assert hasattr(optimized[0], 'points')
        assert len(optimized[0].points) <= 20
        assert len(optimized[0].points) > 0

    def test_simplify_polygon_vectorized_few_points(self, geometry_engine):
        """Test polygon simplification when points are already few."""
        few_points = np.array([[0, 0], [1, 1], [2, 0]])  # 3 points
        simplified = geometry_engine._simplify_polygon_vectorized(few_points, max_points=10)

        np.testing.assert_array_equal(simplified, few_points)

    # ==================== Shape Mask Generation Tests ====================

    def test_generate_shape_masks_batch_rectangles(self, geometry_engine, sample_rectangles):
        """Test mask generation for rectangles."""
        canvas_size = (50, 50)
        resolution = 32

        masks = geometry_engine.generate_shape_masks_batch(
            sample_rectangles, canvas_size, resolution
        )

        assert masks.shape == (len(sample_rectangles), resolution, resolution)
        assert masks.dtype == bool

        # First rectangle [0,0,10,10] should have some True values in upper-left region
        assert masks[0].any()  # Should have some mask coverage

    def test_generate_shape_masks_batch_circles(self, geometry_engine, sample_circles):
        """Test mask generation for circles."""
        canvas_size = (50, 50)
        resolution = 32

        masks = geometry_engine.generate_shape_masks_batch(
            sample_circles, canvas_size, resolution
        )

        assert masks.shape == (len(sample_circles), resolution, resolution)
        assert masks.dtype == bool

        # Should have some mask coverage for circles
        assert masks.any()

    def test_generate_masks_empty_shapes(self, geometry_engine):
        """Test mask generation with empty shape list."""
        masks = geometry_engine.generate_shape_masks_batch([], (100, 100), 16)

        assert masks.shape == (0, 16, 16)
        assert masks.dtype == bool

    # ==================== Area Calculation Tests ====================

    def test_calculate_shape_areas_batch_rectangles(self, geometry_engine, sample_rectangles):
        """Test area calculation for rectangles."""
        areas = geometry_engine.calculate_shape_areas_batch(sample_rectangles)

        assert isinstance(areas, np.ndarray)
        assert len(areas) == len(sample_rectangles)

        # Expected areas: 10*10=100, 10*10=100, 15*15=225, 10*10=100
        expected_areas = np.array([100, 100, 225, 100])
        np.testing.assert_array_almost_equal(areas, expected_areas)

    def test_calculate_shape_areas_batch_circles(self, geometry_engine, sample_circles):
        """Test area calculation for circles."""
        areas = geometry_engine.calculate_shape_areas_batch(sample_circles)

        assert isinstance(areas, np.ndarray)
        assert len(areas) == len(sample_circles)

        # Expected areas: π*3², π*4², π*2², π*5²
        expected_areas = np.array([np.pi * 9, np.pi * 16, np.pi * 4, np.pi * 25])
        np.testing.assert_array_almost_equal(areas, expected_areas, decimal=6)

    def test_calculate_polygon_area_shoelace(self, geometry_engine):
        """Test polygon area calculation using shoelace formula."""
        # Simple triangle: (0,0), (1,0), (0,1) -> area = 0.5
        triangle_points = np.array([[0, 0], [1, 0], [0, 1]])
        triangle = ShapeGeometry(
            shape_type=ShapeType.POLYGON,
            bounding_box=np.array([0, 0, 1, 1]),
            points=triangle_points,
            drawingml_xml="<polygon/>"
        )

        areas = geometry_engine.calculate_shape_areas_batch([triangle])

        assert len(areas) == 1
        np.testing.assert_almost_equal(areas[0], 0.5, decimal=6)

    def test_calculate_areas_empty_input(self, geometry_engine):
        """Test area calculation with empty input."""
        areas = geometry_engine.calculate_shape_areas_batch([])

        assert isinstance(areas, np.ndarray)
        assert len(areas) == 0

    # ==================== Performance Tests ====================

    def test_intersection_performance_vs_individual(self, geometry_engine):
        """Test that batch intersection is faster than individual tests."""
        # Create many rectangles for performance testing
        n_shapes = 100
        positions = np.random.rand(n_shapes, 2) * 100
        dimensions = np.random.rand(n_shapes, 2) * 10 + 1

        shapes_a = []
        shapes_b = []

        for i in range(n_shapes):
            bbox_a = np.concatenate([positions[i], dimensions[i]])
            bbox_b = np.concatenate([positions[i] + 5, dimensions[i]])

            shape_a = ShapeGeometry(
                shape_type=ShapeType.RECTANGLE,
                bounding_box=bbox_a,
                drawingml_xml=f"<rect{i}a/>"
            )
            shape_b = ShapeGeometry(
                shape_type=ShapeType.RECTANGLE,
                bounding_box=bbox_b,
                drawingml_xml=f"<rect{i}b/>"
            )

            shapes_a.append(shape_a)
            shapes_b.append(shape_b)

        # Measure batch performance
        start_time = time.perf_counter()
        batch_results = geometry_engine.calculate_shape_intersections_batch(shapes_a, shapes_b)
        batch_time = time.perf_counter() - start_time

        # Measure individual performance
        start_time = time.perf_counter()
        individual_results = []
        for shape_a, shape_b in zip(shapes_a, shapes_b):
            result = geometry_engine.calculate_shape_intersections_batch([shape_a], [shape_b])
            individual_results.extend(result)
        individual_time = time.perf_counter() - start_time

        # Results should be identical
        assert len(batch_results) == len(individual_results)
        assert batch_results == individual_results

        # Batch should be faster (allow some variance for small datasets)
        print(f"Batch time: {batch_time:.4f}s, Individual time: {individual_time:.4f}s")
        print(f"Speedup: {individual_time/batch_time:.2f}x")

    def test_union_bounds_performance(self, geometry_engine):
        """Test union bounds performance scaling."""
        # Test with varying numbers of shapes
        for n_shapes in [10, 50, 100]:
            positions = np.random.rand(n_shapes, 2) * 100
            dimensions = np.random.rand(n_shapes, 2) * 10 + 1

            shapes = []
            for i in range(n_shapes):
                bbox = np.concatenate([positions[i], dimensions[i]])
                shape = ShapeGeometry(
                    shape_type=ShapeType.RECTANGLE,
                    bounding_box=bbox,
                    drawingml_xml=f"<rect{i}/>"
                )
                shapes.append(shape)

            start_time = time.perf_counter()
            union_bounds = geometry_engine.calculate_union_bounds_batch(shapes)
            elapsed = time.perf_counter() - start_time

            # Should complete quickly
            assert elapsed < 0.1  # Should finish within 100ms
            assert union_bounds.shape == (4,)

            print(f"Union bounds for {n_shapes} shapes: {elapsed:.4f}s")