#!/usr/bin/env python3
"""
Comprehensive test suite for NumPy Path Processing Engine.

Tests performance, accuracy, and functionality of the ultra-fast
NumPy-based path system targeting 100-300x speedups.
"""

import pytest
import numpy as np
import time
from src.paths.numpy_paths import (
    PathEngine, PathData, PathCommandType,
    create_path_engine, parse_path, process_path_batch, transform_coordinates
)


class TestPathEngineBasics:
    """Test basic PathEngine functionality."""

    def test_engine_initialization(self):
        """Test PathEngine initialization."""
        engine = PathEngine()

        # Should have pre-compiled patterns
        assert engine._command_pattern is not None
        assert engine._number_pattern is not None
        assert len(engine._command_map) > 0

    def test_simple_path_parsing(self):
        """Test simple path parsing."""
        engine = PathEngine()

        # Test basic moveto and lineto
        result = engine.process_path("M 10 20 L 30 40")

        assert result['commands'] == 2
        assert result['coordinates'] == 4

        path_data = result['path_data']
        commands = path_data.commands

        # Check first command (M 10 20)
        assert commands[0]['type'] == PathCommandType.MOVE_TO
        assert commands[0]['relative'] == 0  # absolute
        assert commands[0]['coord_count'] == 2
        assert np.allclose(commands[0]['coords'][:2], [10, 20])

        # Check second command (L 30 40)
        assert commands[1]['type'] == PathCommandType.LINE_TO
        assert commands[1]['coord_count'] == 2
        assert np.allclose(commands[1]['coords'][:2], [30, 40])

    def test_complex_path_parsing(self):
        """Test complex path with curves."""
        engine = PathEngine()

        path_string = "M 100 200 C 100 100 400 100 400 200 Q 500 100 600 200 Z"
        result = engine.process_path(path_string)

        assert result['commands'] == 4  # M, C, Q, Z
        assert result['coordinates'] > 0

        path_data = result['path_data']
        commands = path_data.commands

        # Check cubic curve command
        cubic_cmd = None
        for cmd in commands:
            if cmd['type'] == PathCommandType.CUBIC_CURVE:
                cubic_cmd = cmd
                break

        assert cubic_cmd is not None
        assert cubic_cmd['coord_count'] == 6

        # Check quadratic curve command
        quad_cmd = None
        for cmd in commands:
            if cmd['type'] == PathCommandType.QUADRATIC:
                quad_cmd = cmd
                break

        assert quad_cmd is not None
        assert quad_cmd['coord_count'] == 4

    def test_relative_vs_absolute_commands(self):
        """Test relative vs absolute command parsing."""
        engine = PathEngine()

        # Test absolute commands
        result1 = engine.process_path("M 10 20 L 30 40")
        commands1 = result1['path_data'].commands
        assert commands1[0]['relative'] == 0  # M is absolute
        assert commands1[1]['relative'] == 0  # L is absolute

        # Test relative commands
        result2 = engine.process_path("m 10 20 l 30 40")
        commands2 = result2['path_data'].commands
        assert commands2[0]['relative'] == 1  # m is relative
        assert commands2[1]['relative'] == 1  # l is relative

    def test_empty_and_invalid_paths(self):
        """Test handling of empty and invalid paths."""
        engine = PathEngine()

        # Empty path
        result = engine.process_path("")
        assert result['commands'] == 0
        assert result['coordinates'] == 0

        # Invalid path
        result = engine.process_path("invalid path data")
        assert result['commands'] == 0

    def test_multiple_coordinate_sets(self):
        """Test commands with multiple coordinate sets."""
        engine = PathEngine()

        # Line command with multiple points
        result = engine.process_path("M 0 0 L 10 10 20 20 30 30")

        # Should create multiple line commands
        commands = result['path_data'].commands
        line_commands = [cmd for cmd in commands if cmd['type'] == PathCommandType.LINE_TO]
        assert len(line_commands) == 3  # Three L commands


class TestPathData:
    """Test PathData functionality."""

    def test_pathdata_creation(self):
        """Test PathData creation."""
        # Empty path
        path_data = PathData()
        assert path_data.command_count == 0
        assert path_data.coordinate_count == 0

        # Path from string
        path_data = PathData("M 10 20 L 30 40")
        assert path_data.command_count == 2
        assert path_data.coordinate_count == 4

    def test_pathdata_properties(self):
        """Test PathData properties."""
        path_data = PathData("M 100 200 C 100 100 400 100 400 200")

        assert path_data.command_count == 2  # M and C
        assert path_data.coordinate_count == 8  # 2 + 6 coordinates

        commands = path_data.commands
        assert len(commands) == 2


