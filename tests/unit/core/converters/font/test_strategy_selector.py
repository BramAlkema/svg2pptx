#!/usr/bin/env python3
"""
Unit tests for FontStrategySelector

Tests intelligent font strategy selection based on text complexity,
font availability, and policy decisions.
"""

import pytest
from unittest.mock import Mock, patch

from core.converters.font.strategy_selector import FontStrategySelector, SelectionResult
from core.converters.font.types import FontConversionConfig, FontComplexity
from core.ir import TextFrame, Run, Point, Rect
from core.ir.font_metadata import FontStrategy
from core.services.conversion_services import ConversionServices
from core.policy import Policy


@pytest.fixture
def mock_services():
    """Mock ConversionServices for testing."""
    services = Mock(spec=ConversionServices)
    services.font_service = Mock()
    services.font_service.is_font_available = Mock(return_value=True)
    services.font_service.get_font_metrics = Mock(return_value=Mock(
        estimated_width=100,
        estimated_height=20,
        ascent=15,
        descent=5
    ))
    return services


@pytest.fixture
def mock_policy():
    """Mock Policy for testing."""
    policy = Mock(spec=Policy)
    policy.decide_text = Mock(return_value=Mock(
        use_wordart=False,
        preset=None,
        use_text_to_path=False,
        use_embedding=False,
        confidence=0.5
    ))
    return policy


@pytest.fixture
def config():
    """Default configuration for testing."""
    return FontConversionConfig()


@pytest.fixture
def simple_text_frame():
    """Create a simple text frame for testing."""
    run = Mock()
    run.text = "Hello"
    run.font_family = "Arial"
    run.font_size_pt = 12
    run.bold = False
    run.italic = False
    run.underline = False
    run.strike = False
    # Mock shouldn't have 'effects' attribute
    if hasattr(run, 'effects'):
        delattr(run, 'effects')

    frame = Mock()
    frame.runs = [run]
    # Mock shouldn't have 'transform' attribute initially
    if hasattr(frame, 'transform'):
        delattr(frame, 'transform')
    return frame


@pytest.fixture
def complex_text_frame():
    """Create a complex text frame for testing."""
    runs = []
    for i in range(6):  # Multiple runs
        run = Mock(spec=Run)
        run.text = f"Text{i}"
        run.font_family = "Times" if i % 2 else "Arial"  # Multiple fonts
        run.font_size_pt = 12 + i  # Varying sizes
        run.bold = i % 2 == 0
        run.italic = False
        run.underline = i == 2
        run.strike = False
        runs.append(run)

    frame = Mock(spec=TextFrame)
    frame.runs = runs
    frame.transform = Mock()  # Has transform
    return frame


@pytest.fixture
def selector(mock_services, mock_policy, config):
    """Create FontStrategySelector for testing."""
    return FontStrategySelector(mock_services, mock_policy, config)


class TestFontStrategySelectorInitialization:
    """Test FontStrategySelector initialization."""

    def test_initialization(self, mock_services, mock_policy, config):
        """Test selector initialization."""
        selector = FontStrategySelector(mock_services, mock_policy, config)

        assert selector.services == mock_services
        assert selector.policy == mock_policy
        assert selector.config == config
        assert selector._font_cache == {}

    def test_logger_setup(self, mock_services, mock_policy, config):
        """Test logger setup."""
        selector = FontStrategySelector(mock_services, mock_policy, config)
        assert selector.logger is not None


