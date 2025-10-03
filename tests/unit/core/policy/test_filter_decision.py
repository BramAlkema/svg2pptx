#!/usr/bin/env python3
"""Unit tests for FilterDecision class."""

import pytest
from core.policy.targets import FilterDecision, DecisionReason


class TestFilterDecisionFactoryMethods:
    """Test FilterDecision factory methods."""

    def test_native_factory(self):
        """Test FilterDecision.native() factory method."""
        decision = FilterDecision.native(
            filter_type='blur',
            primitive_count=1,
            complexity_score=10
        )

        assert decision.use_native is True
        assert decision.use_native_effects is True
        assert decision.filter_type == 'blur'
        assert decision.primitive_count == 1
        assert decision.complexity_score == 10
        assert DecisionReason.NATIVE_FILTER_AVAILABLE in decision.reasons

    def test_emf_factory(self):
        """Test FilterDecision.emf() factory method."""
        decision = FilterDecision.emf(
            filter_type='chain',
            primitive_count=10,
            complexity_score=100
        )

        assert decision.use_native is False
        assert decision.use_emf_fallback is True
        assert decision.filter_type == 'chain'
        assert decision.primitive_count == 10
        assert decision.complexity_score == 100
        assert DecisionReason.FILTER_CHAIN_COMPLEX in decision.reasons

    def test_rasterize_factory(self):
        """Test FilterDecision.rasterize() factory method."""
        decision = FilterDecision.rasterize(
            filter_type='complex',
            primitive_count=20,
            complexity_score=200
        )

        assert decision.use_native is False
        assert decision.use_rasterization is True
        assert decision.filter_type == 'complex'
        assert decision.primitive_count == 20
        assert decision.complexity_score == 200
        assert DecisionReason.FILTER_RASTERIZED in decision.reasons


class TestFilterDecisionSerialization:
    """Test FilterDecision serialization."""

    def test_to_dict_native(self):
        """Test to_dict() for native filter decision."""
        decision = FilterDecision.native(
            filter_type='blur',
            primitive_count=1,
            complexity_score=10,
            native_approximation='<a:blur>'
        )

        result = decision.to_dict()

        assert result['filter_type'] == 'blur'
        assert result['primitive_count'] == 1
        assert result['complexity_score'] == 10
        assert result['use_native_effects'] is True
        assert result['use_emf_fallback'] is False
        assert result['use_rasterization'] is False
        assert result['native_approximation'] == '<a:blur>'
        assert 'reasons' in result

    def test_to_dict_emf(self):
        """Test to_dict() for EMF filter decision."""
        decision = FilterDecision.emf(
            filter_type='chain',
            primitive_count=10,
            has_unsupported_primitives=True
        )

        result = decision.to_dict()

        assert result['filter_type'] == 'chain'
        assert result['primitive_count'] == 10
        assert result['has_unsupported_primitives'] is True
        assert result['use_native_effects'] is False
        assert result['use_emf_fallback'] is True

    def test_to_dict_rasterize(self):
        """Test to_dict() for rasterization decision."""
        decision = FilterDecision.rasterize(
            filter_type='extreme',
            primitive_count=50
        )

        result = decision.to_dict()

        assert result['use_rasterization'] is True
        assert result['primitive_count'] == 50


class TestFilterDecisionImmutability:
    """Test FilterDecision immutability (frozen dataclass)."""

    def test_cannot_modify_fields(self):
        """Test that FilterDecision fields cannot be modified."""
        decision = FilterDecision.native(filter_type='blur')

        with pytest.raises(AttributeError):
            decision.filter_type = 'shadow'

        with pytest.raises(AttributeError):
            decision.use_native = False


class TestFilterDecisionCustomReasons:
    """Test FilterDecision with custom reasons."""

    def test_custom_reasons(self):
        """Test FilterDecision with custom DecisionReason list."""
        custom_reasons = [
            DecisionReason.SIMPLE_FILTER,
            DecisionReason.NATIVE_FILTER_AVAILABLE
        ]

        decision = FilterDecision.native(
            filter_type='blur',
            reasons=custom_reasons
        )

        assert decision.reasons == custom_reasons
        assert len(decision.reasons) == 2

    def test_multiple_reasons_in_dict(self):
        """Test that multiple reasons are serialized correctly."""
        decision = FilterDecision.emf(
            filter_type='chain',
            reasons=[
                DecisionReason.FILTER_CHAIN_COMPLEX,
                DecisionReason.UNSUPPORTED_FILTER_PRIMITIVE
            ]
        )

        result = decision.to_dict()

        assert len(result['reasons']) == 2
        assert 'filter_chain_complex' in result['reasons']
        assert 'unsupported_filter_primitive' in result['reasons']


class TestFilterDecisionOutputFormat:
    """Test FilterDecision output format inference."""

    def test_native_output_format(self):
        """Test that native decisions have DrawingML output format."""
        decision = FilterDecision.native(filter_type='blur')

        assert decision.output_format == 'DrawingML'

    def test_emf_output_format(self):
        """Test that EMF decisions have EMF output format."""
        decision = FilterDecision.emf(filter_type='chain')

        assert decision.output_format == 'EMF'

    def test_rasterize_output_format(self):
        """Test that rasterization decisions have appropriate format."""
        decision = FilterDecision.rasterize(filter_type='complex')

        # Rasterization should be EMF-based or image-based
        assert decision.output_format in ['EMF', 'Image', 'DrawingML']
