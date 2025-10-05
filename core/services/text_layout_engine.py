#!/usr/bin/env python3
"""
Text Layout Engine for Clean Slate Text Processing

Modern implementation of precise SVG to PowerPoint text layout conversion.
Replaces legacy text_layout.py with Clean Slate architecture principles.

Key Features:
- Precise SVG baseline to PowerPoint top-left conversion
- Font metrics integration for accurate positioning
- Text anchor handling (start/middle/end)
- Text measurement with font processor integration
- Immutable result structures with comprehensive metadata
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Tuple

from ..ir.font_metadata import FontMetadata, FontMetrics
from ..ir.geometry import Point, Rect
from ..ir.text import TextAnchor

logger = logging.getLogger(__name__)

# Constants
EMU_PER_POINT = 12700  # Standard EMU conversion
PX_TO_EMU_96DPI = 9525  # 1px = 9525 EMU at 96 DPI
DEFAULT_LINE_HEIGHT_MULTIPLIER = 1.2


class CoordinateSpace(Enum):
    """Coordinate space for layout calculations."""
    SVG = "svg"           # SVG coordinate space
    POWERPOINT = "ppt"    # PowerPoint coordinate space
    EMU = "emu"           # EMU units (PowerPoint native)


@dataclass(frozen=True)
class TextMeasurements:
    """Immutable text measurement results."""
    width_pt: float                    # Text width in points
    height_pt: float                   # Text height in points
    width_emu: int                     # Text width in EMU
    height_emu: int                    # Text height in EMU
    baseline_offset_pt: float          # Baseline offset from top
    baseline_offset_emu: int           # Baseline offset in EMU
    measurement_method: str = "estimated"  # Method used for measurement
    confidence: float = 0.8            # Confidence in measurements (0-1)

    @property
    def aspect_ratio(self) -> float:
        """Get aspect ratio (width/height)."""
        return self.width_pt / self.height_pt if self.height_pt > 0 else 1.0


@dataclass(frozen=True)
class TextLayoutResult:
    """Immutable text layout calculation result."""
    # Position in EMU (PowerPoint coordinates)
    x_emu: int                         # Left position
    y_emu: int                         # Top position
    width_emu: int                     # Text box width
    height_emu: int                    # Text box height

    # Original SVG coordinates
    svg_x: float                       # Original SVG X
    svg_y: float                       # Original SVG Y (baseline)
    anchor: TextAnchor                 # Text anchor used

    # Measurements and metadata
    measurements: TextMeasurements     # Text measurements
    font_metadata: FontMetadata        # Font information
    layout_time_ms: float             # Time taken for layout

    # Coordinate transformations
    baseline_x_emu: int               # Baseline X in EMU
    baseline_y_emu: int               # Baseline Y in EMU
    ascent_emu: int                   # Font ascent in EMU
    descent_emu: int                  # Font descent in EMU

    @property
    def bounds(self) -> Rect:
        """Get text bounds as Rect."""
        return Rect(
            x=float(self.x_emu),
            y=float(self.y_emu),
            width=float(self.width_emu),
            height=float(self.height_emu),
        )

    @property
    def center_point(self) -> Point:
        """Get center point of text box."""
        return Point(
            x=self.x_emu + (self.width_emu // 2),
            y=self.y_emu + (self.height_emu // 2),
        )

    @property
    def baseline_point(self) -> Point:
        """Get baseline point in EMU coordinates."""
        return Point(x=self.baseline_x_emu, y=self.baseline_y_emu)


class TextLayoutEngine:
    """
    Modern text layout engine for Clean Slate architecture.

    Provides precise SVG to PowerPoint text layout calculations with:
    - Font metrics integration
    - Accurate coordinate transformations
    - Text anchor positioning
    - Comprehensive measurement support
    """

    def __init__(self, unit_converter=None, font_processor=None):
        """
        Initialize text layout engine.

        Args:
            unit_converter: Service for unit conversions (optional)
            font_processor: Service for font metrics and measurements (optional)
        """
        self._unit_converter = unit_converter
        self._font_processor = font_processor
        self._measurement_cache: dict[str, TextMeasurements] = {}

        logger.debug("TextLayoutEngine initialized")

    def calculate_text_layout(
        self,
        svg_x: float,
        svg_y: float,
        text: str,
        font_metadata: FontMetadata,
        anchor: TextAnchor = TextAnchor.START,
    ) -> TextLayoutResult:
        """
        Calculate precise text layout for PowerPoint placement.

        Args:
            svg_x: SVG X coordinate
            svg_y: SVG Y coordinate (baseline)
            text: Text content
            font_metadata: Font information
            anchor: Text anchor positioning

        Returns:
            TextLayoutResult with precise positioning
        """
        import time
        start_time = time.perf_counter()

        try:
            # Step 1: Convert SVG coordinates to EMU
            baseline_x_emu, baseline_y_emu = self._convert_svg_to_emu(svg_x, svg_y)

            # Step 2: Get font metrics
            font_metrics = self._get_font_metrics(font_metadata)

            # Step 3: Measure text dimensions
            measurements = self._measure_text(text, font_metadata, font_metrics)

            # Step 4: Calculate ascent and descent in EMU
            ascent_emu = int(font_metadata.size_pt * font_metrics.ascent * EMU_PER_POINT)
            descent_emu = int(font_metadata.size_pt * font_metrics.descent * EMU_PER_POINT)

            # Step 5: Convert baseline to top-left (subtract ascent)
            y_top_emu = baseline_y_emu - ascent_emu

            # Step 6: Apply text anchor adjustment
            x_left_emu = self._apply_text_anchor(
                baseline_x_emu, measurements.width_emu, anchor,
            )

            # Step 7: Create result
            layout_time = (time.perf_counter() - start_time) * 1000

            result = TextLayoutResult(
                x_emu=x_left_emu,
                y_emu=y_top_emu,
                width_emu=measurements.width_emu,
                height_emu=measurements.height_emu,
                svg_x=svg_x,
                svg_y=svg_y,
                anchor=anchor,
                measurements=measurements,
                font_metadata=font_metadata,
                layout_time_ms=layout_time,
                baseline_x_emu=baseline_x_emu,
                baseline_y_emu=baseline_y_emu,
                ascent_emu=ascent_emu,
                descent_emu=descent_emu,
            )

            logger.debug(f"Text layout calculated in {layout_time:.2f}ms: "
                        f"({svg_x}, {svg_y}) -> ({x_left_emu}, {y_top_emu})")

            return result

        except Exception as e:
            logger.error(f"Text layout calculation failed: {e}")
            raise

    def _convert_svg_to_emu(self, svg_x: float, svg_y: float) -> tuple[int, int]:
        """
        Convert SVG coordinates to EMU units.

        Args:
            svg_x: SVG X coordinate
            svg_y: SVG Y coordinate

        Returns:
            Tuple of (x_emu, y_emu)
        """
        if self._unit_converter:
            # Use proper unit converter with unit suffixes
            try:
                x_emu = self._unit_converter.to_emu(f"{svg_x}px")
                y_emu = self._unit_converter.to_emu(f"{svg_y}px")
                return int(x_emu), int(y_emu)
            except Exception as e:
                logger.warning(f"Unit converter failed, using fallback: {e}")

        # Fallback conversion (96 DPI assumption)
        x_emu = int(svg_x * PX_TO_EMU_96DPI)
        y_emu = int(svg_y * PX_TO_EMU_96DPI)
        return x_emu, y_emu

    def _get_font_metrics(self, font_metadata: FontMetadata) -> FontMetrics:
        """
        Get font metrics for layout calculations.

        Args:
            font_metadata: Font information

        Returns:
            FontMetrics with ascent/descent information
        """
        # Use metrics from font metadata if available
        if font_metadata.metrics:
            return font_metadata.metrics

        # Try to get metrics from font processor
        if (self._font_processor and
                hasattr(self._font_processor, 'get_metrics')):
            try:
                processor_metrics = self._font_processor.get_metrics(font_metadata.family)
                if processor_metrics:
                    return FontMetrics(
                        ascent=getattr(processor_metrics, 'ascent', 0.8),
                        descent=getattr(processor_metrics, 'descent', 0.2),
                        line_height=getattr(processor_metrics, 'line_height', 1.2),
                    )
            except Exception as e:
                logger.debug(f"Font processor metrics failed: {e}")

        # Return default metrics
        return FontMetrics()

    def _measure_text(
        self,
        text: str,
        font_metadata: FontMetadata,
        font_metrics: FontMetrics,
    ) -> TextMeasurements:
        """
        Measure text dimensions.

        Args:
            text: Text content
            font_metadata: Font information
            font_metrics: Font metrics

        Returns:
            TextMeasurements with width and height
        """
        # Create cache key
        cache_key = f"{text}:{font_metadata.family}:{font_metadata.size_pt}:{font_metadata.weight}"

        # Check cache first
        if cache_key in self._measurement_cache:
            return self._measurement_cache[cache_key]

        # Try precise measurement with font processor
        if (self._font_processor and
                hasattr(self._font_processor, 'measure_text_width')):
            try:
                width_pt = self._font_processor.measure_text_width(
                    text, font_metadata.family, font_metadata.size_pt,
                )
                measurement_method = "font_processor"
                confidence = 0.95
            except Exception as e:
                logger.debug(f"Font processor measurement failed: {e}")
                width_pt = None
        else:
            width_pt = None

        # Fallback to estimation if precise measurement failed
        if width_pt is None:
            # Character-based estimation (average character width)
            avg_char_width = font_metadata.size_pt * 0.6  # Typical ratio
            width_pt = len(text) * avg_char_width
            measurement_method = "estimated"
            confidence = 0.7

        # Calculate height using font metrics
        line_height_pt = font_metadata.size_pt * font_metrics.line_height
        height_pt = line_height_pt

        # Convert to EMU
        width_emu = int(width_pt * EMU_PER_POINT)
        height_emu = int(height_pt * EMU_PER_POINT)

        # Calculate baseline offset
        baseline_offset_pt = font_metadata.size_pt * font_metrics.ascent
        baseline_offset_emu = int(baseline_offset_pt * EMU_PER_POINT)

        # Create measurements
        measurements = TextMeasurements(
            width_pt=width_pt,
            height_pt=height_pt,
            width_emu=width_emu,
            height_emu=height_emu,
            baseline_offset_pt=baseline_offset_pt,
            baseline_offset_emu=baseline_offset_emu,
            measurement_method=measurement_method,
            confidence=confidence,
        )

        # Cache result
        self._measurement_cache[cache_key] = measurements

        return measurements

    def _apply_text_anchor(self, baseline_x_emu: int, width_emu: int, anchor: TextAnchor) -> int:
        """
        Apply text anchor positioning.

        Args:
            baseline_x_emu: Baseline X position in EMU
            width_emu: Text width in EMU
            anchor: Text anchor

        Returns:
            Left X position in EMU
        """
        if anchor == TextAnchor.MIDDLE:
            return baseline_x_emu - (width_emu // 2)
        elif anchor == TextAnchor.END:
            return baseline_x_emu - width_emu
        else:  # START or None
            return baseline_x_emu

    def measure_text_only(
        self,
        text: str,
        font_metadata: FontMetadata,
    ) -> TextMeasurements:
        """
        Measure text dimensions without full layout calculation.

        Args:
            text: Text content
            font_metadata: Font information

        Returns:
            TextMeasurements with dimensions
        """
        font_metrics = self._get_font_metrics(font_metadata)
        return self._measure_text(text, font_metadata, font_metrics)

    def clear_measurement_cache(self) -> None:
        """Clear text measurement cache."""
        self._measurement_cache.clear()
        logger.debug("Text measurement cache cleared")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get measurement cache statistics."""
        return {
            "cache_size": len(self._measurement_cache),
            "cache_enabled": True,
        }


