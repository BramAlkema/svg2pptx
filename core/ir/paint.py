#!/usr/bin/env python3
"""
Paint and stroke definitions for IR

Canonical representation of fill and stroke properties.
Adapts the proven color system from src/color/
"""

from dataclasses import dataclass
from typing import List, Optional, Literal, Union
from enum import Enum
# Use shared numpy compatibility
from .numpy_compat import np, NUMPY_AVAILABLE


@dataclass(frozen=True)
class SolidPaint:
    """Solid color fill"""
    rgb: str  # RRGGBB format (no #)
    opacity: float = 1.0

    def __post_init__(self):
        if not (0.0 <= self.opacity <= 1.0):
            raise ValueError(f"Opacity must be 0.0-1.0, got {self.opacity}")
        if len(self.rgb) != 6:
            raise ValueError(f"RGB must be 6 hex chars, got {self.rgb}")


@dataclass(frozen=True)
class GradientStop:
    """Single gradient stop"""
    offset: float  # 0.0 to 1.0
    rgb: str      # RRGGBB format
    opacity: float = 1.0


@dataclass(frozen=True)
class LinearGradientPaint:
    """Linear gradient fill"""
    stops: List[GradientStop]
    start: tuple  # (x, y) coordinates
    end: tuple    # (x, y) coordinates
    transform: Optional[np.ndarray] = None  # 3x3 matrix

    def __post_init__(self):
        if len(self.stops) < 2:
            raise ValueError("Gradient must have at least 2 stops")


@dataclass(frozen=True)
class RadialGradientPaint:
    """Radial gradient fill"""
    stops: List[GradientStop]
    center: tuple  # (x, y) coordinates
    radius: float
    focal_point: Optional[tuple] = None  # (x, y) coordinates, defaults to center
    transform: Optional[np.ndarray] = None


@dataclass(frozen=True)
class PatternPaint:
    """Pattern fill (fallback to EMF typically)"""
    pattern_id: str
    transform: Optional[np.ndarray] = None


# Union type for all paint types
Paint = Union[SolidPaint, LinearGradientPaint, RadialGradientPaint, PatternPaint, None]


class StrokeJoin(Enum):
    """Stroke line join types"""
    MITER = "miter"
    ROUND = "round"
    BEVEL = "bevel"


class StrokeCap(Enum):
    """Stroke line cap types"""
    BUTT = "butt"
    ROUND = "round"
    SQUARE = "square"


@dataclass(frozen=True)
class Stroke:
    """Stroke properties"""
    paint: Paint
    width: float
    join: StrokeJoin = StrokeJoin.MITER
    cap: StrokeCap = StrokeCap.BUTT
    miter_limit: float = 4.0
    dash_array: Optional[List[float]] = None
    dash_offset: float = 0.0
    opacity: float = 1.0

    def __post_init__(self):
        if self.width < 0:
            raise ValueError(f"Stroke width must be non-negative, got {self.width}")
        if not (0.0 <= self.opacity <= 1.0):
            raise ValueError(f"Stroke opacity must be 0.0-1.0, got {self.opacity}")

    @property
    def is_dashed(self) -> bool:
        """Check if stroke has dash pattern"""
        return self.dash_array is not None and len(self.dash_array) > 0

    @property
    def complexity_score(self) -> int:
        """Complexity score for policy decisions"""
        score = 0
        if self.is_dashed:
            score += 2
        if self.join == StrokeJoin.MITER and self.miter_limit > 10:
            score += 1
        if isinstance(self.paint, (LinearGradientPaint, RadialGradientPaint)):
            score += 1
        return score