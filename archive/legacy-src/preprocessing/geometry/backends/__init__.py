"""
Boolean operation backends for path processing.

This module provides concrete implementations of the PathBooleanEngine interface
using different underlying libraries:

- PathOpsBackend: Uses Skia PathOps for curve-faithful operations
- PyClipperBackend: Uses PyClipper for polygon-based operations
"""

# Backend imports with graceful fallback handling
try:
    from .pathops_backend import PathOpsBackend
    PATHOPS_AVAILABLE = True
except ImportError:
    PathOpsBackend = None
    PATHOPS_AVAILABLE = False

try:
    from .pyclipper_backend import PyClipperBackend
    PYCLIPPER_AVAILABLE = True
except ImportError:
    PyClipperBackend = None
    PYCLIPPER_AVAILABLE = False

__all__ = ['PathOpsBackend', 'PyClipperBackend', 'PATHOPS_AVAILABLE', 'PYCLIPPER_AVAILABLE']