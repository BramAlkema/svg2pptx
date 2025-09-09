#!/usr/bin/env python3
"""
Unit tests for units module functionality.

Tests the Universal Unit Converter including unit parsing, EMU conversions,
viewport context handling, and DPI detection.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import sys
import math

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.units import (
    UnitConverter, ViewportContext, UnitType,
    EMU_PER_INCH, EMU_PER_POINT, EMU_PER_MM, EMU_PER_CM,
    DEFAULT_DPI, PRINT_DPI, HIGH_DPI,
    to_emu, to_pixels, create_context, parse_length
)


class TestUnitType:
    """Test UnitType enum."""
    
    def test_unit_type_values(self):
        """Test unit type enum values."""
        assert UnitType.PIXEL.value == "px"
        assert UnitType.POINT.value == "pt"
        assert UnitType.MILLIMETER.value == "mm"
        assert UnitType.CENTIMETER.value == "cm"
        assert UnitType.INCH.value == "in"
        assert UnitType.EM.value == "em"
        assert UnitType.EX.value == "ex"
        assert UnitType.PERCENT.value == "%"
        assert UnitType.VIEWPORT_WIDTH.value == "vw"
        assert UnitType.VIEWPORT_HEIGHT.value == "vh"
        assert UnitType.UNITLESS.value == ""


class TestViewportContext:
    """Test ViewportContext dataclass."""
    
    def test_default_viewport_context(self):
        """Test default viewport context creation."""
        context = ViewportContext()
        
        assert context.width == 800.0
        assert context.height == 600.0
        assert context.font_size == 16.0
        assert context.x_height == 8.0
        assert context.dpi == DEFAULT_DPI
        assert context.parent_width is None
        assert context.parent_height is None
    
    def test_custom_viewport_context(self):
        """Test custom viewport context creation."""
        context = ViewportContext(
            width=1200.0,
            height=800.0,
            font_size=14.0,
            x_height=7.0,
            dpi=PRINT_DPI,
            parent_width=500.0,
            parent_height=400.0
        )
        
        assert context.width == 1200.0
        assert context.height == 800.0
        assert context.font_size == 14.0
        assert context.x_height == 7.0
        assert context.dpi == PRINT_DPI
        assert context.parent_width == 500.0
        assert context.parent_height == 400.0


class TestUnitConverter:
    """Test UnitConverter functionality."""
    
    def test_unit_converter_init_default(self):
        """Test default unit converter initialization."""
        converter = UnitConverter()
        
        assert converter.default_context.width == 800.0
        assert converter.default_context.height == 600.0
        assert converter.default_context.font_size == 16.0
        assert converter.default_context.dpi == DEFAULT_DPI
    
    def test_unit_converter_init_custom(self):
        """Test custom unit converter initialization."""
        converter = UnitConverter(
            default_dpi=PRINT_DPI,
            viewport_width=1024.0,
            viewport_height=768.0,
            default_font_size=14.0
        )
        
        assert converter.default_context.width == 1024.0
        assert converter.default_context.height == 768.0
        assert converter.default_context.font_size == 14.0
        assert converter.default_context.dpi == PRINT_DPI
    
    def test_parse_length_pixels(self):
        """Test parsing pixel values."""
        converter = UnitConverter()
        
        value, unit = converter.parse_length("100px")
        assert value == 100.0
        assert unit == UnitType.PIXEL
        
        value, unit = converter.parse_length("50.5px")
        assert value == 50.5
        assert unit == UnitType.PIXEL
    
    def test_parse_length_points(self):
        """Test parsing point values."""
        converter = UnitConverter()
        
        value, unit = converter.parse_length("72pt")
        assert value == 72.0
        assert unit == UnitType.POINT
    
    def test_parse_length_inches(self):
        """Test parsing inch values."""
        converter = UnitConverter()
        
        value, unit = converter.parse_length("1in")
        assert value == 1.0
        assert unit == UnitType.INCH
    
    def test_parse_length_millimeters(self):
        """Test parsing millimeter values."""
        converter = UnitConverter()
        
        value, unit = converter.parse_length("25.4mm")
        assert value == 25.4
        assert unit == UnitType.MILLIMETER
    
    def test_parse_length_centimeters(self):
        """Test parsing centimeter values."""
        converter = UnitConverter()
        
        value, unit = converter.parse_length("2.54cm")
        assert value == 2.54
        assert unit == UnitType.CENTIMETER
    
    def test_parse_length_em(self):
        """Test parsing em values."""
        converter = UnitConverter()
        
        value, unit = converter.parse_length("2em")
        assert value == 2.0
        assert unit == UnitType.EM
    
    def test_parse_length_ex(self):
        """Test parsing ex values."""
        converter = UnitConverter()
        
        value, unit = converter.parse_length("1.5ex")
        assert value == 1.5
        assert unit == UnitType.EX
    
    def test_parse_length_percent(self):
        """Test parsing percentage values."""
        converter = UnitConverter()
        
        value, unit = converter.parse_length("50%")
        assert value == 0.5  # Converted to decimal
        assert unit == UnitType.PERCENT
        
        value, unit = converter.parse_length("100%")
        assert value == 1.0
        assert unit == UnitType.PERCENT
    
    def test_parse_length_viewport_units(self):
        """Test parsing viewport units."""
        converter = UnitConverter()
        
        value, unit = converter.parse_length("50vw")
        assert value == 50.0
        assert unit == UnitType.VIEWPORT_WIDTH
        
        value, unit = converter.parse_length("75vh")
        assert value == 75.0
        assert unit == UnitType.VIEWPORT_HEIGHT
    
    def test_parse_length_unitless(self):
        """Test parsing unitless values."""
        converter = UnitConverter()
        
        # Numeric input
        value, unit = converter.parse_length(100)
        assert value == 100.0
        assert unit == UnitType.UNITLESS
        
        # String without unit
        value, unit = converter.parse_length("50")
        assert value == 50.0
        assert unit == UnitType.UNITLESS
    
    def test_parse_length_invalid(self):
        """Test parsing invalid values."""
        converter = UnitConverter()
        
        value, unit = converter.parse_length("")
        assert value == 0.0
        assert unit == UnitType.UNITLESS
        
        value, unit = converter.parse_length("invalid")
        assert value == 0.0
        assert unit == UnitType.UNITLESS
        
        value, unit = converter.parse_length(None)
        assert value == 0.0
        assert unit == UnitType.UNITLESS
    
    def test_to_emu_pixels(self):
        """Test EMU conversion for pixels."""
        converter = UnitConverter()
        context = ViewportContext(dpi=96.0)
        
        # 100 pixels at 96 DPI = 100 * 9525 EMU
        emu = converter.to_emu("100px", context)
        expected = int(100 * EMU_PER_INCH / 96.0)
        assert emu == expected
    
    def test_to_emu_points(self):
        """Test EMU conversion for points."""
        converter = UnitConverter()
        
        emu = converter.to_emu("72pt")
        expected = int(72 * EMU_PER_POINT)
        assert emu == expected
    
    def test_to_emu_inches(self):
        """Test EMU conversion for inches."""
        converter = UnitConverter()
        
        emu = converter.to_emu("1in")
        assert emu == EMU_PER_INCH
    
    def test_to_emu_millimeters(self):
        """Test EMU conversion for millimeters."""
        converter = UnitConverter()
        
        emu = converter.to_emu("1mm")
        assert emu == EMU_PER_MM
    
    def test_to_emu_centimeters(self):
        """Test EMU conversion for centimeters."""
        converter = UnitConverter()
        
        emu = converter.to_emu("1cm")
        assert emu == EMU_PER_CM
    
    def test_to_emu_em(self):
        """Test EMU conversion for em units."""
        converter = UnitConverter()
        context = ViewportContext(font_size=16.0, dpi=96.0)
        
        # 2em = 2 * 16px = 32px
        emu = converter.to_emu("2em", context)
        expected = int(32 * EMU_PER_INCH / 96.0)
        assert emu == expected
    
    def test_to_emu_ex(self):
        """Test EMU conversion for ex units."""
        converter = UnitConverter()
        context = ViewportContext(x_height=8.0, dpi=96.0)
        
        # 2ex = 2 * 8px = 16px
        emu = converter.to_emu("2ex", context)
        expected = int(16 * EMU_PER_INCH / 96.0)
        assert emu == expected
    
    def test_to_emu_percent(self):
        """Test EMU conversion for percentage units."""
        converter = UnitConverter()
        context = ViewportContext(width=800.0, height=600.0, dpi=96.0)
        
        # 50% of width = 400px
        emu = converter.to_emu("50%", context, axis='x')
        expected = int(400 * EMU_PER_INCH / 96.0)
        assert emu == expected
        
        # 25% of height = 150px
        emu = converter.to_emu("25%", context, axis='y')
        expected = int(150 * EMU_PER_INCH / 96.0)
        assert emu == expected
    
    def test_to_emu_percent_with_parent(self):
        """Test EMU conversion for percentage with parent dimensions."""
        converter = UnitConverter()
        context = ViewportContext(
            width=800.0, height=600.0,
            parent_width=200.0, parent_height=150.0,
            dpi=96.0
        )
        
        # 50% of parent width = 100px
        emu = converter.to_emu("50%", context, axis='x')
        expected = int(100 * EMU_PER_INCH / 96.0)
        assert emu == expected
    
    def test_to_emu_viewport_units(self):
        """Test EMU conversion for viewport units."""
        converter = UnitConverter()
        context = ViewportContext(width=800.0, height=600.0, dpi=96.0)
        
        # 50vw = 50% of viewport width = 400px
        emu = converter.to_emu("50vw", context)
        expected = int(400 * EMU_PER_INCH / 96.0)
        assert emu == expected
        
        # 25vh = 25% of viewport height = 150px
        emu = converter.to_emu("25vh", context)
        expected = int(150 * EMU_PER_INCH / 96.0)
        assert emu == expected
    
    def test_to_emu_zero_values(self):
        """Test EMU conversion for zero values."""
        converter = UnitConverter()
        
        assert converter.to_emu("0") == 0
        assert converter.to_emu("0px") == 0
        assert converter.to_emu("0pt") == 0
    
    def test_to_pixels_basic_units(self):
        """Test pixel conversion for basic units."""
        converter = UnitConverter()
        context = ViewportContext(dpi=96.0)
        
        assert converter.to_pixels("100px", context) == 100.0
        assert converter.to_pixels("72pt", context) == 96.0  # 72pt = 1in = 96px at 96 DPI
        assert converter.to_pixels("1in", context) == 96.0
        assert abs(converter.to_pixels("25.4mm", context) - 96.0) < 0.1
        assert abs(converter.to_pixels("2.54cm", context) - 96.0) < 0.1
    
    def test_to_pixels_relative_units(self):
        """Test pixel conversion for relative units."""
        converter = UnitConverter()
        context = ViewportContext(
            width=800.0, height=600.0,
            font_size=16.0, x_height=8.0
        )
        
        assert converter.to_pixels("2em", context) == 32.0
        assert converter.to_pixels("4ex", context) == 32.0
        assert converter.to_pixels("50%", context, axis='x') == 400.0
        assert converter.to_pixels("50vw", context) == 400.0
        assert converter.to_pixels("25vh", context) == 150.0
    
    def test_batch_convert(self):
        """Test batch conversion of multiple values."""
        converter = UnitConverter()
        context = ViewportContext(dpi=96.0)
        
        values = {
            'x': '10px',
            'y': '20px', 
            'width': '100px',
            'height': '50px'
        }
        
        result = converter.batch_convert(values, context)
        
        assert result['x'] == int(10 * EMU_PER_INCH / 96.0)
        assert result['y'] == int(20 * EMU_PER_INCH / 96.0)
        assert result['width'] == int(100 * EMU_PER_INCH / 96.0)
        assert result['height'] == int(50 * EMU_PER_INCH / 96.0)
    
    def test_format_emu(self):
        """Test EMU formatting."""
        converter = UnitConverter()
        
        assert converter.format_emu(914400) == "914400"
        assert converter.format_emu(0) == "0"
    
    def test_create_context_from_viewbox(self):
        """Test creating context from viewBox."""
        converter = UnitConverter()
        
        context = converter.create_context(
            viewbox=(0, 0, 200, 150)
        )
        
        assert context.width == 200.0
        assert context.height == 150.0
    
    def test_create_context_with_overrides(self):
        """Test creating context with parameter overrides."""
        converter = UnitConverter()
        
        context = converter.create_context(
            parent_dimensions=(300, 250),
            font_size=18.0,
            dpi_override=PRINT_DPI
        )
        
        assert context.parent_width == 300.0
        assert context.parent_height == 250.0
        assert context.font_size == 18.0
        assert context.x_height == 9.0  # 18 * 0.5
        assert context.dpi == PRINT_DPI
    
    def test_dpi_detection_default(self):
        """Test DPI detection with no hints."""
        converter = UnitConverter()
        
        dpi = converter._detect_dpi(None)
        assert dpi == DEFAULT_DPI
    
    def test_dpi_detection_print_hints(self):
        """Test DPI detection with print creator hints."""
        converter = UnitConverter()
        
        mock_element = Mock()
        mock_element.attrib = {'data-creator': 'Adobe Illustrator'}
        
        dpi = converter._detect_dpi(mock_element)
        assert dpi == PRINT_DPI
    
    def test_dpi_detection_web_hints(self):
        """Test DPI detection with web creator hints."""
        converter = UnitConverter()
        
        mock_element = Mock()
        mock_element.attrib = {'data-creator': 'Figma Web'}
        
        dpi = converter._detect_dpi(mock_element)
        assert dpi == DEFAULT_DPI
    
    def test_dpi_detection_high_res_dimensions(self):
        """Test DPI detection with high-resolution dimensions."""
        converter = UnitConverter()
        
        mock_element = Mock()
        mock_element.attrib = {
            'width': '2500px',
            'height': '2000px'
        }
        
        dpi = converter._detect_dpi(mock_element)
        assert dpi == HIGH_DPI
    
    def test_debug_conversion(self):
        """Test debug conversion information."""
        converter = UnitConverter()
        context = ViewportContext(dpi=96.0)
        
        debug_info = converter.debug_conversion("100px", context)
        
        assert debug_info['input'] == "100px"
        assert debug_info['parsed_value'] == 100.0
        assert debug_info['unit_type'] == "px"
        assert debug_info['pixels'] == 100.0
        assert debug_info['emu'] == int(100 * EMU_PER_INCH / 96.0)
        assert debug_info['context_dpi'] == 96.0
        assert debug_info['context_viewport'] == (800.0, 600.0)  # Default
        assert debug_info['context_font_size'] == 16.0  # Default


class TestConvenienceFunctions:
    """Test global convenience functions."""
    
    def test_to_emu_function(self):
        """Test global to_emu function."""
        emu = to_emu("100px")
        expected = int(100 * EMU_PER_INCH / DEFAULT_DPI)
        assert emu == expected
    
    def test_to_pixels_function(self):
        """Test global to_pixels function."""
        pixels = to_pixels("1in")
        assert pixels == DEFAULT_DPI  # 96 pixels per inch at default DPI
    
    def test_create_context_function(self):
        """Test global create_context function."""
        context = create_context(viewbox=(0, 0, 400, 300))
        assert context.width == 400.0
        assert context.height == 300.0
    
    def test_parse_length_function(self):
        """Test global parse_length function."""
        value, unit = parse_length("50px")
        assert value == 50.0
        assert unit == UnitType.PIXEL


class TestConstants:
    """Test module constants."""
    
    def test_emu_constants(self):
        """Test EMU conversion constants."""
        assert EMU_PER_INCH == 914400
        assert EMU_PER_POINT == 12700
        assert EMU_PER_MM == 36000
        assert EMU_PER_CM == 360000
    
    def test_dpi_constants(self):
        """Test DPI constants."""
        assert DEFAULT_DPI == 96.0
        assert PRINT_DPI == 72.0
        assert HIGH_DPI == 150.0
    
    def test_emu_relationships(self):
        """Test EMU constant relationships."""
        # 1 inch = 72 points
        assert abs(EMU_PER_INCH - (72 * EMU_PER_POINT)) < 1
        
        # 1 inch = 25.4 mm
        assert abs(EMU_PER_INCH - (25.4 * EMU_PER_MM)) < 100
        
        # 1 cm = 10 mm
        assert EMU_PER_CM == EMU_PER_MM * 10


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_scientific_notation(self):
        """Test scientific notation parsing."""
        converter = UnitConverter()
        
        value, unit = converter.parse_length("1e2px")
        assert value == 100.0
        assert unit == UnitType.PIXEL
        
        value, unit = converter.parse_length("1.5E-1em")
        assert value == 0.15
        assert unit == UnitType.EM
    
    def test_negative_values(self):
        """Test negative value handling."""
        converter = UnitConverter()
        
        emu = converter.to_emu("-10px")
        assert emu < 0
        
        pixels = converter.to_pixels("-5em")
        assert pixels < 0
    
    def test_very_large_values(self):
        """Test handling of very large values."""
        converter = UnitConverter()
        
        emu = converter.to_emu("1000000px")
        assert emu > 0
        assert isinstance(emu, int)
    
    def test_very_small_values(self):
        """Test handling of very small values."""
        converter = UnitConverter()
        
        emu = converter.to_emu("0.001px")
        assert isinstance(emu, int)
        
        pixels = converter.to_pixels("0.001em")
        assert isinstance(pixels, float)
    
    def test_whitespace_handling(self):
        """Test whitespace in value strings."""
        converter = UnitConverter()
        
        value, unit = converter.parse_length("  100  px  ")
        assert value == 100.0
        assert unit == UnitType.PIXEL
        
        emu = converter.to_emu("  50  pt  ")
        expected = int(50 * EMU_PER_POINT)
        assert emu == expected