class TestCoordinateTransformations:
    """Test coordinate transformation functionality."""

    def test_simple_coordinate_transformation(self):
        """Test simple coordinate transformation."""
        engine = PathEngine()

        # Identity transform should not change coordinates
        identity = np.eye(3, dtype=np.float64)
        result = engine.process_path("M 10 20 L 30 40", transform_matrix=identity)

        commands = result['path_data'].commands
        assert np.allclose(commands[0]['coords'][:2], [10, 20])
        assert np.allclose(commands[1]['coords'][:2], [30, 40])

    def test_scaling_transformation(self):
        """Test scaling transformation."""
        engine = PathEngine()

        # 2x scaling transform
        scale_matrix = np.array([
            [2, 0, 0],
            [0, 2, 0],
            [0, 0, 1]
        ], dtype=np.float64)

        result = engine.process_path("M 10 20 L 30 40", transform_matrix=scale_matrix)

        commands = result['path_data'].commands
        assert np.allclose(commands[0]['coords'][:2], [20, 40])  # 10*2, 20*2
        assert np.allclose(commands[1]['coords'][:2], [60, 80])  # 30*2, 40*2

    def test_viewport_transformation(self):
        """Test viewport transformation."""
        engine = PathEngine()

        # Transform from 100x100 viewport to 200x200 target
        result = engine.process_path(
            "M 0 0 L 100 100",
            viewport=(0, 0, 100, 100),
            target_size=(200, 200)
        )

        commands = result['path_data'].commands
        # Should scale by 2x
        assert np.allclose(commands[0]['coords'][:2], [0, 0])
        assert np.allclose(commands[1]['coords'][:2], [200, 200])

    def test_combined_transformations(self):
        """Test combining viewport and matrix transformations."""
        engine = PathEngine()

        # Translation matrix
        translate_matrix = np.array([
            [1, 0, 10],
            [0, 1, 20],
            [0, 0, 1]
        ], dtype=np.float64)

        result = engine.process_path(
            "M 0 0 L 50 50",
            transform_matrix=translate_matrix,
            viewport=(0, 0, 100, 100),
            target_size=(200, 200)
        )

        # Should apply viewport scaling then translation
        assert result['transformed'] is True


class TestBezierCurveProcessing:
    """Test Bezier curve processing functionality."""

    def test_cubic_bezier_extraction(self):
        """Test cubic Bezier curve extraction."""
        engine = PathEngine()

        path_data = PathData("M 0 0 C 50 0 100 50 100 100")
        bezier_data = engine.extract_bezier_curves(path_data)

        assert 'cubic_curves' in bezier_data
        assert len(bezier_data['cubic_curves']) == 1

        # Check control points
        control_points = bezier_data['cubic_curves'][0]
        assert control_points.shape == (4, 2)  # 4 control points with x,y

    def test_quadratic_bezier_extraction(self):
        """Test quadratic Bezier curve extraction."""
        engine = PathEngine()

        path_data = PathData("M 0 0 Q 50 0 100 50")
        bezier_data = engine.extract_bezier_curves(path_data)

        assert 'quadratic_curves' in bezier_data
        assert len(bezier_data['quadratic_curves']) == 1

        # Check control points
        control_points = bezier_data['quadratic_curves'][0]
        assert control_points.shape == (3, 2)  # 3 control points with x,y

    def test_bezier_curve_evaluation(self):
        """Test Bezier curve evaluation."""
        engine = PathEngine()

        path_data = PathData("M 0 0 C 0 100 100 100 100 0")
        bezier_data = engine.extract_bezier_curves(path_data, subdivision=11)

        assert 'cubic_evaluated' in bezier_data
        evaluated_curves = bezier_data['cubic_evaluated']

        # Should have 11 points per curve (subdivision=11)
        assert evaluated_curves.shape == (1, 11, 2)

        # Check start and end points
        start_point = evaluated_curves[0, 0]
        end_point = evaluated_curves[0, -1]

        assert np.allclose(start_point, [0, 0])
        assert np.allclose(end_point, [100, 0])

    def test_mixed_curve_types(self):
        """Test paths with mixed curve types."""
        engine = PathEngine()

        path_data = PathData("M 0 0 C 50 0 100 50 100 100 Q 150 50 200 100")
        bezier_data = engine.extract_bezier_curves(path_data)

        assert 'cubic_curves' in bezier_data
        assert 'quadratic_curves' in bezier_data
        assert len(bezier_data['cubic_curves']) == 1
        assert len(bezier_data['quadratic_curves']) == 1


class TestBatchProcessing:
    """Test batch processing functionality."""

    def test_batch_path_processing(self):
        """Test batch path processing."""
        engine = PathEngine()

        paths = [
            "M 10 10 L 90 90",
            "M 0 0 Q 50 0 100 50",
            "M 100 200 C 100 100 400 100 400 200"
        ]

        results = engine.process_batch(paths)

        assert len(results) == 3
        assert all('commands' in result for result in results)
        assert all(result['commands'] > 0 for result in results)

    def test_batch_with_transformations(self):
        """Test batch processing with transformations."""
        engine = PathEngine()

        paths = ["M 0 0 L 100 100", "M 50 50 L 150 150"]

        scale_matrix = np.array([
            [2, 0, 0],
            [0, 2, 0],
            [0, 0, 1]
        ], dtype=np.float64)

        results = engine.process_batch(paths, transform_matrix=scale_matrix)

        assert len(results) == 2
        assert all(result['transformed'] for result in results)

    def test_empty_batch_handling(self):
        """Test handling of empty batch."""
        engine = PathEngine()

        results = engine.process_batch([])
        assert results == []


