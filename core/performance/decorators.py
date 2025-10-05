#!/usr/bin/env python3
"""
Benchmark Decorators and Registration System

Provides easy-to-use decorators for benchmark registration with automatic
registration, parameter validation, and metadata support.
"""

import functools
import logging
from collections.abc import Callable
from typing import Any, Dict, List, Optional, Set, TypeVar, Union

from .framework import BenchmarkMetadata, PerformanceFramework

logger = logging.getLogger(__name__)

# Type variable for decorated functions
F = TypeVar('F', bound=Callable[..., Any])

# Global benchmark registry for automatic registration
_global_benchmarks: dict[str, BenchmarkMetadata] = {}
_auto_register = True


def enable_auto_registration(enabled: bool = True) -> None:
    """Enable or disable automatic benchmark registration."""
    global _auto_register
    _auto_register = enabled
    logger.debug(f"Automatic benchmark registration: {'enabled' if enabled else 'disabled'}")


def get_registered_benchmarks() -> dict[str, BenchmarkMetadata]:
    """Get all globally registered benchmarks."""
    return _global_benchmarks.copy()


def clear_registered_benchmarks() -> None:
    """Clear all globally registered benchmarks."""
    global _global_benchmarks
    _global_benchmarks.clear()
    logger.debug("Cleared all registered benchmarks")


def benchmark(name: str | None = None,
             category: str = "general",
             target_ops_per_sec: float | None = None,
             regression_threshold: float | None = None,
             tags: set[str] | list[str] | None = None,
             description: str | None = None,
             setup: Callable | None = None,
             teardown: Callable | None = None,
             warmup_iterations: int | None = None,
             measurement_iterations: int | None = None,
             enabled: bool = True,
             framework: PerformanceFramework | None = None) -> Callable[[F], F]:
    """
    Decorator to register a function as a benchmark.

    Args:
        name: Unique benchmark name (defaults to function name)
        category: Benchmark category (e.g., "paths", "filters")
        target_ops_per_sec: Target operations per second
        regression_threshold: Custom regression threshold (0.0-1.0)
        tags: Tags for grouping benchmarks
        description: Human-readable description
        setup: Setup function called before benchmark
        teardown: Teardown function called after benchmark
        warmup_iterations: Number of warmup iterations
        measurement_iterations: Number of measurement iterations
        enabled: Whether this benchmark is enabled
        framework: Optional specific framework instance to register with

    Returns:
        Decorated function with benchmark metadata

    Example:
        @benchmark("fast_conversion", category="converters", target_ops_per_sec=10000)
        def test_rectangle_conversion():
            # Benchmark implementation
            return convert_rectangle()

        @benchmark(tags={"performance", "critical"}, description="Path processing benchmark")
        def benchmark_path_processing():
            return process_paths()
    """
    def decorator(func: F) -> F:
        # Determine benchmark name
        benchmark_name = name or f"{func.__module__}.{func.__qualname__}"

        # Validate parameters
        validation_errors = _validate_benchmark_parameters(
            benchmark_name, category, target_ops_per_sec, regression_threshold, tags,
        )
        if validation_errors:
            raise ValueError(f"Invalid benchmark parameters for '{benchmark_name}': {', '.join(validation_errors)}")

        # Convert tags to set
        tag_set = set()
        if tags:
            if isinstance(tags, (list, tuple)):
                tag_set = set(tags)
            elif isinstance(tags, set):
                tag_set = tags
            else:
                raise ValueError(f"Tags must be a set, list, or tuple, got {type(tags)}")

        # Extract description from docstring if not provided
        benchmark_description = description
        if not benchmark_description and func.__doc__:
            benchmark_description = func.__doc__.strip().split('\n')[0]

        # Create benchmark metadata
        metadata = BenchmarkMetadata(
            name=benchmark_name,
            category=category,
            function=func,
            target_ops_per_sec=target_ops_per_sec,
            regression_threshold=regression_threshold,
            tags=tag_set,
            description=benchmark_description,
            setup_function=setup,
            teardown_function=teardown,
        )

        # Store additional metadata on the function
        func._benchmark_metadata = metadata
        func._benchmark_enabled = enabled
        func._warmup_iterations = warmup_iterations
        func._measurement_iterations = measurement_iterations

        # Register globally if auto-registration is enabled
        if _auto_register and enabled:
            _global_benchmarks[benchmark_name] = metadata
            logger.debug(f"Auto-registered benchmark: {benchmark_name} (category: {category})")

        # Register with specific framework if provided
        if framework and enabled:
            framework.registry.register(metadata)
            logger.debug(f"Registered benchmark '{benchmark_name}' with framework")

        # Add convenience methods to the function
        func.get_metadata = lambda: metadata
        func.is_enabled = lambda: enabled
        func.get_benchmark_name = lambda: benchmark_name

        return func

    return decorator


