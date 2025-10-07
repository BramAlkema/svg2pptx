#!/usr/bin/env python3
"""
CoordinateSpace - CTM Stack for Baked Transforms

Manages coordinate transformations during parsing by maintaining a Current
Transformation Matrix (CTM) stack. Transforms are applied at parse time
and baked into coordinates, eliminating the need to store transform fields in IR.
"""

from typing import List, Optional
from .core import Matrix


class CoordinateSpace:
    """
    Manages coordinate transformations with CTM (Current Transformation Matrix) stack.
    
    Applies transforms at parse time instead of storing them in IR.
    Handles nested transforms through push/pop stack operations.
    """

    def __init__(self, viewport_matrix: Optional[Matrix] = None):
        """
        Initialize with viewport transformation.

        Args:
            viewport_matrix: Initial viewport transformation (defaults to identity)
        """
        if viewport_matrix is None:
            viewport_matrix = Matrix.identity()
            
        # CTM stack - starts with viewport matrix
        self.ctm_stack: List[Matrix] = [viewport_matrix]

    def push_transform(self, transform: Matrix):
        """
        Push transform onto CTM stack (for entering groups/elements).

        Composes the new transform with the current CTM.

        Args:
            transform: Transformation matrix to push
        """
        current_ctm = self.ctm_stack[-1]
        # Compose: new_ctm = current_ctm * transform
        new_ctm = current_ctm.multiply(transform)
        self.ctm_stack.append(new_ctm)

    def pop_transform(self):
        """
        Pop transform from CTM stack (for exiting groups/elements).

        Raises:
            ValueError: If attempting to pop the viewport matrix
        """
        if len(self.ctm_stack) <= 1:
            raise ValueError("Cannot pop viewport matrix from CTM stack")
        
        self.ctm_stack.pop()

    def apply_ctm(self, x: float, y: float) -> tuple[float, float]:
        """
        Apply current CTM to coordinates.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Tuple of (transformed_x, transformed_y)
        """
        ctm = self.ctm_stack[-1]
        return ctm.transform_point(x, y)

    def apply_ctm_to_points(
        self,
        points: list[tuple[float, float]]
    ) -> list[tuple[float, float]]:
        """
        Apply current CTM to multiple points (batch operation).

        Args:
            points: List of (x, y) coordinate tuples

        Returns:
            List of transformed (x, y) tuples
        """
        ctm = self.ctm_stack[-1]
        return ctm.transform_points(points)

    @property
    def current_ctm(self) -> Matrix:
        """
        Get current CTM.

        Returns:
            Current transformation matrix
        """
        return self.ctm_stack[-1]

    @property
    def depth(self) -> int:
        """
        Get current CTM stack depth.

        Returns:
            Stack depth (1 = viewport only, >1 = nested transforms)
        """
        return len(self.ctm_stack)

    def is_identity(self) -> bool:
        """
        Check if current CTM is identity (no transformation).

        Returns:
            True if current CTM is identity matrix
        """
        return self.current_ctm.is_identity()

    def reset_to_viewport(self):
        """
        Reset CTM stack to viewport matrix only.

        Useful for error recovery.
        """
        if len(self.ctm_stack) > 1:
            self.ctm_stack = [self.ctm_stack[0]]

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"CoordinateSpace(depth={self.depth}, ctm={self.current_ctm})"
