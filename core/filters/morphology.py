#!/usr/bin/env python3
"""
Morphology Filter Implementation for SVG feMorphology Elements

Migrated from archive/legacy-src/converters/filters/geometric/morphology.py
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


class MorphologyFilterException(FilterException):
    """Exception raised when morphology filter processing fails."""
    pass


class MorphologyOperator(Enum):
    """Morphology operation types."""
    DILATE = "dilate"
    ERODE = "erode"


@dataclass
class MorphologyParameters:
    """Parameters for morphology operations."""
    operator: MorphologyOperator
    radius_x: float
    radius_y: float
    input_source: str = "SourceGraphic"
    result_name: str = "morphology"


class MorphologyProcessor(FilterProcessor):
    """
    Morphology filter processor for SVG feMorphology elements.

    Implements erosion and dilation operations using PowerPoint's native vector
    effects with comprehensive fallback strategies for complex operations.
    Integrates with clean slate architecture and policy engine for optimal
    rendering decisions.

    Features:
    - Dilate and erode operations using PowerPoint native shadows
    - Asymmetric radius support (different X/Y values)
    - Policy-driven strategy selection based on complexity
    - Template-based XML generation
    - Vector-first approach avoiding rasterization when possible

    Policy Integration:
    - NATIVE: Uses PowerPoint native shadow effects for moderate radius values
    - APPROXIMATION: Simplified shadow effects for complex asymmetric operations
    - EMF_RASTERIZE: Falls back to raster for extremely large radius values

    Morphology Operation Support Matrix:
    - NATIVE: symmetric operations, radius < 10px
    - APPROXIMATION: asymmetric operations, radius 10-20px
    - EMF_RASTERIZE: extreme radius values > 20px, complex asymmetric cases

    Example:
        >>> processor = MorphologyProcessor('feMorphology', policy)
        >>> element = ET.fromstring('<feMorphology operator="dilate" radius="5"/>')
        >>> result = processor.apply(element, context)
        >>> print(result.get_drawingml())  # '<a:outerShdw>...</a:outerShdw>'
    """

    def __init__(self, filter_type: str = 'feMorphology', policy: Optional['Policy'] = None):
        """
        Initialize the morphology filter processor.

        Args:
            filter_type: Filter type name (default: 'feMorphology')
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

        # Check for feMorphology elements
        tag = self._get_element_localname(element)
        return (
            tag == 'feMorphology' or
            tag.endswith('feMorphology') or
            element.get('type') == 'feMorphology'
        )

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        """
        Apply morphology operation to the SVG element.

        Uses policy engine to select optimal rendering strategy based on
        morphology complexity and PowerPoint native support capabilities.

        Args:
            element: SVG feMorphology element
            context: Filter processing context

        Returns:
            FilterResult containing the morphology effect DrawingML
        """
        try:
            # Validate parameters first
            if not self._validate_parameters(element, context):
                return self._create_failure_result(
                    "Invalid feMorphology parameters"
                )

            # Parse morphology parameters
            params = self._parse_morphology_parameters(element)

            # Get policy decision for rendering strategy
            strategy = self._get_rendering_strategy(params, context)

            # Generate DrawingML based on strategy
            drawingml = self._generate_morphology_drawingml(params, context, strategy)

            # Create success result with comprehensive metadata
            return self._create_success_result(
                drawingml=drawingml,
                strategy=strategy,
                filter_type=self.filter_type,
                processing_strategy=strategy.value,
                operator=params.operator.value,
                radius_x=params.radius_x,
                radius_y=params.radius_y,
                input_source=params.input_source,
                result_name=params.result_name,
                strategy_value=strategy.value,
                native_support=self._has_native_support(params),
                is_symmetric=abs(params.radius_x - params.radius_y) < 0.1,
                morphology_complexity=self._get_morphology_complexity(params),
                processing_method=self._get_processing_method_description(strategy, params),
                max_radius=max(params.radius_x, params.radius_y)
            )

        except Exception as e:
            self.logger.error(f"Morphology filter processing failed: {e}")
            return self._create_failure_result(f"Morphology processing failed: {e}")

    def _validate_parameters(self, element: ET.Element, context: FilterContext) -> bool:
        """
        Validate morphology filter parameters.

        Args:
            element: SVG element to validate
            context: Filter processing context

        Returns:
            True if parameters are valid, False otherwise
        """
        if element is None or context is None:
            return False

        try:
            # Try to parse parameters - if it succeeds, they're valid
            self._parse_morphology_parameters(element)
            return True
        except (MorphologyFilterException, ValueError, TypeError):
            return False

    def _parse_morphology_parameters(self, element: ET.Element) -> MorphologyParameters:
        """
        Parse morphology parameters from SVG feMorphology element.

        Args:
            element: SVG feMorphology element

        Returns:
            MorphologyParameters with parsed values

        Raises:
            MorphologyFilterException: If parameters are invalid
        """
        try:
            # Parse operator
            operator_str = element.get('operator', 'dilate')
            try:
                operator = MorphologyOperator(operator_str)
            except ValueError:
                raise MorphologyFilterException(f"Invalid morphology operator: '{operator_str}'")

            # Parse radius (can be single value or space-separated x,y values)
            radius_str = element.get('radius', '0')
            radius_parts = radius_str.strip().split()

            if len(radius_parts) == 1:
                # Single radius value applies to both X and Y
                radius_x = radius_y = float(radius_parts[0])
            elif len(radius_parts) == 2:
                # Separate X and Y radius values
                radius_x = float(radius_parts[0])
                radius_y = float(radius_parts[1])
            else:
                raise MorphologyFilterException(f"Invalid radius format: '{radius_str}'")

            # Ensure non-negative radius values
            if radius_x < 0 or radius_y < 0:
                raise MorphologyFilterException("Radius values must be non-negative")

            # Parse input source
            input_source = element.get('in', 'SourceGraphic')

            # Parse result name
            result_name = element.get('result', 'morphology')

            return MorphologyParameters(
                operator=operator,
                radius_x=radius_x,
                radius_y=radius_y,
                input_source=input_source,
                result_name=result_name
            )

        except (ValueError, TypeError) as e:
            raise MorphologyFilterException(f"Failed to parse morphology parameters: {e}")

    def _get_rendering_strategy(self, params: MorphologyParameters, context: FilterContext) -> FilterStrategy:
        """
        Get rendering strategy from policy engine based on morphology complexity.

        Args:
            params: Morphology parameters
            context: Filter processing context

        Returns:
            FilterStrategy enum value
        """
        if self.policy:
            decision_context = self._create_decision_context(params, context)
            try:
                return self.policy.decide_filter_strategy(
                    filter_type=self.filter_type,
                    element=context.element,
                    context=decision_context
                )
            except Exception as e:
                self.logger.warning(f"Policy decision failed, using fallback: {e}")

        # Fallback decision logic
        max_radius = max(params.radius_x, params.radius_y)

        if max_radius == 0.0:
            return FilterStrategy.NATIVE  # No-op case

        if self._has_native_support(params):
            return FilterStrategy.NATIVE
        elif self._has_approximation_support(params):
            return FilterStrategy.APPROXIMATION
        else:
            return FilterStrategy.EMF_RASTERIZE

    def _has_native_support(self, params: MorphologyParameters) -> bool:
        """
        Determine if morphology operation has native PowerPoint support.
        PowerPoint has good native support for symmetric morphology operations
        with moderate radius values using shadow effects.

        Args:
            params: Morphology parameters

        Returns:
            True if native support is available
        """
        max_radius = max(params.radius_x, params.radius_y)

        # Native support for moderate radius values
        if max_radius > 10.0:
            return False

        # Prefer native for symmetric operations
        is_symmetric = abs(params.radius_x - params.radius_y) < 0.1

        return is_symmetric and max_radius <= 10.0

    def _has_approximation_support(self, params: MorphologyParameters) -> bool:
        """
        Determine if morphology operation can be approximated.

        Args:
            params: Morphology parameters

        Returns:
            True if approximation is possible
        """
        max_radius = max(params.radius_x, params.radius_y)

        # Approximation for larger radius values and asymmetric operations
        return max_radius <= 20.0

    def _get_morphology_complexity(self, params: MorphologyParameters) -> str:
        """
        Assess morphology operation complexity for policy decisions.

        Args:
            params: Morphology parameters

        Returns:
            Complexity level string
        """
        max_radius = max(params.radius_x, params.radius_y)
        is_symmetric = abs(params.radius_x - params.radius_y) < 0.1

        if max_radius == 0.0:
            return "no-op"
        elif max_radius <= 5.0 and is_symmetric:
            return "simple"
        elif max_radius <= 10.0:
            return "moderate"
        elif max_radius <= 20.0:
            return "complex"
        else:
            return "extreme"

    def _create_decision_context(self, params: MorphologyParameters, context: FilterContext) -> Dict[str, Any]:
        """
        Create decision context for policy engine.

        Args:
            params: Morphology parameters
            context: Filter processing context

        Returns:
            Dictionary with decision context information
        """
        max_radius = max(params.radius_x, params.radius_y)
        is_symmetric = abs(params.radius_x - params.radius_y) < 0.1

        return {
            'operator': params.operator.value,
            'max_radius': max_radius,
            'radius_x': params.radius_x,
            'radius_y': params.radius_y,
            'is_symmetric': is_symmetric,
            'native_support': self._has_native_support(params),
            'complexity': self._get_morphology_complexity(params),
            'input_source': params.input_source
        }

    def _generate_morphology_drawingml(self, params: MorphologyParameters, context: FilterContext,
                                       strategy: FilterStrategy) -> str:
        """
        Generate morphology effect DrawingML based on strategy.

        Args:
            params: Morphology parameters
            context: Filter processing context
            strategy: Rendering strategy

        Returns:
            Generated DrawingML XML string
        """
        if strategy == FilterStrategy.NATIVE:
            return self._generate_native_morphology_drawingml(params, context)
        elif strategy == FilterStrategy.APPROXIMATION:
            return self._generate_approximation_morphology_drawingml(params, context)
        else:  # EMF_RASTERIZE
            return self._generate_raster_fallback_drawingml(params, context)

    def _generate_native_morphology_drawingml(self, params: MorphologyParameters, context: FilterContext) -> str:
        """
        Generate native PowerPoint morphology effect using shadow effects.

        Args:
            params: Morphology parameters
            context: Filter processing context

        Returns:
            Native DrawingML XML string
        """
        # Convert radius to EMU (English Metric Units)
        radius_x_emu = int(params.radius_x * 12700)  # 1px = 12700 EMU
        radius_y_emu = int(params.radius_y * 12700)

        # Handle no-op case
        if max(params.radius_x, params.radius_y) == 0.0:
            return "<!-- No morphology operation: zero radius -->"

        # Check if symmetric operation
        is_symmetric = abs(params.radius_x - params.radius_y) < 0.1

        if params.operator == MorphologyOperator.DILATE:
            if is_symmetric:
                # Symmetric dilate using outer shadow
                return f"""<!-- Native morphology: {params.operator.value} radius={params.radius_x} -->
<a:effectLst>
  <a:outerShdw blurRad="0" dist="{radius_x_emu}" dir="0"
              rotWithShape="0" sx="100000" sy="100000" kx="0" ky="0" algn="ctr">
    <a:srgbClr val="000000">
      <a:alpha val="100000"/>
    </a:srgbClr>
  </a:outerShdw>
</a:effectLst>"""
            else:
                # Asymmetric dilate with proportional scaling
                avg_radius_emu = int((radius_x_emu + radius_y_emu) / 2)
                sx_scaling = int((radius_x_emu / avg_radius_emu) * 100000) if avg_radius_emu > 0 else 100000
                sy_scaling = int((radius_y_emu / avg_radius_emu) * 100000) if avg_radius_emu > 0 else 100000

                return f"""<!-- Native morphology: {params.operator.value} asymmetric rx={params.radius_x} ry={params.radius_y} -->
<a:effectLst>
  <a:outerShdw blurRad="0" dist="{avg_radius_emu}" dir="0"
              rotWithShape="0" sx="{sx_scaling}" sy="{sy_scaling}" kx="0" ky="0" algn="ctr">
    <a:srgbClr val="000000">
      <a:alpha val="100000"/>
    </a:srgbClr>
  </a:outerShdw>
</a:effectLst>"""

        else:  # ERODE
            if is_symmetric:
                # Symmetric erode using inner shadow
                return f"""<!-- Native morphology: {params.operator.value} radius={params.radius_x} -->
<a:effectLst>
  <a:innerShdw blurRad="0" dist="{radius_x_emu}" dir="180"
              rotWithShape="0" sx="100000" sy="100000" kx="0" ky="0" algn="ctr">
    <a:srgbClr val="FFFFFF">
      <a:alpha val="100000"/>
    </a:srgbClr>
  </a:innerShdw>
</a:effectLst>"""
            else:
                # Asymmetric erode with proportional scaling
                avg_radius_emu = int((radius_x_emu + radius_y_emu) / 2)
                sx_scaling = int((radius_x_emu / avg_radius_emu) * 100000) if avg_radius_emu > 0 else 100000
                sy_scaling = int((radius_y_emu / avg_radius_emu) * 100000) if avg_radius_emu > 0 else 100000

                return f"""<!-- Native morphology: {params.operator.value} asymmetric rx={params.radius_x} ry={params.radius_y} -->
<a:effectLst>
  <a:innerShdw blurRad="0" dist="{avg_radius_emu}" dir="180"
              rotWithShape="0" sx="{sx_scaling}" sy="{sy_scaling}" kx="0" ky="0" algn="ctr">
    <a:srgbClr val="FFFFFF">
      <a:alpha val="100000"/>
    </a:srgbClr>
  </a:innerShdw>
</a:effectLst>"""

    def _generate_approximation_morphology_drawingml(self, params: MorphologyParameters, context: FilterContext) -> str:
        """
        Generate approximation morphology effect for complex operations.

        Args:
            params: Morphology parameters
            context: Filter processing context

        Returns:
            Approximation DrawingML XML string
        """
        # Simplified shadow effects for complex operations
        radius_emu = int(max(params.radius_x, params.radius_y) * 12700)

        if params.operator == MorphologyOperator.DILATE:
            return f"""<!-- Approximated morphology: {params.operator.value} simplified -->
<a:effectLst>
  <a:outerShdw blurRad="{radius_emu // 4}" dist="{radius_emu}" dir="0"
              rotWithShape="0" sx="100000" sy="100000" kx="0" ky="0" algn="ctr">
    <a:srgbClr val="000000">
      <a:alpha val="80000"/>
    </a:srgbClr>
  </a:outerShdw>
</a:effectLst>"""
        else:  # ERODE
            return f"""<!-- Approximated morphology: {params.operator.value} simplified -->
<a:effectLst>
  <a:innerShdw blurRad="{radius_emu // 4}" dist="{radius_emu}" dir="180"
              rotWithShape="0" sx="100000" sy="100000" kx="0" ky="0" algn="ctr">
    <a:srgbClr val="FFFFFF">
      <a:alpha val="80000"/>
    </a:srgbClr>
  </a:innerShdw>
</a:effectLst>"""

    def _generate_raster_fallback_drawingml(self, params: MorphologyParameters, context: FilterContext) -> str:
        """
        Generate EMF rasterization fallback for extremely complex morphology operations.

        Args:
            params: Morphology parameters
            context: Filter processing context

        Returns:
            EMF fallback DrawingML XML string
        """
        return f"""<!-- EMF rasterization required: complex morphology operation {params.operator.value} -->
<a:blip>
  <!-- Morphology operation: {params.input_source} {params.operator.value} rx={params.radius_x} ry={params.radius_y} -->
  <a:extLst>
    <a:ext uri="{{raster-fallback}}">
      <r:morphology operator="{params.operator.value}" radiusX="{params.radius_x}" radiusY="{params.radius_y}" in="{params.input_source}"
/>
    </a:ext>
  </a:extLst>
</a:blip>"""

    def _get_processing_method_description(self, strategy: FilterStrategy, params: MorphologyParameters) -> str:
        """
        Get human-readable description of processing method.

        Args:
            strategy: Selected strategy
            params: Morphology parameters

        Returns:
            Processing method description
        """
        if strategy == FilterStrategy.NATIVE:
            return f"Native PowerPoint {params.operator.value} using shadow effects"
        elif strategy == FilterStrategy.APPROXIMATION:
            return f"Approximated {params.operator.value} with simplified shadow effects"
        else:
            return f"EMF rasterization fallback for complex {params.operator.value}"


def create_morphology_processor(policy: Optional['Policy'] = None) -> MorphologyProcessor:
    """
    Factory function to create a MorphologyProcessor instance.

    Args:
        policy: Optional policy engine for decision making

    Returns:
        Configured MorphologyProcessor instance
    """
    return MorphologyProcessor(policy=policy)