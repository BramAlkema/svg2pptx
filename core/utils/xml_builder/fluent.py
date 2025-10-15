"""Fluent interface helpers for composing PPTX shapes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lxml.etree import Element

from .constants import NSMAP

if TYPE_CHECKING:  # pragma: no cover
    from .builder import EnhancedXMLBuilder


class FluentShapeBuilder:
    """Chainable builder for configuring shape geometry and transforms."""

    def __init__(self, xml_builder: "EnhancedXMLBuilder", shape_id: int, name: str):
        self.xml_builder = xml_builder
        self.shape_element = xml_builder.create_shape_element(shape_id, name)

    def position(self, x: int, y: int) -> "FluentShapeBuilder":
        """Set shape position."""
        xfrm = self.shape_element.find(".//a:xfrm", NSMAP)
        if xfrm is not None:
            off = xfrm.find(".//a:off", NSMAP)
            if off is not None:
                off.set("x", str(x))
                off.set("y", str(y))
        return self

    def size(self, width: int, height: int) -> "FluentShapeBuilder":
        """Set shape dimensions."""
        xfrm = self.shape_element.find(".//a:xfrm", NSMAP)
        if xfrm is not None:
            ext = xfrm.find(".//a:ext", NSMAP)
            if ext is not None:
                ext.set("cx", str(width))
                ext.set("cy", str(height))
        return self

    def geometry(self, geometry_element: Element) -> "FluentShapeBuilder":
        """Attach geometry content to the underlying shape."""
        self.xml_builder.add_geometry_to_shape(self.shape_element, geometry_element)
        return self

    def build(self) -> Element:
        """Return the assembled shape element."""
        return self.shape_element
