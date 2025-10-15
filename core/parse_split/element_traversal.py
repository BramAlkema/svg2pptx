"""DOM traversal helpers for the sliced SVG parser."""

from __future__ import annotations

from typing import Callable, Iterable, List

from lxml import etree as ET

from ..transforms.coordinate_space import CoordinateSpace
from ..transforms.core import Matrix


TraverseCallback = Callable[[ET.Element, object | None], list]


class ElementTraversal:
    """Traverse SVG DOM nodes and delegate conversion to the IR converter."""

    def __init__(
        self,
        ir_converter,
        hyperlink_processor,
        transform_parser,
        children_iter: Callable[[ET.Element], Iterable[ET.Element]],
        logger,
    ) -> None:
        self._ir_converter = ir_converter
        self._hyperlinks = hyperlink_processor
        self._transform_parser = transform_parser
        self._children = children_iter
        self._logger = logger
        self._coord_space = CoordinateSpace(Matrix.identity())

    def extract(self, svg_root: ET.Element) -> list:
        """Convert an SVG element (typically the root) into IR elements."""
        return self._extract_recursive(svg_root, current_navigation=None)

    def _extract_recursive(self, element: ET.Element, current_navigation) -> list:
        ir_elements: list = []

        transform_pushed = self._push_transform(element)

        try:
            tag = self._local_name(getattr(element, "tag", None))
            if tag == "a":
                navigation_spec = self._hyperlinks.resolve_navigation(element)
                child_navigation = navigation_spec or current_navigation
                for child in self._children(element):
                    ir_elements.extend(self._extract_recursive(child, child_navigation))
                return ir_elements

            if tag == "g":
                child_nodes: list = []
                for child in self._children(element):
                    child_nodes.extend(self._extract_recursive(child, current_navigation))

                group = self._ir_converter.convert_group(element, child_nodes)
                if group:
                    self._ir_converter.attach_metadata(group, element, current_navigation)
                    ir_elements.append(group)
                return ir_elements

            converted = self._ir_converter.convert_element(
                tag=tag,
                element=element,
                coord_space=self._coord_space,
                current_navigation=current_navigation,
                traverse_callback=self._extract_recursive,
            )

            if converted is None:
                for child in self._children(element):
                    ir_elements.extend(self._extract_recursive(child, current_navigation))
                return ir_elements

            if not isinstance(converted, list):
                converted = [converted]

            for item in converted:
                if item is None:
                    continue
                self._ir_converter.attach_metadata(item, element, current_navigation)
                ir_elements.append(item)

            return ir_elements
        finally:
            if transform_pushed:
                self._pop_transform()

    def _push_transform(self, element: ET.Element) -> bool:
        transform_attr = element.get("transform")
        if not transform_attr:
            return False

        try:
            matrix = self._transform_parser.parse_to_matrix(transform_attr)
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.warning(f"Failed to parse transform '{transform_attr}': {exc}")
            return False

        if matrix is None:
            return False

        try:
            self._coord_space.push_transform(matrix)
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.warning(f"Failed to push transform '{transform_attr}': {exc}")
            return False
        return True

    def _pop_transform(self) -> None:
        try:
            self._coord_space.pop_transform()
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.warning(f"Failed to pop transform: {exc}")

    @staticmethod
    def _local_name(tag: str | None) -> str:
        if not tag:
            return ""
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag


__all__ = ["ElementTraversal"]
