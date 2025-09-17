#!/usr/bin/env python3
"""
Unit Conversion Performance Analysis

Analyzes current bottlenecks in the unit conversion system to identify
areas for NumPy optimization.
"""

import time
import sys
import os
import numpy as np
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from units import UnitConverter, ViewportContext, UnitType


def benchmark_parsing_performance():
    """Benchmark unit parsing performance."""
    print("=== Unit Parsing Performance Analysis ===")

    converter = UnitConverter()

    # Test values that are commonly found in SVG files
    test_values = [
        "100px", "50.5px", "1.25em", "2.5in", "10mm", "50%",
        "200pt", "3.14cm", "0.5ex", "75vh", "25vw", "100",
        "-10.5px", "1e2px", "0.001in", "999.999mm"
    ] * 1000  # 16,000 total values

    # Benchmark parsing
    start_time = time.time()
    parsed_results = []
    for value in test_values:
        result = converter.parse_length(value)
        parsed_results.append(result)
    parsing_time = time.time() - start_time

    print(f"Parsed {len(test_values)} values in {parsing_time:.4f}s")
    print(f"Parsing rate: {len(test_values)/parsing_time:,.0f} values/sec")
    print(f"Per-value time: {parsing_time/len(test_values)*1000:.3f}ms")

    return parsing_time, len(test_values)


def benchmark_conversion_performance():
    """Benchmark unit conversion to EMU performance."""
    print("\n=== Unit Conversion Performance Analysis ===")

    converter = UnitConverter()
    context = ViewportContext(width=800, height=600, dpi=96)

    # Test conversion performance
    test_conversions = [
        ("100px", 'x'), ("50px", 'y'), ("2em", 'x'), ("1in", 'x'),
        ("10mm", 'y'), ("50%", 'x'), ("25vh", 'y'), ("75vw", 'x')
    ] * 2000  # 16,000 conversions

    start_time = time.time()
    emu_results = []
    for value, axis in test_conversions:
        emu = converter.to_emu(value, context, axis)
        emu_results.append(emu)
    conversion_time = time.time() - start_time

    print(f"Converted {len(test_conversions)} values in {conversion_time:.4f}s")
    print(f"Conversion rate: {len(test_conversions)/conversion_time:,.0f} conversions/sec")
    print(f"Per-conversion time: {conversion_time/len(test_conversions)*1000:.3f}ms")

    return conversion_time, len(test_conversions)


def benchmark_batch_performance():
    """Benchmark batch conversion performance."""
    print("\n=== Batch Conversion Performance Analysis ===")

    converter = UnitConverter()
    context = ViewportContext(width=800, height=600, dpi=96)

    # Simulate common SVG element attributes
    test_batches = []
    for i in range(2000):
        batch = {
            'x': f"{i % 100}px",
            'y': f"{(i * 2) % 100}px",
            'width': f"{50 + i % 50}px",
            'height': f"{30 + i % 30}px",
            'stroke-width': f"{1 + i % 5}px"
        }
        test_batches.append(batch)

    # Individual conversions (current approach)
    start_time = time.time()
    individual_results = []
    for batch in test_batches:
        result = {}
        for key, value in batch.items():
            axis = 'y' if key in ['y', 'height'] else 'x'
            result[key] = converter.to_emu(value, context, axis)
        individual_results.append(result)
    individual_time = time.time() - start_time

    # Batch conversions
    start_time = time.time()
    batch_results = []
    for batch in test_batches:
        result = converter.batch_convert(batch, context)
        batch_results.append(result)
    batch_time = time.time() - start_time

    total_conversions = len(test_batches) * 5
    print(f"Individual conversions: {individual_time:.4f}s ({total_conversions/individual_time:,.0f} conv/sec)")
    print(f"Batch conversions: {batch_time:.4f}s ({total_conversions/batch_time:,.0f} conv/sec)")
    print(f"Batch speedup: {individual_time/batch_time:.2f}x")

    return individual_time, batch_time, total_conversions


def analyze_regex_performance():
    """Analyze regex parsing performance bottleneck."""
    print("\n=== Regex Parsing Analysis ===")

    converter = UnitConverter()
    import re

    # The current regex pattern
    current_pattern = r'([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*(.*)$'

    test_values = ["100px", "50.5px", "1.25em", "2.5in", "-10.5px", "1e2px"] * 5000

    # Test current regex approach
    start_time = time.time()
    for value in test_values:
        match = re.match(current_pattern, value.strip())
        if match:
            numeric_part = float(match.group(1))
            unit_part = match.group(2).lower().strip()
    current_regex_time = time.time() - start_time

    # Test compiled regex (optimization)
    compiled_pattern = re.compile(current_pattern)
    start_time = time.time()
    for value in test_values:
        match = compiled_pattern.match(value.strip())
        if match:
            numeric_part = float(match.group(1))
            unit_part = match.group(2).lower().strip()
    compiled_regex_time = time.time() - start_time

    print(f"Current regex: {current_regex_time:.4f}s")
    print(f"Compiled regex: {compiled_regex_time:.4f}s")
    print(f"Compiled speedup: {current_regex_time/compiled_regex_time:.2f}x")

    return current_regex_time, compiled_regex_time