class TestPerformanceBenchmarks:
    """Performance tests for NumPy path system."""

    def test_path_parsing_performance(self):
        """Benchmark path parsing performance."""
        engine = PathEngine()

        # Create test paths
        test_paths = [
            "M 100 200 C 100 100 400 100 400 200",
            "M 10 80 Q 95 10 180 80 T 340 80",
            "M 50 50 A 25 25 0 1 1 50 49 Z"
        ] * 1000  # 3000 paths

        # Warmup
        for _ in range(10):
            engine.process_path(test_paths[0])

        # Benchmark
        start_time = time.time()
        results = engine.process_batch(test_paths)
        parsing_time = time.time() - start_time

        print(f"Path parsing: {len(test_paths)} paths in {parsing_time:.4f}s")
        rate = len(test_paths) / parsing_time
        print(f"Parsing rate: {rate:,.0f} paths/sec")

        # Should be much faster than legacy
        assert rate > 50000  # Target: 50k+ paths/sec
        assert len(results) == len(test_paths)

    def test_coordinate_transformation_performance(self):
        """Benchmark coordinate transformation performance."""
        engine = PathEngine()

        # Create complex path with many coordinates
        coords_per_curve = 6  # Cubic curve has 6 coordinates
        n_curves = 1000
        path_parts = ["M 0 0"]

        for i in range(n_curves):
            x1, y1 = i * 10, i * 5
            x2, y2 = i * 10 + 5, i * 5 + 10
            x3, y3 = i * 10 + 10, i * 5
            path_parts.append(f"C {x1} {y1} {x2} {y2} {x3} {y3}")

        complex_path = " ".join(path_parts)

        # Create transformation matrix
        transform = np.array([
            [1.5, 0, 100],
            [0, 1.5, 200],
            [0, 0, 1]
        ], dtype=np.float64)

        # Benchmark transformation
        start_time = time.time()
        result = engine.process_path(complex_path, transform_matrix=transform)
        transform_time = time.time() - start_time

        print(f"Coordinate transformation: {result['coordinates']} coords in {transform_time:.4f}s")
        rate = result['coordinates'] / transform_time
        print(f"Transform rate: {rate:,.0f} coords/sec")

        # Should be very fast
        assert rate > 100000  # Target: 100k+ coords/sec

    def test_bezier_evaluation_performance(self):
        """Benchmark Bezier curve evaluation performance."""
        engine = PathEngine()

        # Create path with many Bezier curves
        n_curves = 500
        path_parts = ["M 0 0"]

        for i in range(n_curves):
            x1, y1 = i * 20, i * 10
            x2, y2 = i * 20 + 10, i * 10 + 20
            x3, y3 = i * 20 + 20, i * 10
            path_parts.append(f"C {x1} {y1} {x2} {y2} {x3} {y3}")

        bezier_path = " ".join(path_parts)
        path_data = PathData(bezier_path)

        # Benchmark Bezier evaluation
        start_time = time.time()
        bezier_data = engine.extract_bezier_curves(path_data, subdivision=20)
        bezier_time = time.time() - start_time

        if 'cubic_curves' in bezier_data:
            n_evaluated = len(bezier_data['cubic_curves'])
            print(f"Bezier evaluation: {n_evaluated} curves in {bezier_time:.4f}s")
            rate = n_evaluated / bezier_time
            print(f"Bezier rate: {rate:,.0f} curves/sec")

            # Should be very fast
            assert rate > 10000  # Target: 10k+ curves/sec


class TestFactoryFunctions:
    """Test factory and convenience functions."""

    def test_create_path_engine(self):
        """Test path engine factory function."""
        engine = create_path_engine()
        assert isinstance(engine, PathEngine)

    def test_parse_path_function(self):
        """Test parse_path convenience function."""
        path_data = parse_path("M 10 20 L 30 40")
        assert isinstance(path_data, PathData)
        assert path_data.command_count == 2

    def test_process_path_batch_function(self):
        """Test process_path_batch convenience function."""
        paths = ["M 0 0 L 100 100", "M 50 50 Q 75 25 100 50"]
        results = process_path_batch(paths)

        assert len(results) == 2
        assert all('path_data' in result for result in results)

    def test_transform_coordinates_function(self):
        """Test transform_coordinates convenience function."""
        coords = np.array([[10, 20], [30, 40]], dtype=np.float64)
        scale_matrix = np.array([
            [2, 0, 0],
            [0, 2, 0],
            [0, 0, 1]
        ], dtype=np.float64)

        transformed = transform_coordinates(coords, scale_matrix)

        assert np.allclose(transformed, [[20, 40], [60, 80]])


class TestCachePerformance:
    """Test caching system performance."""

    def test_parsing_cache_effectiveness(self):
        """Test that parsing results are cached effectively."""
        engine = PathEngine()

        path_string = "M 100 200 C 100 100 400 100 400 200"

        # First parse (cache miss)
        initial_stats = engine.cache_stats
        result1 = engine.process_path(path_string)

        # Second parse (cache hit)
        result2 = engine.process_path(path_string)

        final_stats = engine.cache_stats
        assert final_stats['hits'] > initial_stats['hits']

        # Results should be identical
        assert result1['commands'] == result2['commands']
        assert result1['coordinates'] == result2['coordinates']

    def test_cache_hit_rate(self):
        """Test cache hit rate with repeated parsing."""
        engine = PathEngine()

        paths = [
            "M 10 20 L 30 40",
            "M 0 0 Q 50 0 100 50"
        ] * 100  # Repeat paths multiple times

        # Process all paths
        for path in paths:
            engine.process_path(path)

        stats = engine.cache_stats
        # Should have high hit rate due to repetition
        assert stats['hit_rate'] > 0.8


