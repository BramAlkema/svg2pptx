#!/usr/bin/env python3

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from lxml import etree as ET

pytest.importorskip("tinycss2")

from core.clip import ClipComputeResult, ClipCustGeom, ClipFallback, ClipMediaMeta, StructuredClipService
from core.policy.config import ClipPolicy
from core.ir import Path as IRPath, SolidPaint
from core.ir.geometry import LineSegment, Point, Rect
from core.ir.scene import ClipRef
from core.policy.targets import DecisionReason, PathDecision
from core.map.path_mapper import PathMapper
from core.services.conversion_services import ConversionServices
from core.map.clipping_adapter import ClippingPathAdapter
from core.map.base import OutputFormat
from core.groups.clipping_analyzer import ClippingComplexity, ClippingStrategy


@pytest.fixture(scope="module")
def services():
    return ConversionServices.create_default()


def test_clipping_adapter_generates_native_clip_from_segments(services):
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

    adapter = ClippingPathAdapter(services=services)
    result = adapter.generate_clip_xml(clip_ref)

    assert result.strategy == ClipFallback.NONE
    assert result.custgeom is not None
    clip_element = ET.fromstring(result.custgeom.path_xml)
    ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
    assert clip_element.tag == '{http://schemas.openxmlformats.org/drawingml/2006/main}clipPath'
    assert clip_element.find('a:path', ns) is not None
    assert clip_element.findall('.//a:lnTo', ns)


class _NoOpStructuredClipService(StructuredClipService):
    def __init__(self, services):
        super().__init__(services=services)

    def compute(self, clip_ref, analysis, element_context=None):
        return None


class _MockClipDefinition:
    def __init__(self, clip_id: str = "mockClip"):
        self.id = clip_id
        self.path_data = "M0 0 L10 0 L10 10 Z"
        self.shapes = []
        self.transform = None
        self.clip_rule = "nonzero"
        self.bounding_box = Rect(0, 0, 10, 10)


def test_structured_adapter_noop_when_service_returns_none(services):
    clip_ref = ClipRef(clip_id="url(#noopClip)")
    clip_policy = ClipPolicy(enable_structured_adapter=True)

    adapter = ClippingPathAdapter(
        services=services,
        clip_policy=clip_policy,
        structured_clip_service=_NoOpStructuredClipService(services),
    )

    svg_root = ET.Element("svg")
    ET.SubElement(svg_root, "clipPath", id="noopClip")

    adapter._clipping_available = True
    adapter.clippath_analyzer = type(
        "StubAnalyzer",
        (),
        {"analyze_clipping_scenario": lambda self, element, context: _StubAnalysis("noopClip")},
    )()

    result = adapter.generate_clip_xml(clip_ref, element_context={"svg_root": svg_root})

    assert isinstance(result, ClipComputeResult)
    assert result.custgeom is not None
    clip_element = ET.fromstring(result.custgeom.path_xml)
    ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
    assert clip_element.tag == '{http://schemas.openxmlformats.org/drawingml/2006/main}clipPath'


class _StubAnalysis:
    def __init__(self, clip_id: str = "mockClip", *, strategy: ClippingStrategy = ClippingStrategy.CUSTGEOM,
                 complexity: ClippingComplexity = ClippingComplexity.SIMPLE):
        self.complexity = complexity
        self.recommended_strategy = strategy
        self.fallback_strategy = ClippingStrategy.EMF_VECTOR
        self.requires_preprocessing = False
        self.optimization_opportunities: list[str] = []
        self.estimated_performance_impact = "low"
        self.clip_chain = [_MockClipDefinition(clip_id)]

    @property
    def requires_emf(self) -> bool:
        return self.recommended_strategy == ClippingStrategy.EMF_VECTOR

    @property
    def can_preprocess(self) -> bool:
        return self.requires_preprocessing


class _StubStructuredService(StructuredClipService):
    def __init__(self, services):
        super().__init__(services=services)

    def compute(self, clip_ref, analysis, element_context=None):
        from core.clip.model import ClipComputeResult, ClipCustGeom, ClipFallback

        xml = (
            "<a:clipPath><a:path w=\"0\" h=\"0\" fill=\"none\">"
            "<a:moveTo><a:pt x=\"0\" y=\"0\"/></a:moveTo>"
            "<a:lnTo><a:pt x=\"100\" y=\"0\"/></a:lnTo>"
            "<a:lnTo><a:pt x=\"100\" y=\"100\"/></a:lnTo>"
            "<a:close/></a:path></a:clipPath>"
        )
        custgeom = ClipCustGeom(path_xml=xml, fill_rule_even_odd=False)
        return ClipComputeResult(strategy=ClipFallback.NONE, custgeom=custgeom, used_bbox_rect=True)


