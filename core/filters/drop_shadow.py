#!/usr/bin/env python3
"""
Drop Shadow Filter Processor for SVG Filter Effects

Implements SVG feDropShadow filter as a composite effect combining
offset and blur operations, using PowerPoint native shadow effects
for high-fidelity conversion.

This is a convenience filter that combines feOffset and feGaussianBlur
into a single effect for creating drop shadow appearances.
"""

from typing import Dict, List, Optional, Tuple, Union, Any
from enum import Enum
from dataclasses import dataclass
from lxml import etree as ET
import math

from .base import FilterProcessor, FilterContext, FilterResult, FilterStrategy
from .offset import OffsetParameters, OffsetProcessor
from .blur import BlurParameters, GaussianBlurProcessor
from ..units import unit
from ..policy.targets import PolicyDecision


class DropShadowException(Exception):
    """Exception raised during drop shadow processing."""
    pass


class DropShadowValidationError(DropShadowException, ValueError):
    """Exception raised when drop shadow parameters are invalid."""
    pass


@dataclass
class DropShadowParameters:
    """Parameters for drop shadow processing."""
    dx: float = 2.0  # Horizontal offset
    dy: float = 2.0  # Vertical offset
    std_deviation: float = 2.0  # Blur standard deviation
    flood_color: str = "black"  # Shadow color
    flood_opacity: float = 1.0  # Shadow opacity
    input_source: str = "SourceGraphic"
    result_name: Optional[str] = None

    def __post_init__(self):
        """Validate parameters after initialization."""
        # Ensure non-negative blur
        if self.std_deviation < 0:
            self.std_deviation = 0.0

        # Clamp opacity to valid range
        self.flood_opacity = max(0.0, min(self.flood_opacity, 1.0))

        # Normalize color
        if not self.flood_color:
            self.flood_color = "black"

    def get_complexity_score(self) -> float:
        """Calculate complexity score for strategy selection."""
        complexity = 0.0

        # Base complexity from offset magnitude
        offset_magnitude = math.sqrt(self.dx**2 + self.dy**2)
        complexity += min(offset_magnitude / 20.0, 2.0)  # Cap at 2x

        # Blur complexity
        complexity += min(self.std_deviation / 10.0, 2.0)  # Cap at 2x

        # Color complexity (non-black is more complex)
        if self.flood_color.lower() not in ["black", "#000000", "#000"]:
            complexity += 0.5

        # Partial opacity adds complexity
        if self.flood_opacity < 1.0:
            complexity += 0.3

        return complexity

    def is_effective(self) -> bool:
        """Check if drop shadow has any visible effect."""
        # Need either offset or blur to be visible
        has_offset = abs(self.dx) > 0.1 or abs(self.dy) > 0.1
        has_blur = self.std_deviation > 0.1
        has_opacity = self.flood_opacity > 0.01
        return (has_offset or has_blur) and has_opacity

    def get_shadow_distance(self) -> float:
        """Get shadow distance magnitude."""
        return math.sqrt(self.dx**2 + self.dy**2)

    def get_shadow_angle(self) -> float:
        """Get shadow angle in PowerPoint units (21600000 = 360°)."""
        if self.dx == 0 and self.dy == 0:
            return 0

        # Calculate angle in radians, then convert to PowerPoint units
        angle_rad = math.atan2(self.dy, self.dx)
        angle_deg = math.degrees(angle_rad)

        # PowerPoint uses 21600000 units for 360 degrees
        ppt_angle = int((angle_deg * 60000) % 21600000)
        return ppt_angle

    def to_offset_parameters(self) -> OffsetParameters:
        """Convert to OffsetParameters for composite processing."""
        return OffsetParameters(
            dx=self.dx,
            dy=self.dy,
            input_source=self.input_source,
            result_name="offset_shadow"
        )

    def to_blur_parameters(self) -> BlurParameters:
        """Convert to BlurParameters for composite processing."""
        return BlurParameters(
            std_deviation_x=self.std_deviation,
            std_deviation_y=self.std_deviation,
            edge_mode="duplicate",
            input_source="offset_shadow",
            result_name=self.result_name or "drop_shadow"
        )


