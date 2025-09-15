#!/usr/bin/env python3
"""
Unit tests for feDisplacementMap Vector-First Filter Implementation.

This test module covers the vector-first approach for SVG feDisplacementMap filter effects,
testing path subdivision algorithms and coordinate offsetting for PowerPoint conversion.

Tests follow the TDD approach established in Task 2.5:
- Subtask 2.5.1: Unit tests for displacement map parsing and channel extraction
- Subtask 2.5.2: Tests for path subdivision and coordinate offsetting
- Subtask 2.5.3: feDisplacementMap parser with displacement source analysis
- Subtask 2.5.4: Path subdivision algorithms for smooth displacement approximation
- Subtask 2.5.5: Node coordinate offsetting based on displacement values
- Subtask 2.5.6: Micro-warp effects using a:custGeom with adjusted vertices
- Subtask 2.5.7: Displacement scaling and boundary conditions
- Subtask 2.5.8: Vector quality preservation with minimal distortion
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from lxml import etree

# Import the filter implementation (to be created)
from src.converters.filters.geometric.displacement_map import (
    DisplacementMapFilter,
    DisplacementMapParameters
)
from src.converters.filters.core.base import FilterContext, FilterResult


class TestDisplacementMapFilterBasics(unittest.TestCase):
    """Test basic DisplacementMapFilter functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.filter = DisplacementMapFilter()

        # Mock FilterContext with standardized tools
        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.color_parser = Mock()
        self.mock_context.transform_parser = Mock()
        self.mock_context.viewport_resolver = Mock()

        # Configure unit converter mock to return EMU values
        self.mock_context.unit_converter.to_emu.side_effect = lambda x: int(float(x.replace('px', '')) * 12700)

    def test_filter_initialization(self):
        """Test DisplacementMapFilter initialization."""
        self.assertEqual(self.filter.filter_type, "displacement_map")
        self.assertEqual(self.filter.strategy, "vector_first")
        self.assertIsInstance(self.filter.complexity_threshold, (int, float))

    def test_can_apply_fedisplacementmap_element(self):
        """Test can_apply returns True for feDisplacementMap elements."""
        element = etree.Element("feDisplacementMap")

        result = self.filter.can_apply(element, self.mock_context)
        self.assertTrue(result)

    def test_can_apply_with_namespace(self):
        """Test can_apply handles namespaced elements correctly."""
        element = etree.Element("{http://www.w3.org/2000/svg}feDisplacementMap")

        result = self.filter.can_apply(element, self.mock_context)
        self.assertTrue(result)

    def test_can_apply_non_fedisplacementmap_element(self):
        """Test can_apply returns False for non-feDisplacementMap elements."""
        element = etree.Element("feGaussianBlur")

        result = self.filter.can_apply(element, self.mock_context)
        self.assertFalse(result)

    def test_can_apply_none_element(self):
        """Test can_apply handles None element gracefully."""
        result = self.filter.can_apply(None, self.mock_context)
        self.assertFalse(result)


