"""
SVG Group and Container Element Handler

Handles SVG container elements with support for:
- Group elements (<g>)
- SVG root elements
- Symbol and use elements (basic support)
- Defs and marker elements
- Nested element processing
- Transform accumulation through hierarchy
"""

from typing import List, Dict, Any, Optional
from lxml import etree as ET
from .base import BaseConverter, ConversionContext, ConverterRegistry
from .transforms import TransformConverter


class GroupHandler(BaseConverter):
    """Handles SVG group elements and nested structure"""

    supported_elements = ['g', 'svg', 'symbol', 'defs', 'marker']

    def __init__(self, services):
        super().__init__(services)
        self.transform_converter = TransformConverter(services)
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the given element"""
        tag_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        return tag_name in self.supported_elements
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG group element to DrawingML group"""
        tag_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        
        if tag_name == 'g':
            return self._convert_group(element, context)
        elif tag_name == 'svg':
            return self._convert_svg_root(element, context)
        elif tag_name == 'symbol':
            return self._convert_symbol(element, context)
        elif tag_name in ['defs', 'marker']:
            # These are definition containers, usually processed separately
            return ""
        
        return ""
    
    def _convert_group(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG group element"""
        # Get group transform
        group_transform = self.transform_converter.get_element_transform(element)
        
        # Create new context with accumulated transform
        new_context = ConversionContext(context.svg_root, services=self.services)
        new_context.coordinate_system = context.coordinate_system
        new_context.converter_registry = context.converter_registry
        new_context.shape_id_counter = context.shape_id_counter
        
        # Process all child elements
        child_elements = []
        for child in element:
            child_xml = self._process_child_element(child, new_context, group_transform)
            if child_xml.strip():
                child_elements.append(child_xml)
        
        if not child_elements:
            return ""
        
        # Get group properties
        group_id = element.get('id', f'group_{context.get_next_shape_id()}')
        
        # If group has transforms or multiple children, wrap in group
        if not group_transform.is_identity() or len(child_elements) > 1:
            children_xml = '\n    '.join(child_elements)
            
            return f"""<a:grpSp>
    <a:nvGrpSpPr>
        <a:cNvPr id="{context.get_next_shape_id()}" name="{group_id}"/>
        <a:cNvGrpSpPr/>
    </a:nvGrpSpPr>
    <a:grpSpPr>
        {self.transform_converter.get_drawingml_transform(group_transform, context)}
    </a:grpSpPr>
    {children_xml}
</a:grpSp>"""
        else:
            # Single child without transform - return child directly
            return child_elements[0]
    
    def _convert_svg_root(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG root element"""
        # Process all child elements
        child_elements = []
        for child in element:
            # Skip certain elements that are processed separately
            child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if child_tag in ['defs', 'style', 'title', 'desc', 'metadata']:
                continue
            
            child_xml = self._process_child_element(child, context)
            if child_xml.strip():
                child_elements.append(child_xml)
        
        if not child_elements:
            return ""
        
        # Return all children without wrapping (SVG root is container)
        return '\n'.join(child_elements)
    
    def _convert_symbol(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG symbol element (similar to group)"""
        # Symbols are typically referenced by <use> elements
        # For now, treat like a group
        return self._convert_group(element, context)
    
    def _process_child_element(self, child: ET.Element, context: ConversionContext, 
                             parent_transform: Optional[object] = None) -> str:
        """Process a child element with optional parent transform"""
        child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        
        # Skip certain elements
        if child_tag in ['title', 'desc', 'metadata', 'style']:
            return ""
        
        # Get element transform and combine with parent
        element_transform = self.transform_converter.get_element_transform(child)
        if parent_transform and not parent_transform.is_identity():
            # Combine transforms: parent * element
            combined_transform = parent_transform.multiply(element_transform)
            
            # Temporarily set combined transform on element for processing
            if not combined_transform.is_identity():
                child.set('transform', str(combined_transform))
        
        # Get appropriate converter for this element
        converter = context.converter_registry.get_converter(child_tag)
        if converter:
            return converter.convert(child, context)
        
        # If no specific converter, check if it's a container element
        if child_tag in ['g', 'svg', 'symbol']:
            return self.convert(child, context)
        
        return ""
    
    def process_use_element(self, use_element: ET.Element, context: ConversionContext) -> str:
        """Process SVG <use> element (references other elements)"""
        href = use_element.get('href') or use_element.get('{http://www.w3.org/1999/xlink}href')
        if not href or not href.startswith('#'):
            return ""
        
        # Find referenced element
        ref_id = href[1:]  # Remove '#'
        referenced_element = None
        
        # Search in SVG root
        for elem in context.svg_root.iter():
            if elem.get('id') == ref_id:
                referenced_element = elem
                break
        
        if referenced_element is None:
            return ""
        
        # Get use transform
        use_x = float(use_element.get('x', '0'))
        use_y = float(use_element.get('y', '0'))
        use_transform = self.transform_converter.get_element_transform(use_element)
        
        # Create translation for x,y offset
        if use_x != 0 or use_y != 0:
            from .transforms import Matrix
            translation = Matrix(1, 0, 0, 1, use_x, use_y)
            use_transform = use_transform.multiply(translation)
        
        # Clone the referenced element and apply use transform
        cloned_element = self._clone_element_with_transform(referenced_element, use_transform)
        
        # Process the cloned element
        return self._process_child_element(cloned_element, context)
    
    def _clone_element_with_transform(self, element: ET.Element, transform: object) -> ET.Element:
        """Clone an element and apply additional transform"""
        # Create a copy of the element
        cloned = ET.Element(element.tag, element.attrib)
        cloned.text = element.text
        cloned.tail = element.tail
        
        # Add children
        for child in element:
            cloned.append(self._clone_element_with_transform(child, transform))
        
        # Apply transform
        if not transform.is_identity():
            existing_transform = cloned.get('transform', '')
            if existing_transform:
                # Combine transforms
                existing = self.transform_converter.parse_transform(existing_transform)
                combined = transform.multiply(existing)
                cloned.set('transform', str(combined))
            else:
                cloned.set('transform', str(transform))
        
        return cloned
    
    def extract_definitions(self, svg_root: ET.Element) -> Dict[str, ET.Element]:
        """Extract all definition elements (gradients, patterns, etc.) from SVG"""
        definitions = {}
        
        # Find <defs> elements
        for defs in svg_root.findall('.//defs'):
            for child in defs:
                element_id = child.get('id')
                if element_id:
                    definitions[element_id] = child
        
        # Also check for definitions outside <defs> (common in some SVGs)
        for element in svg_root.iter():
            if element.get('id') and element.tag.split('}')[-1] in [
                'linearGradient', 'radialGradient', 'pattern', 'mask', 
                'clipPath', 'filter', 'marker', 'symbol'
            ]:
                definitions[element.get('id')] = element
        
        return definitions
    
    def process_nested_svg(self, svg_element: ET.Element, context: ConversionContext) -> str:
        """Process nested SVG element (SVG inside SVG)"""
        # Get nested SVG dimensions and viewport
        x = float(svg_element.get('x', '0'))
        y = float(svg_element.get('y', '0'))
        width = svg_element.get('width', '100%')
        height = svg_element.get('height', '100%')
        viewBox = svg_element.get('viewBox', '')
        
        # Create new coordinate system for nested SVG
        from .base import CoordinateSystem
        
        # Parse dimensions
        # Use viewbox dimensions as parent size for percentage calculations
        parent_width = context.coordinate_system.viewbox[2] if context.coordinate_system else 100
        parent_height = context.coordinate_system.viewbox[3] if context.coordinate_system else 100
        
        svg_width = self._parse_dimension(width, parent_width)
        svg_height = self._parse_dimension(height, parent_height)
        
        # Create nested context
        nested_coord_system = CoordinateSystem((0, 0, svg_width, svg_height))
        nested_context = ConversionContext(svg_element, services=self.services)
        nested_context.coordinate_system = nested_coord_system
        nested_context.converter_registry = context.converter_registry
        nested_context.shape_id_counter = context.shape_id_counter
        
        # Process children
        children_xml = self._convert_svg_root(svg_element, nested_context)
        
        if not children_xml.strip():
            return ""
        
        # Wrap in group with positioning
        x_emu, y_emu = context.coordinate_system.svg_to_emu(x, y)
        width_emu = context.to_emu(f"{svg_width}px", 'x')
        height_emu = context.to_emu(f"{svg_height}px", 'y')
        
        return f"""<a:grpSp>
    <a:nvGrpSpPr>
        <a:cNvPr id="{context.get_next_shape_id()}" name="NestedSVG"/>
        <a:cNvGrpSpPr/>
    </a:nvGrpSpPr>
    <a:grpSpPr>
        <a:xfrm>
            <a:off x="{x_emu}" y="{y_emu}"/>
            <a:ext cx="{width_emu}" cy="{height_emu}"/>
        </a:xfrm>
    </a:grpSpPr>
    {children_xml}
</a:grpSp>"""
    
    def _parse_dimension(self, dimension_str: str, parent_size: float) -> float:
        """Parse SVG dimension (px, %, em, etc.)"""
        dimension_str = dimension_str.strip().lower()
        
        if dimension_str.endswith('%'):
            # Percentage of parent
            percent = float(dimension_str[:-1])
            return (percent / 100) * parent_size
        elif dimension_str.endswith('px'):
            return float(dimension_str[:-2])
        elif dimension_str.endswith('em'):
            # Assume 12px base font size
            return float(dimension_str[:-2]) * 12
        elif dimension_str.endswith('pt'):
            # Points to pixels (72 DPI)
            return float(dimension_str[:-2])
        else:
            # Try to parse as number (assume pixels)
            try:
                return float(dimension_str)
            except ValueError:
                return parent_size  # Fallback to parent size