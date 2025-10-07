#!/usr/bin/env python3
"""
Shape policy engine for native PowerPoint shape decisions

Determines whether simple shapes (Circle, Ellipse, Rectangle) should use:
- Native PowerPoint preset shapes (<a:prstGeom prst="ellipse">)
- Custom geometry paths (<a:custGeom> with Bezier curves)

Decision factors:
- Transform complexity (rotation, skew disqualify native shapes)
- Filter effects (filters require custom geometry)
- Clipping paths (clipping requires custom geometry)
- Stroke complexity (dash patterns may require custom geometry)
"""

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from ..ir.shapes import Circle, Ellipse, Rectangle
from .targets import DecisionReason, PolicyDecision


@dataclass(frozen=True)
class ShapeDecision(PolicyDecision):
    """Policy decision for native shape elements

    Extends PolicyDecision with shape-specific metadata for tracing
    and debugging policy decisions.

    Attributes:
        use_native: True for DrawingML output (preset or custom)
        reasons: List of DecisionReason explaining the decision
        shape_type: Type of shape ('circle', 'ellipse', 'rectangle')
        use_preset: True for native PowerPoint shapes (prstGeom)
        preset_name: PowerPoint preset name ('ellipse', 'rect', 'roundRect')
        complexity_score: Numeric complexity score (higher = more complex)
        has_filters: True if shape has filter effects
        has_clipping: True if shape has clipping path

    Note: has_complex_transform removed in Phase 2 (baked transforms).
          All transforms are applied during parsing, shapes never have transforms.
    """
    # Shape-specific fields (all must have defaults due to parent class)
    shape_type: str = "unknown"
    use_preset: bool = False
    preset_name: Optional[str] = None
    complexity_score: int = 0
    has_filters: bool = False
    has_clipping: bool = False

    @classmethod
    def preset(
        cls,
        shape_type: str,
        preset_name: str,
        reasons: list[DecisionReason],
        **kwargs
    ) -> 'ShapeDecision':
        """Create decision for native preset shape

        Args:
            shape_type: Type of shape ('circle', 'ellipse', 'rectangle')
            preset_name: PowerPoint preset ('ellipse', 'rect', 'roundRect')
            reasons: List of reasons for using preset
            **kwargs: Additional metadata

        Returns:
            ShapeDecision with use_native=True, use_preset=True
        """
        return cls(
            use_native=True,
            use_preset=True,
            shape_type=shape_type,
            preset_name=preset_name,
            reasons=reasons,
            **kwargs
        )

    @classmethod
    def custom_geometry(
        cls,
        shape_type: str,
        reasons: list[DecisionReason],
        **kwargs
    ) -> 'ShapeDecision':
        """Create decision for custom geometry fallback

        Args:
            shape_type: Type of shape ('circle', 'ellipse', 'rectangle')
            reasons: List of reasons for using custom geometry
            **kwargs: Additional metadata (complexity_score, feature flags)

        Returns:
            ShapeDecision with use_native=True, use_preset=False
        """
        return cls(
            use_native=True,
            use_preset=False,
            shape_type=shape_type,
            preset_name=None,
            reasons=reasons,
            **kwargs
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize ShapeDecision to dictionary for tracing

        Returns:
            Dictionary with all decision metadata
        """
        base_dict = {
            'use_native': self.use_native,
            'use_preset': self.use_preset,
            'shape_type': self.shape_type,
            'preset_name': self.preset_name,
            'reasons': [r.value for r in self.reasons],
            'complexity_score': self.complexity_score,
        }

        # Add feature flags if present
        # Note: has_complex_transform removed in Phase 2 (baked transforms)
        if self.has_filters:
            base_dict['has_filters'] = True
        if self.has_clipping:
            base_dict['has_clipping'] = True

        return base_dict


def decide_shape_strategy(
    shape: Circle | Ellipse | Rectangle,
    context: Optional[Any] = None
) -> ShapeDecision:
    """
    Determine if shape can use native PowerPoint preset geometry.

    Analyzes shape complexity and context to decide between:
    1. Native preset shape (prstGeom) - best fidelity and performance
    2. Custom geometry path (custGeom) - fallback for complex cases

    Decision logic:
    - Check for complex transforms (rotation, skew) → custom geometry
    - Check for filter effects → custom geometry
    - Check for clipping paths → custom geometry
    - Simple shapes with translate/scale only → native preset

    Args:
        shape: Circle, Ellipse, or Rectangle IR object
        context: Optional conversion context with filters/clipping info

    Returns:
        ShapeDecision indicating preset vs custom geometry with reasons

    Examples:
        >>> circle = Circle(center=Point(0, 0), radius=10)
        >>> decision = decide_shape_strategy(circle)
        >>> assert decision.use_preset is True
        >>> assert decision.preset_name == 'ellipse'

        Note: Transform checking removed in Phase 2 (baked transforms).
              All coordinates are pre-transformed during parsing, so shapes
              never have complex transforms at this point.
    """
    reasons = []
    complexity_score = 0

    # Phase 2 Note: Transform check removed - all transforms are baked during parsing.
    # Shapes in IR already have transformed coordinates, no transform field exists.

    # Check for filter effects in context
    if context and hasattr(context, 'filters') and context.filters:
        reasons.append(DecisionReason.UNSUPPORTED_FEATURES)
        complexity_score += 20
        return ShapeDecision.custom_geometry(
            type(shape).__name__.lower(),
            reasons,
            has_filters=True,
            complexity_score=complexity_score,
        )

    # Check for clipping paths in context
    if context and hasattr(context, 'clip') and context.clip:
        reasons.append(DecisionReason.CLIPPING_COMPLEX)
        complexity_score += 15
        return ShapeDecision.custom_geometry(
            type(shape).__name__.lower(),
            reasons,
            has_clipping=True,
            complexity_score=complexity_score,
        )

    # Qualified for native preset shape
    reasons.append(DecisionReason.NATIVE_PRESET_AVAILABLE)
    reasons.append(DecisionReason.SIMPLE_GEOMETRY)

    # Map shape types to PowerPoint preset names
    if isinstance(shape, Circle):
        return ShapeDecision.preset('circle', 'ellipse', reasons)

    elif isinstance(shape, Ellipse):
        return ShapeDecision.preset('ellipse', 'ellipse', reasons)

    elif isinstance(shape, Rectangle):
        # Choose between rect and roundRect based on corner_radius
        preset = 'roundRect' if shape.corner_radius > 0 else 'rect'
        return ShapeDecision.preset('rectangle', preset, reasons)

    # Fallback (should never reach here with proper typing)
    reasons = [DecisionReason.UNSUPPORTED_FEATURES]
    return ShapeDecision.custom_geometry('unknown', reasons, complexity_score=100)


def _is_simple_transform(matrix: np.ndarray) -> bool:
    """DEPRECATED: Check if transform is simple (Phase 2 baked transforms)

    This function is no longer used in Phase 2 architecture where all transforms
    are baked during parsing. Shapes in IR never have transform fields.

    Kept for backward compatibility only. Always returns True since shapes
    arriving at this point have already had transforms applied.

    Args:
        matrix: 3x3 transformation matrix (deprecated, unused)

    Returns:
        True (always, since transforms are pre-applied)

    Note: In Phase 2, all transformations are applied during SVG parsing,
          so shapes never have transform matrices at the decision point.
    """
    # Phase 2: All transforms are baked, this function is obsolete
    return True
