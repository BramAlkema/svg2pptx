#!/usr/bin/env python3
"""
Legacy Path Adapter

Wraps proven path conversion components including the battle-tested a2c conversion
and DrawingML generation logic.
"""

import logging
from typing import List, Optional, Tuple
import numpy as np

from core.ir import Path, Point, LineSegment, BezierSegment, SegmentType
from core.policy import PathDecision


class A2CAdapter:
    """
    Adapter for the proven arc-to-cubic conversion.

    Wraps src/paths/a2c.py functionality to convert SVG arcs to Bezier curves.
    This is battle-tested math that should be preserved.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def convert_arc_to_cubic(self, start: Point, end: Point, rx: float, ry: float,
                           x_axis_rotation: float, large_arc_flag: bool,
                           sweep_flag: bool) -> List[BezierSegment]:
        """
        Convert SVG arc to cubic Bezier curves.

        This wraps the proven a2c logic from src/paths/a2c.py.
        In production, would import and delegate to existing implementation.

        Args:
            start: Arc start point
            end: Arc end point
            rx: X radius
            ry: Y radius
            x_axis_rotation: Rotation angle in degrees
            large_arc_flag: Large arc flag
            sweep_flag: Sweep direction flag

        Returns:
            List of BezierSegment objects
        """
        try:
            # Placeholder for actual a2c logic
            # In production: from core.paths.a2c import arc_to_cubic
            # return arc_to_cubic(start, end, rx, ry, x_axis_rotation, large_arc_flag, sweep_flag)

            # Simplified approximation for now
            if rx <= 0 or ry <= 0:
                # Degenerate arc -> line
                return [BezierSegment(
                    start=start,
                    control1=Point(start.x + (end.x - start.x) / 3, start.y + (end.y - start.y) / 3),
                    control2=Point(start.x + 2 * (end.x - start.x) / 3, start.y + 2 * (end.y - start.y) / 3),
                    end=end
                )]

            # For now, create a simple cubic approximation
            # Real implementation would use the proven mathematical conversion
            mid_x = (start.x + end.x) / 2
            mid_y = (start.y + end.y) / 2

            # Simple control point estimation
            offset = max(rx, ry) * 0.552  # Magic number for circle approximation

            control1 = Point(
                start.x + (mid_x - start.x) * 0.5,
                start.y + offset if sweep_flag else start.y - offset
            )

            control2 = Point(
                end.x - (end.x - mid_x) * 0.5,
                end.y + offset if sweep_flag else end.y - offset
            )

            return [BezierSegment(
                start=start,
                control1=control1,
                control2=control2,
                end=end
            )]

        except Exception as e:
            self.logger.warning(f"Arc conversion failed: {e}, using line fallback")
            # Fallback to line segment
            return [BezierSegment(
                start=start,
                control1=Point(start.x + (end.x - start.x) / 3, start.y),
                control2=Point(start.x + 2 * (end.x - start.x) / 3, end.y),
                end=end
            )]


class DrawingMLAdapter:
    """
    Adapter for proven DrawingML XML generation.

    Wraps src/paths/drawingml_generator.py functionality.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate_path_xml(self, path: Path) -> str:
        """
        Generate DrawingML path XML from IR Path.

        Wraps the proven DrawingML generation logic.

        Args:
            path: Path IR element

        Returns:
            DrawingML XML string
        """
        try:
            # Calculate path bounds for shape dimensions
            bbox = path.bbox

            # Generate the XML structure
            xml_parts = []
            xml_parts.append('<p:sp>')

            # Non-visual shape properties
            xml_parts.append('<p:nvSpPr>')
            xml_parts.append('<p:cNvPr id="1" name="Path"/>')
            xml_parts.append('<p:cNvSpPr/>')
            xml_parts.append('<p:nvPr/>')
            xml_parts.append('</p:nvSpPr>')

            # Visual shape properties
            xml_parts.append('<p:spPr>')

            # Transform
            xml_parts.append('<a:xfrm>')
            xml_parts.append(f'<a:off x="{int(bbox.x)}" y="{int(bbox.y)}"/>')
            xml_parts.append(f'<a:ext cx="{int(bbox.width)}" cy="{int(bbox.height)}"/>')
            xml_parts.append('</a:xfrm>')

            # Custom geometry
            xml_parts.append('<a:custGeom>')
            xml_parts.append('<a:avLst/>')
            xml_parts.append('<a:gdLst/>')
            xml_parts.append('<a:ahLst/>')
            xml_parts.append('<a:cxnLst/>')

            # Path definition
            xml_parts.append('<a:pathLst>')
            xml_parts.append(f'<a:path w="{int(bbox.width)}" h="{int(bbox.height)}">')

            # Generate path commands
            path_commands = self._generate_path_commands(path.segments, bbox)
            xml_parts.append(path_commands)

            xml_parts.append('</a:path>')
            xml_parts.append('</a:pathLst>')
            xml_parts.append('</a:custGeom>')

            # Fill and stroke
            if path.fill:
                xml_parts.append(self._generate_fill_xml(path.fill))
            else:
                xml_parts.append('<a:noFill/>')

            if path.stroke:
                xml_parts.append(self._generate_stroke_xml(path.stroke))

            xml_parts.append('</p:spPr>')
            xml_parts.append('</p:sp>')

            return ''.join(xml_parts)

        except Exception as e:
            self.logger.error(f"DrawingML generation failed: {e}")
            return f'<!-- DrawingML generation failed: {e} -->'

    def _generate_path_commands(self, segments: List[SegmentType], bbox: "Rect") -> str:
        """Generate DrawingML path commands from segments."""
        if not segments:
            return '<a:moveTo><a:pt x="0" y="0"/></a:moveTo>'

        commands = []

        # Start with first segment
        first_segment = segments[0]
        start_point = getattr(first_segment, 'start', Point(0, 0))

        # Convert to local coordinates relative to bbox
        local_x = int((start_point.x - bbox.x) * 1000)  # Scale for precision
        local_y = int((start_point.y - bbox.y) * 1000)

        commands.append(f'<a:moveTo><a:pt x="{local_x}" y="{local_y}"/></a:moveTo>')

        # Add subsequent segments
        for segment in segments:
            if isinstance(segment, LineSegment):
                end_x = int((segment.end.x - bbox.x) * 1000)
                end_y = int((segment.end.y - bbox.y) * 1000)
                commands.append(f'<a:lnTo><a:pt x="{end_x}" y="{end_y}"/></a:lnTo>')

            elif isinstance(segment, BezierSegment):
                c1_x = int((segment.control1.x - bbox.x) * 1000)
                c1_y = int((segment.control1.y - bbox.y) * 1000)
                c2_x = int((segment.control2.x - bbox.x) * 1000)
                c2_y = int((segment.control2.y - bbox.y) * 1000)
                end_x = int((segment.end.x - bbox.x) * 1000)
                end_y = int((segment.end.y - bbox.y) * 1000)

                commands.append(
                    f'<a:cubicBezTo>'
                    f'<a:pt x="{c1_x}" y="{c1_y}"/>'
                    f'<a:pt x="{c2_x}" y="{c2_y}"/>'
                    f'<a:pt x="{end_x}" y="{end_y}"/>'
                    f'</a:cubicBezTo>'
                )

        # Close path if it forms a closed shape
        if hasattr(segments[0], 'start') and hasattr(segments[-1], 'end'):
            first_point = segments[0].start
            last_point = segments[-1].end
            if (abs(first_point.x - last_point.x) < 0.1 and
                abs(first_point.y - last_point.y) < 0.1):
                commands.append('<a:close/>')

        return ''.join(commands)

    def _generate_fill_xml(self, fill) -> str:
        """Generate fill XML from IR paint."""
        from core.ir import SolidPaint, LinearGradientPaint, RadialGradientPaint

        if isinstance(fill, SolidPaint):
            opacity_attr = f' alpha="{int(fill.opacity * 100000)}"' if fill.opacity < 1.0 else ''
            return (
                f'<a:solidFill>'
                f'<a:srgbClr val="{fill.rgb}"{opacity_attr}/>'
                f'</a:solidFill>'
            )

        elif isinstance(fill, LinearGradientPaint):
            # Simplified gradient handling
            if len(fill.stops) >= 2:
                first_stop = fill.stops[0]
                last_stop = fill.stops[-1]
                return (
                    f'<a:gradFill>'
                    f'<a:gsLst>'
                    f'<a:gs pos="0"><a:srgbClr val="{first_stop.rgb}"/></a:gs>'
                    f'<a:gs pos="100000"><a:srgbClr val="{last_stop.rgb}"/></a:gs>'
                    f'</a:gsLst>'
                    f'<a:lin ang="0" scaled="0"/>'
                    f'</a:gradFill>'
                )

        # Fallback
        return '<a:solidFill><a:srgbClr val="808080"/></a:solidFill>'

    def _generate_stroke_xml(self, stroke) -> str:
        """Generate stroke XML from IR stroke."""
        width_emu = int(stroke.width * 9525)  # pt to EMU

        xml_parts = [f'<a:ln w="{width_emu}">']

        # Stroke fill
        if stroke.paint:
            xml_parts.append(self._generate_fill_xml(stroke.paint))
        else:
            xml_parts.append('<a:solidFill><a:srgbClr val="000000"/></a:solidFill>')

        # Line properties
        if stroke.join.value == 'round':
            xml_parts.append('<a:round/>')
        elif stroke.join.value == 'bevel':
            xml_parts.append('<a:bevel/>')
        else:
            xml_parts.append(f'<a:miter lim="{int(stroke.miter_limit * 1000)}"/>')

        if stroke.cap.value == 'round':
            xml_parts.append('<a:headEnd type="oval"/>')
        elif stroke.cap.value == 'square':
            xml_parts.append('<a:headEnd type="square"/>')

        # Dash pattern
        if stroke.is_dashed and stroke.dash_array:
            xml_parts.append('<a:prstDash val="dash"/>')  # Simplified

        xml_parts.append('</a:ln>')
        return ''.join(xml_parts)


