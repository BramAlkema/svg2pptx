#!/usr/bin/env python3
"""
Comprehensive tests for NumPy-based Fractional EMU system.
"""

import pytest
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.fractional_emu_numpy import (
    NumPyFractionalEMU, PrecisionMode, UnitType,
    create_converter, batch_convert_to_emu, convert_svg_viewbox_to_emu,
    EMU_PER_INCH, EMU_PER_POINT, EMU_PER_MM, EMU_PER_CM,
    POWERPOINT_MAX_EMU
)


class TestNumPyFractionalEMU:
    """Test NumPy fractional EMU converter."""

    def test_initialization(self):
        """Test converter initialization."""
        converter = NumPyFractionalEMU()
        assert converter.precision_mode == PrecisionMode.SUBPIXEL
        assert converter.precision_factor == 100.0
        assert converter.default_dpi == 96.0

        # Test with different precision modes
        converter_high = NumPyFractionalEMU(precision_mode=PrecisionMode.HIGH)
        assert converter_high.precision_factor == 1000.0

    def test_basic_pixel_conversion(self):
        """Test basic pixel to EMU conversion."""
        converter = NumPyFractionalEMU(precision_mode=PrecisionMode.STANDARD)

        # Single value
        coords = np.array([100.0])
        units = np.array([UnitType.PIXEL])
        emu = converter.batch_to_emu(coords, units, preserve_precision=False)

        expected = 100.0 * (EMU_PER_INCH / 96.0)
        np.testing.assert_allclose(emu, [expected], rtol=1e-10)

    def test_batch_conversion_multiple_units(self):
        """Test batch conversion with different unit types."""
        converter = NumPyFractionalEMU(precision_mode=PrecisionMode.STANDARD)

        coords = np.array([100.0, 72.0, 10.0, 1.0, 1.0])
        units = np.array([
            UnitType.PIXEL,
            UnitType.POINT,
            UnitType.MM,
            UnitType.CM,
            UnitType.INCH
        ])

        emu = converter.batch_to_emu(coords, units, preserve_precision=False)

        expected = np.array([
            100.0 * (EMU_PER_INCH / 96.0),
            72.0 * EMU_PER_POINT,
            10.0 * EMU_PER_MM,
            1.0 * EMU_PER_CM,
            1.0 * EMU_PER_INCH
        ])

        np.testing.assert_allclose(emu, expected, rtol=1e-10)

    def test_precision_modes(self):
        """Test different precision modes."""
        coords = np.array([1.0])
        units = np.array([UnitType.PIXEL])

        # Standard precision
        conv_standard = NumPyFractionalEMU(precision_mode=PrecisionMode.STANDARD)
        emu_standard = conv_standard.batch_to_emu(coords, units)

        # Subpixel precision (100x)
        conv_subpixel = NumPyFractionalEMU(precision_mode=PrecisionMode.SUBPIXEL)
        emu_subpixel = conv_subpixel.batch_to_emu(coords, units)

        assert emu_subpixel[0] == emu_standard[0] * 100.0

        # High precision (1000x)
        conv_high = NumPyFractionalEMU(precision_mode=PrecisionMode.HIGH)
        emu_high = conv_high.batch_to_emu(coords, units)

        assert emu_high[0] == emu_standard[0] * 1000.0

    def test_rounding_precision(self):
        """Test precision rounding for PowerPoint compatibility."""
        converter = NumPyFractionalEMU()

        values = np.array([
            123.456789,
            987.654321,
            0.123456,
            1234567.89
        ])

        # Round to 3 decimal places (PowerPoint max)
        rounded = converter.round_precision(values, decimal_places=3)

        expected = np.array([123.457, 987.654, 0.123, 1234567.890])
        np.testing.assert_allclose(rounded, expected, rtol=1e-10)

    def test_validation_and_clamping(self):
        """Test EMU value validation and clamping."""
        converter = NumPyFractionalEMU()

        # Test with invalid values
        coords = np.array([
            -100.0,  # Negative
            1e12,    # Too large
            np.nan,  # NaN
            np.inf,  # Infinity
            100.0    # Valid
        ])
        units = np.full(5, UnitType.PIXEL)

        with pytest.warns(UserWarning, match="Non-finite EMU values"):
            emu = converter.batch_to_emu(coords, units, preserve_precision=False)

        # Check clamping
        assert emu[0] == 0.0  # Negative clamped to 0
        assert emu[1] == POWERPOINT_MAX_EMU  # Large value clamped
        assert emu[2] == 0.0  # NaN converted to 0
        assert emu[3] == 0.0  # Inf converted to 0
        assert emu[4] > 0  # Valid value preserved

    def test_2d_coordinate_arrays(self):
        """Test conversion of 2D coordinate arrays."""
        converter = NumPyFractionalEMU()

        # 2D array of x,y coordinate pairs
        coords = np.array([
            [100.0, 200.0],
            [150.0, 250.0],
            [200.0, 300.0]
        ])
        units = np.full_like(coords, UnitType.PIXEL, dtype=np.int32)

        emu = converter.batch_to_emu(coords, units, preserve_precision=False)

        assert emu.shape == coords.shape
        assert np.all(emu > 0)

    def test_viewbox_conversion(self):
        """Test SVG viewBox to EMU conversion."""
        x, y, width, height = convert_svg_viewbox_to_emu(
            10.5, 20.75, 100.25, 200.125,
            unit_type=UnitType.PIXEL,
            dpi=96.0
        )

        assert isinstance(x, int)
        assert isinstance(y, int)
        assert isinstance(width, int)
        assert isinstance(height, int)
        assert all(val > 0 for val in [x, y, width, height])

    def test_transform_operations(self):
        """Test coordinate transformation operations."""
        converter = NumPyFractionalEMU()

        # Create test coordinates
        coords = np.array([
            [0, 0],
            [100, 0],
            [100, 100],
            [0, 100]
        ], dtype=np.float64)

        # Create transform matrix (scale by 2, translate by 50)
        transform = converter.create_transform_matrix(
            scale=2.0,
            translate_x=50.0,
            translate_y=25.0
        )

        # Apply transformation
        transformed = converter.apply_transform_batch(coords, transform)

        expected = np.array([
            [50, 25],
            [250, 25],
            [250, 225],
            [50, 225]
        ])

        np.testing.assert_allclose(transformed, expected, rtol=1e-10)

    def test_coordinate_optimization(self):
        """Test coordinate stream optimization."""
        converter = NumPyFractionalEMU()

        # Create coordinates with some redundant precision
        coords = np.array([
            100.0,
            100.05,  # Very small change
            100.1,   # Still small
            150.0,   # Significant change
            150.02,  # Small change
            200.0    # Significant change
        ])

        optimized, mask = converter.optimize_coordinate_stream(coords, tolerance=1.0)

        # Should keep significant changes only
        assert len(optimized) < len(coords)
        assert optimized[0] == 100.0
        assert 150.0 in optimized
        assert 200.0 in optimized

    def test_parallel_path_processing(self):
        """Test parallel processing of multiple paths."""
        converter = NumPyFractionalEMU()

        # Create multiple paths
        path1 = np.array([[0, 0], [100, 100]])
        path2 = np.array([[50, 50], [150, 150], [200, 100]])
        path3 = np.array([[25, 25]])

        paths = [path1, path2, path3]

        # Process in parallel
        emu_paths = converter.parallel_process_paths(
            paths,
            unit_type=UnitType.PIXEL,
            dpi=96.0
        )

        assert len(emu_paths) == len(paths)
        assert emu_paths[0].shape == path1.shape
        assert emu_paths[1].shape == path2.shape
        assert emu_paths[2].shape == path3.shape

    def test_performance_benchmark(self):
        """Test performance benchmarking."""
        converter = NumPyFractionalEMU()

        metrics = converter.benchmark_performance(n_coords=10000)

        assert 'coords_per_second' in metrics
        assert metrics['coords_per_second'] > 1000000  # Should process >1M coords/sec
        assert metrics['conversion_rate_millions'] > 1.0
        assert metrics['n_coordinates'] == 10000

    def test_memory_efficiency(self):
        """Test memory usage reporting."""
        converter = NumPyFractionalEMU()

        memory_info = converter.get_memory_usage()

        assert 'total_bytes' in memory_info
        assert memory_info['total_bytes'] > 0
        assert memory_info['precision_mode'] == 'SUBPIXEL'

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        converter = NumPyFractionalEMU()

        # Empty array
        empty = np.array([])
        units = np.array([], dtype=np.int32)
        result = converter.batch_to_emu(empty, units)
        assert len(result) == 0

        # Single value
        single = np.array([42.0])
        units = np.array([UnitType.POINT])
        result = converter.batch_to_emu(single, units)
        assert len(result) == 1

        # Very large array
        large = np.random.uniform(0, 100, 100000)
        units = np.full(100000, UnitType.PIXEL, dtype=np.int32)
        result = converter.batch_to_emu(large, units)
        assert len(result) == 100000

    def test_convenience_functions(self):
        """Test convenience functions."""
        # Test create_converter
        conv = create_converter(PrecisionMode.HIGH)
        assert conv.precision_mode == PrecisionMode.HIGH

        # Test batch_convert_to_emu
        coords = np.array([100, 200, 300])
        emu = batch_convert_to_emu(coords, UnitType.PIXEL, dpi=96.0)
        assert len(emu) == 3
        assert np.all(emu > 0)

    def test_unit_broadcasting(self):
        """Test unit type broadcasting for uniform conversions."""
        converter = NumPyFractionalEMU()

        # Many coordinates, single unit type
        coords = np.random.uniform(0, 100, (100, 2))
        single_unit = np.array([UnitType.PIXEL])

        # Should broadcast the single unit to all coordinates
        emu = converter.batch_to_emu(coords, single_unit)
        assert emu.shape == coords.shape

    def test_mixed_precision_comparison(self):
        """Compare results between different precision modes."""
        # Use a smaller coordinate that won't exceed PowerPoint limits when scaled
        coords = np.array([1.0])  # 1mm = 36,000 EMU, safe for 1000x scaling
        units = np.array([UnitType.MM])

        # Get results with different precisions
        conv_standard = NumPyFractionalEMU(precision_mode=PrecisionMode.STANDARD)
        conv_high = NumPyFractionalEMU(precision_mode=PrecisionMode.HIGH)

        emu_standard = conv_standard.batch_to_emu(coords, units, preserve_precision=False)
        emu_high = conv_high.batch_to_emu(coords, units, preserve_precision=False)

        # Without precision factor, results should be identical
        np.testing.assert_allclose(emu_standard, emu_high, rtol=1e-10)

        # With precision factor
        emu_standard_prec = conv_standard.batch_to_emu(coords, units, preserve_precision=True)
        emu_high_prec = conv_high.batch_to_emu(coords, units, preserve_precision=True)

        # High precision should be 1000x standard (1000/1)
        np.testing.assert_allclose(emu_high_prec[0], emu_standard_prec[0] * 1000.0, rtol=1e-10)

    def test_advanced_rounding_methods(self):
        """Test advanced rounding methods."""
        converter = NumPyFractionalEMU()

        # Test values with known rounding expectations
        test_values = np.array([12.345, 12.355, 12.365, 12.375])

        # Test different rounding methods
        nearest = converter.advanced_round(test_values, method='nearest', decimal_places=2)
        floor_result = converter.advanced_round(test_values, method='floor', decimal_places=2)
        ceil_result = converter.advanced_round(test_values, method='ceil', decimal_places=2)
        truncate = converter.advanced_round(test_values, method='truncate', decimal_places=2)
        banker = converter.advanced_round(test_values, method='banker', decimal_places=2)

        # Verify results (NumPy uses "round half to even" by default)
        expected_nearest = np.array([12.34, 12.36, 12.36, 12.38])  # Round half to even
        expected_floor = np.array([12.34, 12.35, 12.36, 12.37])
        expected_ceil = np.array([12.35, 12.36, 12.37, 12.38])
        expected_truncate = np.array([12.34, 12.35, 12.36, 12.37])

        np.testing.assert_allclose(nearest, expected_nearest, rtol=1e-10)
        np.testing.assert_allclose(floor_result, expected_floor, rtol=1e-10)
        np.testing.assert_allclose(ceil_result, expected_ceil, rtol=1e-10)
        np.testing.assert_allclose(truncate, expected_truncate, rtol=1e-10)

        # Banker's rounding test
        assert len(banker) == len(test_values)

    def test_grid_quantization(self):
        """Test grid quantization functionality."""
        converter = NumPyFractionalEMU()

        # Test values
        emu_values = np.array([1023.7, 2048.1, 3072.9, 4095.2])

        # Quantize to 512 EMU grid
        grid_size = 512.0
        quantized = converter.quantize_to_grid(emu_values, grid_size)

        # Results should be multiples of grid size
        expected = np.array([1024.0, 2048.0, 3072.0, 4096.0])
        np.testing.assert_allclose(quantized, expected, rtol=1e-10)

        # Verify all results are grid-aligned
        assert np.all(quantized % grid_size == 0)

    def test_adaptive_precision_rounding(self):
        """Test adaptive precision rounding."""
        converter = NumPyFractionalEMU()

        # Test values of different magnitudes
        values = np.array([0.123456, 12.3456, 123.456, 1234.56, 12345.6])

        rounded = converter.adaptive_precision_round(values)

        # Should round each value appropriately based on magnitude
        assert len(rounded) == len(values)
        assert np.all(np.isfinite(rounded))

    def test_smart_quantization_modes(self):
        """Test smart quantization for different quality levels."""
        converter = NumPyFractionalEMU()

        test_values = np.array([123.456789, 456.789123, 789.123456])

        # Test different quality modes
        low_quality = converter.smart_quantization(test_values, 'low')
        medium_quality = converter.smart_quantization(test_values, 'medium')
        high_quality = converter.smart_quantization(test_values, 'high')
        ultra_quality = converter.smart_quantization(test_values, 'ultra')

        # Low quality should be integers
        assert np.all(low_quality == np.round(test_values))

        # Medium quality should have 1 decimal place
        expected_medium = np.array([123.5, 456.8, 789.1])
        np.testing.assert_allclose(medium_quality, expected_medium, rtol=1e-10)

        # High quality should have 3 decimal places
        expected_high = np.array([123.457, 456.789, 789.123])
        np.testing.assert_allclose(high_quality, expected_high, rtol=1e-10)

        # All results should be finite
        assert np.all(np.isfinite(ultra_quality))

    def test_tolerance_based_rounding(self):
        """Test rounding with tolerance threshold."""
        converter = NumPyFractionalEMU()

        # Values with small and large deviations
        test_values = np.array([100.001, 100.5, 200.002, 200.7])
        tolerance = 0.1

        result = converter.batch_round_with_tolerance(test_values, tolerance)

        # Small deviations should be preserved, large ones rounded
        # 100.001 -> preserved (change < 0.1)
        # 100.5 -> rounded (change >= 0.1)
        # 200.002 -> preserved (change < 0.1)
        # 200.7 -> rounded (change >= 0.1)

        assert len(result) == len(test_values)
        assert np.all(np.isfinite(result))

    def test_rounding_error_handling(self):
        """Test error handling in rounding methods."""
        converter = NumPyFractionalEMU()

        test_values = np.array([100.0, 200.0])

        # Test invalid rounding method
        with pytest.raises(ValueError, match="Unknown rounding method"):
            converter.advanced_round(test_values, method='invalid')

        # Test invalid resolution
        with pytest.raises(ValueError, match="Unknown target resolution"):
            converter.smart_quantization(test_values, 'invalid')


if __name__ == "__main__":
    print("Running NumPy Fractional EMU tests...")
    pytest.main([__file__, "-v"])