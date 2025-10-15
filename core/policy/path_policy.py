"""
Path policy helper encapsulating native vs EMF decisions.
"""

from __future__ import annotations

import logging

from .config import PolicyConfig
from ..ir import LinearGradientPaint, Paint, Path, RadialGradientPaint, Stroke
from .targets import DecisionReason, PathDecision


class PathPolicy:
    """Evaluate path complexity and determine rendering strategy."""

    def __init__(self, config: PolicyConfig, logger: logging.Logger | None = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    def decide(self, path: Path) -> PathDecision:
        reasons: list[DecisionReason] = []
        segment_count = len(path.segments)
        complexity_score = path.complexity_score
        has_clipping = path.clip is not None
        native_clip_ready = bool(getattr(path.clip, 'path_segments', None))
        has_complex_stroke = self._has_complex_stroke(path.stroke)
        has_complex_fill = self._has_complex_fill(path.fill)

        thresholds = self.config.thresholds

        if self.config.conservative_clipping and has_clipping and not native_clip_ready:
            reasons.extend([DecisionReason.CONSERVATIVE_MODE])
            return PathDecision.emf(
                reasons=reasons,
                segment_count=segment_count,
                complexity_score=complexity_score,
                has_clipping=has_clipping,
                has_complex_stroke=has_complex_stroke,
                has_complex_fill=has_complex_fill,
                confidence=0.9,
            )

        if segment_count > thresholds.max_path_segments:
            reasons.extend([DecisionReason.ABOVE_THRESHOLDS, DecisionReason.COMPLEX_GEOMETRY])
            return PathDecision.emf(
                reasons=reasons,
                segment_count=segment_count,
                complexity_score=complexity_score,
                has_clipping=has_clipping,
                has_complex_stroke=has_complex_stroke,
                has_complex_fill=has_complex_fill,
                confidence=0.95,
            )

        if complexity_score > thresholds.max_path_complexity_score:
            reasons.append(DecisionReason.ABOVE_THRESHOLDS)
            if has_complex_stroke:
                reasons.append(DecisionReason.STROKE_COMPLEX)
            if has_complex_fill:
                reasons.append(DecisionReason.GRADIENT_COMPLEX)
            if has_clipping and not native_clip_ready:
                reasons.append(DecisionReason.CLIPPING_COMPLEX)

            return PathDecision.emf(
                reasons=reasons,
                segment_count=segment_count,
                complexity_score=complexity_score,
                has_clipping=has_clipping,
                has_complex_stroke=has_complex_stroke,
                has_complex_fill=has_complex_fill,
                confidence=0.85,
            )

        if path.has_complex_features and not native_clip_ready:
            reasons.append(DecisionReason.UNSUPPORTED_FEATURES)
            return PathDecision.emf(
                reasons=reasons,
                segment_count=segment_count,
                complexity_score=complexity_score,
                has_clipping=has_clipping,
                has_complex_stroke=has_complex_stroke,
                has_complex_fill=has_complex_fill,
                confidence=0.9,
            )

        reasons.extend([DecisionReason.BELOW_THRESHOLDS, DecisionReason.SIMPLE_GEOMETRY])
        if not has_clipping or native_clip_ready:
            reasons.append(DecisionReason.SUPPORTED_FEATURES)

        return PathDecision.native(
            reasons=reasons,
            segment_count=segment_count,
            complexity_score=complexity_score,
            has_clipping=has_clipping,
            has_complex_stroke=has_complex_stroke,
            has_complex_fill=has_complex_fill,
            confidence=0.95,
            estimated_quality=0.98,
            estimated_performance=0.9,
        )

    def _has_complex_stroke(self, stroke: Stroke | None) -> bool:
        if stroke is None:
            return False

        thresholds = self.config.thresholds
        return (
            stroke.is_dashed
            or stroke.width > thresholds.max_stroke_width
            or stroke.miter_limit > thresholds.max_miter_limit
            or isinstance(stroke.paint, (LinearGradientPaint, RadialGradientPaint))
        )

    def _has_complex_fill(self, fill: Paint | None) -> bool:
        if fill is None:
            return False

        thresholds = self.config.thresholds
        if isinstance(fill, (LinearGradientPaint, RadialGradientPaint)):
            stops = len(fill.stops)
            return stops > thresholds.max_gradient_stops
        return False


__all__ = ["PathPolicy"]
