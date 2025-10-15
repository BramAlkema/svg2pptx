#!/usr/bin/env python3
"""
Shared base utilities for XML builder components.

Provides template-loader management and ID generation so higher level
builders can focus on presentation-specific concerns.
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from lxml import etree as ET
from lxml.etree import Element

if TYPE_CHECKING:  # pragma: no cover
    from ...io.template_loader import TemplateLoader


def _resolve_template_loader():
    from ...io.template_loader import get_template_loader

    return get_template_loader()


class XMLBuilderBase:
    """Base class supplying template access and ID counters for builders."""

    def __init__(
        self,
        *,
        template_loader: "TemplateLoader" | None = None,
        services: Any | None = None,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self._id_counter = 1
        self.template_loader: "TemplateLoader" = template_loader or _resolve_template_loader()
        self.services = services

    def load_template(self, name: str) -> Element:
        """Fetch a template element using the configured loader."""
        return self.template_loader.load_template(name)

    def get_next_id(self) -> int:
        """Return the next unique ID for generated XML nodes."""
        current = self._id_counter
        self._id_counter += 1
        return current


    def reset_id_counter(self) -> None:
        """Reset the ID counter—handy for tests and fresh documents."""
        self._id_counter = 1

    def element_to_string(self, element: Element, pretty_print: bool = True) -> str:
        """Serialize an XML element to a UTF-8 string."""
        return ET.tostring(
            element,
            xml_declaration=True,
            encoding="UTF-8",
            pretty_print=pretty_print,
        ).decode("utf-8")

    def validate_element(self, element: Element, schema_path: str | None = None) -> bool:
        """Validate XML element structure, optionally using an XSD schema."""
        try:
            ET.fromstring(ET.tostring(element))
            if schema_path:
                try:
                    with open(schema_path, "rb") as handle:
                        schema_doc = ET.parse(handle)
                        schema = ET.XMLSchema(schema_doc)
                        schema.assertValid(element)
                except Exception as exc:  # noqa: BLE001
                    self.logger.warning("Schema validation failed: %s", exc)
                    return False
            return True
        except ET.XMLSyntaxError as exc:
            self.logger.error("XML validation failed: %s", exc)
            return False

    def add_text_to_element(self, element: Element, text: str) -> None:
        """Attach text content to an element, handling None gracefully."""
        if text:
            element.text = str(text)

    def emu(self, value: float | int, axis: str = "uniform"):
        """Delegate EMU conversion via attached services if available."""
        if not self.services or not hasattr(self.services, "emu"):
            raise RuntimeError(
                "XMLBuilder requires ConversionServices.emu(); attach services before use."
            )
        return self.services.emu(value, axis=axis)
