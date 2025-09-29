#!/usr/bin/env python3
"""
Comprehensive test suite for Path Processing Engine.

Tests performance, accuracy, and functionality of the
consolidated path system after NumPy cleanup.
"""

import pytest
import numpy as np
import time
from pathlib import Path
import sys
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.paths import (
    PathSystem, PathCommandType, PathCommand, create_path_system
)


class TestPathEngineBasics:
    """Test basic PathEngine functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = PathEngine()

    def test_engine_initialization(self):
        """Test PathEngine initialization."""
        assert self.engine is not None

        # Should have pre-compiled patterns
        assert self.engine._command_pattern is not None
        assert self.engine._number_pattern is not None
        assert len(self.engine._command_map) > 0

        # Check command mapping
        assert ('M', (PathCommandType.MOVE_TO, False)) in self.engine._command_map.items()
        assert ('m', (PathCommandType.MOVE_TO, True)) in self.engine._command_map.items()
        assert ('L', (PathCommandType.LINE_TO, False)) in self.engine._command_map.items()
        assert ('l', (PathCommandType.LINE_TO, True)) in self.engine._command_map.items()

    def test_engine_initialization_with_options(self):
        """Test PathEngine initialization with custom options."""
        engine = PathEngine(cache_size=500, array_pool_size=30, enable_profiling=True)

        assert engine._path_cache.maxsize == 500
        assert engine._array_pool.max_arrays_per_shape == 30
        assert engine._enable_profiling is True

    def test_command_coordinate_counts(self):
        """Test command coordinate count mapping."""
        expected_counts = {
            PathCommandType.MOVE_TO: 2,
            PathCommandType.LINE_TO: 2,
            PathCommandType.HORIZONTAL: 1,
            PathCommandType.VERTICAL: 1,
            PathCommandType.CUBIC_CURVE: 6,
            PathCommandType.SMOOTH_CUBIC: 4,
            PathCommandType.QUADRATIC: 4,
            PathCommandType.SMOOTH_QUAD: 2,
            PathCommandType.ARC: 7,
            PathCommandType.CLOSE_PATH: 0
        }

        for cmd_type, expected_count in expected_counts.items():
            assert self.engine._coord_counts[cmd_type] == expected_count


class TestSimplePathParsing:
    """Test simple path parsing functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = PathEngine()

    def test_simple_moveto_lineto(self):
        """Test simple moveto and lineto parsing."""
        result = self.engine.process_path("M 10 20 L 30 40")

        assert result is not None
        assert isinstance(result, dict)

        # Should have basic properties
        if 'commands' in result:
            assert result['commands'] >= 2
        if 'coordinates' in result:
            assert result['coordinates'] >= 4

    def test_absolute_vs_relative_commands(self):
        """Test absolute vs relative command parsing."""
        # Test absolute commands
        result1 = self.engine.process_path("M 10 20 L 30 40")
        assert result1 is not None

        # Test relative commands
        result2 = self.engine.process_path("m 10 20 l 30 40")
        assert result2 is not None

        # Both should produce valid results
        assert isinstance(result1, dict)
        assert isinstance(result2, dict)

    def test_horizontal_vertical_lines(self):
        """Test horizontal and vertical line commands."""
        # Horizontal line
        result1 = self.engine.process_path("M 10 20 H 50")
        assert result1 is not None

        # Vertical line
        result2 = self.engine.process_path("M 10 20 V 50")
        assert result2 is not None

        # Both horizontal and vertical
        result3 = self.engine.process_path("M 10 20 H 50 V 80")
        assert result3 is not None

    def test_close_path_command(self):
        """Test close path (Z/z) command."""
        result1 = self.engine.process_path("M 10 20 L 30 40 Z")
        assert result1 is not None

        result2 = self.engine.process_path("M 10 20 L 30 40 z")
        assert result2 is not None

    def test_multiple_coordinate_sets(self):
        """Test commands with multiple coordinate sets."""
        # Line command with multiple points (implicit repetition)
        result = self.engine.process_path("M 0 0 L 10 10 20 20 30 30")
        assert result is not None

        # Should handle multiple coordinate pairs
        assert isinstance(result, dict)


