#!/usr/bin/env python3
from __future__ import annotations

import types

import pytest
from lxml import etree as ET

from core.groups.clipping_analyzer import (
    ClippingAnalyzer,
    ClippingAnalysis,
    ClippingComplexity,
    ClippingPath,
    ClippingStrategy,
)
from core.ir.geometry import Rect

SVG_NS = "http://www.w3.org/2000/svg"


def _svg(markup: str) -> ET.Element:
    return ET.fromstring(f'<svg xmlns="{SVG_NS}">{markup}</svg>')


def _analyzer(policy_engine=None) -> ClippingAnalyzer:
    services = types.SimpleNamespace()
    return ClippingAnalyzer(services, policy_engine=policy_engine)


def test_analyze_clipping_scenario_uses_cache():
    svg = _svg(
        """
        <defs>
          <clipPath id="clip1"><rect width="10" height="5"/></clipPath>
        </defs>
        <rect id="target" clip-path="url(#clip1)"/>
        """
    )
    element = svg.find(f'{{{SVG_NS}}}rect[@id="target"]')
    context = types.SimpleNamespace(svg_root=svg, clippath_definitions=None)

    analyzer = _analyzer()
    analysis_first = analyzer.analyze_clipping_scenario(element, context)
    analysis_second = analyzer.analyze_clipping_scenario(element, context)

    assert analysis_first is analysis_second
    stats = analyzer.get_analysis_statistics()
    assert stats["cache_hits"] == 1
    assert analysis_first.clipping_paths[0].complexity == ClippingComplexity.SIMPLE


def test_shape_bbox_and_merge_rects():
    analyzer = _analyzer()
    rect = ET.Element("rect", x="1", y="2", width="5", height="3")
    circle = ET.Element("circle", cx="6", cy="4", r="2")
    bbox_rect = analyzer._shape_bbox(rect)
    bbox_circle = analyzer._shape_bbox(circle)

    merged = analyzer._merge_rects([bbox_rect, bbox_circle])
    assert merged.x == 1
    assert merged.y == 2
    assert merged.width == pytest.approx(7)
    assert merged.height == pytest.approx(4)


def test_determine_strategy_without_policy():
    analyzer = _analyzer()
    simple_clip = ClippingPath(
        id="clip",
        path_data=None,
        shapes=[ET.Element("rect")],
        units="userSpaceOnUse",
        transform=None,
        complexity=ClippingComplexity.SIMPLE,
        powerpoint_compatible=True,
        clip_rule=None,
        bounding_box=Rect(0, 0, 1, 1),
    )

    strategy = analyzer._determine_strategy([simple_clip], ClippingComplexity.SIMPLE)
    assert strategy is ClippingStrategy.POWERPOINT_NATIVE

    complex_clip = simple_clip.__class__(
        **{**simple_clip.__dict__, "complexity": ClippingComplexity.COMPLEX, "powerpoint_compatible": False}
    )
    strategy_complex = analyzer._determine_strategy([complex_clip], ClippingComplexity.COMPLEX)
    assert strategy_complex is ClippingStrategy.EMF_VECTOR


def test_determine_strategy_with_policy(monkeypatch):
    class StubDecision:
        def __init__(self, clipping=False, native=False):
            self.use_native_clipping = clipping
            self.use_native = native

    class StubPolicy:
        def __init__(self, decision):
            self._decision = decision

        def decide_clippath(self, **_kwargs):
            return self._decision

    clip = ClippingPath(
        id="clip",
        path_data="M0 0 L1 0 L1 1 Z",
        shapes=[ET.Element("rect")],
        units="userSpaceOnUse",
        transform=None,
        complexity=ClippingComplexity.SIMPLE,
        powerpoint_compatible=True,
        clip_rule=None,
        bounding_box=Rect(0, 0, 1, 1),
    )

    policy = StubPolicy(StubDecision(clipping=True))
    analyzer = _analyzer(policy)
    assert analyzer._determine_strategy([clip], ClippingComplexity.SIMPLE) is ClippingStrategy.POWERPOINT_NATIVE

    policy_non_native = StubPolicy(StubDecision(clipping=False, native=False))
    analyzer = _analyzer(policy_non_native)
    assert analyzer._determine_strategy([clip], ClippingComplexity.SIMPLE) is ClippingStrategy.EMF_VECTOR


def test_requires_preprocessing_flags_complex_cases():
    analyzer = _analyzer()

    element = ET.Element("g")
    clip = ClippingPath(
        id="clip",
        path_data=None,
        shapes=[ET.Element("path")],
        units="userSpaceOnUse",
        transform=None,
        complexity=ClippingComplexity.MODERATE,
        powerpoint_compatible=False,
        clip_rule=None,
        bounding_box=None,
    )

    assert analyzer._requires_preprocessing(element, [clip]) is True
    element.set("data-clip-operation", "flattened")
    assert analyzer._requires_preprocessing(element, [clip]) is False


def test_identify_optimizations_and_performance():
    analyzer = _analyzer()
    clip = ClippingPath(
        id="clip",
        path_data="M" + "L" * 250,
        shapes=[ET.Element("rect"), ET.Element("rect", transform="scale(2)")],
        units="userSpaceOnUse",
        transform="rotate(45)",
        complexity=ClippingComplexity.COMPLEX,
        powerpoint_compatible=False,
        clip_rule=None,
        bounding_box=Rect(0, 0, 200, 200),
    )

    optimizations = analyzer._identify_optimizations([clip], ClippingComplexity.COMPLEX)
    assert 'path_simplification' in optimizations
    assert 'transform_flattening' in optimizations

    fallback = analyzer._determine_fallback_strategy(ClippingStrategy.CUSTGEOM, ClippingComplexity.COMPLEX)
    assert fallback is ClippingStrategy.EMF_VECTOR

    impact = analyzer._estimate_performance_impact([clip], ClippingComplexity.COMPLEX)
    assert impact in {"medium", "high", "very_high"}


def test_create_no_clipping_analysis_defaults():
    analyzer = _analyzer()
    element = ET.Element("rect")
    analysis = analyzer._create_no_clipping_analysis(element)

    assert analysis.recommended_strategy is ClippingStrategy.POWERPOINT_NATIVE
    assert analysis.complexity is ClippingComplexity.SIMPLE
