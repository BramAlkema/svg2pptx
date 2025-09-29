#!/usr/bin/env python3
"""
SVG2PPTX Performance Framework Examples

This file demonstrates various ways to use the performance framework
for benchmarking SVG2PPTX conversion operations.
"""

import time
import random
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.performance import (
    benchmark, benchmark_suite, parametrized_benchmark,
    PerformanceFramework, BenchmarkEngine, MetricsCollector,
    measure_performance, measure_block, PerformanceProfiler,
    Benchmark, DataGeneratorBenchmark, MultiPhaseBenchmark,
    ComparisonBenchmark, benchmark_compare
)


# Example 1: Basic Benchmark Decorators
# ====================================

@benchmark("svg_parsing_simple", category="parsing", target_ops_per_sec=5000)
def benchmark_svg_parsing():
    """Simple SVG parsing benchmark."""
    # Simulate SVG parsing work
    time.sleep(random.uniform(0.001, 0.003))
    return {"elements_parsed": 100}


@benchmark("rectangle_conversion", category="converters",
           target_ops_per_sec=10000, tags={"geometry", "basic"})
def benchmark_rectangle_conversion():
    """Rectangle conversion performance test."""
    # Simulate rectangle conversion
    rectangles_converted = random.randint(50, 150)
    time.sleep(rectangles_converted * 0.00001)
    return {
        "rectangles_converted": rectangles_converted,
        "ops_per_sec": rectangles_converted / 0.001  # Simulated ops/sec
    }


# Example 2: Parametrized Benchmarks
# ==================================

@parametrized_benchmark(
    "svg_complexity_test",
    category="scalability",
    parameters={
        "element_count": [100, 500, 1000, 5000],
        "complexity": ["simple", "medium", "complex"]
    }
)
def benchmark_svg_complexity(element_count, complexity):
    """Test performance with different SVG complexity levels."""
    complexity_multiplier = {"simple": 1.0, "medium": 2.0, "complex": 3.0}
    processing_time = (element_count / 10000.0) * complexity_multiplier[complexity]
    time.sleep(processing_time)

    return {
        "elements_processed": element_count,
        "complexity_level": complexity,
        "processing_rate": element_count / processing_time
    }


# Example 3: Benchmark Suites
# ===========================

@benchmark_suite("converter_performance", category="converters",
                 description="Complete converter performance suite")
class ConverterBenchmarkSuite:
    """Comprehensive converter benchmark suite."""

    def setup_suite(self):
        """Setup called once before all benchmarks in the suite."""
        self.test_data = self._generate_test_data()

    def _generate_test_data(self):
        """Generate common test data for all benchmarks."""
        return {
            "rectangles": list(range(100)),
            "circles": list(range(50)),
            "paths": list(range(200))
        }

    @benchmark("rectangle_batch", target_ops_per_sec=8000)
    def benchmark_rectangle_batch(self):
        """Batch rectangle conversion benchmark."""
        time.sleep(0.012)  # Simulate batch processing
        return {"rectangles_processed": len(self.test_data["rectangles"])}

    @benchmark("circle_batch", target_ops_per_sec=6000)
    def benchmark_circle_batch(self):
        """Batch circle conversion benchmark."""
        time.sleep(0.008)  # Simulate batch processing
        return {"circles_processed": len(self.test_data["circles"])}

    @benchmark("path_batch", target_ops_per_sec=4000)
    def benchmark_path_batch(self):
        """Batch path conversion benchmark."""
        time.sleep(0.025)  # Simulate complex path processing
        return {"paths_processed": len(self.test_data["paths"])}


# Example 4: Advanced Benchmark Classes
# =====================================

class SVGProcessingBenchmark(DataGeneratorBenchmark):
    """Data-driven SVG processing benchmark."""

    def __init__(self, svg_size="medium"):
        super().__init__(
            name=f"svg_processing_{svg_size}",
            category="processing",
            description=f"SVG processing benchmark with {svg_size} complexity",
            target_ops_per_sec=2000
        )
        self.svg_size = svg_size

    def generate_data(self, context):
        """Generate test SVG data of specified complexity."""
        size_multiplier = {"small": 1, "medium": 5, "large": 20}
        element_count = 100 * size_multiplier[self.svg_size]

        # Simulate SVG data generation
        svg_data = {
            "elements": [f"element_{i}" for i in range(element_count)],
            "complexity": self.svg_size,
            "estimated_processing_time": element_count * 0.00005
        }
        return svg_data

    def execute_with_data(self, data, context):
        """Execute benchmark with generated data."""
        # Simulate processing
        processing_time = data["estimated_processing_time"]
        time.sleep(processing_time)

        return {
            "elements_processed": len(data["elements"]),
            "processing_time": processing_time,
            "complexity": data["complexity"]
        }


