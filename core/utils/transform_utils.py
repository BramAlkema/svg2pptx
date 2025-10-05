#!/usr/bin/env python3
"""
Transform Utilities for Safe SVG Processing

Provides safe access to SVG transform attributes and parsing,
preventing cython crashes and handling malformed data gracefully.
"""

from typing import Optional

from lxml import etree as ET


def get_transform_safe(element: ET.Element) -> str | None:
    """
    Safely get transform attribute from element.

    Args:
        element: SVG element that may have transform attribute

    Returns:
        Transform string if present and valid, None otherwise
    """
    if element is None:
        return None

    try:
        transform = element.get('transform')
        if transform is None:
            return None

        # Check for empty or whitespace-only strings
        transform = transform.strip()
        if not transform:
            return None

        return transform
    except (AttributeError, TypeError):
        # Handle cases where element.get() fails
        return None


def has_transform_safe(element: ET.Element) -> bool:
    """
    Safely check if element has a transform attribute.

    Args:
        element: SVG element to check

    Returns:
        True if element has non-empty transform attribute
    """
    return get_transform_safe(element) is not None


def parse_transform_safe(transform_str: str | None) -> str | None:
    """
    Safely parse and validate transform string.

    Args:
        transform_str: Transform string to validate

    Returns:
        Validated transform string or None if invalid
    """
    if not transform_str:
        return None

    try:
        # Basic validation - ensure it contains expected transform functions
        transform_str = transform_str.strip()
        if not transform_str:
            return None

        # Check for basic transform function patterns
        valid_patterns = ['translate(', 'scale(', 'rotate(', 'matrix(', 'skewX(', 'skewY(']
        if any(pattern in transform_str for pattern in valid_patterns):
            return transform_str

        # If no recognized patterns, it might be malformed
        return None

    except (AttributeError, TypeError):
        return None


def get_attribute_safe(element: ET.Element, attr_name: str, default: str = '') -> str:
    """
    Safely get any attribute from element with default fallback.

    Args:
        element: SVG element
        attr_name: Attribute name to retrieve
        default: Default value if attribute not present

    Returns:
        Attribute value or default
    """
    if element is None or attr_name is None:
        return default

    try:
        value = element.get(attr_name)
        return value if value is not None else default
    except (AttributeError, TypeError):
        return default


def has_attribute_safe(element: ET.Element, attr_name: str) -> bool:
    """
    Safely check if element has specified attribute.

    Args:
        element: SVG element to check
        attr_name: Attribute name to check for

    Returns:
        True if attribute exists and is not None
    """
    if element is None or attr_name is None:
        return False

    try:
        return element.get(attr_name) is not None
    except (AttributeError, TypeError):
        return False