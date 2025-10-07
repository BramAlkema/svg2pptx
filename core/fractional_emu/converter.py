#!/usr/bin/env python3
"""
Fractional EMU Converter

Core converter for maintaining float64 precision throughout coordinate pipeline.
Only rounds to int at final XML serialization.
"""

import logging
from typing import Optional, Union
from decimal import Decimal, ROUND_HALF_UP

from .constants import (
    EMU_PER_INCH,
    EMU_PER_POINT,
    EMU_PER_MM,
    EMU_PER_CM,
    DEFAULT_DPI,
    MIN_EMU_VALUE,
    MAX_EMU_VALUE,
)
from .types import PrecisionMode, PrecisionContext
from .errors import (
    CoordinateValidationError,
    PrecisionOverflowError,
    EMUBoundaryError,
)


class FractionalEMUConverter:
    """
    Fractional EMU coordinate converter.
    
    Maintains float64 precision throughout conversion pipeline.
    Integrates with existing UnitConverter via ConversionServices.
    """

    def __init__(
        self,
        precision_mode: PrecisionMode = PrecisionMode.STANDARD,
        dpi: float = DEFAULT_DPI,
        validate_bounds: bool = True,
    ):
        """
        Initialize fractional EMU converter.

        Args:
            precision_mode: Precision level for calculations
            dpi: Display DPI for pixel conversions
            validate_bounds: Whether to validate EMU bounds
        """
        self.precision_mode = precision_mode
        self.dpi = dpi
        self.validate_bounds = validate_bounds
        
        # Precision scale factors
        self.scale_factor = float(precision_mode.value)
        
        # Conversion cache for performance
        self._cache = {}
        
        # Logging
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def pixels_to_fractional_emu(
        self,
        pixels: float,
        dpi: Optional[float] = None,
    ) -> float:
        """
        Convert pixels to fractional EMU (float64).

        Args:
            pixels: Pixel value
            dpi: Display DPI (uses instance DPI if not provided)

        Returns:
            Float EMU value with precision maintained

        Examples:
            >>> converter.pixels_to_fractional_emu(100.5)
            957262.5  # Fractional precision maintained
        """
        if dpi is None:
            dpi = self.dpi
            
        # Maintain float precision throughout
        emu = (pixels / dpi) * EMU_PER_INCH
        
        if self.validate_bounds:
            self._validate_emu_bounds(emu, pixels)
            
        return emu

    def points_to_fractional_emu(self, points: float) -> float:
        """
        Convert points to fractional EMU.

        Args:
            points: Point value

        Returns:
            Float EMU value
        """
        emu = points * EMU_PER_POINT
        
        if self.validate_bounds:
            self._validate_emu_bounds(emu, points)
            
        return emu

    def mm_to_fractional_emu(self, mm: float) -> float:
        """Convert millimeters to fractional EMU."""
        emu = mm * EMU_PER_MM
        
        if self.validate_bounds:
            self._validate_emu_bounds(emu, mm)
            
        return emu

    def cm_to_fractional_emu(self, cm: float) -> float:
        """Convert centimeters to fractional EMU."""
        emu = cm * EMU_PER_CM
        
        if self.validate_bounds:
            self._validate_emu_bounds(emu, cm)
            
        return emu

    def inches_to_fractional_emu(self, inches: float) -> float:
        """Convert inches to fractional EMU."""
        emu = inches * EMU_PER_INCH
        
        if self.validate_bounds:
            self._validate_emu_bounds(emu, inches)
            
        return emu

    def transform_point(
        self,
        x: float,
        y: float,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        translate_x: float = 0.0,
        translate_y: float = 0.0,
    ) -> tuple[float, float]:
        """
        Transform point coordinates (fractional).

        Args:
            x, y: Input coordinates
            scale_x, scale_y: Scale factors
            translate_x, translate_y: Translation offsets

        Returns:
            Tuple of (emu_x, emu_y) as float values
        """
        emu_x = x * scale_x + translate_x
        emu_y = y * scale_y + translate_y
        
        if self.validate_bounds:
            self._validate_emu_bounds(emu_x, x)
            self._validate_emu_bounds(emu_y, y)
            
        return emu_x, emu_y

    def round_to_emu(
        self,
        fractional_emu: float,
        mode: str = "half_up",
    ) -> int:
        """
        Round fractional EMU to integer for XML serialization.

        Args:
            fractional_emu: Float EMU value
            mode: Rounding mode ('half_up', 'floor', 'ceiling')

        Returns:
            Integer EMU value for XML output
        """
        if mode == "half_up":
            # Use Decimal for precise rounding
            return int(Decimal(str(fractional_emu)).quantize(
                Decimal('1'),
                rounding=ROUND_HALF_UP
            ))
        elif mode == "floor":
            return int(fractional_emu)
        elif mode == "ceiling":
            import math
            return math.ceil(fractional_emu)
        else:
            raise ValueError(f"Unknown rounding mode: {mode}")

    def batch_transform_points(
        self,
        points: list[tuple[float, float]],
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        translate_x: float = 0.0,
        translate_y: float = 0.0,
    ) -> list[tuple[float, float]]:
        """
        Transform multiple points efficiently.

        Args:
            points: List of (x, y) coordinate tuples
            scale_x, scale_y: Scale factors
            translate_x, translate_y: Translation offsets

        Returns:
            List of transformed (emu_x, emu_y) tuples
        """
        return [
            self.transform_point(x, y, scale_x, scale_y, translate_x, translate_y)
            for x, y in points
        ]

    def _validate_emu_bounds(self, emu: float, original_value: float):
        """
        Validate EMU value is within PowerPoint bounds.

        Args:
            emu: EMU value to validate
            original_value: Original input value for error messages

        Raises:
            EMUBoundaryError: If EMU exceeds PowerPoint limits
        """
        if emu < MIN_EMU_VALUE or emu > MAX_EMU_VALUE:
            raise EMUBoundaryError(
                f"EMU value {emu} (from {original_value}) exceeds PowerPoint "
                f"bounds [{MIN_EMU_VALUE}, {MAX_EMU_VALUE}]"
            )

    def create_precision_context(
        self,
        scale_factor: Optional[float] = None,
        validate: bool = True,
    ) -> PrecisionContext:
        """
        Create precision context for calculations.

        Args:
            scale_factor: Optional scale factor override
            validate: Whether to validate bounds

        Returns:
            PrecisionContext instance
        """
        return PrecisionContext(
            mode=self.precision_mode,
            scale_factor=scale_factor or self.scale_factor,
            validate=validate,
        )

    def clear_cache(self):
        """Clear conversion cache."""
        self._cache.clear()

    def get_stats(self) -> dict:
        """
        Get converter statistics.

        Returns:
            Dictionary with stats (cache size, precision mode, etc.)
        """
        return {
            'precision_mode': self.precision_mode.name,
            'scale_factor': self.scale_factor,
            'dpi': self.dpi,
            'cache_size': len(self._cache),
            'validate_bounds': self.validate_bounds,
        }
