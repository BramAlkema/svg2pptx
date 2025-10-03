#!/usr/bin/env python3
"""
Unit tests for Known Color Profiles.

Tests the built-in color profile support for standard color spaces
without requiring external ICC files.
"""

import pytest
import numpy as np
from tests.helpers.color_asserts import approx_eq, assert_rgb_close

from core.color.known_profiles import (
    get_known_profile,
    list_known_profiles,
    is_known_profile,
    convert_between_profiles,
    convert_to_srgb,
    get_profile_gamut_volume,
    get_profile_info,
    validate_profile_conversion,
    chromatic_adaptation,
    KNOWN_PROFILES
)
from core.color.profile_model import RenderingIntent


class TestKnownProfileRegistry:
    """Test known profile registry functionality."""

    def test_list_known_profiles(self):
        """Test getting list of known profiles."""
        profiles = list_known_profiles()

        # Should include all standard profiles
        expected_profiles = ['srgb', 'display-p3', 'adobe-rgb', 'rec2020', 'prophoto-rgb']
        for profile in expected_profiles:
            assert profile in profiles

    def test_get_known_profile(self):
        """Test profile retrieval by name."""
        # Test valid profiles
        srgb = get_known_profile('srgb')
        assert srgb is not None
        assert srgb.name == 'srgb'
        assert srgb.description == 'sRGB IEC61966-2.1'

        p3 = get_known_profile('display-p3')
        assert p3 is not None
        assert p3.name == 'display-p3'

        # Test case insensitive
        adobe = get_known_profile('Adobe-RGB')
        assert adobe is not None
        assert adobe.name == 'adobe-rgb'

        # Test with underscores
        rec2020 = get_known_profile('rec_2020')
        assert rec2020 is not None
        assert rec2020.name == 'rec2020'

    def test_get_unknown_profile(self):
        """Test handling of unknown profiles."""
        unknown = get_known_profile('nonexistent-profile')
        assert unknown is None

    def test_is_known_profile(self):
        """Test profile existence check."""
        assert is_known_profile('srgb') is True
        assert is_known_profile('display-p3') is True
        assert is_known_profile('ADOBE-RGB') is True  # Case insensitive
        assert is_known_profile('unknown-profile') is False


