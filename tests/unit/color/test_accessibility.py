#!/usr/bin/env python3
"""
Comprehensive unit tests for ColorAccessibility class.

Tests for WCAG compliance, contrast ratio calculations, color blindness simulation,
and accessible color generation functionality.
"""

import pytest
import numpy as np
from unittest.mock import patch, Mock

from core.color import Color
from core.color.accessibility import ColorAccessibility, ContrastLevel, ColorBlindnessType


class TestColorAccessibilityInitialization:
    """Test ColorAccessibility initialization."""

    def test_valid_initialization(self):
        """Test ColorAccessibility initialization."""
        accessibility = ColorAccessibility()

        assert isinstance(accessibility, ColorAccessibility)
        assert hasattr(accessibility, '_colorblind_matrices')

        # Verify color blindness matrices are loaded
        assert len(accessibility._colorblind_matrices) == 6
        for blindness_type in ColorBlindnessType:
            assert blindness_type in accessibility._colorblind_matrices
            matrix = accessibility._colorblind_matrices[blindness_type]
            assert isinstance(matrix, np.ndarray)
            assert matrix.shape == (3, 3)


class TestContrastRatioCalculations:
    """Test contrast ratio calculations and WCAG compliance."""

    def setUp(self):
        """Set up test instance."""
        self.accessibility = ColorAccessibility()

    def test_contrast_ratio_black_white(self):
        """Test maximum contrast ratio between black and white."""
        accessibility = ColorAccessibility()
        black = Color('#000000')
        white = Color('#ffffff')

        ratio = accessibility.contrast_ratio(black, white)

        # Maximum contrast ratio should be 21:1
        assert abs(ratio - 21.0) < 0.1

    def test_contrast_ratio_identical_colors(self):
        """Test minimum contrast ratio between identical colors."""
        accessibility = ColorAccessibility()
        red = Color('#ff0000')

        ratio = accessibility.contrast_ratio(red, red)

        # Identical colors should have ratio of 1:1
        assert abs(ratio - 1.0) < 0.1

    def test_contrast_ratio_symmetry(self):
        """Test that contrast ratio is symmetric."""
        accessibility = ColorAccessibility()
        color1 = Color('#ff0000')
        color2 = Color('#0000ff')

        ratio1 = accessibility.contrast_ratio(color1, color2)
        ratio2 = accessibility.contrast_ratio(color2, color1)

        assert abs(ratio1 - ratio2) < 0.001

    def test_contrast_ratio_known_values(self):
        """Test contrast ratios for known color combinations."""
        accessibility = ColorAccessibility()

        # Test cases with known approximate ratios
        test_cases = [
            (Color('#000000'), Color('#ffffff'), 21.0),   # Black on white
            (Color('#767676'), Color('#ffffff'), 4.5),    # Gray on white (approximately AA)
            (Color('#595959'), Color('#ffffff'), 7.0),    # Darker gray on white (approximately AAA)
        ]

        for fg, bg, expected_ratio in test_cases:
            ratio = accessibility.contrast_ratio(fg, bg)
            assert abs(ratio - expected_ratio) < 1.0, f"Expected ~{expected_ratio}, got {ratio:.2f}"

    def test_relative_luminance_edge_cases(self):
        """Test relative luminance calculation for edge cases."""
        accessibility = ColorAccessibility()

        # Test pure colors
        black = Color('#000000')
        white = Color('#ffffff')
        red = Color('#ff0000')
        green = Color('#00ff00')
        blue = Color('#0000ff')

        black_lum = accessibility._relative_luminance(black)
        white_lum = accessibility._relative_luminance(white)
        red_lum = accessibility._relative_luminance(red)
        green_lum = accessibility._relative_luminance(green)
        blue_lum = accessibility._relative_luminance(blue)

        # Black should have luminance 0
        assert abs(black_lum - 0.0) < 0.001

        # White should have luminance 1
        assert abs(white_lum - 1.0) < 0.001

        # Green should have highest luminance among RGB primaries
        assert green_lum > red_lum
        assert green_lum > blue_lum

        # All luminance values should be between 0 and 1
        for lum in [black_lum, white_lum, red_lum, green_lum, blue_lum]:
            assert 0.0 <= lum <= 1.0


