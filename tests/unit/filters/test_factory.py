#!/usr/bin/env python3
"""
Tests for FilterFactory dynamic filter creation system.

Validates filter registration, creation, policy integration,
and fallback handling mechanisms.
"""

import pytest
from unittest.mock import Mock, MagicMock
from lxml import etree as ET

from core.filters.factory import (
    FilterFactory,
    FilterRegistrationError,
    FilterNotFoundError,
    create_filter_factory
)
from core.filters.base import FilterProcessor, FilterContext, FilterResult, FilterStrategy


class MockFilterProcessor(FilterProcessor):
    """Mock filter processor for testing."""

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        return True

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        return self._create_success_result(
            drawingml='<a:mockEffect/>',
            strategy=FilterStrategy.NATIVE
        )


class AnotherMockProcessor(FilterProcessor):
    """Another mock processor for testing registration."""

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        return True

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        return self._create_success_result(
            drawingml='<a:anotherEffect/>',
            strategy=FilterStrategy.APPROXIMATION
        )


class TestFilterFactory:
    """Test FilterFactory core functionality."""

    def test_factory_initialization(self):
        """Test FilterFactory initialization with and without policy."""
        # Without policy
        factory = FilterFactory()
        assert factory.policy is None
        assert len(factory._filter_registry) == 16  # Auto-registered core filters
        assert len(factory._supported_filters) == 16  # Core filters

        # With policy
        policy = Mock()
        factory_with_policy = FilterFactory(policy)
        assert factory_with_policy.policy == policy

    def test_register_filter_success(self):
        """Test successful filter registration."""
        factory = FilterFactory()

        factory.register_filter('feTest', MockFilterProcessor)

        assert 'feTest' in factory._filter_registry
        assert 'feTest' in factory._supported_filters
        assert factory._filter_registry['feTest'] == MockFilterProcessor

    def test_register_filter_invalid_type(self):
        """Test registration with invalid filter type."""
        factory = FilterFactory()

        with pytest.raises(FilterRegistrationError, match="Filter type cannot be empty"):
            factory.register_filter('', MockFilterProcessor)

    def test_register_filter_invalid_class(self):
        """Test registration with invalid processor class."""
        factory = FilterFactory()

        class NotAProcessor:
            pass

        with pytest.raises(FilterRegistrationError, match="must inherit from FilterProcessor"):
            factory.register_filter('feInvalid', NotAProcessor)

    def test_register_filter_override_warning(self, caplog):
        """Test warning when overriding existing registration."""
        factory = FilterFactory()

        # Register first processor
        factory.register_filter('feTest', MockFilterProcessor)

        # Override with different processor
        factory.register_filter('feTest', AnotherMockProcessor)

        assert factory._filter_registry['feTest'] == AnotherMockProcessor
        assert 'Overriding existing filter registration' in caplog.text

    def test_unregister_filter(self):
        """Test filter unregistration."""
        factory = FilterFactory()
        factory.register_filter('feTest', MockFilterProcessor)

        # Unregister existing filter
        result = factory.unregister_filter('feTest')
        assert result is True
        assert 'feTest' not in factory._filter_registry
        assert 'feTest' not in factory._supported_filters

        # Try to unregister non-existent filter
        result = factory.unregister_filter('feNonExistent')
        assert result is False

    def test_create_filter_success(self):
        """Test successful filter creation."""
        factory = FilterFactory()
        factory.register_filter('feTest', MockFilterProcessor)

        processor = factory.create_filter('feTest')

        assert processor is not None
        assert isinstance(processor, MockFilterProcessor)
        assert processor.filter_type == 'feTest'

    def test_create_filter_not_found(self):
        """Test filter creation for unregistered type."""
        factory = FilterFactory()

        processor = factory.create_filter('feNonExistent')
        assert processor is None

    def test_create_filter_creation_failure(self):
        """Test handling of processor creation failures."""
        factory = FilterFactory()

        # Mock a processor class that raises exception during creation
        class FailingProcessor(FilterProcessor):
            def __init__(self, *args, **kwargs):
                raise ValueError("Creation failed")

            def can_apply(self, element, context):
                return True

            def apply(self, element, context):
                return Mock()

        factory.register_filter('feFailing', FailingProcessor)

        with pytest.raises(FilterRegistrationError, match="Failed to create filter processor"):
            factory.create_filter('feFailing')

    def test_create_filter_for_element(self):
        """Test filter creation from SVG element."""
        factory = FilterFactory()
        factory.register_filter('feBlur', MockFilterProcessor)

        # Test with namespaced element
        element = ET.Element('{http://www.w3.org/2000/svg}feBlur')
        processor = factory.create_filter_for_element(element)
        assert isinstance(processor, MockFilterProcessor)

        # Test with simple element - feOffset is now auto-registered
        simple_element = ET.Element('feOffset')
        processor = factory.create_filter_for_element(simple_element)
        assert processor is not None  # Auto-registered core filter

        # Test with None element
        processor = factory.create_filter_for_element(None)
        assert processor is None

    def test_is_filter_supported(self):
        """Test filter support checking."""
        factory = FilterFactory()
        factory.register_filter('feTest', MockFilterProcessor)

        assert factory.is_filter_supported('feTest') is True
        assert factory.is_filter_supported('feNonExistent') is False

        # Test with fallback handler
        fallback = MockFilterProcessor('feFallback')
        factory.register_fallback_handler('feFallback', fallback)
        assert factory.is_filter_supported('feFallback') is True

    def test_get_supported_filters(self):
        """Test getting supported filters list."""
        factory = FilterFactory()
        factory.register_filter('feTest1', MockFilterProcessor)
        factory.register_filter('feTest2', AnotherMockProcessor)

        supported = factory.get_supported_filters()
        assert 'feTest1' in supported
        assert 'feTest2' in supported

        # Verify it's a copy (modification doesn't affect original)
        supported.add('feAdded')
        assert 'feAdded' not in factory.get_supported_filters()

    def test_get_filter_coverage(self):
        """Test filter coverage reporting."""
        factory = FilterFactory()
        factory.register_filter('feBlur', MockFilterProcessor)

        coverage = factory.get_filter_coverage()

        # Should include all standard SVG filters
        expected_filters = {
            'feBlend', 'feColorMatrix', 'feComponentTransfer', 'feComposite',
            'feConvolveMatrix', 'feDiffuseLighting', 'feDisplacementMap',
            'feDropShadow', 'feFlood', 'feGaussianBlur', 'feImage', 'feMerge',
            'feMorphology', 'feOffset', 'feSpecularLighting', 'feTile', 'feTurbulence'
        }

        assert set(coverage.keys()) == expected_filters
        # Core filters are now auto-registered
        assert coverage['feGaussianBlur'] is True  # Core filter
        assert coverage['feOffset'] is True  # Now implemented
        assert coverage['feMerge'] is False  # Not implemented yet

    def test_register_fallback_handler(self):
        """Test fallback handler registration."""
        factory = FilterFactory()
        fallback = MockFilterProcessor('feFallback')

        factory.register_fallback_handler('feUnsupported', fallback)

        assert 'feUnsupported' in factory._fallback_handlers
        assert factory._fallback_handlers['feUnsupported'] == fallback

        # Test using fallback
        processor = factory.create_filter('feUnsupported')
        assert processor == fallback

    def test_normalize_filter_type(self):
        """Test filter type normalization."""
        factory = FilterFactory()

        # Test namespace removal
        assert factory._normalize_filter_type('{http://www.w3.org/2000/svg}feBlur') == 'feBlur'

        # Test simple name
        assert factory._normalize_filter_type('feOffset') == 'feOffset'

        # Test whitespace removal
        assert factory._normalize_filter_type('  feFlood  ') == 'feFlood'

        # Test empty string
        assert factory._normalize_filter_type('') == ''

        # Test malformed namespace
        assert factory._normalize_filter_type('{malformed') == '{malformed'

    def test_get_element_tag_name(self):
        """Test element tag name extraction."""
        factory = FilterFactory()

        # Test normal element
        element = ET.Element('feBlur')
        assert factory._get_element_tag_name(element) == 'feBlur'

        # Test namespaced element
        ns_element = ET.Element('{http://www.w3.org/2000/svg}feOffset')
        assert factory._get_element_tag_name(ns_element) == 'feOffset'

        # Test None element
        assert factory._get_element_tag_name(None) == ''

        # Test element with None tag
        mock_element = Mock()
        mock_element.tag = None
        assert factory._get_element_tag_name(mock_element) == ''

    def test_validate_configuration(self):
        """Test factory configuration validation."""
        factory = FilterFactory()
        factory.register_filter('feTest', MockFilterProcessor)

        validation = factory.validate_configuration()

        assert 'total_filters' in validation
        assert 'supported_filters' in validation
        assert 'coverage_percentage' in validation
        assert 'registered_processors' in validation
        assert 'fallback_handlers' in validation
        assert 'missing_filters' in validation
        assert 'configuration_valid' in validation

        assert validation['total_filters'] == 17  # Standard SVG filters
        assert validation['registered_processors'] == 17  # 16 core + 1 test
        assert validation['fallback_handlers'] == 0
        assert validation['configuration_valid'] is True
        assert isinstance(validation['missing_filters'], list)

    def test_string_representations(self):
        """Test string representation methods."""
        policy = Mock()
        factory = FilterFactory(policy)
        factory.register_filter('feTest', MockFilterProcessor)

        str_repr = str(factory)
        assert 'FilterFactory' in str_repr
        assert 'registered=17' in str_repr  # 16 core + 1 test
        assert 'policy=enabled' in str_repr

        full_repr = repr(factory)
        assert 'FilterFactory' in full_repr
        assert 'feTest' in full_repr

    def test_core_filters_initialization(self):
        """Test that core filters are properly initialized."""
        factory = FilterFactory()

        # Check that core filters are marked as supported (feMerge is NOT auto-registered)
        core_filters = ['feGaussianBlur', 'feDropShadow', 'feDiffuseLighting',
                       'feSpecularLighting']

        for filter_type in core_filters:
            assert filter_type in factory._supported_filters

    def test_policy_integration(self):
        """Test policy engine integration."""
        policy = Mock()
        factory = FilterFactory(policy)
        factory.register_filter('feTest', MockFilterProcessor)

        processor = factory.create_filter('feTest')

        # Verify policy is passed to processor
        assert processor.policy == policy


class TestCreateFilterFactory:
    """Test create_filter_factory function."""

    def test_create_filter_factory_without_policy(self):
        """Test factory creation without policy."""
        factory = create_filter_factory()

        assert isinstance(factory, FilterFactory)
        assert factory.policy is None

    def test_create_filter_factory_with_policy(self):
        """Test factory creation with policy."""
        policy = Mock()
        factory = create_filter_factory(policy)

        assert isinstance(factory, FilterFactory)
        assert factory.policy == policy


if __name__ == '__main__':
    pytest.main([__file__])