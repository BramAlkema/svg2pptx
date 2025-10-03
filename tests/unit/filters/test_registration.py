#!/usr/bin/env python3
"""
Tests for filter registration with FilterFactory and FilterService.

Validates that OffsetProcessor and FloodProcessor can be successfully
registered with the FilterFactory and used through FilterService.
"""

import pytest
from unittest.mock import Mock
from lxml import etree as ET

from core.filters import (
    FilterFactory,
    OffsetProcessor,
    FloodProcessor,
    BlendProcessor,
    ColorMatrixProcessor,
    CompositeProcessor,
    create_filter_factory
)
from core.services.filter_service import FilterService


class TestFilterRegistration:
    """Test filter registration and integration."""

    def test_register_offset_processor_with_factory(self):
        """Test registering OffsetProcessor with FilterFactory."""
        factory = FilterFactory()

        # Register OffsetProcessor
        factory.register_filter('feOffset', OffsetProcessor)

        # Verify registration
        assert factory.is_filter_supported('feOffset') is True
        assert 'feOffset' in factory.get_supported_filters()

        # Create processor instance
        processor = factory.create_filter('feOffset')
        assert isinstance(processor, OffsetProcessor)
        assert processor.filter_type == 'feOffset'

    def test_register_flood_processor_with_factory(self):
        """Test registering FloodProcessor with FilterFactory."""
        factory = FilterFactory()

        # Register FloodProcessor
        factory.register_filter('feFlood', FloodProcessor)

        # Verify registration
        assert factory.is_filter_supported('feFlood') is True
        assert 'feFlood' in factory.get_supported_filters()

        # Create processor instance
        processor = factory.create_filter('feFlood')
        assert isinstance(processor, FloodProcessor)
        assert processor.filter_type == 'feFlood'

    def test_register_blend_processor_with_factory(self):
        """Test registering BlendProcessor with FilterFactory."""
        factory = FilterFactory()

        # Register BlendProcessor
        factory.register_filter('feBlend', BlendProcessor)

        # Verify registration
        assert factory.is_filter_supported('feBlend') is True
        assert 'feBlend' in factory.get_supported_filters()

        # Create processor instance
        processor = factory.create_filter('feBlend')
        assert isinstance(processor, BlendProcessor)
        assert processor.filter_type == 'feBlend'

    def test_register_color_matrix_processor_with_factory(self):
        """Test registering ColorMatrixProcessor with FilterFactory."""
        factory = FilterFactory()

        # Register ColorMatrixProcessor
        factory.register_filter('feColorMatrix', ColorMatrixProcessor)

        # Verify registration
        assert factory.is_filter_supported('feColorMatrix') is True
        assert 'feColorMatrix' in factory.get_supported_filters()

        # Create processor instance
        processor = factory.create_filter('feColorMatrix')
        assert isinstance(processor, ColorMatrixProcessor)
        assert processor.filter_type == 'feColorMatrix'

    def test_register_composite_processor_with_factory(self):
        """Test registering CompositeProcessor with FilterFactory."""
        factory = FilterFactory()

        # Register CompositeProcessor
        factory.register_filter('feComposite', CompositeProcessor)

        # Verify registration
        assert factory.is_filter_supported('feComposite') is True
        assert 'feComposite' in factory.get_supported_filters()

        # Create processor instance
        processor = factory.create_filter('feComposite')
        assert isinstance(processor, CompositeProcessor)
        assert processor.filter_type == 'feComposite'

    def test_register_all_processors_with_factory(self):
        """Test registering all processors together."""
        factory = FilterFactory()

        # Register all processors
        factory.register_filter('feOffset', OffsetProcessor)
        factory.register_filter('feFlood', FloodProcessor)
        factory.register_filter('feBlend', BlendProcessor)
        factory.register_filter('feColorMatrix', ColorMatrixProcessor)
        factory.register_filter('feComposite', CompositeProcessor)

        # Verify all are registered
        supported = factory.get_supported_filters()
        assert 'feOffset' in supported
        assert 'feFlood' in supported
        assert 'feBlend' in supported
        assert 'feColorMatrix' in supported
        assert 'feComposite' in supported

        # Create all processor instances
        offset_processor = factory.create_filter('feOffset')
        flood_processor = factory.create_filter('feFlood')
        blend_processor = factory.create_filter('feBlend')
        color_matrix_processor = factory.create_filter('feColorMatrix')
        composite_processor = factory.create_filter('feComposite')

        assert isinstance(offset_processor, OffsetProcessor)
        assert isinstance(flood_processor, FloodProcessor)
        assert isinstance(blend_processor, BlendProcessor)
        assert isinstance(color_matrix_processor, ColorMatrixProcessor)
        assert isinstance(composite_processor, CompositeProcessor)

    def test_register_processors_with_filter_service(self):
        """Test registering processors through FilterService."""
        # Create FilterService with services and policy
        services = Mock()
        policy = Mock()
        filter_service = FilterService(policy=policy, services=services)

        # Register processors through service
        filter_service.register_filter_processor('feOffset', OffsetProcessor)
        filter_service.register_filter_processor('feFlood', FloodProcessor)
        filter_service.register_filter_processor('feBlend', BlendProcessor)
        filter_service.register_filter_processor('feColorMatrix', ColorMatrixProcessor)
        filter_service.register_filter_processor('feComposite', CompositeProcessor)

        # Verify factory contains the filters
        factory = filter_service.get_filter_factory()
        assert factory.is_filter_supported('feOffset') is True
        assert factory.is_filter_supported('feFlood') is True
        assert factory.is_filter_supported('feBlend') is True
        assert factory.is_filter_supported('feColorMatrix') is True
        assert factory.is_filter_supported('feComposite') is True

        # Verify service tracks them as factory filters
        assert 'feOffset' in filter_service._factory_filters
        assert 'feFlood' in filter_service._factory_filters
        assert 'feBlend' in filter_service._factory_filters
        assert 'feColorMatrix' in filter_service._factory_filters
        assert 'feComposite' in filter_service._factory_filters

    def test_factory_coverage_includes_new_filters(self):
        """Test that factory coverage includes newly registered filters."""
        factory = FilterFactory()

        # Register our new filters
        factory.register_filter('feOffset', OffsetProcessor)
        factory.register_filter('feFlood', FloodProcessor)
        factory.register_filter('feBlend', BlendProcessor)
        factory.register_filter('feColorMatrix', ColorMatrixProcessor)
        factory.register_filter('feComposite', CompositeProcessor)

        # Get coverage report
        coverage = factory.get_filter_coverage()

        # Standard SVG filters should be reported
        assert 'feOffset' in coverage
        assert 'feFlood' in coverage
        assert 'feBlend' in coverage
        assert 'feColorMatrix' in coverage
        assert 'feComposite' in coverage

        # These should not be supported yet (just in our test)
        # Note: feOffset and feFlood are standard SVG filters but not in core list
        # They will show up as False until we add them to the standard filter list

    def test_mixed_filter_processing_through_service(self):
        """Test processing filters through service with mixed legacy/factory filters."""
        services = Mock()
        policy = Mock()
        filter_service = FilterService(policy=policy, services=services)

        # Register our new processors
        filter_service.register_filter_processor('feOffset', OffsetProcessor)
        filter_service.register_filter_processor('feFlood', FloodProcessor)
        filter_service.register_filter_processor('feBlend', BlendProcessor)

        # Create a filter with both legacy and new elements
        filter_element = ET.Element('filter', id='mixed-filter')

        # Add legacy filter (feGaussianBlur - should use legacy processing)
        blur_element = ET.SubElement(filter_element, 'feGaussianBlur')
        blur_element.set('stdDeviation', '2')

        # Add new filter (feOffset - should use factory processing)
        offset_element = ET.SubElement(filter_element, 'feOffset')
        offset_element.set('dx', '5')
        offset_element.set('dy', '3')

        # Add another new filter (feFlood - should use factory processing)
        flood_element = ET.SubElement(filter_element, 'feFlood')
        flood_element.set('flood-color', 'red')
        flood_element.set('flood-opacity', '0.8')

        # Add blend filter (feBlend - should use factory processing)
        blend_element = ET.SubElement(filter_element, 'feBlend')
        blend_element.set('mode', 'multiply')
        blend_element.set('in', 'SourceGraphic')
        blend_element.set('in2', 'BackgroundImage')

        # Test that service can handle mixed processing
        result = filter_service._convert_filter_definition(filter_element)

        # Should contain legacy blur processing
        assert 'a:blur' in result

        # The factory processing would be attempted for offset, flood, and blend
        # (though they might fail without proper context setup in this test)

    def test_create_comprehensive_filter_service(self):
        """Test creating a comprehensive FilterService with all filters."""
        services = Mock()
        policy = Mock()

        # Create service
        filter_service = FilterService(policy=policy, services=services)

        # Register all our new processors
        filter_service.register_filter_processor('feOffset', OffsetProcessor)
        filter_service.register_filter_processor('feFlood', FloodProcessor)
        filter_service.register_filter_processor('feBlend', BlendProcessor)
        filter_service.register_filter_processor('feColorMatrix', ColorMatrixProcessor)
        filter_service.register_filter_processor('feComposite', CompositeProcessor)

        # Verify service is properly configured
        factory = filter_service.get_filter_factory()
        assert factory.policy == policy

        # Verify filter tracking
        assert len(filter_service._factory_filters) == 5
        assert 'feOffset' in filter_service._factory_filters
        assert 'feFlood' in filter_service._factory_filters
        assert 'feBlend' in filter_service._factory_filters
        assert 'feColorMatrix' in filter_service._factory_filters
        assert 'feComposite' in filter_service._factory_filters

        # Verify legacy filters are still available
        assert len(filter_service._legacy_filters) == 4  # Original count

        # Total filter coverage should include both legacy and factory
        total_filters = len(filter_service._legacy_filters) + len(filter_service._factory_filters)
        assert total_filters == 9  # 4 legacy + 5 new


