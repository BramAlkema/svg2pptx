#!/usr/bin/env python3
"""
Navigation specification utilities.

Provides a structured representation for all hyperlink/navigation behaviours
produced during SVG parsing and consumed by downstream mappers/embedders.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class NavigationKind(Enum):
    """Navigation target categories."""

    EXTERNAL = "external"
    SLIDE = "slide"
    ACTION = "action"
    BOOKMARK = "bookmark"
    CUSTOM_SHOW = "custom_show"


class NavigationAction(Enum):
    """Built-in presentation jump actions."""

    NEXT = "nextslide"
    PREVIOUS = "previousslide"
    FIRST = "firstslide"
    LAST = "lastslide"
    ENDSHOW = "endshow"


@dataclass(frozen=True)
class SlideTarget:
    """Reference to another slide in the deck."""

    index: int


@dataclass(frozen=True)
class BookmarkTarget:
    """Named anchor within the current slide."""

    name: str


@dataclass(frozen=True)
class CustomShowTarget:
    """Named custom show to launch."""

    name: str


@dataclass
class NavigationSpec:
    """Structured navigation definition."""

    kind: NavigationKind
    tooltip: Optional[str] = None
    visited: bool = True

    href: Optional[str] = None
    slide: Optional[SlideTarget] = None
    action: Optional[NavigationAction] = None
    bookmark: Optional[BookmarkTarget] = None
    custom_show: Optional[CustomShowTarget] = None

    def __post_init__(self) -> None:
        """Validate that the navigation fields align with the kind."""
        fields = {
            NavigationKind.EXTERNAL: bool(self.href),
            NavigationKind.SLIDE: bool(self.slide),
            NavigationKind.ACTION: bool(self.action),
            NavigationKind.BOOKMARK: bool(self.bookmark),
            NavigationKind.CUSTOM_SHOW: bool(self.custom_show),
        }
        if not fields.get(self.kind, False):
            raise ValueError(f"NavigationSpec kind '{self.kind.value}' requires matching target data")

    def get_target_description(self) -> str:
        """Human-readable target description for logging."""
        if self.kind == NavigationKind.EXTERNAL and self.href:
            return f"external:{self.href}"
        if self.kind == NavigationKind.SLIDE and self.slide:
            return f"slide:{self.slide.index}"
        if self.kind == NavigationKind.ACTION and self.action:
            return f"action:{self.action.value}"
        if self.kind == NavigationKind.BOOKMARK and self.bookmark:
            return f"bookmark:{self.bookmark.name}"
        if self.kind == NavigationKind.CUSTOM_SHOW and self.custom_show:
            return f"custom_show:{self.custom_show.name}"
        return self.kind.value

    def as_dict(self) -> Dict[str, object]:
        """Return a serialisable representation of the navigation spec."""
        payload: Dict[str, object] = {
            "kind": self.kind.value,
            "tooltip": self.tooltip,
            "visited": self.visited,
        }
        if self.href:
            payload["href"] = self.href
        if self.slide:
            payload["slide"] = {"index": self.slide.index}
        if self.action:
            payload["action"] = self.action.value
        if self.bookmark:
            payload["bookmark"] = {"name": self.bookmark.name}
        if self.custom_show:
            payload["custom_show"] = {"name": self.custom_show.name}
        return payload


def parse_svg_navigation(
    href: Optional[str],
    attrs: Dict[str, str],
    tooltip: Optional[str] = None,
) -> Optional[NavigationSpec]:
    """
    Parse SVG navigation attributes into a NavigationSpec.

    Supported attributes:
        - data-slide="N"
        - data-jump="next|previous|first|last|endshow"
        - data-bookmark="anchor"
        - data-custom-show="name"
        - data-visited="true|false"
        - href / xlink:href (external or bookmark)
    """
    visited = _coerce_bool(attrs.get("data-visited"), default=True)

    slide_attr = attrs.get("data-slide")
    if slide_attr:
        index = _parse_positive_int(slide_attr, "data-slide")
        return NavigationSpec(
            kind=NavigationKind.SLIDE,
            slide=SlideTarget(index=index),
            tooltip=tooltip,
            visited=visited,
        )

    jump_attr = attrs.get("data-jump")
    if jump_attr:
        action = _parse_jump_action(jump_attr)
        return NavigationSpec(
            kind=NavigationKind.ACTION,
            action=action,
            tooltip=tooltip,
            visited=visited,
        )

    bookmark_attr = attrs.get("data-bookmark")
    if bookmark_attr:
        return NavigationSpec(
            kind=NavigationKind.BOOKMARK,
            bookmark=BookmarkTarget(name=bookmark_attr),
            tooltip=tooltip,
            visited=visited,
        )

    custom_show_attr = attrs.get("data-custom-show")
    if custom_show_attr:
        return NavigationSpec(
            kind=NavigationKind.CUSTOM_SHOW,
            custom_show=CustomShowTarget(name=custom_show_attr),
            tooltip=tooltip,
            visited=visited,
        )

    if href:
        trimmed = href.strip()
        if not trimmed:
            return None
        if trimmed.startswith("#"):
            return NavigationSpec(
                kind=NavigationKind.BOOKMARK,
                bookmark=BookmarkTarget(name=trimmed[1:]),
                tooltip=tooltip,
                visited=visited,
            )
        lower_href = trimmed.lower()
        if lower_href.startswith("slide:"):
            index = _parse_positive_int(trimmed.split(":", 1)[1], "href slide")
            return NavigationSpec(
                kind=NavigationKind.SLIDE,
                slide=SlideTarget(index=index),
                tooltip=tooltip,
                visited=visited,
            )
        return NavigationSpec(
            kind=NavigationKind.EXTERNAL,
            href=trimmed,
            tooltip=tooltip,
            visited=visited,
        )

    return None


def build_action_uri(nav: NavigationSpec) -> Optional[str]:
    """Return the PowerPoint action URI for action/bookmark/custom-show targets."""
    if nav.kind == NavigationKind.ACTION and nav.action:
        return f"ppaction://hlinkshowjump?jump={nav.action.value}"
    if nav.kind == NavigationKind.BOOKMARK and nav.bookmark:
        return f"ppaction://hlinkshowjump?bookmark={nav.bookmark.name}"
    if nav.kind == NavigationKind.CUSTOM_SHOW and nav.custom_show:
        return f"ppaction://hlinkshowjump?show={nav.custom_show.name}"
    return None


def _coerce_bool(value: Optional[str], *, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"false", "0", "no"}


def _parse_positive_int(raw: str, field: str) -> int:
    try:
        index = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid integer for {field}: {raw}") from exc
    if index <= 0:
        raise ValueError(f"{field} must be positive, got {index}")
    return index


def _parse_jump_action(value: str) -> NavigationAction:
    lookup = value.strip().replace("-", "").replace("_", "").lower()
    mapping = {
        "next": NavigationAction.NEXT,
        "nextslide": NavigationAction.NEXT,
        "previous": NavigationAction.PREVIOUS,
        "prev": NavigationAction.PREVIOUS,
        "previousslide": NavigationAction.PREVIOUS,
        "first": NavigationAction.FIRST,
        "firstslide": NavigationAction.FIRST,
        "last": NavigationAction.LAST,
        "lastslide": NavigationAction.LAST,
        "end": NavigationAction.ENDSHOW,
        "endshow": NavigationAction.ENDSHOW,
    }
    if lookup not in mapping:
        raise ValueError(f"Unsupported navigation jump action: {value}")
    return mapping[lookup]


__all__ = [
    "NavigationSpec",
    "NavigationKind",
    "NavigationAction",
    "SlideTarget",
    "BookmarkTarget",
    "CustomShowTarget",
    "parse_svg_navigation",
    "build_action_uri",
]
