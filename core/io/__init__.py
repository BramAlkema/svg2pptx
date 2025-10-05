#!/usr/bin/env python3
"""
PPTX Integration Module

Provides components for integrating mapped IR elements into PowerPoint slides.
"""

from .embedder import DrawingMLEmbedder, EmbedderResult, EmbeddingError, create_embedder
from .package_writer import PackageError, PackageWriter, create_package_writer
from .slide_builder import SlideBuilder, SlideTemplate

__all__ = [
    "DrawingMLEmbedder",
    "EmbedderResult",
    "EmbeddingError",
    "create_embedder",
    "SlideBuilder",
    "SlideTemplate",
    "PackageWriter",
    "PackageError",
    "create_package_writer",
]