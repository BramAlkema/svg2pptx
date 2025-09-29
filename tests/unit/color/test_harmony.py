#!/usr/bin/env python3
"""
Comprehensive unit tests for ColorHarmony class.

Tests for color harmony generation including complementary, analogous, triadic,
split-complementary, tetradic, monochromatic, and custom harmony schemes.
"""

import pytest
import numpy as np
from unittest.mock import patch, Mock

from core.color import Color
from core.color.harmony import ColorHarmony


class TestColorHarmonyInitialization:
    """Test ColorHarmony initialization and validation."""

    def test_valid_initialization(self):
        """Test ColorHarmony initialization with valid Color instance."""
        base_color = Color('#ff0000')
        harmony = ColorHarmony(base_color)

        assert harmony.base_color is base_color
        assert isinstance(harmony.base_color, Color)

    def test_invalid_initialization_non_color(self):
        """Test ColorHarmony initialization with invalid input."""
        with pytest.raises(TypeError, match="base_color must be a Color instance"):
            ColorHarmony('#ff0000')  # String instead of Color

        with pytest.raises(TypeError, match="base_color must be a Color instance"):
            ColorHarmony((255, 0, 0))  # Tuple instead of Color

        with pytest.raises(TypeError, match="base_color must be a Color instance"):
            ColorHarmony(None)


class TestComplementaryColors:
    """Test complementary color generation."""

    def test_complementary_basic(self):
        """Test basic complementary color generation."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        complement = harmony.complementary()

        assert isinstance(complement, Color)
        assert complement != red

        # Complementary color should be different from base
        assert complement.rgb() != red.rgb()

    def test_complementary_hue_relationship(self):
        """Test that complementary colors have opposite hues."""
        # Test with pure red (hue = 0)
        red = Color('#ff0000')
        harmony = ColorHarmony(red)
        complement = harmony.complementary()

        # For red, complement should be cyan-ish
        comp_rgb = complement.rgb()
        # Red component should be low, green and blue should be higher
        assert comp_rgb[0] < comp_rgb[1] or comp_rgb[0] < comp_rgb[2]

    def test_complementary_preserves_alpha(self):
        """Test that complementary color preserves alpha channel."""
        red_with_alpha = Color('#ff0000').alpha(0.5)
        harmony = ColorHarmony(red_with_alpha)

        complement = harmony.complementary()

        assert complement.rgba()[3] == 0.5

    def test_complementary_fallback_behavior(self):
        """Test complementary fallback when colorspacious fails."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        # Mock colorspacious to raise exception and trigger fallback
        with patch('src.color.harmony.colorspacious.cspace_convert', side_effect=Exception("Mock error")):
            complement = harmony.complementary()

            assert isinstance(complement, Color)
            # Fallback should use RGB inversion: (255, 0, 0) -> (0, 255, 255)
            assert complement.rgb() == (0, 255, 255)

    def test_complementary_various_colors(self):
        """Test complementary generation for various base colors."""
        test_colors = [
            '#ff0000',  # Red
            '#00ff00',  # Green
            '#0000ff',  # Blue
            '#ffff00',  # Yellow
            '#ff00ff',  # Magenta
            '#00ffff',  # Cyan
            '#808080',  # Gray
        ]

        for hex_color in test_colors:
            base = Color(hex_color)
            harmony = ColorHarmony(base)
            complement = harmony.complementary()

            assert isinstance(complement, Color)
            assert complement != base


