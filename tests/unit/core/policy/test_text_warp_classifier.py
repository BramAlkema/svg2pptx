import pytest

from core.algorithms.curve_text_positioning import (
    PathSamplingMethod,
    create_curve_text_positioner,
)
from core.ir.text_path import TextPathMethod, TextPathSide, create_simple_text_path
from core.policy.text_warp_classifier import classify_text_path_warp


def _sample_points(path_data: str, samples: int = 64):
    positioner = create_curve_text_positioner(PathSamplingMethod.DETERMINISTIC)
    return positioner.sample_path_for_text(path_data, samples)


def test_classify_upward_arch_returns_arch_preset():
    path_data = "M 0 0 Q 50 120 100 0"
    points = _sample_points(path_data)
    text_path = create_simple_text_path("Hello", path_reference="#curve")

    result = classify_text_path_warp(text_path, points, path_data)

    assert result is not None
    assert result['preset'].startswith('textArch') or result['preset'].startswith('textCurve')
    assert result['confidence'] > 0.5


def test_classify_two_cycle_wave_uses_wave_preset():
    path_data = "M 0 0 Q 25 40 50 0 Q 75 -40 100 0 Q 125 40 150 0"
    points = _sample_points(path_data, samples=80)
    text_path = create_simple_text_path("Wave", path_reference="#wave")

    result = classify_text_path_warp(text_path, points, path_data)

    assert result is not None
    assert result['preset'] in {'textWave2', 'textWave4', 'textDoubleWave1'}
    assert result['confidence'] > 0.55


def test_closed_circle_path_prefers_ring_presets():
    path_data = "M 50 0 A 50 50 0 1 1 49.999 0 Z"
    points = _sample_points(path_data, samples=72)
    text_path = create_simple_text_path(
        "Circle",
        path_reference="#circle",
        side=TextPathSide.LEFT,
        method=TextPathMethod.ALIGN,
    )

    result = classify_text_path_warp(text_path, points, path_data)

    assert result is not None
    assert result['preset'] in {'textCircle', 'textRingInside', 'textCirclePour', 'textButtonPour'}
    assert result['confidence'] > 0.5


def test_flat_baseline_prefers_plain_preset():
    path_data = "M 0 0 L 120 0"
    points = _sample_points(path_data, samples=32)
    text_path = create_simple_text_path("Flat", path_reference="#flat")

    result = classify_text_path_warp(text_path, points, path_data)

    assert result is not None
    assert result['preset'] == 'textPlain'
    assert result['confidence'] >= 0.85


def test_returns_none_when_samples_missing():
    text_path = create_simple_text_path("Few", path_reference="#few")

    result = classify_text_path_warp(text_path, [])

    assert result is None
