#!/usr/bin/env python3
"""
Expand USE Elements Preprocessor

Expands <use> elements by copying referenced content inline.
This eliminates the need for complex reference resolution during conversion.

Features:
- Recursive use expansion
- Transform inheritance
- Circular reference detection
- ID conflict resolution
"""

import logging
from typing import Dict, Set, Optional
from lxml import etree as ET

from .base import BasePreprocessor


class ExpandUsePreprocessor(BasePreprocessor):
    """
    Preprocessor that expands <use> elements inline.

    Replaces <use> references with actual copies of the referenced content,
    applying proper transforms and resolving ID conflicts.
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.id_map: Dict[str, ET.Element] = {}
        self.expanded_uses: Set[str] = set()

    def process(self, svg_root: ET.Element) -> ET.Element:
        """
        Expand all <use> elements in the SVG.

        Args:
            svg_root: SVG root element

        Returns:
            SVG with expanded use elements
        """
        self.logger.debug("Starting USE element expansion")

        # Build ID map for quick lookups
        self._build_id_map(svg_root)

        # Expand use elements recursively
        self._expand_use_elements(svg_root)

        # Clean up unused defs (optional optimization)
        self._cleanup_unused_defs(svg_root)

        self.logger.debug(f"Expanded {len(self.expanded_uses)} use elements")
        return svg_root

    def _build_id_map(self, root: ET.Element) -> None:
        """Build map of ID -> element for reference resolution."""
        self.id_map.clear()

        for element in root.xpath(".//*[@id]"):
            element_id = element.get('id')
            if element_id:
                self.id_map[element_id] = element

        self.logger.debug(f"Built ID map with {len(self.id_map)} entries")

    def _expand_use_elements(self, element: ET.Element) -> None:
        """Recursively expand use elements."""
        # Process children first (bottom-up to handle nested uses)
        for child in list(element):
            self._expand_use_elements(child)

        # Find and expand use elements
        use_elements = element.xpath(".//svg:use",
                                   namespaces={'svg': 'http://www.w3.org/2000/svg'})

        for use_elem in use_elements:
            self._expand_single_use(use_elem)

    def _expand_single_use(self, use_elem: ET.Element) -> None:
        """Expand a single use element."""
        href = self._get_href(use_elem)
        if not href or not href.startswith('#'):
            self.logger.warning(f"Invalid or external href in use element: {href}")
            return

        ref_id = href[1:]  # Remove '#' prefix

        # Check for circular references
        if ref_id in self.expanded_uses:
            self.logger.warning(f"Circular reference detected for ID: {ref_id}")
            return

        # Find referenced element
        ref_element = self.id_map.get(ref_id)
        if ref_element is None:
            self.logger.warning(f"Referenced element not found: {ref_id}")
            return

        try:
            self.expanded_uses.add(ref_id)

            # Create expanded content
            expanded = self._create_expanded_element(use_elem, ref_element)

            # Replace use element with expanded content
            parent = use_elem.getparent()
            if parent is not None:
                use_index = list(parent).index(use_elem)
                parent.remove(use_elem)
                parent.insert(use_index, expanded)

            self.logger.debug(f"Expanded use element referencing {ref_id}")

        except Exception as e:
            self.logger.error(f"Failed to expand use element {ref_id}: {e}")

        finally:
            self.expanded_uses.discard(ref_id)

    def _get_href(self, use_elem: ET.Element) -> Optional[str]:
        """Get href attribute from use element (handles both href and xlink:href)."""
        # Try standard href first
        href = use_elem.get('href')
        if href:
            return href

        # Try xlink:href
        href = use_elem.get('{http://www.w3.org/1999/xlink}href')
        return href

    def _create_expanded_element(self, use_elem: ET.Element, ref_element: ET.Element) -> ET.Element:
        """Create expanded element from use and reference."""
        # Create a group to contain the expanded content
        group = ET.Element('{http://www.w3.org/2000/svg}g')

        # Copy use element attributes (except href)
        for attr, value in use_elem.attrib.items():
            if not (attr == 'href' or attr.endswith('href')):
                group.set(attr, value)

        # Build transform for positioning
        transform_parts = []

        # Add translation from use x,y
        x = use_elem.get('x', '0')
        y = use_elem.get('y', '0')
        if x != '0' or y != '0':
            transform_parts.append(f"translate({x},{y})")

        # Add existing transform
        existing_transform = use_elem.get('transform')
        if existing_transform:
            transform_parts.append(existing_transform)

        # Set combined transform
        if transform_parts:
            group.set('transform', ' '.join(transform_parts))

        # Deep copy referenced element
        expanded_content = self._deep_copy_element(ref_element)

        # Resolve ID conflicts
        self._resolve_id_conflicts(expanded_content)

        # Add content to group
        if ref_element.tag.endswith('g'):
            # If referenced element is a group, copy its children
            for child in expanded_content:
                group.append(child)
        else:
            # Single element
            group.append(expanded_content)

        return group

    def _deep_copy_element(self, element: ET.Element) -> ET.Element:
        """Create deep copy of element and all children."""
        # Create new element with same tag and attributes
        copy = ET.Element(element.tag, element.attrib)
        copy.text = element.text
        copy.tail = element.tail

        # Recursively copy children
        for child in element:
            copy.append(self._deep_copy_element(child))

        return copy

    def _resolve_id_conflicts(self, element: ET.Element) -> None:
        """Resolve ID conflicts in expanded content."""
        # Generate unique ID suffix
        import time
        suffix = f"_expanded_{int(time.time() * 1000) % 100000}"

        # Update IDs and references
        self._update_ids_recursive(element, suffix)

    def _update_ids_recursive(self, element: ET.Element, suffix: str) -> None:
        """Recursively update IDs and references."""
        # Update element ID
        if element.get('id'):
            old_id = element.get('id')
            new_id = f"{old_id}{suffix}"
            element.set('id', new_id)

        # Update references to IDs in common attributes
        ref_attrs = ['fill', 'stroke', 'clip-path', 'mask', 'filter']
        for attr in ref_attrs:
            value = element.get(attr)
            if value and value.startswith('url(#'):
                # Extract ID and update reference
                old_ref = value[5:-1]  # Remove 'url(#' and ')'
                new_ref = f"{old_ref}{suffix}"
                element.set(attr, f"url(#{new_ref})")

        # Update href references
        href = self._get_href(element)
        if href and href.startswith('#'):
            old_ref = href[1:]
            new_ref = f"{old_ref}{suffix}"
            # Update both possible href attributes
            if element.get('href'):
                element.set('href', f"#{new_ref}")
            if element.get('{http://www.w3.org/1999/xlink}href'):
                element.set('{http://www.w3.org/1999/xlink}href', f"#{new_ref}")

        # Recursively process children
        for child in element:
            self._update_ids_recursive(child, suffix)

    def _cleanup_unused_defs(self, svg_root: ET.Element) -> None:
        """Remove unused definitions after expansion (optional optimization)."""
        # Find all defs elements
        defs_elements = svg_root.xpath(".//svg:defs",
                                     namespaces={'svg': 'http://www.w3.org/2000/svg'})

        for defs in defs_elements:
            # Find unused children (this is a simplified approach)
            unused_children = []

            for child in defs:
                child_id = child.get('id')
                if child_id and not self._is_referenced(svg_root, child_id):
                    unused_children.append(child)

            # Remove unused definitions
            for unused in unused_children:
                defs.remove(unused)
                self.logger.debug(f"Removed unused definition: {unused.get('id')}")

            # Remove empty defs elements
            if len(defs) == 0:
                parent = defs.getparent()
                if parent is not None:
                    parent.remove(defs)

    def _is_referenced(self, root: ET.Element, ref_id: str) -> bool:
        """Check if an ID is referenced anywhere in the document."""
        # Look for url(#id) references
        xpath_expr = f".//*[contains(@fill, 'url(#{ref_id})') or " \
                     f"contains(@stroke, 'url(#{ref_id})') or " \
                     f"contains(@clip-path, 'url(#{ref_id})') or " \
                     f"contains(@mask, 'url(#{ref_id})') or " \
                     f"contains(@filter, 'url(#{ref_id})')]"

        matches = root.xpath(xpath_expr)
        return len(matches) > 0


def expand_use_elements(svg_root: ET.Element) -> ET.Element:
    """
    Convenience function to expand use elements.

    Args:
        svg_root: SVG root element

    Returns:
        SVG with expanded use elements
    """
    preprocessor = ExpandUsePreprocessor()
    return preprocessor.process(svg_root)