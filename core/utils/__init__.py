"""
Utility services and migration tracking for SVG2PPTX.
"""

from .migration_tracker import DuplicateWarning, mark_duplicate

__all__ = ['DuplicateWarning', 'mark_duplicate']