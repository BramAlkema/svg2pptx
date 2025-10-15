import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.ir.font_metadata import create_font_metadata
from core.ir.text import TextAnchor
from core.services.conversion_services import ConversionServices
from core.services.text_layout_engine import (
    create_text_layout_engine,
    svg_text_to_ppt_box_modern,
)


@pytest.fixture(scope="module")
def layout_context():
    services = ConversionServices.create_default()
    engine = create_text_layout_engine(
        services.unit_converter,
        services.font_processor,
        services=services,
    )
    return services, engine


def test_text_layout_respects_unit_converter(layout_context):
    services, engine = layout_context

    font_metadata = create_font_metadata("Arial", size_pt=18.0)
    svg_x = 120.0
    svg_y = 48.0

    result = engine.calculate_text_layout(
        svg_x=svg_x,
        svg_y=svg_y,
        text="Baseline Test",
        font_metadata=font_metadata,
        anchor=TextAnchor.START,
    )

    expected_baseline_x = int(services.unit_converter.to_emu(f"{svg_x}px"))
    expected_baseline_y = int(services.unit_converter.to_emu(f"{svg_y}px"))

    assert result.baseline_x_emu == expected_baseline_x
    assert result.baseline_y_emu == expected_baseline_y
    assert result.y_emu == expected_baseline_y - result.ascent_emu
    assert result.height_emu >= result.ascent_emu + result.descent_emu


def test_text_layout_anchor_adjustments(layout_context):
    services, engine = layout_context
    font_metadata = create_font_metadata("Arial", size_pt=16.0)
    svg_x = 200.0
    svg_y = 80.0

    baseline_x = int(services.unit_converter.to_emu(f"{svg_x}px"))

    start_result = engine.calculate_text_layout(
        svg_x, svg_y, "Anchor", font_metadata, TextAnchor.START,
    )
    middle_result = engine.calculate_text_layout(
        svg_x, svg_y, "Anchor", font_metadata, TextAnchor.MIDDLE,
    )
    end_result = engine.calculate_text_layout(
        svg_x, svg_y, "Anchor", font_metadata, TextAnchor.END,
    )

    assert start_result.x_emu == baseline_x
    assert middle_result.x_emu == baseline_x - middle_result.measurements.width_emu // 2
    assert end_result.x_emu == baseline_x - end_result.measurements.width_emu


def test_svg_text_to_ppt_box_modern(layout_context):
    services, _ = layout_context
    x_emu, y_emu, width_emu, height_emu = svg_text_to_ppt_box_modern(
        svg_x=42.0,
        svg_y=20.0,
        anchor="start",
        text="Compat Helper",
        font_family="Arial",
        font_size_pt=14.0,
        services=services,
    )

    assert isinstance(x_emu, int)
    assert isinstance(y_emu, int)
    assert width_emu > 0
    assert height_emu > 0
