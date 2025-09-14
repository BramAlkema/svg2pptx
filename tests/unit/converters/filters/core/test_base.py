"""
Tests for SVG filter base classes and core functionality.

This module contains unit tests for the abstract Filter base class,
FilterContext, and FilterResult classes that form the foundation
of the modular filter system.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional, List
import xml.etree.ElementTree as ET
from lxml import etree

from src.converters.filters.core.base import (
    Filter,
    FilterContext,
    FilterResult,
    FilterException,
    FilterValidationError
)


class TestFilterContext:
    """Tests for FilterContext class."""

    @pytest.fixture
    def setup_test_data(self):
        """Setup common test data and mock objects."""
        mock_svg_element = etree.Element("{http://www.w3.org/2000/svg}filter")
        mock_svg_element.set("id", "test-filter")

        return {
            'mock_svg_element': mock_svg_element,
            'viewport_info': {'width': 100, 'height': 200},
            'unit_converter': Mock(),
            'transform_parser': Mock(),
            'color_parser': Mock(),
            'test_properties': {'opacity': '0.5', 'fill': '#FF0000'},
            'expected_context_keys': ['viewport', 'unit_converter', 'properties']
        }

    @pytest.fixture
    def filter_context_instance(self, setup_test_data):
        """Create FilterContext instance for testing."""
        return FilterContext(
            element=setup_test_data['mock_svg_element'],
            viewport=setup_test_data['viewport_info'],
            unit_converter=setup_test_data['unit_converter'],
            transform_parser=setup_test_data['transform_parser'],
            color_parser=setup_test_data['color_parser'],
            properties=setup_test_data['test_properties']
        )

    def test_initialization(self, filter_context_instance, setup_test_data):
        """Test FilterContext initializes correctly with required attributes."""
        context = filter_context_instance

        assert context.element is not None
        assert context.viewport == setup_test_data['viewport_info']
        assert context.unit_converter == setup_test_data['unit_converter']
        assert context.transform_parser == setup_test_data['transform_parser']
        assert context.color_parser == setup_test_data['color_parser']
        assert context.properties == setup_test_data['test_properties']
        assert hasattr(context, 'cache')
        assert isinstance(context.cache, dict)

    def test_basic_functionality(self, filter_context_instance):
        """Test core methods and expected input/output behavior."""
        context = filter_context_instance

        # Test cache functionality
        context.cache['test_key'] = 'test_value'
        assert context.cache['test_key'] == 'test_value'

        # Test property access
        assert context.get_property('opacity') == '0.5'
        assert context.get_property('fill') == '#FF0000'
        assert context.get_property('nonexistent') is None
        assert context.get_property('nonexistent', 'default') == 'default'

    def test_error_handling(self, setup_test_data):
        """Test invalid input handling and missing dependencies."""
        # Test missing element
        with pytest.raises(FilterValidationError):
            FilterContext(
                element=None,
                viewport=setup_test_data['viewport_info'],
                unit_converter=setup_test_data['unit_converter'],
                transform_parser=setup_test_data['transform_parser'],
                color_parser=setup_test_data['color_parser']
            )

        # Test missing required dependencies
        with pytest.raises(FilterValidationError):
            FilterContext(
                element=setup_test_data['mock_svg_element'],
                viewport=setup_test_data['viewport_info'],
                unit_converter=None,  # Missing required dependency
                transform_parser=setup_test_data['transform_parser'],
                color_parser=setup_test_data['color_parser']
            )

    def test_edge_cases(self, setup_test_data):
        """Test edge cases and boundary conditions."""
        # Test empty properties
        context = FilterContext(
            element=setup_test_data['mock_svg_element'],
            viewport=setup_test_data['viewport_info'],
            unit_converter=setup_test_data['unit_converter'],
            transform_parser=setup_test_data['transform_parser'],
            color_parser=setup_test_data['color_parser'],
            properties={}
        )
        assert context.get_property('any_key') is None

        # Test None properties
        context_no_props = FilterContext(
            element=setup_test_data['mock_svg_element'],
            viewport=setup_test_data['viewport_info'],
            unit_converter=setup_test_data['unit_converter'],
            transform_parser=setup_test_data['transform_parser'],
            color_parser=setup_test_data['color_parser'],
            properties=None
        )
        assert context_no_props.get_property('any_key') is None


class TestFilterResult:
    """Tests for FilterResult class."""

    @pytest.fixture
    def setup_test_data(self):
        """Setup common test data for FilterResult testing."""
        return {
            'success_drawingml': '<a:blur r="50000"/>',
            'error_message': 'Filter processing failed',
            'metadata': {'filter_type': 'blur', 'processing_time': 0.123},
            'performance_stats': {'memory_used': 1024, 'cpu_time': 0.05}
        }

    @pytest.fixture
    def filter_result_instance(self, setup_test_data):
        """Create FilterResult instance for testing."""
        return FilterResult(
            success=True,
            drawingml=setup_test_data['success_drawingml'],
            metadata=setup_test_data['metadata']
        )

    def test_initialization(self, filter_result_instance, setup_test_data):
        """Test FilterResult initializes correctly with required attributes."""
        result = filter_result_instance

        assert result.success is True
        assert result.drawingml == setup_test_data['success_drawingml']
        assert result.metadata == setup_test_data['metadata']
        assert result.error_message is None

    def test_basic_functionality(self, setup_test_data):
        """Test core methods and expected behavior for success and error cases."""
        # Test successful result
        success_result = FilterResult(
            success=True,
            drawingml=setup_test_data['success_drawingml'],
            metadata=setup_test_data['metadata']
        )
        assert success_result.is_success() is True
        assert success_result.get_drawingml() == setup_test_data['success_drawingml']
        assert success_result.get_metadata() == setup_test_data['metadata']

        # Test error result
        error_result = FilterResult(
            success=False,
            error_message=setup_test_data['error_message'],
            metadata=setup_test_data['metadata']
        )
        assert error_result.is_success() is False
        assert error_result.get_error_message() == setup_test_data['error_message']
        assert error_result.get_drawingml() is None

    def test_error_handling(self, setup_test_data):
        """Test validation and error conditions."""
        # Test invalid error result (missing error message)
        with pytest.raises(FilterValidationError):
            FilterResult(success=False, error_message=None)

        # Test invalid error result (empty error message)
        with pytest.raises(FilterValidationError):
            FilterResult(success=False, error_message="")

    @pytest.mark.parametrize("success,drawingml,error_msg,should_raise", [
        (True, '<a:blur r="50000"/>', None, False),
        (False, None, 'Error occurred', False),
        (True, None, None, False),  # Success without drawingml - now allowed
        (False, None, None, True),  # Error without message
        (True, '', None, False),    # Empty drawingml - now allowed
        (False, None, '', True),   # Empty error message
    ])
    def test_parametrized_validation_scenarios(self, success, drawingml, error_msg, should_raise):
        """Test FilterResult validation with various input combinations."""
        if should_raise:
            with pytest.raises(FilterValidationError):
                FilterResult(success=success, drawingml=drawingml, error_message=error_msg)
        else:
            result = FilterResult(success=success, drawingml=drawingml, error_message=error_msg)
            assert result.success == success


class MockTestFilter(Filter):
    """Mock Filter implementation for testing abstract base class."""

    def __init__(self, filter_type: str = "test_filter"):
        super().__init__(filter_type)
        self.apply_called = False
        self.validate_called = False

    def can_apply(self, element: etree.Element, context: FilterContext) -> bool:
        """Test implementation of can_apply method."""
        return element.tag.endswith('filter') or element.tag.endswith('rect')

    def apply(self, element: etree.Element, context: FilterContext) -> FilterResult:
        """Test implementation of apply method."""
        self.apply_called = True
        return FilterResult(
            success=True,
            drawingml='<test>Applied test filter</test>',
            metadata={'filter_type': self.filter_type}
        )

    def validate_parameters(self, element: etree.Element, context: FilterContext) -> bool:
        """Test implementation of validate_parameters method."""
        self.validate_called = True
        return True


class TestFilter:
    """Tests for abstract Filter base class."""

    @pytest.fixture
    def setup_test_data(self):
        """Setup common test data and mock objects."""
        mock_svg_element = etree.Element("{http://www.w3.org/2000/svg}filter")
        mock_svg_element.set("id", "test-filter")
        mock_svg_element.set("x", "10")
        mock_svg_element.set("y", "20")

        mock_rect_element = etree.Element("{http://www.w3.org/2000/svg}rect")
        mock_rect_element.set("width", "100")
        mock_rect_element.set("height", "50")

        return {
            'mock_svg_element': mock_svg_element,
            'mock_rect_element': mock_rect_element,
            'filter_context': Mock(spec=FilterContext),
            'expected_result_type': FilterResult,
            'test_filter_type': 'gaussian_blur'
        }

    @pytest.fixture
    def filter_instance(self, setup_test_data):
        """Create concrete Filter instance for testing."""
        return MockTestFilter(setup_test_data['test_filter_type'])

    def test_initialization(self, filter_instance, setup_test_data):
        """Test Filter initializes correctly with required attributes."""
        filter_obj = filter_instance

        assert filter_obj.filter_type == setup_test_data['test_filter_type']
        assert hasattr(filter_obj, 'filter_type')
        assert hasattr(filter_obj, 'can_apply')
        assert hasattr(filter_obj, 'apply')
        assert hasattr(filter_obj, 'validate_parameters')

    def test_basic_functionality(self, filter_instance, setup_test_data):
        """Test core methods and expected input/output behavior."""
        filter_obj = filter_instance

        # Test can_apply method
        can_apply_filter = filter_obj.can_apply(
            setup_test_data['mock_svg_element'],
            setup_test_data['filter_context']
        )
        assert can_apply_filter is True

        can_apply_rect = filter_obj.can_apply(
            setup_test_data['mock_rect_element'],
            setup_test_data['filter_context']
        )
        assert can_apply_rect is True

        # Test apply method
        result = filter_obj.apply(
            setup_test_data['mock_svg_element'],
            setup_test_data['filter_context']
        )
        assert isinstance(result, FilterResult)
        assert result.success is True
        assert filter_obj.apply_called is True

        # Test validate_parameters method
        is_valid = filter_obj.validate_parameters(
            setup_test_data['mock_svg_element'],
            setup_test_data['filter_context']
        )
        assert is_valid is True
        assert filter_obj.validate_called is True

    def test_error_handling(self, setup_test_data):
        """Test abstract class instantiation and method requirements."""
        # Test that abstract Filter cannot be instantiated directly
        with pytest.raises(TypeError):
            Filter("test_type")  # This should fail as Filter is abstract

    def test_configuration_options(self, filter_instance, setup_test_data):
        """Test filter configuration and customization options."""
        filter_obj = filter_instance

        # Test filter type property
        assert filter_obj.filter_type == setup_test_data['test_filter_type']

        # Test that filter can be configured with different types
        different_filter = MockTestFilter("custom_filter")
        assert different_filter.filter_type == "custom_filter"

    @pytest.mark.parametrize("element_tag,expected_can_apply", [
        ("{http://www.w3.org/2000/svg}filter", True),
        ("{http://www.w3.org/2000/svg}rect", True),
        ("{http://www.w3.org/2000/svg}circle", False),
        ("{http://www.w3.org/2000/svg}path", False),
        ("{http://www.w3.org/2000/svg}text", False),
    ])
    def test_parametrized_can_apply_scenarios(self, filter_instance, element_tag, expected_can_apply, setup_test_data):
        """Test can_apply method with various element types."""
        filter_obj = filter_instance

        test_element = etree.Element(element_tag)
        result = filter_obj.can_apply(test_element, setup_test_data['filter_context'])
        assert result == expected_can_apply

    def test_performance_characteristics(self, filter_instance, setup_test_data):
        """Test filter performance and resource usage characteristics."""
        filter_obj = filter_instance

        # Test that multiple applies work correctly
        for i in range(10):
            result = filter_obj.apply(
                setup_test_data['mock_svg_element'],
                setup_test_data['filter_context']
            )
            assert result.success is True
            assert isinstance(result.drawingml, str)

        # Test that filter maintains state correctly
        assert filter_obj.filter_type == setup_test_data['test_filter_type']

    def test_thread_safety(self, filter_instance, setup_test_data):
        """Test thread safety of filter operations."""
        import threading
        import time

        filter_obj = filter_instance
        results = []
        errors = []

        def apply_filter():
            try:
                result = filter_obj.apply(
                    setup_test_data['mock_svg_element'],
                    setup_test_data['filter_context']
                )
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=apply_filter)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify results
        assert len(errors) == 0, f"Thread errors occurred: {errors}"
        assert len(results) == 5
        for result in results:
            assert result.success is True


class TestFilterExceptions:
    """Tests for Filter exception classes."""

    def test_filter_exception_initialization(self):
        """Test FilterException creates correctly."""
        message = "Test filter exception"
        exception = FilterException(message)
        assert str(exception) == message
        assert isinstance(exception, Exception)

    def test_filter_validation_error_initialization(self):
        """Test FilterValidationError creates correctly."""
        message = "Invalid filter parameters"
        exception = FilterValidationError(message)
        assert str(exception) == message
        assert isinstance(exception, FilterException)
        assert isinstance(exception, ValueError)

    def test_exception_hierarchy(self):
        """Test exception inheritance hierarchy."""
        validation_error = FilterValidationError("test")

        assert isinstance(validation_error, FilterValidationError)
        assert isinstance(validation_error, FilterException)
        assert isinstance(validation_error, ValueError)
        assert isinstance(validation_error, Exception)


class TestFilterHelperFunctions:
    """Tests for helper functions in the base module."""

    def test_create_filter_context_helper(self, setup_test_data=None):
        """Test helper function for creating FilterContext instances."""
        # This will be implemented when helper functions are added
        pass

    def test_validate_svg_element_helper(self):
        """Test helper function for validating SVG elements."""
        # This will be implemented when helper functions are added
        pass


class TestFilterIntegration:
    """Integration tests for Filter base class with other components."""

    @pytest.fixture
    def integration_setup(self):
        """Setup for integration testing."""
        return {
            'mock_unit_converter': Mock(),
            'mock_transform_parser': Mock(),
            'mock_color_parser': Mock(),
            'svg_content': '''<svg xmlns="http://www.w3.org/2000/svg">
                <filter id="test-filter">
                    <feGaussianBlur stdDeviation="2"/>
                </filter>
                <rect width="100" height="50" filter="url(#test-filter)"/>
            </svg>'''
        }

    def test_integration_with_filter_context(self, integration_setup):
        """Test Filter integration with FilterContext."""
        # Parse SVG
        root = etree.fromstring(integration_setup['svg_content'])
        filter_element = root.find('.//{http://www.w3.org/2000/svg}filter')

        # Create context
        context = FilterContext(
            element=filter_element,
            viewport={'width': 200, 'height': 100},
            unit_converter=integration_setup['mock_unit_converter'],
            transform_parser=integration_setup['mock_transform_parser'],
            color_parser=integration_setup['mock_color_parser']
        )

        # Create and apply filter
        filter_obj = MockTestFilter("gaussian_blur")
        result = filter_obj.apply(filter_element, context)

        assert result.success is True
        assert isinstance(result.drawingml, str)
        assert result.metadata['filter_type'] == 'gaussian_blur'

    def test_integration_with_real_svg_parsing(self, integration_setup):
        """Test Filter integration with actual SVG parsing."""
        # This test demonstrates integration with the broader SVG processing pipeline
        root = etree.fromstring(integration_setup['svg_content'])

        # Find all filterable elements
        elements = root.xpath('.//*[@filter]')
        filters = root.xpath('.//svg:filter', namespaces={'svg': 'http://www.w3.org/2000/svg'})

        assert len(elements) >= 1  # Should find rect with filter
        assert len(filters) >= 1   # Should find filter definition

        # Test that our filter system can handle real SVG structure
        filter_obj = MockTestFilter("integration_test")
        context = FilterContext(
            element=filters[0],
            viewport={'width': 200, 'height': 100},
            unit_converter=integration_setup['mock_unit_converter'],
            transform_parser=integration_setup['mock_transform_parser'],
            color_parser=integration_setup['mock_color_parser']
        )

        can_process = filter_obj.can_apply(filters[0], context)
        assert can_process is True