#!/usr/bin/env python3
import math
from xml.etree import ElementTree as ET

import pytest

from core.utils import preprocessor_utilities as module
from core.utils.preprocessor_utilities import PreprocessorUtilities


@pytest.fixture
def utils():
    return PreprocessorUtilities()


def test_format_number_handles_special_cases(utils):
    assert utils.format_number(42.0) == "42"
    assert utils.format_number(3.14159, precision=2) == "3.14"
    assert utils.format_number(float("nan")) == "0"
    assert utils.format_number(float("inf")) == "0"
    assert utils.format_number(1_500_000, precision=2) == "1500000"
    assert utils.format_number(1_234_567.89, precision=2) == "1.23e+06"
    assert utils.format_number(0.0000007, precision=3) == "0"


def test_format_number_pair_consistent_precision(utils):
    assert utils.format_number_pair(10.125, 5.5, precision=2) == "10.12,5.5"


def test_clean_numeric_value_uses_validator(utils):
    assert utils.clean_numeric_value("12px", precision=1) == "12"
    assert utils.clean_numeric_value("bad-value") == "bad-value"


def test_parse_points_string_manual_fallback(monkeypatch, utils):
    monkeypatch.setattr(module, "UTILITY_SERVICES_AVAILABLE", False)
    monkeypatch.setattr(module, "coordinate_transformer", None)
    result = utils.parse_points_string("0,0 10,20")
    assert result.success is True
    assert result.value == [(0.0, 0.0), (10.0, 20.0)]


def test_parse_points_string_handles_exceptions(utils):
    class ExplodingPattern:
        def findall(self, *_args, **_kwargs):
            raise ValueError("boom")

    utils.number_pattern = ExplodingPattern()
    result = utils.parse_points_string("0,0 1,1")
    assert result.success is False
    assert "Points parsing failed" in result.errors[0]


def test_parse_style_attribute_manual(monkeypatch, utils):
    monkeypatch.setattr(module, "UTILITY_SERVICES_AVAILABLE", False)
    monkeypatch.setattr(module, "style_parser", None)
    result = utils.parse_style_attribute("fill: red; stroke : #000 ;")
    assert result.success is True
    assert result.value == {"fill": "red", "stroke": "#000"}


def test_parse_style_attribute_error_branch(utils):
    class BadStr(str):
        def split(self, *_args, **_kwargs):
            raise ValueError("split failure")

    result = utils.parse_style_attribute(BadStr("fill:red"))
    assert result.success is False
    assert "Style parsing failed" in result.errors[0]


def test_format_style_attribute_skips_empty(utils):
    assert utils.format_style_attribute({"fill": "red", "stroke": ""}) == "fill:red"
    assert utils.format_style_attribute({}) == ""


def test_parse_transform_attribute_all_variants(utils):
    transform_str = (
        "matrix(1,0,0,1,5,6) translate(10,20) scale(2,3) "
        "rotate(45 1 2) skewX(10) skewY(-5)"
    )
    result = utils.parse_transform_attribute(transform_str)
    types = {item["type"] for item in result.value}
    assert types == {"matrix", "translate", "scale", "rotate", "skewX", "skewY"}


def test_parse_transform_attribute_collects_errors(monkeypatch, utils):
    original = utils._parse_transform_match

    def faulty(func_name, match):
        if func_name == "scale":
            raise ValueError("bad scale")
        return original(func_name, match)

    monkeypatch.setattr(utils, "_parse_transform_match", faulty)
    result = utils.parse_transform_attribute("scale(2) translate(1,2)")
    assert "Failed to parse scale" in result.errors[0]


def test_format_transform_attribute_round_trip(utils):
    transforms = [
        {"type": "matrix", "a": 1, "b": 0, "c": 0, "d": 1, "e": 5.5, "f": 6.25},
        {"type": "translate", "tx": 10, "ty": 0},
        {"type": "translate", "tx": 10, "ty": 20},
        {"type": "scale", "sx": 2, "sy": 3},
        {"type": "rotate", "angle": 90, "cx": 1, "cy": 2},
        {"type": "skewX", "angle": 15},
        {"type": "skewY", "angle": -10},
    ]
    result = utils.format_transform_attribute(transforms)
    assert result == (
        "matrix(1,0,0,1,5.5,6.25) translate(10) translate(10,20) "
        "scale(2,3) rotate(90 1 2) skewX(15) skewY(-10)"
    )


def test_parse_dimension_value_variants(utils):
    percent = utils.parse_dimension_value("25%")
    pixels = utils.parse_dimension_value("100px")
    plain = utils.parse_dimension_value("42")
    assert percent.success and percent.value == 25.0
    assert pixels.success and pixels.value == 100.0
    assert plain.success and plain.value == 42.0


def test_parse_dimension_value_failure(utils):
    result = utils.parse_dimension_value("invalid")
    assert result.success is False
    assert "Dimension parsing failed" in result.errors[0]


def test_optimize_numeric_precision(utils):
    text = "Move 10.0000,20.5000 to 1000000 and 0.0004"
    optimized = utils.optimize_numeric_precision(text, precision=2)
    assert optimized == "Move 10,20.5 to 1000000 and 0"


def test_validate_element_attribute_scenarios(utils):
    element = ET.Element("rect", attrib={"width": "100.5", "title": "  Label "})
    numeric_result = utils.validate_element_attribute(element, "width", float)
    text_result = utils.validate_element_attribute(element, "title", str)
    missing_result = utils.validate_element_attribute(element, "height", float)
    element.set("height", "oops")
    invalid_result = utils.validate_element_attribute(element, "height", float)

    assert numeric_result.success and math.isclose(numeric_result.value, 100.5)
    assert text_result.success and text_result.value == "Label"
    assert missing_result.success is False
    assert invalid_result.success is False
    assert "Type conversion failed" in invalid_result.errors[0]
