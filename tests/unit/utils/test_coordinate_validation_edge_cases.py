#!/usr/bin/env python3
"""
Test suite for coordinate validation and error handling edge cases.

Tests comprehensive edge case handling, error recovery mechanisms,
and validation logic for the fractional EMU precision system.
"""

import pytest
import math
from decimal import Decimal
from typing import Dict, Any

from src.fractional_emu import (
    FractionalEMUConverter, PrecisionMode, FractionalCoordinateContext,
    CoordinateValidationError, PrecisionOverflowError, EMUBoundaryError
)
from src.subpixel_shapes import SubpixelShapeProcessor, SubpixelShapeContext
from src.units import ViewportContext, DEFAULT_DPI


class TestCoordinateValidationEdgeCases:
    """Test coordinate validation and error handling edge cases."""

    @pytest.fixture
    def fractional_converter(self):
        """Create fractional EMU converter for testing."""
        return FractionalEMUConverter(
            precision_mode=PrecisionMode.SUBPIXEL,
            default_dpi=DEFAULT_DPI
        )

    @pytest.fixture
    def shape_processor(self):
        """Create subpixel shape processor for testing."""
        context = SubpixelShapeContext(
            viewport_context=ViewportContext(width=800, height=600),
            precision_mode=PrecisionMode.SUBPIXEL
        )
        return SubpixelShapeProcessor(context=context)

    def test_none_value_validation(self, fractional_converter):
        """Test validation of None input values returns fallback."""
        result = fractional_converter.to_fractional_emu(None)
        # Should return fallback value instead of raising exception
        assert result == 0.0

    def test_empty_string_validation(self, fractional_converter):
        """Test validation of empty string inputs returns fallback."""
        result1 = fractional_converter.to_fractional_emu("")
        result2 = fractional_converter.to_fractional_emu("   ")
        # Should return fallback values instead of raising exception
        assert result1 == 0.0
        assert result2 == 0.0

    def test_oversized_string_validation(self, fractional_converter):
        """Test validation of excessively long coordinate strings returns fallback."""
        oversized_string = "1" * 101 + "px"  # 101+ characters
        result = fractional_converter.to_fractional_emu(oversized_string)
        # Should return fallback value instead of raising exception
        assert result == 0.0

    @pytest.mark.parametrize("invalid_value,description", [
        (float('inf'), "positive infinity"),
        (float('-inf'), "negative infinity"),
        (float('nan'), "not a number")
    ])
    def test_non_finite_value_validation(self, fractional_converter, invalid_value, description):
        """Test validation of non-finite numeric values returns fallback."""
        result = fractional_converter.to_fractional_emu(invalid_value)
        # Should return fallback value instead of raising exception
        assert result == 0.0

    def test_extreme_coordinate_values(self, fractional_converter):
        """Test handling of extremely large coordinate values."""
        # Test coordinate exceeding maximum allowed value
        extreme_value = 1e11  # Exceeds coordinate_max_value (1e10)
        result = fractional_converter.to_fractional_emu(extreme_value)
        # Should return fallback value instead of raising exception
        assert result == 0.0

    def test_precision_overflow_detection(self, fractional_converter):
        """Test detection and handling of precision calculation overflow."""
        # Use ultra precision mode to trigger overflow more easily
        ultra_converter = FractionalEMUConverter(
            precision_mode=PrecisionMode.ULTRA_PRECISION
        )

        # Value that might cause overflow when multiplied by precision factor
        large_value = 1e12
        result = ultra_converter.to_fractional_emu(large_value)
        # Should return fallback value instead of raising exception
        assert result == 0.0

    def test_batch_coordinate_validation_errors(self, fractional_converter):
        """Test batch coordinate conversion with validation errors."""
        invalid_coordinates = {
            "valid_x": "100px",
            "invalid_none": None,
            "invalid_empty": "",
            "invalid_inf": float('inf'),
            "valid_y": "200px"
        }

        # Should not raise exception but handle errors gracefully
        result = fractional_converter.batch_convert_coordinates(invalid_coordinates)

        # Valid coordinates should be converted
        assert "valid_x" in result
        assert "valid_y" in result
        assert result["valid_x"] > 0
        assert result["valid_y"] > 0

        # Invalid coordinates should get fallback values
        assert "invalid_none" in result
        assert "invalid_empty" in result
        assert "invalid_inf" in result
        assert result["invalid_none"] == 0.0  # Fallback value
        assert result["invalid_empty"] == 0.0  # Fallback value
        assert result["invalid_inf"] == 0.0  # Fallback value

    def test_batch_size_validation(self, fractional_converter):
        """Test validation of batch processing size limits."""
        # Create oversized batch (> 1000 coordinates) - this should raise exception
        oversized_batch = {f"coord_{i}": "10px" for i in range(1001)}

        with pytest.raises(CoordinateValidationError, match="Batch size too large"):
            fractional_converter.batch_convert_coordinates(oversized_batch)

    def test_invalid_batch_input_type(self, fractional_converter):
        """Test validation of batch input type."""
        with pytest.raises(CoordinateValidationError, match="must be a dictionary"):
            fractional_converter.batch_convert_coordinates("not a dict")

    def test_drawingml_coordinate_validation(self, fractional_converter):
        """Test DrawingML coordinate conversion validation."""
        # Test division by zero protection - should return fallback coordinates
        result1 = fractional_converter.to_precise_drawingml_coords(100, 100, 0, 100)
        result2 = fractional_converter.to_precise_drawingml_coords(100, 100, 100, 0)

        # Should return safe fallback coordinates
        assert result1 == (0.0, 0.0)
        assert result2 == (0.0, 0.0)

        # Test with invalid input types - should return fallback coordinates
        result3 = fractional_converter.to_precise_drawingml_coords("invalid", 100, 100, 100)
        assert result3 == (0.0, 0.0)

    def test_shape_input_validation(self, shape_processor):
        """Test shape input parameter validation."""
        # Test that invalid shapes return fallback values gracefully
        result1 = shape_processor.calculate_precise_rectangle(x=None, y=20, width=30, height=40)
        result2 = shape_processor.calculate_precise_rectangle(x=10, y=20, width=-30, height=40)

        # Should return fallback rectangle with valid dimensions
        assert isinstance(result1, dict)
        assert isinstance(result2, dict)
        assert all(key in result1 for key in ['x_emu', 'y_emu', 'width_emu', 'height_emu'])
        assert all(key in result2 for key in ['x_emu', 'y_emu', 'width_emu', 'height_emu'])
        assert all(math.isfinite(value) for value in result1.values())
        assert all(math.isfinite(value) for value in result2.values())

    def test_emu_boundary_validation(self, fractional_converter):
        """Test EMU boundary validation and clamping."""
        # Test value exceeding PowerPoint maximum
        max_value = fractional_converter.powerpoint_max_emu + 1000
        result = fractional_converter.to_fractional_emu(max_value)

        # Should be clamped to maximum
        assert result <= fractional_converter.powerpoint_max_emu

        # Test negative values
        negative_result = fractional_converter.to_fractional_emu(-100)
        assert negative_result >= 0.0  # Should be clamped to 0

    def test_decimal_precision_validation(self):
        """Test decimal precision validation for PowerPoint compatibility."""
        context = FractionalCoordinateContext(max_decimal_places=3)
        converter = FractionalEMUConverter(
            precision_mode=PrecisionMode.SUBPIXEL,
            fractional_context=context
        )

        # Test value with many decimal places
        precise_value = 123.123456789
        result = converter.to_fractional_emu(precise_value)

        # Should be rounded to 3 decimal places maximum
        decimal_places = len(str(result).split('.')[-1]) if '.' in str(result) else 0
        assert decimal_places <= 3

    def test_error_recovery_mechanisms(self, fractional_converter):
        """Test error recovery and fallback mechanisms."""
        # Test fallback for parsing errors
        result = fractional_converter.to_fractional_emu("invalid_unit_xyz")
        assert isinstance(result, float)
        assert result >= 0.0  # Should provide safe fallback

        # Test fallback for extreme values
        extreme_string = f"{1e20}px"  # Extremely large value
        result = fractional_converter.to_fractional_emu(extreme_string)
        assert isinstance(result, float)
        assert math.isfinite(result)

    def test_validation_error_messages(self, fractional_converter, caplog):
        """Test that validation errors provide informative log messages."""
        # Clear any previous log records
        caplog.clear()

        # Test None value error logging
        fractional_converter.to_fractional_emu(None)
        assert any("cannot be None" in record.message for record in caplog.records)

        # Test empty string error logging
        caplog.clear()
        fractional_converter.to_fractional_emu("")
        assert any("cannot be empty" in record.message for record in caplog.records)

        # Test non-finite error logging
        caplog.clear()
        fractional_converter.to_fractional_emu(float('nan'))
        assert any("not finite" in record.message for record in caplog.records)

    def test_shape_validation_error_recovery(self, shape_processor):
        """Test error recovery in shape calculations."""
        # Test rectangle calculation with invalid inputs
        result = shape_processor.calculate_precise_rectangle(
            x=float('nan'), y=20, width=30, height=40
        )

        # Should return fallback rectangle
        assert isinstance(result, dict)
        assert all(key in result for key in ['x_emu', 'y_emu', 'width_emu', 'height_emu'])
        assert all(math.isfinite(value) for value in result.values())

    def test_logging_integration(self, fractional_converter, caplog):
        """Test that errors are properly logged."""
        # Clear any previous log records
        caplog.clear()

        # Test that validation errors are logged - use None which definitely causes error
        fractional_converter.to_fractional_emu(None)

        # Check that error was logged
        assert len(caplog.records) > 0
        assert any("conversion failed" in record.message.lower() for record in caplog.records)

    def test_cache_behavior_with_errors(self, fractional_converter):
        """Test caching behavior when errors occur."""
        # Clear cache first
        fractional_converter.clear_cache()

        # Test that error cases don't pollute cache
        initial_cache_size = len(fractional_converter.fractional_cache)

        # Attempt conversion with invalid value
        fractional_converter.to_fractional_emu("invalid_value")

        # Cache should not grow from error cases
        final_cache_size = len(fractional_converter.fractional_cache)
        assert final_cache_size <= initial_cache_size + 1  # At most one entry for fallback


