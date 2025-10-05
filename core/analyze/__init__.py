#!/usr/bin/env python3
"""
SVG Analysis Module

Provides analysis capabilities for SVG structure and complexity assessment.
"""

from .analyzer import AnalysisResult, SVGAnalyzer
from .api_adapter import SVGAnalyzerAPI, create_api_analyzer
from .complexity_calculator import ComplexityCalculator
from .svg_validator import (
    SVGValidator,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    create_svg_validator,
)
from .types import (
    CompatibilityLevel,
    CompatibilityReport,
    ElementCounts,
    FeatureSet,
    PerformanceEstimate,
    PolicyRecommendation,
    SupportLevel,
    SVGAnalysisResult,
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
    'CompatibilityReport',
]