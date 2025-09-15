"""
Integration tests for filter system components.

This module contains integration tests for the complete filter system,
testing the interaction between FilterRegistry, FilterChain, and
individual filter implementations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional, List
from lxml import etree

from src.converters.filters.core.base import Filter, FilterContext, FilterResult
from src.converters.filters.core.registry import FilterRegistry
from src.converters.filters.core.chain import FilterChain, ChainExecutionMode
from src.converters.filters.image.blur import GaussianBlurFilter, MotionBlurFilter
from src.converters.filters.image.color import ColorMatrixFilter, FloodFilter, LightingFilter


class TestImageFiltersRegistration:
    """Tests for image filters registration with FilterRegistry."""

    @pytest.fixture
    def setup_registry_with_image_filters(self):
        """Setup FilterRegistry with all image filters registered."""
        registry = FilterRegistry()

        # Register blur filters
        gaussian_blur = GaussianBlurFilter()
        motion_blur = MotionBlurFilter()
        registry.register(gaussian_blur)
        registry.register(motion_blur)

        # Register color filters
        color_matrix = ColorMatrixFilter()
        flood = FloodFilter()
        lighting = LightingFilter()
        registry.register(color_matrix)
        registry.register(flood)
        registry.register(lighting)

        return {
            'registry': registry,
            'gaussian_blur': gaussian_blur,
            'motion_blur': motion_blur,
            'color_matrix': color_matrix,
            'flood': flood,
            'lighting': lighting,
            'expected_filter_count': 5
        }

    @pytest.fixture
    def mock_context(self):
        """Create mock FilterContext with proper dependencies."""
        mock_unit_converter = Mock()
        mock_unit_converter.to_emu.return_value = 50000
        mock_unit_converter.to_px.return_value = 2.0

        mock_transform_parser = Mock()
        mock_color_parser = Mock()
        mock_color_parser.parse.return_value = Mock(hex="FF0000", rgb=(255, 0, 0), alpha=1.0)

        mock_context = Mock(spec=FilterContext)
        mock_context.unit_converter = mock_unit_converter
        mock_context.transform_parser = mock_transform_parser
        mock_context.color_parser = mock_color_parser
        mock_context.viewport = {'width': 200, 'height': 100}
        mock_context.get_property.return_value = None

        return mock_context

    def test_all_image_filters_registered(self, setup_registry_with_image_filters):
        """Test that all image filters are properly registered."""
        registry_data = setup_registry_with_image_filters
        registry = registry_data['registry']

        # Check filter count
        filter_types = registry.list_filters()
        assert len(filter_types) == registry_data['expected_filter_count']

        # Check specific filter types
        assert 'gaussian_blur' in filter_types
        assert 'motion_blur' in filter_types
        assert 'color_matrix' in filter_types
        assert 'flood' in filter_types
        assert 'lighting' in filter_types

    def test_filter_retrieval_by_type(self, setup_registry_with_image_filters):
        """Test retrieving filters by their type identifiers."""
        registry_data = setup_registry_with_image_filters
        registry = registry_data['registry']

        # Test gaussian blur filter
        gaussian_filter = registry.get_filter('gaussian_blur')
        assert isinstance(gaussian_filter, GaussianBlurFilter)
        assert gaussian_filter.filter_type == 'gaussian_blur'

        # Test color matrix filter
        color_filter = registry.get_filter('color_matrix')
        assert isinstance(color_filter, ColorMatrixFilter)
        assert color_filter.filter_type == 'color_matrix'

        # Test flood filter
        flood_filter = registry.get_filter('flood')
        assert isinstance(flood_filter, FloodFilter)
        assert flood_filter.filter_type == 'flood'

    def test_filter_discovery_for_svg_elements(self, setup_registry_with_image_filters, mock_context):
        """Test filter discovery for different SVG elements."""
        registry_data = setup_registry_with_image_filters
        registry = registry_data['registry']

        # Test feGaussianBlur element
        blur_element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
        blur_element.set("stdDeviation", "2.0")

        found_filter = registry.find_filter_for_element(blur_element, mock_context)
        assert found_filter is not None
        assert isinstance(found_filter, GaussianBlurFilter)

        # Test feColorMatrix element
        color_element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        color_element.set("type", "saturate")
        color_element.set("values", "0.5")

        found_filter = registry.find_filter_for_element(color_element, mock_context)
        assert found_filter is not None
        assert isinstance(found_filter, ColorMatrixFilter)

        # Test feFlood element
        flood_element = etree.Element("{http://www.w3.org/2000/svg}feFlood")
        flood_element.set("flood-color", "#FF0000")

        found_filter = registry.find_filter_for_element(flood_element, mock_context)
        assert found_filter is not None
        assert isinstance(found_filter, FloodFilter)

    def test_registry_statistics(self, setup_registry_with_image_filters):
        """Test registry statistics and information."""
        registry_data = setup_registry_with_image_filters
        registry = registry_data['registry']

        stats = registry.get_statistics()

        assert stats['total_filters'] == registry_data['expected_filter_count']
        assert len(stats['filter_types']) == registry_data['expected_filter_count']
        assert stats['element_mappings'] > 0  # Should have element mappings

    def test_registry_thread_safety(self, setup_registry_with_image_filters, mock_context):
        """Test thread safety of registry operations with image filters."""
        import threading
        import time

        registry_data = setup_registry_with_image_filters
        registry = registry_data['registry']

        results = []
        errors = []
        lock = threading.Lock()

        def test_registry_operations():
            try:
                # Test filter retrieval
                gaussian_filter = registry.get_filter('gaussian_blur')

                # Test element-based discovery
                element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
                element.set("stdDeviation", "1.5")

                found_filter = registry.find_filter_for_element(element, mock_context)

                with lock:
                    results.append({
                        'retrieved_filter': isinstance(gaussian_filter, GaussianBlurFilter),
                        'found_filter': isinstance(found_filter, GaussianBlurFilter)
                    })

            except Exception as e:
                with lock:
                    errors.append(str(e))

        # Create and run threads
        threads = [threading.Thread(target=test_registry_operations) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify results
        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(results) == 5
        for result in results:
            assert result['retrieved_filter'] is True
            assert result['found_filter'] is True


class TestFilterChainIntegration:
    """Tests for FilterChain integration with image filters."""

    @pytest.fixture
    def setup_filter_chain(self):
        """Setup FilterChain with image filters."""
        gaussian_blur = GaussianBlurFilter()
        color_matrix = ColorMatrixFilter()
        flood = FloodFilter()

        chain = FilterChain([gaussian_blur, color_matrix, flood])

        return {
            'chain': chain,
            'gaussian_blur': gaussian_blur,
            'color_matrix': color_matrix,
            'flood': flood
        }

    @pytest.fixture
    def mock_context(self):
        """Create mock FilterContext with proper dependencies."""
        mock_unit_converter = Mock()
        mock_unit_converter.to_emu.return_value = 50000
        mock_transform_parser = Mock()
        mock_color_parser = Mock()
        mock_color_parser.parse.return_value = Mock(hex="0000FF", rgb=(0, 0, 255), alpha=0.8)

        mock_context = Mock(spec=FilterContext)
        mock_context.unit_converter = mock_unit_converter
        mock_context.transform_parser = mock_transform_parser
        mock_context.color_parser = mock_color_parser
        mock_context.viewport = {'width': 300, 'height': 150}

        return mock_context

    def test_chain_with_multiple_image_filters(self, setup_filter_chain, mock_context):
        """Test FilterChain execution with multiple image filters."""
        chain_data = setup_filter_chain
        chain = chain_data['chain']

        # Create test element (will be processed by first applicable filter)
        test_element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
        test_element.set("stdDeviation", "3.0")

        # Execute chain
        result = chain.apply(test_element, mock_context)

        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.drawingml is not None
        assert result.metadata['chain_length'] == 3

    def test_chain_sequential_execution_mode(self, setup_filter_chain, mock_context):
        """Test chain with sequential execution mode."""
        chain_data = setup_filter_chain
        chain = chain_data['chain']
        chain.execution_mode = ChainExecutionMode.SEQUENTIAL

        test_element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        test_element.set("type", "saturate")
        test_element.set("values", "0.8")

        result = chain.apply(test_element, mock_context)

        assert result.success is True
        assert result.metadata['execution_mode'] == 'sequential'

    def test_chain_parallel_execution_mode(self, setup_filter_chain, mock_context):
        """Test chain with parallel execution mode."""
        chain_data = setup_filter_chain
        chain = chain_data['chain']
        chain.execution_mode = ChainExecutionMode.PARALLEL

        test_element = etree.Element("{http://www.w3.org/2000/svg}feFlood")
        test_element.set("flood-color", "#00FF00")

        result = chain.apply(test_element, mock_context)

        assert result.success is True
        assert result.metadata['execution_mode'] == 'parallel'

    def test_chain_lazy_execution_mode(self, setup_filter_chain, mock_context):
        """Test chain with lazy execution mode."""
        chain_data = setup_filter_chain
        chain = chain_data['chain']

        test_element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
        test_element.set("stdDeviation", "1.0")

        # Test lazy evaluation
        results = list(chain.apply_lazy(test_element, mock_context))

        assert len(results) >= 1  # At least one filter should apply
        for result in results:
            assert isinstance(result, FilterResult)

    def test_chain_performance_with_image_filters(self, setup_filter_chain, mock_context):
        """Test chain performance characteristics with image filters."""
        import time

        chain_data = setup_filter_chain
        chain = chain_data['chain']

        # Create multiple test elements
        test_elements = []
        for i in range(10):
            element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
            element.set("stdDeviation", str(i + 1))
            test_elements.append(element)

        # Measure processing time
        start_time = time.time()
        for element in test_elements:
            result = chain.apply(element, mock_context)
            assert result.success is True

        processing_time = time.time() - start_time

        # Should process reasonably fast
        assert processing_time < 2.0, f"Processing took too long: {processing_time}s"


class TestCompleteSystemIntegration:
    """Tests for complete filter system integration."""

    @pytest.fixture
    def complete_system_setup(self):
        """Setup complete filter system with registry and chain."""
        # Create registry with all filters
        registry = FilterRegistry()

        # Register image filters
        image_filters = [
            GaussianBlurFilter(),
            MotionBlurFilter(),
            ColorMatrixFilter(),
            FloodFilter(),
            LightingFilter()
        ]

        for filter_obj in image_filters:
            registry.register(filter_obj)

        # Create chain from registry filters
        blur_filter = registry.get_filter('gaussian_blur')
        color_filter = registry.get_filter('color_matrix')
        flood_filter = registry.get_filter('flood')

        chain = FilterChain([blur_filter, color_filter, flood_filter])

        return {
            'registry': registry,
            'chain': chain,
            'image_filters': image_filters
        }

    @pytest.fixture
    def mock_context(self):
        """Create comprehensive mock FilterContext."""
        mock_unit_converter = Mock()
        mock_unit_converter.to_emu.return_value = 63500  # 2.5px
        mock_unit_converter.to_px.return_value = 2.5

        mock_transform_parser = Mock()

        mock_color_parser = Mock()
        mock_color_parser.parse.return_value = Mock(hex="FF6600", rgb=(255, 102, 0), alpha=0.9)

        mock_context = Mock(spec=FilterContext)
        mock_context.unit_converter = mock_unit_converter
        mock_context.transform_parser = mock_transform_parser
        mock_context.color_parser = mock_color_parser
        mock_context.viewport = {'width': 400, 'height': 200}
        mock_context.get_property.return_value = None
        mock_context.cache = {}

        return mock_context

    def test_complete_svg_processing_workflow(self, complete_system_setup, mock_context):
        """Test complete SVG filter processing workflow."""
        system = complete_system_setup
        registry = system['registry']
        chain = system['chain']

        # Create complex SVG with multiple filters
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <filter id="complex-filter">
                    <feGaussianBlur stdDeviation="2.5" result="blur"/>
                    <feColorMatrix type="saturate" values="0.8" in="blur" result="saturated"/>
                    <feFlood flood-color="#FF6600" flood-opacity="0.7" result="flood"/>
                </filter>
            </defs>
            <rect width="100" height="50" filter="url(#complex-filter)"/>
        </svg>'''

        # Parse SVG
        root = etree.fromstring(svg_content)
        filter_elements = root.xpath('.//*[local-name()="feGaussianBlur" or '
                                   'local-name()="feColorMatrix" or '
                                   'local-name()="feFlood"]')

        assert len(filter_elements) == 3

        # Process each filter element through registry
        for element in filter_elements:
            # Find appropriate filter
            filter_obj = registry.find_filter_for_element(element, mock_context)
            assert filter_obj is not None

            # Apply filter
            result = filter_obj.apply(element, mock_context)
            assert result.success is True
            assert result.drawingml is not None

    def test_filter_fallback_and_error_handling(self, complete_system_setup, mock_context):
        """Test filter system fallback and error handling."""
        system = complete_system_setup
        registry = system['registry']

        # Test unknown element
        unknown_element = etree.Element("{http://www.w3.org/2000/svg}feUnknown")
        unknown_element.set("someAttribute", "value")

        found_filter = registry.find_filter_for_element(unknown_element, mock_context)
        assert found_filter is None  # Should not find a filter

        # Test malformed element
        malformed_element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
        malformed_element.set("stdDeviation", "invalid_value")

        blur_filter = registry.find_filter_for_element(malformed_element, mock_context)
        assert blur_filter is not None

        # Filter should handle malformed input gracefully
        result = blur_filter.apply(malformed_element, mock_context)
        assert isinstance(result, FilterResult)
        # Result might be success with defaults or failure with error message

    def test_system_performance_characteristics(self, complete_system_setup, mock_context):
        """Test overall system performance with realistic workload."""
        import time

        system = complete_system_setup
        registry = system['registry']
        chain = system['chain']

        # Create varied test elements
        test_elements = [
            # Gaussian blur elements
            *[self._create_blur_element(f"{i + 1}.0") for i in range(5)],
            # Color matrix elements
            *[self._create_saturate_element(f"{(i + 1) * 0.2}") for i in range(5)],
            # Flood elements
            *[self._create_flood_element(f"#{hex(i * 40)[2:].zfill(2)}0000") for i in range(5)]
        ]

        # Test registry performance
        start_time = time.time()
        for element in test_elements:
            filter_obj = registry.find_filter_for_element(element, mock_context)
            if filter_obj:
                result = filter_obj.apply(element, mock_context)

        registry_time = time.time() - start_time

        # Test chain performance
        start_time = time.time()
        for element in test_elements[:5]:  # Test subset with chain
            result = chain.apply(element, mock_context)

        chain_time = time.time() - start_time

        # Performance assertions
        assert registry_time < 2.0, f"Registry processing too slow: {registry_time}s"
        assert chain_time < 1.0, f"Chain processing too slow: {chain_time}s"

    def test_memory_usage_and_cleanup(self, complete_system_setup, mock_context):
        """Test memory usage and proper cleanup."""
        system = complete_system_setup
        registry = system['registry']

        # Test that filters don't accumulate state
        initial_filter_vars = {}
        for filter_type in registry.list_filters():
            filter_obj = registry.get_filter(filter_type)
            initial_filter_vars[filter_type] = len(vars(filter_obj))

        # Process multiple elements
        for i in range(20):
            element = self._create_blur_element(f"{i + 1}.0")
            filter_obj = registry.find_filter_for_element(element, mock_context)
            if filter_obj:
                filter_obj.apply(element, mock_context)

        # Check that filters didn't accumulate state
        for filter_type in registry.list_filters():
            filter_obj = registry.get_filter(filter_type)
            final_vars = len(vars(filter_obj))
            assert final_vars == initial_filter_vars[filter_type], \
                f"Filter {filter_type} accumulated state: {initial_filter_vars[filter_type]} -> {final_vars}"

    # Helper methods for creating test elements
    def _create_blur_element(self, std_deviation: str) -> etree.Element:
        """Create feGaussianBlur test element."""
        element = etree.Element("{http://www.w3.org/2000/svg}feGaussianBlur")
        element.set("stdDeviation", std_deviation)
        return element

    def _create_saturate_element(self, saturation: str) -> etree.Element:
        """Create feColorMatrix saturate test element."""
        element = etree.Element("{http://www.w3.org/2000/svg}feColorMatrix")
        element.set("type", "saturate")
        element.set("values", saturation)
        return element

    def _create_flood_element(self, color: str) -> etree.Element:
        """Create feFlood test element."""
        element = etree.Element("{http://www.w3.org/2000/svg}feFlood")
        element.set("flood-color", color)
        return element


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing code."""

    def test_filter_package_imports(self):
        """Test that all filters can be imported from main package."""
        # Test individual imports
        from src.converters.filters.image import GaussianBlurFilter
        from src.converters.filters.image import ColorMatrixFilter
        from src.converters.filters.image import FloodFilter

        # Verify filter types
        gaussian_blur = GaussianBlurFilter()
        assert gaussian_blur.filter_type == 'gaussian_blur'

        color_matrix = ColorMatrixFilter()
        assert color_matrix.filter_type == 'color_matrix'

        flood = FloodFilter()
        assert flood.filter_type == 'flood'

    def test_main_package_imports(self):
        """Test imports from main filters package."""
        from src.converters.filters import FilterRegistry, FilterChain

        # Test that core classes are available
        registry = FilterRegistry()
        assert isinstance(registry, FilterRegistry)

        chain = FilterChain()
        assert isinstance(chain, FilterChain)

    def test_default_registry_functionality(self):
        """Test default registry functionality."""
        from src.converters.filters import get_default_registry

        # Get default registry
        default_registry = get_default_registry()
        assert isinstance(default_registry, FilterRegistry)

        # Should be same instance on subsequent calls
        second_call = get_default_registry()
        assert default_registry is second_call