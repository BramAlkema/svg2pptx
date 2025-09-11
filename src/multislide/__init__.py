"""
Multi-slide PowerPoint generation framework.

This module provides infrastructure for generating PowerPoint presentations
with multiple slides from complex SVG documents, animation sequences,
and batch conversions.
"""

from .document import MultiSlideDocument, SlideContent
from .detection import SlideDetector, SlideBoundary, SlideType
from .templates import SlideTemplate, SlideLayout

__all__ = [
    'MultiSlideDocument',
    'SlideContent', 
    'SlideDetector',
    'SlideBoundary',
    'SlideType',
    'SlideTemplate',
    'SlideLayout'
]