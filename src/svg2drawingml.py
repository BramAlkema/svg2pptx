#!/usr/bin/env python3
"""
SVG to DrawingML Converter

Direct conversion from SVG vector graphics to Microsoft Office DrawingML format.
Based on LibreOffice's conversion algorithms but bypasses their incomplete SVG import.

Architecture:
- SVG Parser: Extract vector elements from SVG XML
- DrawingML Generator: Create Office Open XML markup  
- Coordinate Mapper: Convert SVG units to DrawingML units
- Shape Converter: Map SVG elements to DrawingML equivalents
"""

from lxml import etree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re
import math
from .units import EMU_PER_POINT
from .converters.base import ConverterRegistryFactory, CoordinateSystem, ConversionContext


class SVGParser:
    """Parse SVG XML and extract vector graphics elements."""
    
    def __init__(self, svg_content: str):
        self.root = ET.fromstring(svg_content)
        self.width, self.height = self._parse_dimensions()
        self.viewbox = self._parse_viewbox()
        self.gradients = self._parse_gradients()
    
    def _parse_viewbox(self) -> Tuple[float, float, float, float]:
        """Parse SVG viewBox attribute."""
        viewbox = self.root.get('viewBox')
        if viewbox:
            values = [float(v) for v in viewbox.split()]
            return tuple(values)
        return (0, 0, self.width or 100, self.height or 100)
    
    def _parse_dimensions(self) -> Tuple[Optional[float], Optional[float]]:
        """Parse SVG width and height attributes."""
        width = self._parse_length(self.root.get('width'))
        height = self._parse_length(self.root.get('height'))
        return width, height
    
    def _parse_length(self, length_str: str) -> Optional[float]:
        """Parse SVG length values (with units)."""
        if not length_str:
            return None
        
        # Remove units and convert to float
        match = re.match(r'([0-9.]+)', length_str)
        if match:
            return float(match.group(1))
        return None
    
    def extract_elements(self) -> List[Dict]:
        """Extract all drawable elements from SVG."""
        elements = []
        self._extract_recursive(self.root, elements)
        return elements
    
    def _extract_recursive(self, element: ET.Element, elements: List[Dict]) -> None:
        """Recursively extract elements from SVG tree."""
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        
        if tag in ['rect', 'circle', 'ellipse', 'line', 'path', 'polygon', 'polyline']:
            elements.append({
                'type': tag,
                'attributes': dict(element.attrib),
                'element': element
            })
        
        # Recurse into child elements
        for child in element:
            self._extract_recursive(child, elements)
    
    def _parse_gradients(self) -> Dict[str, Dict]:
        """Parse gradient definitions from SVG."""
        gradients = {}
        
        # Find defs section
        defs = self.root.find('.//defs') or self.root.find('.//{http://www.w3.org/2000/svg}defs')
        if defs is None:
            return gradients
        
        # Parse linear gradients
        for grad in defs.findall('.//linearGradient') or defs.findall('.//{http://www.w3.org/2000/svg}linearGradient'):
            grad_id = grad.get('id')
            if grad_id:
                gradients[grad_id] = {
                    'type': 'linear',
                    'x1': grad.get('x1', '0%'),
                    'y1': grad.get('y1', '0%'),
                    'x2': grad.get('x2', '100%'),
                    'y2': grad.get('y2', '0%'),
                    'stops': self._parse_gradient_stops(grad)
                }
        
        # Parse radial gradients
        for grad in defs.findall('.//radialGradient') or defs.findall('.//{http://www.w3.org/2000/svg}radialGradient'):
            grad_id = grad.get('id')
            if grad_id:
                gradients[grad_id] = {
                    'type': 'radial',
                    'cx': grad.get('cx', '50%'),
                    'cy': grad.get('cy', '50%'),
                    'r': grad.get('r', '50%'),
                    'stops': self._parse_gradient_stops(grad)
                }
        
        return gradients
    
    def _parse_gradient_stops(self, gradient_element: ET.Element) -> List[Dict]:
        """Parse gradient stop elements."""
        stops = []
        
        for stop in gradient_element.findall('.//stop') or gradient_element.findall('.//{http://www.w3.org/2000/svg}stop'):
            stop_data = {
                'offset': stop.get('offset', '0%'),
                'color': '#000000',
                'opacity': '1'
            }
            
            # Parse style attribute or direct attributes
            style = stop.get('style', '')
            if style:
                style_parts = [part.strip() for part in style.split(';') if part.strip()]
                for part in style_parts:
                    if ':' in part:
                        prop, value = part.split(':', 1)
                        prop = prop.strip()
                        value = value.strip()
                        
                        if prop == 'stop-color':
                            stop_data['color'] = value
                        elif prop == 'stop-opacity':
                            stop_data['opacity'] = value
            
            # Direct attributes override style
            if stop.get('stop-color'):
                stop_data['color'] = stop.get('stop-color')
            if stop.get('stop-opacity'):
                stop_data['opacity'] = stop.get('stop-opacity')
            
            stops.append(stop_data)
        
        return stops


