#!/usr/bin/env python3

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

pytest.importorskip("tinycss2")

from core.pipeline.navigation import NavigationKind
from core.parse.parser import SVGParser
from core.ir import Rectangle, TextFrame, RichTextFrame


def _parse(svg: str):
    parser = SVGParser(enable_normalization=False)
    scene, result = parser.parse_to_ir(svg)
    assert result.success, result.error
    return scene


def test_navigation_attached_to_ir_elements():
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg">
      <a href="https://example.com" data-visited="false">
        <rect id="linkRect" x="0" y="0" width="10" height="5" />
      </a>
    </svg>
    """

    scene = _parse(svg)
    rect = next(elem for elem in scene if isinstance(elem, Rectangle))

    navigation = getattr(rect, "navigation", None)
    assert navigation is not None
    assert navigation.kind == NavigationKind.EXTERNAL
    assert navigation.href == "https://example.com"
    assert navigation.visited is False
    assert rect.source_id == "linkRect"


def test_inline_text_navigation_emits_run_metadata():
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg">
      <text id="navText">
        Regular
        <a href="https://example.com" data-visited="true">Website</a>
        <tspan> middle </tspan>
        <a data-slide="2" data-visited="false">Slide</a>
      </text>
    </svg>
    """

    scene = _parse(svg)
    text_element = next(
        elem for elem in scene if isinstance(elem, (TextFrame, RichTextFrame))
    )

    if isinstance(text_element, RichTextFrame):
        runs = text_element.to_text_frame().runs
    else:
        runs = text_element.runs

    assert runs[0].text.startswith("Regular")
    assert runs[0].navigation is None

    assert runs[1].text == "Website"
    assert runs[1].navigation and runs[1].navigation.kind == NavigationKind.EXTERNAL

    assert runs[2].text.strip() == "middle"
    assert runs[2].navigation is None

    assert runs[3].text == "Slide"
    assert runs[3].navigation
    assert runs[3].navigation.kind == NavigationKind.SLIDE
    assert runs[3].navigation.slide.index == 2
    assert runs[3].navigation.visited is False
