#!/usr/bin/env python3
"""
Color fixtures for SVG2PPTX testing.

Provides standardized color objects and utilities for testing color conversion
and rendering functionality across the test suite.
"""

import pytest
from core.color import Color


@pytest.fixture
def basic_red_color():
    """Basic red color for testing."""
    return Color("#FF0000")


@pytest.fixture
def basic_blue_color():
    """Basic blue color for testing."""
    return Color("#0000FF")


@pytest.fixture
def semi_transparent_gray():
    """Semi-transparent gray color for testing alpha channels."""
    return Color("rgba(128,128,128,0.8)")


@pytest.fixture
def hex_color():
    """Hex format color for testing."""
    return Color("#FFA500")


@pytest.fixture
def named_color():
    """Named color for testing."""
    return Color("green")


@pytest.fixture
def color_test_cases():
    """Collection of test color cases for comprehensive testing."""
    return [
        {
            'name': 'red',
            'color': Color("#FF0000"),
            'expected_hex': 'FF0000'
        },
        {
            'name': 'blue_transparent',
            'color': Color("rgba(0,0,255,0.5)"),
            'expected_hex': '0000FF'
        },
        {
            'name': 'green_hex',
            'color': Color("#00FF00"),
            'expected_hex': '00FF00'
        }
    ]


# Drop shadow specific fixtures for filter tests
@pytest.fixture
def drop_shadow_color():
    """Standard drop shadow color for filter testing."""
    return Color("rgba(128,128,128,0.8)")


@pytest.fixture
def black_color():
    """Black color fixture."""
    return Color("#000000")