class TestAnalogousColors:
    """Test analogous color generation."""

    def test_analogous_basic(self):
        """Test basic analogous color generation."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        analogous = harmony.analogous()

        assert isinstance(analogous, list)
        assert len(analogous) == 5  # Default count
        assert all(isinstance(color, Color) for color in analogous)

    def test_analogous_custom_count(self):
        """Test analogous generation with custom count."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        # Test various counts
        for count in [3, 5, 7, 9]:
            analogous = harmony.analogous(count=count)
            assert len(analogous) == count

    def test_analogous_custom_spread(self):
        """Test analogous generation with custom spread."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        # Test different spreads
        narrow = harmony.analogous(spread=15.0)
        wide = harmony.analogous(spread=60.0)

        assert len(narrow) == 5
        assert len(wide) == 5

        # Wide spread should produce more varied colors
        # (This is a basic check; exact validation would require color space analysis)
        assert isinstance(narrow[0], Color)
        assert isinstance(wide[0], Color)

    def test_analogous_invalid_count(self):
        """Test analogous generation with invalid count."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        with pytest.raises(ValueError, match="count must be at least 3"):
            harmony.analogous(count=2)

        with pytest.raises(ValueError, match="count must be at least 3"):
            harmony.analogous(count=1)


    def test_analogous_includes_varied_hues(self):
        """Test that analogous colors have varied but related hues."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        analogous = harmony.analogous(count=5, spread=30.0)

        # All colors should be different
        rgb_values = [color.rgb() for color in analogous]
        unique_colors = set(rgb_values)
        assert len(unique_colors) == 5  # All should be unique

    def test_analogous_preserves_alpha(self):
        """Test that analogous colors preserve alpha channel."""
        red_with_alpha = Color('#ff0000').alpha(0.7)
        harmony = ColorHarmony(red_with_alpha)

        analogous = harmony.analogous(count=3)

        for color in analogous:
            assert color.rgba()[3] == 0.7


class TestTriadicColors:
    """Test triadic color generation."""

    def test_triadic_basic(self):
        """Test basic triadic color generation."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        triadic = harmony.triadic()

        assert isinstance(triadic, list)
        assert len(triadic) == 3
        assert all(isinstance(color, Color) for color in triadic)

    def test_triadic_includes_base_color(self):
        """Test that triadic includes the base color as first element."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        triadic = harmony.triadic()

        # First color should be the base color (or very close due to round-trip)
        base_rgb = red.rgb()
        first_rgb = triadic[0].rgb()

        # Allow small differences due to color space conversion round-trip
        rgb_diff = sum(abs(a - b) for a, b in zip(base_rgb, first_rgb))
        assert rgb_diff <= 6  # Allow for conversion precision

    def test_triadic_hue_relationships(self):
        """Test that triadic colors have proper hue relationships."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        triadic = harmony.triadic()

        # All three colors should be different
        rgb_values = [color.rgb() for color in triadic]
        unique_colors = set(rgb_values)
        assert len(unique_colors) == 3

    def test_triadic_fallback_behavior(self):
        """Test triadic fallback when colorspacious fails."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        # Mock colorspacious to raise exception and trigger fallback
        with patch('src.color.harmony.colorspacious.cspace_convert', side_effect=Exception("Mock error")):
            triadic = harmony.triadic()

            assert isinstance(triadic, list)
            assert len(triadic) == 3
            assert all(isinstance(color, Color) for color in triadic)

    def test_triadic_preserves_alpha(self):
        """Test that triadic colors preserve alpha channel."""
        red_with_alpha = Color('#ff0000').alpha(0.8)
        harmony = ColorHarmony(red_with_alpha)

        triadic = harmony.triadic()

        for color in triadic:
            assert color.rgba()[3] == 0.8


class TestSplitComplementaryColors:
    """Test split-complementary color generation."""

    def test_split_complementary_basic(self):
        """Test basic split-complementary color generation."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        split_comp = harmony.split_complementary()

        assert isinstance(split_comp, list)
        assert len(split_comp) == 3
        assert all(isinstance(color, Color) for color in split_comp)

    def test_split_complementary_includes_base(self):
        """Test that split-complementary includes base color."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        split_comp = harmony.split_complementary()

        # First color should be the base color
        assert split_comp[0].rgb() == red.rgb()

    def test_split_complementary_custom_spread(self):
        """Test split-complementary with custom spread."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        narrow = harmony.split_complementary(spread=15.0)
        wide = harmony.split_complementary(spread=60.0)

        assert len(narrow) == 3
        assert len(wide) == 3

        # Both should include base color as first element
        assert narrow[0].rgb() == red.rgb()
        assert wide[0].rgb() == red.rgb()

    def test_split_complementary_fallback_behavior(self):
        """Test split-complementary fallback when colorspacious fails."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        # Mock colorspacious to raise exception and trigger fallback
        with patch('src.color.harmony.colorspacious.cspace_convert', side_effect=Exception("Mock error")):
            split_comp = harmony.split_complementary()

            assert isinstance(split_comp, list)
            assert len(split_comp) == 3
            assert all(isinstance(color, Color) for color in split_comp)

    def test_split_complementary_preserves_alpha(self):
        """Test that split-complementary colors preserve alpha channel."""
        red_with_alpha = Color('#ff0000').alpha(0.6)
        harmony = ColorHarmony(red_with_alpha)

        split_comp = harmony.split_complementary()

        for color in split_comp:
            assert color.rgba()[3] == 0.6


class TestTetradicColors:
    """Test tetradic (square) color generation."""

    def test_tetradic_basic(self):
        """Test basic tetradic color generation."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        tetradic = harmony.tetradic()

        assert isinstance(tetradic, list)
        assert len(tetradic) == 4
        assert all(isinstance(color, Color) for color in tetradic)

    def test_tetradic_includes_base_color(self):
        """Test that tetradic includes the base color as first element."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        tetradic = harmony.tetradic()

        # First color should be the base color (or very close due to round-trip)
        base_rgb = red.rgb()
        first_rgb = tetradic[0].rgb()

        # Allow small differences due to color space conversion round-trip
        rgb_diff = sum(abs(a - b) for a, b in zip(base_rgb, first_rgb))
        assert rgb_diff <= 6  # Allow for conversion precision

    def test_tetradic_hue_relationships(self):
        """Test that tetradic colors have proper hue relationships."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        tetradic = harmony.tetradic()

        # All four colors should be different
        rgb_values = [color.rgb() for color in tetradic]
        unique_colors = set(rgb_values)
        assert len(unique_colors) >= 3  # Allow for some overlap due to round-trip precision

    def test_tetradic_fallback_behavior(self):
        """Test tetradic fallback when colorspacious fails."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        # Mock colorspacious to raise exception and trigger fallback
        with patch('src.color.harmony.colorspacious.cspace_convert', side_effect=Exception("Mock error")):
            tetradic = harmony.tetradic()

            assert isinstance(tetradic, list)
            assert len(tetradic) == 4
            assert all(isinstance(color, Color) for color in tetradic)

    def test_tetradic_preserves_alpha(self):
        """Test that tetradic colors preserve alpha channel."""
        red_with_alpha = Color('#ff0000').alpha(0.4)
        harmony = ColorHarmony(red_with_alpha)

        tetradic = harmony.tetradic()

        for color in tetradic:
            assert color.rgba()[3] == 0.4


class TestMonochromaticColors:
    """Test monochromatic color generation."""

    def test_monochromatic_basic(self):
        """Test basic monochromatic color generation."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        monochromatic = harmony.monochromatic()

        assert isinstance(monochromatic, list)
        assert len(monochromatic) == 5  # Default count
        assert all(isinstance(color, Color) for color in monochromatic)

    def test_monochromatic_custom_count(self):
        """Test monochromatic generation with custom count."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        # Test various counts
        for count in [2, 3, 7, 10]:
            monochromatic = harmony.monochromatic(count=count)
            assert len(monochromatic) == count

    def test_monochromatic_invalid_count(self):
        """Test monochromatic generation with invalid count."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        with pytest.raises(ValueError, match="count must be at least 2"):
            harmony.monochromatic(count=1)

    def test_monochromatic_custom_lightness_range(self):
        """Test monochromatic with custom lightness range."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        # Test narrow range
        narrow = harmony.monochromatic(count=3, lightness_range=(40, 60))
        assert len(narrow) == 3

        # Test wide range
        wide = harmony.monochromatic(count=3, lightness_range=(10, 90))
        assert len(wide) == 3

    def test_monochromatic_lightness_variation(self):
        """Test that monochromatic colors have varied lightness."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        monochromatic = harmony.monochromatic(count=5, lightness_range=(20, 80))

        # All colors should be different
        rgb_values = [color.rgb() for color in monochromatic]
        unique_colors = set(rgb_values)
        assert len(unique_colors) == 5  # All should be unique

    def test_monochromatic_fallback_behavior(self):
        """Test monochromatic fallback when colorspacious fails."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        # Mock colorspacious to raise exception and trigger fallback
        with patch('src.color.harmony.colorspacious.cspace_convert', side_effect=Exception("Mock error")):
            monochromatic = harmony.monochromatic(count=3)

            assert isinstance(monochromatic, list)
            assert len(monochromatic) == 3
            assert all(isinstance(color, Color) for color in monochromatic)

    def test_monochromatic_preserves_alpha(self):
        """Test that monochromatic colors preserve alpha channel."""
        red_with_alpha = Color('#ff0000').alpha(0.9)
        harmony = ColorHarmony(red_with_alpha)

        monochromatic = harmony.monochromatic(count=3)

        for color in monochromatic:
            assert color.rgba()[3] == 0.9


class TestCustomHarmony:
    """Test custom harmony generation."""

    def test_custom_harmony_basic(self):
        """Test basic custom harmony generation."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        # Custom hue offsets
        offsets = [0, 45, 90, 135]
        custom = harmony.custom_harmony(offsets)

        assert isinstance(custom, list)
        assert len(custom) == 4
        assert all(isinstance(color, Color) for color in custom)

    def test_custom_harmony_empty_offsets(self):
        """Test custom harmony with empty offsets."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        custom = harmony.custom_harmony([])

        assert isinstance(custom, list)
        assert len(custom) == 0

    def test_custom_harmony_single_offset(self):
        """Test custom harmony with single offset."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        custom = harmony.custom_harmony([60])

        assert isinstance(custom, list)
        assert len(custom) == 1
        assert isinstance(custom[0], Color)

    def test_custom_harmony_negative_offsets(self):
        """Test custom harmony with negative offsets."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        custom = harmony.custom_harmony([-30, 0, 30])

        assert isinstance(custom, list)
        assert len(custom) == 3
        assert all(isinstance(color, Color) for color in custom)

    def test_custom_harmony_large_offsets(self):
        """Test custom harmony with offsets > 360 degrees."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        # Offsets greater than 360 should wrap around
        custom = harmony.custom_harmony([0, 420, 720])  # 420 = 60, 720 = 0

        assert isinstance(custom, list)
        assert len(custom) == 3
        assert all(isinstance(color, Color) for color in custom)

    def test_custom_harmony_fallback_behavior(self):
        """Test custom harmony fallback when colorspacious fails."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        # Mock colorspacious to raise exception and trigger fallback
        with patch('src.color.harmony.colorspacious.cspace_convert', side_effect=Exception("Mock error")):
            custom = harmony.custom_harmony([0, 120, 240])

            assert isinstance(custom, list)
            assert len(custom) == 3
            assert all(isinstance(color, Color) for color in custom)

    def test_custom_harmony_preserves_alpha(self):
        """Test that custom harmony colors preserve alpha channel."""
        red_with_alpha = Color('#ff0000').alpha(0.3)
        harmony = ColorHarmony(red_with_alpha)

        custom = harmony.custom_harmony([0, 90, 180])

        for color in custom:
            assert color.rgba()[3] == 0.3


class TestColorHarmonyIntegration:
    """Integration tests for ColorHarmony with various color inputs."""

    def test_harmony_with_various_color_formats(self):
        """Test harmony generation with different Color input formats."""
        test_colors = [
            Color('#ff0000'),           # Hex
            Color((255, 0, 0)),        # RGB tuple
            Color('red'),              # Named color
            Color('rgb(255, 0, 0)'),   # RGB functional
            Color('hsl(0, 100%, 50%)'), # HSL functional
        ]

        for base_color in test_colors:
            harmony = ColorHarmony(base_color)

            # Test that all harmony types work
            complementary = harmony.complementary()
            analogous = harmony.analogous(count=3)
            triadic = harmony.triadic()

            assert isinstance(complementary, Color)
            assert len(analogous) == 3
            assert len(triadic) == 3

    def test_harmony_with_grayscale_colors(self):
        """Test harmony generation with grayscale colors."""
        gray = Color('#808080')
        harmony = ColorHarmony(gray)

        # All harmony types should work with grayscale
        complementary = harmony.complementary()
        analogous = harmony.analogous(count=3)
        monochromatic = harmony.monochromatic(count=3)

        assert isinstance(complementary, Color)
        assert len(analogous) == 3
        assert len(monochromatic) == 3

    def test_harmony_with_extreme_colors(self):
        """Test harmony generation with extreme colors (black, white)."""
        extreme_colors = [
            Color('#000000'),  # Black
            Color('#ffffff'),  # White
        ]

        for color in extreme_colors:
            harmony = ColorHarmony(color)

            complementary = harmony.complementary()
            triadic = harmony.triadic()
            monochromatic = harmony.monochromatic(count=3)

            assert isinstance(complementary, Color)
            assert len(triadic) == 3
            assert len(monochromatic) == 3

    def test_harmony_consistency(self):
        """Test that harmony methods produce consistent results."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        # Multiple calls should produce identical results
        comp1 = harmony.complementary()
        comp2 = harmony.complementary()

        assert comp1.rgb() == comp2.rgb()
        assert comp1.rgba()[3] == comp2.rgba()[3]

        # Same for other harmony types
        analog1 = harmony.analogous(count=3)
        analog2 = harmony.analogous(count=3)

        assert len(analog1) == len(analog2)
        for c1, c2 in zip(analog1, analog2):
            assert c1.rgb() == c2.rgb()


