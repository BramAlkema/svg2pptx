#!/usr/bin/env python3
"""
Test suite for ColorAccessibility functionality.

Tests WCAG compliance checking, contrast calculations, color blindness simulation,
and accessible color generation.
"""

import pytest
import math
from typing import List

from src.color import Color, ColorAccessibility, ContrastLevel, ColorBlindnessType


class TestColorAccessibilityBasics:
    """Test basic ColorAccessibility functionality."""

    @pytest.fixture
    def accessibility(self):
        """Provide ColorAccessibility instance."""
        return ColorAccessibility()

    def test_accessibility_initialization(self, accessibility):
        """Test ColorAccessibility initialization."""
        assert isinstance(accessibility, ColorAccessibility)

    def test_contrast_ratio_white_black(self, accessibility):
        """Test contrast ratio calculation for maximum contrast."""
        white = Color('#ffffff')
        black = Color('#000000')

        ratio = accessibility.contrast_ratio(white, black)

        # Maximum contrast should be close to 21:1
        assert 20.5 <= ratio <= 21.5

    def test_contrast_ratio_same_colors(self, accessibility):
        """Test contrast ratio for identical colors."""
        red = Color('#ff0000')

        ratio = accessibility.contrast_ratio(red, red)

        # Same colors should have 1:1 ratio
        assert abs(ratio - 1.0) < 0.01

    def test_contrast_ratio_symmetry(self, accessibility):
        """Test that contrast ratio is symmetric."""
        color1 = Color('#ff0000')
        color2 = Color('#0000ff')

        ratio1 = accessibility.contrast_ratio(color1, color2)
        ratio2 = accessibility.contrast_ratio(color2, color1)

        assert abs(ratio1 - ratio2) < 0.01


class TestWCAGCompliance:
    """Test WCAG compliance checking."""

    @pytest.fixture
    def accessibility(self):
        """Provide ColorAccessibility instance."""
        return ColorAccessibility()

    def test_meets_aa_normal_text(self, accessibility):
        """Test WCAG AA compliance for normal text."""
        # High contrast combination
        white = Color('#ffffff')
        dark_blue = Color('#003366')

        meets_aa = accessibility.meets_contrast_requirement(
            dark_blue, white, ContrastLevel.AA_NORMAL
        )

        assert meets_aa

    def test_fails_aa_normal_text(self, accessibility):
        """Test WCAG AA failure for low contrast."""
        light_gray = Color('#cccccc')
        white = Color('#ffffff')

        meets_aa = accessibility.meets_contrast_requirement(
            light_gray, white, ContrastLevel.AA_NORMAL
        )

        assert not meets_aa

    def test_aaa_requirements_stricter(self, accessibility):
        """Test that AAA requirements are stricter than AA."""
        # Color that meets AA but not AAA
        gray = Color('#666666')
        white = Color('#ffffff')

        meets_aa = accessibility.meets_contrast_requirement(
            gray, white, ContrastLevel.AA_NORMAL
        )
        meets_aaa = accessibility.meets_contrast_requirement(
            gray, white, ContrastLevel.AAA_NORMAL
        )

        # Should meet AA but not AAA for this specific case
        assert meets_aa
        assert not meets_aaa

    def test_large_text_requirements(self, accessibility):
        """Test that large text has lower requirements."""
        color = Color('#757575')
        white = Color('#ffffff')

        meets_aa_normal = accessibility.meets_contrast_requirement(
            color, white, ContrastLevel.AA_NORMAL
        )
        meets_aa_large = accessibility.meets_contrast_requirement(
            color, white, ContrastLevel.AA_LARGE
        )

        # Large text should have lower requirements
        assert not meets_aa_normal or meets_aa_large


