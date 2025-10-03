#!/usr/bin/env python3
"""
Scene graph representation for IR

Core IR types representing the canonical SVG scene graph.
All SVG complexity is preprocessed before reaching this layer.
"""

from dataclasses import dataclass
from typing import List, Optional, Union, Literal, TYPE_CHECKING
from enum import Enum

# Use shared numpy compatibility
from .numpy_compat import np, NUMPY_AVAILABLE

from .geometry import Point, Rect, SegmentType
from .paint import Paint, Stroke
from .text import TextFrame

# Import navigation types for type annotation only
if TYPE_CHECKING:
    from ..pipeline.hyperlinks import HyperlinkSpec
    from ..pipeline.navigation import NavigationSpec


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
    Supports SVG filter effects via filter reference.
    """
    segments: List[SegmentType]
    fill: Paint = None
    stroke: Optional[Stroke] = None
    clip: Optional[ClipRef] = None
    opacity: float = 1.0
    transform: Optional[np.ndarray] = None  # Identity if None
    hyperlink: Optional['HyperlinkSpec'] = None  # Legacy hyperlink support (deprecated)
    navigation: Optional['NavigationSpec'] = None  # Enhanced navigation support
    id: Optional[str] = None  # Original SVG element ID for tracing
    filter: Optional[str] = None  # SVG filter reference, e.g., "url(#blur)" or "#blur"

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
    Supports SVG filter effects applied to entire group.
    """
    children: List[Union['Path', 'TextFrame', 'Group', 'Image']]
    clip: Optional[ClipRef] = None
    opacity: float = 1.0
    transform: Optional[np.ndarray] = None
    hyperlink: Optional['HyperlinkSpec'] = None  # Legacy hyperlink support (deprecated)
    navigation: Optional['NavigationSpec'] = None  # Enhanced navigation support
    id: Optional[str] = None  # Original SVG element ID for tracing
    filter: Optional[str] = None  # SVG filter reference, applies to all children

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
    Typically mapped to DrawingML <p:pic> with media embedding.
    Supports SVG filter effects applied to image.
    """
    # Source information
    href: str                           # Original href (data:, file:, http://)
    source_type: str                    # "data_url" | "file" | "http" | "https"

    # Format information
    mime_type: str                      # "image/png", "image/jpeg", etc.
    format_ext: str                     # "png", "jpg", etc. (for file naming)

    # Dimensions (SVG units)
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

    # Optional data (populated for data URLs or after loading)
    image_data: Optional[bytes] = None  # Raw image bytes

    # Metadata
    title: Optional[str] = None
    desc: Optional[str] = None
    sha256: Optional[str] = None        # For deduplication

    # Styling
    clip: Optional[ClipRef] = None
    opacity: float = 1.0
    transform: Optional[np.ndarray] = None

    # Navigation
    hyperlink: Optional['HyperlinkSpec'] = None  # Legacy hyperlink support (deprecated)
    navigation: Optional['NavigationSpec'] = None  # Enhanced navigation support

    # Filter effects
    filter: Optional[str] = None        # SVG filter reference

    # Legacy fields for backward compatibility
    origin: Optional[Point] = None      # Deprecated: use x, y instead
    size: Optional[Rect] = None         # Deprecated: use width, height instead
    data: Optional[bytes] = None        # Deprecated: use image_data instead
    format: Optional[Literal["png", "jpg", "gif", "svg"]] = None  # Deprecated: use format_ext

    def __post_init__(self):
        if not (0.0 <= self.opacity <= 1.0):
            raise ValueError(f"Image opacity must be 0.0-1.0, got {self.opacity}")
        if not self.href:
            raise ValueError("Image must have href")

    @property
    def bbox(self) -> Rect:
        """Get image bounding box"""
        return Rect(self.x, self.y, self.width, self.height)


# Type aliases for convenience
IRElement = Union[Path, TextFrame, Group, Image]
SceneGraph = List[IRElement]


# Navigation conversion utilities for backward compatibility

def get_effective_navigation(element: IRElement) -> Optional['NavigationSpec']:
    """
    Get the effective navigation for an IR element.

    Prefers NavigationSpec over HyperlinkSpec for enhanced features,
    but converts HyperlinkSpec to NavigationSpec if only legacy format is available.

    Args:
        element: IR element to extract navigation from

    Returns:
        NavigationSpec if navigation is available, None otherwise
    """
    # Check if element has navigation field
    if hasattr(element, 'navigation') and element.navigation is not None:
        return element.navigation

    # Fall back to converting hyperlink to navigation
    if hasattr(element, 'hyperlink') and element.hyperlink is not None:
        from ..pipeline.navigation import navigation_from_hyperlink_spec
        return navigation_from_hyperlink_spec(element.hyperlink)

    return None


def has_navigation(element: IRElement) -> bool:
    """
    Check if an IR element has any navigation (new or legacy format).

    Args:
        element: IR element to check

    Returns:
        True if element has navigation, False otherwise
    """
    return get_effective_navigation(element) is not None


def update_element_navigation(element: IRElement, navigation_spec: 'NavigationSpec') -> IRElement:
    """
    Create a new IR element with updated navigation.

    Sets the NavigationSpec and clears the legacy HyperlinkSpec to avoid conflicts.

    Args:
        element: Original IR element
        navigation_spec: New NavigationSpec to apply

    Returns:
        New IR element with updated navigation

    Raises:
        ValueError: If element type is not supported
    """
    if isinstance(element, Path):
        return element.__class__(
            segments=element.segments,
            fill=element.fill,
            stroke=element.stroke,
            clip=element.clip,
            opacity=element.opacity,
            transform=element.transform,
            hyperlink=None,  # Clear legacy field
            navigation=navigation_spec
        )
    elif isinstance(element, Group):
        return element.__class__(
            children=element.children,
            clip=element.clip,
            opacity=element.opacity,
            transform=element.transform,
            hyperlink=None,  # Clear legacy field
            navigation=navigation_spec
        )
    elif isinstance(element, Image):
        return element.__class__(
            origin=element.origin,
            size=element.size,
            data=element.data,
            format=element.format,
            href=element.href,
            clip=element.clip,
            opacity=element.opacity,
            transform=element.transform,
            hyperlink=None,  # Clear legacy field
            navigation=navigation_spec
        )
    elif hasattr(element, 'navigation'):  # TextFrame or other types
        # Use dataclasses.replace for generic dataclass update
        from dataclasses import replace
        return replace(element, hyperlink=None, navigation=navigation_spec)
    else:
        raise ValueError(f"Unsupported element type for navigation update: {type(element)}")