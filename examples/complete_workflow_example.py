#!/usr/bin/env python3
"""
Complete Performance Framework Workflow Example

This example demonstrates the complete workflow of the SVG2PPTX performance
framework, including benchmark registration, execution, and analysis.
"""

import time
import random
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.performance import (
    PerformanceFramework, BenchmarkEngine, MetricsCollector,
    BenchmarkMetadata, PerformanceConfig
)


def create_sample_benchmarks():
    """Create sample benchmark functions for testing."""

    def svg_parsing_benchmark():
        """Sample SVG parsing benchmark."""
        # Simulate SVG parsing work
        elements = random.randint(50, 200)
        time.sleep(elements * 0.00002)  # 0.02ms per element
        return {
            "elements_parsed": elements,
            "ops_per_sec": elements / 0.001
        }

    def rectangle_conversion_benchmark():
        """Sample rectangle conversion benchmark."""
        # Simulate rectangle conversion
        rectangles = random.randint(20, 100)
        time.sleep(rectangles * 0.00001)  # 0.01ms per rectangle
        return {
            "rectangles_converted": rectangles,
            "ops_per_sec": rectangles / 0.001
        }

    def path_processing_benchmark():
        """Sample path processing benchmark."""
        # Simulate complex path processing
        paths = random.randint(10, 50)
        time.sleep(paths * 0.0001)  # 0.1ms per path
        return {
            "paths_processed": paths,
            "ops_per_sec": paths / 0.001
        }

    def full_pipeline_benchmark():
        """Sample full pipeline benchmark."""
        # Simulate full conversion pipeline
        time.sleep(random.uniform(0.015, 0.025))  # 15-25ms
        return {
            "documents_converted": 1,
            "ops_per_sec": 50
        }

    return {
        "svg_parsing": svg_parsing_benchmark,
        "rectangle_conversion": rectangle_conversion_benchmark,
        "path_processing": path_processing_benchmark,
        "full_pipeline": full_pipeline_benchmark
    }


