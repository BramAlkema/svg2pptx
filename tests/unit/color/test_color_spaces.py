#!/usr/bin/env python3
"""
Unit tests for ColorSpaceConverter module.

Tests the dedicated color space conversion engine for OKLab and OKLCh.
"""

import pytest
import numpy as np
from src.color.color_spaces import ColorSpaceConverter, rgb_to_oklab, oklab_to_rgb


class TestColorSpaceConverter:
    """Test ColorSpaceConverter class."""

    def test_rgb_to_oklab_conversion(self):
        """Test RGB to OKLab conversion."""
        # Test pure red
        r, g, b = 255, 0, 0
        oklab = ColorSpaceConverter.rgb_to_oklab(r, g, b)

        assert len(oklab) == 3
        l, a, b_val = oklab

        # Basic sanity checks for red in OKLab
        assert 0.0 <= l <= 1.0  # Lightness in valid range
        assert a > 0  # Red should have positive a (red-green axis)
        assert isinstance(l, (float, np.floating))
        assert isinstance(a, (float, np.floating))
        assert isinstance(b_val, (float, np.floating))

    def test_oklab_to_rgb_conversion(self):
        """Test OKLab to RGB conversion."""
        # Test conversion of OKLab red back to RGB
        oklab_red = (0.628, 0.225, 0.126)
        rgb = ColorSpaceConverter.oklab_to_rgb(*oklab_red)

        assert len(rgb) == 3
        r, g, b = rgb

        # Should be close to red
        assert 200 <= r <= 255  # Allow some tolerance
        assert 0 <= g <= 50     # Should be low
        assert 0 <= b <= 50     # Should be low

        # All values should be integers in valid range
        assert all(isinstance(c, int) for c in rgb)
        assert all(0 <= c <= 255 for c in rgb)

    def test_oklab_to_oklch_conversion(self):
        """Test OKLab to OKLCh conversion."""
        oklab = (0.628, 0.225, 0.126)
        oklch = ColorSpaceConverter.oklab_to_oklch(*oklab)

        assert len(oklch) == 3
        l, c, h = oklch

        # Validate OKLCh ranges
        assert 0.0 <= l <= 1.0      # Lightness
        assert c >= 0               # Chroma non-negative
        assert 0.0 <= h <= 360.0    # Hue in degrees

        # For red, hue should be in the red range
        assert 0 <= h <= 90  # Red-orange range

    def test_oklch_to_oklab_conversion(self):
        """Test OKLCh to OKLab conversion."""
        oklch = (0.628, 0.258, 29.2)
        oklab = ColorSpaceConverter.oklch_to_oklab(*oklch)

        assert len(oklab) == 3
        l, a, b = oklab

        # Lightness should be preserved
        assert abs(l - 0.628) < 1e-10

        # a and b should be reasonable for red
        assert a > 0  # Red has positive a
        assert b >= 0  # Red-orange has positive b

    def test_round_trip_rgb_oklab_rgb(self):
        """Test round-trip conversion RGB -> OKLab -> RGB."""
        original_colors = [
            (255, 0, 0),     # Red
            (0, 255, 0),     # Green
            (0, 0, 255),     # Blue
            (255, 255, 255), # White
            (0, 0, 0),       # Black
            (128, 128, 128), # Gray
        ]

        for r, g, b in original_colors:
            # RGB -> OKLab -> RGB
            oklab = ColorSpaceConverter.rgb_to_oklab(r, g, b)
            rgb_back = ColorSpaceConverter.oklab_to_rgb(*oklab)

            # Allow small differences due to floating point precision
            assert all(abs(orig - back) <= 2 for orig, back in zip((r, g, b), rgb_back))

    def test_round_trip_oklab_oklch_oklab(self):
        """Test round-trip conversion OKLab -> OKLCh -> OKLab."""
        test_oklab_values = [
            (0.628, 0.225, 0.126),   # Red-ish
            (0.866, -0.234, 0.179),  # Green-ish
            (0.452, -0.032, -0.312), # Blue-ish
            (1.0, 0.0, 0.0),         # White
            (0.0, 0.0, 0.0),         # Black
        ]

        for l, a, b in test_oklab_values:
            # OKLab -> OKLCh -> OKLab
            oklch = ColorSpaceConverter.oklab_to_oklch(l, a, b)
            oklab_back = ColorSpaceConverter.oklch_to_oklab(*oklch)

            # Check round-trip accuracy
            assert abs(l - oklab_back[0]) < 1e-10
            assert abs(a - oklab_back[1]) < 1e-10
            assert abs(b - oklab_back[2]) < 1e-10

    def test_direct_rgb_oklch_conversions(self):
        """Test direct RGB <-> OKLCh conversion methods."""
        # Test RGB -> OKLCh
        rgb = (255, 128, 64)
        oklch = ColorSpaceConverter.rgb_to_oklch(*rgb)

        assert len(oklch) == 3
        l, c, h = oklch
        assert 0.0 <= l <= 1.0
        assert c >= 0
        assert 0.0 <= h <= 360.0

        # Test OKLCh -> RGB
        rgb_back = ColorSpaceConverter.oklch_to_rgb(*oklch)

        # Should be close to original
        assert all(abs(orig - back) <= 2 for orig, back in zip(rgb, rgb_back))

    def test_edge_case_achromatic_colors(self):
        """Test edge cases with achromatic (gray) colors."""
        # Pure gray should have zero chroma in OKLCh
        gray_rgb = (128, 128, 128)
        oklch = ColorSpaceConverter.rgb_to_oklch(*gray_rgb)

        l, c, h = oklch
        assert 0.0 <= l <= 1.0
        assert c < 0.01  # Chroma should be very small for gray

        # Hue can be anything for achromatic colors, so we don't test it

    def test_extreme_color_values(self):
        """Test extreme color values."""
        # Pure white
        white_oklab = ColorSpaceConverter.rgb_to_oklab(255, 255, 255)
        assert white_oklab[0] > 0.9  # Very high lightness
        assert abs(white_oklab[1]) < 0.1  # Near zero a
        assert abs(white_oklab[2]) < 0.1  # Near zero b

        # Pure black
        black_oklab = ColorSpaceConverter.rgb_to_oklab(0, 0, 0)
        assert black_oklab[0] < 0.1  # Very low lightness
        assert abs(black_oklab[1]) < 0.1  # Near zero a
        assert abs(black_oklab[2]) < 0.1  # Near zero b


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_convenience_function_equivalence(self):
        """Test that convenience functions match class methods."""
        rgb = (255, 100, 50)

        # Test rgb_to_oklab convenience function
        oklab1 = rgb_to_oklab(*rgb)
        oklab2 = ColorSpaceConverter.rgb_to_oklab(*rgb)
        assert oklab1 == oklab2

        # Test oklab_to_rgb convenience function
        rgb1 = oklab_to_rgb(*oklab1)
        rgb2 = ColorSpaceConverter.oklab_to_rgb(*oklab1)
        assert rgb1 == rgb2

    def test_all_convenience_functions_exist(self):
        """Test that all convenience functions are available."""
        from src.color.color_spaces import (
            rgb_to_oklab, oklab_to_rgb,
            rgb_to_oklch, oklch_to_rgb,
            oklab_to_oklch, oklch_to_oklab
        )

        # Test that they're all callable
        assert callable(rgb_to_oklab)
        assert callable(oklab_to_rgb)
        assert callable(rgb_to_oklch)
        assert callable(oklch_to_rgb)
        assert callable(oklab_to_oklch)
        assert callable(oklch_to_oklab)


