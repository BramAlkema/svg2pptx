#!/usr/bin/env python3
"""
Profile boundary detection algorithms to identify performance bottlenecks.

This script analyzes the current detection algorithms and provides detailed
performance metrics to guide optimization efforts.
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.multislide.detection import SlideDetector
from src.multislide.config import DetectionConfig
from tests.support.multislide.performance_helpers import (
    DetectionPerformanceTester,
    generate_test_svg,
    generate_large_nested_svg
)


def main():
    """Run performance profiling analysis."""
    print("=== Boundary Detection Performance Analysis ===\n")

    # Create detector with all features enabled
    config = DetectionConfig(
        enable_animation_detection=True,
        enable_nested_svg_detection=True,
        enable_layer_detection=True,
        enable_section_marker_detection=True,
        enable_input_validation=False,  # Skip validation for pure algorithm timing
        enable_performance_optimizations=False  # Test unoptimized algorithms
    )
    detector = SlideDetector(config)

    # Create performance tester
    tester = DetectionPerformanceTester(detector)

    print("1. Identifying bottlenecks in detection methods...")
    bottlenecks = tester.identify_bottlenecks()

    print(f"Slowest detection method: {bottlenecks['slowest_method']}")
    print(f"Execution time: {bottlenecks['slowest_time_ms']:.2f}ms\n")

    print("Individual method performance:")
    for method, metrics in bottlenecks['bottlenecks'].items():
        print(f"  {method:20}: {metrics['execution_time_ms']:6.2f}ms "
              f"({metrics['ops_per_second']:6.1f} ops/sec)")
    print()

    print("2. Testing scalability across document sizes...")
    scalability_results = tester.test_detection_scalability()

    for test_name, benchmark in scalability_results.items():
        print(f"\n{test_name.replace('_', ' ').title()}:")
        print(f"  Average time: {benchmark.average_time_ms:.2f}ms")
        print(f"  Median time:  {benchmark.median_time_ms:.2f}ms")
        print(f"  Complexity:   {benchmark.complexity_estimate}")

        if benchmark.document_sizes and benchmark.execution_times:
            print("  Size vs Time:")
            for size, time_ms in zip(benchmark.document_sizes, benchmark.execution_times):
                print(f"    {size:5} elements: {time_ms:6.2f}ms")

    print("\n3. Testing nested document performance...")
    nested_benchmark = tester.test_nested_performance()
    print(f"Nested detection complexity: {nested_benchmark.complexity_estimate}")
    print(f"Average time: {nested_benchmark.average_time_ms:.2f}ms")

    print("\n4. Analysis Summary:")
    print("=" * 50)

    # Identify O(n²) algorithms
    quadratic_algorithms = []
    for test_name, benchmark in scalability_results.items():
        if "n²" in benchmark.complexity_estimate or "worse" in benchmark.complexity_estimate:
            quadratic_algorithms.append(test_name)

    if quadratic_algorithms:
        print(f"⚠️  O(n²) or worse algorithms detected: {', '.join(quadratic_algorithms)}")
    else:
        print("✅ No obvious O(n²) algorithms detected")

    # Performance recommendations
    print("\n5. Optimization Recommendations:")
    print("-" * 40)

    if bottlenecks['slowest_time_ms'] > 100:
        print(f"• Focus optimization on '{bottlenecks['slowest_method']}' method")

    for test_name, benchmark in scalability_results.items():
        if "n²" in benchmark.complexity_estimate:
            print(f"• Optimize '{test_name}' - showing quadratic complexity")

    if nested_benchmark.average_time_ms > 200:
        print("• Improve nested element traversal efficiency")

    # Specific algorithm analysis
    print("\n6. Algorithm-Specific Analysis:")
    print("-" * 35)

    layer_benchmark = scalability_results.get('layer_detection')
    if layer_benchmark and layer_benchmark.average_time_ms > 50:
        print("• Layer detection: Consider pre-indexing groups by ID/class")

    animation_benchmark = scalability_results.get('animation_detection')
    if animation_benchmark and animation_benchmark.average_time_ms > 30:
        print("• Animation detection: Consider caching XPath results")

    section_benchmark = scalability_results.get('section_detection')
    if section_benchmark and section_benchmark.average_time_ms > 20:
        print("• Section detection: Consider text element pre-filtering")

    print("\n7. Target Performance Goals:")
    print("-" * 30)
    print("• Achieve 50%+ performance improvement")
    print("• Reduce algorithm complexity from O(n²) to O(n log n) or better")
    print("• Optimize for documents with 1000+ elements")
    print("• Maintain accuracy while improving speed")

    # Save results for comparison
    results_file = project_root / "performance_baseline.json"
    with open(results_file, 'w') as f:
        json.dump({
            'bottlenecks': bottlenecks,
            'scalability': {name: {
                'average_time_ms': bench.average_time_ms,
                'complexity': bench.complexity_estimate,
                'document_sizes': bench.document_sizes,
                'execution_times': bench.execution_times
            } for name, bench in scalability_results.items()},
            'nested_performance': {
                'average_time_ms': nested_benchmark.average_time_ms,
                'complexity': nested_benchmark.complexity_estimate
            }
        }, indent=2)

    print(f"\n📊 Results saved to: {results_file}")


if __name__ == "__main__":
    main()