class TestDisplacementMapParameterParsing(unittest.TestCase):
    """Test displacement map parameter parsing (Subtask 2.5.1)."""

    def setUp(self):
        """Set up test fixtures."""
        self.filter = DisplacementMapFilter()
        self.mock_context = Mock(spec=FilterContext)

    def test_basic_displacement_map_parsing(self):
        """Test basic feDisplacementMap parameter parsing."""
        element = etree.Element("feDisplacementMap")
        element.set("in", "SourceGraphic")
        element.set("in2", "DisplacementSource")
        element.set("scale", "30")
        element.set("xChannelSelector", "R")
        element.set("yChannelSelector", "G")

        params = self.filter._parse_parameters(element)

        self.assertEqual(params.input_source, "SourceGraphic")
        self.assertEqual(params.displacement_source, "DisplacementSource")
        self.assertEqual(params.scale, 30.0)
        self.assertEqual(params.x_channel_selector, "R")
        self.assertEqual(params.y_channel_selector, "G")
        self.assertIsNone(params.result_name)

    def test_default_parameter_values(self):
        """Test default values for missing parameters."""
        element = etree.Element("feDisplacementMap")

        params = self.filter._parse_parameters(element)

        self.assertEqual(params.input_source, "SourceGraphic")
        self.assertEqual(params.displacement_source, "SourceGraphic")
        self.assertEqual(params.scale, 0.0)
        self.assertEqual(params.x_channel_selector, "A")
        self.assertEqual(params.y_channel_selector, "A")

    def test_channel_selector_validation(self):
        """Test channel selector validation for R, G, B, A values."""
        element = etree.Element("feDisplacementMap")

        # Test valid channel selectors
        for channel in ["R", "G", "B", "A"]:
            element.set("xChannelSelector", channel)
            element.set("yChannelSelector", channel)

            params = self.filter._parse_parameters(element)
            self.assertEqual(params.x_channel_selector, channel)
            self.assertEqual(params.y_channel_selector, channel)

    def test_invalid_channel_selector_handling(self):
        """Test handling of invalid channel selector values."""
        element = etree.Element("feDisplacementMap")
        element.set("xChannelSelector", "INVALID")
        element.set("yChannelSelector", "X")

        params = self.filter._parse_parameters(element)

        # Should default to 'A' for invalid values
        self.assertEqual(params.x_channel_selector, "A")
        self.assertEqual(params.y_channel_selector, "A")

    def test_scale_parameter_parsing(self):
        """Test scale parameter parsing and validation."""
        element = etree.Element("feDisplacementMap")

        # Test valid scale values
        test_cases = [
            ("0", 0.0),
            ("10", 10.0),
            ("50.5", 50.5),
            ("-20", -20.0)
        ]

        for scale_str, expected_scale in test_cases:
            element.set("scale", scale_str)
            params = self.filter._parse_parameters(element)
            self.assertEqual(params.scale, expected_scale)

    def test_invalid_scale_parameter_handling(self):
        """Test handling of invalid scale parameter values."""
        element = etree.Element("feDisplacementMap")
        element.set("scale", "invalid_number")

        params = self.filter._parse_parameters(element)
        self.assertEqual(params.scale, 0.0)  # Should default to 0

    def test_result_name_parsing(self):
        """Test result name parsing."""
        element = etree.Element("feDisplacementMap")
        element.set("result", "DisplacedResult")

        params = self.filter._parse_parameters(element)
        self.assertEqual(params.result_name, "DisplacedResult")

    def test_complex_displacement_configuration(self):
        """Test parsing complex displacement map configuration."""
        element = etree.Element("feDisplacementMap")
        element.set("in", "BackgroundImage")
        element.set("in2", "TurbulenceNoise")
        element.set("scale", "15")
        element.set("xChannelSelector", "B")
        element.set("yChannelSelector", "R")
        element.set("result", "WarpedBackground")

        params = self.filter._parse_parameters(element)

        self.assertEqual(params.input_source, "BackgroundImage")
        self.assertEqual(params.displacement_source, "TurbulenceNoise")
        self.assertEqual(params.scale, 15.0)
        self.assertEqual(params.x_channel_selector, "B")
        self.assertEqual(params.y_channel_selector, "R")
        self.assertEqual(params.result_name, "WarpedBackground")


