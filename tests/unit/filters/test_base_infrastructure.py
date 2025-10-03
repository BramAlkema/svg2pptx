#!/usr/bin/env python3
"""
Tests for the filter system base infrastructure.

This module provides comprehensive testing utilities and base classes
for all filter-related tests, including fixtures, helpers, and common
patterns for testing FilterProcessor implementations.
"""

import pytest
from unittest.mock import Mock, MagicMock
from lxml import etree as ET
from typing import Dict, Any, Optional

from core.filters.base import (
    FilterProcessor,
    FilterContext,
    FilterResult,
    FilterStrategy,
    FilterException,
    FilterValidationError,
    create_filter_context
)
from core.filters.factory import FilterFactory, create_filter_factory


class MockTestFilterProcessor(FilterProcessor):
    """Test implementation of FilterProcessor."""

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        # Simple test: can apply if element has 'test' attribute
        return element.get('test') is not None

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        if not self.can_apply(element, context):
            return self._create_failure_result("Cannot apply to element without 'test' attribute")

        test_value = element.get('test', '')
        if test_value == 'fail':
            return self._create_failure_result("Test configured to fail")

        return self._create_success_result(
            drawingml=f'<a:testEffect test="{test_value}"/>',
            strategy=FilterStrategy.NATIVE
        )


class AlwaysFailProcessor(FilterProcessor):
    """Processor that always fails for testing error handling."""

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        return True

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        return self._create_failure_result("Always fails for testing")


class ConditionalProcessor(FilterProcessor):
    """Processor with configurable behavior for testing."""

    def __init__(self, filter_type: str, policy=None, can_apply_result=True,
                 success=True, strategy=FilterStrategy.NATIVE):
        super().__init__(filter_type, policy)
        self._can_apply_result = can_apply_result
        self._success = success
        self._strategy = strategy

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        return self._can_apply_result

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        if self._success:
            return self._create_success_result(
                drawingml=f'<a:conditionalEffect type="{self.filter_type}"/>',
                strategy=self._strategy
            )
        else:
            return self._create_failure_result("Configured to fail")


@pytest.fixture
def mock_policy():
    """Create a mock policy for testing."""
    policy = Mock()
    policy.decide_filter_strategy = Mock(return_value=FilterStrategy.NATIVE)
    policy.should_use_filter = Mock(return_value=True)
    return policy


@pytest.fixture
def mock_services():
    """Create mock ConversionServices for testing."""
    services = Mock()
    services.unit_converter = Mock()
    services.viewport_handler = Mock()
    services.font_service = Mock()
    services.gradient_service = Mock()
    services.pattern_service = Mock()
    services.clip_service = Mock()
    services.transform_parser = Mock()
    services.color_parser = Mock()
    return services


@pytest.fixture
def basic_filter_context(mock_services):
    """Create a basic FilterContext for testing."""
    return FilterContext(
        element=ET.Element('filter'),
        viewport={'width': 100, 'height': 100},
        services=mock_services
    )


@pytest.fixture
def filter_factory(mock_policy):
    """Create a FilterFactory for testing."""
    factory = FilterFactory(mock_policy)
    factory.register_filter('feTest', MockTestFilterProcessor)
    factory.register_filter('feAlwaysFail', AlwaysFailProcessor)
    return factory


