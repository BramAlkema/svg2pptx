#!/usr/bin/env python3
"""
Diffuse Lighting Filter Processor for SVG Filter Effects

Implements SVG feDiffuseLighting filter with 3D lighting effects,
using PowerPoint native sp3d, bevel, and lightRig effects for
high-fidelity 3D appearance simulation.

This processor creates realistic 3D lighting effects by combining:
- a:sp3d for 3D shape simulation
- a:bevel for directional surface effects
- a:lightRig for lighting positioning
- a:innerShdw for depth perception
"""

from typing import Dict, List, Optional, Tuple, Union, Any
from enum import Enum
from dataclasses import dataclass
from lxml import etree as ET
import math

from .base import FilterProcessor, FilterContext, FilterResult, FilterStrategy
from ..units import unit
from ..policy.targets import PolicyDecision


class DiffuseLightingException(Exception):
    """Exception raised during diffuse lighting processing."""
    pass


class DiffuseLightingValidationError(DiffuseLightingException, ValueError):
    """Exception raised when diffuse lighting parameters are invalid."""
    pass


@dataclass
class DiffuseLightingParameters:
    """Parameters for diffuse lighting processing."""
    surface_scale: float = 1.0
    diffuse_constant: float = 1.0
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
        self.surface_scale = max(0.0, min(self.surface_scale, 50.0))

        # Clamp diffuse constant to reasonable range
        self.diffuse_constant = max(0.0, min(self.diffuse_constant, 10.0))

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
        complexity = 0.0

        # Base complexity from surface parameters
        complexity += min(self.surface_scale / 10.0, 2.0)
        complexity += min(self.diffuse_constant / 5.0, 1.5)

        # Light source type complexity
        if self.light_source_type == "point":
            complexity += 0.5
        elif self.light_source_type == "spot":
            complexity += 1.0

        # Complex angles add complexity
        if self.light_elevation > 80.0 or self.light_elevation < 10.0:
            complexity += 0.3

        # Colored lighting adds complexity
        if self.lighting_color.lower() not in ["white", "#ffffff", "#fff"]:
            complexity += 0.2

        return complexity

    def is_effective(self) -> bool:
        """Check if diffuse lighting has any visible effect."""
        return (self.surface_scale > 0.01 and
                self.diffuse_constant > 0.01)

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

    def get_powerpoint_light_direction(self) -> str:
        """Map light direction to PowerPoint lightRig direction."""
        x, y, z = self.get_light_direction_vector()

        # Determine primary direction based on strongest component
        abs_x, abs_y, abs_z = abs(x), abs(y), abs(z)

        if abs_z > 0.7:  # Primarily vertical
            return "t" if z > 0 else "b"  # top or bottom
        elif abs_y > abs_x:  # Primarily front/back
            return "bl" if y > 0 else "tl"  # back-left or top-left
        else:  # Primarily left/right
            return "br" if x > 0 else "tr"  # bottom-right or top-right


