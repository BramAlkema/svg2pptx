#!/usr/bin/env python3
"""
Comprehensive test suite for Unit Conversion Engine.

Tests performance, accuracy, and functionality of the
consolidated unit system after NumPy cleanup.
"""

import pytest
import numpy as np
import time
from pathlib import Path
import sys
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from core.units.core import (
    UnitConverter, ConversionContext, UnitType,
    to_emu
)
from core.units import unit, units


class TestUnitConverterBasics:
    """Test basic UnitConverter functionality."""

    def test_converter_initialization(self):
        """Test UnitConverter initialization."""
        converter = UnitConverter()

        # Should have default context
        # Should have default context
        assert converter.context is not None
        assert converter.context.dpi == 96.0
        assert converter.context.viewport_width == 800.0

    def test_single_unit_parsing(self):
        """Test single unit parsing."""
        converter = UnitConverter()

        # Test various unit types
        parsed = converter.parse_unit("100px")
        assert len(parsed) == 1
        assert parsed[0]['value'] == 100.0
        assert parsed[0]['unit_type'] == UnitType.PIXEL

        # Test em units
        parsed = converter.parse_unit("2.5em")
        assert parsed[0]['value'] == 2.5
        assert parsed[0]['unit_type'] == UnitType.EM

        # Test percentages
        parsed = converter.parse_unit("50%")
        assert parsed[0]['value'] == 0.5  # Should convert to decimal
        assert parsed[0]['unit_type'] == UnitType.PERCENT

    def test_numeric_input_handling(self):
        """Test numeric input handling."""
        converter = UnitConverter()

        # Test integer input
        parsed = converter.parse_unit(100)
        assert parsed[0]['value'] == 100.0
        assert parsed[0]['unit_type'] == UnitType.PIXEL

        # Test float input
        parsed = converter.parse_unit(50.5)
        assert parsed[0]['value'] == 50.5
        assert parsed[0]['unit_type'] == UnitType.PIXEL

    def test_batch_unit_parsing(self):
        """Test batch unit parsing."""
        converter = UnitConverter()

        values = ["100px", "2em", "1in", "50%"]
        parsed = converter.parse_unit(values)

        assert len(parsed) == 4
        assert parsed[0]['unit_type'] == UnitType.PIXEL
        assert parsed[1]['unit_type'] == UnitType.EM
        assert parsed[2]['unit_type'] == UnitType.INCH
        assert parsed[3]['unit_type'] == UnitType.PERCENT

    def test_empty_and_invalid_inputs(self):
        """Test handling of empty and invalid inputs."""
        converter = UnitConverter()

        # Empty string
        parsed = converter.parse_unit("")
        assert parsed[0]['unit_type'] == UnitType.UNITLESS

        # Invalid string
        parsed = converter.parse_unit("invalid")
        assert parsed[0]['unit_type'] == UnitType.UNITLESS


class TestConversionContext:
    """Test ConversionContext functionality."""

    def test_context_creation(self):
        """Test context creation."""
        context = ConversionContext(
            viewport_width=1920,
            viewport_height=1080,
            dpi=150,
            font_size=18
        )

        assert context.viewport_width == 1920
        assert context.viewport_height == 1080
        assert context.dpi == 150
        assert context.font_size == 18

    def test_context_updates(self):
        """Test context update functionality."""
        context = ConversionContext()
        updated = context.with_updates(dpi=150, font_size=20)

        # Original should be unchanged
        assert context.dpi == 96.0
        assert context.font_size == 16.0

        # Updated should have new values
        assert updated.dpi == 150.0
        assert updated.font_size == 20.0

    def test_context_copying(self):
        """Test context copying."""
        original = ConversionContext(dpi=150)
        copy = original.copy()

        assert copy.dpi == original.dpi
        assert copy is not original


class TestUnitConversions:
    """Test unit conversion accuracy."""

    def test_pixel_conversions(self):
        """Test pixel to EMU conversions."""
        converter = UnitConverter()

        # 100px at 96 DPI should be calculated correctly
        emu = converter.to_emu("100px")
        expected = int(100 * 914400 / 96)
        assert emu == expected

    def test_inch_conversions(self):
        """Test inch to EMU conversions."""
        converter = UnitConverter()

        # 1 inch should be 914,400 EMUs
        emu = converter.to_emu("1in")
        assert emu == 914400

    def test_point_conversions(self):
        """Test point to EMU conversions."""
        converter = UnitConverter()

        # 72 points should be 1 inch = 914,400 EMUs
        emu = converter.to_emu("72pt")
        assert emu == 914400

    def test_em_conversions(self):
        """Test em to EMU conversions."""
        context = ConversionContext(font_size=16, dpi=96)
        converter = UnitConverter(context)

        # 1em = 16px at 96 DPI
        emu = converter.to_emu("1em")
        expected = int(16 * 914400 / 96)
        assert emu == expected

    def test_percentage_conversions(self):
        """Test percentage conversions."""
        context = ConversionContext(
            viewport_width=800,
            viewport_height=600,
            parent_width=400,
            parent_height=300,
            dpi=96
        )
        converter = UnitConverter(context)

        # 50% of parent width (400px) = 200px
        emu = converter.to_emu("50%", axis='x')
        expected = int(200 * 914400 / 96)
        assert emu == expected

        # 50% of parent height (300px) = 150px
        emu = converter.to_emu("50%", axis='y')
        expected = int(150 * 914400 / 96)
        assert emu == expected

    def test_viewport_conversions(self):
        """Test viewport unit conversions."""
        context = ConversionContext(viewport_width=1920, viewport_height=1080, dpi=96)
        converter = UnitConverter(context)

        # 10vw = 10% of 1920px = 192px
        emu = converter.to_emu("10vw")
        expected = int(192 * 914400 / 96)
        assert emu == expected

        # 10vh = 10% of 1080px = 108px
        emu = converter.to_emu("10vh")
        expected = int(108 * 914400 / 96)
        assert emu == expected


