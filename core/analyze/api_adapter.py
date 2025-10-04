"""
API Adapter for SVG Analyzer

Adapts the existing SVG Analyzer to API-friendly response format and adds
additional features needed for REST API endpoints.
"""

from typing import Dict, Any, List, Set
from lxml import etree as ET

from .analyzer import SVGAnalyzer, AnalysisResult
from .types import (
    ElementCounts,
    FeatureSet,
    PerformanceEstimate,
    PolicyRecommendation,
    SVGAnalysisResult
)
from .constants import FILTER_NAME_MAP, SVG_NAMESPACE
from core.policy.config import OutputTarget


class SVGAnalyzerAPI:
    """
    API-friendly wrapper around SVGAnalyzer.

    Converts internal analyzer results to API response format and adds
    policy-based recommendations.
    """

    def __init__(self):
        """Initialize API adapter with core analyzer."""
        self.analyzer = SVGAnalyzer()

    def analyze_svg(self, svg_content: str) -> SVGAnalysisResult:
        """
        Analyze SVG and return API-formatted result.

        Args:
            svg_content: SVG XML content as string

        Returns:
            SVGAnalysisResult with complexity, features, and recommendations
        """
        # Parse SVG
        try:
            svg_root = ET.fromstring(svg_content.encode('utf-8'))
        except ET.XMLSyntaxError as e:
            raise ValueError(f"Invalid SVG XML: {str(e)}")

        # Run core analysis
        analysis = self.analyzer.analyze(svg_root)

        # Convert to API format
        element_counts = self._extract_element_counts(analysis)
        features = self._extract_features(analysis, svg_root)
        recommended_policy = self._recommend_policy(analysis)
        performance = self._estimate_performance(analysis)
        warnings = self._generate_warnings(analysis, features)

        return SVGAnalysisResult(
            complexity_score=int(analysis.complexity_score * 100),  # Convert 0-1 to 0-100
            element_counts=element_counts,
            features=features,
            recommended_policy=recommended_policy,
            estimated_performance=performance,
            warnings=warnings
        )

    def _extract_element_counts(self, analysis: AnalysisResult) -> ElementCounts:
        """Extract element counts from analysis result."""
        return ElementCounts(
            total_elements=analysis.element_count,
            shapes=self._count_shapes(analysis),
            paths=analysis.path_count,
            text=analysis.text_count,
            groups=analysis.group_count,
            gradients=analysis.gradient_count,
            filters=analysis.filter_count,
            images=analysis.image_count,
            max_nesting_depth=analysis.group_nesting_depth
        )

    def _count_shapes(self, analysis: AnalysisResult) -> int:
        """
        Count basic shapes (rect, circle, ellipse, line, polyline, polygon).

        Note: Current analyzer doesn't separate shapes from total count,
        so we estimate based on element_count minus known counts.
        """
        # Estimate shapes as: total - (paths + text + groups + images + filters + gradients)
        known_counts = (
            analysis.path_count +
            analysis.text_count +
            analysis.group_count +
            analysis.image_count +
            analysis.filter_count +
            analysis.gradient_count
        )
        return max(0, analysis.element_count - known_counts)

    def _extract_features(self, analysis: AnalysisResult, svg_root: ET.Element) -> FeatureSet:
        """Extract detected features from analysis."""
        features = FeatureSet()

        # Set boolean flags
        features.has_animations = analysis.has_animations
        features.has_clipping = analysis.has_clipping
        features.has_patterns = analysis.has_patterns
        features.has_gradients = analysis.gradient_count > 0
        features.has_filters = analysis.filter_count > 0

        # Detect gradient types
        if analysis.gradient_count > 0:
            features.gradient_types = self._detect_gradient_types(svg_root)

        # Detect filter types
        if analysis.filter_count > 0:
            features.filter_types = self._detect_filter_types(svg_root)

        # Detect complex features
        features.has_complex_paths = analysis.path_complexity > 0.6
        features.has_complex_transforms = analysis.has_transforms
        features.has_embedded_images = analysis.image_count > 0

        return features

    def _detect_gradient_types(self, svg_root: ET.Element) -> set:
        """Detect types of gradients used in SVG."""
        gradient_types = set()

        # Check for linear gradients
        if svg_root.findall('.//{http://www.w3.org/2000/svg}linearGradient'):
            gradient_types.add('linear')

        # Check for radial gradients
        if svg_root.findall('.//{http://www.w3.org/2000/svg}radialGradient'):
            gradient_types.add('radial')

        # Check for mesh gradients
        if svg_root.findall('.//{http://www.w3.org/2000/svg}meshgradient'):
            gradient_types.add('mesh')

        return gradient_types

    def _detect_filter_types(self, svg_root: ET.Element) -> Set[str]:
        """
        Detect types of filters used in SVG.

        Uses proper FILTER_NAME_MAP for accurate filter name conversion.
        Covers all 17 SVG filter primitives.

        Args:
            svg_root: Root SVG element

        Returns:
            Set of simplified filter names (e.g., 'blur', 'dropshadow')
        """
        filter_types = set()

        # Use proper mapping from constants (all 17 filter primitives)
        for fe_name, simple_name in FILTER_NAME_MAP.items():
            if svg_root.findall(f'.//{{{SVG_NAMESPACE}}}{fe_name}'):
                filter_types.add(simple_name)

        return filter_types

    def _recommend_policy(self, analysis: AnalysisResult) -> PolicyRecommendation:
        """
        Recommend policy based on complexity and features.

        Maps analyzer's complexity score to OutputTarget policy.
        """
        score = analysis.complexity_score

        # Decision thresholds
        if score < 0.3:
            # Simple SVG - speed is fine
            target = "speed"
            confidence = 0.9
            reasons = [
                f"Low complexity (score: {int(score * 100)})",
                f"Only {analysis.element_count} elements",
                "No complex features detected"
            ]
        elif score < 0.6:
            # Moderate complexity - balanced is best
            target = "balanced"
            confidence = 0.85
            reasons = [
                f"Moderate complexity (score: {int(score * 100)})",
                f"{analysis.element_count} elements with some complexity"
            ]

            if analysis.gradient_count > 0:
                reasons.append(f"{analysis.gradient_count} gradients detected")
            if analysis.filter_count > 0:
                reasons.append(f"{analysis.filter_count} filters may need native rendering")
        else:
            # High complexity - quality needed
            target = "quality"
            confidence = 0.95
            reasons = [
                f"High complexity (score: {int(score * 100)})",
                f"{analysis.element_count} elements require careful rendering"
            ]

            if analysis.filter_count > 0:
                reasons.append(f"{analysis.filter_count} filters require quality mode")
            if analysis.path_complexity > 0.7:
                reasons.append("Complex paths detected")
            if analysis.group_nesting_depth > 5:
                reasons.append(f"Deep nesting ({analysis.group_nesting_depth} levels)")

        return PolicyRecommendation(
            target=target,
            confidence=confidence,
            reasons=reasons
        )

    def _estimate_performance(self, analysis: AnalysisResult) -> PerformanceEstimate:
        """
        Estimate conversion performance.

        Uses analyzer's conversion time estimate and adds memory/size estimates.
        """
        # Use analyzer's time estimate
        conversion_time_ms = int(analysis.estimated_conversion_time_ms)

        # Estimate output size: base size + element overhead
        # Base PPTX is ~30KB, each element adds ~2KB average
        output_size_kb = 30 + (analysis.element_count * 2)

        # Add overhead for complex features
        if analysis.filter_count > 0:
            output_size_kb += analysis.filter_count * 10  # Filters add significant size
        if analysis.image_count > 0:
            output_size_kb += analysis.image_count * 20  # Images add size

        # Estimate memory: base + per-element overhead
        # Base memory ~50MB, each element adds ~1KB
        memory_usage_mb = 50 + ((analysis.element_count * 1024) // (1024 * 1024))

        return PerformanceEstimate(
            conversion_time_ms=conversion_time_ms,
            output_size_kb=output_size_kb,
            memory_usage_mb=memory_usage_mb
        )

    def _generate_warnings(self, analysis: AnalysisResult, features: FeatureSet) -> List[str]:
        """Generate warnings based on analysis."""
        warnings = []

        # Filter warnings
        if analysis.filter_count > 0:
            if analysis.filter_count > 5:
                warnings.append(
                    f"SVG contains {analysis.filter_count} filters - some may be rasterized for compatibility"
                )
            else:
                warnings.append(
                    f"SVG contains {analysis.filter_count} filters that may need EMF fallback"
                )

        # Gradient warnings
        if analysis.gradient_count > 10:
            warnings.append(
                f"High gradient count ({analysis.gradient_count}) may impact file size"
            )

        # Text warnings
        if analysis.text_complexity > 0.7:
            warnings.append(
                "Complex text rendering detected - font availability may vary across platforms"
            )

        # Path warnings
        if analysis.path_complexity > 0.8:
            warnings.append(
                "Very complex paths detected - consider simplifying for better performance"
            )

        # Nesting warnings
        if analysis.group_nesting_depth > 10:
            warnings.append(
                f"Deep nesting ({analysis.group_nesting_depth} levels) may impact conversion performance"
            )

        # Animation warnings
        if features.has_animations:
            warnings.append(
                "SVG animations will be converted to static frames or slide sequences"
            )

        return warnings

    @staticmethod
    def _svg_ns() -> str:
        """Return SVG namespace URI."""
        return "http://www.w3.org/2000/svg"


def create_api_analyzer() -> SVGAnalyzerAPI:
    """Factory function to create API analyzer."""
    return SVGAnalyzerAPI()
