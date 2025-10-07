#!/usr/bin/env python3
"""
Fractional EMU Precision System

Maintains float64 precision throughout coordinate pipeline.
Only rounds to int at final XML serialization.
"""

from .constants import (
    EMU_PER_INCH,
    EMU_PER_POINT,
    EMU_PER_MM,
    EMU_PER_CM,
    DEFAULT_DPI,
    POINTS_PER_INCH,
    SLIDE_WIDTH_EMU,
    SLIDE_HEIGHT_EMU,
    MAX_FRACTIONAL_PRECISION,
    MIN_EMU_VALUE,
    MAX_EMU_VALUE,
    DRAWINGML_COORD_SPACE,
)

from .types import (
    PrecisionMode,
    FractionalCoordinateContext,
    PrecisionContext,
)

from .errors import (
    CoordinateValidationError,
    PrecisionOverflowError,
    EMUBoundaryError,
)

from .converter import FractionalEMUConverter

# Optional vectorized engine (requires NumPy)
try:
    from .precision_engine import VectorizedPrecisionEngine
    VECTORIZED_AVAILABLE = True
except ImportError:
    VectorizedPrecisionEngine = None
    VECTORIZED_AVAILABLE = False


__all__ = [
    # Constants
    'EMU_PER_INCH',
    'EMU_PER_POINT',
    'EMU_PER_MM',
    'EMU_PER_CM',
    'DEFAULT_DPI',
    'POINTS_PER_INCH',
    'SLIDE_WIDTH_EMU',
    'SLIDE_HEIGHT_EMU',
    'MAX_FRACTIONAL_PRECISION',
    'MIN_EMU_VALUE',
    'MAX_EMU_VALUE',
    'DRAWINGML_COORD_SPACE',
    
    # Types
    'PrecisionMode',
    'FractionalCoordinateContext',
    'PrecisionContext',
    
    # Errors
    'CoordinateValidationError',
    'PrecisionOverflowError',
    'EMUBoundaryError',
    
    # Converters
    'FractionalEMUConverter',
    'VectorizedPrecisionEngine',
    'VECTORIZED_AVAILABLE',
]


# Convenience factory function
def create_converter(
    precision_mode: PrecisionMode = PrecisionMode.STANDARD,
    **kwargs
) -> FractionalEMUConverter:
    """
    Create a FractionalEMUConverter with specified precision mode.

    Args:
        precision_mode: Precision level (STANDARD, SUBPIXEL, HIGH, ULTRA)
        **kwargs: Additional converter parameters

    Returns:
        Configured FractionalEMUConverter instance

    Examples:
        >>> converter = create_converter(PrecisionMode.SUBPIXEL)
        >>> emu = converter.pixels_to_fractional_emu(100.5)
        957262.5
    """
    return FractionalEMUConverter(precision_mode=precision_mode, **kwargs)
