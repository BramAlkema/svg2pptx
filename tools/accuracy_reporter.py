#!/usr/bin/env python3
"""
Advanced accuracy reporting and analytics system.

This module provides comprehensive reporting capabilities for accuracy
measurements, including trend analysis, comparative reports, and
dashboard-style visualizations for conversion quality assessment.

DEPRECATED: This module is replaced by tools.reporting_utilities.AccuracyReporter
"""

import warnings
from pathlib import Path

# Import from new consolidated utilities
from tools.reporting_utilities import (
    AccuracyReporter as NewAccuracyReporter,
    AccuracyMetrics
)

warnings.warn(
    "tools.accuracy_reporter is deprecated. Use tools.reporting_utilities.AccuracyReporter instead.",
    DeprecationWarning,
    stacklevel=2
)

# For backward compatibility, re-export the new classes
AccuracyReporter = NewAccuracyReporter

# Legacy compatibility function
def create_accuracy_reporter(database_path: Path) -> NewAccuracyReporter:
    """Create accuracy reporter - use tools.reporting_utilities.AccuracyReporter directly."""
    warnings.warn(
        "create_accuracy_reporter is deprecated. Use AccuracyReporter(database_path) directly.",
        DeprecationWarning,
        stacklevel=2
    )
    return NewAccuracyReporter(database_path)


if __name__ == "__main__":
    print("This module is deprecated. Use tools.reporting_utilities.AccuracyReporter instead.")