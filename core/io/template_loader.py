#!/usr/bin/env python3
"""
Template loader utilities for EnhancedXMLBuilder.

Provides a minimal filesystem-backed loader with a built-in fallback set of
namespaced templates so unit tests and developer workflows do not depend on
the full PPTX template bundle being present.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from lxml import etree as ET

P_URI = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_URI = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_URI = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT_URI = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_URI = "http://schemas.openxmlformats.org/package/2006/relationships"

_FALLBACK_TEMPLATES: Dict[str, str] = {
    "presentation.xml": f"""
        <p:presentation xmlns:p="{P_URI}" xmlns:a="{A_URI}">
            <p:sldSz cx="9144000" cy="6858000" type="screen4x3"/>
            <p:notesSz cx="6858000" cy="5143500"/>
            <p:sldIdLst/>
        </p:presentation>
    """,
    "slide_template.xml": f"""
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
    """,
    "content_types.xml": f"""
        <Types xmlns="{CT_URI}">
            <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
            <Default Extension="xml" ContentType="application/xml"/>
            <Override PartName="/ppt/presentation.xml"
                      ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
        </Types>
    """,
    "group_shape.xml": f"""
        <p:grpSp xmlns:p="{P_URI}" xmlns:a="{A_URI}">
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name="Group"/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr/>
        </p:grpSp>
    """,
    "group_picture.xml": f"""
        <p:pic xmlns:p="{P_URI}" xmlns:a="{A_URI}" xmlns:r="{R_URI}">
            <p:nvPicPr>
                <p:cNvPr id="2" name="Group Picture"/>
                <p:cNvPicPr/>
                <p:nvPr/>
            </p:nvPicPr>
            <p:blipFill>
                <a:blip r:embed="rId1"/>
                <a:stretch><a:fillRect/></a:stretch>
            </p:blipFill>
            <p:spPr/>
        </p:pic>
    """,
    "path_shape.xml": f"""
        <p:sp xmlns:p="{P_URI}" xmlns:a="{A_URI}">
            <p:nvSpPr>
                <p:cNvPr id="3" name="Path Shape"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr>
                <a:custGeom>
                    <a:avLst/>
                    <a:gdLst/>
                    <a:pathLst/>
                </a:custGeom>
            </p:spPr>
        </p:sp>
    """,
    "path_emf_picture.xml": f"""
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
    """,
    "path_emf_placeholder.xml": f"""
        <p:sp xmlns:p="{P_URI}" xmlns:a="{A_URI}">
            <p:nvSpPr>
                <p:cNvPr id="5" name="Path Placeholder"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr/>
        </p:sp>
    """,
    "text_shape.xml": f"""
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
    """,
    "text_emf_picture.xml": f"""
        <p:pic xmlns:p="{P_URI}" xmlns:a="{A_URI}" xmlns:r="{R_URI}">
            <p:nvPicPr>
                <p:cNvPr id="7" name="Text EMF"/>
                <p:cNvPicPr/>
                <p:nvPr/>
            </p:nvPicPr>
            <p:blipFill>
                <a:blip r:embed="rId3"/>
                <a:stretch><a:fillRect/></a:stretch>
            </p:blipFill>
            <p:spPr/>
        </p:pic>
    """,
    "text_paragraph.xml": f"""
        <a:p xmlns:a="{A_URI}">
            <a:pPr/>
            <a:r>
                <a:rPr lang="en-US" sz="1200"/>
                <a:t>Sample</a:t>
            </a:r>
        </a:p>
    """,
    "text_run.xml": f"""
        <a:r xmlns:a="{A_URI}">
            <a:rPr lang="en-US" sz="1200"/>
            <a:t>Sample</a:t>
        </a:r>
    """,
}


@dataclass
class TemplateLoader:
    """Load PPTX templates from disk with a fallback for unit tests."""

    template_root: Path | None = None

    def __post_init__(self) -> None:
        default_root = Path(__file__).parents[2] / "pptx_templates"
        self._root = self.template_root or default_root
        self._cache: Dict[str, ET._Element] = {}
        self._parser = ET.XMLParser(remove_blank_text=False)

    def load_template(self, name: str) -> ET._Element:
        """Return a mutable XML element for the requested template."""
        if name in self._cache:
            return copy.deepcopy(self._cache[name])

        candidate_paths = [
            self._root / name,
            self._root / "clean_slate" / name,
            self._root / f"{name}.xml",
            self._root / "clean_slate" / f"{name}.xml",
        ]

        for path in candidate_paths:
            if path.exists():
                with path.open("rb") as handle:
                    element = ET.fromstring(handle.read(), parser=self._parser)
                self._cache[name] = element
                return copy.deepcopy(element)

        if name in _FALLBACK_TEMPLATES:
            element = ET.fromstring(_FALLBACK_TEMPLATES[name])
            self._cache[name] = element
            return copy.deepcopy(element)

        raise FileNotFoundError(name)


def get_template_loader(template_root: Path | None = None) -> TemplateLoader:
    """Factory for the default template loader."""
    return TemplateLoader(template_root=template_root)


def build_stub_loader() -> TemplateLoader:
    """Return a loader bound to the embedded fallback templates."""
    return TemplateLoader(template_root=None)


__all__ = ["TemplateLoader", "build_stub_loader", "get_template_loader"]
