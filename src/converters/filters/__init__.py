"""
SVG Filter Processing Package.

This package provides a modular architecture for processing SVG filter effects
and converting them to PowerPoint Drawing Markup Language (DrawingML).

Key Components:
    - core: Abstract base classes and interfaces
    - image: Image processing filters (blur, color, distortion)
    - geometric: Geometric transformation and composite operations
    - utils: Parsing utilities and mathematical helpers
    - compatibility: Backward compatibility layer

Example:
    Basic usage of the filter system:

    >>> from filters import FilterRegistry, FilterChain
    >>> registry = FilterRegistry()
    >>> chain = FilterChain([registry.get_filter('blur'), registry.get_filter('shadow')])
    >>> result = chain.apply(svg_element, context)
"""

# Core interfaces and classes
from .core.base import Filter, FilterContext, FilterResult
from .core.registry import FilterRegistry
from .core.chain import FilterChain

# Backward compatibility - maintain original imports
# This ensures existing code continues to work
from .compatibility.legacy import *

__version__ = "2.0.0"
__all__ = [
    # Core classes
    "Filter",
    "FilterContext",
    "FilterResult",
    "FilterRegistry",
    "FilterChain",
]

# Initialize default registry
_default_registry = None

def get_default_registry() -> FilterRegistry:
    """Get the default filter registry instance."""
    global _default_registry
    if _default_registry is None:
        _default_registry = FilterRegistry()
        _default_registry.register_default_filters()
    return _default_registry