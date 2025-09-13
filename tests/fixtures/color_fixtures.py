#!/usr/bin/env python3
"""
Color fixtures for SVG2PPTX testing.

Provides standardized color objects and utilities for testing color conversion
and rendering functionality across the test suite.
"""

import pytest
from src.colors import ColorInfo, ColorFormat


@pytest.fixture
def basic_red_color():
    """Basic red color for testing."""
    return ColorInfo(
        red=255,
        green=0,
        blue=0,
        alpha=1.0,
        format=ColorFormat.RGB,
        original="rgb(255,0,0)"
    )


@pytest.fixture
def basic_blue_color():
    """Basic blue color for testing."""
    return ColorInfo(
        red=0,
        green=0,
        blue=255,
        alpha=1.0,
        format=ColorFormat.RGB,
        original="rgb(0,0,255)"
    )


@pytest.fixture
def semi_transparent_gray():
    """Semi-transparent gray color for testing alpha channels."""
    return ColorInfo(
        red=128,
        green=128,
        blue=128,
        alpha=0.8,
        format=ColorFormat.RGBA,
        original="rgba(128,128,128,0.8)"
    )


@pytest.fixture
def hex_color():
    """Hex format color for testing."""
    return ColorInfo(
        red=255,
        green=165,
        blue=0,
        alpha=1.0,
        format=ColorFormat.HEX,
        original="#FFA500"
    )


@pytest.fixture
def named_color():
    """Named color for testing."""
    return ColorInfo(
        red=0,
        green=128,
        blue=0,
        alpha=1.0,
        format=ColorFormat.NAMED,
        original="green"
    )


@pytest.fixture
def color_test_cases():
    """Collection of test color cases for comprehensive testing."""
    return [
        {
            'name': 'red',
            'color': ColorInfo(255, 0, 0, 1.0, ColorFormat.RGB, "rgb(255,0,0)"),
            'expected_hex': 'FF0000'
        },
        {
            'name': 'blue_transparent',
            'color': ColorInfo(0, 0, 255, 0.5, ColorFormat.RGBA, "rgba(0,0,255,0.5)"),
            'expected_hex': '0000FF'
        },
        {
            'name': 'green_hex',
            'color': ColorInfo(0, 255, 0, 1.0, ColorFormat.HEX, "#00FF00"),
            'expected_hex': '00FF00'
        }
    ]


# Drop shadow specific fixtures for filter tests
@pytest.fixture
def drop_shadow_color():
    """Standard drop shadow color for filter testing."""
    return ColorInfo(
        red=128,
        green=128,
        blue=128,
        alpha=0.8,
        format=ColorFormat.RGBA,
        original="rgba(128,128,128,0.8)"
    )


@pytest.fixture
def black_color():
    """Black color fixture."""
    return ColorInfo(
        red=0,
        green=0,
        blue=0,
        alpha=1.0,
        format=ColorFormat.RGB,
        original="rgb(0,0,0)"
    )