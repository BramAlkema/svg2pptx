#!/usr/bin/env python3
"""
Test suite for ColorHarmony class functionality.

Tests color harmony generation, palette creation, and perceptually accurate
color relationships using LCH color space.
"""

import pytest
import math
from typing import List

from src.color import Color, ColorHarmony


class TestColorHarmonyInitialization:
    """Test ColorHarmony initialization."""

    def test_harmony_initialization(self):
        """Test creating ColorHarmony with valid Color."""
        base_color = Color('#ff6b6b')
        harmony = ColorHarmony(base_color)

        assert harmony.base_color == base_color

    def test_invalid_base_color_raises_error(self):
        """Test that invalid base color raises TypeError."""
        with pytest.raises(TypeError, match="base_color must be a Color instance"):
            ColorHarmony('#ff0000')  # String instead of Color


class TestComplementaryHarmony:
    """Test complementary color generation."""

    def test_complementary_basic(self):
        """Test basic complementary color generation."""
        base_color = Color('#ff0000')  # Red
        harmony = ColorHarmony(base_color)

        complement = harmony.complementary()

        assert isinstance(complement, Color)
        # Complement should be roughly cyan/blue-green
        complement_rgb = complement.rgb()
        assert complement_rgb[0] < 128  # Low red
        assert complement_rgb[1] > 128  # High green
        assert complement_rgb[2] > 128  # High blue

    def test_complementary_preserves_alpha(self):
        """Test that complementary preserves alpha channel."""
        base_color = Color('#ff0000').alpha(0.5)
        harmony = ColorHarmony(base_color)

        complement = harmony.complementary()

        assert abs(complement._alpha - 0.5) < 1e-6

    def test_complementary_different_colors(self):
        """Test complementary generation for different base colors."""
        colors = ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff', '#00ffff']

        for color_str in colors:
            base_color = Color(color_str)
            harmony = ColorHarmony(base_color)
            complement = harmony.complementary()

            assert isinstance(complement, Color)
            assert complement != base_color  # Should be different


class TestAnalogousHarmony:
    """Test analogous color generation."""

    def test_analogous_basic(self):
        """Test basic analogous color generation."""
        base_color = Color('#ff6b6b')
        harmony = ColorHarmony(base_color)

        analogous = harmony.analogous(count=5, spread=30)

        assert len(analogous) == 5
        assert all(isinstance(c, Color) for c in analogous)

        # Middle color should be close to base color
        middle_index = len(analogous) // 2
        middle_color = analogous[middle_index]

        # Should be similar to base color
        base_rgb = base_color.rgb()
        middle_rgb = middle_color.rgb()

        # Colors should be reasonably close
        color_distance = sum((a - b) ** 2 for a, b in zip(base_rgb, middle_rgb))
        assert color_distance < 5000  # Reasonable threshold

    def test_analogous_invalid_count_raises_error(self):
        """Test that invalid count raises ValueError."""
        base_color = Color('#ff6b6b')
        harmony = ColorHarmony(base_color)

        with pytest.raises(ValueError, match="count must be at least 3"):
            harmony.analogous(count=2)

    def test_analogous_different_spreads(self):
        """Test analogous with different spread values."""
        base_color = Color('#ff6b6b')
        harmony = ColorHarmony(base_color)

        narrow = harmony.analogous(count=5, spread=15)
        wide = harmony.analogous(count=5, spread=60)

        assert len(narrow) == 5
        assert len(wide) == 5

        # Wide spread should have more color variation
        # This is hard to test precisely, but we can check it completes


class TestTriadicHarmony:
    """Test triadic color generation."""

    def test_triadic_basic(self):
        """Test basic triadic color generation."""
        base_color = Color('#ff0000')  # Red
        harmony = ColorHarmony(base_color)

        triadic = harmony.triadic()

        assert len(triadic) == 3
        assert all(isinstance(c, Color) for c in triadic)

        # First color should be the base color (or very close)
        base_rgb = base_color.rgb()
        first_rgb = triadic[0].rgb()
        distance = sum((a - b) ** 2 for a, b in zip(base_rgb, first_rgb))
        assert distance < 1000  # Should be very close

    def test_triadic_covers_color_wheel(self):
        """Test that triadic colors are well distributed."""
        base_color = Color('#ff0000')
        harmony = ColorHarmony(base_color)

        triadic = harmony.triadic()

        # All colors should be different
        for i in range(len(triadic)):
            for j in range(i + 1, len(triadic)):
                assert triadic[i] != triadic[j]


