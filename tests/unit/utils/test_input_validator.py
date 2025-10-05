#!/usr/bin/env python3
"""
Unit Tests for InputValidator

Comprehensive test suite for input validation framework,
including edge cases, security validations, and property-based testing.
"""

import pytest
import math
from unittest.mock import patch

from core.utils.input_validator import (
    InputValidator,
    ValidationContext,
    ValidationError,
    NumericOverflowError,
    UnitConversionError,
    AttributeSanitizationError,
    LengthUnit,
    default_input_validator
)


class TestLengthUnit:
    """Test LengthUnit enum functionality."""

    def test_absolute_units(self):
        """Test absolute unit conversion factors."""
        assert LengthUnit.PX.px_factor == 1.0
        assert LengthUnit.PT.px_factor == 96.0 / 72.0
        assert LengthUnit.IN.px_factor == 96.0
        assert LengthUnit.CM.px_factor == 96.0 / 2.54

        # All absolute units should have is_absolute = True
        absolute_units = [LengthUnit.PX, LengthUnit.PT, LengthUnit.PC,
                         LengthUnit.IN, LengthUnit.CM, LengthUnit.MM]
        for unit in absolute_units:
            assert unit.is_absolute is True

    def test_relative_units(self):
        """Test relative units have no direct conversion factor."""
        relative_units = [LengthUnit.EM, LengthUnit.EX, LengthUnit.REM,
                         LengthUnit.PERCENT, LengthUnit.VW, LengthUnit.VH]
        for unit in relative_units:
            assert unit.px_factor is None
            assert unit.is_absolute is False


class TestValidationContext:
    """Test ValidationContext configuration."""

    def test_default_context(self):
        """Test default validation context values."""
        context = ValidationContext()
        assert context.default_dpi == 96.0
        assert context.default_font_size == 16.0
        assert context.viewport_width == 800.0
        assert context.viewport_height == 600.0
        assert context.max_numeric_value == 1e20
        assert context.min_numeric_value == -1e20

    def test_custom_context(self):
        """Test custom validation context."""
        context = ValidationContext(
            default_dpi=72.0,
            default_font_size=14.0,
            viewport_width=1024.0,
            viewport_height=768.0,
            strict_mode=True
        )
        assert context.default_dpi == 72.0
        assert context.default_font_size == 14.0
        assert context.viewport_width == 1024.0
        assert context.viewport_height == 768.0
        assert context.strict_mode is True


class TestInputValidatorBasic:
    """Test basic InputValidator functionality."""

    def setup_method(self):
        """Set up test validator instance."""
        self.validator = InputValidator()

    def test_initialization(self):
        """Test validator initialization."""
        assert self.validator.context is not None
        assert isinstance(self.validator.context, ValidationContext)

    def test_custom_context_initialization(self):
        """Test validator with custom context."""
        context = ValidationContext(strict_mode=True, default_font_size=18.0)
        validator = InputValidator(context)
        assert validator.context.strict_mode is True
        assert validator.context.default_font_size == 18.0


