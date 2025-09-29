#!/usr/bin/env python3
"""
Core Converters for Clean Slate Architecture

Essential converters migrated from legacy src/converters/ for self-contained operation.
"""

from .image import ImageConverter
from .clippath_analyzer import ClipPathAnalyzer
from .masking import MaskingConverter, MaskDefinition
from .clippath_types import ClipPathComplexity, ClipPathDefinition, ClipPathAnalysis

__all__ = [
    'ImageConverter',
    'ClipPathAnalyzer',
    'MaskingConverter',
    'MaskDefinition',
    'ClipPathComplexity',
    'ClipPathDefinition',
    'ClipPathAnalysis'
]