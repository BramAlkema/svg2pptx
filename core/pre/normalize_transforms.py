#!/usr/bin/env python3
"""
Normalize Transforms Preprocessor

Flattens transform hierarchies and normalizes transform syntax.
This simplifies coordinate handling during IR conversion.

Features:
- Matrix composition
- Transform flattening
- Coordinate system normalization
- Viewport handling
"""

import logging
import re
import math
from typing import List
import numpy as np
from lxml import etree as ET

from .base import BasePreprocessor


class NormalizeTransformsPreprocessor(BasePreprocessor):
    """
    Preprocessor that normalizes transform hierarchies.

    Flattens nested transforms into single matrix representations
    and applies transforms to geometric attributes where possible.
    """

    def __init__(self, flatten_simple_transforms: bool = True):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.flatten_simple_transforms = flatten_simple_transforms

    def process(self, svg_root: ET.Element) -> ET.Element:
        """
        Normalize transforms in the SVG.

        Args:
            svg_root: SVG root element

        Returns:
            SVG with normalized transforms
        """
        self.logger.debug("Starting transform normalization")

        # Establish root coordinate system
        self._establish_root_coordinate_system(svg_root)

        # Normalize transform hierarchy
        self._normalize_transform_hierarchy(svg_root, np.eye(3))

        self.logger.debug("Transform normalization complete")
        return svg_root

    def _establish_root_coordinate_system(self, svg_root: ET.Element) -> None:
        """Establish consistent root coordinate system."""
        # Ensure viewBox is present and normalized
        viewbox = svg_root.get('viewBox')
        width = svg_root.get('width', '100')
        height = svg_root.get('height', '100')

        # Parse dimensions
        width_val = self._parse_dimension(width)
        height_val = self._parse_dimension(height)

        if not viewbox:
            # Create viewBox from dimensions
            svg_root.set('viewBox', f'0 0 {width_val} {height_val}')
            self.logger.debug(f"Added viewBox: 0 0 {width_val} {height_val}")

        # Normalize dimension units (remove units, keep numeric values)
        svg_root.set('width', str(width_val))
        svg_root.set('height', str(height_val))

    def _normalize_transform_hierarchy(self, element: ET.Element, parent_matrix: np.ndarray) -> None:
        """Recursively normalize transform hierarchy."""
        # Get element's transform
        element_matrix = self._parse_transform(element.get('transform', ''))

        # Compose with parent transform
        combined_matrix = parent_matrix @ element_matrix

        # Apply transform normalization based on element type
        self._apply_transform_normalization(element, combined_matrix)

        # Process children with combined transform
        for child in element:
            self._normalize_transform_hierarchy(child, combined_matrix)

    def _apply_transform_normalization(self, element: ET.Element, matrix: np.ndarray) -> None:
        """Apply appropriate transform normalization for element type."""
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag

        if tag in ['rect', 'circle', 'ellipse', 'line']:
            self._normalize_basic_shape_transform(element, matrix, tag)
        elif tag == 'path':
            self._normalize_path_transform(element, matrix)
        elif tag == 'text':
            self._normalize_text_transform(element, matrix)
        elif tag in ['g', 'defs', 'clipPath', 'mask']:
            self._normalize_container_transform(element, matrix)
        else:
            # Generic transform handling
            self._set_element_transform(element, matrix)

    def _normalize_basic_shape_transform(self, element: ET.Element, matrix: np.ndarray, shape_type: str) -> None:
        """Normalize transforms for basic shapes (rect, circle, etc.)."""
        if self.flatten_simple_transforms and self._is_simple_transform(matrix):
            # Apply transform to geometric attributes
            if shape_type == 'rect':
                self._transform_rect_attributes(element, matrix)
            elif shape_type == 'circle':
                self._transform_circle_attributes(element, matrix)
            elif shape_type == 'ellipse':
                self._transform_ellipse_attributes(element, matrix)
            elif shape_type == 'line':
                self._transform_line_attributes(element, matrix)

            # Remove transform attribute since it's been applied
            if element.get('transform'):
                del element.attrib['transform']
        else:
            # Keep as matrix transform
            self._set_element_transform(element, matrix)

    def _normalize_path_transform(self, element: ET.Element, matrix: np.ndarray) -> None:
        """Normalize transforms for path elements."""
        # For paths, generally keep transform as matrix since path data
        # transformation is complex and better handled during IR conversion
        self._set_element_transform(element, matrix)

    def _normalize_text_transform(self, element: ET.Element, matrix: np.ndarray) -> None:
        """Normalize transforms for text elements."""
        # Apply translation to text position, keep other transforms as matrix
        if self._is_translation_only(matrix):
            # Apply translation to x,y attributes
            x = float(element.get('x', '0'))
            y = float(element.get('y', '0'))

            # Transform position
            pos = np.array([x, y, 1.0])
            transformed_pos = matrix @ pos

            element.set('x', str(transformed_pos[0]))
            element.set('y', str(transformed_pos[1]))

            # Remove transform
            if element.get('transform'):
                del element.attrib['transform']
        else:
            # Keep complex transform as matrix
            self._set_element_transform(element, matrix)

    def _normalize_container_transform(self, element: ET.Element, matrix: np.ndarray) -> None:
        """Normalize transforms for container elements."""
        # For containers, set the combined transform
        self._set_element_transform(element, matrix)

    def _parse_transform(self, transform_str: str) -> np.ndarray:
        """Parse SVG transform string into 3x3 matrix."""
        if not transform_str:
            return np.eye(3)

        matrix = np.eye(3)

        # Parse transform functions
        # Pattern to match transform functions
        pattern = r'(\w+)\s*\(\s*([^)]*)\s*\)'
        matches = re.findall(pattern, transform_str)

        for func_name, params_str in matches:
            params = [float(x.strip()) for x in params_str.replace(',', ' ').split() if x.strip()]
            func_matrix = self._parse_transform_function(func_name, params)
            matrix = matrix @ func_matrix

        return matrix

    def _parse_transform_function(self, func_name: str, params: List[float]) -> np.ndarray:
        """Parse individual transform function into matrix."""
        func_name = func_name.lower()

        if func_name == 'translate':
            tx = params[0] if len(params) > 0 else 0
            ty = params[1] if len(params) > 1 else 0
            return np.array([
                [1, 0, tx],
                [0, 1, ty],
                [0, 0, 1]
            ])

        elif func_name == 'scale':
            sx = params[0] if len(params) > 0 else 1
            sy = params[1] if len(params) > 1 else sx
            return np.array([
                [sx, 0, 0],
                [0, sy, 0],
                [0, 0, 1]
            ])

        elif func_name == 'rotate':
            angle = math.radians(params[0]) if len(params) > 0 else 0
            cx = params[1] if len(params) > 1 else 0
            cy = params[2] if len(params) > 2 else 0

            cos_a = math.cos(angle)
            sin_a = math.sin(angle)

            if cx == 0 and cy == 0:
                return np.array([
                    [cos_a, -sin_a, 0],
                    [sin_a, cos_a, 0],
                    [0, 0, 1]
                ])
            else:
                # Rotate around center point
                # translate(-cx, -cy) * rotate(angle) * translate(cx, cy)
                return np.array([
                    [cos_a, -sin_a, cx - cx * cos_a + cy * sin_a],
                    [sin_a, cos_a, cy - cx * sin_a - cy * cos_a],
                    [0, 0, 1]
                ])

        elif func_name == 'skewx':
            angle = math.radians(params[0]) if len(params) > 0 else 0
            return np.array([
                [1, math.tan(angle), 0],
                [0, 1, 0],
                [0, 0, 1]
            ])

        elif func_name == 'skewy':
            angle = math.radians(params[0]) if len(params) > 0 else 0
            return np.array([
                [1, 0, 0],
                [math.tan(angle), 1, 0],
                [0, 0, 1]
            ])

        elif func_name == 'matrix':
            if len(params) >= 6:
                a, b, c, d, e, f = params[:6]
                return np.array([
                    [a, c, e],
                    [b, d, f],
                    [0, 0, 1]
                ])

        # Default to identity matrix for unknown functions
        return np.eye(3)

    def _is_simple_transform(self, matrix: np.ndarray) -> bool:
        """Check if transform is simple (translation + uniform scale)."""
        # Check if matrix is close to identity with translation
        if np.allclose(matrix, np.eye(3)):
            return True

        # Check for translation only
        if (np.allclose(matrix[0, 0], 1.0) and np.allclose(matrix[1, 1], 1.0) and
            np.allclose(matrix[0, 1], 0.0) and np.allclose(matrix[1, 0], 0.0)):
            return True

        # Check for uniform scale + translation
        scale_x = matrix[0, 0]
        scale_y = matrix[1, 1]
        if (np.allclose(scale_x, scale_y) and
            np.allclose(matrix[0, 1], 0.0) and np.allclose(matrix[1, 0], 0.0)):
            return True

        return False

    def _is_translation_only(self, matrix: np.ndarray) -> bool:
        """Check if transform is translation only."""
        return (np.allclose(matrix[0, 0], 1.0) and np.allclose(matrix[1, 1], 1.0) and
                np.allclose(matrix[0, 1], 0.0) and np.allclose(matrix[1, 0], 0.0))

    def _set_element_transform(self, element: ET.Element, matrix: np.ndarray) -> None:
        """Set element transform from matrix."""
        if np.allclose(matrix, np.eye(3)):
            # Identity matrix - remove transform
            if element.get('transform'):
                del element.attrib['transform']
        else:
            # Convert matrix to SVG transform string
            a, c, e = matrix[0, :]
            b, d, f = matrix[1, :]
            transform_str = f"matrix({a:.6g},{b:.6g},{c:.6g},{d:.6g},{e:.6g},{f:.6g})"
            element.set('transform', transform_str)

    def _transform_rect_attributes(self, element: ET.Element, matrix: np.ndarray) -> None:
        """Apply transform to rectangle attributes."""
        x = float(element.get('x', '0'))
        y = float(element.get('y', '0'))
        width = float(element.get('width', '0'))
        height = float(element.get('height', '0'))

        # Transform corner points
        corners = np.array([
            [x, y, 1],
            [x + width, y, 1],
            [x, y + height, 1],
            [x + width, y + height, 1]
        ]).T

        transformed_corners = matrix @ corners

        # Calculate new bounding box
        min_x = np.min(transformed_corners[0, :])
        min_y = np.min(transformed_corners[1, :])
        max_x = np.max(transformed_corners[0, :])
        max_y = np.max(transformed_corners[1, :])

        element.set('x', str(min_x))
        element.set('y', str(min_y))
        element.set('width', str(max_x - min_x))
        element.set('height', str(max_y - min_y))

    def _transform_circle_attributes(self, element: ET.Element, matrix: np.ndarray) -> None:
        """Apply transform to circle attributes."""
        cx = float(element.get('cx', '0'))
        cy = float(element.get('cy', '0'))
        r = float(element.get('r', '0'))

        # Transform center point
        center = np.array([cx, cy, 1.0])
        transformed_center = matrix @ center

        # For uniform scaling, transform radius
        scale_factor = math.sqrt(abs(np.linalg.det(matrix[:2, :2])))
        transformed_r = r * scale_factor

        element.set('cx', str(transformed_center[0]))
        element.set('cy', str(transformed_center[1]))
        element.set('r', str(transformed_r))

    def _transform_ellipse_attributes(self, element: ET.Element, matrix: np.ndarray) -> None:
        """Apply transform to ellipse attributes."""
        cx = float(element.get('cx', '0'))
        cy = float(element.get('cy', '0'))
        rx = float(element.get('rx', '0'))
        ry = float(element.get('ry', '0'))

        # Transform center point
        center = np.array([cx, cy, 1.0])
        transformed_center = matrix @ center

        # For simple transforms, scale radii
        scale_x = math.sqrt(matrix[0, 0]**2 + matrix[1, 0]**2)
        scale_y = math.sqrt(matrix[0, 1]**2 + matrix[1, 1]**2)

        element.set('cx', str(transformed_center[0]))
        element.set('cy', str(transformed_center[1]))
        element.set('rx', str(rx * scale_x))
        element.set('ry', str(ry * scale_y))

    def _transform_line_attributes(self, element: ET.Element, matrix: np.ndarray) -> None:
        """Apply transform to line attributes."""
        x1 = float(element.get('x1', '0'))
        y1 = float(element.get('y1', '0'))
        x2 = float(element.get('x2', '0'))
        y2 = float(element.get('y2', '0'))

        # Transform both points
        point1 = matrix @ np.array([x1, y1, 1.0])
        point2 = matrix @ np.array([x2, y2, 1.0])

        element.set('x1', str(point1[0]))
        element.set('y1', str(point1[1]))
        element.set('x2', str(point2[0]))
        element.set('y2', str(point2[1]))

    def _parse_dimension(self, dim_str: str) -> float:
        """Parse dimension string to numeric value."""
        if not dim_str:
            return 0.0

        # Remove common units and extract numeric value
        dim_str = dim_str.strip().lower()
        for unit in ['px', 'pt', 'pc', 'mm', 'cm', 'in', '%']:
            if dim_str.endswith(unit):
                dim_str = dim_str[:-len(unit)]
                break

        try:
            return float(dim_str)
        except ValueError:
            return 0.0


def normalize_transform_hierarchy(svg_root: ET.Element, flatten_simple: bool = True) -> ET.Element:
    """
    Convenience function to normalize transforms.

    Args:
        svg_root: SVG root element
        flatten_simple: Whether to flatten simple transforms to attributes

    Returns:
        SVG with normalized transforms
    """
    preprocessor = NormalizeTransformsPreprocessor(flatten_simple)
    return preprocessor.process(svg_root)