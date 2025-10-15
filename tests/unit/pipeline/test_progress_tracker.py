from __future__ import annotations

import time

from core.pipeline.progress_tracker import ProgressTracker


def test_report_records_sample_and_invokes_callback():
    seen = []

    def callback(stage: str, elapsed: float) -> None:
        seen.append((stage, elapsed))

    tracker = ProgressTracker(callback=callback)
    tracker.report("parsing", 12.5)

    samples = tracker.iter_samples()
    assert len(samples) == 1
    assert samples[0].stage == "parsing"
    assert samples[0].elapsed_ms == 12.5
    assert seen and seen[0][0] == "parsing"


def test_track_context_manager_records_elapsed_time():
    tracker = ProgressTracker()
    with tracker.track("analysis"):
        time.sleep(0.001)

    samples = tracker.iter_samples()
    assert samples[-1].stage == "analysis"
    assert samples[-1].elapsed_ms > 0
    assert tracker.total_elapsed_ms() >= samples[-1].elapsed_ms


def test_clear_removes_samples():
    tracker = ProgressTracker()
    tracker.report("stage", 5.0)
    tracker.clear()
    assert list(tracker.iter_samples()) == []
