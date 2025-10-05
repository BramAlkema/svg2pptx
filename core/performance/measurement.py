#!/usr/bin/env python3
"""
Performance Measurement Utilities

Additional utilities and decorators for performance measurement
in the SVG2PPTX performance framework.
"""

import functools
import logging
import time
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any, Dict, Optional, Tuple, TypeVar, cast

from .benchmark import BenchmarkEngine
from .config import get_config

logger = logging.getLogger(__name__)

# Type variable for decorated functions
F = TypeVar('F', bound=Callable[..., Any])


def measure_performance(benchmark_name: str | None = None,
                       category: str = "general",
                       warmup_iterations: int = 0,
                       measurement_iterations: int = 1,
                       log_results: bool = True) -> Callable[[F], F]:
    """
    Decorator to measure performance of a function.

    Args:
        benchmark_name: Name for the benchmark (defaults to function name)
        category: Benchmark category
        warmup_iterations: Number of warmup iterations
        measurement_iterations: Number of measurement iterations
        log_results: Whether to log results

    Returns:
        Decorated function with performance measurement
    """
    def decorator(func: F) -> F:
        name = benchmark_name or f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            engine = BenchmarkEngine()

            # Store the original function result
            original_result = None

            def benchmark_func():
                nonlocal original_result
                original_result = func(*args, **kwargs)
                return original_result

            result = engine.execute_benchmark(
                benchmark_function=benchmark_func,
                benchmark_name=name,
                category=category,
                warmup_iterations=warmup_iterations,
                measurement_iterations=measurement_iterations,
            )

            if log_results and result.success:
                logger.info(f"Performance: {name} executed in {result.mean_time_ms:.2f}ms "
                           f"({result.ops_per_sec:.0f} ops/sec)")
            elif not result.success:
                logger.error(f"Performance measurement failed for {name}: {result.error_message}")

            # Store result in wrapper function metadata for later retrieval
            if not hasattr(wrapper, '_performance_results'):
                wrapper._performance_results = []
            wrapper._performance_results.append(result)

            # Return the original function's result
            return original_result

        return cast(F, wrapper)
    return decorator


@contextmanager
def measure_block(block_name: str,
                 category: str = "code_block",
                 log_result: bool = True):
    """
    Context manager to measure performance of a code block.

    Args:
        block_name: Name for the measured block
        category: Benchmark category
        log_result: Whether to log the result

    Yields:
        Dictionary to store additional metadata

    Example:
        with measure_block("data_processing") as measurement:
            # Your code here
            data = process_large_dataset()
            measurement['items_processed'] = len(data)
    """
    config = get_config()
    engine = BenchmarkEngine(config)
    measurement_context = engine.create_measurement_context(block_name)

    metadata = {}

    with measurement_context.measure():
        start_time = time.perf_counter()
        try:
            yield metadata
        finally:
            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000

            if log_result:
                logger.info(f"Block '{block_name}' executed in {execution_time:.2f}ms")

            # Store additional metadata
            measurement_context.metadata.update(metadata)


class PerformanceProfiler:
    """
    Simple performance profiler for tracking multiple measurements.
    """

    def __init__(self, name: str = "profiler"):
        self.name = name
        self.measurements: dict[str, List[float]] = {}
        self.metadata: dict[str, dict[str, Any]] = {}

    @contextmanager
    def measure(self, operation_name: str, **metadata):
        """
        Measure a single operation.

        Args:
            operation_name: Name of the operation
            **metadata: Additional metadata to store
        """
        start_time = time.perf_counter()
        try:
            yield
        finally:
            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000

            # Store measurement
            if operation_name not in self.measurements:
                self.measurements[operation_name] = []
                self.metadata[operation_name] = {}

            self.measurements[operation_name].append(execution_time)
            self.metadata[operation_name].update(metadata)

    def get_summary(self) -> dict[str, Any]:
        """
        Get summary of all measurements.

        Returns:
            Dictionary with performance summary
        """
        import statistics

        summary = {
            "profiler_name": self.name,
            "total_operations": len(self.measurements),
            "operations": {},
        }

        for operation, times in self.measurements.items():
            if times:
                operation_summary = {
                    "count": len(times),
                    "total_time_ms": sum(times),
                    "avg_time_ms": statistics.mean(times),
                    "min_time_ms": min(times),
                    "max_time_ms": max(times),
                    "metadata": self.metadata.get(operation, {}),
                }

                if len(times) > 1:
                    operation_summary["std_dev_ms"] = statistics.stdev(times)
                    operation_summary["median_time_ms"] = statistics.median(times)

                summary["operations"][operation] = operation_summary

        return summary

    def reset(self):
        """Reset all measurements."""
        self.measurements.clear()
        self.metadata.clear()

    def log_summary(self):
        """Log performance summary."""
        summary = self.get_summary()

        logger.info(f"Performance Summary for '{self.name}':")
        logger.info(f"  Total operations: {summary['total_operations']}")

        for operation, stats in summary["operations"].items():
            logger.info(f"  {operation}:")
            logger.info(f"    Count: {stats['count']}")
            logger.info(f"    Average: {stats['avg_time_ms']:.2f}ms")
            logger.info(f"    Range: {stats['min_time_ms']:.2f} - {stats['max_time_ms']:.2f}ms")


