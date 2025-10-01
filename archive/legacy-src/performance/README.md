# SVG2PPTX Performance Framework

A comprehensive performance benchmarking, measurement, and analysis framework designed specifically for SVG2PPTX conversion operations with statistical analysis, regression detection, and CI/CD integration.

## Features

- **Unified Benchmark Registration**: Decorator-based system for easy benchmark creation
- **Statistical Analysis**: Comprehensive statistical analysis with confidence intervals
- **Memory Profiling**: Built-in memory usage tracking with tracemalloc and psutil
- **Metrics Collection**: Time-series storage and historical trend analysis
- **Regression Detection**: Automated performance regression detection
- **CI/CD Integration**: Built for continuous integration workflows

## Quick Start

### Basic Benchmark Creation

```python
from src.performance import benchmark, PerformanceFramework

# Simple function benchmark
@benchmark("rectangle_conversion", category="converters", target_ops_per_sec=10000)
def test_rectangle_conversion():
    # Your benchmark code here
    return convert_rectangle_svg()

# Execute the benchmark
framework = PerformanceFramework()
result = framework.execute_benchmark("rectangle_conversion")
print(f"Average time: {result.mean_time_ms:.2f}ms")
```

### Using the Measurement Decorator

```python
from src.performance import measure_performance

@measure_performance("path_processing", category="paths")
def process_svg_paths(svg_data):
    # Function automatically gets performance measurement
    return parse_and_convert_paths(svg_data)

result = process_svg_paths(my_svg_data)
# Performance data is logged and stored on the function
```

### Manual Performance Measurement

```python
from src.performance import BenchmarkEngine, measure_block

engine = BenchmarkEngine()

# Context manager for code blocks
with measure_block("data_processing") as measurement:
    processed_data = expensive_operation(data)
    measurement['items_processed'] = len(processed_data)

# Direct benchmark execution
def my_benchmark():
    return perform_conversion()

result = engine.execute_benchmark(
    benchmark_function=my_benchmark,
    benchmark_name="conversion_test",
    category="integration"
)
```

## Framework Components

### 1. Performance Framework (Core)

The `PerformanceFramework` is the central orchestration system:

```python
from src.performance import PerformanceFramework, PerformanceConfig

# Create with custom configuration
config = PerformanceConfig(
    benchmark_timeout=60,
    min_sample_size=15,
    warmup_iterations=5
)

framework = PerformanceFramework(config=config)

# Register benchmarks
framework.register_benchmark(
    name="svg_parsing",
    function=parse_svg_function,
    category="parsing",
    target_ops_per_sec=5000
)

# Execute individual benchmarks
result = framework.execute_benchmark("svg_parsing")

# Execute all benchmarks in a category
results = framework.execute_category("parsing")

# Get framework statistics
stats = framework.get_statistics()
```

### 2. Benchmark Engine (Statistical Analysis)

The `BenchmarkEngine` provides comprehensive statistical analysis:

```python
from src.performance import BenchmarkEngine

engine = BenchmarkEngine()

def my_benchmark_function():
    # Simulate work
    time.sleep(0.001)
    return {"result": "success"}

result = engine.execute_benchmark(
    benchmark_function=my_benchmark_function,
    benchmark_name="test_performance",
    category="unit_test",
    warmup_iterations=3,
    measurement_iterations=10,
    timeout_seconds=30
)

# Access statistical results
print(f"Mean time: {result.mean_time_ms:.2f}ms")
print(f"Standard deviation: {result.std_dev_ms:.2f}ms")
print(f"95% confidence interval: {result.confidence_interval}")
print(f"Operations per second: {result.ops_per_sec:.0f}")
```

### 3. Benchmark Decorators

Multiple decorator types for different use cases:

#### Basic Benchmark Decorator

```python
@benchmark(
    name="path_conversion",
    category="converters",
    target_ops_per_sec=1000,
    tags={"performance", "paths"}
)
def benchmark_path_conversion():
    return convert_svg_paths()
```

