#!/usr/bin/env python3
"""
Smart Font Converter

Main converter class that orchestrates font conversion strategies for text rendering
in PowerPoint. Integrates system fonts, WordArt, and text-to-path conversion with
intelligent strategy selection based on context.
"""

import logging
import time
from typing import Dict, Any, Optional

from ...ir import TextFrame
from ...services.conversion_services import ConversionServices
from ...policy import Policy
from .types import (
    FontConversionConfig,
    FontConversionResult,
    FontComplexity,
    ExecutionResult
)
from .strategy_selector import FontStrategySelector
from .strategy_executor import FontStrategyExecutor


logger = logging.getLogger(__name__)


class SmartFontConverter:
    """
    Unified font conversion system for Clean Slate architecture.

    Integrates system fonts, WordArt, and text-to-path conversion
    with intelligent strategy selection based on:
    - Font availability
    - Text complexity
    - Transform requirements
    - Policy decisions

    Example:
        >>> converter = SmartFontConverter(services, policy)
        >>> result = converter.convert(text_frame, context)
        >>> print(f"Used strategy: {result.strategy_used}")
        >>> print(f"Confidence: {result.confidence}")
    """

    def __init__(self, services: ConversionServices, policy: Policy,
                 config: Optional[FontConversionConfig] = None):
        """
        Initialize Smart Font Converter.

        Args:
            services: ConversionServices container with all required services
            policy: Policy engine for decision making
            config: Optional configuration for converter behavior
        """
        self.services = services
        self.policy = policy
        self.config = config or FontConversionConfig()
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.strategy_selector = FontStrategySelector(services, policy, self.config)
        self.strategy_executor = FontStrategyExecutor(services, self.config)

        # Performance tracking
        self.stats = {
            'total_conversions': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'strategy_usage': {},
            'total_time_ms': 0.0,
            'average_time_ms': 0.0
        }

        if self.config.verbose_logging:
            self.logger.setLevel(logging.DEBUG)

    def convert(self, text_frame: TextFrame,
                context: Optional[Dict[str, Any]] = None) -> FontConversionResult:
        """
        Convert TextFrame using optimal font strategy.

        This is the main entry point for text conversion. The method:
        1. Analyzes the text frame complexity
        2. Selects the best rendering strategy
        3. Executes the conversion
        4. Handles fallback if needed

        Args:
            text_frame: TextFrame IR element to convert
            context: Optional conversion context with additional information

        Returns:
            FontConversionResult with DrawingML XML and metadata

        Raises:
            ValueError: If text_frame is invalid
            RuntimeError: If all strategies fail
        """
        start_time = time.perf_counter()
        context = context or {}

        # Validate input
        if not text_frame or not text_frame.runs:
            raise ValueError("TextFrame must have at least one run")

        try:
            # Analyze text complexity
            complexity = self._analyze_complexity(text_frame)
            self.logger.debug(f"Text complexity: {complexity.value}")

            # Select optimal strategy
            selection_start = time.perf_counter()
            selection_result = self.strategy_selector.select(text_frame, context)
            selection_time_ms = (time.perf_counter() - selection_start) * 1000

            self.logger.debug(f"Selected strategy: {selection_result.primary_strategy.value}")
            self.logger.debug(f"Fallback chain: {[s.value for s in selection_result.fallback_chain]}")

            # Execute conversion with selected strategy
            execution_start = time.perf_counter()
            execution_result = self._execute_with_fallback(
                text_frame,
                selection_result.primary_strategy,
                selection_result.fallback_chain,
                context
            )
            execution_time_ms = (time.perf_counter() - execution_start) * 1000

            # Build final result
            total_time_ms = (time.perf_counter() - start_time) * 1000

            result = FontConversionResult(
                strategy_used=execution_result.strategy,
                drawingml_xml=execution_result.handler_result.xml_content,
                confidence=execution_result.handler_result.confidence,
                strategies_attempted=[execution_result.strategy],
                fallback_chain=selection_result.fallback_chain,
                total_time_ms=total_time_ms,
                strategy_selection_ms=selection_time_ms,
                execution_time_ms=execution_time_ms,
                complexity=complexity,
                font_available=selection_result.font_available,
                metadata=execution_result.handler_result.metadata,
                warnings=execution_result.handler_result.warnings
            )

            # Extract strategy-specific metadata
            if 'wordart_preset' in execution_result.handler_result.metadata:
                result.wordart_preset = execution_result.handler_result.metadata['wordart_preset']
            if 'path_count' in execution_result.handler_result.metadata:
                result.path_count = execution_result.handler_result.metadata['path_count']

            # Track statistics
            self._update_statistics(result, success=True)

            return result

        except Exception as e:
            self.logger.error(f"Font conversion failed: {e}")
            self._update_statistics(None, success=False)

            # Create error result with fallback content
            total_time_ms = (time.perf_counter() - start_time) * 1000
            return self._create_error_result(text_frame, e, total_time_ms)

    def _execute_with_fallback(self, text_frame: TextFrame,
                               primary_strategy, fallback_chain,
                               context: Dict[str, Any]) -> ExecutionResult:
        """
        Execute conversion with fallback support.

        Tries primary strategy first, then falls back through the chain
        if needed until successful conversion.
        """
        strategies_to_try = [primary_strategy] + fallback_chain

        for i, strategy in enumerate(strategies_to_try):
            self.logger.debug(f"Attempting strategy: {strategy.value}")

            result = self.strategy_executor.execute(strategy, text_frame, context)

            if result.handler_result.success:
                result.fallback_attempted = i > 0
                if i > 0:
                    result.fallback_strategy = strategies_to_try[i - 1]
                return result

            self.logger.warning(
                f"Strategy {strategy.value} failed: "
                f"{result.handler_result.warnings}"
            )

        # All strategies failed
        raise RuntimeError(
            f"All strategies failed for text conversion. "
            f"Tried: {[s.value for s in strategies_to_try]}"
        )

    def _analyze_complexity(self, text_frame: TextFrame) -> FontComplexity:
        """Analyze text frame complexity for strategy selection."""
        run_count = len(text_frame.runs)
        has_transform = hasattr(text_frame, 'transform') and text_frame.transform is not None
        has_effects = any(
            run.underline or run.strike or hasattr(run, 'effects')
            for run in text_frame.runs
        )

        # Check for multiple fonts
        fonts = set(run.font_family for run in text_frame.runs)
        has_multiple_fonts = len(fonts) > 1

        # Determine complexity level
        if run_count == 1 and not has_transform and not has_effects:
            return FontComplexity.SIMPLE
        elif run_count <= 3 and not has_transform:
            return FontComplexity.MODERATE
        elif has_transform or has_multiple_fonts or run_count > 5:
            return FontComplexity.COMPLEX
        else:
            return FontComplexity.EXTREME

    def _create_error_result(self, text_frame: TextFrame,
                             error: Exception,
                             total_time_ms: float) -> FontConversionResult:
        """Create a result for error cases with fallback text."""
        # Generate basic fallback XML
        fallback_xml = self._generate_fallback_xml(text_frame)

        from ...ir.font_metadata import FontStrategy
        return FontConversionResult(
            strategy_used=FontStrategy.FALLBACK,
            drawingml_xml=fallback_xml,
            confidence=0.1,
            strategies_attempted=[FontStrategy.FALLBACK],
            fallback_chain=[],
            total_time_ms=total_time_ms,
            strategy_selection_ms=0.0,
            execution_time_ms=0.0,
            complexity=FontComplexity.SIMPLE,
            font_available=False,
            warnings=[f"Conversion failed: {str(error)}"]
        )

    def _generate_fallback_xml(self, text_frame: TextFrame) -> str:
        """Generate basic fallback XML for error cases."""
        text_content = ' '.join(run.text for run in text_frame.runs)
        return f"""
            <p:sp>
                <p:nvSpPr>
                    <p:cNvPr id="1" name="Text"/>
                    <p:cNvSpPr txBox="1"/>
                    <p:nvPr/>
                </p:nvSpPr>
                <p:spPr>
                    <a:xfrm>
                        <a:off x="{int(text_frame.origin.x)}" y="{int(text_frame.origin.y)}"/>
                        <a:ext cx="1000000" cy="500000"/>
                    </a:xfrm>
                </p:spPr>
                <p:txBody>
                    <a:bodyPr/>
                    <a:lstStyle/>
                    <a:p>
                        <a:r>
                            <a:rPr lang="en-US" sz="1200">
                                <a:latin typeface="Arial"/>
                            </a:rPr>
                            <a:t>{text_content}</a:t>
                        </a:r>
                    </a:p>
                </p:txBody>
            </p:sp>
        """

    def _update_statistics(self, result: Optional[FontConversionResult],
                           success: bool):
        """Update converter statistics."""
        self.stats['total_conversions'] += 1

        if success and result:
            self.stats['successful_conversions'] += 1
            strategy = result.strategy_used.value
            self.stats['strategy_usage'][strategy] = \
                self.stats['strategy_usage'].get(strategy, 0) + 1
            self.stats['total_time_ms'] += result.total_time_ms
        else:
            self.stats['failed_conversions'] += 1

        # Update average time
        if self.stats['total_conversions'] > 0:
            self.stats['average_time_ms'] = (
                self.stats['total_time_ms'] / self.stats['successful_conversions']
                if self.stats['successful_conversions'] > 0 else 0
            )

    def get_statistics(self) -> Dict[str, Any]:
        """Get converter performance statistics."""
        return self.stats.copy()

    def reset_statistics(self):
        """Reset converter statistics."""
        self.stats = {
            'total_conversions': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'strategy_usage': {},
            'total_time_ms': 0.0,
            'average_time_ms': 0.0
        }