from __future__ import annotations

import logging
from dataclasses import dataclass

import pytest
from lxml import etree as ET

from core.ir.geometry import LineSegment, Point, Rect
from core.parse_split.ir_converter import IRConverter
from core.parse_split.models import ClipDefinition
from core.pipeline.navigation import NavigationKind, NavigationSpec


@dataclass
class StubStyleResolver:
    paint_style: dict
    text_style: dict

    def compute_paint_style(self, element, context=None):
        return dict(self.paint_style)

    def compute_text_style(self, element, parent_style=None):
        base = dict(parent_style or {})
        base.update(self.text_style)
        return base


class StubStyleContextBuilder:
    def build(self, _root):
        return {"scope": "stub"}


class StubHyperlinkProcessor:
    def resolve_inline_navigation(self, element):
        return element.attrib.get("data-nav")


class OffsetCoordinateSpace:
    def __init__(self, dx: float = 0.0, dy: float = 0.0):
        self.dx = dx
        self.dy = dy

    def apply_ctm(self, x: float, y: float) -> tuple[float, float]:
        return x + self.dx, y + self.dy


def _build_converter():
    style_resolver = StubStyleResolver(
        paint_style={
            "fill": "FF0000",
            "fill_opacity": 0.9,
            "stroke": "0000FF",
            "stroke_opacity": 0.8,
            "stroke_width_px": 2.5,
            "opacity": 0.75,
        },
        text_style={
            "font_family": "Inter",
            "font_size_pt": 14.0,
            "font_weight": "normal",
            "font_style": "normal",
            "fill": "222222",
            "text_decoration": "none",
        },
    )
    converter = IRConverter(
        style_resolver=style_resolver,
        style_context_builder=StubStyleContextBuilder(),
        hyperlink_processor=StubHyperlinkProcessor(),
        children_iter=list,
        logger=logging.getLogger("tests.ir_converter"),
    )
    converter._style_context = {"scope": "stub"}  # Pre-populate as convert() would
    return converter


def test_convert_path_applies_coordinate_space_and_clip():
    converter = _build_converter()

    clip_segments = (
        LineSegment(start=Point(0, 0), end=Point(1, 0)),
        LineSegment(start=Point(1, 0), end=Point(1, 1)),
    )
    converter._clip_definitions = {
        "clip-1": ClipDefinition(
            clip_id="clip-1",
            segments=clip_segments,
            bounding_box=Rect(0, 0, 1, 1),
            clip_rule="evenodd",
        ),
    }

    element = ET.Element(
        "path",
        attrib={
            "d": "M0 0 l10 0 l0 5 z",
            "clip-path": "#clip-1",
        },
    )

    path = converter.convert_element(
        tag="path",
        element=element,
        coord_space=OffsetCoordinateSpace(dx=5.0, dy=-2.0),
        current_navigation=None,
        traverse_callback=lambda _node, _nav: [],
    )

    assert path is not None, "Expected IR Path output"
    assert len(path.segments) == 3  # move command ignored, closing segment added

    first_segment = path.segments[0]
    assert isinstance(first_segment, LineSegment)
    assert first_segment.start == Point(5.0, -2.0)
    assert first_segment.end == Point(15.0, -2.0)

    closing_segment = path.segments[-1]
    assert closing_segment.end == Point(5.0, -2.0)

    assert path.opacity == pytest.approx(0.75)
    assert path.clip is not None
    assert path.clip.clip_id == "url(#clip-1)"
    assert path.clip.path_segments == clip_segments
    assert path.clip.bounding_box == Rect(0, 0, 1, 1)
    assert path.clip.clip_rule == "evenodd"


def test_convert_text_propagates_navigation_to_runs():
    converter = _build_converter()
    converter._clip_definitions = {}

    element = ET.Element("text", attrib={"x": "10", "y": "20"})
    element.text = "Hello"

    navigation = NavigationSpec(
        kind=NavigationKind.EXTERNAL,
        href="https://example.test",
    )

    text_frame = converter.convert_element(
        tag="text",
        element=element,
        coord_space=OffsetCoordinateSpace(),
        current_navigation=navigation,
        traverse_callback=lambda _node, _nav: [],
    )

    assert text_frame is not None, "Expected TextFrame output"
    assert text_frame.runs, "TextFrame should contain at least one run"

    run = text_frame.runs[0]
    assert run.text == "Hello"
    assert run.navigation is navigation
    assert run.font_family == "Inter"
    assert run.font_size_pt == pytest.approx(14.0)
    assert text_frame.anchor.name == "START"
