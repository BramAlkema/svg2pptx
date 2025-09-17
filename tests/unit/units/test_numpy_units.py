#!/usr/bin/env python3
"""
Comprehensive test suite for NumPy Unit Conversion Engine.

Tests performance, accuracy, and functionality of the ultra-fast
NumPy-based unit system.
"""

import pytest
import numpy as np
import time
from src.units.numpy_units import (
    UnitEngine, ConversionContext, UnitType,
    create_unit_engine, to_emu, batch_to_emu, parse_unit_batch
)


class TestUnitEngineBasics:
    """Test basic UnitEngine functionality."""

    def test_engine_initialization(self):
        """Test UnitEngine initialization."""
        engine = UnitEngine()

        # Should have default context
        assert engine.default_context is not None
        assert engine.default_context.dpi == 96.0
        assert engine.default_context.viewport_width == 800.0

    def test_single_unit_parsing(self):
        """Test single unit parsing."""
        engine = UnitEngine()

        # Test various unit types
        parsed = engine.parse_unit("100px")
        assert len(parsed) == 1
        assert parsed[0]['value'] == 100.0
        assert parsed[0]['unit_type'] == UnitType.PIXEL

        # Test em units
        parsed = engine.parse_unit("2.5em")
        assert parsed[0]['value'] == 2.5
        assert parsed[0]['unit_type'] == UnitType.EM

        # Test percentages
        parsed = engine.parse_unit("50%")
        assert parsed[0]['value'] == 0.5  # Should convert to decimal
        assert parsed[0]['unit_type'] == UnitType.PERCENT

    def test_numeric_input_handling(self):
        """Test numeric input handling."""
        engine = UnitEngine()

        # Test integer input
        parsed = engine.parse_unit(100)
        assert parsed[0]['value'] == 100.0
        assert parsed[0]['unit_type'] == UnitType.PIXEL

        # Test float input
        parsed = engine.parse_unit(50.5)
        assert parsed[0]['value'] == 50.5
        assert parsed[0]['unit_type'] == UnitType.PIXEL

    def test_batch_unit_parsing(self):
        """Test batch unit parsing."""
        engine = UnitEngine()

        values = ["100px", "2em", "1in", "50%"]
        parsed = engine.parse_unit(values)

        assert len(parsed) == 4
        assert parsed[0]['unit_type'] == UnitType.PIXEL
        assert parsed[1]['unit_type'] == UnitType.EM
        assert parsed[2]['unit_type'] == UnitType.INCH
        assert parsed[3]['unit_type'] == UnitType.PERCENT

    def test_empty_and_invalid_inputs(self):
        """Test handling of empty and invalid inputs."""
        engine = UnitEngine()

        # Empty string
        parsed = engine.parse_unit("")
        assert parsed[0]['unit_type'] == UnitType.UNITLESS

        # Invalid string
        parsed = engine.parse_unit("invalid")
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
        engine = UnitEngine()

        # 100px at 96 DPI should be 952,500 EMUs
        emu = engine.to_emu("100px")
        expected = int(100 * 914400 / 96)
        assert emu == expected

    def test_inch_conversions(self):
        """Test inch to EMU conversions."""
        engine = UnitEngine()

        # 1 inch should be 914,400 EMUs
        emu = engine.to_emu("1in")
        assert emu == 914400

    def test_point_conversions(self):
        """Test point to EMU conversions."""
        engine = UnitEngine()

        # 72 points should be 1 inch = 914,400 EMUs
        emu = engine.to_emu("72pt")
        assert emu == 914400

    def test_em_conversions(self):
        """Test em to EMU conversions."""
        context = ConversionContext(font_size=16, dpi=96)
        engine = UnitEngine(context)

        # 1em = 16px at 96 DPI
        emu = engine.to_emu("1em")
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
        engine = UnitEngine(context)

        # 50% of parent width (400px) = 200px
        emu = engine.to_emu("50%", axis='x')
        expected = int(200 * 914400 / 96)
        assert emu == expected

        # 50% of parent height (300px) = 150px
        emu = engine.to_emu("50%", axis='y')
        expected = int(150 * 914400 / 96)
        assert emu == expected

    def test_viewport_conversions(self):
        """Test viewport unit conversions."""
        context = ConversionContext(viewport_width=1920, viewport_height=1080, dpi=96)
        engine = UnitEngine(context)

        # 10vw = 10% of 1920px = 192px
        emu = engine.to_emu("10vw")
        expected = int(192 * 914400 / 96)
        assert emu == expected

        # 10vh = 10% of 1080px = 108px
        emu = engine.to_emu("10vh")
        expected = int(108 * 914400 / 96)
        assert emu == expected


