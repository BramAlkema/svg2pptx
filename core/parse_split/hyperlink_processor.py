"""Navigation helpers for the sliced SVG parser."""

from __future__ import annotations

from typing import Callable, Iterable

from lxml import etree as ET

from ..pipeline.navigation import NavigationSpec, parse_svg_navigation


ChildIterator = Callable[[ET.Element], Iterable[ET.Element]]


class HyperlinkProcessor:
    """Extracts navigation metadata from SVG hyperlink elements."""

    def __init__(self, logger, children_iter: ChildIterator) -> None:
        self._logger = logger
        self._children = children_iter

    def resolve_navigation(self, hyperlink_element: ET.Element) -> NavigationSpec | None:
        """Return navigation spec for a hyperlink element, logging on invalid data."""
        href = hyperlink_element.get("href") or hyperlink_element.get("{http://www.w3.org/1999/xlink}href")
        attrs = self._extract_navigation_attributes(hyperlink_element)
        tooltip = self._extract_hyperlink_tooltip(hyperlink_element)

        has_navigation_data = bool(href) or any(attrs.values())

        navigation_spec = self._parse_navigation_attributes(href, attrs, tooltip)
        if navigation_spec is None and has_navigation_data:
            self._logger.warning(f"Invalid navigation attributes: href={href}, attrs={attrs}")

        return navigation_spec

    def resolve_inline_navigation(self, anchor_element: ET.Element) -> NavigationSpec | None:
        """Return navigation spec for inline hyperlink nodes inside text content."""
        href = anchor_element.get("href") or anchor_element.get("{http://www.w3.org/1999/xlink}href")
        attrs = self._extract_navigation_attributes(anchor_element)
        tooltip = self._extract_hyperlink_tooltip(anchor_element)

        try:
            return self._parse_navigation_attributes(href, attrs, tooltip)
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.warning("Failed to parse navigation attributes: %s", exc)
            return None

    def _extract_navigation_attributes(self, hyperlink_element: ET.Element) -> dict:
        navigation_attrs: dict[str, str] = {}

        for attr_name in (
            "data-slide",
            "data-jump",
            "data-bookmark",
            "data-custom-show",
            "data-visited",
        ):
            attr_value = hyperlink_element.get(attr_name)
            if attr_value is not None:
                navigation_attrs[attr_name] = attr_value

        return navigation_attrs

    def _extract_hyperlink_tooltip(self, hyperlink_element: ET.Element) -> str | None:
        for child in self._children(hyperlink_element):
            if self._local_name(child.tag) == "title":
                tooltip = self._collect_text_content(child)
                if tooltip and tooltip.strip():
                    return tooltip.strip()
        return None

    def _collect_text_content(self, element: ET.Element) -> str:
        parts: list[str] = []

        if element.text:
            parts.append(element.text)

        for child in self._children(element):
            child_text = self._collect_text_content(child)
            if child_text:
                parts.append(child_text)
            if child.tail:
                parts.append(child.tail)

        if element.tail:
            parts.append(element.tail)

        return "".join(parts)

    def _parse_navigation_attributes(
        self,
        href: str | None,
        element_attrs: dict,
        tooltip: str | None,
    ) -> NavigationSpec | None:
        if not (href or element_attrs or tooltip):
            return None

        return parse_svg_navigation(href, element_attrs, tooltip)

    @staticmethod
    def _local_name(tag: str | None) -> str:
        if not tag:
            return ""
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag


__all__ = ["HyperlinkProcessor"]
