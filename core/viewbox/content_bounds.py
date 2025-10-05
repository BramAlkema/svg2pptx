#!/usr/bin/env python3
"""
Content Bounds Calculator for SVG Viewport System

Calculates actual content bounding box after all transforms are applied,
handling common patterns like:
- translate(509.85 466.99) with paths at m-493.81-466.99
- Large coordinate systems brought into viewBox via transforms
"""

import re
from typing import Tuple

import numpy as np
from lxml import etree as ET

from ..utils.transform_utils import get_transform_safe


def parse_transform(transform_str: str) -> np.ndarray:
    """Parse SVG transform string into 3x3 transformation matrix."""
    # Default identity matrix
    matrix = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)

    if not transform_str:
        return matrix

    # Parse translate(x, y)
    translate_match = re.search(r'translate\s*\(\s*([^,\s]+)(?:[\s,]+([^)]+))?\s*\)', transform_str)
    if translate_match:
        tx = float(translate_match.group(1))
        ty = float(translate_match.group(2)) if translate_match.group(2) else 0
        translate_matrix = np.array([[1, 0, tx], [0, 1, ty], [0, 0, 1]], dtype=float)
        matrix = matrix @ translate_matrix

    # Parse matrix(a, b, c, d, e, f)
    matrix_match = re.search(r'matrix\s*\(\s*([^,\s]+)[\s,]+([^,\s]+)[\s,]+([^,\s]+)[\s,]+([^,\s]+)[\s,]+([^,\s]+)[\s,]+([^)]+)\s*\)', transform_str)
    if matrix_match:
        a, b, c, d, e, f = [float(x) for x in matrix_match.groups()]
        transform_matrix = np.array([[a, c, e], [b, d, f], [0, 0, 1]], dtype=float)
        matrix = matrix @ transform_matrix

    # Parse scale(sx, sy)
    scale_match = re.search(r'scale\s*\(\s*([^,\s]+)(?:[\s,]+([^)]+))?\s*\)', transform_str)
    if scale_match:
        sx = float(scale_match.group(1))
        sy = float(scale_match.group(2)) if scale_match.group(2) else sx
        scale_matrix = np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1]], dtype=float)
        matrix = matrix @ scale_matrix

    return matrix


def parse_path_bounds(path_d: str) -> tuple[float, float, float, float]:
    """Extract bounding box from SVG path d attribute (simplified)."""
    if not path_d:
        return 0, 0, 0, 0

    # Extract all coordinate pairs using regex
    coords = re.findall(r'[-+]?\d*\.?\d+', path_d)
    if len(coords) < 2:
        return 0, 0, 0, 0

    # Convert to float pairs
    points = []
    for i in range(0, len(coords) - 1, 2):
        try:
            x, y = float(coords[i]), float(coords[i + 1])
            points.append((x, y))
        except (ValueError, IndexError):
            continue

    if not points:
        return 0, 0, 0, 0

    # Calculate bounding box
    xs, ys = zip(*points)
    return min(xs), min(ys), max(xs), max(ys)