# Factory function for service creation
def create_text_layout_engine(unit_converter=None, font_processor=None) -> TextLayoutEngine:
    """
    Create TextLayoutEngine with services.

    Args:
        unit_converter: Unit conversion service (optional)
        font_processor: Font processing service (optional)

    Returns:
        Configured TextLayoutEngine instance
    """
    return TextLayoutEngine(unit_converter, font_processor)


# Legacy compatibility function
def svg_text_to_ppt_box_modern(
    svg_x: float,
    svg_y: float,
    anchor: str,
    text: str,
    font_family: str,
    font_size_pt: float,
    services=None,
) -> tuple[int, int, int, int]:
    """
    Modern replacement for legacy svg_text_to_ppt_box function.

    Provides same interface but uses modern TextLayoutEngine internally.
    """
    from ..ir.font_metadata import create_font_metadata
    from ..ir.text import TextAnchor

    # Convert legacy anchor string to TextAnchor enum
    anchor_map = {
        'start': TextAnchor.START,
        'middle': TextAnchor.MIDDLE,
        'end': TextAnchor.END,
    }
    text_anchor = anchor_map.get(anchor, TextAnchor.START)

    # Create font metadata
    font_metadata = create_font_metadata(font_family, size_pt=font_size_pt)

    # Extract services
    unit_converter = getattr(services, 'unit_converter', None) if services else None
    font_processor = getattr(services, 'font_processor', None) if services else None

    # Create layout engine
    layout_engine = TextLayoutEngine(unit_converter, font_processor)

    # Calculate layout
    result = layout_engine.calculate_text_layout(
        svg_x, svg_y, text, font_metadata, text_anchor,
    )

    # Return in legacy format
    return result.x_emu, result.y_emu, result.width_emu, result.height_emu