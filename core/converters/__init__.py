#!/usr/bin/env python3
"""
Core Converters for Clean Slate Architecture

Essential converters migrated from legacy src/converters/ for self-contained operation.
"""

# Import only what's actually available
try:
    from .masking import MaskDefinition, MaskingConverter
    _MASKING_AVAILABLE = True
except ImportError:
    _MASKING_AVAILABLE = False

try:
    from .custgeom_generator import CustGeomGenerator
    _CUSTGEOM_AVAILABLE = True
except ImportError:
    _CUSTGEOM_AVAILABLE = False

# Re-export ClippingAnalyzer from groups for backward compatibility
from ..groups.clipping_analyzer import ClippingAnalyzer
from .clippath_types import ClipPathAnalysis, ClipPathComplexity, ClipPathDefinition

__all__ = [
    'ClippingAnalyzer',
    'ClipPathComplexity',
    'ClipPathDefinition',
    'ClipPathAnalysis',
]

if _MASKING_AVAILABLE:
    __all__.extend(['MaskingConverter', 'MaskDefinition'])

if _CUSTGEOM_AVAILABLE:
    __all__.append('CustGeomGenerator')
