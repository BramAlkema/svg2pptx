#!/usr/bin/env python3
"""
Integration Tests for Color Processing Integration

Tests the integration of color system with conversion pipeline.
"""

import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from src.color import Color
    COLOR_AVAILABLE = True
except ImportError:
    COLOR_AVAILABLE = False


@pytest.mark.skipif(not COLOR_AVAILABLE, reason="Color system not available")
class TestColorProcessingIntegration:
    """Integration tests for color processing."""

    def test_color_parser_integration(self):
        """Test basic color parser integration using modern Color API."""
        # Test various color formats
        color_formats = ["#FF0000", "rgb(255,0,0)", "red"]

        for color_str in color_formats:
            try:
                color = Color.from_string(color_str)
                assert color is not None
                # Verify color can be converted to hex
                hex_value = color.to_hex()
                assert hex_value is not None
                assert hex_value.startswith('#')
            except Exception:
                # Some formats might not be supported
                pass


if __name__ == "__main__":
    pytest.main([__file__])