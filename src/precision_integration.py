#!/usr/bin/env python3
"""
Precision Integration System for Advanced SVG Features

Integrates the fractional EMU precision system with existing SVG parsers,
converters, and OOXML generators to enable subpixel-accurate conversion
while maintaining backward compatibility.

Key Features:
- Seamless integration with existing BaseConverter and ConversionContext
- Enhanced CoordinateSystem with fractional EMU precision
- Precision-aware OOXML generation utilities
- Backward compatibility with existing converter architecture
- Performance optimization for precision calculations

Integration Points:
- ConversionContext enhancement with FractionalEMUConverter
- CoordinateSystem upgrade with subpixel coordinate transformation
- BaseConverter integration with precision-aware methods
- OOXML output formatting with fractional coordinates
"""

from typing import Dict, List, Tuple, Optional, Any, Union
from lxml import etree as ET
import logging

from .fractional_emu import FractionalEMUConverter, PrecisionMode, FractionalCoordinateContext
from .subpixel_shapes import SubpixelShapeProcessor, ShapeComplexity, SubpixelShapeContext
from .units import UnitConverter, ViewportContext, DEFAULT_DPI
from .converters.base import CoordinateSystem, ConversionContext, BaseConverter

logger = logging.getLogger(__name__)


class EnhancedCoordinateSystem(CoordinateSystem):
    """
    Enhanced coordinate system with fractional EMU precision capabilities.

    Extends the base CoordinateSystem to support subpixel-accurate coordinate
    transformations while maintaining backward compatibility.
    """

    def __init__(self,
                 viewbox: Tuple[float, float, float, float],
                 slide_width: float = 9144000,
                 slide_height: float = 6858000,
                 precision_mode: PrecisionMode = PrecisionMode.SUBPIXEL,
                 enable_fractional_emu: bool = True):
        """
        Initialize enhanced coordinate system with precision capabilities.

        Args:
            viewbox: SVG viewBox (x, y, width, height)
            slide_width: PowerPoint slide width in EMUs
            slide_height: PowerPoint slide height in EMUs
            precision_mode: Precision level for fractional calculations
            enable_fractional_emu: Whether to enable fractional EMU precision
        """
        super().__init__(viewbox, slide_width, slide_height)

        self.precision_mode = precision_mode
        self.enable_fractional_emu = enable_fractional_emu

        # Initialize fractional EMU converter
        self.fractional_converter = FractionalEMUConverter(
            precision_mode=precision_mode,
            viewport_width=viewbox[2],
            viewport_height=viewbox[3]
        ) if enable_fractional_emu else None

        # Calculate fractional scaling factors
        if self.enable_fractional_emu:
            self.fractional_scale_x = slide_width / viewbox[2] if viewbox[2] > 0 else 1.0
            self.fractional_scale_y = slide_height / viewbox[3] if viewbox[3] > 0 else 1.0

            if self.preserve_aspect_ratio:
                self.fractional_scale = min(self.fractional_scale_x, self.fractional_scale_y)
                self.fractional_scale_x = self.fractional_scale_y = self.fractional_scale

                # Fractional centering offsets
                self.fractional_offset_x = (slide_width - viewbox[2] * self.fractional_scale) / 2
                self.fractional_offset_y = (slide_height - viewbox[3] * self.fractional_scale) / 2
            else:
                self.fractional_offset_x = 0.0
                self.fractional_offset_y = 0.0

    def svg_to_fractional_emu(self, x: float, y: float) -> Tuple[float, float]:
        """Convert SVG coordinates to fractional EMUs with subpixel precision."""
        if not self.enable_fractional_emu or not self.fractional_converter:
            # Fallback to integer conversion
            emu_x, emu_y = self.svg_to_emu(x, y)
            return float(emu_x), float(emu_y)

        # Adjust for viewbox offset
        x -= self.viewbox[0]
        y -= self.viewbox[1]

        # Scale with fractional precision and add centering offset
        fractional_emu_x = x * self.fractional_scale_x + self.fractional_offset_x
        fractional_emu_y = y * self.fractional_scale_y + self.fractional_offset_y

        return fractional_emu_x, fractional_emu_y

    def svg_length_to_fractional_emu(self, length: float, axis: str = 'x') -> float:
        """Convert SVG length to fractional EMU with subpixel precision."""
        if not self.enable_fractional_emu:
            return float(self.svg_length_to_emu(length, axis))

        scale = self.fractional_scale_x if axis == 'x' else self.fractional_scale_y
        return length * scale

    def batch_convert_coordinates(self,
                                coordinates: Dict[str, Union[str, float]]) -> Dict[str, float]:
        """Batch convert multiple coordinates with fractional precision."""
        if not self.enable_fractional_emu or not self.fractional_converter:
            # Fallback to standard conversion
            return {k: float(self.svg_length_to_emu(v)) for k, v in coordinates.items()}

        # Use fractional converter for batch processing
        viewport_context = ViewportContext(
            width=self.svg_width,
            height=self.svg_height
        )

        return self.fractional_converter.batch_convert_coordinates(
            coordinates, viewport_context
        )


