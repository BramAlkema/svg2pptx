#!/usr/bin/env python3
"""
Simple unit tests for Task 2.1.3 advanced geometric operations.
Tests only the core NumPy geometry engine without full converter dependencies.
"""

import numpy as np
import pytest
import sys
import os
import time

# Add source to path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../'))

# Direct import to avoid converter dependency issues
from src.converters.shapes.numpy_geometry import (
    NumPyGeometryEngine,
    ShapeGeometry,
    ShapeType
)


class TestAdvancedGeometricOperationsCore:
    """Core tests for Task 2.1.3 advanced geometric operations."""

    @pytest.fixture
    def geometry_engine(self):
        """Create a geometry engine for testing."""
        return NumPyGeometryEngine(optimization_level=2)

    @pytest.fixture
    def sample_rectangles(self):
        """Create sample rectangle geometries for testing."""
        rectangles = []
        bboxes = [
            [0, 0, 10, 10],    # Rectangle 1: [0,0] to [10,10]
            [10, 10, 10, 10],  # Rectangle 2: [10,10] to [20,20]
            [5, 5, 15, 15],    # Rectangle 3: [5,5] to [20,20]
            [20, 0, 10, 10],   # Rectangle 4: [20,0] to [30,10]
        ]

        for i, bbox in enumerate(bboxes):
            geom = ShapeGeometry(
                shape_type=ShapeType.RECTANGLE,
                bounding_box=np.array(bbox, dtype=np.float64),
                drawingml_xml=f"<rect{i}/>"
            )
            rectangles.append(geom)

        return rectangles

    @pytest.fixture
    def sample_circles(self):
        """Create sample circle geometries for testing."""
        circles = []
        # Format: [cx, cy, r] -> [x-r, y-r, 2r, 2r]
        circle_specs = [
            [5, 5, 3],    # Center [5,5], radius 3
            [15, 15, 4],  # Center [15,15], radius 4
            [25, 5, 2],   # Center [25,5], radius 2
            [35, 15, 5],  # Center [35,15], radius 5
        ]

        for i, (cx, cy, r) in enumerate(circle_specs):
            bbox = [cx - r, cy - r, 2 * r, 2 * r]
            geom = ShapeGeometry(
                shape_type=ShapeType.CIRCLE,
                bounding_box=np.array(bbox, dtype=np.float64),
                drawingml_xml=f"<circle{i}/>"
            )
            circles.append(geom)

        return circles

    # ==================== Shape Intersection Tests ====================

    def test_rectangle_intersection_basic(self, geometry_engine, sample_rectangles):
        """Test basic rectangle intersection detection."""
        # Test non-overlapping rectangles
        rects_a = [sample_rectangles[0]]  # [0,0,10,10]
        rects_b = [sample_rectangles[3]]  # [20,0,10,10]

        intersections = geometry_engine.calculate_shape_intersections_batch(rects_a, rects_b)

        assert len(intersections) == 1
        assert isinstance(intersections[0], bool)
        assert intersections[0] == False  # Should not intersect

    def test_rectangle_intersection_overlapping(self, geometry_engine):
        """Test overlapping rectangle intersection."""
        rect_a = ShapeGeometry(
            shape_type=ShapeType.RECTANGLE,
            bounding_box=np.array([0, 0, 10, 10], dtype=np.float64),
            drawingml_xml="<rect1/>"
        )
        rect_b = ShapeGeometry(
            shape_type=ShapeType.RECTANGLE,
            bounding_box=np.array([5, 5, 10, 10], dtype=np.float64),  # Overlaps
            drawingml_xml="<rect2/>"
        )

        intersections = geometry_engine.calculate_shape_intersections_batch([rect_a], [rect_b])
        assert intersections[0] == True

    def test_circle_intersection(self, geometry_engine):
        """Test circle intersection detection."""
        # Two circles that intersect
        circle_a = ShapeGeometry(
            shape_type=ShapeType.CIRCLE,
            bounding_box=np.array([0, 0, 6, 6], dtype=np.float64),  # Center [3,3], radius 3
            drawingml_xml="<circle1/>"
        )
        circle_b = ShapeGeometry(
            shape_type=ShapeType.CIRCLE,
            bounding_box=np.array([2, 2, 6, 6], dtype=np.float64),  # Center [5,5], radius 3
            drawingml_xml="<circle2/>"
        )

        intersections = geometry_engine.calculate_shape_intersections_batch([circle_a], [circle_b])
        # Distance between [3,3] and [5,5] = √8 ≈ 2.83, sum_radii = 6
        assert intersections[0] == True

    def test_intersection_empty_input(self, geometry_engine):
        """Test intersection with empty input."""
        intersections = geometry_engine.calculate_shape_intersections_batch([], [])
        assert intersections == []

    def test_intersection_mismatched_lengths(self, geometry_engine, sample_rectangles):
        """Test intersection with mismatched input lengths."""
        with pytest.raises(ValueError, match="Shape sets must have equal length"):
            geometry_engine.calculate_shape_intersections_batch(
                [sample_rectangles[0]], [sample_rectangles[0], sample_rectangles[1]]
            )

    # ==================== Union Bounds Tests ====================

    def test_union_bounds_rectangles(self, geometry_engine, sample_rectangles):
        """Test union bounding box calculation."""
        union_bounds = geometry_engine.calculate_union_bounds_batch(sample_rectangles)

        assert isinstance(union_bounds, np.ndarray)
        assert union_bounds.shape == (4,)

        # Expected: min_x=0, min_y=0, max_x=30, max_y=20 -> [0, 0, 30, 20]
        expected = np.array([0, 0, 30, 20])
        np.testing.assert_array_equal(union_bounds, expected)

    def test_union_bounds_single_shape(self, geometry_engine, sample_rectangles):
        """Test union bounds for single shape."""
        union_bounds = geometry_engine.calculate_union_bounds_batch([sample_rectangles[0]])
        expected = np.array([0, 0, 10, 10])
        np.testing.assert_array_equal(union_bounds, expected)

    def test_union_bounds_empty_input(self, geometry_engine):
        """Test union bounds with empty input."""
        union_bounds = geometry_engine.calculate_union_bounds_batch([])
        expected = np.array([0, 0, 0, 0])
        np.testing.assert_array_equal(union_bounds, expected)

    # ==================== Coordinate Transformation Tests ====================

    def test_transform_coordinates_identity(self, geometry_engine):
        """Test coordinate transformation with identity matrices."""
        coordinates = np.array([[[1, 2], [3, 4]], [[5, 6], [7, 8]]], dtype=np.float64)
        identity_matrices = np.array([np.eye(3), np.eye(3)], dtype=np.float64)

        transformed = geometry_engine.transform_coordinates_batch(coordinates, identity_matrices)
        np.testing.assert_array_almost_equal(transformed, coordinates)

    def test_transform_coordinates_translation(self, geometry_engine):
        """Test coordinate transformation with translation."""
        coordinates = np.array([[[0, 0], [1, 1]], [[2, 2], [3, 3]]], dtype=np.float64)

        # Translation matrices
        transform1 = np.array([[1, 0, 10], [0, 1, 20], [0, 0, 1]], dtype=np.float64)
        transform2 = np.array([[1, 0, 30], [0, 1, 40], [0, 0, 1]], dtype=np.float64)
        transform_matrices = np.array([transform1, transform2])

        transformed = geometry_engine.transform_coordinates_batch(coordinates, transform_matrices)

        expected = np.array([[[10, 20], [11, 21]], [[32, 42], [33, 43]]], dtype=np.float64)
        np.testing.assert_array_almost_equal(transformed, expected)

    # ==================== Area Calculation Tests ====================

    def test_calculate_areas_rectangles(self, geometry_engine, sample_rectangles):
        """Test area calculation for rectangles."""
        areas = geometry_engine.calculate_shape_areas_batch(sample_rectangles)

        assert isinstance(areas, np.ndarray)
        assert len(areas) == len(sample_rectangles)

        # Expected areas: 10*10=100, 10*10=100, 15*15=225, 10*10=100
        expected_areas = np.array([100, 100, 225, 100], dtype=np.float64)
        np.testing.assert_array_almost_equal(areas, expected_areas)

    def test_calculate_areas_circles(self, geometry_engine, sample_circles):
        """Test area calculation for circles."""
        areas = geometry_engine.calculate_shape_areas_batch(sample_circles)

        assert isinstance(areas, np.ndarray)
        assert len(areas) == len(sample_circles)

        # Expected areas: π*3², π*4², π*2², π*5²
        expected_areas = np.array([np.pi * 9, np.pi * 16, np.pi * 4, np.pi * 25])
        np.testing.assert_array_almost_equal(areas, expected_areas, decimal=6)

    def test_calculate_areas_empty_input(self, geometry_engine):
        """Test area calculation with empty input."""
        areas = geometry_engine.calculate_shape_areas_batch([])
        assert isinstance(areas, np.ndarray)
        assert len(areas) == 0

    # ==================== Shape Complexity Tests ====================

    def test_optimize_shape_complexity_rectangles(self, geometry_engine, sample_rectangles):
        """Test complexity optimization for rectangles (no change expected)."""
        optimized = geometry_engine.optimize_shape_complexity_batch(sample_rectangles, max_points_per_shape=50)

        assert len(optimized) == len(sample_rectangles)
        for original, opt in zip(sample_rectangles, optimized):
            assert opt.shape_type == original.shape_type
            np.testing.assert_array_equal(opt.bounding_box, original.bounding_box)

    def test_optimize_polygon_complexity(self, geometry_engine):
        """Test polygon point reduction."""
        # Create polygon with many points
        many_points = np.array([[i, i % 3] for i in range(50)], dtype=np.float64)
        polygon = ShapeGeometry(
            shape_type=ShapeType.POLYGON,
            bounding_box=np.array([0, 0, 49, 2], dtype=np.float64),
            points=many_points,
            drawingml_xml="<polygon/>"
        )

        optimized = geometry_engine.optimize_shape_complexity_batch([polygon], max_points_per_shape=20)

        assert len(optimized) == 1
        assert hasattr(optimized[0], 'points')
        assert len(optimized[0].points) <= 20
        assert len(optimized[0].points) > 0

    # ==================== Shape Mask Generation Tests ====================

    def test_generate_shape_masks_rectangles(self, geometry_engine, sample_rectangles):
        """Test mask generation for rectangles."""
        canvas_size = (50, 50)
        resolution = 32

        masks = geometry_engine.generate_shape_masks_batch(
            sample_rectangles, canvas_size, resolution
        )

        assert masks.shape == (len(sample_rectangles), resolution, resolution)
        assert masks.dtype == bool
        assert masks.any()  # Should have some coverage

    def test_generate_masks_empty_shapes(self, geometry_engine):
        """Test mask generation with empty shape list."""
        masks = geometry_engine.generate_shape_masks_batch([], (100, 100), 16)
        assert masks.shape == (0, 16, 16)
        assert masks.dtype == bool

    # ==================== Performance Tests ====================

    def test_intersection_performance(self, geometry_engine):
        """Test intersection performance scaling."""
        n_shapes = 50
        shapes_a = []
        shapes_b = []

        for i in range(n_shapes):
            bbox_a = np.array([i*2, i*3, 10, 10], dtype=np.float64)
            bbox_b = np.array([i*2+5, i*3+5, 10, 10], dtype=np.float64)

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

        # Measure performance
        start_time = time.perf_counter()
        intersections = geometry_engine.calculate_shape_intersections_batch(shapes_a, shapes_b)
        elapsed = time.perf_counter() - start_time

        assert len(intersections) == n_shapes
        assert elapsed < 0.1  # Should complete quickly
        print(f"Intersection test for {n_shapes} pairs: {elapsed:.4f}s")

    def test_union_bounds_performance(self, geometry_engine):
        """Test union bounds performance."""
        n_shapes = 100
        shapes = []

        for i in range(n_shapes):
            bbox = np.array([i*5, i*3, 10+i%5, 8+i%3], dtype=np.float64)
            shape = ShapeGeometry(
                shape_type=ShapeType.RECTANGLE,
                bounding_box=bbox,
                drawingml_xml=f"<rect{i}/>"
            )
            shapes.append(shape)

        start_time = time.perf_counter()
        union_bounds = geometry_engine.calculate_union_bounds_batch(shapes)
        elapsed = time.perf_counter() - start_time

        assert union_bounds.shape == (4,)
        assert elapsed < 0.05  # Should be very fast
        print(f"Union bounds for {n_shapes} shapes: {elapsed:.4f}s")

    def test_area_calculation_performance(self, geometry_engine):
        """Test area calculation performance."""
        n_shapes = 200
        shapes = []

        for i in range(n_shapes):
            if i % 2 == 0:  # Rectangle
                bbox = np.array([i*2, i*3, 10+i%5, 8+i%3], dtype=np.float64)
                shape_type = ShapeType.RECTANGLE
            else:  # Circle
                r = 5 + i % 10
                bbox = np.array([i*2, i*3, 2*r, 2*r], dtype=np.float64)
                shape_type = ShapeType.CIRCLE

            shape = ShapeGeometry(
                shape_type=shape_type,
                bounding_box=bbox,
                drawingml_xml=f"<shape{i}/>"
            )
            shapes.append(shape)

        start_time = time.perf_counter()
        areas = geometry_engine.calculate_shape_areas_batch(shapes)
        elapsed = time.perf_counter() - start_time

        assert len(areas) == n_shapes
        assert np.all(areas > 0)  # All areas should be positive
        assert elapsed < 0.1  # Should complete quickly
        print(f"Area calculation for {n_shapes} shapes: {elapsed:.4f}s")

    # ==================== Algorithm Correctness Tests ====================

    def test_aabb_intersection_algorithm(self, geometry_engine):
        """Test AABB intersection algorithm correctness."""
        # Test cases: [box1, box2, expected_intersection]
        test_cases = [
            # Completely separate
            ([0, 0, 5, 5], [10, 10, 5, 5], False),
            # Overlapping
            ([0, 0, 10, 10], [5, 5, 10, 10], True),
            # Touching edges (should not intersect)
            ([0, 0, 5, 5], [5, 0, 5, 5], False),
            # One inside another
            ([0, 0, 20, 20], [5, 5, 5, 5], True),
            # Identical boxes
            ([0, 0, 10, 10], [0, 0, 10, 10], True),
        ]

        for i, (box1, box2, expected) in enumerate(test_cases):
            boxes_a = np.array([box1], dtype=np.float64)
            boxes_b = np.array([box2], dtype=np.float64)

            result = geometry_engine._intersect_aabb_batch(boxes_a, boxes_b)

            assert len(result) == 1, f"Test case {i}: Expected 1 result"
            assert result[0] == expected, f"Test case {i}: Expected {expected}, got {result[0]}"

    def test_circle_intersection_algorithm(self, geometry_engine):
        """Test circle intersection algorithm correctness."""
        # Test cases: [center1, center2, radius1, radius2, expected]
        test_cases = [
            # Separate circles
            ([0, 0], [10, 0], 3, 3, False),
            # Touching circles (distance = sum of radii)
            ([0, 0], [6, 0], 3, 3, True),
            # Overlapping circles
            ([0, 0], [4, 0], 3, 3, True),
            # One inside another
            ([0, 0], [1, 0], 5, 2, True),
            # Identical circles
            ([5, 5], [5, 5], 4, 4, True),
        ]

        for i, (center1, center2, r1, r2, expected) in enumerate(test_cases):
            centers_a = np.array([center1], dtype=np.float64)
            centers_b = np.array([center2], dtype=np.float64)
            radii_a = np.array([r1], dtype=np.float64)
            radii_b = np.array([r2], dtype=np.float64)

            result = geometry_engine._intersect_circles_batch(centers_a, centers_b, radii_a, radii_b)

            assert len(result) == 1, f"Test case {i}: Expected 1 result"
            assert result[0] == expected, f"Test case {i}: Expected {expected}, got {result[0]}"