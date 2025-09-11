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
from .speedrun_cache import SpeedrunCache, get_speedrun_cache, enable_speedrun_mode as enable_cache_speedrun
from .speedrun_optimizer import SVGSpeedrunOptimizer, SpeedrunMode, get_speedrun_optimizer, enable_speedrun_mode

__all__ = [
    'ConversionCache',
    'PathCache', 
    'ColorCache',
    'TransformCache',
    'ConverterPool',
    'UtilityPool',
    'BatchProcessor',
    'PerformanceProfiler',
    'PerformanceOptimizer',
    'SpeedrunCache',
    'SVGSpeedrunOptimizer',
    'SpeedrunMode',
    'get_speedrun_cache',
    'get_speedrun_optimizer',
    'enable_speedrun_mode',
    'enable_cache_speedrun'
]