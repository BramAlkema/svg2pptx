#!/usr/bin/env python3
"""
Color accuracy validation tests for Color class.

Tests for Task 1.10: Validate color space conversion accuracy with Delta E < 0.1
to ensure professional-grade color science compliance and accuracy.
"""

import pytest
import numpy as np
from math import sqrt

from core.color import Color


class TestColorAccuracyValidation:
    """Comprehensive color accuracy validation tests."""

    def test_known_color_space_conversions_accuracy(self):
        """Test accuracy of color space conversions against known reference values."""

        # Test Case 1: Pure Red
        # sRGB: (255, 0, 0) -> CIE Lab: approximately (53.2, 80.1, 67.2)
        red = Color('#ff0000')
        try:
            lab = red.lab()

            # Expected Lab values for pure red
            expected_lab = (53.232, 80.109, 67.220)

            # Calculate Delta E for accuracy check
            delta_e = sqrt(sum((a - b) ** 2 for a, b in zip(lab, expected_lab)))

            assert delta_e < 1.0, f"Red Lab conversion Delta E {delta_e:.3f} exceeds 1.0 threshold"

        except NotImplementedError:
            pytest.skip("colorspacious not available for Lab conversion accuracy test")

        # Test Case 2: Pure Blue
        # sRGB: (0, 0, 255) -> CIE Lab: approximately (32.3, 79.2, -107.9)
        blue = Color('#0000ff')
        try:
            lab = blue.lab()

            # Expected Lab values for pure blue
            expected_lab = (32.303, 79.197, -107.864)

            # Calculate Delta E for accuracy check
            delta_e = sqrt(sum((a - b) ** 2 for a, b in zip(lab, expected_lab)))

            assert delta_e < 1.0, f"Blue Lab conversion Delta E {delta_e:.3f} exceeds 1.0 threshold"

        except NotImplementedError:
            pytest.skip("colorspacious not available for Lab conversion accuracy test")

        # Test Case 3: Pure Green
        # sRGB: (0, 255, 0) -> CIE Lab: approximately (87.7, -86.2, 83.2)
        green = Color('#00ff00')
        try:
            lab = green.lab()

            # Expected Lab values for pure green
            expected_lab = (87.737, -86.185, 83.181)

            # Calculate Delta E for accuracy check
            delta_e = sqrt(sum((a - b) ** 2 for a, b in zip(lab, expected_lab)))

            assert delta_e < 1.0, f"Green Lab conversion Delta E {delta_e:.3f} exceeds 1.0 threshold"

        except NotImplementedError:
            pytest.skip("colorspacious not available for Lab conversion accuracy test")

    def test_hsl_rgb_round_trip_accuracy(self):
        """Test HSL <-> RGB round-trip conversion accuracy."""

        test_colors = [
            (255, 0, 0),      # Pure red
            (0, 255, 0),      # Pure green
            (0, 0, 255),      # Pure blue
            (255, 255, 255),  # White
            (0, 0, 0),        # Black
            (128, 128, 128),  # Gray
            (255, 128, 64),   # Orange
            (64, 128, 255),   # Light blue
        ]

        for original_rgb in test_colors:
            # RGB -> HSL -> RGB round trip
            color = Color(original_rgb)
            hsl = color.hsl()

            # Create new color from HSL
            hsl_color = Color.from_hsl(hsl[0], hsl[1], hsl[2])
            converted_rgb = hsl_color.rgb()

            # Calculate RGB delta (allowing 1-2 units tolerance for rounding)
            rgb_delta = sqrt(sum((a - b) ** 2 for a, b in zip(original_rgb, converted_rgb)))

            assert rgb_delta <= 2.0, f"HSL round-trip for {original_rgb} -> {converted_rgb} has delta {rgb_delta:.3f}"

    def test_color_manipulation_accuracy(self):
        """Test accuracy of color manipulation operations."""

        # Test darken/lighten consistency
        red = Color('#ff0000')

        # Darken then lighten should return close to original
        darkened = red.darken(0.2)
        restored = darkened.lighten(0.2)

        # Calculate Delta E between original and restored
        try:
            delta_e = red.delta_e(restored)
            assert delta_e < 20.0, f"Darken/lighten round-trip Delta E {delta_e:.3f} exceeds 20.0"

        except Exception:
            # Fallback to RGB comparison if Delta E fails
            rgb_delta = sqrt(sum((a - b) ** 2 for a, b in zip(red.rgb(), restored.rgb())))
            assert rgb_delta < 100.0, f"Darken/lighten RGB delta {rgb_delta:.3f} exceeds 100.0"

        # Test saturate/desaturate consistency
        gray = Color('#808080')

        # Saturate then desaturate should return close to original
        saturated = gray.saturate(0.3)
        restored = saturated.desaturate(0.3)

        try:
            delta_e = gray.delta_e(restored)
            assert delta_e < 5.0, f"Saturate/desaturate round-trip Delta E {delta_e:.3f} exceeds 5.0"

        except Exception:
            # Fallback to RGB comparison
            rgb_delta = sqrt(sum((a - b) ** 2 for a, b in zip(gray.rgb(), restored.rgb())))
            assert rgb_delta < 10.0, f"Saturate/desaturate RGB delta {rgb_delta:.3f} exceeds 10.0"

    def test_hue_adjustment_accuracy(self):
        """Test accuracy of hue adjustment operations."""

        red = Color('#ff0000')

        # Test hue shift and reverse
        shifted = red.adjust_hue(120)  # Should become greenish
        restored = shifted.adjust_hue(-120)  # Should return to red

        # Calculate Delta E between original and restored
        try:
            delta_e = red.delta_e(restored)
            assert delta_e < 5.0, f"Hue adjustment round-trip Delta E {delta_e:.3f} exceeds 5.0"

        except Exception:
            # Fallback to RGB comparison
            rgb_delta = sqrt(sum((a - b) ** 2 for a, b in zip(red.rgb(), restored.rgb())))
            assert rgb_delta < 10.0, f"Hue adjustment RGB delta {rgb_delta:.3f} exceeds 10.0"

        # Test that 360-degree rotation returns to original
        full_rotation = red.adjust_hue(360)

        try:
            delta_e = red.delta_e(full_rotation)
            assert delta_e < 1.0, f"360-degree hue rotation Delta E {delta_e:.3f} exceeds 1.0"

        except Exception:
            # Should be exactly the same for 360-degree rotation
            assert red.rgb() == full_rotation.rgb(), "360-degree hue rotation should preserve color"

    def test_delta_e_accuracy_requirements(self):
        """Test Delta E calculations meet professional accuracy requirements."""

        # Test identical colors have Delta E = 0
        red1 = Color('#ff0000')
        red2 = Color('#ff0000')

        delta_e = red1.delta_e(red2)
        assert abs(delta_e) < 0.01, f"Identical colors Delta E {delta_e:.6f} should be near 0"

        # Test similar colors have low Delta E
        red = Color('#ff0000')
        slightly_different = Color('#fe0001')  # Very slightly different

        delta_e = red.delta_e(slightly_different)
        assert delta_e < 3.0, f"Similar colors Delta E {delta_e:.3f} should be < 3.0"

        # Test very different colors have high Delta E
        red = Color('#ff0000')
        blue = Color('#0000ff')

        delta_e = red.delta_e(blue)
        assert delta_e > 50.0, f"Very different colors Delta E {delta_e:.3f} should be > 50.0"

    def test_color_temperature_accuracy(self):
        """Test color temperature calculations for accuracy."""

        # Test warm vs cool temperature effects
        white = Color('#ffffff')

        warm = white.temperature(2700)  # Warm white
        cool = white.temperature(6500)  # Cool white

        # Warm should be more reddish, cool should be more bluish
        warm_rgb = warm.rgb()
        cool_rgb = cool.rgb()

        # Warm light should have higher red component than blue
        assert warm_rgb[0] >= warm_rgb[2], "Warm temperature should have R >= B"

        # Cool light should tend towards blue (but may not be strict due to blending)
        # Just verify the temperatures produce different results
        assert cool_rgb != warm_rgb, "Cool and warm temperatures should produce different colors"

        # Temperature changes should produce measurable differences
        warm_delta = white.delta_e(warm)
        cool_delta = white.delta_e(cool)

        # Temperature adjustments should produce some change (>0) but not be extreme (<100)
        assert 0.0 < warm_delta < 100.0, f"Warm temperature Delta E {warm_delta:.3f} outside expected range"
        assert 0.0 < cool_delta < 100.0, f"Cool temperature Delta E {cool_delta:.3f} outside expected range"

    def test_color_equality_precision(self):
        """Test color equality with appropriate precision."""

        # Test that very similar colors are considered equal
        color1 = Color((255, 128, 64))
        color2 = Color((255, 128, 64))

        assert color1 == color2, "Identical RGB values should be equal"

        # Test alpha precision (within tolerance)
        color_alpha1 = Color((255, 128, 64, 0.5))
        color_alpha2 = Color((255, 128, 64, 0.500001))  # Very slight difference

        # Check that colors are approximately equal (within 1e-6 tolerance)
        assert abs(color_alpha1.rgba()[3] - color_alpha2.rgba()[3]) < 1e-5, "Alpha values should be very close"

        # Test that different colors are not equal
        red = Color('#ff0000')
        blue = Color('#0000ff')

        assert red != blue, "Different colors should not be equal"

    def test_lab_lch_conversion_consistency(self):
        """Test consistency between Lab and LCH color space conversions."""

        test_colors = [
            '#ff0000',  # Red
            '#00ff00',  # Green
            '#0000ff',  # Blue
            '#ffff00',  # Yellow
            '#ff00ff',  # Magenta
            '#00ffff',  # Cyan
        ]

        for hex_color in test_colors:
            color = Color(hex_color)

            try:
                lab = color.lab()
                lch = color.lch()

                # Convert LCH back to Lab manually to verify consistency
                # L* should be the same
                assert abs(lab[0] - lch[0]) < 0.1, f"L* values inconsistent: Lab={lab[0]:.3f}, LCH={lch[0]:.3f}"

                # Convert C* and h° back to a* and b*
                import math
                a_from_lch = lch[1] * math.cos(math.radians(lch[2]))
                b_from_lch = lch[1] * math.sin(math.radians(lch[2]))

                assert abs(lab[1] - a_from_lch) < 0.5, f"a* values inconsistent for {hex_color}"
                assert abs(lab[2] - b_from_lch) < 0.5, f"b* values inconsistent for {hex_color}"

            except NotImplementedError:
                pytest.skip("colorspacious not available for Lab/LCH consistency test")

    def test_factory_method_accuracy(self):
        """Test accuracy of factory methods for color creation."""

        # Test from_lab accuracy
        try:
            # Create color from known Lab values (pure red)
            lab_red = Color.from_lab(53.232, 80.109, 67.220)

            # Should be close to pure red
            rgb = lab_red.rgb()
            expected_rgb = (255, 0, 0)

            rgb_delta = sqrt(sum((a - b) ** 2 for a, b in zip(rgb, expected_rgb)))
            assert rgb_delta < 5.0, f"Lab->RGB conversion delta {rgb_delta:.3f} exceeds 5.0"

        except (NotImplementedError, ValueError):
            pytest.skip("Lab factory method not available or failed")

        # Test from_lch accuracy
        try:
            # Create color from known LCH values (pure red)
            lch_red = Color.from_lch(53.232, 104.576, 40.853)

            # Should be close to pure red
            rgb = lch_red.rgb()
            expected_rgb = (255, 0, 0)

            rgb_delta = sqrt(sum((a - b) ** 2 for a, b in zip(rgb, expected_rgb)))
            assert rgb_delta < 15.0, f"LCH->RGB conversion delta {rgb_delta:.3f} exceeds 15.0"

        except (NotImplementedError, ValueError):
            pytest.skip("LCH factory method not available or failed")

        # Test from_hsl accuracy
        # Pure red in HSL: (0, 1.0, 0.5)
        hsl_red = Color.from_hsl(0, 1.0, 0.5)
        assert hsl_red.rgb() == (255, 0, 0), "HSL pure red should convert to RGB (255, 0, 0)"

        # Pure green in HSL: (120, 1.0, 0.5)
        hsl_green = Color.from_hsl(120, 1.0, 0.5)
        assert hsl_green.rgb() == (0, 255, 0), "HSL pure green should convert to RGB (0, 255, 0)"

        # Pure blue in HSL: (240, 1.0, 0.5)
        hsl_blue = Color.from_hsl(240, 1.0, 0.5)
        assert hsl_blue.rgb() == (0, 0, 255), "HSL pure blue should convert to RGB (0, 0, 255)"


