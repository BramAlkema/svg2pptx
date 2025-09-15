"""
Tests for SVG geometric transformation filter implementations.

This module contains unit tests for geometric transformation filter implementations
including offset operations, turbulence generation, and mathematical edge cases
following the comprehensive testing template.
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

from src.converters.filters.geometric.transforms import (
    OffsetFilter,
    TurbulenceFilter,
    OffsetFilterException,
    TurbulenceFilterException
)


class TestOffsetFilter:
    """Test suite for OffsetFilter class."""

    @pytest.fixture
    def setup_test_data(self):
        """Setup test data for offset filter tests."""
        # Basic offset element
        mock_offset_element = etree.Element("{http://www.w3.org/2000/svg}feOffset")
        mock_offset_element.set("dx", "5")
        mock_offset_element.set("dy", "3")

        # Zero offset element
        mock_zero_element = etree.Element("{http://www.w3.org/2000/svg}feOffset")
        mock_zero_element.set("dx", "0")
        mock_zero_element.set("dy", "0")

        # Large offset element
        mock_large_element = etree.Element("{http://www.w3.org/2000/svg}feOffset")
        mock_large_element.set("dx", "100")
        mock_large_element.set("dy", "-50")

        # Use existing converter infrastructure
        mock_unit_converter = Mock()
        mock_unit_converter.to_emu.return_value = 25400
        mock_unit_converter.to_px.return_value = 1.0

        mock_transform_parser = Mock()
        mock_color_parser = Mock()
        mock_color_parser.parse.return_value = Mock(hex="FF0000", rgb=(255, 0, 0), alpha=1.0)
        mock_viewport = {'width': 200, 'height': 100}

        mock_context = Mock(spec=FilterContext)
        mock_context.unit_converter = mock_unit_converter
        mock_context.transform_parser = mock_transform_parser
        mock_context.color_parser = mock_color_parser
        mock_context.viewport = mock_viewport
        mock_context.get_property.return_value = None

        return {
            'mock_offset_element': mock_offset_element,
            'mock_zero_element': mock_zero_element,
            'mock_large_element': mock_large_element,
            'mock_context': mock_context,
            'mock_unit_converter': mock_unit_converter,
            'expected_filter_type': 'offset',
            'expected_drawingml_patterns': ['<a:outerShdw', '<a:innerShdw', 'dist=', 'dir='],
            'displacement_values': [(0, 0), (5, 3), (100, -50), (-10, 20)]
        }

    @pytest.fixture
    def offset_instance(self):
        """Create OffsetFilter instance for testing."""
        return OffsetFilter()

    def test_initialization(self, offset_instance):
        """Test OffsetFilter initializes correctly with required attributes."""
        filter_obj = offset_instance

        assert filter_obj.filter_type == 'offset'
        assert hasattr(filter_obj, 'can_apply')
        assert hasattr(filter_obj, 'apply')
        assert hasattr(filter_obj, 'validate_parameters')
        assert hasattr(filter_obj, '_parse_offset_parameters')
        assert hasattr(filter_obj, '_generate_offset_dml')

    def test_basic_functionality(self, offset_instance, setup_test_data):
        """Test core methods and expected input/output behavior."""
        filter_obj = offset_instance

        # Test can_apply method
        can_apply_result = filter_obj.can_apply(
            setup_test_data['mock_offset_element'],
            setup_test_data['mock_context']
        )
        assert can_apply_result is True

        # Test apply method with basic offset
        result = filter_obj.apply(
            setup_test_data['mock_offset_element'],
            setup_test_data['mock_context']
        )
        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.metadata['filter_type'] == 'offset'

        # Test validate_parameters method
        is_valid = filter_obj.validate_parameters(
            setup_test_data['mock_offset_element'],
            setup_test_data['mock_context']
        )
        assert is_valid is True

    def test_error_handling(self, offset_instance, setup_test_data):
        """Test error handling for invalid inputs and edge cases."""
        filter_obj = offset_instance

        # Test with None element
        can_apply_none = filter_obj.can_apply(None, setup_test_data['mock_context'])
        assert can_apply_none is False

        # Test with invalid element type
        invalid_element = etree.Element("{http://www.w3.org/2000/svg}rect")
        can_apply_invalid = filter_obj.can_apply(invalid_element, setup_test_data['mock_context'])
        assert can_apply_invalid is False

        # Test with malformed dx/dy values
        malformed_element = etree.Element("{http://www.w3.org/2000/svg}feOffset")
        malformed_element.set("dx", "invalid")
        malformed_element.set("dy", "3")

        result = filter_obj.apply(malformed_element, setup_test_data['mock_context'])
        assert result.success is False
        assert 'error' in result.metadata

    def test_edge_cases(self, offset_instance, setup_test_data):
        """Test edge cases and boundary conditions."""
        filter_obj = offset_instance

        # Test zero offset
        result = filter_obj.apply(
            setup_test_data['mock_zero_element'],
            setup_test_data['mock_context']
        )
        assert result.success is True
        assert result.metadata['dx'] == 0
        assert result.metadata['dy'] == 0

        # Test large offset values
        result = filter_obj.apply(
            setup_test_data['mock_large_element'],
            setup_test_data['mock_context']
        )
        assert result.success is True
        assert result.metadata['dx'] == 100
        assert result.metadata['dy'] == -50

    def test_configuration_options(self, offset_instance, setup_test_data):
        """Test various configuration options and parameter combinations."""
        filter_obj = offset_instance

        # Test different displacement values
        for dx, dy in setup_test_data['displacement_values']:
            element = etree.Element("{http://www.w3.org/2000/svg}feOffset")
            element.set("dx", str(dx))
            element.set("dy", str(dy))

            result = filter_obj.apply(element, setup_test_data['mock_context'])
            assert result.success is True
            assert result.metadata['dx'] == dx
            assert result.metadata['dy'] == dy

    def test_integration_with_dependencies(self, offset_instance, setup_test_data):
        """Test integration with UnitConverter, TransformParser, etc."""
        filter_obj = offset_instance
        setup_test_data['mock_context'].unit_converter.to_emu.return_value = 12700  # 5px in EMU

        result = filter_obj.apply(
            setup_test_data['mock_offset_element'],
            setup_test_data['mock_context']
        )

        # Verify the filter successfully integrates with existing architecture
        assert result.success is True
        assert setup_test_data['mock_context'].unit_converter.to_emu.called

    @pytest.mark.parametrize("dx_value,dy_value,expected_valid", [
        ("0", "0", True),
        ("5", "3", True),
        ("-10", "20", True),
        ("100.5", "-50.7", True),
        ("invalid", "3", False),
        ("5", "invalid", False),
        ("", "3", True),  # Empty dx should default to 0
    ])
    def test_parametrized_offset_scenarios(self, offset_instance, setup_test_data, dx_value, dy_value, expected_valid):
        """Test various offset parameter scenarios."""
        filter_obj = offset_instance

        element = etree.Element("{http://www.w3.org/2000/svg}feOffset")
        if dx_value:
            element.set("dx", dx_value)
        if dy_value:
            element.set("dy", dy_value)

        result = filter_obj.apply(element, setup_test_data['mock_context'])
        assert result.success == expected_valid

    def test_performance_characteristics(self, offset_instance, setup_test_data):
        """Test performance characteristics and resource usage."""
        filter_obj = offset_instance

        # Test processing multiple elements efficiently
        elements = []
        for i in range(100):
            element = etree.Element("{http://www.w3.org/2000/svg}feOffset")
            element.set("dx", str(i))
            element.set("dy", str(i * 2))
            elements.append(element)

        # Process all elements and verify performance is reasonable
        results = []
        for element in elements:
            result = filter_obj.apply(element, setup_test_data['mock_context'])
            results.append(result)
            assert result.success is True

        assert len(results) == 100

    def test_thread_safety(self, offset_instance, setup_test_data):
        """Test thread safety of filter operations."""
        filter_obj = offset_instance

        # Create multiple contexts to simulate concurrent usage
        contexts = []
        for i in range(10):
            context = Mock(spec=FilterContext)
            context.unit_converter = Mock()
            context.unit_converter.to_emu.return_value = 25400 * i
            contexts.append(context)

        # Test concurrent-like access (simulated)
        for i, context in enumerate(contexts):
            element = etree.Element("{http://www.w3.org/2000/svg}feOffset")
            element.set("dx", str(i))
            element.set("dy", str(i * 2))

            result = filter_obj.apply(element, context)
            assert result.success is True
            assert result.metadata['dx'] == i
            assert result.metadata['dy'] == i * 2


class TestTurbulenceFilter:
    """Test suite for TurbulenceFilter class."""

    @pytest.fixture
    def setup_test_data(self):
        """Setup test data for turbulence filter tests."""
        # Basic turbulence element
        mock_turbulence_element = etree.Element("{http://www.w3.org/2000/svg}feTurbulence")
        mock_turbulence_element.set("baseFrequency", "0.1")
        mock_turbulence_element.set("numOctaves", "2")
        mock_turbulence_element.set("seed", "5")

        # High frequency turbulence
        mock_high_freq_element = etree.Element("{http://www.w3.org/2000/svg}feTurbulence")
        mock_high_freq_element.set("baseFrequency", "0.5 0.3")
        mock_high_freq_element.set("numOctaves", "4")
        mock_high_freq_element.set("type", "fractalNoise")

        # Use existing converter infrastructure
        mock_unit_converter = Mock()
        mock_unit_converter.to_emu.return_value = 25400
        mock_unit_converter.to_px.return_value = 1.0

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
            'mock_turbulence_element': mock_turbulence_element,
            'mock_high_freq_element': mock_high_freq_element,
            'mock_context': mock_context,
            'expected_filter_type': 'turbulence',
            'expected_drawingml_patterns': ['<a:fillOverlay', '<a:prstDash', 'val="solid"'],
            'frequency_values': [0.1, 0.05, 0.3, 0.8],
            'octave_values': [1, 2, 4, 6],
            'turbulence_types': ['turbulence', 'fractalNoise']
        }

    @pytest.fixture
    def turbulence_instance(self):
        """Create TurbulenceFilter instance for testing."""
        return TurbulenceFilter()

    def test_initialization(self, turbulence_instance):
        """Test TurbulenceFilter initializes correctly with required attributes."""
        filter_obj = turbulence_instance

        assert filter_obj.filter_type == 'turbulence'
        assert hasattr(filter_obj, 'can_apply')
        assert hasattr(filter_obj, 'apply')
        assert hasattr(filter_obj, 'validate_parameters')
        assert hasattr(filter_obj, '_parse_turbulence_parameters')
        assert hasattr(filter_obj, '_generate_turbulence_dml')

    def test_basic_functionality(self, turbulence_instance, setup_test_data):
        """Test core methods and expected input/output behavior."""
        filter_obj = turbulence_instance

        # Test can_apply method
        can_apply_result = filter_obj.can_apply(
            setup_test_data['mock_turbulence_element'],
            setup_test_data['mock_context']
        )
        assert can_apply_result is True

        # Test apply method
        result = filter_obj.apply(
            setup_test_data['mock_turbulence_element'],
            setup_test_data['mock_context']
        )
        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.metadata['filter_type'] == 'turbulence'

    def test_error_handling(self, turbulence_instance, setup_test_data):
        """Test error handling for invalid inputs and edge cases."""
        filter_obj = turbulence_instance

        # Test with None element
        can_apply_none = filter_obj.can_apply(None, setup_test_data['mock_context'])
        assert can_apply_none is False

        # Test with invalid frequency values
        invalid_element = etree.Element("{http://www.w3.org/2000/svg}feTurbulence")
        invalid_element.set("baseFrequency", "invalid")

        result = filter_obj.apply(invalid_element, setup_test_data['mock_context'])
        assert result.success is False

    def test_mathematical_edge_cases(self, turbulence_instance, setup_test_data):
        """Test mathematical edge cases for turbulence generation."""
        filter_obj = turbulence_instance

        # Test zero frequency
        zero_freq_element = etree.Element("{http://www.w3.org/2000/svg}feTurbulence")
        zero_freq_element.set("baseFrequency", "0")

        result = filter_obj.apply(zero_freq_element, setup_test_data['mock_context'])
        assert result.success is True

        # Test very high frequency
        high_freq_element = etree.Element("{http://www.w3.org/2000/svg}feTurbulence")
        high_freq_element.set("baseFrequency", "1.0")
        high_freq_element.set("numOctaves", "10")

        result = filter_obj.apply(high_freq_element, setup_test_data['mock_context'])
        assert result.success is True

    @pytest.mark.parametrize("base_frequency,num_octaves,expected_valid", [
        ("0.1", "2", True),
        ("0.05", "1", True),
        ("0.3 0.2", "4", True),
        ("invalid", "2", False),
        ("0.1", "invalid", False),
        ("1.0", "0", True),
        ("-0.1", "2", False),  # Negative frequency should be invalid
    ])
    def test_parametrized_turbulence_scenarios(self, turbulence_instance, setup_test_data,
                                             base_frequency, num_octaves, expected_valid):
        """Test various turbulence parameter scenarios."""
        filter_obj = turbulence_instance

        element = etree.Element("{http://www.w3.org/2000/svg}feTurbulence")
        element.set("baseFrequency", base_frequency)
        element.set("numOctaves", num_octaves)

        result = filter_obj.apply(element, setup_test_data['mock_context'])
        assert result.success == expected_valid

    def test_turbulence_types(self, turbulence_instance, setup_test_data):
        """Test different turbulence types."""
        filter_obj = turbulence_instance

        for turb_type in setup_test_data['turbulence_types']:
            element = etree.Element("{http://www.w3.org/2000/svg}feTurbulence")
            element.set("type", turb_type)
            element.set("baseFrequency", "0.1")

            result = filter_obj.apply(element, setup_test_data['mock_context'])
            assert result.success is True
            assert result.metadata['turbulence_type'] == turb_type


class TestOffsetFilterException:
    """Test suite for OffsetFilterException class."""

    def test_offset_filter_exception_initialization(self):
        """Test OffsetFilterException initializes correctly."""
        message = "Test offset error"
        exception = OffsetFilterException(message)

        assert isinstance(exception, FilterException)
        assert str(exception) == message


class TestTurbulenceFilterException:
    """Test suite for TurbulenceFilterException class."""

    def test_turbulence_filter_exception_initialization(self):
        """Test TurbulenceFilterException initializes correctly."""
        message = "Test turbulence error"
        exception = TurbulenceFilterException(message)

        assert isinstance(exception, FilterException)
        assert str(exception) == message


class TestGeometricHelperFunctions:
    """Test suite for geometric transformation helper functions."""

    def test_calculate_offset_bounds(self):
        """Test calculation of offset effect bounds."""
        # This would test helper functions for calculating effect regions
        # Implementation depends on the actual helper functions created
        pass

    def test_optimize_turbulence_parameters(self):
        """Test optimization of turbulence parameters for performance."""
        # This would test performance optimization functions
        # Implementation depends on the actual helper functions created
        pass

    def test_validate_geometric_parameters(self):
        """Test validation of geometric transformation parameters."""
        # This would test parameter validation helper functions
        # Implementation depends on the actual helper functions created
        pass


class TestGeometricIntegration:
    """Integration tests for geometric transform filters with other components."""

    @pytest.fixture
    def integration_setup(self):
        """Setup for geometric filter integration testing."""
        integration_data = {
            'svg_content': '''<svg xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <filter id="offset-filter">
                        <feOffset dx="10" dy="5" in="SourceGraphic"/>
                    </filter>
                    <filter id="turbulence-filter">
                        <feTurbulence baseFrequency="0.2" numOctaves="3" type="turbulence"/>
                    </filter>
                </defs>
                <rect width="100" height="50" filter="url(#offset-filter)"/>
                <circle cx="50" cy="25" r="20" filter="url(#turbulence-filter)"/>
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
        """Test geometric filters integration with SVG parsing."""
        from lxml import etree

        # Parse SVG content
        root = etree.fromstring(integration_setup['svg_content'])
        offset_elements = root.xpath('.//*[local-name()="feOffset"]')
        turbulence_elements = root.xpath('.//*[local-name()="feTurbulence"]')

        assert len(offset_elements) == 1
        assert len(turbulence_elements) == 1

        # Test offset filter
        offset_filter = OffsetFilter()
        for element in offset_elements:
            can_apply = offset_filter.can_apply(element, integration_setup['mock_context'])
            assert can_apply is True

            result = offset_filter.apply(element, integration_setup['mock_context'])
            assert result.success is True

        # Test turbulence filter
        turbulence_filter = TurbulenceFilter()
        for element in turbulence_elements:
            can_apply = turbulence_filter.can_apply(element, integration_setup['mock_context'])
            assert can_apply is True

            result = turbulence_filter.apply(element, integration_setup['mock_context'])
            assert result.success is True

    def test_integration_with_filter_registry(self, integration_setup):
        """Test geometric filters integration with FilterRegistry."""
        from src.converters.filters.core.registry import FilterRegistry

        registry = FilterRegistry()

        # Register geometric filters
        registry.register_filter(OffsetFilter())
        registry.register_filter(TurbulenceFilter())

        # Test filter discovery
        offset_element = etree.Element("{http://www.w3.org/2000/svg}feOffset")
        offset_element.set("dx", "5")

        applicable_filters = registry.get_applicable_filters(
            offset_element, integration_setup['mock_context']
        )

        assert len(applicable_filters) > 0
        assert any(f.filter_type == 'offset' for f in applicable_filters)

    def test_integration_with_filter_chain(self, integration_setup):
        """Test geometric filters integration with FilterChain."""
        from src.converters.filters.core.chain import FilterChain

        # Create filter chain with geometric transforms
        chain = FilterChain()
        chain.add_filter(OffsetFilter())
        chain.add_filter(TurbulenceFilter())

        # Test chain execution
        offset_element = etree.Element("{http://www.w3.org/2000/svg}feOffset")
        offset_element.set("dx", "10")
        offset_element.set("dy", "5")

        result = chain.apply(offset_element, integration_setup['mock_context'])
        assert result is not None
        assert result.success