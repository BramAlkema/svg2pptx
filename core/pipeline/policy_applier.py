"""
Policy application helpers for the Clean Slate converter (Phase 2D refactor).

This module centralises policy decisions that previously lived inside the
converter so orchestration code can remain lean.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple

from core.animations import AnimationDefinition
from core.animations.core import CalcMode
from core.policy import PolicyEngine


@dataclass(slots=True)
class PolicyContext:
    """Container for policy-related collaborators required by the converter."""

    engine: PolicyEngine


@dataclass(slots=True)
class AnimationRejection:
    """Represents an animation that was rejected by policy decisions."""

    animation_id: str | None
    reason: str


class PolicyApplier:
    """Facade that mediates policy lookups and surfaces structured results."""

    def __init__(self, context: PolicyContext) -> None:
        self.context = context

    def filter_animations(
        self,
        animations: Iterable[AnimationDefinition],
    ) -> Tuple[List[AnimationDefinition], List[AnimationRejection]]:
        """
        Apply animation policy decisions and separate approved/rejected items.

        Returns:
            approved_animations: animations that may be embedded natively.
            rejections: metadata describing skipped animations.
        """
        engine = self.context.engine

        approved: list[AnimationDefinition] = []
        rejections: list[AnimationRejection] = []

        for animation in animations:
            animation_type_value = _safe_value(getattr(animation, "animation_type", None))
            keyframe_count = len(getattr(animation, "values", []) or [])

            duration = getattr(getattr(animation, "timing", None), "duration", 0.0) or 0.0
            duration_ms = duration * 1000.0

            calc_mode = getattr(animation, "calc_mode", None)
            if isinstance(calc_mode, CalcMode):
                interpolation = calc_mode.value
            else:
                interpolation = str(calc_mode) if calc_mode is not None else "none"

            decision = engine.decide_animation(
                animation_type=animation_type_value,
                keyframe_count=keyframe_count,
                duration_ms=duration_ms,
                interpolation=interpolation,
            )

            if getattr(decision, "use_native", False):
                approved.append(animation)
                continue

            reason = getattr(getattr(decision, "primary_reason", None), "value", None)
            if not reason:
                reason = str(getattr(decision, "primary_reason", "unspecified"))
            rejections.append(
                AnimationRejection(
                    animation_id=getattr(animation, "element_id", None),
                    reason=reason,
                ),
            )

        return approved, rejections


def _safe_value(enum_member: object | None) -> str:
    """Extract `.value` when available, otherwise stringify the member."""
    if enum_member is None:
        return "unknown"
    value = getattr(enum_member, "value", None)
    if value is not None:
        return value
    return str(enum_member)
