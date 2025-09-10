"""
Core preprocessing plugins ported from SVGO.
"""

import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set
from .base import PreprocessingPlugin, PreprocessingContext


class CleanupAttrsPlugin(PreprocessingPlugin):
    """Clean up attributes from newlines, trailing and repeating spaces."""
    
    name = "cleanupAttrs"
    description = "cleanups attributes from newlines, trailing and repeating spaces"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return len(element.attrib) > 0
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        modified = False
        for key, value in list(element.attrib.items()):
            # Remove newlines, excessive whitespace
            cleaned = re.sub(r'\s+', ' ', value.strip())
            if cleaned != value:
                element.set(key, cleaned)
                modified = True
        
        if modified:
            context.record_modification(self.name, "cleaned_attrs")
        return modified


class CleanupNumericValuesPlugin(PreprocessingPlugin):
    """Round numeric values to fixed precision, remove default 'px' units."""
    
    name = "cleanupNumericValues"
    description = "rounds numeric values to the fixed precision, removes default 'px' units"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return True
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        modified = False
        numeric_attrs = {
            'x', 'y', 'width', 'height', 'cx', 'cy', 'r', 'rx', 'ry',
            'x1', 'y1', 'x2', 'y2', 'stroke-width', 'font-size'
        }
        
        for attr in numeric_attrs:
            if attr in element.attrib:
                value = element.attrib[attr]
                cleaned = self._clean_numeric_value(value, context.precision)
                if cleaned != value:
                    element.set(attr, cleaned)
                    modified = True
        
        # Clean up path data
        if element.tag.endswith('path') and 'd' in element.attrib:
            path_data = element.attrib['d']
            cleaned_path = self._clean_path_data(path_data, context.precision)
            if cleaned_path != path_data:
                element.set('d', cleaned_path)
                modified = True
        
        if modified:
            context.record_modification(self.name, "cleaned_numeric")
        return modified
    
    def _clean_numeric_value(self, value: str, precision: int) -> str:
        """Clean a single numeric value."""
        # Remove 'px' units
        value = value.replace('px', '')
        
        try:
            # Try to parse as float and round
            num = float(value)
            if num.is_integer():
                return str(int(num))
            else:
                return f"{num:.{precision}f}".rstrip('0').rstrip('.')
        except ValueError:
            return value
    
    def _clean_path_data(self, path_data: str, precision: int) -> str:
        """Clean numeric values in path data."""
        # Match numbers (including negative and decimal)
        def replace_number(match):
            num_str = match.group(0)
            try:
                num = float(num_str)
                if num.is_integer():
                    return str(int(num))
                else:
                    return f"{num:.{precision}f}".rstrip('0').rstrip('.')
            except ValueError:
                return num_str
        
        return re.sub(r'-?\d*\.?\d+', replace_number, path_data)


class RemoveEmptyAttrsPlugin(PreprocessingPlugin):
    """Remove empty attributes."""
    
    name = "removeEmptyAttrs"
    description = "removes empty attributes"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return len(element.attrib) > 0
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        empty_attrs = [key for key, value in element.attrib.items() if not value.strip()]
        
        for key in empty_attrs:
            del element.attrib[key]
        
        if empty_attrs:
            context.record_modification(self.name, "removed_empty_attrs")
            return True
        return False


class RemoveEmptyContainersPlugin(PreprocessingPlugin):
    """Remove empty container elements."""
    
    name = "removeEmptyContainers"
    description = "removes empty container elements"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        container_tags = {'g', 'defs', 'symbol', 'marker', 'pattern', 'clipPath', 'mask'}
        return any(element.tag.endswith(tag) for tag in container_tags)
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        # Check if container is empty (no children and no significant attributes)
        if len(element) == 0:
            significant_attrs = set(element.attrib.keys()) - {'id', 'class'}
            if not significant_attrs:
                context.mark_for_removal(element)
                context.record_modification(self.name, "removed_empty_container")
                return True
        return False


class RemoveCommentsPlugin(PreprocessingPlugin):
    """Remove XML comments."""
    
    name = "removeComments"
    description = "removes comments"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return True
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        # ElementTree doesn't preserve comments by default, so this is mainly for completeness
        # In practice, comments are removed during parsing
        return False


