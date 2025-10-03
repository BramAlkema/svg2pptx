#!/usr/bin/env python3
"""
Base handler for font conversion strategies

Abstract base class that all strategy handlers must implement.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging
import time

from ....ir import TextFrame
from ....services.conversion_services import ConversionServices
from ..types import HandlerResult


class BaseStrategyHandler(ABC):
    """
    Abstract base class for font conversion strategy handlers.

    Each handler implements a specific font rendering strategy
    (system fonts, WordArt, text-to-path, etc.).
    """

    def __init__(self, services: ConversionServices):
        """
        Initialize handler with conversion services.

        Args:
            services: ConversionServices container
        """
        self.services = services
        self.logger = logging.getLogger(self.__class__.__name__)

        # Performance tracking
        self.stats = {
            'total_conversions': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'total_time_ms': 0.0,
            'average_time_ms': 0.0
        }

    @abstractmethod
    def can_handle(self, text_frame: TextFrame, context: Dict[str, Any]) -> bool:
        """
        Check if this handler can process the given text frame.

        Args:
            text_frame: Text frame to check
            context: Conversion context with additional information

        Returns:
            True if handler can process this text frame
        """
        pass

    @abstractmethod
    def convert(self, text_frame: TextFrame, context: Dict[str, Any]) -> HandlerResult:
        """
        Convert text frame to DrawingML using this strategy.

        Args:
            text_frame: Text frame to convert
            context: Conversion context with additional information

        Returns:
            HandlerResult with XML content and metadata
        """
        pass

    def execute(self, text_frame: TextFrame, context: Optional[Dict[str, Any]] = None) -> HandlerResult:
        """
        Execute conversion with error handling and statistics tracking.

        Args:
            text_frame: Text frame to convert
            context: Optional conversion context

        Returns:
            HandlerResult with XML content or error information
        """
        start_time = time.perf_counter()
        context = context or {}

        try:
            # Check if handler can process this text
            if not self.can_handle(text_frame, context):
                return HandlerResult(
                    success=False,
                    xml_content="",
                    confidence=0.0,
                    warnings=[f"{self.__class__.__name__} cannot handle this text frame"]
                )

            # Execute conversion
            result = self.convert(text_frame, context)

            # Track statistics
            if result.success:
                self.stats['successful_conversions'] += 1
            else:
                self.stats['failed_conversions'] += 1

            return result

        except Exception as e:
            self.logger.error(f"Handler execution failed: {e}")
            self.stats['failed_conversions'] += 1

            return HandlerResult(
                success=False,
                xml_content="",
                confidence=0.0,
                error=e,
                warnings=[f"Handler execution failed: {str(e)}"]
            )

        finally:
            # Update statistics
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self.stats['total_conversions'] += 1
            self.stats['total_time_ms'] += elapsed_ms
            if self.stats['total_conversions'] > 0:
                self.stats['average_time_ms'] = (
                    self.stats['total_time_ms'] / self.stats['total_conversions']
                )

    def get_statistics(self) -> Dict[str, Any]:
        """Get handler performance statistics."""
        return self.stats.copy()

    def reset_statistics(self):
        """Reset handler statistics."""
        self.stats = {
            'total_conversions': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'total_time_ms': 0.0,
            'average_time_ms': 0.0
        }

    # Helper methods for subclasses

    def _extract_font_info(self, text_frame: TextFrame) -> Dict[str, Any]:
        """Extract font information from text frame."""
        fonts = set()
        for run in text_frame.runs:
            fonts.add(run.font_family)

        return {
            'primary_font': text_frame.runs[0].font_family if text_frame.runs else 'Arial',
            'all_fonts': list(fonts),
            'has_multiple_fonts': len(fonts) > 1
        }

    def _calculate_bounds(self, text_frame: TextFrame) -> Dict[str, float]:
        """Calculate text bounds in EMU."""
        EMU_PER_POINT = 12700

        # Use bbox if available
        if text_frame.bbox:
            return {
                'x': text_frame.bbox.x,
                'y': text_frame.bbox.y,
                'width': text_frame.bbox.width,
                'height': text_frame.bbox.height
            }

        # Estimate bounds based on text content
        total_height = sum(run.font_size_pt * 1.2 for run in text_frame.runs)
        max_width = max(
            len(run.text) * run.font_size_pt * 0.6
            for run in text_frame.runs
        ) if text_frame.runs else 100

        return {
            'x': text_frame.origin.x,
            'y': text_frame.origin.y,
            'width': max_width * EMU_PER_POINT,
            'height': total_height * EMU_PER_POINT
        }

    def _generate_shape_properties(self, bounds: Dict[str, float]) -> str:
        """Generate common shape properties XML."""
        return f"""
            <p:spPr>
                <a:xfrm>
                    <a:off x="{int(bounds['x'])}" y="{int(bounds['y'])}"/>
                    <a:ext cx="{int(bounds['width'])}" cy="{int(bounds['height'])}"/>
                </a:xfrm>
                <a:prstGeom prst="rect">
                    <a:avLst/>
                </a:prstGeom>
            </p:spPr>
        """

    def _generate_text_properties(self, text_frame: TextFrame) -> str:
        """Generate common text properties XML."""
        # Map TextAnchor to DrawingML alignment
        anchor_map = {
            'start': 'l',
            'middle': 'ctr',
            'end': 'r'
        }

        anchor = anchor_map.get(
            text_frame.anchor.value if hasattr(text_frame.anchor, 'value') else str(text_frame.anchor),
            'l'
        )

        return f"""
            <p:txBody>
                <a:bodyPr wrap="square" rtlCol="0" anchor="{anchor}">
                    <a:spAutoFit/>
                </a:bodyPr>
                <a:lstStyle/>
                {self._generate_paragraphs(text_frame)}
            </p:txBody>
        """

    def _generate_paragraphs(self, text_frame: TextFrame) -> str:
        """Generate paragraph XML for text runs."""
        paragraphs = []

        for run in text_frame.runs:
            run_xml = self._generate_text_run(run)
            paragraphs.append(f"""
                <a:p>
                    <a:pPr algn="l"/>
                    {run_xml}
                </a:p>
            """)

        return '\n'.join(paragraphs)

    def _generate_text_run(self, run) -> str:
        """Generate text run XML."""
        EMU_PER_POINT = 12700
        font_size_emu = int(run.font_size_pt * 100)  # Font size in 100ths of a point

        bold = 'b="1"' if run.bold else ''
        italic = 'i="1"' if run.italic else ''
        underline = 'u="sng"' if run.underline else ''
        strike = 'strike="sngStrike"' if run.strike else ''

        return f"""
            <a:r>
                <a:rPr lang="en-US" sz="{font_size_emu}" {bold} {italic} {underline} {strike}>
                    <a:solidFill>
                        <a:srgbClr val="{run.rgb}"/>
                    </a:solidFill>
                    <a:latin typeface="{run.font_family}"/>
                </a:rPr>
                <a:t>{self._escape_xml(run.text)}</a:t>
            </a:r>
        """

    def _escape_xml(self, text: str) -> str:
        """Escape special XML characters."""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&apos;'))