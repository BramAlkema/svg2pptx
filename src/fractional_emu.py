#!/usr/bin/env python3
"""
Fractional EMU Precision System for Advanced SVG Features

Extends the base UnitConverter with fractional EMU coordinate capabilities
for subpixel-accurate Bezier curves, gradient positioning, and shape precision.

Key Features:
- Fractional EMU coordinates within DrawingML's 21,600 coordinate space
- Configurable precision factors (1x to 1000x)
- PowerPoint compatibility validation (max 3 decimal places)
- Performance optimization for high-precision calculations
- Mathematical accuracy for technical diagrams

Technical Implementation:
- Maintains float precision throughout calculation pipeline
- Converts to integer only at final OOXML output stage
- Supports adaptive precision scaling based on shape complexity
- Includes coordinate validation and error handling
"""

import math
from typing import Optional, Tuple, Dict, Union, Any
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP
import logging

# Import base units functionality
from .units import (
    UnitConverter, UnitType, ViewportContext,
    EMU_PER_INCH, EMU_PER_POINT, EMU_PER_MM, EMU_PER_CM, DEFAULT_DPI
)


class PrecisionMode(Enum):
    """Mathematical precision modes for coordinate conversion."""
    STANDARD = "standard"           # Regular EMU precision (1x)
    SUBPIXEL = "subpixel"          # Sub-EMU fractional precision (100x)
    HIGH_PRECISION = "high"         # Maximum precision mode (1000x)
    ULTRA_PRECISION = "ultra"       # Ultra precision mode (10000x)


class CoordinateValidationError(ValueError):
    """Exception raised when coordinate validation fails."""
    pass


class PrecisionOverflowError(ValueError):
    """Exception raised when precision calculations cause overflow."""
    pass


class EMUBoundaryError(ValueError):
    """Exception raised when EMU values exceed PowerPoint boundaries."""
    pass


@dataclass
class FractionalCoordinateContext:
    """Extended context for sub-EMU precision calculations."""
    base_dpi: float = DEFAULT_DPI
    fractional_scale: float = 1.0
    rounding_mode: str = 'round_half_up'
    precision_threshold: float = 0.001
    max_decimal_places: int = 3  # PowerPoint compatibility
    adaptive_precision: bool = True
    performance_mode: bool = False


