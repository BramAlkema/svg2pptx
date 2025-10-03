#!/usr/bin/env python3
"""
Policy configuration and thresholds

Configurable parameters for policy decision making.
Allows tuning for different output quality vs performance trade-offs.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum


class OutputTarget(Enum):
    """Target output quality/performance profiles"""
    SPEED = "speed"           # Favor EMF for complex elements (fastest)
    BALANCED = "balanced"     # Smart mix of native DML and EMF (default)
    QUALITY = "quality"       # Favor native DML when possible (highest fidelity)
    COMPATIBILITY = "compatibility"  # Conservative native DML (maximum compatibility)


@dataclass
class Thresholds:
    """Configurable thresholds for policy decisions"""

    # Path complexity thresholds
    max_path_segments: int = 1000        # Segments before EMF fallback
    max_path_complexity_score: int = 100  # Combined complexity score
    max_bezier_control_distance: float = 1000.0  # Control point distance

    # Text complexity thresholds
    max_text_runs: int = 20              # Runs before EMF fallback
    max_text_complexity_score: int = 15  # Combined text complexity
    min_font_size_pt: float = 6.0        # Minimum readable font size

    # Font strategy thresholds (Three-Tier Strategy: ADR-003)
    enable_font_embedding: bool = True        # Tier 1: Embed @font-face fonts in PPTX
    enable_system_font_fallback: bool = True  # Tier 2: Use system font matching
    enable_text_to_path: bool = True          # Tier 3: Convert to paths as last resort
    min_font_match_confidence: float = 0.7    # Minimum confidence for system font match
    prefer_font_embedding: bool = True        # Prefer Tier 1 over Tier 2 when available
    max_font_file_size_mb: float = 2.0        # Maximum font file size to embed

    # Stroke thresholds
    max_stroke_width: float = 100.0      # EMU stroke width limit
    max_miter_limit: float = 10.0        # Miter join limit

    # Dash pattern thresholds
    max_dash_segments: int = 16          # Dash pattern complexity limit
    prefer_dash_presets: bool = True     # Try to map to dot/dash/lgDash presets
    allow_custom_dash: bool = True       # Emit <a:custDash> when no preset matches
    respect_dashoffset: bool = True      # Apply stroke-dashoffset phase rotation
    min_dash_segment_pct: float = 0.01   # Minimum dash segment as % of stroke width (1%)

    # Group thresholds
    max_group_elements: int = 500        # Elements before flattening
    max_nesting_depth: int = 20          # Group nesting limit

    # Gradient thresholds (expanded)
    max_gradient_stops: int = 10                    # Stop count limit
    max_gradient_transform_complexity: float = 5.0  # Transform determinant limit
    enable_gradient_simplification: bool = True     # Reduce stops if needed
    max_mesh_patches: int = 100                     # Mesh gradient patch limit
    max_mesh_grid_size: int = 10                    # Max rows/cols for mesh
    prefer_linear_over_radial: bool = False         # Simplify radial to linear
    enable_color_space_conversion: bool = True      # Convert non-sRGB gradients

    # Performance thresholds
    max_processing_time_ms: float = 100.0  # Per-element processing time
    max_memory_usage_mb: float = 50.0       # Memory usage limit

    # Transform thresholds (WordArt compatibility)
    max_skew_angle_deg: float = 18.0        # Maximum skew angle for WordArt
    max_scale_ratio: float = 5.0            # Maximum scale aspect ratio
    max_rotation_deviation_deg: float = 5.0  # Deviation from orthogonal angles

    # Filter effect thresholds
    max_filter_primitives: int = 5          # Chain length before fallback
    enable_native_blur: bool = True         # Use DrawingML blur effects
    enable_native_shadow: bool = True       # Use DrawingML shadow effects
    enable_filter_approximation: bool = True  # Approximate unsupported filters
    max_filter_complexity_score: int = 50   # Complexity before rasterization
    prefer_filter_rasterization: bool = False  # Prefer image over EMF fallback

    # Multi-page detection thresholds
    max_single_page_size_kb: int = 500          # Size before auto-split
    min_elements_per_page: int = 3              # Minimum content for page
    enable_auto_page_detection: bool = True     # Auto-detect pages
    prefer_explicit_markers: bool = True        # Trust data-page attributes
    max_pages_per_conversion: int = 50          # Hard limit on pages
    enable_size_based_splitting: bool = True    # Split large SVGs
    page_detection_heuristic: str = "balanced"  # 'strict' | 'balanced' | 'aggressive'

    # Animation thresholds
    max_animation_keyframes: int = 20           # Keyframe limit
    max_animation_duration_ms: float = 10000.0  # Duration limit (10s)
    enable_animation_conversion: bool = True    # Convert animations
    enable_video_export: bool = False           # Export as video instead
    max_simultaneous_animations: int = 5        # Concurrent animation limit
    prefer_entrance_effects: bool = True        # Favor entrance over motion

    # Clipping thresholds
    max_clip_path_segments: int = 100       # Clip path complexity
    max_clip_nesting_depth: int = 3         # Nested clip limit
    enable_native_clipping: bool = True     # Use DrawingML clipping
    enable_boolean_operations: bool = False # Support union/intersect
    prefer_rect_clips: bool = True          # Simplify to rectangles


@dataclass
class PolicyConfig:
    """Complete policy configuration"""

    target: OutputTarget = OutputTarget.BALANCED
    thresholds: Thresholds = None

    # Feature flags
    enable_path_optimization: bool = True
    enable_text_optimization: bool = True
    enable_group_flattening: bool = True
    enable_gradient_simplification: bool = True
    enable_clip_boolean_ops: bool = True
    enable_wordart_classification: bool = True

    # Fallback behavior
    conservative_clipping: bool = False    # Use EMF for any clipping
    conservative_gradients: bool = False   # Use EMF for complex gradients
    conservative_text: bool = False        # Use EMF for any text effects

    # WordArt configuration
    wordart_confidence_threshold: float = 0.8  # Minimum confidence for WordArt preset
    wordart_max_sample_points: int = 256       # Max points for path analysis

    # Performance monitoring
    enable_metrics: bool = True
    log_decisions: bool = False            # Log all policy decisions

    def __post_init__(self):
        if self.thresholds is None:
            self.thresholds = self._get_default_thresholds()

    def _get_default_thresholds(self) -> Thresholds:
        """Get default thresholds based on output target"""
        base_thresholds = Thresholds()

        if self.target == OutputTarget.SPEED:
            # Lower thresholds - prefer EMF for speed
            return Thresholds(
                max_path_segments=500,
                max_path_complexity_score=50,
                max_text_runs=10,
                max_text_complexity_score=8,
                max_group_elements=200,
                max_gradient_stops=5
            )

        elif self.target == OutputTarget.QUALITY:
            # Higher thresholds - prefer native DML for quality
            return Thresholds(
                max_path_segments=2000,
                max_path_complexity_score=200,
                max_text_runs=50,
                max_text_complexity_score=30,
                max_group_elements=1000,
                max_gradient_stops=20
            )

        elif self.target == OutputTarget.COMPATIBILITY:
            # Conservative thresholds for maximum compatibility
            return Thresholds(
                max_path_segments=300,
                max_path_complexity_score=30,
                max_text_runs=5,
                max_text_complexity_score=5,
                max_group_elements=100,
                max_gradient_stops=3,
                max_stroke_width=50.0,
                max_miter_limit=4.0
            )

        else:  # BALANCED
            return base_thresholds

    @classmethod
    def for_target(cls, target: OutputTarget, **overrides) -> 'PolicyConfig':
        """Create configuration for specific output target"""
        config = cls(target=target)

        # Apply any overrides
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
            elif hasattr(config.thresholds, key):
                setattr(config.thresholds, key, value)

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration to dictionary"""
        return {
            "target": self.target.value,
            "thresholds": {
                "max_path_segments": self.thresholds.max_path_segments,
                "max_path_complexity_score": self.thresholds.max_path_complexity_score,
                "max_text_runs": self.thresholds.max_text_runs,
                "max_text_complexity_score": self.thresholds.max_text_complexity_score,
                "max_group_elements": self.thresholds.max_group_elements,
                "max_gradient_stops": self.thresholds.max_gradient_stops,
            },
            "flags": {
                "enable_path_optimization": self.enable_path_optimization,
                "enable_text_optimization": self.enable_text_optimization,
                "enable_group_flattening": self.enable_group_flattening,
                "conservative_clipping": self.conservative_clipping,
                "conservative_gradients": self.conservative_gradients,
                "conservative_text": self.conservative_text,
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PolicyConfig':
        """Deserialize configuration from dictionary"""
        target = OutputTarget(data.get("target", "balanced"))
        config = cls.for_target(target)

        # Apply threshold overrides
        if "thresholds" in data:
            for key, value in data["thresholds"].items():
                if hasattr(config.thresholds, key):
                    setattr(config.thresholds, key, value)

        # Apply flag overrides
        if "flags" in data:
            for key, value in data["flags"].items():
                if hasattr(config, key):
                    setattr(config, key, value)

        return config

    @classmethod
    def speed(cls) -> 'PolicyConfig':
        """Create speed-optimized configuration"""
        return cls.for_target(OutputTarget.SPEED)

    @classmethod
    def balanced(cls) -> 'PolicyConfig':
        """Create balanced configuration (default)"""
        return cls.for_target(OutputTarget.BALANCED)

    @classmethod
    def quality(cls) -> 'PolicyConfig':
        """Create quality-optimized configuration"""
        return cls.for_target(OutputTarget.QUALITY)

    @classmethod
    def compatibility(cls) -> 'PolicyConfig':
        """Create compatibility-optimized configuration"""
        return cls.for_target(OutputTarget.COMPATIBILITY)


# Predefined configurations for common use cases
SPEED_CONFIG = PolicyConfig.for_target(OutputTarget.SPEED)
BALANCED_CONFIG = PolicyConfig.for_target(OutputTarget.BALANCED)
QUALITY_CONFIG = PolicyConfig.for_target(OutputTarget.QUALITY)
COMPATIBILITY_CONFIG = PolicyConfig.for_target(OutputTarget.COMPATIBILITY)