def benchmark_compare(func1: Callable,
                     func2: Callable,
                     func1_name: str = "function1",
                     func2_name: str = "function2",
                     iterations: int = 10,
                     warmup: int = 3) -> dict[str, Any]:
    """
    Compare performance of two functions.

    Args:
        func1: First function to compare
        func2: Second function to compare
        func1_name: Name for first function
        func2_name: Name for second function
        iterations: Number of iterations for each function
        warmup: Number of warmup iterations

    Returns:
        Comparison results
    """
    engine = BenchmarkEngine()

    result1 = engine.execute_benchmark(
        benchmark_function=func1,
        benchmark_name=func1_name,
        category="comparison",
        warmup_iterations=warmup,
        measurement_iterations=iterations,
    )

    result2 = engine.execute_benchmark(
        benchmark_function=func2,
        benchmark_name=func2_name,
        category="comparison",
        warmup_iterations=warmup,
        measurement_iterations=iterations,
    )

    if not result1.success or not result2.success:
        return {
            "error": "One or both benchmarks failed",
            "result1": result1,
            "result2": result2,
        }

    speedup = result1.speedup_vs(result2)
    winner = func1_name if result1.mean_time_ms < result2.mean_time_ms else func2_name

    return {
        "winner": winner,
        "speedup": speedup,
        "results": {
            func1_name: {
                "avg_time_ms": result1.mean_time_ms,
                "ops_per_sec": result1.ops_per_sec,
                "std_dev_ms": result1.std_dev_ms,
            },
            func2_name: {
                "avg_time_ms": result2.mean_time_ms,
                "ops_per_sec": result2.ops_per_sec,
                "std_dev_ms": result2.std_dev_ms,
            },
        },
        "analysis": {
            "faster_function": winner,
            "speed_improvement": f"{speedup:.2f}x" if speedup != float('inf') else "∞",
            "time_difference_ms": abs(result1.mean_time_ms - result2.mean_time_ms),
            "statistical_significance": result1.std_dev_ms + result2.std_dev_ms < abs(result1.mean_time_ms - result2.mean_time_ms),
        },
    }


# Convenience functions for quick measurements

def time_function(func: Callable, *args, **kwargs) -> tuple[Any, float]:
    """
    Time a single function call.

    Args:
        func: Function to time
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        Tuple of (function_result, execution_time_ms)
    """
    start_time = time.perf_counter()
    result = func(*args, **kwargs)
    end_time = time.perf_counter()
    execution_time = (end_time - start_time) * 1000
    return result, execution_time


def measure_memory_usage(func: Callable, *args, **kwargs) -> tuple[Any, float, float]:
    """
    Measure memory usage of a function call.

    Args:
        func: Function to measure
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        Tuple of (function_result, memory_before_mb, memory_after_mb)
    """
    # Try to import psutil, fallback to 0 if not available
    try:
        import os

        import psutil
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / (1024 * 1024)
    except ImportError:
        memory_before = 0.0

    result = func(*args, **kwargs)

    try:
        memory_after = process.memory_info().rss / (1024 * 1024)
    except (ImportError, NameError):
        memory_after = 0.0

    return result, memory_before, memory_after