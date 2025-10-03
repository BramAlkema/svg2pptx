#!/usr/bin/env python3
"""
Specular Lighting Filter Processor for SVG Filter Effects

Implements SVG feSpecularLighting filter with 3D specular lighting effects,
using PowerPoint native sp3d, bevel, lightRig, and outerShdw effects for
high-fidelity 3D specular reflection simulation.

This processor creates realistic 3D specular lighting effects by combining:
- a:sp3d for 3D shape simulation (reused from diffuse lighting)
- a:bevel for directional surface effects (reused from diffuse lighting)
- a:lightRig for lighting positioning (reused from diffuse lighting)
- a:outerShdw for specular highlight generation (new for specular)
- Material property mapping based on shininess
"""

from typing import Dict, List, Optional, Tuple, Union, Any
from enum import Enum
from dataclasses import dataclass
from lxml import etree as ET
import math

from .base import FilterProcessor, FilterContext, FilterResult, FilterStrategy
from ..units import unit
from ..policy.targets import PolicyDecision


class SpecularLightingException(Exception):
    """Exception raised during specular lighting processing."""
    pass


class SpecularLightingValidationError(SpecularLightingException, ValueError):
    """Exception raised when specular lighting parameters are invalid."""
    pass


@dataclass
class SpecularLightingParameters:
    """Parameters for specular lighting processing."""
    surface_scale: float = 1.0
    specular_constant: float = 1.0
    specular_exponent: float = 1.0
    lighting_color: str = "white"
    light_source_type: str = "distant"  # distant, point, spot

    # Distant light parameters
    light_azimuth: float = 0.0  # 0-360 degrees
    light_elevation: float = 0.0  # 0-90 degrees

    # Point light parameters
    light_x: float = 0.0
    light_y: float = 0.0
    light_z: float = 0.0

    # Spot light parameters
    light_points_at_x: float = 0.0
    light_points_at_y: float = 0.0
    light_points_at_z: float = 0.0
    cone_angle: float = 90.0
    spot_exponent: float = 1.0

    input_source: str = "SourceGraphic"
    result_name: Optional[str] = None

    def __post_init__(self):
        """Validate parameters after initialization."""
        # Clamp surface scale to reasonable range
        self.surface_scale = max(-50.0, min(self.surface_scale, 50.0))

        # Clamp specular constant to reasonable range
        self.specular_constant = max(0.0, min(self.specular_constant, 10.0))

        # Clamp specular exponent to reasonable range
        self.specular_exponent = max(0.0, min(self.specular_exponent, 128.0))

        # Normalize light angles
        self.light_azimuth = self.light_azimuth % 360.0
        self.light_elevation = max(0.0, min(self.light_elevation, 90.0))

        # Validate light source type
        valid_types = {"distant", "point", "spot"}
        if self.light_source_type not in valid_types:
            self.light_source_type = "distant"

        # Normalize lighting color
        if not self.lighting_color:
            self.lighting_color = "white"

    def get_complexity_score(self) -> float:
        """Calculate complexity score for strategy selection."""
        complexity = 0.5  # Base complexity

        # Surface scale complexity
        complexity += min(abs(self.surface_scale) / 10.0, 2.0)

        # Specular constant complexity
        complexity += min(self.specular_constant / 5.0, 1.5)

        # Specular exponent (shininess) complexity
        if self.specular_exponent > 64.0:
            complexity += 2.0  # High shininess is complex
        elif self.specular_exponent > 32.0:
            complexity += 1.5
        elif self.specular_exponent > 16.0:
            complexity += 1.0
        elif self.specular_exponent > 8.0:
            complexity += 0.5

        # Light source type complexity
        if self.light_source_type == "spot":
            complexity += 1.0
            if self.cone_angle < 30.0:
                complexity += 0.5  # Narrow cone is more complex
        elif self.light_source_type == "point":
            complexity += 0.5

        # Colored lighting adds complexity
        if self.lighting_color.lower() not in ["white", "#ffffff", "#fff"]:
            complexity += 0.3

        return complexity

    def is_effective(self) -> bool:
        """Check if specular lighting has any visible effect."""
        return (abs(self.surface_scale) > 0.01 and
                self.specular_constant > 0.01 and
                self.specular_exponent > 0.01)

    def get_light_direction_vector(self) -> Tuple[float, float, float]:
        """Calculate light direction vector for any light source type."""
        if self.light_source_type == "distant":
            # Convert spherical coordinates to Cartesian
            azimuth_rad = math.radians(self.light_azimuth)
            elevation_rad = math.radians(self.light_elevation)

            x = math.cos(elevation_rad) * math.cos(azimuth_rad)
            y = math.cos(elevation_rad) * math.sin(azimuth_rad)
            z = math.sin(elevation_rad)

            return (x, y, z)

        elif self.light_source_type == "point":
            # Normalize position vector
            length = math.sqrt(self.light_x**2 + self.light_y**2 + self.light_z**2)
            if length < 1e-6:
                return (0.0, 0.0, 1.0)  # Default to top

            return (self.light_x/length, self.light_y/length, self.light_z/length)

        elif self.light_source_type == "spot":
            # Direction from light position to target
            dx = self.light_points_at_x - self.light_x
            dy = self.light_points_at_y - self.light_y
            dz = self.light_points_at_z - self.light_z

            length = math.sqrt(dx**2 + dy**2 + dz**2)
            if length < 1e-6:
                return (0.0, 0.0, -1.0)  # Default down

            return (dx/length, dy/length, dz/length)

        return (0.0, 0.0, 1.0)  # Default

    def get_shininess_material(self) -> str:
        """Map specular exponent to PowerPoint material properties."""
        if self.specular_exponent <= 1.0:
            return "flat"         # No shininess - flat material
        elif self.specular_exponent <= 4.0:
            return "matte"        # Low shininess - matte material
        elif self.specular_exponent <= 16.0:
            return "plastic"      # Medium shininess - plastic material
        elif self.specular_exponent <= 32.0:
            return "softEdge"     # Medium-high shininess - soft edge material
        elif self.specular_exponent <= 64.0:
            return "metal"        # High shininess - metallic material
        elif self.specular_exponent < 128.0:
            return "warmMatte"    # Very high shininess - warm matte (glass-like)
        else:
            return "clear"        # Extreme shininess - clear/mirror-like material


