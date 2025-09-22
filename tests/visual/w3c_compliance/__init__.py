"""
W3C SVG Compliance Testing with LibreOffice

This module provides comprehensive W3C SVG test suite integration for validating
SVG to PPTX conversion compliance using LibreOffice and Playwright automation.

Features:
- W3C SVG test suite download and management
- LibreOffice headless automation with Playwright
- Side-by-side SVG vs PPTX visual comparison
- Comprehensive compliance reporting
- Standards conformance metrics
"""

__version__ = "1.0.0"
__author__ = "SVG2PPTX Team"

from .w3c_test_manager import W3CTestSuiteManager
from .libreoffice_controller import LibreOfficePlaywrightController
from .svg_pptx_comparator import SVGPPTXComparator
from .compliance_runner import W3CComplianceTestRunner

__all__ = [
    "W3CTestSuiteManager",
    "LibreOfficePlaywrightController",
    "SVGPPTXComparator",
    "W3CComplianceTestRunner"
]