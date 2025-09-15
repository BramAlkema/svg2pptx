"""
Filter chain for composable filter operations.

This module provides the FilterChain class that manages pipeline pattern
processing with lazy evaluation, memory-efficient streaming, and various
execution modes for optimal performance and flexibility.
"""

from enum import Enum
from typing import List, Iterator, Optional, Union, Any, Dict
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from lxml import etree

from .base import Filter, FilterContext, FilterResult, FilterException, FilterValidationError

logger = logging.getLogger(__name__)


class ChainExecutionMode(Enum):
    """Enumeration of chain execution modes."""
    SEQUENTIAL = "sequential"  # Process filters one after another
    PARALLEL = "parallel"      # Process compatible filters in parallel
    LAZY = "lazy"             # Lazy evaluation with iterator interface
    STREAMING = "streaming"    # Memory-efficient streaming processing


class FilterChainError(FilterException):
    """Exception raised when filter chain execution fails."""
    pass


@dataclass
class FilterChainNode:
    """
    Node in a filter processing chain.

    This class wraps a filter instance with additional metadata and
    configuration options for chain processing.

    Attributes:
        filter_obj: The filter instance to execute
        metadata: Additional metadata for the node
        enabled: Whether this node is enabled for processing
    """
    filter_obj: Filter
    metadata: Optional[Dict[str, Any]] = None
    enabled: bool = True

    def __post_init__(self):
        """Validate node configuration after creation."""
        if self.filter_obj is None:
            raise FilterValidationError("FilterChainNode requires a valid filter object")

        if not isinstance(self.filter_obj, Filter):
            raise FilterValidationError(
                f"FilterChainNode filter_obj must be a Filter instance, got {type(self.filter_obj)}"
            )

        if self.metadata is None:
            self.metadata = {}

    def execute(self, element: etree.Element, context: FilterContext) -> FilterResult:
        """
        Execute this node's filter on the given element.

        Args:
            element: SVG element to process
            context: Filter processing context

        Returns:
            FilterResult from the filter execution
        """
        if not self.enabled:
            return FilterResult(
                success=True,
                drawingml="",
                metadata={'skipped': True, 'filter_type': self.filter_obj.filter_type}
            )

        return self.filter_obj.apply(element, context)