def demonstrate_complete_workflow():
    """Demonstrate complete performance framework workflow."""
    print("Complete Performance Framework Workflow")
    print("=" * 50)

    # Step 1: Setup configuration
    print("\n1. Setting up configuration...")
    config = PerformanceConfig(
        benchmark_timeout=10,
        warmup_iterations=2,
        measurement_iterations=5,
        min_sample_size=3
    )

    # Step 2: Create framework and collectors
    print("2. Initializing framework...")
    framework = PerformanceFramework(config=config)
    metrics_collector = MetricsCollector(config=config)

    # Step 3: Create and register benchmarks
    print("3. Registering benchmarks...")
    benchmarks = create_sample_benchmarks()

    # Register benchmarks with the framework
    framework.register_benchmark(
        name="svg_parsing",
        function=benchmarks["svg_parsing"],
        category="parsing",
        target_ops_per_sec=5000,
        tags={"core", "parsing"}
    )

    framework.register_benchmark(
        name="rectangle_conversion",
        function=benchmarks["rectangle_conversion"],
        category="converters",
        target_ops_per_sec=10000,
        tags={"geometry", "converters"}
    )

    framework.register_benchmark(
        name="path_processing",
        function=benchmarks["path_processing"],
        category="converters",
        target_ops_per_sec=3000,
        tags={"paths", "complex"}
    )

    framework.register_benchmark(
        name="full_pipeline",
        function=benchmarks["full_pipeline"],
        category="integration",
        target_ops_per_sec=500,
        tags={"integration", "end-to-end"}
    )

    # Step 4: Execute individual benchmarks
    print("\n4. Executing individual benchmarks...")
    individual_results = {}

    for benchmark_name in ["svg_parsing", "rectangle_conversion", "path_processing", "full_pipeline"]:
        print(f"   Running {benchmark_name}...")
        result = framework.execute_benchmark(benchmark_name)

        if result and result.get('success', False):
            individual_results[benchmark_name] = result
            print(f"   ✅ {benchmark_name}: {result.get('mean_time_ms', 0):.2f}ms "
                  f"({result.get('ops_per_sec', 0):.0f} ops/sec)")
        else:
            print(f"   ❌ {benchmark_name}: Failed")

    # Step 5: Execute by category
    print("\n5. Executing benchmarks by category...")

    # Execute converter benchmarks
    converter_results = framework.execute_category("converters")
    print(f"   Converters: {len(converter_results)} benchmarks executed")
    for result in converter_results:
        if result.get('success', False):
            print(f"     - {result.get('benchmark_name', 'unknown')}: {result.get('mean_time_ms', 0):.2f}ms")

    # Execute integration benchmarks
    integration_results = framework.execute_category("integration")
    print(f"   Integration: {len(integration_results)} benchmarks executed")
    for result in integration_results:
        if result.get('success', False):
            print(f"     - {result.get('benchmark_name', 'unknown')}: {result.get('mean_time_ms', 0):.2f}ms")

    # Step 6: Analyze results using BenchmarkEngine
    print("\n6. Analyzing results with BenchmarkEngine...")
    engine = BenchmarkEngine(config)

    # Skip the analysis step as the framework returns dict format, not BenchmarkResult objects
    print("   Skipping detailed analysis (framework returns dict format)")

    # Simple result summary
    successful_count = len([r for r in individual_results.values() if r.get('success', False)])
    total_count = len(individual_results)

    print(f"   Simple analysis:")
    print(f"     - Total benchmarks: {total_count}")
    print(f"     - Successful: {successful_count}")
    print(f"     - Success rate: {(successful_count/total_count)*100:.1f}%")

    # Step 7: Collect and analyze custom metrics
    print("\n7. Collecting custom metrics...")
    metrics_collector.collect_custom_metric(
        benchmark_name="custom_throughput",
        category="performance",
        metric_name="elements_per_second",
        value=15000.0,
        metadata={"algorithm": "optimized", "version": "1.2"}
    )

    metrics_collector.collect_custom_metric(
        benchmark_name="memory_usage",
        category="resources",
        metric_name="peak_memory_mb",
        value=125.5,
        metadata={"workload": "large_svg"}
    )

    # Step 8: Generate performance summary
    print("\n8. Generating performance summaries...")

    try:
        # Get benchmark summary (this might not have historical data yet)
        for benchmark_name in individual_results.keys():
            try:
                summary = metrics_collector.get_benchmark_summary(benchmark_name, days=1)
                if "error" not in summary:
                    print(f"   {benchmark_name} summary:")
                    if "mean_time_ms" in summary.get("metrics", {}):
                        mean_stats = summary["metrics"]["mean_time_ms"]
                        print(f"     - Mean time: {mean_stats['mean']:.2f}ms")
                        print(f"     - Sample count: {mean_stats['sample_count']}")
                else:
                    print(f"   {benchmark_name}: {summary['error']}")
            except Exception as e:
                print(f"   {benchmark_name}: Error getting summary - {e}")

    except Exception as e:
        print(f"   Error generating summaries: {e}")

    # Step 9: Framework statistics
    print("\n9. Framework statistics...")
    stats = framework.get_statistics()
    print(f"   Framework stats:")
    print(f"     - Total benchmarks registered: {stats.get('total_benchmarks', 0)}")
    print(f"     - Categories: {stats.get('categories', 0)}")
    print(f"     - Configuration: {stats.get('config', {}).get('benchmark_timeout', 'unknown')}s timeout")

    # Step 10: Performance comparison example
    print("\n10. Performance comparison example...")

    def old_algorithm():
        time.sleep(0.008)  # 8ms
        return {"result": "processed"}

    def new_algorithm():
        time.sleep(0.005)  # 5ms
        return {"result": "processed"}

    # Manual comparison using BenchmarkEngine
    old_result = engine.execute_benchmark(
        benchmark_function=old_algorithm,
        benchmark_name="old_algorithm",
        category="comparison"
    )

    new_result = engine.execute_benchmark(
        benchmark_function=new_algorithm,
        benchmark_name="new_algorithm",
        category="comparison"
    )

    if old_result.success and new_result.success:
        speedup = old_result.mean_time_ms / new_result.mean_time_ms
        improvement = ((old_result.mean_time_ms - new_result.mean_time_ms) / old_result.mean_time_ms) * 100

        print(f"   Algorithm comparison:")
        print(f"     - Old algorithm: {old_result.mean_time_ms:.2f}ms")
        print(f"     - New algorithm: {new_result.mean_time_ms:.2f}ms")
        print(f"     - Speedup: {speedup:.2f}x")
        print(f"     - Improvement: {improvement:.1f}%")

    print("\n✅ Complete workflow demonstration finished!")
    print(f"\n📊 Final Results Summary:")
    print(f"   - Benchmarks executed: {len(individual_results)}")

    if individual_results:
        # Calculate average from dict results
        times = [r.get('mean_time_ms', 0) for r in individual_results.values() if r.get('success', False)]
        if times:
            print(f"   - Average execution time: {sum(times) / len(times):.2f}ms")
            best_key = min(individual_results.keys(), key=lambda k: individual_results[k].get('mean_time_ms', float('inf')))
            worst_key = max(individual_results.keys(), key=lambda k: individual_results[k].get('mean_time_ms', 0))
            print(f"   - Best performer: {best_key}")
            print(f"   - Slowest performer: {worst_key}")
        else:
            print("   - No successful benchmarks to analyze")


if __name__ == "__main__":
    demonstrate_complete_workflow()