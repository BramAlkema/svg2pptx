#!/usr/bin/env python3
"""
Comprehensive test suite for color space conversions in colors.py.

Tests RGB↔XYZ↔LAB↔LCH conversions with mathematical accuracy verification
using known color science reference values.
"""

import pytest
import math
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.colors import ColorParser, ColorInfo, ColorFormat


class TestColorSpaceConversions:
    """
    Test suite for advanced color space conversions.

    Tests the native implementation of RGB↔XYZ↔LAB↔LCH conversions
    against known reference values from colorimetry standards.
    """

    @pytest.fixture
    def parser(self):
        """ColorParser instance for testing."""
        return ColorParser()

    @pytest.fixture
    def reference_colors(self):
        """
        Reference colors with known values across multiple color spaces.

        Values calculated using standard colorimetry formulas with D65 white point.
        Sources: CIE standards, Bruce Lindbloom color calculator.
        """
        return {
            # Pure colors
            'red': {
                'rgb': (255, 0, 0),
                'xyz': (0.4124564, 0.2126729, 0.0193339),  # D65 normalized
                'lab': (53.23, 80.11, 67.22),
                'lch': (53.23, 104.55, 39.99)
            },
            'green': {
                'rgb': (0, 255, 0),
                'xyz': (0.3575761, 0.7151522, 0.1191920),
                'lab': (87.73, -86.18, 83.18),
                'lch': (87.73, 119.78, 136.02)
            },
            'blue': {
                'rgb': (0, 0, 255),
                'xyz': (0.1804375, 0.0721750, 0.9503041),
                'lab': (32.30, 79.19, -107.86),
                'lch': (32.30, 133.81, 306.29)
            },
            # Neutral colors
            'white': {
                'rgb': (255, 255, 255),
                'xyz': (0.95047, 1.00000, 1.08883),  # D65 white point
                'lab': (100.00, 0.00, 0.00),
                'lch': (100.00, 0.00, 0.00)
            },
            'gray': {
                'rgb': (128, 128, 128),
                'xyz': (0.20515, 0.21587, 0.23507),
                'lab': (53.59, 0.00, 0.00),
                'lch': (53.59, 0.00, 0.00)
            },
            'black': {
                'rgb': (0, 0, 0),
                'xyz': (0.00000, 0.00000, 0.00000),
                'lab': (0.00, 0.00, 0.00),
                'lch': (0.00, 0.00, 0.00)
            },
            # Complex colors for interpolation testing
            'orange': {
                'rgb': (255, 165, 0),
                'xyz': (0.5436, 0.4881, 0.0663),
                'lab': (74.93, 23.93, 78.95),
                'lch': (74.93, 82.49, 73.10)
            }
        }

    def assert_color_close(self, actual, expected, tolerance=1.0, description=""):
        """
        Assert color values are within tolerance.

        Args:
            actual: Actual color tuple (r, g, b) or (l, a, b) or (l, c, h)
            expected: Expected color tuple
            tolerance: Maximum allowed difference per component
            description: Test description for error messages
        """
        assert len(actual) == len(expected), f"{description}: Length mismatch"

        for i, (a, e) in enumerate(zip(actual, expected)):
            diff = abs(a - e)
            assert diff <= tolerance, \
                f"{description}: Component {i} differs by {diff:.3f} (tolerance {tolerance}). " \
                f"Expected {e:.3f}, got {a:.3f}"

    @pytest.mark.parametrize("color_name", ['red', 'green', 'blue', 'white', 'gray', 'black', 'orange'])
    def test_rgb_to_xyz_conversion(self, parser, reference_colors, color_name):
        """Test RGB to XYZ conversion accuracy."""
        ref = reference_colors[color_name]
        color_info = ColorInfo(*ref['rgb'], 1.0, ColorFormat.RGB, f"#{ref['rgb'][0]:02x}{ref['rgb'][1]:02x}{ref['rgb'][2]:02x}")

        xyz = color_info.to_xyz()
        self.assert_color_close(xyz, ref['xyz'], tolerance=0.01,
                               description=f"RGB to XYZ conversion for {color_name}")

    @pytest.mark.parametrize("color_name", ['red', 'green', 'blue', 'white', 'gray', 'black', 'orange'])
    def test_xyz_to_lab_conversion(self, parser, reference_colors, color_name):
        """Test XYZ to LAB conversion accuracy."""
        ref = reference_colors[color_name]
        color_info = ColorInfo(*ref['rgb'], 1.0, ColorFormat.RGB, f"#{ref['rgb'][0]:02x}{ref['rgb'][1]:02x}{ref['rgb'][2]:02x}")

        lab = color_info.to_lab()
        self.assert_color_close(lab, ref['lab'], tolerance=1.0,
                               description=f"XYZ to LAB conversion for {color_name}")

    @pytest.mark.parametrize("color_name", ['red', 'green', 'blue', 'white', 'gray', 'black', 'orange'])
    def test_lab_to_lch_conversion(self, parser, reference_colors, color_name):
        """Test LAB to LCH conversion accuracy."""
        ref = reference_colors[color_name]
        color_info = ColorInfo(*ref['rgb'], 1.0, ColorFormat.RGB, f"#{ref['rgb'][0]:02x}{ref['rgb'][1]:02x}{ref['rgb'][2]:02x}")

        lch = color_info.to_lch()

        # Handle special cases for neutral colors (undefined hue)
        if color_name in ['white', 'gray', 'black']:
            # For neutral colors, lightness and chroma should match, hue is undefined
            assert abs(lch[0] - ref['lch'][0]) <= 1.0, f"Lightness mismatch for {color_name}"
            assert abs(lch[1] - ref['lch'][1]) <= 1.0, f"Chroma mismatch for {color_name}"
            # Hue is undefined for neutral colors, so we don't test it
        else:
            self.assert_color_close(lch, ref['lch'], tolerance=2.0,
                                   description=f"LAB to LCH conversion for {color_name}")

    @pytest.mark.parametrize("color_name", ['red', 'green', 'blue', 'white', 'gray', 'black', 'orange'])
    def test_round_trip_rgb_xyz_rgb(self, parser, reference_colors, color_name):
        """Test RGB → XYZ → RGB round-trip conversion accuracy."""
        ref = reference_colors[color_name]
        original_rgb = ref['rgb']

        color_info = ColorInfo(*original_rgb, 1.0, ColorFormat.RGB, f"#{original_rgb[0]:02x}{original_rgb[1]:02x}{original_rgb[2]:02x}")

        # Convert to XYZ and back
        xyz = color_info.to_xyz()
        rgb_back = ColorInfo.from_xyz(*xyz, 1.0).rgb_tuple

        self.assert_color_close(rgb_back, original_rgb, tolerance=2.0,
                               description=f"RGB→XYZ→RGB round-trip for {color_name}")

    @pytest.mark.parametrize("color_name", ['red', 'green', 'blue', 'white', 'gray', 'black', 'orange'])
    def test_round_trip_rgb_lab_rgb(self, parser, reference_colors, color_name):
        """Test RGB → LAB → RGB round-trip conversion accuracy."""
        ref = reference_colors[color_name]
        original_rgb = ref['rgb']

        color_info = ColorInfo(*original_rgb, 1.0, ColorFormat.RGB, f"#{original_rgb[0]:02x}{original_rgb[1]:02x}{original_rgb[2]:02x}")

        # Convert to LAB and back
        lab = color_info.to_lab()
        rgb_back = ColorInfo.from_lab(*lab, 1.0).rgb_tuple

        self.assert_color_close(rgb_back, original_rgb, tolerance=3.0,
                               description=f"RGB→LAB→RGB round-trip for {color_name}")

    @pytest.mark.parametrize("color_name", ['red', 'green', 'blue', 'white', 'gray', 'black', 'orange'])
    def test_round_trip_rgb_lch_rgb(self, parser, reference_colors, color_name):
        """Test RGB → LCH → RGB round-trip conversion accuracy."""
        ref = reference_colors[color_name]
        original_rgb = ref['rgb']

        color_info = ColorInfo(*original_rgb, 1.0, ColorFormat.RGB, f"#{original_rgb[0]:02x}{original_rgb[1]:02x}{original_rgb[2]:02x}")

        # Convert to LCH and back
        lch = color_info.to_lch()
        rgb_back = ColorInfo.from_lch(*lch, 1.0).rgb_tuple

        self.assert_color_close(rgb_back, original_rgb, tolerance=3.0,
                               description=f"RGB→LCH→RGB round-trip for {color_name}")

    def test_edge_cases(self, parser):
        """Test edge cases and error conditions."""
        # Test very small values near zero
        color_info = ColorInfo(1, 1, 1, 1.0, ColorFormat.RGB, "#010101")
        xyz = color_info.to_xyz()
        assert all(x >= 0 for x in xyz), "XYZ values should be non-negative"

        # Test values at RGB boundaries
        color_info = ColorInfo(254, 254, 254, 1.0, ColorFormat.RGB, "#FEFEFE")
        lab = color_info.to_lab()
        assert 0 <= lab[0] <= 100, "L* should be in range [0, 100]"

        # Test alpha preservation through conversions
        color_info = ColorInfo(128, 64, 192, 0.5, ColorFormat.RGB, "rgba(128,64,192,0.5)")
        lch = color_info.to_lch()
        assert hasattr(color_info, 'alpha'), "Alpha should be preserved"
        assert color_info.alpha == 0.5, "Alpha value should remain unchanged"

    def test_xyz_white_point_normalization(self, parser):
        """Test that XYZ conversion uses proper D65 white point normalization."""
        # D65 white point should convert to XYZ (0.95047, 1.00000, 1.08883)
        white = ColorInfo(255, 255, 255, 1.0, ColorFormat.RGB, "#FFFFFF")
        xyz = white.to_xyz()

        expected_d65 = (0.95047, 1.00000, 1.08883)
        self.assert_color_close(xyz, expected_d65, tolerance=0.01,
                               description="D65 white point XYZ conversion")

    def test_lab_range_validation(self, parser):
        """Test that LAB values are within expected ranges."""
        test_colors = [
            ColorInfo(255, 0, 0, 1.0, ColorFormat.RGB, "red"),    # Red
            ColorInfo(0, 255, 0, 1.0, ColorFormat.RGB, "green"),  # Green
            ColorInfo(0, 0, 255, 1.0, ColorFormat.RGB, "blue"),   # Blue
            ColorInfo(128, 128, 128, 1.0, ColorFormat.RGB, "gray") # Gray
        ]

        for color_info in test_colors:
            lab = color_info.to_lab()

            # L* should be in range [0, 100]
            assert 0 <= lab[0] <= 100, f"L* value {lab[0]} out of range [0, 100]"

            # a* and b* typically range from -128 to +127, but can exceed slightly
            assert -150 <= lab[1] <= 150, f"a* value {lab[1]} out of reasonable range"
            assert -150 <= lab[2] <= 150, f"b* value {lab[2]} out of reasonable range"

    def test_lch_hue_angle_normalization(self, parser):
        """Test that LCH hue angles are properly normalized to [0, 360)."""
        test_colors = [
            ColorInfo(255, 0, 0, 1.0, ColorFormat.RGB, "red"),
            ColorInfo(255, 255, 0, 1.0, ColorFormat.RGB, "yellow"),
            ColorInfo(0, 255, 0, 1.0, ColorFormat.RGB, "green"),
            ColorInfo(0, 255, 255, 1.0, ColorFormat.RGB, "cyan"),
            ColorInfo(0, 0, 255, 1.0, ColorFormat.RGB, "blue"),
            ColorInfo(255, 0, 255, 1.0, ColorFormat.RGB, "magenta")
        ]

        for color_info in test_colors:
            lch = color_info.to_lch()

            # Lightness [0, 100]
            assert 0 <= lch[0] <= 100, f"L* value {lch[0]} out of range [0, 100]"

            # Chroma should be non-negative
            assert lch[1] >= 0, f"Chroma value {lch[1]} should be non-negative"

            # Hue should be in range [0, 360)
            if lch[1] > 0.1:  # Only test hue for colors with significant chroma
                assert 0 <= lch[2] < 360, f"Hue angle {lch[2]} out of range [0, 360)"

    def test_colorimetric_delta_e(self, parser):
        """Test Delta E calculation between colors in LAB space."""
        # Red and slightly different red
        red1 = ColorInfo(255, 0, 0, 1.0, ColorFormat.RGB, "red1")
        red2 = ColorInfo(250, 5, 5, 1.0, ColorFormat.RGB, "red2")

        lab1 = red1.to_lab()
        lab2 = red2.to_lab()

        # Calculate Delta E (CIE76 formula)
        delta_e = math.sqrt(
            (lab1[0] - lab2[0])**2 +
            (lab1[1] - lab2[1])**2 +
            (lab1[2] - lab2[2])**2
        )

        # Delta E should be small for similar colors
        assert delta_e < 10, f"Delta E {delta_e} too large for similar colors"

        # Different colors should have larger Delta E
        blue = ColorInfo(0, 0, 255, 1.0, ColorFormat.RGB, "blue")
        lab_blue = blue.to_lab()

        delta_e_different = math.sqrt(
            (lab1[0] - lab_blue[0])**2 +
            (lab1[1] - lab_blue[1])**2 +
            (lab1[2] - lab_blue[2])**2
        )

        assert delta_e_different > 50, f"Delta E {delta_e_different} too small for different colors"


if __name__ == "__main__":
    # Run with: python -m pytest tests/unit/utils/test_color_space_conversions.py -v
    pytest.main([__file__, "-v"])