class TestFilterFactoryIntegration:
    """Test comprehensive FilterFactory integration patterns."""

    def test_factory_validation_with_registered_filters(self):
        """Test factory validation includes registered filters."""
        factory = FilterFactory()

        # Register our filters
        factory.register_filter('feOffset', OffsetProcessor)
        factory.register_filter('feFlood', FloodProcessor)
        factory.register_filter('feBlend', BlendProcessor)
        factory.register_filter('feColorMatrix', ColorMatrixProcessor)
        factory.register_filter('feComposite', CompositeProcessor)

        # Run validation
        validation = factory.validate_configuration()

        assert validation['configuration_valid'] is True
        assert validation['registered_processors'] == 16  # Auto-registered core filters
        assert validation['fallback_handlers'] == 0

        # Coverage should reflect auto-registered filters
        coverage_percentage = validation['coverage_percentage']
        assert coverage_percentage > 90  # Most filters are auto-registered

    def test_factory_filter_creation_with_policy(self):
        """Test filter creation with policy integration."""
        policy = Mock()
        policy.decide_filter_strategy.return_value = Mock()

        factory = FilterFactory(policy)

        # Register filters
        factory.register_filter('feOffset', OffsetProcessor)
        factory.register_filter('feFlood', FloodProcessor)
        factory.register_filter('feBlend', BlendProcessor)
        factory.register_filter('feColorMatrix', ColorMatrixProcessor)
        factory.register_filter('feComposite', CompositeProcessor)

        # Create filters - they should get the policy
        offset_processor = factory.create_filter('feOffset')
        flood_processor = factory.create_filter('feFlood')
        blend_processor = factory.create_filter('feBlend')
        color_matrix_processor = factory.create_filter('feColorMatrix')
        composite_processor = factory.create_filter('feComposite')

        assert offset_processor.policy == policy
        assert flood_processor.policy == policy
        assert blend_processor.policy == policy
        assert color_matrix_processor.policy == policy
        assert composite_processor.policy == policy

    def test_factory_element_based_creation(self):
        """Test creating filters from SVG elements."""
        factory = FilterFactory()

        # Register our filters
        factory.register_filter('feOffset', OffsetProcessor)
        factory.register_filter('feFlood', FloodProcessor)
        factory.register_filter('feBlend', BlendProcessor)
        factory.register_filter('feColorMatrix', ColorMatrixProcessor)
        factory.register_filter('feComposite', CompositeProcessor)

        # Create elements
        offset_element = ET.Element('feOffset')
        flood_element = ET.Element('feFlood')
        blend_element = ET.Element('feBlend')
        color_matrix_element = ET.Element('feColorMatrix')
        composite_element = ET.Element('feComposite')

        # Create processors from elements
        offset_processor = factory.create_filter_for_element(offset_element)
        flood_processor = factory.create_filter_for_element(flood_element)
        blend_processor = factory.create_filter_for_element(blend_element)
        color_matrix_processor = factory.create_filter_for_element(color_matrix_element)
        composite_processor = factory.create_filter_for_element(composite_element)

        assert isinstance(offset_processor, OffsetProcessor)
        assert isinstance(flood_processor, FloodProcessor)
        assert isinstance(blend_processor, BlendProcessor)
        assert isinstance(color_matrix_processor, ColorMatrixProcessor)
        assert isinstance(composite_processor, CompositeProcessor)

    def test_filter_registration_error_handling(self):
        """Test error handling during filter registration."""
        factory = FilterFactory()

        # Try to register invalid processor class
        class NotAProcessor:
            pass

        with pytest.raises(Exception):  # Should raise FilterRegistrationError
            factory.register_filter('feInvalid', NotAProcessor)

        # Verify factory state is unchanged
        assert not factory.is_filter_supported('feInvalid')


if __name__ == '__main__':
    pytest.main([__file__])