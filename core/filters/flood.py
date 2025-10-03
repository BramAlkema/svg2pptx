#!/usr/bin/env python3
"""
Flood Filter Implementation for SVG feFlood Elements

Migrated from archive/legacy-src/converters/filters/image/color.py
and adapted to the clean slate FilterProcessor architecture with policy
integration and template-based XML generation.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass
import logging
from lxml import etree as ET

from .base import FilterProcessor, FilterContext, FilterResult, FilterStrategy
from ..color import Color

if TYPE_CHECKING:
    from ..policy.engine import Policy

logger = logging.getLogger(__name__)


class FloodFilterException(Exception):
    """Exception raised when flood filter processing fails."""
    pass


@dataclass
class FloodParameters:
    """Parameters for flood fill operations."""
    flood_color: str = "black"
    flood_opacity: float = 1.0
    input_source: str = "SourceGraphic"
    result_name: str = "flood"


class FloodProcessor(FilterProcessor):
    """
    Flood filter processor for SVG feFlood elements.

    Implements solid color flood fills using PowerPoint's native solid fill
    effects with proper color parsing and opacity handling. Integrates with
    clean slate architecture and core Color system.

    Features:
    - Native PowerPoint solid fill generation
    - Full Color system integration for parsing and validation
    - Opacity handling with proper alpha channel mapping
    - Policy-driven strategy selection
    - Template-based XML generation

    Policy Integration:
    - NATIVE: Uses PowerPoint solidFill effects (always preferred for flood)
    - APPROXIMATION: Fallback for complex color expressions
    - EMF_RASTERIZE: Only for extreme cases with unsupported features

    Example:
        >>> processor = FloodProcessor('feFlood', policy)
        >>> element = ET.fromstring('<feFlood flood-color="#FF0000" flood-opacity="0.8"/>')
        >>> result = processor.apply(element, context)
        >>> print(result.get_drawingml())  # '<a:solidFill>...</a:solidFill>'
    """

    def __init__(self, filter_type: str = 'feFlood', policy: Optional['Policy'] = None):
        """
        Initialize the flood filter processor.

        Args:
            filter_type: Filter type name (default: 'feFlood')
            policy: Policy engine for strategy decisions
        """
        super().__init__(filter_type, policy)
        self.logger = logging.getLogger(__name__)

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        """
        Check if this processor can handle the given element.

        Args:
            element: SVG element to check
            context: Filter processing context

        Returns:
            True if this processor can handle the element
        """
        if element is None:
            return False

        # Check for feFlood elements
        tag = self._get_element_localname(element)
        return (
            tag == 'feFlood' or
            tag.endswith('feFlood') or
            element.get('type') == 'feFlood'
        )

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        """
        Apply flood fill to the SVG element.

        Uses core Color system for parsing and validation, with policy engine
        to select optimal rendering strategy. Flood fills typically use native
        PowerPoint solid fill effects for optimal compatibility.

        Args:
            element: SVG feFlood element
            context: Filter processing context

        Returns:
            FilterResult containing the flood fill DrawingML
        """
        try:
            # Validate parameters first
            if not self._validate_parameters(element, context):
                return self._create_failure_result(
                    "Invalid feFlood parameters"
                )

            # Parse flood parameters
            params = self._parse_flood_parameters(element, context)

            # Get policy decision for rendering strategy
            strategy = self._get_rendering_strategy(params, context)

            # Generate DrawingML based on strategy
            drawingml = self._generate_flood_drawingml(params, context, strategy)

            # Create comprehensive metadata
            metadata = {
                'filter_type': self.filter_type,
                'flood_color': params.flood_color,
                'flood_opacity': params.flood_opacity,
                'input_source': params.input_source,
                'result_name': params.result_name,
                'strategy': strategy.value,
                'color_format': self._get_color_format(params.flood_color),
                'has_transparency': params.flood_opacity < 1.0,
                'processing_method': self._get_processing_method(strategy)
            }

            return self._create_success_result(
                drawingml=drawingml,
                strategy=strategy,
                metadata=metadata
            )

        except FloodFilterException as e:
            self.logger.warning(f"Flood filter processing failed: {e}")
            return self._create_failure_result(str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error in flood filter: {e}")
            return self._create_failure_result(f"Flood processing failed: {str(e)}")

    def _validate_parameters(self, element: ET.Element, context: FilterContext) -> bool:
        """
        Validate that the element has valid parameters for flood processing.

        Args:
            element: SVG element to validate
            context: Filter processing context

        Returns:
            True if element parameters are valid
        """
        try:
            params = self._parse_flood_parameters(element, context)

            # Validate opacity range (0.0 to 1.0)
            if not (0.0 <= params.flood_opacity <= 1.0):
                return False

            # Validate color (basic validation - Color system will handle parsing)
            if not params.flood_color or not isinstance(params.flood_color, str):
                return False

            return True

        except Exception:
            return False

    def _parse_flood_parameters(self, element: ET.Element, context: FilterContext) -> FloodParameters:
        """
        Parse flood parameters from SVG feFlood element.

        Args:
            element: SVG feFlood element
            context: Filter processing context

        Returns:
            FloodParameters with parsed values

        Raises:
            FloodFilterException: If parameters are invalid
        """
        try:
            # Parse flood color with default
            flood_color = element.get('flood-color', 'black')

            # Parse flood opacity with validation
            flood_opacity_str = element.get('flood-opacity', '1.0')
            try:
                flood_opacity = float(flood_opacity_str)
                # Clamp to valid range
                flood_opacity = max(0.0, min(flood_opacity, 1.0))
            except ValueError:
                raise FloodFilterException(f"Invalid flood-opacity value: '{flood_opacity_str}'")

            # Parse input and result references
            input_source = element.get('in', 'SourceGraphic')
            result_name = element.get('result', 'flood')

            return FloodParameters(
                flood_color=flood_color,
                flood_opacity=flood_opacity,
                input_source=input_source,
                result_name=result_name
            )

        except Exception as e:
            raise FloodFilterException(f"Failed to parse flood parameters: {e}")

    def _get_rendering_strategy(self, params: FloodParameters, context: FilterContext) -> FilterStrategy:
        """
        Determine optimal rendering strategy using policy engine.

        Flood fills typically use native PowerPoint solid fills since they
        map directly to PowerPoint's capabilities.

        Args:
            params: Parsed flood parameters
            context: Filter processing context

        Returns:
            FilterStrategy for rendering this flood fill
        """
        if self.policy:
            # Use policy to make informed decision
            decision_context = {
                'color_complexity': self._get_color_complexity(params.flood_color),
                'has_transparency': params.flood_opacity < 1.0,
                'complexity': 'simple'
            }

            try:
                return self.policy.decide_filter_strategy(
                    filter_type=self.filter_type,
                    element=context.element,
                    context=decision_context
                )
            except Exception as e:
                self.logger.warning(f"Policy decision failed, using fallback: {e}")

        # Fallback decision logic - flood fills almost always use native
        if self._is_simple_color(params.flood_color):
            return FilterStrategy.NATIVE
        else:
            # Complex colors might need approximation
            return FilterStrategy.APPROXIMATION

    def _is_simple_color(self, color_str: str) -> bool:
        """
        Check if color is simple enough for native PowerPoint support.

        Args:
            color_str: Color string to check

        Returns:
            True if color is simple (hex, named colors, etc.)
        """
        # Named colors and hex colors are simple
        if color_str.lower() in ['black', 'white', 'red', 'green', 'blue', 'yellow', 'cyan', 'magenta']:
            return True

        # Hex colors are simple
        if color_str.startswith('#') and len(color_str) in [4, 7]:
            return True

        # RGB functions need validation
        if color_str.startswith('rgb('):
            return True

        # More complex expressions may need approximation
        return False

    def _get_color_complexity(self, color_str: str) -> str:
        """
        Assess color complexity for policy decisions.

        Args:
            color_str: Color string to assess

        Returns:
            Complexity level: 'simple', 'moderate', 'complex'
        """
        # Check for moderate complexity first
        if 'rgb(' in color_str or 'hsl(' in color_str:
            return 'moderate'
        elif self._is_simple_color(color_str):
            return 'simple'
        else:
            return 'complex'

    def _get_color_format(self, color_str: str) -> str:
        """
        Determine color format for metadata.

        Args:
            color_str: Color string

        Returns:
            Format type: 'hex', 'named', 'rgb', 'hsl', 'other'
        """
        if color_str.startswith('#'):
            return 'hex'
        elif color_str.startswith('rgb('):
            return 'rgb'
        elif color_str.startswith('hsl('):
            return 'hsl'
        elif color_str.lower() in ['black', 'white', 'red', 'green', 'blue', 'yellow', 'cyan', 'magenta', 'transparent']:
            return 'named'
        else:
            return 'other'

    def _generate_flood_drawingml(self, params: FloodParameters, context: FilterContext,
                                 strategy: FilterStrategy) -> str:
        """
        Generate DrawingML for flood fill based on strategy.

        Args:
            params: Flood parameters
            context: Filter processing context
            strategy: Rendering strategy to use

        Returns:
            DrawingML XML string for flood fill effect
        """
        if strategy == FilterStrategy.NATIVE:
            return self._generate_native_flood_drawingml(params, context)
        elif strategy == FilterStrategy.APPROXIMATION:
            return self._generate_approximation_flood_drawingml(params, context)
        else:
            # EMF_RASTERIZE - provide placeholder for raster fallback
            return self._generate_raster_fallback_drawingml(params, context)

    def _generate_native_flood_drawingml(self, params: FloodParameters, context: FilterContext) -> str:
        """
        Generate native PowerPoint solid fill DrawingML.

        Uses PowerPoint's <a:solidFill> with proper color parsing through
        the core Color system for accurate color representation.

        Args:
            params: Flood parameters
            context: Filter processing context

        Returns:
            DrawingML XML string for native solid fill
        """
        try:
            # Parse color using core Color system
            color = Color(params.flood_color)
            hex_color = color.hex(include_hash=False).upper()

        except Exception as e:
            self.logger.warning(f"Color parsing failed for '{params.flood_color}': {e}")
            # Fallback to default
            hex_color = "000000"  # Black fallback

        # Convert opacity to PowerPoint alpha (0-100000, where 100000 = fully opaque)
        alpha_val = int(params.flood_opacity * 100000)

        # Generate solid fill DrawingML
        if alpha_val == 100000:
            # Fully opaque - no alpha needed
            drawingml_parts = [
                '<a:solidFill>',
                f'  <a:srgbClr val="{hex_color}"/>',
                '</a:solidFill>'
            ]
        else:
            # Include alpha channel
            drawingml_parts = [
                '<a:solidFill>',
                f'  <a:srgbClr val="{hex_color}">',
                f'    <a:alpha val="{alpha_val}"/>',
                '  </a:srgbClr>',
                '</a:solidFill>'
            ]

        return '\n'.join(drawingml_parts)

    def _generate_approximation_flood_drawingml(self, params: FloodParameters, context: FilterContext) -> str:
        """
        Generate approximation flood fill for complex colors.

        Uses fallback parsing and simplified color representation when
        the core Color system cannot parse the input color.

        Args:
            params: Flood parameters
            context: Filter processing context

        Returns:
            DrawingML XML string for approximated flood fill
        """
        # Try basic color parsing fallback
        fallback_color = self._parse_color_fallback(params.flood_color)

        # Convert opacity to PowerPoint alpha
        alpha_val = int(params.flood_opacity * 100000)

        drawingml_parts = [
            f'<!-- Approximated flood color: {params.flood_color} -->',
            '<a:solidFill>',
            f'  <a:srgbClr val="{fallback_color}">',
            f'    <a:alpha val="{alpha_val}"/>',
            '  </a:srgbClr>',
            '</a:solidFill>'
        ]

        return '\n'.join(drawingml_parts)

    def _generate_raster_fallback_drawingml(self, params: FloodParameters, context: FilterContext) -> str:
        """
        Generate EMF rasterization fallback for extremely complex colors.

        Args:
            params: Flood parameters
            context: Filter processing context

        Returns:
            DrawingML XML string with rasterization hint
        """
        # Provide metadata for EMF rasterization system
        drawingml_parts = [
            f'<!-- EMF rasterization required: complex flood color {params.flood_color} -->',
            '<a:blip>',
            f'  <!-- Flood fill: color={params.flood_color}, opacity={params.flood_opacity} -->',
            '  <a:extLst>',
            '    <a:ext uri="{raster-fallback}">',
            f'      <r:flood color="{params.flood_color}" opacity="{params.flood_opacity}"/>',
            '    </a:ext>',
            '  </a:extLst>',
            '</a:blip>'
        ]

        return '\n'.join(drawingml_parts)

    def _parse_color_fallback(self, color_str: str) -> str:
        """
        Parse color with basic fallback logic.

        Args:
            color_str: Color string to parse

        Returns:
            Hex color string (without #)
        """
        # Basic color name mapping
        color_map = {
            'black': '000000',
            'white': 'FFFFFF',
            'red': 'FF0000',
            'green': '00FF00',
            'blue': '0000FF',
            'yellow': 'FFFF00',
            'cyan': '00FFFF',
            'magenta': 'FF00FF',
            'transparent': '000000'  # Transparent becomes black
        }

        color_lower = color_str.lower().strip()

        # Named colors
        if color_lower in color_map:
            return color_map[color_lower]

        # Hex colors
        if color_str.startswith('#'):
            hex_part = color_str[1:]
            if len(hex_part) == 3:
                # Expand #RGB to #RRGGBB
                return ''.join([c*2 for c in hex_part]).upper()
            elif len(hex_part) == 6:
                return hex_part.upper()

        # Default fallback
        return '000000'

    def _get_processing_method(self, strategy: FilterStrategy) -> str:
        """
        Get human-readable description of processing method.

        Args:
            strategy: Rendering strategy

        Returns:
            Description of processing method
        """
        method_map = {
            FilterStrategy.NATIVE: 'Native PowerPoint solid fill',
            FilterStrategy.APPROXIMATION: 'Approximated color parsing',
            FilterStrategy.EMF_RASTERIZE: 'EMF rasterization fallback'
        }

        return method_map.get(strategy, 'Unknown processing method')


def create_flood_processor(policy: Optional['Policy'] = None) -> FloodProcessor:
    """
    Factory function to create FloodProcessor with proper configuration.

    Args:
        policy: Optional policy engine for rendering decisions

    Returns:
        Configured FloodProcessor instance
    """
    return FloodProcessor('feFlood', policy)