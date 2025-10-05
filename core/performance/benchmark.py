#!/usr/bin/env python3
"""
Benchmark Engine and Execution Management

Core benchmark execution engine with statistical analysis, memory profiling,
and performance measurement capabilities for the SVG2PPTX performance framework.
"""

import logging
import os
import statistics
import time
import tracemalloc
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Optional psutil dependency for memory profiling
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from .config import PerformanceConfig, get_config

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Standardized benchmark result with statistical analysis."""

    name: str
    category: str
    execution_times_ms: list[float]
    memory_usage_mb: float
    peak_memory_mb: float
    ops_per_sec: float | None = None
    timestamp: float = field(default_factory=time.time)
    implementation: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    # Statistical analysis results
    mean_time_ms: float = 0.0
    median_time_ms: float = 0.0
    std_dev_ms: float = 0.0
    min_time_ms: float = 0.0
    max_time_ms: float = 0.0
    confidence_interval: tuple[float, float] = (0.0, 0.0)

    # Success/failure information
    success: bool = True
    error_message: str | None = None
    warning_messages: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Calculate statistical metrics after initialization."""
        if self.execution_times_ms:
            self._calculate_statistics()

    def _calculate_statistics(self):
        """Calculate statistical metrics from execution times."""
        if not self.execution_times_ms:
            return

        self.mean_time_ms = statistics.mean(self.execution_times_ms)
        self.median_time_ms = statistics.median(self.execution_times_ms)
        self.min_time_ms = min(self.execution_times_ms)
        self.max_time_ms = max(self.execution_times_ms)

        if len(self.execution_times_ms) > 1:
            self.std_dev_ms = statistics.stdev(self.execution_times_ms)

            # Calculate 95% confidence interval
            n = len(self.execution_times_ms)
            if n >= 3:
                # Using t-distribution approximation for small samples
                import math
                t_value = 2.776 if n < 5 else 2.571 if n < 10 else 1.96  # Rough t-values
                margin = t_value * (self.std_dev_ms / math.sqrt(n))
                self.confidence_interval = (
                    self.mean_time_ms - margin,
                    self.mean_time_ms + margin,
                )
        else:
            self.std_dev_ms = 0.0
            self.confidence_interval = (self.mean_time_ms, self.mean_time_ms)

    def speedup_vs(self, baseline: 'BenchmarkResult') -> float:
        """Calculate speedup compared to baseline result."""
        if baseline.mean_time_ms == 0:
            return float('inf') if self.mean_time_ms > 0 else 1.0
        return baseline.mean_time_ms / self.mean_time_ms

    def regression_percent(self, baseline: 'BenchmarkResult') -> float:
        """Calculate regression percentage compared to baseline (positive = slower)."""
        if baseline.mean_time_ms == 0:
            return 0.0
        return ((self.mean_time_ms - baseline.mean_time_ms) / baseline.mean_time_ms) * 100


@dataclass
class MemorySnapshot:
    """Memory usage snapshot during benchmark execution."""

    current_mb: float
    peak_mb: float
    allocated_blocks: int
    timestamp: float = field(default_factory=time.time)


class PerformanceMeasurement:
    """Context manager for performance measurement with statistical sampling."""

    def __init__(self,
                 benchmark_name: str,
                 config: PerformanceConfig,
                 warmup_iterations: int = 0,
                 measurement_iterations: int = 0):
        self.benchmark_name = benchmark_name
        self.config = config
        self.warmup_iterations = warmup_iterations or config.warmup_iterations
        self.measurement_iterations = measurement_iterations or config.measurement_iterations

        self.execution_times: list[float] = []
        self.memory_snapshots: list[MemorySnapshot] = []
        self.start_memory: MemorySnapshot | None = None
        self.peak_memory_mb = 0.0
        self.metadata: dict[str, Any] = {}

        self._tracemalloc_started = False

    @contextmanager
    def measure(self):
        """Context manager for single measurement."""
        # Start memory tracking
        if not tracemalloc.is_tracing():
            tracemalloc.start(self.config.memory_profiling.get('precision', 3))
            self._tracemalloc_started = True

        # Take initial memory snapshot
        self._take_memory_snapshot()

        start_time = time.perf_counter()
        try:
            yield self
        finally:
            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
            self.execution_times.append(execution_time)

            # Take final memory snapshot
            self._take_memory_snapshot()

            # Clean up tracemalloc if we started it
            if self._tracemalloc_started:
                tracemalloc.stop()

    def _take_memory_snapshot(self):
        """Take a memory usage snapshot."""
        try:
            # Get memory info from psutil if available
            current_mb = 0.0
            if PSUTIL_AVAILABLE:
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                current_mb = memory_info.rss / (1024 * 1024)  # RSS in MB

            # Get tracemalloc info if available
            peak_mb = current_mb
            allocated_blocks = 0

            if tracemalloc.is_tracing():
                current_trace, peak_trace = tracemalloc.get_traced_memory()
                peak_mb = max(current_mb, peak_trace / (1024 * 1024))

                # Get number of allocated blocks
                snapshot = tracemalloc.take_snapshot()
                allocated_blocks = len(snapshot.traces)

            snapshot = MemorySnapshot(
                current_mb=current_mb,
                peak_mb=peak_mb,
                allocated_blocks=allocated_blocks,
            )

            self.memory_snapshots.append(snapshot)
            self.peak_memory_mb = max(self.peak_memory_mb, peak_mb)

            # Store start memory for delta calculation
            if self.start_memory is None:
                self.start_memory = snapshot

        except Exception as e:
            logger.warning(f"Failed to take memory snapshot: {e}")

    def get_average_memory_mb(self) -> float:
        """Get average memory usage during measurement."""
        if not self.memory_snapshots:
            return 0.0
        return statistics.mean(s.current_mb for s in self.memory_snapshots)

    def get_memory_delta_mb(self) -> float:
        """Get memory usage delta from start to end."""
        if not self.memory_snapshots or not self.start_memory:
            return 0.0
        return self.memory_snapshots[-1].current_mb - self.start_memory.current_mb

    def result(self) -> BenchmarkResult:
        """Get benchmark result with statistical analysis."""
        avg_memory = self.get_average_memory_mb()

        result = BenchmarkResult(
            name=self.benchmark_name,
            category="unknown",  # Will be set by BenchmarkEngine
            execution_times_ms=self.execution_times.copy(),
            memory_usage_mb=avg_memory,
            peak_memory_mb=self.peak_memory_mb,
            metadata={
                'warmup_iterations': self.warmup_iterations,
                'measurement_iterations': self.measurement_iterations,
                'memory_delta_mb': self.get_memory_delta_mb(),
                'memory_snapshots': len(self.memory_snapshots),
            },
        )

        return result


