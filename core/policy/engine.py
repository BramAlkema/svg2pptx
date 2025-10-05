#!/usr/bin/env python3
"""
Policy Engine Implementation

The brain of SVG2PPTX - makes all "native DML vs EMF" decisions.
Centralized, configurable, and transparent decision making.
"""

import logging
import time
from typing import Any, Optional, Union

# Policy thresholds and constants
MIN_COLORS_FOR_COMPLEX_GRADIENT = 16
MIN_STOPS_FOR_COMPLEX_GRADIENT = 3
ARCH_PEAK_MIN_POSITION = 0.3  # 30% from start
ARCH_PEAK_MAX_POSITION = 0.7  # 70% from start
MIN_ARCH_HEIGHT = 10
COMPLEX_TRANSFORM_COUNT = 2
MIN_QUALITY_THRESHOLD = 0.2
VERY_LOW_QUALITY_THRESHOLD = 0.1
MAX_NESTED_GROUPS = 5
MAX_CLIP_COMPLEXITY = 10
MAX_SIMPLE_PATH_SEGMENTS = 10

from ..ir import (
    Group,
    Image,
    LinearGradientPaint,
    Paint,
    Path,
    RadialGradientPaint,
    Stroke,
    TextFrame,
)
from .config import OutputTarget, PolicyConfig
from .targets import (
    AnimationDecision,
    ClipPathDecision,
    DecisionReason,
    FilterDecision,
    GradientDecision,
    GroupDecision,
    ImageDecision,
    MultiPageDecision,
    PathDecision,
    PolicyMetrics,
    TextDecision,
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
                confidence=0.9,
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
                confidence=0.95,
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
                confidence=0.85,
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
                confidence=0.9,
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
            estimated_performance=0.9,
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
                confidence=0.9,
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
                confidence=0.85,
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
                confidence=0.8,
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
                confidence=0.95,
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
                confidence=0.9,
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
                estimated_performance=0.98,  # WordArt is very fast
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
            estimated_performance=0.95,
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
                confidence=0.9,
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
                confidence=0.85,
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
            estimated_performance=0.85,
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
            estimated_performance=0.9,
        )
        self._current_decision = decision
        return decision

    def _has_complex_stroke(self, stroke: Stroke | None) -> bool:
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
        # PRIORITY: MEDIUM - Better font fallback decisions
        # EFFORT: 2-3 hours - Font service integration
        # BLOCKER: None - Font service is available
        # TRACKING: Issue #TBD - Font availability checking in policy engine
        return False

    def _check_wordart_opportunity(self, text: TextFrame) -> dict[str, Any] | None:
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
                PathSamplingMethod,
                create_curve_text_positioner,
            )

            # Create deterministic positioner for WordArt classification
            positioner = create_curve_text_positioner(PathSamplingMethod.DETERMINISTIC)

            # Sample path with appropriate density for classification
            num_samples = min(self.config.wordart_max_sample_points, 128)
            path_points = positioner.sample_path_for_text(
                text.text_path.path_data,
                num_samples,
            )

            if len(path_points) < MIN_COLORS_FOR_COMPLEX_GRADIENT:  # Need minimum points for classification
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

    def _classify_wordart_pattern(self, path_points) -> dict[str, Any] | None:
        """
        Simplified WordArt pattern classification.

        This is a basic implementation - the full implementation would use
        the sophisticated algorithms from the deterministic_curve_positioning.py spec.
        """
        if len(path_points) < MIN_COLORS_FOR_COMPLEX_GRADIENT:
            return None

        # Basic pattern detection (simplified for integration)
        # Real implementation would use FFT, circle fitting, etc.

        # Check for simple arch pattern (basic heuristic)
        y_values = [p.y for p in path_points]
        [p.x for p in path_points]

        # Simple arch detection: check if Y values form single peak
        if len(y_values) >= MIN_STOPS_FOR_COMPLEX_GRADIENT:
            max_y_idx = y_values.index(max(y_values))
            min_y = min(y_values)
            max_y = max(y_values)

            # If peak is in middle and there's significant height variation
            if (ARCH_PEAK_MIN_POSITION <= max_y_idx / len(y_values) <= ARCH_PEAK_MAX_POSITION and
                (max_y - min_y) > MIN_ARCH_HEIGHT):  # Minimum arch height

                return {
                    'preset': 'arch',
                    'parameters': {
                        'bend': min(1.0, (max_y - min_y) / 100.0),
                    },
                    'confidence': 0.85,
                }

        # Check for roughly horizontal line (rise/slant)
        if len(path_points) >= COMPLEX_TRANSFORM_COUNT:
            start_y = path_points[0].y
            end_y = path_points[-1].y
            start_x = path_points[0].x
            end_x = path_points[-1].x

            y_range = abs(end_y - start_y)
            x_range = abs(end_x - start_x)

            # If mostly horizontal with slight slope
            if x_range > 0 and y_range / max(x_range, 1) < MIN_QUALITY_THRESHOLD:
                slope = (end_y - start_y) / x_range
                return {
                    'preset': 'rise' if abs(slope) < VERY_LOW_QUALITY_THRESHOLD else 'slant',
                    'parameters': {
                        'angle': slope,
                    },
                    'confidence': 0.9,
                }

        return None

    def _analyze_transform_complexity(self, text: TextFrame) -> dict[str, Any] | None:
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
                analysis['complexity_score'] < MAX_NESTED_GROUPS
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
            len(group.children) < MAX_CLIP_COMPLEXITY and
            group.clip is None
        )

    def decide_filter(self, filter_element: Any = None, filter_type: str = "",
                     primitive_count: int = 0) -> FilterDecision:
        """
        Decide output format for SVG filter effects.

        Args:
            filter_element: Optional filter element from SVG
            filter_type: Type of filter ('blur', 'shadow', 'color_matrix', etc.)
            primitive_count: Number of filter primitives in chain

        Returns:
            FilterDecision with reasoning
        """
        start_time = time.time()
        decision = self._analyze_filter(filter_type, primitive_count)
        elapsed_ms = (time.time() - start_time) * 1000.0

        if self.config.enable_metrics:
            self.metrics.record_decision(decision, elapsed_ms)

        return decision

    def _analyze_filter(self, filter_type: str, primitive_count: int) -> FilterDecision:
        """Analyze filter complexity and make decision"""
        thresholds = self.config.thresholds

        # Calculate complexity score (0-100)
        complexity_score = primitive_count * 10  # Simple scoring for now

        # Check if too many primitives
        if primitive_count > thresholds.max_filter_primitives:
            return FilterDecision.emf(
                filter_type=filter_type or 'chain',
                reasons=[DecisionReason.FILTER_CHAIN_COMPLEX, DecisionReason.ABOVE_THRESHOLDS],
                primitive_count=primitive_count,
                complexity_score=complexity_score,
            )

        # Check complexity score
        if complexity_score > thresholds.max_filter_complexity_score:
            if thresholds.prefer_filter_rasterization:
                return FilterDecision.rasterize(
                    filter_type=filter_type or 'complex',
                    reasons=[DecisionReason.FILTER_RASTERIZED, DecisionReason.ABOVE_THRESHOLDS],
                    primitive_count=primitive_count,
                    complexity_score=complexity_score,
                )
            else:
                return FilterDecision.emf(
                    filter_type=filter_type or 'complex',
                    reasons=[DecisionReason.FILTER_CHAIN_COMPLEX],
                    primitive_count=primitive_count,
                    complexity_score=complexity_score,
                )

        # Check for native support
        if filter_type == 'blur' and thresholds.enable_native_blur:
            return FilterDecision.native(
                filter_type='blur',
                reasons=[DecisionReason.NATIVE_FILTER_AVAILABLE, DecisionReason.SIMPLE_FILTER],
                primitive_count=primitive_count,
                complexity_score=complexity_score,
                native_approximation='<a:blur>',
            )

        if filter_type == 'shadow' and thresholds.enable_native_shadow:
            return FilterDecision.native(
                filter_type='shadow',
                reasons=[DecisionReason.NATIVE_FILTER_AVAILABLE, DecisionReason.SIMPLE_FILTER],
                primitive_count=primitive_count,
                complexity_score=complexity_score,
                native_approximation='<a:outerShdw>',
            )

        # Simple filters can use approximation
        if primitive_count <= COMPLEX_TRANSFORM_COUNT and thresholds.enable_filter_approximation:
            return FilterDecision.native(
                filter_type=filter_type or 'simple',
                reasons=[DecisionReason.SIMPLE_FILTER, DecisionReason.BELOW_THRESHOLDS],
                primitive_count=primitive_count,
                complexity_score=complexity_score,
            )

        # Default to EMF for unsupported filters
        return FilterDecision.emf(
            filter_type=filter_type or 'unknown',
            reasons=[DecisionReason.UNSUPPORTED_FILTER_PRIMITIVE],
            primitive_count=primitive_count,
            complexity_score=complexity_score,
            has_unsupported_primitives=True,
        )

    def decide_gradient(self, gradient: LinearGradientPaint | RadialGradientPaint | Any = None,
                       gradient_type: str = "", stop_count: int = 0,
                       mesh_rows: int = 0, mesh_cols: int = 0) -> GradientDecision:
        """
        Decide output format for gradient fills.

        Args:
            gradient: Gradient paint object
            gradient_type: 'linear', 'radial', 'mesh', or 'conic'
            stop_count: Number of gradient stops
            mesh_rows: Mesh gradient rows (if applicable)
            mesh_cols: Mesh gradient columns (if applicable)

        Returns:
            GradientDecision with reasoning
        """
        start_time = time.time()
        decision = self._analyze_gradient(gradient_type, stop_count, mesh_rows, mesh_cols)
        elapsed_ms = (time.time() - start_time) * 1000.0

        if self.config.enable_metrics:
            self.metrics.record_decision(decision, elapsed_ms)

        return decision

    def _analyze_gradient(self, gradient_type: str, stop_count: int,
                         mesh_rows: int, mesh_cols: int) -> GradientDecision:
        """Analyze gradient complexity and make decision"""
        thresholds = self.config.thresholds

        # Calculate mesh patch count if mesh gradient
        mesh_patch_count = 0
        if gradient_type == 'mesh' and mesh_rows > 0 and mesh_cols > 0:
            mesh_patch_count = mesh_rows * mesh_cols * 4  # 4 patches per grid cell

        # Check mesh gradient limits
        if gradient_type == 'mesh':
            if mesh_patch_count > thresholds.max_mesh_patches or \
               mesh_rows > thresholds.max_mesh_grid_size or \
               mesh_cols > thresholds.max_mesh_grid_size:
                return GradientDecision(
                    use_native=False,
                    reasons=[DecisionReason.MESH_GRADIENT_COMPLEX, DecisionReason.ABOVE_THRESHOLDS],
                    gradient_type='mesh',
                    stop_count=stop_count,
                    mesh_rows=mesh_rows,
                    mesh_cols=mesh_cols,
                    mesh_patch_count=mesh_patch_count,
                )

        # Check stop count
        if stop_count > thresholds.max_gradient_stops:
            if thresholds.enable_gradient_simplification:
                return GradientDecision.simplified(
                    gradient_type=gradient_type or 'linear',
                    stop_count=stop_count,
                    mesh_rows=mesh_rows,
                    mesh_cols=mesh_cols,
                    mesh_patch_count=mesh_patch_count,
                )
            else:
                return GradientDecision(
                    use_native=False,
                    reasons=[DecisionReason.TOO_MANY_GRADIENT_STOPS, DecisionReason.ABOVE_THRESHOLDS],
                    gradient_type=gradient_type or 'linear',
                    stop_count=stop_count,
                )

        # Simple gradients use native
        return GradientDecision.native(
            gradient_type=gradient_type or 'linear',
            reasons=[DecisionReason.SIMPLE_GRADIENT, DecisionReason.BELOW_THRESHOLDS],
            stop_count=stop_count,
            mesh_rows=mesh_rows,
            mesh_cols=mesh_cols,
            mesh_patch_count=mesh_patch_count,
        )

    def decide_multipage(self, page_count: int = 1, detection_method: str = "none",
                        total_size_bytes: int = 0, elements_per_page: list[int] = None,
                        page_titles: list[str | None] = None) -> MultiPageDecision:
        """
        Decide multi-page SVG handling strategy.

        Args:
            page_count: Number of detected pages
            detection_method: 'markers', 'grouped', 'size_split', or 'none'
            total_size_bytes: Total SVG content size
            elements_per_page: Element count per page
            page_titles: Titles for each page

        Returns:
            MultiPageDecision with reasoning
        """
        start_time = time.time()
        decision = self._analyze_multipage(page_count, detection_method, total_size_bytes,
                                           elements_per_page, page_titles)
        elapsed_ms = (time.time() - start_time) * 1000.0

        if self.config.enable_metrics:
            self.metrics.record_decision(decision, elapsed_ms)

        return decision

    def _analyze_multipage(self, page_count: int, detection_method: str, total_size_bytes: int,
                          elements_per_page: list[int] = None,
                          page_titles: list[str | None] = None) -> MultiPageDecision:
        """Analyze multi-page requirements and make decision"""
        thresholds = self.config.thresholds

        # Single page if count is 1
        if page_count <= 1:
            return MultiPageDecision.single_page(
                total_size_bytes=total_size_bytes,
            )

        # Check page limit
        if page_count > thresholds.max_pages_per_conversion:
            return MultiPageDecision.single_page(
                reasons=[DecisionReason.PAGE_LIMIT_EXCEEDED],
                total_size_bytes=total_size_bytes,
                page_titles=['Page limit exceeded - treating as single page'],
            )

        # Check size threshold for auto-splitting
        size_kb = total_size_bytes / 1024
        if size_kb > thresholds.max_single_page_size_kb and thresholds.enable_size_based_splitting:
            return MultiPageDecision.multi_page(
                page_count=page_count,
                method=detection_method or 'size_split',
                reasons=[DecisionReason.SIZE_THRESHOLD_EXCEEDED],
                total_size_bytes=total_size_bytes,
                elements_per_page=elements_per_page,
                page_titles=page_titles,
                split_threshold_exceeded=True,
            )

        # Explicit page markers
        if detection_method == 'markers' and thresholds.prefer_explicit_markers:
            return MultiPageDecision.multi_page(
                page_count=page_count,
                method='markers',
                reasons=[DecisionReason.EXPLICIT_PAGE_MARKERS],
                total_size_bytes=total_size_bytes,
                elements_per_page=elements_per_page,
                page_titles=page_titles,
            )

        # Grouped content detected
        if detection_method == 'grouped':
            return MultiPageDecision.multi_page(
                page_count=page_count,
                method='grouped',
                reasons=[DecisionReason.GROUPED_CONTENT_DETECTED],
                total_size_bytes=total_size_bytes,
                elements_per_page=elements_per_page,
                page_titles=page_titles,
            )

        # Default multi-page
        return MultiPageDecision.multi_page(
            page_count=page_count,
            method=detection_method or 'auto',
            total_size_bytes=total_size_bytes,
            elements_per_page=elements_per_page,
            page_titles=page_titles,
        )

    def decide_animation(self, animation_type: str = "", keyframe_count: int = 0,
                        duration_ms: float = 0.0, interpolation: str = "linear") -> AnimationDecision:
        """
        Decide animation conversion strategy.

        Args:
            animation_type: 'transform', 'opacity', 'color', 'path', or 'sequence'
            keyframe_count: Number of keyframes
            duration_ms: Animation duration in milliseconds
            interpolation: Interpolation type

        Returns:
            AnimationDecision with reasoning
        """
        start_time = time.time()
        decision = self._analyze_animation(animation_type, keyframe_count, duration_ms, interpolation)
        elapsed_ms = (time.time() - start_time) * 1000.0

        if self.config.enable_metrics:
            self.metrics.record_decision(decision, elapsed_ms)

        return decision

    def _analyze_animation(self, animation_type: str, keyframe_count: int,
                          duration_ms: float, interpolation: str) -> AnimationDecision:
        """Analyze animation complexity and make decision"""
        thresholds = self.config.thresholds

        # Check if animation conversion is disabled
        if not thresholds.enable_animation_conversion:
            return AnimationDecision.skip(
                animation_type=animation_type or 'unknown',
                reasons=[DecisionReason.ANIMATION_SKIPPED, DecisionReason.USER_PREFERENCE],
                keyframe_count=keyframe_count,
                duration_ms=duration_ms,
                interpolation=interpolation,
            )

        # Check keyframe count
        if keyframe_count > thresholds.max_animation_keyframes:
            return AnimationDecision.skip(
                animation_type=animation_type or 'complex',
                reasons=[DecisionReason.ANIMATION_TOO_COMPLEX, DecisionReason.ABOVE_THRESHOLDS],
                keyframe_count=keyframe_count,
                duration_ms=duration_ms,
                interpolation=interpolation,
            )

        # Check duration
        if duration_ms > thresholds.max_animation_duration_ms:
            return AnimationDecision.skip(
                animation_type=animation_type or 'long',
                reasons=[DecisionReason.ANIMATION_TOO_COMPLEX],
                keyframe_count=keyframe_count,
                duration_ms=duration_ms,
                interpolation=interpolation,
            )

        # Simple animations can convert
        return AnimationDecision.native(
            animation_type=animation_type or 'transform',
            reasons=[DecisionReason.SIMPLE_ANIMATION, DecisionReason.BELOW_THRESHOLDS],
            keyframe_count=keyframe_count,
            duration_ms=duration_ms,
            interpolation=interpolation,
        )

    def decide_clippath(self, clip_type: str = "", path_complexity: int = 0,
                       nesting_level: int = 0, has_boolean_ops: bool = False,
                       boolean_op_type: str | None = None) -> ClipPathDecision:
        """
        Decide clipping path rendering strategy.

        Args:
            clip_type: 'rect', 'ellipse', 'path', 'complex', or 'boolean'
            path_complexity: Number of path segments
            nesting_level: Clip nesting depth
            has_boolean_ops: Whether boolean operations are needed
            boolean_op_type: 'union', 'intersect', or 'subtract'

        Returns:
            ClipPathDecision with reasoning
        """
        start_time = time.time()
        decision = self._analyze_clippath(clip_type, path_complexity, nesting_level,
                                          has_boolean_ops, boolean_op_type)
        elapsed_ms = (time.time() - start_time) * 1000.0

        if self.config.enable_metrics:
            self.metrics.record_decision(decision, elapsed_ms)

        return decision

    def _analyze_clippath(self, clip_type: str, path_complexity: int, nesting_level: int,
                         has_boolean_ops: bool, boolean_op_type: str | None) -> ClipPathDecision:
        """Analyze clipping path complexity and make decision"""
        thresholds = self.config.thresholds

        # Check if native clipping is disabled
        if not thresholds.enable_native_clipping:
            return ClipPathDecision.emf(
                clip_type=clip_type or 'disabled',
                reasons=[DecisionReason.USER_PREFERENCE],
                path_complexity=path_complexity,
                nesting_level=nesting_level,
                has_boolean_ops=has_boolean_ops,
                boolean_op_type=boolean_op_type,
            )

        # Check boolean operations
        if has_boolean_ops and not thresholds.enable_boolean_operations:
            return ClipPathDecision.emf(
                clip_type='boolean',
                reasons=[DecisionReason.BOOLEAN_CLIP_OPERATION, DecisionReason.UNSUPPORTED_FEATURES],
                path_complexity=path_complexity,
                nesting_level=nesting_level,
                has_boolean_ops=True,
                boolean_op_type=boolean_op_type,
            )

        # Check nesting depth
        if nesting_level > thresholds.max_clip_nesting_depth:
            return ClipPathDecision.emf(
                clip_type=clip_type or 'nested',
                reasons=[DecisionReason.NESTED_CLIPPING, DecisionReason.ABOVE_THRESHOLDS],
                path_complexity=path_complexity,
                nesting_level=nesting_level,
                has_boolean_ops=has_boolean_ops,
                boolean_op_type=boolean_op_type,
            )

        # Check path complexity
        if path_complexity > thresholds.max_clip_path_segments:
            return ClipPathDecision.emf(
                clip_type='complex',
                reasons=[DecisionReason.CLIP_PATH_COMPLEX, DecisionReason.ABOVE_THRESHOLDS],
                path_complexity=path_complexity,
                nesting_level=nesting_level,
                has_boolean_ops=has_boolean_ops,
                boolean_op_type=boolean_op_type,
            )

        # Simple clips use native
        if clip_type in ('rect', 'ellipse') or path_complexity <= MAX_CLIP_COMPLEXITY:
            return ClipPathDecision.native(
                clip_type=clip_type or 'simple',
                reasons=[DecisionReason.SIMPLE_CLIP_PATH, DecisionReason.BELOW_THRESHOLDS],
                path_complexity=path_complexity,
                nesting_level=nesting_level,
                has_boolean_ops=has_boolean_ops,
                boolean_op_type=boolean_op_type,
            )

        # Default to native for moderate complexity
        return ClipPathDecision.native(
            clip_type=clip_type or 'path',
            reasons=[DecisionReason.SIMPLE_CLIP_PATH],
            path_complexity=path_complexity,
            nesting_level=nesting_level,
            has_boolean_ops=has_boolean_ops,
            boolean_op_type=boolean_op_type,
        )

    def get_metrics(self) -> PolicyMetrics:
        """Get policy decision metrics"""
        return self.metrics

    def reset_metrics(self):
        """Reset policy metrics"""
        self.metrics = PolicyMetrics()


def create_policy(target: str | OutputTarget = OutputTarget.BALANCED, **kwargs) -> Policy:
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