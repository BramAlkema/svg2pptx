"""
Sequence builder utilities for animations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from .core import AnimationDefinition
from .time_utils import parse_time_value

if TYPE_CHECKING:
    from .builders import AnimationBuilder


class AnimationSequenceBuilder:
    """Fluent builder for constructing animation sequences."""

    def __init__(self):
        self._animations: List[AnimationDefinition] = []
        self._current_time_offset: float = 0.0

    def add_animation(self, animation: AnimationDefinition) -> 'AnimationSequenceBuilder':
        animation.timing.begin += self._current_time_offset
        self._animations.append(animation)
        return self

    def add_builder(self, builder: 'AnimationBuilder') -> 'AnimationSequenceBuilder':
        animation = builder.build()
        return self.add_animation(animation)

    def then_after(self, delay: str | float) -> 'AnimationSequenceBuilder':
        if isinstance(delay, str):
            delay_seconds = parse_time_value(delay)
        else:
            delay_seconds = float(delay)

        if self._animations:
            last_animation = self._animations[-1]
            last_end_time = last_animation.timing.begin + last_animation.timing.duration
            self._current_time_offset = last_end_time + delay_seconds
        else:
            self._current_time_offset += delay_seconds
        return self

    def simultaneously(self) -> 'AnimationSequenceBuilder':
        if self._animations:
            self._current_time_offset = self._animations[-1].timing.begin
        return self

    def build(self) -> List[AnimationDefinition]:
        return self._animations.copy()


__all__ = ["AnimationSequenceBuilder"]
