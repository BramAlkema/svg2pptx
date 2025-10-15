#!/usr/bin/env python3
"""Integration-style unit tests for SVGParser and the sliced helpers."""

from __future__ import annotations

from core.parse import SVGParser


def _find_first(scene, cls_name: str):
    return next((element for element in scene if element.__class__.__name__ == cls_name), None)


def test_parse_to_ir_basic_rect():
    """SVGParser.parse_to_ir should emit native rectangle geometry for simple input."""
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" width="120" height="80">
        <rect x="10" y="20" width="40" height="30" fill="#FF0000"/>
    </svg>
    """

    parser = SVGParser(enable_normalization=False)
    scene, result = parser.parse_to_ir(svg)

    assert result.success, result.error
    assert len(scene) > 0

    rectangle = _find_first(scene, "Rectangle")
    assert rectangle is not None
    assert rectangle.bounds.x == 10
    assert rectangle.bounds.y == 20
    assert rectangle.bounds.width == 40
    assert rectangle.bounds.height == 30


def test_parse_to_ir_collects_clip_paths():
    """ClipPathExtractor wiring should populate ClipRef on converted geometry."""
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
        <defs>
            <clipPath id="clip-rect">
                <rect x="0" y="0" width="50" height="50"/>
            </clipPath>
        </defs>
        <rect x="20" y="20" width="80" height="80" clip-path="url(#clip-rect)" />
    </svg>
    """

    parser = SVGParser(enable_normalization=False)
    scene, result = parser.parse_to_ir(svg)
    assert result.success

    path = _find_first(scene, "Path")
    assert path is not None
    assert getattr(path, "clip", None) is not None
    assert path.clip.clip_id == "url(#clip-rect)"


def test_parse_to_ir_hyperlink_navigation_propagates():
    """HyperlinkProcessor should attach NavigationSpec metadata to converted elements."""
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
        <a data-slide="3" data-visited="false">
            <text x="10" y="40">Go to slide</text>
        </a>
    </svg>
    """

    parser = SVGParser(enable_normalization=False)
    scene, result = parser.parse_to_ir(svg)
    assert result.success

    navigations = []
    for element in scene:
        nav = getattr(element, "navigation", None)
        if nav is not None:
            navigations.append(nav)
        if hasattr(element, "runs"):
            for run in element.runs:
                run_nav = getattr(run, "navigation", None)
                if run_nav is not None:
                    navigations.append(run_nav)
    assert navigations, "Expected navigation metadata on converted elements"
    assert any(nav.slide.index == 3 for nav in navigations)
    assert any(nav.visited is False for nav in navigations)
