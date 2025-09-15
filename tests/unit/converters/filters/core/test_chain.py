"""
Tests for SVG filter chain functionality.

This module contains unit tests for the FilterChain class that manages
composable filter operations with pipeline pattern, lazy evaluation,
and memory-efficient streaming.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any, Optional, List, Iterator
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
from src.converters.filters.core.chain import (
    FilterChain,
    FilterChainError,
    FilterChainNode,
    ChainExecutionMode
)


# Mock filter implementations for testing
class MockProcessingFilter(Filter):
    """Mock filter that processes elements successfully."""

    def __init__(self, filter_type: str, output_suffix: str = ""):
        super().__init__(filter_type)
        self.output_suffix = output_suffix
        self.apply_count = 0

    def can_apply(self, element: etree.Element, context: FilterContext) -> bool:
        return True

    def apply(self, element: etree.Element, context: FilterContext) -> FilterResult:
        self.apply_count += 1
        output = f'<{self.filter_type}>{self.output_suffix}</{self.filter_type}>'
        return FilterResult(
            success=True,
            drawingml=output,
            metadata={
                'filter_type': self.filter_type,
                'apply_count': self.apply_count,
                'processed_element': element.tag
            }
        )

    def validate_parameters(self, element: etree.Element, context: FilterContext) -> bool:
        return True


class MockFailingFilter(Filter):
    """Mock filter that fails processing."""

    def __init__(self, failure_mode: str = "apply"):
        super().__init__("failing")
        self.failure_mode = failure_mode

    def can_apply(self, element: etree.Element, context: FilterContext) -> bool:
        if self.failure_mode == "can_apply":
            raise FilterException("can_apply failure")
        return self.failure_mode != "can_apply_false"

    def apply(self, element: etree.Element, context: FilterContext) -> FilterResult:
        if self.failure_mode == "apply":
            return FilterResult(
                success=False,
                error_message="Intentional apply failure",
                metadata={'filter_type': 'failing'}
            )
        elif self.failure_mode == "exception":
            raise FilterException("Intentional exception in apply")
        return FilterResult(success=True, drawingml="<success/>")

    def validate_parameters(self, element: etree.Element, context: FilterContext) -> bool:
        if self.failure_mode == "validate":
            return False
        return True


class MockSlowFilter(Filter):
    """Mock filter that simulates slow processing."""

    def __init__(self, delay: float = 0.1):
        super().__init__("slow")
        self.delay = delay
        self.start_times = []
        self.end_times = []

    def can_apply(self, element: etree.Element, context: FilterContext) -> bool:
        return True

    def apply(self, element: etree.Element, context: FilterContext) -> FilterResult:
        start_time = time.time()
        self.start_times.append(start_time)

        time.sleep(self.delay)

        end_time = time.time()
        self.end_times.append(end_time)

        return FilterResult(
            success=True,
            drawingml=f'<slow delay="{self.delay}"/>',
            metadata={
                'filter_type': 'slow',
                'processing_time': end_time - start_time
            }
        )

    def validate_parameters(self, element: etree.Element, context: FilterContext) -> bool:
        return True


class TestFilterChainNode:
    """Tests for FilterChainNode class."""

    @pytest.fixture
    def setup_test_data(self):
        """Setup common test data for FilterChainNode testing."""
        return {
            'test_filter': MockProcessingFilter('test', 'node_test'),
            'mock_element': etree.Element("{http://www.w3.org/2000/svg}rect"),
            'mock_context': Mock(spec=FilterContext),
            'node_metadata': {'position': 0, 'enabled': True},
        }

    @pytest.fixture
    def chain_node_instance(self, setup_test_data):
        """Create FilterChainNode instance for testing."""
        return FilterChainNode(
            filter_obj=setup_test_data['test_filter'],
            metadata=setup_test_data['node_metadata']
        )

    def test_initialization(self, chain_node_instance, setup_test_data):
        """Test FilterChainNode initializes correctly with required attributes."""
        node = chain_node_instance

        assert node.filter_obj == setup_test_data['test_filter']
        assert node.metadata == setup_test_data['node_metadata']
        assert node.enabled is True
        assert hasattr(node, 'filter_obj')
        assert hasattr(node, 'metadata')
        assert hasattr(node, 'enabled')

    def test_basic_functionality(self, chain_node_instance, setup_test_data):
        """Test core methods and expected input/output behavior."""
        node = chain_node_instance

        # Test that node can execute filter
        result = node.execute(
            setup_test_data['mock_element'],
            setup_test_data['mock_context']
        )

        assert isinstance(result, FilterResult)
        assert result.success is True
        assert 'test' in result.drawingml
        assert result.metadata['filter_type'] == 'test'

    def test_error_handling(self, setup_test_data):
        """Test invalid input handling and error scenarios."""
        # Test node with None filter
        with pytest.raises(FilterValidationError):
            FilterChainNode(filter_obj=None)

        # Test node with non-Filter object
        with pytest.raises(FilterValidationError):
            FilterChainNode(filter_obj="not a filter")

    def test_configuration_options(self, setup_test_data):
        """Test node configuration and customization options."""
        # Test enabled/disabled node
        node = FilterChainNode(
            filter_obj=setup_test_data['test_filter'],
            enabled=False
        )
        assert node.enabled is False

        # Test node with custom metadata
        custom_metadata = {'custom_key': 'custom_value', 'priority': 10}
        node = FilterChainNode(
            filter_obj=setup_test_data['test_filter'],
            metadata=custom_metadata
        )
        assert node.metadata == custom_metadata


class TestFilterChain:
    """Tests for FilterChain class."""

    @pytest.fixture
    def setup_test_data(self):
        """Setup common test data and mock objects."""
        mock_svg_element = etree.Element("{http://www.w3.org/2000/svg}rect")
        mock_svg_element.set("width", "100")
        mock_svg_element.set("height", "50")

        return {
            'mock_svg_element': mock_svg_element,
            'mock_context': Mock(spec=FilterContext),
            'blur_filter': MockProcessingFilter('blur', 'blur_applied'),
            'shadow_filter': MockProcessingFilter('shadow', 'shadow_applied'),
            'color_filter': MockProcessingFilter('color', 'color_applied'),
            'failing_filter': MockFailingFilter('apply'),
            'slow_filter': MockSlowFilter(0.05),
            'filter_list': [],
            'expected_chain_methods': ['add_filter', 'remove_filter', 'apply', 'clear']
        }

    @pytest.fixture
    def filter_chain_instance(self, setup_test_data):
        """Create FilterChain instance for testing."""
        filters = [
            setup_test_data['blur_filter'],
            setup_test_data['shadow_filter']
        ]
        return FilterChain(filters)

    def test_initialization(self, setup_test_data):
        """Test FilterChain initializes correctly with required attributes."""
        # Test empty chain
        empty_chain = FilterChain()
        assert len(empty_chain.nodes) == 0
        assert empty_chain.execution_mode == ChainExecutionMode.SEQUENTIAL
        assert hasattr(empty_chain, 'nodes')
        assert hasattr(empty_chain, 'execution_mode')

        # Test chain with filters
        filters = [setup_test_data['blur_filter'], setup_test_data['shadow_filter']]
        chain = FilterChain(filters)
        assert len(chain.nodes) == 2
        assert all(isinstance(node, FilterChainNode) for node in chain.nodes)

    def test_basic_functionality(self, filter_chain_instance, setup_test_data):
        """Test core methods and expected input/output behavior."""
        chain = filter_chain_instance

        # Test apply method
        result = chain.apply(
            setup_test_data['mock_svg_element'],
            setup_test_data['mock_context']
        )

        assert isinstance(result, FilterResult)
        assert result.success is True

        # Result should contain output from both filters
        drawingml = result.drawingml
        assert 'blur' in drawingml
        assert 'shadow' in drawingml

        # Test that both filters were applied
        assert setup_test_data['blur_filter'].apply_count == 1
        assert setup_test_data['shadow_filter'].apply_count == 1

    def test_error_handling(self, setup_test_data):
        """Test invalid input handling and error scenarios."""
        # Test chain with failing filter
        failing_filter = MockFailingFilter('apply')
        chain = FilterChain([setup_test_data['blur_filter'], failing_filter])

        # By default, chain should continue processing after failures
        result = chain.apply(
            setup_test_data['mock_svg_element'],
            setup_test_data['mock_context']
        )

        # Result might be partial success depending on failure handling strategy
        assert isinstance(result, FilterResult)

        # Test chain with exception-throwing filter
        exception_filter = MockFailingFilter('exception')
        chain_with_exception = FilterChain([exception_filter])

        # Should handle exceptions gracefully
        result = chain_with_exception.apply(
            setup_test_data['mock_svg_element'],
            setup_test_data['mock_context']
        )
        assert isinstance(result, FilterResult)

    def test_edge_cases(self, setup_test_data):
        """Test edge cases and boundary conditions."""
        # Test empty chain
        empty_chain = FilterChain()
        result = empty_chain.apply(
            setup_test_data['mock_svg_element'],
            setup_test_data['mock_context']
        )
        # Empty chain should return successful but empty result
        assert result.success is True
        assert not result.drawingml or result.drawingml == ""

        # Test chain with single filter
        single_chain = FilterChain([setup_test_data['blur_filter']])
        result = single_chain.apply(
            setup_test_data['mock_svg_element'],
            setup_test_data['mock_context']
        )
        assert result.success is True
        assert 'blur' in result.drawingml

    def test_configuration_options(self, setup_test_data):
        """Test chain configuration and customization options."""
        # Test different execution modes
        sequential_chain = FilterChain(
            [setup_test_data['blur_filter'], setup_test_data['shadow_filter']],
            execution_mode=ChainExecutionMode.SEQUENTIAL
        )
        assert sequential_chain.execution_mode == ChainExecutionMode.SEQUENTIAL

        parallel_chain = FilterChain(
            [setup_test_data['blur_filter'], setup_test_data['shadow_filter']],
            execution_mode=ChainExecutionMode.PARALLEL
        )
        assert parallel_chain.execution_mode == ChainExecutionMode.PARALLEL

        # Test failure handling modes
        fail_fast_chain = FilterChain(
            [setup_test_data['blur_filter'], setup_test_data['shadow_filter']],
            fail_fast=True
        )
        assert fail_fast_chain.fail_fast is True

    def test_integration_with_dependencies(self, setup_test_data):
        """Test FilterChain integration with Filter objects and dependencies."""
        chain = FilterChain()

        # Test adding filters dynamically
        chain.add_filter(setup_test_data['blur_filter'])
        chain.add_filter(setup_test_data['shadow_filter'])
        chain.add_filter(setup_test_data['color_filter'])

        assert len(chain.nodes) == 3

        # Test that all filters are accessible and functional
        result = chain.apply(
            setup_test_data['mock_svg_element'],
            setup_test_data['mock_context']
        )

        assert result.success is True
        assert 'blur' in result.drawingml
        assert 'shadow' in result.drawingml
        assert 'color' in result.drawingml

    @pytest.mark.parametrize("execution_mode,expected_behavior", [
        (ChainExecutionMode.SEQUENTIAL, "sequential_processing"),
        (ChainExecutionMode.PARALLEL, "parallel_processing"),
        (ChainExecutionMode.LAZY, "lazy_evaluation"),
    ])
    def test_parametrized_execution_modes(self, setup_test_data, execution_mode, expected_behavior):
        """Test FilterChain with various execution modes."""
        chain = FilterChain(
            [setup_test_data['blur_filter'], setup_test_data['shadow_filter']],
            execution_mode=execution_mode
        )

        result = chain.apply(
            setup_test_data['mock_svg_element'],
            setup_test_data['mock_context']
        )

        # All modes should produce valid results
        assert isinstance(result, FilterResult)
        assert result.success is True

        # Verify execution mode is set correctly
        assert chain.execution_mode == execution_mode

    def test_performance_characteristics(self, setup_test_data):
        """Test chain performance and resource usage characteristics."""
        # Create chain with multiple filters
        filters = [
            MockProcessingFilter(f'filter_{i}', f'output_{i}')
            for i in range(10)
        ]
        chain = FilterChain(filters)

        # Measure processing time
        start_time = time.time()
        result = chain.apply(
            setup_test_data['mock_svg_element'],
            setup_test_data['mock_context']
        )
        processing_time = time.time() - start_time

        # Processing should be reasonably fast
        assert processing_time < 1.0, f"Chain processing took too long: {processing_time}s"
        assert result.success is True

        # Verify all filters were applied
        for i, filter_obj in enumerate(filters):
            assert filter_obj.apply_count == 1, f"Filter {i} was not applied"

    def test_thread_safety(self, setup_test_data):
        """Test thread safety of chain operations."""
        chain = FilterChain([
            setup_test_data['blur_filter'],
            setup_test_data['shadow_filter'],
            setup_test_data['color_filter']
        ])

        results = []
        errors = []
        lock = threading.Lock()

        def apply_chain():
            try:
                result = chain.apply(
                    setup_test_data['mock_svg_element'],
                    setup_test_data['mock_context']
                )
                with lock:
                    results.append(result)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=apply_chain)
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
            assert isinstance(result.drawingml, str)

    def test_lazy_evaluation(self, setup_test_data):
        """Test lazy evaluation functionality."""
        # Create chain with lazy evaluation
        chain = FilterChain(
            [setup_test_data['blur_filter'], setup_test_data['shadow_filter']],
            execution_mode=ChainExecutionMode.LAZY
        )

        # Apply filters lazily
        result_iterator = chain.apply_lazy(
            setup_test_data['mock_svg_element'],
            setup_test_data['mock_context']
        )

        # Verify iterator interface
        assert hasattr(result_iterator, '__iter__')
        assert hasattr(result_iterator, '__next__')

        # Collect results from iterator
        results = list(result_iterator)
        assert len(results) == 2

        # Verify each result
        for result in results:
            assert isinstance(result, FilterResult)
            assert result.success is True

    def test_memory_efficient_streaming(self, setup_test_data):
        """Test memory-efficient streaming of filter results."""
        # Create chain with many filters for memory testing
        filters = [MockProcessingFilter(f'stream_{i}') for i in range(20)]
        chain = FilterChain(filters, execution_mode=ChainExecutionMode.STREAMING)

        # Test streaming interface
        result_stream = chain.apply_stream(
            setup_test_data['mock_svg_element'],
            setup_test_data['mock_context']
        )

        # Process results one at a time (memory efficient)
        processed_count = 0
        for result in result_stream:
            assert isinstance(result, FilterResult)
            processed_count += 1

            # In streaming mode, we don't accumulate all results in memory
            # This test verifies the streaming interface works

        assert processed_count == len(filters)

    def test_filter_composition(self, setup_test_data):
        """Test composable filter operations and chaining."""
        # Create multiple chains
        blur_chain = FilterChain([setup_test_data['blur_filter']])
        effect_chain = FilterChain([setup_test_data['shadow_filter'], setup_test_data['color_filter']])

        # Test chain composition
        composed_chain = FilterChain()
        composed_chain.extend(blur_chain)
        composed_chain.extend(effect_chain)

        assert len(composed_chain.nodes) == 3

        # Test composed chain execution
        result = composed_chain.apply(
            setup_test_data['mock_svg_element'],
            setup_test_data['mock_context']
        )

        assert result.success is True
        assert 'blur' in result.drawingml
        assert 'shadow' in result.drawingml
        assert 'color' in result.drawingml

    def test_error_propagation(self, setup_test_data):
        """Test error handling and propagation in filter chains."""
        # Test fail-fast mode
        fail_fast_chain = FilterChain([
            setup_test_data['blur_filter'],
            MockFailingFilter('apply'),
            setup_test_data['shadow_filter']  # Should not be reached
        ], fail_fast=True)

        result = fail_fast_chain.apply(
            setup_test_data['mock_svg_element'],
            setup_test_data['mock_context']
        )

        # In fail-fast mode, processing should stop at first failure
        assert setup_test_data['blur_filter'].apply_count == 1  # First filter applied
        assert setup_test_data['shadow_filter'].apply_count == 0  # Third filter not reached

        # Test continue-on-error mode
        continue_chain = FilterChain([
            setup_test_data['blur_filter'],
            MockFailingFilter('apply'),
            setup_test_data['shadow_filter']
        ], fail_fast=False)

        # Reset apply counts
        setup_test_data['blur_filter'].apply_count = 0
        setup_test_data['shadow_filter'].apply_count = 0

        result = continue_chain.apply(
            setup_test_data['mock_svg_element'],
            setup_test_data['mock_context']
        )

        # In continue mode, all filters should be attempted
        assert setup_test_data['blur_filter'].apply_count == 1
        assert setup_test_data['shadow_filter'].apply_count == 1


class TestChainExecutionMode:
    """Tests for ChainExecutionMode enum."""

    def test_execution_mode_values(self):
        """Test that execution mode enum has expected values."""
        assert ChainExecutionMode.SEQUENTIAL.value == "sequential"
        assert ChainExecutionMode.PARALLEL.value == "parallel"
        assert ChainExecutionMode.LAZY.value == "lazy"
        assert ChainExecutionMode.STREAMING.value == "streaming"

    def test_execution_mode_comparison(self):
        """Test execution mode comparison and equality."""
        assert ChainExecutionMode.SEQUENTIAL == ChainExecutionMode.SEQUENTIAL
        assert ChainExecutionMode.SEQUENTIAL != ChainExecutionMode.PARALLEL


class TestFilterChainError:
    """Tests for FilterChainError exception."""

    def test_filter_chain_error_initialization(self):
        """Test FilterChainError creates correctly."""
        message = "Chain execution failed"
        exception = FilterChainError(message)
        assert str(exception) == message
        assert isinstance(exception, FilterException)


class TestFilterChainHelperFunctions:
    """Tests for helper functions in the chain module."""

    def test_chain_optimization(self):
        """Test chain optimization helper functions."""
        # This will be implemented when optimization functions are added
        pass

    def test_result_merging(self):
        """Test filter result merging helper functions."""
        # This will be implemented when result merging functions are added
        pass


class TestFilterChainIntegration:
    """Integration tests for FilterChain with other components."""

    @pytest.fixture
    def integration_setup(self):
        """Setup for integration testing."""
        return {
            'svg_content': '''<svg xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <filter id="complex-filter">
                        <feGaussianBlur stdDeviation="2"/>
                        <feDropShadow dx="2" dy="2"/>
                        <feColorMatrix values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 1 0"/>
                    </filter>
                </defs>
                <rect width="100" height="50" filter="url(#complex-filter)"/>
            </svg>''',
            'mock_context': Mock(spec=FilterContext)
        }

    def test_integration_with_svg_parsing(self, integration_setup):
        """Test FilterChain integration with SVG parsing and real elements."""
        # Parse SVG content
        root = etree.fromstring(integration_setup['svg_content'])
        filter_elements = root.xpath('.//*[local-name()="filter"]/*')

        # Create chain that matches the SVG filter definition
        chain = FilterChain([
            MockProcessingFilter('blur'),
            MockProcessingFilter('shadow'),
            MockProcessingFilter('color')
        ])

        # Test that chain can process real SVG structure
        assert len(filter_elements) == 3  # Three filter primitives in SVG

        # Apply chain to each filter element
        for element in filter_elements:
            result = chain.apply(element, integration_setup['mock_context'])
            assert isinstance(result, FilterResult)
            assert result.success is True

    def test_integration_with_registry(self):
        """Test FilterChain integration with FilterRegistry."""
        # This test demonstrates integration with the registry system
        from src.converters.filters.core.registry import FilterRegistry

        registry = FilterRegistry()
        registry.register(MockProcessingFilter('blur'))
        registry.register(MockProcessingFilter('shadow'))

        # Create chain from registry filters
        filters = [registry.get_filter('blur'), registry.get_filter('shadow')]
        chain = FilterChain(filters)

        # Test that chain works with registry-managed filters
        assert len(chain.nodes) == 2

        mock_element = etree.Element("{http://www.w3.org/2000/svg}rect")
        mock_context = Mock(spec=FilterContext)

        result = chain.apply(mock_element, mock_context)
        assert result.success is True