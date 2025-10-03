#!/usr/bin/env python3
"""
Tests for FilterProcessor base classes and infrastructure.

Validates the foundation of the filter processing system with policy
integration and clean slate architecture patterns.
"""

import pytest
from unittest.mock import Mock, MagicMock
from lxml import etree as ET

from core.filters.base import (
    FilterProcessor,
    FilterContext,
    FilterResult,
    FilterStrategy,
    FilterException,
    FilterValidationError,
    create_filter_context
)


class MockFilterProcessor(FilterProcessor):
    """Mock implementation for testing FilterProcessor interface."""

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        """Test implementation that accepts all elements."""
        return True

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        """Test implementation that generates simple blur effect."""
        return self._create_success_result(
            drawingml='<a:blur rad="50000"/>',
            strategy=FilterStrategy.NATIVE,
            test_metadata="mock_value"
        )


class TestFilterContext:
    """Test FilterContext dataclass and methods."""

    def test_filter_context_creation(self):
        """Test basic FilterContext creation with required fields."""
        element = ET.Element('filter')
        services = Mock()
        viewport = {'width': 100, 'height': 200}

        context = FilterContext(
            element=element,
            viewport=viewport,
            services=services
        )

        assert context.element == element
        assert context.viewport == viewport
        assert context.services == services
        assert context.properties == {}
        assert context.cache == {}

    def test_filter_context_validation_missing_element(self):
        """Test validation fails with missing element."""
        services = Mock()
        viewport = {'width': 100, 'height': 200}

        with pytest.raises(FilterValidationError, match="requires a valid SVG element"):
            FilterContext(
                element=None,
                viewport=viewport,
                services=services
            )

    def test_filter_context_validation_missing_services(self):
        """Test validation fails with missing services."""
        element = ET.Element('filter')
        viewport = {'width': 100, 'height': 200}

        with pytest.raises(FilterValidationError, match="requires ConversionServices"):
            FilterContext(
                element=element,
                viewport=viewport,
                services=None
            )

    def test_filter_context_validation_invalid_viewport(self):
        """Test validation fails with invalid viewport."""
        element = ET.Element('filter')
        services = Mock()

        with pytest.raises(FilterValidationError, match="requires valid viewport dictionary"):
            FilterContext(
                element=element,
                viewport=None,
                services=services
            )

    def test_get_property(self):
        """Test property retrieval methods."""
        element = ET.Element('filter')
        services = Mock()
        viewport = {'width': 100, 'height': 200}
        properties = {'opacity': '0.5', 'blend-mode': 'multiply'}

        context = FilterContext(
            element=element,
            viewport=viewport,
            services=services,
            properties=properties
        )

        assert context.get_property('opacity') == '0.5'
        assert context.get_property('blend-mode') == 'multiply'
        assert context.get_property('missing', 'default') == 'default'

    def test_get_element_attribute(self):
        """Test element attribute retrieval."""
        element = ET.Element('filter')
        element.set('id', 'test-filter')
        element.set('x', '10')

        services = Mock()
        viewport = {'width': 100, 'height': 200}

        context = FilterContext(
            element=element,
            viewport=viewport,
            services=services
        )

        assert context.get_element_attribute('id') == 'test-filter'
        assert context.get_element_attribute('x') == '10'
        assert context.get_element_attribute('missing', 'default') == 'default'

    def test_get_viewport_dimension(self):
        """Test viewport dimension retrieval."""
        element = ET.Element('filter')
        services = Mock()
        viewport = {'width': 100.5, 'height': 200.3}

        context = FilterContext(
            element=element,
            viewport=viewport,
            services=services
        )

        assert context.get_viewport_dimension('width') == 100.5
        assert context.get_viewport_dimension('height') == 200.3
        assert context.get_viewport_dimension('missing', 42.0) == 42.0

    def test_service_properties(self):
        """Test access to services through properties."""
        element = ET.Element('filter')
        services = Mock()
        services.unit_converter = Mock()
        services.color_parser = Mock()
        services.transform_parser = Mock()
        viewport = {'width': 100, 'height': 200}

        context = FilterContext(
            element=element,
            viewport=viewport,
            services=services
        )

        assert context.unit_converter == services.unit_converter
        assert context.color_parser == services.color_parser
        assert context.transform_parser == services.transform_parser


