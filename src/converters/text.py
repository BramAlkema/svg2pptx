"""
SVG Text to DrawingML Converter

Handles SVG text elements with support for:
- Basic text content and positioning
- Font family, size, weight, style
- Text anchoring (start, middle, end)
- Text decorations (underline, strikethrough)
- Multi-line text with tspan elements
- Text paths (basic support)
"""

from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET
from .base import BaseConverter, ConversionContext


class TextConverter(BaseConverter):
    """Converts SVG text elements to DrawingML text shapes"""
    
    supported_elements = ['text', 'tspan']
    
    # Font weight mappings
    FONT_WEIGHTS = {
        'normal': '400',
        'bold': '700',
        'bolder': '800',
        'lighter': '200',
        '100': '100', '200': '200', '300': '300', '400': '400', '500': '500',
        '600': '600', '700': '700', '800': '800', '900': '900'
    }
    
    # Text anchor mappings
    TEXT_ANCHORS = {
        'start': 'l',    # left
        'middle': 'ctr', # center
        'end': 'r'       # right
    }
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG text to DrawingML text shape"""
        
        # Get text position
        x = float(element.get('x', '0'))
        y = float(element.get('y', '0'))
        
        # Convert coordinates to EMU
        x_emu = context.coord_system.svg_to_emu_x(x)
        y_emu = context.coord_system.svg_to_emu_y(y)
        
        # Get text content and formatting
        text_content = self._extract_text_content(element)
        if not text_content.strip():
            return ""
        
        # Get text properties
        font_family = self._get_font_family(element)
        font_size = self._get_font_size(element, context)
        font_weight = self._get_font_weight(element)
        font_style = self._get_font_style(element)
        text_anchor = self._get_text_anchor(element)
        text_decoration = self._get_text_decoration(element)
        fill_color = self._get_fill_color(element)
        
        # Calculate text box dimensions (approximate)
        text_width = max(len(text_content) * font_size * 0.6, 100)  # Rough estimation
        text_height = font_size * 1.2  # Line height approximation
        
        # Adjust position based on text anchor
        if text_anchor == 'ctr':
            x_emu -= int(text_width * context.coord_system.pixels_per_inch * 12700 / 2)
        elif text_anchor == 'r':
            x_emu -= int(text_width * context.coord_system.pixels_per_inch * 12700)
        
        # Create text shape
        return f"""<a:sp>
    <a:nvSpPr>
        <a:cNvPr id="{context.get_next_id()}" name="Text"/>
        <a:cNvSpPr txBox="1"/>
    </a:nvSpPr>
    <a:spPr>
        <a:xfrm>
            <a:off x="{x_emu}" y="{y_emu}"/>
            <a:ext cx="{int(text_width * context.coord_system.pixels_per_inch * 12700)}" cy="{int(text_height * context.coord_system.pixels_per_inch * 12700)}"/>
        </a:xfrm>
        <a:prstGeom prst="rect">
            <a:avLst/>
        </a:prstGeom>
        <a:noFill/>
        <a:ln><a:noFill/></a:ln>
    </a:spPr>
    <a:txBody>
        <a:bodyPr wrap="none" rtlCol="0">
            <a:spAutoFit/>
        </a:bodyPr>
        <a:lstStyle/>
        <a:p>
            <a:pPr algn="{text_anchor}"/>
            <a:r>
                <a:rPr lang="en-US" sz="{font_size * 100}" b="{1 if font_weight in ['700', '800', '900', 'bold'] else 0}" i="{1 if font_style == 'italic' else 0}"{' u="sng"' if 'underline' in text_decoration else ''}{' strike="sngStrike"' if 'line-through' in text_decoration else ''}>
                    <a:latin typeface="{font_family}"/>
                    {fill_color}
                </a:rPr>
                <a:t>{self._escape_xml(text_content)}</a:t>
            </a:r>
        </a:p>
    </a:txBody>
