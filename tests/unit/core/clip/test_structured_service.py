#!/usr/bin/env python3

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytest.importorskip("tinycss2")

from core.clip.model import ClipFallback
from core.clip.service import StructuredClipService
from core.converters.clippath_types import ClipPathComplexity, ClipPathDefinition
from core.ir.geometry import Rect
from core.ir.scene import ClipRef


class _DummyAnalysis:
    def __init__(self, complexity, requires_emf=False, clip_chain=None):
        self.complexity = complexity
        self.requires_emf = requires_emf
        self.clip_chain = clip_chain or []


def test_structured_service_returns_custgeom_for_simple_clip():
    service = StructuredClipService()
    clip_ref = ClipRef(clip_id="#bboxClip", bounding_box=Rect(0, 0, 100, 100))
    clip_def = ClipPathDefinition(
        id="clip1",
        units="userSpaceOnUse",
        clip_rule="nonzero",
        path_data="M0 0 L100 0 L100 100 L0 100 Z",
        shapes=None,
    )
    analysis = _DummyAnalysis(ClipPathComplexity.SIMPLE, clip_chain=[clip_def])

    result = service.compute(clip_ref, analysis, element_context={})

    assert result is not None
    assert result.strategy == ClipFallback.NONE
    assert result.custgeom is not None
    assert "a:custGeom" in result.custgeom.path_xml
    assert result.used_bbox_rect is False


def test_structured_service_returns_none_when_emf_required():
    service = StructuredClipService()
    clip_ref = ClipRef(clip_id="#bboxClip", bounding_box=Rect(0, 0, 1, 1))
    analysis = _DummyAnalysis(ClipPathComplexity.COMPLEX, requires_emf=True)

    assert service.compute(clip_ref, analysis) is None
