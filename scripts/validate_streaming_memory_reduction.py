#!/usr/bin/env python3
"""
Validate memory usage reduction for streaming multislide processing.

This script tests streaming vs non-streaming processing to validate
the 30%+ memory usage reduction target for large SVG documents.
"""

import gc
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available, memory measurement will be limited")

from src.multislide.detection import SlideDetector
from src.multislide.config import DetectionConfig
from src.multislide.document import MultiSlideDocument, DocumentConfig
from src.multislide.streaming import (
    StreamingMultislideProcessor,
    StreamingConfig,
    memory_monitoring
)
from tests.support.multislide.performance_helpers import generate_test_svg


class MemoryUsageValidator:
    """Validates memory usage reduction for streaming processing."""

    def __init__(self):
        self.baseline_measurements = {}
        self.streaming_measurements = {}
        self.process = psutil.Process() if PSUTIL_AVAILABLE else None

    def measure_memory_usage(self, operation_name: str) -> Dict[str, float]:
        """Measure current memory usage."""
        if not PSUTIL_AVAILABLE:
            return {"rss_mb": 0.0, "vms_mb": 0.0}

        memory_info = self.process.memory_info()
        return {
            "rss_mb": memory_info.rss / (1024 * 1024),
            "vms_mb": memory_info.vms / (1024 * 1024),
            "timestamp": time.time()
        }

    def test_baseline_processing(self, svg_root, element_count: int) -> Dict[str, Any]:
        """Test baseline (non-streaming) processing."""
        print(f"Testing baseline processing for {element_count} elements...")

        # Force garbage collection before test
        gc.collect()
        start_memory = self.measure_memory_usage("baseline_start")

        # Standard detection and document generation
        detection_config = DetectionConfig()
        detector = SlideDetector(detection_config)

        # Peak memory during detection
        detection_start = self.measure_memory_usage("detection_start")
        boundaries = detector.detect_boundaries(svg_root)
        detection_peak = self.measure_memory_usage("detection_peak")

        # Peak memory during slide generation
        doc_config = DocumentConfig()
        document = MultiSlideDocument(doc_config)

        generation_start = self.measure_memory_usage("generation_start")
        for i, boundary in enumerate(boundaries):
            slide_content = f"<p:sp><p:nvSpPr><p:cNvPr id='{i+1}' name='shape_{i+1}'/></p:nvSpPr></p:sp>"
            document.add_slide(slide_content, title=f"Slide {i+1}")
        generation_peak = self.measure_memory_usage("generation_peak")

        # Final memory usage
        end_memory = self.measure_memory_usage("baseline_end")

        return {
            "element_count": element_count,
            "boundaries_detected": len(boundaries),
            "slides_generated": len(document.slides),
            "memory_start": start_memory,
            "memory_detection_peak": detection_peak,
            "memory_generation_peak": generation_peak,
            "memory_end": end_memory,
            "peak_memory_mb": max(
                detection_peak["rss_mb"],
                generation_peak["rss_mb"]
            ),
            "memory_increase_mb": end_memory["rss_mb"] - start_memory["rss_mb"]
        }

    def test_streaming_processing(self, svg_content: str, element_count: int) -> Dict[str, Any]:
        """Test streaming processing."""
        print(f"Testing streaming processing for {element_count} elements...")

        # Force garbage collection before test
        gc.collect()
        start_memory = self.measure_memory_usage("streaming_start")

        # Configure streaming for memory efficiency
        streaming_config = StreamingConfig.create_memory_efficient()
        if element_count > 5000:
            streaming_config.max_memory_mb = 50
            streaming_config.boundary_detection_threshold = 100
        elif element_count > 1000:
            streaming_config.max_memory_mb = 75
            streaming_config.boundary_detection_threshold = 250

        detection_config = DetectionConfig()
        processor = StreamingMultislideProcessor(detection_config, streaming_config)

        # Track peak memory during streaming
        peak_memory = start_memory["rss_mb"]
        slides_generated = 0

        def memory_callback(stats):
            nonlocal peak_memory
            current_memory = self.measure_memory_usage("streaming_progress")
            peak_memory = max(peak_memory, current_memory["rss_mb"])

        # Process with streaming
        for slide_data in processor.process_svg_stream(svg_content, memory_callback):
            slides_generated += 1
            # Measure memory after each slide
            current_memory = self.measure_memory_usage("streaming_slide")
            peak_memory = max(peak_memory, current_memory["rss_mb"])

        # Final memory measurement
        end_memory = self.measure_memory_usage("streaming_end")
        stats = processor.get_stats()

        return {
            "element_count": element_count,
            "boundaries_detected": stats.boundaries_detected,
            "slides_generated": slides_generated,
            "memory_start": start_memory,
            "memory_end": end_memory,
            "peak_memory_mb": peak_memory,
            "memory_increase_mb": end_memory["rss_mb"] - start_memory["rss_mb"],
            "gc_collections": stats.gc_collections,
            "streaming_stats": stats
        }

    def validate_memory_reduction(self, document_sizes: List[int]) -> Dict[str, Any]:
        """Validate memory reduction across different document sizes."""
        print("=== Streaming Memory Usage Validation ===\n")

        validation_results = {
            "test_cases": [],
            "overall_memory_reduction": 0.0,
            "target_achieved": False,
            "recommendations": []
        }

        for size in document_sizes:
            print(f"\n--- Testing with {size} elements ---")

            # Generate test SVG
            svg_root = generate_test_svg(size)
            svg_content = f'<svg>{svg_root}</svg>'  # Simple wrapper for string processing

            # Test baseline processing
            baseline_results = self.test_baseline_processing(svg_root, size)

            # Test streaming processing
            streaming_results = self.test_streaming_processing(svg_content, size)

            # Calculate memory reduction
            baseline_peak = baseline_results["peak_memory_mb"]
            streaming_peak = streaming_results["peak_memory_mb"]

            if baseline_peak > 0:
                memory_reduction = ((baseline_peak - streaming_peak) / baseline_peak) * 100
            else:
                memory_reduction = 0.0

            test_case = {
                "element_count": size,
                "baseline": baseline_results,
                "streaming": streaming_results,
                "memory_reduction_percent": memory_reduction,
                "memory_reduction_mb": baseline_peak - streaming_peak,
                "target_achieved": memory_reduction >= 30.0
            }

            validation_results["test_cases"].append(test_case)

            # Print results for this test case
            print(f"Baseline peak memory: {baseline_peak:.1f}MB")
            print(f"Streaming peak memory: {streaming_peak:.1f}MB")
            print(f"Memory reduction: {memory_reduction:.1f}%")
            print(f"Target achieved: {'✅ YES' if test_case['target_achieved'] else '❌ NO'}")

        # Calculate overall results
        if validation_results["test_cases"]:
            total_baseline = sum(case["baseline"]["peak_memory_mb"] for case in validation_results["test_cases"])
            total_streaming = sum(case["streaming"]["peak_memory_mb"] for case in validation_results["test_cases"])

            if total_baseline > 0:
                overall_reduction = ((total_baseline - total_streaming) / total_baseline) * 100
                validation_results["overall_memory_reduction"] = overall_reduction
                validation_results["target_achieved"] = overall_reduction >= 30.0

        # Generate recommendations
        self._generate_recommendations(validation_results)

        return validation_results

    def _generate_recommendations(self, results: Dict[str, Any]) -> None:
        """Generate recommendations based on validation results."""
        recommendations = []

        overall_reduction = results["overall_memory_reduction"]

        if overall_reduction >= 30.0:
            recommendations.append(f"✅ Target achieved: {overall_reduction:.1f}% memory reduction")
        else:
            recommendations.append(f"❌ Target not achieved: {overall_reduction:.1f}% reduction (need 30%+)")

        # Analyze by document size
        large_doc_cases = [case for case in results["test_cases"] if case["element_count"] >= 5000]
        if large_doc_cases:
            large_doc_reduction = sum(case["memory_reduction_percent"] for case in large_doc_cases) / len(large_doc_cases)
            if large_doc_reduction < 30.0:
                recommendations.append(f"Large documents need better optimization ({large_doc_reduction:.1f}% reduction)")

        # Check for consistent improvements
        failed_cases = [case for case in results["test_cases"] if not case["target_achieved"]]
        if failed_cases:
            recommendations.append(f"{len(failed_cases)} test cases failed to meet 30% target")

        # Memory efficiency suggestions
        max_streaming_memory = max(case["streaming"]["peak_memory_mb"] for case in results["test_cases"])
        if max_streaming_memory > 100:
            recommendations.append("Consider more aggressive memory limits for large documents")

        results["recommendations"] = recommendations

    def print_detailed_report(self, results: Dict[str, Any]) -> None:
        """Print detailed validation report."""
        print("\n" + "=" * 70)
        print("STREAMING MEMORY USAGE VALIDATION REPORT")
        print("=" * 70)

        print(f"\nOVERALL RESULTS:")
        print(f"Memory reduction: {results['overall_memory_reduction']:.1f}%")
        print(f"Target (30%+): {'✅ ACHIEVED' if results['target_achieved'] else '❌ NOT ACHIEVED'}")

        print(f"\nDETAILED RESULTS BY DOCUMENT SIZE:")
        print(f"{'Size':<8} {'Baseline':<12} {'Streaming':<12} {'Reduction':<12} {'Target':<8}")
        print("-" * 60)

        for case in results["test_cases"]:
            size = case["element_count"]
            baseline = case["baseline"]["peak_memory_mb"]
            streaming = case["streaming"]["peak_memory_mb"]
            reduction = case["memory_reduction_percent"]
            achieved = "✅" if case["target_achieved"] else "❌"

            print(f"{size:<8} {baseline:<12.1f} {streaming:<12.1f} {reduction:<12.1f} {achieved:<8}")

        print(f"\nRECOMMENDATIONS:")
        for rec in results["recommendations"]:
            print(f"• {rec}")

        print(f"\nSTREAMING PERFORMANCE INSIGHTS:")
        for case in results["test_cases"]:
            streaming_stats = case["streaming"]["streaming_stats"]
            print(f"  {case['element_count']} elements: "
                  f"{streaming_stats.gc_collections} GC collections, "
                  f"{streaming_stats.boundaries_detected} boundaries detected")


def main():
    """Run streaming memory validation."""
    if not PSUTIL_AVAILABLE:
        print("❌ psutil is required for memory validation")
        return 1

    validator = MemoryUsageValidator()

    # Test different document sizes
    document_sizes = [1000, 2000, 5000, 8000, 10000]

    try:
        results = validator.validate_memory_reduction(document_sizes)
        validator.print_detailed_report(results)

        # Return success/failure based on target achievement
        return 0 if results["target_achieved"] else 1

    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())