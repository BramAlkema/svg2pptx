"""
Geometry processing utilities for SVG preprocessing.

This module provides boolean operations on paths and other geometric utilities
used during SVG optimization and preprocessing.

Key Components:
- PathBooleanEngine: Protocol for boolean path operations (union, intersection, difference)
- Backend implementations: PathOpsBackend (Skia), PyClipperBackend (polygon-based)
- Service adapters: Integration with existing SVG2PPTX path processing infrastructure
- Factory functions: Easy creation of configured boolean engines
"""

from .path_boolean_engine import (
    PathBooleanEngine, PathSpec, FillRule, normalize_fill_rule,
    validate_path_spec, create_path_spec
)

from .path_adapters import (
    BooleanEngineFactory, get_available_backends, create_boolean_engine
)

from .service_adapters import create_service_adapters

# Backend availability flags
from .backends import PATHOPS_AVAILABLE, PYCLIPPER_AVAILABLE

__all__ = [
    # Core interfaces and types
    'PathBooleanEngine', 'PathSpec', 'FillRule',

    # Utility functions
    'normalize_fill_rule', 'validate_path_spec', 'create_path_spec',

    # Factory and adapter functions
    'BooleanEngineFactory', 'get_available_backends', 'create_boolean_engine',
    'create_service_adapters',

    # Backend availability
    'PATHOPS_AVAILABLE', 'PYCLIPPER_AVAILABLE'
]