class PrecisionConversionContext(ConversionContext):
    """
    Enhanced conversion context with fractional EMU precision capabilities.

    Extends the base ConversionContext to support advanced precision calculations
    and subpixel-aware shape processing.
    """

    def __init__(self,
                 svg_root: Optional[ET.Element] = None,
                 precision_mode: PrecisionMode = PrecisionMode.SUBPIXEL,
                 enable_fractional_emu: bool = True,
                 services=None):
        """
        Initialize precision-aware conversion context.

        Args:
            svg_root: Root SVG element
            precision_mode: Precision level for calculations
            enable_fractional_emu: Whether to enable fractional EMU precision
            services: ConversionServices instance
        """
        super().__init__(svg_root, services=services)

        self.precision_mode = precision_mode
        self.enable_fractional_emu = enable_fractional_emu

        # Replace standard unit converter with fractional EMU converter
        if enable_fractional_emu:
            self.fractional_unit_converter = FractionalEMUConverter(
                precision_mode=precision_mode,
                default_dpi=DEFAULT_DPI
            )

            # Initialize subpixel shape processor
            self.subpixel_processor = SubpixelShapeProcessor(
                fractional_converter=self.fractional_unit_converter
            )
        else:
            self.fractional_unit_converter = None
            self.subpixel_processor = None

        # Precision calculation statistics
        self.precision_statistics = {
            'coordinates_processed': 0,
            'shapes_processed': 0,
            'precision_gains': [],
            'cache_hits': 0
        }

    def to_fractional_emu(self, value: Union[str, float], axis: str = 'x') -> float:
        """Convert SVG length to fractional EMUs with subpixel precision."""
        if not self.enable_fractional_emu or not self.fractional_unit_converter:
            return float(self.to_emu(value, axis))

        fractional_result = self.fractional_unit_converter.to_fractional_emu(
            value, self.viewport_context, axis, preserve_precision=False
        )

        # Update statistics
        self.precision_statistics['coordinates_processed'] += 1

        return fractional_result

    def to_high_precision_emu(self, value: Union[str, float], axis: str = 'x') -> float:
        """Convert SVG length to high-precision fractional EMUs."""
        if not self.enable_fractional_emu or not self.fractional_unit_converter:
            return float(self.to_emu(value, axis))

        # Use high precision mode for critical calculations
        original_mode = self.fractional_unit_converter.precision_mode
        self.fractional_unit_converter.precision_mode = PrecisionMode.HIGH_PRECISION

        try:
            result = self.fractional_unit_converter.to_fractional_emu(
                value, self.viewport_context, axis, preserve_precision=True
            )
            return result
        finally:
            # Restore original precision mode
            self.fractional_unit_converter.precision_mode = original_mode

    def batch_convert_to_fractional_emu(self, values: Dict[str, Any]) -> Dict[str, float]:
        """Convert multiple SVG lengths to fractional EMUs in one call."""
        if not self.enable_fractional_emu or not self.fractional_unit_converter:
            # Fallback to standard conversion
            result = self.batch_convert_to_emu(values)
            return {k: float(v) for k, v in result.items()}

        fractional_results = self.fractional_unit_converter.batch_convert_coordinates(
            values, self.viewport_context
        )

        # Update statistics
        self.precision_statistics['coordinates_processed'] += len(values)

        return fractional_results

    def calculate_precise_shape(self,
                              shape_type: str,
                              coordinates: Dict[str, Union[str, float]]) -> Dict[str, float]:
        """Calculate precise shape coordinates using subpixel algorithms."""
        if not self.enable_fractional_emu or not self.subpixel_processor:
            # Fallback to standard coordinate calculation
            return self.batch_convert_to_fractional_emu(coordinates)

        # Use specialized subpixel shape algorithms
        if shape_type == 'rectangle':
            shape_result = self.subpixel_processor.calculate_precise_rectangle(
                coordinates.get('x', 0),
                coordinates.get('y', 0),
                coordinates.get('width', 0),
                coordinates.get('height', 0)
            )
        elif shape_type == 'circle':
            shape_result = self.subpixel_processor.calculate_precise_circle(
                coordinates.get('cx', 0),
                coordinates.get('cy', 0),
                coordinates.get('r', 0)
            )
        elif shape_type == 'ellipse':
            shape_result = self.subpixel_processor.calculate_precise_ellipse(
                coordinates.get('cx', 0),
                coordinates.get('cy', 0),
                coordinates.get('rx', 0),
                coordinates.get('ry', 0)
            )
        else:
            # Fallback to batch conversion for unknown shape types
            shape_result = self.batch_convert_to_fractional_emu(coordinates)

        # Update statistics
        self.precision_statistics['shapes_processed'] += 1

        return shape_result

    def get_precision_statistics(self) -> Dict[str, Any]:
        """Get comprehensive precision calculation statistics."""
        base_stats = self.precision_statistics.copy()

        # Add fractional converter statistics if available
        if self.fractional_unit_converter:
            base_stats.update({
                'precision_mode': self.fractional_unit_converter.precision_mode.value,
                'cache_size': len(self.fractional_unit_converter.fractional_cache),
                'average_precision_gain': (
                    sum(base_stats['precision_gains']) / len(base_stats['precision_gains'])
                    if base_stats['precision_gains'] else 0
                )
            })

        # Add subpixel processor statistics if available
        if self.subpixel_processor:
            processor_stats = self.subpixel_processor.get_shape_precision_statistics()
            base_stats.update(processor_stats)

        return base_stats


