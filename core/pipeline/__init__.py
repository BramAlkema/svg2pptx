#!/usr/bin/env python3
"""
Clean Slate Pipeline Module

Provides end-to-end SVG to PPTX conversion pipeline using the clean slate architecture.
"""

from .converter import CleanSlateConverter, ConversionResult, ConversionError
from .factory import PipelineFactory, create_default_pipeline
from .config import PipelineConfig, OutputFormat as PipelineOutputFormat

__all__ = [
    "CleanSlateConverter",
    "ConversionResult",
    "ConversionError",
    "PipelineFactory",
    "create_default_pipeline",
    "PipelineConfig",
    "PipelineOutputFormat",
]