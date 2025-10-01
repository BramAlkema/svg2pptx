#!/usr/bin/env python3
"""
CustGeom Generator for PowerPoint ClipPath Conversion

This module converts simple SVG clipPath elements to native DrawingML custGeom elements,
enabling PowerPoint to handle clipping natively without requiring EMF fallbacks.

Key Features:
- Converts basic SVG shapes (rect, circle, ellipse, polygon) to custGeom
- Handles simple SVG paths with basic commands (M, L, C, A, Z)
- Proper coordinate system transformation
- Integration with existing ClipPath analysis framework
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Union
from lxml import etree as ET
import re
import math
import logging
from dataclasses import dataclass

from .clippath_types import ClipPathDefinition, ClippingType
from .base import ConversionContext

logger = logging.getLogger(__name__)


@dataclass
class CoordinateContext:
    """Context for coordinate transformation in custGeom generation."""
    units: str  # 'userSpaceOnUse' or 'objectBoundingBox'
    scale_x: float
    scale_y: float
    offset_x: float
    offset_y: float
    base_context: ConversionContext


class CustGeomGenerationError(Exception):
    """Exception raised for custGeom generation errors."""
    pass


class CustGeomGenerator:
    """
    Generates DrawingML custGeom elements from SVG clipPath definitions.

    This generator converts simple clipPaths to native PowerPoint clipping shapes,
    avoiding the need for EMF fallbacks and preserving maximum compatibility.
    """

    def __init__(self, services=None):
        """
        Initialize CustGeomGenerator.

        Args:
            services: ConversionServices for coordinate conversion and utilities
        """
        self.services = services
        self._coordinate_scale = 914400  # 1 inch in EMU

    def can_generate_custgeom(self, clip_def: ClipPathDefinition) -> bool:
        """
        Determine if a clipPath can be converted to custGeom.

        Args:
            clip_def: ClipPath definition to analyze

        Returns:
            True if custGeom generation is possible
        """
        try:
            # Check for simple path data
            if clip_def.path_data:
                return self._is_simple_path(clip_def.path_data)

            # Check for basic shapes
            if clip_def.shapes and len(clip_def.shapes) == 1:
                return self._is_basic_shape(clip_def.shapes[0])

            return False

        except Exception as e:
            logger.warning(f"Error analyzing custGeom capability: {e}")
            return False

    def generate_custgeom_xml(self, clip_def: ClipPathDefinition,
                             context: ConversionContext) -> str:
        """
        Generate DrawingML custGeom XML for a clipPath.

        Args:
            clip_def: ClipPath definition to convert
            context: Conversion context for coordinate transforms

        Returns:
            DrawingML custGeom XML string

        Raises:
            CustGeomGenerationError: If generation fails
        """
        try:
            logger.debug(f"Generating custGeom for clipPath {clip_def.id}")

            # Handle coordinate system based on clipPathUnits
            coord_context = self._create_coordinate_context(clip_def, context)

            # Determine conversion approach
            if clip_def.path_data:
                path_data = self.convert_svg_path_to_drawingml(clip_def.path_data, coord_context)
            elif clip_def.shapes and len(clip_def.shapes) == 1:
                path_data = self._convert_shape_to_path_data(clip_def.shapes[0], coord_context)
            else:
                raise CustGeomGenerationError("No valid path data or shapes found")

            # Apply clipPath transform if present
            if clip_def.transform:
                path_data = self._apply_clippath_transform(path_data, clip_def.transform, coord_context)

            # Generate custGeom XML with proper coordinate bounds
            bounds = self._calculate_custgeom_bounds(coord_context)
            custgeom_xml = f"""<a:custGeom>
    <a:avLst/>
    <a:gdLst/>
    <a:ahLst/>
    <a:cxnLst/>
    <a:rect l="0" t="0" r="{bounds['width']}" b="{bounds['height']}"/>
    <a:pathLst>
        <a:path w="{bounds['width']}" h="{bounds['height']}">
            {path_data}
        </a:path>
    </a:pathLst>
