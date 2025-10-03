#!/usr/bin/env python3
"""
Unit tests for font converter type definitions

Tests dataclasses, enums, and validation logic for the font conversion system.
"""

import pytest
from dataclasses import FrozenInstanceError

from core.converters.font.types import (
    FontComplexity,
    FontConversionConfig,
    HandlerResult,
    ExecutionResult,
    FontConversionResult
)
from core.ir.font_metadata import FontStrategy


class TestFontComplexity:
    """Test FontComplexity enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert FontComplexity.SIMPLE.value == "simple"
        assert FontComplexity.MODERATE.value == "moderate"
        assert FontComplexity.COMPLEX.value == "complex"
        assert FontComplexity.EXTREME.value == "extreme"

    def test_enum_ordering(self):
        """Test enum comparison (if needed for complexity scoring)."""
        complexities = list(FontComplexity)
        assert len(complexities) == 4
        assert FontComplexity.SIMPLE in complexities
        assert FontComplexity.EXTREME in complexities


class TestFontConversionConfig:
    """Test FontConversionConfig dataclass."""

    def test_default_values(self):
        """Test configuration with default values."""
        config = FontConversionConfig()

        # Strategy options
        assert config.enable_wordart is True
        assert config.enable_text_to_path is True
        assert config.enable_font_embedding is False

        # Performance settings
        assert config.cache_size == 256
        assert config.timeout_ms == 500.0

        # Quality settings
        assert config.path_optimization_level == 1
        assert config.wordart_confidence_threshold == 0.7

        # Fallback behavior
        assert config.fallback_font_chain == ['Arial', 'Calibri', 'Helvetica', 'sans-serif']

        # Debug options
        assert config.verbose_logging is False
        assert config.performance_tracking is True

    def test_custom_values(self):
        """Test configuration with custom values."""
        config = FontConversionConfig(
            enable_wordart=False,
            cache_size=512,
            timeout_ms=1000.0,
            path_optimization_level=2,
            wordart_confidence_threshold=0.8,
            fallback_font_chain=['Times', 'Arial'],
            verbose_logging=True,
            performance_tracking=False
        )

        assert config.enable_wordart is False
        assert config.cache_size == 512
        assert config.timeout_ms == 1000.0
        assert config.path_optimization_level == 2
        assert config.wordart_confidence_threshold == 0.8
        assert config.fallback_font_chain == ['Times', 'Arial']
        assert config.verbose_logging is True
        assert config.performance_tracking is False

    def test_frozen_config(self):
        """Test that configuration is frozen (immutable)."""
        config = FontConversionConfig()

        with pytest.raises(FrozenInstanceError):
            config.enable_wordart = False

        with pytest.raises(FrozenInstanceError):
            config.cache_size = 512


class TestHandlerResult:
    """Test HandlerResult dataclass."""

    def test_valid_result(self):
        """Test creation of valid handler result."""
        result = HandlerResult(
            success=True,
            xml_content="<test>content</test>",
            confidence=0.8,
            metadata={'key': 'value'},
            warnings=['warning1'],
            error=None
        )

        assert result.success is True
        assert result.xml_content == "<test>content</test>"
        assert result.confidence == 0.8
        assert result.metadata == {'key': 'value'}
        assert result.warnings == ['warning1']
        assert result.error is None

    def test_minimal_valid_result(self):
        """Test creation with minimal required fields."""
        result = HandlerResult(
            success=True,
            xml_content="<test/>",
            confidence=0.5
        )

        assert result.success is True
        assert result.xml_content == "<test/>"
        assert result.confidence == 0.5
        assert result.metadata == {}
        assert result.warnings == []
        assert result.error is None

    def test_confidence_validation_bounds(self):
        """Test confidence value validation."""
        # Valid confidence values
        HandlerResult(success=True, xml_content="<test/>", confidence=0.0)
        HandlerResult(success=True, xml_content="<test/>", confidence=0.5)
        HandlerResult(success=True, xml_content="<test/>", confidence=1.0)

        # Invalid confidence values
        with pytest.raises(ValueError, match="Confidence must be 0.0-1.0"):
            HandlerResult(success=True, xml_content="<test/>", confidence=-0.1)

        with pytest.raises(ValueError, match="Confidence must be 0.0-1.0"):
            HandlerResult(success=True, xml_content="<test/>", confidence=1.1)

    def test_success_xml_validation(self):
        """Test that successful results must have XML content."""
        # Valid successful result
        HandlerResult(success=True, xml_content="<test/>", confidence=0.8)

        # Invalid: successful but no XML
        with pytest.raises(ValueError, match="Successful result must have XML content"):
            HandlerResult(success=True, xml_content="", confidence=0.8)

        # Valid: failed result can have empty XML
        HandlerResult(success=False, xml_content="", confidence=0.0)

    def test_error_result(self):
        """Test creation of error result."""
        error = RuntimeError("Test error")
        result = HandlerResult(
            success=False,
            xml_content="",
            confidence=0.0,
            error=error,
            warnings=["Conversion failed"]
        )

        assert result.success is False
        assert result.xml_content == ""
        assert result.confidence == 0.0
        assert result.error == error
        assert result.warnings == ["Conversion failed"]


class TestExecutionResult:
    """Test ExecutionResult dataclass."""

    def test_basic_execution_result(self):
        """Test basic execution result creation."""
        handler_result = HandlerResult(
            success=True,
            xml_content="<test/>",
            confidence=0.9
        )

        result = ExecutionResult(
            strategy=FontStrategy.SYSTEM,
            handler_result=handler_result,
            execution_time_ms=5.0
        )

        assert result.strategy == FontStrategy.SYSTEM
        assert result.handler_result == handler_result
        assert result.execution_time_ms == 5.0
        assert result.fallback_attempted is False
        assert result.fallback_strategy is None

    def test_execution_result_with_fallback(self):
        """Test execution result with fallback information."""
        handler_result = HandlerResult(
            success=True,
            xml_content="<fallback/>",
            confidence=0.6
        )

        result = ExecutionResult(
            strategy=FontStrategy.FALLBACK,
            handler_result=handler_result,
            execution_time_ms=10.0,
            fallback_attempted=True,
            fallback_strategy=FontStrategy.SYSTEM
        )

        assert result.strategy == FontStrategy.FALLBACK
        assert result.fallback_attempted is True
        assert result.fallback_strategy == FontStrategy.SYSTEM


class TestFontConversionResult:
    """Test FontConversionResult dataclass."""

    def test_valid_conversion_result(self):
        """Test creation of valid font conversion result."""
        result = FontConversionResult(
            strategy_used=FontStrategy.SYSTEM,
            drawingml_xml="<test>content</test>",
            confidence=0.9,
            strategies_attempted=[FontStrategy.SYSTEM],
            fallback_chain=[FontStrategy.FALLBACK],
            total_time_ms=15.0,
            strategy_selection_ms=3.0,
            execution_time_ms=12.0,
            complexity=FontComplexity.SIMPLE,
            font_available=True,
            wordart_preset="preset1",
            path_count=5,
            metadata={'test': 'value'},
            warnings=['warning1']
        )

        assert result.strategy_used == FontStrategy.SYSTEM
        assert result.drawingml_xml == "<test>content</test>"
        assert result.confidence == 0.9
        assert result.strategies_attempted == [FontStrategy.SYSTEM]
        assert result.fallback_chain == [FontStrategy.FALLBACK]
        assert result.total_time_ms == 15.0
        assert result.strategy_selection_ms == 3.0
        assert result.execution_time_ms == 12.0
        assert result.complexity == FontComplexity.SIMPLE
        assert result.font_available is True
        assert result.wordart_preset == "preset1"
        assert result.path_count == 5
        assert result.metadata == {'test': 'value'}
        assert result.warnings == ['warning1']

    def test_minimal_conversion_result(self):
        """Test creation with minimal required fields."""
        result = FontConversionResult(
            strategy_used=FontStrategy.SYSTEM,
            drawingml_xml="<test/>",
            confidence=0.8,
            strategies_attempted=[FontStrategy.SYSTEM],
            fallback_chain=[],
            total_time_ms=10.0,
            strategy_selection_ms=2.0,
            execution_time_ms=8.0,
            complexity=FontComplexity.SIMPLE,
            font_available=True
        )

        assert result.strategy_used == FontStrategy.SYSTEM
        assert result.wordart_preset is None
        assert result.path_count is None
        assert result.metadata == {}
        assert result.warnings == []

    def test_drawingml_xml_validation(self):
        """Test that result must have DrawingML XML."""
        # Valid result
        FontConversionResult(
            strategy_used=FontStrategy.SYSTEM,
            drawingml_xml="<test/>",
            confidence=0.8,
            strategies_attempted=[FontStrategy.SYSTEM],
            fallback_chain=[],
            total_time_ms=10.0,
            strategy_selection_ms=2.0,
            execution_time_ms=8.0,
            complexity=FontComplexity.SIMPLE,
            font_available=True
        )

        # Invalid: empty XML
        with pytest.raises(ValueError, match="Conversion result must have DrawingML XML"):
            FontConversionResult(
                strategy_used=FontStrategy.SYSTEM,
                drawingml_xml="",
                confidence=0.8,
                strategies_attempted=[FontStrategy.SYSTEM],
                fallback_chain=[],
                total_time_ms=10.0,
                strategy_selection_ms=2.0,
                execution_time_ms=8.0,
                complexity=FontComplexity.SIMPLE,
                font_available=True
            )

    def test_confidence_validation_in_result(self):
        """Test confidence validation in conversion result."""
        # Valid confidence
        FontConversionResult(
            strategy_used=FontStrategy.SYSTEM,
            drawingml_xml="<test/>",
            confidence=0.8,
            strategies_attempted=[FontStrategy.SYSTEM],
            fallback_chain=[],
            total_time_ms=10.0,
            strategy_selection_ms=2.0,
            execution_time_ms=8.0,
            complexity=FontComplexity.SIMPLE,
            font_available=True
        )

        # Invalid confidence
        with pytest.raises(ValueError, match="Confidence must be 0.0-1.0"):
            FontConversionResult(
                strategy_used=FontStrategy.SYSTEM,
                drawingml_xml="<test/>",
                confidence=1.5,
                strategies_attempted=[FontStrategy.SYSTEM],
                fallback_chain=[],
                total_time_ms=10.0,
                strategy_selection_ms=2.0,
                execution_time_ms=8.0,
                complexity=FontComplexity.SIMPLE,
                font_available=True
            )

    def test_property_methods(self):
        """Test property methods on conversion result."""
        # High confidence result
        high_confidence_result = FontConversionResult(
            strategy_used=FontStrategy.SYSTEM,
            drawingml_xml="<test/>",
            confidence=0.95,
            strategies_attempted=[FontStrategy.SYSTEM],
            fallback_chain=[],
            total_time_ms=10.0,
            strategy_selection_ms=2.0,
            execution_time_ms=8.0,
            complexity=FontComplexity.SIMPLE,
            font_available=True
        )

        assert high_confidence_result.is_high_confidence is True
        assert high_confidence_result.used_fallback is False

        # Low confidence result with fallback
        low_confidence_result = FontConversionResult(
            strategy_used=FontStrategy.FALLBACK,
            drawingml_xml="<test/>",
            confidence=0.3,
            strategies_attempted=[FontStrategy.SYSTEM, FontStrategy.FALLBACK],
            fallback_chain=[FontStrategy.FALLBACK],
            total_time_ms=20.0,
            strategy_selection_ms=5.0,
            execution_time_ms=15.0,
            complexity=FontComplexity.COMPLEX,
            font_available=False
        )

        assert low_confidence_result.is_high_confidence is False
        assert low_confidence_result.used_fallback is True