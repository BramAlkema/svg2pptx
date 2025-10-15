#!/usr/bin/env python3

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from core.pipeline.navigation import (
    NavigationAction,
    NavigationKind,
    NavigationSpec,
    parse_svg_navigation,
)


def test_parse_external_navigation():
    spec = parse_svg_navigation("https://example.com", {}, tooltip="Visit")
    assert isinstance(spec, NavigationSpec)
    assert spec.kind == NavigationKind.EXTERNAL
    assert spec.href == "https://example.com"
    assert spec.tooltip == "Visit"
    assert spec.visited is True


def test_parse_slide_navigation():
    spec = parse_svg_navigation(None, {"data-slide": "3"}, tooltip=None)
    assert spec.kind == NavigationKind.SLIDE
    assert spec.slide is not None and spec.slide.index == 3


def test_parse_action_navigation():
    spec = parse_svg_navigation(None, {"data-jump": "next"}, tooltip="Next")
    assert spec.kind == NavigationKind.ACTION
    assert spec.action is NavigationAction.NEXT
    assert spec.tooltip == "Next"


def test_parse_bookmark_from_href():
    spec = parse_svg_navigation("#intro", {}, tooltip=None)
    assert spec.kind == NavigationKind.BOOKMARK
    assert spec.bookmark and spec.bookmark.name == "intro"


def test_parse_invalid_slide_value_raises():
    with pytest.raises(ValueError):
        parse_svg_navigation(None, {"data-slide": "zero"}, tooltip=None)
