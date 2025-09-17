"""
ViewBox and Viewport System for SVG2PPTX.

This package provides both legacy scalar and modern NumPy-based viewport
resolution systems with high-performance vectorized operations.
"""

# Import NumPy-based classes for performance (legacy classes have been removed)
from .numpy_viewbox import (
    NumPyViewportEngine, ViewBoxArray, ViewportArray, ViewportMappingArray,
    AspectAlign, MeetOrSlice
)

# Provide compatibility aliases for legacy code
ViewportResolver = NumPyViewportEngine
AspectRatioAlign = AspectAlign

__all__ = [
    # Current NumPy classes
    'NumPyViewportEngine', 'ViewBoxArray', 'ViewportArray', 'ViewportMappingArray',
    'AspectAlign', 'MeetOrSlice',

    # Compatibility aliases
    'ViewportResolver', 'AspectRatioAlign'
]