class TestAccuracyValidation:
    """Test numerical accuracy and edge cases."""

    def test_floating_point_precision(self):
        """Test floating point precision in parsing."""
        engine = PathEngine()

        # Test various floating point formats
        test_values = [
            "M 0.123 456.789",
            "M 1e-3 2.5e2",
            "M -123.456 +789.012"
        ]

        for path_string in test_values:
            result = engine.process_path(path_string)
            assert result['commands'] > 0

    def test_extreme_coordinate_values(self):
        """Test handling of extreme coordinate values."""
        engine = PathEngine()

        # Very large coordinates
        result1 = engine.process_path("M 1000000 2000000 L 3000000 4000000")
        assert result1['commands'] == 2

        # Very small coordinates
        result2 = engine.process_path("M 0.001 0.002 L 0.003 0.004")
        assert result2['commands'] == 2

        # Negative coordinates
        result3 = engine.process_path("M -100 -200 L -300 -400")
        assert result3['commands'] == 2

    def test_transformation_accuracy(self):
        """Test transformation accuracy."""
        engine = PathEngine()

        # Test transformation with known result
        path_string = "M 1 1 L 2 2"
        scale_2x = np.array([
            [2, 0, 0],
            [0, 2, 0],
            [0, 0, 1]
        ], dtype=np.float64)

        result = engine.process_path(path_string, transform_matrix=scale_2x)
        commands = result['path_data'].commands

        # Check precision
        assert np.allclose(commands[0]['coords'][:2], [2, 2], rtol=1e-10)
        assert np.allclose(commands[1]['coords'][:2], [4, 4], rtol=1e-10)


