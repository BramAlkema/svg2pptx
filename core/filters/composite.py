#!/usr/bin/env python3
"""
Composite Filter Implementation for SVG feComposite Elements

Migrated from archive/legacy-src/converters/filters/geometric/composite.py
and adapted to the clean slate FilterProcessor architecture with policy
integration and template-based XML generation.
"""

from typing import Dict, Any, Optional, List, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum
import logging
from lxml import etree as ET

from .base import FilterProcessor, FilterContext, FilterResult, FilterStrategy, FilterException

if TYPE_CHECKING:
    from ..policy.engine import Policy

logger = logging.getLogger(__name__)


class CompositeFilterException(FilterException):
    """Exception raised when composite filter processing fails."""
    pass


class CompositeOperator(Enum):
    """Composite operation types for Porter-Duff and blend operations."""
    OVER = "over"
    IN = "in"
    OUT = "out"
    ATOP = "atop"
    XOR = "xor"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    DARKEN = "darken"
    LIGHTEN = "lighten"
    ARITHMETIC = "arithmetic"


@dataclass
class CompositeParameters:
    """Parameters for composite operations."""
    operator: CompositeOperator
    input1: str
    input2: str
    k1: float = 0.0  # For arithmetic operations
    k2: float = 0.0
    k3: float = 0.0
    k4: float = 0.0
    result_name: str = "composite"


