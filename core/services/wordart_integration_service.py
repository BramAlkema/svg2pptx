#!/usr/bin/env python3
"""
WordArt Integration Service

Central service that orchestrates all WordArt mapping components:
- Transform decomposition and policy decisions
- Color and gradient mapping
- Path fitting and warp analysis
- Complete DrawingML generation

Provides high-level interface for SVG text to WordArt conversion.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from lxml import etree as ET

from ..services.conversion_services import ConversionServices
from ..converters.base import ConversionContext
from ..services.wordart_transform_service import (
    create_transform_decomposer, TransformComponents
)
from ..services.wordart_color_mapping_service import (
    create_wordart_color_mapping_service
)
from ..converters.wordart_builder import (
    WordArtTransformBuilder, WordArtShapeConfig
)
from core.algorithms.curve_text_positioning import (
    create_path_warp_fitter, WarpFitResult
)
from core.policy.engine import Policy
from core.policy.targets import TextDecision


@dataclass
class WordArtGenerationResult:
    """Result of complete WordArt generation process."""

    success: bool
    wordart_xml: Optional[ET.Element]
    decision_metadata: Dict[str, Any]
    performance_metrics: Dict[str, float]
    fallback_reason: Optional[str] = None


@dataclass
class TextRun:
    """Represents a styled text run within WordArt."""

    text: str
    font_family: str = "Arial"
    font_size: float = 24.0
    fill_color: str = "#000000"
    stroke_color: Optional[str] = None
    stroke_width: float = 0.0
    opacity: float = 1.0


class WordArtIntegrationService:
    """
    Central orchestrator for WordArt generation.

    Integrates all mapping services to provide complete SVG text
    to PowerPoint WordArt conversion with fallback strategies.
    """

    def __init__(self, services: ConversionServices):
        """
        Initialize integration service with all dependencies.

        Args:
            services: ConversionServices container
        """
        self.services = services

        # Initialize component services
        self.transform_decomposer = create_transform_decomposer()
        self.color_service = create_wordart_color_mapping_service(services)
        self.wordart_builder = WordArtTransformBuilder()
        self.warp_fitter = create_path_warp_fitter()

        # Policy engine for decision making
        self.policy = Policy()

    def generate_wordart(self, text_element: ET.Element,
                        context: ConversionContext) -> WordArtGenerationResult:
        """
        Generate complete WordArt from SVG text element.

        Args:
            text_element: SVG text element
            context: Conversion context

        Returns:
            WordArtGenerationResult with XML and metadata
        """
        import time
        start_time = time.time()

        try:
            # Parse text content and styling
            text_runs = self._parse_text_runs(text_element)
            if not text_runs:
                return self._failure_result("No text content found")

            # Analyze transforms and paths
            transform_analysis = self._analyze_transforms(text_element)
            path_analysis = self._analyze_text_paths(text_element)

            # Make policy decision
            decision = self._make_policy_decision(
                text_element, transform_analysis, path_analysis
            )

            if not decision.use_native:
                return self._failure_result(
                    f"Policy decision: {', '.join(decision.reasons)}"
                )

            # Generate WordArt shape
            wordart_config = self._build_wordart_config(
                text_runs, transform_analysis, path_analysis
            )

            wordart_xml = self._generate_wordart_xml(
                wordart_config, text_element, context
            )

            # Calculate performance metrics
            generation_time = (time.time() - start_time) * 1000  # ms

            return WordArtGenerationResult(
                success=True,
                wordart_xml=wordart_xml,
                decision_metadata={
                    'policy_decision': decision.__dict__,
                    'transform_analysis': transform_analysis,
                    'path_analysis': path_analysis.__dict__ if path_analysis else None
                },
                performance_metrics={
                    'generation_time_ms': generation_time,
                    'text_run_count': len(text_runs)
                }
            )

        except Exception as e:
            return self._failure_result(f"Generation failed: {e}")

    def _parse_text_runs(self, text_element: ET.Element) -> List[TextRun]:
        """Parse text content into styled runs."""
        runs = []

        # Get text content
        text_content = self._extract_text_content(text_element)
        if not text_content.strip():
            return runs

        # Extract styling
        font_family = text_element.get('font-family', 'Arial')
        font_size = float(text_element.get('font-size', '24'))
        fill_color = text_element.get('fill', '#000000')
        stroke_color = text_element.get('stroke')
        stroke_width = float(text_element.get('stroke-width', '0'))

        # Parse opacity
        opacity = 1.0
        opacity_attr = text_element.get('opacity')
        if opacity_attr:
            opacity = float(opacity_attr)

        # Create single run (can be extended for tspan support)
        runs.append(TextRun(
            text=text_content,
            font_family=font_family,
            font_size=font_size,
            fill_color=fill_color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            opacity=opacity
        ))

        return runs

    def _extract_text_content(self, element: ET.Element) -> str:
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

    def _analyze_transforms(self, text_element: ET.Element) -> Optional[Dict[str, Any]]:
        """Analyze element transforms for complexity."""
        transform_attr = text_element.get('transform')
        if not transform_attr:
            return None

        try:
            # Decompose transform
            components = self.transform_decomposer.decompose_transform_string(transform_attr)

            # Analyze complexity
            complexity_analysis = self.transform_decomposer.analyze_transform_complexity(components)

            return {
                'transform_string': transform_attr,
                'components': components.__dict__,
                'complexity': complexity_analysis
            }

        except Exception as e:
            return {'error': str(e), 'transform_string': transform_attr}

    def _analyze_text_paths(self, text_element: ET.Element) -> Optional[WarpFitResult]:
        """Analyze text paths for warp fitting."""
        # Check for textPath element
        textpath = text_element.find('.//{http://www.w3.org/2000/svg}textPath')
        if textpath is None:
            return None

        # Get path reference
        href = textpath.get('{http://www.w3.org/1999/xlink}href') or textpath.get('href')
        if not href or not href.startswith('#'):
            return None

        # Find path definition (simplified - would need full SVG context)
        path_data = self._find_path_data(href[1:], text_element)
        if not path_data:
            return None

        try:
            # Fit path to warp families
            warp_result = self.warp_fitter.fit_path_to_warp(path_data, min_confidence=0.6)
            return warp_result

        except Exception as e:
            return None

    def _find_path_data(self, path_id: str, context_element: ET.Element) -> Optional[str]:
        """Find path data by ID (simplified implementation)."""
        # This would need full SVG document context in real implementation
        # For now, return None to indicate path not found
        return None

    def _make_policy_decision(self, text_element: ET.Element,
                            transform_analysis: Optional[Dict],
                            path_analysis: Optional[WarpFitResult]) -> TextDecision:
        """Make policy decision using existing policy engine."""

        # Create mock text frame for policy analysis
        # In real implementation, this would be a proper TextFrame IR object
        mock_text_frame = type('MockTextFrame', (), {
            'transform': text_element.get('transform'),
            'complexity_score': 5,  # Default
            'runs': [type('MockRun', (), {'has_decoration': False})()],
            'is_multiline': False
        })()

        # If we have transform analysis, include complexity
        if transform_analysis and 'complexity' in transform_analysis:
            mock_text_frame.complexity_score = transform_analysis['complexity'].get('complexity_score', 5)

        return self.policy.decide_text(mock_text_frame)

    def _build_wordart_config(self, text_runs: List[TextRun],
                             transform_analysis: Optional[Dict],
                             path_analysis: Optional[WarpFitResult]) -> WordArtShapeConfig:
        """Build WordArt configuration from analysis results."""

        # Use first text run for primary styling
        primary_run = text_runs[0]

        # Build basic config
        config = WordArtShapeConfig(
            text=primary_run.text,
            font_family=primary_run.font_family,
            font_size=primary_run.font_size,
            fill_color=primary_run.fill_color,
            stroke_color=primary_run.stroke_color,
            stroke_width=primary_run.stroke_width,
            width=len(primary_run.text) * primary_run.font_size * 0.6,  # Estimate
            height=primary_run.font_size * 1.2  # Estimate
        )

        # Add transform if available
        if transform_analysis and 'transform_string' in transform_analysis:
            config.transform = transform_analysis['transform_string']

        # Add WordArt preset from path analysis
        if path_analysis and path_analysis.confidence > 0.6:
            config.wordart_preset = path_analysis.preset_type
            config.wordart_parameters = path_analysis.parameters

        return config

    def _generate_wordart_xml(self, config: WordArtShapeConfig,
                             text_element: ET.Element,
                             context: ConversionContext) -> ET.Element:
        """Generate final WordArt XML."""

        # Generate base WordArt shape
        wordart_shape = self.wordart_builder.build_wordart_shape(config)

        # Apply additional styling if needed
        self._apply_advanced_styling(wordart_shape, text_element, context)

        return wordart_shape

    def _apply_advanced_styling(self, wordart_shape: ET.Element,
                               text_element: ET.Element,
                               context: ConversionContext) -> None:
        """Apply advanced styling using color service."""

        # Check for gradient fills
        fill_attr = text_element.get('fill', '')
        if fill_attr.startswith('url(#'):
            # Try to map gradient fill
            svg_root = context.svg_root
            defs = svg_root.find('.//{http://www.w3.org/2000/svg}defs')

            if defs is not None:
                gradient_fill = self.color_service.map_fill_reference(
                    fill_attr, defs, context
                )

                if gradient_fill is not None:
                    # Replace solid fill with gradient
                    self._replace_shape_fill(wordart_shape, gradient_fill)

    def _replace_shape_fill(self, shape: ET.Element, new_fill: ET.Element) -> None:
        """Replace shape's fill with new fill element."""
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
        p_ns = "{http://schemas.openxmlformats.org/presentationml/2006/main}"

        # Find shape properties
        sppr = shape.find(f"{p_ns}spPr")
        if sppr is not None:
            # Remove existing solid fill
            solid_fill = sppr.find(f"{a_ns}solidFill")
            if solid_fill is not None:
                sppr.remove(solid_fill)

            # Add new fill
            sppr.append(new_fill)

    def _failure_result(self, reason: str) -> WordArtGenerationResult:
        """Create failure result with reason."""
        return WordArtGenerationResult(
            success=False,
            wordart_xml=None,
            decision_metadata={'failure_reason': reason},
            performance_metrics={},
            fallback_reason=reason
        )


def create_wordart_integration_service(services: ConversionServices) -> WordArtIntegrationService:
    """
    Factory function to create WordArt integration service.

    Args:
        services: ConversionServices container

    Returns:
        WordArtIntegrationService instance
    """
    return WordArtIntegrationService(services)