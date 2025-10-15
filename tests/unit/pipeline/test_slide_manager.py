from __future__ import annotations

from core.pipeline.slide_manager import SlideManager


def test_slide_manager_tracks_and_resets_slides():
    manager = SlideManager()
    assert manager.primary_payload() is None

    idx0 = manager.add_slide("slide-1", {"title": "Intro"})
    assert idx0 == 0
    assert manager.primary_payload() == "slide-1"

    idx1 = manager.add_slide("slide-2")
    assert idx1 == 1
    payloads = manager.iter_payloads()
    assert payloads == ("slide-1", "slide-2")

    manager.reset()
    assert manager.iter_payloads() == ()
    assert manager.primary_payload() is None
