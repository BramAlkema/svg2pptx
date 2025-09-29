#!/usr/bin/env python3
"""
Matrix Composer for SVG Viewport Transformation

Implements complete viewport matrix composition following SVG specification:
1. viewBox → coordinate system transformation
2. preserveAspectRatio → alignment and scaling behavior
3. Content normalization → handling large coordinate spaces

This fixes the core issue where SVGs with complex transforms (like DTDA logo)
end up with shapes positioned off-slide due to improper matrix composition.
"""

import re
import math
from typing import Tuple, Optional, Union
from lxml import etree as ET
import numpy as np

from ..utils.transform_utils import get_transform_safe, has_attribute_safe


# EMU Constants for PowerPoint coordinate system
EMU_PER_INCH = 914400
EMU_PER_POINT = 12700
EMU_PER_MM = 36000
EMU_PER_CM = 360000

# Standard PowerPoint slide dimensions in EMU
STANDARD_SLIDE_WIDTH_EMU = 9144000   # 10 inches
STANDARD_SLIDE_HEIGHT_EMU = 6858000  # 7.5 inches


def parse_viewbox(svg_element: ET.Element) -> Tuple[float, float, float, float]:
    """
    Parse SVG viewBox attribute into (x, y, width, height).

    Args:
        svg_element: SVG root element with viewBox attribute

    Returns:
        Tuple of (min_x, min_y, width, height) in SVG user units

    Raises:
        ValueError: If viewBox is invalid or missing
    """
    viewbox_str = svg_element.get('viewBox', '').strip()
    if not viewbox_str:
        # Fallback to width/height attributes
        width_str = svg_element.get('width', '100')
        height_str = svg_element.get('height', '100')

        # Parse width/height, removing units
        width = parse_svg_length(width_str)
        height = parse_svg_length(height_str)

        return 0.0, 0.0, width, height

    # Parse viewBox string
    try:
        # Replace commas with spaces and split
        cleaned = re.sub(r'[,\s]+', ' ', viewbox_str.strip())
        parts = cleaned.split()

        if len(parts) != 4:
            raise ValueError(f"viewBox must have 4 values, got {len(parts)}")

        x, y, width, height = [float(p) for p in parts]

        if width <= 0 or height <= 0:
            raise ValueError(f"viewBox width and height must be positive, got {width}x{height}")

        return x, y, width, height

    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid viewBox '{viewbox_str}': {e}")


def parse_svg_length(length_str: str) -> float:
    """
    Parse SVG length value, removing units and converting to user units.

    Args:
        length_str: SVG length value (e.g., "100px", "50mm", "10")

    Returns:
        Length value in user units (assuming 1 user unit = 1px for simplicity)
    """
    if not length_str:
        return 0.0

    # Remove common units and convert
    length_str = length_str.strip()

    # Extract numeric part
    numeric_match = re.match(r'^([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)', length_str)
    if not numeric_match:
        return 0.0

    value = float(numeric_match.group(1))

    # For now, treat all units as user units (more sophisticated conversion possible)
    # This handles the common case where viewBox and dimensions use same coordinate space
    return value


def parse_preserve_aspect_ratio(svg_element: ET.Element) -> Tuple[str, str]:
    """
    Parse preserveAspectRatio attribute into alignment and meet/slice values.

    Args:
        svg_element: SVG root element with preserveAspectRatio attribute

    Returns:
        Tuple of (alignment, meet_or_slice) strings
        Default: ('xMidYMid', 'meet')
    """
    par_str = svg_element.get('preserveAspectRatio', 'xMidYMid meet').strip().lower()

    if par_str == 'none':
        return ('none', 'meet')

    parts = par_str.split()

    # Parse alignment (default: xMidYMid)
    alignment = 'xmidymid'
    meet_slice = 'meet'

    for part in parts:
        if part in ['xminymin', 'xmidymin', 'xmaxymin',
                   'xminymid', 'xmidymid', 'xmaxymid',
                   'xminymax', 'xmidymax', 'xmaxymax', 'none']:
            alignment = part
        elif part in ['meet', 'slice']:
            meet_slice = part

    return alignment, meet_slice


def get_alignment_factors(alignment: str) -> Tuple[float, float]:
    """
    Get alignment offset factors for viewport positioning.

    Args:
        alignment: Alignment string (e.g., 'xmidymid', 'xminymin')

    Returns:
        Tuple of (x_factor, y_factor) where 0=min, 0.5=mid, 1=max
    """
    alignment_map = {
        'xminymin': (0.0, 0.0),
        'xmidymin': (0.5, 0.0),
        'xmaxymin': (1.0, 0.0),
        'xminymid': (0.0, 0.5),
        'xmidymid': (0.5, 0.5),  # Default
        'xmaxymid': (1.0, 0.5),
        'xminymax': (0.0, 1.0),
        'xmidymax': (0.5, 1.0),
        'xmaxymax': (1.0, 1.0),
        'none': (0.0, 0.0),
    }

    return alignment_map.get(alignment, (0.5, 0.5))


