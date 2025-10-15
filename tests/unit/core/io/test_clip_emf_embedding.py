#!/usr/bin/env python3

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.clip import ClipMediaMeta
from core.io.embedder import DrawingMLEmbedder
from core.map.base import MapperResult, OutputFormat
from core.map.clipping_adapter import ClippingPathAdapter
from core.policy.targets import DecisionReason, PathDecision
from core.ir import Path as IRPath
from core.ir.geometry import LineSegment, Point
from core.services.conversion_services import ConversionServices


def _emf_mapper_result() -> MapperResult:
    media_meta = ClipMediaMeta(
        content_type="application/emf",
        rel_id="rIdClip",
        part_name=None,
        bbox_emu=(0, 0, 914400, 914400),
        data=b"clip-emf",
        description="clip_emf_fallback",
    )

    emf_xml = ClippingPathAdapter._build_emf_pic_xml(media_meta)

    segments = [
        LineSegment(Point(0, 0), Point(1, 0)),
        LineSegment(Point(1, 0), Point(1, 1)),
        LineSegment(Point(1, 1), Point(0, 0)),
    ]
    path = IRPath(segments=segments, fill=None, clip=None)

    metadata = {
        "strategy": "emf_fallback",
        "clip_strategy": "emf_fallback",
        "fallback_reason": "clip_emf_fallback",
        "media_meta": media_meta,
    }

    media_entry = {
        "type": "emf",
        "data": media_meta.data,
        "relationship_id": media_meta.rel_id,
        "content_type": media_meta.content_type,
        "width_emu": media_meta.bbox_emu[2],
        "height_emu": media_meta.bbox_emu[3],
    }

    return MapperResult(
        element=path,
        output_format=OutputFormat.EMF_VECTOR,
        xml_content=emf_xml,
        policy_decision=PathDecision.emf(
            reasons=[DecisionReason.CLIP_PATH_COMPLEX],
            segment_count=len(segments),
            has_clipping=True,
        ),
        metadata=metadata,
        estimated_quality=0.95,
        estimated_performance=0.8,
        output_size_bytes=len(emf_xml.encode("utf-8")),
        media_files=[media_entry],
    )


def test_embedder_embeds_clip_emf_picture():
    mapper_result = _emf_mapper_result()
    services = ConversionServices.create_default()
    embedder = DrawingMLEmbedder(services=services)

    embed_result = embedder.embed_scene([], [mapper_result])

    assert '<p:pic' in embed_result.slide_xml
    assert 'r:embed="rIdClip"' in embed_result.slide_xml

    assert embed_result.relationship_data
    assert any(rel['id'] == 'rIdClip' for rel in embed_result.relationship_data)

    assert embed_result.media_files
    media_entry = embed_result.media_files[0]
    assert media_entry['relationship_id'] == 'rIdClip'
    assert media_entry['data'] == b'clip-emf'
