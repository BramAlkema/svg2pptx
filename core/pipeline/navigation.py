#!/usr/bin/env python3
"""
Navigation System for SVG to PowerPoint Conversion

Provides comprehensive navigation capabilities including:
- External links (HTTP, mailto, tel, file)
- Slide jumps (to specific slide indices)
- Presentation actions (next/prev/first/last/end)
- Same-slide bookmarks (named anchors)
- Custom shows (named presentation segments)

This module replaces and extends the basic HyperlinkSpec with PowerPoint-native
navigation features that properly use relationships vs action URIs.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union, Any, Dict
import re
from urllib.parse import urlparse


class NavKind(Enum):
    """Navigation type enumeration."""
    EXTERNAL = "external"              # http(s), mailto, tel, file
    SLIDE    = "slide"                 # jump to slide index/part
    ACTION   = "action"                # next/prev/first/last/end
    BOOKMARK = "bookmark"              # same-slide anchor (action-URI)
    CUSTOM_SHOW = "custom_show"        # jump to named custom show (action-URI)


class JumpAction(Enum):
    """PowerPoint presentation navigation actions."""
    NEXT       = "nextslide"
    PREVIOUS   = "previousslide"
    FIRST      = "firstslide"
    LAST       = "lastslide"
    ENDSHOW    = "endshow"


@dataclass(frozen=True)
class SlideTarget:
    """Target for slide navigation."""
    index: int                         # 1-based slide index

    def __post_init__(self):
        """Validate slide index."""
        if self.index < 1:
            raise ValueError(f"Slide index must be >= 1, got {self.index}")


@dataclass(frozen=True)
class BookmarkTarget:
    """Target for same-slide bookmark navigation."""
    name: str                          # anchor name within the current slide

    def __post_init__(self):
        """Validate bookmark name."""
        if not self.name or not self.name.strip():
            raise ValueError("Bookmark name cannot be empty")
        if len(self.name) > 255:
            raise ValueError(f"Bookmark name too long: {len(self.name)} chars (max 255)")


@dataclass(frozen=True)
class CustomShowTarget:
    """Target for custom show navigation."""
    name: str                          # custom show name

    def __post_init__(self):
        """Validate custom show name."""
        if not self.name or not self.name.strip():
            raise ValueError("Custom show name cannot be empty")
        if len(self.name) > 255:
            raise ValueError(f"Custom show name too long: {len(self.name)} chars (max 255)")


@dataclass(frozen=True)
class NavigationSpec:
    """
    Comprehensive navigation specification for PowerPoint presentations.

    Supports all PowerPoint navigation types with proper distinction between
    relationship-based links (external, slide jumps) and action-based links
    (navigation actions, bookmarks, custom shows).
    """
    kind: NavKind
    tooltip: Optional[str] = None
    visited: bool = True

    # Navigation targets (exactly one should be set based on kind)
    href: Optional[str] = None                     # for EXTERNAL
    slide: Optional[SlideTarget] = None            # for SLIDE
    action: Optional[JumpAction] = None            # for ACTION
    bookmark: Optional[BookmarkTarget] = None      # for BOOKMARK
    custom_show: Optional[CustomShowTarget] = None # for CUSTOM_SHOW

    def __post_init__(self):
        """Validate navigation specification consistency."""
        # Count non-None targets
        targets = [
            self.href, self.slide, self.action,
            self.bookmark, self.custom_show
        ]
        non_none_targets = [t for t in targets if t is not None]

        if len(non_none_targets) != 1:
            raise ValueError(
                f"Exactly one navigation target must be set, got {len(non_none_targets)}"
            )

        # Validate target matches kind
        if self.kind == NavKind.EXTERNAL and self.href is None:
            raise ValueError("EXTERNAL navigation requires href")
        elif self.kind == NavKind.SLIDE and self.slide is None:
            raise ValueError("SLIDE navigation requires slide target")
        elif self.kind == NavKind.ACTION and self.action is None:
            raise ValueError("ACTION navigation requires action")
        elif self.kind == NavKind.BOOKMARK and self.bookmark is None:
            raise ValueError("BOOKMARK navigation requires bookmark target")
        elif self.kind == NavKind.CUSTOM_SHOW and self.custom_show is None:
            raise ValueError("CUSTOM_SHOW navigation requires custom_show target")

    def is_external_link(self) -> bool:
        """Check if this is an external link requiring relationship."""
        return self.kind == NavKind.EXTERNAL

    def is_slide_jump(self) -> bool:
        """Check if this is a slide jump requiring relationship."""
        return self.kind == NavKind.SLIDE

    def is_action_based(self) -> bool:
        """Check if this uses PowerPoint action URIs."""
        return self.kind in (NavKind.ACTION, NavKind.BOOKMARK, NavKind.CUSTOM_SHOW)

    def requires_relationship(self) -> bool:
        """Check if this navigation type requires a PowerPoint relationship."""
        return self.kind in (NavKind.EXTERNAL, NavKind.SLIDE)

    def get_target_description(self) -> str:
        """Get human-readable description of navigation target."""
        if self.kind == NavKind.EXTERNAL:
            return f"External: {self.href}"
        elif self.kind == NavKind.SLIDE:
            return f"Slide: {self.slide.index}"
        elif self.kind == NavKind.ACTION:
            return f"Action: {self.action.value}"
        elif self.kind == NavKind.BOOKMARK:
            return f"Bookmark: {self.bookmark.name}"
        elif self.kind == NavKind.CUSTOM_SHOW:
            return f"Custom Show: {self.custom_show.name}"
        return "Unknown navigation type"


# Factory Functions for Common Navigation Patterns

def create_external_navigation(href: str, tooltip: Optional[str] = None, visited: bool = True) -> NavigationSpec:
    """
    Create external link navigation.

    Args:
        href: External URL (http, https, mailto, tel, file)
        tooltip: Optional tooltip text
        visited: Whether link should be marked as visited

    Returns:
        NavigationSpec for external navigation

    Raises:
        ValueError: If href is invalid
    """
    if not href or not href.strip():
        raise ValueError("External href cannot be empty")

    # Basic URL validation
    parsed = urlparse(href)
    if not parsed.scheme:
        raise ValueError(f"Invalid URL scheme in href: {href}")

    return NavigationSpec(
        kind=NavKind.EXTERNAL,
        href=href.strip(),
        tooltip=tooltip,
        visited=visited
    )


def create_slide_navigation(slide_index: int, tooltip: Optional[str] = None, visited: bool = True) -> NavigationSpec:
    """
    Create slide jump navigation.

    Args:
        slide_index: 1-based slide index to jump to
        tooltip: Optional tooltip text
        visited: Whether link should be marked as visited

    Returns:
        NavigationSpec for slide navigation
    """
    return NavigationSpec(
        kind=NavKind.SLIDE,
        slide=SlideTarget(index=slide_index),
        tooltip=tooltip,
        visited=visited
    )


def create_action_navigation(action: JumpAction, tooltip: Optional[str] = None, visited: bool = True) -> NavigationSpec:
    """
    Create presentation action navigation.

    Args:
        action: JumpAction to perform
        tooltip: Optional tooltip text
        visited: Whether link should be marked as visited

    Returns:
        NavigationSpec for action navigation
    """
    return NavigationSpec(
        kind=NavKind.ACTION,
        action=action,
        tooltip=tooltip,
        visited=visited
    )


def create_bookmark_navigation(bookmark_name: str, tooltip: Optional[str] = None, visited: bool = True) -> NavigationSpec:
    """
    Create same-slide bookmark navigation.

    Args:
        bookmark_name: Name of bookmark anchor within current slide
        tooltip: Optional tooltip text
        visited: Whether link should be marked as visited

    Returns:
        NavigationSpec for bookmark navigation
    """
    return NavigationSpec(
        kind=NavKind.BOOKMARK,
        bookmark=BookmarkTarget(name=bookmark_name.strip()),
        tooltip=tooltip,
        visited=visited
    )


def create_custom_show_navigation(show_name: str, tooltip: Optional[str] = None, visited: bool = True) -> NavigationSpec:
    """
    Create custom show navigation.

    Args:
        show_name: Name of custom show to jump to
        tooltip: Optional tooltip text
        visited: Whether link should be marked as visited

    Returns:
        NavigationSpec for custom show navigation
    """
    return NavigationSpec(
        kind=NavKind.CUSTOM_SHOW,
        custom_show=CustomShowTarget(name=show_name.strip()),
        tooltip=tooltip,
        visited=visited
    )


# Backward Compatibility and Migration

def navigation_from_hyperlink_spec(hyperlink_spec) -> NavigationSpec:
    """
    Convert existing HyperlinkSpec to NavigationSpec for backward compatibility.

    Args:
        hyperlink_spec: Existing HyperlinkSpec instance

    Returns:
        Equivalent NavigationSpec

    Raises:
        ValueError: If hyperlink_spec cannot be converted
    """
    from .hyperlinks import HyperlinkSpec  # Avoid circular import

    if not isinstance(hyperlink_spec, HyperlinkSpec):
        raise ValueError(f"Expected HyperlinkSpec, got {type(hyperlink_spec)}")

    href = hyperlink_spec.href
    tooltip = hyperlink_spec.tooltip
    visited = getattr(hyperlink_spec, 'visited', True)

    # Check for internal slide link patterns
    if href and href.startswith('slide:'):
        try:
            slide_num = int(href[6:])  # Remove 'slide:' prefix
            return create_slide_navigation(slide_num, tooltip, visited)
        except ValueError:
            pass  # Fall through to external link

    # Treat as external link
    return create_external_navigation(href, tooltip, visited)


def parse_svg_navigation(href: Optional[str], element_attrs: Dict[str, str], tooltip: Optional[str] = None) -> Optional[NavigationSpec]:
    """
    Parse SVG element attributes to create NavigationSpec.

    Args:
        href: Value of href or xlink:href attribute
        element_attrs: Dictionary of element attributes (data-* attributes)
        tooltip: Optional tooltip from title element

    Returns:
        NavigationSpec if navigation attributes found, None otherwise
    """
    # Check for PowerPoint-specific navigation attributes (in priority order)
    # data-slide takes highest priority
    if 'data-slide' in element_attrs:
        try:
            slide_index = int(element_attrs['data-slide'])
            return create_slide_navigation(slide_index, tooltip)
        except ValueError:
            pass  # Invalid slide index, continue to next

    # data-jump takes second priority
    if 'data-jump' in element_attrs:
        jump_action_value = element_attrs['data-jump'].lower()
        # Find matching action by value
        for action in JumpAction:
            if action.value == jump_action_value:
                return create_action_navigation(action, tooltip)
        # If no exact match, try partial match for convenience
        for action in JumpAction:
            if jump_action_value in action.value or action.value in jump_action_value:
                return create_action_navigation(action, tooltip)

    # data-bookmark takes third priority
    if 'data-bookmark' in element_attrs:
        bookmark_name = element_attrs['data-bookmark'].strip()
        if bookmark_name:
            return create_bookmark_navigation(bookmark_name, tooltip)

    # data-custom-show takes fourth priority
    if 'data-custom-show' in element_attrs:
        show_name = element_attrs['data-custom-show'].strip()
        if show_name:
            return create_custom_show_navigation(show_name, tooltip)

    # Fall back to href-based navigation
    if href and href.strip():
        href = href.strip()

        # Check for internal slide reference patterns
        if href.startswith('slide:'):
            try:
                slide_num = int(href[6:])  # Remove 'slide:' prefix
                if slide_num >= 1:  # Validate slide number
                    return create_slide_navigation(slide_num, tooltip)
                else:
                    return None  # Invalid slide index (0 or negative)
            except ValueError:
                return None  # Invalid slide reference format

        # Check for bookmark reference patterns
        if href.startswith('#'):
            bookmark_name = href[1:].strip()
            if bookmark_name:
                return create_bookmark_navigation(bookmark_name, tooltip)

        # Treat as external link
        try:
            return create_external_navigation(href, tooltip)
        except ValueError:
            pass  # Invalid external URL

    return None  # No valid navigation found


# Validation Utilities

def validate_navigation_spec(nav_spec: NavigationSpec) -> bool:
    """
    Validate NavigationSpec for PowerPoint compatibility.

    Args:
        nav_spec: NavigationSpec to validate

    Returns:
        True if valid for PowerPoint, False otherwise
    """
    try:
        # Basic structure validation
        if not isinstance(nav_spec, NavigationSpec):
            return False

        # Kind-specific validation
        if nav_spec.kind == NavKind.EXTERNAL:
            if not nav_spec.href:
                return False
            # Check URL format
            parsed = urlparse(nav_spec.href)
            return bool(parsed.scheme)

        elif nav_spec.kind == NavKind.SLIDE:
            return nav_spec.slide is not None and nav_spec.slide.index >= 1

        elif nav_spec.kind == NavKind.ACTION:
            return nav_spec.action is not None

        elif nav_spec.kind == NavKind.BOOKMARK:
            return nav_spec.bookmark is not None and bool(nav_spec.bookmark.name.strip())

        elif nav_spec.kind == NavKind.CUSTOM_SHOW:
            return nav_spec.custom_show is not None and bool(nav_spec.custom_show.name.strip())

        return False

    except Exception:
        return False


def get_navigation_summary(nav_specs: list[NavigationSpec]) -> Dict[str, Any]:
    """
    Get summary statistics for a list of navigation specifications.

    Args:
        nav_specs: List of NavigationSpec instances

    Returns:
        Dictionary with navigation statistics
    """
    if not nav_specs:
        return {
            'total': 0,
            'by_kind': {},
            'requires_relationships': 0,
            'uses_action_uris': 0,
            'has_tooltips': 0
        }

    by_kind = {}
    requires_relationships = 0
    uses_action_uris = 0
    has_tooltips = 0

    for nav in nav_specs:
        # Count by kind
        kind_name = nav.kind.value
        by_kind[kind_name] = by_kind.get(kind_name, 0) + 1

        # Count mechanism types
        if nav.requires_relationship():
            requires_relationships += 1
        if nav.is_action_based():
            uses_action_uris += 1
        if nav.tooltip:
            has_tooltips += 1

    return {
        'total': len(nav_specs),
        'by_kind': by_kind,
        'requires_relationships': requires_relationships,
        'uses_action_uris': uses_action_uris,
        'has_tooltips': has_tooltips
    }