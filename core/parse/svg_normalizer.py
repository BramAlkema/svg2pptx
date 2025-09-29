#!/usr/bin/env python3
"""
SVG Normalizer

Normalizes SVG content for consistent processing by the clean slate pipeline.
Integrates with existing preprocessing patterns from src/preprocessing/.
"""

import logging
from typing import Dict, Any, Tuple, Optional
from lxml import etree as ET
from ..xml.safe_iter import walk, children

logger = logging.getLogger(__name__)


class SVGNormalizer:
    """
    Normalizes SVG content for clean slate processing.

    Applies similar normalizations to the existing preprocessing pipeline
    but focused on core structural issues needed for parsing.
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
            'validate_structure': True
        }

    def normalize(self, svg_root: ET.Element) -> Tuple[ET.Element, Dict[str, Any]]:
        """
        Normalize SVG element tree.

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
            'whitespace_normalized': False
        }

        try:
            # 1. Fix namespace issues
            if self.settings['fix_namespaces']:
                svg_root = self._fix_namespaces(svg_root, changes)

            # 2. Add missing required attributes
            if self.settings['add_missing_attributes']:
                svg_root = self._add_missing_attributes(svg_root, changes)

            # 3. Normalize whitespace in text content
            if self.settings['normalize_whitespace']:
                self._normalize_whitespace(svg_root, changes)

            # 4. Fix common structural issues
            if self.settings['validate_structure']:
                self._fix_structure_issues(svg_root, changes)

            self.logger.debug(f"SVG normalization completed: {changes}")
            return svg_root, changes

        except Exception as e:
            self.logger.error(f"SVG normalization failed: {e}")
            # Return original element with error info
            changes['error'] = str(e)
            return svg_root, changes

    def _fix_namespaces(self, svg_root: ET.Element, changes: Dict[str, Any]) -> ET.Element:
        """Fix namespace declarations and prefixes"""
        # Check if SVG namespace is properly declared
        svg_ns = 'http://www.w3.org/2000/svg'
        xlink_ns = 'http://www.w3.org/1999/xlink'

        # Get current namespace map
        nsmap = svg_root.nsmap if hasattr(svg_root, 'nsmap') else {}

        needs_svg_ns = svg_ns not in nsmap.values()
        needs_xlink_ns = xlink_ns not in nsmap.values()

        if needs_svg_ns or needs_xlink_ns:
            # Create new element with proper namespaces
            new_nsmap = dict(nsmap) if nsmap else {}

            if needs_svg_ns:
                new_nsmap[None] = svg_ns  # Default namespace

            if needs_xlink_ns:
                new_nsmap['xlink'] = xlink_ns

            # Rebuild element tree with correct namespaces
            svg_root = self._rebuild_with_namespaces(svg_root, new_nsmap)
            changes['namespaces_fixed'] = True

        return svg_root

    def _rebuild_with_namespaces(self, element: ET.Element, nsmap: Dict[str, str]) -> ET.Element:
        """Rebuild element tree with proper namespace declarations"""
        # Create new root with correct namespaces
        new_root = ET.Element(element.tag, nsmap=nsmap)

        # Copy attributes
        for attr, value in element.attrib.items():
            new_root.set(attr, value)

        # Copy text content
        if element.text:
            new_root.text = element.text
        if element.tail:
            new_root.tail = element.tail

        # Recursively copy children
        for child in element:
            new_child = self._copy_element_with_namespaces(child, nsmap)
            new_root.append(new_child)

        return new_root

    def _copy_element_with_namespaces(self, element: ET.Element, nsmap: Dict[str, str]) -> ET.Element:
        """Copy element preserving namespace context"""
        new_element = ET.Element(element.tag)

        # Copy attributes
        for attr, value in element.attrib.items():
            new_element.set(attr, value)

        # Copy text content
        if element.text:
            new_element.text = element.text
        if element.tail:
            new_element.tail = element.tail

        # Recursively copy children
        for child in element:
            new_child = self._copy_element_with_namespaces(child, nsmap)
            new_element.append(new_child)

        return new_element

    def _add_missing_attributes(self, svg_root: ET.Element, changes: Dict[str, Any]) -> ET.Element:
        """Add missing required SVG attributes"""
        added_attrs = []

        # Add version if missing
        if not svg_root.get('version'):
            svg_root.set('version', '1.1')
            added_attrs.append('version="1.1"')

        # Add basic dimensions if completely missing
        has_width = svg_root.get('width') is not None
        has_height = svg_root.get('height') is not None
        has_viewbox = svg_root.get('viewBox') is not None

        if not (has_width or has_height or has_viewbox):
            # Add default dimensions
            svg_root.set('width', '100')
            svg_root.set('height', '100')
            svg_root.set('viewBox', '0 0 100 100')
            added_attrs.extend(['width="100"', 'height="100"', 'viewBox="0 0 100 100"'])

        changes['attributes_added'] = added_attrs
        return svg_root

    def _normalize_whitespace(self, svg_root: ET.Element, changes: Dict[str, Any]):
        """Normalize whitespace in text elements while preserving meaningful spaces"""
        text_elements = []

        for element in walk(svg_root):
            tag = self._get_local_tag(element.tag)
            if tag in ['text', 'tspan', 'title', 'desc']:
                text_elements.append(element)

        if text_elements:
            for element in text_elements:
                if element.text:
                    # Normalize whitespace but preserve single spaces
                    normalized = ' '.join(element.text.split())
                    if normalized != element.text:
                        element.text = normalized

            changes['whitespace_normalized'] = len(text_elements) > 0

    def _fix_structure_issues(self, svg_root: ET.Element, changes: Dict[str, Any]):
        """Fix common SVG structure issues"""
        fixes = []

        # Remove empty container elements (except defs, which can be legitimately empty)
        empty_containers = []
        for element in walk(svg_root):
            tag = self._get_local_tag(element.tag)
            if tag in ['g', 'svg'] and tag != 'defs':
                # Check if element has no children and no meaningful attributes
                if (len(element) == 0 and
                    not element.text and
                    not element.tail and
                    not self._has_meaningful_attributes(element)):
                    empty_containers.append(element)

        # Remove empty containers
        for element in empty_containers:
            parent = element.getparent()
            if parent is not None:
                parent.remove(element)
                fixes.append(f'removed_empty_{self._get_local_tag(element.tag)}')

        # Fix invalid nesting (basic checks)
        self._fix_invalid_nesting(svg_root, fixes)

        changes['structure_fixes'] = fixes

    def _has_meaningful_attributes(self, element: ET.Element) -> bool:
        """Check if element has attributes that affect rendering"""
        meaningful_attrs = {
            'transform', 'style', 'class', 'id',
            'fill', 'stroke', 'opacity',
            'clip-path', 'mask', 'filter'
        }

        for attr in element.attrib:
            local_attr = self._get_local_name(attr)
            if local_attr in meaningful_attrs:
                return True

        return False

    def _fix_invalid_nesting(self, svg_root: ET.Element, fixes: list):
        """Fix common invalid nesting issues"""
        # This is a simplified version - full implementation would handle
        # more complex SVG structure validation rules

        for element in list(walk(svg_root)):
            tag = self._get_local_tag(element.tag)

            # Move misplaced text elements
            if tag == 'text':
                parent = element.getparent()
                if parent is not None:
                    parent_tag = self._get_local_tag(parent.tag)
                    # Text shouldn't be direct child of certain elements
                    if parent_tag in ['defs', 'clipPath', 'mask']:
                        # This would need more sophisticated repositioning logic
                        # For now, just note the issue
                        fixes.append(f'text_in_{parent_tag}_detected')

    def _get_local_tag(self, tag: str) -> str:
        """Extract local tag name from namespaced tag"""
        if '}' in tag:
            return tag.split('}')[1]
        return tag

    def _get_local_name(self, name: str) -> str:
        """Extract local name from namespaced attribute name"""
        if '}' in name:
            return name.split('}')[1]
        return name

    def set_normalization_options(self, **options):
        """Update normalization settings"""
        for key, value in options.items():
            if key in self.settings:
                self.settings[key] = value
            else:
                self.logger.warning(f"Unknown normalization option: {key}")


def create_normalizer(**options) -> SVGNormalizer:
    """Factory function to create SVGNormalizer with custom options"""
    normalizer = SVGNormalizer()
    if options:
        normalizer.set_normalization_options(**options)
    return normalizer