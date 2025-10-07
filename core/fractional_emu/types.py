#!/usr/bin/env python3
"""
Fractional EMU Types

Type definitions for fractional EMU system.
"""

from dataclasses import dataclass
from enum import Enum
from .constants import DEFAULT_DPI


class PrecisionMode(Enum):
    """Mathematical precision modes for coordinate conversion."""
    STANDARD = 1           # Regular EMU precision (1x)
    SUBPIXEL = 100        # Sub-EMU fractional precision (100x)
    HIGH = 1000           # High precision mode (1000x)
    ULTRA = 10000         # Ultra precision mode (10000x)


@dataclass
class FractionalCoordinateContext:
    """Extended context for sub-EMU precision calculations."""
    base_dpi: float = DEFAULT_DPI
    fractional_scale: float = 1.0
    rounding_mode: str = 'round_half_up'
    precision_threshold: float = 0.001
    validate_bounds: bool = True
    
    
@dataclass
class PrecisionContext:
    """Context for precision calculations."""
    mode: PrecisionMode = PrecisionMode.STANDARD
    scale_factor: float = 1.0
    validate: bool = True
