#!/usr/bin/env python3
"""
Performance Framework Core

Central orchestration system for SVG2PPTX performance benchmarking,
regression detection, and performance monitoring.
"""

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from .config import PerformanceConfig, get_config, validate_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkMetadata:
    """Metadata for registered benchmarks."""

    name: str
    category: str
    function: Callable
    target_ops_per_sec: float | None = None
    regression_threshold: float | None = None
    tags: set[str] = field(default_factory=set)
    description: str | None = None
    setup_function: Callable | None = None
    teardown_function: Callable | None = None


class BenchmarkRegistry:
    """Registry for managing benchmark functions and metadata."""

    def __init__(self):
        self._benchmarks: dict[str, BenchmarkMetadata] = {}
        self._categories: dict[str, set[str]] = defaultdict(set)
        self._tags: dict[str, set[str]] = defaultdict(set)

    def register(self, metadata: BenchmarkMetadata) -> None:
        """
        Register a benchmark with metadata.

        Args:
            metadata: Benchmark metadata including function and configuration
        """
        if metadata.name in self._benchmarks:
            logger.warning(f"Benchmark '{metadata.name}' already registered, overwriting")

        self._benchmarks[metadata.name] = metadata
        self._categories[metadata.category].add(metadata.name)

        # Register tags
        for tag in metadata.tags:
            self._tags[tag].add(metadata.name)

        logger.debug(f"Registered benchmark: {metadata.name} (category: {metadata.category})")

    def get(self, name: str) -> BenchmarkMetadata | None:
        """Get benchmark metadata by name."""
        return self._benchmarks.get(name)

    def get_by_category(self, category: str) -> list[BenchmarkMetadata]:
        """Get all benchmarks in a category."""
        benchmark_names = self._categories.get(category, set())
        return [self._benchmarks[name] for name in benchmark_names]

    def get_by_tag(self, tag: str) -> list[BenchmarkMetadata]:
        """Get all benchmarks with a specific tag."""
        benchmark_names = self._tags.get(tag, set())
        return [self._benchmarks[name] for name in benchmark_names]

    def list_categories(self) -> list[str]:
        """List all registered benchmark categories."""
        return list(self._categories.keys())

    def list_tags(self) -> list[str]:
        """List all registered tags."""
        return list(self._tags.keys())

    def list_benchmarks(self) -> list[str]:
        """List all registered benchmark names."""
        return list(self._benchmarks.keys())

    def count(self) -> int:
        """Get total number of registered benchmarks."""
        return len(self._benchmarks)


