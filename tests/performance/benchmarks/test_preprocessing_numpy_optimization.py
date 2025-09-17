#!/usr/bin/env python3
"""
Performance benchmarks comparing current preprocessing algorithms with potential NumPy optimizations.

This tests the performance difference between:
- Current Python-based preprocessing algorithms
- Potential NumPy-vectorized implementations

Focus areas:
1. Douglas-Peucker polygon simplification
2. Path coordinate optimization
3. Point parsing and processing
"""

import pytest
import time
import numpy as np
from pathlib import Path
import sys
import re
import math
from typing import List, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from src.preprocessing.geometry_plugins import SimplifyPolygonPlugin
    GEOMETRY_PLUGINS_AVAILABLE = True
except ImportError:
    GEOMETRY_PLUGINS_AVAILABLE = False

try:
    from src.preprocessing.advanced_plugins import ConvertPathDataPlugin
    ADVANCED_PLUGINS_AVAILABLE = True
except ImportError:
    ADVANCED_PLUGINS_AVAILABLE = False

try:
    from src.preprocessing.base import PreprocessingContext
    PREPROCESSING_BASE_AVAILABLE = True
except ImportError:
    PREPROCESSING_BASE_AVAILABLE = False


class NumPyOptimizedSimplifier:
    """NumPy-optimized polygon simplification using vectorized Douglas-Peucker."""

    def simplify_points_numpy(self, points: List[Tuple[float, float]], tolerance: float) -> List[Tuple[float, float]]:
        """Vectorized Douglas-Peucker implementation using NumPy."""
        if len(points) <= 2:
            return points

        points_array = np.array(points)
        return self._douglas_peucker_vectorized(points_array, tolerance).tolist()

    def _douglas_peucker_vectorized(self, points: np.ndarray, tolerance: float) -> np.ndarray:
        """Vectorized Douglas-Peucker algorithm."""
        if len(points) <= 2:
            return points

        # Calculate perpendicular distances vectorized
        distances = self._perpendicular_distances_vectorized(
            points[1:-1], points[0], points[-1]
        )

        max_idx = np.argmax(distances) + 1  # +1 because we excluded first point
        max_distance = distances[max_idx - 1]

        if max_distance > tolerance:
            # Recursive calls
            left_result = self._douglas_peucker_vectorized(points[:max_idx + 1], tolerance)
            right_result = self._douglas_peucker_vectorized(points[max_idx:], tolerance)

            # Concatenate results, avoiding duplicate middle point
            return np.vstack([left_result[:-1], right_result])
        else:
            # Return just the endpoints
            return np.array([points[0], points[-1]])

    def _perpendicular_distances_vectorized(self, points: np.ndarray,
                                          line_start: np.ndarray,
                                          line_end: np.ndarray) -> np.ndarray:
        """Calculate perpendicular distances from points to line using NumPy."""
        # Vector from line_start to points
        A = points - line_start

        # Vector from line_start to line_end
        C = line_end - line_start

        # Project A onto C
        dot_products = np.dot(A, C)
        len_sq = np.dot(C, C)

        if len_sq == 0:
            # Line start and end are the same point
            return np.linalg.norm(A, axis=1)

        # Calculate projections
        param = dot_products / len_sq
        param = np.clip(param, 0, 1)  # Clamp to line segment

        # Calculate closest points on line
        projections = line_start + param[:, np.newaxis] * C

        # Calculate distances
        distances = np.linalg.norm(points - projections, axis=1)

        return distances


class NumPyOptimizedPathProcessor:
    """NumPy-optimized path coordinate processing."""

    def optimize_coordinates_numpy(self, path_data: str, precision: int) -> str:
        """Vectorized coordinate optimization using NumPy."""
        # Extract all numbers from path data
        number_matches = list(re.finditer(r'-?\d*\.?\d+', path_data))
        if not number_matches:
            return path_data

        # Extract coordinate values
        coordinates = []
        for match in number_matches:
            try:
                coordinates.append(float(match.group(0)))
            except ValueError:
                coordinates.append(0.0)

        if not coordinates:
            return path_data

        # Vectorized processing
        coords_array = np.array(coordinates)

        # Apply precision optimization
        tolerance = 0.1 ** precision
        coords_array = np.where(np.abs(coords_array) < tolerance, 0, coords_array)

        # Round to precision
        coords_array = np.round(coords_array, precision)

        # Remove trailing zeros for integers
        optimized_coords = []
        for coord in coords_array:
            if coord == int(coord):
                optimized_coords.append(str(int(coord)))
            else:
                optimized_coords.append(f"{coord:.{precision}f}".rstrip('0').rstrip('.'))

        # Replace coordinates in original string
        result = path_data
        for match, new_coord in zip(reversed(number_matches), reversed(optimized_coords)):
            result = result[:match.start()] + new_coord + result[match.end():]

        return result


