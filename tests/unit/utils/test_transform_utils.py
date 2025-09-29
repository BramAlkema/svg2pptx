#!/usr/bin/env python3
"""
Unit tests for transform utilities
"""

import pytest
from lxml import etree as ET
from core.utils.transform_utils import (
    get_transform_safe, has_transform_safe,
    parse_transform_safe, get_attribute_safe, has_attribute_safe
)


class TestTransformUtils:
    """Test safe transform utility functions."""

    def test_get_transform_safe_valid(self):
        """Test get_transform_safe with valid transform."""
        svg = '<g transform="translate(10 20)"></g>'
        element = ET.fromstring(svg)
        result = get_transform_safe(element)
        assert result == "translate(10 20)"

    def test_get_transform_safe_empty(self):
        """Test get_transform_safe with empty transform."""
        svg = '<g transform=""></g>'
        element = ET.fromstring(svg)
        result = get_transform_safe(element)
        assert result is None

    def test_get_transform_safe_whitespace(self):
        """Test get_transform_safe with whitespace-only transform."""
        svg = '<g transform="   "></g>'
        element = ET.fromstring(svg)
        result = get_transform_safe(element)
        assert result is None

    def test_get_transform_safe_none_element(self):
        """Test get_transform_safe with None element."""
        result = get_transform_safe(None)
        assert result is None

    def test_get_transform_safe_no_attribute(self):
        """Test get_transform_safe with no transform attribute."""
        svg = '<g></g>'
        element = ET.fromstring(svg)
        result = get_transform_safe(element)
        assert result is None

    def test_has_transform_safe_true(self):
        """Test has_transform_safe returns True for valid transform."""
        svg = '<g transform="matrix(1 0 0 1 0 0)"></g>'
        element = ET.fromstring(svg)
        result = has_transform_safe(element)
        assert result is True

    def test_has_transform_safe_false(self):
        """Test has_transform_safe returns False for no transform."""
        svg = '<g></g>'
        element = ET.fromstring(svg)
        result = has_transform_safe(element)
        assert result is False

    def test_parse_transform_safe_valid(self):
        """Test parse_transform_safe with valid transform string."""
        result = parse_transform_safe("translate(10 20)")
        assert result == "translate(10 20)"

    def test_parse_transform_safe_invalid(self):
        """Test parse_transform_safe with invalid transform string."""
        result = parse_transform_safe("invalid_transform")
        assert result is None

    def test_parse_transform_safe_none(self):
        """Test parse_transform_safe with None input."""
        result = parse_transform_safe(None)
        assert result is None

    def test_parse_transform_safe_empty(self):
        """Test parse_transform_safe with empty string."""
        result = parse_transform_safe("")
        assert result is None

    def test_get_attribute_safe_present(self):
        """Test get_attribute_safe with present attribute."""
        svg = '<rect x="10" y="20"></rect>'
        element = ET.fromstring(svg)
        result = get_attribute_safe(element, 'x')
        assert result == "10"

    def test_get_attribute_safe_missing(self):
        """Test get_attribute_safe with missing attribute."""
        svg = '<rect x="10"></rect>'
        element = ET.fromstring(svg)
        result = get_attribute_safe(element, 'y', 'default')
        assert result == "default"

    def test_get_attribute_safe_none_element(self):
        """Test get_attribute_safe with None element."""
        result = get_attribute_safe(None, 'x', 'default')
        assert result == "default"

    def test_has_attribute_safe_true(self):
        """Test has_attribute_safe returns True for present attribute."""
        svg = '<rect fill="red"></rect>'
        element = ET.fromstring(svg)
        result = has_attribute_safe(element, 'fill')
        assert result is True

    def test_has_attribute_safe_false(self):
        """Test has_attribute_safe returns False for missing attribute."""
        svg = '<rect></rect>'
        element = ET.fromstring(svg)
        result = has_attribute_safe(element, 'fill')
        assert result is False

    def test_has_attribute_safe_none_element(self):
        """Test has_attribute_safe with None element."""
        result = has_attribute_safe(None, 'fill')
        assert result is False

    def test_cython_crash_prevention(self):
        """Test that functions prevent cython membership crashes."""
        # This test ensures we're using .get() instead of 'in' operations
        svg = '<g transform="translate(100 200)"></g>'
        element = ET.fromstring(svg)

        # These should not raise "argument of type 'cython_function_or_method' is not iterable"
        try:
            result1 = has_transform_safe(element)
            result2 = get_transform_safe(element)
            result3 = has_attribute_safe(element, 'transform')
            result4 = get_attribute_safe(element, 'transform')

            assert result1 is True
            assert result2 == "translate(100 200)"
            assert result3 is True
            assert result4 == "translate(100 200)"

        except TypeError as e:
            if "not iterable" in str(e):
                pytest.fail("Cython crash occurred - membership test used instead of .get()")
            else:
                raise