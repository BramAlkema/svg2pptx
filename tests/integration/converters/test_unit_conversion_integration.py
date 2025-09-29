#!/usr/bin/env python3
"""
Integration Tests for Unit Conversion Integration

Tests the integration of unit conversion with coordinate systems.
"""

import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from src.converters.base import CoordinateSystem
    COORDINATE_AVAILABLE = True
except ImportError:
    COORDINATE_AVAILABLE = False


@pytest.mark.skipif(not COORDINATE_AVAILABLE, reason="Coordinate system not available")
class TestUnitConversionIntegration:
    """Integration tests for unit conversion."""

    def test_coordinate_system_integration(self):
        """Test coordinate system unit conversion integration."""
        coord_system = CoordinateSystem(
            viewbox=(0, 0, 100, 100),
            slide_width=9144000,
            slide_height=6858000
        )

        # Test unit conversion
        emu_x, emu_y = coord_system.svg_to_emu(50, 50)
        assert isinstance(emu_x, int)
        assert isinstance(emu_y, int)
        assert emu_x > 0
        assert emu_y > 0


if __name__ == "__main__":
    pytest.main([__file__])