"""Path shape generation helpers."""

from __future__ import annotations

from lxml import etree as ET
from lxml.etree import Element, QName

from ..constants import A_URI, NSMAP, R_URI
from .base import BaseShapeGenerator


class PathShapeGenerator(BaseShapeGenerator):
    """Generate path-based shapes and EMF placeholders."""

    def generate_path_shape(
        self,
        path_id: int,
        x_emu: int,
        y_emu: int,
        width_emu: int,
        height_emu: int,
        path_data: str,
        *,
        fill_xml: str | None = None,
        stroke_xml: str | None = None,
        clip_xml: str | None = None,
    ) -> Element:
        path_shape = self.builder.load_template("path_shape.xml")

        cnv_pr = path_shape.find(".//p:cNvPr", NSMAP)
        if cnv_pr is not None:
            cnv_pr.set("id", str(path_id))
            cnv_pr.set("name", f"Path{path_id}")

        xfrm = path_shape.find(".//a:xfrm", NSMAP)
        if xfrm is not None:
            off = xfrm.find(".//a:off", NSMAP)
            if off is not None:
                off.set("x", str(x_emu))
                off.set("y", str(y_emu))
            ext = xfrm.find(".//a:ext", NSMAP)
            if ext is not None:
                ext.set("cx", str(width_emu))
                ext.set("cy", str(height_emu))

        path_element = path_shape.find(".//a:path", NSMAP)
        if path_element is not None:
            path_element.clear()
            if path_data and path_data.strip():
                try:
                    container = ET.fromstring(
                        f'<container xmlns:a="{A_URI}">{path_data}</container>'
                    )
                    for child in container:
                        path_element.append(child)
                except ET.XMLSyntaxError as exc:
                    self.builder.logger.error(
                        "Failed to parse path data as XML: %s", exc
                    )
                    path_element.text = path_data

        sp_pr = path_shape.find(".//p:spPr", NSMAP)
        if sp_pr is not None:
            if fill_xml:
                try:
                    fill_element = ET.fromstring(fill_xml)
                    sp_pr.append(fill_element)
                except ET.XMLSyntaxError:
                    self.builder.logger.warning(
                        "Invalid fill XML provided: %s", fill_xml
                    )
            if stroke_xml:
                try:
                    stroke_element = ET.fromstring(stroke_xml)
                    sp_pr.append(stroke_element)
                except ET.XMLSyntaxError:
                    self.builder.logger.warning(
                        "Invalid stroke XML provided: %s", stroke_xml
                    )
            if clip_xml:
                try:
                    clip_element = ET.fromstring(clip_xml)
                    sp_pr.append(clip_element)
                except ET.XMLSyntaxError:
                    self.builder.logger.warning(
                        "Invalid clip XML provided: %s", clip_xml
                    )

        return path_shape

    def generate_path_emf_picture(
        self,
        path_id: int,
        x_emu: int,
        y_emu: int,
        width_emu: int,
        height_emu: int,
        embed_id: str,
        *,
        opacity: float | None = None,
        clip_xml: str | None = None,
    ) -> Element:
        emf_pic = self.builder.load_template("path_emf_picture.xml")

        cnv_pr = emf_pic.find(".//p:cNvPr", NSMAP)
        if cnv_pr is not None:
            cnv_pr.set("id", str(path_id))
            cnv_pr.set("name", f"PathEMFPicture{path_id}")

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

        if opacity is not None and opacity < 1.0:
            sp_pr = emf_pic.find(".//p:spPr", NSMAP)
            if sp_pr is not None:
                opacity_val = int(opacity * 100000)
                effect_lst = ET.SubElement(sp_pr, QName(A_URI, "effectLst"))
                alpha_elem = ET.SubElement(effect_lst, QName(A_URI, "alpha"))
                alpha_elem.set("val", str(opacity_val))

        sp_pr = emf_pic.find(".//p:spPr", NSMAP)
        if sp_pr is not None and clip_xml:
            try:
                clip_element = ET.fromstring(clip_xml)
                sp_pr.append(clip_element)
            except ET.XMLSyntaxError:
                self.builder.logger.warning(
                    "Invalid clip XML provided: %s", clip_xml
                )

        return emf_pic

    def generate_path_emf_placeholder(
        self,
        path_id: int,
        x_emu: int,
        y_emu: int,
        width_emu: int,
        height_emu: int,
        embed_id: str,
        *,
        fill_xml: str | None = None,
        stroke_xml: str | None = None,
        clip_xml: str | None = None,
    ) -> Element:
        placeholder = self.builder.load_template("path_emf_placeholder.xml")

        cnv_pr = placeholder.find(".//p:cNvPr", NSMAP)
        if cnv_pr is not None:
            cnv_pr.set("id", str(path_id))
            cnv_pr.set("name", f"PathEMFPlaceholder{path_id}")

        xfrm = placeholder.find(".//a:xfrm", NSMAP)
        if xfrm is not None:
            off = xfrm.find(".//a:off", NSMAP)
            if off is not None:
                off.set("x", str(x_emu))
                off.set("y", str(y_emu))
            ext = xfrm.find(".//a:ext", NSMAP)
            if ext is not None:
                ext.set("cx", str(width_emu))
                ext.set("cy", str(height_emu))

        blip = placeholder.find(".//a:blip", NSMAP)
        if blip is not None:
            blip.set(QName(R_URI, "embed"), embed_id)

        sp_pr = placeholder.find(".//p:spPr", NSMAP)
        if sp_pr is not None:
            if fill_xml:
                try:
                    fill_element = ET.fromstring(fill_xml)
                    sp_pr.append(fill_element)
                except ET.XMLSyntaxError:
                    self.builder.logger.warning(
                        "Invalid fill XML provided: %s", fill_xml
                    )
            if stroke_xml:
                try:
                    stroke_element = ET.fromstring(stroke_xml)
                    sp_pr.append(stroke_element)
                except ET.XMLSyntaxError:
                    self.builder.logger.warning(
                        "Invalid stroke XML provided: %s", stroke_xml
                    )
            if clip_xml:
                try:
                    clip_element = ET.fromstring(clip_xml)
                    sp_pr.append(clip_element)
                except ET.XMLSyntaxError:
                    self.builder.logger.warning(
                        "Invalid clip XML provided: %s", clip_xml
                    )

        return placeholder
