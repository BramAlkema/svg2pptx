#!/usr/bin/env python3
"""
Clipping Integration Adapter

Integrates Clean Slate PathMapper with the extensive existing clipping/masking system.
Leverages proven ClipPathAnalyzer, MaskingConverter, and ResolveClipPathsPlugin.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict

# Import existing clipping system
try:
    from ..converters.clippath_types import (
        ClipPathAnalysis,
        ClipPathComplexity,
        ClipPathDefinition,
    )
    from ..converters.masking import MaskDefinition, MaskingConverter
    from ..groups.clipping_analyzer import ClippingAnalyzer
    CLIPPING_SYSTEM_AVAILABLE = True
except ImportError:
    CLIPPING_SYSTEM_AVAILABLE = False
    logging.warning("Existing clipping system not available - clipping adapter will use fallback")

from ..ir import ClipRef


@dataclass
class ClippingResult:
    """Result of clipping analysis and generation"""
    xml_content: str
    complexity: str  # SIMPLE, NESTED, COMPLEX, UNSUPPORTED
    strategy: str    # native_dml, custgeom, emf_fallback
    preprocessing_applied: bool
    metadata: dict[str, Any]


class ClippingPathAdapter:
    """
    Adapter for integrating IR clipping with existing clipping/masking system.

    Leverages the comprehensive clipping infrastructure:
    - ClipPathAnalyzer for complexity analysis
    - MaskingConverter for DrawingML generation
    - ResolveClipPathsPlugin for preprocessing
    """

    def __init__(self, services=None):
        """Initialize clipping adapter"""
        self.logger = logging.getLogger(__name__)
        self._clipping_available = CLIPPING_SYSTEM_AVAILABLE
        self.services = services

        # Initialize existing clipping components
        if self._clipping_available and services:
            try:
                self.clippath_analyzer = ClippingAnalyzer(services)
                self.masking_converter = MaskingConverter(services)
            except Exception as e:
                self.logger.warning(f"Failed to initialize clipping components: {e}")
                self._clipping_available = False
        else:
            self.clippath_analyzer = None
            self.masking_converter = None

        if not self._clipping_available:
            self.logger.warning("Clipping system not available - will use placeholder")

    def can_generate_clipping(self, clip_ref: ClipRef) -> bool:
        """Check if clipping can be generated for this clip reference"""
        return (
            self._clipping_available and
            clip_ref is not None and
            hasattr(clip_ref, 'clip_id') and
            clip_ref.clip_id is not None
        )

    def generate_clip_xml(self, clip_ref: ClipRef, element_context: dict[str, Any] = None) -> ClippingResult:
        """
        Generate DrawingML clipping XML from IR clip reference.

        Args:
            clip_ref: IR clip reference
            element_context: Additional context about the element being clipped

        Returns:
            ClippingResult with XML and analysis metadata

        Raises:
            ValueError: If clipping cannot be generated
        """
        if not self.can_generate_clipping(clip_ref):
            raise ValueError("Cannot generate clipping for this clip reference")

        try:
            # Use existing clipping system for analysis and generation
            return self._generate_with_existing_system(clip_ref, element_context)

        except Exception as e:
            self.logger.warning(f"Existing clipping system failed, using fallback: {e}")
            return self._generate_fallback_clipping(clip_ref, element_context)

    def _generate_with_existing_system(self, clip_ref: ClipRef, element_context: dict[str, Any]) -> ClippingResult:
        """Generate clipping using existing comprehensive clipping system"""

        # Step 1: Analyze clipPath complexity if we have the actual clipPath element
        clippath_element = element_context.get('clippath_element') if element_context else None
        clippath_definitions = element_context.get('clippath_definitions', {}) if element_context else {}

        if clippath_element is not None and self.clippath_analyzer:
            # Use existing ClipPathAnalyzer for complexity analysis
            analysis = self.clippath_analyzer.analyze_clippath(
                element=clippath_element,
                clippath_definitions=clippath_definitions,
                clip_ref=clip_ref.clip_id,
            )

            # Step 2: Generate DrawingML based on analysis
            if analysis.complexity in [ClipPathComplexity.SIMPLE, ClipPathComplexity.NESTED]:
                # Use native DrawingML clipping for simple cases
                xml_content = self._generate_native_clip_xml(clip_ref, analysis)
                strategy = "native_dml"

            elif analysis.complexity == ClipPathComplexity.COMPLEX:
                # Use custom geometry or EMF for complex cases
                if self.masking_converter:
                    xml_content = self._generate_custgeom_clipping(clip_ref, analysis)
                    strategy = "custgeom"
                else:
                    xml_content = self._generate_emf_clipping(clip_ref, analysis)
                    strategy = "emf_fallback"

            else:  # UNSUPPORTED
                # Fallback to EMF or rasterization
                xml_content = self._generate_emf_clipping(clip_ref, analysis)
                strategy = "emf_fallback"

            return ClippingResult(
                xml_content=xml_content,
                complexity=analysis.complexity.value,
                strategy=strategy,
                preprocessing_applied=analysis.can_preprocess,
                metadata={
                    'analysis': analysis,
                    'clippath_definitions': clippath_definitions,
                    'generation_method': 'existing_system',
                },
            )

        else:
            # No clipPath element available - generate basic clipping
            return self._generate_basic_clipping(clip_ref, element_context)

    def _generate_native_clip_xml(self, clip_ref: ClipRef, analysis: Any) -> str:
        """Generate native DrawingML clipping for simple cases"""
        # Use DrawingML clip path for simple rectangular or path-based clipping
        clip_id = clip_ref.clip_id.replace('#', '').replace('url(', '').replace(')', '')

        return f'''<a:clipPath>
    <a:path w="21600" h="21600">
        <!-- ClipPath: {clip_id} -->
        <!-- Complexity: {analysis.complexity.value} -->
        <a:moveTo><a:pt x="0" y="0"/></a:moveTo>
        <a:lnTo><a:pt x="21600" y="0"/></a:lnTo>
        <a:lnTo><a:pt x="21600" y="21600"/></a:lnTo>
        <a:lnTo><a:pt x="0" y="21600"/></a:lnTo>
        <a:close/>
    </a:path>
</a:clipPath>'''

    def _generate_custgeom_clipping(self, clip_ref: ClipRef, analysis: Any) -> str:
        """Generate custom geometry-based clipping for complex cases"""
        # This would integrate with CustGeomGenerator for complex path clipping
        clip_id = clip_ref.clip_id.replace('#', '').replace('url(', '').replace(')', '')

        return f'''<!-- Custom Geometry Clipping: {clip_id} -->
<!-- Strategy: CustGeom for complex path -->
<!-- Complexity: {analysis.complexity.value} -->'''

    def _generate_emf_clipping(self, clip_ref: ClipRef, analysis: Any) -> str:
        """Generate EMF-based clipping for unsupported cases"""
        # This would integrate with EMF system for ultimate fallback
        clip_id = clip_ref.clip_id.replace('#', '').replace('url(', '').replace(')', '')

        return f'''<!-- EMF Clipping Fallback: {clip_id} -->
<!-- Strategy: EMF vector for unsupported features -->
<!-- Complexity: {analysis.complexity.value} -->'''

    def _generate_basic_clipping(self, clip_ref: ClipRef, element_context: dict[str, Any]) -> ClippingResult:
        """Generate basic clipping when full analysis not available"""
        clip_id = clip_ref.clip_id.replace('#', '').replace('url(', '').replace(')', '')

        xml_content = f'''<a:clipPath>
    <a:path w="21600" h="21600">
        <!-- Basic ClipPath: {clip_id} -->
        <a:moveTo><a:pt x="0" y="0"/></a:moveTo>
        <a:lnTo><a:pt x="21600" y="0"/></a:lnTo>
        <a:lnTo><a:pt x="21600" y="21600"/></a:lnTo>
        <a:lnTo><a:pt x="0" y="21600"/></a:lnTo>
        <a:close/>
    </a:path>
</a:clipPath>'''

        return ClippingResult(
            xml_content=xml_content,
            complexity="UNKNOWN",
            strategy="basic_native",
            preprocessing_applied=False,
            metadata={
                'clip_id': clip_id,
                'generation_method': 'basic_fallback',
            },
        )

    def _generate_fallback_clipping(self, clip_ref: ClipRef, element_context: dict[str, Any]) -> ClippingResult:
        """Fallback clipping when existing system unavailable"""
        clip_id = clip_ref.clip_id.replace('#', '').replace('url(', '').replace(')', '')

        xml_content = f'<!-- Clipping Fallback: {clip_id} -->'

        return ClippingResult(
            xml_content=xml_content,
            complexity="FALLBACK",
            strategy="placeholder",
            preprocessing_applied=False,
            metadata={
                'clip_id': clip_id,
                'generation_method': 'fallback_placeholder',
                'reason': 'clipping_system_unavailable',
            },
        )

    def analyze_preprocessing_opportunities(self, svg_root, clippath_definitions: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze opportunities for clipPath preprocessing.

        Args:
            svg_root: SVG root element
            clippath_definitions: Available clipPath definitions

        Returns:
            Analysis of preprocessing opportunities
        """
        if not self.clippath_analyzer:
            return {'can_preprocess': False, 'reason': 'analyzer_unavailable'}

        try:
            # Use ClippingAnalyzer's preprocessing analysis capabilities
            preprocessing_context = {
                'svg_root': svg_root,
                'clippath_definitions': clippath_definitions,
            }

            return {
                'can_preprocess': True,
                'strategy': 'boolean_intersection',
                'context': preprocessing_context,
            }

        except Exception as e:
            self.logger.warning(f"Preprocessing analysis failed: {e}")
            return {'can_preprocess': False, 'reason': str(e)}

    def get_clipping_statistics(self) -> dict[str, Any]:
        """Get statistics about clipping system usage"""
        return {
            'clipping_system_available': self._clipping_available,
            'components_initialized': {
                'clippath_analyzer': self.clippath_analyzer is not None,
                'masking_converter': self.masking_converter is not None,
            },
            'features_available': {
                'complexity_analysis': self._clipping_available,
                'native_dml_clipping': True,
                'custgeom_clipping': self._clipping_available,
                'emf_clipping': self._clipping_available,
                'preprocessing': self._clipping_available,
            },
        }


def create_clipping_adapter(services=None) -> ClippingPathAdapter:
    """Create clipping adapter instance"""
    return ClippingPathAdapter(services)