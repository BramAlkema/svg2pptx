"""
Extended XML utilities built on safe iteration foundation.
"""

from lxml import etree as ET
from typing import Iterator, Optional, Dict, List
from .safe_iter import children, walk


def get_descendants(elem: ET.Element) -> Iterator[ET.Element]:
    """
    Get all descendant elements (excluding the element itself).

    Args:
        elem: Root element

    Yields:
        All descendant elements
    """
    for node in walk(elem):
        if node is not elem:
            yield node


def first_child(elem: ET.Element) -> Optional[ET.Element]:
    """
    Get first child element (ignoring comments/PIs).

    Args:
        elem: Parent element

    Returns:
        First child element or None if no element children
    """
    for child in children(elem):
        return child
    return None


def collect_attributes(root: ET.Element) -> Dict[str, List[str]]:
    """
    Collect all unique attribute names and values from tree.

    Args:
        root: Root element to analyze

    Returns:
        Dict mapping attribute names to lists of unique values
    """
    attributes = {}
    for elem in walk(root):
        for attr_name, attr_value in elem.attrib.items():
            if attr_name not in attributes:
                attributes[attr_name] = []
            if attr_value not in attributes[attr_name]:
                attributes[attr_name].append(attr_value)
    return attributes


def count_by_tag(root: ET.Element) -> Dict[str, int]:
    """
    Count elements by tag name (local name, without namespace).

    Args:
        root: Root element to count from

    Returns:
        Dict mapping tag names to counts
    """
    counts = {}
    for elem in walk(root):
        local_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        counts[local_tag] = counts.get(local_tag, 0) + 1
    return counts


def has_external_references(root: ET.Element) -> bool:
    """
    Check if SVG has external references (images, fonts, etc.).

    Args:
        root: Root SVG element

    Returns:
        True if external references found
    """
    for elem in walk(root):
        # Check for external image references
        href = elem.get('href') or elem.get('{http://www.w3.org/1999/xlink}href')
        if href and (href.startswith('http://') or href.startswith('https://') or href.startswith('file://')):
            return True

        # Check for external font references
        if elem.get('font-family') and 'url(' in str(elem.get('font-family')):
            return True

        # Check for external stylesheets
        if elem.tag.endswith('style') and elem.text:
            style_content = elem.text
            if '@import' in style_content or 'url(' in style_content:
                return True

    return False


def safe_get_text_content(elem: ET.Element) -> str:
    """
    Safely get all text content from element and its descendants.

    Args:
        elem: Element to extract text from

    Returns:
        Combined text content
    """
    text_parts = []

    # Get direct text content
    if elem.text:
        text_parts.append(elem.text)

    # Process child elements
    for child in children(elem):
        if child.text:
            text_parts.append(child.text)
        # Handle tail text after child
        if child.tail:
            text_parts.append(child.tail)

    return ''.join(text_parts).strip()