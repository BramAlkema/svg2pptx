#!/usr/bin/env python3
"""
Unit tests for FontStrategyExecutor

Tests strategy execution, handler management, error handling,
and performance tracking.
"""

import pytest
from unittest.mock import Mock, patch
import time

from core.converters.font.strategy_executor import FontStrategyExecutor
from core.converters.font.types import FontConversionConfig, ExecutionResult, HandlerResult
from core.converters.font.handlers.base import BaseStrategyHandler
from core.ir import TextFrame, Run, Point, Rect
from core.ir.font_metadata import FontStrategy
from core.services.conversion_services import ConversionServices


class MockHandler(BaseStrategyHandler):
    """Mock handler for testing."""

    def __init__(self, services, should_succeed=True, execution_time=0.001):
        super().__init__(services)
        self.should_succeed = should_succeed
        self.execution_time = execution_time

    def can_handle(self, text_frame, context):
        return True

    def convert(self, text_frame, context):
        # Simulate execution time
        time.sleep(self.execution_time)

        if self.should_succeed:
            return HandlerResult(
                success=True,
                xml_content="<mock>successful conversion</mock>",
                confidence=0.9,
                metadata={'mock': True}
            )
        else:
            return HandlerResult(
                success=False,
                xml_content="",
                confidence=0.0,
                warnings=["Mock conversion failed"]
            )


class FailingHandler(BaseStrategyHandler):
    """Handler that raises exceptions for testing."""

    def can_handle(self, text_frame, context):
        return True

    def convert(self, text_frame, context):
        raise RuntimeError("Mock handler error")


@pytest.fixture
def mock_services():
    """Mock ConversionServices for testing."""
    return Mock(spec=ConversionServices)


@pytest.fixture
def config():
    """Default configuration for testing."""
    return FontConversionConfig(timeout_ms=1000.0)


@pytest.fixture
def simple_text_frame():
    """Create a simple text frame for testing."""
    run = Mock()
    run.text = "Hello"
    run.font_family = "Arial"
    run.font_size_pt = 12

    frame = Mock()
    frame.runs = [run]
    return frame


@pytest.fixture
def executor(mock_services, config):
    """Create FontStrategyExecutor for testing."""
    return FontStrategyExecutor(mock_services, config)


class TestFontStrategyExecutorInitialization:
    """Test FontStrategyExecutor initialization."""

    def test_initialization(self, mock_services, config):
        """Test executor initialization."""
        executor = FontStrategyExecutor(mock_services, config)

        assert executor.services == mock_services
        assert executor.config == config
        assert executor.handlers == {}
        assert executor.stats['total_executions'] == 0

    def test_statistics_initialization(self, executor):
        """Test statistics are properly initialized."""
        stats = executor.get_statistics()

        assert stats['total_executions'] == 0
        assert stats['successful_executions'] == 0
        assert stats['failed_executions'] == 0
        assert stats['strategy_usage'] == {}
        assert stats['total_time_ms'] == 0.0
        assert stats['average_time_ms'] == 0.0
        assert stats['handler_count'] == 0
        assert stats['available_strategies'] == []