class SpecularLightingProcessor(FilterProcessor):
    """Processor for SVG feSpecularLighting filter effects."""

    def __init__(self, policy=None):
        super().__init__(filter_type='feSpecularLighting', policy=policy)
        self.max_surface_scale = 20.0  # Practical limit for PowerPoint 3D effects
        self.max_extrusion_emu = 1270000  # ~50px max extrusion

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        """Check if this processor can handle the given element."""
        if element is None or element.tag != 'feSpecularLighting':
            return False
        return self._validate_parameters(element, context)

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        """Apply specular lighting processing to the element."""
        try:
            # Validate parameters first
            if not self._validate_parameters(element, context):
                raise SpecularLightingException("Invalid specular lighting parameters")

            # Parse specular lighting parameters
            params = self._parse_specular_lighting_parameters(element)

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
                error_message=f"Specular lighting processing failed: {str(e)}"
            )

    def _validate_parameters(self, element: ET.Element, context: FilterContext) -> bool:
        """Validate specular lighting parameters."""
        if element is None or context is None:
            return False
        try:
            params = self._parse_specular_lighting_parameters(element)

            # Validate specular constant (should be non-negative)
            if params.specular_constant < 0:
                return False

            # Validate specular exponent (should be non-negative)
            if params.specular_exponent < 0:
                return False

            return True
        except (SpecularLightingException, ValueError, TypeError):
            return False

    def _parse_specular_lighting_parameters(self, element: ET.Element) -> SpecularLightingParameters:
        """Parse specular lighting parameters from SVG element."""
        # Parse basic lighting parameters
        surface_scale = float(element.get('surfaceScale', '1.0'))
        specular_constant = float(element.get('specularConstant', '1.0'))
        specular_exponent = float(element.get('specularExponent', '1.0'))
        lighting_color = element.get('lighting-color', 'white')

        # Parse input source
        input_source = element.get('in', 'SourceGraphic')
        result_name = element.get('result')

        # Find light source child element
        light_source_type = "distant"
        light_params = {}

        for child in element:
            if child.tag == 'feDistantLight':
                light_source_type = "distant"
                light_params.update({
                    'light_azimuth': float(child.get('azimuth', '0')),
                    'light_elevation': float(child.get('elevation', '0'))
                })
            elif child.tag == 'fePointLight':
                light_source_type = "point"
                light_params.update({
                    'light_x': float(child.get('x', '0')),
                    'light_y': float(child.get('y', '0')),
                    'light_z': float(child.get('z', '0'))
                })
            elif child.tag == 'feSpotLight':
                light_source_type = "spot"
                light_params.update({
                    'light_x': float(child.get('x', '0')),
                    'light_y': float(child.get('y', '0')),
                    'light_z': float(child.get('z', '0')),
                    'light_points_at_x': float(child.get('pointsAtX', '0')),
                    'light_points_at_y': float(child.get('pointsAtY', '0')),
                    'light_points_at_z': float(child.get('pointsAtZ', '0')),
                    'cone_angle': float(child.get('limitingConeAngle', '90')),
                    'spot_exponent': float(child.get('specularExponent', '1'))
                })

        return SpecularLightingParameters(
            surface_scale=surface_scale,
            specular_constant=specular_constant,
            specular_exponent=specular_exponent,
            lighting_color=lighting_color,
            light_source_type=light_source_type,
            input_source=input_source,
            result_name=result_name,
            **light_params
        )

    def _get_strategy(self, params: SpecularLightingParameters, context: FilterContext) -> FilterStrategy:
        """Determine the best strategy for specular lighting processing."""
        if self.policy:
            decision = self.policy.decide_specular_lighting_strategy(params, context)
            return decision.strategy

        # Default strategy logic
        complexity = params.get_complexity_score()

        if self._can_use_native_3d(params):
            return FilterStrategy.NATIVE
        elif complexity < 4.5:
            return FilterStrategy.APPROXIMATION
        else:
            return FilterStrategy.EMF_RASTERIZE

    def _can_use_native_3d(self, params: SpecularLightingParameters) -> bool:
        """Check if parameters can be handled with native PowerPoint 3D effects."""
        # Check if lighting is effective
        if not params.is_effective():
            return True  # No-op case

        # Check surface scale constraints
        if abs(params.surface_scale) > self.max_surface_scale:
            return False

        # PowerPoint 3D effects work well with reasonable parameters
        if params.specular_constant > 5.0:
            return False  # Too intense

        # Very high shininess may not render well
        if params.specular_exponent > 128.0:
            return False

        return True

    def _apply_native_strategy(self, params: SpecularLightingParameters, context: FilterContext) -> FilterResult:
        """Apply native PowerPoint 3D specular lighting effects."""
        try:
            drawingml = ""

            if not params.is_effective():
                drawingml = "<!-- No visible specular lighting effect -->"
            else:
                drawingml = self._generate_3d_specular_drawingml(params, context)

            return FilterResult(
                success=True,
                strategy=FilterStrategy.NATIVE,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'native_3d_specular',
                    'surface_scale': params.surface_scale,
                    'specular_constant': params.specular_constant,
                    'specular_exponent': params.specular_exponent,
                    'lighting_color': params.lighting_color,
                    'light_source_type': params.light_source_type,
                    'material': params.get_shininess_material(),
                    'complexity': params.get_complexity_score()
                }
            )

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.NATIVE,
                drawingml="",
                error_message=f"Native specular lighting failed: {str(e)}"
            )

    def _generate_3d_specular_drawingml(self, params: SpecularLightingParameters, context: FilterContext) -> str:
        """Generate comprehensive 3D specular lighting effects using PowerPoint components."""
        effects = []

        # Generate a:sp3d for 3D shape simulation
        sp3d_effect = self._generate_sp3d_configuration(params, context)
        effects.append(sp3d_effect)

        # Generate a:bevel effects based on light direction
        bevel_effect = self._generate_bevel_effects(params, context)
        effects.append(bevel_effect)

        # Generate a:lightRig for lighting positioning
        lightrig_effect = self._generate_lightrig_positioning(params, context)
        effects.append(lightrig_effect)

        # Add outer highlight shadow for specular reflection
        highlight_effect = self._generate_specular_highlights(params, context)
        effects.append(highlight_effect)

        return '\n'.join(effects)

    def _generate_sp3d_configuration(self, params: SpecularLightingParameters, context: FilterContext) -> str:
        """Generate a:sp3d configuration for 3D shape simulation with specular materials."""
        # Calculate extrusion height based on surface scale
        extrusion_height = min(
            int(unit(f"{abs(params.surface_scale) * 10}px").to_emu()),
            self.max_extrusion_emu
        )

        # Calculate contour width based on specular constant
        contour_width = int(unit(f"{params.specular_constant * 2}px").to_emu())

        # Determine material properties based on shininess
        material = params.get_shininess_material()

        return f"""<a:sp3d extrusionH="{extrusion_height}" contourW="{contour_width}" prstMaterial="{material}">
  <!-- 3D shape simulation: surface_scale={params.surface_scale}, specular_exponent={params.specular_exponent} -->
  <!-- Material: {material} mapped from shininess -->
</a:sp3d>"""

    def _generate_bevel_effects(self, params: SpecularLightingParameters, context: FilterContext) -> str:
        """Generate a:bevel effects mapping from light direction and specular intensity."""
        x, y, z = params.get_light_direction_vector()

        # Determine primary direction based on strongest component
        abs_x, abs_y, abs_z = abs(x), abs(y), abs(z)

        if abs_z > 0.7:  # Primarily vertical
            bevel_type = "bevelT" if z > 0 else "bevelB"
        elif abs_y > abs_x:  # Primarily front/back
            bevel_type = "bevelT" if y > 0 else "bevelB"
        else:  # Primarily left/right
            bevel_type = "bevelT" if x > 0 else "bevelB"

        # Calculate bevel dimensions based on specular parameters
        bevel_width = int(unit(f"{params.specular_constant * 3}px").to_emu())
        bevel_height = int(unit(f"{params.specular_constant * 2}px").to_emu())

        return f"""<a:bevel {bevel_type}="1" w="{bevel_width}" h="{bevel_height}">
  <!-- Bevel effects: light_direction=({x:.2f}, {y:.2f}, {z:.2f}) -->
  <!-- Specular intensity: {params.specular_constant} -->
</a:bevel>"""

    def _generate_lightrig_positioning(self, params: SpecularLightingParameters, context: FilterContext) -> str:
        """Generate a:lightRig positioning based on light source parameters."""
        x, y, z = params.get_light_direction_vector()

        # Map to PowerPoint light rig types
        if abs(z) > 0.7:  # Primarily vertical
            rig_type = "threePt" if z > 0 else "balanced"
            direction = "t" if z > 0 else "b"
        elif abs(y) > abs(x):  # Primarily front/back
            rig_type = "soft" if y > 0 else "harsh"
            direction = "bl" if y > 0 else "tl"
        else:  # Primarily left/right
            rig_type = "warm" if x > 0 else "cool"
            direction = "br" if x > 0 else "tr"

        light_info = ""
        if params.light_source_type == "distant":
            light_info = f"azimuth {params.light_azimuth}, elevation {params.light_elevation}"
        elif params.light_source_type == "point":
            light_info = f"point position ({params.light_x}, {params.light_y}, {params.light_z})"
        elif params.light_source_type == "spot":
            light_info = f"spot cone angle {params.cone_angle}°"

        return f"""<a:lightRig rig="{rig_type}" dir="{direction}">
  <!-- Light rig positioning: {light_info} -->
  <!-- Optimized for specular reflection -->
</a:lightRig>"""

    def _generate_specular_highlights(self, params: SpecularLightingParameters, context: FilterContext) -> str:
        """Generate outer highlight shadow for specular reflection."""
        # Calculate highlight parameters based on specular properties
        if params.specular_exponent >= 64.0:
            blur_radius = int(unit(f"{abs(params.surface_scale) * 0.5}px").to_emu())
            highlight_intensity = 80000  # High intensity for shiny surfaces
            focus_comment = "sharp, focused highlight for high shininess"
        elif params.specular_exponent >= 16.0:
            blur_radius = int(unit(f"{abs(params.surface_scale) * 1.0}px").to_emu())
            highlight_intensity = 60000  # Medium intensity
            focus_comment = "medium highlight focus"
        else:
            blur_radius = int(unit(f"{abs(params.surface_scale) * 2.0}px").to_emu())
            highlight_intensity = 40000  # Lower intensity for matte surfaces
            focus_comment = "soft, diffused highlight for low shininess"

        # Calculate highlight distance
        highlight_distance = int(unit(f"{abs(params.surface_scale) * 1.5}px").to_emu())

        # Determine highlight direction based on light source
        if params.light_source_type == "distant":
            highlight_angle = int(params.light_azimuth * 60000)  # Convert to EMU angle
        else:
            highlight_angle = 5400000  # Default top-left highlight (90° in EMU)

        # Scale highlight opacity based on specular constant
        highlight_opacity = min(80000, int(params.specular_constant * 30000))

        # Convert lighting color for highlight tint
        highlight_color = self._convert_color_to_hex(params.lighting_color)

        return f"""<a:outerShdw blurRad="{blur_radius}" dist="{highlight_distance}" dir="{highlight_angle}"
                   rotWithShape="1" sx="100000" sy="100000" kx="0" ky="0" algn="ctr">
  <a:srgbClr val="{highlight_color}">
    <a:alpha val="{highlight_opacity}"/>
  </a:srgbClr>
  <!-- Specular highlight: {focus_comment} (exponent={params.specular_exponent}) -->
</a:outerShdw>"""

    def _apply_approximation_strategy(self, params: SpecularLightingParameters, context: FilterContext) -> FilterResult:
        """Apply approximation strategy for complex specular lighting."""
        try:
            drawingml = self._generate_approximation_specular_drawingml(params, context)

            return FilterResult(
                success=True,
                strategy=FilterStrategy.APPROXIMATION,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'approximation',
                    'surface_scale': params.surface_scale,
                    'specular_constant': params.specular_constant,
                    'specular_exponent': params.specular_exponent,
                    'lighting_color': params.lighting_color,
                    'light_source_type': params.light_source_type,
                    'complexity': params.get_complexity_score()
                }
            )

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.APPROXIMATION,
                drawingml="",
                error_message=f"Approximation specular lighting failed: {str(e)}"
            )

    def _generate_approximation_specular_drawingml(self, params: SpecularLightingParameters, context: FilterContext) -> str:
        """Generate approximated specular lighting using simpler effects."""
        effects = []

        # Simplified 3D effect with reduced parameters
        reduced_extrusion = min(
            int(unit(f"{min(abs(params.surface_scale), self.max_surface_scale) * 5}px").to_emu()),
            self.max_extrusion_emu
        )

        material = params.get_shininess_material()
        effects.append(f'<a:sp3d extrusionH="{reduced_extrusion}" prstMaterial="{material}"/>')

        # Basic highlight approximation using glow
        if params.lighting_color.lower() not in ["white", "#ffffff", "#fff"]:
            glow_color = self._convert_color_to_hex(params.lighting_color)
            glow_radius = int(unit(f"{params.specular_constant * 2}px").to_emu())
            effects.append(f'<a:glow rad="{glow_radius}"><a:srgbClr val="{glow_color}"/></a:glow>')

        effects.append(f'<!-- Specular lighting approximation: original surface_scale={params.surface_scale}, specular_exponent={params.specular_exponent} -->')

        return '\n'.join(effects)

    def _apply_emf_strategy(self, params: SpecularLightingParameters, context: FilterContext) -> FilterResult:
        """Apply EMF rasterization strategy for complex specular lighting."""
        try:
            # EMF rasterization placeholder
            return FilterResult(
                success=True,
                strategy=FilterStrategy.EMF_RASTERIZE,
                drawingml="<!-- EMF rasterization for complex specular lighting -->",
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'emf',
                    'surface_scale': params.surface_scale,
                    'specular_constant': params.specular_constant,
                    'specular_exponent': params.specular_exponent,
                    'lighting_color': params.lighting_color,
                    'light_source_type': params.light_source_type,
                    'complexity': params.get_complexity_score()
                }
            )

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.EMF_RASTERIZE,
                drawingml="",
                error_message=f"EMF specular lighting failed: {str(e)}"
            )

    def _convert_color_to_hex(self, color: str) -> str:
        """Convert color string to hex format for PowerPoint."""
        # Simple color name to hex conversion
        color_map = {
            'white': 'FFFFFF',
            'black': '000000',
            'red': 'FF0000',
            'green': '008000',
            'blue': '0000FF',
            'yellow': 'FFFF00',
            'cyan': '00FFFF',
            'magenta': 'FF00FF',
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

        # Default to white for unknown colors
        return 'FFFFFF'


def create_specular_lighting_processor(policy=None) -> SpecularLightingProcessor:
    """Factory function to create a SpecularLightingProcessor instance."""
    return SpecularLightingProcessor(policy=policy)