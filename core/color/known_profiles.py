#!/usr/bin/env python3
"""
Known Color Profiles

Provides built-in support for standard color spaces without external ICC files.
Implements conversion matrices and functions for common wide-gamut profiles
with high accuracy and performance optimization.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List
import logging

from .profile_model import RenderingIntent

logger = logging.getLogger(__name__)

# Standard illuminants (CIE 1931 2° observer)
ILLUMINANTS = {
    'D50': np.array([0.96422, 1.00000, 0.82521]),
    'D65': np.array([0.95047, 1.00000, 1.08883]),
}

# Bradford chromatic adaptation transform matrices
M_BRADFORD = np.array([[ 0.8951,  0.2664, -0.1614],
                       [-0.7502,  1.7135,  0.0367],
                       [ 0.0389, -0.0685,  1.0296]])
M_BRADFORD_INV = np.linalg.inv(M_BRADFORD)


@dataclass
class KnownProfile:
    """
    Definition of a known color profile with conversion matrices.

    Attributes:
        name: Profile name
        description: Human-readable description
        white_point: White point illuminant name
        primaries: RGB primaries as (rx, ry, gx, gy, bx, by)
        gamma: Gamma function type or value
        rgb_to_xyz: RGB to XYZ conversion matrix
        xyz_to_rgb: XYZ to RGB conversion matrix
        transfer_functions: Gamma encoding/decoding functions
    """
    name: str
    description: str
    white_point: str
    primaries: Tuple[float, float, float, float, float, float]  # rx, ry, gx, gy, bx, by
    gamma: float | str
    rgb_to_xyz: np.ndarray
    xyz_to_rgb: np.ndarray
    transfer_functions: Tuple[callable, callable]  # encode, decode


def _srgb_encode(linear_rgb: np.ndarray) -> np.ndarray:
    """sRGB gamma encoding function."""
    return np.where(linear_rgb <= 0.0031308,
                   12.92 * linear_rgb,
                   1.055 * np.power(np.clip(linear_rgb, 0, None), 1/2.4) - 0.055)


def _srgb_decode(encoded_rgb: np.ndarray) -> np.ndarray:
    """sRGB gamma decoding function."""
    return np.where(encoded_rgb <= 0.04045,
                   encoded_rgb / 12.92,
                   np.power((encoded_rgb + 0.055) / 1.055, 2.4))


def _gamma_encode(gamma: float):
    """Create gamma encoding function."""
    def encode(linear_rgb: np.ndarray) -> np.ndarray:
        return np.power(np.clip(linear_rgb, 0, None), 1/gamma)
    return encode


def _gamma_decode(gamma: float):
    """Create gamma decoding function."""
    def decode(encoded_rgb: np.ndarray) -> np.ndarray:
        return np.power(np.clip(encoded_rgb, 0, None), gamma)
    return decode


def _compute_rgb_to_xyz_matrix(primaries: Tuple[float, ...], white_point: str) -> np.ndarray:
    """
    Compute RGB to XYZ transformation matrix from primaries and white point.

    Args:
        primaries: (rx, ry, gx, gy, bx, by) chromaticity coordinates
        white_point: White point illuminant name

    Returns:
        3x3 RGB to XYZ transformation matrix
    """
    rx, ry, gx, gy, bx, by = primaries

    # Convert chromaticity to XYZ (assuming Y=1)
    rz = 1 - rx - ry
    gz = 1 - gx - gy
    bz = 1 - bx - by

    # Primary matrix
    primaries_matrix = np.array([
        [rx/ry, gx/gy, bx/by],
        [1.0,   1.0,   1.0  ],
        [rz/ry, gz/gy, bz/by]
    ])

    # White point
    wp = ILLUMINANTS[white_point]

    # Solve for scaling factors
    scaling = np.linalg.solve(primaries_matrix, wp)

    # Apply scaling to get final matrix
    rgb_to_xyz = primaries_matrix * scaling

    return rgb_to_xyz


# Define known color profiles
def _create_known_profiles() -> Dict[str, KnownProfile]:
    """Create dictionary of known color profiles."""
    profiles = {}

    # sRGB (reference)
    srgb_primaries = (0.6400, 0.3300, 0.3000, 0.6000, 0.1500, 0.0600)
    srgb_rgb_to_xyz = _compute_rgb_to_xyz_matrix(srgb_primaries, 'D65')
    srgb_xyz_to_rgb = np.linalg.inv(srgb_rgb_to_xyz)

    profiles['srgb'] = KnownProfile(
        name='srgb',
        description='sRGB IEC61966-2.1',
        white_point='D65',
        primaries=srgb_primaries,
        gamma='srgb',
        rgb_to_xyz=srgb_rgb_to_xyz,
        xyz_to_rgb=srgb_xyz_to_rgb,
        transfer_functions=(_srgb_encode, _srgb_decode)
    )

    # Display P3
    p3_primaries = (0.6800, 0.3200, 0.2650, 0.6900, 0.1500, 0.0600)
    p3_rgb_to_xyz = _compute_rgb_to_xyz_matrix(p3_primaries, 'D65')
    p3_xyz_to_rgb = np.linalg.inv(p3_rgb_to_xyz)

    profiles['display-p3'] = KnownProfile(
        name='display-p3',
        description='Display P3',
        white_point='D65',
        primaries=p3_primaries,
        gamma='srgb',  # Display P3 uses sRGB transfer function
        rgb_to_xyz=p3_rgb_to_xyz,
        xyz_to_rgb=p3_xyz_to_rgb,
        transfer_functions=(_srgb_encode, _srgb_decode)
    )

    # Rec2020 (ITU-R BT.2020)
    rec2020_primaries = (0.7080, 0.2920, 0.1700, 0.7970, 0.1310, 0.0460)
    rec2020_rgb_to_xyz = _compute_rgb_to_xyz_matrix(rec2020_primaries, 'D65')
    rec2020_xyz_to_rgb = np.linalg.inv(rec2020_rgb_to_xyz)

    profiles['rec2020'] = KnownProfile(
        name='rec2020',
        description='ITU-R BT.2020',
        white_point='D65',
        primaries=rec2020_primaries,
        gamma=2.4,
        rgb_to_xyz=rec2020_rgb_to_xyz,
        xyz_to_rgb=rec2020_xyz_to_rgb,
        transfer_functions=(_gamma_encode(2.4), _gamma_decode(2.4))
    )

    # Adobe RGB (1998)
    adobe_primaries = (0.6400, 0.3300, 0.2100, 0.7100, 0.1500, 0.0600)
    adobe_rgb_to_xyz = _compute_rgb_to_xyz_matrix(adobe_primaries, 'D65')
    adobe_xyz_to_rgb = np.linalg.inv(adobe_rgb_to_xyz)

    profiles['adobe-rgb'] = KnownProfile(
        name='adobe-rgb',
        description='Adobe RGB (1998)',
        white_point='D65',
        primaries=adobe_primaries,
        gamma=2.2,
        rgb_to_xyz=adobe_rgb_to_xyz,
        xyz_to_rgb=adobe_xyz_to_rgb,
        transfer_functions=(_gamma_encode(2.2), _gamma_decode(2.2))
    )

    # ProPhoto RGB
    prophoto_primaries = (0.7347, 0.2653, 0.1596, 0.8404, 0.0366, 0.0001)
    prophoto_rgb_to_xyz = _compute_rgb_to_xyz_matrix(prophoto_primaries, 'D50')
    prophoto_xyz_to_rgb = np.linalg.inv(prophoto_rgb_to_xyz)

    profiles['prophoto-rgb'] = KnownProfile(
        name='prophoto-rgb',
        description='ProPhoto RGB',
        white_point='D50',
        primaries=prophoto_primaries,
        gamma=1.8,
        rgb_to_xyz=prophoto_rgb_to_xyz,
        xyz_to_rgb=prophoto_xyz_to_rgb,
        transfer_functions=(_gamma_encode(1.8), _gamma_decode(1.8))
    )

    return profiles


# Global profiles registry
KNOWN_PROFILES = _create_known_profiles()


def get_known_profile(name: str) -> Optional[KnownProfile]:
    """
    Get known profile by name.

    Args:
        name: Profile name (case-insensitive)

    Returns:
        KnownProfile if found, None otherwise
    """
    if not name:
        return None

    # Normalize name: lowercase, replace underscores/spaces with dashes
    normalized_name = name.lower().replace('_', '-').replace(' ', '-')

    # Try direct lookup first
    profile = KNOWN_PROFILES.get(normalized_name)
    if profile:
        return profile

    # Try without separators for names like "rec2020"
    compact_name = normalized_name.replace('-', '')
    profile = KNOWN_PROFILES.get(compact_name)
    if profile:
        return profile

    # Try common variations
    name_variations = {
        'rec-2020': 'rec2020',
        'bt-2020': 'rec2020',
        'bt2020': 'rec2020',
        'adobe-rgb': 'adobe-rgb',
        'adobergb': 'adobe-rgb',
        'prophoto-rgb': 'prophoto-rgb',
        'prophoto': 'prophoto-rgb',
        'romm-rgb': 'prophoto-rgb',
        'display-p3': 'display-p3',
        'displayp3': 'display-p3',
        'p3': 'display-p3',
    }

    canonical_name = name_variations.get(normalized_name)
    if canonical_name:
        return KNOWN_PROFILES.get(canonical_name)

    return None


def list_known_profiles() -> List[str]:
    """
    Get list of available known profile names.

    Returns:
        List of profile names
    """
    return list(KNOWN_PROFILES.keys())


def is_known_profile(name: str) -> bool:
    """
    Check if profile is a known built-in profile.

    Args:
        name: Profile name

    Returns:
        True if profile is known, False otherwise
    """
    return get_known_profile(name) is not None


def chromatic_adaptation(xyz: np.ndarray, src_white: str, dst_white: str) -> np.ndarray:
    """
    Perform chromatic adaptation using Bradford transform.

    Args:
        xyz: XYZ values to adapt
        src_white: Source white point name
        dst_white: Destination white point name

    Returns:
        Adapted XYZ values
    """
    if src_white == dst_white:
        return xyz  # No adaptation needed

    src_wp = ILLUMINANTS[src_white]
    dst_wp = ILLUMINANTS[dst_white]

    # Convert white points to cone response domain
    cone_src = M_BRADFORD @ src_wp
    cone_dst = M_BRADFORD @ dst_wp

    # Compute adaptation matrix
    adaptation_matrix = M_BRADFORD_INV @ np.diag(cone_dst / cone_src) @ M_BRADFORD

    # Apply adaptation
    if xyz.ndim == 1:
        return adaptation_matrix @ xyz
    else:
        return xyz @ adaptation_matrix.T


def convert_between_profiles(rgb: np.ndarray,
                           src_profile: str,
                           dst_profile: str = 'srgb',
                           rendering_intent: RenderingIntent = RenderingIntent.PERCEPTUAL) -> np.ndarray:
    """
    Convert RGB values between known color profiles.

    Args:
        rgb: RGB values in [0,1] range
        src_profile: Source profile name
        dst_profile: Destination profile name (default: sRGB)
        rendering_intent: Rendering intent (currently ignored for simplicity)

    Returns:
        Converted RGB values in [0,1] range

    Raises:
        ValueError: If profile is not known
    """
    src = get_known_profile(src_profile)
    dst = get_known_profile(dst_profile)

    if src is None:
        raise ValueError(f"Unknown source profile: {src_profile}")
    if dst is None:
        raise ValueError(f"Unknown destination profile: {dst_profile}")

    # Ensure input is numpy array
    rgb = np.asarray(rgb)

    # Step 1: Decode gamma to linear RGB
    linear_rgb = src.transfer_functions[1](rgb)

    # Step 2: Convert to XYZ
    xyz = linear_rgb @ src.rgb_to_xyz.T

    # Step 3: Chromatic adaptation if needed
    if src.white_point != dst.white_point:
        xyz = chromatic_adaptation(xyz, src.white_point, dst.white_point)

    # Step 4: Convert to destination RGB
    dst_linear_rgb = xyz @ dst.xyz_to_rgb.T

    # Step 5: Apply destination gamma
    dst_rgb = dst.transfer_functions[0](dst_linear_rgb)

    # Clip to valid range
    return np.clip(dst_rgb, 0, 1)


def convert_to_srgb(rgb: np.ndarray, src_profile: str) -> np.ndarray:
    """
    Convert RGB values from source profile to sRGB.

    Args:
        rgb: RGB values in [0,1] range
        src_profile: Source profile name

    Returns:
        sRGB values in [0,1] range
    """
    return convert_between_profiles(rgb, src_profile, 'srgb')


def get_profile_gamut_volume(profile_name: str) -> Optional[float]:
    """
    Get relative gamut volume compared to sRGB.

    Args:
        profile_name: Profile name

    Returns:
        Gamut volume ratio (sRGB = 1.0), or None if unknown
    """
    # Approximate gamut volumes relative to sRGB
    # These are rough estimates for comparison purposes
    gamut_volumes = {
        'srgb': 1.0,
        'display-p3': 1.25,
        'adobe-rgb': 1.35,
        'rec2020': 1.76,
        'prophoto-rgb': 2.10,
    }

    normalized_name = profile_name.lower().replace('_', '-')
    return gamut_volumes.get(normalized_name)


def get_profile_info(profile_name: str) -> Optional[Dict[str, any]]:
    """
    Get detailed information about a known profile.

    Args:
        profile_name: Profile name

    Returns:
        Dictionary with profile information, or None if unknown
    """
    profile = get_known_profile(profile_name)
    if profile is None:
        return None

    gamut_volume = get_profile_gamut_volume(profile_name)

    return {
        'name': profile.name,
        'description': profile.description,
        'white_point': profile.white_point,
        'primaries': profile.primaries,
        'gamma': profile.gamma,
        'gamut_volume': gamut_volume,
        'is_wide_gamut': gamut_volume > 1.1 if gamut_volume else False,
    }


def validate_profile_conversion(src_profile: str, dst_profile: str) -> bool:
    """
    Validate that conversion between profiles is possible.

    Args:
        src_profile: Source profile name
        dst_profile: Destination profile name

    Returns:
        True if conversion is possible, False otherwise
    """
    return (is_known_profile(src_profile) and
            is_known_profile(dst_profile))


def get_optimal_conversion_path(src_profile: str, dst_profile: str) -> List[str]:
    """
    Get optimal conversion path between profiles.

    For known profiles, direct conversion is always optimal.

    Args:
        src_profile: Source profile name
        dst_profile: Destination profile name

    Returns:
        List of profile names in conversion path
    """
    if not validate_profile_conversion(src_profile, dst_profile):
        return []

    # Direct conversion is optimal for known profiles
    return [src_profile, dst_profile]