class TestAdvancedBezierCalculations:
    """Test advanced vectorized Bezier calculation capabilities."""

    def setup_method(self):
        """Set up test engine."""
        self.engine = PathEngine()

    def test_batch_bezier_evaluation(self):
        """Test batch evaluation of multiple Bezier curves."""
        # Create test control points for 3 cubic curves
        control_points = np.array([
            [[0, 0], [10, 30], [30, 30], [40, 0]],  # First curve
            [[40, 0], [50, -20], [70, -20], [80, 0]],  # Second curve
            [[0, 50], [20, 80], [60, 80], [80, 50]]   # Third curve
        ])

        # Evaluate batch
        results = self.engine.evaluate_bezier_batch(control_points, subdivision=10)

        # Check dimensions
        assert results.shape == (3, 10, 2)  # 3 curves, 10 points each, 2D

        # Check start and end points
        np.testing.assert_array_almost_equal(results[0, 0], [0, 0])   # First curve start
        np.testing.assert_array_almost_equal(results[0, -1], [40, 0])  # First curve end
        np.testing.assert_array_almost_equal(results[1, 0], [40, 0])   # Second curve start
        np.testing.assert_array_almost_equal(results[1, -1], [80, 0])  # Second curve end

    def test_bezier_subdivision(self):
        """Test Bezier curve subdivision using De Casteljau's algorithm."""
        # Create test control points
        control_points = np.array([
            [[0, 0], [10, 20], [30, 20], [40, 0]],
            [[40, 0], [50, -10], [70, -10], [80, 0]]
        ])

        # Subdivision parameters
        t_values = np.array([0.5, 0.3])  # Split first curve at t=0.5, second at t=0.3

        # Perform subdivision
        subdivided = self.engine.subdivide_bezier_curves(control_points, t_values)

        # Check dimensions: 2 curves, each split into 2 parts, each with 4 control points
        assert subdivided.shape == (2, 2, 4, 2)

        # Verify continuity - end of left curve should match start of right curve
        np.testing.assert_array_almost_equal(
            subdivided[0, 0, 3],  # End of left part of first curve
            subdivided[0, 1, 0]   # Start of right part of first curve
        )

    def test_arc_to_bezier_conversion(self):
        """Test conversion of elliptical arcs to cubic Bezier curves."""
        # Test arc parameters
        center = np.array([50, 50])
        radii = np.array([30, 20])
        rotation = np.pi / 6  # 30 degrees
        start_angle = 0
        sweep_angle = np.pi / 2  # 90 degrees

        # Convert arc to Bezier
        bezier_curves = self.engine.convert_arc_to_bezier(
            center, radii, rotation, start_angle, sweep_angle
        )

        # Should return array of control points
        assert bezier_curves.ndim == 3  # (n_segments, 4, 2)
        assert bezier_curves.shape[1] == 4  # 4 control points per curve
        assert bezier_curves.shape[2] == 2  # 2D coordinates

    def test_bezier_curve_optimization(self):
        """Test optimization of Bezier curves by removing redundant control points."""
        # Create curves with some that are essentially lines
        control_points = np.array([
            [[0, 0], [10, 5], [20, 10], [30, 15]],    # Nearly linear
            [[0, 0], [10, 30], [30, 30], [40, 0]],    # Proper curve
            [[50, 50], [50.001, 50.001], [50.002, 50.002], [50.003, 50.003]]  # Degenerate
        ])

        # Optimize curves
        optimized = self.engine.optimize_bezier_curves(control_points, tolerance=1e-2)

        # Should return same number of curves
        assert optimized.shape[0] == 3

        # Linear curves should be converted to line representation
        # (start = p0, control points = start/end, end = p3)
        assert (np.allclose(optimized[0, 1], optimized[0, 0]) or
               np.allclose(optimized[0, 1], optimized[0, 3]))

    def test_quadratic_to_cubic_conversion(self):
        """Test accurate conversion of quadratic Bezier to cubic."""
        # Test path with quadratic curve
        path_string = "M 0 0 Q 50 100 100 0"
        result = self.engine.process_path(path_string)

        # Extract Bezier curves
        bezier_data = self.engine.extract_bezier_curves(result['path_data'])

        # Should have converted quadratic curves
        if 'quadratic_curves' in bezier_data:
            assert 'quadratic_as_cubic' in bezier_data
            assert 'quadratic_evaluated' in bezier_data

            # Cubic conversion should preserve start and end points
            original_quad = bezier_data['quadratic_curves'][0]
            converted_cubic = bezier_data['quadratic_as_cubic'][0]

            np.testing.assert_array_almost_equal(original_quad[0], converted_cubic[0])  # Start
            np.testing.assert_array_almost_equal(original_quad[2], converted_cubic[3])  # End

    def test_complex_path_bezier_extraction(self):
        """Test Bezier extraction from complex path with multiple curve types."""
        # Complex path with cubic and quadratic commands
        path_string = "M 10 10 C 20 0 40 0 50 10 Q 60 20 70 10"
        result = self.engine.process_path(path_string)

        # Extract all Bezier curves
        bezier_data = self.engine.extract_bezier_curves(result['path_data'], subdivision=15)

        # Should have performance metrics
        assert 'performance' in bezier_data
        perf = bezier_data['performance']
        assert 'total_curves' in perf
        assert 'subdivision_points' in perf
        assert perf['subdivision_points'] == 15

        # Should have processed multiple curve types
        curve_types_found = 0
        if 'cubic_curves' in bezier_data:
            curve_types_found += 1
        if 'quadratic_curves' in bezier_data:
            curve_types_found += 1

        assert curve_types_found >= 1

    def test_bezier_batch_performance(self):
        """Test performance characteristics of batch Bezier operations."""
        # Create batch of curves for performance testing
        n_curves = 50  # Reduced for test efficiency
        control_points = np.random.rand(n_curves, 4, 2) * 100

        # Time batch evaluation
        import time
        start_time = time.time()
        results = self.engine.evaluate_bezier_batch(control_points, subdivision=20)
        batch_time = time.time() - start_time

        # Time individual evaluations for comparison
        start_time = time.time()
        t_values = np.linspace(0, 1, 20)
        individual_results = []
        for i in range(n_curves):
            curve_result = self.engine._evaluate_cubic_bezier(
                control_points[i, 0], control_points[i, 1],
                control_points[i, 2], control_points[i, 3], t_values
            )
            individual_results.append(curve_result)
        individual_time = time.time() - start_time

        # Batch should be competitive (allow 3x overhead for setup)
        assert batch_time < individual_time * 3.0

        # Results should be equivalent
        individual_array = np.array(individual_results)
        np.testing.assert_array_almost_equal(results, individual_array, decimal=10)

    def test_vectorized_bezier_accuracy(self):
        """Test accuracy of vectorized Bezier calculations against reference."""
        # Reference cubic Bezier curve
        p0 = np.array([0, 0])
        p1 = np.array([0, 100])
        p2 = np.array([100, 100])
        p3 = np.array([100, 0])

        t_values = np.linspace(0, 1, 11)

        # Single curve evaluation
        single_result = self.engine._evaluate_cubic_bezier(p0, p1, p2, p3, t_values)

        # Batch evaluation with single curve
        control_points_batch = np.array([[p0, p1, p2, p3]])
        batch_result = self.engine._evaluate_cubic_bezier_batch(control_points_batch, t_values)

        # Should be identical
        np.testing.assert_array_almost_equal(single_result, batch_result[0], decimal=12)

    def test_arc_bezier_approximation_accuracy(self):
        """Test accuracy of arc-to-Bezier approximation."""
        # Test quarter circle
        center = np.array([0, 0])
        radii = np.array([100, 100])
        rotation = 0
        start_angle = 0
        sweep_angle = np.pi / 2

        bezier_segments = self.engine.convert_arc_to_bezier(
            center, radii, rotation, start_angle, sweep_angle
        )

        # For quarter circle, should get one segment
        assert bezier_segments.shape[0] >= 1

        # Check start point is on circle
        start_point = bezier_segments[0, 0]
        assert np.allclose(np.linalg.norm(start_point - center), 100, rtol=1e-10)

        # Check end point is on circle
        end_point = bezier_segments[-1, 3]
        assert np.allclose(np.linalg.norm(end_point - center), 100, rtol=1e-10)


