#!/usr/bin/env python3
"""
Color Profile Data Models

Core data structures for ICC color profile management in SVG2PPTX.
Provides immutable, validated data classes for color profile references
and profiled color values with type safety and comprehensive validation.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, Union
import re


class RenderingIntent(Enum):
    """
    ICC Rendering Intent for color conversion.

    Defines how out-of-gamut colors should be handled during
    color space conversions according to ICC specifications.
    """
    AUTO = "auto"
    PERCEPTUAL = "perceptual"
    RELATIVE_COLORIMETRIC = "relative-colorimetric"
    SATURATION = "saturation"
    ABSOLUTE_COLORIMETRIC = "absolute-colorimetric"

    @classmethod
    def from_string(cls, value: Optional[str]) -> 'RenderingIntent':
        """
        Parse rendering intent from string with normalization.

        Args:
            value: Intent string (case-insensitive, allows underscores/hyphens)

        Returns:
            RenderingIntent enum value, defaults to AUTO for invalid input
        """
        if not value:
            return cls.AUTO

        # Normalize: lowercase, convert underscores to hyphens
        normalized = value.strip().lower().replace('_', '-')

        # Map common variations
        intent_map = {
            'auto': cls.AUTO,
            'perceptual': cls.PERCEPTUAL,
            'relative-colorimetric': cls.RELATIVE_COLORIMETRIC,
            'relative': cls.RELATIVE_COLORIMETRIC,  # Common abbreviation
            'saturation': cls.SATURATION,
            'absolute-colorimetric': cls.ABSOLUTE_COLORIMETRIC,
            'absolute': cls.ABSOLUTE_COLORIMETRIC,  # Common abbreviation
        }

        return intent_map.get(normalized, cls.AUTO)


@dataclass(frozen=True)
class ColorProfileRef:
    """
    Reference to an ICC color profile.

    Immutable reference that can point to embedded profiles (data: URLs),
    local files, or remote resources (subject to security policy).

    Attributes:
        name: Profile identifier (required, non-empty)
        href: URI to profile resource (optional)
        local: Whether profile is locally available (affects loading strategy)
        rendering_intent: How to handle out-of-gamut colors
    """
    name: str
    href: Optional[str] = None
    local: bool = True
    rendering_intent: RenderingIntent = RenderingIntent.AUTO

    def __post_init__(self) -> None:
        """Validate profile reference after initialization."""
        if not self.name or not isinstance(self.name, str):
            raise ValueError(f"Profile name must be non-empty string, got: {self.name!r}")

        if not self.name.strip():
            raise ValueError("Profile name cannot be whitespace-only")

        # Validate name contains only safe characters (letters, numbers, hyphens, underscores)
        if not re.match(r'^[a-zA-Z0-9_-]+$', self.name.strip()):
            raise ValueError(f"Profile name contains invalid characters: {self.name!r}")

        if self.href is not None:
            if not isinstance(self.href, str):
                raise ValueError(f"Profile href must be string or None, got: {type(self.href)}")
            if not self.href.strip():
                raise ValueError("Profile href cannot be empty string (use None instead)")

    @property
    def is_data_url(self) -> bool:
        """Check if profile uses data: URL encoding."""
        return self.href is not None and self.href.startswith('data:')

    @property
    def is_remote(self) -> bool:
        """Check if profile requires remote loading."""
        return (self.href is not None and
                (self.href.startswith('http://') or self.href.startswith('https://')))

    @property
    def safe_name(self) -> str:
        """Get sanitized profile name for file system use."""
        return re.sub(r'[^a-zA-Z0-9_-]', '_', self.name.strip())


@dataclass(frozen=True)
class ProfiledColor:
    """
    Color value defined in a specific color profile space.

    Represents a color with explicit profile reference and channel values.
    Used for CSS Color 4 color(profile ...) syntax and SVG profiled colors.

    Attributes:
        profile: Profile name (must match registered profile)
        channels: Color channel values (typically RGB, but depends on profile)
        alpha: Opacity value (0.0 = transparent, 1.0 = opaque)
    """
    profile: str
    channels: Tuple[float, ...]
    alpha: float = 1.0

    def __post_init__(self) -> None:
        """Validate profiled color after initialization."""
        if not self.profile or not isinstance(self.profile, str):
            raise ValueError(f"Profile name must be non-empty string, got: {self.profile!r}")

        if not self.profile.strip():
            raise ValueError("Profile name cannot be whitespace-only")

        if not isinstance(self.channels, tuple):
            raise ValueError(f"Channels must be tuple, got: {type(self.channels)}")

        if len(self.channels) == 0:
            raise ValueError("Channels tuple cannot be empty")

        if len(self.channels) > 10:  # Reasonable upper limit
            raise ValueError(f"Too many channels ({len(self.channels)}), max 10 supported")

        # Validate all channels are numeric and in reasonable range
        for i, channel in enumerate(self.channels):
            if not isinstance(channel, (int, float)):
                raise ValueError(f"Channel {i} must be numeric, got: {type(channel)}")
            if not (-1000.0 <= channel <= 1000.0):  # Generous range for various color spaces
                raise ValueError(f"Channel {i} value {channel} outside reasonable range [-1000, 1000]")

        if not isinstance(self.alpha, (int, float)):
            raise ValueError(f"Alpha must be numeric, got: {type(self.alpha)}")

        if not (0.0 <= self.alpha <= 1.0):
            raise ValueError(f"Alpha must be in range [0.0, 1.0], got: {self.alpha}")

    @property
    def is_rgb(self) -> bool:
        """Check if this appears to be RGB color (3 channels)."""
        return len(self.channels) == 3

    @property
    def is_cmyk(self) -> bool:
        """Check if this appears to be CMYK color (4 channels)."""
        return len(self.channels) == 4

    @property
    def is_opaque(self) -> bool:
        """Check if color is fully opaque."""
        return self.alpha >= 1.0

    @property
    def is_transparent(self) -> bool:
        """Check if color is fully transparent."""
        return self.alpha <= 0.0

    def with_alpha(self, alpha: float) -> 'ProfiledColor':
        """
        Create new ProfiledColor with different alpha value.

        Args:
            alpha: New alpha value (0.0-1.0)

        Returns:
            New ProfiledColor instance with updated alpha
        """
        return ProfiledColor(
            profile=self.profile,
            channels=self.channels,
            alpha=alpha
        )

    def with_channels(self, channels: Tuple[float, ...]) -> 'ProfiledColor':
        """
        Create new ProfiledColor with different channel values.

        Args:
            channels: New channel values

        Returns:
            New ProfiledColor instance with updated channels
        """
        return ProfiledColor(
            profile=self.profile,
            channels=channels,
            alpha=self.alpha
        )


# Type aliases for convenience
ProfileReference = Union[str, ColorProfileRef]
ColorValue = Union[ProfiledColor, str, Tuple[float, ...]]


def normalize_profile_reference(ref: ProfileReference) -> ColorProfileRef:
    """
    Normalize profile reference to ColorProfileRef object.

    Args:
        ref: Profile reference (string name or ColorProfileRef)

    Returns:
        ColorProfileRef object

    Raises:
        ValueError: If reference is invalid
    """
    if isinstance(ref, str):
        return ColorProfileRef(name=ref)
    elif isinstance(ref, ColorProfileRef):
        return ref
    else:
        raise ValueError(f"Invalid profile reference type: {type(ref)}")


def validate_color_channels(channels: Tuple[float, ...], expected_count: Optional[int] = None) -> None:
    """
    Validate color channel values.

    Args:
        channels: Channel values to validate
        expected_count: Expected number of channels (optional)

    Raises:
        ValueError: If channels are invalid
    """
    if not isinstance(channels, tuple):
        raise ValueError(f"Channels must be tuple, got: {type(channels)}")

    if expected_count is not None and len(channels) != expected_count:
        raise ValueError(f"Expected {expected_count} channels, got {len(channels)}")

    for i, channel in enumerate(channels):
        if not isinstance(channel, (int, float)):
            raise ValueError(f"Channel {i} must be numeric, got: {type(channel)}")