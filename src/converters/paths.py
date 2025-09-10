"""
SVG Path to DrawingML Converter

Handles SVG path elements with support for:
- Move (M, m)
- Line (L, l, H, h, V, v)
- Cubic Bezier curves (C, c, S, s)
- Quadratic Bezier curves (Q, q, T, t)
- Arcs (A, a)
- Close path (Z, z)
"""

import re
import math
from typing import List, Tuple, Dict, Any
from lxml import etree as ET
from .base import BaseConverter, ConversionContext


class PathData:
    """Represents parsed SVG path data with commands and coordinates"""
    
    def __init__(self, path_string: str):
        self.commands = []
        self.parse(path_string)
    
    def parse(self, path_string: str):
        """Parse SVG path data string into commands and coordinates"""
        if not path_string:
            return
            
        # Clean and tokenize path data
        path_string = re.sub(r'[,\s]+', ' ', path_string.strip())
        
        # Split by commands while preserving the command character
        parts = re.split(r'([MmLlHhVvCcSsQqTtAaZz])', path_string)
        parts = [p.strip() for p in parts if p.strip()]
        
        current_command = None
        for part in parts:
            if re.match(r'[MmLlHhVvCcSsQqTtAaZz]', part):
                current_command = part
                # Handle commands that don't need coordinates (Z, z)
                if current_command.lower() == 'z':
                    self.commands.append((current_command, []))
            elif current_command and part:
                coords = [float(x) for x in part.split() if x]
                self.commands.append((current_command, coords))


class PathConverter(BaseConverter):
    """Converts SVG path elements to DrawingML custom geometry"""
    
    supported_elements = ['path']
    
    def __init__(self):
        super().__init__()
        self.current_pos = [0.0, 0.0]  # Current position
        self.last_control = None  # Last control point for smooth curves
        self.start_pos = [0.0, 0.0]  # Path start position for Z command
    
    def can_convert(self, element) -> bool:
        """Check if this converter can handle the element."""
        tag = self.get_element_tag(element)
        return tag == 'path'
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG path to DrawingML custom geometry with viewport-aware coordinate mapping"""
        path_data = element.get('d', '')
        if not path_data:
            return ""
        
        # Reset path state
        self.current_pos = [0.0, 0.0]
        self.last_control = None
        self.start_pos = [0.0, 0.0]
        
        # Parse path data
        path = PathData(path_data)
        
        # Initialize viewport-aware coordinate mapping if SVG root is available
        if context.svg_root is not None:
            self._initialize_viewport_mapping(context)
        
        # Handle transforms
        transform_matrix = self.get_element_transform_matrix(element, context.viewport_context)
        transform_xml = self._get_transform_xml(transform_matrix, context)
        
        # Convert to DrawingML path geometry
        geometry_xml = self._create_custom_geometry(path, context, transform_matrix)
        
        # Get style attributes
        style_attrs = self._get_style_attributes(element, context)
        
        return f"""<a:sp>
    <a:nvSpPr>
        <a:cNvPr id="{context.get_next_shape_id()}" name="Path"/>
        <a:cNvSpPr/>
    </a:nvSpPr>
    <a:spPr>
        {transform_xml}
        {geometry_xml}
        {style_attrs}
    </a:spPr>
