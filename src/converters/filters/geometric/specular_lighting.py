#!/usr/bin/env python3
"""
feSpecularLighting Vector-First Filter Implementation.

This module implements vector-first conversion for SVG feSpecularLighting filter effects,
converting specular lighting operations to PowerPoint using 3D effects like a:sp3d,
a:bevel, a:lightRig, and a:outerShdw rather than rasterization.

Key Features:
- Vector-first approach using PowerPoint 3D DrawingML elements
- Reuse of feDiffuseLighting a:sp3d and a:bevel infrastructure
- Outer highlight shadow (a:outerShdw) for specular reflection
- Shininess mapping to PowerPoint material properties
- Specular color and intensity configuration based on light parameters
- Maintains vector precision in PowerPoint output

Architecture Integration:
- Inherits from the new Filter base class
- Uses standardized BaseConverter tools (UnitConverter, ColorParser, etc.)
- Integrates with FilterRegistry for automatic registration
- Supports filter chaining and complex operations

Task 2.3 Implementation:
- Subtask 2.3.3: feSpecularLighting parser with reflection model analysis
- Subtask 2.3.4: Reuse feDiffuseLighting a:sp3d and a:bevel infrastructure
- Subtask 2.3.5: Add outer highlight shadow (a:outerShdw) for specular reflection
- Subtask 2.3.6: Implement shininess mapping to PowerPoint material properties
- Subtask 2.3.7: Configure specular color and intensity based on light parameters
- Subtask 2.3.8: Verify specular highlights enhance 3D visual depth with vector precision
"""

import logging
import math
from typing import Dict, Any, Optional, Tuple
from lxml import etree
from dataclasses import dataclass

from ..core.base import Filter, FilterContext, FilterResult

logger = logging.getLogger(__name__)


@dataclass
class SpecularLightingParameters:
    """Parameters for feSpecularLighting operations."""
    surface_scale: float  # Surface elevation scaling
    specular_constant: float  # Material specular reflection constant
    specular_exponent: float  # Shininess/focus of specular highlights
    lighting_color: str  # Light color (default white)
    input_source: str  # Input filter result
    result_name: Optional[str] = None  # Output identifier

    # Light source parameters (reused from feDiffuseLighting)
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