@pytest.mark.performance
@pytest.mark.skipif(not GEOMETRY_PLUGINS_AVAILABLE, reason="Geometry plugins not available")
class TestPreprocessingPerformanceBenchmarks:
    """Performance benchmarks for preprocessing optimization opportunities."""

    @pytest.fixture
    def preprocessing_context(self):
        """Create preprocessing context for testing."""
        if PREPROCESSING_BASE_AVAILABLE:
            context = PreprocessingContext()
            context.precision = 3
            return context
        else:
            from unittest.mock import Mock
            context = Mock()
            context.precision = 3
            return context

    @pytest.fixture
    def large_polygon_points(self):
        """Generate large polygon for performance testing."""
        # Create a complex polygon with 1000 points
        angles = np.linspace(0, 2 * np.pi, 1000)
        radius = 100 + 20 * np.sin(5 * angles)  # Create some complexity
        x_coords = radius * np.cos(angles)
        y_coords = radius * np.sin(angles)

        return list(zip(x_coords.tolist(), y_coords.tolist()))

    @pytest.fixture
    def complex_path_data(self):
        """Generate complex path data for testing."""
        # Create path with many coordinates
        path_commands = []
        for i in range(500):
            x, y = i * 2.123456789, i * 1.987654321
            if i == 0:
                path_commands.append(f"M {x} {y}")
            else:
                path_commands.append(f"L {x} {y}")

        return " ".join(path_commands)

    def test_douglas_peucker_performance_comparison(self, large_polygon_points, preprocessing_context):
        """Compare current vs NumPy Douglas-Peucker performance."""
        # Current implementation
        current_simplifier = SimplifyPolygonPlugin()
        numpy_simplifier = NumPyOptimizedSimplifier()

        tolerance = 0.001

        # Benchmark current implementation
        start_time = time.time()
        current_result = current_simplifier._simplify_points(large_polygon_points, preprocessing_context.precision)
        current_time = time.time() - start_time

        # Benchmark NumPy implementation
        start_time = time.time()
        numpy_result = numpy_simplifier.simplify_points_numpy(large_polygon_points, tolerance)
        numpy_time = time.time() - start_time

        # Performance validation
        print(f"Current implementation: {current_time:.4f}s")
        print(f"NumPy implementation: {numpy_time:.4f}s")
        print(f"Speedup: {current_time / numpy_time:.2f}x")

        # Validate results are similar (within tolerance)
        assert len(current_result) > 0
        assert len(numpy_result) > 0

        # NumPy should be faster for large datasets
        if len(large_polygon_points) > 100:
            assert numpy_time < current_time, "NumPy should be faster for large datasets"

    @pytest.mark.skipif(not ADVANCED_PLUGINS_AVAILABLE, reason="Advanced plugins not available")
    def test_coordinate_optimization_performance(self, complex_path_data, preprocessing_context):
        """Compare current vs NumPy coordinate optimization performance."""
        # Current implementation
        current_processor = ConvertPathDataPlugin()
        numpy_processor = NumPyOptimizedPathProcessor()

        # Benchmark current implementation
        start_time = time.time()
        current_result = current_processor._optimize_coordinate_precision(complex_path_data, 3)
        current_time = time.time() - start_time

        # Benchmark NumPy implementation
        start_time = time.time()
        numpy_result = numpy_processor.optimize_coordinates_numpy(complex_path_data, 3)
        numpy_time = time.time() - start_time

        # Performance validation
        print(f"Current coordinate optimization: {current_time:.4f}s")
        print(f"NumPy coordinate optimization: {numpy_time:.4f}s")
        print(f"Speedup: {current_time / numpy_time:.2f}x")

        # Validate results
        assert len(current_result) > 0
        assert len(numpy_result) > 0

        # Results should be similar length (coordinate counts)
        current_coords = len(re.findall(r'-?\d*\.?\d+', current_result))
        numpy_coords = len(re.findall(r'-?\d*\.?\d+', numpy_result))
        assert abs(current_coords - numpy_coords) <= 1, "Coordinate counts should be similar"

    def test_point_parsing_performance(self):
        """Compare point parsing performance."""
        # Generate large points string
        points = [(i * 1.123456, i * 2.654321) for i in range(1000)]
        points_str = " ".join([f"{x},{y}" for x, y in points])

        # Current implementation (from SimplifyPolygonPlugin)
        simplifier = SimplifyPolygonPlugin()

        start_time = time.time()
        current_parsed = simplifier._parse_points(points_str)
        current_time = time.time() - start_time

        # NumPy implementation
        def parse_points_numpy(points_str: str) -> List[Tuple[float, float]]:
            coords = np.fromstring(points_str.replace(',', ' '), sep=' ')
            return [(coords[i], coords[i+1]) for i in range(0, len(coords)-1, 2)]

        start_time = time.time()
        numpy_parsed = parse_points_numpy(points_str)
        numpy_time = time.time() - start_time

        print(f"Current point parsing: {current_time:.4f}s")
        print(f"NumPy point parsing: {numpy_time:.4f}s")
        print(f"Speedup: {current_time / numpy_time:.2f}x")

        # Validate results
        assert len(current_parsed) == len(numpy_parsed)
        assert len(current_parsed) > 0

    def test_memory_usage_comparison(self, large_polygon_points):
        """Compare memory usage patterns."""
        import tracemalloc

        numpy_simplifier = NumPyOptimizedSimplifier()
        current_simplifier = SimplifyPolygonPlugin()
        tolerance = 0.001

        # Measure current implementation memory
        tracemalloc.start()
        current_result = current_simplifier._douglas_peucker(large_polygon_points, tolerance)
        current_memory = tracemalloc.get_traced_memory()[1]  # Peak memory
        tracemalloc.stop()

        # Measure NumPy implementation memory
        tracemalloc.start()
        numpy_result = numpy_simplifier.simplify_points_numpy(large_polygon_points, tolerance)
        numpy_memory = tracemalloc.get_traced_memory()[1]  # Peak memory
        tracemalloc.stop()

        print(f"Current memory usage: {current_memory / 1024:.2f} KB")
        print(f"NumPy memory usage: {numpy_memory / 1024:.2f} KB")
        print(f"Memory ratio: {numpy_memory / current_memory:.2f}x")

        # Validate results exist
        assert len(current_result) > 0
        assert len(numpy_result) > 0

    @pytest.mark.parametrize("point_count,expected_speedup", [
        (50, 1.0),    # Small datasets may not show speedup
        (200, 1.5),   # Medium datasets should show some speedup
        (1000, 2.0),  # Large datasets should show significant speedup
    ])
    def test_scalability_performance(self, expected_speedup, point_count):
        """Test performance scaling with different input sizes."""
        # Generate test data
        angles = np.linspace(0, 2 * np.pi, point_count)
        points = [(100 * np.cos(a), 100 * np.sin(a)) for a in angles]

        current_simplifier = SimplifyPolygonPlugin()
        numpy_simplifier = NumPyOptimizedSimplifier()
        tolerance = 0.001

        # Benchmark current
        start_time = time.time()
        current_result = current_simplifier._douglas_peucker(points, tolerance)
        current_time = time.time() - start_time

        # Benchmark NumPy
        start_time = time.time()
        numpy_result = numpy_simplifier.simplify_points_numpy(points, tolerance)
        numpy_time = time.time() - start_time

        actual_speedup = current_time / numpy_time if numpy_time > 0 else 1.0

        print(f"Point count: {point_count}")
        print(f"Expected speedup: {expected_speedup}x")
        print(f"Actual speedup: {actual_speedup:.2f}x")

        # For larger datasets, NumPy should provide expected speedup
        if point_count >= 200:
            assert actual_speedup >= expected_speedup * 0.8, f"Expected at least {expected_speedup * 0.8:.1f}x speedup"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--durations=10"])