#!/usr/bin/env python3
"""
Group Mapper

Maps IR.Group elements to DrawingML or EMF with intelligent flattening
and nested structure handling.
"""

import logging
import time
from typing import Any, Dict, Optional

from ..ir import Group, Image, IRElement, Path, TextFrame
from ..ir.shapes import Circle, Ellipse, Rectangle
from ..policy import GroupDecision, Policy
from .base import Mapper, MapperResult, MappingError, OutputFormat

logger = logging.getLogger(__name__)


class GroupMapper(Mapper):
    """
    Maps IR.Group elements to DrawingML or EMF output.

    Handles intelligent group flattening, nested structure optimization,
    and group-level clipping and transforms.
    """

    def __init__(self, policy: Policy, child_mappers: dict[str, Mapper] = None):
        """
        Initialize group mapper.

        Args:
            policy: Policy engine for decision making
            child_mappers: Mappers for child elements (path, text, image)
        """
        super().__init__(policy)
        self.logger = logging.getLogger(__name__)
        self.child_mappers = child_mappers or {}

    def can_map(self, element: IRElement) -> bool:
        """Check if element is a Group"""
        return isinstance(element, Group)

    def map(self, group: Group) -> MapperResult:
        """
        Map Group element to appropriate output format.

        Args:
            group: Group IR element

        Returns:
            MapperResult with DrawingML or EMF content

        Raises:
            MappingError: If mapping fails
        """
        start_time = time.perf_counter()

        try:
            # Get policy decision
            decision = self.policy.decide_group(group)

            # Map based on decision
            if decision.use_native:
                result = self._map_to_drawingml(group, decision)
            else:
                result = self._map_to_emf(group, decision)

            # Record timing
            result.processing_time_ms = (time.perf_counter() - start_time) * 1000

            # Record statistics
            self._record_mapping(result)

            return result

        except Exception as e:
            self._record_error(e)
            raise MappingError(f"Failed to map group: {e}", element=group, cause=e)

    def _map_to_drawingml(self, group: Group, decision: GroupDecision) -> MapperResult:
        """Map group to native DrawingML format"""
        try:
            # Decide whether to flatten or preserve group structure
            if decision.should_flatten:
                return self._map_flattened_group(group, decision)
            else:
                return self._map_nested_group(group, decision)

        except Exception as e:
            raise MappingError(f"Failed to generate DrawingML for group: {e}", group, e)

    def _map_flattened_group(self, group: Group, decision: GroupDecision) -> MapperResult:
        """Map group as flattened individual shapes"""
        try:
            # Map each child element individually
            child_results = []
            for child in group.children:
                child_mapper = self._get_child_mapper(child)
                if child_mapper:
                    child_result = child_mapper.map(child)
                    child_results.append(child_result.xml_content)
                else:
                    self.logger.warning(f"No mapper found for child type: {type(child)}")

            # Combine child XML content
            xml_content = '\n'.join(child_results)

            return MapperResult(
                element=group,
                output_format=OutputFormat.NATIVE_DML,
                xml_content=xml_content,
                policy_decision=decision,
                metadata={
                    'element_count': len(group.children),
                    'nesting_depth': 0,  # Flattened
                    'group_strategy': 'flattened',
                    'child_count': len(child_results),
                    'flattening_applied': True,
                },
                estimated_quality=decision.estimated_quality or 0.95,
                estimated_performance=decision.estimated_performance or 0.9,
                output_size_bytes=len(xml_content.encode('utf-8')),
            )

        except Exception as e:
            raise MappingError(f"Failed to flatten group: {e}", group, e)

    def _map_nested_group(self, group: Group, decision: GroupDecision) -> MapperResult:
        """Map group as nested structure with grouping preserved"""
        try:
            # Calculate group positioning
            bbox = group.bbox
            x_emu = int(bbox.x * 12700)  # Convert to EMU
            y_emu = int(bbox.y * 12700)
            width_emu = int(bbox.width * 12700)
            height_emu = int(bbox.height * 12700)

            # Map child elements
            child_xmls = []
            for child in group.children:
                child_mapper = self._get_child_mapper(child)
                if child_mapper:
                    child_result = child_mapper.map(child)
                    child_xmls.append(child_result.xml_content)
                else:
                    self.logger.warning(f"No mapper found for child type: {type(child)}")

            # Generate group clipping if needed
            clip_xml = self._generate_group_clip_xml(group.clip) if group.clip else ""

            # Generate opacity if needed
            opacity_xml = ""
            if group.opacity < 1.0:
                opacity_val = int(group.opacity * 100000)
                opacity_xml = f'<a:effectLst><a:alpha val="{opacity_val}"/></a:effectLst>'

            # Create group shape
            xml_content = f"""<p:grpSp>
    <p:nvGrpSpPr>
        <p:cNvPr id="1" name="Group"/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
    </p:nvGrpSpPr>
    <p:grpSpPr>
        <a:xfrm>
            <a:off x="{x_emu}" y="{y_emu}"/>
            <a:ext cx="{width_emu}" cy="{height_emu}"/>
            <a:chOff x="0" y="0"/>
            <a:chExt cx="{width_emu}" cy="{height_emu}"/>
        </a:xfrm>
        {opacity_xml}
        {clip_xml}
    </p:grpSpPr>
    {chr(10).join(child_xmls)}
</p:grpSp>"""

            return MapperResult(
                element=group,
                output_format=OutputFormat.NATIVE_DML,
                xml_content=xml_content,
                policy_decision=decision,
                metadata={
                    'element_count': len(group.children),
                    'nesting_depth': decision.nesting_depth,
                    'group_strategy': 'nested',
                    'child_count': len(child_xmls),
                    'has_opacity': group.opacity < 1.0,
                    'has_clipping': group.clip is not None,
                },
                estimated_quality=decision.estimated_quality or 0.95,
                estimated_performance=decision.estimated_performance or 0.85,
                output_size_bytes=len(xml_content.encode('utf-8')),
            )

        except Exception as e:
            raise MappingError(f"Failed to create nested group: {e}", group, e)

    def _map_to_emf(self, group: Group, decision: GroupDecision) -> MapperResult:
        """Map group to EMF fallback format"""
        try:
            # For complex groups, render entire group as EMF
            bbox = group.bbox
            x_emu = int(bbox.x * 12700)
            y_emu = int(bbox.y * 12700)
            width_emu = int(bbox.width * 12700)
            height_emu = int(bbox.height * 12700)

            xml_content = f"""<p:pic>
    <p:nvPicPr>
        <p:cNvPr id="1" name="EMF_Group"/>
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
                element=group,
                output_format=OutputFormat.EMF_VECTOR,
                xml_content=xml_content,
                policy_decision=decision,
                metadata={
                    'fallback_reason': 'Complex group structure requires EMF',
                    'element_count': len(group.children),
                    'nesting_depth': decision.nesting_depth,
                    'bbox': bbox,
                    'emf_required': True,
                },
                estimated_quality=0.98,  # EMF preserves full fidelity
                estimated_performance=0.8,   # Slower than native
                output_size_bytes=len(xml_content.encode('utf-8')),
            )

        except Exception as e:
            raise MappingError(f"Failed to generate EMF for group: {e}", group, e)

    def _get_child_mapper(self, child: IRElement) -> Mapper | None:
        """Get appropriate mapper for child element"""
        if isinstance(child, Path):
            return self.child_mappers.get('path')
        elif isinstance(child, TextFrame):
            return self.child_mappers.get('text')
        elif isinstance(child, Image):
            return self.child_mappers.get('image')
        elif isinstance(child, Circle):
            return self.child_mappers.get('circle')
        elif isinstance(child, Ellipse):
            return self.child_mappers.get('ellipse')
        elif isinstance(child, Rectangle):
            return self.child_mappers.get('rectangle')
        elif isinstance(child, Group):
            return self  # Recursive group mapping
        else:
            return None

    def _generate_group_clip_xml(self, clip_ref: Any) -> str:
        """Generate group-level clipping XML"""
        if not clip_ref:
            return ""

        # Simplified clipping - real implementation would integrate
        # with clipping preprocessing results
        return f'<!-- Group clipping: {clip_ref.clip_id} -->'

    def set_child_mappers(self, mappers: dict[str, Mapper]) -> None:
        """Set child element mappers"""
        self.child_mappers.update(mappers)

    def supports_flattening(self) -> bool:
        """Check if group mapper supports flattening optimization"""
        return True

    def get_flattening_statistics(self) -> dict[str, int]:
        """Get group flattening statistics"""
        stats = self.get_statistics()
        return {
            'total_groups': stats['total_mapped'],
            'flattened_groups': stats.get('flattened_count', 0),
            'nested_groups': stats.get('nested_count', 0),
            'emf_groups': stats['emf_count'],
        }


def create_group_mapper(policy: Policy, child_mappers: dict[str, Mapper] = None) -> GroupMapper:
    """
    Create GroupMapper with policy engine and child mappers.

    Args:
        policy: Policy engine for decisions
        child_mappers: Dictionary of child element mappers

    Returns:
        Configured GroupMapper
    """
    return GroupMapper(policy, child_mappers)