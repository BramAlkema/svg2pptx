#!/usr/bin/env python3
"""
CSS Utilities

Provides helpers for parsing and resolving CSS declarations so that styling
logic can be shared across the conversion pipeline.
"""

from .resolver import (
    StyleResolver,
    StyleContext,
    parse_color,
    parse_font_size,
    normalize_font_weight,
)
from .animation_extractor import CSSAnimationExtractor

__all__ = [
    "StyleResolver",
    "StyleContext",
    "parse_color",
    "parse_font_size",
    "normalize_font_weight",
    "CSSAnimationExtractor",
]
