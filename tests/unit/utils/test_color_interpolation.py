#!/usr/bin/env python3
"""
Comprehensive test suite for advanced color interpolation functionality.

Tests perceptual color interpolation in LAB space, LCH hue handling,
bezier curves, color harmony generation, and accessibility features.
"""

import pytest
import math
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.colors import ColorParser, ColorInfo, ColorFormat


class TestColorInterpolation:
    """
    Test suite for advanced color interpolation functionality.

    Tests perceptual color blending, harmony generation, and accessibility features.
    """

    @pytest.fixture
    def parser(self):
        """ColorParser instance for testing."""
        return ColorParser()

    @pytest.fixture
    def test_colors(self):
        """Common colors for interpolation testing."""
        return {
            'red': ColorInfo(255, 0, 0, 1.0, ColorFormat.RGB, "red"),
            'green': ColorInfo(0, 255, 0, 1.0, ColorFormat.RGB, "green"),
            'blue': ColorInfo(0, 0, 255, 1.0, ColorFormat.RGB, "blue"),
            'white': ColorInfo(255, 255, 255, 1.0, ColorFormat.RGB, "white"),
            'black': ColorInfo(0, 0, 0, 1.0, ColorFormat.RGB, "black"),
            'gray': ColorInfo(128, 128, 128, 1.0, ColorFormat.RGB, "gray"),
            'yellow': ColorInfo(255, 255, 0, 1.0, ColorFormat.RGB, "yellow"),
            'cyan': ColorInfo(0, 255, 255, 1.0, ColorFormat.RGB, "cyan"),
            'magenta': ColorInfo(255, 0, 255, 1.0, ColorFormat.RGB, "magenta")
        }

    def assert_color_in_range(self, color_info, min_rgb=(0, 0, 0), max_rgb=(255, 255, 255)):
        """Assert color RGB values are within valid range."""
        r, g, b = color_info.rgb_tuple
        min_r, min_g, min_b = min_rgb
        max_r, max_g, max_b = max_rgb

        assert min_r <= r <= max_r, f"Red {r} out of range [{min_r}, {max_r}]"
        assert min_g <= g <= max_g, f"Green {g} out of range [{min_g}, {max_g}]"
        assert min_b <= b <= max_b, f"Blue {b} out of range [{min_b}, {max_b}]"

    # LAB-based Linear Interpolation Tests

    @pytest.mark.parametrize("ratio", [0.0, 0.25, 0.5, 0.75, 1.0])
    def test_lab_interpolation_red_to_green(self, parser, test_colors, ratio):
        """Test LAB-based interpolation between red and green."""
        red = test_colors['red']
        green = test_colors['green']

        result = parser.interpolate_lab(red, green, ratio)

        # Validate result is a ColorInfo
        assert isinstance(result, ColorInfo)

        # Validate color is within valid RGB range
        self.assert_color_in_range(result)

        # Check edge cases
        if ratio == 0.0:
            assert result.rgb_tuple == red.rgb_tuple
        elif ratio == 1.0:
            assert result.rgb_tuple == green.rgb_tuple

        # Alpha should be preserved
        assert result.alpha == red.alpha

    @pytest.mark.parametrize("color_pair", [
        ('red', 'blue'), ('green', 'blue'), ('black', 'white'),
        ('yellow', 'cyan'), ('magenta', 'gray')
    ])
    def test_lab_interpolation_various_pairs(self, parser, test_colors, color_pair):
        """Test LAB interpolation between various color pairs."""
        color1 = test_colors[color_pair[0]]
        color2 = test_colors[color_pair[1]]

        # Test midpoint interpolation
        result = parser.interpolate_lab(color1, color2, 0.5)

        assert isinstance(result, ColorInfo)
        self.assert_color_in_range(result)
        assert result.alpha == color1.alpha

    def test_lab_interpolation_preserves_alpha(self, parser):
        """Test that LAB interpolation preserves alpha channel."""
        # Colors with different alpha values
        red_semi = ColorInfo(255, 0, 0, 0.5, ColorFormat.RGBA, "red_semi")
        blue_semi = ColorInfo(0, 0, 255, 0.7, ColorFormat.RGBA, "blue_semi")

        result = parser.interpolate_lab(red_semi, blue_semi, 0.5)

        assert isinstance(result, ColorInfo)
        self.assert_color_in_range(result)
        # Alpha should be interpolated
        expected_alpha = 0.5 + (0.7 - 0.5) * 0.5
        assert abs(result.alpha - expected_alpha) <= 0.01

    # LCH Interpolation with Hue Handling Tests

    @pytest.mark.parametrize("ratio", [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0])
    def test_lch_interpolation_hue_path(self, parser, test_colors, ratio):
        """Test LCH interpolation takes shortest hue path."""
        red = test_colors['red']
        cyan = test_colors['cyan']

        # Red is ~0°, Cyan is ~180° in hue
        # Should interpolate through shorter path
        result = parser.interpolate_lch(red, cyan, ratio)

        assert isinstance(result, ColorInfo)
        self.assert_color_in_range(result)

        # Check edge cases
        if ratio == 0.0:
            assert result.rgb_tuple == red.rgb_tuple
        elif ratio == 1.0:
            assert result.rgb_tuple == cyan.rgb_tuple

    def test_lch_hue_wraparound(self, parser):
        """Test LCH hue interpolation handles 0°/360° wraparound."""
        # Color near 0° hue
        color_0 = ColorInfo(255, 50, 50, 1.0, ColorFormat.RGB, "near_0")
        # Color near 360° hue
        color_360 = ColorInfo(255, 50, 100, 1.0, ColorFormat.RGB, "near_360")

        result = parser.interpolate_lch(color_0, color_360, 0.5)

        assert isinstance(result, ColorInfo)
        self.assert_color_in_range(result)

    def test_lch_interpolation_neutral_colors(self, parser, test_colors):
        """Test LCH interpolation with neutral colors (undefined hue)."""
        white = test_colors['white']
        gray = test_colors['gray']

        # Neutral colors have undefined hue, should still interpolate smoothly
        result = parser.interpolate_lch(white, gray, 0.5)

        assert isinstance(result, ColorInfo)
        self.assert_color_in_range(result)

    # Bezier Curve Interpolation Tests

    def test_bezier_cubic_interpolation(self, parser, test_colors):
        """Test cubic bezier curve interpolation between colors."""
        red = test_colors['red']
        green = test_colors['green']
        blue = test_colors['blue']
        yellow = test_colors['yellow']

        # 4-point bezier curve
        control_points = [red, green, blue, yellow]

        result = parser.interpolate_bezier(control_points, 0.5)

        assert isinstance(result, ColorInfo)
        self.assert_color_in_range(result)

    @pytest.mark.parametrize("t", [0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    def test_bezier_parametric_values(self, parser, test_colors, t):
        """Test bezier interpolation at various parametric values."""
        control_points = [
            test_colors['red'],
            test_colors['green'],
            test_colors['blue']
        ]

        result = parser.interpolate_bezier(control_points, t)

        assert isinstance(result, ColorInfo)
        self.assert_color_in_range(result)

        # Check edge cases
        if t == 0.0:
            assert result.rgb_tuple == test_colors['red'].rgb_tuple
        elif t == 1.0:
            assert result.rgb_tuple == test_colors['blue'].rgb_tuple

    # Color Harmony Generation Tests

    def test_complementary_harmony(self, parser, test_colors):
        """Test complementary color harmony generation."""
        red = test_colors['red']

        complements = parser.generate_complementary(red)

        assert isinstance(complements, list)
        assert len(complements) == 2  # Original + complement
        assert isinstance(complements[0], ColorInfo)
        assert isinstance(complements[1], ColorInfo)
        # First color should be the original
        assert complements[0].rgb_tuple == red.rgb_tuple

    def test_triadic_harmony(self, parser, test_colors):
        """Test triadic color harmony generation."""
        blue = test_colors['blue']

        triadic = parser.generate_triadic(blue)

        assert isinstance(triadic, list)
        assert len(triadic) == 3  # Three equally spaced colors
        for color in triadic:
            assert isinstance(color, ColorInfo)
            self.assert_color_in_range(color)
        # First color should be the original
        assert triadic[0].rgb_tuple == blue.rgb_tuple

    def test_analogous_harmony(self, parser, test_colors):
        """Test analogous color harmony generation."""
        green = test_colors['green']

        analogous = parser.generate_analogous(green, count=5)

        assert isinstance(analogous, list)
        assert len(analogous) == 5  # Requested count
        for color in analogous:
            assert isinstance(color, ColorInfo)
            self.assert_color_in_range(color)
        # Base color should be in the middle (index 2 for count=5)
        # Note: Due to rounding and color space conversions, we check approximate equality
        base_in_list = any(abs(c.red - green.red) <= 2 and
                          abs(c.green - green.green) <= 2 and
                          abs(c.blue - green.blue) <= 2 for c in analogous)
        assert base_in_list

    def test_split_complementary_harmony(self, parser, test_colors):
        """Test split-complementary color harmony."""
        yellow = test_colors['yellow']

        split_comp = parser.generate_split_complementary(yellow)

        assert isinstance(split_comp, list)
        assert len(split_comp) == 3  # Original + two split complements
        for color in split_comp:
            assert isinstance(color, ColorInfo)
            self.assert_color_in_range(color)
        # First color should be the original
        assert split_comp[0].rgb_tuple == yellow.rgb_tuple

    # Color Temperature and Tint Tests

    @pytest.mark.parametrize("temperature", [2000, 3000, 5000, 6500, 9000])
    def test_color_temperature_adjustment(self, parser, test_colors, temperature):
        """Test color temperature adjustment."""
        white = test_colors['white']

        adjusted = parser.adjust_temperature(white, temperature)

        assert isinstance(adjusted, ColorInfo)
        self.assert_color_in_range(adjusted)
        assert adjusted.alpha == white.alpha

    @pytest.mark.parametrize("tint", [-50, -25, 0, 25, 50])
    def test_color_tint_adjustment(self, parser, test_colors, tint):
        """Test color tint adjustment."""
        gray = test_colors['gray']

        adjusted = parser.adjust_tint(gray, tint)

        assert isinstance(adjusted, ColorInfo)
        self.assert_color_in_range(adjusted)
        assert adjusted.alpha == gray.alpha

    def test_white_balance_correction(self, parser, test_colors):
        """Test white balance correction (using temperature adjustment)."""
        image_color = test_colors['cyan']

        # Use temperature adjustment as white balance proxy
        corrected = parser.adjust_temperature(image_color, 6500)

        assert isinstance(corrected, ColorInfo)
        self.assert_color_in_range(corrected)
        assert corrected.alpha == image_color.alpha

    # Accessibility Contrast Ratio Tests

    def test_wcag_contrast_ratios(self, parser, test_colors):
        """Test WCAG contrast ratio calculations."""
        white = test_colors['white']
        black = test_colors['black']

        # Black on white should have high contrast (~21:1)
        contrast = parser.calculate_contrast_ratio(black, white)

        assert isinstance(contrast, (int, float))
        assert contrast > 15  # Should be close to 21:1
        assert contrast <= 21  # Upper theoretical limit

    @pytest.mark.parametrize("level", ["AA", "AAA"])
    def test_wcag_compliance_check(self, parser, test_colors, level):
        """Test WCAG compliance checking."""
        text_color = test_colors['black']
        bg_color = test_colors['white']

        compliant = parser.check_wcag_compliance(text_color, bg_color, level)

        assert isinstance(compliant, dict)
        assert compliant['normal_text_compliant'] is True  # Black on white should pass both AA and AAA
        assert compliant['large_text_compliant'] is True

    def test_find_accessible_color(self, parser, test_colors):
        """Test finding accessible color variant."""
        base_color = test_colors['gray']
        background = test_colors['white']

        # Should find a variant that meets accessibility standards
        accessible = parser.find_accessible_color(base_color, background, min_contrast=4.5)

        assert isinstance(accessible, ColorInfo)
        self.assert_color_in_range(accessible)

        # Verify it meets the contrast requirement
        contrast = parser.calculate_contrast_ratio(accessible, background)
        assert contrast >= 4.5

    # Edge Cases and Error Handling Tests

    def test_interpolation_edge_ratios(self, parser, test_colors):
        """Test interpolation with edge case ratios."""
        red = test_colors['red']
        blue = test_colors['blue']

        # Test valid edge ratios
        valid_ratios = [0.0, 1.0]
        for ratio in valid_ratios:
            result = parser.interpolate_lab(red, blue, ratio)
            assert isinstance(result, ColorInfo)
            self.assert_color_in_range(result)

        # Test invalid ratios should be clamped or raise appropriate errors
        invalid_ratios = [-0.1, 1.1, 2.0]
        for ratio in invalid_ratios:
            try:
                result = parser.interpolate_lab(red, blue, ratio)
                # If it doesn't raise an error, result should still be valid
                assert isinstance(result, ColorInfo)
                self.assert_color_in_range(result)
            except ValueError:
                # ValueError is acceptable for out-of-range ratios
                pass

    def test_invalid_color_inputs(self, parser):
        """Test interpolation with invalid color inputs."""
        valid_color = ColorInfo(128, 128, 128, 1.0, ColorFormat.RGB, "gray")

        # None color
        with pytest.raises((TypeError, AttributeError)):
            parser.interpolate_lab(valid_color, None, 0.5)

        # Invalid color object
        with pytest.raises((TypeError, AttributeError)):
            parser.interpolate_lab(valid_color, "not_a_color", 0.5)

    def test_interpolation_alpha_preservation(self, parser):
        """Test that all interpolation methods preserve alpha correctly."""
        semi_red = ColorInfo(255, 0, 0, 0.3, ColorFormat.RGBA, "semi_red")
        semi_blue = ColorInfo(0, 0, 255, 0.7, ColorFormat.RGBA, "semi_blue")

        interpolation_methods = ['interpolate_lab', 'interpolate_lch']

        for method_name in interpolation_methods:
            method = getattr(parser, method_name)
            result = method(semi_red, semi_blue, 0.5)

            assert isinstance(result, ColorInfo)
            self.assert_color_in_range(result)
            # Alpha should be interpolated
            expected_alpha = 0.3 + (0.7 - 0.3) * 0.5
            assert abs(result.alpha - expected_alpha) <= 0.01

    # Performance and Batch Processing Tests

    def test_batch_color_interpolation(self, parser, test_colors):
        """Test batch processing of color interpolations."""
        # Need pairs of colors for batch interpolation
        colors = [test_colors['red'], test_colors['green'], test_colors['blue'], test_colors['yellow']]
        ratios = [0.2, 0.5]

        results = parser.batch_interpolate(colors, ratios, method='lab')

        assert isinstance(results, list)
        assert len(results) == len(ratios)
        for result in results:
            assert isinstance(result, ColorInfo)
            self.assert_color_in_range(result)

    def test_gradient_generation(self, parser, test_colors):
        """Test automatic gradient generation with specified stops."""
        start_color = test_colors['red']
        end_color = test_colors['blue']
        num_stops = 10

        gradient = parser.generate_gradient(start_color, end_color, num_stops, method='lab')

        assert isinstance(gradient, list)
        assert len(gradient) == num_stops
        for color in gradient:
            assert isinstance(color, ColorInfo)
            self.assert_color_in_range(color)

        # First and last colors should match input
        assert gradient[0].rgb_tuple == start_color.rgb_tuple
        assert gradient[-1].rgb_tuple == end_color.rgb_tuple

    # Color Distance and Similarity Tests

    def test_delta_e_calculations(self, parser, test_colors):
        """Test basic color difference calculation using LAB space."""
        red = test_colors['red']
        slightly_different_red = ColorInfo(250, 5, 5, 1.0, ColorFormat.RGB, "similar_red")

        # Calculate basic Delta E using LAB distance
        lab1 = red.to_lab()
        lab2 = slightly_different_red.to_lab()

        delta_e = ((lab1[0] - lab2[0])**2 + (lab1[1] - lab2[1])**2 + (lab1[2] - lab2[2])**2)**0.5

        assert isinstance(delta_e, (int, float))
        assert delta_e >= 0  # Delta E should be non-negative
        assert delta_e < 20  # Should be small for similar colors

    def test_perceptual_color_distance(self, parser, test_colors):
        """Test perceptual color distance using LAB space."""
        color1 = test_colors['red']
        color2 = test_colors['green']

        # Calculate perceptual distance in LAB space
        lab1 = color1.to_lab()
        lab2 = color2.to_lab()
        distance = ((lab1[0] - lab2[0])**2 + (lab1[1] - lab2[1])**2 + (lab1[2] - lab2[2])**2)**0.5

        assert isinstance(distance, (int, float))
        assert distance >= 0  # Distance should be non-negative

        # Distance between different colors should be significant
        assert distance > 50

        # Distance from a color to itself should be 0
        lab_same = color1.to_lab()
        same_distance = ((lab1[0] - lab_same[0])**2 + (lab1[1] - lab_same[1])**2 + (lab1[2] - lab_same[2])**2)**0.5
        assert same_distance == 0


if __name__ == "__main__":
    # Run with: python -m pytest tests/unit/utils/test_color_interpolation.py -v
    pytest.main([__file__, "-v"])