class CompositeProcessor(FilterProcessor):
    """
    Composite filter processor for SVG feComposite elements.

    Implements layer composition operations using PowerPoint's native blend
    capabilities with comprehensive fallback strategies for complex compositing.
    Integrates with clean slate architecture and policy engine for optimal
    rendering decisions.

    Features:
    - Standard Porter-Duff operations (over, in, out, atop, xor)
    - Blend operations (multiply, screen, darken, lighten)
    - Arithmetic operations with custom coefficients
    - Policy-driven strategy selection
    - Template-based XML generation
    - Multi-input layer composition handling

    Policy Integration:
    - NATIVE: Uses PowerPoint native blend modes (over, multiply, screen, darken, lighten)
    - APPROXIMATION: Maps complex operations to closest PowerPoint equivalents
    - EMF_RASTERIZE: Falls back to raster for extremely complex compositing

    Composite Operation Support Matrix:
    - NATIVE: over, multiply, screen, darken, lighten
    - APPROXIMATION: in, out, atop, xor, arithmetic (with coefficient analysis)
    - EMF_RASTERIZE: complex arithmetic operations with multiple non-zero coefficients

    Example:
        >>> processor = CompositeProcessor('feComposite', policy)
        >>> element = ET.fromstring('<feComposite operator="over" in="A" in2="B"/>')
        >>> result = processor.apply(element, context)
        >>> print(result.get_drawingml())  # '<a:blend blendMode="over">...</a:blend>'
    """

    def __init__(self, filter_type: str = 'feComposite', policy: Optional['Policy'] = None):
        """
        Initialize the composite filter processor.

        Args:
            filter_type: Filter type name (default: 'feComposite')
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

        # Check for feComposite elements
        tag = self._get_element_localname(element)
        return (
            tag == 'feComposite' or
            tag.endswith('feComposite') or
            element.get('type') == 'feComposite'
        )

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        """
        Apply composite operation to the SVG element.

        Uses policy engine to select optimal rendering strategy based on
        composite operation complexity and PowerPoint native support capabilities.

        Args:
            element: SVG feComposite element
            context: Filter processing context

        Returns:
            FilterResult containing the composite effect DrawingML
        """
        try:
            # Validate parameters first
            if not self._validate_parameters(element, context):
                return self._create_failure_result(
                    "Invalid feComposite parameters"
                )

            # Parse composite parameters
            params = self._parse_composite_parameters(element)

            # Get policy decision for rendering strategy
            strategy = self._get_rendering_strategy(params, context)

            # Generate DrawingML based on strategy
            drawingml = self._generate_composite_drawingml(params, context, strategy)

            return self._create_success_result(
                drawingml=drawingml,
                strategy=strategy,
                filter_type=self.filter_type,
                operator=params.operator.value,
                input1=params.input1,
                input2=params.input2,
                result_name=params.result_name,
                strategy_value=strategy.value,
                native_support=self._has_native_support(params),
                is_arithmetic=params.operator == CompositeOperator.ARITHMETIC,
                composite_complexity=self._get_composite_complexity(params),
                processing_method=self._get_processing_method(strategy),
                # Add arithmetic coefficients if relevant
                k1=params.k1 if params.operator == CompositeOperator.ARITHMETIC else None,
                k2=params.k2 if params.operator == CompositeOperator.ARITHMETIC else None,
                k3=params.k3 if params.operator == CompositeOperator.ARITHMETIC else None,
                k4=params.k4 if params.operator == CompositeOperator.ARITHMETIC else None
            )

        except CompositeFilterException as e:
            self.logger.warning(f"Composite filter processing failed: {e}")
            return self._create_failure_result(str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error in composite filter: {e}")
            return self._create_failure_result(f"Composite processing failed: {str(e)}")

    def _validate_parameters(self, element: ET.Element, context: FilterContext) -> bool:
        """
        Validate that the element has valid parameters for composite processing.

        Args:
            element: SVG element to validate
            context: Filter processing context

        Returns:
            True if element parameters are valid
        """
        try:
            params = self._parse_composite_parameters(element)

            # Validate operator
            if params.operator not in CompositeOperator:
                return False

            # Validate inputs (should be non-empty)
            if not params.input1 or not params.input2:
                return False

            return True

        except Exception:
            return False

    def _parse_composite_parameters(self, element: ET.Element) -> CompositeParameters:
        """
        Parse composite parameters from SVG feComposite element.

        Args:
            element: SVG feComposite element

        Returns:
            CompositeParameters with parsed values

        Raises:
            CompositeFilterException: If parameters are invalid
        """
        try:
            # Parse operator
            operator_str = element.get('operator', 'over')
            try:
                operator = CompositeOperator(operator_str)
            except ValueError:
                raise CompositeFilterException(f"Invalid composite operator: '{operator_str}'")

            # Parse inputs
            input1 = element.get('in', 'SourceGraphic')
            input2 = element.get('in2', 'SourceGraphic')

            # Parse arithmetic coefficients (used for arithmetic operator)
            k1 = float(element.get('k1', '0'))
            k2 = float(element.get('k2', '0'))
            k3 = float(element.get('k3', '0'))
            k4 = float(element.get('k4', '0'))

            # Parse result name
            result_name = element.get('result', 'composite')

            return CompositeParameters(
                operator=operator,
                input1=input1,
                input2=input2,
                k1=k1, k2=k2, k3=k3, k4=k4,
                result_name=result_name
            )

        except ValueError as e:
            raise CompositeFilterException(f"Invalid composite parameters: {e}")
        except Exception as e:
            raise CompositeFilterException(f"Failed to parse composite parameters: {e}")

    def _get_rendering_strategy(self, params: CompositeParameters, context: FilterContext) -> FilterStrategy:
        """
        Determine optimal rendering strategy using policy engine.

        Args:
            params: Parsed composite parameters
            context: Filter processing context

        Returns:
            FilterStrategy for rendering this composite operation
        """
        if self.policy:
            # Use policy to make informed decision
            decision_context = {
                'operator': params.operator.value,
                'native_support': self._has_native_support(params),
                'is_arithmetic': params.operator == CompositeOperator.ARITHMETIC,
                'complexity': self._get_composite_complexity(params),
                'inputs': [params.input1, params.input2]
            }

            # Add arithmetic coefficients to context if relevant
            if params.operator == CompositeOperator.ARITHMETIC:
                decision_context.update({
                    'k1': params.k1, 'k2': params.k2,
                    'k3': params.k3, 'k4': params.k4
                })

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

    def _has_native_support(self, params: CompositeParameters) -> bool:
        """
        Determine if composite operation has native PowerPoint support.

        PowerPoint has excellent native support for common blend operations
        that map directly to its blend mode capabilities.

        Args:
            params: Composite parameters

        Returns:
            True if operation has native PowerPoint support
        """
        # PowerPoint has good support for common blend operations
        native_ops = [
            CompositeOperator.OVER,      # → over
            CompositeOperator.MULTIPLY,  # → mult
            CompositeOperator.SCREEN,    # → screen
            CompositeOperator.DARKEN,    # → darken
            CompositeOperator.LIGHTEN    # → lighten
        ]

        return params.operator in native_ops

    def _has_approximation_support(self, params: CompositeParameters) -> bool:
        """
        Check if composite operation can be approximated with PowerPoint effects.

        Args:
            params: Composite parameters

        Returns:
            True if operation can be reasonably approximated
        """
        # Porter-Duff operations can be approximated to some degree
        approximation_ops = [
            CompositeOperator.IN,      # Can be approximated with alpha effects
            CompositeOperator.OUT,     # Can be approximated with inverse alpha
            CompositeOperator.ATOP,    # Can be approximated with combined effects
            CompositeOperator.XOR,     # Can be approximated with exclusion
            CompositeOperator.ARITHMETIC  # Can be approximated based on coefficients
        ]

        return params.operator in approximation_ops

    def _get_composite_complexity(self, params: CompositeParameters) -> str:
        """
        Assess composite operation complexity for policy decisions.

        Args:
            params: Composite parameters

        Returns:
            Complexity level: 'simple', 'moderate', 'complex'
        """
        if params.operator in [CompositeOperator.OVER, CompositeOperator.MULTIPLY, CompositeOperator.SCREEN]:
            return 'simple'
        elif params.operator in [CompositeOperator.DARKEN, CompositeOperator.LIGHTEN, CompositeOperator.IN, CompositeOperator.OUT]:
            return 'moderate'
        elif params.operator == CompositeOperator.ARITHMETIC:
            # Complexity depends on number of non-zero coefficients
            non_zero_coeffs = sum(1 for k in [params.k1, params.k2, params.k3, params.k4] if k != 0)
            if non_zero_coeffs <= 2:
                return 'moderate'
            else:
                return 'complex'
        else:
            return 'complex'

    def _generate_composite_drawingml(self, params: CompositeParameters, context: FilterContext,
                                    strategy: FilterStrategy) -> str:
        """
        Generate DrawingML for composite operation based on strategy.

        Args:
            params: Composite parameters
            context: Filter processing context
            strategy: Rendering strategy to use

        Returns:
            DrawingML XML string for composite effect
        """
        if strategy == FilterStrategy.NATIVE:
            return self._generate_native_composite_drawingml(params, context)
        elif strategy == FilterStrategy.APPROXIMATION:
            return self._generate_approximation_composite_drawingml(params, context)
        else:
            # EMF_RASTERIZE - provide placeholder for raster fallback
            return self._generate_raster_fallback_drawingml(params, context)

    def _generate_native_composite_drawingml(self, params: CompositeParameters, context: FilterContext) -> str:
        """
        Generate native PowerPoint blend effect DrawingML.

        Uses PowerPoint's <a:blend> element with direct operator mapping for
        optimal rendering quality and performance.

        Args:
            params: Composite parameters
            context: Filter processing context

        Returns:
            DrawingML XML string for native blend effect
        """
        # Map composite operators to PowerPoint blend modes
        blend_map = {
            CompositeOperator.OVER: 'over',
            CompositeOperator.MULTIPLY: 'mult',
            CompositeOperator.SCREEN: 'screen',
            CompositeOperator.DARKEN: 'darken',
            CompositeOperator.LIGHTEN: 'lighten'
        }

        blend_mode = blend_map.get(params.operator, 'over')

        drawingml_parts = [
            f'<a:blend blendMode="{blend_mode}">',
            f'  <!-- Native composite: {params.input1} {params.operator.value} {params.input2} -->',
            '</a:blend>'
        ]

        return '\n'.join(drawingml_parts)

    def _generate_approximation_composite_drawingml(self, params: CompositeParameters, context: FilterContext) -> str:
        """
        Generate approximation composite effect for complex operations.

        Maps Porter-Duff and arithmetic operations to the closest available PowerPoint
        equivalent, providing reasonable visual approximation.

        Args:
            params: Composite parameters
            context: Filter processing context

        Returns:
            DrawingML XML string for approximated composite effect
        """
        if params.operator == CompositeOperator.ARITHMETIC:
            return self._generate_arithmetic_approximation_drawingml(params, context)
        else:
            return self._generate_porter_duff_approximation_drawingml(params, context)

    def _generate_arithmetic_approximation_drawingml(self, params: CompositeParameters, context: FilterContext) -> str:
        """
        Generate arithmetic composite approximation.

        Arithmetic compositing formula: result = k1*i1*i2 + k2*i1 + k3*i2 + k4

        Args:
            params: Composite parameters
            context: Filter processing context

        Returns:
            DrawingML XML string for arithmetic approximation
        """
        effects = []

        # Determine the primary operation based on coefficients
        if params.k1 > 0 and abs(params.k1) > max(abs(params.k2), abs(params.k3)):
            # Multiplication-like operation (k1 is dominant)
            effects.append('<a:blend blendMode="mult">')
            effects.append(f'  <!-- Arithmetic: multiplication-based (k1={params.k1}) -->')
        elif params.k2 > 0 and params.k3 > 0:
            # Addition-like operation (both k2 and k3 positive)
            effects.append('<a:blend blendMode="lighten">')
            effects.append(f'  <!-- Arithmetic: addition-based (k2={params.k2}, k3={params.k3}) -->')
        elif abs(params.k2) > abs(params.k3):
            # Input1 dominant
            effects.append('<a:blend blendMode="over">')
            effects.append(f'  <!-- Arithmetic: input1 dominant (k2={params.k2}) -->')
        elif abs(params.k3) > 0:
            # Input2 dominant
            effects.append('<a:blend blendMode="over">')
            effects.append(f'  <!-- Arithmetic: input2 dominant (k3={params.k3}) -->')
        else:
            # Default to over
            effects.append('<a:blend blendMode="over">')
            effects.append('  <!-- Arithmetic: default fallback -->')

        # Add transparency based on k4 offset
        if params.k4 != 0:
            # Convert k4 to alpha (k4 is additive offset, alpha is multiplicative)
            alpha_val = max(0, min(100000, int((1.0 - abs(params.k4)) * 100000)))
            effects.append(f'  <a:alpha val="{alpha_val}"/><!-- k4 offset: {params.k4} -->')

        effects.extend([
            f'  <!-- Full arithmetic: k1={params.k1} k2={params.k2} k3={params.k3} k4={params.k4} -->',
            '</a:blend>'
        ])

        return '\n'.join(effects)

    def _generate_porter_duff_approximation_drawingml(self, params: CompositeParameters, context: FilterContext) -> str:
        """
        Generate Porter-Duff operation approximation.

        Args:
            params: Composite parameters
            context: Filter processing context

        Returns:
            DrawingML XML string for Porter-Duff approximation
        """
        # Map Porter-Duff operations to closest PowerPoint equivalents
        approximation_map = {
            CompositeOperator.IN: 'mult',      # Source in destination
            CompositeOperator.OUT: 'exclusion',  # Source out of destination
            CompositeOperator.ATOP: 'overlay',   # Source atop destination
            CompositeOperator.XOR: 'exclusion'   # Exclusive or
        }

        blend_mode = approximation_map.get(params.operator, 'over')

        drawingml_parts = [
            f'<!-- Approximated Porter-Duff operation: {params.operator.value} → {blend_mode} -->',
            f'<a:blend blendMode="{blend_mode}">',
            f'  <!-- Approximation for {params.operator.value} using {blend_mode} -->',
            f'  <!-- Inputs: {params.input1}, {params.input2} -->',
            '</a:blend>'
        ]

        return '\n'.join(drawingml_parts)

    def _generate_raster_fallback_drawingml(self, params: CompositeParameters, context: FilterContext) -> str:
        """
        Generate EMF rasterization fallback for extremely complex compositing.

        Args:
            params: Composite parameters
            context: Filter processing context

        Returns:
            DrawingML XML string with rasterization hint
        """
        # Provide metadata for EMF rasterization system
        drawingml_parts = [
            f'<!-- EMF rasterization required: complex composite operation {params.operator.value} -->',
            '<a:blip>',
            f'  <!-- Composite operation: {params.input1} {params.operator.value} {params.input2} -->',
            '  <a:extLst>',
            '    <a:ext uri="{raster-fallback}">',
            f'      <r:composite operator="{params.operator.value}" in1="{params.input1}" in2="{params.input2}"'
        ]

        # Add arithmetic coefficients if relevant
        if params.operator == CompositeOperator.ARITHMETIC:
            drawingml_parts[-1] += f' k1="{params.k1}" k2="{params.k2}" k3="{params.k3}" k4="{params.k4}"'

        drawingml_parts.extend([
            '/>',
            '    </a:ext>',
            '  </a:extLst>',
            '</a:blip>'
        ])

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
            FilterStrategy.APPROXIMATION: 'Approximated composite operation mapping',
            FilterStrategy.EMF_RASTERIZE: 'EMF rasterization fallback'
        }

        return method_map.get(strategy, 'Unknown processing method')


def create_composite_processor(policy: Optional['Policy'] = None) -> CompositeProcessor:
    """
    Factory function to create CompositeProcessor with proper configuration.

    Args:
        policy: Optional policy engine for rendering decisions

    Returns:
        Configured CompositeProcessor instance
    """
    return CompositeProcessor('feComposite', policy)