def viewport_matrix(svg_root: ET.Element, slide_w_emu: int, slide_h_emu: int) -> np.ndarray:
    """
    Compute complete viewport transformation matrix from SVG to EMU coordinates.

    This implements the SVG viewport transformation chain:
    1. viewBox translate to origin: Translate(-vb.x, -vb.y)
    2. Scale for meet/slice preserving aspect ratio
    3. Align inside the slide according to preserveAspectRatio

    Args:
        svg_root: SVG root element with viewBox and preserveAspectRatio
        slide_w_emu: Target slide width in EMU
        slide_h_emu: Target slide height in EMU

    Returns:
        3x3 transformation matrix that maps SVG user units to slide EMU coordinates
    """
    # Parse viewBox and preserveAspectRatio
    vb_x, vb_y, vb_w, vb_h = parse_viewbox(svg_root)
    alignment, meet_slice = parse_preserve_aspect_ratio(svg_root)

    # 1) viewBox translate to origin
    T_vb = np.array([
        [1, 0, -vb_x],
        [0, 1, -vb_y],
        [0, 0, 1]
    ], dtype=float)

    # 2) Scale for meet/slice preserving aspect ratio
    sx = slide_w_emu / vb_w
    sy = slide_h_emu / vb_h

    if meet_slice == "meet":
        # Scale to fit entirely within viewport (uniform scaling)
        s = min(sx, sy)
    else:  # slice
        # Scale to fill entire viewport (uniform scaling)
        s = max(sx, sy)

    S = np.array([
        [s, 0, 0],
        [0, s, 0],
        [0, 0, 1]
    ], dtype=float)

    # 3) Align inside the slide
    align_x, align_y = get_alignment_factors(alignment)

    # Calculate offset for alignment
    scaled_w = vb_w * s
    scaled_h = vb_h * s

    off_x = (slide_w_emu - scaled_w) * align_x
    off_y = (slide_h_emu - scaled_h) * align_y

    A = np.array([
        [1, 0, off_x],
        [0, 1, off_y],
        [0, 0, 1]
    ], dtype=float)

    # Compose: Align @ Scale @ ViewBoxTranslate
    return A @ S @ T_vb


def parse_transform(transform_str: Optional[str]) -> np.ndarray:
    """
    Parse SVG transform string into 3x3 transformation matrix.

    Args:
        transform_str: SVG transform attribute value

    Returns:
        3x3 transformation matrix (identity if transform_str is None/empty)
    """
    if not transform_str:
        return np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)

    # Initialize with identity matrix
    matrix = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)

    # Parse translate(x, y) or translate(x)
    translate_matches = re.finditer(r'translate\s*\(\s*([^,\s)]+)(?:[\s,]+([^)]*))?\s*\)', transform_str)
    for match in translate_matches:
        tx = float(match.group(1))
        ty = float(match.group(2)) if match.group(2) and match.group(2).strip() else 0
        translate_matrix = np.array([[1, 0, tx], [0, 1, ty], [0, 0, 1]], dtype=float)
        matrix = matrix @ translate_matrix

    # Parse matrix(a, b, c, d, e, f)
    matrix_matches = re.finditer(r'matrix\s*\(\s*([^,\s)]+)[\s,]+([^,\s)]+)[\s,]+([^,\s)]+)[\s,]+([^,\s)]+)[\s,]+([^,\s)]+)[\s,]+([^)]+)\s*\)', transform_str)
    for match in matrix_matches:
        a, b, c, d, e, f = [float(x) for x in match.groups()]
        transform_matrix = np.array([[a, c, e], [b, d, f], [0, 0, 1]], dtype=float)
        matrix = matrix @ transform_matrix

    # Parse scale(sx, sy) or scale(s)
    scale_matches = re.finditer(r'scale\s*\(\s*([^,\s)]+)(?:[\s,]+([^)]*))?\s*\)', transform_str)
    for match in scale_matches:
        sx = float(match.group(1))
        sy = float(match.group(2)) if match.group(2) and match.group(2).strip() else sx
        scale_matrix = np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1]], dtype=float)
        matrix = matrix @ scale_matrix

    # Parse rotate(angle) or rotate(angle, cx, cy)
    rotate_matches = re.finditer(r'rotate\s*\(\s*([^,\s)]+)(?:[\s,]+([^,\s)]+)[\s,]+([^)]+))?\s*\)', transform_str)
    for match in rotate_matches:
        angle = math.radians(float(match.group(1)))
        cx = float(match.group(2)) if match.group(2) else 0
        cy = float(match.group(3)) if match.group(3) else 0

        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        if cx != 0 or cy != 0:
            # Rotate around point (cx, cy): T(cx,cy) @ R @ T(-cx,-cy)
            rotate_matrix = np.array([
                [cos_a, -sin_a, cx - cx * cos_a + cy * sin_a],
                [sin_a, cos_a, cy - cx * sin_a - cy * cos_a],
                [0, 0, 1]
            ], dtype=float)
        else:
            # Rotate around origin
            rotate_matrix = np.array([
                [cos_a, -sin_a, 0],
                [sin_a, cos_a, 0],
                [0, 0, 1]
            ], dtype=float)

        matrix = matrix @ rotate_matrix

    return matrix