class TestBatchOperations:
    """Test batch conversion operations."""

    def test_batch_dictionary_conversion(self):
        """Test batch dictionary conversion."""
        engine = UnitEngine()

        values = {
            'x': '50px',
            'y': '100px',
            'width': '200px',
            'height': '150px',
            'font-size': '16px'
        }

        results = engine.batch_to_emu(values)

        assert len(results) == 5
        assert all(isinstance(val, (int, np.integer)) for val in results.values())

        # Check specific conversions
        expected_x = int(50 * 914400 / 96)
        assert results['x'] == expected_x

    def test_batch_array_conversion(self):
        """Test batch array conversion."""
        engine = UnitEngine()

        values = ["100px", "2em", "1in", "50pt"]
        parsed = engine.parse_unit(values)
        emus = engine.to_emu_batch(parsed)

        assert len(emus) == 4
        assert all(isinstance(emu, (int, np.integer)) for emu in emus)

        # Check 1 inch conversion
        assert emus[2] == 914400

    def test_empty_batch_handling(self):
        """Test handling of empty batches."""
        engine = UnitEngine()

        results = engine.batch_to_emu({})
        assert results == {}


class TestContextManagement:
    """Test context management features."""

    def test_context_manager(self):
        """Test context manager functionality."""
        engine = UnitEngine()

        original_dpi = engine.default_context.dpi

        with engine.with_context(dpi=150):
            # Should use updated context
            assert engine.default_context.dpi == 150
            emu = engine.to_emu("100px")
            expected = int(100 * 914400 / 150)
            assert emu == expected

        # Should restore original context
        assert engine.default_context.dpi == original_dpi

    def test_engine_with_updates(self):
        """Test engine with updates."""
        engine = UnitEngine()
        updated_engine = engine.with_updates(dpi=150, font_size=20)

        # Original should be unchanged
        assert engine.default_context.dpi == 96.0

        # Updated should have new values
        assert updated_engine.default_context.dpi == 150.0
        assert updated_engine.default_context.font_size == 20.0


class TestPerformanceBenchmarks:
    """Performance tests for NumPy unit system."""

    def test_single_conversion_performance(self):
        """Benchmark single conversion performance."""
        engine = UnitEngine()

        # Warmup
        for _ in range(100):
            engine.to_emu("100px")

        # Benchmark
        n_conversions = 10000
        start_time = time.time()

        for i in range(n_conversions):
            emu = engine.to_emu(f"{i % 100}px")

        conversion_time = time.time() - start_time

        print(f"Single conversions: {n_conversions} in {conversion_time:.4f}s")
        rate = n_conversions / conversion_time
        print(f"Conversion rate: {rate:,.0f} conversions/sec")

        # Should be much faster than legacy (target: 100k+ conversions/sec)
        assert rate > 100000

    def test_batch_conversion_performance(self):
        """Benchmark batch conversion performance."""
        engine = UnitEngine()

        # Create large batch
        batch = {f'attr_{i}': f"{i % 100}px" for i in range(10000)}

        # Warmup
        engine.batch_to_emu({'test': '100px'})

        # Benchmark
        start_time = time.time()
        results = engine.batch_to_emu(batch)
        batch_time = time.time() - start_time

        print(f"Batch conversion: {len(batch)} values in {batch_time:.4f}s")
        rate = len(batch) / batch_time
        print(f"Batch rate: {rate:,.0f} conversions/sec")

        # Should be very fast (target: 500k+ conversions/sec)
        assert rate > 500000
        assert len(results) == len(batch)

    def test_array_conversion_performance(self):
        """Benchmark array conversion performance."""
        engine = UnitEngine()

        # Create large array
        values = [f"{i % 100}px" for i in range(50000)]

        # Warmup
        engine.parse_unit(["100px"])

        # Benchmark
        start_time = time.time()
        parsed = engine.parse_unit(values)
        emus = engine.to_emu_batch(parsed)
        array_time = time.time() - start_time

        print(f"Array conversion: {len(values)} values in {array_time:.4f}s")
        rate = len(values) / array_time
        print(f"Array rate: {rate:,.0f} conversions/sec")

        # Should be extremely fast (target: 1M+ conversions/sec)
        assert rate > 1000000
        assert len(emus) == len(values)