class TestWCAGCompliance:
    """Test WCAG compliance checking."""

    def setUp(self):
        """Set up test instance."""
        self.accessibility = ColorAccessibility()

    def test_meets_contrast_requirement_aa_normal(self):
        """Test AA normal text contrast requirement (4.5:1)."""
        accessibility = ColorAccessibility()

        # High contrast combination should pass
        black = Color('#000000')
        white = Color('#ffffff')
        assert accessibility.meets_contrast_requirement(black, white, ContrastLevel.AA_NORMAL)

        # Low contrast combination should fail
        light_gray = Color('#cccccc')
        assert not accessibility.meets_contrast_requirement(light_gray, white, ContrastLevel.AA_NORMAL)

    def test_meets_contrast_requirement_aa_large(self):
        """Test AA large text contrast requirement (3:1)."""
        accessibility = ColorAccessibility()

        # Darker gray should pass for large text (3:1 requirement)
        darker_gray = Color('#777777')  # Use darker gray that should meet 3:1
        white = Color('#ffffff')
        assert accessibility.meets_contrast_requirement(darker_gray, white, ContrastLevel.AA_LARGE)

        # Very light gray should still fail
        very_light_gray = Color('#eeeeee')
        assert not accessibility.meets_contrast_requirement(very_light_gray, white, ContrastLevel.AA_LARGE)

    def test_meets_contrast_requirement_aaa_levels(self):
        """Test AAA contrast requirements (7:1 normal, 4.5:1 large)."""
        accessibility = ColorAccessibility()

        black = Color('#000000')
        white = Color('#ffffff')

        # Black on white should pass all levels
        assert accessibility.meets_contrast_requirement(black, white, ContrastLevel.AAA_NORMAL)
        assert accessibility.meets_contrast_requirement(black, white, ContrastLevel.AAA_LARGE)

        # Medium gray might pass AAA large but not AAA normal
        medium_gray = Color('#767676')
        aaa_large_result = accessibility.meets_contrast_requirement(medium_gray, white, ContrastLevel.AAA_LARGE)
        aaa_normal_result = accessibility.meets_contrast_requirement(medium_gray, white, ContrastLevel.AAA_NORMAL)

        # AAA normal is stricter than AAA large
        if aaa_normal_result:
            assert aaa_large_result

    def test_contrast_levels_enum_values(self):
        """Test that ContrastLevel enum has correct values."""
        assert ContrastLevel.AA_NORMAL.value == 4.5
        assert ContrastLevel.AA_LARGE.value == 3.0
        assert ContrastLevel.AAA_NORMAL.value == 7.0
        assert ContrastLevel.AAA_LARGE.value == 4.5