class TestNumericalStability:
    """Test numerical stability and precision."""

    def test_precision_with_small_values(self):
        """Test precision with very small color values."""
        # Very dark color
        dark_rgb = (1, 1, 1)
        oklab = ColorSpaceConverter.rgb_to_oklab(*dark_rgb)
        rgb_back = ColorSpaceConverter.oklab_to_rgb(*oklab)

        # Should handle small values correctly
        assert all(0 <= c <= 5 for c in rgb_back)  # Allow small tolerance

    def test_precision_with_large_values(self):
        """Test precision with maximum color values."""
        # Maximum RGB values
        bright_rgb = (255, 255, 255)
        oklab = ColorSpaceConverter.rgb_to_oklab(*bright_rgb)
        rgb_back = ColorSpaceConverter.oklab_to_rgb(*oklab)

        # Should handle maximum values correctly
        assert all(250 <= c <= 255 for c in rgb_back)

    def test_floating_point_edge_cases(self):
        """Test floating point edge cases."""
        # Test with OKLab values at boundaries
        boundary_tests = [
            (0.0, 0.0, 0.0),    # Minimum
            (1.0, 0.0, 0.0),    # Maximum lightness
            (0.5, 0.5, 0.5),    # Mid-range
            (0.5, -0.5, 0.5),   # Negative a
            (0.5, 0.5, -0.5),   # Negative b
        ]

        for l, a, b in boundary_tests:
            try:
                rgb = ColorSpaceConverter.oklab_to_rgb(l, a, b)
                # Should produce valid RGB values (may be clamped)
                assert all(0 <= c <= 255 for c in rgb)
                assert all(isinstance(c, int) for c in rgb)
            except Exception as e:
                pytest.fail(f"Failed on boundary case ({l}, {a}, {b}): {e}")