#!/usr/bin/env python3
"""
Root conftest.py for SVG2PPTX testing.

This file imports shared fixtures from the centralized fixture library
and provides additional pytest configuration.
"""

import sys
import os
from pathlib import Path
from lxml import etree as ET

import pytest

# Ensure repo root and src are importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
SRC = os.path.join(ROOT, "src")
if os.path.isdir(SRC) and SRC not in sys.path:
    sys.path.insert(0, SRC)

# Import all fixtures from centralized library
from tests.fixtures import *

# Import dependency checking utilities
from tests.utils.dependency_checks import get_dependency_status, print_dependency_report


# Pytest hooks for customizing test behavior
def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "requires_network: mark test as requiring network access")
    config.addinivalue_line("markers", "template_generated: mark test as template generated")
    config.addinivalue_line("markers", "converter_unit: mark test as converter unit test")
    config.addinivalue_line("markers", "converter_integration: mark test as converter integration test")
    config.addinivalue_line("markers", "automated_pattern: mark test as using automated pattern")

    # Set up logging
    import logging
    logging.basicConfig(level=logging.DEBUG if config.getoption("--verbose") else logging.WARNING)

    # Print dependency report if in verbose mode
    if config.getoption("--verbose"):
        print_dependency_report()


def pytest_collection_modifyitems(config, items):
    """Modify test items during collection."""
    # Skip slow tests unless explicitly requested
    if not config.getoption("--runslow"):
        skip_slow = pytest.mark.skip(reason="need --runslow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


@pytest.fixture
def component_instance():
    """
    Generic component instance fixture for template-generated tests.

    This fixture provides a basic mock component that can be used by
    comprehensive test suites that were generated from templates.
    """
    from unittest.mock import Mock

    mock_component = Mock()
    mock_component.name = "test_component"
    mock_component.version = "1.0.0"
    mock_component.initialized = True

    # Add common methods that tests might expect
    mock_component.process = Mock(return_value="processed")
    mock_component.validate = Mock(return_value=True)
    mock_component.configure = Mock(return_value=True)

    return mock_component


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