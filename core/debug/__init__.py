"""
Debug utilities for SVG2PPTX pipeline.

Provides tracing, profiling, and visualization tools.
"""

from .element_tracer import (
    ElementTracer,
    PipelineStage,
    TraceEvent,
    get_tracer,
    enable_tracing,
    disable_tracing
)

__all__ = [
    'ElementTracer',
    'PipelineStage',
    'TraceEvent',
    'get_tracer',
    'enable_tracing',
    'disable_tracing',
]