class TestHandlerRegistration:
    """Test handler registration and management."""

    def test_register_handler(self, executor, mock_services):
        """Test handler registration."""
        handler_class = MockHandler

        executor.register_handler(FontStrategy.SYSTEM, handler_class)

        assert executor.has_handler(FontStrategy.SYSTEM)
        assert FontStrategy.SYSTEM in executor.handlers
        assert isinstance(executor.handlers[FontStrategy.SYSTEM], MockHandler)

    def test_register_multiple_handlers(self, executor, mock_services):
        """Test registering multiple handlers."""
        executor.register_handler(FontStrategy.SYSTEM, MockHandler)
        executor.register_handler(FontStrategy.FALLBACK, MockHandler)

        assert len(executor.handlers) == 2
        assert executor.has_handler(FontStrategy.SYSTEM)
        assert executor.has_handler(FontStrategy.FALLBACK)

    def test_unregister_handler(self, executor, mock_services):
        """Test handler unregistration."""
        executor.register_handler(FontStrategy.SYSTEM, MockHandler)
        assert executor.has_handler(FontStrategy.SYSTEM)

        executor.unregister_handler(FontStrategy.SYSTEM)
        assert not executor.has_handler(FontStrategy.SYSTEM)
        assert FontStrategy.SYSTEM not in executor.handlers

    def test_get_available_strategies(self, executor, mock_services):
        """Test getting available strategies."""
        executor.register_handler(FontStrategy.SYSTEM, MockHandler)
        executor.register_handler(FontStrategy.FALLBACK, MockHandler)

        strategies = executor.get_available_strategies()
        assert len(strategies) == 2
        assert FontStrategy.SYSTEM in strategies
        assert FontStrategy.FALLBACK in strategies

    def test_register_handler_initialization_failure(self, executor, mock_services):
        """Test handling of handler initialization failures."""
        class BadHandler(BaseStrategyHandler):
            def __init__(self, services):
                raise RuntimeError("Initialization failed")

            def can_handle(self, text_frame, context):
                return True

            def convert(self, text_frame, context):
                pass

        with pytest.raises(RuntimeError):
            executor.register_handler(FontStrategy.SYSTEM, BadHandler)

        assert not executor.has_handler(FontStrategy.SYSTEM)


class TestExecution:
    """Test strategy execution logic."""

    def test_successful_execution(self, executor, mock_services, simple_text_frame):
        """Test successful strategy execution."""
        executor.register_handler(FontStrategy.SYSTEM, MockHandler)

        result = executor.execute(FontStrategy.SYSTEM, simple_text_frame, {})

        assert isinstance(result, ExecutionResult)
        assert result.strategy == FontStrategy.SYSTEM
        assert result.handler_result.success is True
        assert result.handler_result.xml_content == "<mock>successful conversion</mock>"
        assert result.handler_result.confidence == 0.9
        assert result.execution_time_ms > 0

    def test_execution_with_context(self, executor, mock_services, simple_text_frame):
        """Test execution with conversion context."""
        executor.register_handler(FontStrategy.SYSTEM, MockHandler)
        context = {'test_key': 'test_value'}

        result = executor.execute(FontStrategy.SYSTEM, simple_text_frame, context)

        assert result.handler_result.success is True

    def test_execution_no_handler(self, executor, simple_text_frame):
        """Test execution when no handler is available."""
        result = executor.execute(FontStrategy.SYSTEM, simple_text_frame, {})

        assert result.strategy == FontStrategy.SYSTEM
        assert result.handler_result.success is False
        assert "No handler available" in result.handler_result.warnings[0]

    def test_execution_handler_failure(self, executor, mock_services, simple_text_frame):
        """Test execution when handler fails."""
        failing_handler = type('FailingHandler', (MockHandler,), {
            '__init__': lambda self, services: super(MockHandler, self).__init__(services)
        })
        failing_handler.should_succeed = False

        executor.register_handler(FontStrategy.SYSTEM, lambda services: MockHandler(services, should_succeed=False))

        result = executor.execute(FontStrategy.SYSTEM, simple_text_frame, {})

        assert result.handler_result.success is False
        assert "Mock conversion failed" in result.handler_result.warnings

    def test_execution_handler_exception(self, executor, mock_services, simple_text_frame):
        """Test execution when handler raises exception."""
        executor.register_handler(FontStrategy.SYSTEM, FailingHandler)

        result = executor.execute(FontStrategy.SYSTEM, simple_text_frame, {})

        assert result.handler_result.success is False
        assert result.handler_result.error is not None
        assert "Handler execution failed" in result.handler_result.warnings[0]

    def test_execution_invalid_input(self, executor, mock_services):
        """Test execution with invalid input."""
        executor.register_handler(FontStrategy.SYSTEM, MockHandler)

        # Empty text frame
        empty_frame = Mock()
        empty_frame.runs = []

        result = executor.execute(FontStrategy.SYSTEM, empty_frame, {})

        assert result.handler_result.success is False
        assert "TextFrame must have at least one run" in result.handler_result.warnings[0]

    def test_execution_with_timeout(self, executor, mock_services, simple_text_frame):
        """Test execution with timeout checking."""
        # Register handler with longer execution time
        slow_handler = type('SlowHandler', (MockHandler,), {})
        executor.register_handler(FontStrategy.SYSTEM, lambda services: MockHandler(services, execution_time=0.1))

        result = executor.execute_with_timeout(FontStrategy.SYSTEM, simple_text_frame, {}, timeout_ms=50)

        # Should complete but log timeout warning
        assert result.handler_result.success is True
        # Note: In a real implementation, we might want to interrupt the handler


