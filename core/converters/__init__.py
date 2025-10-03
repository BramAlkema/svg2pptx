#!/usr/bin/env python3
"""
Core Converters for Clean Slate Architecture

Essential converters migrated from legacy src/converters/ for self-contained operation.
"""

# Import only what's actually available
try:
    from .image import ImageConverter
    _IMAGE_AVAILABLE = True
except ImportError:
    _IMAGE_AVAILABLE = False

try:
    from .masking import MaskingConverter, MaskDefinition
    _MASKING_AVAILABLE = True
except ImportError:
    _MASKING_AVAILABLE = False

from .clippath_types import ClipPathComplexity, ClipPathDefinition, ClipPathAnalysis

# Re-export ClippingAnalyzer from groups for backward compatibility
from ..groups.clipping_analyzer import ClippingAnalyzer

__all__ = [
    'ClippingAnalyzer',
    'ClipPathComplexity',
    'ClipPathDefinition',
    'ClipPathAnalysis'
]

if _IMAGE_AVAILABLE:
    __all__.append('ImageConverter')

if _MASKING_AVAILABLE:
    __all__.extend(['MaskingConverter', 'MaskDefinition'])