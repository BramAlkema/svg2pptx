"""
Type definitions for SVG analysis system.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from enum import Enum


class SupportLevel(Enum):
    """Feature support level."""
    FULL = "full"  # Native PowerPoint support
    PARTIAL = "partial"  # Supported with limitations
    VIA_EMF = "via_emf"  # Rasterized to EMF vector
    VIA_RASTER = "via_raster"  # Rasterized to PNG
    NOT_SUPPORTED = "not_supported"  # Not converted


class CompatibilityLevel(Enum):
    """Platform compatibility level."""
    FULL = "full"
    PARTIAL = "partial"
    LIMITED = "limited"
    NONE = "none"


@dataclass
class ElementCounts:
    """SVG element count statistics."""
    total_elements: int = 0
    shapes: int = 0  # rect, circle, ellipse, line, polyline, polygon
    paths: int = 0
    text: int = 0
    groups: int = 0
    gradients: int = 0
    filters: int = 0
    images: int = 0
    use_elements: int = 0
    symbols: int = 0
    defs: int = 0
    animations: int = 0
    max_nesting_depth: int = 0

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            "total_elements": self.total_elements,
            "shapes": self.shapes,
            "paths": self.paths,
            "text": self.text,
            "groups": self.groups,
            "gradients": self.gradients,
            "filters": self.filters,
            "images": self.images,
            "use_elements": self.use_elements,
            "symbols": self.symbols,
            "defs": self.defs,
            "animations": self.animations,
            "max_nesting_depth": self.max_nesting_depth
        }


@dataclass
class FeatureSet:
    """Detected SVG features."""
    # Basic categories
    has_animations: bool = False
    has_gradients: bool = False
    has_filters: bool = False
    has_clipping: bool = False
    has_masks: bool = False
    has_text_on_path: bool = False
    has_patterns: bool = False
    has_markers: bool = False

    # Detailed feature lists
    gradient_types: Set[str] = field(default_factory=set)  # linear, radial, mesh
    filter_types: Set[str] = field(default_factory=set)  # blur, drop-shadow, etc.
    animation_types: Set[str] = field(default_factory=set)  # animate, animateTransform
    transform_types: Set[str] = field(default_factory=set)  # translate, rotate, scale

    # Complexity indicators
    has_complex_paths: bool = False  # Bezier curves, arcs
    has_complex_transforms: bool = False  # Matrix, skew
    has_embedded_images: bool = False
    has_external_references: bool = False

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "animations": self.has_animations,
            "gradients": list(self.gradient_types) if self.gradient_types else [],
            "filters": list(self.filter_types) if self.filter_types else [],
            "clipping": self.has_clipping,
            "masks": self.has_masks,
            "text_on_path": self.has_text_on_path,
            "patterns": self.has_patterns,
            "markers": self.has_markers,
            "complex_paths": self.has_complex_paths,
            "complex_transforms": self.has_complex_transforms,
            "embedded_images": self.has_embedded_images,
            "external_references": self.has_external_references
        }


@dataclass
class PerformanceEstimate:
    """Estimated conversion performance metrics."""
    conversion_time_ms: int  # Estimated conversion time in milliseconds
    output_size_kb: int  # Estimated PPTX file size in KB
    memory_usage_mb: int  # Estimated peak memory usage in MB

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            "conversion_time_ms": self.conversion_time_ms,
            "output_size_kb": self.output_size_kb,
            "memory_usage_mb": self.memory_usage_mb
        }


@dataclass
class PolicyRecommendation:
    """Policy recommendation with reasoning."""
    target: str  # "speed", "balanced", "quality"
    confidence: float  # 0.0 to 1.0
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "target": self.target,
            "confidence": self.confidence,
            "reasons": self.reasons
        }


@dataclass
class SVGAnalysisResult:
    """Complete SVG analysis result."""
    complexity_score: int  # 0-100
    element_counts: ElementCounts
    features: FeatureSet
    recommended_policy: PolicyRecommendation
    estimated_performance: PerformanceEstimate
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            "complexity_score": self.complexity_score,
            "element_counts": self.element_counts.to_dict(),
            "features_detected": self.features.to_dict(),
            "recommended_policy": self.recommended_policy.to_dict(),
            "estimated_performance": self.estimated_performance.to_dict(),
            "warnings": self.warnings
        }


@dataclass
class CompatibilityReport:
    """Platform compatibility report."""
    powerpoint_2016: CompatibilityLevel
    powerpoint_2019: CompatibilityLevel
    powerpoint_365: CompatibilityLevel
    google_slides: CompatibilityLevel
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "powerpoint_2016": self.powerpoint_2016.value,
            "powerpoint_2019": self.powerpoint_2019.value,
            "powerpoint_365": self.powerpoint_365.value,
            "google_slides": self.google_slides.value,
            "notes": self.notes
        }
