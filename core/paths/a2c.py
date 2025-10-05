#!/usr/bin/env python3
"""
Arc to Cubic Bezier Conversion (a2c algorithm)

This module implements the industry-standard a2c algorithm for converting SVG
elliptical arcs to cubic Bezier curves, based on the fontello/svgpath implementation.

The algorithm follows the SVG specification (Appendix F) for converting from
endpoint parameterization to center parameterization, then generates cubic
Bezier curve approximations.

References:
- SVG 1.1 Specification, Appendix F: Elliptical arc implementation notes
- fontello/svgpath a2c.js implementation
- "Drawing an elliptical arc using polylines, quadratic or cubic Bézier curves"
  by L. Maisonobe
"""

import logging
import math
from typing import List, Tuple

logger = logging.getLogger(__name__)


class ArcTooBigError(ValueError):
    """Raised when arc parameters result in an arc that is too large to process."""
    pass


class InvalidArcParametersError(ValueError):
    """Raised when arc parameters are mathematically invalid."""
    pass


def arc_to_cubic_bezier(start_x: float, start_y: float, rx: float, ry: float,
                       rotation: float, large_arc_flag: bool, sweep_flag: bool,
                       end_x: float, end_y: float, max_segment_angle: float = 90.0) -> list[tuple[float, float, float, float, float, float, float, float]]:
    """
    Convert SVG elliptical arc to cubic Bézier curve segments.

    This is the main a2c (arc-to-cubic) function that implements the industry-standard
    algorithm used by fontello/svgpath and other SVG processing libraries.

    Args:
        start_x, start_y: Arc start point coordinates
        rx, ry: Arc radii (semi-major and semi-minor axes)
        rotation: Rotation angle in degrees
        large_arc_flag: Large arc flag (True or False)
        sweep_flag: Sweep direction flag (True or False)
        end_x, end_y: Arc end point coordinates
        max_segment_angle: Maximum angle per segment in degrees (default: 90.0)

    Returns:
        List of cubic Bézier curve segments, each as (start_x, start_y, cp1_x, cp1_y, cp2_x, cp2_y, end_x, end_y)

    Note:
        This function handles all the complexity of arc-to-Bézier conversion:
        - Endpoint to center parameterization
        - Arc segmentation for large arcs (>90°)
        - Proper handling of degenerate cases
    """
    try:
        # Handle degenerate cases
        if abs(start_x - end_x) < 1e-10 and abs(start_y - end_y) < 1e-10:
            return []  # Zero-length arc

        if abs(rx) < 1e-10 or abs(ry) < 1e-10:
            # Degenerate arc becomes a line
            return [(start_x, start_y, end_x, end_y, end_x, end_y, end_x, end_y)]

        # Ensure radii are positive
        rx = abs(rx)
        ry = abs(ry)

        # Convert rotation angle to radians
        phi_rad = math.radians(rotation % 360)
        cos_phi = math.cos(phi_rad)
        sin_phi = math.sin(phi_rad)

        # Step 1: Compute (x1', y1') - SVG spec F.6.5.1
        dx = (start_x - end_x) / 2.0
        dy = (start_y - end_y) / 2.0
        x1_prime = cos_phi * dx + sin_phi * dy
        y1_prime = -sin_phi * dx + cos_phi * dy

        # Step 2: Ensure radii are large enough - SVG spec F.6.6.2
        lambda_coeff = (x1_prime * x1_prime) / (rx * rx) + (y1_prime * y1_prime) / (ry * ry)
        if lambda_coeff > 1:
            sqrt_lambda = math.sqrt(lambda_coeff)
            rx *= sqrt_lambda
            ry *= sqrt_lambda

        # Step 3: Compute (cx', cy') - SVG spec F.6.5.2
        sign = -1 if large_arc_flag == sweep_flag else 1

        rx_sq = rx * rx
        ry_sq = ry * ry
        x1_prime_sq = x1_prime * x1_prime
        y1_prime_sq = y1_prime * y1_prime

        # Compute the discriminant
        discriminant = (rx_sq * ry_sq - rx_sq * y1_prime_sq - ry_sq * x1_prime_sq) / (rx_sq * y1_prime_sq + ry_sq * x1_prime_sq)
        discriminant = max(0, discriminant)  # Ensure non-negative

        coeff = sign * math.sqrt(discriminant)
        cx_prime = coeff * (rx * y1_prime / ry)
        cy_prime = coeff * -(ry * x1_prime / rx)

        # Step 4: Compute (cx, cy) - SVG spec F.6.5.3
        cx = cos_phi * cx_prime - sin_phi * cy_prime + (start_x + end_x) / 2.0
        cy = sin_phi * cx_prime + cos_phi * cy_prime + (start_y + end_y) / 2.0

        # Step 5: Compute angles - SVG spec F.6.5.4-6
        start_angle = compute_angle((x1_prime - cx_prime) / rx, (y1_prime - cy_prime) / ry)
        end_angle = compute_angle((-x1_prime - cx_prime) / rx, (-y1_prime - cy_prime) / ry)

        # Calculate sweep angle
        sweep_angle = end_angle - start_angle

        # Adjust sweep angle based on sweep direction
        if sweep_flag == 0 and sweep_angle > 0:
            sweep_angle -= 2 * math.pi
        elif sweep_flag == 1 and sweep_angle < 0:
            sweep_angle += 2 * math.pi

        # Step 6: Convert to cubic Bézier curves
        return _convert_arc_to_bezier_curves(cx, cy, rx, ry, phi_rad, start_angle, sweep_angle, max_segment_angle)

    except Exception as e:
        logger.error(f"Arc conversion failed: {e}")
        # Fallback to linear approximation
        return [(start_x, start_y, end_x, end_y, end_x, end_y, end_x, end_y)]


