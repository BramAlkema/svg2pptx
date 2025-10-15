"""
Progress and telemetry tracking helpers for the converter pipeline.

Provides lightweight timing utilities and callback hooks so the converter
can surface stage-by-stage progress updates without managing bookkeeping
internally.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterable, Iterator


ProgressCallback = Callable[[str, float], None]


@dataclass(slots=True)
class StageSample:
    """Timing measurement for a single pipeline stage."""

    stage: str
    elapsed_ms: float


class ProgressTracker:
    """Tracks stage timings and emits progress callbacks."""

    def __init__(self, callback: ProgressCallback | None = None) -> None:
        self._callback = callback
        self._samples: list[StageSample] = []

    def set_callback(self, callback: ProgressCallback | None) -> None:
        """Replace the progress callback used for reporting."""
        self._callback = callback

    def report(self, stage: str, elapsed_ms: float) -> None:
        """Record a timing measurement and notify observers."""
        sample = StageSample(stage=stage, elapsed_ms=elapsed_ms)
        self._samples.append(sample)
        if self._callback:
            self._callback(stage, elapsed_ms)

    @contextmanager
    def track(self, stage: str) -> Iterator[None]:
        """
        Context manager that measures a stage duration automatically.

        Example:
            with tracker.track("parsing"):
                do_work()
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = (time.perf_counter() - start) * 1000.0
            self.report(stage, elapsed)

    def iter_samples(self) -> Iterable[StageSample]:
        """Return recorded samples in order."""
        return tuple(self._samples)

    def total_elapsed_ms(self) -> float:
        """Return the total elapsed time across all recorded stages."""
        return sum(sample.elapsed_ms for sample in self._samples)

    def clear(self) -> None:
        """Forget all recorded samples."""
        self._samples.clear()
