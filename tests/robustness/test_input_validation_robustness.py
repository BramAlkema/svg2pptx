#!/usr/bin/env python3
"""
Property-Based Robustness Tests for Input Validation

Uses Hypothesis for property-based testing to validate input validation
framework against arbitrary inputs and edge cases.
"""

import pytest
import math

# Import hypothesis for property-based testing
try:
    from hypothesis import given, strategies as st, settings, example
    from hypothesis import Verbosity, HealthCheck
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False

from core.utils.input_validator import (
    InputValidator,
    ValidationContext,
    ValidationError,
    NumericOverflowError,
    UnitConversionError,
    AttributeSanitizationError
)


# Skip all tests if hypothesis is not available
pytestmark = pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="Hypothesis not available")


@given(st.text(max_size=100))
@settings(max_examples=50, deadline=1000, suppress_health_check=[HealthCheck.too_slow])
def test_length_parsing_never_crashes(length_str):
    """Test that length parsing never crashes on arbitrary input."""
    validator = InputValidator()
    try:
        result = validator.parse_length_safe(length_str)

        # Should either return None or valid number
        assert result is None or isinstance(result, (int, float))

        # If result is a number, should be reasonable (not infinite or NaN)
        if isinstance(result, (int, float)):
            assert not (math.isnan(result) or math.isinf(result))
            assert -1e20 < result < 1e20  # Reasonable bounds

    except (ValidationError, NumericOverflowError, UnitConversionError):
        # These exceptions are acceptable for invalid/extreme inputs
        pass
    except Exception as e:
        pytest.fail(f"Unexpected exception for length parsing '{length_str}': {e}")


@given(st.text(max_size=100))
@settings(max_examples=50, deadline=1000)
def test_numeric_parsing_never_crashes(numeric_str):
    """Test that numeric parsing never crashes on arbitrary input."""
    validator = InputValidator()
    try:
        result = validator.parse_numeric_safe(numeric_str)

        # Should either return None or valid number
        assert result is None or isinstance(result, (int, float))

        # If result is a number, should be finite
        if isinstance(result, (int, float)):
            assert not (math.isnan(result) or math.isinf(result))

    except (ValidationError, NumericOverflowError):
        # These exceptions are acceptable
        pass
    except Exception as e:
        pytest.fail(f"Unexpected exception for numeric parsing '{numeric_str}': {e}")


@given(st.dictionaries(
    keys=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
                min_size=1, max_size=20),
    values=st.text(max_size=100),
    max_size=5
))
@settings(max_examples=25, deadline=2000)
def test_svg_attributes_robustness(attributes):
    """Test SVG attribute validation with arbitrary attributes."""
    validator = InputValidator()
    try:
        result = validator.validate_svg_attributes(attributes)

        # Should always return a dictionary
        assert isinstance(result, dict)

        # All keys and values should be strings
        for key, value in result.items():
            assert isinstance(key, str)
            assert isinstance(value, str)

            # Values should not contain obvious dangerous content
            assert '<script>' not in value.lower()
            assert 'javascript:' not in value.lower()

    except AttributeSanitizationError:
        # Acceptable in strict mode
        pass
    except Exception as e:
        pytest.fail(f"Unexpected exception for attribute validation: {e}")


@given(st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126),
               max_size=100))
@settings(max_examples=30)
def test_viewbox_parsing_robustness(viewbox_str):
    """Test viewBox parsing with arbitrary strings."""
    validator = InputValidator()
    try:
        result = validator.validate_viewbox(viewbox_str)

        # Should either return None or valid tuple
        assert result is None or (
            isinstance(result, tuple) and
            len(result) == 4 and
            all(isinstance(v, (int, float)) for v in result)
        )

        # If valid, width and height should be positive
        if result is not None:
            min_x, min_y, width, height = result
            assert width > 0
            assert height > 0
            assert all(not (math.isnan(v) or math.isinf(v)) for v in result)

    except Exception as e:
        pytest.fail(f"Unexpected exception for viewBox parsing '{viewbox_str}': {e}")


@given(st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126),
               max_size=100))
@settings(max_examples=30)
def test_transform_validation_robustness(transform_str):
    """Test transform validation with arbitrary strings."""
    validator = InputValidator()
    try:
        result = validator.validate_transform_list(transform_str)

        # Should always return a boolean
        assert isinstance(result, bool)

    except Exception as e:
        pytest.fail(f"Unexpected exception for transform validation '{transform_str}': {e}")


@given(st.text().filter(lambda x: any(c in x for c in '<>"\'&')))
@settings(max_examples=30)
def test_html_injection_prevention(potentially_malicious):
    """Test prevention of HTML injection attempts."""
    validator = InputValidator()
    try:
        attrs = {"test_attr": potentially_malicious}
        result = validator.validate_svg_attributes(attrs)

        # Any returned value should be safe
        for key, value in result.items():
            if value:
                # Should not contain obvious HTML injection patterns
                assert not any(pattern in value.lower() for pattern in [
                    '<script', '</script>', 'javascript:', 'data:text/html'
                ])
                # Should not be identical to the original malicious content
                if value == potentially_malicious and any(pattern in value.lower() for pattern in ['<script', 'javascript:']):
                    pytest.fail(f"Dangerous content not sanitized: {value}")

    except Exception as e:
        pytest.fail(f"Unexpected exception for HTML injection test: {e}")


@given(st.floats(min_value=0.1, max_value=1000, allow_nan=False, allow_infinity=False),
       st.floats(min_value=1, max_value=100, allow_nan=False, allow_infinity=False),
       st.floats(min_value=100, max_value=5000, allow_nan=False, allow_infinity=False),
       st.floats(min_value=100, max_value=5000, allow_nan=False, allow_infinity=False))
@settings(max_examples=10)
def test_context_configuration_robustness(dpi, font_size, viewport_w, viewport_h):
    """Test validation with various context configurations."""
    try:
        context = ValidationContext(
            default_dpi=dpi,
            default_font_size=font_size,
            viewport_width=viewport_w,
            viewport_height=viewport_h
        )

        validator = InputValidator(context)

        # Should be able to parse relative units
        em_result = validator.parse_length_safe("2em")
        vw_result = validator.parse_length_safe("10vw")
        vh_result = validator.parse_length_safe("20vh")

        # Results should be proportional to context values
        if em_result is not None:
            assert em_result == pytest.approx(2 * font_size, rel=0.01)

        if vw_result is not None:
            assert vw_result == pytest.approx(10 * viewport_w / 100, rel=0.01)

        if vh_result is not None:
            assert vh_result == pytest.approx(20 * viewport_h / 100, rel=0.01)

    except Exception as e:
        pytest.fail(f"Unexpected exception with context configuration: {e}")


if __name__ == "__main__":
    if HYPOTHESIS_AVAILABLE:
        pytest.main([__file__, "-v", "--tb=short"])
    else:
        print("Hypothesis not available - skipping property-based tests")
        print("Install with: pip install hypothesis")