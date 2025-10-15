"""
Shared data structures for image processing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional

from lxml import etree as ET


class ImageFormat(Enum):
    """Supported image formats."""

    PNG = "png"
    JPEG = "jpeg"
    SVG = "svg"
    GIF = "gif"
    BMP = "bmp"
    TIFF = "tiff"
    UNKNOWN = "unknown"


class ImageOptimization(Enum):
    """Image optimization strategies."""

    NONE = "none"
    COMPRESS = "compress"
    RESIZE = "resize"
    CONVERT_FORMAT = "convert_format"
    EMBED_INLINE = "embed_inline"


@dataclass
class ImageDimensions:
    """Image dimension information."""

    width: float
    height: float
    aspect_ratio: float
    units: str = "px"

    @property
    def is_square(self) -> bool:
        return abs(self.aspect_ratio - 1.0) < 0.01


@dataclass
class ImageAnalysis:
    """Result of image analysis."""

    element: ET.Element
    href: str
    format: ImageFormat
    dimensions: ImageDimensions
    file_size: Optional[int]
    is_embedded: bool
    is_vector: bool
    requires_preprocessing: bool
    optimization_opportunities: List[ImageOptimization]
    powerpoint_compatible: bool
    estimated_performance_impact: str


__all__ = [
    "ImageFormat",
    "ImageOptimization",
    "ImageDimensions",
    "ImageAnalysis",
]
