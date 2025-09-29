#!/usr/bin/env python3
"""
Direct Unit Converter Performance Test

Tests the fast unit converter against realistic scenarios to validate
the actual performance improvements from NumPy vectorization.
"""

import sys
import time
import gc
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np

# Import the fast unit converter
import importlib.util

units_fast_path = project_root / "src" / "units_fast.py"
spec = importlib.util.spec_from_file_location("units_fast", units_fast_path)
units_fast = importlib.util.module_from_spec(spec)
spec.loader.exec_module(units_fast)

UnitConverter = units_fast.UnitConverter
Context = units_fast.Context


def test_fast_converter_performance():
    """Test the performance of the fast unit converter."""
    print("🚀 Fast Unit Converter Performance Test")
    print("=" * 50)

    converter = UnitConverter()
    context = Context(width=800, height=600, font_size=16, dpi=96)

    # Test scenarios
    scenarios = [
        ("Small batch", 1000),
        ("Medium batch", 10000),
        ("Large batch", 50000),
        ("Extra large", 100000)
    ]

    # Test data - mixed units like real SVG content
    test_units = ['px', 'pt', 'mm', 'cm', 'in', 'em', '%']

    for scenario_name, size in scenarios:
        print(f"\n--- {scenario_name}: {size:,} conversions ---")

        # Generate realistic test data
        test_values = []
        for i in range(size):
            unit = test_units[i % len(test_units)]
            value = f"{(i * 0.123 + 1.0):.2f}{unit}"
            test_values.append(value)

        # Test individual conversions
        gc.collect()
        start_time = time.perf_counter()

        individual_results = []
        for value in test_values[:1000]:  # Subset for individual test
            emu = converter.to_emu(value, context)
            individual_results.append(emu)

        individual_time = time.perf_counter() - start_time
        individual_throughput = 1000 / individual_time

        # Test batch conversions
        gc.collect()
        start_time = time.perf_counter()

        batch_results = converter.batch_to_emu(test_values, context)

        batch_time = time.perf_counter() - start_time
        batch_throughput = size / batch_time

        # Test ultra-fast batch conversions
        gc.collect()
        start_time = time.perf_counter()

        ultra_fast_results = converter.batch_to_emu_ultra_fast(test_values, context)

        ultra_fast_time = time.perf_counter() - start_time
        ultra_fast_throughput = size / ultra_fast_time

        # Calculate speedup
        estimated_individual_time = individual_time * (size / 1000)
        speedup = estimated_individual_time / batch_time
        ultra_speedup = estimated_individual_time / ultra_fast_time

        print(f"  Individual (1K subset): {individual_time:.6f}s ({individual_throughput:.0f} conv/sec)")
        print(f"  Estimated for {size:,}: {estimated_individual_time:.6f}s")
        print(f"  Batch ({size:,}): {batch_time:.6f}s ({batch_throughput:.0f} conv/sec)")
        print(f"  Ultra-fast ({size:,}): {ultra_fast_time:.6f}s ({ultra_fast_throughput:.0f} conv/sec)")
        print(f"  Batch speedup: {speedup:.1f}x {'✅' if speedup >= 5 else '❌'}")
        print(f"  Ultra speedup: {ultra_speedup:.1f}x {'✅' if ultra_speedup >= 10 else '❌'}")

        # Test string parsing performance
        gc.collect()
        start_time = time.perf_counter()

        numeric_values, unit_types = converter.parse_batch(test_values)

        parsing_time = time.perf_counter() - start_time
        parsing_throughput = size / parsing_time

        print(f"  Parsing only: {parsing_time:.6f}s ({parsing_throughput:.0f} parse/sec)")

        # Verify correctness
        if len(batch_results) >= 10:
            sample_individual = individual_results[:5]
            sample_batch = batch_results[:5]
            sample_ultra = ultra_fast_results[:5]
            print(f"  Sample batch: {sample_batch.tolist()}")
            print(f"  Sample ultra: {sample_ultra.tolist()}")

            # Check if arrays are equal (allowing for potential type differences)
            try:
                arrays_equal = np.allclose(sample_batch, sample_ultra, rtol=1e-10)
                print(f"  Results match: {'✅' if arrays_equal else '❌'}")
            except:
                print(f"  Results comparison: ⚠️  (type mismatch)")


def test_conversion_accuracy():
    """Test conversion accuracy."""
    print("\n🔍 Conversion Accuracy Test")
    print("=" * 30)

    converter = UnitConverter()
    context = Context(width=800, height=600, font_size=16, dpi=96)

    test_cases = [
        ("100px", "pixels"),
        ("72pt", "points (1 inch at 72 DPI)"),
        ("25.4mm", "millimeters (1 inch)"),
        ("2.54cm", "centimeters (1 inch)"),
        ("1in", "inches"),
        ("100%", "percentage"),
        ("16em", "em units (16 * font_size)"),
        ("50vw", "viewport width (50% of 800px)")
    ]

    for value_str, description in test_cases:
        emu_result = converter.to_emu(value_str, context)
        pixel_result = converter.to_pixels(value_str, context)

        print(f"  {value_str:8} ({description:25}): {emu_result:8} EMU, {pixel_result:6.1f} px")


def test_vectorized_vs_loop_parsing():
    """Compare vectorized vs loop-based parsing."""
    print("\n⚡ Vectorized vs Loop Parsing")
    print("=" * 35)

    converter = UnitConverter()

    # Generate test data
    test_values = [
        "100px", "2.5em", "50%", "1.5in", "10mm", "12pt",
        "0.5vh", "25vw", "1.2ex", "0px", "-10px", "1.23px"
    ] * 5000  # 60,000 parsing operations

    print(f"Testing with {len(test_values):,} string values...")

    # Test vectorized parsing
    gc.collect()
    start_time = time.perf_counter()

    numeric_batch, unit_batch = converter.parse_batch(test_values)

    vectorized_time = time.perf_counter() - start_time
    vectorized_throughput = len(test_values) / vectorized_time

    # Test individual parsing (subset)
    subset_size = min(1000, len(test_values))
    subset_values = test_values[:subset_size]

    gc.collect()
    start_time = time.perf_counter()

    individual_results = []
    for value in subset_values:
        numeric, unit_type = converter.parse_value(value)
        individual_results.append((numeric, unit_type))

    individual_time = time.perf_counter() - start_time
    estimated_individual_time = individual_time * (len(test_values) / subset_size)
    parsing_speedup = estimated_individual_time / vectorized_time

    print(f"  Vectorized: {vectorized_time:.6f}s ({vectorized_throughput:.0f} parse/sec)")
    print(f"  Individual est: {estimated_individual_time:.6f}s")
    print(f"  Parsing speedup: {parsing_speedup:.1f}x {'✅' if parsing_speedup >= 2 else '❌'}")

    # Verify accuracy
    sample_vectorized = [(numeric_batch[i], unit_batch[i]) for i in range(5)]
    sample_individual = individual_results[:5]

    print(f"  Sample vectorized: {sample_vectorized}")
    print(f"  Sample individual: {sample_individual}")
    print(f"  Results match: {'✅' if sample_vectorized == sample_individual else '❌'}")


def main():
    """Run the performance tests."""
    try:
        test_fast_converter_performance()
        test_conversion_accuracy()
        test_vectorized_vs_loop_parsing()

        print("\n✅ Performance testing complete!")
        return 0

    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())