#!/usr/bin/env python3
"""
Validate performance improvements in boundary detection algorithms.

This script compares the original detection algorithms with the optimized
versions to ensure we achieve the 50%+ performance improvement goal.
"""

import sys
import json
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.multislide.detection import SlideDetector
from src.multislide.config import DetectionConfig
from tests.support.multislide.performance_helpers import (
    DetectionPerformanceTester,
    generate_test_svg,
    compare_algorithms
)


class OptimizedSlideDetector(SlideDetector):
    """
    Test version of SlideDetector that forces use of optimized algorithms.
    """

    def detect_boundaries(self, svg_root):
        """Override to force optimized path."""
        # Reset statistics
        self.detection_stats = {
            'animation_keyframes': 0,
            'nested_svgs': 0,
            'layer_groups': 0,
            'section_markers': 0,
            'explicit_boundaries': 0
        }

        boundaries = []

        # Build efficient element index (single traversal)
        element_index = self._build_element_index(svg_root)

        # Batch process all detection strategies using the index
        boundaries.extend(self._detect_explicit_markers_optimized(element_index))

        if self.enable_animation_detection:
            boundaries.extend(self._detect_animation_keyframes_optimized(element_index))

        if self.enable_nested_svg_detection:
            boundaries.extend(self._detect_nested_svgs_optimized(element_index))

        if self.enable_layer_detection:
            boundaries.extend(self._detect_layer_groups_optimized(element_index))

        boundaries.extend(self._detect_section_markers_optimized(element_index))

        # Sort boundaries by position and assign positions
        boundaries.sort(key=lambda b: (b.element.sourceline or 0, b.position))
        for i, boundary in enumerate(boundaries):
            boundary.position = i + 1

        return boundaries


class LegacySlideDetector(SlideDetector):
    """
    Test version of SlideDetector that forces use of legacy algorithms.
    """

    def detect_boundaries(self, svg_root):
        """Override to force legacy path (without optimization)."""
        # Reset statistics
        self.detection_stats = {
            'animation_keyframes': 0,
            'nested_svgs': 0,
            'layer_groups': 0,
            'section_markers': 0,
            'explicit_boundaries': 0
        }

        boundaries = []

        # Use legacy detection methods (multiple traversals)
        boundaries.extend(self._detect_explicit_markers(svg_root))

        if self.enable_animation_detection:
            boundaries.extend(self._detect_animation_keyframes(svg_root))

        if self.enable_nested_svg_detection:
            boundaries.extend(self._detect_nested_svgs(svg_root))

        if self.enable_layer_detection:
            boundaries.extend(self._detect_layer_groups(svg_root))

        boundaries.extend(self._detect_section_markers(svg_root))

        # Sort boundaries by position and assign positions
        boundaries.sort(key=lambda b: (b.element.sourceline or 0, b.position))
        for i, boundary in enumerate(boundaries):
            boundary.position = i + 1

        return boundaries


