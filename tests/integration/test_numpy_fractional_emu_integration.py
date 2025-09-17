#!/usr/bin/env python3
"""
Integration tests for NumPy Fractional EMU system with the main codebase.
"""

import pytest
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.fractional_emu_numpy import (
    NumPyFractionalEMU, PrecisionMode, UnitType,
    create_converter, batch_convert_to_emu, convert_svg_viewbox_to_emu,
    EMU_PER_INCH, EMU_PER_POINT
)


class TestNumPyFractionalEMUIntegration:
    """Integration tests for NumPy fractional EMU system."""

    def test_svg_coordinate_processing_pipeline(self):
        """Test typical SVG coordinate processing pipeline."""
        converter = create_converter(PrecisionMode.HIGH)

        # Simulate SVG coordinate data
        svg_coords = {
            'x': [10.5, 20.75, 30.125],
            'y': [15.25, 25.5, 35.875],
            'width': [100.0, 200.0, 300.0],
            'height': [50.0, 75.0, 100.0]
        }

        # Convert each coordinate type
        results = {}
        for coord_type, values in svg_coords.items():
            coords = np.array(values)
            units = np.full(len(coords), UnitType.PIXEL)
            emu_values = converter.batch_to_emu(coords, units)
            results[coord_type] = emu_values

            # Verify all results are valid
            assert np.all(np.isfinite(emu_values))
            assert np.all(emu_values > 0)

        # Test batch processing of complete coordinate sets
        all_coords = np.concatenate([
            svg_coords['x'], svg_coords['y'],
            svg_coords['width'], svg_coords['height']
        ])
        all_units = np.full(len(all_coords), UnitType.PIXEL)

        batch_result = converter.batch_to_emu(all_coords, all_units)
        assert len(batch_result) == len(all_coords)
        assert np.all(np.isfinite(batch_result))

    def test_multi_unit_document_processing(self):
        """Test processing document with mixed unit types."""
        converter = NumPyFractionalEMU()

        # Mixed unit document simulation
        coordinates = np.array([
            100.0,  # pixels
            72.0,   # points
            25.4,   # mm
            2.54,   # cm
            1.0     # inch
        ])

        unit_types = np.array([
            UnitType.PIXEL,
            UnitType.POINT,
            UnitType.MM,
            UnitType.CM,
            UnitType.INCH
        ])

        # Process with different quality settings
        for quality in ['low', 'medium', 'high', 'ultra']:
            emu_values = converter.batch_to_emu(coordinates, unit_types)
            quantized = converter.smart_quantization(emu_values, quality)

            # Verify results are appropriate for quality level
            assert len(quantized) == len(coordinates)
            assert np.all(np.isfinite(quantized))

            if quality == 'low':
                # Should be integers
                assert np.all(quantized == np.round(quantized))

    def test_viewbox_conversion_integration(self):
        """Test SVG viewBox to DrawingML conversion."""
        # Test various viewBox scenarios
        viewbox_cases = [
            (0, 0, 100, 100, UnitType.PIXEL),
            (10.5, 20.75, 200.25, 150.125, UnitType.PIXEL),
            (0, 0, 72, 72, UnitType.POINT),
            (5.0, 10.0, 50.0, 75.0, UnitType.MM)
        ]

        for x, y, width, height, unit_type in viewbox_cases:
            emu_x, emu_y, emu_width, emu_height = convert_svg_viewbox_to_emu(
                x, y, width, height, unit_type
            )

            # Verify all are positive integers (DrawingML requirement)
            assert isinstance(emu_x, int) and emu_x >= 0
            assert isinstance(emu_y, int) and emu_y >= 0
            assert isinstance(emu_width, int) and emu_width > 0
            assert isinstance(emu_height, int) and emu_height > 0

    def test_performance_vs_baseline(self):
        """Test performance improvement vs scalar operations."""
        import time

        # Generate large coordinate dataset
        n_coords = 10000
        test_coords = np.random.uniform(0, 1000, n_coords)
        test_units = np.full(n_coords, UnitType.PIXEL)

        # Time NumPy implementation
        converter = NumPyFractionalEMU()

        start_time = time.perf_counter()
        numpy_result = converter.batch_to_emu(test_coords, test_units)
        numpy_time = time.perf_counter() - start_time

        # Performance should be reasonable (>100k coords/sec)
        coords_per_sec = n_coords / numpy_time
        assert coords_per_sec > 100000, f"Performance too slow: {coords_per_sec:,.0f} coords/sec"

        # Results should all be valid
        assert len(numpy_result) == n_coords
        assert np.all(np.isfinite(numpy_result))

    def test_precision_preservation_chain(self):
        """Test precision preservation through processing chain."""
        converter = NumPyFractionalEMU(precision_mode=PrecisionMode.SUBPIXEL)

        # High precision input
        precise_coords = np.array([123.456789012345])
        units = np.array([UnitType.MM])

        # Process through chain with precision preservation
        emu_precise = converter.batch_to_emu(precise_coords, units, preserve_precision=True)

        # Apply different rounding strategies
        rounded_standard = converter.round_precision(emu_precise)
        rounded_adaptive = converter.adaptive_precision_round(emu_precise)
        rounded_banker = converter.advanced_round(emu_precise, 'banker', 3)

        # All should be finite and reasonable
        for result in [rounded_standard, rounded_adaptive, rounded_banker]:
            assert np.all(np.isfinite(result))
            assert np.all(result > 0)

        # Standard and banker's rounding should be close
        np.testing.assert_allclose(rounded_standard, rounded_banker, rtol=0.01)

    def test_grid_alignment_workflow(self):
        """Test grid alignment for design consistency."""
        converter = NumPyFractionalEMU()

        # Simulate imprecise coordinates from SVG parsing
        messy_coords = np.array([
            100.3, 200.7, 300.1, 400.9, 500.2
        ])
        units = np.full(len(messy_coords), UnitType.PIXEL)

        # Convert to EMU
        emu_coords = converter.batch_to_emu(messy_coords, units)

        # Align to common grid sizes
        grid_sizes = [64, 128, 256, 512]  # Common EMU grid sizes

        for grid_size in grid_sizes:
            aligned = converter.quantize_to_grid(emu_coords, grid_size)

            # Verify grid alignment
            assert np.all(aligned % grid_size == 0)
            assert len(aligned) == len(emu_coords)

    def test_error_handling_integration(self):
        """Test error handling in integration scenarios."""
        converter = NumPyFractionalEMU()

        # Test with problematic input data
        problematic_coords = np.array([
            np.nan,      # Invalid
            np.inf,      # Invalid
            -100.0,      # Negative
            1e10,        # Too large
            0.0,         # Valid edge case
            100.0        # Valid
        ])
        units = np.full(len(problematic_coords), UnitType.PIXEL)

        # Should handle gracefully with warnings
        with pytest.warns(UserWarning):
            result = converter.batch_to_emu(problematic_coords, units)

        # Should clamp/fix invalid values
        assert len(result) == len(problematic_coords)
        assert np.all(np.isfinite(result))
        assert np.all(result >= 0)

    def test_memory_efficiency_integration(self):
        """Test memory efficiency in realistic scenarios."""
        converter = NumPyFractionalEMU()

        # Simulate processing multiple SVG documents
        doc_sizes = [100, 1000, 10000]  # Different document complexities

        for doc_size in doc_sizes:
            # Generate document coordinates
            coords = np.random.uniform(0, 1000, doc_size)
            units = np.random.choice([UnitType.PIXEL, UnitType.POINT, UnitType.MM], doc_size)

            # Process document
            emu_coords = converter.batch_to_emu(coords, units)
            optimized = converter.smart_quantization(emu_coords, 'high')

            # Verify memory usage is reasonable
            memory_info = converter.get_memory_usage()
            assert memory_info['total_bytes'] < 1000000  # < 1MB for converter itself

            # Results should be valid
            assert len(optimized) == doc_size
            assert np.all(np.isfinite(optimized))


if __name__ == "__main__":
    print("Running NumPy Fractional EMU Integration Tests...")

    # Run specific integration tests
    test_integration = TestNumPyFractionalEMUIntegration()

    print("✓ Testing SVG coordinate processing pipeline...")
    test_integration.test_svg_coordinate_processing_pipeline()

    print("✓ Testing multi-unit document processing...")
    test_integration.test_multi_unit_document_processing()

    print("✓ Testing viewBox conversion integration...")
    test_integration.test_viewbox_conversion_integration()

    print("✓ Testing performance vs baseline...")
    test_integration.test_performance_vs_baseline()

    print("✓ Testing precision preservation chain...")
    test_integration.test_precision_preservation_chain()

    print("✓ Testing grid alignment workflow...")
    test_integration.test_grid_alignment_workflow()

    print("✓ Testing error handling integration...")
    test_integration.test_error_handling_integration()

    print("✓ Testing memory efficiency integration...")
    test_integration.test_memory_efficiency_integration()

    print("=== All NumPy Fractional EMU Integration Tests Passed ===")