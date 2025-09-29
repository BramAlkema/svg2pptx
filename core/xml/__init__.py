"""
Core XML processing utilities with cython Comment object safety.
"""

from .safe_iter import is_element, children, walk

__all__ = [
    'is_element',
    'children',
    'walk'
]