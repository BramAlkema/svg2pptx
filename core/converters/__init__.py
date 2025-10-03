#!/usr/bin/env python3
"""
Core Converters for Clean Slate Architecture

Essential converters migrated from legacy src/converters/ for self-contained operation.
"""

# Only import available components
from .clippath_analyzer import ClipPathAnalyzer
from .clippath_types import ClipPathComplexity, ClipPathDefinition, ClipPathAnalysis

# Import custgeom_generator (newly migrated)
from .custgeom_generator import CustGeomGenerator

# Import marker processor (newly migrated)
from .marker_processor import MarkerProcessor, MarkerDefinition, MarkerPosition, create_marker_processor

# Import switch processor (newly implemented)
from .switch_converter import SwitchProcessor, SwitchResult, create_switch_processor

__all__ = [
    'ClipPathAnalyzer',
    'ClipPathComplexity',
    'ClipPathDefinition',
    'ClipPathAnalysis',
    'CustGeomGenerator',
    'MarkerProcessor',
    'MarkerDefinition',
    'MarkerPosition',
    'create_marker_processor',
    'SwitchProcessor',
    'SwitchResult',
    'create_switch_processor'
]