#!/usr/bin/env python3
"""
Unit tests for SmartFontConverter

Tests the main font conversion orchestration logic including strategy
selection, execution, and fallback handling.
"""

import pytest
from unittest.mock import Mock, patch
import time
from dataclasses import dataclass

from core.converters.font.smart_converter import SmartFontConverter
from core.converters.font.types import (
    FontConversionConfig,
    FontConversionResult,
    FontComplexity,
    HandlerResult,
    ExecutionResult
)
from core.ir import TextFrame, Run, Point, Rect
from core.ir.font_metadata import FontStrategy
from core.services.conversion_services import ConversionServices
from core.policy import Policy


@pytest.fixture
def mock_services():
    """Mock ConversionServices for testing."""
    services = Mock(spec=ConversionServices)
    services.font_service = Mock()
    services.unit_converter = Mock()
    return services


@pytest.fixture
def mock_policy():
    """Mock Policy for testing."""
    return Mock(spec=Policy)


@pytest.fixture
def sample_text_frame():
    """Create a sample TextFrame for testing."""
    run = Mock(spec=Run)
    run.text = "Hello World"
    run.font_family = "Arial"
    run.font_size_pt = 12
    run.bold = False
    run.italic = False
    run.underline = False
    run.strike = False
    run.rgb = "000000"

    frame = Mock(spec=TextFrame)
    frame.runs = [run]
    frame.origin = Point(x=0, y=0)
    frame.bbox = Rect(x=0, y=0, width=100, height=20)
    frame.anchor = "start"

    return frame


@pytest.fixture
def converter(mock_services, mock_policy):
    """Create SmartFontConverter instance for testing."""
    return SmartFontConverter(mock_services, mock_policy)


class TestSmartFontConverterInitialization:
    """Test SmartFontConverter initialization."""

    def test_initialization_with_defaults(self, mock_services, mock_policy):
        """Test initialization with default configuration."""
        converter = SmartFontConverter(mock_services, mock_policy)

        assert converter.services == mock_services
        assert converter.policy == mock_policy
        assert isinstance(converter.config, FontConversionConfig)
        assert converter.strategy_selector is not None
        assert converter.strategy_executor is not None
        assert converter.stats['total_conversions'] == 0

    def test_initialization_with_custom_config(self, mock_services, mock_policy):
        """Test initialization with custom configuration."""
        config = FontConversionConfig(
            enable_wordart=False,
            verbose_logging=True,
            timeout_ms=1000.0
        )

        converter = SmartFontConverter(mock_services, mock_policy, config)

        assert converter.config == config
        assert not converter.config.enable_wordart
        assert converter.config.verbose_logging
        assert converter.config.timeout_ms == 1000.0

    def test_statistics_initialization(self, converter):
        """Test that statistics are properly initialized."""
        stats = converter.get_statistics()

        assert stats['total_conversions'] == 0
        assert stats['successful_conversions'] == 0
        assert stats['failed_conversions'] == 0
        assert stats['strategy_usage'] == {}
        assert stats['total_time_ms'] == 0.0
        assert stats['average_time_ms'] == 0.0


class TestTextComplexityAnalysis:
    """Test text complexity analysis logic."""

    def test_simple_complexity(self, converter, sample_text_frame):
        """Test detection of simple text complexity."""
        # Single run, no transforms, no effects
        complexity = converter._analyze_complexity(sample_text_frame)
        assert complexity == FontComplexity.SIMPLE

    def test_moderate_complexity(self, converter, sample_text_frame):
        """Test detection of moderate text complexity."""
        # Multiple runs, no transforms
        run2 = Mock()
        run2.font_family = "Arial"
        run2.underline = False
        run2.strike = False
        sample_text_frame.runs = [sample_text_frame.runs[0], run2]

        complexity = converter._analyze_complexity(sample_text_frame)
        assert complexity == FontComplexity.MODERATE

    def test_complex_complexity_with_transform(self, converter, sample_text_frame):
        """Test detection of complex text with transforms."""
        sample_text_frame.transform = Mock()  # Has transform

        complexity = converter._analyze_complexity(sample_text_frame)
        assert complexity == FontComplexity.COMPLEX

    def test_complex_complexity_with_multiple_fonts(self, converter, sample_text_frame):
        """Test detection of complex text with multiple fonts."""
        run2 = Mock()
        run2.font_family = "Times"  # Different font
        run2.underline = False
        run2.strike = False
        sample_text_frame.runs = [sample_text_frame.runs[0], run2]

        complexity = converter._analyze_complexity(sample_text_frame)
        assert complexity == FontComplexity.COMPLEX

    def test_extreme_complexity(self, converter, sample_text_frame):
        """Test detection of extreme text complexity."""
        # More than 5 runs
        runs = []
        for i in range(6):
            run = Mock()
            run.font_family = "Arial"
            run.underline = False
            run.strike = False
            runs.append(run)
        sample_text_frame.runs = runs

        complexity = converter._analyze_complexity(sample_text_frame)
        assert complexity == FontComplexity.EXTREME


