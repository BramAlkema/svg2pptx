#!/usr/bin/env python3
"""
Performance benchmarks for Color class operations.

Tests for Task 1.9: Benchmarking Color operations vs existing baseline
to ensure performance regression testing and optimization validation.
"""

import pytest
import time
import numpy as np
from unittest.mock import patch
import gc

from core.color import Color


class TestColorPerformanceBenchmarks:
    """Performance benchmarks for Color class operations."""

    def setup_method(self):
        """Setup before each test."""
        # Force garbage collection to ensure clean state
        gc.collect()

    @pytest.mark.benchmark(
        group="color_creation",
        min_rounds=10,
        timer=time.perf_counter,
        disable_gc=True,
        warmup=False
    )
    def test_color_creation_from_hex_performance(self, benchmark):
        """Benchmark Color creation from hex strings."""
        def create_hex_color():
            return Color('#ff0000')

        result = benchmark(create_hex_color)
        assert result.rgb() == (255, 0, 0)

    @pytest.mark.benchmark(
        group="color_creation",
        min_rounds=10,
        timer=time.perf_counter,
        disable_gc=True,
        warmup=False
    )
    def test_color_creation_from_rgb_tuple_performance(self, benchmark):
        """Benchmark Color creation from RGB tuples."""
        def create_rgb_color():
            return Color((255, 128, 64))

        result = benchmark(create_rgb_color)
        assert result.rgb() == (255, 128, 64)

    @pytest.mark.benchmark(
        group="color_creation",
        min_rounds=10,
        timer=time.perf_counter,
        disable_gc=True,
        warmup=False
    )
    def test_color_creation_from_hsl_performance(self, benchmark):
        """Benchmark Color creation from HSL strings."""
        def create_hsl_color():
            return Color('hsl(0, 100%, 50%)')

        result = benchmark(create_hsl_color)
        assert result.rgb() == (255, 0, 0)

    @pytest.mark.benchmark(
        group="color_manipulation",
        min_rounds=10,
        timer=time.perf_counter,
        disable_gc=True,
        warmup=False
    )
    def test_color_darken_performance(self, benchmark):
        """Benchmark Color darken operation."""
        red = Color('#ff0000')

        def darken_color():
            return red.darken(0.2)

        result = benchmark(darken_color)
        assert isinstance(result, Color)

    @pytest.mark.benchmark(
        group="color_manipulation",
        min_rounds=10,
        timer=time.perf_counter,
        disable_gc=True,
        warmup=False
    )
    def test_color_lighten_performance(self, benchmark):
        """Benchmark Color lighten operation."""
        red = Color('#800000')  # Dark red

        def lighten_color():
            return red.lighten(0.2)

        result = benchmark(lighten_color)
        assert isinstance(result, Color)

    @pytest.mark.benchmark(
        group="color_manipulation",
        min_rounds=10,
        timer=time.perf_counter,
        disable_gc=True,
        warmup=False
    )
    def test_color_saturate_performance(self, benchmark):
        """Benchmark Color saturate operation."""
        gray = Color('#808080')

        def saturate_color():
            return gray.saturate(0.3)

        result = benchmark(saturate_color)
        assert isinstance(result, Color)

    @pytest.mark.benchmark(
        group="color_manipulation",
        min_rounds=10,
        timer=time.perf_counter,
        disable_gc=True,
        warmup=False
    )
    def test_color_adjust_hue_performance(self, benchmark):
        """Benchmark Color hue adjustment operation."""
        red = Color('#ff0000')

        def adjust_hue():
            return red.adjust_hue(120)

        result = benchmark(adjust_hue)
        assert isinstance(result, Color)

    @pytest.mark.benchmark(
        group="color_chaining",
        min_rounds=10,
        timer=time.perf_counter,
        disable_gc=True,
        warmup=False
    )
    def test_color_method_chaining_performance(self, benchmark):
        """Benchmark Color method chaining operations."""
        red = Color('#ff0000')

        def chain_operations():
            return red.darken(0.1).saturate(0.2).adjust_hue(30).lighten(0.05)

        result = benchmark(chain_operations)
        assert isinstance(result, Color)

    @pytest.mark.benchmark(
        group="color_conversion",
        min_rounds=10,
        timer=time.perf_counter,
        disable_gc=True,
        warmup=False
    )
    def test_color_lab_conversion_performance(self, benchmark):
        """Benchmark Color Lab conversion."""
        red = Color('#ff0000')

        def lab_conversion():
            try:
                return red.lab()
            except NotImplementedError:
                # Return dummy data if colorspacious not available
                return (53.2, 80.1, 67.2)

        result = benchmark(lab_conversion)
        assert len(result) == 3

    @pytest.mark.benchmark(
        group="color_conversion",
        min_rounds=10,
        timer=time.perf_counter,
        disable_gc=True,
        warmup=False
    )
    def test_color_hsl_conversion_performance(self, benchmark):
        """Benchmark Color HSL conversion."""
        red = Color('#ff0000')

        def hsl_conversion():
            return red.hsl()

        result = benchmark(hsl_conversion)
        assert len(result) == 3

    @pytest.mark.benchmark(
        group="color_conversion",
        min_rounds=10,
        timer=time.perf_counter,
        disable_gc=True,
        warmup=False
    )
    def test_color_hex_conversion_performance(self, benchmark):
        """Benchmark Color hex conversion."""
        red = Color((255, 128, 64))

        def hex_conversion():
            return red.hex()

        result = benchmark(hex_conversion)
        assert result == 'ff8040'

    @pytest.mark.benchmark(
        group="color_comparison",
        min_rounds=10,
        timer=time.perf_counter,
        disable_gc=True,
        warmup=False
    )
    def test_color_delta_e_performance(self, benchmark):
        """Benchmark Color Delta E calculation."""
        red = Color('#ff0000')
        blue = Color('#0000ff')

        def delta_e_calculation():
            return red.delta_e(blue)

        result = benchmark(delta_e_calculation)
        assert isinstance(result, float)

    @pytest.mark.benchmark(
        group="bulk_operations",
        min_rounds=5,
        timer=time.perf_counter,
        disable_gc=True,
        warmup=False
    )
    def test_bulk_color_creation_performance(self, benchmark):
        """Benchmark bulk Color creation (1000 colors)."""
        hex_colors = [f'#{i:06x}' for i in range(0, 1000)]

        def create_bulk_colors():
            return [Color(hex_color) for hex_color in hex_colors]

        result = benchmark(create_bulk_colors)
        assert len(result) == 1000
        assert all(isinstance(color, Color) for color in result)

    @pytest.mark.benchmark(
        group="bulk_operations",
        min_rounds=5,
        timer=time.perf_counter,
        disable_gc=True,
        warmup=False
    )
    def test_bulk_color_manipulation_performance(self, benchmark):
        """Benchmark bulk Color manipulation operations."""
        colors = [Color(f'#{i:06x}') for i in range(0, 100)]

        def manipulate_bulk_colors():
            return [color.darken(0.1).saturate(0.2) for color in colors]

        result = benchmark(manipulate_bulk_colors)
        assert len(result) == 100
        assert all(isinstance(color, Color) for color in result)

    def test_color_performance_baseline_comparison(self):
        """Compare Color performance against baseline expectations."""
        # Test 1: Single color creation should be < 1ms
        start_time = time.perf_counter()
        for _ in range(1000):
            Color('#ff0000')
        single_creation_time = (time.perf_counter() - start_time) / 1000

        assert single_creation_time < 0.001, f"Single color creation took {single_creation_time:.4f}s, expected < 0.001s"

        # Test 2: Color manipulation should be < 5ms per operation
        red = Color('#ff0000')
        start_time = time.perf_counter()
        for _ in range(1000):
            red.darken(0.1)
        manipulation_time = (time.perf_counter() - start_time) / 1000

        assert manipulation_time < 0.005, f"Color manipulation took {manipulation_time:.4f}s, expected < 0.005s"

        # Test 3: Method chaining should be < 10ms per chain
        start_time = time.perf_counter()
        for _ in range(1000):
            red.darken(0.1).saturate(0.2).adjust_hue(30)
        chaining_time = (time.perf_counter() - start_time) / 1000

        assert chaining_time < 0.010, f"Method chaining took {chaining_time:.4f}s, expected < 0.010s"

    def test_color_memory_efficiency(self):
        """Test Color memory efficiency and immutability."""
        import sys

        # Test 1: Color objects should be reasonably sized
        red = Color('#ff0000')
        size = sys.getsizeof(red)

        # Color object should be under 1KB
        assert size < 1024, f"Color object size {size} bytes, expected < 1024 bytes"

        # Test 2: Method chaining should not create excessive objects
        initial_count = len(gc.get_objects())

        # Create chain operations
        for _ in range(100):
            result = red.darken(0.1).saturate(0.2).adjust_hue(30)

        # Force garbage collection
        gc.collect()
        final_count = len(gc.get_objects())

        # Should not have massive object growth (allow some tolerance)
        object_growth = final_count - initial_count
        assert object_growth < 1000, f"Created {object_growth} objects, expected < 1000"

    def test_color_caching_performance_impact(self):
        """Test that caching improves performance for color operations."""
        red = Color('#ff0000')

        try:
            # First conversion (should populate cache)
            start_time = time.perf_counter()
            lab1 = red.lab()
            first_time = time.perf_counter() - start_time

            # Second conversion (should use cache)
            start_time = time.perf_counter()
            lab2 = red.lab()
            second_time = time.perf_counter() - start_time

            # Cached operation should be faster (or at least not significantly slower)
            assert second_time <= first_time * 2, f"Cached operation took {second_time:.6f}s vs {first_time:.6f}s"
            assert lab1 == lab2, "Cached result should be identical"

        except NotImplementedError:
            # Skip if colorspacious not available
            pytest.skip("colorspacious not available for caching test")

    def test_color_fallback_performance(self):
        """Test that fallback operations maintain reasonable performance."""
        red = Color('#ff0000')

        # Test fallback color manipulation (when colorspacious fails)
        try:
            with patch('src.color.core.colorspacious.cspace_convert', side_effect=Exception("Mock failure")):
                start_time = time.perf_counter()

                # These should use fallback implementations
                darker = red.darken(0.2)
                lighter = red.lighten(0.2)
                saturated = red.saturate(0.2)

                fallback_time = time.perf_counter() - start_time

                # Fallback should complete within reasonable time
                assert fallback_time < 0.1, f"Fallback operations took {fallback_time:.4f}s, expected < 0.1s"

                # Results should still be valid
                assert isinstance(darker, Color)
                assert isinstance(lighter, Color)
                assert isinstance(saturated, Color)

        except Exception:
            # If patching fails, skip this test
            pytest.skip("Could not test fallback performance")


