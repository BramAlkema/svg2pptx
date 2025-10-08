#!/usr/bin/env python3

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

pytest.importorskip("tinycss2")

from core.clip import LegacyClipBridge, StructuredClipService
from core.policy.config import ClipPolicy
from core.ir import Path as IRPath, SolidPaint
from core.ir.geometry import LineSegment, Point, Rect
from core.ir.scene import ClipRef
from core.policy.targets import DecisionReason, PathDecision
from core.map.path_mapper import PathMapper
from core.map.clipping_adapter import ClippingPathAdapter, ClippingResult


def test_clipping_adapter_generates_native_clip_from_segments():
    segments = (
        LineSegment(Point(0, 0), Point(10, 0)),
        LineSegment(Point(10, 0), Point(10, 5)),
        LineSegment(Point(10, 5), Point(0, 5)),
        LineSegment(Point(0, 5), Point(0, 0)),
    )
    clip_ref = ClipRef(
        clip_id="url(#segClip)",
        path_segments=segments,
        bounding_box=Rect(0, 0, 10, 5),
    )

    adapter = ClippingPathAdapter()
    result = adapter.generate_clip_xml(clip_ref)

    assert result.strategy == "native_dml"
    assert "<a:clipPath>" in result.xml_content
    assert "<a:lnTo>" in result.xml_content


class _NoOpStructuredClipService(StructuredClipService):
    def compute(self, clip_ref, analysis, element_context=None):
        return None


def test_structured_adapter_noop_when_service_returns_none():
    clip_ref = ClipRef(clip_id="url(#noopClip)")
    clip_policy = ClipPolicy(enable_structured_adapter=True)

    adapter = ClippingPathAdapter(
        clip_policy=clip_policy,
        structured_clip_service=_NoOpStructuredClipService(),
        clip_bridge=LegacyClipBridge(),
    )

    adapter._clipping_available = True
    adapter.clippath_analyzer = type("StubAnalyzer", (), {"analyze_clippath": lambda self, **_: _StubAnalysis()})()

    result = adapter.generate_clip_xml(clip_ref)

    assert result is not None
    assert "<a:clipPath>" in result.xml_content


class _StubAnalysis:
    def __init__(self):
        from core.converters.clippath_types import ClipPathComplexity

        self.complexity = ClipPathComplexity.SIMPLE
        self.requires_emf = False
        self.can_preprocess = False
        self.clip_chain = []


class _StubStructuredService(StructuredClipService):
    def compute(self, clip_ref, analysis, element_context=None):
        from core.clip.model import ClipComputeResult, ClipCustGeom, ClipFallback

        xml = (
            "<a:custGeom><a:pathLst><a:path w=\"0\" h=\"0\" fill=\"none\">"
            "<a:moveTo><a:pt x=\"0\" y=\"0\"/></a:moveTo>"
            "<a:lnTo><a:pt x=\"100\" y=\"0\"/></a:lnTo>"
            "<a:lnTo><a:pt x=\"100\" y=\"100\"/></a:lnTo>"
            "<a:close/></a:path></a:pathLst></a:custGeom>"
        )
        custgeom = ClipCustGeom(path_xml=xml, fill_rule_even_odd=False)
        return ClipComputeResult(strategy=ClipFallback.NONE, custgeom=custgeom, used_bbox_rect=True)


def test_structured_adapter_bridge_path(monkeypatch):
    clip_ref = ClipRef(clip_id="url(#bridgeClip)")
    policy = ClipPolicy(enable_structured_adapter=True)
    adapter = ClippingPathAdapter(
        clip_policy=policy,
        structured_clip_service=_StubStructuredService(),
        clip_bridge=LegacyClipBridge(),
    )

    adapter.clippath_analyzer = type("StubAnalyzer", (), {"analyze_clippath": lambda self, **_: _StubAnalysis()})()
    adapter._clipping_available = True

    element_context = {"clippath_element": object(), "clippath_definitions": {}}

    result = adapter.generate_clip_xml(clip_ref, element_context)

    assert result.strategy == "custgeom_bridge"
    assert "custGeom" in result.xml_content
    assert "structured_result" in result.metadata


def test_emf_clipping_generates_media(monkeypatch):
    from core.converters.clippath_types import ClipPathComplexity

    class _EmfStubAdapter:
        def can_generate_emf(self, path):
            return True

        def generate_emf_blob(self, path):
            return type(
                "EmfResult",
                (),
                {
                    "emf_data": b"emf-bytes",
                    "relationship_id": "rId777",
                    "width_emu": 914400,
                    "height_emu": 914400,
                    "metadata": {},
                },
            )()

    monkeypatch.setattr("core.map.emf_adapter.create_emf_adapter", lambda: _EmfStubAdapter())

    clip_ref = ClipRef(clip_id="url(#complexClip)", bounding_box=Rect(0, 0, 1, 1))
    analysis = type(
        "Analysis",
        (),
        {
            "complexity": ClipPathComplexity.COMPLEX,
            "requires_emf": True,
            "can_preprocess": False,
            "clip_chain": [],
        },
    )()

    adapter = ClippingPathAdapter(clip_policy=ClipPolicy(enable_structured_adapter=False))
    result = adapter._generate_emf_clipping(clip_ref, analysis)

    assert isinstance(result, ClippingResult)
    media = result.metadata.get("media_files")
    assert media and media[0]["data"] == b"emf-bytes"


def test_path_mapper_propagates_clip_media(monkeypatch):
    class _StubClipAdapter:
        def can_generate_clipping(self, clip):
            return True

        def generate_clip_xml(self, clip, element_context=None):
            return ClippingResult(
                xml_content="<!-- emf fallback -->",
                complexity="COMPLEX",
                strategy="emf_fallback",
                preprocessing_applied=False,
                metadata={
                    'media_files': [{
                        'type': 'emf',
                        'data': b'clip-emf',
                        'relationship_id': 'rIdClip',
                        'content_type': 'application/emf',
                        'width_emu': 914400,
                        'height_emu': 914400,
                    }],
                },
            )

    monkeypatch.setattr("core.map.clipping_adapter.create_clipping_adapter", lambda services=None, **_: _StubClipAdapter())

    class _Policy:
        def decide_path(self, path):
            return PathDecision.native(
                reasons=[DecisionReason.SIMPLE_GEOMETRY],
                segment_count=len(path.segments),
                has_clipping=path.clip is not None,
            )

    clip_ref = ClipRef(clip_id="url(#emfClip)", bounding_box=Rect(0, 0, 1, 1))
    segments = [
        LineSegment(Point(0, 0), Point(1, 0)),
        LineSegment(Point(1, 0), Point(1, 1)),
        LineSegment(Point(1, 1), Point(0, 0)),
    ]
    path = IRPath(segments=segments, fill=SolidPaint(rgb="FF0000"), clip=clip_ref)

    mapper = PathMapper(_Policy())
    mapper.services = None

    result = mapper.map(path)

    assert result.media_files
    assert result.media_files[0]['data'] == b'clip-emf'
