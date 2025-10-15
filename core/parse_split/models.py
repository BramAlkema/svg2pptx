"""
Dataclasses shared across the split parser implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..ir.geometry import Rect, SegmentType
from ..transforms.core import Matrix


@dataclass
class ClipDefinition:
    """Resolved clipPath definition used for ClipRef construction."""

    clip_id: str
    segments: tuple[SegmentType, ...]
    bounding_box: Rect | None = None
    clip_rule: str | None = None
    transform: Matrix | None = None


@dataclass
class ParseResult:
    """Result of SVG parsing."""

    success: bool
    svg_root: Any | None = None  # ET.Element is not a type, it's a factory
    error: str | None = None
    processing_time_ms: float = 0.0

    # Parse statistics
    element_count: int = 0
    namespace_count: int = 0
    has_external_references: bool = False

    # Normalization results
    normalization_applied: bool = False
    normalization_changes: dict[str, Any] | None = None
    clip_paths: dict[str, ClipDefinition] | None = None

    def __post_init__(self) -> None:
        if self.normalization_changes is None:
            self.normalization_changes = {}
        if self.clip_paths is None:
            self.clip_paths = {}


__all__ = ["ParseResult", "ClipDefinition"]