</a:sp>"""
    
    def _get_transform_xml(self, matrix, context: ConversionContext) -> str:
        """Generate DrawingML transform XML from matrix"""
        if matrix.is_identity():
            return '<a:xfrm><a:off x="0" y="0"/><a:ext cx="21600" cy="21600"/></a:xfrm>'
        
        # Use the transform parser to generate DrawingML transform
        return self.transform_parser.to_drawingml_transform(matrix)
    
    def _create_custom_geometry(self, path: PathData, context: ConversionContext, transform_matrix=None) -> str:
        """Create DrawingML custom geometry from parsed path data"""
        path_commands = []
        
        for command, coords in path.commands:
            if command in ['M', 'm']:  # Move to
                path_commands.extend(self._handle_move(command, coords, context))
            elif command in ['L', 'l']:  # Line to
                path_commands.extend(self._handle_line(command, coords, context))
            elif command in ['H', 'h']:  # Horizontal line
                path_commands.extend(self._handle_horizontal_line(command, coords, context))
            elif command in ['V', 'v']:  # Vertical line
                path_commands.extend(self._handle_vertical_line(command, coords, context))
            elif command in ['C', 'c']:  # Cubic Bezier curve
                path_commands.extend(self._handle_cubic_curve(command, coords, context))
            elif command in ['S', 's']:  # Smooth cubic Bezier
                path_commands.extend(self._handle_smooth_cubic(command, coords, context))
            elif command in ['Q', 'q']:  # Quadratic Bezier curve
                path_commands.extend(self._handle_quadratic_curve(command, coords, context))
            elif command in ['T', 't']:  # Smooth quadratic Bezier
                path_commands.extend(self._handle_smooth_quadratic(command, coords, context))
            elif command in ['A', 'a']:  # Arc
                path_commands.extend(self._handle_arc(command, coords, context))
            elif command in ['Z', 'z']:  # Close path
                path_commands.append('<a:close/>')
        
        path_list = '\n                    '.join(path_commands)
        
        return f"""<a:custGeom>
            <a:avLst/>
            <a:gdLst/>
            <a:ahLst/>
            <a:cxnLst/>
            <a:rect l="0" t="0" r="21600" b="21600"/>
            <a:pathLst>
                <a:path w="21600" h="21600">
                    {path_list}
                </a:path>
            </a:pathLst>
        </a:custGeom>"""
    
    def _handle_move(self, command: str, coords: List[float], context: ConversionContext) -> List[str]:
        """Handle Move commands (M, m)"""
        commands = []
        absolute = command.isupper()
        
        # Process coordinate pairs
        for i in range(0, len(coords), 2):
            if i + 1 >= len(coords):
                break
                
            x, y = coords[i], coords[i + 1]
            
            if not absolute:
                x += self.current_pos[0]
                y += self.current_pos[1]
            
            # Convert to DrawingML coordinates using viewport-aware mapping
            dx, dy = self._convert_svg_to_drawingml_coords(x, y, context)
            
            if i == 0:  # First move is moveTo
                commands.append(f'<a:moveTo><a:pt x="{dx}" y="{dy}"/></a:moveTo>')
                self.start_pos = [x, y]
            else:  # Subsequent moves are lineTo
                commands.append(f'<a:lnTo><a:pt x="{dx}" y="{dy}"/></a:lnTo>')
            
            self.current_pos = [x, y]
            self.last_control = None
        
        return commands
    
    def _handle_line(self, command: str, coords: List[float], context: ConversionContext) -> List[str]:
        """Handle Line commands (L, l)"""
        commands = []
        absolute = command.isupper()
        
        for i in range(0, len(coords), 2):
            if i + 1 >= len(coords):
                break
                
            x, y = coords[i], coords[i + 1]
            
            if not absolute:
                x += self.current_pos[0]
                y += self.current_pos[1]
            
            dx, dy = self._convert_svg_to_drawingml_coords(x, y, context)
            
            commands.append(f'<a:lnTo><a:pt x="{dx}" y="{dy}"/></a:lnTo>')
            self.current_pos = [x, y]
        
        self.last_control = None
        return commands
    
    def _handle_horizontal_line(self, command: str, coords: List[float], context: ConversionContext) -> List[str]:
        """Handle Horizontal line commands (H, h)"""
        commands = []
        absolute = command.isupper()
        
        for x in coords:
            if not absolute:
                x += self.current_pos[0]
            
            dx, dy = self._convert_svg_to_drawingml_coords(x, self.current_pos[1], context)
            
            commands.append(f'<a:lnTo><a:pt x="{dx}" y="{dy}"/></a:lnTo>')
            self.current_pos[0] = x
        
        self.last_control = None
        return commands
    
    def _handle_vertical_line(self, command: str, coords: List[float], context: ConversionContext) -> List[str]:
        """Handle Vertical line commands (V, v)"""
        commands = []
        absolute = command.isupper()
        
        for y in coords:
            if not absolute:
                y += self.current_pos[1]
            
            dx, dy = self._convert_svg_to_drawingml_coords(self.current_pos[0], y, context)
            
            commands.append(f'<a:lnTo><a:pt x="{dx}" y="{dy}"/></a:lnTo>')
            self.current_pos[1] = y
        
        self.last_control = None
        return commands
    
    def _handle_cubic_curve(self, command: str, coords: List[float], context: ConversionContext) -> List[str]:
        """Handle Cubic Bezier curve commands (C, c)"""
        commands = []
        absolute = command.isupper()
        
        for i in range(0, len(coords), 6):
            if i + 5 >= len(coords):
                break
            
            x1, y1, x2, y2, x, y = coords[i:i+6]
            
            if not absolute:
                x1 += self.current_pos[0]
                y1 += self.current_pos[1]
                x2 += self.current_pos[0]
                y2 += self.current_pos[1]
                x += self.current_pos[0]
                y += self.current_pos[1]
            
            # Convert control points and end point using viewport-aware mapping
            dx1, dy1 = self._convert_svg_to_drawingml_coords(x1, y1, context)
            dx2, dy2 = self._convert_svg_to_drawingml_coords(x2, y2, context)
            dx, dy = self._convert_svg_to_drawingml_coords(x, y, context)
            
            commands.append(f'<a:cubicBezTo><a:pt x="{dx1}" y="{dy1}"/><a:pt x="{dx2}" y="{dy2}"/><a:pt x="{dx}" y="{dy}"/></a:cubicBezTo>')
            
            self.current_pos = [x, y]
            self.last_control = [x2, y2]  # Store for smooth curves
        
        return commands
    
    def _handle_smooth_cubic(self, command: str, coords: List[float], context: ConversionContext) -> List[str]:
        """Handle Smooth cubic Bezier commands (S, s)"""
        commands = []
        absolute = command.isupper()
        
        for i in range(0, len(coords), 4):
            if i + 3 >= len(coords):
                break
            
            x2, y2, x, y = coords[i:i+4]
            
            if not absolute:
                x2 += self.current_pos[0]
                y2 += self.current_pos[1]
                x += self.current_pos[0]
                y += self.current_pos[1]
            
            # Calculate first control point (reflection of last control point)
            if self.last_control:
                x1 = 2 * self.current_pos[0] - self.last_control[0]
                y1 = 2 * self.current_pos[1] - self.last_control[1]
            else:
                x1, y1 = self.current_pos
            
            # Convert all points
            dx1, dy1 = self._convert_svg_to_drawingml_coords(x1, y1, context)
            dx2, dy2 = self._convert_svg_to_drawingml_coords(x2, y2, context)
            dx, dy = self._convert_svg_to_drawingml_coords(x, y, context)
            
            commands.append(f'<a:cubicBezTo><a:pt x="{dx1}" y="{dy1}"/><a:pt x="{dx2}" y="{dy2}"/><a:pt x="{dx}" y="{dy}"/></a:cubicBezTo>')
            
            self.current_pos = [x, y]
            self.last_control = [x2, y2]
        
        return commands
    
    def _handle_quadratic_curve(self, command: str, coords: List[float], context: ConversionContext) -> List[str]:
        """Handle Quadratic Bezier curve commands (Q, q)"""
        commands = []
        absolute = command.isupper()
        
        for i in range(0, len(coords), 4):
            if i + 3 >= len(coords):
                break
            
            x1, y1, x, y = coords[i:i+4]
            
            if not absolute:
                x1 += self.current_pos[0]
                y1 += self.current_pos[1]
                x += self.current_pos[0]
                y += self.current_pos[1]
            
            # Convert quadratic to cubic Bezier
            # Control points for cubic: current + 2/3 * (quad_control - current)
            cx1 = self.current_pos[0] + (2/3) * (x1 - self.current_pos[0])
            cy1 = self.current_pos[1] + (2/3) * (y1 - self.current_pos[1])
            cx2 = x + (2/3) * (x1 - x)
            cy2 = y + (2/3) * (y1 - y)
            
            dx1, dy1 = self._convert_svg_to_drawingml_coords(cx1, cy1, context)
            dx2, dy2 = self._convert_svg_to_drawingml_coords(cx2, cy2, context)
            dx, dy = self._convert_svg_to_drawingml_coords(x, y, context)
            
            commands.append(f'<a:cubicBezTo><a:pt x="{dx1}" y="{dy1}"/><a:pt x="{dx2}" y="{dy2}"/><a:pt x="{dx}" y="{dy}"/></a:cubicBezTo>')
            
            self.current_pos = [x, y]
            self.last_control = [x1, y1]  # Store quadratic control point
        
        return commands
    
    def _handle_smooth_quadratic(self, command: str, coords: List[float], context: ConversionContext) -> List[str]:
        """Handle Smooth quadratic Bezier commands (T, t)"""
        commands = []
        absolute = command.isupper()
        
        for i in range(0, len(coords), 2):
            if i + 1 >= len(coords):
                break
            
            x, y = coords[i], coords[i + 1]
            
            if not absolute:
                x += self.current_pos[0]
                y += self.current_pos[1]
            
            # Calculate control point (reflection of last quadratic control)
            if self.last_control:
                x1 = 2 * self.current_pos[0] - self.last_control[0]
                y1 = 2 * self.current_pos[1] - self.last_control[1]
            else:
                x1, y1 = self.current_pos
            
            # Convert quadratic to cubic Bezier
            cx1 = self.current_pos[0] + (2/3) * (x1 - self.current_pos[0])
            cy1 = self.current_pos[1] + (2/3) * (y1 - self.current_pos[1])
            cx2 = x + (2/3) * (x1 - x)
            cy2 = y + (2/3) * (y1 - y)
            
            dx1, dy1 = self._convert_svg_to_drawingml_coords(cx1, cy1, context)
            dx2, dy2 = self._convert_svg_to_drawingml_coords(cx2, cy2, context)
            dx, dy = self._convert_svg_to_drawingml_coords(x, y, context)
            
            commands.append(f'<a:cubicBezTo><a:pt x="{dx1}" y="{dy1}"/><a:pt x="{dx2}" y="{dy2}"/><a:pt x="{dx}" y="{dy}"/></a:cubicBezTo>')
            
            self.current_pos = [x, y]
            self.last_control = [x1, y1]
        
        return commands
    
    def _handle_arc(self, command: str, coords: List[float], context: ConversionContext) -> List[str]:
        """Handle Arc commands (A, a) - approximated with cubic Bezier curves"""
        commands = []
        absolute = command.isupper()
        
        for i in range(0, len(coords), 7):
            if i + 6 >= len(coords):
                break
            
            rx, ry, x_axis_rotation, large_arc_flag, sweep_flag, x, y = coords[i:i+7]
            
            if not absolute:
                x += self.current_pos[0]
                y += self.current_pos[1]
            
            # Approximate arc with cubic Bezier curves
            arc_commands = self._arc_to_bezier(
                self.current_pos[0], self.current_pos[1],
                x, y, rx, ry, x_axis_rotation,
                large_arc_flag, sweep_flag, context
            )
            commands.extend(arc_commands)
            
            self.current_pos = [x, y]
        
        self.last_control = None
        return commands
    
    def _arc_to_bezier(self, x1: float, y1: float, x2: float, y2: float,
                      rx: float, ry: float, phi: float,
                      large_arc: int, sweep: int,
                      context: ConversionContext) -> List[str]:
        """Convert SVG arc to cubic Bezier curves"""
        # This is a simplified implementation
        # For production use, implement proper arc-to-bezier conversion
        
        # For now, just draw a straight line as fallback
        dx, dy = self._convert_svg_to_drawingml_coords(x2, y2, context)
        
        return [f'<a:lnTo><a:pt x="{dx}" y="{dy}"/></a:lnTo>']
    
    def _initialize_viewport_mapping(self, context: ConversionContext):
        """Initialize viewport-aware coordinate mapping using ViewportResolver."""
        try:
            # Use ViewportResolver to get proper viewport mapping
            viewport_mapping = self.viewport_resolver.resolve_svg_viewport(
                context.svg_root,
                target_width_emu=21600,  # DrawingML coordinate space
                target_height_emu=21600,
                context=context.viewport_context
            )
            
            # Store viewport mapping for coordinate conversion
            context.viewport_mapping = viewport_mapping
            
        except Exception as e:
            # Fallback to existing coordinate system if ViewportResolver fails
            self.logger.warning(f"ViewportResolver initialization failed: {e}, using fallback")
            context.viewport_mapping = None
    
    def _convert_svg_to_drawingml_coords(self, x: float, y: float, context: ConversionContext) -> tuple[int, int]:
        """Convert SVG coordinates to DrawingML coordinates using viewport-aware mapping."""
        if hasattr(context, 'viewport_mapping') and context.viewport_mapping is not None:
            # Use ViewportResolver mapping for accurate coordinate conversion
            return context.viewport_mapping.svg_to_emu(x, y)
        else:
            # Fallback to manual scaling for compatibility
            dx = int((x / context.coordinate_system.svg_width) * 21600)
            dy = int((y / context.coordinate_system.svg_height) * 21600)
            return dx, dy
    
    def _get_style_attributes(self, element: ET.Element, context: ConversionContext) -> str:
        """Get style attributes for the path element."""
        fill = self.get_attribute_with_style(element, 'fill', 'black')
        stroke = self.get_attribute_with_style(element, 'stroke', 'none')
        stroke_width = self.get_attribute_with_style(element, 'stroke-width', '1')
        opacity = self.get_attribute_with_style(element, 'opacity', '1')
        fill_opacity = self.get_attribute_with_style(element, 'fill-opacity', opacity)
        stroke_opacity = self.get_attribute_with_style(element, 'stroke-opacity', opacity)
        
        style_parts = []
        
        if fill and fill != 'none':
            style_parts.append(self.generate_fill(fill, fill_opacity, context))
        
        if stroke and stroke != 'none':
            style_parts.append(self.generate_stroke(stroke, stroke_width, stroke_opacity, context))
        
        return '\n        '.join(style_parts)