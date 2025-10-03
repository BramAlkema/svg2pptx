#!/usr/bin/env python3
"""
Tests for FilterService integration with FilterFactory.

Validates the enhanced FilterService with factory-based processing
while maintaining backward compatibility with legacy filters.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from lxml import etree as ET

from core.services.filter_service import FilterService
from core.filters import FilterProcessor, FilterContext, FilterResult, FilterStrategy


class MockProcessor(FilterProcessor):
    """Mock processor for testing factory integration."""

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        return True

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        return self._create_success_result(
            drawingml='<a:factoryEffect/>',
            strategy=FilterStrategy.NATIVE
        )


class TestFilterServiceIntegration:
    """Test FilterService with factory integration."""

    def test_service_initialization_basic(self):
        """Test basic FilterService initialization."""
        service = FilterService()

        assert service._filter_factory is not None
        assert service._services is None
        assert service._policy is None
        assert len(service._legacy_filters) == 4
        assert len(service._factory_filters) == 0

    def test_service_initialization_with_policy_and_services(self):
        """Test FilterService initialization with policy and services."""
        policy = Mock()
        services = Mock()

        service = FilterService(policy=policy, services=services)

        assert service._policy == policy
        assert service._services == services
        assert service._filter_factory.policy == policy

    def test_should_use_factory_for_registered_filter(self):
        """Test factory usage decision for registered filters."""
        service = FilterService()

        # Register a filter in factory
        service.register_filter_processor('feTest', MockProcessor)

        assert service._should_use_factory('feTest') is True
        assert 'feTest' in service._factory_filters

    def test_should_use_factory_for_legacy_filter(self):
        """Test factory usage decision for legacy filters."""
        service = FilterService()

        # Legacy filters should not use factory
        assert service._should_use_factory('feGaussianBlur') is False
        assert service._should_use_factory('feDropShadow') is False

    def test_should_use_factory_for_core_supported_filter(self):
        """Test factory usage for core supported filters."""
        service = FilterService()

        # Core auto-registered non-legacy filters should use factory
        assert service._should_use_factory('feOffset') is True
        assert 'feOffset' in service._factory_filters

    def test_process_with_factory_success(self):
        """Test successful factory processing."""
        services = Mock()
        service = FilterService(services=services)

        # Register processor
        service.register_filter_processor('feTest', MockProcessor)

        # Create test element
        element = ET.Element('feTest')

        # Mock factory to return our processor
        mock_processor = MockProcessor('feTest')
        service._filter_factory.create_filter_for_element = Mock(return_value=mock_processor)

        result = service._process_with_factory(element)

        assert result == '<a:factoryEffect/>'

    def test_process_with_factory_no_services(self):
        """Test factory processing without services."""
        service = FilterService()  # No services

        element = ET.Element('feTest')
        result = service._process_with_factory(element)

        assert result is None

    def test_process_with_factory_no_processor(self):
        """Test factory processing when no processor available."""
        services = Mock()
        service = FilterService(services=services)

        element = ET.Element('feUnsupported')

        # Mock factory to return None
        service._filter_factory.create_filter_for_element = Mock(return_value=None)

        result = service._process_with_factory(element)
        assert result is None

    def test_process_with_factory_processor_cannot_apply(self):
        """Test factory processing when processor cannot apply."""
        services = Mock()
        service = FilterService(services=services)

        element = ET.Element('feTest')

        # Mock processor that cannot apply
        mock_processor = Mock()
        mock_processor.can_apply.return_value = False
        service._filter_factory.create_filter_for_element = Mock(return_value=mock_processor)

        result = service._process_with_factory(element)
        assert result is None

    def test_process_with_factory_processing_failure(self):
        """Test factory processing when apply fails."""
        services = Mock()
        service = FilterService(services=services)

        element = ET.Element('feTest')

        # Mock processor that fails processing
        mock_processor = Mock()
        mock_processor.can_apply.return_value = True
        failed_result = Mock()
        failed_result.is_success.return_value = False
        failed_result.get_error_message.return_value = "Processing failed"
        mock_processor.apply.return_value = failed_result

        service._filter_factory.create_filter_for_element = Mock(return_value=mock_processor)

        result = service._process_with_factory(element)
        assert result is None

    def test_convert_filter_definition_with_factory_processing(self):
        """Test filter definition conversion using factory."""
        services = Mock()
        service = FilterService(services=services)

        # Register a processor
        service.register_filter_processor('feTest', MockProcessor)

        # Create filter with test element
        filter_element = ET.Element('filter', id='test-filter')
        test_child = ET.SubElement(filter_element, 'feTest')

        # Mock factory processing
        service._process_with_factory = Mock(return_value='<a:factoryEffect/>')

        result = service._convert_filter_definition(filter_element)

        assert '<a:factoryEffect/>' in result
        service._process_with_factory.assert_called_once()

    def test_convert_filter_definition_factory_fallback_to_legacy(self):
        """Test fallback to legacy processing when factory fails."""
        services = Mock()
        service = FilterService(services=services)

        # Create filter with legacy element
        filter_element = ET.Element('filter', id='test-filter')
        blur_child = ET.SubElement(filter_element, 'feGaussianBlur')
        blur_child.set('stdDeviation', '2')

        # Mock factory processing to fail
        service._process_with_factory = Mock(side_effect=Exception("Factory failed"))

        result = service._convert_filter_definition(filter_element)

        # Should fall back to legacy processing
        assert 'a:blur' in result
        assert 'rad=' in result

    def test_convert_filter_definition_unsupported_filter(self):
        """Test handling of completely unsupported filters."""
        service = FilterService()

        # Create filter with unsupported element
        filter_element = ET.Element('filter', id='test-filter')
        unsupported_child = ET.SubElement(filter_element, 'feUnsupported')

        result = service._convert_filter_definition(filter_element)

        # Should contain unsupported comment
        assert 'Unsupported filter: feUnsupported' in result

    def test_register_filter_processor_success(self):
        """Test successful filter processor registration."""
        service = FilterService()

        service.register_filter_processor('feTest', MockProcessor)

        assert 'feTest' in service._factory_filters
        assert service._filter_factory.is_filter_supported('feTest')

    def test_register_filter_processor_failure(self):
        """Test handling of filter processor registration failure."""
        service = FilterService()

        # Mock factory to raise exception
        service._filter_factory.register_filter = Mock(side_effect=Exception("Registration failed"))

        # Should not raise exception
        service.register_filter_processor('feTest', MockProcessor)

        # Filter should not be in factory filters
        assert 'feTest' not in service._factory_filters

    def test_get_filter_coverage(self):
        """Test filter coverage reporting."""
        service = FilterService()

        coverage = service.get_filter_coverage()

        assert isinstance(coverage, dict)
        assert 'feGaussianBlur' in coverage
        assert 'feDropShadow' in coverage
        assert len(coverage) > 10  # Should have standard filters

    def test_get_filter_factory(self):
        """Test factory instance access."""
        service = FilterService()

        factory = service.get_filter_factory()

        assert factory is service._filter_factory

    def test_backward_compatibility_legacy_methods(self):
        """Test that legacy FilterService methods still work."""
        service = FilterService()

        # Test filter registration (legacy)
        filter_element = ET.Element('filter', id='test')
        service.register_filter('test', filter_element)

        assert 'test' in service._filter_cache

        # Test filter retrieval (legacy)
        content = service.get_filter_content('test')
        assert content is not None

    def test_legacy_filter_processing_unchanged(self):
        """Test that legacy filters still process correctly."""
        service = FilterService()

        # Create filter with legacy Gaussian blur
        filter_element = ET.Element('filter', id='blur-filter')
        blur_child = ET.SubElement(filter_element, 'feGaussianBlur')
        blur_child.set('stdDeviation', '3')

        result = service._convert_filter_definition(filter_element)

        # Should contain legacy blur processing
        assert 'a:blur' in result
        assert 'rad=' in result
        # Should have correct radius calculation (3 * 12700)
        assert '38100' in result

    def test_mixed_filter_processing(self):
        """Test filter with both legacy and factory elements."""
        services = Mock()
        service = FilterService(services=services)

        # Register factory processor
        service.register_filter_processor('feTest', MockProcessor)

        # Create filter with mixed elements
        filter_element = ET.Element('filter', id='mixed-filter')
        blur_child = ET.SubElement(filter_element, 'feGaussianBlur')
        blur_child.set('stdDeviation', '2')
        test_child = ET.SubElement(filter_element, 'feTest')

        # Mock factory processing for feTest
        service._process_with_factory = Mock(return_value='<a:factoryEffect/>')

        result = service._convert_filter_definition(filter_element)

        # Should contain both legacy and factory processing
        assert 'a:blur' in result  # Legacy
        assert '<a:factoryEffect/>' in result  # Factory

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        service = FilterService()

        # Add items to caches
        service._filter_cache['test'] = Mock()
        service._conversion_cache['test'] = 'cached_result'

        service.clear_cache()

        assert len(service._filter_cache) == 0
        assert len(service._conversion_cache) == 0


if __name__ == '__main__':
    pytest.main([__file__])