class FilterChain:
    """
    Chain of filter operations for composable processing.

    This class implements the pipeline pattern for filter processing, supporting
    various execution modes including sequential, parallel, lazy evaluation,
    and memory-efficient streaming. It provides robust error handling and
    performance optimization options.

    Attributes:
        nodes: List of FilterChainNode objects in the chain
        execution_mode: Mode for executing the filter chain
        fail_fast: Whether to stop on first error or continue processing
        max_workers: Maximum number of worker threads for parallel execution

    Example:
        >>> chain = FilterChain([blur_filter, shadow_filter])
        >>> result = chain.apply(svg_element, context)
        >>>
        >>> # Lazy evaluation
        >>> lazy_chain = FilterChain(filters, execution_mode=ChainExecutionMode.LAZY)
        >>> for result in lazy_chain.apply_lazy(element, context):
        ...     process_result(result)
        >>>
        >>> # Streaming processing
        >>> stream_chain = FilterChain(filters, execution_mode=ChainExecutionMode.STREAMING)
        >>> for result in stream_chain.apply_stream(element, context):
        ...     yield result
    """

    def __init__(
        self,
        filters: Optional[List[Filter]] = None,
        execution_mode: ChainExecutionMode = ChainExecutionMode.SEQUENTIAL,
        fail_fast: bool = False,
        max_workers: int = 4
    ):
        """
        Initialize the filter chain.

        Args:
            filters: List of filters to include in the chain
            execution_mode: Mode for executing the chain
            fail_fast: Whether to stop processing on first error
            max_workers: Maximum worker threads for parallel execution
        """
        self.nodes: List[FilterChainNode] = []
        self.execution_mode = execution_mode
        self.fail_fast = fail_fast
        self.max_workers = max_workers
        self.lock = threading.RLock()

        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")

        # Add initial filters if provided
        if filters:
            for filter_obj in filters:
                self.add_filter(filter_obj)

    def add_filter(self, filter_obj: Filter, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a filter to the end of the chain.

        Args:
            filter_obj: Filter to add to the chain
            metadata: Optional metadata for the filter node
        """
        with self.lock:
            node = FilterChainNode(filter_obj=filter_obj, metadata=metadata)
            self.nodes.append(node)
            self.logger.debug(f"Added filter to chain: {filter_obj.filter_type}")

    def remove_filter(self, filter_type: str) -> bool:
        """
        Remove the first filter of the specified type from the chain.

        Args:
            filter_type: Type identifier of the filter to remove

        Returns:
            True if a filter was removed, False otherwise
        """
        with self.lock:
            for i, node in enumerate(self.nodes):
                if node.filter_obj.filter_type == filter_type:
                    removed_node = self.nodes.pop(i)
                    self.logger.debug(f"Removed filter from chain: {filter_type}")
                    return True
            return False

    def clear(self) -> None:
        """Remove all filters from the chain."""
        with self.lock:
            self.nodes.clear()
            self.logger.debug("Cleared all filters from chain")

    def extend(self, other_chain: 'FilterChain') -> None:
        """
        Extend this chain with filters from another chain.

        Args:
            other_chain: FilterChain to extend this chain with
        """
        with self.lock:
            for node in other_chain.nodes:
                # Create new node to avoid shared references
                new_node = FilterChainNode(
                    filter_obj=node.filter_obj,
                    metadata=node.metadata.copy() if node.metadata else None,
                    enabled=node.enabled
                )
                self.nodes.append(new_node)

    def apply(self, element: etree.Element, context: FilterContext) -> FilterResult:
        """
        Apply all filters in the chain to the given element.

        Args:
            element: SVG element to process
            context: Filter processing context

        Returns:
            FilterResult containing the combined output of all filters
        """
        if not self.nodes:
            return FilterResult(
                success=True,
                drawingml="",
                metadata={'empty_chain': True}
            )

        if self.execution_mode == ChainExecutionMode.SEQUENTIAL:
            return self._apply_sequential(element, context)
        elif self.execution_mode == ChainExecutionMode.PARALLEL:
            return self._apply_parallel(element, context)
        elif self.execution_mode == ChainExecutionMode.LAZY:
            # For lazy mode, collect all results since apply() expects a single result
            results = list(self.apply_lazy(element, context))
            return self._merge_results(results)
        elif self.execution_mode == ChainExecutionMode.STREAMING:
            # For streaming mode, collect all results since apply() expects a single result
            results = list(self.apply_stream(element, context))
            return self._merge_results(results)
        else:
            raise FilterChainError(f"Unsupported execution mode: {self.execution_mode}")

    def apply_lazy(self, element: etree.Element, context: FilterContext) -> Iterator[FilterResult]:
        """
        Apply filters lazily using iterator interface.

        This method yields results one at a time as filters are processed,
        allowing for memory-efficient processing of large filter chains.

        Args:
            element: SVG element to process
            context: Filter processing context

        Yields:
            FilterResult from each filter in the chain
        """
        for node in self.nodes:
            if not node.enabled:
                continue

            try:
                result = node.execute(element, context)
                yield result

                # Handle fail-fast mode
                if self.fail_fast and not result.success:
                    self.logger.warning(f"Chain stopped due to failure in {node.filter_obj.filter_type}")
                    break

            except Exception as e:
                error_result = FilterResult(
                    success=False,
                    error_message=f"Exception in {node.filter_obj.filter_type}: {str(e)}",
                    metadata={'filter_type': node.filter_obj.filter_type, 'exception': str(e)}
                )
                yield error_result

                if self.fail_fast:
                    self.logger.warning(f"Chain stopped due to exception in {node.filter_obj.filter_type}: {e}")
                    break

    def apply_stream(self, element: etree.Element, context: FilterContext) -> Iterator[FilterResult]:
        """
        Apply filters using memory-efficient streaming.

        This method processes filters in a streaming fashion, yielding results
        as they become available while maintaining minimal memory footprint.

        Args:
            element: SVG element to process
            context: Filter processing context

        Yields:
            FilterResult from each filter as it's processed
        """
        # Streaming implementation is similar to lazy evaluation
        # but optimized for memory efficiency and can include
        # additional optimizations like result buffering, etc.
        yield from self.apply_lazy(element, context)

    def _apply_sequential(self, element: etree.Element, context: FilterContext) -> FilterResult:
        """
        Apply filters sequentially in chain order.

        Args:
            element: SVG element to process
            context: Filter processing context

        Returns:
            FilterResult containing combined output
        """
        results = []
        successful_results = []
        failed_results = []

        for node in self.nodes:
            if not node.enabled:
                continue

            try:
                result = node.execute(element, context)
                results.append(result)

                if result.success:
                    successful_results.append(result)
                else:
                    failed_results.append(result)
                    if self.fail_fast:
                        self.logger.warning(f"Sequential chain stopped at {node.filter_obj.filter_type}")
                        break

            except Exception as e:
                error_result = FilterResult(
                    success=False,
                    error_message=f"Exception in {node.filter_obj.filter_type}: {str(e)}",
                    metadata={'filter_type': node.filter_obj.filter_type, 'exception': str(e)}
                )
                results.append(error_result)
                failed_results.append(error_result)

                if self.fail_fast:
                    self.logger.warning(f"Sequential chain stopped due to exception in {node.filter_obj.filter_type}: {e}")
                    break

        return self._merge_results(results)

    def _apply_parallel(self, element: etree.Element, context: FilterContext) -> FilterResult:
        """
        Apply filters in parallel where possible.

        Args:
            element: SVG element to process
            context: Filter processing context

        Returns:
            FilterResult containing combined output
        """
        if not self.nodes:
            return FilterResult(success=True, drawingml="", metadata={'empty_chain': True})

        results = []

        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all filter tasks
            future_to_node = {}
            for node in self.nodes:
                if node.enabled:
                    future = executor.submit(node.execute, element, context)
                    future_to_node[future] = node

            # Collect results as they complete
            for future in as_completed(future_to_node):
                node = future_to_node[future]
                try:
                    result = future.result()
                    results.append(result)

                    # In parallel mode, we can't easily implement fail_fast
                    # since all tasks are already submitted
                    if not result.success:
                        self.logger.warning(f"Filter failed in parallel execution: {node.filter_obj.filter_type}")

                except Exception as e:
                    error_result = FilterResult(
                        success=False,
                        error_message=f"Exception in {node.filter_obj.filter_type}: {str(e)}",
                        metadata={'filter_type': node.filter_obj.filter_type, 'exception': str(e)}
                    )
                    results.append(error_result)

        # Sort results by original node order if needed
        # (parallel execution may complete out of order)
        return self._merge_results(results)

    def _merge_results(self, results: List[FilterResult]) -> FilterResult:
        """
        Merge multiple FilterResults into a single result.

        Args:
            results: List of FilterResult objects to merge

        Returns:
            Single FilterResult containing merged output
        """
        if not results:
            return FilterResult(success=True, drawingml="", metadata={'no_results': True})

        # Separate successful and failed results
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]

        # Combine DrawingML from successful results
        combined_drawingml = ""
        if successful_results:
            drawingml_parts = []
            for result in successful_results:
                if result.drawingml:
                    drawingml_parts.append(result.drawingml)

            if drawingml_parts:
                combined_drawingml = "".join(drawingml_parts)

        # Determine overall success
        overall_success = len(successful_results) > 0 and (not self.fail_fast or len(failed_results) == 0)

        # Combine metadata
        combined_metadata = {
            'chain_length': len(results),
            'successful_filters': len(successful_results),
            'failed_filters': len(failed_results),
            'execution_mode': self.execution_mode.value,
            'filter_results': [r.metadata for r in results if r.metadata]
        }

        # Handle error messages
        error_message = None
        if failed_results:
            error_messages = [r.error_message for r in failed_results if r.error_message]
            if error_messages:
                error_message = "; ".join(error_messages)

        if overall_success:
            return FilterResult(
                success=True,
                drawingml=combined_drawingml,
                metadata=combined_metadata
            )
        else:
            return FilterResult(
                success=False,
                error_message=error_message or "One or more filters failed",
                metadata=combined_metadata
            )

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get chain statistics and information.

        Returns:
            Dictionary containing chain statistics
        """
        with self.lock:
            enabled_nodes = [n for n in self.nodes if n.enabled]
            disabled_nodes = [n for n in self.nodes if not n.enabled]

            return {
                'total_nodes': len(self.nodes),
                'enabled_nodes': len(enabled_nodes),
                'disabled_nodes': len(disabled_nodes),
                'execution_mode': self.execution_mode.value,
                'fail_fast': self.fail_fast,
                'max_workers': self.max_workers,
                'filter_types': [n.filter_obj.filter_type for n in self.nodes]
            }

    def validate_chain(self) -> List[str]:
        """
        Validate the filter chain configuration.

        Returns:
            List of validation warnings/errors
        """
        warnings = []

        with self.lock:
            if not self.nodes:
                warnings.append("Chain is empty - no filters to process")

            if len(self.nodes) > 20:
                warnings.append(f"Chain has {len(self.nodes)} filters - consider optimization")

            # Check for duplicate filter types
            filter_types = [n.filter_obj.filter_type for n in self.nodes]
            duplicates = set([t for t in filter_types if filter_types.count(t) > 1])
            if duplicates:
                warnings.append(f"Duplicate filter types found: {duplicates}")

            # Check for conflicting filters (this would need domain knowledge)
            # For example, blur + sharpen might be conflicting

            # Check execution mode compatibility
            if self.execution_mode == ChainExecutionMode.PARALLEL and self.fail_fast:
                warnings.append("fail_fast mode is less effective with parallel execution")

        return warnings

    def optimize_chain(self) -> None:
        """
        Optimize the filter chain for better performance.

        This method can reorder filters, remove redundant filters,
        or apply other optimizations based on filter characteristics.
        """
        with self.lock:
            # Example optimization: move fast filters before slow ones
            # In practice, this would need more sophisticated analysis

            # Remove disabled nodes
            self.nodes = [n for n in self.nodes if n.enabled]

            # Could add other optimizations:
            # - Reorder based on filter complexity
            # - Merge compatible filters
            # - Remove redundant filters

            self.logger.debug("Chain optimization completed")

    def __len__(self) -> int:
        """Get the number of nodes in the chain."""
        return len(self.nodes)

    def __iter__(self) -> Iterator[FilterChainNode]:
        """Iterate over nodes in the chain."""
        return iter(self.nodes)

    def __str__(self) -> str:
        """String representation of the chain."""
        filter_types = [n.filter_obj.filter_type for n in self.nodes]
        return f"FilterChain(filters={len(self.nodes)}, types={filter_types}, mode={self.execution_mode.value})"

    def __repr__(self) -> str:
        """Detailed string representation of the chain."""
        return (
            f"FilterChain("
            f"nodes={len(self.nodes)}, "
            f"execution_mode={self.execution_mode.value}, "
            f"fail_fast={self.fail_fast}, "
            f"max_workers={self.max_workers})"
        )