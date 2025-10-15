import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.services.font_subsetter import FontSubsetter
from core.data.embedded_font import FontSubsetRequest


def test_build_subset_options_drops_kern_by_default():
    subsetter = FontSubsetter(preserve_kerning_tables=False)
    request = FontSubsetRequest(font_path="dummy.ttf", characters={"A"})

    options = subsetter.build_subset_options(request)

    assert "kern" in options.drop_tables
    assert options.text == "A"


def test_build_subset_options_preserves_kern_when_requested():
    subsetter = FontSubsetter(preserve_kerning_tables=False)
    request = FontSubsetRequest(
        font_path="dummy.ttf",
        characters={"A", "B"},
        preserve_kerning=True,
    )

    options = subsetter.build_subset_options(request)

    assert "kern" not in options.drop_tables
    assert sorted(options.text) == ["A", "B"]


def test_default_preserve_setting_can_be_enabled():
    subsetter = FontSubsetter(preserve_kerning_tables=True)
    request = FontSubsetRequest(font_path="dummy.ttf", characters={"X"})

    options = subsetter.build_subset_options(request)

    assert "kern" not in options.drop_tables
