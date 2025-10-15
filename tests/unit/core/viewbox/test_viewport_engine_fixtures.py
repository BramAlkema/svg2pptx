#!/usr/bin/env python3
"""Fixture-backed tests for the sliced viewport engine facade."""

from __future__ import annotations

import numpy as np
import pytest

from core.viewbox.core import ViewportEngine, create_viewport_engine
from core.viewbox_new.config import (
    AspectAlign,
    MeetOrSlice,
    ViewBoxArray,
    ViewportArray,
    ViewportMappingArray,
)
from testing.fixtures.module_slicing import svg_batch_samples


def test_viewport_engine_fluent_resolution():
    engine = ViewportEngine()
    svg = svg_batch_samples()[0]

    mapping = (
        engine.for_svg(svg)
        .with_slide_size(9144000, 6858000)
        .center()
        .meet()
        .resolve_single()
    )

    assert mapping["viewport_width"] == 9144000
    assert mapping["viewport_height"] == 6858000
    assert mapping["scale_x"] == pytest.approx(mapping["scale_y"])


def test_viewport_engine_requires_svg_before_resolve():
    engine = ViewportEngine()
    with pytest.raises(ValueError):
        engine.resolve()


def test_calculate_viewport_mappings_handles_alignment_modes():
    engine = ViewportEngine()

    viewboxes = np.zeros(2, dtype=ViewBoxArray)
    viewboxes["min_x"] = [0, 10]
    viewboxes["min_y"] = [0, 10]
    viewboxes["width"] = [800, 400]
    viewboxes["height"] = [600, 200]

    viewports = np.zeros(2, dtype=ViewportArray)
    viewports["width"] = [1600, 800]
    viewports["height"] = [1200, 600]

    mappings = engine.calculate_viewport_mappings(
        viewboxes,
        viewports,
        align=AspectAlign.X_MID_Y_MID,
        meet_or_slice=MeetOrSlice.MEET,
    )

    assert mappings["scale_x"][0] == pytest.approx(mappings["scale_y"][0])
    assert bool(mappings["clip_needed"][0]) is False

    # Invalid viewBox falls back to identity mapping
    viewboxes["width"][1] = 0
    viewboxes["height"][1] = 0
    mappings_invalid = engine.calculate_viewport_mappings(viewboxes, viewports, align=AspectAlign.NONE)
    assert mappings_invalid["scale_x"][1] == 1.0
    assert mappings_invalid["viewport_width"][1] == viewports["width"][1]


def test_calculate_viewport_mappings_batch_preserves_aspect_ratio():
    engine = ViewportEngine()

    viewboxes = np.zeros(3, dtype=ViewBoxArray)
    viewboxes["width"] = [800, 500, 0]
    viewboxes["height"] = [600, 400, 0]

    viewports = np.zeros(3, dtype=ViewportArray)
    viewports["width"] = [1600, 500, 300]
    viewports["height"] = [1200, 400, 200]

    alignments = np.array([AspectAlign.NONE.value, AspectAlign.X_MID_Y_MID.value, AspectAlign.X_MIN_Y_MIN.value])
    meet_slice = np.array([MeetOrSlice.MEET.value, MeetOrSlice.SLICE.value, MeetOrSlice.MEET.value])

    batch = engine.calculate_viewport_mappings_batch(viewboxes, viewports, alignments, meet_slice)

    assert np.isfinite(batch["scale_x"]).all()
    assert batch["scale_x"][2] == 0.0
    assert isinstance(batch["clip_needed"][1].item(), (bool, np.bool_))


def test_svg_to_emu_pipeline_and_transform_matrices():
    engine = ViewportEngine()
    svg = svg_batch_samples()[0]
    mappings = engine.batch_resolve_svg_viewports(
        [svg],
        target_sizes=[(9144000, 6858000)],
    )

    points = np.array([[0.0, 0.0], [100.0, 50.0]])
    transformed = engine.batch_svg_to_emu_coordinates(points, mappings)

    assert transformed.shape == (2, 2)
    assert transformed[0, 0] == pytest.approx(mappings["translate_x"][0])

    matrices = engine.generate_transform_matrices_batch(mappings)
    assert matrices.shape == (1, 3, 3)
    assert matrices[0, 2, 2] == 1.0


def test_performance_and_memory_helpers():
    engine = create_viewport_engine()
    stats = engine.get_performance_stats()
    assert "work_buffer_size" in stats
    assert stats["mapping_dtype_size"] == ViewportMappingArray.itemsize

    memory = engine.get_memory_usage()
    assert "alignment_factors_bytes" in memory


def test_advanced_coordinate_mapping_and_intersection():
    engine = ViewportEngine()

    source_spaces = np.zeros(2, dtype=[("min_x", "f8"), ("min_y", "f8"), ("width", "f8"), ("height", "f8")])
    target_spaces = np.zeros_like(source_spaces)
    source_spaces["width"] = [100.0, 50.0]
    source_spaces["height"] = [50.0, 25.0]
    target_spaces["width"] = [200.0, 100.0]
    target_spaces["height"] = [100.0, 50.0]

    points = np.array([[10.0, 10.0], [5.0, 5.0]])
    mapping = engine.advanced_coordinate_space_mapping(source_spaces, target_spaces, points)
    assert mapping["mapping_valid"].all()
    assert np.allclose(mapping["scale_factor_x"], [2.0, 2.0])

    bounds_a = np.array([[0.0, 0.0, 10.0, 10.0], [5.0, 5.0, 10.0, 10.0]])
    bounds_b = np.array([[5.0, 0.0, 10.0, 10.0], [20.0, 20.0, 5.0, 5.0]])
    intersections = engine.efficient_bounds_intersection(bounds_a, bounds_b)
    assert bool(intersections["has_intersection"][0]) is True
    assert bool(intersections["has_intersection"][1]) is False