def get_element_bounds(element: ET.Element, parent_transform: np.ndarray = None) -> tuple[float, float, float, float]:
    """Calculate bounding box for a single SVG element with transforms."""
    if parent_transform is None:
        parent_transform = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)

    # Apply element's own transform using safe parsing
    transform_str = get_transform_safe(element)
    element_transform = parse_transform(transform_str) if transform_str else np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
    combined_transform = parent_transform @ element_transform

    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')

    tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag

    if tag == 'path':
        # Parse path data
        d = element.get('d', '')
        if d:
            path_min_x, path_min_y, path_max_x, path_max_y = parse_path_bounds(d)

            # Transform corners
            corners = np.array([
                [path_min_x, path_min_y, 1],
                [path_max_x, path_min_y, 1],
                [path_min_x, path_max_y, 1],
                [path_max_x, path_max_y, 1],
            ]).T

            transformed = combined_transform @ corners
            transformed_x = transformed[0, :]
            transformed_y = transformed[1, :]

            min_x = min(min_x, transformed_x.min())
            max_x = max(max_x, transformed_x.max())
            min_y = min(min_y, transformed_y.min())
            max_y = max(max_y, transformed_y.max())

    elif tag == 'rect':
        # Parse rectangle
        x = float(element.get('x', 0))
        y = float(element.get('y', 0))
        width = float(element.get('width', 0))
        height = float(element.get('height', 0))

        # Transform corners
        corners = np.array([
            [x, y, 1],
            [x + width, y, 1],
            [x, y + height, 1],
            [x + width, y + height, 1],
        ]).T

        transformed = combined_transform @ corners
        transformed_x = transformed[0, :]
        transformed_y = transformed[1, :]

        min_x = min(min_x, transformed_x.min())
        max_x = max(max_x, transformed_x.max())
        min_y = min(min_y, transformed_y.min())
        max_y = max(max_y, transformed_y.max())

    elif tag == 'circle':
        # Parse circle
        cx = float(element.get('cx', 0))
        cy = float(element.get('cy', 0))
        r = float(element.get('r', 0))

        # Transform center and radius points
        center = np.array([[cx, cy, 1]]).T
        radius_points = np.array([
            [cx - r, cy, 1],
            [cx + r, cy, 1],
            [cx, cy - r, 1],
            [cx, cy + r, 1],
        ]).T

        transformed = combined_transform @ radius_points
        transformed_x = transformed[0, :]
        transformed_y = transformed[1, :]

        min_x = min(min_x, transformed_x.min())
        max_x = max(max_x, transformed_x.max())
        min_y = min(min_y, transformed_y.min())
        max_y = max(max_y, transformed_y.max())

    # Recursively process children
    for child in element:
        child_min_x, child_min_y, child_max_x, child_max_y = get_element_bounds(child, combined_transform)
        if child_min_x != float('inf'):
            min_x = min(min_x, child_min_x)
            max_x = max(max_x, child_max_x)
            min_y = min(min_y, child_min_y)
            max_y = max(max_y, child_max_y)

    # Return invalid bounds if no content found
    if min_x == float('inf'):
        return 0, 0, 0, 0

    return min_x, min_y, max_x, max_y


def calculate_raw_content_bounds(svg_element: ET.Element) -> tuple[float, float, float, float]:
    """Calculate raw content bounds without viewBox clipping - for normalization detection."""
    # Get actual content bounds without any viewBox intersection logic
    min_x, min_y, max_x, max_y = get_element_bounds(svg_element)

    # Return invalid bounds if no content found
    if min_x == float('inf'):
        return 0, 0, 0, 0

    return min_x, min_y, max_x, max_y


def calculate_content_bounds(svg_element: ET.Element) -> tuple[float, float, float, float]:
    """Calculate the actual content bounding box for an SVG after all transforms."""
    # Get the viewBox for clipping context
    viewbox = svg_element.get('viewBox', '')
    viewbox_bounds = None

    if viewbox:
        parts = viewbox.split()
        if len(parts) == 4:
            vb_x, vb_y, vb_w, vb_h = [float(p) for p in parts]
            viewbox_bounds = (vb_x, vb_y, vb_x + vb_w, vb_y + vb_h)

    # Calculate actual content bounds
    min_x, min_y, max_x, max_y = get_element_bounds(svg_element)

    # If no content found, fall back to viewBox
    if min_x == float('inf'):
        if viewbox_bounds:
            return viewbox_bounds
        else:
            return 0, 0, 100, 100

    # For SVGs with transforms that bring large coordinates into viewBox range,
    # check if the content intersects with viewBox and adjust accordingly
    if viewbox_bounds:
        vb_min_x, vb_min_y, vb_max_x, vb_max_y = viewbox_bounds

        # Check if content is primarily outside viewBox (common pattern)
        content_width = max_x - min_x
        content_height = max_y - min_y
        viewbox_width = vb_max_x - vb_min_x
        viewbox_height = vb_max_y - vb_min_y

        # If content is much larger than viewBox, check intersection pattern
        if (content_width > 3 * viewbox_width or content_height > 3 * viewbox_height):
            # Check for intersection
            intersect_min_x = max(min_x, vb_min_x)
            intersect_min_y = max(min_y, vb_min_y)
            intersect_max_x = min(max_x, vb_max_x)
            intersect_max_y = min(max_y, vb_max_y)

            if intersect_min_x < intersect_max_x and intersect_min_y < intersect_max_y:
                # Content intersects viewBox - use the intersection as bounds
                return intersect_min_x, intersect_min_y, intersect_max_x, intersect_max_y
            else:
                # No intersection - content is entirely off-slide
                # Return actual content bounds for normalization system to detect and fix
                return min_x, min_y, max_x, max_y

    return min_x, min_y, max_x, max_y