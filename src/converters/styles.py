"""
SVG Style and Attribute Processor

Handles SVG styling with support for:
- CSS style attributes
- Inline style properties
- Presentation attributes (fill, stroke, etc.)
- Inherited styles from parent elements
- CSS selectors and cascade rules (basic support)
- Color parsing and conversion
"""

from typing import Dict, Any, Optional, List, Tuple
import xml.etree.ElementTree as ET
import re
from .base import BaseConverter, ConversionContext
from .gradients import GradientConverter


class StyleProcessor:
    """Processes SVG styles and converts them to DrawingML properties"""
    
    def __init__(self):
        self.gradient_converter = GradientConverter()
        self.css_rules = {}  # Store CSS rules from <style> elements
    
    def process_element_styles(self, element: ET.Element, context: ConversionContext) -> Dict[str, Any]:
        """Process all styles for an element and return DrawingML properties"""
        # Collect styles from various sources
        styles = {}
        
        # 1. Inherited styles (simplified - walk up parent chain)
        styles.update(self._get_inherited_styles(element))
        
        # 2. CSS rules from <style> elements
        styles.update(self._get_css_styles(element, context))
        
        # 3. Presentation attributes
        styles.update(self._get_presentation_attributes(element))
        
        # 4. Inline style attribute (highest priority)
        styles.update(self._parse_style_attribute(element.get('style', '')))
        
        # Convert to DrawingML properties
        return self._convert_to_drawingml(styles, element, context)
    
    def _get_inherited_styles(self, element: ET.Element) -> Dict[str, str]:
        """Get inherited styles from parent elements"""
        inherited = {}
        
        # Properties that inherit by default
        inheritable_props = {
            'color', 'font-family', 'font-size', 'font-weight', 'font-style',
            'text-anchor', 'direction', 'writing-mode', 'opacity'
        }
        
        # Walk up the parent chain
        parent = element.getparent() if hasattr(element, 'getparent') else None
        while parent is not None:
            # Check parent's style attribute
            parent_styles = self._parse_style_attribute(parent.get('style', ''))
            for prop, value in parent_styles.items():
                if prop in inheritable_props and prop not in inherited:
                    inherited[prop] = value
            
            # Check parent's presentation attributes
            for attr_name, attr_value in parent.attrib.items():
                if attr_name in inheritable_props and attr_name not in inherited:
                    inherited[attr_name] = attr_value
            
            parent = parent.getparent() if hasattr(parent, 'getparent') else None
        
        return inherited
    
    def _get_css_styles(self, element: ET.Element, context: ConversionContext) -> Dict[str, str]:
        """Get styles from CSS rules (simplified CSS selector matching)"""
        styles = {}
        
        # Get element tag name and attributes for matching
        tag_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        element_id = element.get('id', '')
        element_class = element.get('class', '')
        
        # Match CSS rules (simplified)
        for selector, rule_styles in self.css_rules.items():
            if self._matches_selector(selector, tag_name, element_id, element_class):
                styles.update(rule_styles)
        
        return styles
    
    def _matches_selector(self, selector: str, tag_name: str, element_id: str, element_class: str) -> bool:
        """Simple CSS selector matching"""
        selector = selector.strip()
        
        # Element selector
        if selector == tag_name:
            return True
        
        # ID selector
        if selector.startswith('#') and selector[1:] == element_id:
            return True
        
        # Class selector
        if selector.startswith('.') and selector[1:] in element_class.split():
            return True
        
        # Universal selector
        if selector == '*':
            return True
        
        return False
    
    def _get_presentation_attributes(self, element: ET.Element) -> Dict[str, str]:
        """Get SVG presentation attributes"""
        presentation_attrs = {
            'fill', 'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin',
            'stroke-dasharray', 'stroke-opacity', 'fill-opacity', 'opacity',
            'font-family', 'font-size', 'font-weight', 'font-style',
            'text-anchor', 'text-decoration', 'visibility', 'display'
        }
        
        styles = {}
        for attr_name, attr_value in element.attrib.items():
            if attr_name in presentation_attrs:
                styles[attr_name] = attr_value
        
        return styles
    
    def _parse_style_attribute(self, style_str: str) -> Dict[str, str]:
        """Parse CSS style attribute string"""
        styles = {}
        if not style_str:
            return styles
        
        # Split by semicolon and parse each property
        for prop_str in style_str.split(';'):
            prop_str = prop_str.strip()
            if ':' in prop_str:
                prop_name, prop_value = prop_str.split(':', 1)
                styles[prop_name.strip()] = prop_value.strip()
        
        return styles
    
    def _convert_to_drawingml(self, styles: Dict[str, str], element: ET.Element, context: ConversionContext) -> Dict[str, Any]:
        """Convert CSS styles to DrawingML properties"""
        drawingml_props = {}
        
        # Process fill
        fill_xml = self._process_fill(styles, element, context)
        if fill_xml:
            drawingml_props['fill'] = fill_xml
        
        # Process stroke
        stroke_xml = self._process_stroke(styles, context)
        if stroke_xml:
            drawingml_props['stroke'] = stroke_xml
        
        # Process opacity
        opacity = self._get_opacity(styles)
        if opacity < 1.0:
            drawingml_props['opacity'] = opacity
        
        # Process other properties
        if 'visibility' in styles and styles['visibility'] == 'hidden':
            drawingml_props['hidden'] = True
        
        return drawingml_props
    
    def _process_fill(self, styles: Dict[str, str], element: ET.Element, context: ConversionContext) -> Optional[str]:
        """Process fill styles and return DrawingML fill XML"""
        fill_value = styles.get('fill', 'black')
        fill_opacity = float(styles.get('fill-opacity', '1'))
        
        if fill_value == 'none':
            return '<a:noFill/>'
        
        # Handle URL references (gradients, patterns)
        if fill_value.startswith('url(#') and fill_value.endswith(')'):
            gradient_fill = self.gradient_converter.get_fill_from_url(fill_value, context)
            if gradient_fill:
                # Apply opacity to gradient if needed
                if fill_opacity < 1.0:
                    # This is simplified - proper gradient opacity requires modifying each stop
                    return gradient_fill
                return gradient_fill
        
        # Solid color fill
        color_hex = self._parse_color(fill_value)
        if color_hex:
            if fill_opacity < 1.0:
                alpha = int(fill_opacity * 100000)
                return f'<a:solidFill><a:srgbClr val="{color_hex}" alpha="{alpha}"/></a:solidFill>'
            else:
                return f'<a:solidFill><a:srgbClr val="{color_hex}"/></a:solidFill>'
        
        return None
    
    def _process_stroke(self, styles: Dict[str, str], context: ConversionContext) -> Optional[str]:
        """Process stroke styles and return DrawingML line XML"""
        stroke_value = styles.get('stroke')
        if not stroke_value or stroke_value == 'none':
            return '<a:ln><a:noFill/></a:ln>'
        
        stroke_width = styles.get('stroke-width', '1')
        stroke_opacity = float(styles.get('stroke-opacity', '1'))
        stroke_linecap = styles.get('stroke-linecap', 'butt')
        stroke_linejoin = styles.get('stroke-linejoin', 'miter')
        stroke_dasharray = styles.get('stroke-dasharray', '')
        
        # Parse stroke width (convert to EMU)
        width_emu = self._parse_length_to_emu(stroke_width, context)
        
        # Parse stroke color
        stroke_fill = ''
        if stroke_value.startswith('url(#') and stroke_value.endswith(')'):
            # Gradient stroke
            gradient_fill = self.gradient_converter.get_fill_from_url(stroke_value, context)
            if gradient_fill:
                stroke_fill = gradient_fill
        else:
            # Solid color stroke
            color_hex = self._parse_color(stroke_value)
            if color_hex:
                if stroke_opacity < 1.0:
                    alpha = int(stroke_opacity * 100000)
                    stroke_fill = f'<a:solidFill><a:srgbClr val="{color_hex}" alpha="{alpha}"/></a:solidFill>'
                else:
                    stroke_fill = f'<a:solidFill><a:srgbClr val="{color_hex}"/></a:solidFill>'
        
        # Line caps
        cap_map = {'butt': 'flat', 'round': 'rnd', 'square': 'sq'}
        cap = cap_map.get(stroke_linecap, 'flat')
        
        # Line joins  
        join_map = {'miter': 'miter', 'round': 'round', 'bevel': 'bevel'}
        join = join_map.get(stroke_linejoin, 'miter')
        
        # Dash pattern
        dash_xml = ''
        if stroke_dasharray and stroke_dasharray != 'none':
            dash_xml = self._create_dash_pattern(stroke_dasharray)
        
        return f"""<a:ln w="{width_emu}" cap="{cap}">
    {stroke_fill}
    {dash_xml}
    <a:miter lim="800000"/>
    <a:headEnd type="none" w="med" len="med"/>
    <a:tailEnd type="none" w="med" len="med"/>
</a:ln>"""
    
    def _create_dash_pattern(self, dasharray: str) -> str:
        """Create DrawingML dash pattern from SVG stroke-dasharray"""
        # Parse dash array
        dashes = []
        for dash in re.split(r'[,\s]+', dasharray.strip()):
            if dash:
                try:
                    dashes.append(float(dash))
                except ValueError:
                    continue
        
        if not dashes:
            return ''
        
        # Convert to DrawingML dash pattern (simplified)
        if len(dashes) == 2:
            # Simple dash-gap pattern
            dash_len = int(dashes[0] * 1000)  # Convert to per-mille
            gap_len = int(dashes[1] * 1000)
            
            if dash_len <= 300 and gap_len <= 300:
                return '<a:prstDash val="dot"/>'
            elif dash_len <= 800:
                return '<a:prstDash val="dash"/>'
            else:
                return '<a:prstDash val="lgDash"/>'
        
        return '<a:prstDash val="dash"/>'  # Default to dash
    
    def _get_opacity(self, styles: Dict[str, str]) -> float:
        """Get element opacity"""
        opacity_str = styles.get('opacity', '1')
        try:
            return float(opacity_str)
        except ValueError:
            return 1.0
    
    def _parse_length_to_emu(self, length_str: str, context: ConversionContext) -> int:
        """Parse CSS length value to EMU using Universal Unit Converter"""
        # Use the context's universal unit converter for accurate conversion
        return context.to_emu(length_str)
    
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
        
        # Named colors (basic set)
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
    
    def parse_css_from_style_element(self, style_element: ET.Element):
        """Parse CSS rules from <style> element"""
        css_text = style_element.text or ''
        
        # Remove comments
        css_text = re.sub(r'/\*.*?\*/', '', css_text, flags=re.DOTALL)
        
        # Parse simple CSS rules
        rule_pattern = r'([^{]+)\{([^}]+)\}'
        for match in re.finditer(rule_pattern, css_text):
            selectors = match.group(1).strip()
            properties = match.group(2).strip()
            
            # Parse properties
            rule_styles = {}
            for prop in properties.split(';'):
                prop = prop.strip()
                if ':' in prop:
                    prop_name, prop_value = prop.split(':', 1)
                    rule_styles[prop_name.strip()] = prop_value.strip()
            
            # Store for each selector
            for selector in selectors.split(','):
                self.css_rules[selector.strip()] = rule_styles