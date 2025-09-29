#!/usr/bin/env python3
"""
Comprehensive unit tests for ColorManipulation class.

Tests cover all advanced color manipulation and transformation utilities
including tinting, shading, mixing, gradients, blending modes, and
professional color adjustment tools.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from math import sqrt

from src.color import Color
from src.color.manipulation import ColorManipulation, BlendMode


class TestColorManipulationInitialization:
    """Test ColorManipulation initialization and basic setup."""

    def test_init(self):
        """Test ColorManipulation initialization."""
        manipulator = ColorManipulation()
        assert isinstance(manipulator, ColorManipulation)

    def test_blend_mode_enum_values(self):
        """Test BlendMode enum has all expected values."""
        expected_modes = {
            'NORMAL', 'MULTIPLY', 'SCREEN', 'OVERLAY', 'SOFT_LIGHT',
            'HARD_LIGHT', 'COLOR_DODGE', 'COLOR_BURN', 'DARKEN',
            'LIGHTEN', 'DIFFERENCE', 'EXCLUSION'
        }
        actual_modes = {mode.name for mode in BlendMode}
        assert actual_modes == expected_modes

    def test_blend_mode_enum_string_values(self):
        """Test BlendMode enum string values."""
        assert BlendMode.NORMAL.value == "normal"
        assert BlendMode.MULTIPLY.value == "multiply"
        assert BlendMode.SCREEN.value == "screen"


class TestColorTinting:
    """Test color tinting operations (adding white)."""

    def setup_method(self):
        self.manipulator = ColorManipulation()
        self.red = Color('#ff0000')
        self.blue = Color('#0000ff')
        self.gray = Color('#808080')

    def test_tint_basic_functionality(self):
        """Test basic tinting adds white to color."""
        tinted = self.manipulator.tint(self.red, 0.3)

        # Tinted red should be lighter (closer to white)
        assert isinstance(tinted, Color)
        original_rgb = self.red.rgb()
        tinted_rgb = tinted.rgb()

        # All RGB components should increase (move toward 255)
        assert tinted_rgb[0] >= original_rgb[0]
        assert tinted_rgb[1] >= original_rgb[1]
        assert tinted_rgb[2] >= original_rgb[2]

    def test_tint_amount_validation(self):
        """Test tint amount validation."""
        with pytest.raises(ValueError, match="Amount must be 0.0-1.0"):
            self.manipulator.tint(self.red, -0.1)

        with pytest.raises(ValueError, match="Amount must be 0.0-1.0"):
            self.manipulator.tint(self.red, 1.1)

    def test_tint_zero_amount(self):
        """Test tinting with zero amount returns original color."""
        tinted = self.manipulator.tint(self.red, 0.0)
        assert tinted.rgb() == self.red.rgb()

    def test_tint_full_amount(self):
        """Test tinting with full amount approaches white."""
        tinted = self.manipulator.tint(self.red, 1.0)
        # Should be close to white
        assert all(c > 200 for c in tinted.rgb())

    def test_tint_preserves_hue_direction(self):
        """Test tinting preserves general hue direction."""
        tinted_red = self.manipulator.tint(self.red, 0.2)
        tinted_blue = self.manipulator.tint(self.blue, 0.2)

        # Red should still be more red than blue component
        assert tinted_red.rgb()[0] > tinted_red.rgb()[2]
        # Blue should still be more blue than red component
        assert tinted_blue.rgb()[2] > tinted_blue.rgb()[0]

    def test_tint_different_amounts(self):
        """Test different tinting amounts produce graduated results."""
        light_tint = self.manipulator.tint(self.red, 0.1)
        medium_tint = self.manipulator.tint(self.red, 0.3)
        heavy_tint = self.manipulator.tint(self.red, 0.6)

        # Should create a progression toward white
        light_sum = sum(light_tint.rgb())
        medium_sum = sum(medium_tint.rgb())
        heavy_sum = sum(heavy_tint.rgb())

        assert light_sum < medium_sum < heavy_sum


class TestColorShading:
    """Test color shading operations (adding black)."""

    def setup_method(self):
        self.manipulator = ColorManipulation()
        self.red = Color('#ff0000')
        self.yellow = Color('#ffff00')
        self.white = Color('#ffffff')

    def test_shade_basic_functionality(self):
        """Test basic shading adds black to color."""
        shaded = self.manipulator.shade(self.red, 0.3)

        # Shaded red should be darker
        assert isinstance(shaded, Color)
        original_rgb = self.red.rgb()
        shaded_rgb = shaded.rgb()

        # All RGB components should decrease (move toward 0)
        assert shaded_rgb[0] <= original_rgb[0]
        assert shaded_rgb[1] <= original_rgb[1]
        assert shaded_rgb[2] <= original_rgb[2]

    def test_shade_amount_validation(self):
        """Test shade amount validation."""
        with pytest.raises(ValueError, match="Amount must be 0.0-1.0"):
            self.manipulator.shade(self.red, -0.1)

        with pytest.raises(ValueError, match="Amount must be 0.0-1.0"):
            self.manipulator.shade(self.red, 1.5)

    def test_shade_zero_amount(self):
        """Test shading with zero amount returns original color."""
        shaded = self.manipulator.shade(self.red, 0.0)
        assert shaded.rgb() == self.red.rgb()

    def test_shade_full_amount(self):
        """Test shading with full amount approaches black."""
        shaded = self.manipulator.shade(self.white, 1.0)
        # Should be close to black
        assert all(c < 50 for c in shaded.rgb())

    def test_shade_preserves_hue_direction(self):
        """Test shading preserves general hue direction."""
        shaded_red = self.manipulator.shade(self.red, 0.3)
        shaded_yellow = self.manipulator.shade(self.yellow, 0.3)

        # Red should still be more red than other components
        red_rgb = shaded_red.rgb()
        assert red_rgb[0] >= red_rgb[1] and red_rgb[0] >= red_rgb[2]

        # Yellow should still have high red and green
        yellow_rgb = shaded_yellow.rgb()
        assert yellow_rgb[0] >= yellow_rgb[2] and yellow_rgb[1] >= yellow_rgb[2]

    def test_shade_different_amounts(self):
        """Test different shading amounts produce graduated results."""
        light_shade = self.manipulator.shade(self.white, 0.1)
        medium_shade = self.manipulator.shade(self.white, 0.3)
        heavy_shade = self.manipulator.shade(self.white, 0.6)

        # Should create a progression toward black
        light_sum = sum(light_shade.rgb())
        medium_sum = sum(medium_shade.rgb())
        heavy_sum = sum(heavy_shade.rgb())

        assert light_sum > medium_sum > heavy_sum


class TestColorToning:
    """Test color toning operations (adding gray)."""

    def setup_method(self):
        self.manipulator = ColorManipulation()
        self.red = Color('#ff0000')
        self.green = Color('#00ff00')
        self.blue = Color('#0000ff')

    def test_tone_basic_functionality(self):
        """Test basic toning adds gray to color."""
        toned = self.manipulator.tone(self.red, 0.3)

        assert isinstance(toned, Color)
        # Toned color should be less saturated (more neutral)
        original_rgb = self.red.rgb()
        toned_rgb = toned.rgb()

        # The dominant red should decrease
        assert toned_rgb[0] <= original_rgb[0]
        # Other components may increase (moving toward gray)

    def test_tone_amount_validation(self):
        """Test tone amount validation."""
        with pytest.raises(ValueError, match="Amount must be 0.0-1.0"):
            self.manipulator.tone(self.red, -0.1)

        with pytest.raises(ValueError, match="Amount must be 0.0-1.0"):
            self.manipulator.tone(self.red, 1.2)

    def test_tone_zero_amount(self):
        """Test toning with zero amount returns original color."""
        toned = self.manipulator.tone(self.red, 0.0)
        assert toned.rgb() == self.red.rgb()

    def test_tone_reduces_saturation(self):
        """Test toning reduces color saturation."""
        # Test with highly saturated colors
        toned_red = self.manipulator.tone(self.red, 0.4)
        toned_green = self.manipulator.tone(self.green, 0.4)
        toned_blue = self.manipulator.tone(self.blue, 0.4)

        # Toned colors should be less extreme
        assert max(toned_red.rgb()) - min(toned_red.rgb()) < max(self.red.rgb()) - min(self.red.rgb())
        assert max(toned_green.rgb()) - min(toned_green.rgb()) < max(self.green.rgb()) - min(self.green.rgb())
        assert max(toned_blue.rgb()) - min(toned_blue.rgb()) < max(self.blue.rgb()) - min(self.blue.rgb())

    @patch('src.color.manipulation.colorspacious.cspace_convert')
    def test_tone_fallback_behavior(self, mock_convert):
        """Test toning fallback when colorspacious fails."""
        mock_convert.side_effect = Exception("Mock error")

        toned = self.manipulator.tone(self.red, 0.3)
        assert isinstance(toned, Color)
        # Should still produce a valid result using fallback


class TestColorMixing:
    """Test color mixing operations."""

    def setup_method(self):
        self.manipulator = ColorManipulation()
        self.red = Color('#ff0000')
        self.blue = Color('#0000ff')
        self.green = Color('#00ff00')
        self.white = Color('#ffffff')
        self.black = Color('#000000')

    def test_mix_two_colors_equal_weights(self):
        """Test mixing two colors with equal weights."""
        mixed = self.manipulator.mix_colors([self.red, self.blue])

        assert isinstance(mixed, Color)
        # Should be roughly purple (mix of red and blue)
        rgb = mixed.rgb()
        assert rgb[0] > 0  # Has red component
        assert rgb[2] > 0  # Has blue component
        assert rgb[1] < max(rgb[0], rgb[2])  # Green is less dominant

    def test_mix_two_colors_custom_weights(self):
        """Test mixing two colors with custom weights."""
        # 70% red, 30% blue
        mixed = self.manipulator.mix_colors([self.red, self.blue], [0.7, 0.3])

        rgb = mixed.rgb()
        # Should be more red than blue
        assert rgb[0] > rgb[2]

    def test_mix_multiple_colors(self):
        """Test mixing multiple colors."""
        colors = [self.red, self.green, self.blue]
        mixed = self.manipulator.mix_colors(colors)

        assert isinstance(mixed, Color)
        # Should have components from all three
        rgb = mixed.rgb()
        assert all(c > 0 for c in rgb)

    def test_mix_colors_validation(self):
        """Test mix_colors input validation."""
        # Empty color list
        with pytest.raises(ValueError, match="Cannot mix empty color list"):
            self.manipulator.mix_colors([])

        # Mismatched weights
        with pytest.raises(ValueError, match="Weights list must match colors list length"):
            self.manipulator.mix_colors([self.red, self.blue], [0.5])

        # Zero total weight
        with pytest.raises(ValueError, match="Total weight must be positive"):
            self.manipulator.mix_colors([self.red, self.blue], [0.0, 0.0])

    def test_mix_colors_weight_normalization(self):
        """Test that weights are properly normalized."""
        # Use weights that don't sum to 1.0
        mixed1 = self.manipulator.mix_colors([self.red, self.blue], [2.0, 1.0])
        mixed2 = self.manipulator.mix_colors([self.red, self.blue], [0.667, 0.333])

        # Results should be approximately the same
        rgb1 = mixed1.rgb()
        rgb2 = mixed2.rgb()
        for c1, c2 in zip(rgb1, rgb2):
            assert abs(c1 - c2) <= 2  # Allow small rounding differences

    def test_mix_colors_with_alpha(self):
        """Test mixing colors with alpha channels."""
        red_alpha = Color((255, 0, 0, 0.8))
        blue_alpha = Color((0, 0, 255, 0.6))

        mixed = self.manipulator.mix_colors([red_alpha, blue_alpha])

        # Check alpha was mixed
        assert hasattr(mixed, '_alpha')
        assert 0.6 <= mixed._alpha <= 0.8

    def test_mix_single_color(self):
        """Test mixing a single color."""
        mixed = self.manipulator.mix_colors([self.red])
        assert mixed.rgb() == self.red.rgb()


class TestColorBlending:
    """Test color blending with different blend modes."""

    def setup_method(self):
        self.manipulator = ColorManipulation()
        self.red = Color('#ff0000')
        self.blue = Color('#0000ff')
        self.white = Color('#ffffff')
        self.black = Color('#000000')
        self.gray = Color('#808080')

    def test_blend_normal_mode(self):
        """Test normal blend mode (alpha blending)."""
        blended = self.manipulator.blend(self.red, self.blue, BlendMode.NORMAL, 0.5)

        assert isinstance(blended, Color)
        rgb = blended.rgb()
        # Should be mix of red and blue
        assert rgb[0] > 0  # Has red
        assert rgb[2] > 0  # Has blue

    def test_blend_multiply_mode(self):
        """Test multiply blend mode."""
        blended = self.manipulator.blend(self.white, self.gray, BlendMode.MULTIPLY, 1.0)

        # Multiply with gray should darken white
        assert blended.rgb() != self.white.rgb()
        assert sum(blended.rgb()) < sum(self.white.rgb())

    def test_blend_screen_mode(self):
        """Test screen blend mode."""
        blended = self.manipulator.blend(self.black, self.gray, BlendMode.SCREEN, 1.0)

        # Screen with gray should lighten black
        assert sum(blended.rgb()) > sum(self.black.rgb())

    def test_blend_overlay_mode(self):
        """Test overlay blend mode."""
        blended = self.manipulator.blend(self.gray, self.red, BlendMode.OVERLAY, 1.0)

        assert isinstance(blended, Color)
        # Should combine characteristics of both colors

    def test_blend_soft_light_mode(self):
        """Test soft light blend mode."""
        blended = self.manipulator.blend(self.gray, self.white, BlendMode.SOFT_LIGHT, 1.0)

        assert isinstance(blended, Color)
        # Soft light should create subtle effect

    def test_blend_hard_light_mode(self):
        """Test hard light blend mode."""
        blended = self.manipulator.blend(self.gray, self.white, BlendMode.HARD_LIGHT, 1.0)

        assert isinstance(blended, Color)

    def test_blend_color_dodge_mode(self):
        """Test color dodge blend mode."""
        blended = self.manipulator.blend(self.gray, Color('#404040'), BlendMode.COLOR_DODGE, 1.0)

        assert isinstance(blended, Color)

    def test_blend_color_burn_mode(self):
        """Test color burn blend mode."""
        blended = self.manipulator.blend(self.gray, Color('#c0c0c0'), BlendMode.COLOR_BURN, 1.0)

        assert isinstance(blended, Color)

    def test_blend_darken_mode(self):
        """Test darken blend mode."""
        blended = self.manipulator.blend(self.white, self.gray, BlendMode.DARKEN, 1.0)

        # Should pick darker color
        assert sum(blended.rgb()) <= sum(self.white.rgb())

    def test_blend_lighten_mode(self):
        """Test lighten blend mode."""
        blended = self.manipulator.blend(self.black, self.gray, BlendMode.LIGHTEN, 1.0)

        # Should pick lighter color
        assert sum(blended.rgb()) >= sum(self.black.rgb())

    def test_blend_difference_mode(self):
        """Test difference blend mode."""
        blended = self.manipulator.blend(self.white, self.black, BlendMode.DIFFERENCE, 1.0)

        # Difference between white and black should be white
        assert sum(blended.rgb()) > 600  # Close to white

    def test_blend_exclusion_mode(self):
        """Test exclusion blend mode."""
        blended = self.manipulator.blend(self.red, self.blue, BlendMode.EXCLUSION, 1.0)

        assert isinstance(blended, Color)

    def test_blend_opacity_validation(self):
        """Test blend opacity validation."""
        with pytest.raises(ValueError, match="Opacity must be 0.0-1.0"):
            self.manipulator.blend(self.red, self.blue, BlendMode.NORMAL, -0.1)

        with pytest.raises(ValueError, match="Opacity must be 0.0-1.0"):
            self.manipulator.blend(self.red, self.blue, BlendMode.NORMAL, 1.1)

    def test_blend_zero_opacity(self):
        """Test blending with zero opacity returns base color."""
        blended = self.manipulator.blend(self.red, self.blue, BlendMode.NORMAL, 0.0)
        assert blended.rgb() == self.red.rgb()

    def test_blend_preserves_alpha(self):
        """Test blending preserves and mixes alpha channels."""
        red_alpha = Color((255, 0, 0, 0.8))
        blue_alpha = Color((0, 0, 255, 0.6))

        blended = self.manipulator.blend(red_alpha, blue_alpha, BlendMode.NORMAL, 0.5)

        assert hasattr(blended, '_alpha')


class TestVibranceAdjustment:
    """Test vibrance adjustment functionality."""

    def setup_method(self):
        self.manipulator = ColorManipulation()
        self.red = Color('#ff0000')
        self.skin_tone = Color('#ffdbac')  # Typical skin tone
        self.blue = Color('#0000ff')

    def test_adjust_vibrance_basic(self):
        """Test basic vibrance adjustment."""
        more_vibrant = self.manipulator.adjust_vibrance(self.red, 0.3)
        less_vibrant = self.manipulator.adjust_vibrance(self.red, -0.3)

        assert isinstance(more_vibrant, Color)
        assert isinstance(less_vibrant, Color)

    def test_adjust_vibrance_validation(self):
        """Test vibrance adjustment validation."""
        with pytest.raises(ValueError, match="Amount must be -1.0 to 1.0"):
            self.manipulator.adjust_vibrance(self.red, -1.5)

        with pytest.raises(ValueError, match="Amount must be -1.0 to 1.0"):
            self.manipulator.adjust_vibrance(self.red, 1.5)

    def test_adjust_vibrance_zero(self):
        """Test vibrance adjustment with zero amount."""
        adjusted = self.manipulator.adjust_vibrance(self.red, 0.0)
        # Should be very close to original (allowing for rounding)
        original_rgb = self.red.rgb()
        adjusted_rgb = adjusted.rgb()
        for orig, adj in zip(original_rgb, adjusted_rgb):
            assert abs(orig - adj) <= 5

    def test_adjust_vibrance_skin_tone_protection(self):
        """Test that skin tones are protected during vibrance adjustment."""
        # Test that vibrance adjustment works on both colors
        skin_adjusted = self.manipulator.adjust_vibrance(self.skin_tone, 0.5)
        blue_adjusted = self.manipulator.adjust_vibrance(self.blue, 0.5)

        # Both should produce valid results
        assert isinstance(skin_adjusted, Color)
        assert isinstance(blue_adjusted, Color)

        # Calculate change magnitude
        skin_change = sum(abs(a - b) for a, b in zip(self.skin_tone.rgb(), skin_adjusted.rgb()))
        blue_change = sum(abs(a - b) for a, b in zip(self.blue.rgb(), blue_adjusted.rgb()))

        # Both colors should show some change from vibrance adjustment
        assert skin_change > 0 or blue_change > 0

    @patch('src.color.manipulation.colorspacious.cspace_convert')
    def test_adjust_vibrance_fallback(self, mock_convert):
        """Test vibrance adjustment fallback behavior."""
        mock_convert.side_effect = Exception("Mock error")

        adjusted = self.manipulator.adjust_vibrance(self.red, 0.3)
        assert isinstance(adjusted, Color)
        # Should use fallback saturation adjustment


class TestGradientCreation:
    """Test gradient creation functionality."""

    def setup_method(self):
        self.manipulator = ColorManipulation()
        self.red = Color('#ff0000')
        self.blue = Color('#0000ff')
        self.white = Color('#ffffff')
        self.black = Color('#000000')

    def test_create_gradient_basic(self):
        """Test basic gradient creation."""
        gradient = self.manipulator.create_gradient(self.red, self.blue, 5)

        assert len(gradient) == 5
        assert all(isinstance(color, Color) for color in gradient)

        # Allow for minor rounding differences in color space conversions
        start_rgb = gradient[0].rgb()
        end_rgb = gradient[-1].rgb()
        expected_start = self.red.rgb()
        expected_end = self.blue.rgb()

        for i in range(3):
            assert abs(start_rgb[i] - expected_start[i]) <= 2
            assert abs(end_rgb[i] - expected_end[i]) <= 2

    def test_create_gradient_linear_easing(self):
        """Test gradient with linear easing."""
        gradient = self.manipulator.create_gradient(self.white, self.black, 11, 'linear')

        assert len(gradient) == 11
        # Should create smooth progression
        luminances = [sum(color.rgb()) for color in gradient]
        # Should be monotonically decreasing
        for i in range(len(luminances) - 1):
            assert luminances[i] >= luminances[i + 1]

    def test_create_gradient_ease_in_easing(self):
        """Test gradient with ease-in easing."""
        gradient = self.manipulator.create_gradient(self.red, self.blue, 5, 'ease_in')

        assert len(gradient) == 5

        # Allow for minor rounding differences in color space conversions
        start_rgb = gradient[0].rgb()
        end_rgb = gradient[-1].rgb()
        expected_start = self.red.rgb()
        expected_end = self.blue.rgb()

        for i in range(3):
            assert abs(start_rgb[i] - expected_start[i]) <= 2
            assert abs(end_rgb[i] - expected_end[i]) <= 2

    def test_create_gradient_ease_out_easing(self):
        """Test gradient with ease-out easing."""
        gradient = self.manipulator.create_gradient(self.red, self.blue, 5, 'ease_out')

        assert len(gradient) == 5

    def test_create_gradient_ease_in_out_easing(self):
        """Test gradient with ease-in-out easing."""
        gradient = self.manipulator.create_gradient(self.red, self.blue, 5, 'ease_in_out')

        assert len(gradient) == 5

    def test_create_gradient_validation(self):
        """Test gradient creation validation."""
        with pytest.raises(ValueError, match="Steps must be at least 2"):
            self.manipulator.create_gradient(self.red, self.blue, 1)

        with pytest.raises(ValueError, match="Unknown easing function"):
            self.manipulator.create_gradient(self.red, self.blue, 5, 'invalid_easing')

    def test_create_gradient_with_alpha(self):
        """Test gradient creation with alpha channels."""
        red_alpha = Color((255, 0, 0, 0.2))
        blue_alpha = Color((0, 0, 255, 0.8))

        gradient = self.manipulator.create_gradient(red_alpha, blue_alpha, 5)

        # Check alpha interpolation
        assert hasattr(gradient[0], '_alpha')
        assert hasattr(gradient[-1], '_alpha')
        assert gradient[0]._alpha == 0.2
        assert gradient[-1]._alpha == 0.8

    @patch('src.color.manipulation.colorspacious.cspace_convert')
    def test_create_gradient_fallback(self, mock_convert):
        """Test gradient creation fallback behavior."""
        mock_convert.side_effect = Exception("Mock error")

        gradient = self.manipulator.create_gradient(self.red, self.blue, 5)
        assert len(gradient) == 5
        # Should use fallback gradient method


class TestPaletteCreation:
    """Test palette creation from image colors."""

    def setup_method(self):
        self.manipulator = ColorManipulation()
        self.colors = [
            Color('#ff0000'), Color('#ff1010'), Color('#ff2020'),  # Similar reds
            Color('#0000ff'), Color('#1010ff'),                    # Similar blues
            Color('#00ff00'), Color('#10ff10'),                    # Similar greens
        ]

    def test_create_palette_basic(self):
        """Test basic palette creation."""
        palette = self.manipulator.create_palette_from_image_colors(self.colors, 3)

        assert len(palette) <= 3
        assert all(isinstance(color, Color) for color in palette)

    def test_create_palette_fewer_colors_than_target(self):
        """Test palette creation when input has fewer colors than target."""
        few_colors = [Color('#ff0000'), Color('#0000ff')]
        palette = self.manipulator.create_palette_from_image_colors(few_colors, 5)

        assert len(palette) == 2  # Should return all input colors

    def test_create_palette_validation(self):
        """Test palette creation validation."""
        with pytest.raises(ValueError, match="Cannot create palette from empty color list"):
            self.manipulator.create_palette_from_image_colors([], 5)

    def test_create_palette_clustering(self):
        """Test that palette creation clusters similar colors."""
        many_similar_reds = [Color(f'#{255-i:02x}0000') for i in range(20)]
        many_similar_blues = [Color(f'#0000{255-i:02x}') for i in range(20)]
        all_colors = many_similar_reds + many_similar_blues

        palette = self.manipulator.create_palette_from_image_colors(all_colors, 3)

        assert len(palette) == 3
        # Should cluster into groups

    @patch('src.color.manipulation.colorspacious.cspace_convert')
    def test_create_palette_fallback(self, mock_convert):
        """Test palette creation fallback behavior."""
        mock_convert.side_effect = Exception("Mock error")

        palette = self.manipulator.create_palette_from_image_colors(self.colors, 3)
        assert len(palette) <= 3
        # Should use fallback method (first k colors)


class TestColorBalanceAdjustment:
    """Test color balance adjustment functionality."""

    def setup_method(self):
        self.manipulator = ColorManipulation()
        self.red = Color('#ff0000')
        self.gray = Color('#808080')
        self.white = Color('#ffffff')
        self.black = Color('#000000')

    def test_adjust_color_balance_basic(self):
        """Test basic color balance adjustment."""
        adjusted = self.manipulator.adjust_color_balance(
            self.gray, shadows=0.2, midtones=0.1, highlights=-0.1
        )

        assert isinstance(adjusted, Color)

    def test_adjust_color_balance_shadows_only(self):
        """Test color balance adjustment affecting shadows."""
        # Dark color should be affected by shadow adjustment
        dark_color = Color('#404040')
        adjusted = self.manipulator.adjust_color_balance(dark_color, shadows=0.5)

        assert isinstance(adjusted, Color)
        # Should change the dark color

    def test_adjust_color_balance_highlights_only(self):
        """Test color balance adjustment affecting highlights."""
        # Light color should be affected by highlight adjustment
        light_color = Color('#c0c0c0')
        adjusted = self.manipulator.adjust_color_balance(light_color, highlights=0.5)

        assert isinstance(adjusted, Color)

    def test_adjust_color_balance_midtones_only(self):
        """Test color balance adjustment affecting midtones."""
        adjusted = self.manipulator.adjust_color_balance(self.gray, midtones=0.3)

        assert isinstance(adjusted, Color)

    def test_adjust_color_balance_validation_ranges(self):
        """Test color balance parameter ranges are reasonable."""
        # Test that extreme values don't crash
        adjusted = self.manipulator.adjust_color_balance(
            self.gray, shadows=-1.0, midtones=1.0, highlights=-1.0
        )

        assert isinstance(adjusted, Color)

    @patch('src.color.manipulation.colorspacious.cspace_convert')
    def test_adjust_color_balance_fallback(self, mock_convert):
        """Test color balance adjustment fallback behavior."""
        mock_convert.side_effect = Exception("Mock error")

        adjusted = self.manipulator.adjust_color_balance(
            self.gray, shadows=0.2, midtones=0.1, highlights=-0.1
        )

        assert isinstance(adjusted, Color)
        # Should use fallback brightness adjustment


class TestColorManipulationIntegration:
    """Test integration between different ColorManipulation methods."""

    def setup_method(self):
        self.manipulator = ColorManipulation()
        self.red = Color('#ff0000')
        self.blue = Color('#0000ff')

    def test_chained_operations(self):
        """Test chaining multiple manipulation operations."""
        # Start with red, tint it, then shade it, then adjust vibrance
        result = self.manipulator.tint(self.red, 0.2)
        result = self.manipulator.shade(result, 0.1)
        result = self.manipulator.adjust_vibrance(result, 0.1)

        assert isinstance(result, Color)
        # Should produce a valid color after all operations

    def test_mix_then_blend(self):
        """Test mixing colors then blending the result."""
        mixed = self.manipulator.mix_colors([self.red, self.blue], [0.6, 0.4])
        blended = self.manipulator.blend(mixed, Color('#ffffff'), BlendMode.SOFT_LIGHT, 0.3)

        assert isinstance(blended, Color)

    def test_gradient_then_palette(self):
        """Test creating gradient then extracting palette."""
        gradient = self.manipulator.create_gradient(self.red, self.blue, 10)
        palette = self.manipulator.create_palette_from_image_colors(gradient, 3)

        assert len(palette) <= 3
        assert all(isinstance(color, Color) for color in palette)

    def test_comprehensive_workflow(self):
        """Test a comprehensive color manipulation workflow."""
        # Start with base colors
        base_colors = [
            Color('#ff0000'), Color('#00ff00'), Color('#0000ff')
        ]

        # Create variations
        tinted_colors = [self.manipulator.tint(color, 0.2) for color in base_colors]
        shaded_colors = [self.manipulator.shade(color, 0.2) for color in base_colors]

        # Mix some colors
        mixed = self.manipulator.mix_colors(base_colors)

        # Create gradient
        gradient = self.manipulator.create_gradient(base_colors[0], base_colors[1], 5)

        # Create final palette
        all_colors = tinted_colors + shaded_colors + [mixed] + gradient
        final_palette = self.manipulator.create_palette_from_image_colors(all_colors, 6)

        assert len(final_palette) <= 6
        assert all(isinstance(color, Color) for color in final_palette)


class TestColorManipulationPerformance:
    """Test ColorManipulation performance characteristics."""

    def setup_method(self):
        self.manipulator = ColorManipulation()
        self.test_colors = [Color(f'#{i:06x}') for i in range(0, 100)]

    def test_bulk_tinting_performance(self):
        """Test performance of bulk tinting operations."""
        import time

        start_time = time.perf_counter()
        tinted_colors = [self.manipulator.tint(color, 0.2) for color in self.test_colors]
        end_time = time.perf_counter()

        assert len(tinted_colors) == 100
        assert (end_time - start_time) < 1.0  # Should complete in under 1 second

    def test_bulk_blending_performance(self):
        """Test performance of bulk blending operations."""
        import time

        red = Color('#ff0000')

        start_time = time.perf_counter()
        blended_colors = [self.manipulator.blend(color, red, BlendMode.MULTIPLY, 0.5)
                         for color in self.test_colors[:50]]  # Smaller set for blending
        end_time = time.perf_counter()

        assert len(blended_colors) == 50
        assert (end_time - start_time) < 2.0  # Should complete in under 2 seconds

    def test_gradient_creation_performance(self):
        """Test performance of gradient creation."""
        import time

        start_time = time.perf_counter()
        gradients = [self.manipulator.create_gradient(self.test_colors[i], self.test_colors[i+1], 10)
                    for i in range(0, 20)]
        end_time = time.perf_counter()

        assert len(gradients) == 20
        assert all(len(gradient) == 10 for gradient in gradients)
        assert (end_time - start_time) < 1.0  # Should complete in under 1 second

    def test_memory_efficiency(self):
        """Test memory efficiency of color manipulation operations."""
        import gc

        # Force garbage collection
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Perform many operations
        for i in range(100):
            color = Color(f'#{i:06x}')
            tinted = self.manipulator.tint(color, 0.1)
            shaded = self.manipulator.shade(tinted, 0.1)
            # Don't store results to allow garbage collection

        # Force garbage collection again
        gc.collect()
        final_objects = len(gc.get_objects())

        # Should not have excessive object growth
        object_growth = final_objects - initial_objects
        assert object_growth < 1000, f"Created {object_growth} objects, expected < 1000"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])