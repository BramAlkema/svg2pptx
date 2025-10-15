"""
Policy module for image preprocessing and optimization decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from lxml import etree as ET

from ..elements.image_models import ImageDimensions, ImageFormat, ImageOptimization


@dataclass(frozen=True)
class ImageMetrics:
    """Raw metrics describing an image element."""

    element: ET.Element
    href: str
    format: ImageFormat
    dimensions: ImageDimensions
    is_embedded: bool
    file_size: int | None


@dataclass(frozen=True)
class ImageOptimizationDecision:
    """Decision result for image optimization policy."""

    requires_preprocessing: bool
    optimizations: list[ImageOptimization]
    powerpoint_compatible: bool
    performance_impact: str


class ImageOptimizationPolicyProtocol(Protocol):
    def evaluate(self, metrics: ImageMetrics) -> ImageOptimizationDecision: ...


class ImageOptimizationPolicy:
    """Policy encapsulating heuristics for image preprocessing and optimization."""

    def evaluate(self, metrics: ImageMetrics) -> ImageOptimizationDecision:
        requires_preprocessing = self._requires_preprocessing(metrics)
        optimizations = self._identify_optimizations(metrics)
        powerpoint_compatible = self._assess_powerpoint_compatibility(metrics)
        performance_impact = self._estimate_performance_impact(metrics)

        return ImageOptimizationDecision(
            requires_preprocessing=requires_preprocessing,
            optimizations=optimizations,
            powerpoint_compatible=powerpoint_compatible,
            performance_impact=performance_impact,
        )

    def _requires_preprocessing(self, metrics: ImageMetrics) -> bool:
        element = metrics.element

        if element.get('data-image-optimized'):
            return False
        if metrics.format == ImageFormat.SVG:
            return True
        if element.get('transform'):
            return True
        if element.get('clip-path') or element.get('mask'):
            return True

        return False

    def _identify_optimizations(self, metrics: ImageMetrics) -> list[ImageOptimization]:
        optimizations: list[ImageOptimization] = []

        if metrics.dimensions.width > 2000 or metrics.dimensions.height > 2000:
            optimizations.append(ImageOptimization.RESIZE)

        if not metrics.is_embedded:
            optimizations.append(ImageOptimization.EMBED_INLINE)

        if metrics.format == ImageFormat.SVG:
            optimizations.append(ImageOptimization.CONVERT_FORMAT)

        if metrics.is_embedded:
            estimated_size = metrics.file_size
            if estimated_size and estimated_size > 100000:
                optimizations.append(ImageOptimization.COMPRESS)

        return optimizations

    def _assess_powerpoint_compatibility(self, metrics: ImageMetrics) -> bool:
        compatible_formats = {
            ImageFormat.PNG,
            ImageFormat.JPEG,
            ImageFormat.GIF,
            ImageFormat.BMP,
        }

        if metrics.format not in compatible_formats:
            return False

        if metrics.dimensions.width > 5000 or metrics.dimensions.height > 5000:
            return False

        return True

    def _estimate_performance_impact(self, metrics: ImageMetrics) -> str:
        pixel_count = metrics.dimensions.width * metrics.dimensions.height

        if pixel_count > 4_000_000:
            return 'high'

        if metrics.file_size and metrics.file_size > 500_000:
            return 'high'

        if pixel_count > 1_000_000 or (metrics.file_size and metrics.file_size > 100_000):
            return 'medium'

        if not metrics.is_embedded:
            return 'medium'

        return 'low'


__all__ = [
    "ImageMetrics",
    "ImageOptimizationDecision",
    "ImageOptimizationPolicy",
    "ImageOptimizationPolicyProtocol",
]
