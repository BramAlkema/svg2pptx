#!/usr/bin/env python3
"""
Unit tests for feDisplacementMap Path Processing and Micro-Warp Effects.

This test module specifically covers path subdivision, coordinate offsetting,
and custom geometry generation for displacement map effects.

Focus Areas:
- Subtask 2.5.2: Path subdivision and coordinate offsetting tests
- Subtask 2.5.4: Path subdivision algorithms for smooth displacement approximation
- Subtask 2.5.5: Node coordinate offsetting based on displacement values
- Subtask 2.5.6: Micro-warp effects using a:custGeom with adjusted vertices
- Subtask 2.5.7: Displacement scaling and boundary conditions
- Subtask 2.5.8: Vector quality preservation with minimal distortion
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import math

# Import the filter implementation (to be created)
from src.converters.filters.geometric.displacement_map import (
    DisplacementMapFilter,
    DisplacementMapParameters
)
from src.converters.filters.core.base import FilterContext, FilterResult


class TestPathSubdivisionAlgorithms(unittest.TestCase):
    """Test advanced path subdivision algorithms (Subtask 2.5.4)."""

    def setUp(self):
        """Set up test fixtures."""
        self.filter = DisplacementMapFilter()
        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = lambda x: int(float(x.replace('px', '')) * 12700)

    def test_bezier_curve_subdivision(self):
        """Test subdivision of Bézier curves for smooth displacement."""
        # Cubic Bézier curve: start, control1, control2, end
        control_points = [(0, 0), (50, 100), (150, 100), (200, 0)]
        subdivisions = 8

        subdivided_points = self.filter._subdivide_bezier_curve(control_points, subdivisions)

        # Should return subdivisions + 1 points
        self.assertEqual(len(subdivided_points), subdivisions + 1)

        # First and last points should match curve endpoints
        self.assertEqual(subdivided_points[0], (0, 0))
        self.assertEqual(subdivided_points[-1], (200, 0))

        # Check that curve follows expected Bézier pattern
        # At t=0.5, Bézier should be at approximately (100, 75)
        mid_point = subdivided_points[len(subdivided_points) // 2]
        self.assertAlmostEqual(mid_point[0], 100, delta=10)
        self.assertAlmostEqual(mid_point[1], 75, delta=15)

    def test_arc_subdivision(self):
        """Test subdivision of elliptical arc segments."""
        # Arc parameters: center, radius_x, radius_y, start_angle, end_angle
        arc_params = {
            'center': (100, 100),
            'radius_x': 50,
            'radius_y': 30,
            'start_angle': 0,  # radians
            'end_angle': math.pi / 2,  # 90 degrees
            'subdivisions': 6
        }

        subdivided_points = self.filter._subdivide_arc(arc_params)

        # Should return subdivision count + 1 points
        expected_count = arc_params['subdivisions'] + 1
        self.assertEqual(len(subdivided_points), expected_count)

        # First point should be at start of arc
        start_point = subdivided_points[0]
        expected_start = (150, 100)  # center + (radius_x, 0)
        self.assertAlmostEqual(start_point[0], expected_start[0], places=1)
        self.assertAlmostEqual(start_point[1], expected_start[1], places=1)

        # Last point should be at end of arc
        end_point = subdivided_points[-1]
        expected_end = (100, 130)  # center + (0, radius_y)
        self.assertAlmostEqual(end_point[0], expected_end[0], places=1)
        self.assertAlmostEqual(end_point[1], expected_end[1], places=1)

    def test_adaptive_subdivision_density(self):
        """Test adaptive subdivision based on displacement complexity."""
        # Test parameters with different displacement scales
        low_complexity_params = DisplacementMapParameters(
            input_source="SourceGraphic",
            displacement_source="MinorNoise",
            scale=5.0,
            x_channel_selector="R",
            y_channel_selector="G"
        )

        high_complexity_params = DisplacementMapParameters(
            input_source="SourceGraphic",
            displacement_source="IntenseNoise",
            scale=80.0,
            x_channel_selector="R",
            y_channel_selector="G"
        )

        # Calculate adaptive subdivisions for a 200px segment
        segment_length = 200.0

        low_subdivisions = self.filter._calculate_adaptive_subdivisions(
            low_complexity_params, segment_length
        )
        high_subdivisions = self.filter._calculate_adaptive_subdivisions(
            high_complexity_params, segment_length
        )

        # Higher displacement should require more subdivisions
        self.assertGreater(high_subdivisions, low_subdivisions)

        # Both should be reasonable numbers (not too high or too low)
        self.assertGreaterEqual(low_subdivisions, 2)
        self.assertLessEqual(high_subdivisions, 50)

    def test_path_segment_classification(self):
        """Test classification of different SVG path segment types."""
        # Test linear segments
        linear_segments = [
            ("L", [100, 50]),           # Line to
            ("l", [50, 25]),            # Relative line to
            ("H", [120]),               # Horizontal line to
            ("h", [30]),                # Relative horizontal line
            ("V", [80]),                # Vertical line to
            ("v", [-20])                # Relative vertical line
        ]

        for command, coords in linear_segments:
            segment_type = self.filter._classify_path_segment(command, coords)
            self.assertEqual(segment_type, "linear")

        # Test curved segments
        curved_segments = [
            ("C", [50, 25, 100, 75, 150, 50]),  # Cubic Bézier
            ("c", [25, 12, 50, 37, 75, 25]),    # Relative cubic
            ("S", [100, 75, 150, 50]),          # Smooth cubic
            ("s", [50, 37, 75, 25]),            # Relative smooth cubic
            ("Q", [50, 25, 100, 50]),           # Quadratic Bézier
            ("q", [25, 12, 50, 25]),            # Relative quadratic
            ("T", [100, 50]),                   # Smooth quadratic
            ("t", [50, 25])                     # Relative smooth quadratic
        ]

        for command, coords in curved_segments:
            segment_type = self.filter._classify_path_segment(command, coords)
            self.assertEqual(segment_type, "curved")

    def test_curvature_based_subdivision(self):
        """Test subdivision density based on path curvature."""
        # High curvature curve (sharp turn)
        sharp_curve = [(0, 0), (10, 200), (190, 200), (200, 0)]

        # Low curvature curve (gentle turn)
        gentle_curve = [(0, 0), (60, 20), (140, 20), (200, 0)]

        sharp_subdivisions = self.filter._calculate_curvature_subdivisions(sharp_curve)
        gentle_subdivisions = self.filter._calculate_curvature_subdivisions(gentle_curve)

        # Sharp curves should require more subdivisions
        self.assertGreater(sharp_subdivisions, gentle_subdivisions)


class TestCoordinateOffsetAlgorithms(unittest.TestCase):
    """Test coordinate offsetting algorithms (Subtask 2.5.5)."""

    def setUp(self):
        """Set up test fixtures."""
        self.filter = DisplacementMapFilter()
        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 127000

    def test_displacement_vector_calculation(self):
        """Test calculation of displacement vectors from channel values."""
        # Mock displacement map data (RGBA pixels)
        displacement_data = {
            (50, 50): (128, 64, 192, 255),   # R=0.5, G=0.25, B=0.75, A=1.0
            (75, 75): (0, 255, 128, 255),    # R=0, G=1.0, B=0.5, A=1.0
            (100, 100): (255, 0, 64, 255)   # R=1.0, G=0, B=0.25, A=1.0
        }

        params = DisplacementMapParameters(
            input_source="SourceGraphic",
            displacement_source="NoiseMap",
            scale=20.0,
            x_channel_selector="R",
            y_channel_selector="G"
        )

        for (x, y), rgba in displacement_data.items():
            displacement_vector = self.filter._calculate_displacement_vector(
                (x, y), rgba, params
            )

            # Verify displacement is scaled correctly
            expected_x = (rgba[0]/255 - 0.5) * params.scale
            expected_y = (rgba[1]/255 - 0.5) * params.scale

            self.assertAlmostEqual(displacement_vector[0], expected_x, places=2)
            self.assertAlmostEqual(displacement_vector[1], expected_y, places=2)

    def test_bilinear_displacement_interpolation(self):
        """Test bilinear interpolation of displacement values."""
        # Four corner displacement values
        corner_displacements = {
            (0, 0): (10, 5),       # Top-left
            (100, 0): (15, 8),     # Top-right
            (0, 100): (5, 12),     # Bottom-left
            (100, 100): (12, 15)   # Bottom-right
        }

        # Test point in the middle
        test_point = (50, 50)

        interpolated_displacement = self.filter._interpolate_displacement_bilinear(
            test_point, corner_displacements
        )

        # Should be average of all four corners
        expected_x = (10 + 15 + 5 + 12) / 4
        expected_y = (5 + 8 + 12 + 15) / 4

        self.assertAlmostEqual(interpolated_displacement[0], expected_x, places=2)
        self.assertAlmostEqual(interpolated_displacement[1], expected_y, places=2)

    def test_normal_vector_calculation(self):
        """Test calculation of normal vectors for displacement direction."""
        # Test horizontal line segment
        horizontal_segment = [(0, 50), (100, 50)]
        horizontal_normal = self.filter._calculate_segment_normal(horizontal_segment)

        # Normal to horizontal line should be vertical (0, ±1)
        expected_horizontal_normal = (0, 1)  # Assuming upward normal
        self.assertAlmostEqual(horizontal_normal[0], expected_horizontal_normal[0], places=3)
        self.assertAlmostEqual(abs(horizontal_normal[1]), abs(expected_horizontal_normal[1]), places=3)

        # Test vertical line segment
        vertical_segment = [(50, 0), (50, 100)]
        vertical_normal = self.filter._calculate_segment_normal(vertical_segment)

        # Normal to vertical line should be horizontal (±1, 0)
        expected_vertical_normal = (1, 0)  # Assuming rightward normal
        self.assertAlmostEqual(abs(vertical_normal[0]), abs(expected_vertical_normal[0]), places=3)
        self.assertAlmostEqual(vertical_normal[1], expected_vertical_normal[1], places=3)

    def test_displacement_along_normal(self):
        """Test applying displacement along segment normal vectors."""
        original_point = (50, 50)
        segment_normal = (0.6, 0.8)  # Normalized normal vector
        displacement_magnitude = 15.0

        displaced_point = self.filter._apply_displacement_along_normal(
            original_point, segment_normal, displacement_magnitude
        )

        # Point should be moved along the normal vector
        expected_x = original_point[0] + segment_normal[0] * displacement_magnitude
        expected_y = original_point[1] + segment_normal[1] * displacement_magnitude

        self.assertAlmostEqual(displaced_point[0], expected_x, places=2)
        self.assertAlmostEqual(displaced_point[1], expected_y, places=2)

    def test_tangential_displacement_smoothing(self):
        """Test smoothing of displacement to maintain path continuity."""
        # Path points with displacement values
        path_points = [
            ((0, 50), (5, 0)),     # Point with displacement vector
            ((25, 50), (8, 2)),    # Next point
            ((50, 50), (12, -1)),  # Middle point
            ((75, 50), (7, 3)),    # Next point
            ((100, 50), (4, 1))    # End point
        ]

        # Smooth the middle point's displacement
        smoothed_displacement = self.filter._smooth_displacement_vector(
            path_points, 2  # Index of middle point
        )

        # Smoothed displacement should be influenced by neighboring points
        original_displacement = path_points[2][1]

        # Should be different from original (smoothed)
        self.assertNotEqual(smoothed_displacement, original_displacement)

        # But should still be reasonable (not too far from neighbors)
        neighbor_avg_x = (path_points[1][1][0] + path_points[3][1][0]) / 2
        neighbor_avg_y = (path_points[1][1][1] + path_points[3][1][1]) / 2

        # Smoothed value should be closer to neighbor average than original
        original_distance = ((original_displacement[0] - neighbor_avg_x)**2 +
                           (original_displacement[1] - neighbor_avg_y)**2)**0.5
        smoothed_distance = ((smoothed_displacement[0] - neighbor_avg_x)**2 +
                           (smoothed_displacement[1] - neighbor_avg_y)**2)**0.5

        self.assertLessEqual(smoothed_distance, original_distance)


class TestMicroWarpEffects(unittest.TestCase):
    """Test micro-warp effects using PowerPoint custom geometry (Subtask 2.5.6)."""

    def setUp(self):
        """Set up test fixtures."""
        self.filter = DisplacementMapFilter()
        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = lambda x: int(float(x.replace('px', '')) * 12700)

    def test_custom_geometry_generation(self):
        """Test generation of PowerPoint custom geometry for warped paths."""
        # Displaced path points (original + displacement)
        displaced_path = [
            (0, 50),      # Start point
            (23, 52),     # Slightly displaced
            (48, 47),     # More displaced
            (76, 53),     # Displaced in other direction
            (100, 49)     # End point
        ]

        custom_geometry = self.filter._generate_custom_geometry(displaced_path, self.mock_context)

        # Should generate valid PowerPoint custom geometry DrawingML
        self.assertIn("a:custGeom", custom_geometry)
        self.assertIn("a:pathLst", custom_geometry)
        self.assertIn("a:path", custom_geometry)

        # Should contain move and line commands for the displaced path
        self.assertIn("a:moveTo", custom_geometry)
        self.assertIn("a:lnTo", custom_geometry)

        # Should convert coordinates to EMU units
        for x, y in displaced_path:
            expected_emu_x = int(x * 12700)
            expected_emu_y = int(y * 12700)
            self.assertIn(str(expected_emu_x), custom_geometry)
            self.assertIn(str(expected_emu_y), custom_geometry)

    def test_curved_path_custom_geometry(self):
        """Test custom geometry generation for curved displaced paths."""
        # Curved path with displacement (cubic Bézier)
        displaced_curve_points = [
            (0, 50),       # Start
            (20, 55),      # Displaced control point 1
            (80, 45),      # Displaced control point 2
            (100, 52)      # End
        ]

        # Path type indicates this is a cubic curve
        path_type = "cubic_bezier"

        custom_geometry = self.filter._generate_curved_custom_geometry(
            displaced_curve_points, path_type, self.mock_context
        )

        # Should use cubic Bézier DrawingML commands
        self.assertIn("a:cubicBezTo", custom_geometry)

        # Should contain all control points
        for x, y in displaced_curve_points:
            expected_emu_x = int(x * 12700)
            expected_emu_y = int(y * 12700)
            self.assertIn(str(expected_emu_x), custom_geometry)
            self.assertIn(str(expected_emu_y), custom_geometry)

    def test_path_closure_handling(self):
        """Test handling of closed paths in custom geometry."""
        # Closed path (ends where it starts)
        closed_displaced_path = [
            (50, 25),     # Start
            (75, 30),     # Point 1
            (75, 70),     # Point 2
            (25, 70),     # Point 3
            (25, 25),     # Point 4
            (50, 25)      # Back to start (closed)
        ]

        is_closed_path = True

        custom_geometry = self.filter._generate_custom_geometry(
            closed_displaced_path, self.mock_context, is_closed_path
        )

        # Should include path closure command
        self.assertIn("a:close", custom_geometry)

        # Should not duplicate the start point
        move_to_count = custom_geometry.count("<a:moveTo>")  # Count opening tags only
        self.assertEqual(move_to_count, 1)  # Only one move command

    def test_multi_path_custom_geometry(self):
        """Test custom geometry for multiple displaced sub-paths."""
        # Multiple disconnected paths (e.g., from complex shape)
        displaced_sub_paths = [
            # Path 1
            [(10, 10), (40, 15), (70, 8)],
            # Path 2 (separate)
            [(20, 50), (50, 55), (80, 48)],
            # Path 3 (separate)
            [(30, 90), (60, 93), (90, 87)]
        ]

        custom_geometry = self.filter._generate_multi_path_custom_geometry(
            displaced_sub_paths, self.mock_context
        )

        # Should contain multiple path elements (excluding the pathLst element)
        path_count = custom_geometry.count("<a:path w=")  # Count actual path elements with dimensions
        self.assertEqual(path_count, len(displaced_sub_paths))

        # Each path should have its own moveTo command
        move_to_count = custom_geometry.count("<a:moveTo>")  # Count opening tags only
        self.assertEqual(move_to_count, len(displaced_sub_paths))


class TestDisplacementScalingAndBounds(unittest.TestCase):
    """Test displacement scaling and boundary conditions (Subtask 2.5.7)."""

    def setUp(self):
        """Set up test fixtures."""
        self.filter = DisplacementMapFilter()
        self.mock_context = Mock(spec=FilterContext)

    def test_displacement_scale_application(self):
        """Test application of displacement scale factor."""
        # Normalized displacement values (-0.5 to 0.5 range)
        normalized_displacements = [
            (0.1, -0.2),   # Small displacement
            (0.5, 0.3),    # Large positive displacement
            (-0.4, 0.0),   # Negative X displacement
            (0.0, -0.5)    # Large negative Y displacement
        ]

        scale_factor = 25.0

        for norm_x, norm_y in normalized_displacements:
            scaled_displacement = self.filter._apply_scale_to_displacement(
                (norm_x, norm_y), scale_factor
            )

            expected_x = norm_x * scale_factor
            expected_y = norm_y * scale_factor

            self.assertAlmostEqual(scaled_displacement[0], expected_x, places=2)
            self.assertAlmostEqual(scaled_displacement[1], expected_y, places=2)

    def test_boundary_clamping(self):
        """Test clamping displaced points to shape boundaries."""
        # Original shape bounds
        shape_bounds = {
            'min_x': 0,
            'min_y': 0,
            'max_x': 200,
            'max_y': 100
        }

        # Test points that would be displaced outside bounds
        test_cases = [
            # (original_point, displacement, expected_clamped_point)
            ((10, 10), (-20, -15), (0, 0)),        # Clamp to min bounds
            ((190, 90), (25, 20), (200, 100)),     # Clamp to max bounds
            ((100, 50), (-150, 75), (0, 100)),     # Mixed clamping
            ((50, 25), (10, -50), (60, 0))         # Partial clamping
        ]

        for original, displacement, expected in test_cases:
            clamped_point = self.filter._clamp_displaced_point(
                original, displacement, shape_bounds
            )

            self.assertEqual(clamped_point, expected)

    def test_proportional_boundary_scaling(self):
        """Test proportional scaling when displacement exceeds boundaries."""
        # Instead of hard clamping, test proportional reduction
        original_point = (50, 50)
        large_displacement = (100, -80)  # Would move to (150, -30)
        max_displacement_bounds = {'x': 75, 'y': 40}

        # Scale displacement proportionally to stay within bounds
        scaled_displacement = self.filter._scale_displacement_proportionally(
            large_displacement, max_displacement_bounds
        )

        # Displacement should be reduced but maintain direction
        displacement_ratio = (scaled_displacement[0] / large_displacement[0])
        expected_y = large_displacement[1] * displacement_ratio

        self.assertAlmostEqual(scaled_displacement[1], expected_y, places=2)

        # Final displaced point should be within bounds
        final_point = (
            original_point[0] + scaled_displacement[0],
            original_point[1] + scaled_displacement[1]
        )

        # Should not exceed maximum displacement bounds
        self.assertLessEqual(abs(scaled_displacement[0]), max_displacement_bounds['x'])
        self.assertLessEqual(abs(scaled_displacement[1]), max_displacement_bounds['y'])

    def test_adaptive_scale_reduction(self):
        """Test adaptive scale reduction for extreme displacement values."""
        params = DisplacementMapParameters(
            input_source="SourceGraphic",
            displacement_source="ExtremeNoise",
            scale=200.0,  # Very high scale
            x_channel_selector="R",
            y_channel_selector="G"
        )

        # Path segment length
        segment_length = 50.0

        # Should automatically reduce scale for short segments
        effective_scale = self.filter._calculate_effective_scale(params, segment_length)

        # Effective scale should be reasonable for segment length
        # Implementation returns scale value based on segment analysis
        self.assertGreaterEqual(effective_scale, params.scale * 0.1)  # At least 10% of original
        self.assertLessEqual(effective_scale, params.scale)  # Not more than original

        # But should still provide reasonable displacement
        self.assertGreater(effective_scale, 0)

    def test_boundary_condition_edge_cases(self):
        """Test edge cases in boundary condition handling."""
        # Test zero-sized bounds
        zero_bounds = {'min_x': 50, 'min_y': 50, 'max_x': 50, 'max_y': 50}
        point_in_bounds = (50, 50)
        any_displacement = (10, -5)

        clamped = self.filter._clamp_displaced_point(
            point_in_bounds, any_displacement, zero_bounds
        )

        # Should clamp to the single valid point
        self.assertEqual(clamped, (50, 50))

        # Test inverted bounds (max < min) - should handle gracefully
        inverted_bounds = {'min_x': 100, 'min_y': 100, 'max_x': 0, 'max_y': 0}
        test_point = (50, 50)

        try:
            result = self.filter._clamp_displaced_point(
                test_point, any_displacement, inverted_bounds
            )
            # Should not crash, may return corrected bounds or original point
            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 2)
        except ValueError:
            # Or may raise ValueError for invalid bounds - both acceptable
            pass


class TestVectorQualityAndDistortion(unittest.TestCase):
    """Test vector quality preservation with minimal distortion (Subtask 2.5.8)."""

    def setUp(self):
        """Set up test fixtures."""
        self.filter = DisplacementMapFilter()
        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = lambda x: int(float(x.replace('px', '')) * 12700)

    def test_displacement_smoothing_quality(self):
        """Test that displacement preserves smooth vector paths."""
        # Original smooth curve
        original_curve = [
            (0, 50), (25, 60), (50, 65), (75, 60), (100, 50)
        ]

        # Small random displacements
        small_displacements = [
            (2, 1), (1, -2), (-1, 2), (2, -1), (-2, 1)
        ]

        displaced_curve = []
        for i, (point, displacement) in enumerate(zip(original_curve, small_displacements)):
            displaced_point = (point[0] + displacement[0], point[1] + displacement[1])
            displaced_curve.append(displaced_point)

        # Check that the displaced curve maintains smoothness
        smoothness_score = self.filter._calculate_path_smoothness(displaced_curve)

        # Should still be relatively smooth despite displacement
        self.assertGreater(smoothness_score, 0.7)  # 70% smoothness retained

    def test_distortion_measurement(self):
        """Test measurement of distortion introduced by displacement."""
        # Original regular shape (square)
        original_square = [
            (0, 0), (100, 0), (100, 100), (0, 100), (0, 0)
        ]

        # Displaced square (slightly warped)
        displaced_square = [
            (2, -1), (98, 3), (102, 97), (-2, 103), (2, -1)
        ]

        distortion_metric = self.filter._measure_path_distortion(
            original_square, displaced_square
        )

        # Should quantify the amount of distortion
        self.assertGreater(distortion_metric, 0)  # Some distortion present
        self.assertLess(distortion_metric, 0.1)   # But minimal for small displacements

    def test_adaptive_quality_preservation(self):
        """Test adaptive quality preservation based on displacement magnitude."""
        params_low = DisplacementMapParameters(
            input_source="SourceGraphic",
            displacement_source="MinorNoise",
            scale=5.0,  # Low displacement
            x_channel_selector="R",
            y_channel_selector="G"
        )

        params_high = DisplacementMapParameters(
            input_source="SourceGraphic",
            displacement_source="MajorNoise",
            scale=50.0,  # High displacement
            x_channel_selector="R",
            y_channel_selector="G"
        )

        # Generate DrawingML for both scenarios
        drawingml_low = self.filter._generate_displacement_drawingml(params_low, self.mock_context)
        drawingml_high = self.filter._generate_displacement_drawingml(params_high, self.mock_context)

        # Low displacement should maintain more vector elements
        self.assertIn("custGeom", drawingml_low)  # Should use custom geometry

        # High displacement might use different approach or more subdivisions
        # Both should still be vector-based
        self.assertNotIn("raster", drawingml_low.lower())
        self.assertNotIn("raster", drawingml_high.lower())

    def test_vector_precision_maintenance(self):
        """Test that vector precision is maintained through displacement."""
        # High-precision coordinates
        precise_points = [
            (12.3456, 78.9012),
            (34.5678, 90.1234),
            (56.7890, 12.3456)
        ]

        # Small precise displacements
        precise_displacements = [
            (1.1111, -2.2222),
            (-0.3333, 1.4444),
            (2.5555, -0.7777)
        ]

        # Apply displacement and generate custom geometry
        displaced_points = []
        for point, displacement in zip(precise_points, precise_displacements):
            displaced_point = (
                point[0] + displacement[0],
                point[1] + displacement[1]
            )
            displaced_points.append(displaced_point)

        custom_geometry = self.filter._generate_custom_geometry(
            displaced_points, self.mock_context
        )

        # Should preserve precision in EMU conversion
        for x, y in displaced_points:
            expected_emu_x = int(x * 12700)
            expected_emu_y = int(y * 12700)

            # Should find the precise EMU values in the output
            self.assertIn(str(expected_emu_x), custom_geometry)
            self.assertIn(str(expected_emu_y), custom_geometry)

    def test_readability_preservation(self):
        """Test that displaced paths remain readable in PowerPoint."""
        params = DisplacementMapParameters(
            input_source="SourceGraphic",
            displacement_source="SubtleTexture",
            scale=15.0,
            x_channel_selector="R",
            y_channel_selector="G"
        )

        drawingml = self.filter._generate_displacement_drawingml(params, self.mock_context)

        # Should include readability preservation comments and structure
        self.assertIn("vector", drawingml.lower())
        self.assertIn("readable", drawingml.lower() or "quality" in drawingml.lower())

        # Should use appropriate PowerPoint elements for maintaining editability
        self.assertIn("a:custGeom", drawingml)

        # Should not use overly complex nested structures
        nesting_level = drawingml.count("<") - drawingml.count("<!--")
        self.assertLess(nesting_level, 50)  # Reasonable complexity limit


if __name__ == '__main__':
    unittest.main()