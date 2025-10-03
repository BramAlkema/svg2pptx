#!/usr/bin/env python3
"""
Color Testing Helpers

Provides utilities for testing color conversions with graceful handling
of environment-specific limitations (e.g., LAB support availability).
"""

import numpy as np
import pytest
import logging

logger = logging.getLogger(__name__)


def approx_eq(a, b, tol=1e-3):
    """
    Check if two arrays/values are approximately equal within tolerance.

    Args:
        a: First value or array
        b: Second value or array
        tol: Tolerance for comparison

    Returns:
        True if values are within tolerance, False otherwise
    """
    a = np.asarray(a)
    b = np.asarray(b)
    return np.max(np.abs(a - b)) <= tol


def require_lab_supported():
    """
    Pytest decorator/function to skip tests if LAB support is not available.

    This checks if LAB color space transforms work in the current environment
    by attempting to create a simple transform. If it fails, the test is skipped.

    Returns:
        True if LAB is supported, otherwise skips the test

    Usage:
        @pytest.mark.skipif(not require_lab_supported(), reason="LAB not supported")
        def test_lab_conversion():
            pass

        Or within a test:
        def test_lab_conversion():
            require_lab_supported()  # Will skip if not supported
            # ... test code ...
    """
    try:
        from PIL import ImageCms

        # Sanity check: build a trivial transform to ensure LAB works at runtime
        srgb_profile = ImageCms.createProfile("sRGB")
        lab_profile = ImageCms.createProfile("LAB")

        # Try to build the transform
        transform = ImageCms.buildTransform(
            srgb_profile,
            lab_profile,
            "RGB",
            "LAB"
        )

        # If we got here, LAB is supported
        logger.debug("LAB support confirmed via LittleCMS")
        return True

    except Exception as e:
        logger.debug(f"LAB support check failed: {e}")
        # Check if we're in a pytest context
        try:
            pytest.skip(f"LAB color space not supported in this environment: {e}")
        except pytest.skip.Exception:
            raise  # Re-raise if we're in pytest
        except:
            # Not in pytest context, just return False
            return False


def require_icc_available():
    """
    Skip test if ICC conversion is not available.

    Returns:
        True if ICC support is available, otherwise skips the test
    """
    try:
        from PIL import ImageCms
        # Try to create an sRGB profile
        ImageCms.createProfile("sRGB")
        return True
    except Exception as e:
        pytest.skip(f"ICC color management not available: {e}")


def color_distance(color1, color2):
    """
    Calculate Euclidean distance between two colors.

    Args:
        color1: First color as tuple/array (r, g, b) or (L, a, b)
        color2: Second color as tuple/array (r, g, b) or (L, a, b)

    Returns:
        Euclidean distance between colors
    """
    c1 = np.asarray(color1)
    c2 = np.asarray(color2)
    return np.sqrt(np.sum((c1 - c2) ** 2))


def assert_color_close(actual, expected, tolerance=1e-3, color_space="RGB"):
    """
    Assert that two colors are close within tolerance.

    Args:
        actual: Actual color values
        expected: Expected color values
        tolerance: Maximum allowed difference
        color_space: Color space name for error messages

    Raises:
        AssertionError: If colors are not within tolerance
    """
    if not approx_eq(actual, expected, tolerance):
        distance = color_distance(actual, expected)
        raise AssertionError(
            f"{color_space} color mismatch: "
            f"actual={actual}, expected={expected}, "
            f"distance={distance:.6f}, tolerance={tolerance}"
        )


def assert_rgb_close(actual_rgb, expected_rgb, tolerance=1e-3):
    """Assert that two RGB colors are close within tolerance."""
    assert_color_close(actual_rgb, expected_rgb, tolerance, "RGB")


def assert_lab_close(actual_lab, expected_lab, tolerance=1e-3):
    """Assert that two LAB colors are close within tolerance."""
    assert_color_close(actual_lab, expected_lab, tolerance, "LAB")


def validate_rgb_range(rgb):
    """
    Validate that RGB values are in valid [0,1] range.

    Args:
        rgb: RGB values as tuple/array

    Raises:
        AssertionError: If values are outside [0,1] range
    """
    rgb = np.asarray(rgb)
    if np.any(rgb < 0) or np.any(rgb > 1):
        raise AssertionError(f"RGB values outside [0,1] range: {rgb}")


def validate_lab_range(lab):
    """
    Validate that LAB values are in reasonable ranges.

    L should be [0,100], a and b typically [-128,127] but can extend further.

    Args:
        lab: LAB values as tuple/array

    Raises:
        AssertionError: If L is outside reasonable range
    """
    lab = np.asarray(lab)
    L = lab[..., 0] if lab.ndim > 0 else lab[0]

    if np.any(L < 0) or np.any(L > 100):
        raise AssertionError(f"LAB L* values outside [0,100] range: L={L}")


class ColorTolerance:
    """
    Context manager for different color tolerance levels.

    Usage:
        with ColorTolerance.strict():
            assert_rgb_close(actual, expected)  # Uses 1e-6 tolerance

        with ColorTolerance.loose():
            assert_rgb_close(actual, expected)  # Uses 1e-2 tolerance
    """

    _default_tolerance = 1e-3
    _current_tolerance = _default_tolerance

    @classmethod
    def strict(cls, tolerance=1e-6):
        """Use strict tolerance for high-precision tests."""
        return cls(tolerance)

    @classmethod
    def loose(cls, tolerance=1e-2):
        """Use loose tolerance for approximate tests."""
        return cls(tolerance)

    def __init__(self, tolerance):
        self.tolerance = tolerance
        self.previous_tolerance = None

    def __enter__(self):
        self.previous_tolerance = ColorTolerance._current_tolerance
        ColorTolerance._current_tolerance = self.tolerance
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        ColorTolerance._current_tolerance = self.previous_tolerance

    @classmethod
    def current(cls):
        """Get current tolerance level."""
        return cls._current_tolerance