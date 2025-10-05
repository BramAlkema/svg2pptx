#!/usr/bin/env python3
"""
Base Preprocessor Class

Abstract base class for SVG preprocessors that provides common functionality
and establishes the preprocessor interface.
"""

from abc import ABC, abstractmethod

from lxml import etree as ET


class BasePreprocessor(ABC):
    """
    Abstract base class for SVG preprocessors.

    All preprocessors should inherit from this class and implement
    the process method.
    """

    @abstractmethod
    def process(self, svg_root: ET.Element) -> ET.Element:
        """
        Process the SVG element tree.

        Args:
            svg_root: Root SVG element

        Returns:
            Processed SVG element tree
        """
        pass

    def validate_svg(self, svg_root: ET.Element) -> bool:
        """
        Validate that the element is a valid SVG root.

        Args:
            svg_root: Element to validate

        Returns:
            True if valid SVG root
        """
        if svg_root is None:
            return False

        # Check if it's an SVG element
        if not svg_root.tag.endswith('svg'):
            return False

        return True

    def get_svg_namespace_uri(self) -> str:
        """Get the SVG namespace URI."""
        return "http://www.w3.org/2000/svg"

    def create_svg_element(self, tag: str, **attributes) -> ET.Element:
        """
        Create an SVG element with proper namespace.

        Args:
            tag: Element tag name (without namespace)
            **attributes: Element attributes

        Returns:
            SVG element
        """
        full_tag = f"{{{self.get_svg_namespace_uri()}}}{tag}"
        element = ET.Element(full_tag, attributes)
        return element

    def is_svg_element(self, element: ET.Element, tag: str) -> bool:
        """
        Check if element is an SVG element with specific tag.

        Args:
            element: Element to check
            tag: Tag name to match

        Returns:
            True if element matches
        """
        if element is None:
            return False

        return element.tag.endswith(tag)

    def get_element_id(self, element: ET.Element) -> str:
        """
        Get the ID of an element, generating one if needed.

        Args:
            element: Element to get ID for

        Returns:
            Element ID
        """
        element_id = element.get('id')
        if not element_id:
            # Generate unique ID
            import time
            element_id = f"gen_{int(time.time() * 1000) % 1000000}"
            element.set('id', element_id)

        return element_id

    def copy_attributes(self, source: ET.Element, target: ET.Element,
                       exclude: set = None) -> None:
        """
        Copy attributes from source to target element.

        Args:
            source: Source element
            target: Target element
            exclude: Set of attribute names to exclude
        """
        exclude = exclude or set()

        for attr, value in source.attrib.items():
            if attr not in exclude:
                target.set(attr, value)