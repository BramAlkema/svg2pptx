#!/usr/bin/env python3
"""Unit tests for GradientDecision class."""

import pytest
from core.policy.targets import GradientDecision, DecisionReason


class TestGradientDecisionFactoryMethods:
    """Test GradientDecision factory methods."""

    def test_native_factory_linear(self):
        """Test GradientDecision.native() for linear gradient."""
        decision = GradientDecision.native(
            gradient_type='linear',
            stop_count=5
        )

        assert decision.use_native is True
        assert decision.gradient_type == 'linear'
        assert decision.stop_count == 5
        assert decision.use_simplified_gradient is False
        assert DecisionReason.SIMPLE_GRADIENT in decision.reasons

    def test_native_factory_radial(self):
        """Test GradientDecision.native() for radial gradient."""
        decision = GradientDecision.native(
            gradient_type='radial',
            stop_count=8
        )

        assert decision.use_native is True
        assert decision.gradient_type == 'radial'
        assert decision.stop_count == 8

    def test_simplified_factory(self):
        """Test GradientDecision.simplified() factory method."""
        decision = GradientDecision.simplified(
            gradient_type='linear',
            stop_count=15
        )

        assert decision.use_native is True
        assert decision.use_simplified_gradient is True
        assert decision.gradient_type == 'linear'
        assert decision.stop_count == 15
        assert DecisionReason.GRADIENT_SIMPLIFIED in decision.reasons


class TestGradientDecisionMeshSupport:
    """Test GradientDecision mesh gradient support."""

    def test_mesh_gradient_fields(self):
        """Test mesh gradient specific fields."""
        decision = GradientDecision.native(
            gradient_type='mesh',
            stop_count=0,
            mesh_rows=5,
            mesh_cols=5,
            mesh_patch_count=100
        )

        assert decision.gradient_type == 'mesh'
        assert decision.mesh_rows == 5
        assert decision.mesh_cols == 5
        assert decision.mesh_patch_count == 100

    def test_mesh_gradient_complex_fallback(self):
        """Test mesh gradient EMF fallback for complex meshes."""
        decision = GradientDecision(
            use_native=False,
            gradient_type='mesh',
            stop_count=0,
            mesh_rows=20,
            mesh_cols=20,
            mesh_patch_count=1600,
            reasons=[DecisionReason.MESH_GRADIENT_COMPLEX]
        )

        assert decision.use_native is False
        assert decision.mesh_patch_count == 1600
        assert DecisionReason.MESH_GRADIENT_COMPLEX in decision.reasons


class TestGradientDecisionSerialization:
    """Test GradientDecision serialization."""

    def test_to_dict_simple_gradient(self):
        """Test to_dict() for simple gradient."""
        decision = GradientDecision.native(
            gradient_type='linear',
            stop_count=5,
            color_space='sRGB'
        )

        result = decision.to_dict()

        assert result['gradient_type'] == 'linear'
        assert result['stop_count'] == 5
        assert result['color_space'] == 'sRGB'
        assert result['use_simplified_gradient'] is False
        assert result['mesh_rows'] == 0
        assert result['mesh_cols'] == 0

    def test_to_dict_simplified_gradient(self):
        """Test to_dict() for simplified gradient."""
        decision = GradientDecision.simplified(
            gradient_type='radial',
            stop_count=15
        )

        result = decision.to_dict()

        assert result['gradient_type'] == 'radial'
        assert result['stop_count'] == 15
        assert result['use_simplified_gradient'] is True

    def test_to_dict_mesh_gradient(self):
        """Test to_dict() for mesh gradient."""
        decision = GradientDecision.native(
            gradient_type='mesh',
            mesh_rows=10,
            mesh_cols=10,
            mesh_patch_count=400
        )

        result = decision.to_dict()

        assert result['gradient_type'] == 'mesh'
        assert result['mesh_rows'] == 10
        assert result['mesh_cols'] == 10
        assert result['mesh_patch_count'] == 400


