#!/usr/bin/env python3
"""
Tests for Comprehensive WordArt Builder

Tests the complete WordArt generation pipeline integration.
"""

import pytest
from lxml import etree as ET
from unittest.mock import Mock, patch

from src.converters.comprehensive_wordart_builder import (
    ComprehensiveWordArtBuilder,
    WordArtGenerationConfig,
    ComprehensiveWordArtResult,
    create_comprehensive_wordart_builder
)
from core.services.conversion_services import ConversionServices
from src.converters.base import ConversionContext
from core.policy.targets import TextDecision


class TestComprehensiveWordArtBuilder:
    """Test comprehensive WordArt builder functionality."""

    def setup_method(self):
        """Set up test builder with mock services."""
        # Create mock services
        self.mock_services = Mock(spec=ConversionServices)
        self.mock_services.unit_converter = Mock()
        self.mock_services.viewport_handler = Mock()
        self.mock_services.font_service = Mock()
        self.mock_services.gradient_service = Mock()
        self.mock_services.pattern_service = Mock()
        self.mock_services.clip_service = Mock()

        # Create mock context
        self.mock_context = Mock(spec=ConversionContext)
        self.mock_context.services = self.mock_services
        self.mock_context.svg_root = ET.Element('svg')

        # Create config
        self.config = WordArtGenerationConfig(
            enable_transform_analysis=True,
            enable_gradient_mapping=True,
            enable_path_warping=True,
            enable_policy_decisions=True
        )

        self.builder = ComprehensiveWordArtBuilder(self.mock_services, self.config)

    def test_initialization(self):
        """Test builder initialization."""
        assert self.builder.services is self.mock_services
        assert self.builder.config is self.config
        assert hasattr(self.builder, 'integration_service')
        assert hasattr(self.builder, 'transform_decomposer')
        assert hasattr(self.builder, 'color_service')
        assert hasattr(self.builder, 'wordart_builder')
        assert hasattr(self.builder, 'warp_fitter')
        assert hasattr(self.builder, 'policy')

    def test_build_wordart_success(self):
        """Test successful WordArt building."""
        # Create test text element
        text_element = ET.Element('text')
        text_element.text = 'Hello World'
        text_element.set('font-family', 'Arial')
        text_element.set('font-size', '24')
        text_element.set('fill', '#FF0000')

        # Mock successful policy decision
        mock_decision = TextDecision.native([])

        # Mock successful generation
        mock_wordart_xml = ET.Element('wordart')

        with patch.object(self.builder, '_validate_input') as mock_validate, \
             patch.object(self.builder, '_comprehensive_analysis') as mock_analysis, \
             patch.object(self.builder, '_make_comprehensive_policy_decision') as mock_policy, \
             patch.object(self.builder.integration_service, 'generate_wordart') as mock_generate, \
             patch.object(self.builder, '_optimize_wordart_xml') as mock_optimize:

            # Setup mocks
            mock_validate.return_value = {'valid': True, 'text_content': 'Hello World'}
            mock_analysis.return_value = {
                'text_content': 'Hello World',
                'text_complexity': 2.0,
                'transform_analysis': None,
                'style_analysis': {'style_complexity': 1.0}
            }
            mock_policy.return_value = mock_decision

            # Mock integration service result
            mock_integration_result = Mock()
            mock_integration_result.success = True
            mock_integration_result.wordart_xml = mock_wordart_xml
            mock_integration_result.decision_metadata = {'test': 'data'}
            mock_integration_result.performance_metrics = {'generation_time_ms': 100}
            mock_integration_result.fallback_reason = None
            mock_generate.return_value = mock_integration_result

            mock_optimize.return_value = mock_wordart_xml

            # Test building
            result = self.builder.build_wordart(text_element, self.mock_context)

            # Verify result
            assert isinstance(result, ComprehensiveWordArtResult)
            assert result.success is True
            assert result.wordart_xml is mock_wordart_xml
            assert 'analysis_result' in result.generation_metadata
            assert 'total_generation_time_ms' in result.performance_metrics
            assert result.policy_decision is mock_decision

    def test_build_wordart_input_validation_failure(self):
        """Test WordArt building with input validation failure."""
        # Test with None element
        result = self.builder.build_wordart(None, self.mock_context)

        assert result.success is False
        assert 'Input validation failed' in result.fallback_reason

    def test_build_wordart_policy_rejection(self):
        """Test WordArt building with policy rejection."""
        text_element = ET.Element('text')
        text_element.text = 'Complex Text'

        # Mock policy rejection
        from core.policy.targets import DecisionReason
        mock_decision = TextDecision.emf([DecisionReason.COMPLEX_GEOMETRY, DecisionReason.COMPLEX_TRANSFORM])

        with patch.object(self.builder, '_validate_input') as mock_validate, \
             patch.object(self.builder, '_comprehensive_analysis') as mock_analysis, \
             patch.object(self.builder, '_make_comprehensive_policy_decision') as mock_policy, \
             patch.object(self.builder, '_suggest_alternatives') as mock_alternatives:

            mock_validate.return_value = {'valid': True, 'text_content': 'Complex Text'}
            mock_analysis.return_value = {'text_complexity': 8.0}
            mock_policy.return_value = mock_decision
            mock_alternatives.return_value = ['EMF embedding', 'Text-to-path']

            result = self.builder.build_wordart(text_element, self.mock_context)

            assert result.success is False
            assert 'Policy rejected WordArt' in result.fallback_reason
            assert result.policy_decision is mock_decision
            assert result.alternative_strategies == ['EMF embedding', 'Text-to-path']

    def test_validate_input_success(self):
        """Test input validation with valid element."""
        text_element = ET.Element('text')
        text_element.text = 'Valid Text'

        result = self.builder._validate_input(text_element, self.mock_context)

        assert result['valid'] is True
        assert result['text_content'] == 'Valid Text'

    def test_validate_input_failures(self):
        """Test input validation with various failure cases."""
        # None element
        result = self.builder._validate_input(None, self.mock_context)
        assert result['valid'] is False
        assert 'Text element is None' in result['reason']

        # Invalid element tag
        invalid_element = ET.Element('rect')
        result = self.builder._validate_input(invalid_element, self.mock_context)
        assert result['valid'] is False
        assert 'Invalid element tag' in result['reason']

        # Empty text content
        empty_element = ET.Element('text')
        result = self.builder._validate_input(empty_element, self.mock_context)
        assert result['valid'] is False
        assert 'No text content found' in result['reason']

    def test_calculate_text_complexity(self):
        """Test text complexity calculation."""
        # Simple text
        simple_element = ET.Element('text')
        simple_element.text = 'Hello'
        complexity = self.builder._calculate_text_complexity(simple_element)
        assert 0 < complexity < 2

        # Complex text with special characters
        complex_element = ET.Element('text')
        complex_element.text = 'Hello@#$%^&*()World!\nSecond Line'
        complexity = self.builder._calculate_text_complexity(complex_element)
        assert complexity > 2

        # Text with nested elements
        nested_element = ET.Element('text')
        nested_element.text = 'Hello '
        tspan = ET.SubElement(nested_element, 'tspan')
        tspan.text = 'World'
        complexity = self.builder._calculate_text_complexity(nested_element)
        assert complexity > 1

    def test_analyze_styling(self):
        """Test styling analysis."""
        # Basic styling
        text_element = ET.Element('text')
        text_element.set('font-family', 'Arial')
        text_element.set('font-size', '24')
        text_element.set('fill', '#FF0000')

        analysis = self.builder._analyze_styling(text_element)

        assert analysis['font_family'] == 'Arial'
        assert analysis['font_size'] == '24'
        assert analysis['fill_color'] == '#FF0000'
        assert analysis['has_gradient_fill'] is False
        assert analysis['has_stroke'] is False
        assert analysis['wordart_compatible'] is True

        # Complex styling with gradient
        complex_element = ET.Element('text')
        complex_element.set('fill', 'url(#gradient1)')
        complex_element.set('stroke', '#000000')
        complex_element.set('opacity', '0.5')

        complex_analysis = self.builder._analyze_styling(complex_element)

        assert complex_analysis['has_gradient_fill'] is True
        assert complex_analysis['has_stroke'] is True
        assert complex_analysis['has_opacity'] is True
        assert complex_analysis['style_complexity'] > 1

    def test_analyze_layout(self):
        """Test layout analysis."""
        text_element = ET.Element('text')
        text_element.set('x', '100')
        text_element.set('y', '200')
        text_element.set('font-size', '24')
        text_element.set('text-anchor', 'middle')
        text_element.text = 'Test Text'

        analysis = self.builder._analyze_layout(text_element, self.mock_context)

        assert analysis['x'] == '100'
        assert analysis['y'] == '200'
        assert analysis['text_anchor'] == 'middle'
        assert analysis['has_custom_anchor'] is True
        assert 'estimated_bounds' in analysis

        bounds = analysis['estimated_bounds']
        assert bounds['x'] == 100.0
        assert bounds['y'] == 200.0
        assert bounds['width'] > 0
        assert bounds['height'] > 0

    def test_suggest_alternatives(self):
        """Test alternative strategy suggestions."""
        # Policy decision with complexity issues
        from core.policy.targets import DecisionReason
        decision = TextDecision.emf([DecisionReason.COMPLEX_GEOMETRY, DecisionReason.COMPLEX_TRANSFORM])

        alternatives = self.builder._suggest_alternatives(decision)

        assert len(alternatives) > 0
        assert any('EMF embedding' in alt for alt in alternatives)
        assert any('Matrix decomposition' in alt for alt in alternatives)

    def test_factory_function(self):
        """Test factory function."""
        mock_services = Mock(spec=ConversionServices)
        config = WordArtGenerationConfig(enable_transform_analysis=False)

        builder = create_comprehensive_wordart_builder(mock_services, config)

        assert isinstance(builder, ComprehensiveWordArtBuilder)
        assert builder.services is mock_services
        assert builder.config is config