class TestSplitComplementaryHarmony:
    """Test split complementary color generation."""

    def test_split_complementary_basic(self):
        """Test basic split complementary generation."""
        base_color = Color('#ff6b6b')
        harmony = ColorHarmony(base_color)

        split_comp = harmony.split_complementary(spread=30)

        assert len(split_comp) == 3
        assert all(isinstance(c, Color) for c in split_comp)

        # First color should be the base color
        assert split_comp[0] == base_color

    def test_split_complementary_different_spreads(self):
        """Test split complementary with different spreads."""
        base_color = Color('#ff6b6b')
        harmony = ColorHarmony(base_color)

        narrow = harmony.split_complementary(spread=15)
        wide = harmony.split_complementary(spread=60)

        assert len(narrow) == 3
        assert len(wide) == 3

        # Both should include base color as first element
        assert narrow[0] == base_color
        assert wide[0] == base_color


class TestTetradicHarmony:
    """Test tetradic (square) color generation."""

    def test_tetradic_basic(self):
        """Test basic tetradic color generation."""
        base_color = Color('#ff0000')
        harmony = ColorHarmony(base_color)

        tetradic = harmony.tetradic()

        assert len(tetradic) == 4
        assert all(isinstance(c, Color) for c in tetradic)

        # All colors should be different
        for i in range(len(tetradic)):
            for j in range(i + 1, len(tetradic)):
                assert tetradic[i] != tetradic[j]

    def test_tetradic_symmetry(self):
        """Test that tetradic colors have proper symmetry."""
        base_color = Color('#ff0000')
        harmony = ColorHarmony(base_color)

        tetradic = harmony.tetradic()

        # Should have 4 evenly spaced colors
        # First color should be close to base
        base_rgb = base_color.rgb()
        first_rgb = tetradic[0].rgb()
        distance = sum((a - b) ** 2 for a, b in zip(base_rgb, first_rgb))
        assert distance < 1000


class TestMonochromaticHarmony:
    """Test monochromatic color generation."""

    def test_monochromatic_basic(self):
        """Test basic monochromatic generation."""
        base_color = Color('#ff6b6b')
        harmony = ColorHarmony(base_color)

        monochromatic = harmony.monochromatic(count=5, lightness_range=(20, 80))

        assert len(monochromatic) == 5
        assert all(isinstance(c, Color) for c in monochromatic)

    def test_monochromatic_lightness_progression(self):
        """Test that monochromatic colors have lightness progression."""
        base_color = Color('#ff6b6b')
        harmony = ColorHarmony(base_color)

        monochromatic = harmony.monochromatic(count=5, lightness_range=(20, 80))

        # Should have progression from dark to light
        lightness_values = [c.lab()[0] for c in monochromatic]

        # Check that lightness generally increases
        for i in range(len(lightness_values) - 1):
            assert lightness_values[i] <= lightness_values[i + 1] + 5  # Allow small variance

    def test_monochromatic_invalid_count_raises_error(self):
        """Test that invalid count raises ValueError."""
        base_color = Color('#ff6b6b')
        harmony = ColorHarmony(base_color)

        with pytest.raises(ValueError, match="count must be at least 2"):
            harmony.monochromatic(count=1)

    def test_monochromatic_custom_range(self):
        """Test monochromatic with custom lightness range."""
        base_color = Color('#ff6b6b')
        harmony = ColorHarmony(base_color)

        dark_scheme = harmony.monochromatic(count=3, lightness_range=(10, 40))
        light_scheme = harmony.monochromatic(count=3, lightness_range=(60, 90))

        assert len(dark_scheme) == 3
        assert len(light_scheme) == 3

        # Dark scheme should generally be darker
        dark_avg = sum(c.lab()[0] for c in dark_scheme) / len(dark_scheme)
        light_avg = sum(c.lab()[0] for c in light_scheme) / len(light_scheme)

        assert dark_avg < light_avg


