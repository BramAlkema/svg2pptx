#!/usr/bin/env python3
"""
Font Metadata for Clean Slate IR

Immutable data structures for font information and strategy decisions.
Designed for the Clean Slate text processing system.
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class FontStrategy(Enum):
    """Font handling strategy for 3-tier system."""
    EMBEDDED = "embedded"     # Tier 1: Embed font in PPTX package
    SYSTEM = "system"         # Tier 2: Use system-available fonts
    PATH = "path"             # Tier 3: Convert text to vector paths
    FALLBACK = "fallback"     # Tier 4: Basic text with generic font


class FontAvailability(Enum):
    """Font availability status."""
    AVAILABLE = "available"           # Font is available for use
    UNAVAILABLE = "unavailable"       # Font not found
    UNKNOWN = "unknown"               # Availability not yet determined
    EMBEDDED = "embedded"             # Font is/will be embedded
    SYSTEM_FALLBACK = "system_fallback"  # Using system fallback


class FontWeight(Enum):
    """CSS font weight values."""
    THIN = 100
    EXTRA_LIGHT = 200
    LIGHT = 300
    NORMAL = 400
    MEDIUM = 500
    SEMI_BOLD = 600
    BOLD = 700
    EXTRA_BOLD = 800
    BLACK = 900


@dataclass(frozen=True)
class FontMetrics:
    """Font metrics for precise text layout calculations."""
    ascent: float = 0.8          # Typical ascent ratio
    descent: float = 0.2         # Typical descent ratio
    line_height: float = 1.2     # Default line height multiplier
    x_height: float = 0.5        # X-height ratio for lowercase
    cap_height: float = 0.7      # Capital letter height ratio

    @property
    def total_height(self) -> float:
        """Total font height (ascent + descent)."""
        return self.ascent + self.descent


@dataclass(frozen=True)
class FontMetadata:
    """
    Comprehensive font metadata for text processing.

    Immutable structure containing all font information needed
    for strategy decisions and precise layout calculations.
    """
    family: str                                    # Font family name
    weight: int = 400                             # Numeric weight (100-900)
    style: str = "normal"                         # normal|italic|oblique
    size_pt: float = 12.0                        # Font size in points

    # Strategy and availability
    strategy: FontStrategy = FontStrategy.SYSTEM  # Chosen strategy
    availability: FontAvailability = FontAvailability.UNKNOWN

    # Optional advanced properties
    metrics: Optional[FontMetrics] = None         # Font metrics if available
    embedding_required: bool = False              # Whether embedding is needed
    embedding_confidence: float = 0.0            # Confidence in font detection (0-1)
    fallback_chain: List[str] = None             # Fallback font list

    # CSS properties
    variant: str = "normal"                       # normal|small-caps
    stretch: str = "normal"                       # Font stretch value

    def __post_init__(self):
        """Validate font metadata."""
        if self.weight < 100 or self.weight > 900:
            raise ValueError(f"Font weight must be 100-900, got {self.weight}")
        if self.size_pt <= 0:
            raise ValueError(f"Font size must be positive, got {self.size_pt}")
        if not self.family.strip():
            raise ValueError("Font family cannot be empty")

        # Set default fallback chain if not provided
        if self.fallback_chain is None:
            object.__setattr__(self, 'fallback_chain', ['Arial', 'sans-serif'])

    @property
    def is_bold(self) -> bool:
        """Check if font weight indicates bold."""
        return self.weight >= 700

    @property
    def is_italic(self) -> bool:
        """Check if font style is italic/oblique."""
        return self.style.lower() in ('italic', 'oblique')

    @property
    def css_weight_name(self) -> str:
        """Get CSS weight name for the numeric weight."""
        weight_names = {
            100: 'thin',
            200: 'extra-light',
            300: 'light',
            400: 'normal',
            500: 'medium',
            600: 'semi-bold',
            700: 'bold',
            800: 'extra-bold',
            900: 'black'
        }
        return weight_names.get(self.weight, str(self.weight))

    @property
    def effective_metrics(self) -> FontMetrics:
        """Get font metrics, using defaults if not available."""
        return self.metrics or FontMetrics()

    def with_strategy(self, strategy: FontStrategy) -> 'FontMetadata':
        """Create new FontMetadata with different strategy."""
        return FontMetadata(
            family=self.family,
            weight=self.weight,
            style=self.style,
            size_pt=self.size_pt,
            strategy=strategy,
            availability=self.availability,
            metrics=self.metrics,
            embedding_required=self.embedding_required,
            embedding_confidence=self.embedding_confidence,
            fallback_chain=self.fallback_chain,
            variant=self.variant,
            stretch=self.stretch
        )

    def with_availability(self, availability: FontAvailability) -> 'FontMetadata':
        """Create new FontMetadata with different availability."""
        return FontMetadata(
            family=self.family,
            weight=self.weight,
            style=self.style,
            size_pt=self.size_pt,
            strategy=self.strategy,
            availability=availability,
            metrics=self.metrics,
            embedding_required=self.embedding_required,
            embedding_confidence=self.embedding_confidence,
            fallback_chain=self.fallback_chain,
            variant=self.variant,
            stretch=self.stretch
        )


@dataclass(frozen=True)
class FontAnalysisResult:
    """Result of font analysis for strategy decisions."""
    font_metadata: FontMetadata
    recommended_strategy: FontStrategy
    confidence: float                    # Confidence in recommendation (0-1)
    analysis_time_ms: float             # Time taken for analysis
    notes: List[str] = None             # Additional analysis notes

    def __post_init__(self):
        if self.notes is None:
            object.__setattr__(self, 'notes', [])


# CSS font weight mapping for legacy compatibility
CSS_FONT_WEIGHTS = {
    # CSS keywords
    'normal': 400,
    'bold': 700,
    'bolder': 800,  # Relative to parent
    'lighter': 200, # Relative to parent

    # CSS Level 1-4 numeric weights
    '100': 100, '200': 200, '300': 300, '400': 400, '500': 500,
    '600': 600, '700': 700, '800': 800, '900': 900,

    # Extended CSS weight keywords
    'thin': 100,
    'hairline': 100,
    'extralight': 200,
    'ultralight': 200,
    'light': 300,
    'regular': 400,
    'medium': 500,
    'semibold': 600,
    'demibold': 600,
    'extrabold': 800,
    'ultrabold': 800,
    'heavy': 800,
    'black': 900,
    'ultrablack': 900
}

# CSS font style mapping
CSS_FONT_STYLES = {
    'normal': 'normal',
    'italic': 'italic',
    'oblique': 'italic',  # Map oblique to italic for PowerPoint
    'inherit': 'normal'
}


def parse_font_weight(weight_str: str) -> int:
    """
    Parse CSS font weight string to numeric value.

    Args:
        weight_str: CSS weight value (numeric or keyword)

    Returns:
        Numeric weight value (100-900)

    Raises:
        ValueError: If weight string is invalid
    """
    if not weight_str:
        return 400

    weight_str = weight_str.strip().lower()

    # Try direct numeric conversion first
    try:
        weight = int(weight_str)
        if 100 <= weight <= 900:
            return weight
    except ValueError:
        pass

    # Look up in CSS mapping
    if weight_str in CSS_FONT_WEIGHTS:
        return CSS_FONT_WEIGHTS[weight_str]

    # Default to normal if unrecognized
    return 400


def normalize_font_style(style_str: str) -> str:
    """
    Normalize CSS font style to PowerPoint-compatible value.

    Args:
        style_str: CSS font style value

    Returns:
        Normalized style ('normal' or 'italic')
    """
    if not style_str:
        return 'normal'

    style_str = style_str.strip().lower()
    return CSS_FONT_STYLES.get(style_str, 'normal')


def create_font_metadata(
    family: str,
    weight: Optional[str] = None,
    style: Optional[str] = None,
    size_pt: float = 12.0,
    **kwargs
) -> FontMetadata:
    """
    Create FontMetadata with CSS value parsing.

    Args:
        family: Font family name
        weight: CSS font weight (optional)
        style: CSS font style (optional)
        size_pt: Font size in points
        **kwargs: Additional FontMetadata parameters

    Returns:
        FontMetadata instance with parsed values
    """
    return FontMetadata(
        family=family.strip(),
        weight=parse_font_weight(weight) if weight else 400,
        style=normalize_font_style(style) if style else 'normal',
        size_pt=size_pt,
        **kwargs
    )