class ConversionPipelineBenchmark(MultiPhaseBenchmark):
    """Multi-phase conversion pipeline benchmark."""

    def __init__(self):
        super().__init__(
            name="conversion_pipeline",
            category="integration",
            description="Complete SVG to PPTX conversion pipeline"
        )

    def get_phases(self):
        """Define the conversion pipeline phases."""
        return ["parsing", "preprocessing", "conversion", "serialization"]

    def execute_phase(self, phase_name, context):
        """Execute a specific pipeline phase."""
        phase_times = {
            "parsing": 0.005,
            "preprocessing": 0.003,
            "conversion": 0.015,
            "serialization": 0.008
        }

        # Simulate phase execution
        phase_time = phase_times.get(phase_name, 0.001)
        time.sleep(phase_time)

        return {
            "phase": phase_name,
            "elements_processed": random.randint(50, 200),
            "phase_time": phase_time
        }


class AlgorithmComparisonBenchmark(ComparisonBenchmark):
    """Compare different processing algorithms."""

    def __init__(self):
        super().__init__(
            name="algorithm_comparison",
            category="algorithms",
            description="Compare path processing algorithms"
        )

        # Add implementations to compare
        self.add_implementation("legacy_algorithm", self._legacy_algorithm)
        self.add_implementation("optimized_algorithm", self._optimized_algorithm)
        self.add_implementation("parallel_algorithm", self._parallel_algorithm)

    def get_test_data(self, context):
        """Generate test data for algorithm comparison."""
        return {
            "path_count": 1000,
            "complexity": "medium",
            "data_size_mb": 2.5
        }

    def _legacy_algorithm(self, test_data):
        """Legacy processing algorithm (slower)."""
        time.sleep(0.025)  # Simulate slower processing
        return {"algorithm": "legacy", "paths_processed": test_data["path_count"]}

    def _optimized_algorithm(self, test_data):
        """Optimized processing algorithm (faster)."""
        time.sleep(0.015)  # Simulate faster processing
        return {"algorithm": "optimized", "paths_processed": test_data["path_count"]}

    def _parallel_algorithm(self, test_data):
        """Parallel processing algorithm (fastest)."""
        time.sleep(0.008)  # Simulate parallel processing
        return {"algorithm": "parallel", "paths_processed": test_data["path_count"]}


# Example 5: Manual Performance Measurement
# =========================================

@measure_performance("decorated_function", category="utilities")
def decorated_processing_function(data_size):
    """Function with automatic performance measurement."""
    # Simulate data processing
    processing_time = data_size * 0.00001
    time.sleep(processing_time)
    return {"data_processed": data_size}


def manual_performance_measurement_example():
    """Example of manual performance measurement."""
    print("\n=== Manual Performance Measurement ===")

    # Using BenchmarkEngine directly
    engine = BenchmarkEngine()

    def test_function():
        time.sleep(random.uniform(0.005, 0.015))
        return {"operation": "completed"}

    result = engine.execute_benchmark(
        benchmark_function=test_function,
        benchmark_name="manual_test",
        category="examples",
        warmup_iterations=3,
        measurement_iterations=10
    )

    print(f"Manual benchmark result:")
    print(f"  Mean time: {result.mean_time_ms:.2f}ms")
    print(f"  Std deviation: {result.std_dev_ms:.2f}ms")
    print(f"  Operations/sec: {result.ops_per_sec:.0f}")


def performance_profiler_example():
    """Example using the PerformanceProfiler."""
    print("\n=== Performance Profiler Example ===")

    profiler = PerformanceProfiler("conversion_example")

    with profiler.measure("initialization"):
        time.sleep(0.002)

    with profiler.measure("data_loading", data_size="large"):
        time.sleep(0.008)

    with profiler.measure("processing", algorithm="optimized"):
        time.sleep(0.015)

    with profiler.measure("finalization"):
        time.sleep(0.003)

    # Get and display summary
    summary = profiler.get_summary()
    print("Profiler Summary:")
    for operation, stats in summary["operations"].items():
        print(f"  {operation}: {stats['avg_time_ms']:.2f}ms "
              f"(count: {stats['count']})")


def measure_block_example():
    """Example using measure_block context manager."""
    print("\n=== Measure Block Example ===")

    with measure_block("svg_processing_block") as measurement:
        # Simulate SVG processing work
        elements_processed = random.randint(100, 500)
        time.sleep(elements_processed * 0.00002)

        # Add metadata to the measurement
        measurement['elements_processed'] = elements_processed
        measurement['algorithm'] = 'standard'


# Example 6: Metrics Collection
# =============================

