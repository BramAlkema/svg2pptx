#!/usr/bin/env python3
"""
Benchmark Base Classes

Provides base classes for creating complex benchmarks with setup/teardown,
data generation, and multi-phase execution patterns.
"""

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .benchmark import BenchmarkEngine, BenchmarkResult
from .config import PerformanceConfig, get_config

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkContext:
    """Context object passed to benchmark methods."""

    name: str
    category: str
    config: PerformanceConfig
    metadata: dict[str, Any] = field(default_factory=dict)
    iterations: int = 0
    current_iteration: int = 0


class Benchmark(ABC):
    """
    Base class for complex benchmarks with setup/teardown lifecycle.

    Provides a structured approach to benchmark implementation with:
    - Setup and teardown methods
    - Data generation and preparation
    - Multiple execution phases
    - Result validation and processing

    Example:
        class PathProcessingBenchmark(Benchmark):
            def setup(self, context):
                self.test_data = generate_path_data(1000)

            def execute(self, context):
                return process_paths(self.test_data)

            def teardown(self, context):
                cleanup_resources()
    """

    def __init__(self,
                 name: str,
                 category: str = "benchmark",
                 description: str | None = None,
                 target_ops_per_sec: float | None = None):
        """
        Initialize benchmark.

        Args:
            name: Benchmark name
            category: Benchmark category
            description: Human-readable description
            target_ops_per_sec: Target performance
        """
        self.name = name
        self.category = category
        self.description = description or self.__class__.__doc__
        self.target_ops_per_sec = target_ops_per_sec

        self._setup_completed = False
        self._teardown_completed = False

    @abstractmethod
    def execute(self, context: BenchmarkContext) -> Any:
        """
        Execute the benchmark.

        Args:
            context: Benchmark execution context

        Returns:
            Benchmark result data
        """
        pass

    def setup(self, context: BenchmarkContext) -> None:
        """
        Setup method called before benchmark execution.

        Args:
            context: Benchmark execution context
        """
        pass

    def teardown(self, context: BenchmarkContext) -> None:
        """
        Teardown method called after benchmark execution.

        Args:
            context: Benchmark execution context
        """
        pass

    def validate_setup(self, context: BenchmarkContext) -> bool:
        """
        Validate that setup was completed successfully.

        Args:
            context: Benchmark execution context

        Returns:
            True if setup is valid
        """
        return True

    def validate_result(self, result: Any, context: BenchmarkContext) -> bool:
        """
        Validate benchmark result.

        Args:
            result: Result from execute method
            context: Benchmark execution context

        Returns:
            True if result is valid
        """
        return result is not None

    def get_metadata(self) -> dict[str, Any]:
        """Get benchmark metadata."""
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "target_ops_per_sec": self.target_ops_per_sec,
            "class": self.__class__.__name__,
        }

    def run(self,
            engine: BenchmarkEngine | None = None,
            config: PerformanceConfig | None = None,
            **kwargs) -> BenchmarkResult:
        """
        Run the complete benchmark lifecycle.

        Args:
            engine: Benchmark engine to use
            config: Performance configuration
            **kwargs: Additional arguments

        Returns:
            BenchmarkResult with execution data
        """
        engine = engine or BenchmarkEngine(config or get_config())
        config = config or get_config()

        # Create context
        context = BenchmarkContext(
            name=self.name,
            category=self.category,
            config=config,
            metadata=kwargs,
        )

        def benchmark_wrapper():
            """Wrapper function for the benchmark engine."""
            # Setup phase
            if not self._setup_completed:
                logger.debug(f"Running setup for benchmark: {self.name}")
                self.setup(context)
                self._setup_completed = True

                if not self.validate_setup(context):
                    raise RuntimeError(f"Setup validation failed for benchmark: {self.name}")

            try:
                # Execute phase
                logger.debug(f"Executing benchmark: {self.name}")
                result = self.execute(context)

                # Validate result
                if not self.validate_result(result, context):
                    logger.warning(f"Result validation failed for benchmark: {self.name}")

                return result

            finally:
                # Teardown phase
                if not self._teardown_completed:
                    logger.debug(f"Running teardown for benchmark: {self.name}")
                    try:
                        self.teardown(context)
                        self._teardown_completed = True
                    except Exception as e:
                        logger.error(f"Teardown failed for benchmark {self.name}: {e}")

        # Execute using benchmark engine
        return engine.execute_benchmark(
            benchmark_function=benchmark_wrapper,
            benchmark_name=self.name,
            category=self.category,
            **kwargs,
        )


class DataGeneratorBenchmark(Benchmark):
    """
    Benchmark that generates test data before execution.

    Useful for benchmarks that need fresh data for each iteration
    or specific data sizes for testing.
    """

    @abstractmethod
    def generate_data(self, context: BenchmarkContext) -> Any:
        """
        Generate test data for the benchmark.

        Args:
            context: Benchmark execution context

        Returns:
            Generated test data
        """
        pass

    def setup(self, context: BenchmarkContext) -> None:
        """Setup with data generation."""
        super().setup(context)
        logger.debug(f"Generating test data for benchmark: {self.name}")
        context.metadata['test_data'] = self.generate_data(context)

    def execute(self, context: BenchmarkContext) -> Any:
        """Execute with generated data."""
        test_data = context.metadata.get('test_data')
        if test_data is None:
            raise RuntimeError("Test data not available - setup may have failed")

        return self.execute_with_data(test_data, context)

    @abstractmethod
    def execute_with_data(self, data: Any, context: BenchmarkContext) -> Any:
        """
        Execute benchmark with generated data.

        Args:
            data: Generated test data
            context: Benchmark execution context

        Returns:
            Benchmark result
        """
        pass