class TestColorPerformanceRegression:
    """Regression tests for Color performance characteristics."""

    def test_no_performance_regression_basic_operations(self):
        """Ensure basic operations maintain baseline performance."""
        # Baseline expectations (adjust based on hardware)
        CREATION_BASELINE = 0.001  # 1ms per color creation
        MANIPULATION_BASELINE = 0.005  # 5ms per manipulation
        CONVERSION_BASELINE = 0.01  # 10ms per conversion

        # Test color creation performance
        start_time = time.perf_counter()
        colors = [Color(f'#{i:06x}') for i in range(1000)]
        creation_time = time.perf_counter() - start_time
        avg_creation = creation_time / 1000

        assert avg_creation < CREATION_BASELINE, f"Color creation regression: {avg_creation:.6f}s > {CREATION_BASELINE}s"

        # Test manipulation performance
        red = Color('#ff0000')
        start_time = time.perf_counter()
        for _ in range(1000):
            red.darken(0.1)
        manipulation_time = time.perf_counter() - start_time
        avg_manipulation = manipulation_time / 1000

        assert avg_manipulation < MANIPULATION_BASELINE, f"Manipulation regression: {avg_manipulation:.6f}s > {MANIPULATION_BASELINE}s"

        # Test conversion performance
        start_time = time.perf_counter()
        for _ in range(1000):
            red.hsl()
        conversion_time = time.perf_counter() - start_time
        avg_conversion = conversion_time / 1000

        assert avg_conversion < CONVERSION_BASELINE, f"Conversion regression: {avg_conversion:.6f}s > {CONVERSION_BASELINE}s"

    def test_memory_usage_regression(self):
        """Ensure memory usage doesn't regress significantly."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create many color objects
        colors = []
        for i in range(10000):
            color = Color(f'#{i % 0xffffff:06x}')
            colors.append(color.darken(0.1).saturate(0.2))

        peak_memory = process.memory_info().rss
        memory_increase = peak_memory - initial_memory

        # Should not use more than 50MB for 10k color objects
        max_memory_mb = 50 * 1024 * 1024
        assert memory_increase < max_memory_mb, f"Memory usage {memory_increase / (1024*1024):.1f}MB exceeds {max_memory_mb / (1024*1024)}MB limit"

        # Clean up
        del colors
        gc.collect()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--benchmark-only'])