def element_ctm(node: ET.Element, parent_ctm: Optional[np.ndarray], viewport_ctm: np.ndarray) -> np.ndarray:
    """
    Calculate Current Transformation Matrix for element.

    Args:
        node: SVG element with optional transform attribute
        parent_ctm: Parent element's CTM (or None for root)
        viewport_ctm: Root viewport transformation matrix

    Returns:
        3x3 CTM for this element (parent_ctm @ local_transform)
    """
    # Parse local transform
    transform_str = get_transform_safe(node)
    local_transform = parse_transform(transform_str)

    if parent_ctm is not None:
        # Compose with parent CTM
        return parent_ctm @ local_transform
    else:
        # First element - compose with viewport CTM
        return viewport_ctm @ local_transform


def normalise_content_matrix(min_x: float, min_y: float) -> np.ndarray:
    """
    Create normalization matrix to move content to origin.

    Args:
        min_x: Minimum X coordinate of content bounds
        min_y: Minimum Y coordinate of content bounds

    Returns:
        3x3 translation matrix: Translate(-min_x, -min_y)
    """
    return np.array([
        [1, 0, -min_x],
        [0, 1, -min_y],
        [0, 0, 1]
    ], dtype=float)


def needs_normalise(svg_root: ET.Element) -> bool:
    """
    Determine if SVG needs content normalization using comprehensive heuristics.

    Detects patterns where content appears off-slide due to large coordinates:
    1. Content 3× larger than viewBox (transform pattern)
    2. Content with significant negative coordinates
    3. Content positioned far outside viewBox (DTDA pattern)
    4. Content entirely outside viewBox bounds

    Args:
        svg_root: SVG root element

    Returns:
        True if content bounds normalization should be applied
    """
    try:
        from ..viewbox.content_bounds import calculate_raw_content_bounds

        # Get viewBox bounds
        vb_x, vb_y, vb_w, vb_h = parse_viewbox(svg_root)

        # Calculate actual content bounds without viewBox clipping
        min_x, min_y, max_x, max_y = calculate_raw_content_bounds(svg_root)
        content_w = max_x - min_x
        content_h = max_y - min_y

        # Apply heuristics to detect need for content normalization

        # 1. Content much larger than viewBox suggests transform pattern
        size_ratio_threshold = 3.0
        if (content_w > size_ratio_threshold * vb_w or
            content_h > size_ratio_threshold * vb_h):
            return True

        # 2. Content with significant negative coordinates
        if min_x < -vb_w * 0.1 or min_y < -vb_h * 0.1:
            return True

        # 3. Content positioned far outside viewBox bounds (DTDA pattern)
        # Check if content center is far from viewBox center
        vb_center_x = vb_x + vb_w / 2
        vb_center_y = vb_y + vb_h / 2
        content_center_x = min_x + content_w / 2
        content_center_y = min_y + content_h / 2

        # Distance from viewBox center to content center
        center_distance_x = abs(content_center_x - vb_center_x)
        center_distance_y = abs(content_center_y - vb_center_y)

        # If content center is > 2× viewBox dimensions away, normalize
        distance_threshold = 2.0
        if (center_distance_x > distance_threshold * vb_w or
            center_distance_y > distance_threshold * vb_h):
            return True

        # 4. Content entirely outside viewBox (no intersection)
        vb_max_x = vb_x + vb_w
        vb_max_y = vb_y + vb_h

        # Check if there's any intersection with viewBox
        intersect_min_x = max(min_x, vb_x)
        intersect_min_y = max(min_y, vb_y)
        intersect_max_x = min(max_x, vb_max_x)
        intersect_max_y = min(max_y, vb_max_y)

        has_intersection = (intersect_min_x < intersect_max_x and
                           intersect_min_y < intersect_max_y)

        if not has_intersection:
            return True

        return False

    except Exception:
        # If content bounds calculation fails, be conservative
        return False


def on_slide(x: int, y: int, w: int, h: int, slide_w: int, slide_h: int, margin: int = 50000) -> bool:
    """
    Check if shape coordinates fall within slide bounds.

    Args:
        x, y: Shape position in EMU
        w, h: Shape dimensions in EMU
        slide_w, slide_h: Slide dimensions in EMU
        margin: EMU margin for partial visibility (default ~3.9mm)

    Returns:
        True if shape is visible on slide
    """
    return (x + w > -margin and
            y + h > -margin and
            x < slide_w + margin and
            y < slide_h + margin)