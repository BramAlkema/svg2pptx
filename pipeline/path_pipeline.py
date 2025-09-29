#!/usr/bin/env python3
"""
Path Pipeline MVP

Demonstrates the complete clean architecture pipeline for SVG path conversion:
1. SVG preprocessing (normalize transforms, expand paths)
2. IR conversion (using legacy path adapter)
3. Policy decisions (native DrawingML vs EMF fallback)
4. PPTX generation (using legacy I/O adapter)

This MVP proves the architecture works end-to-end while preserving
battle-tested components via adapters.
"""

import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from lxml import etree as ET

# Import core architecture components
from core.ir import Path as IRPath, Point, LineSegment, BezierSegment
from core.policy import PolicyEngine, PolicyConfig, PathDecision
from adapters.legacy_paths import LegacyPathAdapter
from adapters.legacy_io import LegacyIOAdapter


@dataclass
class ConversionResult:
    """Result of end-to-end path conversion."""
    success: bool
    ir_elements: List[IRPath]
    policy_decisions: List[PathDecision]
    pptx_bytes: Optional[bytes]
    metrics: Dict[str, Any]
    duration_sec: float
    error_message: Optional[str] = None

    @property
    def element_count(self) -> int:
        """Number of IR elements created."""
        return len(self.ir_elements)

    @property
    def native_count(self) -> int:
        """Number of elements using native DrawingML."""
        return sum(1 for d in self.policy_decisions if d.use_native)

    @property
    def emf_count(self) -> int:
        """Number of elements using EMF fallback."""
        return sum(1 for d in self.policy_decisions if not d.use_native)


@dataclass
class PipelineContext:
    """Context for pipeline execution."""
    slide_width: int = 9144000   # 10" in EMU
    slide_height: int = 6858000  # 7.5" in EMU
    policy_config: Optional[PolicyConfig] = None
    debug_mode: bool = False

    def __post_init__(self):
        if self.policy_config is None:
            # Default to balanced policy
            self.policy_config = PolicyConfig.balanced()


