#!/usr/bin/env python3
"""
Policy decision types and results

Defines the output types and decision structures used by the policy engine.
Provides clear reasoning for all policy decisions.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict, Any
from enum import Enum

# Import font strategy types for integration
from ..ir.font_metadata import FontStrategy


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

    # Filter-specific reasons
    SIMPLE_CONTENT = "simple_content"
    COMPLEX_CONTENT = "complex_content"
    QUALITY_PRIORITY = "quality_priority"
    PERFORMANCE_PRIORITY = "performance_priority"

    # Font embedding reasons
    CUSTOM_FONT_REQUIRED = "custom_font_required"
    FONT_ALREADY_EMBEDDED = "font_already_embedded"
    FONT_SIZE_LIMIT_EXCEEDED = "font_size_limit_exceeded"
    EMBEDDING_DISABLED = "embedding_disabled"
    LICENSE_RESTRICTION = "license_restriction"  # Font license prohibits embedding
    BALANCED_MODE = "balanced_mode"

    # Font strategy reasons
    SYSTEM_FONT_AVAILABLE = "system_font_available"
    SYSTEM_FONT_OPTIMAL = "system_font_optimal"
    FONT_EMBEDDING_PREFERRED = "font_embedding_preferred"
    FONT_EMBEDDING_REQUIRED = "font_embedding_required"
    PATH_CONVERSION_REQUIRED = "path_conversion_required"
    PATH_CONVERSION_OPTIMAL = "path_conversion_optimal"
    FALLBACK_STRATEGY_REQUIRED = "fallback_strategy_required"
    ALL_STRATEGIES_FAILED = "all_strategies_failed"
    COMPLEX_TEXT_TRANSFORMS = "complex_text_transforms"
    HIGH_FIDELITY_REQUIRED = "high_fidelity_required"

    # Image reasons
    IMAGE_FORMAT_SUPPORTED = "image_format_supported"
    IMAGE_SIZE_OK = "image_size_ok"
    IMAGE_SIZE_TOO_LARGE = "image_size_too_large"
    IMAGE_EXTERNAL_URL = "image_external_url"
    IMAGE_CONVERSION_NEEDED = "image_conversion_needed"
    IMAGE_ALREADY_EMBEDDED = "image_already_embedded"


@dataclass(frozen=True)
class PolicyDecision:
    """Base policy decision"""
    use_native: bool
    reasons: List[DecisionReason]
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
            reason_list = [r.value.replace('_', ' ') for r in self.reasons]
            explanation += f" - {primary} + {len(self.reasons)-1} other factors"

        return explanation


@dataclass(frozen=True)
class PathDecision(PolicyDecision):
    """Policy decision for Path elements"""
    segment_count: int = 0
    complexity_score: int = 0
    has_clipping: bool = False
    has_complex_stroke: bool = False
    has_complex_fill: bool = False

    @classmethod
    def native(cls, reasons: List[DecisionReason], **kwargs) -> 'PathDecision':
        """Create decision for native DrawingML"""
        return cls(use_native=True, reasons=reasons, **kwargs)

    @classmethod
    def emf(cls, reasons: List[DecisionReason], **kwargs) -> 'PathDecision':
        """Create decision for EMF fallback"""
        return cls(use_native=False, reasons=reasons, **kwargs)


@dataclass(frozen=True)
class TextDecision(PolicyDecision):
    """Policy decision for TextFrame elements"""
    run_count: int = 0
    complexity_score: int = 0
    has_missing_fonts: bool = False
    has_effects: bool = False
    has_multiline: bool = False
    wordart_preset: Optional[str] = None
    wordart_parameters: Optional[Dict[str, Any]] = None
    wordart_confidence: float = 0.0
    transform_complexity: Optional[Dict[str, Any]] = None

    # Font strategy integration fields
    font_strategy: Optional[FontStrategy] = None
    font_availability: Dict[str, bool] = field(default_factory=dict)
    requires_path_conversion: bool = False
    requires_embedding: bool = False
    fallback_reason: Optional[str] = None

    @classmethod
    def native(cls, reasons: List[DecisionReason], **kwargs) -> 'TextDecision':
        """Create decision for native DrawingML"""
        return cls(use_native=True, reasons=reasons, **kwargs)

    @classmethod
    def emf(cls, reasons: List[DecisionReason], **kwargs) -> 'TextDecision':
        """Create decision for EMF fallback"""
        return cls(use_native=False, reasons=reasons, **kwargs)

    @classmethod
    def wordart(cls, preset: str, parameters: Dict[str, Any], confidence: float,
                reasons: List[DecisionReason] = None, **kwargs) -> 'TextDecision':
        """Create decision for WordArt preset"""
        if reasons is None:
            reasons = [DecisionReason.WORDART_PATTERN_DETECTED, DecisionReason.NATIVE_PRESET_AVAILABLE]

        return cls(
            use_native=True,
            reasons=reasons,
            wordart_preset=preset,
            wordart_parameters=parameters,
            wordart_confidence=confidence,
            **kwargs
        )

    @classmethod
    def system_font(cls, reasons: List[DecisionReason], font_availability: Dict[str, bool] = None,
                   **kwargs) -> 'TextDecision':
        """Create decision for system font strategy"""
        return cls(
            use_native=True,
            font_strategy=FontStrategy.SYSTEM,
            font_availability=font_availability or {},
            reasons=reasons,
            **kwargs
        )

    @classmethod
    def embedded_font(cls, reasons: List[DecisionReason], font_availability: Dict[str, bool] = None,
                     **kwargs) -> 'TextDecision':
        """Create decision for embedded font strategy"""
        return cls(
            use_native=True,
            font_strategy=FontStrategy.EMBEDDED,
            font_availability=font_availability or {},
            requires_embedding=True,
            reasons=reasons,
            **kwargs
        )

    @classmethod
    def text_to_path(cls, reasons: List[DecisionReason], font_availability: Dict[str, bool] = None,
                    **kwargs) -> 'TextDecision':
        """Create decision for text-to-path strategy"""
        return cls(
            use_native=True,
            font_strategy=FontStrategy.PATH,
            font_availability=font_availability or {},
            requires_path_conversion=True,
            reasons=reasons,
            **kwargs
        )

    @classmethod
    def fallback(cls, reasons: List[DecisionReason], fallback_reason: str = None,
                font_availability: Dict[str, bool] = None, **kwargs) -> 'TextDecision':
        """Create decision for fallback strategy"""
        return cls(
            use_native=True,
            font_strategy=FontStrategy.FALLBACK,
            font_availability=font_availability or {},
            fallback_reason=fallback_reason,
            reasons=reasons,
            **kwargs
        )

    @property
    def is_wordart(self) -> bool:
        """Check if this is a WordArt decision"""
        return self.wordart_preset is not None

    @property
    def has_font_strategy(self) -> bool:
        """Check if this decision has a font strategy"""
        return self.font_strategy is not None

    @property
    def is_system_font(self) -> bool:
        """Check if this is a system font strategy decision"""
        return self.font_strategy == FontStrategy.SYSTEM

    @property
    def is_embedded_font(self) -> bool:
        """Check if this is an embedded font strategy decision"""
        return self.font_strategy == FontStrategy.EMBEDDED

    @property
    def is_text_to_path(self) -> bool:
        """Check if this is a text-to-path strategy decision"""
        return self.font_strategy == FontStrategy.PATH

    @property
    def is_fallback(self) -> bool:
        """Check if this is a fallback strategy decision"""
        return self.font_strategy == FontStrategy.FALLBACK

    @property
    def output_format(self) -> str:
        """Get target output format"""
        if self.is_wordart:
            return f"WordArt({self.wordart_preset})"
        elif self.has_font_strategy:
            return f"Font({self.font_strategy.value})"
        return "DrawingML" if self.use_native else "EMF"


@dataclass(frozen=True)
class GroupDecision(PolicyDecision):
    """Policy decision for Group elements"""
    element_count: int = 0
    nesting_depth: int = 0
    should_flatten: bool = False
    has_complex_clipping: bool = False

    @classmethod
    def native(cls, reasons: List[DecisionReason], **kwargs) -> 'GroupDecision':
        """Create decision for native DrawingML"""
        return cls(use_native=True, reasons=reasons, **kwargs)

    @classmethod
    def emf(cls, reasons: List[DecisionReason], **kwargs) -> 'GroupDecision':
        """Create decision for EMF fallback"""
        return cls(use_native=False, reasons=reasons, **kwargs)


@dataclass(frozen=True)
class ImageDecision(PolicyDecision):
    """Policy decision for Image elements"""
    # Image metadata
    format: str = ""                    # png, jpg, gif, etc.
    size_bytes: int = 0
    dimensions: tuple = (0, 0)          # (width, height)
    has_transparency: bool = False

    # Embedding strategy
    embed_inline: bool = True           # Embed in PPTX vs external reference
    convert_format: bool = False        # Convert to different format
    target_format: Optional[str] = None # If converting: "png", "jpg"

    # Optimization
    compress: bool = False
    max_dimension: Optional[int] = None # Resize if larger

    @classmethod
    def native(cls, reasons: List[DecisionReason], **kwargs) -> 'ImageDecision':
        """Create decision to embed image in PPTX"""
        return cls(use_native=True, embed_inline=True, reasons=reasons, **kwargs)

    @classmethod
    def external(cls, reasons: List[DecisionReason], **kwargs) -> 'ImageDecision':
        """Create decision to keep as external reference (http URLs)"""
        return cls(use_native=True, embed_inline=False, reasons=reasons, **kwargs)

    @classmethod
    def emf(cls, reasons: List[DecisionReason], **kwargs) -> 'ImageDecision':
        """Create decision for EMF fallback"""
        return cls(use_native=False, reasons=reasons, **kwargs)


@dataclass(frozen=True)
class FontEmbeddingDecision(PolicyDecision):
    """Policy decision for font embedding"""
    font_family: str = ""
    font_size_bytes: int = 0
    sha1_checksum: str = ""
    should_embed: bool = True

    @classmethod
    def embed(cls, reasons: List[DecisionReason], **kwargs) -> 'FontEmbeddingDecision':
        """Create decision to embed font"""
        return cls(use_native=True, should_embed=True, reasons=reasons, **kwargs)

    @classmethod
    def skip(cls, reasons: List[DecisionReason], **kwargs) -> 'FontEmbeddingDecision':
        """Create decision to skip font (already embedded or disabled)"""
        return cls(use_native=True, should_embed=False, reasons=reasons, **kwargs)


# Type alias for all decision types
ElementDecision = Union[PathDecision, TextDecision, GroupDecision, ImageDecision]


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
            },
            "by_reason": self.reason_counts
        }