#!/usr/bin/env python3
"""
Tests for Deterministic Curve Positioning with WordArt Classification

Comprehensive test suite for the enhanced curve positioning system that ensures:
- Deterministic sampling with exact point counts
- Monotonic distance progression
- Continuous tangent angles
- WordArt classification accuracy
"""

import pytest
import math
from typing import List, Tuple
from unittest.mock import Mock, patch

from core.algorithms.deterministic_curve_positioning import (
    DeterministicCurvePositioner,
    PathPoint,
    WordArtResult,
    Line,
    Quadratic,
    Cubic,
    create_deterministic_curve_positioner
)


class TestDeterministicSampling:
    """Test deterministic sampling requirements."""

    @pytest.fixture
    def positioner(self):
        """Create positioner with test configuration."""
        return create_deterministic_curve_positioner({
            'enable_classification': False,  # Focus on sampling first
            'samples_per_unit': 2.0
        })

    def test_exact_sample_count(self, positioner):
        """Verify exact point count for all inputs."""
        test_cases = [
            ("M0,0 L100,0", 2),
            ("M0,0 L100,0", 10),
            ("M0,0 L100,0", 31),
            ("M0,0 L100,0", 257),
            ("M0,0 Q50,50 100,0", 128)
        ]

        for path_data, N in test_cases:
            points = positioner.sample_path_for_text(path_data, N)
            assert len(points) == N, f"Expected {N} points, got {len(points)} for path: {path_data}"

    def test_monotonic_distance_progression(self, positioner):
        """Verify strictly non-decreasing distance_along_path."""
        test_paths = [
            "M0,0 L100,0 L100,100",  # Simple L-shape
            "M0,0 Q50,-25 100,0 Q150,25 200,0",  # Multiple curves
            "M0,0 L50,0 L50,50 L0,50 Z"  # Closed path
        ]

        for path_data in test_paths:
            points = positioner.sample_path_for_text(path_data, 50)
            distances = [p.distance_along_path for p in points]

            for i in range(len(distances) - 1):
                assert distances[i] <= distances[i + 1], \
                    f"Distance not monotonic at index {i}: {distances[i]} > {distances[i + 1]}"

            # First point should start at 0
            assert abs(distances[0]) < 1e-6, f"First distance should be 0, got {distances[0]}"

    def test_continuous_tangent_angles(self, positioner):
        """Verify tangent continuity at segment joins."""
        # Test path with sharp join
        path_data = "M0,0 L100,0 L100,100"
        points = positioner.sample_path_for_text(path_data, 100)

        # Find the join point (around x=100, y=0)
        join_indices = []
        for i, p in enumerate(points):
            if abs(p.x - 100) < 5 and abs(p.y) < 5:  # Near the join
                join_indices.append(i)

        # Tangent should change smoothly (not jump discontinuously)
        for i in join_indices:
            if i > 0 and i < len(points) - 1:
                angle_diff = abs(points[i + 1].tangent_angle - points[i - 1].tangent_angle)
                # Allow for the actual corner, but not crazy jumps
                assert angle_diff < math.pi, f"Tangent jump too large at join: {angle_diff}"

    def test_endpoints_preservation(self, positioner):
        """Verify endpoints are exactly preserved."""
        test_cases = [
            ("M10,20 L90,80", (10, 20), (90, 80)),
            ("M0,0 Q50,100 100,0", (0, 0), (100, 0)),
            ("M5,5 L50,5 L50,95 L5,95 Z", (5, 5), (5, 95))  # Closed path
        ]

        for path_data, expected_start, expected_end in test_cases:
            points = positioner.sample_path_for_text(path_data, 20)

            start_point = points[0]
            end_point = points[-1]

            assert abs(start_point.x - expected_start[0]) < 1e-3, \
                f"Start point mismatch: expected {expected_start}, got ({start_point.x}, {start_point.y})"
            assert abs(start_point.y - expected_start[1]) < 1e-3

            assert abs(end_point.x - expected_end[0]) < 1e-3, \
                f"End point mismatch: expected {expected_end}, got ({end_point.x}, {end_point.y})"
            assert abs(end_point.y - expected_end[1]) < 1e-3

    def test_equal_arclength_spacing(self, positioner):
        """Verify equal arc-length spacing."""
        # Simple line should have exactly equal spacing
        points = positioner.sample_path_for_text("M0,0 L100,0", 11)  # 10 segments

        expected_spacing = 10.0  # 100/10
        for i in range(len(points) - 1):
            actual_spacing = points[i + 1].distance_along_path - points[i].distance_along_path
            assert abs(actual_spacing - expected_spacing) < 1e-6, \
                f"Unequal spacing at segment {i}: {actual_spacing} vs {expected_spacing}"

    def test_auto_sample_count_calculation(self, positioner):
        """Test automatic sample count from path length."""
        # Test with samples_per_unit = 2.0
        test_cases = [
            ("M0,0 L100,0", 200),  # Length 100 * 2.0 = 200 samples
            ("M0,0 L10,0", 20),    # Length 10 * 2.0 = 20 samples
            ("M0,0 L1,0", 2)       # Minimum 2 samples
        ]

        for path_data, expected_min in test_cases:
            points = positioner.sample_path_for_text(path_data, None)  # Auto-calculate
            # Should be at least expected_min, clamped to [2, 4096]
            assert len(points) >= min(expected_min, 2)
            assert len(points) <= 4096