class PathPipeline:
    """
    End-to-end path conversion pipeline.

    Demonstrates the clean architecture by converting SVG paths through
    the complete pipeline while reusing proven legacy components.
    """

    def __init__(self, context: PipelineContext = None):
        """
        Initialize path pipeline.

        Args:
            context: Pipeline configuration
        """
        self.context = context or PipelineContext()
        self.logger = logging.getLogger(__name__)

        # Initialize architecture components
        self.policy_engine = PolicyEngine(self.context.policy_config)
        self.path_adapter = LegacyPathAdapter()
        self.io_adapter = LegacyIOAdapter()

    def convert_svg_to_pptx(self, svg_content: str) -> ConversionResult:
        """
        Convert SVG content to PPTX using clean architecture pipeline.

        Args:
            svg_content: SVG XML content

        Returns:
            Conversion result with metrics
        """
        start_time = time.perf_counter()

        try:
            self.logger.info("Starting path pipeline conversion")

            # Phase 1: Preprocessing
            self.logger.debug("Phase 1: SVG preprocessing")
            preprocessed_svg = self._preprocess_svg(svg_content)

            # Phase 2: IR Conversion
            self.logger.debug("Phase 2: Converting to IR")
            ir_elements = self._convert_to_ir(preprocessed_svg)

            if not ir_elements:
                return ConversionResult(
                    success=False,
                    ir_elements=[],
                    policy_decisions=[],
                    pptx_bytes=None,
                    metrics={},
                    duration_sec=time.perf_counter() - start_time,
                    error_message="No path elements found in SVG"
                )

            # Phase 3: Policy Decisions
            self.logger.debug("Phase 3: Making policy decisions")
            policy_decisions = self._make_policy_decisions(ir_elements)

            # Phase 4: PPTX Generation
            self.logger.debug("Phase 4: Generating PPTX")
            pptx_bytes = self._generate_pptx(ir_elements, policy_decisions)

            # Calculate metrics
            duration = time.perf_counter() - start_time
            metrics = self._calculate_metrics(ir_elements, policy_decisions, duration)

            self.logger.info(f"Pipeline completed successfully in {duration:.3f}s")

            return ConversionResult(
                success=True,
                ir_elements=ir_elements,
                policy_decisions=policy_decisions,
                pptx_bytes=pptx_bytes,
                metrics=metrics,
                duration_sec=duration
            )

        except Exception as e:
            duration = time.perf_counter() - start_time
            self.logger.error(f"Pipeline failed: {e}")

            return ConversionResult(
                success=False,
                ir_elements=[],
                policy_decisions=[],
                pptx_bytes=None,
                metrics={},
                duration_sec=duration,
                error_message=str(e)
            )

    def _preprocess_svg(self, svg_content: str) -> ET.Element:
        """
        Preprocess SVG for optimal conversion.

        Phase 1: SVG preprocessing
        - Parse and validate SVG
        - Normalize transforms
        - Expand path data
        - Basic cleanup
        """
        try:
            # Parse SVG
            root = ET.fromstring(svg_content.encode())

            # Ensure SVG namespace
            if not root.tag.endswith('svg'):
                # Wrap in SVG if needed
                wrapper = ET.Element('{http://www.w3.org/2000/svg}svg')
                wrapper.set('width', '100')
                wrapper.set('height', '100')
                wrapper.append(root)
                root = wrapper

            # Normalize coordinate system
            self._normalize_svg_coordinates(root)

            # Simplify transforms (basic implementation)
            self._simplify_transforms(root)

            return root

        except ET.XMLSyntaxError as e:
            raise ValueError(f"Invalid SVG content: {e}")

    def _normalize_svg_coordinates(self, svg_root: ET.Element) -> None:
        """Normalize SVG coordinate system."""
        # Ensure we have width/height
        if not svg_root.get('width'):
            svg_root.set('width', '100')
        if not svg_root.get('height'):
            svg_root.set('height', '100')

        # Add viewBox if missing (simplified)
        if not svg_root.get('viewBox'):
            width = svg_root.get('width', '100').rstrip('px')
            height = svg_root.get('height', '100').rstrip('px')
            svg_root.set('viewBox', f'0 0 {width} {height}')

    def _simplify_transforms(self, element: ET.Element) -> None:
        """Simplify transform attributes (basic implementation)."""
        # Remove identity transforms
        transform = element.get('transform')
        if transform:
            # Very basic: remove "translate(0,0)" and "scale(1,1)"
            if transform.strip() in ('translate(0,0)', 'scale(1,1)', 'rotate(0)'):
                del element.attrib['transform']

        # Recursively process children
        for child in element:
            self._simplify_transforms(child)

    def _convert_to_ir(self, svg_root: ET.Element) -> List[IRPath]:
        """
        Convert SVG paths to IR elements.

        Phase 2: IR Conversion using legacy path adapter
        """
        ir_elements = []

        # Find all path elements
        for path_elem in svg_root.xpath('.//svg:path', namespaces={'svg': 'http://www.w3.org/2000/svg'}):
            try:
                # Use legacy adapter to convert path
                ir_path = self.path_adapter.convert_svg_path_to_ir(path_elem)
                ir_elements.append(ir_path)

                if self.context.debug_mode:
                    self.logger.debug(f"Converted path: {len(ir_path.segments)} segments")

            except Exception as e:
                self.logger.warning(f"Failed to convert path element: {e}")

        # Also handle basic shapes that can be converted to paths
        for shape_elem in svg_root.xpath('.//svg:rect | .//svg:circle | .//svg:ellipse',
                                       namespaces={'svg': 'http://www.w3.org/2000/svg'}):
            try:
                ir_path = self._convert_shape_to_path_ir(shape_elem)
                if ir_path:
                    ir_elements.append(ir_path)

            except Exception as e:
                self.logger.warning(f"Failed to convert shape element: {e}")

        return ir_elements

    def _convert_shape_to_path_ir(self, shape_elem: ET.Element) -> Optional[IRPath]:
        """Convert basic shapes to path IR (simplified implementation)."""
        tag = shape_elem.tag.split('}')[-1] if '}' in shape_elem.tag else shape_elem.tag

        if tag == 'rect':
            return self._rect_to_path_ir(shape_elem)
        elif tag == 'circle':
            return self._circle_to_path_ir(shape_elem)
        elif tag == 'ellipse':
            return self._ellipse_to_path_ir(shape_elem)

        return None

    def _rect_to_path_ir(self, rect_elem: ET.Element) -> IRPath:
        """Convert rect to path IR."""
        x = float(rect_elem.get('x', '0'))
        y = float(rect_elem.get('y', '0'))
        width = float(rect_elem.get('width', '0'))
        height = float(rect_elem.get('height', '0'))

        # Create rectangle path
        segments = [
            LineSegment(Point(x, y), Point(x + width, y)),
            LineSegment(Point(x + width, y), Point(x + width, y + height)),
            LineSegment(Point(x + width, y + height), Point(x, y + height)),
            LineSegment(Point(x, y + height), Point(x, y))
        ]

        return IRPath(
            segments=segments,
            fill=self._extract_fill(rect_elem),
            stroke=self._extract_stroke(rect_elem),
            opacity=float(rect_elem.get('opacity', '1.0'))
        )

    def _circle_to_path_ir(self, circle_elem: ET.Element) -> IRPath:
        """Convert circle to path IR using Bezier approximation."""
        cx = float(circle_elem.get('cx', '0'))
        cy = float(circle_elem.get('cy', '0'))
        r = float(circle_elem.get('r', '0'))

        # Approximate circle with 4 Bezier curves
        # Magic number for circle approximation: 0.552
        k = r * 0.552

        segments = [
            # Top to right
            BezierSegment(
                Point(cx, cy - r),
                Point(cx + k, cy - r),
                Point(cx + r, cy - k),
                Point(cx + r, cy)
            ),
            # Right to bottom
            BezierSegment(
                Point(cx + r, cy),
                Point(cx + r, cy + k),
                Point(cx + k, cy + r),
                Point(cx, cy + r)
            ),
            # Bottom to left
            BezierSegment(
                Point(cx, cy + r),
                Point(cx - k, cy + r),
                Point(cx - r, cy + k),
                Point(cx - r, cy)
            ),
            # Left to top
            BezierSegment(
                Point(cx - r, cy),
                Point(cx - r, cy - k),
                Point(cx - k, cy - r),
                Point(cx, cy - r)
            )
        ]

        return IRPath(
            segments=segments,
            fill=self._extract_fill(circle_elem),
            stroke=self._extract_stroke(circle_elem),
            opacity=float(circle_elem.get('opacity', '1.0'))
        )

    def _ellipse_to_path_ir(self, ellipse_elem: ET.Element) -> IRPath:
        """Convert ellipse to path IR (simplified to circle)."""
        # For MVP, treat ellipse as circle using average radius
        cx = float(ellipse_elem.get('cx', '0'))
        cy = float(ellipse_elem.get('cy', '0'))
        rx = float(ellipse_elem.get('rx', '0'))
        ry = float(ellipse_elem.get('ry', '0'))

        # Use average radius for simplification
        r = (rx + ry) / 2

        # Create temporary circle element
        circle_elem = ET.Element('circle')
        circle_elem.set('cx', str(cx))
        circle_elem.set('cy', str(cy))
        circle_elem.set('r', str(r))

        # Copy attributes
        for attr, value in ellipse_elem.attrib.items():
            if attr not in ('cx', 'cy', 'rx', 'ry'):
                circle_elem.set(attr, value)

        return self._circle_to_path_ir(circle_elem)

    def _extract_fill(self, element: ET.Element):
        """Extract fill styling (simplified)."""
        from core.ir import SolidPaint

        fill = element.get('fill', 'black')
        if fill == 'none':
            return None

        # Simple color parsing
        if fill.startswith('#'):
            rgb = fill[1:].upper()
            return SolidPaint(rgb) if len(rgb) == 6 else SolidPaint("000000")

        # Named colors
        color_map = {
            'black': '000000', 'white': 'FFFFFF', 'red': 'FF0000',
            'green': '008000', 'blue': '0000FF', 'yellow': 'FFFF00'
        }
        rgb = color_map.get(fill.lower(), '000000')
        return SolidPaint(rgb)

    def _extract_stroke(self, element: ET.Element):
        """Extract stroke styling (simplified)."""
        from core.ir import Stroke, SolidPaint, StrokeJoin, StrokeCap

        stroke = element.get('stroke')
        if not stroke or stroke == 'none':
            return None

        width = float(element.get('stroke-width', '1'))

        # Simple stroke color
        if stroke.startswith('#'):
            rgb = stroke[1:].upper()
            stroke_paint = SolidPaint(rgb) if len(rgb) == 6 else SolidPaint("000000")
        else:
            stroke_paint = SolidPaint("000000")

        return Stroke(
            paint=stroke_paint,
            width=width,
            join=StrokeJoin.MITER,
            cap=StrokeCap.BUTT
        )

    def _make_policy_decisions(self, ir_elements: List[IRPath]) -> List[PathDecision]:
        """
        Make policy decisions for each IR element.

        Phase 3: Policy decisions using policy engine
        """
        decisions = []

        for ir_path in ir_elements:
            try:
                decision = self.policy_engine.decide_path(ir_path)
                decisions.append(decision)

                if self.context.debug_mode:
                    self.logger.debug(f"Path decision: {'native' if decision.use_native else 'EMF'} "
                                    f"({len(decision.reasons)} reasons)")

            except Exception as e:
                self.logger.warning(f"Policy decision failed, using EMF fallback: {e}")
                decisions.append(PathDecision.emf(reasons=[f"Policy error: {e}"]))

        return decisions

    def _generate_pptx(self, ir_elements: List[IRPath],
                      decisions: List[PathDecision]) -> bytes:
        """
        Generate PPTX from IR elements and decisions.

        Phase 4: PPTX generation using legacy I/O adapter
        """
        try:
            # Create presentation context
            slide_dims = (self.context.slide_width, self.context.slide_height)

            with self.io_adapter.create_presentation_from_ir(ir_elements, slide_dims) as presentation:
                return presentation.to_bytes()

        except Exception as e:
            self.logger.error(f"PPTX generation failed: {e}")
            raise

    def _calculate_metrics(self, ir_elements: List[IRPath],
                          decisions: List[PathDecision],
                          duration: float) -> Dict[str, Any]:
        """Calculate conversion metrics."""
        total_segments = sum(len(path.segments) for path in ir_elements)
        native_count = sum(1 for d in decisions if d.use_native)
        emf_count = len(decisions) - native_count

        return {
            'total_elements': len(ir_elements),
            'total_segments': total_segments,
            'native_elements': native_count,
            'emf_elements': emf_count,
            'native_ratio': native_count / max(len(decisions), 1),
            'avg_segments_per_element': total_segments / max(len(ir_elements), 1),
            'conversion_speed_elements_per_sec': len(ir_elements) / max(duration, 0.001),
            'pipeline_duration_sec': duration
        }