#!/usr/bin/env python3
"""
Policy decision types and results

Defines the output types and decision structures used by the policy engine.
Provides clear reasoning for all policy decisions.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class DecisionReason(Enum):
    """Reasons for policy decisions"""

    # Native DML reasons
    SIMPLE_GEOMETRY = "simple_geometry"
    SUPPORTED_FEATURES = "supported_features"
    PERFORMANCE_OK = "performance_ok"
    FONT_AVAILABLE = "font_available"
    BELOW_THRESHOLDS = "below_thresholds"
    WORDART_PATTERN_DETECTED = "wordart_pattern_detected"
    NATIVE_PRESET_AVAILABLE = "native_preset_available"

    # EMF fallback reasons
    COMPLEX_GEOMETRY = "complex_geometry"
    UNSUPPORTED_FEATURES = "unsupported_features"
    PERFORMANCE_LIMIT = "performance_limit"
    FONT_UNAVAILABLE = "font_unavailable"
    ABOVE_THRESHOLDS = "above_thresholds"
    CLIPPING_COMPLEX = "clipping_complex"
    GRADIENT_COMPLEX = "gradient_complex"
    STROKE_COMPLEX = "stroke_complex"
    TEXT_EFFECTS_COMPLEX = "text_effects_complex"
    COMPLEX_TRANSFORM = "complex_transform"

    # Conservative reasons
    CONSERVATIVE_MODE = "conservative_mode"
    COMPATIBILITY_MODE = "compatibility_mode"
    USER_PREFERENCE = "user_preference"

    # Filter reasons
    SIMPLE_FILTER = "simple_filter"
    NATIVE_FILTER_AVAILABLE = "native_filter_available"
    FILTER_CHAIN_COMPLEX = "filter_chain_complex"
    UNSUPPORTED_FILTER_PRIMITIVE = "unsupported_filter_primitive"
    FILTER_RASTERIZED = "filter_rasterized"

    # Gradient reasons
    SIMPLE_GRADIENT = "simple_gradient"
    GRADIENT_SIMPLIFIED = "gradient_simplified"
    GRADIENT_TRANSFORM_COMPLEX = "gradient_transform_complex"
    MESH_GRADIENT_COMPLEX = "mesh_gradient_complex"
    TOO_MANY_GRADIENT_STOPS = "too_many_gradient_stops"

    # Multi-page reasons
    EXPLICIT_PAGE_MARKERS = "explicit_page_markers"
    GROUPED_CONTENT_DETECTED = "grouped_content_detected"
    SIZE_THRESHOLD_EXCEEDED = "size_threshold_exceeded"
    SINGLE_PAGE_ONLY = "single_page_only"
    PAGE_LIMIT_EXCEEDED = "page_limit_exceeded"

    # Animation reasons
    SIMPLE_ANIMATION = "simple_animation"
    ANIMATION_TOO_COMPLEX = "animation_too_complex"
    UNSUPPORTED_ANIMATION_TYPE = "unsupported_animation_type"
    ANIMATION_SKIPPED = "animation_skipped"

    # Clipping reasons
    SIMPLE_CLIP_PATH = "simple_clip_path"
    CLIP_PATH_COMPLEX = "clip_path_complex"
    NESTED_CLIPPING = "nested_clipping"
    BOOLEAN_CLIP_OPERATION = "boolean_clip_operation"


@dataclass(frozen=True)
class PolicyDecision:
    """Base policy decision"""
    use_native: bool
    reasons: list[DecisionReason]
    confidence: float = 1.0  # 0.0 to 1.0
    fallback_available: bool = True
    estimated_quality: float = 1.0  # 0.0 to 1.0
    estimated_performance: float = 1.0  # 0.0 to 1.0 (higher = faster)

    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")
        if not (0.0 <= self.estimated_quality <= 1.0):
            raise ValueError(f"Quality must be 0.0-1.0, got {self.estimated_quality}")
        if not (0.0 <= self.estimated_performance <= 1.0):
            raise ValueError(f"Performance must be 0.0-1.0, got {self.estimated_performance}")

    @property
    def output_format(self) -> str:
        """Get target output format"""
        return "DrawingML" if self.use_native else "EMF"

    @property
    def primary_reason(self) -> DecisionReason:
        """Get primary reason for decision"""
        return self.reasons[0] if self.reasons else DecisionReason.USER_PREFERENCE

    def explain(self) -> str:
        """Human-readable explanation of decision"""
        format_name = self.output_format
        primary = self.primary_reason.value.replace('_', ' ')
        confidence_pct = int(self.confidence * 100)

        explanation = f"Using {format_name} (confidence: {confidence_pct}%)"

        if len(self.reasons) == 1:
            explanation += f" - {primary}"
        else:
            [r.value.replace('_', ' ') for r in self.reasons]
            explanation += f" - {primary} + {len(self.reasons)-1} other factors"

        return explanation

    def to_dict(self) -> dict[str, Any]:
        """Serialize decision to dictionary for tracing"""
        return {
            'use_native': self.use_native,
            'output_format': self.output_format,
            'reasons': [r.value for r in self.reasons],
            'confidence': self.confidence,
            'fallback_available': self.fallback_available,
            'estimated_quality': self.estimated_quality,
            'estimated_performance': self.estimated_performance,
            'primary_reason': self.primary_reason.value,
        }


@dataclass(frozen=True)
class PathDecision(PolicyDecision):
    """Policy decision for Path elements"""
    segment_count: int = 0
    complexity_score: int = 0
    has_clipping: bool = False
    has_complex_stroke: bool = False
    has_complex_fill: bool = False

    @classmethod
    def native(cls, reasons: list[DecisionReason], **kwargs) -> 'PathDecision':
        """Create decision for native DrawingML"""
        return cls(use_native=True, reasons=reasons, **kwargs)

    @classmethod
    def emf(cls, reasons: list[DecisionReason], **kwargs) -> 'PathDecision':
        """Create decision for EMF fallback"""
        return cls(use_native=False, reasons=reasons, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Serialize PathDecision to dictionary for tracing"""
        base_dict = super().to_dict()
        base_dict.update({
            'segment_count': self.segment_count,
            'complexity_score': self.complexity_score,
            'has_clipping': self.has_clipping,
            'has_complex_stroke': self.has_complex_stroke,
            'has_complex_fill': self.has_complex_fill,
        })
        return base_dict


