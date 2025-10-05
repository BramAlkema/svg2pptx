#!/usr/bin/env python3
"""
Text Processing Pipeline

Provides comprehensive text processing capabilities with preprocessing
integration and documented fixes implementation.

Components:
- TextLayoutEngine: Layout processing with preprocessing metadata
- TextConverterService: High-level text conversion orchestration
- Documented fixes integration for SVG text issues

Usage:
    from core.text import create_text_converter_service

    # Create service with dependency injection
    text_service = create_text_converter_service(services)

    # Convert text element with preprocessing
    drawingml = text_service.convert_text_element(text_element, context)
"""

from .converter_service import TextConverterService, create_text_converter_service
from .integration_adapter import (
    TextIntegrationAdapter,
    create_text_integration_adapter,
    patch_existing_text_converter,
)
from .layout_engine import TextLayoutEngine, create_text_layout_engine

__all__ = [
    # Core classes
    'TextLayoutEngine',
    'TextConverterService',
    'TextIntegrationAdapter',

    # Factory functions
    'create_text_layout_engine',
    'create_text_converter_service',
    'create_text_integration_adapter',

    # Integration utilities
    'patch_existing_text_converter',
]

__version__ = '1.0.0'