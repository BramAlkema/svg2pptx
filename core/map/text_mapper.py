#!/usr/bin/env python3
"""
Text Mapper

Maps IR.TextFrame elements to DrawingML or EMF with documented text fixes applied.
Implements all critical text positioning and alignment corrections.
"""

import time
import logging
from typing import List

from ..ir import IRElement, TextFrame, RichTextFrame, Run, TextAnchor
from ..policy import Policy, TextDecision
from .base import Mapper, MapperResult, OutputFormat, MappingError

logger = logging.getLogger(__name__)

# Constants for text fixes (matching documented issues)
EMU_PER_POINT = 12700  # Correct point-to-EMU conversion
BASELINE_ADJUSTMENT_FACTOR = 0.05  # Conservative 5% baseline shift


class TextMapper(Mapper):
    """
    Maps IR.TextFrame elements to DrawingML or EMF output.

    Implements all documented text fixes:
    1. Raw anchor handling (no double mapping)
    2. Per-tspan styling inheritance
    3. Conservative baseline calculation
    4. Proper paragraph alignment separation
    """

    def __init__(self, policy: Policy, services=None):
        """
        Initialize text mapper.

        Args:
            policy: Policy engine for decision making
            services: Optional services for text processing integration
        """
        super().__init__(policy)
        self.logger = logging.getLogger(__name__)
        self.services = services

        # Initialize text processing adapter
        try:
            from .text_adapter import create_text_adapter
            self.text_adapter = create_text_adapter(services)
            self._has_text_adapter = True
        except ImportError:
            self.text_adapter = None
            self._has_text_adapter = False
            self.logger.warning("Text adapter not available - using standard text processing")

        # Text anchor mapping (direct, no double mapping)
        self._anchor_map = {
            TextAnchor.START: 'l',    # Left alignment
            TextAnchor.MIDDLE: 'ctr', # Center alignment
            TextAnchor.END: 'r'       # Right alignment
        }

    def can_map(self, element: IRElement) -> bool:
        """Check if element is a TextFrame or RichTextFrame"""
        return isinstance(element, (TextFrame, RichTextFrame))

    def map(self, element) -> MapperResult:
        """
        Map TextFrame or RichTextFrame element to appropriate output format.

        Args:
            element: TextFrame or RichTextFrame IR element

        Returns:
            MapperResult with DrawingML or EMF content

        Raises:
            MappingError: If mapping fails
        """
        start_time = time.perf_counter()

        try:
            # Convert RichTextFrame to TextFrame if needed for policy decisions
            if isinstance(element, RichTextFrame):
                text_frame = element.to_text_frame()
            else:
                text_frame = element

            # Get policy decision
            decision = self.policy.decide_text(text_frame)

            # Map based on decision using original element
            if decision.use_native:
                result = self._map_to_drawingml(element, decision)
            else:
                result = self._map_to_emf(element, decision)

            # Record timing
            result.processing_time_ms = (time.perf_counter() - start_time) * 1000

            # Record statistics
            self._record_mapping(result)

            return result

        except Exception as e:
            self._record_error(e)
            raise MappingError(f"Failed to map text: {e}", element=element, cause=e)

    def _map_to_drawingml(self, element, decision: TextDecision) -> MapperResult:
        """Map text to native DrawingML format with all fixes applied"""
        try:
            # Convert RichTextFrame to TextFrame for compatibility if needed
            if isinstance(element, RichTextFrame):
                # Use RichTextFrame directly for enhanced processing
                text = element  # Keep original for enhanced processing
                text_frame = element.to_text_frame()  # For adapter compatibility
            else:
                text = element
                text_frame = element

            # Try to enhance text processing using text adapter if available
            if self._has_text_adapter and self.text_adapter.can_enhance_text_processing(text_frame):
                try:
                    # First generate standard XML with documented fixes
                    standard_xml = self._generate_standard_text_xml(text)

                    # Enhance with text adapter
                    processing_result = self.text_adapter.enhance_text_layout(text_frame, standard_xml)

                    # Use enhanced XML
                    xml_content = processing_result.xml_content
                    text_adapter_used = True
                    processing_metadata = processing_result.metadata

                except Exception as e:
                    self.logger.warning(f"Text adapter enhancement failed: {e}")
                    # Fall back to standard processing
                    xml_content = self._generate_standard_text_xml(text)
                    text_adapter_used = False
                    processing_metadata = {'processing_method': 'fallback'}
            else:
                # Standard processing without text adapter
                xml_content = self._generate_standard_text_xml(text)
                text_adapter_used = False
                processing_metadata = {'processing_method': 'standard'}

            return MapperResult(
                element=text,
                output_format=OutputFormat.NATIVE_DML,
                xml_content=xml_content,
                policy_decision=decision,
                metadata={
                    'run_count': len(text.runs),
                    'complexity_score': text.complexity_score,
                    'bbox': text.bbox,
                    'anchor': text.anchor.value if hasattr(text.anchor, 'value') else str(text.anchor),
                    'baseline_adjusted': True,
                    'fixes_applied': ['raw_anchor', 'per_tspan_styling', 'conservative_baseline', 'proper_alignment'],
                    'text_adapter_used': text_adapter_used,
                    'processing_metadata': processing_metadata
                },
                estimated_quality=decision.estimated_quality or 0.95,
                estimated_performance=decision.estimated_performance or 0.95,
                output_size_bytes=len(xml_content.encode('utf-8'))
            )

        except Exception as e:
            raise MappingError(f"Failed to generate DrawingML for text: {e}", text, e)

    def _generate_standard_text_xml(self, element) -> str:
        """Generate standard text XML with documented fixes applied"""
        # Handle both TextFrame and RichTextFrame
        if isinstance(element, RichTextFrame):
            # Use RichTextFrame properties - coordinates already in EMU from ConversionContext
            x_emu = int(element.position.x)
            y_emu = int(element.position.y)

            if element.bounds:
                width_emu = int(element.bounds.width)
                height_emu = int(element.bounds.height)
            else:
                # Estimate bounds for multi-line text (already in EMU)
                total_height = sum(line.primary_font_size * 1.2 for line in element.lines)
                max_width = max(
                    sum(len(run.text) * run.font_size_pt * 0.6 for run in line.runs)
                    for line in element.lines
                )
                width_emu = int(max_width * EMU_PER_POINT)
                height_emu = int(total_height * EMU_PER_POINT)

            # Apply baseline adjustment (documented fix #4)
            primary_font_size = element.lines[0].primary_font_size if element.lines else 12.0
            baseline_shift_emu = int(primary_font_size * EMU_PER_POINT * BASELINE_ADJUSTMENT_FACTOR)
            y_emu += baseline_shift_emu

            # Generate paragraph XML for each line
            paragraphs_xml = self._generate_rich_paragraphs_xml(element)
        else:
            # Handle TextFrame - coordinates already in EMU from ConversionContext
            bbox = element.bbox
            x_emu = int(bbox.x)
            y_emu = int(bbox.y)
            width_emu = int(bbox.width)
            height_emu = int(bbox.height)

            # Apply baseline adjustment (documented fix #4)
            baseline_shift_emu = int(element.primary_font_size * EMU_PER_POINT * BASELINE_ADJUSTMENT_FACTOR)
            y_emu += baseline_shift_emu

            # Generate paragraph XML with proper alignment separation
            paragraphs_xml = self._generate_paragraphs_xml(element)

        # Generate complete text shape XML
        xml_content = f"""<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="1" name="TextFrame"/>
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
        {paragraphs_xml}
    </p:txBody>
</p:sp>"""

        return xml_content

    def _map_to_emf(self, text: TextFrame, decision: TextDecision) -> MapperResult:
        """Map text to EMF fallback format"""
        try:
            # For EMF fallback, create a picture shape that would contain
            # rendered text with full fidelity - coordinates already in EMU from ConversionContext
            bbox = text.bbox
            x_emu = int(bbox.x)
            y_emu = int(bbox.y)
            width_emu = int(bbox.width)
            height_emu = int(bbox.height)

            xml_content = f"""<p:pic>
    <p:nvPicPr>
        <p:cNvPr id="1" name="EMF_Text"/>
        <p:cNvPicPr/>
        <p:nvPr/>
    </p:nvPicPr>
    <p:blipFill>
        <a:blip r:embed="rId1">
            <a:extLst>
                <a:ext uri="{{A7D7AC89-857B-4B46-9C2E-2B86D7B4E2B4}}">
                    <emf:emfBlip xmlns:emf="http://schemas.microsoft.com/office/drawing/2010/emf"/>
                </a:ext>
            </a:extLst>
        </a:blip>
        <a:stretch>
            <a:fillRect/>
        </a:stretch>
    </p:blipFill>
    <p:spPr>
        <a:xfrm>
            <a:off x="{x_emu}" y="{y_emu}"/>
            <a:ext cx="{width_emu}" cy="{height_emu}"/>
        </a:xfrm>
        <a:prstGeom prst="rect">
            <a:avLst/>
        </a:prstGeom>
    </p:spPr>
</p:pic>"""

            return MapperResult(
                element=text,
                output_format=OutputFormat.EMF_VECTOR,
                xml_content=xml_content,
                policy_decision=decision,
                metadata={
                    'fallback_reason': 'Complex text features require EMF',
                    'run_count': len(text.runs),
                    'complexity_score': text.complexity_score,
                    'bbox': bbox,
                    'emf_required': True
                },
                estimated_quality=0.98,  # EMF preserves full fidelity
                estimated_performance=0.85,  # Slightly slower than native
                output_size_bytes=len(xml_content.encode('utf-8'))
            )

        except Exception as e:
            raise MappingError(f"Failed to generate EMF for text: {e}", text, e)

    def _generate_paragraphs_xml(self, text: TextFrame) -> str:
        """Generate paragraph XML with proper alignment and run styling"""
        paragraphs = []

        if text.is_multiline:
            # Split runs into paragraphs at line breaks
            current_runs = []
            for run in text.runs:
                if '\n' in run.text:
                    # Split on newlines
                    parts = run.text.split('\n')
                    for i, part in enumerate(parts):
                        if part:  # Non-empty part
                            split_run = Run(
                                text=part,
                                font_family=run.font_family,
                                font_size_pt=run.font_size_pt,
                                bold=run.bold,
                                italic=run.italic,
                                underline=run.underline,
                                strike=run.strike,
                                rgb=run.rgb
                            )
                            current_runs.append(split_run)

                        if i < len(parts) - 1:  # Not the last part
                            # End of paragraph
                            if current_runs:
                                paragraphs.append(current_runs)
                                current_runs = []
                else:
                    current_runs.append(run)

            # Add remaining runs as final paragraph
            if current_runs:
                paragraphs.append(current_runs)
        else:
            # Single paragraph
            paragraphs.append(text.runs)

        # Generate XML for each paragraph
        paragraph_xmls = []
        for para_runs in paragraphs:
            para_xml = self._generate_paragraph_xml(para_runs, text.anchor)
            paragraph_xmls.append(para_xml)

        return '\n'.join(paragraph_xmls)

    def _generate_paragraph_xml(self, runs: List[Run], anchor: TextAnchor) -> str:
        """Generate single paragraph XML with proper alignment and run styling"""
        # Apply raw anchor handling (documented fix #1)
        alignment = self._anchor_map.get(anchor, 'l')

        # Generate runs XML with per-tspan styling (documented fix #2)
        runs_xml = []
        for run in runs:
            run_xml = self._generate_run_xml(run)
            runs_xml.append(run_xml)

        # Combine into paragraph with proper alignment separation (fix #4)
        paragraph_xml = f"""<a:p>
    <a:pPr algn="{alignment}"/>
    {chr(10).join(runs_xml)}
</a:p>"""

        return paragraph_xml

    def _generate_run_xml(self, run: Run) -> str:
        """Generate single run XML with complete styling inheritance"""
        # Convert font size to DrawingML units (fix #3: correct EMU conversion)
        font_size_hundredths = int(run.font_size_pt * 100)

        # Build style attributes
        style_attrs = []
        style_attrs.append(f'sz="{font_size_hundredths}"')

        if run.bold:
            style_attrs.append('b="1"')
        if run.italic:
            style_attrs.append('i="1"')
        if run.underline:
            style_attrs.append('u="sng"')
        if run.strike:
            style_attrs.append('strike="sngStrike"')

        style_xml = ' '.join(style_attrs)

        # Generate complete run XML
        run_xml = f"""<a:r>
    <a:rPr {style_xml}>
        <a:solidFill>
            <a:srgbClr val="{run.rgb}"/>
        </a:solidFill>
        <a:latin typeface="{run.font_family}"/>
    </a:rPr>
    <a:t>{self._escape_xml_text(run.text)}</a:t>
</a:r>"""

        return run_xml

    def _escape_xml_text(self, text: str) -> str:
        """Escape text for XML content"""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&apos;'))

    def _generate_rich_paragraphs_xml(self, element: RichTextFrame) -> str:
        """Generate paragraph XML for RichTextFrame with per-line styling"""
        paragraph_xmls = []

        for line in element.lines:
            # Generate runs XML with per-tspan styling (documented fix #2)
            runs_xml = []
            for run in line.runs:
                run_xml = self._generate_run_xml(run)
                runs_xml.append(run_xml)

            # Apply raw anchor handling (documented fix #1)
            alignment = self._anchor_map.get(line.anchor, 'l')

            # Combine into paragraph with proper alignment separation (fix #4)
            paragraph_xml = f"""<a:p>
    <a:pPr algn="{alignment}"/>
    {chr(10).join(runs_xml)}
</a:p>"""
            paragraph_xmls.append(paragraph_xml)

        return '\n'.join(paragraph_xmls)

    def get_text_fixes_applied(self) -> List[str]:
        """Get list of documented text fixes implemented"""
        return [
            'raw_anchor_handling',          # Fix #1: No double mapping
            'per_tspan_styling_inheritance', # Fix #2: Proper run styling
            'conservative_baseline_calc',    # Fix #3: 5% baseline adjustment
            'proper_alignment_separation'    # Fix #4: Paragraph vs run alignment
        ]


def create_text_mapper(policy: Policy, services=None) -> TextMapper:
    """
    Create TextMapper with policy engine.

    Args:
        policy: Policy engine for decisions
        services: Optional services for text processing integration

    Returns:
        Configured TextMapper with all text fixes applied
    """
    return TextMapper(policy, services)