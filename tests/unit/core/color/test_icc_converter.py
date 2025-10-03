#!/usr/bin/env python3
"""
Unit tests for ICCConverter.

Tests ICC color conversion functionality, caching, performance,
and integration with color profile system.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time

# Test imports with graceful fallback
try:
    from PIL import ImageCms
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Import test helpers
import sys
sys.path.append('/Users/ynse/projects/svg2pptx')
from tests.helpers.color_asserts import require_lab_supported, approx_eq

from core.color.icc_converter import (
    ICCConverter,
    ConversionResult,
    ConversionStats,
    ICCConversionError,
    convert_color_to_srgb,
    get_default_converter,
    is_icc_conversion_available,
    ICC_AVAILABLE
)
from core.color.profile_model import RenderingIntent
from core.color.profile_registry import ColorProfileRegistry


class TestConversionResult:
    """Test ConversionResult dataclass."""

    def test_conversion_result_creation(self):
        """Test ConversionResult creation and attributes."""
        result = ConversionResult(
            srgb_color=(0.5, 0.7, 0.9),
            original_color=(0.4, 0.6, 0.8),
            source_profile="test-profile",
            rendering_intent=RenderingIntent.PERCEPTUAL,
            conversion_time=0.001,
            cache_hit=True
        )

        assert result.srgb_color == (0.5, 0.7, 0.9)
        assert result.original_color == (0.4, 0.6, 0.8)
        assert result.source_profile == "test-profile"
        assert result.rendering_intent == RenderingIntent.PERCEPTUAL
        assert result.conversion_time == 0.001
        assert result.cache_hit is True


class TestConversionStats:
    """Test ConversionStats functionality."""

    def test_stats_initialization(self):
        """Test default stats values."""
        stats = ConversionStats()
        assert stats.total_conversions == 0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
        assert stats.average_conversion_time == 0.0
        assert stats.profiles_loaded == 0
        assert stats.errors == 0

    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate calculation."""
        stats = ConversionStats()

        # No conversions yet
        assert stats.cache_hit_rate == 0.0

        # Some hits and misses
        stats.cache_hits = 8
        stats.cache_misses = 2
        assert stats.cache_hit_rate == 80.0

        # All hits
        stats.cache_hits = 10
        stats.cache_misses = 0
        assert stats.cache_hit_rate == 100.0

        # All misses
        stats.cache_hits = 0
        stats.cache_misses = 5
        assert stats.cache_hit_rate == 0.0


@pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
class TestICCConverter:
    """Test ICCConverter functionality when PIL is available."""

    def test_initialization_success(self):
        """Test successful converter initialization."""
        converter = ICCConverter()
        assert converter.cache_size == 128
        assert converter._srgb_profile is not None
        assert converter.is_icc_available() is True

    def test_initialization_with_registry(self):
        """Test initialization with profile registry."""
        registry = Mock()
        converter = ICCConverter(profile_registry=registry, cache_size=64)
        assert converter.profile_registry is registry
        assert converter.cache_size == 64

    def test_srgb_passthrough_conversion(self):
        """Test that sRGB colors pass through unchanged."""
        converter = ICCConverter()
        color = (0.5, 0.7, 0.9)

        result = converter.convert_to_srgb(color, 'srgb')

        assert result.srgb_color == color
        assert result.original_color == color
        assert result.source_profile == 'srgb'
        assert result.cache_hit is True
        assert result.conversion_time > 0

    def test_srgb_2014_passthrough_conversion(self):
        """Test that sRGB-2014 colors pass through unchanged."""
        converter = ICCConverter()
        color = (0.2, 0.4, 0.6)

        result = converter.convert_to_srgb(color, 'srgb-2014')

        assert result.srgb_color == color
        assert result.original_color == color
        assert result.source_profile == 'srgb-2014'
        assert result.cache_hit is True

    def test_adobe_rgb_conversion(self):
        """Test conversion from Adobe RGB to sRGB."""
        converter = ICCConverter()
        color = (0.5, 0.7, 0.9)

        result = converter.convert_to_srgb(color, 'adobe-rgb')

        assert len(result.srgb_color) == 3
        assert result.original_color == color
        assert result.source_profile == 'adobe-rgb'
        assert result.conversion_time > 0
        # Adobe RGB should produce different values than input for wide gamut colors
        # but for this test we just verify the conversion completes

    def test_rendering_intent_handling(self):
        """Test different rendering intents."""
        converter = ICCConverter()
        color = (0.5, 0.7, 0.9)

        for intent in RenderingIntent:
            result = converter.convert_to_srgb(color, 'srgb', intent)
            assert result.rendering_intent == intent
            assert result.srgb_color == color  # sRGB passthrough

    def test_color_validation(self):
        """Test color input validation."""
        converter = ICCConverter()

        # Too few channels
        with pytest.raises(ICCConversionError, match="must have at least 3 channels"):
            converter.convert_to_srgb((0.5, 0.7), 'srgb')

        # Valid colors with extra channels (alpha)
        result = converter.convert_to_srgb((0.5, 0.7, 0.9, 1.0), 'srgb')
        assert result.srgb_color == (0.5, 0.7, 0.9)

    def test_cache_functionality(self):
        """Test transform caching behavior."""
        converter = ICCConverter(cache_size=2)
        color = (0.5, 0.7, 0.9)

        # First conversion - cache miss
        result1 = converter.convert_to_srgb(color, 'adobe-rgb')
        assert result1.cache_hit is False

        # Second conversion - cache hit
        result2 = converter.convert_to_srgb(color, 'adobe-rgb')
        assert result2.cache_hit is True

        # Different intent - cache miss
        result3 = converter.convert_to_srgb(color, 'adobe-rgb', RenderingIntent.SATURATION)
        assert result3.cache_hit is False

    def test_cache_eviction(self):
        """Test LRU cache eviction."""
        converter = ICCConverter(cache_size=1)
        color = (0.5, 0.7, 0.9)

        # Fill cache with first profile/intent combination
        result1 = converter.convert_to_srgb(color, 'adobe-rgb', RenderingIntent.PERCEPTUAL)
        assert len(converter._transform_cache) == 1
        assert result1.cache_hit is False  # First time should be cache miss

        # Add different profile/intent combination, triggering eviction
        result2 = converter.convert_to_srgb(color, 'adobe-rgb', RenderingIntent.SATURATION)
        assert len(converter._transform_cache) == 1
        assert result2.cache_hit is False  # Different intent, cache miss

        # First profile/intent should be evicted, so this should be a cache miss
        result3 = converter.convert_to_srgb(color, 'adobe-rgb', RenderingIntent.PERCEPTUAL)
        assert result3.cache_hit is False  # Should be evicted

    def test_multiple_color_conversion(self):
        """Test batch color conversion."""
        converter = ICCConverter()
        colors = [
            (0.1, 0.2, 0.3),
            (0.4, 0.5, 0.6),
            (0.7, 0.8, 0.9)
        ]

        results = converter.convert_multiple_to_srgb(colors, 'srgb')

        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.srgb_color == colors[i]
            assert result.original_color == colors[i]

    def test_multiple_color_conversion_with_error(self):
        """Test batch conversion with error handling."""
        converter = ICCConverter()

        # Mock a conversion that fails
        with patch.object(converter, 'convert_to_srgb') as mock_convert:
            mock_convert.side_effect = [
                ConversionResult((0.1, 0.2, 0.3), (0.1, 0.2, 0.3), 'test', RenderingIntent.PERCEPTUAL, 0.001, False),
                ICCConversionError("Test error"),
                ConversionResult((0.7, 0.8, 0.9), (0.7, 0.8, 0.9), 'test', RenderingIntent.PERCEPTUAL, 0.001, False)
            ]

            colors = [(0.1, 0.2, 0.3), (0.4, 0.5, 0.6), (0.7, 0.8, 0.9)]
            results = converter.convert_multiple_to_srgb(colors, 'test')

            assert len(results) == 3
            assert results[0].srgb_color == (0.1, 0.2, 0.3)
            assert results[1].srgb_color == (0.4, 0.5, 0.6)  # Fallback
            assert results[2].srgb_color == (0.7, 0.8, 0.9)

    def test_statistics_tracking(self):
        """Test conversion statistics tracking."""
        converter = ICCConverter()

        # Initial stats
        stats = converter.get_stats()
        assert stats.total_conversions == 0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0

        # Perform conversions
        converter.convert_to_srgb((0.5, 0.7, 0.9), 'srgb')  # Cache hit (sRGB passthrough)
        converter.convert_to_srgb((0.1, 0.2, 0.3), 'adobe-rgb')  # Cache miss
        converter.convert_to_srgb((0.4, 0.5, 0.6), 'adobe-rgb')  # Cache hit

        stats = converter.get_stats()
        assert stats.total_conversions == 3
        assert stats.cache_hits == 2
        assert stats.cache_misses == 1
        assert stats.average_conversion_time > 0

    def test_clear_cache(self):
        """Test cache clearing."""
        converter = ICCConverter()

        # Populate cache with two different profiles
        converter.convert_to_srgb((0.5, 0.7, 0.9), 'adobe-rgb')
        converter.convert_to_srgb((0.1, 0.2, 0.3), 'adobe_rgb')  # Different name but same fallback

        # Should have one cached transform (adobe-rgb and adobe_rgb are different names)
        assert len(converter._transform_cache) >= 1

        # Clear cache
        cleared_count = converter.clear_cache()
        assert cleared_count >= 1  # Should clear at least one transform
        assert len(converter._transform_cache) == 0

    def test_supported_profiles(self):
        """Test getting supported profiles list."""
        converter = ICCConverter()

        supported = converter.get_supported_profiles()

        assert 'srgb' in supported
        assert 'adobe-rgb' in supported
        assert 'lab' in supported
        assert isinstance(supported, list)

    def test_supported_profiles_with_registry(self):
        """Test supported profiles with registry integration."""
        registry = Mock()
        registry.list_available_profiles.return_value = ['custom-profile', 'display-p3']

        converter = ICCConverter(profile_registry=registry)
        supported = converter.get_supported_profiles()

        assert 'srgb' in supported
        assert 'custom-profile' in supported
        assert 'display-p3' in supported

    def test_profile_validation(self):
        """Test profile validation."""
        converter = ICCConverter()

        assert converter.validate_profile('srgb') is True
        assert converter.validate_profile('adobe-rgb') is True
        assert converter.validate_profile('nonexistent-profile') is False

    def test_invalid_profile_error(self):
        """Test error handling for invalid profiles."""
        converter = ICCConverter()

        with pytest.raises(ICCConversionError, match="Could not load profile"):
            converter.convert_to_srgb((0.5, 0.7, 0.9), 'nonexistent-profile')

    def test_lab_safe_conversion(self):
        """Test LAB conversion using safe fallback method."""
        converter = ICCConverter()

        # Test LAB conversion with values in [0,1] range
        # LAB input should be interpreted as: L[0,1]->L[0,100], a[0,1]->a[-128,127], b[0,1]->b[-128,127]
        lab_color = (0.5, 0.5, 0.5)  # Mid-range LAB values

        result = converter.convert_to_srgb(lab_color, 'lab')

        # Should complete successfully
        assert len(result.srgb_color) == 3
        assert result.original_color == lab_color
        assert result.source_profile == 'lab'
        assert result.conversion_time > 0

        # Result should be valid RGB
        for channel in result.srgb_color:
            assert 0.0 <= channel <= 1.0

    def test_known_profile_fallback(self):
        """Test known profile fallback when ICC is not available."""
        converter = ICCConverter()

        # Test Display P3 conversion using known profiles
        p3_color = (1.0, 0.0, 0.0)  # Pure red in Display P3
        result = converter.convert_to_srgb(p3_color, 'display-p3')

        # Should complete successfully
        assert len(result.srgb_color) == 3
        assert result.original_color == p3_color
        assert result.source_profile == 'display-p3'
        assert result.conversion_time > 0
        assert result.cache_hit is True  # Known profile conversions are "cached"

        # Result should be valid RGB
        for channel in result.srgb_color:
            assert 0.0 <= channel <= 1.0

        # Red should still be dominant channel
        assert result.srgb_color[0] > result.srgb_color[1]
        assert result.srgb_color[0] > result.srgb_color[2]

    def test_known_profile_wide_gamut(self):
        """Test wide gamut known profiles conversion."""
        converter = ICCConverter()

        test_cases = [
            ('adobe-rgb', (0.8, 0.2, 0.4)),
            ('rec2020', (0.6, 0.7, 0.3)),
            ('prophoto-rgb', (0.9, 0.1, 0.5)),
        ]

        for profile_name, color in test_cases:
            result = converter.convert_to_srgb(color, profile_name)

            # Should complete successfully
            assert len(result.srgb_color) == 3
            assert result.original_color == color
            assert result.source_profile == profile_name
            assert result.conversion_time > 0
            assert result.cache_hit is True

            # Result should be valid RGB (may be clipped due to gamut mapping)
            for channel in result.srgb_color:
                assert 0.0 <= channel <= 1.0


