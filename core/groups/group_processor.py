#!/usr/bin/env python3
"""
Group Processing Engine

Enhanced group handling that integrates with the preprocessing pipeline
to provide optimized group conversion with transform flattening and
structure optimization.

Features:
- Preprocessing-aware group handling
- Transform hierarchy optimization
- Nested group flattening
- Clipping integration
- Performance optimization for complex groups
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
from lxml import etree as ET

from ..services.conversion_services import ConversionServices
from ..pre.resolve_clips import ResolveClipsPreprocessor
from ..xml.safe_iter import children

logger = logging.getLogger(__name__)


class GroupProcessor:
    """
    Processes SVG groups with preprocessing integration.

    Handles group elements that have been processed by the preprocessing
    pipeline and provides optimized conversion strategies.
    """

    def __init__(self, services: ConversionServices):
        """
        Initialize group processor.

        Args:
            services: ConversionServices container
        """
        self.services = services
        self.logger = logging.getLogger(__name__)

        # Initialize clipping preprocessor for integration
        self.clip_preprocessor = ResolveClipsPreprocessor(flatten_nested_clips=True)

        # Group processing statistics
        self.stats = {
            'groups_processed': 0,
            'groups_flattened': 0,
            'groups_with_clipping': 0,
            'nested_groups_resolved': 0
        }

    def process_group_element(self, group_element: ET.Element, context: Any,
                            apply_optimizations: bool = True) -> Dict[str, Any]:
        """
        Process a group element with preprocessing integration.

        Args:
            group_element: SVG group element (possibly preprocessed)
            context: Conversion context
            apply_optimizations: Whether to apply group optimizations

        Returns:
            Group processing information for conversion
        """
        self.stats['groups_processed'] += 1

        # Check if group has preprocessing metadata
        group_info = self._analyze_group_structure(group_element)

        # Determine processing strategy
        if apply_optimizations:
            group_info = self._apply_group_optimizations(group_element, group_info, context)

        # Process clipping if present
        if group_info['has_clipping']:
            group_info = self._process_group_clipping(group_element, group_info, context)
            self.stats['groups_with_clipping'] += 1

        # Process nested groups
        if group_info['has_nested_groups']:
            group_info = self._process_nested_groups(group_element, group_info, context)
            self.stats['nested_groups_resolved'] += 1

        self.logger.debug(f"Processed group with {len(group_info['children'])} children")
        return group_info

    def _analyze_group_structure(self, group_element: ET.Element) -> Dict[str, Any]:
        """Analyze group structure and metadata."""
        # Basic group information
        group_info = {
            'id': group_element.get('id', f'group_{id(group_element)}'),
            'transform': group_element.get('transform'),
            'has_clipping': False,
            'has_nested_groups': False,
            'has_preprocessing_metadata': False,
            'children': [],
            'clipping_info': None,
            'optimization_opportunities': [],
            'structure_complexity': 'simple'
        }

        # Check for clipping
        clip_path = group_element.get('clip-path')
        if clip_path:
            group_info['has_clipping'] = True
            group_info['clipping_info'] = {
                'clip_path_ref': clip_path,
                'from_preprocessing': group_element.get('data-clip-operation') is not None
            }

        # Check for preprocessing metadata
        if group_element.get('data-clip-operation'):
            group_info['has_preprocessing_metadata'] = True
            group_info['clipping_info'] = {
                'operation': group_element.get('data-clip-operation'),
                'source': group_element.get('data-clip-source', ''),
                'from_preprocessing': True
            }

        # Analyze children
        child_info = self._analyze_group_children(group_element)
        group_info.update(child_info)

        # Determine complexity
        group_info['structure_complexity'] = self._assess_group_complexity(group_info)

        return group_info

    def _analyze_group_children(self, group_element: ET.Element) -> Dict[str, Any]:
        """Analyze group children and structure."""
        child_nodes = []
        has_nested_groups = False
        transform_count = 0
        clipping_count = 0

        for child in children(group_element):
            child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

            # Skip metadata elements
            if child_tag in ['title', 'desc', 'metadata']:
                continue

            child_info = {
                'element': child,
                'tag': child_tag,
                'has_transform': child.get('transform') is not None,
                'has_clipping': child.get('clip-path') is not None or child.get('data-clip-operation') is not None,
                'is_group': child_tag == 'g',
                'is_clipping_mask': child.get('data-clip-role') == 'mask'
            }

            child_nodes.append(child_info)

            # Track structure information
            if child_info['is_group']:
                has_nested_groups = True

            if child_info['has_transform']:
                transform_count += 1

            if child_info['has_clipping']:
                clipping_count += 1

        return {
            'children': child_nodes,
            'has_nested_groups': has_nested_groups,
            'transform_count': transform_count,
            'clipping_count': clipping_count,
            'child_count': len(child_nodes)
        }

    def _assess_group_complexity(self, group_info: Dict[str, Any]) -> str:
        """Assess the complexity of a group structure."""
        child_count = group_info['child_count']
        transform_count = group_info['transform_count']
        clipping_count = group_info['clipping_count']
        has_nested = group_info['has_nested_groups']

        # Simple group
        if child_count <= 3 and transform_count <= 1 and clipping_count == 0 and not has_nested:
            return 'simple'

        # Complex group
        if child_count > 10 or transform_count > 5 or clipping_count > 2 or has_nested:
            return 'complex'

        # Moderate complexity
        return 'moderate'

    def _apply_group_optimizations(self, group_element: ET.Element,
                                 group_info: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Apply group optimizations based on structure analysis."""
        optimizations = []

        # Optimization 1: Transform flattening
        if self._can_flatten_transforms(group_info):
            optimizations.append('transform_flattening')
            group_info = self._apply_transform_flattening(group_element, group_info)

        # Optimization 2: Group unwrapping for single children
        if self._can_unwrap_group(group_info):
            optimizations.append('group_unwrapping')
            group_info['should_unwrap'] = True

        # Optimization 3: Nested group flattening
        if self._can_flatten_nested_groups(group_info):
            optimizations.append('nested_flattening')
            group_info = self._apply_nested_flattening(group_element, group_info)
            self.stats['groups_flattened'] += 1

        group_info['applied_optimizations'] = optimizations
        return group_info

    def _can_flatten_transforms(self, group_info: Dict[str, Any]) -> bool:
        """Check if transforms can be flattened."""
        # Can flatten if transforms are simple and no clipping
        return (group_info['transform_count'] > 1 and
                not group_info['has_clipping'] and
                group_info['structure_complexity'] != 'complex')

    def _can_unwrap_group(self, group_info: Dict[str, Any]) -> bool:
        """Check if group can be unwrapped (single child, no group-specific attributes)."""
        return (group_info['child_count'] == 1 and
                not group_info['has_clipping'] and
                not group_info['transform'] and
                not group_info['has_preprocessing_metadata'])

    def _can_flatten_nested_groups(self, group_info: Dict[str, Any]) -> bool:
        """Check if nested groups can be flattened."""
        return (group_info['has_nested_groups'] and
                group_info['structure_complexity'] != 'complex' and
                not group_info['has_clipping'])

    def _apply_transform_flattening(self, group_element: ET.Element,
                                  group_info: Dict[str, Any]) -> Dict[str, Any]:
        """Apply transform flattening optimization."""
        # Mark for transform flattening during conversion
        group_info['transform_flattening'] = {
            'enabled': True,
            'group_transform': group_element.get('transform'),
            'child_transforms': [
                child['element'].get('transform') for child in group_info['children']
                if child['has_transform']
            ]
        }

        self.logger.debug(f"Applied transform flattening to group {group_info['id']}")
        return group_info

    def _apply_nested_flattening(self, group_element: ET.Element,
                               group_info: Dict[str, Any]) -> Dict[str, Any]:
        """Apply nested group flattening."""
        flattened_children = []

        for child_info in group_info['children']:
            if child_info['is_group'] and not child_info['has_clipping']:
                # Flatten this nested group
                nested_children = self._extract_nested_children(child_info['element'])
                flattened_child_nodes.extend(nested_children)
                self.logger.debug(f"Flattened nested group with {len(nested_children)} children")
            else:
                flattened_child_nodes.append(child_info)

        group_info['children'] = flattened_children
        group_info['child_count'] = len(flattened_children)
        group_info['flattening_applied'] = True

        return group_info

    def _extract_nested_children(self, nested_group: ET.Element) -> List[Dict[str, Any]]:
        """Extract children from a nested group for flattening."""
        extracted = []

        for child in nested_group:
            child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

            if child_tag in ['title', 'desc', 'metadata']:
                continue

            # Apply nested group's transform to child if needed
            nested_transform = nested_group.get('transform')
            if nested_transform:
                child_transform = child.get('transform')
                if child_transform:
                    # Combine transforms
                    combined_transform = f"{nested_transform} {child_transform}"
                    child.set('transform', combined_transform)
                else:
                    child.set('transform', nested_transform)

            child_info = {
                'element': child,
                'tag': child_tag,
                'has_transform': child.get('transform') is not None,
                'has_clipping': child.get('clip-path') is not None,
                'is_group': child_tag == 'g',
                'is_clipping_mask': child.get('data-clip-role') == 'mask',
                'flattened_from_nested': True
            }

            extracted.append(child_info)

        return extracted

    def _process_group_clipping(self, group_element: ET.Element,
                              group_info: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Process group clipping with preprocessing integration."""
        clipping_info = group_info['clipping_info']

        if clipping_info.get('from_preprocessing'):
            # Use preprocessing metadata
            group_info['clipping_strategy'] = self._determine_preprocessing_clip_strategy(
                group_element, clipping_info
            )
        else:
            # Apply clipping preprocessor
            group_info['clipping_strategy'] = self._apply_clipping_preprocessor(
                group_element, clipping_info, context
            )

        return group_info

    def _determine_preprocessing_clip_strategy(self, group_element: ET.Element,
                                             clipping_info: Dict[str, Any]) -> Dict[str, Any]:
        """Determine clipping strategy from preprocessing metadata."""
        operation = clipping_info.get('operation', 'intersect')
        source = clipping_info.get('source', '')

        # Find clipping masks in children
        mask_elements = []
        content_elements = []

        for child in group_element:
            if child.get('data-clip-role') == 'mask':
                mask_elements.append(child)
            else:
                content_elements.append(child)

        strategy = {
            'type': 'preprocessing_resolved',
            'operation': operation,
            'source': source,
            'mask_elements': mask_elements,
            'content_elements': content_elements,
            'powerpoint_compatible': len(mask_elements) == 1 and operation == 'intersect'
        }

        self.logger.debug(f"Preprocessing clip strategy: {operation} with {len(mask_elements)} masks")
        return strategy

    def _apply_clipping_preprocessor(self, group_element: ET.Element,
                                   clipping_info: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Apply clipping preprocessor to resolve clip-path references."""
        # Create temporary SVG for preprocessing
        temp_svg = ET.Element('{http://www.w3.org/2000/svg}svg')
        temp_svg.append(group_element)

        # Apply clipping preprocessor
        try:
            processed_svg = self.clip_preprocessor.process(temp_svg)
            processed_group = processed_svg.find('.//{http://www.w3.org/2000/svg}g')

            if processed_group is not None:
                # Extract resolved clipping information
                return self._extract_resolved_clipping_info(processed_group)
            else:
                self.logger.warning("Clipping preprocessor failed to return group")
                return {'type': 'fallback', 'powerpoint_compatible': False}

        except Exception as e:
            self.logger.warning(f"Clipping preprocessing failed: {e}")
            return {'type': 'fallback', 'powerpoint_compatible': False}

    def _extract_resolved_clipping_info(self, processed_group: ET.Element) -> Dict[str, Any]:
        """Extract clipping information from preprocessed group."""
        operation = processed_group.get('data-clip-operation', 'unknown')
        source = processed_group.get('data-clip-source', '')

        mask_elements = []
        content_elements = []

        for child in processed_group:
            if child.get('data-clip-role') == 'mask':
                mask_elements.append(child)
            else:
                content_elements.append(child)

        return {
            'type': 'resolved',
            'operation': operation,
            'source': source,
            'mask_elements': mask_elements,
            'content_elements': content_elements,
            'powerpoint_compatible': len(mask_elements) <= 2 and operation in ['intersect', 'union']
        }

    def _process_nested_groups(self, group_element: ET.Element,
                             group_info: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Process nested groups recursively."""
        processed_children = []

        for child_info in group_info['children']:
            if child_info['is_group']:
                # Recursively process nested group
                nested_info = self.process_group_element(
                    child_info['element'], context, apply_optimizations=True
                )
                child_info['nested_group_info'] = nested_info

            processed_child_nodes.append(child_info)

        group_info['children'] = processed_children
        return group_info

    def generate_drawingml_structure(self, group_info: Dict[str, Any], context: Any) -> str:
        """Generate DrawingML structure from processed group information."""
        # Check if group should be unwrapped
        if group_info.get('should_unwrap', False):
            return self._generate_unwrapped_content(group_info, context)

        # Check clipping strategy
        if group_info.get('clipping_strategy'):
            return self._generate_clipped_group_drawingml(group_info, context)

        # Standard group conversion
        return self._generate_standard_group_drawingml(group_info, context)

    def _generate_unwrapped_content(self, group_info: Dict[str, Any], context: Any) -> str:
        """Generate DrawingML for unwrapped group (single child)."""
        child_info = group_info['children'][0]
        element = child_info['element']

        # Convert child element directly using appropriate converter
        converter = self._get_element_converter(element, context)
        if converter:
            return converter.convert(element, context)

        return ""

    def _generate_clipped_group_drawingml(self, group_info: Dict[str, Any], context: Any) -> str:
        """Generate DrawingML for group with clipping."""
        clipping_strategy = group_info['clipping_strategy']

        if clipping_strategy.get('powerpoint_compatible', False):
            return self._generate_powerpoint_clipped_group(group_info, context)
        else:
            return self._generate_emf_clipped_group(group_info, context)

    def _generate_standard_group_drawingml(self, group_info: Dict[str, Any], context: Any) -> str:
        """Generate standard DrawingML group."""
        group_id = group_info['id']
        children_xml = []

        # Process all children
        for child_info in group_info['children']:
            if child_info.get('is_clipping_mask', False):
                continue  # Skip clipping masks in standard groups

            element = child_info['element']
            converter = self._get_element_converter(element, context)
            if converter:
                child_xml = converter.convert(element, context)
                if child_xml.strip():
                    children_xml.append(child_xml)

        if not children_xml:
            return ""

        # Generate group XML
        shape_id = context.get_next_shape_id() if hasattr(context, 'get_next_shape_id') else 1
        children_content = '\n    '.join(children_xml)

        # Apply transform if needed
        transform_xml = ""
        if group_info.get('transform'):
            transform_xml = self._generate_transform_xml(group_info['transform'], context)

        return f'''<a:grpSp>
    <a:nvGrpSpPr>
        <a:cNvPr id="{shape_id}" name="{group_id}"/>
        <a:cNvGrpSpPr/>
    </a:nvGrpSpPr>
    <a:grpSpPr>
        {transform_xml}
    </a:grpSpPr>
    {children_content}
</a:grpSp>'''

    def _generate_powerpoint_clipped_group(self, group_info: Dict[str, Any], context: Any) -> str:
        """Generate PowerPoint-compatible clipped group."""
        clipping_strategy = group_info['clipping_strategy']
        mask_elements = clipping_strategy.get('mask_elements', [])
        content_elements = clipping_strategy.get('content_elements', [])

        # Generate content
        content_xml = []
        for element in content_elements:
            converter = self._get_element_converter(element, context)
            if converter:
                xml = converter.convert(element, context)
                if xml.strip():
                    content_xml.append(xml)

        if not content_xml:
            return ""

        # For PowerPoint clipping, we typically use shape intersection
        shape_id = context.get_next_shape_id() if hasattr(context, 'get_next_shape_id') else 1
        content = '\n    '.join(content_xml)

        return f'''<!-- PowerPoint Compatible Clipped Group -->
<a:grpSp>
    <a:nvGrpSpPr>
        <a:cNvPr id="{shape_id}" name="ClippedGroup"/>
        <a:cNvGrpSpPr/>
    </a:nvGrpSpPr>
    <a:grpSpPr>
        <!-- Clipping: {clipping_strategy['operation']} with {len(mask_elements)} masks -->
    </a:grpSpPr>
    {content}
</a:grpSp>'''

    def _generate_emf_clipped_group(self, group_info: Dict[str, Any], context: Any) -> str:
        """Generate EMF-based clipped group for complex clipping."""
        clipping_strategy = group_info['clipping_strategy']

        shape_id = context.get_next_shape_id() if hasattr(context, 'get_next_shape_id') else 1

        return f'''<!-- EMF Clipped Group -->
<!-- Strategy: {clipping_strategy.get('type', 'unknown')} -->
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="EMFClippedGroup"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <!-- EMF clipping implementation would go here -->
    </p:spPr>
</p:sp>'''

    def _generate_transform_xml(self, transform: str, context: Any) -> str:
        """Generate transform XML for DrawingML."""
        # Basic transform XML generation
        # In a full implementation, this would parse the transform and generate proper DrawingML
        return f'''<a:xfrm>
    <!-- Transform: {transform} -->
    <a:off x="0" y="0"/>
    <a:ext cx="914400" cy="914400"/>
</a:xfrm>'''

    def _get_element_converter(self, element: ET.Element, context: Any):
        """Get appropriate converter for element."""
        if hasattr(context, 'converter_registry'):
            return context.converter_registry.get_converter(element)
        return None

    def get_processing_statistics(self) -> Dict[str, int]:
        """Get group processing statistics."""
        return self.stats.copy()

    def reset_statistics(self) -> None:
        """Reset processing statistics."""
        self.stats = {
            'groups_processed': 0,
            'groups_flattened': 0,
            'groups_with_clipping': 0,
            'nested_groups_resolved': 0
        }


def create_group_processor(services: ConversionServices) -> GroupProcessor:
    """
    Create a group processor with services.

    Args:
        services: ConversionServices container

    Returns:
        Configured GroupProcessor
    """
    return GroupProcessor(services)