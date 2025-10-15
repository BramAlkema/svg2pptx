"""Low-level SVG XML parsing utilities."""

from __future__ import annotations

import logging
import time
from typing import Any

from lxml import etree as ET

from ..xml.safe_iter import walk

logger = logging.getLogger(__name__)


class XMLParser:
    """Wrapper around lxml parsing with recoverable defaults."""

    def __init__(self, parser_config: dict[str, Any]) -> None:
        self.parser_config = parser_config

    def parse(self, content: str) -> ET.Element:
        parser = ET.XMLParser(**self.parser_config)
        return ET.fromstring(content.encode('utf-8'), parser=parser)

    def validate_root(self, svg_root: ET.Element) -> None:
        if svg_root.tag.split('}')[-1].lower() != 'svg':
            raise ValueError("Root element is not <svg>")

    def collect_statistics(self, svg_root: ET.Element) -> dict[str, Any]:
        element_count = sum(1 for _ in walk(svg_root))
        namespaces = set()
        for element in walk(svg_root):
            tag = getattr(element, "tag", "")
            if "}" in str(tag):
                namespace = str(tag).split("}")[0][1:]
                namespaces.add(namespace)
        return {
            "element_count": element_count,
            "namespace_count": len(namespaces),
        }
