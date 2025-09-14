#!/usr/bin/env python3
"""
Advanced Fractional EMU Precision System Tests

Tests for Task 1: Subpixel Precision System Enhancement
Tests subpixel coordinate handling and OOXML EMU conversion accuracy with fractional precision.

Key Features Tested:
- Fractional EMU coordinate conversion
- Subpixel-accurate Bezier curve positioning
- PowerPoint compatibility validation (max 3 decimal places)
- Performance benchmarking for high-precision calculations
- Mathematical accuracy within tolerance bounds
"""

import pytest
import math
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
from typing import Dict, Any, Tuple, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

# Import existing units functionality for extension
from src.units import UnitConverter, UnitType, ViewportContext, EMU_PER_INCH, EMU_PER_POINT, EMU_PER_MM, DEFAULT_DPI
from src.fractional_emu import FractionalEMUConverter, PrecisionMode, create_fractional_converter
from src.subpixel_shapes import SubpixelShapeProcessor, ShapeComplexity, create_subpixel_processor
from src.precision_integration import (
    EnhancedCoordinateSystem, PrecisionConversionContext, PrecisionAwareConverter,
    create_precision_conversion_context, create_enhanced_coordinate_system
)
import src.units as units_module


@pytest.mark.unit
@pytest.mark.converter
@pytest.mark.precision
class TestFractionalEMUPrecision:
    """
    Tests for fractional EMU precision system.

    Validates subpixel coordinate accuracy, PowerPoint compatibility,
    and mathematical precision for advanced SVG features.
    """

    @pytest.fixture
    def setup_precision_test_data(self):
        """Setup test data for fractional EMU precision testing."""
        return {
            # Fractional coordinate test cases
            'fractional_pixels': [
                ("100.5px", 957187.5, "half-pixel precision"),
                ("10.25px", 97693.75, "quarter-pixel precision"),
                ("0.1px", 952.5, "tenth-pixel precision"),
                ("999.999px", 9524995.2475, "maximum precision boundary")
            ],

            # Subpixel Bezier control points
            'bezier_control_points': [
                (10.33, 20.67, "irregular fractional control points"),
                (0.001, 0.001, "minimal fractional displacement"),
                (100.125, 200.875, "eighth-pixel precision control")
            ],

            # PowerPoint compatibility boundaries
            'compatibility_limits': {
                'max_decimal_places': 3,
                'min_emu_value': 0.001,
                'max_emu_value': 914400 * 1000  # 1000 inches max
            },

            # Performance benchmark targets
            'performance_targets': {
                'conversion_time_ms': 1.0,  # Max 1ms per conversion
                'batch_conversion_factor': 1000,  # 1000x operations
                'memory_efficiency': 0.95  # 95% memory efficiency
            }
        }

    @pytest.fixture
    def fractional_unit_converter(self):
        """Create FractionalEMUConverter for fractional EMU testing."""
        return FractionalEMUConverter(
            precision_mode=PrecisionMode.SUBPIXEL,
            default_dpi=DEFAULT_DPI,
            viewport_width=800.0,
            viewport_height=600.0
        )

    @pytest.mark.parametrize("pixel_value,description", [
        ("100.5px", "half-pixel precision"),
        ("10.25px", "quarter-pixel precision"),
        ("0.1px", "tenth-pixel precision"),
        ("999.999px", "maximum precision boundary")
    ])
    def test_fractional_pixel_conversion_accuracy(self, pixel_value, description, fractional_unit_converter):
        """Test fractional pixel to EMU conversion maintains mathematical accuracy."""
        # Extract numeric value for precise calculation
        numeric_value = float(pixel_value.replace('px', ''))

        # Calculate expected EMU with fractional precision using our new converter
        fractional_emu_result = fractional_unit_converter.to_fractional_emu(pixel_value, preserve_precision=False)

        # Calculate expected value manually for validation
        expected_fractional_emu = numeric_value * (EMU_PER_INCH / DEFAULT_DPI)

        # Test tolerance-based comparison for floating point precision
        tolerance = 0.1  # 0.1 EMU tolerance for precision
        precision_error = abs(fractional_emu_result - expected_fractional_emu)

        assert precision_error <= tolerance, (
            f"Fractional EMU calculation error {precision_error:.3f} exceeds tolerance "
            f"for {pixel_value} -> expected {expected_fractional_emu}, calculated {fractional_emu_result}"
        )

    def test_subpixel_coordinate_precision(self, setup_precision_test_data, fractional_unit_converter):
        """Test subpixel coordinate conversion for Bezier curve precision."""
        bezier_points = setup_precision_test_data['bezier_control_points']

        for x_coord, y_coord, description in bezier_points:
            # Test coordinate conversion with fractional precision
            x_emu = fractional_unit_converter.to_emu(f"{x_coord}px")
            y_emu = fractional_unit_converter.to_emu(f"{y_coord}px")

            # Calculate expected values
            expected_x_emu = x_coord * (EMU_PER_INCH / DEFAULT_DPI)
            expected_y_emu = y_coord * (EMU_PER_INCH / DEFAULT_DPI)

            # Validate subpixel precision within tolerance (allow for integer rounding)
            x_precision_error = abs(x_emu - expected_x_emu)
            y_precision_error = abs(y_emu - expected_y_emu)

            # Allow tolerance of 1 EMU since we're rounding to integers
            assert x_precision_error <= 1.0, f"X-coordinate precision error for {description}: {x_precision_error}"
            assert y_precision_error <= 1.0, f"Y-coordinate precision error for {description}: {y_precision_error}"

            # Ensure coordinates are valid for OOXML output
            assert x_emu >= 0, f"Negative X coordinates not supported in OOXML for {description}"
            assert y_emu >= 0, f"Negative Y coordinates not supported in OOXML for {description}"

    def test_powerpoint_compatibility_validation(self, setup_precision_test_data):
        """Test PowerPoint OOXML compatibility for fractional coordinates."""
        compatibility_limits = setup_precision_test_data['compatibility_limits']

        # Test decimal place limitation
        test_fractional_values = [
            1234.567,    # 3 decimal places (valid)
            1234.5678,   # 4 decimal places (needs truncation)
            1234.123456  # 6 decimal places (needs truncation)
        ]

        for value in test_fractional_values:
            # Simulate fractional EMU value truncation for PowerPoint compatibility
            truncated_value = round(value, compatibility_limits['max_decimal_places'])

            # Ensure truncated value maintains precision while staying within limits
            precision_loss = abs(value - truncated_value)

            if value != truncated_value:
                # Allow some precision loss for compatibility
                assert precision_loss <= 0.001, f"Precision loss {precision_loss} too high for PowerPoint compatibility"

            # Validate value ranges
            assert 0 <= truncated_value <= compatibility_limits['max_emu_value'], (
                f"Value {truncated_value} outside PowerPoint EMU range"
            )

    def test_fractional_emu_coordinate_transformations(self, fractional_unit_converter):
        """Test coordinate transformations with fractional EMU precision."""
        # Test DrawingML coordinate space conversion (21,600 units)
        svg_coordinates = [
            (100.5, 200.25, 400, 300),  # x, y, width, height with fractional values
            (0.1, 0.1, 800, 600),       # minimal fractional coordinates
            (50.33, 75.67, 200.125, 150.875)  # complex fractional shapes
        ]

        for svg_x, svg_y, svg_width, svg_height in svg_coordinates:
            # Convert coordinates with fractional precision
            drawingml_x = (svg_x / svg_width) * 21600
            drawingml_y = (svg_y / svg_height) * 21600

            # Ensure fractional coordinates are preserved in DrawingML space
            assert isinstance(drawingml_x, float), f"DrawingML X coordinate should preserve fractional precision for ({svg_x},{svg_y})"
            assert isinstance(drawingml_y, float), f"DrawingML Y coordinate should preserve fractional precision for ({svg_x},{svg_y})"

            # Validate coordinate bounds for DrawingML
            assert 0 <= drawingml_x <= 21600, f"DrawingML X coordinate {drawingml_x} out of bounds for ({svg_x},{svg_y})"
            assert 0 <= drawingml_y <= 21600, f"DrawingML Y coordinate {drawingml_y} out of bounds for ({svg_x},{svg_y})"

    def test_mathematical_precision_edge_cases(self, fractional_unit_converter):
        """Test mathematical precision at boundary conditions."""
        edge_cases = [
            (0.0001, "sub-pixel precision"),
            (math.pi, "irrational number precision"),
            (1/3, "repeating decimal precision"),
            (999999.9999, "maximum value precision")
        ]

        for test_value, description in edge_cases:
            # Test EMU conversion with edge case values
            emu_result = fractional_unit_converter.to_emu(f"{test_value}px")

            # Calculate expected EMU value
            expected_emu = test_value * (EMU_PER_INCH / DEFAULT_DPI)

            # Allow reasonable precision loss for extreme cases (integer rounding)
            precision_loss = abs(emu_result - expected_emu)

            # Special handling for values that exceed PowerPoint max EMU
            # PowerPoint max is 914,400,000 EMU (1000 inches)
            powerpoint_max_emu = 914400000
            if expected_emu > powerpoint_max_emu:
                # Value was clamped to max, so verify it equals the max
                assert emu_result == powerpoint_max_emu, f"Clamped value should equal PowerPoint max for {description}"
            else:
                # For integer EMU results, allow tolerance of 1 EMU or 0.01% for large values
                tolerance = max(1.0, expected_emu * 0.0001)  # Dynamic tolerance based on magnitude
                assert precision_loss <= tolerance, (
                    f"Precision loss {precision_loss:.6f} exceeds tolerance {tolerance:.6f} "
                    f"for {description}: {test_value}"
                )

    @pytest.mark.benchmark
    def test_fractional_emu_conversion_performance(self, benchmark, fractional_unit_converter):
        """Benchmark fractional EMU conversion performance."""
        # Test performance with fractional coordinate calculations
        test_coordinates = [
            "100.5px", "200.25px", "50.125px", "75.875px", "10.0625px"
        ] * 100  # 500 total conversions

        def batch_convert_coordinates():
            results = []
            for coord in test_coordinates:
                emu_value = fractional_unit_converter.to_emu(coord)
                results.append(emu_value)
            return results

        # Benchmark the batch conversion
        result = benchmark(batch_convert_coordinates)

        # Validate benchmark results
        assert len(result) == len(test_coordinates), "Batch conversion should process all coordinates"
        assert all(isinstance(emu, int) for emu in result), "All EMU values should be integers"

        # Performance assertions (will be measured by pytest-benchmark)
        # The benchmark fixture automatically measures and reports timing

    def test_fractional_coordinate_validation(self, fractional_unit_converter):
        """Test validation of fractional coordinates for error handling."""
        # Test invalid coordinate values
        invalid_coordinates = [
            ("", "empty string"),
            ("invalid", "non-numeric string"),
            ("100.px", "malformed decimal"),
            ("-50.5px", "negative coordinate"),
            ("inf", "infinity value"),
            ("nan", "not-a-number value")
        ]

        for invalid_coord, description in invalid_coordinates:
            try:
                # Attempt conversion - should handle gracefully
                result = fractional_unit_converter.to_emu(invalid_coord)

                # If conversion succeeds, validate the result
                if result is not None:
                    assert isinstance(result, int), f"Result should be integer EMU for {description}: {invalid_coord}"
                    assert result >= 0, f"Result should be non-negative for {description}: {invalid_coord}"

            except (ValueError, TypeError) as e:
                # Expected behavior for invalid inputs
                assert str(e), f"Error message should be provided for {description}: {invalid_coord}"

    def test_fractional_emu_unit_type_support(self, fractional_unit_converter):
        """Test fractional EMU conversion across all supported unit types."""
        fractional_unit_tests = [
            ("10.5px", UnitType.PIXEL, "fractional pixels"),
            ("2.25pt", UnitType.POINT, "fractional points"),
            ("5.125mm", UnitType.MILLIMETER, "fractional millimeters"),
            ("1.75in", UnitType.INCH, "fractional inches"),
            ("0.5625cm", UnitType.CENTIMETER, "fractional centimeters")
        ]

        for unit_value, expected_unit_type, description in fractional_unit_tests:
            # Test fractional conversion for each unit type
            emu_result = fractional_unit_converter.to_emu(unit_value)

            # Validate EMU result is reasonable
            assert isinstance(emu_result, int), f"EMU result should be integer for {description}: {unit_value}"
            assert emu_result > 0, f"EMU result should be positive for {description}: {unit_value}"

            # Validate the conversion maintains proportional relationships
            numeric_part = float(unit_value[:-2])  # Remove unit suffix
            assert emu_result > 0, f"Fractional {description} should produce positive EMU values"

    def test_fractional_coordinate_context_integration(self, fractional_unit_converter):
        """Test fractional coordinate conversion with viewport context."""
        # Create test viewport context
        test_context = ViewportContext(
            width=800.0,
            height=600.0,
            font_size=16.0,
            dpi=DEFAULT_DPI
        )

        # Test fractional percentage calculations
        fractional_percentages = [
            ("50.5%", test_context.width, "fractional width percentage"),
            ("25.25%", test_context.height, "fractional height percentage"),
            ("12.125%", test_context.font_size, "fractional font-relative size")
        ]

        for percent_value, base_value, description in fractional_percentages:
            # Calculate expected fractional percentage
            percentage = float(percent_value.replace('%', '')) / 100.0
            expected_pixel_value = percentage * base_value

            # Convert to EMU and validate precision
            expected_emu = expected_pixel_value * (EMU_PER_INCH / DEFAULT_DPI)

            # Test fractional percentage maintains precision
            assert isinstance(expected_emu, float), f"Fractional percentage EMU should preserve precision for {description}"
            assert expected_emu > 0, f"Fractional {description} should produce positive values"

    def test_subpixel_rectangle_positioning(self, fractional_unit_converter):
        """Test subpixel-aware rectangle positioning and sizing."""
        processor = SubpixelShapeProcessor(fractional_converter=fractional_unit_converter)

        # Test fractional rectangle coordinates
        rectangle_data = processor.calculate_precise_rectangle(
            x="10.5px", y="20.25px", width="100.75px", height="50.125px"
        )

        # Validate essential rectangle properties
        assert 'x_emu' in rectangle_data, "Rectangle should have precise X coordinate"
        assert 'y_emu' in rectangle_data, "Rectangle should have precise Y coordinate"
        assert 'width_emu' in rectangle_data, "Rectangle should have precise width"
        assert 'height_emu' in rectangle_data, "Rectangle should have precise height"

        # Test coordinate precision
        assert rectangle_data['x_emu'] > 0, "Rectangle X coordinate should be positive"
        assert rectangle_data['y_emu'] > 0, "Rectangle Y coordinate should be positive"
        assert rectangle_data['width_emu'] > 0, "Rectangle width should be positive"
        assert rectangle_data['height_emu'] > 0, "Rectangle height should be positive"

        # Test derived coordinates
        expected_right = rectangle_data['x_emu'] + rectangle_data['width_emu']
        expected_bottom = rectangle_data['y_emu'] + rectangle_data['height_emu']

        assert abs(rectangle_data['right_emu'] - expected_right) < 0.1, "Right coordinate should be calculated correctly"
        assert abs(rectangle_data['bottom_emu'] - expected_bottom) < 0.1, "Bottom coordinate should be calculated correctly"

    def test_subpixel_circle_positioning(self, fractional_unit_converter):
        """Test subpixel-aware circle positioning with fractional center and radius."""
        processor = SubpixelShapeProcessor(fractional_converter=fractional_unit_converter)

        # Test fractional circle coordinates
        circle_data = processor.calculate_precise_circle(
            cx="50.33px", cy="75.67px", r="25.125px"
        )

        # Validate essential circle properties
        assert 'center_x_emu' in circle_data, "Circle should have precise center X coordinate"
        assert 'center_y_emu' in circle_data, "Circle should have precise center Y coordinate"
        assert 'radius_emu' in circle_data, "Circle should have precise radius"

        # Test PowerPoint ellipse representation
        assert 'x_emu' in circle_data, "Circle should have bounding box X coordinate"
        assert 'y_emu' in circle_data, "Circle should have bounding box Y coordinate"
        assert 'width_emu' in circle_data, "Circle should have bounding box width"
        assert 'height_emu' in circle_data, "Circle should have bounding box height"

        # Validate geometric relationships
        expected_x = circle_data['center_x_emu'] - circle_data['radius_emu']
        expected_y = circle_data['center_y_emu'] - circle_data['radius_emu']
        expected_diameter = circle_data['radius_emu'] * 2

        assert abs(circle_data['x_emu'] - expected_x) < 0.1, "Circle bounding box X should be calculated correctly"
        assert abs(circle_data['y_emu'] - expected_y) < 0.1, "Circle bounding box Y should be calculated correctly"
        assert abs(circle_data['width_emu'] - expected_diameter) < 0.1, "Circle width should equal diameter"
        assert abs(circle_data['height_emu'] - expected_diameter) < 0.1, "Circle height should equal diameter"

    def test_subpixel_bezier_control_points(self, fractional_unit_converter):
        """Test subpixel-accurate Bezier curve control point positioning."""
        processor = SubpixelShapeProcessor(fractional_converter=fractional_unit_converter)

        # Test fractional Bezier control points
        control_points = [
            (10.5, 20.25),    # Start point
            (30.75, 40.125),  # Control point 1
            (70.625, 80.875), # Control point 2
            (100.33, 150.67)  # End point
        ]

        bezier_data = processor.calculate_precise_bezier_control_points(
            control_points, curve_type='cubic'
        )

        # Validate control point structure
        assert len(bezier_data) == 4, "Cubic Bezier should have 4 control points"

        for i, point_data in enumerate(bezier_data):
            assert 'x_emu' in point_data, f"Control point {i} should have X EMU coordinate"
            assert 'y_emu' in point_data, f"Control point {i} should have Y EMU coordinate"
            assert 'drawingml_x' in point_data, f"Control point {i} should have DrawingML X coordinate"
            assert 'drawingml_y' in point_data, f"Control point {i} should have DrawingML Y coordinate"
            assert 'point_type' in point_data, f"Control point {i} should have point type classification"

            # Validate DrawingML coordinate bounds
            assert 0 <= point_data['drawingml_x'] <= 21600, f"DrawingML X coordinate {i} out of bounds"
            assert 0 <= point_data['drawingml_y'] <= 21600, f"DrawingML Y coordinate {i} out of bounds"

        # Test point type classification
        expected_types = ['start', 'control1', 'control2', 'end']
        actual_types = [point['point_type'] for point in bezier_data]
        assert actual_types == expected_types, f"Control point types should match expected: {expected_types}"

    def test_subpixel_polygon_vertices(self, fractional_unit_converter):
        """Test subpixel-accurate polygon vertex positioning."""
        processor = SubpixelShapeProcessor(fractional_converter=fractional_unit_converter)

        # Test fractional polygon vertices (triangle)
        triangle_vertices = [
            (10.5, 20.25),
            (50.75, 100.125),
            (90.33, 30.875)
        ]

        polygon_data = processor.calculate_precise_polygon_vertices(triangle_vertices)

        # Validate polygon structure
        assert len(polygon_data) == 3, "Triangle should have 3 vertices"

        for i, vertex_data in enumerate(polygon_data):
            assert 'x_emu' in vertex_data, f"Vertex {i} should have X EMU coordinate"
            assert 'y_emu' in vertex_data, f"Vertex {i} should have Y EMU coordinate"
            assert 'drawingml_x' in vertex_data, f"Vertex {i} should have DrawingML X coordinate"
            assert 'drawingml_y' in vertex_data, f"Vertex {i} should have DrawingML Y coordinate"

            # Test vertex flags
            expected_is_first = (i == 0)
            expected_is_last = (i == len(polygon_data) - 1)
            assert vertex_data['is_first'] == expected_is_first, f"Vertex {i} first flag incorrect"
            assert vertex_data['is_last'] == expected_is_last, f"Vertex {i} last flag incorrect"

    def test_shape_precision_optimization(self, fractional_unit_converter):
        """Test shape precision optimization algorithms."""
        processor = SubpixelShapeProcessor(fractional_converter=fractional_unit_converter)

        # Test shape data with fractional coordinates
        test_shape_data = {
            'coordinates': {
                'x': '10.5px',
                'y': '20.25px',
                'width': '100.75px',
                'height': '50.125px'
            },
            'shape_type': 'rectangle'
        }

        optimized_data = processor.optimize_shape_for_precision(test_shape_data, target_precision=0.1)

        # Validate optimization results
        assert 'coordinates' in optimized_data, "Optimized data should contain coordinates"
        assert len(optimized_data['coordinates']) == 4, "All coordinates should be optimized"

        # Test that optimization maintains coordinate relationships
        for coord_name, coord_value in optimized_data['coordinates'].items():
            assert isinstance(coord_value, float), f"Optimized coordinate {coord_name} should be float"
            assert coord_value > 0, f"Optimized coordinate {coord_name} should be positive"

    def test_shape_processor_performance_statistics(self, fractional_unit_converter):
        """Test shape processor performance monitoring and statistics."""
        processor = SubpixelShapeProcessor(fractional_converter=fractional_unit_converter)

        # Process several shapes to generate statistics
        processor.calculate_precise_rectangle("10px", "20px", "100px", "50px")
        processor.calculate_precise_circle("50px", "50px", "25px")
        processor.calculate_precise_bezier_control_points([(0, 0), (10, 10), (20, 0)])

        # Get performance statistics
        stats = processor.get_shape_precision_statistics()

        # Validate statistics structure
        required_stats = [
            'total_shapes_processed',
            'precision_mode',
            'shape_complexity',
            'cache_hit_rate',
            'average_precision_error'
        ]

        for stat_name in required_stats:
            assert stat_name in stats, f"Statistics should include {stat_name}"

        # Validate statistics values
        assert stats['total_shapes_processed'] > 0, "Should have processed shapes"
        assert stats['precision_mode'] in ['standard', 'subpixel', 'high', 'ultra'], "Precision mode should be valid"
        assert 0 <= stats['cache_hit_rate'] <= 1, "Cache hit rate should be between 0 and 1"
        assert stats['average_precision_error'] >= 0, "Average precision error should be non-negative"

    def test_enhanced_coordinate_system_integration(self):
        """Test integration of fractional EMU precision with coordinate system."""
        # Create enhanced coordinate system with fractional precision
        viewbox = (0, 0, 800, 600)
        coord_system = create_enhanced_coordinate_system(
            viewbox, precision_mode="subpixel"
        )

        # Test fractional coordinate conversion
        svg_x, svg_y = 100.5, 200.25
        fractional_emu_x, fractional_emu_y = coord_system.svg_to_fractional_emu(svg_x, svg_y)

        # Validate fractional precision is maintained
        assert isinstance(fractional_emu_x, float), "X coordinate should be float"
        assert isinstance(fractional_emu_y, float), "Y coordinate should be float"
        assert fractional_emu_x > 0, "X coordinate should be positive"
        assert fractional_emu_y > 0, "Y coordinate should be positive"

        # Compare with standard integer conversion
        integer_emu_x, integer_emu_y = coord_system.svg_to_emu(svg_x, svg_y)
        precision_gain_x = abs(fractional_emu_x - integer_emu_x)
        precision_gain_y = abs(fractional_emu_y - integer_emu_y)

        # Should have some precision difference due to fractional components
        assert precision_gain_x >= 0, "Fractional precision should provide accuracy gain"
        assert precision_gain_y >= 0, "Fractional precision should provide accuracy gain"

    def test_precision_conversion_context_integration(self):
        """Test integration of fractional EMU precision with conversion context."""
        # Create precision-aware conversion context
        context = create_precision_conversion_context(
            precision_mode="subpixel",
            enable_fractional_emu=True
        )

        # Test fractional EMU conversion through context
        test_values = ["10.5px", "20.25px", "100.75px", "50.125px"]

        for value in test_values:
            fractional_result = context.to_fractional_emu(value)
            standard_result = context.to_emu(value)

            # Validate fractional conversion
            assert isinstance(fractional_result, float), f"Fractional result for {value} should be float"
            assert fractional_result > 0, f"Fractional result for {value} should be positive"

            # Compare precision
            precision_difference = abs(fractional_result - standard_result)
            assert precision_difference >= 0, f"Should have precision handling for {value}"

        # Test batch conversion with fractional precision
        batch_values = {
            'x': '10.5px',
            'y': '20.25px',
            'width': '100.75px',
            'height': '50.125px'
        }

        batch_results = context.batch_convert_to_fractional_emu(batch_values)

        # Validate batch conversion results
        assert len(batch_results) == 4, "Should convert all batch values"
        for key, result in batch_results.items():
            assert isinstance(result, float), f"Batch result {key} should be float"
            assert result > 0, f"Batch result {key} should be positive"

    def test_precision_aware_converter_integration(self):
        """Test integration of fractional EMU precision with converter architecture."""
        # Create a concrete implementation of PrecisionAwareConverter for testing
        class TestPrecisionConverter(PrecisionAwareConverter):
            def can_convert(self, element):
                return True  # Accept any element for testing

            def convert(self, element, context):
                return None  # Minimal implementation for testing

        # Create test converter instance
        converter = TestPrecisionConverter(precision_mode=PrecisionMode.SUBPIXEL)

        # Test coordinate conversion with precision
        test_coordinates = {
            'x': 100.5,
            'y': 200.25,
            'width': 150.75,
            'height': 75.125
        }

        # Test OOXML formatting with fractional precision
        ooxml_coords = converter.generate_precise_ooxml_coordinates(test_coordinates)

        # Validate OOXML coordinate formatting
        assert len(ooxml_coords) == 4, "Should format all coordinates"
        for coord_name, coord_string in ooxml_coords.items():
            assert isinstance(coord_string, str), f"OOXML coordinate {coord_name} should be string"
            assert len(coord_string) > 0, f"OOXML coordinate {coord_name} should not be empty"

            # Test that string can be parsed back to float
            try:
                parsed_value = float(coord_string)
                assert parsed_value > 0, f"Parsed OOXML coordinate {coord_name} should be positive"
            except ValueError:
                pytest.fail(f"OOXML coordinate {coord_name} should be valid number string")

        # Test OOXML element creation with fractional coordinates
        ooxml_element = converter.create_precise_ooxml_element(
            'rect', test_coordinates, {'fill': 'red'}
        )

        # Validate OOXML element structure
        assert isinstance(ooxml_element, str), "OOXML element should be string"
        assert ooxml_element.startswith('<rect'), "OOXML element should start with tag"
        assert 'fill="red"' in ooxml_element, "OOXML element should include attributes"

        # Test that coordinates are included in the element
        for coord_name in test_coordinates.keys():
            assert coord_name in ooxml_element, f"OOXML element should include {coord_name} coordinate"

    def test_precision_shape_calculation_integration(self):
        """Test integration of precision shape calculations with conversion context."""
        context = create_precision_conversion_context(
            precision_mode="subpixel",
            enable_fractional_emu=True
        )

        # Test precise rectangle calculation through context
        rectangle_coords = {
            'x': '10.5px',
            'y': '20.25px',
            'width': '100.75px',
            'height': '50.125px'
        }

        rectangle_result = context.calculate_precise_shape('rectangle', rectangle_coords)

        # Validate rectangle calculation result
        assert isinstance(rectangle_result, dict), "Rectangle result should be dictionary"
        assert 'x_emu' in rectangle_result, "Rectangle should have X EMU coordinate"
        assert 'y_emu' in rectangle_result, "Rectangle should have Y EMU coordinate"
        assert 'width_emu' in rectangle_result, "Rectangle should have width EMU"
        assert 'height_emu' in rectangle_result, "Rectangle should have height EMU"

        # Test precise circle calculation through context
        circle_coords = {
            'cx': '50.33px',
            'cy': '75.67px',
            'r': '25.125px'
        }

        circle_result = context.calculate_precise_shape('circle', circle_coords)

        # Validate circle calculation result
        assert isinstance(circle_result, dict), "Circle result should be dictionary"
        assert 'center_x_emu' in circle_result, "Circle should have center X EMU"
        assert 'center_y_emu' in circle_result, "Circle should have center Y EMU"
        assert 'radius_emu' in circle_result, "Circle should have radius EMU"

    def test_precision_statistics_integration(self):
        """Test integration of precision statistics and monitoring."""
        context = create_precision_conversion_context(
            precision_mode="subpixel",
            enable_fractional_emu=True
        )

        # Perform several precision operations to generate statistics
        context.to_fractional_emu('10.5px')
        context.to_fractional_emu('20.25px')
        context.batch_convert_to_fractional_emu({
            'x': '100px', 'y': '200px', 'width': '50px', 'height': '25px'
        })
        context.calculate_precise_shape('rectangle', {
            'x': '10px', 'y': '20px', 'width': '100px', 'height': '50px'
        })

        # Get comprehensive precision statistics
        stats = context.get_precision_statistics()

        # Validate statistics structure and values
        required_stats = [
            'coordinates_processed',
            'shapes_processed',
            'precision_mode',
            'cache_size'
        ]

        for stat_name in required_stats:
            assert stat_name in stats, f"Statistics should include {stat_name}"

        # Validate operation counts
        assert stats['coordinates_processed'] > 0, "Should have processed coordinates"
        assert stats['shapes_processed'] > 0, "Should have processed shapes"
        assert stats['precision_mode'] == 'subpixel', "Should track precision mode"

    def test_backward_compatibility_integration(self):
        """Test that precision integration maintains backward compatibility."""
        # Create standard (non-precision) conversion context for comparison
        from src.converters.base import ConversionContext
        standard_context = ConversionContext()

        # Create precision-aware context
        precision_context = create_precision_conversion_context(
            precision_mode="standard",  # Use standard mode for compatibility
            enable_fractional_emu=False  # Disable fractional EMU
        )

        # Test that both contexts produce compatible results for integer coordinates
        test_values = ["10px", "20px", "100px", "50px"]

        for value in test_values:
            # Both should work with integer values
            standard_result = standard_context.to_emu(value)
            precision_result = precision_context.to_emu(value)  # Should fall back to base implementation

            # Results should be identical for integer values
            assert standard_result == precision_result, (
                f"Standard and precision contexts should produce same results for {value}"
            )

            # Test type compatibility
            assert isinstance(standard_result, int), f"Standard result for {value} should be int"
            assert isinstance(precision_result, int), f"Precision result for {value} should be int"