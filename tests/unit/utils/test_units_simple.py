#!/usr/bin/env python3
"""
Simple Unit Tests for Units Module
"""

import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.units import UnitConverter, to_emu, to_pixels

class TestUnitConverter:
    """Simple test cases for UnitConverter class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.converter = UnitConverter()

    def test_initialization(self):
        """Test UnitConverter initialization."""
        converter = UnitConverter()
        assert converter is not None

    def test_to_emu_pixels(self):
        """Test pixel to EMU conversion."""
        result = self.converter.to_emu(100, 'px')
        assert result > 0
        assert isinstance(result, (int, float))

    def test_to_emu_points(self):
        """Test point to EMU conversion."""
        result = self.converter.to_emu(72, 'pt')
        assert result > 0
        assert isinstance(result, (int, float))

    def test_to_emu_inches(self):
        """Test inch to EMU conversion."""
        result = self.converter.to_emu(1, 'in')
        assert result > 0
        assert isinstance(result, (int, float))


class TestUtilityFunctions:
    """Test utility functions."""

    def test_to_emu_function(self):
        """Test to_emu utility function."""
        result = to_emu(100)
        assert isinstance(result, (int, float))

    def test_to_pixels_function(self):
        """Test to_pixels utility function."""
        result = to_pixels(914400)  # 1 inch in EMUs
        assert isinstance(result, (int, float))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])