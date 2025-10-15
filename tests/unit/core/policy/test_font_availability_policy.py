import pytest

from core.ir.geometry import Point, Rect
from core.ir.text import Run, TextAnchor, TextFrame
from core.policy.engine import Policy


class MockFontService:
    def __init__(self, available_families):
        self.available_families = {name.lower() for name in available_families}
        self.calls = []

    def find_font_file(self, font_family, font_weight="normal", font_style="normal"):
        self.calls.append((font_family, font_weight, font_style))
        return "/mock/path.ttf" if font_family.lower() in self.available_families else None


def _make_text_frame(font_family: str) -> TextFrame:
    return TextFrame(
        origin=Point(0, 0),
        anchor=TextAnchor.START,
        bbox=Rect(0, 0, 1000, 400),
        runs=[
            Run(
                text="Hello",
                font_family=font_family,
                font_size_pt=14.0,
            ),
        ],
    )


def test_font_available_prefers_system_strategy():
    policy = Policy(font_service=MockFontService({"MockFont"}))
    decision = policy.decide_text(_make_text_frame("MockFont"))

    assert decision.use_native is True
    assert decision.font_strategy == "system"
    assert decision.font_match_confidence >= 0.9
    assert decision.missing_fonts == []
    assert decision.system_font_fallback == "MockFont"


def test_missing_font_triggers_text_to_path_strategy():
    policy = Policy(font_service=MockFontService(set()))
    decision = policy.decide_text(_make_text_frame("MissingFont"))

    assert decision.use_native is False
    assert decision.font_strategy == "text_to_path"
    assert decision.has_missing_fonts is True
    assert "MissingFont" in decision.missing_fonts
    assert decision.font_match_confidence == 0.0
