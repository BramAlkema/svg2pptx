"""
Migration tracking and duplicate warning system for SVG2PPTX consolidation.

This module provides infrastructure for tracking duplicate code elimination
and warning about legacy implementations during the consolidation process.
"""

import inspect
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class DuplicateMetadata:
    """Metadata for tracking duplicate implementations."""
    file_path: str
    line_range: tuple[int, int]
    category: str  # 'color', 'style', 'coordinate', 'xml', 'transform'
    canonical_replacement: str
    priority: str  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    migration_complexity: str  # 'SIMPLE', 'MEDIUM', 'COMPLEX'
    estimated_effort: str  # '1h', '4h', '1d', '3d'


class DuplicateWarning:
    """Warning system for marking duplicate implementations."""

    # Registry of all known duplicates
    _duplicate_registry: dict[str, DuplicateMetadata] = {}

    @staticmethod
    def warn_duplicate(canonical_location: str,
                      replacement_method: str = None,
                      category: str = 'unknown',
                      priority: str = 'MEDIUM',
                      deprecation_version: str = None):
        """
        Issue deprecation warning for duplicate implementation.

        Args:
            canonical_location: Path to canonical implementation
            replacement_method: Specific method to use instead
            category: Type of duplicate (color, style, coordinate, etc.)
            priority: Migration priority level
            deprecation_version: Version when this will be removed
        """
        # Get caller information
        frame = inspect.currentframe().f_back
        caller_file = frame.f_code.co_filename
        caller_line = frame.f_lineno
        caller_function = frame.f_code.co_name

        # Create warning message
        message = f"DUPLICATE CODE WARNING: {caller_function}() in {Path(caller_file).name}:{caller_line}"
        message += f"\n  ┌─ Canonical implementation: {canonical_location}"
        if replacement_method:
            message += f"\n  ├─ Use instead: {replacement_method}"
        message += f"\n  ├─ Category: {category.upper()}"
        message += f"\n  ├─ Priority: {priority}"
        if deprecation_version:
            message += f"\n  └─ Deprecated in version: {deprecation_version}"
        else:
            message += "\n  └─ Scheduled for removal in Phase 1-6 consolidation"

        warnings.warn(message, UserWarning, stacklevel=2)

        # Register duplicate for tracking
        key = f"{caller_file}:{caller_line}"
        DuplicateWarning._duplicate_registry[key] = DuplicateMetadata(
            file_path=caller_file,
            line_range=(caller_line, caller_line),
            category=category,
            canonical_replacement=canonical_location,
            priority=priority,
            migration_complexity='MEDIUM',  # Default
            estimated_effort='4h',  # Default
        )

    @classmethod
    def get_duplicate_registry(cls) -> dict[str, DuplicateMetadata]:
        """Get registry of all tracked duplicates."""
        return cls._duplicate_registry.copy()

    @classmethod
    def generate_migration_report(cls) -> dict[str, list[str]]:
        """Generate report of remaining duplicates by category."""
        report = {}
        for key, metadata in cls._duplicate_registry.items():
            category = metadata.category
            if category not in report:
                report[category] = []
            report[category].append(f"{metadata.file_path}:{metadata.line_range[0]} - {metadata.priority}")
        return report


def mark_duplicate(canonical_location: str,
                  category: str = 'unknown',
                  priority: str = 'MEDIUM',
                  replacement_method: str = None):
    """
    Decorator to mark functions as duplicates requiring migration.

    Args:
        canonical_location: Path to canonical implementation
        category: Type of duplicate (color, style, coordinate, etc.)
        priority: Migration priority level
        replacement_method: Specific method to use instead

    Example:
        @mark_duplicate('src/color/core.py', 'color', 'HIGH', 'ColorParser.parse_color_string()')
        def legacy_color_parser(color_str: str):
            # Legacy implementation
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            DuplicateWarning.warn_duplicate(
                canonical_location=canonical_location,
                replacement_method=replacement_method,
                category=category,
                priority=priority,
            )
            return func(*args, **kwargs)

        # Preserve function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator


# TODO comment standards for manual marking
TODO_TEMPLATE = """
# TODO: DUPLICATE - Consolidate with {canonical_location}
# WARNING: This implementation duplicates functionality available in {service}
# MIGRATE: Replace with {service}.{method}() - Priority: {priority}
# REMOVE: After migration to {canonical_implementation}
"""

def generate_todo_comment(canonical_location: str,
                         service: str,
                         method: str,
                         priority: str = 'MEDIUM') -> str:
    """Generate standardized TODO comment for duplicate code."""
    return TODO_TEMPLATE.format(
        canonical_location=canonical_location,
        service=service,
        method=method,
        priority=priority,
        canonical_implementation=canonical_location,
    ).strip()


# Example usage patterns for developers
MIGRATION_EXAMPLES = {
    'color': {
        'canonical': 'src/color/core.py',
        'service': 'ColorParser',
        'method': 'parse_color_string()',
        'example': '''
# TODO: DUPLICATE - Consolidate with src/color/core.py
# WARNING: This duplicates ColorParser.parse_color_string() functionality
# MIGRATE: Replace with self.services.color_parser.parse_color_string()
# PRIORITY: CRITICAL - Phase 1 color system migration
def parse_hex_color(self, hex_str: str):
    DuplicateWarning.warn_duplicate('src/color/core.py', 'ColorParser.parse_color_string()', 'color', 'CRITICAL')
    # Legacy implementation continues...
        ''',
    },
    'style': {
        'canonical': 'src/utils/style_parser.py',
        'service': 'StyleParser',
        'method': 'parse_style_string()',
        'example': '''
# TODO: DUPLICATE - Consolidate with src/utils/style_parser.py
# WARNING: This duplicates StyleParser.parse_style_string() functionality
# MIGRATE: Replace with self.services.style_parser.parse_style_string()
# PRIORITY: HIGH - Phase 1 style processing migration
def parse_style_attr(self, style_str: str):
    DuplicateWarning.warn_duplicate('src/utils/style_parser.py', 'StyleParser.parse_style_string()', 'style', 'HIGH')
    # Legacy implementation continues...
        ''',
    },
    'coordinate': {
        'canonical': 'src/utils/coordinate_transformer.py',
        'service': 'CoordinateTransformer',
        'method': 'parse_coordinate_string()',
        'example': '''
# TODO: DUPLICATE - Consolidate with src/utils/coordinate_transformer.py
# WARNING: This duplicates CoordinateTransformer functionality
# MIGRATE: Replace with self.services.coordinate_transformer.parse_coordinate_string()
# PRIORITY: HIGH - Phase 1 coordinate processing migration
def parse_points(self, points_str: str):
    DuplicateWarning.warn_duplicate('src/utils/coordinate_transformer.py', 'CoordinateTransformer.parse_coordinate_string()', 'coordinate', 'HIGH')
    # Legacy implementation continues...
        ''',
    },
}