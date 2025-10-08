#!/usr/bin/env python3
"""
Structured clipping intermediate representations.

These dataclasses describe clip paths, custGeom payloads, and EMF fallbacks
in a mapper-agnostic way. They can be translated back to the legacy XML-based
ClippingResult until all consumers migrate to the richer IR.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


class ClipFallback(Enum):
    """Fallback strategy selected for a clipping operation."""

    NONE = "none"          # Emit native <a:clipPath>/<a:custGeom>
    EMF_SHAPE = "emf_shape"  # Replace clipped shape with <p:pic> EMF
    EMF_GROUP = "emf_group"  # Render an entire group as EMF


@dataclass
class ClipMediaMeta:
    """Metadata describing a generated media asset for clipping."""

    content_type: str
    rel_id: Optional[str]
    part_name: Optional[str]
    bbox_emu: Tuple[int, int, int, int]  # x, y, width, height in EMU
    data: Optional[bytes] = None
    description: Optional[str] = None


@dataclass
class ClipCustGeom:
    """Custom geometry definition for native clipping."""

    path: List["ClipPathSegment"] = field(default_factory=list)
    path_xml: Optional[str] = None
    fill_rule_even_odd: bool = False


@dataclass
class ClipPathSegment:
    """Normalized path segment command."""

    cmd: str
    args: List[float] = field(default_factory=list)


@dataclass
class ClipComputeResult:
    """Structured result produced by the new clipping service."""

    strategy: ClipFallback
    custgeom: Optional[ClipCustGeom] = None
    media: Optional[ClipMediaMeta] = None
    used_bbox_rect: bool = False
