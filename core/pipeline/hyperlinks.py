#!/usr/bin/env python3
"""
Hyperlink Specification for SVG to PowerPoint Conversion

This module provides the core data structures for representing hyperlinks
that will be converted from SVG <a> elements to PowerPoint interactive links.

⚠️ DEPRECATION NOTICE: This module is maintained for backward compatibility.
   New code should use NavigationSpec from core.pipeline.navigation for
   enhanced PowerPoint navigation features including slide jumps, actions,
   bookmarks, and custom shows.

Supports:
- External hyperlinks (http, https, mailto, tel, file)
- Internal slide navigation (#slide-N, slide:N)
- Tooltips from SVG <title> elements
- Visited state tracking
"""

import re
from dataclasses import dataclass
from typing import Optional, Union
from enum import Enum


class HyperlinkType(Enum):
    """Types of hyperlinks supported in PowerPoint conversion."""
    EXTERNAL_HTTP = "external_http"     # http:// or https://
    EXTERNAL_MAILTO = "external_mailto" # mailto:
    EXTERNAL_TEL = "external_tel"       # tel:
    EXTERNAL_FILE = "external_file"     # file://
    INTERNAL_SLIDE = "internal_slide"   # #slide-N or slide:N
    UNKNOWN = "unknown"                 # Fallback for unrecognized formats


@dataclass
class HyperlinkSpec:
    """
    Specification for a hyperlink to be embedded in PowerPoint.

    This class represents a hyperlink that can be attached to PowerPoint
    shapes or text runs, converted from SVG <a> elements.

    Attributes:
        href: The hyperlink target URL or slide reference
        tooltip: Optional tooltip text (from SVG <title> elements)
        visited: Whether to mark the link as visited (affects styling)

    Examples:
        # External web link
        HyperlinkSpec(href="https://example.com", tooltip="Visit our website")

        # Email link
        HyperlinkSpec(href="mailto:contact@example.com")

        # Phone link
        HyperlinkSpec(href="tel:+1-555-0123", tooltip="Call us")

        # Internal slide navigation
        HyperlinkSpec(href="slide:3", tooltip="Go to slide 3")
        HyperlinkSpec(href="#slide-5")

        # File link
        HyperlinkSpec(href="file:///path/to/document.pdf")
    """

    href: str                        # "https://…", "mailto:…", "tel:…", "#slide-3", "slide:3"
    tooltip: Optional[str] = None    # from <a><title>…</title> if present
    visited: bool = True             # track visited color/history (PowerPoint default)

    def __post_init__(self):
        """Validate the hyperlink specification after initialization."""
        if not self.href:
            raise ValueError("href cannot be empty")

        # Normalize href for consistency
        self.href = self.href.strip()

        # Check if href is empty after stripping
        if not self.href:
            raise ValueError("href cannot be empty")

        # Validate href format
        link_type = self.get_link_type()
        if link_type == HyperlinkType.UNKNOWN:
            # Allow unknown types but warn
            pass  # Could add logging here if needed

        # Normalize tooltip
        if self.tooltip is not None:
            self.tooltip = self.tooltip.strip()
            if not self.tooltip:
                self.tooltip = None

    def get_link_type(self) -> HyperlinkType:
        """
        Determine the type of hyperlink based on the href.

        Returns:
            HyperlinkType enum value indicating the link category
        """
        href_lower = self.href.lower()

        if href_lower.startswith(('http://', 'https://')):
            return HyperlinkType.EXTERNAL_HTTP
        elif href_lower.startswith('mailto:'):
            return HyperlinkType.EXTERNAL_MAILTO
        elif href_lower.startswith('tel:'):
            return HyperlinkType.EXTERNAL_TEL
        elif href_lower.startswith('file://'):
            return HyperlinkType.EXTERNAL_FILE
        elif (href_lower.startswith('#slide-') or
              href_lower.startswith('slide:') or
              self._is_slide_reference(self.href)):
            return HyperlinkType.INTERNAL_SLIDE
        else:
            return HyperlinkType.UNKNOWN

    def is_external_link(self) -> bool:
        """
        Check if this is an external hyperlink (not internal slide navigation).

        Returns:
            True if the link points to an external resource
        """
        link_type = self.get_link_type()
        return link_type in {
            HyperlinkType.EXTERNAL_HTTP,
            HyperlinkType.EXTERNAL_MAILTO,
            HyperlinkType.EXTERNAL_TEL,
            HyperlinkType.EXTERNAL_FILE
        }

    def is_internal_slide_link(self) -> bool:
        """
        Check if this is an internal slide navigation link.

        Returns:
            True if the link navigates to another slide in the presentation
        """
        return self.get_link_type() == HyperlinkType.INTERNAL_SLIDE

    def get_slide_number(self) -> Optional[int]:
        """
        Extract slide number from internal slide links.

        Returns:
            Slide number (1-based) if this is an internal slide link, None otherwise

        Examples:
            "slide:3" -> 3
            "#slide-5" -> 5
            "https://example.com" -> None
        """
        if not self.is_internal_slide_link():
            return None

        href_lower = self.href.lower()

        # Handle "slide:N" format (case insensitive)
        if href_lower.startswith('slide:'):
            try:
                return int(self.href[6:])  # Skip "slide:"
            except ValueError:
                return None

        # Handle "#slide-N" format (case insensitive)
        if href_lower.startswith('#slide-'):
            try:
                return int(self.href[7:])  # Skip "#slide-"
            except ValueError:
                return None

        return None

    def get_powerpoint_target(self) -> str:
        """
        Get the target path/URL for PowerPoint relationship.

        Returns:
            Target string appropriate for PowerPoint relationship XML

        Examples:
            "https://example.com" -> "https://example.com"
            "slide:3" -> "../slides/slide3.xml"
            "#slide-5" -> "../slides/slide5.xml"
        """
        if self.is_internal_slide_link():
            slide_num = self.get_slide_number()
            if slide_num is not None:
                return f"../slides/slide{slide_num}.xml"
            else:
                # Fallback for malformed slide references
                return "../slides/slide1.xml"
        else:
            # External links use href as-is
            return self.href

    def get_relationship_type(self) -> str:
        """
        Get the OpenXML relationship type for this hyperlink.

        Returns:
            Relationship type URI for PowerPoint XML
        """
        if self.is_internal_slide_link():
            return "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
        else:
            return "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"

    def is_external_for_relationship(self) -> bool:
        """
        Determine if this link should be marked as external in relationship XML.

        Returns:
            True if the relationship should have TargetMode="External"
        """
        # Internal slide links are not external relationships
        return not self.is_internal_slide_link()

    def _is_slide_reference(self, href: str) -> bool:
        """
        Check if href looks like a slide reference using regex.

        Handles edge cases and variations in slide reference formats.
        """
        # Pattern for #slide-N or slide:N where N is a positive integer
        slide_pattern = re.compile(r'^(#slide-\d+|slide:\d+)$', re.IGNORECASE)
        return bool(slide_pattern.match(href))

    def validate(self) -> bool:
        """
        Perform comprehensive validation of the hyperlink specification.

        Returns:
            True if the hyperlink is valid and can be processed

        Raises:
            ValueError: If the hyperlink specification is invalid
        """
        if not self.href:
            raise ValueError("Hyperlink href cannot be empty")

        link_type = self.get_link_type()

        # Validate internal slide links
        if link_type == HyperlinkType.INTERNAL_SLIDE:
            slide_num = self.get_slide_number()
            if slide_num is None or slide_num < 1:
                raise ValueError(f"Invalid slide reference: {self.href}")

        # Validate external HTTP links
        elif link_type == HyperlinkType.EXTERNAL_HTTP:
            if not (self.href.startswith('http://') or self.href.startswith('https://')):
                raise ValueError(f"Invalid HTTP URL: {self.href}")

        # Validate mailto links
        elif link_type == HyperlinkType.EXTERNAL_MAILTO:
            if not self.href.startswith('mailto:') or len(self.href) <= 7:
                raise ValueError(f"Invalid mailto URL: {self.href}")

        # Validate tel links
        elif link_type == HyperlinkType.EXTERNAL_TEL:
            if not self.href.startswith('tel:') or len(self.href) <= 4:
                raise ValueError(f"Invalid tel URL: {self.href}")

        return True

    def __str__(self) -> str:
        """String representation for debugging."""
        tooltip_str = f", tooltip='{self.tooltip}'" if self.tooltip else ""
        return f"HyperlinkSpec(href='{self.href}'{tooltip_str}, visited={self.visited})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"HyperlinkSpec(href='{self.href}', tooltip={self.tooltip!r}, "
                f"visited={self.visited}, type={self.get_link_type().value})")


