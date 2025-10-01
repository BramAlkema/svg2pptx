"""
Core filter infrastructure.

This module provides the foundational classes and interfaces for the filter system:
- Abstract Filter base class
- FilterRegistry for dynamic filter discovery
- FilterChain for composable filter operations
- FilterContext for shared state management
"""

from .base import Filter, FilterContext, FilterResult
from .registry import FilterRegistry
from .chain import FilterChain

__all__ = [
    "Filter",
    "FilterContext",
    "FilterResult",
    "FilterRegistry",
    "FilterChain",
]