class TestBatchOperations:
    """Test batch conversion operations."""

    def test_batch_parsing_and_conversion(self):
        """Test batch parsing and conversion."""
        converter = UnitConverter()

        # Test batch parsing
        values = ["100px", "2em", "1in", "50%", "10vw"]
        parsed = converter.parse_unit(values)

        assert len(parsed) == 5
        assert all(isinstance(unit['value'], (int, float, np.number)) for unit in parsed)

        # Test batch conversion to EMU
        context = ConversionContext(font_size=16, viewport_width=800)
        emus = converter.to_emu_batch(parsed, context)

        assert len(emus) == 5
        assert all(isinstance(emu, (int, np.integer)) for emu in emus)

    def test_batch_to_emu_function(self):
        """Test batch_to_emu convenience function."""
        values = {
            'widths': ["100px", "1in", "2em"],
            'heights': ["50px", "0.5in", "1.5em"]
        }

        result = batch_to_emu(values)

        assert 'widths' in result
        assert 'heights' in result
        assert len(result['widths']) == 3
        assert len(result['heights']) == 3

        # Verify 1in = 914,400 EMU
        assert result['widths'][1] == 914400


class TestHelperFunctions:
    """Test module-level helper functions."""

    def test_UnitConverter_function(self):
        """Test UnitConverter convenience function."""
        converter = UnitConverter(
            viewport_width=1920,
            viewport_height=1080,
            font_size=24,
            dpi=144
        )

        assert isinstance(converter, UnitConverter)
        assert converter.context.viewport_width == 1920
        assert converter.context.font_size == 24

    def test_module_level_to_emu_function(self):
        """Test module-level to_emu convenience function."""
        result = to_emu("1in")
        assert result == 914400

        result = to_emu("100px")
        expected = int(100 * 914400 / 96)
        assert result == expected

    def test_parse_unit_batch_function(self):
        """Test parse_unit_batch convenience function."""
        values = ["100px", "1in", "2em"]
        result = parse_unit_batch(values)

        assert len(result) == 3
        assert result[0]['unit_type'] == UnitType.PIXEL
        assert result[1]['unit_type'] == UnitType.INCH
        assert result[2]['unit_type'] == UnitType.EM


class TestPerformanceCharacteristics:
    """Test performance-related behavior."""

    def test_large_batch_performance(self):
        """Test performance with large batches."""
        converter = UnitConverter()

        # Create large batch
        large_batch = [f"{i}px" for i in range(1000)]

        start_time = time.time()
        parsed = converter.parse_unit(large_batch)
        parse_time = time.time() - start_time

        start_time = time.time()
        emus = converter.to_emu_batch(parsed)
        convert_time = time.time() - start_time

        # Should handle 1000 units reasonably fast
        assert parse_time < 1.0  # Less than 1 second
        assert convert_time < 1.0  # Less than 1 second
        assert len(emus) == 1000

    def test_caching_performance(self):
        """Test caching improves performance."""
        converter = UnitConverter()

        # Parse same values multiple times
        test_values = ["100px", "1in", "2em", "50%"]

        # First parse (cache miss)
        start_time = time.time()
        for _ in range(100):
            for value in test_values:
                converter.parse_unit(value)
        first_time = time.time() - start_time

        # Second parse (cache hit)
        start_time = time.time()
        for _ in range(100):
            for value in test_values:
                converter.parse_unit(value)
        second_time = time.time() - start_time

        # Cache should provide some speedup
        assert second_time <= first_time


@pytest.mark.integration
class TestUnitConverterIntegration:
    """Integration tests for UnitConverter."""

    def test_end_to_end_conversion_workflow(self):
        """Test complete workflow from parsing to EMU conversion."""
        converter = UnitConverter()

        # Parse various units
        units = ["100px", "1in", "72pt", "2em", "50%"]
        parsed = converter.parse_unit(units)

        # Convert to EMU with context
        context = ConversionContext(font_size=16.0, viewport_width=800.0)
        emu_values = converter.to_emu_batch(parsed, context=context)

        assert len(emu_values) == 5
        assert all(isinstance(val, (int, np.integer)) for val in emu_values)

        # Verify 1in = 914,400 EMU
        assert emu_values[1] == 914400

    def test_real_world_svg_units_scenario(self):
        """Test with real-world SVG unit scenarios."""
        converter = UnitConverter()

        # Typical SVG viewport and font context
        svg_context = ConversionContext(
            viewport_width=1920.0,
            viewport_height=1080.0,
            font_size=14.0,
            dpi=96.0
        )

        # Common SVG units
        unit_values = ["100px", "50%", "1.2em", "10pt", "5mm"]

        for unit_value in unit_values:
            result = converter.to_emu(unit_value, context=svg_context)
            assert isinstance(result, (int, np.integer))
            assert result > 0  # All should be positive values

    def test_context_switching_performance(self):
        """Test context switching with context manager."""
        converter = UnitConverter()

        original_dpi = converter.context.dpi

        with converter.with_context(dpi=150, font_size=20):
            # Should use new context
            result = converter.to_emu("1em")
            expected = int(20 * 914400 / 150)
            assert result == expected

        # Should restore original context
        assert converter.context.dpi == original_dpi


if __name__ == "__main__":
    # Allow running tests directly with: python test_units.py
    pytest.main([__file__])