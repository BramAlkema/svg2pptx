"""
Tests for SVG composite filter implementations.

This module contains unit tests for composite filter implementations including
merge operations, blend modes, and multi-layer processing scenarios
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

from src.converters.filters.geometric.composite import (
    CompositeFilter,
    MergeFilter,
    BlendFilter,
    CompositeFilterException,
    MergeFilterException,
    BlendFilterException
)


class TestCompositeFilter:
    """Test suite for CompositeFilter class."""

    @pytest.fixture
    def setup_test_data(self):
        """Setup test data for composite filter tests."""
        # Basic composite element - 'over' operation
        mock_over_element = etree.Element("{http://www.w3.org/2000/svg}feComposite")
        mock_over_element.set("operator", "over")
        mock_over_element.set("in", "SourceGraphic")
        mock_over_element.set("in2", "BackgroundImage")

        # Arithmetic composite element
        mock_arithmetic_element = etree.Element("{http://www.w3.org/2000/svg}feComposite")
        mock_arithmetic_element.set("operator", "arithmetic")
        mock_arithmetic_element.set("k1", "0")
        mock_arithmetic_element.set("k2", "1")
        mock_arithmetic_element.set("k3", "1")
        mock_arithmetic_element.set("k4", "0")

        # XOR composite element
        mock_xor_element = etree.Element("{http://www.w3.org/2000/svg}feComposite")
        mock_xor_element.set("operator", "xor")
        mock_xor_element.set("in", "SourceGraphic")
        mock_xor_element.set("in2", "blur-result")

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
            'mock_over_element': mock_over_element,
            'mock_arithmetic_element': mock_arithmetic_element,
            'mock_xor_element': mock_xor_element,
            'mock_context': mock_context,
            'mock_unit_converter': mock_unit_converter,
            'expected_filter_type': 'composite',
            'expected_drawingml_patterns': ['<a:blend', '<a:alpha', '<a:solidFill'],
            'composite_operators': ['over', 'in', 'out', 'atop', 'xor', 'multiply', 'screen', 'darken', 'lighten', 'arithmetic'],
            'arithmetic_coefficients': [(0, 1, 1, 0), (1, 0, 0, 0), (0.5, 0.5, 0.5, 0.2)]
        }

    @pytest.fixture
    def composite_instance(self):
        """Create CompositeFilter instance for testing."""
        return CompositeFilter()

    def test_initialization(self, composite_instance):
        """Test CompositeFilter initializes correctly with required attributes."""
        filter_obj = composite_instance

        assert filter_obj.filter_type == 'composite'
        assert hasattr(filter_obj, 'can_apply')
        assert hasattr(filter_obj, 'apply')
        assert hasattr(filter_obj, 'validate_parameters')
        assert hasattr(filter_obj, '_parse_composite_parameters')
        assert hasattr(filter_obj, '_generate_composite_dml')

    def test_basic_functionality(self, composite_instance, setup_test_data):
        """Test core methods and expected input/output behavior."""
        filter_obj = composite_instance

        # Test can_apply method
        can_apply_result = filter_obj.can_apply(
            setup_test_data['mock_over_element'],
            setup_test_data['mock_context']
        )
        assert can_apply_result is True

        # Test apply method with 'over' operation
        result = filter_obj.apply(
            setup_test_data['mock_over_element'],
            setup_test_data['mock_context']
        )
        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.metadata['filter_type'] == 'composite'
        assert result.metadata['operator'] == 'over'

        # Test validate_parameters method
        is_valid = filter_obj.validate_parameters(
            setup_test_data['mock_over_element'],
            setup_test_data['mock_context']
        )
        assert is_valid is True

    def test_error_handling(self, composite_instance, setup_test_data):
        """Test error handling for invalid inputs and edge cases."""
        filter_obj = composite_instance

        # Test with None element
        can_apply_none = filter_obj.can_apply(None, setup_test_data['mock_context'])
        assert can_apply_none is False

        # Test with invalid element type
        invalid_element = etree.Element("{http://www.w3.org/2000/svg}rect")
        can_apply_invalid = filter_obj.can_apply(invalid_element, setup_test_data['mock_context'])
        assert can_apply_invalid is False

        # Test with invalid operator
        invalid_element = etree.Element("{http://www.w3.org/2000/svg}feComposite")
        invalid_element.set("operator", "invalid-op")

        result = filter_obj.apply(invalid_element, setup_test_data['mock_context'])
        assert result.success is False
        assert 'error' in result.metadata

    def test_edge_cases(self, composite_instance, setup_test_data):
        """Test edge cases and boundary conditions."""
        filter_obj = composite_instance

        # Test arithmetic operation with edge coefficients
        result = filter_obj.apply(
            setup_test_data['mock_arithmetic_element'],
            setup_test_data['mock_context']
        )
        assert result.success is True
        assert result.metadata['operator'] == 'arithmetic'
        assert result.metadata['k1'] == 0
        assert result.metadata['k2'] == 1

        # Test XOR operation
        result = filter_obj.apply(
            setup_test_data['mock_xor_element'],
            setup_test_data['mock_context']
        )
        assert result.success is True
        assert result.metadata['operator'] == 'xor'

    def test_configuration_options(self, composite_instance, setup_test_data):
        """Test various configuration options and parameter combinations."""
        filter_obj = composite_instance

        # Test different composite operators
        for operator in setup_test_data['composite_operators']:
            element = etree.Element("{http://www.w3.org/2000/svg}feComposite")
            element.set("operator", operator)
            element.set("in", "SourceGraphic")
            element.set("in2", "BackgroundImage")

            if operator == 'arithmetic':
                element.set("k1", "0.5")
                element.set("k2", "0.5")
                element.set("k3", "0.5")
                element.set("k4", "0.1")

            result = filter_obj.apply(element, setup_test_data['mock_context'])
            assert result.success is True
            assert result.metadata['operator'] == operator

    def test_integration_with_dependencies(self, composite_instance, setup_test_data):
        """Test integration with UnitConverter, TransformParser, etc."""
        filter_obj = composite_instance

        result = filter_obj.apply(
            setup_test_data['mock_over_element'],
            setup_test_data['mock_context']
        )

        # Verify the filter successfully integrates with existing architecture
        assert result.success is True
        # Composite operations typically don't directly use unit converter
        # but should have access to the full context

    @pytest.mark.parametrize("operator,k1,k2,k3,k4,expected_valid", [
        ("over", None, None, None, None, True),
        ("multiply", None, None, None, None, True),
        ("screen", None, None, None, None, True),
        ("arithmetic", "0", "1", "1", "0", True),
        ("arithmetic", "0.5", "0.5", "0.5", "0.2", True),
        ("arithmetic", "invalid", "1", "1", "0", False),
        ("invalid-operator", None, None, None, None, False),
    ])
    def test_parametrized_composite_scenarios(self, composite_instance, setup_test_data,
                                            operator, k1, k2, k3, k4, expected_valid):
        """Test various composite parameter scenarios."""
        filter_obj = composite_instance

        element = etree.Element("{http://www.w3.org/2000/svg}feComposite")
        element.set("operator", operator)
        element.set("in", "SourceGraphic")
        element.set("in2", "BackgroundImage")

        if operator == 'arithmetic':
            if k1: element.set("k1", k1)
            if k2: element.set("k2", k2)
            if k3: element.set("k3", k3)
            if k4: element.set("k4", k4)

        result = filter_obj.apply(element, setup_test_data['mock_context'])
        assert result.success == expected_valid

    def test_multi_layer_processing(self, composite_instance, setup_test_data):
        """Test multi-layer processing scenarios."""
        filter_obj = composite_instance

        # Create multiple composite operations to test layering
        layer_configs = [
            ("multiply", "layer1", "layer2"),
            ("screen", "layer2", "layer3"),
            ("over", "layer3", "SourceGraphic")
        ]

        for operator, in1, in2 in layer_configs:
            element = etree.Element("{http://www.w3.org/2000/svg}feComposite")
            element.set("operator", operator)
            element.set("in", in1)
            element.set("in2", in2)

            result = filter_obj.apply(element, setup_test_data['mock_context'])
            assert result.success is True
            assert result.metadata['operator'] == operator
            assert result.metadata['input1'] == in1
            assert result.metadata['input2'] == in2


class TestMergeFilter:
    """Test suite for MergeFilter class."""

    @pytest.fixture
    def setup_test_data(self):
        """Setup test data for merge filter tests."""
        # Basic merge element with merge nodes
        mock_merge_element = etree.Element("{http://www.w3.org/2000/svg}feMerge")

        node1 = etree.SubElement(mock_merge_element, "{http://www.w3.org/2000/svg}feMergeNode")
        node1.set("in", "SourceGraphic")

        node2 = etree.SubElement(mock_merge_element, "{http://www.w3.org/2000/svg}feMergeNode")
        node2.set("in", "blur-effect")

        node3 = etree.SubElement(mock_merge_element, "{http://www.w3.org/2000/svg}feMergeNode")
        node3.set("in", "shadow-effect")

        # Use existing converter infrastructure
        mock_unit_converter = Mock()
        mock_unit_converter.to_emu.return_value = 25400

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
            'mock_merge_element': mock_merge_element,
            'mock_context': mock_context,
            'expected_filter_type': 'merge',
            'expected_merge_inputs': ['SourceGraphic', 'blur-effect', 'shadow-effect']
        }

    @pytest.fixture
    def merge_instance(self):
        """Create MergeFilter instance for testing."""
        return MergeFilter()

    def test_initialization(self, merge_instance):
        """Test MergeFilter initializes correctly with required attributes."""
        filter_obj = merge_instance

        assert filter_obj.filter_type == 'merge'
        assert hasattr(filter_obj, 'can_apply')
        assert hasattr(filter_obj, 'apply')
        assert hasattr(filter_obj, 'validate_parameters')
        assert hasattr(filter_obj, '_parse_merge_nodes')
        assert hasattr(filter_obj, '_generate_merge_dml')

    def test_basic_functionality(self, merge_instance, setup_test_data):
        """Test core methods and expected input/output behavior."""
        filter_obj = merge_instance

        # Test can_apply method
        can_apply_result = filter_obj.can_apply(
            setup_test_data['mock_merge_element'],
            setup_test_data['mock_context']
        )
        assert can_apply_result is True

        # Test apply method
        result = filter_obj.apply(
            setup_test_data['mock_merge_element'],
            setup_test_data['mock_context']
        )
        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.metadata['filter_type'] == 'merge'
        assert len(result.metadata['merge_inputs']) == 3

    def test_error_handling(self, merge_instance, setup_test_data):
        """Test error handling for invalid inputs and edge cases."""
        filter_obj = merge_instance

        # Test with None element
        can_apply_none = filter_obj.can_apply(None, setup_test_data['mock_context'])
        assert can_apply_none is False

        # Test with empty merge (no merge nodes)
        empty_merge = etree.Element("{http://www.w3.org/2000/svg}feMerge")
        result = filter_obj.apply(empty_merge, setup_test_data['mock_context'])
        assert result.success is True  # Empty merge should be valid
        assert len(result.metadata['merge_inputs']) == 0


class TestBlendFilter:
    """Test suite for BlendFilter class."""

    @pytest.fixture
    def setup_test_data(self):
        """Setup test data for blend filter tests."""
        # Basic blend element
        mock_blend_element = etree.Element("{http://www.w3.org/2000/svg}feBlend")
        mock_blend_element.set("mode", "multiply")
        mock_blend_element.set("in", "SourceGraphic")
        mock_blend_element.set("in2", "BackgroundImage")

        # Screen blend element
        mock_screen_element = etree.Element("{http://www.w3.org/2000/svg}feBlend")
        mock_screen_element.set("mode", "screen")
        mock_screen_element.set("in", "layer1")
        mock_screen_element.set("in2", "layer2")

        # Use existing converter infrastructure
        mock_unit_converter = Mock()
        mock_unit_converter.to_emu.return_value = 25400

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
            'mock_blend_element': mock_blend_element,
            'mock_screen_element': mock_screen_element,
            'mock_context': mock_context,
            'expected_filter_type': 'blend',
            'blend_modes': ['normal', 'multiply', 'screen', 'darken', 'lighten', 'overlay', 'color-dodge', 'color-burn', 'hard-light', 'soft-light', 'difference', 'exclusion']
        }

    @pytest.fixture
    def blend_instance(self):
        """Create BlendFilter instance for testing."""
        return BlendFilter()

    def test_initialization(self, blend_instance):
        """Test BlendFilter initializes correctly with required attributes."""
        filter_obj = blend_instance

        assert filter_obj.filter_type == 'blend'
        assert hasattr(filter_obj, 'can_apply')
        assert hasattr(filter_obj, 'apply')
        assert hasattr(filter_obj, 'validate_parameters')
        assert hasattr(filter_obj, '_parse_blend_parameters')
        assert hasattr(filter_obj, '_generate_blend_dml')

    def test_basic_functionality(self, blend_instance, setup_test_data):
        """Test core methods and expected input/output behavior."""
        filter_obj = blend_instance

        # Test can_apply method
        can_apply_result = filter_obj.can_apply(
            setup_test_data['mock_blend_element'],
            setup_test_data['mock_context']
        )
        assert can_apply_result is True

        # Test apply method
        result = filter_obj.apply(
            setup_test_data['mock_blend_element'],
            setup_test_data['mock_context']
        )
        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.metadata['filter_type'] == 'blend'
        assert result.metadata['mode'] == 'multiply'

    @pytest.mark.parametrize("blend_mode,expected_valid", [
        ("normal", True),
        ("multiply", True),
        ("screen", True),
        ("overlay", True),
        ("darken", True),
        ("lighten", True),
        ("color-dodge", True),
        ("invalid-mode", False),
    ])
    def test_parametrized_blend_modes(self, blend_instance, setup_test_data, blend_mode, expected_valid):
        """Test various blend mode scenarios."""
        filter_obj = blend_instance

        element = etree.Element("{http://www.w3.org/2000/svg}feBlend")
        element.set("mode", blend_mode)
        element.set("in", "SourceGraphic")
        element.set("in2", "BackgroundImage")

        result = filter_obj.apply(element, setup_test_data['mock_context'])
        assert result.success == expected_valid


class TestCompositeHelperFunctions:
    """Test suite for composite operation helper functions."""

    def test_blend_mode_mapping(self):
        """Test mapping of SVG blend modes to PowerPoint equivalents."""
        # This would test helper functions for blend mode conversion
        pass

    def test_composite_operation_optimization(self):
        """Test optimization of composite operations for performance."""
        # This would test performance optimization functions
        pass


class TestCompositeIntegration:
    """Integration tests for composite filters with other components."""

    @pytest.fixture
    def integration_setup(self):
        """Setup for composite filter integration testing."""
        integration_data = {
            'svg_content': '''<svg xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <filter id="composite-filter">
                        <feComposite operator="over" in="SourceGraphic" in2="BackgroundImage"/>
                    </filter>
                    <filter id="merge-filter">
                        <feMerge>
                            <feMergeNode in="SourceGraphic"/>
                            <feMergeNode in="effect1"/>
                            <feMergeNode in="effect2"/>
                        </feMerge>
                    </filter>
                    <filter id="blend-filter">
                        <feBlend mode="multiply" in="SourceGraphic" in2="BackgroundImage"/>
                    </filter>
                </defs>
                <rect width="100" height="50" filter="url(#composite-filter)"/>
                <circle cx="50" cy="25" r="20" filter="url(#blend-filter)"/>
            </svg>''',
            'mock_context': Mock(spec=FilterContext)
        }

        # Setup mock context attributes using existing architecture
        integration_data['mock_context'].unit_converter = Mock()
        integration_data['mock_context'].unit_converter.to_emu.return_value = 50000
        integration_data['mock_context'].transform_parser = Mock()
        integration_data['mock_context'].color_parser = Mock()
        integration_data['mock_context'].viewport = {'width': 200, 'height': 100}
        integration_data['mock_context'].get_property.return_value = None

        return integration_data

    def test_integration_with_svg_parsing(self, integration_setup):
        """Test composite filters integration with SVG parsing."""
        from lxml import etree

        # Parse SVG content
        root = etree.fromstring(integration_setup['svg_content'])
        composite_elements = root.xpath('.//*[local-name()="feComposite"]')
        merge_elements = root.xpath('.//*[local-name()="feMerge"]')
        blend_elements = root.xpath('.//*[local-name()="feBlend"]')

        assert len(composite_elements) == 1
        assert len(merge_elements) == 1
        assert len(blend_elements) == 1

        # Test composite filter
        composite_filter = CompositeFilter()
        for element in composite_elements:
            can_apply = composite_filter.can_apply(element, integration_setup['mock_context'])
            assert can_apply is True

            result = composite_filter.apply(element, integration_setup['mock_context'])
            assert result.success is True

    def test_integration_with_filter_registry(self, integration_setup):
        """Test composite filters integration with FilterRegistry."""
        from src.converters.filters.core.registry import FilterRegistry

        registry = FilterRegistry()

        # Register composite filters
        registry.register_filter(CompositeFilter())
        registry.register_filter(MergeFilter())
        registry.register_filter(BlendFilter())

        # Test filter discovery
        composite_element = etree.Element("{http://www.w3.org/2000/svg}feComposite")
        composite_element.set("operator", "over")

        applicable_filters = registry.get_applicable_filters(
            composite_element, integration_setup['mock_context']
        )

        assert len(applicable_filters) > 0
        assert any(f.filter_type == 'composite' for f in applicable_filters)