#!/usr/bin/env python3
"""
Tests for FallbackHandler

Comprehensive test suite for the fallback font strategy handler,
ensuring it always succeeds and provides safe, compatible text output
in all circumstances.
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Dict, Any

# Import handler and dependencies
from core.converters.font.handlers.fallback_handler import FallbackHandler
from core.converters.font.types import HandlerResult
from core.ir import TextFrame
from core.ir.text import Run, TextAnchor
from core.ir.font_metadata import FontStrategy
from core.services.conversion_services import ConversionServices


@pytest.fixture
def mock_services():
    """Create mock ConversionServices for testing."""
    services = Mock(spec=ConversionServices)
    return services


@pytest.fixture
def sample_text_frame():
    """Create sample TextFrame for testing."""
    run = Mock(spec=Run)
    run.text = "Hello World"
    run.font_family = "Arial"
    run.font_size_pt = 12.0
    run.bold = False
    run.italic = False
    run.underline = False
    run.strike = False
    run.rgb = "000000"

    text_frame = Mock(spec=TextFrame)
    text_frame.runs = [run]
    text_frame.anchor = TextAnchor.START
    text_frame.x = 100.0
    text_frame.y = 200.0
    text_frame.width = 200.0
    text_frame.height = 50.0

    return text_frame


@pytest.fixture
def empty_text_frame():
    """Create empty TextFrame for testing."""
    text_frame = Mock(spec=TextFrame)
    text_frame.runs = []
    text_frame.x = 0.0
    text_frame.y = 0.0
    text_frame.width = 100.0
    text_frame.height = 30.0

    return text_frame


@pytest.fixture
def problematic_text_frame():
    """Create TextFrame with problematic content."""
    run1 = Mock(spec=Run)
    run1.text = "Text with\x00null\x0bchars"  # Problematic characters
    run1.font_family = "NonExistentFont"
    run1.font_size_pt = 200.0  # Very large size
    run1.rgb = "invalid_color"

    run2 = Mock(spec=Run)
    run2.text = "A" * 1500  # Very long text
    run2.font_family = ""  # Empty font
    run2.font_size_pt = 1.0  # Very small size
    run2.rgb = None

    text_frame = Mock(spec=TextFrame)
    text_frame.runs = [run1, run2]
    text_frame.x = None  # Missing position
    text_frame.y = None
    text_frame.width = None
    text_frame.height = None

    return text_frame


class TestFallbackHandlerInitialization:
    """Test handler initialization."""

    def test_initialization_with_services(self, mock_services):
        """Test handler initializes correctly with services."""
        handler = FallbackHandler(mock_services)

        assert handler.services == mock_services
        assert handler.logger is not None
        assert isinstance(handler.universal_fonts, list)
        assert 'Arial' in handler.universal_fonts
        assert isinstance(handler.safe_colors, dict)

    def test_universal_fonts_availability(self, mock_services):
        """Test universal fonts list contains safe options."""
        handler = FallbackHandler(mock_services)

        # Should contain widely available fonts
        assert 'Arial' in handler.universal_fonts
        assert 'Times New Roman' in handler.universal_fonts
        assert 'Calibri' in handler.universal_fonts

    def test_safe_colors_palette(self, mock_services):
        """Test safe colors palette is well defined."""
        handler = FallbackHandler(mock_services)

        assert 'black' in handler.safe_colors
        assert 'white' in handler.safe_colors
        assert handler.safe_colors['black'] == '000000'
        assert handler.safe_colors['white'] == 'FFFFFF'


class TestCanHandle:
    """Test can_handle method - should always return True."""

    def test_can_handle_normal_text(self, mock_services, sample_text_frame):
        """Test can_handle accepts normal text."""
        handler = FallbackHandler(mock_services)

        result = handler.can_handle(sample_text_frame, {})

        assert result is True

    def test_can_handle_empty_runs(self, mock_services, empty_text_frame):
        """Test can_handle accepts empty runs."""
        handler = FallbackHandler(mock_services)

        result = handler.can_handle(empty_text_frame, {})

        assert result is True

    def test_can_handle_problematic_text(self, mock_services, problematic_text_frame):
        """Test can_handle accepts problematic text."""
        handler = FallbackHandler(mock_services)

        result = handler.can_handle(problematic_text_frame, {})

        assert result is True

    def test_can_handle_with_exception(self, mock_services):
        """Test can_handle still returns True even with exceptions."""
        handler = FallbackHandler(mock_services)

        # Create text frame that will cause exception
        bad_text_frame = Mock()
        bad_text_frame.runs = None  # This should cause issues

        result = handler.can_handle(bad_text_frame, {})

        assert result is True  # Fallback always accepts

    def test_can_handle_various_contexts(self, mock_services, sample_text_frame):
        """Test can_handle works with various context scenarios."""
        handler = FallbackHandler(mock_services)

        contexts = [
            {},
            {'force_fallback': True},
            {'system_font_failed': True, 'wordart_failed': True, 'path_failed': True},
            {'error': 'All other strategies failed'}
        ]

        for context in contexts:
            result = handler.can_handle(sample_text_frame, context)
            assert result is True


class TestTextExtraction:
    """Test safe text content extraction."""

    def test_extract_safe_text_content_normal(self, mock_services, sample_text_frame):
        """Test text extraction from normal text frame."""
        handler = FallbackHandler(mock_services)

        result = handler._extract_safe_text_content(sample_text_frame)

        assert result == "Hello World"

    def test_extract_safe_text_content_empty_runs(self, mock_services, empty_text_frame):
        """Test text extraction from empty runs."""
        handler = FallbackHandler(mock_services)

        result = handler._extract_safe_text_content(empty_text_frame)

        assert result == "[Empty Text]"

    def test_extract_safe_text_content_multiple_runs(self, mock_services):
        """Test text extraction from multiple runs."""
        handler = FallbackHandler(mock_services)

        run1 = Mock()
        run1.text = "Hello"
        run2 = Mock()
        run2.text = "World"

        text_frame = Mock()
        text_frame.runs = [run1, run2]

        result = handler._extract_safe_text_content(text_frame)

        assert "Hello" in result
        assert "World" in result

    def test_extract_safe_text_content_with_empty_runs(self, mock_services):
        """Test text extraction handles empty run text."""
        handler = FallbackHandler(mock_services)

        run1 = Mock()
        run1.text = "Valid Text"
        run2 = Mock()
        run2.text = ""
        run3 = Mock()
        run3.text = None

        text_frame = Mock()
        text_frame.runs = [run1, run2, run3]

        result = handler._extract_safe_text_content(text_frame)

        assert result == "Valid Text"

    def test_extract_safe_text_content_exception_handling(self, mock_services):
        """Test text extraction handles exceptions gracefully."""
        handler = FallbackHandler(mock_services)

        text_frame = Mock()
        text_frame.runs = [Mock()]
        text_frame.runs[0].text = Mock(side_effect=Exception("Text access failed"))

        result = handler._extract_safe_text_content(text_frame)

        assert "[Text Extraction Failed]" in result


class TestTextSanitization:
    """Test text sanitization functionality."""

    def test_sanitize_text_normal(self, mock_services):
        """Test sanitization of normal text."""
        handler = FallbackHandler(mock_services)

        result = handler._sanitize_text("Hello World")

        assert result == "Hello World"

    def test_sanitize_text_empty(self, mock_services):
        """Test sanitization of empty text."""
        handler = FallbackHandler(mock_services)

        result = handler._sanitize_text("")

        assert result == ""

    def test_sanitize_text_null_bytes(self, mock_services):
        """Test sanitization removes null bytes."""
        handler = FallbackHandler(mock_services)

        result = handler._sanitize_text("Hello\x00World")

        assert result == "HelloWorld"

    def test_sanitize_text_problematic_chars(self, mock_services):
        """Test sanitization handles problematic characters."""
        handler = FallbackHandler(mock_services)

        result = handler._sanitize_text("Text\x0bwith\x0cchars")

        assert "\x0b" not in result
        assert "\x0c" not in result
        assert "Text" in result

    def test_sanitize_text_length_limit(self, mock_services):
        """Test sanitization enforces length limits."""
        handler = FallbackHandler(mock_services)

        long_text = "A" * 1500
        result = handler._sanitize_text(long_text)

        assert len(result) <= 1000
        assert result.endswith("...")


class TestSafeSelections:
    """Test safe font, size, and color selection."""

    def test_select_safe_font_known_font(self, mock_services, sample_text_frame):
        """Test safe font selection with known font."""
        handler = FallbackHandler(mock_services)

        result = handler._select_safe_font(sample_text_frame)

        assert result == "Arial"  # Arial is in universal_fonts

    def test_select_safe_font_unknown_font(self, mock_services):
        """Test safe font selection with unknown font."""
        handler = FallbackHandler(mock_services)

        run = Mock()
        run.font_family = "UnknownFont"

        text_frame = Mock()
        text_frame.runs = [run]

        result = handler._select_safe_font(text_frame)

        assert result == "Arial"  # Default fallback

    def test_select_safe_font_case_variants(self, mock_services):
        """Test safe font selection handles case variants."""
        handler = FallbackHandler(mock_services)

        test_cases = [
            ("arial", "Arial"),
            ("HELVETICA", "Arial"),
            ("times", "Times New Roman"),
            ("Times New Roman", "Times New Roman")
        ]

        for input_font, expected in test_cases:
            run = Mock()
            run.font_family = input_font

            text_frame = Mock()
            text_frame.runs = [run]

            result = handler._select_safe_font(text_frame)
            assert result == expected

    def test_select_safe_font_exception_handling(self, mock_services):
        """Test safe font selection handles exceptions."""
        handler = FallbackHandler(mock_services)

        text_frame = Mock()
        text_frame.runs = [Mock()]
        text_frame.runs[0].font_family = Mock(side_effect=Exception("Font access failed"))

        result = handler._select_safe_font(text_frame)

        assert result == "Arial"  # Default fallback

    def test_select_safe_font_size_normal(self, mock_services, sample_text_frame):
        """Test safe font size selection with normal size."""
        handler = FallbackHandler(mock_services)

        result = handler._select_safe_font_size(sample_text_frame)

        assert result == 12.0

    def test_select_safe_font_size_clamping(self, mock_services):
        """Test safe font size selection clamps extreme values."""
        handler = FallbackHandler(mock_services)

        test_cases = [
            (2.0, 8.0),   # Too small, clamp to minimum
            (100.0, 72.0),  # Too large, clamp to maximum
            (24.0, 24.0),   # Normal size, no change
        ]

        for input_size, expected in test_cases:
            run = Mock()
            run.font_size_pt = input_size

            text_frame = Mock()
            text_frame.runs = [run]

            result = handler._select_safe_font_size(text_frame)
            assert result == expected

    def test_select_safe_color_valid(self, mock_services, sample_text_frame):
        """Test safe color selection with valid color."""
        handler = FallbackHandler(mock_services)

        result = handler._select_safe_color(sample_text_frame)

        assert result == "000000"

    def test_select_safe_color_invalid(self, mock_services):
        """Test safe color selection with invalid color."""
        handler = FallbackHandler(mock_services)

        run = Mock()
        run.rgb = "invalid"

        text_frame = Mock()
        text_frame.runs = [run]

        result = handler._select_safe_color(text_frame)

        assert result == "000000"  # Default black

    def test_select_safe_color_various_formats(self, mock_services):
        """Test safe color selection handles various formats."""
        handler = FallbackHandler(mock_services)

        test_cases = [
            ("FF0000", "FF0000"),  # Valid uppercase
            ("ff0000", "FF0000"),  # Valid lowercase, converted to uppercase
            ("INVALID", "000000"),  # Invalid, fallback to black
            ("12345", "000000"),   # Wrong length, fallback
            ("", "000000"),        # Empty, fallback
        ]

        for input_color, expected in test_cases:
            run = Mock()
            run.rgb = input_color

            text_frame = Mock()
            text_frame.runs = [run]

            result = handler._select_safe_color(text_frame)
            assert result == expected


class TestBoundsCalculation:
    """Test safe bounds calculation."""

    def test_calculate_safe_bounds_normal(self, mock_services, sample_text_frame):
        """Test bounds calculation with normal text frame."""
        handler = FallbackHandler(mock_services)

        result = handler._calculate_safe_bounds(sample_text_frame)

        assert result['x'] == 100.0
        assert result['y'] == 200.0
        assert result['width'] == 200.0
        assert result['height'] == 50.0

    def test_calculate_safe_bounds_missing_values(self, mock_services):
        """Test bounds calculation with missing values."""
        handler = FallbackHandler(mock_services)

        text_frame = Mock()
        text_frame.x = None
        text_frame.y = None
        text_frame.width = None
        text_frame.height = None
        text_frame.runs = [Mock(text="Hello")]

        result = handler._calculate_safe_bounds(text_frame)

        assert result['x'] == 100.0  # Default
        assert result['y'] == 100.0  # Default
        assert result['width'] >= 200.0  # Estimated
        assert result['height'] == 50.0  # Default

    def test_calculate_safe_bounds_negative_values(self, mock_services):
        """Test bounds calculation handles negative values."""
        handler = FallbackHandler(mock_services)

        text_frame = Mock()
        text_frame.x = -50.0
        text_frame.y = -100.0
        text_frame.width = 200.0
        text_frame.height = 50.0
        text_frame.runs = []

        result = handler._calculate_safe_bounds(text_frame)

        assert result['x'] >= 0.0  # Negative values corrected
        assert result['y'] >= 0.0
        assert result['width'] == 200.0
        assert result['height'] == 50.0

    def test_calculate_safe_bounds_exception_handling(self, mock_services):
        """Test bounds calculation handles exceptions."""
        handler = FallbackHandler(mock_services)

        text_frame = Mock()
        text_frame.x = Mock(side_effect=Exception("Position access failed"))

        result = handler._calculate_safe_bounds(text_frame)

        # Should return safe defaults
        assert result['x'] == 100.0
        assert result['y'] == 100.0
        assert result['width'] == 200.0
        assert result['height'] == 50.0


class TestConversion:
    """Test text conversion functionality."""

    def test_convert_success_normal(self, mock_services, sample_text_frame):
        """Test successful conversion with normal text."""
        handler = FallbackHandler(mock_services)
        handler._to_emu_coords = Mock(return_value=(1000000, 2000000))
        handler._to_emu = Mock(return_value=500000)
        handler._escape_xml = Mock(side_effect=lambda x: x)

        result = handler.convert(sample_text_frame, {})

        assert result.success is True
        assert result.confidence == 0.5  # Moderate confidence for fallback
        assert result.metadata['strategy'] == 'fallback'
        assert 'fallback' in result.warnings[0].lower()

    def test_convert_success_empty_text(self, mock_services, empty_text_frame):
        """Test successful conversion with empty text."""
        handler = FallbackHandler(mock_services)
        handler._to_emu_coords = Mock(return_value=(1000000, 2000000))
        handler._to_emu = Mock(return_value=500000)
        handler._escape_xml = Mock(side_effect=lambda x: x)

        result = handler.convert(empty_text_frame, {})

        assert result.success is True
        assert "[Empty Text]" in result.xml_content

    def test_convert_success_problematic_text(self, mock_services, problematic_text_frame):
        """Test successful conversion with problematic text."""
        handler = FallbackHandler(mock_services)
        handler._to_emu_coords = Mock(return_value=(1000000, 2000000))
        handler._to_emu = Mock(return_value=500000)
        handler._escape_xml = Mock(side_effect=lambda x: x)

        result = handler.convert(problematic_text_frame, {})

        assert result.success is True
        assert result.metadata['strategy'] == 'fallback'

    def test_convert_emergency_fallback(self, mock_services, sample_text_frame):
        """Test emergency fallback when conversion fails."""
        handler = FallbackHandler(mock_services)
        handler._extract_safe_text_content = Mock(side_effect=Exception("Extraction failed"))

        result = handler.convert(sample_text_frame, {})

        assert result.success is True  # Even emergency fallback succeeds
        assert result.confidence == 0.1  # Very low confidence
        assert result.metadata.get('emergency_content') is True
        assert "[Text Conversion Error]" in result.xml_content


class TestXMLGeneration:
    """Test XML generation functionality."""

    def test_generate_safe_text_shape(self, mock_services):
        """Test safe text shape XML generation."""
        handler = FallbackHandler(mock_services)
        handler._to_emu_coords = Mock(return_value=(1000000, 2000000))
        handler._to_emu = Mock(return_value=500000)
        handler._escape_xml = Mock(side_effect=lambda x: x)

        bounds = {'x': 100, 'y': 200, 'width': 200, 'height': 50}
        result = handler._generate_safe_text_shape(
            "Hello", "Arial", 12.0, "000000", bounds, {}
        )

        assert "<p:sp>" in result
        assert "<p:txBody>" in result
        assert "Hello" in result
        assert "Arial" in result
        assert "1200" in result  # Font size in 100ths

    def test_emergency_fallback_xml(self, mock_services, sample_text_frame):
        """Test emergency fallback XML generation."""
        handler = FallbackHandler(mock_services)

        result = handler._create_emergency_fallback(sample_text_frame, "Test error")

        assert result.success is True
        assert "[Text Conversion Error]" in result.xml_content
        assert "<p:sp>" in result.xml_content
        assert result.metadata['emergency_content'] is True


class TestSupportedFeatures:
    """Test supported features reporting."""

    def test_get_supported_features(self, mock_services):
        """Test supported features dictionary."""
        handler = FallbackHandler(mock_services)

        features = handler.get_supported_features()

        assert features['system_fonts'] is True
        assert features['basic_styling'] is True
        assert features['guaranteed_success'] is True
        assert features['high_fidelity'] is False  # Safety over fidelity
        assert features['text_effects'] is False  # No effects for safety


class TestCacheManagement:
    """Test cache management functionality."""

    def test_clear_cache(self, mock_services):
        """Test cache clearing (no-op for fallback handler)."""
        handler = FallbackHandler(mock_services)

        # Should not raise exception
        handler.clear_cache()


class TestReliabilityScenarios:
    """Test handler reliability in extreme scenarios."""

    def test_null_text_frame(self, mock_services):
        """Test handling of null text frame."""
        handler = FallbackHandler(mock_services)

        result = handler.can_handle(None, {})

        assert result is True  # Fallback always accepts

    def test_corrupted_runs(self, mock_services):
        """Test handling of corrupted runs."""
        handler = FallbackHandler(mock_services)

        text_frame = Mock()
        text_frame.runs = "not_a_list"  # Corrupted runs

        result = handler.can_handle(text_frame, {})

        assert result is True

    def test_unicode_text_handling(self, mock_services):
        """Test handling of unicode text."""
        handler = FallbackHandler(mock_services)

        run = Mock()
        run.text = "Hello 世界 🌍"
        run.font_family = "Arial"
        run.font_size_pt = 12.0
        run.rgb = "000000"

        text_frame = Mock()
        text_frame.runs = [run]
        text_frame.x = 100.0
        text_frame.y = 200.0
        text_frame.width = 200.0
        text_frame.height = 50.0

        result = handler._extract_safe_text_content(text_frame)

        assert "Hello" in result
        # Unicode should be preserved if safe

    def test_extreme_coordinates(self, mock_services):
        """Test handling of extreme coordinate values."""
        handler = FallbackHandler(mock_services)

        text_frame = Mock()
        text_frame.x = 1e10  # Very large value
        text_frame.y = -1e10  # Very negative value
        text_frame.width = 0.001  # Very small value
        text_frame.height = 1e6  # Very large height
        text_frame.runs = [Mock(text="Test")]

        bounds = handler._calculate_safe_bounds(text_frame)

        # Should be clamped to safe values
        assert bounds['x'] >= 0
        assert bounds['y'] >= 0
        assert bounds['width'] >= 50.0  # Minimum width
        assert bounds['height'] >= 20.0  # Minimum height