@dataclass(frozen=True)
class TextDecision(PolicyDecision):
    """Policy decision for TextFrame elements"""
    run_count: int = 0
    complexity_score: int = 0
    has_missing_fonts: bool = False
    has_effects: bool = False
    has_multiline: bool = False

    # WordArt detection
    wordart_preset: str | None = None
    wordart_parameters: dict[str, Any] | None = None
    wordart_confidence: float = 0.0
    transform_complexity: dict[str, Any] | None = None

    # Font strategy (Three-Tier: ADR-003)
    font_strategy: str | None = None  # 'embedded' | 'system' | 'text_to_path'
    font_match_confidence: float = 0.0   # Confidence in font matching (Tier 2)
    embedded_font_name: str | None = None  # Name of embedded font (Tier 1)
    system_font_fallback: str | None = None  # System font used (Tier 2)

    @classmethod
    def native(cls, reasons: list[DecisionReason], **kwargs) -> 'TextDecision':
        """Create decision for native DrawingML"""
        return cls(use_native=True, reasons=reasons, **kwargs)

    @classmethod
    def emf(cls, reasons: list[DecisionReason], **kwargs) -> 'TextDecision':
        """Create decision for EMF fallback"""
        return cls(use_native=False, reasons=reasons, **kwargs)

    @classmethod
    def wordart(cls, preset: str, parameters: dict[str, Any], confidence: float,
                reasons: list[DecisionReason] = None, **kwargs) -> 'TextDecision':
        """Create decision for WordArt preset"""
        if reasons is None:
            reasons = [DecisionReason.WORDART_PATTERN_DETECTED, DecisionReason.NATIVE_PRESET_AVAILABLE]

        return cls(
            use_native=True,
            reasons=reasons,
            wordart_preset=preset,
            wordart_parameters=parameters,
            wordart_confidence=confidence,
            **kwargs,
        )

    @property
    def is_wordart(self) -> bool:
        """Check if this is a WordArt decision"""
        return self.wordart_preset is not None

    @property
    def output_format(self) -> str:
        """Get target output format"""
        if self.is_wordart:
            return f"WordArt({self.wordart_preset})"
        return "DrawingML" if self.use_native else "EMF"

    def to_dict(self) -> dict[str, Any]:
        """Serialize TextDecision to dictionary for tracing"""
        base_dict = super().to_dict()
        base_dict.update({
            'run_count': self.run_count,
            'complexity_score': self.complexity_score,
            'has_missing_fonts': self.has_missing_fonts,
            'has_effects': self.has_effects,
            'has_multiline': self.has_multiline,
            'wordart_preset': self.wordart_preset,
            'wordart_parameters': self.wordart_parameters,
            'wordart_confidence': self.wordart_confidence,
            'transform_complexity': self.transform_complexity,
            'is_wordart': self.is_wordart,
            'font_strategy': self.font_strategy,
            'font_match_confidence': self.font_match_confidence,
            'embedded_font_name': self.embedded_font_name,
            'system_font_fallback': self.system_font_fallback,
        })
        return base_dict