class TestFontConversionFlow:
    """Test the main font conversion flow."""

    @patch('core.converters.font.smart_converter.time.perf_counter')
    def test_successful_conversion(self, mock_time, converter, sample_text_frame):
        """Test successful font conversion flow."""
        # Mock timing
        mock_time.side_effect = [0.0, 0.001, 0.002, 0.003]  # start, selection, execution, end

        # Mock strategy selector
        from core.converters.font.strategy_selector import SelectionResult
        selection_result = SelectionResult(
            primary_strategy=FontStrategy.SYSTEM,
            fallback_chain=[FontStrategy.FALLBACK],
            font_available=True,
            complexity=FontComplexity.SIMPLE,
            confidence=0.9,
            metadata={}
        )
        converter.strategy_selector.select = Mock(return_value=selection_result)

        # Mock strategy executor
        execution_result = ExecutionResult(
            strategy=FontStrategy.SYSTEM,
            handler_result=HandlerResult(
                success=True,
                xml_content="<test>XML content</test>",
                confidence=0.9,
                metadata={'test': 'value'}
            ),
            execution_time_ms=1.0
        )
        converter._execute_with_fallback = Mock(return_value=execution_result)

        # Execute conversion
        result = converter.convert(sample_text_frame)

        # Verify result
        assert isinstance(result, FontConversionResult)
        assert result.strategy_used == FontStrategy.SYSTEM
        assert result.drawingml_xml == "<test>XML content</test>"
        assert result.confidence == 0.9
        assert result.complexity == FontComplexity.SIMPLE
        assert result.font_available is True
        assert result.total_time_ms == 3.0
        assert result.strategy_selection_ms == 1.0
        assert result.execution_time_ms == 1.0

    def test_conversion_with_invalid_input(self, converter):
        """Test conversion with invalid input."""
        with pytest.raises(ValueError, match="TextFrame must have at least one run"):
            converter.convert(None)

        # Empty text frame
        empty_frame = Mock()
        empty_frame.runs = []

        with pytest.raises(ValueError, match="TextFrame must have at least one run"):
            converter.convert(empty_frame)

    @patch('core.converters.font.smart_converter.time.perf_counter')
    def test_conversion_with_error(self, mock_time, converter, sample_text_frame):
        """Test conversion error handling."""
        mock_time.side_effect = [0.0, 0.005]  # start, end

        # Mock strategy selector to raise exception
        converter.strategy_selector.select = Mock(side_effect=RuntimeError("Test error"))

        # Execute conversion
        result = converter.convert(sample_text_frame)

        # Verify error result
        assert result.strategy_used == FontStrategy.FALLBACK
        assert result.confidence == 0.1
        assert result.font_available is False
        assert result.total_time_ms == 5.0
        assert "Conversion failed: Test error" in result.warnings


