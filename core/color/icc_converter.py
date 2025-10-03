#!/usr/bin/env python3
"""
Core ICC Color Converter

High-performance ICC color conversion engine using Pillow/LittleCMS.
Provides color space transformations with sRGB target for PowerPoint compatibility.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, Union, Any
from functools import lru_cache
import time

try:
    from PIL import ImageCms
    from PIL.ImageCms import ImageCmsProfile, ImageCmsTransform
    ICC_AVAILABLE = True
except ImportError:
    ImageCms = None
    ImageCmsProfile = None
    ImageCmsTransform = None
    ICC_AVAILABLE = False

from .profile_model import RenderingIntent, ColorProfileRef
from .profile_registry import ColorProfileRegistry

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """
    Result of ICC color conversion operation.

    Attributes:
        srgb_color: Converted sRGB color tuple (r, g, b) in [0, 1] range
        original_color: Original color values before conversion
        source_profile: Name of source color profile
        rendering_intent: Rendering intent used for conversion
        conversion_time: Time taken for conversion in seconds
        cache_hit: Whether the transform was retrieved from cache
    """
    srgb_color: Tuple[float, float, float]
    original_color: Tuple[float, ...]
    source_profile: str
    rendering_intent: RenderingIntent
    conversion_time: float
    cache_hit: bool


@dataclass
class ConversionStats:
    """
    Statistics for ICC conversion operations.

    Attributes:
        total_conversions: Total number of conversions performed
        cache_hits: Number of cache hits
        cache_misses: Number of cache misses
        average_conversion_time: Average time per conversion
        profiles_loaded: Number of profiles loaded
        errors: Number of conversion errors
    """
    total_conversions: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    average_conversion_time: float = 0.0
    profiles_loaded: int = 0
    errors: int = 0

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0


class ICCConversionError(Exception):
    """Exception raised during ICC color conversion."""
    pass


class ICCConverter:
    """
    High-performance ICC color converter with sRGB target.

    Provides color space transformations using Pillow/LittleCMS with
    caching, performance optimization, and comprehensive error handling.
    """

    def __init__(self, profile_registry: Optional[ColorProfileRegistry] = None,
                 cache_size: int = 128):
        """
        Initialize ICC converter.

        Args:
            profile_registry: Registry for profile resolution
            cache_size: Maximum number of cached transforms
        """
        if not ICC_AVAILABLE:
            raise ICCConversionError(
                "Pillow with ICC support is required but not available. "
                "Install with: pip install pillow"
            )

        self.profile_registry = profile_registry
        self.cache_size = cache_size
        self._transform_cache: Dict[str, ImageCmsTransform] = {}
        self._srgb_profile: Optional[ImageCmsProfile] = None
        self._stats = ConversionStats()

        # Initialize sRGB profile
        self._init_srgb_profile()

        logger.info(f"ICC Converter initialized with cache size {cache_size}")

    def _init_srgb_profile(self) -> None:
        """Initialize sRGB target profile."""
        try:
            self._srgb_profile = ImageCms.createProfile('sRGB')
            logger.debug("sRGB target profile created successfully")
        except Exception as e:
            raise ICCConversionError(f"Failed to create sRGB profile: {e}") from e

    def _get_cache_key(self, source_profile_name: str,
                      rendering_intent: RenderingIntent) -> str:
        """Generate cache key for transform."""
        return f"{source_profile_name}:{rendering_intent.value}"

    def _get_cms_intent(self, rendering_intent: RenderingIntent) -> int:
        """Convert RenderingIntent enum to ImageCms constant."""
        intent_map = {
            RenderingIntent.PERCEPTUAL: ImageCms.Intent.PERCEPTUAL,
            RenderingIntent.RELATIVE_COLORIMETRIC: ImageCms.Intent.RELATIVE_COLORIMETRIC,
            RenderingIntent.SATURATION: ImageCms.Intent.SATURATION,
            RenderingIntent.ABSOLUTE_COLORIMETRIC: ImageCms.Intent.ABSOLUTE_COLORIMETRIC,
            RenderingIntent.AUTO: ImageCms.Intent.PERCEPTUAL  # Default to perceptual
        }
        return intent_map.get(rendering_intent, ImageCms.Intent.PERCEPTUAL)

    def _load_source_profile(self, profile_name: str) -> Optional[ImageCmsProfile]:
        """Load source profile with fallback chain: ICC file → built-in profile → known profile → None."""
        try:
            # Step 1: Try ICC profiles from registry first
            if self.profile_registry:
                profile_data = self.profile_registry.get_profile_data(profile_name)
                if profile_data:
                    try:
                        from io import BytesIO
                        return ImageCms.ImageCmsProfile(BytesIO(profile_data))
                    except Exception as e:
                        logger.debug(f"Failed to load ICC data for {profile_name}: {e}")

            # Step 2: Try built-in LittleCMS profiles
            try:
                if profile_name.lower() in ['srgb', 'srgb-2014']:
                    return ImageCms.createProfile('sRGB')
                elif profile_name.lower() in ['lab', 'cielab']:
                    try:
                        return ImageCms.createProfile('LAB')
                    except Exception:
                        # LAB profile may not be compatible in this environment
                        logger.debug(f"LAB profile not available via LittleCMS, will use safe fallback")
                        return None  # Will trigger safe LAB handling
            except Exception as e:
                logger.debug(f"Built-in profile creation failed for {profile_name}: {e}")

            # Step 3: Check if it's a known profile that can be handled by fallback
            from .known_profiles import is_known_profile
            if is_known_profile(profile_name):
                logger.debug(f"Profile {profile_name} is a known profile, will use fallback conversion")
                return None  # Will trigger known profile handling

            logger.warning(f"Profile not found: {profile_name}")
            return None

        except Exception as e:
            logger.error(f"Failed to load profile {profile_name}: {e}")
            return None

    def _create_transform(self, source_profile: ImageCmsProfile,
                         rendering_intent: RenderingIntent) -> ImageCmsTransform:
        """Create color transform from source to sRGB."""
        try:
            cms_intent = self._get_cms_intent(rendering_intent)

            # Create transform with proper flags for accuracy
            try:
                # Try new API first (PIL 10+)
                flags = ImageCms.Flags.NOTPRECALC
            except (AttributeError, TypeError):
                # Fall back to legacy API
                try:
                    flags = ImageCms.FLAGS['NOTPRECALC']
                except (KeyError, AttributeError):
                    # If all else fails, use 0 (no flags)
                    flags = 0

            transform = ImageCms.buildTransform(
                source_profile,
                self._srgb_profile,
                'RGB',  # Input format
                'RGB',  # Output format
                renderingIntent=cms_intent,
                flags=flags
            )

            return transform

        except Exception as e:
            raise ICCConversionError(f"Failed to create color transform: {e}") from e

    def _get_transform(self, profile_name: str,
                      rendering_intent: RenderingIntent) -> Tuple[ImageCmsTransform, bool]:
        """Get cached transform or create new one."""
        cache_key = self._get_cache_key(profile_name, rendering_intent)

        # Check cache first
        if cache_key in self._transform_cache:
            return self._transform_cache[cache_key], True

        # Load source profile
        source_profile = self._load_source_profile(profile_name)
        if source_profile is None:
            raise ICCConversionError(f"Could not load profile: {profile_name}")

        # Create transform
        transform = self._create_transform(source_profile, rendering_intent)

        # Cache management - LRU eviction
        if len(self._transform_cache) >= self.cache_size:
            # Remove oldest entry (simple FIFO for now)
            oldest_key = next(iter(self._transform_cache))
            del self._transform_cache[oldest_key]

        # Cache the transform
        self._transform_cache[cache_key] = transform

        return transform, False

    def convert_to_srgb(self, color: Tuple[float, ...],
                       source_profile: str,
                       rendering_intent: RenderingIntent = RenderingIntent.PERCEPTUAL) -> ConversionResult:
        """
        Convert color from source profile to sRGB.

        Args:
            color: Color values in source profile space (typically RGB)
            source_profile: Name of source color profile
            rendering_intent: Rendering intent for conversion

        Returns:
            ConversionResult with sRGB color and metadata

        Raises:
            ICCConversionError: If conversion fails
        """
        start_time = time.perf_counter()

        try:
            # Validate input
            if len(color) < 3:
                raise ICCConversionError(f"Color must have at least 3 channels, got {len(color)}")

            # Extract RGB channels (ignore alpha for now)
            r, g, b = color[0], color[1], color[2]

            # Convert to 0-255 range for ImageCms
            r_255 = max(0, min(255, int(r * 255)))
            g_255 = max(0, min(255, int(g * 255)))
            b_255 = max(0, min(255, int(b * 255)))

            # Check if already sRGB
            if source_profile.lower() in ['srgb', 'srgb-2014']:
                conversion_time = time.perf_counter() - start_time
                self._stats.total_conversions += 1
                self._stats.cache_hits += 1
                self._update_average_time(conversion_time)

                return ConversionResult(
                    srgb_color=(r, g, b),
                    original_color=color,
                    source_profile=source_profile,
                    rendering_intent=rendering_intent,
                    conversion_time=conversion_time,
                    cache_hit=True
                )

            # Check for LAB conversion using safe fallback
            if source_profile.lower() in ['lab', 'cielab']:
                from .safe_lab import convert_lab_to_srgb_safe

                try:
                    # Convert LAB to sRGB using safe method
                    lab_color = (r * 100, g * 255 - 128, b * 255 - 128)  # Scale to LAB ranges
                    srgb_result = convert_lab_to_srgb_safe(lab_color)

                    conversion_time = time.perf_counter() - start_time
                    self._stats.total_conversions += 1
                    self._stats.cache_hits += 1  # Safe conversion is always "cached"
                    self._update_average_time(conversion_time)

                    return ConversionResult(
                        srgb_color=srgb_result,
                        original_color=color,
                        source_profile=source_profile,
                        rendering_intent=rendering_intent,
                        conversion_time=conversion_time,
                        cache_hit=True
                    )
                except Exception as e:
                    logger.warning(f"Safe LAB conversion failed: {e}")
                    # Fall through to normal profile loading

            # Check for known profile conversion
            from .known_profiles import is_known_profile, convert_to_srgb as known_convert_to_srgb
            if is_known_profile(source_profile):
                try:
                    # Convert using known profiles
                    import numpy as np
                    rgb_array = np.array([r, g, b])
                    srgb_array = known_convert_to_srgb(rgb_array, source_profile)
                    srgb_result = tuple(float(x) for x in srgb_array)

                    conversion_time = time.perf_counter() - start_time
                    self._stats.total_conversions += 1
                    self._stats.cache_hits += 1  # Known profile conversion is always "cached"
                    self._update_average_time(conversion_time)

                    return ConversionResult(
                        srgb_color=srgb_result,
                        original_color=color,
                        source_profile=source_profile,
                        rendering_intent=rendering_intent,
                        conversion_time=conversion_time,
                        cache_hit=True
                    )
                except Exception as e:
                    logger.warning(f"Known profile conversion failed for {source_profile}: {e}")
                    # Fall through to normal profile loading

            # Get transform
            transform, cache_hit = self._get_transform(source_profile, rendering_intent)

            # Apply transform using PIL Image
            from PIL import Image

            # Create a 1x1 pixel image for transformation
            img = Image.new('RGB', (1, 1), (r_255, g_255, b_255))
            transformed_img = ImageCms.applyTransform(img, transform)

            # Extract the transformed color from the pixel
            rgb_output = transformed_img.getpixel((0, 0))

            # Convert back to 0-1 range
            srgb_r = rgb_output[0] / 255.0
            srgb_g = rgb_output[1] / 255.0
            srgb_b = rgb_output[2] / 255.0

            conversion_time = time.perf_counter() - start_time

            # Update statistics
            self._stats.total_conversions += 1
            if cache_hit:
                self._stats.cache_hits += 1
            else:
                self._stats.cache_misses += 1
            self._update_average_time(conversion_time)

            return ConversionResult(
                srgb_color=(srgb_r, srgb_g, srgb_b),
                original_color=color,
                source_profile=source_profile,
                rendering_intent=rendering_intent,
                conversion_time=conversion_time,
                cache_hit=cache_hit
            )

        except Exception as e:
            self._stats.errors += 1
            if isinstance(e, ICCConversionError):
                raise
            else:
                raise ICCConversionError(f"Color conversion failed: {e}") from e

    def convert_multiple_to_srgb(self, colors: list[Tuple[float, ...]],
                                source_profile: str,
                                rendering_intent: RenderingIntent = RenderingIntent.PERCEPTUAL) -> list[ConversionResult]:
        """
        Convert multiple colors efficiently using cached transforms.

        Args:
            colors: List of color tuples to convert
            source_profile: Name of source color profile
            rendering_intent: Rendering intent for conversion

        Returns:
            List of ConversionResult objects
        """
        results = []

        for color in colors:
            try:
                result = self.convert_to_srgb(color, source_profile, rendering_intent)
                results.append(result)
            except ICCConversionError as e:
                logger.warning(f"Failed to convert color {color}: {e}")
                # Create fallback result (pass through as sRGB)
                fallback_result = ConversionResult(
                    srgb_color=(color[0], color[1], color[2]) if len(color) >= 3 else (0, 0, 0),
                    original_color=color,
                    source_profile=source_profile,
                    rendering_intent=rendering_intent,
                    conversion_time=0.0,
                    cache_hit=False
                )
                results.append(fallback_result)

        return results

    def _update_average_time(self, conversion_time: float) -> None:
        """Update running average of conversion times."""
        total = self._stats.total_conversions
        if total == 1:
            self._stats.average_conversion_time = conversion_time
        else:
            # Running average formula
            self._stats.average_conversion_time = (
                (self._stats.average_conversion_time * (total - 1) + conversion_time) / total
            )

    def get_stats(self) -> ConversionStats:
        """Get conversion statistics."""
        return self._stats

    def clear_cache(self) -> int:
        """
        Clear transform cache.

        Returns:
            Number of cached transforms removed
        """
        count = len(self._transform_cache)
        self._transform_cache.clear()
        logger.info(f"Cleared {count} cached transforms")
        return count

    def get_supported_profiles(self) -> list[str]:
        """
        Get list of supported profile names.

        Returns:
            List of profile names that can be used as source profiles
        """
        # Built-in profiles that are guaranteed to work
        supported = ['srgb', 'srgb-2014']

        # Add profiles with fallback behavior
        supported.extend(['lab', 'cielab'])

        # Add known profiles from the known_profiles module
        from .known_profiles import list_known_profiles
        supported.extend(list_known_profiles())

        # Add profiles from registry
        if self.profile_registry:
            registry_profiles = self.profile_registry.list_available_profiles()
            supported.extend(registry_profiles)

        return sorted(set(supported))

    def validate_profile(self, profile_name: str) -> bool:
        """
        Validate that a profile can be loaded and used.

        Args:
            profile_name: Name of profile to validate

        Returns:
            True if profile is valid and usable
        """
        try:
            source_profile = self._load_source_profile(profile_name)
            return source_profile is not None
        except Exception:
            return False

    def is_icc_available(self) -> bool:
        """Check if ICC functionality is available."""
        return ICC_AVAILABLE and self._srgb_profile is not None


# Convenience functions for simple use cases

def convert_color_to_srgb(color: Tuple[float, float, float],
                         source_profile: str = 'srgb',
                         rendering_intent: RenderingIntent = RenderingIntent.PERCEPTUAL,
                         converter: Optional[ICCConverter] = None) -> Tuple[float, float, float]:
    """
    Convert a single color to sRGB using default converter.

    Args:
        color: RGB color tuple in [0, 1] range
        source_profile: Source color profile name
        rendering_intent: Rendering intent for conversion
        converter: Optional converter instance (creates default if None)

    Returns:
        sRGB color tuple in [0, 1] range
    """
    if converter is None:
        converter = ICCConverter()

    result = converter.convert_to_srgb(color, source_profile, rendering_intent)
    return result.srgb_color


@lru_cache(maxsize=1)
def get_default_converter() -> ICCConverter:
    """Get cached default converter instance."""
    return ICCConverter()


def is_icc_conversion_available() -> bool:
    """Check if ICC conversion is available on this system."""
    return ICC_AVAILABLE