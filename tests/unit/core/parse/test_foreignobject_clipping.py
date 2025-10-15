#!/usr/bin/env python3

import pytest
from lxml import etree as ET

from core.parse.parser import SVGParser

SVG_NS = "http://www.w3.org/2000/svg"
XHTML_NS = "http://www.w3.org/1999/xhtml"


def _ns(tag: str, namespace: str = SVG_NS) -> str:
    return f"{{{namespace}}}{tag}"


def test_foreignobject_nested_svg_generates_bbox_clip():
    svg_markup = f"""
    <svg xmlns="{SVG_NS}">
        <foreignObject x="10" y="20" width="120" height="60">
            <svg xmlns="{SVG_NS}" width="120" height="60">
                <rect x="0" y="0" width="50" height="30" fill="red"/>
            </svg>
        </foreignObject>
    </svg>
    """
    root = ET.fromstring(svg_markup)
    foreignobject = root.find(_ns("foreignObject"))
    parser = SVGParser()

    result = parser._convert_foreignobject_to_ir(foreignobject)

    assert result is not None
    assert result.clip is not None
    assert result.clip.clip_id.startswith("bbox:"), result.clip.clip_id


def test_foreignobject_image_generates_bbox_clip():
    svg_markup = f"""
    <svg xmlns="{SVG_NS}">
        <foreignObject x="5" y="15" width="80" height="40">
            <img xmlns="{XHTML_NS}" src="example.png" width="80" height="40"/>
        </foreignObject>
    </svg>
    """
    root = ET.fromstring(svg_markup)
    foreignobject = root.find(_ns("foreignObject"))
    parser = SVGParser()

    result = parser._convert_foreignobject_to_ir(foreignobject)

    assert result is not None
    assert getattr(result, "clip", None) is not None
    assert result.clip.clip_id.startswith("bbox:"), result.clip.clip_id
