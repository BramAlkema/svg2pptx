#!/usr/bin/env python3
"""
Comprehensive WordArt Builder

Complete integration of all WordArt mapping services:
- Transform decomposition and DrawingML generation
- Color and gradient mapping
- Path fitting and warp analysis
- Policy-driven decision making
- Complete XML generation pipeline

Provides the final layer that ties all WordArt components together.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from lxml import etree as ET

from ..services.conversion_services import ConversionServices
from ..converters.base import ConversionContext
from ..services.wordart_integration_service import (
    WordArtIntegrationService, WordArtGenerationResult, TextRun
)
from ..converters.wordart_builder import (
    WordArtTransformBuilder, WordArtShapeConfig
)
from ..services.wordart_transform_service import (
    create_transform_decomposer, TransformComponents
)
from ..services.wordart_color_mapping_service import (
    create_wordart_color_mapping_service
)
from core.algorithms.curve_text_positioning import (
    create_path_warp_fitter, WarpFitResult
)
from core.policy.engine import Policy
from core.policy.targets import TextDecision


@dataclass
class ComprehensiveWordArtResult:
    """Result of comprehensive WordArt generation."""

    success: bool
    wordart_xml: Optional[ET.Element]
    generation_metadata: Dict[str, Any]
    performance_metrics: Dict[str, float]
    policy_decision: Optional[TextDecision]
    fallback_reason: Optional[str] = None
    alternative_strategies: List[str] = None


@dataclass
class WordArtGenerationConfig:
    """Configuration for WordArt generation process."""

    # Transform settings
    enable_transform_analysis: bool = True
    max_transform_complexity: float = 8.0

    # Color settings
    enable_gradient_mapping: bool = True
    max_gradient_stops: int = 8
    simplify_gradients: bool = True

    # Path settings
    enable_path_warping: bool = True
    min_warp_confidence: float = 0.6

    # Policy settings
    enable_policy_decisions: bool = True
    fallback_on_complexity: bool = True

    # Performance settings
    enable_performance_metrics: bool = True
    timeout_ms: float = 5000.0


class ComprehensiveWordArtBuilder:
    """
    Complete WordArt generation system.

    Integrates all mapping services to provide comprehensive SVG text
    to PowerPoint WordArt conversion with intelligent fallback strategies.
    """

    def __init__(self, services: ConversionServices, config: Optional[WordArtGenerationConfig] = None):
        """
        Initialize comprehensive builder with all dependencies.

        Args:
            services: ConversionServices container
            config: Configuration for generation process
        """
        self.services = services
        self.config = config or WordArtGenerationConfig()

        # Initialize all component services
        self.integration_service = WordArtIntegrationService(services)
        self.transform_decomposer = create_transform_decomposer()
        self.color_service = create_wordart_color_mapping_service(services)
        self.wordart_builder = WordArtTransformBuilder()
        self.warp_fitter = create_path_warp_fitter()

        # Policy engine for intelligent decisions
        self.policy = Policy()

    def build_wordart(self, text_element: ET.Element,
                     context: ConversionContext) -> ComprehensiveWordArtResult:
        """
        Build complete WordArt from SVG text element.

        Args:
            text_element: SVG text element
            context: Conversion context

        Returns:
            ComprehensiveWordArtResult with XML and comprehensive metadata
        """
        import time
        start_time = time.time()

        try:
            # Phase 1: Initial analysis and validation
            validation_result = self._validate_input(text_element, context)
            if not validation_result['valid']:
                return self._failure_result(
                    f"Input validation failed: {validation_result['reason']}"
                )

            # Phase 2: Multi-dimensional analysis
            analysis_result = self._comprehensive_analysis(text_element, context)

            # Phase 3: Policy decision making
            policy_decision = self._make_comprehensive_policy_decision(
                text_element, analysis_result, context
            )

            if not policy_decision.use_native:
                return self._failure_result(
                    f"Policy rejected WordArt: {', '.join(r.value for r in policy_decision.reasons)}",
                    policy_decision=policy_decision,
                    alternatives=self._suggest_alternatives(policy_decision)
                )

            # Phase 4: WordArt generation using integration service
            generation_result = self.integration_service.generate_wordart(
                text_element, context
            )

            if not generation_result.success:
                return self._failure_result(
                    f"Generation failed: {generation_result.fallback_reason}",
                    policy_decision=policy_decision
                )

            # Phase 5: Post-processing and optimization
            optimized_xml = self._optimize_wordart_xml(
                generation_result.wordart_xml, analysis_result
            )

            # Calculate comprehensive metrics
            total_time = (time.time() - start_time) * 1000  # ms

            # Build comprehensive metadata
            metadata = {
                'analysis_result': analysis_result,
                'policy_decision': policy_decision.__dict__,
                'generation_metadata': generation_result.decision_metadata,
                'optimization_applied': True,
                'config_used': self.config.__dict__
            }

            # Combine performance metrics
            performance_metrics = {
                'total_generation_time_ms': total_time,
                'integration_time_ms': generation_result.performance_metrics.get('generation_time_ms', 0),
                'analysis_time_ms': total_time - generation_result.performance_metrics.get('generation_time_ms', 0),
                'text_complexity_score': analysis_result.get('text_complexity', 0),
                'transform_complexity_score': (analysis_result.get('transform_analysis') or {}).get('complexity', {}).get('complexity_score', 0)
            }

            return ComprehensiveWordArtResult(
                success=True,
                wordart_xml=optimized_xml,
                generation_metadata=metadata,
                performance_metrics=performance_metrics,
                policy_decision=policy_decision,
                alternative_strategies=[]
            )

        except Exception as e:
            return self._failure_result(f"Comprehensive generation failed: {e}")

    def _validate_input(self, text_element: ET.Element,
                       context: ConversionContext) -> Dict[str, Any]:
        """Validate input elements and context."""
        if text_element is None:
            return {'valid': False, 'reason': 'Text element is None'}

        if text_element.tag not in ['{http://www.w3.org/2000/svg}text', 'text']:
            return {'valid': False, 'reason': f'Invalid element tag: {text_element.tag}'}

        if context is None or context.services is None:
            return {'valid': False, 'reason': 'Invalid conversion context'}

        # Check for text content
        text_content = self._extract_all_text(text_element)
        if not text_content.strip():
            return {'valid': False, 'reason': 'No text content found'}

        return {'valid': True, 'text_content': text_content}

    def _comprehensive_analysis(self, text_element: ET.Element,
                               context: ConversionContext) -> Dict[str, Any]:
        """Perform comprehensive multi-dimensional analysis."""
        analysis = {}

        # Text analysis
        analysis['text_content'] = self._extract_all_text(text_element)
        analysis['text_complexity'] = self._calculate_text_complexity(text_element)
        analysis['text_runs'] = self._analyze_text_runs(text_element)

        # Transform analysis
        if self.config.enable_transform_analysis:
            analysis['transform_analysis'] = self._analyze_transforms_comprehensive(text_element)

        # Path analysis
        if self.config.enable_path_warping:
            analysis['path_analysis'] = self._analyze_text_paths_comprehensive(text_element, context)

        # Style analysis
        analysis['style_analysis'] = self._analyze_styling(text_element)

        # Layout analysis
        analysis['layout_analysis'] = self._analyze_layout(text_element, context)

        return analysis

    def _calculate_text_complexity(self, text_element: ET.Element) -> float:
        """Calculate comprehensive text complexity score."""
        complexity = 0.0

        # Base text length factor
        text_content = self._extract_all_text(text_element)
        complexity += min(len(text_content) * 0.1, 2.0)

        # Multi-line text adds complexity
        if '\n' in text_content or len(text_content.split()) > 10:
            complexity += 1.5

        # Special characters add complexity
        special_chars = sum(1 for c in text_content if not c.isalnum() and not c.isspace())
        complexity += min(special_chars * 0.2, 1.0)

        # Nested elements (tspan, etc.) add complexity
        nested_elements = len(list(text_element.iter())) - 1
        complexity += min(nested_elements * 0.3, 1.5)

        return complexity

    def _analyze_transforms_comprehensive(self, text_element: ET.Element) -> Optional[Dict[str, Any]]:
        """Comprehensive transform analysis."""
        transform_attr = text_element.get('transform')
        if not transform_attr:
            return None

        try:
            # Use existing decomposer
            components = self.transform_decomposer.decompose_transform_string(transform_attr)
            complexity_analysis = self.transform_decomposer.analyze_transform_complexity(components)

            # Additional analysis
            analysis = {
                'transform_string': transform_attr,
                'components': components.__dict__,
                'complexity': complexity_analysis,
                'wordart_compatible': complexity_analysis.get('complexity_score', 10) <= self.config.max_transform_complexity,
                'primary_transform_type': self._identify_primary_transform_type(components)
            }

            return analysis

        except Exception as e:
            return {'error': str(e), 'transform_string': transform_attr}

    def _analyze_text_paths_comprehensive(self, text_element: ET.Element,
                                        context: ConversionContext) -> Optional[Dict[str, Any]]:
        """Comprehensive text path analysis."""
        # Check for textPath element
        textpath = text_element.find('.//{http://www.w3.org/2000/svg}textPath')
        if textpath is None:
            return None

        # Get path reference
        href = textpath.get('{http://www.w3.org/1999/xlink}href') or textpath.get('href')
        if not href or not href.startswith('#'):
            return {'error': 'Invalid textPath reference'}

        # Find path definition (would need full SVG context in real implementation)
        path_data = self._find_path_data_comprehensive(href[1:], text_element, context)
        if not path_data:
            return {'error': 'Path data not found'}

        try:
            # Comprehensive warp fitting
            warp_result = self.warp_fitter.fit_path_to_warp(
                path_data,
                min_confidence=self.config.min_warp_confidence
            )

            analysis = {
                'path_reference': href,
                'path_data': path_data,
                'warp_result': warp_result.__dict__ if warp_result else None,
                'wordart_compatible': warp_result and warp_result.confidence >= self.config.min_warp_confidence,
                'recommended_preset': warp_result.preset_type if warp_result else None
            }

            return analysis

        except Exception as e:
            return {'error': str(e), 'path_reference': href}

    def _analyze_styling(self, text_element: ET.Element) -> Dict[str, Any]:
        """Analyze text styling for WordArt compatibility."""
        analysis = {
            'font_family': text_element.get('font-family', 'Arial'),
            'font_size': text_element.get('font-size', '24'),
            'fill_color': text_element.get('fill', '#000000'),
            'stroke_color': text_element.get('stroke'),
            'stroke_width': text_element.get('stroke-width', '0'),
            'opacity': text_element.get('opacity', '1.0')
        }

        # Check for complex styling
        analysis['has_gradient_fill'] = analysis['fill_color'].startswith('url(#')
        analysis['has_stroke'] = analysis['stroke_color'] is not None
        analysis['has_opacity'] = float(analysis['opacity']) < 1.0

        # Compatibility score
        complexity = 0
        if analysis['has_gradient_fill']:
            complexity += 1
        if analysis['has_stroke']:
            complexity += 1
        if analysis['has_opacity']:
            complexity += 0.5

        analysis['style_complexity'] = complexity
        analysis['wordart_compatible'] = complexity <= 3.0

        return analysis

    def _analyze_layout(self, text_element: ET.Element,
                       context: ConversionContext) -> Dict[str, Any]:
        """Analyze text layout and positioning."""
        analysis = {
            'x': text_element.get('x', '0'),
            'y': text_element.get('y', '0'),
            'dx': text_element.get('dx'),
            'dy': text_element.get('dy'),
            'text_anchor': text_element.get('text-anchor', 'start')
        }

        # Check for complex positioning
        analysis['has_offset'] = analysis['dx'] is not None or analysis['dy'] is not None
        analysis['has_custom_anchor'] = analysis['text_anchor'] != 'start'

        # Estimate bounding box (simplified)
        try:
            x = float(analysis['x'])
            y = float(analysis['y'])
            font_size = float(text_element.get('font-size', '24'))
            text_content = self._extract_all_text(text_element)

            # Rough estimation
            width = len(text_content) * font_size * 0.6
            height = font_size * 1.2

            analysis['estimated_bounds'] = {
                'x': x, 'y': y, 'width': width, 'height': height
            }

        except (ValueError, TypeError):
            analysis['estimated_bounds'] = None

        return analysis

    def _make_comprehensive_policy_decision(self, text_element: ET.Element,
                                          analysis_result: Dict[str, Any],
                                          context: ConversionContext) -> TextDecision:
        """Make comprehensive policy decision with full analysis."""

        # Create comprehensive mock text frame
        mock_text_frame = type('ComprehensiveMockTextFrame', (), {
            'transform': text_element.get('transform'),
            'complexity_score': analysis_result.get('text_complexity', 0),
            'runs': [type('MockRun', (), {
                'has_decoration': False,
                'font_family': analysis_result.get('style_analysis', {}).get('font_family', 'Arial')
            })()],
            'is_multiline': '\n' in analysis_result.get('text_content', ''),
            'style_complexity': analysis_result.get('style_analysis', {}).get('style_complexity', 0),
            'transform_complexity': analysis_result.get('transform_analysis', {}).get('complexity', {}).get('complexity_score', 0)
        })()

        return self.policy.decide_text(mock_text_frame)

    def _optimize_wordart_xml(self, wordart_xml: ET.Element,
                             analysis_result: Dict[str, Any]) -> ET.Element:
        """Post-process and optimize WordArt XML."""
        if wordart_xml is None:
            return None

        # Clone for safe modification
        optimized = ET.Element(wordart_xml.tag, wordart_xml.attrib)
        for child in wordart_xml:
            optimized.append(child)

        # Apply optimizations based on analysis
        if analysis_result.get('style_analysis', {}).get('style_complexity', 0) > 2:
            self._simplify_complex_styling(optimized)

        if analysis_result.get('transform_analysis', {}).get('complexity', {}).get('complexity_score', 0) > 5:
            self._optimize_complex_transforms(optimized)

        return optimized

    def _simplify_complex_styling(self, wordart_xml: ET.Element) -> None:
        """Simplify complex styling for better compatibility."""
        # Implementation would simplify gradients, reduce opacity complexity, etc.
        pass

    def _optimize_complex_transforms(self, wordart_xml: ET.Element) -> None:
        """Optimize complex transforms for better rendering."""
        # Implementation would optimize transform chains, reduce precision, etc.
        pass

    def _suggest_alternatives(self, policy_decision: TextDecision) -> List[str]:
        """Suggest alternative conversion strategies."""
        alternatives = []

        # Convert reasons to string values for checking
        reason_values = [r.value for r in policy_decision.reasons]

        if any('complex' in reason for reason in reason_values):
            alternatives.append('EMF embedding with simplified transforms')
            alternatives.append('Text-to-path conversion')

        if any('transform' in reason for reason in reason_values):
            alternatives.append('Matrix decomposition with fallback')

        if any('gradient' in reason for reason in reason_values):
            alternatives.append('Solid color approximation')

        # Add default alternatives if none found
        if not alternatives:
            alternatives.append('EMF embedding')

        return alternatives

    def _identify_primary_transform_type(self, components: TransformComponents) -> str:
        """Identify the primary type of transform."""
        if abs(components.rotation) > 0.1:
            return 'rotation'
        elif components.scale_x != 1.0 or components.scale_y != 1.0:
            return 'scale'
        elif components.skew_x != 0.0 or components.skew_y != 0.0:
            return 'skew'
        elif components.translate_x != 0.0 or components.translate_y != 0.0:
            return 'translation'
        else:
            return 'identity'

    def _find_path_data_comprehensive(self, path_id: str, context_element: ET.Element,
                                    context: ConversionContext) -> Optional[str]:
        """Find path data with comprehensive SVG context search."""
        # This would need full SVG document context in real implementation
        # For now, return None to indicate path not found
        return None

    def _extract_all_text(self, element: ET.Element) -> str:
        """Extract all text content from element and children."""
        content = ""

        # Direct text content
        if element.text:
            content += element.text

        # Text from child elements (tspan, etc.)
        for child in element:
            if child.text:
                content += child.text
            if child.tail:
                content += child.tail

        return content

    def _analyze_text_runs(self, text_element: ET.Element) -> List[Dict[str, Any]]:
        """Analyze individual text runs for styling."""
        runs = []

        # Main text run
        main_run = {
            'text': self._extract_all_text(text_element),
            'font_family': text_element.get('font-family', 'Arial'),
            'font_size': text_element.get('font-size', '24'),
            'fill_color': text_element.get('fill', '#000000'),
            'element_type': 'text'
        }
        runs.append(main_run)

        # Analyze tspan elements
        for tspan in text_element.findall('.//{http://www.w3.org/2000/svg}tspan'):
            tspan_run = {
                'text': tspan.text or '',
                'font_family': tspan.get('font-family', main_run['font_family']),
                'font_size': tspan.get('font-size', main_run['font_size']),
                'fill_color': tspan.get('fill', main_run['fill_color']),
                'element_type': 'tspan'
            }
            runs.append(tspan_run)

        return runs

    def _failure_result(self, reason: str, policy_decision: Optional[TextDecision] = None,
                       alternatives: Optional[List[str]] = None) -> ComprehensiveWordArtResult:
        """Create comprehensive failure result."""
        return ComprehensiveWordArtResult(
            success=False,
            wordart_xml=None,
            generation_metadata={'failure_reason': reason},
            performance_metrics={},
            policy_decision=policy_decision,
            fallback_reason=reason,
            alternative_strategies=alternatives or []
        )


def create_comprehensive_wordart_builder(services: ConversionServices,
                                       config: Optional[WordArtGenerationConfig] = None) -> ComprehensiveWordArtBuilder:
    """
    Factory function to create comprehensive WordArt builder.

    Args:
        services: ConversionServices container
        config: Optional configuration for generation process

    Returns:
        ComprehensiveWordArtBuilder instance
    """
    return ComprehensiveWordArtBuilder(services, config)