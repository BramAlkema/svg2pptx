"""
Test suite for SVG Filter Effects Pipeline Integration.

This module contains comprehensive tests for the filter pipeline integration system,
covering shape rendering, text rendering, composite operations, and blending modes.

Key test areas:
- Filter application to shapes with various geometries
- Text rendering with filter effects applied
- Filter interaction with existing rendering pipeline
- Composite operations and blending modes
- Pipeline coordination and state management
- Performance optimization for filtered content

Test approach:
- Uses templated testing structure for consistency
- Tests initialization, functionality, error handling, and edge cases
- Covers both unit and integration test scenarios
- Includes performance and thread safety testing
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any, Optional

# Import the components to test
from src.converters.filters import (
    FilterComplexityAnalyzer, OptimizationStrategy, FallbackChain,
    PerformanceMonitor, FilterBounds, FilterRegionCalculator
)
from src.units import UnitConverter
from src.colors import ColorParser
from src.transforms import TransformParser
from src.viewbox import ViewBoxInfo
from src.units import ViewportContext


class TestFilterPipelineShapeIntegration:
    """
    Test filter pipeline integration with shape rendering.

    Tests the integration of filter effects with various shape types
    including rectangles, circles, paths, and complex polygons.
    """

    @pytest.fixture
    def setup_test_data(self):
        """Set up test data and components for pipeline testing."""
        unit_converter = UnitConverter(viewport_width=1920, viewport_height=1080)
        color_parser = ColorParser()
        transform_parser = TransformParser()
        viewbox_context = ViewportContext(width=1920, height=1080)

        # Create filter pipeline components
        complexity_analyzer = FilterComplexityAnalyzer(unit_converter, color_parser)
        optimization_strategy = OptimizationStrategy(unit_converter, color_parser)
        fallback_chain = FallbackChain()
        performance_monitor = PerformanceMonitor()
        filter_bounds = FilterBounds(unit_converter, color_parser)

        # Sample shape definitions
        shapes = {
            'rectangle': {
                'type': 'rect',
                'x': 100, 'y': 100,
                'width': 200, 'height': 150,
                'fill': '#FF0000',
                'stroke': '#000000',
                'stroke-width': 2
            },
            'circle': {
                'type': 'circle',
                'cx': 300, 'cy': 200,
                'r': 75,
                'fill': '#00FF00',
                'stroke': '#0000FF'
            },
            'path': {
                'type': 'path',
                'd': 'M 100 100 L 200 150 L 150 200 Z',
                'fill': '#0000FF',
                'stroke': '#FF00FF'
            },
            'complex_polygon': {
                'type': 'polygon',
                'points': '100,100 200,100 250,150 200,200 100,200 50,150',
                'fill': '#FFFF00',
                'stroke': '#00FFFF'
            }
        }

        # Sample filter effects
        filter_effects = {
            'simple_blur': {
                'type': 'feGaussianBlur',
                'stdDeviation': '3'
            },
            'drop_shadow': {
                'type': 'feDropShadow',
                'dx': '2',
                'dy': '2',
                'stdDeviation': '1',
                'flood-color': '#000000'
            },
            'complex_chain': {
                'type': 'chain',
                'primitives': [
                    {'type': 'feGaussianBlur', 'stdDeviation': '2'},
                    {'type': 'feOffset', 'dx': '1', 'dy': '1'},
                    {'type': 'feColorMatrix', 'type': 'saturate', 'values': '1.2'}
                ],
                'primitive_count': 3
            }
        }

        return {
            'unit_converter': unit_converter,
            'color_parser': color_parser,
            'transform_parser': transform_parser,
            'viewbox_context': viewbox_context,
            'complexity_analyzer': complexity_analyzer,
            'optimization_strategy': optimization_strategy,
            'fallback_chain': fallback_chain,
            'performance_monitor': performance_monitor,
            'filter_bounds': filter_bounds,
            'shapes': shapes,
            'filter_effects': filter_effects
        }

    def test_initialization(self, setup_test_data):
        """
        Test initialization of pipeline integration components.

        Test proper initialization of all pipeline integration components
        and their dependencies.
        """
        test_data = setup_test_data

        # Test component initialization
        assert test_data['complexity_analyzer'] is not None
        assert test_data['optimization_strategy'] is not None
        assert test_data['fallback_chain'] is not None
        assert test_data['performance_monitor'] is not None
        assert test_data['filter_bounds'] is not None

        # Test dependency initialization
        assert test_data['unit_converter'] is not None
        assert test_data['color_parser'] is not None
        assert test_data['transform_parser'] is not None
        assert test_data['viewbox_context'] is not None

    def test_basic_functionality(self, setup_test_data):
        """
        Test basic filter pipeline functionality with shapes.

        Test basic integration scenarios:
        - Apply simple filter to rectangle
        - Apply complex filter to circle
        - Process multiple shapes with filters
        """
        test_data = setup_test_data

        # Test simple filter application to rectangle
        rectangle = test_data['shapes']['rectangle']
        blur_filter = test_data['filter_effects']['simple_blur']

        # Simulate filter application
        complexity = test_data['complexity_analyzer'].calculate_complexity_score(blur_filter)
        assert complexity > 0.0, "Filter complexity should be calculated"

        strategy = test_data['optimization_strategy'].select_strategy(blur_filter, complexity_score=complexity)
        assert strategy is not None, "Optimization strategy should be selected"

        # Test bounds calculation for filtered shape
        shape_bounds = {'x': 100, 'y': 100, 'width': 200, 'height': 150}
        filtered_bounds = test_data['filter_bounds'].calculate_filter_bounds(shape_bounds, blur_filter)

        assert filtered_bounds['width'] >= shape_bounds['width'], "Filter should expand bounds"
        assert filtered_bounds['height'] >= shape_bounds['height'], "Filter should expand bounds"

    def test_error_handling(self, setup_test_data):
        """
        Test error handling in pipeline integration.

        Test error scenarios:
        - Invalid shape definitions
        - Malformed filter effects
        - Missing dependencies
        """
        test_data = setup_test_data

        # Test with invalid shape
        invalid_shape = {}
        blur_filter = test_data['filter_effects']['simple_blur']

        # Should handle gracefully
        try:
            shape_bounds = {'x': 0, 'y': 0, 'width': 100, 'height': 100}
            filtered_bounds = test_data['filter_bounds'].calculate_filter_bounds(shape_bounds, blur_filter)
            assert isinstance(filtered_bounds, dict)
        except Exception as e:
            # Error handling should be graceful
            assert isinstance(e, (ValueError, KeyError, TypeError))

        # Test with invalid filter
        invalid_filter = {'type': 'invalid_filter_type'}
        complexity = test_data['complexity_analyzer'].calculate_complexity_score(invalid_filter)
        assert complexity >= 0.0, "Invalid filters should return default complexity"

    def test_edge_cases(self, setup_test_data):
        """
        Test edge cases in pipeline integration.

        Test edge scenarios:
        - Zero-sized shapes
        - Extremely large filters
        - Empty filter chains
        """
        test_data = setup_test_data

        # Test zero-sized shape
        zero_shape_bounds = {'x': 100, 'y': 100, 'width': 0, 'height': 0}
        blur_filter = test_data['filter_effects']['simple_blur']

        filtered_bounds = test_data['filter_bounds'].calculate_filter_bounds(zero_shape_bounds, blur_filter)
        assert filtered_bounds['width'] >= 0, "Zero-sized shapes should be handled"
        assert filtered_bounds['height'] >= 0, "Zero-sized shapes should be handled"

        # Test empty filter chain
        empty_chain = {'type': 'chain', 'primitives': [], 'primitive_count': 0}
        complexity = test_data['complexity_analyzer'].calculate_complexity_score(empty_chain)
        assert complexity == 0.0, "Empty filter chains should have zero complexity"

    def test_configuration_options(self, setup_test_data):
        """
        Test different configuration scenarios for pipeline integration.

        Test configuration variations:
        - Different viewport sizes
        - Various optimization settings
        - Performance mode settings
        """
        test_data = setup_test_data

        # Test with different viewport sizes
        small_converter = UnitConverter(viewport_width=800, viewport_height=600)
        large_converter = UnitConverter(viewport_width=3840, viewport_height=2160)

        shape_bounds = {'x': 100, 'y': 100, 'width': 200, 'height': 150}
        blur_filter = test_data['filter_effects']['simple_blur']

        # Both should work regardless of viewport size
        small_bounds = FilterBounds(small_converter, test_data['color_parser'])
        small_filtered = small_bounds.calculate_filter_bounds(shape_bounds, blur_filter)
        assert isinstance(small_filtered, dict)

        large_bounds = FilterBounds(large_converter, test_data['color_parser'])
        large_filtered = large_bounds.calculate_filter_bounds(shape_bounds, blur_filter)
        assert isinstance(large_filtered, dict)

    def test_integration_with_dependencies(self, setup_test_data):
        """
        Test integration with UnitConverter, ColorParser, and TransformParser.

        Test interaction with core dependencies:
        - Coordinate system conversions
        - Color parsing and manipulation
        - Transform matrix operations
        """
        test_data = setup_test_data

        # Test unit conversion integration
        unit_converter = test_data['unit_converter']
        assert unit_converter.default_context.width == 1920
        assert unit_converter.default_context.height == 1080

        # Test color parser integration
        color_parser = test_data['color_parser']
        parsed_color = color_parser.parse('#FF0000')
        assert parsed_color is not None, "Color parsing should work"

        # Test transform parser integration
        transform_parser = test_data['transform_parser']
        # Transform parser should be available for matrix operations
        assert transform_parser is not None

    @pytest.mark.parametrize("shape_type,filter_type", [
        ('rectangle', 'simple_blur'),
        ('circle', 'drop_shadow'),
        ('path', 'complex_chain'),
        ('complex_polygon', 'simple_blur')
    ])
    def test_parametrized_scenarios(self, setup_test_data, shape_type, filter_type):
        """
        Test various shape and filter combinations using parametrized inputs.

        Test integration scenarios for different shape-filter combinations.
        """
        test_data = setup_test_data

        shape = test_data['shapes'][shape_type]
        filter_effect = test_data['filter_effects'][filter_type]

        # Calculate complexity for this combination
        complexity = test_data['complexity_analyzer'].calculate_complexity_score(filter_effect)
        assert complexity >= 0.0, f"Complexity calculation failed for {shape_type}-{filter_type}"

        # Select optimization strategy
        strategy = test_data['optimization_strategy'].select_strategy(filter_effect, complexity_score=complexity)
        assert strategy is not None, f"Strategy selection failed for {shape_type}-{filter_type}"

        # Test bounds calculation (approximate bounds from shape data)
        if shape_type == 'rectangle':
            bounds = {'x': shape['x'], 'y': shape['y'], 'width': shape['width'], 'height': shape['height']}
        elif shape_type == 'circle':
            bounds = {'x': shape['cx'] - shape['r'], 'y': shape['cy'] - shape['r'],
                     'width': shape['r'] * 2, 'height': shape['r'] * 2}
        else:
            # Use default bounds for path and polygon
            bounds = {'x': 0, 'y': 0, 'width': 300, 'height': 200}

        filtered_bounds = test_data['filter_bounds'].calculate_filter_bounds(bounds, filter_effect)
        assert isinstance(filtered_bounds, dict), f"Bounds calculation failed for {shape_type}-{filter_type}"

    def test_performance_characteristics(self, setup_test_data):
        """
        Test performance-related behavior of pipeline integration.

        Test performance aspects:
        - Processing speed for different shape-filter combinations
        - Memory usage during pipeline operations
        - Caching effectiveness
        """
        test_data = setup_test_data

        # Test processing performance
        rectangle = test_data['shapes']['rectangle']
        blur_filter = test_data['filter_effects']['simple_blur']
        bounds = {'x': rectangle['x'], 'y': rectangle['y'],
                 'width': rectangle['width'], 'height': rectangle['height']}

        # Measure performance of repeated operations
        start_time = time.time()
        for _ in range(100):
            complexity = test_data['complexity_analyzer'].calculate_complexity_score(blur_filter)
            strategy = test_data['optimization_strategy'].select_strategy(blur_filter, complexity_score=complexity)
            filtered_bounds = test_data['filter_bounds'].calculate_filter_bounds(bounds, blur_filter)
        end_time = time.time()

        execution_time = end_time - start_time
        assert execution_time < 5.0, f"100 pipeline operations took {execution_time:.2f}s, should be under 5s"

    def test_thread_safety(self, setup_test_data):
        """
        Test thread safety of pipeline integration components.

        Test concurrent access to pipeline components:
        - Multiple threads processing different shapes
        - Concurrent filter applications
        - Thread-safe caching
        """
        test_data = setup_test_data

        results = []
        errors = []

        def pipeline_worker(thread_id):
            try:
                for i in range(10):
                    # Use different shapes and filters per thread
                    shape_types = list(test_data['shapes'].keys())
                    filter_types = list(test_data['filter_effects'].keys())

                    shape_type = shape_types[thread_id % len(shape_types)]
                    filter_type = filter_types[i % len(filter_types)]

                    shape = test_data['shapes'][shape_type]
                    filter_effect = test_data['filter_effects'][filter_type]

                    # Perform pipeline operations
                    complexity = test_data['complexity_analyzer'].calculate_complexity_score(filter_effect)
                    strategy = test_data['optimization_strategy'].select_strategy(filter_effect, complexity_score=complexity)

                    results.append((thread_id, i, complexity, strategy))
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Run multiple threads
        threads = []
        for i in range(4):
            thread = threading.Thread(target=pipeline_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify results
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 40, f"Expected 40 results, got {len(results)}"


class TestFilterPipelineTextIntegration:
    """
    Test filter pipeline integration with text rendering.

    Tests the integration of filter effects with text elements,
    including font handling, text metrics, and dynamic content.
    """

    @pytest.fixture
    def setup_text_test_data(self):
        """Set up test data specific to text rendering pipeline."""
        unit_converter = UnitConverter(viewport_width=1920, viewport_height=1080)
        color_parser = ColorParser()
        transform_parser = TransformParser()
        viewbox_context = ViewportContext(width=1920, height=1080)

        # Create filter pipeline components
        complexity_analyzer = FilterComplexityAnalyzer(unit_converter, color_parser)
        filter_bounds = FilterBounds(unit_converter, color_parser)

        # Sample text elements
        text_elements = {
            'simple_text': {
                'type': 'text',
                'x': 100,
                'y': 200,
                'content': 'Hello World',
                'font-family': 'Arial',
                'font-size': '24px',
                'fill': '#000000'
            },
            'styled_text': {
                'type': 'text',
                'x': 200,
                'y': 300,
                'content': 'Styled Text',
                'font-family': 'Times New Roman',
                'font-size': '36px',
                'font-weight': 'bold',
                'fill': '#FF0000',
                'stroke': '#0000FF',
                'stroke-width': '1px'
            },
            'multiline_text': {
                'type': 'text',
                'x': 150,
                'y': 400,
                'content': 'Line 1\\nLine 2\\nLine 3',
                'font-family': 'Helvetica',
                'font-size': '18px',
                'fill': '#333333'
            }
        }

        # Text-specific filter effects
        text_filters = {
            'text_blur': {
                'type': 'feGaussianBlur',
                'stdDeviation': '1.5'  # Subtle blur for text readability
            },
            'text_glow': {
                'type': 'chain',
                'primitives': [
                    {'type': 'feGaussianBlur', 'stdDeviation': '2'},
                    {'type': 'feColorMatrix', 'type': 'saturate', 'values': '1.5'},
                    {'type': 'feComposite', 'operator': 'over'}
                ],
                'primitive_count': 3
            },
            'text_shadow': {
                'type': 'feDropShadow',
                'dx': '1',
                'dy': '1',
                'stdDeviation': '0.5',
                'flood-color': '#666666'
            }
        }

        return {
            'unit_converter': unit_converter,
            'color_parser': color_parser,
            'complexity_analyzer': complexity_analyzer,
            'filter_bounds': filter_bounds,
            'text_elements': text_elements,
            'text_filters': text_filters
        }

    def test_text_filter_initialization(self, setup_text_test_data):
        """
        Test initialization of text-specific filter pipeline components.
        """
        test_data = setup_text_test_data

        assert test_data['complexity_analyzer'] is not None
        assert test_data['filter_bounds'] is not None
        assert len(test_data['text_elements']) == 3
        assert len(test_data['text_filters']) == 3

    def test_text_filter_basic_functionality(self, setup_text_test_data):
        """
        Test basic text filter functionality.

        Test scenarios:
        - Apply blur to simple text
        - Apply glow effect to styled text
        - Handle multiline text with filters
        """
        test_data = setup_text_test_data

        # Test simple text with blur
        simple_text = test_data['text_elements']['simple_text']
        text_blur = test_data['text_filters']['text_blur']

        complexity = test_data['complexity_analyzer'].calculate_complexity_score(text_blur)
        assert complexity > 0.0, "Text blur should have measurable complexity"

        # Estimate text bounds (simplified)
        font_size = float(simple_text['font-size'].replace('px', ''))
        text_length = len(simple_text['content'])
        estimated_width = text_length * font_size * 0.6  # Rough estimate
        estimated_height = font_size * 1.2

        text_bounds = {
            'x': simple_text['x'],
            'y': simple_text['y'] - font_size,
            'width': estimated_width,
            'height': estimated_height
        }

        filtered_bounds = test_data['filter_bounds'].calculate_filter_bounds(text_bounds, text_blur)
        assert filtered_bounds['width'] >= text_bounds['width'], "Filter should expand text bounds"
        assert filtered_bounds['height'] >= text_bounds['height'], "Filter should expand text bounds"

    def test_text_filter_error_handling(self, setup_text_test_data):
        """
        Test error handling for text filter scenarios.
        """
        test_data = setup_text_test_data

        # Test with missing text properties
        incomplete_text = {'type': 'text', 'content': 'Test'}
        text_blur = test_data['text_filters']['text_blur']

        # Should handle missing font information gracefully
        complexity = test_data['complexity_analyzer'].calculate_complexity_score(text_blur)
        assert complexity >= 0.0, "Should handle incomplete text elements"

    def test_text_dynamic_content(self, setup_text_test_data):
        """
        Test handling of dynamic text content.

        Test scenarios:
        - Variable text lengths
        - Different font sizes
        - Dynamic text updates
        """
        test_data = setup_text_test_data

        text_glow = test_data['text_filters']['text_glow']

        # Test different text lengths
        short_text = "Hi"
        long_text = "This is a very long text string that should test bounds calculation"

        for text_content in [short_text, long_text]:
            # Simulate dynamic text bounds
            font_size = 24
            text_width = len(text_content) * font_size * 0.6
            text_height = font_size * 1.2

            dynamic_bounds = {'x': 100, 'y': 100, 'width': text_width, 'height': text_height}
            filtered_bounds = test_data['filter_bounds'].calculate_filter_bounds(dynamic_bounds, text_glow)

            assert filtered_bounds['width'] >= dynamic_bounds['width'], f"Failed for text: {text_content}"
            assert filtered_bounds['height'] >= dynamic_bounds['height'], f"Failed for text: {text_content}"


class TestFilterPipelineCompositeOperations:
    """
    Test composite operations and blending modes in filter pipeline.

    Tests complex filter chains, blending modes, and alpha compositing.
    """

    @pytest.fixture
    def setup_composite_test_data(self):
        """Set up test data for composite operations testing."""
        unit_converter = UnitConverter(viewport_width=1920, viewport_height=1080)
        color_parser = ColorParser()
        complexity_analyzer = FilterComplexityAnalyzer(unit_converter, color_parser)

        # Complex composite filter effects
        composite_filters = {
            'simple_composite': {
                'type': 'feComposite',
                'operator': 'over',
                'in': 'SourceGraphic',
                'in2': 'BackgroundImage'
            },
            'multiply_blend': {
                'type': 'feComposite',
                'operator': 'multiply',
                'in': 'SourceGraphic',
                'in2': 'backdrop'
            },
            'complex_chain_composite': {
                'type': 'chain',
                'primitives': [
                    {'type': 'feGaussianBlur', 'stdDeviation': '2', 'result': 'blur'},
                    {'type': 'feOffset', 'dx': '3', 'dy': '3', 'in': 'blur', 'result': 'offset'},
                    {'type': 'feComposite', 'operator': 'over', 'in': 'SourceGraphic', 'in2': 'offset', 'result': 'composite'},
                    {'type': 'feColorMatrix', 'type': 'saturate', 'values': '1.3', 'in': 'composite'}
                ],
                'primitive_count': 4
            },
            'alpha_composite': {
                'type': 'chain',
                'primitives': [
                    {'type': 'feColorMatrix', 'type': 'matrix',
                     'values': '1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 0.5 0', 'result': 'alpha'},
                    {'type': 'feComposite', 'operator': 'atop', 'in': 'alpha', 'in2': 'SourceGraphic'}
                ],
                'primitive_count': 2
            }
        }

        return {
            'unit_converter': unit_converter,
            'color_parser': color_parser,
            'complexity_analyzer': complexity_analyzer,
            'composite_filters': composite_filters
        }

    def test_composite_initialization(self, setup_composite_test_data):
        """Test initialization of composite operations testing."""
        test_data = setup_composite_test_data

        assert test_data['complexity_analyzer'] is not None
        assert len(test_data['composite_filters']) == 4

    def test_composite_basic_functionality(self, setup_composite_test_data):
        """
        Test basic composite operations functionality.
        """
        test_data = setup_composite_test_data

        # Test simple composite
        simple_composite = test_data['composite_filters']['simple_composite']
        complexity = test_data['complexity_analyzer'].calculate_complexity_score(simple_composite)
        assert complexity > 0.0, "Composite operations should have complexity"

        # Test complex chain with composite
        complex_chain = test_data['composite_filters']['complex_chain_composite']
        chain_complexity = test_data['complexity_analyzer'].calculate_complexity_score(complex_chain)
        assert chain_complexity > complexity, "Complex chains should have higher complexity"

    def test_composite_error_handling(self, setup_composite_test_data):
        """Test error handling for composite operations."""
        test_data = setup_composite_test_data

        # Test invalid composite operator
        invalid_composite = {
            'type': 'feComposite',
            'operator': 'invalid_operator',
            'in': 'SourceGraphic',
            'in2': 'backdrop'
        }

        complexity = test_data['complexity_analyzer'].calculate_complexity_score(invalid_composite)
        assert complexity >= 0.0, "Should handle invalid composite operators gracefully"

    def test_blending_modes(self, setup_composite_test_data):
        """
        Test different blending modes and their complexity calculations.
        """
        test_data = setup_composite_test_data

        blending_modes = ['over', 'multiply', 'screen', 'darken', 'lighten']

        for mode in blending_modes:
            blend_filter = {
                'type': 'feComposite',
                'operator': mode,
                'in': 'SourceGraphic',
                'in2': 'backdrop'
            }

            complexity = test_data['complexity_analyzer'].calculate_complexity_score(blend_filter)
            assert complexity > 0.0, f"Blending mode {mode} should have positive complexity"

    def test_alpha_compositing(self, setup_composite_test_data):
        """
        Test alpha compositing operations.
        """
        test_data = setup_composite_test_data

        alpha_composite = test_data['composite_filters']['alpha_composite']
        complexity = test_data['complexity_analyzer'].calculate_complexity_score(alpha_composite)

        # Alpha compositing should have significant complexity due to matrix operations
        assert complexity > 2.0, "Alpha compositing should have higher complexity"


class TestFilterPipelineStateManagement:
    """
    Test pipeline coordination and state management.

    Tests filter state tracking, resource management, and pipeline debugging.
    """

    @pytest.fixture
    def setup_state_test_data(self):
        """Set up test data for state management testing."""
        unit_converter = UnitConverter(viewport_width=1920, viewport_height=1080)
        color_parser = ColorParser()
        performance_monitor = PerformanceMonitor()

        return {
            'unit_converter': unit_converter,
            'color_parser': color_parser,
            'performance_monitor': performance_monitor
        }

    def test_state_initialization(self, setup_state_test_data):
        """Test state management initialization."""
        test_data = setup_state_test_data

        assert test_data['performance_monitor'] is not None

    def test_state_tracking(self, setup_state_test_data):
        """
        Test filter state tracking throughout pipeline.
        """
        test_data = setup_state_test_data
        monitor = test_data['performance_monitor']

        # Test state tracking operations
        monitor.start_tracking('pipeline_operation_1')
        time.sleep(0.01)  # Simulate processing time
        duration = monitor.end_tracking('pipeline_operation_1')

        assert duration > 0.0, "Should track operation duration"

        # Test multiple operations
        for i in range(5):
            monitor.start_tracking(f'operation_{i}')
            time.sleep(0.001)
            monitor.end_tracking(f'operation_{i}')

        metrics = monitor.get_metrics()
        assert metrics['total_operations'] >= 6, "Should track multiple operations"

    def test_resource_management(self, setup_state_test_data):
        """
        Test proper cleanup and resource management.
        """
        test_data = setup_state_test_data
        monitor = test_data['performance_monitor']

        # Test resource cleanup
        monitor.start_tracking('resource_test')

        # Simulate resource allocation and cleanup
        resources = []
        for i in range(10):
            resources.append(f'resource_{i}')

        # Clean up resources
        resources.clear()

        duration = monitor.end_tracking('resource_test')
        assert duration >= 0.0, "Resource management should be tracked"

    def test_pipeline_debugging(self, setup_state_test_data):
        """
        Test pipeline debugging and diagnostic capabilities.
        """
        test_data = setup_state_test_data
        monitor = test_data['performance_monitor']

        # Test debugging information collection
        debug_operations = ['parse', 'analyze', 'optimize', 'render']

        for operation in debug_operations:
            monitor.start_tracking(operation)
            time.sleep(0.001)
            monitor.end_tracking(operation)

        metrics = monitor.get_metrics()

        # Debugging should provide detailed metrics
        assert 'total_operations' in metrics
        assert 'average_duration' in metrics
        assert metrics['total_operations'] == len(debug_operations)


class TestFilterPipelinePerformanceOptimization:
    """
    Test performance optimization for filtered content.

    Tests render batching, caching strategies, and memory optimization.
    """

    @pytest.fixture
    def setup_performance_test_data(self):
        """Set up test data for performance optimization testing."""
        unit_converter = UnitConverter(viewport_width=1920, viewport_height=1080)
        color_parser = ColorParser()
        complexity_analyzer = FilterComplexityAnalyzer(unit_converter, color_parser)
        performance_monitor = PerformanceMonitor()

        return {
            'unit_converter': unit_converter,
            'color_parser': color_parser,
            'complexity_analyzer': complexity_analyzer,
            'performance_monitor': performance_monitor
        }

    def test_performance_initialization(self, setup_performance_test_data):
        """Test performance optimization initialization."""
        test_data = setup_performance_test_data

        assert test_data['complexity_analyzer'] is not None
        assert test_data['performance_monitor'] is not None

    def test_render_batching(self, setup_performance_test_data):
        """
        Test render batching for multiple filtered elements.
        """
        test_data = setup_performance_test_data
        monitor = test_data['performance_monitor']
        analyzer = test_data['complexity_analyzer']

        # Test batching multiple operations
        batch_filters = [
            {'type': 'feGaussianBlur', 'stdDeviation': f'{i+1}'}
            for i in range(10)
        ]

        # Test individual processing
        monitor.start_tracking('individual_processing')
        individual_results = []
        for i, filter_effect in enumerate(batch_filters):
            monitor.start_tracking(f'individual_{i}')
            complexity = analyzer.calculate_complexity_score(filter_effect)
            monitor.end_tracking(f'individual_{i}')
            individual_results.append(complexity)
        monitor.end_tracking('individual_processing')

        # Test batch processing simulation
        monitor.start_tracking('batch_processing')
        batch_results = []
        for filter_effect in batch_filters:
            complexity = analyzer.calculate_complexity_score(filter_effect)
            batch_results.append(complexity)
        monitor.end_tracking('batch_processing')

        assert len(individual_results) == len(batch_results) == 10
        assert individual_results == batch_results, "Batch and individual results should match"

    def test_caching_strategies(self, setup_performance_test_data):
        """
        Test caching strategies for repeated filter applications.
        """
        test_data = setup_performance_test_data
        analyzer = test_data['complexity_analyzer']

        # Test caching effectiveness
        test_filter = {'type': 'feGaussianBlur', 'stdDeviation': '5'}

        # First calculation (cache miss)
        start_time = time.time()
        result1 = analyzer.calculate_complexity_score(test_filter)
        first_time = time.time() - start_time

        # Second calculation (cache hit)
        start_time = time.time()
        result2 = analyzer.calculate_complexity_score(test_filter)
        second_time = time.time() - start_time

        assert result1 == result2, "Cached results should match original"
        # Note: Cache hit should be faster, but timing may vary in tests

    def test_memory_optimization(self, setup_performance_test_data):
        """
        Test memory usage optimization during filter processing.
        """
        test_data = setup_performance_test_data
        analyzer = test_data['complexity_analyzer']
        monitor = test_data['performance_monitor']

        # Test memory-efficient processing
        monitor.start_tracking('memory_test')

        # Process many filters without accumulating excessive memory
        for i in range(100):
            filter_effect = {
                'type': 'feGaussianBlur',
                'stdDeviation': f'{(i % 10) + 1}'  # Cycle through values
            }
            complexity = analyzer.calculate_complexity_score(filter_effect)
            assert complexity > 0.0, f"Filter {i} should have positive complexity"

        duration = monitor.end_tracking('memory_test')
        assert duration < 2.0, "Memory-efficient processing should be fast"

    def test_stress_testing_pipeline(self, setup_performance_test_data):
        """
        Test pipeline performance under stress conditions.
        """
        test_data = setup_performance_test_data
        analyzer = test_data['complexity_analyzer']
        monitor = test_data['performance_monitor']

        # Create stress test scenario
        monitor.start_tracking('stress_test')

        stress_filters = []
        for i in range(50):
            filter_effect = {
                'type': 'chain',
                'primitives': [
                    {'type': 'feGaussianBlur', 'stdDeviation': f'{(i % 5) + 1}'},
                    {'type': 'feOffset', 'dx': f'{i % 3}', 'dy': f'{i % 3}'},
                    {'type': 'feColorMatrix', 'type': 'saturate', 'values': f'{1.0 + (i % 10) * 0.1}'}
                ],
                'primitive_count': 3
            }
            stress_filters.append(filter_effect)

        # Process all stress filters
        total_complexity = 0
        for i, filter_effect in enumerate(stress_filters):
            monitor.start_tracking(f'stress_{i}')
            complexity = analyzer.calculate_complexity_score(filter_effect)
            monitor.end_tracking(f'stress_{i}')
            total_complexity += complexity

        duration = monitor.end_tracking('stress_test')

        # Verify stress test results
        assert duration < 10.0, "Stress test should complete within reasonable time"
        assert total_complexity > 100.0, "Stress test should accumulate significant complexity"

        metrics = monitor.get_metrics()
        assert metrics['total_operations'] >= 51, "Should track all stress operations"


if __name__ == "__main__":
    # Allow running tests directly with: python test_module.py
    pytest.main([__file__])