class TestPathTransformationAndOptimization:
    """Test advanced path transformation and optimization features."""

    def setup_method(self):
        """Set up test engine."""
        self.engine = PathEngine()

    def test_path_geometry_optimization(self):
        """Test path geometry optimization by removing redundant elements."""
        # Create path with redundant zero-length lines and near-linear curves
        path_string = "M 0 0 L 0 0 L 10 10 C 10 10.01 19.99 19.99 20 20 L 30 30"
        result = self.engine.process_path(path_string)

        # Optimize the path
        optimized_path = self.engine.optimize_path_geometry(result['path_data'], tolerance=1e-1)

        # Should have fewer commands after optimization
        original_commands = len(result['path_data'].commands)
        optimized_commands = len(optimized_path.commands)

        assert optimized_commands <= original_commands
        print(f"Optimization: {original_commands} → {optimized_commands} commands")

    def test_viewport_transformation(self):
        """Test viewport transformation scaling."""
        # Create simple path
        path_string = "M 10 10 L 90 90"
        result = self.engine.process_path(path_string)

        # Transform from (0,0,100,100) to (0,0,200,200) - 2x scale
        source_viewport = (0, 0, 100, 100)
        target_viewport = (0, 0, 200, 200)

        transformed_path = self.engine.apply_viewport_transformation(
            result['path_data'], source_viewport, target_viewport
        )

        # Check that coordinates are scaled by 2
        commands = transformed_path.commands
        move_coords = commands[0]['coords'][:2]
        line_coords = commands[1]['coords'][:2]

        np.testing.assert_array_almost_equal(move_coords, [20, 20])  # 10*2
        np.testing.assert_array_almost_equal(line_coords, [180, 180])  # 90*2

    def test_path_metrics_calculation(self):
        """Test comprehensive path metrics calculation."""
        # Complex path with various command types
        path_string = "M 0 0 L 100 0 C 100 50 150 50 200 0 Q 250 100 300 0 Z"
        result = self.engine.process_path(path_string)

        # Calculate metrics
        metrics = self.engine.calculate_path_metrics(result['path_data'])

        # Check required metrics
        assert 'total_commands' in metrics
        assert 'command_breakdown' in metrics
        assert 'total_coordinates' in metrics
        assert 'bounding_box' in metrics
        assert 'estimated_length' in metrics
        assert 'complexity_score' in metrics

        # Verify command breakdown
        breakdown = metrics['command_breakdown']
        assert breakdown['move_to'] >= 1
        assert breakdown['line_to'] >= 1
        assert breakdown['cubic_curve'] >= 1
        assert breakdown['quadratic'] >= 1
        assert breakdown['close'] >= 1

        # Verify bounding box
        bbox = metrics['bounding_box']
        assert bbox['width'] > 0
        assert bbox['height'] >= 0

    def test_consecutive_line_merging(self):
        """Test merging of consecutive collinear line segments."""
        # Path with many small collinear segments
        path_string = "M 0 0 L 10 10 L 20 20 L 30 30 L 40 40"
        result = self.engine.process_path(path_string)

        # Merge consecutive lines
        merged_path = self.engine.merge_consecutive_lines(
            result['path_data'], angle_tolerance=0.1
        )

        # Should have fewer line commands after merging
        original_lines = sum(1 for cmd in result['path_data'].commands
                           if cmd['type'] == PathCommandType.LINE_TO)
        merged_lines = sum(1 for cmd in merged_path.commands
                         if cmd['type'] == PathCommandType.LINE_TO)

        assert merged_lines <= original_lines
        print(f"Line merging: {original_lines} → {merged_lines} line commands")

    def test_bounds_calculation_vectorized(self):
        """Test vectorized bounding box calculation."""
        # Create test coordinates
        coords = np.array([
            [10, 20],
            [30, 5],
            [15, 40],
            [25, 15]
        ])

        bounds = self.engine._calculate_path_bounds_vectorized(coords)

        # Verify bounds
        expected = np.array([10, 5, 30, 40])  # min_x, min_y, max_x, max_y
        np.testing.assert_array_equal(bounds, expected)

    def test_complexity_score_calculation(self):
        """Test path complexity score calculation."""
        # Simple path
        simple_stats = {
            'move_to': 1,
            'line_to': 2,
            'cubic_curve': 0,
            'quadratic': 0,
            'arc': 0,
            'close': 0
        }
        simple_score = self.engine._calculate_complexity_score(simple_stats, 6)

        # Complex path
        complex_stats = {
            'move_to': 2,
            'line_to': 5,
            'cubic_curve': 3,
            'quadratic': 2,
            'arc': 1,
            'close': 1
        }
        complex_score = self.engine._calculate_complexity_score(complex_stats, 30)

        # Complex path should have higher score
        assert complex_score > simple_score

    def test_line_sequence_simplification(self):
        """Test Douglas-Peucker-like line sequence simplification."""
        # Zigzag line that can be simplified
        line_points = np.array([
            [0, 0],
            [10, 0.1],   # Nearly on straight line
            [20, -0.1],  # Nearly on straight line
            [30, 0.05],  # Nearly on straight line
            [40, 0]
        ])

        simplified = self.engine._simplify_line_sequence(line_points, angle_tolerance=0.5)

        # Should remove intermediate points that don't contribute significant direction change
        assert len(simplified) <= len(line_points)

        # Should preserve start and end points
        np.testing.assert_array_equal(simplified[0], line_points[0])
        np.testing.assert_array_equal(simplified[-1], line_points[-1])

    def test_transformation_with_viewport_offset(self):
        """Test viewport transformation with translation offset."""
        path_string = "M 0 0 L 50 50"
        result = self.engine.process_path(path_string)

        # Transform with offset
        source_viewport = (0, 0, 100, 100)
        target_viewport = (100, 200, 100, 100)  # Same size, different position

        transformed_path = self.engine.apply_viewport_transformation(
            result['path_data'], source_viewport, target_viewport
        )

        # Check translation
        commands = transformed_path.commands
        move_coords = commands[0]['coords'][:2]
        line_coords = commands[1]['coords'][:2]

        np.testing.assert_array_almost_equal(move_coords, [100, 200])  # 0+100, 0+200
        np.testing.assert_array_almost_equal(line_coords, [150, 250])  # 50+100, 50+200

    def test_optimization_preserves_path_integrity(self):
        """Test that optimization preserves essential path characteristics."""
        # Create path with intentional redundancy
        path_string = "M 100 100 C 100 100 150 150 200 200 L 200 200 L 300 300"
        result = self.engine.process_path(path_string)

        # Calculate metrics before optimization
        original_metrics = self.engine.calculate_path_metrics(result['path_data'])

        # Optimize path
        optimized_path = self.engine.optimize_path_geometry(result['path_data'])
        optimized_metrics = self.engine.calculate_path_metrics(optimized_path)

        # Bounding box should be similar (allowing for minor numerical differences)
        orig_bbox = original_metrics['bounding_box']
        opt_bbox = optimized_metrics['bounding_box']

        assert abs(orig_bbox['width'] - opt_bbox['width']) < 1e-6
        assert abs(orig_bbox['height'] - opt_bbox['height']) < 1e-6

    def test_edge_cases_handling(self):
        """Test handling of edge cases in transformation and optimization."""
        # Empty path
        empty_path = PathData("")
        empty_path.commands = np.array([])

        # Should handle empty paths gracefully
        try:
            optimized_empty = self.engine.optimize_path_geometry(empty_path)
            metrics_empty = self.engine.calculate_path_metrics(empty_path)
            assert True  # No exception thrown
        except Exception as e:
            assert False, f"Failed to handle empty path: {e}"

        # Single point path
        single_point = "M 50 50"
        result = self.engine.process_path(single_point)
        metrics = self.engine.calculate_path_metrics(result['path_data'])

        # Should have valid metrics for single point
        assert metrics['total_commands'] == 1
        assert metrics['bounding_box']['width'] == 0
        assert metrics['bounding_box']['height'] == 0


