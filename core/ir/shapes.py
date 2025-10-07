#!/usr/bin/env python3
"""
Native shape IR types for PowerPoint fidelity

Provides Circle, Ellipse, and Rectangle IR representations that preserve
geometric parameters for native PowerPoint shape output (prstGeom).

These types enable ADR-002 compliance by maintaining separate representations
for different shape types instead of converting everything to paths.
"""

from dataclasses import dataclass, field
from typing import Optional

from .effects import Effect
from .geometry import Point, Rect
from .paint import Paint, Stroke
from .numpy_compat import np


@dataclass
class Circle:
    """Native circle representation for PowerPoint fidelity

    Preserves center point and radius to enable output as native PowerPoint
    ellipse shape (<a:prstGeom prst="ellipse">). Falls back to custom geometry
    path for complex cases (filters, clipping, complex transforms).

    Attributes:
        center: Circle center point in transformed coordinates
        radius: Circle radius in transformed units
        fill: Fill paint (solid, gradient, pattern, or None)
        stroke: Stroke properties (width, color, cap, join, or None)
        opacity: Overall opacity (0.0-1.0)
        effects: List of applied effects (shadows, glows, etc.)

    Note: Coordinates are pre-transformed (baked transforms from Phase 2).
          No transform field - all transformations applied during parsing.
    """
    center: Point
    radius: float
    fill: Optional[Paint] = None
    stroke: Optional[Stroke] = None
    opacity: float = 1.0
    effects: list[Effect] = field(default_factory=list)

    def __post_init__(self):
        """Validate circle parameters"""
        if not (0.0 <= self.opacity <= 1.0):
            raise ValueError(f"Opacity must be 0.0-1.0, got {self.opacity}")
        if self.radius <= 0:
            raise ValueError(f"Radius must be positive, got {self.radius}")

    @property
    def bbox(self) -> Rect:
        """Calculate bounding box"""
        return Rect(
            x=self.center.x - self.radius,
            y=self.center.y - self.radius,
            width=self.radius * 2,
            height=self.radius * 2,
        )

    @property
    def is_closed(self) -> bool:
        """Circles are always closed shapes"""
        return True


@dataclass
class Ellipse:
    """Native ellipse representation for PowerPoint fidelity

    Preserves center point and radii to enable output as native PowerPoint
    ellipse shape. Includes detection for circles (when rx ≈ ry).

    Attributes:
        center: Ellipse center point in transformed coordinates
        radius_x: Horizontal radius in transformed units
        radius_y: Vertical radius in transformed units
        fill: Fill paint (solid, gradient, pattern, or None)
        stroke: Stroke properties (width, color, cap, join, or None)
        opacity: Overall opacity (0.0-1.0)
        effects: List of applied effects (shadows, glows, etc.)

    Note: Coordinates are pre-transformed (baked transforms from Phase 2).
          No transform field - all transformations applied during parsing.
    """
    center: Point
    radius_x: float
    radius_y: float
    fill: Optional[Paint] = None
    stroke: Optional[Stroke] = None
    opacity: float = 1.0
    effects: list[Effect] = field(default_factory=list)

    def __post_init__(self):
        """Validate ellipse parameters"""
        if not (0.0 <= self.opacity <= 1.0):
            raise ValueError(f"Opacity must be 0.0-1.0, got {self.opacity}")
        if self.radius_x <= 0:
            raise ValueError(f"radius_x must be positive, got {self.radius_x}")
        if self.radius_y <= 0:
            raise ValueError(f"radius_y must be positive, got {self.radius_y}")

    @property
    def bbox(self) -> Rect:
        """Calculate bounding box"""
        return Rect(
            x=self.center.x - self.radius_x,
            y=self.center.y - self.radius_y,
            width=self.radius_x * 2,
            height=self.radius_y * 2,
        )

    @property
    def is_closed(self) -> bool:
        """Ellipses are always closed shapes"""
        return True

    def is_circle(self, tolerance: float = 0.01) -> bool:
        """Check if ellipse is actually a circle

        Args:
            tolerance: Maximum relative difference to consider as circle

        Returns:
            True if radius_x ≈ radius_y within tolerance
        """
        if self.radius_x == 0 or self.radius_y == 0:
            return False

        ratio = self.radius_x / self.radius_y
        return abs(ratio - 1.0) < tolerance


@dataclass
class Rectangle:
    """Native rectangle representation for PowerPoint fidelity

    Preserves bounds and corner radius to enable output as native PowerPoint
    rect or roundRect shape (<a:prstGeom prst="rect"> or prst="roundRect">).

    Attributes:
        bounds: Rectangle bounds (x, y, width, height) in transformed coordinates
        fill: Fill paint (solid, gradient, pattern, or None)
        stroke: Stroke properties (width, color, cap, join, or None)
        opacity: Overall opacity (0.0-1.0)
        corner_radius: Corner radius in transformed units (0 = sharp corners)
        effects: List of applied effects (shadows, glows, etc.)

    Note: Coordinates are pre-transformed (baked transforms from Phase 2).
          No transform field - all transformations applied during parsing.
    """
    bounds: Rect
    fill: Optional[Paint] = None
    stroke: Optional[Stroke] = None
    opacity: float = 1.0
    corner_radius: float = 0.0
    effects: list[Effect] = field(default_factory=list)

    def __post_init__(self):
        """Validate rectangle parameters"""
        if not (0.0 <= self.opacity <= 1.0):
            raise ValueError(f"Opacity must be 0.0-1.0, got {self.opacity}")
        if self.bounds.width <= 0:
            raise ValueError(f"Width must be positive, got {self.bounds.width}")
        if self.bounds.height <= 0:
            raise ValueError(f"Height must be positive, got {self.bounds.height}")
        if self.corner_radius < 0:
            raise ValueError(f"corner_radius must be non-negative, got {self.corner_radius}")

    @property
    def bbox(self) -> Rect:
        """Bounding box is the same as bounds"""
        return self.bounds

    @property
    def is_closed(self) -> bool:
        """Rectangles are always closed shapes"""
        return True

    @property
    def is_rounded(self) -> bool:
        """Check if rectangle has rounded corners"""
        return self.corner_radius > 0
