#!/usr/bin/env python3
"""
Shared helper functions for shape mapping to DrawingML

Provides fill and stroke XML generation utilities used by
CircleMapper, EllipseMapper, and RectangleMapper.
"""

from typing import Any, Optional

from ..ir.paint import (
    Paint,
    SolidPaint,
    LinearGradientPaint,
    RadialGradientPaint,
    PatternPaint,
)
from ..ir.paint import Stroke, StrokeCap, StrokeJoin


def generate_fill_xml(fill: Optional[Paint]) -> str:
    """Generate DrawingML fill XML from IR paint

    Args:
        fill: Paint object (SolidPaint, gradient, pattern, or None)

    Returns:
        DrawingML XML string for fill (<a:solidFill>, <a:gradFill>, etc.)

    Examples:
        >>> from core.ir.paint import SolidPaint
        >>> fill = SolidPaint(rgb="FF0000")
        >>> xml = generate_fill_xml(fill)
        >>> assert '<a:solidFill>' in xml
        >>> assert 'FF0000' in xml
    """
    if fill is None:
        return '<a:noFill/>'

    if isinstance(fill, SolidPaint):
        return f'<a:solidFill><a:srgbClr val="{fill.rgb}"/></a:solidFill>'

    elif isinstance(fill, LinearGradientPaint):
        stops_xml = ""
        for stop in fill.stops:
            pos = int(stop.offset * 100000)  # DrawingML uses 0-100000
            stops_xml += f'<a:gs pos="{pos}"><a:srgbClr val="{stop.rgb}"/></a:gs>'

        # Calculate angle from start/end coordinates
        # DrawingML angles: 0° = right, 90° = down, counter-clockwise
        import math
        dx = fill.end[0] - fill.start[0]
        dy = fill.end[1] - fill.start[1]
        angle_radians = math.atan2(dy, dx)
        angle_degrees = math.degrees(angle_radians)
        # Convert to DrawingML units (60000 per degree)
        angle_emu = int(angle_degrees * 60000)

        return f'''<a:gradFill flip="none" rotWithShape="1">
    <a:gsLst>{stops_xml}</a:gsLst>
    <a:lin ang="{angle_emu}" scaled="1"/>
</a:gradFill>'''

    elif isinstance(fill, RadialGradientPaint):
        stops_xml = ""
        for stop in fill.stops:
            pos = int(stop.offset * 100000)
            stops_xml += f'<a:gs pos="{pos}"><a:srgbClr val="{stop.rgb}"/></a:gs>'

        return f'''<a:gradFill flip="none" rotWithShape="1">
    <a:gsLst>{stops_xml}</a:gsLst>
    <a:path path="circle">
        <a:fillToRect l="0" t="0" r="0" b="0"/>
    </a:path>
</a:gradFill>'''

    elif isinstance(fill, PatternPaint):
        # Pattern fills use preset patterns
        preset = getattr(fill, 'preset', 'pct5')
        fg = getattr(fill, 'foreground', '000000')
        bg = getattr(fill, 'background', 'FFFFFF')

        return f'''<a:pattFill prst="{preset}">
    <a:fgClr><a:srgbClr val="{fg}"/></a:fgClr>
    <a:bgClr><a:srgbClr val="{bg}"/></a:bgClr>
</a:pattFill>'''

    else:
        # Fallback to no fill for unknown paint types
        return '<a:noFill/>'


def generate_stroke_xml(stroke: Optional[Stroke]) -> str:
    """Generate DrawingML stroke XML from IR stroke

    Args:
        stroke: Stroke object with width, color, cap, join, dash properties

    Returns:
        DrawingML XML string for line (<a:ln>)

    Examples:
        >>> from core.ir.paint import Stroke, SolidPaint, StrokeCap, StrokeJoin
        >>> stroke = Stroke(
        ...     width=2.0,
        ...     paint=SolidPaint(rgb="000000"),
        ...     cap=StrokeCap.ROUND,
        ...     join=StrokeJoin.MITER,
        ... )
        >>> xml = generate_stroke_xml(stroke)
        >>> assert '<a:ln w=' in xml
        >>> assert '<a:cap val="rnd"/>' in xml
    """
    if stroke is None:
        return '<a:ln><a:noFill/></a:ln>'

    # Convert width to EMU (1 pt = 12700 EMU)
    width_emu = int(stroke.width * 12700)

    xml = f'<a:ln w="{width_emu}">'

    # Stroke paint (usually solid, but can be gradient)
    if hasattr(stroke, 'paint') and stroke.paint:
        if isinstance(stroke.paint, SolidPaint):
            xml += f'<a:solidFill><a:srgbClr val="{stroke.paint.rgb}"/></a:solidFill>'
        else:
            # Use fill helper for gradients/patterns
            xml += generate_fill_xml(stroke.paint)
    else:
        # Default to black
        xml += '<a:solidFill><a:srgbClr val="000000"/></a:solidFill>'

    # Stroke cap - map SVG values to DrawingML
    if hasattr(stroke, 'cap') and stroke.cap:
        cap_map = {
            StrokeCap.BUTT: 'flat',
            StrokeCap.ROUND: 'rnd',
            StrokeCap.SQUARE: 'sq',
            'butt': 'flat',
            'round': 'rnd',
            'square': 'sq',
        }
        cap_value = cap_map.get(stroke.cap, 'flat')
        xml += f'<a:cap val="{cap_value}"/>'

    # Stroke join - map SVG values to DrawingML elements
    if hasattr(stroke, 'join') and stroke.join:
        join_value = stroke.join

        # Handle enum or string
        if hasattr(join_value, 'value'):
            join_str = join_value.value
        else:
            join_str = str(join_value).lower()

        if join_str == 'miter':
            xml += '<a:miter/>'
        elif join_str == 'round':
            xml += '<a:round/>'
        elif join_str == 'bevel':
            xml += '<a:bevel/>'
        else:
            # Default to miter
            xml += '<a:miter/>'

    # Dash pattern (simplified - just detect dashed vs solid)
    if hasattr(stroke, 'dash_array') and stroke.dash_array:
        xml += '<a:prstDash val="dash"/>'

    xml += '</a:ln>'
    return xml