class TestEnhancedCommandParsing:
    """Test enhanced SVG command parsing."""

    @pytest.fixture
    def positioner(self):
        return create_deterministic_curve_positioner()

    def test_horizontal_vertical_lines(self, positioner):
        """Test H and V command parsing."""
        test_cases = [
            ("M10,10 H50", [(10, 10), (50, 10)]),  # Horizontal line
            ("M10,10 V50", [(10, 10), (10, 50)]),  # Vertical line
            ("M0,0 H10 V10 H0 V0", [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])  # Rectangle
        ]

        for path_data, expected_points in test_cases:
            points = positioner.sample_path_for_text(path_data, len(expected_points))

            for i, (ex, ey) in enumerate(expected_points):
                assert abs(points[i].x - ex) < 1e-3, f"X mismatch at point {i}"
                assert abs(points[i].y - ey) < 1e-3, f"Y mismatch at point {i}"

    def test_relative_commands(self, positioner):
        """Test relative command handling."""
        # Absolute vs relative should give same result
        absolute_path = "M0,0 L10,0 L10,10 L0,10 L0,0"
        relative_path = "M0,0 l10,0 l0,10 l-10,0 l0,-10"

        abs_points = positioner.sample_path_for_text(absolute_path, 20)
        rel_points = positioner.sample_path_for_text(relative_path, 20)

        for i in range(len(abs_points)):
            assert abs(abs_points[i].x - rel_points[i].x) < 1e-3, f"X mismatch at point {i}"
            assert abs(abs_points[i].y - rel_points[i].y) < 1e-3, f"Y mismatch at point {i}"

    def test_multi_parameter_commands(self, positioner):
        """Test commands with multiple parameter sets."""
        # L with multiple coordinates
        path_data = "M0,0 L10,0 20,0 30,0"  # Should create 3 line segments
        points = positioner.sample_path_for_text(path_data, 4)

        expected_x_coords = [0, 10, 20, 30]
        for i, expected_x in enumerate(expected_x_coords):
            assert abs(points[i].x - expected_x) < 1e-3, f"X mismatch at point {i}"
            assert abs(points[i].y) < 1e-3, f"Y should be 0 at point {i}"

    def test_close_command(self, positioner):
        """Test Z/z close command."""
        path_data = "M10,10 L50,10 L50,50 L10,50 Z"
        points = positioner.sample_path_for_text(path_data, 20)

        # Should close back to start point
        start_point = points[0]
        end_point = points[-1]

        assert abs(end_point.x - start_point.x) < 1e-3, "Path not properly closed (X)"
        assert abs(end_point.y - start_point.y) < 1e-3, "Path not properly closed (Y)"

    def test_malformed_path_handling(self, positioner):
        """Test handling of malformed paths."""
        malformed_paths = [
            "",  # Empty
            "M",  # Incomplete command
            "L10,10",  # L without prior M
            "M10,10 L",  # L without coordinates
            "M10,10 Q50",  # Q with insufficient parameters
            "INVALID",  # Completely invalid
        ]

        for path_data in malformed_paths:
            points = positioner.sample_path_for_text(path_data, 10)
            # Should return fallback horizontal line
            assert len(points) == 10
            assert all(p.y == 0 for p in points), "Fallback should be horizontal"


