#!/usr/bin/env python3
"""
Font Strategy Selector

Intelligent selection of font rendering strategy based on text complexity,
font availability, and policy decisions.
"""

import logging
from typing import Dict, Any, List
from dataclasses import dataclass

from ...ir import TextFrame
from ...ir.font_metadata import FontStrategy
from ...services.conversion_services import ConversionServices
from ...policy import Policy
from .types import FontConversionConfig, FontComplexity


@dataclass
class SelectionResult:
    """Result of strategy selection process."""
    primary_strategy: FontStrategy
    fallback_chain: List[FontStrategy]
    font_available: bool
    complexity: FontComplexity
    confidence: float
    metadata: Dict[str, Any]


class FontStrategySelector:
    """
    Intelligent selection of font rendering strategy.

    Analyzes text frames and selects the optimal rendering strategy based on:
    - Font availability in the system
    - Text complexity (transforms, effects, multi-run)
    - Policy engine decisions
    - WordArt opportunity detection
    """

    def __init__(self, services: ConversionServices, policy: Policy,
                 config: FontConversionConfig):
        """
        Initialize strategy selector.

        Args:
            services: ConversionServices container
            policy: Policy engine for decisions
            config: Configuration for selection behavior
        """
        self.services = services
        self.policy = policy
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Font availability cache
        self._font_cache = {}

    def select(self, text_frame: TextFrame,
               context: Dict[str, Any]) -> SelectionResult:
        """
        Select optimal font strategy for text frame.

        Args:
            text_frame: Text frame to analyze
            context: Conversion context

        Returns:
            SelectionResult with primary strategy and fallback chain
        """
        try:
            # Step 1: Analyze text complexity
            complexity = self._analyze_text_complexity(text_frame)
            self.logger.debug(f"Text complexity: {complexity.value}")

            # Step 2: Check font availability
            font_available = self._check_font_availability(text_frame)
            self.logger.debug(f"Font available: {font_available}")

            # Step 3: Policy engine decisions
            policy_decisions = self._get_policy_decisions(text_frame, context)
            self.logger.debug(f"Policy decisions: {policy_decisions}")

            # Step 4: Strategy selection logic
            primary_strategy, confidence = self._select_primary_strategy(
                text_frame, complexity, font_available, policy_decisions
            )

            # Step 5: Build fallback chain
            fallback_chain = self._build_fallback_chain(
                primary_strategy, complexity, font_available
            )

            # Step 6: Create result with metadata
            metadata = {
                'policy_decisions': policy_decisions,
                'analysis_time_ms': 0.0,  # Placeholder for timing
                'font_metrics': self._get_font_metrics(text_frame),
                'transform_detected': hasattr(text_frame, 'transform') and text_frame.transform is not None
            }

            result = SelectionResult(
                primary_strategy=primary_strategy,
                fallback_chain=fallback_chain,
                font_available=font_available,
                complexity=complexity,
                confidence=confidence,
                metadata=metadata
            )

            self.logger.debug(f"Selected strategy: {primary_strategy.value} with confidence {confidence}")
            return result

        except Exception as e:
            self.logger.error(f"Strategy selection failed: {e}")
            # Return safe fallback selection
            return SelectionResult(
                primary_strategy=FontStrategy.FALLBACK,
                fallback_chain=[],
                font_available=False,
                complexity=FontComplexity.SIMPLE,
                confidence=0.1,
                metadata={'error': str(e)}
            )

    def _analyze_text_complexity(self, text_frame: TextFrame) -> FontComplexity:
        """
        Analyze text frame complexity for strategy selection.

        Args:
            text_frame: Text frame to analyze

        Returns:
            FontComplexity level based on analysis
        """
        # Basic complexity factors
        run_count = len(text_frame.runs)

        # Check for transforms
        has_transform = hasattr(text_frame, 'transform') and text_frame.transform is not None

        # Check for text effects/decorations
        has_effects = any(
            run.underline or run.strike or hasattr(run, 'effects')
            for run in text_frame.runs
        )

        # Check for multiple fonts
        fonts = set(run.font_family for run in text_frame.runs)
        has_multiple_fonts = len(fonts) > 1

        # Check for varying font sizes
        font_sizes = set(run.font_size_pt for run in text_frame.runs)
        has_varying_sizes = len(font_sizes) > 1

        # Check text content characteristics
        total_text = ''.join(run.text for run in text_frame.runs)
        has_line_breaks = '\n' in total_text
        has_special_chars = any(ord(c) > 127 for c in total_text)

        # Complexity scoring
        complexity_score = 0

        # Run count factor
        if run_count == 1:
            complexity_score += 0
        elif run_count <= 3:
            complexity_score += 1
        elif run_count <= 5:
            complexity_score += 2
        else:
            complexity_score += 3

        # Transform and styling factors
        if has_transform:
            complexity_score += 2
        if has_effects:
            complexity_score += 1
        if has_multiple_fonts:
            complexity_score += 2
        if has_varying_sizes:
            complexity_score += 1
        if has_line_breaks:
            complexity_score += 1
        if has_special_chars:
            complexity_score += 1

        # Map score to complexity level
        if complexity_score == 0:
            return FontComplexity.SIMPLE
        elif complexity_score <= 2:
            return FontComplexity.MODERATE
        elif complexity_score <= 5:
            return FontComplexity.COMPLEX
        else:
            return FontComplexity.EXTREME

    def _check_font_availability(self, text_frame: TextFrame) -> bool:
        """
        Check if required fonts are available in the system.

        Args:
            text_frame: Text frame to check

        Returns:
            True if primary font is available
        """
        primary_font = text_frame.runs[0].font_family if text_frame.runs else 'Arial'

        # Check cache first
        if primary_font in self._font_cache:
            return self._font_cache[primary_font]

        # Use font service to check availability
        try:
            font_available = self.services.font_service.is_font_available(primary_font)
            self._font_cache[primary_font] = font_available
            return font_available
        except Exception as e:
            self.logger.warning(f"Font availability check failed for {primary_font}: {e}")
            # Conservative default - assume font is not available
            self._font_cache[primary_font] = False
            return False

    def _get_policy_decisions(self, text_frame: TextFrame, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get policy engine decisions for text frame.

        Args:
            text_frame: Text frame to analyze
            context: Conversion context

        Returns:
            Policy decisions dict
        """
        try:
            # Convert TextFrame to format expected by policy engine
            policy_context = {
                'text_frame': text_frame,
                'context': context,
                'run_count': len(text_frame.runs),
                'has_transform': hasattr(text_frame, 'transform') and text_frame.transform is not None
            }

            # Check for WordArt opportunities
            wordart_decision = self.policy.decide_text(text_frame, context)

            return {
                'wordart_opportunity': wordart_decision.use_wordart if hasattr(wordart_decision, 'use_wordart') else False,
                'wordart_preset': getattr(wordart_decision, 'preset', None),
                'text_to_path_recommended': getattr(wordart_decision, 'use_text_to_path', False),
                'embedding_recommended': getattr(wordart_decision, 'use_embedding', False),
                'confidence': getattr(wordart_decision, 'confidence', 0.5)
            }
        except Exception as e:
            self.logger.warning(f"Policy decision failed: {e}")
            return {
                'wordart_opportunity': False,
                'wordart_preset': None,
                'text_to_path_recommended': False,
                'embedding_recommended': False,
                'confidence': 0.1
            }

    def _select_primary_strategy(self, text_frame: TextFrame, complexity: FontComplexity,
                                font_available: bool, policy_decisions: Dict[str, Any]) -> tuple[FontStrategy, float]:
        """
        Select primary strategy based on analysis.

        Args:
            text_frame: Text frame being converted
            complexity: Text complexity level
            font_available: Whether font is available
            policy_decisions: Policy engine decisions

        Returns:
            Tuple of (strategy, confidence)
        """
        # Check configuration settings
        wordart_enabled = self.config.enable_wordart
        text_to_path_enabled = self.config.enable_text_to_path
        embedding_enabled = self.config.enable_font_embedding

        # Strategy selection logic

        # 1. WordArt strategy (highest priority for compatible text)
        if (wordart_enabled and
            policy_decisions.get('wordart_opportunity', False) and
            complexity in [FontComplexity.SIMPLE, FontComplexity.MODERATE]):

            preset_confidence = 0.9 if policy_decisions.get('wordart_preset') else 0.7
            if preset_confidence >= self.config.wordart_confidence_threshold:
                return FontStrategy.WORDART, preset_confidence

        # 2. System font strategy (best for simple text with available fonts)
        if (font_available and
            complexity in [FontComplexity.SIMPLE, FontComplexity.MODERATE]):
            return FontStrategy.SYSTEM, 0.9

        # 3. Embedded font strategy (for unavailable fonts, if enabled)
        if (embedding_enabled and
            not font_available and
            complexity in [FontComplexity.SIMPLE, FontComplexity.MODERATE]):
            return FontStrategy.EMBEDDED, 0.7

        # 4. Text-to-path strategy (for complex text or transforms)
        if (text_to_path_enabled and
            (complexity in [FontComplexity.COMPLEX, FontComplexity.EXTREME] or
             hasattr(text_frame, 'transform'))):
            return FontStrategy.PATH, 0.8

        # 5. WordArt fallback (lower confidence for complex text)
        if (wordart_enabled and
            policy_decisions.get('wordart_opportunity', False)):
            return FontStrategy.WORDART, 0.5

        # 6. Text-to-path fallback (if enabled)
        if text_to_path_enabled:
            return FontStrategy.PATH, 0.6

        # 7. Final fallback
        return FontStrategy.FALLBACK, 0.3

    def _build_fallback_chain(self, primary_strategy: FontStrategy,
                              complexity: FontComplexity, font_available: bool) -> List[FontStrategy]:
        """
        Build fallback strategy chain.

        Args:
            primary_strategy: Selected primary strategy
            complexity: Text complexity level
            font_available: Whether font is available

        Returns:
            List of fallback strategies in order of preference
        """
        fallback_chain = []

        # Build fallback chain based on primary strategy
        if primary_strategy == FontStrategy.SYSTEM:
            if self.config.enable_wordart:
                fallback_chain.append(FontStrategy.WORDART)
            if self.config.enable_text_to_path:
                fallback_chain.append(FontStrategy.PATH)
            fallback_chain.append(FontStrategy.FALLBACK)

        elif primary_strategy == FontStrategy.WORDART:
            if font_available:
                fallback_chain.append(FontStrategy.SYSTEM)
            if self.config.enable_text_to_path:
                fallback_chain.append(FontStrategy.PATH)
            fallback_chain.append(FontStrategy.FALLBACK)

        elif primary_strategy == FontStrategy.PATH:
            if font_available:
                fallback_chain.append(FontStrategy.SYSTEM)
            if self.config.enable_wordart:
                fallback_chain.append(FontStrategy.WORDART)
            fallback_chain.append(FontStrategy.FALLBACK)

        elif primary_strategy == FontStrategy.EMBEDDED:
            if self.config.enable_wordart:
                fallback_chain.append(FontStrategy.WORDART)
            fallback_chain.append(FontStrategy.SYSTEM)  # Try system font anyway
            if self.config.enable_text_to_path:
                fallback_chain.append(FontStrategy.PATH)
            fallback_chain.append(FontStrategy.FALLBACK)

        else:  # FALLBACK primary
            pass  # No further fallbacks

        # Remove duplicates while preserving order
        seen = set()
        unique_fallbacks = []
        for strategy in fallback_chain:
            if strategy not in seen and strategy != primary_strategy:
                seen.add(strategy)
                unique_fallbacks.append(strategy)

        return unique_fallbacks

    def _get_font_metrics(self, text_frame: TextFrame) -> Dict[str, Any]:
        """
        Get font metrics for the text frame.

        Args:
            text_frame: Text frame to analyze

        Returns:
            Font metrics dict
        """
        if not text_frame.runs:
            return {}

        try:
            primary_run = text_frame.runs[0]
            metrics = self.services.font_service.get_font_metrics(
                primary_run.font_family,
                primary_run.font_size_pt
            )

            return {
                'font_family': primary_run.font_family,
                'font_size_pt': primary_run.font_size_pt,
                'estimated_width': getattr(metrics, 'estimated_width', 0),
                'estimated_height': getattr(metrics, 'estimated_height', 0),
                'ascent': getattr(metrics, 'ascent', 0),
                'descent': getattr(metrics, 'descent', 0)
            }
        except Exception as e:
            self.logger.warning(f"Font metrics calculation failed: {e}")
            return {
                'font_family': text_frame.runs[0].font_family,
                'font_size_pt': text_frame.runs[0].font_size_pt,
                'error': str(e)
            }