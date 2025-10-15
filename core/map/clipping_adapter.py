#!/usr/bin/env python3
"""
Clipping Integration Adapter

This adapter now returns structured ClipComputeResult payloads that describe the
native custGeom clip or any media fallback. Legacy XML translation is handled
by the consumers (mappers) so we can phase out the LegacyClipBridge.
"""

from __future__ import annotations

import logging
import os
from types import SimpleNamespace
from typing import Any, Iterable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.services.conversion_services import ConversionServices, EmuValue

logger = logging.getLogger(__name__)

try:
    from ..groups.clipping_analyzer import ClippingAnalyzer, ClippingComplexity, ClippingStrategy
    CLIPPING_SYSTEM_AVAILABLE = True
except ImportError:
    CLIPPING_SYSTEM_AVAILABLE = False
    logger.warning(
        "Existing clipping system not available - clipping adapter will operate in fallback mode",
    )

from lxml import etree as ET

from ..clip import (
    ClipComputeResult,
    ClipCustGeom,
    ClipFallback,
    ClipMediaMeta,
    StructuredClipService,
)
from ..policy.config import ClipPolicy
from ..ir import ClipRef, Path as IRPath, SolidPaint
from ..ir.geometry import BezierSegment, LineSegment, Point, Rect, SegmentType
from ..utils.xml_builder import get_xml_builder


def _env_enabled(flag: str) -> bool:
    value = os.getenv(flag)
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


