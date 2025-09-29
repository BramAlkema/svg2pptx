#!/usr/bin/env python3
"""
Performance benchmarking and testing utilities for multislide detection.

This module provides comprehensive performance measurement tools for boundary
detection algorithms, including complexity analysis and regression testing.
"""

import time
import psutil
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Any, Callable, Optional
from pathlib import Path
import statistics

from lxml import etree as ET


@dataclass
class PerformanceMetrics:
    """Performance measurement results."""

    operation_name: str
    execution_time_ms: float
    memory_usage_mb: float
    element_count: int
    boundary_count: int
    complexity_score: float = 0.0
    operations_per_second: float = 0.0

    def __post_init__(self):
        """Calculate derived metrics."""
        if self.execution_time_ms > 0:
            self.operations_per_second = 1000.0 / self.execution_time_ms


@dataclass
class PerformanceBenchmark:
    """Comprehensive performance benchmark results."""

    test_name: str
    document_sizes: List[int] = field(default_factory=list)
    execution_times: List[float] = field(default_factory=list)
    memory_usage: List[float] = field(default_factory=list)
    boundary_counts: List[int] = field(default_factory=list)

    @property
    def average_time_ms(self) -> float:
        """Calculate average execution time."""
        return statistics.mean(self.execution_times) if self.execution_times else 0.0

    @property
    def median_time_ms(self) -> float:
        """Calculate median execution time."""
        return statistics.median(self.execution_times) if self.execution_times else 0.0

    @property
    def complexity_estimate(self) -> str:
        """Estimate algorithmic complexity based on scaling."""
        if len(self.document_sizes) < 3 or len(self.execution_times) < 3:
            return "insufficient_data"

        # Calculate ratios of time vs size increases
        ratios = []
        for i in range(1, len(self.document_sizes)):
            size_ratio = self.document_sizes[i] / self.document_sizes[i-1]
            time_ratio = self.execution_times[i] / self.execution_times[i-1]
            complexity_ratio = time_ratio / size_ratio
            ratios.append(complexity_ratio)

        avg_ratio = statistics.mean(ratios)

        # Classify complexity
        if avg_ratio < 1.5:
            return "O(n)"
        elif avg_ratio < 3.0:
            return "O(n_log_n)"
        elif avg_ratio < 10.0:
            return "O(n²)"
        else:
            return "O(n³_or_worse)"


class PerformanceProfiler:
    """
    Performance profiler for boundary detection algorithms.

    Provides detailed measurement and analysis of detection performance
    with support for memory tracking and complexity analysis.
    """

    def __init__(self):
        """Initialize performance profiler."""
        self.benchmarks: Dict[str, PerformanceBenchmark] = {}
        self.process = psutil.Process()

    def measure_operation(self,
                         operation: Callable,
                         operation_name: str,
                         svg_element: ET.Element,
                         *args, **kwargs) -> PerformanceMetrics:
        """
        Measure performance of a single detection operation.

        Args:
            operation: Function to measure
            operation_name: Name for identification
            svg_element: SVG element being processed
            *args, **kwargs: Arguments for operation

        Returns:
            Performance metrics for the operation
        """
        # Get initial memory usage
        memory_before = self.process.memory_info().rss / 1024 / 1024  # MB

        # Measure execution time
        start_time = time.perf_counter()
        result = operation(svg_element, *args, **kwargs)
        end_time = time.perf_counter()

        # Get final memory usage
        memory_after = self.process.memory_info().rss / 1024 / 1024  # MB

        # Calculate metrics
        execution_time_ms = (end_time - start_time) * 1000
        memory_usage_mb = memory_after - memory_before
        element_count = len(list(svg_element.iter()))
        boundary_count = len(result) if hasattr(result, '__len__') else 0

        return PerformanceMetrics(
            operation_name=operation_name,
            execution_time_ms=execution_time_ms,
            memory_usage_mb=memory_usage_mb,
            element_count=element_count,
            boundary_count=boundary_count
        )

    def benchmark_scalability(self,
                             operation: Callable,
                             test_name: str,
                             svg_generator: Callable[[int], ET.Element],
                             size_range: List[int]) -> PerformanceBenchmark:
        """
        Benchmark operation scalability across different document sizes.

        Args:
            operation: Function to benchmark
            test_name: Name for benchmark
            svg_generator: Function that generates SVG of given complexity
            size_range: List of element counts to test

        Returns:
            Comprehensive benchmark results
        """
        benchmark = PerformanceBenchmark(test_name=test_name)

        for size in size_range:
            # Generate test SVG
            svg_element = svg_generator(size)

            # Measure performance
            metrics = self.measure_operation(operation, test_name, svg_element)

            # Record results
            benchmark.document_sizes.append(size)
            benchmark.execution_times.append(metrics.execution_time_ms)
            benchmark.memory_usage.append(metrics.memory_usage_mb)
            benchmark.boundary_counts.append(metrics.boundary_count)

        self.benchmarks[test_name] = benchmark
        return benchmark

    def run_regression_test(self,
                           baseline_benchmark: PerformanceBenchmark,
                           current_benchmark: PerformanceBenchmark,
                           tolerance_percent: float = 10.0) -> Dict[str, Any]:
        """
        Compare current performance against baseline.

        Args:
            baseline_benchmark: Previous performance results
            current_benchmark: Current performance results
            tolerance_percent: Acceptable performance degradation

        Returns:
            Regression test results
        """
        if not baseline_benchmark.execution_times or not current_benchmark.execution_times:
            return {"status": "insufficient_data"}

        baseline_avg = baseline_benchmark.average_time_ms
        current_avg = current_benchmark.average_time_ms

        performance_change = ((current_avg - baseline_avg) / baseline_avg) * 100

        status = "pass"
        if performance_change > tolerance_percent:
            status = "regression"
        elif performance_change < -tolerance_percent:
            status = "improvement"

        return {
            "status": status,
            "baseline_avg_ms": baseline_avg,
            "current_avg_ms": current_avg,
            "performance_change_percent": performance_change,
            "tolerance_percent": tolerance_percent,
            "baseline_complexity": baseline_benchmark.complexity_estimate,
            "current_complexity": current_benchmark.complexity_estimate
        }


