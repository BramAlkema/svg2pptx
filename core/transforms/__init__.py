#!/usr/bin/env python3
"""
Transform System for SVG2PPTX

Provides matrix composition, CTM propagation, and coordinate transformation
for proper SVG viewport mapping to PowerPoint EMU coordinates.
"""

from .core import Matrix
from .engine import TransformEngine
from .matrix_composer import (
    element_ctm,
    needs_normalise,
    normalise_content_matrix,
    parse_preserve_aspect_ratio,
    parse_viewbox,
    viewport_matrix,
)
from .parser import TransformParser

__all__ = [
    'viewport_matrix',
    'element_ctm',
    'normalise_content_matrix',
    'needs_normalise',
    'parse_viewbox',
    'parse_preserve_aspect_ratio',
    'TransformEngine',
    'Matrix',
    'TransformParser',
]