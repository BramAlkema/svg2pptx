"""
SVG Preprocessing Module

Python port of key SVGO optimizations for SVG2PPTX conversion preprocessing.
"""

from .optimizer import SVGOptimizer, create_optimizer
from .plugins import *

__all__ = ['SVGOptimizer', 'create_optimizer']