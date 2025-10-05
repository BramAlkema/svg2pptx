"""
ViewBox and Viewport System for SVG2PPTX.

Core viewport resolution system with high-performance vectorized operations.
Eliminates confusing NumPy naming while maintaining performance benefits.
"""

# Import core classes for performance
from .core import (
    AspectAlign,
    MeetOrSlice,
    ViewBoxArray,
    ViewportArray,
    ViewportEngine,
    ViewportMappingArray,
)

# Modern imports - no aliases needed

__all__ = [
    # Core classes
    'ViewportEngine', 'ViewBoxArray', 'ViewportArray', 'ViewportMappingArray',
    'AspectAlign', 'MeetOrSlice',
]