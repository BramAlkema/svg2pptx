#!/usr/bin/env python3
"""
WordArt Transform Service

Leverages existing Matrix infrastructure to decompose SVG transformations
into PowerPoint-compatible components for WordArt mapping.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from lxml import etree as ET

from src.transforms import Matrix
from ..transforms.engine import TransformEngine
from ..utils.transform_utils import get_transform_safe


@dataclass
class TransformComponents:
    """Decomposed transform components for PowerPoint mapping."""

    # Translation components
    translate_x: float = 0.0
    translate_y: float = 0.0

    # Rotation in degrees
    rotation_deg: float = 0.0

    # Scale components
    scale_x: float = 1.0
    scale_y: float = 1.0

    # Skew in degrees
    skew_x_deg: float = 0.0

    # PowerPoint compatibility flags
    flip_h: bool = False
    flip_v: bool = False

    @property
    def has_skew(self) -> bool:
        """Check if transform has skew components."""
        return abs(self.skew_x_deg) > 0.1

    @property
    def max_skew_angle(self) -> float:
        """Get skew angle for policy decisions."""
        return abs(self.skew_x_deg)

    @property
    def has_negative_scale(self) -> bool:
        """Check if original transform had negative scales."""
        return self.flip_h or self.flip_v

    @property
    def scale_ratio(self) -> float:
        """Get scale aspect ratio (max/min)."""
        if min(abs(self.scale_x), abs(self.scale_y)) == 0:
            return float('inf')
        return max(abs(self.scale_x), abs(self.scale_y)) / min(abs(self.scale_x), abs(self.scale_y))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for policy decisions."""
        return {
            'translate': (self.translate_x, self.translate_y),
            'rotate': self.rotation_deg,
            'scale_x': self.scale_x,
            'scale_y': self.scale_y,
            'skew_x': self.skew_x_deg,
            'flip_h': self.flip_h,
            'flip_v': self.flip_v,
            'max_skew': self.max_skew_angle,
            'scale_ratio': self.scale_ratio
        }


class SVGTransformDecomposer:
    """
    Decomposes SVG transformations using existing Matrix infrastructure.

    Leverages the proven Matrix.decompose() method for reliable transform analysis.
    """

    def __init__(self):
        """Initialize decomposer with transform engine."""
        self.engine = TransformEngine()

    def decompose_element_transform(self, element: ET.Element) -> TransformComponents:
        """
        Decompose transform attribute from SVG element.

        Args:
            element: SVG element with optional transform attribute

        Returns:
            TransformComponents with decomposed values
        """
        transform_str = get_transform_safe(element)
        if not transform_str:
            return TransformComponents()

        return self.decompose_transform_string(transform_str)

    def decompose_transform_string(self, transform_str: str) -> TransformComponents:
        """
        Decompose SVG transform string using existing Matrix infrastructure.

        Args:
            transform_str: SVG transform string

        Returns:
            TransformComponents with decomposed values
        """
        try:
            # Use existing engine to parse transform
            matrix = self.engine.parse_to_matrix(transform_str)

            # Use existing decompose method
            decomposed = matrix.decompose()

            # Handle negative scales as flips for PowerPoint compatibility
            flip_h = decomposed['scaleX'] < 0
            flip_v = decomposed['scaleY'] < 0

            return TransformComponents(
                translate_x=decomposed['translateX'],
                translate_y=decomposed['translateY'],
                rotation_deg=decomposed['rotation'],
                scale_x=abs(decomposed['scaleX']),
                scale_y=abs(decomposed['scaleY']),
                skew_x_deg=decomposed['skewX'],
                flip_h=flip_h,
                flip_v=flip_v
            )

        except Exception:
            # Fallback to identity transform
            return TransformComponents()

    def decompose_matrix(self, matrix) -> TransformComponents:
        """
        Decompose matrix using existing Matrix infrastructure.

        Args:
            matrix: Matrix object or numpy array

        Returns:
            TransformComponents with decomposed values
        """
        try:
            # Convert numpy array to Matrix if needed
            if hasattr(matrix, 'shape'):  # numpy array
                # Convert 2x3 or 3x3 numpy array to Matrix
                if matrix.shape == (2, 3):
                    matrix_obj = Matrix(
                        matrix[0, 0], matrix[1, 0], matrix[0, 1],
                        matrix[1, 1], matrix[0, 2], matrix[1, 2]
                    )
                elif matrix.shape == (3, 3):
                    matrix_obj = Matrix(
                        matrix[0, 0], matrix[1, 0], matrix[0, 1],
                        matrix[1, 1], matrix[0, 2], matrix[1, 2]
                    )
                else:
                    return TransformComponents()
            else:
                # Already a Matrix object
                matrix_obj = matrix

            # Use existing decompose method
            decomposed = matrix_obj.decompose()

            # Handle negative scales as flips
            flip_h = decomposed['scaleX'] < 0
            flip_v = decomposed['scaleY'] < 0

            return TransformComponents(
                translate_x=decomposed['translateX'],
                translate_y=decomposed['translateY'],
                rotation_deg=decomposed['rotation'],
                scale_x=abs(decomposed['scaleX']),
                scale_y=abs(decomposed['scaleY']),
                skew_x_deg=decomposed['skewX'],
                flip_h=flip_h,
                flip_v=flip_v
            )

        except Exception:
            return TransformComponents()

    def analyze_transform_complexity(self, components: TransformComponents) -> Dict[str, Any]:
        """
        Analyze transform complexity for policy decisions.

        Args:
            components: Decomposed transform components

        Returns:
            Dictionary with complexity analysis
        """
        complexity_score = 0
        issues = []

        # Skew complexity
        if components.has_skew:
            complexity_score += 3
            issues.append(f"skew_{components.max_skew_angle:.1f}deg")

        # Scale ratio complexity
        if components.scale_ratio > 3.0:
            complexity_score += 2
            issues.append(f"scale_ratio_{components.scale_ratio:.1f}")

        # Rotation complexity (non-orthogonal angles)
        rot_mod_90 = abs(components.rotation_deg) % 90
        if rot_mod_90 > 5 and rot_mod_90 < 85:
            complexity_score += 1
            issues.append("non_orthogonal_rotation")

        return {
            'complexity_score': complexity_score,
            'issues': issues,
            'can_wordart_native': complexity_score < 5,
            'recommend_outline': complexity_score >= 5,
            'max_skew_exceeded': components.max_skew_angle > 18.0
        }


def create_transform_decomposer() -> SVGTransformDecomposer:
    """
    Factory function to create transform decomposer.

    Returns:
        SVGTransformDecomposer instance
    """
    return SVGTransformDecomposer()