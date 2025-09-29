#!/usr/bin/env python3
"""
Unit tests for matrix composer functions
"""

import pytest
import numpy as np
from lxml import etree as ET
from src.transforms.matrix_composer import (
    parse_viewbox, parse_preserve_aspect_ratio, get_alignment_factors,
    viewport_matrix, parse_transform, element_ctm,
    normalise_content_matrix, needs_normalise, on_slide
)


class TestParseViewBox:
    """Test viewBox parsing functionality."""

    def test_parse_viewbox_standard(self):
        """Test parsing standard viewBox."""
        svg = '<svg viewBox="0 0 100 50"></svg>'
        element = ET.fromstring(svg)
        result = parse_viewbox(element)
        assert result == (0.0, 0.0, 100.0, 50.0)

    def test_parse_viewbox_with_offset(self):
        """Test parsing viewBox with offset."""
        svg = '<svg viewBox="10 20 100 50"></svg>'
        element = ET.fromstring(svg)
        result = parse_viewbox(element)
        assert result == (10.0, 20.0, 100.0, 50.0)

    def test_parse_viewbox_with_commas(self):
        """Test parsing viewBox with comma separators."""
        svg = '<svg viewBox="0,0,100,50"></svg>'
        element = ET.fromstring(svg)
        result = parse_viewbox(element)
        assert result == (0.0, 0.0, 100.0, 50.0)

    def test_parse_viewbox_mixed_separators(self):
        """Test parsing viewBox with mixed separators."""
        svg = '<svg viewBox="0, 0 100,50"></svg>'
        element = ET.fromstring(svg)
        result = parse_viewbox(element)
        assert result == (0.0, 0.0, 100.0, 50.0)

    def test_parse_viewbox_missing_fallback(self):
        """Test fallback to width/height when viewBox missing."""
        svg = '<svg width="200" height="100"></svg>'
        element = ET.fromstring(svg)
        result = parse_viewbox(element)
        assert result == (0.0, 0.0, 200.0, 100.0)

    def test_parse_viewbox_invalid_values(self):
        """Test error handling for invalid viewBox."""
        svg = '<svg viewBox="0 0 0 50"></svg>'  # Zero width
        element = ET.fromstring(svg)
        with pytest.raises(ValueError, match="width and height must be positive"):
            parse_viewbox(element)

    def test_parse_viewbox_wrong_count(self):
        """Test error handling for wrong number of values."""
        svg = '<svg viewBox="0 0 100"></svg>'  # Only 3 values
        element = ET.fromstring(svg)
        with pytest.raises(ValueError, match="must have 4 values"):
            parse_viewbox(element)


class TestPreserveAspectRatio:
    """Test preserveAspectRatio parsing."""

    def test_parse_par_default(self):
        """Test default preserveAspectRatio."""
        svg = '<svg></svg>'
        element = ET.fromstring(svg)
        alignment, meet_slice = parse_preserve_aspect_ratio(element)
        assert alignment == "xmidymid"
        assert meet_slice == "meet"

    def test_parse_par_explicit(self):
        """Test explicit preserveAspectRatio values."""
        svg = '<svg preserveAspectRatio="xMinYMin slice"></svg>'
        element = ET.fromstring(svg)
        alignment, meet_slice = parse_preserve_aspect_ratio(element)
        assert alignment == "xminymin"
        assert meet_slice == "slice"

    def test_parse_par_none(self):
        """Test preserveAspectRatio="none"."""
        svg = '<svg preserveAspectRatio="none"></svg>'
        element = ET.fromstring(svg)
        alignment, meet_slice = parse_preserve_aspect_ratio(element)
        assert alignment == "none"
        assert meet_slice == "meet"

    def test_get_alignment_factors(self):
        """Test alignment factor calculation."""
        assert get_alignment_factors("xminymin") == (0.0, 0.0)
        assert get_alignment_factors("xmidymid") == (0.5, 0.5)
        assert get_alignment_factors("xmaxymax") == (1.0, 1.0)
        assert get_alignment_factors("invalid") == (0.5, 0.5)  # Default


