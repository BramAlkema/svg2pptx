#!/usr/bin/env python3
"""
Smart Font Converter System

Unified font conversion system for Clean Slate architecture that integrates:
- System fonts with optional embedding
- WordArt/SmartArt for complex transforms
- Text-to-path conversion for maximum fidelity
- Intelligent strategy selection based on context
"""

from .smart_converter import SmartFontConverter, FontConversionResult
from .types import (
    FontStrategy,
    FontComplexity,
    ExecutionResult,
    HandlerResult,
    FontConversionConfig
)
from .strategy_selector import FontStrategySelector
from .strategy_executor import FontStrategyExecutor

__all__ = [
    # Main converter
    'SmartFontConverter',
    'FontConversionResult',

    # Types and enums
    'FontStrategy',
    'FontComplexity',
    'ExecutionResult',
    'HandlerResult',
    'FontConversionConfig',

    # Core components
    'FontStrategySelector',
    'FontStrategyExecutor',
]