class TestColorConversion:
    """Test color conversion between profiles."""

    def test_srgb_identity_conversion(self):
        """Test sRGB to sRGB conversion is identity."""
        color = np.array([0.5, 0.7, 0.9])
        result = convert_to_srgb(color, 'srgb')

        assert_rgb_close(result, color, tolerance=1e-6)

    def test_display_p3_conversion(self):
        """Test Display P3 to sRGB conversion."""
        # Pure red in Display P3 should be converted to sRGB
        p3_red = np.array([1.0, 0.0, 0.0])
        srgb_result = convert_to_srgb(p3_red, 'display-p3')

        # Should be valid RGB
        assert len(srgb_result) == 3
        assert np.all(srgb_result >= 0)
        assert np.all(srgb_result <= 1)

        # Red channel should dominate
        assert srgb_result[0] > srgb_result[1]
        assert srgb_result[0] > srgb_result[2]

    def test_adobe_rgb_conversion(self):
        """Test Adobe RGB to sRGB conversion."""
        # Test conversion with mid-range values
        adobe_color = np.array([0.5, 0.6, 0.7])
        srgb_result = convert_to_srgb(adobe_color, 'adobe-rgb')

        # Should be valid RGB
        assert len(srgb_result) == 3
        assert np.all(srgb_result >= 0)
        assert np.all(srgb_result <= 1)

    def test_rec2020_conversion(self):
        """Test Rec2020 to sRGB conversion."""
        # Test with a range of values
        rec2020_colors = np.array([
            [0.2, 0.3, 0.4],
            [0.6, 0.7, 0.8],
            [1.0, 0.5, 0.0]
        ])

        for color in rec2020_colors:
            srgb_result = convert_to_srgb(color, 'rec2020')

            # Should be valid RGB
            assert len(srgb_result) == 3
            assert np.all(srgb_result >= 0)
            assert np.all(srgb_result <= 1)

    def test_prophoto_rgb_conversion(self):
        """Test ProPhoto RGB to sRGB conversion."""
        # ProPhoto RGB has very wide gamut
        prophoto_color = np.array([0.8, 0.2, 0.4])
        srgb_result = convert_to_srgb(prophoto_color, 'prophoto-rgb')

        # Should be valid RGB (may be clipped due to gamut mapping)
        assert len(srgb_result) == 3
        assert np.all(srgb_result >= 0)
        assert np.all(srgb_result <= 1)

    def test_convert_between_profiles(self):
        """Test conversion between arbitrary profiles."""
        # Convert from Adobe RGB to Display P3
        adobe_color = np.array([0.6, 0.7, 0.8])
        p3_result = convert_between_profiles(adobe_color, 'adobe-rgb', 'display-p3')

        # Should be valid RGB
        assert len(p3_result) == 3
        assert np.all(p3_result >= 0)
        assert np.all(p3_result <= 1)

    def test_batch_conversion(self):
        """Test conversion of multiple colors."""
        colors = np.array([
            [0.2, 0.3, 0.4],
            [0.5, 0.6, 0.7],
            [0.8, 0.9, 1.0]
        ])

        results = convert_to_srgb(colors, 'display-p3')

        assert results.shape == colors.shape
        assert np.all(results >= 0)
        assert np.all(results <= 1)

    def test_rendering_intent_parameter(self):
        """Test that rendering intent parameter is accepted."""
        color = np.array([0.5, 0.6, 0.7])

        # Should not raise error with different rendering intents
        for intent in RenderingIntent:
            result = convert_between_profiles(
                color, 'adobe-rgb', 'srgb', rendering_intent=intent
            )
            assert len(result) == 3


class TestChromaticAdaptation:
    """Test chromatic adaptation functionality."""

    def test_identity_adaptation(self):
        """Test adaptation with same white point is identity."""
        xyz = np.array([0.5, 0.6, 0.7])
        result = chromatic_adaptation(xyz, 'D65', 'D65')

        assert_rgb_close(result, xyz, tolerance=1e-6)

    def test_d65_to_d50_adaptation(self):
        """Test D65 to D50 adaptation."""
        xyz_d65 = np.array([0.5, 0.6, 0.7])
        xyz_d50 = chromatic_adaptation(xyz_d65, 'D65', 'D50')

        # Should be different from input
        assert not approx_eq(xyz_d50, xyz_d65, tol=1e-3)

        # Should be valid XYZ
        assert len(xyz_d50) == 3

    def test_batch_adaptation(self):
        """Test adaptation of multiple XYZ values."""
        xyz_batch = np.array([
            [0.2, 0.3, 0.4],
            [0.5, 0.6, 0.7],
            [0.8, 0.9, 1.0]
        ])

        result = chromatic_adaptation(xyz_batch, 'D65', 'D50')

        assert result.shape == xyz_batch.shape
        assert not approx_eq(result, xyz_batch, tol=1e-3)