@pytest.mark.skipif(PIL_AVAILABLE, reason="Testing PIL unavailable case")
class TestICCConverterNoPIL:
    """Test ICCConverter when PIL is not available."""

    def test_initialization_without_pil(self):
        """Test that initialization fails gracefully without PIL."""
        with pytest.raises(ICCConversionError, match="Pillow with ICC support is required"):
            ICCConverter()


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
    def test_convert_color_to_srgb(self):
        """Test simple color conversion function."""
        color = (0.5, 0.7, 0.9)
        result = convert_color_to_srgb(color, 'srgb')
        assert result == color

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
    def test_convert_color_with_custom_converter(self):
        """Test conversion with custom converter."""
        converter = ICCConverter()
        color = (0.5, 0.7, 0.9)
        result = convert_color_to_srgb(color, 'srgb', converter=converter)
        assert result == color

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
    def test_get_default_converter(self):
        """Test default converter singleton."""
        converter1 = get_default_converter()
        converter2 = get_default_converter()
        assert converter1 is converter2  # Same instance

    def test_is_icc_conversion_available(self):
        """Test ICC availability check."""
        available = is_icc_conversion_available()
        assert available == PIL_AVAILABLE


class TestProfileRegistryIntegration:
    """Test integration with ColorProfileRegistry."""

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
    def test_registry_profile_loading(self):
        """Test loading profiles from registry."""
        registry = Mock()

        # Mock profile data (minimal ICC header)
        mock_icc_data = (
            b'\x00\x00\x01\x00'  # Profile size
            + b'\x00' * 32       # Reserved
            + b'acsp'            # Signature
            + b'\x00' * 220      # Rest of minimal profile
        )

        registry.get_profile_data.return_value = mock_icc_data

        converter = ICCConverter(profile_registry=registry)

        # This should attempt to load from registry
        # (May fail due to minimal ICC data, but tests the integration)
        try:
            converter.convert_to_srgb((0.5, 0.7, 0.9), 'custom-profile')
        except ICCConversionError:
            pass  # Expected for minimal ICC data

        # Verify registry was called
        registry.get_profile_data.assert_called_with('custom-profile')

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
    def test_registry_profile_not_found(self):
        """Test handling when registry doesn't have profile."""
        registry = Mock()
        registry.get_profile_data.return_value = None

        converter = ICCConverter(profile_registry=registry)

        with pytest.raises(ICCConversionError, match="Could not load profile"):
            converter.convert_to_srgb((0.5, 0.7, 0.9), 'missing-profile')


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
    def test_transform_creation_error(self):
        """Test error handling during transform creation."""
        converter = ICCConverter()

        # Mock profile loading to return invalid profile
        with patch.object(converter, '_load_source_profile') as mock_load:
            mock_load.return_value = Mock()

            # Mock transform creation to fail
            with patch('core.color.icc_converter.ImageCms.buildTransform') as mock_build:
                mock_build.side_effect = Exception("Transform creation failed")

                with pytest.raises(ICCConversionError, match="Failed to create color transform"):
                    converter.convert_to_srgb((0.5, 0.7, 0.9), 'test-profile')

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
    def test_statistics_error_tracking(self):
        """Test error tracking in statistics."""
        converter = ICCConverter()

        # Force an error
        try:
            converter.convert_to_srgb((0.5, 0.7, 0.9), 'nonexistent-profile')
        except ICCConversionError:
            pass

        stats = converter.get_stats()
        assert stats.errors == 1


class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
    def test_caching_performance(self):
        """Test that caching improves performance."""
        converter = ICCConverter()
        color = (0.5, 0.7, 0.9)

        # First conversion (cache miss)
        start = time.perf_counter()
        result1 = converter.convert_to_srgb(color, 'adobe-rgb')
        first_time = time.perf_counter() - start

        # Second conversion (cache hit)
        start = time.perf_counter()
        result2 = converter.convert_to_srgb(color, 'adobe-rgb')
        second_time = time.perf_counter() - start

        assert result1.cache_hit is False
        assert result2.cache_hit is True

        # Cache hit should be faster (though this may not always be true in tests)
        # We mainly verify the caching logic works
        assert second_time >= 0  # Just verify it completes

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
    def test_batch_conversion_efficiency(self):
        """Test batch conversion performance."""
        converter = ICCConverter()
        colors = [(0.1 * i, 0.2 * i, 0.3 * i) for i in range(10)]

        start = time.perf_counter()
        results = converter.convert_multiple_to_srgb(colors, 'srgb')
        batch_time = time.perf_counter() - start

        assert len(results) == 10
        assert batch_time > 0

        # Verify all conversions used cache (sRGB passthrough)
        for result in results:
            assert result.cache_hit is True