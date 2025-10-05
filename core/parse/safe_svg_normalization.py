#!/usr/bin/env python3
"""
Safe SVG Normalization

Enhanced version of SVG normalization that handles lxml/cython edge cases.
Specifically addresses the issue where XML comments appear as cython functions
during element iteration, causing "argument of type '_cython_3_1_3.cython_function_or_method' is not iterable" errors.
"""

import logging
from collections.abc import Iterator
from typing import Any, Dict, Optional, Tuple

from lxml import etree as ET

from ..xml.safe_iter import children, walk


def safe_element_iteration(element: ET.Element) -> Iterator[ET.Element]:
    """
    Safely iterate over XML element children, filtering out cython Comment objects.

    This is a compatibility wrapper for existing code. New code should use
    core.xml.safe_iter.children() directly.

    Args:
        element: XML element to iterate over

    Yields:
        Child elements that are actual XML Element objects (not comments, processing instructions, etc.)
    """
    return children(element)


def safe_normalize_svg(svg_content: str) -> Optional[Any]:  # ET.Element is not a type (Cython factory)
    """
    Safe SVG normalization with comprehensive error handling.

    Args:
        svg_content: SVG content as string

    Returns:
        Normalized SVG element or None if normalization fails
    """
    if not svg_content or not svg_content.strip():
        logging.warning("Empty or whitespace SVG content")
        return None

    try:
        # Parse with lxml safety
        parsed = ET.fromstring(svg_content.encode('utf-8'))
        if parsed is None:
            logging.error("SVG parsing returned None")
            return None

        # Validate root element
        if not hasattr(parsed, 'tag') or 'svg' not in parsed.tag.lower():
            logging.error(f"Invalid SVG root element: {getattr(parsed, 'tag', 'unknown')}")
            return None

        return parsed

    except ET.XMLSyntaxError as e:
        logging.error(f"SVG XML syntax error: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected SVG normalization error: {e}")
        return None


