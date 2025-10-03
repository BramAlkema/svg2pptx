#!/usr/bin/env python3
"""
Type definitions for Smart Font Converter

Provides data structures and enums for the font conversion system.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum

from ...ir.font_metadata import FontStrategy


class FontComplexity(Enum):
    """Text complexity levels for strategy selection."""
    SIMPLE = "simple"           # Single font, no transforms
    MODERATE = "moderate"       # Multiple runs, basic styling
    COMPLEX = "complex"         # Transforms, effects, gradients
    EXTREME = "extreme"         # Path-following, heavy transforms


@dataclass(frozen=True)
class FontConversionConfig:
    """Configuration for Smart Font Converter."""

    # Strategy selection
    enable_wordart: bool = True
    enable_text_to_path: bool = True
    enable_font_embedding: bool = False

    # Performance
    cache_size: int = 256
    timeout_ms: float = 500.0

    # Quality settings
    path_optimization_level: int = 1  # 0=none, 1=basic, 2=aggressive
    wordart_confidence_threshold: float = 0.7

    # Fallback behavior
    fallback_font_chain: List[str] = field(default_factory=lambda: [
        'Arial', 'Calibri', 'Helvetica', 'sans-serif'
    ])

    # Debug options
    verbose_logging: bool = False
    performance_tracking: bool = True


@dataclass
class HandlerResult:
    """Result from a strategy handler."""

    success: bool
    xml_content: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    error: Optional[Exception] = None

    def __post_init__(self):
        """Validate handler result."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")
        if self.success and not self.xml_content:
            raise ValueError("Successful result must have XML content")


@dataclass
class ExecutionResult:
    """Result from strategy executor."""

    strategy: FontStrategy
    handler_result: HandlerResult
    execution_time_ms: float
    fallback_attempted: bool = False
    fallback_strategy: Optional[FontStrategy] = None


@dataclass
class FontConversionResult:
    """Final result of font conversion process."""

    # Core results
    strategy_used: FontStrategy
    drawingml_xml: str
    confidence: float

    # Strategy information
    strategies_attempted: List[FontStrategy]
    fallback_chain: List[FontStrategy]

    # Performance metrics
    total_time_ms: float
    strategy_selection_ms: float
    execution_time_ms: float

    # Metadata
    complexity: FontComplexity
    font_available: bool
    wordart_preset: Optional[str] = None
    path_count: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Debug information
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate conversion result."""
        if not self.drawingml_xml:
            raise ValueError("Conversion result must have DrawingML XML")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")

    @property
    def is_high_confidence(self) -> bool:
        """Check if conversion has high confidence."""
        return self.confidence >= 0.9

    @property
    def used_fallback(self) -> bool:
        """Check if fallback strategy was used."""
        return len(self.strategies_attempted) > 1