def generate_effects_xml(effects: list) -> str:
    """Generate DrawingML effect list XML from IR effects

    Args:
        effects: List of Effect objects (BlurEffect, ShadowEffect, etc.)

    Returns:
        DrawingML XML string for effects (<a:effectLst>)
        Empty string if no effects
    """
    if not effects:
        return ''

    from ..ir.effects import (
        BlurEffect, ShadowEffect, GlowEffect,
        SoftEdgeEffect, ReflectionEffect
    )

    effect_elements = []

    for effect in effects:
        if isinstance(effect, BlurEffect):
            rad = effect.to_emu()
            effect_elements.append(f'<a:blur rad="{rad}"/>')

        elif isinstance(effect, ShadowEffect):
            blur_rad, dist = effect.to_emu()
            direction = effect.to_direction_emu()
            alpha = effect.to_alpha_val()

            effect_elements.append(f'''<a:outerShdw blurRad="{blur_rad}" dist="{dist}" dir="{direction}" rotWithShape="0">
    <a:srgbClr val="{effect.color}">
        <a:alpha val="{alpha}"/>
    </a:srgbClr>
</a:outerShdw>''')

        elif isinstance(effect, GlowEffect):
            rad = effect.to_emu()
            effect_elements.append(f'''<a:glow rad="{rad}">
    <a:srgbClr val="{effect.color}"/>
</a:glow>''')

        elif isinstance(effect, SoftEdgeEffect):
            rad = effect.to_emu()
            effect_elements.append(f'<a:softEdge rad="{rad}"/>')

        elif isinstance(effect, ReflectionEffect):
            blur_rad, dist = effect.to_emu()
            start_a, end_a = effect.to_alpha_vals()
            effect_elements.append(f'<a:reflection blurRad="{blur_rad}" stA="{start_a}" endA="{end_a}" dist="{dist}"/>')

    if not effect_elements:
        return ''

    effects_xml = '\n    '.join(effect_elements)
    return f'''<a:effectLst>
    {effects_xml}
</a:effectLst>'''


def generate_shape_properties_xml(
    x_emu: int,
    y_emu: int,
    width_emu: int,
    height_emu: int,
    preset_name: str,
    fill: Optional[Paint] = None,
    stroke: Optional[Stroke] = None,
    effects: list = None,
) -> str:
    """Generate complete <p:spPr> element for native preset shape

    Args:
        x_emu: X position in EMU
        y_emu: Y position in EMU
        width_emu: Width in EMU
        height_emu: Height in EMU
        preset_name: PowerPoint preset ('ellipse', 'rect', 'roundRect')
        fill: Optional fill paint
        stroke: Optional stroke
        effects: Optional list of effects (blur, shadow, glow, etc.)

    Returns:
        Complete <p:spPr> XML with transform, geometry, effects, fill, stroke
    """
    fill_xml = generate_fill_xml(fill)
    stroke_xml = generate_stroke_xml(stroke)
    effects_xml = generate_effects_xml(effects or [])

    return f'''<p:spPr>
    <a:xfrm>
        <a:off x="{x_emu}" y="{y_emu}"/>
        <a:ext cx="{width_emu}" cy="{height_emu}"/>
    </a:xfrm>
    <a:prstGeom prst="{preset_name}">
        <a:avLst/>
    </a:prstGeom>
    {effects_xml}
    {fill_xml}
    {stroke_xml}
</p:spPr>'''


def generate_style_xml() -> str:
    """Generate standard <p:style> element for shapes

    Returns:
        Standard PowerPoint style XML with theme references
    """
    return '''<p:style>
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
</p:style>'''


def generate_text_body_xml() -> str:
    """Generate standard <p:txBody> element for shapes

    Returns:
        Standard PowerPoint text body XML (empty paragraph)
    """
    return '''<p:txBody>
    <a:bodyPr rtlCol="0" anchor="ctr"/>
    <a:lstStyle/>
    <a:p>
        <a:pPr algn="ctr"/>
    </a:p>
</p:txBody>'''
