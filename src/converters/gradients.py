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
        """Convert SVG pattern to DrawingML pattern fill with full pattern support."""
        pattern_id = element.get('id', '')
        
        # Extract pattern properties
        pattern_units = element.get('patternUnits', 'objectBoundingBox')
        pattern_transform = element.get('patternTransform', '')
        
        # Get pattern dimensions
        width = self._parse_pattern_dimension(element.get('width', '0'), context)
        height = self._parse_pattern_dimension(element.get('height', '0'), context)
        
        if width <= 0 or height <= 0:
            # Invalid pattern dimensions, fallback to solid color
            fill_color = self._extract_pattern_color(element)
            if fill_color:
                return f'<a:solidFill><a:srgbClr val="{fill_color}"/></a:solidFill>'
            return ""
        
        # Analyze pattern content to determine best PowerPoint representation
        pattern_analysis = self._analyze_pattern_content(element, context)
        
        # Choose conversion strategy based on pattern complexity
        if pattern_analysis['is_simple_texture']:
            return self._convert_simple_pattern(element, pattern_analysis, context)
        elif pattern_analysis['is_geometric']:
            return self._convert_geometric_pattern(element, pattern_analysis, context)
        elif pattern_analysis['has_gradients']:
            return self._convert_gradient_pattern(element, pattern_analysis, context)
        else:
            # Complex pattern - generate texture image
            return self._convert_complex_pattern(element, pattern_analysis, context)
    
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
    
    def _parse_pattern_dimension(self, dimension_str: str, context: ConversionContext) -> float:
        """Parse pattern dimension string to float value."""
        if not dimension_str:
            return 0.0
        
        try:
            # Remove units and parse
            clean_str = dimension_str.replace('px', '').replace('pt', '').replace('%', '')
            return float(clean_str)
        except (ValueError, TypeError):
            return 0.0
    
    def _analyze_pattern_content(self, pattern_element: ET.Element, context: ConversionContext) -> Dict[str, Any]:
        """Analyze pattern content to determine conversion strategy."""
        analysis = {
            'is_simple_texture': False,
            'is_geometric': False,
            'has_gradients': False,
            'element_count': 0,
            'dominant_shapes': [],
            'color_count': 0,
            'complexity_score': 0
        }
        
        # Count elements and analyze shapes
        all_elements = list(pattern_element.iter())
        shape_counts = {}
        colors = set()
        
        for elem in all_elements:
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            if tag in ['rect', 'circle', 'ellipse', 'path', 'polygon', 'line']:
                analysis['element_count'] += 1
                shape_counts[tag] = shape_counts.get(tag, 0) + 1
                
                # Extract colors
                fill = elem.get('fill', '')
                stroke = elem.get('stroke', '')
                if fill and fill != 'none':
                    colors.add(fill)
                if stroke and stroke != 'none':
                    colors.add(stroke)
            
            elif tag in ['linearGradient', 'radialGradient']:
                analysis['has_gradients'] = True
        
        analysis['color_count'] = len(colors)
        analysis['dominant_shapes'] = sorted(shape_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Determine pattern type
        if analysis['element_count'] <= 2 and not analysis['has_gradients']:
            analysis['is_simple_texture'] = True
        elif analysis['element_count'] <= 5 and any(shape in ['rect', 'circle'] for shape, _ in analysis['dominant_shapes']):
            analysis['is_geometric'] = True
        
        # Calculate complexity
        analysis['complexity_score'] = (
            analysis['element_count'] * 2 +
            analysis['color_count'] * 1.5 +
            (10 if analysis['has_gradients'] else 0)
        )
        
        return analysis
    
    def _convert_simple_pattern(self, element: ET.Element, analysis: Dict[str, Any], context: ConversionContext) -> str:
        """Convert simple patterns to PowerPoint texture fills."""
        # For simple patterns, use a basic texture approach
        pattern_color = self._extract_pattern_color(element)
        if pattern_color:
            return f'<a:solidFill><a:srgbClr val="{pattern_color}"/></a:solidFill>'
        
        # Fallback to default color
        return '<a:solidFill><a:srgbClr val="808080"/></a:solidFill>'
    
    def _convert_geometric_pattern(self, element: ET.Element, analysis: Dict[str, Any], context: ConversionContext) -> str:
        """Convert geometric patterns to PowerPoint pattern fills."""
        # Map common geometric patterns to PowerPoint presets
        if analysis['dominant_shapes']:
            dominant_shape = analysis['dominant_shapes'][0][0]
            
            pattern_color = self._extract_pattern_color(element) or "808080"
            
            if dominant_shape == 'rect':
                # Use a checkerboard-like pattern
                return f'''<a:pattFill prst="shingle">
                    <a:fgClr><a:srgbClr val="{pattern_color}"/></a:fgClr>
                    <a:bgClr><a:srgbClr val="FFFFFF"/></a:bgClr>
                </a:pattFill>'''
            
            elif dominant_shape == 'circle':
                # Use a dotted pattern
                return f'''<a:pattFill prst="dotGrid">
                    <a:fgClr><a:srgbClr val="{pattern_color}"/></a:fgClr>
                    <a:bgClr><a:srgbClr val="FFFFFF"/></a:bgClr>
                </a:pattFill>'''
        
        # Default geometric pattern
        pattern_color = self._extract_pattern_color(element) or "808080"
        return f'''<a:pattFill prst="diagBrick">
            <a:fgClr><a:srgbClr val="{pattern_color}"/></a:fgClr>
            <a:bgClr><a:srgbClr val="FFFFFF"/></a:bgClr>
        </a:pattFill>'''
    
    def _convert_gradient_pattern(self, element: ET.Element, analysis: Dict[str, Any], context: ConversionContext) -> str:
        """Convert patterns with gradients to PowerPoint gradient fills."""
        # Find gradient elements in pattern
        gradients = element.xpath('.//linearGradient | .//radialGradient')
        
        if gradients:
            # Convert the first gradient found
            gradient_elem = gradients[0]
            return self.convert(gradient_elem, context)
        
        # Fallback if no gradients found despite analysis
        pattern_color = self._extract_pattern_color(element) or "808080"
        return f'<a:solidFill><a:srgbClr val="{pattern_color}"/></a:solidFill>'
    
    def _convert_complex_pattern(self, element: ET.Element, analysis: Dict[str, Any], context: ConversionContext) -> str:
        """Convert complex patterns by generating a representative texture."""
        # For complex patterns, fall back to a textured fill
        # This would ideally generate an image texture, but for now use pattern fill
        
        pattern_color = self._extract_pattern_color(element) or "808080"
        
        # Choose pattern based on complexity
        if analysis['complexity_score'] > 15:
            preset = "weave"
        elif analysis['complexity_score'] > 10:
            preset = "zigZag"
        else:
            preset = "cross"
        
        return f'''<a:pattFill prst="{preset}">
            <a:fgClr><a:srgbClr val="{pattern_color}"/></a:fgClr>
            <a:bgClr><a:srgbClr val="FFFFFF"/></a:bgClr>
        </a:pattFill>'''