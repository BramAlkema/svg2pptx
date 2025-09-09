#!/usr/bin/env python3
"""
Shape converters for SVG to DrawingML conversion.

Handles basic shapes: rectangle, circle, ellipse, polygon, polyline.
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional
import math
import re

from .base import BaseConverter, ConversionContext


class RectangleConverter(BaseConverter):
    """Converter for SVG rectangle elements."""
    
    supported_elements = ['rect']
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the element."""
        tag = self.get_element_tag(element)
        return tag == 'rect'
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG rect to DrawingML."""
        # Extract attributes - keep as strings for unit parsing
        x_str = element.get('x', '0')
        y_str = element.get('y', '0')
        width_str = element.get('width', '0')
        height_str = element.get('height', '0')
        rx_str = element.get('rx', '0')
        ry_str = element.get('ry', '0')
        
        # Use new units system for batch conversion
        dimensions = context.batch_convert_to_emu({
            'x': x_str,
            'y': y_str,
            'width': width_str,
            'height': height_str,
            'rx': rx_str,
            'ry': ry_str
        })
        
        # Extract converted values
        emu_x = dimensions['x']
        emu_y = dimensions['y']
        emu_width = dimensions['width']
        emu_height = dimensions['height']
        rx_emu = dimensions['rx']
        ry_emu = dimensions['ry']
        
        # Handle rounded corners
        if rx_emu == 0 and ry_emu > 0:
            rx_emu = ry_emu
        elif ry_emu == 0 and rx_emu > 0:
            ry_emu = rx_emu
        
        # Get style attributes
        fill = self.get_attribute_with_style(element, 'fill', 'black')
        stroke = self.get_attribute_with_style(element, 'stroke', 'none')
        stroke_width = self.get_attribute_with_style(element, 'stroke-width', '1')
        opacity = self.get_attribute_with_style(element, 'opacity', '1')
        fill_opacity = self.get_attribute_with_style(element, 'fill-opacity', opacity)
        stroke_opacity = self.get_attribute_with_style(element, 'stroke-opacity', opacity)
        
        # Handle transforms
        transform = element.get('transform')
        transform_xml = self._generate_transform(transform, context) if transform else ''
        
        # Get shape ID
        shape_id = context.get_next_shape_id()
        
        # Determine shape preset
        if rx > 0 or ry > 0:
            # Rounded rectangle
            # Calculate corner radius as percentage (DrawingML uses percentage)
            corner_radius_x = min(50, (rx / width) * 100) if width > 0 else 0
            corner_radius_y = min(50, (ry / height) * 100) if height > 0 else 0
            corner_radius = max(corner_radius_x, corner_radius_y)
            
            shape_preset = f'''<a:prstGeom prst="roundRect">
                    <a:avLst>
                        <a:gd name="adj" fmla="val {int(corner_radius * 1000)}"/>
                    </a:avLst>
                </a:prstGeom>'''
        else:
            # Regular rectangle
            shape_preset = '''<a:prstGeom prst="rect">
                    <a:avLst/>
                </a:prstGeom>'''
        
        return f'''
        <p:sp>
            <p:nvSpPr>
                <p:cNvPr id="{shape_id}" name="Rectangle {shape_id}"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr>
                {transform_xml}
                <a:xfrm>
                    <a:off x="{emu_x}" y="{emu_y}"/>
                    <a:ext cx="{emu_width}" cy="{emu_height}"/>
                </a:xfrm>
                {shape_preset}
                {self.generate_fill(fill, fill_opacity, context)}
                {self.generate_stroke(stroke, stroke_width, stroke_opacity, context)}
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
    
    def _generate_transform(self, transform: str, context: ConversionContext) -> str:
        """Generate DrawingML transform from SVG transform."""
        # This is a placeholder - full implementation in TransformConverter
        return ''


class CircleConverter(BaseConverter):
    """Converter for SVG circle elements."""
    
    supported_elements = ['circle']
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the element."""
        tag = self.get_element_tag(element)
        return tag == 'circle'
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG circle to DrawingML."""
        # Extract attributes
        cx = self.parse_length(element.get('cx', '0'))
        cy = self.parse_length(element.get('cy', '0'))
        r = self.parse_length(element.get('r', '0'))
        
        # Convert to bounding box coordinates
        x = cx - r
        y = cy - r
        diameter = 2 * r
        
        # Convert to EMUs
        emu_x, emu_y = context.coordinate_system.svg_to_emu(x, y)
        emu_diameter = context.coordinate_system.svg_length_to_emu(diameter, 'x')
        
        # Get style attributes
        fill = self.get_attribute_with_style(element, 'fill', 'black')
        stroke = self.get_attribute_with_style(element, 'stroke', 'none')
        stroke_width = self.get_attribute_with_style(element, 'stroke-width', '1')
        opacity = self.get_attribute_with_style(element, 'opacity', '1')
        fill_opacity = self.get_attribute_with_style(element, 'fill-opacity', opacity)
        stroke_opacity = self.get_attribute_with_style(element, 'stroke-opacity', opacity)
        
        # Get shape ID
        shape_id = context.get_next_shape_id()
        
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
                {self.generate_fill(fill, fill_opacity, context)}
                {self.generate_stroke(stroke, stroke_width, stroke_opacity, context)}
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


class EllipseConverter(BaseConverter):
    """Converter for SVG ellipse elements."""
    
    supported_elements = ['ellipse']
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the element."""
        tag = self.get_element_tag(element)
        return tag == 'ellipse'
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG ellipse to DrawingML."""
        # Extract attributes
        cx = self.parse_length(element.get('cx', '0'))
        cy = self.parse_length(element.get('cy', '0'))
        rx = self.parse_length(element.get('rx', '0'))
        ry = self.parse_length(element.get('ry', '0'))
        
        # Convert to bounding box coordinates
        x = cx - rx
        y = cy - ry
        width = 2 * rx
        height = 2 * ry
        
        # Convert to EMUs
        emu_x, emu_y = context.coordinate_system.svg_to_emu(x, y)
        emu_width = context.coordinate_system.svg_length_to_emu(width, 'x')
        emu_height = context.coordinate_system.svg_length_to_emu(height, 'y')
        
        # Get style attributes
        fill = self.get_attribute_with_style(element, 'fill', 'black')
        stroke = self.get_attribute_with_style(element, 'stroke', 'none')
        stroke_width = self.get_attribute_with_style(element, 'stroke-width', '1')
        opacity = self.get_attribute_with_style(element, 'opacity', '1')
        fill_opacity = self.get_attribute_with_style(element, 'fill-opacity', opacity)
        stroke_opacity = self.get_attribute_with_style(element, 'stroke-opacity', opacity)
        
        # Get shape ID
        shape_id = context.get_next_shape_id()
        
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
                {self.generate_fill(fill, fill_opacity, context)}
                {self.generate_stroke(stroke, stroke_width, stroke_opacity, context)}
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


class PolygonConverter(BaseConverter):
    """Converter for SVG polygon and polyline elements."""
    
    supported_elements = ['polygon', 'polyline']
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the element."""
        tag = self.get_element_tag(element)
        return tag in ['polygon', 'polyline']
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG polygon/polyline to DrawingML."""
        tag = self.get_element_tag(element)
        points_str = element.get('points', '')
        
        if not points_str:
            return '<!-- Empty polygon/polyline -->'
        
        # Parse points
        points = self._parse_points(points_str)
        if len(points) < 2:
            return '<!-- Insufficient points for polygon/polyline -->'
        
        # Calculate bounding box
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        width = max_x - min_x
        height = max_y - min_y
        
        # Convert bounding box to EMUs
        emu_x, emu_y = context.coordinate_system.svg_to_emu(min_x, min_y)
        emu_width = context.coordinate_system.svg_length_to_emu(width, 'x')
        emu_height = context.coordinate_system.svg_length_to_emu(height, 'y')
        
        # Get style attributes
        fill = self.get_attribute_with_style(element, 'fill', 'black' if tag == 'polygon' else 'none')
        stroke = self.get_attribute_with_style(element, 'stroke', 'none' if tag == 'polygon' else 'black')
        stroke_width = self.get_attribute_with_style(element, 'stroke-width', '1')
        opacity = self.get_attribute_with_style(element, 'opacity', '1')
        fill_opacity = self.get_attribute_with_style(element, 'fill-opacity', opacity)
        stroke_opacity = self.get_attribute_with_style(element, 'stroke-opacity', opacity)
        
        # Generate path for custom geometry
        path_xml = self._generate_path(points, min_x, min_y, width, height, tag == 'polygon')
        
        # Get shape ID
        shape_id = context.get_next_shape_id()
        
        return f'''
        <p:sp>
            <p:nvSpPr>
                <p:cNvPr id="{shape_id}" name="{tag.capitalize()} {shape_id}"/>
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
                    <a:rect l="0" t="0" r="{emu_width}" b="{emu_height}"/>
                    <a:pathLst>
                        {path_xml}
                    </a:pathLst>
                </a:custGeom>
                {self.generate_fill(fill, fill_opacity, context)}
                {self.generate_stroke(stroke, stroke_width, stroke_opacity, context)}
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
    
    def _parse_points(self, points_str: str) -> List[Tuple[float, float]]:
        """Parse SVG points string into list of coordinate tuples."""
        points = []
        # Replace commas with spaces and split
        coords = re.split(r'[\s,]+', points_str.strip())
        
        # Group into pairs
        for i in range(0, len(coords) - 1, 2):
            try:
                x = float(coords[i])
                y = float(coords[i + 1])
                points.append((x, y))
            except (ValueError, IndexError):
                continue
        
        return points
    
    def _generate_path(self, points: List[Tuple[float, float]], 
                       min_x: float, min_y: float, 
                       width: float, height: float, 
                       close_path: bool) -> str:
        """Generate DrawingML path from points."""
        if not points:
            return ''
        
        # Scale points to path coordinate space (21600x21600 is standard)
        scale_x = 21600 / width if width > 0 else 1
        scale_y = 21600 / height if height > 0 else 1
        
        path_commands = []
        
        # Move to first point
        first_x = int((points[0][0] - min_x) * scale_x)
        first_y = int((points[0][1] - min_y) * scale_y)
        path_commands.append(f'''
                            <a:moveTo>
                                <a:pt x="{first_x}" y="{first_y}"/>
                            </a:moveTo>''')
        
        # Line to remaining points
        for point in points[1:]:
            x = int((point[0] - min_x) * scale_x)
            y = int((point[1] - min_y) * scale_y)
            path_commands.append(f'''
                            <a:lnTo>
                                <a:pt x="{x}" y="{y}"/>
                            </a:lnTo>''')
        
        # Close path for polygon
        if close_path:
            path_commands.append('''
                            <a:close/>''')
        
        return f'''
                        <a:path w="21600" h="21600">
                            {''.join(path_commands)}
                        </a:path>'''


class LineConverter(BaseConverter):
    """Converter for SVG line elements."""
    
    supported_elements = ['line']
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the element."""
        tag = self.get_element_tag(element)
        return tag == 'line'
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG line to DrawingML."""
        # Extract attributes
        x1 = self.parse_length(element.get('x1', '0'))
        y1 = self.parse_length(element.get('y1', '0'))
        x2 = self.parse_length(element.get('x2', '0'))
        y2 = self.parse_length(element.get('y2', '0'))
        
        # Calculate bounding box
        min_x = min(x1, x2)
        min_y = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        
        # Handle zero-dimension lines
        if width == 0 and height == 0:
            return '<!-- Zero-length line -->'
        
        # Convert to EMUs
        emu_x, emu_y = context.coordinate_system.svg_to_emu(min_x, min_y)
        emu_width = context.coordinate_system.svg_length_to_emu(width, 'x') if width > 0 else 1
        emu_height = context.coordinate_system.svg_length_to_emu(height, 'y') if height > 0 else 1
        
        # Get style attributes (lines typically only have stroke)
        stroke = self.get_attribute_with_style(element, 'stroke', 'black')
        stroke_width = self.get_attribute_with_style(element, 'stroke-width', '1')
        opacity = self.get_attribute_with_style(element, 'opacity', '1')
        stroke_opacity = self.get_attribute_with_style(element, 'stroke-opacity', opacity)
        
        # Determine line direction for path
        if x1 <= x2 and y1 <= y2:
            # Top-left to bottom-right
            start_x, start_y = 0, 0
            end_x, end_y = 21600, 21600
        elif x1 > x2 and y1 <= y2:
            # Top-right to bottom-left
            start_x, start_y = 21600, 0
            end_x, end_y = 0, 21600
        elif x1 <= x2 and y1 > y2:
            # Bottom-left to top-right
            start_x, start_y = 0, 21600
            end_x, end_y = 21600, 0
        else:
            # Bottom-right to top-left
            start_x, start_y = 21600, 21600
            end_x, end_y = 0, 0
        
        # Get shape ID
        shape_id = context.get_next_shape_id()
        
        return f'''
        <p:cxnSp>
            <p:nvCxnSpPr>
                <p:cNvPr id="{shape_id}" name="Line {shape_id}"/>
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
                        <a:path w="21600" h="21600">
                            <a:moveTo>
                                <a:pt x="{start_x}" y="{start_y}"/>
                            </a:moveTo>
                            <a:lnTo>
                                <a:pt x="{end_x}" y="{end_y}"/>
                            </a:lnTo>
                        </a:path>
                    </a:pathLst>
                </a:custGeom>
                {self.generate_stroke(stroke, stroke_width, stroke_opacity, context)}
            </p:spPr>
        </p:cxnSp>'''