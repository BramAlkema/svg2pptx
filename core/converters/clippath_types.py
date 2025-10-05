#!/usr/bin/env python3
"""
ClipPath data types and structures.

This module contains shared data types for clipPath analysis and conversion
to avoid circular imports between analyzer and converter modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from lxml import etree as ET


class ClipPathComplexity(Enum):
    """Classification of clipPath complexity for conversion strategy."""
    SIMPLE = "simple"          # Single basic shape or path → custGeom
    NESTED = "nested"          # Multiple/nested clips → boolean flatten + custGeom
    COMPLEX = "complex"        # Requires EMF (text, complex transforms, filters)
    UNSUPPORTED = "unsupported" # Requires rasterization (animations, unsupported features)


class ClippingType(Enum):
    """Types of clipping operations."""
    PATH_BASED = "path"
    SHAPE_BASED = "shape"
    COMPLEX = "complex"


@dataclass
class ClipPathDefinition:
    """Definition of an SVG clipPath element."""
    id: str
    units: str  # userSpaceOnUse or objectBoundingBox
    clip_rule: str  # nonzero or evenodd
    path_data: str | None = None
    shapes: list[ET.Element] | None = None
    clipping_type: ClippingType = ClippingType.PATH_BASED
    transform: str | None = None


@dataclass
class ClipPathAnalysis:
    """Complete analysis result for a clipPath element."""
    complexity: ClipPathComplexity
    clip_chain: list[ClipPathDefinition]
    can_flatten: bool
    requires_emf: bool
    reason: str
    estimated_nodes: int = 0
    has_text: bool = False
    has_filters: bool = False
    has_animations: bool = False
    transform_complexity: int = 0  # 0=none, 1=simple, 2=complex