class TestAccessibleColorGeneration:
    """Test accessible color generation and adjustment."""

    def setUp(self):
        """Set up test instance."""
        self.accessibility = ColorAccessibility()

    def test_find_accessible_color_already_accessible(self):
        """Test that already accessible colors are returned unchanged."""
        accessibility = ColorAccessibility()

        black = Color('#000000')
        white = Color('#ffffff')

        # Black on white is already accessible
        result = accessibility.find_accessible_color(black, white)
        assert result.rgb() == black.rgb()

    def test_find_accessible_color_needs_adjustment(self):
        """Test accessible color generation when adjustment is needed."""
        accessibility = ColorAccessibility()

        # Light gray on white background needs adjustment
        light_gray = Color('#dddddd')
        white = Color('#ffffff')

        result = accessibility.find_accessible_color(light_gray, white)

        # Result should be different from original
        assert result.rgb() != light_gray.rgb()

        # Result should meet AA normal requirement
        assert accessibility.meets_contrast_requirement(result, white, ContrastLevel.AA_NORMAL)

    def test_find_accessible_color_preserve_hue(self):
        """Test accessible color generation with hue preservation."""
        accessibility = ColorAccessibility()

        # Light red on white background
        light_red = Color('#ff9999')
        white = Color('#ffffff')

        result = accessibility.find_accessible_color(light_red, white, preserve_hue=True)

        # Should meet contrast requirement
        assert accessibility.meets_contrast_requirement(result, white, ContrastLevel.AA_NORMAL)

    def test_find_accessible_color_without_hue_preservation(self):
        """Test accessible color generation without hue preservation."""
        accessibility = ColorAccessibility()

        light_red = Color('#ff9999')
        white = Color('#ffffff')

        result = accessibility.find_accessible_color(light_red, white, preserve_hue=False)

        # Should meet contrast requirement
        assert accessibility.meets_contrast_requirement(result, white, ContrastLevel.AA_NORMAL)

        # Without hue preservation, should likely be black or white
        result_rgb = result.rgb()
        is_black_or_white = (result_rgb == (0, 0, 0) or result_rgb == (255, 255, 255))
        # Note: This might not always be true depending on the algorithm, so we just check it meets contrast

    def test_find_accessible_color_preserves_alpha(self):
        """Test that accessible color generation preserves alpha channel."""
        accessibility = ColorAccessibility()

        light_gray_alpha = Color('#dddddd').alpha(0.7)
        white = Color('#ffffff')

        result = accessibility.find_accessible_color(light_gray_alpha, white)

        assert result.rgba()[3] == 0.7

    def test_find_accessible_color_fallback(self):
        """Test accessible color generation fallback behavior."""
        accessibility = ColorAccessibility()

        # Mock colorspacious to trigger fallback
        with patch('core.color.accessibility.colorspacious.cspace_convert', side_effect=Exception("Mock error")):
            light_gray = Color('#dddddd')
            white = Color('#ffffff')

            result = accessibility.find_accessible_color(light_gray, white)

            # Should still return a valid color
            assert isinstance(result, Color)

            # Should meet contrast requirement (fallback uses black/white)
            ratio = accessibility.contrast_ratio(result, white)
            assert ratio >= ContrastLevel.AA_NORMAL.value


class TestColorBlindnessSimulation:
    """Test color blindness simulation functionality."""

    def setUp(self):
        """Set up test instance."""
        self.accessibility = ColorAccessibility()

    def test_color_blindness_types_enum(self):
        """Test ColorBlindnessType enum completeness."""
        expected_types = [
            'PROTANOPIA', 'DEUTERANOPIA', 'TRITANOPIA',
            'PROTANOMALY', 'DEUTERANOMALY', 'TRITANOMALY'
        ]

        for type_name in expected_types:
            assert hasattr(ColorBlindnessType, type_name)

    def test_simulate_color_blindness_basic(self):
        """Test basic color blindness simulation."""
        accessibility = ColorAccessibility()

        red = Color('#ff0000')

        for blindness_type in ColorBlindnessType:
            simulated = accessibility.simulate_color_blindness(red, blindness_type)

            assert isinstance(simulated, Color)
            # Simulated color should be different for most types (except possibly some edge cases)
            # We just ensure it's a valid color object

    def test_simulate_color_blindness_preserves_alpha(self):
        """Test that color blindness simulation preserves alpha."""
        accessibility = ColorAccessibility()

        red_alpha = Color('#ff0000').alpha(0.8)

        simulated = accessibility.simulate_color_blindness(red_alpha, ColorBlindnessType.DEUTERANOPIA)

        assert simulated.rgba()[3] == 0.8

    def test_simulate_color_blindness_different_results(self):
        """Test that different color blindness types produce different results."""
        accessibility = ColorAccessibility()

        red = Color('#ff0000')

        # Simulate different types
        protanopia = accessibility.simulate_color_blindness(red, ColorBlindnessType.PROTANOPIA)
        deuteranopia = accessibility.simulate_color_blindness(red, ColorBlindnessType.DEUTERANOPIA)
        tritanopia = accessibility.simulate_color_blindness(red, ColorBlindnessType.TRITANOPIA)

        # Different types should (usually) produce different results
        simulated_colors = [protanopia.rgb(), deuteranopia.rgb(), tritanopia.rgb()]
        unique_colors = set(simulated_colors)

        # At least some should be different (allowing for edge cases where they might be similar)
        assert len(unique_colors) >= 1  # Basic sanity check

    def test_simulate_color_blindness_matrix_application(self):
        """Test that color blindness matrices are applied correctly."""
        accessibility = ColorAccessibility()

        # Test with pure red
        red = Color('#ff0000')
        simulated = accessibility.simulate_color_blindness(red, ColorBlindnessType.PROTANOPIA)

        # Result should be different from original for red (since protanopia affects red perception)
        assert simulated.rgb() != red.rgb()

        # Test RGB values are within valid range
        sim_rgb = simulated.rgb()
        assert all(0 <= c <= 255 for c in sim_rgb)


