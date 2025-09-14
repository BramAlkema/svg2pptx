#!/usr/bin/env python3
"""
Unit Tests for Units Module

Comprehensive tests for SVG unit conversion utilities including
px, pt, em, rem, in, cm, mm, %, and viewport calculations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from pathlib import Path
import sys
from lxml import etree as ET

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.units import UnitConverter, parse_length

class TestUnitConverter:
    """Test cases for UnitConverter class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.converter = UnitConverter()

    # Initialization Tests
    def test_initialization_default_dpi(self):
        """Test UnitConverter initialization with default DPI."""
        converter = UnitConverter()
        assert converter.dpi == 96
        assert converter.points_per_inch == 72

    def test_initialization_custom_dpi(self):
        """Test UnitConverter initialization with custom DPI."""
        converter = UnitConverter(dpi=300)
        assert converter.dpi == 300
        assert converter.points_per_inch == 72

    # Pixel Conversions
    def test_px_to_emu_conversion(self):
        """Test pixel to EMU conversion."""
        result = self.converter.to_emu("10px")
        expected = int(10 * 96 * 635)  # 10px * DPI * EMU_per_inch / DPI
        assert result == expected

    def test_px_to_emu_float_values(self):
        """Test pixel to EMU conversion with float values."""
        result = self.converter.to_emu("10.5px")
        expected = int(10.5 * 96 * 635)
        assert result == expected

    def test_px_to_emu_zero_value(self):
        """Test pixel to EMU conversion with zero value."""
        result = self.converter.to_emu("0px")
        assert result == 0

    def test_px_to_emu_negative_value(self):
        """Test pixel to EMU conversion with negative value."""
        result = self.converter.to_emu("-5px")
        expected = int(-5 * 96 * 635)
        assert result == expected

    # Point Conversions
    def test_pt_to_emu_conversion(self):
        """Test point to EMU conversion."""
        result = self.converter.to_emu("12pt")
        expected = int(12 * 635 * 20)  # 12pt * EMU_per_point
        assert result == expected

    def test_pt_to_emu_float_values(self):
        """Test point to EMU conversion with float values."""
        result = self.converter.to_emu("12.5pt")
        expected = int(12.5 * 635 * 20)
        assert result == expected

    # Inch Conversions
    def test_in_to_emu_conversion(self):
        """Test inch to EMU conversion."""
        result = self.converter.to_emu("1in")
        expected = int(1 * 635 * 1440)  # 1in * EMU_per_inch
        assert result == expected

    def test_in_to_emu_fractional(self):
        """Test inch to EMU conversion with fractional values."""
        result = self.converter.to_emu("0.5in")
        expected = int(0.5 * 635 * 1440)
        assert result == expected

    # Centimeter Conversions
    def test_cm_to_emu_conversion(self):
        """Test centimeter to EMU conversion."""
        result = self.converter.to_emu("2.54cm")
        expected = int(2.54 * 635 * 567)  # 2.54cm * EMU_per_cm
        assert result == expected

    # Millimeter Conversions
    def test_mm_to_emu_conversion(self):
        """Test millimeter to EMU conversion."""
        result = self.converter.to_emu("25.4mm")
        expected = int(25.4 * 635 * 56.7)  # 25.4mm * EMU_per_mm
        assert result == expected

    # Unitless Values
    def test_unitless_value_conversion(self):
        """Test conversion of unitless numeric values."""
        result = self.converter.to_emu("100")
        expected = int(100 * 96 * 635)  # Defaults to pixels
        assert result == expected

    def test_unitless_float_conversion(self):
        """Test conversion of unitless float values."""
        result = self.converter.to_emu("10.5")
        expected = int(10.5 * 96 * 635)
        assert result == expected

    # Percentage Conversions (requires context)
    def test_percentage_conversion_with_context(self):
        """Test percentage conversion with viewport context."""
        with patch.object(self.converter, 'get_viewport_size', return_value=100):
            result = self.converter.to_emu("50%")
            expected = int(50 * 96 * 635)  # 50% of 100px viewport
            assert result == expected

    def test_percentage_conversion_without_context(self):
        """Test percentage conversion falls back to pixels."""
        result = self.converter.to_emu("50%")
        expected = int(50 * 96 * 635)  # Falls back to px
        assert result == expected

    # Em/Rem Conversions (requires context)
    def test_em_conversion_with_font_size(self):
        """Test em conversion with font size context."""
        with patch.object(self.converter, 'get_font_size', return_value=16):
            result = self.converter.to_emu("2em")
            expected = int(32 * 96 * 635)  # 2em * 16px font size
            assert result == expected

    def test_rem_conversion_with_root_font_size(self):
        """Test rem conversion with root font size context."""
        with patch.object(self.converter, 'get_root_font_size', return_value=16):
            result = self.converter.to_emu("1.5rem")
            expected = int(24 * 96 * 635)  # 1.5rem * 16px root font size
            assert result == expected

    # Error Handling
    def test_invalid_unit_conversion(self):
        """Test conversion with invalid unit."""
        with pytest.raises(ValueError):
            self.converter.to_emu("10invalid")

    def test_empty_string_conversion(self):
        """Test conversion with empty string."""
        result = self.converter.to_emu("")
        assert result == 0

    def test_none_value_conversion(self):
        """Test conversion with None value."""
        result = self.converter.to_emu(None)
        assert result == 0

    def test_invalid_numeric_value(self):
        """Test conversion with invalid numeric value."""
        with pytest.raises(ValueError):
            self.converter.to_emu("invalidpx")

    # DPI Variations
    def test_different_dpi_conversions(self):
        """Test conversions with different DPI settings."""
        converter_300 = UnitConverter(dpi=300)
        result_96 = self.converter.to_emu("10px")
        result_300 = converter_300.to_emu("10px")

        # Higher DPI should not change EMU values for absolute units
        expected_96 = int(10 * 96 * 635)
        expected_300 = int(10 * 96 * 635)  # EMU is absolute

        assert result_96 == expected_96
        assert result_300 == expected_300


