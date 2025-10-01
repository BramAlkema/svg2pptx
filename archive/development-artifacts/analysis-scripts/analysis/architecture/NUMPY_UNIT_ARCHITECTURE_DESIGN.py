#!/usr/bin/env python3
"""
NumPy Unit Conversion Architecture Design

Ultra-fast unit conversion system targeting 30-100x performance improvements
over legacy implementation through pure NumPy design without backwards compatibility.

Design Principles:
- Pure NumPy structured arrays for all data
- Vectorized operations for batch processing
- Pre-compiled regex patterns and lookup tables
- Zero-copy operations where possible
- Memory-efficient cache management
- Compiled critical paths with Numba
"""

import numpy as np
import re
from typing import Union, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import IntEnum
import numba
from functools import lru_cache


# ============================================================================
# Core Type Definitions - Optimized for NumPy
# ============================================================================

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
PARSED_UNIT_DTYPE = np.dtype([
    ('value', 'f8'),           # Numeric value (64-bit float)
    ('unit_type', 'u1'),       # Unit type (8-bit unsigned int)
    ('axis_hint', 'u1')        # Axis hint: 0=x, 1=y, 2=both
])

CONVERSION_CONTEXT_DTYPE = np.dtype([
    ('viewport_width', 'f8'),   # Viewport width in pixels
    ('viewport_height', 'f8'),  # Viewport height in pixels
    ('font_size', 'f8'),        # Font size in pixels
    ('x_height', 'f8'),         # X-height in pixels
    ('dpi', 'f8'),              # Display DPI
    ('parent_width', 'f8'),     # Parent width for % calculations
    ('parent_height', 'f8')     # Parent height for % calculations
])


# ============================================================================
# Pre-computed Conversion Constants - NumPy Arrays
# ============================================================================

