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
import xml.etree.ElementTree as ET
import math
from .base import BaseConverter, ConversionContext


class GradientConverter(BaseConverter):
    """Converts SVG gradients to DrawingML fill properties"""
    
    supported_elements = ['linearGradient', 'radialGradient', 'pattern']
    
    def __init__(self):
        super().__init__()
        self.gradients = {}  # Cache for gradient definitions
    
    def can_convert(self, element: ET.Element) -> bool:
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
    
    def _convert_linear_gradient(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG linear gradient to DrawingML linear gradient"""
        # Get gradient coordinates
        x1 = float(element.get('x1', '0%').rstrip('%'))
        y1 = float(element.get('y1', '0%').rstrip('%'))
        x2 = float(element.get('x2', '100%').rstrip('%'))
        y2 = float(element.get('y2', '0%').rstrip('%'))
        
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
        # Get gradient properties
        cx = float(element.get('cx', '50%').rstrip('%'))
        cy = float(element.get('cy', '50%').rstrip('%'))
        r = float(element.get('r', '50%').rstrip('%'))
        fx = float(element.get('fx', str(cx)).rstrip('%'))
        fy = float(element.get('fy', str(cy)).rstrip('%'))
        
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
            # Get stop position (offset)
            offset = stop.get('offset', '0')
            if offset.endswith('%'):
                position = float(offset[:-1]) / 100
            else:
                position = float(offset)
            
            # Get stop color
            stop_color = stop.get('stop-color', '#000000')
            stop_opacity = float(stop.get('stop-opacity', '1'))
            
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
                    stop_opacity = float(style_props['stop-opacity'])
            
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
    
    
    def _hsl_to_rgb(self, h: float, s: float, l: float) -> Tuple[int, int, int]:
        """Convert HSL to RGB"""
        h = h / 360.0  # Convert to 0-1 range
        
        if s == 0:
            # Achromatic (gray)
            r = g = b = l
        else:
            def hue_to_rgb(p: float, q: float, t: float) -> float:
                if t < 0:
                    t += 1
                if t > 1:
                    t -= 1
                if t < 1/6:
                    return p + (q - p) * 6 * t
                if t < 1/2:
                    return q
                if t < 2/3:
                    return p + (q - p) * (2/3 - t) * 6
                return p
            
            q = l * (1 + s) if l < 0.5 else l + s - l * s
            p = 2 * l - q
            
            r = hue_to_rgb(p, q, h + 1/3)
            g = hue_to_rgb(p, q, h)
            b = hue_to_rgb(p, q, h - 1/3)
        
        return (int(r * 255), int(g * 255), int(b * 255))