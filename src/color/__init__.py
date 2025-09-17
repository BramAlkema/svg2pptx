#!/usr/bin/env python3
"""
Modern Color System for SVG2PPTX

This package provides a fluent, chainable color API using NumPy and colorspacious
for accurate color science operations while maintaining backwards compatibility.

Key Features:
- Fluent API: Color('#ff0000').darken(0.2).saturate(1.5).hex()
- Professional color science via colorspacious
- 5-10x performance improvements through NumPy vectorization
- Complete backwards compatibility with existing ColorParser/ColorInfo

Example Usage:
    from svg2pptx.color import Color

    # Basic fluent operations
    result = Color('#3498db').darken(0.1).saturate(0.2).hex()

    # Color harmony generation
    palette = Color('#ff6b6b').analogous(count=5)

    # Accessibility compliance
    accessible = Color('#ff0000').find_accessible_contrast('#ffffff')

    # Advanced color science
    delta_e = Color('#ff0000').delta_e(Color('#ff3333'))
"""

# Core Color class - primary public API
from .core import Color

# Utility classes for specific use cases
from .batch import ColorBatch
from .harmony import ColorHarmony

# Advanced features
from .accessibility import ColorAccessibility, ContrastLevel, ColorBlindnessType
from .manipulation import ColorManipulation, BlendMode

# Legacy compatibility - maintain existing interfaces
from ..colors import ColorParser, ColorInfo

# Export main public API
__all__ = [
    # Primary modern API
    'Color',

    # Specialized utilities
    'ColorBatch',
    'ColorHarmony',

    # Advanced features
    'ColorAccessibility',
    'ContrastLevel',
    'ColorBlindnessType',
    'ColorManipulation',
    'BlendMode',

    # Legacy compatibility
    'ColorParser',
    'ColorInfo',
]

# Version info
__version__ = '2.0.0'
__author__ = 'SVG2PPTX Team'