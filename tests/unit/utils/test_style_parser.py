#!/usr/bin/env python3
from __future__ import annotations

import pytest

from core.utils.style_parser import StyleParser


@pytest.fixture
def parser():
    return StyleParser()


def test_parse_style_string_handles_important(parser):
    style = "fill: #ff0000; stroke-width: 2px !important; invalid"
    result = parser.parse_style_string(style)

    assert "fill" in result.declarations
    assert result.declarations["stroke-width"].priority == "important"
    # Invalid declaration should be ignored without raising
    assert result.parsing_errors == []


def test_parse_style_to_dict_and_get_property(parser):
    style = "font-family: 'Open Sans', Arial; font-size: 12px; opacity: 0.5"
    as_dict = parser.parse_style_to_dict(style)
    assert as_dict["font-size"] == "12px"
    assert parser.get_property_value(style, "opacity") == "0.5"
    assert parser.get_property_value(style, "missing", default="n/a") == "n/a"


def test_extract_font_family_returns_primary(parser):
    style = "font-family: \"Fira Sans\", Helvetica, Arial"
    assert parser.extract_font_family(style) == "Fira Sans"


def test_merge_styles_later_styles_override(parser):
    merged = parser.merge_styles(
        "fill: red; stroke: blue",
        "fill: green; stroke-width: 2px !important",
    )
    # Later value overrides earlier
    assert "fill: green" in merged
    # !important flag is preserved
    assert "stroke-width: 2px !important" in merged
    # Original stroke preserved because not overridden
    assert "stroke: blue" in merged