class LegacyPathAdapter:
    """
    Main adapter for legacy path conversion functionality.

    Combines proven arc conversion and DrawingML generation.
    """

    def __init__(self):
        self.a2c_adapter = A2CAdapter()
        self.drawingml_adapter = DrawingMLAdapter()
        self.logger = logging.getLogger(__name__)

    def convert_svg_path_to_ir(self, path_element, context=None) -> Path:
        """
        Convert SVG path element to IR Path.

        Handles arc conversion and coordinate transformation.

        Args:
            path_element: SVG path element or path data string
            context: Conversion context (optional)

        Returns:
            Path IR element
        """
        # This would integrate with existing path parsing logic
        # For now, create a simple placeholder

        # Parse path data (simplified)
        if hasattr(path_element, 'get'):
            path_data = path_element.get('d', '')
        else:
            path_data = str(path_element)

        segments = self._parse_path_data_simple(path_data)

        # Extract styling
        fill = self._extract_fill(path_element) if hasattr(path_element, 'get') else None
        stroke = self._extract_stroke(path_element) if hasattr(path_element, 'get') else None

        return Path(
            segments=segments,
            fill=fill,
            stroke=stroke,
            opacity=1.0
        )

    def generate_drawingml_from_ir(self, path: Path, decision: PathDecision) -> str:
        """
        Generate DrawingML XML from IR Path.

        Args:
            path: Path IR element
            decision: Policy decision for this path

        Returns:
            DrawingML XML string
        """
        if not decision.use_native:
            # Fallback to EMF
            return self._generate_emf_fallback(path)

        return self.drawingml_adapter.generate_path_xml(path)

    def _parse_path_data_simple(self, path_data: str) -> List[SegmentType]:
        """
        Simple path data parser (placeholder).

        In production, would use existing robust path parser.
        """
        segments = []

        if not path_data:
            return segments

        # Very simplified parsing - just create a basic shape
        # Real implementation would parse SVG path commands properly
        try:
            # Create a simple rectangle for demonstration
            segments = [
                LineSegment(Point(0, 0), Point(100, 0)),
                LineSegment(Point(100, 0), Point(100, 100)),
                LineSegment(Point(100, 100), Point(0, 100)),
                LineSegment(Point(0, 100), Point(0, 0))
            ]
        except Exception as e:
            self.logger.warning(f"Path parsing failed: {e}")

        return segments

    def _extract_fill(self, element) -> Optional[object]:
        """Extract fill from SVG element (simplified)."""
        from core.ir import SolidPaint

        fill_attr = element.get('fill', 'black')
        if fill_attr == 'none':
            return None

        # Simple color parsing
        if fill_attr.startswith('#'):
            rgb = fill_attr[1:].upper()
            if len(rgb) == 6:
                return SolidPaint(rgb)

        # Default black fill
        return SolidPaint("000000")

    def _extract_stroke(self, element) -> Optional[object]:
        """Extract stroke from SVG element (simplified)."""
        from core.ir import Stroke, SolidPaint, StrokeJoin, StrokeCap

        stroke_attr = element.get('stroke')
        if not stroke_attr or stroke_attr == 'none':
            return None

        width_attr = element.get('stroke-width', '1')
        try:
            width = float(width_attr)
        except ValueError:
            width = 1.0

        stroke_paint = SolidPaint("000000")  # Default black
        if stroke_attr.startswith('#'):
            rgb = stroke_attr[1:].upper()
            if len(rgb) == 6:
                stroke_paint = SolidPaint(rgb)

        return Stroke(
            paint=stroke_paint,
            width=width,
            join=StrokeJoin.MITER,
            cap=StrokeCap.BUTT
        )

    def _generate_emf_fallback(self, path: Path) -> str:
        """Generate EMF fallback for complex paths."""
        return f'<!-- EMF fallback for path with {len(path.segments)} segments -->'