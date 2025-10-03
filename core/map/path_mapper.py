#!/usr/bin/env python3
"""
Path Mapper

Maps IR.Path elements to DrawingML or EMF based on policy decisions.
Leverages battle-tested path generation components via adapters.
"""

import time
import logging
from typing import Dict, Any, Optional
from lxml import etree as ET

from ..ir import IRElement, Path, Point, Segment, BezierSegment, LineSegment
from ..ir import SolidPaint, LinearGradientPaint, RadialGradientPaint, PatternPaint, GradientReferencePaint
from ..policy import Policy, PolicyDecision, PathDecision
from .base import Mapper, MapperResult, OutputFormat, MappingError
from ..utils.enhanced_xml_builder import EnhancedXMLBuilder
from ..converters.marker_processor import create_marker_processor

logger = logging.getLogger(__name__)


class PathMapper(Mapper):
    """
    Maps IR.Path elements to DrawingML or EMF output.

    Uses policy engine to decide between native DrawingML and EMF fallback
    based on path complexity, features, and target requirements.

    Integrates with existing PathSystem for battle-tested path processing.
    """

    def __init__(self, policy: Policy, path_system: Optional[Any] = None, services=None):
        """
        Initialize path mapper.

        Args:
            policy: Policy engine for decision making
            path_system: Optional existing PathSystem for integration
            services: Optional ConversionServices for gradient resolution, etc.
        """
        super().__init__(policy, services)
        self.logger = logging.getLogger(__name__)

        # Integration with existing PathSystem
        self.path_system = path_system

        # Enhanced XML builder for template-based generation
        self.xml_builder = EnhancedXMLBuilder()

        # Marker processor for arrowheads and line decorations
        self.marker_processor = create_marker_processor()

        # Adapter initialization (will be connected to legacy components)
        self._drawingml_adapter = None
        self._emf_adapter = None

    def can_map(self, element: IRElement) -> bool:
        """Check if element is a Path"""
        return isinstance(element, Path)

    def map(self, path: Path) -> MapperResult:
        """
        Map Path element to appropriate output format.

        Args:
            path: Path IR element

        Returns:
            MapperResult with DrawingML or EMF content

        Raises:
            MappingError: If mapping fails
        """
        start_time = time.perf_counter()

        try:
            # Tracer hook: trace element entering map stage
            from ..debug import get_tracer
            tracer = get_tracer()
            element_id = getattr(path, 'id', 'path_unknown')
            tracer.trace_map(
                element_id=element_id,
                mapper_type='PathMapper',
                decision={'stage': 'entering'},
                location="path_mapper.py:map"
            )

            # Get policy decision
            decision = self.policy.decide_path(path)

            # Map based on decision
            if decision.use_native:
                result = self._map_to_drawingml(path, decision)
            else:
                result = self._map_to_emf(path, decision)

            # Record timing
            result.processing_time_ms = (time.perf_counter() - start_time) * 1000

            # Record statistics
            self._record_mapping(result)

            # Tracer hook: trace element exiting map stage
            tracer.trace_map_exit(
                element_id=element_id,
                output_format=result.output_format.value if hasattr(result.output_format, 'value') else str(result.output_format),
                output_size=result.output_size_bytes
            )

            return result

        except Exception as e:
            self._record_error(e)
            raise MappingError(f"Failed to map path: {e}", element=path, cause=e)

    def _map_to_drawingml(self, path: Path, decision: PathDecision) -> MapperResult:
        """Map path to native DrawingML format"""
        try:
            # Use existing PathSystem if available
            if self.path_system and hasattr(path, 'data'):
                try:
                    # Leverage battle-tested PathSystem
                    result = self.path_system.process_path(path.data)

                    if result.success:
                        # Extract hyperlink information
                        hyperlink_info = self._extract_hyperlink_info(path)

                        return MapperResult(
                            element=path,
                            output_format=OutputFormat.NATIVE_DML,
                            xml_content=self._wrap_path_xml(result.path_xml, path),
                            policy_decision=decision,
                            metadata={
                                'used_existing_path_system': True,
                                'path_segments': len(path.segments) if path.segments else 0,
                                'complexity_score': getattr(path, 'complexity_score', 0.5),
                                'processing_method': 'existing_system'
                            },
                            estimated_quality=decision.estimated_quality or 0.98,
                            estimated_performance=decision.estimated_performance or 0.95,
                            output_size_bytes=len(result.path_xml.encode('utf-8')),
                            **hyperlink_info
                        )
                except Exception as e:
                    self.logger.warning(f"Existing PathSystem failed, falling back to native implementation: {e}")

            # Fallback to native implementation
            return self._map_to_drawingml_native(path, decision)

        except Exception as e:
            raise MappingError(f"Failed to generate DrawingML for path: {e}", path, e)

    def _map_to_drawingml_native(self, path: Path, decision: PathDecision) -> MapperResult:
        """Map path to native DrawingML format using clean slate implementation"""
        try:
            # Generate path data string
            path_data = self._generate_path_data(path)

            # Generate fill XML
            fill_xml = self._generate_fill_xml(path.fill) if path.fill else ""

            # Generate stroke XML
            stroke_xml = self._generate_stroke_xml(path.stroke) if path.stroke else ""

            # Generate clipping XML
            clip_xml = self._generate_clip_xml(path.clip) if path.clip else ""

            # Calculate bounds for positioning
            bbox = getattr(path, 'bbox', None)
            if bbox:
                x_emu = int(bbox.x * 12700)  # Convert to EMU (1 point = 12700 EMU)
                y_emu = int(bbox.y * 12700)
                width_emu = int(bbox.width * 12700)
                height_emu = int(bbox.height * 12700)
            else:
                # Default bounds if bbox not available
                x_emu = y_emu = 0
                width_emu = height_emu = 914400  # 1 inch in EMU

            # Generate complete shape XML using enhanced XML builder
            path_element = self.xml_builder.generate_path_shape(
                path_id=1,  # TODO: Use proper ID from context
                x_emu=x_emu,
                y_emu=y_emu,
                width_emu=width_emu,
                height_emu=height_emu,
                path_data=path_data,
                fill_xml=fill_xml if fill_xml else None,
                stroke_xml=stroke_xml if stroke_xml else None,
                clip_xml=clip_xml if clip_xml else None
            )

            # Convert Element back to XML string
            xml_content = self.xml_builder.element_to_string(path_element)

            # Apply filter effects if present
            filter_applied = False
            if path.filter:
                enhanced_xml = self._apply_filter_effects(xml_content, path.filter)
                if enhanced_xml:
                    xml_content = enhanced_xml
                    filter_applied = True
                    self.logger.debug(f"Filter {path.filter} applied to path {path.id}")

            # Extract hyperlink information
            hyperlink_info = self._extract_hyperlink_info(path)

            return MapperResult(
                element=path,
                output_format=OutputFormat.NATIVE_DML,
                xml_content=xml_content,
                policy_decision=decision,
                metadata={
                    'path_segments': len(path.segments) if path.segments else 0,
                    'complexity_score': getattr(path, 'complexity_score', 0.5),
                    'bbox': bbox,
                    'has_fill': path.fill is not None,
                    'has_stroke': path.stroke is not None,
                    'has_clip': path.clip is not None,
                    'filter_applied': filter_applied,
                    'filter': path.filter if path.filter else None,
                    'processing_method': 'native_clean_slate'
                },
                estimated_quality=decision.estimated_quality or 0.95,
                estimated_performance=decision.estimated_performance or 0.9,
                output_size_bytes=len(xml_content.encode('utf-8')),
                **hyperlink_info
            )

        except Exception as e:
            raise MappingError(f"Failed to generate DrawingML for path: {e}", path, e)

    def _map_to_emf(self, path: Path, decision: PathDecision) -> MapperResult:
        """Map path to EMF fallback format using real EMF generation"""
        try:
            # Import EMF adapter
            from .emf_adapter import create_emf_adapter

            # Generate real EMF blob
            emf_adapter = create_emf_adapter()

            if not emf_adapter.can_generate_emf(path):
                # Fallback to placeholder if EMF generation not available
                return self._map_to_emf_placeholder(path, decision)

            # Generate actual EMF blob
            emf_result = emf_adapter.generate_emf_blob(path)

            # Create proper EMF picture XML using enhanced XML builder
            emf_pic_element = self.xml_builder.generate_path_emf_picture(
                path_id=1,  # TODO: Use proper ID from context
                x_emu=0,  # EMF pictures are positioned at origin
                y_emu=0,
                width_emu=emf_result.width_emu,
                height_emu=emf_result.height_emu,
                embed_id=emf_result.relationship_id
            )

            # Convert Element back to XML string
            xml_content = self.xml_builder.element_to_string(emf_pic_element)

            # Extract hyperlink information
            hyperlink_info = self._extract_hyperlink_info(path)

            return MapperResult(
                element=path,
                output_format=OutputFormat.EMF_VECTOR,
                xml_content=xml_content,
                policy_decision=decision,
                metadata={
                    'emf_generation': 'real_blob',
                    'emf_size_bytes': len(emf_result.emf_data),
                    'relationship_id': emf_result.relationship_id,
                    **emf_result.metadata
                },
                estimated_quality=emf_result.quality_score,
                estimated_performance=0.8,  # EMF processing overhead
                output_size_bytes=len(xml_content.encode('utf-8')),
                media_files=[{
                    'type': 'emf',
                    'data': emf_result.emf_data,
                    'relationship_id': emf_result.relationship_id
                }],
                **hyperlink_info
            )

        except Exception as e:
            self.logger.warning(f"EMF generation failed, using placeholder: {e}")
            return self._map_to_emf_placeholder(path, decision)

    def _map_to_emf_placeholder(self, path: Path, decision: PathDecision) -> MapperResult:
        """Fallback EMF implementation when real EMF generation fails"""
        try:
            bbox = getattr(path, 'bbox', None)
            if bbox:
                x_emu = int(bbox.x * 12700)
                y_emu = int(bbox.y * 12700)
                width_emu = int(bbox.width * 12700)
                height_emu = int(bbox.height * 12700)
            else:
                x_emu = y_emu = 0
                width_emu = height_emu = 914400

            # Generate placeholder EMF XML using enhanced XML builder
            # Note: EMF placeholders may have fill, stroke, clip styling
            fill_xml = self._generate_fill_xml(path.fill) if path.fill else None
            stroke_xml = self._generate_stroke_xml(path.stroke) if path.stroke else None
            clip_xml = self._generate_clip_xml(path.clip) if path.clip else None

            emf_placeholder_element = self.xml_builder.generate_path_emf_placeholder(
                path_id=1,  # TODO: Use proper ID from context
                x_emu=x_emu,
                y_emu=y_emu,
                width_emu=width_emu,
                height_emu=height_emu,
                embed_id="rId1",  # Placeholder embed ID
                fill_xml=fill_xml,
                stroke_xml=stroke_xml,
                clip_xml=clip_xml
            )

            # Convert Element back to XML string
            xml_content = self.xml_builder.element_to_string(emf_placeholder_element)

            # Extract hyperlink information
            hyperlink_info = self._extract_hyperlink_info(path)

            return MapperResult(
                element=path,
                output_format=OutputFormat.EMF_VECTOR,
                xml_content=xml_content,
                policy_decision=decision,
                metadata={
                    'emf_generation': 'placeholder',
                    'fallback_reason': 'EMF system not available',
                    'path_segments': len(path.segments) if path.segments else 0,
                    'complexity_score': getattr(path, 'complexity_score', 0.5),
                    'bbox': bbox
                },
                estimated_quality=0.7,  # Lower quality for placeholder
                estimated_performance=0.9,  # Faster than real EMF
                output_size_bytes=len(xml_content.encode('utf-8')),
                **hyperlink_info
            )

        except Exception as e:
            raise MappingError(f"Failed to generate EMF placeholder for path: {e}", path, e)

    def _generate_path_data(self, path: Path) -> str:
        """Generate DrawingML path data string from IR segments"""
        commands = []

        for i, segment in enumerate(path.segments):
            if isinstance(segment, LineSegment):
                if i == 0:
                    # First segment needs moveTo
                    commands.append(f'<a:moveTo><a:pt x="{self._coord_to_drawingml(segment.start.x)}" y="{self._coord_to_drawingml(segment.start.y)}"/></a:moveTo>')
                commands.append(f'<a:lnTo><a:pt x="{self._coord_to_drawingml(segment.end.x)}" y="{self._coord_to_drawingml(segment.end.y)}"/></a:lnTo>')

            elif isinstance(segment, BezierSegment):
                if i == 0:
                    # First segment needs moveTo
                    commands.append(f'<a:moveTo><a:pt x="{self._coord_to_drawingml(segment.start.x)}" y="{self._coord_to_drawingml(segment.start.y)}"/></a:moveTo>')

                commands.append(f'''<a:cubicBezTo>
    <a:pt x="{self._coord_to_drawingml(segment.control1.x)}" y="{self._coord_to_drawingml(segment.control1.y)}"/>
    <a:pt x="{self._coord_to_drawingml(segment.control2.x)}" y="{self._coord_to_drawingml(segment.control2.y)}"/>
    <a:pt x="{self._coord_to_drawingml(segment.end.x)}" y="{self._coord_to_drawingml(segment.end.y)}"/>
</a:cubicBezTo>''')

        # Close path if it's closed
        if path.is_closed:
            commands.append('<a:close/>')

        return '\n'.join(commands)

    def _coord_to_drawingml(self, coord: float) -> str:
        """Convert coordinate to DrawingML units (0-21600 range)"""
        # This is a simplified conversion - real implementation would
        # use the path's bounding box to normalize coordinates
        normalized = max(0, min(21600, int(coord * 100)))
        return str(normalized)

    def _generate_fill_xml(self, fill: Any) -> str:
        """Generate DrawingML fill XML from IR paint"""
        if isinstance(fill, GradientReferencePaint):
            # Resolve gradient reference using gradient_service
            gradient_xml = self.services.gradient_service.get_gradient_content(fill.gradient_id)
            if gradient_xml:
                return gradient_xml
            else:
                # Fallback if gradient not found
                self.logger.warning(f"Gradient not found: {fill.gradient_id}, using black fill")
                return '<a:solidFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:srgbClr val="000000"/></a:solidFill>'

        elif isinstance(fill, SolidPaint):
            return f'<a:solidFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:srgbClr val="{fill.rgb}"/></a:solidFill>'

        elif isinstance(fill, LinearGradientPaint):
            stops_xml = ""
            for stop in fill.stops:
                stops_xml += f'<a:gs pos="{int(stop.position * 1000)}"><a:srgbClr val="{stop.color}"/></a:gs>'

            angle = int(fill.angle * 60000)  # Convert to DrawingML angle units
            return f'''<a:gradFill flip="none" rotWithShape="1">
    <a:gsLst>{stops_xml}</a:gsLst>
    <a:lin ang="{angle}" scaled="1"/>
</a:gradFill>'''

        elif isinstance(fill, RadialGradientPaint):
            stops_xml = ""
            for stop in fill.stops:
                stops_xml += f'<a:gs pos="{int(stop.position * 1000)}"><a:srgbClr val="{stop.color}"/></a:gs>'

            return f'''<a:gradFill flip="none" rotWithShape="1">
    <a:gsLst>{stops_xml}</a:gsLst>
    <a:path path="circle">
        <a:fillToRect l="0" t="0" r="0" b="0"/>
    </a:path>
</a:gradFill>'''

        elif isinstance(fill, PatternPaint):
            # Pattern fills may use preset patterns or fall back to solid
            return f'<a:pattFill prst="{fill.preset or "pct5"}"><a:fgClr><a:srgbClr val="{fill.foreground}"/></a:fgClr><a:bgClr><a:srgbClr val="{fill.background}"/></a:bgClr></a:pattFill>'

        else:
            # Default to solid black
            return '<a:solidFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:srgbClr val="000000"/></a:solidFill>'

    def _generate_stroke_xml(self, stroke: Any) -> str:
        """Generate DrawingML stroke XML from IR stroke"""
        if not stroke:
            return '<a:ln><a:noFill/></a:ln>'

        width_emu = int(stroke.width * 12700)  # Convert to EMU
        xml = f'<a:ln w="{width_emu}">'

        # Stroke paint
        if hasattr(stroke, 'paint') and stroke.paint:
            xml += self._generate_fill_xml(stroke.paint)
        else:
            xml += '<a:solidFill><a:srgbClr val="000000"/></a:solidFill>'

        # Stroke properties - convert enum to DrawingML values
        if hasattr(stroke, 'cap') and stroke.cap:
            # Map StrokeCap enum to DrawingML cap style values
            cap_value = stroke.cap.value if hasattr(stroke.cap, 'value') else str(stroke.cap)
            # DrawingML expects: flat, rnd, sq
            cap_map = {'butt': 'flat', 'round': 'rnd', 'square': 'sq'}
            xml += f'<a:capStyle val="{cap_map.get(cap_value, cap_value)}"/>'

        if hasattr(stroke, 'join') and stroke.join:
            # Map StrokeJoin enum to DrawingML join style values
            join_value = stroke.join.value if hasattr(stroke.join, 'value') else str(stroke.join)
            # DrawingML expects: miter, round, bevel (already correct, but extract enum value)
            xml += f'<a:joinStyle val="{join_value}"/>'

        # Dash pattern
        if hasattr(stroke, 'dash_array') and stroke.dash_array:
            xml += '<a:prstDash val="dash"/>'

        xml += '</a:ln>'
        return xml

    def _generate_clip_xml(self, clip: Any) -> str:
        """Generate DrawingML clipping XML from IR clip reference using real clipping system"""
        if not clip:
            return ""

        try:
            # Import clipping adapter
            from .clipping_adapter import create_clipping_adapter

            # Generate real clipping using existing comprehensive system
            clipping_adapter = create_clipping_adapter(self.services)

            if not clipping_adapter.can_generate_clipping(clip):
                # Fallback to basic placeholder
                return f'<!-- Clipping Fallback: {clip.clip_id} -->'

            # Generate clipping with existing system integration
            clipping_result = clipping_adapter.generate_clip_xml(clip)

            # Log clipping strategy for debugging
            self.logger.debug(f"Clipping generated - Strategy: {clipping_result.strategy}, "
                            f"Complexity: {clipping_result.complexity}")

            return clipping_result.xml_content

        except Exception as e:
            self.logger.warning(f"Clipping generation failed, using placeholder: {e}")
            return f'<!-- Clipping Error: {clip.clip_id} - {str(e)} -->'

    def _apply_filter_effects(self, xml_content: str, filter_ref: str) -> Optional[str]:
        """
        Apply filter effects to shape XML by injecting filter DrawingML.

        Args:
            xml_content: Base shape XML to enhance
            filter_ref: Filter reference like "url(#blur)" or "#blur"

        Returns:
            Enhanced XML with filter effects, or None if filter not found/failed
        """
        if not self.services or not hasattr(self.services, 'filter_service'):
            self.logger.warning("Filter service not available")
            return None

        try:
            # Get filter DrawingML from service
            filter_xml = self.services.filter_service.get_filter_content(
                filter_ref, context=None
            )

            if not filter_xml:
                self.logger.warning(f"Filter not found: {filter_ref}")
                return None

            # Strategy: Insert filter XML before closing </p:spPr>
            # Find the insertion point
            insertion_point = xml_content.rfind('</p:spPr>')

            if insertion_point == -1:
                self.logger.warning("Could not find </p:spPr> tag for filter insertion")
                return None

            # Inject filter effects
            enhanced_xml = (
                xml_content[:insertion_point] +
                '\n' +
                filter_xml +
                '\n' +
                xml_content[insertion_point:]
            )

            self.logger.debug(f"Applied filter {filter_ref} to shape")
            return enhanced_xml

        except Exception as e:
            self.logger.error(f"Filter application failed for {filter_ref}: {e}")
            return None

    def _wrap_path_xml(self, path_xml: str, path: Path) -> str:
        """Wrap existing PathSystem XML in complete shape structure"""
        # Extract bounds from path if available
        bbox = getattr(path, 'bbox', None)
        if bbox:
            x_emu = int(bbox.x * 12700)
            y_emu = int(bbox.y * 12700)
            width_emu = int(bbox.width * 12700)
            height_emu = int(bbox.height * 12700)
        else:
            x_emu = y_emu = 0
            width_emu = height_emu = 914400

        # Generate fill/stroke XML for styling
        fill_xml = self._generate_fill_xml(path.fill) if path.fill else ""
        stroke_xml = self._generate_stroke_xml(path.stroke) if path.stroke else ""

        return f"""<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="1" name="Path_Existing"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:xfrm>
            <a:off x="{x_emu}" y="{y_emu}"/>
            <a:ext cx="{width_emu}" cy="{height_emu}"/>
        </a:xfrm>
        {path_xml}
        {fill_xml}
        {stroke_xml}
    </p:spPr>
</p:sp>"""

    def set_drawingml_adapter(self, adapter: Any) -> None:
        """Set adapter for legacy DrawingML generation"""
        self._drawingml_adapter = adapter

    def set_emf_adapter(self, adapter: Any) -> None:
        """Set adapter for EMF generation"""
        self._emf_adapter = adapter

    def set_path_system(self, path_system: Any) -> None:
        """Set existing PathSystem for integration"""
        self.path_system = path_system


def create_path_mapper(policy: Policy, path_system: Optional[Any] = None) -> PathMapper:
    """
    Create PathMapper with policy engine and optional existing PathSystem.

    Args:
        policy: Policy engine for decisions
        path_system: Optional existing PathSystem for integration

    Returns:
        Configured PathMapper
    """
    return PathMapper(policy, path_system)