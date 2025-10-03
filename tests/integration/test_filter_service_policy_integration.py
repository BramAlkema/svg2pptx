#!/usr/bin/env python3
"""Integration tests for FilterService with PolicyEngine."""

import pytest
from lxml import etree as ET
from core.services.filter_service import FilterService
from core.policy.engine import create_policy
from core.policy.config import OutputTarget


class TestFilterServicePolicyIntegration:
    """Test FilterService integration with PolicyEngine."""

    @pytest.fixture
    def policy_engine(self):
        """Create policy engine for testing."""
        return create_policy(OutputTarget.BALANCED)

    @pytest.fixture
    def filter_service(self, policy_engine):
        """Create FilterService with policy engine."""
        return FilterService(policy_engine=policy_engine)

    @pytest.fixture
    def legacy_filter_service(self):
        """Create FilterService without policy engine (legacy mode)."""
        return FilterService()

    def test_legacy_mode_without_policy(self, legacy_filter_service):
        """Test FilterService works in legacy mode without policy engine."""
        blur_filter = ET.fromstring('''
        <filter id="blur1" xmlns="http://www.w3.org/2000/svg">
            <feGaussianBlur stdDeviation="2"/>
        </filter>
        ''')

        legacy_filter_service.register_filter('blur1', blur_filter)
        result = legacy_filter_service.get_filter_content('blur1')

        assert result is not None
        assert '<a:blur' in result

    def test_simple_blur_with_policy(self, filter_service):
        """Test simple blur filter uses native DrawingML with policy."""
        blur_filter = ET.fromstring('''
        <filter id="blur1" xmlns="http://www.w3.org/2000/svg">
            <feGaussianBlur stdDeviation="2"/>
        </filter>
        ''')

        filter_service.register_filter('blur1', blur_filter)
        result = filter_service.get_filter_content('blur1')

        assert result is not None
        assert '<a:blur' in result
        assert 'rad=' in result

    def test_drop_shadow_with_policy(self, filter_service):
        """Test drop shadow filter uses native DrawingML with policy."""
        shadow_filter = ET.fromstring('''
        <filter id="shadow1" xmlns="http://www.w3.org/2000/svg">
            <feDropShadow dx="3" dy="3" stdDeviation="2"/>
        </filter>
        ''')

        filter_service.register_filter('shadow1', shadow_filter)
        result = filter_service.get_filter_content('shadow1')

        assert result is not None
        assert '<a:outerShdw' in result

    def test_complex_filter_chain_emf_fallback(self, filter_service):
        """Test complex filter chain triggers EMF fallback per policy."""
        complex_filter = ET.fromstring('''
        <filter id="complex" xmlns="http://www.w3.org/2000/svg">
            <feGaussianBlur stdDeviation="2"/>
            <feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0"/>
            <feComposite in="SourceGraphic" operator="over"/>
            <feGaussianBlur stdDeviation="1"/>
            <feColorMatrix type="saturate" values="0.5"/>
            <feComposite operator="atop"/>
        </filter>
        ''')

        filter_service.register_filter('complex', complex_filter)
        result = filter_service.get_filter_content('complex')

        assert result is not None
        assert 'EMF fallback required' in result
        assert 'primitives: 6' in result

    def test_policy_metrics_tracked(self, filter_service, policy_engine):
        """Test that policy engine tracks filter decisions."""
        blur_filter = ET.fromstring('''
        <filter id="blur1" xmlns="http://www.w3.org/2000/svg">
            <feGaussianBlur stdDeviation="2"/>
        </filter>
        ''')

        initial_count = policy_engine.get_metrics().filter_decisions

        filter_service.register_filter('blur1', blur_filter)
        filter_service.get_filter_content('blur1')

        final_count = policy_engine.get_metrics().filter_decisions

        assert final_count > initial_count

    def test_filter_caching(self, filter_service):
        """Test that filter conversions are cached."""
        blur_filter = ET.fromstring('''
        <filter id="blur1" xmlns="http://www.w3.org/2000/svg">
            <feGaussianBlur stdDeviation="2"/>
        </filter>
        ''')

        filter_service.register_filter('blur1', blur_filter)

        # First call
        result1 = filter_service.get_filter_content('blur1')

        # Second call should use cache
        result2 = filter_service.get_filter_content('blur1')

        assert result1 == result2

    def test_unsupported_filter_fallback(self, filter_service):
        """Test unsupported filter primitives trigger appropriate fallback."""
        unsupported_filter = ET.fromstring('''
        <filter id="unsupported" xmlns="http://www.w3.org/2000/svg">
            <feTurbulence type="turbulence" baseFrequency="0.05"/>
        </filter>
        ''')

        filter_service.register_filter('unsupported', unsupported_filter)
        result = filter_service.get_filter_content('unsupported')

        # Should get either EMF fallback or "no supported primitives" message
        assert result is not None

    def test_filter_service_clear_cache(self, filter_service):
        """Test clearing filter cache."""
        blur_filter = ET.fromstring('''
        <filter id="blur1" xmlns="http://www.w3.org/2000/svg">
            <feGaussianBlur stdDeviation="2"/>
        </filter>
        ''')

        filter_service.register_filter('blur1', blur_filter)
        filter_service.get_filter_content('blur1')

        # Clear cache
        filter_service.clear_cache()

        # Cache should be empty
        assert len(filter_service._filter_cache) == 0
        assert len(filter_service._conversion_cache) == 0
