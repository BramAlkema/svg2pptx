#!/usr/bin/env python3
"""
Offset Filter Implementation for SVG feOffset Elements

Migrated from archive/legacy-src/converters/filters/geometric/transforms.py
and adapted to the clean slate FilterProcessor architecture with policy
integration and template-based XML generation.
"""

import math
from typing import Dict, Any, Tuple, Optional, TYPE_CHECKING
from dataclasses import dataclass
import logging
from lxml import etree as ET

from .base import FilterProcessor, FilterContext, FilterResult, FilterStrategy
from ..units import unit

if TYPE_CHECKING:
    from ..policy.engine import Policy

logger = logging.getLogger(__name__)


class OffsetFilterException(Exception):
    """Exception raised when offset filter processing fails."""
    pass


@dataclass
class OffsetParameters:
    """Parameters for offset transformation operations."""
    dx: float
    dy: float
    input_source: str = "SourceGraphic"
    result_name: str = "offset"


class OffsetProcessor(FilterProcessor):
    """
    Offset filter processor for SVG feOffset elements.

    Implements geometric offset transformations using PowerPoint's native
    shadow effects when possible, with transform-based fallbacks for complex
    scenarios. Integrates with clean slate architecture and policy engine.

    Features:
    - Native PowerPoint shadow effects for moderate offsets
    - Transform-based positioning for large offsets
    - Policy-driven strategy selection
    - Template-based XML generation
    - Full unit conversion support via ConversionServices

    Policy Integration:
    - NATIVE: Uses PowerPoint shadow effects (up to 50px offset)
    - APPROXIMATION: Uses transform-based positioning
    - EMF_RASTERIZE: Falls back to raster for extreme cases

    Example:
        >>> processor = OffsetProcessor('feOffset', policy)
        >>> element = ET.fromstring('<feOffset dx="5" dy="3"/>')
        >>> result = processor.apply(element, context)
        >>> print(result.get_drawingml())  # '<a:outerShdw dist="..." dir="..."/>'
    """

    def __init__(self, filter_type: str = 'feOffset', policy: Optional['Policy'] = None):
        """
        Initialize the offset filter processor.

        Args:
            filter_type: Filter type name (default: 'feOffset')
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

        # Check for feOffset elements
        tag = self._get_element_localname(element)
        return (
            tag == 'feOffset' or
            tag.endswith('feOffset') or
            element.get('type') == 'feOffset'
        )

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        """
        Apply offset transformation to the SVG element.

        Uses policy engine to select optimal rendering strategy:
        - Native PowerPoint shadows for moderate offsets
        - Transform-based positioning for large offsets
        - EMF rasterization for extreme cases

        Args:
            element: SVG feOffset element
            context: Filter processing context

        Returns:
            FilterResult containing the offset effect DrawingML
        """
        try:
            # Validate parameters first
            if not self._validate_parameters(element, context):
                return self._create_failure_result(
                    "Invalid feOffset parameters"
                )

            # Parse offset parameters
            params = self._parse_offset_parameters(element)

            # Get policy decision for rendering strategy
            strategy = self._get_rendering_strategy(params, context)

            # Generate DrawingML based on strategy
            drawingml = self._generate_offset_drawingml(params, context, strategy)

            # Create comprehensive metadata
            metadata = {
                'filter_type': self.filter_type,
                'dx': params.dx,
                'dy': params.dy,
                'input_source': params.input_source,
                'result_name': params.result_name,
                'strategy': strategy.value,
                'displacement_emu': self._calculate_displacement_emu(params, context),
                'native_support': self._has_native_support(params),
                'processing_method': self._get_processing_method(strategy)
            }

            return self._create_success_result(
                drawingml=drawingml,
                strategy=strategy,
                metadata=metadata
            )

        except OffsetFilterException as e:
            self.logger.warning(f"Offset filter processing failed: {e}")
            return self._create_failure_result(str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error in offset filter: {e}")
            return self._create_failure_result(f"Offset processing failed: {str(e)}")

    def _validate_parameters(self, element: ET.Element, context: FilterContext) -> bool:
        """
        Validate that the element has valid parameters for offset processing.

        Args:
            element: SVG element to validate
            context: Filter processing context

        Returns:
            True if element parameters are valid
        """
        try:
            params = self._parse_offset_parameters(element)

            # All numeric dx/dy values are valid (including negative and zero)
            # No additional validation needed for basic offset operations
            return True

        except Exception:
            return False

    def _parse_offset_parameters(self, element: ET.Element) -> OffsetParameters:
        """
        Parse offset parameters from SVG feOffset element.

        Args:
            element: SVG feOffset element

        Returns:
            OffsetParameters with parsed values

        Raises:
            OffsetFilterException: If parameters are invalid
        """
        try:
            # Parse dx and dy attributes with defaults of 0
            dx_str = element.get('dx', '0')
            dy_str = element.get('dy', '0')

            try:
                dx = float(dx_str)
                dy = float(dy_str)
            except ValueError:
                raise OffsetFilterException(f"Invalid numeric values: dx='{dx_str}', dy='{dy_str}'")

            # Parse input and result references
            input_source = element.get('in', 'SourceGraphic')
            result_name = element.get('result', 'offset')

            return OffsetParameters(
                dx=dx,
                dy=dy,
                input_source=input_source,
                result_name=result_name
            )

        except Exception as e:
            raise OffsetFilterException(f"Failed to parse offset parameters: {e}")

    def _get_rendering_strategy(self, params: OffsetParameters, context: FilterContext) -> FilterStrategy:
        """
        Determine optimal rendering strategy using policy engine.

        Args:
            params: Parsed offset parameters
            context: Filter processing context

        Returns:
            FilterStrategy for rendering this offset
        """
        if self.policy:
            # Use policy to make informed decision
            decision_context = {
                'offset_magnitude': math.sqrt(params.dx * params.dx + params.dy * params.dy),
                'has_native_support': self._has_native_support(params),
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

        # Fallback decision logic
        if self._has_native_support(params):
            return FilterStrategy.NATIVE
        elif self._is_moderate_offset(params):
            return FilterStrategy.APPROXIMATION
        else:
            return FilterStrategy.EMF_RASTERIZE

    def _has_native_support(self, params: OffsetParameters) -> bool:
        """
        Determine if offset can use native PowerPoint shadow effects.

        PowerPoint's outer shadow effects work well for moderate offsets
        but have limitations for very large displacements.

        Args:
            params: Offset parameters

        Returns:
            True if can use native shadow effects
        """
        # Calculate total offset magnitude
        magnitude = math.sqrt(params.dx * params.dx + params.dy * params.dy)

        # PowerPoint shadows work well up to ~50px offset
        return magnitude <= 50.0

    def _is_moderate_offset(self, params: OffsetParameters) -> bool:
        """
        Check if offset is moderate enough for transform approximation.

        Args:
            params: Offset parameters

        Returns:
            True if offset is suitable for transform approximation
        """
        magnitude = math.sqrt(params.dx * params.dx + params.dy * params.dy)

        # Transform-based positioning works up to ~200px
        return magnitude <= 200.0

    def _calculate_displacement_emu(self, params: OffsetParameters, context: FilterContext) -> Tuple[int, int]:
        """
        Calculate displacement in EMUs using ConversionServices.

        Args:
            params: Offset parameters
            context: Filter processing context

        Returns:
            Tuple of (dx_emu, dy_emu) displacement values
        """
        # Use fluent API for unit conversion
        dx_emu = unit(f"{params.dx}px").to_emu()
        dy_emu = unit(f"{params.dy}px").to_emu()

        return (int(dx_emu), int(dy_emu))

    def _generate_offset_drawingml(self, params: OffsetParameters, context: FilterContext,
                                  strategy: FilterStrategy) -> str:
        """
        Generate DrawingML for offset transformation based on strategy.

        Args:
            params: Offset parameters
            context: Filter processing context
            strategy: Rendering strategy to use

        Returns:
            DrawingML XML string for offset effect
        """
        if strategy == FilterStrategy.NATIVE:
            return self._generate_native_shadow_drawingml(params, context)
        elif strategy == FilterStrategy.APPROXIMATION:
            return self._generate_transform_drawingml(params, context)
        else:
            # EMF_RASTERIZE - provide placeholder for raster fallback
            return self._generate_raster_fallback_drawingml(params, context)

    def _generate_native_shadow_drawingml(self, params: OffsetParameters, context: FilterContext) -> str:
        """
        Generate native PowerPoint shadow effect DrawingML.

        Uses PowerPoint's <a:outerShdw> element with proper distance and direction
        calculations for high-fidelity offset effects.

        Args:
            params: Offset parameters
            context: Filter processing context

        Returns:
            DrawingML XML string for native shadow effect
        """
        # Calculate displacement in EMUs
        dx_emu, dy_emu = self._calculate_displacement_emu(params, context)

        # Handle zero offset case
        if dx_emu == 0 and dy_emu == 0:
            return '<!-- Zero offset: no shadow effect -->'

        # Calculate shadow distance and direction
        distance = math.sqrt(dx_emu * dx_emu + dy_emu * dy_emu)

        # PowerPoint angle system: 0 = right, 90 = down (in 1/60000 degree units)
        angle_rad = math.atan2(dy_emu, dx_emu)
        angle_deg = math.degrees(angle_rad)
        # Convert to PowerPoint's angle units (21600000 = 360°)
        ppt_angle = int((angle_deg * 60000) % 21600000)

        # Clamp distance to PowerPoint shadow limits
        distance = max(0, min(int(distance), 914400))  # Max ~36px in EMUs

        # Generate shadow DrawingML with subtle default appearance
        drawingml_parts = [
            f'<a:outerShdw blurRad="0" dist="{distance}" dir="{ppt_angle}" algn="ctr">',
            '  <a:srgbClr val="000000">',
            '    <a:alpha val="50000"/>',  # 50% opacity
            '  </a:srgbClr>',
            '</a:outerShdw>'
        ]

        return '\n'.join(drawingml_parts)

    def _generate_transform_drawingml(self, params: OffsetParameters, context: FilterContext) -> str:
        """
        Generate transform-based offset using DrawingML positioning.

        For larger offsets that exceed shadow limits, use coordinate
        transformation to achieve the displacement effect.

        Args:
            params: Offset parameters
            context: Filter processing context

        Returns:
            DrawingML XML string for transform-based offset
        """
        dx_emu, dy_emu = self._calculate_displacement_emu(params, context)

        # Generate transform-based positioning
        drawingml_parts = [
            f'<!-- Transform-based offset: dx={params.dx}px, dy={params.dy}px -->',
            '<a:xfrm>',
            f'  <a:off x="{dx_emu}" y="{dy_emu}"/>',
            '</a:xfrm>'
        ]

        return '\n'.join(drawingml_parts)

    def _generate_raster_fallback_drawingml(self, params: OffsetParameters, context: FilterContext) -> str:
        """
        Generate EMF rasterization fallback for extreme offsets.

        Args:
            params: Offset parameters
            context: Filter processing context

        Returns:
            DrawingML XML string with rasterization hint
        """
        dx_emu, dy_emu = self._calculate_displacement_emu(params, context)

        # Provide metadata for EMF rasterization system
        drawingml_parts = [
            f'<!-- EMF rasterization required: extreme offset dx={params.dx}px, dy={params.dy}px -->',
            '<a:blip>',
            f'  <!-- Raster offset: {dx_emu} EMU x, {dy_emu} EMU y -->',
            '  <a:extLst>',
            '    <a:ext uri="{raster-fallback}">',
            f'      <r:offset dx="{dx_emu}" dy="{dy_emu}"/>',
            '    </a:ext>',
            '  </a:extLst>',
            '</a:blip>'
        ]

        return '\n'.join(drawingml_parts)

    def _get_processing_method(self, strategy: FilterStrategy) -> str:
        """
        Get human-readable description of processing method.

        Args:
            strategy: Rendering strategy

        Returns:
            Description of processing method
        """
        method_map = {
            FilterStrategy.NATIVE: 'Native PowerPoint shadow',
            FilterStrategy.APPROXIMATION: 'Transform-based positioning',
            FilterStrategy.EMF_RASTERIZE: 'EMF rasterization fallback'
        }

        return method_map.get(strategy, 'Unknown processing method')


def create_offset_processor(policy: Optional['Policy'] = None) -> OffsetProcessor:
    """
    Factory function to create OffsetProcessor with proper configuration.

    Args:
        policy: Optional policy engine for rendering decisions

    Returns:
        Configured OffsetProcessor instance
    """
    return OffsetProcessor('feOffset', policy)