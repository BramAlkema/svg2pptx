#!/usr/bin/env python3

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from unittest.mock import Mock

from lxml import etree as ET

pytest.importorskip("tinycss2")

from core.pipeline.navigation import (
    NavigationAction,
    NavigationKind,
    NavigationSpec,
    SlideTarget,
)
from core.io.embedder import DrawingMLEmbedder
from core.ir import Point, Run, TextAnchor, TextFrame
from core.ir.geometry import Rect
from core.ir.scene import Rectangle, SceneGraph
from core.map.base import MapperResult, OutputFormat
from core.map.text_mapper import TextMapper
from core.policy.targets import DecisionReason, PolicyDecision, TextDecision
from core.services.conversion_services import ConversionServices


def _build_rect(bounds: Rect) -> Rectangle:
    rect = Rectangle(bounds=bounds)
    setattr(rect, "source_id", "shape1")
    return rect


def _build_mapper_result(rect: Rectangle, navigation: list[NavigationSpec]) -> MapperResult:
    decision = PolicyDecision(use_native=True, reasons=[DecisionReason.SIMPLE_GEOMETRY])
    nsmap = {
        'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    }

    sp = ET.Element('{%s}sp' % nsmap['p'], nsmap=nsmap)
    nv_sppr = ET.SubElement(sp, '{%s}nvSpPr' % nsmap['p'])
    ET.SubElement(nv_sppr, '{%s}cNvPr' % nsmap['p'], id="1", name="Shape")
    ET.SubElement(nv_sppr, '{%s}cNvSpPr' % nsmap['p'])
    ET.SubElement(nv_sppr, '{%s}nvPr' % nsmap['p'])
    ET.SubElement(sp, '{%s}spPr' % nsmap['p'])

    shape_xml = ET.tostring(sp, encoding='unicode')
    return MapperResult(
        element=rect,
        output_format=OutputFormat.NATIVE_DML,
        xml_content=shape_xml,
        policy_decision=decision,
        metadata={'source_id': getattr(rect, 'source_id', None)},
        navigation=navigation,
    )


def _embed(mapper_result: MapperResult):
    services = ConversionServices.create_default()
    embedder = DrawingMLEmbedder(services=services)
    rect = mapper_result.element
    scene: SceneGraph = [rect]
    result = embedder.embed_scene(scene, [mapper_result])
    return embedder, result


def test_external_navigation_embeds_relationship():
    rect = _build_rect(Rect(0, 0, 100, 50))
    nav = NavigationSpec(kind=NavigationKind.EXTERNAL, href="https://example.com", tooltip="Example")
    mapper_result = _build_mapper_result(rect, [nav])

    embedder, embed_result = _embed(mapper_result)

    hyperlink_rels = [
        rel for rel in embed_result.relationship_data
        if rel.get('type') == 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink'
    ]
    assert len(hyperlink_rels) == 1
    assert hyperlink_rels[0]['target'] == "https://example.com"
    assert hyperlink_rels[0].get('target_mode') == 'External'
    root = ET.fromstring(embed_result.slide_xml.encode('utf-8'))
    ns = {
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    }
    link_nodes = root.xpath('.//a:hlinkClick', namespaces=ns)
    assert link_nodes
    assert link_nodes[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id') == hyperlink_rels[0]['id']
    assert not root.xpath(".//a:hlinkClick[contains(@tooltip, 'https://') or contains(@action, 'https://')]", namespaces=ns)


def test_slide_navigation_uses_slide_relationship():
    rect = _build_rect(Rect(0, 0, 100, 50))
    nav = NavigationSpec(kind=NavigationKind.SLIDE, slide=SlideTarget(index=3))
    mapper_result = _build_mapper_result(rect, [nav])

    _, embed_result = _embed(mapper_result)

    slide_rels = [
        rel for rel in embed_result.relationship_data
        if rel.get('type') == 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide'
    ]
    assert len(slide_rels) == 1
    assert slide_rels[0]['target'] == '../slides/slide3.xml'
    root = ET.fromstring(embed_result.slide_xml.encode('utf-8'))
    ns = {
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    }
    assert not root.xpath(".//a:hlinkClick[contains(@action, 'ppaction://')]", namespaces=ns)


def test_action_navigation_sets_action_uri():
    rect = _build_rect(Rect(0, 0, 100, 50))
    nav = NavigationSpec(kind=NavigationKind.ACTION, action=NavigationAction.NEXT)
    mapper_result = _build_mapper_result(rect, [nav])

    _, embed_result = _embed(mapper_result)

    root = ET.fromstring(embed_result.slide_xml.encode('utf-8'))
    ns = {
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    }
    action_nodes = root.xpath(".//a:hlinkClick[@action='ppaction://hlinkshowjump?jump=nextslide']", namespaces=ns)
    assert action_nodes


def test_text_run_navigation_embeds_hyperlinks():
    services = ConversionServices.create_default()

    policy = Mock()
    decision = TextDecision(
        use_native=True,
        estimated_quality=0.95,
        estimated_performance=0.9,
        reasons=[DecisionReason.SIMPLE_GEOMETRY],
    )
    policy.decide_text.return_value = decision
    policy.services = services

    mapper = TextMapper(policy, services=services)

    nav_external = NavigationSpec(kind=NavigationKind.EXTERNAL, href="https://example.com", tooltip="Site")
    nav_slide = NavigationSpec(
        kind=NavigationKind.SLIDE,
        slide=SlideTarget(index=4),
        visited=False,
    )

    runs = [
        Run(text="Visit", font_family="Arial", font_size_pt=12, navigation=nav_external),
        Run(text=" & ", font_family="Arial", font_size_pt=12),
        Run(text="Next", font_family="Arial", font_size_pt=12, navigation=nav_slide),
    ]

    text_frame = TextFrame(
        origin=Point(0, 0),
        runs=runs,
        bbox=Rect(0, 0, 120, 20),
        anchor=TextAnchor.START,
    )

    mapper_result = mapper.map(text_frame)

    embedder = DrawingMLEmbedder(services=services)
    scene: SceneGraph = [text_frame]
    embed_result = embedder.embed_scene(scene, [mapper_result])

    hyperlink_rels = [
        rel for rel in embed_result.relationship_data
        if rel.get('type') == 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink'
    ]
    assert hyperlink_rels
    external_usage = [
        usage for usage in hyperlink_rels[0].get('usage', [])
        if usage.get('scope') == 'text_run'
    ]
    assert external_usage
    assert external_usage[0].get('text') == 'Visit'

    slide_rels = [
        rel for rel in embed_result.relationship_data
        if rel.get('type') == 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide'
    ]
    assert slide_rels
    slide_usage = [
        usage for usage in slide_rels[0].get('usage', [])
        if usage.get('scope') == 'text_run'
    ]
    assert slide_usage
    assert slide_usage[0].get('text') == 'Next'
    slide_rel_id = slide_rels[0]['id']

    assert 'svg2pptx:navKey' not in embed_result.slide_xml

    ns = {
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    }
    root = ET.fromstring(embed_result.slide_xml.encode('utf-8'))
    run_hlinks = root.xpath('.//a:rPr/a:hlinkClick', namespaces=ns)
    assert len(run_hlinks) == 2

    rel_ids = {link.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id') for link in run_hlinks}
    assert slide_rel_id in rel_ids

    slide_link = next(
        link for link in run_hlinks
        if link.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id') == slide_rel_id
    )
    assert slide_link.get('history') == '0'
