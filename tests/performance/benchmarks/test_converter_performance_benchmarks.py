#!/usr/bin/env python3
"""
Performance benchmark tests for critical conversion paths.

This module tests the performance characteristics of key converters to ensure
they meet performance targets and can handle various workloads efficiently.
"""

import pytest
import time
from lxml import etree as ET
from pathlib import Path
import sys
from unittest.mock import Mock

# Import centralized fixtures
from tests.fixtures.common import *
from tests.fixtures.mock_objects import *
from tests.fixtures.svg_content import *

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.converters.shapes import RectangleConverter, CircleConverter, PolygonConverter
from src.converters.text import TextConverter
from src.converters.paths import PathConverter
from src.converters.base import ConversionContext


@pytest.mark.benchmark
@pytest.mark.performance
class TestShapeConverterPerformance:
    """Performance benchmarks for shape converters."""

    def test_rectangle_converter_performance(self, benchmark):
        """Benchmark rectangle converter with standard shapes."""
        converter = RectangleConverter()

        # Create test rectangle
        element = ET.fromstring('<rect x="10" y="10" width="100" height="50" fill="red"/>')

        # Setup context
        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.return_value = (9144, 9144)
        context.coordinate_system.svg_length_to_emu.side_effect = lambda val, direction: int(val * 914.4)
        context.get_next_shape_id.return_value = 1001

        # Mock style methods for performance focus
        converter.generate_fill = Mock(return_value='<fill/>')
        converter.generate_stroke = Mock(return_value='<stroke/>')

        # Benchmark the conversion
        def convert_rectangle():
            return converter.convert(element, context)

        result = benchmark(convert_rectangle)

        # Verify functionality
        assert isinstance(result, str)
        assert len(result) > 0
        assert '<p:sp>' in result

    def test_circle_converter_performance(self, benchmark):
        """Benchmark circle converter performance."""
        converter = CircleConverter()

        element = ET.fromstring('<circle cx="50" cy="50" r="25" fill="blue"/>')

        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.return_value = (22860, 22860)
        context.coordinate_system.svg_length_to_emu.return_value = 45720
        context.get_next_shape_id.return_value = 2001

        converter.generate_fill = Mock(return_value='<fill/>')
        converter.generate_stroke = Mock(return_value='<stroke/>')

        def convert_circle():
            return converter.convert(element, context)

        result = benchmark(convert_circle)

        assert isinstance(result, str)
        assert '<a:prstGeom prst="ellipse">' in result

    def test_polygon_converter_performance_small(self, benchmark):
        """Benchmark polygon converter with small polygon."""
        converter = PolygonConverter()

        # Small triangle
        element = ET.fromstring('<polygon points="0,0 100,0 50,100" fill="green"/>')

        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.return_value = (0, 0)
        context.coordinate_system.svg_length_to_emu.side_effect = [91440, 91440]
        context.get_next_shape_id.return_value = 3001

        converter.generate_fill = Mock(return_value='<fill/>')
        converter.generate_stroke = Mock(return_value='<stroke/>')

        def convert_small_polygon():
            return converter.convert(element, context)

        result = benchmark(convert_small_polygon)

        assert isinstance(result, str)
        assert '<a:custGeom>' in result

    def test_polygon_converter_performance_large(self, benchmark):
        """Benchmark polygon converter with large polygon (100+ points)."""
        converter = PolygonConverter()

        # Generate large polygon with 100 points
        import math
        points = []
        for i in range(100):
            angle = 2 * math.pi * i / 100
            x = 50 + 40 * math.cos(angle)
            y = 50 + 40 * math.sin(angle)
            points.append(f"{x:.2f},{y:.2f}")

        points_str = " ".join(points)
        element = ET.fromstring(f'<polygon points="{points_str}" fill="purple"/>')

        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.return_value = (9144, 9144)
        context.coordinate_system.svg_length_to_emu.side_effect = [73152, 73152]
        context.get_next_shape_id.return_value = 3002

        converter.generate_fill = Mock(return_value='<fill/>')
        converter.generate_stroke = Mock(return_value='<stroke/>')

        def convert_large_polygon():
            return converter.convert(element, context)

        result = benchmark(convert_large_polygon)

        assert isinstance(result, str)
        assert '<a:custGeom>' in result

        # Should complete within reasonable time even with 100 points
        # pytest-benchmark will track this automatically


