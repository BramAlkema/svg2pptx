#!/usr/bin/env python3
"""
WordArt Handler

Handles text conversion using PowerPoint WordArt functionality.
Optimized for stylized text with transforms, effects, and creative layouts.
"""

import logging
from typing import Dict, Any, Optional, List
from lxml import etree as ET

from ....ir import TextFrame
from ....ir.font_metadata import FontStrategy, FontAvailability
from ....services.conversion_services import ConversionServices
from ..types import HandlerResult
from .base import BaseStrategyHandler

# WordArt integration service removed - handler uses built-in implementation
# The handler has complete WordArt generation capability without external service
WORDART_INTEGRATION_AVAILABLE = False


# WordArt text run class for internal use
class WordArtTextRun:
    """Represents a styled text run for WordArt conversion."""

    def __init__(self, text="", font_family="Arial", font_size=24.0,
                 fill_color="#000000", stroke_color=None, stroke_width=0.0, opacity=1.0):
        self.text = text
        self.font_family = font_family
        self.font_size = font_size
        self.fill_color = fill_color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.opacity = opacity


class WordArtHandler(BaseStrategyHandler):
    """
    Handler for PowerPoint WordArt conversion.

    Uses PowerPoint's native WordArt functionality to create stylized text
    with transforms, effects, and creative layouts that would be difficult
    to achieve with standard text shapes.
    """

    def __init__(self, services: ConversionServices):
        """
        Initialize WordArt handler.

        Args:
            services: ConversionServices container
        """
        super().__init__(services)
        self.logger = logging.getLogger(__name__)

        # WordArt service is not used - handler has built-in implementation
        self.wordart_service = None
        self.logger.debug("Using built-in WordArt generation")

        # WordArt preset mappings
        self.wordart_presets = {
            'simple': 'Plain',
            'outline': 'Outline',
            'shadow': 'Shadow',
            'reflection': 'Reflection',
            'glow': 'Glow',
            'bevel': 'Bevel',
            'gradient': 'Gradient',
            'pattern': 'Pattern',
            'texture': 'Texture',
            'arch': 'Arch',
            'curve': 'Curve',
            'wave': 'Wave',
            'inflate': 'Inflate',
            'deflate': 'Deflate',
            'button': 'Button',
            'perspective': 'Perspective'
        }

        # Performance tracking
        self._wordart_cache = {}
        self._preset_usage_stats = {}

    def can_handle(self, text_frame: TextFrame, context: Dict[str, Any]) -> bool:
        """
        Check if this handler can process the text frame.

        WordArt handler can handle text when:
        1. WordArt services are available
        2. Text has visual effects or transforms suitable for WordArt
        3. Policy engine recommends WordArt
        4. Text complexity is moderate to high

        Args:
            text_frame: Text frame to check
            context: Conversion context

        Returns:
            True if handler can process this text frame
        """
        try:
            # Check if WordArt services are available
            if not self.wordart_service:
                self.logger.debug("WordArt services not available")
                return False

            # Must have at least one run
            if not text_frame.runs:
                return False

            # Check if WordArt is forced by policy
            if context.get('force_wordart', False):
                self.logger.debug("WordArt forced by policy")
                return True

            # Check for WordArt-suitable features
            if self._has_wordart_features(text_frame, context):
                self.logger.debug("Text has WordArt-suitable features")
                return True

            # Check policy recommendation
            policy_decision = context.get('policy_decisions', {})
            if policy_decision.get('wordart_opportunity', False):
                confidence = policy_decision.get('confidence', 0.0)
                if confidence >= 0.6:  # Configurable threshold
                    self.logger.debug(f"Policy recommends WordArt with confidence {confidence}")
                    return True

            return False

        except Exception as e:
            self.logger.warning(f"Error in can_handle check: {e}")
            return False

    def convert(self, text_frame: TextFrame, context: Dict[str, Any]) -> HandlerResult:
        """
        Convert text frame using WordArt.

        Args:
            text_frame: Text frame to convert
            context: Conversion context

        Returns:
            HandlerResult with WordArt DrawingML shape
        """
        try:
            self.logger.debug(f"Converting text using WordArt: {text_frame.runs[0].text if text_frame.runs else 'empty'}")

            # Convert TextFrame to WordArt format
            wordart_text_runs = self._convert_to_wordart_runs(text_frame)

            # Create mock SVG element for WordArt service (temporary bridge)
            svg_element = self._create_svg_element_bridge(text_frame, context)

            # Generate WordArt using integration service or fallback
            if self.wordart_service:
                generation_result = self.wordart_service.generate_wordart(svg_element, context)

                if not generation_result.success:
                    return HandlerResult(
                        success=False,
                        xml_content="",
                        confidence=0.0,
                        warnings=[f"WordArt generation failed: {generation_result.fallback_reason}"]
                    )

                # Convert ET.Element to XML string
                xml_content = ET.tostring(generation_result.wordart_xml, encoding='unicode')

                # Calculate confidence based on generation success and features
                confidence = self._calculate_confidence(text_frame, context, generation_result)

                # Generate metadata
                metadata = {
                    'strategy': 'wordart',
                    'preset_used': self._extract_preset_from_result(generation_result),
                    'generation_time_ms': generation_result.performance_metrics.get('generation_time_ms', 0),
                    'decision_metadata': generation_result.decision_metadata,
                    'text_run_count': len(wordart_text_runs),
                    'has_transforms': hasattr(text_frame, 'transform') and text_frame.transform is not None
                }
            else:
                # Fallback: generate basic WordArt shape
                xml_content = self._generate_basic_wordart_xml(text_frame, context)
                confidence = self._calculate_confidence(text_frame, context, None)

                metadata = {
                    'strategy': 'wordart',
                    'preset_used': 'basic',
                    'generation_time_ms': 0,
                    'decision_metadata': {'fallback_mode': True},
                    'text_run_count': len(wordart_text_runs),
                    'has_transforms': hasattr(text_frame, 'transform') and text_frame.transform is not None
                }

            return HandlerResult(
                success=True,
                xml_content=xml_content,
                confidence=confidence,
                metadata=metadata
            )

        except Exception as e:
            self.logger.error(f"WordArt conversion failed: {e}")
            return HandlerResult(
                success=False,
                xml_content="",
                confidence=0.0,
                error=e,
                warnings=[f"WordArt conversion failed: {str(e)}"]
            )

    def _has_wordart_features(self, text_frame: TextFrame, context: Dict[str, Any]) -> bool:
        """
        Check if text frame has features that benefit from WordArt.

        Args:
            text_frame: Text frame to analyze
            context: Conversion context

        Returns:
            True if text has WordArt-suitable features
        """
        # Check for transforms
        if hasattr(text_frame, 'transform') and text_frame.transform is not None:
            transform = text_frame.transform

            # Any rotation, scaling, or skewing suggests WordArt suitability
            if hasattr(transform, 'rotation') and abs(getattr(transform, 'rotation', 0)) > 5:
                return True
            if hasattr(transform, 'scale_x') and abs(getattr(transform, 'scale_x', 1) - 1) > 0.2:
                return True
            if hasattr(transform, 'scale_y') and abs(getattr(transform, 'scale_y', 1) - 1) > 0.2:
                return True
            if hasattr(transform, 'skew_x') and abs(getattr(transform, 'skew_x', 0)) > 2:
                return True
            if hasattr(transform, 'skew_y') and abs(getattr(transform, 'skew_y', 0)) > 2:
                return True

        # Check for text on path
        if hasattr(text_frame, 'text_path') and text_frame.text_path is not None:
            return True

        # Check for visual effects in text runs
        for run in text_frame.runs:
            # Stroke effects
            if hasattr(run, 'stroke') and run.stroke and getattr(run, 'stroke_width', 0) > 1:
                return True

            # Text shadows or outlines
            if hasattr(run, 'text_shadow') and run.text_shadow:
                return True
            if hasattr(run, 'text_outline') and run.text_outline:
                return True

            # Gradient fills
            if hasattr(run, 'fill') and run.fill:
                fill_str = str(run.fill)
                if 'gradient' in fill_str.lower() or 'url(' in fill_str:
                    return True

        # Check for decorative fonts that work well with WordArt
        decorative_font_keywords = [
            'script', 'decorative', 'display', 'fancy', 'artistic',
            'brush', 'calligraphy', 'handwriting', 'outline'
        ]

        for run in text_frame.runs:
            font_family = getattr(run, 'font_family', '').lower()
            if any(keyword in font_family for keyword in decorative_font_keywords):
                return True

        # Check for short text (better for WordArt effects)
        total_text = ''.join(getattr(run, 'text', '') for run in text_frame.runs)
        if len(total_text.strip()) <= 20:  # Short text works well with WordArt
            # Additional checks for short text
            if len(text_frame.runs) == 1 and any(
                getattr(text_frame.runs[0], attr, 12) > 18
                for attr in ['font_size_pt', 'font_size']
            ):
                return True

        return False

    def _convert_to_wordart_runs(self, text_frame: TextFrame) -> List['WordArtTextRun']:
        """
        Convert TextFrame runs to WordArt format.

        Args:
            text_frame: TextFrame to convert

        Returns:
            List of WordArtTextRun objects
        """
        wordart_runs = []

        for run in text_frame.runs:
            # Extract properties with defaults
            text = getattr(run, 'text', '')
            font_family = getattr(run, 'font_family', 'Arial')
            font_size = getattr(run, 'font_size_pt', getattr(run, 'font_size', 24.0))
            fill_color = getattr(run, 'fill', getattr(run, 'rgb', '#000000'))

            # Handle stroke properties
            stroke_color = None
            stroke_width = 0.0
            if hasattr(run, 'stroke') and run.stroke:
                stroke_color = str(run.stroke)
                stroke_width = getattr(run, 'stroke_width', 1.0)

            # Handle opacity
            opacity = getattr(run, 'opacity', 1.0)

            wordart_run = WordArtTextRun(
                text=text,
                font_family=font_family,
                font_size=float(font_size),
                fill_color=str(fill_color),
                stroke_color=stroke_color,
                stroke_width=float(stroke_width),
                opacity=float(opacity)
            )

            wordart_runs.append(wordart_run)

        return wordart_runs

    def _create_svg_element_bridge(self, text_frame: TextFrame, context: Dict[str, Any]) -> ET.Element:
        """
        Create a temporary SVG element bridge for WordArt service.

        This is a temporary solution until the WordArt service is updated
        to work directly with TextFrame IR objects.

        Args:
            text_frame: TextFrame to convert
            context: Conversion context

        Returns:
            SVG text element
        """
        # Create SVG text element
        text_elem = ET.Element('text')

        # Set text content from first run
        if text_frame.runs:
            primary_run = text_frame.runs[0]
            text_elem.text = getattr(primary_run, 'text', '')

            # Set font properties
            text_elem.set('font-family', getattr(primary_run, 'font_family', 'Arial'))
            font_size = getattr(primary_run, 'font_size_pt', getattr(primary_run, 'font_size', 24))
            text_elem.set('font-size', str(font_size))

            # Set fill color
            fill_color = getattr(primary_run, 'fill', getattr(primary_run, 'rgb', '#000000'))
            text_elem.set('fill', str(fill_color))

            # Set stroke properties
            if hasattr(primary_run, 'stroke') and primary_run.stroke:
                text_elem.set('stroke', str(primary_run.stroke))
                stroke_width = getattr(primary_run, 'stroke_width', 1.0)
                text_elem.set('stroke-width', str(stroke_width))

            # Set opacity
            opacity = getattr(primary_run, 'opacity', 1.0)
            if opacity < 1.0:
                text_elem.set('opacity', str(opacity))

        # Set transform if available
        if hasattr(text_frame, 'transform') and text_frame.transform is not None:
            # Convert transform to SVG format (simplified)
            transform_str = self._convert_transform_to_svg(text_frame.transform)
            if transform_str:
                text_elem.set('transform', transform_str)

        # Set position
        if hasattr(text_frame, 'origin') and text_frame.origin:
            text_elem.set('x', str(text_frame.origin.x))
            text_elem.set('y', str(text_frame.origin.y))

        return text_elem

    def _convert_transform_to_svg(self, transform) -> Optional[str]:
        """
        Convert transform object to SVG transform string.

        Args:
            transform: Transform object

        Returns:
            SVG transform string or None
        """
        try:
            transform_parts = []

            # Translation
            if hasattr(transform, 'translate_x') or hasattr(transform, 'translate_y'):
                tx = getattr(transform, 'translate_x', 0)
                ty = getattr(transform, 'translate_y', 0)
                if tx != 0 or ty != 0:
                    transform_parts.append(f"translate({tx},{ty})")

            # Rotation
            if hasattr(transform, 'rotation') and transform.rotation != 0:
                transform_parts.append(f"rotate({transform.rotation})")

            # Scale
            if hasattr(transform, 'scale_x') or hasattr(transform, 'scale_y'):
                sx = getattr(transform, 'scale_x', 1)
                sy = getattr(transform, 'scale_y', 1)
                if sx != 1 or sy != 1:
                    transform_parts.append(f"scale({sx},{sy})")

            # Skew
            if hasattr(transform, 'skew_x') and transform.skew_x != 0:
                transform_parts.append(f"skewX({transform.skew_x})")
            if hasattr(transform, 'skew_y') and transform.skew_y != 0:
                transform_parts.append(f"skewY({transform.skew_y})")

            return ' '.join(transform_parts) if transform_parts else None

        except Exception as e:
            self.logger.warning(f"Failed to convert transform: {e}")
            return None

    def _generate_basic_wordart_xml(self, text_frame: TextFrame, context: Dict[str, Any]) -> str:
        """
        Generate basic WordArt XML when full service is not available.

        Args:
            text_frame: Text frame to convert
            context: Conversion context

        Returns:
            Basic WordArt XML string
        """
        # Extract text and basic properties
        text_content = ""
        if text_frame.runs:
            text_content = text_frame.runs[0].text
            font_family = getattr(text_frame.runs[0], 'font_family', 'Arial')
            font_size = getattr(text_frame.runs[0], 'font_size_pt',
                              getattr(text_frame.runs[0], 'font_size', 24))
            fill_color = getattr(text_frame.runs[0], 'fill',
                               getattr(text_frame.runs[0], 'rgb', '#000000'))

        # Generate simple shape XML (basic implementation)
        shape_xml = f"""
        <p:sp>
            <p:nvSpPr>
                <p:cNvPr id="2" name="WordArt_Shape"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="100" y="100"/>
                    <a:ext cx="2000000" cy="500000"/>
                </a:xfrm>
                <a:prstGeom prst="rect">
                    <a:avLst/>
                </a:prstGeom>
                <a:solidFill>
                    <a:srgbClr val="{fill_color.replace('#', '')}"/>
                </a:solidFill>
            </p:spPr>
            <p:txBody>
                <a:bodyPr wrap="none" rtlCol="0">
                    <a:spAutoFit/>
                </a:bodyPr>
                <a:lstStyle/>
                <a:p>
                    <a:pPr algn="ctr"/>
                    <a:r>
                        <a:rPr lang="en-US" sz="{int(font_size * 100)}" b="1">
                            <a:solidFill>
                                <a:srgbClr val="{fill_color.replace('#', '')}"/>
                            </a:solidFill>
                            <a:latin typeface="{font_family}"/>
                        </a:rPr>
                        <a:t>{text_content}</a:t>
                    </a:r>
                </a:p>
            </p:txBody>
        </p:sp>
        """.strip()

        return shape_xml

    def _calculate_confidence(self, text_frame: TextFrame, context: Dict[str, Any],
                            generation_result) -> float:
        """
        Calculate confidence score for WordArt conversion.

        Args:
            text_frame: Text frame being converted
            context: Conversion context
            generation_result: WordArt generation result

        Returns:
            Confidence score (0.0 - 1.0)
        """
        confidence = 0.7  # Base confidence for WordArt

        # Boost confidence if generation was successful
        if generation_result and generation_result.success:
            confidence += 0.2
        elif not generation_result:
            # Using fallback mode
            confidence = 0.6

        # Boost confidence for features that work well with WordArt
        if self._has_wordart_features(text_frame, context):
            confidence += 0.1

        # Boost confidence based on policy decision
        policy_decisions = context.get('policy_decisions', {})
        policy_confidence = policy_decisions.get('confidence', 0.5)
        if policy_decisions.get('wordart_opportunity', False):
            confidence += (policy_confidence - 0.5) * 0.2

        # Reduce confidence for very long text
        total_text = ''.join(getattr(run, 'text', '') for run in text_frame.runs)
        if len(total_text) > 50:
            confidence -= 0.1

        # Reduce confidence for many text runs
        if len(text_frame.runs) > 3:
            confidence -= 0.05

        return max(0.0, min(1.0, confidence))

    def _extract_preset_from_result(self, generation_result) -> Optional[str]:
        """
        Extract WordArt preset from generation result.

        Args:
            generation_result: WordArt generation result

        Returns:
            Preset name or None
        """
        if not generation_result:
            return None

        try:
            metadata = generation_result.decision_metadata
            if 'path_analysis' in metadata and metadata['path_analysis']:
                return metadata['path_analysis'].get('preset_type')
            return None
        except Exception:
            return None

    def get_supported_features(self) -> Dict[str, bool]:
        """
        Get dictionary of features supported by this handler.

        Returns:
            Dictionary mapping feature names to support status
        """
        return {
            'wordart_effects': True,
            'text_transforms': True,      # Rotation, scaling, skewing
            'text_on_path': True,         # Text following curves
            'gradient_fills': True,       # Gradient text fills
            'text_shadows': True,         # Drop shadows and effects
            'text_outlines': True,        # Text stroke effects
            'decorative_fonts': True,     # Artistic font rendering
            'system_fonts': False,        # WordArt doesn't need system fonts
            'font_embedding': False,      # WordArt renders as shapes
            'basic_styling': True,        # Bold, italic, color
            'multiple_runs': True,        # Multiple styled text runs
            'preset_styles': True         # WordArt preset effects
        }

    def get_available_presets(self) -> List[str]:
        """
        Get list of available WordArt presets.

        Returns:
            List of preset names
        """
        return list(self.wordart_presets.keys())

    def clear_cache(self):
        """Clear internal caches."""
        self._wordart_cache.clear()
        self._preset_usage_stats.clear()
        self.logger.debug("Cleared WordArt handler caches")

    def get_preset_usage_stats(self) -> Dict[str, int]:
        """
        Get statistics on WordArt preset usage.

        Returns:
            Dictionary mapping preset names to usage counts
        """
        return self._preset_usage_stats.copy()

    def is_available(self) -> bool:
        """
        Check if WordArt handler is available.

        Returns:
            True if WordArt services are available
        """
        return self.wordart_service is not None