class TestAdvancedPathOperations:
    """Test advanced path operations including intersections and shape conversions."""

    def setup_method(self):
        """Set up test engine."""
        self.engine = PathEngine()

    def test_path_intersection_calculation(self):
        """Test vectorized path intersection calculations."""
        # Create two intersecting paths - X pattern
        path1_string = "M 0 0 L 100 100"  # Diagonal line
        path2_string = "M 0 100 L 100 0"  # Counter-diagonal line

        result1 = self.engine.process_path(path1_string)
        result2 = self.engine.process_path(path2_string)

        # Calculate intersections
        intersections = self.engine.calculate_path_intersections(
            result1['path_data'], result2['path_data']
        )

        # Should find one intersection at (50, 50)
        assert len(intersections) == 1
        expected_intersection = np.array([50.0, 50.0])
        np.testing.assert_array_almost_equal(intersections[0], expected_intersection, decimal=6)

    def test_parallel_lines_no_intersection(self):
        """Test that parallel lines produce no intersections."""
        path1_string = "M 0 0 L 100 0"    # Horizontal line
        path2_string = "M 0 10 L 100 10"  # Parallel horizontal line

        result1 = self.engine.process_path(path1_string)
        result2 = self.engine.process_path(path2_string)

        intersections = self.engine.calculate_path_intersections(
            result1['path_data'], result2['path_data']
        )

        # No intersections should be found
        assert len(intersections) == 0

    def test_path_to_polygon_conversion(self):
        """Test conversion of path to polygon vertex array."""
        # Square path
        path_string = "M 0 0 L 100 0 L 100 100 L 0 100 Z"
        result = self.engine.process_path(path_string)

        # Convert to polygon
        polygon_data = self.engine.convert_path_to_shape_data(result['path_data'], "polygon")

        # Should have vertices for the square
        assert 'vertices' in polygon_data
        assert 'vertex_count' in polygon_data
        assert polygon_data['vertex_count'] >= 4

        vertices = polygon_data['vertices']
        assert len(vertices) >= 4

        # Check some expected vertices (allowing for different ordering)
        vertex_set = {tuple(v) for v in vertices}
        expected_vertices = {(0, 0), (100, 0), (100, 100), (0, 100)}
        assert expected_vertices.issubset(vertex_set)

    def test_path_to_rectangle_conversion(self):
        """Test conversion of path to rectangle bounds."""
        # Triangle path
        path_string = "M 10 20 L 90 30 L 50 80 Z"
        result = self.engine.process_path(path_string)

        # Convert to rectangle bounds
        rect_data = self.engine.convert_path_to_shape_data(result['path_data'], "rectangle")

        # Check required fields
        assert 'bounds' in rect_data
        assert 'center' in rect_data
        assert 'size' in rect_data

        bounds = rect_data['bounds']
        # Should encompass all triangle vertices
        assert bounds[0] <= 10  # min_x
        assert bounds[1] <= 20  # min_y
        assert bounds[2] >= 90  # max_x
        assert bounds[3] >= 80  # max_y

    def test_path_to_circle_conversion(self):
        """Test conversion of path to circle parameters."""
        # Approximate circle using line segments
        path_string = "M 100 50 L 87 87 L 50 100 L 13 87 L 0 50 L 13 13 L 50 0 L 87 13 Z"
        result = self.engine.process_path(path_string)

        # Convert to circle
        circle_data = self.engine.convert_path_to_shape_data(result['path_data'], "circle")

        # Check required fields
        assert 'center' in circle_data
        assert 'radius' in circle_data
        assert 'fit_error' in circle_data

        center = circle_data['center']
        radius = circle_data['radius']

        # Center should be roughly at (50, 50)
        assert abs(center[0] - 50) < 20
        assert abs(center[1] - 50) < 20

        # Radius should be roughly 50
        assert abs(radius - 50) < 20

    def test_batch_path_operations(self):
        """Test batch processing of multiple path operations."""
        # Create multiple test paths
        paths = [
            "M 0 0 L 100 100",
            "M 10 10 L 90 90 L 50 150",
            "M 20 20 C 40 0 60 0 80 20"
        ]

        path_data_list = []
        for path_string in paths:
            result = self.engine.process_path(path_string)
            path_data_list.append(result['path_data'])

        # Batch process with multiple operations
        operations = ["metrics", "optimize", "convert_polygon"]
        batch_results = self.engine.batch_process_path_operations(path_data_list, operations)

        # Should have results for all paths
        assert len(batch_results) == 3

        # Each path should have results for all operations
        for path_result in batch_results:
            assert 'metrics' in path_result
            assert 'optimized' in path_result
            assert 'shape_polygon' in path_result

    def test_path_similarity_calculation(self):
        """Test calculation of similarity metrics between paths."""
        # Similar paths
        path1_string = "M 0 0 L 100 100 L 200 0"
        path2_string = "M 5 5 L 105 105 L 205 5"  # Slightly translated

        result1 = self.engine.process_path(path1_string)
        result2 = self.engine.process_path(path2_string)

        similarity = self.engine.calculate_path_similarity(
            result1['path_data'], result2['path_data']
        )

        # Check required metrics
        assert 'overall_similarity' in similarity
        assert 'bounding_box_similarity' in similarity
        assert 'structure_similarity' in similarity
        assert 'size_similarity' in similarity

        # Similar paths should have high similarity
        assert similarity['overall_similarity'] > 0.5
        assert similarity['structure_similarity'] > 0.8  # Same structure

    def test_path_union_creation(self):
        """Test creation of path unions."""
        # Create two separate paths
        path1_string = "M 0 0 L 50 50"
        path2_string = "M 100 100 L 150 150"

        result1 = self.engine.process_path(path1_string)
        result2 = self.engine.process_path(path2_string)

        # Create union
        union_path = self.engine.create_path_union([result1['path_data'], result2['path_data']])

        # Union should have commands from both paths
        union_commands = len(union_path.commands)
        path1_commands = len(result1['path_data'].commands)
        path2_commands = len(result2['path_data'].commands)

        assert union_commands == path1_commands + path2_commands

    def test_advanced_transformations(self):
        """Test application of advanced transformation sequences."""
        path_string = "M 10 10 L 20 20"
        result = self.engine.process_path(path_string)

        # Define transformation sequence
        transformations = [
            {"type": "scale", "scale_x": 2.0, "scale_y": 2.0},
            {"type": "rotate", "angle": np.pi / 4},  # 45 degrees
            {"type": "translate", "tx": 100, "ty": 200}
        ]

        # Apply transformations
        transformed_path = self.engine.apply_advanced_transformations(
            result['path_data'], transformations
        )

        # Should have same number of commands
        assert len(transformed_path.commands) == len(result['path_data'].commands)

        # Coordinates should be transformed
        original_coords = result['path_data'].commands[0]['coords'][:2]
        transformed_coords = transformed_path.commands[0]['coords'][:2]

        # Should not be the same after transformation
        assert not np.allclose(original_coords, transformed_coords)

    def test_empty_path_operations(self):
        """Test advanced operations with empty paths."""
        empty_path = PathData("")
        empty_path.commands = np.array([])

        # Should handle empty paths gracefully
        intersections = self.engine.calculate_path_intersections(empty_path, empty_path)
        assert len(intersections) == 0

        polygon_data = self.engine.convert_path_to_shape_data(empty_path, "polygon")
        assert polygon_data['vertex_count'] == 0

        circle_data = self.engine.convert_path_to_shape_data(empty_path, "circle")
        assert circle_data['radius'] == 0.0

    def test_invalid_shape_conversion(self):
        """Test error handling for invalid shape types."""
        path_string = "M 0 0 L 100 100"
        result = self.engine.process_path(path_string)

        # Should raise error for unsupported shape type
        try:
            self.engine.convert_path_to_shape_data(result['path_data'], "invalid_shape")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Unsupported shape type" in str(e)

    def test_complex_intersection_scenario(self):
        """Test intersection calculation with multiple segments."""
        # Create paths with multiple segments
        path1_string = "M 0 50 L 50 50 L 100 50"      # Horizontal line with segments
        path2_string = "M 25 0 L 25 100 M 75 0 L 75 100"  # Two vertical lines

        result1 = self.engine.process_path(path1_string)
        result2 = self.engine.process_path(path2_string)

        intersections = self.engine.calculate_path_intersections(
            result1['path_data'], result2['path_data']
        )

        # Should find two intersections
        assert len(intersections) == 2

        # Sort intersections by x-coordinate for consistent testing
        intersections = intersections[intersections[:, 0].argsort()]

        # Check intersection points
        np.testing.assert_array_almost_equal(intersections[0], [25.0, 50.0], decimal=6)
        np.testing.assert_array_almost_equal(intersections[1], [75.0, 50.0], decimal=6)


if __name__ == "__main__":
    # Run performance benchmarks if executed directly
    print("=== NumPy Path Processing Performance Benchmarks ===")

    test_perf = TestPerformanceBenchmarks()
    test_perf.test_path_parsing_performance()
    test_perf.test_coordinate_transformation_performance()
    test_perf.test_bezier_evaluation_performance()

    print("=== Advanced Bezier Calculation Tests ===")
    test_bezier = TestAdvancedBezierCalculations()
    test_bezier.setup_method()
    test_bezier.test_batch_bezier_evaluation()
    test_bezier.test_bezier_subdivision()
    test_bezier.test_arc_to_bezier_conversion()

    print("=== All benchmarks completed ===")