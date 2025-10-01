#!/usr/bin/env python3
"""
Text Processing Adapter

Integrates Clean Slate TextMapper with modern font and text layout services.
Leverages the new Clean Slate FontSystem and TextLayoutEngine for enhanced text processing.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Import Clean Slate text processing services
try:
    from ..services.font_system import FontSystem, FontAnalysisResult
    from ..services.text_layout_engine import TextLayoutEngine, svg_text_to_ppt_box_modern
    from ..ir.font_metadata import create_font_metadata
    CLEAN_SLATE_AVAILABLE = True
except ImportError:
    CLEAN_SLATE_AVAILABLE = False
    logging.warning("Clean Slate text services not available - text adapter will use fallback")

# Fallback to legacy system if Clean Slate not available
try:
    from ..services.font_service import FontService
    from ..services.text_layout import svg_text_to_ppt_box
    LEGACY_SYSTEM_AVAILABLE = True
except ImportError:
    LEGACY_SYSTEM_AVAILABLE = False
    logging.warning("Legacy text system not available")

from ..ir import TextFrame, RichTextFrame, Run, TextAnchor, EnhancedRun


@dataclass
class TextProcessingResult:
    """Result of text processing"""
    xml_content: str
    layout_method: str  # native_dml, emf_fallback, adapter_enhanced
    font_metrics_used: bool
    text_layout_applied: bool
    metadata: Dict[str, Any]


class TextProcessingAdapter:
    """
    Adapter for integrating IR text processing with Clean Slate text services.

    Leverages modern Clean Slate infrastructure:
    - FontSystem for comprehensive font analysis and strategy decisions
    - TextLayoutEngine for precise SVG-to-PowerPoint coordinate conversion
    - Enhanced IR structures with font metadata integration
    """

    def __init__(self, services=None):
        """Initialize text processing adapter with Clean Slate services"""
        self.logger = logging.getLogger(__name__)
        self.services = services

        # Try to initialize Clean Slate services first
        if CLEAN_SLATE_AVAILABLE:
            try:
                # Use services from dependency injection if available
                if services and hasattr(services, 'font_system'):
                    self.font_system = services.font_system
                else:
                    from ..services.font_system import create_font_system
                    self.font_system = create_font_system()

                if services and hasattr(services, 'text_layout_engine'):
                    self.text_layout_engine = services.text_layout_engine
                else:
                    from ..services.text_layout_engine import create_text_layout_engine
                    unit_converter = getattr(services, 'unit_converter', None) if services else None
                    font_processor = getattr(services, 'font_processor', None) if services else None
                    self.text_layout_engine = create_text_layout_engine(unit_converter, font_processor)

                self._clean_slate_available = True
                self.logger.info("Clean Slate text services initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Clean Slate services: {e}")
                self._clean_slate_available = False
        else:
            self._clean_slate_available = False

        # Fallback to legacy system if Clean Slate unavailable
        if not self._clean_slate_available and LEGACY_SYSTEM_AVAILABLE:
            try:
                self.font_service = FontService() if not services else getattr(services, 'font_service', FontService())
                self._legacy_available = True
                self.logger.info("Legacy text services initialized as fallback")
            except Exception as e:
                self.logger.warning(f"Failed to initialize legacy services: {e}")
                self._legacy_available = False
        else:
            self._legacy_available = False

        if not self._clean_slate_available and not self._legacy_available:
            self.logger.warning("No text processing services available - using basic fallback")

    def can_enhance_text_processing(self, text_frame: TextFrame) -> bool:
        """Check if text processing can be enhanced for this text frame"""
        return (
            (self._clean_slate_available or self._legacy_available) and
            text_frame is not None and
            hasattr(text_frame, 'runs') and
            text_frame.runs
        )

    def _get_runs(self, text_frame):
        """Get runs from either TextFrame or RichTextFrame"""
        if isinstance(text_frame, RichTextFrame):
            return text_frame.all_runs
        return text_frame.runs if hasattr(text_frame, 'runs') else []

    def enhance_text_layout(self, text_frame: TextFrame, base_xml: str = None) -> TextProcessingResult:
        """
        Enhance text layout using Clean Slate or legacy text services.

        Args:
            text_frame: IR TextFrame element to process
            base_xml: Optional base XML content to enhance

        Returns:
            TextProcessingResult with enhanced layout and metadata

        Raises:
            ValueError: If text cannot be processed
        """
        if not self.can_enhance_text_processing(text_frame):
            return self._process_fallback_text(text_frame, base_xml)

        try:
            # Try Clean Slate services first
            if self._clean_slate_available:
                return self._process_with_clean_slate(text_frame, base_xml)
            # Fall back to legacy system
            elif self._legacy_available:
                return self._process_with_legacy_system(text_frame, base_xml)
            else:
                return self._process_fallback_text(text_frame, base_xml)

        except Exception as e:
            self.logger.warning(f"Text processing failed, using fallback: {e}")
            return self._process_fallback_text(text_frame, base_xml)

    def _process_with_clean_slate(self, text_frame: TextFrame, base_xml: str) -> TextProcessingResult:
        """Process text using Clean Slate services"""

        # Step 1: Use FontSystem for enhanced font analysis
        enhanced_font_analysis = {}
        font_analysis_used = False

        runs = self._get_runs(text_frame)
        if self.font_system and runs:
            try:
                for i, run in enumerate(runs):
                    # Create font metadata for analysis
                    font_metadata = create_font_metadata(
                        run.font_family,
                        weight="700" if run.bold else "400",
                        style="italic" if run.italic else "normal",
                        size_pt=run.font_size_pt
                    )

                    # Analyze font using FontSystem
                    analysis_result = self.font_system.analyze_font(font_metadata)

                    enhanced_font_analysis[f'run_{i}'] = {
                        'font_family': run.font_family,
                        'strategy': analysis_result.recommended_strategy.value,
                        'confidence': analysis_result.confidence,
                        'availability': getattr(analysis_result, 'availability', None),
                        'notes': analysis_result.notes
                    }
                    font_analysis_used = True

            except Exception as e:
                self.logger.warning(f"FontSystem analysis failed: {e}")
                font_analysis_used = False

        # Step 2: Use TextLayoutEngine for enhanced positioning
        text_layout_applied = False
        enhanced_positioning = {}

        if self.text_layout_engine and hasattr(text_frame, 'bbox'):
            try:
                for i, run in enumerate(runs):
                    # Create font metadata for layout
                    font_metadata = create_font_metadata(
                        run.font_family,
                        size_pt=run.font_size_pt
                    )

                    # Calculate precise layout using TextLayoutEngine
                    layout_result = self.text_layout_engine.calculate_text_layout(
                        svg_x=text_frame.bbox.x,
                        svg_y=text_frame.bbox.y,
                        text=run.text,
                        font_metadata=font_metadata,
                        anchor=text_frame.anchor
                    )

                    enhanced_positioning[f'run_{i}'] = {
                        'x_emu': layout_result.x_emu,
                        'y_emu': layout_result.y_emu,
                        'width_emu': layout_result.width_emu,
                        'height_emu': layout_result.height_emu,
                        'baseline_x_emu': layout_result.baseline_x_emu,
                        'baseline_y_emu': layout_result.baseline_y_emu,
                        'layout_time_ms': layout_result.layout_time_ms
                    }
                    text_layout_applied = True

            except Exception as e:
                self.logger.warning(f"TextLayoutEngine processing failed: {e}")
                text_layout_applied = False

        # Step 3: Generate enhanced XML with Clean Slate improvements
        if font_analysis_used or text_layout_applied:
            xml_content = self._generate_clean_slate_xml(
                text_frame, enhanced_font_analysis, enhanced_positioning, base_xml
            )
            layout_method = "clean_slate_enhanced"
        else:
            # Fall back to base XML if enhancements failed
            xml_content = base_xml or self._generate_basic_text_xml(text_frame)
            layout_method = "clean_slate_basic"

        return TextProcessingResult(
            xml_content=xml_content,
            layout_method=layout_method,
            font_metrics_used=font_analysis_used,
            text_layout_applied=text_layout_applied,
            metadata={
                'enhanced_font_analysis': enhanced_font_analysis,
                'enhanced_positioning': enhanced_positioning,
                'run_count': len(runs),
                'processing_method': 'clean_slate',
                'font_system_used': font_analysis_used,
                'text_layout_engine_used': text_layout_applied
            }
        )

    def _process_with_legacy_system(self, text_frame: TextFrame, base_xml: str) -> TextProcessingResult:
        """Process text using existing comprehensive text system"""

        # Step 1: Use FontService for enhanced font metrics
        enhanced_metrics = {}
        font_metrics_used = False

        runs = self._get_runs(text_frame)
        if self.font_service and runs:
            try:
                for run in runs:
                    metrics = self.font_service.get_metrics(run.font_family)
                    enhanced_metrics[run.font_family] = {
                        'ascent': metrics.ascent,
                        'descent': metrics.descent,
                        'available': True
                    }
                    font_metrics_used = True

                    # Enhanced text width measurement if available
                    if hasattr(self.font_service, 'measure_text_width'):
                        try:
                            text_width = self.font_service.measure_text_width(
                                run.text, run.font_family, run.font_size_pt
                            )
                            enhanced_metrics[run.font_family]['measured_width'] = text_width
                        except Exception:
                            pass  # Width measurement optional

            except Exception as e:
                self.logger.warning(f"FontService processing failed: {e}")
                font_metrics_used = False

        # Step 2: Use text layout utilities for enhanced positioning
        text_layout_applied = False
        enhanced_positioning = {}

        if self._has_text_layout and self.services and hasattr(text_frame, 'bbox'):
            try:
                # Use svg_text_to_ppt_box for enhanced coordinate conversion
                for i, run in enumerate(runs):
                    if hasattr(text_frame, 'anchor'):
                        anchor_str = text_frame.anchor.value if hasattr(text_frame.anchor, 'value') else str(text_frame.anchor)

                        # Convert TextAnchor enum to string
                        if text_frame.anchor == TextAnchor.START:
                            anchor_str = 'start'
                        elif text_frame.anchor == TextAnchor.MIDDLE:
                            anchor_str = 'middle'
                        elif text_frame.anchor == TextAnchor.END:
                            anchor_str = 'end'

                        x_emu, y_emu, width_emu, height_emu = svg_text_to_ppt_box(
                            svg_x=text_frame.bbox.x,
                            svg_y=text_frame.bbox.y,
                            anchor=anchor_str,
                            text=run.text,
                            font_family=run.font_family,
                            font_size_pt=run.font_size_pt,
                            services=self.services
                        )

                        enhanced_positioning[f'run_{i}'] = {
                            'x_emu': x_emu,
                            'y_emu': y_emu,
                            'width_emu': width_emu,
                            'height_emu': height_emu,
                            'layout_enhanced': True
                        }
                        text_layout_applied = True

            except Exception as e:
                self.logger.warning(f"Text layout processing failed: {e}")
                text_layout_applied = False

        # Step 3: Generate enhanced XML with improved metrics and positioning
        if font_metrics_used or text_layout_applied:
            xml_content = self._generate_enhanced_text_xml(
                text_frame, enhanced_metrics, enhanced_positioning, base_xml
            )
            layout_method = "adapter_enhanced"
        else:
            # Fall back to base XML if enhancements failed
            xml_content = base_xml or self._generate_basic_text_xml(text_frame)
            layout_method = "basic_fallback"

        return TextProcessingResult(
            xml_content=xml_content,
            layout_method=layout_method,
            font_metrics_used=font_metrics_used,
            text_layout_applied=text_layout_applied,
            metadata={
                'enhanced_metrics': enhanced_metrics,
                'enhanced_positioning': enhanced_positioning,
                'run_count': len(runs),
                'processing_method': 'existing_system',
                'font_service_used': font_metrics_used,
                'text_layout_used': text_layout_applied
            }
        )

    def _generate_enhanced_text_xml(self, text_frame: TextFrame, enhanced_metrics: Dict[str, Any],
                                   enhanced_positioning: Dict[str, Any], base_xml: str) -> str:
        """Generate enhanced XML with improved font metrics and positioning"""

        # If we have enhanced positioning, use it
        if enhanced_positioning and 'run_0' in enhanced_positioning:
            pos = enhanced_positioning['run_0']
            x_emu = pos['x_emu']
            y_emu = pos['y_emu']
            width_emu = pos['width_emu']
            height_emu = pos['height_emu']

            # Enhanced positioning comment
            positioning_comment = f"<!-- Enhanced positioning: x={x_emu}, y={y_emu}, w={width_emu}, h={height_emu} -->"
        else:
            # Use original positioning
            EMU_PER_POINT = 12700
            bbox = text_frame.bbox
            x_emu = int(bbox.x * EMU_PER_POINT)
            y_emu = int(bbox.y * EMU_PER_POINT)
            width_emu = int(bbox.width * EMU_PER_POINT)
            height_emu = int(bbox.height * EMU_PER_POINT)
            positioning_comment = "<!-- Standard positioning -->"

        # Enhanced font metrics comment
        metrics_comment = ""
        if enhanced_metrics:
            font_families = list(enhanced_metrics.keys())
            metrics_comment = f"<!-- Enhanced font metrics for: {', '.join(font_families)} -->"

        # Generate enhanced text shape XML
        xml_content = f"""{positioning_comment}
{metrics_comment}
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="1" name="EnhancedTextFrame"/>
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
    </p:spPr>
    <p:txBody>
        <a:bodyPr wrap="none" rtlCol="0">
            <a:spAutoFit/>
        </a:bodyPr>
        <a:lstStyle/>
        {self._generate_enhanced_paragraphs_xml(text_frame, enhanced_metrics)}
    </p:txBody>