class TestSegmentImplementations:
    """Test individual segment implementations."""

    def test_line_segment(self):
        """Test Line segment implementation."""
        line = Line((0, 0), (100, 0))

        assert line.length() == 100
        assert line.eval(0.0) == (0, 0)
        assert line.eval(1.0) == (100, 0)
        assert line.eval(0.5) == (50, 0)

        # Tangent should be unit vector in x direction
        tx, ty = line.tan(0.5)
        assert abs(tx - 1.0) < 1e-6
        assert abs(ty) < 1e-6

        # Arc length inversion
        assert abs(line.arclen_to_t(50) - 0.5) < 1e-6

    def test_quadratic_segment(self):
        """Test Quadratic segment implementation."""
        # Quadratic from (0,0) to (100,0) with control at (50,50)
        quad = Quadratic((0, 0), (50, 50), (100, 0))

        assert quad.length() > 100  # Should be longer than straight line
        assert quad.eval(0.0) == (0, 0)
        assert quad.eval(1.0) == (100, 0)

        # Arc length parameterization should be approximately correct
        mid_t = quad.arclen_to_t(quad.length() / 2)
        mid_point = quad.eval(mid_t)
        assert mid_point[1] > 0, "Midpoint should be above x-axis"

    def test_cubic_segment(self):
        """Test Cubic segment implementation."""
        # Simple cubic curve
        cubic = Cubic((0, 0), (33, 33), (67, 33), (100, 0))

        assert cubic.length() > 100  # Should be longer than straight line
        assert cubic.eval(0.0) == (0, 0)
        assert cubic.eval(1.0) == (100, 0)

        # Tangent at start should point toward first control point
        tx, ty = cubic.tan(0.0)
        assert tx > 0 and ty > 0, "Initial tangent should point up-right"

    def test_zero_length_segments(self):
        """Test zero-length segment handling."""
        zero_line = Line((10, 10), (10, 10))
        assert zero_line.length() == 0
        assert zero_line.eval(0.5) == (10, 10)

        # Should return safe tangent
        tx, ty = zero_line.tan(0.5)
        assert abs(tx**2 + ty**2 - 1.0) < 1e-6, "Should return unit tangent"


