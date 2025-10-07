#!/usr/bin/env python3
"""
RectangleMapper: Maps Rectangle IR to native PowerPoint shapes

Converts Rectangle IR to either:
1. Native PowerPoint rect (<a:prstGeom prst="rect">) for sharp corners
2. Native PowerPoint roundRect (<a:prstGeom prst="roundRect">) for rounded corners
3. Custom geometry path for complex rectangles

Supports corner_radius for rounded rectangles.
"""

import logging
from typing import Any, Optional

from ..ir.shapes import Rectangle
from ..ir.geometry import Point, LineSegment
from ..ir.scene import Path
from ..policy.shape_policy import decide_shape_strategy
from .base import MapperResult, OutputFormat
from .shape_helpers import (
    generate_shape_properties_xml,
    generate_style_xml,
    generate_text_body_xml,
)


class RectangleMapper:
    """Maps Rectangle IR to native PowerPoint rect/roundRect or custom geometry"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def map(self, rect: Rectangle, context: Optional[Any] = None) -> MapperResult:
        """
        Map Rectangle to DrawingML XML.

        Args:
            rect: Rectangle IR object
            context: Optional conversion context

        Returns:
            Dictionary with 'xml_content', 'decision', 'format' keys
        """
        # Get policy decision (will choose rect vs roundRect)
        decision = decide_shape_strategy(rect, context)

        if decision.use_preset:
            return self._map_to_preset(rect, decision)
        else:
            return self._map_to_custom_geometry(rect, decision)

    def _map_to_preset(self, rect: Rectangle, decision: Any) -> MapperResult:
        """Generate native PowerPoint rect or roundRect shape

        Args:
            rect: Rectangle IR object
            decision: ShapeDecision from policy engine (contains preset_name)

        Returns:
            Dictionary with XML and metadata
        """
        # Convert bounds to EMU
        x_emu = int(rect.bounds.x * 12700)
        y_emu = int(rect.bounds.y * 12700)
        width_emu = int(rect.bounds.width * 12700)
        height_emu = int(rect.bounds.height * 12700)

        # Get shape ID
        shape_id = getattr(rect, 'shape_id', 1)

        # Use preset name from decision (rect or roundRect)
        preset_name = decision.preset_name or 'rect'

        # Generate shape properties with effects
        shape_props = generate_shape_properties_xml(
            x_emu=x_emu,
            y_emu=y_emu,
            width_emu=width_emu,
            height_emu=height_emu,
            preset_name=preset_name,
            fill=rect.fill,
            stroke=rect.stroke,
            effects=rect.effects,
        )

        xml_content = f'''<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="Rectangle"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    {shape_props}
    {generate_style_xml()}
    {generate_text_body_xml()}
</p:sp>'''

        return MapperResult(
            element=rect,
            output_format=OutputFormat.NATIVE_DML,
            xml_content=xml_content,
            policy_decision=decision,
            metadata={'preset_name': decision.preset_name or 'rect'},
            estimated_quality=1.0,
            estimated_performance=1.0,
        )

    def _map_to_custom_geometry(self, rect: Rectangle, decision: Any) -> MapperResult:
        """Fallback to custom geometry path for complex rectangles

        Args:
            rect: Rectangle IR object
            decision: ShapeDecision from policy engine

        Returns:
            Dictionary with XML and metadata
        """
        path = self._rectangle_to_path(rect)

        self.logger.info(f"Rectangle falls back to custom geometry: {decision.reasons}")

        return MapperResult(
            element=rect,
            output_format=OutputFormat.NATIVE_DML,
            xml_content='<!-- Custom geometry path for complex rectangle -->',
            policy_decision=decision,
            metadata={'fallback': 'custom_geometry', 'path': path},
            estimated_quality=0.95,
            estimated_performance=0.9,
        )

    def _rectangle_to_path(self, rect: Rectangle) -> Path:
        """Convert Rectangle to Path with line segments

        Args:
            rect: Rectangle IR object

        Returns:
            Path IR object with 4 line segments
        """
        x = rect.bounds.x
        y = rect.bounds.y
        w = rect.bounds.width
        h = rect.bounds.height

        segments = [
            # Top edge
            LineSegment(
                start=Point(x, y),
                end=Point(x + w, y),
            ),
            # Right edge
            LineSegment(
                start=Point(x + w, y),
                end=Point(x + w, y + h),
            ),
            # Bottom edge
            LineSegment(
                start=Point(x + w, y + h),
                end=Point(x, y + h),
            ),
            # Left edge
            LineSegment(
                start=Point(x, y + h),
                end=Point(x, y),
            ),
        ]

        return Path(
            segments=segments,
            fill=rect.fill,
            stroke=rect.stroke,
            opacity=rect.opacity,
        )