class ConvertColorsPlugin(PreprocessingPlugin):
    """Convert colors: rgb() to #rrggbb and #rrggbb to #rgb."""
    
    name = "convertColors"
    description = "converts colors: rgb() to #rrggbb and #rrggbb to #rgb"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        color_attrs = {'fill', 'stroke', 'stop-color', 'color'}
        return any(attr in element.attrib for attr in color_attrs)
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        modified = False
        color_attrs = {'fill', 'stroke', 'stop-color', 'color'}
        
        for attr in color_attrs:
            if attr in element.attrib:
                original_color = element.attrib[attr]
                converted_color = self._convert_color(original_color)
                if converted_color != original_color:
                    element.set(attr, converted_color)
                    modified = True
        
        if modified:
            context.record_modification(self.name, "converted_colors")
        return modified
    
    def _convert_color(self, color: str) -> str:
        """Convert a color value to its shortest representation."""
        color = color.strip()
        
        # Convert rgb() to hex
        rgb_match = re.match(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', color)
        if rgb_match:
            r, g, b = map(int, rgb_match.groups())
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            # Try to shorten to 3-digit hex
            if hex_color[1] == hex_color[2] and hex_color[3] == hex_color[4] and hex_color[5] == hex_color[6]:
                return f"#{hex_color[1]}{hex_color[3]}{hex_color[5]}"
            return hex_color
        
        # Convert 6-digit hex to 3-digit if possible
        hex_match = re.match(r'#([0-9a-fA-F]{6})', color)
        if hex_match:
            hex_val = hex_match.group(1).lower()
            if hex_val[0] == hex_val[1] and hex_val[2] == hex_val[3] and hex_val[4] == hex_val[5]:
                return f"#{hex_val[0]}{hex_val[2]}{hex_val[4]}"
        
        return color


class CollapseGroupsPlugin(PreprocessingPlugin):
    """Collapse useless groups."""
    
    name = "collapseGroups"
    description = "collapses useless groups"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return element.tag.endswith('g')
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        # Check if group has only one child and no significant attributes
        if len(element) == 1:
            significant_attrs = set(element.attrib.keys()) - {'id', 'class'}
            if not significant_attrs:
                # Move child up to replace this group
                child = element[0]
                parent = None
                # Note: In a real implementation, we'd need parent tracking
                # For now, just mark for special handling
                context.record_modification(self.name, "collapsed_group")
                return True
        return False


class RemoveUnusedNamespacesPlugin(PreprocessingPlugin):
    """Remove unused namespace declarations."""
    
    name = "removeUnusedNS"
    description = "removes unused namespaces declaration"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return element.tag == '{http://www.w3.org/2000/svg}svg' or 'xmlns' in str(element.attrib)
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        # This would require a full document analysis to determine which namespaces are actually used
        # For now, we'll implement a basic version that removes common unused namespaces
        modified = False
        unused_ns_prefixes = {
            'xmlns:sodipodi', 'xmlns:inkscape', 'xmlns:sketch', 'xmlns:figma'
        }
        
        for attr_name in list(element.attrib.keys()):
            if any(attr_name.startswith(prefix) for prefix in unused_ns_prefixes):
                del element.attrib[attr_name]
                modified = True
        
        if modified:
            context.record_modification(self.name, "removed_unused_ns")
        return modified


class ConvertShapeToPathPlugin(PreprocessingPlugin):
    """Convert basic shapes to path elements for unified processing."""
    
    name = "convertShapeToPath"
    description = "converts basic shapes to more compact path form"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        shape_tags = {'rect', 'circle', 'ellipse', 'line', 'polygon', 'polyline'}
        return any(element.tag.endswith(tag) for tag in shape_tags)
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        
        path_data = None
        if tag == 'rect':
            path_data = self._rect_to_path(element)
        elif tag == 'circle':
            path_data = self._circle_to_path(element)
        elif tag == 'ellipse':
            path_data = self._ellipse_to_path(element)
        elif tag == 'line':
            path_data = self._line_to_path(element)
        
        if path_data:
            # Convert element to path
            element.tag = element.tag.replace(tag, 'path')
            element.set('d', path_data)
            
            # Remove shape-specific attributes
            shape_attrs = {'x', 'y', 'width', 'height', 'cx', 'cy', 'r', 'rx', 'ry', 
                          'x1', 'y1', 'x2', 'y2', 'points'}
            for attr in shape_attrs:
                if attr in element.attrib:
                    del element.attrib[attr]
            
            context.record_modification(self.name, f"converted_{tag}_to_path")
            return True
        
        return False
    
    def _rect_to_path(self, element: ET.Element) -> Optional[str]:
        """Convert rectangle to path data."""
        try:
            x = float(element.get('x', 0))
            y = float(element.get('y', 0))
            width = float(element.get('width', 0))
            height = float(element.get('height', 0))
            rx = float(element.get('rx', 0))
            ry = float(element.get('ry', 0))
            
            if rx == 0 and ry == 0:
                # Simple rectangle
                return f"M{x},{y}h{width}v{height}h{-width}z"
            else:
                # Rounded rectangle - simplified version
                return f"M{x+rx},{y}h{width-2*rx}a{rx},{ry} 0 0 1 {rx},{ry}v{height-2*ry}a{rx},{ry} 0 0 1 {-rx},{ry}h{-width+2*rx}a{rx},{ry} 0 0 1 {-rx},{-ry}v{-height+2*ry}a{rx},{ry} 0 0 1 {rx},{-ry}z"
        except (ValueError, TypeError):
            return None
    
    def _circle_to_path(self, element: ET.Element) -> Optional[str]:
        """Convert circle to path data."""
        try:
            cx = float(element.get('cx', 0))
            cy = float(element.get('cy', 0))
            r = float(element.get('r', 0))
            
            # Circle as two semicircle arcs
            return f"M{cx-r},{cy}A{r},{r} 0 1 1 {cx+r},{cy}A{r},{r} 0 1 1 {cx-r},{cy}z"
        except (ValueError, TypeError):
            return None
    
    def _ellipse_to_path(self, element: ET.Element) -> Optional[str]:
        """Convert ellipse to path data."""
        try:
            cx = float(element.get('cx', 0))
            cy = float(element.get('cy', 0))
            rx = float(element.get('rx', 0))
            ry = float(element.get('ry', 0))
            
            # Ellipse as two semi-ellipse arcs
            return f"M{cx-rx},{cy}A{rx},{ry} 0 1 1 {cx+rx},{cy}A{rx},{ry} 0 1 1 {cx-rx},{cy}z"
        except (ValueError, TypeError):
            return None
    
    def _line_to_path(self, element: ET.Element) -> Optional[str]:
        """Convert line to path data."""
        try:
            x1 = float(element.get('x1', 0))
            y1 = float(element.get('y1', 0))
            x2 = float(element.get('x2', 0))
            y2 = float(element.get('y2', 0))
            
            return f"M{x1},{y1}L{x2},{y2}"
        except (ValueError, TypeError):
            return None