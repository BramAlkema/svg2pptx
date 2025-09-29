#!/usr/bin/env python3
"""
Performance and Quality Validation Tests for Clean Slate Pipeline.

Comprehensive validation of performance characteristics, quality metrics,
and production readiness of the complete Clean Slate Architecture.
"""

import pytest
from pathlib import Path
import sys
import time
import psutil
import gc
from unittest.mock import Mock, patch
import tempfile
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from core.parsers import SVGParser
    from core.ir import Scene, Path, TextFrame, Group, Image
    from core.policies import PolicyEngine, ConversionPolicy, QualityEngine
    from core.mappers import SceneMapper, PathMapper, TextMapper
    from lxml import etree
    CORE_PIPELINE_AVAILABLE = True
except ImportError:
    CORE_PIPELINE_AVAILABLE = False
    pytest.skip("Core pipeline components not available", allow_module_level=True)


class TestPipelinePerformanceBenchmarks:
    """Performance benchmarking tests for the Clean Slate pipeline."""

    def test_svg_parsing_performance_benchmark(self):
        """Benchmark SVG parsing performance."""
        # Generate test SVGs of varying complexity
        test_cases = [
            # Simple SVG
            '''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
                <rect x="10" y="10" width="80" height="80" fill="#FF0000"/>
               </svg>''',

            # Medium complexity SVG
            '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
                <rect x="10" y="10" width="80" height="80" fill="#FF0000"/>
                <circle cx="100" cy="100" r="40" fill="#00FF00"/>
                <text x="100" y="180" text-anchor="middle" font-size="16">Medium</text>
               </svg>''',

            # Complex SVG with many elements
            '''<svg xmlns="http://www.w3.org/2000/svg" width="500" height="500" viewBox="0 0 500 500">
                ''' + ''.join([
                    f'<rect x="{i*20}" y="{i*15}" width="15" height="10" fill="#{i*4:02x}{255-i*4:02x}00"/>'
                    for i in range(25)
                ]) + '''
                ''' + ''.join([
                    f'<circle cx="{250 + i*10}" cy="{250 + i*8}" r="5" fill="#0000{i*10:02x}"/>'
                    for i in range(25)
                ]) + '''
                <text x="250" y="480" text-anchor="middle" font-size="20">Complex</text>
               </svg>'''
        ]

        try:
            parser = SVGParser()
            performance_results = []

            for i, svg_content in enumerate(test_cases):
                # Warm up
                parser.parse_to_ir(svg_content)

                # Benchmark
                start_time = time.time()

                for _ in range(10):  # Run multiple times for average
                    scene_ir = parser.parse_to_ir(svg_content)
                    assert scene_ir is not None

                end_time = time.time()
                avg_time = (end_time - start_time) / 10

                performance_results.append({
                    'complexity': ['Simple', 'Medium', 'Complex'][i],
                    'avg_parse_time': avg_time,
                    'elements_count': len(scene_ir.elements)
                })

            # Performance assertions
            assert performance_results[0]['avg_parse_time'] < 0.01  # Simple < 10ms
            assert performance_results[1]['avg_parse_time'] < 0.05  # Medium < 50ms
            assert performance_results[2]['avg_parse_time'] < 0.1   # Complex < 100ms

            # Validate performance scaling
            simple_time = performance_results[0]['avg_parse_time']
            complex_time = performance_results[2]['avg_parse_time']
            assert complex_time / simple_time < 20  # Should scale reasonably

        except NameError:
            pytest.skip("SVGParser not available")

    def test_policy_evaluation_performance_benchmark(self):
        """Benchmark policy evaluation performance."""
        try:
            # Create test IR elements of different complexities
            simple_path = Path(
                segments=[],  # Will be populated
                fill=None,
                stroke=None,
                is_closed=False,
                data="M 0 0 L 100 100"
            )

            # Generate complex path
            from core.ir import LineSegment, Point, SolidPaint
            complex_segments = []
            for i in range(100):
                complex_segments.append(LineSegment(Point(i, 0), Point(i+1, 1)))

            complex_path = Path(
                segments=complex_segments,
                fill=SolidPaint(color="#FF0000"),
                stroke=None,
                is_closed=False,
                data="M " + " L ".join([f"{i} {i%2}" for i in range(101)])
            )

            policy_engine = PolicyEngine()

            # Benchmark simple elements
            start_time = time.time()
            for _ in range(100):
                decision = policy_engine.evaluate_element(simple_path)
                assert decision is not None
            simple_time = (time.time() - start_time) / 100

            # Benchmark complex elements
            start_time = time.time()
            for _ in range(100):
                decision = policy_engine.evaluate_element(complex_path)
                assert decision is not None
            complex_time = (time.time() - start_time) / 100

            # Performance assertions
            assert simple_time < 0.001  # Simple elements < 1ms
            assert complex_time < 0.01  # Complex elements < 10ms
            assert complex_time / simple_time < 15  # Reasonable scaling

        except NameError:
            pytest.skip("PolicyEngine not available")

    def test_mapping_performance_benchmark(self):
        """Benchmark mapping performance."""
        try:
            from core.ir import LineSegment, Point, SolidPaint

            # Create test paths of varying complexity
            simple_path = Path(
                segments=[LineSegment(Point(0, 0), Point(100, 100))],
                fill=SolidPaint(color="#FF0000"),
                stroke=None,
                is_closed=False,
                data="M 0 0 L 100 100"
            )

            # Medium complexity path
            medium_segments = []
            for i in range(10):
                medium_segments.append(LineSegment(Point(i*10, 0), Point(i*10+10, 10)))

            medium_path = Path(
                segments=medium_segments,
                fill=SolidPaint(color="#00FF00"),
                stroke=None,
                is_closed=False,
                data="M " + " L ".join([f"{i*10} {10 if i%2 else 0}" for i in range(11)])
            )

            path_mapper = PathMapper()

            # Benchmark simple mapping
            start_time = time.time()
            for _ in range(50):
                result = path_mapper.map_path(simple_path)
                assert result is not None
            simple_mapping_time = (time.time() - start_time) / 50

            # Benchmark medium mapping
            start_time = time.time()
            for _ in range(50):
                result = path_mapper.map_path(medium_path)
                assert result is not None
            medium_mapping_time = (time.time() - start_time) / 50

            # Performance assertions
            assert simple_mapping_time < 0.005  # Simple < 5ms
            assert medium_mapping_time < 0.02   # Medium < 20ms

        except NameError:
            pytest.skip("PathMapper not available")

    def test_end_to_end_pipeline_performance_benchmark(self):
        """Benchmark complete pipeline performance."""
        test_svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200">
            <rect x="20" y="20" width="100" height="80" fill="#FF0000"/>
            <circle cx="200" cy="60" r="40" fill="#00FF00"/>
            <text x="150" y="150" text-anchor="middle" font-size="16">Benchmark</text>
            <path d="M 50 180 L 100 160 L 150 180 L 200 160 L 250 180" stroke="#0000FF" stroke-width="2" fill="none"/>
        </svg>
        '''

        try:
            # Complete pipeline benchmark
            parser = SVGParser()
            policy_engine = PolicyEngine()
            scene_mapper = SceneMapper()

            start_time = time.time()

            for _ in range(20):
                # Parse
                scene_ir = parser.parse_to_ir(test_svg)
                assert scene_ir is not None

                # Policy evaluation
                scene_decision = policy_engine.evaluate_element(scene_ir)
                assert scene_decision is not None

                # Mapping
                result = scene_mapper.map_scene(scene_ir)
                assert result is not None

            total_time = (time.time() - start_time) / 20

            # Performance assertion
            assert total_time < 0.1  # Complete pipeline < 100ms

        except NameError:
            pytest.skip("Pipeline components not available")


class TestPipelineMemoryUsage:
    """Memory usage validation tests."""

    def test_memory_usage_during_parsing(self):
        """Test memory usage during SVG parsing."""
        try:
            # Monitor memory usage
            process = psutil.Process()
            initial_memory = process.memory_info().rss

            # Generate large SVG
            elements = []
            for i in range(200):
                elements.append(f'<rect x="{i*2}" y="{i}" width="10" height="8" fill="#{i:02x}00{255-i:02x}"/>')

            large_svg = f'''
            <svg xmlns="http://www.w3.org/2000/svg" width="800" height="400" viewBox="0 0 800 400">
                {"".join(elements)}
            </svg>
            '''

            parser = SVGParser()

            # Parse and measure memory
            scene_ir = parser.parse_to_ir(large_svg)
            assert scene_ir is not None
            assert len(scene_ir.elements) == 200

            peak_memory = process.memory_info().rss
            memory_increase = peak_memory - initial_memory

            # Memory usage should be reasonable (< 50MB for 200 elements)
            assert memory_increase < 50 * 1024 * 1024

            # Clean up and verify memory release
            del scene_ir
            gc.collect()

            final_memory = process.memory_info().rss
            memory_after_cleanup = final_memory - initial_memory

            # Should release most memory
            assert memory_after_cleanup < memory_increase / 2

        except (NameError, ImportError):
            pytest.skip("Memory monitoring or SVGParser not available")

    def test_memory_usage_during_policy_evaluation(self):
        """Test memory usage during policy evaluation."""
        try:
            from core.ir import LineSegment, Point, SolidPaint

            process = psutil.Process()
            initial_memory = process.memory_info().rss

            # Create many elements for policy evaluation
            elements = []
            for i in range(100):
                path = Path(
                    segments=[LineSegment(Point(i, 0), Point(i+5, 5))],
                    fill=SolidPaint(color=f"#{i:02x}0000"),
                    stroke=None,
                    is_closed=False,
                    data=f"M {i} 0 L {i+5} 5"
                )
                elements.append(path)

            policy_engine = PolicyEngine()

            # Evaluate policies and measure memory
            decisions = []
            for element in elements:
                decision = policy_engine.evaluate_element(element)
                decisions.append(decision)

            peak_memory = process.memory_info().rss
            memory_increase = peak_memory - initial_memory

            assert len(decisions) == 100
            # Policy evaluation should be memory efficient (< 20MB)
            assert memory_increase < 20 * 1024 * 1024

        except (NameError, ImportError):
            pytest.skip("Memory monitoring or PolicyEngine not available")

    def test_memory_leaks_in_pipeline(self):
        """Test for memory leaks in the pipeline."""
        test_svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
            <rect x="50" y="50" width="100" height="100" fill="#FF0000"/>
            <text x="100" y="170" text-anchor="middle" font-size="16">Leak Test</text>
        </svg>
        '''

        try:
            process = psutil.Process()
            initial_memory = process.memory_info().rss

            parser = SVGParser()
            policy_engine = PolicyEngine()
            scene_mapper = SceneMapper()

            # Run pipeline multiple times
            for iteration in range(50):
                scene_ir = parser.parse_to_ir(test_svg)
                scene_decision = policy_engine.evaluate_element(scene_ir)
                result = scene_mapper.map_scene(scene_ir)

                # Clean up references
                del scene_ir, scene_decision, result

                # Force garbage collection every 10 iterations
                if iteration % 10 == 0:
                    gc.collect()

            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory

            # Should not have significant memory growth (< 10MB)
            assert memory_increase < 10 * 1024 * 1024

        except (NameError, ImportError):
            pytest.skip("Memory monitoring or pipeline components not available")


class TestPipelineQualityMetrics:
    """Quality metrics validation tests."""

    def test_fidelity_quality_metrics(self):
        """Test fidelity quality metrics."""
        try:
            from core.policies import QualityEngine

            # High-detail SVG for fidelity testing
            detailed_svg = '''
            <svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">
                <defs>
                    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" style="stop-color:#FF0000;stop-opacity:1" />
                        <stop offset="50%" style="stop-color:#FFFF00;stop-opacity:1" />
                        <stop offset="100%" style="stop-color:#0000FF;stop-opacity:1" />
                    </linearGradient>
                </defs>

                <!-- Complex curved path -->
                <path d="M 50 150 Q 100 50 150 150 T 250 150" stroke="#000" stroke-width="3" fill="url(#grad1)"/>

                <!-- Detailed text -->
                <text x="150" y="200" text-anchor="middle" font-family="Times New Roman"
                      font-size="18" font-style="italic" fill="#8B4513">High Fidelity</text>

                <!-- Complex shape -->
                <polygon points="150,220 170,260 210,260 180,290 190,340 150,310 110,340 120,290 90,260 130,260"
                         fill="#FFD700" stroke="#FF8C00" stroke-width="2"/>
            </svg>
            '''

            parser = SVGParser()
            scene_ir = parser.parse_to_ir(detailed_svg)

            quality_engine = QualityEngine()
            metrics = quality_engine.evaluate_quality(scene_ir)

            assert metrics is not None

            # Validate fidelity metrics
            if hasattr(metrics, 'fidelity_score'):
                assert 0 <= metrics.fidelity_score <= 100
                # Complex elements should score reasonably high for fidelity potential
                assert metrics.fidelity_score >= 70

            if hasattr(metrics, 'complexity_score'):
                assert metrics.complexity_score >= 50  # Should detect complexity

        except (NameError, ImportError):
            pytest.skip("QualityEngine not available")

    def test_performance_quality_metrics(self):
        """Test performance quality metrics."""
        try:
            from core.policies import QualityEngine

            # Performance-optimized SVG (simple shapes)
            simple_svg = '''
            <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
                <rect x="50" y="50" width="100" height="100" fill="#FF0000"/>
                <circle cx="100" cy="100" r="30" fill="#FFFFFF"/>
                <text x="100" y="170" text-anchor="middle" font-size="14">Simple</text>
            </svg>
            '''

            parser = SVGParser()
            scene_ir = parser.parse_to_ir(simple_svg)

            quality_engine = QualityEngine()
            metrics = quality_engine.evaluate_quality(scene_ir)

            assert metrics is not None

            # Validate performance metrics
            if hasattr(metrics, 'performance_score'):
                assert 0 <= metrics.performance_score <= 100
                # Simple elements should score high for performance
                assert metrics.performance_score >= 80

            if hasattr(metrics, 'rendering_performance_score'):
                assert metrics.rendering_performance_score >= 85

        except (NameError, ImportError):
            pytest.skip("QualityEngine not available")

    def test_compatibility_quality_metrics(self):
        """Test compatibility quality metrics."""
        try:
            from core.policies import QualityEngine

            # Basic SVG with high compatibility
            basic_svg = '''
            <svg xmlns="http://www.w3.org/2000/svg" width="150" height="150" viewBox="0 0 150 150">
                <rect x="25" y="25" width="100" height="100" fill="#008080" stroke="#000000" stroke-width="2"/>
                <text x="75" y="85" text-anchor="middle" font-family="Arial" font-size="16" fill="white">Basic</text>
            </svg>
            '''

            parser = SVGParser()
            scene_ir = parser.parse_to_ir(basic_svg)

            quality_engine = QualityEngine()
            metrics = quality_engine.evaluate_quality(scene_ir)

            assert metrics is not None

            # Validate compatibility metrics
            if hasattr(metrics, 'compatibility_score'):
                assert 0 <= metrics.compatibility_score <= 100
                # Basic elements should have high compatibility
                assert metrics.compatibility_score >= 90

        except (NameError, ImportError):
            pytest.skip("QualityEngine not available")


class TestPipelineStressTests:
    """Stress testing for pipeline robustness."""

    def test_large_element_count_stress(self):
        """Stress test with large number of elements."""
        try:
            # Generate SVG with many elements
            elements = []
            for i in range(500):  # Large number of elements
                if i % 5 == 0:
                    elements.append(f'<rect x="{i*2}" y="{(i*3)%200}" width="8" height="6" fill="#{i%256:02x}{(i*2)%256:02x}{(i*3)%256:02x}"/>')
                elif i % 5 == 1:
                    elements.append(f'<circle cx="{i*2+4}" cy="{(i*3)%200+3}" r="3" fill="#{(i*4)%256:02x}00{(i*5)%256:02x}"/>')
                else:
                    elements.append(f'<text x="{i*2}" y="{(i*3)%200+15}" font-size="8">{i%10}</text>')

            stress_svg = f'''
            <svg xmlns="http://www.w3.org/2000/svg" width="1000" height="600" viewBox="0 0 1000 600">
                {"".join(elements)}
            </svg>
            '''

            # Process with pipeline
            parser = SVGParser()
            start_time = time.time()

            scene_ir = parser.parse_to_ir(stress_svg)
            parse_time = time.time() - start_time

            assert scene_ir is not None
            assert len(scene_ir.elements) >= 400  # Should process most elements
            assert parse_time < 5.0  # Should complete within reasonable time

            # Continue with policy and mapping
            policy_engine = PolicyEngine()
            start_time = time.time()

            scene_decision = policy_engine.evaluate_element(scene_ir)
            policy_time = time.time() - start_time

            assert scene_decision is not None
            assert policy_time < 2.0  # Policy evaluation should be fast

        except NameError:
            pytest.skip("Pipeline components not available")

    def test_deeply_nested_structure_stress(self):
        """Stress test with deeply nested SVG structure."""
        try:
            # Generate deeply nested groups
            nested_svg = '''
            <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
            '''

            # Create 10 levels of nesting
            for level in range(10):
                nested_svg += f'<g transform="translate({level*2}, {level*2}) scale(0.9)">'

            nested_svg += '<rect x="50" y="50" width="100" height="100" fill="#FF0000"/>'

            for level in range(10):
                nested_svg += '</g>'

            nested_svg += '</svg>'

            # Process nested structure
            parser = SVGParser()
            scene_ir = parser.parse_to_ir(nested_svg)

            assert scene_ir is not None
            # Should handle nesting either by flattening or preserving hierarchy

            policy_engine = PolicyEngine()
            scene_decision = policy_engine.evaluate_element(scene_ir)

            assert scene_decision is not None

        except NameError:
            pytest.skip("Pipeline components not available")

    def test_complex_path_data_stress(self):
        """Stress test with complex path data."""
        try:
            # Generate very complex path
            path_commands = ["M 0 100"]

            # Add many curve commands
            for i in range(100):
                path_commands.append(f"Q {i*5} {50 + (i*13)%100} {(i+1)*5} 100")

            path_commands.append("Z")

            complex_path_svg = f'''
            <svg xmlns="http://www.w3.org/2000/svg" width="600" height="200" viewBox="0 0 600 200">
                <path d="{' '.join(path_commands)}" fill="#0000FF" stroke="#000000" stroke-width="1"/>
            </svg>
            '''

            # Process complex path
            parser = SVGParser()
            start_time = time.time()

            scene_ir = parser.parse_to_ir(complex_path_svg)
            parse_time = time.time() - start_time

            assert scene_ir is not None
            assert len(scene_ir.elements) >= 1
            assert parse_time < 1.0  # Should handle complex paths efficiently

            # Test mapping performance
            scene_mapper = SceneMapper()
            start_time = time.time()

            result = scene_mapper.map_scene(scene_ir)
            mapping_time = time.time() - start_time

            assert result is not None
            assert mapping_time < 2.0  # Mapping should be reasonable

        except NameError:
            pytest.skip("Pipeline components not available")


class TestPipelineProductionReadiness:
    """Production readiness validation tests."""

    def test_error_recovery_robustness(self):
        """Test pipeline robustness and error recovery."""
        error_cases = [
            # Malformed XML
            '<svg><rect x="10" y="10" width="50" height="invalid"></svg>',

            # Missing required attributes
            '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="#FF0000"/></svg>',

            # Invalid color values
            '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect x="10" y="10" width="50" height="50" fill="invalid_color"/></svg>',

            # Empty content
            '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"></svg>'
        ]

        try:
            parser = SVGParser()
            policy_engine = PolicyEngine()
            scene_mapper = SceneMapper()

            for i, error_svg in enumerate(error_cases):
                try:
                    # Pipeline should handle errors gracefully
                    scene_ir = parser.parse_to_ir(error_svg)

                    if scene_ir is not None:
                        scene_decision = policy_engine.evaluate_element(scene_ir)

                        if scene_decision is not None:
                            result = scene_mapper.map_scene(scene_ir)
                            assert result is not None

                except (ValueError, TypeError, etree.XMLSyntaxError):
                    # Expected for malformed input
                    pass

        except NameError:
            pytest.skip("Pipeline components not available")

    def test_concurrent_processing_safety(self):
        """Test pipeline safety under concurrent processing."""
        try:
            import threading

            test_svg = '''
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
                <rect x="25" y="25" width="50" height="50" fill="#FF0000"/>
            </svg>
            '''

            parser = SVGParser()
            policy_engine = PolicyEngine()
            scene_mapper = SceneMapper()

            results = []
            errors = []

            def process_svg(thread_id):
                try:
                    scene_ir = parser.parse_to_ir(test_svg)
                    scene_decision = policy_engine.evaluate_element(scene_ir)
                    result = scene_mapper.map_scene(scene_ir)
                    results.append((thread_id, result))
                except Exception as e:
                    errors.append((thread_id, e))

            # Run multiple threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=process_svg, args=(i,))
                threads.append(thread)
                thread.start()

            # Wait for completion
            for thread in threads:
                thread.join()

            # Validate concurrent processing
            assert len(results) == 5
            assert len(errors) == 0

            # All results should be similar
            for thread_id, result in results:
                assert result is not None

        except (NameError, ImportError):
            pytest.skip("Threading or pipeline components not available")

    def test_resource_cleanup_validation(self):
        """Test proper resource cleanup."""
        try:
            import gc

            # Process multiple SVGs and verify cleanup
            test_svgs = [
                '''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
                    <rect x="10" y="10" width="80" height="80" fill="#FF0000"/>
                   </svg>''',
                '''<svg xmlns="http://www.w3.org/2000/svg" width="150" height="150">
                    <circle cx="75" cy="75" r="50" fill="#00FF00"/>
                   </svg>''',
                '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
                    <text x="100" y="100" text-anchor="middle" font-size="16">Test</text>
                   </svg>'''
            ]

            parser = SVGParser()
            policy_engine = PolicyEngine()
            scene_mapper = SceneMapper()

            initial_objects = len(gc.get_objects())

            # Process all SVGs
            for svg_content in test_svgs:
                scene_ir = parser.parse_to_ir(svg_content)
                scene_decision = policy_engine.evaluate_element(scene_ir)
                result = scene_mapper.map_scene(scene_ir)

                # Clear references
                del scene_ir, scene_decision, result

            # Force garbage collection
            gc.collect()

            final_objects = len(gc.get_objects())
            object_growth = final_objects - initial_objects

            # Should not have significant object growth
            assert object_growth < 1000

        except NameError:
            pytest.skip("Pipeline components not available")


if __name__ == "__main__":
    pytest.main([__file__])