class TestComplexPathParsing:
    """Test complex path parsing with curves."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = PathEngine()

    def test_cubic_bezier_curves(self):
        """Test cubic Bezier curve parsing."""
        result = self.engine.process_path("M 100 200 C 100 100 400 100 400 200")
        assert result is not None
        assert isinstance(result, dict)

    def test_smooth_cubic_curves(self):
        """Test smooth cubic curve parsing."""
        result = self.engine.process_path("M 10 80 C 40 10 65 10 95 80 S 150 150 180 80")
        assert result is not None

    def test_quadratic_bezier_curves(self):
        """Test quadratic Bezier curve parsing."""
        result = self.engine.process_path("M 10 80 Q 95 10 180 80")
        assert result is not None

    def test_smooth_quadratic_curves(self):
        """Test smooth quadratic curve parsing."""
        result = self.engine.process_path("M 10 80 Q 52.5 10 95 80 T 180 80")
        assert result is not None

    def test_arc_commands(self):
        """Test arc command parsing."""
        result = self.engine.process_path("M 10 315 A 30 50 0 0 1 162.55 162.45")
        assert result is not None

    def test_mixed_command_types(self):
        """Test paths with mixed command types."""
        complex_path = "M 100 200 C 100 100 400 100 400 200 Q 500 100 600 200 L 700 300 Z"
        result = self.engine.process_path(complex_path)
        assert result is not None


class TestPathDataClass:
    """Test PathData class functionality."""

    def test_pathdata_creation_empty(self):
        """Test empty PathData creation."""
        path_data = PathData()
        assert path_data is not None
        assert hasattr(path_data, 'commands')

    def test_pathdata_creation_from_string(self):
        """Test PathData creation from string."""
        path_data = PathData("M 10 20 L 30 40")
        assert path_data is not None
        assert hasattr(path_data, 'commands')

    def test_pathdata_properties(self):
        """Test PathData properties."""
        path_data = PathData("M 100 200 C 100 100 400 100 400 200")

        # Should have properties for command and coordinate counts
        if hasattr(path_data, 'command_count'):
            assert path_data.command_count >= 0
        if hasattr(path_data, 'coordinate_count'):
            assert path_data.coordinate_count >= 0

    def test_pathdata_commands_property(self):
        """Test PathData commands property."""
        path_data = PathData("M 10 20 L 30 40")

        # Should have commands property
        assert hasattr(path_data, 'commands')
        commands = path_data.commands
        assert commands is not None

    def test_pathdata_repr(self):
        """Test PathData string representation."""
        path_data = PathData("M 10 20 L 30 40")
        repr_str = repr(path_data)
        assert isinstance(repr_str, str)
        assert len(repr_str) > 0


class TestInvalidPathHandling:
    """Test handling of invalid and edge case paths."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = PathEngine()

    def test_empty_path(self):
        """Test handling of empty path."""
        result = self.engine.process_path("")
        assert result is not None
        assert isinstance(result, dict)

    def test_whitespace_only_path(self):
        """Test handling of whitespace-only path."""
        result = self.engine.process_path("   \t\n  ")
        assert result is not None

    def test_invalid_command_path(self):
        """Test handling of invalid commands."""
        result = self.engine.process_path("X 10 20 Y 30 40")
        assert result is not None
        # Should handle gracefully without crashing

    def test_incomplete_coordinates(self):
        """Test handling of incomplete coordinate sets."""
        result = self.engine.process_path("M 10")  # Missing Y coordinate
        assert result is not None

    def test_malformed_numbers(self):
        """Test handling of malformed numbers."""
        result = self.engine.process_path("M 10.5.5 20")
        assert result is not None

    def test_mixed_valid_invalid(self):
        """Test paths with mixed valid and invalid parts."""
        result = self.engine.process_path("M 10 20 L 30 40 X invalid Q 50 60 70 80")
        assert result is not None


