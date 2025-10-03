#!/usr/bin/env python3
"""
Element Processing System

Enhanced element processors that integrate with the preprocessing pipeline
to provide optimized conversion for complex SVG elements like images,
gradients, and patterns.

Components:
- ImageProcessor: Enhanced image processing with preprocessing integration
- GradientProcessor: Gradient processing with color system integration
- PatternProcessor: Pattern support with optimization
"""

from .image_processor import ImageProcessor, create_image_processor
from .gradient_processor import GradientProcessor, create_gradient_processor
from .pattern_processor import PatternProcessor, create_pattern_processor

__all__ = [
    # Core classes
    'ImageProcessor',
    'GradientProcessor',
    'PatternProcessor',

    # Factory functions
    'create_image_processor',
    'create_gradient_processor',
    'create_pattern_processor',
]

__version__ = '1.0.0'
