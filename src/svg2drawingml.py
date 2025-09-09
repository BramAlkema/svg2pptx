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

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re
import math


class SVGParser:
    """Parse SVG XML and extract vector graphics elements."""
    
    def __init__(self, svg_content: str):
        self.root = ET.fromstring(svg_content)
        self.width, self.height = self._parse_dimensions()
        self.viewbox = self._parse_viewbox()
    
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
                'attributes': element.attrib.copy(),
                'element': element
            })
        
        # Recurse into child elements
        for child in element:
            self._extract_recursive(child, elements)


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
    
    def __init__(self, coordinate_mapper: CoordinateMapper):
        self.coord_mapper = coordinate_mapper
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
            if fill.startswith('#'):
                # Convert hex color to RGB
                color = fill[1:]  # Remove #
                fill_xml = f'''<a:solidFill>
                    <a:srgbClr val="{color}"/>
                </a:solidFill>'''
            else:
                # Default fill
                fill_xml = '''<a:solidFill>
                    <a:srgbClr val="000000"/>
                </a:solidFill>'''
        else:
            fill_xml = "<a:noFill/>"
        
        # Handle stroke
        if stroke and stroke != 'none':
            width_emu = int(float(stroke_width) * 12700)  # Convert to EMUs
            if stroke.startswith('#'):
                color = stroke[1:]
                stroke_xml = f'''<a:ln w="{width_emu}">
                    <a:solidFill>
                        <a:srgbClr val="{color}"/>
                    </a:solidFill>
                </a:ln>'''
            else:
                stroke_xml = f'''<a:ln w="{width_emu}">
                    <a:solidFill>
                        <a:srgbClr val="000000"/>
                    </a:solidFill>
                </a:ln>'''
        
        return fill_xml + stroke_xml
    
    def _generate_stroke_only(self, attrs: Dict) -> str:
        """Generate stroke-only properties (for lines)."""
        stroke = attrs.get('stroke', 'black')
        stroke_width = attrs.get('stroke-width', '1')
        
        width_emu = int(float(stroke_width) * 12700)
        color = stroke[1:] if stroke.startswith('#') else "000000"
        
        return f'''<a:ln w="{width_emu}">
            <a:solidFill>
                <a:srgbClr val="{color}"/>
            </a:solidFill>
        </a:ln>'''


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
        
        # Set up DrawingML generator
        self.generator = DrawingMLGenerator(self.coord_mapper)
        
        # Convert each element
        drawingml_shapes = []
        for element in elements:
            shape_xml = self.generator.generate_shape(element)
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