class PrecisionAwareConverter(BaseConverter):
    """
    Enhanced base converter with fractional EMU precision capabilities.

    Provides methods for precision-aware SVG to OOXML conversion while
    maintaining compatibility with existing converter architecture.
    """

    def __init__(self, precision_mode: PrecisionMode = PrecisionMode.SUBPIXEL):
        """
        Initialize precision-aware converter.

        Args:
            precision_mode: Precision level for coordinate calculations
        """
        super().__init__()
        self.precision_mode = precision_mode

        # Replace standard unit converter with fractional EMU converter
        self.fractional_unit_converter = FractionalEMUConverter(
            precision_mode=precision_mode
        )

        # Initialize precision-aware utilities
        self.precision_logger = logging.getLogger(f"{self.__class__.__name__}.Precision")

    def convert_coordinate_with_precision(self,
                                        value: Union[str, float],
                                        context: ConversionContext,
                                        axis: str = 'x') -> float:
        """Convert coordinate with fractional EMU precision."""
        if isinstance(context, PrecisionConversionContext):
            return context.to_fractional_emu(value, axis)
        else:
            # Fallback for standard context
            return self.fractional_unit_converter.to_fractional_emu(
                value, context.viewport_context, axis
            )

    def format_fractional_emu_for_ooxml(self, emu_value: float, max_decimal_places: int = 3) -> str:
        """Format fractional EMU value for OOXML output with PowerPoint compatibility."""
        # Round to specified decimal places for PowerPoint compatibility
        rounded_value = round(emu_value, max_decimal_places)

        # Format as integer if no fractional part
        if rounded_value == int(rounded_value):
            return str(int(rounded_value))

        # Format with minimal decimal places
        formatted = f"{rounded_value:.{max_decimal_places}f}".rstrip('0').rstrip('.')
        return formatted if '.' in formatted else str(int(rounded_value))

    def generate_precise_ooxml_coordinates(self,
                                         coordinates: Dict[str, float]) -> Dict[str, str]:
        """Generate OOXML coordinate strings with fractional precision."""
        ooxml_coords = {}

        for coord_name, coord_value in coordinates.items():
            ooxml_coords[coord_name] = self.format_fractional_emu_for_ooxml(coord_value)

        return ooxml_coords

    def create_precise_ooxml_element(self,
                                   tag: str,
                                   coordinates: Dict[str, float],
                                   attributes: Optional[Dict[str, str]] = None) -> str:
        """Create OOXML element with precise fractional coordinates."""
        # Format coordinates for OOXML
        ooxml_coords = self.generate_precise_ooxml_coordinates(coordinates)

        # Build attribute string
        all_attributes = ooxml_coords.copy()
        if attributes:
            all_attributes.update(attributes)

        attr_string = ' '.join(f'{k}="{v}"' for k, v in all_attributes.items())

        return f'<{tag} {attr_string}/>' if attr_string else f'<{tag}/>'