def simulate_svg_processing_load():
    """Simulate realistic SVG processing workload."""
    print("\n=== Realistic SVG Processing Simulation ===")

    converter = UnitConverter()
    context = ViewportContext(width=1920, height=1080, dpi=96)

    # Simulate processing a complex SVG with many elements
    elements = []
    for i in range(1000):  # 1000 SVG elements
        element = {
            'rect': {
                'x': f"{i % 1920}px", 'y': f"{(i * 2) % 1080}px",
                'width': f"{50 + i % 100}px", 'height': f"{30 + i % 80}px",
                'stroke-width': f"{1 + i % 3}px"
            },
            'circle': {
                'cx': f"{i % 1920}px", 'cy': f"{(i * 3) % 1080}px",
                'r': f"{10 + i % 50}px", 'stroke-width': f"{0.5 + i % 2}px"
            },
            'text': {
                'x': f"{i % 1920}px", 'y': f"{(i * 4) % 1080}px",
                'font-size': f"{12 + i % 24}px", 'letter-spacing': f"{i % 3}px"
            }
        }
        elements.append(element)

    # Process all elements
    start_time = time.time()
    total_conversions = 0

    for element in elements:
        for shape_type, attributes in element.items():
            for attr_name, attr_value in attributes.items():
                axis = 'y' if attr_name in ['y', 'cy', 'height', 'font-size'] else 'x'
                emu_value = converter.to_emu(attr_value, context, axis)
                total_conversions += 1

    processing_time = time.time() - start_time

    print(f"Processed {len(elements)} SVG elements with {total_conversions} unit conversions")
    print(f"Total time: {processing_time:.4f}s")
    print(f"Elements/sec: {len(elements)/processing_time:,.0f}")
    print(f"Conversions/sec: {total_conversions/processing_time:,.0f}")
    print(f"Time per element: {processing_time/len(elements)*1000:.2f}ms")

    return processing_time, total_conversions


def identify_bottlenecks():
    """Identify specific performance bottlenecks."""
    print("\n=== Performance Bottleneck Analysis ===")

    print("\n1. String Processing:")
    print("   - Regex compilation happens on every parse_length call")
    print("   - String operations (.strip(), .lower()) are repeated")
    print("   - No caching of common unit parsing results")

    print("\n2. Mathematical Operations:")
    print("   - Individual scalar calculations instead of vectorized")
    print("   - Repeated DPI conversions (EMU_PER_INCH / dpi)")
    print("   - No pre-computed conversion factors")

    print("\n3. Object Creation Overhead:")
    print("   - ViewportContext object access for every conversion")
    print("   - UnitType enum lookups")
    print("   - Dictionary lookups for unit mapping")

    print("\n4. Algorithmic Inefficiencies:")
    print("   - No batch processing optimization")
    print("   - Redundant calculations in loops")
    print("   - Missing NumPy vectorization opportunities")


def numpy_optimization_potential():
    """Show NumPy optimization potential with simple examples."""
    print("\n=== NumPy Optimization Potential ===")

    # Current scalar approach simulation
    values = np.random.random(10000) * 100  # 10k pixel values
    dpi = 96.0
    emu_per_inch = 914400

    # Scalar approach (current)
    start_time = time.time()
    scalar_results = []
    for value in values:
        emu_per_pixel = emu_per_inch / dpi
        emu_value = int(value * emu_per_pixel)
        scalar_results.append(emu_value)
    scalar_time = time.time() - start_time

    # Vectorized approach (NumPy)
    start_time = time.time()
    emu_per_pixel = emu_per_inch / dpi
    vectorized_results = (values * emu_per_pixel).astype(np.int32)
    vectorized_time = time.time() - start_time

    print(f"Scalar conversion time: {scalar_time:.4f}s")
    print(f"Vectorized conversion time: {vectorized_time:.4f}s")
    print(f"NumPy speedup potential: {scalar_time/vectorized_time:.1f}x")

    # Batch processing simulation
    batch_size = 1000
    batches = [values[i:i+batch_size] for i in range(0, len(values), batch_size)]

    start_time = time.time()
    for batch in batches:
        result = (batch * emu_per_pixel).astype(np.int32)
    batch_time = time.time() - start_time

    print(f"Batch processing time: {batch_time:.4f}s")
    print(f"Batch vs scalar speedup: {scalar_time/batch_time:.1f}x")


def main():
    """Run comprehensive unit conversion performance analysis."""
    print("SVG2PPTX Unit Conversion Performance Analysis")
    print("=" * 50)

    # Core performance benchmarks
    parsing_time, parsing_count = benchmark_parsing_performance()
    conversion_time, conversion_count = benchmark_conversion_performance()
    individual_time, batch_time, batch_conversions = benchmark_batch_performance()

    # Detailed analysis
    current_regex, compiled_regex = analyze_regex_performance()
    svg_time, svg_conversions = simulate_svg_processing_load()

    # Identify bottlenecks and potential
    identify_bottlenecks()
    numpy_optimization_potential()

    # Summary
    print("\n" + "=" * 50)
    print("PERFORMANCE ANALYSIS SUMMARY")
    print("=" * 50)
    print(f"Current parsing rate: {parsing_count/parsing_time:,.0f} values/sec")
    print(f"Current conversion rate: {conversion_count/conversion_time:,.0f} conversions/sec")
    print(f"Regex optimization potential: {current_regex/compiled_regex:.1f}x speedup")
    print(f"Batch processing current speedup: {individual_time/batch_time:.1f}x")
    print(f"SVG processing rate: {svg_conversions/svg_time:,.0f} conversions/sec")

    print(f"\nNUMPY REFACTORING TARGETS:")
    print(f"- Target parsing rate: {parsing_count/parsing_time*50:,.0f} values/sec (50x)")
    print(f"- Target conversion rate: {conversion_count/conversion_time*100:,.0f} conversions/sec (100x)")
    print(f"- Target SVG processing: {svg_conversions/svg_time*30:,.0f} conversions/sec (30x)")


if __name__ == "__main__":
    main()