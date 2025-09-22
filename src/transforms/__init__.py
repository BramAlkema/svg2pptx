#!/usr/bin/env python3
"""
Transform System for SVG2PPTX

Clean, high-performance 2D transformation engine using pure NumPy.
Consolidated transform functionality with both legacy Matrix and modern TransformEngine.
"""

# Import from core module
from .core import Matrix
from .parser import TransformParser, TransformEngine

# Export Transform as the primary transform class (using Matrix for compatibility)
Transform = Matrix
TransformBuilder = TransformEngine

# Export clean interface
__all__ = [
    'Transform',           # Primary transform class (Matrix)
    'Matrix',             # Original Matrix class
    'TransformEngine',    # Transform parser (alias for TransformParser)
    'TransformParser',    # Transform parser class
    'TransformBuilder',   # Alias for TransformEngine
]

# Version info
__version__ = '3.0.0'
__author__ = 'SVG2PPTX Team'