#!/usr/bin/env python3
"""Integration tests for GradientService with PolicyEngine."""

import pytest
from lxml import etree as ET
from core.services.gradient_service import GradientService
from core.policy.engine import create_policy
from core.policy.config import OutputTarget


class TestGradientServicePolicyIntegration:
    """Test GradientService integration with PolicyEngine."""

    @pytest.fixture
    def policy_engine(self):
        """Create policy engine for testing."""
        return create_policy(OutputTarget.BALANCED)

    @pytest.fixture
    def gradient_service(self, policy_engine):
        """Create GradientService with policy engine."""
        return GradientService(policy_engine=policy_engine)

    @pytest.fixture
    def legacy_gradient_service(self):
        """Create GradientService without policy engine (legacy mode)."""
        return GradientService()

    def test_legacy_mode_without_policy(self, legacy_gradient_service):
        """Test GradientService works in legacy mode without policy engine."""
        linear_gradient = ET.fromstring('''
        <linearGradient id="grad1" xmlns="http://www.w3.org/2000/svg">
            <stop offset="0%" stop-color="#ff0000"/>
            <stop offset="100%" stop-color="#0000ff"/>
        </linearGradient>
        ''')

        legacy_gradient_service.register_gradient('grad1', linear_gradient)
        result = legacy_gradient_service.get_gradient_content('grad1')

        assert result is not None
        assert '<a:gradFill>' in result

    def test_simple_linear_gradient_with_policy(self, gradient_service):
        """Test simple linear gradient uses native DrawingML with policy."""
        linear_gradient = ET.fromstring('''
        <linearGradient id="grad1" xmlns="http://www.w3.org/2000/svg">
            <stop offset="0%" stop-color="#ff0000"/>
            <stop offset="50%" stop-color="#00ff00"/>
            <stop offset="100%" stop-color="#0000ff"/>
        </linearGradient>
        ''')

        gradient_service.register_gradient('grad1', linear_gradient)
        result = gradient_service.get_gradient_content('grad1')

        assert result is not None
        assert '<a:gradFill>' in result
        assert '<a:gsLst>' in result
        # Should have 3 stops
        assert result.count('<a:gs pos=') == 3

    def test_complex_gradient_simplification(self, gradient_service, policy_engine):
        """Test complex gradient is simplified per policy."""
        # Create gradient with 15 stops (exceeds max of 10)
        stops = ''.join([
            f'<stop offset="{i*7}%" stop-color="#{i:02x}{i:02x}{i:02x}"/>'
            for i in range(15)
        ])

        complex_gradient = ET.fromstring(f'''
        <linearGradient id="complex" xmlns="http://www.w3.org/2000/svg">
            {stops}
        </linearGradient>
        ''')

        gradient_service.register_gradient('complex', complex_gradient)
        result = gradient_service.get_gradient_content('complex')

        assert result is not None
        # Should be simplified to max 10 stops
        stop_count = result.count('<a:gs pos=')
        assert stop_count <= policy_engine.config.thresholds.max_gradient_stops

    def test_radial_gradient_with_policy(self, gradient_service):
        """Test radial gradient conversion with policy."""
        radial_gradient = ET.fromstring('''
        <radialGradient id="radial1" xmlns="http://www.w3.org/2000/svg">
            <stop offset="0%" stop-color="#ff0000"/>
            <stop offset="100%" stop-color="#0000ff"/>
        </radialGradient>
        ''')

        gradient_service.register_gradient('radial1', radial_gradient)
        result = gradient_service.get_gradient_content('radial1')

        assert result is not None
        assert '<a:gradFill>' in result
        assert '<a:path path="circle"/>' in result

    def test_mesh_gradient_within_limits(self, gradient_service):
        """Test small mesh gradient within policy limits."""
        mesh_gradient = ET.fromstring('''
        <meshgradient id="mesh1" x="2" y="2" xmlns="http://www.w3.org/2000/svg">
            <meshrow>
                <meshpatch/>
                <meshpatch/>
            </meshrow>
            <meshrow>
                <meshpatch/>
                <meshpatch/>
            </meshrow>
        </meshgradient>
        ''')

        gradient_service.register_gradient('mesh1', mesh_gradient)
        result = gradient_service.get_gradient_content('mesh1')

        assert result is not None
        # Should either convert or indicate mesh engine not available

    def test_large_mesh_gradient_emf_fallback(self, gradient_service):
        """Test large mesh gradient triggers EMF fallback per policy."""
        # Create 20x20 mesh
        mesh_rows = []
        for _ in range(20):
            mesh_rows.append('<meshrow>' + '<meshpatch/>' * 20 + '</meshrow>')

        large_mesh = ET.fromstring(f'''
        <meshgradient id="large_mesh" x="20" y="20" xmlns="http://www.w3.org/2000/svg">
            {''.join(mesh_rows)}
        </meshgradient>
        ''')

        gradient_service.register_gradient('large_mesh', large_mesh)
        result = gradient_service.get_gradient_content('large_mesh')

        assert result is not None
        # Should indicate EMF fallback required
        assert 'EMF fallback' in result or 'Engine not available' in result

    def test_policy_metrics_tracked(self, gradient_service, policy_engine):
        """Test that policy engine tracks gradient decisions."""
        linear_gradient = ET.fromstring('''
        <linearGradient id="grad1" xmlns="http://www.w3.org/2000/svg">
            <stop offset="0%" stop-color="#ff0000"/>
            <stop offset="100%" stop-color="#0000ff"/>
        </linearGradient>
        ''')

        initial_count = policy_engine.get_metrics().gradient_decisions

        gradient_service.register_gradient('grad1', linear_gradient)
        gradient_service.get_gradient_content('grad1')

        final_count = policy_engine.get_metrics().gradient_decisions

        assert final_count > initial_count

    def test_gradient_caching(self, gradient_service):
        """Test that gradient conversions are cached."""
        linear_gradient = ET.fromstring('''
        <linearGradient id="grad1" xmlns="http://www.w3.org/2000/svg">
            <stop offset="0%" stop-color="#ff0000"/>
            <stop offset="100%" stop-color="#0000ff"/>
        </linearGradient>
        ''')

        gradient_service.register_gradient('grad1', linear_gradient)

        # First call
        result1 = gradient_service.get_gradient_content('grad1')

        # Second call should use cache
        result2 = gradient_service.get_gradient_content('grad1')

        assert result1 == result2

    def test_gradient_service_clear_cache(self, gradient_service):
        """Test clearing gradient cache."""
        linear_gradient = ET.fromstring('''
        <linearGradient id="grad1" xmlns="http://www.w3.org/2000/svg">
            <stop offset="0%" stop-color="#ff0000"/>
            <stop offset="100%" stop-color="#0000ff"/>
        </linearGradient>
        ''')

        gradient_service.register_gradient('grad1', linear_gradient)
        gradient_service.get_gradient_content('grad1')

        # Clear cache
        gradient_service.clear_cache()

        # Cache should be empty
        assert len(gradient_service._gradient_cache) == 0
        assert len(gradient_service._conversion_cache) == 0

    def test_gradient_stop_color_parsing(self, gradient_service):
        """Test gradient stop color parsing from various formats."""
        gradient_with_styles = ET.fromstring('''
        <linearGradient id="styled" xmlns="http://www.w3.org/2000/svg">
            <stop offset="0%" style="stop-color:#ff0000"/>
            <stop offset="50%" stop-color="#00ff00"/>
            <stop offset="100%" style="stop-color:rgb(0,0,255)"/>
        </linearGradient>
        ''')

        gradient_service.register_gradient('styled', gradient_with_styles)
        result = gradient_service.get_gradient_content('styled')

        assert result is not None
        assert '<a:gradFill>' in result