def test_structured_adapter_bridge_path(monkeypatch, services):
    clip_ref = ClipRef(clip_id="url(#bridgeClip)")
    policy = ClipPolicy(enable_structured_adapter=True)
    adapter = ClippingPathAdapter(
        services=services,
        clip_policy=policy,
        structured_clip_service=_StubStructuredService(services),
    )

    svg_root = ET.Element("svg")
    ET.SubElement(svg_root, "clipPath", id="bridgeClip")
    adapter.clippath_analyzer = type(
        "StubAnalyzer",
        (),
        {"analyze_clipping_scenario": lambda self, element, context: _StubAnalysis("bridgeClip")},
    )()
    adapter._clipping_available = True

    element_context = {"svg_root": svg_root}

    result = adapter.generate_clip_xml(clip_ref, element_context)

    assert isinstance(result, ClipComputeResult)
    assert result.strategy == ClipFallback.NONE
    assert result.metadata
    assert result.metadata.get("generation_method") == "structured_service"
    assert "analysis" in result.metadata
    assert result.custgeom and "clipPath" in (result.custgeom.path_xml or "")


def test_emf_clipping_generates_media(monkeypatch, services):
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

    monkeypatch.setattr("core.map.emf_adapter.create_emf_adapter", lambda services: _EmfStubAdapter())

    clip_ref = ClipRef(clip_id="url(#complexClip)", bounding_box=Rect(0, 0, 1, 1))
    analysis = _StubAnalysis(
        "complexClip",
        strategy=ClippingStrategy.EMF_VECTOR,
        complexity=ClippingComplexity.COMPLEX,
    )

    adapter = ClippingPathAdapter(services=services, clip_policy=ClipPolicy(enable_structured_adapter=False))
    result = adapter._generate_emf_clipping(clip_ref, analysis, {"generation_method": "existing_system"})

    assert isinstance(result, ClipComputeResult)
    assert result.media is not None
    assert result.media.data == b"emf-bytes"
    metadata = result.metadata or {}
    assert metadata.get("media_files")
    assert metadata.get("emf_pic_xml", "").startswith("<p:pic>")
    assert metadata.get("strategy") == "emf_fallback"
    assert metadata.get("clip_strategy") == ClipFallback.EMF_SHAPE.value
    assert metadata.get("tracer_strategy") == "emf_fallback"


class _StubCustGeomGenerator:
    def can_generate_custgeom(self, clip_def):
        return True

    def generate_custgeom_xml(self, clip_def, context):
        return "<a:custGeom><a:pathLst><a:path w=\"0\" h=\"0\"><a:moveTo><a:pt x=\"0\" y=\"0\"/></a:moveTo></a:path></a:pathLst></a:custGeom>"


def test_existing_system_uses_custgeom_generator(monkeypatch, services):
    clip_ref = ClipRef(clip_id="url(#custClip)", bounding_box=Rect(0, 0, 10, 10))
    analysis = _StubAnalysis("custClip", strategy=ClippingStrategy.CUSTGEOM, complexity=ClippingComplexity.SIMPLE)

    structured_service = StructuredClipService(services=services, custgeom_generator=_StubCustGeomGenerator())
    adapter = ClippingPathAdapter(
        services=services,
        clip_policy=ClipPolicy(enable_structured_adapter=False),
        structured_clip_service=structured_service,
    )

    adapter._clipping_available = True

    result = adapter._generate_with_existing_system(clip_ref, analysis, {})

    assert isinstance(result, ClipComputeResult)
    assert result.custgeom is not None
    assert result.custgeom.path_xml and "<a:custGeom>" in result.custgeom.path_xml
    assert result.metadata
    assert result.metadata.get("generation_method") == "custgeom_generator"
    assert result.used_bbox_rect is False


def test_path_mapper_propagates_clip_media(monkeypatch, services):
    class _StubClipAdapter:
        def can_generate_clipping(self, clip):
            return True

        def generate_clip_xml(self, clip, element_context=None):
            media_meta = ClipMediaMeta(
                content_type="application/emf",
                rel_id="rIdClip",
                part_name=None,
                bbox_emu=(0, 0, 914400, 914400),
                data=b"clip-emf",
                description="clip_emf_fallback",
            )
            return ClipComputeResult(
                strategy=ClipFallback.EMF_SHAPE,
                custgeom=None,
                media=media_meta,
                used_bbox_rect=False,
                metadata={
                    'strategy': 'emf_fallback',
                    'clip_strategy': ClipFallback.EMF_SHAPE.value,
                    'tracer_strategy': 'emf_fallback',
                    'media_files': [{
                        'type': 'emf',
                        'data': b'clip-emf',
                        'relationship_id': 'rIdClip',
                        'content_type': 'application/emf',
                        'width_emu': 914400,
                        'height_emu': 914400,
                    }],
                    'media_meta': media_meta,
                    'emf_pic_xml': '<p:pic><p:blipFill><a:blip r:embed="rIdClip"/></p:blipFill></p:pic>',
                },
            )

    monkeypatch.setattr("core.map.clipping_adapter.create_clipping_adapter", lambda services, **_: _StubClipAdapter())

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

    mapper = PathMapper(_Policy(), services)

    result = mapper.map(path)

    assert result.output_format == OutputFormat.EMF_VECTOR
    assert result.media_files
    assert result.media_files[0]['data'] == b'clip-emf'
    assert '<a:blip' in result.xml_content
    assert result.metadata.get('fallback_reason') == 'clip_emf_fallback'
    assert result.metadata.get('clip_strategy') == 'emf_fallback'
