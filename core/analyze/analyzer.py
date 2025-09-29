#!/usr/bin/env python3
"""
SVG Analyzer

Analyzes SVG structure and recommends conversion strategies.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from lxml import etree as ET

# Import safe iteration utilities
from ..xml.safe_iter import walk, children, is_element

# Import OutputFormat with fallback for testing
try:
    from ..pipeline.config import OutputFormat
except ImportError:
    # Fallback for testing or standalone usage
    from enum import Enum
    class OutputFormat(Enum):
        PPTX = "pptx"
        SLIDE_XML = "slide_xml"
        DEBUG_JSON = "debug_json"
from .complexity_calculator import ComplexityCalculator

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Result of SVG analysis"""
    # Core analysis data
    complexity_score: float
    element_count: int
    recommended_output_format: OutputFormat
    scene: Optional[Any] = None  # Will be IR Scene when available

    # Detailed metrics
    path_count: int = 0
    text_count: int = 0
    group_count: int = 0
    image_count: int = 0
    filter_count: int = 0
    gradient_count: int = 0

    # Feature flags
    has_transforms: bool = False
    has_clipping: bool = False
    has_patterns: bool = False
    has_animations: bool = False

    # Performance metrics
    processing_time_ms: float = 0.0
    estimated_conversion_time_ms: float = 0.0

    # Quality indicators
    text_complexity: float = 0.0
    path_complexity: float = 0.0
    group_nesting_depth: int = 0

    # Recommendations
    recommended_strategies: List[str] = None
    optimization_suggestions: List[str] = None

    def __post_init__(self):
        if self.recommended_strategies is None:
            self.recommended_strategies = []
        if self.optimization_suggestions is None:
            self.optimization_suggestions = []


