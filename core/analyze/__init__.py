#!/usr/bin/env python3
"""
SVG Analysis Module

Provides analysis capabilities for SVG structure and complexity assessment.
"""

from .analyzer import SVGAnalyzer, AnalysisResult
from .complexity_calculator import ComplexityCalculator
from .api_adapter import SVGAnalyzerAPI, create_api_analyzer
from .svg_validator import SVGValidator, create_svg_validator, ValidationResult, ValidationIssue, ValidationSeverity
from .types import (
    ElementCounts,
    FeatureSet,
    PerformanceEstimate,
    PolicyRecommendation,
    SVGAnalysisResult,
    SupportLevel,
    CompatibilityLevel,
    CompatibilityReport
)

__all__ = [
    'SVGAnalyzer',
    'AnalysisResult',
    'ComplexityCalculator',
    'SVGAnalyzerAPI',
    'create_api_analyzer',
    'SVGValidator',
    'create_svg_validator',
    'ValidationResult',
    'ValidationIssue',
    'ValidationSeverity',
    'ElementCounts',
    'FeatureSet',
    'PerformanceEstimate',
    'PolicyRecommendation',
    'SVGAnalysisResult',
    'SupportLevel',
    'CompatibilityLevel',
    'CompatibilityReport'
]