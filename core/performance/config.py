#!/usr/bin/env python3
"""
Performance Framework Configuration

Centralized configuration for the SVG2PPTX performance framework including
benchmark categories, regression thresholds, and execution parameters.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PerformanceConfig:
    """Performance framework configuration."""

    # Storage and baseline configuration
    baseline_storage: str = "data/performance_baselines/"
    results_storage: str = "data/performance_results/"

    # Benchmark execution parameters
    benchmark_timeout: int = 30  # seconds
    min_sample_size: int = 10
    warmup_iterations: int = 3
    measurement_iterations: int = 10

    # Statistical analysis parameters
    confidence_level: float = 0.95
    outlier_detection: bool = True
    outlier_threshold: float = 2.0  # standard deviations

    # Regression detection thresholds
    regression_thresholds: dict[str, float] = field(default_factory=lambda: {
        "minor": 0.05,    # 5% slowdown
        "major": 0.15,    # 15% slowdown
        "critical": 0.30,  # 30% slowdown
    })

    # Performance targets (ops per second)
    performance_targets: dict[str, float] = field(default_factory=lambda: {
        "unit_conversion": 791453,     # Target from units core module
        "bezier_evaluation": 100000,   # Target for path processing
        "filter_displacement": 50000,  # Target for filter operations
        "gradient_generation": 75000,  # Target for gradient processing
        "converter_basic": 25000,      # Target for basic conversions
    })

    # Benchmark categories and their associated benchmarks
    benchmark_categories: dict[str, list[str]] = field(default_factory=lambda: {
        "paths": [
            "bezier_evaluation",
            "path_parsing",
            "coordinate_transformation",
            "batch_path_processing",
        ],
        "filters": [
            "displacement_map",
            "color_matrix",
            "gaussian_blur",
            "component_transfer",
            "composite_operations",
        ],
        "converters": [
            "rectangle_conversion",
            "text_conversion",
            "gradient_conversion",
            "complex_shape_conversion",
            "batch_conversion",
        ],
        "units": [
            "emu_conversion",
            "batch_parsing",
            "context_resolution",
            "unit_validation",
        ],
        "gradients": [
            "linear_gradient_generation",
            "radial_gradient_generation",
            "gradient_transformation",
            "color_interpolation",
        ],
    })

    # Memory profiling configuration
    memory_profiling: dict[str, Any] = field(default_factory=lambda: {
        "enabled": True,
        "precision": 3,  # tracemalloc precision
        "threshold": 1024 * 1024,  # 1MB threshold for leak detection
        "max_frames": 10,  # stack trace frames to capture
    })

    # Reporting configuration
    reporting: dict[str, Any] = field(default_factory=lambda: {
        "html_reports": True,
        "json_export": True,
        "csv_export": False,
        "chart_generation": True,
        "trend_analysis": True,
        "comparison_reports": True,
    })


# Global configuration instance
_config: PerformanceConfig | None = None


def get_config() -> PerformanceConfig:
    """Get global performance configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def load_config(config_path: str | None = None) -> PerformanceConfig:
    """
    Load performance configuration from file or environment.

    Args:
        config_path: Optional path to configuration file

    Returns:
        PerformanceConfig instance with loaded settings
    """
    config = PerformanceConfig()

    # Load from environment variables if present
    if os.getenv("PERFORMANCE_BASELINE_STORAGE"):
        config.baseline_storage = os.getenv("PERFORMANCE_BASELINE_STORAGE")

    if os.getenv("PERFORMANCE_TIMEOUT"):
        try:
            config.benchmark_timeout = int(os.getenv("PERFORMANCE_TIMEOUT"))
        except ValueError:
            pass  # Use default

    if os.getenv("PERFORMANCE_MIN_SAMPLES"):
        try:
            config.min_sample_size = int(os.getenv("PERFORMANCE_MIN_SAMPLES"))
        except ValueError:
            pass  # Use default

    # Ensure storage directories exist
    Path(config.baseline_storage).mkdir(parents=True, exist_ok=True)
    Path(config.results_storage).mkdir(parents=True, exist_ok=True)

    return config


def set_config(config: PerformanceConfig) -> None:
    """Set global performance configuration."""
    global _config
    _config = config


def reset_config() -> None:
    """Reset configuration to default values."""
    global _config
    _config = None


# Configuration validation
def validate_config(config: PerformanceConfig) -> list[str]:
    """
    Validate performance configuration.

    Args:
        config: Configuration to validate

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Validate numeric ranges
    if config.benchmark_timeout <= 0:
        errors.append("benchmark_timeout must be positive")

    if config.min_sample_size < 1:
        errors.append("min_sample_size must be at least 1")

    if not (0.0 < config.confidence_level < 1.0):
        errors.append("confidence_level must be between 0 and 1")

    # Validate regression thresholds
    for level, threshold in config.regression_thresholds.items():
        if not (0.0 <= threshold <= 1.0):
            errors.append(f"regression_threshold.{level} must be between 0 and 1")

    # Validate directory paths
    try:
        Path(config.baseline_storage).mkdir(parents=True, exist_ok=True)
        Path(config.results_storage).mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        errors.append(f"Cannot create storage directories: {e}")

    return errors