#!/usr/bin/env python3
"""Focused tests for PathShapeGenerator using module-slicing fixtures."""

from __future__ import annotations

import pytest
from textwrap import dedent

from lxml import etree as ET

from core.utils.xml_builder import EnhancedXMLBuilder, A_URI, NSMAP, P_URI, R_URI
from testing.fixtures.module_slicing import path_fill_xml, path_clip_xml, path_stroke_xml


class DummyLoader:
    """Minimal template loader tuned for the path generator tests."""

    def __init__(self) -> None:
        content_types_uri = "http://schemas.openxmlformats.org/package/2006/content-types"
        self._templates = {
            "presentation.xml": dedent(
                f"""
                <p:presentation xmlns:p="{P_URI}" xmlns:a="{A_URI}">
                    <p:sldSz cx="9144000" cy="6858000" type="screen4x3"/>
                    <p:notesSz cx="6858000" cy="5143500"/>
                    <p:sldIdLst/>
                </p:presentation>
                """
            ).strip(),
            "slide_template.xml": dedent(
                f"""
                <p:sld xmlns:p="{P_URI}" xmlns:a="{A_URI}" xmlns:r="{R_URI}">
                    <p:cSld>
                        <p:spTree>
                            <p:nvGrpSpPr>
                                <p:cNvPr id="1" name="Group 1"/>
                                <p:cNvGrpSpPr/>
                                <p:nvPr/>
                            </p:nvGrpSpPr>
                            <p:grpSpPr/>
                        </p:spTree>
                    </p:cSld>
                    <p:clrMapOvr/>
                </p:sld>
                """
            ).strip(),
            "content_types.xml": dedent(
                f"""
                <Types xmlns="{content_types_uri}">
                    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
                    <Override PartName="/ppt/presentation.xml"
                              ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
                </Types>
                """
            ).strip(),
            "group_shape.xml": dedent(
                f"""
                <p:grpSp xmlns:p="{P_URI}" xmlns:a="{A_URI}">
                    <p:nvGrpSpPr>
                        <p:cNvPr id="1" name="Group"/>
                        <p:cNvGrpSpPr/>
                        <p:nvPr/>
                    </p:nvGrpSpPr>
                    <p:grpSpPr/>
                </p:grpSp>
                """
            ).strip(),
            "group_picture.xml": dedent(
                f"""
                <p:pic xmlns:p="{P_URI}" xmlns:a="{A_URI}" xmlns:r="{R_URI}">
                    <p:nvPicPr>
                        <p:cNvPr id="2" name="Group Picture"/>
                        <p:cNvPicPr/>
                        <p:nvPr/>
                    </p:nvPicPr>
                    <p:blipFill>
                        <a:blip r:embed="rId1"/>
                    </p:blipFill>
                    <p:spPr/>
                </p:pic>
                """
            ).strip(),
            "path_shape.xml": dedent(
                f"""
                <p:sp xmlns:p="{P_URI}" xmlns:a="{A_URI}">
                    <p:nvSpPr>
                        <p:cNvPr id="3" name="Path Shape"/>
                        <p:cNvSpPr/>
                        <p:nvPr/>
                    </p:nvSpPr>
                    <p:spPr>
                        <a:xfrm>
                            <a:off x="0" y="0"/>
                            <a:ext cx="1" cy="1"/>
                        </a:xfrm>
                        <a:custGeom>
                            <a:pathLst>
                                <a:path w="1" h="1"/>
                            </a:pathLst>
                        </a:custGeom>
                    </p:spPr>
                </p:sp>
                """
            ).strip(),
            "path_emf_picture.xml": dedent(
                f"""
                <p:pic xmlns:p="{P_URI}" xmlns:a="{A_URI}" xmlns:r="{R_URI}">
                    <p:nvPicPr>
                        <p:cNvPr id="4" name="Path EMF"/>
                        <p:cNvPicPr/>
                        <p:nvPr/>
                    </p:nvPicPr>
                    <p:blipFill>
                        <a:blip r:embed="rId2"/>
                        <a:stretch><a:fillRect/></a:stretch>
                    </p:blipFill>
                    <p:spPr/>
                </p:pic>
                """
            ).strip(),
            "path_emf_placeholder.xml": dedent(
                f"""
                <p:sp xmlns:p="{P_URI}" xmlns:a="{A_URI}" xmlns:r="{R_URI}">
                    <p:nvSpPr>
                        <p:cNvPr id="5" name="Path Placeholder"/>
                        <p:cNvSpPr/>
                        <p:nvPr/>
                    </p:nvSpPr>
                    <p:spPr/>
                    <p:blipFill>
                        <a:blip r:embed="rId5"/>
                    </p:blipFill>
                </p:sp>
                """
            ).strip(),
            "text_shape.xml": dedent(
                f"""
                <p:sp xmlns:p="{P_URI}" xmlns:a="{A_URI}">
                    <p:nvSpPr>
                        <p:cNvPr id="6" name="Text Shape"/>
                        <p:cNvSpPr txBox="1"/>
                        <p:nvPr/>
                    </p:nvSpPr>
                    <p:spPr/>
                    <p:txBody>
                        <a:bodyPr/>
                        <a:p/>
                    </p:txBody>
                </p:sp>
                """
            ).strip(),
            "text_emf_picture.xml": dedent(
                f"""
                <p:pic xmlns:p="{P_URI}" xmlns:a="{A_URI}" xmlns:r="{R_URI}">
                    <p:nvPicPr>
                        <p:cNvPr id="7" name="Text EMF"/>
                        <p:cNvPicPr/>
                        <p:nvPr/>
                    </p:nvPicPr>
                    <p:blipFill>
                        <a:blip r:embed="rId3"/>
                    </p:blipFill>
                    <p:spPr/>
                </p:pic>
                """
            ).strip(),
            "text_paragraph.xml": dedent(
                f"""
                <a:p xmlns:a="{A_URI}">
                    <a:pPr/>
                    <a:r>
                        <a:rPr lang="en-US" sz="1200"/>
                        <a:t>Sample</a:t>
                    </a:r>
                </a:p>
                """
            ).strip(),
            "text_run.xml": dedent(
                f"""
                <a:r xmlns:a="{A_URI}">
                    <a:rPr lang="en-US" sz="1200"/>
                    <a:t>Sample</a:t>
                </a:r>
                """
            ).strip(),
        }

    def load_template(self, name: str) -> ET._Element:
        try:
            return ET.fromstring(self._templates[name])
        except KeyError as exc:  # pragma: no cover - sanity
            raise FileNotFoundError(name) from exc


