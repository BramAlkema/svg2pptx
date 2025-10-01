#!/usr/bin/env python3
"""
GradientService for handling SVG gradient definitions and conversions.

Provides gradient resolution, caching, and conversion to DrawingML.
"""

from typing import Dict, Optional, List, Any
from lxml import etree as ET
import logging

# Mesh gradient engine will be imported lazily to avoid circular imports

logger = logging.getLogger(__name__)


class GradientService:
    """Service for managing SVG gradient definitions and conversions."""

    def __init__(self):
        self._gradient_cache: Dict[str, ET.Element] = {}
        self._conversion_cache: Dict[str, str] = {}
        self._mesh_engine = None  # Lazy initialization

    def register_gradient(self, gradient_id: str, gradient_element: ET.Element) -> None:
        """Register a gradient definition for later resolution."""
        self._gradient_cache[gradient_id] = gradient_element

    def get_gradient_content(self, gradient_id: str, context: Any = None) -> Optional[str]:
        """
        Get gradient content by ID.

        Args:
            gradient_id: The ID of the gradient to resolve
            context: Optional conversion context

        Returns:
            Gradient content as string, or None if not found
        """
        # Remove url() wrapper if present
        clean_id = gradient_id.replace('url(#', '').replace(')', '').replace('#', '')

        # Check cache first
        if clean_id in self._conversion_cache:
            return self._conversion_cache[clean_id]

        # Look for gradient in cache
        if clean_id in self._gradient_cache:
            gradient_element = self._gradient_cache[clean_id]

            # Simple gradient conversion to DrawingML-like content
            gradient_type = gradient_element.tag.split('}')[-1]  # Remove namespace

            if gradient_type == 'linearGradient':
                content = self._convert_linear_gradient(gradient_element)
            elif gradient_type == 'radialGradient':
                content = self._convert_radial_gradient(gradient_element)
            elif gradient_type == 'meshgradient':
                content = self._convert_mesh_gradient(gradient_element)
            else:
                content = f"<!-- Unsupported gradient type: {gradient_type} -->"

            # Cache the result
            self._conversion_cache[clean_id] = content
            return content

        logger.warning(f"Gradient not found: {gradient_id}")
        return None

    def _convert_linear_gradient(self, gradient_element: ET.Element) -> str:
        """Convert linear gradient to basic DrawingML representation."""
        stops = self._extract_gradient_stops(gradient_element)

        # Simple linear gradient representation
        return f"<a:gradFill><a:gsLst>{stops}</a:gsLst><a:lin ang=\"0\" scaled=\"0\"/></a:gradFill>"

    def _convert_radial_gradient(self, gradient_element: ET.Element) -> str:
        """Convert radial gradient to basic DrawingML representation."""
        stops = self._extract_gradient_stops(gradient_element)

        # Simple radial gradient representation
        return f"<a:gradFill><a:gsLst>{stops}</a:gsLst><a:path path=\"circle\"/></a:gradFill>"

    def _convert_mesh_gradient(self, gradient_element: ET.Element) -> str:
        """Convert mesh gradient to DrawingML using the mesh gradient engine."""
        # Lazy import and initialization to avoid circular imports
        if self._mesh_engine is None:
            from ..converters.gradients.mesh_engine import MeshGradientEngine
            self._mesh_engine = MeshGradientEngine()

        return self._mesh_engine.convert_mesh_gradient(gradient_element)

    def _extract_gradient_stops(self, gradient_element: ET.Element) -> str:
        """Extract gradient stops and convert to DrawingML format."""
        stops = []

        for stop in gradient_element.findall('.//{http://www.w3.org/2000/svg}stop'):
            offset = stop.get('offset', '0')
            # Convert percentage to position (0-100000)
            if offset.endswith('%'):
                pos = int(float(offset[:-1]) * 1000)
            else:
                pos = int(float(offset) * 100000)

            # Try to get color from style attribute first, then fallback to stop-color attribute
            color = self._extract_stop_color(stop)

            # Convert color to hex format for DrawingML
            color_hex = self._convert_color_to_hex(color)
            stops.append(f'<a:gs pos="{pos}"><a:srgbClr val="{color_hex}"/></a:gs>')

        return ''.join(stops)

    def _extract_stop_color(self, stop_element: ET.Element) -> str:
        """Extract stop color from style attribute or stop-color attribute."""
        # Check style attribute first
        style = stop_element.get('style', '')
        if style:
            # Parse style for stop-color
            for declaration in style.split(';'):
                declaration = declaration.strip()
                if declaration.startswith('stop-color:'):
                    return declaration.split(':', 1)[1].strip()

        # Fallback to stop-color attribute
        return stop_element.get('stop-color', '#000000')

    def _convert_color_to_hex(self, color: str) -> str:
        """Convert color value to 6-digit hex format for DrawingML using unified Color API."""
        try:
            # Use unified Color API for consistent color parsing
            from ..color import Color
            color_obj = Color(color.strip())
            hex_result = color_obj.hex()
            # Color API returns hex without # prefix, so use directly
            hex_color = hex_result if not hex_result.startswith('#') else hex_result[1:]
            return hex_color.upper()
        except Exception as e:
            logger.debug(f"Color API failed for '{color}', using fallback: {e}")

            # Fallback to basic parsing for edge cases
            color = color.strip()

            # Handle hex colors
            if color.startswith('#'):
                hex_color = color[1:]
                # Ensure 6-digit format
                if len(hex_color) == 3:
                    hex_color = ''.join([c*2 for c in hex_color])
                elif len(hex_color) == 6:
                    pass  # Already correct format
                else:
                    hex_color = '000000'  # Invalid hex, fallback to black
                return hex_color.upper()

            # Handle basic named colors as final fallback
            basic_colors = {
                'red': 'FF0000', 'blue': '0000FF', 'green': '008000', 'black': '000000',
                'white': 'FFFFFF', 'yellow': 'FFFF00', 'cyan': '00FFFF', 'magenta': 'FF00FF'
            }

            return basic_colors.get(color.lower(), '000000')

    def process_svg_gradients(self, svg_root: ET.Element) -> None:
        """Process all gradient definitions in an SVG document."""
        # Find and register all gradients
        for grad in svg_root.xpath('.//svg:defs//svg:linearGradient | .//svg:defs//svg:radialGradient',
                                   namespaces={'svg': 'http://www.w3.org/2000/svg'}):
            grad_id = grad.get('id')
            if grad_id:
                self.register_gradient(grad_id, grad)

    def clear_cache(self) -> None:
        """Clear all cached gradients and conversions."""
        self._gradient_cache.clear()
        self._conversion_cache.clear()