#!/usr/bin/env python3
"""
Transform Performance Analysis for Task 1.1

This script analyzes the current transform system performance and identifies
bottlenecks that need to be addressed in the NumPy Transform Matrix Engine.
"""

import sys
import time
import gc
from pathlib import Path
from typing import List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("❌ NumPy not available - tests will be limited")

from src.transforms.core import Matrix, TransformEngine


def test_legacy_matrix_performance():
    """Test performance of legacy Matrix class."""
    print("\n=== Legacy Matrix Performance ===")

    # Create test data
    matrix = Matrix.translate(10, 20).multiply(Matrix.rotate(45)).multiply(Matrix.scale(2.0))
    points = [(float(i), float(i * 2)) for i in range(10000)]

    # Test single point transformation
    gc.collect()
    start_time = time.perf_counter()

    single_results = []
    for x, y in points[:1000]:  # Smaller subset for single point test
        result = matrix.transform_point(x, y)
        single_results.append(result)

    single_time = time.perf_counter() - start_time

    # Test batch transformation (list comprehension)
    gc.collect()
    start_time = time.perf_counter()

    batch_results = matrix.transform_points(points)

    batch_time = time.perf_counter() - start_time

    print(f"  Single point (1K): {single_time:.6f}s ({1000/single_time:.0f} pts/sec)")
    print(f"  Batch points (10K): {batch_time:.6f}s ({len(points)/batch_time:.0f} pts/sec)")

    return {
        'single_time': single_time,
        'batch_time': batch_time,
        'single_throughput': 1000 / single_time,
        'batch_throughput': len(points) / batch_time
    }


def test_numpy_engine_performance():
    """Test performance of NumPy TransformEngine."""
    print("\n=== NumPy TransformEngine Performance ===")

    if not NUMPY_AVAILABLE:
        print("❌ SKIPPED - NumPy not available")
        return {'skipped': True}

    # Create test data
    engine = TransformEngine()
    engine.translate(10, 20).rotate(45).scale(2.0)

    # NumPy array format
    points_array = np.array([(float(i), float(i * 2)) for i in range(10000)], dtype=np.float64)

    # Test vectorized transformation
    gc.collect()
    start_time = time.perf_counter()

    vectorized_results = engine.transform_points(points_array)

    vectorized_time = time.perf_counter() - start_time

    # Test smaller batches to simulate typical usage
    small_batch = points_array[:1000]

    gc.collect()
    start_time = time.perf_counter()

    small_results = engine.transform_points(small_batch)

    small_time = time.perf_counter() - start_time

    print(f"  Vectorized (10K): {vectorized_time:.6f}s ({len(points_array)/vectorized_time:.0f} pts/sec)")
    print(f"  Small batch (1K): {small_time:.6f}s ({len(small_batch)/small_time:.0f} pts/sec)")

    return {
        'vectorized_time': vectorized_time,
        'small_time': small_time,
        'vectorized_throughput': len(points_array) / vectorized_time,
        'small_throughput': len(small_batch) / small_time
    }


def test_matrix_composition_performance():
    """Test matrix composition performance."""
    print("\n=== Matrix Composition Performance ===")

    # Legacy matrix composition
    gc.collect()
    start_time = time.perf_counter()

    legacy_result = Matrix.identity()
    for i in range(1000):
        transform = Matrix.translate(i, i).multiply(Matrix.rotate(i % 360)).multiply(Matrix.scale(1.1))
        legacy_result = legacy_result.multiply(transform)

    legacy_compose_time = time.perf_counter() - start_time

    # NumPy engine composition
    if NUMPY_AVAILABLE:
        gc.collect()
        start_time = time.perf_counter()

        engine = TransformEngine()
        for i in range(1000):
            engine.translate(i, i).rotate(i % 360).scale(1.1)

        numpy_compose_time = time.perf_counter() - start_time

        speedup = legacy_compose_time / numpy_compose_time if numpy_compose_time > 0 else 0

        print(f"  Legacy composition (1K): {legacy_compose_time:.6f}s")
        print(f"  NumPy composition (1K): {numpy_compose_time:.6f}s")
        print(f"  Composition speedup: {speedup:.1f}x")

        return {
            'legacy_time': legacy_compose_time,
            'numpy_time': numpy_compose_time,
            'speedup': speedup
        }
    else:
        print(f"  Legacy composition (1K): {legacy_compose_time:.6f}s")
        print("  NumPy composition: SKIPPED")
        return {'legacy_time': legacy_compose_time}


