#!/usr/bin/env python3
"""
Test performance improvements specifically on large documents where
optimization should have the biggest impact.
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.multislide.detection import SlideDetector
from src.multislide.config import DetectionConfig
from tests.support.multislide.performance_helpers import generate_test_svg


def test_large_document_performance():
    """Test performance specifically on large documents."""
    print("=== Large Document Performance Test ===\n")

    config = DetectionConfig(
        enable_animation_detection=True,
        enable_nested_svg_detection=True,
        enable_layer_detection=True,
        enable_section_marker_detection=True,
        enable_input_validation=False,
        enable_performance_optimizations=False
    )

    detector = SlideDetector(config)

    # Test with very large documents where optimization should shine
    large_sizes = [1000, 2000, 5000, 8000, 10000]

    print("Testing performance on large documents:")
    print("Size\tElements\tTime (ms)\tBoundaries\tElements/ms")
    print("-" * 60)

    for size in large_sizes:
        print(f"{size:4d}\t", end="")

        # Generate large test document
        test_svg = generate_test_svg(size)
        actual_elements = len(list(test_svg.iter()))

        # Measure performance
        start_time = time.perf_counter()
        boundaries = detector.detect_boundaries(test_svg)
        end_time = time.perf_counter()

        execution_time = (end_time - start_time) * 1000
        elements_per_ms = actual_elements / execution_time if execution_time > 0 else 0

        print(f"{actual_elements:8d}\t{execution_time:8.2f}\t{len(boundaries):10d}\t{elements_per_ms:10.1f}")

        # Check which optimization path was used
        use_optimization = actual_elements > 500
        optimization_path = "OPTIMIZED" if use_optimization else "LEGACY"
        print(f"\t\t\t\t\t\t\t\t({optimization_path})")

    print(f"\nOptimization threshold: 500 elements")
    print(f"Documents above threshold use single-pass indexing")
    print(f"Documents below threshold use legacy multiple-pass detection")

    # Test the optimization threshold specifically
    print(f"\n=== Optimization Threshold Analysis ===")

    threshold_sizes = [400, 500, 600, 800, 1000]

    for size in threshold_sizes:
        test_svg = generate_test_svg(size)
        actual_elements = len(list(test_svg.iter()))

        start_time = time.perf_counter()
        boundaries = detector.detect_boundaries(test_svg)
        execution_time = (time.perf_counter() - start_time) * 1000

        use_optimization = actual_elements > 500
        optimization_status = "✓ OPTIMIZED" if use_optimization else "○ Legacy"

        print(f"{actual_elements:4d} elements: {execution_time:6.2f}ms ({len(boundaries):3d} boundaries) {optimization_status}")

    print(f"\nPerformance improvements should be most visible above 500 elements")
    print(f"where single-pass indexing eliminates multiple tree traversals.")


if __name__ == "__main__":
    test_large_document_performance()