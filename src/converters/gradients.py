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
            color_hex = self._parse_color(stop_color)
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
                color = self._parse_color(fill)
                if color:
                    return color
            
            # Check style attribute
            style = element.get('style', '')
            if 'fill:' in style:
                for part in style.split(';'):
                    if part.strip().startswith('fill:'):
                        fill = part.split(':', 1)[1].strip()
                        if fill and fill != 'none' and not fill.startswith('url('):
                            color = self._parse_color(fill)
                            if color:
                                return color
        
        return None
    
    def _parse_color(self, color: str) -> Optional[str]:
        """Parse color value to hex format"""
        color = color.strip().lower()
        
        # Hex colors
        if color.startswith('#'):
            hex_color = color[1:]
            if len(hex_color) == 3:
                # Expand short hex
                hex_color = ''.join([c*2 for c in hex_color])
            if len(hex_color) == 6:
                return hex_color.upper()
        
        # RGB colors
        if color.startswith('rgb('):
            try:
                rgb_str = color[4:-1]  # Remove 'rgb(' and ')'
                r, g, b = [int(x.strip()) for x in rgb_str.split(',')]
                return f"{r:02X}{g:02X}{b:02X}"
            except (ValueError, IndexError):
                pass
        
        # RGBA colors
        if color.startswith('rgba('):
            try:
                rgba_str = color[5:-1]  # Remove 'rgba(' and ')'
                parts = [x.strip() for x in rgba_str.split(',')]
                if len(parts) >= 3:
                    r, g, b = [int(parts[i]) for i in range(3)]
                    return f"{r:02X}{g:02X}{b:02X}"
            except (ValueError, IndexError):
                pass
        
        # HSL colors (simplified conversion)
        if color.startswith('hsl('):
            try:
                hsl_str = color[4:-1]  # Remove 'hsl(' and ')'
                h, s, l = [float(x.strip().rstrip('%')) for x in hsl_str.split(',')]
                rgb = self._hsl_to_rgb(h, s/100, l/100)
                return f"{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
            except (ValueError, IndexError):
                pass
        
        # Named colors (extended set)
        color_names = {
            'aliceblue': 'F0F8FF', 'antiquewhite': 'FAEBD7', 'aqua': '00FFFF',
            'aquamarine': '7FFFD4', 'azure': 'F0FFFF', 'beige': 'F5F5DC',
            'bisque': 'FFE4C4', 'black': '000000', 'blanchedalmond': 'FFEBCD',
            'blue': '0000FF', 'blueviolet': '8A2BE2', 'brown': 'A52A2A',
            'burlywood': 'DEB887', 'cadetblue': '5F9EA0', 'chartreuse': '7FFF00',
            'chocolate': 'D2691E', 'coral': 'FF7F50', 'cornflowerblue': '6495ED',
            'cornsilk': 'FFF8DC', 'crimson': 'DC143C', 'cyan': '00FFFF',
            'darkblue': '00008B', 'darkcyan': '008B8B', 'darkgoldenrod': 'B8860B',
            'darkgray': 'A9A9A9', 'darkgreen': '006400', 'darkkhaki': 'BDB76B',
            'darkmagenta': '8B008B', 'darkolivegreen': '556B2F', 'darkorange': 'FF8C00',
            'darkorchid': '9932CC', 'darkred': '8B0000', 'darksalmon': 'E9967A',
            'darkseagreen': '8FBC8F', 'darkslateblue': '483D8B', 'darkslategray': '2F4F4F',
            'darkturquoise': '00CED1', 'darkviolet': '9400D3', 'deeppink': 'FF1493',
            'deepskyblue': '00BFFF', 'dimgray': '696969', 'dodgerblue': '1E90FF',
            'firebrick': 'B22222', 'floralwhite': 'FFFAF0', 'forestgreen': '228B22',
            'fuchsia': 'FF00FF', 'gainsboro': 'DCDCDC', 'ghostwhite': 'F8F8FF',
            'gold': 'FFD700', 'goldenrod': 'DAA520', 'gray': '808080',
            'green': '008000', 'greenyellow': 'ADFF2F', 'honeydew': 'F0FFF0',
            'hotpink': 'FF69B4', 'indianred': 'CD5C5C', 'indigo': '4B0082',
            'ivory': 'FFFFF0', 'khaki': 'F0E68C', 'lavender': 'E6E6FA',
            'lavenderblush': 'FFF0F5', 'lawngreen': '7CFC00', 'lemonchiffon': 'FFFACD',
            'lightblue': 'ADD8E6', 'lightcoral': 'F08080', 'lightcyan': 'E0FFFF',
            'lightgoldenrodyellow': 'FAFAD2', 'lightgray': 'D3D3D3', 'lightgreen': '90EE90',
            'lightpink': 'FFB6C1', 'lightsalmon': 'FFA07A', 'lightseagreen': '20B2AA',
            'lightskyblue': '87CEFA', 'lightslategray': '778899', 'lightsteelblue': 'B0C4DE',
            'lightyellow': 'FFFFE0', 'lime': '00FF00', 'limegreen': '32CD32',
            'linen': 'FAF0E6', 'magenta': 'FF00FF', 'maroon': '800000',
            'mediumaquamarine': '66CDAA', 'mediumblue': '0000CD', 'mediumorchid': 'BA55D3',
            'mediumpurple': '9370DB', 'mediumseagreen': '3CB371', 'mediumslateblue': '7B68EE',
            'mediumspringgreen': '00FA9A', 'mediumturquoise': '48D1CC', 'mediumvioletred': 'C71585',
            'midnightblue': '191970', 'mintcream': 'F5FFFA', 'mistyrose': 'FFE4E1',
            'moccasin': 'FFE4B5', 'navajowhite': 'FFDEAD', 'navy': '000080',
            'oldlace': 'FDF5E6', 'olive': '808000', 'olivedrab': '6B8E23',
            'orange': 'FFA500', 'orangered': 'FF4500', 'orchid': 'DA70D6',
            'palegoldenrod': 'EEE8AA', 'palegreen': '98FB98', 'paleturquoise': 'AFEEEE',
            'palevioletred': 'DB7093', 'papayawhip': 'FFEFD5', 'peachpuff': 'FFDAB9',
            'peru': 'CD853F', 'pink': 'FFC0CB', 'plum': 'DDA0DD',
            'powderblue': 'B0E0E6', 'purple': '800080', 'red': 'FF0000',
            'rosybrown': 'BC8F8F', 'royalblue': '4169E1', 'saddlebrown': '8B4513',
            'salmon': 'FA8072', 'sandybrown': 'F4A460', 'seagreen': '2E8B57',
            'seashell': 'FFF5EE', 'sienna': 'A0522D', 'silver': 'C0C0C0',
            'skyblue': '87CEEB', 'slateblue': '6A5ACD', 'slategray': '708090',
            'snow': 'FFFAFA', 'springgreen': '00FF7F', 'steelblue': '4682B4',
            'tan': 'D2B48C', 'teal': '008080', 'thistle': 'D8BFD8',
            'tomato': 'FF6347', 'turquoise': '40E0D0', 'violet': 'EE82EE',
            'wheat': 'F5DEB3', 'white': 'FFFFFF', 'whitesmoke': 'F5F5F5',
            'yellow': 'FFFF00', 'yellowgreen': '9ACD32'
        }
        
        return color_names.get(color)
    
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