def generate_test_svg(element_count: int) -> ET.Element:
    """
    Generate test SVG with specified number of elements.

    Args:
        element_count: Number of elements to include

    Returns:
        Generated SVG element for testing
    """
    svg = ET.Element("svg",
                     width="1000",
                     height="1000",
                     xmlns="http://www.w3.org/2000/svg")

    # Add various element types for realistic testing
    elements_per_type = element_count // 5

    # Add rectangles
    for i in range(elements_per_type):
        rect = ET.SubElement(svg, "rect",
                           x=str(i * 10), y=str(i * 10),
                           width="50", height="50",
                           fill=f"rgb({i % 255}, 100, 150)")

    # Add circles
    for i in range(elements_per_type):
        circle = ET.SubElement(svg, "circle",
                             cx=str(200 + i * 15), cy=str(200 + i * 15),
                             r="25", fill=f"rgb(100, {i % 255}, 150)")

    # Add groups (potential layer boundaries)
    for i in range(elements_per_type):
        group = ET.SubElement(svg, "g",
                            id=f"layer-{i}",
                            **{"class": "slide-layer"})

        # Add content to group
        for j in range(3):
            rect = ET.SubElement(group, "rect",
                               x=str(400 + i * 20 + j * 5),
                               y=str(400 + i * 20 + j * 5),
                               width="20", height="20")

    # Add text elements (potential section markers)
    for i in range(elements_per_type):
        text = ET.SubElement(svg, "text",
                           x=str(600 + i * 30), y=str(50 + i * 25))
        text.text = f"Section {i + 1}"

    # Add animation elements
    for i in range(elements_per_type):
        animate = ET.SubElement(svg, "animate",
                              attributeName="opacity",
                              values="0;1;0",
                              dur="2s",
                              begin=f"{i}s")

    return svg


def generate_large_nested_svg(depth: int, children_per_level: int) -> ET.Element:
    """
    Generate deeply nested SVG for stress testing.

    Args:
        depth: Nesting depth
        children_per_level: Number of children at each level

    Returns:
        Nested SVG element
    """
    def create_nested_group(current_depth: int, parent: ET.Element):
        if current_depth >= depth:
            return

        for i in range(children_per_level):
            group = ET.SubElement(parent, "g",
                                id=f"nested-{current_depth}-{i}",
                                **{"class": "nested-layer"})

            # Add some content
            rect = ET.SubElement(group, "rect",
                               x=str(current_depth * 50),
                               y=str(i * 30),
                               width="40", height="25")

            # Recurse
            create_nested_group(current_depth + 1, group)

    svg = ET.Element("svg", width="2000", height="2000",
                     xmlns="http://www.w3.org/2000/svg")
    create_nested_group(0, svg)
    return svg