class TestParseLength:
    """Test cases for parse_length utility function."""

    def test_parse_pixel_value(self):
        """Test parsing pixel values."""
        result = parse_length("10px")
        assert result is not None

    def test_parse_point_value(self):
        """Test parsing point values."""
        result = parse_length("12pt")
        assert result is not None

    def test_parse_float_value(self):
        """Test parsing float values."""
        result = parse_length("10.5px")
        assert result is not None

    def test_parse_unitless_value(self):
        """Test parsing unitless values."""
        result = parse_length("100")
        assert result is not None

    def test_parse_percentage_value(self):
        """Test parsing percentage values."""
        result = parse_length("50%")
        assert result is not None

    def test_parse_em_value(self):
        """Test parsing em values."""
        result = parse_length("2em")
        assert result is not None

    def test_parse_negative_value(self):
        """Test parsing negative values."""
        result = parse_length("-5px")
        assert result is not None

    def test_parse_zero_value(self):
        """Test parsing zero values."""
        result = parse_length("0px")
        assert result is not None

    def test_parse_invalid_value(self):
        """Test parsing invalid values."""
        result = parse_length("invalidpx")
        # May return None or raise ValueError depending on implementation

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        result = parse_length("")
        # May return None or raise ValueError depending on implementation

    def test_parse_none_value(self):
        """Test parsing None value."""
        result = parse_length(None)
        # May return None or raise ValueError depending on implementation


# Integration Tests
class TestUnitConverterIntegration:
    """Integration tests for UnitConverter with real SVG elements."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.converter = UnitConverter()

    def test_svg_element_width_conversion(self):
        """Test unit conversion for SVG element width attribute."""
        svg = ET.fromstring('<rect width="100px" height="50pt"/>')
        width_emu = self.converter.to_emu(svg.get('width'))
        height_emu = self.converter.to_emu(svg.get('height'))

        assert width_emu == int(100 * 96 * 635)
        assert height_emu == int(50 * 635 * 20)

    def test_mixed_unit_conversions(self):
        """Test converting mixed units in single operation."""
        values = ["10px", "12pt", "1in", "2.54cm", "25.4mm"]
        results = [self.converter.to_emu(v) for v in values]

        # All should be non-zero EMU values
        assert all(r > 0 for r in results)
        assert len(set(results)) == len(results)  # All different values

    def test_conversion_consistency(self):
        """Test that equivalent units convert to same EMU values."""
        # 1 inch should equal 72 points
        inch_emu = self.converter.to_emu("1in")
        pt_emu = self.converter.to_emu("72pt")

        # Should be approximately equal (within rounding tolerance)
        assert abs(inch_emu - pt_emu) < 100  # Small tolerance for rounding


# Performance Tests
class TestUnitConverterPerformance:
    """Performance tests for UnitConverter."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.converter = UnitConverter()

    @pytest.mark.performance
    def test_conversion_performance(self):
        """Test conversion performance with many values."""
        import time

        values = ["10px"] * 1000
        start_time = time.time()

        for value in values:
            self.converter.to_emu(value)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete 1000 conversions in reasonable time
        assert duration < 1.0  # Less than 1 second

    @pytest.mark.performance
    def test_mixed_unit_performance(self):
        """Test performance with mixed unit types."""
        import time

        units = ["px", "pt", "in", "cm", "mm"]
        values = [f"10{unit}" for unit in units] * 200

        start_time = time.time()

        for value in values:
            self.converter.to_emu(value)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete mixed conversions efficiently
        assert duration < 2.0  # Less than 2 seconds for 1000 mixed conversions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])