</p:sp>"""

        return xml_content

    def _generate_enhanced_paragraphs_xml(self, text_frame: TextFrame, enhanced_metrics: Dict[str, Any]) -> str:
        """Generate paragraph XML with enhanced font metrics"""
        # Convert anchor to alignment
        anchor_map = {
            TextAnchor.START: 'l',
            TextAnchor.MIDDLE: 'ctr',
            TextAnchor.END: 'r'
        }
        alignment = anchor_map.get(text_frame.anchor, 'l')

        # Generate enhanced runs
        runs_xml = []
        runs = self._get_runs(text_frame)
        for run in runs:
            # Use enhanced metrics if available
            font_size_hundredths = int(run.font_size_pt * 100)

            # Check if we have enhanced metrics for this font
            font_metrics = enhanced_metrics.get(run.font_family, {})
            metrics_comment = ""
            if font_metrics.get('available'):
                ascent = font_metrics.get('ascent', 0.82)
                descent = font_metrics.get('descent', 0.18)
                metrics_comment = f'<!-- Enhanced metrics: ascent={ascent:.3f}, descent={descent:.3f} -->'

            run_xml = f"""{metrics_comment}
    <a:r>
        <a:rPr sz="{font_size_hundredths}" b="{'1' if run.bold else '0'}" i="{'1' if run.italic else '0'}">
            <a:solidFill>
                <a:srgbClr val="{run.rgb}"/>
            </a:solidFill>
            <a:latin typeface="{run.font_family}"/>
        </a:rPr>
        <a:t>{self._escape_xml_text(run.text)}</a:t>
    </a:r>"""
            runs_xml.append(run_xml)

        paragraph_xml = f"""<a:p>
    <a:pPr algn="{alignment}"/>
    {chr(10).join(runs_xml)}