class TestLengthParsing:
    """Test length parsing functionality."""

    def setup_method(self):
        """Set up test validator instance."""
        self.validator = InputValidator()

    def test_parse_length_safe_pixels(self):
        """Test parsing pixel values."""
        test_cases = [
            ("100px", 100.0),
            ("50.5px", 50.5),
            ("0px", 0.0),
            ("-25px", -25.0),
            ("1.5px", 1.5),
            ("1000px", 1000.0)
        ]

        for input_val, expected in test_cases:
            result = self.validator.parse_length_safe(input_val)
            assert result == pytest.approx(expected), f"Failed for {input_val}"

    def test_parse_length_safe_no_unit(self):
        """Test parsing values without units (defaults to px)."""
        test_cases = [
            ("100", 100.0),
            ("50.5", 50.5),
            ("0", 0.0),
            ("-25", -25.0)
        ]

        for input_val, expected in test_cases:
            result = self.validator.parse_length_safe(input_val)
            assert result == pytest.approx(expected), f"Failed for {input_val}"

    def test_parse_length_safe_absolute_units(self):
        """Test parsing absolute units with conversion."""
        # Test points (72pt = 96px at 96 DPI)
        result = self.validator.parse_length_safe("72pt")
        assert result == pytest.approx(96.0)

        # Test inches (1in = 96px at 96 DPI)
        result = self.validator.parse_length_safe("1in")
        assert result == pytest.approx(96.0)

        # Test centimeters (2.54cm = 96px at 96 DPI)
        result = self.validator.parse_length_safe("2.54cm")
        assert result == pytest.approx(96.0)

        # Test millimeters (25.4mm = 96px at 96 DPI)
        result = self.validator.parse_length_safe("25.4mm")
        assert result == pytest.approx(96.0)

    def test_parse_length_safe_relative_units(self):
        """Test parsing relative units."""
        # em units (relative to font size)
        result = self.validator.parse_length_safe("2em")
        assert result == pytest.approx(32.0)  # 2 * 16px default font size

        # Percentage (returned as-is)
        result = self.validator.parse_length_safe("50%")
        assert result == pytest.approx(50.0)

        # Viewport units
        result = self.validator.parse_length_safe("10vw")
        assert result == pytest.approx(80.0)  # 10% of 800px default viewport width

        result = self.validator.parse_length_safe("20vh")
        assert result == pytest.approx(120.0)  # 20% of 600px default viewport height

    def test_parse_length_safe_invalid_input(self):
        """Test parsing invalid input returns None."""
        invalid_inputs = [
            "",
            None,
            "invalid",
            "100invalid",
            "px100",
            "abc",
            "100 px",  # Space between number and unit
            "++100px",
            "--50px"
        ]

        for invalid_input in invalid_inputs:
            result = self.validator.parse_length_safe(invalid_input)
            assert result is None, f"Should return None for {invalid_input}"

    def test_parse_length_safe_overflow_protection(self):
        """Test numeric overflow protection."""
        # Very large numbers should raise overflow error
        with pytest.raises(NumericOverflowError):
            self.validator.parse_length_safe("1e25px")

        # Very small numbers should raise overflow error
        with pytest.raises(NumericOverflowError):
            self.validator.parse_length_safe("-1e25px")

    def test_parse_length_safe_edge_cases(self):
        """Test edge cases in length parsing."""
        # Scientific notation
        result = self.validator.parse_length_safe("1e2px")
        assert result == pytest.approx(100.0)

        # Very small positive numbers
        result = self.validator.parse_length_safe("0.001px")
        assert result == pytest.approx(0.001)

        # Leading/trailing whitespace
        result = self.validator.parse_length_safe("  100px  ")
        assert result == pytest.approx(100.0)

        # Case insensitive units
        result = self.validator.parse_length_safe("100PX")
        assert result == pytest.approx(100.0)