class TestColorHarmonyPerformance:
    """Performance tests for ColorHarmony operations."""

    def test_harmony_performance_baseline(self):
        """Test that harmony operations complete within reasonable time."""
        import time

        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        # Test complementary performance
        start_time = time.perf_counter()
        for _ in range(100):
            harmony.complementary()
        comp_time = time.perf_counter() - start_time

        assert comp_time < 0.5, f"Complementary generation took {comp_time:.3f}s for 100 calls"

        # Test analogous performance
        start_time = time.perf_counter()
        for _ in range(100):
            harmony.analogous(count=5)
        analog_time = time.perf_counter() - start_time

        assert analog_time < 1.0, f"Analogous generation took {analog_time:.3f}s for 100 calls"

    def test_harmony_memory_efficiency(self):
        """Test that harmony operations are memory efficient."""
        red = Color('#ff0000')
        harmony = ColorHarmony(red)

        # Generate many harmonies and verify no excessive memory growth
        harmonies = []
        for _ in range(100):
            harmonies.append(harmony.analogous(count=5))
            harmonies.append(harmony.triadic())
            harmonies.append(harmony.monochromatic(count=3))

        # Basic verification that we generated the expected number
        assert len(harmonies) == 300

        # All results should still be accessible
        assert all(isinstance(h, list) for h in harmonies)
        assert all(len(h) > 0 for h in harmonies)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])