#!/usr/bin/env python3
"""Targeted coverage for EnhancedXMLBuilder using module-slicing fixtures."""

from __future__ import annotations

from lxml import etree as ET

from core.io.template_loader import build_stub_loader

from core.utils.xml_builder import (
    A_URI,
    CONTENT_TYPES_URI,
    NSMAP,
    P_URI,
    EnhancedXMLBuilder,
    FluentShapeBuilder,
)


def build_builder() -> EnhancedXMLBuilder:
    """Create a builder backed by deterministic stub templates."""
    return EnhancedXMLBuilder(template_loader=build_stub_loader())


def test_presentation_generation_updates_dimensions_and_slide_ids():
    builder = build_builder()
    presentation = builder.create_presentation_element(123456, 654321, slide_type="screen16x9")

    slide_sz = presentation.find(".//p:sldSz", namespaces={"p": P_URI})
    assert slide_sz is not None
    assert slide_sz.get("cx") == "123456"
    assert slide_sz.get("cy") == "654321"
    assert slide_sz.get("type") == "screen16x9"

    notes_sz = presentation.find(".//p:notesSz", namespaces={"p": P_URI})
    assert notes_sz is not None
    assert notes_sz.get("cx") == "654321"

    builder.add_slide_to_presentation(presentation, slide_id=256, rel_id="rId5")
    slide_ids = presentation.findall(".//p:sldId", namespaces={"p": P_URI, "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"})
    assert len(slide_ids) == 1
    slide_id = slide_ids[0]
    assert slide_id.get("id") == "256"
    assert slide_id.get(f"{{{NSMAP['r']}}}id") == "rId5"


def test_fluent_shape_builder_applies_position_size_and_geometry():
    builder = build_builder()
    fluent = FluentShapeBuilder(builder, shape_id=7, name="DemoShape")
    geometry = ET.Element(f"{{{A_URI}}}custGeom")
    ET.SubElement(geometry, f"{{{A_URI}}}pathLst")

    shape = (
        fluent.position(111, 222)
        .size(333, 444)
        .geometry(geometry)
        .build()
    )

    xfrm = shape.find(".//a:xfrm", namespaces={"a": A_URI})
    assert xfrm is not None
    off = xfrm.find(".//a:off", namespaces={"a": A_URI})
    ext = xfrm.find(".//a:ext", namespaces={"a": A_URI})
    assert off.get("x") == "111"
    assert off.get("y") == "222"
    assert ext.get("cx") == "333"
    assert ext.get("cy") == "444"

    sp_pr = shape.find(".//p:spPr", namespaces={"p": P_URI})
    assert sp_pr is not None
    appended_geom = sp_pr.find(".//a:custGeom", namespaces={"a": A_URI})
    assert appended_geom is not None

    xml_text = builder.element_to_string(shape)
    assert "custGeom" in xml_text


def test_content_types_override_injection():
    builder = build_builder()
    types = builder.create_content_types_element(
        additional_overrides=[
            {"PartName": "/ppt/custom/item1.xml", "ContentType": "application/vnd.custom+xml"},
        ]
    )

    override = None
    for child in types:
        if child.tag == f"{{{CONTENT_TYPES_URI}}}Override" and child.get("PartName") == "/ppt/custom/item1.xml":
            override = child
            break

    assert override is not None
    assert override.get("ContentType") == "application/vnd.custom+xml"