class CoordinateMapper:
    """Convert between SVG and DrawingML coordinate systems."""
    
    def __init__(self, svg_viewbox: Tuple[float, float, float, float], 
                 slide_width: float = 9144000, slide_height: float = 6858000):
        """
        Initialize coordinate mapper.
        
        Args:
            svg_viewbox: (min_x, min_y, width, height) from SVG
            slide_width: PowerPoint slide width in EMUs (default: 10 inches)
            slide_height: PowerPoint slide height in EMUs (default: 7.5 inches)
        """
        self.svg_viewbox = svg_viewbox
        self.slide_width = slide_width
        self.slide_height = slide_height
        
        # Calculate scaling factors
        svg_width = svg_viewbox[2]
        svg_height = svg_viewbox[3]
        self.scale_x = slide_width / svg_width
        self.scale_y = slide_height / svg_height
    
    def svg_to_emu(self, x: float, y: float) -> Tuple[int, int]:
        """Convert SVG coordinates to DrawingML EMUs (English Metric Units)."""
        # Adjust for viewbox offset
        x -= self.svg_viewbox[0]
        y -= self.svg_viewbox[1]
        
        # Scale to slide dimensions
        emu_x = int(x * self.scale_x)
        emu_y = int(y * self.scale_y)
        
        return emu_x, emu_y
    
    def svg_length_to_emu(self, length: float, axis: str = 'x') -> int:
        """Convert SVG length to EMU."""
        scale = self.scale_x if axis == 'x' else self.scale_y
        return int(length * scale)


