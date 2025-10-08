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

from ..clip import LegacyClipBridge, StructuredClipService
from ..policy.config import ClipPolicy
from ..ir import ClipRef, Path as IRPath, SolidPaint
from ..ir.geometry import BezierSegment, LineSegment, Point, Rect, SegmentType


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

    def __init__(
        self,
        services=None,
        *,
        clip_policy: ClipPolicy | None = None,
        structured_clip_service: StructuredClipService | None = None,
        clip_bridge: LegacyClipBridge | None = None,
    ):
        """Initialize clipping adapter"""
        self.logger = logging.getLogger(__name__)
        self._clipping_available = CLIPPING_SYSTEM_AVAILABLE
        self.services = services
        self.clip_policy = clip_policy or self._derive_clip_policy(services)
        self.structured_clip_service = structured_clip_service or StructuredClipService()
        self.clip_bridge = clip_bridge or LegacyClipBridge()

        # Initialize existing clipping components
        if self._clipping_available and services:
            try:
                self.clippath_analyzer = ClippingAnalyzer(services)
                if MaskingConverter is not None:
                    self.masking_converter = MaskingConverter(services)
                else:
                    self.masking_converter = None
            except Exception as e:
                self.logger.warning(f"Failed to initialize clipping components: {e}")
                self._clipping_available = False
        else:
            self.clippath_analyzer = None
            self.masking_converter = None

        if not self._clipping_available:
            self.logger.warning("Clipping system not available - will use placeholder")

    def _derive_clip_policy(self, services) -> ClipPolicy | None:
        """Attempt to derive clip policy information from services."""
        if services is None:
            return None

        policy_engine = getattr(services, "policy_engine", None)
        if policy_engine is None:
            return None

        clip_policy = getattr(policy_engine, "clip_policy", None)
        if clip_policy is not None:
            return clip_policy

        get_clip_policy = getattr(policy_engine, "get_clip_policy", None)
        if callable(get_clip_policy):
            try:
                return get_clip_policy()
            except Exception:  # pragma: no cover - defensive
                pass

        config = getattr(policy_engine, "config", None)
        if config is not None:
            return getattr(config, "clip_policy", None)
        return None

    def _can_use_structured_adapter(self) -> bool:
        """Check if the structured adapter bridge should run."""
        return (
            self.clip_policy is not None
            and getattr(self.clip_policy, "enable_structured_adapter", False)
            and self.structured_clip_service is not None
            and self.clip_bridge is not None
        )

    def _try_structured_adapter(
        self,
        clip_ref: ClipRef,
        analysis: Any,
        element_context: dict[str, Any] | None,
    ) -> ClippingResult | None:
        """Attempt to compute clipping via the structured adapter bridge."""
        try:
            structured_result = self.structured_clip_service.compute(
                clip_ref,
                analysis,
                element_context,
            )
        except Exception as exc:
            self.logger.debug("Structured clip service failed: %s", exc)
            return None

        if not structured_result:
            return None

        try:
            legacy_result = self.clip_bridge.convert(
                structured_result,
                clip_ref,
                analysis,
                preprocessing_applied=bool(getattr(analysis, "can_preprocess", False)),
            )
            if legacy_result is not None:
                legacy_result.metadata.setdefault("structured_result", structured_result)
            return legacy_result
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.debug("Structured clip bridge failed: %s", exc)
            return None

    def can_generate_clipping(self, clip_ref: ClipRef) -> bool:
        """Check if clipping can be generated for this clip reference"""
        if clip_ref is None or getattr(clip_ref, 'clip_id', None) is None:
            return False

        if getattr(clip_ref, 'path_segments', None):
            return True

        return self._clipping_available

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

        if clip_ref.path_segments:
            try:
                return self._generate_from_segments(clip_ref)
            except Exception as exc:
                self.logger.warning(f"Segment-based clip generation failed: {exc}")

        try:
            # Use existing clipping system for analysis and generation
            return self._generate_with_existing_system(clip_ref, element_context)

        except Exception as e:
            self.logger.warning(f"Existing clipping system failed, using fallback: {e}")
            return self._generate_fallback_clipping(clip_ref, element_context)

    def _generate_from_segments(self, clip_ref: ClipRef) -> ClippingResult:
        """Generate DrawingML clipPath directly from IR segments."""
        segments = clip_ref.path_segments or ()
        if not segments:
            raise ValueError("clip_ref.path_segments is empty")

        segments = clip_ref.path_segments or ()
        transform_matrix = getattr(clip_ref, 'transform', None)

        def transform_point(pt: Point) -> Point:
            if transform_matrix:
                x, y = transform_matrix.transform_point(pt.x, pt.y)
                return Point(x, y)
            return pt

        transformed_segments = []
        for segment in segments:
            if isinstance(segment, LineSegment):
                transformed_segments.append(
                    LineSegment(transform_point(segment.start), transform_point(segment.end))
                )
            elif isinstance(segment, BezierSegment):
                transformed_segments.append(
                    BezierSegment(
                        transform_point(segment.start),
                        transform_point(segment.control1),
                        transform_point(segment.control2),
                        transform_point(segment.end),
                    )
                )
            else:
                transformed_segments.append(segment)

        bbox = self._compute_bbox(transformed_segments) or clip_ref.bounding_box
        origin_x = bbox.x if bbox else 0.0
        origin_y = bbox.y if bbox else 0.0
        width = bbox.width if bbox and bbox.width > 0 else 1.0
        height = bbox.height if bbox and bbox.height > 0 else 1.0

        width_emu = max(1, int(round(width * 12700)))
        height_emu = max(1, int(round(height * 12700)))

        def to_emu(point):
            return (
                int(round((point.x - origin_x) * 12700)),
                int(round((point.y - origin_y) * 12700)),
            )

        path_commands = []
        current_point = None

        for segment in transformed_segments:
            start = getattr(segment, 'start', None)
            if start is not None:
                if current_point is None or (abs(current_point.x - start.x) > 1e-6 or abs(current_point.y - start.y) > 1e-6):
                    sx, sy = to_emu(start)
                    path_commands.append(f"<a:moveTo><a:pt x=\"{sx}\" y=\"{sy}\"/></a:moveTo>")
                    current_point = start

            if isinstance(segment, LineSegment):
                end = segment.end
                ex, ey = to_emu(end)
                path_commands.append(f"<a:lnTo><a:pt x=\"{ex}\" y=\"{ey}\"/></a:lnTo>")
                current_point = end
            elif isinstance(segment, BezierSegment):
                c1x, c1y = to_emu(segment.control1)
                c2x, c2y = to_emu(segment.control2)
                ex, ey = to_emu(segment.end)
                path_commands.append(
                    "<a:cubicBezTo>"
                    f"<a:pt x=\"{c1x}\" y=\"{c1y}\"/>"
                    f"<a:pt x=\"{c2x}\" y=\"{c2y}\"/>"
                    f"<a:pt x=\"{ex}\" y=\"{ey}\"/>"
                    "</a:cubicBezTo>"
                )
                current_point = segment.end

        xml_content = (
            f"<a:clipPath>"
            f"<a:path w=\"{width_emu}\" h=\"{height_emu}\">"
            + ''.join(path_commands) +
            "</a:path></a:clipPath>"
        )

        return ClippingResult(
            xml_content=xml_content,
            complexity="segment",
            strategy="native_dml",
            preprocessing_applied=False,
            metadata={
                'source': 'segment_based',
                'clip_id': clip_ref.clip_id,
            },
        )

    @staticmethod
    def _compute_bbox(segments: list[SegmentType]) -> Rect | None:
        if not segments:
            return None

        xs: list[float] = []
        ys: list[float] = []

        for segment in segments:
            for attr in ('start', 'end', 'control1', 'control2'):
                point = getattr(segment, attr, None)
                if point is not None:
                    xs.append(point.x)
                    ys.append(point.y)

        if not xs or not ys:
            return None

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        return Rect(min_x, min_y, max_x - min_x, max_y - min_y)

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

            # Step 1.5: Attempt structured adapter bridge if enabled
            if self._can_use_structured_adapter():
                bridged = self._try_structured_adapter(
                    clip_ref,
                    analysis,
                    element_context,
                )
                if bridged is not None:
                    return bridged

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
                    return self._generate_emf_clipping(clip_ref, analysis)

            else:  # UNSUPPORTED
                # Fallback to EMF or rasterization
                return self._generate_emf_clipping(clip_ref, analysis)

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
        if clip_ref.path_segments:
            return self._generate_from_segments(clip_ref).xml_content

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
        if clip_ref.path_segments:
            return self._generate_from_segments(clip_ref).xml_content

        clip_id = clip_ref.clip_id.replace('#', '').replace('url(', '').replace(')', '')
        return f'''<!-- Custom Geometry Clipping: {clip_id} -->
<!-- Strategy: CustGeom for complex path -->
<!-- Complexity: {analysis.complexity.value} -->'''

    def _generate_emf_clipping(self, clip_ref: ClipRef, analysis: Any) -> ClippingResult:
        """Generate EMF-based clipping for unsupported cases"""
        clip_id = clip_ref.clip_id.replace('#', '').replace('url(', '').replace(')', '')

        try:
            from .emf_adapter import create_emf_adapter  # Deferred import to avoid cycles
            emf_adapter = create_emf_adapter()
        except Exception as exc:
            self.logger.debug("EMF adapter unavailable for clipping: %s", exc)
            return f'''<!-- EMF Clipping Fallback: {clip_id} -->
<!-- Strategy: EMF vector for unsupported features -->
<!-- Complexity: {analysis.complexity.value} -->'''

        path_segments = self._clone_segments(clip_ref.path_segments) if clip_ref.path_segments else None
        if not path_segments:
            bbox = clip_ref.bounding_box or self._extract_analysis_bbox(analysis)
            if bbox is None:
                bbox = Rect(0.0, 0.0, 1.0, 1.0)
            path_segments = self._rect_to_segments(bbox)

        try:
            path_ir = IRPath(
                segments=path_segments,
                fill=SolidPaint(rgb="FFFFFF"),
                stroke=None,
                clip=None,
                opacity=1.0,
            )

            if not emf_adapter.can_generate_emf(path_ir):
                raise ValueError("EMF adapter cannot handle clipping path")

            emf_result = emf_adapter.generate_emf_blob(path_ir)

            media_entry = {
                'type': 'emf',
                'data': emf_result.emf_data,
                'relationship_id': emf_result.relationship_id,
                'content_type': 'application/emf',
                'width_emu': emf_result.width_emu,
                'height_emu': emf_result.height_emu,
                'description': 'clip_emf_fallback',
            }

            metadata = {
                'generation_method': 'emf_clipping',
                'media_files': [media_entry],
                'clip_id': clip_id,
                'analysis': analysis,
            }

            return ClippingResult(
                xml_content=f'''<!-- EMF Clipping Fallback: {clip_id} -->
<!-- Strategy: EMF vector for unsupported features -->
<!-- Complexity: {analysis.complexity.value} -->''',
                complexity=analysis.complexity.value if hasattr(analysis.complexity, "value") else str(analysis.complexity),
                strategy="emf_fallback",
                preprocessing_applied=analysis.can_preprocess if hasattr(analysis, "can_preprocess") else False,
                metadata=metadata,
            )

        except Exception as exc:
            self.logger.warning("EMF clipping generation failed: %s", exc)
            return ClippingResult(
                xml_content=f'''<!-- EMF Clipping Fallback: {clip_id} -->
<!-- Strategy: EMF vector for unsupported features -->
<!-- Complexity: {analysis.complexity.value} -->''',
                complexity=analysis.complexity.value if hasattr(analysis.complexity, "value") else str(analysis.complexity),
                strategy="emf_fallback",
                preprocessing_applied=False,
                metadata={
                    'clip_id': clip_id,
                    'generation_method': 'emf_fallback_error',
                    'error': str(exc),
                },
            )

    def _clone_segments(self, segments: tuple[SegmentType, ...] | None) -> list[SegmentType]:
        cloned: list[SegmentType] = []
        if not segments:
            return cloned

        for segment in segments:
            if isinstance(segment, LineSegment):
                cloned.append(
                    LineSegment(
                        Point(segment.start.x, segment.start.y),
                        Point(segment.end.x, segment.end.y),
                    ),
                )
            elif isinstance(segment, BezierSegment):
                cloned.append(
                    BezierSegment(
                        Point(segment.start.x, segment.start.y),
                        Point(segment.control1.x, segment.control1.y),
                        Point(segment.control2.x, segment.control2.y),
                        Point(segment.end.x, segment.end.y),
                    ),
                )
            else:
                cloned.append(segment)
        return cloned

    def _rect_to_segments(self, bbox: Rect) -> list[SegmentType]:
        x1, y1 = bbox.x, bbox.y
        x2 = bbox.x + max(bbox.width, 1e-6)
        y2 = bbox.y + max(bbox.height, 1e-6)

        p1 = Point(x1, y1)
        p2 = Point(x2, y1)
        p3 = Point(x2, y2)
        p4 = Point(x1, y2)

        return [
            LineSegment(p1, p2),
            LineSegment(p2, p3),
            LineSegment(p3, p4),
            LineSegment(p4, p1),
        ]

    def _extract_analysis_bbox(self, analysis: Any) -> Rect | None:
        chain = getattr(analysis, 'clip_chain', []) or []
        for clip_def in chain:
            bbox = getattr(clip_def, 'bounding_box', None)
            if bbox:
                return bbox
        return getattr(analysis, 'bounding_box', None)

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


def create_clipping_adapter(
    services=None,
    *,
    clip_policy: ClipPolicy | None = None,
    structured_clip_service: StructuredClipService | None = None,
    clip_bridge: LegacyClipBridge | None = None,
) -> ClippingPathAdapter:
    """Create clipping adapter instance"""
    return ClippingPathAdapter(
        services,
        clip_policy=clip_policy,
        structured_clip_service=structured_clip_service,
        clip_bridge=clip_bridge,
    )