class TestComplexityAnalysis:
    """Test text complexity analysis logic."""

    def test_simple_complexity(self, selector, simple_text_frame):
        """Test simple complexity detection."""
        complexity = selector._analyze_text_complexity(simple_text_frame)
        assert complexity == FontComplexity.SIMPLE

    def test_moderate_complexity_multiple_runs(self, selector):
        """Test moderate complexity with multiple runs."""
        runs = []
        for i in range(2):  # 2 runs - moderate (score: 1)
            run = Mock()
            run.text = f"Text{i}"
            run.font_family = "Arial"
            run.font_size_pt = 12
            run.underline = False
            run.strike = False
            # Explicitly set that this run doesn't have effects attribute
            del run.effects
            runs.append(run)

        frame = Mock()
        frame.runs = runs
        # Explicitly set that this frame doesn't have transform
        del frame.transform

        complexity = selector._analyze_text_complexity(frame)
        assert complexity == FontComplexity.MODERATE

    def test_complex_complexity_with_transform(self, selector, simple_text_frame):
        """Test complex complexity due to transform."""
        simple_text_frame.transform = Mock()  # Add transform

        complexity = selector._analyze_text_complexity(simple_text_frame)
        assert complexity == FontComplexity.COMPLEX

    def test_complex_complexity_multiple_fonts(self, selector):
        """Test complex complexity due to multiple fonts."""
        runs = []
        for text, family in [("Hello", "Arial"), ("World", "Times")]:
            run = Mock()
            run.text = text
            run.font_family = family
            run.font_size_pt = 12
            run.underline = False
            run.strike = False
            if hasattr(run, 'effects'):
                delattr(run, 'effects')
            runs.append(run)

        frame = Mock()
        frame.runs = runs
        if hasattr(frame, 'transform'):
            delattr(frame, 'transform')

        complexity = selector._analyze_text_complexity(frame)
        assert complexity == FontComplexity.COMPLEX

    def test_extreme_complexity(self, selector, complex_text_frame):
        """Test extreme complexity detection."""
        complexity = selector._analyze_text_complexity(complex_text_frame)
        assert complexity == FontComplexity.EXTREME

    def test_complexity_with_special_characters(self, selector, simple_text_frame):
        """Test complexity with special characters."""
        simple_text_frame.runs[0].text = "Hello 世界"  # Contains unicode

        complexity = selector._analyze_text_complexity(simple_text_frame)
        assert complexity == FontComplexity.MODERATE  # +1 for special chars

    def test_complexity_with_line_breaks(self, selector, simple_text_frame):
        """Test complexity with line breaks."""
        simple_text_frame.runs[0].text = "Hello\nWorld"

        complexity = selector._analyze_text_complexity(simple_text_frame)
        assert complexity == FontComplexity.MODERATE  # +1 for line breaks


class TestFontAvailabilityCheck:
    """Test font availability checking logic."""

    def test_font_available_from_service(self, selector, simple_text_frame):
        """Test font availability check using service."""
        selector.services.font_service.is_font_available.return_value = True

        available = selector._check_font_availability(simple_text_frame)

        assert available is True
        selector.services.font_service.is_font_available.assert_called_with("Arial")

    def test_font_not_available(self, selector, simple_text_frame):
        """Test when font is not available."""
        selector.services.font_service.is_font_available.return_value = False

        available = selector._check_font_availability(simple_text_frame)

        assert available is False

    def test_font_availability_cached(self, selector, simple_text_frame):
        """Test font availability caching."""
        selector.services.font_service.is_font_available.return_value = True

        # First call
        available1 = selector._check_font_availability(simple_text_frame)
        # Second call
        available2 = selector._check_font_availability(simple_text_frame)

        assert available1 is True
        assert available2 is True
        # Service should only be called once due to caching
        selector.services.font_service.is_font_available.assert_called_once()

    def test_font_availability_service_error(self, selector, simple_text_frame):
        """Test error handling in font availability check."""
        selector.services.font_service.is_font_available.side_effect = Exception("Service error")

        available = selector._check_font_availability(simple_text_frame)

        assert available is False  # Conservative default

    def test_empty_text_frame(self, selector):
        """Test font availability with empty text frame."""
        frame = Mock(runs=[])

        available = selector._check_font_availability(frame)

        # Should check Arial (default)
        selector.services.font_service.is_font_available.assert_called_with("Arial")


class TestPolicyDecisions:
    """Test policy engine integration."""

    def test_policy_decisions_basic(self, selector, simple_text_frame):
        """Test basic policy decision extraction."""
        selector.policy.decide_text.return_value = Mock(
            use_wordart=True,
            preset="textArchUp",
            use_text_to_path=False,
            use_embedding=False,
            confidence=0.8
        )

        decisions = selector._get_policy_decisions(simple_text_frame, {})

        assert decisions['wordart_opportunity'] is True
        assert decisions['wordart_preset'] == "textArchUp"
        assert decisions['text_to_path_recommended'] is False
        assert decisions['embedding_recommended'] is False
        assert decisions['confidence'] == 0.8

    def test_policy_decisions_error_handling(self, selector, simple_text_frame):
        """Test policy decision error handling."""
        selector.policy.decide_text.side_effect = Exception("Policy error")

        decisions = selector._get_policy_decisions(simple_text_frame, {})

        assert decisions['wordart_opportunity'] is False
        assert decisions['wordart_preset'] is None
        assert decisions['confidence'] == 0.1

    def test_policy_decisions_missing_attributes(self, selector, simple_text_frame):
        """Test handling of policy results with missing attributes."""
        selector.policy.decide_text.return_value = Mock()  # No attributes

        decisions = selector._get_policy_decisions(simple_text_frame, {})

        assert decisions['wordart_opportunity'] is False
        assert decisions['wordart_preset'] is None
        assert decisions['confidence'] == 0.5  # Default