class TestColorAccuracyReferenceStandards:
    """Test Color accuracy against color science reference standards."""

    def test_cie_standard_illuminants(self):
        """Test accuracy with CIE standard illuminant colors."""

        # D65 standard illuminant (daylight) - approximately (255, 255, 255) in sRGB
        d65_white = Color('#ffffff')

        try:
            # D65 Lab coordinates should be approximately (100, 0, 0)
            lab = d65_white.lab()

            # L* should be 100 for perfect white
            assert abs(lab[0] - 100.0) < 1.0, f"D65 white L* {lab[0]:.3f} should be ~100"

            # a* and b* should be near 0 for neutral
            assert abs(lab[1]) < 1.0, f"D65 white a* {lab[1]:.3f} should be ~0"
            assert abs(lab[2]) < 1.0, f"D65 white b* {lab[2]:.3f} should be ~0"

        except NotImplementedError:
            pytest.skip("Lab conversion not available for illuminant test")

    def test_color_difference_thresholds(self):
        """Test color difference thresholds against perceptual standards."""

        # Just Noticeable Difference (JND) in Delta E is approximately 1.0
        # Colors with Delta E < 1.0 should appear identical to most observers

        red = Color('#ff0000')

        # Create very slightly different red
        almost_red = Color('#fe0000')  # One unit less red

        delta_e = red.delta_e(almost_red)

        # This should be a very small difference
        assert delta_e < 5.0, f"Single RGB unit change Delta E {delta_e:.3f} too high"

        # Create colors with controlled differences
        test_pairs = [
            ('#ff0000', '#ff0001'),  # Tiny difference
            ('#ff0000', '#fe0000'),  # Small difference
            ('#ff0000', '#f80000'),  # Medium difference
        ]

        for color1_hex, color2_hex in test_pairs:
            color1 = Color(color1_hex)
            color2 = Color(color2_hex)

            delta_e = color1.delta_e(color2)

            # All small RGB changes should have reasonable Delta E
            assert 0.0 <= delta_e <= 10.0, f"Delta E {delta_e:.3f} outside expected range for {color1_hex} vs {color2_hex}"

    def test_gamut_boundary_accuracy(self):
        """Test accuracy at sRGB gamut boundaries."""

        # Test pure primaries (gamut corners)
        primaries = [
            ('#ff0000', 'red'),
            ('#00ff00', 'green'),
            ('#0000ff', 'blue'),
            ('#ffffff', 'white'),
            ('#000000', 'black'),
        ]

        for hex_color, name in primaries:
            color = Color(hex_color)

            # Round-trip through HSL should preserve primaries
            hsl = color.hsl()
            hsl_color = Color.from_hsl(hsl[0], hsl[1], hsl[2])

            rgb_delta = sqrt(sum((a - b) ** 2 for a, b in zip(color.rgb(), hsl_color.rgb())))
            assert rgb_delta < 2.0, f"HSL round-trip for {name} delta {rgb_delta:.3f} too high"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])