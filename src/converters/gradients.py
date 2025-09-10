"""
SVG Gradient to DrawingML Converter

Handles SVG gradient elements with support for:
- Linear gradients (linearGradient)
- Radial gradients (radialGradient)
- Gradient stops with colors and opacity
- Gradient transforms
- Pattern fills (basic support)
"""

from typing import List, Dict, Any, Optional, Tuple
from lxml import etree as ET
import math
from .base import BaseConverter, ConversionContext


class GradientConverter(BaseConverter):
    """Converts SVG gradients to DrawingML fill properties"""
    
    supported_elements = ['linearGradient', 'radialGradient', 'pattern']
    
    def __init__(self):
        super().__init__()
        self.gradients = {}  # Cache for gradient definitions
    
    def can_convert(self, element: ET.Element, context: Optional[ConversionContext] = None) -> bool:
        """Check if this converter can handle the given element."""
        tag = self.get_element_tag(element)
        return tag in self.supported_elements
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG gradient to DrawingML gradient fill"""
        if element.tag.endswith('linearGradient'):
            return self._convert_linear_gradient(element, context)
        elif element.tag.endswith('radialGradient'):
            return self._convert_radial_gradient(element, context)
        elif element.tag.endswith('pattern'):
            return self._convert_pattern(element, context)
        return ""
    
    def get_fill_from_url(self, url: str, context: ConversionContext) -> str:
        """Get fill definition from URL reference (url(#id))"""
        if not url.startswith('url(#') or not url.endswith(')'):
            return ""
        
        if context.svg_root is None:
            return ""
        
        gradient_id = url[5:-1]  # Remove 'url(#' and ')'
        
        # Find gradient element in SVG
        gradient_element = context.svg_root.find(f".//*[@id='{gradient_id}']")
        if gradient_element is None:
            # Also check in defs section
            defs = context.svg_root.find('.//defs')
            if defs is not None:
                gradient_element = defs.find(f".//*[@id='{gradient_id}']")
        
        if gradient_element is not None:
            return self.convert(gradient_element, context)
        
        return ""
    
    def _safe_float_parse(self, value: str, default: float = 0.0) -> float:
        """Safely parse a string to float, returning default on error"""
        try:
            return float(value.rstrip('%'))
        except (ValueError, AttributeError):
            return default

    def _convert_linear_gradient(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG linear gradient to DrawingML linear gradient"""
        # Get gradient coordinates with safe parsing
        x1 = self._safe_float_parse(element.get('x1', '0%'), 0.0)
        y1 = self._safe_float_parse(element.get('y1', '0%'), 0.0)
        x2 = self._safe_float_parse(element.get('x2', '100%'), 100.0)
        y2 = self._safe_float_parse(element.get('y2', '0%'), 0.0)
        
        # Convert percentage to actual values
        if element.get('x1', '').endswith('%'):
            x1 = x1 / 100
        if element.get('y1', '').endswith('%'):
            y1 = y1 / 100
        if element.get('x2', '').endswith('%'):
            x2 = x2 / 100
        if element.get('y2', '').endswith('%'):
            y2 = y2 / 100
        
        # Calculate angle in degrees
        dx = x2 - x1
        dy = y2 - y1
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        
        # Convert to DrawingML angle (0-21600000, where 21600000 = 360°)
        # DrawingML angles start from 3 o'clock and go clockwise
        drawingml_angle = int(((90 - angle_deg) % 360) * 60000)
        
        # Get gradient stops
        stops = self._get_gradient_stops(element)
        if not stops:
            return ""
        
        # Create gradient stop list
        stop_list = []
        for position, color, opacity in stops:
            stop_position = int(position * 1000)  # Convert to per-mille (0-1000)
            alpha_attr = f' alpha="{int(opacity * 100000)}"' if opacity < 1.0 else ""
            stop_list.append(f'<a:gs pos="{stop_position}"><a:srgbClr val="{color}"{alpha_attr}/></a:gs>')
        
        stops_xml = '\n                    '.join(stop_list)
        
        return f"""<a:gradFill flip="none" rotWithShape="1">
            <a:gsLst>
                {stops_xml}
            </a:gsLst>
            <a:lin ang="{drawingml_angle}" scaled="1"/>
        </a:gradFill>"""
    
    def _convert_radial_gradient(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG radial gradient to DrawingML radial gradient"""
        # Get gradient properties with safe parsing
        cx = self._safe_float_parse(element.get('cx', '50%'), 50.0)
        cy = self._safe_float_parse(element.get('cy', '50%'), 50.0)
        r = self._safe_float_parse(element.get('r', '50%'), 50.0)
        fx = self._safe_float_parse(element.get('fx', element.get('cx', '50%')), cx)
        fy = self._safe_float_parse(element.get('fy', element.get('cy', '50%')), cy)
        
        # Convert percentage to actual values
        if element.get('cx', '').endswith('%'):
            cx = cx / 100
        if element.get('cy', '').endswith('%'):
            cy = cy / 100
        if element.get('r', '').endswith('%'):
            r = r / 100
        if element.get('fx', '').endswith('%'):
            fx = fx / 100
        if element.get('fy', '').endswith('%'):
            fy = fy / 100
        
        # Get gradient stops
        stops = self._get_gradient_stops(element)
        if not stops:
            return ""
        
        # Create gradient stop list (reverse order for radial)
        stop_list = []
        for position, color, opacity in reversed(stops):
            stop_position = int((1.0 - position) * 1000)  # Reverse position
            alpha_attr = f' alpha="{int(opacity * 100000)}"' if opacity < 1.0 else ""
            stop_list.append(f'<a:gs pos="{stop_position}"><a:srgbClr val="{color}"{alpha_attr}/></a:gs>')
        
        stops_xml = '\n                    '.join(stop_list)
        
        # Calculate focus offset (simplified)
        focus_x = int((fx - cx) * 100)  # Percentage offset
        focus_y = int((fy - cy) * 100)  # Percentage offset
        
        return f"""<a:gradFill flip="none" rotWithShape="1">
            <a:gsLst>
                {stops_xml}
            </a:gsLst>
            <a:path path="circle">
                <a:fillToRect l="0" t="0" r="0" b="0"/>
            </a:path>
        </a:gradFill>"""
    
    def _convert_pattern(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG pattern to DrawingML pattern fill (simplified)"""
        # For now, convert pattern to solid fill with dominant color
        # This is a fallback - full pattern support would require more complex implementation
        
        # Try to extract a representative color from pattern content
        fill_color = self._extract_pattern_color(element)
        if fill_color:
            return f'<a:solidFill><a:srgbClr val="{fill_color}"/></a:solidFill>'
        
        return ""
    
    def _get_gradient_stops(self, gradient_element: ET.Element) -> List[Tuple[float, str, float]]:
        """Extract gradient stops with position, color, and opacity"""
        stops = []
        
        for stop in gradient_element.findall('.//stop'):
            # Get stop position (offset) with safe parsing
            offset = stop.get('offset', '0')
            try:
                if offset.endswith('%'):
                    position = float(offset[:-1]) / 100
                else:
                    position = float(offset)
            except (ValueError, TypeError):
                position = 0.0  # Default to start if invalid
            
            # Get stop color
            stop_color = stop.get('stop-color', '#000000')
            try:
                stop_opacity = float(stop.get('stop-opacity', '1'))
            except (ValueError, TypeError):
                stop_opacity = 1.0
            
            # Check style attribute for color/opacity
            style = stop.get('style', '')
            if style:
                style_props = {}
                for prop in style.split(';'):
                    if ':' in prop:
                        key, value = prop.split(':', 1)
                        style_props[key.strip()] = value.strip()
                
                if 'stop-color' in style_props:
                    stop_color = style_props['stop-color']
                if 'stop-opacity' in style_props:
                    try:
                        stop_opacity = float(style_props['stop-opacity'])
                    except (ValueError, TypeError):
                        stop_opacity = 1.0
            
            # Parse color
            color_hex = self.parse_color(stop_color)
            if color_hex:
                stops.append((position, color_hex, stop_opacity))
        
        # Sort by position
        stops.sort(key=lambda x: x[0])
        return stops
    
    def _extract_pattern_color(self, pattern_element: ET.Element) -> Optional[str]:
        """Extract a representative color from pattern content"""
        # Look for fill colors in pattern content
        for element in pattern_element.iter():
            fill = element.get('fill')
            if fill and fill != 'none' and not fill.startswith('url('):
                color = self.parse_color(fill)
                if color:
                    return color
            
            # Check style attribute
            style = element.get('style', '')
            if 'fill:' in style:
                for part in style.split(';'):
                    if part.strip().startswith('fill:'):
                        fill = part.split(':', 1)[1].strip()
                        if fill and fill != 'none' and not fill.startswith('url('):
                            color = self.parse_color(fill)
                            if color:
                                return color
        
        return None