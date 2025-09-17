#!/usr/bin/env python3
"""
Ultra-Fast NumPy Unit Conversion Engine for SVG2PPTX

Complete rewrite of unit system using pure NumPy for maximum performance.
Targets 30-100x speedup over legacy implementation through:
- Native NumPy structured arrays
- Vectorized operations
- Pre-compiled patterns
- Advanced caching
- Compiled critical paths

No backwards compatibility - designed for pure performance.
"""

import numpy as np
import re
from typing import Union, Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
from contextlib import contextmanager
from enum import IntEnum
import functools
import math

# Optional numba import for performance
try:
    import numba
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    # Mock decorator for when numba is not available
    class MockNumba:
        @staticmethod
        def jit(*args, **kwargs):
            def decorator(func):
                return func
            return decorator
    numba = MockNumba()

# Type aliases for clarity and performance
UnitArray = np.ndarray       # Structured array for parsed units
ContextArray = np.ndarray    # Structured array for contexts
ValueArray = Union[np.ndarray, list, tuple, str, float, int]


class UnitType(IntEnum):
    """Unit types as integers for efficient NumPy storage."""
    UNITLESS = 0
    PIXEL = 1
    POINT = 2
    MILLIMETER = 3
    CENTIMETER = 4
    INCH = 5
    EM = 6
    EX = 7
    PERCENT = 8
    VIEWPORT_WIDTH = 9
    VIEWPORT_HEIGHT = 10


# NumPy structured dtypes for maximum performance
UNIT_DTYPE = np.dtype([
    ('value', 'f8'),           # Numeric value (64-bit float)
    ('unit_type', 'u1'),       # Unit type (8-bit unsigned int)
    ('axis_hint', 'u1')        # Axis hint: 0=x, 1=y, 2=both
])

CONTEXT_DTYPE = np.dtype([
    ('viewport_width', 'f8'),   # Viewport width in pixels
    ('viewport_height', 'f8'),  # Viewport height in pixels
    ('font_size', 'f8'),        # Font size in pixels
    ('x_height', 'f8'),         # X-height in pixels
    ('dpi', 'f8'),              # Display DPI
    ('parent_width', 'f8'),     # Parent width for % calculations
    ('parent_height', 'f8')     # Parent height for % calculations
])


class ConversionContext:
    """NumPy-optimized conversion context with vectorized operations."""

    def __init__(self, viewport_width: float = 800.0,
                 viewport_height: float = 600.0,
                 font_size: float = 16.0,
                 dpi: float = 96.0,
                 parent_width: Optional[float] = None,
                 parent_height: Optional[float] = None):
        """Create optimized conversion context."""
        self._data = np.array([(
            viewport_width,
            viewport_height,
            font_size,
            font_size * 0.5,  # x_height
            dpi,
            parent_width or viewport_width,
            parent_height or viewport_height
        )], dtype=CONTEXT_DTYPE)[0]

    @property
    def array(self) -> ContextArray:
        """Get underlying NumPy array."""
        return self._data

    @property
    def viewport_width(self) -> float:
        return float(self._data['viewport_width'])

    @property
    def viewport_height(self) -> float:
        return float(self._data['viewport_height'])

    @property
    def font_size(self) -> float:
        return float(self._data['font_size'])

    @property
    def dpi(self) -> float:
        return float(self._data['dpi'])

    def copy(self) -> 'ConversionContext':
        """Create a copy of this context."""
        result = ConversionContext.__new__(ConversionContext)
        result._data = self._data.copy()
        return result

    def with_updates(self, **kwargs) -> 'ConversionContext':
        """Create updated copy with new values."""
        new_context = self.copy()
        for key, value in kwargs.items():
            if key in ['viewport_width', 'viewport_height', 'font_size',
                      'dpi', 'parent_width', 'parent_height']:
                new_context._data[key] = value
            elif key == 'x_height':
                new_context._data['x_height'] = value
        return new_context


