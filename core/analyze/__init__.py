#!/usr/bin/env python3
"""
SVG Analysis Module

Provides analysis capabilities for SVG structure and complexity assessment.
"""

from .analyzer import SVGAnalyzer, AnalysisResult
from .complexity_calculator import ComplexityCalculator

__all__ = [
    'SVGAnalyzer',
    'AnalysisResult',
    'ComplexityCalculator'
]