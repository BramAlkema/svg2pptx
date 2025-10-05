#!/usr/bin/env python3
"""
Group Converter Service

High-level service that orchestrates group processing, clipping analysis,
and DrawingML generation with preprocessing integration.

Features:
- Group processing orchestration
- Clipping analysis integration
- Performance optimization
- PowerPoint compatibility assessment
"""

import logging
from typing import Dict, Optional, Any, TYPE_CHECKING
from lxml import etree as ET

from .group_processor import GroupProcessor
from .clipping_analyzer import ClippingAnalyzer, ClippingStrategy
from ..services.conversion_services import ConversionServices

if TYPE_CHECKING:
    from ..policy.engine import PolicyEngine

logger = logging.getLogger(__name__)


class GroupConverterService:
    """
    Service that orchestrates group and clipping conversion.

    Coordinates between group processing, clipping analysis, and DrawingML
    generation to provide comprehensive group conversion capabilities.
    """

    def __init__(self, services: ConversionServices, policy_engine: Optional['PolicyEngine'] = None):
        """
        Initialize group converter service.

        Args:
            services: ConversionServices container
            policy_engine: Optional policy engine for complexity decisions
        """
        self.services = services
        self._policy_engine = policy_engine
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.group_processor = GroupProcessor(services)
        self.clipping_analyzer = ClippingAnalyzer(services, policy_engine=policy_engine)

        # Conversion statistics
        self.stats = {
            'groups_converted': 0,
            'clipped_elements_converted': 0,
            'powerpoint_compatible': 0,
            'emf_fallbacks': 0,
            'rasterization_fallbacks': 0,
            'optimizations_applied': 0
        }

    def convert_group_element(self, element: ET.Element, context: Any,
                            enable_optimizations: bool = True) -> str:
        """
        Convert group element with comprehensive processing.

        Args:
            element: SVG group element
            context: Conversion context
            enable_optimizations: Whether to enable optimizations

        Returns:
            DrawingML XML string
        """
        try:
            self.stats['groups_converted'] += 1

            # Process group structure
            group_info = self.group_processor.process_group_element(
                element, context, apply_optimizations=enable_optimizations
            )

            # Apply clipping analysis if needed
            if group_info.get('has_clipping', False):
                group_info = self._enhance_with_clipping_analysis(element, group_info, context)

            # Generate DrawingML
            drawingml = self.group_processor.generate_drawingml_structure(group_info, context)

            # Update statistics
            self._update_conversion_statistics(group_info)

            self.logger.debug(f"Converted group '{group_info['id']}' successfully")
            return drawingml

        except Exception as e:
            self.logger.error(f"Group conversion failed: {e}")
            return self._generate_fallback_group(element, context)

    def convert_clipped_element(self, element: ET.Element, context: Any) -> str:
        """
        Convert element with clipping applied.

        Args:
            element: Element with clipping
            context: Conversion context

        Returns:
            DrawingML XML string
        """
        try:
            self.stats['clipped_elements_converted'] += 1

            # Analyze clipping scenario
            clipping_analysis = self.clipping_analyzer.analyze_clipping_scenario(element, context)

            # Generate appropriate conversion based on analysis
            if clipping_analysis.powerpoint_compatible:
                return self._convert_powerpoint_compatible_clipping(element, clipping_analysis, context)
            elif clipping_analysis.recommended_strategy == ClippingStrategy.EMF_VECTOR:
                return self._convert_emf_clipping(element, clipping_analysis, context)
            else:
                return self._convert_fallback_clipping(element, clipping_analysis, context)

        except Exception as e:
            self.logger.error(f"Clipped element conversion failed: {e}")
            return self._generate_fallback_clipped_element(element, context)

    def _enhance_with_clipping_analysis(self, element: ET.Element, group_info: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Enhance group info with clipping analysis."""
        clipping_analysis = self.clipping_analyzer.analyze_clipping_scenario(element, context)

        # Integrate clipping analysis with group info
        group_info['clipping_analysis'] = clipping_analysis
        group_info['clipping_strategy'] = clipping_analysis.recommended_strategy
        group_info['clipping_complexity'] = clipping_analysis.complexity
        group_info['powerpoint_compatible'] = clipping_analysis.powerpoint_compatible

        # Apply optimizations based on analysis
        if clipping_analysis.optimization_opportunities:
            group_info = self._apply_clipping_optimizations(group_info, clipping_analysis)

        return group_info

    def _apply_clipping_optimizations(self, group_info: Dict[str, Any], analysis) -> Dict[str, Any]:
        """Apply clipping-specific optimizations."""
        optimizations = analysis.optimization_opportunities

        if 'preprocessing_resolution' in optimizations:
            group_info['needs_clip_preprocessing'] = True

        if 'shape_merging' in optimizations:
            group_info['can_merge_clip_shapes'] = True

        if 'transform_flattening' in optimizations:
            group_info['can_flatten_clip_transforms'] = True

        if 'path_simplification' in optimizations:
            group_info['can_simplify_clip_paths'] = True

        self.stats['optimizations_applied'] += len(optimizations)
        return group_info

    def _convert_powerpoint_compatible_clipping(self, element: ET.Element, analysis, context: Any) -> str:
        """Convert PowerPoint-compatible clipping."""
        self.stats['powerpoint_compatible'] += 1

        clipping_paths = analysis.clipping_paths
        if not clipping_paths:
            return ""

        # Use first clipping path for PowerPoint conversion
        primary_clip = clipping_paths[0]

        # Generate PowerPoint-compatible clipping shape
        shape_id = context.get_next_shape_id() if hasattr(context, 'get_next_shape_id') else 1

        if primary_clip.path_data:
            # Path-based clipping
            return self._generate_powerpoint_path_clip(element, primary_clip, shape_id, context)
        elif primary_clip.shapes:
            # Shape-based clipping
            return self._generate_powerpoint_shape_clip(element, primary_clip, shape_id, context)

        return ""

    def _generate_powerpoint_path_clip(self, element: ET.Element, clip_path, shape_id: int, context: Any) -> str:
        """Generate PowerPoint path-based clipping."""
        path_data = clip_path.path_data

        # Convert SVG path to PowerPoint custGeom
        custgeom_xml = self._convert_path_to_custgeom(path_data)

        return f'''<!-- PowerPoint Path Clipping -->
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="PathClippedShape"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:xfrm>
            <a:off x="0" y="0"/>
            <a:ext cx="914400" cy="914400"/>
        </a:xfrm>
        {custgeom_xml}
        <a:solidFill>
            <a:srgbClr val="FF0000"/>
        </a:solidFill>
    </p:spPr>
</p:sp>'''

    def _generate_powerpoint_shape_clip(self, element: ET.Element, clip_path, shape_id: int, context: Any) -> str:
        """Generate PowerPoint shape-based clipping."""
        if not clip_path.shapes:
            return ""

        shape = clip_path.shapes[0]
        tag = shape.tag.split('}')[-1] if '}' in shape.tag else shape.tag

        if tag == 'rect':
            return self._generate_rect_clip(element, shape, shape_id)
        elif tag == 'circle':
            return self._generate_circle_clip(element, shape, shape_id)
        elif tag == 'ellipse':
            return self._generate_ellipse_clip(element, shape, shape_id)

        return ""

    def _generate_rect_clip(self, element: ET.Element, rect: ET.Element, shape_id: int) -> str:
        """Generate rectangle clipping shape."""
        x = float(rect.get('x', '0'))
        y = float(rect.get('y', '0'))
        width = float(rect.get('width', '100'))
        height = float(rect.get('height', '100'))

        # Convert to EMU
        x_emu = int(x * 9525)
        y_emu = int(y * 9525)
        width_emu = int(width * 9525)
        height_emu = int(height * 9525)

        return f'''<!-- Rectangle Clipping -->
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="RectClip"/>
        <p:cNvSpPr/>
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
    </p:spPr>
</p:sp>'''

    def _generate_circle_clip(self, element: ET.Element, circle: ET.Element, shape_id: int) -> str:
        """Generate circle clipping shape."""
        cx = float(circle.get('cx', '0'))
        cy = float(circle.get('cy', '0'))
        r = float(circle.get('r', '50'))

        # Convert to EMU
        x_emu = int((cx - r) * 9525)
        y_emu = int((cy - r) * 9525)
        size_emu = int(2 * r * 9525)

        return f'''<!-- Circle Clipping -->
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="CircleClip"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:xfrm>
            <a:off x="{x_emu}" y="{y_emu}"/>
            <a:ext cx="{size_emu}" cy="{size_emu}"/>
        </a:xfrm>
        <a:prstGeom prst="ellipse">
            <a:avLst/>
        </a:prstGeom>
    </p:spPr>
</p:sp>'''

    def _generate_ellipse_clip(self, element: ET.Element, ellipse: ET.Element, shape_id: int) -> str:
        """Generate ellipse clipping shape."""
        cx = float(ellipse.get('cx', '0'))
        cy = float(ellipse.get('cy', '0'))
        rx = float(ellipse.get('rx', '50'))
        ry = float(ellipse.get('ry', '25'))

        # Convert to EMU
        x_emu = int((cx - rx) * 9525)
        y_emu = int((cy - ry) * 9525)
        width_emu = int(2 * rx * 9525)
        height_emu = int(2 * ry * 9525)

        return f'''<!-- Ellipse Clipping -->
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="EllipseClip"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:xfrm>
            <a:off x="{x_emu}" y="{y_emu}"/>
            <a:ext cx="{width_emu}" cy="{height_emu}"/>
        </a:xfrm>
        <a:prstGeom prst="ellipse">
            <a:avLst/>
        </a:prstGeom>
    </p:spPr>
</p:sp>'''

    def _convert_emf_clipping(self, element: ET.Element, analysis, context: Any) -> str:
        """Convert complex clipping using EMF."""
        self.stats['emf_fallbacks'] += 1

        shape_id = context.get_next_shape_id() if hasattr(context, 'get_next_shape_id') else 1

        return f'''<!-- EMF Vector Clipping -->
<!-- Complexity: {analysis.complexity.value} -->
<!-- Strategy: {analysis.recommended_strategy.value} -->
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="EMFClippedElement"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <!-- EMF clipping would be implemented here -->
        <!-- Performance impact: {analysis.estimated_performance_impact} -->
    </p:spPr>
</p:sp>'''

    def _convert_fallback_clipping(self, element: ET.Element, analysis, context: Any) -> str:
        """Convert clipping using fallback strategy."""
        if analysis.fallback_strategy == ClippingStrategy.RASTERIZATION:
            self.stats['rasterization_fallbacks'] += 1

        shape_id = context.get_next_shape_id() if hasattr(context, 'get_next_shape_id') else 1

        return f'''<!-- Fallback Clipping -->
<!-- Primary strategy: {analysis.recommended_strategy.value} -->
<!-- Fallback strategy: {analysis.fallback_strategy.value} -->
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="FallbackClippedElement"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <!-- Fallback implementation would go here -->
    </p:spPr>
</p:sp>'''

    def _convert_path_to_custgeom(self, path_data: str) -> str:
        """Convert SVG path to PowerPoint custGeom."""
        if not path_data:
            return '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'

        # Basic custGeom structure for path
        return f'''<a:custGeom>
    <a:avLst/>
    <a:gdLst/>
    <a:ahLst/>
    <a:cxnLst/>
    <a:rect l="0" t="0" r="21600" b="21600"/>
    <a:pathLst>
        <a:path w="21600" h="21600">
            <!-- Path data: {path_data[:100]}... -->
            <!-- TODO: Convert SVG path to PowerPoint path commands -->
        </a:path>
    </a:pathLst>
</a:custGeom>'''

    def _generate_fallback_group(self, element: ET.Element, context: Any) -> str:
        """Generate fallback group when conversion fails."""
        shape_id = context.get_next_shape_id() if hasattr(context, 'get_next_shape_id') else 1
        group_id = element.get('id', f'fallback_group_{shape_id}')

        return f'''<!-- Fallback Group -->
<a:grpSp>
    <a:nvGrpSpPr>
        <a:cNvPr id="{shape_id}" name="{group_id}"/>
        <a:cNvGrpSpPr/>
    </a:nvGrpSpPr>
    <a:grpSpPr>
        <a:xfrm>
            <a:off x="0" y="0"/>
            <a:ext cx="914400" cy="914400"/>
        </a:xfrm>
    </a:grpSpPr>
    <!-- Group conversion failed - children would be processed individually -->
</a:grpSp>'''

    def _generate_fallback_clipped_element(self, element: ET.Element, context: Any) -> str:
        """Generate fallback for clipped element when conversion fails."""
        shape_id = context.get_next_shape_id() if hasattr(context, 'get_next_shape_id') else 1

        return f'''<!-- Fallback Clipped Element -->
<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="FallbackClippedElement"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <!-- Clipping conversion failed -->
    </p:spPr>
</p:sp>'''

    def _update_conversion_statistics(self, group_info: Dict[str, Any]) -> None:
        """Update conversion statistics based on group info."""
        if group_info.get('powerpoint_compatible', False):
            self.stats['powerpoint_compatible'] += 1

        optimizations = group_info.get('applied_optimizations', [])
        self.stats['optimizations_applied'] += len(optimizations)

    def validate_group_element(self, element: ET.Element) -> Dict[str, Any]:
        """
        Validate group element and provide recommendations.

        Args:
            element: SVG group element

        Returns:
            Validation report with recommendations
        """
        report = {
            'valid': True,
            'issues': [],
            'recommendations': [],
            'optimization_opportunities': [],
            'preprocessing_benefits': []
        }

        # Check for complex nesting
        nested_groups = element.xpath(".//svg:g", namespaces={'svg': 'http://www.w3.org/2000/svg'})
        if len(nested_groups) > 5:
            report['issues'].append(f"Deep nesting detected: {len(nested_groups)} nested groups")
            report['optimization_opportunities'].append("nested_group_flattening")

        # Check for clipping
        clip_path = element.get('clip-path')
        if clip_path:
            report['preprocessing_benefits'].append("clipping_resolution")

        # Check for transforms
        transform_elements = element.xpath(".//*[@transform]")
        if len(transform_elements) > 3:
            report['optimization_opportunities'].append("transform_flattening")

        # Check for preprocessing metadata
        if element.get('data-clip-operation'):
            report['preprocessing_benefits'].append("preprocessing_integration")

        # Overall recommendations
        if report['optimization_opportunities']:
            report['recommendations'].append("Apply group optimizations for better performance")

        if report['preprocessing_benefits']:
            report['recommendations'].append("Element will benefit from preprocessing pipeline")

        return report

    def get_conversion_statistics(self) -> Dict[str, int]:
        """Get conversion statistics."""
        return self.stats.copy()

    def get_combined_statistics(self) -> Dict[str, Any]:
        """Get combined statistics from all components."""
        return {
            'converter': self.stats.copy(),
            'group_processor': self.group_processor.get_processing_statistics(),
            'clipping_analyzer': self.clipping_analyzer.get_analysis_statistics()
        }

    def reset_statistics(self) -> None:
        """Reset all statistics."""
        self.stats = {
            'groups_converted': 0,
            'clipped_elements_converted': 0,
            'powerpoint_compatible': 0,
            'emf_fallbacks': 0,
            'rasterization_fallbacks': 0,
            'optimizations_applied': 0
        }
        self.group_processor.reset_statistics()
        self.clipping_analyzer.reset_statistics()


def create_group_converter_service(services: ConversionServices, policy_engine: Optional['PolicyEngine'] = None) -> GroupConverterService:
    """
    Create a group converter service with services.

    Args:
        services: ConversionServices container
        policy_engine: Optional policy engine for complexity decisions

    Returns:
        Configured GroupConverterService
    """
    return GroupConverterService(services, policy_engine=policy_engine)