class TestViewportMatrix:
    """Test viewport matrix composition."""

    def test_viewport_matrix_identity(self):
        """Test viewport matrix for identity case."""
        svg = '<svg viewBox="0 0 100 100"></svg>'
        element = ET.fromstring(svg)

        # 100x100 viewBox to 914400x914400 EMU (1" x 1")
        matrix = viewport_matrix(element, 914400, 914400)

        # Should be diagonal scaling matrix
        assert matrix[0, 0] == 9144.0  # Scale factor
        assert matrix[1, 1] == 9144.0  # Scale factor
        assert matrix[0, 2] == 0.0     # No X offset
        assert matrix[1, 2] == 0.0     # No Y offset

    def test_viewport_matrix_with_viewbox_offset(self):
        """Test viewport matrix with viewBox offset."""
        svg = '<svg viewBox="10 20 100 100"></svg>'
        element = ET.fromstring(svg)

        matrix = viewport_matrix(element, 914400, 914400)

        # Should translate viewBox origin to (0,0)
        assert matrix[0, 2] == -10 * 9144.0  # -10 * scale
        assert matrix[1, 2] == -20 * 9144.0  # -20 * scale

    def test_viewport_matrix_aspect_ratio_meet(self):
        """Test viewport matrix with aspect ratio preservation (meet)."""
        svg = '<svg viewBox="0 0 200 100" preserveAspectRatio="xMidYMid meet"></svg>'
        element = ET.fromstring(svg)

        # 2:1 aspect ratio viewBox to 1:1 slide
        matrix = viewport_matrix(element, 914400, 914400)

        # Should scale by min(sx, sy) and center
        expected_scale = 914400 / 200  # 4572 (limited by width)
        assert abs(matrix[0, 0] - expected_scale) < 1e-6
        assert abs(matrix[1, 1] - expected_scale) < 1e-6

        # Should center vertically
        expected_y_offset = (914400 - 100 * expected_scale) / 2
        assert abs(matrix[1, 2] - expected_y_offset) < 1e-6


class TestTransformParsing:
    """Test SVG transform parsing."""

    def test_parse_transform_identity(self):
        """Test identity transform (empty string)."""
        matrix = parse_transform("")
        expected = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
        np.testing.assert_array_almost_equal(matrix, expected)

    def test_parse_transform_translate(self):
        """Test translate transform."""
        matrix = parse_transform("translate(10, 20)")
        expected = np.array([[1, 0, 10], [0, 1, 20], [0, 0, 1]], dtype=float)
        np.testing.assert_array_almost_equal(matrix, expected)

    def test_parse_transform_translate_single(self):
        """Test translate with single value."""
        matrix = parse_transform("translate(15)")
        expected = np.array([[1, 0, 15], [0, 1, 0], [0, 0, 1]], dtype=float)
        np.testing.assert_array_almost_equal(matrix, expected)

    def test_parse_transform_scale(self):
        """Test scale transform."""
        matrix = parse_transform("scale(2, 3)")
        expected = np.array([[2, 0, 0], [0, 3, 0], [0, 0, 1]], dtype=float)
        np.testing.assert_array_almost_equal(matrix, expected)

    def test_parse_transform_scale_uniform(self):
        """Test uniform scale transform."""
        matrix = parse_transform("scale(2)")
        expected = np.array([[2, 0, 0], [0, 2, 0], [0, 0, 1]], dtype=float)
        np.testing.assert_array_almost_equal(matrix, expected)

    def test_parse_transform_matrix(self):
        """Test matrix transform."""
        matrix = parse_transform("matrix(1, 0, 0, 1, 10, 20)")
        expected = np.array([[1, 0, 10], [0, 1, 20], [0, 0, 1]], dtype=float)
        np.testing.assert_array_almost_equal(matrix, expected)

    def test_parse_transform_multiple(self):
        """Test multiple transforms composition."""
        matrix = parse_transform("translate(10, 20) scale(2)")

        # Should be translate @ scale (in that order)
        translate = np.array([[1, 0, 10], [0, 1, 20], [0, 0, 1]], dtype=float)
        scale = np.array([[2, 0, 0], [0, 2, 0], [0, 0, 1]], dtype=float)
        expected = translate @ scale

        np.testing.assert_array_almost_equal(matrix, expected)


