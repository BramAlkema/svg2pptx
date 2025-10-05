#!/usr/bin/env python3
"""
Performance optimization and benchmarking module for SVG2PPTX conversion.

This module provides caching, pooling, batch processing capabilities, and
comprehensive performance benchmarking framework for SVG2PPTX conversion.

Performance Framework Features:
- Unified benchmark registration and execution
- Statistical performance analysis
- Automated regression detection
- Performance trend tracking
- CI/CD integration support
"""

from .base import (
    Benchmark,
    BenchmarkContext,
    ComparisonBenchmark,
    DataGeneratorBenchmark,
    MultiPhaseBenchmark,
    ParameterizedBenchmark,
)
from .batch import BatchProcessor
from .benchmark import BenchmarkEngine, BenchmarkResult, PerformanceMeasurement
from .cache import ColorCache, ConversionCache, PathCache, TransformCache
from .config import PerformanceConfig, get_config, set_config, validate_config
from .decorators import BenchmarkRegistry as DecoratorRegistry
from .decorators import (
    benchmark,
    benchmark_group,
    benchmark_suite,
    clear_registered_benchmarks,
    enable_auto_registration,
    get_registered_benchmarks,
    memory_benchmark,
    parametrized_benchmark,
    performance_critical,
    quick_benchmark,
    regression_test,
    skip_benchmark,
)

# Performance Framework
from .framework import BenchmarkMetadata, BenchmarkRegistry, PerformanceFramework
from .measurement import (
    PerformanceProfiler,
    benchmark_compare,
    measure_block,
    measure_performance,
)
from .metrics import (
    AggregatedMetric,
    MetricPoint,
    MetricsAggregator,
    MetricsCollector,
    TimeSeriesStorage,
    collect_benchmark_metrics,
    get_benchmark_trends,
)
from .optimizer import PerformanceOptimizer
from .pools import ConverterPool, UtilityPool
from .profiler import PerformanceProfiler
from .speedrun_cache import SpeedrunCache, get_speedrun_cache
from .speedrun_cache import enable_speedrun_mode as enable_cache_speedrun
from .speedrun_optimizer import (
    SpeedrunMode,
    SVGSpeedrunOptimizer,
    enable_speedrun_mode,
    get_speedrun_optimizer,
)

__all__ = [
    # Existing performance optimization
    'ConversionCache',
    'PathCache',
    'ColorCache',
    'TransformCache',
    'ConverterPool',
    'UtilityPool',
    'BatchProcessor',
    'PerformanceProfiler',
    'PerformanceOptimizer',
    'SpeedrunCache',
    'SVGSpeedrunOptimizer',
    'SpeedrunMode',
    'get_speedrun_cache',
    'get_speedrun_optimizer',
    'enable_speedrun_mode',
    'enable_cache_speedrun',

    # Performance Framework
    'PerformanceFramework',
    'BenchmarkRegistry',
    'BenchmarkMetadata',
    'PerformanceConfig',
    'get_config',
    'set_config',
    'validate_config',
    'BenchmarkEngine',
    'BenchmarkResult',
    'PerformanceMeasurement',
    'measure_performance',
    'measure_block',
    'PerformanceProfiler',
    'benchmark_compare',

    # Benchmark Decorators and Base Classes
    'benchmark',
    'benchmark_suite',
    'parametrized_benchmark',
    'skip_benchmark',
    'benchmark_group',
    'DecoratorRegistry',
    'enable_auto_registration',
    'get_registered_benchmarks',
    'clear_registered_benchmarks',
    'quick_benchmark',
    'performance_critical',
    'regression_test',
    'memory_benchmark',
    'Benchmark',
    'BenchmarkContext',
    'DataGeneratorBenchmark',
    'MultiPhaseBenchmark',
    'ComparisonBenchmark',
    'ParameterizedBenchmark',

    # Metrics Collection System
    'MetricPoint',
    'AggregatedMetric',
    'TimeSeriesStorage',
    'MetricsAggregator',
    'MetricsCollector',
    'collect_benchmark_metrics',
    'get_benchmark_trends',
]