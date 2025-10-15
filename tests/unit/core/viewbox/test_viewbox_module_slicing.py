#!/usr/bin/env python3
"""Module slicing coverage for ViewportEngine."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from lxml import etree as ET

from core.viewbox.core import AspectAlign, MeetOrSlice, ViewportEngine
from core.viewbox_new import resolve_viewports as resolve_viewports_new

FIXTURE_PATH = Path("testing/fixtures/module_slicing/viewbox/preserve_aspect_ratio.svg")


def load_svg_element() -> ET.Element:
    return ET.fromstring(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_parse_viewbox_and_preserve_aspect_ratio_vectors():
    engine = ViewportEngine()

    parsed = engine.parse_viewbox_strings(np.array(["0 0 200 100", "invalid"]))
    assert parsed[0]['min_x'] == pytest.approx(0.0)
    assert parsed[0]['width'] == pytest.approx(200.0)
    assert parsed[0]['aspect_ratio'] == pytest.approx(2.0)
    # Invalid entries become sentinel values
    assert parsed[1]['width'] == -1
    assert parsed[1]['height'] == -1

    alignments, meet_slice = engine.parse_preserve_aspect_ratio_batch(
        np.array(["xMidYMid meet", "none", "xMaxYMin slice"])
    )
    assert alignments.tolist() == [
        AspectAlign.X_MID_Y_MID.value,
        AspectAlign.NONE.value,
        AspectAlign.X_MAX_Y_MIN.value,
    ]
    assert meet_slice.tolist() == [
        MeetOrSlice.MEET.value,
        MeetOrSlice.MEET.value,
        MeetOrSlice.SLICE.value,
    ]


def test_batch_resolve_respects_target_sizes():
    engine = ViewportEngine()
    svg = load_svg_element()

    target_width = 400_000
    target_height = 200_000

    mappings = engine.batch_resolve_svg_viewports(
        [svg],
        target_sizes=[(target_width, target_height)],
    )
    mapping = mappings[0]

    assert mapping['scale_x'] == pytest.approx(2000.0)
    assert mapping['scale_y'] == pytest.approx(2000.0)
    assert mapping['translate_x'] == pytest.approx(0.0)
    assert mapping['translate_y'] == pytest.approx(0.0)
    assert mapping['content_width'] == target_width
    assert mapping['content_height'] == target_height
    assert not mapping['clip_needed']


def test_fluent_resolution_chain_matches_batch_output():
    svg = load_svg_element()
    target_width = 300_000
    target_height = 150_000

    engine = ViewportEngine()
    record = (
        engine
        .for_svg(svg)
        .with_slide_size(target_width, target_height)
        .center()
        .meet()
        .resolve_single()
    )

    assert record is not None
    assert record['scale_x'] == pytest.approx(1500.0)
    assert record['scale_y'] == pytest.approx(1500.0)
    assert record['content_width'] == target_width
    assert record['content_height'] == target_height


def test_viewport_builder_delegates_to_engine_state():
    svg = load_svg_element()
    engine = ViewportEngine()

    builder = engine.builder()
    builder.for_svg(svg).with_slide_size(250_000, 125_000).bottom_right().slice()

    result = builder.resolve()
    mapping = result[0]

    assert mapping['viewport_width'] == 250_000
    assert mapping['viewport_height'] == 125_000
    assert engine._alignment == AspectAlign.X_MAX_Y_MAX
    assert engine._meet_or_slice == MeetOrSlice.SLICE


def test_new_api_resolve_viewports_matches_legacy_engine():
    svg = load_svg_element()
    legacy = ViewportEngine().batch_resolve_svg_viewports([svg])
    modern = resolve_viewports_new([svg])
    assert np.array_equal(legacy, modern)


def test_coordinate_transforms_and_matrices():
    engine = ViewportEngine()
    svg = load_svg_element()
    mappings = engine.batch_resolve_svg_viewports(
        [svg],
        target_sizes=[(200_000, 100_000)],
    )
    coords = np.array([[10.0, 5.0], [0.0, 0.0]])
    emu_coords = engine.batch_svg_to_emu_coordinates(coords, mappings)
    assert emu_coords.shape == coords.shape
    # Scale factor should be 1000, so 10 -> 10000
    assert emu_coords[0, 0] == 10_000
    assert emu_coords[0, 1] == 5_000

    matrices = engine.generate_transform_matrices_batch(mappings)
    assert matrices.shape == (1, 3, 3)
    assert matrices[0, 0, 0] == pytest.approx(1000.0)
    assert matrices[0, 2, 2] == 1.0