class TestGradientDecisionColorSpace:
    """Test GradientDecision color space handling."""

    def test_default_color_space(self):
        """Test default color space is sRGB."""
        decision = GradientDecision.native(
            gradient_type='linear',
            stop_count=3
        )

        assert decision.color_space == 'sRGB'

    def test_custom_color_space(self):
        """Test custom color space."""
        decision = GradientDecision.native(
            gradient_type='linear',
            stop_count=5,
            color_space='linearRGB'
        )

        assert decision.color_space == 'linearRGB'

    def test_color_interpolation_flag(self):
        """Test color interpolation flag."""
        decision = GradientDecision.native(
            gradient_type='linear',
            stop_count=5,
            has_color_interpolation=True
        )

        assert decision.has_color_interpolation is True


class TestGradientDecisionTransformComplexity:
    """Test GradientDecision transform complexity."""

    def test_simple_transform(self):
        """Test gradient with simple transform."""
        decision = GradientDecision.native(
            gradient_type='linear',
            stop_count=5,
            has_complex_transform=False
        )

        assert decision.has_complex_transform is False

    def test_complex_transform(self):
        """Test gradient with complex transform."""
        decision = GradientDecision(
            use_native=False,
            gradient_type='radial',
            stop_count=5,
            has_complex_transform=True,
            reasons=[DecisionReason.GRADIENT_TRANSFORM_COMPLEX]
        )

        assert decision.has_complex_transform is True
        assert DecisionReason.GRADIENT_TRANSFORM_COMPLEX in decision.reasons


class TestGradientDecisionImmutability:
    """Test GradientDecision immutability."""

    def test_cannot_modify_fields(self):
        """Test that GradientDecision fields cannot be modified."""
        decision = GradientDecision.native(gradient_type='linear')

        with pytest.raises(AttributeError):
            decision.gradient_type = 'radial'

        with pytest.raises(AttributeError):
            decision.stop_count = 10


class TestGradientDecisionReasons:
    """Test GradientDecision reasons."""

    def test_simple_gradient_reasons(self):
        """Test reasons for simple gradient."""
        decision = GradientDecision.native(
            gradient_type='linear',
            stop_count=5
        )

        assert DecisionReason.SIMPLE_GRADIENT in decision.reasons

    def test_simplified_gradient_reasons(self):
        """Test reasons for simplified gradient."""
        decision = GradientDecision.simplified(
            gradient_type='linear',
            stop_count=15
        )

        assert DecisionReason.GRADIENT_SIMPLIFIED in decision.reasons

    def test_too_many_stops_reasons(self):
        """Test reasons for too many stops."""
        decision = GradientDecision.simplified(
            gradient_type='linear',
            stop_count=20,
            reasons=[
                DecisionReason.GRADIENT_SIMPLIFIED,
                DecisionReason.TOO_MANY_GRADIENT_STOPS
            ]
        )

        assert DecisionReason.TOO_MANY_GRADIENT_STOPS in decision.reasons

    def test_mesh_complex_reasons(self):
        """Test reasons for complex mesh gradient."""
        decision = GradientDecision(
            use_native=False,
            gradient_type='mesh',
            mesh_patch_count=1600,
            reasons=[DecisionReason.MESH_GRADIENT_COMPLEX]
        )

        assert DecisionReason.MESH_GRADIENT_COMPLEX in decision.reasons


class TestGradientDecisionOutputFormat:
    """Test GradientDecision output format."""

    def test_native_output_format(self):
        """Test native gradient output format."""
        decision = GradientDecision.native(
            gradient_type='linear',
            stop_count=5
        )

        assert decision.output_format == 'DrawingML'

    def test_emf_fallback_output_format(self):
        """Test EMF fallback output format."""
        decision = GradientDecision(
            use_native=False,
            gradient_type='mesh',
            mesh_patch_count=1600,
            reasons=[DecisionReason.MESH_GRADIENT_COMPLEX]
        )

        assert decision.output_format == 'EMF'
