"""
Image analysis helper used by ImageProcessor.
"""

from __future__ import annotations

import logging
from typing import Any

from lxml import etree as ET

from .image_models import ImageAnalysis, ImageDimensions, ImageFormat
from .image_utils import determine_image_format, estimate_file_size, extract_image_href, is_embedded_image
from ..policy.image_policy import ImageMetrics, ImageOptimizationPolicy, ImageOptimizationPolicyProtocol


class ImageAnalyzer:
    """Perform image analysis and produce ImageAnalysis metadata."""

    def __init__(self, services: Any, logger: logging.Logger | None = None,
                 policy: ImageOptimizationPolicyProtocol | None = None):
        self.services = services
        self.logger = logger or logging.getLogger(__name__)
        self._policy = policy or ImageOptimizationPolicy()

    def analyze(self, element: ET.Element, context: Any) -> ImageAnalysis:
        """Analyze an image element and return its characteristics."""
        href = extract_image_href(element)
        if not href:
            return self._create_invalid_analysis(element, "No href found")

        image_format = determine_image_format(href)
        dimensions = self._extract_image_dimensions(element, context)
        embedded = is_embedded_image(href)
        file_size = estimate_file_size(href) if embedded else None
        is_vector = image_format == ImageFormat.SVG

        decision = self._policy.evaluate(
            ImageMetrics(
                element=element,
                href=href,
                format=image_format,
                dimensions=dimensions,
                is_embedded=embedded,
                file_size=file_size,
            ),
        )

        return ImageAnalysis(
            element=element,
            href=href,
            format=image_format,
            dimensions=dimensions,
            file_size=file_size,
            is_embedded=embedded,
            is_vector=is_vector,
            requires_preprocessing=decision.requires_preprocessing,
            optimization_opportunities=decision.optimizations,
            powerpoint_compatible=decision.powerpoint_compatible,
            estimated_performance_impact=decision.performance_impact,
        )

    def _create_invalid_analysis(self, element: ET.Element, reason: str) -> ImageAnalysis:
        self.logger.warning(f"Invalid image element: {reason}")
        return ImageAnalysis(
            element=element,
            href="",
            format=ImageFormat.UNKNOWN,
            dimensions=ImageDimensions(width=0, height=0, aspect_ratio=1.0),
            file_size=None,
            is_embedded=False,
            is_vector=False,
            requires_preprocessing=False,
            optimization_opportunities=[],
            powerpoint_compatible=False,
            estimated_performance_impact='none',
        )

    def _extract_image_dimensions(self, element: ET.Element, context: Any) -> ImageDimensions:
        width_str = element.get('width', '100')
        height_str = element.get('height', '100')

        width = self._parse_dimension(width_str, context)
        height = self._parse_dimension(height_str, context)
        aspect_ratio = width / height if height != 0 else 1.0

        return ImageDimensions(
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            units="px",
        )

    def _parse_dimension(self, dimension_str: str, context: Any) -> float:
        if not dimension_str:
            return 100.0

        import re

        match = re.match(r'([\d.]+)(\w*)', dimension_str.strip())
        if not match:
            return 100.0

        value = float(match.group(1))
        unit = match.group(2) or 'px'

        if hasattr(self.services, 'unit_converter'):
            try:
                return self.services.unit_converter.to_pixels(value, unit)
            except Exception as exc:
                self.logger.warning(f"Unit conversion failed: {exc}")

        unit_map = {
            'px': 1.0,
            'pt': 1.333,
            'in': 96.0,
            'cm': 37.795,
            'mm': 3.7795,
            'em': 16.0,
            'rem': 16.0,
            '%': 1.0,
        }
        return value * unit_map.get(unit.lower(), 1.0)

__all__ = ["ImageAnalyzer"]