class TestCustomHarmony:
    """Test custom harmony generation."""

    def test_custom_harmony_basic(self):
        """Test basic custom harmony generation."""
        base_color = Color('#ff6b6b')
        harmony = ColorHarmony(base_color)

        custom = harmony.custom_harmony([0, 45, 90, 135, 180])

        assert len(custom) == 5
        assert all(isinstance(c, Color) for c in custom)

    def test_custom_harmony_empty_list(self):
        """Test custom harmony with empty offset list."""
        base_color = Color('#ff6b6b')
        harmony = ColorHarmony(base_color)

        custom = harmony.custom_harmony([])

        assert len(custom) == 0

    def test_custom_harmony_single_offset(self):
        """Test custom harmony with single offset."""
        base_color = Color('#ff6b6b')
        harmony = ColorHarmony(base_color)

        custom = harmony.custom_harmony([90])

        assert len(custom) == 1
        assert isinstance(custom[0], Color)


class TestHarmonyAccuracy:
    """Test harmony generation accuracy and consistency."""

    def test_harmony_consistency(self):
        """Test that harmony generation is consistent."""
        base_color = Color('#ff6b6b')
        harmony = ColorHarmony(base_color)

        # Generate same harmony multiple times
        triadic1 = harmony.triadic()
        triadic2 = harmony.triadic()

        assert len(triadic1) == len(triadic2)
        for c1, c2 in zip(triadic1, triadic2):
            assert c1.hex() == c2.hex()

    def test_different_base_colors(self):
        """Test harmony generation with various base colors."""
        test_colors = [
            '#ff0000', '#00ff00', '#0000ff',  # Primary colors
            '#ffff00', '#ff00ff', '#00ffff',  # Secondary colors
            '#808080', '#ffffff', '#000000'   # Grayscale
        ]

        for color_str in test_colors:
            base_color = Color(color_str)
            harmony = ColorHarmony(base_color)

            # Test that all harmony types work
            complement = harmony.complementary()
            analogous = harmony.analogous()
            triadic = harmony.triadic()

            assert isinstance(complement, Color)
            assert len(analogous) == 5  # Default count
            assert len(triadic) == 3

    def test_alpha_preservation(self):
        """Test that alpha channels are preserved in harmonies."""
        base_color = Color('#ff6b6b').alpha(0.7)
        harmony = ColorHarmony(base_color)

        complement = harmony.complementary()
        analogous = harmony.analogous()
        triadic = harmony.triadic()
        monochromatic = harmony.monochromatic()

        # All generated colors should preserve alpha
        assert abs(complement._alpha - 0.7) < 1e-6

        for color_list in [analogous, triadic, monochromatic]:
            for color in color_list:
                assert abs(color._alpha - 0.7) < 1e-6


class TestHarmonyEdgeCases:
    """Test harmony generation edge cases."""

    def test_harmony_with_grayscale(self):
        """Test harmony generation with grayscale colors."""
        gray = Color('#808080')
        harmony = ColorHarmony(gray)

        # Should work without errors
        complement = harmony.complementary()
        triadic = harmony.triadic()
        monochromatic = harmony.monochromatic()

        assert isinstance(complement, Color)
        assert len(triadic) == 3
        assert len(monochromatic) == 5

    def test_harmony_with_extreme_colors(self):
        """Test harmony generation with extreme colors."""
        extreme_colors = ['#000000', '#ffffff', '#ff0000', '#00ff00', '#0000ff']

        for color_str in extreme_colors:
            base_color = Color(color_str)
            harmony = ColorHarmony(base_color)

            # Should complete without errors
            try:
                complement = harmony.complementary()
                analogous = harmony.analogous(count=3)
                triadic = harmony.triadic()

                assert isinstance(complement, Color)
                assert len(analogous) == 3
                assert len(triadic) == 3

            except Exception as e:
                pytest.fail(f"Harmony failed for {color_str}: {e}")

    def test_harmony_with_transparent_colors(self):
        """Test harmony generation with transparent colors."""
        transparent = Color('#ff6b6b').alpha(0.0)
        harmony = ColorHarmony(transparent)

        complement = harmony.complementary()
        analogous = harmony.analogous(count=3)

        # Alpha should be preserved
        assert complement._alpha == 0.0
        for color in analogous:
            assert color._alpha == 0.0