#!/usr/bin/env python3
"""
Unit test fixtures and configuration.

This conftest.py provides fixtures specific to unit testing of individual components.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from lxml import etree as ET


@pytest.fixture
def mock_unit_converter():
    """Mock UniversalUnitConverter for unit tests."""
    mock = Mock()
    mock.convert_to_emu.return_value = 914400  # 1 inch in EMU
    mock.convert_to_pixels.return_value = 96.0
    mock.to_user_units.return_value = 1.0
    return mock


@pytest.fixture
def mock_color_parser():
    """Mock UniversalColorParser for unit tests."""
    mock = Mock()
    mock.parse_color.return_value = (255, 0, 0, 1.0)  # Red, fully opaque
    mock.to_hex.return_value = "#FF0000"
    mock.to_rgb.return_value = "rgb(255,0,0)"
    return mock


@pytest.fixture
def mock_transform_engine():
    """Mock UniversalTransformEngine for unit tests."""
    mock = Mock()
    mock.parse_transform.return_value = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]  # Identity matrix
    mock.apply_transform.return_value = (10.0, 20.0)  # Sample transformed coordinates
    return mock


@pytest.fixture
def mock_viewport_handler():
    """Mock ViewportHandler for unit tests."""
    mock = Mock()
    mock.create_viewport_context.return_value = Mock()
    mock.get_default_context.return_value = Mock()
    return mock


@pytest.fixture
def sample_element_attributes():
    """Sample element attributes for testing."""
    return {
        'x': '10',
        'y': '20', 
        'width': '100',
        'height': '50',
        'fill': 'red',
        'stroke': 'blue',
        'stroke-width': '2',
        'transform': 'translate(5,5)'
    }


@pytest.fixture
def unit_test_svg_elements():
    """Common SVG elements for unit testing."""
    return {
        'rect': ET.fromstring('<rect x="10" y="10" width="50" height="30" fill="red"/>'),
        'circle': ET.fromstring('<circle cx="50" cy="50" r="25" fill="blue"/>'),
        'line': ET.fromstring('<line x1="0" y1="0" x2="100" y2="100" stroke="black"/>'),
        'path': ET.fromstring('<path d="M 10 10 L 90 90" stroke="green" fill="none"/>'),
        'text': ET.fromstring('<text x="50" y="50" fill="black">Hello</text>')
    }


# Note: mock_conversion_context fixture is now imported from tests.fixtures.mock_objects
# If you need unit-test-specific enhancements, override it locally in individual test files