class TestChannelExtractionAnalysis(unittest.TestCase):
    """Test displacement channel extraction and analysis (Subtask 2.5.1)."""

    def setUp(self):
        """Set up test fixtures."""
        self.filter = DisplacementMapFilter()
        self.mock_context = Mock(spec=FilterContext)

    def test_channel_value_extraction(self):
        """Test extracting displacement values from RGBA channels."""
        params = DisplacementMapParameters(
            input_source="SourceGraphic",
            displacement_source="NoiseMap",
            scale=20.0,
            x_channel_selector="R",
            y_channel_selector="G"
        )

        # Mock pixel data (RGBA format)
        rgba_pixel = (128, 64, 192, 255)  # R=128, G=64, B=192, A=255

        x_displacement = self.filter._extract_channel_value(rgba_pixel, params.x_channel_selector)
        y_displacement = self.filter._extract_channel_value(rgba_pixel, params.y_channel_selector)

        # Channel values should be normalized to -0.5 to 0.5 range
        # 128/255 ≈ 0.502, so (0.502 - 0.5) ≈ 0.002
        # 64/255 ≈ 0.251, so (0.251 - 0.5) ≈ -0.249
        self.assertAlmostEqual(x_displacement, (128/255 - 0.5), places=3)
        self.assertAlmostEqual(y_displacement, (64/255 - 0.5), places=3)

    def test_all_channel_selectors(self):
        """Test channel value extraction for all RGBA channels."""
        rgba_pixel = (100, 150, 200, 50)

        test_cases = [
            ("R", 100/255 - 0.5),
            ("G", 150/255 - 0.5),
            ("B", 200/255 - 0.5),
            ("A", 50/255 - 0.5)
        ]

        for channel, expected_value in test_cases:
            result = self.filter._extract_channel_value(rgba_pixel, channel)
            self.assertAlmostEqual(result, expected_value, places=3)

    def test_displacement_scaling_application(self):
        """Test applying scale factor to displacement values."""
        # Normalized displacement value of 0.1 (channel value ~152/255)
        normalized_displacement = 0.1
        scale = 30.0

        scaled_displacement = self.filter._apply_displacement_scaling(normalized_displacement, scale)

        # Scaled displacement should be normalized_value * scale
        expected_displacement = normalized_displacement * scale
        self.assertAlmostEqual(scaled_displacement, expected_displacement, places=3)

    def test_zero_scale_handling(self):
        """Test handling of zero scale factor."""
        normalized_displacement = 0.2
        scale = 0.0

        scaled_displacement = self.filter._apply_displacement_scaling(normalized_displacement, scale)
        self.assertEqual(scaled_displacement, 0.0)

    def test_negative_scale_handling(self):
        """Test handling of negative scale factor."""
        normalized_displacement = 0.1
        scale = -15.0

        scaled_displacement = self.filter._apply_displacement_scaling(normalized_displacement, scale)
        expected_displacement = normalized_displacement * scale
        self.assertAlmostEqual(scaled_displacement, expected_displacement, places=3)