class SafeSVGNormalizer:
    """
    Enhanced SVG normalizer with cython/lxml compatibility.

    Provides the same functionality as the original SVGNormalizer but with
    safe iteration patterns that handle cython Comment objects properly.
    """

    def __init__(self):
        """Initialize normalizer with basic configuration"""
        self.logger = logging.getLogger(__name__)

        # Normalization settings
        self.settings = {
            'fix_namespaces': True,
            'normalize_whitespace': True,
            'fix_encoding_issues': True,
            'add_missing_attributes': True,
            'validate_structure': True,
            'filter_comments': True,  # New setting for comment filtering
        }

    def normalize(self, svg_root: ET.Element) -> tuple[ET.Element, dict[str, Any]]:
        """
        Normalize SVG element tree with safe iteration.

        Args:
            svg_root: SVG root element to normalize

        Returns:
            Tuple of (normalized_element, changes_dict)
        """
        changes = {
            'namespaces_fixed': False,
            'attributes_added': [],
            'structure_fixes': [],
            'encoding_fixes': [],
            'whitespace_normalized': False,
            'comments_filtered': False,  # Track comment filtering
        }

        try:
            self.logger.debug("Starting safe SVG normalization")

            # Apply safe normalization steps
            if self.settings['fix_namespaces']:
                svg_root = self._safe_fix_namespaces(svg_root, changes)

            if self.settings['add_missing_attributes']:
                svg_root = self._safe_add_missing_attributes(svg_root, changes)

            if self.settings['normalize_whitespace']:
                self._safe_normalize_whitespace(svg_root, changes)

            if self.settings['validate_structure']:
                self._safe_fix_structure_issues(svg_root, changes)

            self.logger.debug(f"Safe SVG normalization completed: {changes}")
            return svg_root, changes

        except Exception as e:
            self.logger.error(f"Safe SVG normalization failed: {e}")
            # Return original element with error info
            changes['error'] = str(e)
            return svg_root, changes

    def _safe_fix_namespaces(self, svg_root: ET.Element, changes: dict[str, Any]) -> ET.Element:
        """Fix namespace declarations with safe iteration."""
        # Check if SVG namespace is properly declared
        svg_ns = 'http://www.w3.org/2000/svg'

        try:
            # Check current namespace
            if svg_root.nsmap is None or svg_ns not in svg_root.nsmap.values():
                # Need to rebuild with proper namespaces
                nsmap = {None: svg_ns}  # Default namespace

                # Preserve existing namespaces
                if hasattr(svg_root, 'nsmap') and svg_root.nsmap:
                    for prefix, uri in svg_root.nsmap.items():
                        if uri != svg_ns:  # Don't duplicate SVG namespace
                            nsmap[prefix] = uri

                # Rebuild element tree with correct namespaces
                svg_root = self._safe_rebuild_with_namespaces(svg_root, nsmap)
                changes['namespaces_fixed'] = True

            return svg_root

        except Exception as e:
            self.logger.warning(f"Namespace fixing failed: {e}")
            return svg_root

    def _safe_rebuild_with_namespaces(self, element: ET.Element, nsmap: dict[str, str]) -> ET.Element:
        """Rebuild element tree with proper namespaces using safe iteration."""
        # Create new root with namespace map
        tag = element.tag
        if '}' not in tag and nsmap.get(None):
            # Add default namespace if missing
            tag = f"{{{nsmap[None]}}}{tag}"

        new_root = ET.Element(tag, nsmap=nsmap)

        # Copy attributes
        for attr, value in element.attrib.items():
            new_root.set(attr, value)

        # Copy text content
        if element.text:
            new_root.text = element.text
        if element.tail:
            new_root.tail = element.tail

        # Safely copy children using safe iteration
        for child in children(element):
            new_child = self._safe_copy_element_with_namespaces(child, nsmap)
            new_root.append(new_child)

        return new_root

    def _safe_copy_element_with_namespaces(self, element: ET.Element, nsmap: dict[str, str]) -> ET.Element:
        """Copy element preserving namespace context with safe iteration."""
        # Handle tag namespace
        tag = element.tag
        if '}' not in tag and nsmap.get(None):
            tag = f"{{{nsmap[None]}}}{tag}"

        new_element = ET.Element(tag)

        # Copy attributes
        for attr, value in element.attrib.items():
            new_element.set(attr, value)

        # Copy text content
        if element.text:
            new_element.text = element.text
        if element.tail:
            new_element.tail = element.tail

        # Safely copy children using safe iteration
        for child in children(element):
            new_child = self._safe_copy_element_with_namespaces(child, nsmap)
            new_element.append(new_child)

        return new_element

    def _safe_add_missing_attributes(self, svg_root: ET.Element, changes: dict[str, Any]) -> ET.Element:
        """Add missing required SVG attributes with safe processing."""
        added_attrs = []

        try:
            # Ensure SVG has version
            if 'version' not in svg_root.attrib:
                svg_root.set('version', '1.1')
                added_attrs.append('version')

            # Ensure SVG has xmlns if missing in attributes
            if 'xmlns' not in svg_root.attrib:
                svg_ns = 'http://www.w3.org/2000/svg'
                if svg_ns not in (svg_root.nsmap or {}).values():
                    svg_root.set('xmlns', svg_ns)
                    added_attrs.append('xmlns')

            changes['attributes_added'] = added_attrs

        except Exception as e:
            self.logger.warning(f"Adding missing attributes failed: {e}")

        return svg_root

    def _safe_normalize_whitespace(self, svg_root: ET.Element, changes: dict[str, Any]):
        """Normalize whitespace with safe element iteration."""
        try:
            whitespace_normalized = False

            # Use safe iteration over all elements
            for element in self._safe_iter_all_elements(svg_root):
                # Normalize text content whitespace
                if element.text and element.text.strip() != element.text:
                    element.text = element.text.strip() if element.text.strip() else None
                    whitespace_normalized = True

                if element.tail and element.tail.strip() != element.tail:
                    element.tail = element.tail.strip() if element.tail.strip() else None
                    whitespace_normalized = True

            changes['whitespace_normalized'] = whitespace_normalized

        except Exception as e:
            self.logger.warning(f"Whitespace normalization failed: {e}")

    def _safe_fix_structure_issues(self, svg_root: ET.Element, changes: dict[str, Any]):
        """Fix structural issues with safe element iteration."""
        fixes = []

        try:
            # Find empty containers that should be removed
            empty_containers = []
            for element in self._safe_iter_all_elements(svg_root):
                if self._is_empty_container(element):
                    empty_containers.append(element)

            # Remove empty containers
            for element in empty_containers:
                parent = element.getparent()
                if parent is not None:
                    parent.remove(element)
                    fixes.append(f"removed_empty_{self._get_local_tag(element.tag)}")

            changes['structure_fixes'] = fixes

        except Exception as e:
            self.logger.warning(f"Structure fixes failed: {e}")

    def _safe_iter_all_elements(self, root: ET.Element) -> Iterator[ET.Element]:
        """Safely iterate over all elements in the tree."""
        return walk(root)

    def _is_empty_container(self, element: ET.Element) -> bool:
        """Check if element is an empty container that can be removed."""
        local_tag = self._get_local_tag(element.tag)

        # Only consider removing group-like elements (containers)
        container_tags = {'g', 'defs', 'clipPath', 'mask', 'pattern', 'marker', 'symbol'}
        if local_tag not in container_tags:
            return False  # Don't remove actual shape/content elements

        # Don't remove if it has meaningful attributes
        if self._has_meaningful_attributes(element):
            return False

        # Don't remove if it has text content
        if element.text and element.text.strip():
            return False

        # Don't remove if it has children (use safe iteration to check)
        for _ in children(element):
            return False  # Has at least one child

        # Empty container with no meaningful content
        return True

    def _has_meaningful_attributes(self, element: ET.Element) -> bool:
        """Check if element has attributes that make it meaningful to keep."""
        meaningful_attrs = {
            'id', 'class', 'style', 'transform', 'fill', 'stroke', 'opacity',
            # Geometric attributes for shapes
            'x', 'y', 'width', 'height', 'cx', 'cy', 'r', 'rx', 'ry',
            'd', 'points', 'x1', 'y1', 'x2', 'y2',
            # Text attributes
            'font-size', 'font-family', 'text-anchor',
            # Image attributes
            'href', 'xlink:href',
            # Pattern/gradient attributes
            'patternUnits', 'gradientUnits', 'offset', 'stop-color',
            # Filter attributes
            'in', 'result', 'stdDeviation',
        }

        for attr in element.attrib:
            local_attr = self._get_local_name(attr)
            if local_attr in meaningful_attrs:
                return True
        return False

    def _get_local_tag(self, tag: str) -> str:
        """Extract local tag name from namespaced tag."""
        if '}' in tag:
            return tag.split('}')[1]
        return tag

    def _get_local_name(self, name: str) -> str:
        """Extract local name from namespaced attribute name."""
        if '}' in name:
            return name.split('}')[1]
        return name

    def set_normalization_options(self, **options):
        """Update normalization settings."""
        for key, value in options.items():
            if key in self.settings:
                self.settings[key] = value


def create_safe_normalizer(**options) -> SafeSVGNormalizer:
    """
    Factory function to create a safe SVG normalizer.

    Args:
        **options: Normalization options to override defaults

    Returns:
        SafeSVGNormalizer instance
    """
    normalizer = SafeSVGNormalizer()
    if options:
        normalizer.set_normalization_options(**options)
    return normalizer