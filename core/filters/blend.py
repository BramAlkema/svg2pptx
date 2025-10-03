#!/usr/bin/env python3
"""
Blend Filter Implementation for SVG feBlend Elements

Migrated from archive/legacy-src/converters/filters/geometric/composite.py
and adapted to the clean slate FilterProcessor architecture with policy
integration and template-based XML generation.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum
import logging
from lxml import etree as ET

from .base import FilterProcessor, FilterContext, FilterResult, FilterStrategy

if TYPE_CHECKING:
    from ..policy.engine import Policy

logger = logging.getLogger(__name__)


class BlendFilterException(Exception):
    """Exception raised when blend filter processing fails."""
    pass


class BlendMode(Enum):
    """SVG blend mode types."""
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    DARKEN = "darken"
    LIGHTEN = "lighten"
    COLOR_DODGE = "color-dodge"
    COLOR_BURN = "color-burn"
    HARD_LIGHT = "hard-light"
    SOFT_LIGHT = "soft-light"
    DIFFERENCE = "difference"
    EXCLUSION = "exclusion"


@dataclass
class BlendParameters:
    """Parameters for blend operations."""
    mode: BlendMode
    input1: str
    input2: str
    result_name: str = "blend"


class BlendProcessor(FilterProcessor):
    """
    Blend filter processor for SVG feBlend elements.

    Implements blend mode operations using PowerPoint's native blend capabilities
    with comprehensive fallback strategies for unsupported modes. Integrates with
    clean slate architecture and policy engine for optimal rendering decisions.

    Features:
    - Native PowerPoint blend mode mapping (6 core modes)
    - Intelligent approximation for unsupported modes (6 additional modes)
    - Policy-driven strategy selection based on complexity
    - Template-based XML generation with proper PowerPoint syntax
    - Full metadata tracking for debugging and analysis

    Policy Integration:
    - NATIVE: Uses PowerPoint native blend modes (normal, multiply, screen, overlay, darken, lighten)
    - APPROXIMATION: Maps unsupported modes to closest PowerPoint equivalents
    - EMF_RASTERIZE: Falls back to raster for extremely complex scenarios

    Blend Mode Support Matrix:
    - NATIVE: normal→over, multiply→mult, screen→screen, overlay→overlay, darken→darken, lighten→lighten
    - APPROXIMATION: color-dodge→lighten, color-burn→darken, hard-light→overlay, soft-light→overlay,
                     difference→exclusion, exclusion→exclusion

    Example:
        >>> processor = BlendProcessor('feBlend', policy)
        >>> element = ET.fromstring('<feBlend mode="multiply" in="A" in2="B"/>')
        >>> result = processor.apply(element, context)
        >>> print(result.get_drawingml())  # '<a:blend blendMode="mult">...</a:blend>'
    """

    def __init__(self, filter_type: str = 'feBlend', policy: Optional['Policy'] = None):
        """
        Initialize the blend filter processor.

        Args:
            filter_type: Filter type name (default: 'feBlend')
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

        # Check for feBlend elements
        tag = self._get_element_localname(element)
        return (
            tag == 'feBlend' or
            tag.endswith('feBlend') or
            element.get('type') == 'feBlend'
        )

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        """
        Apply blend operation to combine two inputs with specified mode.

        Uses policy engine to select optimal rendering approach based on blend
        mode complexity and PowerPoint native support capabilities.

        Args:
            element: SVG feBlend element
            context: Filter processing context

        Returns:
            FilterResult containing the blend effect DrawingML
        """
        try:
            # Validate parameters first
            if not self._validate_parameters(element, context):
                return self._create_failure_result(
                    "Invalid feBlend parameters"
                )

            # Parse blend parameters
            params = self._parse_blend_parameters(element)

            # Get policy decision for rendering strategy
            strategy = self._get_rendering_strategy(params, context)

            # Generate DrawingML based on strategy
            drawingml = self._generate_blend_drawingml(params, context, strategy)

            return self._create_success_result(
                drawingml=drawingml,
                strategy=strategy,
                filter_type=self.filter_type,
                mode=params.mode.value,
                input1=params.input1,
                input2=params.input2,
                result_name=params.result_name,
                strategy_value=strategy.value,
                native_support=self._has_native_support(params),
                powerpoint_mode=self._get_powerpoint_mode(params.mode),
                processing_method=self._get_processing_method(strategy),
                blend_complexity=self._get_blend_complexity(params.mode)
            )

        except BlendFilterException as e:
            self.logger.warning(f"Blend filter processing failed: {e}")
            return self._create_failure_result(str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error in blend filter: {e}")
            return self._create_failure_result(f"Blend processing failed: {str(e)}")

    def _validate_parameters(self, element: ET.Element, context: FilterContext) -> bool:
        """
        Validate that the element has valid parameters for blend processing.

        Args:
            element: SVG element to validate
            context: Filter processing context

        Returns:
            True if element parameters are valid
        """
        try:
            params = self._parse_blend_parameters(element)

            # Validate blend mode
            if params.mode not in BlendMode:
                return False

            # Validate inputs (should be non-empty)
            if not params.input1 or not params.input2:
                return False

            return True

        except Exception:
            return False

    def _parse_blend_parameters(self, element: ET.Element) -> BlendParameters:
        """
        Parse blend parameters from SVG feBlend element.

        Args:
            element: SVG feBlend element

        Returns:
            BlendParameters with parsed values

        Raises:
            BlendFilterException: If parameters are invalid
        """
        try:
            # Parse blend mode with default
            mode_str = element.get('mode', 'normal')
            try:
                mode = BlendMode(mode_str)
            except ValueError:
                raise BlendFilterException(f"Invalid blend mode: '{mode_str}'")

            # Parse input references
            input1 = element.get('in', 'SourceGraphic')
            input2 = element.get('in2', 'SourceGraphic')

            # Parse result name
            result_name = element.get('result', 'blend')

            return BlendParameters(
                mode=mode,
                input1=input1,
                input2=input2,
                result_name=result_name
            )

        except Exception as e:
            raise BlendFilterException(f"Failed to parse blend parameters: {e}")

    def _get_rendering_strategy(self, params: BlendParameters, context: FilterContext) -> FilterStrategy:
        """
        Determine optimal rendering strategy using policy engine.

        Args:
            params: Parsed blend parameters
            context: Filter processing context

        Returns:
            FilterStrategy for rendering this blend operation
        """
        if self.policy:
            # Use policy to make informed decision
            decision_context = {
                'blend_mode': params.mode.value,
                'native_support': self._has_native_support(params),
                'complexity': self._get_blend_complexity(params.mode),
                'inputs': [params.input1, params.input2]
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
        elif self._has_approximation_support(params):
            return FilterStrategy.APPROXIMATION
        else:
            return FilterStrategy.EMF_RASTERIZE

    def _has_native_support(self, params: BlendParameters) -> bool:
        """
        Determine if blend mode has native PowerPoint support.

        PowerPoint has excellent native support for the core 6 blend modes
        that map directly to its blend effect capabilities.

        Args:
            params: Blend parameters

        Returns:
            True if mode has native PowerPoint support
        """
        native_modes = [
            BlendMode.NORMAL,      # → over
            BlendMode.MULTIPLY,    # → mult
            BlendMode.SCREEN,      # → screen
            BlendMode.OVERLAY,     # → overlay
            BlendMode.DARKEN,      # → darken
            BlendMode.LIGHTEN      # → lighten
        ]

        return params.mode in native_modes

    def _has_approximation_support(self, params: BlendParameters) -> bool:
        """
        Check if blend mode can be approximated with PowerPoint effects.

        Args:
            params: Blend parameters

        Returns:
            True if mode can be reasonably approximated
        """
        approximation_modes = [
            BlendMode.COLOR_DODGE,   # → lighten
            BlendMode.COLOR_BURN,    # → darken
            BlendMode.HARD_LIGHT,    # → overlay
            BlendMode.SOFT_LIGHT,    # → overlay
            BlendMode.DIFFERENCE,    # → exclusion (limited support)
            BlendMode.EXCLUSION      # → exclusion (limited support)
        ]

        return params.mode in approximation_modes

    def _get_blend_complexity(self, mode: BlendMode) -> str:
        """
        Assess blend mode complexity for policy decisions.

        Args:
            mode: Blend mode to assess

        Returns:
            Complexity level: 'simple', 'moderate', 'complex'
        """
        if mode in [BlendMode.NORMAL, BlendMode.MULTIPLY, BlendMode.SCREEN]:
            return 'simple'
        elif mode in [BlendMode.OVERLAY, BlendMode.DARKEN, BlendMode.LIGHTEN]:
            return 'moderate'
        else:
            return 'complex'

    def _get_powerpoint_mode(self, mode: BlendMode) -> str:
        """
        Get the PowerPoint blend mode equivalent.

        Args:
            mode: SVG blend mode

        Returns:
            PowerPoint blend mode string
        """
        native_map = {
            BlendMode.NORMAL: 'over',
            BlendMode.MULTIPLY: 'mult',
            BlendMode.SCREEN: 'screen',
            BlendMode.OVERLAY: 'overlay',
            BlendMode.DARKEN: 'darken',
            BlendMode.LIGHTEN: 'lighten'
        }

        approximation_map = {
            BlendMode.COLOR_DODGE: 'lighten',
            BlendMode.COLOR_BURN: 'darken',
            BlendMode.HARD_LIGHT: 'overlay',
            BlendMode.SOFT_LIGHT: 'overlay',
            BlendMode.DIFFERENCE: 'exclusion',
            BlendMode.EXCLUSION: 'exclusion'
        }

        return native_map.get(mode) or approximation_map.get(mode, 'over')

    def _generate_blend_drawingml(self, params: BlendParameters, context: FilterContext,
                                 strategy: FilterStrategy) -> str:
        """
        Generate DrawingML for blend operation based on strategy.

        Args:
            params: Blend parameters
            context: Filter processing context
            strategy: Rendering strategy to use

        Returns:
            DrawingML XML string for blend effect
        """
        if strategy == FilterStrategy.NATIVE:
            return self._generate_native_blend_drawingml(params, context)
        elif strategy == FilterStrategy.APPROXIMATION:
            return self._generate_approximation_blend_drawingml(params, context)
        else:
            # EMF_RASTERIZE - provide placeholder for raster fallback
            return self._generate_raster_fallback_drawingml(params, context)

    def _generate_native_blend_drawingml(self, params: BlendParameters, context: FilterContext) -> str:
        """
        Generate native PowerPoint blend effect DrawingML.

        Uses PowerPoint's <a:blend> element with direct mode mapping for
        optimal rendering quality and performance.

        Args:
            params: Blend parameters
            context: Filter processing context

        Returns:
            DrawingML XML string for native blend effect
        """
        ppt_mode = self._get_powerpoint_mode(params.mode)

        drawingml_parts = [
            f'<a:blend blendMode="{ppt_mode}">',
            f'  <!-- Native blend: {params.input1} {params.mode.value} {params.input2} -->',
            '</a:blend>'
        ]

        return '\n'.join(drawingml_parts)

    def _generate_approximation_blend_drawingml(self, params: BlendParameters, context: FilterContext) -> str:
        """
        Generate approximation blend effect for unsupported modes.

        Maps unsupported SVG blend modes to the closest available PowerPoint
        equivalent, providing reasonable visual approximation.

        Args:
            params: Blend parameters
            context: Filter processing context

        Returns:
            DrawingML XML string for approximated blend effect
        """
        ppt_mode = self._get_powerpoint_mode(params.mode)

        drawingml_parts = [
            f'<!-- Approximated blend mode: {params.mode.value} → {ppt_mode} -->',
            f'<a:blend blendMode="{ppt_mode}">',
            f'  <!-- Approximation for {params.mode.value} using {ppt_mode} -->',
            f'  <!-- Inputs: {params.input1}, {params.input2} -->',
            '</a:blend>'
        ]

        return '\n'.join(drawingml_parts)

    def _generate_raster_fallback_drawingml(self, params: BlendParameters, context: FilterContext) -> str:
        """
        Generate EMF rasterization fallback for complex blend modes.

        Args:
            params: Blend parameters
            context: Filter processing context

        Returns:
            DrawingML XML string with rasterization hint
        """
        # Provide metadata for EMF rasterization system
        drawingml_parts = [
            f'<!-- EMF rasterization required: complex blend mode {params.mode.value} -->',
            '<a:blip>',
            f'  <!-- Blend operation: {params.input1} {params.mode.value} {params.input2} -->',
            '  <a:extLst>',
            '    <a:ext uri="{raster-fallback}">',
            f'      <r:blend mode="{params.mode.value}" in1="{params.input1}" in2="{params.input2}"/>',
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
            FilterStrategy.NATIVE: 'Native PowerPoint blend modes',
            FilterStrategy.APPROXIMATION: 'Approximated blend mode mapping',
            FilterStrategy.EMF_RASTERIZE: 'EMF rasterization fallback'
        }

        return method_map.get(strategy, 'Unknown processing method')


def create_blend_processor(policy: Optional['Policy'] = None) -> BlendProcessor:
    """
    Factory function to create BlendProcessor with proper configuration.

    Args:
        policy: Optional policy engine for rendering decisions

    Returns:
        Configured BlendProcessor instance
    """
    return BlendProcessor('feBlend', policy)