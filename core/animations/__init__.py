#!/usr/bin/env python3
"""
Animation System for SVG2PPTX

Modular animation system for converting SMIL animations to PowerPoint format.
Following ADR-006 animation system architecture and ADR-005 fluent API patterns.

This module provides:
- SMIL animation parsing and validation
- Timeline generation with keyframe interpolation
- PowerPoint DrawingML animation generation
- Fluent API builders for intuitive animation construction
- Comprehensive error handling and reporting

Example usage:
    # Direct conversion
    from src.animations import AnimationConverter
    converter = AnimationConverter()
    result = converter.convert_svg_animations(svg_element)

    # Fluent API
    from src.animations import AnimationBuilder
    animation = (AnimationBuilder()
        .target("rect1")
        .animate("opacity")
        .from_to("0", "1")
        .duration("2s")
        .with_easing("ease-in-out")
        .build())
"""

# Core types and data models
# Fluent API builders
from .builders import (
    AnimationBuilder,
    AnimationComposer,
    AnimationSequenceBuilder,
    TimingBuilder,
)
from .core import (
    AnimationComplexity,
    AnimationDefinition,
    AnimationKeyframe,
    AnimationScene,
    AnimationSummary,
    AnimationTiming,
    AnimationType,
    CalcMode,
    FillMode,
    TransformType,
    format_transform_string,
)

# Specialized components
from .interpolation import (
    BezierEasing,
    ColorInterpolator,
    InterpolationEngine,
    InterpolationResult,
    NumericInterpolator,
    TransformInterpolator,
)

# Main parser (converter now in src.converters.animation_converter)
from .parser import SMILParser, SMILParsingError
from .powerpoint import PowerPointAnimationGenerator, PowerPointAnimationSequence
from .timeline import TimelineConfig, TimelineGenerator

# Version information
__version__ = "1.0.0"
__author__ = "SVG2PPTX Animation System"

# Module-level convenience functions
def create_animation_converter(services=None):
    """
    Create animation converter with optional services.

    Args:
        services: ConversionServices instance (optional)

    Returns:
        Configured AnimationConverter instance
    """
    from ..converters.animation_converter import AnimationConverter
    if services is None:
        from ..services.conversion_services import ConversionServices
        services = ConversionServices.create_default()
    return AnimationConverter(services=services)

def parse_svg_animations(svg_element) -> list:
    """
    Parse animations from SVG element using default parser.

    Args:
        svg_element: SVG root element

    Returns:
        List of AnimationDefinition objects
    """
    parser = SMILParser()
    return parser.parse_svg_animations(svg_element)

def create_animation_builder() -> AnimationBuilder:
    """
    Create new animation builder for fluent API usage.

    Returns:
        New AnimationBuilder instance
    """
    return AnimationBuilder()

def create_sequence_builder() -> AnimationSequenceBuilder:
    """
    Create new sequence builder for fluent API usage.

    Returns:
        New AnimationSequenceBuilder instance
    """
    return AnimationSequenceBuilder()

def create_composer() -> AnimationComposer:
    """
    Create new animation composer for high-level animation creation.

    Returns:
        New AnimationComposer instance
    """
    return AnimationComposer()

# Export all public components
__all__ = [
    # Core types
    'AnimationType',
    'FillMode',
    'TransformType',
    'CalcMode',
    'AnimationComplexity',
    'AnimationTiming',
    'AnimationKeyframe',
    'AnimationDefinition',
    'AnimationScene',
    'AnimationSummary',
    'format_transform_string',

    # Main components (AnimationConverter moved to src.converters.animation_converter)
    'SMILParser',
    'SMILParsingError',

    # Specialized components
    'InterpolationEngine',
    'InterpolationResult',
    'ColorInterpolator',
    'NumericInterpolator',
    'TransformInterpolator',
    'BezierEasing',
    'TimelineGenerator',
    'TimelineConfig',
    'PowerPointAnimationGenerator',
    'PowerPointAnimationSequence',

    # Fluent API
    'AnimationBuilder',
    'AnimationSequenceBuilder',
    'TimingBuilder',
    'AnimationComposer',

    # Convenience functions
    'create_animation_converter',
    'parse_svg_animations',
    'create_animation_builder',
    'create_sequence_builder',
    'create_composer',
]