</a:sp>"""
    
    def _extract_text_content(self, element: ET.Element) -> str:
        """Extract text content from element including nested tspan elements"""
        text_parts = []
        
        # Add direct text content
        if element.text:
            text_parts.append(element.text.strip())
        
        # Process child elements (mainly tspan)
        for child in element:
            if child.tag.endswith('tspan'):
                if child.text:
                    text_parts.append(child.text.strip())
            if child.tail:
                text_parts.append(child.tail.strip())
        
        return ' '.join(text_parts)
    
    def _get_font_family(self, element: ET.Element) -> str:
        """Get font family from element or inherited styles"""
        # Check direct attribute
        font_family = element.get('font-family')
        if font_family:
            # Clean up font family (remove quotes, get first font)
            font_family = font_family.strip('\'"').split(',')[0].strip()
            return font_family
        
        # Check style attribute
        style = element.get('style', '')
        if 'font-family:' in style:
            for part in style.split(';'):
                if part.strip().startswith('font-family:'):
                    font_family = part.split(':', 1)[1].strip()
                    return font_family.strip('\'"').split(',')[0].strip()
        
        return 'Arial'  # Default font
    
    def _get_font_size(self, element: ET.Element, context: ConversionContext) -> int:
        """Get font size in points"""
        # Check direct attribute
        font_size = element.get('font-size')
        if font_size:
            return self._parse_font_size(font_size, context)
        
        # Check style attribute
        style = element.get('style', '')
        if 'font-size:' in style:
            for part in style.split(';'):
                if part.strip().startswith('font-size:'):
                    font_size = part.split(':', 1)[1].strip()
                    return self._parse_font_size(font_size, context)
        
        return 12  # Default font size
    
    def _parse_font_size(self, font_size: str, context: ConversionContext) -> int:
        """Parse font size with units using Universal Unit Converter"""
        try:
            # Convert to pixels first using Universal Unit Converter
            pixels = context.to_pixels(font_size)
            # Convert pixels to points for PowerPoint (using context's DPI)
            points = pixels * 72.0 / context.viewport_context.dpi
            return int(points)
        except:
            return 12  # Default font size in points
    
    def _get_font_weight(self, element: ET.Element) -> str:
        """Get font weight"""
        # Check direct attribute
        font_weight = element.get('font-weight', 'normal')
        if font_weight in self.FONT_WEIGHTS:
            return self.FONT_WEIGHTS[font_weight]
        
        # Check style attribute
        style = element.get('style', '')
        if 'font-weight:' in style:
            for part in style.split(';'):
                if part.strip().startswith('font-weight:'):
                    weight = part.split(':', 1)[1].strip()
                    return self.FONT_WEIGHTS.get(weight, '400')
        
        return '400'  # Normal weight
    
    def _get_font_style(self, element: ET.Element) -> str:
        """Get font style (normal, italic)"""
        # Check direct attribute
        font_style = element.get('font-style', 'normal')
        if font_style in ['italic', 'oblique']:
            return 'italic'
        
        # Check style attribute
        style = element.get('style', '')
        if 'font-style:' in style:
            for part in style.split(';'):
                if part.strip().startswith('font-style:'):
                    style_val = part.split(':', 1)[1].strip()
                    return 'italic' if style_val in ['italic', 'oblique'] else 'normal'
        
        return 'normal'
    
    def _get_text_anchor(self, element: ET.Element) -> str:
        """Get text anchor alignment"""
        # Check direct attribute
        text_anchor = element.get('text-anchor', 'start')
        return self.TEXT_ANCHORS.get(text_anchor, 'l')
    
    def _get_text_decoration(self, element: ET.Element) -> List[str]:
        """Get text decorations (underline, line-through)"""
        decorations = []
        
        # Check direct attribute
        text_decoration = element.get('text-decoration', '')
        if text_decoration:
            decorations.extend(text_decoration.split())
        
        # Check style attribute
        style = element.get('style', '')
        if 'text-decoration:' in style:
            for part in style.split(';'):
                if part.strip().startswith('text-decoration:'):
                    decoration_val = part.split(':', 1)[1].strip()
                    decorations.extend(decoration_val.split())
        
        return decorations
    
    def _get_fill_color(self, element: ET.Element) -> str:
        """Get text fill color"""
        # Check direct fill attribute
        fill = element.get('fill')
        if fill and fill != 'none':
            color = self._parse_color(fill)
            if color:
                return f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
        
        # Check style attribute
        style = element.get('style', '')
        if 'fill:' in style:
            for part in style.split(';'):
                if part.strip().startswith('fill:'):
                    fill = part.split(':', 1)[1].strip()
                    if fill and fill != 'none':
                        color = self._parse_color(fill)
                        if color:
                            return f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
        
        # Default black color
        return '<a:solidFill><a:srgbClr val="000000"/></a:solidFill>'
    
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
        
        # Named colors (basic set)
        color_names = {
            'black': '000000', 'white': 'FFFFFF', 'red': 'FF0000',
            'green': '008000', 'blue': '0000FF', 'yellow': 'FFFF00',
            'cyan': '00FFFF', 'magenta': 'FF00FF', 'silver': 'C0C0C0',
            'gray': '808080', 'maroon': '800000', 'olive': '808000',
            'lime': '00FF00', 'aqua': '00FFFF', 'teal': '008080',
            'navy': '000080', 'fuchsia': 'FF00FF', 'purple': '800080'
        }
        
        return color_names.get(color)
    
    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters"""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&apos;'))