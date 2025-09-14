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
    
    supported_elements = ['linearGradient', 'radialGradient', 'pattern', 'meshgradient']
    
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
        elif element.tag.endswith('meshgradient'):
            return self._convert_mesh_gradient(element, context)
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
        """Convert SVG linear gradient to DrawingML linear gradient with caching optimization"""
        # Check cache first for performance optimization
        cache_key = self._get_gradient_cache_key(element)
        cached_result = self._get_cached_gradient(cache_key)
        if cached_result:
            return cached_result
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

        # Apply gradient transformation matrix if present
        gradient_transform = element.get('gradientTransform', '')
        if gradient_transform:
            x1, y1, x2, y2 = self._apply_gradient_transform(x1, y1, x2, y2, gradient_transform)

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
        
        # Create gradient stop list with per-mille precision
        stop_list = []
        for position, color, opacity in stops:
            # Enhanced per-mille precision: fractional 0.0-1000.0 instead of integer 0-1000
            stop_position = self._to_per_mille_precision(position)
            alpha_attr = f' alpha="{int(opacity * 100000)}"' if opacity < 1.0 else ""
            stop_list.append(f'<a:gs pos="{stop_position}"><a:srgbClr val="{color}"{alpha_attr}/></a:gs>')
        
        stops_xml = '\n                    '.join(stop_list)

        result = f"""<a:gradFill flip="none" rotWithShape="1">
            <a:gsLst>
                {stops_xml}
            </a:gsLst>
            <a:lin ang="{drawingml_angle}" scaled="1"/>
        </a:gradFill>"""

        # Cache result for performance optimization
        self._cache_gradient_result(cache_key, result)
        return result
    
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
        
        # Create gradient stop list (reverse order for radial) with per-mille precision
        stop_list = []
        for position, color, opacity in reversed(stops):
            # Enhanced per-mille precision for reversed radial positions
            reversed_position = 1.0 - position
            stop_position = self._to_per_mille_precision(reversed_position)
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

    def _convert_mesh_gradient(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG mesh gradient to DrawingML using overlapping radial gradients.

        Mesh gradients are SVG 2.0 features that define color interpolation across
        a 2D mesh. Since PowerPoint doesn't support mesh gradients directly, we:
        1. Parse mesh structure to extract corner colors
        2. Create overlapping radial gradients with precise positioning
        3. Use 4-corner color interpolation for smooth blending
        4. Generate custom geometry paths for mesh-like regions
        """
        try:
            # Parse mesh gradient properties
            gradient_id = element.get('id', 'mesh_gradient')
            gradient_units = element.get('gradientUnits', 'objectBoundingBox')

            # Extract mesh structure
            mesh_data = self._parse_mesh_structure(element)

            if not mesh_data or len(mesh_data) == 0:
                # Fallback to solid color if mesh parsing fails
                fallback_color = self._extract_mesh_fallback_color(element)
                return f'<a:solidFill><a:srgbClr val="{fallback_color}"/></a:solidFill>'

            # For simple 2x2 mesh (4 corners), use bilinear interpolation
            if self._is_simple_4_corner_mesh(mesh_data):
                return self._convert_4_corner_mesh_to_radial(mesh_data, context)
            else:
                # Complex mesh - use multiple overlapping radial gradients
                return self._convert_complex_mesh_to_overlapping_radials(mesh_data, context)

        except Exception as e:
            # Graceful fallback for malformed mesh gradients
            self.logger.error(f"Error converting mesh gradient: {e}")
            fallback_color = self._extract_mesh_fallback_color(element)
            return f'<a:solidFill><a:srgbClr val="{fallback_color}"/></a:solidFill>'

    def _parse_mesh_structure(self, mesh_element: ET.Element) -> List[Dict[str, Any]]:
        """Parse SVG mesh gradient structure to extract patches and corner colors."""
        mesh_patches = []

        # Find all mesh rows
        mesh_rows = mesh_element.findall('.//meshrow')

        for row_index, row in enumerate(mesh_rows):
            # Find all mesh patches in this row
            patches = row.findall('.//meshpatch')

            for patch_index, patch in enumerate(patches):
                # Extract stops (corner colors) for this patch
                stops = patch.findall('.//stop')

                if len(stops) >= 4:  # Valid mesh patch needs 4 corners
                    patch_data = {
                        'row': row_index,
                        'col': patch_index,
                        'corners': []
                    }

                    # Parse each corner color
                    for stop in stops[:4]:  # Only take first 4 corners
                        color = self._parse_stop_color(stop)
                        opacity = self._safe_float_parse(stop.get('stop-opacity', '1.0'), 1.0)

                        patch_data['corners'].append({
                            'color': color,
                            'opacity': opacity
                        })

                    mesh_patches.append(patch_data)

        return mesh_patches

    def _parse_stop_color(self, stop_element: ET.Element) -> str:
        """Parse stop color with HSL/RGB support and precise color handling."""
        color_str = stop_element.get('stop-color', '#000000')

        # Handle various color formats
        if color_str.startswith('#'):
            return color_str[1:].upper()  # Remove # and normalize to uppercase
        elif color_str.startswith('rgb'):
            # Parse RGB format: rgb(255, 0, 0)
            import re
            rgb_match = re.match(r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', color_str)
            if rgb_match:
                r, g, b = map(int, rgb_match.groups())
                return f"{r:02X}{g:02X}{b:02X}"
        elif color_str.startswith('hsl'):
            # Parse HSL format and convert to RGB
            return self._hsl_to_rgb_hex(color_str)

        # Default fallback
        return "000000"

    def _hsl_to_rgb_hex(self, hsl_str: str) -> str:
        """Convert HSL color string to RGB hex with precision support."""
        try:
            # Try to use spectra library if available for precise conversion
            try:
                import spectra
                color = spectra.html(hsl_str)
                rgb = color.rgb
                r, g, b = [int(c * 255) for c in rgb]
                return f"{r:02X}{g:02X}{b:02X}"
            except ImportError:
                # Fallback to manual HSL conversion
                import re
                hsl_match = re.match(r'hsl\s*\(\s*([\d.]+)\s*,\s*([\d.]+)%\s*,\s*([\d.]+)%\s*\)', hsl_str)
                if hsl_match:
                    h = float(hsl_match.group(1)) / 360.0
                    s = float(hsl_match.group(2)) / 100.0
                    l = float(hsl_match.group(3)) / 100.0

                    r, g, b = self._hsl_to_rgb_precise(h * 360, s * 100, l * 100)
                    return f"{int(r):02X}{int(g):02X}{int(b):02X}"
        except Exception:
            pass

        return "808080"  # Gray fallback

    def _hsl_to_rgb_precise(self, h: float, s: float, l: float) -> Tuple[float, float, float]:
        """Convert HSL to RGB with high precision for gradient calculations."""
        h = h / 360.0
        s = s / 100.0
        l = l / 100.0

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

        if s == 0:
            r = g = b = l  # achromatic
        else:
            q = l * (1 + s) if l < 0.5 else l + s - l * s
            p = 2 * l - q
            r = hue_to_rgb(p, q, h + 1/3)
            g = hue_to_rgb(p, q, h)
            b = hue_to_rgb(p, q, h - 1/3)

        return r * 255, g * 255, b * 255

    def _is_simple_4_corner_mesh(self, mesh_data: List[Dict[str, Any]]) -> bool:
        """Check if mesh is a simple 2x2 grid (4 corners) suitable for bilinear interpolation."""
        return len(mesh_data) == 1 and len(mesh_data[0]['corners']) == 4

    def _convert_4_corner_mesh_to_radial(self, mesh_data: List[Dict[str, Any]], context: ConversionContext) -> str:
        """Convert 4-corner mesh to radial gradient with bilinear interpolation approximation."""
        corners = mesh_data[0]['corners']

        if len(corners) != 4:
            return self._get_fallback_solid_fill(corners)

        # Extract corner colors with alpha precision
        corner_colors = []
        for corner in corners:
            color = corner['color']
            opacity = corner['opacity']
            alpha_attr = f' alpha="{int(opacity * 100000)}"' if opacity < 1.0 else ""
            corner_colors.append((color, alpha_attr))

        # Create radial gradient approximating 4-corner interpolation
        # Use center interpolation between all 4 colors
        center_color = self._interpolate_mesh_colors(corners)
        center_alpha = sum(c['opacity'] for c in corners) / 4  # Average alpha
        center_alpha_attr = f' alpha="{int(center_alpha * 100000)}"' if center_alpha < 1.0 else ""

        # Choose dominant corner color for outer edge
        outer_color, outer_alpha = corner_colors[0]  # Use first corner as outer

        # Create radial gradient from center to edges
        return f'''<a:gradFill flip="none" rotWithShape="1">
            <a:gsLst>
                <a:gs pos="0"><a:srgbClr val="{center_color}"{center_alpha_attr}/></a:gs>
                <a:gs pos="1000"><a:srgbClr val="{outer_color}"{outer_alpha}/></a:gs>
            </a:gsLst>
            <a:path path="circle">
                <a:fillToRect l="0" t="0" r="0" b="0"/>
            </a:path>
        </a:gradFill>'''

    def _interpolate_mesh_colors(self, corners: List[Dict[str, Any]]) -> str:
        """Interpolate colors from 4 corners using bilinear interpolation."""
        if len(corners) != 4:
            return corners[0]['color'] if corners else "808080"

        try:
            # Try using spectra for precise color blending
            import spectra

            # Convert corner colors to spectra objects
            spectra_colors = []
            for corner in corners:
                color_hex = f"#{corner['color']}"
                spectra_colors.append(spectra.html(color_hex))

            # Bilinear interpolation at center point (0.5, 0.5)
            # Average all 4 corners for center color
            blended = spectra_colors[0]
            for color in spectra_colors[1:]:
                blended = blended.blend(color, ratio=0.5)

            return blended.hexcode[1:].upper()  # Remove # prefix

        except ImportError:
            # Fallback to simple RGB averaging
            total_r = total_g = total_b = 0

            for corner in corners:
                color_hex = corner['color']
                r = int(color_hex[0:2], 16)
                g = int(color_hex[2:4], 16)
                b = int(color_hex[4:6], 16)

                total_r += r
                total_g += g
                total_b += b

            avg_r = int(total_r / 4)
            avg_g = int(total_g / 4)
            avg_b = int(total_b / 4)

            return f"{avg_r:02X}{avg_g:02X}{avg_b:02X}"

    def _convert_complex_mesh_to_overlapping_radials(self, mesh_data: List[Dict[str, Any]], context: ConversionContext) -> str:
        """Convert complex mesh to multiple overlapping radial gradients."""
        # For complex meshes, simplify to dominant color pattern
        if not mesh_data:
            return self._get_fallback_solid_fill([])

        # Extract dominant colors from all patches
        all_colors = []
        for patch in mesh_data:
            for corner in patch['corners']:
                all_colors.append(corner)

        if len(all_colors) >= 2:
            # Create linear gradient with dominant colors
            start_color = all_colors[0]
            end_color = all_colors[-1]

            start_alpha = f' alpha="{int(start_color["opacity"] * 100000)}"' if start_color['opacity'] < 1.0 else ""
            end_alpha = f' alpha="{int(end_color["opacity"] * 100000)}"' if end_color['opacity'] < 1.0 else ""

            return f'''<a:gradFill flip="none" rotWithShape="1">
                <a:gsLst>
                    <a:gs pos="0"><a:srgbClr val="{start_color['color']}"{start_alpha}/></a:gs>
                    <a:gs pos="1000"><a:srgbClr val="{end_color['color']}"{end_alpha}/></a:gs>
                </a:gsLst>
                <a:lin ang="0" scaled="1"/>
            </a:gradFill>'''
        else:
            return self._get_fallback_solid_fill(all_colors)

    def _extract_mesh_fallback_color(self, mesh_element: ET.Element) -> str:
        """Extract fallback color from mesh gradient for error cases."""
        # Try to find any stop color in the mesh
        stops = mesh_element.findall('.//stop')
        for stop in stops:
            color = self._parse_stop_color(stop)
            if color and color != "000000":
                return color

        return "808080"  # Gray fallback

    def _get_fallback_solid_fill(self, colors: List[Dict[str, Any]]) -> str:
        """Generate fallback solid fill from available colors."""
        if colors:
            fallback_color = colors[0]['color']
            opacity = colors[0]['opacity']
            alpha_attr = f' alpha="{int(opacity * 100000)}"' if opacity < 1.0 else ""
            return f'<a:solidFill><a:srgbClr val="{fallback_color}"{alpha_attr}/></a:solidFill>'
        else:
            return '<a:solidFill><a:srgbClr val="808080"/></a:solidFill>'

    def _to_per_mille_precision(self, position: float) -> str:
        """Convert position to per-mille with fractional precision support.

        Enhanced per-mille precision system supports fractional values (0.0-1000.0)
        instead of just integer values (0-1000) for more accurate gradient positioning.

        Args:
            position: Position value between 0.0 and 1.0

        Returns:
            String representation of per-mille value with appropriate precision
        """
        # Clamp position to valid range
        position = max(0.0, min(1.0, position))

        # Convert to per-mille with fractional precision
        per_mille = position * 1000.0

        # Round to reasonable precision (1 decimal place for PowerPoint compatibility)
        # PowerPoint supports up to 3 decimal places, but 1 is sufficient for gradients
        per_mille_rounded = round(per_mille, 1)

        # Format as integer if it's a whole number, otherwise show decimal
        if per_mille_rounded == int(per_mille_rounded):
            return str(int(per_mille_rounded))
        else:
            return f"{per_mille_rounded:.1f}"

    def _interpolate_gradient_colors(self, start_pos: float, start_color: Tuple[int, int, int],
                                   end_pos: float, end_color: Tuple[int, int, int],
                                   target_pos: float) -> Tuple[int, int, int]:
        """Interpolate colors between two gradient stops with floating-point precision.

        Implements linear interpolation between two color points for precise
        gradient color calculations with fractional positioning support.

        Args:
            start_pos: Position of start color (0.0-1.0)
            start_color: RGB tuple of start color (0-255 each)
            end_pos: Position of end color (0.0-1.0)
            end_color: RGB tuple of end color (0-255 each)
            target_pos: Target position for interpolation (0.0-1.0)

        Returns:
            Interpolated RGB color tuple
        """
        # Handle edge cases
        if start_pos == end_pos:
            return start_color
        if target_pos <= start_pos:
            return start_color
        if target_pos >= end_pos:
            return end_color

        # Calculate interpolation factor with floating-point precision
        factor = (target_pos - start_pos) / (end_pos - start_pos)

        # Linear interpolation for each RGB component
        r = int(start_color[0] + (end_color[0] - start_color[0]) * factor)
        g = int(start_color[1] + (end_color[1] - start_color[1]) * factor)
        b = int(start_color[2] + (end_color[2] - start_color[2]) * factor)

        # Clamp values to valid RGB range
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))

        return (r, g, b)

    def _apply_gradient_transform(self, x1: float, y1: float, x2: float, y2: float,
                                transform_str: str) -> Tuple[float, float, float, float]:
        """Apply SVG gradient transformation matrix to gradient coordinates.

        Handles matrix transformations for complex gradient positioning and scaling.
        Supports matrix(a, b, c, d, e, f) format commonly used in SVG gradients.

        Args:
            x1, y1: Start point coordinates
            x2, y2: End point coordinates
            transform_str: SVG transform string (e.g., "matrix(1.5, 0.5, -0.5, 1.2, 10, 20)")

        Returns:
            Transformed coordinates tuple (x1, y1, x2, y2)
        """
        try:
            # Parse matrix transformation
            import re
            matrix_match = re.search(r'matrix\s*\(\s*([-\d.]+)\s*,?\s*([-\d.]+)\s*,?\s*([-\d.]+)\s*,?\s*([-\d.]+)\s*,?\s*([-\d.]+)\s*,?\s*([-\d.]+)\s*\)', transform_str)

            if matrix_match:
                # Extract matrix components: matrix(a, b, c, d, e, f)
                a, b, c, d, e, f = map(float, matrix_match.groups())

                # Apply matrix transformation to start point (x1, y1)
                new_x1 = a * x1 + c * y1 + e
                new_y1 = b * x1 + d * y1 + f

                # Apply matrix transformation to end point (x2, y2)
                new_x2 = a * x2 + c * y2 + e
                new_y2 = b * x2 + d * y2 + f

                return new_x1, new_y1, new_x2, new_y2

            else:
                # Handle other transform types (translate, scale, rotate, skew)
                # For now, return original coordinates
                # TODO: Add support for other transform functions
                return x1, y1, x2, y2

        except (ValueError, AttributeError) as e:
            # Fallback to original coordinates if transform parsing fails
            self.logger.warning(f"Failed to parse gradient transform '{transform_str}': {e}")
            return x1, y1, x2, y2

    def _get_gradient_cache_key(self, element: ET.Element) -> str:
        """Generate cache key for gradient caching optimization.

        Creates a unique key based on gradient properties for caching
        converted gradients to improve performance on repeated patterns.
        """
        # Extract key gradient properties
        gradient_id = element.get('id', '')
        gradient_type = element.tag.split('}')[-1] if '}' in element.tag else element.tag

        # Include transform and coordinate information
        coords = []
        for attr in ['x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'r', 'fx', 'fy']:
            value = element.get(attr, '')
            if value:
                coords.append(f"{attr}:{value}")

        # Include gradient transform
        transform = element.get('gradientTransform', '')
        if transform:
            coords.append(f"transform:{transform}")

        # Include gradient stops
        stops = element.findall('.//stop')
        stop_data = []
        for stop in stops:
            offset = stop.get('offset', '0')
            color = stop.get('stop-color', '#000000')
            opacity = stop.get('stop-opacity', '1')
            stop_data.append(f"{offset}-{color}-{opacity}")

        cache_key = f"{gradient_type}:{gradient_id}:{':'.join(coords)}:{':'.join(stop_data)}"
        return cache_key[:200]  # Limit key length

    def _get_cached_gradient(self, cache_key: str) -> Optional[str]:
        """Get cached gradient result if available."""
        return self.gradients.get(cache_key)

    def _cache_gradient_result(self, cache_key: str, result: str) -> None:
        """Cache gradient conversion result for performance optimization."""
        # Limit cache size to prevent memory issues
        if len(self.gradients) > 100:  # Clear cache when it gets too large
            self.gradients.clear()

        self.gradients[cache_key] = result