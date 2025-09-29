#!/usr/bin/env python3
"""
Policy Engine Implementation

The brain of SVG2PPTX - makes all "native DML vs EMF" decisions.
Centralized, configurable, and transparent decision making.
"""

import time
from typing import List, Optional, Union, Dict, Any
import logging

from ..ir import Path, TextFrame, Group, Image, Paint, Stroke, ClipRef
from ..ir import LinearGradientPaint, RadialGradientPaint, SolidPaint
from .config import PolicyConfig, OutputTarget
from .targets import (
    PolicyDecision, PathDecision, TextDecision, GroupDecision, ImageDecision,
    DecisionReason, PolicyMetrics
)


class Policy:
    """
    Central policy engine for output format decisions.

    Makes smart decisions about when to use native DrawingML vs EMF fallback
    based on element complexity, target quality, and performance constraints.
    """

    def __init__(self, config: PolicyConfig = None):
        """
        Initialize policy engine.

        Args:
            config: Policy configuration (defaults to BALANCED)
        """
        self.config = config or PolicyConfig()
        self.metrics = PolicyMetrics()
        self.logger = logging.getLogger(__name__)

        if self.config.log_decisions:
            self.logger.setLevel(logging.DEBUG)

    def decide_path(self, path: Path) -> PathDecision:
        """
        Decide output format for Path element.

        Args:
            path: Path IR element

        Returns:
            PathDecision with reasoning
        """
        start_time = time.perf_counter()

        try:
            decision = self._analyze_path(path)
            return decision
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            if hasattr(self, '_current_decision'):
                self.metrics.record_decision(self._current_decision, elapsed_ms)

    def decide_text(self, text: TextFrame) -> TextDecision:
        """
        Decide output format for TextFrame element.

        Args:
            text: TextFrame IR element

        Returns:
            TextDecision with reasoning
        """
        start_time = time.perf_counter()

        try:
            decision = self._analyze_text(text)
            return decision
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            if hasattr(self, '_current_decision'):
                self.metrics.record_decision(self._current_decision, elapsed_ms)

    def decide_group(self, group: Group) -> GroupDecision:
        """
        Decide output format for Group element.

        Args:
            group: Group IR element

        Returns:
            GroupDecision with reasoning
        """
        start_time = time.perf_counter()

        try:
            decision = self._analyze_group(group)
            return decision
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            if hasattr(self, '_current_decision'):
                self.metrics.record_decision(self._current_decision, elapsed_ms)

    def decide_image(self, image: Image) -> ImageDecision:
        """
        Decide output format for Image element.

        Args:
            image: Image IR element

        Returns:
            ImageDecision with reasoning
        """
        start_time = time.perf_counter()

        try:
            decision = self._analyze_image(image)
            return decision
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            if hasattr(self, '_current_decision'):
                self.metrics.record_decision(self._current_decision, elapsed_ms)

    def _analyze_path(self, path: Path) -> PathDecision:
        """Analyze path and make policy decision"""
        reasons = []
        segment_count = len(path.segments)
        complexity_score = path.complexity_score
        has_clipping = path.clip is not None
        has_complex_stroke = self._has_complex_stroke(path.stroke)
        has_complex_fill = self._has_complex_fill(path.fill)

        # Conservative mode overrides
        if self.config.conservative_clipping and has_clipping:
            reasons.append(DecisionReason.CONSERVATIVE_MODE)
            decision = PathDecision.emf(
                reasons=reasons,
                segment_count=segment_count,
                complexity_score=complexity_score,
                has_clipping=has_clipping,
                has_complex_stroke=has_complex_stroke,
                has_complex_fill=has_complex_fill,
                confidence=0.9
            )
            self._current_decision = decision
            return decision

        # Check segment count threshold
        if segment_count > self.config.thresholds.max_path_segments:
            reasons.append(DecisionReason.ABOVE_THRESHOLDS)
            reasons.append(DecisionReason.COMPLEX_GEOMETRY)
            decision = PathDecision.emf(
                reasons=reasons,
                segment_count=segment_count,
                complexity_score=complexity_score,
                has_clipping=has_clipping,
                has_complex_stroke=has_complex_stroke,
                has_complex_fill=has_complex_fill,
                confidence=0.95
            )
            self._current_decision = decision
            return decision

        # Check complexity score threshold
        if complexity_score > self.config.thresholds.max_path_complexity_score:
            reasons.append(DecisionReason.ABOVE_THRESHOLDS)
            if has_complex_stroke:
                reasons.append(DecisionReason.STROKE_COMPLEX)
            if has_complex_fill:
                reasons.append(DecisionReason.GRADIENT_COMPLEX)
            if has_clipping:
                reasons.append(DecisionReason.CLIPPING_COMPLEX)

            decision = PathDecision.emf(
                reasons=reasons,
                segment_count=segment_count,
                complexity_score=complexity_score,
                has_clipping=has_clipping,
                has_complex_stroke=has_complex_stroke,
                has_complex_fill=has_complex_fill,
                confidence=0.85
            )
            self._current_decision = decision
            return decision

        # Check for unsupported features
        if path.has_complex_features:
            reasons.append(DecisionReason.UNSUPPORTED_FEATURES)
            decision = PathDecision.emf(
                reasons=reasons,
                segment_count=segment_count,
                complexity_score=complexity_score,
                has_clipping=has_clipping,
                has_complex_stroke=has_complex_stroke,
                has_complex_fill=has_complex_fill,
                confidence=0.9
            )
            self._current_decision = decision
            return decision

        # Use native DrawingML
        reasons.append(DecisionReason.BELOW_THRESHOLDS)
        reasons.append(DecisionReason.SIMPLE_GEOMETRY)
        if not has_clipping:
            reasons.append(DecisionReason.SUPPORTED_FEATURES)

        decision = PathDecision.native(
            reasons=reasons,
            segment_count=segment_count,
            complexity_score=complexity_score,
            has_clipping=has_clipping,
            has_complex_stroke=has_complex_stroke,
            has_complex_fill=has_complex_fill,
            confidence=0.95,
            estimated_quality=0.98,
            estimated_performance=0.9
        )
        self._current_decision = decision
        return decision

    def _analyze_text(self, text: TextFrame) -> TextDecision:
        """Analyze text and make policy decision"""
        reasons = []
        run_count = len(text.runs)
        complexity_score = text.complexity_score
        has_effects = any(run.has_decoration for run in text.runs)
        has_multiline = text.is_multiline

        # Check for missing fonts (simplified - would integrate with font service)
        has_missing_fonts = self._check_missing_fonts(text)

        # Conservative mode overrides
        if self.config.conservative_text and has_effects:
            reasons.append(DecisionReason.CONSERVATIVE_MODE)
            reasons.append(DecisionReason.TEXT_EFFECTS_COMPLEX)
            decision = TextDecision.emf(
                reasons=reasons,
                run_count=run_count,
                complexity_score=complexity_score,
                has_missing_fonts=has_missing_fonts,
                has_effects=has_effects,
                has_multiline=has_multiline,
                confidence=0.9
            )
            self._current_decision = decision
            return decision

        # Check run count threshold
        if run_count > self.config.thresholds.max_text_runs:
            reasons.append(DecisionReason.ABOVE_THRESHOLDS)
            reasons.append(DecisionReason.COMPLEX_GEOMETRY)
            decision = TextDecision.emf(
                reasons=reasons,
                run_count=run_count,
                complexity_score=complexity_score,
                has_missing_fonts=has_missing_fonts,
                has_effects=has_effects,
                has_multiline=has_multiline,
                confidence=0.85
            )
            self._current_decision = decision
            return decision

        # Check complexity score
        if complexity_score > self.config.thresholds.max_text_complexity_score:
            reasons.append(DecisionReason.ABOVE_THRESHOLDS)
            if has_effects:
                reasons.append(DecisionReason.TEXT_EFFECTS_COMPLEX)
            decision = TextDecision.emf(
                reasons=reasons,
                run_count=run_count,
                complexity_score=complexity_score,
                has_missing_fonts=has_missing_fonts,
                has_effects=has_effects,
                has_multiline=has_multiline,
                confidence=0.8
            )
            self._current_decision = decision
            return decision

        # Check for missing fonts
        if has_missing_fonts:
            reasons.append(DecisionReason.FONT_UNAVAILABLE)
            decision = TextDecision.emf(
                reasons=reasons,
                run_count=run_count,
                complexity_score=complexity_score,
                has_missing_fonts=has_missing_fonts,
                has_effects=has_effects,
                has_multiline=has_multiline,
                confidence=0.95
            )
            self._current_decision = decision
            return decision

        # Check transform complexity for WordArt compatibility
        transform_analysis = self._analyze_transform_complexity(text)
        if transform_analysis and not transform_analysis['can_wordart_native']:
            reasons.append(DecisionReason.COMPLEX_TRANSFORM)
            if transform_analysis['max_skew_exceeded']:
                reasons.append(DecisionReason.ABOVE_THRESHOLDS)
            decision = TextDecision.emf(
                reasons=reasons,
                run_count=run_count,
                complexity_score=complexity_score,
                has_missing_fonts=has_missing_fonts,
                has_effects=has_effects,
                has_multiline=has_multiline,
                transform_complexity=transform_analysis,
                confidence=0.9
            )
            self._current_decision = decision
            return decision

        # Check for WordArt pattern if text has a path
        wordart_result = self._check_wordart_opportunity(text)
        if wordart_result and wordart_result['confidence'] >= self.config.wordart_confidence_threshold:
            reasons.append(DecisionReason.WORDART_PATTERN_DETECTED)
            reasons.append(DecisionReason.NATIVE_PRESET_AVAILABLE)

            decision = TextDecision.wordart(
                preset=wordart_result['preset'],
                parameters=wordart_result['parameters'],
                confidence=wordart_result['confidence'],
                reasons=reasons,
                run_count=run_count,
                complexity_score=complexity_score,
                has_missing_fonts=has_missing_fonts,
                has_effects=has_effects,
                has_multiline=has_multiline,
                estimated_quality=0.95,  # WordArt maintains high quality
                estimated_performance=0.98  # WordArt is very fast
            )
            self._current_decision = decision
            return decision

        # Use native DrawingML
        reasons.append(DecisionReason.BELOW_THRESHOLDS)
        reasons.append(DecisionReason.FONT_AVAILABLE)
        reasons.append(DecisionReason.SUPPORTED_FEATURES)

        decision = TextDecision.native(
            reasons=reasons,
            run_count=run_count,
            complexity_score=complexity_score,
            has_missing_fonts=has_missing_fonts,
            has_effects=has_effects,
            has_multiline=has_multiline,
            confidence=0.95,
            estimated_quality=0.98,
            estimated_performance=0.95
        )
        self._current_decision = decision
        return decision

    def _analyze_group(self, group: Group) -> GroupDecision:
        """Analyze group and make policy decision"""
        reasons = []
        element_count = len(group.children)
        nesting_depth = self._calculate_nesting_depth(group)
        has_complex_clipping = group.clip is not None
        should_flatten = self._should_flatten_group(group)

        # Check element count threshold
        if element_count > self.config.thresholds.max_group_elements:
            reasons.append(DecisionReason.ABOVE_THRESHOLDS)
            reasons.append(DecisionReason.COMPLEX_GEOMETRY)
            decision = GroupDecision.emf(
                reasons=reasons,
                element_count=element_count,
                nesting_depth=nesting_depth,
                should_flatten=should_flatten,
                has_complex_clipping=has_complex_clipping,
                confidence=0.9
            )
            self._current_decision = decision
            return decision

        # Check nesting depth
        if nesting_depth > self.config.thresholds.max_nesting_depth:
            reasons.append(DecisionReason.ABOVE_THRESHOLDS)
            reasons.append(DecisionReason.COMPLEX_GEOMETRY)
            decision = GroupDecision.emf(
                reasons=reasons,
                element_count=element_count,
                nesting_depth=nesting_depth,
                should_flatten=should_flatten,
                has_complex_clipping=has_complex_clipping,
                confidence=0.85
            )
            self._current_decision = decision
            return decision

        # Use native DrawingML
        reasons.append(DecisionReason.BELOW_THRESHOLDS)
        reasons.append(DecisionReason.SIMPLE_GEOMETRY)

        decision = GroupDecision.native(
            reasons=reasons,
            element_count=element_count,
            nesting_depth=nesting_depth,
            should_flatten=should_flatten,
            has_complex_clipping=has_complex_clipping,
            confidence=0.9,
            estimated_quality=0.95,
            estimated_performance=0.85
        )
        self._current_decision = decision
        return decision

    def _analyze_image(self, image: Image) -> ImageDecision:
        """Analyze image and make policy decision"""
        reasons = []
        size_bytes = len(image.data)
        has_transparency = image.format in ["png", "gif"]

        # Images typically go to EMF for best fidelity
        reasons.append(DecisionReason.PERFORMANCE_OK)
        decision = ImageDecision.emf(
            reasons=reasons,
            format=image.format,
            size_bytes=size_bytes,
            has_transparency=has_transparency,
            confidence=0.95,
            estimated_quality=0.98,
            estimated_performance=0.9
        )
        self._current_decision = decision
        return decision

    def _has_complex_stroke(self, stroke: Optional[Stroke]) -> bool:
        """Check if stroke has complex features"""
        if stroke is None:
            return False

        return (
            stroke.is_dashed or
            stroke.width > self.config.thresholds.max_stroke_width or
            stroke.miter_limit > self.config.thresholds.max_miter_limit or
            isinstance(stroke.paint, (LinearGradientPaint, RadialGradientPaint))
        )

    def _has_complex_fill(self, fill: Paint) -> bool:
        """Check if fill has complex features"""
        if fill is None:
            return False

        if isinstance(fill, (LinearGradientPaint, RadialGradientPaint)):
            stops = len(fill.stops)
            return stops > self.config.thresholds.max_gradient_stops

        return False

    def _check_missing_fonts(self, text: TextFrame) -> bool:
        """Check if any fonts are missing (simplified)"""
        # TODO: Integrate with font service to check font availability
        return False

    def _check_wordart_opportunity(self, text: TextFrame) -> Optional[Dict[str, Any]]:
        """
        Check if text with path can be converted to WordArt preset.

        Args:
            text: TextFrame IR element

        Returns:
            Dict with preset info if WordArt opportunity found, None otherwise
        """
        if not self.config.enable_wordart_classification:
            return None

        # Only check TextPath elements (text with path data)
        if not hasattr(text, 'text_path') or not text.text_path:
            return None

        try:
            # Import curve positioner with deterministic sampling
            from ..algorithms.curve_text_positioning import (
                create_curve_text_positioner, PathSamplingMethod
            )

            # Create deterministic positioner for WordArt classification
            positioner = create_curve_text_positioner(PathSamplingMethod.DETERMINISTIC)

            # Sample path with appropriate density for classification
            num_samples = min(self.config.wordart_max_sample_points, 128)
            path_points = positioner.sample_path_for_text(
                text.text_path.path_data,
                num_samples
            )

            if len(path_points) < 16:  # Need minimum points for classification
                return None

            # Classify using simplified pattern detection
            wordart_result = self._classify_wordart_pattern(path_points)

            # Only return if confidence meets threshold
            if wordart_result and wordart_result['confidence'] >= self.config.wordart_confidence_threshold:
                return wordart_result

            return None

        except Exception as e:
            self.logger.debug(f"WordArt classification failed: {e}")
            return None

    def _classify_wordart_pattern(self, path_points) -> Optional[Dict[str, Any]]:
        """
        Simplified WordArt pattern classification.

        This is a basic implementation - the full implementation would use
        the sophisticated algorithms from the deterministic_curve_positioning.py spec.
        """
        if len(path_points) < 16:
            return None

        # Basic pattern detection (simplified for integration)
        # Real implementation would use FFT, circle fitting, etc.

        # Check for simple arch pattern (basic heuristic)
        y_values = [p.y for p in path_points]
        x_values = [p.x for p in path_points]

        # Simple arch detection: check if Y values form single peak
        if len(y_values) >= 3:
            max_y_idx = y_values.index(max(y_values))
            min_y = min(y_values)
            max_y = max(y_values)

            # If peak is in middle and there's significant height variation
            if (0.3 <= max_y_idx / len(y_values) <= 0.7 and
                (max_y - min_y) > 10):  # Minimum arch height

                return {
                    'preset': 'arch',
                    'parameters': {
                        'bend': min(1.0, (max_y - min_y) / 100.0)
                    },
                    'confidence': 0.85
                }

        # Check for roughly horizontal line (rise/slant)
        if len(path_points) >= 2:
            start_y = path_points[0].y
            end_y = path_points[-1].y
            start_x = path_points[0].x
            end_x = path_points[-1].x

            y_range = abs(end_y - start_y)
            x_range = abs(end_x - start_x)

            # If mostly horizontal with slight slope
            if x_range > 0 and y_range / max(x_range, 1) < 0.2:
                slope = (end_y - start_y) / x_range
                return {
                    'preset': 'rise' if abs(slope) < 0.1 else 'slant',
                    'parameters': {
                        'angle': slope
                    },
                    'confidence': 0.9
                }

        return None

    def _analyze_transform_complexity(self, text: TextFrame) -> Optional[Dict[str, Any]]:
        """
        Analyze transform complexity for WordArt compatibility decisions.

        Args:
            text: TextFrame IR element

        Returns:
            Transform analysis dict if element has transforms, None otherwise
        """
        # Only analyze elements with transforms
        if not hasattr(text, 'transform') or text.transform is None:
            return None

        try:
            # Import the transform decomposer service
            from ..services.wordart_transform_service import create_transform_decomposer

            # Create decomposer instance
            decomposer = create_transform_decomposer()

            # Decompose transform string or matrix
            if isinstance(text.transform, str):
                components = decomposer.decompose_transform_string(text.transform)
            else:
                components = decomposer.decompose_matrix(text.transform)

            # Use decomposer's complexity analysis
            analysis = decomposer.analyze_transform_complexity(components)

            # Apply policy thresholds
            max_skew_exceeded = components.max_skew_angle > self.config.thresholds.max_skew_angle_deg
            scale_ratio_exceeded = components.scale_ratio > self.config.thresholds.max_scale_ratio

            # Calculate rotation deviation from orthogonal angles
            rotation_mod_90 = abs(components.rotation_deg) % 90
            rotation_deviation = min(rotation_mod_90, 90 - rotation_mod_90)
            rotation_deviation_exceeded = rotation_deviation > self.config.thresholds.max_rotation_deviation_deg

            # Override complexity analysis with policy thresholds
            analysis['max_skew_exceeded'] = max_skew_exceeded
            analysis['scale_ratio_exceeded'] = scale_ratio_exceeded
            analysis['rotation_deviation_exceeded'] = rotation_deviation_exceeded

            # Update WordArt compatibility based on policy thresholds
            analysis['can_wordart_native'] = (
                not max_skew_exceeded and
                not scale_ratio_exceeded and
                not rotation_deviation_exceeded and
                analysis['complexity_score'] < 5
            )

            # Add policy-specific metadata
            analysis['policy_score'] = (
                (2 if max_skew_exceeded else 0) +
                (2 if scale_ratio_exceeded else 0) +
                (1 if rotation_deviation_exceeded else 0)
            )

            return analysis

        except Exception as e:
            self.logger.debug(f"Transform analysis failed: {e}")
            return None

    def _calculate_nesting_depth(self, group: Group, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth of group"""
        max_depth = current_depth
        for child in group.children:
            if isinstance(child, Group):
                child_depth = self._calculate_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
        return max_depth

    def _should_flatten_group(self, group: Group) -> bool:
        """Check if group should be flattened"""
        return (
            self.config.enable_group_flattening and
            group.is_leaf_group and
            len(group.children) < 10 and
            group.clip is None
        )

    def get_metrics(self) -> PolicyMetrics:
        """Get policy decision metrics"""
        return self.metrics

    def reset_metrics(self):
        """Reset policy metrics"""
        self.metrics = PolicyMetrics()


def create_policy(target: Union[str, OutputTarget] = OutputTarget.BALANCED, **kwargs) -> Policy:
    """
    Factory function to create policy with configuration.

    Args:
        target: Output target (speed/balanced/quality/compatibility)
        **kwargs: Additional configuration overrides

    Returns:
        Configured Policy instance
    """
    if isinstance(target, str):
        target = OutputTarget(target.lower())

    config = PolicyConfig.for_target(target, **kwargs)
    return Policy(config)


# Alias for backwards compatibility and clarity
PolicyEngine = Policy