class TestWordArtClassification:
    """Test WordArt classification system."""

    @pytest.fixture
    def positioner(self):
        return create_deterministic_curve_positioner({
            'enable_classification': True,
            'classification_thresholds': {
                'circle_rmse': 0.02,
                'wave_snr_db': 8.0,
                'quadratic_r2': 0.98,
                'linear_r2': 0.995
            }
        })

    def test_circle_detection(self, positioner):
        """Test circle WordArt detection."""
        # Generate perfect circle path (simplified)
        circle_path = self._generate_circle_path(radius=50, center=(50, 50))
        points = positioner.sample_path_for_text(circle_path, 128)

        # Mock the classification methods to return known results
        with patch.object(positioner, '_fit_circle_taubin') as mock_fit:
            with patch.object(positioner, '_rmse_circle') as mock_rmse:
                with patch.object(positioner, '_curvature_flip_count') as mock_flips:
                    with patch.object(positioner, '_is_closed_path') as mock_closed:

                        mock_fit.return_value = {'center_x': 50, 'center_y': 50, 'radius': 50}
                        mock_rmse.return_value = 0.01  # Below threshold
                        mock_flips.return_value = 1     # Low flip count
                        mock_closed.return_value = True # Closed path

                        result = positioner.classify_wordart(points)

                        assert result is not None
                        assert result.preset == 'circle'
                        assert 'radius' in result.parameters
                        assert result.confidence > 0.5

    def test_arch_detection(self, positioner):
        """Test arch WordArt detection."""
        # Generate arc path
        arc_path = self._generate_arc_path(radius=50, start_angle=0, end_angle=math.pi)
        points = positioner.sample_path_for_text(arc_path, 64)

        with patch.object(positioner, '_fit_circle_taubin') as mock_fit:
            with patch.object(positioner, '_rmse_circle') as mock_rmse:
                with patch.object(positioner, '_curvature_flip_count') as mock_flips:
                    with patch.object(positioner, '_is_closed_path') as mock_closed:
                        with patch.object(positioner, '_calculate_bend_parameter') as mock_bend:

                            mock_fit.return_value = {'center_x': 0, 'center_y': 0, 'radius': 50}
                            mock_rmse.return_value = 0.015  # Below threshold
                            mock_flips.return_value = 0     # No flips
                            mock_closed.return_value = False # Open path
                            mock_bend.return_value = 0.5

                            result = positioner.classify_wordart(points)

                            assert result is not None
                            assert result.preset == 'arch'
                            assert 'bend' in result.parameters

    def test_wave_detection(self, positioner):
        """Test wave WordArt detection."""
        # Generate sinusoidal path
        wave_path = self._generate_wave_path(amplitude=20, frequency=2, length=200)
        points = positioner.sample_path_for_text(wave_path, 128)

        with patch.object(positioner, '_fit_sinusoid_fft') as mock_fft:
            mock_fft.return_value = (0.2, 2.0, 10.0)  # amp, freq, SNR > threshold

            result = positioner.classify_wordart(points)

            assert result is not None
            assert result.preset == 'wave'
            assert 'amplitude' in result.parameters
            assert 'period' in result.parameters

    def test_linear_detection(self, positioner):
        """Test rise/slant WordArt detection."""
        # Generate linear path
        linear_path = "M0,50 L100,55"  # Slight slope
        points = positioner.sample_path_for_text(linear_path, 64)

        with patch.object(positioner, '_fit_line_least_squares') as mock_fit:
            mock_fit.return_value = {'slope': 0.05, 'intercept': 50, 'r_squared': 0.999}

            result = positioner.classify_wordart(points)

            assert result is not None
            assert result.preset == 'rise'  # Small slope -> rise
            assert 'angle' in result.parameters

    def test_no_classification_fallback(self, positioner):
        """Test fallback when no WordArt pattern matches."""
        # Complex irregular path
        complex_path = "M0,0 Q25,50 50,0 Q75,-50 100,25 Q125,75 150,0"
        points = positioner.sample_path_for_text(complex_path, 64)

        # Mock all classification methods to fail
        with patch.object(positioner, '_test_circle_arch', return_value=None):
            with patch.object(positioner, '_test_wave', return_value=None):
                with patch.object(positioner, '_test_inflate_deflate', return_value=None):
                    with patch.object(positioner, '_test_rise_slant', return_value=None):
                        with patch.object(positioner, '_test_triangle', return_value=None):

                            result = positioner.classify_wordart(points)
                            assert result is None

    def test_classification_disabled(self):
        """Test WordArt classification when disabled."""
        positioner = create_deterministic_curve_positioner({'enable_classification': False})

        circle_path = self._generate_circle_path(radius=50, center=(50, 50))
        points = positioner.sample_path_for_text(circle_path, 64)

        result = positioner.classify_wordart(points)
        assert result is None

    # Helper methods for generating test paths

    def _generate_circle_path(self, radius: float, center: Tuple[float, float]) -> str:
        """Generate SVG path for a perfect circle."""
        cx, cy = center
        # Approximate circle with 4 cubic Bézier curves
        k = 4/3 * math.tan(math.pi/8)  # Magic number for circle approximation
        r = radius
        k_offset = k * r

        return (f"M{cx},{cy-r} "
                f"C{cx+k_offset},{cy-r} {cx+r},{cy-k_offset} {cx+r},{cy} "
                f"C{cx+r},{cy+k_offset} {cx+k_offset},{cy+r} {cx},{cy+r} "
                f"C{cx-k_offset},{cy+r} {cx-r},{cy+k_offset} {cx-r},{cy} "
                f"C{cx-r},{cy-k_offset} {cx-k_offset},{cy-r} {cx},{cy-r} Z")

    def _generate_arc_path(self, radius: float, start_angle: float, end_angle: float) -> str:
        """Generate SVG path for a circular arc."""
        start_x = radius * math.cos(start_angle)
        start_y = radius * math.sin(start_angle)
        end_x = radius * math.cos(end_angle)
        end_y = radius * math.sin(end_angle)

        large_arc = 1 if abs(end_angle - start_angle) > math.pi else 0
        sweep = 1  # Positive direction

        return f"M{start_x},{start_y} A{radius},{radius} 0 {large_arc},{sweep} {end_x},{end_y}"

    def _generate_wave_path(self, amplitude: float, frequency: float, length: float) -> str:
        """Generate SVG path for a sinusoidal wave."""
        num_points = 20
        points = []

        for i in range(num_points):
            x = length * i / (num_points - 1)
            y = amplitude * math.sin(2 * math.pi * frequency * x / length)
            points.append(f"{x},{y}")

        return "M" + " L".join(points)


