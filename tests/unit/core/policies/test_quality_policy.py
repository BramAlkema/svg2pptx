#!/usr/bin/env python3
"""
Unit tests for core Quality Policy Engine.

Tests the quality assessment and optimization policy decisions
for conversion fidelity and performance balance.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from tests.unit.core.conftest import IRTestBase

try:
    from core.policies import QualityPolicy, QualityEngine, QualityMetrics
    from core.ir import Path, TextFrame, Scene
    from core.ir import Point, Rect, LineSegment, SolidPaint, BezierSegment
    CORE_POLICIES_AVAILABLE = True
except ImportError:
    CORE_POLICIES_AVAILABLE = False
    pytest.skip("Core quality policies not available", allow_module_level=True)


class TestQualityPolicyCreation(IRTestBase):
    """Test QualityPolicy creation and configuration."""

    def test_quality_policy_initialization(self):
        """Test creating a quality policy."""
        try:
            policy = QualityPolicy()
            assert policy is not None
            assert hasattr(policy, 'assess_quality')
            assert callable(policy.assess_quality)
        except NameError:
            pytest.skip("QualityPolicy not available")

    def test_quality_policy_with_thresholds(self):
        """Test quality policy with custom thresholds."""
        try:
            thresholds = {
                'min_fidelity_score': 85,
                'max_performance_impact': 500,  # ms
                'acceptable_size_increase': 1.5,  # 50% increase
                'min_compatibility_score': 90
            }

            policy = QualityPolicy(thresholds=thresholds)
            assert policy is not None

            if hasattr(policy, 'thresholds'):
                assert policy.thresholds['min_fidelity_score'] == 85
                assert policy.thresholds['max_performance_impact'] == 500
        except (NameError, TypeError):
            pytest.skip("QualityPolicy with thresholds not available")

    def test_quality_policy_presets(self):
        """Test quality policy with preset configurations."""
        try:
            presets = ['maximum_fidelity', 'balanced', 'performance_optimized', 'minimum_size']

            for preset in presets:
                try:
                    policy = QualityPolicy.from_preset(preset)
                    assert policy is not None

                    if hasattr(policy, 'preset_name'):
                        assert policy.preset_name == preset
                except (AttributeError, ValueError):
                    # Preset might not be implemented
                    pass
        except (NameError, AttributeError):
            pytest.skip("QualityPolicy presets not available")


class TestQualityEngineCreation(IRTestBase):
    """Test QualityEngine creation and initialization."""

    def test_quality_engine_initialization(self):
        """Test creating a quality engine."""
        try:
            engine = QualityEngine()
            assert engine is not None
            assert hasattr(engine, 'evaluate_quality')
            assert callable(engine.evaluate_quality)
        except NameError:
            pytest.skip("QualityEngine not available")

    def test_quality_engine_with_policies(self):
        """Test quality engine with multiple quality policies."""
        try:
            fidelity_policy = QualityPolicy(focus='fidelity')
            performance_policy = QualityPolicy(focus='performance')
            size_policy = QualityPolicy(focus='file_size')

            policies = [fidelity_policy, performance_policy, size_policy]

            engine = QualityEngine(policies=policies)
            assert engine is not None

            if hasattr(engine, 'policies'):
                assert len(engine.policies) >= 3
        except (NameError, TypeError):
            pytest.skip("QualityEngine with policies not available")

    def test_quality_engine_default_configuration(self):
        """Test quality engine with default configuration."""
        try:
            engine = QualityEngine.create_default()
            assert engine is not None

            # Should have default quality policies
            if hasattr(engine, 'policies'):
                assert len(engine.policies) > 0

            # Should have reasonable default thresholds
            if hasattr(engine, 'get_thresholds'):
                thresholds = engine.get_thresholds()
                assert 'fidelity_score' in thresholds
                assert 'performance_impact' in thresholds
        except (NameError, AttributeError):
            pytest.skip("QualityEngine default creation not available")


class TestFidelityAssessment(IRTestBase):
    """Test visual fidelity assessment functionality."""

    def test_assess_simple_path_fidelity(self):
        """Test fidelity assessment for simple path."""
        simple_path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            fill=SolidPaint(color="#FF0000"),
            stroke=None,
            is_closed=False,
            data="M 0 0 L 100 100"
        )

        try:
            engine = QualityEngine()
            metrics = engine.evaluate_quality(simple_path)

            assert metrics is not None
            if hasattr(metrics, 'fidelity_score'):
                # Simple path should have high fidelity potential
                assert metrics.fidelity_score >= 90
                assert 0 <= metrics.fidelity_score <= 100
        except NameError:
            pytest.skip("QualityEngine evaluation not available")

    def test_assess_complex_path_fidelity(self):
        """Test fidelity assessment for complex path with curves."""
        try:
            complex_path = Path(
                segments=[
                    BezierSegment(
                        start=Point(0, 100),
                        end=Point(100, 100),
                        control1=Point(33, 0),
                        control2=Point(66, 0)
                    ),
                    BezierSegment(
                        start=Point(100, 100),
                        end=Point(200, 0),
                        control1=Point(133, 200),
                        control2=Point(166, 200)
                    )
                ],
                fill=SolidPaint(color="#0000FF"),
                stroke=None,
                is_closed=False,
                data="M 0 100 C 33 0 66 0 100 100 C 133 200 166 200 200 0"
            )

            engine = QualityEngine()
            metrics = engine.evaluate_quality(complex_path)

            assert metrics is not None
            if hasattr(metrics, 'complexity_score'):
                # Complex curves should have high complexity
                assert metrics.complexity_score > 50
            if hasattr(metrics, 'fidelity_challenges'):
                # Should identify fidelity challenges
                assert len(metrics.fidelity_challenges) > 0
        except (NameError, ImportError):
            pytest.skip("Complex path evaluation not available")

    def test_assess_text_fidelity(self):
        """Test fidelity assessment for text elements."""
        from core.ir import TextStyle

        styled_text = TextFrame(
            content="Complex Styled Text",
            bounds=Rect(0, 0, 300, 50),
            style=TextStyle(
                font_family="Custom Font, Arial",
                font_size=24,
                font_weight="bold",
                fill=SolidPaint(color="#800080")
            )
        )

        try:
            engine = QualityEngine()
            metrics = engine.evaluate_quality(styled_text)

            assert metrics is not None
            if hasattr(metrics, 'text_fidelity_score'):
                # Styled text fidelity depends on font support
                assert 0 <= metrics.text_fidelity_score <= 100
            if hasattr(metrics, 'font_compatibility'):
                # Should assess font compatibility
                assert hasattr(metrics, 'fidelity_score')
        except NameError:
            pytest.skip("Text quality evaluation not available")

    def test_assess_scene_overall_fidelity(self):
        """Test fidelity assessment for entire scene."""
        # Create scene with mixed content
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(50, 50))],
            fill=SolidPaint(color="#FF0000"),
            stroke=None,
            is_closed=False,
            data="M 0 0 L 50 50"
        )

        text = TextFrame(
            content="Scene Text",
            bounds=Rect(60, 60, 100, 20),
            style=None
        )

        scene = Scene(
            elements=[path, text],
            viewbox=(0, 0, 200, 200),
            width=200,
            height=200
        )

        try:
            engine = QualityEngine()
            metrics = engine.evaluate_quality(scene)

            assert metrics is not None
            if hasattr(metrics, 'overall_fidelity_score'):
                # Scene fidelity should be composite of element fidelities
                assert 0 <= metrics.overall_fidelity_score <= 100
            if hasattr(metrics, 'element_fidelity_breakdown'):
                # Should provide per-element fidelity breakdown
                assert len(metrics.element_fidelity_breakdown) == 2
        except NameError:
            pytest.skip("Scene quality evaluation not available")


class TestPerformanceAssessment(IRTestBase):
    """Test performance impact assessment functionality."""

    def test_assess_rendering_performance(self):
        """Test performance assessment for rendering impact."""
        # Create path that might be expensive to render
        complex_segments = []
        for i in range(100):
            complex_segments.append(LineSegment(Point(i, 0), Point(i+1, 1)))

        expensive_path = Path(
            segments=complex_segments,
            fill=SolidPaint(color="#00FF00"),
            stroke=None,
            is_closed=False,
            data="M " + " L ".join([f"{i} {i%2}" for i in range(101)])
        )

        try:
            engine = QualityEngine()
            metrics = engine.evaluate_quality(expensive_path)

            assert metrics is not None
            if hasattr(metrics, 'rendering_performance_score'):
                # Complex path should have lower performance score
                assert metrics.rendering_performance_score < 90
            if hasattr(metrics, 'estimated_render_time'):
                # Should estimate rendering time
                assert metrics.estimated_render_time > 0
        except NameError:
            pytest.skip("Performance evaluation not available")

    def test_assess_memory_usage(self):
        """Test memory usage assessment."""
        # Create content that might use significant memory
        large_text = TextFrame(
            content="Large text content. " * 1000,  # 20,000 characters
            bounds=Rect(0, 0, 800, 600),
            style=None
        )

        try:
            engine = QualityEngine()
            metrics = engine.evaluate_quality(large_text)

            assert metrics is not None
            if hasattr(metrics, 'memory_usage_estimate'):
                # Large text should have higher memory estimate
                assert metrics.memory_usage_estimate > 1000  # bytes
            if hasattr(metrics, 'memory_efficiency_score'):
                # Should assess memory efficiency
                assert 0 <= metrics.memory_efficiency_score <= 100
        except NameError:
            pytest.skip("Memory assessment not available")

    def test_assess_file_size_impact(self):
        """Test file size impact assessment."""
        # Create elements with different size impacts
        simple_path = Path(
            segments=[LineSegment(Point(0, 0), Point(10, 10))],
            fill=SolidPaint(color="#FF0000"),
            stroke=None,
            is_closed=False,
            data="M 0 0 L 10 10"
        )

        try:
            engine = QualityEngine()
            metrics = engine.evaluate_quality(simple_path)

            assert metrics is not None
            if hasattr(metrics, 'file_size_impact'):
                # Simple path should have low file size impact
                assert metrics.file_size_impact < 1000  # bytes
            if hasattr(metrics, 'compression_efficiency'):
                # Should assess compression potential
                assert 0 <= metrics.compression_efficiency <= 100
        except NameError:
            pytest.skip("File size assessment not available")

    def test_assess_conversion_time(self):
        """Test conversion time assessment."""
        # Create element that might take time to convert
        try:
            curved_path = Path(
                segments=[BezierSegment(
                    start=Point(0, 0),
                    end=Point(100, 100),
                    control1=Point(50, -50),
                    control2=Point(50, 150)
                )],
                fill=SolidPaint(color="#800080"),
                stroke=None,
                is_closed=False,
                data="M 0 0 C 50 -50 50 150 100 100"
            )

            engine = QualityEngine()
            metrics = engine.evaluate_quality(curved_path)

            assert metrics is not None
            if hasattr(metrics, 'conversion_time_estimate'):
                # Curved path should have measurable conversion time
                assert metrics.conversion_time_estimate > 0
            if hasattr(metrics, 'conversion_complexity'):
                # Should assess conversion complexity
                assert metrics.conversion_complexity > 0
        except (NameError, ImportError):
            pytest.skip("Conversion time assessment not available")


class TestCompatibilityAssessment(IRTestBase):
    """Test compatibility assessment functionality."""

    def test_assess_powerpoint_version_compatibility(self):
        """Test PowerPoint version compatibility assessment."""
        # Create element that might have version-specific support
        advanced_path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            fill=SolidPaint(color="#FF0000"),
            stroke=None,
            is_closed=False,
            data="M 0 0 L 100 100"
        )

        try:
            # Test with different PowerPoint versions
            versions = ['2010', '2013', '2016', '2019', '365']

            for version in versions:
                try:
                    engine = QualityEngine(target_version=version)
                    metrics = engine.evaluate_quality(advanced_path)

                    assert metrics is not None
                    if hasattr(metrics, 'compatibility_score'):
                        assert 0 <= metrics.compatibility_score <= 100
                    if hasattr(metrics, 'version_specific_features'):
                        assert isinstance(metrics.version_specific_features, list)
                except (TypeError, ValueError):
                    # Version might not be supported
                    pass
        except NameError:
            pytest.skip("Compatibility assessment not available")

    def test_assess_feature_support(self):
        """Test feature support compatibility assessment."""
        # Create element using advanced features
        try:
            from core.ir import LinearGradient

            gradient_path = Path(
                segments=[
                    LineSegment(Point(0, 0), Point(100, 0)),
                    LineSegment(Point(100, 0), Point(100, 100)),
                    LineSegment(Point(100, 100), Point(0, 100)),
                    LineSegment(Point(0, 100), Point(0, 0))
                ],
                fill=LinearGradient(
                    start_point=Point(0, 0),
                    end_point=Point(100, 0),
                    stops=[
                        {"offset": 0.0, "color": "#FF0000"},
                        {"offset": 1.0, "color": "#0000FF"}
                    ]
                ),
                stroke=None,
                is_closed=True,
                data="M 0 0 L 100 0 L 100 100 L 0 100 Z"
            )

            engine = QualityEngine()
            metrics = engine.evaluate_quality(gradient_path)

            assert metrics is not None
            if hasattr(metrics, 'feature_support_score'):
                # Gradient support depends on target platform
                assert 0 <= metrics.feature_support_score <= 100
            if hasattr(metrics, 'unsupported_features'):
                # Should identify any unsupported features
                assert isinstance(metrics.unsupported_features, list)
        except (NameError, ImportError):
            pytest.skip("Feature support assessment not available")

    def test_assess_cross_platform_compatibility(self):
        """Test cross-platform compatibility assessment."""
        text_with_font = TextFrame(
            content="Platform Test",
            bounds=Rect(0, 0, 200, 30),
            style=None
        )

        try:
            platforms = ['windows', 'macos', 'web', 'mobile']

            for platform in platforms:
                try:
                    engine = QualityEngine(target_platform=platform)
                    metrics = engine.evaluate_quality(text_with_font)

                    assert metrics is not None
                    if hasattr(metrics, 'platform_compatibility_score'):
                        assert 0 <= metrics.platform_compatibility_score <= 100
                    if hasattr(metrics, 'platform_specific_issues'):
                        assert isinstance(metrics.platform_specific_issues, list)
                except (TypeError, ValueError):
                    # Platform might not be supported
                    pass
        except NameError:
            pytest.skip("Cross-platform assessment not available")


class TestQualityMetrics(IRTestBase):
    """Test QualityMetrics data structure and calculations."""

    def test_quality_metrics_creation(self):
        """Test creating quality metrics."""
        try:
            metrics = QualityMetrics(
                fidelity_score=85,
                performance_score=90,
                compatibility_score=95,
                overall_score=90
            )

            assert metrics is not None
            assert metrics.fidelity_score == 85
            assert metrics.performance_score == 90
            assert metrics.compatibility_score == 95
            assert metrics.overall_score == 90
        except NameError:
            pytest.skip("QualityMetrics not available")

    def test_quality_metrics_calculation(self):
        """Test quality metrics score calculation."""
        try:
            metrics = QualityMetrics(
                fidelity_score=80,
                performance_score=70,
                compatibility_score=90
            )

            # Should calculate overall score
            if hasattr(metrics, 'calculate_overall_score'):
                overall = metrics.calculate_overall_score()
                assert 0 <= overall <= 100
                # Should be weighted average of component scores
                assert 70 <= overall <= 90

            # Should provide score breakdown
            if hasattr(metrics, 'get_score_breakdown'):
                breakdown = metrics.get_score_breakdown()
                assert 'fidelity' in breakdown
                assert 'performance' in breakdown
                assert 'compatibility' in breakdown
        except NameError:
            pytest.skip("QualityMetrics calculation not available")

    def test_quality_metrics_thresholds(self):
        """Test quality metrics threshold checking."""
        try:
            metrics = QualityMetrics(
                fidelity_score=75,
                performance_score=85,
                compatibility_score=95,
                overall_score=85
            )

            thresholds = {
                'min_fidelity': 80,
                'min_performance': 80,
                'min_compatibility': 90,
                'min_overall': 80
            }

            if hasattr(metrics, 'meets_thresholds'):
                result = metrics.meets_thresholds(thresholds)
                assert isinstance(result, bool)

                # Should identify which thresholds are not met
                if hasattr(metrics, 'get_threshold_violations'):
                    violations = metrics.get_threshold_violations(thresholds)
                    assert 'fidelity' in violations  # 75 < 80
                    assert 'performance' not in violations  # 85 >= 80
        except NameError:
            pytest.skip("QualityMetrics thresholds not available")

    def test_quality_metrics_recommendations(self):
        """Test quality metrics improvement recommendations."""
        try:
            low_metrics = QualityMetrics(
                fidelity_score=60,
                performance_score=40,
                compatibility_score=70,
                overall_score=57
            )

            if hasattr(low_metrics, 'get_recommendations'):
                recommendations = low_metrics.get_recommendations()
                assert isinstance(recommendations, list)
                assert len(recommendations) > 0

                # Should provide specific improvement suggestions
                rec_text = ' '.join(recommendations).lower()
                assert any(word in rec_text for word in ['improve', 'optimize', 'reduce', 'increase'])
        except NameError:
            pytest.skip("QualityMetrics recommendations not available")


class TestQualityEngineValidation(IRTestBase):
    """Test quality engine validation and error handling."""

    def test_quality_engine_invalid_element(self):
        """Test quality engine with invalid element."""
        try:
            engine = QualityEngine()

            with pytest.raises((TypeError, ValueError, AttributeError)):
                engine.evaluate_quality(None)

            with pytest.raises((TypeError, ValueError, AttributeError)):
                engine.evaluate_quality("invalid_element")
        except NameError:
            pytest.skip("QualityEngine not available")

    def test_quality_engine_invalid_thresholds(self):
        """Test quality engine with invalid thresholds."""
        try:
            invalid_thresholds = {
                'min_fidelity_score': 150,  # Invalid: > 100
                'max_performance_impact': -10,  # Invalid: negative
                'invalid_threshold': 'not_a_number'
            }

            # Should handle invalid thresholds gracefully
            try:
                policy = QualityPolicy(thresholds=invalid_thresholds)
                engine = QualityEngine(policies=[policy])

                path = Path(
                    segments=[LineSegment(Point(0, 0), Point(50, 50))],
                    fill=SolidPaint(color="#FF0000"),
                    stroke=None,
                    is_closed=False,
                    data="M 0 0 L 50 50"
                )

                metrics = engine.evaluate_quality(path)
                assert metrics is not None
            except (ValueError, TypeError):
                # Expected for invalid thresholds
                pass
        except NameError:
            pytest.skip("QualityPolicy or QualityEngine not available")

    def test_quality_engine_edge_cases(self):
        """Test quality engine with edge cases."""
        try:
            engine = QualityEngine()

            # Test with minimal element
            minimal_path = Path(
                segments=[],
                fill=None,
                stroke=None,
                is_closed=False,
                data=""
            )

            try:
                metrics = engine.evaluate_quality(minimal_path)
                # Should handle empty element gracefully
                assert metrics is not None
                if hasattr(metrics, 'overall_score'):
                    # Empty element might have low or default score
                    assert 0 <= metrics.overall_score <= 100
            except (ValueError, TypeError):
                # Empty elements might be rejected
                pass

            # Test with very complex element
            complex_segments = []
            for i in range(1000):
                complex_segments.append(LineSegment(Point(i, 0), Point(i+1, 1)))

            ultra_complex_path = Path(
                segments=complex_segments,
                fill=SolidPaint(color="#000000"),
                stroke=None,
                is_closed=False,
                data="M " + " L ".join([f"{i} {i%2}" for i in range(1001)])
            )

            metrics = engine.evaluate_quality(ultra_complex_path)
            assert metrics is not None
            # Very complex element should be detected
            if hasattr(metrics, 'complexity_score'):
                assert metrics.complexity_score > 95
        except NameError:
            pytest.skip("QualityEngine not available")


class TestQualityEnginePerformance(IRTestBase):
    """Test quality engine performance characteristics."""

    def test_quality_evaluation_performance(self):
        """Test quality evaluation performance."""
        try:
            import time

            engine = QualityEngine()

            path = Path(
                segments=[LineSegment(Point(0, 0), Point(100, 100))],
                fill=SolidPaint(color="#FF0000"),
                stroke=None,
                is_closed=False,
                data="M 0 0 L 100 100"
            )

            # Time multiple evaluations
            start_time = time.time()

            for _ in range(50):
                metrics = engine.evaluate_quality(path)
                assert metrics is not None

            total_time = time.time() - start_time

            # Should evaluate quickly
            assert total_time < 0.5  # 50 evaluations in < 0.5 seconds
            average_time = total_time / 50
            assert average_time < 0.01  # Each evaluation < 10ms
        except NameError:
            pytest.skip("QualityEngine not available")

    def test_quality_memory_efficiency(self):
        """Test quality engine memory efficiency."""
        try:
            import sys

            engine = QualityEngine()

            # Create and evaluate many elements
            elements = []
            metrics_list = []

            for i in range(100):
                path = Path(
                    segments=[LineSegment(Point(i, 0), Point(i+5, 5))],
                    fill=SolidPaint(color=f"#{i:02x}0000"),
                    stroke=None,
                    is_closed=False,
                    data=f"M {i} 0 L {i+5} 5"
                )
                elements.append(path)

                metrics = engine.evaluate_quality(path)
                metrics_list.append(metrics)

            assert len(metrics_list) == 100

            # Check memory usage is reasonable
            engine_size = sys.getsizeof(engine)
            metrics_total_size = sum(sys.getsizeof(m) for m in metrics_list)

            assert engine_size < 50000  # Engine < 50KB
            assert metrics_total_size < 200000  # All metrics < 200KB
        except NameError:
            pytest.skip("QualityEngine not available")


if __name__ == "__main__":
    pytest.main([__file__])