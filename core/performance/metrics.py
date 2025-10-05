#!/usr/bin/env python3
"""
Metrics Collection and Aggregation System

Provides comprehensive metrics collection for benchmarks with time-series
storage, aggregation functions, and historical data querying capabilities.
"""

import json
import logging
import sqlite3
import statistics
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .benchmark import BenchmarkResult
from .config import PerformanceConfig, get_config

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point with timestamp."""

    timestamp: float
    benchmark_name: str
    category: str
    metric_name: str
    value: float | int | str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure timestamp is properly set."""
        if self.timestamp <= 0:
            self.timestamp = time.time()


@dataclass
class AggregatedMetric:
    """Aggregated metrics over a time period."""

    metric_name: str
    period_start: float
    period_end: float
    sample_count: int
    min_value: float
    max_value: float
    mean_value: float
    median_value: float
    std_dev: float = 0.0
    percentiles: dict[int, float] = field(default_factory=dict)


class TimeSeriesStorage:
    """SQLite-based time-series storage for metrics."""

    def __init__(self, database_path: str):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize the metrics database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    benchmark_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL,
                    string_value TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON metrics(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_benchmark_name ON metrics(benchmark_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metric_name ON metrics(metric_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON metrics(category)")

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get database connection with proper cleanup."""
        conn = sqlite3.connect(str(self.database_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def store_metric(self, metric: MetricPoint) -> None:
        """Store a single metric point."""
        with self._get_connection() as conn:
            # Handle both numeric and string values
            numeric_value = None
            string_value = None

            if isinstance(metric.value, (int, float)):
                numeric_value = float(metric.value)
            else:
                string_value = str(metric.value)

            conn.execute("""
                INSERT INTO metrics
                (timestamp, benchmark_name, category, metric_name, value, string_value, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                metric.timestamp,
                metric.benchmark_name,
                metric.category,
                metric.metric_name,
                numeric_value,
                string_value,
                json.dumps(metric.metadata) if metric.metadata else None,
            ))
            conn.commit()

    def store_metrics(self, metrics: list[MetricPoint]) -> None:
        """Store multiple metric points efficiently."""
        if not metrics:
            return

        with self._get_connection() as conn:
            data = []
            for metric in metrics:
                numeric_value = None
                string_value = None

                if isinstance(metric.value, (int, float)):
                    numeric_value = float(metric.value)
                else:
                    string_value = str(metric.value)

                data.append((
                    metric.timestamp,
                    metric.benchmark_name,
                    metric.category,
                    metric.metric_name,
                    numeric_value,
                    string_value,
                    json.dumps(metric.metadata) if metric.metadata else None,
                ))

            conn.executemany("""
                INSERT INTO metrics
                (timestamp, benchmark_name, category, metric_name, value, string_value, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, data)
            conn.commit()

    def query_metrics(self,
                     benchmark_name: str | None = None,
                     metric_name: str | None = None,
                     category: str | None = None,
                     start_time: float | None = None,
                     end_time: float | None = None,
                     limit: int | None = None) -> list[MetricPoint]:
        """Query metrics with flexible filtering."""
        query = "SELECT * FROM metrics WHERE 1=1"
        params = []

        if benchmark_name:
            query += " AND benchmark_name = ?"
            params.append(benchmark_name)

        if metric_name:
            query += " AND metric_name = ?"
            params.append(metric_name)

        if category:
            query += " AND category = ?"
            params.append(category)

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            results = []

            for row in cursor.fetchall():
                # Parse metadata
                metadata = {}
                if row['metadata']:
                    try:
                        metadata = json.loads(row['metadata'])
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse metadata for metric ID {row['id']}")

                # Get value (numeric or string)
                value = row['value'] if row['value'] is not None else row['string_value']

                metric = MetricPoint(
                    timestamp=row['timestamp'],
                    benchmark_name=row['benchmark_name'],
                    category=row['category'],
                    metric_name=row['metric_name'],
                    value=value,
                    metadata=metadata,
                )
                results.append(metric)

            return results

    def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """Remove metrics older than specified days."""
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)

        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff_time,))
            deleted_count = cursor.rowcount
            conn.commit()

            logger.info(f"Cleaned up {deleted_count} old metric records")
            return deleted_count


class MetricsAggregator:
    """Aggregates metrics data over time periods."""

    def __init__(self, storage: TimeSeriesStorage):
        self.storage = storage

    def aggregate_metric(self,
                        metric_name: str,
                        benchmark_name: str | None = None,
                        category: str | None = None,
                        start_time: float | None = None,
                        end_time: float | None = None) -> AggregatedMetric | None:
        """Aggregate a single metric over a time period."""
        metrics = self.storage.query_metrics(
            benchmark_name=benchmark_name,
            metric_name=metric_name,
            category=category,
            start_time=start_time,
            end_time=end_time,
        )

        # Filter to numeric values only
        numeric_values = []
        for metric in metrics:
            if isinstance(metric.value, (int, float)):
                numeric_values.append(float(metric.value))

        if not numeric_values:
            return None

        # Calculate statistics
        aggregated = AggregatedMetric(
            metric_name=metric_name,
            period_start=start_time or min(m.timestamp for m in metrics),
            period_end=end_time or max(m.timestamp for m in metrics),
            sample_count=len(numeric_values),
            min_value=min(numeric_values),
            max_value=max(numeric_values),
            mean_value=statistics.mean(numeric_values),
            median_value=statistics.median(numeric_values),
        )

        # Calculate standard deviation if we have enough samples
        if len(numeric_values) > 1:
            aggregated.std_dev = statistics.stdev(numeric_values)

        # Calculate percentiles
        if len(numeric_values) >= 5:
            sorted_values = sorted(numeric_values)
            percentiles = [50, 75, 90, 95, 99]

            for p in percentiles:
                if p <= 100:
                    index = int((p / 100.0) * (len(sorted_values) - 1))
                    aggregated.percentiles[p] = sorted_values[index]

        return aggregated

    def aggregate_benchmark_metrics(self,
                                   benchmark_name: str,
                                   start_time: float | None = None,
                                   end_time: float | None = None) -> dict[str, AggregatedMetric]:
        """Aggregate all metrics for a specific benchmark."""
        # Get all unique metric names for this benchmark
        all_metrics = self.storage.query_metrics(
            benchmark_name=benchmark_name,
            start_time=start_time,
            end_time=end_time,
        )

        unique_metrics = set(m.metric_name for m in all_metrics)
        aggregated = {}

        for metric_name in unique_metrics:
            agg = self.aggregate_metric(
                metric_name=metric_name,
                benchmark_name=benchmark_name,
                start_time=start_time,
                end_time=end_time,
            )
            if agg:
                aggregated[metric_name] = agg

        return aggregated


class MetricsCollector:
    """
    Central metrics collection system for performance benchmarks.

    Provides data aggregation, time-series storage, and querying capabilities
    for comprehensive performance analysis and trend tracking.
    """

    def __init__(self, config: PerformanceConfig | None = None):
        """
        Initialize metrics collector.

        Args:
            config: Optional performance configuration
        """
        self.config = config or get_config()

        # Initialize storage
        storage_path = Path(self.config.results_storage) / "metrics.db"
        self.storage = TimeSeriesStorage(str(storage_path))
        self.aggregator = MetricsAggregator(self.storage)

        logger.info(f"Metrics collector initialized with storage: {storage_path}")

    def collect_from_result(self, result: BenchmarkResult) -> None:
        """
        Collect metrics from a benchmark result.

        Args:
            result: BenchmarkResult to extract metrics from
        """
        if not result.success:
            logger.warning(f"Skipping metrics collection for failed benchmark: {result.name}")
            return

        timestamp = result.timestamp
        metrics = []

        # Core performance metrics
        metrics.extend([
            MetricPoint(timestamp, result.name, result.category, "mean_time_ms", result.mean_time_ms),
            MetricPoint(timestamp, result.name, result.category, "median_time_ms", result.median_time_ms),
            MetricPoint(timestamp, result.name, result.category, "min_time_ms", result.min_time_ms),
            MetricPoint(timestamp, result.name, result.category, "max_time_ms", result.max_time_ms),
            MetricPoint(timestamp, result.name, result.category, "std_dev_ms", result.std_dev_ms),
            MetricPoint(timestamp, result.name, result.category, "memory_usage_mb", result.memory_usage_mb),
            MetricPoint(timestamp, result.name, result.category, "peak_memory_mb", result.peak_memory_mb),
        ])

        if result.ops_per_sec:
            metrics.append(MetricPoint(timestamp, result.name, result.category, "ops_per_sec", result.ops_per_sec))

        # Implementation and sample size info
        metrics.extend([
            MetricPoint(timestamp, result.name, result.category, "implementation", result.implementation),
            MetricPoint(timestamp, result.name, result.category, "sample_count", len(result.execution_times_ms)),
        ])

        # Extract custom metrics from metadata
        for key, value in result.metadata.items():
            if isinstance(value, (int, float, str)):
                metric_name = f"custom_{key}"
                metrics.append(MetricPoint(timestamp, result.name, result.category, metric_name, value))

        # Store all metrics
        self.storage.store_metrics(metrics)
        logger.debug(f"Collected {len(metrics)} metrics for benchmark: {result.name}")

    def collect_custom_metric(self,
                             benchmark_name: str,
                             category: str,
                             metric_name: str,
                             value: float | int | str,
                             metadata: dict[str, Any] | None = None) -> None:
        """
        Collect a custom metric.

        Args:
            benchmark_name: Name of the benchmark
            category: Benchmark category
            metric_name: Name of the metric
            value: Metric value
            metadata: Optional metadata
        """
        metric = MetricPoint(
            timestamp=time.time(),
            benchmark_name=benchmark_name,
            category=category,
            metric_name=metric_name,
            value=value,
            metadata=metadata or {},
        )

        self.storage.store_metric(metric)
        logger.debug(f"Collected custom metric: {benchmark_name}.{metric_name} = {value}")

    def get_benchmark_summary(self,
                             benchmark_name: str,
                             days: int = 30) -> dict[str, Any]:
        """
        Get comprehensive summary for a benchmark over specified days.

        Args:
            benchmark_name: Name of the benchmark
            days: Number of days to analyze

        Returns:
            Dictionary with benchmark summary statistics
        """
        start_time = time.time() - (days * 24 * 60 * 60)

        # Get aggregated metrics
        aggregated_metrics = self.aggregator.aggregate_benchmark_metrics(
            benchmark_name=benchmark_name,
            start_time=start_time,
        )

        if not aggregated_metrics:
            return {"error": f"No metrics found for benchmark '{benchmark_name}' in last {days} days"}

        # Get recent metrics for trend analysis
        recent_metrics = self.storage.query_metrics(
            benchmark_name=benchmark_name,
            start_time=start_time,
            limit=100,
        )

        summary = {
            "benchmark_name": benchmark_name,
            "analysis_period_days": days,
            "data_points": len(recent_metrics),
            "metrics": {},
            "trends": {},
            "categories": set(m.category for m in recent_metrics),
        }

        # Convert aggregated metrics to dict format
        for metric_name, agg in aggregated_metrics.items():
            summary["metrics"][metric_name] = {
                "sample_count": agg.sample_count,
                "min": agg.min_value,
                "max": agg.max_value,
                "mean": agg.mean_value,
                "median": agg.median_value,
                "std_dev": agg.std_dev,
                "percentiles": agg.percentiles,
            }

        # Simple trend analysis for key metrics
        performance_metrics = ["mean_time_ms", "ops_per_sec"]
        for metric_name in performance_metrics:
            if metric_name in aggregated_metrics:
                trend = self._calculate_trend(benchmark_name, metric_name, start_time)
                if trend:
                    summary["trends"][metric_name] = trend

        return summary

    def _calculate_trend(self,
                        benchmark_name: str,
                        metric_name: str,
                        start_time: float) -> dict[str, Any] | None:
        """Calculate trend for a specific metric."""
        metrics = self.storage.query_metrics(
            benchmark_name=benchmark_name,
            metric_name=metric_name,
            start_time=start_time,
        )

        # Filter to numeric values and sort by timestamp
        numeric_data = []
        for m in metrics:
            if isinstance(m.value, (int, float)):
                numeric_data.append((m.timestamp, float(m.value)))

        if len(numeric_data) < 3:
            return None

        numeric_data.sort(key=lambda x: x[0])  # Sort by timestamp

        # Simple linear trend calculation
        timestamps = [d[0] for d in numeric_data]
        values = [d[1] for d in numeric_data]

        # Calculate correlation coefficient between time and values
        n = len(values)
        if n < 3:
            return None

        # Normalize timestamps to relative positions
        time_positions = list(range(n))

        try:
            correlation = statistics.correlation(time_positions, values)
            recent_avg = statistics.mean(values[-min(5, n):])  # Last 5 or all values
            overall_avg = statistics.mean(values)

            trend_direction = "improving" if correlation < 0 else "degrading" if correlation > 0 else "stable"
            if metric_name == "ops_per_sec":
                trend_direction = "improving" if correlation > 0 else "degrading" if correlation < 0 else "stable"

            return {
                "direction": trend_direction,
                "correlation": correlation,
                "recent_average": recent_avg,
                "overall_average": overall_avg,
                "change_percent": ((recent_avg - overall_avg) / overall_avg) * 100 if overall_avg > 0 else 0,
            }

        except (statistics.StatisticsError, ZeroDivisionError):
            return None

    def get_category_summary(self, category: str, days: int = 30) -> dict[str, Any]:
        """
        Get summary for all benchmarks in a category.

        Args:
            category: Benchmark category
            days: Number of days to analyze

        Returns:
            Category summary with benchmark comparisons
        """
        start_time = time.time() - (days * 24 * 60 * 60)

        # Get all benchmarks in this category
        all_metrics = self.storage.query_metrics(
            category=category,
            start_time=start_time,
        )

        if not all_metrics:
            return {"error": f"No metrics found for category '{category}' in last {days} days"}

        # Group by benchmark name
        benchmarks = {}
        for metric in all_metrics:
            if metric.benchmark_name not in benchmarks:
                benchmarks[metric.benchmark_name] = []
            benchmarks[metric.benchmark_name].append(metric)

        summary = {
            "category": category,
            "analysis_period_days": days,
            "benchmark_count": len(benchmarks),
            "benchmarks": {},
        }

        # Analyze each benchmark
        for benchmark_name in benchmarks.keys():
            benchmark_agg = self.aggregator.aggregate_benchmark_metrics(
                benchmark_name=benchmark_name,
                start_time=start_time,
            )

            if "mean_time_ms" in benchmark_agg:
                summary["benchmarks"][benchmark_name] = {
                    "mean_time_ms": benchmark_agg["mean_time_ms"].mean_value,
                    "sample_count": benchmark_agg["mean_time_ms"].sample_count,
                    "ops_per_sec": benchmark_agg.get("ops_per_sec", {}).mean_value if "ops_per_sec" in benchmark_agg else None,
                }

        # Add category-level statistics
        if summary["benchmarks"]:
            all_times = [b["mean_time_ms"] for b in summary["benchmarks"].values()]
            summary["category_stats"] = {
                "fastest_benchmark": min(summary["benchmarks"].items(), key=lambda x: x[1]["mean_time_ms"])[0],
                "slowest_benchmark": max(summary["benchmarks"].items(), key=lambda x: x[1]["mean_time_ms"])[0],
                "average_time_ms": statistics.mean(all_times),
                "median_time_ms": statistics.median(all_times),
            }

        return summary

    def cleanup_old_data(self, days_to_keep: int = 90) -> int:
        """
        Clean up old metric data.

        Args:
            days_to_keep: Number of days to retain

        Returns:
            Number of records deleted
        """
        return self.storage.cleanup_old_data(days_to_keep)


# Convenience functions for quick metric collection

def collect_benchmark_metrics(result: BenchmarkResult, config: PerformanceConfig | None = None) -> None:
    """
    Quick function to collect metrics from a benchmark result.

    Args:
        result: BenchmarkResult to collect metrics from
        config: Optional performance configuration
    """
    collector = MetricsCollector(config)
    collector.collect_from_result(result)


def get_benchmark_trends(benchmark_name: str,
                        days: int = 30,
                        config: PerformanceConfig | None = None) -> dict[str, Any]:
    """
    Quick function to get benchmark trends.

    Args:
        benchmark_name: Name of the benchmark
        days: Number of days to analyze
        config: Optional performance configuration

    Returns:
        Benchmark trend analysis
    """
    collector = MetricsCollector(config)
    return collector.get_benchmark_summary(benchmark_name, days)


# Export all classes and functions
__all__ = [
    'MetricPoint',
    'AggregatedMetric',
    'TimeSeriesStorage',
    'MetricsAggregator',
    'MetricsCollector',
    'collect_benchmark_metrics',
    'get_benchmark_trends',
]