class DetectionPerformanceTester:
    """
    Specialized performance tester for boundary detection algorithms.
    """

    def __init__(self, detector):
        """Initialize with detector instance."""
        self.detector = detector
        self.profiler = PerformanceProfiler()

    def test_detection_scalability(self) -> Dict[str, PerformanceBenchmark]:
        """Test detection scalability across document sizes."""
        size_range = [100, 500, 1000, 2000, 5000]

        benchmarks = {}

        # Test overall detection
        benchmarks['full_detection'] = self.profiler.benchmark_scalability(
            self.detector.detect_boundaries,
            'full_detection',
            generate_test_svg,
            size_range
        )

        # Test individual detection methods
        benchmarks['animation_detection'] = self.profiler.benchmark_scalability(
            self.detector._detect_animation_keyframes,
            'animation_detection',
            generate_test_svg,
            size_range
        )

        benchmarks['layer_detection'] = self.profiler.benchmark_scalability(
            self.detector._detect_layer_groups,
            'layer_detection',
            generate_test_svg,
            size_range
        )

        benchmarks['section_detection'] = self.profiler.benchmark_scalability(
            self.detector._detect_section_markers,
            'section_detection',
            generate_test_svg,
            size_range
        )

        return benchmarks

    def test_nested_performance(self) -> PerformanceBenchmark:
        """Test performance with deeply nested documents."""
        def nested_generator(complexity: int):
            depth = complexity // 10
            children = 3
            return generate_large_nested_svg(depth, children)

        return self.profiler.benchmark_scalability(
            self.detector.detect_boundaries,
            'nested_detection',
            nested_generator,
            [20, 50, 100, 150, 200]  # Depth levels
        )

    def identify_bottlenecks(self) -> Dict[str, Any]:
        """Identify performance bottlenecks in detection."""
        test_svg = generate_test_svg(1000)

        bottlenecks = {}

        # Measure each detection method individually
        methods = [
            ('explicit_markers', self.detector._detect_explicit_markers),
            ('animation_keyframes', self.detector._detect_animation_keyframes),
            ('nested_svgs', self.detector._detect_nested_svgs),
            ('layer_groups', self.detector._detect_layer_groups),
            ('section_markers', self.detector._detect_section_markers)
        ]

        for method_name, method in methods:
            metrics = self.profiler.measure_operation(method, method_name, test_svg)
            bottlenecks[method_name] = {
                'execution_time_ms': metrics.execution_time_ms,
                'memory_usage_mb': metrics.memory_usage_mb,
                'ops_per_second': metrics.operations_per_second
            }

        # Identify slowest method
        slowest_method = max(bottlenecks.items(),
                           key=lambda x: x[1]['execution_time_ms'])

        return {
            'bottlenecks': bottlenecks,
            'slowest_method': slowest_method[0],
            'slowest_time_ms': slowest_method[1]['execution_time_ms']
        }


def compare_algorithms(old_detector, new_detector, test_name: str) -> Dict[str, Any]:
    """
    Compare performance between old and new detection algorithms.

    Args:
        old_detector: Original detector instance
        new_detector: Optimized detector instance
        test_name: Name for comparison

    Returns:
        Performance comparison results
    """
    profiler = PerformanceProfiler()

    # Test with various document sizes
    size_range = [500, 1000, 2000, 3000]
    old_results = []
    new_results = []

    for size in size_range:
        test_svg = generate_test_svg(size)

        # Measure old algorithm
        old_metrics = profiler.measure_operation(
            old_detector.detect_boundaries,
            f'old_{test_name}',
            test_svg
        )
        old_results.append(old_metrics.execution_time_ms)

        # Measure new algorithm
        new_metrics = profiler.measure_operation(
            new_detector.detect_boundaries,
            f'new_{test_name}',
            test_svg
        )
        new_results.append(new_metrics.execution_time_ms)

    # Calculate improvement
    old_avg = statistics.mean(old_results)
    new_avg = statistics.mean(new_results)
    improvement_percent = ((old_avg - new_avg) / old_avg) * 100

    return {
        'old_average_ms': old_avg,
        'new_average_ms': new_avg,
        'improvement_percent': improvement_percent,
        'size_range': size_range,
        'old_results': old_results,
        'new_results': new_results,
        'meets_50_percent_goal': improvement_percent >= 50.0
    }