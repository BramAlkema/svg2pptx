#!/usr/bin/env python3

import sys
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.ir import ClipRef
from core.map.group_mapper import GroupMapper
from core.map.image_mapper import ImageMapper
from core.policy.engine import Policy


def test_group_mapper_generates_clip_path_for_bbox_clip():
    mapper = GroupMapper(policy=Mock(), child_mappers={})
    clip_xml, meta = mapper._generate_group_clip_xml(ClipRef("bbox:0:0:100:50"))

    assert "<a:clipPath>" in clip_xml
    assert "1270000" in clip_xml and "635000" in clip_xml
    assert meta and meta.get('strategy') == 'bbox'


def test_image_mapper_generates_clip_path_for_bbox_clip():
    policy = Mock(spec=Policy)
    image_mapper = ImageMapper(policy=policy, services=None)
    clip_xml, meta = image_mapper._generate_image_clip_xml(ClipRef("bbox:0:0:90:30"))

    assert "<a:clipPath>" in clip_xml
    assert "1143000" in clip_xml and "381000" in clip_xml
    assert meta and meta.get('strategy') == 'bbox'
