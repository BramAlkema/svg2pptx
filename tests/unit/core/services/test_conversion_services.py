#!/usr/bin/env python3

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.services.conversion_services import (
    ConversionServices,
    ConversionConfig,
    EmuPoint,
    EmuRect,
    EmuValue,
)


@pytest.fixture()
def services():
    config = ConversionConfig(default_dpi=96.0)
    return ConversionServices.create_default(config=config)


def _expected_emu(services, value: float) -> int:
    """Derive the expected EMU output honoring fractional converter availability."""
    if services.fractional_emu_converter:
        unit = "px"
    else:
        unit = "pt"
    return int(round(services.unit_converter.to_emu(f"{value}{unit}")))


def test_emu_returns_expected_integer(services):
    result = services.emu(10.0)
    assert isinstance(result, EmuValue)
    assert result.value == _expected_emu(services, 10.0)
    assert result.rounding_strategy == "round"
    assert result.used_fractional is bool(services.fractional_emu_converter)
    if services.fractional_emu_converter:
        assert result.fractional is not None
    else:
        assert result.fractional is None


def test_emu_point_and_rect_helpers(services):
    from core.ir.geometry import Point, Rect

    point = Point(1.5, 2.5)
    rect = Rect(0.0, 0.0, 3.0, 4.0)

    point_result = services.emu_point(point)
    rect_result = services.emu_rect(rect)

    assert isinstance(point_result, EmuPoint)
    assert isinstance(point_result.x, EmuValue)
    assert isinstance(point_result.y, EmuValue)
    assert isinstance(rect_result, EmuRect)
    assert rect_result.width.value == _expected_emu(services, 3.0)
    assert rect_result.height.value == _expected_emu(services, 4.0)
    assert rect_result.width.axis == "x"
    assert rect_result.height.axis == "y"


def test_color_helpers(services):
    assert services.color_to_hex('rgb(0, 128, 255)') == '0080FF'
    assert services.normalize_color('#ff00ff', include_hash=True) == '#FF00FF'
    assert services.color_to_rgb('#010203') == (1, 2, 3)
