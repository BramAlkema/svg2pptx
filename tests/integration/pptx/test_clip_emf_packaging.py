#!/usr/bin/env python3

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytest.importorskip("tinycss2")

from core.io.embedder import DrawingMLEmbedder
from core.map.base import MapperResult, OutputFormat
from core.policy.targets import DecisionReason, PathDecision
from core.ir import Path as IRPath, SolidPaint
from core.ir.geometry import LineSegment, Point
from core.ir.scene import ClipRef


def test_embedder_records_clip_emf_media():
    segments = [
        LineSegment(Point(0, 0), Point(1, 0)),
        LineSegment(Point(1, 0), Point(1, 1)),
        LineSegment(Point(1, 1), Point(0, 0)),
    ]
    clip = ClipRef(clip_id="url(#clip)")
    path = IRPath(segments=segments, fill=SolidPaint(rgb="FF0000"), clip=clip)

    decision = PathDecision.native(reasons=[DecisionReason.SIMPLE_GEOMETRY])

    media_files = [{
        'type': 'emf',
        'data': b'clip-emf',
        'relationship_id': 'rIdClip',
        'content_type': 'application/emf',
        'width_emu': 914400,
        'height_emu': 914400,
    }]

    mapper_result = MapperResult(
        element=path,
        output_format=OutputFormat.EMF_VECTOR,
        xml_content='<p:sp/>',
        policy_decision=decision,
        metadata={},
        media_files=media_files,
    )

    embedder = DrawingMLEmbedder()
    result = embedder.embed_scene([], [mapper_result])

    assert any(m['type'] == 'emf' for m in result.media_files)
    assert any(rel['type'].endswith('/relationships/image') for rel in result.relationship_data)