def build_builder() -> EnhancedXMLBuilder:
    return EnhancedXMLBuilder(template_loader=DummyLoader())


def _geometry_commands() -> str:
    return (
        f'<a:moveTo xmlns:a="{A_URI}"><a:pt x="0" y="0"/></a:moveTo>'
        f'<a:lnTo xmlns:a="{A_URI}"><a:pt x="2000" y="0"/></a:lnTo>'
        f'<a:lnTo xmlns:a="{A_URI}"><a:pt x="2000" y="2000"/></a:lnTo>'
        f'<a:close xmlns:a="{A_URI}"/>'
    )


def test_generate_path_shape_populates_template():
    builder = build_builder()
    path_shape = builder.path_shapes.generate_path_shape(
        path_id=5,
        x_emu=100,
        y_emu=200,
        width_emu=300,
        height_emu=400,
        path_data=_geometry_commands(),
        fill_xml=path_fill_xml(),
        stroke_xml=path_stroke_xml(),
        clip_xml=path_clip_xml(),
    )

    cnv_pr = path_shape.find(".//p:cNvPr", NSMAP)
    assert cnv_pr is not None
    assert cnv_pr.get("id") == "5"
    assert cnv_pr.get("name") == "Path5"

    xfrm = path_shape.find(".//a:xfrm", NSMAP)
    off = xfrm.find(".//a:off", NSMAP)
    ext = xfrm.find(".//a:ext", NSMAP)
    assert off.get("x") == "100"
    assert off.get("y") == "200"
    assert ext.get("cx") == "300"
    assert ext.get("cy") == "400"

    path_element = path_shape.find(".//a:path", NSMAP)
    assert path_element is not None
    assert len(list(path_element)) == 4  # moveTo, lnTo, lnTo, close appended

    sp_pr = path_shape.find(".//p:spPr", NSMAP)
    assert sp_pr is not None
    tags = [child.tag for child in sp_pr]
    assert any("solidFill" in tag for tag in tags)
    assert any("ln" in tag for tag in tags)
    assert any("clipPath" in tag for tag in tags)


def test_generate_path_emf_picture_adds_opacity_and_clip():
    builder = build_builder()
    emf = builder.path_shapes.generate_path_emf_picture(
        path_id=9,
        x_emu=10,
        y_emu=20,
        width_emu=30,
        height_emu=40,
        embed_id="rId99",
        opacity=0.5,
        clip_xml=path_clip_xml(),
    )

    cnv_pr = emf.find(".//p:cNvPr", NSMAP)
    assert cnv_pr is not None and cnv_pr.get("name") == "PathEMFPicture9"

    blip = emf.find(".//a:blip", NSMAP)
    assert blip is not None
    assert blip.get(f"{{{NSMAP['r']}}}embed") == "rId99"

    effect_lst = emf.find(".//a:effectLst", namespaces={"a": A_URI})
    assert effect_lst is not None
    alpha = effect_lst.find(".//a:alpha", namespaces={"a": A_URI})
    assert alpha is not None and alpha.get("val") == "50000"

    clip = emf.find(".//a:clipPath", namespaces={"a": A_URI})
    assert clip is not None


def test_generate_path_emf_placeholder_warns_on_invalid_fragments(caplog):
    builder = build_builder()
    caplog.set_level("WARNING")

    placeholder = builder.path_shapes.generate_path_emf_placeholder(
        path_id=3,
        x_emu=1,
        y_emu=2,
        width_emu=3,
        height_emu=4,
        embed_id="rId5",
        fill_xml="<not-xml",
        stroke_xml="<also-not-xml",
        clip_xml="<still-not-xml",
    )

    blip = placeholder.find(".//a:blip", NSMAP)
    assert blip is not None
    assert blip.get(f"{{{NSMAP['r']}}}embed") == "rId5"

    # Invalid XML fragments emit warnings without raising
    warnings = [record.message for record in caplog.records if "Invalid" in record.message]
    assert any("Invalid fill XML" in message for message in warnings)
    assert any("Invalid stroke XML" in message for message in warnings)
    assert any("Invalid clip XML" in message for message in warnings)
