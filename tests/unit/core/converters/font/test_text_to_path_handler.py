#!/usr/bin/env python3
"""
Tests for TextToPathHandler

Comprehensive test suite for the text-to-path font strategy handler,
including font availability detection, path conversion logic, and integration
with text-to-path services.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Import handler and dependencies
from core.converters.font.handlers.text_to_path_handler import TextToPathHandler
from core.converters.font.types import HandlerResult
from core.ir import TextFrame
from core.ir.text import Run, TextAnchor
from core.ir.font_metadata import FontStrategy
from core.services.conversion_services import ConversionServices


@pytest.fixture
def mock_services():
    """Create mock ConversionServices for testing."""
    services = Mock(spec=ConversionServices)
    services.font_service = Mock()
    services.font_service.find_font_file = Mock()
    services.font_service.map_svg_font_to_ppt = Mock(side_effect=lambda x: x)
    services.text_layout_service = Mock()
    services.path_service = Mock()
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
    text_frame.transform = None
    text_frame.text_path = None

    return text_frame


@pytest.fixture
def complex_text_frame():
    """Create complex TextFrame with challenging features."""
    run1 = Mock(spec=Run)
    run1.text = "Complex"
    run1.font_family = "NonExistentFont"
    run1.font_size_pt = 3.0  # Very small
    run1.bold = True
    run1.italic = False
    run1.underline = False
    run1.strike = False
    run1.rgb = "FF0000"

    run2 = Mock(spec=Run)
    run2.text = " Text"
    run2.font_family = "AnotherMissingFont"
    run2.font_size_pt = 180.0  # Very large
    run2.bold = False
    run2.italic = True
    run2.underline = True
    run2.strike = False
    run2.rgb = "00FF00"

    # Mock transform with skewing
    transform = Mock()
    transform.skew_x = 15.0
    transform.skew_y = 10.0
    transform.rotation = 45.0

    text_frame = Mock(spec=TextFrame)
    text_frame.runs = [run1, run2]
    text_frame.anchor = TextAnchor.MIDDLE
    text_frame.x = 50.0
    text_frame.y = 100.0
    text_frame.width = 300.0
    text_frame.height = 80.0
    text_frame.transform = transform
    text_frame.text_path = None

    return text_frame


class TestTextToPathHandlerInitialization:
    """Test handler initialization and service integration."""

    def test_initialization_with_services(self, mock_services):
        """Test handler initializes correctly with services."""
        handler = TextToPathHandler(mock_services)

        assert handler.services == mock_services
        assert handler.logger is not None
        assert isinstance(handler._font_availability_cache, dict)
        assert isinstance(handler.common_system_fonts, set)

    @patch('core.converters.font.handlers.text_to_path_handler.TEXT_TO_PATH_SERVICE_AVAILABLE', True)
    @patch('core.converters.font.handlers.text_to_path_handler.create_text_to_path_processor')
    def test_initialization_with_text_to_path_service(self, mock_create_processor, mock_services):
        """Test initialization when text-to-path service is available."""
        mock_processor = Mock()
        mock_create_processor.return_value = mock_processor

        handler = TextToPathHandler(mock_services)

        mock_create_processor.assert_called_once()
        assert handler.text_to_path_processor == mock_processor

    @patch('core.converters.font.handlers.text_to_path_handler.TEXT_TO_PATH_SERVICE_AVAILABLE', False)
    def test_initialization_without_text_to_path_service(self, mock_services):
        """Test initialization when text-to-path service is unavailable."""
        handler = TextToPathHandler(mock_services)

        assert handler.text_to_path_processor is None

    @patch('core.converters.font.handlers.text_to_path_handler.TEXT_TO_PATH_SERVICE_AVAILABLE', True)
    @patch('core.converters.font.handlers.text_to_path_handler.create_text_to_path_processor')
    def test_initialization_with_service_creation_failure(self, mock_create_processor, mock_services):
        """Test graceful handling when service creation fails."""
        mock_create_processor.side_effect = Exception("Service creation failed")

        handler = TextToPathHandler(mock_services)

        assert handler.text_to_path_processor is None


class TestCanHandle:
    """Test can_handle method for various scenarios."""

    def test_can_handle_empty_runs(self, mock_services):
        """Test can_handle returns False for empty runs."""
        handler = TextToPathHandler(mock_services)
        text_frame = Mock()
        text_frame.runs = []

        result = handler.can_handle(text_frame, {})

        assert result is False

    def test_can_handle_forced_text_to_path(self, mock_services, sample_text_frame):
        """Test can_handle returns True when forced."""
        handler = TextToPathHandler(mock_services)
        context = {'force_text_to_path': True}

        result = handler.can_handle(sample_text_frame, context)

        assert result is True

    def test_can_handle_no_fonts_available(self, mock_services, sample_text_frame):
        """Test can_handle returns True when no fonts are available."""
        handler = TextToPathHandler(mock_services)
        handler._is_font_available = Mock(return_value=False)

        result = handler.can_handle(sample_text_frame, {})

        assert result is True

    def test_can_handle_complex_features(self, mock_services, complex_text_frame):
        """Test can_handle returns True for complex features."""
        handler = TextToPathHandler(mock_services)
        handler._is_font_available = Mock(return_value=True)
        handler._requires_path_conversion = Mock(return_value=True)

        result = handler.can_handle(complex_text_frame, {})

        assert result is True

    def test_can_handle_previous_strategies_failed(self, mock_services, sample_text_frame):
        """Test can_handle returns True when previous strategies failed."""
        handler = TextToPathHandler(mock_services)
        handler._is_font_available = Mock(return_value=True)
        context = {'system_font_failed': True, 'wordart_failed': True}

        result = handler.can_handle(sample_text_frame, context)

        assert result is True

    def test_can_handle_fonts_available_no_complex_features(self, mock_services, sample_text_frame):
        """Test can_handle returns False when fonts available and no complex features."""
        handler = TextToPathHandler(mock_services)
        handler._is_font_available = Mock(return_value=True)
        handler._requires_path_conversion = Mock(return_value=False)

        result = handler.can_handle(sample_text_frame, {})

        assert result is False

    def test_can_handle_exception_handling(self, mock_services, sample_text_frame):
        """Test can_handle handles exceptions gracefully."""
        handler = TextToPathHandler(mock_services)
        handler._is_font_available = Mock(side_effect=Exception("Font check failed"))

        result = handler.can_handle(sample_text_frame, {})

        assert result is True  # Defaults to True on exception


class TestFontAvailability:
    """Test font availability detection."""

    def test_is_font_available_empty_font(self, mock_services):
        """Test font availability check with empty font."""
        handler = TextToPathHandler(mock_services)

        result = handler._is_font_available("")

        assert result is False

    def test_is_font_available_cached_result(self, mock_services):
        """Test font availability uses cache."""
        handler = TextToPathHandler(mock_services)
        handler._font_availability_cache["Arial"] = True

        result = handler._is_font_available("Arial")

        assert result is True
        # Font service should not be called due to cache hit
        assert not mock_services.font_service.find_font_file.called

    def test_is_font_available_with_font_service(self, mock_services):
        """Test font availability check with font service."""
        handler = TextToPathHandler(mock_services)
        mock_services.font_service.find_font_file.return_value = "/path/to/font.ttf"

        result = handler._is_font_available("CustomFont")

        assert result is True
        mock_services.font_service.find_font_file.assert_called_once_with("CustomFont")

    def test_is_font_available_font_service_returns_none(self, mock_services):
        """Test font availability when font service returns None."""
        handler = TextToPathHandler(mock_services)
        mock_services.font_service.find_font_file.return_value = None

        result = handler._is_font_available("MissingFont")

        assert result is False

    def test_is_font_available_no_font_service(self, mock_services):
        """Test font availability fallback when no font service."""
        handler = TextToPathHandler(mock_services)
        handler.services.font_service = None

        result = handler._is_font_available("Arial")

        assert result is True  # Arial is in common_system_fonts

    def test_is_font_available_common_font(self, mock_services):
        """Test font availability for common system fonts."""
        handler = TextToPathHandler(mock_services)
        handler.services.font_service = None

        for font in ["Arial", "Times New Roman", "Helvetica"]:
            result = handler._is_font_available(font)
            assert result is True

    def test_is_font_available_unknown_font_no_service(self, mock_services):
        """Test font availability for unknown fonts without service."""
        handler = TextToPathHandler(mock_services)
        handler.services.font_service = None

        result = handler._is_font_available("UnknownFont")

        assert result is False

    def test_is_font_available_exception_handling(self, mock_services):
        """Test font availability handles exceptions gracefully."""
        handler = TextToPathHandler(mock_services)
        mock_services.font_service.find_font_file.side_effect = Exception("Service error")

        result = handler._is_font_available("Arial")

        assert result is True  # Falls back to common font check


class TestPathConversionRequirements:
    """Test path conversion requirement detection."""

    def test_requires_path_conversion_complex_skew(self, mock_services):
        """Test path conversion required for complex skewing."""
        handler = TextToPathHandler(mock_services)

        # Create text frame with high skew
        text_frame = Mock()
        transform = Mock()
        transform.skew_x = 10.0
        transform.skew_y = 8.0
        text_frame.transform = transform
        text_frame.text_path = None
        text_frame.runs = [Mock(font_size_pt=12.0)]

        result = handler._requires_path_conversion(text_frame, {})

        assert result is True

    def test_requires_path_conversion_text_path(self, mock_services):
        """Test path conversion required for text on path."""
        handler = TextToPathHandler(mock_services)

        text_frame = Mock()
        text_frame.transform = None
        text_frame.text_path = Mock()  # Has text path
        text_frame.runs = [Mock(font_size_pt=12.0)]

        result = handler._requires_path_conversion(text_frame, {})

        assert result is True

    def test_requires_path_conversion_extreme_font_sizes(self, mock_services):
        """Test path conversion required for extreme font sizes."""
        handler = TextToPathHandler(mock_services)

        text_frame = Mock()
        text_frame.transform = None
        text_frame.text_path = None

        # Very small font
        small_run = Mock()
        small_run.font_size_pt = 2.0
        text_frame.runs = [small_run]

        result = handler._requires_path_conversion(text_frame, {})
        assert result is True

        # Very large font
        large_run = Mock()
        large_run.font_size_pt = 200.0
        text_frame.runs = [large_run]

        result = handler._requires_path_conversion(text_frame, {})
        assert result is True

    def test_requires_path_conversion_complex_outline(self, mock_services):
        """Test path conversion required for complex text outline."""
        handler = TextToPathHandler(mock_services)

        text_frame = Mock()
        text_frame.transform = None
        text_frame.text_path = None

        # Run with complex outline
        run = Mock()
        run.font_size_pt = 12.0
        run.text_shadow = None
        outline = Mock()
        outline.width = 2.0  # 2pt outline on 12pt text = ~17%
        run.text_outline = outline
        text_frame.runs = [run]

        result = handler._requires_path_conversion(text_frame, {})

        assert result is True

    def test_requires_path_conversion_simple_case(self, mock_services):
        """Test path conversion not required for simple text."""
        handler = TextToPathHandler(mock_services)

        text_frame = Mock()
        text_frame.transform = None
        text_frame.text_path = None

        run = Mock()
        run.font_size_pt = 12.0
        run.text_shadow = None
        run.text_outline = None
        text_frame.runs = [run]

        result = handler._requires_path_conversion(text_frame, {})

        assert result is False


class TestConversion:
    """Test text conversion functionality."""

    def test_convert_success_with_processor(self, mock_services, sample_text_frame):
        """Test successful conversion with text-to-path processor."""
        handler = TextToPathHandler(mock_services)
        handler.text_to_path_processor = Mock()
        handler._calculate_bounds = Mock(return_value={
            'x': 100, 'y': 200, 'width': 200, 'height': 50
        })
        handler._convert_with_processor = Mock(return_value="<p:sp>processor content</p:sp>")
        handler._calculate_confidence = Mock(return_value=0.8)

        result = handler.convert(sample_text_frame, {})

        assert result.success is True
        assert result.confidence == 0.8
        assert "processor content" in result.xml_content
        assert result.metadata['strategy'] == 'text_to_path'

    def test_convert_success_with_fallback(self, mock_services, sample_text_frame):
        """Test successful conversion with fallback method."""
        handler = TextToPathHandler(mock_services)
        handler.text_to_path_processor = None
        handler._calculate_bounds = Mock(return_value={
            'x': 100, 'y': 200, 'width': 200, 'height': 50
        })
        handler._convert_with_fallback = Mock(return_value="<p:sp>fallback content</p:sp>")
        handler._calculate_confidence = Mock(return_value=0.6)

        result = handler.convert(sample_text_frame, {})

        assert result.success is True
        assert result.confidence == 0.6
        assert "fallback content" in result.xml_content

    def test_convert_exception_handling(self, mock_services, sample_text_frame):
        """Test conversion handles exceptions gracefully."""
        handler = TextToPathHandler(mock_services)
        handler._calculate_bounds = Mock(side_effect=Exception("Bounds calculation failed"))

        result = handler.convert(sample_text_frame, {})

        assert result.success is False
        assert result.confidence == 0.0
        assert result.xml_content == ""
        assert len(result.warnings) > 0


class TestProcessorConversion:
    """Test conversion with text-to-path processor."""

    def test_convert_with_processor_path_conversion(self, mock_services):
        """Test processor conversion when path conversion recommended."""
        handler = TextToPathHandler(mock_services)
        handler.text_to_path_processor = Mock()

        # Mock assessment recommending path conversion
        assessment = Mock()
        assessment.should_convert_to_path = True
        handler.text_to_path_processor.assess_text_conversion_strategy.return_value = assessment
        handler.text_to_path_processor.convert_text_to_path.return_value = "M 0 0 L 100 0 L 100 50 Z"

        handler._create_path_shape_xml = Mock(return_value="<p:sp>path shape</p:sp>")

        bounds = {'x': 100, 'y': 200, 'width': 200, 'height': 50}
        result = handler._convert_with_processor("Hello", ["Arial"], 12.0, bounds, {})

        assert "path shape" in result
        handler._create_path_shape_xml.assert_called_once()

    def test_convert_with_processor_no_path_conversion(self, mock_services):
        """Test processor conversion when path conversion not recommended."""
        handler = TextToPathHandler(mock_services)
        handler.text_to_path_processor = Mock()

        # Mock assessment not recommending path conversion
        assessment = Mock()
        assessment.should_convert_to_path = False
        handler.text_to_path_processor.assess_text_conversion_strategy.return_value = assessment

        handler._create_fallback_text_shape = Mock(return_value="<p:sp>text shape</p:sp>")

        bounds = {'x': 100, 'y': 200, 'width': 200, 'height': 50}
        result = handler._convert_with_processor("Hello", ["Arial"], 12.0, bounds, {})

        assert "text shape" in result
        handler._create_fallback_text_shape.assert_called_once()

    def test_convert_with_processor_exception(self, mock_services):
        """Test processor conversion handles exceptions."""
        handler = TextToPathHandler(mock_services)
        handler.text_to_path_processor = Mock()
        handler.text_to_path_processor.assess_text_conversion_strategy.side_effect = Exception("Assessment failed")
        handler._convert_with_fallback = Mock(return_value="<p:sp>fallback</p:sp>")

        bounds = {'x': 100, 'y': 200, 'width': 200, 'height': 50}
        result = handler._convert_with_processor("Hello", ["Arial"], 12.0, bounds, {})

        assert "fallback" in result
        handler._convert_with_fallback.assert_called_once()


class TestFallbackConversion:
    """Test fallback conversion methods."""

    def test_convert_with_fallback(self, mock_services):
        """Test fallback conversion creates path shape."""
        handler = TextToPathHandler(mock_services)
        handler._to_emu_coords = Mock(return_value=(1000000, 2000000))
        handler._to_emu = Mock(return_value=500000)
        handler._create_path_shape_xml = Mock(return_value="<p:sp>fallback path</p:sp>")

        bounds = {'x': 100, 'y': 200, 'width': 200, 'height': 50}
        result = handler._convert_with_fallback("Hello", ["Arial"], 12.0, bounds, {})

        assert "fallback path" in result
        handler._create_path_shape_xml.assert_called_once()

    def test_create_path_shape_xml(self, mock_services):
        """Test path shape XML creation."""
        handler = TextToPathHandler(mock_services)
        handler._to_emu_coords = Mock(return_value=(1000000, 2000000))
        handler._to_emu = Mock(return_value=500000)
        handler._generate_shape_properties = Mock(return_value="<shape_props/>")
        handler._generate_non_visual_properties = Mock(return_value="<nv_props/>")

        bounds = {'x': 100, 'y': 200, 'width': 200, 'height': 50}
        result = handler._create_path_shape_xml("M 0 0 L 100 0", bounds, {})

        assert "<p:sp>" in result
        assert "<a:custGeom>" in result
        assert "500000" in result  # Width/height EMU

    def test_create_fallback_text_shape(self, mock_services):
        """Test fallback text shape creation."""
        handler = TextToPathHandler(mock_services)
        handler._to_emu_coords = Mock(return_value=(1000000, 2000000))
        handler._to_emu = Mock(return_value=500000)
        handler._generate_shape_properties = Mock(return_value="<shape_props/>")
        handler._generate_non_visual_properties = Mock(return_value="<nv_props/>")
        handler._escape_xml = Mock(side_effect=lambda x: x)

        bounds = {'x': 100, 'y': 200, 'width': 200, 'height': 50}
        result = handler._create_fallback_text_shape("Hello", "Arial", 12.0, bounds, {})

        assert "<p:sp>" in result
        assert "<p:txBody>" in result
        assert "Hello" in result
        assert "Arial" in result


class TestConfidenceCalculation:
    """Test confidence score calculation."""

    def test_calculate_confidence_no_fonts_available(self, mock_services, sample_text_frame):
        """Test confidence boost when no fonts available."""
        handler = TextToPathHandler(mock_services)
        handler._is_font_available = Mock(return_value=False)
        handler._requires_path_conversion = Mock(return_value=False)
        handler.text_to_path_processor = None

        confidence = handler._calculate_confidence(sample_text_frame, {})

        assert confidence >= 0.8  # Base + no fonts boost

    def test_calculate_confidence_complex_features(self, mock_services, sample_text_frame):
        """Test confidence boost for complex features."""
        handler = TextToPathHandler(mock_services)
        handler._is_font_available = Mock(return_value=True)
        handler._requires_path_conversion = Mock(return_value=True)
        handler.text_to_path_processor = None

        confidence = handler._calculate_confidence(sample_text_frame, {})

        assert confidence >= 0.8  # Base + complex features boost

    def test_calculate_confidence_long_text_penalty(self, mock_services):
        """Test confidence reduction for very long text."""
        handler = TextToPathHandler(mock_services)
        handler._is_font_available = Mock(return_value=True)
        handler._requires_path_conversion = Mock(return_value=False)
        handler.text_to_path_processor = None

        # Create text frame with very long text
        long_run = Mock()
        long_run.text = "A" * 150  # Very long text
        long_run.font_family = "Arial"

        text_frame = Mock()
        text_frame.runs = [long_run]

        confidence = handler._calculate_confidence(text_frame, {})

        assert confidence <= 0.7  # Base confidence with penalty

    def test_calculate_confidence_with_processor(self, mock_services, sample_text_frame):
        """Test confidence boost when processor available."""
        handler = TextToPathHandler(mock_services)
        handler._is_font_available = Mock(return_value=True)
        handler._requires_path_conversion = Mock(return_value=False)
        handler.text_to_path_processor = Mock()  # Processor available

        confidence = handler._calculate_confidence(sample_text_frame, {})

        assert confidence >= 0.7  # Base + processor boost


class TestSupportedFeatures:
    """Test supported features reporting."""

    def test_get_supported_features(self, mock_services):
        """Test supported features dictionary."""
        handler = TextToPathHandler(mock_services)

        features = handler.get_supported_features()

        assert features['system_fonts'] is False
        assert features['text_transforms'] is True
        assert features['text_effects'] is True
        assert features['high_fidelity'] is True
        assert features['editability'] is False


class TestCacheManagement:
    """Test cache management functionality."""

    def test_clear_cache(self, mock_services):
        """Test cache clearing functionality."""
        handler = TextToPathHandler(mock_services)
        handler._font_availability_cache = {"Arial": True, "Times": False}
        handler.text_to_path_processor = Mock()

        handler.clear_cache()

        assert len(handler._font_availability_cache) == 0
        handler.text_to_path_processor.clear_cache.assert_called_once()

    def test_clear_cache_no_processor(self, mock_services):
        """Test cache clearing when no processor available."""
        handler = TextToPathHandler(mock_services)
        handler._font_availability_cache = {"Arial": True}
        handler.text_to_path_processor = None

        # Should not raise exception
        handler.clear_cache()

        assert len(handler._font_availability_cache) == 0