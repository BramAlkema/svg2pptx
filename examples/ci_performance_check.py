#!/usr/bin/env python3
"""
CI/CD Performance Check Example

This script demonstrates how to integrate the SVG2PPTX performance framework
into a CI/CD pipeline for automated performance regression detection.
"""

import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.performance import (
    PerformanceFramework, PerformanceConfig, MetricsCollector,
    benchmark, get_benchmark_trends
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Define critical benchmarks for CI/CD
# ====================================

@benchmark("ci_svg_parsing", category="critical",
           target_ops_per_sec=5000, tags={"ci", "parsing"})
def ci_benchmark_svg_parsing():
    """Critical SVG parsing performance benchmark for CI."""
    # Simulate SVG parsing work
    time.sleep(0.002)  # 2ms target
    return {"elements_parsed": 100, "ops_per_sec": 50000}


@benchmark("ci_rectangle_conversion", category="critical",
           target_ops_per_sec=10000, tags={"ci", "converters"})
def ci_benchmark_rectangle_conversion():
    """Critical rectangle conversion benchmark for CI."""
    # Simulate rectangle conversion
    time.sleep(0.001)  # 1ms target
    return {"rectangles_converted": 50, "ops_per_sec": 50000}


@benchmark("ci_path_processing", category="critical",
           target_ops_per_sec=3000, tags={"ci", "paths"})
def ci_benchmark_path_processing():
    """Critical path processing benchmark for CI."""
    # Simulate complex path processing
    time.sleep(0.005)  # 5ms target
    return {"paths_processed": 25, "ops_per_sec": 5000}


@benchmark("ci_full_pipeline", category="critical",
           target_ops_per_sec=500, tags={"ci", "integration"})
def ci_benchmark_full_pipeline():
    """Critical end-to-end pipeline benchmark for CI."""
    # Simulate full conversion pipeline
    time.sleep(0.020)  # 20ms target
    return {"documents_converted": 1, "ops_per_sec": 50}


# Performance Check Configuration
# ==============================

class PerformanceCheckConfig:
    """Configuration for CI/CD performance checks."""

    def __init__(self):
        # Critical benchmarks that must pass
        self.critical_benchmarks = [
            "ci_svg_parsing",
            "ci_rectangle_conversion",
            "ci_path_processing",
            "ci_full_pipeline"
        ]

        # Performance thresholds (percentage slower than target)
        self.performance_thresholds = {
            "warning": 0.10,    # 10% slower triggers warning
            "failure": 0.25,    # 25% slower triggers failure
            "critical": 0.50    # 50% slower triggers critical failure
        }

        # Regression detection settings
        self.regression_check_days = 7  # Look back 7 days for trends
        self.min_historical_samples = 3  # Minimum samples for trend analysis

        # CI-specific configuration
        self.max_execution_time = 300  # 5 minutes max for all benchmarks
        self.timeout_per_benchmark = 30  # 30 seconds per benchmark


class PerformanceChecker:
    """Main performance checker for CI/CD integration."""

    def __init__(self, config: Optional[PerformanceCheckConfig] = None):
        self.config = config or PerformanceCheckConfig()

        # Setup performance framework with CI-optimized config
        perf_config = PerformanceConfig(
            benchmark_timeout=self.config.timeout_per_benchmark,
            warmup_iterations=2,  # Fewer warmup iterations for CI
            measurement_iterations=5,  # Fewer measurement iterations for CI
            min_sample_size=3
        )

        self.framework = PerformanceFramework(config=perf_config)
        self.metrics_collector = MetricsCollector(config=perf_config)

        # Results tracking
        self.results = {
            "passed": [],
            "warnings": [],
            "failures": [],
            "critical_failures": [],
            "regressions": [],
            "total_execution_time": 0.0
        }

    def run_performance_check(self) -> bool:
        """
        Run complete performance check for CI/CD.

        Returns:
            True if all checks pass, False if any failures
        """
        logger.info("Starting CI/CD performance check")
        start_time = time.time()

        try:
            # Step 1: Execute critical benchmarks
            self._execute_critical_benchmarks()

            # Step 2: Check for performance regressions
            self._check_performance_regressions()

            # Step 3: Analyze results
            self._analyze_results()

            # Step 4: Generate report
            self._generate_report()

            # Step 5: Determine overall success
            success = self._determine_success()

            total_time = time.time() - start_time
            self.results["total_execution_time"] = total_time

            logger.info(f"Performance check completed in {total_time:.1f}s")
            return success

        except Exception as e:
            logger.error(f"Performance check failed with error: {e}")
            self.results["critical_failures"].append({
                "error": "performance_check_exception",
                "message": str(e)
            })
            return False

    def _execute_critical_benchmarks(self) -> None:
        """Execute all critical benchmarks."""
        logger.info("Executing critical benchmarks")

        for benchmark_name in self.config.critical_benchmarks:
            logger.info(f"Running benchmark: {benchmark_name}")

            try:
                result = self.framework.execute_benchmark(benchmark_name)

                if not result or not result.success:
                    self.results["failures"].append({
                        "benchmark": benchmark_name,
                        "error": "benchmark_execution_failed",
                        "message": result.error_message if result else "No result returned"
                    })
                    continue

                # Collect metrics for trend analysis
                self.metrics_collector.collect_from_result(result)

                # Check performance against targets
                self._check_benchmark_performance(benchmark_name, result)

            except Exception as e:
                logger.error(f"Error executing benchmark {benchmark_name}: {e}")
                self.results["failures"].append({
                    "benchmark": benchmark_name,
                    "error": "benchmark_exception",
                    "message": str(e)
                })

    def _check_benchmark_performance(self, benchmark_name: str, result) -> None:
        """Check individual benchmark performance against thresholds."""
        # Get target performance from benchmark metadata
        benchmark_info = self.framework.get_benchmark_info(benchmark_name)
        if not benchmark_info or not benchmark_info.get("target_ops_per_sec"):
            logger.warning(f"No target performance set for {benchmark_name}")
            return

        target_ops = benchmark_info["target_ops_per_sec"]
        actual_ops = result.ops_per_sec or 0

        if actual_ops == 0:
            self.results["failures"].append({
                "benchmark": benchmark_name,
                "error": "zero_ops_per_sec",
                "message": "Benchmark returned 0 operations per second"
            })
            return

        # Calculate performance ratio (< 1.0 means slower than target)
        performance_ratio = actual_ops / target_ops
        slowdown_percent = (1.0 - performance_ratio)

        logger.info(f"{benchmark_name}: {actual_ops:.0f} ops/sec "
                   f"(target: {target_ops:.0f}, ratio: {performance_ratio:.2f})")

        # Classify performance
        if slowdown_percent >= self.config.performance_thresholds["critical"]:
            self.results["critical_failures"].append({
                "benchmark": benchmark_name,
                "slowdown_percent": slowdown_percent * 100,
                "actual_ops_per_sec": actual_ops,
                "target_ops_per_sec": target_ops,
                "severity": "critical"
            })
        elif slowdown_percent >= self.config.performance_thresholds["failure"]:
            self.results["failures"].append({
                "benchmark": benchmark_name,
                "slowdown_percent": slowdown_percent * 100,
                "actual_ops_per_sec": actual_ops,
                "target_ops_per_sec": target_ops,
                "severity": "failure"
            })
        elif slowdown_percent >= self.config.performance_thresholds["warning"]:
            self.results["warnings"].append({
                "benchmark": benchmark_name,
                "slowdown_percent": slowdown_percent * 100,
                "actual_ops_per_sec": actual_ops,
                "target_ops_per_sec": target_ops,
                "severity": "warning"
            })
        else:
            self.results["passed"].append({
                "benchmark": benchmark_name,
                "performance_ratio": performance_ratio,
                "actual_ops_per_sec": actual_ops,
                "target_ops_per_sec": target_ops
            })

    def _check_performance_regressions(self) -> None:
        """Check for performance regressions using historical data."""
        logger.info("Checking for performance regressions")

        for benchmark_name in self.config.critical_benchmarks:
            try:
                trends = get_benchmark_trends(
                    benchmark_name,
                    days=self.config.regression_check_days
                )

                if "error" in trends:
                    logger.debug(f"No historical data for {benchmark_name}: {trends['error']}")
                    continue

                # Check if we have enough data
                data_points = trends.get("data_points", 0)
                if data_points < self.config.min_historical_samples:
                    logger.debug(f"Insufficient historical data for {benchmark_name} "
                               f"({data_points} samples)")
                    continue

                # Check trends
                trend_data = trends.get("trends", {})
                mean_time_trend = trend_data.get("mean_time_ms", {})

                if mean_time_trend and mean_time_trend.get("direction") == "degrading":
                    change_percent = mean_time_trend.get("change_percent", 0)
                    if abs(change_percent) > 10:  # More than 10% degradation
                        self.results["regressions"].append({
                            "benchmark": benchmark_name,
                            "trend_direction": "degrading",
                            "change_percent": change_percent,
                            "correlation": mean_time_trend.get("correlation", 0),
                            "days_analyzed": self.config.regression_check_days
                        })

            except Exception as e:
                logger.warning(f"Error checking regression for {benchmark_name}: {e}")

    def _analyze_results(self) -> None:
        """Analyze and log results summary."""
        total_benchmarks = len(self.config.critical_benchmarks)
        passed = len(self.results["passed"])
        warnings = len(self.results["warnings"])
        failures = len(self.results["failures"])
        critical_failures = len(self.results["critical_failures"])
        regressions = len(self.results["regressions"])

        logger.info(f"Performance check results:")
        logger.info(f"  Total benchmarks: {total_benchmarks}")
        logger.info(f"  Passed: {passed}")
        logger.info(f"  Warnings: {warnings}")
        logger.info(f"  Failures: {failures}")
        logger.info(f"  Critical failures: {critical_failures}")
        logger.info(f"  Regressions detected: {regressions}")

        # Log detailed failures
        for failure in self.results["failures"]:
            logger.error(f"FAILURE: {failure}")

        for critical in self.results["critical_failures"]:
            logger.error(f"CRITICAL: {critical}")

        for regression in self.results["regressions"]:
            logger.warning(f"REGRESSION: {regression}")

    def _generate_report(self) -> None:
        """Generate performance report for CI/CD."""
        report = {
            "timestamp": time.time(),
            "performance_check": {
                "status": "completed",
                "total_execution_time": self.results["total_execution_time"],
                "benchmarks_executed": len(self.config.critical_benchmarks)
            },
            "results": self.results,
            "summary": {
                "passed": len(self.results["passed"]),
                "warnings": len(self.results["warnings"]),
                "failures": len(self.results["failures"]),
                "critical_failures": len(self.results["critical_failures"]),
                "regressions": len(self.results["regressions"])
            }
        }

        # Save report to file
        report_path = Path("performance_check_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Performance report saved to {report_path}")

    def _determine_success(self) -> bool:
        """Determine overall success of performance check."""
        # Fail if any critical failures
        if self.results["critical_failures"]:
            logger.error("Performance check FAILED: Critical failures detected")
            return False

        # Fail if any benchmark failures
        if self.results["failures"]:
            logger.error("Performance check FAILED: Benchmark failures detected")
            return False

        # Warn about regressions but don't fail (configurable)
        if self.results["regressions"]:
            logger.warning("Performance regressions detected but not failing build")

        # Warn about performance warnings but don't fail
        if self.results["warnings"]:
            logger.warning("Performance warnings detected but not failing build")

        logger.info("Performance check PASSED: All benchmarks within acceptable limits")
        return True


def main() -> int:
    """Main entry point for CI/CD performance check."""
    logger.info("SVG2PPTX CI/CD Performance Check")
    logger.info("=" * 50)

    try:
        # Create and run performance checker
        checker = PerformanceChecker()
        success = checker.run_performance_check()

        # Return appropriate exit code for CI/CD
        if success:
            logger.info("✅ Performance check PASSED")
            return 0
        else:
            logger.error("❌ Performance check FAILED")
            return 1

    except KeyboardInterrupt:
        logger.info("Performance check interrupted by user")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"Unexpected error in performance check: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)