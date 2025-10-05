#!/usr/bin/env python3
"""
Core Path Processing System for SVG2PPTX

Modern modular path processing system with industry-standard algorithms.
Uses clean separation of concerns through specialized components:
- PathSystem for orchestration and end-to-end processing
- PathParser for parsing SVG path commands
- CoordinateSystem for viewport and coordinate transformations
- ArcConverter with industry-standard a2c algorithm
- DrawingMLGenerator for PowerPoint XML generation

Example Usage:
    Basic path processing:
    >>> from svg2pptx.paths import create_path_system
    >>> system = create_path_system(800, 600, (0, 0, 400, 300))
    >>> result = system.process_path("M 100 200 C 100 100 400 100 400 200")

    Advanced processing with styling:
    >>> result = system.process_path(
    ...     "M 100 200 C 100 100 400 100 400 200",
    ...     {'fill': '#FF0000', 'stroke': '#000000'}
    ... )
"""

# Modular architecture components
from .arc_converter import ArcConverter
from .architecture import (
    ArcConversionError,
    BezierSegment,
    CoordinatePoint,
    CoordinateTransformError,
    PathBounds,
    PathCommand,
    PathCommandType,
    PathParseError,
    PathSystemContext,
    PathSystemError,
    XMLGenerationError,
)
from .coordinate_system import CoordinateSystem
from .drawingml_generator import DrawingMLGenerator
from .parser import PathParser
from .path_system import PathProcessingResult, PathSystem, create_path_system

# Export main public API
__all__ = [
    # Main path system
    'PathSystem',
    'PathProcessingResult',
    'create_path_system',

    # Core components
    'CoordinateSystem',
    'PathParser',
    'ArcConverter',
    'DrawingMLGenerator',

    # Data structures
    'PathCommand',
    'CoordinatePoint',
    'BezierSegment',
    'PathBounds',
    'PathSystemContext',
    'PathCommandType',

    # Exceptions
    'PathSystemError',
    'PathParseError',
    'CoordinateTransformError',
    'ArcConversionError',
    'XMLGenerationError',
]

# Version info
__version__ = '2.0.0'
__author__ = 'SVG2PPTX Team'