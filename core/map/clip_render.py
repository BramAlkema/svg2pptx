#!/usr/bin/env python3
"""Utilities for translating ClipComputeResult into mapper-friendly outputs."""

from __future__ import annotations

from typing import Any, List, Optional

from core.clip import ClipComputeResult
from core.ir import ClipRef


def clip_result_to_xml(
    result: ClipComputeResult | None,
    clip_ref: ClipRef | None = None,
) -> tuple[str, Optional[dict[str, Any]], Optional[List[dict[str, Any]]]]:
    """
    Translate a ClipComputeResult into XML, metadata, and optional media files.

    Returns:
        Tuple of (xml_string, metadata_dict | None, media_files | None)
    """
    clip_id = getattr(clip_ref, "clip_id", None)

    if result is None:
        placeholder = f"<!-- Clip unavailable: {clip_id or 'unknown'} -->"
        return placeholder, {"strategy": "unavailable", "clip_id": clip_id}, None

    metadata: dict[str, Any] = dict(result.metadata or {})
    if "strategy" not in metadata:
        metadata["strategy"] = result.strategy.value
    metadata.setdefault("clip_id", clip_id)
    metadata.setdefault("clip_strategy", metadata["strategy"])
    metadata["used_bbox_rect"] = bool(result.used_bbox_rect)

    if "media_files" in metadata and metadata["media_files"] is None:
        metadata.pop("media_files")

    xml_snippet: str
    if result.custgeom and result.custgeom.path_xml:
        xml_snippet = result.custgeom.path_xml
    else:
        placeholder = metadata.get("xml_placeholder")
        if not placeholder:
            placeholder = f"<!-- Clip placeholder: {clip_id or 'unknown'} -->"
        xml_snippet = str(placeholder)

    media_files: Optional[List[dict[str, Any]]] = None
    if result.media:
        media = result.media
        media_dict: dict[str, Any] = {
            "type": _infer_media_type(media.content_type),
            "content_type": media.content_type,
            "relationship_id": media.rel_id,
            "part_name": media.part_name,
            "data": media.data,
            "bbox_emu": media.bbox_emu,
            "width_emu": media.bbox_emu[2],
            "height_emu": media.bbox_emu[3],
            "description": media.description,
            "clip_strategy": result.strategy.value,
        }
        media_files = [media_dict]
        metadata["media_meta"] = media
        metadata["media_files"] = media_files

    result.metadata = metadata
    return xml_snippet, metadata, media_files


def _infer_media_type(content_type: Optional[str]) -> str:
    if not content_type:
        return "media"
    content_lower = content_type.lower()
    if "emf" in content_lower:
        return "emf"
    if "image" in content_lower:
        return "image"
    return "media"
