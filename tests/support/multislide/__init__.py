#!/usr/bin/env python3
"""
Support utilities for multislide testing.

This package provides:
- SVG test utilities and builders
- Mock conversion services
- Test assertion helpers
- File management utilities
- Performance profiling tools
"""

# SVG test utilities
from .svg_helpers import (
    SVGTestBuilder,
    SVGValidator,
    SVGTestLoader,
    SVGComparisonHelper
)

# Mock services
from .mock_services import (
    MockConversionServices,
    MockUnitConverter,
    MockViewportHandler,
    MockFontService,
    MockGradientService,
    MockPatternService,
    MockClipService,
    MockFilterService,
    MockAnimationService,
    MockSlideDetector,
    MockMultiSlideDocument,
    create_mock_services,
    create_mock_slide_detector
)

# Test utilities
from .test_utilities import (
    TestSlideExpectation,
    TestCaseExpectation,
    TestFileManager,
    AssertionHelper,
    TestDataGenerator,
    PerformanceProfiler,
    parametrize_test_samples,
    skip_if_no_expected_output,
    load_expected_output
)

__version__ = "1.0.0"

__all__ = [
    # SVG helpers
    'SVGTestBuilder',
    'SVGValidator',
    'SVGTestLoader',
    'SVGComparisonHelper',

    # Mock services
    'MockConversionServices',
    'MockUnitConverter',
    'MockViewportHandler',
    'MockFontService',
    'MockGradientService',
    'MockPatternService',
    'MockClipService',
    'MockFilterService',
    'MockAnimationService',
    'MockSlideDetector',
    'MockMultiSlideDocument',
    'create_mock_services',
    'create_mock_slide_detector',

    # Test utilities
    'TestSlideExpectation',
    'TestCaseExpectation',
    'TestFileManager',
    'AssertionHelper',
    'TestDataGenerator',
    'PerformanceProfiler',
    'parametrize_test_samples',
    'skip_if_no_expected_output',
    'load_expected_output'
]