@pytest.mark.benchmark
@pytest.mark.performance
class TestTextConverterPerformance:
    """Performance benchmarks for text converter."""

    def test_simple_text_performance(self, benchmark):
        """Benchmark simple text conversion."""
        converter = TextConverter()

        element = ET.fromstring('<text x="50" y="50">Simple Text</text>')

        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.return_value = (45720, 45720)
        context.get_next_shape_id.return_value = 4001

        # Mock helper methods
        converter._extract_text_content = Mock(return_value='Simple Text')
        converter._get_font_family = Mock(return_value='Arial')
        converter._get_font_size = Mock(return_value=12)
        converter._get_font_weight = Mock(return_value='normal')
        converter._get_font_style = Mock(return_value='normal')
        converter._get_text_anchor = Mock(return_value='l')
        converter._get_text_decoration = Mock(return_value='')
        converter._get_fill_color = Mock(return_value='<fill/>')
        converter.to_emu = Mock(return_value=91440)

        def convert_simple_text():
            return converter.convert(element, context)

        result = benchmark(convert_simple_text)

        assert isinstance(result, str)
        assert 'Simple Text' in result

    def test_large_text_performance(self, benchmark):
        """Benchmark conversion of large text content."""
        converter = TextConverter()

        # Large text content (1KB)
        large_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 20
        element = ET.fromstring(f'<text x="50" y="50">{large_text}</text>')

        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.return_value = (45720, 45720)
        context.get_next_shape_id.return_value = 4002

        # Mock helper methods for performance focus
        converter._extract_text_content = Mock(return_value=large_text)
        converter._get_font_family = Mock(return_value='Arial')
        converter._get_font_size = Mock(return_value=12)
        converter._get_font_weight = Mock(return_value='normal')
        converter._get_font_style = Mock(return_value='normal')
        converter._get_text_anchor = Mock(return_value='l')
        converter._get_text_decoration = Mock(return_value='')
        converter._get_fill_color = Mock(return_value='<fill/>')
        converter.to_emu = Mock(return_value=91440)

        def convert_large_text():
            return converter.convert(element, context)

        result = benchmark(convert_large_text)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_complex_tspan_performance(self, benchmark):
        """Benchmark text with complex tspan structure."""
        converter = TextConverter()

        # Complex nested tspan structure
        tspan_xml = '''<text x="50" y="50">
            Root text
            <tspan>First span</tspan>
            <tspan>
                Nested start
                <tspan>Deep nested</tspan>
                Nested end
            </tspan>
            Final text
        </text>'''

        element = ET.fromstring(tspan_xml)

        def extract_complex_text():
            return converter._extract_text_content(element)

        result = benchmark(extract_complex_text)

        assert isinstance(result, str)
        assert 'Root text' in result
        assert 'Deep nested' in result


@pytest.mark.benchmark
@pytest.mark.performance
class TestPathConverterPerformance:
    """Performance benchmarks for path converter."""

    def test_simple_path_performance(self, benchmark):
        """Benchmark simple path conversion."""
        try:
            from src.converters.paths import PathConverter
        except ImportError:
            pytest.skip("PathConverter not available")

        converter = PathConverter()

        # Simple path
        element = ET.fromstring('<path d="M 10 10 L 90 90 Z" fill="red"/>')

        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.return_value = (9144, 9144)
        context.coordinate_system.svg_length_to_emu.side_effect = lambda val, direction: int(val * 914.4)
        context.get_next_shape_id.return_value = 5001

        # Mock methods that might exist
        if hasattr(converter, 'generate_fill'):
            converter.generate_fill = Mock(return_value='<fill/>')
        if hasattr(converter, 'generate_stroke'):
            converter.generate_stroke = Mock(return_value='<stroke/>')

        def convert_simple_path():
            return converter.convert(element, context)

        result = benchmark(convert_simple_path)

        assert isinstance(result, str)

    def test_complex_path_performance(self, benchmark):
        """Benchmark complex path with curves."""
        try:
            from src.converters.paths import PathConverter
        except ImportError:
            pytest.skip("PathConverter not available")

        converter = PathConverter()

        # Complex path with curves
        complex_path = '''M 20 80 C 40 10, 65 10, 95 80 S 150 150, 180 80
                         Q 200 50, 220 80 T 250 60 L 280 100 Z'''
        element = ET.fromstring(f'<path d="{complex_path}" fill="blue"/>')

        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.return_value = (18288, 9144)
        context.coordinate_system.svg_length_to_emu.side_effect = lambda val, direction: int(val * 914.4)
        context.get_next_shape_id.return_value = 5002

        if hasattr(converter, 'generate_fill'):
            converter.generate_fill = Mock(return_value='<fill/>')
        if hasattr(converter, 'generate_stroke'):
            converter.generate_stroke = Mock(return_value='<stroke/>')

        def convert_complex_path():
            return converter.convert(element, context)

        result = benchmark(convert_complex_path)

        assert isinstance(result, str)