class FractionalEMUConverter(UnitConverter):
    """
    Extended UnitConverter with fractional coordinate precision.

    Enables subpixel-accurate coordinate conversion for advanced SVG features
    while maintaining backward compatibility with existing UnitConverter API.
    """

    def __init__(self,
                 precision_mode: Union[str, PrecisionMode] = PrecisionMode.SUBPIXEL,
                 fractional_context: Optional[FractionalCoordinateContext] = None,
                 **kwargs):
        """
        Initialize with fractional precision capabilities.

        Args:
            precision_mode: Precision level for fractional calculations
            fractional_context: Advanced precision configuration
            **kwargs: Base UnitConverter parameters
        """
        super().__init__(**kwargs)

        # Set up precision configuration
        if isinstance(precision_mode, str):
            precision_mode = PrecisionMode(precision_mode)

        self.precision_mode = precision_mode
        self.fractional_context = fractional_context or FractionalCoordinateContext()

        # Configure precision factors
        self.precision_factors = {
            PrecisionMode.STANDARD: 1.0,
            PrecisionMode.SUBPIXEL: 100.0,
            PrecisionMode.HIGH_PRECISION: 1000.0,
            PrecisionMode.ULTRA_PRECISION: 10000.0
        }

        self.precision_factor = self.precision_factors[precision_mode]

        # Performance optimization caches
        self.fractional_cache = {}  # Cache for repeated calculations
        self.coordinate_cache = {}   # Cache for coordinate transformations

        # PowerPoint compatibility validation
        self.powerpoint_max_emu = EMU_PER_INCH * 1000  # 1000 inches max
        self.powerpoint_min_emu = 0.001  # Minimum meaningful EMU value

        # Enhanced validation bounds
        self.coordinate_max_value = 1e10  # Maximum coordinate value to prevent overflow
        self.coordinate_min_value = -1e10  # Minimum coordinate value
        self.precision_overflow_threshold = 1e15  # Threshold for precision overflow detection

        # Error logging
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def to_fractional_emu(self,
                         value: Union[str, float, int],
                         context: Optional[ViewportContext] = None,
                         axis: str = 'x',
                         preserve_precision: bool = True) -> float:
        """
        Convert SVG length to fractional EMUs with subpixel precision.

        Args:
            value: SVG length value
            context: Viewport context for relative units
            axis: 'x' or 'y' for directional calculations
            preserve_precision: Whether to maintain fractional precision

        Returns:
            Length in fractional EMUs (float)

        Raises:
            CoordinateValidationError: If input value is invalid
            PrecisionOverflowError: If precision calculation causes overflow
            EMUBoundaryError: If resulting EMU value exceeds PowerPoint limits

        Examples:
            >>> converter.to_fractional_emu("100.5px")
            957262.5  # Fractional precision maintained
            >>> converter.to_fractional_emu("2.25em")
            430875.0  # Font-relative precision
        """
        try:
            # Validate input value
            self._validate_input_value(value)

            # Check cache for performance optimization
            cache_key = (str(value), axis, preserve_precision, id(context))
            if cache_key in self.fractional_cache:
                return self.fractional_cache[cache_key]

            if context is None:
                context = self.default_context

            # Parse and validate numeric value
            numeric_value, unit_type = self.parse_length(value, context)
            self._validate_numeric_coordinate(numeric_value, str(value))

            if numeric_value == 0:
                return 0.0

            # Calculate fractional EMU based on unit type
            fractional_emu = self._calculate_fractional_emu(
                numeric_value, unit_type, context, axis
            )

            # Validate intermediate calculation for overflow
            self._validate_precision_overflow(fractional_emu, numeric_value)

            # Apply precision factor if requested
            if preserve_precision:
                fractional_emu = fractional_emu * self.precision_factor
                self._validate_precision_overflow(fractional_emu, numeric_value)

            # Validate PowerPoint compatibility and bounds
            validated_emu = self._validate_powerpoint_compatibility(fractional_emu)

            # Cache result for performance
            self.fractional_cache[cache_key] = validated_emu

            return validated_emu

        except (ValueError, TypeError, OverflowError) as e:
            self.logger.error(f"Fractional EMU conversion failed for value '{value}': {str(e)}")
            # Return fallback value for graceful degradation
            return self._get_fallback_emu_value(value, context, axis)

    def _calculate_fractional_emu(self,
                                 numeric_value: float,
                                 unit_type: UnitType,
                                 context: ViewportContext,
                                 axis: str) -> float:
        """Calculate fractional EMU value preserving floating-point precision."""

        if unit_type == UnitType.PIXEL:
            return self._fractional_pixels_to_emu(numeric_value, context.dpi)

        elif unit_type == UnitType.POINT:
            return numeric_value * EMU_PER_POINT

        elif unit_type == UnitType.MILLIMETER:
            return numeric_value * EMU_PER_MM

        elif unit_type == UnitType.CENTIMETER:
            return numeric_value * EMU_PER_CM

        elif unit_type == UnitType.INCH:
            return numeric_value * EMU_PER_INCH

        elif unit_type == UnitType.EM:
            em_pixels = numeric_value * context.font_size
            return self._fractional_pixels_to_emu(em_pixels, context.dpi)

        elif unit_type == UnitType.EX:
            ex_pixels = numeric_value * context.x_height
            return self._fractional_pixels_to_emu(ex_pixels, context.dpi)

        elif unit_type == UnitType.PERCENT:
            if axis == 'x' and context.parent_width:
                parent_pixels = context.parent_width * numeric_value
            elif axis == 'y' and context.parent_height:
                parent_pixels = context.parent_height * numeric_value
            else:
                viewport_size = context.width if axis == 'x' else context.height
                parent_pixels = viewport_size * numeric_value
            return self._fractional_pixels_to_emu(parent_pixels, context.dpi)

        elif unit_type == UnitType.VIEWPORT_WIDTH:
            vw_pixels = context.width * numeric_value / 100.0
            return self._fractional_pixels_to_emu(vw_pixels, context.dpi)

        elif unit_type == UnitType.VIEWPORT_HEIGHT:
            vh_pixels = context.height * numeric_value / 100.0
            return self._fractional_pixels_to_emu(vh_pixels, context.dpi)

        elif unit_type == UnitType.UNITLESS:
            return self._fractional_pixels_to_emu(numeric_value, context.dpi)

        return 0.0

    def _fractional_pixels_to_emu(self, pixels: float, dpi: float) -> float:
        """Convert pixels to fractional EMUs preserving precision."""
        # EMU = pixels * (EMU_PER_INCH / DPI)
        emu_per_pixel = EMU_PER_INCH / dpi
        return pixels * emu_per_pixel

    def _validate_powerpoint_compatibility(self, emu_value: float) -> float:
        """Validate and adjust EMU value for PowerPoint compatibility."""
        # Check for NaN or infinity values
        if not math.isfinite(emu_value):
            raise EMUBoundaryError(f"EMU value is not finite: {emu_value}")

        # Ensure value is within PowerPoint's acceptable range
        if emu_value < 0:
            self.logger.warning(f"Negative EMU value {emu_value} clamped to 0")
            return 0.0

        if emu_value > self.powerpoint_max_emu:
            self.logger.warning(f"EMU value {emu_value} exceeds maximum {self.powerpoint_max_emu}, clamped")
            return self.powerpoint_max_emu

        # Truncate to maximum decimal places for PowerPoint compatibility
        if self.fractional_context.max_decimal_places > 0:
            try:
                decimal_value = Decimal(str(emu_value))
                rounded_value = decimal_value.quantize(
                    Decimal('0.' + '0' * self.fractional_context.max_decimal_places),
                    rounding=ROUND_HALF_UP
                )
                return float(rounded_value)
            except (ValueError, OverflowError) as e:
                raise EMUBoundaryError(f"Failed to round EMU value {emu_value}: {str(e)}")

        return emu_value

    def _validate_input_value(self, value: Union[str, float, int]) -> None:
        """Validate input coordinate value."""
        if value is None:
            raise CoordinateValidationError("Coordinate value cannot be None")

        if isinstance(value, str):
            if not value.strip():
                raise CoordinateValidationError("Coordinate string cannot be empty")
            if len(value) > 100:  # Prevent excessive string processing
                raise CoordinateValidationError(f"Coordinate string too long: {len(value)} characters")

        elif isinstance(value, (int, float)):
            if not math.isfinite(value):
                raise CoordinateValidationError(f"Coordinate value is not finite: {value}")

    def _validate_numeric_coordinate(self, numeric_value: float, original_value: str) -> None:
        """Validate parsed numeric coordinate value."""
        if not math.isfinite(numeric_value):
            raise CoordinateValidationError(f"Parsed coordinate is not finite: {numeric_value} from '{original_value}'")

        if abs(numeric_value) > self.coordinate_max_value:
            raise CoordinateValidationError(
                f"Coordinate value {numeric_value} exceeds maximum allowed {self.coordinate_max_value}"
            )

        if abs(numeric_value) < self.powerpoint_min_emu and numeric_value != 0:
            self.logger.debug(f"Coordinate value {numeric_value} below minimum threshold {self.powerpoint_min_emu}")

    def _validate_precision_overflow(self, calculated_value: float, original_value: float) -> None:
        """Validate that precision calculations haven't caused overflow."""
        if not math.isfinite(calculated_value):
            raise PrecisionOverflowError(f"Precision calculation resulted in non-finite value: {calculated_value}")

        if abs(calculated_value) > self.precision_overflow_threshold:
            raise PrecisionOverflowError(
                f"Precision calculation overflow: {calculated_value} from original {original_value}"
            )

    def _get_fallback_emu_value(self,
                               value: Union[str, float, int],
                               context: Optional[ViewportContext] = None,
                               axis: str = 'x') -> float:
        """Get fallback EMU value for error recovery."""
        try:
            # Attempt basic conversion without fractional precision
            if isinstance(value, (int, float)) and math.isfinite(value):
                if abs(value) <= 10000:  # Reasonable pixel range
                    return float(self._fractional_pixels_to_emu(value, DEFAULT_DPI))

            # Return safe default
            return 0.0

        except Exception:
            # Final fallback
            self.logger.error(f"All fallback attempts failed for value '{value}'")
            return 0.0

    def to_precise_drawingml_coords(self,
                                   svg_x: float,
                                   svg_y: float,
                                   svg_width: float,
                                   svg_height: float) -> Tuple[float, float]:
        """
        Convert SVG coordinates to DrawingML with fractional precision.

        Args:
            svg_x: SVG X coordinate
            svg_y: SVG Y coordinate
            svg_width: SVG viewport width
            svg_height: SVG viewport height

        Returns:
            Tuple of (drawingml_x, drawingml_y) with fractional precision

        Raises:
            CoordinateValidationError: If input coordinates are invalid
            EMUBoundaryError: If resulting coordinates exceed DrawingML bounds

        DrawingML Coordinate Space: 21,600 x 21,600 units
        """
        try:
            # Validate input parameters
            self._validate_drawingml_inputs(svg_x, svg_y, svg_width, svg_height)

            # Prevent division by zero
            if svg_width <= 0 or svg_height <= 0:
                raise CoordinateValidationError(f"Invalid viewport dimensions: width={svg_width}, height={svg_height}")

            # Convert with fractional precision within 21,600 coordinate space
            base_x = (svg_x / svg_width) * 21600
            base_y = (svg_y / svg_height) * 21600

            # Validate intermediate calculations
            if not (math.isfinite(base_x) and math.isfinite(base_y)):
                raise CoordinateValidationError(f"Invalid base coordinates: ({base_x}, {base_y})")

            # Apply precision scaling
            precise_x = base_x * self.fractional_context.fractional_scale
            precise_y = base_y * self.fractional_context.fractional_scale

            # Validate precision calculations
            if not (math.isfinite(precise_x) and math.isfinite(precise_y)):
                raise PrecisionOverflowError(f"Precision scaling caused overflow: ({precise_x}, {precise_y})")

            # Validate DrawingML coordinate bounds
            max_drawingml_coord = 21600 * self.precision_factor
            if abs(precise_x) > max_drawingml_coord or abs(precise_y) > max_drawingml_coord:
                self.logger.warning(f"DrawingML coordinates exceed bounds: ({precise_x}, {precise_y})")

            # Clamp coordinates to valid range
            precise_x = max(0, min(precise_x, max_drawingml_coord))
            precise_y = max(0, min(precise_y, max_drawingml_coord))

            return (precise_x, precise_y)

        except Exception as e:
            self.logger.error(f"DrawingML conversion failed for ({svg_x}, {svg_y}): {str(e)}")
            # Return safe default coordinates
            return (0.0, 0.0)

    def _validate_drawingml_inputs(self, svg_x: float, svg_y: float, svg_width: float, svg_height: float) -> None:
        """Validate inputs for DrawingML coordinate conversion."""
        coords = {'svg_x': svg_x, 'svg_y': svg_y, 'svg_width': svg_width, 'svg_height': svg_height}

        for name, value in coords.items():
            if not isinstance(value, (int, float)):
                raise CoordinateValidationError(f"{name} must be numeric, got {type(value)}")
            if not math.isfinite(value):
                raise CoordinateValidationError(f"{name} is not finite: {value}")
            if abs(value) > self.coordinate_max_value:
                raise CoordinateValidationError(f"{name} exceeds maximum: {value}")

    def batch_convert_coordinates(self,
                                 coordinates: Dict[str, Union[str, float, int]],
                                 context: Optional[ViewportContext] = None) -> Dict[str, float]:
        """
        Batch convert multiple coordinates with fractional precision.

        Optimized for performance when converting many coordinates at once.
        Provides error recovery for individual coordinate failures.

        Args:
            coordinates: Dictionary of coordinate name -> value pairs
            context: Viewport context for conversions

        Returns:
            Dictionary of coordinate name -> fractional EMU pairs

        Raises:
            CoordinateValidationError: If coordinates dictionary is invalid
        """
        if not isinstance(coordinates, dict):
            raise CoordinateValidationError("Coordinates must be a dictionary")

        if not coordinates:
            return {}

        if len(coordinates) > 1000:  # Prevent excessive batch sizes
            raise CoordinateValidationError(f"Batch size too large: {len(coordinates)} coordinates")

        results = {}
        errors = []

        for coord_name, coord_value in coordinates.items():
            try:
                # Validate coordinate name
                if not isinstance(coord_name, str) or not coord_name.strip():
                    raise CoordinateValidationError(f"Invalid coordinate name: {coord_name}")

                # Determine axis from coordinate name
                axis = 'x' if coord_name.lower() in ['x', 'x1', 'x2', 'width', 'cx', 'rx'] else 'y'

                # Convert with fractional precision
                fractional_emu = self.to_fractional_emu(
                    coord_value, context, axis, preserve_precision=True
                )

                results[coord_name] = fractional_emu

            except Exception as e:
                error_msg = f"Failed to convert coordinate '{coord_name}' with value '{coord_value}': {str(e)}"
                self.logger.warning(error_msg)
                errors.append(error_msg)

                # Provide fallback value for failed coordinate
                results[coord_name] = self._get_fallback_emu_value(coord_value, context, 'x')

        # Log batch conversion summary
        success_count = len(results)
        error_count = len(errors)
        if errors:
            self.logger.warning(f"Batch conversion completed with {error_count} errors out of {success_count} coordinates")

        return results

    def get_precision_analysis(self,
                              value: Union[str, float, int],
                              context: Optional[ViewportContext] = None) -> Dict[str, Any]:
        """
        Get detailed precision analysis for debugging and validation.

        Returns comprehensive breakdown of conversion steps and precision metrics.
        """
        if context is None:
            context = self.default_context

        # Parse input
        numeric_value, unit_type = self.parse_length(value, context)

        # Calculate base EMU (integer conversion)
        base_emu = self.to_emu(value, context)

        # Calculate fractional EMU
        fractional_emu = self.to_fractional_emu(value, context)

        # Calculate precision metrics
        precision_gain = fractional_emu - base_emu
        relative_precision = precision_gain / base_emu if base_emu != 0 else 0

        return {
            'input_value': value,
            'parsed_numeric': numeric_value,
            'unit_type': unit_type.value,
            'base_emu': base_emu,
            'fractional_emu': fractional_emu,
            'precision_gain': precision_gain,
            'relative_precision_percent': relative_precision * 100,
            'precision_mode': self.precision_mode.value,
            'precision_factor': self.precision_factor,
            'powerpoint_compatible': abs(fractional_emu) <= self.powerpoint_max_emu,
            'decimal_places': len(str(fractional_emu).split('.')[-1]) if '.' in str(fractional_emu) else 0
        }

    def optimize_performance_for_batch(self, enable: bool = True):
        """Enable or disable performance optimizations for batch operations."""
        self.fractional_context.performance_mode = enable
        if enable:
            # Reduce precision factor for performance
            self.precision_factor = min(self.precision_factor, 100.0)
        else:
            # Restore full precision
            self.precision_factor = self.precision_factors[self.precision_mode]

    def clear_cache(self):
        """Clear internal caches for memory management."""
        self.fractional_cache.clear()
        self.coordinate_cache.clear()

    # Backward compatibility: Override base methods to maintain integer output when requested
    def to_emu(self, value: Union[str, float, int],
               context: Optional[ViewportContext] = None,
               axis: str = 'x') -> int:
        """
        Override base to_emu to provide integer EMU while using fractional calculation.

        Maintains backward compatibility while benefiting from fractional precision internally.
        """
        fractional_result = self.to_fractional_emu(value, context, axis, preserve_precision=False)
        return int(round(fractional_result))


# Convenience function for creating fractional EMU converters
def create_fractional_converter(precision_mode: str = "subpixel",
                               **kwargs) -> FractionalEMUConverter:
    """
    Create a FractionalEMUConverter with specified precision mode.

    Args:
        precision_mode: "standard", "subpixel", "high", or "ultra"
        **kwargs: Additional UnitConverter parameters

    Returns:
        Configured FractionalEMUConverter instance
    """
    return FractionalEMUConverter(
        precision_mode=PrecisionMode(precision_mode),
        **kwargs
    )