class UnitEngine:
    """
    Ultra-fast NumPy-based unit conversion engine.

    Performance Features:
    - Native NumPy structured arrays for all operations
    - Vectorized batch conversions
    - Pre-computed conversion constants
    - Advanced caching with LRU eviction
    - Compiled critical paths with Numba
    - Context manager for state management
    - Zero-copy operations where possible

    Target: 30-100x speedup over legacy implementation
    """

    # EMU conversion constants
    EMU_PER_INCH = 914400.0

    # Pre-computed conversion factors as NumPy array
    _EMU_CONSTANTS = np.array([
        0.0,                    # UNITLESS (special case)
        EMU_PER_INCH / 96.0,   # PIXEL (at 96 DPI baseline)
        EMU_PER_INCH / 72.0,   # POINT
        EMU_PER_INCH / 25.4,   # MILLIMETER
        EMU_PER_INCH / 2.54,   # CENTIMETER
        EMU_PER_INCH,          # INCH
        0.0,                   # EM (context-dependent)
        0.0,                   # EX (context-dependent)
        0.0,                   # PERCENT (context-dependent)
        0.0,                   # VIEWPORT_WIDTH (context-dependent)
        0.0                    # VIEWPORT_HEIGHT (context-dependent)
    ], dtype=np.float64)

    def __init__(self, default_context: Optional[ConversionContext] = None):
        """Initialize ultra-fast unit conversion engine."""
        self.default_context = default_context or ConversionContext()

        # Pre-compile regex pattern for maximum speed
        self._value_pattern = re.compile(
            r'([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*(.*)$'
        )

        # Unit mapping optimized for lookup speed
        self._unit_lookup = {
            '': UnitType.UNITLESS,
            'px': UnitType.PIXEL,
            'pt': UnitType.POINT,
            'mm': UnitType.MILLIMETER,
            'cm': UnitType.CENTIMETER,
            'in': UnitType.INCH,
            'em': UnitType.EM,
            'ex': UnitType.EX,
            '%': UnitType.PERCENT,
            'vw': UnitType.VIEWPORT_WIDTH,
            'vh': UnitType.VIEWPORT_HEIGHT
        }

        # High-performance LRU cache for parsed results
        self._parse_cache: dict = {}
        self._cache_hits = 0
        self._cache_misses = 0

        # Pre-computed DPI factors for common DPI values
        self._dpi_cache = {}
        for dpi in [72.0, 96.0, 120.0, 150.0, 300.0]:
            self._dpi_cache[dpi] = self.EMU_PER_INCH / dpi

    @functools.lru_cache(maxsize=1000)
    def _parse_single_cached(self, value: str) -> Tuple[float, int]:
        """Parse single unit string with caching."""
        if not isinstance(value, str):
            return 0.0, UnitType.UNITLESS

        value = value.strip()
        if not value:
            return 0.0, UnitType.UNITLESS

        match = self._value_pattern.match(value)
        if not match:
            return 0.0, UnitType.UNITLESS

        numeric_part = float(match.group(1))
        unit_part = match.group(2).lower().strip()

        # Fast unit lookup
        unit_type = self._unit_lookup.get(unit_part, UnitType.UNITLESS)

        # Convert percentage to decimal
        if unit_type == UnitType.PERCENT:
            numeric_part = numeric_part / 100.0

        return numeric_part, unit_type

    def parse_unit(self, value: ValueArray) -> UnitArray:
        """
        Parse unit value(s) into NumPy structured array.

        Args:
            value: Unit string, number, or array of units

        Returns:
            Structured NumPy array with parsed values
        """
        # Handle different input types
        if isinstance(value, (int, float)):
            # Treat numbers as pixels
            return np.array([(float(value), UnitType.PIXEL, 0)], dtype=UNIT_DTYPE)

        if isinstance(value, str):
            # Single string value
            parsed_value, unit_type = self._parse_single_cached(value)
            return np.array([(parsed_value, unit_type, 0)], dtype=UNIT_DTYPE)

        if isinstance(value, (list, tuple)):
            # Convert to numpy array
            value = np.array(value)

        if isinstance(value, np.ndarray):
            # Array of values
            if value.dtype.kind in ['U', 'S', 'O']:  # String arrays
                n_values = len(value)
                result = np.empty(n_values, dtype=UNIT_DTYPE)

                for i, val in enumerate(value):
                    parsed_value, unit_type = self._parse_single_cached(str(val))
                    result[i] = (parsed_value, unit_type, 0)

                return result
            else:
                # Numeric array - treat as pixels
                result = np.empty(len(value), dtype=UNIT_DTYPE)
                result['value'] = value.astype(np.float64)
                result['unit_type'] = UnitType.PIXEL
                result['axis_hint'] = 0
                return result

        # Fallback
        return np.array([(0.0, UnitType.UNITLESS, 0)], dtype=UNIT_DTYPE)

    @staticmethod
    @numba.jit(nopython=True, cache=True)
    def _vectorized_basic_conversion(values: np.ndarray,
                                   unit_types: np.ndarray,
                                   conversion_factors: np.ndarray) -> np.ndarray:
        """Compiled vectorized conversion for basic units."""
        n_values = len(values)
        result = np.zeros(n_values, dtype=np.int32)

        for i in range(n_values):
            unit_type = unit_types[i]
            if unit_type < len(conversion_factors):
                factor = conversion_factors[unit_type]
                if factor > 0:  # Non-context-dependent units
                    result[i] = int(values[i] * factor)

        return result

    def to_emu_batch(self, parsed_units: UnitArray,
                    context: Optional[ConversionContext] = None) -> np.ndarray:
        """
        Convert batch of parsed units to EMUs using vectorized operations.

        Args:
            parsed_units: Structured array from parse_unit
            context: Conversion context (uses default if None)

        Returns:
            Array of EMU values (int32)
        """
        if context is None:
            context = self.default_context

        values = parsed_units['value']
        unit_types = parsed_units['unit_type']
        axis_hints = parsed_units['axis_hint']

        n_values = len(values)
        result = np.zeros(n_values, dtype=np.int32)

        # Get DPI factor efficiently
        dpi = context.dpi
        dpi_factor = self._dpi_cache.get(dpi, self.EMU_PER_INCH / dpi)

        # Create DPI-adjusted conversion factors
        adjusted_factors = self._EMU_CONSTANTS.copy()
        adjusted_factors[UnitType.PIXEL] = dpi_factor

        # Vectorized conversion for basic units
        basic_result = self._vectorized_basic_conversion(
            values, unit_types, adjusted_factors
        )

        # Handle context-dependent units
        context_data = context.array
        for i in range(n_values):
            unit_type = unit_types[i]
            value = values[i]
            axis = axis_hints[i]

            if adjusted_factors[unit_type] > 0:
                # Basic unit - use pre-computed result
                result[i] = basic_result[i]
            else:
                # Context-dependent unit
                if unit_type == UnitType.EM:
                    em_pixels = value * context_data['font_size']
                    result[i] = int(em_pixels * dpi_factor)
                elif unit_type == UnitType.EX:
                    ex_pixels = value * context_data['x_height']
                    result[i] = int(ex_pixels * dpi_factor)
                elif unit_type == UnitType.PERCENT:
                    if axis == 0:  # X-axis
                        parent_pixels = context_data['parent_width'] * value
                    else:  # Y-axis
                        parent_pixels = context_data['parent_height'] * value
                    result[i] = int(parent_pixels * dpi_factor)
                elif unit_type == UnitType.VIEWPORT_WIDTH:
                    vw_pixels = context_data['viewport_width'] * value / 100.0
                    result[i] = int(vw_pixels * dpi_factor)
                elif unit_type == UnitType.VIEWPORT_HEIGHT:
                    vh_pixels = context_data['viewport_height'] * value / 100.0
                    result[i] = int(vh_pixels * dpi_factor)
                elif unit_type == UnitType.UNITLESS:
                    # Treat as pixels
                    result[i] = int(value * dpi_factor)

        return result

    def to_emu(self, value: ValueArray,
              context: Optional[ConversionContext] = None,
              axis: str = 'x') -> int:
        """
        Convert unit value to EMUs.

        Args:
            value: Unit value (string, number, or array)
            context: Conversion context
            axis: 'x' or 'y' for directional calculations

        Returns:
            EMU value (int) or array of EMU values
        """
        parsed = self.parse_unit(value)

        # Set axis hints for single values
        if len(parsed) == 1:
            parsed[0]['axis_hint'] = 1 if axis == 'y' else 0

        emu_values = self.to_emu_batch(parsed, context)

        # Return single value or array based on input
        if len(emu_values) == 1:
            return int(emu_values[0])
        return emu_values

    def batch_to_emu(self, values: Dict[str, ValueArray],
                    context: Optional[ConversionContext] = None) -> Dict[str, int]:
        """
        Convert dictionary of values to EMUs efficiently.

        Args:
            values: Dictionary of {name: unit_value} pairs
            context: Conversion context

        Returns:
            Dictionary of {name: emu_value} pairs
        """
        if not values:
            return {}

        # Parse all values
        names = list(values.keys())
        unit_values = []
        parsed_units_list = []

        for name, value in values.items():
            parsed = self.parse_unit(value)

            # Set axis hint based on attribute name
            axis_hint = 1 if name.lower() in ['y', 'cy', 'height', 'dy', 'y1', 'y2', 'vh'] else 0
            parsed['axis_hint'] = axis_hint

            parsed_units_list.append(parsed)

        # Concatenate all parsed units
        if parsed_units_list:
            all_parsed = np.concatenate(parsed_units_list)
            all_emus = self.to_emu_batch(all_parsed, context)

            # Split results back into dictionary
            result = {}
            idx = 0
            for name, parsed in zip(names, parsed_units_list):
                n_values = len(parsed)
                if n_values == 1:
                    result[name] = int(all_emus[idx])
                else:
                    result[name] = all_emus[idx:idx + n_values].astype(int)
                idx += n_values

            return result

        return {}

    @contextmanager
    def with_context(self, **kwargs):
        """Context manager for temporary context changes."""
        original_context = self.default_context
        try:
            self.default_context = self.default_context.with_updates(**kwargs)
            yield self
        finally:
            self.default_context = original_context

    def with_updates(self, **kwargs) -> 'UnitEngine':
        """Create new engine with updated context."""
        new_engine = UnitEngine.__new__(UnitEngine)
        new_engine.__dict__ = self.__dict__.copy()
        new_engine.default_context = self.default_context.with_updates(**kwargs)
        return new_engine

    @property
    def cache_stats(self) -> dict:
        """Get caching performance statistics."""
        return {
            'hits': self._cache_hits,
            'misses': self._cache_misses,
            'hit_rate': self._cache_hits / max(1, self._cache_hits + self._cache_misses)
        }

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"UnitEngine(dpi={self.default_context.dpi}, "
                f"viewport={self.default_context.viewport_width}x{self.default_context.viewport_height})")


# Convenience functions for direct usage
def create_unit_engine(viewport_width: float = 800.0,
                      viewport_height: float = 600.0,
                      font_size: float = 16.0,
                      dpi: float = 96.0) -> UnitEngine:
    """Create unit engine with specified context."""
    context = ConversionContext(
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        font_size=font_size,
        dpi=dpi
    )
    return UnitEngine(context)


def to_emu(value: ValueArray, axis: str = 'x',
          dpi: float = 96.0, font_size: float = 16.0) -> Union[int, np.ndarray]:
    """Convert unit value to EMUs using default settings."""
    engine = create_unit_engine(dpi=dpi, font_size=font_size)
    return engine.to_emu(value, axis=axis)


def batch_to_emu(values: Dict[str, ValueArray],
                dpi: float = 96.0, font_size: float = 16.0) -> Dict[str, int]:
    """Convert batch of values to EMUs using default settings."""
    engine = create_unit_engine(dpi=dpi, font_size=font_size)
    return engine.batch_to_emu(values)


def parse_unit_batch(values: ValueArray) -> UnitArray:
    """Parse batch of unit values into structured array."""
    engine = UnitEngine()
    return engine.parse_unit(values)