</a:p>"""

        return paragraph_xml

    def _generate_clean_slate_xml(self, text_frame: TextFrame, font_analysis: Dict[str, Any],
                                 positioning: Dict[str, Any], base_xml: str) -> str:
        """Generate enhanced XML using Clean Slate font analysis and positioning"""

        # Use enhanced positioning if available
        if positioning and 'run_0' in positioning:
            pos = positioning['run_0']
            x_emu = pos['x_emu']
            y_emu = pos['y_emu']
            width_emu = pos['width_emu']
            height_emu = pos['height_emu']

            # Clean Slate positioning comment
            positioning_comment = f"<!-- Clean Slate positioning: x={x_emu}, y={y_emu}, w={width_emu}, h={height_emu} -->"
        else:
            # Use original positioning
            bbox = text_frame.bbox if hasattr(text_frame, 'bbox') else None
            if bbox:
                x_emu = int(bbox.x)
                y_emu = int(bbox.y)
                width_emu = int(bbox.width)
                height_emu = int(bbox.height)
            else:
                # Fallback dimensions
                x_emu = y_emu = 0
                width_emu = height_emu = 100
            positioning_comment = "<!-- Standard positioning -->"

        # Font analysis comment
        font_comment = ""
        if font_analysis:
            strategies = [analysis.get('strategy', 'unknown') for analysis in font_analysis.values()]
            font_comment = f"<!-- Font strategies: {', '.join(strategies)} -->"

        # Generate Clean Slate enhanced text shape XML
        xml_content = f"""{positioning_comment}
{font_comment}
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="1" name="CleanSlateTextFrame"/>
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
    </p:spPr>
    <p:txBody>
        <a:bodyPr wrap="none" rtlCol="0">
            <a:spAutoFit/>
        </a:bodyPr>
        <a:lstStyle/>
        {self._generate_clean_slate_paragraphs_xml(text_frame, font_analysis)}
    </p:txBody>
