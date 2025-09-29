#!/usr/bin/env python3
"""
SVG2PPTX Core Architecture

Clean slate architecture for world-class SVG to PowerPoint conversion.

This module implements a clean separation of concerns:
- IR: Canonical scene graph representation
- Preprocessors: SVG normalization and cleanup
- Mappers: Policy-driven IR to DrawingML/EMF conversion
- Adapters: Thin wrappers around proven legacy components
- Policy: Centralized output format decisions

Architecture:
    SVG → Preprocessors → IR → Mappers → DrawingML/EMF → PPTX

Key principles:
- Pure data in IR (no side effects)
- Stateless preprocessors
- Policy-driven mapping decisions
- Heavy reuse of battle-tested components
"""

__version__ = "2.0.0-alpha"
__author__ = "SVG2PPTX Core Team"

# Core components
from .ir import *
from .policy import *
from .multipage import *

__all__ = [
    # IR types
    "Path", "TextFrame", "Group", "Run", "Paint", "Stroke",
    "Point", "Rect", "ClipRef", "Segment",

    # Policy engine
    "Policy", "OutputTarget",

    # Multi-page converter
    "CleanSlateMultiPageConverter", "PageSource", "MultiPageResult",
    "SimplePageDetector", "PageBreak",
]