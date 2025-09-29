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

Usage:
    from core.elements import create_image_processor_service

    # Create service with dependency injection
    image_service = create_image_processor_service(services)

    # Process image element with optimizations
    result = image_service.process_image_element(image_element, context)
"""

from .image_processor import ImageProcessor, create_image_processor
from .image_service import ImageProcessorService, create_image_processor_service
from .gradient_processor import GradientProcessor, create_gradient_processor
from .gradient_service import GradientProcessorService, create_gradient_processor_service
from .pattern_processor import PatternProcessor, create_pattern_processor
from .pattern_service import PatternProcessorService, create_pattern_processor_service

__all__ = [
    # Core classes
    'ImageProcessor',
    'ImageProcessorService',
    'GradientProcessor',
    'GradientProcessorService',
    'PatternProcessor',
    'PatternProcessorService',

    # Factory functions
    'create_image_processor',
    'create_image_processor_service',
    'create_gradient_processor',
    'create_gradient_processor_service',
    'create_pattern_processor',
    'create_pattern_processor_service',
]

__version__ = '1.0.0'