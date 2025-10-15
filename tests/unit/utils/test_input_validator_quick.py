#!/usr/bin/env python3
import pytest

from core.utils.input_validator import (
    AttributeSanitizationError,
    InputValidator,
    NumericOverflowError,
    ValidationContext,
)


def test_parse_length_safe_handles_absolute_and_relative_units():
    validator = InputValidator()
    assert validator.parse_length_safe("2cm") == pytest.approx(2 * (96.0 / 2.54))
    assert validator.parse_length_safe("10EM") == pytest.approx(160.0)
    assert validator.parse_length_safe("50%") == pytest.approx(50.0)
    assert validator.parse_length_safe("invalid") is None


def test_parse_length_safe_respects_numeric_bounds():
    validator = InputValidator(ValidationContext(max_numeric_value=10, min_numeric_value=-10))
    assert validator.parse_length_safe("5px") == pytest.approx(5.0)
    with pytest.raises(NumericOverflowError):
        validator.parse_length_safe("11px")
    with pytest.raises(NumericOverflowError):
        validator.parse_length_safe("-11px")


def test_parse_numeric_safe_with_bounds():
    validator = InputValidator()
    assert validator.parse_numeric_safe("42.5", min_val=0, max_val=100) == pytest.approx(42.5)
    assert validator.parse_numeric_safe("bad-value", min_val=0, max_val=100) is None
    with pytest.raises(NumericOverflowError):
        validator.parse_numeric_safe("200", min_val=0, max_val=100)


def test_validate_svg_attributes_sanitizes_and_blocks_scripts():
    validator = InputValidator()
    attrs = {
        "width": "100",
        "onload": "alert(1)",
        "href": "javascript:alert(1)",
        "data-url": "data:text/html;base64,PHNjcmlwdD5hbGVydCgpfTwvc2NyaXB0Pg==",
        "title": "<script>alert(2)</script>",
    }
    sanitized = validator.validate_svg_attributes(attrs)
    assert sanitized["width"] == "100.0"
    assert "onload" not in sanitized
    assert "href" not in sanitized
    assert sanitized.get("data-url") == "data:text/html;base64,PHNjcmlwdD5hbGVydCgpfTwvc2NyaXB0Pg=="
    assert "title" not in sanitized


def test_validate_svg_attributes_strict_mode_raises(monkeypatch):
    validator = InputValidator(ValidationContext(strict_mode=True))

    def boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(validator, "_sanitize_attribute_value", boom)
    with pytest.raises(AttributeSanitizationError):
        validator.validate_svg_attributes({"fill": "red"})
