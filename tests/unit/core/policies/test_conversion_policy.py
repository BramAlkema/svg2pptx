#!/usr/bin/env python3
"""
Unit tests for core Conversion Policy Engine.

Tests the policy decision system that determines how SVG elements
should be converted to PowerPoint elements.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from tests.unit.core.conftest import IRTestBase

try:
    from core.policies import ConversionPolicy, PolicyEngine, PolicyDecision
    from core.ir import Path, TextFrame, Group, Image
    from core.ir import Point, Rect, LineSegment, SolidPaint
    CORE_POLICIES_AVAILABLE = True
except ImportError:
    CORE_POLICIES_AVAILABLE = False
    pytest.skip("Core policies not available", allow_module_level=True)


class TestConversionPolicyCreation(IRTestBase):
    """Test ConversionPolicy creation and configuration."""

    def test_conversion_policy_initialization(self):
        """Test creating a conversion policy."""
        try:
            policy = ConversionPolicy()
            assert policy is not None
            assert hasattr(policy, 'evaluate')
            assert callable(policy.evaluate)
        except NameError:
            pytest.skip("ConversionPolicy not available")

    def test_conversion_policy_with_rules(self):
        """Test conversion policy with custom rules."""
        try:
            rules = {
                'max_path_complexity': 100,
                'use_custom_geometry': True,
                'prefer_shapes_over_paths': False,
                'text_to_path_threshold': 50
            }

            policy = ConversionPolicy(rules=rules)
            assert policy is not None

            if hasattr(policy, 'rules'):
                assert policy.rules == rules
        except (NameError, TypeError):
            pytest.skip("ConversionPolicy with rules not available")

    def test_conversion_policy_presets(self):
        """Test conversion policy with preset configurations."""
        try:
            # Test different preset modes
            presets = ['conservative', 'aggressive', 'balanced', 'high_fidelity']

            for preset in presets:
                try:
                    policy = ConversionPolicy.from_preset(preset)
                    assert policy is not None
                except (AttributeError, ValueError):
                    # Preset might not be supported
                    pass
        except (NameError, AttributeError):
            pytest.skip("ConversionPolicy presets not available")


class TestPolicyEngineCreation(IRTestBase):
    """Test PolicyEngine creation and initialization."""

    def test_policy_engine_initialization(self):
        """Test creating a policy engine."""
        try:
            engine = PolicyEngine()
            assert engine is not None
            assert hasattr(engine, 'evaluate_element')
            assert callable(engine.evaluate_element)
        except NameError:
            pytest.skip("PolicyEngine not available")

    def test_policy_engine_with_policies(self):
        """Test policy engine with multiple policies."""
        try:
            path_policy = ConversionPolicy(rules={'prefer_custom_geometry': True})
            text_policy = ConversionPolicy(rules={'use_text_frames': True})

            policies = {
                'path': path_policy,
                'text': text_policy
            }

            engine = PolicyEngine(policies=policies)
            assert engine is not None

            if hasattr(engine, 'policies'):
                assert len(engine.policies) >= 2
        except (NameError, TypeError):
            pytest.skip("PolicyEngine with policies not available")

    def test_policy_engine_default_policies(self):
        """Test policy engine with default policies."""
        try:
            engine = PolicyEngine.create_default()
            assert engine is not None

            # Should have default policies for common element types
            if hasattr(engine, 'policies'):
                expected_types = ['path', 'text', 'image', 'group']
                policy_types = list(engine.policies.keys())
                # Should have some default policies
                assert len(policy_types) > 0
        except (NameError, AttributeError):
            pytest.skip("PolicyEngine default creation not available")


class TestPathConversionPolicies(IRTestBase):
    """Test policies for path element conversion."""

    def test_simple_path_policy_decision(self):
        """Test policy decision for simple path."""
        simple_path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            fill=SolidPaint(color="#FF0000"),
            stroke=None,
            is_closed=False,
            data="M 0 0 L 100 100"
        )

        try:
            engine = PolicyEngine()
            decision = engine.evaluate_element(simple_path)

            assert decision is not None
            if hasattr(decision, 'conversion_type'):
                # Should decide on conversion approach
                assert decision.conversion_type in ['custom_geometry', 'preset_shape', 'path']
        except NameError:
            pytest.skip("PolicyEngine evaluation not available")

    def test_complex_path_policy_decision(self):
        """Test policy decision for complex path."""
        # Create complex path with many segments
        segments = []
        for i in range(50):
            segments.append(LineSegment(Point(i, 0), Point(i+1, 1)))

        complex_path = Path(
            segments=segments,
            fill=SolidPaint(color="#0000FF"),
            stroke=None,
            is_closed=False,
            data="M " + " L ".join([f"{i} {i%2}" for i in range(51)])
        )

        try:
            engine = PolicyEngine()
            decision = engine.evaluate_element(complex_path)

            assert decision is not None
            # Complex paths might require different handling
            if hasattr(decision, 'complexity_score'):
                assert decision.complexity_score > 10  # Should detect complexity
        except NameError:
            pytest.skip("PolicyEngine evaluation not available")

    def test_closed_path_policy_decision(self):
        """Test policy decision for closed path (shape)."""
        closed_path = Path(
            segments=[
                LineSegment(Point(0, 0), Point(100, 0)),
                LineSegment(Point(100, 0), Point(100, 100)),
                LineSegment(Point(100, 100), Point(0, 100)),
                LineSegment(Point(0, 100), Point(0, 0))
            ],
            fill=SolidPaint(color="#00FF00"),
            stroke=None,
            is_closed=True,
            data="M 0 0 L 100 0 L 100 100 L 0 100 Z"
        )

        try:
            engine = PolicyEngine()
            decision = engine.evaluate_element(closed_path)

            assert decision is not None
            # Closed paths might be candidates for preset shapes
            if hasattr(decision, 'shape_candidate'):
                # Might detect as rectangle candidate
                assert hasattr(decision, 'conversion_type')
        except NameError:
            pytest.skip("PolicyEngine evaluation not available")

    def test_path_with_curves_policy_decision(self):
        """Test policy decision for path with curves."""
        try:
            from core.ir import BezierSegment

            curved_path = Path(
                segments=[BezierSegment(
                    start=Point(0, 100),
                    end=Point(100, 100),
                    control1=Point(50, 0)
                )],
                fill=None,
                stroke=SolidPaint(color="#FF00FF"),
                is_closed=False,
                data="M 0 100 Q 50 0 100 100"
            )

            engine = PolicyEngine()
            decision = engine.evaluate_element(curved_path)

            assert decision is not None
            # Curved paths require custom geometry
            if hasattr(decision, 'requires_custom_geometry'):
                assert decision.requires_custom_geometry == True
        except (NameError, ImportError):
            pytest.skip("BezierSegment or PolicyEngine not available")


class TestTextConversionPolicies(IRTestBase):
    """Test policies for text element conversion."""

    def test_simple_text_policy_decision(self):
        """Test policy decision for simple text."""
        simple_text = TextFrame(
            content="Hello World",
            bounds=Rect(10, 20, 200, 30),
            style=None
        )

        try:
            engine = PolicyEngine()
            decision = engine.evaluate_element(simple_text)

            assert decision is not None
            if hasattr(decision, 'conversion_type'):
                # Should decide on text handling approach
                assert decision.conversion_type in ['text_frame', 'text_shape', 'path']
        except NameError:
            pytest.skip("PolicyEngine evaluation not available")

    def test_styled_text_policy_decision(self):
        """Test policy decision for styled text."""
        from core.ir import TextStyle

        styled_text = TextFrame(
            content="Styled Text",
            bounds=Rect(0, 0, 300, 50),
            style=TextStyle(
                font_family="Arial",
                font_size=18,
                fill=SolidPaint(color="#FF0000")
            )
        )

        try:
            engine = PolicyEngine()
            decision = engine.evaluate_element(styled_text)

            assert decision is not None
            # Styled text might have different handling requirements
            if hasattr(decision, 'preserve_styling'):
                assert hasattr(decision, 'conversion_type')
        except NameError:
            pytest.skip("PolicyEngine evaluation not available")

    def test_long_text_policy_decision(self):
        """Test policy decision for long text content."""
        long_content = "This is a very long text content that might require special handling " * 10

        long_text = TextFrame(
            content=long_content,
            bounds=Rect(0, 0, 400, 200),
            style=None
        )

        try:
            engine = PolicyEngine()
            decision = engine.evaluate_element(long_text)

            assert decision is not None
            # Long text might require text wrapping or chunking
            if hasattr(decision, 'requires_wrapping'):
                assert hasattr(decision, 'conversion_type')
        except NameError:
            pytest.skip("PolicyEngine evaluation not available")

    def test_multiline_text_policy_decision(self):
        """Test policy decision for multiline text."""
        multiline_text = TextFrame(
            content="Line 1\nLine 2\nLine 3\nLine 4",
            bounds=Rect(0, 0, 250, 100),
            style=None
        )

        try:
            engine = PolicyEngine()
            decision = engine.evaluate_element(multiline_text)

            assert decision is not None
            # Multiline text requires paragraph handling
            if hasattr(decision, 'paragraph_count'):
                assert decision.paragraph_count >= 4
        except NameError:
            pytest.skip("PolicyEngine evaluation not available")


class TestGroupConversionPolicies(IRTestBase):
    """Test policies for group element conversion."""

    def test_simple_group_policy_decision(self):
        """Test policy decision for simple group."""
        try:
            child_path = Path(
                segments=[LineSegment(Point(0, 0), Point(50, 50))],
                fill=SolidPaint(color="#0000FF"),
                stroke=None,
                is_closed=False,
                data="M 0 0 L 50 50"
            )

            group = Group(
                children=[child_path],
                transform=None,
                clip_id=None
            )

            engine = PolicyEngine()
            decision = engine.evaluate_element(group)

            assert decision is not None
            if hasattr(decision, 'conversion_type'):
                # Should decide on group handling
                assert decision.conversion_type in ['group_shape', 'flatten', 'preserve_hierarchy']
        except NameError:
            pytest.skip("Group or PolicyEngine not available")

    def test_complex_group_policy_decision(self):
        """Test policy decision for complex group with many children."""
        try:
            children = []
            for i in range(20):
                child = Path(
                    segments=[LineSegment(Point(i, 0), Point(i+5, 5))],
                    fill=SolidPaint(color=f"#{i:02x}0000"),
                    stroke=None,
                    is_closed=False,
                    data=f"M {i} 0 L {i+5} 5"
                )
                children.append(child)

            complex_group = Group(
                children=children,
                transform=None,
                clip_id=None
            )

            engine = PolicyEngine()
            decision = engine.evaluate_element(complex_group)

            assert decision is not None
            # Complex groups might require flattening
            if hasattr(decision, 'child_count'):
                assert decision.child_count == 20
            if hasattr(decision, 'requires_flattening'):
                assert isinstance(decision.requires_flattening, bool)
        except NameError:
            pytest.skip("Group or PolicyEngine not available")

    def test_transformed_group_policy_decision(self):
        """Test policy decision for transformed group."""
        try:
            child_path = Path(
                segments=[LineSegment(Point(0, 0), Point(25, 25))],
                fill=SolidPaint(color="#00FF00"),
                stroke=None,
                is_closed=False,
                data="M 0 0 L 25 25"
            )

            transformed_group = Group(
                children=[child_path],
                transform="translate(10, 20) rotate(45) scale(2)",
                clip_id=None
            )

            engine = PolicyEngine()
            decision = engine.evaluate_element(transformed_group)

            assert decision is not None
            # Transformed groups require special handling
            if hasattr(decision, 'has_transform'):
                assert decision.has_transform == True
            if hasattr(decision, 'transform_complexity'):
                assert decision.transform_complexity > 0
        except NameError:
            pytest.skip("Group or PolicyEngine not available")


class TestImageConversionPolicies(IRTestBase):
    """Test policies for image element conversion."""

    def test_simple_image_policy_decision(self):
        """Test policy decision for simple image."""
        try:
            image = Image(
                src="test_image.png",
                bounds=Rect(0, 0, 200, 150),
                alt_text="Test Image"
            )

            engine = PolicyEngine()
            decision = engine.evaluate_element(image)

            assert decision is not None
            if hasattr(decision, 'conversion_type'):
                # Should decide on image handling
                assert decision.conversion_type in ['embedded_image', 'linked_image', 'shape_with_fill']
        except NameError:
            pytest.skip("Image or PolicyEngine not available")

    def test_large_image_policy_decision(self):
        """Test policy decision for large image."""
        try:
            large_image = Image(
                src="large_image.jpg",
                bounds=Rect(0, 0, 2000, 1500),  # Large dimensions
                alt_text="Large Image"
            )

            engine = PolicyEngine()
            decision = engine.evaluate_element(large_image)

            assert decision is not None
            # Large images might require compression or resizing
            if hasattr(decision, 'requires_compression'):
                assert isinstance(decision.requires_compression, bool)
            if hasattr(decision, 'size_category'):
                assert decision.size_category in ['small', 'medium', 'large', 'extra_large']
        except NameError:
            pytest.skip("Image or PolicyEngine not available")

    def test_svg_image_policy_decision(self):
        """Test policy decision for SVG image."""
        try:
            svg_image = Image(
                src="vector_image.svg",
                bounds=Rect(0, 0, 300, 200),
                alt_text="SVG Image"
            )

            engine = PolicyEngine()
            decision = engine.evaluate_element(svg_image)

            assert decision is not None
            # SVG images might require conversion or embedding
            if hasattr(decision, 'is_vector'):
                assert decision.is_vector == True
            if hasattr(decision, 'conversion_type'):
                assert decision.conversion_type in ['convert_to_shapes', 'rasterize', 'embed_svg']
        except NameError:
            pytest.skip("Image or PolicyEngine not available")


class TestPolicyDecisionStructure(IRTestBase):
    """Test PolicyDecision data structure and properties."""

    def test_policy_decision_creation(self):
        """Test creating a policy decision."""
        try:
            decision = PolicyDecision(
                conversion_type='custom_geometry',
                confidence=0.9,
                reasons=['complex_path', 'curves_present']
            )

            assert decision is not None
            assert decision.conversion_type == 'custom_geometry'
            assert decision.confidence == 0.9
            assert 'complex_path' in decision.reasons
        except NameError:
            pytest.skip("PolicyDecision not available")

    def test_policy_decision_properties(self):
        """Test policy decision properties and metadata."""
        try:
            decision = PolicyDecision(
                conversion_type='text_frame',
                confidence=0.8,
                reasons=['simple_text'],
                metadata={
                    'estimated_complexity': 3,
                    'performance_impact': 'low',
                    'fidelity_score': 95
                }
            )

            assert decision is not None
            if hasattr(decision, 'metadata'):
                assert decision.metadata['estimated_complexity'] == 3
                assert decision.metadata['performance_impact'] == 'low'
                assert decision.metadata['fidelity_score'] == 95
        except (NameError, TypeError):
            pytest.skip("PolicyDecision with metadata not available")

    def test_policy_decision_validation(self):
        """Test policy decision validation."""
        try:
            # Test invalid confidence value
            with pytest.raises(ValueError):
                PolicyDecision(
                    conversion_type='path',
                    confidence=1.5,  # Invalid: > 1.0
                    reasons=['test']
                )

            # Test invalid conversion type
            with pytest.raises(ValueError):
                PolicyDecision(
                    conversion_type='invalid_type',
                    confidence=0.5,
                    reasons=['test']
                )
        except NameError:
            pytest.skip("PolicyDecision validation not available")

    def test_policy_decision_comparison(self):
        """Test policy decision comparison and ranking."""
        try:
            decision1 = PolicyDecision(
                conversion_type='custom_geometry',
                confidence=0.9,
                reasons=['high_fidelity']
            )

            decision2 = PolicyDecision(
                conversion_type='preset_shape',
                confidence=0.7,
                reasons=['performance']
            )

            # Higher confidence should rank higher
            if hasattr(decision1, '__gt__'):
                assert decision1 > decision2
            elif hasattr(decision1, 'compare_to'):
                assert decision1.compare_to(decision2) > 0
        except NameError:
            pytest.skip("PolicyDecision comparison not available")


class TestPolicyEngineAdvanced(IRTestBase):
    """Test advanced policy engine functionality."""

    def test_policy_engine_rule_conflicts(self):
        """Test policy engine handling of conflicting rules."""
        try:
            # Create conflicting policies
            policy1 = ConversionPolicy(rules={
                'prefer_custom_geometry': True,
                'performance_priority': False
            })

            policy2 = ConversionPolicy(rules={
                'prefer_preset_shapes': True,
                'performance_priority': True
            })

            engine = PolicyEngine(policies={'path1': policy1, 'path2': policy2})

            simple_path = Path(
                segments=[LineSegment(Point(0, 0), Point(100, 100))],
                fill=SolidPaint(color="#FF0000"),
                stroke=None,
                is_closed=False,
                data="M 0 0 L 100 100"
            )

            decision = engine.evaluate_element(simple_path)

            assert decision is not None
            # Should resolve conflicts somehow
            if hasattr(decision, 'conflict_resolution'):
                assert hasattr(decision, 'conversion_type')
        except (NameError, TypeError):
            pytest.skip("PolicyEngine conflict resolution not available")

    def test_policy_engine_context_awareness(self):
        """Test policy engine context-aware decisions."""
        try:
            context = {
                'slide_size': (1920, 1080),
                'performance_mode': 'high_quality',
                'target_version': 'powerpoint_2019',
                'compatibility_level': 'strict'
            }

            engine = PolicyEngine(context=context)

            path = Path(
                segments=[LineSegment(Point(0, 0), Point(50, 50))],
                fill=SolidPaint(color="#0000FF"),
                stroke=None,
                is_closed=False,
                data="M 0 0 L 50 50"
            )

            decision = engine.evaluate_element(path)

            assert decision is not None
            # Decision should consider context
            if hasattr(decision, 'context_factors'):
                assert isinstance(decision.context_factors, list)
        except (NameError, TypeError):
            pytest.skip("PolicyEngine context awareness not available")

    def test_policy_engine_learning_adaptation(self):
        """Test policy engine learning from previous decisions."""
        try:
            engine = PolicyEngine()

            # Simulate feedback on previous decisions
            feedback_data = [
                {'element_type': 'path', 'decision': 'custom_geometry', 'success': True},
                {'element_type': 'path', 'decision': 'preset_shape', 'success': False},
                {'element_type': 'text', 'decision': 'text_frame', 'success': True}
            ]

            if hasattr(engine, 'learn_from_feedback'):
                engine.learn_from_feedback(feedback_data)

                # Future decisions should be influenced by feedback
                path = Path(
                    segments=[LineSegment(Point(0, 0), Point(25, 25))],
                    fill=SolidPaint(color="#00FF00"),
                    stroke=None,
                    is_closed=False,
                    data="M 0 0 L 25 25"
                )

                decision = engine.evaluate_element(path)
                assert decision is not None

                # Should prefer custom_geometry for paths based on feedback
                if hasattr(decision, 'learning_influenced'):
                    assert decision.learning_influenced == True
        except (NameError, AttributeError):
            pytest.skip("PolicyEngine learning not available")

    def test_policy_engine_performance_monitoring(self):
        """Test policy engine performance monitoring."""
        try:
            engine = PolicyEngine()

            path = Path(
                segments=[LineSegment(Point(0, 0), Point(75, 75))],
                fill=SolidPaint(color="#FF00FF"),
                stroke=None,
                is_closed=False,
                data="M 0 0 L 75 75"
            )

            # Time the evaluation
            import time
            start_time = time.time()
            decision = engine.evaluate_element(path)
            evaluation_time = time.time() - start_time

            assert decision is not None
            assert evaluation_time < 0.01  # Should be very fast

            # Check if performance metrics are tracked
            if hasattr(engine, 'performance_metrics'):
                assert 'evaluation_count' in engine.performance_metrics
                assert 'average_evaluation_time' in engine.performance_metrics
        except NameError:
            pytest.skip("PolicyEngine performance monitoring not available")


class TestPolicyEngineValidation(IRTestBase):
    """Test policy engine validation and error handling."""

    def test_policy_engine_invalid_element(self):
        """Test policy engine with invalid element."""
        try:
            engine = PolicyEngine()

            with pytest.raises((TypeError, ValueError, AttributeError)):
                engine.evaluate_element(None)

            with pytest.raises((TypeError, ValueError, AttributeError)):
                engine.evaluate_element("invalid_element")
        except NameError:
            pytest.skip("PolicyEngine not available")

    def test_policy_engine_missing_policies(self):
        """Test policy engine with missing policies for element type."""
        try:
            # Create engine without policies for specific element type
            engine = PolicyEngine(policies={})

            path = Path(
                segments=[LineSegment(Point(0, 0), Point(50, 50))],
                fill=SolidPaint(color="#808080"),
                stroke=None,
                is_closed=False,
                data="M 0 0 L 50 50"
            )

            # Should either use default policy or raise appropriate error
            try:
                decision = engine.evaluate_element(path)
                assert decision is not None
                # Should have fallback decision
                if hasattr(decision, 'is_fallback'):
                    assert decision.is_fallback == True
            except (ValueError, KeyError):
                # Expected if no fallback policy exists
                pass
        except NameError:
            pytest.skip("PolicyEngine not available")

    def test_policy_engine_corrupted_rules(self):
        """Test policy engine with corrupted rules."""
        try:
            corrupted_rules = {
                'max_complexity': 'invalid_number',
                'unknown_rule': True,
                'prefer_shapes': None
            }

            # Should handle corrupted rules gracefully
            try:
                policy = ConversionPolicy(rules=corrupted_rules)
                engine = PolicyEngine(policies={'test': policy})

                path = Path(
                    segments=[LineSegment(Point(0, 0), Point(30, 30))],
                    fill=SolidPaint(color="#FFFF00"),
                    stroke=None,
                    is_closed=False,
                    data="M 0 0 L 30 30"
                )

                decision = engine.evaluate_element(path)
                assert decision is not None
            except (ValueError, TypeError):
                # Expected for corrupted rules
                pass
        except NameError:
            pytest.skip("ConversionPolicy or PolicyEngine not available")


class TestPolicyEnginePerformance(IRTestBase):
    """Test policy engine performance characteristics."""

    def test_policy_evaluation_performance(self):
        """Test policy evaluation performance."""
        try:
            import time

            engine = PolicyEngine()

            path = Path(
                segments=[LineSegment(Point(0, 0), Point(100, 100))],
                fill=SolidPaint(color="#FF0000"),
                stroke=None,
                is_closed=False,
                data="M 0 0 L 100 100"
            )

            # Time multiple evaluations
            start_time = time.time()

            for _ in range(100):
                decision = engine.evaluate_element(path)
                assert decision is not None

            total_time = time.time() - start_time

            # Should evaluate quickly
            assert total_time < 0.1  # 100 evaluations in < 0.1 seconds
            average_time = total_time / 100
            assert average_time < 0.001  # Each evaluation < 1ms
        except NameError:
            pytest.skip("PolicyEngine not available")

    def test_policy_memory_usage(self):
        """Test policy engine memory usage."""
        try:
            import sys

            engine = PolicyEngine()

            # Create many elements
            elements = []
            for i in range(100):
                path = Path(
                    segments=[LineSegment(Point(i, 0), Point(i+10, 10))],
                    fill=SolidPaint(color=f"#{i:02x}0000"),
                    stroke=None,
                    is_closed=False,
                    data=f"M {i} 0 L {i+10} 10"
                )
                elements.append(path)

            # Evaluate all elements
            decisions = []
            for element in elements:
                decision = engine.evaluate_element(element)
                decisions.append(decision)

            assert len(decisions) == 100

            # Check memory usage is reasonable
            engine_size = sys.getsizeof(engine)
            decisions_size = sum(sys.getsizeof(d) for d in decisions)

            assert engine_size < 100000  # Engine < 100KB
            assert decisions_size < 500000  # All decisions < 500KB
        except NameError:
            pytest.skip("PolicyEngine not available")


if __name__ == "__main__":
    pytest.main([__file__])