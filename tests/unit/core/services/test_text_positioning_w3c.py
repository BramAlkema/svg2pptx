import math

import pytest

from core.ir.font_metadata import create_font_metadata
from core.ir.text import TextAnchor
from core.services.conversion_services import ConversionServices
from core.services.text_layout_engine import create_text_layout_engine


def _create_engine():
    services = ConversionServices.create_default()
    engine = create_text_layout_engine(
        services.unit_converter,
        services.font_processor,
        services=services,
    )
    return services, engine


@pytest.fixture(scope="module")
def layout_engine():
    return _create_engine()


W3C_CASES = [
    {
        "name": "start-anchor",
        "svg_x": 120.0,
        "svg_y": 48.0,
        "text": "Start",  # mirrors text-anchor:start behaviour
        "anchor": TextAnchor.START,
        "font": {"family": "Arial", "size_pt": 16.0},
    },
    {
        "name": "middle-anchor",
        "svg_x": 200.0,
        "svg_y": 60.0,
        "text": "Middle",
        "anchor": TextAnchor.MIDDLE,
        "font": {"family": "Arial", "size_pt": 18.0},
    },
    {
        "name": "end-anchor",
        "svg_x": 260.0,
        "svg_y": 72.0,
        "text": "End",
        "anchor": TextAnchor.END,
        "font": {"family": "Arial", "size_pt": 14.0},
    },
]


@pytest.mark.parametrize("case", W3C_CASES, ids=lambda c: c["name"])
def test_text_positioning_w3c(layout_engine, case):
    services, engine = layout_engine

    font_metadata = create_font_metadata(
        case["font"]["family"],
        size_pt=case["font"]["size_pt"],
    )

    layout = engine.calculate_text_layout(
        svg_x=case["svg_x"],
        svg_y=case["svg_y"],
        text=case["text"],
        font_metadata=font_metadata,
        anchor=case["anchor"],
    )

    unit_converter = services.unit_converter
    expected_baseline_x = int(unit_converter.to_emu(f"{case['svg_x']}px"))
    expected_baseline_y = int(unit_converter.to_emu(f"{case['svg_y']}px"))

    assert layout.baseline_x_emu == expected_baseline_x
    assert layout.baseline_y_emu == expected_baseline_y

    # Acceptance criteria: anchor alignment checks
    if case["anchor"] is TextAnchor.START:
        assert layout.x_emu == expected_baseline_x
    elif case["anchor"] is TextAnchor.MIDDLE:
        midpoint = layout.x_emu + layout.width_emu / 2.0
        assert math.isclose(midpoint, expected_baseline_x, abs_tol=2)
    elif case["anchor"] is TextAnchor.END:
        right_edge = layout.x_emu + layout.width_emu
        assert math.isclose(right_edge, expected_baseline_x, abs_tol=2)

    # Baseline to top-left conversion: y should equal baseline minus ascent
    assert layout.y_emu == layout.baseline_y_emu - layout.ascent_emu


def test_text_positioning_accuracy_summary(layout_engine):
    services, engine = layout_engine
    font_metadata = create_font_metadata("Arial", size_pt=16.0)

    samples = 0
    within_tolerance = 0

    for svg_x in range(0, 401, 80):
        for anchor in (TextAnchor.START, TextAnchor.MIDDLE, TextAnchor.END):
            layout = engine.calculate_text_layout(
                svg_x=svg_x,
                svg_y=40.0,
                text="Accuracy",
                font_metadata=font_metadata,
                anchor=anchor,
            )

            baseline_x = layout.baseline_x_emu

            if anchor is TextAnchor.START:
                delta = abs(layout.x_emu - baseline_x)
            elif anchor is TextAnchor.MIDDLE:
                delta = abs((layout.x_emu + layout.width_emu / 2.0) - baseline_x)
            else:
                delta = abs((layout.x_emu + layout.width_emu) - baseline_x)

            samples += 1
            if delta <= 2:  # approximately within 0.02 pt
                within_tolerance += 1

    accuracy = within_tolerance / samples
    assert accuracy >= 0.9