class DrawingMLGenerator:
    """Generate DrawingML XML markup from SVG elements."""
    
    def __init__(self, coordinate_mapper: CoordinateMapper, gradients: Dict[str, Dict] = None):
        self.coord_mapper = coordinate_mapper
        self.gradients = gradients or {}
        self.shape_id = 1000  # Starting ID for shapes
    
    def generate_shape(self, svg_element: Dict) -> str:
        """Generate DrawingML for a single SVG element."""
        element_type = svg_element['type']
        
        if element_type == 'rect':
            return self._generate_rectangle(svg_element)
        elif element_type == 'circle':
            return self._generate_circle(svg_element)
        elif element_type == 'ellipse':
            return self._generate_ellipse(svg_element)
        elif element_type == 'line':
            return self._generate_line(svg_element)
        elif element_type == 'path':
            return self._generate_path(svg_element)
        else:
            return f"<!-- Unsupported element type: {element_type} -->"
    
    def _generate_rectangle(self, svg_element: Dict) -> str:
        """Generate DrawingML for SVG rectangle."""
        attrs = svg_element['attributes']
        
        x = float(attrs.get('x', 0))
        y = float(attrs.get('y', 0))
        width = float(attrs.get('width', 0))
        height = float(attrs.get('height', 0))
        
        # Convert to EMUs
        emu_x, emu_y = self.coord_mapper.svg_to_emu(x, y)
        emu_width = self.coord_mapper.svg_length_to_emu(width, 'x')
        emu_height = self.coord_mapper.svg_length_to_emu(height, 'y')
        
        shape_id = self.shape_id
        self.shape_id += 1
        
        return f'''
        <p:sp>
            <p:nvSpPr>
                <p:cNvPr id="{shape_id}" name="Rectangle {shape_id}"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="{emu_x}" y="{emu_y}"/>
                    <a:ext cx="{emu_width}" cy="{emu_height}"/>
                </a:xfrm>
                <a:prstGeom prst="rect">
                    <a:avLst/>
                </a:prstGeom>
                {self._generate_fill_and_stroke(attrs)}
            </p:spPr>
            <p:txBody>
                <a:bodyPr/>
                <a:lstStyle/>
                <a:p>
                    <a:pPr/>
                    <a:endParaRPr/>
                </a:p>
            </p:txBody>
        </p:sp>'''
    
    def _generate_circle(self, svg_element: Dict) -> str:
        """Generate DrawingML for SVG circle."""
        attrs = svg_element['attributes']
        
        cx = float(attrs.get('cx', 0))
        cy = float(attrs.get('cy', 0))
        r = float(attrs.get('r', 0))
        
        # Convert to rectangle coordinates (top-left corner)
        x = cx - r
        y = cy - r
        diameter = 2 * r
        
        # Convert to EMUs
        emu_x, emu_y = self.coord_mapper.svg_to_emu(x, y)
        emu_diameter = self.coord_mapper.svg_length_to_emu(diameter, 'x')
        
        shape_id = self.shape_id
        self.shape_id += 1
        
        return f'''
        <p:sp>
            <p:nvSpPr>
                <p:cNvPr id="{shape_id}" name="Circle {shape_id}"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="{emu_x}" y="{emu_y}"/>
                    <a:ext cx="{emu_diameter}" cy="{emu_diameter}"/>
                </a:xfrm>
                <a:prstGeom prst="ellipse">
                    <a:avLst/>
                </a:prstGeom>
                {self._generate_fill_and_stroke(attrs)}
            </p:spPr>
            <p:txBody>
                <a:bodyPr/>
                <a:lstStyle/>
                <a:p>
                    <a:pPr/>
                    <a:endParaRPr/>
                </a:p>
            </p:txBody>
        </p:sp>'''
    
    def _generate_ellipse(self, svg_element: Dict) -> str:
        """Generate DrawingML for SVG ellipse."""
        attrs = svg_element['attributes']
        
        cx = float(attrs.get('cx', 0))
        cy = float(attrs.get('cy', 0))
        rx = float(attrs.get('rx', 0))
        ry = float(attrs.get('ry', 0))
        
        # Convert to rectangle coordinates
        x = cx - rx
        y = cy - ry
        width = 2 * rx
        height = 2 * ry
        
        # Convert to EMUs
        emu_x, emu_y = self.coord_mapper.svg_to_emu(x, y)
        emu_width = self.coord_mapper.svg_length_to_emu(width, 'x')
        emu_height = self.coord_mapper.svg_length_to_emu(height, 'y')
        
        shape_id = self.shape_id
        self.shape_id += 1
        
        return f'''
        <p:sp>
            <p:nvSpPr>
                <p:cNvPr id="{shape_id}" name="Ellipse {shape_id}"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="{emu_x}" y="{emu_y}"/>
                    <a:ext cx="{emu_width}" cy="{emu_height}"/>
                </a:xfrm>
                <a:prstGeom prst="ellipse">
                    <a:avLst/>
                </a:prstGeom>
                {self._generate_fill_and_stroke(attrs)}
            </p:spPr>
            <p:txBody>
                <a:bodyPr/>
                <a:lstStyle/>
                <a:p>
                    <a:pPr/>
                    <a:endParaRPr/>
                </a:p>
            </p:txBody>
        </p:sp>'''
    
    def _generate_line(self, svg_element: Dict) -> str:
        """Generate DrawingML for SVG line."""
        attrs = svg_element['attributes']
        
        x1 = float(attrs.get('x1', 0))
        y1 = float(attrs.get('y1', 0))
        x2 = float(attrs.get('x2', 0))
        y2 = float(attrs.get('y2', 0))
        
        # Convert to EMUs
        emu_x1, emu_y1 = self.coord_mapper.svg_to_emu(x1, y1)
        emu_x2, emu_y2 = self.coord_mapper.svg_to_emu(x2, y2)
        
        shape_id = self.shape_id
        self.shape_id += 1
        
        return f'''
        <p:cxnSp>
            <p:nvCxnSpPr>
                <p:cNvPr id="{shape_id}" name="Line {shape_id}"/>
                <p:cNvCxnSpPr/>
                <p:nvPr/>
            </p:nvCxnSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="{min(emu_x1, emu_x2)}" y="{min(emu_y1, emu_y2)}"/>
                    <a:ext cx="{abs(emu_x2 - emu_x1)}" cy="{abs(emu_y2 - emu_y1)}"/>
                </a:xfrm>
                <a:custGeom>
                    <a:avLst/>
                    <a:gdLst/>
                    <a:ahLst/>
                    <a:cxnLst/>
                    <a:rect l="0" t="0" r="0" b="0"/>
                    <a:pathLst>
                        <a:path w="{abs(emu_x2 - emu_x1)}" h="{abs(emu_y2 - emu_y1)}">
                            <a:moveTo>
                                <a:pt x="0" y="0"/>
                            </a:moveTo>
                            <a:lnTo>
                                <a:pt x="{abs(emu_x2 - emu_x1)}" y="{abs(emu_y2 - emu_y1)}"/>
                            </a:lnTo>
                        </a:path>
                    </a:pathLst>
                </a:custGeom>
                {self._generate_stroke_only(attrs)}
            </p:spPr>
        </p:cxnSp>'''
    
    def _generate_path(self, svg_element: Dict) -> str:
        """Generate DrawingML for SVG path (basic implementation)."""
        attrs = svg_element['attributes']
        path_data = attrs.get('d', '')
        
        # This is a simplified path implementation
        # Full SVG path parsing would require more complex logic
        shape_id = self.shape_id
        self.shape_id += 1
        
        return f'''
        <!-- SVG Path: {path_data} -->
        <!-- Path conversion requires more complex implementation -->
        <p:sp>
            <p:nvSpPr>
                <p:cNvPr id="{shape_id}" name="Path {shape_id}"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="914400" cy="914400"/>
                </a:xfrm>
                <a:prstGeom prst="rect">
                    <a:avLst/>
                </a:prstGeom>
                {self._generate_fill_and_stroke(attrs)}
            </p:spPr>
            <p:txBody>
                <a:bodyPr/>
                <a:lstStyle/>
                <a:p>
                    <a:pPr/>
                    <a:endParaRPr/>
                </a:p>
            </p:txBody>
        </p:sp>'''
    
    def _generate_fill_and_stroke(self, attrs: Dict) -> str:
        """Generate fill and stroke properties from SVG attributes."""
        fill = attrs.get('fill', 'black')
        stroke = attrs.get('stroke', 'none')
        stroke_width = attrs.get('stroke-width', '1')
        
        fill_xml = ""
        stroke_xml = ""
        
        # Handle fill
        if fill and fill != 'none':
            if fill.startswith('url(#'):
                # Gradient fill reference
                grad_id = fill[5:-1]  # Remove url(# and )
                fill_xml = self._generate_gradient_fill(grad_id)
            elif fill.startswith('#'):
                # Convert hex color to RGB
                color = fill[1:]  # Remove #
                fill_xml = f'''<a:solidFill>
                    <a:srgbClr val="{color}"/>
                </a:solidFill>'''
            elif fill.startswith('rgb('):
                # RGB color
                fill_xml = self._parse_rgb_fill(fill)
            else:
                # Named color or default fill
                color = self._color_name_to_hex(fill)
                fill_xml = f'''<a:solidFill>
                    <a:srgbClr val="{color}"/>
                </a:solidFill>'''
        else:
            fill_xml = "<a:noFill/>"
        
        # Handle stroke
        if stroke and stroke != 'none':
            width_emu = int(float(stroke_width) * EMU_PER_POINT)  # Convert to EMUs
            if stroke.startswith('#'):
                color = stroke[1:]
                stroke_xml = f'''<a:ln w="{width_emu}">
                    <a:solidFill>
                        <a:srgbClr val="{color}"/>
                    </a:solidFill>
                </a:ln>'''
            else:
                color = self._color_name_to_hex(stroke)
                stroke_xml = f'''<a:ln w="{width_emu}">
                    <a:solidFill>
                        <a:srgbClr val="{color}"/>
                    </a:solidFill>
                </a:ln>'''
        
        return fill_xml + stroke_xml
    
    def _generate_stroke_only(self, attrs: Dict) -> str:
        """Generate stroke-only properties (for lines)."""
        stroke = attrs.get('stroke', 'black')
        stroke_width = attrs.get('stroke-width', '1')
        
        width_emu = int(float(stroke_width) * EMU_PER_POINT)
        color = stroke[1:] if stroke.startswith('#') else self._color_name_to_hex(stroke)
        
        return f'''<a:ln w="{width_emu}">
            <a:solidFill>
                <a:srgbClr val="{color}"/>
            </a:solidFill>
        </a:ln>'''
    
    def _generate_gradient_fill(self, grad_id: str) -> str:
        """Generate DrawingML gradient fill from SVG gradient definition."""
        if grad_id not in self.gradients:
            # Fallback to solid fill if gradient not found
            return '''<a:solidFill>
                <a:srgbClr val="808080"/>
            </a:solidFill>'''
        
        gradient = self.gradients[grad_id]
        
        if gradient['type'] == 'linear':
            return self._generate_linear_gradient(gradient)
        elif gradient['type'] == 'radial':
            return self._generate_radial_gradient(gradient)
        else:
            return '''<a:solidFill>
                <a:srgbClr val="808080"/>
            </a:solidFill>'''
    
    def _generate_linear_gradient(self, gradient: Dict) -> str:
        """Generate DrawingML linear gradient."""
        stops = gradient.get('stops', [])
        if not stops:
            return '''<a:solidFill>
                <a:srgbClr val="808080"/>
            </a:solidFill>'''
        
        # Convert SVG gradient direction to DrawingML angle
        x1 = self._parse_percentage(gradient.get('x1', '0%'))
        y1 = self._parse_percentage(gradient.get('y1', '0%'))  
        x2 = self._parse_percentage(gradient.get('x2', '100%'))
        y2 = self._parse_percentage(gradient.get('y2', '0%'))
        
        # Calculate angle (DrawingML uses 60000 units per degree)
        dx = x2 - x1
        dy = y2 - y1
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        angle_60k = int(angle_deg * 60000)
        
        # Generate gradient stops
        gradient_stops = []
        for stop in stops:
            offset = self._parse_percentage(stop['offset'])
            color = self._parse_color(stop['color'])
            opacity = float(stop.get('opacity', '1'))
            alpha = int(opacity * 100000)  # DrawingML uses 100000 for full opacity
            
            gradient_stops.append(f'''
                <a:gs pos="{int(offset * 1000)}">
                    <a:srgbClr val="{color}">
                        <a:alpha val="{alpha}"/>
                    </a:srgbClr>
                </a:gs>''')
        
        return f'''<a:gradFill flip="none" rotWithShape="1">
            <a:gsLst>
                {''.join(gradient_stops)}
            </a:gsLst>
            <a:lin ang="{angle_60k}" scaled="0"/>
        </a:gradFill>'''
    
    def _generate_radial_gradient(self, gradient: Dict) -> str:
        """Generate DrawingML radial gradient."""
        stops = gradient.get('stops', [])
        if not stops:
            return '''<a:solidFill>
                <a:srgbClr val="808080"/>
            </a:solidFill>'''
        
        # Generate gradient stops
        gradient_stops = []
        for stop in stops:
            offset = self._parse_percentage(stop['offset'])
            color = self._parse_color(stop['color'])
            opacity = float(stop.get('opacity', '1'))
            alpha = int(opacity * 100000)
            
            gradient_stops.append(f'''
                <a:gs pos="{int(offset * 1000)}">
                    <a:srgbClr val="{color}">
                        <a:alpha val="{alpha}"/>
                    </a:srgbClr>
                </a:gs>''')
        
        return f'''<a:gradFill flip="none" rotWithShape="1">
            <a:gsLst>
                {''.join(gradient_stops)}
            </a:gsLst>
            <a:path path="circle">
                <a:fillToRect l="50000" t="-80000" r="50000" b="180000"/>
            </a:path>
        </a:gradFill>'''
    
    def _parse_percentage(self, value: str) -> float:
        """Parse percentage or decimal value to float 0-1."""
        if value.endswith('%'):
            return float(value[:-1]) / 100.0
        return float(value)
    
    def _parse_color(self, color: str) -> str:
        """Parse color value to hex string."""
        if color.startswith('#'):
            return color[1:].upper()
        elif color.startswith('rgb('):
            return self._parse_rgb_color(color)
        else:
            return self._color_name_to_hex(color)
    
    def _parse_rgb_color(self, rgb_str: str) -> str:
        """Parse rgb(r,g,b) string to hex."""
        rgb_match = re.match(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', rgb_str)
        if rgb_match:
            r, g, b = map(int, rgb_match.groups())
            return f"{r:02X}{g:02X}{b:02X}"
        return "808080"  # Default gray
    
    def _parse_rgb_fill(self, rgb_str: str) -> str:
        """Generate solid fill from rgb() color."""
        color = self._parse_rgb_color(rgb_str)
        return f'''<a:solidFill>
            <a:srgbClr val="{color}"/>
        </a:solidFill>'''
    
    def _color_name_to_hex(self, color_name: str) -> str:
        """Convert color name to hex value."""
        color_map = {
            'black': '000000', 'white': 'FFFFFF', 'red': 'FF0000',
            'green': '008000', 'blue': '0000FF', 'yellow': 'FFFF00',
            'cyan': '00FFFF', 'magenta': 'FF00FF', 'gray': '808080',
            'grey': '808080', 'darkred': '8B0000', 'darkgreen': '006400',
            'darkblue': '00008B', 'orange': 'FFA500', 'purple': '800080'
        }
        return color_map.get(color_name.lower(), '000000')


class SVGToDrawingMLConverter:
    """Main converter class that orchestrates the conversion process."""
    
    def __init__(self):
        self.parser = None
        self.coord_mapper = None
        self.generator = None
    
    def convert(self, svg_content: str) -> str:
        """Convert SVG content to DrawingML shapes."""
        # Parse SVG
        self.parser = SVGParser(svg_content)
        elements = self.parser.extract_elements()
        
        # Set up coordinate mapping
        self.coord_mapper = CoordinateMapper(self.parser.viewbox)
        
        # Get the converter registry
        registry = ConverterRegistryFactory.get_registry()
        
        # Create conversion context with proper coordinate system
        svg_root = ET.fromstring(svg_content)
        coord_sys = CoordinateSystem(self.parser.viewbox)
        context = ConversionContext(svg_root)
        context.coordinate_system = coord_sys
        
        # Add parsed gradients to context
        context.gradients = self.parser.gradients
        
        # Convert each element using the registry
        drawingml_shapes = []
        for element_data in elements:
            # Extract the actual ET.Element from the dict
            if isinstance(element_data, dict) and 'element' in element_data:
                element = element_data['element']
            else:
                element = element_data
                
            shape_xml = registry.convert_element(element, context)
            if shape_xml:  # Only add non-None results
                drawingml_shapes.append(shape_xml)
        
        return '\n'.join(drawingml_shapes)
    
    def convert_file(self, svg_file: str) -> str:
        """Convert SVG file to DrawingML."""
        with open(svg_file, 'r', encoding='utf-8') as f:
            svg_content = f.read()
        return self.convert(svg_content)


def main():
    """Demo/test function."""
    # Simple test SVG
    test_svg = '''<?xml version="1.0" encoding="UTF-8"?>
    <svg width="200" height="200" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
        <rect x="10" y="10" width="50" height="30" fill="#ff0000" stroke="#000000" stroke-width="2"/>
        <circle cx="100" cy="100" r="25" fill="#00ff00"/>
        <ellipse cx="150" cy="50" rx="20" ry="15" fill="#0000ff"/>
        <line x1="20" y1="150" x2="180" y2="150" stroke="#000000" stroke-width="3"/>
    </svg>'''
    
    converter = SVGToDrawingMLConverter()
    result = converter.convert(test_svg)
    
    print("DrawingML Output:")
    print(result)


if __name__ == "__main__":
    main()