#!/usr/bin/env python3
"""
Root conftest.py for SVG2PPTX testing.

This file contains shared fixtures and configuration for all test modules.
Provides common test utilities, mock objects, and test data fixtures.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator
from lxml import etree as ET

import pytest


# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    try:
        yield temp_path
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_svg_content() -> str:
    """Provide sample SVG content for testing."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="30" height="20" fill="red"/>
    <circle cx="70" cy="30" r="15" fill="blue"/>
    <path d="M 20 60 L 80 60 L 50 90 Z" fill="green"/>
    <text x="50" y="80" text-anchor="middle" fill="black">Test</text>
</svg>'''


@pytest.fixture
def sample_svg_file(temp_dir: Path, sample_svg_content: str) -> Path:
    """Create a sample SVG file for testing."""
    svg_file = temp_dir / "test.svg"
    svg_file.write_text(sample_svg_content)
    return svg_file


@pytest.fixture
def complex_svg_content() -> str:
    """Provide complex SVG content with advanced features."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="200" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
            <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
        </linearGradient>
        <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
            <polygon points="0 0, 10 3, 0 6" fill="black"/>
        </marker>
    </defs>
    <g transform="translate(20,20) rotate(45)">
        <rect x="0" y="0" width="50" height="30" fill="url(#grad1)"/>
        <line x1="0" y1="40" x2="80" y2="40" stroke="black" marker-end="url(#arrow)"/>
        <path d="M 10 60 Q 50 30 90 60 T 150 60" stroke="blue" fill="none" stroke-width="2"/>
    </g>
    <text x="100" y="150">
        <tspan x="100" dy="0" fill="red">Multi</tspan>
        <tspan x="100" dy="20" fill="blue">line</tspan>
        <tspan x="100" dy="20" fill="green">text</tspan>
    </text>
</svg>'''


@pytest.fixture
def mock_conversion_context():
    """Mock conversion context for testing converters."""
    from src.context import ConversionContext
    
    context = ConversionContext()
    context.shape_id_counter = 1000
    context.coordinate_system = None
    context.gradients = {}
    context.patterns = {}
    context.clips = {}
    context.fonts = {}
    
    return context


@pytest.fixture
def mock_svg_element() -> ET.Element:
    """Create a mock SVG element for testing."""
    root = ET.fromstring('''
    <rect x="10" y="10" width="50" height="30" 
          fill="red" stroke="blue" stroke-width="2"
          transform="translate(5,5)"/>
    ''')
    return root


@pytest.fixture
def mock_converter_output() -> str:
    """Mock DrawingML output from a converter."""
    return '''<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="1001" name="Rectangle"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:xfrm>
            <a:off x="914400" y="914400"/>
            <a:ext cx="4572000" cy="2743200"/>
        </a:xfrm>
        <a:prstGeom prst="rect"/>
        <a:solidFill>
            <a:srgbClr val="FF0000"/>
        </a:solidFill>
    </p:spPr>
</p:sp>'''


@pytest.fixture
def sample_path_data() -> Dict[str, str]:
    """Sample path data for testing path converters."""
    return {
        "simple_line": "M 10 10 L 90 90",
        "curve": "M 10 80 C 40 10, 65 10, 95 80 S 150 150, 180 80",
        "complex": "M 20 20 L 80 20 A 30 30 0 0 1 80 80 L 20 80 Z",
        "relative": "m 10,10 l 30,0 l 0,20 l -30,0 z"
    }


@pytest.fixture
def benchmark_data_dir(temp_dir: Path) -> Path:
    """Create directory for benchmark test data."""
    bench_dir = temp_dir / "benchmarks"
    bench_dir.mkdir()
    return bench_dir


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables and configuration."""
    # Set test environment variables
    os.environ["TESTING"] = "1"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    # Create test data directories
    test_root = Path(__file__).parent
    test_data_dir = test_root / "data"
    test_data_dir.mkdir(exist_ok=True)
    
    # Create subdirectories for test assets
    (test_data_dir / "svg").mkdir(exist_ok=True)
    (test_data_dir / "expected").mkdir(exist_ok=True)
    (test_data_dir / "baselines").mkdir(exist_ok=True)
    
    yield
    
    # Cleanup after all tests
    if "TESTING" in os.environ:
        del os.environ["TESTING"]


@pytest.fixture
def performance_config():
    """Configuration for performance testing."""
    return {
        "timeout": 30.0,
        "max_memory_mb": 500,
        "benchmark_rounds": 5,
        "warmup_rounds": 2
    }


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