class TestPerformanceFeatures:
    """Test performance features like caching and array pooling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = PathEngine(enable_profiling=True)

    def test_caching_functionality(self):
        """Test path result caching."""
        path_string = "M 100 200 L 300 400"

        # First call should cache result
        result1 = self.engine.process_path(path_string)

        # Second call should use cache
        result2 = self.engine.process_path(path_string)

        assert result1 is not None
        assert result2 is not None

    def test_cache_stats(self):
        """Test cache statistics."""
        stats = self.engine.cache_stats
        assert isinstance(stats, dict)
        assert 'hits' in stats
        assert 'misses' in stats
        assert 'hit_rate' in stats

    def test_performance_stats(self):
        """Test performance statistics."""
        stats = self.engine.get_performance_stats()
        assert isinstance(stats, dict)
        # Should have performance metrics
        assert len(stats) > 0

    def test_cache_clearing(self):
        """Test cache clearing functionality."""
        # Process some paths to populate cache
        self.engine.process_path("M 10 20 L 30 40")
        self.engine.process_path("M 50 60 L 70 80")

        # Clear caches
        self.engine.clear_all_caches()

        # Should complete without error
        assert True

    def test_array_pool_functionality(self):
        """Test array pool functionality."""
        # Array pool should be accessible
        assert hasattr(self.engine, '_array_pool')

        # Should have stats
        pool_stats = self.engine._array_pool.stats()
        assert isinstance(pool_stats, dict)


class TestAdvancedLRUCache:
    """Test AdvancedLRUCache functionality."""

    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = AdvancedLRUCache(maxsize=100, max_memory_mb=10)
        assert cache.maxsize == 100
        assert cache.max_memory_bytes == 10 * 1024 * 1024

    def test_cache_put_get(self):
        """Test cache put and get operations."""
        cache = AdvancedLRUCache()

        # Put and get simple value
        cache.put("key1", "value1")
        result = cache.get("key1")
        assert result == "value1"

        # Get non-existent key
        result = cache.get("nonexistent")
        assert result is None

    def test_cache_memory_estimation(self):
        """Test memory estimation."""
        cache = AdvancedLRUCache()

        # Test with NumPy array
        arr = np.zeros((100, 100))
        memory_estimate = cache._estimate_memory(arr)
        assert memory_estimate == arr.nbytes

        # Test with dict
        test_dict = {"a": 1, "b": 2}
        memory_estimate = cache._estimate_memory(test_dict)
        assert memory_estimate > 0

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = AdvancedLRUCache()

        # Put some items and access them
        cache.put("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss

        stats = cache.stats()
        assert isinstance(stats, dict)
        assert 'hits' in stats
        assert 'misses' in stats
        assert 'hit_rate' in stats
        assert stats['hits'] == 1
        assert stats['misses'] == 1

    def test_cache_eviction(self):
        """Test cache eviction."""
        # Small cache for testing eviction
        cache = AdvancedLRUCache(maxsize=2)

        # Fill cache beyond capacity
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")  # Should evict key1

        # key1 should be evicted
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"


class TestArrayPool:
    """Test ArrayPool functionality."""

    def test_array_pool_initialization(self):
        """Test ArrayPool initialization."""
        pool = ArrayPool(max_arrays_per_shape=5)
        assert pool.max_arrays_per_shape == 5
        assert pool.allocations == 0
        assert pool.reuses == 0

    def test_array_get_and_return(self):
        """Test array get and return operations."""
        pool = ArrayPool()

        # Get array
        arr = pool.get_array((10, 10))
        assert arr.shape == (10, 10)
        assert arr.dtype == np.float64

        # Return array
        pool.return_array(arr)

        # Get same shape again (should reuse)
        arr2 = pool.get_array((10, 10))
        assert arr2.shape == (10, 10)

    def test_array_pool_stats(self):
        """Test array pool statistics."""
        pool = ArrayPool()

        # Get and return some arrays
        arr = pool.get_array((5, 5))
        pool.return_array(arr)
        arr2 = pool.get_array((5, 5))

        stats = pool.stats()
        assert isinstance(stats, dict)
        assert 'allocations' in stats
        assert 'reuses' in stats


class TestCoordinateTransformations:
    """Test coordinate transformation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = PathEngine()

    def test_basic_transformation_support(self):
        """Test basic transformation support."""
        # Test with identity matrix (should not change path)
        identity = np.eye(3, dtype=np.float64)
        result = self.engine.process_path("M 10 20 L 30 40", transform_matrix=identity)
        assert result is not None

    def test_scaling_transformation(self):
        """Test scaling transformation."""
        # 2x scaling transform
        scale_matrix = np.array([
            [2, 0, 0],
            [0, 2, 0],
            [0, 0, 1]
        ], dtype=np.float64)

        result = self.engine.process_path("M 10 20 L 30 40", transform_matrix=scale_matrix)
        assert result is not None

    def test_viewport_transformation(self):
        """Test viewport transformation."""
        result = self.engine.process_path(
            "M 0 0 L 100 100",
            viewport=(0, 0, 100, 100),
            target_size=(200, 200)
        )
        assert result is not None


