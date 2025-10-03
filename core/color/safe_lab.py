#!/usr/bin/env python3
"""
Safe LAB Color Conversion Shim

Provides LAB/XYZ color space conversions with graceful fallbacks:
1. Uses LittleCMS (Pillow) when available for maximum accuracy
2. Falls back to pure NumPy implementation with Bradford CAT for compatibility

This ensures LAB color conversions work reliably across different environments
while maintaining high color accuracy when possible.
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)

# --- Constants (D50 white point and Bradford Chromatic Adaptation Transform) ---
D50 = np.array([0.96422, 1.00000, 0.82521])  # PCS white point
D65 = np.array([0.95047, 1.00000, 1.08883])  # D65 white point

# Bradford transformation matrices
M_BRADFORD = np.array([[ 0.8951,  0.2664, -0.1614],
                       [-0.7502,  1.7135,  0.0367],
                       [ 0.0389, -0.0685,  1.0296]])
M_BRADFORD_INV = np.linalg.inv(M_BRADFORD)

# sRGB transformation matrices (D65-based)
M_RGB_TO_XYZ = np.array([[0.4124564, 0.3575761, 0.1804375],
                         [0.2126729, 0.7151522, 0.0721750],
                         [0.0193339, 0.1191920, 0.9503041]])
M_XYZ_TO_RGB = np.linalg.inv(M_RGB_TO_XYZ)


def _f(t):
    """LAB conversion function."""
    eps = (6/29)**3
    k   = (29/3)**2 / 3
    return np.where(t > eps, np.cbrt(t), k*t + 4/29)


def _finv(t):
    """Inverse LAB conversion function."""
    th = 6/29
    return np.where(t > th, t**3, 3*th**2*(t - 4/29))


def xyz_to_lab(xyz):
    """
    Convert XYZ (D50) to LAB color space.

    Args:
        xyz: XYZ values in D50 white point, shape (..., 3)

    Returns:
        LAB values, shape (..., 3)
    """
    xyz = np.asarray(xyz)
    xr = xyz[..., 0] / D50[0]
    yr = xyz[..., 1] / D50[1]
    zr = xyz[..., 2] / D50[2]

    fx, fy, fz = _f(xr), _f(yr), _f(zr)

    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)

    return np.stack([L, a, b], axis=-1)


def lab_to_xyz(lab):
    """
    Convert LAB to XYZ (D50) color space.

    Args:
        lab: LAB values, shape (..., 3)

    Returns:
        XYZ values in D50 white point, shape (..., 3)
    """
    lab = np.asarray(lab)
    L = lab[..., 0]
    a = lab[..., 1]
    b = lab[..., 2]

    fy = (L + 16) / 116
    fx = fy + (a / 500)
    fz = fy - (b / 200)

    x = D50[0] * _finv(fx)
    y = D50[1] * _finv(fy)
    z = D50[2] * _finv(fz)

    return np.stack([x, y, z], axis=-1)


def _srgb_gamma_inv(c):
    """sRGB gamma removal (linearization)."""
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _srgb_gamma_fwd(c):
    """sRGB gamma application (encoding)."""
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * (np.clip(c, 0, None) ** (1/2.4)) - 0.055)


def srgb_to_xyz(rgb):
    """
    Convert sRGB to XYZ (D50) color space with Bradford adaptation.

    Args:
        rgb: sRGB values in [0,1] range, shape (..., 3)

    Returns:
        XYZ values in D50 white point, shape (..., 3)
    """
    rgb = np.asarray(rgb)

    # Remove sRGB gamma
    lin = _srgb_gamma_inv(rgb)

    # Convert to XYZ (D65)
    xyz_d65 = lin @ M_RGB_TO_XYZ.T

    # Adapt D65 -> D50 using Bradford CAT
    cone_src = M_BRADFORD @ D65
    cone_dst = M_BRADFORD @ D50
    Ma = M_BRADFORD_INV @ np.diag(cone_dst / cone_src) @ M_BRADFORD

    return xyz_d65 @ Ma.T


def xyz_to_srgb(xyz_d50):
    """
    Convert XYZ (D50) to sRGB color space with Bradford adaptation.

    Args:
        xyz_d50: XYZ values in D50 white point, shape (..., 3)

    Returns:
        sRGB values in [0,1] range, shape (..., 3)
    """
    xyz_d50 = np.asarray(xyz_d50)

    # Adapt D50 -> D65 using Bradford CAT
    cone_src = M_BRADFORD @ D50
    cone_dst = M_BRADFORD @ D65
    Ma = M_BRADFORD_INV @ np.diag(cone_dst / cone_src) @ M_BRADFORD

    xyz_d65 = xyz_d50 @ Ma.T

    # Convert to linear RGB
    lin = xyz_d65 @ M_XYZ_TO_RGB.T

    # Apply sRGB gamma
    return _srgb_gamma_fwd(lin)


def lab_from_srgb(rgb01):
    """
    Convert sRGB to LAB via XYZ using NumPy implementation.

    Args:
        rgb01: sRGB values in [0,1] range

    Returns:
        LAB values
    """
    return xyz_to_lab(srgb_to_xyz(rgb01))


def srgb_from_lab(lab):
    """
    Convert LAB to sRGB via XYZ using NumPy implementation.

    Args:
        lab: LAB values

    Returns:
        sRGB values in [0,1] range, clipped
    """
    return np.clip(xyz_to_srgb(lab_to_xyz(lab)), 0, 1)


def try_lcms_lab_to_srgb(lab_img):
    """
    Best-effort LAB to sRGB conversion via Pillow/LittleCMS.

    Args:
        lab_img: PIL Image in LAB mode

    Returns:
        PIL Image in RGB mode, or None if conversion fails
    """
    try:
        from PIL import ImageCms, Image

        # Create profiles
        lab_profile = ImageCms.createProfile("LAB")
        srgb_profile = ImageCms.createProfile("sRGB")

        # Create transform
        transform = ImageCms.buildTransform(
            lab_profile,
            srgb_profile,
            "LAB",
            "RGB",
            renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC
        )

        # Apply transform
        return ImageCms.applyTransform(lab_img, transform)

    except Exception as e:
        logger.debug(f"LittleCMS LAB conversion failed: {e}")
        return None


def try_lcms_srgb_to_lab(rgb_img):
    """
    Best-effort sRGB to LAB conversion via Pillow/LittleCMS.

    Args:
        rgb_img: PIL Image in RGB mode

    Returns:
        PIL Image in LAB mode, or None if conversion fails
    """
    try:
        from PIL import ImageCms, Image

        # Create profiles
        srgb_profile = ImageCms.createProfile("sRGB")
        lab_profile = ImageCms.createProfile("LAB")

        # Create transform
        transform = ImageCms.buildTransform(
            srgb_profile,
            lab_profile,
            "RGB",
            "LAB",
            renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC
        )

        # Apply transform
        return ImageCms.applyTransform(rgb_img, transform)

    except Exception as e:
        logger.debug(f"LittleCMS LAB conversion failed: {e}")
        return None


def convert_srgb_to_lab_safe(rgb_tuple):
    """
    Safe sRGB to LAB conversion with fallback.

    First tries LittleCMS for maximum accuracy, falls back to NumPy implementation.

    Args:
        rgb_tuple: RGB values in [0,1] range as tuple (r, g, b)

    Returns:
        LAB values as tuple (L, a, b)
    """
    try:
        # Try LittleCMS first
        from PIL import Image

        # Convert to 8-bit for PIL
        r_255 = max(0, min(255, int(rgb_tuple[0] * 255)))
        g_255 = max(0, min(255, int(rgb_tuple[1] * 255)))
        b_255 = max(0, min(255, int(rgb_tuple[2] * 255)))

        # Create 1x1 image
        img = Image.new('RGB', (1, 1), (r_255, g_255, b_255))

        # Try LittleCMS conversion
        lab_img = try_lcms_srgb_to_lab(img)
        if lab_img is not None:
            # Extract LAB values and convert to proper range
            lab_pixel = lab_img.getpixel((0, 0))
            # PIL LAB uses different encoding: L[0,100], a[-128,127], b[-128,127]
            L = lab_pixel[0] * 100.0 / 255.0  # Scale L to [0,100]
            a = (lab_pixel[1] - 128.0) * 255.0 / 255.0  # Scale a to [-128,127]
            b = (lab_pixel[2] - 128.0) * 255.0 / 255.0  # Scale b to [-128,127]
            return (L, a, b)

    except Exception as e:
        logger.debug(f"LittleCMS conversion failed, using NumPy fallback: {e}")

    # Fall back to NumPy implementation
    rgb_array = np.array([[rgb_tuple]])  # Shape (1, 1, 3)
    lab_array = lab_from_srgb(rgb_array)
    lab_result = lab_array[0, 0]  # Extract single pixel

    return (float(lab_result[0]), float(lab_result[1]), float(lab_result[2]))


def convert_lab_to_srgb_safe(lab_tuple):
    """
    Safe LAB to sRGB conversion with fallback.

    First tries LittleCMS for maximum accuracy, falls back to NumPy implementation.

    Args:
        lab_tuple: LAB values as tuple (L, a, b)

    Returns:
        sRGB values in [0,1] range as tuple (r, g, b)
    """
    try:
        # Try LittleCMS first
        from PIL import Image

        # Convert LAB to PIL encoding: L[0,255], a[0,255], b[0,255]
        L_255 = max(0, min(255, int(lab_tuple[0] * 255.0 / 100.0)))  # Scale L from [0,100] to [0,255]
        a_255 = max(0, min(255, int(lab_tuple[1] + 128.0)))  # Scale a from [-128,127] to [0,255]
        b_255 = max(0, min(255, int(lab_tuple[2] + 128.0)))  # Scale b from [-128,127] to [0,255]

        # Create 1x1 LAB image
        img = Image.new('LAB', (1, 1), (L_255, a_255, b_255))

        # Try LittleCMS conversion
        rgb_img = try_lcms_lab_to_srgb(img)
        if rgb_img is not None:
            rgb_pixel = rgb_img.getpixel((0, 0))
            return (rgb_pixel[0] / 255.0, rgb_pixel[1] / 255.0, rgb_pixel[2] / 255.0)

    except Exception as e:
        logger.debug(f"LittleCMS conversion failed, using NumPy fallback: {e}")

    # Fall back to NumPy implementation
    lab_array = np.array([[lab_tuple]])  # Shape (1, 1, 3)
    rgb_array = srgb_from_lab(lab_array)
    rgb_result = rgb_array[0, 0]  # Extract single pixel

    return (float(rgb_result[0]), float(rgb_result[1]), float(rgb_result[2]))


def is_lab_conversion_available():
    """
    Check if LAB conversion is available (either LittleCMS or NumPy fallback).

    Returns:
        True (always available due to NumPy fallback)
    """
    return True


def is_lcms_lab_available():
    """
    Check if LittleCMS LAB conversion is available.

    Returns:
        True if LittleCMS LAB support is working, False otherwise
    """
    try:
        from PIL import ImageCms, Image

        # Test basic LAB transform creation
        srgb_profile = ImageCms.createProfile("sRGB")
        lab_profile = ImageCms.createProfile("LAB")

        # Try to build a transform
        transform = ImageCms.buildTransform(
            srgb_profile,
            lab_profile,
            "RGB",
            "LAB"
        )

        return True

    except Exception:
        return False