</p:sp>"""

        return xml_content

    def _generate_clean_slate_paragraphs_xml(self, text_frame: TextFrame, font_analysis: Dict[str, Any]) -> str:
        """Generate paragraph XML with Clean Slate font analysis"""
        # Convert anchor to alignment
        anchor_map = {
            TextAnchor.START: 'l',
            TextAnchor.MIDDLE: 'ctr',
            TextAnchor.END: 'r'
        }
        alignment = anchor_map.get(text_frame.anchor, 'l')

        # Generate enhanced runs with font strategy information
        runs_xml = []
        runs = self._get_runs(text_frame)
        for i, run in enumerate(runs):
            # Use font analysis if available
            font_size_hundredths = int(run.font_size_pt * 100)

            # Check if we have font analysis for this run
            run_analysis = font_analysis.get(f'run_{i}', {})
            analysis_comment = ""
            if run_analysis:
                strategy = run_analysis.get('strategy', 'unknown')
                confidence = run_analysis.get('confidence', 0.0)
                analysis_comment = f'<!-- Font strategy: {strategy}, confidence: {confidence:.2f} -->'

            run_xml = f"""{analysis_comment}
    <a:r>
        <a:rPr sz="{font_size_hundredths}" b="{'1' if run.bold else '0'}" i="{'1' if run.italic else '0'}">
            <a:solidFill>
                <a:srgbClr val="{run.rgb}"/>
            </a:solidFill>
            <a:latin typeface="{run.font_family}"/>
        </a:rPr>
        <a:t>{self._escape_xml_text(run.text)}</a:t>
    </a:r>"""
            runs_xml.append(run_xml)

        paragraph_xml = f"""<a:p>
    <a:pPr algn="{alignment}"/>
    {chr(10).join(runs_xml)}