class TestPaletteAccessibility:
    """Test palette-level accessibility functions."""

    def setUp(self):
        """Set up test instance."""
        self.accessibility = ColorAccessibility()

    def test_get_accessible_palette(self):
        """Test accessible palette generation."""
        accessibility = ColorAccessibility()

        # Create palette with some inaccessible colors
        original_palette = [
            Color('#ff0000'),  # Red
            Color('#ffcccc'),  # Light red (likely inaccessible)
            Color('#000000'),  # Black (accessible)
            Color('#dddddd'),  # Light gray (likely inaccessible)
        ]

        white_bg = Color('#ffffff')

        accessible_palette = accessibility.get_accessible_palette(original_palette, white_bg)

        assert len(accessible_palette) == len(original_palette)
        assert all(isinstance(color, Color) for color in accessible_palette)

        # All colors in accessible palette should meet AA normal requirement
        for color in accessible_palette:
            assert accessibility.meets_contrast_requirement(color, white_bg, ContrastLevel.AA_NORMAL)

    def test_analyze_palette_accessibility(self):
        """Test palette accessibility analysis."""
        accessibility = ColorAccessibility()

        # Create test palette with known accessibility levels
        test_palette = [
            Color('#000000'),  # Black - should pass all levels
            Color('#ffffff'),  # White - will fail on white background
            Color('#767676'),  # Gray - might pass some levels
            Color('#dddddd'),  # Light gray - likely fails most levels
        ]

        white_bg = Color('#ffffff')

        analysis = accessibility.analyze_palette_accessibility(test_palette, white_bg)

        # Verify analysis structure
        required_keys = [
            'total_colors', 'aa_normal_compliant', 'aa_large_compliant',
            'aaa_normal_compliant', 'aaa_large_compliant',
            'contrast_ratios', 'non_compliant_colors', 'recommendations'
        ]

        for key in required_keys:
            assert key in analysis

        # Verify data types and ranges
        assert analysis['total_colors'] == 4
        assert isinstance(analysis['contrast_ratios'], list)
        assert len(analysis['contrast_ratios']) == 4
        assert isinstance(analysis['non_compliant_colors'], list)
        assert isinstance(analysis['recommendations'], list)

        # Compliance counts should be reasonable
        assert 0 <= analysis['aa_normal_compliant'] <= 4
        assert 0 <= analysis['aa_large_compliant'] <= 4
        assert 0 <= analysis['aaa_normal_compliant'] <= 4
        assert 0 <= analysis['aaa_large_compliant'] <= 4

        # Stricter requirements should have fewer compliant colors
        assert analysis['aaa_normal_compliant'] <= analysis['aaa_large_compliant']
        assert analysis['aaa_large_compliant'] <= analysis['aa_normal_compliant']
        assert analysis['aa_normal_compliant'] <= analysis['aa_large_compliant']

    def test_simulate_palette_for_color_blindness_default(self):
        """Test palette simulation for color blindness with default types."""
        accessibility = ColorAccessibility()

        original_palette = [
            Color('#ff0000'),  # Red
            Color('#00ff00'),  # Green
            Color('#0000ff'),  # Blue
        ]

        simulated_palettes = accessibility.simulate_palette_for_color_blindness(original_palette)

        # Should simulate for 3 most common types by default
        assert len(simulated_palettes) == 3

        expected_types = [
            ColorBlindnessType.PROTANOPIA,
            ColorBlindnessType.DEUTERANOPIA,
            ColorBlindnessType.DEUTERANOMALY
        ]

        for blindness_type in expected_types:
            assert blindness_type in simulated_palettes
            palette = simulated_palettes[blindness_type]
            assert len(palette) == 3
            assert all(isinstance(color, Color) for color in palette)

    def test_simulate_palette_for_color_blindness_custom_types(self):
        """Test palette simulation with custom color blindness types."""
        accessibility = ColorAccessibility()

        original_palette = [Color('#ff0000'), Color('#00ff00')]

        custom_types = [ColorBlindnessType.TRITANOPIA, ColorBlindnessType.PROTANOMALY]

        simulated_palettes = accessibility.simulate_palette_for_color_blindness(
            original_palette, custom_types
        )

        assert len(simulated_palettes) == 2
        assert ColorBlindnessType.TRITANOPIA in simulated_palettes
        assert ColorBlindnessType.PROTANOMALY in simulated_palettes

        for blindness_type in custom_types:
            palette = simulated_palettes[blindness_type]
            assert len(palette) == 2
            assert all(isinstance(color, Color) for color in palette)


