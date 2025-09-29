#!/usr/bin/env python3
"""
Text-to-Path Processor for Clean Slate Architecture

Refactored from legacy src/converters/text_to_path.py, providing sophisticated
font fallback detection and automatic text-to-path conversion for better
PowerPoint compatibility when fonts are unavailable.

Key Features:
- Intelligent font availability detection
- Automatic fallback chain analysis
- Text-to-path conversion with layout preservation
- Integration with Clean Slate FontSystem and TextLayoutEngine
- Performance tracking and analytics
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Import Clean Slate components
from ..ir.text import Run, TextAnchor
from ..ir.font_metadata import FontMetadata, create_font_metadata
from ..ir.geometry import Point

logger = logging.getLogger(__name__)


class FontFallbackStrategy(Enum):
    """Font fallback strategies."""
    SYSTEM_FONTS = "system_fonts"
    UNIVERSAL_FALLBACK = "universal_fallback"
    PATH_CONVERSION = "path_conversion"


@dataclass
class FontDetectionResult:
    """Result of font availability detection."""
    primary_font_available: bool
    available_fonts: List[str]
    fallback_chain: List[str]
    confidence_score: float
    recommended_strategy: FontFallbackStrategy


@dataclass
class TextToPathResult:
    """Result of text-to-path conversion processing."""
    should_convert_to_path: bool
    conversion_strategy: FontFallbackStrategy
    font_detection: FontDetectionResult
    path_data: Optional[str]
    processing_time_ms: float
    metadata: Dict[str, Any]


class TextToPathProcessor:
    """
    Modern text-to-path processor using Clean Slate architecture.

    Analyzes font availability and provides intelligent fallback strategies,
    including automatic text-to-path conversion when needed.
    """

    def __init__(self, font_system=None, text_layout_engine=None, path_generator=None):
        """
        Initialize text-to-path processor with Clean Slate services.

        Args:
            font_system: FontSystem for font analysis
            text_layout_engine: TextLayoutEngine for text measurement
            path_generator: Path generation service for text vectorization
        """
        self.logger = logging.getLogger(__name__)
        self.font_system = font_system
        self.text_layout_engine = text_layout_engine
        self.path_generator = path_generator

        # Configuration for conversion decisions
        self.config = {
            'font_detection_enabled': True,
            'fallback_confidence_threshold': 0.8,
            'universal_fallback_fonts': ['Arial', 'Times New Roman', 'Helvetica', 'Calibri'],
            'path_conversion_threshold': 0.6,
            'cache_size': 256
        }

        # Performance tracking
        self.stats = {
            'total_assessments': 0,
            'path_conversions': 0,
            'fallback_used': 0,
            'system_fonts_used': 0,
            'cache_hits': 0
        }

        # Font availability cache
        self._font_cache = {}

        # Initialize fallback services if needed
        if not self.font_system:
            try:
                from .font_system import create_font_system
                self.font_system = create_font_system()
            except ImportError:
                self.logger.warning("FontSystem not available")

        if not self.text_layout_engine:
            try:
                from .text_layout_engine import create_text_layout_engine
                self.text_layout_engine = create_text_layout_engine()
            except ImportError:
                self.logger.warning("TextLayoutEngine not available")

    def assess_text_conversion_strategy(self, text_content: str, font_families: List[str],
                                      font_size: float = 12.0) -> TextToPathResult:
        """
        Assess optimal conversion strategy for text with specified fonts.

        Args:
            text_content: Text content to analyze
            font_families: List of requested font families (in priority order)
            font_size: Font size in points

        Returns:
            TextToPathResult with recommended strategy and analysis
        """
        import time
        start_time = time.perf_counter()

        try:
            self.stats['total_assessments'] += 1

            # Step 1: Detect font availability
            font_detection = self._detect_font_availability(font_families)

            # Step 2: Analyze text complexity
            text_complexity = self._analyze_text_complexity(text_content)

            # Step 3: Determine optimal strategy
            strategy = self._determine_conversion_strategy(
                font_detection, text_complexity, font_size
            )

            # Step 4: Track strategy statistics (don't generate path data in assessment)
            path_data = None  # Assessment doesn't generate actual paths
            if strategy == FontFallbackStrategy.PATH_CONVERSION:
                self.stats['path_conversions'] += 1
            elif strategy == FontFallbackStrategy.UNIVERSAL_FALLBACK:
                self.stats['fallback_used'] += 1
            else:
                self.stats['system_fonts_used'] += 1

            processing_time = (time.perf_counter() - start_time) * 1000

            return TextToPathResult(
                should_convert_to_path=(strategy == FontFallbackStrategy.PATH_CONVERSION),
                conversion_strategy=strategy,
                font_detection=font_detection,
                path_data=path_data,
                processing_time_ms=processing_time,
                metadata={
                    'text_complexity': text_complexity,
                    'font_size': font_size,
                    'cache_used': any(f in self._font_cache for f in font_families)
                }
            )

        except Exception as e:
            self.logger.error(f"Text conversion assessment failed: {e}")
            # Return safe fallback
            return TextToPathResult(
                should_convert_to_path=True,
                conversion_strategy=FontFallbackStrategy.PATH_CONVERSION,
                font_detection=FontDetectionResult(
                    primary_font_available=False,
                    available_fonts=[],
                    fallback_chain=[],
                    confidence_score=0.0,
                    recommended_strategy=FontFallbackStrategy.PATH_CONVERSION
                ),
                path_data=None,
                processing_time_ms=(time.perf_counter() - start_time) * 1000,
                metadata={'error': str(e)}
            )

    def _detect_font_availability(self, font_families: List[str]) -> FontDetectionResult:
        """Detect availability of requested fonts."""
        available_fonts = []
        fallback_chain = []

        # Check each requested font
        for font_family in font_families:
            if self._is_font_available(font_family):
                available_fonts.append(font_family)
                if not fallback_chain:  # First available font becomes primary
                    fallback_chain.append(font_family)

        # Add universal fallbacks if no fonts available
        if not available_fonts:
            for fallback_font in self.config['universal_fallback_fonts']:
                if self._is_font_available(fallback_font):
                    fallback_chain.append(fallback_font)
                    break

        # Calculate confidence score
        primary_available = len(available_fonts) > 0
        confidence = 1.0 if primary_available else (0.6 if fallback_chain else 0.0)

        # Determine recommended strategy
        if primary_available:
            strategy = FontFallbackStrategy.SYSTEM_FONTS
        elif fallback_chain:
            strategy = FontFallbackStrategy.UNIVERSAL_FALLBACK
        else:
            strategy = FontFallbackStrategy.PATH_CONVERSION

        return FontDetectionResult(
            primary_font_available=primary_available,
            available_fonts=available_fonts,
            fallback_chain=fallback_chain,
            confidence_score=confidence,
            recommended_strategy=strategy
        )

    def _is_font_available(self, font_family: str) -> bool:
        """Check if font is available on the system."""
        # Check cache first
        if font_family in self._font_cache:
            self.stats['cache_hits'] += 1
            return self._font_cache[font_family]

        # Use FontSystem if available
        if self.font_system:
            try:
                is_available = self.font_system.is_font_available(font_family)
                self._font_cache[font_family] = is_available
                return is_available
            except Exception as e:
                self.logger.debug(f"FontSystem check failed for {font_family}: {e}")

        # Fallback to simple heuristics
        is_available = self._basic_font_check(font_family)
        self._font_cache[font_family] = is_available
        return is_available

    def _basic_font_check(self, font_family: str) -> bool:
        """Basic font availability check using common font names."""
        # Normalize font name
        normalized = font_family.lower().strip()

        # Common system fonts that are usually available
        common_fonts = {
            'arial', 'helvetica', 'times', 'times new roman', 'calibri',
            'verdana', 'georgia', 'courier', 'courier new', 'trebuchet ms',
            'comic sans ms', 'impact', 'lucida grande', 'tahoma',
            'palatino', 'garamond', 'bookman', 'avant garde'
        }

        return normalized in common_fonts

    def _analyze_text_complexity(self, text_content: str) -> Dict[str, Any]:
        """Analyze text complexity for conversion decisions."""
        return {
            'character_count': len(text_content),
            'line_count': text_content.count('\n') + 1,
            'has_unicode': any(ord(c) > 127 for c in text_content),
            'has_special_chars': bool(re.search(r'[^\w\s\-.,!?;:]', text_content)),
            'complexity_score': min(10, len(text_content) // 10 + text_content.count('\n'))
        }

    def _determine_conversion_strategy(self, font_detection: FontDetectionResult,
                                     text_complexity: Dict[str, Any],
                                     font_size: float) -> FontFallbackStrategy:
        """Determine optimal conversion strategy based on analysis."""

        # If primary fonts available and text is simple, use system fonts
        if (font_detection.primary_font_available and
            text_complexity['complexity_score'] <= 5 and
            font_size >= 8.0):
            return FontFallbackStrategy.SYSTEM_FONTS

        # If good fallback available and not too complex, use fallback
        if (font_detection.fallback_chain and
            font_detection.confidence_score >= self.config['fallback_confidence_threshold'] and
            text_complexity['complexity_score'] <= 7):
            return FontFallbackStrategy.UNIVERSAL_FALLBACK

        # For complex text, small fonts, or no good fonts, convert to path
        return FontFallbackStrategy.PATH_CONVERSION

    def convert_text_to_path(self, text_content: str, font_families: List[str],
                           font_size: float) -> Optional[str]:
        """
        Actually convert text to path data.

        This method performs the actual conversion, unlike assess_text_conversion_strategy
        which only analyzes and recommends a strategy.
        """
        return self._generate_text_path_data(text_content, font_families, font_size)

    def _generate_text_path_data(self, text_content: str, font_families: List[str],
                               font_size: float) -> Optional[str]:
        """Generate SVG path data for text content."""
        try:
            # Use path generator if available
            if self.path_generator:
                return self.path_generator.generate_text_path(
                    text_content, font_families, font_size
                )

            # Use text layout engine for measurement and approximation
            if self.text_layout_engine:
                font_metadata = create_font_metadata(
                    font_families[0] if font_families else 'Arial',
                    size_pt=font_size
                )
                measurements = self.text_layout_engine.measure_text_only(text_content, font_metadata)

                # Create simple rectangular path as fallback
                width = measurements.width_pt
                height = measurements.height_pt
                return f"M 0 0 L {width} 0 L {width} {height} L 0 {height} Z"

            # Basic fallback path
            char_width = font_size * 0.6  # Rough estimation
            total_width = len(text_content) * char_width
            return f"M 0 0 L {total_width} 0 L {total_width} {font_size} L 0 {font_size} Z"

        except Exception as e:
            self.logger.warning(f"Path generation failed: {e}")
            return None

    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics and capabilities."""
        return {
            'statistics': dict(self.stats),
            'services_available': {
                'font_system': self.font_system is not None,
                'text_layout_engine': self.text_layout_engine is not None,
                'path_generator': self.path_generator is not None
            },
            'capabilities': {
                'font_detection': True,
                'fallback_analysis': True,
                'path_generation': self.path_generator is not None,
                'text_measurement': self.text_layout_engine is not None,
                'font_availability_check': self.font_system is not None
            },
            'configuration': dict(self.config),
            'cache_size': len(self._font_cache)
        }

    def clear_cache(self):
        """Clear font availability cache."""
        self._font_cache.clear()
        self.logger.info("Font availability cache cleared")


def create_text_to_path_processor(font_system=None, text_layout_engine=None,
                                path_generator=None) -> TextToPathProcessor:
    """
    Create text-to-path processor with services.

    Args:
        font_system: FontSystem service (optional)
        text_layout_engine: TextLayoutEngine service (optional)
        path_generator: Path generation service (optional)

    Returns:
        Configured TextToPathProcessor instance
    """
    return TextToPathProcessor(font_system, text_layout_engine, path_generator)