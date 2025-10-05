#!/usr/bin/env python3
"""
DrawingML Generator for Path Processing

This module implements the DrawingMLGenerator interface for converting processed
path commands into PowerPoint-compatible XML format. It handles all SVG path
command types and generates proper DrawingML structure.

Key Features:
- Converts all SVG path commands to DrawingML format
- Proper coordinate transformation integration
- Complete shape XML generation with styling
- Error handling and validation
- Support for relative coordinate system
"""

import logging
from typing import List, Dict, Any
from xml.sax.saxutils import escape

# Add lxml imports for safe XML generation
try:
    from lxml import etree
    from lxml.builder import E
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False

from .interfaces import DrawingMLGenerator as BaseDrawingMLGenerator
from .architecture import (
    PathCommand, PathBounds, PathCommandType, CoordinatePoint,
    XMLGenerationError
)

logger = logging.getLogger(__name__)


class DrawingMLGenerator(BaseDrawingMLGenerator):
    """
    Generates PowerPoint-compatible DrawingML XML from processed path commands.

    This generator converts structured path commands into the specific XML format
    required by PowerPoint, handling coordinate transformations through the
    provided coordinate system and ensuring proper XML structure.

    Example Usage:
        ```python
        generator = DrawingMLGenerator()

        # Generate path XML
        path_xml = generator.generate_path_xml(
            commands=path_commands,
            bounds=path_bounds,
            coordinate_system=coord_system,
            arc_converter=arc_converter
        )

        # Generate complete shape XML
        shape_xml = generator.generate_shape_xml(
            path_xml=path_xml,
            bounds=path_bounds,
            style_attributes={'fill': '#FF0000', 'stroke': '#000000'}
        )
        ```
    """

    def __init__(self, enable_logging: bool = True):
        """
        Initialize the DrawingML generator with lxml.builder infrastructure.

        Args:
            enable_logging: Whether to enable debug logging
        """
        super().__init__(enable_logging)

        # DrawingML namespace constants for safe XML generation
        self.A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
        self.nsmap = {'a': self.A_NS}

        # Check lxml availability and configure XML generation mode
        self.use_lxml = LXML_AVAILABLE
        if not self.use_lxml:
            logger.warning("lxml not available, falling back to string concatenation for XML generation")

        # Command mapping for DrawingML generation
        self._command_handlers = {
            PathCommandType.MOVE_TO: self._generate_move_to,
            PathCommandType.LINE_TO: self._generate_line_to,
            PathCommandType.HORIZONTAL: self._generate_horizontal_line,
            PathCommandType.VERTICAL: self._generate_vertical_line,
            PathCommandType.CUBIC_CURVE: self._generate_cubic_curve,
            PathCommandType.SMOOTH_CUBIC: self._generate_smooth_cubic,
            PathCommandType.QUADRATIC: self._generate_quadratic_curve,
            PathCommandType.SMOOTH_QUAD: self._generate_smooth_quadratic,
            PathCommandType.ARC: self._generate_arc,
            PathCommandType.CLOSE_PATH: self._generate_close_path,
        }

        # State tracking for smooth curves (S/T commands)
        self._last_cmd = None
        self._last_c2 = None   # Previous cubic control point (cx2, cy2)
        self._last_qc = None   # Previous quadratic control point (x1, y1)

        self.log_debug("DrawingMLGenerator initialized")

    def _create_element(self, tag_name: str, **attributes):
        """
        Create namespace-aware XML element using lxml.builder.

        Args:
            tag_name: Element tag name (without namespace)
            **attributes: Element attributes

        Returns:
            lxml Element if available, otherwise None for fallback to string generation
        """
        if not self.use_lxml:
            return None

        # Create fully qualified tag name with namespace
        qualified_tag = f"{{{self.A_NS}}}{tag_name}"
        return E(qualified_tag, **attributes)

    def generate_path_xml(self, commands: List[PathCommand], bounds: PathBounds,
                         coordinate_system, arc_converter, shape_id: int = None) -> str:
        """
        Generate DrawingML path XML for a series of path commands.

        Uses the coordinate system for all transformations and arc converter
        for arc processing. Generates valid PowerPoint XML structure.

        Args:
            commands: List of path commands with SVG coordinates
            bounds: Path bounding box (for coordinate transformations)
            coordinate_system: Coordinate transformation system
            arc_converter: Arc to bezier converter

        Returns:
            DrawingML path XML string

        Raises:
            XMLGenerationError: If XML generation fails
        """
        try:
            if not commands:
                return ""

            self.log_debug(f"Generating DrawingML for {len(commands)} path commands")

            # Reset state tracking for smooth curves
            self._last_cmd = None
            self._last_c2 = None
            self._last_qc = None

            # Generate individual command XML elements
            path_elements = []
            current_point = CoordinatePoint(x=0, y=0, coordinate_system='svg')

            for i, command in enumerate(commands):
                try:
                    # Handle arc commands by converting to bezier curves first
                    if command.command_type == PathCommandType.ARC:
                        bezier_commands = arc_converter.convert_arc_command(command, current_point)
                        for bc in bezier_commands:
                            xml = self._generate_command_xml(bc, coordinate_system, bounds, current_point)
                            if xml:
                                path_elements.append(xml)
                            current_point = self._update_current_point(bc, current_point)
                        # Update continuity for smooth curves (S commands)
                        if bezier_commands:
                            p = bezier_commands[-1].parameters
                            self._last_cmd = 'C'
                            self._last_c2 = (p[2], p[3])  # cx2, cy2 from cubic bezier
                        continue
                    else:
                        element_xml = self._generate_command_xml(
                            command, coordinate_system, bounds, current_point
                        )
                        # Check for None explicitly (handles both Element and string)
                        if element_xml is not None:
                            path_elements.append(element_xml)

                        # Update current point based on command
                        current_point = self._update_current_point(command, current_point)

                except Exception as e:
                    self.log_error(f"Failed to generate XML for command {i}: {e}")
                    # Continue with other commands

            if not path_elements:
                return ""

            # Create the complete path XML structure
            # When using lxml, elements are Element objects that need serialization
            if self.use_lxml:
                # Serialize lxml Element objects to XML strings
                path_content = ''.join(
                    etree.tostring(elem, encoding='unicode') if isinstance(elem, etree._Element) else str(elem)
                    for elem in path_elements
                )
            else:
                # String concatenation for fallback mode
                path_content = ''.join(path_elements)

            # Use normalized coordinates (0-100000 range) for path dimensions
            path_xml = f'''<a:pathLst xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
                <a:path w="100000" h="100000">
                    {path_content}
                </a:path>
            </a:pathLst>'''

            self.log_debug(f"Generated DrawingML path XML with {len(path_elements)} elements")
            return path_xml

        except Exception as e:
            raise XMLGenerationError(f"Failed to generate path XML: {e}")

    def generate_shape_xml(self, path_xml: str, bounds: PathBounds,
                          style_attributes: Dict[str, Any]) -> str:
        """
        Generate complete PowerPoint shape XML with path and styling.

        Creates a complete PowerPoint shape with the provided path XML
        and applies styling based on SVG style attributes.

        Args:
            path_xml: Generated path XML from generate_path_xml()
            bounds: Shape bounds in EMU coordinates
            style_attributes: SVG style attributes (fill, stroke, etc.)

        Returns:
            Complete PowerPoint shape XML string

        Raises:
            XMLGenerationError: If XML generation fails
        """
        try:
            if not path_xml:
                return ""

            self.log_debug("Generating complete shape XML with styling")

            # Extract styling information
            fill_xml = self._generate_fill_xml(style_attributes)
            stroke_xml = self._generate_stroke_xml(style_attributes)

            # Create shape properties
            shape_props = f"""<p:spPr>
                <a:xfrm>
                    <a:off x="{int(bounds.min_x)}" y="{int(bounds.min_y)}"/>
                    <a:ext cx="{int(bounds.width)}" cy="{int(bounds.height)}"/>
                </a:xfrm>
                <a:custGeom>
                    <a:avLst/>
                    <a:gdLst/>
                    <a:ahLst/>
                    <a:cxnLst/>
                    <a:rect l="0" t="0" r="100000" b="100000"/>
                    {path_xml}
                </a:custGeom>
                {fill_xml}
                {stroke_xml}
            </p:spPr>"""

            # Generate unique shape ID
            import time
            shape_id = int(time.time() * 1000) % 1000000  # Use timestamp for uniqueness

            # Create complete shape XML
            shape_xml = f"""<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
                <p:nvSpPr>
                    <p:cNvPr id="{shape_id}" name="Custom Shape {shape_id}"/>
                    <p:cNvSpPr/>
                    <p:nvPr/>
                </p:nvSpPr>
                {shape_props}
                <p:style>
                    <a:lnRef idx="1">
                        <a:schemeClr val="accent1"/>
                    </a:lnRef>
                    <a:fillRef idx="3">
                        <a:schemeClr val="accent1"/>
                    </a:fillRef>
                    <a:effectRef idx="2">
                        <a:schemeClr val="accent1"/>
                    </a:effectRef>
                    <a:fontRef idx="minor">
                        <a:schemeClr val="lt1"/>
                    </a:fontRef>
                </p:style>
                <p:txBody>
                    <a:bodyPr rtlCol="0" anchor="ctr"/>
                    <a:lstStyle/>
                    <a:p>
                        <a:pPr algn="ctr"/>
                        <a:endParaRPr/>
                    </a:p>
                </p:txBody>
            </p:sp>"""

            self.log_debug("Generated complete shape XML")
            return shape_xml

        except Exception as e:
            raise XMLGenerationError(f"Failed to generate shape XML: {e}")

    def _generate_command_xml(self, command: PathCommand, coordinate_system,
                            bounds: PathBounds, current_point: CoordinatePoint) -> str:
        """Generate XML for a specific path command."""
        handler = self._command_handlers.get(command.command_type)
        if handler:
            return handler(command, coordinate_system, bounds, current_point)
        else:
            self.log_error(f"No handler for command type: {command.command_type}")
            return ""

    def _generate_move_to(self, command: PathCommand, coordinate_system,
                         bounds: PathBounds, current_point: CoordinatePoint):
        """Generate DrawingML for MOVE_TO command using lxml.builder for safety."""
        if len(command.parameters) < 2:
            return "" if not self.use_lxml else None

        x, y = command.parameters[0], command.parameters[1]

        # Handle relative coordinates
        if command.is_relative and current_point:
            x += current_point.x
            y += current_point.y

        rel_x, rel_y = coordinate_system.svg_to_relative(x, y, bounds)

        if self.use_lxml:
            # Use lxml.builder for safe XML generation
            pt_element = self._create_element("pt",
                                            x=self._format_coordinate(rel_x),
                                            y=self._format_coordinate(rel_y))
            move_element = self._create_element("moveTo")
            move_element.append(pt_element)
            return move_element
        else:
            # Fallback to string concatenation
            return f'<a:moveTo><a:pt x="{self._format_coordinate(rel_x)}" y="{self._format_coordinate(rel_y)}"/></a:moveTo>'

    def _generate_line_to(self, command: PathCommand, coordinate_system,
                         bounds: PathBounds, current_point: CoordinatePoint):
        """Generate DrawingML for LINE_TO command using lxml.builder for safety."""
        if len(command.parameters) < 2:
            return "" if not self.use_lxml else None

        x, y = command.parameters[0], command.parameters[1]

        # Handle relative coordinates
        if command.is_relative and current_point:
            x += current_point.x
            y += current_point.y

        rel_x, rel_y = coordinate_system.svg_to_relative(x, y, bounds)

        if self.use_lxml:
            # Use lxml.builder for safe XML generation
            pt_element = self._create_element("pt",
                                            x=self._format_coordinate(rel_x),
                                            y=self._format_coordinate(rel_y))
            line_element = self._create_element("lnTo")
            line_element.append(pt_element)
            return line_element
        else:
            # Fallback to string concatenation
            return f'<a:lnTo><a:pt x="{self._format_coordinate(rel_x)}" y="{self._format_coordinate(rel_y)}"/></a:lnTo>'

    def _generate_horizontal_line(self, command: PathCommand, coordinate_system,
                                bounds: PathBounds, current_point: CoordinatePoint) -> str:
        """Generate DrawingML for HORIZONTAL line command."""
        if len(command.parameters) < 1:
            return ""

        x = command.parameters[0]
        if command.is_relative:
            x = current_point.x + x
        # Use current point's y coordinate
        y = current_point.y
        rel_x, rel_y = coordinate_system.svg_to_relative(x, y, bounds)

        return f'<a:lnTo><a:pt x="{self._format_coordinate(rel_x)}" y="{self._format_coordinate(rel_y)}"/></a:lnTo>'

    def _generate_vertical_line(self, command: PathCommand, coordinate_system,
                              bounds: PathBounds, current_point: CoordinatePoint) -> str:
        """Generate DrawingML for VERTICAL line command."""
        if len(command.parameters) < 1:
            return ""

        y = command.parameters[0]
        if command.is_relative:
            y = current_point.y + y
        x = current_point.x
        rel_x, rel_y = coordinate_system.svg_to_relative(x, y, bounds)

        return f'<a:lnTo><a:pt x="{self._format_coordinate(rel_x)}" y="{self._format_coordinate(rel_y)}"/></a:lnTo>'

    def _generate_cubic_curve(self, command: PathCommand, coordinate_system,
                            bounds: PathBounds, current_point: CoordinatePoint) -> str:
        """Generate DrawingML for CUBIC_CURVE command."""
        if len(command.parameters) < 6:
            return ""

        # Parameters: cx1, cy1, cx2, cy2, x, y
        cx1, cy1 = command.parameters[0], command.parameters[1]
        cx2, cy2 = command.parameters[2], command.parameters[3]
        x, y = command.parameters[4], command.parameters[5]

        # Handle relative coordinates
        if command.is_relative and current_point:
            cx1 += current_point.x
            cy1 += current_point.y
            cx2 += current_point.x
            cy2 += current_point.y
            x += current_point.x
            y += current_point.y

        # Update state for smooth curves
        self._last_cmd = 'C'
        self._last_c2 = (cx2, cy2)

        # Transform all control points
        rel_x1, rel_y1 = coordinate_system.svg_to_relative(cx1, cy1, bounds)
        rel_x2, rel_y2 = coordinate_system.svg_to_relative(cx2, cy2, bounds)
        rel_x, rel_y = coordinate_system.svg_to_relative(x, y, bounds)

        return f'''<a:cubicBezTo>
                        <a:pt x="{self._format_coordinate(rel_x1)}" y="{self._format_coordinate(rel_y1)}"/>
                        <a:pt x="{self._format_coordinate(rel_x2)}" y="{self._format_coordinate(rel_y2)}"/>
                        <a:pt x="{self._format_coordinate(rel_x)}" y="{self._format_coordinate(rel_y)}"/>
                    </a:cubicBezTo>'''

    def _generate_smooth_cubic(self, command: PathCommand, coordinate_system,
                             bounds: PathBounds, current_point: CoordinatePoint) -> str:
        """Generate DrawingML for SMOOTH_CUBIC command."""
        if len(command.parameters) < 4:
            return ""

        # Parameters: x2, y2, x, y
        x2, y2 = command.parameters[0], command.parameters[1]
        x, y = command.parameters[2], command.parameters[3]

        if command.is_relative:
            x2 += current_point.x
            y2 += current_point.y
            x += current_point.x
            y += current_point.y

        # Calculate first control point by reflecting previous control point
        if self._last_cmd in ['C', 'S'] and self._last_c2 is not None:
            # Reflect the last control point across current_point
            cx1 = 2 * current_point.x - self._last_c2[0]
            cy1 = 2 * current_point.y - self._last_c2[1]
        else:
            # No previous curve, use current point
            cx1, cy1 = current_point.x, current_point.y

        # Update state for next smooth curve
        self._last_cmd = 'S'
        self._last_c2 = (x2, y2)

        rel_x1, rel_y1 = coordinate_system.svg_to_relative(cx1, cy1, bounds)
        rel_x2, rel_y2 = coordinate_system.svg_to_relative(x2, y2, bounds)
        rel_x, rel_y = coordinate_system.svg_to_relative(x, y, bounds)

        return f'''<a:cubicBezTo>
                        <a:pt x="{self._format_coordinate(rel_x1)}" y="{self._format_coordinate(rel_y1)}"/>
                        <a:pt x="{self._format_coordinate(rel_x2)}" y="{self._format_coordinate(rel_y2)}"/>
                        <a:pt x="{self._format_coordinate(rel_x)}" y="{self._format_coordinate(rel_y)}"/>
                    </a:cubicBezTo>'''

    def _generate_quadratic_curve(self, command: PathCommand, coordinate_system,
                                bounds: PathBounds, current_point: CoordinatePoint) -> str:
        """Generate DrawingML for QUADRATIC curve command."""
        if len(command.parameters) < 4:
            return ""

        # Parameters: x1, y1, x, y
        x1, y1 = command.parameters[0], command.parameters[1]
        x, y = command.parameters[2], command.parameters[3]

        # Handle relative coordinates
        if command.is_relative:
            x1 += current_point.x
            y1 += current_point.y
            x += current_point.x
            y += current_point.y

        # Update state for smooth curves
        self._last_cmd = 'Q'
        self._last_qc = (x1, y1)

        # Quadratic to cubic conversion: CP1 = P0 + 2/3(P1 - P0), CP2 = P2 + 2/3(P1 - P2)
        cp1_x = current_point.x + (2/3) * (x1 - current_point.x)
        cp1_y = current_point.y + (2/3) * (y1 - current_point.y)
        cp2_x = x + (2/3) * (x1 - x)
        cp2_y = y + (2/3) * (y1 - y)

        # Transform control points
        rel_cp1_x, rel_cp1_y = coordinate_system.svg_to_relative(cp1_x, cp1_y, bounds)
        rel_cp2_x, rel_cp2_y = coordinate_system.svg_to_relative(cp2_x, cp2_y, bounds)
        rel_x, rel_y = coordinate_system.svg_to_relative(x, y, bounds)

        return f'''<a:cubicBezTo>
                        <a:pt x="{self._format_coordinate(rel_cp1_x)}" y="{self._format_coordinate(rel_cp1_y)}"/>
                        <a:pt x="{self._format_coordinate(rel_cp2_x)}" y="{self._format_coordinate(rel_cp2_y)}"/>
                        <a:pt x="{self._format_coordinate(rel_x)}" y="{self._format_coordinate(rel_y)}"/>
                    </a:cubicBezTo>'''

    def _generate_smooth_quadratic(self, command: PathCommand, coordinate_system,
                                 bounds: PathBounds, current_point: CoordinatePoint) -> str:
        """Generate DrawingML for SMOOTH_QUAD command."""
        if len(command.parameters) < 2:
            return ""

        # Parameters: x, y
        x, y = command.parameters[0], command.parameters[1]

        if command.is_relative:
            x += current_point.x
            y += current_point.y

        # Calculate control point by reflecting previous control point
        if self._last_cmd in ['Q', 'T'] and self._last_qc is not None:
            # Reflect the last control point across current_point
            cx = 2 * current_point.x - self._last_qc[0]
            cy = 2 * current_point.y - self._last_qc[1]
        else:
            # No previous curve, use current point
            cx, cy = current_point.x, current_point.y

        # Update state for next smooth curve
        self._last_cmd = 'T'
        self._last_qc = (cx, cy)

        # Convert quadratic to cubic bezier
        # Cubic control points are at 2/3 of the way from endpoints to the quadratic control point
        cx1 = current_point.x + 2/3 * (cx - current_point.x)
        cy1 = current_point.y + 2/3 * (cy - current_point.y)
        cx2 = x + 2/3 * (cx - x)
        cy2 = y + 2/3 * (cy - y)

        rel_x1, rel_y1 = coordinate_system.svg_to_relative(cx1, cy1, bounds)
        rel_x2, rel_y2 = coordinate_system.svg_to_relative(cx2, cy2, bounds)
        rel_x, rel_y = coordinate_system.svg_to_relative(x, y, bounds)

        return f'''<a:cubicBezTo>
                        <a:pt x="{self._format_coordinate(rel_x1)}" y="{self._format_coordinate(rel_y1)}"/>
                        <a:pt x="{self._format_coordinate(rel_x2)}" y="{self._format_coordinate(rel_y2)}"/>
                        <a:pt x="{self._format_coordinate(rel_x)}" y="{self._format_coordinate(rel_y)}"/>
                    </a:cubicBezTo>'''

    def _generate_arc(self, command: PathCommand, coordinate_system,
                     bounds: PathBounds, current_point: CoordinatePoint) -> str:
        """Generate DrawingML for ARC command (should not be called directly)."""
        # Arc commands should be converted to bezier curves before reaching this point
        self.log_error("Arc command reached DrawingML generator - should be converted to bezier first")
        return ""

    def _generate_close_path(self, command: PathCommand, coordinate_system,
                           bounds: PathBounds, current_point: CoordinatePoint) -> str:
        """Generate DrawingML for CLOSE_PATH command."""
        return '<a:close/>'

    def _update_current_point(self, command: PathCommand, current_point: CoordinatePoint) -> CoordinatePoint:
        """Update the current point based on the command."""
        if command.command_type == PathCommandType.MOVE_TO and len(command.parameters) >= 2:
            return CoordinatePoint(x=command.parameters[0], y=command.parameters[1], coordinate_system='svg')
        elif command.command_type == PathCommandType.LINE_TO and len(command.parameters) >= 2:
            return CoordinatePoint(x=command.parameters[0], y=command.parameters[1], coordinate_system='svg')
        elif command.command_type == PathCommandType.HORIZONTAL and len(command.parameters) >= 1:
            return CoordinatePoint(x=command.parameters[0], y=current_point.y, coordinate_system='svg')
        elif command.command_type == PathCommandType.VERTICAL and len(command.parameters) >= 1:
            return CoordinatePoint(x=current_point.x, y=command.parameters[0], coordinate_system='svg')
        elif command.command_type == PathCommandType.CUBIC_CURVE and len(command.parameters) >= 6:
            return CoordinatePoint(x=command.parameters[4], y=command.parameters[5], coordinate_system='svg')
        elif command.command_type == PathCommandType.SMOOTH_CUBIC and len(command.parameters) >= 4:
            return CoordinatePoint(x=command.parameters[2], y=command.parameters[3], coordinate_system='svg')
        elif command.command_type == PathCommandType.QUADRATIC and len(command.parameters) >= 4:
            return CoordinatePoint(x=command.parameters[2], y=command.parameters[3], coordinate_system='svg')
        elif command.command_type == PathCommandType.SMOOTH_QUAD and len(command.parameters) >= 2:
            return CoordinatePoint(x=command.parameters[0], y=command.parameters[1], coordinate_system='svg')
        elif command.command_type == PathCommandType.ARC and len(command.parameters) >= 7:
            # Arc parameters: rx, ry, x-axis-rotation, large-arc-flag, sweep-flag, x, y
            # End point is the last two parameters
            return CoordinatePoint(x=command.parameters[5], y=command.parameters[6], coordinate_system='svg')
        elif command.command_type == PathCommandType.CLOSE_PATH:
            return current_point  # Close path doesn't change current point
        else:
            return current_point

    def _generate_fill_xml(self, style_attributes: Dict[str, Any]) -> str:
        """Generate fill XML from style attributes."""
        fill = style_attributes.get('fill', 'black')
        opacity = style_attributes.get('fill-opacity') or style_attributes.get('opacity')

        if fill == 'none':
            return '<a:noFill/>'
        elif fill.startswith('#'):
            # Convert hex color using existing color system
            color = self._to_hex(fill)
            alpha_xml = self._alpha_xml(opacity)
            return f'<a:solidFill><a:srgbClr val="{color}">{alpha_xml}</a:srgbClr></a:solidFill>'
        else:
            # Default to black for unknown colors
            alpha_xml = self._alpha_xml(opacity)
            return f'<a:solidFill><a:srgbClr val="000000">{alpha_xml}</a:srgbClr></a:solidFill>'

    def _generate_stroke_xml(self, style_attributes: Dict[str, Any]) -> str:
        """Generate stroke/line XML from style attributes."""
        stroke = style_attributes.get('stroke', 'none')
        stroke_width = style_attributes.get('stroke-width', '1')

        if stroke == 'none':
            return ''

        # Convert stroke width to EMU using the units system
        try:
            if hasattr(self, 'services') and self.services and hasattr(self.services, 'unit_converter'):
                # Use the existing unit converter
                width_emu = self.services.unit_converter.to_emu(f"{stroke_width}px")
            else:
                # Fallback conversion: SVG px to pt (*0.75), then pt to EMU (*12700)
                width_px = float(stroke_width)
                width_pt = width_px * 0.75
                width_emu = int(width_pt * 12700)
        except (ValueError, TypeError):
            width_emu = 12700  # Default 1pt

        # Get stroke opacity
        stroke_opacity = style_attributes.get('stroke-opacity') or style_attributes.get('opacity')

        if stroke.startswith('#'):
            # Convert hex color using existing color system
            color = self._to_hex(stroke)
            alpha_xml = self._alpha_xml(stroke_opacity)
            return f'<a:ln w="{width_emu}"><a:solidFill><a:srgbClr val="{color}">{alpha_xml}</a:srgbClr></a:solidFill></a:ln>'
        else:
            # Default to black stroke
            alpha_xml = self._alpha_xml(stroke_opacity)
            return f'<a:ln w="{width_emu}"><a:solidFill><a:srgbClr val="000000">{alpha_xml}</a:srgbClr></a:solidFill></a:ln>'

    def validate_xml_output(self, xml_string: str) -> bool:
        """
        Validate that the generated XML is well-formed.

        Args:
            xml_string: The XML string to validate

        Returns:
            True if XML is valid, False otherwise
        """
        try:
            from lxml import etree
            etree.fromstring(xml_string.encode())
            return True
        except etree.ParseError:
            return False
        except Exception:
            return False

    def _to_hex(self, color_value) -> str:
        """Convert color value to hex format using existing color system."""
        # Use the existing color parser from services
        try:
            if hasattr(self, 'services') and self.services and hasattr(self.services, 'color_parser'):
                color_obj = self.services.color_parser(color_value)
                return color_obj.hex.lstrip('#').upper()
        except Exception:
            pass

        # Fallback for simple hex colors
        if isinstance(color_value, str) and color_value.startswith('#'):
            color = color_value[1:]
            if len(color) == 3:
                color = ''.join([c*2 for c in color])
            return color.upper()
        return "000000"

    def _alpha_xml(self, opacity) -> str:
        """Generate alpha XML for opacity values."""
        if opacity is None or opacity == 1.0:
            return ""

        try:
            opacity_val = float(opacity)
            if opacity_val >= 1.0:
                return ""

            # Convert to percentage for DrawingML (0.5 -> 50000)
            alpha_pct = int(opacity_val * 100000)
            return f'<a:alpha val="{alpha_pct}"/>'
        except (ValueError, TypeError):
            return ""