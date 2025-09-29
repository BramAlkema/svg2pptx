#!/usr/bin/env python3
"""
Legacy Adapters for SVG2PPTX

Thin wrappers around proven legacy components to preserve battle-tested logic
while providing clean interfaces for the new core architecture.

Key principles:
- Minimal wrapper overhead
- Preserve proven performance characteristics
- Clean interfaces hiding legacy complexity
- Easy migration path to new implementations
"""

from .legacy_text import *
from .legacy_paths import *
from .legacy_color import *
from .legacy_io import *

__all__ = [
    # Text adapter
    "LegacyTextAdapter", "TextStyleResolver", "FontMetricsAdapter",

    # Path adapter
    "LegacyPathAdapter", "A2CAdapter", "DrawingMLAdapter",

    # Color adapter
    "LegacyColorAdapter", "ColorSystemAdapter",

    # I/O adapter
    "LegacyIOAdapter", "PPTXBuilderAdapter",
]