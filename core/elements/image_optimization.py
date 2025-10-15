"""
Image optimization helper used by ImageProcessor.
"""

from __future__ import annotations

import logging
from typing import Any

from lxml import etree as ET

from .image_models import ImageAnalysis, ImageFormat, ImageOptimization


class ImageOptimizer:
    """Apply recommended optimizations to image elements."""

    def __init__(self, services: Any, logger: logging.Logger | None = None):
        self.services = services
        self.logger = logger or logging.getLogger(__name__)

    def apply(self, element: ET.Element, analysis: ImageAnalysis, context: Any) -> tuple[ET.Element, int]:
        optimized_element = self._copy_element(element)
        applied_count = 0

        for optimization in analysis.optimization_opportunities:
            try:
                if optimization == ImageOptimization.RESIZE:
                    optimized_element = self._apply_resize(optimized_element, analysis)
                elif optimization == ImageOptimization.EMBED_INLINE:
                    optimized_element = self._apply_embed_inline(optimized_element)
                elif optimization == ImageOptimization.CONVERT_FORMAT:
                    optimized_element = self._apply_format_conversion(optimized_element, analysis)
                elif optimization == ImageOptimization.COMPRESS:
                    optimized_element = self._apply_compression(optimized_element)
                applied_count += 1
            except Exception as exc:
                self.logger.warning(f"Failed to apply optimization {optimization}: {exc}")

        optimized_element.set('data-image-optimized', 'true')
        return optimized_element, applied_count

    def _copy_element(self, element: ET.Element) -> ET.Element:
        copied = ET.Element(element.tag)

        for key, value in element.attrib.items():
            copied.set(key, value)

        if element.text:
            copied.text = element.text
        if element.tail:
            copied.tail = element.tail

        for child in element:
            copied.append(self._copy_element(child))

        return copied

    def _apply_resize(self, element: ET.Element, analysis: ImageAnalysis) -> ET.Element:
        max_width, max_height = 1920, 1080

        current_width = analysis.dimensions.width
        current_height = analysis.dimensions.height

        if current_width > max_width or current_height > max_height:
            scale_x = max_width / current_width
            scale_y = max_height / current_height
            scale = min(scale_x, scale_y)

            new_width = current_width * scale
            new_height = current_height * scale

            element.set('width', str(new_width))
            element.set('height', str(new_height))
            element.set('data-resize-applied', 'true')

        return element

    def _apply_embed_inline(self, element: ET.Element) -> ET.Element:
        element.set('data-embed-pending', 'true')
        return element

    def _apply_format_conversion(self, element: ET.Element, analysis: ImageAnalysis) -> ET.Element:
        if analysis.format is ImageFormat.SVG:
            element.set('data-convert-to-raster', 'true')
            element.set('data-target-format', 'png')
        return element

    def _apply_compression(self, element: ET.Element) -> ET.Element:
        element.set('data-compress-image', 'true')
        element.set('data-quality', '85')
        return element


__all__ = ["ImageOptimizer"]