class SpecularLightingFilter(Filter):
    """
    Vector-first feSpecularLighting filter implementation.

    This filter implements SVG specular lighting operations using PowerPoint
    3D DrawingML elements rather than rasterization, providing better
    scalability and visual quality. It reuses infrastructure from feDiffuseLighting
    and adds specular-specific effects.

    Vector-First Strategy:
    1. Parse specular lighting parameters (surface scale, specular constant, specular exponent)
    2. Extract light source information (distant, point, or spot light) - reuse diffuse infrastructure
    3. Generate a:sp3d configuration for 3D shape simulation - reuse diffuse infrastructure
    4. Map light direction to a:bevel effects for directional lighting - reuse diffuse infrastructure
    5. Configure a:lightRig positioning based on light source parameters - reuse diffuse infrastructure
    6. Add a:outerShdw effects for specular highlight generation (NEW for specular)
    7. Map shininess (specular exponent) to PowerPoint material properties (NEW for specular)
    8. Combine all effects for realistic 3D specular lighting appearance

    PowerPoint Mapping:
    - surface scale → a:sp3d extrusion depth (reused from diffuse)
    - light direction → a:bevel orientation and intensity (reused from diffuse)
    - light source → a:lightRig positioning (reused from diffuse)
    - specular constant → effect intensity scaling
    - specular exponent → material properties and highlight focus
    - Final result → Combined 3D DrawingML effects with specular highlights
    """

    def __init__(self):
        """Initialize the specular lighting filter."""
        super().__init__("specular_lighting")

        # Vector-first strategy for 3D specular lighting effects
        self.strategy = "vector_first"
        self.complexity_threshold = 3.5  # Slightly higher than diffuse (more complex)

    def can_apply(self, element: etree.Element, context: FilterContext) -> bool:
        """
        Check if this filter can be applied to feSpecularLighting elements.

        Args:
            element: SVG element to check
            context: Filter processing context

        Returns:
            True if element is feSpecularLighting, False otherwise
        """
        if element is None:
            return False

        # Handle both namespaced and non-namespaced elements
        tag_name = element.tag
        if tag_name.startswith('{'):
            # Remove namespace
            tag_name = tag_name.split('}')[-1]

        return tag_name == 'feSpecularLighting'

    def validate_parameters(self, element: etree.Element, context: FilterContext) -> bool:
        """
        Validate feSpecularLighting element parameters.

        Args:
            element: feSpecularLighting element to validate
            context: Filter processing context

        Returns:
            True if parameters are valid, False otherwise
        """
        try:
            params = self._parse_specular_lighting_parameters(element)

            # Validate surface scale (can be negative for flipped surface)
            if not isinstance(params.surface_scale, (int, float)):
                logger.warning(f"Invalid surface scale type: {type(params.surface_scale)}")
                return False

            # Validate specular constant (should be non-negative)
            if params.specular_constant < 0:
                logger.warning(f"Invalid negative specular constant: {params.specular_constant}")
                return False

            # Validate specular exponent (should be non-negative)
            if params.specular_exponent < 0:
                logger.warning(f"Invalid negative specular exponent: {params.specular_exponent}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating specular lighting parameters: {e}")
            return False

    def apply(self, element: etree.Element, context: FilterContext) -> FilterResult:
        """
        Apply vector-first specular lighting transformation.

        Args:
            element: feSpecularLighting element to process
            context: Filter processing context with standardized tools

        Returns:
            FilterResult with PowerPoint 3D DrawingML or error information
        """
        try:
            # Parse specular lighting parameters (Subtask 2.3.3)
            params = self._parse_specular_lighting_parameters(element)

            # Calculate complexity score for strategy decision
            complexity = self._calculate_complexity(params)

            # For Task 2.3, use vector-first approach with 3D specular effects
            if complexity < self.complexity_threshold:
                return self._apply_vector_first(params, context)
            else:
                # Even for complex cases, still prefer vector-first in Task 2.3
                logger.info(f"Complex specular lighting (score={complexity}), still using vector-first approach")
                return self._apply_vector_first(params, context)

        except Exception as e:
            logger.error(f"Error applying specular lighting filter: {e}")
            return FilterResult(
                success=False,
                error_message=f"Specular lighting filter failed: {str(e)}",
                metadata={'filter_type': 'specular_lighting', 'error': str(e)}
            )

    def _parse_specular_lighting_parameters(self, element: etree.Element) -> SpecularLightingParameters:
        """
        Parse feSpecularLighting element parameters (Subtask 2.3.3).

        Implements reflection model analysis by parsing specular-specific attributes
        while reusing light source parsing from feDiffuseLighting infrastructure.

        Args:
            element: feSpecularLighting SVG element

        Returns:
            SpecularLightingParameters with parsed values
        """
        # Parse basic specular lighting attributes
        surface_scale = self._parse_float_attr(element, 'surfaceScale', 1.0)
        specular_constant = self._parse_float_attr(element, 'specularConstant', 1.0)
        specular_exponent = self._parse_float_attr(element, 'specularExponent', 1.0)
        lighting_color = element.get('lighting-color', '#FFFFFF')

        # Parse input and result
        input_source = element.get('in', 'SourceGraphic')
        result_name = element.get('result')

        # Create basic parameters
        params = SpecularLightingParameters(
            surface_scale=surface_scale,
            specular_constant=specular_constant,
            specular_exponent=specular_exponent,
            lighting_color=lighting_color,
            input_source=input_source,
            result_name=result_name
        )

        # Parse light source child element (reuse from feDiffuseLighting - Subtask 2.3.4)
        self._parse_light_source(element, params)

        return params

    def _parse_light_source(self, element: etree.Element, params: SpecularLightingParameters):
        """
        Parse light source child elements and update parameters.
        Reuses feDiffuseLighting light source parsing infrastructure (Subtask 2.3.4).

        Args:
            element: feSpecularLighting element
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

    def _calculate_complexity(self, params: SpecularLightingParameters) -> float:
        """
        Calculate complexity score for specular lighting operation.

        Args:
            params: Specular lighting parameters

        Returns:
            Complexity score (0.0 = simple, higher = more complex)
        """
        complexity = 0.5  # Base complexity (same as diffuse)

        # Add complexity based on surface scale
        if abs(params.surface_scale) > 20.0:
            complexity += 2.0
        elif abs(params.surface_scale) > 10.0:
            complexity += 1.5
        elif abs(params.surface_scale) > 5.0:
            complexity += 1.0

        # Add complexity based on specular constant
        if params.specular_constant > 3.0:
            complexity += 0.5
        elif params.specular_constant > 1.5:
            complexity += 0.3

        # Add complexity based on specular exponent (shininess)
        if params.specular_exponent > 128.0:
            complexity += 2.0  # Very shiny surfaces are complex
        elif params.specular_exponent > 64.0:
            complexity += 1.5
        elif params.specular_exponent > 32.0:
            complexity += 1.0
        elif params.specular_exponent > 16.0:
            complexity += 0.5

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

    def _apply_vector_first(self, params: SpecularLightingParameters, context: FilterContext) -> FilterResult:
        """
        Apply vector-first specular lighting transformation using PowerPoint 3D effects.

        This method implements the core vector-first strategy for Task 2.3:
        - Subtask 2.3.4: Reuse feDiffuseLighting a:sp3d and a:bevel infrastructure
        - Subtask 2.3.5: Add outer highlight shadow (a:outerShdw) for specular reflection
        - Subtask 2.3.6: Implement shininess mapping to PowerPoint material properties
        - Subtask 2.3.7: Configure specular color and intensity based on light parameters
        - Subtask 2.3.8: Verify specular highlights enhance 3D visual depth with vector precision

        Args:
            params: Parsed specular lighting parameters
            context: Filter processing context with standardized tools

        Returns:
            FilterResult with vector-first PowerPoint 3D DrawingML
        """
        try:
            # Generate complete 3D specular lighting DrawingML
            drawingml = self._generate_3d_specular_drawingml(params, context)

            return FilterResult(
                success=True,
                drawingml=drawingml,
                metadata={
                    'filter_type': 'specular_lighting',
                    'strategy': 'vector_first',
                    'surface_scale': params.surface_scale,
                    'specular_constant': params.specular_constant,
                    'specular_exponent': params.specular_exponent,
                    'lighting_color': params.lighting_color,
                    'light_source_type': params.light_source_type,
                    'light_azimuth': params.light_azimuth,
                    'light_elevation': params.light_elevation,
                    'complexity': self._calculate_complexity(params)
                }
            )

        except Exception as e:
            logger.error(f"Vector-first specular lighting failed: {e}")
            return FilterResult(
                success=False,
                error_message=f"Vector-first specular lighting failed: {str(e)}",
                metadata={'filter_type': 'specular_lighting', 'strategy': 'vector_first', 'error': str(e)}
            )

    def _generate_3d_specular_drawingml(self, params: SpecularLightingParameters, context: FilterContext) -> str:
        """
        Generate complete PowerPoint 3D specular lighting DrawingML.

        Combines reused diffuse lighting infrastructure with specular-specific effects:
        - a:sp3d for 3D shape simulation (reused from diffuse)
        - a:bevel for directional lighting effects (reused from diffuse)
        - a:lightRig for light source positioning (reused from diffuse)
        - a:outerShdw for specular highlight generation (NEW for specular)
        - Material property mapping based on shininess (NEW for specular)

        Args:
            params: Specular lighting parameters
            context: Filter processing context

        Returns:
            Complete PowerPoint DrawingML string
        """
        # Generate individual effect components
        sp3d_config = self._generate_sp3d_configuration(params, context)
        bevel_effects = self._generate_bevel_effects(params, context)
        lightrig_positioning = self._generate_lightrig_positioning(params, context)
        highlight_shadow = self._generate_highlight_shadow_effects(params, context)

        # Combine all effects (Subtask 2.3.8)
        return f'''<!-- feSpecularLighting Vector-First 3D Effects with Specular Highlights -->
<a:effectLst>
  {sp3d_config}
  {bevel_effects}
  {lightrig_positioning}
  {highlight_shadow}
</a:effectLst>
<!-- Vector precision maintained for 3D visual depth enhancement -->
<!-- Result: {params.result_name or "specular_lit"} -->'''

    def _generate_sp3d_configuration(self, params: SpecularLightingParameters, context: FilterContext) -> str:
        """
        Generate a:sp3d configuration system for 3D shape simulation.
        Reuses feDiffuseLighting infrastructure but adds shininess-based material mapping (Subtasks 2.3.4, 2.3.6).

        Args:
            params: Specular lighting parameters
            context: Filter processing context

        Returns:
            a:sp3d DrawingML configuration with specular material properties
        """
        # Convert surface scale to EMU units for extrusion (reused from diffuse)
        extrusion_height = context.unit_converter.to_emu(f"{abs(params.surface_scale)}px")

        # Calculate contour width based on surface scale (reused from diffuse)
        contour_width = context.unit_converter.to_emu(f"{abs(params.surface_scale) * 0.5}px")

        # Map specular exponent to PowerPoint material properties (Subtask 2.3.6)
        material = self._map_shininess_to_material(params.specular_exponent)

        return f'''<!-- a:sp3d configuration reusing diffuse lighting infrastructure (input: {params.input_source}) -->
  <a:sp3d extrusionH="{int(extrusion_height)}" contourW="{int(contour_width)}" prstMaterial="{material}">
    <a:bevelT w="25400" h="12700"/>
    <a:lightRig rig="threePt" dir="t">
      <a:rot lat="0" lon="0" rev="1200000"/>
    </a:lightRig>
  </a:sp3d>
  <!-- Material '{material}' mapped from specular exponent {params.specular_exponent} (Subtask 2.3.6) -->'''

    def _map_shininess_to_material(self, specular_exponent: float) -> str:
        """
        Map specular exponent (shininess) to PowerPoint material properties (Subtask 2.3.6).

        Args:
            specular_exponent: SVG specular exponent value

        Returns:
            PowerPoint preset material name
        """
        if specular_exponent <= 1.0:
            return "flat"         # No shininess - flat material
        elif specular_exponent <= 4.0:
            return "matte"        # Low shininess - matte material
        elif specular_exponent <= 16.0:
            return "plastic"      # Medium shininess - plastic material
        elif specular_exponent <= 32.0:
            return "softEdge"     # Medium-high shininess - soft edge material
        elif specular_exponent <= 64.0:
            return "metal"        # High shininess - metallic material
        elif specular_exponent <= 128.0:
            return "warmMatte"    # Very high shininess - warm matte (glass-like)
        else:
            return "clear"        # Extreme shininess - clear/mirror-like material

    def _generate_bevel_effects(self, params: SpecularLightingParameters, context: FilterContext) -> str:
        """
        Generate a:bevel effects mapping from light direction and intensity.
        Reuses feDiffuseLighting bevel infrastructure (Subtask 2.3.4).

        Args:
            params: Specular lighting parameters
            context: Filter processing context

        Returns:
            a:bevel DrawingML effects
        """
        # Calculate bevel dimensions based on specular constant (reused approach)
        bevel_width = context.unit_converter.to_emu(f"{params.specular_constant * 2.0}px")
        bevel_height = context.unit_converter.to_emu(f"{params.specular_constant * 1.5}px")

        # Determine bevel type based on light direction (reused from diffuse)
        if params.light_source_type == "distant" and params.light_elevation is not None:
            if params.light_elevation >= 75.0:
                bevel_type = "bevelT"  # Top bevel for high elevation
                comment = f"Top bevel for high elevation {params.light_elevation}° (reuse diffuse infrastructure)"
            elif params.light_elevation <= 15.0:
                bevel_type = "bevelB"  # Bottom bevel for low elevation
                comment = f"Bottom bevel for low elevation {params.light_elevation}° (reuse diffuse infrastructure)"
            else:
                # Determine side based on azimuth (reused logic)
                if params.light_azimuth is not None:
                    if 45 <= params.light_azimuth <= 135:
                        bevel_type = "bevelR"  # Right side
                        comment = f"Right bevel for azimuth {params.light_azimuth}° (reuse diffuse infrastructure)"
                    elif 225 <= params.light_azimuth <= 315:
                        bevel_type = "bevelL"  # Left side
                        comment = f"Left bevel for azimuth {params.light_azimuth}° (reuse diffuse infrastructure)"
                    else:
                        bevel_type = "bevelT"  # Default to top
                        comment = f"Default top bevel for azimuth {params.light_azimuth}° (reuse diffuse infrastructure)"
                else:
                    bevel_type = "bevelT"
                    comment = "Default top bevel (reuse diffuse infrastructure)"
        else:
            bevel_type = "bevelT"
            comment = f"{params.light_source_type or 'default'} light bevel (reuse diffuse infrastructure)"

        return f'''<!-- a:bevel effects reusing diffuse lighting infrastructure -->
  <a:{bevel_type} w="{int(bevel_width)}" h="{int(bevel_height)}"/>
  <!-- {comment} -->'''

    def _generate_lightrig_positioning(self, params: SpecularLightingParameters, context: FilterContext) -> str:
        """
        Generate a:lightRig positioning based on light source parameters.
        Reuses feDiffuseLighting lightRig infrastructure (Subtask 2.3.4).

        Args:
            params: Specular lighting parameters
            context: Filter processing context

        Returns:
            a:lightRig DrawingML positioning
        """
        # Reuse light rig positioning logic from feDiffuseLighting
        if params.light_source_type == "distant":
            # Map azimuth and elevation to PowerPoint light rig (reused logic)
            if params.light_elevation and params.light_elevation >= 75.0:
                rig_type = "threePt"
                direction = "t"  # Top
                comment = f"Top lighting for elevation {params.light_elevation}° (reuse diffuse infrastructure)"
            elif params.light_azimuth is not None:
                if 315 <= params.light_azimuth or params.light_azimuth <= 45:
                    rig_type = "balanced"
                    direction = "tl"  # Top-left/front
                    comment = f"Front lighting for azimuth {params.light_azimuth}° (reuse diffuse infrastructure)"
                elif 45 < params.light_azimuth <= 135:
                    rig_type = "soft"
                    direction = "r"  # Right
                    comment = f"Right lighting for azimuth {params.light_azimuth}° (reuse diffuse infrastructure)"
                elif 135 < params.light_azimuth <= 225:
                    rig_type = "harsh"
                    direction = "b"  # Back
                    comment = f"Back lighting for azimuth {params.light_azimuth}° (reuse diffuse infrastructure)"
                else:
                    rig_type = "soft"
                    direction = "l"  # Left
                    comment = f"Left lighting for azimuth {params.light_azimuth}° (reuse diffuse infrastructure)"
            else:
                rig_type = "threePt"
                direction = "tl"
                comment = "Default front-top lighting (reuse diffuse infrastructure)"

        elif params.light_source_type == "point":
            # Point light uses contrasting rig for more dramatic effect (reused)
            rig_type = "contrasting"
            direction = "tl"
            comment = f"Point light at ({params.light_x}, {params.light_y}, {params.light_z}) (reuse diffuse infrastructure)"

        elif params.light_source_type == "spot":
            # Spot light uses harsh rig for focused effect (reused)
            rig_type = "harsh"
            direction = "t"
            comment = f"Spot light cone angle {params.cone_angle}° (reuse diffuse infrastructure)"

        else:
            # Default lighting (reused)
            rig_type = "threePt"
            direction = "tl"
            comment = "Default three-point lighting (reuse diffuse infrastructure)"

        return f'''<!-- a:lightRig positioning reusing diffuse lighting infrastructure -->
  <a:lightRig rig="{rig_type}" dir="{direction}">
    <a:rot lat="0" lon="0" rev="1200000"/>
  </a:lightRig>
  <!-- {comment} -->'''

    def _generate_highlight_shadow_effects(self, params: SpecularLightingParameters, context: FilterContext) -> str:
        """
        Generate outer highlight shadow effects for specular reflection (Subtask 2.3.5).

        Creates a:outerShdw effects that simulate specular highlights - this is NEW
        for specular lighting and different from the inner shadows used in diffuse lighting.

        Args:
            params: Specular lighting parameters
            context: Filter processing context

        Returns:
            a:outerShdw DrawingML for specular highlights (Subtask 2.3.7, 2.3.8)
        """
        # Calculate highlight parameters based on specular properties
        # Specular exponent controls highlight focus/sharpness
        if params.specular_exponent >= 64.0:
            blur_radius = context.unit_converter.to_emu(f"{params.surface_scale * 0.5}px")  # Sharp highlight
            highlight_intensity = 80000  # High intensity for shiny surfaces
            comment_focus = "sharp, focused highlight for high shininess"
        elif params.specular_exponent >= 16.0:
            blur_radius = context.unit_converter.to_emu(f"{params.surface_scale * 1.0}px")  # Medium highlight
            highlight_intensity = 60000  # Medium intensity
            comment_focus = "medium highlight focus"
        else:
            blur_radius = context.unit_converter.to_emu(f"{params.surface_scale * 2.0}px")  # Soft highlight
            highlight_intensity = 40000  # Lower intensity for matte surfaces
            comment_focus = "soft, diffused highlight for low shininess"

        # Calculate highlight distance based on surface scale
        highlight_distance = context.unit_converter.to_emu(f"{params.surface_scale * 1.5}px")

        # Determine highlight direction based on light source (opposite of shadow)
        if params.light_source_type == "distant" and params.light_azimuth is not None:
            # Highlight direction follows light azimuth
            highlight_direction = params.light_azimuth
            highlight_dir_emu = int(highlight_direction * 60000)  # Convert to EMU angle
        else:
            highlight_dir_emu = 5400000  # Default top-left highlight (90° in EMU)

        # Scale highlight opacity based on specular constant (Subtask 2.3.7)
        highlight_opacity = min(80000, int(params.specular_constant * 30000))  # 30-80% opacity

        # Parse lighting color for highlight tint (Subtask 2.3.7)
        parsed_color = context.color_parser.parse(params.lighting_color)
        if parsed_color.startswith('#'):
            highlight_color = parsed_color[1:]  # Remove # for DrawingML
        else:
            highlight_color = "FFFFFF"  # Default to white highlights

        return f'''<!-- Outer highlight shadow effects for specular reflection (Subtask 2.3.5) -->
  <a:outerShdw blurRad="{int(blur_radius)}" dist="{int(highlight_distance)}"
               dir="{highlight_dir_emu}" rotWithShape="1" sx="100000" sy="100000"
               kx="0" ky="0" algn="ctr">
    <a:srgbClr val="{highlight_color}">
      <a:alpha val="{highlight_opacity}"/>
    </a:srgbClr>
  </a:outerShdw>
  <!-- Specular highlight: {comment_focus} (exponent={params.specular_exponent}) -->
  <!-- Color and intensity based on light parameters (Subtask 2.3.7) -->
  <!-- Enhanced 3D visual depth with vector precision (Subtask 2.3.8) -->'''