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
        """Parse SVG viewBox attribute using canonical ViewportResolver."""
        viewbox = self.root.get('viewBox')
        if viewbox:
            try:
                # Use the canonical high-performance ViewportResolver for parsing
                from .viewbox import ViewportResolver
                import numpy as np

                resolver = ViewportResolver()
                parsed = resolver.parse_viewbox_strings(np.array([viewbox]))
                if len(parsed) > 0 and len(parsed[0]) >= 4:
                    return tuple(parsed[0][:4])
            except ImportError:
                # Fallback to legacy parsing if ViewportResolver not available
                pass
            except Exception:
                # Fallback on any parsing error
                pass

            # Legacy fallback - enhanced to handle commas
            try:
                cleaned = viewbox.strip().replace(',', ' ')
                values = [float(v) for v in cleaned.split()]
                if len(values) >= 4:
                    return tuple(values[:4])
            except (ValueError, IndexError):
                pass

        return (0, 0, self.width or 100, self.height or 100)
    
    def _parse_dimensions(self) -> Tuple[Optional[float], Optional[float]]:
        """Parse SVG width and height attributes."""
        width = self._parse_length(self.root.get('width'))
        height = self._parse_length(self.root.get('height'))
        return width, height
    
    def _parse_length(self, length_str: str) -> Optional[float]:
        """Parse SVG length values (with units).

        Supports:
        - Positive numbers: 5, 10.5, +15
        - Negative numbers: -5, -2.5px
        - Scientific notation: 1.5e2, 2.3E-1, -4.5e+3
        - Various units: px, pt, em, %, mm, cm, in
        """
        if not length_str:
            return None

        # Enhanced regex to handle negative numbers, positive signs, and scientific notation
        # Pattern breakdown:
        # [-+]? - optional positive or negative sign
        # (?:[0-9]+\.?[0-9]*|\.[0-9]+) - either digits.digits or .digits (valid number format)
        # (?:[eE][-+]?[0-9]+)? - optional complete scientific notation (e/E followed by optional sign and digits)
        # (?:[a-zA-Z%]*)? - optional units at the end
        # ^ and $ ensure complete string match to avoid partial matches
        pattern = r'^([-+]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][-+]?[0-9]+)?)(?:[a-zA-Z%]*)?$'
        match = re.match(pattern, length_str)

        # Additional validation: if string contains 'e' or 'E' immediately followed by end of string
        # or non-alphabetic characters (indicating incomplete scientific notation), reject it
        # This avoids rejecting valid units like 'em' while catching incomplete scientific notation like '5e'
        if re.search(r'\d[eE]$', length_str) or re.search(r'\d[eE][^a-zA-Z0-9+-]', length_str):
            return None
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                # Handle edge cases where regex matches but float conversion fails
                return None
        return None
    
    def extract_elements(self) -> List[Dict]:
        """Extract all drawable elements from SVG."""
        elements = []
        self._extract_recursive(self.root, elements)
        return elements
    
    def _extract_recursive(self, element: ET.Element, elements: List[Dict]) -> None:
        """Recursively extract elements from SVG tree."""
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        
        if tag in ['rect', 'circle', 'ellipse', 'line', 'path', 'polygon', 'polyline', 'text', 'image', 'g', 'use', 'symbol']:
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
        """Generate DrawingML for a single SVG element.

        TODO: Implement polygon/polyline DrawingML emission
        ==================================================
        PROBLEM: DrawingMLGenerator.generate_shape never handles 'polygon'
        or 'polyline' types, so those parsed elements fall into the
        "unsupported" branch and disappear from the output.

        FIX NEEDED: Add _generate_polygon() and _generate_polyline() methods
        and call them from this dispatch method.
        """
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
        elif element_type == 'polygon':
            return self._generate_polygon(svg_element)
        elif element_type == 'polyline':
            return self._generate_polyline(svg_element)
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
        """Generate DrawingML for SVG path (basic implementation).

        TODO: Convert SVG paths into actual DrawingML geometry
        ====================================================
        PROBLEM: _generate_path currently outputs a placeholder rectangle
        with comments instead of translating the SVG path data, so arbitrary
        <path> elements never become real vector shapes.

        FIX NEEDED: Parse SVG path data (d attribute) and convert to
        DrawingML custom geometry with proper commands (moveTo, lineTo,
        curveTo, etc.).
        """
        attrs = svg_element['attributes']
        path_data = attrs.get('d', '')

        # TODO: Parse path_data and convert to actual DrawingML geometry
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

    def _generate_polygon(self, svg_element: Dict) -> str:
        """Generate DrawingML for SVG polygon element.

        Converts SVG polygon with points attribute to DrawingML custom geometry.
        Polygons are closed shapes where the last point connects back to the first.
        """
        attrs = svg_element['attributes']
        points_str = attrs.get('points', '')

        if not points_str.strip():
            return f"<!-- Empty polygon points -->"

        # Parse points: "x1,y1 x2,y2 x3,y3" or "x1 y1 x2 y2 x3 y3"
        points = self._parse_points(points_str)
        if len(points) < 3:
            return f"<!-- Polygon needs at least 3 points, got {len(points)} -->"

        # Calculate bounding box for DrawingML transform
        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)

        width = max_x - min_x
        height = max_y - min_y

        # Convert to EMUs
        emu_x, emu_y = self.coord_mapper.svg_to_emu(min_x, min_y)
        emu_width = self.coord_mapper.svg_length_to_emu(width, 'x')
        emu_height = self.coord_mapper.svg_length_to_emu(height, 'y')

        shape_id = self.shape_id
        self.shape_id += 1

        # Generate path commands for polygon (closed shape)
        path_commands = self._generate_path_commands(points, min_x, min_y, width, height, closed=True)

        return f'''
        <p:sp>
            <p:nvSpPr>
                <p:cNvPr id="{shape_id}" name="Polygon {shape_id}"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="{emu_x}" y="{emu_y}"/>
                    <a:ext cx="{emu_width}" cy="{emu_height}"/>
                </a:xfrm>
                <a:custGeom>
                    <a:avLst/>
                    <a:gdLst/>
                    <a:ahLst/>
                    <a:cxnLst/>
                    <a:rect l="0" t="0" r="0" b="0"/>
                    <a:pathLst>
                        <a:path w="{emu_width}" h="{emu_height}">
                            {path_commands}
                        </a:path>
                    </a:pathLst>
                </a:custGeom>
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

    def _generate_polyline(self, svg_element: Dict) -> str:
        """Generate DrawingML for SVG polyline element.

        Converts SVG polyline with points attribute to DrawingML custom geometry.
        Polylines are open shapes (not closed like polygons).
        """
        attrs = svg_element['attributes']
        points_str = attrs.get('points', '')

        if not points_str.strip():
            return f"<!-- Empty polyline points -->"

        # Parse points: "x1,y1 x2,y2 x3,y3" or "x1 y1 x2 y2 x3 y3"
        points = self._parse_points(points_str)
        if len(points) < 2:
            return f"<!-- Polyline needs at least 2 points, got {len(points)} -->"

        # Calculate bounding box for DrawingML transform
        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)

        width = max_x - min_x if max_x != min_x else 1
        height = max_y - min_y if max_y != min_y else 1

        # Convert to EMUs
        emu_x, emu_y = self.coord_mapper.svg_to_emu(min_x, min_y)
        emu_width = self.coord_mapper.svg_length_to_emu(width, 'x')
        emu_height = self.coord_mapper.svg_length_to_emu(height, 'y')

        shape_id = self.shape_id
        self.shape_id += 1

        # Generate path commands for polyline (open shape)
        path_commands = self._generate_path_commands(points, min_x, min_y, width, height, closed=False)

        return f'''
        <p:cxnSp>
            <p:nvCxnSpPr>
                <p:cNvPr id="{shape_id}" name="Polyline {shape_id}"/>
                <p:cNvCxnSpPr/>
                <p:nvPr/>
            </p:nvCxnSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="{emu_x}" y="{emu_y}"/>
                    <a:ext cx="{emu_width}" cy="{emu_height}"/>
                </a:xfrm>
                <a:custGeom>
                    <a:avLst/>
                    <a:gdLst/>
                    <a:ahLst/>
                    <a:cxnLst/>
                    <a:rect l="0" t="0" r="0" b="0"/>
                    <a:pathLst>
                        <a:path w="{emu_width}" h="{emu_height}">
                            {path_commands}
                        </a:path>
                    </a:pathLst>
                </a:custGeom>
                {self._generate_stroke_only(attrs)}
            </p:spPr>
        </p:cxnSp>'''

    def _parse_points(self, points_str: str) -> List[Tuple[float, float]]:
        """Parse SVG points attribute into list of (x, y) tuples.

        Handles both comma-separated and space-separated formats:
        - "x1,y1 x2,y2 x3,y3"
        - "x1 y1 x2 y2 x3 y3"
        """
        points = []

        # Clean and normalize the points string
        points_str = points_str.strip()
        if not points_str:
            return points

        # Replace commas with spaces and split on whitespace
        normalized = points_str.replace(',', ' ')
        values = normalized.split()

        # Parse pairs of coordinates
        for i in range(0, len(values) - 1, 2):
            try:
                x = float(values[i])
                y = float(values[i + 1])
                points.append((x, y))
            except (ValueError, IndexError):
                # Skip invalid coordinate pairs
                continue

        return points

    def _generate_path_commands(self, points: List[Tuple[float, float]], min_x: float, min_y: float,
                               width: float, height: float, closed: bool = False) -> str:
        """Generate DrawingML path commands from points.

        Args:
            points: List of (x, y) coordinate tuples
            min_x, min_y: Bounding box origin for coordinate transformation
            width, height: Bounding box dimensions
            closed: Whether to close the path (for polygons)

        Returns:
            DrawingML path commands as XML string
        """
        if not points:
            return ""

        commands = []

        # Start with moveTo for first point
        first_x, first_y = points[0]
        rel_x = int(((first_x - min_x) / width) * 100000) if width > 0 else 0
        rel_y = int(((first_y - min_y) / height) * 100000) if height > 0 else 0

        commands.append(f'''
                            <a:moveTo>
                                <a:pt x="{rel_x}" y="{rel_y}"/>
                            </a:moveTo>''')

        # Add lineTo commands for remaining points
        for x, y in points[1:]:
            rel_x = int(((x - min_x) / width) * 100000) if width > 0 else 0
            rel_y = int(((y - min_y) / height) * 100000) if height > 0 else 0

            commands.append(f'''
                            <a:lnTo>
                                <a:pt x="{rel_x}" y="{rel_y}"/>
                            </a:lnTo>''')

        # Close path for polygons
        if closed:
            commands.append('''
                            <a:close/>''')

        return ''.join(commands)

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
        """Parse color value to hex string using canonical Color system."""
        try:
            # Use canonical Color class for parsing
            from .color import Color
            color_obj = Color(color.strip())
            # Get hex without '#' prefix for DrawingML compatibility
            return color_obj.hex().lstrip('#').upper()
        except (ValueError, TypeError):
            # Fallback to black for invalid colors
            return "000000"
    
    def _parse_rgb_color(self, rgb_str: str) -> str:
        """Parse rgb(r,g,b) string to hex using canonical Color system."""
        return self._parse_color(rgb_str)
    
    def _parse_rgb_fill(self, rgb_str: str) -> str:
        """Generate solid fill from rgb() color."""
        color = self._parse_rgb_color(rgb_str)
        return f'''<a:solidFill>
            <a:srgbClr val="{color}"/>
        </a:solidFill>'''
    
    def _color_name_to_hex(self, color_name: str) -> str:
        """Convert color name to hex value using canonical Color system."""
        return self._parse_color(color_name)


class SVGToDrawingMLConverter:
    """Main converter class that orchestrates the conversion process."""

    def __init__(self, services: 'ConversionServices' = None):
        """Initialize SVGToDrawingMLConverter with ConversionServices.

        Args:
            services: ConversionServices instance (required for new usage, optional for migration)
        """
        self.parser = None
        self.coord_mapper = None
        self.generator = None

        # Import here to avoid circular imports
        from .services.conversion_services import ConversionServices

        # Create default services if none provided (for migration compatibility)
        if services is None:
            services = ConversionServices.create_default()

        self.services = services
    
    def convert(self, svg_content: str) -> str:
        """Convert SVG content to DrawingML shapes."""
        # Parse SVG
        self.parser = SVGParser(svg_content)
        elements = self.parser.extract_elements()
        
        # Set up coordinate mapping
        self.coord_mapper = CoordinateMapper(self.parser.viewbox)
        
        # Get the converter registry with services
        registry = ConverterRegistryFactory.get_registry(services=self.services)
        
        # Create conversion context with proper coordinate system
        svg_root = ET.fromstring(svg_content)
        coord_sys = CoordinateSystem(self.parser.viewbox)
        context = ConversionContext(svg_root, services=self.services)
        context.coordinate_system = coord_sys
        
        # Add parsed gradients to context
        context.gradients = self.parser.gradients

        # Register gradients with gradient service for DrawingML conversion
        if self.parser.gradients and self.services.gradient_service:
            svg_root = ET.fromstring(svg_content)
            defs = svg_root.find('.//defs') or svg_root.find('.//{http://www.w3.org/2000/svg}defs')
            if defs is not None:
                # Register linear gradients
                for grad in defs.findall('.//linearGradient') or defs.findall('.//{http://www.w3.org/2000/svg}linearGradient'):
                    grad_id = grad.get('id')
                    if grad_id:
                        self.services.gradient_service.register_gradient(grad_id, grad)

                # Register radial gradients
                for grad in defs.findall('.//radialGradient') or defs.findall('.//{http://www.w3.org/2000/svg}radialGradient'):
                    grad_id = grad.get('id')
                    if grad_id:
                        self.services.gradient_service.register_gradient(grad_id, grad)

                # Register patterns
                for pattern in defs.findall('.//pattern') or defs.findall('.//{http://www.w3.org/2000/svg}pattern'):
                    pattern_id = pattern.get('id')
                    if pattern_id:
                        self.services.pattern_service.register_pattern(pattern_id, pattern)

                # Register filters
                for filter_elem in defs.findall('.//filter') or defs.findall('.//{http://www.w3.org/2000/svg}filter'):
                    filter_id = filter_elem.get('id')
                    if filter_id:
                        self.services.filter_service.register_filter(filter_id, filter_elem)
        
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