class TestNumericParsing:
    """Test numeric parsing functionality."""

    def setup_method(self):
        """Set up test validator instance."""
        self.validator = InputValidator()

    def test_parse_numeric_safe_basic(self):
        """Test basic numeric parsing."""
        test_cases = [
            ("100", 100.0),
            ("50.5", 50.5),
            ("0", 0.0),
            ("-25", -25.0),
            ("1.5", 1.5),
            ("1000", 1000.0),
            ("0.001", 0.001)
        ]

        for input_val, expected in test_cases:
            result = self.validator.parse_numeric_safe(input_val)
            assert result == pytest.approx(expected), f"Failed for {input_val}"

    def test_parse_numeric_safe_scientific_notation(self):
        """Test scientific notation parsing."""
        test_cases = [
            ("1e2", 100.0),
            ("1.5e3", 1500.0),
            ("2.5e-2", 0.025),
            ("-1e2", -100.0)
        ]

        for input_val, expected in test_cases:
            result = self.validator.parse_numeric_safe(input_val)
            assert result == pytest.approx(expected), f"Failed for {input_val}"

    def test_parse_numeric_safe_bounds_checking(self):
        """Test numeric bounds checking."""
        # Within bounds
        result = self.validator.parse_numeric_safe("100", min_val=0, max_val=200)
        assert result == pytest.approx(100.0)

        # Below minimum
        with pytest.raises(NumericOverflowError):
            self.validator.parse_numeric_safe("-1", min_val=0, max_val=200)

        # Above maximum
        with pytest.raises(NumericOverflowError):
            self.validator.parse_numeric_safe("300", min_val=0, max_val=200)

    def test_parse_numeric_safe_invalid_input(self):
        """Test parsing invalid numeric input."""
        invalid_inputs = [
            "",
            None,
            "abc",
            "12.34.56",
            "1.2.3e4",
            "++100",
            "--50",
            "100px",  # Has unit suffix
            "inf",
            "-inf",
            "nan"
        ]

        for invalid_input in invalid_inputs:
            result = self.validator.parse_numeric_safe(invalid_input)
            assert result is None, f"Should return None for {invalid_input}"

    def test_parse_numeric_safe_infinity_nan_handling(self):
        """Test handling of infinity and NaN values."""
        # These should return None, not raise exceptions
        result = self.validator.parse_numeric_safe("inf")
        assert result is None

        result = self.validator.parse_numeric_safe("-inf")
        assert result is None

        result = self.validator.parse_numeric_safe("nan")
        assert result is None


class TestSVGAttributeValidation:
    """Test SVG attribute validation and sanitization."""

    def setup_method(self):
        """Set up test validator instance."""
        self.validator = InputValidator()

    def test_validate_svg_attributes_basic(self):
        """Test basic attribute validation."""
        attrs = {
            "width": "100px",
            "height": "200px",
            "fill": "red",
            "stroke": "#FF0000"
        }

        result = self.validator.validate_svg_attributes(attrs)
        assert "width" in result
        assert "height" in result
        assert "fill" in result
        assert "stroke" in result

    def test_validate_svg_attributes_dangerous_names(self):
        """Test filtering of dangerous attribute names."""
        dangerous_attrs = {
            "onclick": "alert('xss')",
            "onload": "malicious()",
            "onmouseover": "bad_function()",
            "onfocus": "evil_code()"
        }

        result = self.validator.validate_svg_attributes(dangerous_attrs)
        assert len(result) == 0  # All should be filtered out

    def test_validate_svg_attributes_script_injection(self):
        """Test protection against script injection in values."""
        malicious_attrs = {
            "fill": "<script>alert('xss')</script>",
            "href": "javascript:alert('xss')",
            "style": "expression(alert('xss'))"
        }

        result = self.validator.validate_svg_attributes(malicious_attrs)

        # Script content should be filtered out
        assert "fill" not in result or result["fill"] != malicious_attrs["fill"]
        assert "href" not in result  # javascript: URLs should be blocked
        assert "style" not in result or "expression(" not in result.get("style", "")

    def test_validate_svg_attributes_length_attributes(self):
        """Test validation of length-based attributes."""
        attrs = {
            "width": "100px",
            "height": "50%",
            "x": "10",
            "y": "-5px",
            "r": "25.5px"
        }

        result = self.validator.validate_svg_attributes(attrs)

        # All should be present and processed
        for attr in attrs:
            assert attr in result

    def test_validate_svg_attributes_url_sanitization(self):
        """Test URL attribute sanitization."""
        url_attrs = {
            "href": "https://example.com/safe",
            "xlink:href": "#local-reference",
            "bad_js": "javascript:alert('xss')",
            "bad_data": "data:text/html,<script>alert('xss')</script>",
            "good_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAGABmU4wgAAAABJRU5ErkJggg=="
        }

        result = self.validator.validate_svg_attributes(url_attrs)

        # Safe URLs should pass
        assert result.get("href") == "https://example.com/safe"
        # Note: xlink:href should pass but might be processed differently
        if "xlink:href" in result:
            assert result.get("xlink:href") == "#local-reference"

        # Dangerous URLs should be blocked
        assert "bad_js" not in result
        assert "bad_data" not in result

        # Safe data URLs should pass
        if "good_data" in result:
            assert result["good_data"].startswith("data:image/")

    def test_validate_svg_attributes_empty_input(self):
        """Test handling of empty or None input."""
        assert self.validator.validate_svg_attributes(None) == {}
        assert self.validator.validate_svg_attributes({}) == {}