class TestElementCTM:
    """Test Current Transformation Matrix calculation."""

    def test_element_ctm_with_parent(self):
        """Test CTM composition with parent."""
        parent_ctm = np.array([[2, 0, 10], [0, 2, 20], [0, 0, 1]], dtype=float)
        viewport_ctm = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)

        svg = '<g transform="translate(5, 10)"></g>'
        element = ET.fromstring(svg)

        result = element_ctm(element, parent_ctm, viewport_ctm)

        # Should be parent @ local
        local = np.array([[1, 0, 5], [0, 1, 10], [0, 0, 1]], dtype=float)
        expected = parent_ctm @ local

        np.testing.assert_array_almost_equal(result, expected)

    def test_element_ctm_root(self):
        """Test CTM composition for root element."""
        viewport_ctm = np.array([[9144, 0, 0], [0, 9144, 0], [0, 0, 1]], dtype=float)

        svg = '<g transform="translate(1, 2)"></g>'
        element = ET.fromstring(svg)

        result = element_ctm(element, None, viewport_ctm)

        # Should be viewport @ local
        local = np.array([[1, 0, 1], [0, 1, 2], [0, 0, 1]], dtype=float)
        expected = viewport_ctm @ local

        np.testing.assert_array_almost_equal(result, expected)


class TestNormalization:
    """Test content normalization functions."""

    def test_normalise_content_matrix(self):
        """Test normalization matrix creation."""
        matrix = normalise_content_matrix(-100, -50)
        expected = np.array([[1, 0, 100], [0, 1, 50], [0, 0, 1]], dtype=float)
        np.testing.assert_array_almost_equal(matrix, expected)

    def test_on_slide_bounds_checking(self):
        """Test on-slide bounds checking."""
        slide_w, slide_h = 9144000, 6858000  # Standard slide

        # Shape fully on slide
        assert on_slide(1000000, 1000000, 1000000, 1000000, slide_w, slide_h) is True

        # Shape completely off slide
        assert on_slide(-2000000, -2000000, 1000000, 1000000, slide_w, slide_h) is False

        # Shape partially on slide (within margin)
        assert on_slide(-40000, -40000, 1000000, 1000000, slide_w, slide_h) is True


class TestDTDALogoCase:
    """Test specific cases for DTDA logo pattern."""

    def test_dtda_logo_transform_pattern(self):
        """Test transform parsing for DTDA logo pattern."""
        # DTDA logo uses translate(509.85 466.99)
        matrix = parse_transform("translate(509.85 466.99)")
        expected = np.array([[1, 0, 509.85], [0, 1, 466.99], [0, 0, 1]], dtype=float)
        np.testing.assert_array_almost_equal(matrix, expected)

    def test_dtda_viewbox_pattern(self):
        """Test viewBox parsing for DTDA logo pattern."""
        svg = '<svg viewBox="0 0 174.58 42.967"></svg>'
        element = ET.fromstring(svg)
        result = parse_viewbox(element)
        assert result == (0.0, 0.0, 174.58, 42.967)

    def test_performance_matrix_composition(self):
        """Test matrix composition performance for large transform chains."""
        import time

        # Create a complex transform chain
        transforms = [
            "translate(100, 200)",
            "scale(1.5)",
            "rotate(45)",
            "translate(50, -30)",
            "scale(0.8, 1.2)"
        ]

        start_time = time.time()

        # Compose 1000 times (stress test)
        for _ in range(1000):
            for transform_str in transforms:
                matrix = parse_transform(transform_str)

        end_time = time.time()
        elapsed = end_time - start_time

        # Should complete within reasonable time (<100ms for 1000 iterations)
        assert elapsed < 0.1, f"Matrix composition too slow: {elapsed:.3f}s"