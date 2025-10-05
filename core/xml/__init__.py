"""
Core XML processing utilities with cython Comment object safety.
"""

from .safe_iter import children, is_element, walk

__all__ = [
    'is_element',
    'children',
    'walk',
]