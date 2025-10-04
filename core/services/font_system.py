#!/usr/bin/env python3
"""
Font System for Clean Slate Text Processing

Unified font handling service implementing the 3-tier font strategy:
1. Embedded fonts (best quality, larger file size)
2. System fonts (good quality, no file impact)
3. Path conversion (perfect fidelity, complex geometry)
4. Fallback text (basic rendering, guaranteed compatibility)

This service replaces all legacy font handling with modern Clean Slate architecture.
"""

import logging
import time
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import hashlib

from ..ir.font_metadata import (
    FontMetadata, FontStrategy, FontAvailability, FontAnalysisResult,
    FontMetrics, create_font_metadata, parse_font_weight, normalize_font_style
)

logger = logging.getLogger(__name__)


@dataclass
class FontSystemConfig:
    """Configuration for font system behavior."""
    # Strategy preferences
    prefer_embedding: bool = True
    embedding_size_limit_mb: float = 10.0
    confidence_threshold: float = 0.8

    # Performance settings
    enable_caching: bool = True
    cache_size_limit: int = 256
    analysis_timeout_ms: float = 100.0

    # Fallback settings
    default_fallback_chain: List[str] = None
    enable_path_conversion: bool = True
    path_conversion_threshold: float = 0.5

    def __post_init__(self):
        if self.default_fallback_chain is None:
            object.__setattr__(self, 'default_fallback_chain',
                             ['Arial', 'Helvetica', 'sans-serif'])


class FontAvailabilityCache:
    """Cache for font availability analysis results."""

    def __init__(self, max_size: int = 256):
        self._cache: Dict[str, FontAnalysisResult] = {}
        self._access_order: List[str] = []
        self._max_size = max_size

    def get(self, font_key: str) -> Optional[FontAnalysisResult]:
        """Get cached analysis result."""
        if font_key in self._cache:
            # Move to end for LRU
            self._access_order.remove(font_key)
            self._access_order.append(font_key)
            return self._cache[font_key]
        return None

    def put(self, font_key: str, result: FontAnalysisResult) -> None:
        """Cache analysis result."""
        if font_key in self._cache:
            # Update existing
            self._cache[font_key] = result
            self._access_order.remove(font_key)
            self._access_order.append(font_key)
        else:
            # Add new
            if len(self._cache) >= self._max_size:
                # Remove least recently used
                oldest = self._access_order.pop(0)
                del self._cache[oldest]

            self._cache[font_key] = result
            self._access_order.append(font_key)

    def clear(self) -> None:
        """Clear all cached results."""
        self._cache.clear()
        self._access_order.clear()

    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


