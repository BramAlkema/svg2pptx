#!/usr/bin/env python3
"""
Path Mapper

Maps IR.Path elements to DrawingML or EMF based on policy decisions.
Leverages battle-tested path generation components via adapters.
"""

import logging
import time
from typing import Any, Optional

from ..ir import (
    BezierSegment,
    IRElement,
    LinearGradientPaint,
    LineSegment,
    Path,
    PatternPaint,
    RadialGradientPaint,
    SolidPaint,
)
from ..policy import PathDecision, Policy
from .base import Mapper, MapperResult, MappingError, OutputFormat

logger = logging.getLogger(__name__)


class PathMapper(Mapper):
    """
    Maps IR.Path elements to DrawingML or EMF output.

    Uses policy engine to decide between native DrawingML and EMF fallback
    based on path complexity, features, and target requirements.

    Integrates with existing PathSystem for battle-tested path processing.
    """

    def __init__(self, policy: Policy, path_system: Any | None = None):
        """
        Initialize path mapper.

        Args:
            policy: Policy engine for decision making
            path_system: Optional existing PathSystem for integration
        """
        super().__init__(policy)
        self.logger = logging.getLogger(__name__)

        # Integration with existing PathSystem
        self.path_system = path_system

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
                        return MapperResult(
                            element=path,
                            output_format=OutputFormat.NATIVE_DML,
                            xml_content=self._wrap_path_xml(result.path_xml, path),
                            policy_decision=decision,
                            metadata={
                                'used_existing_path_system': True,
                                'path_segments': len(path.segments) if path.segments else 0,
                                'complexity_score': getattr(path, 'complexity_score', 0.5),
                                'processing_method': 'existing_system',
                            },
                            estimated_quality=decision.estimated_quality or 0.98,
                            estimated_performance=decision.estimated_performance or 0.95,
                            output_size_bytes=len(result.path_xml.encode('utf-8')),
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

            # Get shape ID from path metadata or use default
            shape_id = getattr(path, 'shape_id', 1)

            # Generate complete shape XML with required PowerPoint elements
            xml_content = f"""<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="Path {shape_id}"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:xfrm>
            <a:off x="{x_emu}" y="{y_emu}"/>
            <a:ext cx="{width_emu}" cy="{height_emu}"/>
        </a:xfrm>
        <a:custGeom>
            <a:avLst/>
            <a:gdLst/>
            <a:ahLst/>
            <a:cxnLst/>
            <a:rect l="0" t="0" r="21600" b="21600"/>
            <a:pathLst>
                <a:path w="21600" h="21600">
                    {path_data}
                </a:path>
            </a:pathLst>
        </a:custGeom>
        {fill_xml}
        {stroke_xml}
        {clip_xml}
    </p:spPr>
    <p:style>
        <a:lnRef idx="1">
            <a:schemeClr val="accent1"/>
        </a:lnRef>
        <a:fillRef idx="3">
            <a:schemeClr val="accent1"/>
        </a:fillRef>
        <a:effectRef idx="2">
            <a:schemeClr val="accent1"/>
        </a:effectRef>
        <a:fontRef idx="minor">
            <a:schemeClr val="lt1"/>
        </a:fontRef>
    </p:style>
    <p:txBody>
        <a:bodyPr rtlCol="0" anchor="ctr"/>
        <a:lstStyle/>
        <a:p>
            <a:pPr algn="ctr"/>
        </a:p>
    </p:txBody>
</p:sp>"""

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
                    'processing_method': 'native_clean_slate',
                },
                estimated_quality=decision.estimated_quality or 0.95,
                estimated_performance=decision.estimated_performance or 0.9,
                output_size_bytes=len(xml_content.encode('utf-8')),
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

            # Create proper EMF picture XML with real relationship
            xml_content = f"""<p:pic>
    <p:nvPicPr>
        <p:cNvPr id="1" name="EMF_Path"/>
        <p:cNvPicPr/>
        <p:nvPr/>
    </p:nvPicPr>
    <p:blipFill>
        <a:blip r:embed="{emf_result.relationship_id}">
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
            <a:off x="0" y="0"/>
            <a:ext cx="{emf_result.width_emu}" cy="{emf_result.height_emu}"/>
        </a:xfrm>
        <a:prstGeom prst="rect">
            <a:avLst/>
        </a:prstGeom>
    </p:spPr>
</p:pic>"""

            return MapperResult(
                element=path,
                output_format=OutputFormat.EMF_VECTOR,
                xml_content=xml_content,
                policy_decision=decision,
                metadata={
                    'emf_generation': 'real_blob',
                    'emf_size_bytes': len(emf_result.emf_data),
                    'relationship_id': emf_result.relationship_id,
                    **emf_result.metadata,
                },
                estimated_quality=emf_result.quality_score,
                estimated_performance=0.8,  # EMF processing overhead
                output_size_bytes=len(xml_content.encode('utf-8')),
                media_files=[{
                    'type': 'emf',
                    'data': emf_result.emf_data,
                    'relationship_id': emf_result.relationship_id,
                }],
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

            # Placeholder EMF uses generic picture shape
            xml_content = f"""<p:pic>
    <p:nvPicPr>
        <p:cNvPr id="1" name="EMF_Path_Placeholder"/>
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
                element=path,
                output_format=OutputFormat.EMF_VECTOR,
                xml_content=xml_content,
                policy_decision=decision,
                metadata={
                    'emf_generation': 'placeholder',
                    'fallback_reason': 'EMF system not available',
                    'path_segments': len(path.segments) if path.segments else 0,
                    'complexity_score': getattr(path, 'complexity_score', 0.5),
                    'bbox': bbox,
                },
                estimated_quality=0.7,  # Lower quality for placeholder
                estimated_performance=0.9,  # Faster than real EMF
                output_size_bytes=len(xml_content.encode('utf-8')),
            )

        except Exception as e:
            raise MappingError(f"Failed to generate EMF placeholder for path: {e}", path, e)

    def _generate_path_data(self, path: Path) -> str:
        """Generate DrawingML path data string from IR segments"""
        commands = []

        # Get bounding box for coordinate normalization
        bbox = getattr(path, 'bbox', None)

        for i, segment in enumerate(path.segments):
            if isinstance(segment, LineSegment):
                if i == 0:
                    # First segment needs moveTo
                    commands.append(f'<a:moveTo><a:pt x="{self._coord_to_drawingml(segment.start.x, bbox)}" y="{self._coord_to_drawingml(segment.start.y, bbox, is_y=True)}"/></a:moveTo>')
                commands.append(f'<a:lnTo><a:pt x="{self._coord_to_drawingml(segment.end.x, bbox)}" y="{self._coord_to_drawingml(segment.end.y, bbox, is_y=True)}"/></a:lnTo>')

            elif isinstance(segment, BezierSegment):
                if i == 0:
                    # First segment needs moveTo
                    commands.append(f'<a:moveTo><a:pt x="{self._coord_to_drawingml(segment.start.x, bbox)}" y="{self._coord_to_drawingml(segment.start.y, bbox, is_y=True)}"/></a:moveTo>')

                commands.append(f'''<a:cubicBezTo>
    <a:pt x="{self._coord_to_drawingml(segment.control1.x, bbox)}" y="{self._coord_to_drawingml(segment.control1.y, bbox, is_y=True)}"/>
    <a:pt x="{self._coord_to_drawingml(segment.control2.x, bbox)}" y="{self._coord_to_drawingml(segment.control2.y, bbox, is_y=True)}"/>
    <a:pt x="{self._coord_to_drawingml(segment.end.x, bbox)}" y="{self._coord_to_drawingml(segment.end.y, bbox, is_y=True)}"/>
</a:cubicBezTo>''')

        # Close path if it's closed
        if path.is_closed:
            commands.append('<a:close/>')

        return '\n'.join(commands)

    def _coord_to_drawingml(self, coord: float, bbox: Any = None, is_y: bool = False) -> str:
        """Convert coordinate to DrawingML units (0-21600 range) normalized to bounding box"""
        if bbox:
            # Normalize coordinate relative to bounding box
            if is_y:
                # Y coordinate: normalize relative to bbox.y and bbox.height
                normalized = ((coord - bbox.y) / bbox.height) * 21600 if bbox.height > 0 else 0
            else:
                # X coordinate: normalize relative to bbox.x and bbox.width
                normalized = ((coord - bbox.x) / bbox.width) * 21600 if bbox.width > 0 else 0

            return str(int(max(0, min(21600, normalized))))
        else:
            # Fallback: simple scaling
            normalized = max(0, min(21600, int(coord * 100)))
            return str(normalized)

    def _generate_fill_xml(self, fill: Any) -> str:
        """Generate DrawingML fill XML from IR paint"""
        if isinstance(fill, SolidPaint):
            return f'<a:solidFill><a:srgbClr val="{fill.rgb}"/></a:solidFill>'

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
            return '<a:solidFill><a:srgbClr val="000000"/></a:solidFill>'

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

        # Stroke cap - map to DrawingML values
        if hasattr(stroke, 'cap') and stroke.cap:
            cap_map = {'butt': 'flat', 'round': 'rnd', 'square': 'sq'}
            cap_value = stroke.cap.value if hasattr(stroke.cap, 'value') else str(stroke.cap)
            dml_cap = cap_map.get(cap_value, 'flat')
            xml += f'<a:cap val="{dml_cap}"/>'

        # Stroke join - map to DrawingML elements
        if hasattr(stroke, 'join') and stroke.join:
            join_value = stroke.join.value if hasattr(stroke.join, 'value') else str(stroke.join)
            if join_value == 'miter':
                xml += '<a:miter/>'
            elif join_value == 'round':
                xml += '<a:round/>'
            elif join_value == 'bevel':
                xml += '<a:bevel/>'

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


def create_path_mapper(policy: Policy, path_system: Any | None = None) -> PathMapper:
    """
    Create PathMapper with policy engine and optional existing PathSystem.

    Args:
        policy: Policy engine for decisions
        path_system: Optional existing PathSystem for integration

    Returns:
        Configured PathMapper
    """
    return PathMapper(policy, path_system)