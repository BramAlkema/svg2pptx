"""Image shape generation helpers."""

from __future__ import annotations

from lxml import etree as ET
from lxml.etree import Element, QName

from ..constants import NSMAP, R_URI
from .base import BaseShapeGenerator


class ImageShapeGenerator(BaseShapeGenerator):
    """Generate raster/vector image picture elements."""

    def generate_image_raster_picture(
        self,
        image_id: int,
        x_emu: int,
        y_emu: int,
        width_emu: int,
        height_emu: int,
        rel_id: str,
        *,
        effects_xml: str | None = None,
    ) -> Element:
        image_pic = self.builder.load_template("image_raster_picture.xml")

        cnv_pr = image_pic.find(".//p:cNvPr", NSMAP)
        if cnv_pr is not None:
            cnv_pr.set("id", str(image_id))
            cnv_pr.set("name", f"Image_{image_id}")

        xfrm = image_pic.find(".//a:xfrm", NSMAP)
        if xfrm is not None:
            off = xfrm.find(".//a:off", NSMAP)
            if off is not None:
                off.set("x", str(x_emu))
                off.set("y", str(y_emu))
            ext = xfrm.find(".//a:ext", NSMAP)
            if ext is not None:
                ext.set("cx", str(width_emu))
                ext.set("cy", str(height_emu))

        blip = image_pic.find(".//a:blip", NSMAP)
        if blip is not None:
            blip.set(QName(R_URI, "embed"), rel_id)

        if effects_xml:
            try:
                effects_element = ET.fromstring(effects_xml)
                sp_pr = image_pic.find(".//p:spPr", NSMAP)
                if sp_pr is not None:
                    sp_pr.append(effects_element)
            except ET.XMLSyntaxError:
                self.builder.logger.warning(
                    "Invalid effects XML provided: %s", effects_xml
                )

        return image_pic

    def generate_image_vector_picture(
        self,
        image_id: int,
        x_emu: int,
        y_emu: int,
        width_emu: int,
        height_emu: int,
        rel_id: str,
        *,
        effects_xml: str | None = None,
    ) -> Element:
        image_pic = self.builder.load_template("image_vector_picture.xml")

        cnv_pr = image_pic.find(".//p:cNvPr", NSMAP)
        if cnv_pr is not None:
            cnv_pr.set("id", str(image_id))
            cnv_pr.set("name", f"VectorImage_{image_id}")

        xfrm = image_pic.find(".//a:xfrm", NSMAP)
        if xfrm is not None:
            off = xfrm.find(".//a:off", NSMAP)
            if off is not None:
                off.set("x", str(x_emu))
                off.set("y", str(y_emu))
            ext = xfrm.find(".//a:ext", NSMAP)
            if ext is not None:
                ext.set("cx", str(width_emu))
                ext.set("cy", str(height_emu))

        blip = image_pic.find(".//a:blip", NSMAP)
        if blip is not None:
            blip.set(QName(R_URI, "embed"), rel_id)

        if effects_xml:
            try:
                effects_element = ET.fromstring(effects_xml)
                sp_pr = image_pic.find(".//p:spPr", NSMAP)
                if sp_pr is not None:
                    sp_pr.append(effects_element)
            except ET.XMLSyntaxError:
                self.builder.logger.warning(
                    "Invalid effects XML provided: %s", effects_xml
                )

        return image_pic
