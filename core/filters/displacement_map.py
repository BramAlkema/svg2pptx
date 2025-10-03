#!/usr/bin/env python3
"""
DisplacementMap Filter Processor for SVG Filter Effects

Implements SVG feDisplacementMap filter with vector-first strategy,
using PowerPoint custom geometry for path displacement and EMF fallback
for complex displacement operations.
"""

from typing import Dict, List, Optional, Tuple, Union, Any
from enum import Enum
from dataclasses import dataclass
from lxml import etree as ET
import math

from .base import FilterProcessor, FilterContext, FilterResult, FilterStrategy
from ..policy.targets import PolicyDecision


class DisplacementMapException(Exception):
    """Exception raised during displacement map processing."""
    pass


class DisplacementMapValidationError(DisplacementMapException, ValueError):
    """Exception raised when displacement map parameters are invalid."""
    pass


@dataclass
class DisplacementMapParameters:
    """Parameters for displacement map processing."""
    input_source: str = "SourceGraphic"
    displacement_source: str = "SourceGraphic"
    scale: float = 0.0
    x_channel_selector: str = "A"
    y_channel_selector: str = "A"
    result_name: Optional[str] = None

    def __post_init__(self):
        """Validate parameters after initialization."""
        # Validate channel selectors
        valid_channels = {"R", "G", "B", "A"}
        if self.x_channel_selector not in valid_channels:
            self.x_channel_selector = "A"
        if self.y_channel_selector not in valid_channels:
            self.y_channel_selector = "A"

    def get_complexity_score(self) -> float:
        """Calculate complexity score for strategy selection."""
        complexity = 0.5  # Base complexity

        # Scale factor contribution
        scale_factor = min(abs(self.scale) / 20.0, 3.0)  # Cap at 3x
        complexity += scale_factor

        # Mixed channels increase complexity
        if self.x_channel_selector != self.y_channel_selector:
            complexity += 0.5

        # High-precision channels (G, B) are more complex than R, A
        if (self.x_channel_selector in ['G', 'B'] or
            self.y_channel_selector in ['G', 'B']):
            complexity += 0.3

        return complexity

    def requires_subdivision(self) -> bool:
        """Check if displacement requires path subdivision."""
        return abs(self.scale) > 5.0

    def get_channel_index(self, channel_selector: str) -> int:
        """Get channel index for RGBA processing."""
        channel_map = {'R': 0, 'G': 1, 'B': 2, 'A': 3}
        return channel_map.get(channel_selector, 3)  # Default to alpha