class TimeoutException(Exception):
    """Exception raised when benchmark execution times out."""
    pass


def timeout_handler(signum, frame):
    """Signal handler for benchmark timeout."""
    raise TimeoutException("Benchmark execution timed out")


class BenchmarkEngine:
    """
    Core benchmark execution engine with statistical analysis and memory profiling.

    Provides comprehensive benchmark execution including:
    - Statistical sampling and analysis
    - Memory profiling and leak detection
    - Timeout and error handling
    - Performance measurement utilities
    """

    def __init__(self, config: PerformanceConfig | None = None):
        """
        Initialize benchmark engine.

        Args:
            config: Optional performance configuration
        """
        self.config = config or get_config()
        self._active_measurements: dict[str, PerformanceMeasurement] = {}
        self._executor = ThreadPoolExecutor(max_workers=1)  # Single-threaded execution

    def execute_benchmark(self,
                         benchmark_function: Callable,
                         benchmark_name: str,
                         category: str = "unknown",
                         warmup_iterations: int | None = None,
                         measurement_iterations: int | None = None,
                         timeout_seconds: float | None = None,
                         **kwargs) -> BenchmarkResult:
        """
        Execute a benchmark function with statistical analysis.

        Args:
            benchmark_function: Function to benchmark
            benchmark_name: Name of the benchmark
            category: Benchmark category
            warmup_iterations: Number of warmup iterations (optional)
            measurement_iterations: Number of measurement iterations (optional)
            timeout_seconds: Execution timeout in seconds (optional)
            **kwargs: Additional arguments passed to benchmark function

        Returns:
            BenchmarkResult with statistical analysis
        """
        warmup_iter = warmup_iterations or self.config.warmup_iterations
        measurement_iter = measurement_iterations or self.config.measurement_iterations
        timeout = timeout_seconds or self.config.benchmark_timeout

        logger.info(f"Executing benchmark '{benchmark_name}' "
                   f"(warmup: {warmup_iter}, measurements: {measurement_iter})")

        try:
            # Create performance measurement context
            measurement = PerformanceMeasurement(
                benchmark_name=benchmark_name,
                config=self.config,
                warmup_iterations=warmup_iter,
                measurement_iterations=measurement_iter,
            )

            # Execute warmup iterations
            if warmup_iter > 0:
                logger.debug(f"Running {warmup_iter} warmup iterations")
                for i in range(warmup_iter):
                    try:
                        self._execute_with_timeout(benchmark_function, timeout, **kwargs)
                    except Exception as e:
                        logger.warning(f"Warmup iteration {i+1} failed: {e}")

            # Execute measurement iterations
            logger.debug(f"Running {measurement_iter} measurement iterations")
            for i in range(measurement_iter):
                with measurement.measure():
                    try:
                        result = self._execute_with_timeout(benchmark_function, timeout, **kwargs)

                        # Extract ops_per_sec if provided by benchmark
                        if isinstance(result, dict) and 'ops_per_sec' in result:
                            measurement.metadata['ops_per_sec'] = result['ops_per_sec']

                    except TimeoutException:
                        logger.error(f"Benchmark '{benchmark_name}' timed out after {timeout}s")
                        return BenchmarkResult(
                            name=benchmark_name,
                            category=category,
                            execution_times_ms=[],
                            memory_usage_mb=0.0,
                            peak_memory_mb=0.0,
                            success=False,
                            error_message=f"Benchmark timed out after {timeout} seconds",
                        )
                    except Exception as e:
                        logger.error(f"Benchmark '{benchmark_name}' failed on iteration {i+1}: {e}")
                        return BenchmarkResult(
                            name=benchmark_name,
                            category=category,
                            execution_times_ms=[],
                            memory_usage_mb=0.0,
                            peak_memory_mb=0.0,
                            success=False,
                            error_message=str(e),
                        )

            # Get final result with statistical analysis
            result = measurement.result()
            result.category = category

            # Calculate ops_per_sec if not provided
            if result.ops_per_sec is None and result.mean_time_ms > 0:
                result.ops_per_sec = 1000.0 / result.mean_time_ms  # ops per second

            # Detect outliers and add warnings
            self._detect_outliers(result)

            logger.info(f"Benchmark '{benchmark_name}' completed: "
                       f"{result.mean_time_ms:.2f}ms avg, "
                       f"{result.ops_per_sec:.0f} ops/sec")

            return result

        except Exception as e:
            logger.error(f"Benchmark engine error for '{benchmark_name}': {e}")
            logger.debug(traceback.format_exc())

            return BenchmarkResult(
                name=benchmark_name,
                category=category,
                execution_times_ms=[],
                memory_usage_mb=0.0,
                peak_memory_mb=0.0,
                success=False,
                error_message=f"Benchmark engine error: {str(e)}",
            )

    def _execute_with_timeout(self,
                             benchmark_function: Callable,
                             timeout_seconds: float,
                             **kwargs) -> Any:
        """Execute benchmark function with timeout using thread executor."""
        try:
            future = self._executor.submit(benchmark_function, **kwargs)
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError:
            raise TimeoutException(f"Benchmark execution timed out after {timeout_seconds} seconds")

    def _detect_outliers(self, result: BenchmarkResult) -> None:
        """Detect outliers in execution times and add warnings."""
        if len(result.execution_times_ms) < 3 or not self.config.outlier_detection:
            return

        times = result.execution_times_ms
        mean_time = result.mean_time_ms
        std_dev = result.std_dev_ms

        if std_dev == 0:
            return

        threshold = self.config.outlier_threshold
        outliers = []

        for i, time_ms in enumerate(times):
            z_score = abs(time_ms - mean_time) / std_dev
            if z_score > threshold:
                outliers.append((i, time_ms, z_score))

        if outliers:
            outlier_info = [f"iteration {i+1}: {time:.2f}ms (z={z:.1f})"
                           for i, time, z in outliers]
            result.warning_messages.append(
                f"Detected {len(outliers)} outliers: {', '.join(outlier_info)}",
            )
            logger.warning(f"Benchmark '{result.name}' has {len(outliers)} outliers")

    def create_measurement_context(self, benchmark_name: str) -> PerformanceMeasurement:
        """
        Create a performance measurement context for manual measurement.

        Args:
            benchmark_name: Name of the benchmark

        Returns:
            PerformanceMeasurement context manager
        """
        return PerformanceMeasurement(benchmark_name, self.config)

    def analyze_results(self, results: list[BenchmarkResult]) -> dict[str, Any]:
        """
        Analyze multiple benchmark results for trends and comparisons.

        Args:
            results: List of benchmark results to analyze

        Returns:
            Analysis summary with statistics and trends
        """
        if not results:
            return {"error": "No results to analyze"}

        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]

        analysis = {
            "total_benchmarks": len(results),
            "successful": len(successful_results),
            "failed": len(failed_results),
            "success_rate": len(successful_results) / len(results) * 100,
            "categories": {},
            "performance_summary": {},
            "warnings": [],
        }

        if not successful_results:
            analysis["warnings"].append("No successful benchmarks to analyze")
            return analysis

        # Category-wise analysis
        by_category = {}
        for result in successful_results:
            if result.category not in by_category:
                by_category[result.category] = []
            by_category[result.category].append(result)

        for category, cat_results in by_category.items():
            avg_time = statistics.mean(r.mean_time_ms for r in cat_results)
            avg_ops = statistics.mean(r.ops_per_sec for r in cat_results if r.ops_per_sec)

            analysis["categories"][category] = {
                "benchmark_count": len(cat_results),
                "avg_time_ms": avg_time,
                "avg_ops_per_sec": avg_ops,
                "fastest_benchmark": min(cat_results, key=lambda r: r.mean_time_ms).name,
                "slowest_benchmark": max(cat_results, key=lambda r: r.mean_time_ms).name,
            }

        # Overall performance summary
        all_times = [r.mean_time_ms for r in successful_results]
        all_ops = [r.ops_per_sec for r in successful_results if r.ops_per_sec]

        analysis["performance_summary"] = {
            "fastest_time_ms": min(all_times),
            "slowest_time_ms": max(all_times),
            "median_time_ms": statistics.median(all_times),
            "avg_time_ms": statistics.mean(all_times),
            "highest_ops_per_sec": max(all_ops) if all_ops else 0,
            "median_ops_per_sec": statistics.median(all_ops) if all_ops else 0,
        }

        return analysis

    def shutdown(self):
        """Clean up resources used by the benchmark engine."""
        self._executor.shutdown(wait=True)
        logger.debug("Benchmark engine shutdown complete")