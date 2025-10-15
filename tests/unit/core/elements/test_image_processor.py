#!/usr/bin/env python3
"""
Focused unit tests for ImageProcessor covering caching and optimization paths.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from lxml import etree as ET

from core.elements.image_analysis import ImageAnalyzer
from core.elements.image_processor import (
    ImageAnalysis,
    ImageDimensions,
    ImageFormat,
    ImageOptimization,
    ImageProcessor,
)
from core.policy.image_policy import ImageMetrics, ImageOptimizationPolicy


def make_processor():
    """Create an ImageProcessor with a minimal services container."""
    return ImageProcessor(services=SimpleNamespace())


def test_analyze_image_element_identifies_svg_optimizations():
    processor = make_processor()
    element = ET.Element('image', href='https://example.com/logo.svg', width='3000', height='1000')

    analysis = processor.analyze_image_element(element, context=SimpleNamespace())

    assert analysis.format is ImageFormat.SVG
    assert analysis.requires_preprocessing is True  # vector input triggers preprocessing
    assert analysis.is_vector is True
    assert analysis.is_embedded is False
    assert ImageOptimization.RESIZE in analysis.optimization_opportunities
    assert ImageOptimization.CONVERT_FORMAT in analysis.optimization_opportunities
    assert ImageOptimization.EMBED_INLINE in analysis.optimization_opportunities
    assert analysis.powerpoint_compatible is False
    assert analysis.estimated_performance_impact == 'medium'


def test_analyze_image_element_uses_cache_and_detects_large_embedded_images():
    processor = make_processor()
    base64_payload = "A" * 200_000
    data_url = f"data:image/png;base64,base64,{base64_payload}"
    element = ET.Element('image', href=data_url, width='100', height='100')

    first_analysis = processor.analyze_image_element(element, context=None)
    second_analysis = processor.analyze_image_element(element, context=None)

    assert first_analysis is second_analysis  # cached analysis reused
    assert processor.stats['images_processed'] == 1
    assert processor.stats['cache_hits'] == 1
    assert ImageOptimization.COMPRESS in first_analysis.optimization_opportunities
    assert first_analysis.is_embedded is True
    assert first_analysis.file_size and first_analysis.file_size > 0


def test_apply_image_optimizations_updates_element_attributes():
    processor = make_processor()
    source = ET.Element('image', href='https://example.com/photo.png', width='4000', height='3000')
    analysis = ImageAnalysis(
        element=source,
        href='https://example.com/photo.png',
        format=ImageFormat.PNG,
        dimensions=ImageDimensions(width=4000, height=3000, aspect_ratio=4 / 3),
        file_size=600_000,
        is_embedded=False,
        is_vector=False,
        requires_preprocessing=False,
        optimization_opportunities=[
            ImageOptimization.RESIZE,
            ImageOptimization.EMBED_INLINE,
            ImageOptimization.COMPRESS,
        ],
        powerpoint_compatible=True,
        estimated_performance_impact='high',
    )

    optimized = processor.apply_image_optimizations(source, analysis, context=None)

    assert optimized is not source  # copy created before mutations
    assert optimized.get('data-image-optimized') == 'true'
    assert optimized.get('data-embed-pending') == 'true'
    assert optimized.get('data-compress-image') == 'true'
    assert optimized.get('data-quality') == '85'
    assert optimized.get('data-resize-applied') == 'true'
    assert float(optimized.get('width')) <= 1920.0
    assert float(optimized.get('height')) <= 1080.0
    assert processor.stats['optimizations_applied'] == len(analysis.optimization_opportunities)


def test_parse_dimension_uses_unit_converter():
    class UnitConverterStub:
        def __init__(self):
            self.calls = []

        def to_pixels(self, value, unit):
            self.calls.append((value, unit))
            return 321.0

    services = SimpleNamespace(unit_converter=UnitConverterStub())
    analyzer = ImageAnalyzer(services=services)

    element = ET.Element('image', href='https://example.com/image.png', width='10cm', height='5cm')
    analysis = analyzer.analyze(element, context=None)

    assert services.unit_converter.calls == [(10.0, 'cm'), (5.0, 'cm')]
    assert analysis.dimensions.width == pytest.approx(321.0)
    assert analysis.dimensions.height == pytest.approx(321.0)


def test_parse_dimension_fallback_when_converter_raises():
    class UnitConverterStub:
        def to_pixels(self, value, unit):
            raise RuntimeError("conversion failed")

    services = SimpleNamespace(unit_converter=UnitConverterStub())
    analyzer = ImageAnalyzer(services=services)

    element = ET.Element('image', href='https://example.com/image.png', width='2in', height='1in')
    analysis = analyzer.analyze(element, context=None)

    assert analysis.dimensions.width == pytest.approx(192.0)
    assert analysis.dimensions.height == pytest.approx(96.0)


def test_create_invalid_image_analysis_sets_expected_defaults():
    analyzer = ImageAnalyzer(services=SimpleNamespace())
    element = ET.Element('image')

    analysis = analyzer.analyze(element, context=None)

    assert analysis.href == ""
    assert analysis.format is ImageFormat.UNKNOWN
    assert analysis.requires_preprocessing is False
    assert analysis.powerpoint_compatible is False
    assert analysis.estimated_performance_impact == 'none'


def test_estimate_performance_impact_scales_with_pixels():
    policy = ImageOptimizationPolicy()
    element = ET.Element('image')
    base_metrics = lambda dims, embedded, size: ImageMetrics(
        element=element,
        href='data:image/png;base64,',
        format=ImageFormat.PNG,
        dimensions=dims,
        is_embedded=embedded,
        file_size=size,
    )

    small = policy.evaluate(base_metrics(ImageDimensions(100, 100, 1.0), True, 10_000)).performance_impact
    medium = policy.evaluate(base_metrics(ImageDimensions(1200, 900, 4 / 3), False, None)).performance_impact
    large = policy.evaluate(base_metrics(ImageDimensions(3000, 3000, 1.0), True, None)).performance_impact

    assert small == 'low'
    assert medium == 'medium'
    assert large == 'high'