class FontSystem:
    """
    Unified font processing system for Clean Slate architecture.

    Provides comprehensive font handling including:
    - 3-tier font strategy decisions
    - Font availability detection
    - Font metadata extraction and caching
    - Integration with text processing pipeline
    """

    def __init__(self, config: Optional[FontSystemConfig] = None):
        """
        Initialize font system.

        Args:
            config: Optional configuration, uses defaults if not provided
        """
        self._config = config or FontSystemConfig()
        self._cache = FontAvailabilityCache(self._config.cache_size_limit) if self._config.enable_caching else None

        # Font detection components (lazy loaded)
        self._font_detector = None
        self._font_embedder = None

        # System font registry
        self._system_fonts: Optional[Set[str]] = None
        self._embedded_fonts: Set[str] = set()

        logger.info(f"FontSystem initialized with config: {self._config}")

    def analyze_font(self, font_metadata: FontMetadata) -> FontAnalysisResult:
        """
        Analyze font and determine optimal strategy.

        Args:
            font_metadata: Font information to analyze

        Returns:
            FontAnalysisResult with strategy recommendation
        """
        start_time = time.perf_counter()

        # Create cache key
        font_key = self._create_font_key(font_metadata)

        # Check cache first
        if self._cache:
            cached_result = self._cache.get(font_key)
            if cached_result:
                logger.debug(f"Font analysis cache hit for {font_metadata.family}")
                return cached_result

        # Perform analysis
        try:
            strategy, confidence, notes = self._determine_font_strategy(font_metadata)

            # Update metadata with strategy
            updated_metadata = font_metadata.with_strategy(strategy)
            updated_metadata = updated_metadata.with_availability(
                self._strategy_to_availability(strategy)
            )

            # Create result
            analysis_time = (time.perf_counter() - start_time) * 1000
            result = FontAnalysisResult(
                font_metadata=updated_metadata,
                recommended_strategy=strategy,
                confidence=confidence,
                analysis_time_ms=analysis_time,
                notes=notes
            )

            # Cache result
            if self._cache:
                self._cache.put(font_key, result)

            logger.debug(f"Font analysis complete for {font_metadata.family}: "
                        f"strategy={strategy.value}, confidence={confidence:.2f}")

            return result

        except Exception as e:
            logger.error(f"Font analysis failed for {font_metadata.family}: {e}")
            # Fallback to basic strategy
            analysis_time = (time.perf_counter() - start_time) * 1000
            return FontAnalysisResult(
                font_metadata=font_metadata.with_strategy(FontStrategy.FALLBACK),
                recommended_strategy=FontStrategy.FALLBACK,
                confidence=0.0,
                analysis_time_ms=analysis_time,
                notes=[f"Analysis failed: {str(e)}"]
            )

    def _determine_font_strategy(self, font_metadata: FontMetadata) -> Tuple[FontStrategy, float, List[str]]:
        """
        Determine optimal font strategy using 3-tier system.

        Returns:
            Tuple of (strategy, confidence, notes)
        """
        notes = []

        # Check if font is already embedded
        if font_metadata.family in self._embedded_fonts:
            notes.append("Font already embedded in package")
            return FontStrategy.EMBEDDED, 1.0, notes

        # Tier 1: Embedded fonts (if enabled and font not too large)
        if self._config.prefer_embedding:
            embedding_feasible = self._check_embedding_feasibility(font_metadata)
            if embedding_feasible:
                notes.append("Font suitable for embedding")
                return FontStrategy.EMBEDDED, 0.95, notes

        # Tier 2: System fonts
        if self._is_system_font_available(font_metadata.family):
            notes.append("Font available on system")
            return FontStrategy.SYSTEM, 0.85, notes

        # Check fallback chain
        for fallback_font in font_metadata.fallback_chain:
            if self._is_system_font_available(fallback_font):
                notes.append(f"Fallback font '{fallback_font}' available on system")
                return FontStrategy.SYSTEM, 0.75, notes

        # Tier 3: Path conversion (if enabled)
        if self._config.enable_path_conversion:
            notes.append("Font unavailable, using path conversion")
            return FontStrategy.PATH, 0.90, notes

        # Tier 4: Basic fallback
        notes.append("Using basic fallback text rendering")
        return FontStrategy.FALLBACK, 0.60, notes

    def _check_embedding_feasibility(self, font_metadata: FontMetadata) -> bool:
        """Check if font embedding is feasible."""
        try:
            # Initialize font detector if needed
            if not self._font_detector:
                self._font_detector = self._create_font_detector()

            # Check if font file exists and size
            if self._font_detector:
                font_path = self._font_detector.find_font_file(
                    font_metadata.family,
                    font_metadata.weight,
                    font_metadata.is_italic
                )

                if font_path and Path(font_path).exists():
                    size_mb = Path(font_path).stat().st_size / (1024 * 1024)
                    return size_mb <= self._config.embedding_size_limit_mb

            return False

        except Exception as e:
            logger.debug(f"Font embedding feasibility check failed: {e}")
            return False

    def _is_system_font_available(self, font_family: str) -> bool:
        """Check if font is available on the system."""
        try:
            # Lazy load system fonts
            if self._system_fonts is None:
                self._system_fonts = self._discover_system_fonts()

            # Normalize font name for comparison
            normalized_family = font_family.lower().replace(' ', '').replace('-', '')

            for system_font in self._system_fonts:
                normalized_system = system_font.lower().replace(' ', '').replace('-', '')
                if normalized_family == normalized_system:
                    return True

            return False

        except Exception as e:
            logger.debug(f"System font availability check failed: {e}")
            return False

    def _discover_system_fonts(self) -> Set[str]:
        """Discover available system fonts."""
        system_fonts = set()

        try:
            # Try to use font detection library
            if not self._font_detector:
                self._font_detector = self._create_font_detector()

            if self._font_detector and hasattr(self._font_detector, 'list_system_fonts'):
                system_fonts = set(self._font_detector.list_system_fonts())
            else:
                # Fallback to common fonts
                system_fonts = {
                    'Arial', 'Helvetica', 'Times New Roman', 'Times',
                    'Courier New', 'Courier', 'Verdana', 'Georgia',
                    'Comic Sans MS', 'Trebuchet MS', 'Arial Black',
                    'Impact', 'Palatino', 'Garamond', 'Bookman',
                    'Avant Garde', 'sans-serif', 'serif', 'monospace'
                }

            logger.info(f"Discovered {len(system_fonts)} system fonts")
            return system_fonts

        except Exception as e:
            logger.warning(f"System font discovery failed: {e}")
            # Return minimal fallback set
            return {'Arial', 'Helvetica', 'sans-serif', 'serif', 'monospace'}

    def _create_font_detector(self):
        """Create font detector with graceful fallback."""
        try:
            # Try to import font detection libraries
            try:
                from fontTools.ttLib import TTFont
                from .font_detector import FontDetector
                return FontDetector()
            except ImportError:
                logger.debug("FontTools not available, using basic font detection")

            try:
                import matplotlib.font_manager as fm
                from .matplotlib_font_detector import MatplotlibFontDetector
                return MatplotlibFontDetector()
            except ImportError:
                logger.debug("Matplotlib not available for font detection")

            # Basic fallback detector
            from .basic_font_detector import BasicFontDetector
            return BasicFontDetector()

        except Exception as e:
            logger.warning(f"Could not create font detector: {e}")
            return None

    def _create_font_key(self, font_metadata: FontMetadata) -> str:
        """Create cache key for font metadata."""
        key_data = f"{font_metadata.family}:{font_metadata.weight}:{font_metadata.style}:{font_metadata.size_pt}"
        return hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()

    def _strategy_to_availability(self, strategy: FontStrategy) -> FontAvailability:
        """Convert font strategy to availability status."""
        mapping = {
            FontStrategy.EMBEDDED: FontAvailability.EMBEDDED,
            FontStrategy.SYSTEM: FontAvailability.AVAILABLE,
            FontStrategy.PATH: FontAvailability.UNAVAILABLE,
            FontStrategy.FALLBACK: FontAvailability.SYSTEM_FALLBACK
        }
        return mapping.get(strategy, FontAvailability.UNKNOWN)

    def register_embedded_font(self, font_family: str) -> None:
        """Register a font as embedded in the package."""
        self._embedded_fonts.add(font_family)
        logger.debug(f"Registered embedded font: {font_family}")

    def get_system_fonts(self) -> Set[str]:
        """Get set of available system fonts."""
        if self._system_fonts is None:
            self._system_fonts = self._discover_system_fonts()
        return self._system_fonts.copy()

    def clear_cache(self) -> None:
        """Clear all cached analysis results."""
        if self._cache:
            self._cache.clear()
            logger.debug("Font analysis cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self._cache:
            return {"caching_enabled": False}

        return {
            "caching_enabled": True,
            "cache_size": self._cache.size(),
            "max_size": self._config.cache_size_limit,
            "hit_rate": "Not tracked"  # Could be enhanced
        }

    # Utility methods for legacy compatibility
    @staticmethod
    def parse_css_font_weight(weight_str: str) -> int:
        """Parse CSS font weight string to numeric value."""
        return parse_font_weight(weight_str)

    @staticmethod
    def normalize_css_font_style(style_str: str) -> str:
        """Normalize CSS font style to PowerPoint-compatible value."""
        return normalize_font_style(style_str)

    @staticmethod
    def create_font_metadata_from_css(
        family: str,
        weight: Optional[str] = None,
        style: Optional[str] = None,
        size_pt: float = 12.0
    ) -> FontMetadata:
        """Create FontMetadata from CSS values."""
        return create_font_metadata(family, weight, style, size_pt)


# Factory function for service creation
def create_font_system(config: Optional[FontSystemConfig] = None) -> FontSystem:
    """
    Create FontSystem with configuration.

    Args:
        config: Optional configuration, uses defaults if not provided

    Returns:
        Configured FontSystem instance
    """
    return FontSystem(config)


# Basic font detector fallback
class BasicFontDetector:
    """Basic font detector that doesn't require external dependencies."""

    def __init__(self):
        self._common_fonts = {
            'Arial', 'Helvetica', 'Times New Roman', 'Times',
            'Courier New', 'Courier', 'Verdana', 'Georgia',
            'Comic Sans MS', 'Trebuchet MS', 'Arial Black',
            'Impact', 'Palatino', 'Garamond', 'sans-serif',
            'serif', 'monospace'
        }

    def find_font_file(self, family: str, weight: int, italic: bool) -> Optional[str]:
        """Basic font file detection (returns None - no embedding support)."""
        return None

    def list_system_fonts(self) -> List[str]:
        """Return list of commonly available fonts."""
        return list(self._common_fonts)