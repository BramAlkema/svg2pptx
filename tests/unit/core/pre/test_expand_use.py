#!/usr/bin/env python3
from __future__ import annotations

import time

import pytest
from lxml import etree as ET

from core.pre.expand_use import ExpandUsePreprocessor, expand_use_elements

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"


def _svg(fragment: str) -> ET.Element:
    return ET.fromstring(
        f'<svg xmlns="{SVG_NS}" xmlns:xlink="{XLINK_NS}">{fragment}</svg>'
    )


def test_expand_use_replaces_reference(monkeypatch):
    svg = _svg("""
      <defs>
        <linearGradient id="grad"><stop offset="0%"/></linearGradient>
        <rect id="box" width="10" height="20" fill="url(#grad)"/>
      </defs>
      <use xlink:href="#box" x="5" y="7" />
    """)

    # Fix suffix generation for deterministic IDs
    monkeypatch.setattr(time, "time", lambda: 0.12345)

    pre = ExpandUsePreprocessor()
    result = pre.process(svg)

    groups = result.findall(f".//{{{SVG_NS}}}g")
    assert len(groups) == 1
    expanded_group = groups[0]
    assert expanded_group.get("transform") == "translate(5,7)"

    child_rect = expanded_group.find(f"{{{SVG_NS}}}rect")
    assert child_rect is not None
    assert child_rect.get("width") == "10"
    assert child_rect.get("fill").startswith("url(#grad_expanded_")

    # The original use element should be removed
    assert result.find(f".//{{{SVG_NS}}}use") is None


def test_expand_use_handles_missing_reference():
    svg = _svg('<use xlink:href="#missing" />')
    result = expand_use_elements(svg)
    # Use element should remain untouched because reference is missing
    assert result.find(f".//{{{SVG_NS}}}use") is not None
