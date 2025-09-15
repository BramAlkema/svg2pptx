#!/usr/bin/env python3
"""
feDiffuseLighting Vector-First Filter Implementation.

This module implements vector-first conversion for SVG feDiffuseLighting filter effects,
converting diffuse lighting operations to PowerPoint using 3D effects like a:sp3d,
a:bevel, a:lightRig, and a:innerShdw rather than rasterization.

Key Features:
- Vector-first approach using PowerPoint 3D DrawingML elements
- a:sp3d configuration for 3D shape simulation
- a:bevel effects mapping from light direction and intensity
- a:lightRig positioning based on light source parameters
- a:innerShdw effects for depth enhancement
- Maintains vector precision in PowerPoint output

Architecture Integration:
- Inherits from the new Filter base class
- Uses standardized BaseConverter tools (UnitConverter, ColorParser, etc.)
- Integrates with FilterRegistry for automatic registration
- Supports filter chaining and complex operations

Task 2.2 Implementation:
- Subtask 2.2.3: feDiffuseLighting parser with lighting model extraction
- Subtask 2.2.4: a:sp3d configuration system for 3D shape simulation
- Subtask 2.2.5: a:bevel effects mapping from light direction and intensity
- Subtask 2.2.6: a:lightRig positioning based on light source parameters
- Subtask 2.2.7: Inner shadow effects (a:innerShdw) for depth enhancement
- Subtask 2.2.8: Verify diffuse lighting creates realistic 3D appearance using vector effects
"""

import logging
import math
from typing import Dict, Any, Optional, Tuple
from lxml import etree
from dataclasses import dataclass

from ..core.base import Filter, FilterContext, FilterResult

logger = logging.getLogger(__name__)


@dataclass
class DiffuseLightingParameters:
    """Parameters for feDiffuseLighting operations."""
    surface_scale: float  # Surface elevation scaling
    diffuse_constant: float  # Material diffuse reflection constant
    lighting_color: str  # Light color (default white)
    input_source: str  # Input filter result
    result_name: Optional[str] = None  # Output identifier

    # Light source parameters
    light_source_type: Optional[str] = None  # distant, point, spot
    light_azimuth: Optional[float] = None  # For distant light
    light_elevation: Optional[float] = None  # For distant light
    light_x: Optional[float] = None  # For point/spot light
    light_y: Optional[float] = None  # For point/spot light
    light_z: Optional[float] = None  # For point/spot light
    light_points_at_x: Optional[float] = None  # For spot light
    light_points_at_y: Optional[float] = None  # For spot light
    light_points_at_z: Optional[float] = None  # For spot light
    cone_angle: Optional[float] = None  # For spot light
    spot_exponent: Optional[float] = None  # For spot light