@dataclass(frozen=True)
class GroupDecision(PolicyDecision):
    """Policy decision for Group elements"""
    element_count: int = 0
    nesting_depth: int = 0
    should_flatten: bool = False
    has_complex_clipping: bool = False

    @classmethod
    def native(cls, reasons: list[DecisionReason], **kwargs) -> 'GroupDecision':
        """Create decision for native DrawingML"""
        return cls(use_native=True, reasons=reasons, **kwargs)

    @classmethod
    def emf(cls, reasons: list[DecisionReason], **kwargs) -> 'GroupDecision':
        """Create decision for EMF fallback"""
        return cls(use_native=False, reasons=reasons, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Serialize GroupDecision to dictionary for tracing"""
        base_dict = super().to_dict()
        base_dict.update({
            'element_count': self.element_count,
            'nesting_depth': self.nesting_depth,
            'should_flatten': self.should_flatten,
            'has_complex_clipping': self.has_complex_clipping,
        })
        return base_dict


@dataclass(frozen=True)
class ImageDecision(PolicyDecision):
    """Policy decision for Image elements"""
    format: str = ""
    size_bytes: int = 0
    has_transparency: bool = False

    @classmethod
    def native(cls, reasons: list[DecisionReason], **kwargs) -> 'ImageDecision':
        """Create decision for native DrawingML"""
        return cls(use_native=True, reasons=reasons, **kwargs)

    @classmethod
    def emf(cls, reasons: list[DecisionReason], **kwargs) -> 'ImageDecision':
        """Create decision for EMF fallback"""
        return cls(use_native=False, reasons=reasons, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Serialize ImageDecision to dictionary for tracing"""
        base_dict = super().to_dict()
        base_dict.update({
            'format': self.format,
            'size_bytes': self.size_bytes,
            'has_transparency': self.has_transparency,
        })
        return base_dict


@dataclass(frozen=True)
class FilterDecision(PolicyDecision):
    """Policy decision for SVG filter elements (parsing layer)

    Decides how to handle SVG <filter> elements with filter primitives
    (feGaussianBlur, feDropShadow, etc.). Determines strategy:
    - Native: Convert SVG filter chain to DrawingML effects (then use EffectDecision)
    - EMF: Render filter to EMF
    - Rasterize: Render filter to image

    This is the SVG→IR decision. For IR→DrawingML governance, see EffectDecision.
    """
    filter_type: str = ""           # 'blur' | 'shadow' | 'color_matrix' | 'composite' | 'chain'
    primitive_count: int = 0        # Number of filter primitives in chain
    complexity_score: int = 0       # Calculated complexity (0-100)
    has_unsupported_primitives: bool = False
    native_approximation: str | None = None  # DrawingML equivalent if available

    # Rendering strategy
    use_native_effects: bool = False   # Use DrawingML effects
    use_emf_fallback: bool = False     # Render to EMF
    use_rasterization: bool = False    # Rasterize to image

    @classmethod
    def native(cls, filter_type: str, reasons: list[DecisionReason] = None, **kwargs) -> 'FilterDecision':
        """Create decision for native DrawingML effects"""
        if reasons is None:
            reasons = [DecisionReason.NATIVE_FILTER_AVAILABLE]
        return cls(use_native=True, filter_type=filter_type,
                   use_native_effects=True, reasons=reasons, **kwargs)

    @classmethod
    def emf(cls, filter_type: str, reasons: list[DecisionReason] = None, **kwargs) -> 'FilterDecision':
        """Create decision for EMF fallback"""
        if reasons is None:
            reasons = [DecisionReason.FILTER_CHAIN_COMPLEX]
        return cls(use_native=False, filter_type=filter_type,
                   use_emf_fallback=True, reasons=reasons, **kwargs)

    @classmethod
    def rasterize(cls, filter_type: str, reasons: list[DecisionReason] = None, **kwargs) -> 'FilterDecision':
        """Create decision for rasterization"""
        if reasons is None:
            reasons = [DecisionReason.FILTER_RASTERIZED]
        return cls(use_native=False, filter_type=filter_type,
                   use_rasterization=True, reasons=reasons, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Serialize FilterDecision to dictionary for tracing"""
        base_dict = super().to_dict()
        base_dict.update({
            'filter_type': self.filter_type,
            'primitive_count': self.primitive_count,
            'complexity_score': self.complexity_score,
            'has_unsupported_primitives': self.has_unsupported_primitives,
            'native_approximation': self.native_approximation,
            'use_native_effects': self.use_native_effects,
            'use_emf_fallback': self.use_emf_fallback,
            'use_rasterization': self.use_rasterization,
        })
        return base_dict


@dataclass(frozen=True)
class GradientDecision(PolicyDecision):
    """Policy decision for gradient fills"""
    gradient_type: str = ""         # 'linear' | 'radial' | 'mesh' | 'conic'
    stop_count: int = 0             # Number of gradient stops
    has_complex_transform: bool = False
    has_color_interpolation: bool = False
    color_space: str = "sRGB"       # 'sRGB' | 'linearRGB' | 'lab'

    # Mesh gradient specific
    mesh_rows: int = 0
    mesh_cols: int = 0
    mesh_patch_count: int = 0

    # Rendering strategy
    use_simplified_gradient: bool = False  # Reduce stops
    use_approximation: bool = False        # Approximate complex gradients

    @classmethod
    def native(cls, gradient_type: str, reasons: list[DecisionReason] = None, **kwargs) -> 'GradientDecision':
        """Create decision for native DrawingML gradient"""
        if reasons is None:
            reasons = [DecisionReason.SIMPLE_GRADIENT]
        return cls(use_native=True, gradient_type=gradient_type, reasons=reasons, **kwargs)

    @classmethod
    def simplified(cls, gradient_type: str, reasons: list[DecisionReason] = None, **kwargs) -> 'GradientDecision':
        """Create decision for simplified gradient (reduce stops)"""
        if reasons is None:
            reasons = [DecisionReason.GRADIENT_SIMPLIFIED, DecisionReason.TOO_MANY_GRADIENT_STOPS]
        return cls(use_native=True, gradient_type=gradient_type,
                   use_simplified_gradient=True, reasons=reasons, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Serialize GradientDecision to dictionary for tracing"""
        base_dict = super().to_dict()
        base_dict.update({
            'gradient_type': self.gradient_type,
            'stop_count': self.stop_count,
            'has_complex_transform': self.has_complex_transform,
            'has_color_interpolation': self.has_color_interpolation,
            'color_space': self.color_space,
            'mesh_rows': self.mesh_rows,
            'mesh_cols': self.mesh_cols,
            'mesh_patch_count': self.mesh_patch_count,
            'use_simplified_gradient': self.use_simplified_gradient,
            'use_approximation': self.use_approximation,
        })
        return base_dict


@dataclass(frozen=True)
class MultiPageDecision(PolicyDecision):
    """Policy decision for multi-page SVG handling"""
    page_count: int = 1
    detection_method: str = "none"  # 'markers' | 'grouped' | 'size_split' | 'none'
    total_size_bytes: int = 0
    elements_per_page: list[int] | None = None
    page_titles: list[str | None] | None = None

    # Split decision
    should_split: bool = False
    split_threshold_exceeded: bool = False

    @classmethod
    def single_page(cls, reasons: list[DecisionReason] = None, **kwargs) -> 'MultiPageDecision':
        """Create decision for no splitting needed"""
        if reasons is None:
            reasons = [DecisionReason.SINGLE_PAGE_ONLY]
        return cls(use_native=True, page_count=1,
                   detection_method="none", reasons=reasons, **kwargs)

    @classmethod
    def multi_page(cls, page_count: int, method: str, reasons: list[DecisionReason] = None, **kwargs) -> 'MultiPageDecision':
        """Create decision for split into multiple pages"""
        if reasons is None:
            reasons = [DecisionReason.EXPLICIT_PAGE_MARKERS]
        return cls(use_native=True, page_count=page_count,
                   detection_method=method, should_split=True, reasons=reasons, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Serialize MultiPageDecision to dictionary for tracing"""
        base_dict = super().to_dict()
        base_dict.update({
            'page_count': self.page_count,
            'detection_method': self.detection_method,
            'total_size_bytes': self.total_size_bytes,
            'elements_per_page': self.elements_per_page,
            'page_titles': self.page_titles,
            'should_split': self.should_split,
            'split_threshold_exceeded': self.split_threshold_exceeded,
        })
        return base_dict


@dataclass(frozen=True)
class AnimationDecision(PolicyDecision):
    """Policy decision for SVG animations"""
    animation_type: str = ""        # 'transform' | 'opacity' | 'color' | 'path' | 'sequence'
    keyframe_count: int = 0
    duration_ms: float = 0.0
    has_complex_timing: bool = False
    interpolation: str = "linear"   # 'linear' | 'ease' | 'cubic-bezier'

    # Rendering strategy
    convert_to_pptx_animation: bool = False
    export_as_video: bool = False
    skip_animation: bool = False

    @classmethod
    def native(cls, animation_type: str, reasons: list[DecisionReason] = None, **kwargs) -> 'AnimationDecision':
        """Create decision for converting to PowerPoint animation"""
        if reasons is None:
            reasons = [DecisionReason.SIMPLE_ANIMATION]
        return cls(use_native=True, animation_type=animation_type,
                   convert_to_pptx_animation=True, reasons=reasons, **kwargs)

    @classmethod
    def skip(cls, animation_type: str, reasons: list[DecisionReason] = None, **kwargs) -> 'AnimationDecision':
        """Create decision for skipping animation"""
        if reasons is None:
            reasons = [DecisionReason.ANIMATION_SKIPPED]
        return cls(use_native=False, animation_type=animation_type,
                   skip_animation=True, reasons=reasons, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Serialize AnimationDecision to dictionary for tracing"""
        base_dict = super().to_dict()
        base_dict.update({
            'animation_type': self.animation_type,
            'keyframe_count': self.keyframe_count,
            'duration_ms': self.duration_ms,
            'has_complex_timing': self.has_complex_timing,
            'interpolation': self.interpolation,
            'convert_to_pptx_animation': self.convert_to_pptx_animation,
            'export_as_video': self.export_as_video,
            'skip_animation': self.skip_animation,
        })
        return base_dict


@dataclass(frozen=True)
class ClipPathDecision(PolicyDecision):
    """Policy decision for clipping paths"""
    clip_type: str = ""             # 'rect' | 'ellipse' | 'path' | 'complex' | 'boolean'
    path_complexity: int = 0        # Path segment count
    nesting_level: int = 0          # Nested clip depth
    has_boolean_ops: bool = False   # Union, intersection, etc.
    boolean_op_type: str | None = None  # 'union' | 'intersect' | 'subtract'

    # Rendering strategy
    use_native_clipping: bool = False
    use_boolean_approximation: bool = False

    @classmethod
    def native(cls, clip_type: str, reasons: list[DecisionReason] = None, **kwargs) -> 'ClipPathDecision':
        """Create decision for native DrawingML clipping"""
        if reasons is None:
            reasons = [DecisionReason.SIMPLE_CLIP_PATH]
        return cls(use_native=True, clip_type=clip_type,
                   use_native_clipping=True, reasons=reasons, **kwargs)

    @classmethod
    def emf(cls, clip_type: str, reasons: list[DecisionReason] = None, **kwargs) -> 'ClipPathDecision':
        """Create decision for EMF fallback"""
        if reasons is None:
            reasons = [DecisionReason.CLIP_PATH_COMPLEX]
        return cls(use_native=False, clip_type=clip_type, reasons=reasons, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Serialize ClipPathDecision to dictionary for tracing"""
        base_dict = super().to_dict()
        base_dict.update({
            'clip_type': self.clip_type,
            'path_complexity': self.path_complexity,
            'nesting_level': self.nesting_level,
            'has_boolean_ops': self.has_boolean_ops,
            'boolean_op_type': self.boolean_op_type,
            'use_native_clipping': self.use_native_clipping,
            'use_boolean_approximation': self.use_boolean_approximation,
        })
        return base_dict


@dataclass(frozen=True)
class EffectDecision(PolicyDecision):
    """Policy decision for DrawingML effect IR objects (rendering layer)

    Decides whether to allow, clamp, downgrade, or drop individual Effect IR objects
    (BlurEffect, ShadowEffect, etc.) when generating DrawingML output.

    This is the IR→DrawingML governance layer. For SVG→IR decisions, see FilterDecision.

    Policy rules applied:
    - Effect type and caps (blur/shadow radius, distance, alpha limits)
    - Color governance (sRGB vs scheme colors)
    - Shape context (text vs shapes, logo restrictions)
    - Performance budgets (effects per shape, per slide)
    """
    effect_type: str = ""                    # 'blur' | 'shadow' | 'glow' | 'soft_edge' | 'reflection'
    action: str = "allow"                    # 'allow' | 'clamp' | 'downgrade' | 'drop' | 'rasterize'
    original_effect: Any = None              # Original effect before policy
    modified_effect: Any = None              # Clamped/downgraded effect (if action != 'allow')
    violation_reason: str | None = None      # Why effect was modified/dropped

    # Caps applied
    clamped_blur: bool = False
    clamped_distance: bool = False
    clamped_alpha: bool = False
    color_downgraded: bool = False           # sRGB → scheme

    @classmethod
    def allow(cls, effect: Any, effect_type: str, reasons: list[DecisionReason] = None) -> 'EffectDecision':
        """Effect allowed as-is"""
        if reasons is None:
            reasons = [DecisionReason.SUPPORTED_FEATURES]
        return cls(
            use_native=True,
            effect_type=effect_type,
            action="allow",
            original_effect=effect,
            modified_effect=effect,
            reasons=reasons
        )

    @classmethod
    def clamp(cls, original: Any, modified: Any, effect_type: str,
              reason: str, reasons: list[DecisionReason] = None, **kwargs) -> 'EffectDecision':
        """Effect clamped to caps"""
        if reasons is None:
            reasons = [DecisionReason.ABOVE_THRESHOLDS]
        return cls(
            use_native=True,
            effect_type=effect_type,
            action="clamp",
            original_effect=original,
            modified_effect=modified,
            violation_reason=reason,
            reasons=reasons,
            **kwargs
        )

    @classmethod
    def drop(cls, effect: Any, effect_type: str, reason: str,
             reasons: list[DecisionReason] = None) -> 'EffectDecision':
        """Effect dropped/forbidden"""
        if reasons is None:
            reasons = [DecisionReason.UNSUPPORTED_FEATURES]
        return cls(
            use_native=False,
            effect_type=effect_type,
            action="drop",
            original_effect=effect,
            modified_effect=None,
            violation_reason=reason,
            reasons=reasons
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize EffectDecision to dictionary"""
        base_dict = super().to_dict()
        base_dict.update({
            'effect_type': self.effect_type,
            'action': self.action,
            'violation_reason': self.violation_reason,
            'clamped_blur': self.clamped_blur,
            'clamped_distance': self.clamped_distance,
            'clamped_alpha': self.clamped_alpha,
            'color_downgraded': self.color_downgraded,
        })
        return base_dict


# Type alias for all decision types
ElementDecision = Union[PathDecision, TextDecision, GroupDecision, ImageDecision,
                        FilterDecision, GradientDecision, MultiPageDecision,
                        EffectDecision,
                        AnimationDecision, ClipPathDecision]


@dataclass
class PolicyMetrics:
    """Metrics collected during policy decision making"""

    # Decision counts
    total_decisions: int = 0
    native_decisions: int = 0
    emf_decisions: int = 0

    # Element type breakdown
    path_decisions: int = 0
    text_decisions: int = 0
    group_decisions: int = 0
    image_decisions: int = 0
    filter_decisions: int = 0
    gradient_decisions: int = 0
    multipage_decisions: int = 0
    animation_decisions: int = 0
    clippath_decisions: int = 0

    # Reason breakdown
    reason_counts: dict = None

    # Performance metrics
    avg_decision_time_ms: float = 0.0
    max_decision_time_ms: float = 0.0
    total_decision_time_ms: float = 0.0

    def __post_init__(self):
        if self.reason_counts is None:
            self.reason_counts = {}

    @property
    def native_percentage(self) -> float:
        """Percentage of decisions using native DrawingML"""
        if self.total_decisions == 0:
            return 0.0
        return (self.native_decisions / self.total_decisions) * 100.0

    @property
    def emf_percentage(self) -> float:
        """Percentage of decisions using EMF fallback"""
        return 100.0 - self.native_percentage

    def record_decision(self, decision: ElementDecision, time_ms: float):
        """Record a policy decision and its timing"""
        self.total_decisions += 1
        self.total_decision_time_ms += time_ms

        if time_ms > self.max_decision_time_ms:
            self.max_decision_time_ms = time_ms

        self.avg_decision_time_ms = self.total_decision_time_ms / self.total_decisions

        if decision.use_native:
            self.native_decisions += 1
        else:
            self.emf_decisions += 1

        # Count by element type
        if isinstance(decision, PathDecision):
            self.path_decisions += 1
        elif isinstance(decision, TextDecision):
            self.text_decisions += 1
        elif isinstance(decision, GroupDecision):
            self.group_decisions += 1
        elif isinstance(decision, ImageDecision):
            self.image_decisions += 1
        elif isinstance(decision, FilterDecision):
            self.filter_decisions += 1
        elif isinstance(decision, GradientDecision):
            self.gradient_decisions += 1
        elif isinstance(decision, MultiPageDecision):
            self.multipage_decisions += 1
        elif isinstance(decision, AnimationDecision):
            self.animation_decisions += 1
        elif isinstance(decision, ClipPathDecision):
            self.clippath_decisions += 1

        # Count reasons
        for reason in decision.reasons:
            reason_key = reason.value
            self.reason_counts[reason_key] = self.reason_counts.get(reason_key, 0) + 1

    def to_dict(self) -> dict:
        """Serialize metrics to dictionary"""
        return {
            "summary": {
                "total_decisions": self.total_decisions,
                "native_percentage": round(self.native_percentage, 1),
                "emf_percentage": round(self.emf_percentage, 1),
                "avg_decision_time_ms": round(self.avg_decision_time_ms, 3),
                "max_decision_time_ms": round(self.max_decision_time_ms, 3),
            },
            "by_element_type": {
                "paths": self.path_decisions,
                "text": self.text_decisions,
                "groups": self.group_decisions,
                "images": self.image_decisions,
                "filters": self.filter_decisions,
                "gradients": self.gradient_decisions,
                "multipages": self.multipage_decisions,
                "animations": self.animation_decisions,
                "clippaths": self.clippath_decisions,
            },
            "by_reason": self.reason_counts,
        }