#### Parametrized Benchmarks

```python
@parametrized_benchmark(
    "matrix_operations",
    category="math",
    parameters={
        "size": [100, 500, 1000],
        "dtype": ["float32", "float64"]
    }
)
def benchmark_matrix_ops(size, dtype):
    return perform_matrix_operations(size, dtype)
```

#### Benchmark Suites

```python
@benchmark_suite("converter_suite", category="converters")
class ConverterBenchmarks:
    @benchmark("rectangle_conversion")
    def test_rectangles(self):
        return convert_rectangles()

    @benchmark("circle_conversion")
    def test_circles(self):
        return convert_circles()
```

#### Convenience Decorators

```python
# Quick benchmark with minimal setup
@quick_benchmark
def simple_test():
    return basic_operation()

# Performance-critical benchmark
@performance_critical
def critical_path_test():
    return critical_operation()

# Regression test with threshold
@regression_test(threshold=0.05)
def regression_check():
    return monitored_operation()

# Memory profiling benchmark
@memory_benchmark
def memory_intensive_test():
    return memory_operation()
```

### 4. Advanced Benchmark Classes

For complex benchmarking scenarios:

#### Data Generator Benchmarks

```python
from src.performance import DataGeneratorBenchmark

class PathProcessingBenchmark(DataGeneratorBenchmark):
    def __init__(self):
        super().__init__(
            name="path_processing",
            category="paths",
            target_ops_per_sec=5000
        )

    def generate_data(self, context):
        # Generate test data
        return create_test_svg_paths(1000)

    def execute_with_data(self, data, context):
        return process_paths(data)

# Run the benchmark
benchmark = PathProcessingBenchmark()
result = benchmark.run()
```

#### Multi-Phase Benchmarks

```python
from src.performance import MultiPhaseBenchmark

class ConversionPipelineBenchmark(MultiPhaseBenchmark):
    def __init__(self):
        super().__init__(
            name="conversion_pipeline",
            category="integration"
        )

    def get_phases(self):
        return ["parsing", "preprocessing", "conversion", "serialization"]

    def execute_phase(self, phase_name, context):
        if phase_name == "parsing":
            return parse_svg(self.test_data)
        elif phase_name == "preprocessing":
            return preprocess_svg(self.parsed_data)
        # ... handle other phases
```

#### Comparison Benchmarks

```python
from src.performance import ComparisonBenchmark

class AlgorithmComparison(ComparisonBenchmark):
    def __init__(self):
        super().__init__(
            name="path_algorithm_comparison",
            category="algorithms"
        )

        # Add implementations to compare
        self.add_implementation("numpy_implementation", numpy_path_processing)
        self.add_implementation("native_implementation", native_path_processing)

    def get_test_data(self, context):
        return generate_path_test_data()

comparison = AlgorithmComparison()
result = comparison.run()
```

### 5. Metrics Collection

Comprehensive metrics collection and analysis:

```python
from src.performance import MetricsCollector, collect_benchmark_metrics

# Automatic collection from benchmark results
collector = MetricsCollector()
collector.collect_from_result(benchmark_result)

# Custom metrics
collector.collect_custom_metric(
    benchmark_name="custom_test",
    category="performance",
    metric_name="processing_rate",
    value=1500.0,
    metadata={"algorithm": "optimized"}
)

# Get benchmark trends
summary = collector.get_benchmark_summary("svg_conversion", days=30)
print(f"Average performance: {summary['metrics']['mean_time_ms']['mean']:.2f}ms")

# Category analysis
category_summary = collector.get_category_summary("converters", days=7)
print(f"Fastest benchmark: {category_summary['category_stats']['fastest_benchmark']}")

# Convenience function
from src.performance import get_benchmark_trends
trends = get_benchmark_trends("important_benchmark", days=14)
```

## Configuration

### Performance Configuration

