#!/usr/bin/env python3
"""
Font Strategy Executor

Executes font conversion based on selected strategy by routing to
appropriate strategy handlers.
"""

import logging
import time
from typing import Dict, Any, Optional, Type

from ...ir import TextFrame
from ...ir.font_metadata import FontStrategy
from ...services.conversion_services import ConversionServices
from .types import FontConversionConfig, ExecutionResult, HandlerResult
from .handlers.base import BaseStrategyHandler


class FontStrategyExecutor:
    """
    Execute font conversion based on selected strategy.

    Routes to appropriate strategy handlers and manages their execution
    with error handling and performance tracking.
    """

    def __init__(self, services: ConversionServices, config: FontConversionConfig):
        """
        Initialize strategy executor.

        Args:
            services: ConversionServices container
            config: Configuration for execution behavior
        """
        self.services = services
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Strategy handlers registry
        self.handlers: Dict[FontStrategy, BaseStrategyHandler] = {}
        self._handler_classes: Dict[FontStrategy, Type[BaseStrategyHandler]] = {}

        # Performance tracking
        self.stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'strategy_usage': {},
            'total_time_ms': 0.0,
            'average_time_ms': 0.0
        }

        # Initialize handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register strategy handlers."""
        # Import handler classes
        from .handlers.system_font_handler import SystemFontHandler
        from .handlers.wordart_handler import WordArtHandler
        from .handlers.text_to_path_handler import TextToPathHandler
        from .handlers.fallback_handler import FallbackHandler

        # Handler registrations
        self._handler_classes = {
            FontStrategy.SYSTEM: SystemFontHandler,       # Task 2.1: SystemFontHandler ✓
            FontStrategy.EMBEDDED: None,                  # Task 2.1: EmbeddedFontHandler (TODO)
            FontStrategy.WORDART: WordArtHandler,         # Task 2.2: WordArtHandler ✓
            FontStrategy.PATH: TextToPathHandler,         # Task 2.3: TextToPathHandler ✓
            FontStrategy.FALLBACK: FallbackHandler        # Task 2.4: FallbackHandler ✓
        }

        # Initialize available handlers
        self._initialize_available_handlers()

    def _initialize_available_handlers(self):
        """Initialize handlers that have been implemented."""
        for strategy, handler_class in self._handler_classes.items():
            if handler_class is not None:
                try:
                    handler = handler_class(self.services)
                    self.handlers[strategy] = handler
                    self.logger.debug(f"Registered handler for strategy: {strategy.value}")
                except Exception as e:
                    self.logger.error(f"Failed to initialize handler for {strategy.value}: {e}")

    def register_handler(self, strategy: FontStrategy, handler_class: Type[BaseStrategyHandler]):
        """
        Register a strategy handler class.

        Args:
            strategy: Font strategy this handler supports
            handler_class: Handler class to register
        """
        self._handler_classes[strategy] = handler_class

        # Initialize the handler immediately
        try:
            handler = handler_class(self.services)
            self.handlers[strategy] = handler
            self.logger.info(f"Registered handler for strategy: {strategy.value}")
        except Exception as e:
            self.logger.error(f"Failed to register handler for {strategy.value}: {e}")
            raise

    def unregister_handler(self, strategy: FontStrategy):
        """
        Unregister a strategy handler.

        Args:
            strategy: Font strategy to unregister
        """
        if strategy in self.handlers:
            del self.handlers[strategy]
        if strategy in self._handler_classes:
            self._handler_classes[strategy] = None
        self.logger.info(f"Unregistered handler for strategy: {strategy.value}")

    def get_available_strategies(self) -> list[FontStrategy]:
        """
        Get list of strategies with registered handlers.

        Returns:
            List of available font strategies
        """
        return list(self.handlers.keys())

    def has_handler(self, strategy: FontStrategy) -> bool:
        """
        Check if a handler is available for the given strategy.

        Args:
            strategy: Font strategy to check

        Returns:
            True if handler is available
        """
        return strategy in self.handlers

    def execute(self, strategy: FontStrategy, text_frame: TextFrame,
                context: Dict[str, Any]) -> ExecutionResult:
        """
        Execute conversion with selected strategy.

        Args:
            strategy: Font strategy to use
            text_frame: Text frame to convert
            context: Conversion context

        Returns:
            ExecutionResult with handler result and metadata
        """
        start_time = time.perf_counter()

        try:
            # Update statistics
            self.stats['total_executions'] += 1
            strategy_key = strategy.value
            self.stats['strategy_usage'][strategy_key] = \
                self.stats['strategy_usage'].get(strategy_key, 0) + 1

            # Validate inputs
            if not text_frame or not text_frame.runs:
                raise ValueError("TextFrame must have at least one run")

            # Check if handler is available
            if not self.has_handler(strategy):
                return self._create_no_handler_result(strategy, start_time)

            # Get handler and execute
            handler = self.handlers[strategy]

            self.logger.debug(f"Executing strategy: {strategy.value}")
            handler_result = handler.execute(text_frame, context)

            # Calculate execution time
            execution_time_ms = (time.perf_counter() - start_time) * 1000

            # Create execution result
            result = ExecutionResult(
                strategy=strategy,
                handler_result=handler_result,
                execution_time_ms=execution_time_ms
            )

            # Update statistics
            if handler_result.success:
                self.stats['successful_executions'] += 1
            else:
                self.stats['failed_executions'] += 1

            self.stats['total_time_ms'] += execution_time_ms
            self._update_average_time()

            self.logger.debug(
                f"Strategy {strategy.value} execution completed in {execution_time_ms:.2f}ms, "
                f"success: {handler_result.success}, confidence: {handler_result.confidence}"
            )

            return result

        except Exception as e:
            self.stats['failed_executions'] += 1
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            self.stats['total_time_ms'] += execution_time_ms
            self._update_average_time()

            self.logger.error(f"Strategy execution failed for {strategy.value}: {e}")

            return ExecutionResult(
                strategy=strategy,
                handler_result=HandlerResult(
                    success=False,
                    xml_content="",
                    confidence=0.0,
                    error=e,
                    warnings=[f"Execution failed: {str(e)}"]
                ),
                execution_time_ms=execution_time_ms
            )

    def _create_no_handler_result(self, strategy: FontStrategy, start_time: float) -> ExecutionResult:
        """
        Create result when no handler is available for strategy.

        Args:
            strategy: Requested strategy
            start_time: Execution start time

        Returns:
            ExecutionResult indicating no handler available
        """
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        self.stats['failed_executions'] += 1
        self.stats['total_time_ms'] += execution_time_ms
        self._update_average_time()

        warning_msg = f"No handler available for strategy: {strategy.value}"
        self.logger.warning(warning_msg)

        return ExecutionResult(
            strategy=strategy,
            handler_result=HandlerResult(
                success=False,
                xml_content="",
                confidence=0.0,
                warnings=[warning_msg]
            ),
            execution_time_ms=execution_time_ms
        )

    def _update_average_time(self):
        """Update average execution time statistic."""
        if self.stats['total_executions'] > 0:
            self.stats['average_time_ms'] = \
                self.stats['total_time_ms'] / self.stats['total_executions']

    def execute_with_timeout(self, strategy: FontStrategy, text_frame: TextFrame,
                            context: Dict[str, Any],
                            timeout_ms: Optional[float] = None) -> ExecutionResult:
        """
        Execute conversion with timeout protection.

        Args:
            strategy: Font strategy to use
            text_frame: Text frame to convert
            context: Conversion context
            timeout_ms: Optional timeout in milliseconds

        Returns:
            ExecutionResult with handler result and metadata
        """
        timeout = timeout_ms or self.config.timeout_ms
        start_time = time.perf_counter()

        # For now, we'll implement a simple timeout check
        # A more sophisticated implementation would use threading or async
        result = self.execute(strategy, text_frame, context)

        # Check if execution exceeded timeout
        if result.execution_time_ms > timeout:
            self.logger.warning(
                f"Execution exceeded timeout ({timeout}ms): {result.execution_time_ms:.2f}ms"
            )
            result.handler_result.warnings.append(
                f"Execution exceeded timeout: {result.execution_time_ms:.2f}ms > {timeout}ms"
            )

        return result

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get executor performance statistics.

        Returns:
            Dictionary with performance metrics
        """
        stats = self.stats.copy()
        stats['handler_count'] = len(self.handlers)
        stats['available_strategies'] = [s.value for s in self.get_available_strategies()]
        return stats

    def reset_statistics(self):
        """Reset executor performance statistics."""
        self.stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'strategy_usage': {},
            'total_time_ms': 0.0,
            'average_time_ms': 0.0
        }
        self.logger.info("Reset executor statistics")

    def get_handler_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics from all registered handlers.

        Returns:
            Dictionary mapping strategy names to handler statistics
        """
        handler_stats = {}
        for strategy, handler in self.handlers.items():
            try:
                handler_stats[strategy.value] = handler.get_statistics()
            except Exception as e:
                self.logger.warning(f"Failed to get statistics from {strategy.value} handler: {e}")
                handler_stats[strategy.value] = {'error': str(e)}
        return handler_stats

    def reset_handler_statistics(self):
        """Reset statistics for all registered handlers."""
        for strategy, handler in self.handlers.items():
            try:
                handler.reset_statistics()
            except Exception as e:
                self.logger.warning(f"Failed to reset statistics for {strategy.value} handler: {e}")

    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate executor configuration and handler setup.

        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'valid': True,
            'issues': [],
            'warnings': []
        }

        # Check if at least one handler is registered
        if not self.handlers:
            validation_result['valid'] = False
            validation_result['issues'].append("No handlers registered")

        # Check for required fallback handler
        if not self.has_handler(FontStrategy.FALLBACK):
            validation_result['warnings'].append("No fallback handler registered")

        # Validate configuration
        if self.config.timeout_ms <= 0:
            validation_result['issues'].append("Invalid timeout configuration")

        # Test each handler
        for strategy, handler in self.handlers.items():
            try:
                # Basic validation by checking if handler has required methods
                if not hasattr(handler, 'can_handle') or not hasattr(handler, 'convert'):
                    validation_result['issues'].append(
                        f"Handler for {strategy.value} missing required methods"
                    )
            except Exception as e:
                validation_result['issues'].append(
                    f"Handler validation failed for {strategy.value}: {e}"
                )

        if validation_result['issues']:
            validation_result['valid'] = False

        return validation_result