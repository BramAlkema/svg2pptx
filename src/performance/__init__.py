#!/usr/bin/env python3
"""
Performance optimization module for SVG2PPTX conversion.

This module provides caching, pooling, and batch processing capabilities
to significantly improve conversion performance for complex SVG files.
"""

from .cache import ConversionCache, PathCache, ColorCache, TransformCache
from .pools import ConverterPool, UtilityPool
from .batch import BatchProcessor
from .profiler import PerformanceProfiler
from .optimizer import PerformanceOptimizer

__all__ = [
    'ConversionCache',
    'PathCache', 
    'ColorCache',
    'TransformCache',
    'ConverterPool',
    'UtilityPool',
    'BatchProcessor',
    'PerformanceProfiler',
    'PerformanceOptimizer'
]