@pytest.mark.precision
class TestAdvancedValidationScenarios:
    """Test advanced validation scenarios and edge cases."""

    def test_concurrent_validation_errors(self):
        """Test handling of multiple concurrent validation errors."""
        converter = FractionalEMUConverter()

        # Batch with multiple error types
        error_batch = {
            "none_value": None,
            "empty_string": "",
            "infinite_value": float('inf'),
            "oversized_string": "x" * 200,
            "valid_coord": "100px"
        }

        result = converter.batch_convert_coordinates(error_batch)

        # Should handle all errors gracefully
        assert len(result) == 5
        assert result["valid_coord"] > 0
        assert all(math.isfinite(value) for value in result.values())

    def test_precision_mode_validation_differences(self):
        """Test validation behavior across different precision modes."""
        modes = [PrecisionMode.STANDARD, PrecisionMode.SUBPIXEL,
                PrecisionMode.HIGH_PRECISION, PrecisionMode.ULTRA_PRECISION]

        test_value = 1000.123456789

        for mode in modes:
            converter = FractionalEMUConverter(precision_mode=mode)
            result = converter.to_fractional_emu(test_value)

            # All modes should produce valid results
            assert math.isfinite(result)
            assert result > 0

    def test_context_dependent_validation(self):
        """Test validation that depends on viewport context."""
        small_context = ViewportContext(width=10, height=10)
        large_context = ViewportContext(width=10000, height=10000)

        converter = FractionalEMUConverter()

        # Same relative value should validate differently in different contexts
        relative_value = "50%"

        small_result = converter.to_fractional_emu(relative_value, small_context)
        large_result = converter.to_fractional_emu(relative_value, large_context)

        # Both should be valid but different
        assert math.isfinite(small_result)
        assert math.isfinite(large_result)
        assert small_result != large_result

    def test_validation_performance_under_load(self):
        """Test validation performance with large batches."""
        converter = FractionalEMUConverter()

        # Create large valid batch
        large_batch = {f"coord_{i}": f"{i}px" for i in range(500)}

        # Should complete without timeout or memory issues
        result = converter.batch_convert_coordinates(large_batch)

        assert len(result) == 500
        assert all(math.isfinite(value) for value in result.values())

    def test_nested_error_scenarios(self):
        """Test complex nested error scenarios."""
        context = SubpixelShapeContext(
            viewport_context=ViewportContext(width=800, height=600)
        )
        processor = SubpixelShapeProcessor(context=context)

        # Test shape with multiple levels of invalid data
        result = processor.calculate_precise_rectangle(
            x="invalid", y=float('inf'), width=-100, height="also_invalid"
        )

        # Should recover gracefully
        assert isinstance(result, dict)
        assert all(math.isfinite(value) for value in result.values())