class TestStatistics:
    """Test statistics tracking."""

    def test_statistics_tracking_success(self, executor, mock_services, simple_text_frame):
        """Test statistics tracking for successful execution."""
        executor.register_handler(FontStrategy.SYSTEM, MockHandler)

        executor.execute(FontStrategy.SYSTEM, simple_text_frame, {})

        stats = executor.get_statistics()
        assert stats['total_executions'] == 1
        assert stats['successful_executions'] == 1
        assert stats['failed_executions'] == 0
        assert stats['strategy_usage']['system'] == 1
        assert stats['total_time_ms'] > 0
        assert stats['average_time_ms'] > 0

    def test_statistics_tracking_failure(self, executor, mock_services, simple_text_frame):
        """Test statistics tracking for failed execution."""
        executor.register_handler(FontStrategy.SYSTEM, FailingHandler)

        executor.execute(FontStrategy.SYSTEM, simple_text_frame, {})

        stats = executor.get_statistics()
        assert stats['total_executions'] == 1
        assert stats['successful_executions'] == 0
        assert stats['failed_executions'] == 1

    def test_statistics_multiple_executions(self, executor, mock_services, simple_text_frame):
        """Test statistics across multiple executions."""
        executor.register_handler(FontStrategy.SYSTEM, MockHandler)
        executor.register_handler(FontStrategy.FALLBACK, MockHandler)

        # Execute multiple times
        for _ in range(3):
            executor.execute(FontStrategy.SYSTEM, simple_text_frame, {})
        for _ in range(2):
            executor.execute(FontStrategy.FALLBACK, simple_text_frame, {})

        stats = executor.get_statistics()
        assert stats['total_executions'] == 5
        assert stats['successful_executions'] == 5
        assert stats['strategy_usage']['system'] == 3
        assert stats['strategy_usage']['fallback'] == 2

    def test_reset_statistics(self, executor, mock_services, simple_text_frame):
        """Test statistics reset."""
        executor.register_handler(FontStrategy.SYSTEM, MockHandler)
        executor.execute(FontStrategy.SYSTEM, simple_text_frame, {})

        # Verify statistics exist
        assert executor.get_statistics()['total_executions'] == 1

        # Reset and verify
        executor.reset_statistics()
        stats = executor.get_statistics()
        assert stats['total_executions'] == 0
        assert stats['total_time_ms'] == 0.0

    def test_handler_statistics(self, executor, mock_services, simple_text_frame):
        """Test getting handler statistics."""
        executor.register_handler(FontStrategy.SYSTEM, MockHandler)
        executor.execute(FontStrategy.SYSTEM, simple_text_frame, {})

        handler_stats = executor.get_handler_statistics()
        assert 'system' in handler_stats
        assert isinstance(handler_stats['system'], dict)

    def test_reset_handler_statistics(self, executor, mock_services, simple_text_frame):
        """Test resetting handler statistics."""
        executor.register_handler(FontStrategy.SYSTEM, MockHandler)
        executor.execute(FontStrategy.SYSTEM, simple_text_frame, {})

        # Reset handler statistics
        executor.reset_handler_statistics()

        # Handler statistics should be reset (implementation dependent)
        handler_stats = executor.get_handler_statistics()
        assert 'system' in handler_stats