def identify_bottlenecks():
    """Identify specific performance bottlenecks."""
    print("\n=== Performance Bottleneck Analysis ===")

    bottlenecks = []

    # Test coordinate transformation overhead
    legacy_results = test_legacy_matrix_performance()
    numpy_results = test_numpy_engine_performance()
    composition_results = test_matrix_composition_performance()

    # Analyze bottlenecks
    if not numpy_results.get('skipped'):
        # Compare throughput
        legacy_throughput = legacy_results['batch_throughput']
        numpy_throughput = numpy_results['vectorized_throughput']

        current_speedup = numpy_throughput / legacy_throughput if legacy_throughput > 0 else 0

        print(f"\nCurrent Performance Analysis:")
        print(f"  Legacy batch throughput: {legacy_throughput:.0f} points/sec")
        print(f"  NumPy vectorized throughput: {numpy_throughput:.0f} points/sec")
        print(f"  Current speedup: {current_speedup:.1f}x")
        print(f"  Target speedup: 20-50x")
        print(f"  Gap to target: {20.0/current_speedup:.1f}x additional improvement needed" if current_speedup > 0 else "  Gap: Unable to calculate")

        if current_speedup < 20:
            bottlenecks.append(f"Coordinate transformation speedup only {current_speedup:.1f}x, target 20-50x")

    # Check matrix composition speedup
    if 'speedup' in composition_results:
        comp_speedup = composition_results['speedup']
        print(f"  Matrix composition speedup: {comp_speedup:.1f}x")
        if comp_speedup < 10:
            bottlenecks.append(f"Matrix composition speedup only {comp_speedup:.1f}x, target 10x+")

    # Identify specific bottlenecks
    print(f"\n🔍 IDENTIFIED BOTTLENECKS:")
    if bottlenecks:
        for i, bottleneck in enumerate(bottlenecks, 1):
            print(f"  {i}. {bottleneck}")
    else:
        print("  ✅ Performance targets appear to be met")

    # Improvement recommendations
    print(f"\n💡 IMPROVEMENT RECOMMENDATIONS:")
    print(f"  1. Implement pure NumPy matrix operations (no loops)")
    print(f"  2. Use np.dot() or @ operator for matrix multiplication")
    print(f"  3. Leverage broadcasting for batch operations")
    print(f"  4. Add Numba JIT compilation for critical paths")
    print(f"  5. Implement memory-efficient in-place operations")
    print(f"  6. Add SIMD-optimized operations for large datasets")

    return bottlenecks


def main():
    """Run comprehensive transform performance analysis."""
    print("🔍 Transform Performance Analysis - Task 1.1")
    print("=" * 60)

    try:
        bottlenecks = identify_bottlenecks()

        print("\n" + "=" * 60)
        print("📊 ANALYSIS SUMMARY")
        print("=" * 60)

        if bottlenecks:
            print(f"❌ {len(bottlenecks)} performance bottlenecks identified")
            print("🔧 NumPy Transform Matrix Engine improvements needed")
            print("📈 Target: 20-50x speedup for coordinate transformations")
        else:
            print("✅ Current performance meets targets")
            print("🚀 NumPy Transform Matrix Engine working effectively")

        print("\n🎯 Next Steps:")
        print("  1. Implement identified improvements")
        print("  2. Add comprehensive benchmarking")
        print("  3. Integrate with converter pipeline")
        print("  4. Validate performance targets")

        return 0 if not bottlenecks else 1

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())