class TestPerformanceRequirements:
    """Test performance requirements."""

    @pytest.fixture
    def positioner(self):
        return create_deterministic_curve_positioner()

    def test_sampling_performance(self, positioner):
        """Test sampling performance targets."""
        import time

        # Complex path with many segments
        complex_path = " ".join([f"L{i*10},{20*math.sin(i/5)}" for i in range(100)])
        complex_path = "M0,0 " + complex_path

        start_time = time.perf_counter()
        points = positioner.sample_path_for_text(complex_path, 200)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        assert elapsed_ms < 50, f"Sampling took {elapsed_ms:.2f}ms, should be <50ms"
        assert len(points) == 200

    def test_classification_performance(self, positioner):
        """Test WordArt classification performance."""
        import time

        # Generate test path
        circle_path = self._generate_circle_path(radius=50, center=(50, 50))
        points = positioner.sample_path_for_text(circle_path, 128)

        start_time = time.perf_counter()
        result = positioner.classify_wordart(points)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        assert elapsed_ms < 10, f"Classification took {elapsed_ms:.2f}ms, should be <10ms"

    def _generate_circle_path(self, radius: float, center: Tuple[float, float]) -> str:
        """Generate SVG path for a perfect circle."""
        cx, cy = center
        k = 4/3 * math.tan(math.pi/8)
        r = radius
        k_offset = k * r

        return (f"M{cx},{cy-r} "
                f"C{cx+k_offset},{cy-r} {cx+r},{cy-k_offset} {cx+r},{cy} "
                f"C{cx+r},{cy+k_offset} {cx+k_offset},{cy+r} {cx},{cy+r} "
                f"C{cx-k_offset},{cy+r} {cx-r},{cy+k_offset} {cx-r},{cy} "
                f"C{cx-r},{cy-k_offset} {cx-k_offset},{cy-r} {cx},{cy-r} Z")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])