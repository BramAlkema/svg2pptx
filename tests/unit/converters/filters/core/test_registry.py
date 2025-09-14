"""
Tests for SVG filter registry functionality.

This module contains unit tests for the FilterRegistry class that manages
dynamic filter discovery, registration, and instantiation with thread-safe
operations and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional, List, Type
import threading
import time
from lxml import etree

from src.converters.filters.core.base import (
    Filter,
    FilterContext,
    FilterResult,
    FilterException,
    FilterValidationError
)
from src.converters.filters.core.registry import (
    FilterRegistry,
    FilterRegistrationError,
    FilterNotFoundError
)


# Mock filter implementations for testing
class MockBlurFilter(Filter):
    """Mock blur filter for testing."""

    def __init__(self):
        super().__init__("blur")
        self.applied_count = 0

    def can_apply(self, element: etree.Element, context: FilterContext) -> bool:
        return ('blur' in element.tag.lower() or
                'blur' in element.get('type', '') or
                element.tag.endswith('feGaussianBlur'))

    def apply(self, element: etree.Element, context: FilterContext) -> FilterResult:
        self.applied_count += 1
        return FilterResult(
            success=True,
            drawingml='<a:blur r="50000"/>',
            metadata={'filter_type': 'blur', 'applied_count': self.applied_count}
        )

    def validate_parameters(self, element: etree.Element, context: FilterContext) -> bool:
        return element.get('stdDeviation') is not None


class MockShadowFilter(Filter):
    """Mock shadow filter for testing."""

    def __init__(self):
        super().__init__("shadow")

    def can_apply(self, element: etree.Element, context: FilterContext) -> bool:
        return ('shadow' in element.tag.lower() or
                'shadow' in element.get('type', '') or
                element.tag.endswith('feDropShadow'))

    def apply(self, element: etree.Element, context: FilterContext) -> FilterResult:
        return FilterResult(
            success=True,
            drawingml='<a:outerShdw/>',
            metadata={'filter_type': 'shadow'}
        )

    def validate_parameters(self, element: etree.Element, context: FilterContext) -> bool:
        return True


class MockColorFilter(Filter):
    """Mock color filter for testing."""

    def __init__(self):
        super().__init__("color")

    def can_apply(self, element: etree.Element, context: FilterContext) -> bool:
        return ('color' in element.tag.lower() or
                'color' in element.get('type', '') or
                element.tag.endswith('feColorMatrix'))

    def apply(self, element: etree.Element, context: FilterContext) -> FilterResult:
        return FilterResult(
            success=True,
            drawingml='<a:tint val="50000"/>',
            metadata={'filter_type': 'color'}
        )

    def validate_parameters(self, element: etree.Element, context: FilterContext) -> bool:
        return element.get('values') is not None


class MockFailingFilter(Filter):
    """Mock filter that always fails for testing error scenarios."""

    def __init__(self):
        super().__init__("failing")

    def can_apply(self, element: etree.Element, context: FilterContext) -> bool:
        return True

    def apply(self, element: etree.Element, context: FilterContext) -> FilterResult:
        return FilterResult(
            success=False,
            error_message="Mock filter intentionally failed",
            metadata={'filter_type': 'failing'}
        )

    def validate_parameters(self, element: etree.Element, context: FilterContext) -> bool:
        return False


class TestFilterRegistry:
    """Tests for FilterRegistry class."""

    @pytest.fixture
    def setup_test_data(self):
        """Setup common test data and mock objects."""
        mock_svg_blur = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
        mock_svg_blur.set("stdDeviation", "2")

        mock_svg_shadow = etree.Element("{http://www.w3.org/2000/svg}feDropShadow")
        mock_svg_shadow.set("dx", "2")
        mock_svg_shadow.set("dy", "2")

        mock_svg_color = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        mock_svg_color.set("values", "1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 1 0")

        return {
            'mock_blur_element': mock_svg_blur,
            'mock_shadow_element': mock_svg_shadow,
            'mock_color_element': mock_svg_color,
            'mock_context': Mock(spec=FilterContext),
            'blur_filter': MockBlurFilter(),
            'shadow_filter': MockShadowFilter(),
            'color_filter': MockColorFilter(),
            'failing_filter': MockFailingFilter(),
            'filter_classes': [MockBlurFilter, MockShadowFilter, MockColorFilter],
            'expected_registry_methods': ['register', 'get_filter', 'list_filters', 'clear']
        }

    @pytest.fixture
    def registry_instance(self, setup_test_data):
        """Create FilterRegistry instance for testing."""
        registry = FilterRegistry()
        # Pre-register some filters
        registry.register(setup_test_data['blur_filter'])
        registry.register(setup_test_data['shadow_filter'])
        return registry

    def test_initialization(self, setup_test_data):
        """Test FilterRegistry initializes correctly with required attributes."""
        registry = FilterRegistry()

        assert hasattr(registry, 'filters')
        assert hasattr(registry, 'filter_map')
        assert hasattr(registry, 'lock')
        assert isinstance(registry.filters, dict)
        assert isinstance(registry.filter_map, dict)
        assert len(registry.filters) == 0
        assert len(registry.filter_map) == 0

    def test_basic_functionality(self, registry_instance, setup_test_data):
        """Test core methods and expected input/output behavior."""
        registry = registry_instance

        # Test registration worked
        assert len(registry.filters) == 2
        assert 'blur' in registry.filters
        assert 'shadow' in registry.filters

        # Test get_filter method
        blur_filter = registry.get_filter('blur')
        assert blur_filter is not None
        assert isinstance(blur_filter, MockBlurFilter)
        assert blur_filter.filter_type == 'blur'

        shadow_filter = registry.get_filter('shadow')
        assert shadow_filter is not None
        assert isinstance(shadow_filter, MockShadowFilter)

        # Test list_filters method
        filter_types = registry.list_filters()
        assert 'blur' in filter_types
        assert 'shadow' in filter_types
        assert len(filter_types) == 2

    def test_error_handling(self, setup_test_data):
        """Test invalid input handling, missing filters, and error scenarios."""
        registry = FilterRegistry()

        # Test getting non-existent filter
        with pytest.raises(FilterNotFoundError):
            registry.get_filter('nonexistent')

        # Test registering invalid filter (None)
        with pytest.raises(FilterRegistrationError):
            registry.register(None)

        # Test registering non-Filter object
        with pytest.raises(FilterRegistrationError):
            registry.register("not a filter")

        # Test registering filter with duplicate type
        registry.register(setup_test_data['blur_filter'])
        with pytest.raises(FilterRegistrationError):
            # Attempt to register another blur filter
            duplicate_blur = MockBlurFilter()
            registry.register(duplicate_blur)

    def test_edge_cases(self, setup_test_data):
        """Test edge cases and boundary conditions."""
        registry = FilterRegistry()

        # Test empty registry operations
        assert len(registry.list_filters()) == 0

        with pytest.raises(FilterNotFoundError):
            registry.get_filter('any_filter')

        # Test clear functionality
        registry.register(setup_test_data['blur_filter'])
        registry.register(setup_test_data['shadow_filter'])
        assert len(registry.filters) == 2

        registry.clear()
        assert len(registry.filters) == 0
        assert len(registry.filter_map) == 0
        assert len(registry.list_filters()) == 0

    def test_configuration_options(self, setup_test_data):
        """Test registry configuration and customization options."""
        # Test custom registry configuration
        registry = FilterRegistry(allow_duplicates=False)

        # Test default behavior
        registry.register(setup_test_data['blur_filter'])
        filter_count_before = len(registry.filters)

        # Attempt duplicate registration should fail
        with pytest.raises(FilterRegistrationError):
            duplicate_blur = MockBlurFilter()
            registry.register(duplicate_blur)

        assert len(registry.filters) == filter_count_before

    def test_integration_with_dependencies(self, setup_test_data):
        """Test FilterRegistry integration with Filter objects and dependencies."""
        registry = FilterRegistry()

        # Test registry with various filter types
        for filter_obj in [setup_test_data['blur_filter'],
                          setup_test_data['shadow_filter'],
                          setup_test_data['color_filter']]:
            registry.register(filter_obj)

        # Test that all filters are accessible
        assert len(registry.list_filters()) == 3

        # Test that filters maintain their functionality after registration
        blur_filter = registry.get_filter('blur')
        assert blur_filter.can_apply(setup_test_data['mock_blur_element'], setup_test_data['mock_context'])

        shadow_filter = registry.get_filter('shadow')
        assert shadow_filter.can_apply(setup_test_data['mock_shadow_element'], setup_test_data['mock_context'])

    @pytest.mark.parametrize("filter_type,filter_class,expected_registered", [
        ('blur', MockBlurFilter, True),
        ('shadow', MockShadowFilter, True),
        ('color', MockColorFilter, True),
        ('failing', MockFailingFilter, True),
    ])
    def test_parametrized_registration_scenarios(self, filter_type, filter_class, expected_registered, setup_test_data):
        """Test filter registration with various filter types and classes."""
        registry = FilterRegistry()
        filter_instance = filter_class()

        registry.register(filter_instance)

        if expected_registered:
            assert filter_type in registry.list_filters()
            retrieved_filter = registry.get_filter(filter_type)
            assert isinstance(retrieved_filter, filter_class)
        else:
            assert filter_type not in registry.list_filters()

    def test_performance_characteristics(self, setup_test_data):
        """Test registry performance and resource usage characteristics."""
        registry = FilterRegistry()

        # Test registration performance with many filters
        import time
        start_time = time.time()

        for i in range(100):
            # Create unique filter types for performance testing
            class DynamicFilter(Filter):
                def __init__(self, filter_id):
                    super().__init__(f"dynamic_{filter_id}")

                def can_apply(self, element, context):
                    return True

                def apply(self, element, context):
                    return FilterResult(success=True, drawingml=f"<dynamic_{filter_id}/>")

                def validate_parameters(self, element, context):
                    return True

            filter_instance = DynamicFilter(i)
            registry.register(filter_instance)

        registration_time = time.time() - start_time

        # Registration should be reasonably fast
        assert registration_time < 1.0, f"Registration took too long: {registration_time}s"
        assert len(registry.list_filters()) == 100

        # Test retrieval performance
        start_time = time.time()
        for i in range(100):
            filter_obj = registry.get_filter(f"dynamic_{i}")
            assert filter_obj is not None
        retrieval_time = time.time() - start_time

        # Retrieval should be very fast
        assert retrieval_time < 0.5, f"Retrieval took too long: {retrieval_time}s"

    def test_thread_safety(self, setup_test_data):
        """Test thread safety of registry operations."""
        registry = FilterRegistry()
        results = []
        errors = []
        lock = threading.Lock()

        def register_filter(filter_id):
            try:
                class ThreadTestFilter(Filter):
                    def __init__(self, fid):
                        super().__init__(f"thread_{fid}")

                    def can_apply(self, element, context):
                        return True

                    def apply(self, element, context):
                        return FilterResult(success=True, drawingml=f"<thread_{fid}/>")

                    def validate_parameters(self, element, context):
                        return True

                filter_instance = ThreadTestFilter(filter_id)
                registry.register(filter_instance)

                with lock:
                    results.append(filter_id)

            except Exception as e:
                with lock:
                    errors.append((filter_id, str(e)))

        def retrieve_filter(filter_id):
            try:
                time.sleep(0.01)  # Small delay to increase chance of race conditions
                filter_obj = registry.get_filter(f"thread_{filter_id}")
                with lock:
                    results.append(f"retrieved_{filter_id}")
            except Exception as e:
                with lock:
                    errors.append((f"retrieve_{filter_id}", str(e)))

        # Create threads for registration
        registration_threads = []
        for i in range(10):
            thread = threading.Thread(target=register_filter, args=(i,))
            registration_threads.append(thread)

        # Start all registration threads
        for thread in registration_threads:
            thread.start()

        # Wait for registration to complete
        for thread in registration_threads:
            thread.join()

        # Create threads for retrieval
        retrieval_threads = []
        for i in range(10):
            thread = threading.Thread(target=retrieve_filter, args=(i,))
            retrieval_threads.append(thread)

        # Start all retrieval threads
        for thread in retrieval_threads:
            thread.start()

        # Wait for retrieval to complete
        for thread in retrieval_threads:
            thread.join()

        # Verify results
        assert len(errors) == 0, f"Thread errors occurred: {errors}"
        assert len([r for r in results if isinstance(r, int)]) == 10  # 10 registrations
        assert len([r for r in results if isinstance(r, str) and r.startswith('retrieved_')]) == 10  # 10 retrievals

    def test_find_filter_for_element(self, registry_instance, setup_test_data):
        """Test finding appropriate filter for SVG elements."""
        registry = registry_instance

        # Test finding filter for blur element
        blur_filter = registry.find_filter_for_element(
            setup_test_data['mock_blur_element'],
            setup_test_data['mock_context']
        )
        assert blur_filter is not None
        assert isinstance(blur_filter, MockBlurFilter)

        # Test finding filter for shadow element
        shadow_filter = registry.find_filter_for_element(
            setup_test_data['mock_shadow_element'],
            setup_test_data['mock_context']
        )
        assert shadow_filter is not None
        assert isinstance(shadow_filter, MockShadowFilter)

        # Test element with no applicable filter
        unknown_element = etree.Element("{http://www.w3.org/2000/svg}unknown")
        no_filter = registry.find_filter_for_element(unknown_element, setup_test_data['mock_context'])
        assert no_filter is None

    def test_register_class_method(self, setup_test_data):
        """Test registering filter classes vs instances."""
        registry = FilterRegistry()

        # Test registering filter class
        registry.register_class(MockBlurFilter)
        assert 'blur' in registry.list_filters()

        blur_filter = registry.get_filter('blur')
        assert isinstance(blur_filter, MockBlurFilter)

        # Test registering multiple classes
        registry.register_class(MockShadowFilter)
        registry.register_class(MockColorFilter)

        assert len(registry.list_filters()) == 3
        assert 'blur' in registry.list_filters()
        assert 'shadow' in registry.list_filters()
        assert 'color' in registry.list_filters()

    def test_registry_default_filters(self):
        """Test default filter registration functionality."""
        registry = FilterRegistry()

        # Test that registry can be initialized with default filters
        # This method will be called when default filters are implemented
        with patch.object(registry, '_load_default_filters') as mock_load:
            registry.register_default_filters()
            mock_load.assert_called_once()


class TestFilterRegistrationError:
    """Tests for FilterRegistrationError exception."""

    def test_filter_registration_error_initialization(self):
        """Test FilterRegistrationError creates correctly."""
        message = "Filter registration failed"
        exception = FilterRegistrationError(message)
        assert str(exception) == message
        assert isinstance(exception, FilterException)


class TestFilterNotFoundError:
    """Tests for FilterNotFoundError exception."""

    def test_filter_not_found_error_initialization(self):
        """Test FilterNotFoundError creates correctly."""
        filter_type = "nonexistent_filter"
        exception = FilterNotFoundError(filter_type)
        expected_message = f"Filter not found: {filter_type}"
        assert str(exception) == expected_message
        assert isinstance(exception, FilterException)


class TestFilterRegistryHelperFunctions:
    """Tests for helper functions in the registry module."""

    def test_filter_type_validation(self):
        """Test filter type validation helper function."""
        # This will be implemented when helper functions are added
        pass

    def test_filter_compatibility_check(self):
        """Test filter compatibility checking helper function."""
        # This will be implemented when helper functions are added
        pass


class TestFilterRegistryIntegration:
    """Integration tests for FilterRegistry with other components."""

    @pytest.fixture
    def integration_setup(self):
        """Setup for integration testing."""
        return {
            'svg_content': '''<svg xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <filter id="blur-filter">
                        <feGaussianBlur stdDeviation="2"/>
                    </filter>
                    <filter id="shadow-filter">
                        <feDropShadow dx="2" dy="2"/>
                    </filter>
                </defs>
                <rect width="100" height="50" filter="url(#blur-filter)"/>
                <circle cx="50" cy="25" r="20" filter="url(#shadow-filter)"/>
            </svg>''',
            'mock_context': Mock(spec=FilterContext)
        }

    def test_integration_with_svg_parsing(self, integration_setup):
        """Test FilterRegistry integration with SVG parsing."""
        registry = FilterRegistry()
        registry.register(MockBlurFilter())
        registry.register(MockShadowFilter())

        # Parse SVG content
        root = etree.fromstring(integration_setup['svg_content'])

        # Find filter elements
        blur_filter_elem = root.find('.//{http://www.w3.org/2000/svg}feGaussianBlur')
        shadow_filter_elem = root.find('.//{http://www.w3.org/2000/svg}feDropShadow')

        assert blur_filter_elem is not None
        assert shadow_filter_elem is not None

        # Test that registry can find appropriate filters
        blur_filter = registry.find_filter_for_element(
            blur_filter_elem,
            integration_setup['mock_context']
        )
        assert isinstance(blur_filter, MockBlurFilter)

        shadow_filter = registry.find_filter_for_element(
            shadow_filter_elem,
            integration_setup['mock_context']
        )
        assert isinstance(shadow_filter, MockShadowFilter)

    def test_integration_with_filter_pipeline(self, integration_setup):
        """Test FilterRegistry integration with broader filter processing pipeline."""
        registry = FilterRegistry()
        registry.register(MockBlurFilter())
        registry.register(MockShadowFilter())
        registry.register(MockColorFilter())

        # Test that registry provides consistent interfaces for pipeline integration
        all_filters = [registry.get_filter(ft) for ft in registry.list_filters()]

        assert len(all_filters) == 3

        # Test that all filters follow the same interface
        for filter_obj in all_filters:
            assert hasattr(filter_obj, 'can_apply')
            assert hasattr(filter_obj, 'apply')
            assert hasattr(filter_obj, 'validate_parameters')
            assert hasattr(filter_obj, 'filter_type')

        # Test that filters can be used interchangeably in processing
        test_element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
        test_element.set("stdDeviation", "2")

        applicable_filters = [
            f for f in all_filters
            if f.can_apply(test_element, integration_setup['mock_context'])
        ]

        assert len(applicable_filters) >= 1  # At least blur filter should apply