"""
Text policy helper encapsulating font availability and WordArt decisions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .config import PolicyConfig
from ..ir import TextFrame
from .targets import DecisionReason, TextDecision
from .text_warp_classifier import classify_text_path_warp

MIN_COLORS_FOR_COMPLEX_GRADIENT = 16
MAX_NESTED_GROUPS = 5

GENERIC_FONT_FALLBACKS = {
    'sans-serif': ['Arial', 'Helvetica'],
    'serif': ['Times New Roman', 'Georgia'],
    'monospace': ['Courier New', 'Consolas', 'Courier'],
    'cursive': ['Comic Sans MS', 'Brush Script MT'],
    'fantasy': ['Impact', 'Papyrus'],
}


@dataclass
class FontDecisionContext:
    """Result of policy font availability analysis."""

    has_missing_fonts: bool = False
    strategy: str | None = None
    confidence: float = 0.0
    embedded_font: str | None = None
    fallback_font: str | None = None
    missing_fonts: list[str] | None = None

    def to_decision_kwargs(self) -> dict[str, Any]:
        return {
            'font_strategy': self.strategy,
            'font_match_confidence': self.confidence,
            'embedded_font_name': self.embedded_font,
            'system_font_fallback': self.fallback_font,
            'missing_fonts': self.missing_fonts or [],
        }


class TextPolicy:
    """Evaluate text complexity and determine rendering strategy."""

    def __init__(
        self,
        config: PolicyConfig,
        logger: logging.Logger | None = None,
        *,
        font_service: Any | None = None,
        font_system: Any | None = None,
    ):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.font_service = font_service
        self.font_system = font_system

    def attach_font_services(self, font_service=None, font_system=None) -> None:
        if font_service is not None:
            self.font_service = font_service
        if font_system is not None:
            self.font_system = font_system

    def decide(
        self,
        text: TextFrame,
        *,
        transform_analyzer: Callable[[TextFrame], dict[str, Any] | None] | None = None,
        wordart_checker: Callable[[TextFrame], dict[str, Any] | None] | None = None,
    ) -> TextDecision:
        reasons: list[DecisionReason] = []
        run_count = len(text.runs)
        complexity_score = text.complexity_score
        has_effects = any(run.has_decoration for run in text.runs)
        has_multiline = text.is_multiline

        font_context = self._evaluate_font_availability(text)
        has_missing_fonts = font_context.has_missing_fonts
        font_kwargs = font_context.to_decision_kwargs()

        thresholds = self.config.thresholds

        if self.config.conservative_text and has_effects:
            reasons.extend([DecisionReason.CONSERVATIVE_MODE, DecisionReason.TEXT_EFFECTS_COMPLEX])
            return TextDecision.emf(
                reasons=reasons,
                run_count=run_count,
                complexity_score=complexity_score,
                has_missing_fonts=has_missing_fonts,
                has_effects=has_effects,
                has_multiline=has_multiline,
                confidence=0.9,
                **font_kwargs,
            )

        if run_count > thresholds.max_text_runs:
            reasons.extend([DecisionReason.ABOVE_THRESHOLDS, DecisionReason.COMPLEX_GEOMETRY])
            return TextDecision.emf(
                reasons=reasons,
                run_count=run_count,
                complexity_score=complexity_score,
                has_missing_fonts=has_missing_fonts,
                has_effects=has_effects,
                has_multiline=has_multiline,
                confidence=0.85,
                **font_kwargs,
            )

        if complexity_score > thresholds.max_text_complexity_score:
            reasons.append(DecisionReason.ABOVE_THRESHOLDS)
            if has_effects:
                reasons.append(DecisionReason.TEXT_EFFECTS_COMPLEX)
            return TextDecision.emf(
                reasons=reasons,
                run_count=run_count,
                complexity_score=complexity_score,
                has_missing_fonts=has_missing_fonts,
                has_effects=has_effects,
                has_multiline=has_multiline,
                confidence=0.8,
                **font_kwargs,
            )

        if has_missing_fonts:
            behavior = getattr(self.config, "font_missing_behavior", "embedded")
            behavior = (behavior or "embedded").lower()
            reasons.append(DecisionReason.FONT_UNAVAILABLE)
            font_kwargs = dict(font_kwargs)
            existing_strategy = font_kwargs.pop('font_strategy', None)

            if behavior == "error":
                missing = ', '.join(font_kwargs.get('missing_fonts') or [])
                raise RuntimeError(
                    f"Missing fonts detected ({missing or 'unknown'}), and policy is set to error."
                )

            if behavior == "outline":
                return TextDecision.native(
                    reasons=reasons,
                    run_count=run_count,
                    complexity_score=complexity_score,
                    has_missing_fonts=has_missing_fonts,
                    has_effects=has_effects,
                    has_multiline=has_multiline,
                    confidence=0.9,
                    font_strategy="text_to_path",
                    **font_kwargs,
                )

            if behavior == "fallback_family":
                fallback_font = font_kwargs.get('system_font_fallback')
                if not fallback_font:
                    # Fall back to EMF if no system fallback available
                    behavior = "emf"
                else:
                    return TextDecision.native(
                        reasons=reasons,
                        run_count=run_count,
                        complexity_score=complexity_score,
                        has_missing_fonts=has_missing_fonts,
                        has_effects=has_effects,
                        has_multiline=has_multiline,
                        confidence=0.88,
                        font_strategy="system_fallback",
                        system_font_fallback=fallback_font,
                        **font_kwargs,
                    )

            if behavior == "emf":
                return TextDecision.emf(
                    reasons=reasons,
                    run_count=run_count,
                    complexity_score=complexity_score,
                    has_missing_fonts=has_missing_fonts,
                    has_effects=has_effects,
                    has_multiline=has_multiline,
                    confidence=0.95,
                    font_strategy="emf_fallback",
                    **font_kwargs,
                )

            # Default embedded behavior (attempt embedding; fall back to EMF if unreachable)
            return TextDecision.emf(
                reasons=reasons,
                run_count=run_count,
                complexity_score=complexity_score,
                has_missing_fonts=has_missing_fonts,
                has_effects=has_effects,
                has_multiline=has_multiline,
                confidence=0.95,
                font_strategy=existing_strategy or "embedded",
                **font_kwargs,
            )

        transform_fn = transform_analyzer or self._analyze_transform_complexity
        transform_analysis = transform_fn(text)
        if transform_analysis and not transform_analysis['can_wordart_native']:
            reasons.append(DecisionReason.COMPLEX_TRANSFORM)
            if transform_analysis['max_skew_exceeded']:
                reasons.append(DecisionReason.ABOVE_THRESHOLDS)
            return TextDecision.emf(
                reasons=reasons,
                run_count=run_count,
                complexity_score=complexity_score,
                has_missing_fonts=has_missing_fonts,
                has_effects=has_effects,
                has_multiline=has_multiline,
                transform_complexity=transform_analysis,
                confidence=0.9,
                **font_kwargs,
            )

        wordart_fn = wordart_checker or self._check_wordart_opportunity
        wordart_result = wordart_fn(text)
        if wordart_result and wordart_result['confidence'] >= self.config.wordart_confidence_threshold:
            reasons.extend([DecisionReason.WORDART_PATTERN_DETECTED, DecisionReason.NATIVE_PRESET_AVAILABLE])
            return TextDecision.wordart(
                preset=wordart_result['preset'],
                parameters=wordart_result['parameters'],
                confidence=wordart_result['confidence'],
                reasons=reasons,
                run_count=run_count,
                complexity_score=complexity_score,
                has_missing_fonts=has_missing_fonts,
                has_effects=has_effects,
                has_multiline=has_multiline,
                estimated_quality=0.95,
                estimated_performance=0.98,
                **font_kwargs,
            )

        reasons.extend(
            [
                DecisionReason.BELOW_THRESHOLDS,
                DecisionReason.FONT_AVAILABLE,
                DecisionReason.SUPPORTED_FEATURES,
            ],
        )

        return TextDecision.native(
            reasons=reasons,
            run_count=run_count,
            complexity_score=complexity_score,
            has_missing_fonts=has_missing_fonts,
            has_effects=has_effects,
            has_multiline=has_multiline,
            confidence=0.95,
            estimated_quality=0.98,
            estimated_performance=0.95,
            **font_kwargs,
        )

    def _evaluate_font_availability(self, text: TextFrame) -> FontDecisionContext:
        context = FontDecisionContext(missing_fonts=[])

        embedded_font = getattr(text, 'embedded_font_name', None)
        if embedded_font:
            context.strategy = 'embedded'
            context.confidence = 0.95
            context.embedded_font = embedded_font
            return context

        if not self.font_service:
            context.strategy = 'system'
            context.confidence = 0.0
            return context

        missing_fonts: list[str] = []
        fallback_font: str | None = None
        available_runs = 0
        total_runs = len(text.runs) or 1
        lookup_cache: dict[tuple[str, str, str], bool] = {}

        for run in text.runs:
            families = self._parse_font_families(getattr(run, 'font_family', None))
            if not families:
                families = ['sans-serif']

            weight = 'bold' if getattr(run, 'bold', False) else 'normal'
            style = 'italic' if getattr(run, 'italic', False) else 'normal'

            candidates: list[str] = []
            for family in families:
                generic_fallbacks = GENERIC_FONT_FALLBACKS.get(family.lower())
                if generic_fallbacks:
                    candidates.extend(generic_fallbacks)
                else:
                    candidates.append(family)

            font_found = False
            for candidate in candidates:
                key = (candidate.lower(), weight, style)
                if key not in lookup_cache:
                    result = self.font_service.find_font_file(candidate, weight, style)
                    lookup_cache[key] = bool(result)
                if lookup_cache[key]:
                    font_found = True
                    available_runs += 1
                    if fallback_font is None:
                        fallback_font = candidate
                    break

            if not font_found:
                primary = families[0] if families else 'Unknown'
                if primary not in missing_fonts:
                    missing_fonts.append(primary)

        context.missing_fonts = missing_fonts
        context.has_missing_fonts = bool(missing_fonts)
        context.confidence = round(available_runs / total_runs, 2)
        context.fallback_font = fallback_font

        if context.has_missing_fonts:
            thresholds = self.config.thresholds
            if thresholds.enable_text_to_path:
                context.strategy = 'text_to_path'
            elif thresholds.enable_system_font_fallback and fallback_font:
                context.strategy = 'system'
            else:
                context.strategy = 'fallback'
        else:
            context.strategy = context.strategy or 'system'
            if context.confidence == 0.0:
                context.confidence = 0.9

        return context

    @staticmethod
    def _parse_font_families(font_family: Optional[str]) -> list[str]:
        if not font_family:
            return []

        families: list[str] = []
        for token in font_family.split(','):
            name = token.strip().strip('"').strip("'")
            if name:
                families.append(name)
        return families

    def _check_wordart_opportunity(self, text: TextFrame) -> dict[str, Any] | None:
        if not self.config.enable_wordart_classification:
            return None
        if not hasattr(text, 'text_path') or not text.text_path:
            return None

        try:
            from ..algorithms.curve_text_positioning import (
                PathSamplingMethod,
                create_curve_text_positioner,
            )

            positioner = create_curve_text_positioner(PathSamplingMethod.DETERMINISTIC)
            num_samples = min(self.config.wordart_max_sample_points, 128)
            path_points = positioner.sample_path_for_text(
                text.text_path.path_data,
                num_samples,
            )

            if len(path_points) < MIN_COLORS_FOR_COMPLEX_GRADIENT:
                return None

            wordart_result = self._classify_wordart_pattern(text, path_points)
            if wordart_result and wordart_result['confidence'] >= self.config.wordart_confidence_threshold:
                return wordart_result
            return None
        except Exception as exc:
            self.logger.debug(f"WordArt classification failed: {exc}")
            return None

    def _classify_wordart_pattern(self, text: TextFrame, path_points) -> dict[str, Any] | None:
        if len(path_points) < MIN_COLORS_FOR_COMPLEX_GRADIENT:
            return None

        text_path = getattr(text, 'text_path', None)
        path_data = getattr(text_path, 'path_data', None) if text_path else None

        try:
            return classify_text_path_warp(text_path, path_points, path_data)
        except Exception as exc:
            self.logger.debug(f"Warp classification failure: {exc}")
            return None

    def _analyze_transform_complexity(self, text: TextFrame) -> dict[str, Any] | None:
        if not hasattr(text, 'transform') or text.transform is None:
            return None

        try:
            from ..services.wordart_transform_service import create_transform_decomposer

            decomposer = create_transform_decomposer()
            if isinstance(text.transform, str):
                components = decomposer.decompose_transform_string(text.transform)
            else:
                components = decomposer.decompose_matrix(text.transform)

            analysis = decomposer.analyze_transform_complexity(components)
            thresholds = self.config.thresholds

            max_skew_exceeded = components.max_skew_angle > thresholds.max_skew_angle_deg
            scale_ratio_exceeded = components.scale_ratio > thresholds.max_scale_ratio

            rotation_mod_90 = abs(components.rotation_deg) % 90
            rotation_deviation = min(rotation_mod_90, 90 - rotation_mod_90)
            rotation_deviation_exceeded = rotation_deviation > thresholds.max_rotation_deviation_deg

            analysis['max_skew_exceeded'] = max_skew_exceeded
            analysis['scale_ratio_exceeded'] = scale_ratio_exceeded
            analysis['rotation_deviation_exceeded'] = rotation_deviation_exceeded
            analysis['can_wordart_native'] = (
                not max_skew_exceeded
                and not scale_ratio_exceeded
                and not rotation_deviation_exceeded
                and analysis['complexity_score'] < MAX_NESTED_GROUPS
            )
            analysis['policy_score'] = (
                (2 if max_skew_exceeded else 0)
                + (2 if scale_ratio_exceeded else 0)
                + (1 if rotation_deviation_exceeded else 0)
            )
            return analysis
        except Exception as exc:
            self.logger.debug(f"Transform analysis failed: {exc}")
            return None


__all__ = ["TextPolicy", "FontDecisionContext"]