def benchmark_suite(name: str,
                   category: str = "suite",
                   description: str | None = None,
                   tags: set[str] | list[str] | None = None,
                   setup_all: Callable | None = None,
                   teardown_all: Callable | None = None) -> Callable[[F], F]:
    """
    Decorator to mark a class as a benchmark suite.

    Args:
        name: Suite name
        category: Suite category
        description: Suite description
        tags: Suite tags
        setup_all: Setup function for entire suite
        teardown_all: Teardown function for entire suite

    Example:
        @benchmark_suite("path_processing", category="paths", description="Path processing benchmarks")
        class PathBenchmarks:
            @benchmark("bezier_evaluation")
            def test_bezier_curves(self):
                return evaluate_bezier_curves()

            @benchmark("path_parsing")
            def test_path_parsing(self):
                return parse_svg_paths()
    """
    def decorator(cls: F) -> F:
        # Store suite metadata on the class
        cls._suite_name = name
        cls._suite_category = category
        cls._suite_description = description or cls.__doc__
        cls._suite_tags = set(tags) if tags else set()
        cls._suite_setup = setup_all
        cls._suite_teardown = teardown_all

        # Find all benchmark methods in the class
        benchmark_methods = []
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if hasattr(attr, '_benchmark_metadata'):
                benchmark_methods.append((attr_name, attr))

        cls._benchmark_methods = benchmark_methods
        logger.debug(f"Benchmark suite '{name}' registered with {len(benchmark_methods)} benchmarks")

        return cls

    return decorator


def parametrized_benchmark(name: str | None = None,
                          category: str = "parametrized",
                          parameters: dict[str, list[Any]] | None = None,
                          **kwargs) -> Callable[[F], F]:
    """
    Decorator for parametrized benchmarks that run with different parameter sets.

    Args:
        name: Base benchmark name
        category: Benchmark category
        parameters: Dictionary of parameter names to value lists
        **kwargs: Additional benchmark decorator arguments

    Example:
        @parametrized_benchmark(
            "matrix_multiplication",
            category="math",
            parameters={
                "size": [100, 500, 1000],
                "dtype": ["float32", "float64"]
            }
        )
        def benchmark_matrix_multiply(size, dtype):
            return multiply_matrices(size, dtype)
    """
    def decorator(func: F) -> F:
        if not parameters:
            # No parameters, treat as regular benchmark
            return benchmark(name, category, **kwargs)(func)

        # Generate parameter combinations
        param_combinations = _generate_parameter_combinations(parameters)

        # Create separate benchmark for each parameter combination
        for i, param_combo in enumerate(param_combinations):
            param_name_parts = [f"{k}={v}" for k, v in param_combo.items()]
            param_suffix = "_".join(param_name_parts)
            benchmark_name = f"{name or func.__name__}_{param_suffix}"

            # Create wrapper function for this parameter combination
            def create_wrapper(params):
                @functools.wraps(func)
                def wrapper():
                    return func(**params)
                return wrapper

            param_wrapper = create_wrapper(param_combo)
            param_wrapper.__name__ = benchmark_name

            # Apply benchmark decorator to wrapper
            benchmark(
                benchmark_name,
                category=category,
                description=f"{func.__doc__ or 'Parametrized benchmark'} (params: {param_combo})",
                **kwargs,
            )(param_wrapper)

        return func

    return decorator


def skip_benchmark(reason: str = "Benchmark disabled") -> Callable[[F], F]:
    """
    Decorator to skip a benchmark with a reason.

    Args:
        reason: Reason for skipping the benchmark

    Example:
        @skip_benchmark("Feature not implemented yet")
        @benchmark("future_feature")
        def test_future_feature():
            pass
    """
    def decorator(func: F) -> F:
        func._benchmark_skip_reason = reason
        func._benchmark_enabled = False
        logger.debug(f"Benchmark '{func.__name__}' marked as skipped: {reason}")
        return func

    return decorator


def benchmark_group(*group_tags: str) -> Callable[[F], F]:
    """
    Decorator to add a benchmark to one or more groups.

    Args:
        *group_tags: Group tags to add to the benchmark

    Example:
        @benchmark_group("critical", "performance")
        @benchmark("important_feature")
        def test_important_feature():
            pass
    """
    def decorator(func: F) -> F:
        if hasattr(func, '_benchmark_metadata'):
            func._benchmark_metadata.tags.update(group_tags)
        else:
            # Store groups for later when benchmark decorator is applied
            if not hasattr(func, '_pending_groups'):
                func._pending_groups = set()
            func._pending_groups.update(group_tags)
        return func

    return decorator


