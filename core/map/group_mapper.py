#!/usr/bin/env python3
"""
Group Mapper

Maps IR.Group elements to DrawingML or EMF with intelligent flattening
and nested structure handling.
"""

import time
import logging
from typing import Dict, Any, Optional, List, Union
from lxml.etree import Element

from ..ir import IRElement, Group, Path, TextFrame, Image, Point, Rect
from ..policy import Policy, PolicyDecision, GroupDecision
from .base import Mapper, MapperResult, OutputFormat, MappingError
from ..utils.enhanced_xml_builder import EnhancedXMLBuilder

logger = logging.getLogger(__name__)


class GroupMapper(Mapper):
    """
    Maps IR.Group elements to DrawingML or EMF output.

    Handles intelligent group flattening, nested structure optimization,
    and group-level clipping and transforms.
    """

    def __init__(self, policy: Policy, services=None, child_mappers: Dict[str, Mapper] = None):
        """
        Initialize group mapper.

        Args:
            policy: Policy engine for decision making
            services: Optional ConversionServices for advanced functionality
            child_mappers: Mappers for child elements (path, text, image)
        """
        super().__init__(policy, services)
        self.logger = logging.getLogger(__name__)
        self.child_mappers = child_mappers or {}
        self.xml_builder = EnhancedXMLBuilder()

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
            # Get parent filter for propagation
            parent_filter = getattr(group, 'filter', None)

            # Map each child element individually
            child_results = []
            for child in group.children:
                # Propagate parent filter to child if needed
                child_with_filter = self._propagate_filter_to_child(child, parent_filter)

                child_mapper = self._get_child_mapper(child_with_filter)
                if child_mapper:
                    child_result = child_mapper.map(child_with_filter)
                    child_results.append(child_result.xml_content)
                else:
                    self.logger.warning(f"No mapper found for child type: {type(child)}")

            # Combine child XML content
            xml_content = '\n'.join(child_results)

            # Extract hyperlink information
            hyperlink_info = self._extract_hyperlink_info(group)

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
                    'flattening_applied': True
                },
                estimated_quality=decision.estimated_quality or 0.95,
                estimated_performance=decision.estimated_performance or 0.9,
                output_size_bytes=len(xml_content.encode('utf-8')),
                **hyperlink_info
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

            # Get parent filter for propagation
            parent_filter = getattr(group, 'filter', None)

            # Map child elements
            child_xmls = []
            for child in group.children:
                # Propagate parent filter to child if needed
                child_with_filter = self._propagate_filter_to_child(child, parent_filter)

                child_mapper = self._get_child_mapper(child_with_filter)
                if child_mapper:
                    child_result = child_mapper.map(child_with_filter)
                    child_xmls.append(child_result.xml_content)
                else:
                    self.logger.warning(f"No mapper found for child type: {type(child)}")

            # Generate group clipping if needed
            clip_xml = self._generate_group_clip_xml(group.clip) if group.clip else None

            # Convert child XML strings to Elements for template-based generation
            child_elements = []
            for child_xml in child_xmls:
                try:
                    # Parse child XML string to Element
                    from lxml import etree as ET
                    child_element = ET.fromstring(child_xml)
                    child_elements.append(child_element)
                except ET.XMLSyntaxError as e:
                    self.logger.warning(f"Failed to parse child XML: {e}")
                    continue

            # Create group shape using enhanced XML builder
            group_element = self.xml_builder.generate_group_shape(
                group_id=1,  # TODO: Use proper ID from context
                x_emu=x_emu,
                y_emu=y_emu,
                width_emu=width_emu,
                height_emu=height_emu,
                child_elements=child_elements,
                opacity=group.opacity if group.opacity < 1.0 else None,
                clip_xml=clip_xml
            )

            # Convert Element back to XML string
            xml_content = self.xml_builder.element_to_string(group_element)

            # Extract hyperlink information
            hyperlink_info = self._extract_hyperlink_info(group)

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
                    'has_clipping': group.clip is not None
                },
                estimated_quality=decision.estimated_quality or 0.95,
                estimated_performance=decision.estimated_performance or 0.85,
                output_size_bytes=len(xml_content.encode('utf-8')),
                **hyperlink_info
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

            # Create group picture using enhanced XML builder for EMF fallback
            group_pic_element = self.xml_builder.generate_group_picture(
                group_id=1,  # TODO: Use proper ID from context
                x_emu=x_emu,
                y_emu=y_emu,
                width_emu=width_emu,
                height_emu=height_emu,
                embed_id="rId1"  # EMF embed reference
            )

            # Convert Element back to XML string
            xml_content = self.xml_builder.element_to_string(group_pic_element)

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
                    'emf_required': True
                },
                estimated_quality=0.98,  # EMF preserves full fidelity
                estimated_performance=0.8,   # Slower than native
                output_size_bytes=len(xml_content.encode('utf-8')),
                **hyperlink_info
            )

        except Exception as e:
            raise MappingError(f"Failed to generate EMF for group: {e}", group, e)

    def _propagate_filter_to_child(self, child: IRElement, parent_filter: Optional[str]) -> IRElement:
        """
        Propagate parent group's filter to child if child doesn't have its own filter.

        Args:
            child: Child IR element
            parent_filter: Filter from parent group

        Returns:
            Child element with filter applied (returns original if no propagation needed)
        """
        if not parent_filter:
            return child

        # Check if child already has a filter
        if hasattr(child, 'filter') and child.filter:
            # Child has its own filter, don't override
            return child

        # Child doesn't have filter, propagate from parent
        # Create new instance with filter
        try:
            if isinstance(child, Path):
                return Path(
                    segments=child.segments,
                    fill=child.fill,
                    stroke=child.stroke,
                    clip=child.clip,
                    opacity=child.opacity,
                    transform=child.transform,
                    hyperlink=child.hyperlink,
                    navigation=child.navigation,
                    id=child.id,
                    filter=parent_filter
                )
            elif isinstance(child, TextFrame):
                return TextFrame(
                    origin=child.origin,
                    runs=child.runs,
                    bbox=child.bbox,
                    anchor=child.anchor,
                    line_height=child.line_height,
                    baseline_shift=child.baseline_shift,
                    hyperlink=child.hyperlink,
                    navigation=child.navigation,
                    id=child.id,
                    filter=parent_filter
                )
            elif isinstance(child, Image):
                return Image(
                    origin=child.origin,
                    size=child.size,
                    data=child.data,
                    format=child.format,
                    href=child.href,
                    clip=child.clip,
                    opacity=child.opacity,
                    transform=child.transform,
                    hyperlink=child.hyperlink,
                    navigation=child.navigation,
                    id=child.id,
                    filter=parent_filter
                )
            elif isinstance(child, Group):
                # For nested groups, propagate to the group itself
                return Group(
                    children=child.children,
                    clip=child.clip,
                    opacity=child.opacity,
                    transform=child.transform,
                    hyperlink=child.hyperlink,
                    navigation=child.navigation,
                    id=child.id,
                    filter=parent_filter
                )
            else:
                # Unknown type, return as-is
                return child
        except Exception as e:
            self.logger.warning(f"Failed to propagate filter to child: {e}")
            return child

    def _get_child_mapper(self, child: IRElement) -> Optional[Mapper]:
        """Get appropriate mapper for child element"""
        if isinstance(child, Path):
            return self.child_mappers.get('path')
        elif isinstance(child, TextFrame):
            return self.child_mappers.get('text')
        elif isinstance(child, Image):
            return self.child_mappers.get('image')
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

    def set_child_mappers(self, mappers: Dict[str, Mapper]) -> None:
        """Set child element mappers"""
        self.child_mappers.update(mappers)

    def supports_flattening(self) -> bool:
        """Check if group mapper supports flattening optimization"""
        return True

    def get_flattening_statistics(self) -> Dict[str, int]:
        """Get group flattening statistics"""
        stats = self.get_statistics()
        return {
            'total_groups': stats['total_mapped'],
            'flattened_groups': stats.get('flattened_count', 0),
            'nested_groups': stats.get('nested_count', 0),
            'emf_groups': stats['emf_count']
        }


def create_group_mapper(policy: Policy, child_mappers: Dict[str, Mapper] = None) -> GroupMapper:
    """
    Create GroupMapper with policy engine and child mappers.

    Args:
        policy: Policy engine for decisions
        child_mappers: Dictionary of child element mappers

    Returns:
        Configured GroupMapper
    """
    return GroupMapper(policy, child_mappers)