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
                    # Validate element before processing
                    if not self._validate_gradient_element(element):
                        self.logger.debug(f"Gradient element validation failed, using fallback for {element.get('id', 'unknown')}")
                        return self._convert_with_fallback(element, context)

                    result = self.gradient_engine.process_single_gradient(element)
                    if result and len(result.strip()) > 0:
                        self.logger.debug(f"High-performance engine succeeded for gradient {element.get('id', 'unknown')}")
                        return result
                    else:
                        self.logger.debug(f"High-performance engine returned empty result for {element.get('id', 'unknown')}, using fallback")
                        return self._convert_with_fallback(element, context)

                except Exception as e:
                    self.logger.warning(f"High-performance engine failed for gradient {element.get('id', 'unknown')}: {e}")
                    import traceback
                    self.logger.debug(f"Gradient engine traceback: {traceback.format_exc()}")
                    return self._convert_with_fallback(element, context)

            # Handle other gradient types
            return self._convert_with_fallback(element, context)

        except Exception as e:
            self.logger.error(f"Error converting gradient element {element.tag}: {e}")
            return self._create_fallback_gradient()

    def _convert_with_fallback(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert using fallback implementation with proper routing"""
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

    def _validate_gradient_element(self, element: ET.Element) -> bool:
        """Validate gradient element before processing with high-performance engine"""
        try:
            # Check if element is valid
            if element is None:
                return False

            # Check if element has required attributes based on type
            if element.tag.endswith('linearGradient'):
                # Linear gradients should have coordinate attributes (with defaults)
                return True  # LinearGradient engine handles defaults
            elif element.tag.endswith('radialGradient'):
                # Radial gradients should have center/radius attributes (with defaults)
                return True  # RadialGradient engine handles defaults

            return True

        except Exception as e:
            self.logger.debug(f"Gradient validation error: {e}")
            return False

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
            # Handle percentage values
            if value and value.strip().endswith('%'):
                percentage_val = value.strip()[:-1]
                return float(percentage_val) / 100.0

            # Use the coordinate transformer service for consistent parsing
            parsed_result = self.services.coordinate_transformer.parse_coordinate_string(value)
            if parsed_result and parsed_result.coordinates:
                # Return the first coordinate's x value
                return parsed_result.coordinates[0][0]

            # Try direct float parsing as fallback
            return float(value) if value else default

        except (ValueError, TypeError, AttributeError) as e:
            self.logger.debug(f"Coordinate parsing failed for '{value}': {e}, using default {default}")
            return default

    def _convert_linear_gradient(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert linear gradient using enhanced coordinate transformer"""
        # Extract gradient attributes using coordinate transformer service for consistency
        try:
            # Get coordinate values with defaults
            x1_str = element.get('x1', '0%')
            y1_str = element.get('y1', '0%')
            x2_str = element.get('x2', '100%')
            y2_str = element.get('y2', '0%')

            # Use CoordinateTransformer for consistent coordinate parsing
            x1 = self._safe_float_parse(x1_str, 0.0)
            y1 = self._safe_float_parse(y1_str, 0.0)
            x2 = self._safe_float_parse(x2_str, 1.0)
            y2 = self._safe_float_parse(y2_str, 0.0)

            self.logger.debug(f"Parsed gradient coordinates: x1={x1}, y1={y1}, x2={x2}, y2={y2}")

        except Exception as e:
            self.logger.warning(f"Coordinate parsing failed for gradient {element.get('id', 'unknown')}: {e}")
            # Safe fallback values
            x1, y1, x2, y2 = 0.0, 0.0, 1.0, 0.0

        # Calculate angle with coordinate validation
        dx = x2 - x1
        dy = y2 - y1

        # Validate coordinate differences
        if abs(dx) < 1e-10 and abs(dy) < 1e-10:
            # Zero-length gradient, default to horizontal
            angle = 0
            self.logger.debug(f"Zero-length gradient detected, using horizontal angle")
        else:
            # Calculate angle using robust math
            angle = math.atan2(dy, dx) * 180 / math.pi
            angle = (90 - angle) % 360  # Convert to DrawingML angle system

            # Validate angle range
            if not (0 <= angle <= 360):
                self.logger.warning(f"Invalid angle {angle}, clamping to valid range")
                angle = max(0, min(360, angle))

        angle_emu = int(angle * 60000)  # Convert to EMU (1/60000 degree)

        # Validate EMU range for DrawingML
        if not (0 <= angle_emu <= 21600000):  # 21600000 = 360 * 60000
            self.logger.warning(f"Angle EMU {angle_emu} out of range, clamping")
            angle_emu = max(0, min(21600000, angle_emu))

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

            # Also check style attribute for stop-color
            style = stop.get('style', '')
            if 'stop-color:' in style and self.services.style_parser:
                style_color = self.services.style_parser.get_property_value(style, 'stop-color')
                if style_color:
                    stop_color_str = style_color

            try:
                color_obj = self.services.color_parser(stop_color_str.strip())
                hex_result = color_obj.hex()
                # Color API returns hex without # prefix, so use directly
                stop_color = hex_result if not hex_result.startswith('#') else hex_result[1:]
                self.logger.debug(f"Successfully parsed color '{stop_color_str}' to hex '{stop_color}'")
            except Exception as e:
                # Enhanced fallback for invalid colors with logging
                self.logger.debug(f"Color parsing failed for '{stop_color_str}': {e}, using fallback")

                # Try basic hex extraction as fallback
                fallback_color = self._extract_fallback_color(stop_color_str)
                stop_color = fallback_color
                self.logger.debug(f"Used fallback color '{stop_color}' for invalid input '{stop_color_str}'")

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

    def _extract_fallback_color(self, color_str: str) -> str:
        """Extract fallback color when Color API fails"""
        try:
            color_clean = color_str.strip().lower()

            # Try basic hex parsing
            if color_clean.startswith('#'):
                hex_part = color_clean[1:]
                if len(hex_part) == 3:
                    # Expand 3-digit hex
                    hex_part = ''.join([c*2 for c in hex_part])
                elif len(hex_part) == 6:
                    # Already valid 6-digit hex
                    pass
                else:
                    # Invalid length, use default
                    return "000000"

                # Validate hex characters
                try:
                    int(hex_part, 16)
                    return hex_part.upper()
                except ValueError:
                    pass

            # Basic named color fallbacks
            basic_colors = {
                'red': 'FF0000', 'green': '008000', 'blue': '0000FF', 'yellow': 'FFFF00',
                'black': '000000', 'white': 'FFFFFF', 'gray': '808080', 'grey': '808080',
                'cyan': '00FFFF', 'magenta': 'FF00FF', 'orange': 'FFA500', 'purple': '800080'
            }

            if color_clean in basic_colors:
                return basic_colors[color_clean]

        except Exception:
            pass

        # Final fallback to black
        return "000000"