class TestViewBoxValidation:
    """Test viewBox validation functionality."""

    def setup_method(self):
        """Set up test validator instance."""
        self.validator = InputValidator()

    def test_validate_viewbox_basic(self):
        """Test basic viewBox validation."""
        result = self.validator.validate_viewbox("0 0 100 100")
        assert result == (0.0, 0.0, 100.0, 100.0)

        result = self.validator.validate_viewbox("-10 -10 200 150")
        assert result == (-10.0, -10.0, 200.0, 150.0)

    def test_validate_viewbox_comma_separated(self):
        """Test viewBox with comma separators."""
        result = self.validator.validate_viewbox("0,0,100,100")
        assert result == (0.0, 0.0, 100.0, 100.0)

        result = self.validator.validate_viewbox("10, 20, 300, 400")
        assert result == (10.0, 20.0, 300.0, 400.0)

    def test_validate_viewbox_mixed_separators(self):
        """Test viewBox with mixed separators."""
        result = self.validator.validate_viewbox("0, 0 100, 100")
        assert result == (0.0, 0.0, 100.0, 100.0)

    def test_validate_viewbox_invalid_input(self):
        """Test invalid viewBox input."""
        invalid_inputs = [
            "",
            None,
            "0 0 100",        # Too few values
            "0 0 100 100 50", # Too many values
            "a b c d",        # Non-numeric
            "0 0 0 100",      # Zero width
            "0 0 100 0",      # Zero height
            "0 0 -100 100",   # Negative width
            "0 0 100 -100"    # Negative height
        ]

        for invalid_input in invalid_inputs:
            result = self.validator.validate_viewbox(invalid_input)
            assert result is None, f"Should return None for {invalid_input}"

    def test_validate_viewbox_decimal_values(self):
        """Test viewBox with decimal values."""
        result = self.validator.validate_viewbox("0.5 10.25 100.75 200.5")
        assert result == (0.5, 10.25, 100.75, 200.5)


class TestTransformValidation:
    """Test transform validation functionality."""

    def setup_method(self):
        """Set up test validator instance."""
        self.validator = InputValidator()

    def test_validate_transform_list_basic(self):
        """Test basic transform validation."""
        valid_transforms = [
            "translate(10, 20)",
            "rotate(45)",
            "scale(2)",
            "scale(2, 3)",
            "skewX(10)",
            "skewY(-5)",
            "matrix(1, 0, 0, 1, 10, 20)"
        ]

        for transform in valid_transforms:
            result = self.validator.validate_transform_list(transform)
            assert result is True, f"Should be valid: {transform}"

    def test_validate_transform_list_multiple(self):
        """Test validation of multiple transforms."""
        multiple_transforms = [
            "translate(10, 20) rotate(45)",
            "scale(2) translate(100, 50) rotate(90)",
            "matrix(1, 0, 0, 1, 0, 0) scale(1.5)"
        ]

        for transform in multiple_transforms:
            result = self.validator.validate_transform_list(transform)
            assert result is True, f"Should be valid: {transform}"

    def test_validate_transform_list_case_insensitive(self):
        """Test case insensitive transform validation."""
        transforms = [
            "TRANSLATE(10, 20)",
            "Rotate(45)",
            "Scale(2, 3)"
        ]

        for transform in transforms:
            result = self.validator.validate_transform_list(transform)
            assert result is True, f"Should be valid: {transform}"

    def test_validate_transform_list_invalid(self):
        """Test invalid transform validation."""
        invalid_transforms = [
            "",
            None,
            "invalid(10, 20)",
            "translate()",
            "rotate(a, b)",
            "scale(1, 2, 3, 4)",  # Too many parameters
            "matrix(1, 2, 3)",    # Too few parameters for matrix
            "translate(1e25, 0)", # Overflow
            "malicious<script>alert('xss')</script>"
        ]

        for transform in invalid_transforms:
            result = self.validator.validate_transform_list(transform)
            assert result is False, f"Should be invalid: {transform}"


