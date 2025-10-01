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

from .cache import ConversionCache, PathCache, ColorCache, TransformCache
from .pools import ConverterPool, UtilityPool
from .batch import BatchProcessor
from .profiler import PerformanceProfiler
from .optimizer import PerformanceOptimizer
from .speedrun_cache import SpeedrunCache, get_speedrun_cache, enable_speedrun_mode as enable_cache_speedrun
from .speedrun_optimizer import SVGSpeedrunOptimizer, SpeedrunMode, get_speedrun_optimizer, enable_speedrun_mode

# Performance Framework
from .framework import PerformanceFramework, BenchmarkRegistry, BenchmarkMetadata
from .config import PerformanceConfig, get_config, set_config, validate_config
from .benchmark import BenchmarkEngine, BenchmarkResult, PerformanceMeasurement
from .measurement import measure_performance, measure_block, PerformanceProfiler, benchmark_compare
from .decorators import (
    benchmark, benchmark_suite, parametrized_benchmark, skip_benchmark,
    benchmark_group, BenchmarkRegistry as DecoratorRegistry, enable_auto_registration,
    get_registered_benchmarks, clear_registered_benchmarks, quick_benchmark,
    performance_critical, regression_test, memory_benchmark
)
from .base import (
    Benchmark, BenchmarkContext, DataGeneratorBenchmark, MultiPhaseBenchmark,
    ComparisonBenchmark, ParameterizedBenchmark
)
from .metrics import (
    MetricPoint, AggregatedMetric, TimeSeriesStorage, MetricsAggregator,
    MetricsCollector, collect_benchmark_metrics, get_benchmark_trends
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
    'get_benchmark_trends'
]