class DiffuseLightingFilter(Filter):
    """
    Vector-first feDiffuseLighting filter implementation.

    This filter implements SVG diffuse lighting operations using PowerPoint
    3D DrawingML elements rather than rasterization, providing better
    scalability and visual quality.

    Vector-First Strategy:
    1. Parse diffuse lighting parameters (surface scale, diffuse constant, lighting color)
    2. Extract light source information (distant, point, or spot light)
    3. Generate a:sp3d configuration for 3D shape simulation
    4. Map light direction to a:bevel effects for directional lighting
    5. Configure a:lightRig positioning based on light source parameters
    6. Add a:innerShdw effects for depth enhancement
    7. Combine all effects for realistic 3D lighting appearance

    PowerPoint Mapping:
    - surface scale → a:sp3d extrusion depth
    - light direction → a:bevel orientation and intensity
    - light source → a:lightRig positioning
    - diffuse constant → effect intensity scaling
    - Final result → Combined 3D DrawingML effects
    """

    def __init__(self):
        """Initialize the diffuse lighting filter."""
        super().__init__("diffuse_lighting")

        # Vector-first strategy for 3D lighting effects
        self.strategy = "vector_first"
        self.complexity_threshold = 3.0  # Below this, use full vector approach

    def can_apply(self, element: etree.Element, context: FilterContext) -> bool:
        """
        Check if this filter can be applied to feDiffuseLighting elements.

        Args:
            element: SVG element to check
            context: Filter processing context

        Returns:
            True if element is feDiffuseLighting, False otherwise
        """
        if element is None:
            return False

        # Handle both namespaced and non-namespaced elements
        tag_name = element.tag
        if tag_name.startswith('{'):
            # Remove namespace
            tag_name = tag_name.split('}')[-1]

        return tag_name == 'feDiffuseLighting'

    def validate_parameters(self, element: etree.Element, context: FilterContext) -> bool:
        """
        Validate feDiffuseLighting element parameters.

        Args:
            element: feDiffuseLighting element to validate
            context: Filter processing context

        Returns:
            True if parameters are valid, False otherwise
        """
        try:
            params = self._parse_diffuse_lighting_parameters(element)

            # Validate surface scale (can be negative for flipped surface)
            if not isinstance(params.surface_scale, (int, float)):
                logger.warning(f"Invalid surface scale type: {type(params.surface_scale)}")
                return False

            # Validate diffuse constant (should be non-negative)
            if params.diffuse_constant < 0:
                logger.warning(f"Invalid negative diffuse constant: {params.diffuse_constant}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating diffuse lighting parameters: {e}")
            return False

    def apply(self, element: etree.Element, context: FilterContext) -> FilterResult:
        """
        Apply vector-first diffuse lighting transformation.

        Args:
            element: feDiffuseLighting element to process
            context: Filter processing context with standardized tools

        Returns:
            FilterResult with PowerPoint 3D DrawingML or error information
        """
        try:
            # Parse diffuse lighting parameters (Subtask 2.2.3)
            params = self._parse_diffuse_lighting_parameters(element)

            # Calculate complexity score for strategy decision
            complexity = self._calculate_complexity(params)

            # For Task 2.2, use vector-first approach with 3D effects
            if complexity < self.complexity_threshold:
                return self._apply_vector_first(params, context)
            else:
                # Even for complex cases, still prefer vector-first in Task 2.2
                logger.info(f"Complex diffuse lighting (score={complexity}), still using vector-first approach")
                return self._apply_vector_first(params, context)

        except Exception as e:
            logger.error(f"Error applying diffuse lighting filter: {e}")
            return FilterResult(
                success=False,
                error_message=f"Diffuse lighting filter failed: {str(e)}",
                metadata={'filter_type': 'diffuse_lighting', 'error': str(e)}
            )

    def _parse_diffuse_lighting_parameters(self, element: etree.Element) -> DiffuseLightingParameters:
        """
        Parse feDiffuseLighting element parameters (Subtask 2.2.3).

        Args:
            element: feDiffuseLighting SVG element

        Returns:
            DiffuseLightingParameters with parsed values
        """
        # Parse basic lighting attributes
        surface_scale = self._parse_float_attr(element, 'surfaceScale', 1.0)
        diffuse_constant = self._parse_float_attr(element, 'diffuseConstant', 1.0)
        lighting_color = element.get('lighting-color', '#FFFFFF')

        # Parse input and result
        input_source = element.get('in', 'SourceGraphic')
        result_name = element.get('result')

        # Create basic parameters
        params = DiffuseLightingParameters(
            surface_scale=surface_scale,
            diffuse_constant=diffuse_constant,
            lighting_color=lighting_color,
            input_source=input_source,
            result_name=result_name
        )

        # Parse light source child element
        self._parse_light_source(element, params)

        return params

    def _parse_light_source(self, element: etree.Element, params: DiffuseLightingParameters):
        """
        Parse light source child elements and update parameters.

        Args:
            element: feDiffuseLighting element
            params: Parameters object to update with light source info
        """
        for child in element:
            tag_name = child.tag
            if tag_name.startswith('{'):
                tag_name = tag_name.split('}')[-1]

            if tag_name == 'feDistantLight':
                params.light_source_type = "distant"
                params.light_azimuth = self._parse_float_attr(child, 'azimuth', 0.0)
                params.light_elevation = self._parse_float_attr(child, 'elevation', 45.0)

            elif tag_name == 'fePointLight':
                params.light_source_type = "point"
                params.light_x = self._parse_float_attr(child, 'x', 0.0)
                params.light_y = self._parse_float_attr(child, 'y', 0.0)
                params.light_z = self._parse_float_attr(child, 'z', 0.0)

            elif tag_name == 'feSpotLight':
                params.light_source_type = "spot"
                params.light_x = self._parse_float_attr(child, 'x', 0.0)
                params.light_y = self._parse_float_attr(child, 'y', 0.0)
                params.light_z = self._parse_float_attr(child, 'z', 0.0)
                params.light_points_at_x = self._parse_float_attr(child, 'pointsAtX', 0.0)
                params.light_points_at_y = self._parse_float_attr(child, 'pointsAtY', 0.0)
                params.light_points_at_z = self._parse_float_attr(child, 'pointsAtZ', 0.0)
                params.cone_angle = self._parse_float_attr(child, 'limitingConeAngle', 90.0)
                params.spot_exponent = self._parse_float_attr(child, 'specularExponent', 1.0)

        # Default to distant light if no light source specified
        if params.light_source_type is None:
            params.light_source_type = "distant"
            params.light_azimuth = 0.0
            params.light_elevation = 45.0

    def _parse_float_attr(self, element: etree.Element, attr_name: str, default: float) -> float:
        """
        Parse float attribute with default fallback.

        Args:
            element: XML element
            attr_name: Attribute name
            default: Default value

        Returns:
            Parsed float value or default
        """
        try:
            attr_value = element.get(attr_name)
            if attr_value is not None:
                return float(attr_value)
            return default
        except (ValueError, TypeError):
            logger.warning(f"Invalid float value for {attr_name}: '{attr_value}', using default {default}")
            return default

    def _calculate_complexity(self, params: DiffuseLightingParameters) -> float:
        """
        Calculate complexity score for diffuse lighting operation.

        Args:
            params: Diffuse lighting parameters

        Returns:
            Complexity score (0.0 = simple, higher = more complex)
        """
        complexity = 0.5  # Base complexity

        # Add complexity based on surface scale
        if abs(params.surface_scale) > 20.0:
            complexity += 2.0
        elif abs(params.surface_scale) > 10.0:
            complexity += 1.5
        elif abs(params.surface_scale) > 5.0:
            complexity += 1.0

        # Add complexity based on diffuse constant
        if params.diffuse_constant > 3.0:
            complexity += 0.5
        elif params.diffuse_constant > 1.5:
            complexity += 0.3

        # Add complexity for light source type
        if params.light_source_type == "spot":
            complexity += 1.0
            if params.cone_angle and params.cone_angle < 30.0:
                complexity += 0.5  # Narrow cone is more complex
        elif params.light_source_type == "point":
            complexity += 0.5

        # Add complexity for colored lighting
        if params.lighting_color != "#FFFFFF":
            complexity += 0.3

        return complexity

    def _apply_vector_first(self, params: DiffuseLightingParameters, context: FilterContext) -> FilterResult:
        """
        Apply vector-first diffuse lighting transformation using PowerPoint 3D effects.

        This method implements the core vector-first strategy for Task 2.2:
        - Subtask 2.2.4: a:sp3d configuration system for 3D shape simulation
        - Subtask 2.2.5: a:bevel effects mapping from light direction and intensity
        - Subtask 2.2.6: a:lightRig positioning based on light source parameters
        - Subtask 2.2.7: Inner shadow effects (a:innerShdw) for depth enhancement

        Args:
            params: Parsed diffuse lighting parameters
            context: Filter processing context with standardized tools

        Returns:
            FilterResult with vector-first PowerPoint 3D DrawingML
        """
        try:
            # Generate complete 3D lighting DrawingML
            drawingml = self._generate_3d_lighting_drawingml(params, context)

            return FilterResult(
                success=True,
                drawingml=drawingml,
                metadata={
                    'filter_type': 'diffuse_lighting',
                    'strategy': 'vector_first',
                    'surface_scale': params.surface_scale,
                    'diffuse_constant': params.diffuse_constant,
                    'lighting_color': params.lighting_color,
                    'light_source_type': params.light_source_type,
                    'light_azimuth': params.light_azimuth,
                    'light_elevation': params.light_elevation,
                    'complexity': self._calculate_complexity(params)
                }
            )

        except Exception as e:
            logger.error(f"Vector-first diffuse lighting failed: {e}")
            return FilterResult(
                success=False,
                error_message=f"Vector-first diffuse lighting failed: {str(e)}",
                metadata={'filter_type': 'diffuse_lighting', 'strategy': 'vector_first', 'error': str(e)}
            )

    def _generate_3d_lighting_drawingml(self, params: DiffuseLightingParameters, context: FilterContext) -> str:
        """
        Generate complete PowerPoint 3D lighting DrawingML.

        Combines all 3D effects for realistic diffuse lighting:
        - a:sp3d for 3D shape simulation
        - a:bevel for directional lighting effects
        - a:lightRig for light source positioning
        - a:innerShdw for depth enhancement

        Args:
            params: Diffuse lighting parameters
            context: Filter processing context

        Returns:
            Complete PowerPoint DrawingML string
        """
        # Generate individual effect components
        sp3d_config = self._generate_sp3d_configuration(params, context)
        bevel_effects = self._generate_bevel_effects(params, context)
        lightrig_positioning = self._generate_lightrig_positioning(params, context)
        inner_shadow = self._generate_inner_shadow_effects(params, context)

        # Combine all effects
        return f'''<!-- feDiffuseLighting Vector-First 3D Effects -->
<a:effectLst>
  {sp3d_config}
  {bevel_effects}
  {lightrig_positioning}
  {inner_shadow}
</a:effectLst>
<!-- Result: {params.result_name or "diffuse_lit"} -->'''

    def _generate_sp3d_configuration(self, params: DiffuseLightingParameters, context: FilterContext) -> str:
        """
        Generate a:sp3d configuration system for 3D shape simulation (Subtask 2.2.4).

        Maps surface scale to 3D extrusion and material properties.

        Args:
            params: Diffuse lighting parameters
            context: Filter processing context

        Returns:
            a:sp3d DrawingML configuration
        """
        # Convert surface scale to EMU units for extrusion
        extrusion_height = context.unit_converter.to_emu(f"{abs(params.surface_scale)}px")

        # Calculate contour width based on surface scale
        contour_width = context.unit_converter.to_emu(f"{abs(params.surface_scale) * 0.5}px")

        # Determine material properties based on diffuse constant
        if params.diffuse_constant >= 2.0:
            material = "matte"
        elif params.diffuse_constant >= 1.0:
            material = "softEdge"
        else:
            material = "flat"

        return f'''<!-- a:sp3d configuration for 3D shape simulation (input: {params.input_source}) -->
  <a:sp3d extrusionH="{int(extrusion_height)}" contourW="{int(contour_width)}" prstMaterial="{material}">
    <a:bevelT w="25400" h="12700"/>
    <a:lightRig rig="threePt" dir="t">
      <a:rot lat="0" lon="0" rev="1200000"/>
    </a:lightRig>
  </a:sp3d>'''

    def _generate_bevel_effects(self, params: DiffuseLightingParameters, context: FilterContext) -> str:
        """
        Generate a:bevel effects mapping from light direction and intensity (Subtask 2.2.5).

        Maps light source direction and diffuse constant to bevel effects.

        Args:
            params: Diffuse lighting parameters
            context: Filter processing context

        Returns:
            a:bevel DrawingML effects
        """
        # Calculate bevel dimensions based on diffuse constant
        bevel_width = context.unit_converter.to_emu(f"{params.diffuse_constant * 2.0}px")
        bevel_height = context.unit_converter.to_emu(f"{params.diffuse_constant * 1.5}px")

        # Determine bevel type based on light direction
        if params.light_source_type == "distant" and params.light_elevation is not None:
            if params.light_elevation >= 75.0:
                bevel_type = "bevelT"  # Top bevel for high elevation
                comment = f"Top bevel for high elevation {params.light_elevation}°"
            elif params.light_elevation <= 15.0:
                bevel_type = "bevelB"  # Bottom bevel for low elevation
                comment = f"Bottom bevel for low elevation {params.light_elevation}°"
            else:
                # Determine side based on azimuth
                if params.light_azimuth is not None:
                    if 45 <= params.light_azimuth <= 135:
                        bevel_type = "bevelR"  # Right side
                        comment = f"Right bevel for azimuth {params.light_azimuth}°"
                    elif 225 <= params.light_azimuth <= 315:
                        bevel_type = "bevelL"  # Left side
                        comment = f"Left bevel for azimuth {params.light_azimuth}°"
                    else:
                        bevel_type = "bevelT"  # Default to top
                        comment = f"Default top bevel for azimuth {params.light_azimuth}°"
                else:
                    bevel_type = "bevelT"
                    comment = "Default top bevel"
        else:
            bevel_type = "bevelT"
            comment = f"{params.light_source_type or 'default'} light bevel"

        return f'''<!-- a:bevel effects mapping from light direction and intensity -->
  <a:{bevel_type} w="{int(bevel_width)}" h="{int(bevel_height)}"/>
  <!-- {comment} -->'''

    def _generate_lightrig_positioning(self, params: DiffuseLightingParameters, context: FilterContext) -> str:
        """
        Generate a:lightRig positioning based on light source parameters (Subtask 2.2.6).

        Maps light source type and direction to PowerPoint light rig configuration.

        Args:
            params: Diffuse lighting parameters
            context: Filter processing context

        Returns:
            a:lightRig DrawingML positioning
        """
        if params.light_source_type == "distant":
            # Map azimuth and elevation to PowerPoint light rig
            if params.light_elevation and params.light_elevation >= 75.0:
                rig_type = "threePt"
                direction = "t"  # Top
                comment = f"Top lighting for elevation {params.light_elevation}°"
            elif params.light_azimuth is not None:
                if 315 <= params.light_azimuth or params.light_azimuth <= 45:
                    rig_type = "balanced"
                    direction = "tl"  # Top-left/front
                    comment = f"Front lighting for azimuth {params.light_azimuth}°"
                elif 45 < params.light_azimuth <= 135:
                    rig_type = "soft"
                    direction = "r"  # Right
                    comment = f"Right lighting for azimuth {params.light_azimuth}°"
                elif 135 < params.light_azimuth <= 225:
                    rig_type = "harsh"
                    direction = "b"  # Back
                    comment = f"Back lighting for azimuth {params.light_azimuth}°"
                else:
                    rig_type = "soft"
                    direction = "l"  # Left
                    comment = f"Left lighting for azimuth {params.light_azimuth}°"
            else:
                rig_type = "threePt"
                direction = "tl"
                comment = "Default front-top lighting"

        elif params.light_source_type == "point":
            # Point light uses contrasting rig for more dramatic effect
            rig_type = "contrasting"
            direction = "tl"
            comment = f"Point light at ({params.light_x}, {params.light_y}, {params.light_z})"

        elif params.light_source_type == "spot":
            # Spot light uses harsh rig for focused effect
            rig_type = "harsh"
            direction = "t"
            comment = f"Spot light cone angle {params.cone_angle}°"

        else:
            # Default lighting
            rig_type = "threePt"
            direction = "tl"
            comment = "Default three-point lighting"

        return f'''<!-- a:lightRig positioning based on light source parameters -->
  <a:lightRig rig="{rig_type}" dir="{direction}">
    <a:rot lat="0" lon="0" rev="1200000"/>
  </a:lightRig>
  <!-- {comment} -->'''

    def _generate_inner_shadow_effects(self, params: DiffuseLightingParameters, context: FilterContext) -> str:
        """
        Generate inner shadow effects for depth enhancement (Subtask 2.2.7).

        Creates a:innerShdw effects that enhance the 3D lighting appearance.

        Args:
            params: Diffuse lighting parameters
            context: Filter processing context

        Returns:
            a:innerShdw DrawingML for depth enhancement
        """
        # Calculate shadow parameters based on surface scale
        blur_radius = context.unit_converter.to_emu(f"{params.surface_scale * 2.0}px")
        shadow_distance = context.unit_converter.to_emu(f"{params.surface_scale * 1.0}px")

        # Determine shadow direction opposite to light source
        if params.light_source_type == "distant" and params.light_azimuth is not None:
            # Shadow direction is opposite to light azimuth
            shadow_direction = (params.light_azimuth + 180.0) % 360.0
            shadow_dir_emu = int(shadow_direction * 60000)  # Convert to EMU angle
        else:
            shadow_dir_emu = 13500000  # Default bottom-right shadow

        # Calculate shadow opacity based on diffuse constant
        shadow_opacity = min(50000, int(params.diffuse_constant * 20000))  # 20-50% opacity

        # Parse lighting color for shadow tint
        parsed_color = context.color_parser.parse(params.lighting_color)
        if parsed_color.startswith('#'):
            shadow_color = parsed_color[1:]  # Remove # for DrawingML
        else:
            shadow_color = "000000"  # Default to black

        return f'''<!-- Inner shadow effects for depth enhancement -->
  <a:innerShdw blurRad="{int(blur_radius)}" dist="{int(shadow_distance)}"
               dir="{shadow_dir_emu}" rotWithShape="1" sx="100000" sy="100000"
               kx="0" ky="0" algn="ctr">
    <a:srgbClr val="{shadow_color}">
      <a:alpha val="{shadow_opacity}"/>
    </a:srgbClr>
  </a:innerShdw>
  <!-- Depth enhancement for surface scale {params.surface_scale} -->'''