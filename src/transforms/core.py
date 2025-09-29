#!/usr/bin/env python3
"""
Core Transform Matrix Implementation for SVG2PPTX

This module provides a clean, dependency-free 2D transformation matrix implementation
extracted from the legacy transforms module. Designed for maximum compatibility and
zero circular dependencies.

Key Features:
- Complete 2D matrix operations (translate, rotate, scale, skew, matrix)
- Matrix composition and decomposition
- Point and multi-point transformation
- Matrix analysis (identity, rotation, scale detection)
- Comprehensive type hints for enhanced IDE support

Usage:
    from src.transforms.core import Matrix

    # Create transformations
    translate = Matrix.translate(10, 20)
    rotate = Matrix.rotate(45)
    scale = Matrix.scale(2, 1.5)

    # Compose transformations
    combined = translate.multiply(rotate).multiply(scale)

    # Transform points
    new_x, new_y = combined.transform_point(100, 100)
"""

import math
from typing import List, Tuple, Optional, Dict


class Matrix:
    """
    2D transformation matrix [a b c d e f] representing:
    [a c e]   [x]   [a*x + c*y + e]
    [b d f] * [y] = [b*x + d*y + f]
    [0 0 1]   [1]   [1]

    Where:
    - a, d: scaling components
    - b, c: shearing/rotation components
    - e, f: translation components

    This implementation provides comprehensive 2D matrix operations with
    mathematical accuracy and performance optimizations.
    """

    def __init__(self, a: float = 1, b: float = 0, c: float = 0,
                 d: float = 1, e: float = 0, f: float = 0) -> None:
        """
        Initialize transformation matrix with standard 2D transform parameters.

        Args:
            a: X-scale component (default: 1)
            b: Y-shear component (default: 0)
            c: X-shear component (default: 0)
            d: Y-scale component (default: 1)
            e: X-translation component (default: 0)
            f: Y-translation component (default: 0)
        """
        self.a = a  # x-scale component
        self.b = b  # y-shear component
        self.c = c  # x-shear component
        self.d = d  # y-scale component
        self.e = e  # x-translate
        self.f = f  # y-translate

    @classmethod
    def identity(cls) -> 'Matrix':
        """
        Create identity matrix (no transformation).

        Returns:
            Identity matrix equivalent to Matrix(1, 0, 0, 1, 0, 0)
        """
        return cls()

    @classmethod
    def translate(cls, tx: float, ty: float = 0) -> 'Matrix':
        """
        Create translation matrix.

        Args:
            tx: Translation along X-axis
            ty: Translation along Y-axis (default: 0)

        Returns:
            Translation matrix
        """
        return cls(1, 0, 0, 1, tx, ty)

    @classmethod
    def scale(cls, sx: float, sy: Optional[float] = None) -> 'Matrix':
        """
        Create scale matrix.

        Args:
            sx: Scale factor along X-axis
            sy: Scale factor along Y-axis (default: same as sx for uniform scaling)

        Returns:
            Scale matrix
        """
        if sy is None:
            sy = sx
        return cls(sx, 0, 0, sy, 0, 0)

    @classmethod
    def rotate(cls, angle_deg: float) -> 'Matrix':
        """
        Create rotation matrix.

        Args:
            angle_deg: Rotation angle in degrees (positive = counterclockwise)

        Returns:
            Rotation matrix
        """
        angle_rad = math.radians(angle_deg)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        return cls(cos_a, sin_a, -sin_a, cos_a, 0, 0)

    @classmethod
    def skew_x(cls, angle_deg: float) -> 'Matrix':
        """
        Create X-axis skew matrix.

        Args:
            angle_deg: Skew angle in degrees

        Returns:
            X-axis skew matrix
        """
        angle_rad = math.radians(angle_deg)
        return cls(1, 0, math.tan(angle_rad), 1, 0, 0)

    @classmethod
    def skew_y(cls, angle_deg: float) -> 'Matrix':
        """
        Create Y-axis skew matrix.

        Args:
            angle_deg: Skew angle in degrees

        Returns:
            Y-axis skew matrix
        """
        angle_rad = math.radians(angle_deg)
        return cls(1, math.tan(angle_rad), 0, 1, 0, 0)

    def multiply(self, other: 'Matrix') -> 'Matrix':
        """
        Multiply this matrix with another matrix (this * other).

        Args:
            other: Matrix to multiply with

        Returns:
            Result of matrix multiplication
        """
        return Matrix(
            self.a * other.a + self.c * other.b,
            self.b * other.a + self.d * other.b,
            self.a * other.c + self.c * other.d,
            self.b * other.c + self.d * other.d,
            self.a * other.e + self.c * other.f + self.e,
            self.b * other.e + self.d * other.f + self.f
        )

    def __matmul__(self, other: 'Matrix') -> 'Matrix':
        """
        Matrix multiplication using @ operator (Python 3.5+).

        Args:
            other: Matrix to multiply with

        Returns:
            Result of matrix multiplication (same as multiply())
        """
        return self.multiply(other)

    def inverse(self) -> Optional['Matrix']:
        """
        Calculate matrix inverse.

        Returns:
            Inverse matrix if matrix is invertible, None otherwise
        """
        det = self.a * self.d - self.b * self.c
        if abs(det) < 1e-10:
            return None  # Non-invertible

        inv_det = 1.0 / det
        return Matrix(
            self.d * inv_det,
            -self.b * inv_det,
            -self.c * inv_det,
            self.a * inv_det,
            (self.c * self.f - self.d * self.e) * inv_det,
            (self.b * self.e - self.a * self.f) * inv_det
        )

    def transform_point(self, x: float, y: float) -> Tuple[float, float]:
        """
        Transform a single point using this matrix.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Tuple of transformed (x, y) coordinates
        """
        new_x = self.a * x + self.c * y + self.e
        new_y = self.b * x + self.d * y + self.f
        return (new_x, new_y)

    def transform_points(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        Transform multiple points using this matrix.

        Args:
            points: List of (x, y) coordinate tuples

        Returns:
            List of transformed (x, y) coordinate tuples
        """
        return [self.transform_point(x, y) for x, y in points]

    def decompose(self) -> Dict[str, float]:
        """
        Decompose matrix into transform components.

        Returns:
            Dictionary with translateX, translateY, scaleX, scaleY, rotation, skewX
        """
        # Translation is straightforward
        translate_x = self.e
        translate_y = self.f

        # Calculate scale and rotation
        scale_x = math.sqrt(self.a * self.a + self.b * self.b)
        scale_y = math.sqrt(self.c * self.c + self.d * self.d)

        # Check if determinant is negative (indicates reflection)
        det = self.a * self.d - self.b * self.c
        if det < 0:
            scale_x = -scale_x

        # Calculate rotation (in degrees)
        rotation = math.degrees(math.atan2(self.b, self.a))

        # Calculate skew
        skew_x = math.degrees(math.atan2(self.a * self.c + self.b * self.d,
                                       scale_x * scale_x))

        return {
            'translateX': translate_x,
            'translateY': translate_y,
            'scaleX': scale_x,
            'scaleY': scale_y,
            'rotation': rotation,
            'skewX': skew_x
        }

    def get_translation(self) -> Tuple[float, float]:
        """
        Get translation components.

        Returns:
            Tuple of (translateX, translateY)
        """
        return (self.e, self.f)

    def get_scale(self) -> Tuple[float, float]:
        """
        Get scale components.

        Returns:
            Tuple of (scaleX, scaleY)
        """
        scale_x = math.sqrt(self.a * self.a + self.b * self.b)
        scale_y = math.sqrt(self.c * self.c + self.d * self.d)
        return (scale_x, scale_y)

    def get_rotation(self) -> float:
        """
        Get rotation angle in degrees.

        Returns:
            Rotation angle in degrees
        """
        return math.degrees(math.atan2(self.b, self.a))

    def is_identity(self, tolerance: float = 1e-6) -> bool:
        """
        Check if this is an identity matrix.

        Args:
            tolerance: Numerical tolerance for comparison

        Returns:
            True if matrix is identity within tolerance
        """
        return (abs(self.a - 1) < tolerance and abs(self.b) < tolerance and
                abs(self.c) < tolerance and abs(self.d - 1) < tolerance and
                abs(self.e) < tolerance and abs(self.f) < tolerance)

    def is_translation_only(self, tolerance: float = 1e-6) -> bool:
        """
        Check if this is a pure translation matrix (no scale, rotation, or skew).

        Args:
            tolerance: Numerical tolerance for comparison

        Returns:
            True if matrix contains only translation
        """
        return (abs(self.a - 1) < tolerance and abs(self.b) < tolerance and
                abs(self.c) < tolerance and abs(self.d - 1) < tolerance)

    def has_rotation(self, tolerance: float = 1e-6) -> bool:
        """
        Check if matrix contains rotation or shear.

        Args:
            tolerance: Numerical tolerance for comparison

        Returns:
            True if matrix contains rotation or shear
        """
        return abs(self.b) > tolerance or abs(self.c) > tolerance

    def has_scale(self, tolerance: float = 1e-6) -> bool:
        """
        Check if matrix contains scaling.

        Args:
            tolerance: Numerical tolerance for comparison

        Returns:
            True if matrix contains scaling
        """
        # Calculate the determinant of the linear part (excluding translation)
        det = abs(self.a * self.d - self.b * self.c)
        # For pure rotation/reflection, determinant should be ±1
        # For scaling, determinant will be different from 1
        return abs(det - 1) > tolerance

    def __str__(self) -> str:
        """String representation of matrix."""
        return f"matrix({self.a}, {self.b}, {self.c}, {self.d}, {self.e}, {self.f})"

    def __repr__(self) -> str:
        """Detailed string representation of matrix."""
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        """Check matrix equality."""
        if not isinstance(other, Matrix):
            return False
        return (self.a == other.a and self.b == other.b and self.c == other.c and
                self.d == other.d and self.e == other.e and self.f == other.f)