class TestProfileMetadata:
    """Test profile metadata functionality."""

    def test_get_profile_info(self):
        """Test getting profile information."""
        info = get_profile_info('srgb')

        assert info is not None
        assert info['name'] == 'srgb'
        assert info['description'] == 'sRGB IEC61966-2.1'
        assert info['white_point'] == 'D65'
        assert info['gamma'] == 'srgb'
        assert info['gamut_volume'] == 1.0
        assert info['is_wide_gamut'] is False

    def test_get_wide_gamut_info(self):
        """Test wide gamut profile information."""
        info = get_profile_info('display-p3')

        assert info is not None
        assert info['is_wide_gamut'] is True
        assert info['gamut_volume'] > 1.0

    def test_get_unknown_profile_info(self):
        """Test handling of unknown profile info."""
        info = get_profile_info('unknown-profile')
        assert info is None

    def test_get_profile_gamut_volume(self):
        """Test gamut volume calculation."""
        # sRGB should be 1.0 (reference)
        assert get_profile_gamut_volume('srgb') == 1.0

        # Wide gamut profiles should be > 1.0
        assert get_profile_gamut_volume('display-p3') > 1.0
        assert get_profile_gamut_volume('rec2020') > 1.0

        # Unknown profile should return None
        assert get_profile_gamut_volume('unknown') is None

    def test_validate_profile_conversion(self):
        """Test profile conversion validation."""
        # Valid conversions
        assert validate_profile_conversion('srgb', 'display-p3') is True
        assert validate_profile_conversion('adobe-rgb', 'rec2020') is True

        # Invalid conversions
        assert validate_profile_conversion('unknown', 'srgb') is False
        assert validate_profile_conversion('srgb', 'unknown') is False


class TestProfileAccuracy:
    """Test color conversion accuracy."""

    def test_srgb_white_point_preservation(self):
        """Test that sRGB white point is preserved."""
        white = np.array([1.0, 1.0, 1.0])
        result = convert_to_srgb(white, 'srgb')

        assert_rgb_close(result, white, tolerance=1e-6)

    def test_srgb_black_point_preservation(self):
        """Test that sRGB black point is preserved."""
        black = np.array([0.0, 0.0, 0.0])
        result = convert_to_srgb(black, 'srgb')

        assert_rgb_close(result, black, tolerance=1e-6)

    def test_primary_colors_conversion(self):
        """Test conversion of primary colors."""
        primaries = np.array([
            [1.0, 0.0, 0.0],  # Red
            [0.0, 1.0, 0.0],  # Green
            [0.0, 0.0, 1.0],  # Blue
        ])

        for profile_name in ['display-p3', 'adobe-rgb']:
            results = convert_to_srgb(primaries, profile_name)

            # Results should be valid
            assert np.all(results >= 0)
            assert np.all(results <= 1)

            # Each primary should have its dominant channel
            assert results[0, 0] > results[0, 1]  # Red > Green for red primary
            assert results[0, 0] > results[0, 2]  # Red > Blue for red primary
            assert results[1, 1] > results[1, 0]  # Green > Red for green primary
            assert results[1, 1] > results[1, 2]  # Green > Blue for green primary
            assert results[2, 2] > results[2, 0]  # Blue > Red for blue primary
            assert results[2, 2] > results[2, 1]  # Blue > Green for blue primary


class TestErrorHandling:
    """Test error handling in profile operations."""

    def test_invalid_profile_conversion(self):
        """Test handling of invalid profile names."""
        color = np.array([0.5, 0.6, 0.7])

        with pytest.raises(ValueError, match="Unknown source profile"):
            convert_between_profiles(color, 'unknown-profile', 'srgb')

        with pytest.raises(ValueError, match="Unknown destination profile"):
            convert_between_profiles(color, 'srgb', 'unknown-profile')

    def test_invalid_color_input(self):
        """Test handling of invalid color inputs."""
        # Should handle various input shapes gracefully
        scalar_input = 0.5
        with pytest.raises((ValueError, IndexError)):
            convert_to_srgb(scalar_input, 'srgb')

    def test_edge_case_colors(self):
        """Test handling of edge case color values."""
        # Test with extreme values
        extreme_colors = np.array([
            [0.0, 0.0, 0.0],    # Black
            [1.0, 1.0, 1.0],    # White
            [1.0, 0.0, 0.0],    # Pure red
            [0.0, 1.0, 0.0],    # Pure green
            [0.0, 0.0, 1.0],    # Pure blue
            [0.5, 0.5, 0.5],    # Mid gray
        ])

        for profile_name in list_known_profiles():
            results = convert_to_srgb(extreme_colors, profile_name)

            # All results should be valid
            assert np.all(results >= 0)
            assert np.all(results <= 1)
            assert not np.any(np.isnan(results))
            assert not np.any(np.isinf(results))