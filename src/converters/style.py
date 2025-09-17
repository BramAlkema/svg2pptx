"""
StyleConverter for handling SVG <style> elements.
Processes CSS styles and applies them to SVG elements.
"""

from lxml import etree as ET
import re
from typing import Dict, List, Optional, Tuple
from .base import BaseConverter, ConversionContext
from ..services.conversion_services import ConversionServices


class StyleConverter(BaseConverter):
    """Converter for SVG style elements containing CSS."""

    supported_elements = ['style']

    def __init__(self, services: ConversionServices):
        super().__init__(services)
        self.parsed_styles: Dict[str, Dict[str, str]] = {}
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the element."""
        tag = self.get_element_tag(element)
        return tag == 'style'
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG style element by parsing CSS and storing rules."""
        # Get CSS content
        css_content = element.text or ""
        if not css_content.strip():
            return '<!-- Empty style element -->'
        
        # Parse CSS rules
        rules = self._parse_css(css_content)
        
        # Store parsed styles in context for other converters to use
        if hasattr(context, 'css_styles'):
            context.css_styles.update(rules)
        else:
            context.css_styles = rules
        
        # Style elements don't generate direct DrawingML output
        return f'<!-- Processed {len(rules)} CSS rules -->'
    
    def _parse_css(self, css_content: str) -> Dict[str, Dict[str, str]]:
        """Parse CSS content and return selector -> properties mapping."""
        rules = {}
        
        # Remove comments
        css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
        
        # Split into rules (simple parser)
        rule_pattern = r'([^{]+)\{([^}]+)\}'
        matches = re.findall(rule_pattern, css_content)
        
        for selector_group, properties_text in matches:
            # Handle multiple selectors separated by commas
            selectors = [s.strip() for s in selector_group.split(',')]
            
            # Parse properties
            properties = self._parse_properties(properties_text)
            
            # Store for each selector
            for selector in selectors:
                if selector:
                    rules[selector] = properties
        
        return rules
    
    def _parse_properties(self, properties_text: str) -> Dict[str, str]:
        """Parse CSS properties from a rule block."""
        properties = {}
        
        # Split by semicolons and parse key-value pairs
        for prop in properties_text.split(';'):
            prop = prop.strip()
            if ':' in prop:
                key, value = prop.split(':', 1)
                properties[key.strip()] = value.strip()
        
        return properties
    
    def get_element_styles(self, element: ET.Element, context: ConversionContext) -> Dict[str, str]:
        """Get CSS styles that apply to a specific element."""
        if not hasattr(context, 'css_styles'):
            return {}
        
        element_styles = {}
        
        # Get element information
        tag_name = self.get_element_tag(element)
        element_id = element.get('id', '')
        element_classes = element.get('class', '').split()
        
        # Check for matching selectors in order of specificity
        css_styles = context.css_styles
        
        # 1. Type selectors (e.g., "rect", "circle")
        if tag_name in css_styles:
            element_styles.update(css_styles[tag_name])
        
        # 2. Class selectors (e.g., ".my-class")
        for class_name in element_classes:
            class_selector = f'.{class_name}'
            if class_selector in css_styles:
                element_styles.update(css_styles[class_selector])
        
        # 3. ID selectors (e.g., "#my-id") - highest specificity
        if element_id:
            id_selector = f'#{element_id}'
            if id_selector in css_styles:
                element_styles.update(css_styles[id_selector])
        
        # 4. Attribute selectors (basic support)
        for selector in css_styles:
            if self._matches_attribute_selector(selector, element):
                element_styles.update(css_styles[selector])
        
        return element_styles
    
    def _matches_attribute_selector(self, selector: str, element: ET.Element) -> bool:
        """Check if an attribute selector matches the element."""
        # Simple attribute selector support: [attribute], [attribute="value"]
        attr_pattern = r'\[([^=\]]+)(?:="([^"]+)")?\]'
        match = re.search(attr_pattern, selector)
        
        if not match:
            return False
        
        attr_name, attr_value = match.groups()
        
        if attr_value:
            # [attribute="value"]
            return element.get(attr_name) == attr_value
        else:
            # [attribute] - just check presence
            return attr_name in element.attrib
    
    def apply_css_styles(self, element: ET.Element, context: ConversionContext) -> None:
        """Apply CSS styles to an element by setting attributes."""
        css_styles = self.get_element_styles(element, context)
        
        if not css_styles:
            return
        
        # Map CSS properties to SVG attributes
        css_to_svg_mapping = {
            'fill': 'fill',
            'stroke': 'stroke',
            'stroke-width': 'stroke-width',
            'stroke-dasharray': 'stroke-dasharray',
            'stroke-linecap': 'stroke-linecap',
            'stroke-linejoin': 'stroke-linejoin',
            'opacity': 'opacity',
            'fill-opacity': 'fill-opacity',
            'stroke-opacity': 'stroke-opacity',
            'font-family': 'font-family',
            'font-size': 'font-size',
            'font-weight': 'font-weight',
            'font-style': 'font-style',
            'text-anchor': 'text-anchor',
            'visibility': 'visibility',
            'display': 'display'
        }
        
        # Apply CSS properties as SVG attributes
        for css_prop, svg_attr in css_to_svg_mapping.items():
            if css_prop in css_styles:
                # Only set if not already present as attribute (attributes have higher precedence)
                if svg_attr not in element.attrib:
                    element.set(svg_attr, css_styles[css_prop])
    
    def merge_css_with_attributes(self, element: ET.Element, context: ConversionContext) -> Dict[str, str]:
        """Merge CSS styles with element attributes, with attributes taking precedence."""
        css_styles = self.get_element_styles(element, context)
        
        # Start with CSS styles
        merged = css_styles.copy()
        
        # Override with element attributes (higher precedence)
        svg_properties = [
            'fill', 'stroke', 'stroke-width', 'stroke-dasharray', 'stroke-linecap',
            'stroke-linejoin', 'opacity', 'fill-opacity', 'stroke-opacity',
            'font-family', 'font-size', 'font-weight', 'font-style', 'text-anchor',
            'visibility', 'display'
        ]
        
        for prop in svg_properties:
            if prop in element.attrib:
                merged[prop] = element.get(prop)
        
        return merged
    
    def get_computed_style_value(self, element: ET.Element, property_name: str, 
                                context: ConversionContext, default: str = '') -> str:
        """Get computed style value for a property, considering CSS and attributes."""
        # Check element attribute first (highest precedence)
        if property_name in element.attrib:
            return element.get(property_name)
        
        # Check CSS styles
        css_styles = self.get_element_styles(element, context)
        if property_name in css_styles:
            return css_styles[property_name]
        
        # Return default
        return default
    
    def _normalize_selector(self, selector: str) -> str:
        """Normalize selector for consistent matching."""
        # Remove extra whitespace and normalize
        return ' '.join(selector.split())
    
    def _calculate_specificity(self, selector: str) -> Tuple[int, int, int]:
        """Calculate CSS specificity (IDs, classes, elements)."""
        id_count = len(re.findall(r'#[^.#\s\[]+', selector))
        class_count = len(re.findall(r'\.[^.#\s\[]+', selector))
        element_count = len(re.findall(r'[^.#\s\[]+(?:\[[^\]]*\])?', selector))
        
        return (id_count, class_count, element_count)