#!/usr/bin/env python3
"""
Clipping Analyzer

Enhanced clipping analysis that integrates with the preprocessing pipeline
to provide optimized clipping conversion strategies.

Features:
- Preprocessing-aware clipping analysis
- PowerPoint compatibility assessment
- EMF fallback strategy
- Performance optimization for complex clipping
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from lxml import etree as ET
from enum import Enum
from dataclasses import dataclass

from ..services.conversion_services import ConversionServices

logger = logging.getLogger(__name__)


class ClippingComplexity(Enum):
    """Clipping complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    UNSUPPORTED = "unsupported"


class ClippingStrategy(Enum):
    """Clipping conversion strategies."""
    POWERPOINT_NATIVE = "powerpoint_native"
    CUSTGEOM = "custgeom"
    EMF_VECTOR = "emf_vector"
    RASTERIZATION = "rasterization"


@dataclass
class ClippingPath:
    """Information about a clipping path."""
    id: str
    path_data: Optional[str]
    shapes: List[ET.Element]
    units: str
    transform: Optional[str]
    complexity: ClippingComplexity
    powerpoint_compatible: bool


@dataclass
class ClippingAnalysis:
    """Result of clipping analysis."""
    target_element: ET.Element
    clipping_paths: List[ClippingPath]
    complexity: ClippingComplexity
    recommended_strategy: ClippingStrategy
    powerpoint_compatible: bool
    requires_preprocessing: bool
    optimization_opportunities: List[str]
    fallback_strategy: ClippingStrategy
    estimated_performance_impact: str