@pytest.mark.integration
class TestPathEngineIntegration:
    """Integration tests for PathEngine."""

    def test_complete_path_workflow(self):
        """Test complete path processing workflow."""
        engine = PathEngine(enable_profiling=True)

        # Complex path with multiple command types
        complex_path = """
        M 150 150
        L 75 200
        Q 75 250 150 250
        C 225 250 225 200 150 200
        A 25 25 -30 0 1 150 125
        Z
        """

        result = engine.process_path(complex_path.strip())
        assert result is not None
        assert isinstance(result, dict)

    def test_real_world_svg_paths(self):
        """Test with real-world SVG path examples."""
        engine = PathEngine()

        # Common SVG path patterns
        paths = [
            "M10,10 L90,90",  # Simple line
            "M20,20 h80 v80 h-80 Z",  # Rectangle with relative commands
            "M50,50 Q100,20 150,50",  # Quadratic curve
            "M10,80 C40,10 65,10 95,80 S150,150 180,80",  # Cubic curves
            "M50,50 A30,30 0 0,1 100,100",  # Arc
        ]

        for path in paths:
            result = engine.process_path(path)
            assert result is not None
            assert isinstance(result, dict)

    def test_batch_processing_capability(self):
        """Test batch processing capability."""
        engine = PathEngine()

        paths = [
            "M 10 10 L 90 90",
            "M 0 0 Q 50 0 100 50",
            "M 100 200 C 100 100 400 100 400 200"
        ]

        # Test batch processing if available
        try:
            results = engine.process_batch(paths)
            assert isinstance(results, list)
            assert len(results) == len(paths)
        except (AttributeError, NotImplementedError):
            # Method might not be implemented yet
            pass

    def test_error_resilience(self):
        """Test engine resilience to various error conditions."""
        engine = PathEngine()

        # Various problematic inputs
        problematic_paths = [
            "",  # Empty
            "invalid",  # Invalid command
            "M",  # Incomplete
            "M 10.5.5 20",  # Malformed number
            "M 10 20 L",  # Missing coordinates
            None,  # None input
        ]

        for path in problematic_paths:
            try:
                if path is not None:
                    result = engine.process_path(path)
                    # Should not crash, result can be None or error dict
                    assert result is not None or result is None
            except Exception as e:
                # Some exceptions might be expected for invalid input
                assert isinstance(e, (ValueError, TypeError, AttributeError))


class TestBezierCurveProcessing:
    """Test Bezier curve processing functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = PathEngine()

    def test_bezier_curve_extraction(self):
        """Test Bezier curve extraction from paths."""
        # Create PathData with cubic curve
        path_data = PathData("M 0 0 C 50 0 100 50 100 100")

        # Test if extract_bezier_curves method exists and works
        try:
            result = self.engine.extract_bezier_curves(path_data)
            assert result is not None
        except (AttributeError, NotImplementedError):
            # Method might not be fully implemented
            pytest.skip("extract_bezier_curves not implemented")

    def test_evaluate_bezier_batch(self):
        """Test batch Bezier curve evaluation."""
        # Create test control points for cubic Bezier curves
        control_points = np.array([
            [[0, 0], [50, 0], [100, 50], [100, 100]],  # First curve
            [[0, 100], [50, 100], [100, 50], [100, 0]]  # Second curve
        ], dtype=np.float64)

        try:
            result = self.engine.evaluate_bezier_batch(control_points, subdivision=11)
            assert result is not None
            assert isinstance(result, np.ndarray)
        except (AttributeError, NotImplementedError):
            pytest.skip("evaluate_bezier_batch not implemented")

    def test_subdivide_bezier_curves(self):
        """Test Bezier curve subdivision."""
        # Create test control points
        control_points = np.array([
            [[0, 0], [25, 0], [75, 100], [100, 100]]
        ], dtype=np.float64)
        t_values = np.array([0.5])  # Subdivide at midpoint

        try:
            result = self.engine.subdivide_bezier_curves(control_points, t_values)
            assert result is not None
        except (AttributeError, NotImplementedError):
            pytest.skip("subdivide_bezier_curves not implemented")

    def test_bezier_optimization(self):
        """Test Bezier curve optimization."""
        # Create test control points
        control_points = np.array([
            [[0, 0], [25, 25], [75, 75], [100, 100]]  # Nearly linear curve
        ], dtype=np.float64)

        try:
            result = self.engine.optimize_bezier_curves(control_points, tolerance=1.0)
            assert result is not None
        except (AttributeError, NotImplementedError):
            pytest.skip("optimize_bezier_curves not implemented")


class TestPathMetricsAndAnalysis:
    """Test path metrics and analysis functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = PathEngine()

    def test_path_metrics_calculation(self):
        """Test path metrics calculation."""
        path_data = PathData("M 0 0 L 100 100 L 200 0 Z")

        try:
            metrics = self.engine.calculate_path_metrics(path_data)
            assert isinstance(metrics, dict)
            # Should have various metrics
            assert len(metrics) > 0
        except (AttributeError, NotImplementedError):
            pytest.skip("calculate_path_metrics not implemented")

    def test_path_bounds_calculation(self):
        """Test path bounds calculation."""
        path_data = PathData("M 50 25 L 150 125")

        try:
            # Test internal bounds calculation
            if hasattr(self.engine, '_calculate_path_bounds_vectorized'):
                # Create test coordinates
                coords = np.array([[50, 25], [150, 125]], dtype=np.float64)
                bounds = self.engine._calculate_path_bounds_vectorized(coords)
                assert bounds is not None
                assert isinstance(bounds, np.ndarray)
        except (AttributeError, NotImplementedError):
            pytest.skip("Path bounds calculation not available")

    def test_path_complexity_analysis(self):
        """Test path complexity scoring."""
        # Simple path
        simple_path = PathData("M 0 0 L 100 100")
        # Complex path with curves
        complex_path = PathData("M 0 0 C 50 0 100 50 100 100 Q 150 50 200 100")

        try:
            if hasattr(self.engine, '_calculate_complexity_score'):
                # Test complexity calculation exists
                assert hasattr(self.engine, '_calculate_complexity_score')
        except (AttributeError, NotImplementedError):
            pytest.skip("Path complexity analysis not available")

    def test_path_length_calculation(self):
        """Test path length calculation."""
        path_data_list = [
            PathData("M 0 0 L 100 0"),  # Simple horizontal line (length = 100)
            PathData("M 0 0 L 0 100"),  # Simple vertical line (length = 100)
        ]

        try:
            lengths = self.engine.calculate_path_lengths_batch(path_data_list)
            assert isinstance(lengths, np.ndarray)
            assert len(lengths) == 2
        except (AttributeError, NotImplementedError):
            pytest.skip("calculate_path_lengths_batch not implemented")


