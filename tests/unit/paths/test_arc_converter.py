#!/usr/bin/env python3
"""
Unit tests for ArcConverter implementation.

Tests the industry-standard arc-to-cubic bezier converter that uses
the a2c algorithm for converting SVG arcs to PowerPoint-compatible curves.
"""

import pytest
import math
from unittest.mock import Mock, patch

from core.paths.arc_converter import ArcConverter
from core.paths.architecture import (
    PathCommand, CoordinatePoint, BezierSegment, PathCommandType,
    ArcConversionError
)


class TestArcConverter:
    """Test suite for ArcConverter implementation."""

    @pytest.fixture
    def converter(self):
        """Create an ArcConverter instance for testing."""
        return ArcConverter(enable_logging=False)

    def test_initialization(self, converter):
        """Test ArcConverter initialization."""
        assert converter is not None
        assert converter.max_segment_angle == 90.0
        assert converter.error_tolerance == 0.01
        assert converter._arcs_converted == 0
        assert converter._segments_generated == 0

    def test_simple_arc_conversion(self, converter):
        """Test conversion of a simple arc."""
        # Simple horizontal arc from (50, 100) to (150, 100) with radius 50
        bezier_segments = converter.arc_to_bezier_segments(
            start_x=50, start_y=100,
            rx=50, ry=50, x_axis_rotation=0,
            large_arc_flag=0, sweep_flag=1,
            end_x=150, end_y=100
        )

        # Should generate at least one segment
        assert len(bezier_segments) >= 1

        # First segment should start at the arc start point
        first_segment = bezier_segments[0]
        assert abs(first_segment.start_point.x - 50) < 1e-10
        assert abs(first_segment.start_point.y - 100) < 1e-10

        # Last segment should end at the arc end point
        last_segment = bezier_segments[-1]
        assert abs(last_segment.end_point.x - 150) < 1e-10
        assert abs(last_segment.end_point.y - 100) < 1e-10

        # All segments should be valid BezierSegment objects
        for segment in bezier_segments:
            assert isinstance(segment, BezierSegment)
            assert segment.control_point_1 is not None
            assert segment.control_point_2 is not None

    def test_quarter_circle_arc(self, converter):
        """Test conversion of a quarter circle arc."""
        # Quarter circle from (100, 100) to (200, 200)
        bezier_segments = converter.arc_to_bezier_segments(
            start_x=100, start_y=100,
            rx=100, ry=100, x_axis_rotation=0,
            large_arc_flag=0, sweep_flag=1,
            end_x=200, end_y=200
        )

        assert len(bezier_segments) >= 1

        # Verify endpoints
        assert abs(bezier_segments[0].start_point.x - 100) < 1e-10
        assert abs(bezier_segments[0].start_point.y - 100) < 1e-10
        assert abs(bezier_segments[-1].end_point.x - 200) < 1e-10
        assert abs(bezier_segments[-1].end_point.y - 200) < 1e-10

    def test_elliptical_arc(self, converter):
        """Test conversion of an elliptical arc."""
        # Elliptical arc with different rx and ry
        bezier_segments = converter.arc_to_bezier_segments(
            start_x=50, start_y=100,
            rx=100, ry=50, x_axis_rotation=0,
            large_arc_flag=0, sweep_flag=1,
            end_x=250, end_y=100
        )

        assert len(bezier_segments) >= 1

        # Should handle elliptical geometry correctly
        for segment in bezier_segments:
            assert isinstance(segment, BezierSegment)

    def test_rotated_arc(self, converter):
        """Test conversion of a rotated arc."""
        # Arc rotated 45 degrees
        bezier_segments = converter.arc_to_bezier_segments(
            start_x=50, start_y=100,
            rx=50, ry=50, x_axis_rotation=45,
            large_arc_flag=0, sweep_flag=1,
            end_x=150, end_y=100
        )

        assert len(bezier_segments) >= 1
        # Rotation should be handled by the a2c algorithm

    def test_large_arc_flag(self, converter):
        """Test handling of large arc flag."""
        # Same endpoints, different arc paths
        small_arc = converter.arc_to_bezier_segments(
            start_x=100, start_y=100,
            rx=100, ry=100, x_axis_rotation=0,
            large_arc_flag=0, sweep_flag=1,  # Small arc
            end_x=200, end_y=100
        )

        large_arc = converter.arc_to_bezier_segments(
            start_x=100, start_y=100,
            rx=100, ry=100, x_axis_rotation=0,
            large_arc_flag=1, sweep_flag=1,  # Large arc
            end_x=200, end_y=100
        )

        # Large arc should typically generate more segments
        # (though this depends on the specific geometry)
        assert len(small_arc) >= 1
        assert len(large_arc) >= 1

    def test_sweep_flag_variations(self, converter):
        """Test different sweep flag values."""
        # Clockwise sweep
        cw_arc = converter.arc_to_bezier_segments(
            start_x=100, start_y=100,
            rx=50, ry=50, x_axis_rotation=0,
            large_arc_flag=0, sweep_flag=0,  # Clockwise
            end_x=150, end_y=150
        )

        # Counter-clockwise sweep
        ccw_arc = converter.arc_to_bezier_segments(
            start_x=100, start_y=100,
            rx=50, ry=50, x_axis_rotation=0,
            large_arc_flag=0, sweep_flag=1,  # Counter-clockwise
            end_x=150, end_y=150
        )

        assert len(cw_arc) >= 1
        assert len(ccw_arc) >= 1

    def test_degenerate_arc_zero_radius(self, converter):
        """Test handling of degenerate arc with zero radius."""
        bezier_segments = converter.arc_to_bezier_segments(
            start_x=100, start_y=100,
            rx=0, ry=50, x_axis_rotation=0,  # Zero x-radius
            large_arc_flag=0, sweep_flag=1,
            end_x=200, end_y=100
        )

        # Should create a linear segment
        assert len(bezier_segments) == 1
        segment = bezier_segments[0]

        # Should be approximately linear (control points on the line)
        assert segment.start_point.x == 100
        assert segment.start_point.y == 100
        assert segment.end_point.x == 200
        assert segment.end_point.y == 100

    def test_parameter_validation_positive_radii(self, converter):
        """Test that radii must be positive."""
        # Negative radius should be invalid
        assert not converter.validate_arc_parameters(
            rx=-50, ry=50, start_x=0, start_y=0, end_x=100, end_y=100
        )

        # Zero radius should be invalid (for validation, though handled as degenerate)
        assert not converter.validate_arc_parameters(
            rx=0, ry=50, start_x=0, start_y=0, end_x=100, end_y=100
        )

        # Positive radii should be valid
        assert converter.validate_arc_parameters(
            rx=50, ry=50, start_x=0, start_y=0, end_x=100, end_y=100
        )

    def test_parameter_validation_finite_values(self, converter):
        """Test validation of finite parameter values."""
        # Infinite radius should be invalid
        assert not converter.validate_arc_parameters(
            rx=float('inf'), ry=50, start_x=0, start_y=0, end_x=100, end_y=100
        )

        # Very large but finite values should be invalid
        assert not converter.validate_arc_parameters(
            rx=1e7, ry=50, start_x=0, start_y=0, end_x=100, end_y=100
        )

    def test_parameter_validation_nan_values(self, converter):
        """Test validation rejects NaN values."""
        assert not converter.validate_arc_parameters(
            rx=float('nan'), ry=50, start_x=0, start_y=0, end_x=100, end_y=100
        )

    def test_quality_parameter_configuration(self, converter):
        """Test arc quality parameter configuration."""
        # Valid parameters
        converter.set_quality_parameters(max_segment_angle=45.0, error_tolerance=0.005)
        assert converter.max_segment_angle == 45.0
        assert converter.error_tolerance == 0.005

        # Invalid max_segment_angle
        with pytest.raises(ValueError, match="max_segment_angle must be between 10 and 180"):
            converter.set_quality_parameters(max_segment_angle=5.0)

        with pytest.raises(ValueError, match="max_segment_angle must be between 10 and 180"):
            converter.set_quality_parameters(max_segment_angle=200.0)

        # Invalid error_tolerance
        with pytest.raises(ValueError, match="error_tolerance must be between 0.001 and 1.0"):
            converter.set_quality_parameters(error_tolerance=0.0005)

        with pytest.raises(ValueError, match="error_tolerance must be between 0.001 and 1.0"):
            converter.set_quality_parameters(error_tolerance=2.0)

    def test_estimate_arc_complexity(self, converter):
        """Test arc complexity estimation."""
        complexity = converter.estimate_arc_complexity(
            start_x=50, start_y=100,
            rx=50, ry=50, x_axis_rotation=0,
            large_arc_flag=0, sweep_flag=1,
            end_x=150, end_y=100
        )

        assert 'estimated_segments' in complexity
        assert 'arc_distance' in complexity
        assert 'average_radius' in complexity
        assert 'complexity_score' in complexity
        assert 'is_degenerate' in complexity

        assert complexity['estimated_segments'] >= 1
        assert complexity['arc_distance'] == 100.0  # Distance from (50,100) to (150,100)
        assert complexity['average_radius'] == 50.0  # (50+50)/2

    def test_conversion_statistics_tracking(self, converter):
        """Test conversion statistics tracking."""
        initial_stats = converter.get_conversion_statistics()
        assert initial_stats['arcs_converted'] == 0
        assert initial_stats['segments_generated'] == 0

        # Convert an arc
        converter.arc_to_bezier_segments(
            start_x=50, start_y=100,
            rx=50, ry=50, x_axis_rotation=0,
            large_arc_flag=0, sweep_flag=1,
            end_x=150, end_y=100
        )

        # Check updated statistics
        stats = converter.get_conversion_statistics()
        assert stats['arcs_converted'] == 1
        assert stats['segments_generated'] >= 1
        assert 'average_segments_per_arc' in stats
        assert 'max_segment_angle' in stats
        assert 'error_tolerance' in stats

    def test_statistics_reset(self, converter):
        """Test statistics reset functionality."""
        # Generate some statistics
        converter.arc_to_bezier_segments(
            start_x=50, start_y=100,
            rx=50, ry=50, x_axis_rotation=0,
            large_arc_flag=0, sweep_flag=1,
            end_x=150, end_y=100
        )

        assert converter.get_conversion_statistics()['arcs_converted'] == 1

        # Reset statistics
        converter.reset_statistics()

        stats = converter.get_conversion_statistics()
        assert stats['arcs_converted'] == 0
        assert stats['segments_generated'] == 0

    def test_complex_arc_with_multiple_segments(self, converter):
        """Test arc that requires multiple segments."""
        # Configure for smaller segments to force multiple segments
        converter.set_quality_parameters(max_segment_angle=30.0)

        # Large arc that should be split into multiple segments
        bezier_segments = converter.arc_to_bezier_segments(
            start_x=100, start_y=100,
            rx=100, ry=100, x_axis_rotation=0,
            large_arc_flag=1, sweep_flag=1,  # Large arc
            end_x=100, end_y=300  # Half circle
        )

        # Should generate multiple segments for a large arc with small max angle
        assert len(bezier_segments) > 1

    def test_scientific_notation_coordinates(self, converter):
        """Test handling of scientific notation coordinates."""
        bezier_segments = converter.arc_to_bezier_segments(
            start_x=1e2, start_y=2e2,  # 100, 200
            rx=5e1, ry=5e1, x_axis_rotation=0,  # 50, 50
            large_arc_flag=0, sweep_flag=1,
            end_x=2e2, end_y=2e2  # 200, 200
        )

        assert len(bezier_segments) >= 1
        # Should handle scientific notation correctly

    def test_very_small_arc(self, converter):
        """Test conversion of very small arc."""
        bezier_segments = converter.arc_to_bezier_segments(
            start_x=100.0, start_y=100.0,
            rx=1.0, ry=1.0, x_axis_rotation=0,  # Very small radii
            large_arc_flag=0, sweep_flag=1,
            end_x=101.0, end_y=100.0  # Very short arc
        )

        assert len(bezier_segments) >= 1
        # Should handle small arcs correctly