```python
from src.performance import PerformanceConfig, set_config

config = PerformanceConfig(
    # Storage locations
    baseline_storage="data/performance_baselines/",
    results_storage="data/performance_results/",

    # Execution parameters
    benchmark_timeout=30,
    warmup_iterations=3,
    measurement_iterations=10,
    min_sample_size=10,

    # Statistical analysis
    confidence_level=0.95,
    outlier_detection=True,
    outlier_threshold=2.0,

    # Regression detection
    regression_thresholds={
        "minor": 0.05,    # 5% slower
        "major": 0.15,    # 15% slower
        "critical": 0.30  # 30% slower
    },

    # Memory profiling
    memory_profiling={
        "enabled": True,
        "precision": 3
    }
)

# Set as global configuration
set_config(config)
```

### Environment Variables

```bash
# Configuration via environment variables
export PERFORMANCE_TIMEOUT=60
export PERFORMANCE_MIN_SAMPLES=15
export PERFORMANCE_WARMUP_ITERATIONS=5
export PERFORMANCE_BASELINE_STORAGE="/path/to/baselines/"
export PERFORMANCE_RESULTS_STORAGE="/path/to/results/"
```

## Advanced Features

### 1. Performance Profiler

```python
from src.performance import PerformanceProfiler

profiler = PerformanceProfiler("conversion_pipeline")

with profiler.measure("svg_parsing"):
    parsed_svg = parse_svg_file(svg_path)

with profiler.measure("preprocessing", optimization_level="aggressive"):
    optimized_svg = preprocess_svg(parsed_svg)

with profiler.measure("conversion"):
    pptx_data = convert_to_pptx(optimized_svg)

# Get comprehensive summary
summary = profiler.get_summary()
profiler.log_summary()
```

### 2. Benchmark Comparison

```python
from src.performance import benchmark_compare

def old_algorithm():
    return legacy_conversion()

def new_algorithm():
    return optimized_conversion()

comparison = benchmark_compare(
    func1=old_algorithm,
    func2=new_algorithm,
    func1_name="legacy",
    func2_name="optimized",
    iterations=20,
    warmup=5
)

print(f"Winner: {comparison['winner']}")
print(f"Speedup: {comparison['speedup']:.2f}x")
print(f"Statistical significance: {comparison['analysis']['statistical_significance']}")
```

### 3. Memory Measurement

```python
from src.performance import measure_memory_usage

def memory_intensive_operation():
    # Some operation that uses memory
    data = process_large_dataset()
    return data

result, memory_before, memory_after = measure_memory_usage(memory_intensive_operation)
memory_delta = memory_after - memory_before
print(f"Memory delta: {memory_delta:.1f} MB")
```

## Best Practices

### 1. Benchmark Organization

```python
# Organize benchmarks by category
@benchmark("svg_parsing", category="parsing")
def benchmark_svg_parsing():
    pass

@benchmark("path_conversion", category="converters")
def benchmark_path_conversion():
    pass

@benchmark("full_pipeline", category="integration")
def benchmark_full_pipeline():
    pass
```

### 2. Meaningful Metrics

```python
@benchmark("rectangle_processing", target_ops_per_sec=10000)
def benchmark_rectangles():
    rectangles_processed = process_rectangles(test_data)
    # Return meaningful data for ops_per_sec calculation
    return {
        "rectangles_processed": rectangles_processed,
        "ops_per_sec": rectangles_processed / execution_time
    }
```

### 3. Error Handling

```python
@benchmark("robust_conversion", category="converters")
def benchmark_with_error_handling():
    try:
        result = potentially_failing_operation()
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 4. Data Cleanup

```python
from src.performance import MetricsCollector

# Regular cleanup of old data
collector = MetricsCollector()
deleted_count = collector.cleanup_old_data(days_to_keep=90)
logger.info(f"Cleaned up {deleted_count} old metric records")
```

## Integration Examples

### 1. CI/CD Integration

```python
# ci_performance_check.py
from src.performance import PerformanceFramework, get_benchmark_trends

