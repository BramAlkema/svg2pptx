#!/usr/bin/env python3
"""
Unit tests for OOXMLTransformUtils conversions.
"""

import pytest

from core.utils.ooxml_transform_utils import OOXMLTransformUtils


class _StubEmuValue:
    def __init__(self, value):
        self.value = int(value)


class _StubContext:
    def __init__(self, dpi: float):
        self.dpi = dpi


class _StubUnitConverter:
    def __init__(self, dpi: float):
        self.default_context = _StubContext(dpi)


class _StubServices:
    def __init__(self, axis_map: dict[str, int], dpi: float = 96.0):
        self._axis_map = axis_map
        self.unit_converter = _StubUnitConverter(dpi)

    def emu(self, coord, *, axis="uniform"):
        scale = self._axis_map.get(axis, self._axis_map.get("uniform", 1))
        return _StubEmuValue(coord * scale)


def test_points_to_emu_uses_services_axis_scaling():
    services = _StubServices({"x": 1000})
    utils = OOXMLTransformUtils(services=services)

    result = utils.points_to_emu(2.5, axis="x")

    assert result == 2500


def test_pixels_to_emu_respects_service_dpi_and_axis():
    services = _StubServices({"x": 1000}, dpi=120.0)
    utils = OOXMLTransformUtils(services=services)

    # 120 px at 120 DPI -> 72 pt -> scaled by stub axis factor (1000)
    result = utils.pixels_to_emu(120, axis="x")

    assert result == 72000


def test_emu_to_pixels_caches_per_axis():
    axis_map = {"x": 1000, "y": 2000, "uniform": 1500}
    services = _StubServices(axis_map, dpi=96.0)
    utils = OOXMLTransformUtils(services=services)

    # All use 3 points (3 * 72 / 72) -> expect 4 pixels after rounding to float
    assert pytest.approx(utils.emu_to_pixels(3000, axis="x")) == 4.0
    assert pytest.approx(utils.emu_to_pixels(6000, axis="y")) == 4.0
    assert pytest.approx(utils.emu_to_pixels(4500, axis="uniform")) == 4.0


def test_utils_requires_services():
    with pytest.raises(RuntimeError):
        OOXMLTransformUtils()
