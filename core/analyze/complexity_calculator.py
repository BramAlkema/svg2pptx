#!/usr/bin/env python3
"""
Complexity Calculator

Calculates SVG complexity scores for conversion strategy decisions.
"""

import logging
import math
from typing import Dict, Any, List
from lxml import etree as ET
from ..xml.safe_iter import walk, children, is_element

logger = logging.getLogger(__name__)


class ComplexityCalculator:
    """
    Calculates complexity scores for SVG elements and overall scenes.

    Uses multiple factors to determine how complex an SVG is to convert,
    helping the policy engine make informed decisions.
    """

    def __init__(self):
        """Initialize complexity calculator with weights and thresholds"""
        # Element type weights (higher = more complex)
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
            'pattern': 0.8,
            'animate': 1.0,
            'animateTransform': 1.1,
            'animateMotion': 1.2
        }

        # Feature complexity multipliers
        self.feature_multipliers = {
            'has_transforms': 1.2,
            'has_clipping': 1.3,
            'has_patterns': 1.25,
            'has_animations': 1.5,
            'has_gradients': 1.1,
            'has_filters': 1.4,
            'has_masks': 1.35
        }

        self.logger = logging.getLogger(__name__)

    def calculate_overall_complexity(self, svg_root: ET.Element,
                                   element_counts: Dict[str, int]) -> float:
        """
        Calculate overall complexity score for SVG.

        Args:
            svg_root: SVG root element
            element_counts: Dictionary of element type counts

        Returns:
            Complexity score from 0.0 (simple) to 1.0 (complex)
        """
        try:
            # Base complexity from element counts and weights
            base_complexity = self._calculate_base_complexity(element_counts)

            # Feature-based complexity adjustments
            feature_multiplier = self._calculate_feature_multiplier(svg_root)

            # Structure-based complexity (nesting, relationships)
            structure_complexity = self._calculate_structure_complexity(svg_root)

            # Content-based complexity (text length, path complexity)
            content_complexity = self._calculate_content_complexity(svg_root)

            # Combine all factors
            raw_complexity = (
                base_complexity * feature_multiplier +
                structure_complexity * 0.3 +
                content_complexity * 0.2
            )

            # Normalize to 0-1 range using sigmoid function
            normalized_complexity = self._normalize_complexity(raw_complexity)

            self.logger.debug(f"Complexity calculation: base={base_complexity:.3f}, "
                            f"features={feature_multiplier:.3f}, structure={structure_complexity:.3f}, "
                            f"content={content_complexity:.3f}, final={normalized_complexity:.3f}")

            return normalized_complexity

        except Exception as e:
            self.logger.error(f"Complexity calculation failed: {e}")
            return 0.5  # Default to moderate complexity

    def _calculate_base_complexity(self, element_counts: Dict[str, int]) -> float:
        """Calculate base complexity from element counts and weights"""
        total_weighted_elements = 0.0

        for element_type, count in element_counts.items():
            weight = self.element_weights.get(element_type, 0.5)  # Default weight for unknown elements
            total_weighted_elements += count * weight

        # Normalize by expected element count (50 weighted elements = high complexity)
        return min(total_weighted_elements / 50.0, 2.0)

    def _calculate_feature_multiplier(self, svg_root: ET.Element) -> float:
        """Calculate complexity multiplier based on SVG features"""
        multiplier = 1.0
        detected_features = set()

        for element in walk(svg_root):
            # Check for transforms
            if element.get('transform'):
                detected_features.add('has_transforms')

            # Check for clipping
            if element.get('clip-path') or self._get_local_tag(element.tag) == 'clipPath':
                detected_features.add('has_clipping')

            # Check for patterns
            if self._get_local_tag(element.tag) == 'pattern':
                detected_features.add('has_patterns')

            # Check for gradients
            tag = self._get_local_tag(element.tag)
            if tag in ['linearGradient', 'radialGradient']:
                detected_features.add('has_gradients')

            # Check for filters
            if tag.startswith('fe') or tag == 'filter' or element.get('filter'):
                detected_features.add('has_filters')

            # Check for masks
            if tag == 'mask' or element.get('mask'):
                detected_features.add('has_masks')

            # Check for animations
            if tag in ['animate', 'animateTransform', 'animateMotion', 'animateColor', 'set']:
                detected_features.add('has_animations')

        # Apply multipliers for detected features
        for feature in detected_features:
            feature_multiplier = self.feature_multipliers.get(feature, 1.0)
            multiplier *= feature_multiplier

        return min(multiplier, 3.0)  # Cap at 3x multiplier

    def _calculate_structure_complexity(self, svg_root: ET.Element) -> float:
        """Calculate complexity based on SVG structure"""
        complexity_factors = []

        # Group nesting depth
        max_nesting = self._calculate_max_nesting_depth(svg_root)
        nesting_complexity = min(max_nesting / 10.0, 1.0)  # Max depth 10 = full complexity
        complexity_factors.append(nesting_complexity)

        # Definition usage complexity
        defs_complexity = self._calculate_defs_complexity(svg_root)
        complexity_factors.append(defs_complexity)

        # Cross-references (use elements, href attributes)
        reference_complexity = self._calculate_reference_complexity(svg_root)
        complexity_factors.append(reference_complexity)

        return sum(complexity_factors) / len(complexity_factors) if complexity_factors else 0.0

    def _calculate_content_complexity(self, svg_root: ET.Element) -> float:
        """Calculate complexity based on content characteristics"""
        complexity_factors = []

        # Path data complexity
        path_complexity = self._calculate_path_data_complexity(svg_root)
        complexity_factors.append(path_complexity)

        # Text content complexity
        text_complexity = self._calculate_text_content_complexity(svg_root)
        complexity_factors.append(text_complexity)

        # Coordinate precision complexity
        precision_complexity = self._calculate_precision_complexity(svg_root)
        complexity_factors.append(precision_complexity)

        return sum(complexity_factors) / len(complexity_factors) if complexity_factors else 0.0

    def _calculate_max_nesting_depth(self, element: ET.Element, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth in SVG"""
        max_depth = current_depth

        for child in children(element):
            child_depth = self._calculate_max_nesting_depth(child, current_depth + 1)
            max_depth = max(max_depth, child_depth)

        return max_depth

    def _calculate_defs_complexity(self, svg_root: ET.Element) -> float:
        """Calculate complexity from definitions and their usage"""
        defs_elements = svg_root.findall('.//{http://www.w3.org/2000/svg}defs')

        if not defs_elements:
            return 0.0

        total_def_children = sum(len(defs) for defs in defs_elements)

        # Count references to definitions
        reference_count = 0
        for element in walk(svg_root):
            for attr_value in element.attrib.values():
                if isinstance(attr_value, str) and attr_value.startswith('url(#'):
                    reference_count += 1

        # More definitions and references = higher complexity
        def_complexity = min(total_def_children / 20.0, 1.0)
        ref_complexity = min(reference_count / 30.0, 1.0)

        return (def_complexity + ref_complexity) / 2.0

    def _calculate_reference_complexity(self, svg_root: ET.Element) -> float:
        """Calculate complexity from cross-references and use elements"""
        use_elements = len(svg_root.findall('.//{http://www.w3.org/2000/svg}use'))

        # Count href references
        href_count = 0
        for element in walk(svg_root):
            if element.get('href') or element.get('{http://www.w3.org/1999/xlink}href'):
                href_count += 1

        # Normalize reference complexity
        use_complexity = min(use_elements / 10.0, 1.0)
        href_complexity = min(href_count / 15.0, 1.0)

        return (use_complexity + href_complexity) / 2.0

    def _calculate_path_data_complexity(self, svg_root: ET.Element) -> float:
        """Calculate complexity of path data strings"""
        path_elements = svg_root.findall('.//{http://www.w3.org/2000/svg}path')

        if not path_elements:
            return 0.0

        complexity_scores = []

        for path in path_elements:
            path_data = path.get('d', '')
            if not path_data:
                complexity_scores.append(0.0)
                continue

            # Count command types (curves are more complex)
            curve_commands = path_data.count('C') + path_data.count('c') + \
                           path_data.count('Q') + path_data.count('q') + \
                           path_data.count('A') + path_data.count('a')

            total_commands = len([c for c in path_data if c.isalpha()])

            if total_commands == 0:
                complexity_scores.append(0.0)
                continue

            # Higher ratio of curves = higher complexity
            curve_ratio = curve_commands / total_commands
            path_length_factor = min(len(path_data) / 1000.0, 1.0)  # Long paths are complex

            path_score = (curve_ratio * 0.7 + path_length_factor * 0.3)
            complexity_scores.append(min(path_score, 1.0))

        return sum(complexity_scores) / len(complexity_scores) if complexity_scores else 0.0

    def _calculate_text_content_complexity(self, svg_root: ET.Element) -> float:
        """Calculate complexity of text content"""
        text_elements = svg_root.findall('.//{http://www.w3.org/2000/svg}text') + \
                       svg_root.findall('.//{http://www.w3.org/2000/svg}tspan')

        if not text_elements:
            return 0.0

        complexity_factors = []

        for text_elem in text_elements:
            factor = 0.0

            # Text length
            text_content = text_elem.text or ''
            if len(text_content) > 50:
                factor += 0.3

            # Multiple tspan children
            tspan_children = text_elem.findall('.//{http://www.w3.org/2000/svg}tspan')
            if len(tspan_children) > 3:
                factor += 0.4

            # Complex positioning
            if text_elem.get('dx') or text_elem.get('dy'):
                factor += 0.2

            # Text on path
            if text_elem.find('.//{http://www.w3.org/2000/svg}textPath') is not None:
                factor += 0.5

            complexity_factors.append(min(factor, 1.0))

        return sum(complexity_factors) / len(complexity_factors) if complexity_factors else 0.0

    def _calculate_precision_complexity(self, svg_root: ET.Element) -> float:
        """Calculate complexity from coordinate precision"""
        high_precision_count = 0
        total_numeric_attrs = 0

        numeric_attrs = ['x', 'y', 'width', 'height', 'cx', 'cy', 'r', 'rx', 'ry',
                        'x1', 'y1', 'x2', 'y2', 'offset']

        for element in walk(svg_root):
            for attr in numeric_attrs:
                value = element.get(attr)
                if value and '.' in str(value):
                    total_numeric_attrs += 1
                    decimal_places = len(str(value).split('.')[-1])
                    if decimal_places > 3:
                        high_precision_count += 1

        if total_numeric_attrs == 0:
            return 0.0

        precision_ratio = high_precision_count / total_numeric_attrs
        return min(precision_ratio, 1.0)

    def _normalize_complexity(self, raw_complexity: float) -> float:
        """Normalize complexity score to 0-1 range using sigmoid function"""
        # Use sigmoid function to map raw complexity to 0-1 range
        # This ensures extreme values don't break the scale
        return 1.0 / (1.0 + math.exp(-2.0 * (raw_complexity - 1.0)))

    def _get_local_tag(self, tag: str) -> str:
        """Extract local tag name from namespaced tag"""
        if '}' in tag:
            return tag.split('}')[1]
        return tag