def main():
    framework = PerformanceFramework()

    # Run critical benchmarks
    critical_benchmarks = [
        "svg_parsing_performance",
        "rectangle_conversion_speed",
        "full_pipeline_benchmark"
    ]

    failed_benchmarks = []

    for benchmark_name in critical_benchmarks:
        result = framework.execute_benchmark(benchmark_name)

        if not result.success:
            failed_benchmarks.append(benchmark_name)
            continue

        # Check for performance regression
        trends = get_benchmark_trends(benchmark_name, days=7)
        if trends.get("trends", {}).get("mean_time_ms", {}).get("direction") == "degrading":
            failed_benchmarks.append(f"{benchmark_name} (regression detected)")

    if failed_benchmarks:
        print(f"❌ Performance check failed: {', '.join(failed_benchmarks)}")
        exit(1)
    else:
        print("✅ All performance benchmarks passed")

if __name__ == "__main__":
    main()
```

### 2. Development Workflow

```python
# development_profiling.py
from src.performance import PerformanceFramework, benchmark

# Development-time benchmarks
@benchmark("dev_svg_parsing", category="development")
def dev_benchmark_parsing():
    return parse_development_svg()

@benchmark("dev_conversion", category="development")
def dev_benchmark_conversion():
    return convert_development_svg()

def profile_development_changes():
    framework = PerformanceFramework()

    # Execute development benchmarks
    dev_results = framework.execute_category("development")

    # Compare with baseline
    for result in dev_results:
        if result.success:
            print(f"{result.name}: {result.mean_time_ms:.2f}ms "
                  f"({result.ops_per_sec:.0f} ops/sec)")

if __name__ == "__main__":
    profile_development_changes()
```

## Troubleshooting

### Common Issues

1. **ImportError for psutil**
   ```python
   # psutil is optional - framework falls back to basic memory tracking
   # Install with: pip install psutil
   ```

2. **Database locked errors**
   ```python
   # If metrics database is locked, check for concurrent access
   # Consider using separate database files for concurrent processes
   ```

3. **Timeout errors**
   ```python
   # Increase timeout for long-running benchmarks
   @benchmark("long_running_test", category="integration")
   def long_benchmark():
       # Set longer timeout in configuration
       pass
   ```

4. **Memory profiling issues**
   ```python
   # Ensure tracemalloc is working properly
   import tracemalloc
   tracemalloc.start()
   # Your benchmark code
   tracemalloc.stop()
   ```

### Performance Tips

1. **Warmup iterations**: Use adequate warmup for consistent results
2. **Sample size**: Increase sample size for better statistical confidence
3. **Outlier detection**: Enable outlier detection for cleaner analysis
4. **Memory cleanup**: Regular cleanup of old metrics data
5. **Database optimization**: Use SSD storage for metrics database

## API Reference

For detailed API documentation, see the individual module docstrings:

- `src.performance.framework` - Core framework and registry
- `src.performance.benchmark` - Benchmark engine and statistical analysis
- `src.performance.decorators` - Decorator system and registration
- `src.performance.base` - Advanced benchmark base classes
- `src.performance.metrics` - Metrics collection and analysis
- `src.performance.measurement` - Measurement utilities and context managers
- `src.performance.config` - Configuration management

## Contributing

When adding new benchmarks or extending the framework:

1. Follow existing naming conventions
2. Add comprehensive tests using the test template system
3. Update documentation with examples
4. Consider backward compatibility
5. Add appropriate error handling

Example test structure:
```python
# tests/unit/performance/test_my_feature.py
import pytest
from src.performance import MyNewFeature

class TestMyNewFeature:
    def test_initialization(self):
        feature = MyNewFeature()
        assert feature is not None

    def test_basic_functionality(self):
        # Test core functionality
        pass

    def test_error_handling(self):
        # Test error conditions
        pass
```