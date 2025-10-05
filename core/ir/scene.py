#!/usr/bin/env python3
"""
Scene graph representation for IR

Core IR types representing the canonical SVG scene graph.
All SVG complexity is preprocessed before reaching this layer.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Literal, Optional, Union

from .geometry import Point, Rect, SegmentType

# Use shared numpy compatibility
from .numpy_compat import np
from .paint import Paint, Stroke
from .text import TextFrame


class ClipStrategy(Enum):
    """Strategy for handling clipping paths"""
    NATIVE = "native"      # Use DrawingML clipping
    BOOLEAN = "boolean"    # Geometric boolean operations
    EMF = "emf"           # Fallback to EMF


@dataclass(frozen=True)
class ClipRef:
    """Reference to a clipping path

    Used when boolean preprocessing cannot resolve clipping geometrically.
    Policy engine decides whether to use native clipping or EMF fallback.
    """
    clip_id: str
    strategy: ClipStrategy = ClipStrategy.NATIVE

    def __post_init__(self):
        if not self.clip_id:
            raise ValueError("Clip ID cannot be empty")


@dataclass(frozen=True)
class ClipRef:
    """Reference to a clipping path definition"""
    clip_id: str  # e.g., "url(#my-clip)" or "#my-clip"


@dataclass(frozen=True)
class Path:
    """Canonical path representation

    All arcs converted to Bezier curves by preprocessors.
    Transforms already applied to coordinates.
    Ready for direct mapping to DrawingML or EMF.
    """
    segments: list[SegmentType]
    fill: Paint = None
    stroke: Stroke | None = None
    clip: ClipRef | None = None
    opacity: float = 1.0
    transform: np.ndarray | None = None  # Identity if None

    def __post_init__(self):
        if not (0.0 <= self.opacity <= 1.0):
            raise ValueError(f"Opacity must be 0.0-1.0, got {self.opacity}")
        if not self.segments:
            raise ValueError("Path must have at least one segment")

    @property
    def bbox(self) -> Rect:
        """Calculate bounding box of all segments"""
        if not self.segments:
            return Rect(0, 0, 0, 0)

        # Get all points from segments
        xs, ys = [], []
        for segment in self.segments:
            if hasattr(segment, 'start'):
                xs.extend([segment.start.x])
                ys.extend([segment.start.y])
            if hasattr(segment, 'end'):
                xs.extend([segment.end.x])
                ys.extend([segment.end.y])
            if hasattr(segment, 'control1'):
                xs.extend([segment.control1.x])
                ys.extend([segment.control1.y])
            if hasattr(segment, 'control2'):
                xs.extend([segment.control2.x])
                ys.extend([segment.control2.y])

        if not xs or not ys:
            return Rect(0, 0, 0, 0)

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        return Rect(min_x, min_y, max_x - min_x, max_y - min_y)

    @property
    def is_closed(self) -> bool:
        """Check if path forms a closed shape"""
        if len(self.segments) < 2:
            return False

        first_point = getattr(self.segments[0], 'start', None)
        last_point = getattr(self.segments[-1], 'end', None)

        if first_point and last_point:
            # Consider closed if endpoints are very close
            dx = abs(first_point.x - last_point.x)
            dy = abs(first_point.y - last_point.y)
            return dx < 0.1 and dy < 0.1

        return False

    @property
    def complexity_score(self) -> int:
        """Complexity score for policy decisions"""
        score = len(self.segments)

        if self.stroke and self.stroke.complexity_score > 0:
            score += self.stroke.complexity_score

        if self.clip:
            score += 3  # Clipping adds complexity

        # Check for complex fills
        if self.fill and hasattr(self.fill, 'stops'):
            score += len(getattr(self.fill, 'stops', []))

        return score

    @property
    def has_complex_features(self) -> bool:
        """Check if path has features that might require EMF"""
        return (
            self.complexity_score > 100 or
            (self.stroke and self.stroke.is_dashed) or
            (self.clip and self.clip.strategy == ClipStrategy.EMF)
        )


@dataclass(frozen=True)
class Group:
    """Container for nested elements

    Represents SVG groups with applied transforms and clipping.
    Children are flattened when possible for optimization.
    """
    children: list[Union['Path', 'TextFrame', 'Group', 'Image']]
    clip: ClipRef | None = None
    opacity: float = 1.0
    transform: np.ndarray | None = None

    def __post_init__(self):
        if not (0.0 <= self.opacity <= 1.0):
            raise ValueError(f"Group opacity must be 0.0-1.0, got {self.opacity}")

    @property
    def bbox(self) -> Rect:
        """Calculate bounding box of all children"""
        if not self.children:
            return Rect(0, 0, 0, 0)

        bboxes = []
        for child in self.children:
            if hasattr(child, 'bbox'):
                bboxes.append(child.bbox)

        if not bboxes:
            return Rect(0, 0, 0, 0)

        min_x = min(bbox.x for bbox in bboxes)
        min_y = min(bbox.y for bbox in bboxes)
        max_x = max(bbox.x + bbox.width for bbox in bboxes)
        max_y = max(bbox.y + bbox.height for bbox in bboxes)

        return Rect(min_x, min_y, max_x - min_x, max_y - min_y)

    @property
    def is_leaf_group(self) -> bool:
        """Check if group contains only primitive elements (no nested groups)"""
        return all(not isinstance(child, Group) for child in self.children)

    @property
    def total_element_count(self) -> int:
        """Count total elements including nested groups"""
        count = len(self.children)
        for child in self.children:
            if isinstance(child, Group):
                count += child.total_element_count
        return count


@dataclass(frozen=True)
class Image:
    """Raster image element

    Represents embedded or referenced images.
    Typically mapped to EMF for best fidelity.
    """
    origin: Point
    size: Rect
    data: bytes                      # Embedded image data
    format: Literal["png", "jpg", "gif", "svg"]
    href: str | None = None       # Image source reference (data URL, file path, or URL)
    clip: ClipRef | None = None
    opacity: float = 1.0
    transform: np.ndarray | None = None

    def __post_init__(self):
        if not (0.0 <= self.opacity <= 1.0):
            raise ValueError(f"Image opacity must be 0.0-1.0, got {self.opacity}")
        if not self.data and not self.href:
            raise ValueError("Image must have either data or href")

    @property
    def bbox(self) -> Rect:
        """Get image bounding box"""
        return Rect(self.origin.x, self.origin.y, self.size.width, self.size.height)


# Type aliases for convenience
IRElement = Union[Path, TextFrame, Group, Image]
SceneGraph = list[IRElement]