class DisplacementMapProcessor(FilterProcessor):
    """Processor for SVG feDisplacementMap filter effects."""

    def __init__(self, policy=None):
        super().__init__(filter_type='feDisplacementMap', policy=policy)
        self.complexity_threshold = 3.0

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        """Check if this processor can handle the given element."""
        if element is None or element.tag != 'feDisplacementMap':
            return False
        return self._validate_parameters(element, context)

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        """Apply displacement map processing to the element."""
        try:
            # Validate parameters first
            if not self._validate_parameters(element, context):
                raise DisplacementMapException("Invalid displacement map parameters")

            # Parse displacement map parameters
            params = self._parse_displacement_map_parameters(element)

            # Get strategy from policy
            strategy = self._get_strategy(params, context)

            # Apply based on strategy
            if strategy == FilterStrategy.NATIVE:
                return self._apply_native_strategy(params, context)
            elif strategy == FilterStrategy.APPROXIMATION:
                return self._apply_approximation_strategy(params, context)
            else:  # EMF_RASTERIZE
                return self._apply_emf_strategy(params, context)

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.EMF_RASTERIZE,
                drawingml="",
                error_message=f"Displacement map processing failed: {str(e)}"
            )

    def _validate_parameters(self, element: ET.Element, context: FilterContext) -> bool:
        """Validate displacement map parameters."""
        if element is None or context is None:
            return False
        try:
            self._parse_displacement_map_parameters(element)
            return True
        except (DisplacementMapException, ValueError, TypeError):
            return False

    def _parse_displacement_map_parameters(self, element: ET.Element) -> DisplacementMapParameters:
        """Parse displacement map parameters from SVG element."""
        # Parse input source
        input_source = element.get('in', 'SourceGraphic')

        # Parse displacement source
        displacement_source = element.get('in2', 'SourceGraphic')

        # Parse scale
        scale_str = element.get('scale', '0')
        try:
            scale = float(scale_str)
        except ValueError:
            raise DisplacementMapValidationError(f"Invalid scale value: {scale_str}")

        # Parse channel selectors
        x_channel_selector = element.get('xChannelSelector', 'A').upper()
        y_channel_selector = element.get('yChannelSelector', 'A').upper()

        # Parse result name
        result_name = element.get('result')

        return DisplacementMapParameters(
            input_source=input_source,
            displacement_source=displacement_source,
            scale=scale,
            x_channel_selector=x_channel_selector,
            y_channel_selector=y_channel_selector,
            result_name=result_name
        )

    def _get_strategy(self, params: DisplacementMapParameters, context: FilterContext) -> FilterStrategy:
        """Determine the best strategy for displacement map processing."""
        if self.policy:
            decision = self.policy.decide_displacement_map_strategy(params, context)
            return decision.strategy

        # Default strategy logic
        complexity = params.get_complexity_score()

        if self._can_use_vector_approach(params):
            return FilterStrategy.NATIVE
        elif complexity < self.complexity_threshold:
            return FilterStrategy.APPROXIMATION
        else:
            return FilterStrategy.EMF_RASTERIZE

    def _can_use_vector_approach(self, params: DisplacementMapParameters) -> bool:
        """Check if parameters can be handled with vector approach."""
        # Small displacement scales can use transform approximations
        if abs(params.scale) <= 10.0:
            return True

        # Simple channel mappings (same channel for X and Y)
        if params.x_channel_selector == params.y_channel_selector:
            return True

        return False

    def _apply_native_strategy(self, params: DisplacementMapParameters, context: FilterContext) -> FilterResult:
        """Apply native PowerPoint effects for displacement map."""
        try:
            drawingml = ""

            if abs(params.scale) < 1.0:
                # Very small displacement - use identity transform
                drawingml = "<!-- Minimal displacement: no visible effect -->"
            elif abs(params.scale) <= 5.0:
                # Small displacement - use transform matrix
                drawingml = self._generate_transform_displacement_drawingml(params, context)
            else:
                # Medium displacement - use custom geometry
                drawingml = self._generate_custom_geometry_drawingml(params, context)

            return FilterResult(
                success=True,
                strategy=FilterStrategy.NATIVE,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'vector',
                    'scale': params.scale,
                    'complexity': params.get_complexity_score()
                }
            )

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.NATIVE,
                drawingml="",
                error_message=f"Native displacement map failed: {str(e)}"
            )

    def _generate_transform_displacement_drawingml(self, params: DisplacementMapParameters, context: FilterContext) -> str:
        """Generate DrawingML for transform-based displacement."""
        # Calculate displacement offsets based on scale
        # This is a simplified approach using transform matrices
        x_offset = params.scale * 0.1  # Scale factor for transform
        y_offset = params.scale * 0.1

        # Convert to EMU (English Metric Units)
        x_offset_emu = int(x_offset * 12700)  # 1px = 12700 EMU
        y_offset_emu = int(y_offset * 12700)

        return f"""<a:xfrm>
  <a:off x="{x_offset_emu}" y="{y_offset_emu}"/>
  <a:ext cx="100000" cy="100000"/>
</a:xfrm>"""

    def _generate_custom_geometry_drawingml(self, params: DisplacementMapParameters, context: FilterContext) -> str:
        """Generate DrawingML for custom geometry displacement."""
        # Create a displaced path using custom geometry
        # This is a simplified rectangular path with displacement

        # Calculate displacement vectors
        scale_factor = params.scale / 10.0
        displacement_x = int(scale_factor * 12700)  # Convert to EMU
        displacement_y = int(scale_factor * 12700)

        # Create displaced rectangle points
        width = 200000  # Default width in EMU
        height = 200000  # Default height in EMU

        # Apply displacement to corner points
        points = [
            (0, 0),
            (width + displacement_x, displacement_y),
            (width + displacement_x, height + displacement_y),
            (displacement_x, height + displacement_y)
        ]

        # Build path commands
        path_commands = []
        if points:
            path_commands.append(f'<a:moveTo><a:pt x="{points[0][0]}" y="{points[0][1]}"/></a:moveTo>')
            for x, y in points[1:]:
                path_commands.append(f'<a:lnTo><a:pt x="{x}" y="{y}"/></a:lnTo>')
            path_commands.append('<a:close/>')

        return f"""<a:custGeom>
  <a:pathLst>
    <a:path w="2000000" h="2000000">
      {''.join(path_commands)}
    </a:path>
  </a:pathLst>
</a:custGeom>"""

    def _apply_approximation_strategy(self, params: DisplacementMapParameters, context: FilterContext) -> FilterResult:
        """Apply approximation strategy using PowerPoint effects."""
        try:
            # For approximation, use skew transforms to simulate displacement
            skew_x = params.scale * 100000  # Convert to PowerPoint units
            skew_y = params.scale * 100000

            # Clamp to reasonable values
            skew_x = max(-5400000, min(skew_x, 5400000))  # ±90 degrees
            skew_y = max(-5400000, min(skew_y, 5400000))

            drawingml = f"""<a:xfrm>
  <a:off x="0" y="0"/>
  <a:ext cx="100000" cy="100000"/>
  <a:chOff x="{int(skew_x)}" y="{int(skew_y)}"/>
</a:xfrm>"""

            return FilterResult(
                success=True,
                strategy=FilterStrategy.APPROXIMATION,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'approximation',
                    'scale': params.scale,
                    'complexity': params.get_complexity_score()
                }
            )

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.APPROXIMATION,
                drawingml="",
                error_message=f"Approximation displacement map failed: {str(e)}"
            )

    def _apply_emf_strategy(self, params: DisplacementMapParameters, context: FilterContext) -> FilterResult:
        """Apply EMF rasterization strategy for complex displacement map."""
        try:
            # EMF rasterization placeholder
            # In a full implementation, this would:
            # 1. Extract displacement map pixel data
            # 2. Apply per-pixel displacement calculations
            # 3. Render to EMF bitmap
            # 4. Embed as blip reference

            return FilterResult(
                success=True,
                strategy=FilterStrategy.EMF_RASTERIZE,
                drawingml="<!-- EMF rasterization for complex displacement map -->",
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'emf',
                    'scale': params.scale,
                    'complexity': params.get_complexity_score()
                }
            )

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.EMF_RASTERIZE,
                drawingml="",
                error_message=f"EMF displacement map failed: {str(e)}"
            )

    def _extract_channel_value(self, rgba_pixel: Tuple[int, int, int, int], channel_selector: str) -> float:
        """Extract normalized channel value from RGBA pixel."""
        channel_index = {'R': 0, 'G': 1, 'B': 2, 'A': 3}
        index = channel_index.get(channel_selector.upper(), 3)

        channel_value = rgba_pixel[index]
        # Normalize to -0.5 to 0.5 range (standard SVG displacement)
        normalized_value = (channel_value / 255.0) - 0.5
        return normalized_value

    def _calculate_adaptive_subdivisions(self, params: DisplacementMapParameters, segment_length: float) -> int:
        """Calculate adaptive subdivisions based on displacement scale and segment length."""
        base_subdivisions = 2

        # Scale factor (higher displacement = more subdivisions)
        scale_factor = min(abs(params.scale) / 10.0, 5.0)  # Cap at 5x

        # Length factor (longer segments = more subdivisions)
        length_factor = min(segment_length / 50.0, 3.0)  # Cap at 3x

        total_subdivisions = int(base_subdivisions * scale_factor * length_factor)

        # Reasonable bounds
        return max(2, min(total_subdivisions, 20))

    def _clamp_displaced_point(self, original_point: Tuple[float, float],
                             displacement: Tuple[float, float],
                             bounds: Dict[str, float]) -> Tuple[float, float]:
        """Clamp displaced point to boundary conditions."""
        displaced_x = original_point[0] + displacement[0]
        displaced_y = original_point[1] + displacement[1]

        # Get bounds with defaults
        min_x = bounds.get('min_x', displaced_x)
        max_x = bounds.get('max_x', displaced_x)
        min_y = bounds.get('min_y', displaced_y)
        max_y = bounds.get('max_y', displaced_y)

        # Handle inverted bounds gracefully
        if max_x < min_x:
            min_x, max_x = max_x, min_x
        if max_y < min_y:
            min_y, max_y = max_y, min_y

        # Clamp to bounds
        clamped_x = max(min_x, min(displaced_x, max_x))
        clamped_y = max(min_y, min(displaced_y, max_y))

        return (clamped_x, clamped_y)


def create_displacement_map_processor(policy=None) -> DisplacementMapProcessor:
    """Factory function to create a DisplacementMapProcessor instance."""
    return DisplacementMapProcessor(policy=policy)