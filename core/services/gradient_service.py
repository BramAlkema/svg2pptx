#!/usr/bin/env python3
"""
GradientService for handling SVG gradient definitions and conversions.

Provides gradient resolution, caching, and conversion to DrawingML.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from lxml import etree as ET

if TYPE_CHECKING:
    from core.policy.engine import PolicyEngine

# Mesh gradient engine will be imported lazily to avoid circular imports

logger = logging.getLogger(__name__)


class GradientService:
    """Service for managing SVG gradient definitions and conversions."""

    def __init__(self, policy_engine: Optional['PolicyEngine'] = None):
        self._gradient_cache: dict[str, ET.Element] = {}
        self._conversion_cache: dict[str, str] = {}
        self._mesh_engine = None  # Lazy initialization
        self._policy_engine = policy_engine

    def register_gradient(self, gradient_id: str, gradient_element: ET.Element) -> None:
        """Register a gradient definition for later resolution."""
        self._gradient_cache[gradient_id] = gradient_element

    def get_gradient_content(self, gradient_id: str, context: Any = None) -> str | None:
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
        # Get all stops before potential simplification
        all_stops = gradient_element.findall('.//{http://www.w3.org/2000/svg}stop')
        stop_count = len(all_stops)

        # Use policy engine if available
        if self._policy_engine:
            decision = self._policy_engine.decide_gradient(
                gradient=gradient_element,
                gradient_type='linear',
                stop_count=stop_count,
            )

            # Handle simplification if needed
            if decision.use_simplified_gradient:
                stops = self._simplify_gradient_stops(all_stops, decision)
            else:
                stops = self._extract_gradient_stops(gradient_element)
        else:
            stops = self._extract_gradient_stops(gradient_element)

        # Simple linear gradient representation
        return f"<a:gradFill><a:gsLst>{stops}</a:gsLst><a:lin ang=\"0\" scaled=\"0\"/></a:gradFill>"

    def _convert_radial_gradient(self, gradient_element: ET.Element) -> str:
        """Convert radial gradient to basic DrawingML representation."""
        # Get all stops before potential simplification
        all_stops = gradient_element.findall('.//{http://www.w3.org/2000/svg}stop')
        stop_count = len(all_stops)

        # Use policy engine if available
        if self._policy_engine:
            decision = self._policy_engine.decide_gradient(
                gradient=gradient_element,
                gradient_type='radial',
                stop_count=stop_count,
            )

            # Handle simplification if needed
            if decision.use_simplified_gradient:
                stops = self._simplify_gradient_stops(all_stops, decision)
            else:
                stops = self._extract_gradient_stops(gradient_element)
        else:
            stops = self._extract_gradient_stops(gradient_element)

        # Simple radial gradient representation
        return f"<a:gradFill><a:gsLst>{stops}</a:gsLst><a:path path=\"circle\"/></a:gradFill>"

    def _convert_mesh_gradient(self, gradient_element: ET.Element) -> str:
        """Convert mesh gradient to DrawingML using the mesh gradient engine."""
        # Analyze mesh dimensions
        mesh_rows, mesh_cols = self._analyze_mesh_dimensions(gradient_element)

        # Use policy engine if available
        if self._policy_engine:
            decision = self._policy_engine.decide_gradient(
                gradient=gradient_element,
                gradient_type='mesh',
                stop_count=0,  # Mesh gradients don't have traditional stops
                mesh_rows=mesh_rows,
                mesh_cols=mesh_cols,
            )

            # Check if mesh is too complex for native conversion
            if not decision.use_native:
                return f"<!-- Mesh gradient: EMF fallback required (patches: {decision.mesh_patch_count}) -->"

        # Lazy import and initialization to avoid circular imports
        if self._mesh_engine is None:
            try:
                from ..converters.gradients.mesh_engine import MeshGradientEngine
                self._mesh_engine = MeshGradientEngine()
            except ImportError:
                logger.warning("Mesh gradient engine not available")
                return "<!-- Mesh gradient: Engine not available -->"

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
                'white': 'FFFFFF', 'yellow': 'FFFF00', 'cyan': '00FFFF', 'magenta': 'FF00FF',
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

    def _simplify_gradient_stops(self, stops: list[ET.Element], decision: Any) -> str:
        """
        Simplify gradient stops by reducing count to match policy thresholds.

        Args:
            stops: List of gradient stop elements
            decision: GradientDecision with target stop count

        Returns:
            Simplified stops as DrawingML string
        """
        if not stops:
            return ""

        # Get max stops from policy
        max_stops = self._policy_engine.config.thresholds.max_gradient_stops if self._policy_engine else 10

        # If already within limit, use all stops
        if len(stops) <= max_stops:
            simplified_stops = []
            for stop in stops:
                offset = stop.get('offset', '0')
                if offset.endswith('%'):
                    pos = int(float(offset[:-1]) * 1000)
                else:
                    pos = int(float(offset) * 100000)

                color = self._extract_stop_color(stop)
                color_hex = self._convert_color_to_hex(color)
                simplified_stops.append(f'<a:gs pos="{pos}"><a:srgbClr val="{color_hex}"/></a:gs>')

            return ''.join(simplified_stops)

        # Reduce stops by sampling evenly
        indices = [int(i * (len(stops) - 1) / (max_stops - 1)) for i in range(max_stops)]
        simplified_stops = []

        for idx in indices:
            stop = stops[idx]
            offset = stop.get('offset', '0')
            if offset.endswith('%'):
                pos = int(float(offset[:-1]) * 1000)
            else:
                pos = int(float(offset) * 100000)

            color = self._extract_stop_color(stop)
            color_hex = self._convert_color_to_hex(color)
            simplified_stops.append(f'<a:gs pos="{pos}"><a:srgbClr val="{color_hex}"/></a:gs>')

        logger.info(f"Simplified gradient from {len(stops)} to {max_stops} stops")
        return ''.join(simplified_stops)

    def _analyze_mesh_dimensions(self, gradient_element: ET.Element) -> tuple:
        """
        Analyze mesh gradient dimensions.

        Args:
            gradient_element: Mesh gradient element

        Returns:
            Tuple of (rows, cols)
        """
        # Try to extract from mesh gradient structure
        # This is a simplified version - actual mesh gradients can be complex
        rows = int(gradient_element.get('x', '2'))  # Default 2x2 mesh
        cols = int(gradient_element.get('y', '2'))

        # Look for mesh rows/patches
        patches = gradient_element.findall('.//{http://www.w3.org/2000/svg}meshrow')
        if patches:
            rows = len(patches)
            # Count patches in first row to estimate cols
            if patches:
                cols = len(patches[0].findall('.//{http://www.w3.org/2000/svg}meshpatch'))

        return (rows, cols)