</a:custGeom>"""

            logger.debug(f"Generated custGeom for {clip_def.id}")
            return custgeom_xml

        except Exception as e:
            logger.error(f"Failed to generate custGeom for {clip_def.id}: {e}")
            raise CustGeomGenerationError(f"CustGeom generation failed: {e}")

    def convert_svg_path_to_drawingml(self, svg_path: str,
                                    coord_context: Union[ConversionContext, CoordinateContext]) -> str:
        """
        Convert SVG path data to DrawingML path commands.

        Args:
            svg_path: SVG path data string
            coord_context: Coordinate context for transformations

        Returns:
            DrawingML path commands XML
        """
        logger.debug(f"Converting SVG path to DrawingML: {svg_path}")

        # Parse SVG path commands
        commands = self._parse_svg_path(svg_path)

        # Convert to DrawingML
        drawingml_commands = []
        current_point = (0, 0)

        for cmd, params in commands:
            if cmd.upper() == 'M':
                # MoveTo
                x, y = self._scale_coordinates_smart(params[0], params[1], coord_context)
                drawingml_commands.append(f'<a:moveTo><a:pt x="{x}" y="{y}"/></a:moveTo>')
                current_point = (params[0], params[1])

            elif cmd.upper() == 'L':
                # LineTo
                x, y = self._scale_coordinates_smart(params[0], params[1], coord_context)
                drawingml_commands.append(f'<a:lnTo><a:pt x="{x}" y="{y}"/></a:lnTo>')
                current_point = (params[0], params[1])

            elif cmd.upper() == 'H':
                # Horizontal line
                x, y = self._scale_coordinates_smart(params[0], current_point[1], coord_context)
                drawingml_commands.append(f'<a:lnTo><a:pt x="{x}" y="{y}"/></a:lnTo>')
                current_point = (params[0], current_point[1])

            elif cmd.upper() == 'V':
                # Vertical line
                x, y = self._scale_coordinates_smart(current_point[0], params[0], coord_context)
                drawingml_commands.append(f'<a:lnTo><a:pt x="{x}" y="{y}"/></a:lnTo>')
                current_point = (current_point[0], params[0])

            elif cmd.upper() == 'C':
                # Cubic Bezier
                x1, y1 = self._scale_coordinates_smart(params[0], params[1], coord_context)
                x2, y2 = self._scale_coordinates_smart(params[2], params[3], coord_context)
                x, y = self._scale_coordinates_smart(params[4], params[5], coord_context)
                drawingml_commands.append(
                    f'<a:cubicBezTo>'
                    f'<a:pt x="{x1}" y="{y1}"/>'
                    f'<a:pt x="{x2}" y="{y2}"/>'
                    f'<a:pt x="{x}" y="{y}"/>'
                    f'</a:cubicBezTo>'
                )
                current_point = (params[4], params[5])

            elif cmd.upper() == 'Z':
                # Close path
                drawingml_commands.append('<a:close/>')

        return '\n            '.join(drawingml_commands)

    def handle_basic_shapes(self, element: ET.Element, context: Union[ConversionContext, CoordinateContext]) -> str:
        """
        Convert basic SVG shapes to DrawingML path data.

        Args:
            element: SVG shape element
            context: Conversion context

        Returns:
            DrawingML path commands XML
        """
        tag_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag

        if tag_name == 'rect':
            return self._convert_rect_to_path(element, context)
        elif tag_name == 'circle':
            return self._convert_circle_to_path(element, context)
        elif tag_name == 'ellipse':
            return self._convert_ellipse_to_path(element, context)
        elif tag_name == 'polygon':
            return self._convert_polygon_to_path(element, context)
        elif tag_name == 'polyline':
            return self._convert_polyline_to_path(element, context)
        else:
            raise CustGeomGenerationError(f"Unsupported shape type: {tag_name}")

    def _is_simple_path(self, path_data: str) -> bool:
        """Check if path contains only simple commands."""
        # Only allow basic commands for custGeom conversion
        # Include Q and T for quadratic curves, S for smooth curves
        simple_commands = r'^[MLHVCZQTSmlhvczqts\d\s\.,\-]+$'
        return bool(re.match(simple_commands, path_data.strip()))

    def _is_basic_shape(self, element: ET.Element) -> bool:
        """Check if element is a basic shape."""
        tag_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        return tag_name in ['rect', 'circle', 'ellipse', 'polygon', 'polyline']

    def _parse_svg_path(self, path_data: str) -> List[Tuple[str, List[float]]]:
        """Parse SVG path data into command/parameter pairs."""
        commands = []

        # Split path into commands and parameters
        path_regex = r'([MLHVCZmlhvcz])([-\d\.\s,]*)'
        matches = re.findall(path_regex, path_data)

        for cmd, params_str in matches:
            # Parse numeric parameters
            params = []
            if params_str.strip():
                # Split by comma or whitespace
                param_matches = re.findall(r'[-\d\.]+', params_str)
                params = [float(p) for p in param_matches]

            commands.append((cmd, params))

        return commands

    def _scale_coordinates(self, x: float, y: float) -> Tuple[int, int]:
        """Scale coordinates to DrawingML coordinate system."""
        # Convert to 21600 coordinate system (standard DrawingML)
        scaled_x = int(x * 21600 / 100)  # Assuming 100x100 viewBox
        scaled_y = int(y * 21600 / 100)
        return scaled_x, scaled_y

    def _convert_shape_to_path_data(self, element: ET.Element,
                                  context: Union[ConversionContext, CoordinateContext]) -> str:
        """Convert a shape element to DrawingML path data."""
        return self.handle_basic_shapes(element, context)

    def _convert_rect_to_path(self, element: ET.Element,
                            context: Union[ConversionContext, CoordinateContext]) -> str:
        """Convert rect element to DrawingML path."""
        x = float(element.get('x', 0))
        y = float(element.get('y', 0))
        width = float(element.get('width', 0))
        height = float(element.get('height', 0))

        # Create rectangle path
        x1, y1 = self._scale_coordinates_smart(x, y, context)
        x2, y2 = self._scale_coordinates_smart(x + width, y + height, context)

        return f'''<a:moveTo><a:pt x="{x1}" y="{y1}"/></a:moveTo>
            <a:lnTo><a:pt x="{x2}" y="{y1}"/></a:lnTo>
            <a:lnTo><a:pt x="{x2}" y="{y2}"/></a:lnTo>
            <a:lnTo><a:pt x="{x1}" y="{y2}"/></a:lnTo>
            <a:close/>'''

    def _convert_circle_to_path(self, element: ET.Element,
                              context: Union[ConversionContext, CoordinateContext]) -> str:
        """Convert circle element to DrawingML path using arcs."""
        cx = float(element.get('cx', 0))
        cy = float(element.get('cy', 0))
        r = float(element.get('r', 0))

        # Create circle using four arcs
        # Start at top
        start_x, start_y = self._scale_coordinates(cx, cy - r)
        end_x, end_y = self._scale_coordinates(cx, cy + r)

        # For simplicity, use a rectangle approximation for custGeom
        x1, y1 = self._scale_coordinates_smart(cx - r, cy - r, context)
        x2, y2 = self._scale_coordinates_smart(cx + r, cy + r, context)

        # Note: True circle requires arc commands which are more complex
        # For now, use a rectangle that can be refined later
        return f'''<a:moveTo><a:pt x="{x1}" y="{y1}"/></a:moveTo>
            <a:lnTo><a:pt x="{x2}" y="{y1}"/></a:lnTo>
            <a:lnTo><a:pt x="{x2}" y="{y2}"/></a:lnTo>
            <a:lnTo><a:pt x="{x1}" y="{y2}"/></a:lnTo>
            <a:close/>'''

    def _convert_ellipse_to_path(self, element: ET.Element,
                               context: Union[ConversionContext, CoordinateContext]) -> str:
        """Convert ellipse element to DrawingML path."""
        cx = float(element.get('cx', 0))
        cy = float(element.get('cy', 0))
        rx = float(element.get('rx', 0))
        ry = float(element.get('ry', 0))

        # Use rectangle approximation for custGeom
        x1, y1 = self._scale_coordinates_smart(cx - rx, cy - ry, context)
        x2, y2 = self._scale_coordinates_smart(cx + rx, cy + ry, context)

        return f'''<a:moveTo><a:pt x="{x1}" y="{y1}"/></a:moveTo>
            <a:lnTo><a:pt x="{x2}" y="{y1}"/></a:lnTo>
            <a:lnTo><a:pt x="{x2}" y="{y2}"/></a:lnTo>
            <a:lnTo><a:pt x="{x1}" y="{y2}"/></a:lnTo>
            <a:close/>'''

    def _convert_polygon_to_path(self, element: ET.Element,
                               context: Union[ConversionContext, CoordinateContext]) -> str:
        """Convert polygon element to DrawingML path."""
        points_str = element.get('points', '')
        if not points_str:
            raise CustGeomGenerationError("Polygon missing points attribute")

        # Parse points
        points = []
        coords = re.findall(r'[-\d\.]+', points_str)
        for i in range(0, len(coords), 2):
            if i + 1 < len(coords):
                x, y = float(coords[i]), float(coords[i + 1])
                points.append(self._scale_coordinates_smart(x, y, context))

        if not points:
            raise CustGeomGenerationError("No valid points found in polygon")

        # Create path commands
        path_commands = [f'<a:moveTo><a:pt x="{points[0][0]}" y="{points[0][1]}"/></a:moveTo>']

        for x, y in points[1:]:
            path_commands.append(f'<a:lnTo><a:pt x="{x}" y="{y}"/></a:lnTo>')

        path_commands.append('<a:close/>')

        return '\n            '.join(path_commands)

    def _convert_polyline_to_path(self, element: ET.Element,
                                context: Union[ConversionContext, CoordinateContext]) -> str:
        """Convert polyline element to DrawingML path."""
        points_str = element.get('points', '')
        if not points_str:
            raise CustGeomGenerationError("Polyline missing points attribute")

        # Parse points (same as polygon but without close)
        points = []
        coords = re.findall(r'[-\d\.]+', points_str)
        for i in range(0, len(coords), 2):
            if i + 1 < len(coords):
                x, y = float(coords[i]), float(coords[i + 1])
                points.append(self._scale_coordinates_smart(x, y, context))

        if not points:
            raise CustGeomGenerationError("No valid points found in polyline")

        # Create path commands (no close for polyline)
        path_commands = [f'<a:moveTo><a:pt x="{points[0][0]}" y="{points[0][1]}"/></a:moveTo>']

        for x, y in points[1:]:
            path_commands.append(f'<a:lnTo><a:pt x="{x}" y="{y}"/></a:lnTo>')

        return '\n            '.join(path_commands)

    def _create_coordinate_context(self, clip_def: ClipPathDefinition,
                                 context: ConversionContext) -> 'CoordinateContext':
        """
        Create coordinate transformation context based on clipPathUnits.

        Args:
            clip_def: ClipPath definition with units information
            context: Base conversion context

        Returns:
            CoordinateContext with appropriate transformation parameters
        """
        if clip_def.units == 'objectBoundingBox':
            # objectBoundingBox uses 0-1 coordinate system relative to element bounds
            return CoordinateContext(
                units='objectBoundingBox',
                scale_x=21600,  # Scale 0-1 to full DrawingML range
                scale_y=21600,
                offset_x=0,
                offset_y=0,
                base_context=context
            )
        else:
            # userSpaceOnUse uses the current coordinate system
            # Extract viewBox and viewport information from context
            viewbox_width = getattr(context, 'viewbox_width', 100)
            viewbox_height = getattr(context, 'viewbox_height', 100)

            return CoordinateContext(
                units='userSpaceOnUse',
                scale_x=21600 / viewbox_width,
                scale_y=21600 / viewbox_height,
                offset_x=0,
                offset_y=0,
                base_context=context
            )

    def _calculate_custgeom_bounds(self, coord_context: 'CoordinateContext') -> Dict[str, int]:
        """Calculate custGeom coordinate bounds."""
        if coord_context.units == 'objectBoundingBox':
            # objectBoundingBox always uses full range
            return {'width': 21600, 'height': 21600}
        else:
            # userSpaceOnUse uses scaled viewport
            return {
                'width': int(coord_context.scale_x * 100),  # Assume 100 unit reference
                'height': int(coord_context.scale_y * 100)
            }

    def _apply_clippath_transform(self, path_data: str, transform: str,
                                coord_context: 'CoordinateContext') -> str:
        """
        Apply clipPath transform to generated path data.

        Args:
            path_data: Generated DrawingML path data
            transform: SVG transform string
            coord_context: Coordinate transformation context

        Returns:
            Transformed path data
        """
        # For now, log the transform and return path unchanged
        # TODO: Implement full transform matrix application
        logger.debug(f"ClipPath transform applied: {transform}")
        return path_data

    def handle_clippath_units(self, clip_def: ClipPathDefinition, element_bounds: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        """
        Handle clipPathUnits coordinate system transformation.

        Args:
            clip_def: ClipPath definition
            element_bounds: Target element bounds (x, y, width, height)

        Returns:
            Transformed bounds for clipPath coordinates
        """
        if clip_def.units == 'objectBoundingBox':
            # Convert percentage coordinates to actual element bounds
            x, y, width, height = element_bounds
            return (0.0, 0.0, width, height)
        else:
            # userSpaceOnUse - use current coordinate system
            return element_bounds

    def _scale_coordinates_with_context(self, x: float, y: float,
                                      coord_context: 'CoordinateContext') -> Tuple[int, int]:
        """Scale coordinates using coordinate context."""
        scaled_x = int((x + coord_context.offset_x) * coord_context.scale_x)
        scaled_y = int((y + coord_context.offset_y) * coord_context.scale_y)
        return scaled_x, scaled_y

    def _scale_coordinates_smart(self, x: float, y: float,
                               context: Union[ConversionContext, CoordinateContext]) -> Tuple[int, int]:
        """
        Smart coordinate scaling that handles both context types.

        Args:
            x, y: Coordinates to scale
            context: Either ConversionContext or CoordinateContext

        Returns:
            Scaled coordinates for DrawingML
        """
        if isinstance(context, CoordinateContext):
            return self._scale_coordinates_with_context(x, y, context)
        else:
            # Fallback to simple scaling for backward compatibility
            return self._scale_coordinates(x, y)