#!/usr/bin/env python3
"""
Unit tests for WordArtHandler

Tests WordArt conversion logic, feature detection, and integration
with WordArt services.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from lxml import etree as ET

from core.converters.font.handlers.wordart_handler import WordArtHandler
from core.converters.font.types import HandlerResult
from core.ir import TextFrame, Run, Point, Rect
from core.services.conversion_services import ConversionServices


@pytest.fixture
def mock_services():
    """Mock ConversionServices for testing."""
    services = Mock(spec=ConversionServices)
    return services


@pytest.fixture
def mock_wordart_service():
    """Mock WordArt integration service."""
    service = Mock()

    # Mock generation result
    result = Mock()
    result.success = True
    result.wordart_xml = ET.Element('shape')
    result.decision_metadata = {'policy_decision': {'use_native': True}}
    result.performance_metrics = {'generation_time_ms': 50.0}
    result.fallback_reason = None

    service.generate_wordart.return_value = result
    return service


@pytest.fixture
def wordart_handler(mock_services):
    """Create WordArtHandler for testing."""
    handler = WordArtHandler(mock_services)
    return handler


@pytest.fixture
def simple_text_frame():
    """Create a simple text frame for testing."""
    run = Mock()
    run.text = "WordArt Text"
    run.font_family = "Arial"
    run.font_size_pt = 24
    run.font_size = 24
    run.bold = False
    run.italic = False
    run.fill = "#000000"
    run.rgb = "#000000"
    run.stroke = None
    run.stroke_width = 0
    run.opacity = 1.0

    frame = Mock()
    frame.runs = [run]
    frame.origin = Point(x=100, y=100)
    frame.bbox = Rect(x=100, y=100, width=200, height=50)
    frame.transform = None
    frame.text_path = None
    return frame


@pytest.fixture
def transformed_text_frame():
    """Create a text frame with transform for testing."""
    run = Mock()
    run.text = "Rotated Text"
    run.font_family = "Arial"
    run.font_size_pt = 18
    run.font_size = 18
    run.fill = "#FF0000"
    run.rgb = "#FF0000"
    run.stroke = "#000000"
    run.stroke_width = 2.0
    run.opacity = 0.8

    transform = Mock()
    transform.rotation = 45.0
    transform.scale_x = 1.2
    transform.scale_y = 1.0
    transform.translate_x = 10
    transform.translate_y = 5
    transform.skew_x = 0
    transform.skew_y = 0

    frame = Mock()
    frame.runs = [run]
    frame.origin = Point(x=50, y=50)
    frame.transform = transform
    frame.text_path = None
    return frame


class TestWordArtHandlerInitialization:
    """Test WordArtHandler initialization."""

    def test_initialization_with_wordart_available(self, mock_services):
        """Test handler initialization with built-in WordArt."""
        handler = WordArtHandler(mock_services)

        assert handler.services == mock_services
        assert handler.wordart_service is None  # Service not used
        assert isinstance(handler.wordart_presets, dict)
        assert 'simple' in handler.wordart_presets
        assert 'arch' in handler.wordart_presets

    def test_initialization_without_wordart_available(self, mock_services):
        """Test handler always uses built-in implementation."""
        handler = WordArtHandler(mock_services)

        assert handler.services == mock_services
        assert handler.wordart_service is None

    def test_wordart_presets_populated(self, wordart_handler):
        """Test WordArt presets are properly populated."""
        expected_presets = [
            'simple', 'outline', 'shadow', 'reflection', 'glow',
            'bevel', 'gradient', 'pattern', 'texture', 'arch',
            'curve', 'wave', 'inflate', 'deflate', 'button', 'perspective'
        ]

        for preset in expected_presets:
            assert preset in wordart_handler.wordart_presets


class TestCanHandle:
    """Test can_handle logic."""

    def test_can_handle_wordart_unavailable(self, mock_services, simple_text_frame):
        """Test can_handle when WordArt is unavailable."""
        with patch('core.converters.font.handlers.wordart_handler.WORDART_INTEGRATION_AVAILABLE', False):
            handler = WordArtHandler(mock_services)

        result = handler.can_handle(simple_text_frame, {})
        assert result is False

    def test_can_handle_forced_wordart(self, wordart_handler, simple_text_frame):
        """Test can_handle when WordArt is forced by policy."""
        context = {'force_wordart': True}

        result = wordart_handler.can_handle(simple_text_frame, context)
        assert result is True

    def test_can_handle_empty_runs(self, wordart_handler):
        """Test can_handle with empty text frame."""
        empty_frame = Mock()
        empty_frame.runs = []

        result = wordart_handler.can_handle(empty_frame, {})
        assert result is False

    def test_can_handle_wordart_features(self, wordart_handler, transformed_text_frame):
        """Test can_handle with WordArt-suitable features."""
        # Mock the _has_wordart_features method to return True
        wordart_handler._has_wordart_features = Mock(return_value=True)

        result = wordart_handler.can_handle(transformed_text_frame, {})
        assert result is True

    def test_can_handle_policy_recommendation(self, wordart_handler, simple_text_frame):
        """Test can_handle with policy recommendation."""
        context = {
            'policy_decisions': {
                'wordart_opportunity': True,
                'confidence': 0.8
            }
        }

        # Mock _has_wordart_features to return False so we test policy path
        wordart_handler._has_wordart_features = Mock(return_value=False)

        result = wordart_handler.can_handle(simple_text_frame, context)
        assert result is True

    def test_can_handle_low_policy_confidence(self, wordart_handler, simple_text_frame):
        """Test can_handle with low policy confidence."""
        context = {
            'policy_decisions': {
                'wordart_opportunity': True,
                'confidence': 0.4  # Below threshold
            }
        }

        # Mock _has_wordart_features to return False
        wordart_handler._has_wordart_features = Mock(return_value=False)

        result = wordart_handler.can_handle(simple_text_frame, context)
        assert result is False

    def test_can_handle_exception(self, wordart_handler, simple_text_frame):
        """Test can_handle with exception in processing."""
        # Mock method to raise exception
        wordart_handler._has_wordart_features = Mock(side_effect=Exception("Test error"))

        result = wordart_handler.can_handle(simple_text_frame, {})
        assert result is False


class TestWordArtFeatureDetection:
    """Test WordArt feature detection logic."""

    def test_has_wordart_features_rotation(self, wordart_handler):
        """Test detection of rotation transforms."""
        run = Mock(text="Test", font_family="Arial")
        transform = Mock()
        transform.rotation = 30.0  # Significant rotation

        frame = Mock(runs=[run], transform=transform, text_path=None)

        result = wordart_handler._has_wordart_features(frame, {})
        assert result is True

    def test_has_wordart_features_scaling(self, wordart_handler):
        """Test detection of scaling transforms."""
        run = Mock(text="Test", font_family="Arial")
        transform = Mock()
        transform.rotation = 0
        transform.scale_x = 1.5  # Significant scaling
        transform.scale_y = 1.0

        frame = Mock(runs=[run], transform=transform, text_path=None)

        result = wordart_handler._has_wordart_features(frame, {})
        assert result is True

    def test_has_wordart_features_skewing(self, wordart_handler):
        """Test detection of skew transforms."""
        run = Mock(text="Test", font_family="Arial")
        transform = Mock()
        transform.rotation = 0
        transform.scale_x = 1.0
        transform.scale_y = 1.0
        transform.skew_x = 10.0  # Significant skew

        frame = Mock(runs=[run], transform=transform, text_path=None)

        result = wordart_handler._has_wordart_features(frame, {})
        assert result is True

    def test_has_wordart_features_text_path(self, wordart_handler):
        """Test detection of text on path."""
        run = Mock(text="Test", font_family="Arial")
        frame = Mock(runs=[run], transform=None, text_path=Mock())

        result = wordart_handler._has_wordart_features(frame, {})
        assert result is True

    def test_has_wordart_features_stroke_effects(self, wordart_handler):
        """Test detection of stroke effects."""
        run = Mock(text="Test", font_family="Arial")
        run.stroke = "#FF0000"
        run.stroke_width = 3.0

        frame = Mock(runs=[run], transform=None, text_path=None)

        result = wordart_handler._has_wordart_features(frame, {})
        assert result is True

    def test_has_wordart_features_gradient_fill(self, wordart_handler):
        """Test detection of gradient fills."""
        run = Mock(text="Test", font_family="Arial")
        run.fill = "url(#gradient1)"
        run.stroke = None

        frame = Mock(runs=[run], transform=None, text_path=None)

        result = wordart_handler._has_wordart_features(frame, {})
        assert result is True

    def test_has_wordart_features_decorative_font(self, wordart_handler):
        """Test detection of decorative fonts."""
        run = Mock(text="Test", font_family="Brush Script MT")  # Decorative font
        run.fill = "#000000"
        run.stroke = None

        frame = Mock(runs=[run], transform=None, text_path=None)

        result = wordart_handler._has_wordart_features(frame, {})
        assert result is True

    def test_has_wordart_features_large_short_text(self, wordart_handler):
        """Test detection of large, short text suitable for WordArt."""
        run = Mock(text="BIG", font_family="Arial")
        run.font_size_pt = 36  # Large font
        run.fill = "#000000"
        run.stroke = None

        frame = Mock(runs=[run], transform=None, text_path=None)

        result = wordart_handler._has_wordart_features(frame, {})
        assert result is True

    def test_has_wordart_features_simple_text(self, wordart_handler):
        """Test that simple text is not considered WordArt-suitable."""
        run = Mock(text="Simple text", font_family="Arial")
        run.font_size_pt = 12  # Regular size
        run.fill = "#000000"
        run.stroke = None

        frame = Mock(runs=[run], transform=None, text_path=None)

        result = wordart_handler._has_wordart_features(frame, {})
        assert result is False


class TestConversion:
    """Test WordArt conversion functionality."""

    def test_convert_successful(self, wordart_handler, simple_text_frame, mock_wordart_service):
        """Test successful WordArt conversion."""
        # Mock the WordArt service
        wordart_handler.wordart_service = mock_wordart_service

        result = wordart_handler.convert(simple_text_frame, {})

        assert isinstance(result, HandlerResult)
        assert result.success is True
        assert result.xml_content
        assert result.confidence > 0
        assert 'strategy' in result.metadata
        assert result.metadata['strategy'] == 'wordart'

    def test_convert_service_failure(self, wordart_handler, simple_text_frame):
        """Test conversion when WordArt service fails."""
        # Mock failed generation
        mock_service = Mock()
        failed_result = Mock()
        failed_result.success = False
        failed_result.fallback_reason = "Transform too complex"
        mock_service.generate_wordart.return_value = failed_result

        wordart_handler.wordart_service = mock_service

        result = wordart_handler.convert(simple_text_frame, {})

        assert result.success is False
        assert result.confidence == 0.0
        assert "WordArt generation failed" in result.warnings[0]

    def test_convert_exception_handling(self, wordart_handler, simple_text_frame):
        """Test conversion with exception."""
        # Mock service to raise exception
        wordart_handler.wordart_service = Mock()
        wordart_handler.wordart_service.generate_wordart.side_effect = Exception("Service error")

        result = wordart_handler.convert(simple_text_frame, {})

        assert result.success is False
        assert result.confidence == 0.0
        assert result.error is not None
        assert "WordArt conversion failed" in result.warnings[0]

    def test_convert_with_transforms(self, wordart_handler, transformed_text_frame, mock_wordart_service):
        """Test conversion with text transforms."""
        # Mock the WordArt service
        wordart_handler.wordart_service = mock_wordart_service

        result = wordart_handler.convert(transformed_text_frame, {})

        assert result.success is True
        assert result.metadata['has_transforms'] is True


class TestTextRunConversion:
    """Test text run conversion to WordArt format."""

    def test_convert_to_wordart_runs_simple(self, wordart_handler, simple_text_frame):
        """Test conversion of simple text runs."""
        wordart_runs = wordart_handler._convert_to_wordart_runs(simple_text_frame)

        assert len(wordart_runs) == 1
        run = wordart_runs[0]
        assert run.text == "WordArt Text"
        assert run.font_family == "Arial"
        assert run.font_size == 24.0
        assert run.fill_color == "#000000"

    def test_convert_to_wordart_runs_with_stroke(self, wordart_handler, transformed_text_frame):
        """Test conversion of text runs with stroke."""
        wordart_runs = wordart_handler._convert_to_wordart_runs(transformed_text_frame)

        assert len(wordart_runs) == 1
        run = wordart_runs[0]
        assert run.stroke_color == "#000000"
        assert run.stroke_width == 2.0

    def test_convert_to_wordart_runs_multiple(self, wordart_handler):
        """Test conversion of multiple text runs."""
        run1 = Mock(text="Hello ", font_family="Arial", font_size_pt=12, fill="#000000", stroke=None, opacity=1.0)
        run2 = Mock(text="World", font_family="Times", font_size_pt=14, fill="#FF0000", stroke="#000000", stroke_width=1.0, opacity=0.8)

        frame = Mock(runs=[run1, run2])

        wordart_runs = wordart_handler._convert_to_wordart_runs(frame)

        assert len(wordart_runs) == 2
        assert wordart_runs[0].text == "Hello "
        assert wordart_runs[1].text == "World"
        assert wordart_runs[1].stroke_color == "#000000"


class TestSVGElementBridge:
    """Test SVG element bridge functionality."""

    def test_create_svg_element_bridge_basic(self, wordart_handler, simple_text_frame):
        """Test creation of SVG element bridge."""
        svg_element = wordart_handler._create_svg_element_bridge(simple_text_frame, {})

        assert svg_element.tag == 'text'
        assert svg_element.text == "WordArt Text"
        assert svg_element.get('font-family') == "Arial"
        assert svg_element.get('font-size') == "24"
        assert svg_element.get('fill') == "#000000"

    def test_create_svg_element_bridge_with_transform(self, wordart_handler, transformed_text_frame):
        """Test SVG element bridge with transforms."""
        svg_element = wordart_handler._create_svg_element_bridge(transformed_text_frame, {})

        assert svg_element.get('transform') is not None
        transform_str = svg_element.get('transform')
        assert 'translate(10,5)' in transform_str
        assert 'rotate(45.0)' in transform_str
        assert 'scale(1.2,1.0)' in transform_str

    def test_create_svg_element_bridge_with_stroke(self, wordart_handler, transformed_text_frame):
        """Test SVG element bridge with stroke properties."""
        svg_element = wordart_handler._create_svg_element_bridge(transformed_text_frame, {})

        assert svg_element.get('stroke') == "#000000"
        assert svg_element.get('stroke-width') == "2.0"

    def test_convert_transform_to_svg_complete(self, wordart_handler):
        """Test complete transform conversion to SVG."""
        transform = Mock()
        transform.translate_x = 10
        transform.translate_y = 20
        transform.rotation = 30
        transform.scale_x = 1.5
        transform.scale_y = 2.0
        transform.skew_x = 5
        transform.skew_y = 0

        transform_str = wordart_handler._convert_transform_to_svg(transform)

        assert 'translate(10,20)' in transform_str
        assert 'rotate(30)' in transform_str
        assert 'scale(1.5,2.0)' in transform_str
        assert 'skewX(5)' in transform_str

    def test_convert_transform_to_svg_minimal(self, wordart_handler):
        """Test minimal transform conversion."""
        transform = Mock()
        transform.translate_x = 0
        transform.translate_y = 0
        transform.rotation = 0
        transform.scale_x = 1
        transform.scale_y = 1
        transform.skew_x = 0
        transform.skew_y = 0

        transform_str = wordart_handler._convert_transform_to_svg(transform)

        assert transform_str is None  # No transforms needed


class TestConfidenceCalculation:
    """Test confidence calculation logic."""

    def test_calculate_confidence_successful_generation(self, wordart_handler, simple_text_frame):
        """Test confidence with successful generation."""
        generation_result = Mock()
        generation_result.success = True

        # Mock has_wordart_features to return True
        wordart_handler._has_wordart_features = Mock(return_value=True)

        confidence = wordart_handler._calculate_confidence(simple_text_frame, {}, generation_result)

        assert confidence >= 0.8  # Base + success + features

    def test_calculate_confidence_with_policy(self, wordart_handler, simple_text_frame):
        """Test confidence calculation with policy decisions."""
        generation_result = Mock()
        generation_result.success = True

        context = {
            'policy_decisions': {
                'wordart_opportunity': True,
                'confidence': 0.9
            }
        }

        wordart_handler._has_wordart_features = Mock(return_value=True)

        confidence = wordart_handler._calculate_confidence(simple_text_frame, context, generation_result)

        assert confidence > 0.8  # Should include policy boost

    def test_calculate_confidence_long_text(self, wordart_handler):
        """Test confidence reduction for long text."""
        run = Mock(text="This is a very long text that should reduce confidence")
        frame = Mock(runs=[run])

        generation_result = Mock()
        generation_result.success = True

        wordart_handler._has_wordart_features = Mock(return_value=False)

        confidence = wordart_handler._calculate_confidence(frame, {}, generation_result)

        assert confidence < 0.9  # Should be reduced for long text

    def test_calculate_confidence_many_runs(self, wordart_handler):
        """Test confidence reduction for many text runs."""
        runs = [Mock(text=f"Run {i}") for i in range(5)]
        frame = Mock(runs=runs)

        generation_result = Mock()
        generation_result.success = True

        wordart_handler._has_wordart_features = Mock(return_value=False)

        confidence = wordart_handler._calculate_confidence(frame, {}, generation_result)

        assert confidence < 0.9  # Should be reduced for many runs


class TestUtilityMethods:
    """Test utility and helper methods."""

    def test_get_supported_features(self, wordart_handler):
        """Test supported features reporting."""
        features = wordart_handler.get_supported_features()

        assert features['wordart_effects'] is True
        assert features['text_transforms'] is True
        assert features['text_on_path'] is True
        assert features['gradient_fills'] is True
        assert features['system_fonts'] is False
        assert features['preset_styles'] is True

    def test_get_available_presets(self, wordart_handler):
        """Test getting available presets."""
        presets = wordart_handler.get_available_presets()

        assert isinstance(presets, list)
        assert 'simple' in presets
        assert 'arch' in presets
        assert 'wave' in presets

    def test_clear_cache(self, wordart_handler):
        """Test cache clearing."""
        # Add something to caches
        wordart_handler._wordart_cache['test'] = 'value'
        wordart_handler._preset_usage_stats['simple'] = 5

        assert len(wordart_handler._wordart_cache) > 0
        assert len(wordart_handler._preset_usage_stats) > 0

        wordart_handler.clear_cache()

        assert len(wordart_handler._wordart_cache) == 0
        assert len(wordart_handler._preset_usage_stats) == 0

    def test_is_available(self, wordart_handler):
        """Test availability check."""
        # Should be available since we mocked it as such
        assert wordart_handler.is_available() is True

    def test_is_available_no_service(self, mock_services):
        """Test availability check without service."""
        with patch('core.converters.font.handlers.wordart_handler.WORDART_INTEGRATION_AVAILABLE', False):
            handler = WordArtHandler(mock_services)
            assert handler.is_available() is False

    def test_extract_preset_from_result(self, wordart_handler):
        """Test preset extraction from generation result."""
        generation_result = Mock()
        generation_result.decision_metadata = {
            'path_analysis': {
                'preset_type': 'arch'
            }
        }

        preset = wordart_handler._extract_preset_from_result(generation_result)
        assert preset == 'arch'

    def test_extract_preset_from_result_no_preset(self, wordart_handler):
        """Test preset extraction when no preset available."""
        generation_result = Mock()
        generation_result.decision_metadata = {}

        preset = wordart_handler._extract_preset_from_result(generation_result)
        assert preset is None

    def test_get_preset_usage_stats(self, wordart_handler):
        """Test getting preset usage statistics."""
        # Add some usage stats
        wordart_handler._preset_usage_stats['arch'] = 3
        wordart_handler._preset_usage_stats['wave'] = 1

        stats = wordart_handler.get_preset_usage_stats()

        assert stats['arch'] == 3
        assert stats['wave'] == 1
        # Should be a copy, not the original
        stats['arch'] = 10
        assert wordart_handler._preset_usage_stats['arch'] == 3


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_full_workflow_simple_wordart(self, wordart_handler, simple_text_frame, mock_wordart_service):
        """Test complete workflow for simple WordArt."""
        # Mock WordArt service
        wordart_handler.wordart_service = mock_wordart_service

        # Mock features detection
        wordart_handler._has_wordart_features = Mock(return_value=True)

        context = {'policy_decisions': {'wordart_opportunity': True, 'confidence': 0.8}}

        # Check can handle
        can_handle = wordart_handler.can_handle(simple_text_frame, context)
        assert can_handle is True

        # Perform conversion
        result = wordart_handler.convert(simple_text_frame, context)
        assert result.success is True
        assert result.confidence > 0.7

    def test_full_workflow_complex_transforms(self, wordart_handler, transformed_text_frame, mock_wordart_service):
        """Test complete workflow with complex transforms."""
        # Mock WordArt service
        wordart_handler.wordart_service = mock_wordart_service

        context = {'force_wordart': True}

        # Check can handle
        can_handle = wordart_handler.can_handle(transformed_text_frame, context)
        assert can_handle is True

        # Perform conversion
        result = wordart_handler.convert(transformed_text_frame, context)
        assert result.success is True
        assert result.metadata['has_transforms'] is True

    def test_full_workflow_service_unavailable(self, mock_services, simple_text_frame):
        """Test workflow when WordArt service is unavailable."""
        with patch('core.converters.font.handlers.wordart_handler.WORDART_INTEGRATION_AVAILABLE', False):
            handler = WordArtHandler(mock_services)

        # Should not handle anything
        can_handle = handler.can_handle(simple_text_frame, {})
        assert can_handle is False

        assert handler.is_available() is False