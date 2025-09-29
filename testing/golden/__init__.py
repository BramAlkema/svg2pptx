#!/usr/bin/env python3
"""
Golden Test Framework for SVG2PPTX

A/B comparison infrastructure to validate that the clean architecture
produces identical results to the legacy system.

Key Features:
- Byte-level PPTX comparison
- Visual rendering comparison
- Performance regression detection
- Automated baseline management
"""

from .framework import *
from .comparators import *
from .baselines import *

__all__ = [
    # Core framework
    "GoldenTestRunner", "GoldenTestCase", "ComparisonResult",

    # Comparators
    "PPTXComparator", "VisualComparator", "PerformanceComparator",
    "XMLStructureComparator", "MetricsComparator",

    # Baseline management
    "BaselineManager", "BaselineStrategy", "GoldenBaseline",

    # Utilities
    "generate_test_corpus", "create_comparison_report",
]