class TestWordArtGenerationConfig:
    """Test WordArt generation configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = WordArtGenerationConfig()

        assert config.enable_transform_analysis is True
        assert config.max_transform_complexity == 8.0
        assert config.enable_gradient_mapping is True
        assert config.max_gradient_stops == 8
        assert config.enable_path_warping is True
        assert config.min_warp_confidence == 0.6
        assert config.enable_policy_decisions is True
        assert config.timeout_ms == 5000.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = WordArtGenerationConfig(
            enable_transform_analysis=False,
            max_transform_complexity=5.0,
            max_gradient_stops=4,
            min_warp_confidence=0.8
        )

        assert config.enable_transform_analysis is False
        assert config.max_transform_complexity == 5.0
        assert config.max_gradient_stops == 4
        assert config.min_warp_confidence == 0.8


class TestComprehensiveWordArtIntegration:
    """Test integration with all WordArt services."""

    def setup_method(self):
        """Set up integration test environment."""
        self.mock_services = Mock(spec=ConversionServices)
        self.mock_services.unit_converter = Mock()
        self.mock_services.viewport_handler = Mock()
        self.mock_services.font_service = Mock()
        self.mock_services.gradient_service = Mock()
        self.mock_services.pattern_service = Mock()
        self.mock_services.clip_service = Mock()

        self.mock_context = Mock(spec=ConversionContext)
        self.mock_context.services = self.mock_services

        self.builder = ComprehensiveWordArtBuilder(self.mock_services)

    def test_service_initialization_integration(self):
        """Test that all services are properly initialized."""
        # Check integration service
        assert hasattr(self.builder, 'integration_service')
        assert self.builder.integration_service.services is self.mock_services

        # Check transform service
        assert hasattr(self.builder, 'transform_decomposer')

        # Check color service
        assert hasattr(self.builder, 'color_service')
        assert self.builder.color_service.services is self.mock_services

        # Check WordArt builder
        assert hasattr(self.builder, 'wordart_builder')

        # Check warp fitter
        assert hasattr(self.builder, 'warp_fitter')

        # Check policy engine
        assert hasattr(self.builder, 'policy')

    def test_comprehensive_analysis_integration(self):
        """Test comprehensive analysis with all components."""
        text_element = ET.Element('text')
        text_element.text = 'Integration Test'
        text_element.set('transform', 'translate(10,20) scale(1.5)')
        text_element.set('font-family', 'Arial')

        # Add textPath for path analysis
        textpath = ET.SubElement(text_element, 'textPath')
        textpath.set('href', '#path1')

        with patch.object(self.builder.transform_decomposer, 'decompose_transform_string') as mock_decompose, \
             patch.object(self.builder.transform_decomposer, 'analyze_transform_complexity') as mock_analyze:

            # Mock transform analysis
            mock_components = Mock()
            mock_components.translate_x = 10.0
            mock_components.translate_y = 20.0
            mock_components.scale_x = 1.5
            mock_components.scale_y = 1.0
            mock_components.rotation = 0.0
            mock_components.skew_x = 0.0
            mock_components.skew_y = 0.0
            mock_decompose.return_value = mock_components
            mock_analyze.return_value = {'complexity_score': 3.0}

            analysis = self.builder._comprehensive_analysis(text_element, self.mock_context)

            # Verify comprehensive analysis
            assert 'text_content' in analysis
            assert 'text_complexity' in analysis
            assert 'transform_analysis' in analysis
            assert 'path_analysis' in analysis
            assert 'style_analysis' in analysis
            assert 'layout_analysis' in analysis

            # Check text analysis
            assert analysis['text_content'] == 'Integration Test'
            assert analysis['text_complexity'] > 0

            # Check transform analysis integration
            assert analysis['transform_analysis'] is not None
            assert 'components' in analysis['transform_analysis']

    def test_error_handling_integration(self):
        """Test error handling across all service integrations."""
        text_element = ET.Element('text')
        text_element.text = 'Error Test'

        # Test with failing services
        with patch.object(self.builder, '_validate_input', side_effect=Exception("Validation error")):
            result = self.builder.build_wordart(text_element, self.mock_context)

            assert result.success is False
            assert 'Comprehensive generation failed' in result.fallback_reason