class ClippingAnalyzer:
    """
    Analyzes SVG clipping scenarios and recommends conversion strategies.

    Integrates with the preprocessing pipeline to provide optimized
    clipping conversion with PowerPoint compatibility assessment.
    """

    def __init__(self, services: ConversionServices):
        """
        Initialize clipping analyzer.

        Args:
            services: ConversionServices container
        """
        self.services = services
        self.logger = logging.getLogger(__name__)

        # Analysis cache
        self.analysis_cache: Dict[str, ClippingAnalysis] = {}

        # Statistics
        self.stats = {
            'analyses_performed': 0,
            'simple_clips': 0,
            'complex_clips': 0,
            'unsupported_clips': 0,
            'cache_hits': 0
        }

    def analyze_clipping_scenario(self, element: ET.Element, context: Any) -> ClippingAnalysis:
        """
        Analyze a clipping scenario and recommend conversion strategy.

        Args:
            element: Element with clipping applied
            context: Conversion context

        Returns:
            Clipping analysis with recommendations
        """
        # Generate cache key
        cache_key = self._generate_cache_key(element)

        # Check cache
        if cache_key in self.analysis_cache:
            self.stats['cache_hits'] += 1
            return self.analysis_cache[cache_key]

        self.stats['analyses_performed'] += 1

        # Perform analysis
        analysis = self._perform_clipping_analysis(element, context)

        # Cache result
        self.analysis_cache[cache_key] = analysis

        # Update statistics
        if analysis.complexity == ClippingComplexity.SIMPLE:
            self.stats['simple_clips'] += 1
        elif analysis.complexity in [ClippingComplexity.MODERATE, ClippingComplexity.COMPLEX]:
            self.stats['complex_clips'] += 1
        else:
            self.stats['unsupported_clips'] += 1

        return analysis

    def _perform_clipping_analysis(self, element: ET.Element, context: Any) -> ClippingAnalysis:
        """Perform detailed clipping analysis."""
        # Check for clipping references
        clipping_paths = self._extract_clipping_paths(element, context)

        if not clipping_paths:
            return self._create_no_clipping_analysis(element)

        # Analyze complexity
        overall_complexity = self._assess_overall_complexity(clipping_paths)

        # Check preprocessing status
        requires_preprocessing = self._requires_preprocessing(element, clipping_paths)

        # Determine recommended strategy
        recommended_strategy = self._determine_strategy(clipping_paths, overall_complexity)

        # Check PowerPoint compatibility
        powerpoint_compatible = self._assess_powerpoint_compatibility(clipping_paths, overall_complexity)

        # Identify optimization opportunities
        optimizations = self._identify_optimizations(clipping_paths, overall_complexity)

        # Determine fallback strategy
        fallback_strategy = self._determine_fallback_strategy(recommended_strategy, overall_complexity)

        # Estimate performance impact
        performance_impact = self._estimate_performance_impact(clipping_paths, overall_complexity)

        return ClippingAnalysis(
            target_element=element,
            clipping_paths=clipping_paths,
            complexity=overall_complexity,
            recommended_strategy=recommended_strategy,
            powerpoint_compatible=powerpoint_compatible,
            requires_preprocessing=requires_preprocessing,
            optimization_opportunities=optimizations,
            fallback_strategy=fallback_strategy,
            estimated_performance_impact=performance_impact
        )

    def _extract_clipping_paths(self, element: ET.Element, context: Any) -> List[ClippingPath]:
        """Extract clipping path information from element."""
        clipping_paths = []

        # Check for direct clip-path attribute
        clip_path_ref = element.get('clip-path')
        if clip_path_ref:
            clip_path = self._resolve_clip_path_reference(clip_path_ref, context)
            if clip_path:
                clipping_paths.append(clip_path)

        # Check for preprocessing metadata
        if element.get('data-clip-operation'):
            preprocessing_clips = self._extract_preprocessing_clips(element)
            clipping_paths.extend(preprocessing_clips)

        return clipping_paths

    def _resolve_clip_path_reference(self, clip_ref: str, context: Any) -> Optional[ClippingPath]:
        """Resolve clip-path reference to ClippingPath object."""
        # Extract clip path ID
        clip_id = self._extract_reference_id(clip_ref)
        if not clip_id:
            return None

        # Find clipPath definition in SVG
        svg_root = getattr(context, 'svg_root', None)
        if not svg_root:
            return None

        clippath_element = svg_root.xpath(f".//*[@id='{clip_id}']")
        if not clippath_element:
            self.logger.warning(f"ClipPath definition not found: {clip_id}")
            return None

        clippath_def = clippath_element[0]
        return self._analyze_clippath_definition(clippath_def)

    def _extract_preprocessing_clips(self, element: ET.Element) -> List[ClippingPath]:
        """Extract clipping paths from preprocessing metadata."""
        clips = []

        # Find clipping mask elements
        mask_elements = element.xpath(".//*[@data-clip-role='mask']")

        for mask_element in mask_elements:
            clip_path = self._analyze_mask_element(mask_element)
            if clip_path:
                clips.append(clip_path)

        return clips

    def _analyze_clippath_definition(self, clippath_element: ET.Element) -> ClippingPath:
        """Analyze a clipPath definition element."""
        clip_id = clippath_element.get('id', 'unknown')
        units = clippath_element.get('clipPathUnits', 'userSpaceOnUse')
        transform = clippath_element.get('transform')

        # Extract shapes
        shapes = list(clippath_element)
        path_data = None

        # Check for single path
        if len(shapes) == 1 and shapes[0].tag.endswith('path'):
            path_data = shapes[0].get('d')

        # Analyze complexity
        complexity = self._analyze_clippath_complexity(shapes, path_data)

        # Check PowerPoint compatibility
        powerpoint_compatible = self._is_powerpoint_compatible(shapes, complexity)

        return ClippingPath(
            id=clip_id,
            path_data=path_data,
            shapes=shapes,
            units=units,
            transform=transform,
            complexity=complexity,
            powerpoint_compatible=powerpoint_compatible
        )

    def _analyze_mask_element(self, mask_element: ET.Element) -> Optional[ClippingPath]:
        """Analyze a clipping mask element from preprocessing."""
        mask_id = mask_element.get('id', f'mask_{id(mask_element)}')
        transform = mask_element.get('transform')

        # Extract path data or shape information
        tag = mask_element.tag.split('}')[-1] if '}' in mask_element.tag else mask_element.tag

        if tag == 'path':
            path_data = mask_element.get('d')
            shapes = [mask_element]
        else:
            path_data = None
            shapes = [mask_element]

        # Analyze complexity
        complexity = self._analyze_clippath_complexity(shapes, path_data)

        return ClippingPath(
            id=mask_id,
            path_data=path_data,
            shapes=shapes,
            units='userSpaceOnUse',  # Default for preprocessing
            transform=transform,
            complexity=complexity,
            powerpoint_compatible=self._is_powerpoint_compatible(shapes, complexity)
        )

    def _analyze_clippath_complexity(self, shapes: List[ET.Element], path_data: Optional[str]) -> ClippingComplexity:
        """Analyze the complexity of a clipping path."""
        if not shapes:
            return ClippingComplexity.UNSUPPORTED

        # Single simple shape
        if len(shapes) == 1:
            shape = shapes[0]
            tag = shape.tag.split('}')[-1] if '}' in shape.tag else shape.tag

            if tag in ['rect', 'circle', 'ellipse']:
                return ClippingComplexity.SIMPLE

            if tag == 'path' and path_data:
                return self._analyze_path_complexity(path_data)

        # Multiple shapes
        if len(shapes) <= 3:
            # Check if all shapes are simple
            all_simple = all(
                shape.tag.split('}')[-1] in ['rect', 'circle', 'ellipse', 'path']
                for shape in shapes
            )
            if all_simple:
                return ClippingComplexity.MODERATE

        # Complex scenarios
        if len(shapes) > 5:
            return ClippingComplexity.COMPLEX

        # Check for unsupported elements
        for shape in shapes:
            tag = shape.tag.split('}')[-1] if '}' in shape.tag else shape.tag
            if tag in ['text', 'tspan', 'image', 'use']:
                return ClippingComplexity.UNSUPPORTED
            if shape.get('filter'):
                return ClippingComplexity.COMPLEX

        return ClippingComplexity.MODERATE

    def _analyze_path_complexity(self, path_data: str) -> ClippingComplexity:
        """Analyze the complexity of a path string."""
        if not path_data:
            return ClippingComplexity.UNSUPPORTED

        # Count path commands
        import re
        commands = re.findall(r'[MmLlHhVvCcSsQqTtAaZz]', path_data)
        command_count = len(commands)

        # Simple path
        if command_count <= 5:
            return ClippingComplexity.SIMPLE

        # Moderate complexity
        if command_count <= 20:
            return ClippingComplexity.MODERATE

        # Complex path
        return ClippingComplexity.COMPLEX

    def _assess_overall_complexity(self, clipping_paths: List[ClippingPath]) -> ClippingComplexity:
        """Assess overall complexity from multiple clipping paths."""
        if not clipping_paths:
            return ClippingComplexity.SIMPLE

        # Single clipping path
        if len(clipping_paths) == 1:
            return clipping_paths[0].complexity

        # Multiple clipping paths - increase complexity
        max_complexity = max(clip.complexity for clip in clipping_paths)

        if max_complexity == ClippingComplexity.SIMPLE:
            return ClippingComplexity.MODERATE
        elif max_complexity == ClippingComplexity.MODERATE:
            return ClippingComplexity.COMPLEX
        else:
            return max_complexity

    def _is_powerpoint_compatible(self, shapes: List[ET.Element], complexity: ClippingComplexity) -> bool:
        """Check if clipping is PowerPoint compatible."""
        # PowerPoint has limited clipping support
        if complexity in [ClippingComplexity.COMPLEX, ClippingComplexity.UNSUPPORTED]:
            return False

        # Single simple shape is usually compatible
        if len(shapes) == 1 and complexity == ClippingComplexity.SIMPLE:
            shape = shapes[0]
            tag = shape.tag.split('}')[-1] if '}' in shape.tag else shape.tag
            return tag in ['rect', 'circle', 'ellipse', 'path']

        # Multiple shapes are generally not compatible
        return len(shapes) <= 2 and complexity == ClippingComplexity.SIMPLE

    def _determine_strategy(self, clipping_paths: List[ClippingPath], complexity: ClippingComplexity) -> ClippingStrategy:
        """Determine the recommended conversion strategy."""
        if complexity == ClippingComplexity.UNSUPPORTED:
            return ClippingStrategy.RASTERIZATION

        # Check PowerPoint compatibility
        powerpoint_compatible = all(clip.powerpoint_compatible for clip in clipping_paths)

        if powerpoint_compatible and complexity == ClippingComplexity.SIMPLE:
            return ClippingStrategy.POWERPOINT_NATIVE

        if complexity in [ClippingComplexity.SIMPLE, ClippingComplexity.MODERATE]:
            return ClippingStrategy.CUSTGEOM

        if complexity == ClippingComplexity.COMPLEX:
            return ClippingStrategy.EMF_VECTOR

        return ClippingStrategy.RASTERIZATION

    def _assess_powerpoint_compatibility(self, clipping_paths: List[ClippingPath], complexity: ClippingComplexity) -> bool:
        """Assess overall PowerPoint compatibility."""
        if complexity in [ClippingComplexity.COMPLEX, ClippingComplexity.UNSUPPORTED]:
            return False

        return all(clip.powerpoint_compatible for clip in clipping_paths)

    def _requires_preprocessing(self, element: ET.Element, clipping_paths: List[ClippingPath]) -> bool:
        """Check if preprocessing is required."""
        # Already has preprocessing metadata
        if element.get('data-clip-operation'):
            return False

        # Multiple clipping paths need preprocessing
        if len(clipping_paths) > 1:
            return True

        # Complex clipping might benefit from preprocessing
        for clip in clipping_paths:
            if clip.complexity in [ClippingComplexity.MODERATE, ClippingComplexity.COMPLEX]:
                return True

        return False

    def _identify_optimizations(self, clipping_paths: List[ClippingPath], complexity: ClippingComplexity) -> List[str]:
        """Identify optimization opportunities."""
        optimizations = []

        # Path simplification
        for clip in clipping_paths:
            if clip.path_data and len(clip.path_data) > 200:
                optimizations.append('path_simplification')

        # Shape merging
        if len(clipping_paths) > 1:
            optimizations.append('shape_merging')

        # Transform flattening
        for clip in clipping_paths:
            if clip.transform:
                optimizations.append('transform_flattening')

        # Preprocessing benefits
        if complexity in [ClippingComplexity.MODERATE, ClippingComplexity.COMPLEX]:
            optimizations.append('preprocessing_resolution')

        return optimizations

    def _determine_fallback_strategy(self, primary_strategy: ClippingStrategy, complexity: ClippingComplexity) -> ClippingStrategy:
        """Determine fallback strategy if primary fails."""
        if primary_strategy == ClippingStrategy.POWERPOINT_NATIVE:
            return ClippingStrategy.CUSTGEOM

        if primary_strategy == ClippingStrategy.CUSTGEOM:
            return ClippingStrategy.EMF_VECTOR

        if primary_strategy == ClippingStrategy.EMF_VECTOR:
            return ClippingStrategy.RASTERIZATION

        return ClippingStrategy.RASTERIZATION

    def _estimate_performance_impact(self, clipping_paths: List[ClippingPath], complexity: ClippingComplexity) -> str:
        """Estimate performance impact of clipping conversion."""
        clip_count = len(clipping_paths)

        if complexity == ClippingComplexity.SIMPLE and clip_count == 1:
            return 'low'

        if complexity == ClippingComplexity.MODERATE or clip_count <= 3:
            return 'medium'

        if complexity == ClippingComplexity.COMPLEX or clip_count > 5:
            return 'high'

        return 'very_high'

    def _create_no_clipping_analysis(self, element: ET.Element) -> ClippingAnalysis:
        """Create analysis for element without clipping."""
        return ClippingAnalysis(
            target_element=element,
            clipping_paths=[],
            complexity=ClippingComplexity.SIMPLE,
            recommended_strategy=ClippingStrategy.POWERPOINT_NATIVE,
            powerpoint_compatible=True,
            requires_preprocessing=False,
            optimization_opportunities=[],
            fallback_strategy=ClippingStrategy.POWERPOINT_NATIVE,
            estimated_performance_impact='none'
        )

    def _extract_reference_id(self, reference: str) -> Optional[str]:
        """Extract ID from URL reference."""
        if reference.startswith('url(#') and reference.endswith(')'):
            return reference[5:-1]
        elif reference.startswith('#'):
            return reference[1:]
        return None

    def _generate_cache_key(self, element: ET.Element) -> str:
        """Generate cache key for element."""
        # Use element attributes and children count as key
        attrs = sorted(element.attrib.items())
        children_count = len(list(element))
        return f"{element.tag}:{attrs}:{children_count}"

    def get_analysis_statistics(self) -> Dict[str, int]:
        """Get analysis statistics."""
        return self.stats.copy()

    def clear_cache(self) -> None:
        """Clear analysis cache."""
        self.analysis_cache.clear()

    def reset_statistics(self) -> None:
        """Reset analysis statistics."""
        self.stats = {
            'analyses_performed': 0,
            'simple_clips': 0,
            'complex_clips': 0,
            'unsupported_clips': 0,
            'cache_hits': 0
        }


def create_clipping_analyzer(services: ConversionServices) -> ClippingAnalyzer:
    """
    Create a clipping analyzer with services.

    Args:
        services: ConversionServices container

    Returns:
        Configured ClippingAnalyzer
    """
    return ClippingAnalyzer(services)