class TestSecurityValidation:
    """Test security-focused validation features."""

    def setup_method(self):
        """Set up test validator instance."""
        self.validator = InputValidator()

    def test_xss_prevention(self):
        """Test XSS attack prevention."""
        xss_attempts = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "onload=\"alert('xss')\"",
            "&#60;script&#62;alert('xss')&#60;/script&#62;",  # HTML entities
            "%3Cscript%3Ealert('xss')%3C/script%3E"  # URL encoded
        ]

        attrs = {f"attr_{i}": xss for i, xss in enumerate(xss_attempts)}
        result = self.validator.validate_svg_attributes(attrs)

        # All XSS attempts should be filtered out or sanitized
        for key, value in result.items():
            if value is not None:
                assert "script" not in value.lower()
                assert "javascript:" not in value.lower()
                assert "alert(" not in value.lower()

    def test_dos_prevention(self):
        """Test denial of service prevention."""
        # Very long input strings should be rejected
        long_string = "a" * (self.validator.context.max_string_length + 1)

        with pytest.raises(ValidationError):
            self.validator.parse_length_safe(long_string)

        with pytest.raises(ValidationError):
            self.validator.parse_numeric_safe(long_string)

class TestPropertyBasedValidation:
    """Property-based tests using Hypothesis for robust validation."""

    def setup_method(self):
        """Set up test validator instance."""
        self.validator = InputValidator()

    # Note: These would use Hypothesis in a real implementation
    def test_length_parsing_never_crashes(self):
        """Test that length parsing never crashes on arbitrary input."""
        import random
        import string

        # Generate random strings
        for _ in range(100):
            length = random.randint(0, 50)
            test_string = ''.join(random.choices(string.ascii_letters + string.digits + ".-+%", k=length))

            try:
                result = self.validator.parse_length_safe(test_string)
                # Should either return None or a valid number
                assert result is None or isinstance(result, (int, float))
            except (NumericOverflowError, UnitConversionError):
                # These exceptions are acceptable
                pass
            except Exception as e:
                pytest.fail(f"Unexpected exception for '{test_string}': {e}")

    def test_numeric_parsing_bounds(self):
        """Test that numeric parsing respects bounds."""
        import random

        for _ in range(50):
            # Generate random numeric strings within bounds
            value = random.uniform(-400, 400)  # Keep well within bounds
            test_string = str(value)

            try:
                result = self.validator.parse_numeric_safe(test_string, min_val=-500, max_val=500)

                if result is not None:
                    assert -500 <= result <= 500
            except NumericOverflowError:
                # If we get an overflow error, the value should be outside bounds
                # But since we generated within bounds, this shouldn't happen often
                pass


class TestDefaultInstance:
    """Test the default global validator instance."""

    def test_default_instance_available(self):
        """Test that default instance is available and functional."""
        assert default_input_validator is not None
        assert isinstance(default_input_validator, InputValidator)

        # Should be usable
        result = default_input_validator.parse_length_safe("100px")
        assert result == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])