class TestFilterInfrastructure:
    """Test the base filter testing infrastructure."""

    def test_test_filter_processor_can_apply(self):
        """Test TestFilterProcessor can_apply logic."""
        processor = MockTestFilterProcessor('feTest')

        # Element with test attribute
        element_with_test = ET.Element('feTest')
        element_with_test.set('test', 'value')
        context = Mock()

        assert processor.can_apply(element_with_test, context) is True

        # Element without test attribute
        element_without_test = ET.Element('feTest')
        assert processor.can_apply(element_without_test, context) is False

    def test_test_filter_processor_apply_success(self, basic_filter_context):
        """Test TestFilterProcessor successful application."""
        processor = MockTestFilterProcessor('feTest')

        element = ET.Element('feTest')
        element.set('test', 'success')

        result = processor.apply(element, basic_filter_context)

        assert result.is_success() is True
        assert result.get_drawingml() == '<a:testEffect test="success"/>'
        assert result.get_strategy() == FilterStrategy.NATIVE

    def test_test_filter_processor_apply_failure(self, basic_filter_context):
        """Test TestFilterProcessor configured failure."""
        processor = MockTestFilterProcessor('feTest')

        element = ET.Element('feTest')
        element.set('test', 'fail')

        result = processor.apply(element, basic_filter_context)

        assert result.is_success() is False
        assert result.get_error_message() == "Test configured to fail"

    def test_test_filter_processor_cannot_apply(self, basic_filter_context):
        """Test TestFilterProcessor when cannot apply."""
        processor = MockTestFilterProcessor('feTest')

        element = ET.Element('feTest')  # No test attribute

        result = processor.apply(element, basic_filter_context)

        assert result.is_success() is False
        assert "Cannot apply to element" in result.get_error_message()

    def test_always_fail_processor(self, basic_filter_context):
        """Test AlwaysFailProcessor behavior."""
        processor = AlwaysFailProcessor('feAlwaysFail')

        element = ET.Element('feAlwaysFail')

        assert processor.can_apply(element, basic_filter_context) is True

        result = processor.apply(element, basic_filter_context)
        assert result.is_success() is False
        assert result.get_error_message() == "Always fails for testing"

    def test_conditional_processor_success(self, basic_filter_context):
        """Test ConditionalProcessor in success mode."""
        processor = ConditionalProcessor(
            'feConditional',
            can_apply_result=True,
            success=True,
            strategy=FilterStrategy.APPROXIMATION
        )

        element = ET.Element('feConditional')

        assert processor.can_apply(element, basic_filter_context) is True

        result = processor.apply(element, basic_filter_context)
        assert result.is_success() is True
        assert result.get_strategy() == FilterStrategy.APPROXIMATION
        assert 'feConditional' in result.get_drawingml()

    def test_conditional_processor_failure(self, basic_filter_context):
        """Test ConditionalProcessor in failure mode."""
        processor = ConditionalProcessor(
            'feConditional',
            can_apply_result=False,
            success=False
        )

        element = ET.Element('feConditional')

        assert processor.can_apply(element, basic_filter_context) is False

        result = processor.apply(element, basic_filter_context)
        assert result.is_success() is False
        assert result.get_error_message() == "Configured to fail"


class TestFilterContextCreation:
    """Test FilterContext creation utilities."""

    def test_create_filter_context_basic(self, mock_services):
        """Test basic FilterContext creation."""
        element = ET.Element('feBlur')

        context = create_filter_context(
            element=element,
            services=mock_services,
            viewport={'width': 200, 'height': 150}
        )

        assert context.element == element
        assert context.viewport == {'width': 200, 'height': 150}
        assert context.services == mock_services

    def test_create_filter_context_default_viewport(self, mock_services):
        """Test FilterContext creation with default viewport."""
        element = ET.Element('feOffset')

        context = create_filter_context(
            element=element,
            services=mock_services
        )

        assert context.element == element
        assert context.viewport == {'width': 800.0, 'height': 600.0}
        assert context.services == mock_services


class TestFilterFactoryTesting:
    """Test FilterFactory testing utilities."""

    def test_filter_factory_with_test_processors(self, filter_factory):
        """Test FilterFactory with registered test processors."""
        assert filter_factory.is_filter_supported('feTest') is True
        assert filter_factory.is_filter_supported('feAlwaysFail') is True
        assert filter_factory.is_filter_supported('feNonExistent') is False

    def test_create_test_processors(self, filter_factory, basic_filter_context):
        """Test creating test processors from factory."""
        # Create successful processor
        test_processor = filter_factory.create_filter('feTest')
        assert isinstance(test_processor, MockTestFilterProcessor)

        # Create failing processor
        fail_processor = filter_factory.create_filter('feAlwaysFail')
        assert isinstance(fail_processor, AlwaysFailProcessor)

        # Test element for successful processing
        success_element = ET.Element('feTest')
        success_element.set('test', 'value')

        result = test_processor.apply(success_element, basic_filter_context)
        assert result.is_success() is True

        # Test element for failing processing
        fail_element = ET.Element('feAlwaysFail')
        result = fail_processor.apply(fail_element, basic_filter_context)
        assert result.is_success() is False