class TestFilterResult:
    """Test FilterResult dataclass and methods."""

    def test_successful_filter_result(self):
        """Test creation of successful FilterResult."""
        from core.policy.targets import PolicyDecision, DecisionReason

        decision = PolicyDecision(
            use_native=True,
            reasons=[DecisionReason.SIMPLE_CONTENT],
            confidence=0.9,
            estimated_quality=0.95,
            estimated_performance=0.8
        )

        result = FilterResult(
            success=True,
            drawingml='<a:blur rad="50000"/>',
            strategy=FilterStrategy.NATIVE,
            policy_decision=decision,
            metadata={'filter_type': 'blur'}
        )

        assert result.is_success()
        assert result.get_drawingml() == '<a:blur rad="50000"/>'
        assert result.get_strategy() == FilterStrategy.NATIVE
        assert result.is_native_rendering()
        assert not result.requires_emf()
        assert result.get_quality_estimate() == 0.95

    def test_failed_filter_result(self):
        """Test creation of failed FilterResult."""
        result = FilterResult(
            success=False,
            error_message="Processing failed"
        )

        assert not result.is_success()
        assert result.get_drawingml() is None
        assert result.get_error_message() == "Processing failed"

    def test_failed_result_validation(self):
        """Test validation of failed results requires error message."""
        with pytest.raises(FilterValidationError, match="must have non-empty error_message"):
            FilterResult(success=False)

    def test_emf_strategy_detection(self):
        """Test EMF strategy detection methods."""
        result = FilterResult(
            success=True,
            drawingml="",
            strategy=FilterStrategy.EMF_RASTERIZE
        )

        assert result.requires_emf()
        assert not result.is_native_rendering()

    def test_metadata_handling(self):
        """Test metadata initialization and retrieval."""
        result = FilterResult(
            success=True,
            drawingml='<a:effect/>',
            metadata={'key': 'value'}
        )

        metadata = result.get_metadata()
        assert metadata['key'] == 'value'

        # Test with no metadata
        result_no_meta = FilterResult(success=True, drawingml='<a:effect/>')
        assert result_no_meta.get_metadata() == {}


