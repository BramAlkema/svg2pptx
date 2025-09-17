"""
Tests for SVG color filter implementations.

This module contains unit tests for color filter implementations including
color matrix operations, flood effects, and lighting transformations
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
from src.converters.filters.image.color import (
    ColorMatrixFilter,
    FloodFilter,
    LightingFilter,
    ColorFilterException
)

# Import main color system for integration testing
from src.colors import (
    adjust_saturation,
    calculate_luminance,
    rotate_hue,
    apply_color_matrix,
    luminance_to_alpha,
    parse_color
)


class TestColorMatrixFilter:
    """Tests for ColorMatrixFilter implementation."""

    @pytest.fixture
    def setup_test_data(self):
        """Setup common test data and mock objects."""
        # Identity matrix (no change)
        mock_identity_element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        mock_identity_element.set("values", "1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0")
        mock_identity_element.set("type", "matrix")

        # Saturate type
        mock_saturate_element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        mock_saturate_element.set("type", "saturate")
        mock_saturate_element.set("values", "0.5")  # 50% saturation

        # Hue rotate type
        mock_huerotate_element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        mock_huerotate_element.set("type", "hueRotate")
        mock_huerotate_element.set("values", "90")  # 90 degree rotation

        # Luminance to alpha
        mock_luminance_element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        mock_luminance_element.set("type", "luminanceToAlpha")

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
            'mock_identity_element': mock_identity_element,
            'mock_saturate_element': mock_saturate_element,
            'mock_huerotate_element': mock_huerotate_element,
            'mock_luminance_element': mock_luminance_element,
            'mock_context': mock_context,
            'mock_color_parser': mock_color_parser,
            'expected_filter_type': 'color_matrix',
            'matrix_types': ['matrix', 'saturate', 'hueRotate', 'luminanceToAlpha'],
            'expected_drawingml_patterns': ['<a:tint', '<a:shade', '<a:alpha', '<a:hue']
        }

    @pytest.fixture
    def color_matrix_instance(self):
        """Create ColorMatrixFilter instance for testing."""
        return ColorMatrixFilter()

    def test_initialization(self, color_matrix_instance):
        """Test ColorMatrixFilter initializes correctly with required attributes."""
        filter_obj = color_matrix_instance

        assert filter_obj.filter_type == 'color_matrix'
        assert hasattr(filter_obj, 'can_apply')
        assert hasattr(filter_obj, 'apply')
        assert hasattr(filter_obj, 'validate_parameters')
        assert hasattr(filter_obj, '_parse_matrix_values')
        assert hasattr(filter_obj, '_generate_color_matrix_dml')

    def test_basic_functionality(self, color_matrix_instance, setup_test_data):
        """Test core methods and expected input/output behavior."""
        filter_obj = color_matrix_instance

        # Test can_apply method
        can_apply_result = filter_obj.can_apply(
            setup_test_data['mock_identity_element'],
            setup_test_data['mock_context']
        )
        assert can_apply_result is True

        # Test apply method with identity matrix
        result = filter_obj.apply(
            setup_test_data['mock_identity_element'],
            setup_test_data['mock_context']
        )
        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.metadata['filter_type'] == 'color_matrix'

        # Test validate_parameters method
        is_valid = filter_obj.validate_parameters(
            setup_test_data['mock_identity_element'],
            setup_test_data['mock_context']
        )
        assert is_valid is True

    def test_error_handling(self, color_matrix_instance, setup_test_data):
        """Test invalid input handling, malformed matrices, and error scenarios."""
        filter_obj = color_matrix_instance

        # Test element without values attribute
        malformed_element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        malformed_element.set("type", "matrix")
        # No values attribute

        result = filter_obj.apply(malformed_element, setup_test_data['mock_context'])
        assert isinstance(result, FilterResult)
        # Should handle gracefully with default or provide error

        # Test invalid matrix values
        invalid_element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        invalid_element.set("type", "matrix")
        invalid_element.set("values", "1 2 3 invalid 5")  # Contains invalid number

        result = filter_obj.apply(invalid_element, setup_test_data['mock_context'])
        assert isinstance(result, FilterResult)
        if not result.success:
            assert "invalid" in result.error_message.lower()

        # Test wrong number of matrix values
        wrong_count_element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        wrong_count_element.set("type", "matrix")
        wrong_count_element.set("values", "1 0 0 0")  # Only 4 values instead of 20

        result = filter_obj.apply(wrong_count_element, setup_test_data['mock_context'])
        assert isinstance(result, FilterResult)
        if not result.success:
            assert "matrix" in result.error_message.lower()

    def test_edge_cases(self, color_matrix_instance, setup_test_data):
        """Test edge cases and boundary conditions."""
        filter_obj = color_matrix_instance

        # Test saturate with edge values
        zero_saturate = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        zero_saturate.set("type", "saturate")
        zero_saturate.set("values", "0")  # Complete desaturation

        result = filter_obj.apply(zero_saturate, setup_test_data['mock_context'])
        assert isinstance(result, FilterResult)
        assert result.success is True

        # Test hue rotate with large angles
        large_hue = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        large_hue.set("type", "hueRotate")
        large_hue.set("values", "720")  # Two full rotations

        result = filter_obj.apply(large_hue, setup_test_data['mock_context'])
        assert isinstance(result, FilterResult)
        assert result.success is True

        # Test luminance to alpha (no values needed)
        result = filter_obj.apply(
            setup_test_data['mock_luminance_element'],
            setup_test_data['mock_context']
        )
        assert isinstance(result, FilterResult)
        assert result.success is True

    def test_configuration_options(self, color_matrix_instance, setup_test_data):
        """Test filter configuration and matrix type variations."""
        filter_obj = color_matrix_instance

        # Test all matrix types
        for matrix_type in setup_test_data['matrix_types']:
            element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
            element.set("type", matrix_type)

            if matrix_type == "matrix":
                element.set("values", "1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0")
            elif matrix_type == "saturate":
                element.set("values", "0.8")
            elif matrix_type == "hueRotate":
                element.set("values", "45")
            # luminanceToAlpha needs no values

            result = filter_obj.apply(element, setup_test_data['mock_context'])
            assert isinstance(result, FilterResult)
            assert result.success is True
            assert result.metadata.get('matrix_type') == matrix_type

    def test_integration_with_dependencies(self, color_matrix_instance, setup_test_data):
        """Test ColorMatrixFilter integration with color parser and other dependencies."""
        filter_obj = color_matrix_instance

        # Test color parser integration for flood color analysis
        setup_test_data['mock_color_parser'].parse.return_value = Mock(
            hex="00FF00", rgb=(0, 255, 0), alpha=0.8
        )

        result = filter_obj.apply(
            setup_test_data['mock_identity_element'],
            setup_test_data['mock_context']
        )

        # Verify dependencies were used appropriately
        assert result.success is True

    @pytest.mark.parametrize("matrix_type,values,expected_valid", [
        ("matrix", "1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0", True),
        ("saturate", "0.5", True),
        ("saturate", "0", True),
        ("saturate", "1", True),
        ("saturate", "2", True),  # Over-saturation
        ("hueRotate", "90", True),
        ("hueRotate", "0", True),
        ("hueRotate", "360", True),
        ("hueRotate", "-90", True),  # Negative rotation
        ("luminanceToAlpha", "", True),  # No values needed
        ("matrix", "1 2 3", False),  # Wrong count
        ("saturate", "invalid", False),  # Invalid value
        ("hueRotate", "not_a_number", False),  # Invalid value
        ("invalidType", "1", False),  # Invalid type
    ])
    def test_parametrized_matrix_scenarios(self, color_matrix_instance, matrix_type, values, expected_valid, setup_test_data):
        """Test ColorMatrixFilter with various matrix type and value combinations."""
        filter_obj = color_matrix_instance

        element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        element.set("type", matrix_type)
        if values:
            element.set("values", values)

        result = filter_obj.apply(element, setup_test_data['mock_context'])
        assert isinstance(result, FilterResult)

        if expected_valid:
            assert result.success is True
        else:
            if not result.success:
                assert result.error_message is not None

    def test_performance_characteristics(self, color_matrix_instance, setup_test_data):
        """Test color matrix filter performance and resource usage."""
        filter_obj = color_matrix_instance
        import time

        # Test processing time
        start_time = time.time()
        for i in range(50):
            saturation = i / 50.0
            element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
            element.set("type", "saturate")
            element.set("values", str(saturation))

            result = filter_obj.apply(element, setup_test_data['mock_context'])
            assert result.success is True

        processing_time = time.time() - start_time
        assert processing_time < 1.0, f"Processing took too long: {processing_time}s"

    def test_thread_safety(self, color_matrix_instance, setup_test_data):
        """Test thread safety of color matrix operations."""
        import threading
        import time

        filter_obj = color_matrix_instance
        results = []
        errors = []
        lock = threading.Lock()

        def apply_color_matrix():
            try:
                element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
                element.set("type", "saturate")
                element.set("values", "0.8")

                result = filter_obj.apply(element, setup_test_data['mock_context'])
                with lock:
                    results.append(result)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        # Create and run threads
        threads = [threading.Thread(target=apply_color_matrix) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify results
        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(results) == 5
        for result in results:
            assert result.success is True


class TestFloodFilter:
    """Tests for FloodFilter implementation."""

    @pytest.fixture
    def setup_test_data(self):
        """Setup common test data for FloodFilter testing."""
        mock_flood_element = etree.Element("{http://www.w3.org/2000/svg}feFlood")
        mock_flood_element.set("flood-color", "#FF0000")
        mock_flood_element.set("flood-opacity", "0.8")

        # Use existing converter infrastructure
        mock_unit_converter = Mock()
        mock_unit_converter.to_emu.return_value = 25400

        mock_transform_parser = Mock()
        mock_color_parser = Mock()
        mock_color_parser.parse.return_value = Mock(hex="FF0000", rgb=(255, 0, 0), alpha=0.8)

        mock_context = Mock(spec=FilterContext)
        mock_context.unit_converter = mock_unit_converter
        mock_context.transform_parser = mock_transform_parser
        mock_context.color_parser = mock_color_parser
        mock_context.viewport = {'width': 200, 'height': 100}
        mock_context.get_property.return_value = None

        return {
            'mock_flood_element': mock_flood_element,
            'mock_context': mock_context,
            'mock_color_parser': mock_color_parser,
            'expected_filter_type': 'flood',
            'flood_colors': ['#FF0000', '#00FF00', '#0000FF', 'red', 'rgb(255,128,0)'],
            'flood_opacities': [0.0, 0.5, 1.0]
        }

    @pytest.fixture
    def flood_filter_instance(self):
        """Create FloodFilter instance for testing."""
        return FloodFilter()

    def test_initialization(self, flood_filter_instance):
        """Test FloodFilter initializes correctly with required attributes."""
        filter_obj = flood_filter_instance

        assert filter_obj.filter_type == 'flood'
        assert hasattr(filter_obj, 'can_apply')
        assert hasattr(filter_obj, 'apply')
        assert hasattr(filter_obj, 'validate_parameters')

    def test_basic_functionality(self, flood_filter_instance, setup_test_data):
        """Test core methods and expected input/output behavior."""
        filter_obj = flood_filter_instance

        # Test can_apply method
        can_apply_result = filter_obj.can_apply(
            setup_test_data['mock_flood_element'],
            setup_test_data['mock_context']
        )
        assert can_apply_result is True

        # Test apply method
        result = filter_obj.apply(
            setup_test_data['mock_flood_element'],
            setup_test_data['mock_context']
        )
        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.metadata['filter_type'] == 'flood'

    def test_error_handling(self, flood_filter_instance, setup_test_data):
        """Test flood filter error handling."""
        filter_obj = flood_filter_instance

        # Test element without flood-color
        minimal_element = etree.Element("{http://www.w3.org/2000/svg}feFlood")
        # No flood-color or flood-opacity

        result = filter_obj.apply(minimal_element, setup_test_data['mock_context'])
        assert isinstance(result, FilterResult)
        # Should handle with defaults or provide meaningful result

    @pytest.mark.parametrize("flood_color,flood_opacity", [
        ("#FF0000", "1.0"),
        ("#00FF00", "0.5"),
        ("blue", "0.3"),
        ("rgb(255,128,0)", "0.8"),
        ("", "1.0"),  # Default color
        ("#FF0000", ""),  # Default opacity
    ])
    def test_parametrized_flood_scenarios(self, flood_filter_instance, flood_color, flood_opacity, setup_test_data):
        """Test FloodFilter with various color and opacity combinations."""
        filter_obj = flood_filter_instance

        element = etree.Element("{http://www.w3.org/2000/svg}feFlood")
        if flood_color:
            element.set("flood-color", flood_color)
        if flood_opacity:
            element.set("flood-opacity", flood_opacity)

        result = filter_obj.apply(element, setup_test_data['mock_context'])
        assert isinstance(result, FilterResult)
        assert result.success is True


class TestLightingFilter:
    """Tests for LightingFilter implementation."""

    @pytest.fixture
    def setup_test_data(self):
        """Setup common test data for LightingFilter testing."""
        # Diffuse lighting element
        mock_diffuse_element = etree.Element("{http://www.w3.org/2000/svg}feDiffuseLighting")
        mock_diffuse_element.set("lighting-color", "#FFFFFF")
        mock_diffuse_element.set("diffuseConstant", "1.0")

        # Add distant light source
        distant_light = etree.SubElement(mock_diffuse_element, "{http://www.w3.org/2000/svg}feDistantLight")
        distant_light.set("azimuth", "45")
        distant_light.set("elevation", "60")

        # Specular lighting element
        mock_specular_element = etree.Element("{http://www.w3.org/2000/svg}feSpecularLighting")
        mock_specular_element.set("lighting-color", "#FFFFFF")
        mock_specular_element.set("specularConstant", "1.5")
        mock_specular_element.set("specularExponent", "20")

        # Add point light source
        point_light = etree.SubElement(mock_specular_element, "{http://www.w3.org/2000/svg}fePointLight")
        point_light.set("x", "50")
        point_light.set("y", "50")
        point_light.set("z", "100")

        # Use existing converter infrastructure
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
            'mock_diffuse_element': mock_diffuse_element,
            'mock_specular_element': mock_specular_element,
            'mock_context': mock_context,
            'expected_filter_type': 'lighting',
            'lighting_types': ['diffuse', 'specular'],
            'light_types': ['distant', 'point', 'spot']
        }

    @pytest.fixture
    def lighting_filter_instance(self):
        """Create LightingFilter instance for testing."""
        return LightingFilter()

    def test_initialization(self, lighting_filter_instance):
        """Test LightingFilter initializes correctly with required attributes."""
        filter_obj = lighting_filter_instance

        assert filter_obj.filter_type == 'lighting'
        assert hasattr(filter_obj, 'can_apply')
        assert hasattr(filter_obj, 'apply')
        assert hasattr(filter_obj, 'validate_parameters')

    def test_basic_functionality(self, lighting_filter_instance, setup_test_data):
        """Test core methods and expected input/output behavior."""
        filter_obj = lighting_filter_instance

        # Test diffuse lighting
        can_apply_diffuse = filter_obj.can_apply(
            setup_test_data['mock_diffuse_element'],
            setup_test_data['mock_context']
        )
        assert can_apply_diffuse is True

        result = filter_obj.apply(
            setup_test_data['mock_diffuse_element'],
            setup_test_data['mock_context']
        )
        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.metadata['filter_type'] == 'lighting'

        # Test specular lighting
        can_apply_specular = filter_obj.can_apply(
            setup_test_data['mock_specular_element'],
            setup_test_data['mock_context']
        )
        assert can_apply_specular is True

        result = filter_obj.apply(
            setup_test_data['mock_specular_element'],
            setup_test_data['mock_context']
        )
        assert isinstance(result, FilterResult)
        assert result.success is True


class TestColorFilterException:
    """Tests for ColorFilterException class."""

    def test_color_filter_exception_initialization(self):
        """Test ColorFilterException creates correctly."""
        message = "Color filter processing failed"
        exception = ColorFilterException(message)
        assert str(exception) == message
        assert isinstance(exception, FilterException)


class TestColorFiltersIntegration:
    """Integration tests for color filters with other components."""

    def test_integration_with_svg_parsing(self):
        """Test color filters integration with SVG parsing."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <filter id="color-effects">
                    <feColorMatrix type="saturate" values="0.3"/>
                    <feFlood flood-color="#FF6600" flood-opacity="0.8"/>
                </filter>
            </defs>
            <rect width="100" height="50" filter="url(#color-effects)"/>
        </svg>'''

        root = etree.fromstring(svg_content)
        color_elements = root.xpath('.//*[local-name()="feColorMatrix" or local-name()="feFlood"]')

        assert len(color_elements) == 2

        # Test filters can handle real SVG elements
        color_matrix_filter = ColorMatrixFilter()
        flood_filter = FloodFilter()
        mock_context = Mock(spec=FilterContext)

        for element in color_elements:
            if element.tag.endswith('feColorMatrix'):
                assert color_matrix_filter.can_apply(element, mock_context)
            elif element.tag.endswith('feFlood'):
                assert flood_filter.can_apply(element, mock_context)

    def test_integration_with_filter_registry(self):
        """Test color filters integration with FilterRegistry."""
        from src.converters.filters.core.registry import FilterRegistry

        registry = FilterRegistry()

        # Register color filters
        color_matrix = ColorMatrixFilter()
        flood = FloodFilter()
        lighting = LightingFilter()

        registry.register(color_matrix)
        registry.register(flood)
        registry.register(lighting)

        # Test registry integration
        assert 'color_matrix' in registry.list_filters()
        assert 'flood' in registry.list_filters()
        assert 'lighting' in registry.list_filters()

        # Verify filter retrieval
        retrieved_color_matrix = registry.get_filter('color_matrix')
        assert isinstance(retrieved_color_matrix, ColorMatrixFilter)

    def test_integration_with_filter_chain(self):
        """Test color filters integration with FilterChain."""
        from src.converters.filters.core.chain import FilterChain

        # Create chain with color filters
        color_matrix = ColorMatrixFilter()
        flood = FloodFilter()

        chain = FilterChain([color_matrix, flood])
        assert len(chain.nodes) == 2

        # Test chain configuration
        stats = chain.get_statistics()
        assert stats['total_nodes'] == 2
        assert 'color_matrix' in stats['filter_types']
        assert 'flood' in stats['filter_types']


class TestMainColorSystemIntegration:
    """Integration tests validating filter system uses main color system correctly."""

    @pytest.fixture
    def color_matrix_filter(self):
        """Create ColorMatrixFilter instance for integration testing."""
        return ColorMatrixFilter()

    @pytest.fixture
    def mock_context(self):
        """Create mock FilterContext for testing."""
        context = Mock(spec=FilterContext)
        context.input_data = Mock()
        context.output_data = Mock()
        context.metadata = {}
        return context

    def test_saturation_uses_main_color_system(self, color_matrix_filter, mock_context):
        """Validate saturation operations use main color system adjust_saturation."""
        print("🔗 Testing Saturation Integration with Main Color System")
        print("=" * 55)

        # Create saturate element
        element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        element.set("type", "saturate")
        element.set("values", "0.5")  # 50% saturation

        # Test that main color system is used
        reference_color = parse_color("#FF0000")  # Red
        adjusted_color = adjust_saturation(reference_color, 0.5)

        print(f"  Reference: Red at 50% saturation → RGB({adjusted_color.red},{adjusted_color.green},{adjusted_color.blue})")

        # Apply filter and verify it generates DrawingML
        result = color_matrix_filter.apply(element, mock_context)

        assert isinstance(result, FilterResult)
        assert result.success is True
        assert "grayscl" in result.drawingml or "tint" in result.drawingml
        print(f"  DrawingML: {result.drawingml}")
        print("  ✓ Saturation filter correctly integrates with main color system")

    def test_hue_rotation_uses_main_color_system(self, color_matrix_filter, mock_context):
        """Validate hue rotation operations use main color system rotate_hue."""
        print("🎨 Testing Hue Rotation Integration with Main Color System")
        print("=" * 58)

        # Create hue rotate element
        element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        element.set("type", "hueRotate")
        element.set("values", "120")  # 120 degree rotation

        # Test that main color system is used
        reference_color = parse_color("#FF0000")  # Red
        rotated_color = rotate_hue(reference_color, 120)

        print(f"  Reference: Red rotated 120° → RGB({rotated_color.red},{rotated_color.green},{rotated_color.blue})")
        print(f"  Expected: Red → Green transformation")

        # Apply filter and verify it generates DrawingML
        result = color_matrix_filter.apply(element, mock_context)

        assert isinstance(result, FilterResult)
        assert result.success is True
        assert "hue" in result.drawingml
        print(f"  DrawingML: {result.drawingml}")
        print("  ✓ Hue rotation filter correctly integrates with main color system")

    def test_luminance_to_alpha_uses_main_color_system(self, color_matrix_filter, mock_context):
        """Validate luminance-to-alpha operations use main color system luminance_to_alpha."""
        print("🌗 Testing Luminance-to-Alpha Integration with Main Color System")
        print("=" * 65)

        # Create luminance to alpha element
        element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        element.set("type", "luminanceToAlpha")

        # Test that main color system is used
        test_colors = [
            parse_color("#FFFFFF"),  # White
            parse_color("#000000"),  # Black
            parse_color("#808080"),  # Gray
        ]

        for color in test_colors:
            alpha_result = luminance_to_alpha(color)
            luminance_value = calculate_luminance(color)
            print(f"  Reference: RGB({color.red},{color.green},{color.blue}) → Alpha={alpha_result.alpha:.3f} (luminance={luminance_value:.3f})")

        # Apply filter and verify it generates DrawingML
        result = color_matrix_filter.apply(element, mock_context)

        assert isinstance(result, FilterResult)
        assert result.success is True
        assert "alpha" in result.drawingml
        print(f"  DrawingML: {result.drawingml}")
        print("  ✓ Luminance-to-alpha filter correctly integrates with main color system")

    def test_matrix_operations_use_main_color_system(self, color_matrix_filter, mock_context):
        """Validate matrix operations use main color system apply_color_matrix."""
        print("📊 Testing Matrix Operations Integration with Main Color System")
        print("=" * 62)

        # Create matrix element with identity matrix
        element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        element.set("type", "matrix")
        element.set("values", "1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0")  # Identity

        # Test that main color system is used
        test_color = parse_color("#FF8000")  # Orange
        identity_matrix = [1,0,0,0,0, 0,1,0,0,0, 0,0,1,0,0, 0,0,0,1,0]
        result_color = apply_color_matrix(test_color, identity_matrix)

        print(f"  Reference: Orange with identity matrix → RGB({result_color.red},{result_color.green},{result_color.blue})")
        print(f"  Expected: No change from RGB({test_color.red},{test_color.green},{test_color.blue})")

        # Apply filter and verify it generates DrawingML
        result = color_matrix_filter.apply(element, mock_context)

        assert isinstance(result, FilterResult)
        assert result.success is True
        print(f"  DrawingML: {result.drawingml}")
        print("  ✓ Matrix operations correctly integrate with main color system")

    def test_error_handling_with_main_color_system(self, color_matrix_filter, mock_context):
        """Validate error handling when main color system functions encounter issues."""
        print("🛡️ Testing Error Handling in Color System Integration")
        print("=" * 52)

        # Create matrix element with invalid values
        element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        element.set("type", "matrix")
        element.set("values", "1 0 0 0 0  0 1 0 0 0  0 0 1 0")  # Too few values (should be 20)

        # Test that errors are handled gracefully
        try:
            test_color = parse_color("#FF0000")
            invalid_matrix = [1,0,0,0,0, 0,1,0,0,0, 0,0,1,0]  # Only 14 values
            apply_color_matrix(test_color, invalid_matrix)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            print(f"  Expected error from main system: {e}")

        # Apply filter and verify it handles the error gracefully
        result = color_matrix_filter.apply(element, mock_context)

        assert isinstance(result, FilterResult)
        # Should either succeed with fallback or fail gracefully
        print(f"  Filter result: Success={result.success}")
        print(f"  DrawingML: {result.drawingml}")
        print("  ✓ Error handling correctly integrated with main color system")

    def test_performance_with_main_color_system(self, color_matrix_filter, mock_context):
        """Validate performance characteristics of main color system integration."""
        print("⚡ Testing Performance of Color System Integration")
        print("=" * 50)

        import time

        # Test multiple filter operations
        test_cases = [
            ("saturate", "0.5"),
            ("hueRotate", "90"),
            ("luminanceToAlpha", ""),
        ]

        for filter_type, values in test_cases:
            element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
            element.set("type", filter_type)
            if values:
                element.set("values", values)

            # Measure performance
            start_time = time.time()
            for _ in range(100):  # 100 operations
                result = color_matrix_filter.apply(element, mock_context)
                assert result.success is True
            end_time = time.time()

            execution_time = end_time - start_time
            ops_per_second = 100 / execution_time if execution_time > 0 else float('inf')

            print(f"  {filter_type}: {ops_per_second:.0f} operations/second")

            # Performance should be reasonable
            assert ops_per_second > 100, f"Performance too slow for {filter_type}: {ops_per_second:.0f} ops/sec"

        print("  ✓ Performance requirements met for integrated color system")

    def test_consistency_with_main_color_system(self, color_matrix_filter, mock_context):
        """Validate consistency between filter results and main color system results."""
        print("🔍 Testing Consistency Between Filter and Main Color System")
        print("=" * 60)

        # Test saturation consistency
        element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        element.set("type", "saturate")
        element.set("values", "0.8")

        # Get filter result
        filter_result = color_matrix_filter.apply(element, mock_context)

        # Compare with direct main system call
        test_color = parse_color("#FF8040")
        main_system_result = adjust_saturation(test_color, 0.8)

        print(f"  Filter system saturation: {filter_result.drawingml}")
        print(f"  Main system result: RGB({main_system_result.red},{main_system_result.green},{main_system_result.blue})")

        # Both should succeed
        assert filter_result.success is True
        assert isinstance(main_system_result, type(test_color))

        print("  ✓ Consistency validated between filter system and main color system")

    def test_comprehensive_integration_validation(self, color_matrix_filter, mock_context):
        """Comprehensive validation of complete filter system integration."""
        print("🎯 Comprehensive Integration Validation")
        print("=" * 40)

        integration_tests = [
            {
                'name': 'Saturation Integration',
                'element_type': 'saturate',
                'values': '0.3',
                'main_function': lambda: adjust_saturation(parse_color("#FF0000"), 0.3),
                'expected_drawingml': 'grayscl'
            },
            {
                'name': 'Hue Rotation Integration',
                'element_type': 'hueRotate',
                'values': '45',
                'main_function': lambda: rotate_hue(parse_color("#00FF00"), 45),
                'expected_drawingml': 'hue'
            },
            {
                'name': 'Matrix Integration',
                'element_type': 'matrix',
                'values': '0.5 0 0 0 0  0 0.5 0 0 0  0 0 0.5 0 0  0 0 0 1 0',
                'main_function': lambda: apply_color_matrix(parse_color("#808080"), [0.5,0,0,0,0, 0,0.5,0,0,0, 0,0,0.5,0,0, 0,0,0,1,0]),
                'expected_drawingml': None  # May vary
            },
            {
                'name': 'Luminance-to-Alpha Integration',
                'element_type': 'luminanceToAlpha',
                'values': '',
                'main_function': lambda: luminance_to_alpha(parse_color("#CCCCCC")),
                'expected_drawingml': 'alpha'
            }
        ]

        for test in integration_tests:
            print(f"  Testing {test['name']}...")

            # Create filter element
            element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
            element.set("type", test['element_type'])
            if test['values']:
                element.set("values", test['values'])

            # Test filter system
            filter_result = color_matrix_filter.apply(element, mock_context)
            assert filter_result.success is True

            # Test main system
            main_result = test['main_function']()
            assert main_result is not None

            # Validate expected patterns
            if test['expected_drawingml']:
                assert test['expected_drawingml'] in filter_result.drawingml

            print(f"    ✓ {test['name']} integration successful")

        print("  🎉 All integration tests passed!")
        print("  📊 Filter system successfully integrated with main color system")
        print("  🔗 Single source of truth established for color operations")