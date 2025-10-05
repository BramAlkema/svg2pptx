#!/usr/bin/env python3
"""
Clean Slate Multi-Page Module

Simplified multi-page PPTX generation that replaces the unwieldy 7000+ line
multislide implementation with a clean, focused approach.

Key Features:
- Leverages Clean Slate conversion pipeline
- Simple page source management
- Common-case page detection
- Clean error handling
- Performance tracking

Usage:
    from core.multipage import CleanSlateMultiPageConverter, PageSource

    # Convert multiple SVG files
    converter = CleanSlateMultiPageConverter()
    result = converter.convert_files(['page1.svg', 'page2.svg'], 'output.pptx')

    # Convert page sources
    pages = [
        PageSource(content=svg_content1, title="Page 1"),
        PageSource(content=svg_content2, title="Page 2")
    ]
    result = converter.convert_pages(pages, 'output.pptx')
"""

from .converter import (
    CleanSlateMultiPageConverter,
    MultiPageResult,
    PageSource,
    create_multipage_converter,
)
from .detection import (
    PageBreak,
    SimplePageDetector,
    detect_multiple_svg_files,
    split_svg_into_pages,
)

__all__ = [
    # Converter classes
    'CleanSlateMultiPageConverter',
    'PageSource',
    'MultiPageResult',
    'create_multipage_converter',

    # Detection classes
    'SimplePageDetector',
    'PageBreak',
    'split_svg_into_pages',
    'detect_multiple_svg_files',
]