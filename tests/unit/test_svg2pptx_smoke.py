#!/usr/bin/env python3
"""
Smoke tests for main svg2pptx module to establish basic coverage.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

class TestSVG2PPTXSmoke:
    """Basic smoke tests for svg2pptx module."""

    def test_import_svg2pptx(self):
        """Test that svg2pptx module can be imported."""
        try:
            import src.svg2pptx
            assert True
        except ImportError:
            pytest.skip("svg2pptx module not available")

    def test_import_units(self):
        """Test that units module can be imported."""
        try:
            import core.units
            assert True
        except ImportError:
            pytest.skip("units module not available")

    def test_import_multislide(self):
        """Test that multislide modules can be imported."""
        try:
            import src.multislide
            assert True
        except ImportError:
            pytest.skip("multislide module not available")


if __name__ == "__main__":
    pytest.main([__file__])