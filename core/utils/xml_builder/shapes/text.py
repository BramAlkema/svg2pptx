"""Text shape generation helpers."""

from __future__ import annotations

from lxml import etree as ET
from lxml.etree import Element, QName

from ..constants import A_URI, NSMAP, R_URI
from .base import BaseShapeGenerator


class TextShapeGenerator(BaseShapeGenerator):
    """Generate text frame elements and related EMF placeholders."""

    def generate_text_shape(
        self,
        text_id: int,
        x_emu: int,
        y_emu: int,
        width_emu: int,
        height_emu: int,
        paragraphs_xml: str,
        *,
        effects_xml: str | None = None,
    ) -> Element:
        text_shape = self.builder.load_template("text_shape.xml")

        cnv_pr = text_shape.find(".//p:cNvPr", NSMAP)
        if cnv_pr is not None:
            cnv_pr.set("id", str(text_id))
            cnv_pr.set("name", f"TextFrame{text_id}")

        xfrm = text_shape.find(".//a:xfrm", NSMAP)
        if xfrm is not None:
            off = xfrm.find(".//a:off", NSMAP)
            if off is not None:
                off.set("x", str(x_emu))
                off.set("y", str(y_emu))
            ext = xfrm.find(".//a:ext", NSMAP)
            if ext is not None:
                ext.set("cx", str(width_emu))
                ext.set("cy", str(height_emu))

        tx_body = text_shape.find(".//p:txBody", NSMAP)
        if tx_body is not None and paragraphs_xml:
            try:
                fragment = f"<root xmlns:a='{A_URI}'>{paragraphs_xml}</root>"
                root = ET.fromstring(fragment)
                for paragraph in root:
                    tx_body.append(paragraph)
            except ET.XMLSyntaxError:
                self.builder.logger.warning(
                    "Invalid paragraphs XML provided: %s", paragraphs_xml
                )

        sp_pr = text_shape.find(".//p:spPr", NSMAP)
        if sp_pr is not None and effects_xml:
            try:
                effects_element = ET.fromstring(effects_xml)
                sp_pr.append(effects_element)
            except ET.XMLSyntaxError:
                self.builder.logger.warning(
                    "Invalid effects XML provided: %s", effects_xml
                )

        return text_shape

    def generate_text_emf_picture(
        self,
        text_id: int,
        x_emu: int,
        y_emu: int,
        width_emu: int,
        height_emu: int,
        embed_id: str,
        *,
        effects_xml: str | None = None,
    ) -> Element:
        emf_pic = self.builder.load_template("text_emf_picture.xml")

        cnv_pr = emf_pic.find(".//p:cNvPr", NSMAP)
        if cnv_pr is not None:
            cnv_pr.set("id", str(text_id))
            cnv_pr.set("name", f"EMF_Text{text_id}")

        blip = emf_pic.find(".//a:blip", NSMAP)
        if blip is not None:
            blip.set(QName(R_URI, "embed"), embed_id)

        xfrm = emf_pic.find(".//a:xfrm", NSMAP)
        if xfrm is not None:
            off = xfrm.find(".//a:off", NSMAP)
            if off is not None:
                off.set("x", str(x_emu))
                off.set("y", str(y_emu))
            ext = xfrm.find(".//a:ext", NSMAP)
            if ext is not None:
                ext.set("cx", str(width_emu))
                ext.set("cy", str(height_emu))

        sp_pr = emf_pic.find(".//p:spPr", NSMAP)
        if sp_pr is not None and effects_xml:
            try:
                effects_element = ET.fromstring(effects_xml)
                sp_pr.append(effects_element)
            except ET.XMLSyntaxError:
                self.builder.logger.warning(
                    "Invalid effects XML provided: %s", effects_xml
                )

        return emf_pic

    def generate_text_paragraph(self, runs_xml: str) -> Element:
        paragraph = self.builder.load_template("text_paragraph.xml")

        if runs_xml:
            try:
                fragment = f"<root xmlns:a='{A_URI}'>{runs_xml}</root>"
                root = ET.fromstring(fragment)
                for run in root:
                    paragraph.append(run)
            except ET.XMLSyntaxError:
                self.builder.logger.warning(
                    "Invalid runs XML provided: %s", runs_xml
                )

        return paragraph

    def generate_text_run(
        self,
        text_content: str,
        font_family: str = "Arial",
        font_size: float = 12.0,
        *,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        rgb: str = "000000",
        formatting_xml: str | None = None,
    ) -> Element:
        text_run = self.builder.load_template("text_run.xml")

        text_elem = text_run.find(".//a:t", NSMAP)
        if text_elem is not None:
            self.builder.add_text_to_element(text_elem, text_content)

        r_pr = text_run.find(".//a:rPr", NSMAP)
        if r_pr is not None:
            r_pr.set("lang", "en-US")
            r_pr.set("sz", str(int(font_size * 100)))
            r_pr.set("b", "1" if bold else "0")
            r_pr.set("i", "1" if italic else "0")
            r_pr.set("u", "sng" if underline else "none")
            r_pr.set("dirty", "0")

            srgb_clr = r_pr.find(".//a:srgbClr", NSMAP)
            if srgb_clr is not None:
                srgb_clr.set("val", rgb)

            latin = r_pr.find(".//a:latin", NSMAP)
            if latin is not None:
                latin.set("typeface", font_family)

            if formatting_xml:
                try:
                    formatting_element = ET.fromstring(formatting_xml)
                    r_pr.append(formatting_element)
                except ET.XMLSyntaxError:
                    self.builder.logger.warning(
                        "Invalid formatting XML provided: %s", formatting_xml
                    )

        return text_run