class DropShadowProcessor(FilterProcessor):
    """Processor for SVG feDropShadow filter effects."""

    def __init__(self, policy=None):
        super().__init__(filter_type='feDropShadow', policy=policy)
        self.max_native_distance = 50.0  # PowerPoint works well up to ~50px distance
        self.max_native_blur = 25.0  # PowerPoint works well up to ~25px blur

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        """Check if this processor can handle the given element."""
        if element is None or element.tag != 'feDropShadow':
            return False
        return self._validate_parameters(element, context)

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        """Apply drop shadow processing to the element."""
        try:
            # Validate parameters first
            if not self._validate_parameters(element, context):
                raise DropShadowException("Invalid drop shadow parameters")

            # Parse drop shadow parameters
            params = self._parse_drop_shadow_parameters(element)

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
                error_message=f"Drop shadow processing failed: {str(e)}"
            )

    def _validate_parameters(self, element: ET.Element, context: FilterContext) -> bool:
        """Validate drop shadow parameters."""
        if element is None or context is None:
            return False
        try:
            self._parse_drop_shadow_parameters(element)
            return True
        except (DropShadowException, ValueError, TypeError):
            return False

    def _parse_drop_shadow_parameters(self, element: ET.Element) -> DropShadowParameters:
        """Parse drop shadow parameters from SVG element."""
        # Parse offset values
        dx = float(element.get('dx', '2.0'))
        dy = float(element.get('dy', '2.0'))

        # Parse blur standard deviation
        std_deviation = float(element.get('stdDeviation', '2.0'))

        # Parse flood color and opacity
        flood_color = element.get('flood-color', 'black')
        flood_opacity = float(element.get('flood-opacity', '1.0'))

        # Parse input source
        input_source = element.get('in', 'SourceGraphic')

        # Parse result name
        result_name = element.get('result')

        return DropShadowParameters(
            dx=dx,
            dy=dy,
            std_deviation=std_deviation,
            flood_color=flood_color,
            flood_opacity=flood_opacity,
            input_source=input_source,
            result_name=result_name
        )

    def _get_strategy(self, params: DropShadowParameters, context: FilterContext) -> FilterStrategy:
        """Determine the best strategy for drop shadow processing."""
        if self.policy:
            decision = self.policy.decide_drop_shadow_strategy(params, context)
            return decision.strategy

        # Default strategy logic
        complexity = params.get_complexity_score()

        if self._can_use_native_shadow(params):
            return FilterStrategy.NATIVE
        elif complexity < 3.0:
            return FilterStrategy.APPROXIMATION
        else:
            return FilterStrategy.EMF_RASTERIZE

    def _can_use_native_shadow(self, params: DropShadowParameters) -> bool:
        """Check if parameters can be handled with native PowerPoint shadow."""
        # Check if shadow is effective
        if not params.is_effective():
            return True  # No-op case

        # Check distance constraints
        distance = params.get_shadow_distance()
        if distance > self.max_native_distance:
            return False

        # Check blur constraints
        if params.std_deviation > self.max_native_blur:
            return False

        # PowerPoint shadows work best with standard colors and opacity
        if params.flood_opacity < 0.1:
            return False  # Too transparent

        return True

    def _apply_native_strategy(self, params: DropShadowParameters, context: FilterContext) -> FilterResult:
        """Apply native PowerPoint shadow effects."""
        try:
            drawingml = ""

            if not params.is_effective():
                # No-op case: very small or transparent shadow
                drawingml = "<!-- No visible drop shadow effect -->"
            else:
                # Generate native shadow effect
                drawingml = self._generate_native_shadow_drawingml(params, context)

            return FilterResult(
                success=True,
                strategy=FilterStrategy.NATIVE,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'native',
                    'dx': params.dx,
                    'dy': params.dy,
                    'std_deviation': params.std_deviation,
                    'flood_color': params.flood_color,
                    'flood_opacity': params.flood_opacity,
                    'shadow_distance': params.get_shadow_distance(),
                    'shadow_angle': params.get_shadow_angle(),
                    'complexity': params.get_complexity_score()
                }
            )

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.NATIVE,
                drawingml="",
                error_message=f"Native drop shadow failed: {str(e)}"
            )

    def _generate_native_shadow_drawingml(self, params: DropShadowParameters, context: FilterContext) -> str:
        """Generate DrawingML for native PowerPoint shadow effect."""
        # Calculate shadow parameters
        distance_emu = unit(f"{params.get_shadow_distance()}px").to_emu()
        blur_radius_emu = unit(f"{params.std_deviation}px").to_emu()
        angle = params.get_shadow_angle()

        # Clamp to PowerPoint limits
        distance_emu = max(0, min(int(distance_emu), 1270000))  # ~50px max
        blur_radius_emu = max(0, min(int(blur_radius_emu), 635000))  # ~25px max

        # Convert color
        shadow_color = self._convert_color_to_hex(params.flood_color)

        # Convert opacity to PowerPoint alpha (0-100000)
        alpha_value = int(params.flood_opacity * 100000)

        # Generate outer shadow effect
        shadow_xml = f"""<a:outerShdw blurRad="{blur_radius_emu}" dist="{distance_emu}" dir="{angle}"
                        rotWithShape="0" sx="100000" sy="100000" kx="0" ky="0" algn="ctr">
  <a:srgbClr val="{shadow_color}">
    <a:alpha val="{alpha_value}"/>
  </a:srgbClr>
</a:outerShdw>"""

        return shadow_xml

    def _apply_approximation_strategy(self, params: DropShadowParameters, context: FilterContext) -> FilterResult:
        """Apply approximation strategy using composite effects."""
        try:
            drawingml = self._generate_composite_shadow_drawingml(params, context)

            return FilterResult(
                success=True,
                strategy=FilterStrategy.APPROXIMATION,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'composite',
                    'dx': params.dx,
                    'dy': params.dy,
                    'std_deviation': params.std_deviation,
                    'flood_color': params.flood_color,
                    'flood_opacity': params.flood_opacity,
                    'complexity': params.get_complexity_score()
                }
            )

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.APPROXIMATION,
                drawingml="",
                error_message=f"Approximation drop shadow failed: {str(e)}"
            )

    def _generate_composite_shadow_drawingml(self, params: DropShadowParameters, context: FilterContext) -> str:
        """Generate DrawingML for composite shadow using multiple effects."""
        effects = []

        # Create a less optimal but functional shadow using multiple effects
        # This is used when the shadow parameters exceed native PowerPoint limits

        # Base shadow with reduced parameters
        reduced_distance = min(params.get_shadow_distance(), self.max_native_distance)
        reduced_blur = min(params.std_deviation, self.max_native_blur)

        distance_emu = unit(f"{reduced_distance}px").to_emu()
        blur_radius_emu = unit(f"{reduced_blur}px").to_emu()
        angle = params.get_shadow_angle()

        # Convert color and opacity
        shadow_color = self._convert_color_to_hex(params.flood_color)
        alpha_value = int(params.flood_opacity * 100000)

        # Primary shadow effect
        effects.append(f"""<a:outerShdw blurRad="{int(blur_radius_emu)}" dist="{int(distance_emu)}" dir="{angle}" algn="ctr">
  <a:srgbClr val="{shadow_color}">
    <a:alpha val="{alpha_value}"/>
  </a:srgbClr>
</a:outerShdw>""")

        # Add comment about approximation
        if params.get_shadow_distance() > self.max_native_distance or params.std_deviation > self.max_native_blur:
            effects.append(
                f"<!-- Drop shadow approximation: original distance={params.get_shadow_distance():.1f}px, blur={params.std_deviation:.1f}px -->"
            )

        return '\n'.join(effects)

    def _apply_emf_strategy(self, params: DropShadowParameters, context: FilterContext) -> FilterResult:
        """Apply EMF rasterization strategy for complex drop shadow."""
        try:
            # EMF rasterization placeholder
            # In a full implementation, this would:
            # 1. Render the source graphic to EMF bitmap
            # 2. Apply offset transformation
            # 3. Apply Gaussian blur convolution
            # 4. Apply color overlay
            # 5. Composite with original graphic
            # 6. Embed as blip reference

            return FilterResult(
                success=True,
                strategy=FilterStrategy.EMF_RASTERIZE,
                drawingml="<!-- EMF rasterization for complex drop shadow -->",
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'emf',
                    'dx': params.dx,
                    'dy': params.dy,
                    'std_deviation': params.std_deviation,
                    'flood_color': params.flood_color,
                    'flood_opacity': params.flood_opacity,
                    'complexity': params.get_complexity_score()
                }
            )

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.EMF_RASTERIZE,
                drawingml="",
                error_message=f"EMF drop shadow failed: {str(e)}"
            )

    def _convert_color_to_hex(self, color: str) -> str:
        """Convert color string to hex format for PowerPoint."""
        # Simple color name to hex conversion
        color_map = {
            'black': '000000',
            'white': 'FFFFFF',
            'red': 'FF0000',
            'green': '008000',
            'blue': '0000FF',
            'gray': '808080',
            'grey': '808080'
        }

        color_lower = color.lower().strip()

        # Check for hex format
        if color_lower.startswith('#'):
            hex_color = color_lower[1:]
            if len(hex_color) == 3:
                # Convert 3-digit hex to 6-digit
                hex_color = ''.join([c*2 for c in hex_color])
            return hex_color.upper()

        # Check for named colors
        if color_lower in color_map:
            return color_map[color_lower]

        # Default to black for unknown colors
        return '000000'


def create_drop_shadow_processor(policy=None) -> DropShadowProcessor:
    """Factory function to create a DropShadowProcessor instance."""
    return DropShadowProcessor(policy=policy)