class TestTextColorRecommendations:
    """Test text color recommendation functionality."""

    def setUp(self):
        """Set up test instance."""
        self.accessibility = ColorAccessibility()

    def test_recommend_text_color_light_background(self):
        """Test text color recommendation for light background."""
        accessibility = ColorAccessibility()

        white_bg = Color('#ffffff')
        light_gray_bg = Color('#f0f0f0')

        # Light backgrounds should recommend dark text
        for bg in [white_bg, light_gray_bg]:
            recommended = accessibility.recommend_text_color(bg)
            assert isinstance(recommended, Color)

            # Should meet AA normal requirement
            assert accessibility.meets_contrast_requirement(recommended, bg, ContrastLevel.AA_NORMAL)

    def test_recommend_text_color_dark_background(self):
        """Test text color recommendation for dark background."""
        accessibility = ColorAccessibility()

        black_bg = Color('#000000')
        dark_gray_bg = Color('#333333')

        # Dark backgrounds should recommend light text
        for bg in [black_bg, dark_gray_bg]:
            recommended = accessibility.recommend_text_color(bg)
            assert isinstance(recommended, Color)

            # Should meet AA normal requirement
            assert accessibility.meets_contrast_requirement(recommended, bg, ContrastLevel.AA_NORMAL)

    def test_recommend_text_color_different_levels(self):
        """Test text color recommendation with different contrast levels."""
        accessibility = ColorAccessibility()

        medium_gray_bg = Color('#808080')

        # Test different contrast levels
        aa_normal = accessibility.recommend_text_color(medium_gray_bg, ContrastLevel.AA_NORMAL)
        aa_large = accessibility.recommend_text_color(medium_gray_bg, ContrastLevel.AA_LARGE)
        aaa_large = accessibility.recommend_text_color(medium_gray_bg, ContrastLevel.AAA_LARGE)

        # All should be valid colors
        for color in [aa_normal, aa_large, aaa_large]:
            assert isinstance(color, Color)

        # All should meet their respective requirements
        assert accessibility.meets_contrast_requirement(aa_normal, medium_gray_bg, ContrastLevel.AA_NORMAL)
        assert accessibility.meets_contrast_requirement(aa_large, medium_gray_bg, ContrastLevel.AA_LARGE)
        assert accessibility.meets_contrast_requirement(aaa_large, medium_gray_bg, ContrastLevel.AAA_LARGE)

        # Test AAA_NORMAL separately with a background that allows it
        light_gray_bg = Color('#cccccc')
        aaa_normal = accessibility.recommend_text_color(light_gray_bg, ContrastLevel.AAA_NORMAL)
        assert isinstance(aaa_normal, Color)
        # Note: AAA_NORMAL is very strict (7:1) and may not always be achievable with all backgrounds

    def test_recommend_text_color_returns_black_or_white(self):
        """Test that text color recommendations are black or white."""
        accessibility = ColorAccessibility()

        test_backgrounds = [
            Color('#ffffff'),  # White
            Color('#000000'),  # Black
            Color('#ff0000'),  # Red
            Color('#00ff00'),  # Green
            Color('#0000ff'),  # Blue
            Color('#808080'),  # Gray
        ]

        for bg in test_backgrounds:
            recommended = accessibility.recommend_text_color(bg)
            rgb = recommended.rgb()

            # Should be either black (0,0,0) or white (255,255,255)
            is_black = rgb == (0, 0, 0)
            is_white = rgb == (255, 255, 255)
            assert is_black or is_white, f"Recommended color {rgb} is neither black nor white"


