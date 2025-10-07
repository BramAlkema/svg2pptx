#!/usr/bin/env python3
"""
CircleMapper: Maps Circle IR to native PowerPoint shapes

Converts Circle IR to either:
1. Native PowerPoint ellipse (<a:prstGeom prst="ellipse">) for simple circles
2. Custom geometry path (<a:custGeom>) for complex circles (filters, transforms)

Decision is made by the policy engine (decide_shape_strategy).
"""

import logging
from typing import Any, Optional

from ..ir.shapes import Circle
from ..ir.geometry import Point, BezierSegment
from ..ir.scene import Path
from ..policy.shape_policy import decide_shape_strategy
from ..units import unit
from .base import MapperResult, OutputFormat
from .shape_helpers import (
    generate_fill_xml,
    generate_stroke_xml,
    generate_shape_properties_xml,
    generate_style_xml,
    generate_text_body_xml,
)


class CircleMapper:
    """Maps Circle IR to native PowerPoint ellipse or custom geometry

    Uses policy engine to decide between native preset and custom geometry.
    Native shapes provide better PowerPoint editability and smaller file sizes.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def map(self, circle: Circle, context: Optional[Any] = None) -> MapperResult:
        """
        Map Circle to DrawingML XML.

        Args:
            circle: Circle IR object
            context: Optional conversion context with filters/clipping info

        Returns:
            MapperResult with XML and metadata

        Example:
            >>> mapper = CircleMapper()
            >>> circle = Circle(center=Point(100, 100), radius=50)
            >>> result = mapper.map(circle)
            >>> assert '<a:prstGeom prst="ellipse">' in result.xml_content
        """
        # Get policy decision
        decision = decide_shape_strategy(circle, context)

        if decision.use_preset:
            return self._map_to_preset(circle, decision)
        else:
            return self._map_to_custom_geometry(circle, decision)

    def _map_to_preset(self, circle: Circle, decision: Any) -> MapperResult:
        """Generate native PowerPoint ellipse shape

        Args:
            circle: Circle IR object
            decision: ShapeDecision from policy engine

        Returns:
            MapperResult with XML and metadata
        """
        # Convert circle center and radius to EMU
        # PowerPoint uses top-left corner positioning, not center
        cx_emu = int(circle.center.x * 12700)
        cy_emu = int(circle.center.y * 12700)
        r_emu = int(circle.radius * 12700)

        # Calculate top-left position
        x_emu = cx_emu - r_emu
        y_emu = cy_emu - r_emu
        diameter_emu = r_emu * 2

        # Get shape ID from circle metadata or use default
        shape_id = getattr(circle, 'shape_id', 1)

        # Generate complete shape XML with effects
        shape_props = generate_shape_properties_xml(
            x_emu=x_emu,
            y_emu=y_emu,
            width_emu=diameter_emu,
            height_emu=diameter_emu,
            preset_name='ellipse',
            fill=circle.fill,
            stroke=circle.stroke,
            effects=circle.effects,
        )

        xml_content = f'''<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="Circle"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    {shape_props}
    {generate_style_xml()}
    {generate_text_body_xml()}
</p:sp>'''

        return MapperResult(
            element=circle,
            output_format=OutputFormat.NATIVE_DML,
            xml_content=xml_content,
            policy_decision=decision,
            metadata={'preset_name': 'ellipse'},
            estimated_quality=1.0,  # Perfect fidelity
            estimated_performance=1.0,  # Native shapes are fast
        )

    def _map_to_custom_geometry(self, circle: Circle, decision: Any) -> MapperResult:
        """Fallback to custom geometry path for complex circles

        Converts Circle to Path with Bezier curves and delegates to PathMapper.

        Args:
            circle: Circle IR object
            decision: ShapeDecision from policy engine

        Returns:
            MapperResult with XML and metadata
        """
        # Convert Circle to Path with Bezier approximation
        path = self._circle_to_path(circle)

        # Note: In final integration, this would call PathMapper
        # For now, return placeholder indicating custom geometry
        self.logger.info(f"Circle falls back to custom geometry: {decision.reasons}")

        return MapperResult(
            element=circle,
            output_format=OutputFormat.NATIVE_DML,  # Will be custom geometry
            xml_content='<!-- Custom geometry path for complex circle -->',
            policy_decision=decision,
            metadata={'fallback': 'custom_geometry', 'path': path},
            estimated_quality=0.95,  # Bezier approximation
            estimated_performance=0.9,  # Custom geometry is slower
        )

    def _circle_to_path(self, circle: Circle) -> Path:
        """Convert Circle to Path with Bezier curve approximation

        Uses the optimal Bezier constant k = 0.552284749831 for circle approximation.
        Creates 4 Bezier curves (one per quadrant).

        Args:
            circle: Circle IR object

        Returns:
            Path IR object with 4 Bezier segments
        """
        cx, cy, r = circle.center.x, circle.center.y, circle.radius

        # Magic constant for circle approximation with cubic Bezier curves
        k = 0.552284749831  # 4 * (√2 - 1) / 3

        segments = [
            # Top right quadrant (0° to 90°)
            BezierSegment(
                start=Point(cx + r, cy),
                control1=Point(cx + r, cy - k * r),
                control2=Point(cx + k * r, cy - r),
                end=Point(cx, cy - r),
            ),
            # Top left quadrant (90° to 180°)
            BezierSegment(
                start=Point(cx, cy - r),
                control1=Point(cx - k * r, cy - r),
                control2=Point(cx - r, cy - k * r),
                end=Point(cx - r, cy),
            ),
            # Bottom left quadrant (180° to 270°)
            BezierSegment(
                start=Point(cx - r, cy),
                control1=Point(cx - r, cy + k * r),
                control2=Point(cx - k * r, cy + r),
                end=Point(cx, cy + r),
            ),
            # Bottom right quadrant (270° to 360°)
            BezierSegment(
                start=Point(cx, cy + r),
                control1=Point(cx + k * r, cy + r),
                control2=Point(cx + r, cy + k * r),
                end=Point(cx + r, cy),
            ),
        ]

        return Path(
            segments=segments,
            fill=circle.fill,
            stroke=circle.stroke,
            opacity=circle.opacity,
        )
