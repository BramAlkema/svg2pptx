#!/usr/bin/env python3
"""Regression tests ensuring PathMapper no longer relies on legacy adapter shims."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.ir.geometry import LineSegment, Point
from core.ir.paint import SolidPaint
from core.ir.scene import Path
from core.map.path_mapper import PathMapper
from core.map.emf_adapter import EMFResult
from core.map.base import OutputFormat


class _StubPolicy:
    """Minimal policy stub for mapper tests."""

    def __init__(self, services, *, use_native: bool):
        self.services = services
        self._decision = SimpleNamespace(
            use_native=use_native,
            estimated_quality=0.95,
            estimated_performance=0.9,
            reasoning="stub-decision",
            to_dict=lambda: {
                "use_native": use_native,
                "quality": 0.95,
                "performance": 0.9,
                "reasoning": "stub-decision",
            },
        )

    def decide_path(self, _path: Path):
        return self._decision


@pytest.fixture
def simple_path() -> Path:
    """Create a trivial path for mapper tests."""
    segment = LineSegment(start=Point(0, 0), end=Point(10, 0))
    return Path(
        segments=[segment],
        fill=SolidPaint(rgb="FF0000"),
        stroke=None,
        clip=None,
        opacity=1.0,
    )


def test_path_mapper_has_no_legacy_adapter_hooks(conversion_services, simple_path):
    """PathMapper should not expose legacy adapter setters or cached attributes."""
    policy = _StubPolicy(conversion_services, use_native=True)
    mapper = PathMapper(policy)

    assert not hasattr(PathMapper, "set_emf_adapter")
    assert not hasattr(PathMapper, "set_drawingml_adapter")
    assert "_emf_adapter" not in mapper.__dict__
    assert "_drawingml_adapter" not in mapper.__dict__

    result = mapper.map(simple_path)
    assert result.output_format == OutputFormat.NATIVE_DML
    # Still no shim attributes after mapping
    assert "_emf_adapter" not in mapper.__dict__
    assert "_drawingml_adapter" not in mapper.__dict__


def test_path_mapper_uses_emf_adapter_factory(monkeypatch, conversion_services, simple_path):
    """PathMapper must call create_emf_adapter instead of relying on injected shims."""
    policy = _StubPolicy(conversion_services, use_native=False)
    mapper = PathMapper(policy)

    called = {"count": 0}

    class DummyAdapter:
        def can_generate_emf(self, _path: Path) -> bool:
            return True

        def generate_emf_blob(self, _path: Path) -> EMFResult:
            return EMFResult(
                emf_data=b"stub-emf",
                relationship_id="rId123",
                width_emu=1000,
                height_emu=2000,
                quality_score=0.9,
                metadata={"adapter": "dummy"},
            )

    def fake_create(services):
        assert services is conversion_services
        called["count"] += 1
        return DummyAdapter()

    monkeypatch.setattr("core.map.emf_adapter.create_emf_adapter", fake_create)

    result = mapper.map(simple_path)

    assert called["count"] == 1, "Expected create_emf_adapter to be invoked once"
    assert result.output_format == OutputFormat.EMF_VECTOR
    assert result.metadata.get("emf_generation") == "real_blob"