class TestPathSubdivisionAlgorithms(unittest.TestCase):
    """Test path subdivision algorithms (Subtask 2.5.2)."""

    def setUp(self):
        """Set up test fixtures."""
        self.filter = DisplacementMapFilter()
        self.mock_context = Mock(spec=FilterContext)

    def test_linear_path_subdivision(self):
        """Test subdivision of linear path segments."""
        # Simple line from (0,0) to (100,0)
        start_point = (0.0, 0.0)
        end_point = (100.0, 0.0)
        subdivision_count = 4

        subdivided_points = self.filter._subdivide_linear_segment(start_point, end_point, subdivision_count)

        # Should return 5 points (including start and end)
        self.assertEqual(len(subdivided_points), subdivision_count + 1)

        # Verify endpoints
        self.assertEqual(subdivided_points[0], start_point)
        self.assertEqual(subdivided_points[-1], end_point)

        # Verify intermediate points are evenly spaced
        expected_points = [(0.0, 0.0), (25.0, 0.0), (50.0, 0.0), (75.0, 0.0), (100.0, 0.0)]
        for i, point in enumerate(subdivided_points):
            self.assertAlmostEqual(point[0], expected_points[i][0], places=3)
            self.assertAlmostEqual(point[1], expected_points[i][1], places=3)

    def test_curved_path_subdivision(self):
        """Test subdivision of curved path segments."""
        # Cubic Bézier curve control points
        control_points = [(0.0, 0.0), (25.0, 50.0), (75.0, 50.0), (100.0, 0.0)]
        subdivision_count = 3

        subdivided_points = self.filter._subdivide_cubic_bezier(control_points, subdivision_count)

        # Should return 4 points (including start and end)
        self.assertEqual(len(subdivided_points), subdivision_count + 1)

        # Verify endpoints
        self.assertEqual(subdivided_points[0], control_points[0])
        self.assertEqual(subdivided_points[-1], control_points[3])

        # Verify curve points are different from linear interpolation
        # (indicating proper cubic Bézier calculation)
        linear_mid = ((control_points[0][0] + control_points[3][0])/2,
                     (control_points[0][1] + control_points[3][1])/2)
        curve_mid = subdivided_points[len(subdivided_points)//2]

        # Curve midpoint should be different from linear midpoint
        self.assertNotEqual(curve_mid, linear_mid)

    def test_path_segment_type_detection(self):
        """Test detection of different path segment types."""
        # Test linear segment detection
        linear_commands = ["L", "H", "V", "l", "h", "v"]
        for command in linear_commands:
            self.assertTrue(self.filter._is_linear_segment(command))

        # Test curved segment detection
        curved_commands = ["C", "S", "Q", "T", "c", "s", "q", "t"]
        for command in curved_commands:
            self.assertTrue(self.filter._is_curved_segment(command))

        # Test other commands
        other_commands = ["M", "Z", "m", "z"]
        for command in other_commands:
            self.assertFalse(self.filter._is_linear_segment(command))
            self.assertFalse(self.filter._is_curved_segment(command))

    def test_adaptive_subdivision_density(self):
        """Test adaptive subdivision based on displacement complexity."""
        # Low displacement scale should result in fewer subdivisions
        low_scale_params = DisplacementMapParameters(
            input_source="SourceGraphic",
            displacement_source="Noise",
            scale=5.0,
            x_channel_selector="R",
            y_channel_selector="G"
        )

        low_subdivisions = self.filter._calculate_adaptive_subdivisions(low_scale_params, 100.0)

        # High displacement scale should result in more subdivisions
        high_scale_params = DisplacementMapParameters(
            input_source="SourceGraphic",
            displacement_source="Noise",
            scale=50.0,
            x_channel_selector="R",
            y_channel_selector="G"
        )

        high_subdivisions = self.filter._calculate_adaptive_subdivisions(high_scale_params, 100.0)

        # High scale should require more subdivisions for smooth displacement
        self.assertGreater(high_subdivisions, low_subdivisions)


class TestCoordinateOffsetting(unittest.TestCase):
    """Test coordinate offsetting based on displacement values (Subtask 2.5.2)."""

    def setUp(self):
        """Set up test fixtures."""
        self.filter = DisplacementMapFilter()
        self.mock_context = Mock(spec=FilterContext)

    def test_point_displacement_calculation(self):
        """Test calculating displacement for individual points."""
        original_point = (50.0, 50.0)
        x_displacement = 10.0
        y_displacement = -5.0

        displaced_point = self.filter._apply_point_displacement(
            original_point, x_displacement, y_displacement
        )

        expected_point = (60.0, 45.0)
        self.assertEqual(displaced_point, expected_point)

    def test_boundary_condition_handling(self):
        """Test handling of displacement boundary conditions."""
        # Test displacement that would move point outside bounds
        original_point = (5.0, 95.0)
        x_displacement = -20.0  # Would move to x=-15
        y_displacement = 20.0   # Would move to y=115

        # Assume bounds of (0,0) to (100,100)
        bounds = {"min_x": 0.0, "min_y": 0.0, "max_x": 100.0, "max_y": 100.0}

        clamped_point = self.filter._apply_displacement_with_bounds(
            original_point, x_displacement, y_displacement, bounds
        )

        # Points should be clamped to boundary
        self.assertEqual(clamped_point[0], 0.0)   # Clamped to min_x
        self.assertEqual(clamped_point[1], 100.0) # Clamped to max_y

    def test_displacement_vector_normalization(self):
        """Test normalization of displacement vectors."""
        # Large displacement vector that exceeds reasonable bounds
        large_x_displacement = 150.0
        large_y_displacement = 200.0
        max_displacement = 50.0

        normalized_x, normalized_y = self.filter._normalize_displacement_vector(
            large_x_displacement, large_y_displacement, max_displacement
        )

        # Normalized vector should maintain direction but limit magnitude
        vector_magnitude = (normalized_x**2 + normalized_y**2)**0.5
        self.assertLessEqual(vector_magnitude, max_displacement * 1.01)  # Small tolerance

    def test_smooth_displacement_interpolation(self):
        """Test smooth interpolation between displacement values."""
        # Displacement values at path subdivision points
        displacement_values = [
            (0.0, 0.0),    # Start
            (5.0, 2.0),    # Point 1
            (10.0, -3.0),  # Point 2
            (2.0, 1.0)     # End
        ]

        # Get interpolated displacement at 25% along the path
        interpolation_factor = 0.25

        interpolated_displacement = self.filter._interpolate_displacement(
            displacement_values, interpolation_factor
        )

        # Should be interpolated between start and point 1
        expected_x = 0.0 + (5.0 - 0.0) * interpolation_factor
        expected_y = 0.0 + (2.0 - 0.0) * interpolation_factor

        self.assertAlmostEqual(interpolated_displacement[0], expected_x, places=3)
        self.assertAlmostEqual(interpolated_displacement[1], expected_y, places=3)


class TestVectorFirstApplication(unittest.TestCase):
    """Test vector-first displacement map application."""

    def setUp(self):
        """Set up test fixtures."""
        self.filter = DisplacementMapFilter()
        self.mock_context = Mock(spec=FilterContext)

        # Set up mock unit converter
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = lambda x: int(float(x.replace('px', '')) * 12700)

    def test_apply_simple_displacement_map(self):
        """Test applying simple displacement map filter."""
        element = etree.Element("feDisplacementMap")
        element.set("in", "SourceGraphic")
        element.set("in2", "NoiseMap")
        element.set("scale", "20")
        element.set("xChannelSelector", "R")
        element.set("yChannelSelector", "G")

        result = self.filter.apply(element, self.mock_context)

        self.assertTrue(result.success)
        self.assertIn("displacement", result.drawingml.lower())
        self.assertEqual(result.metadata['filter_type'], 'displacement_map')
        self.assertEqual(result.metadata['strategy'], 'vector_first')

    def test_apply_zero_scale_optimization(self):
        """Test optimization for zero scale displacement."""
        element = etree.Element("feDisplacementMap")
        element.set("scale", "0")

        result = self.filter.apply(element, self.mock_context)

        # Zero scale should result in no-op pass-through
        self.assertTrue(result.success)
        self.assertIn("zero displacement", result.drawingml.lower())

    def test_apply_complex_displacement_still_vector(self):
        """Test that complex displacement maintains vector approach."""
        element = etree.Element("feDisplacementMap")
        element.set("scale", "75")  # High scale displacement
        element.set("xChannelSelector", "B")
        element.set("yChannelSelector", "A")

        result = self.filter.apply(element, self.mock_context)

        self.assertTrue(result.success)
        self.assertEqual(result.metadata['strategy'], 'vector_first')
        self.assertIn('a:custGeom', result.drawingml)  # Should use custom geometry

    @patch('src.converters.filters.geometric.displacement_map.logger')
    def test_apply_with_exception(self, mock_logger):
        """Test handling of exceptions during apply."""
        # Mock the unit converter to raise an exception during processing
        self.mock_context.unit_converter.to_emu.side_effect = ValueError("Unit conversion failed")

        element = etree.Element("feDisplacementMap")
        element.set("scale", "30")

        # Mock the _apply_vector_first to use unit converter and raise exception
        with patch.object(self.filter, '_apply_vector_first') as mock_apply:
            mock_apply.side_effect = ValueError("Displacement processing failed")

            result = self.filter.apply(element, self.mock_context)

            self.assertFalse(result.success)
            self.assertIn("failed", result.error_message.lower())
            self.assertEqual(result.metadata['filter_type'], 'displacement_map')
            mock_logger.error.assert_called()


class TestVectorQualityMaintenance(unittest.TestCase):
    """Test vector quality maintenance and distortion minimization."""

    def setUp(self):
        """Set up test fixtures."""
        self.filter = DisplacementMapFilter()
        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 127000  # Mock EMU value

    def test_vector_quality_preservation(self):
        """Test that displacement maintains vector quality where possible."""
        params = DisplacementMapParameters(
            input_source="SourceGraphic",
            displacement_source="MinorNoise",
            scale=10.0,  # Moderate scale
            x_channel_selector="R",
            y_channel_selector="G"
        )

        drawingml = self.filter._generate_displacement_drawingml(params, self.mock_context)

        # Should use vector-first approach with custom geometry
        self.assertIn("custGeom", drawingml)
        self.assertIn("vector", drawingml.lower())
        self.assertNotIn("raster", drawingml.lower())

    def test_powerpoint_custom_geometry_usage(self):
        """Test usage of PowerPoint custom geometry for displaced paths."""
        params = DisplacementMapParameters(
            input_source="SourceGraphic",
            displacement_source="WarpMap",
            scale=25.0,
            x_channel_selector="R",
            y_channel_selector="G"
        )

        drawingml = self.filter._generate_displacement_drawingml(params, self.mock_context)

        # Should include a:custGeom with path vertices
        self.assertIn("a:custGeom", drawingml)
        self.assertIn("a:pathLst", drawingml)
        self.assertIn("a:path", drawingml)

    def test_quality_optimization_comments(self):
        """Test that DrawingML includes quality optimization comments."""
        params = DisplacementMapParameters(
            input_source="SourceGraphic",
            displacement_source="DisplacementSource",
            scale=15.0,
            x_channel_selector="G",
            y_channel_selector="B"
        )

        drawingml = self.filter._generate_displacement_drawingml(params, self.mock_context)

        # Should include quality and vector precision comments
        self.assertIn("vector", drawingml.lower())
        self.assertIn("quality", drawingml.lower() or "precision" in drawingml.lower())


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases."""

    def setUp(self):
        """Set up test fixtures."""
        self.filter = DisplacementMapFilter()
        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 127000  # Mock EMU value

    def test_parameter_parsing_error_handling(self):
        """Test robust error handling during parameter parsing."""
        # Test with malformed XML element
        element = etree.Element("feDisplacementMap")
        element.set("scale", "not_a_number")
        element.set("xChannelSelector", "INVALID")

        # Should not raise exception, should use defaults
        params = self.filter._parse_parameters(element)

        self.assertEqual(params.scale, 0.0)  # Default for invalid number
        self.assertEqual(params.x_channel_selector, "A")  # Default for invalid channel

    def test_extreme_displacement_values_handling(self):
        """Test handling of extreme displacement parameter values."""
        params = DisplacementMapParameters(
            input_source="SourceGraphic",
            displacement_source="ExtremeMap",
            scale=1000.0,  # Very large scale
            x_channel_selector="R",
            y_channel_selector="G"
        )

        # Should handle extreme values gracefully
        complexity = self.filter._calculate_complexity(params)

        # High scale should result in high complexity score
        self.assertGreater(complexity, 4.0)

    def test_missing_displacement_source_handling(self):
        """Test handling when displacement source is missing."""
        params = DisplacementMapParameters(
            input_source="SourceGraphic",
            displacement_source=None,  # Missing source
            scale=20.0,
            x_channel_selector="R",
            y_channel_selector="G"
        )

        # Should handle gracefully, possibly falling back to identity transform
        drawingml = self.filter._generate_displacement_drawingml(params, self.mock_context)

        # Should produce valid DrawingML even with missing displacement source
        self.assertIsInstance(drawingml, str)
        self.assertGreater(len(drawingml), 0)


if __name__ == '__main__':
    unittest.main()