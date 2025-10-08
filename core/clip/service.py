#!/usr/bin/env python3
"""Structured clipping service implementation."""

from __future__ import annotations

import logging
from typing import Any, Optional

from core.ir.geometry import Rect
from core.units.core import ConversionContext

try:
    from core.converters.custgeom_generator import CustGeomGenerator, CustGeomGenerationError
except ImportError:  # pragma: no cover - optional dependency missing at runtime
    CustGeomGenerator = None  # type: ignore
    CustGeomGenerationError = Exception  # type: ignore

from .model import ClipComputeResult, ClipCustGeom, ClipFallback

EMU_PER_UNIT = 12700

logger = logging.getLogger(__name__)


class StructuredClipService:
    """Generate structured clipping results for supported clip paths."""

    def __init__(
        self,
        services=None,
        custgeom_generator: CustGeomGenerator | None = None,
    ) -> None:
        self.services = services
        if custgeom_generator is not None:
            self.custgeom_generator = custgeom_generator
        elif CustGeomGenerator is not None:
            self.custgeom_generator = CustGeomGenerator(services)
        else:  # pragma: no cover
            self.custgeom_generator = None

    def compute(
        self,
        clip_ref: Any,
        analysis: Any,
        element_context: dict[str, Any] | None = None,
    ) -> ClipComputeResult | None:
        """Attempt to build a structured clipping result."""

        if analysis is None:
            return None

        complexity = getattr(analysis, "complexity", None)
        complexity_value = getattr(complexity, "value", str(complexity).lower() if complexity else None)
        if complexity_value not in {"simple", "nested"}:
            return None

        if getattr(analysis, "requires_emf", False):
            return None

        clip_defs = getattr(analysis, "clip_chain", []) or []
        bbox = self._extract_bounds(clip_ref, element_context)

        custgeom_xml: Optional[str] = None
        used_bbox = False

        if self.custgeom_generator and clip_defs:
            conversion_context = self._build_conversion_context(bbox, element_context)

            for clip_def in clip_defs:
                try:
                    if not self.custgeom_generator.can_generate_custgeom(clip_def):
                        continue
                    custgeom_xml = self.custgeom_generator.generate_custgeom_xml(clip_def, conversion_context)
                    break
                except CustGeomGenerationError as exc:
                    logger.debug("CustGeom generation failed for %s: %s", getattr(clip_def, "id", "clip"), exc)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.debug("Unexpected custGeom error: %s", exc)

        if custgeom_xml is None:
            if bbox is None:
                return None
            custgeom_xml = self._rect_to_custgeom_xml(bbox)
            used_bbox = True

        custgeom = ClipCustGeom(
            path_xml=custgeom_xml,
            fill_rule_even_odd=self._is_even_odd(clip_ref, analysis),
            path=[],
        )

        return ClipComputeResult(
            strategy=ClipFallback.NONE,
            custgeom=custgeom,
            media=None,
            used_bbox_rect=used_bbox,
        )

    def _extract_bounds(self, clip_ref: Any, element_context: Optional[dict[str, Any]]) -> Optional[Rect]:
        bbox = getattr(clip_ref, "bounding_box", None)
        if bbox is None and element_context:
            ctx_bbox = element_context.get("bounding_box")
            if isinstance(ctx_bbox, Rect):
                bbox = ctx_bbox
        return bbox

    def _build_conversion_context(
        self,
        bbox: Optional[Rect],
        element_context: Optional[dict[str, Any]],
    ) -> ConversionContext:
        if element_context:
            ctx = element_context.get("conversion_context")
            if isinstance(ctx, ConversionContext):
                return ctx

        width = getattr(bbox, "width", None) or 1.0
        height = getattr(bbox, "height", None) or 1.0

        dpi = 96.0
        unit_converter = getattr(self.services, "unit_converter", None)
        if unit_converter is not None:
            default_ctx = getattr(unit_converter, "default_context", None)
            if default_ctx is not None:
                dpi = getattr(default_ctx, "dpi", dpi)

        return ConversionContext(width=width, height=height, dpi=dpi)

    def _rect_to_custgeom_xml(self, bbox: Rect) -> str:
        x = int(round(bbox.x * EMU_PER_UNIT))
        y = int(round(bbox.y * EMU_PER_UNIT))
        w = max(1, int(round(bbox.width * EMU_PER_UNIT)))
        h = max(1, int(round(bbox.height * EMU_PER_UNIT)))

        x2 = x + w
        y2 = y + h

        return (
            "<a:custGeom>"
            "<a:pathLst>"
            "<a:path w=\"0\" h=\"0\" fill=\"none\">"
            f"<a:moveTo><a:pt x=\"{x}\" y=\"{y}\"/></a:moveTo>"
            f"<a:lnTo><a:pt x=\"{x2}\" y=\"{y}\"/></a:lnTo>"
            f"<a:lnTo><a:pt x=\"{x2}\" y=\"{y2}\"/></a:lnTo>"
            f"<a:lnTo><a:pt x=\"{x}\" y=\"{y2}\"/></a:lnTo>"
            "<a:close/>"
            "</a:path>"
            "</a:pathLst>"
            "</a:custGeom>"
        )

    def _is_even_odd(self, clip_ref: Any, analysis: Any) -> bool:
        rule = getattr(clip_ref, "clip_rule", None)
        if rule:
            return str(rule).lower() == "evenodd"

        clip_chain = getattr(analysis, "clip_chain", []) or []
        for clip_def in clip_chain:
            clip_rule = getattr(clip_def, "clip_rule", None)
            if clip_rule:
                return str(clip_rule).lower() == "evenodd"
        return False
