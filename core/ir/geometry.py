#!/usr/bin/env python3
"""
Geometric primitives for IR

Core geometric types used throughout the IR.
Uses proven numpy arrays for transforms and coordinates.
"""

from dataclasses import dataclass
from typing import Union

# Use shared numpy compatibility
from .numpy_compat import np


@dataclass(frozen=True)
class Point:
    """2D point in user coordinates"""
    x: float
    y: float

    def __iter__(self):
        """Allow unpacking: x, y = point"""
        yield self.x
        yield self.y

    def transform(self, matrix: np.ndarray) -> 'Point':
        """Apply 3x3 transformation matrix"""
        vec = np.array([self.x, self.y, 1.0])
        transformed = matrix @ vec
        return Point(transformed[0], transformed[1])


@dataclass(frozen=True)
class Rect:
    """Axis-aligned bounding rectangle"""
    x: float
    y: float
    width: float
    height: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def top(self) -> float:
        return self.y

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center(self) -> Point:
        return Point(self.x + self.width / 2, self.y + self.height / 2)

    def contains(self, point: Point) -> bool:
        """Check if point is inside rectangle"""
        return (self.left <= point.x <= self.right and
                self.top <= point.y <= self.bottom)

    def intersects(self, other: 'Rect') -> bool:
        """Check if rectangles intersect"""
        return not (self.right < other.left or
                   self.left > other.right or
                   self.bottom < other.top or
                   self.top > other.bottom)


@dataclass(frozen=True)
class Segment:
    """Base class for path segments"""
    pass


@dataclass(frozen=True)
class LineSegment(Segment):
    """Straight line segment"""
    start: Point
    end: Point

    def length(self) -> float:
        """Calculate segment length"""
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        return np.sqrt(dx * dx + dy * dy)


@dataclass(frozen=True)
class BezierSegment(Segment):
    """Cubic Bezier curve segment

    All arcs are converted to Bezier curves by preprocessors.
    Uses the proven a2c conversion from src/paths/a2c.py
    """
    start: Point
    control1: Point
    control2: Point
    end: Point

    def length_approx(self) -> float:
        """Approximate curve length using control polygon"""
        # Quick approximation for complexity decisions
        d1 = np.sqrt((self.control1.x - self.start.x)**2 + (self.control1.y - self.start.y)**2)
        d2 = np.sqrt((self.control2.x - self.control1.x)**2 + (self.control2.y - self.control1.y)**2)
        d3 = np.sqrt((self.end.x - self.control2.x)**2 + (self.end.y - self.control2.y)**2)
        return d1 + d2 + d3

    def bbox(self) -> Rect:
        """Calculate bounding box (conservative estimate)"""
        xs = [self.start.x, self.control1.x, self.control2.x, self.end.x]
        ys = [self.start.y, self.control1.y, self.control2.y, self.end.y]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        return Rect(min_x, min_y, max_x - min_x, max_y - min_y)


# Type alias for convenience
SegmentType = Union[LineSegment, BezierSegment]