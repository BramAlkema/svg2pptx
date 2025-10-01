#!/usr/bin/env python3
"""
Fallback Handler

The ultimate fallback handler for text conversion when all other font strategies
fail. This handler always succeeds by creating basic text shapes with guaranteed
available fonts and simple styling.

This is the final handler in the font strategy chain and serves as the safety net
to ensure text conversion never completely fails.
"""

import logging
from typing import Dict, Any

from ....ir import TextFrame
from ....ir.font_metadata import FontStrategy
from ....services.conversion_services import ConversionServices
from ..types import HandlerResult
from .base import BaseStrategyHandler


class FallbackHandler(BaseStrategyHandler):
    """
    Ultimate fallback handler for text conversion.

    This handler provides guaranteed success by:
    1. Using only universally available fonts
    2. Applying minimal styling to avoid compatibility issues
    3. Creating basic text shapes that work in all PowerPoint versions
    4. Never failing - always produces usable output

    This is typically the last handler tried when all other strategies
    have been exhausted or deemed unsuitable.
    """

    def __init__(self, services: ConversionServices):
        """
        Initialize fallback handler.

        Args:
            services: ConversionServices container
        """
        super().__init__(services)
        self.logger = logging.getLogger(__name__)

        # Universally available fonts (safe fallbacks)
        self.universal_fonts = [
            'Arial',           # Most widely available
            'Times New Roman', # Default serif
            'Calibri',        # Modern PowerPoint default
            'sans-serif',     # CSS generic fallback
            'serif'           # CSS generic fallback
        ]

        # Safe color palette (high contrast, compatible)
        self.safe_colors = {
            'black': '000000',
            'white': 'FFFFFF',
            'dark_gray': '404040',
            'light_gray': '808080'
        }

    def _to_emu(self, value: float) -> int:
        """Convert value to EMU (914,400 EMU per inch, assuming 96 DPI)"""
        return int(value * 914400 / 96)

    def _to_emu_coords(self, x: float, y: float) -> tuple:
        """Convert coordinate pair to EMU"""
        return self._to_emu(x), self._to_emu(y)

    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters"""
        return (text.replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                    .replace("'", '&apos;'))

    def can_handle(self, text_frame: TextFrame, context: Dict[str, Any]) -> bool:
        """
        Check if this handler can process the text frame.

        The fallback handler can always handle any text frame - it's the
        ultimate safety net. It should only be used when other strategies
        have failed or are unavailable.

        Args:
            text_frame: Text frame to check
            context: Conversion context

        Returns:
            Always True - fallback handler never refuses
        """
        try:
            # Fallback handler always accepts, but it should be last resort
            if not text_frame.runs:
                self.logger.warning("Fallback handler accepting empty text frame")
                return True

            # Log that we're falling back
            self.logger.info(f"Fallback handler accepting text: {[run.text for run in text_frame.runs]}")
            return True

        except Exception as e:
            # Even exceptions don't stop the fallback handler
            self.logger.error(f"Exception in fallback can_handle, but still accepting: {e}")
            return True

    def convert(self, text_frame: TextFrame, context: Dict[str, Any]) -> HandlerResult:
        """
        Convert text frame using guaranteed fallback approach.

        This method never fails - it always produces a usable text shape
        even in the worst circumstances.

        Args:
            text_frame: Text frame to convert
            context: Conversion context

        Returns:
            HandlerResult with basic text shape (always successful)
        """
        try:
            self.logger.info("Converting text using fallback strategy")

            # Extract basic text content
            text_content = self._extract_safe_text_content(text_frame)

            # Use safe fonts and styling
            safe_font = self._select_safe_font(text_frame)
            safe_size = self._select_safe_font_size(text_frame)
            safe_color = self._select_safe_color(text_frame)

            # Calculate basic positioning
            bounds = self._calculate_safe_bounds(text_frame)

            # Generate basic text shape XML
            xml_content = self._generate_safe_text_shape(
                text_content, safe_font, safe_size, safe_color, bounds, context
            )

            # Fallback always has moderate confidence - it works but isn't optimal
            confidence = 0.5

            # Generate metadata
            metadata = {
                'strategy': 'fallback',
                'original_fonts': [run.font_family for run in text_frame.runs] if text_frame.runs else [],
                'fallback_font': safe_font,
                'text_content': text_content[:50],  # First 50 chars for debugging
                'bounds': bounds,
                'run_count': len(text_frame.runs) if text_frame.runs else 0,
                'safety_measures_applied': True
            }

            self.logger.debug(f"Fallback conversion successful for text: {text_content[:30]}")

            return HandlerResult(
                success=True,
                xml_content=xml_content,
                confidence=confidence,
                metadata=metadata,
                warnings=["Using fallback text strategy - original styling may be simplified"]
            )

        except Exception as e:
            # Even if everything fails, provide an absolute minimal fallback
            self.logger.error(f"Fallback conversion encountered error: {e}")
            return self._create_emergency_fallback(text_frame, str(e))

    def _extract_safe_text_content(self, text_frame: TextFrame) -> str:
        """
        Extract text content with safety measures.

        Args:
            text_frame: Text frame to extract from

        Returns:
            Safe text content (never empty)
        """
        try:
            if not text_frame.runs:
                return "[Empty Text]"

            # Combine all text runs
            text_parts = []
            for run in text_frame.runs:
                if hasattr(run, 'text') and run.text:
                    # Sanitize text - remove problematic characters
                    clean_text = self._sanitize_text(run.text)
                    if clean_text:
                        text_parts.append(clean_text)

            combined_text = ' '.join(text_parts).strip()
            return combined_text if combined_text else "[Text Content]"

        except Exception as e:
            self.logger.warning(f"Text extraction failed, using placeholder: {e}")
            return "[Text Extraction Failed]"

    def _sanitize_text(self, text: str) -> str:
        """
        Sanitize text to ensure PowerPoint compatibility.

        Args:
            text: Raw text content

        Returns:
            Sanitized text safe for PowerPoint
        """
        if not text:
            return ""

        # Remove or replace problematic characters
        sanitized = text.replace('\0', '').replace('\x0b', ' ').replace('\x0c', ' ')

        # Limit length to prevent issues
        if len(sanitized) > 1000:
            sanitized = sanitized[:997] + "..."

        return sanitized

    def _select_safe_font(self, text_frame: TextFrame) -> str:
        """
        Select a universally safe font.

        Args:
            text_frame: Text frame being converted

        Returns:
            Safe font family name
        """
        # Try to use a font from the original if it's in our safe list
        try:
            if text_frame.runs:
                for run in text_frame.runs:
                    if hasattr(run, 'font_family') and run.font_family:
                        font_family = run.font_family.strip()
                        # Check if it's one of our safe fonts
                        if font_family in self.universal_fonts:
                            return font_family
                        # Check if it's a common variant
                        if font_family.lower() in ['arial', 'helvetica']:
                            return 'Arial'
                        if font_family.lower() in ['times', 'times new roman']:
                            return 'Times New Roman'
        except Exception as e:
            self.logger.debug(f"Font selection fallback due to error: {e}")

        # Default to the most universally available font
        return 'Arial'

    def _select_safe_font_size(self, text_frame: TextFrame) -> float:
        """
        Select a safe font size.

        Args:
            text_frame: Text frame being converted

        Returns:
            Safe font size in points
        """
        try:
            if text_frame.runs:
                for run in text_frame.runs:
                    if hasattr(run, 'font_size_pt') and run.font_size_pt:
                        size = float(run.font_size_pt)
                        # Clamp to safe range
                        return max(8.0, min(72.0, size))
        except Exception as e:
            self.logger.debug(f"Font size selection fallback due to error: {e}")

        # Default safe size
        return 12.0

    def _select_safe_color(self, text_frame: TextFrame) -> str:
        """
        Select a safe text color.

        Args:
            text_frame: Text frame being converted

        Returns:
            Safe color hex code
        """
        try:
            if text_frame.runs:
                for run in text_frame.runs:
                    if hasattr(run, 'rgb') and run.rgb:
                        # Validate the color format
                        color = str(run.rgb).strip()
                        if len(color) == 6 and all(c in '0123456789ABCDEFabcdef' for c in color):
                            return color.upper()
        except Exception as e:
            self.logger.debug(f"Color selection fallback due to error: {e}")

        # Default to black for maximum compatibility
        return self.safe_colors['black']

    def _calculate_safe_bounds(self, text_frame: TextFrame) -> Dict[str, float]:
        """
        Calculate safe bounds for text positioning.

        Args:
            text_frame: Text frame being converted

        Returns:
            Safe bounds dictionary
        """
        try:
            # Try to use original bounds
            x = getattr(text_frame, 'x', 0.0)
            y = getattr(text_frame, 'y', 0.0)
            width = getattr(text_frame, 'width', None)
            height = getattr(text_frame, 'height', None)

            # Ensure reasonable bounds
            x = max(0.0, float(x)) if x is not None else 100.0
            y = max(0.0, float(y)) if y is not None else 100.0

            # Estimate dimensions if not available
            if width is None or height is None:
                # Estimate based on text content
                text_length = sum(len(run.text) for run in text_frame.runs if hasattr(run, 'text') and run.text)
                width = max(200.0, min(800.0, text_length * 8.0))
                height = 50.0

            return {
                'x': x,
                'y': y,
                'width': max(50.0, float(width)),
                'height': max(20.0, float(height))
            }

        except Exception as e:
            self.logger.warning(f"Bounds calculation failed, using defaults: {e}")
            return {'x': 100.0, 'y': 100.0, 'width': 200.0, 'height': 50.0}

    def _generate_safe_text_shape(self, text_content: str, font_family: str,
                                 font_size: float, color: str, bounds: Dict[str, float],
                                 context: Dict[str, Any]) -> str:
        """
        Generate a guaranteed-safe text shape.

        Args:
            text_content: Text to display
            font_family: Safe font family
            font_size: Safe font size
            color: Safe color hex
            bounds: Safe bounds
            context: Conversion context

        Returns:
            DrawingML XML for safe text shape
        """
        # Convert to EMU with safe defaults
        x_emu, y_emu = self._to_emu_coords(bounds['x'], bounds['y'])
        width_emu = self._to_emu(bounds['width'])
        height_emu = self._to_emu(bounds['height'])

        # Font size in 100ths of a point
        font_size_emu = int(font_size * 100)

        # Escape XML content
        safe_text = self._escape_xml(text_content)
        safe_font = self._escape_xml(font_family)

        # Generate minimal, compatible text shape
        return f"""
            <p:sp>
                <p:nvSpPr>
                    <p:cNvPr id="1" name="FallbackText"/>
                    <p:cNvSpPr txBox="1"/>
                    <p:nvPr/>
                </p:nvSpPr>
                <p:spPr>
                    <a:xfrm>
                        <a:off x="{x_emu}" y="{y_emu}"/>
                        <a:ext cx="{width_emu}" cy="{height_emu}"/>
                    </a:xfrm>
                    <a:prstGeom prst="rect">
                        <a:avLst/>
                    </a:prstGeom>
                    <a:noFill/>
                    <a:ln>
                        <a:noFill/>
                    </a:ln>
                </p:spPr>
                <p:txBody>
                    <a:bodyPr wrap="square" rtlCol="0" anchor="t">
                        <a:spAutoFit/>
                    </a:bodyPr>
                    <a:lstStyle/>
                    <a:p>
                        <a:pPr algn="l"/>
                        <a:r>
                            <a:rPr lang="en-US" sz="{font_size_emu}">
                                <a:solidFill>
                                    <a:srgbClr val="{color}"/>
                                </a:solidFill>
                                <a:latin typeface="{safe_font}"/>
                                <a:ea typeface="{safe_font}"/>
                                <a:cs typeface="{safe_font}"/>
                            </a:rPr>
                            <a:t>{safe_text}</a:t>
                        </a:r>
                    </a:p>
                </p:txBody>
            </p:sp>
        """.strip()

    def _create_emergency_fallback(self, text_frame: TextFrame, error_message: str) -> HandlerResult:
        """
        Create absolute emergency fallback when everything else fails.

        Args:
            text_frame: Original text frame
            error_message: Error that caused the emergency

        Returns:
            HandlerResult with minimal emergency content
        """
        self.logger.critical(f"Creating emergency fallback due to: {error_message}")

        # Absolute minimal text shape
        emergency_xml = """
            <p:sp>
                <p:nvSpPr>
                    <p:cNvPr id="1" name="EmergencyText"/>
                    <p:cNvSpPr txBox="1"/>
                    <p:nvPr/>
                </p:nvSpPr>
                <p:spPr>
                    <a:xfrm>
                        <a:off x="914400" y="914400"/>
                        <a:ext cx="1828800" cy="457200"/>
                    </a:xfrm>
                    <a:prstGeom prst="rect">
                        <a:avLst/>
                    </a:prstGeom>
                    <a:noFill/>
                </p:spPr>
                <p:txBody>
                    <a:bodyPr/>
                    <a:lstStyle/>
                    <a:p>
                        <a:r>
                            <a:rPr lang="en-US" sz="1200">
                                <a:solidFill>
                                    <a:srgbClr val="000000"/>
                                </a:solidFill>
                                <a:latin typeface="Arial"/>
                            </a:rPr>
                            <a:t>[Text Conversion Error]</a:t>
                        </a:r>
                    </a:p>
                </p:txBody>
            </p:sp>
        """.strip()

        return HandlerResult(
            success=True,  # Even emergency fallback is "successful"
            xml_content=emergency_xml,
            confidence=0.1,  # Very low confidence but still usable
            metadata={
                'strategy': 'emergency_fallback',
                'error': error_message,
                'emergency_content': True
            },
            warnings=[f"Emergency fallback used due to error: {error_message}"]
        )

    def get_supported_features(self) -> Dict[str, bool]:
        """
        Get dictionary of features supported by this handler.

        Returns:
            Dictionary mapping feature names to support status
        """
        return {
            'system_fonts': True,           # Uses universal fonts only
            'basic_styling': True,          # Basic text styling only
            'color_text': True,             # Safe colors only
            'multiple_runs': False,         # Simplified to single run
            'font_embedding': False,        # No embedding needed
            'text_transforms': False,       # No complex transforms
            'text_effects': False,          # No effects for safety
            'text_on_path': False,          # No path text
            'wordart_effects': False,       # No WordArt
            'high_fidelity': False,         # Safety over fidelity
            'editability': True,            # Remains editable text
            'guaranteed_success': True      # Always works
        }

    def clear_cache(self):
        """Clear internal caches (fallback handler has no caches)."""
        # Fallback handler doesn't use caches for maximum reliability
        self.logger.debug("Fallback handler cache clear requested (no caches to clear)")
        pass