class TestStrategySelection:
    """Test primary strategy selection logic."""

    def test_wordart_strategy_selected(self, selector, simple_text_frame):
        """Test WordArt strategy selection."""
        policy_decisions = {
            'wordart_opportunity': True,
            'wordart_preset': 'textArchUp',
            'confidence': 0.9
        }

        strategy, confidence = selector._select_primary_strategy(
            simple_text_frame, FontComplexity.SIMPLE, True, policy_decisions
        )

        assert strategy == FontStrategy.WORDART
        assert confidence == 0.9

    def test_system_font_strategy_selected(self, selector, simple_text_frame):
        """Test system font strategy selection."""
        policy_decisions = {'wordart_opportunity': False}

        strategy, confidence = selector._select_primary_strategy(
            simple_text_frame, FontComplexity.SIMPLE, True, policy_decisions
        )

        assert strategy == FontStrategy.SYSTEM
        assert confidence == 0.9

    def test_path_for_complex_text(self, selector, complex_text_frame):
        """Test path strategy for complex text."""
        policy_decisions = {'wordart_opportunity': False}

        strategy, confidence = selector._select_primary_strategy(
            complex_text_frame, FontComplexity.EXTREME, True, policy_decisions
        )

        assert strategy == FontStrategy.PATH
        assert confidence == 0.8

    def test_embedded_font_strategy(self, selector, simple_text_frame):
        """Test embedded font strategy when font unavailable."""
        selector.config = FontConversionConfig(enable_font_embedding=True)
        policy_decisions = {'wordart_opportunity': False}

        strategy, confidence = selector._select_primary_strategy(
            simple_text_frame, FontComplexity.SIMPLE, False, policy_decisions
        )

        assert strategy == FontStrategy.EMBEDDED
        assert confidence == 0.7

    def test_fallback_strategy(self, selector, simple_text_frame):
        """Test fallback strategy selection."""
        # Disable all advanced strategies
        selector.config = FontConversionConfig(
            enable_wordart=False,
            enable_text_to_path=False,
            enable_font_embedding=False
        )
        policy_decisions = {'wordart_opportunity': False}

        strategy, confidence = selector._select_primary_strategy(
            simple_text_frame, FontComplexity.SIMPLE, False, policy_decisions
        )

        assert strategy == FontStrategy.FALLBACK
        assert confidence == 0.3

    def test_wordart_confidence_threshold(self, selector, simple_text_frame):
        """Test WordArt confidence threshold enforcement."""
        selector.config = FontConversionConfig(wordart_confidence_threshold=0.9)
        policy_decisions = {
            'wordart_opportunity': True,
            'wordart_preset': None,  # Low confidence (0.7)
            'confidence': 0.7
        }

        strategy, confidence = selector._select_primary_strategy(
            simple_text_frame, FontComplexity.SIMPLE, True, policy_decisions
        )

        # Should fall back to system font due to low confidence
        assert strategy == FontStrategy.SYSTEM
        assert confidence == 0.9


class TestFallbackChainBuilding:
    """Test fallback chain construction."""

    def test_system_font_fallback_chain(self, selector):
        """Test fallback chain for system font strategy."""
        chain = selector._build_fallback_chain(
            FontStrategy.SYSTEM, FontComplexity.SIMPLE, True
        )

        expected = [FontStrategy.WORDART, FontStrategy.PATH, FontStrategy.FALLBACK]
        assert chain == expected

    def test_wordart_fallback_chain(self, selector):
        """Test fallback chain for WordArt strategy."""
        chain = selector._build_fallback_chain(
            FontStrategy.WORDART, FontComplexity.SIMPLE, True
        )

        expected = [FontStrategy.SYSTEM, FontStrategy.PATH, FontStrategy.FALLBACK]
        assert chain == expected

    def test_path_fallback_chain(self, selector):
        """Test fallback chain for text-to-path strategy."""
        chain = selector._build_fallback_chain(
            FontStrategy.PATH, FontComplexity.COMPLEX, True
        )

        expected = [FontStrategy.SYSTEM, FontStrategy.WORDART, FontStrategy.FALLBACK]
        assert chain == expected

    def test_fallback_primary_no_chain(self, selector):
        """Test no fallback chain for fallback strategy."""
        chain = selector._build_fallback_chain(
            FontStrategy.FALLBACK, FontComplexity.SIMPLE, False
        )

        assert chain == []

    def test_disabled_strategies_not_in_chain(self, selector):
        """Test that disabled strategies are not in fallback chain."""
        selector.config = FontConversionConfig(
            enable_wordart=False,
            enable_text_to_path=False
        )

        chain = selector._build_fallback_chain(
            FontStrategy.SYSTEM, FontComplexity.SIMPLE, True
        )

        assert FontStrategy.WORDART not in chain
        assert FontStrategy.PATH not in chain
        assert chain == [FontStrategy.FALLBACK]


