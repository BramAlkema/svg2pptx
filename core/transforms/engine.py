#!/usr/bin/env python3
"""
Transform Engine for SVG coordinate transformations

Provides backward-compatible TransformEngine that integrates
with the new matrix composer system.
"""

import numpy as np
from typing import List, Optional, Tuple
from lxml import etree as ET

from .matrix_composer import (
    parse_transform, viewport_matrix, element_ctm,
    needs_normalise, normalise_content_matrix
)


class TransformEngine:
    """
    Transform engine for SVG coordinate transformations.

    Provides backward compatibility while integrating with new CTM system.
    """

    def __init__(self):
        """Initialize transform engine."""
        self.current_matrix = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
        self._transform_stack = []

    def apply_combined_transforms(self, transform_list: List[str]) -> None:
        """
        Apply multiple transform strings to current matrix.

        Args:
            transform_list: List of SVG transform strings
        """
        for transform_str in transform_list:
            if transform_str and transform_str.strip():
                transform_matrix = parse_transform(transform_str)
                self.current_matrix = self.current_matrix @ transform_matrix

    def parse_to_matrix(self, transform_str: str, context=None):
        """
        Parse transform string to matrix (backward compatibility).

        Args:
            transform_str: SVG transform string
            context: Optional context (ignored)

        Returns:
            Legacy Matrix object for backward compatibility
        """
        matrix = parse_transform(transform_str)

        # Create legacy Matrix object
        try:
            from ..transforms.core import Matrix
            return Matrix(
                matrix[0, 0], matrix[1, 0], matrix[0, 1],
                matrix[1, 1], matrix[0, 2], matrix[1, 2]
            )
        except ImportError:
            # Return numpy matrix if legacy Matrix not available
            return matrix

    def reset(self) -> None:
        """Reset transform engine to identity."""
        self.current_matrix = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
        self._transform_stack.clear()

    def push_transform(self, transform_str: str) -> None:
        """Push transform onto stack."""
        self._transform_stack.append(self.current_matrix.copy())
        if transform_str and transform_str.strip():
            transform_matrix = parse_transform(transform_str)
            self.current_matrix = self.current_matrix @ transform_matrix

    def pop_transform(self) -> None:
        """Pop transform from stack."""
        if self._transform_stack:
            self.current_matrix = self._transform_stack.pop()
        else:
            self.reset()

    def transform_point(self, x: float, y: float) -> Tuple[float, float]:
        """Transform point using current matrix."""
        point = np.array([x, y, 1])
        transformed = self.current_matrix @ point
        return float(transformed[0]), float(transformed[1])

    def transform_points(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Transform multiple points using current matrix."""
        if not points:
            return points

        # Convert to homogeneous coordinates
        homogeneous = np.array([[x, y, 1] for x, y in points]).T

        # Apply transformation
        transformed = self.current_matrix @ homogeneous

        # Convert back to (x, y) tuples
        return [(float(transformed[0, i]), float(transformed[1, i])) for i in range(transformed.shape[1])]

    def compose(self, transforms: List[str], viewport_context=None):
        """
        Compose transform strings in parent→child order for safe chaining.

        Args:
            transforms: List of SVG transform strings in parent→child order
            viewport_context: Optional viewport context (compatibility parameter)

        Returns:
            Matrix object representing the composed transformation

        Raises:
            ValueError: If transform string is malformed
        """
        from .core import Matrix

        # Start with identity
        result = Matrix.identity()

        for transform_str in transforms:
            if transform_str and transform_str.strip():
                try:
                    # Parse each transform using existing method
                    transform_matrix = self.parse_to_matrix(transform_str, viewport_context)
                    # Compose using @ operator (parent → child order)
                    result = result @ transform_matrix
                except Exception as e:
                    raise ValueError(f"Failed to parse transform '{transform_str}': {e}")

        return result

    def identity(self):
        """
        Return clean identity matrix.

        Returns:
            Matrix: Identity transformation matrix
        """
        from .core import Matrix
        return Matrix.identity()