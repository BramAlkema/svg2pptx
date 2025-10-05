#!/usr/bin/env python3
"""
Intermediate Representation (IR) for SVG2PPTX

Pure data structures representing a canonical SVG scene graph.
All SVG complexity is normalized before reaching the IR layer.

Key principles:
- Immutable data structures
- No DOM references
- Serializable and testable
- Battle-tested math (transforms, coordinates) preserved
"""

from .font_metadata import *
from .geometry import *
from .paint import *
from .scene import *
from .text import *
from .text_path import *
from .validation import *

__all__ = [
    # Core scene graph
    "Path", "TextFrame", "Group", "Image", "IRElement", "SceneGraph",

    # Geometry primitives
    "Point", "Rect", "Segment", "BezierSegment", "LineSegment",

    # Paint and styling
    "Paint", "SolidPaint", "LinearGradientPaint", "RadialGradientPaint", "PatternPaint",
    "GradientStop",
    "Stroke", "StrokeJoin", "StrokeCap",

    # Text components
    "Run", "EnhancedRun", "TextAnchor", "TextLine", "RichTextFrame",

    # TextPath components
    "TextPathFrame", "TextPathLayout", "PathPoint", "CharacterPlacement",
    "TextPathMethod", "TextPathSpacing", "TextPathSide",
    "create_text_path_frame", "create_simple_text_path",

    # Font metadata
    "FontMetadata", "FontStrategy", "FontAvailability", "FontAnalysisResult",
    "FontMetrics", "FontWeight", "create_font_metadata", "parse_font_weight",

    # Clipping
    "ClipRef", "ClipStrategy",

    # Validation
    "validate_ir", "IRValidationError",
]