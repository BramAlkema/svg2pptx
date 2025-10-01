#!/usr/bin/env python3
"""
CLI module for SVG2PPTX command-line interface functionality.

This module provides command-line interface components including:
- Visual report coordination and generation
- CLI argument processing utilities
- Integration with existing visual comparison infrastructure
"""

from .visual_reports import CLIVisualReportCoordinator, VisualReportConfig, CLIVisualComparisonAdapter
from .version import VersionInfo, get_version_summary, print_version_info

__all__ = [
    'CLIVisualReportCoordinator',
    'VisualReportConfig',
    'CLIVisualComparisonAdapter',
    'VersionInfo',
    'get_version_summary',
    'print_version_info'
]