class DiffuseLightingProcessor(FilterProcessor):
    """Processor for SVG feDiffuseLighting filter effects."""

    def __init__(self, policy=None):
        super().__init__(filter_type='feDiffuseLighting', policy=policy)
        self.max_surface_scale = 10.0  # Practical limit for PowerPoint 3D effects
        self.max_extrusion_emu = 1270000  # ~50px max extrusion

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        """Check if this processor can handle the given element."""
        if element is None or element.tag != 'feDiffuseLighting':
            return False
        return self._validate_parameters(element, context)

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        """Apply diffuse lighting processing to the element."""
        try:
            # Validate parameters first
            if not self._validate_parameters(element, context):
                raise DiffuseLightingException("Invalid diffuse lighting parameters")

            # Parse diffuse lighting parameters
            params = self._parse_diffuse_lighting_parameters(element)

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
                error_message=f"Diffuse lighting processing failed: {str(e)}"
            )

    def _validate_parameters(self, element: ET.Element, context: FilterContext) -> bool:
        """Validate diffuse lighting parameters."""
        if element is None or context is None:
            return False
        try:
            self._parse_diffuse_lighting_parameters(element)
            return True
        except (DiffuseLightingException, ValueError, TypeError):
            return False

    def _parse_diffuse_lighting_parameters(self, element: ET.Element) -> DiffuseLightingParameters:
        """Parse diffuse lighting parameters from SVG element."""
        # Parse basic lighting parameters
        surface_scale = float(element.get('surfaceScale', '1.0'))
        diffuse_constant = float(element.get('diffuseConstant', '1.0'))
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

        return DiffuseLightingParameters(
            surface_scale=surface_scale,
            diffuse_constant=diffuse_constant,
            lighting_color=lighting_color,
            light_source_type=light_source_type,
            input_source=input_source,
            result_name=result_name,
            **light_params
        )

    def _get_strategy(self, params: DiffuseLightingParameters, context: FilterContext) -> FilterStrategy:
        """Determine the best strategy for diffuse lighting processing."""
        if self.policy:
            decision = self.policy.decide_diffuse_lighting_strategy(params, context)
            return decision.strategy

        # Default strategy logic
        complexity = params.get_complexity_score()

        if self._can_use_native_3d(params):
            return FilterStrategy.NATIVE
        elif complexity < 4.0:
            return FilterStrategy.APPROXIMATION
        else:
            return FilterStrategy.EMF_RASTERIZE

    def _can_use_native_3d(self, params: DiffuseLightingParameters) -> bool:
        """Check if parameters can be handled with native PowerPoint 3D effects."""
        # Check if lighting is effective
        if not params.is_effective():
            return True  # No-op case

        # Check surface scale constraints
        if params.surface_scale > self.max_surface_scale:
            return False

        # PowerPoint 3D effects work well with standard parameters
        if params.diffuse_constant > 5.0:
            return False  # Too intense

        return True

    def _apply_native_strategy(self, params: DiffuseLightingParameters, context: FilterContext) -> FilterResult:
        """Apply native PowerPoint 3D lighting effects."""
        try:
            drawingml = ""

            if not params.is_effective():
                drawingml = "<!-- No visible diffuse lighting effect -->"
            else:
                drawingml = self._generate_3d_lighting_drawingml(params, context)

            return FilterResult(
                success=True,
                strategy=FilterStrategy.NATIVE,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'native_3d',
                    'surface_scale': params.surface_scale,
                    'diffuse_constant': params.diffuse_constant,
                    'lighting_color': params.lighting_color,
                    'light_source_type': params.light_source_type,
                    'complexity': params.get_complexity_score()
                }
            )

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.NATIVE,
                drawingml="",
                error_message=f"Native diffuse lighting failed: {str(e)}"
            )

    def _generate_3d_lighting_drawingml(self, params: DiffuseLightingParameters, context: FilterContext) -> str:
        """Generate comprehensive 3D lighting effects using PowerPoint components."""
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

        # Add inner shadow for depth perception
        shadow_effect = self._generate_inner_shadow_depth(params, context)
        effects.append(shadow_effect)

        return '\n'.join(effects)

    def _generate_sp3d_configuration(self, params: DiffuseLightingParameters, context: FilterContext) -> str:
        """Generate a:sp3d configuration for 3D shape simulation."""
        # Calculate extrusion height based on surface scale
        extrusion_height = min(
            int(unit(f"{params.surface_scale * 10}px").to_emu()),
            self.max_extrusion_emu
        )

        # Calculate contour width based on diffuse constant
        contour_width = int(unit(f"{params.diffuse_constant * 2}px").to_emu())

        # Determine material properties
        material = "matte" if params.diffuse_constant > 2.0 else "plastic"

        return f"""<a:sp3d extrusionH="{extrusion_height}" contourW="{contour_width}" prstMaterial="{material}">
  <!-- 3D shape simulation: surface_scale={params.surface_scale}, diffuse_constant={params.diffuse_constant} -->
</a:sp3d>"""

    def _generate_bevel_effects(self, params: DiffuseLightingParameters, context: FilterContext) -> str:
        """Generate a:bevel effects mapping from light direction and intensity."""
        light_dir = params.get_powerpoint_light_direction()

        # Map light direction to bevel type
        bevel_mapping = {
            "t": "bevelT",  # top lighting -> top bevel
            "b": "bevelB",  # bottom lighting -> bottom bevel
            "tl": "bevelT", # top-left lighting -> top bevel
            "tr": "bevelT", # top-right lighting -> top bevel
            "bl": "bevelB", # bottom-left lighting -> bottom bevel
            "br": "bevelB"  # bottom-right lighting -> bottom bevel
        }

        bevel_type = bevel_mapping.get(light_dir, "bevelT")

        # Calculate bevel dimensions based on diffuse intensity
        bevel_width = int(unit(f"{params.diffuse_constant * 3}px").to_emu())
        bevel_height = int(unit(f"{params.diffuse_constant * 2}px").to_emu())

        return f"""<a:bevel {bevel_type}="1" w="{bevel_width}" h="{bevel_height}">
  <!-- Bevel effects: light_direction={light_dir}, azimuth={params.light_azimuth}, elevation={params.light_elevation} -->
</a:bevel>"""

    def _generate_lightrig_positioning(self, params: DiffuseLightingParameters, context: FilterContext) -> str:
        """Generate a:lightRig positioning based on light source parameters."""
        light_dir = params.get_powerpoint_light_direction()

        # Map to PowerPoint light rig types
        rig_mapping = {
            "t": "threePt",     # top lighting
            "b": "balanced",    # bottom lighting
            "tl": "soft",       # top-left lighting
            "tr": "harsh",      # top-right lighting
            "bl": "cool",       # bottom-left lighting
            "br": "warm"        # bottom-right lighting
        }

        rig_type = rig_mapping.get(light_dir, "threePt")

        light_info = ""
        if params.light_source_type == "distant":
            light_info = f"azimuth {params.light_azimuth}, elevation {params.light_elevation}"
        elif params.light_source_type == "point":
            light_info = f"point position ({params.light_x}, {params.light_y}, {params.light_z})"
        elif params.light_source_type == "spot":
            light_info = f"spot at ({params.light_x}, {params.light_y}, {params.light_z}) -> ({params.light_points_at_x}, {params.light_points_at_y}, {params.light_points_at_z})"

        return f"""<a:lightRig rig="{rig_type}" dir="{light_dir}">
  <!-- Light rig positioning: {light_info} -->
</a:lightRig>"""

    def _generate_inner_shadow_depth(self, params: DiffuseLightingParameters, context: FilterContext) -> str:
        """Generate inner shadow for depth perception."""
        # Calculate shadow parameters based on lighting
        x, y, z = params.get_light_direction_vector()

        # Shadow offset opposite to light direction
        shadow_offset_x = int(unit(f"{-x * params.surface_scale * 2}px").to_emu())
        shadow_offset_y = int(unit(f"{-y * params.surface_scale * 2}px").to_emu())

        # Shadow blur based on diffuse constant
        blur_radius = int(unit(f"{params.diffuse_constant * 1.5}px").to_emu())

        # Shadow opacity based on lighting intensity
        shadow_alpha = int(min(params.diffuse_constant * 15000, 50000))  # Max 50% opacity

        return f"""<a:innerShdw blurRad="{blur_radius}" dist="0" dir="0" sx="100000" sy="100000" kx="{shadow_offset_x}" ky="{shadow_offset_y}">
  <a:srgbClr val="000000">
    <a:alpha val="{shadow_alpha}"/>
  </a:srgbClr>
  <!-- Inner shadow for depth: light_direction=({x:.2f}, {y:.2f}, {z:.2f}) -->
</a:innerShdw>"""

    def _apply_approximation_strategy(self, params: DiffuseLightingParameters, context: FilterContext) -> FilterResult:
        """Apply approximation strategy for complex diffuse lighting."""
        try:
            drawingml = self._generate_approximation_lighting_drawingml(params, context)

            return FilterResult(
                success=True,
                strategy=FilterStrategy.APPROXIMATION,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'approximation',
                    'surface_scale': params.surface_scale,
                    'diffuse_constant': params.diffuse_constant,
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
                error_message=f"Approximation diffuse lighting failed: {str(e)}"
            )

    def _generate_approximation_lighting_drawingml(self, params: DiffuseLightingParameters, context: FilterContext) -> str:
        """Generate approximated diffuse lighting using simpler effects."""
        effects = []

        # Simplified 3D effect
        reduced_extrusion = min(
            int(unit(f"{min(params.surface_scale, self.max_surface_scale) * 5}px").to_emu()),
            self.max_extrusion_emu
        )

        effects.append(f'<a:sp3d extrusionH="{reduced_extrusion}" prstMaterial="plastic"/>')

        # Basic lighting approximation using glow
        if params.lighting_color.lower() not in ["white", "#ffffff", "#fff"]:
            glow_color = self._convert_color_to_hex(params.lighting_color)
            glow_radius = int(unit(f"{params.diffuse_constant * 3}px").to_emu())
            effects.append(f'<a:glow rad="{glow_radius}"><a:srgbClr val="{glow_color}"/></a:glow>')

        effects.append(f'<!-- Diffuse lighting approximation: original surface_scale={params.surface_scale}, diffuse_constant={params.diffuse_constant} -->')

        return '\n'.join(effects)

    def _apply_emf_strategy(self, params: DiffuseLightingParameters, context: FilterContext) -> FilterResult:
        """Apply EMF rasterization strategy for complex diffuse lighting."""
        try:
            # EMF rasterization placeholder
            return FilterResult(
                success=True,
                strategy=FilterStrategy.EMF_RASTERIZE,
                drawingml="<!-- EMF rasterization for complex diffuse lighting -->",
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'emf',
                    'surface_scale': params.surface_scale,
                    'diffuse_constant': params.diffuse_constant,
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
                error_message=f"EMF diffuse lighting failed: {str(e)}"
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


def create_diffuse_lighting_processor(policy=None) -> DiffuseLightingProcessor:
    """Factory function to create a DiffuseLightingProcessor instance."""
    return DiffuseLightingProcessor(policy=policy)