class TestFilterTestingPatterns:
    """Test common testing patterns for filters."""

    def test_element_creation_patterns(self):
        """Test common SVG element creation patterns for testing."""
        # Basic filter element
        filter_element = ET.Element('filter', id='test-filter')
        assert filter_element.get('id') == 'test-filter'

        # Filter primitive with attributes
        blur_element = ET.Element('feGaussianBlur')
        blur_element.set('stdDeviation', '2')
        blur_element.set('in', 'SourceGraphic')

        assert blur_element.get('stdDeviation') == '2'
        assert blur_element.get('in') == 'SourceGraphic'

        # Nested filter structure
        filter_def = ET.Element('filter', id='complex-filter')
        offset = ET.SubElement(filter_def, 'feOffset')
        offset.set('dx', '3')
        offset.set('dy', '3')

        blur = ET.SubElement(filter_def, 'feGaussianBlur')
        blur.set('stdDeviation', '1')

        assert len(list(filter_def)) == 2
        assert filter_def[0].tag == 'feOffset'
        assert filter_def[1].tag == 'feGaussianBlur'

    def test_context_mocking_patterns(self, mock_services):
        """Test common context mocking patterns."""
        # Configure unit converter mock
        mock_services.unit_converter.to_emu.return_value = 12700
        mock_services.unit_converter.from_emu.return_value = 1.0

        # Configure transform parser mock
        mock_services.transform_parser.parse_transform.return_value = [1, 0, 0, 1, 0, 0]

        # Configure color parser mock
        mock_services.color_parser.parse_color.return_value = {'r': 255, 'g': 0, 'b': 0}

        # Create context and verify mocks work
        context = create_filter_context(
            element=ET.Element('feTest'),
            services=mock_services,
            viewport={'width': 100, 'height': 100}
        )

        # Test that mocks are properly configured
        assert context.services.unit_converter.to_emu(1.0) == 12700
        assert context.services.transform_parser.parse_transform('translate(10,20)') == [1, 0, 0, 1, 0, 0]
        assert context.services.color_parser.parse_color('red')['r'] == 255

    def test_assertion_patterns(self, basic_filter_context):
        """Test common assertion patterns for filter results."""
        processor = MockTestFilterProcessor('feTest')

        # Success pattern
        success_element = ET.Element('feTest')
        success_element.set('test', 'success')

        result = processor.apply(success_element, basic_filter_context)

        # Standard success assertions
        assert result.is_success(), f"Expected success, got error: {result.get_error_message()}"
        assert result.get_drawingml(), "Expected DrawingML output"
        assert result.get_strategy() in [FilterStrategy.NATIVE, FilterStrategy.APPROXIMATION, FilterStrategy.EMF_RASTERIZE]

        # Failure pattern
        fail_element = ET.Element('feTest')
        fail_element.set('test', 'fail')

        fail_result = processor.apply(fail_element, basic_filter_context)

        # Standard failure assertions
        assert not fail_result.is_success(), "Expected failure"
        assert fail_result.get_error_message(), "Expected error message"
        assert not fail_result.get_drawingml(), "Should not have DrawingML on failure"


class TestFilterExceptionHandling:
    """Test filter exception handling patterns."""

    def test_filter_exception_creation(self):
        """Test FilterException creation and handling."""
        try:
            raise FilterException("Test filter error")
        except FilterException as e:
            assert str(e) == "Test filter error"
            assert isinstance(e, Exception)

    def test_filter_validation_error(self):
        """Test FilterValidationError creation and handling."""
        try:
            raise FilterValidationError("Invalid filter configuration")
        except FilterValidationError as e:
            assert str(e) == "Invalid filter configuration"
            assert isinstance(e, FilterException)

    def test_processor_exception_handling(self, basic_filter_context):
        """Test proper exception handling in processors."""
        class ExceptionProcessor(FilterProcessor):
            def can_apply(self, element, context):
                return True

            def apply(self, element, context):
                # Simulate processing error
                raise RuntimeError("Processing failed")

        processor = ExceptionProcessor('feException')
        element = ET.Element('feException')

        # Processor should handle exceptions gracefully
        try:
            result = processor.apply(element, basic_filter_context)
            # If no exception handling in base class, this will raise
            assert False, "Expected exception to be raised"
        except RuntimeError as e:
            assert str(e) == "Processing failed"


if __name__ == '__main__':
    pytest.main([__file__])