#!/usr/bin/env python3
"""
EllipseMapper: Maps Ellipse IR to native PowerPoint shapes

Converts Ellipse IR to either:
1. Native PowerPoint ellipse (<a:prstGeom prst="ellipse">) for simple ellipses
2. Custom geometry path (<a:custGeom>) for complex ellipses

Handles circle detection: ellipses with rx ≈ ry can use square extents.
"""

import logging
from typing import Any, Optional

from ..ir.shapes import Ellipse
from ..ir.geometry import Point, BezierSegment
from ..ir.scene import Path
from ..policy.shape_policy import decide_shape_strategy
from .base import MapperResult, OutputFormat
from .shape_helpers import (
    generate_shape_properties_xml,
    generate_style_xml,
    generate_text_body_xml,
)


class EllipseMapper:
    """Maps Ellipse IR to native PowerPoint ellipse or custom geometry"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def map(self, ellipse: Ellipse, context: Optional[Any] = None) -> MapperResult:
        """
        Map Ellipse to DrawingML XML.

        Args:
            ellipse: Ellipse IR object
            context: Optional conversion context

        Returns:
            Dictionary with 'xml_content', 'decision', 'format' keys
        """
        # Get policy decision
        decision = decide_shape_strategy(ellipse, context)

        if decision.use_preset:
            return self._map_to_preset(ellipse, decision)
        else:
            return self._map_to_custom_geometry(ellipse, decision)

    def _map_to_preset(self, ellipse: Ellipse, decision: Any) -> MapperResult:
        """Generate native PowerPoint ellipse shape

        Args:
            ellipse: Ellipse IR object
            decision: ShapeDecision from policy engine

        Returns:
            Dictionary with XML and metadata
        """
        # Convert ellipse center and radii to EMU
        cx_emu = int(ellipse.center.x * 12700)
        cy_emu = int(ellipse.center.y * 12700)
        rx_emu = int(ellipse.radius_x * 12700)
        ry_emu = int(ellipse.radius_y * 12700)

        # Calculate top-left position
        x_emu = cx_emu - rx_emu
        y_emu = cy_emu - ry_emu
        width_emu = rx_emu * 2
        height_emu = ry_emu * 2

        # Get shape ID
        shape_id = getattr(ellipse, 'shape_id', 1)

        # Generate shape properties with effects
        shape_props = generate_shape_properties_xml(
            x_emu=x_emu,
            y_emu=y_emu,
            width_emu=width_emu,
            height_emu=height_emu,
            preset_name='ellipse',
            fill=ellipse.fill,
            stroke=ellipse.stroke,
            effects=ellipse.effects,
        )

        xml_content = f'''<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="Ellipse"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    {shape_props}
    {generate_style_xml()}
    {generate_text_body_xml()}
</p:sp>'''

        return MapperResult(
            element=ellipse,
            output_format=OutputFormat.NATIVE_DML,
            xml_content=xml_content,
            policy_decision=decision,
            metadata={'preset_name': 'ellipse'},
            estimated_quality=1.0,
            estimated_performance=1.0,
        )

    def _map_to_custom_geometry(self, ellipse: Ellipse, decision: Any) -> MapperResult:
        """Fallback to custom geometry path for complex ellipses

        Args:
            ellipse: Ellipse IR object
            decision: ShapeDecision from policy engine

        Returns:
            Dictionary with XML and metadata
        """
        path = self._ellipse_to_path(ellipse)

        self.logger.info(f"Ellipse falls back to custom geometry: {decision.reasons}")

        return MapperResult(
            element=ellipse,
            output_format=OutputFormat.NATIVE_DML,
            xml_content='<!-- Custom geometry path for complex ellipse -->',
            policy_decision=decision,
            metadata={'fallback': 'custom_geometry', 'path': path},
            estimated_quality=0.95,
            estimated_performance=0.9,
        )

    def _ellipse_to_path(self, ellipse: Ellipse) -> Path:
        """Convert Ellipse to Path with scaled Bezier curves

        Uses same k constant as circles, but scales control points by rx and ry.

        Args:
            ellipse: Ellipse IR object

        Returns:
            Path IR object with 4 Bezier segments
        """
        cx = ellipse.center.x
        cy = ellipse.center.y
        rx = ellipse.radius_x
        ry = ellipse.radius_y

        # Bezier constant scaled by radii
        k = 0.552284749831
        kx = k * rx
        ky = k * ry

        segments = [
            # Top right quadrant
            BezierSegment(
                start=Point(cx + rx, cy),
                control1=Point(cx + rx, cy - ky),
                control2=Point(cx + kx, cy - ry),
                end=Point(cx, cy - ry),
            ),
            # Top left quadrant
            BezierSegment(
                start=Point(cx, cy - ry),
                control1=Point(cx - kx, cy - ry),
                control2=Point(cx - rx, cy - ky),
                end=Point(cx - rx, cy),
            ),
            # Bottom left quadrant
            BezierSegment(
                start=Point(cx - rx, cy),
                control1=Point(cx - rx, cy + ky),
                control2=Point(cx - kx, cy + ry),
                end=Point(cx, cy + ry),
            ),
            # Bottom right quadrant
            BezierSegment(
                start=Point(cx, cy + ry),
                control1=Point(cx + kx, cy + ry),
                control2=Point(cx + rx, cy + ky),
                end=Point(cx + rx, cy),
            ),
        ]

        return Path(
            segments=segments,
            fill=ellipse.fill,
            stroke=ellipse.stroke,
            opacity=ellipse.opacity,
        )
