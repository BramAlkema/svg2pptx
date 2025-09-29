#!/usr/bin/env python3
"""
Resolve Clip Paths Preprocessor

Resolves clipPath references and prepares clipping for boolean operations.
Simplifies complex clipping scenarios for downstream processing.

Features:
- ClipPath reference resolution
- Nested clipping flattening
- Boolean clipping preparation
- Path-based clipping normalization
"""

import logging
from typing import Dict, List, Set, Optional, Tuple
from lxml import etree as ET

from .base import BasePreprocessor


class ResolveClipsPreprocessor(BasePreprocessor):
    """
    Preprocessor that resolves and normalizes clipping paths.

    Converts clipPath references to inline clipping operations
    and prepares for boolean clipping operations.
    """

    def __init__(self, flatten_nested_clips: bool = True):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.flatten_nested_clips = flatten_nested_clips
        self.clippath_defs: Dict[str, ET.Element] = {}
        self.processed_clips: Set[str] = set()

    def process(self, svg_root: ET.Element) -> ET.Element:
        """
        Resolve clip paths in the SVG.

        Args:
            svg_root: SVG root element

        Returns:
            SVG with resolved clip paths
        """
        self.logger.debug("Starting clip path resolution")

        # Build clipPath definitions map
        self._build_clippath_map(svg_root)

        # Resolve clip-path references
        self._resolve_clippath_references(svg_root)

        # Flatten nested clipping if enabled
        if self.flatten_nested_clips:
            self._flatten_nested_clipping(svg_root)

        # Cleanup unused clipPath definitions
        self._cleanup_unused_clippath_defs(svg_root)

        self.logger.debug(f"Resolved {len(self.processed_clips)} clip path references")
        return svg_root

    def _build_clippath_map(self, svg_root: ET.Element) -> None:
        """Build map of clipPath ID -> definition element."""
        self.clippath_defs.clear()

        # Find all clipPath definitions
        clippath_elements = svg_root.xpath(".//svg:clipPath",
                                          namespaces={'svg': 'http://www.w3.org/2000/svg'})

        for clippath in clippath_elements:
            clippath_id = clippath.get('id')
            if clippath_id:
                self.clippath_defs[clippath_id] = clippath

        self.logger.debug(f"Found {len(self.clippath_defs)} clipPath definitions")

    def _resolve_clippath_references(self, element: ET.Element) -> None:
        """Recursively resolve clipPath references."""
        # Check if element has clip-path attribute
        clip_path_attr = element.get('clip-path')
        if clip_path_attr:
            self._resolve_element_clipping(element, clip_path_attr)

        # Process children
        for child in element:
            self._resolve_clippath_references(child)

    def _resolve_element_clipping(self, element: ET.Element, clip_path_attr: str) -> None:
        """Resolve clipping for a single element."""
        # Parse clip-path reference
        clip_id = self._extract_clip_id(clip_path_attr)
        if not clip_id:
            return

        # Find clipPath definition
        clippath_def = self.clippath_defs.get(clip_id)
        if not clippath_def:
            self.logger.warning(f"ClipPath definition not found: {clip_id}")
            return

        try:
            # Create clipping group
            clipping_group = self._create_clipping_group(element, clippath_def)

            # Replace element with clipping group
            parent = element.getparent()
            if parent is not None:
                element_index = list(parent).index(element)
                parent.remove(element)
                parent.insert(element_index, clipping_group)

            self.processed_clips.add(clip_id)
            self.logger.debug(f"Resolved clip-path reference: {clip_id}")

        except Exception as e:
            self.logger.error(f"Failed to resolve clip-path {clip_id}: {e}")

    def _extract_clip_id(self, clip_path_attr: str) -> Optional[str]:
        """Extract clipPath ID from clip-path attribute."""
        # Handle url(#id) format
        if clip_path_attr.startswith('url(#') and clip_path_attr.endswith(')'):
            return clip_path_attr[5:-1]

        # Handle direct #id format
        if clip_path_attr.startswith('#'):
            return clip_path_attr[1:]

        return None

    def _create_clipping_group(self, element: ET.Element, clippath_def: ET.Element) -> ET.Element:
        """Create a group that applies clipping to the element."""
        # Create wrapper group
        clip_group = self.create_svg_element('g')

        # Copy element attributes to group (except clip-path)
        for attr, value in element.attrib.items():
            if attr != 'clip-path':
                clip_group.set(attr, value)

        # Remove clip-path from original element
        if element.get('clip-path'):
            del element.attrib['clip-path']

        # Add clipping metadata for downstream processing
        clip_group.set('data-clip-operation', 'intersect')
        clip_group.set('data-clip-source', clippath_def.get('id', ''))

        # Add clipped element
        clip_group.append(element)

        # Add clipping paths as data
        for clip_child in clippath_def:
            if self.is_svg_element(clip_child, 'path'):
                # Clone clipping path
                clip_path = self._clone_element(clip_child)
                clip_path.set('data-clip-role', 'mask')
                clip_group.append(clip_path)
            elif self.is_svg_element(clip_child, 'use'):
                # Resolve use references in clipPath
                self._resolve_clip_use_reference(clip_group, clip_child)
            else:
                # Other clipping shapes (rect, circle, etc.)
                clip_shape = self._clone_element(clip_child)
                clip_shape.set('data-clip-role', 'mask')
                clip_group.append(clip_shape)

        return clip_group

    def _resolve_clip_use_reference(self, clip_group: ET.Element, use_element: ET.Element) -> None:
        """Resolve use reference within clipPath."""
        href = self._get_href(use_element)
        if not href or not href.startswith('#'):
            return

        ref_id = href[1:]

        # Find referenced element in the document
        svg_root = clip_group.getroottree().getroot()
        ref_element = svg_root.xpath(f".//*[@id='{ref_id}']")

        if ref_element:
            # Clone referenced element as clipping path
            clip_path = self._clone_element(ref_element[0])
            clip_path.set('data-clip-role', 'mask')

            # Apply use element transforms
            use_transform = use_element.get('transform')
            if use_transform:
                existing_transform = clip_path.get('transform', '')
                combined_transform = f"{existing_transform} {use_transform}".strip()
                clip_path.set('transform', combined_transform)

            clip_group.append(clip_path)

    def _flatten_nested_clipping(self, svg_root: ET.Element) -> None:
        """Flatten nested clipping operations."""
        # Find elements with nested clipping (groups with data-clip-operation that contain other clipped elements)
        nested_clip_groups = svg_root.xpath(".//svg:g[@data-clip-operation]//svg:g[@data-clip-operation]",
                                           namespaces={'svg': 'http://www.w3.org/2000/svg'})

        for nested_group in nested_clip_groups:
            try:
                self._flatten_single_nested_clip(nested_group)
            except Exception as e:
                self.logger.warning(f"Failed to flatten nested clipping: {e}")

    def _flatten_single_nested_clip(self, nested_group: ET.Element) -> None:
        """Flatten a single nested clipping operation."""
        # Find parent clipping group
        parent = nested_group.getparent()
        while parent is not None and parent.get('data-clip-operation') is None:
            parent = parent.getparent()

        if parent is None:
            return

        # Combine clipping paths from both levels
        parent_masks = parent.xpath(".//*[@data-clip-role='mask']")
        nested_masks = nested_group.xpath(".//*[@data-clip-role='mask']")

        # Create new combined clipping group
        combined_group = self.create_svg_element('g')
        combined_group.set('data-clip-operation', 'intersect')
        combined_group.set('data-clip-source', f"combined_{self.get_element_id(nested_group)}")

        # Copy content from nested group (excluding masks)
        for child in nested_group:
            if child.get('data-clip-role') != 'mask':
                combined_group.append(self._clone_element(child))

        # Add all masks (parent + nested)
        for mask in parent_masks + nested_masks:
            combined_group.append(self._clone_element(mask))

        # Replace nested group with combined group
        nested_parent = nested_group.getparent()
        if nested_parent is not None:
            nested_index = list(nested_parent).index(nested_group)
            nested_parent.remove(nested_group)
            nested_parent.insert(nested_index, combined_group)

    def _cleanup_unused_clippath_defs(self, svg_root: ET.Element) -> None:
        """Remove unused clipPath definitions."""
        # Find all defs elements
        defs_elements = svg_root.xpath(".//svg:defs",
                                     namespaces={'svg': 'http://www.w3.org/2000/svg'})

        for defs in defs_elements:
            # Remove processed clipPath elements
            clippath_children = defs.xpath(".//svg:clipPath",
                                         namespaces={'svg': 'http://www.w3.org/2000/svg'})

            for clippath in clippath_children:
                clippath_id = clippath.get('id')
                if clippath_id in self.processed_clips:
                    defs.remove(clippath)
                    self.logger.debug(f"Removed processed clipPath definition: {clippath_id}")

            # Remove empty defs elements
            if len(defs) == 0:
                parent = defs.getparent()
                if parent is not None:
                    parent.remove(defs)

    def _get_href(self, element: ET.Element) -> Optional[str]:
        """Get href attribute (handles both href and xlink:href)."""
        href = element.get('href')
        if href:
            return href

        href = element.get('{http://www.w3.org/1999/xlink}href')
        return href

    def _clone_element(self, element: ET.Element) -> ET.Element:
        """Create a deep copy of an element."""
        # Create new element with same tag and attributes
        cloned = ET.Element(element.tag, element.attrib)
        cloned.text = element.text
        cloned.tail = element.tail

        # Recursively clone children
        for child in element:
            cloned.append(self._clone_element(child))

        return cloned


def resolve_clip_paths(svg_root: ET.Element, flatten_nested: bool = True) -> ET.Element:
    """
    Convenience function to resolve clip paths.

    Args:
        svg_root: SVG root element
        flatten_nested: Whether to flatten nested clipping

    Returns:
        SVG with resolved clip paths
    """
    preprocessor = ResolveClipsPreprocessor(flatten_nested)
    return preprocessor.process(svg_root)