</a:p>"""

        return paragraph_xml

    def _escape_xml_text(self, text: str) -> str:
        """Escape text for XML content"""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&apos;'))

    def _generate_basic_text_xml(self, text_frame: TextFrame) -> str:
        """Generate basic text XML when enhancements are not available"""
        EMU_PER_POINT = 12700
        bbox = text_frame.bbox
        x_emu = int(bbox.x * EMU_PER_POINT)
        y_emu = int(bbox.y * EMU_PER_POINT)
        width_emu = int(bbox.width * EMU_PER_POINT)
        height_emu = int(bbox.height * EMU_PER_POINT)

        xml_content = f"""<!-- Basic text processing -->
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="1" name="BasicTextFrame"/>
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
    </p:spPr>
    <p:txBody>
        <a:bodyPr wrap="none" rtlCol="0">
            <a:spAutoFit/>
        </a:bodyPr>
        <a:lstStyle/>
        <a:p>
            <a:pPr algn="l"/>
            <a:r>
                <a:rPr sz="1200">
                    <a:solidFill>
                        <a:srgbClr val="000000"/>
                    </a:solidFill>
                    <a:latin typeface="Arial"/>
                </a:rPr>
                <a:t>Basic Text</a:t>
            </a:r>
        </a:p>
    </p:txBody>
