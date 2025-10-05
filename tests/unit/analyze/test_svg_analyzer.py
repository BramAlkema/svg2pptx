#!/usr/bin/env python3
"""
Unit tests for SVG Analyzer implementation.

Tests the analysis of SVG complexity and recommendation generation.
"""

import sys
import os
import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET

# Add paths for imports (Clean Slate modules)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

# Import the analyzer and related types
from core.analyze.analyzer import SVGAnalyzer, AnalysisResult
from core.analyze.complexity_calculator import ComplexityCalculator
from core.analyze.recommendation_engine import (
    RecommendationEngine, RecommendationContext,
    ConversionStrategy, QualityLevel
)


class TestSVGAnalyzer:
    """Test suite for SVG analyzer implementation."""

    @pytest.fixture
    def analyzer(self):
        """Create an SVGAnalyzer instance for testing."""
        return SVGAnalyzer()

    @pytest.fixture
    def simple_svg(self):
        """Simple SVG for testing"""
        return ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <rect x="10" y="10" width="100" height="50" fill="blue"/>
            <circle cx="200" cy="150" r="30" fill="red"/>
        </svg>''')

    @pytest.fixture
    def complex_svg(self):
        """Complex SVG for testing"""
        return ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <defs>
                <linearGradient id="grad1">
                    <stop offset="0%" stop-color="red"/>
                    <stop offset="100%" stop-color="blue"/>
                </linearGradient>
                <filter id="blur">
                    <feGaussianBlur stdDeviation="3"/>
                </filter>
            </defs>
            <g transform="rotate(45)" opacity="0.8">
                <path d="M 10 10 C 20 20 40 20 50 10 S 80 0 90 10 Q 100 20 110 10 L 120 20 Z" fill="url(#grad1)" filter="url(#blur)"/>
                <g clip-path="url(#clip1)">
                    <text x="50" y="100" font-size="14" font-family="Arial">
                        <tspan dx="5" dy="5">Complex</tspan>
                        <tspan dx="5" dy="15">Text</tspan>
                    </text>
                    <image x="100" y="150" width="50" height="40" href="test.png"/>
                </g>
            </g>
            <animate attributeName="opacity" values="0;1;0" dur="2s" repeatCount="indefinite"/>
        </svg>''')

    def test_analyzer_initialization(self, analyzer):
        """Test that analyzer initializes correctly."""
        assert analyzer is not None
        assert hasattr(analyzer, 'complexity_thresholds')
        assert hasattr(analyzer, 'element_weights')
        assert hasattr(analyzer, 'complexity_calculator')
        assert isinstance(analyzer.complexity_calculator, ComplexityCalculator)

    def test_simple_svg_analysis(self, analyzer, simple_svg):
        """Test analysis of simple SVG."""
        result = analyzer.analyze(simple_svg)

        assert isinstance(result, AnalysisResult)
        assert result.element_count == 2  # rect and circle
        assert result.complexity_score <= 0.5  # Should be low complexity
        assert result.path_count == 0  # No path elements
        assert result.text_count == 0  # No text elements
        assert result.group_count == 0  # No groups
        assert result.image_count == 0  # No images
        assert not result.has_transforms
        assert not result.has_clipping
        assert not result.has_patterns
        assert not result.has_animations
        assert result.processing_time_ms > 0

    def test_complex_svg_analysis(self, analyzer, complex_svg):
        """Test analysis of complex SVG."""
        result = analyzer.analyze(complex_svg)

        assert isinstance(result, AnalysisResult)
        assert result.element_count > 5  # Multiple elements
        assert result.complexity_score > 0.2  # Should be higher than simple SVG
        assert result.path_count >= 1  # Has path element
        assert result.text_count >= 1  # Has text elements
        assert result.group_count >= 1  # Has groups
        assert result.image_count >= 1  # Has image
        assert result.filter_count >= 1  # Has filters
        assert result.gradient_count >= 1  # Has gradients
        assert result.has_transforms  # Has transform attribute
        assert result.has_clipping  # Has clip-path
        assert result.has_animations  # Has animate element
        assert result.group_nesting_depth >= 2  # Nested groups

    def test_element_counting(self, analyzer, complex_svg):
        """Test accurate element counting."""
        counts = analyzer._count_elements_by_type(complex_svg)

        assert 'path' in counts
        assert 'text' in counts
        assert 'g' in counts
        assert 'image' in counts
        assert 'linearGradient' in counts
        assert 'filter' in counts
        assert 'animate' in counts

    def test_complexity_score_calculation(self, analyzer, simple_svg, complex_svg):
        """Test complexity score calculation."""
        simple_counts = analyzer._count_elements_by_type(simple_svg)
        complex_counts = analyzer._count_elements_by_type(complex_svg)

        simple_score = analyzer._calculate_complexity_score(simple_svg, simple_counts)
        complex_score = analyzer._calculate_complexity_score(complex_svg, complex_counts)

        assert 0.0 <= simple_score <= 1.0
        assert 0.0 <= complex_score <= 1.0
        assert complex_score > simple_score

    def test_feature_analysis(self, analyzer, complex_svg):
        """Test feature detection."""
        features = analyzer._analyze_features(complex_svg)

        assert features['has_transforms']
        assert features['has_clipping']
        assert features['has_animations']

    def test_text_complexity_calculation(self, analyzer):
        """Test text complexity analysis."""
        text_svg = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <text x="10" y="20" font-family="Arial" font-size="14" font-weight="bold">Simple</text>
            <text x="50" y="60" dx="5 10 15" dy="2 4 6" text-decoration="underline">
                <tspan>Complex</tspan>
                <tspan dx="5">Text</tspan>
            </text>
        </svg>''')

        complexity = analyzer._calculate_text_complexity(text_svg)
        assert 0.0 <= complexity <= 1.0
        assert complexity > 0.0  # Should detect some complexity

    def test_path_complexity_calculation(self, analyzer):
        """Test path complexity analysis."""
        path_svg = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <path d="M 10 10 L 20 20"/>
            <path d="M 30 30 C 40 40 50 50 60 60 Q 70 70 80 80 A 10 10 0 0 1 90 90"/>
        </svg>''')

        complexity = analyzer._calculate_path_complexity(path_svg)
        assert 0.0 <= complexity <= 1.0
        assert complexity > 0.0  # Should detect path complexity

    def test_group_nesting_depth(self, analyzer):
        """Test group nesting depth calculation."""
        nested_svg = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <g>
                <g>
                    <g>
                        <rect x="0" y="0" width="10" height="10"/>
                    </g>
                </g>
            </g>
        </svg>''')

        depth = analyzer._calculate_group_nesting_depth(nested_svg)
        assert depth == 3

    def test_output_format_recommendation(self, analyzer, simple_svg, complex_svg):
        """Test output format recommendations."""
        simple_result = analyzer.analyze(simple_svg)
        complex_result = analyzer.analyze(complex_svg)

        # Simple SVG should recommend PPTX
        assert simple_result.recommended_output_format.value in ['pptx', 'slide_xml']

        # Complex SVG might recommend debug or slide XML
        assert complex_result.recommended_output_format.value in ['pptx', 'slide_xml', 'debug_json']

    def test_strategy_generation(self, analyzer, simple_svg, complex_svg):
        """Test conversion strategy recommendations."""
        simple_result = analyzer.analyze(simple_svg)
        complex_result = analyzer.analyze(complex_svg)

        # Simple SVG should suggest native approaches
        assert len(simple_result.recommended_strategies) > 0
        assert any('native' in strategy for strategy in simple_result.recommended_strategies)

        # Complex SVG should suggest more sophisticated approaches
        assert len(complex_result.recommended_strategies) > 0

    def test_optimization_suggestions(self, analyzer, complex_svg):
        """Test optimization suggestion generation."""
        result = analyzer.analyze(complex_svg)

        assert len(result.optimization_suggestions) > 0
        # Should detect various optimization opportunities
        suggestions = ' '.join(result.optimization_suggestions)
        assert any(keyword in suggestions for keyword in
                  ['reduction', 'precision', 'definitions', 'transformations'])

    def test_conversion_time_estimation(self, analyzer, simple_svg, complex_svg):
        """Test conversion time estimation."""
        simple_result = analyzer.analyze(simple_svg)
        complex_result = analyzer.analyze(complex_svg)

        assert simple_result.estimated_conversion_time_ms > 0
        assert complex_result.estimated_conversion_time_ms > 0
        assert complex_result.estimated_conversion_time_ms > simple_result.estimated_conversion_time_ms

    def test_error_handling(self, analyzer):
        """Test error handling with malformed SVG."""
        # Test with minimal SVG that might cause issues
        minimal_svg = ET.fromstring('<svg xmlns="http://www.w3.org/2000/svg"></svg>')

        result = analyzer.analyze(minimal_svg)
        assert isinstance(result, AnalysisResult)
        assert result.complexity_score >= 0.0
        assert result.element_count >= 0

    def test_performance_benchmarks(self, analyzer, complex_svg):
        """Test that analysis completes within reasonable time."""
        import time

        start_time = time.perf_counter()
        result = analyzer.analyze(complex_svg)
        end_time = time.perf_counter()

        processing_time_ms = (end_time - start_time) * 1000

        # Analysis should complete quickly (under 100ms for normal SVGs)
        assert processing_time_ms < 100
        assert result.processing_time_ms > 0


class TestComplexityCalculator:
    """Test suite for complexity calculator."""

    @pytest.fixture
    def calculator(self):
        """Create a ComplexityCalculator instance for testing."""
        return ComplexityCalculator()

    def test_calculator_initialization(self, calculator):
        """Test calculator initialization."""
        assert calculator is not None
        assert hasattr(calculator, 'element_weights')
        assert hasattr(calculator, 'feature_multipliers')

    def test_base_complexity_calculation(self, calculator):
        """Test base complexity calculation."""
        element_counts = {
            'rect': 2,
            'circle': 1,
            'path': 3,
            'text': 1
        }

        complexity = calculator._calculate_base_complexity(element_counts)
        assert 0.0 <= complexity <= 2.0
        assert complexity > 0.0

    def test_feature_multiplier_calculation(self, calculator):
        """Test feature multiplier calculation."""
        svg_with_features = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <g transform="rotate(45)">
                <rect x="0" y="0" width="10" height="10" clip-path="url(#clip)"/>
            </g>
        </svg>''')

        multiplier = calculator._calculate_feature_multiplier(svg_with_features)
        assert multiplier >= 1.0  # Should be >= 1.0 due to features
        assert multiplier <= 3.0  # Should be capped

    def test_overall_complexity_calculation(self, calculator):
        """Test overall complexity calculation."""
        simple_svg = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
            <rect x="0" y="0" width="10" height="10"/>
        </svg>''')

        element_counts = {'rect': 1}
        complexity = calculator.calculate_overall_complexity(simple_svg, element_counts)

        assert 0.0 <= complexity <= 1.0

    def test_normalization_function(self, calculator):
        """Test complexity normalization."""
        # Test various raw values
        test_values = [0.0, 0.5, 1.0, 2.0, 5.0, 10.0]

        for value in test_values:
            normalized = calculator._normalize_complexity(value)
            assert 0.0 <= normalized <= 1.0


class TestRecommendationEngine:
    """Test suite for recommendation engine."""

    @pytest.fixture
    def engine(self):
        """Create a RecommendationEngine instance for testing."""
        return RecommendationEngine()

    @pytest.fixture
    def simple_context(self):
        """Simple recommendation context."""
        return RecommendationContext(
            complexity_score=0.2,
            element_count=5,
            path_complexity=0.1,
            text_complexity=0.1,
            group_nesting_depth=1,
            has_transforms=False,
            has_clipping=False,
            has_patterns=False,
            has_animations=False,
            has_filters=False
        )

    @pytest.fixture
    def complex_context(self):
        """Complex recommendation context."""
        return RecommendationContext(
            complexity_score=0.8,
            element_count=50,
            path_complexity=0.9,
            text_complexity=0.7,
            group_nesting_depth=5,
            has_transforms=True,
            has_clipping=True,
            has_patterns=True,
            has_animations=True,
            has_filters=True
        )

    def test_engine_initialization(self, engine):
        """Test recommendation engine initialization."""
        assert engine is not None
        assert hasattr(engine, 'complexity_thresholds')
        assert hasattr(engine, 'strategy_weights')

    def test_simple_svg_recommendations(self, engine, simple_context):
        """Test recommendations for simple SVG."""
        recommendations = engine.generate_recommendations(simple_context)

        assert len(recommendations) > 0
        assert len(recommendations) <= 3  # Should limit to top 3

        # First recommendation should have high confidence
        best_recommendation = recommendations[0]
        assert best_recommendation.confidence > 0.5
        assert best_recommendation.strategy != ConversionStrategy.FALLBACK_MODE

        # Simple SVG should prefer native strategies
        assert best_recommendation.strategy in [
            ConversionStrategy.NATIVE_DRAWINGML,
            ConversionStrategy.HYBRID_APPROACH
        ]

    def test_complex_svg_recommendations(self, engine, complex_context):
        """Test recommendations for complex SVG."""
        recommendations = engine.generate_recommendations(complex_context)

        assert len(recommendations) > 0

        # Complex SVG should prefer robust strategies
        strategy_names = [r.strategy for r in recommendations]
        assert ConversionStrategy.EMF_HEAVY in strategy_names or \
               ConversionStrategy.PREPROCESSING_FIRST in strategy_names

    def test_quality_preference_adjustment(self, engine, simple_context):
        """Test quality preference adjustments."""
        simple_context.quality_preference = QualityLevel.SPEED_OPTIMIZED
        speed_recs = engine.generate_recommendations(simple_context)

        simple_context.quality_preference = QualityLevel.QUALITY_OPTIMIZED
        quality_recs = engine.generate_recommendations(simple_context)

        # Different preferences should potentially give different results
        # (though for simple SVGs the difference might be minimal)
        assert len(speed_recs) > 0
        assert len(quality_recs) > 0

    def test_strategy_evaluation(self, engine, simple_context):
        """Test individual strategy evaluation."""
        recommendation = engine._evaluate_strategy(
            ConversionStrategy.NATIVE_DRAWINGML,
            simple_context
        )

        assert recommendation.confidence >= 0.0
        assert recommendation.estimated_quality >= 0.0
        assert recommendation.estimated_performance >= 0.0
        assert isinstance(recommendation.reasoning, list)
        assert isinstance(recommendation.optimizations, list)
        assert isinstance(recommendation.warnings, list)

    def test_fallback_recommendation(self, engine, simple_context):
        """Test fallback recommendation creation."""
        fallback = engine._create_fallback_recommendation(simple_context)

        assert fallback.strategy == ConversionStrategy.FALLBACK_MODE
        assert fallback.confidence > 0.0
        assert len(fallback.reasoning) > 0
        assert len(fallback.warnings) > 0

    def test_strategy_descriptions(self, engine):
        """Test strategy descriptions."""
        for strategy in ConversionStrategy:
            description = engine.get_strategy_description(strategy)
            assert isinstance(description, str)
            assert len(description) > 0

    def test_recommendation_sorting(self, engine, simple_context):
        """Test that recommendations are sorted by confidence."""
        recommendations = engine.generate_recommendations(simple_context)

        if len(recommendations) > 1:
            for i in range(len(recommendations) - 1):
                assert recommendations[i].confidence >= recommendations[i + 1].confidence


class TestIntegrationScenarios:
    """Test complete analyzer scenarios."""

    @pytest.fixture
    def analyzer(self):
        return SVGAnalyzer()

    @pytest.fixture
    def engine(self):
        return RecommendationEngine()

    def test_end_to_end_workflow(self, analyzer, engine):
        """Test complete analysis and recommendation workflow."""
        # Create test SVG
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <rect x="10" y="10" width="100" height="50" fill="blue"/>
            <path d="M 150 50 C 200 25 250 75 300 50" stroke="red" fill="none"/>
            <text x="50" y="200" font-size="16">Test Text</text>
        </svg>'''

        svg_root = ET.fromstring(svg_content)

        # Analyze SVG
        analysis_result = analyzer.analyze(svg_root)
        assert analysis_result.complexity_score >= 0.0

        # Create recommendation context
        context = RecommendationContext(
            complexity_score=analysis_result.complexity_score,
            element_count=analysis_result.element_count,
            path_complexity=analysis_result.path_complexity,
            text_complexity=analysis_result.text_complexity,
            group_nesting_depth=analysis_result.group_nesting_depth,
            has_transforms=analysis_result.has_transforms,
            has_clipping=analysis_result.has_clipping,
            has_patterns=analysis_result.has_patterns,
            has_animations=analysis_result.has_animations,
            has_filters=getattr(analysis_result, 'has_filters', False)
        )

        # Generate recommendations
        recommendations = engine.generate_recommendations(context)
        assert len(recommendations) > 0

        # Validate complete workflow
        best_recommendation = recommendations[0]
        assert best_recommendation.confidence > 0.0
        assert isinstance(best_recommendation.strategy, ConversionStrategy)

    def test_performance_on_large_svg(self, analyzer):
        """Test analyzer performance on large SVG."""
        # Create SVG with many elements
        elements = []
        for i in range(100):
            elements.append(f'<rect x="{i*5}" y="{i*3}" width="4" height="2" fill="blue"/>')

        large_svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="600">
            {"".join(elements)}
        </svg>'''

        svg_root = ET.fromstring(large_svg_content)

        import time
        start_time = time.perf_counter()
        result = analyzer.analyze(svg_root)
        end_time = time.perf_counter()

        processing_time = (end_time - start_time) * 1000

        assert result.complexity_score >= 0.0
        assert result.element_count == 100
        assert processing_time < 500  # Should complete within 500ms

    def test_various_svg_patterns(self, analyzer):
        """Test analyzer with various SVG patterns."""
        test_patterns = [
            # Basic shapes
            '<svg xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="50" r="25"/></svg>',

            # Complex paths
            '<svg xmlns="http://www.w3.org/2000/svg"><path d="M10,10 Q50,5 90,10 T170,10"/></svg>',

            # Nested groups
            '<svg xmlns="http://www.w3.org/2000/svg"><g><g><g><rect x="0" y="0" width="10" height="10"/></g></g></g></svg>',

            # Text elements
            '<svg xmlns="http://www.w3.org/2000/svg"><text x="10" y="20">Hello <tspan>World</tspan></text></svg>',
        ]

        for pattern in test_patterns:
            svg_root = ET.fromstring(pattern)
            result = analyzer.analyze(svg_root)
            assert result.complexity_score >= 0.0
            assert result.complexity_score >= 0.0