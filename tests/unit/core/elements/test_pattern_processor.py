#!/usr/bin/env python3
from __future__ import annotations

import types

import pytest
from lxml import etree as ET

from core.elements.pattern_processor import (
    PatternComplexity,
    PatternOptimization,
    PatternProcessor,
    PatternType,
)


def _pattern(markup: str) -> ET.Element:
    return ET.fromstring(f'<pattern xmlns="http://www.w3.org/2000/svg" id="pat" width="10" height="10">{markup}</pattern>')


def _processor() -> PatternProcessor:
    services = types.SimpleNamespace()
    return PatternProcessor(services)


def test_analyze_pattern_element_caches_result():
    processor = _processor()
    pattern = _pattern('<circle cx="2" cy="2" r="1" fill="#000"/>')
    context = types.SimpleNamespace()

    analysis1 = processor.analyze_pattern_element(pattern, context)
    analysis2 = processor.analyze_pattern_element(pattern, context)

    assert analysis1 is analysis2
    stats = processor.stats
    assert stats["cache_hits"] == 1
    assert analysis1.pattern_type is PatternType.DOTS
    assert analysis1.complexity is PatternComplexity.SIMPLE


def test_extract_geometry_and_complexity_adjustments():
    processor = _processor()
    pattern = _pattern('<rect width="50" height="2"/>')
    geometry = processor._extract_pattern_geometry(pattern)
    assert geometry.tile_width == pytest.approx(10.0)
    assert geometry.units == 'objectBoundingBox'

    pattern_type, child_count, colors = processor._analyze_pattern_content(pattern)
    assert pattern_type in {PatternType.LINES, PatternType.CUSTOM}
    assert child_count == 1

    complexity = processor._assess_pattern_complexity(pattern_type, child_count, geometry)
    assert complexity in {PatternComplexity.SIMPLE, PatternComplexity.MODERATE}


def test_identify_pattern_optimizations_and_requirements():
    processor = _processor()
    pattern = _pattern(
        '<circle cx="1" cy="1" r="0.5" fill="#111"/>\n'
        '<circle cx="3" cy="1" r="0.5" fill="#222"/>\n'
        '<circle cx="5" cy="1" r="0.5" fill="#333"/>\n'
    )
    pattern.set('patternTransform', 'rotate(45)')

    analysis = processor.analyze_pattern_element(pattern, types.SimpleNamespace())
    assert PatternOptimization.PRESET_MAPPING in analysis.optimization_opportunities
    assert analysis.has_transforms is True

    requires_prep = processor._requires_preprocessing(
        pattern,
        analysis.pattern_type,
        analysis.optimization_opportunities,
    )
    assert requires_prep is True


def test_should_use_emf_fallback_and_performance():
    processor = _processor()
    fallback = processor._should_use_emf_fallback(
        PatternType.CUSTOM,
        PatternComplexity.COMPLEX,
        has_transforms=True,
        preset_candidate=None,
    )
    assert fallback is True

    geometry = processor._extract_pattern_geometry(_pattern('<rect width="200" height="200"/>'))
    impact = processor._estimate_performance_impact(PatternComplexity.MODERATE, 5, geometry)
    assert impact in {"medium", "high"}