class BenchmarkRegistry:
    """
    Enhanced benchmark registry with discovery and validation.
    """

    def __init__(self):
        self.benchmarks: dict[str, BenchmarkMetadata] = {}
        self.suites: dict[str, Any] = {}

    def discover_benchmarks(self,
                           module_names: list[str] | None = None,
                           include_patterns: list[str] | None = None,
                           exclude_patterns: list[str] | None = None) -> int:
        """
        Discover benchmarks from modules.

        Args:
            module_names: Specific modules to search
            include_patterns: Patterns to include
            exclude_patterns: Patterns to exclude

        Returns:
            Number of benchmarks discovered
        """
        discovered = 0

        # Use globally registered benchmarks
        for name, metadata in _global_benchmarks.items():
            if self._should_include_benchmark(name, include_patterns, exclude_patterns):
                self.benchmarks[name] = metadata
                discovered += 1

        logger.info(f"Discovered {discovered} benchmarks")
        return discovered

    def _should_include_benchmark(self,
                                 name: str,
                                 include_patterns: list[str] | None,
                                 exclude_patterns: list[str] | None) -> bool:
        """Check if benchmark should be included based on patterns."""
        # Implementation for pattern matching
        if exclude_patterns:
            for pattern in exclude_patterns:
                if pattern in name:
                    return False

        if include_patterns:
            for pattern in include_patterns:
                if pattern in name:
                    return True
            return False  # Must match at least one include pattern

        return True

    def register_from_globals(self) -> int:
        """Register all globally registered benchmarks."""
        count = 0
        for name, metadata in _global_benchmarks.items():
            self.benchmarks[name] = metadata
            count += 1
        return count


def _validate_benchmark_parameters(name: str,
                                 category: str,
                                 target_ops_per_sec: float | None,
                                 regression_threshold: float | None,
                                 tags: set[str] | list[str] | None) -> list[str]:
    """Validate benchmark decorator parameters."""
    errors = []

    # Validate name
    if not name or not isinstance(name, str):
        errors.append("name must be a non-empty string")

    # Validate category
    if not category or not isinstance(category, str):
        errors.append("category must be a non-empty string")

    # Validate target_ops_per_sec
    if target_ops_per_sec is not None and (not isinstance(target_ops_per_sec, (int, float)) or target_ops_per_sec <= 0):
        errors.append("target_ops_per_sec must be a positive number")

    # Validate regression_threshold
    if regression_threshold is not None and (not isinstance(regression_threshold, (int, float)) or not 0 <= regression_threshold <= 1):
        errors.append("regression_threshold must be a number between 0 and 1")

    # Validate tags
    if tags is not None:
        if not isinstance(tags, (list, tuple, set)):
            errors.append("tags must be a list, tuple, or set")
        else:
            for tag in tags:
                if not isinstance(tag, str):
                    errors.append("all tags must be strings")

    return errors


def _generate_parameter_combinations(parameters: dict[str, list[Any]]) -> list[dict[str, Any]]:
    """Generate all parameter combinations for parametrized benchmarks."""
    import itertools

    if not parameters:
        return [{}]

    keys = list(parameters.keys())
    values = list(parameters.values())

    combinations = []
    for value_combo in itertools.product(*values):
        combinations.append(dict(zip(keys, value_combo)))

    return combinations


# Convenience functions for common benchmark patterns

def quick_benchmark(func: F) -> F:
    """Quick benchmark with minimal configuration."""
    return benchmark()(func)


def performance_critical(func: F) -> F:
    """Mark a benchmark as performance-critical."""
    return benchmark_group("critical", "performance")(benchmark()(func))


def regression_test(threshold: float = 0.05) -> Callable[[F], F]:
    """Mark a benchmark as a regression test with specific threshold."""
    def decorator(func: F) -> F:
        return benchmark(regression_threshold=threshold, tags={"regression"})(func)
    return decorator


def memory_benchmark(func: F) -> F:
    """Mark a benchmark for memory profiling."""
    return benchmark(tags={"memory"}, description="Memory usage benchmark")(func)


# Export all public functions and classes
__all__ = [
    'benchmark',
    'benchmark_suite',
    'parametrized_benchmark',
    'skip_benchmark',
    'benchmark_group',
    'BenchmarkRegistry',
    'enable_auto_registration',
    'get_registered_benchmarks',
    'clear_registered_benchmarks',
    'quick_benchmark',
    'performance_critical',
    'regression_test',
    'memory_benchmark',
]