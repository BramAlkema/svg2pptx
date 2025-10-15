"""Group shape generation helpers."""

from __future__ import annotations

from typing import Iterable

from lxml import etree as ET
from lxml.etree import Element, QName

from ..constants import A_URI, NSMAP, R_URI
from .base import BaseShapeGenerator


class GroupShapeGenerator(BaseShapeGenerator):
    """Generate group-based shapes and pictures."""

    def generate_group_shape(
        self,
        group_id: int,
        x_emu: int,
        y_emu: int,
        width_emu: int,
        height_emu: int,
        child_elements: Iterable[Element],
        *,
        opacity: float | None = None,
        clip_xml: str | None = None,
    ) -> Element:
        group_shape = self.builder.load_template("group_shape.xml")

        cnv_pr = group_shape.find(".//p:cNvPr", NSMAP)
        if cnv_pr is not None:
            cnv_pr.set("id", str(group_id))
            cnv_pr.set("name", f"Group{group_id}")

        xfrm = group_shape.find(".//a:xfrm", NSMAP)
        if xfrm is not None:
            off = xfrm.find(".//a:off", NSMAP)
            if off is not None:
                off.set("x", str(x_emu))
                off.set("y", str(y_emu))
            ext = xfrm.find(".//a:ext", NSMAP)
            if ext is not None:
                ext.set("cx", str(width_emu))
                ext.set("cy", str(height_emu))
            ch_ext = xfrm.find(".//a:chExt", NSMAP)
            if ch_ext is not None:
                ch_ext.set("cx", str(width_emu))
                ch_ext.set("cy", str(height_emu))

        grp_sp_pr = group_shape.find(".//p:grpSpPr", NSMAP)
        if grp_sp_pr is not None:
            if opacity is not None and opacity < 1.0:
                opacity_val = int(opacity * 100000)
                effect_lst = ET.SubElement(grp_sp_pr, QName(A_URI, "effectLst"))
                alpha_elem = ET.SubElement(effect_lst, QName(A_URI, "alpha"))
                alpha_elem.set("val", str(opacity_val))
            if clip_xml:
                try:
                    clip_element = ET.fromstring(clip_xml)
                    grp_sp_pr.append(clip_element)
                except ET.XMLSyntaxError:
                    self.builder.logger.warning(
                        "Invalid clip XML provided: %s", clip_xml
                    )

        if child_elements:
            for comment in group_shape.xpath(
                '//comment()[contains(., "CHILD ELEMENTS")]'
            ):
                parent = comment.getparent()
                if parent is not None:
                    parent.remove(comment)
                    for child in child_elements:
                        parent.append(child)
                    break

        return group_shape

    def generate_group_picture(
        self,
        group_id: int,
        x_emu: int,
        y_emu: int,
        width_emu: int,
        height_emu: int,
        embed_id: str,
        *,
        opacity: float | None = None,
        clip_xml: str | None = None,
    ) -> Element:
        group_pic = self.builder.load_template("group_picture.xml")

        cnv_pr = group_pic.find(".//p:cNvPr", NSMAP)
        if cnv_pr is not None:
            cnv_pr.set("id", str(group_id))
            cnv_pr.set("name", f"GroupPicture{group_id}")

        blip = group_pic.find(".//a:blip", NSMAP)
        if blip is not None:
            blip.set(QName(R_URI, "embed"), embed_id)

        xfrm = group_pic.find(".//a:xfrm", NSMAP)
        if xfrm is not None:
            off = xfrm.find(".//a:off", NSMAP)
            if off is not None:
                off.set("x", str(x_emu))
                off.set("y", str(y_emu))
            ext = xfrm.find(".//a:ext", NSMAP)
            if ext is not None:
                ext.set("cx", str(width_emu))
                ext.set("cy", str(height_emu))

        sp_pr = group_pic.find(".//p:spPr", NSMAP)
        if sp_pr is not None:
            if opacity is not None and opacity < 1.0:
                opacity_val = int(opacity * 100000)
                effect_lst = ET.SubElement(sp_pr, QName(A_URI, "effectLst"))
                alpha_elem = ET.SubElement(effect_lst, QName(A_URI, "alpha"))
                alpha_elem.set("val", str(opacity_val))
            if clip_xml:
                try:
                    clip_element = ET.fromstring(clip_xml)
                    sp_pr.append(clip_element)
                except ET.XMLSyntaxError:
                    self.builder.logger.warning(
                        "Invalid clip XML provided: %s", clip_xml
                    )

        return group_pic
