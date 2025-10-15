#!/usr/bin/env python3
"""Structured clipping interface exports."""

from .model import (
    ClipComputeResult,
    ClipCustGeom,
    ClipFallback,
    ClipMediaMeta,
)
from .service import StructuredClipService

__all__ = [
    "ClipComputeResult",
    "ClipCustGeom",
    "ClipFallback",
    "ClipMediaMeta",
    "StructuredClipService",
]
