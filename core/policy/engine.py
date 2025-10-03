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
    FontEmbeddingDecision, DecisionReason, PolicyMetrics
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

    def decide_image(self, image: Image, already_embedded: set = None) -> ImageDecision:
        """
        Decide output format for Image element.

        Args:
            image: Image IR element
            already_embedded: Set of SHA-256 checksums already embedded

        Returns:
            ImageDecision with reasoning
        """
        start_time = time.perf_counter()

        try:
            decision = self._analyze_image(image, already_embedded)
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
        """Analyze text and make font strategy decision"""
        reasons = []
        run_count = len(text.runs)
        complexity_score = text.complexity_score
        has_effects = any(run.has_decoration for run in text.runs)
        has_multiline = text.is_multiline

        # Analyze font availability for all runs
        font_availability = self._analyze_font_availability(text)
        has_missing_fonts = not any(font_availability.values())

        # Analyze text complexity for strategy selection
        complexity_analysis = self._analyze_text_complexity_for_strategy(text)

        # Conservative mode overrides - use EMF fallback
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
                font_availability=font_availability,
                confidence=0.9
            )
            self._current_decision = decision
            return decision

        # Check for extremely complex text - requires path conversion
        if complexity_analysis['requires_path_conversion']:
            reasons.append(DecisionReason.PATH_CONVERSION_REQUIRED)
            reasons.append(DecisionReason.HIGH_FIDELITY_REQUIRED)
            if complexity_analysis['complex_transforms']:
                reasons.append(DecisionReason.COMPLEX_TEXT_TRANSFORMS)

            decision = TextDecision.text_to_path(
                reasons=reasons,
                run_count=run_count,
                complexity_score=complexity_score,
                has_missing_fonts=has_missing_fonts,
                has_effects=has_effects,
                has_multiline=has_multiline,
                font_availability=font_availability,
                requires_path_conversion=True,
                confidence=0.8
            )
            self._current_decision = decision
            return decision

        # Check for WordArt opportunities
        wordart_result = self._check_wordart_opportunity(text)
        if (wordart_result and
            wordart_result['confidence'] >= self.config.wordart_confidence_threshold and
            not complexity_analysis['too_complex_for_wordart']):

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
                font_availability=font_availability,
                estimated_quality=0.95,
                estimated_performance=0.98
            )
            self._current_decision = decision
            return decision

        # Check if fonts need embedding
        if complexity_analysis['should_embed_fonts']:
            reasons.append(DecisionReason.FONT_EMBEDDING_PREFERRED)
            if complexity_analysis['requires_embedding']:
                reasons.append(DecisionReason.FONT_EMBEDDING_REQUIRED)

            decision = TextDecision.embedded_font(
                reasons=reasons,
                run_count=run_count,
                complexity_score=complexity_score,
                has_missing_fonts=has_missing_fonts,
                has_effects=has_effects,
                has_multiline=has_multiline,
                font_availability=font_availability,
                requires_embedding=True,
                confidence=0.85
            )
            self._current_decision = decision
            return decision

        # Check for system font suitability
        if complexity_analysis['system_font_suitable']:
            reasons.append(DecisionReason.SYSTEM_FONT_AVAILABLE)
            reasons.append(DecisionReason.SYSTEM_FONT_OPTIMAL)

            decision = TextDecision.system_font(
                reasons=reasons,
                run_count=run_count,
                complexity_score=complexity_score,
                has_missing_fonts=has_missing_fonts,
                has_effects=has_effects,
                has_multiline=has_multiline,
                font_availability=font_availability,
                confidence=0.9,
                estimated_quality=0.98,
                estimated_performance=0.95
            )
            self._current_decision = decision
            return decision

        # Ultimate fallback strategy - always succeeds
        reasons.append(DecisionReason.FALLBACK_STRATEGY_REQUIRED)
        if has_missing_fonts:
            reasons.append(DecisionReason.FONT_UNAVAILABLE)
        if complexity_analysis.get('all_strategies_failed', False):
            reasons.append(DecisionReason.ALL_STRATEGIES_FAILED)

        decision = TextDecision.fallback(
            reasons=reasons,
            run_count=run_count,
            complexity_score=complexity_score,
            has_missing_fonts=has_missing_fonts,
            has_effects=has_effects,
            has_multiline=has_multiline,
            font_availability=font_availability,
            fallback_reason="No other strategy suitable",
            confidence=0.5,
            estimated_quality=0.7,
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

    def _analyze_image(self, image: Image, already_embedded: set = None) -> ImageDecision:
        """
        Analyze image and make policy decision.

        Args:
            image: Image IR element
            already_embedded: Set of SHA-256 checksums already embedded

        Returns:
            ImageDecision with embedding strategy
        """
        reasons = []
        already_embedded = already_embedded or set()

        # Get image data and calculate size
        image_data = image.image_data or image.data  # Support both new and legacy fields
        size_bytes = len(image_data) if image_data else 0
        format_ext = image.format_ext or image.format  # Support both new and legacy fields

        # Check deduplication
        if image.sha256 and image.sha256 in already_embedded:
            reasons.append(DecisionReason.IMAGE_ALREADY_EMBEDDED)
            return ImageDecision.native(
                reasons=reasons,
                format=format_ext,
                size_bytes=size_bytes,
                confidence=1.0,
                estimated_quality=1.0,
                estimated_performance=1.0
            )

        # Check format support
        supported_formats = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tif', 'tiff', 'webp'}
        if format_ext and format_ext.lower() not in supported_formats:
            reasons.append(DecisionReason.UNSUPPORTED_FEATURES)
            decision = ImageDecision.emf(
                reasons=reasons,
                format=format_ext,
                size_bytes=size_bytes,
                confidence=0.9,
                estimated_quality=0.95,
                estimated_performance=0.8
            )
            self._current_decision = decision
            return decision

        # Check external URLs
        if hasattr(image, 'source_type') and image.source_type in ('http', 'https'):
            if hasattr(self.config, 'allow_external_images') and self.config.allow_external_images:
                reasons.append(DecisionReason.IMAGE_EXTERNAL_URL)
                decision = ImageDecision.external(
                    reasons=reasons,
                    format=format_ext,
                    size_bytes=size_bytes,
                    confidence=0.8,
                    estimated_quality=0.7,  # External may not load
                    estimated_performance=0.5  # Network dependency
                )
                self._current_decision = decision
                return decision
            else:
                # Fetch and embed
                reasons.append(DecisionReason.IMAGE_FORMAT_SUPPORTED)

        # Check size limits
        if image_data:
            size_mb = size_bytes / (1024 * 1024)
            max_size = getattr(self.config, 'max_image_size_mb', 10.0)
            max_dim = getattr(self.config, 'max_image_dimension', 4096)

            if size_mb > max_size:
                reasons.append(DecisionReason.IMAGE_SIZE_TOO_LARGE)
                decision = ImageDecision.native(
                    reasons=reasons,
                    format=format_ext,
                    size_bytes=size_bytes,
                    compress=True,
                    max_dimension=max_dim,
                    confidence=0.85,
                    estimated_quality=0.9,  # Compression may reduce quality
                    estimated_performance=0.7  # Compression takes time
                )
                self._current_decision = decision
                return decision

        # Default: embed inline
        reasons.append(DecisionReason.IMAGE_FORMAT_SUPPORTED)
        reasons.append(DecisionReason.IMAGE_SIZE_OK)

        decision = ImageDecision.native(
            reasons=reasons,
            format=format_ext,
            size_bytes=size_bytes,
            confidence=0.95,
            estimated_quality=1.0,
            estimated_performance=0.95
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

    def decide_svg_switch_conditions(self, required_features: Optional[str] = None,
                                   system_language: Optional[str] = None,
                                   required_extensions: Optional[str] = None) -> PolicyDecision:
        """
        Decide if SVG switch conditions can be satisfied in PowerPoint conversion.

        Args:
            required_features: Space-separated list of required SVG features
            system_language: Comma-separated list of language preferences
            required_extensions: Space-separated list of required extensions

        Returns:
            PolicyDecision indicating if conditions can be met
        """
        reasons = []
        can_satisfy = True
        confidence = 1.0

        # Evaluate required features
        if required_features:
            supported_features = {
                # Core SVG features we support well
                'http://www.w3.org/TR/SVG11/feature#BasicStructure',
                'http://www.w3.org/TR/SVG11/feature#Shape',
                'http://www.w3.org/TR/SVG11/feature#BasicPaintAttribute',
                'http://www.w3.org/TR/SVG11/feature#BasicGraphicsAttribute',
                'http://www.w3.org/TR/SVG11/feature#Marker',
                'http://www.w3.org/TR/SVG11/feature#BasicText',
                'http://www.w3.org/TR/SVG11/feature#Text',

                # Simplified feature names
                'BasicStructure', 'Shape', 'BasicPaintAttribute',
                'BasicGraphicsAttribute', 'Marker', 'Transform',
                'BasicText', 'Text'
            }

            feature_list = required_features.strip().split()
            unsupported_features = [f for f in feature_list if f not in supported_features]

            if unsupported_features:
                can_satisfy = False
                reasons.append(DecisionReason.UNSUPPORTED_FEATURES)
                confidence *= 0.1  # Very low confidence
                self.logger.debug(f"Unsupported SVG features: {unsupported_features}")
            else:
                reasons.append(DecisionReason.SUPPORTED_FEATURES)
                self.logger.debug(f"All SVG features supported: {feature_list}")

        # Evaluate system language (PowerPoint supports international content)
        if system_language:
            reasons.append(DecisionReason.SUPPORTED_FEATURES)
            self.logger.debug(f"System language accepted: {system_language}")

        # Evaluate required extensions with mimicking capability
        if required_extensions:
            mimickable_extensions = {
                # Animation extensions - PowerPoint has animation capabilities
                'http://www.w3.org/2001/svg-animation', 'svg-animation', 'animation',
                # Interactivity extensions - PowerPoint has hyperlinks/actions
                'http://www.w3.org/2001/svg-interactivity', 'svg-interactivity', 'interactivity',
                # Font extensions - PowerPoint has font embedding
                'http://www.w3.org/2001/svg-fonts', 'svg-fonts', 'fonts',
                # Filter extensions - We have filter system
                'http://www.w3.org/2001/svg-filter-effects', 'svg-filter-effects', 'filter-effects',
                # Transform extensions - PowerPoint has transform capabilities
                'http://www.w3.org/2001/svg-transform', 'svg-transform', 'transform',
                # 3D extensions - PowerPoint has 3D effects
                'http://www.w3.org/2001/svg-3d', 'svg-3d', '3d',
                # Multimedia extensions - PowerPoint supports multimedia
                'http://www.w3.org/2001/svg-multimedia', 'svg-multimedia', 'multimedia',
            }

            extension_list = required_extensions.strip().split()
            mimickable = [e for e in extension_list if e in mimickable_extensions]
            non_mimickable = [e for e in extension_list if e not in mimickable_extensions]

            # Use policy-based decision for extensions
            if self.config.target == OutputTarget.QUALITY:
                # Quality mode: accept if we can mimic all extensions
                if non_mimickable:
                    can_satisfy = False
                    reasons.append(DecisionReason.UNSUPPORTED_FEATURES)
                    confidence *= 0.3
                else:
                    reasons.append(DecisionReason.SUPPORTED_FEATURES)
            elif self.config.target == OutputTarget.BALANCED:
                # Balanced mode: accept if we can mimic majority
                if len(mimickable) > len(non_mimickable):
                    reasons.append(DecisionReason.SUPPORTED_FEATURES)
                    confidence *= 0.8  # Some uncertainty due to partial support
                else:
                    can_satisfy = False
                    reasons.append(DecisionReason.UNSUPPORTED_FEATURES)
                    confidence *= 0.4
            elif self.config.target == OutputTarget.SPEED:
                # Speed mode: more permissive, accept if any can be mimicked
                if mimickable:
                    reasons.append(DecisionReason.SUPPORTED_FEATURES)
                    confidence *= 0.7
                else:
                    can_satisfy = False
                    reasons.append(DecisionReason.UNSUPPORTED_FEATURES)
                    confidence *= 0.2
            else:  # COMPATIBILITY mode
                # Compatibility mode: conservative, need strong support
                if len(mimickable) >= len(non_mimickable) and len(mimickable) > 0:
                    reasons.append(DecisionReason.SUPPORTED_FEATURES)
                    confidence *= 0.9
                else:
                    can_satisfy = False
                    reasons.append(DecisionReason.COMPATIBILITY_MODE)
                    confidence *= 0.1

            self.logger.debug(f"Extensions - mimickable: {mimickable}, non-mimickable: {non_mimickable}")

        # Default case - no conditions specified means always supported
        if not any([required_features, system_language, required_extensions]):
            reasons.append(DecisionReason.SUPPORTED_FEATURES)

        return PolicyDecision(
            use_native=can_satisfy,
            reasons=reasons,
            confidence=confidence,
            fallback_available=True,
            estimated_quality=0.95 if can_satisfy else 0.3,
            estimated_performance=0.9
        )

    def decide_filter_strategy(self, filter_type: str, complexity: float = 0.0,
                              input_count: int = 1, has_blending: bool = False) -> PolicyDecision:
        """
        Decide rendering strategy for SVG filter effects.

        Args:
            filter_type: Type of filter (e.g., 'merge', 'blend', 'composite')
            complexity: Complexity score (0.0 to 1.0)
            input_count: Number of input buffers
            has_blending: Whether filter uses advanced blending modes

        Returns:
            PolicyDecision with recommended strategy
        """
        reasons = []
        use_native = True
        confidence = 0.8

        # Simple filters always use native
        simple_filters = {'blur', 'shadow', 'glow', 'reflection'}
        if filter_type.lower() in simple_filters:
            reasons.append(DecisionReason.SIMPLE_CONTENT)
            return PolicyDecision(
                use_native=True,
                reasons=reasons,
                confidence=0.95,
                estimated_quality=0.95,
                estimated_performance=0.9
            )

        # Complex decision based on output target
        if self.config.output_target == OutputTarget.QUALITY:
            # Quality mode: prefer native unless impossible
            if has_blending and complexity > 0.8:
                use_native = False
                reasons.append(DecisionReason.COMPLEX_CONTENT)
                confidence = 0.6
            else:
                reasons.append(DecisionReason.QUALITY_PRIORITY)
                confidence = 0.9

        elif self.config.output_target == OutputTarget.SPEED:
            # Speed mode: flatten complex filters
            if input_count > 3 or complexity > 0.5:
                use_native = True  # But simplified
                reasons.append(DecisionReason.PERFORMANCE_PRIORITY)
                confidence = 0.7
            else:
                reasons.append(DecisionReason.SIMPLE_CONTENT)

        elif self.config.output_target == OutputTarget.COMPATIBILITY:
            # Compatibility mode: EMF for complex filters
            if complexity > 0.6 or has_blending:
                use_native = False
                reasons.append(DecisionReason.COMPATIBILITY_MODE)
                confidence = 0.5
            else:
                reasons.append(DecisionReason.SUPPORTED_FEATURES)

        else:  # BALANCED
            # Smart decision based on complexity
            if complexity < 0.4 and input_count <= 3:
                reasons.append(DecisionReason.SIMPLE_CONTENT)
            elif complexity > 0.7 or (has_blending and input_count > 2):
                use_native = False
                reasons.append(DecisionReason.COMPLEX_CONTENT)
                confidence = 0.6
            else:
                reasons.append(DecisionReason.BALANCED_MODE)
                confidence = 0.75

        # Log decision if configured
        if self.config.log_decisions:
            self.logger.debug(
                f"Filter strategy for {filter_type}: native={use_native} "
                f"(complexity={complexity:.2f}, inputs={input_count}, blending={has_blending})"
            )

        return PolicyDecision(
            use_native=use_native,
            reasons=reasons,
            confidence=confidence,
            fallback_available=True,
            estimated_quality=0.9 if use_native else 0.7,
            estimated_performance=0.8 if input_count <= 3 else 0.5
        )

    def decide_font_embedding(self, font_family: str, font_size_bytes: int,
                             sha1_checksum: str, already_embedded: set) -> FontEmbeddingDecision:
        """
        Decide whether to embed a custom font.

        Args:
            font_family: Font family name
            font_size_bytes: Font file size in bytes
            sha1_checksum: SHA-1 checksum for deduplication
            already_embedded: Set of SHA-1 checksums already embedded

        Returns:
            FontEmbeddingDecision with reasoning
        """
        reasons = []

        # Check if already embedded (deduplication)
        if sha1_checksum in already_embedded:
            reasons.append(DecisionReason.FONT_ALREADY_EMBEDDED)
            return FontEmbeddingDecision.skip(
                reasons=reasons,
                font_family=font_family,
                font_size_bytes=font_size_bytes,
                sha1_checksum=sha1_checksum
            )

        # Check embedding configuration
        if not self.config.enable_font_embedding:
            reasons.append(DecisionReason.EMBEDDING_DISABLED)
            return FontEmbeddingDecision.skip(
                reasons=reasons,
                font_family=font_family,
                font_size_bytes=font_size_bytes,
                sha1_checksum=sha1_checksum
            )

        # Check size limit (10MB default)
        max_size_bytes = getattr(self.config, 'max_font_size_mb', 10.0) * 1024 * 1024
        if font_size_bytes > max_size_bytes:
            reasons.append(DecisionReason.FONT_SIZE_LIMIT_EXCEEDED)
            return FontEmbeddingDecision.skip(
                reasons=reasons,
                font_family=font_family,
                font_size_bytes=font_size_bytes,
                sha1_checksum=sha1_checksum
            )

        # Embed custom font
        reasons.append(DecisionReason.CUSTOM_FONT_REQUIRED)
        return FontEmbeddingDecision.embed(
            reasons=reasons,
            font_family=font_family,
            font_size_bytes=font_size_bytes,
            sha1_checksum=sha1_checksum
        )

    def _analyze_font_availability(self, text: TextFrame) -> Dict[str, bool]:
        """
        Analyze font availability for all runs in text frame.

        Args:
            text: TextFrame to analyze

        Returns:
            Dictionary mapping font families to availability status
        """
        font_availability = {}

        for run in text.runs:
            font_family = getattr(run, 'font_family', 'Arial')
            if font_family not in font_availability:
                # TODO: Integrate with font service for real availability check
                # For now, assume common fonts are available
                common_fonts = {'Arial', 'Times New Roman', 'Calibri', 'Helvetica', 'Times'}
                font_availability[font_family] = font_family in common_fonts

        return font_availability

    def _analyze_text_complexity_for_strategy(self, text: TextFrame) -> Dict[str, Any]:
        """
        Analyze text complexity to determine optimal font strategy.

        Args:
            text: TextFrame to analyze

        Returns:
            Dictionary with complexity analysis results
        """
        analysis = {
            'requires_path_conversion': False,
            'system_font_suitable': True,
            'should_embed_fonts': False,
            'requires_embedding': False,
            'too_complex_for_wordart': False,
            'complex_transforms': False,
            'all_strategies_failed': False
        }

        # Check transforms
        if hasattr(text, 'transform') and text.transform is not None:
            transform_analysis = self._analyze_transform_complexity(text)
            if transform_analysis:
                # Very complex transforms require path conversion
                if (transform_analysis.get('max_skew_exceeded', False) or
                    transform_analysis.get('scale_ratio_exceeded', False)):
                    analysis['requires_path_conversion'] = True
                    analysis['complex_transforms'] = True
                    analysis['too_complex_for_wordart'] = True
                    analysis['system_font_suitable'] = False

        # Check text effects complexity
        has_complex_effects = False
        for run in text.runs:
            if hasattr(run, 'has_decoration') and run.has_decoration:
                # Check for complex decorations
                if hasattr(run, 'text_shadow') and run.text_shadow:
                    has_complex_effects = True
                if hasattr(run, 'text_outline') and run.text_outline:
                    has_complex_effects = True

        if has_complex_effects:
            analysis['requires_path_conversion'] = True
            analysis['system_font_suitable'] = False

        # Check font availability and embedding needs
        font_availability = self._analyze_font_availability(text)
        missing_fonts = [font for font, available in font_availability.items() if not available]

        if missing_fonts:
            # Missing fonts - need embedding or fallback
            analysis['should_embed_fonts'] = True
            if len(missing_fonts) == len(font_availability):
                # All fonts missing - might need path conversion or fallback
                analysis['requires_embedding'] = True
                analysis['system_font_suitable'] = False

        # Check text complexity score
        if hasattr(text, 'complexity_score'):
            if text.complexity_score > self.config.thresholds.max_text_complexity_score:
                analysis['too_complex_for_wordart'] = True
                if text.complexity_score > self.config.thresholds.max_text_complexity_score * 1.5:
                    analysis['requires_path_conversion'] = True
                    analysis['system_font_suitable'] = False

        # Check run count
        if len(text.runs) > self.config.thresholds.max_text_runs:
            analysis['too_complex_for_wordart'] = True
            analysis['system_font_suitable'] = False

        return analysis


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