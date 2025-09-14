#!/usr/bin/env python3
"""
Simple Unit Tests for SVG2PPTX Module
"""

import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.svg2pptx import SVGToPowerPointConverter, convert_svg_to_pptx

class TestSVGToPowerPointConverter:
    """Simple test cases for SVGToPowerPointConverter class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.converter = SVGToPowerPointConverter()

    def test_initialization_default(self):
        """Test SVGToPowerPointConverter initialization."""
        converter = SVGToPowerPointConverter()
        assert converter is not None

    def test_initialization_with_dimensions(self):
        """Test initialization with custom dimensions."""
        converter = SVGToPowerPointConverter(slide_width=12, slide_height=9)
        assert converter is not None


class TestConvertFunction:
    """Test cases for convert_svg_to_pptx function."""

    def test_function_exists(self):
        """Test that convert function exists."""
        assert callable(convert_svg_to_pptx)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])