def compute_angle(ux: float, uy: float) -> float:
    """
    Compute the angle of a unit vector.

    Args:
        ux, uy: Unit vector components

    Returns:
        Angle in radians
    """
    # Handle the case where the vector is zero
    if abs(ux) < 1e-10 and abs(uy) < 1e-10:
        return 0.0

    # Normalize the vector
    length = math.sqrt(ux * ux + uy * uy)
    if length < 1e-10:
        return 0.0

    ux_norm = ux / length
    uy_norm = uy / length

    # Compute angle using atan2 for correct quadrant
    return math.atan2(uy_norm, ux_norm)


def _convert_arc_to_bezier_curves(cx: float, cy: float, rx: float, ry: float,
                                 phi: float, start_angle: float, sweep_angle: float, max_segment_angle: float = 90.0) -> list[tuple[float, float, float, float, float, float, float, float]]:
    """
    Convert arc parameters to cubic Bézier curve segments.

    This function segments the arc into multiple curves if the sweep angle is large,
    ensuring smooth approximation.

    Args:
        cx, cy: Arc center coordinates
        rx, ry: Arc radii
        phi: Rotation angle in radians
        start_angle: Start angle in radians
        sweep_angle: Sweep angle in radians
        max_segment_angle: Maximum angle per segment in degrees

    Returns:
        List of cubic Bézier curve segments
    """
    # Convert max_segment_angle from degrees to radians
    max_segment_angle_rad = math.radians(max_segment_angle)

    # Determine number of segments needed
    num_segments = max(1, math.ceil(abs(sweep_angle) / max_segment_angle_rad))
    segment_angle = sweep_angle / num_segments

    curves = []
    current_angle = start_angle

    cos_phi = math.cos(phi)
    sin_phi = math.sin(phi)

    for i in range(num_segments):
        # Calculate segment end angle
        next_angle = current_angle + segment_angle

        # Generate cubic Bézier for this segment
        curve = _arc_segment_to_bezier(cx, cy, rx, ry, cos_phi, sin_phi, current_angle, segment_angle)
        curves.append(curve)

        current_angle = next_angle

    return curves