class SVGAnalyzer:
    """
    Analyzes SVG structure and recommends conversion strategies.

    This analyzer evaluates SVG complexity, counts elements, and provides
    recommendations for the best conversion approach.
    """

    def __init__(self):
        """Initialize analyzer with default thresholds"""
        self.complexity_thresholds = {
            'simple': 0.3,
            'moderate': 0.6,
            'complex': 0.8
        }

        # Element complexity weights
        self.element_weights = {
            'path': 1.0,
            'text': 0.8,
            'tspan': 0.6,
            'g': 0.3,
            'rect': 0.2,
            'circle': 0.2,
            'ellipse': 0.3,
            'line': 0.1,
            'polygon': 0.4,
            'polyline': 0.4,
            'image': 0.5,
            'use': 0.7,
            'symbol': 0.6,
            'defs': 0.1,
            'clipPath': 0.5,
            'mask': 0.7,
            'filter': 1.2,
            'feGaussianBlur': 0.8,
            'feDropShadow': 0.6,
            'linearGradient': 0.4,
            'radialGradient': 0.5,
            'pattern': 0.8
        }

        self.complexity_calculator = ComplexityCalculator()
        self.logger = logging.getLogger(__name__)

    def analyze(self, svg_root: ET.Element) -> AnalysisResult:
        """
        Analyze SVG structure and recommend conversion strategy.

        Args:
            svg_root: Root SVG element

        Returns:
            AnalysisResult with complexity score and recommendations
        """
        start_time = time.perf_counter()

        try:
            # Basic element counting
            elements = list(walk(svg_root))
            element_count = len(elements) - 1  # Exclude root SVG element

            # Count specific element types
            element_counts = self._count_elements_by_type(svg_root)

            # Calculate complexity score
            complexity_score = self._calculate_complexity_score(svg_root, element_counts)

            # Analyze features
            features = self._analyze_features(svg_root)

            # Calculate detailed complexity metrics
            text_complexity = self._calculate_text_complexity(svg_root)
            path_complexity = self._calculate_path_complexity(svg_root)
            group_nesting_depth = self._calculate_group_nesting_depth(svg_root)

            # Determine recommended output format
            recommended_format = self._recommend_output_format(complexity_score, features)

            # Generate recommendations
            strategies = self._generate_strategies(complexity_score, features, element_counts)
            optimizations = self._generate_optimization_suggestions(svg_root, features)

            # Calculate processing time
            processing_time = (time.perf_counter() - start_time) * 1000

            # Estimate conversion time
            estimated_conversion_time = self._estimate_conversion_time(complexity_score, element_count)

            # Create IR scene and enhance analysis with IR data
            scene = self._create_ir_scene_placeholder(svg_root, element_counts)

            # If we have IR data, use it to enhance complexity analysis
            if scene and len(scene) > 0:
                ir_complexity_adjustment = self._calculate_ir_complexity_adjustment(scene)
                complexity_score = min(complexity_score * ir_complexity_adjustment, 1.0)

            result = AnalysisResult(
                complexity_score=complexity_score,
                element_count=element_count,
                recommended_output_format=recommended_format,
                scene=scene,
                path_count=element_counts.get('path', 0),
                text_count=element_counts.get('text', 0) + element_counts.get('tspan', 0),
                group_count=element_counts.get('g', 0),
                image_count=element_counts.get('image', 0),
                filter_count=element_counts.get('filter', 0),
                gradient_count=element_counts.get('linearGradient', 0) + element_counts.get('radialGradient', 0),
                has_transforms=features['has_transforms'],
                has_clipping=features['has_clipping'],
                has_patterns=features['has_patterns'],
                has_animations=features['has_animations'],
                processing_time_ms=processing_time,
                estimated_conversion_time_ms=estimated_conversion_time,
                text_complexity=text_complexity,
                path_complexity=path_complexity,
                group_nesting_depth=group_nesting_depth,
                recommended_strategies=strategies,
                optimization_suggestions=optimizations
            )

            self.logger.debug(f"SVG analysis completed in {processing_time:.2f}ms, "
                            f"complexity: {complexity_score:.3f}, elements: {element_count}")

            return result

        except Exception as e:
            self.logger.error(f"SVG analysis failed: {e}")
            # Return minimal fallback result with empty scene (never None)
            processing_time = (time.perf_counter() - start_time) * 1000
            return AnalysisResult(
                complexity_score=1.0,  # Assume complex on error
                element_count=0,
                recommended_output_format=OutputFormat.PPTX,
                scene=[],  # Empty list, not None - this is iterable
                processing_time_ms=processing_time,
                recommended_strategies=['fallback_to_existing_system'],
                optimization_suggestions=['review_svg_structure']
            )

    def _count_elements_by_type(self, svg_root: ET.Element) -> Dict[str, int]:
        """Count elements by type"""
        counts = {}

        for element in walk(svg_root):
            tag = self._get_local_tag(element.tag)
            if tag != 'svg':  # Skip root
                counts[tag] = counts.get(tag, 0) + 1

        return counts

    def _calculate_complexity_score(self, svg_root: ET.Element, element_counts: Dict[str, int]) -> float:
        """Calculate overall complexity score (0.0 to 1.0)"""
        try:
            return self.complexity_calculator.calculate_overall_complexity(svg_root, element_counts)
        except Exception as e:
            self.logger.warning(f"Complexity calculation failed, using fallback: {e}")
            # Fallback calculation
            total_weighted_elements = sum(
                count * self.element_weights.get(element_type, 1.0)
                for element_type, count in element_counts.items()
            )
            # Normalize to 0-1 range (assuming 50 weighted elements = max complexity)
            return min(total_weighted_elements / 50.0, 1.0)

    def _analyze_features(self, svg_root: ET.Element) -> Dict[str, bool]:
        """Analyze SVG features that affect complexity"""
        features = {
            'has_transforms': False,
            'has_clipping': False,
            'has_patterns': False,
            'has_animations': False
        }

        for element in walk(svg_root):
            # Check for transforms
            if element.get('transform'):
                features['has_transforms'] = True

            # Check for clipping
            if element.get('clip-path') or self._get_local_tag(element.tag) == 'clipPath':
                features['has_clipping'] = True

            # Check for patterns
            if self._get_local_tag(element.tag) == 'pattern':
                features['has_patterns'] = True

            # Check for animations
            tag = self._get_local_tag(element.tag)
            if tag in ['animate', 'animateTransform', 'animateMotion', 'animateColor', 'set']:
                features['has_animations'] = True

        return features

    def _calculate_text_complexity(self, svg_root: ET.Element) -> float:
        """Calculate text-specific complexity"""
        text_elements = []

        for element in walk(svg_root):
            tag = self._get_local_tag(element.tag)
            if tag in ['text', 'tspan']:
                text_elements.append(element)

        if not text_elements:
            return 0.0

        complexity_factors = []

        for text_elem in text_elements:
            factor = 0.1  # Base complexity

            # Font complexity
            if text_elem.get('font-family'):
                factor += 0.1
            if text_elem.get('font-size'):
                factor += 0.1
            if text_elem.get('font-weight') in ['bold', 'bolder']:
                factor += 0.1
            if text_elem.get('font-style') == 'italic':
                factor += 0.1

            # Positioning complexity
            if text_elem.get('x') or text_elem.get('y'):
                factor += 0.1
            if text_elem.get('dx') or text_elem.get('dy'):
                factor += 0.2

            # Text effects
            if text_elem.get('text-decoration'):
                factor += 0.1
            if text_elem.get('text-anchor'):
                factor += 0.1

            # Path-based text
            if text_elem.get('textPath'):
                factor += 0.5

            complexity_factors.append(min(factor, 1.0))

        return sum(complexity_factors) / len(complexity_factors) if complexity_factors else 0.0

    def _calculate_path_complexity(self, svg_root: ET.Element) -> float:
        """Calculate path-specific complexity"""
        path_elements = [elem for elem in walk(svg_root) if self._get_local_tag(elem.tag) == 'path']

        if not path_elements:
            return 0.0

        complexity_scores = []

        for path_elem in path_elements:
            path_data = path_elem.get('d', '')
            if not path_data:
                complexity_scores.append(0.0)
                continue

            # Count different command types
            commands = {
                'M': path_data.count('M') + path_data.count('m'),
                'L': path_data.count('L') + path_data.count('l'),
                'C': path_data.count('C') + path_data.count('c'),
                'Q': path_data.count('Q') + path_data.count('q'),
                'A': path_data.count('A') + path_data.count('a'),
                'Z': path_data.count('Z') + path_data.count('z')
            }

            # Calculate complexity based on command types and counts
            total_commands = sum(commands.values())
            if total_commands == 0:
                complexity_scores.append(0.0)
                continue

            # Weighted complexity (curves are more complex than lines)
            weighted_complexity = (
                commands['M'] * 0.1 +
                commands['L'] * 0.2 +
                commands['C'] * 0.8 +
                commands['Q'] * 0.6 +
                commands['A'] * 1.0 +
                commands['Z'] * 0.1
            )

            # Normalize by total commands
            path_complexity = min(weighted_complexity / max(total_commands, 1), 1.0)
            complexity_scores.append(path_complexity)

        return sum(complexity_scores) / len(complexity_scores) if complexity_scores else 0.0

    def _calculate_group_nesting_depth(self, svg_root: ET.Element, current_depth: int = 0) -> int:
        """Calculate maximum group nesting depth"""
        max_depth = current_depth

        for child in svg_root:
            if self._get_local_tag(child.tag) == 'g':
                child_depth = self._calculate_group_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)

        return max_depth

    def _recommend_output_format(self, complexity_score: float, features: Dict[str, bool]) -> OutputFormat:
        """Recommend output format based on complexity and features"""
        # Force specific formats for certain features
        if features['has_animations']:
            return OutputFormat.DEBUG_JSON  # Animations need special handling

        if complexity_score <= self.complexity_thresholds['simple']:
            return OutputFormat.PPTX
        elif complexity_score <= self.complexity_thresholds['moderate']:
            return OutputFormat.PPTX
        elif complexity_score <= self.complexity_thresholds['complex']:
            return OutputFormat.SLIDE_XML  # May need manual review
        else:
            return OutputFormat.DEBUG_JSON  # Too complex, needs analysis

    def _generate_strategies(self, complexity_score: float, features: Dict[str, bool],
                           element_counts: Dict[str, int]) -> List[str]:
        """Generate recommended conversion strategies"""
        strategies = []

        if complexity_score <= self.complexity_thresholds['simple']:
            strategies.append('use_native_drawingml')
            strategies.append('minimal_preprocessing')
        elif complexity_score <= self.complexity_thresholds['moderate']:
            strategies.append('hybrid_approach')
            strategies.append('selective_emf_fallback')
        else:
            strategies.append('comprehensive_preprocessing')
            strategies.append('emf_heavy_approach')

        # Feature-specific strategies
        if features['has_clipping']:
            strategies.append('advanced_clipping_preprocessing')

        if features['has_patterns']:
            strategies.append('pattern_expansion')

        if features['has_animations']:
            strategies.append('animation_extraction')

        if element_counts.get('text', 0) > 10:
            strategies.append('text_optimization')

        if element_counts.get('path', 0) > 20:
            strategies.append('path_simplification')

        return strategies

    def _generate_optimization_suggestions(self, svg_root: ET.Element,
                                         features: Dict[str, bool]) -> List[str]:
        """Generate optimization suggestions"""
        suggestions = []

        # Check for common optimization opportunities
        if len(list(walk(svg_root))) > 100:
            suggestions.append('consider_element_reduction')

        if features['has_transforms']:
            suggestions.append('consolidate_transformations')

        # Check for unused definitions
        defs = svg_root.find('.//{http://www.w3.org/2000/svg}defs')
        if defs is not None and len(defs) > 0:
            suggestions.append('remove_unused_definitions')

        # Check for precision issues
        for element in walk(svg_root):
            for attr_name, attr_value in element.attrib.items():
                if attr_name in ['x', 'y', 'width', 'height', 'cx', 'cy', 'r'] and '.' in str(attr_value):
                    if len(str(attr_value).split('.')[-1]) > 3:
                        suggestions.append('reduce_coordinate_precision')
                        break

        return list(set(suggestions))  # Remove duplicates

    def _estimate_conversion_time(self, complexity_score: float, element_count: int) -> float:
        """Estimate conversion time in milliseconds"""
        # Base time for setup
        base_time = 10.0

        # Time per element (varies by complexity)
        element_time = element_count * (1.0 + complexity_score * 2.0)

        # Complexity overhead
        complexity_overhead = complexity_score * 50.0

        return base_time + element_time + complexity_overhead

    def _create_ir_scene_placeholder(self, svg_root: ET.Element,
                                   element_counts: Dict[str, int]) -> List[Any]:
        """Create IR scene using the new SVG parser - never returns None"""
        try:
            # Use the new SVG to IR parser
            from ..parse.parser import SVGParser

            # Convert the SVG element back to string for the parser
            # This is a bit inefficient but maintains clean interfaces
            svg_string = ET.tostring(svg_root, encoding='unicode')

            parser = SVGParser()
            scene, parse_result = parser.parse_to_ir(svg_string)

            if parse_result.success and scene is not None:
                self.logger.debug(f"Created IR scene with {len(scene)} elements")
                # Tag as placeholder for mappers (if scene supports metadata)
                if hasattr(scene, 'metadata'):
                    if scene.metadata is None:
                        scene.metadata = {}
                    scene.metadata["placeholder"] = True
                    scene.metadata["placeholder_reason"] = "ir_fallback"
                return scene
            else:
                self.logger.warning(f"IR scene creation failed: {parse_result.error if parse_result else 'Unknown error'}")

        except Exception as e:
            self.logger.warning(f"Could not create IR scene: {e}")

        # Synthesize a minimal, valid scene that is iterable
        self.logger.debug("Creating empty scene placeholder")
        return []

    def _calculate_ir_complexity_adjustment(self, scene) -> float:
        """Calculate complexity adjustment based on IR analysis"""
        try:
            from ..ir.scene import Path, TextFrame, Group, Image

            adjustment_factor = 1.0
            total_elements = len(scene)

            if total_elements == 0:
                return adjustment_factor

            path_complexity_scores = []
            text_complexity_scores = []
            group_complexity_scores = []

            for element in scene:
                if isinstance(element, Path):
                    # Analyze path segment complexity
                    segment_count = len(element.segments)

                    # Count Bezier curves (more complex than lines)
                    curve_count = sum(1 for seg in element.segments
                                    if hasattr(seg, 'control1') or hasattr(seg, 'control2'))

                    # Path complexity based on segments and curves
                    if segment_count > 0:
                        curve_ratio = curve_count / segment_count
                        path_score = min((segment_count / 20.0) + (curve_ratio * 0.5), 1.0)
                        path_complexity_scores.append(path_score)

                    # Check for complex features
                    if element.clip:
                        adjustment_factor *= 1.2
                    if element.stroke and hasattr(element.stroke, 'is_dashed') and element.stroke.is_dashed:
                        adjustment_factor *= 1.15

                elif isinstance(element, TextFrame):
                    # Analyze text complexity
                    run_count = len(element.runs)
                    total_text_length = sum(len(run.text) for run in element.runs)

                    text_score = min((run_count / 10.0) + (total_text_length / 200.0), 1.0)
                    text_complexity_scores.append(text_score)

                elif isinstance(element, Group):
                    # Analyze group complexity
                    child_count = len(element.children)
                    group_score = min(child_count / 15.0, 1.0)
                    group_complexity_scores.append(group_score)

                    if element.clip:
                        adjustment_factor *= 1.1

                elif isinstance(element, Image):
                    # Images add moderate complexity
                    adjustment_factor *= 1.05

            # Calculate average complexities
            if path_complexity_scores:
                avg_path_complexity = sum(path_complexity_scores) / len(path_complexity_scores)
                adjustment_factor *= (1.0 + avg_path_complexity * 0.3)

            if text_complexity_scores:
                avg_text_complexity = sum(text_complexity_scores) / len(text_complexity_scores)
                adjustment_factor *= (1.0 + avg_text_complexity * 0.2)

            if group_complexity_scores:
                avg_group_complexity = sum(group_complexity_scores) / len(group_complexity_scores)
                adjustment_factor *= (1.0 + avg_group_complexity * 0.25)

            self.logger.debug(f"IR complexity adjustment: {adjustment_factor:.3f}")
            return min(adjustment_factor, 2.0)  # Cap at 2x adjustment

        except Exception as e:
            self.logger.warning(f"IR complexity adjustment failed: {e}")
            return 1.0  # No adjustment on error

    def _get_local_tag(self, tag: str) -> str:
        """Extract local tag name from namespaced tag"""
        if '}' in tag:
            return tag.split('}')[1]
        return tag


def create_analyzer() -> SVGAnalyzer:
    """Factory function to create SVGAnalyzer"""
    return SVGAnalyzer()