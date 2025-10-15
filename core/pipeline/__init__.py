#!/usr/bin/env python3
"""
Clean Slate Pipeline Module

Provides end-to-end SVG to PPTX conversion pipeline using the clean slate architecture.
"""

from importlib import import_module

from .config import OutputFormat as PipelineOutputFormat
from .config import PipelineConfig

__all__ = [
    "CleanSlateConverter",
    "ConversionResult",
    "ConversionError",
    "PipelineFactory",
    "create_default_pipeline",
    "create_fast_pipeline",
    "create_quality_pipeline",
    "create_debug_pipeline",
    "PipelineConfig",
    "PipelineOutputFormat",
]

_LAZY_IMPORTS = {
    "CleanSlateConverter": ("core.pipeline.converter", "CleanSlateConverter"),
    "ConversionResult": ("core.pipeline.converter", "ConversionResult"),
    "ConversionError": ("core.pipeline.converter", "ConversionError"),
    "PipelineFactory": ("core.pipeline.factory", "PipelineFactory"),
    "create_default_pipeline": ("core.pipeline.factory", "create_default_pipeline"),
    "create_fast_pipeline": ("core.pipeline.factory", "create_fast_pipeline"),
    "create_quality_pipeline": ("core.pipeline.factory", "create_quality_pipeline"),
    "create_debug_pipeline": ("core.pipeline.factory", "create_debug_pipeline"),
}


def __getattr__(name):
    if name in _LAZY_IMPORTS:
        module_name, attr_name = _LAZY_IMPORTS[name]
        module = import_module(module_name)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'core.pipeline' has no attribute '{name}'")
