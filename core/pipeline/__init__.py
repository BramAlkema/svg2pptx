#!/usr/bin/env python3
"""
Clean Slate Pipeline Module

Provides end-to-end SVG to PPTX conversion pipeline using the clean slate architecture.
"""

from .config import OutputFormat as PipelineOutputFormat
from .config import PipelineConfig
from .converter import CleanSlateConverter, ConversionError, ConversionResult
from .factory import PipelineFactory, create_default_pipeline

__all__ = [
    "CleanSlateConverter",
    "ConversionResult",
    "ConversionError",
    "PipelineFactory",
    "create_default_pipeline",
    "PipelineConfig",
    "PipelineOutputFormat",
]