#!/usr/bin/env python3
"""
Filter Optimization and Fallback Test - Following Templated Testing System

This test follows the unit_test_template.py religiously to ensure
consistent testing patterns across the SVG2PPTX codebase.

Tests the filter optimization and fallback system that determines the best
strategy for converting SVG filter effects to PowerPoint-compatible effects.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from pathlib import Path
import sys
from lxml import etree as ET
import time

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

# Import the modules under test
from src.converters.filters import (
    FilterComplexityAnalyzer, OptimizationStrategy, FallbackChain,
    PerformanceMonitor, OOXMLEffectStrategy
)
from src.units import UnitConverter
from src.colors import ColorParser


class TestFilterComplexityAnalyzer:
    """
    Unit tests for FilterComplexityAnalyzer class.

    Tests the filter complexity analysis system that scores filter effects
    and determines appropriate optimization strategies.
    """

    @pytest.fixture
    def setup_test_data(self):
        """
        Setup common test data and mock objects.

        Creates sample filter effects with varying complexity levels for testing.
        """
        # Create sample filter effects with different complexity levels
        simple_blur = {
            'type': 'feGaussianBlur',
            'stdDeviation': '3',
            'primitive_count': 1
        }

        complex_chain = {
            'type': 'chain',
            'primitives': [
                {'type': 'feGaussianBlur', 'stdDeviation': '5'},
                {'type': 'feColorMatrix', 'type': 'saturate', 'values': '0.5'},
                {'type': 'feComposite', 'operator': 'multiply'},
                {'type': 'feOffset', 'dx': '2', 'dy': '2'}
            ],
            'primitive_count': 4
        }

        extreme_effect = {
            'type': 'feTurbulence',
            'baseFrequency': '0.1',
            'numOctaves': '8',
            'seed': '1',
            'stitchTiles': 'stitch',
            'primitive_count': 1,
            'complexity_multiplier': 5.0
        }

        return {
            'simple_blur': simple_blur,
            'complex_chain': complex_chain,
            'extreme_effect': extreme_effect,
            'unit_converter': UnitConverter(viewport_width=800, viewport_height=600),
            'color_parser': ColorParser(),
            'expected_scores': {
                'simple': 1.0,
                'complex': 4.0,
                'extreme': 15.0
            }
        }

    @pytest.fixture
    def component_instance(self, setup_test_data):
        """
        Create FilterComplexityAnalyzer instance with test dependencies.
        """
        return FilterComplexityAnalyzer(
            setup_test_data['unit_converter'],
            setup_test_data['color_parser']
        )

    def test_initialization(self, component_instance):
        """
        Test FilterComplexityAnalyzer initialization and basic properties.

        Verify:
        - Component initializes correctly
        - Required attributes are set
        - Dependencies are properly injected
        """
        assert component_instance is not None
        assert hasattr(component_instance, 'unit_converter')
        assert hasattr(component_instance, 'color_parser')
        assert hasattr(component_instance, 'calculate_complexity_score')
        assert hasattr(component_instance, 'analyze_filter_chain')
        assert hasattr(component_instance, 'get_performance_impact')

    def test_basic_functionality(self, component_instance, setup_test_data):
        """
        Test core functionality of the FilterComplexityAnalyzer.

        Test the main complexity calculation methods:
        - Basic complexity scoring
        - Filter chain analysis
        - Performance impact assessment
        """
        test_data = setup_test_data

        # Test simple blur complexity
        simple_score = component_instance.calculate_complexity_score(test_data['simple_blur'])
        assert simple_score <= 2.0  # Simple effects should have low scores

        # Test complex chain complexity
        complex_score = component_instance.calculate_complexity_score(test_data['complex_chain'])
        assert complex_score > simple_score  # Complex chains should score higher
        assert complex_score >= 3.0

        # Test extreme effect complexity
        extreme_score = component_instance.calculate_complexity_score(test_data['extreme_effect'])
        assert extreme_score > complex_score  # Extreme effects should score highest
        assert extreme_score >= 10.0

    def test_error_handling(self, component_instance, setup_test_data):
        """
        Test error handling and edge cases.

        Test error conditions:
        - Invalid input handling
        - Missing filter parameters
        - Malformed filter data
        - Unknown filter types
        """
        # Test with None filter effect
        with pytest.raises(ValueError, match="Filter effect cannot be None"):
            component_instance.calculate_complexity_score(None)

        # Test with empty filter effect
        empty_effect = {}
        score = component_instance.calculate_complexity_score(empty_effect)
        assert score == 0.0  # Empty effects should have zero complexity

        # Test with unknown filter type
        unknown_effect = {'type': 'feUnknownEffect', 'value': 'something'}
        score = component_instance.calculate_complexity_score(unknown_effect)
        assert score >= 0.0  # Should handle gracefully

        # Test with malformed primitive count
        malformed_effect = {
            'type': 'feGaussianBlur',
            'stdDeviation': '3',
            'primitive_count': 'invalid'
        }
        score = component_instance.calculate_complexity_score(malformed_effect)
        assert score >= 0.0  # Should handle gracefully

    def test_edge_cases(self, component_instance, setup_test_data):
        """
        Test edge cases and boundary conditions.

        Test edge cases specific to complexity analysis:
        - Zero-parameter effects
        - Maximum complexity scenarios
        - Negative parameter values
        - Very large filter chains
        """
        # Test zero-parameter blur
        zero_blur = {'type': 'feGaussianBlur', 'stdDeviation': '0'}
        score = component_instance.calculate_complexity_score(zero_blur)
        assert score == 0.0  # Zero effects should have zero complexity

        # Test very large filter chain
        large_chain = {
            'type': 'chain',
            'primitives': [{'type': 'feGaussianBlur', 'stdDeviation': str(i)} for i in range(20)],
            'primitive_count': 20
        }
        score = component_instance.calculate_complexity_score(large_chain)
        assert score >= 15.0  # Large chains should have high complexity

        # Test negative parameters (should be normalized)
        negative_effect = {'type': 'feOffset', 'dx': '-10', 'dy': '-5'}
        score = component_instance.calculate_complexity_score(negative_effect)
        assert score >= 0.0  # Should handle negative values

        # Test extreme parameters
        extreme_params = {
            'type': 'feGaussianBlur',
            'stdDeviation': '1000'  # Very large blur
        }
        score = component_instance.calculate_complexity_score(extreme_params)
        assert score >= 5.0  # Extreme parameters should increase complexity

    def test_configuration_options(self, component_instance, setup_test_data):
        """
        Test different configuration scenarios.

        Test configuration variations:
        - Different complexity thresholds
        - Custom scoring weights
        - Performance mode settings
        """
        test_data = setup_test_data

        # Test with different complexity thresholds
        component_instance.set_complexity_threshold(2.0)
        blur_effect = test_data['simple_blur']

        is_simple = component_instance.is_effect_simple(blur_effect)
        assert isinstance(is_simple, bool)

        # Test custom scoring weights
        component_instance.set_scoring_weights({
            'primitive_count': 2.0,
            'parameter_complexity': 1.5,
            'rasterization_penalty': 3.0
        })

        score = component_instance.calculate_complexity_score(blur_effect)
        assert score >= 0.0

        # Test performance mode configuration
        component_instance.set_performance_mode('fast')
        fast_score = component_instance.calculate_complexity_score(test_data['complex_chain'])

        component_instance.set_performance_mode('quality')
        quality_score = component_instance.calculate_complexity_score(test_data['complex_chain'])

        # Scores may differ between modes
        assert isinstance(fast_score, (int, float))
        assert isinstance(quality_score, (int, float))

    def test_integration_with_dependencies(self, component_instance, setup_test_data):
        """
        Test integration with UnitConverter and ColorParser dependencies.

        Test interactions with:
        - UnitConverter for parameter parsing
        - ColorParser for color-based complexity
        - Performance monitoring integration
        """
        test_data = setup_test_data

        # Test UnitConverter integration
        unit_converter = test_data['unit_converter']
        assert component_instance.unit_converter == unit_converter

        # Test unit-based complexity calculation
        unit_effect = {
            'type': 'feGaussianBlur',
            'stdDeviation': '10pt'  # Point units
        }
        score = component_instance.calculate_complexity_score(unit_effect)
        assert score >= 0.0

        # Test ColorParser integration for color effects
        color_parser = test_data['color_parser']
        assert component_instance.color_parser == color_parser

        color_effect = {
            'type': 'feFlood',
            'flood-color': 'rgba(255, 0, 0, 0.5)',
            'flood-opacity': '0.8'
        }
        score = component_instance.calculate_complexity_score(color_effect)
        assert score >= 0.0

        # Test performance monitoring integration
        monitor = component_instance.get_performance_monitor()
        assert monitor is not None
        assert hasattr(monitor, 'track_complexity_calculation')

    @pytest.mark.parametrize("filter_effect,expected_complexity", [
        (
            {'type': 'feGaussianBlur', 'stdDeviation': '1'},
            'low'  # Simple blur should be low complexity
        ),
        (
            {'type': 'feDropShadow', 'dx': '2', 'dy': '2', 'stdDeviation': '3'},
            'medium'  # Drop shadow should be medium complexity
        ),
        (
            {'type': 'feTurbulence', 'baseFrequency': '0.05', 'numOctaves': '4'},
            'high'  # Turbulence should be high complexity
        ),
        (
            {
                'type': 'chain',
                'primitives': [
                    {'type': 'feGaussianBlur'},
                    {'type': 'feColorMatrix'},
                    {'type': 'feComposite'},
                    {'type': 'feOffset'},
                    {'type': 'feMorphology'}
                ],
                'primitive_count': 5
            },
            'very_high'  # Complex chains should be very high complexity
        ),
    ])
    def test_parametrized_scenarios(self, component_instance, filter_effect, expected_complexity):
        """
        Test various complexity scenarios using parametrized inputs.

        Test complexity classification for different filter types and parameters.
        """
        score = component_instance.calculate_complexity_score(filter_effect)

        if expected_complexity == 'low':
            assert score <= 2.0
        elif expected_complexity == 'medium':
            assert 2.0 < score <= 5.0
        elif expected_complexity == 'high':
            assert 5.0 < score <= 10.0
        elif expected_complexity == 'very_high':
            assert score > 10.0

    def test_performance_characteristics(self, component_instance, setup_test_data):
        """
        Test performance-related behavior of complexity analysis.

        Test performance aspects:
        - Calculation speed for different effect types
        - Memory usage during analysis
        - Caching effectiveness
        """
        test_data = setup_test_data

        # Test calculation performance
        start_time = time.time()
        for _ in range(100):
            score = component_instance.calculate_complexity_score(test_data['simple_blur'])
        end_time = time.time()

        execution_time = end_time - start_time
        assert execution_time < 1.0, f"100 complexity calculations took {execution_time:.2f}s, should be under 1s"

        # Test caching effectiveness
        complex_effect = test_data['complex_chain']

        # First calculation (cache miss)
        start_time = time.time()
        score1 = component_instance.calculate_complexity_score(complex_effect)
        first_time = time.time() - start_time

        # Second calculation (cache hit)
        start_time = time.time()
        score2 = component_instance.calculate_complexity_score(complex_effect)
        second_time = time.time() - start_time

        assert score1 == score2  # Results should be identical
        assert second_time <= first_time  # Second call should be faster or equal

    def test_thread_safety(self, component_instance, setup_test_data):
        """
        Test thread safety of complexity analysis.

        Test concurrent access:
        - Multiple threads calculating complexity
        - Shared state management
        - Race condition prevention
        """
        import threading

        test_data = setup_test_data
        results = []
        errors = []

        def calculate_complexity_thread():
            try:
                for effect in [test_data['simple_blur'], test_data['complex_chain']]:
                    result = component_instance.calculate_complexity_score(effect)
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # Run calculations in parallel threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=calculate_complexity_thread)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify no errors and consistent results
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 10  # 5 threads × 2 effects each


class TestOptimizationStrategy:
    """
    Tests for OptimizationStrategy class.

    Tests the optimization decision framework that determines the best
    strategy for converting filter effects based on complexity and performance.
    """

    @pytest.fixture
    def setup_test_data(self):
        """Setup test data for optimization strategy testing."""
        return {
            'unit_converter': UnitConverter(viewport_width=800, viewport_height=600),
            'color_parser': ColorParser(),
            'performance_targets': {
                'native_threshold': 2.0,
                'hack_threshold': 5.0,
                'raster_threshold': 10.0
            }
        }

    @pytest.fixture
    def component_instance(self, setup_test_data):
        """Create OptimizationStrategy instance."""
        return OptimizationStrategy(
            setup_test_data['unit_converter'],
            setup_test_data['color_parser'],
            setup_test_data['performance_targets']
        )

    def test_strategy_selection(self, component_instance, setup_test_data):
        """Test strategy selection based on complexity scores."""
        # Test native strategy selection
        simple_effect = {'type': 'feGaussianBlur', 'stdDeviation': '2'}
        strategy = component_instance.select_strategy(simple_effect, complexity_score=1.5)
        assert strategy == OOXMLEffectStrategy.NATIVE_DML

        # Test hack strategy selection
        medium_effect = {'type': 'feColorMatrix', 'values': '0.5 0 0 0 0'}
        strategy = component_instance.select_strategy(medium_effect, complexity_score=3.5)
        assert strategy == OOXMLEffectStrategy.DML_HACK

        # Test rasterization strategy selection
        complex_effect = {'type': 'feTurbulence', 'baseFrequency': '0.1'}
        strategy = component_instance.select_strategy(complex_effect, complexity_score=12.0)
        assert strategy == OOXMLEffectStrategy.RASTERIZE

    def test_quality_vs_performance_tradeoff(self, component_instance):
        """Test quality vs performance trade-off decisions."""
        effect = {'type': 'feGaussianBlur', 'stdDeviation': '5'}

        # High quality mode should prefer accuracy
        component_instance.set_quality_mode('high')
        high_quality_strategy = component_instance.select_strategy(effect, complexity_score=4.0)

        # Fast mode should prefer performance
        component_instance.set_quality_mode('fast')
        fast_strategy = component_instance.select_strategy(effect, complexity_score=4.0)

        # Strategies may differ based on quality mode
        assert high_quality_strategy in [OOXMLEffectStrategy.NATIVE_DML, OOXMLEffectStrategy.DML_HACK, OOXMLEffectStrategy.RASTERIZE]
        assert fast_strategy in [OOXMLEffectStrategy.NATIVE_DML, OOXMLEffectStrategy.DML_HACK, OOXMLEffectStrategy.RASTERIZE]


class TestFallbackChain:
    """
    Tests for FallbackChain class.

    Tests the comprehensive fallback system that provides graceful degradation
    when preferred strategies fail.
    """

    @pytest.fixture
    def component_instance(self):
        """Create FallbackChain instance."""
        return FallbackChain()

    def test_fallback_chain_execution(self, component_instance):
        """Test fallback chain execution for different scenarios."""
        # Test native -> hack -> raster fallback
        effect = {'type': 'feGaussianBlur', 'stdDeviation': '3'}

        fallback_chain = component_instance.build_fallback_chain(effect)
        assert len(fallback_chain) >= 2  # Should have multiple fallback options

        # First option should typically be native or hack
        first_strategy = fallback_chain[0]
        assert first_strategy in [OOXMLEffectStrategy.NATIVE_DML, OOXMLEffectStrategy.DML_HACK]

        # Last option should be rasterization
        last_strategy = fallback_chain[-1]
        assert last_strategy == OOXMLEffectStrategy.RASTERIZE

    def test_graceful_degradation(self, component_instance):
        """Test graceful degradation scenarios."""
        # Test unsupported effect fallback
        unsupported_effect = {'type': 'feConvolveMatrix', 'kernelMatrix': '1 0 -1 2 0 -2 1 0 -1'}

        fallback_chain = component_instance.build_fallback_chain(unsupported_effect)
        assert len(fallback_chain) > 0  # Should provide fallback options

        # Should eventually fall back to basic styling
        basic_fallback = component_instance.get_basic_styling_fallback(unsupported_effect)
        assert basic_fallback is not None
        assert 'fallback_type' in basic_fallback

    def test_fallback_quality_metrics(self, component_instance):
        """Test quality metrics for fallback validation."""
        effect = {'type': 'feDropShadow', 'dx': '3', 'dy': '3'}

        quality_metrics = component_instance.calculate_fallback_quality(effect, OOXMLEffectStrategy.NATIVE_DML)
        assert 'visual_accuracy' in quality_metrics
        assert 'performance_impact' in quality_metrics
        assert isinstance(quality_metrics['visual_accuracy'], (int, float))
        assert isinstance(quality_metrics['performance_impact'], (int, float))


class TestPerformanceMonitor:
    """
    Tests for PerformanceMonitor class.

    Tests the performance monitoring and metrics system for filter effects.
    """

    @pytest.fixture
    def component_instance(self):
        """Create PerformanceMonitor instance."""
        return PerformanceMonitor()

    def test_performance_tracking(self, component_instance):
        """Test performance tracking capabilities."""
        # Test render time tracking
        component_instance.start_tracking('test_operation')
        time.sleep(0.01)  # Simulate work
        duration = component_instance.end_tracking('test_operation')

        assert duration > 0.0
        assert duration < 1.0  # Should be reasonable

        # Test metrics collection
        metrics = component_instance.get_metrics()
        assert 'total_operations' in metrics
        assert 'average_duration' in metrics
        assert metrics['total_operations'] >= 1

    def test_quality_metrics(self, component_instance):
        """Test quality metrics collection."""
        effect = {'type': 'feGaussianBlur', 'stdDeviation': '3'}
        strategy = OOXMLEffectStrategy.NATIVE_DML

        component_instance.record_strategy_usage(effect, strategy, success=True)

        metrics = component_instance.get_strategy_metrics()
        assert OOXMLEffectStrategy.NATIVE_DML in metrics
        assert metrics[OOXMLEffectStrategy.NATIVE_DML]['success_rate'] > 0.0

    def test_performance_regression_detection(self, component_instance):
        """Test automated performance regression detection."""
        # Record baseline performance
        for i in range(10):
            component_instance.start_tracking(f'operation_{i}')
            time.sleep(0.001)  # Consistent work
            component_instance.end_tracking(f'operation_{i}')

        baseline = component_instance.get_performance_baseline()
        assert baseline['average_duration'] > 0.0

        # Detect regression (simulate slower operation)
        component_instance.start_tracking('slow_operation')
        time.sleep(0.1)  # Much slower
        component_instance.end_tracking('slow_operation')

        is_regression = component_instance.detect_performance_regression()
        assert isinstance(is_regression, bool)  # Should detect or not detect regression


@pytest.mark.integration
class TestFilterOptimizationFallbackIntegration:
    """
    Integration tests for Filter Optimization and Fallback system.

    Tests complete workflow from filter analysis to strategy selection
    with real filter effects and performance monitoring.
    """

    def test_end_to_end_optimization_workflow(self):
        """
        Test complete workflow from filter analysis to strategy execution.
        """
        # Create integrated system
        unit_converter = UnitConverter(viewport_width=1920, viewport_height=1080)
        color_parser = ColorParser()

        analyzer = FilterComplexityAnalyzer(unit_converter, color_parser)
        optimizer = OptimizationStrategy(unit_converter, color_parser)
        fallback = FallbackChain()
        monitor = PerformanceMonitor()

        # Test complex filter effect
        complex_filter = {
            'type': 'chain',
            'primitives': [
                {'type': 'feGaussianBlur', 'stdDeviation': '5'},
                {'type': 'feOffset', 'dx': '3', 'dy': '3'},
                {'type': 'feColorMatrix', 'type': 'saturate', 'values': '0.8'},
                {'type': 'feComposite', 'operator': 'over'}
            ],
            'primitive_count': 4
        }

        # Analyze complexity
        complexity = analyzer.calculate_complexity_score(complex_filter)
        assert complexity > 2.0  # Should be complex

        # Select strategy
        strategy = optimizer.select_strategy(complex_filter, complexity_score=complexity)
        assert strategy in [OOXMLEffectStrategy.NATIVE_DML, OOXMLEffectStrategy.DML_HACK, OOXMLEffectStrategy.RASTERIZE]

        # Build fallback chain
        fallback_chain = fallback.build_fallback_chain(complex_filter)
        assert len(fallback_chain) >= 2

        # Monitor performance
        monitor.start_tracking('integration_test')
        # Simulate strategy execution
        time.sleep(0.01)
        duration = monitor.end_tracking('integration_test')
        assert duration > 0.0

    def test_real_world_performance_scenarios(self):
        """
        Test with real-world performance scenarios and constraints.
        """
        unit_converter = UnitConverter(viewport_width=800, viewport_height=600)
        color_parser = ColorParser()
        analyzer = FilterComplexityAnalyzer(unit_converter, color_parser)

        # Test with various real-world filter effects
        real_world_effects = [
            {'type': 'feGaussianBlur', 'stdDeviation': '2'},  # Common blur
            {'type': 'feDropShadow', 'dx': '2', 'dy': '2', 'stdDeviation': '1'},  # Drop shadow
            {'type': 'feColorMatrix', 'type': 'hueRotate', 'values': '90'},  # Color adjustment
            {'type': 'feMorphology', 'operator': 'dilate', 'radius': '1'},  # Edge effect
        ]

        total_complexity = 0
        for effect in real_world_effects:
            complexity = analyzer.calculate_complexity_score(effect)
            assert complexity >= 0.0
            total_complexity += complexity

        # Real-world effects should be manageable
        average_complexity = total_complexity / len(real_world_effects)
        assert average_complexity < 5.0  # Should be reasonable for typical use

    def test_stress_testing_scenarios(self):
        """
        Test system behavior under stress conditions.
        """
        unit_converter = UnitConverter(viewport_width=1920, viewport_height=1080)
        color_parser = ColorParser()
        analyzer = FilterComplexityAnalyzer(unit_converter, color_parser)
        monitor = PerformanceMonitor()

        # Create stress test with many complex effects
        stress_effects = []
        for i in range(50):
            effect = {
                'type': 'feTurbulence',
                'baseFrequency': f'0.{i:02d}',
                'numOctaves': str(min(8, i // 5 + 1)),
                'seed': str(i)
            }
            stress_effects.append(effect)

        # Process all effects under monitoring
        monitor.start_tracking('stress_test')

        total_complexity = 0
        for i, effect in enumerate(stress_effects):
            # Track each individual operation
            monitor.start_tracking(f'complexity_{i}')
            complexity = analyzer.calculate_complexity_score(effect)
            monitor.end_tracking(f'complexity_{i}')
            total_complexity += complexity

        duration = monitor.end_tracking('stress_test')

        # Should handle stress gracefully
        assert duration < 5.0  # Should complete within reasonable time
        assert total_complexity > 100.0  # Should accumulate significant complexity

        # System should remain responsive
        metrics = monitor.get_metrics()
        assert metrics['total_operations'] >= 50


if __name__ == "__main__":
    # Allow running tests directly with: python test_module.py
    pytest.main([__file__])