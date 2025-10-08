#!/usr/bin/env python3

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

pytest.importorskip("tinycss2")

from core.parse.parser import SVGParser
from core.ir.scene import Path as IRPath, Rectangle


def _parse(svg: str):
    parser = SVGParser(enable_normalization=False)
    scene, result = parser.parse_to_ir(svg)
    assert result.success, result.error
    return scene, result


def test_clip_path_segments_attached_to_path():
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg">
      <defs>
        <clipPath id="clipRect">
          <rect x="0" y="0" width="10" height="5"/>
        </clipPath>
      </defs>
      <path d="M0 0 L10 0 L10 10 z" clip-path="url(#clipRect)" />
    </svg>
    """
    scene, result = _parse(svg)

    assert "clipRect" in result.clip_paths
    clip_def = result.clip_paths["clipRect"]
    assert clip_def.segments
    assert clip_def.bounding_box is not None

    path = next(elem for elem in scene if isinstance(elem, IRPath))
    assert path.clip is not None
    assert path.clip.path_segments
    assert path.clip.bounding_box == clip_def.bounding_box


def test_clip_path_segments_support_paths():
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg">
      <defs>
        <clipPath id="clipPath">
          <path d="M0 0 L20 0 L20 10 L0 10 z"/>
        </clipPath>
      </defs>
      <rect x="0" y="0" width="5" height="5" clip-path="url(#clipPath)"/>
    </svg>
    """
    scene, result = _parse(svg)

    assert "clipPath" in result.clip_paths
    clip_def = result.clip_paths["clipPath"]
    assert clip_def.segments

    clipped = next(elem for elem in scene if getattr(elem, 'clip', None))
    assert clipped.clip is not None
    assert clipped.clip.path_segments