# EMU conversion factors as NumPy array for vectorized operations
EMU_PER_INCH = 914400.0
EMU_CONSTANTS = np.array([
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


# ============================================================================
# Ultra-Fast String Parsing Engine
# ============================================================================

class VectorizedUnitParser:
    """
    NumPy-optimized unit parsing engine with pre-compiled patterns
    and vectorized string processing.
    """

    def __init__(self):
        # Pre-compile all regex patterns for maximum speed
        self._value_pattern = re.compile(
            r'([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*(.*)$'
        )

        # Unit mapping optimized for lookup speed
        self._unit_map = np.array([
            ('', UnitType.UNITLESS),
            ('px', UnitType.PIXEL),
            ('pt', UnitType.POINT),
            ('mm', UnitType.MILLIMETER),
            ('cm', UnitType.CENTIMETER),
            ('in', UnitType.INCH),
            ('em', UnitType.EM),
            ('ex', UnitType.EX),
            ('%', UnitType.PERCENT),
            ('vw', UnitType.VIEWPORT_WIDTH),
            ('vh', UnitType.VIEWPORT_HEIGHT)
        ], dtype=[('unit', 'U4'), ('type', 'u1')])

        # Create lookup dictionary for O(1) access
        self._unit_lookup = {unit: unit_type for unit, unit_type in self._unit_map}

        # Pre-computed common values cache (LRU)
        self._parse_cache = {}
        self._cache_size = 1000  # Configurable cache size

    @lru_cache(maxsize=1000)
    def parse_single(self, value: str) -> Tuple[float, int]:
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

    def parse_batch(self, values: np.ndarray) -> np.ndarray:
        """
        Parse batch of unit strings into structured NumPy array.

        Args:
            values: Array of unit strings

        Returns:
            Structured array with parsed values
        """
        n_values = len(values)
        result = np.empty(n_values, dtype=PARSED_UNIT_DTYPE)

        for i, value in enumerate(values):
            parsed_value, unit_type = self.parse_single(str(value))
            result[i] = (parsed_value, unit_type, 0)  # Default axis hint

        return result

    def parse_dict_batch(self, value_dict: Dict[str, str]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Parse dictionary of {name: value} into parallel arrays.

        Returns:
            (names_array, parsed_values_array)
        """
        names = list(value_dict.keys())
        values = list(value_dict.values())

        parsed_values = self.parse_batch(np.array(values))

        # Set axis hints based on attribute names
        for i, name in enumerate(names):
            if name.lower() in ['y', 'cy', 'height', 'dy', 'y1', 'y2', 'vh']:
                parsed_values[i]['axis_hint'] = 1  # Y-axis
            else:
                parsed_values[i]['axis_hint'] = 0  # X-axis

        return np.array(names), parsed_values


# ============================================================================
# Vectorized Conversion Engine
# ============================================================================

class NumPyUnitConverter:
    """
    Ultra-fast NumPy-based unit conversion engine.

    Performance Features:
    - Vectorized batch operations
    - Pre-computed conversion matrices
    - Context-aware percentage resolution
    - Memory-efficient structured arrays
    - Zero-copy operations where possible
    """

    def __init__(self):
        self.parser = VectorizedUnitParser()

        # Default conversion context
        self.default_context = np.array([(
            800.0,  # viewport_width
            600.0,  # viewport_height
            16.0,   # font_size
            8.0,    # x_height
            96.0,   # dpi
            800.0,  # parent_width
            600.0   # parent_height
        )], dtype=CONVERSION_CONTEXT_DTYPE)[0]

        # Pre-computed DPI scaling factors for common DPI values
        self._dpi_cache = {}
        for dpi in [72.0, 96.0, 120.0, 150.0, 300.0]:
            self._dpi_cache[dpi] = EMU_PER_INCH / dpi

    @staticmethod
    @numba.jit(nopython=True, cache=True)
    def _vectorized_pixel_to_emu(values: np.ndarray, dpi: float) -> np.ndarray:
        """Compiled vectorized pixel to EMU conversion."""
        emu_per_pixel = EMU_PER_INCH / dpi
        return (values * emu_per_pixel).astype(np.int32)

    @staticmethod
    @numba.jit(nopython=True, cache=True)
    def _vectorized_basic_conversion(values: np.ndarray,
                                   unit_types: np.ndarray,
                                   conversion_factors: np.ndarray) -> np.ndarray:
        """Compiled vectorized conversion for basic units."""
        n_values = len(values)
        result = np.empty(n_values, dtype=np.int32)

        for i in range(n_values):
            unit_type = unit_types[i]
            if unit_type < len(conversion_factors):
                factor = conversion_factors[unit_type]
                if factor > 0:  # Non-context-dependent units
                    result[i] = int(values[i] * factor)
                else:
                    result[i] = 0  # Will be handled separately
            else:
                result[i] = 0

        return result

    def convert_batch(self, parsed_units: np.ndarray,
                     context: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Convert batch of parsed units to EMUs using vectorized operations.

        Args:
            parsed_units: Structured array from parse_batch
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

        # Create DPI-adjusted conversion factors
        dpi_factor = EMU_PER_INCH / context['dpi']
        adjusted_factors = EMU_CONSTANTS.copy()
        adjusted_factors[UnitType.PIXEL] = dpi_factor

        # Vectorized conversion for basic units
        basic_result = self._vectorized_basic_conversion(
            values, unit_types, adjusted_factors
        )

        # Handle context-dependent units
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
                    em_pixels = value * context['font_size']
                    result[i] = int(em_pixels * dpi_factor)
                elif unit_type == UnitType.EX:
                    ex_pixels = value * context['x_height']
                    result[i] = int(ex_pixels * dpi_factor)
                elif unit_type == UnitType.PERCENT:
                    if axis == 0:  # X-axis
                        parent_pixels = context['parent_width'] * value
                    else:  # Y-axis
                        parent_pixels = context['parent_height'] * value
                    result[i] = int(parent_pixels * dpi_factor)
                elif unit_type == UnitType.VIEWPORT_WIDTH:
                    vw_pixels = context['viewport_width'] * value / 100.0
                    result[i] = int(vw_pixels * dpi_factor)
                elif unit_type == UnitType.VIEWPORT_HEIGHT:
                    vh_pixels = context['viewport_height'] * value / 100.0
                    result[i] = int(vh_pixels * dpi_factor)
                elif unit_type == UnitType.UNITLESS:
                    # Treat as pixels
                    result[i] = int(value * dpi_factor)

        return result

    def convert_single(self, value: Union[str, float],
                      context: Optional[np.ndarray] = None,
                      axis: str = 'x') -> int:
        """Convert single value (convenience method)."""
        if isinstance(value, (int, float)):
            value = f"{value}px"

        parsed = self.parser.parse_batch(np.array([str(value)]))

        # Set axis hint
        parsed[0]['axis_hint'] = 1 if axis == 'y' else 0

        result = self.convert_batch(parsed, context)
        return int(result[0])

    def convert_dict_batch(self, values: Dict[str, Union[str, float]],
                          context: Optional[np.ndarray] = None) -> Dict[str, int]:
        """Convert dictionary of values efficiently."""
        names, parsed_values = self.parser.parse_dict_batch({
            k: str(v) for k, v in values.items()
        })

        emu_values = self.convert_batch(parsed_values, context)

        return {name: int(emu_val) for name, emu_val in zip(names, emu_values)}

    def create_context(self, viewport_width: float = 800.0,
                      viewport_height: float = 600.0,
                      font_size: float = 16.0,
                      dpi: float = 96.0,
                      parent_width: Optional[float] = None,
                      parent_height: Optional[float] = None) -> np.ndarray:
        """Create optimized conversion context."""
        return np.array([(
            viewport_width,
            viewport_height,
            font_size,
            font_size * 0.5,  # x_height
            dpi,
            parent_width or viewport_width,
            parent_height or viewport_height
        )], dtype=CONVERSION_CONTEXT_DTYPE)[0]


# ============================================================================
# Advanced Caching System
# ============================================================================

class ConversionCache:
    """High-performance caching system for unit conversions."""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._cache = {}
        self._access_count = {}

    def get_cached_conversion(self, key: str) -> Optional[int]:
        """Get cached conversion result."""
        if key in self._cache:
            self._access_count[key] += 1
            return self._cache[key]
        return None

    def cache_conversion(self, key: str, result: int):
        """Cache conversion result with LRU eviction."""
        if len(self._cache) >= self.max_size:
            # Evict least recently used
            lru_key = min(self._access_count.keys(),
                         key=lambda k: self._access_count[k])
            del self._cache[lru_key]
            del self._access_count[lru_key]

        self._cache[key] = result
        self._access_count[key] = 1


# ============================================================================
# Public API - NumPy Optimized Unit Converter
# ============================================================================

class UltraFastUnitEngine:
    """
    Public API for ultra-fast NumPy-based unit conversion.

    Targets 30-100x performance improvement over legacy implementation.
    """

    def __init__(self, default_dpi: float = 96.0,
                 viewport_width: float = 800.0,
                 viewport_height: float = 600.0,
                 cache_size: int = 10000):
        """Initialize ultra-fast unit conversion engine."""
        self.converter = NumPyUnitConverter()
        self.cache = ConversionCache(cache_size)

        self.default_context = self.converter.create_context(
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            dpi=default_dpi
        )

    def to_emu(self, value: Union[str, float], axis: str = 'x') -> int:
        """Convert single value to EMU."""
        return self.converter.convert_single(value, self.default_context, axis)

    def batch_to_emu(self, values: Dict[str, Union[str, float]]) -> Dict[str, int]:
        """Convert batch of values to EMU (vectorized)."""
        return self.converter.convert_dict_batch(values, self.default_context)

    def with_context(self, **kwargs) -> 'UltraFastUnitEngine':
        """Create new engine instance with updated context."""
        new_engine = UltraFastUnitEngine()
        new_engine.default_context = self.converter.create_context(**kwargs)
        return new_engine


# ============================================================================
# Performance Testing Framework
# ============================================================================

def benchmark_numpy_performance():
    """Benchmark the NumPy unit conversion performance."""
    print("=== NumPy Unit Conversion Performance Test ===")

    engine = UltraFastUnitEngine()

    # Test batch conversion performance
    test_batch = {
        f'attr_{i}': f"{i % 100}px" for i in range(10000)
    }

    import time
    start_time = time.time()
    results = engine.batch_to_emu(test_batch)
    numpy_time = time.time() - start_time

    print(f"NumPy batch conversion: {len(test_batch)} values in {numpy_time:.4f}s")
    print(f"NumPy conversion rate: {len(test_batch)/numpy_time:,.0f} conversions/sec")

    return numpy_time


if __name__ == "__main__":
    # Demonstration of NumPy architecture
    engine = UltraFastUnitEngine()

    # Single conversions
    print("Single conversions:")
    print(f"100px -> {engine.to_emu('100px')} EMU")
    print(f"1in -> {engine.to_emu('1in')} EMU")
    print(f"2em -> {engine.to_emu('2em')} EMU")

    # Batch conversions
    print("\nBatch conversions:")
    batch = {
        'x': '50px', 'y': '100px',
        'width': '200px', 'height': '150px',
        'font-size': '16px'
    }
    results = engine.batch_to_emu(batch)
    for name, emu in results.items():
        print(f"{name}: {batch[name]} -> {emu} EMU")

    # Performance benchmark
    print(f"\nPerformance benchmark:")
    benchmark_numpy_performance()