</p:sp>"""

        return xml_content

    def _process_fallback_text(self, text_frame: TextFrame, base_xml: str) -> TextProcessingResult:
        """Fallback text processing when existing system unavailable"""

        xml_content = base_xml or self._generate_basic_text_xml(text_frame)

        return TextProcessingResult(
            xml_content=xml_content,
            layout_method="fallback_placeholder",
            font_metrics_used=False,
            text_layout_applied=False,
            metadata={
                'processing_method': 'fallback_placeholder',
                'reason': 'text_system_unavailable',
                'run_count': len(self._get_runs(text_frame))
            }
        )

    def validate_font_availability(self, font_family: str) -> bool:
        """Validate if font is available using FontService"""
        if not self.font_service:
            return False

        try:
            metrics = self.font_service.get_metrics(font_family)
            return metrics is not None
        except Exception:
            return False

    def measure_text_dimensions(self, text: str, font_family: str, font_size_pt: float) -> Tuple[float, float]:
        """Measure text dimensions using FontService if available"""
        if not self.font_service:
            # Fallback estimation
            char_width = font_size_pt * 0.6  # Rough estimate
            return len(text) * char_width, font_size_pt * 1.2

        try:
            if hasattr(self.font_service, 'measure_text_width'):
                width = self.font_service.measure_text_width(text, font_family, font_size_pt)
                height = font_size_pt * 1.2  # Standard line height
                return width, height
            else:
                # Fallback estimation
                char_width = font_size_pt * 0.6
                return len(text) * char_width, font_size_pt * 1.2
        except Exception:
            # Fallback estimation
            char_width = font_size_pt * 0.6
            return len(text) * char_width, font_size_pt * 1.2

    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get statistics about text processing system usage"""
        return {
            'clean_slate_available': self._clean_slate_available,
            'legacy_system_available': self._legacy_available,
            'components_initialized': {
                'font_system': hasattr(self, 'font_system') and self.font_system is not None,
                'text_layout_engine': hasattr(self, 'text_layout_engine') and self.text_layout_engine is not None,
                'legacy_font_service': hasattr(self, 'font_service') and self.font_service is not None
            },
            'features_available': {
                'font_analysis': self._clean_slate_available,
                'font_strategy_decisions': self._clean_slate_available,
                'precise_layout_calculation': self._clean_slate_available,
                'font_metadata_integration': self._clean_slate_available,
                'legacy_font_metrics': self._legacy_available,
                'legacy_text_measurement': self._legacy_available
            }
        }


def create_text_adapter(services=None) -> TextProcessingAdapter:
    """Create text processing adapter instance"""
    return TextProcessingAdapter(services)