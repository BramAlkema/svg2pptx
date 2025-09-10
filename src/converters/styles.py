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
from lxml import etree as ET
import re
from .base import ConversionContext
from .gradients import GradientConverter
from ..colors import ColorParser


class StyleProcessor:
    """Processes SVG styles and converts them to DrawingML properties"""
    
    def __init__(self):
        self.gradient_converter = GradientConverter()
        self.color_parser = ColorParser()
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
        color_info = self.color_parser.parse(fill_value)
        if color_info:
            if fill_opacity < 1.0:
                alpha = int(fill_opacity * 100000)
                return f'<a:solidFill><a:srgbClr val="{color_info.hex}" alpha="{alpha}"/></a:solidFill>'
            else:
                return f'<a:solidFill><a:srgbClr val="{color_info.hex}"/></a:solidFill>'
        
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
            color_info = self.color_parser.parse(stroke_value)
            if color_info:
                if stroke_opacity < 1.0:
                    alpha = int(stroke_opacity * 100000)
                    stroke_fill = f'<a:solidFill><a:srgbClr val="{color_info.hex}" alpha="{alpha}"/></a:solidFill>'
                else:
                    stroke_fill = f'<a:solidFill><a:srgbClr val="{color_info.hex}"/></a:solidFill>'
        
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