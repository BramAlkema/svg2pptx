#!/usr/bin/env python3
"""
Group Processing and Clipping Pipeline

Provides comprehensive group and clipping processing capabilities with
preprocessing integration and PowerPoint optimization.

Components:
- GroupProcessor: Enhanced group structure processing
- ClippingAnalyzer: Clipping scenario analysis and strategy recommendation
- GroupConverterService: High-level orchestration service

Usage:
    from core.groups import create_group_converter_service

    # Create service with dependency injection
    group_service = create_group_converter_service(services)

    # Convert group element with optimizations
    drawingml = group_service.convert_group_element(group_element, context)

    # Convert clipped element
    drawingml = group_service.convert_clipped_element(clipped_element, context)
"""

from .clipping_analyzer import (
    ClippingAnalysis,
    ClippingAnalyzer,
    ClippingComplexity,
    ClippingPath,
    ClippingStrategy,
    create_clipping_analyzer,
)
from .converter_service import GroupConverterService, create_group_converter_service
from .group_processor import GroupProcessor, create_group_processor

__all__ = [
    # Core classes
    'GroupProcessor',
    'ClippingAnalyzer',
    'GroupConverterService',

    # Enums and data classes
    'ClippingComplexity',
    'ClippingStrategy',
    'ClippingPath',
    'ClippingAnalysis',

    # Factory functions
    'create_group_processor',
    'create_clipping_analyzer',
    'create_group_converter_service',
]

__version__ = '1.0.0'