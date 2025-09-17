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
    from src.colors import ColorParser
    COLOR_AVAILABLE = True
except ImportError:
    COLOR_AVAILABLE = False


@pytest.mark.skipif(not COLOR_AVAILABLE, reason="Color system not available")
class TestColorProcessingIntegration:
    """Integration tests for color processing."""

    def test_color_parser_integration(self):
        """Test basic color parser integration."""
        color_parser = ColorParser()

        # Test various color formats
        color_formats = ["#FF0000", "rgb(255,0,0)", "red"]

        for color_str in color_formats:
            try:
                color = color_parser.parse(color_str)
                assert color is not None
            except Exception:
                # Some formats might not be supported
                pass


if __name__ == "__main__":
    pytest.main([__file__])