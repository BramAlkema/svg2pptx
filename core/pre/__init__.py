#!/usr/bin/env python3
"""
SVG Preprocessors

Stateless functions that normalize SVG weirdness before IR conversion.
Each preprocessor transforms the SVG DOM to make downstream conversion cleaner.

Key principles:
- Stateless transformations
- DOM-to-DOM operations
- Preserve semantic meaning
- Normalize common patterns
"""

from .expand_use import *
from .normalize_transforms import *
from .resolve_clips import *
from .text_layout_prep import *
from .chain import PreprocessorChain, create_standard_chain, preprocess_svg, validate_preprocessed_svg

__all__ = [
    # Core preprocessors
    "ExpandUsePreprocessor", "expand_use_elements",
    "NormalizeTransformsPreprocessor", "normalize_transform_hierarchy",
    "ResolveClipsPreprocessor", "resolve_clip_paths",
    "TextLayoutPrepPreprocessor", "prepare_text_layout",

    # Processor chain
    "PreprocessorChain", "create_standard_chain",

    # Utilities
    "preprocess_svg", "validate_preprocessed_svg",
]