class TestAccessibleColorGeneration:
    """Test accessible color generation."""

    @pytest.fixture
    def accessibility(self):
        """Provide ColorAccessibility instance."""
        return ColorAccessibility()

    def test_find_accessible_color_already_compliant(self, accessibility):
        """Test finding accessible color when already compliant."""
        black = Color('#000000')
        white = Color('#ffffff')

        accessible = accessibility.find_accessible_color(
            black, white, ContrastLevel.AA_NORMAL
        )

        # Should return original color if already accessible
        assert accessible == black

    def test_find_accessible_color_light_background(self, accessibility):
        """Test finding accessible color for light background."""
        light_color = Color('#ffcccc')
        white_bg = Color('#ffffff')

        accessible = accessibility.find_accessible_color(
            light_color, white_bg, ContrastLevel.AA_NORMAL, preserve_hue=True
        )

        # Should be darker than original
        original_lab = light_color.lab()
        accessible_lab = accessible.lab()
        assert accessible_lab[0] < original_lab[0]

        # Should meet requirements
        assert accessibility.meets_contrast_requirement(
            accessible, white_bg, ContrastLevel.AA_NORMAL
        )

    def test_find_accessible_color_dark_background(self, accessibility):
        """Test finding accessible color for dark background."""
        dark_color = Color('#330000')
        black_bg = Color('#000000')

        accessible = accessibility.find_accessible_color(
            dark_color, black_bg, ContrastLevel.AA_NORMAL, preserve_hue=True
        )

        # Should meet requirements
        assert accessibility.meets_contrast_requirement(
            accessible, black_bg, ContrastLevel.AA_NORMAL
        )

    def test_accessible_palette_generation(self, accessibility):
        """Test generating accessible palette."""
        original_colors = [
            Color('#ffcccc'),  # Too light
            Color('#333333'),  # Good contrast
            Color('#ff6666'),  # Medium contrast
        ]
        white_bg = Color('#ffffff')

        accessible_palette = accessibility.get_accessible_palette(
            original_colors, white_bg, ContrastLevel.AA_NORMAL
        )

        assert len(accessible_palette) == len(original_colors)

        # All colors should meet requirements
        for color in accessible_palette:
            assert accessibility.meets_contrast_requirement(
                color, white_bg, ContrastLevel.AA_NORMAL
            )


class TestColorBlindnessSimulation:
    """Test color blindness simulation."""

    @pytest.fixture
    def accessibility(self):
        """Provide ColorAccessibility instance."""
        return ColorAccessibility()

    def test_simulate_deuteranopia(self, accessibility):
        """Test deuteranopia simulation."""
        green = Color('#00ff00')

        simulated = accessibility.simulate_color_blindness(
            green, ColorBlindnessType.DEUTERANOPIA
        )

        assert isinstance(simulated, Color)
        # Green should appear different to deuteranopes
        assert simulated.hex() != green.hex()

    def test_simulate_protanopia(self, accessibility):
        """Test protanopia simulation."""
        red = Color('#ff0000')

        simulated = accessibility.simulate_color_blindness(
            red, ColorBlindnessType.PROTANOPIA
        )

        assert isinstance(simulated, Color)
        # Red should appear different to protanopes
        assert simulated.hex() != red.hex()

    def test_simulate_tritanopia(self, accessibility):
        """Test tritanopia simulation."""
        blue = Color('#0000ff')

        simulated = accessibility.simulate_color_blindness(
            blue, ColorBlindnessType.TRITANOPIA
        )

        assert isinstance(simulated, Color)

    def test_simulate_palette_for_color_blindness(self, accessibility):
        """Test simulating entire palette for color blindness."""
        palette = [Color('#ff0000'), Color('#00ff00'), Color('#0000ff')]

        simulated_palettes = accessibility.simulate_palette_for_color_blindness(palette)

        assert len(simulated_palettes) == 3  # Default 3 common types

        for blindness_type, simulated_palette in simulated_palettes.items():
            assert len(simulated_palette) == len(palette)
            assert all(isinstance(c, Color) for c in simulated_palette)

    def test_alpha_preservation_in_simulation(self, accessibility):
        """Test that alpha is preserved in color blindness simulation."""
        transparent_red = Color('#ff0000').alpha(0.5)

        simulated = accessibility.simulate_color_blindness(
            transparent_red, ColorBlindnessType.DEUTERANOPIA
        )

        assert abs(simulated._alpha - 0.5) < 1e-6