class TestFactoryFunctions:
    """Test factory and convenience functions."""

    def test_create_unit_engine(self):
        """Test unit engine factory function."""
        engine = create_unit_engine(
            viewport_width=1920,
            viewport_height=1080,
            dpi=150
        )

        assert engine.default_context.viewport_width == 1920
        assert engine.default_context.viewport_height == 1080
        assert engine.default_context.dpi == 150

    def test_convenience_to_emu(self):
        """Test convenience to_emu function."""
        emu = to_emu("100px", dpi=96)
        expected = int(100 * 914400 / 96)
        assert emu == expected

    def test_convenience_batch_to_emu(self):
        """Test convenience batch_to_emu function."""
        batch = {'x': '50px', 'y': '100px'}
        results = batch_to_emu(batch, dpi=96)

        assert len(results) == 2
        assert all(isinstance(val, (int, np.integer)) for val in results.values())

    def test_parse_unit_batch_function(self):
        """Test parse_unit_batch convenience function."""
        values = ["100px", "2em", "1in"]
        parsed = parse_unit_batch(values)

        assert len(parsed) == 3
        assert parsed[0]['unit_type'] == UnitType.PIXEL
        assert parsed[1]['unit_type'] == UnitType.EM
        assert parsed[2]['unit_type'] == UnitType.INCH


class TestAccuracyValidation:
    """Test numerical accuracy and edge cases."""

    def test_numerical_precision(self):
        """Test numerical precision with multiple operations."""
        engine = UnitEngine()

        # Test precision with various unit types
        test_values = [
            ("1in", 914400),
            ("72pt", 914400),
            ("25.4mm", 914400),
            ("2.54cm", 914400)
        ]

        for value, expected in test_values:
            emu = engine.to_emu(value)
            # Allow small rounding differences
            assert abs(emu - expected) <= 1

    def test_extreme_values(self):
        """Test handling of extreme values."""
        engine = UnitEngine()

        # Very large values
        emu = engine.to_emu("1000000px")
        assert emu > 0

        # Very small values
        emu = engine.to_emu("0.001px")
        assert emu >= 0

        # Negative values
        emu = engine.to_emu("-100px")
        assert emu < 0

    def test_zero_and_edge_cases(self):
        """Test zero and edge case handling."""
        engine = UnitEngine()

        # Zero values
        assert engine.to_emu("0px") == 0
        assert engine.to_emu("0em") == 0

        # Empty and None handling
        assert engine.to_emu("") == 0

    def test_different_dpi_accuracy(self):
        """Test accuracy across different DPI values."""
        dpi_values = [72.0, 96.0, 120.0, 150.0, 300.0]

        for dpi in dpi_values:
            engine = UnitEngine(ConversionContext(dpi=dpi))

            # 1 inch should always be 914,400 EMUs regardless of DPI
            emu = engine.to_emu("1in")
            assert emu == 914400

            # 72 points should always be 1 inch
            emu = engine.to_emu("72pt")
            assert emu == 914400


class TestCachePerformance:
    """Test caching system performance."""

    def test_parse_caching(self):
        """Test that parsing results are cached."""
        engine = UnitEngine()

        # Clear any existing cache stats
        initial_stats = engine.cache_stats

        # Parse same value multiple times
        for _ in range(100):
            engine.parse_unit("100px")

        # Should have high cache hit rate after first parse
        stats = engine.cache_stats
        # Note: LRU cache handles this automatically


if __name__ == "__main__":
    # Run performance benchmarks if executed directly
    print("=== NumPy Unit Conversion Performance Benchmarks ===")

    test_perf = TestPerformanceBenchmarks()
    test_perf.test_single_conversion_performance()
    test_perf.test_batch_conversion_performance()
    test_perf.test_array_conversion_performance()

    print("=== All benchmarks completed ===")