def create_precision_conversion_context(svg_root: Optional[ET.Element] = None,
                                       precision_mode: str = "subpixel",
                                       enable_fractional_emu: bool = True,
                                       services=None) -> PrecisionConversionContext:
    """
    Create a precision-aware conversion context.

    Args:
        svg_root: Root SVG element
        precision_mode: "standard", "subpixel", "high", or "ultra"
        enable_fractional_emu: Whether to enable fractional EMU precision
        services: ConversionServices instance

    Returns:
        Configured PrecisionConversionContext instance
    """
    return PrecisionConversionContext(
        svg_root=svg_root,
        precision_mode=PrecisionMode(precision_mode),
        enable_fractional_emu=enable_fractional_emu,
        services=services
    )


def create_enhanced_coordinate_system(viewbox: Tuple[float, float, float, float],
                                    precision_mode: str = "subpixel",
                                    slide_width: float = 9144000,
                                    slide_height: float = 6858000) -> EnhancedCoordinateSystem:
    """
    Create an enhanced coordinate system with fractional EMU precision.

    Args:
        viewbox: SVG viewBox (x, y, width, height)
        precision_mode: "standard", "subpixel", "high", or "ultra"
        slide_width: PowerPoint slide width in EMUs
        slide_height: PowerPoint slide height in EMUs

    Returns:
        Configured EnhancedCoordinateSystem instance
    """
    return EnhancedCoordinateSystem(
        viewbox=viewbox,
        slide_width=slide_width,
        slide_height=slide_height,
        precision_mode=PrecisionMode(precision_mode),
        enable_fractional_emu=True
    )


def integrate_precision_with_existing_converter(converter: BaseConverter,
                                              precision_mode: str = "subpixel") -> PrecisionAwareConverter:
    """
    Integrate fractional EMU precision with an existing converter.

    This function creates a precision-aware wrapper that can be used as a drop-in
    replacement for existing converters while adding fractional EMU capabilities.

    Args:
        converter: Existing BaseConverter instance
        precision_mode: Precision level to apply

    Returns:
        PrecisionAwareConverter with integrated capabilities
    """
    # Create precision-aware converter with same supported elements
    precision_converter = PrecisionAwareConverter(PrecisionMode(precision_mode))
    precision_converter.supported_elements = converter.supported_elements

    # Copy converter-specific attributes
    for attr_name in dir(converter):
        if not attr_name.startswith('_') and not callable(getattr(converter, attr_name)):
            if hasattr(precision_converter, attr_name):
                continue  # Don't override precision-specific attributes
            setattr(precision_converter, attr_name, getattr(converter, attr_name))

    return precision_converter