def metrics_collection_example():
    """Example of comprehensive metrics collection."""
    print("\n=== Metrics Collection Example ===")

    collector = MetricsCollector()

    # Simulate running some benchmarks and collecting metrics
    for i in range(5):
        # Simulate a benchmark result
        from src.performance import BenchmarkResult

        execution_times = [random.uniform(8, 15) for _ in range(10)]
        result = BenchmarkResult(
            name="example_benchmark",
            category="examples",
            execution_times_ms=execution_times,
            memory_usage_mb=random.uniform(10, 50),
            peak_memory_mb=random.uniform(50, 100),
            ops_per_sec=random.uniform(1000, 5000)
        )

        # Collect metrics from the result
        collector.collect_from_result(result)

    # Collect custom metrics
    collector.collect_custom_metric(
        benchmark_name="example_benchmark",
        category="examples",
        metric_name="custom_throughput",
        value=2500.0,
        metadata={"algorithm": "optimized", "data_size": "medium"}
    )

    # Get benchmark summary
    try:
        summary = collector.get_benchmark_summary("example_benchmark", days=1)
        if "error" not in summary:
            print("Benchmark Summary:")
            if "mean_time_ms" in summary["metrics"]:
                mean_stats = summary["metrics"]["mean_time_ms"]
                print(f"  Mean time: {mean_stats['mean']:.2f}ms")
                print(f"  Sample count: {mean_stats['sample_count']}")
        else:
            print(f"Summary error: {summary['error']}")
    except Exception as e:
        print(f"Error getting summary: {e}")


# Example 7: Algorithm Comparison
# ===============================

def algorithm_comparison_example():
    """Example of comparing different algorithms."""
    print("\n=== Algorithm Comparison Example ===")

    def old_path_algorithm():
        """Simulate old path processing algorithm."""
        time.sleep(0.020)
        return {"paths_processed": 100, "algorithm": "legacy"}

    def new_path_algorithm():
        """Simulate new optimized path processing algorithm."""
        time.sleep(0.012)
        return {"paths_processed": 100, "algorithm": "optimized"}

    comparison = benchmark_compare(
        func1=old_path_algorithm,
        func2=new_path_algorithm,
        func1_name="legacy_algorithm",
        func2_name="optimized_algorithm",
        iterations=15,
        warmup=3
    )

    print("Algorithm Comparison Results:")
    print(f"  Winner: {comparison['winner']}")
    print(f"  Speedup: {comparison['speedup']:.2f}x")
    print(f"  Time difference: {comparison['analysis']['time_difference_ms']:.2f}ms")
    print(f"  Statistically significant: {comparison['analysis']['statistical_significance']}")


# Main execution function
# =======================

def run_all_examples():
    """Run all performance framework examples."""
    print("SVG2PPTX Performance Framework Examples")
    print("=" * 50)

    # Create framework instance
    framework = PerformanceFramework()

    # Example 1: Execute simple benchmarks
    print("\n=== Simple Benchmark Execution ===")

    # Execute individual benchmarks
    svg_result = framework.execute_benchmark("svg_parsing_simple")
    if svg_result and svg_result.success:
        print(f"SVG parsing: {svg_result.mean_time_ms:.2f}ms")

    rect_result = framework.execute_benchmark("rectangle_conversion")
    if rect_result and rect_result.success:
        print(f"Rectangle conversion: {rect_result.mean_time_ms:.2f}ms")

    # Example 2: Execute benchmark suite
    print("\n=== Benchmark Suite Execution ===")
    suite_results = framework.execute_category("converters")
    print(f"Executed {len(suite_results)} converter benchmarks")
    for result in suite_results:
        if result.success:
            print(f"  {result.name}: {result.mean_time_ms:.2f}ms")

    # Example 3: Advanced benchmark classes
    print("\n=== Advanced Benchmark Classes ===")

    # Data generator benchmark
    svg_benchmark = SVGProcessingBenchmark("medium")
    svg_result = svg_benchmark.run()
    if svg_result.success:
        print(f"SVG processing: {svg_result.mean_time_ms:.2f}ms")

    # Multi-phase benchmark
    pipeline_benchmark = ConversionPipelineBenchmark()
    pipeline_result = pipeline_benchmark.run()
    if pipeline_result.success:
        print(f"Pipeline benchmark: {pipeline_result.mean_time_ms:.2f}ms")

    # Comparison benchmark
    comparison_benchmark = AlgorithmComparisonBenchmark()
    comparison_result = comparison_benchmark.run()
    if comparison_result.success:
        print("Algorithm comparison completed")

    # Example 4: Manual measurement examples
    manual_performance_measurement_example()
    performance_profiler_example()
    measure_block_example()

    # Example 5: Metrics collection
    metrics_collection_example()

    # Example 6: Algorithm comparison
    algorithm_comparison_example()

    # Example 7: Framework statistics
    print("\n=== Framework Statistics ===")
    stats = framework.get_statistics()
    print(f"Total benchmarks: {stats.get('total_benchmarks', 0)}")
    print(f"Categories: {stats.get('categories', 0)}")

    # Example 8: Decorated function usage
    print("\n=== Decorated Function Example ===")
    result = decorated_processing_function(1000)
    print(f"Processed data: {result}")


if __name__ == "__main__":
    run_all_examples()