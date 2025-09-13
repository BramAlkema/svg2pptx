#!/usr/bin/env python3
"""
Root conftest.py for SVG2PPTX testing.

This file imports shared fixtures from the centralized fixture library
and provides additional pytest configuration.
"""

import sys
from pathlib import Path
from lxml import etree as ET

import pytest

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import all fixtures from centralized library
from tests.fixtures import *


# Pytest hooks for customizing test behavior
def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "requires_network: mark test as requiring network access")
    
    # Set up logging
    import logging
    logging.basicConfig(level=logging.DEBUG if config.getoption("--verbose") else logging.WARNING)


def pytest_collection_modifyitems(config, items):
    """Modify test items during collection."""
    # Skip slow tests unless explicitly requested
    if not config.getoption("--runslow"):
        skip_slow = pytest.mark.skip(reason="need --runslow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="run slow tests"
    )


@pytest.fixture(autouse=True)
def cleanup_globals():
    """Clean up global state after each test."""
    yield
    
    # Reset any global caches or singletons
    try:
        from src.performance.cache import _global_cache
        if _global_cache:
            _global_cache.clear_all()
    except ImportError:
        pass


# Custom assertion helpers
class CustomAssertions:
    """Custom assertion helpers for testing."""
    
    @staticmethod
    def assert_valid_drawingml(xml_content: str):
        """Assert that XML content is valid DrawingML."""
        try:
            ET.fromstring(xml_content)
        except ET.ParseError as e:
            pytest.fail(f"Invalid XML/DrawingML: {e}")
    
    @staticmethod
    def assert_svg_elements_equal(element1: ET.Element, element2: ET.Element):
        """Assert that two SVG elements are equivalent."""
        assert element1.tag == element2.tag
        assert element1.attrib == element2.attrib
        assert element1.text == element2.text
        assert len(element1) == len(element2)


@pytest.fixture
def assert_helper():
    """Provide custom assertion helpers."""
    return CustomAssertions()