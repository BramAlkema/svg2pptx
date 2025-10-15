"""
Public API for the sliced parser package.

This module intentionally re-exports the building blocks that now live under
`core.parse_split` so callers can import them without drilling into the
individual submodules.
"""

from .clip_parser import ClipPathExtractor
from .constants import (
    FONT_WEIGHT_BOLD_THRESHOLD,
    MAX_SIMPLE_PATH_SEGMENTS,
    MIN_PATH_COORDS_FOR_ARC,
    MIN_PATH_COORDS_FOR_CURVE,
    MIN_PATH_COORDS_FOR_CUBIC,
    MIN_PATH_COORDS_FOR_LINE,
)
from .element_traversal import ElementTraversal
from .hyperlink_processor import HyperlinkProcessor
from .ir_converter import IRConverter
from .models import ClipDefinition, ParseResult
from .style_context import StyleContextBuilder
from .validator import SVGValidator
from .xml_parser import XMLParser

__all__ = [
    "ClipDefinition",
    "ClipPathExtractor",
    "ElementTraversal",
    "FONT_WEIGHT_BOLD_THRESHOLD",
    "HyperlinkProcessor",
    "IRConverter",
    "MAX_SIMPLE_PATH_SEGMENTS",
    "MIN_PATH_COORDS_FOR_ARC",
    "MIN_PATH_COORDS_FOR_CURVE",
    "MIN_PATH_COORDS_FOR_CUBIC",
    "MIN_PATH_COORDS_FOR_LINE",
    "ParseResult",
    "StyleContextBuilder",
    "SVGValidator",
    "XMLParser",
]