@pytest.mark.benchmark
@pytest.mark.performance
class TestBatchConversionPerformance:
    """Performance benchmarks for batch conversion scenarios."""

    def test_multiple_shapes_performance(self, benchmark):
        """Benchmark conversion of multiple shapes together."""
        # Test data: 50 rectangles
        rectangles = []
        rect_converter = RectangleConverter()

        for i in range(50):
            x, y = i * 10, i * 5
            element = ET.fromstring(f'<rect x="{x}" y="{y}" width="50" height="30" fill="red"/>')
            rectangles.append(element)

        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.side_effect = lambda x, y: (int(x * 914.4), int(y * 914.4))
        context.coordinate_system.svg_length_to_emu.side_effect = lambda val, direction: int(val * 914.4)
        context.get_next_shape_id.side_effect = range(6001, 6051)

        rect_converter.generate_fill = Mock(return_value='<fill/>')
        rect_converter.generate_stroke = Mock(return_value='<stroke/>')

        def convert_multiple_shapes():
            results = []
            for rect in rectangles:
                result = rect_converter.convert(rect, context)
                results.append(result)
            return results

        results = benchmark(convert_multiple_shapes)

        assert len(results) == 50
        assert all(isinstance(r, str) for r in results)

    def test_mixed_elements_performance(self, benchmark):
        """Benchmark conversion of mixed element types."""
        # Mixed elements: rectangles, circles, text
        elements = []
        converters = []

        # Create mixed elements
        for i in range(20):
            if i % 3 == 0:
                elem = ET.fromstring(f'<rect x="{i*10}" y="10" width="40" height="20" fill="red"/>')
                conv = RectangleConverter()
            elif i % 3 == 1:
                elem = ET.fromstring(f'<circle cx="{i*10+20}" cy="30" r="15" fill="blue"/>')
                conv = CircleConverter()
            else:
                elem = ET.fromstring(f'<text x="{i*10}" y="50">Text {i}</text>')
                conv = TextConverter()
                # Mock text converter methods
                conv._extract_text_content = Mock(return_value=f'Text {i}')
                conv._get_font_family = Mock(return_value='Arial')
                conv._get_font_size = Mock(return_value=12)
                conv._get_font_weight = Mock(return_value='normal')
                conv._get_font_style = Mock(return_value='normal')
                conv._get_text_anchor = Mock(return_value='l')
                conv._get_text_decoration = Mock(return_value='')
                conv._get_fill_color = Mock(return_value='<fill/>')
                conv.to_emu = Mock(return_value=91440)

            if hasattr(conv, 'generate_fill'):
                conv.generate_fill = Mock(return_value='<fill/>')
            if hasattr(conv, 'generate_stroke'):
                conv.generate_stroke = Mock(return_value='<stroke/>')

            elements.append(elem)
            converters.append(conv)

        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.side_effect = lambda x, y: (int(x * 914.4), int(y * 914.4))
        context.coordinate_system.svg_length_to_emu.side_effect = lambda val, direction: int(val * 914.4)
        context.get_next_shape_id.side_effect = range(7001, 7021)

        def convert_mixed_elements():
            results = []
            for elem, conv in zip(elements, converters):
                result = conv.convert(elem, context)
                results.append(result)
            return results

        results = benchmark(convert_mixed_elements)

        assert len(results) == 20
        assert all(isinstance(r, str) for r in results)