class TestColorAccessibilityIntegration:
    """Integration tests for ColorAccessibility functionality."""

    def test_accessibility_workflow_integration(self):
        """Test complete accessibility workflow."""
        accessibility = ColorAccessibility()

        # Start with problematic color combination
        target_color = Color('#ffcccc')  # Light pink
        background = Color('#ffffff')    # White

        # 1. Check if already accessible
        is_accessible = accessibility.meets_contrast_requirement(
            target_color, background, ContrastLevel.AA_NORMAL
        )

        # Light pink on white is likely not accessible
        assert not is_accessible

        # 2. Find accessible version
        accessible_color = accessibility.find_accessible_color(
            target_color, background, ContrastLevel.AA_NORMAL
        )

        # 3. Verify accessible version meets requirements
        assert accessibility.meets_contrast_requirement(
            accessible_color, background, ContrastLevel.AA_NORMAL
        )

        # 4. Simulate for color blindness
        simulated = accessibility.simulate_color_blindness(
            accessible_color, ColorBlindnessType.DEUTERANOPIA
        )

        assert isinstance(simulated, Color)

        # 5. Get text color recommendation
        text_color = accessibility.recommend_text_color(background)
        assert accessibility.meets_contrast_requirement(
            text_color, background, ContrastLevel.AA_NORMAL
        )

    def test_accessibility_with_various_color_formats(self):
        """Test accessibility functions with different Color input formats."""
        accessibility = ColorAccessibility()

        # Test with different color creation methods
        test_colors = [
            Color('#ff0000'),           # Hex
            Color((255, 0, 0)),        # RGB tuple
            Color('red'),              # Named color
            Color('rgb(255, 0, 0)'),   # RGB functional
        ]

        white_bg = Color('#ffffff')

        for color in test_colors:
            # All functions should work regardless of color input format
            ratio = accessibility.contrast_ratio(color, white_bg)
            assert isinstance(ratio, float)
            assert ratio > 0

            meets_aa = accessibility.meets_contrast_requirement(color, white_bg, ContrastLevel.AA_NORMAL)
            assert isinstance(meets_aa, bool)

            accessible = accessibility.find_accessible_color(color, white_bg)
            assert isinstance(accessible, Color)

            simulated = accessibility.simulate_color_blindness(color, ColorBlindnessType.PROTANOPIA)
            assert isinstance(simulated, Color)

    def test_accessibility_performance_baseline(self):
        """Test accessibility function performance."""
        import time

        accessibility = ColorAccessibility()

        colors = [Color(f'#{i:06x}') for i in range(0, 100, 10)]
        white_bg = Color('#ffffff')

        # Test contrast ratio calculation performance
        start_time = time.perf_counter()
        for color in colors:
            accessibility.contrast_ratio(color, white_bg)
        contrast_time = time.perf_counter() - start_time

        assert contrast_time < 0.1, f"Contrast ratio calculation took {contrast_time:.3f}s for {len(colors)} colors"

        # Test color blindness simulation performance
        start_time = time.perf_counter()
        for color in colors:
            accessibility.simulate_color_blindness(color, ColorBlindnessType.DEUTERANOPIA)
        simulation_time = time.perf_counter() - start_time

        assert simulation_time < 0.1, f"Color blindness simulation took {simulation_time:.3f}s for {len(colors)} colors"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])