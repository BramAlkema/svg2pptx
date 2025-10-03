#!/usr/bin/env python3
"""
System Font Handler

Handles text conversion using system-available fonts.
Optimized for simple text with standard fonts available in PowerPoint.
"""

import logging
from typing import Dict, Any

from ....ir import TextFrame
from ....ir.font_metadata import FontStrategy, FontAvailability
from ....services.conversion_services import ConversionServices
from ..types import HandlerResult
from .base import BaseStrategyHandler


class SystemFontHandler(BaseStrategyHandler):
    """
    Handler for system-available fonts.

    Uses fonts that are available on the system and can be directly
    referenced in PowerPoint without embedding. This is the most
    efficient strategy for common fonts.
    """

    def __init__(self, services: ConversionServices):
        """
        Initialize system font handler.

        Args:
            services: ConversionServices container
        """
        super().__init__(services)
        self.logger = logging.getLogger(__name__)

        # Cache for font availability checks
        self._font_availability_cache = {}

        # Common system fonts that are widely available
        self.common_system_fonts = {
            'Arial', 'Helvetica', 'Times New Roman', 'Times',
            'Courier New', 'Courier', 'Verdana', 'Georgia',
            'Tahoma', 'Comic Sans MS', 'Impact', 'Trebuchet MS',
            'Calibri', 'Cambria', 'Consolas', 'Constantia',
            'Corbel', 'Candara'
        }

    def can_handle(self, text_frame: TextFrame, context: Dict[str, Any]) -> bool:
        """
        Check if this handler can process the text frame.

        System font handler can handle text when:
        1. Font is available in the system
        2. Text complexity is simple to moderate
        3. No special effects requiring other strategies

        Args:
            text_frame: Text frame to check
            context: Conversion context

        Returns:
            True if handler can process this text frame
        """
        try:
            # Must have at least one run
            if not text_frame.runs:
                return False

            # Check font availability for primary font
            primary_font = text_frame.runs[0].font_family
            if not self._is_font_available(primary_font):
                self.logger.debug(f"Font {primary_font} not available in system")
                return False

            # Check for complex features that require other strategies
            if self._has_complex_features(text_frame, context):
                self.logger.debug("Text has complex features, system font handler cannot handle")
                return False

            # Check if policy forces other strategies
            if context.get('force_wordart', False) or context.get('force_text_to_path', False):
                self.logger.debug("Policy forces alternative strategy")
                return False

            return True

        except Exception as e:
            self.logger.warning(f"Error in can_handle check: {e}")
            return False

    def convert(self, text_frame: TextFrame, context: Dict[str, Any]) -> HandlerResult:
        """
        Convert text frame using system fonts.

        Args:
            text_frame: Text frame to convert
            context: Conversion context

        Returns:
            HandlerResult with DrawingML text shape
        """
        try:
            self.logger.debug(f"Converting text using system fonts: {[run.font_family for run in text_frame.runs]}")

            # Extract positioning and size information
            bounds = self._calculate_bounds(text_frame)

            # Map SVG fonts to PowerPoint equivalents
            self._map_fonts_to_powerpoint(text_frame)

            # Generate DrawingML for text shape
            xml_content = self._generate_text_shape_xml(text_frame, bounds, context)

            # Calculate confidence based on font availability and complexity
            confidence = self._calculate_confidence(text_frame, context)

            # Generate metadata
            metadata = {
                'strategy': 'system_font',
                'fonts_used': list(set(run.font_family for run in text_frame.runs)),
                'font_availability': {
                    font: self._is_font_available(font)
                    for font in set(run.font_family for run in text_frame.runs)
                },
                'bounds': bounds,
                'run_count': len(text_frame.runs)
            }

            return HandlerResult(
                success=True,
                xml_content=xml_content,
                confidence=confidence,
                metadata=metadata
            )

        except Exception as e:
            self.logger.error(f"System font conversion failed: {e}")
            return HandlerResult(
                success=False,
                xml_content="",
                confidence=0.0,
                error=e,
                warnings=[f"System font conversion failed: {str(e)}"]
            )

    def _is_font_available(self, font_family: str) -> bool:
        """
        Check if font is available in the system.

        Args:
            font_family: Font family name to check

        Returns:
            True if font is available
        """
        if not font_family:
            return False

        # Check cache first
        if font_family in self._font_availability_cache:
            return self._font_availability_cache[font_family]

        # Use font service to check availability
        try:
            # Map to PowerPoint equivalent first
            mapped_font = self.services.font_service.map_svg_font_to_ppt(font_family)

            # Check if it's a common system font
            if mapped_font in self.common_system_fonts:
                self._font_availability_cache[font_family] = True
                return True

            # Use font service to find font file
            font_file = self.services.font_service.find_font_file(mapped_font)
            available = font_file is not None

            self._font_availability_cache[font_family] = available
            return available

        except Exception as e:
            self.logger.warning(f"Font availability check failed for {font_family}: {e}")
            # Conservative default - check if it's a common font
            available = font_family in self.common_system_fonts
            self._font_availability_cache[font_family] = available
            return available

    def _has_complex_features(self, text_frame: TextFrame, context: Dict[str, Any]) -> bool:
        """
        Check if text frame has features that require specialized handling.

        Args:
            text_frame: Text frame to analyze
            context: Conversion context

        Returns:
            True if text has complex features
        """
        # Check for transforms that might affect text rendering
        if hasattr(text_frame, 'transform') and text_frame.transform is not None:
            # Simple transforms (translate, scale) are OK, but rotation/skew need special handling
            transform = text_frame.transform
            if hasattr(transform, 'rotation') and transform.rotation is not None:
                try:
                    if abs(float(transform.rotation)) > 0.1:
                        return True
                except (TypeError, ValueError):
                    # If rotation is not a number, consider it complex
                    return True
            if hasattr(transform, 'skew_x') and transform.skew_x is not None:
                try:
                    if abs(float(transform.skew_x)) > 0.1:
                        return True
                except (TypeError, ValueError):
                    return True
            if hasattr(transform, 'skew_y') and transform.skew_y is not None:
                try:
                    if abs(float(transform.skew_y)) > 0.1:
                        return True
                except (TypeError, ValueError):
                    return True

        # Check for text on path
        if hasattr(text_frame, 'text_path') and text_frame.text_path is not None:
            return True

        # Check for advanced text effects
        for run in text_frame.runs:
            # Complex decorations
            if hasattr(run, 'text_decoration') and run.text_decoration:
                try:
                    if 'line-through' in str(run.text_decoration) or 'overline' in str(run.text_decoration):
                        return True
                except (TypeError, AttributeError):
                    # If text_decoration is not a string/iterable, skip
                    pass

            # Text shadows or outlines
            if hasattr(run, 'text_shadow') and run.text_shadow:
                return True
            if hasattr(run, 'text_outline') and run.text_outline:
                return True

        # Multiple fonts in single frame (might need WordArt)
        fonts = set(run.font_family for run in text_frame.runs)
        if len(fonts) > 2:
            return True

        # Very large or very small text sizes
        font_sizes = [run.font_size_pt for run in text_frame.runs]
        if any(size < 6 or size > 72 for size in font_sizes):
            return True

        return False

    def _map_fonts_to_powerpoint(self, text_frame: TextFrame):
        """
        Map SVG font families to PowerPoint-compatible equivalents.

        Args:
            text_frame: Text frame to process (modified in place)
        """
        for run in text_frame.runs:
            mapped_font = self.services.font_service.map_svg_font_to_ppt(run.font_family)
            run.font_family = mapped_font

    def _generate_text_shape_xml(self, text_frame: TextFrame, bounds: Dict[str, float],
                                context: Dict[str, Any]) -> str:
        """
        Generate DrawingML XML for text shape using system fonts.

        Args:
            text_frame: Text frame to convert
            bounds: Text bounds in EMU
            context: Conversion context

        Returns:
            DrawingML XML string
        """
        # Generate shape properties
        shape_props = self._generate_shape_properties(bounds)

        # Generate text body with optimized properties for system fonts
        text_body = self._generate_text_body(text_frame)

        # Generate non-visual properties
        nv_props = self._generate_non_visual_properties()

        return f"""
            <p:sp>
                {nv_props}
                {shape_props}
                {text_body}
            </p:sp>
        """

    def _generate_text_body(self, text_frame: TextFrame) -> str:
        """
        Generate text body XML optimized for system fonts.

        Args:
            text_frame: Text frame to convert

        Returns:
            Text body XML string
        """
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

        # Generate paragraphs
        paragraphs = self._generate_paragraphs_for_system_fonts(text_frame)

        return f"""
            <p:txBody>
                <a:bodyPr wrap="square" rtlCol="0" anchor="t" anchoring="{anchor}">
                    <a:spAutoFit/>
                </a:bodyPr>
                <a:lstStyle/>
                {paragraphs}
            </p:txBody>
        """

    def _generate_paragraphs_for_system_fonts(self, text_frame: TextFrame) -> str:
        """
        Generate paragraph XML optimized for system fonts.

        Args:
            text_frame: Text frame to convert

        Returns:
            Paragraphs XML string
        """
        paragraphs = []

        for run in text_frame.runs:
            run_xml = self._generate_system_font_run(run)
            paragraphs.append(f"""
                <a:p>
                    <a:pPr algn="l"/>
                    {run_xml}
                </a:p>
            """)

        return '\n'.join(paragraphs)

    def _generate_system_font_run(self, run) -> str:
        """
        Generate text run XML optimized for system fonts.

        Args:
            run: Text run to convert

        Returns:
            Text run XML string
        """
        # Font size in 100ths of a point (PowerPoint standard)
        font_size_emu = int(run.font_size_pt * 100)

        # Format styling attributes
        bold = 'b="1"' if run.bold else ''
        italic = 'i="1"' if run.italic else ''
        underline = 'u="sng"' if run.underline else ''
        strike = 'strike="sngStrike"' if run.strike else ''

        # Ensure font family is properly escaped
        font_family = self._escape_xml(run.font_family)

        # Use system font with explicit typeface mapping
        return f"""
            <a:r>
                <a:rPr lang="en-US" sz="{font_size_emu}" {bold} {italic} {underline} {strike}>
                    <a:solidFill>
                        <a:srgbClr val="{run.rgb}"/>
                    </a:solidFill>
                    <a:latin typeface="{font_family}"/>
                    <a:ea typeface="{font_family}"/>
                    <a:cs typeface="{font_family}"/>
                </a:rPr>
                <a:t>{self._escape_xml(run.text)}</a:t>
            </a:r>
        """

    def _generate_non_visual_properties(self) -> str:
        """
        Generate non-visual shape properties.

        Returns:
            Non-visual properties XML string
        """
        import uuid
        shape_id = str(uuid.uuid4())[:8]

        return f"""
            <p:nvSpPr>
                <p:cNvPr id="2" name="TextBox_{shape_id}"/>
                <p:cNvSpPr txBox="1"/>
                <p:nvPr/>
            </p:nvSpPr>
        """

    def _calculate_confidence(self, text_frame: TextFrame, context: Dict[str, Any]) -> float:
        """
        Calculate confidence score for system font conversion.

        Args:
            text_frame: Text frame being converted
            context: Conversion context

        Returns:
            Confidence score (0.0 - 1.0)
        """
        confidence = 0.8  # Base confidence for system fonts

        # Boost confidence for common fonts
        fonts = set(run.font_family for run in text_frame.runs)
        common_font_ratio = len(fonts & self.common_system_fonts) / len(fonts)
        confidence += common_font_ratio * 0.15

        # Reduce confidence for complex text
        if len(text_frame.runs) > 3:
            confidence -= 0.1

        # Reduce confidence for mixed font sizes
        font_sizes = set(run.font_size_pt for run in text_frame.runs)
        if len(font_sizes) > 2:
            confidence -= 0.05

        # Boost confidence if all fonts are definitely available
        all_available = all(self._is_font_available(font) for font in fonts)
        if all_available:
            confidence += 0.1

        return max(0.0, min(1.0, confidence))

    def get_supported_features(self) -> Dict[str, bool]:
        """
        Get dictionary of features supported by this handler.

        Returns:
            Dictionary mapping feature names to support status
        """
        return {
            'system_fonts': True,
            'basic_styling': True,      # bold, italic, underline
            'color_text': True,
            'multiple_runs': True,
            'font_embedding': False,    # System fonts don't need embedding
            'text_transforms': False,   # Complex transforms need other handlers
            'text_effects': False,      # Advanced effects need other handlers
            'text_on_path': False,      # Path text needs specialized handler
            'wordart_effects': False    # WordArt needs dedicated handler
        }

    def clear_cache(self):
        """Clear internal caches."""
        self._font_availability_cache.clear()
        self.logger.debug("Cleared system font handler caches")