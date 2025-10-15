import pytest

from core.ir.font_metadata import (
    create_font_metadata,
    parse_font_feature_settings,
    parse_font_variation_settings,
)


def test_parse_font_variation_settings():
    variations = parse_font_variation_settings('"wght" 500, "wdth" 80')
    assert variations == {"wght": 500.0, "wdth": 80.0}

    assert parse_font_variation_settings(None) == {}
    assert parse_font_variation_settings("") == {}


def test_parse_font_feature_settings():
    features = parse_font_feature_settings('"liga" 0, "kern" 1, "smcp"')
    assert features == ["liga", "kern", "smcp"]
    assert parse_font_feature_settings(None) == []


def test_create_font_metadata_with_typography_extensions():
    metadata = create_font_metadata(
        "Inter",
        size_pt=12,
        variation_settings='"wght" 550, "slnt" -7.5',
        feature_settings=["liga", "kern"],
        kerning=False,
    )

    assert metadata.variation_settings == {"wght": 550.0, "slnt": -7.5}
    assert metadata.open_type_features == ["liga", "kern"]
    assert metadata.kerning_enabled is False