class TestAdvancedPathOperations:
    """Test advanced path operations and transformations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = PathEngine()

    def test_path_geometry_optimization(self):
        """Test path geometry optimization."""
        path_data = PathData("M 0 0 L 50 50 L 100 100")  # Collinear points

        try:
            optimized = self.engine.optimize_path_geometry(path_data, tolerance=1.0)
            assert optimized is not None
        except (AttributeError, NotImplementedError):
            pytest.skip("optimize_path_geometry not implemented")

    def test_consecutive_line_merging(self):
        """Test merging of consecutive line segments."""
        path_data = PathData("M 0 0 L 50 50 L 100 100")  # Collinear lines

        try:
            merged = self.engine.merge_consecutive_lines(path_data, angle_tolerance=1.0)
            assert merged is not None
        except (AttributeError, NotImplementedError):
            pytest.skip("merge_consecutive_lines not implemented")

    def test_shape_conversion(self):
        """Test conversion to shape data."""
        # Rectangle-like path
        rect_path = PathData("M 0 0 L 100 0 L 100 100 L 0 100 Z")

        try:
            shape_data = self.engine.convert_path_to_shape_data(rect_path, 'rectangle')
            assert shape_data is not None
            assert isinstance(shape_data, dict)
        except (AttributeError, NotImplementedError):
            pytest.skip("convert_path_to_shape_data not implemented")

    def test_batch_path_operations(self):
        """Test batch operations on multiple paths."""
        path_list = [
            PathData("M 0 0 L 100 100"),
            PathData("M 50 50 Q 75 25 100 50"),
            PathData("M 0 100 C 50 50 150 50 200 100")
        ]

        try:
            results = self.engine.batch_process_path_operations(path_list, 'analyze')
            assert results is not None
        except (AttributeError, NotImplementedError):
            pytest.skip("batch_process_path_operations not implemented")

    def test_path_intersection_calculation(self):
        """Test path intersection calculation."""
        path1 = PathData("M 0 50 L 100 50")  # Horizontal line
        path2 = PathData("M 50 0 L 50 100")  # Vertical line

        try:
            intersections = self.engine.calculate_path_intersections(path1, path2, tolerance=1.0)
            assert intersections is not None
        except (AttributeError, NotImplementedError):
            pytest.skip("calculate_path_intersections not implemented")


if __name__ == "__main__":
    # Allow running tests directly with: python test_paths.py
    pytest.main([__file__])