class TestAccessibilityAnalysis:
    """Test accessibility analysis features."""

    @pytest.fixture
    def accessibility(self):
        """Provide ColorAccessibility instance."""
        return ColorAccessibility()

    def test_analyze_palette_accessibility(self, accessibility):
        """Test comprehensive palette accessibility analysis."""
        palette = [
            Color('#000000'),  # High contrast
            Color('#666666'),  # Medium contrast
            Color('#cccccc'),  # Low contrast
            Color('#ffffff'),  # Very high contrast
        ]
        white_bg = Color('#ffffff')

        analysis = accessibility.analyze_palette_accessibility(palette, white_bg)

        assert analysis['total_colors'] == 4
        assert isinstance(analysis['aa_normal_compliant'], int)
        assert isinstance(analysis['contrast_ratios'], list)
        assert len(analysis['contrast_ratios']) == 4
        assert isinstance(analysis['recommendations'], list)

        # High contrast colors should be identified
        assert analysis['aa_normal_compliant'] >= 1  # At least black should pass

    def test_recommend_text_color_light_background(self, accessibility):
        """Test text color recommendation for light background."""
        light_bg = Color('#f0f0f0')

        recommended = accessibility.recommend_text_color(
            light_bg, ContrastLevel.AA_NORMAL
        )

        # Should recommend dark text on light background
        assert recommended.hex() in ['000000', 'ffffff']

        # Should meet contrast requirements
        assert accessibility.meets_contrast_requirement(
            recommended, light_bg, ContrastLevel.AA_NORMAL
        )

    def test_recommend_text_color_dark_background(self, accessibility):
        """Test text color recommendation for dark background."""
        dark_bg = Color('#2c2c2c')

        recommended = accessibility.recommend_text_color(
            dark_bg, ContrastLevel.AA_NORMAL
        )

        # Should meet contrast requirements
        assert accessibility.meets_contrast_requirement(
            recommended, dark_bg, ContrastLevel.AA_NORMAL
        )


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def accessibility(self):
        """Provide ColorAccessibility instance."""
        return ColorAccessibility()

    def test_extreme_colors(self, accessibility):
        """Test accessibility with extreme colors."""
        extreme_colors = [
            Color('#000000'),  # Pure black
            Color('#ffffff'),  # Pure white
            Color('#ff0000'),  # Pure red
            Color('#00ff00'),  # Pure green
            Color('#0000ff'),  # Pure blue
        ]

        for color in extreme_colors:
            # Should not raise errors
            ratio_with_white = accessibility.contrast_ratio(color, Color('#ffffff'))
            ratio_with_black = accessibility.contrast_ratio(color, Color('#000000'))

            assert ratio_with_white > 0
            assert ratio_with_black > 0

    def test_transparent_colors(self, accessibility):
        """Test accessibility with transparent colors."""
        transparent = Color('#ff0000').alpha(0.0)
        white = Color('#ffffff')

        # Should handle transparent colors gracefully
        ratio = accessibility.contrast_ratio(transparent, white)
        assert ratio > 0

    def test_grayscale_colors(self, accessibility):
        """Test color blindness simulation with grayscale."""
        gray = Color('#808080')

        # Grayscale should be relatively unaffected by color blindness
        deuteranopia = accessibility.simulate_color_blindness(
            gray, ColorBlindnessType.DEUTERANOPIA
        )

        # Should still be a valid color
        assert isinstance(deuteranopia, Color)

    def test_find_accessible_color_preserve_hue_false(self, accessibility):
        """Test accessible color generation without hue preservation."""
        problematic = Color('#ffcccc')
        white_bg = Color('#ffffff')

        accessible = accessibility.find_accessible_color(
            problematic, white_bg, ContrastLevel.AA_NORMAL, preserve_hue=False
        )

        # Should meet requirements
        assert accessibility.meets_contrast_requirement(
            accessible, white_bg, ContrastLevel.AA_NORMAL
        )

        # Should be black or white for maximum contrast
        assert accessible.hex() in ['000000', 'ffffff']