def create_hyperlink_spec(href: str, tooltip: Optional[str] = None,
                         visited: bool = True) -> HyperlinkSpec:
    """
    Factory function to create and validate a HyperlinkSpec.

    Args:
        href: The hyperlink target URL or slide reference
        tooltip: Optional tooltip text
        visited: Whether to mark as visited (default True)

    Returns:
        Validated HyperlinkSpec instance

    Raises:
        ValueError: If the hyperlink specification is invalid
    """
    spec = HyperlinkSpec(href=href, tooltip=tooltip, visited=visited)
    spec.validate()
    return spec


def parse_svg_href(href_attr: str, title_text: Optional[str] = None) -> Optional[HyperlinkSpec]:
    """
    Parse href attribute from SVG <a> element into HyperlinkSpec.

    Args:
        href_attr: Value of href or xlink:href attribute
        title_text: Text content from nested <title> element

    Returns:
        HyperlinkSpec if href is valid, None if href is empty/invalid
    """
    if not href_attr or not href_attr.strip():
        return None

    try:
        return create_hyperlink_spec(
            href=href_attr.strip(),
            tooltip=title_text.strip() if title_text else None,
            visited=True  # Default to visited for SVG links
        )
    except ValueError:
        # Invalid href format - return None to skip this link
        return None


# Backward Compatibility Functions

def to_navigation_spec(hyperlink_spec: HyperlinkSpec):
    """
    Convert HyperlinkSpec to NavigationSpec for enhanced navigation features.

    Args:
        hyperlink_spec: HyperlinkSpec to convert

    Returns:
        NavigationSpec with equivalent functionality

    Note:
        This function provides a migration path to the enhanced navigation system.
        New code should use NavigationSpec directly.
    """
    # Import here to avoid circular dependency
    from .navigation import navigation_from_hyperlink_spec
    return navigation_from_hyperlink_spec(hyperlink_spec)