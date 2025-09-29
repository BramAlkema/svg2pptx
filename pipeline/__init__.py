#!/usr/bin/env python3
"""
SVG2PPTX Clean Architecture Pipeline

End-to-end conversion pipeline demonstrating the clean architecture:
SVG → Preprocessing → IR → Policy Decisions → PPTX Output

This MVP focuses on the Path pipeline with proven a2c arc conversion.
"""

from .path_pipeline import *
from .demo import *

__all__ = [
    # Core pipeline
    "PathPipeline", "PipelineContext", "ConversionResult",

    # Demo
    "run_path_pipeline_demo", "create_path_test_cases",
]