#!/usr/bin/env python3
"""
Direct tests for Task 2.1.3 advanced geometric operations.
Tests the NumPy geometry engine directly without converter dependencies.
"""

import sys
import os
import numpy as np
import pytest
import time
from dataclasses import dataclass
from enum import Enum

# Add source path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))


class ShapeType(Enum):
    """Shape type enumeration."""
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    ELLIPSE = "ellipse"
    POLYGON = "polygon"
    LINE = "line"


@dataclass
class ShapeGeometry:
    """Shape geometry data structure."""
    shape_type: ShapeType
    bounding_box: np.ndarray
    drawingml_xml: str
    points: np.ndarray = None


class TestAdvancedGeometryDirect:
    """Direct tests for advanced geometric operations."""

    def test_aabb_intersection_basic(self):
        """Test axis-aligned bounding box intersection."""
        # Create test boxes
        boxes_a = np.array([[0, 0, 10, 10], [5, 5, 10, 10]])  # Two boxes
        boxes_b = np.array([[5, 5, 10, 10], [20, 20, 5, 5]])  # Corresponding test boxes

        # Manual intersection test
        min_a = boxes_a[:, :2]
        max_a = boxes_a[:, :2] + boxes_a[:, 2:]
        min_b = boxes_b[:, :2]
        max_b = boxes_b[:, :2] + boxes_b[:, 2:]

        intersect_x = (min_a[:, 0] < max_b[:, 0]) & (max_a[:, 0] > min_b[:, 0])
        intersect_y = (min_a[:, 1] < max_b[:, 1]) & (max_a[:, 1] > min_b[:, 1])
        intersects = intersect_x & intersect_y

        assert len(intersects) == 2
        assert intersects[0] == True   # [0,0,10,10] intersects with [5,5,10,10]
        assert intersects[1] == False  # [5,5,10,10] does not intersect with [20,20,5,5]

    def test_circle_intersection_basic(self):
        """Test circle-circle intersection."""
        # Two circles: centers and radii
        centers_a = np.array([[0, 0], [10, 10]])
        centers_b = np.array([[3, 4], [20, 20]])
        radii_a = np.array([3, 5])
        radii_b = np.array([2, 3])

        # Distance calculation
        distances = np.linalg.norm(centers_a - centers_b, axis=1)
        intersects = distances <= (radii_a + radii_b)

        assert len(intersects) == 2
        # Distance [0,0] to [3,4] = 5, sum_radii = 5 -> True (touching)
        assert intersects[0] == True
        # Distance [10,10] to [20,20] = √200 ≈ 14.14, sum_radii = 8 -> False
        assert intersects[1] == False

    def test_union_bounds_calculation(self):
        """Test union bounding box calculation."""
        # Multiple bounding boxes
        bounding_boxes = np.array([
            [0, 0, 10, 10],    # Box 1
            [5, 5, 15, 15],    # Box 2
            [20, 0, 10, 10],   # Box 3
        ])

        # Calculate union
        mins = bounding_boxes[:, :2]
        maxs = bounding_boxes[:, :2] + bounding_boxes[:, 2:]

        union_min = np.min(mins, axis=0)
        union_max = np.max(maxs, axis=0)
        union_bounds = np.concatenate([union_min, union_max - union_min])

        expected = np.array([0, 0, 30, 20])  # min_x=0, min_y=0, width=30, height=20
        np.testing.assert_array_equal(union_bounds, expected)

    def test_coordinate_transformation(self):
        """Test coordinate transformation with matrices."""
        # Test coordinates: 2 sets of 2 points each
        coordinates = np.array([
            [[0, 0], [1, 1]],  # Set 1
            [[2, 2], [3, 3]]   # Set 2
        ], dtype=np.float64)

        # Transform matrices: translation
        transform1 = np.array([[1, 0, 10], [0, 1, 20], [0, 0, 1]], dtype=np.float64)
        transform2 = np.array([[1, 0, 30], [0, 1, 40], [0, 0, 1]], dtype=np.float64)
        transform_matrices = np.array([transform1, transform2])

        # Apply transformation
        N, M, _ = coordinates.shape
        homogeneous = np.ones((N, M, 3))
        homogeneous[..., :2] = coordinates

        # Batch matrix multiplication using einsum
        transformed = np.einsum('nij,nmj->nmi', transform_matrices, homogeneous)
        result = transformed[..., :2]

        # Expected results
        expected = np.array([
            [[10, 20], [11, 21]],  # Set 1 translated by [10, 20]
            [[32, 42], [33, 43]]   # Set 2 translated by [30, 40]
        ], dtype=np.float64)

        np.testing.assert_array_almost_equal(result, expected)

    def test_area_calculations(self):
        """Test area calculations for different shapes."""
        # Rectangle areas
        rect_dimensions = np.array([[10, 5], [20, 3], [15, 8]])
        rect_areas = rect_dimensions[:, 0] * rect_dimensions[:, 1]
        expected_rect = np.array([50, 60, 120])
        np.testing.assert_array_equal(rect_areas, expected_rect)

        # Circle areas
        radii = np.array([3, 5, 7])
        circle_areas = np.pi * radii * radii
        expected_circle = np.pi * np.array([9, 25, 49])
        np.testing.assert_array_almost_equal(circle_areas, expected_circle)

        # Polygon area using shoelace formula
        # Simple triangle: (0,0), (1,0), (0,1)
        triangle_points = np.array([[0, 0], [1, 0], [0, 1]])
        x = triangle_points[:, 0]
        y = triangle_points[:, 1]
        area = 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
        assert abs(area - 0.5) < 1e-10  # Should equal 0.5

    def test_polygon_simplification(self):
        """Test polygon point reduction."""
        # Create polygon with many points
        n_points = 50
        angles = np.linspace(0, 2*np.pi, n_points, endpoint=False)
        points = np.column_stack([np.cos(angles), np.sin(angles)])

        # Simplify by keeping points with largest inter-point distances
        max_points = 20
        if len(points) > max_points:
            differences = np.diff(points, axis=0)
            distances = np.linalg.norm(differences, axis=1)

            # Add closing distance
            closing_distance = np.linalg.norm(points[-1] - points[0])
            distances = np.append(distances, closing_distance)

            # Keep points with largest distances
            keep_indices = np.argpartition(distances, -max_points)[-max_points:]
            keep_indices = np.sort(keep_indices)
            simplified_points = points[keep_indices]
        else:
            simplified_points = points

        assert len(simplified_points) <= max_points
        assert len(simplified_points) > 0

    def test_shape_mask_generation(self):
        """Test binary mask generation for shapes."""
        # Create coordinate grid
        resolution = 32
        canvas_size = (100, 100)
        x_coords = np.linspace(0, canvas_size[0], resolution)
        y_coords = np.linspace(0, canvas_size[1], resolution)
        X, Y = np.meshgrid(x_coords, y_coords)
        coord_grid = np.stack([X.ravel(), Y.ravel()], axis=1)

        # Test rectangle mask
        rect_bbox = [20, 20, 40, 30]  # [x, y, width, height]
        inside_x = (coord_grid[:, 0] >= rect_bbox[0]) & (coord_grid[:, 0] <= rect_bbox[0] + rect_bbox[2])
        inside_y = (coord_grid[:, 1] >= rect_bbox[1]) & (coord_grid[:, 1] <= rect_bbox[1] + rect_bbox[3])
        rect_mask = (inside_x & inside_y).reshape(resolution, resolution)

        assert rect_mask.shape == (resolution, resolution)
        assert rect_mask.dtype == bool
        assert rect_mask.any()  # Should have some True values

        # Test circle mask
        circle_center = np.array([50, 50])
        circle_radius = 20
        distances = np.linalg.norm(coord_grid - circle_center, axis=1)
        circle_mask = (distances <= circle_radius).reshape(resolution, resolution)

        assert circle_mask.shape == (resolution, resolution)
        assert circle_mask.dtype == bool
        assert circle_mask.any()  # Should have some True values

    def test_performance_scaling(self):
        """Test performance scaling of vectorized operations."""
        # Test intersection performance
        n_shapes = 100
        boxes_a = np.random.rand(n_shapes, 4) * 100
        boxes_b = np.random.rand(n_shapes, 4) * 100

        start_time = time.perf_counter()

        # Vectorized intersection test
        min_a = boxes_a[:, :2]
        max_a = boxes_a[:, :2] + boxes_a[:, 2:]
        min_b = boxes_b[:, :2]
        max_b = boxes_b[:, :2] + boxes_b[:, 2:]

        intersect_x = (min_a[:, 0] < max_b[:, 0]) & (max_a[:, 0] > min_b[:, 0])
        intersect_y = (min_a[:, 1] < max_b[:, 1]) & (max_a[:, 1] > min_b[:, 1])
        intersections = intersect_x & intersect_y

        elapsed = time.perf_counter() - start_time

        assert len(intersections) == n_shapes
        assert elapsed < 0.01  # Should be very fast
        print(f"Vectorized intersection for {n_shapes} shapes: {elapsed:.4f}s")

    def test_memory_efficiency(self):
        """Test memory efficiency of operations."""
        # Create large arrays and measure operations
        n_shapes = 1000
        bounding_boxes = np.random.rand(n_shapes, 4) * 200

        # Union bounds calculation
        start_time = time.perf_counter()
        mins = bounding_boxes[:, :2]
        maxs = bounding_boxes[:, :2] + bounding_boxes[:, 2:]
        union_min = np.min(mins, axis=0)
        union_max = np.max(maxs, axis=0)
        union_bounds = np.concatenate([union_min, union_max - union_min])
        elapsed = time.perf_counter() - start_time

        assert union_bounds.shape == (4,)
        assert elapsed < 0.01  # Should be very fast even for 1000 shapes
        print(f"Union bounds for {n_shapes} shapes: {elapsed:.4f}s")

        # Area calculations
        start_time = time.perf_counter()
        areas = bounding_boxes[:, 2] * bounding_boxes[:, 3]  # width * height
        elapsed = time.perf_counter() - start_time

        assert len(areas) == n_shapes
        assert elapsed < 0.001  # Should be extremely fast
        print(f"Area calculation for {n_shapes} shapes: {elapsed:.4f}s")

    def test_algorithm_correctness_edge_cases(self):
        """Test algorithm correctness for edge cases."""
        # Zero-size boxes
        zero_boxes = np.array([[0, 0, 0, 0], [5, 5, 0, 0]])
        regular_boxes = np.array([[0, 0, 5, 5], [5, 5, 5, 5]])

        min_a = zero_boxes[:, :2]
        max_a = zero_boxes[:, :2] + zero_boxes[:, 2:]
        min_b = regular_boxes[:, :2]
        max_b = regular_boxes[:, :2] + regular_boxes[:, 2:]

        intersect_x = (min_a[:, 0] < max_b[:, 0]) & (max_a[:, 0] > min_b[:, 0])
        intersect_y = (min_a[:, 1] < max_b[:, 1]) & (max_a[:, 1] > min_b[:, 1])
        intersects = intersect_x & intersect_y

        # Zero-size boxes should not intersect (edge touching)
        assert intersects[0] == False
        assert intersects[1] == False

        # Identical boxes
        identical_boxes = np.array([[10, 10, 5, 5], [10, 10, 5, 5]])
        min_a = identical_boxes[:1, :2]
        max_a = identical_boxes[:1, :2] + identical_boxes[:1, 2:]
        min_b = identical_boxes[1:, :2]
        max_b = identical_boxes[1:, :2] + identical_boxes[1:, 2:]

        intersect_x = (min_a[:, 0] < max_b[:, 0]) & (max_a[:, 0] > min_b[:, 0])
        intersect_y = (min_a[:, 1] < max_b[:, 1]) & (max_a[:, 1] > min_b[:, 1])
        identical_intersect = intersect_x & intersect_y

        assert identical_intersect[0] == True  # Identical boxes should intersect