class PerformanceFramework:
    """
    Central orchestration system for performance benchmarking.

    Provides unified interface for:
    - Benchmark registration and discovery
    - Benchmark execution and measurement
    - Performance data collection and analysis
    - Regression detection and reporting
    """

    def __init__(self, config: PerformanceConfig | None = None):
        """
        Initialize performance framework.

        Args:
            config: Optional performance configuration. Uses default if None.
        """
        self.config = config or get_config()
        self.registry = BenchmarkRegistry()

        # Initialize benchmark engine for execution
        self._benchmark_engine = None

        # Validate configuration
        config_errors = validate_config(self.config)
        if config_errors:
            raise ValueError(f"Invalid configuration: {', '.join(config_errors)}")

        # Initialize storage paths
        self._ensure_storage_directories()

        logger.info("Performance framework initialized")

    @property
    def benchmark_engine(self):
        """Get or create benchmark engine instance."""
        if self._benchmark_engine is None:
            # Import here to avoid circular imports
            from .benchmark import BenchmarkEngine
            self._benchmark_engine = BenchmarkEngine(self.config)
        return self._benchmark_engine

    def _ensure_storage_directories(self) -> None:
        """Ensure all required storage directories exist."""
        Path(self.config.baseline_storage).mkdir(parents=True, exist_ok=True)
        Path(self.config.results_storage).mkdir(parents=True, exist_ok=True)

        # Create category subdirectories
        for category in self.config.benchmark_categories.keys():
            Path(self.config.baseline_storage, category).mkdir(exist_ok=True)
            Path(self.config.results_storage, category).mkdir(exist_ok=True)

    def register_benchmark(
        self,
        name: str,
        function: Callable,
        category: str,
        target_ops_per_sec: float | None = None,
        regression_threshold: float | None = None,
        tags: set[str] | None = None,
        description: str | None = None,
        setup_function: Callable | None = None,
        teardown_function: Callable | None = None,
    ) -> None:
        """
        Register a benchmark function.

        Args:
            name: Unique benchmark name
            function: Benchmark function to execute
            category: Benchmark category (e.g., "paths", "filters")
            target_ops_per_sec: Target operations per second
            regression_threshold: Custom regression threshold (0.0-1.0)
            tags: Optional tags for grouping benchmarks
            description: Human-readable description
            setup_function: Optional setup function called before benchmark
            teardown_function: Optional teardown function called after benchmark
        """
        metadata = BenchmarkMetadata(
            name=name,
            category=category,
            function=function,
            target_ops_per_sec=target_ops_per_sec,
            regression_threshold=regression_threshold,
            tags=tags or set(),
            description=description,
            setup_function=setup_function,
            teardown_function=teardown_function,
        )

        self.registry.register(metadata)

    def discover_benchmarks(self, module_path: str | None = None) -> int:
        """
        Discover and register benchmarks from modules.

        Args:
            module_path: Optional specific module path to scan

        Returns:
            Number of benchmarks discovered and registered
        """
        # This is a placeholder for automatic discovery
        # Implementation would scan for @benchmark decorators
        discovered_count = 0

        if module_path:
            # Scan specific module
            logger.debug(f"Scanning module: {module_path}")
        else:
            # Scan all known benchmark locations
            benchmark_paths = [
                "tests/performance/benchmarks/",
                "src/converters/",
                "src/paths/",
                "src/units/",
                "src/performance/benchmarks/",
            ]

            for path in benchmark_paths:
                if Path(path).exists():
                    logger.debug(f"Scanning path: {path}")
                    # Discovery implementation would go here

        logger.info(f"Discovered {discovered_count} benchmarks")
        return discovered_count

    def list_benchmarks(
        self,
        category: str | None = None,
        tag: str | None = None,
        include_metadata: bool = False,
    ) -> list[str] | list[BenchmarkMetadata]:
        """
        List registered benchmarks.

        Args:
            category: Optional category filter
            tag: Optional tag filter
            include_metadata: If True, return full metadata instead of names

        Returns:
            List of benchmark names or metadata objects
        """
        if category:
            benchmarks = self.registry.get_by_category(category)
        elif tag:
            benchmarks = self.registry.get_by_tag(tag)
        else:
            benchmark_names = self.registry.list_benchmarks()
            benchmarks = [self.registry.get(name) for name in benchmark_names]

        if include_metadata:
            return benchmarks
        else:
            return [b.name for b in benchmarks if b is not None]

    def get_benchmark_info(self, name: str) -> dict[str, Any] | None:
        """
        Get detailed information about a benchmark.

        Args:
            name: Benchmark name

        Returns:
            Dictionary with benchmark information or None if not found
        """
        metadata = self.registry.get(name)
        if not metadata:
            return None

        return {
            "name": metadata.name,
            "category": metadata.category,
            "target_ops_per_sec": metadata.target_ops_per_sec,
            "regression_threshold": metadata.regression_threshold,
            "tags": list(metadata.tags),
            "description": metadata.description,
            "has_setup": metadata.setup_function is not None,
            "has_teardown": metadata.teardown_function is not None,
        }

    def execute_benchmark(self, name: str, **kwargs) -> dict[str, Any] | None:
        """
        Execute a single benchmark using the BenchmarkEngine.

        Args:
            name: Benchmark name
            **kwargs: Additional arguments passed to benchmark function

        Returns:
            BenchmarkResult as dictionary or None if benchmark not found
        """
        metadata = self.registry.get(name)
        if not metadata:
            logger.error(f"Benchmark '{name}' not found")
            return None

        # Run setup if available
        if metadata.setup_function:
            try:
                metadata.setup_function()
                logger.debug(f"Setup completed for {name}")
            except Exception as e:
                logger.error(f"Setup failed for {name}: {e}")
                return None

        try:
            # Create a wrapper function that includes kwargs
            def benchmark_wrapper():
                return metadata.function(**kwargs)

            # Execute using BenchmarkEngine with statistical analysis
            result = self.benchmark_engine.execute_benchmark(
                benchmark_function=benchmark_wrapper,
                benchmark_name=name,
                category=metadata.category,
            )

            # Convert BenchmarkResult to dictionary for backward compatibility
            result_dict = {
                "benchmark_name": result.name,
                "category": result.category,
                "execution_times_ms": result.execution_times_ms,
                "mean_time_ms": result.mean_time_ms,
                "median_time_ms": result.median_time_ms,
                "std_dev_ms": result.std_dev_ms,
                "min_time_ms": result.min_time_ms,
                "max_time_ms": result.max_time_ms,
                "confidence_interval": result.confidence_interval,
                "memory_usage_mb": result.memory_usage_mb,
                "peak_memory_mb": result.peak_memory_mb,
                "ops_per_sec": result.ops_per_sec,
                "timestamp": result.timestamp,
                "success": result.success,
                "error_message": result.error_message,
                "warning_messages": result.warning_messages,
                "metadata": result.metadata,
            }

            return result_dict

        finally:
            # Run teardown if available
            if metadata.teardown_function:
                try:
                    metadata.teardown_function()
                    logger.debug(f"Teardown completed for {name}")
                except Exception as e:
                    logger.warning(f"Teardown failed for {name}: {e}")

    def execute_category(self, category: str, **kwargs) -> list[dict[str, Any]]:
        """
        Execute all benchmarks in a category.

        Args:
            category: Category name
            **kwargs: Additional arguments passed to benchmark functions

        Returns:
            List of benchmark execution results
        """
        benchmarks = self.list_benchmarks(category=category)
        results = []

        logger.info(f"Executing {len(benchmarks)} benchmarks in category: {category}")

        for benchmark_name in benchmarks:
            result = self.execute_benchmark(benchmark_name, **kwargs)
            if result:
                results.append(result)

        return results

    def get_statistics(self) -> dict[str, Any]:
        """
        Get framework statistics.

        Returns:
            Dictionary with framework statistics
        """
        return {
            "total_benchmarks": self.registry.count(),
            "categories": len(self.registry.list_categories()),
            "tags": len(self.registry.list_tags()),
            "categories_list": self.registry.list_categories(),
            "config": {
                "timeout": self.config.benchmark_timeout,
                "min_samples": self.config.min_sample_size,
                "confidence_level": self.config.confidence_level,
            },
        }