#!/usr/bin/env python3
"""
Tests for the Policy Engine

Validates policy decision making for different element types and complexity levels.
"""

import pytest
import numpy as np
from core.ir import (
    Path, TextFrame, Group, Image, Point, Rect,
    LineSegment, BezierSegment, Run, TextAnchor,
    SolidPaint, LinearGradientPaint, GradientStop, Stroke, StrokeJoin
)
from core.policy import (
    Policy, PolicyConfig, OutputTarget, create_policy,
    DecisionReason, PathDecision, TextDecision, GroupDecision
)


class TestPolicyEngine:
    """Test policy engine decision making"""

    def test_policy_creation(self):
        """Test policy creation with different targets"""
        policy = create_policy(OutputTarget.BALANCED)
        assert policy.config.target == OutputTarget.BALANCED

        speed_policy = create_policy("speed")
        assert speed_policy.config.target == OutputTarget.SPEED

        quality_policy = create_policy("quality")
        assert quality_policy.config.target == OutputTarget.QUALITY

    def test_simple_path_native_decision(self):
        """Test simple path uses native DrawingML"""
        policy = create_policy(OutputTarget.BALANCED)

        # Simple rectangular path
        path = Path(
            segments=[
                LineSegment(Point(0, 0), Point(100, 0)),
                LineSegment(Point(100, 0), Point(100, 100)),
                LineSegment(Point(100, 100), Point(0, 100)),
                LineSegment(Point(0, 100), Point(0, 0))
            ],
            fill=SolidPaint("FF0000"),
            opacity=1.0
        )

        decision = policy.decide_path(path)

        assert isinstance(decision, PathDecision)
        assert decision.use_native is True
        assert DecisionReason.SIMPLE_GEOMETRY in decision.reasons
        assert DecisionReason.BELOW_THRESHOLDS in decision.reasons
        assert decision.confidence > 0.9

    def test_complex_path_emf_decision(self):
        """Test complex path uses EMF fallback"""
        policy = create_policy(OutputTarget.BALANCED)

        # Create path with many segments (above threshold)
        segments = []
        for i in range(1200):  # Above default threshold of 1000
            start = Point(i, 0)
            end = Point(i+1, 1)
            segments.append(LineSegment(start, end))

        path = Path(segments=segments, fill=SolidPaint("FF0000"))

        decision = policy.decide_path(path)

        assert decision.use_native is False
        assert DecisionReason.ABOVE_THRESHOLDS in decision.reasons
        assert DecisionReason.COMPLEX_GEOMETRY in decision.reasons
        assert decision.segment_count == 1200

    def test_simple_text_native_decision(self):
        """Test simple text uses native DrawingML"""
        policy = create_policy(OutputTarget.BALANCED)

        text = TextFrame(
            origin=Point(10, 20),
            runs=[Run(text="Hello World", font_family="Arial", font_size_pt=12.0)],
            anchor=TextAnchor.START,
            bbox=Rect(10, 20, 100, 20)
        )

        decision = policy.decide_text(text)

        assert decision.use_native is True
        assert DecisionReason.BELOW_THRESHOLDS in decision.reasons
        assert DecisionReason.FONT_AVAILABLE in decision.reasons
        assert decision.run_count == 1

    def test_complex_text_emf_decision(self):
        """Test complex text uses EMF fallback"""
        policy = create_policy(OutputTarget.BALANCED)

        # Create text with many runs (above threshold)
        runs = []
        for i in range(25):  # Above default threshold of 20
            runs.append(Run(
                text=f"Run {i}",
                font_family="Arial",
                font_size_pt=12.0,
                bold=i % 2 == 0,
                italic=i % 3 == 0
            ))

        text = TextFrame(
            origin=Point(10, 20),
            runs=runs,
            anchor=TextAnchor.START,
            bbox=Rect(10, 20, 500, 300)
        )

        decision = policy.decide_text(text)

        assert decision.use_native is False
        assert DecisionReason.ABOVE_THRESHOLDS in decision.reasons
        assert decision.run_count == 25

    def test_group_decision(self):
        """Test group decision making"""
        policy = create_policy(OutputTarget.BALANCED)

        # Simple group with few children
        children = [
            Path(
                segments=[LineSegment(Point(0, 0), Point(10, 10))],
                fill=SolidPaint("FF0000")
            )
        ]

        group = Group(children=children, opacity=1.0)

        decision = policy.decide_group(group)

        assert decision.use_native is True
        assert DecisionReason.BELOW_THRESHOLDS in decision.reasons
        assert decision.element_count == 1

    def test_image_decision(self):
        """Test image decision making"""
        policy = create_policy(OutputTarget.BALANCED)

        image = Image(
            origin=Point(0, 0),
            size=Rect(0, 0, 100, 100),
            data=b"fake_image_data",
            format="png"
        )

        decision = policy.decide_image(image)

        # Images typically use EMF for best fidelity
        assert decision.use_native is False
        assert decision.format == "png"

    def test_output_target_thresholds(self):
        """Test different output targets have different thresholds"""
        speed_policy = create_policy(OutputTarget.SPEED)
        quality_policy = create_policy(OutputTarget.QUALITY)

        # Speed should have lower thresholds (prefer EMF)
        assert speed_policy.config.thresholds.max_path_segments < quality_policy.config.thresholds.max_path_segments
        assert speed_policy.config.thresholds.max_text_runs < quality_policy.config.thresholds.max_text_runs

    def test_policy_metrics(self):
        """Test policy metrics collection"""
        policy = create_policy(OutputTarget.BALANCED)

        # Make some decisions
        simple_path = Path(
            segments=[LineSegment(Point(0, 0), Point(10, 10))],
            fill=SolidPaint("FF0000")
        )
        policy.decide_path(simple_path)

        simple_text = TextFrame(
            origin=Point(10, 20),
            runs=[Run(text="Test", font_family="Arial", font_size_pt=12.0)],
            anchor=TextAnchor.START,
            bbox=Rect(10, 20, 50, 20)
        )
        policy.decide_text(simple_text)

        metrics = policy.get_metrics()
        assert metrics.total_decisions == 2
        assert metrics.path_decisions == 1
        assert metrics.text_decisions == 1
        assert metrics.native_decisions == 2  # Both should be native
        assert metrics.emf_decisions == 0

    def test_conservative_mode(self):
        """Test conservative mode forces EMF for clipping"""
        config = PolicyConfig.for_target(OutputTarget.BALANCED, conservative_clipping=True)
        policy = Policy(config)

        # Simple path but with clipping
        from core.ir import ClipRef, ClipStrategy
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(10, 10))],
            fill=SolidPaint("FF0000"),
            clip=ClipRef("clip1", ClipStrategy.NATIVE)
        )

        decision = policy.decide_path(path)

        assert decision.use_native is False
        assert DecisionReason.CONSERVATIVE_MODE in decision.reasons

    def test_decision_explanation(self):
        """Test decision explanation generation"""
        policy = create_policy(OutputTarget.BALANCED)

        path = Path(
            segments=[LineSegment(Point(0, 0), Point(10, 10))],
            fill=SolidPaint("FF0000")
        )

        decision = policy.decide_path(path)
        explanation = decision.explain()

        assert "DrawingML" in explanation
        assert "confidence" in explanation
        assert "%" in explanation

    def test_stroke_complexity_detection(self):
        """Test detection of complex stroke features"""
        policy = create_policy(OutputTarget.BALANCED)

        # Path with complex stroke
        complex_stroke = Stroke(
            paint=SolidPaint("000000"),
            width=5.0,
            dash_array=[5.0, 3.0, 2.0, 3.0]  # Complex dash pattern
        )

        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            stroke=complex_stroke
        )

        decision = policy.decide_path(path)

        # Complex stroke might push toward EMF depending on thresholds
        assert decision.has_complex_stroke is True

    def test_gradient_complexity_detection(self):
        """Test detection of complex gradient features"""
        policy = create_policy(OutputTarget.BALANCED)

        # Gradient with many stops
        many_stops = [
            GradientStop(offset=i/10.0, rgb="FF0000")
            for i in range(15)  # Above default threshold of 10
        ]

        gradient = LinearGradientPaint(
            stops=many_stops,
            start=Point(0, 0),
            end=Point(100, 0)
        )

        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            fill=gradient
        )

        decision = policy.decide_path(path)

        # Many gradient stops might push toward EMF
        assert decision.has_complex_fill is True


if __name__ == "__main__":
    pytest.main([__file__])