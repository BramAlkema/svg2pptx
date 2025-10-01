"""
Filter utilities.

This module contains utility functions and classes for filter processing:
- parsing: SVG filter parsing and parameter extraction
- math_helpers: Mathematical operations and computations
- validation: Input validation and error handling
"""

from .parsing import (
    FilterPrimitiveParser,
    FilterParameterExtractor,
    FilterCoordinateParser,
    FilterValueParser,
    FilterParsingException,
    FilterPrimitive,
    parse_filter_primitive,
    parse_filter_coordinate,
    parse_filter_value,
    extract_primitive_parameters
)
# Mathematical helpers are provided by existing modules:
# - Coordinate/angle calculations: src/transforms.py and src/converters/filters/geometric/transforms.py
# - Color mathematical operations: src/colors.py
# - Unit conversions: src/units.py

__all__ = [
    # Parsing utilities
    "FilterPrimitiveParser",
    "FilterParameterExtractor",
    "FilterCoordinateParser",
    "FilterValueParser",
    "FilterParsingException",
    "FilterPrimitive",
    "parse_filter_primitive",
    "parse_filter_coordinate",
    "parse_filter_value",
    "extract_primitive_parameters",
    # Note: Mathematical helpers are provided by:
    # - transforms.py for coordinate/angle operations
    # - colors.py for color mathematical operations
    # - units.py for unit conversion operations
]