def _arc_segment_to_bezier(cx: float, cy: float, rx: float, ry: float,
                          cos_phi: float, sin_phi: float, start_angle: float, segment_angle: float) -> tuple[float, float, float, float, float, float, float, float]:
    """
    Convert a single arc segment to a cubic Bézier curve.

    This uses the optimal cubic Bézier approximation of a circular arc,
    with the magic number alpha for control point distance.

    Args:
        cx, cy: Arc center
        rx, ry: Arc radii
        cos_phi, sin_phi: Precomputed rotation values
        start_angle: Segment start angle in radians
        segment_angle: Segment sweep angle in radians

    Returns:
        Cubic Bézier curve as (start_x, start_y, cp1_x, cp1_y, cp2_x, cp2_y, end_x, end_y)
    """
    end_angle = start_angle + segment_angle

    # Precompute trigonometric values
    cos_start = math.cos(start_angle)
    sin_start = math.sin(start_angle)
    cos_end = math.cos(end_angle)
    sin_end = math.sin(end_angle)

    # Magic number for optimal cubic Bézier approximation
    # This is the standard formula used in graphics libraries
    alpha = math.sin(segment_angle) * (math.sqrt(4 + 3 * math.tan(segment_angle / 2) ** 2) - 1) / 3

    # Calculate control points in the unit circle
    cp1_unit_x = cos_start - alpha * sin_start
    cp1_unit_y = sin_start + alpha * cos_start
    cp2_unit_x = cos_end + alpha * sin_end
    cp2_unit_y = sin_end - alpha * cos_end

    # Transform control points to the actual ellipse
    cp1_x = cx + rx * (cos_phi * cp1_unit_x - sin_phi * cp1_unit_y)
    cp1_y = cy + ry * (sin_phi * cp1_unit_x + cos_phi * cp1_unit_y)

    cp2_x = cx + rx * (cos_phi * cp2_unit_x - sin_phi * cp2_unit_y)
    cp2_y = cy + ry * (sin_phi * cp2_unit_x + cos_phi * cp2_unit_y)

    # Calculate start and end points
    start_x = cx + rx * (cos_phi * cos_start - sin_phi * sin_start)
    start_y = cy + ry * (sin_phi * cos_start + cos_phi * sin_start)
    end_x = cx + rx * (cos_phi * cos_end - sin_phi * sin_end)
    end_y = cy + ry * (sin_phi * cos_end + cos_phi * sin_end)

    return (start_x, start_y, cp1_x, cp1_y, cp2_x, cp2_y, end_x, end_y)


def validate_arc_parameters(rx: float, ry: float, start_x: float, start_y: float,
                           end_x: float, end_y: float) -> bool:
    """
    Validate arc parameters for mathematical correctness.

    Args:
        rx, ry: Arc radii (must be positive)
        start_x, start_y: Arc start point
        end_x, end_y: Arc end point

    Returns:
        True if parameters are valid, False otherwise
    """
    # Check for positive radii
    if rx <= 0 or ry <= 0:
        return False

    # Check for finite coordinates
    coords = [start_x, start_y, end_x, end_y, rx, ry]
    if not all(math.isfinite(coord) for coord in coords):
        return False

    return True


def estimate_arc_error(rx: float, ry: float, segment_angle: float) -> float:
    """
    Estimate the approximation error for a cubic Bézier arc segment.

    This can be used to determine if additional segmentation is needed
    for high-precision applications.

    Args:
        rx, ry: Arc radii
        segment_angle: Segment angle in radians

    Returns:
        Estimated maximum error in coordinate units
    """
    # This is a simplified error estimation based on the arc radius
    # and segment angle. For a more precise estimate, numerical methods
    # would be needed.
    max_radius = max(rx, ry)
    normalized_angle = abs(segment_angle) / (math.pi / 2)  # Normalize to quarter circle

    # Empirical error formula (approximate)
    error = max_radius * (normalized_angle ** 4) * 0.001

    return error