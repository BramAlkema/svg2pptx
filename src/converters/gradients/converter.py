"""
SVG Gradient to DrawingML Converter

Modern gradient converter that integrates with the high-performance gradient engines.
Uses the optimized GradientEngine for maximum performance while maintaining
compatibility with the converter registry system.
"""

from typing import List, Dict, Any, Optional, Tuple
from lxml import etree as ET
import math

from ..base import BaseConverter, ConversionContext
from ...services.conversion_services import ConversionServices
from .core import GradientEngine
from .mesh_engine import MeshGradientEngine


class GradientConverter(BaseConverter):
    """Converts SVG gradients to DrawingML fill properties using optimized engines"""

    supported_elements = ['linearGradient', 'radialGradient', 'pattern', 'meshgradient']

    def __init__(self, services: ConversionServices):
        """
        Initialize GradientConverter with dependency injection.

        Args:
            services: ConversionServices container with initialized services
        """
        super().__init__(services)
        self.gradients = {}  # Cache for gradient definitions
        self.gradient_engine = GradientEngine(optimization_level=2)
        self.mesh_engine = MeshGradientEngine()

    def can_convert(self, element: ET.Element, context: Optional[ConversionContext] = None) -> bool:
        """Check if this converter can handle the given element."""
        tag = self.get_element_tag(element)
        return tag in self.supported_elements

    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG gradient to DrawingML gradient fill using optimized engine"""
        try:
            # Use the optimized gradient engine for processing
            if element.tag.endswith('linearGradient') or element.tag.endswith('radialGradient'):
                # Try the high-performance engine first
                try:
                    result = self.gradient_engine.process_single_gradient(element)
                    if result:
                        return result
                except Exception as e:
                    self.logger.debug(f"High-performance engine failed, using fallback: {e}")

            # Fallback to basic implementation
            if element.tag.endswith('linearGradient'):
                return self._convert_linear_gradient(element, context)
            elif element.tag.endswith('radialGradient'):
                return self._convert_radial_gradient(element, context)
            elif element.tag.endswith('pattern'):
                return self._convert_pattern(element, context)
            elif element.tag.endswith('meshgradient'):
                return self._convert_mesh_gradient(element, context)
            else:
                self.logger.warning(f"Unknown gradient type: {element.tag}")
                return self._create_fallback_gradient()

        except Exception as e:
            self.logger.error(f"Error converting gradient element {element.tag}: {e}")
            return self._create_fallback_gradient()

    def get_fill_from_url(self, url: str, context: ConversionContext) -> str:
        """Get fill definition from URL reference (url(#id))"""
        try:
            if not isinstance(url, str) or not url.startswith('url(#') or not url.endswith(')'):
                self.logger.warning(f"Invalid URL format: {url}")
                return ""

            if context.svg_root is None:
                self.logger.error("SVG root not available in context")
                return ""

            gradient_id = url[5:-1]  # Remove 'url(#' and ')'

            if not gradient_id or gradient_id.strip() == "":
                self.logger.warning(f"Empty gradient ID in URL: {url}")
                return ""

            # Find gradient element in SVG
            gradient_element = context.svg_root.find(f".//*[@id='{gradient_id}']")
            if gradient_element is None:
                defs = context.svg_root.find('.//defs')
                if defs is not None:
                    gradient_element = defs.find(f".//*[@id='{gradient_id}']")

            if gradient_element is not None:
                return self.convert(gradient_element, context)
            else:
                self.logger.warning(f"Gradient not found: {gradient_id}")
                return self._create_fallback_gradient()

        except Exception as e:
            self.logger.error(f"Unexpected error in get_fill_from_url: {e}")
            return self._create_fallback_gradient()

    def _create_fallback_gradient(self) -> str:
        """Create fallback gradient for error cases"""
        return '''<a:gradFill>
                    <a:gsLst>
                        <a:gs pos="0">
                            <a:srgbClr val="CCCCCC"/>
                        </a:gs>
                        <a:gs pos="100000">
                            <a:srgbClr val="999999"/>
                        </a:gs>
                    </a:gsLst>
                    <a:lin ang="2700000" scaled="0"/>
                </a:gradFill>'''

    def _safe_float_parse(self, value: str, default: float = 0.0) -> float:
        """Safely parse float value with fallback using CoordinateTransformer service."""
        # Migrated to use CoordinateTransformer service for consistent coordinate parsing
        try:
            # Use the coordinate transformer service for consistent parsing
            parsed_result = self.services.coordinate_transformer.parse_single_coordinate(value)
            return parsed_result.value if parsed_result else default
        except (ValueError, TypeError, AttributeError):
            # Fallback to direct parsing if service is not available
            try:
                return float(value)
            except (ValueError, TypeError):
                return default

    def _convert_linear_gradient(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert linear gradient using basic implementation"""
        # Extract gradient attributes using coordinate transformer service
        # Use CoordinateTransformer for consistent coordinate parsing
        coord_str = f"{element.get('x1', '0')},{element.get('y1', '0')} {element.get('x2', '1')},{element.get('y2', '0')}"
        result = self.services.coordinate_transformer.parse_coordinate_string(coord_str)

        if len(result.coordinates) >= 2:
            (x1, y1), (x2, y2) = result.coordinates[0], result.coordinates[1]
        else:
            # Fallback to manual parsing for backward compatibility
            x1 = self._safe_float_parse(element.get('x1', '0'), 0.0)
            y1 = self._safe_float_parse(element.get('y1', '0'), 0.0)
            x2 = self._safe_float_parse(element.get('x2', '1'), 1.0)
            y2 = self._safe_float_parse(element.get('y2', '0'), 0.0)

        # Calculate angle
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            angle = 0
        else:
            angle = math.atan2(dy, dx) * 180 / math.pi
            angle = (90 - angle) % 360  # Convert to DrawingML angle system

        angle_emu = int(angle * 60000)  # Convert to EMU (1/60000 degree)

        # Get gradient stops
        stops = self._get_gradient_stops(element)
        stop_xmls = []

        for position, color, opacity in stops:
            pos_per_mille = int(position * 100000)
            if opacity < 1.0:
                alpha_val = int(opacity * 100000)
                stop_xml = f'<a:gs pos="{pos_per_mille}"><a:srgbClr val="{color}" alpha="{alpha_val}"/></a:gs>'
            else:
                stop_xml = f'<a:gs pos="{pos_per_mille}"><a:srgbClr val="{color}"/></a:gs>'
            stop_xmls.append(stop_xml)

        stops_xml = '\n                        '.join(stop_xmls)

        return f'''<a:gradFill>
                    <a:gsLst>
                        {stops_xml}
                    </a:gsLst>
                    <a:lin ang="{angle_emu}" scaled="0"/>
                </a:gradFill>'''

    def _convert_radial_gradient(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert radial gradient using basic implementation"""
        # Get gradient stops
        stops = self._get_gradient_stops(element)
        stop_xmls = []

        for position, color, opacity in stops:
            pos_per_mille = int(position * 100000)
            if opacity < 1.0:
                alpha_val = int(opacity * 100000)
                stop_xml = f'<a:gs pos="{pos_per_mille}"><a:srgbClr val="{color}" alpha="{alpha_val}"/></a:gs>'
            else:
                stop_xml = f'<a:gs pos="{pos_per_mille}"><a:srgbClr val="{color}"/></a:gs>'
            stop_xmls.append(stop_xml)

        stops_xml = '\n                        '.join(stop_xmls)

        return f'''<a:gradFill>
                    <a:gsLst>
                        {stops_xml}
                    </a:gsLst>
                    <a:path path="circle"/>
                </a:gradFill>'''

    def _convert_pattern(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert pattern - simplified implementation"""
        return self._create_fallback_gradient()

    def _convert_mesh_gradient(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert mesh gradient using dedicated mesh gradient engine"""
        return self.mesh_engine.convert_mesh_gradient(element)

    def _get_gradient_stops(self, gradient_element: ET.Element) -> List[Tuple[float, str, float]]:
        """Extract gradient stops from gradient element"""
        stops = []

        # Find all stop elements
        stop_elements = gradient_element.findall('.//stop')

        if not stop_elements:
            # Create default stops if none found
            return [(0.0, "000000", 1.0), (1.0, "FFFFFF", 1.0)]

        for stop in stop_elements:
            # Parse offset
            offset_str = stop.get('offset', '0')
            if offset_str.endswith('%'):
                offset = float(offset_str[:-1]) / 100.0
            else:
                offset = float(offset_str) if offset_str else 0.0

            # Parse color using canonical Color API for consistency
            stop_color_str = stop.get('stop-color', '#000000')
            try:
                from ...color import Color
                color_obj = Color(stop_color_str)
                stop_color = color_obj.hex()[1:]  # Remove # prefix
            except:
                # Fallback for invalid colors
                stop_color = "000000"

            # Parse opacity with style attribute support
            stop_opacity_str = stop.get('stop-opacity', '1.0')
            # Check for style attribute opacity as well
            style = stop.get('style', '')
            if 'stop-opacity:' in style and self.services.style_parser:
                style_opacity = self.services.style_parser.get_property_value(style, 'stop-opacity')
                if style_opacity:
                    stop_opacity_str = style_opacity

            try:
                stop_opacity = float(stop_opacity_str)
            except (ValueError, TypeError):
                stop_opacity = 1.0

            stops.append((offset, stop_color.upper(), stop_opacity))

        # Sort by offset
        stops.sort(key=lambda x: x[0])

        # Ensure we have at least 2 stops
        if len(stops) < 2:
            if len(stops) == 1:
                color = stops[0][1]
                stops = [(0.0, color, 1.0), (1.0, color, 1.0)]
            else:
                stops = [(0.0, "000000", 1.0), (1.0, "FFFFFF", 1.0)]

        return stops