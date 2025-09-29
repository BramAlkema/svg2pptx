#!/usr/bin/env python3
"""
SVG Parse Module

Provides SVG parsing and normalization capabilities.
"""

from .parser import SVGParser, ParseResult
from .svg_normalizer import SVGNormalizer as OriginalSVGNormalizer
from .safe_svg_normalization import SafeSVGNormalizer as SVGNormalizer

__all__ = [
    'SVGParser',
    'ParseResult',
    'SVGNormalizer',
    'OriginalSVGNormalizer'
]