class MultiPhaseBenchmark(Benchmark):
    """
    Benchmark with multiple execution phases.

    Each phase is timed separately and results are aggregated.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.phases: list[str] = []
        self.phase_results: dict[str, list[float]] = {}

    @abstractmethod
    def get_phases(self) -> list[str]:
        """
        Get list of phase names.

        Returns:
            List of phase names
        """
        pass

    @abstractmethod
    def execute_phase(self, phase_name: str, context: BenchmarkContext) -> Any:
        """
        Execute a specific phase.

        Args:
            phase_name: Name of the phase to execute
            context: Benchmark execution context

        Returns:
            Phase result
        """
        pass

    def execute(self, context: BenchmarkContext) -> dict[str, Any]:
        """Execute all phases and collect results."""
        if not self.phases:
            self.phases = self.get_phases()

        results = {}
        total_time = 0

        for phase_name in self.phases:
            logger.debug(f"Executing phase '{phase_name}' for benchmark: {self.name}")

            start_time = time.perf_counter()
            phase_result = self.execute_phase(phase_name, context)
            end_time = time.perf_counter()

            phase_time = (end_time - start_time) * 1000  # Convert to ms
            total_time += phase_time

            results[phase_name] = {
                'result': phase_result,
                'time_ms': phase_time,
            }

            # Track phase times
            if phase_name not in self.phase_results:
                self.phase_results[phase_name] = []
            self.phase_results[phase_name].append(phase_time)

        results['total_time_ms'] = total_time
        results['phase_breakdown'] = {
            phase: times[-1] for phase, times in self.phase_results.items()
        }

        return results


class ComparisonBenchmark(Benchmark):
    """
    Benchmark for comparing multiple implementations.

    Runs multiple implementations with the same input and
    compares their performance.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.implementations: dict[str, Callable] = {}

    def add_implementation(self, name: str, func: Callable) -> None:
        """
        Add an implementation to compare.

        Args:
            name: Implementation name
            func: Implementation function
        """
        self.implementations[name] = func
        logger.debug(f"Added implementation '{name}' to comparison benchmark: {self.name}")

    @abstractmethod
    def get_test_data(self, context: BenchmarkContext) -> Any:
        """
        Get test data for comparison.

        Args:
            context: Benchmark execution context

        Returns:
            Test data to use for all implementations
        """
        pass

    def execute(self, context: BenchmarkContext) -> dict[str, Any]:
        """Execute all implementations and compare results."""
        if not self.implementations:
            raise RuntimeError("No implementations to compare")

        test_data = self.get_test_data(context)
        results = {}

        for impl_name, impl_func in self.implementations.items():
            logger.debug(f"Running implementation '{impl_name}' for benchmark: {self.name}")

            start_time = time.perf_counter()
            impl_result = impl_func(test_data)
            end_time = time.perf_counter()

            execution_time = (end_time - start_time) * 1000  # ms

            results[impl_name] = {
                'result': impl_result,
                'time_ms': execution_time,
                'ops_per_sec': 1000 / execution_time if execution_time > 0 else float('inf'),
            }

        # Calculate relative performance
        times = [r['time_ms'] for r in results.values()]
        fastest_time = min(times)

        for impl_name, impl_data in results.items():
            impl_data['relative_speed'] = fastest_time / impl_data['time_ms']
            impl_data['slowdown_factor'] = impl_data['time_ms'] / fastest_time

        # Add comparison summary
        fastest_impl = min(results.keys(), key=lambda k: results[k]['time_ms'])
        slowest_impl = max(results.keys(), key=lambda k: results[k]['time_ms'])

        results['_comparison_summary'] = {
            'fastest_implementation': fastest_impl,
            'slowest_implementation': slowest_impl,
            'speedup_ratio': results[slowest_impl]['time_ms'] / results[fastest_impl]['time_ms'],
            'total_implementations': len(self.implementations),
        }

        return results


class ParameterizedBenchmark(Benchmark):
    """
    Benchmark that runs with different parameter sets.

    Automatically generates multiple benchmark runs with different
    parameter combinations.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters: dict[str, list[Any]] = {}

    def add_parameter(self, name: str, values: list[Any]) -> None:
        """
        Add a parameter with possible values.

        Args:
            name: Parameter name
            values: List of possible values
        """
        self.parameters[name] = values

    @abstractmethod
    def execute_with_params(self, params: dict[str, Any], context: BenchmarkContext) -> Any:
        """
        Execute benchmark with specific parameters.

        Args:
            params: Parameter values for this run
            context: Benchmark execution context

        Returns:
            Benchmark result
        """
        pass

    def execute(self, context: BenchmarkContext) -> dict[str, Any]:
        """Execute benchmark with all parameter combinations."""
        import itertools

        if not self.parameters:
            return self.execute_with_params({}, context)

        # Generate parameter combinations
        param_names = list(self.parameters.keys())
        param_values = list(self.parameters.values())

        results = {}

        for i, value_combo in enumerate(itertools.product(*param_values)):
            params = dict(zip(param_names, value_combo))
            param_key = "_".join(f"{k}={v}" for k, v in params.items())

            logger.debug(f"Running benchmark with parameters: {params}")

            start_time = time.perf_counter()
            result = self.execute_with_params(params, context)
            end_time = time.perf_counter()

            execution_time = (end_time - start_time) * 1000  # ms

            results[param_key] = {
                'parameters': params,
                'result': result,
                'time_ms': execution_time,
                'ops_per_sec': 1000 / execution_time if execution_time > 0 else float('inf'),
            }

        return results


# Export all classes
__all__ = [
    'Benchmark',
    'BenchmarkContext',
    'DataGeneratorBenchmark',
    'MultiPhaseBenchmark',
    'ComparisonBenchmark',
    'ParameterizedBenchmark',
]