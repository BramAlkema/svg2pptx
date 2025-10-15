import math

import pytest

from core.ir.text_path import create_simple_text_path
from core.services.conversion_services import ConversionServices
from core.text.path_outliner import TextPathOutliner


@pytest.fixture(scope="module")
def outliner():
    services = ConversionServices.create_default()
    return TextPathOutliner(services)


def test_outliner_generates_glyphs_on_linear_path(outliner):
    text_path = create_simple_text_path("ABC", path_reference="#p", font_family="Arial", font_size_pt=16)
    path_data = "M 0 0 L 180 0"

    outlines = outliner.outline_text_on_path(text_path, path_data)

    assert len(outlines) == 3
    xs = [glyph.x_emu for glyph in outlines]
    assert xs[0] < xs[1] < xs[2]
    assert all(glyph.rotation_60000 == 0 for glyph in outlines)
    assert all(glyph.path_xml for glyph in outlines)


def test_outliner_respects_curve_rotation(outliner):
    text_path = create_simple_text_path("CURVE", path_reference="#curve", font_family="Arial", font_size_pt=14)
    curved_path = "M 0 0 Q 50 60 100 0"

    outlines = outliner.outline_text_on_path(text_path, curved_path)

    assert len(outlines) == len("CURVE")
    assert all(glyph.path_xml for glyph in outlines if glyph.character != " ")
