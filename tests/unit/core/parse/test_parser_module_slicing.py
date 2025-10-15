#!/usr/bin/env python3
"""Focused regression tests for Phase 1 Task 1.3 parser coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.parse.parser import ClipDefinition, SVGParser


FIXTURE_DIR = Path("testing/fixtures/module_slicing/parser")
SVG_NS = {
    "svg": "http://www.w3.org/2000/svg",
    "xlink": "http://www.w3.org/1999/xlink",
}


def load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_parser_handles_gradients_clip_paths_and_navigation():
    parser = SVGParser()
    svg_content = load_fixture("basic_shapes.svg")

    result = parser.parse(svg_content)

    assert result.success, result.error
    assert result.element_count > 0
    assert result.namespace_count >= 2  # svg + xlink

    svg_root = result.svg_root
    assert svg_root.tag.endswith("svg")

    # Gradient definitions should be preserved
    gradient = svg_root.find(".//svg:linearGradient", namespaces=SVG_NS)
    assert gradient is not None

    # clipPath definitions should be collected into the parse result
    assert "clip" in result.clip_paths
    clip_def = result.clip_paths["clip"]
    assert isinstance(clip_def, ClipDefinition)
    assert clip_def.segments

    # Navigation metadata should remain on hyperlink nodes
    hyperlink = svg_root.find(".//svg:a", namespaces=SVG_NS)
    assert hyperlink is not None
    assert hyperlink.get(f"{{{SVG_NS['xlink']}}}href") == "https://example.com"

    # ForeignObject elements should remain available for fallback handling
    foreign_object = svg_root.find(".//svg:foreignObject", namespaces=SVG_NS)
    assert foreign_object is not None

    # Style context seeds downstream services with viewport dimensions
    style_context = parser.get_style_context()
    assert style_context is not None
    assert style_context.viewport_width == pytest.approx(120.0)
    assert style_context.viewport_height == pytest.approx(90.0)


def test_parser_recovers_from_malformed_gradient_definition():
    parser = SVGParser()
    svg_content = load_fixture("malformed_gradient.svg")

    result = parser.parse(svg_content)

    assert result.success
    svg_root = result.svg_root
    gradient = svg_root.find(".//svg:linearGradient", namespaces=SVG_NS)
    assert gradient is not None
    stop = gradient.find(".//svg:stop", namespaces=SVG_NS)
    assert stop is not None
    # Invalid attribute syntax causes the parser to drop the offset attribute
    assert stop.get("offset") is None


def test_parser_handles_filter_service_failures_gracefully():
    class ExplodingFilterService:
        def __init__(self):
            self.calls = []

        def resolve_effects(self, filter_ref, style_context):
            self.calls.append(filter_ref)
            raise RuntimeError("unsupported filter")

    parser = SVGParser()
    service = ExplodingFilterService()
    parser.filter_service = service

    svg_content = load_fixture("filter_error.svg")
    scene, parse_result = parser.parse_to_ir(svg_content)

    assert parse_result.success
    assert scene  # Rect converts successfully
    assert service.calls == ["url(#unsupportedFilter)"]


def test_parser_rejects_non_svg_content():
    parser = SVGParser()
    result = parser.parse("<html></html>")

    assert not result.success
    assert result.error is not None
    assert "does not appear to be SVG" in result.error
