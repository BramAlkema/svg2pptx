#!/usr/bin/env python3
"""
Text-to-Path Handler

Handles text conversion by converting text to vector paths when system fonts
or WordArt solutions are insufficient. This is typically used for complex text
that requires precise rendering fidelity.

Refactored from archive/legacy-src/converters/text_to_path.py and
core/services/text_to_path_processor.py to follow the BaseStrategyHandler pattern.
"""

import logging
import time
from typing import Dict, Any, List, Optional

from ....ir import TextFrame
from ....ir.font_metadata import FontStrategy
from ....services.conversion_services import ConversionServices
from ..types import HandlerResult
from .base import BaseStrategyHandler

# Conditional imports for text-to-path services
try:
    from ....services.text_to_path_processor import (
        TextToPathProcessor, FontFallbackStrategy, create_text_to_path_processor
    )
    TEXT_TO_PATH_SERVICE_AVAILABLE = True
except ImportError:
    TEXT_TO_PATH_SERVICE_AVAILABLE = False

    # Placeholder for when service unavailable
    class TextToPathProcessor:
        def assess_text_conversion_strategy(self, *args, **kwargs):
            return None

        def convert_text_to_path(self, *args, **kwargs):
            return None


class TextToPathHandler(BaseStrategyHandler):
    """
    Handler for text-to-path conversion.

    Converts text to vector paths when system fonts or WordArt approaches
    are insufficient. This provides the highest fidelity for complex text
    but results in larger file sizes and non-editable text.
    """

    def __init__(self, services: ConversionServices):
        """
        Initialize text-to-path handler.

        Args:
            services: ConversionServices container
        """
        super().__init__(services)
        self.logger = logging.getLogger(__name__)

        # Initialize text-to-path processor if available
        if TEXT_TO_PATH_SERVICE_AVAILABLE:
            try:
                self.text_to_path_processor = create_text_to_path_processor(
                    font_system=getattr(services, 'font_service', None),
                    text_layout_engine=getattr(services, 'text_layout_service', None),
                    path_generator=getattr(services, 'path_service', None)
                )
                self.logger.debug("TextToPath processor initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize TextToPath processor: {e}")
                self.text_to_path_processor = None
        else:
            self.text_to_path_processor = None
            self.logger.warning("TextToPath service not available")

        # Font availability cache
        self._font_availability_cache = {}

        # Common fonts that are usually available
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

        Text-to-path handler can handle text when:
        1. System fonts and WordArt have failed or are unsuitable
        2. Text requires high fidelity rendering
        3. Complex transforms or effects are present
        4. Fonts are completely unavailable

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

            # Text-to-path is typically a fallback strategy
            # Check if other strategies have been attempted and failed
            if context.get('force_text_to_path', False):
                return True

            # Check if fonts are completely unavailable
            font_families = [run.font_family for run in text_frame.runs]
            if not any(self._is_font_available(font) for font in font_families):
                self.logger.debug("No fonts available, text-to-path suitable")
                return True

            # Check for complex features that require path conversion
            if self._requires_path_conversion(text_frame, context):
                self.logger.debug("Complex features detected, text-to-path suitable")
                return True

            # Check if previous strategies failed
            if context.get('system_font_failed', False) or context.get('wordart_failed', False):
                self.logger.debug("Previous strategies failed, text-to-path suitable")
                return True

            # Text-to-path is typically not the first choice
            return False

        except Exception as e:
            self.logger.warning(f"Error in can_handle check: {e}")
            return True  # Fallback to handling when in doubt

    def convert(self, text_frame: TextFrame, context: Dict[str, Any]) -> HandlerResult:
        """
        Convert text frame to vector paths.

        Args:
            text_frame: Text frame to convert
            context: Conversion context

        Returns:
            HandlerResult with DrawingML path shapes
        """
        try:
            self.logger.debug(f"Converting text to paths: {[run.text for run in text_frame.runs]}")

            # Extract text content and properties
            text_content = ' '.join(run.text for run in text_frame.runs)
            font_families = [run.font_family for run in text_frame.runs]
            font_size = text_frame.runs[0].font_size_pt if text_frame.runs else 12.0

            # Calculate positioning
            bounds = self._calculate_bounds(text_frame)

            # Generate path conversion
            if self.text_to_path_processor:
                xml_content = self._convert_with_processor(
                    text_content, font_families, font_size, bounds, context
                )
            else:
                xml_content = self._convert_with_fallback(
                    text_content, font_families, font_size, bounds, context
                )

            # Calculate confidence - path conversion typically has high confidence
            # for rendering fidelity but low confidence for editability
            confidence = self._calculate_confidence(text_frame, context)

            # Generate metadata
            metadata = {
                'strategy': 'text_to_path',
                'fonts_used': font_families,
                'text_content': text_content[:100],  # First 100 chars for debugging
                'bounds': bounds,
                'run_count': len(text_frame.runs),
                'processor_available': self.text_to_path_processor is not None
            }

            return HandlerResult(
                success=True,
                xml_content=xml_content,
                confidence=confidence,
                metadata=metadata
            )

        except Exception as e:
            self.logger.error(f"Text-to-path conversion failed: {e}")
            return HandlerResult(
                success=False,
                xml_content="",
                confidence=0.0,
                error=e,
                warnings=[f"Text-to-path conversion failed: {str(e)}"]
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

        # Use font service if available
        try:
            if hasattr(self.services, 'font_service') and self.services.font_service:
                font_file = self.services.font_service.find_font_file(font_family)
                available = font_file is not None
            else:
                # Fallback to simple check
                available = font_family in self.common_system_fonts

            self._font_availability_cache[font_family] = available
            return available

        except Exception as e:
            self.logger.warning(f"Font availability check failed for {font_family}: {e}")
            # Conservative default
            available = font_family in self.common_system_fonts
            self._font_availability_cache[font_family] = available
            return available

    def _requires_path_conversion(self, text_frame: TextFrame, context: Dict[str, Any]) -> bool:
        """
        Check if text frame requires path conversion due to complexity.

        Args:
            text_frame: Text frame to analyze
            context: Conversion context

        Returns:
            True if path conversion is required
        """
        # Very complex transforms that can't be handled by regular text
        if hasattr(text_frame, 'transform') and text_frame.transform is not None:
            transform = text_frame.transform
            # Check for skewing or complex matrix transforms
            if hasattr(transform, 'skew_x') and transform.skew_x is not None:
                try:
                    if abs(float(transform.skew_x)) > 5.0:
                        return True
                except (TypeError, ValueError):
                    return True
            if hasattr(transform, 'skew_y') and transform.skew_y is not None:
                try:
                    if abs(float(transform.skew_y)) > 5.0:
                        return True
                except (TypeError, ValueError):
                    return True

        # Text on complex paths
        if hasattr(text_frame, 'text_path') and text_frame.text_path is not None:
            return True

        # Very small or very large text that might not render well
        for run in text_frame.runs:
            if run.font_size_pt < 4 or run.font_size_pt > 144:
                return True

        # Complex text effects that require precise rendering
        for run in text_frame.runs:
            if hasattr(run, 'text_shadow') and run.text_shadow:
                return True
            if hasattr(run, 'text_outline') and run.text_outline:
                # Only complex outlines, simple strokes can be handled by text
                try:
                    outline_width = float(getattr(run.text_outline, 'width', 0))
                    if outline_width > run.font_size_pt * 0.1:  # Outline > 10% of font size
                        return True
                except (TypeError, ValueError):
                    return True

        return False

    def _convert_with_processor(self, text_content: str, font_families: List[str],
                              font_size: float, bounds: Dict[str, float],
                              context: Dict[str, Any]) -> str:
        """
        Convert text using the text-to-path processor service.

        Args:
            text_content: Text to convert
            font_families: Font families to use
            font_size: Font size in points
            bounds: Text bounds
            context: Conversion context

        Returns:
            DrawingML XML string
        """
        try:
            # Assess conversion strategy
            assessment = self.text_to_path_processor.assess_text_conversion_strategy(
                text_content, font_families, font_size
            )

            if assessment and assessment.should_convert_to_path:
                # Generate actual path data
                path_data = self.text_to_path_processor.convert_text_to_path(
                    text_content, font_families, font_size
                )

                if path_data:
                    return self._create_path_shape_xml(path_data, bounds, context)

            # If assessment suggests not converting to path, create regular text
            return self._create_fallback_text_shape(
                text_content, font_families[0] if font_families else 'Arial',
                font_size, bounds, context
            )

        except Exception as e:
            self.logger.warning(f"Processor conversion failed: {e}")
            return self._convert_with_fallback(
                text_content, font_families, font_size, bounds, context
            )

    def _convert_with_fallback(self, text_content: str, font_families: List[str],
                             font_size: float, bounds: Dict[str, float],
                             context: Dict[str, Any]) -> str:
        """
        Convert text using fallback approach when processor unavailable.

        Args:
            text_content: Text to convert
            font_families: Font families to use
            font_size: Font size in points
            bounds: Text bounds
            context: Conversion context

        Returns:
            DrawingML XML string
        """
        # Create a simple rectangular path representing the text bounds
        # This is a very basic fallback that maintains positioning
        x_emu, y_emu = self._to_emu_coords(bounds['x'], bounds['y'])
        width_emu = self._to_emu(bounds['width'])
        height_emu = self._to_emu(bounds['height'])

        # Create simple path data representing text area
        path_data = f"M 0 0 L {width_emu} 0 L {width_emu} {height_emu} L 0 {height_emu} Z"

        return self._create_path_shape_xml(path_data, bounds, context)

    def _create_path_shape_xml(self, path_data: str, bounds: Dict[str, float],
                             context: Dict[str, Any]) -> str:
        """
        Create DrawingML path shape from path data.

        Args:
            path_data: SVG path data
            bounds: Text bounds
            context: Conversion context

        Returns:
            DrawingML XML string
        """
        x_emu, y_emu = self._to_emu_coords(bounds['x'], bounds['y'])
        width_emu = self._to_emu(bounds['width'])
        height_emu = self._to_emu(bounds['height'])

        # Generate shape properties
        shape_props = self._generate_shape_properties(bounds)

        # Generate non-visual properties
        nv_props = self._generate_non_visual_properties()

        # Create custom geometry with path data
        custom_geom = f"""
            <a:custGeom>
                <a:avLst/>
                <a:gdLst/>
                <a:ahLst/>
                <a:cxnLst/>
                <a:rect l="0" t="0" r="{width_emu}" b="{height_emu}"/>
                <a:pathLst>
                    <a:path w="{width_emu}" h="{height_emu}">
                        <a:moveTo>
                            <a:pt x="0" y="0"/>
                        </a:moveTo>
                        <a:lnTo>
                            <a:pt x="{width_emu}" y="0"/>
                        </a:lnTo>
                        <a:lnTo>
                            <a:pt x="{width_emu}" y="{height_emu}"/>
                        </a:lnTo>
                        <a:lnTo>
                            <a:pt x="0" y="{height_emu}"/>
                        </a:lnTo>
                        <a:close/>
                    </a:path>
                </a:pathLst>
            </a:custGeom>
        """

        return f"""
            <p:sp>
                {nv_props}
                <p:spPr>
                    <a:xfrm>
                        <a:off x="{x_emu}" y="{y_emu}"/>
                        <a:ext cx="{width_emu}" cy="{height_emu}"/>
                    </a:xfrm>
                    {custom_geom}
                    <a:solidFill>
                        <a:srgbClr val="000000"/>
                    </a:solidFill>
                </p:spPr>
            </p:sp>
        """

    def _create_fallback_text_shape(self, text_content: str, font_family: str,
                                   font_size: float, bounds: Dict[str, float],
                                   context: Dict[str, Any]) -> str:
        """
        Create regular text shape as fallback when path conversion fails.

        Args:
            text_content: Text content
            font_family: Font family to use
            font_size: Font size in points
            bounds: Text bounds
            context: Conversion context

        Returns:
            DrawingML XML string
        """
        x_emu, y_emu = self._to_emu_coords(bounds['x'], bounds['y'])
        width_emu = self._to_emu(bounds['width'])
        height_emu = self._to_emu(bounds['height'])

        # Font size in 100ths of a point
        font_size_emu = int(font_size * 100)

        # Ensure font family is properly escaped
        font_family = self._escape_xml(font_family)
        text_content = self._escape_xml(text_content)

        # Generate shape properties
        shape_props = self._generate_shape_properties(bounds)

        # Generate non-visual properties
        nv_props = self._generate_non_visual_properties()

        return f"""
            <p:sp>
                {nv_props}
                {shape_props}
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
                                    <a:srgbClr val="000000"/>
                                </a:solidFill>
                                <a:latin typeface="{font_family}"/>
                                <a:ea typeface="{font_family}"/>
                                <a:cs typeface="{font_family}"/>
                            </a:rPr>
                            <a:t>{text_content}</a:t>
                        </a:r>
                    </a:p>
                </p:txBody>
            </p:sp>
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
                <p:cNvPr id="3" name="TextPath_{shape_id}"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
        """

    def _calculate_confidence(self, text_frame: TextFrame, context: Dict[str, Any]) -> float:
        """
        Calculate confidence score for text-to-path conversion.

        Args:
            text_frame: Text frame being converted
            context: Conversion context

        Returns:
            Confidence score (0.0 - 1.0)
        """
        confidence = 0.7  # Base confidence for path conversion

        # Boost confidence when fonts are unavailable
        font_families = [run.font_family for run in text_frame.runs]
        available_fonts = [f for f in font_families if self._is_font_available(f)]
        if not available_fonts:
            confidence += 0.2

        # Boost confidence for complex features that require path conversion
        if self._requires_path_conversion(text_frame, context):
            confidence += 0.15

        # Reduce confidence for very long text (path conversion creates large files)
        total_text_length = sum(len(run.text) for run in text_frame.runs)
        if total_text_length > 100:
            confidence -= 0.1

        # Boost confidence if processor is available
        if self.text_to_path_processor:
            confidence += 0.1

        return max(0.0, min(1.0, confidence))

    def get_supported_features(self) -> Dict[str, bool]:
        """
        Get dictionary of features supported by this handler.

        Returns:
            Dictionary mapping feature names to support status
        """
        return {
            'system_fonts': False,          # Converts to paths, not text
            'basic_styling': True,          # Can preserve in path form
            'color_text': True,             # Colors preserved in path
            'multiple_runs': True,          # Can handle multiple runs
            'font_embedding': False,        # No embedding needed for paths
            'text_transforms': True,        # All transforms supported via paths
            'text_effects': True,           # Effects can be preserved in paths
            'text_on_path': True,           # Specialized handling for path text
            'wordart_effects': True,        # Can handle via path conversion
            'high_fidelity': True,          # Highest visual fidelity
            'editability': False            # Text becomes uneditable paths
        }

    def clear_cache(self):
        """Clear internal caches."""
        self._font_availability_cache.clear()
        if self.text_to_path_processor:
            self.text_to_path_processor.clear_cache()
        self.logger.debug("Cleared text-to-path handler caches")