class TestValidation:
    """Test configuration and setup validation."""

    def test_validate_configuration_empty(self, executor):
        """Test validation with no handlers."""
        validation = executor.validate_configuration()

        assert validation['valid'] is False
        assert "No handlers registered" in validation['issues']

    def test_validate_configuration_with_handlers(self, executor, mock_services):
        """Test validation with registered handlers."""
        executor.register_handler(FontStrategy.SYSTEM, MockHandler)
        executor.register_handler(FontStrategy.FALLBACK, MockHandler)

        validation = executor.validate_configuration()

        assert validation['valid'] is True
        assert len(validation['issues']) == 0

    def test_validate_configuration_no_fallback(self, executor, mock_services):
        """Test validation warning for missing fallback handler."""
        executor.register_handler(FontStrategy.SYSTEM, MockHandler)

        validation = executor.validate_configuration()

        assert validation['valid'] is True
        assert "No fallback handler registered" in validation['warnings']

    def test_validate_configuration_invalid_timeout(self, mock_services):
        """Test validation with invalid configuration."""
        bad_config = FontConversionConfig(timeout_ms=0)
        executor = FontStrategyExecutor(mock_services, bad_config)

        validation = executor.validate_configuration()

        assert validation['valid'] is False
        assert "Invalid timeout configuration" in validation['issues']

    def test_validate_configuration_bad_handler(self, executor, mock_services):
        """Test validation with malformed handler."""
        class BadHandler:
            def __init__(self, services):
                pass
            # Missing required methods

        # Manually add bad handler to bypass registration validation
        executor.handlers[FontStrategy.SYSTEM] = BadHandler(mock_services)

        validation = executor.validate_configuration()

        assert validation['valid'] is False
        assert any("missing required methods" in issue for issue in validation['issues'])


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_multiple_strategy_execution(self, executor, mock_services, simple_text_frame):
        """Test execution with multiple strategies."""
        executor.register_handler(FontStrategy.SYSTEM, MockHandler)
        executor.register_handler(FontStrategy.FALLBACK, MockHandler)

        # Execute different strategies
        result1 = executor.execute(FontStrategy.SYSTEM, simple_text_frame, {})
        result2 = executor.execute(FontStrategy.FALLBACK, simple_text_frame, {})

        assert result1.strategy == FontStrategy.SYSTEM
        assert result2.strategy == FontStrategy.FALLBACK
        assert result1.handler_result.success and result2.handler_result.success

    def test_fallback_scenario(self, executor, mock_services, simple_text_frame):
        """Test fallback execution scenario."""
        # Only register fallback handler
        executor.register_handler(FontStrategy.FALLBACK, MockHandler)

        # Try to execute SYSTEM strategy (not available)
        result = executor.execute(FontStrategy.SYSTEM, simple_text_frame, {})
        assert result.handler_result.success is False

        # Execute FALLBACK strategy (available)
        result = executor.execute(FontStrategy.FALLBACK, simple_text_frame, {})
        assert result.handler_result.success is True

    def test_performance_tracking(self, executor, mock_services, simple_text_frame):
        """Test comprehensive performance tracking."""
        executor.register_handler(FontStrategy.SYSTEM, MockHandler)

        # Execute multiple times and track performance
        for _ in range(10):
            executor.execute(FontStrategy.SYSTEM, simple_text_frame, {})

        stats = executor.get_statistics()
        assert stats['total_executions'] == 10
        assert stats['average_time_ms'] > 0
        assert stats['handler_count'] == 1

        # Validate statistics make sense
        expected_avg = stats['total_time_ms'] / stats['total_executions']
        assert abs(stats['average_time_ms'] - expected_avg) < 0.001