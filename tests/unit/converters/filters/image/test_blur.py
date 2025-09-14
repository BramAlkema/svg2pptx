"""
Tests for SVG blur filter implementations.

This module contains unit tests for blur filter implementations including
Gaussian blur, motion blur, and various edge cases with different parameter
combinations following the comprehensive testing template.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional, List
from lxml import etree

from src.converters.filters.core.base import (
    Filter,
    FilterContext,
    FilterResult,
    FilterException,
    FilterValidationError
)
from src.converters.filters.image.blur import (
    GaussianBlurFilter,
    MotionBlurFilter,
    BlurFilterException
)


class TestGaussianBlurFilter:
    """Tests for GaussianBlurFilter implementation."""

    @pytest.fixture
    def setup_test_data(self):
        """Setup common test data and mock objects."""
        mock_blur_element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
        mock_blur_element.set("stdDeviation", "2.5")
        mock_blur_element.set("edgeMode", "duplicate")
        mock_blur_element.set("in", "SourceGraphic")
        mock_blur_element.set("result", "blur")

        mock_anisotropic_element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
        mock_anisotropic_element.set("stdDeviation", "3.0 1.5")  # Different X and Y
        mock_anisotropic_element.set("edgeMode", "wrap")

        mock_zero_blur_element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
        mock_zero_blur_element.set("stdDeviation", "0")

        # Use actual converter infrastructure like existing tests
        mock_unit_converter = Mock()
        mock_unit_converter.to_emu.return_value = 50000
        mock_unit_converter.to_px.return_value = 2.0

        mock_transform_parser = Mock()
        mock_color_parser = Mock()
        mock_viewport = {'width': 200, 'height': 100}

        mock_context = Mock(spec=FilterContext)
        mock_context.unit_converter = mock_unit_converter
        mock_context.transform_parser = mock_transform_parser
        mock_context.color_parser = mock_color_parser
        mock_context.viewport = mock_viewport
        mock_context.get_property.return_value = None

        return {
            'mock_blur_element': mock_blur_element,
            'mock_anisotropic_element': mock_anisotropic_element,
            'mock_zero_blur_element': mock_zero_blur_element,
            'mock_context': mock_context,
            'mock_unit_converter': mock_unit_converter,
            'expected_filter_type': 'gaussian_blur',
            'standard_deviation_values': [0, 1, 2.5, 5.0, 10.0, 25.0],
            'edge_mode_values': ['duplicate', 'wrap', 'none'],
            'expected_drawingml_pattern': '<a:blur'
        }

    @pytest.fixture
    def gaussian_blur_instance(self, setup_test_data):
        """Create GaussianBlurFilter instance for testing."""
        return GaussianBlurFilter()

    def test_initialization(self, gaussian_blur_instance):
        """Test GaussianBlurFilter initializes correctly with required attributes."""
        filter_obj = gaussian_blur_instance

        assert filter_obj.filter_type == 'gaussian_blur'
        assert hasattr(filter_obj, 'can_apply')
        assert hasattr(filter_obj, 'apply')
        assert hasattr(filter_obj, 'validate_parameters')
        assert hasattr(filter_obj, '_parse_std_deviation')
        assert hasattr(filter_obj, '_convert_to_ooxml_radius')

    def test_basic_functionality(self, gaussian_blur_instance, setup_test_data):
        """Test core methods and expected input/output behavior."""
        filter_obj = gaussian_blur_instance

        # Test can_apply method
        can_apply_result = filter_obj.can_apply(
            setup_test_data['mock_blur_element'],
            setup_test_data['mock_context']
        )
        assert can_apply_result is True

        # Test apply method with standard blur
        result = filter_obj.apply(
            setup_test_data['mock_blur_element'],
            setup_test_data['mock_context']
        )
        assert isinstance(result, FilterResult)
        assert result.success is True
        assert setup_test_data['expected_drawingml_pattern'] in result.drawingml
        assert 'gaussian_blur' in result.metadata['filter_type']

        # Test validate_parameters method
        is_valid = filter_obj.validate_parameters(
            setup_test_data['mock_blur_element'],
            setup_test_data['mock_context']
        )
        assert is_valid is True

    def test_error_handling(self, gaussian_blur_instance, setup_test_data):
        """Test invalid input handling, missing attributes, and malformed data."""
        filter_obj = gaussian_blur_instance

        # Test element without stdDeviation attribute
        malformed_element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
        # No stdDeviation attribute

        # Should handle gracefully with default value
        result = filter_obj.apply(malformed_element, setup_test_data['mock_context'])
        assert isinstance(result, FilterResult)
        # Should either succeed with default or provide meaningful error

        # Test invalid stdDeviation value
        invalid_element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
        invalid_element.set("stdDeviation", "invalid_number")

        result = filter_obj.apply(invalid_element, setup_test_data['mock_context'])
        assert isinstance(result, FilterResult)
        if not result.success:
            assert "invalid" in result.error_message.lower() or "stddeviation" in result.error_message.lower()

        # Test negative stdDeviation value
        negative_element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
        negative_element.set("stdDeviation", "-2.5")

        result = filter_obj.apply(negative_element, setup_test_data['mock_context'])
        assert isinstance(result, FilterResult)
        # Negative blur should be handled appropriately (either clamped to 0 or error)

    def test_edge_cases(self, gaussian_blur_instance, setup_test_data):
        """Test edge cases and boundary conditions."""
        filter_obj = gaussian_blur_instance

        # Test zero blur (no-op case)
        result = filter_obj.apply(
            setup_test_data['mock_zero_blur_element'],
            setup_test_data['mock_context']
        )
        assert isinstance(result, FilterResult)
        assert result.success is True

        # Test very large blur values
        large_blur_element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
        large_blur_element.set("stdDeviation", "100.0")

        result = filter_obj.apply(large_blur_element, setup_test_data['mock_context'])
        assert isinstance(result, FilterResult)
        assert result.success is True

        # Test anisotropic blur (different X and Y)
        result = filter_obj.apply(
            setup_test_data['mock_anisotropic_element'],
            setup_test_data['mock_context']
        )
        assert isinstance(result, FilterResult)
        assert result.success is True
        # Should handle different X and Y blur values

    def test_configuration_options(self, gaussian_blur_instance, setup_test_data):
        """Test filter configuration and customization options."""
        filter_obj = gaussian_blur_instance

        # Test different edge modes
        for edge_mode in setup_test_data['edge_mode_values']:
            element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
            element.set("stdDeviation", "2.0")
            element.set("edgeMode", edge_mode)

            result = filter_obj.apply(element, setup_test_data['mock_context'])
            assert isinstance(result, FilterResult)
            assert result.success is True
            # Edge mode should be processed correctly

        # Test input and result attributes
        element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
        element.set("stdDeviation", "2.0")
        element.set("in", "SourceAlpha")
        element.set("result", "customBlur")

        result = filter_obj.apply(element, setup_test_data['mock_context'])
        assert isinstance(result, FilterResult)
        assert result.success is True

    def test_integration_with_dependencies(self, gaussian_blur_instance, setup_test_data):
        """Test GaussianBlurFilter integration with unit converter and other dependencies."""
        filter_obj = gaussian_blur_instance

        # Test unit conversion integration
        setup_test_data['mock_unit_converter'].to_emu.return_value = 25400  # Different conversion value

        result = filter_obj.apply(
            setup_test_data['mock_blur_element'],
            setup_test_data['mock_context']
        )

        # Verify unit converter was called
        setup_test_data['mock_unit_converter'].to_emu.assert_called()
        assert result.success is True

        # Test context property integration
        setup_test_data['mock_context'].get_property.return_value = 'some_value'

        result = filter_obj.apply(
            setup_test_data['mock_blur_element'],
            setup_test_data['mock_context']
        )

        # Verify the filter successfully integrates with existing architecture
        assert result.success is True

    @pytest.mark.parametrize("std_deviation,expected_valid", [
        ("0", True),
        ("1.0", True),
        ("2.5", True),
        ("10.0", True),
        ("0.1", True),
        ("100.0", True),  # Large but valid
        ("invalid", False),
        ("-1.0", False),  # Negative
        ("", False),      # Empty
        ("1.0 2.0", True),  # Anisotropic
        ("1.0 invalid", False),  # Partially invalid
    ])
    def test_parametrized_std_deviation_scenarios(self, gaussian_blur_instance, std_deviation, expected_valid, setup_test_data):
        """Test GaussianBlurFilter with various stdDeviation input combinations."""
        filter_obj = gaussian_blur_instance

        element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
        if std_deviation:  # Only set if not empty
            element.set("stdDeviation", std_deviation)

        result = filter_obj.apply(element, setup_test_data['mock_context'])
        assert isinstance(result, FilterResult)

        if expected_valid:
            assert result.success is True
            assert setup_test_data['expected_drawingml_pattern'] in result.drawingml
        else:
            # Invalid inputs might either be handled gracefully or return error
            if not result.success:
                assert result.error_message is not None

    def test_performance_characteristics(self, gaussian_blur_instance, setup_test_data):
        """Test filter performance and resource usage characteristics."""
        filter_obj = gaussian_blur_instance

        import time

        # Test processing time for multiple applications
        start_time = time.time()
        for i in range(100):
            element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
            element.set("stdDeviation", f"{i / 10.0}")

            result = filter_obj.apply(element, setup_test_data['mock_context'])
            assert result.success is True

        processing_time = time.time() - start_time
        assert processing_time < 1.0, f"Processing took too long: {processing_time}s"

        # Test memory efficiency - should not accumulate state
        initial_vars = len(vars(filter_obj))
        for i in range(10):
            element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
            element.set("stdDeviation", "2.0")
            filter_obj.apply(element, setup_test_data['mock_context'])

        final_vars = len(vars(filter_obj))
        assert final_vars == initial_vars, "Filter should not accumulate state"

    def test_thread_safety(self, gaussian_blur_instance, setup_test_data):
        """Test thread safety of blur filter operations."""
        import threading
        import time

        filter_obj = gaussian_blur_instance
        results = []
        errors = []
        lock = threading.Lock()

        def apply_blur():
            try:
                element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
                element.set("stdDeviation", "2.0")

                result = filter_obj.apply(element, setup_test_data['mock_context'])
                with lock:
                    results.append(result)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=apply_blur)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify results
        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(results) == 5
        for result in results:
            assert result.success is True

    def test_std_deviation_parsing(self, gaussian_blur_instance):
        """Test _parse_std_deviation method for various input formats."""
        filter_obj = gaussian_blur_instance

        # Test isotropic blur
        std_x, std_y = filter_obj._parse_std_deviation("2.5")
        assert std_x == 2.5
        assert std_y == 2.5

        # Test anisotropic blur
        std_x, std_y = filter_obj._parse_std_deviation("3.0 1.5")
        assert std_x == 3.0
        assert std_y == 1.5

        # Test zero blur
        std_x, std_y = filter_obj._parse_std_deviation("0")
        assert std_x == 0.0
        assert std_y == 0.0

        # Test invalid input handling
        with pytest.raises(BlurFilterException):
            filter_obj._parse_std_deviation("invalid")

        with pytest.raises(BlurFilterException):
            filter_obj._parse_std_deviation("-1.0")

    def test_ooxml_radius_conversion(self, gaussian_blur_instance, setup_test_data):
        """Test _convert_to_ooxml_radius method for EMU conversion."""
        filter_obj = gaussian_blur_instance

        # Mock unit converter for testing
        setup_test_data['mock_unit_converter'].to_emu.return_value = 63500  # 2.5px in EMUs

        radius = filter_obj._convert_to_ooxml_radius(2.5, setup_test_data['mock_unit_converter'])
        assert radius == 63500

        # Verify unit converter was called with correct parameters
        setup_test_data['mock_unit_converter'].to_emu.assert_called_with("2.5px")


class TestMotionBlurFilter:
    """Tests for MotionBlurFilter implementation."""

    @pytest.fixture
    def setup_test_data(self):
        """Setup common test data for MotionBlurFilter testing."""
        # Motion blur is typically implemented as a custom effect or through transforms
        mock_motion_element = etree.Element("{http://www.w3.org/2000/svg}feConvolveMatrix")
        mock_motion_element.set("kernelMatrix", "1 0 0 0 1 0 0 0 1")  # Identity matrix
        mock_motion_element.set("order", "3")
        mock_motion_element.set("targetX", "1")
        mock_motion_element.set("targetY", "1")

        mock_unit_converter = Mock()
        mock_unit_converter.to_emu.return_value = 25400
        mock_transform_parser = Mock()
        mock_color_parser = Mock()

        mock_context = Mock(spec=FilterContext)
        mock_context.unit_converter = mock_unit_converter
        mock_context.transform_parser = mock_transform_parser
        mock_context.color_parser = mock_color_parser
        mock_context.viewport = {'width': 200, 'height': 100}

        return {
            'mock_motion_element': mock_motion_element,
            'mock_context': mock_context,
            'expected_filter_type': 'motion_blur',
            'motion_angles': [0, 45, 90, 135, 180, 270],
            'motion_distances': [0, 1, 5, 10, 20]
        }

    @pytest.fixture
    def motion_blur_instance(self):
        """Create MotionBlurFilter instance for testing."""
        return MotionBlurFilter()

    def test_initialization(self, motion_blur_instance):
        """Test MotionBlurFilter initializes correctly with required attributes."""
        filter_obj = motion_blur_instance

        assert filter_obj.filter_type == 'motion_blur'
        assert hasattr(filter_obj, 'can_apply')
        assert hasattr(filter_obj, 'apply')
        assert hasattr(filter_obj, 'validate_parameters')

    def test_basic_functionality(self, motion_blur_instance, setup_test_data):
        """Test core methods and expected input/output behavior."""
        filter_obj = motion_blur_instance

        # Test can_apply method
        can_apply_result = filter_obj.can_apply(
            setup_test_data['mock_motion_element'],
            setup_test_data['mock_context']
        )
        # Motion blur might have specific element requirements
        assert isinstance(can_apply_result, bool)

        # Test apply method if applicable
        if can_apply_result:
            result = filter_obj.apply(
                setup_test_data['mock_motion_element'],
                setup_test_data['mock_context']
            )
            assert isinstance(result, FilterResult)

    def test_error_handling(self, motion_blur_instance, setup_test_data):
        """Test motion blur error handling and edge cases."""
        filter_obj = motion_blur_instance

        # Test with invalid motion parameters
        invalid_element = etree.Element("{http://www.w3.org/2000/svg}feConvolveMatrix")
        # Missing required attributes

        result = filter_obj.apply(invalid_element, setup_test_data['mock_context'])
        assert isinstance(result, FilterResult)

    @pytest.mark.parametrize("angle,distance", [
        (0, 5),
        (45, 10),
        (90, 3),
        (180, 7),
        (270, 2),
    ])
    def test_parametrized_motion_scenarios(self, motion_blur_instance, angle, distance, setup_test_data):
        """Test MotionBlurFilter with various angle and distance combinations."""
        filter_obj = motion_blur_instance

        # Create motion blur configuration
        element = etree.Element("{http://www.w3.org/2000/svg}feConvolveMatrix")
        # Set motion parameters based on angle and distance
        element.set("data-motion-angle", str(angle))
        element.set("data-motion-distance", str(distance))

        result = filter_obj.apply(element, setup_test_data['mock_context'])
        assert isinstance(result, FilterResult)


class TestBlurFilterException:
    """Tests for BlurFilterException class."""

    def test_blur_filter_exception_initialization(self):
        """Test BlurFilterException creates correctly."""
        message = "Blur filter processing failed"
        exception = BlurFilterException(message)
        assert str(exception) == message
        assert isinstance(exception, FilterException)


class TestBlurHelperFunctions:
    """Tests for blur filter helper functions."""

    def test_calculate_blur_bounds(self):
        """Test blur bounds calculation helper function."""
        # This will be implemented when helper functions are added
        pass

    def test_optimize_blur_radius(self):
        """Test blur radius optimization helper function."""
        # This will be implemented when helper functions are added
        pass


class TestBlurIntegration:
    """Integration tests for blur filters with other components."""

    @pytest.fixture
    def integration_setup(self):
        """Setup for blur filter integration testing."""
        integration_data = {
            'svg_content': '''<svg xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <filter id="blur-filter">
                        <feGaussianBlur stdDeviation="3" edgeMode="duplicate"/>
                    </filter>
                    <filter id="anisotropic-blur">
                        <feGaussianBlur stdDeviation="5.0 2.0" edgeMode="wrap"/>
                    </filter>
                </defs>
                <rect width="100" height="50" filter="url(#blur-filter)"/>
                <circle cx="50" cy="25" r="20" filter="url(#anisotropic-blur)"/>
            </svg>''',
            'mock_context': Mock(spec=FilterContext)
        }

        # Setup mock context attributes
        integration_data['mock_context'].unit_converter = Mock()
        integration_data['mock_context'].unit_converter.to_emu.return_value = 50000
        integration_data['mock_context'].transform_parser = Mock()
        integration_data['mock_context'].color_parser = Mock()
        integration_data['mock_context'].viewport = {'width': 200, 'height': 100}
        integration_data['mock_context'].get_property.return_value = None

        return integration_data

    def test_integration_with_svg_parsing(self, integration_setup):
        """Test blur filters integration with SVG parsing."""
        from lxml import etree

        # Parse SVG content
        root = etree.fromstring(integration_setup['svg_content'])
        blur_elements = root.xpath('.//*[local-name()="feGaussianBlur"]')

        assert len(blur_elements) == 2

        # Test Gaussian blur filter
        gaussian_filter = GaussianBlurFilter()

        for blur_element in blur_elements:
            can_apply = gaussian_filter.can_apply(
                blur_element,
                integration_setup['mock_context']
            )
            assert can_apply is True

            result = gaussian_filter.apply(
                blur_element,
                integration_setup['mock_context']
            )
            assert isinstance(result, FilterResult)
            assert result.success is True

    def test_integration_with_filter_registry(self):
        """Test blur filters integration with FilterRegistry."""
        from src.converters.filters.core.registry import FilterRegistry

        registry = FilterRegistry()

        # Register blur filters
        gaussian_blur = GaussianBlurFilter()
        motion_blur = MotionBlurFilter()

        registry.register(gaussian_blur)
        registry.register(motion_blur)

        # Test registry integration
        retrieved_gaussian = registry.get_filter('gaussian_blur')
        assert isinstance(retrieved_gaussian, GaussianBlurFilter)

        retrieved_motion = registry.get_filter('motion_blur')
        assert isinstance(retrieved_motion, MotionBlurFilter)

        # Test filter discovery
        filter_types = registry.list_filters()
        assert 'gaussian_blur' in filter_types
        assert 'motion_blur' in filter_types

    def test_integration_with_filter_chain(self):
        """Test blur filters integration with FilterChain."""
        from src.converters.filters.core.chain import FilterChain

        # Create filter chain with blur filters
        gaussian_blur = GaussianBlurFilter()
        motion_blur = MotionBlurFilter()

        chain = FilterChain([gaussian_blur, motion_blur])
        assert len(chain.nodes) == 2

        # Test chain statistics
        stats = chain.get_statistics()
        assert stats['total_nodes'] == 2
        assert 'gaussian_blur' in stats['filter_types']
        assert 'motion_blur' in stats['filter_types']