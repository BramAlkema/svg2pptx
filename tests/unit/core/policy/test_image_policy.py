#!/usr/bin/env python3
"""Unit tests for image optimization policy decisions."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from lxml import etree as ET

from core.elements.image_models import ImageDimensions, ImageFormat, ImageOptimization
from core.policy.image_policy import ImageMetrics, ImageOptimizationPolicy


def make_metrics(format_: ImageFormat = ImageFormat.PNG,
                 width: float = 100,
                 height: float = 100,
                 is_embedded: bool = False,
                 file_size: int | None = None,
                 element: ET.Element | None = None) -> ImageMetrics:
    if element is None:
        element = ET.Element('image')
    return ImageMetrics(
        element=element,
        href='data:image/png;base64,' if is_embedded else 'https://example.com/img.png',
        format=format_,
        dimensions=ImageDimensions(width=width, height=height, aspect_ratio=width / height if height else 1.0),
        is_embedded=is_embedded,
        file_size=file_size,
    )


def test_policy_flags_large_dimensions_for_resize():
    policy = ImageOptimizationPolicy()
    metrics = make_metrics(width=4000, height=3000)

    decision = policy.evaluate(metrics)

    assert ImageOptimization.RESIZE in decision.optimizations
    assert decision.requires_preprocessing is False


def test_policy_embeds_external_images():
    policy = ImageOptimizationPolicy()
    metrics = make_metrics(is_embedded=False)

    decision = policy.evaluate(metrics)

    assert ImageOptimization.EMBED_INLINE in decision.optimizations


def test_policy_converts_svg_and_requires_preprocessing():
    element = ET.Element('image')
    metrics = make_metrics(format_=ImageFormat.SVG, element=element)
    policy = ImageOptimizationPolicy()

    decision = policy.evaluate(metrics)

    assert decision.requires_preprocessing is True
    assert ImageOptimization.CONVERT_FORMAT in decision.optimizations


def test_policy_compresses_large_embedded_images():
    metrics = make_metrics(is_embedded=True, file_size=200_000)
    policy = ImageOptimizationPolicy()

    decision = policy.evaluate(metrics)

    assert ImageOptimization.COMPRESS in decision.optimizations


@pytest.mark.parametrize(
    ("format_", "expected"),
    [
        (ImageFormat.PNG, True),
        (ImageFormat.JPEG, True),
        (ImageFormat.GIF, True),
        (ImageFormat.SVG, False),
    ],
)
def test_policy_assesses_powerpoint_compatibility(format_, expected):
    policy = ImageOptimizationPolicy()
    metrics = make_metrics(format_=format_)

    decision = policy.evaluate(metrics)

    assert decision.powerpoint_compatible is expected


def test_policy_estimates_performance_impact():
    policy = ImageOptimizationPolicy()

    low = policy.evaluate(make_metrics(width=100, height=100, is_embedded=True, file_size=10_000))
    medium = policy.evaluate(make_metrics(width=1200, height=900, is_embedded=False))
    high = policy.evaluate(make_metrics(width=4000, height=4000, is_embedded=True, file_size=600_000))

    assert low.performance_impact == 'low'
    assert medium.performance_impact == 'medium'
    assert high.performance_impact == 'high'
