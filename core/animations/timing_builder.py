"""
Timing builder utilities for animations.
"""

from __future__ import annotations

from .core import AnimationTiming, FillMode
from .time_utils import parse_time_value


class TimingBuilder:
    """Fluent builder for animation timing configuration."""

    def __init__(self):
        self._timing = AnimationTiming()

    def duration(self, duration: str | float) -> 'TimingBuilder':
        if isinstance(duration, str):
            self._timing.duration = parse_time_value(duration)
        else:
            self._timing.duration = float(duration)
        return self

    def delay(self, delay: str | float) -> 'TimingBuilder':
        if isinstance(delay, str):
            self._timing.begin = parse_time_value(delay)
        else:
            self._timing.begin = float(delay)
        return self

    def repeat(self, count: int | str) -> 'TimingBuilder':
        self._timing.repeat_count = count
        return self

    def indefinite(self) -> 'TimingBuilder':
        self._timing.repeat_count = "indefinite"
        return self

    def freeze(self) -> 'TimingBuilder':
        self._timing.fill_mode = FillMode.FREEZE
        return self

    def remove(self) -> 'TimingBuilder':
        self._timing.fill_mode = FillMode.REMOVE
        return self

    def build(self) -> AnimationTiming:
        return self._timing


__all__ = ["TimingBuilder"]