class TestFullSelection:
    """Test complete strategy selection process."""

    def test_successful_selection(self, selector, simple_text_frame):
        """Test successful strategy selection."""
        result = selector.select(simple_text_frame, {})

        assert isinstance(result, SelectionResult)
        assert result.primary_strategy in FontStrategy
        assert isinstance(result.fallback_chain, list)
        assert isinstance(result.font_available, bool)
        assert result.complexity in FontComplexity
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.metadata, dict)

    def test_selection_with_error(self, selector, simple_text_frame):
        """Test selection error handling."""
        # Force an error in complexity analysis
        selector._analyze_text_complexity = Mock(side_effect=Exception("Test error"))

        result = selector.select(simple_text_frame, {})

        assert result.primary_strategy == FontStrategy.FALLBACK
        assert result.confidence == 0.1
        assert 'error' in result.metadata

    def test_metadata_includes_analysis_info(self, selector, simple_text_frame):
        """Test that metadata includes analysis information."""
        result = selector.select(simple_text_frame, {})

        assert 'policy_decisions' in result.metadata
        assert 'font_metrics' in result.metadata
        assert 'transform_detected' in result.metadata

    def test_font_metrics_extraction(self, selector, simple_text_frame):
        """Test font metrics extraction."""
        metrics = selector._get_font_metrics(simple_text_frame)

        assert metrics['font_family'] == "Arial"
        assert metrics['font_size_pt'] == 12
        assert 'estimated_width' in metrics
        assert 'estimated_height' in metrics

    def test_font_metrics_error_handling(self, selector, simple_text_frame):
        """Test font metrics error handling."""
        selector.services.font_service.get_font_metrics.side_effect = Exception("Metrics error")

        metrics = selector._get_font_metrics(simple_text_frame)

        assert 'error' in metrics
        assert metrics['font_family'] == "Arial"

    def test_empty_text_frame_metrics(self, selector):
        """Test font metrics with empty text frame."""
        frame = Mock(runs=[])

        metrics = selector._get_font_metrics(frame)

        assert metrics == {}


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_simple_arial_text(self, selector):
        """Test simple Arial text selection."""
        run = Mock(text="Hello", font_family="Arial", font_size_pt=12,
                  bold=False, italic=False, underline=False, strike=False)
        frame = Mock(runs=[run])

        result = selector.select(frame, {})

        assert result.complexity == FontComplexity.SIMPLE
        assert result.primary_strategy in [FontStrategy.SYSTEM, FontStrategy.WORDART]
        assert result.confidence > 0.5

    def test_complex_styled_text(self, selector):
        """Test complex styled text selection."""
        runs = [
            Mock(text="Bold", font_family="Arial", font_size_pt=16,
                bold=True, italic=False, underline=False, strike=False),
            Mock(text=" and ", font_family="Arial", font_size_pt=12,
                bold=False, italic=False, underline=False, strike=False),
            Mock(text="italic", font_family="Times", font_size_pt=14,
                bold=False, italic=True, underline=True, strike=False)
        ]
        frame = Mock(runs=runs)
        frame.transform = Mock()  # Has transform

        result = selector.select(frame, {})

        assert result.complexity in [FontComplexity.COMPLEX, FontComplexity.EXTREME]
        assert FontStrategy.PATH in [result.primary_strategy] + result.fallback_chain

    def test_unavailable_font_handling(self, selector, simple_text_frame):
        """Test handling of unavailable fonts."""
        selector.services.font_service.is_font_available.return_value = False

        result = selector.select(simple_text_frame, {})

        assert result.font_available is False
        # Should prefer path or embedding over system font
        assert result.primary_strategy in [
            FontStrategy.PATH, FontStrategy.EMBEDDED, FontStrategy.WORDART, FontStrategy.FALLBACK
        ]