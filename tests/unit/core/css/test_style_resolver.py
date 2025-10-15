from lxml import etree as ET

from core.css import StyleResolver, StyleContext, parse_color
from core.units.core import UnitConverter


def test_parse_color_supports_named_and_hex():
    assert parse_color("#abc") == "AABBCC"
    assert parse_color("red") == "FF0000"
    assert parse_color("rgb(0, 128, 255)") == "0080FF"
    assert parse_color(None) == "000000"


def test_compute_text_style_attributes_and_inline():
    resolver = StyleResolver()
    element = ET.fromstring(
        "<text font-family='Helvetica' font-size='16px' "
        "style='font-weight:700; fill: #00ff00'/>"
    )

    style = resolver.compute_text_style(element)

    assert style["font_family"] == "Helvetica"
    assert style["font_size_pt"] == 12.0  # 16px -> 12pt
    assert style["font_weight"] == "bold"
    assert style["fill"] == "00FF00"


def test_compute_text_style_inherits_from_parent():
    resolver = StyleResolver()
    parent = resolver.compute_text_style(ET.fromstring("<text font-style='italic'/>") )
    child = ET.fromstring("<tspan style='font-weight:600'/>")

    merged = resolver.compute_text_style(child, parent_style=parent)

    assert merged["font_style"] == "italic"
    assert merged["font_weight"] == "semibold"


def test_compute_paint_style_with_units():
    converter = UnitConverter()
    conversion_ctx = converter.create_context(
        width=200.0,
        height=100.0,
        font_size=12.0,
        dpi=96.0,
        parent_width=200.0,
        parent_height=100.0,
    )
    context = StyleContext(
        conversion=conversion_ctx,
        viewport_width=200.0,
        viewport_height=100.0,
    )

    resolver = StyleResolver(converter)
    element = ET.fromstring(
        "<rect stroke='blue' stroke-width='10%' fill='none' opacity='0.5' style='stroke-opacity:0.25'/>"
    )

    style = resolver.compute_paint_style(element, context=context)

    assert style["fill"] is None
    assert style["stroke"] == "0000FF"
    assert abs(style["stroke_width_px"] - 20.0) < 1e-6
    assert style["stroke_opacity"] == 0.25
    assert style["opacity"] == 0.5
