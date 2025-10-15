#!/usr/bin/env python3
"""
Tests for animation builder helpers covering validation and timing composition.
"""

from __future__ import annotations

import pytest

from core.animations.builders import AnimationBuilder, AnimationSequenceBuilder, TimingBuilder
from core.animations.core import AnimationType, CalcMode, FillMode, TransformType


def test_animation_builder_requires_target_before_build():
    builder = AnimationBuilder().animate("opacity").from_to("0", "1")

    with pytest.raises(ValueError, match="Target element ID is required"):
        builder.build()


def test_animation_builder_creates_transform_animation_with_easing():
    animation = (
        AnimationBuilder()
        .target("shape-1")
        .animate_transform("scale")
        .from_to("1", "2")
        .duration("2s")
        .with_easing("ease-in")
        .build()
    )

    assert animation.animation_type is AnimationType.ANIMATE_TRANSFORM
    assert animation.transform_type is TransformType.SCALE
    assert animation.timing.duration == pytest.approx(2.0)
    assert animation.values == ["1", "2"]
    assert animation.calc_mode is CalcMode.SPLINE
    assert animation.key_splines == [[0.42, 0.0, 1.0, 1.0]]


def test_animation_sequence_builder_then_after_offsets_next_animation():
    first = (
        AnimationBuilder()
        .target("shape-1")
        .animate("opacity")
        .from_to("0", "1")
        .duration(1.0)
        .build()
    )
    second = (
        AnimationBuilder()
        .target("shape-2")
        .animate("opacity")
        .from_to("1", "0")
        .duration(2.0)
        .build()
    )

    sequence_builder = AnimationSequenceBuilder()
    sequence_builder.add_animation(first)
    sequence_builder.then_after("0.5s")
    sequence_builder.add_animation(second)
    sequence = sequence_builder.build()

    assert sequence[0].timing.begin == pytest.approx(0.0)
    assert sequence[0].timing.duration == pytest.approx(1.0)
    assert sequence[1].timing.begin == pytest.approx(1.5)
    assert sequence[1].timing.duration == pytest.approx(2.0)


def test_timing_builder_supports_indefinite_freeze():
    timing = (
        TimingBuilder()
        .duration("500ms")
        .delay("1s")
        .repeat(3)
        .freeze()
        .build()
    )

    assert timing.duration == pytest.approx(0.5)
    assert timing.begin == pytest.approx(1.0)
    assert timing.repeat_count == 3
    assert timing.fill_mode is FillMode.FREEZE


def test_animation_builder_discrete_calc_mode():
    animation = (
        AnimationBuilder()
        .target("node")
        .animate("opacity")
        .values("0", "1", "0")
        .discrete()
        .build()
    )

    assert animation.calc_mode is CalcMode.DISCRETE
    assert animation.values == ["0", "1", "0"]


def test_animation_builder_additive_sum_mode():
    animation = (
        AnimationBuilder()
        .target("node")
        .animate_transform(TransformType.ROTATE)
        .from_to("0", "90")
        .additive("sum")
        .build()
    )

    assert animation.additive == "sum"
    assert animation.transform_type is TransformType.ROTATE


def test_animation_sequence_simultaneously_aligns_start_times():
    fade_in = (
        AnimationBuilder()
        .target("a")
        .animate("opacity")
        .from_to("0", "1")
        .duration(1.0)
        .build()
    )
    fade_out = (
        AnimationBuilder()
        .target("b")
        .animate("opacity")
        .from_to("1", "0")
        .duration(1.0)
        .delay(2.0)
        .build()
    )
    scale = (
        AnimationBuilder()
        .target("c")
        .animate_transform("scale")
        .from_to("1", "2")
        .duration(1.0)
        .build()
    )

    builder = AnimationSequenceBuilder()
    builder.add_animation(fade_in)
    builder.add_animation(fade_out)
    builder.simultaneously()
    builder.add_animation(scale)

    sequence = builder.build()
    assert sequence[1].timing.begin == pytest.approx(sequence[2].timing.begin)


def test_timing_builder_indefinite_repeat():
    timing = TimingBuilder().duration(2).indefinite().build()

    assert timing.duration == 2.0
    assert timing.repeat_count == "indefinite"