class TestFallbackExecution:
    """Test fallback execution logic."""

    def test_successful_primary_strategy(self, converter, sample_text_frame):
        """Test successful execution with primary strategy."""
        handler_result = HandlerResult(
            success=True,
            xml_content="<primary>success</primary>",
            confidence=0.9
        )
        execution_result = ExecutionResult(
            strategy=FontStrategy.SYSTEM,
            handler_result=handler_result,
            execution_time_ms=1.0
        )
        converter.strategy_executor.execute = Mock(return_value=execution_result)

        result = converter._execute_with_fallback(
            sample_text_frame,
            FontStrategy.SYSTEM,
            [FontStrategy.FALLBACK],
            {}
        )

        assert result.strategy == FontStrategy.SYSTEM
        assert result.fallback_attempted is False
        assert result.fallback_strategy is None

    def test_fallback_after_primary_failure(self, converter, sample_text_frame):
        """Test fallback execution after primary strategy fails."""
        # Primary fails
        primary_result = ExecutionResult(
            strategy=FontStrategy.SYSTEM,
            handler_result=HandlerResult(success=False, xml_content="", confidence=0.0),
            execution_time_ms=1.0
        )

        # Fallback succeeds
        fallback_result = ExecutionResult(
            strategy=FontStrategy.FALLBACK,
            handler_result=HandlerResult(
                success=True,
                xml_content="<fallback>success</fallback>",
                confidence=0.5
            ),
            execution_time_ms=1.0
        )

        converter.strategy_executor.execute = Mock(side_effect=[primary_result, fallback_result])

        result = converter._execute_with_fallback(
            sample_text_frame,
            FontStrategy.SYSTEM,
            [FontStrategy.FALLBACK],
            {}
        )

        assert result.strategy == FontStrategy.FALLBACK
        assert result.fallback_attempted is True
        assert result.fallback_strategy == FontStrategy.SYSTEM

    def test_all_strategies_fail(self, converter, sample_text_frame):
        """Test when all strategies fail."""
        failed_result = ExecutionResult(
            strategy=FontStrategy.SYSTEM,
            handler_result=HandlerResult(success=False, xml_content="", confidence=0.0),
            execution_time_ms=1.0
        )
        converter.strategy_executor.execute = Mock(return_value=failed_result)

        with pytest.raises(RuntimeError, match="All strategies failed"):
            converter._execute_with_fallback(
                sample_text_frame,
                FontStrategy.SYSTEM,
                [FontStrategy.FALLBACK],
                {}
            )


class TestStatisticsTracking:
    """Test statistics tracking functionality."""

    def test_statistics_update_success(self, converter):
        """Test statistics update for successful conversion."""
        result = FontConversionResult(
            strategy_used=FontStrategy.SYSTEM,
            drawingml_xml="<test/>",
            confidence=0.9,
            strategies_attempted=[FontStrategy.SYSTEM],
            fallback_chain=[],
            total_time_ms=10.0,
            strategy_selection_ms=2.0,
            execution_time_ms=8.0,
            complexity=FontComplexity.SIMPLE,
            font_available=True
        )

        converter._update_statistics(result, success=True)

        stats = converter.get_statistics()
        assert stats['total_conversions'] == 1
        assert stats['successful_conversions'] == 1
        assert stats['failed_conversions'] == 0
        assert stats['strategy_usage']['system'] == 1
        assert stats['total_time_ms'] == 10.0
        assert stats['average_time_ms'] == 10.0

    def test_statistics_update_failure(self, converter):
        """Test statistics update for failed conversion."""
        converter._update_statistics(None, success=False)

        stats = converter.get_statistics()
        assert stats['total_conversions'] == 1
        assert stats['successful_conversions'] == 0
        assert stats['failed_conversions'] == 1
        assert stats['average_time_ms'] == 0

    def test_statistics_reset(self, converter):
        """Test statistics reset functionality."""
        # Add some statistics
        converter.stats['total_conversions'] = 5
        converter.stats['successful_conversions'] = 3

        # Reset
        converter.reset_statistics()

        stats = converter.get_statistics()
        assert stats['total_conversions'] == 0
        assert stats['successful_conversions'] == 0
        assert stats['failed_conversions'] == 0


class TestFallbackXMLGeneration:
    """Test fallback XML generation."""

    def test_generate_fallback_xml(self, converter, sample_text_frame):
        """Test fallback XML generation."""
        xml = converter._generate_fallback_xml(sample_text_frame)

        assert "<p:sp>" in xml
        assert "<a:t>Hello World</a:t>" in xml
        assert 'typeface="Arial"' in xml
        assert 'x="0"' in xml
        assert 'y="0"' in xml

    def test_create_error_result(self, converter, sample_text_frame):
        """Test error result creation."""
        error = RuntimeError("Test error")
        result = converter._create_error_result(sample_text_frame, error, 5.0)

        assert result.strategy_used == FontStrategy.FALLBACK
        assert result.confidence == 0.1
        assert result.font_available is False
        assert result.total_time_ms == 5.0
        assert "Conversion failed: Test error" in result.warnings
        assert result.drawingml_xml is not None