class TestFilterProcessor:
    """Test FilterProcessor abstract base class."""

    def test_filter_processor_initialization(self):
        """Test FilterProcessor initialization."""
        policy = Mock()
        processor = MockFilterProcessor("test_filter", policy)

        assert processor.filter_type == "test_filter"
        assert processor.policy == policy
        assert hasattr(processor, 'logger')

    def test_can_apply_interface(self):
        """Test can_apply interface method."""
        processor = MockFilterProcessor("test_filter")
        element = ET.Element('filter')
        context = Mock(spec=FilterContext)

        assert processor.can_apply(element, context) is True

    def test_apply_interface(self):
        """Test apply interface method."""
        processor = MockFilterProcessor("test_filter")
        element = ET.Element('filter')
        context = Mock(spec=FilterContext)

        result = processor.apply(element, context)

        assert isinstance(result, FilterResult)
        assert result.is_success()
        assert result.get_drawingml() == '<a:blur rad="50000"/>'

    def test_validate_parameters_default(self):
        """Test default parameter validation."""
        processor = MockFilterProcessor("test_filter")
        element = ET.Element('filter')
        context = Mock(spec=FilterContext)

        assert processor.validate_parameters(element, context) is True

    def test_validate_parameters_with_none(self):
        """Test parameter validation with None values."""
        processor = MockFilterProcessor("test_filter")

        assert processor.validate_parameters(None, Mock()) is False
        assert processor.validate_parameters(Mock(), None) is False

    def test_policy_decision_without_policy(self):
        """Test policy decision making without policy engine."""
        processor = MockFilterProcessor("test_filter")
        element = ET.Element('filter')
        context = Mock(spec=FilterContext)

        decision = processor._make_policy_decision(element, context)

        assert decision.use_native is True
        assert decision.confidence == 0.8

    def test_policy_decision_with_policy(self):
        """Test policy decision making with policy engine."""
        from core.policy.targets import PolicyDecision, DecisionReason

        mock_decision = PolicyDecision(
            use_native=True,
            reasons=[DecisionReason.QUALITY_PRIORITY],
            confidence=0.95,
            estimated_quality=0.9,
            estimated_performance=0.85
        )

        policy = Mock()
        policy.decide_filter_strategy.return_value = mock_decision

        processor = MockFilterProcessor("test_filter", policy)
        element = ET.Element('filter')
        context = Mock(spec=FilterContext)

        decision = processor._make_policy_decision(element, context, complexity=0.3)

        policy.decide_filter_strategy.assert_called_once_with(
            filter_type="test_filter",
            complexity=0.3
        )
        assert decision == mock_decision

    def test_create_success_result(self):
        """Test success result creation helper."""
        processor = MockFilterProcessor("test_filter")

        result = processor._create_success_result(
            drawingml='<a:test/>',
            strategy=FilterStrategy.APPROXIMATION,
            custom_meta="value"
        )

        assert result.is_success()
        assert result.get_drawingml() == '<a:test/>'
        assert result.get_strategy() == FilterStrategy.APPROXIMATION
        metadata = result.get_metadata()
        assert metadata['filter_type'] == 'test_filter'
        assert metadata['processing_strategy'] == 'approximation'
        assert metadata['custom_meta'] == 'value'

    def test_create_failure_result(self):
        """Test failure result creation helper."""
        processor = MockFilterProcessor("test_filter")

        result = processor._create_failure_result(
            error_message="Test error",
            error_code=123
        )

        assert not result.is_success()
        assert result.get_error_message() == "Test error"
        metadata = result.get_metadata()
        assert metadata['filter_type'] == 'test_filter'
        assert metadata['error'] == 'Test error'
        assert metadata['error_code'] == 123

    def test_get_element_localname(self):
        """Test element local name extraction."""
        processor = MockFilterProcessor("test_filter")

        # Test with namespace
        ns_element = ET.Element('{http://www.w3.org/2000/svg}filter')
        assert processor._get_element_localname(ns_element) == 'filter'

        # Test without namespace
        simple_element = ET.Element('blur')
        assert processor._get_element_localname(simple_element) == 'blur'

        # Test with None tag
        mock_element = Mock()
        mock_element.tag = None
        assert processor._get_element_localname(mock_element) == ""

    def test_string_representations(self):
        """Test string representation methods."""
        processor = MockFilterProcessor("test_filter")

        str_repr = str(processor)
        assert "MockFilterProcessor" in str_repr
        assert "test_filter" in str_repr

        full_repr = repr(processor)
        assert "MockFilterProcessor" in full_repr
        assert "filter_type='test_filter'" in full_repr


class TestCreateFilterContext:
    """Test create_filter_context factory function."""

    def test_create_filter_context_with_viewport(self):
        """Test factory function with custom viewport."""
        element = ET.Element('filter')
        services = Mock()
        viewport = {'width': 1024, 'height': 768}

        context = create_filter_context(element, services, viewport)

        assert isinstance(context, FilterContext)
        assert context.element == element
        assert context.services == services
        assert context.viewport == viewport

    def test_create_filter_context_default_viewport(self):
        """Test factory function with default viewport."""
        element = ET.Element('filter')
        services = Mock()

        context = create_filter_context(element, services)

        assert isinstance(context, FilterContext)
        assert context.viewport == {'width': 800.0, 'height': 600.0}


if __name__ == '__main__':
    pytest.main([__file__])