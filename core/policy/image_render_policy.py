"""
Image rendering policy helper.
"""

from __future__ import annotations

import logging

from .config import PolicyConfig
from ..ir import Image
from .targets import DecisionReason, ImageDecision


class ImageRenderPolicy:
    """Decide how bitmap/vector images should be rendered."""

    def __init__(self, config: PolicyConfig, logger: logging.Logger | None = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    def decide(self, image: Image) -> ImageDecision:
        size_bytes = len(image.data)
        has_transparency = image.format in ["png", "gif"]

        reasons = [DecisionReason.PERFORMANCE_OK]
        return ImageDecision.emf(
            reasons=reasons,
            format=image.format,
            size_bytes=size_bytes,
            has_transparency=has_transparency,
            confidence=0.95,
            estimated_quality=0.98,
            estimated_performance=0.9,
        )


__all__ = ["ImageRenderPolicy"]