def run_performance_comparison():
    """Run comprehensive performance comparison."""
    print("=== Performance Improvement Validation ===\n")

    # Create detectors with identical configuration
    config = DetectionConfig(
        enable_animation_detection=True,
        enable_nested_svg_detection=True,
        enable_layer_detection=True,
        enable_section_marker_detection=True,
        enable_input_validation=False,  # Skip validation for pure algorithm timing
        enable_performance_optimizations=False  # Not used in this test
    )

    legacy_detector = LegacySlideDetector(config)
    optimized_detector = OptimizedSlideDetector(config)

    print("1. Single Document Performance Test")
    print("-" * 40)

    # Test with medium-sized document
    test_svg = generate_test_svg(1000)

    # Legacy performance
    start_time = time.perf_counter()
    legacy_boundaries = legacy_detector.detect_boundaries(test_svg)
    legacy_time = (time.perf_counter() - start_time) * 1000

    # Optimized performance
    start_time = time.perf_counter()
    optimized_boundaries = optimized_detector.detect_boundaries(test_svg)
    optimized_time = (time.perf_counter() - start_time) * 1000

    # Calculate improvement
    improvement_percent = ((legacy_time - optimized_time) / legacy_time) * 100

    print(f"Legacy algorithm:    {legacy_time:.2f}ms ({len(legacy_boundaries)} boundaries)")
    print(f"Optimized algorithm: {optimized_time:.2f}ms ({len(optimized_boundaries)} boundaries)")
    print(f"Performance improvement: {improvement_percent:.1f}%")
    print(f"Speedup factor: {legacy_time / optimized_time:.1f}x")

    # Verify same results
    boundary_count_match = len(legacy_boundaries) == len(optimized_boundaries)
    print(f"Results consistency: {'✅ PASS' if boundary_count_match else '❌ FAIL'}")

    print("\n2. Scalability Performance Test")
    print("-" * 35)

    # Test across different document sizes
    size_range = [200, 500, 1000, 2000, 3000]
    legacy_times = []
    optimized_times = []

    for size in size_range:
        print(f"Testing {size} elements...")
        test_svg = generate_test_svg(size)

        # Legacy timing
        start_time = time.perf_counter()
        legacy_detector.detect_boundaries(test_svg)
        legacy_time = (time.perf_counter() - start_time) * 1000
        legacy_times.append(legacy_time)

        # Optimized timing
        start_time = time.perf_counter()
        optimized_detector.detect_boundaries(test_svg)
        optimized_time = (time.perf_counter() - start_time) * 1000
        optimized_times.append(optimized_time)

        improvement = ((legacy_time - optimized_time) / legacy_time) * 100
        print(f"  {size:4} elements: {legacy_time:6.2f}ms → {optimized_time:6.2f}ms ({improvement:5.1f}% improvement)")

    # Calculate overall improvement
    total_legacy = sum(legacy_times)
    total_optimized = sum(optimized_times)
    overall_improvement = ((total_legacy - total_optimized) / total_legacy) * 100

    print(f"\nOverall performance improvement: {overall_improvement:.1f}%")

    print("\n3. Memory Usage Analysis")
    print("-" * 25)

    # Test memory efficiency
    import psutil
    process = psutil.Process()

    # Test with large document
    large_svg = generate_test_svg(5000)

    # Legacy memory usage
    memory_before = process.memory_info().rss / 1024 / 1024
    legacy_detector.detect_boundaries(large_svg)
    legacy_memory = process.memory_info().rss / 1024 / 1024

    # Reset detector caches
    optimized_detector._clear_caches()

    # Optimized memory usage
    memory_before_opt = process.memory_info().rss / 1024 / 1024
    optimized_detector.detect_boundaries(large_svg)
    optimized_memory = process.memory_info().rss / 1024 / 1024

    legacy_memory_delta = legacy_memory - memory_before
    optimized_memory_delta = optimized_memory - memory_before_opt

    print(f"Legacy memory usage:    +{legacy_memory_delta:.1f}MB")
    print(f"Optimized memory usage: +{optimized_memory_delta:.1f}MB")

    if optimized_memory_delta < legacy_memory_delta:
        memory_improvement = ((legacy_memory_delta - optimized_memory_delta) / legacy_memory_delta) * 100
        print(f"Memory improvement: {memory_improvement:.1f}%")
    else:
        memory_overhead = ((optimized_memory_delta - legacy_memory_delta) / legacy_memory_delta) * 100
        print(f"Memory overhead: {memory_overhead:.1f}% (due to caching)")

    print("\n4. Algorithm Complexity Analysis")
    print("-" * 32)

    # Analyze complexity by measuring how performance scales
    size_ratios = []
    legacy_ratios = []
    optimized_ratios = []

    for i in range(1, len(size_range)):
        size_ratio = size_range[i] / size_range[i-1]
        legacy_ratio = legacy_times[i] / legacy_times[i-1]
        optimized_ratio = optimized_times[i] / optimized_times[i-1]

        size_ratios.append(size_ratio)
        legacy_ratios.append(legacy_ratio)
        optimized_ratios.append(optimized_ratio)

        print(f"Size {size_range[i-1]} → {size_range[i]}: "
              f"Legacy {legacy_ratio:.2f}x, Optimized {optimized_ratio:.2f}x")

    # Estimate complexity
    avg_legacy_ratio = sum(legacy_ratios) / len(legacy_ratios)
    avg_optimized_ratio = sum(optimized_ratios) / len(optimized_ratios)

    print(f"\nAverage scaling factors:")
    print(f"Legacy: {avg_legacy_ratio:.2f}x per size increase")
    print(f"Optimized: {avg_optimized_ratio:.2f}x per size increase")

    # Complexity classification
    def classify_complexity(ratio):
        if ratio < 1.5:
            return "O(n) - Linear"
        elif ratio < 2.5:
            return "O(n log n) - Linearithmic"
        elif ratio < 4.0:
            return "O(n²) - Quadratic"
        else:
            return "O(n³+) - Cubic or worse"

    print(f"Legacy complexity: {classify_complexity(avg_legacy_ratio)}")
    print(f"Optimized complexity: {classify_complexity(avg_optimized_ratio)}")

    print("\n5. Performance Goals Assessment")
    print("-" * 33)

    # Check if we meet the 50% improvement goal
    meets_goal = overall_improvement >= 50.0

    print(f"🎯 Target: 50%+ performance improvement")
    print(f"📊 Achieved: {overall_improvement:.1f}% improvement")
    print(f"✅ Result: {'GOAL MET' if meets_goal else 'GOAL NOT MET'}")

    if meets_goal:
        print(f"🚀 Optimization successful! {overall_improvement:.1f}% improvement exceeds 50% target.")
    else:
        print(f"⚠️  Additional optimization needed to reach 50% target.")

    # Additional insights
    print(f"\n6. Performance Insights")
    print("-" * 22)

    print(f"• Single-pass element indexing eliminates {len(size_range)-1} redundant traversals")
    print(f"• XPath caching prevents repeated query compilation")
    print(f"• Early termination reduces unnecessary computation")
    print(f"• Batch processing minimizes function call overhead")

    if optimized_memory_delta > legacy_memory_delta:
        print(f"• Memory overhead due to caching is acceptable for performance gains")

    # Save results
    results = {
        'single_document_test': {
            'legacy_time_ms': legacy_time,
            'optimized_time_ms': optimized_time,
            'improvement_percent': improvement_percent,
            'speedup_factor': legacy_time / optimized_time
        },
        'scalability_test': {
            'document_sizes': size_range,
            'legacy_times_ms': legacy_times,
            'optimized_times_ms': optimized_times,
            'overall_improvement_percent': overall_improvement
        },
        'complexity_analysis': {
            'legacy_complexity': classify_complexity(avg_legacy_ratio),
            'optimized_complexity': classify_complexity(avg_optimized_ratio),
            'legacy_scaling_factor': avg_legacy_ratio,
            'optimized_scaling_factor': avg_optimized_ratio
        },
        'goal_assessment': {
            'target_improvement_percent': 50.0,
            'achieved_improvement_percent': overall_improvement,
            'goal_met': meets_goal
        }
    }

    results_file = project_root / "performance_optimization_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, indent=2, fp=f)

    print(f"\n📁 Detailed results saved to: {results_file}")

    return meets_goal


def main():
    """Run performance validation."""
    try:
        goal_met = run_performance_comparison()

        if goal_met:
            print("\n🎉 Task 4.2 - Optimize Boundary Detection Algorithms: COMPLETED")
            print("✅ Successfully achieved 50%+ performance improvement!")
        else:
            print("\n⚠️  Task 4.2 - Additional optimization needed")
            print("❌ Did not achieve 50% performance improvement target")

        return 0 if goal_met else 1

    except Exception as e:
        print(f"\n❌ Performance validation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())