class ClippingPathAdapter:
    """
    Adapter for integrating IR clip references with the existing analyzer while
    emitting the new ClipComputeResult structure.
    """

    def __init__(
        self,
        services: 'ConversionServices',
        *,
        clip_policy: ClipPolicy | None = None,
        structured_clip_service: StructuredClipService | None = None,
    ):
        self.logger = logging.getLogger(__name__)
        self.services = services
        if self.services is None:
            raise RuntimeError("ClippingPathAdapter requires ConversionServices injection.")
        self.clip_policy = clip_policy or self._derive_clip_policy(services)
        self.structured_clip_service = structured_clip_service or StructuredClipService(services)
        self._xml_builder = get_xml_builder()

        self._clipping_available = CLIPPING_SYSTEM_AVAILABLE
        if self._clipping_available and services:
            try:
                self.clippath_analyzer = ClippingAnalyzer(services)
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.warning("Failed to initialize ClipPathAnalyzer: %s", exc)
                self.clippath_analyzer = None
                self._clipping_available = False
        else:
            self.clippath_analyzer = None

        if not self._clipping_available:
            self.logger.debug("Clipping analyzer unavailable - structural fallbacks only")

    # --------------------------------------------------------------------- #
    # Public API                                                            #
    # --------------------------------------------------------------------- #

    def can_generate_clipping(self, clip_ref: ClipRef) -> bool:
        if clip_ref is None or getattr(clip_ref, "clip_id", None) is None:
            return False
        if getattr(clip_ref, "path_segments", None):
            return True
        return self._clipping_available

    def generate_clip_xml(  # noqa: D401 - legacy method name retained for callers
        self,
        clip_ref: ClipRef,
        element_context: Optional[dict[str, Any]] = None,
    ) -> ClipComputeResult:
        """Compute a ClipComputeResult for the supplied clip reference."""
        self._emu_trace: list[dict[str, Any]] = []
        if not self.can_generate_clipping(clip_ref):
            raise ValueError("Cannot generate clipping for this clip reference")

        element_context = element_context or {}

        if clip_ref.path_segments:
            return self._generate_from_segments(clip_ref)

        analysis = self._analyze_clip_path(clip_ref, element_context)

        if analysis and self._structured_adapter_enabled():
            structured = self._try_structured_adapter(clip_ref, analysis, element_context)
            if structured is not None:
                return self._with_emu_trace(structured)

        if analysis is not None:
            return self._generate_with_existing_system(clip_ref, analysis, element_context)

        if clip_ref.bounding_box is not None:
            return self._generate_basic_clipping(clip_ref, element_context)

        return self._generate_fallback_clipping(clip_ref)

    def analyze_preprocessing_opportunities(
        self,
        svg_root,
        clippath_definitions: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.clippath_analyzer:
            return {"can_preprocess": False, "reason": "analyzer_unavailable"}

        try:
            preprocessing_context = {
                "svg_root": svg_root,
                "clippath_definitions": clippath_definitions,
            }
            return {
                "can_preprocess": True,
                "strategy": "boolean_intersection",
                "context": preprocessing_context,
            }
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.warning("Preprocessing analysis failed: %s", exc)
            return {"can_preprocess": False, "reason": str(exc)}

    def get_clipping_statistics(self) -> dict[str, Any]:
        return {
            "clipping_system_available": self._clipping_available,
            "structured_enabled": self._structured_adapter_enabled(),
            "components_initialized": {
                "clippath_analyzer": self.clippath_analyzer is not None,
            },
        }

    # --------------------------------------------------------------------- #
    # Internal helpers                                                      #
    # --------------------------------------------------------------------- #

    def _derive_clip_policy(self, services) -> ClipPolicy | None:
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
                return None

        config = getattr(policy_engine, "config", None)
        if config is not None:
            return getattr(config, "clip_policy", None)
        return None

    def _structured_adapter_enabled(self) -> bool:
        if _env_enabled("SVG2PPTX_CLIP_ADAPTER_V2"):
            return True
        if self.clip_policy is None:
            return False
        return getattr(self.clip_policy, "enable_structured_adapter", False)

    def _analyze_clip_path(
        self,
        clip_ref: ClipRef,
        element_context: dict[str, Any],
    ) -> Any | None:
        if not self._clipping_available or not self.clippath_analyzer:
            return None

        context_payload: dict[str, Any] = dict(element_context or {})
        clip_definitions = context_payload.get("clippath_definitions", {})
        context_payload.setdefault("clippath_definitions", clip_definitions)

        svg_root = context_payload.get("svg_root")
        if svg_root is None:
            clippath_element = context_payload.get("clippath_element")
            if hasattr(clippath_element, "getroottree"):
                try:
                    svg_root = clippath_element.getroottree().getroot()
                except Exception:  # pragma: no cover - defensive
                    svg_root = None
            context_payload["svg_root"] = svg_root

        if context_payload.get("svg_root") is None and not clip_definitions:
            # Not enough context to resolve the clip definition
            return None

        normalized_ref = self._normalize_clip_reference(clip_ref.clip_id)
        proxy_element = ET.Element("proxy")
        proxy_element.set("clip-path", normalized_ref)

        analysis_context = SimpleNamespace(**context_payload)

        try:
            return self.clippath_analyzer.analyze_clipping_scenario(
                proxy_element,
                analysis_context,
            )
        except AttributeError:  # pragma: no cover - compatibility fallback
            # Older analyzer versions may not expose analyze_clipping_scenario.
            return None
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.debug("ClipPath analysis failed: %s", exc)
            return None

    def _try_structured_adapter(
        self,
        clip_ref: ClipRef,
        analysis: Any,
        element_context: dict[str, Any],
    ) -> ClipComputeResult | None:
        if not self.structured_clip_service:
            return None

        try:
            structured_result = self.structured_clip_service.compute(
                clip_ref,
                analysis,
                element_context,
            )
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.debug("Structured clip service failed: %s", exc)
            return None

        if structured_result is None:
            return None

        metadata = dict(structured_result.metadata or {})
        metadata.setdefault("generation_method", "structured_service")
        metadata.setdefault("analysis", analysis)
        metadata.setdefault("complexity", self._complexity_value(getattr(analysis, "complexity", None)))
        structured_result.metadata = metadata
        return self._with_emu_trace(structured_result)

    def _generate_from_segments(self, clip_ref: ClipRef) -> ClipComputeResult:
        segments = list(clip_ref.path_segments or ())
        if not segments:
            raise ValueError("clip_ref.path_segments is empty")

        transformed = self._transform_segments(segments, getattr(clip_ref, "transform", None))
        bbox = clip_ref.bounding_box or self._compute_bbox(transformed) or Rect(0.0, 0.0, 1.0, 1.0)

        clip_xml = self._segments_to_clip_xml(transformed, bbox)
        custgeom = ClipCustGeom(
            path=[],
            path_xml=clip_xml,
            fill_rule_even_odd=self._is_even_odd(clip_ref, None),
        )

        metadata = {
            "generation_method": "segments",
            "clip_id": clip_ref.clip_id,
            "complexity": "segments",
        }

        return self._with_emu_trace(ClipComputeResult(
            strategy=ClipFallback.NONE,
            custgeom=custgeom,
            media=None,
            used_bbox_rect=False,
            metadata=metadata,
        ))

    def _generate_with_existing_system(
        self,
        clip_ref: ClipRef,
        analysis: Any,
        element_context: dict[str, Any],
    ) -> ClipComputeResult:
        complexity_value = self._complexity_value(getattr(analysis, "complexity", None))
        preprocessing_applied = getattr(analysis, "requires_preprocessing", None)
        if preprocessing_applied is None:
            preprocessing_applied = getattr(analysis, "can_preprocess", False)
        metadata = {
            "generation_method": "existing_system",
            "analysis": analysis,
            "complexity": complexity_value,
            "preprocessing_applied": preprocessing_applied,
        }

        recommended = getattr(analysis, "recommended_strategy", None)
        if recommended == ClippingStrategy.EMF_VECTOR:
            return self._generate_emf_clipping(clip_ref, analysis, metadata)

        if recommended == ClippingStrategy.RASTERIZATION:
            # Fallback to basic clipping when rasterization is recommended.
            return self._generate_basic_clipping(clip_ref, element_context)

        if recommended in (ClippingStrategy.POWERPOINT_NATIVE, ClippingStrategy.CUSTGEOM):
            return self._generate_custgeom_clipping(clip_ref, analysis, element_context, metadata)

        # Legacy fallback based on complexity if no explicit recommendation provided.
        if complexity_value in {"simple", "moderate"}:
            return self._generate_custgeom_clipping(clip_ref, analysis, element_context, metadata)

        if complexity_value == "complex":
            return self._generate_emf_clipping(clip_ref, analysis, metadata)

        return self._generate_basic_clipping(clip_ref, element_context)

    def _generate_custgeom_clipping(
        self,
        clip_ref: ClipRef,
        analysis: Any,
        element_context: dict[str, Any],
        base_metadata: dict[str, Any],
    ) -> ClipComputeResult:
        metadata = dict(base_metadata)

        structured_result: ClipComputeResult | None = None
        if self.structured_clip_service:
            try:
                structured_result = self.structured_clip_service.compute(
                    clip_ref,
                    analysis,
                    element_context,
                )
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.debug("CustGeom structured service failed: %s", exc)
                structured_result = None

        if structured_result and structured_result.custgeom and structured_result.custgeom.path_xml:
            structured_metadata = dict(structured_result.metadata or {})
            metadata["generation_method"] = structured_metadata.get("generation_method", "custgeom_generator")
            metadata.update(structured_metadata)
            metadata.setdefault("structured_strategy", structured_metadata.get("strategy"))
            metadata.setdefault("structured_kind", "custgeom")
            metadata.setdefault("structured_used_bbox", structured_result.used_bbox_rect)
            metadata.setdefault("strategy", structured_metadata.get("strategy", ClipFallback.NONE.value))
            structured_result.metadata = metadata
            return self._with_emu_trace(structured_result)

        custgeom = self._build_custgeom_from_analysis(clip_ref, analysis, element_context)
        metadata["generation_method"] = "custgeom_bbox"
        metadata.setdefault("strategy", ClipFallback.NONE.value)
        metadata.setdefault("structured_kind", "custgeom")
        metadata.setdefault("structured_used_bbox", True)

        return self._with_emu_trace(ClipComputeResult(
            strategy=ClipFallback.NONE,
            custgeom=custgeom,
            media=None,
            used_bbox_rect=True,
            metadata=metadata,
        ))

    def _build_custgeom_from_analysis(
        self,
        clip_ref: ClipRef,
        analysis: Any,
        element_context: dict[str, Any],
    ) -> ClipCustGeom:
        bbox = clip_ref.bounding_box or self._extract_analysis_bbox(analysis)
        if bbox is None:
            bbox = element_context.get("bounding_box")
        if not isinstance(bbox, Rect):
            bbox = Rect(0.0, 0.0, 1.0, 1.0)

        clip_xml = self._rect_clip_xml(bbox)
        return ClipCustGeom(
            path=[],
            path_xml=clip_xml,
            fill_rule_even_odd=self._is_even_odd(clip_ref, analysis),
        )

    def _generate_emf_clipping(
        self,
        clip_ref: ClipRef,
        analysis: Any,
        base_metadata: dict[str, Any],
    ) -> ClipComputeResult:
        clip_id = self._clean_clip_id(clip_ref.clip_id)
        metadata = dict(base_metadata)
        metadata["strategy"] = "emf_fallback"
        metadata["clip_strategy"] = ClipFallback.EMF_SHAPE.value

        try:
            from .emf_adapter import create_emf_adapter  # Deferred to avoid circular import

            emf_adapter = create_emf_adapter(self.services)
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.debug("EMF adapter unavailable for clipping: %s", exc)
            metadata["xml_placeholder"] = f"<!-- EMF Clipping Fallback: {clip_id} -->"
            metadata["error"] = str(exc)
            return self._with_emu_trace(ClipComputeResult(
                strategy=ClipFallback.EMF_SHAPE,
                custgeom=None,
                media=None,
                used_bbox_rect=False,
                metadata=metadata,
            ))

        path_segments = self._clone_segments(getattr(clip_ref, "path_segments", None))
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

            media = ClipMediaMeta(
                content_type="application/emf",
                rel_id=getattr(emf_result, "relationship_id", None),
                part_name=None,
                bbox_emu=(0, 0, getattr(emf_result, "width_emu", 0), getattr(emf_result, "height_emu", 0)),
                data=getattr(emf_result, "emf_data", None),
                description="clip_emf_fallback",
            )

            metadata["media_meta"] = media
            metadata["media_files"] = [
                {
                    "type": "emf",
                    "data": media.data,
                    "relationship_id": media.rel_id,
                    "content_type": media.content_type,
                    "width_emu": media.bbox_emu[2],
                    "height_emu": media.bbox_emu[3],
                    "clip_strategy": ClipFallback.EMF_SHAPE.value,
                },
            ]
            metadata["xml_placeholder"] = f"<!-- EMF Clipping Fallback: {clip_id} -->"
            metadata["emf_pic_xml"] = self._build_emf_pic_xml(media)
            metadata["tracer_strategy"] = "emf_fallback"

            return self._with_emu_trace(ClipComputeResult(
                strategy=ClipFallback.EMF_SHAPE,
                custgeom=None,
                media=media,
                used_bbox_rect=False,
                metadata=metadata,
            ))

        except Exception as exc:
            self.logger.warning("EMF clipping generation failed: %s", exc)
            metadata["error"] = str(exc)
            metadata["xml_placeholder"] = f"<!-- EMF Clipping Error: {clip_id} -->"
            metadata.setdefault("tracer_strategy", "emf_fallback")
            return self._with_emu_trace(ClipComputeResult(
                strategy=ClipFallback.EMF_SHAPE,
                custgeom=None,
                media=None,
                used_bbox_rect=False,
                metadata=metadata,
            ))

    def _generate_basic_clipping(
        self,
        clip_ref: ClipRef,
        element_context: dict[str, Any],
    ) -> ClipComputeResult:
        bbox = clip_ref.bounding_box or element_context.get("clip_bounding_box")
        if not isinstance(bbox, Rect):
            bbox = Rect(0.0, 0.0, 1.0, 1.0)

        clip_xml = self._rect_clip_xml(bbox)
        metadata = {
            "generation_method": "basic_fallback",
            "clip_id": clip_ref.clip_id,
        }

        custgeom = ClipCustGeom(
            path=[],
            path_xml=clip_xml,
            fill_rule_even_odd=self._is_even_odd(clip_ref, None),
        )

        return self._with_emu_trace(ClipComputeResult(
            strategy=ClipFallback.NONE,
            custgeom=custgeom,
            media=None,
            used_bbox_rect=True,
            metadata=metadata,
        ))

    def _generate_fallback_clipping(self, clip_ref: ClipRef) -> ClipComputeResult:
        clip_id = self._clean_clip_id(clip_ref.clip_id)
        placeholder = f"<!-- Clipping Fallback: {clip_id} -->"

        bbox = getattr(clip_ref, "bounding_box", None)
        if bbox is None:
            parsed = self._parse_bbox_clip_id(clip_ref.clip_id)
            if parsed is not None:
                bbox = parsed

        if bbox is None:
            # Produce a minimal clipPath so downstream consumers still receive valid DrawingML.
            bbox = Rect(0, 0, 1, 1)
            used_bbox = False
        else:
            used_bbox = True

        clip_xml = self._rect_clip_xml(bbox)
        metadata = {
            "generation_method": "fallback_placeholder",
            "clip_id": clip_ref.clip_id,
            "xml_placeholder": placeholder,
        }
        if used_bbox:
            metadata["strategy"] = "bbox"
        custgeom = ClipCustGeom(path=[], path_xml=clip_xml, fill_rule_even_odd=False)
        return self._with_emu_trace(ClipComputeResult(
            strategy=ClipFallback.NONE,
            custgeom=custgeom,
            media=None,
            used_bbox_rect=used_bbox,
            metadata=metadata,
        ))

    @staticmethod
    def _build_emf_pic_xml(media: ClipMediaMeta) -> str:
        rel_id = media.rel_id or ""
        width_emu = media.bbox_emu[2] if media.bbox_emu else 0
        height_emu = media.bbox_emu[3] if media.bbox_emu else 0
        description = media.description or "clip_emf_fallback"

        return (
            "<p:pic>"
            "<p:nvPicPr>"
            f'<p:cNvPr id="1" name="{description}"/>'
            "<p:cNvPicPr/>"
            "<p:nvPr/>"
            "</p:nvPicPr>"
            "<p:blipFill>"
            f'<a:blip r:embed="{rel_id}">'
            "<a:extLst>"
            '<a:ext uri="{A7D7AC89-857B-4B46-9C2E-2B86D7B4E2B4}">'
            '<emf:emfBlip xmlns:emf="http://schemas.microsoft.com/office/drawing/2010/emf"/>'
            "</a:ext>"
            "</a:extLst>"
            "</a:blip>"
            "<a:stretch><a:fillRect/></a:stretch>"
            "</p:blipFill>"
            "<p:spPr>"
            "<a:xfrm>"
            f'<a:off x="0" y="0"/>'
            f'<a:ext cx="{width_emu}" cy="{height_emu}"/>'
            "</a:xfrm>"
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            "</p:spPr>"
            "</p:pic>"
        )

    @staticmethod
    def _parse_bbox_clip_id(clip_id: str | None) -> Rect | None:
        if not clip_id or not clip_id.startswith("bbox:"):
            return None
        parts = clip_id.split(":")
        if len(parts) < 5:
            return None
        try:
            _, x_str, y_str, width_str, height_str = parts[:5]
            x = float(x_str)
            y = float(y_str)
            width = max(float(width_str), 0.0)
            height = max(float(height_str), 0.0)
        except ValueError:
            return None
        return Rect(x, y, width, height)

    # ------------------------------------------------------------------ #
    # Geometry helpers                                                   #
    # ------------------------------------------------------------------ #

    def _transform_segments(
        self,
        segments: Iterable[SegmentType],
        transform_matrix: Any | None,
    ) -> list[SegmentType]:
        if not transform_matrix:
            return list(segments)

        transformed: list[SegmentType] = []
        for segment in segments:
            if isinstance(segment, LineSegment):
                transformed.append(
                    LineSegment(
                        self._transform_point(segment.start, transform_matrix),
                        self._transform_point(segment.end, transform_matrix),
                    ),
                )
            elif isinstance(segment, BezierSegment):
                transformed.append(
                    BezierSegment(
                        self._transform_point(segment.start, transform_matrix),
                        self._transform_point(segment.control1, transform_matrix),
                        self._transform_point(segment.control2, transform_matrix),
                        self._transform_point(segment.end, transform_matrix),
                    ),
                )
            else:
                transformed.append(segment)
        return transformed

    def _transform_point(self, point: Point, matrix: Any) -> Point:
        x, y = matrix.transform_point(point.x, point.y)
        return Point(x, y)

    def _segments_to_clip_xml(self, segments: list[SegmentType], bbox: Rect) -> str:
        origin_x = bbox.x
        origin_y = bbox.y
        width = bbox.width or 1.0
        height = bbox.height or 1.0

        width_emu = self._emu_value(width, axis="x", label="clip_bbox_width")
        height_emu = self._emu_value(height, axis="y", label="clip_bbox_height")
        width_emu_value = max(1, width_emu.value)
        height_emu_value = max(1, height_emu.value)

        def to_emu(point: Point) -> tuple[int, int]:
            return (
                self._emu_value(point.x - origin_x, axis="x", label="clip_point_x").value,
                self._emu_value(point.y - origin_y, axis="y", label="clip_point_y").value,
            )

        command_specs: list[tuple[str, list[tuple[int, int]]]] = []
        current_point: Point | None = None

        for segment in segments:
            start = getattr(segment, "start", None)
            if start is not None:
                if current_point is None or not self._points_equal(current_point, start):
                    sx, sy = to_emu(start)
                    command_specs.append(("moveTo", [(sx, sy)]))
                    current_point = start

            if isinstance(segment, LineSegment):
                end = segment.end
                ex, ey = to_emu(end)
                command_specs.append(("lnTo", [(ex, ey)]))
                current_point = end
            elif isinstance(segment, BezierSegment):
                c1x, c1y = to_emu(segment.control1)
                c2x, c2y = to_emu(segment.control2)
                ex, ey = to_emu(segment.end)
                command_specs.append((
                    "cubicBezTo",
                    [(c1x, c1y), (c2x, c2y), (ex, ey)],
                ))
                current_point = segment.end

        return self._xml_builder.create_clip_path_xml(
            width_emu_value,
            height_emu_value,
            command_specs,
            close=bool(command_specs),
        )

    @staticmethod
    def _points_equal(p1: Point, p2: Point, tolerance: float = 1e-6) -> bool:
        return abs(p1.x - p2.x) <= tolerance and abs(p1.y - p2.y) <= tolerance

    @staticmethod
    def _compute_bbox(segments: list[SegmentType]) -> Rect | None:
        xs: list[float] = []
        ys: list[float] = []

        for segment in segments:
            for attr in ("start", "end", "control1", "control2"):
                point = getattr(segment, attr, None)
                if point is not None:
                    xs.append(point.x)
                    ys.append(point.y)

        if not xs or not ys:
            return None

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        return Rect(min_x, min_y, max_x - min_x, max_y - min_y)

    def _rect_clip_xml(self, bbox: Rect) -> str:
        width_emu = self._emu_value(bbox.width, axis="x", label="rect_clip_width")
        height_emu = self._emu_value(bbox.height, axis="y", label="rect_clip_height")
        width_emu_value = max(1, width_emu.value)
        height_emu_value = max(1, height_emu.value)

        commands = [
            ("moveTo", [(0, 0)]),
            ("lnTo", [(width_emu_value, 0)]),
            ("lnTo", [(width_emu_value, height_emu_value)]),
            ("lnTo", [(0, height_emu_value)]),
        ]

        return self._xml_builder.create_clip_path_xml(
            width_emu_value,
            height_emu_value,
            commands,
        )

    @staticmethod
    def _clone_segments(segments: Iterable[SegmentType] | None) -> list[SegmentType]:
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

    @staticmethod
    def _rect_to_segments(bbox: Rect) -> list[SegmentType]:
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

    @staticmethod
    def _extract_analysis_bbox(analysis: Any) -> Rect | None:
        if analysis is None:
            return None
        chain = getattr(analysis, "clip_chain", []) or []
        for clip_def in chain:
            bbox = getattr(clip_def, "bounding_box", None)
            if bbox:
                return bbox
        return getattr(analysis, "bounding_box", None)

    @staticmethod
    def _is_even_odd(clip_ref: ClipRef, analysis: Any | None) -> bool:
        rule = getattr(clip_ref, "clip_rule", None)
        if rule:
            return str(rule).lower() == "evenodd"

        if analysis is not None:
            clip_chain = getattr(analysis, "clip_chain", []) or []
            for clip_def in clip_chain:
                clip_rule = getattr(clip_def, "clip_rule", None)
                if clip_rule and str(clip_rule).lower() == "evenodd":
                    return True
        return False

    @staticmethod
    def _complexity_value(complexity: Any | None) -> str | None:
        if complexity is None:
            return None
        value = getattr(complexity, "value", None)
        if value is not None:
            return value
        return str(complexity).lower()

    @staticmethod
    def _clean_clip_id(clip_id: str | None) -> str:
        if not clip_id:
            return "clip"
        cleaned = clip_id.strip()
        if cleaned.startswith("url(") and cleaned.endswith(")"):
            cleaned = cleaned[4:-1]
        if cleaned.startswith("#"):
            cleaned = cleaned[1:]
        return cleaned or "clip"

    @staticmethod
    def _normalize_clip_reference(clip_id: str | None) -> str:
        if not clip_id:
            return ""
        clip_id = clip_id.strip()
        if clip_id.startswith("url("):
            return clip_id
        if clip_id.startswith("#"):
            return f"url({clip_id})"
        return f"url(#{clip_id})"

    def _record_emu_value(self, axis: str, label: str | None, emu_value: 'EmuValue') -> None:
        trace = getattr(self, "_emu_trace", None)
        if trace is None:
            trace = []
            self._emu_trace = trace
        trace.append({
            "axis": axis,
            "label": label or axis,
            "emu": emu_value,
        })

    def _with_emu_trace(self, result: ClipComputeResult) -> ClipComputeResult:
        trace = getattr(self, "_emu_trace", None)
        if trace:
            metadata = dict(result.metadata or {})
            metadata.setdefault("emu_trace", []).extend(trace)
            result.metadata = metadata
        return result

    def _emu_value(
        self,
        value: float | int,
        axis: str = "uniform",
        *,
        label: str | None = None,
    ) -> 'EmuValue':
        if not hasattr(self.services, "emu"):
            raise RuntimeError("ClippingPathAdapter requires ConversionServices.emu().")
        emu_val = self.services.emu(value, axis=axis)
        self._record_emu_value(axis=axis, label=label, emu_value=emu_val)
        return emu_val


def create_clipping_adapter(
    services: 'ConversionServices',
    *,
    clip_policy: ClipPolicy | None = None,
    structured_clip_service: StructuredClipService | None = None,
) -> ClippingPathAdapter:
    """Factory helper for callers."""
    if services is None:
        raise RuntimeError("create_clipping_adapter requires ConversionServices instance.")
    return ClippingPathAdapter(
        services,
        clip_policy=clip_policy,
        structured_clip_service=structured_clip_service,
    )
