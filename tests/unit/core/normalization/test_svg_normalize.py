from lxml import etree as ET

import pytest

from svg2pptx.normalize_svg import normalize_svg_string


SVG_NS = "http://www.w3.org/2000/svg"


def _parse(output: str) -> ET.Element:
    return ET.fromstring(output)


def test_normalize_svg_inlines_css_and_preserves_viewbox():
    raw_svg = """<svg xmlns="http://www.w3.org/2000/svg"
        xmlns:xlink="http://www.w3.org/1999/xlink"
        viewBox="0 0 200 200">
      <style>
        .foo { fill: #ff0000; stroke: #0000ff; }
        rect.bar { stroke-width: 5; }
      </style>
      <rect class="foo bar" id="rect1"
            x="10" y="10" width="80" height="80"
            style="stroke:#00ff00; opacity:0.5"/>
    </svg>"""

    normalized = normalize_svg_string(raw_svg)
    root = _parse(normalized)

    # Namespace and viewBox preserved
    assert root.tag == f"{{{SVG_NS}}}svg"
    assert root.get("viewBox") == "0 0 200 200"

    # Ensure <style> nodes removed
    assert not root.findall(f".//{{{SVG_NS}}}style")

    rect = root.find(f".//{{{SVG_NS}}}rect")
    assert rect is not None

    # Inline CSS promoted to attributes with deterministic ordering
    attrib_keys = list(rect.attrib.keys())
    assert attrib_keys == sorted(attrib_keys)

    assert rect.get("fill") == "#ff0000"
    # Inline style (stroke) should win over stylesheet stroke
    assert rect.get("stroke") == "#00ff00"
    # Stroke width from stylesheet promoted
    assert rect.get("stroke-width") == "5"
    # Opacity promoted to dedicated attribute and style removed
    assert rect.get("opacity") == "0.5"
    assert "style" not in rect.attrib


def test_normalize_svg_keeps_existing_dimensions():
    raw_svg = """<svg xmlns="http://www.w3.org/2000/svg"
        width="400" height="160" viewBox="0 0 400 160">
      <text x="20" y="40" style="font-size:24px; fill:#333">Hello</text>
    </svg>"""

    normalized = normalize_svg_string(raw_svg)
    root = _parse(normalized)

    assert root.get("width") == "400"
    assert root.get("height") == "160"

    text = root.find(f".//{{{SVG_NS}}}text")
    assert text is not None
    assert text.get("font-size") == "24px"
    assert text.get("fill") == "#333"
    assert "style" not in text.attrib