@pytest.mark.benchmark
@pytest.mark.performance
class TestMemoryEfficiencyBenchmarks:
    """Memory efficiency benchmarks for converters."""

    def test_memory_usage_large_polygon(self):
        """Test memory usage with large polygon (memory efficiency)."""
        converter = PolygonConverter()

        # Very large polygon (1000 points)
        import math
        points = []
        for i in range(1000):
            angle = 2 * math.pi * i / 1000
            x = 50 + 40 * math.cos(angle)
            y = 50 + 40 * math.sin(angle)
            points.append(f"{x:.6f},{y:.6f}")

        points_str = " ".join(points)
        element = ET.fromstring(f'<polygon points="{points_str}" fill="orange"/>')

        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.return_value = (9144, 9144)
        context.coordinate_system.svg_length_to_emu.side_effect = [73152, 73152]
        context.get_next_shape_id.return_value = 8001

        converter.generate_fill = Mock(return_value='<fill/>')
        converter.generate_stroke = Mock(return_value='<stroke/>')

        # Measure memory usage (basic test)
        import gc
        import psutil
        import os

        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss

        # Convert large polygon
        result = converter.convert(element, context)

        # Force garbage collection
        gc.collect()

        memory_after = process.memory_info().rss
        memory_increase = memory_after - memory_before

        # Should not increase memory significantly (< 50MB for 1000 points)
        assert memory_increase < 50 * 1024 * 1024, f"Memory increase too large: {memory_increase / 1024 / 1024:.2f}MB"
        assert isinstance(result, str)
        assert len(result) > 0

    def test_conversion_time_scaling(self):
        """Test that conversion time scales reasonably with input size."""
        converter = PolygonConverter()

        # Test different polygon sizes
        test_sizes = [10, 50, 100, 200]
        times = []

        for size in test_sizes:
            # Generate polygon
            import math
            points = []
            for i in range(size):
                angle = 2 * math.pi * i / size
                x = 50 + 40 * math.cos(angle)
                y = 50 + 40 * math.sin(angle)
                points.append(f"{x:.3f},{y:.3f}")

            points_str = " ".join(points)
            element = ET.fromstring(f'<polygon points="{points_str}" fill="red"/>')

            context = Mock(spec=ConversionContext)
            context.coordinate_system = Mock()
            context.coordinate_system.svg_to_emu.return_value = (9144, 9144)
            context.coordinate_system.svg_length_to_emu.side_effect = [73152, 73152]
            context.get_next_shape_id.return_value = 9000 + size

            converter.generate_fill = Mock(return_value='<fill/>')
            converter.generate_stroke = Mock(return_value='<stroke/>')

            # Time the conversion
            start_time = time.time()
            result = converter.convert(element, context)
            end_time = time.time()

            conversion_time = end_time - start_time
            times.append(conversion_time)

            assert isinstance(result, str)
            assert len(result) > 0

        # Check that time doesn't grow exponentially
        # Linear growth is acceptable, exponential is not
        for i in range(1, len(times)):
            ratio = times[i] / times[i-1]
            size_ratio = test_sizes[i] / test_sizes[i-1]

            # Time should not grow more than quadratically with size
            assert ratio < size_ratio ** 2, f"Performance degradation too severe: {ratio:.2f}x time for {size_ratio:.2f}x size"


@pytest.mark.benchmark
@pytest.mark.performance
class TestRealWorldPerformance:
    """Real-world performance scenario benchmarks."""

    def test_typical_logo_performance(self, benchmark):
        """Benchmark typical logo conversion scenario."""
        # Simulate a typical logo with mixed elements
        logo_elements = [
            ('<rect x="0" y="0" width="200" height="100" rx="10" fill="blue"/>', RectangleConverter()),
            ('<circle cx="50" cy="50" r="20" fill="white"/>', CircleConverter()),
            ('<text x="100" y="55" font-size="16" fill="white">LOGO</text>', TextConverter()),
        ]

        converters_and_elements = []
        for xml, conv_class in logo_elements:
            element = ET.fromstring(xml)
            converter = conv_class()

            if hasattr(converter, 'generate_fill'):
                converter.generate_fill = Mock(return_value='<fill/>')
            if hasattr(converter, 'generate_stroke'):
                converter.generate_stroke = Mock(return_value='<stroke/>')

            # Special setup for text converter
            if isinstance(converter, TextConverter):
                converter._extract_text_content = Mock(return_value='LOGO')
                converter._get_font_family = Mock(return_value='Arial')
                converter._get_font_size = Mock(return_value=16)
                converter._get_font_weight = Mock(return_value='normal')
                converter._get_font_style = Mock(return_value='normal')
                converter._get_text_anchor = Mock(return_value='l')
                converter._get_text_decoration = Mock(return_value='')
                converter._get_fill_color = Mock(return_value='<fill/>')
                converter.to_emu = Mock(return_value=91440)

            converters_and_elements.append((element, converter))

        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.side_effect = lambda x, y: (int(x * 914.4), int(y * 914.4))
        context.coordinate_system.svg_length_to_emu.side_effect = lambda val, direction: int(val * 914.4)
        context.get_next_shape_id.side_effect = [10001, 10002, 10003]

        def convert_logo():
            results = []
            for element, converter in converters_and_elements:
                result = converter.convert(element, context)
                results.append(result)
            return results

        results = benchmark(convert_logo)

        assert len(results) == 3
        assert all(isinstance(r, str) for r in results)
        assert any('<a:prstGeom prst="roundRect">' in r for r in results)  # Rounded rect
        assert any('<a:prstGeom prst="ellipse">' in r for r in results)    # Circle
        assert any('LOGO' in r for r in results)                          # Text