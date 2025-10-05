#!/usr/bin/env python3
"""
Consolidated Units Module for SVG2PPTX

Single source of truth for all unit conversion functionality.
Combines best features from all parallel implementations:
- Comprehensive unit support
- NumPy optimizations for performance
- Clean, unified API
- Fluent interface for intuitive conversions
- Backward compatibility

Example Usage:

    Fluent API (Recommended):
    >>> from .units import unit, units
    >>>
    >>> # Simple conversions
    >>> unit("100px").to_emu()
    952500
    >>> unit("2em").with_font_size(18).to_pixels()
    36.0
    >>>
    >>> # Context chaining
    >>> unit("50%").with_parent_width(800).to_pixels()
    400.0
    >>> unit("1in").with_dpi(300).to_pixels()
    300.0
    >>>
    >>> # Multiple formats
    >>> u = unit("72pt")
    >>> u.to_pixels()  # 96.0
    >>> u.to_inches()  # 1.0
    >>> u.to_mm()      # 25.4
    >>>
    >>> # Arithmetic operations
    >>> (unit("100px") + unit("50px")).to_pixels()
    150.0
    >>> (unit("100px") * 2).to_pixels()
    200.0
    >>>
    >>> # Batch operations
    >>> units(["100px", "2em", "50%"]).with_font_size(18).to_emu()
    [952500, 342900, 3810000]
    >>> units({"x": "100px", "width": "50%"}).with_parent_width(800).to_emu()
    {"x": 952500, "width": 3810000}

    Traditional API:
    >>> from .units import UnitConverter
    >>> converter = UnitConverter()
    >>> emu = converter.to_emu("100px")
    >>> pixels = converter.to_pixels("2em")

    Context-aware processing:
    >>> context = converter.create_context(width=1024, height=768, dpi=150)
    >>> emu = converter.to_emu("50%", context, axis='x')
"""

# Core implementation
# Fluent API
# Convenience functions for backward compatibility
# EMU constants
from .core import (
    DEFAULT_DPI,
    EMU_PER_CM,
    EMU_PER_INCH,
    EMU_PER_MM,
    EMU_PER_POINT,
    HIGH_DPI,
    PRINT_DPI,
    SLIDE_HEIGHT_EMU,
    SLIDE_WIDTH_EMU,
    ConversionContext,
    UnitBatch,
    UnitConverter,
    UnitType,
    UnitValue,
    create_context,
    to_emu,
    to_pixels,
    unit,
    units,
)

# Export clean public API
__all__ = [
    # Primary API
    'UnitConverter',
    'ConversionContext',
    'UnitType',

    # Fluent API
    'UnitValue',
    'UnitBatch',
    'unit',
    'units',

    # Convenience functions
    'to_emu',
    'to_pixels',
    'create_context',

    # Constants
    'EMU_PER_INCH',
    'EMU_PER_POINT',
    'EMU_PER_MM',
    'EMU_PER_CM',
    'SLIDE_WIDTH_EMU',
    'SLIDE_HEIGHT_EMU',
    'DEFAULT_DPI',
    'PRINT_DPI',
    'HIGH_DPI',
]