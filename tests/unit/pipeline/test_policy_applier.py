from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Dict

from core.animations.core import CalcMode
from core.pipeline.policy_applier import AnimationRejection, PolicyApplier, PolicyContext


@dataclass
class DummyTiming:
    duration: float | None


@dataclass
class DummyAnimation:
    element_id: str | None
    animation_type: object
    values: list
    timing: DummyTiming
    calc_mode: object


@dataclass
class DummyDecision:
    use_native: bool
    primary_reason: object | None


class LookupPolicy:
    """Policy that returns decisions keyed by animation id."""

    def __init__(self, decisions: Dict[str | None, DummyDecision]) -> None:
        self.decisions = decisions

    def decide_animation(self, *, animation_type: str, **kwargs):
        return self.decisions.get(animation_type)


def test_filter_animations_returns_approved_and_rejections() -> None:
    decision_map = {
        "opacity": DummyDecision(use_native=True, primary_reason=None),
        "translate": DummyDecision(
            use_native=False,
            primary_reason=SimpleNamespace(value="exceeds_limits"),
        ),
    }
    policy = LookupPolicy(decisions=decision_map)
    applier = PolicyApplier(PolicyContext(engine=policy))  # type: ignore[arg-type]

    animations = [
        DummyAnimation(
            element_id="anim-1",
            animation_type=SimpleNamespace(value="opacity"),
            values=[1, 2, 3],
            timing=DummyTiming(duration=1.5),
            calc_mode=CalcMode.LINEAR,
        ),
        DummyAnimation(
            element_id="anim-2",
            animation_type=SimpleNamespace(value="translate"),
            values=[1, 2],
            timing=DummyTiming(duration=0.2),
            calc_mode=CalcMode.DISCRETE,
        ),
    ]

    approved, rejections = applier.filter_animations(animations)

    assert [anim.element_id for anim in approved] == ["anim-1"]
    assert rejections == [AnimationRejection(animation_id="anim-2", reason="exceeds_limits")]


def test_filter_animations_handles_reason_without_value() -> None:
    policy = LookupPolicy(
        decisions={
            "scale": DummyDecision(
                use_native=False,
                primary_reason="manual_override",
            ),
        },
    )
    applier = PolicyApplier(PolicyContext(engine=policy))  # type: ignore[arg-type]

    animations = [
        DummyAnimation(
            element_id=None,
            animation_type="scale",
            values=[],
            timing=DummyTiming(duration=None),
            calc_mode="linear",
        ),
    ]

    approved, rejections = applier.filter_animations(animations)

    assert approved == []
    assert rejections == [AnimationRejection(animation_id=None, reason="manual_override")]
