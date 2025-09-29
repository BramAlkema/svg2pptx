#!/usr/bin/env python3
"""
Batch processing system for optimized SVG element conversion.

This module provides batch processing capabilities to:
- Group similar elements for bulk processing
- Reduce overhead of repeated operations
- Optimize resource utilization
- Enable parallel processing where safe
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional, Any, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from collections import defaultdict
from lxml import etree as ET
import time
import logging
from enum import Enum

from .cache import get_global_cache
from .pools import get_converter_pool

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BatchStrategy(Enum):
    """Batch processing strategies."""
    BY_ELEMENT_TYPE = "element_type"       # Group by SVG element type
    BY_COMPLEXITY = "complexity"           # Group by processing complexity
    BY_ATTRIBUTES = "attributes"           # Group by similar attributes
    BY_CONVERTER_TYPE = "converter_type"   # Group by converter class
    SEQUENTIAL = "sequential"              # No batching, process sequentially


@dataclass
class BatchItem:
    """Individual item in a batch."""
    element: ET.Element
    context: Any
    priority: int = 0
    estimated_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchGroup:
    """Group of similar items for batch processing."""
    batch_key: str
    strategy: BatchStrategy
    items: List[BatchItem] = field(default_factory=list)
    converter_class: Optional[type] = None
    estimated_total_time: float = 0.0
    max_batch_size: int = 50
    
    def add_item(self, item: BatchItem):
        """Add item to batch group."""
        self.items.append(item)
        self.estimated_total_time += item.estimated_time
    
    def should_split(self) -> bool:
        """Check if batch should be split due to size."""
        return len(self.items) > self.max_batch_size
    
    def split(self) -> List['BatchGroup']:
        """Split large batch into smaller chunks."""
        if not self.should_split():
            return [self]
        
        chunks = []
        chunk_size = self.max_batch_size
        
        for i in range(0, len(self.items), chunk_size):
            chunk_items = self.items[i:i + chunk_size]
            chunk = BatchGroup(
                batch_key=f"{self.batch_key}_chunk_{i//chunk_size}",
                strategy=self.strategy,
                converter_class=self.converter_class,
                max_batch_size=self.max_batch_size
            )
            chunk.items = chunk_items
            chunk.estimated_total_time = sum(item.estimated_time for item in chunk_items)
            chunks.append(chunk)
        
        return chunks


@dataclass
class BatchResult:
    """Result from batch processing."""
    batch_key: str
    items_processed: int
    processing_time: float
    outputs: List[str]
    errors: List[Exception] = field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0


class BatchProcessor:
    """Main batch processing engine."""
    
    def __init__(self, 
                 max_workers: int = 4,
                 default_strategy: BatchStrategy = BatchStrategy.BY_ELEMENT_TYPE,
                 enable_caching: bool = True,
                 enable_pooling: bool = True):
        """
        Initialize batch processor.
        
        Args:
            max_workers: Maximum number of worker threads
            default_strategy: Default batching strategy
            enable_caching: Whether to use caching
            enable_pooling: Whether to use object pooling
        """
        self.max_workers = max_workers
        self.default_strategy = default_strategy
        self.enable_caching = enable_caching
        self.enable_pooling = enable_pooling
        
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.cache = get_global_cache() if enable_caching else None
        self.converter_pool = get_converter_pool() if enable_pooling else None
        
        # Strategy implementations
        self._strategy_handlers = {
            BatchStrategy.BY_ELEMENT_TYPE: self._group_by_element_type,
            BatchStrategy.BY_COMPLEXITY: self._group_by_complexity,
            BatchStrategy.BY_ATTRIBUTES: self._group_by_attributes,
            BatchStrategy.BY_CONVERTER_TYPE: self._group_by_converter_type,
            BatchStrategy.SEQUENTIAL: self._no_grouping
        }
        
        # Performance tracking
        self.processed_batches = 0
        self.total_items_processed = 0
        self.total_processing_time = 0.0
        self.lock = threading.RLock()
    
    def create_batch_items(self, 
                          elements: List[ET.Element],
                          contexts: List[Any],
                          priorities: Optional[List[int]] = None) -> List[BatchItem]:
        """Create batch items from elements and contexts."""
        if priorities is None:
            priorities = [0] * len(elements)
        
        items = []
        for i, (element, context) in enumerate(zip(elements, contexts)):
            # Estimate processing time based on element complexity
            estimated_time = self._estimate_processing_time(element)
            
            item = BatchItem(
                element=element,
                context=context,
                priority=priorities[i] if i < len(priorities) else 0,
                estimated_time=estimated_time,
                metadata=self._extract_element_metadata(element)
            )
            items.append(item)
        
        return items
    
    def group_items(self, 
                   items: List[BatchItem],
                   strategy: Optional[BatchStrategy] = None) -> List[BatchGroup]:
        """Group batch items according to strategy."""
        strategy = strategy or self.default_strategy
        
        if strategy not in self._strategy_handlers:
            logger.warning(f"Unknown strategy {strategy}, falling back to BY_ELEMENT_TYPE")
            strategy = BatchStrategy.BY_ELEMENT_TYPE
        
        handler = self._strategy_handlers[strategy]
        groups = handler(items)
        
        # Split oversized groups
        final_groups = []
        for group in groups:
            final_groups.extend(group.split())
        
        logger.info(f"Grouped {len(items)} items into {len(final_groups)} batches using {strategy.value}")
        return final_groups
    
    def process_batches(self, 
                       batch_groups: List[BatchGroup],
                       parallel: bool = True) -> List[BatchResult]:
        """Process batch groups."""
        start_time = time.time()
        
        if parallel and len(batch_groups) > 1:
            results = self._process_parallel(batch_groups)
        else:
            results = self._process_sequential(batch_groups)
        
        total_time = time.time() - start_time
        
        # Update statistics
        with self.lock:
            self.processed_batches += len(batch_groups)
            self.total_items_processed += sum(r.items_processed for r in results)
            self.total_processing_time += total_time
        
        logger.info(f"Processed {len(batch_groups)} batches in {total_time:.3f}s")
        return results
    
    def process_elements(self,
                        elements: List[ET.Element],
                        contexts: List[Any],
                        converter_classes: List[type],
                        strategy: Optional[BatchStrategy] = None,
                        parallel: bool = True) -> List[str]:
        """High-level method to process elements with batching."""
        # Create batch items
        items = self.create_batch_items(elements, contexts)
        
        # Add converter class information
        for item, converter_class in zip(items, converter_classes):
            item.metadata['converter_class'] = converter_class
        
        # Group items
        groups = self.group_items(items, strategy)
        
        # Process batches
        results = self.process_batches(groups, parallel)
        
        # Flatten outputs maintaining order
        outputs = []
        for result in results:
            outputs.extend(result.outputs)
        
        return outputs
    
    def _process_parallel(self, batch_groups: List[BatchGroup]) -> List[BatchResult]:
        """Process batch groups in parallel."""
        future_to_group = {}
        
        for group in batch_groups:
            future = self.executor.submit(self._process_single_batch, group)
            future_to_group[future] = group
        
        results = []
        for future in as_completed(future_to_group):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                group = future_to_group[future]
                logger.error(f"Error processing batch {group.batch_key}: {e}")
                # Create error result
                error_result = BatchResult(
                    batch_key=group.batch_key,
                    items_processed=0,
                    processing_time=0.0,
                    outputs=[],
                    errors=[e]
                )
                results.append(error_result)
        
        # Sort results to maintain order
        results.sort(key=lambda r: r.batch_key)
        return results
    
    def _process_sequential(self, batch_groups: List[BatchGroup]) -> List[BatchResult]:
        """Process batch groups sequentially."""
        results = []
        for group in batch_groups:
            try:
                result = self._process_single_batch(group)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing batch {group.batch_key}: {e}")
                error_result = BatchResult(
                    batch_key=group.batch_key,
                    items_processed=0,
                    processing_time=0.0,
                    outputs=[],
                    errors=[e]
                )
                results.append(error_result)
        
        return results
    
    def _process_single_batch(self, group: BatchGroup) -> BatchResult:
        """Process a single batch group."""
        start_time = time.time()
        outputs = []
        errors = []
        cache_hits = 0
        cache_misses = 0
        
        logger.debug(f"Processing batch {group.batch_key} with {len(group.items)} items")
        
        # Get converter if using pooling
        if self.enable_pooling and group.converter_class:
            with self.converter_pool.get_converter(group.converter_class) as converter:
                for item in group.items:
                    try:
                        output, hit = self._process_single_item(item, converter)
                        outputs.append(output)
                        if hit:
                            cache_hits += 1
                        else:
                            cache_misses += 1
                    except Exception as e:
                        logger.error(f"Error processing item: {e}")
                        errors.append(e)
                        outputs.append("")  # Placeholder for failed item
        else:
            # Process without pooling
            for item in group.items:
                try:
                    output, hit = self._process_single_item(item, None)
                    outputs.append(output)
                    if hit:
                        cache_hits += 1
                    else:
                        cache_misses += 1
                except Exception as e:
                    logger.error(f"Error processing item: {e}")
                    errors.append(e)
                    outputs.append("")
        
        processing_time = time.time() - start_time
        
        return BatchResult(
            batch_key=group.batch_key,
            items_processed=len(group.items),
            processing_time=processing_time,
            outputs=outputs,
            errors=errors,
            cache_hits=cache_hits,
            cache_misses=cache_misses
        )
    
    def _process_single_item(self, item: BatchItem, converter) -> Tuple[str, bool]:
        """Process a single batch item."""
        cache_hit = False
        
        # Try cache first if enabled
        if self.enable_caching and self.cache:
            context_hash = self._hash_context(item.context)
            cached_output = self.cache.get_drawingml_output(item.element, context_hash)
            if cached_output is not None:
                return cached_output, True
        
        # Process item
        if converter is None:
            # Create converter instance (fallback if pooling disabled)
            converter_class = item.metadata.get('converter_class')
            if converter_class:
                converter = converter_class()
        
        if hasattr(converter, 'convert'):
            output = converter.convert(item.element, item.context)
        else:
            # Fallback for converters without convert method
            output = str(item.element.tag)  # Simple fallback
        
        # Cache result if enabled
        if self.enable_caching and self.cache:
            context_hash = self._hash_context(item.context)
            self.cache.cache_drawingml_output(item.element, context_hash, output)
        
        return output, cache_hit
    
    def _estimate_processing_time(self, element: ET.Element) -> float:
        """Estimate processing time for an element."""
        # Simple heuristic based on element type and complexity
        base_time = 0.001  # 1ms base
        
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        
        # Time multipliers by element complexity
        complexity_multipliers = {
            'path': 5.0,
            'text': 3.0,
            'image': 10.0,
            'g': 2.0,  # groups can contain many children
            'use': 1.5,
            'circle': 1.0,
            'rect': 1.0,
            'line': 1.0
        }
        
        multiplier = complexity_multipliers.get(tag, 2.0)
        
        # Adjust for attributes
        attr_count = len(element.attrib)
        attr_multiplier = 1.0 + (attr_count * 0.1)
        
        # Adjust for children
        child_count = len(list(element))
        child_multiplier = 1.0 + (child_count * 0.5)
        
        return base_time * multiplier * attr_multiplier * child_multiplier
    
    def _extract_element_metadata(self, element: ET.Element) -> Dict[str, Any]:
        """Extract metadata from element for grouping."""
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        
        return {
            'tag': tag,
            'attribute_count': len(element.attrib),
            'child_count': len(list(element)),
            'has_transform': element.get('transform') is not None,
            'has_style': element.get('style') is not None,
            'has_class': element.get('class') is not None
        }
    
    def _hash_context(self, context) -> str:
        """Create hash of context for caching."""
        # Simple hash - in practice you'd want a more robust implementation
        return str(hash(str(context)))
    
    # Strategy implementations
    def _group_by_element_type(self, items: List[BatchItem]) -> List[BatchGroup]:
        """Group items by SVG element type."""
        groups_dict = defaultdict(list)
        
        for item in items:
            tag = item.metadata.get('tag', 'unknown')
            groups_dict[tag].append(item)
        
        groups = []
        for tag, group_items in groups_dict.items():
            group = BatchGroup(
                batch_key=f"element_type_{tag}",
                strategy=BatchStrategy.BY_ELEMENT_TYPE
            )
            for item in group_items:
                group.add_item(item)
            groups.append(group)
        
        return groups
    
    def _group_by_complexity(self, items: List[BatchItem]) -> List[BatchGroup]:
        """Group items by processing complexity."""
        # Divide into complexity tiers
        low_complexity = []
        medium_complexity = []
        high_complexity = []
        
        for item in items:
            if item.estimated_time < 0.005:  # < 5ms
                low_complexity.append(item)
            elif item.estimated_time < 0.020:  # < 20ms
                medium_complexity.append(item)
            else:
                high_complexity.append(item)
        
        groups = []
        for complexity_level, group_items in [
            ('low', low_complexity),
            ('medium', medium_complexity),
            ('high', high_complexity)
        ]:
            if group_items:
                group = BatchGroup(
                    batch_key=f"complexity_{complexity_level}",
                    strategy=BatchStrategy.BY_COMPLEXITY
                )
                for item in group_items:
                    group.add_item(item)
                groups.append(group)
        
        return groups
    
    def _group_by_attributes(self, items: List[BatchItem]) -> List[BatchGroup]:
        """Group items by similar attributes."""
        groups_dict = defaultdict(list)
        
        for item in items:
            # Create key based on common attributes
            has_transform = item.metadata.get('has_transform', False)
            has_style = item.metadata.get('has_style', False)
            attr_count_tier = min(item.metadata.get('attribute_count', 0) // 3, 3)  # 0-2, 3-5, 6-8, 9+
            
            key = f"attrs_{has_transform}_{has_style}_{attr_count_tier}"
            groups_dict[key].append(item)
        
        groups = []
        for key, group_items in groups_dict.items():
            group = BatchGroup(
                batch_key=f"attributes_{key}",
                strategy=BatchStrategy.BY_ATTRIBUTES
            )
            for item in group_items:
                group.add_item(item)
            groups.append(group)
        
        return groups
    
    def _group_by_converter_type(self, items: List[BatchItem]) -> List[BatchGroup]:
        """Group items by converter class."""
        groups_dict = defaultdict(list)
        
        for item in items:
            converter_class = item.metadata.get('converter_class')
            if converter_class:
                key = converter_class.__name__
                groups_dict[key].append(item)
            else:
                groups_dict['no_converter'].append(item)
        
        groups = []
        for converter_name, group_items in groups_dict.items():
            group = BatchGroup(
                batch_key=f"converter_{converter_name}",
                strategy=BatchStrategy.BY_CONVERTER_TYPE
            )
            
            # Set converter class for pooling
            if group_items and 'converter_class' in group_items[0].metadata:
                group.converter_class = group_items[0].metadata['converter_class']
            
            for item in group_items:
                group.add_item(item)
            groups.append(group)
        
        return groups
    
    def _no_grouping(self, items: List[BatchItem]) -> List[BatchGroup]:
        """No grouping - each item is its own batch."""
        groups = []
        for i, item in enumerate(items):
            group = BatchGroup(
                batch_key=f"sequential_{i}",
                strategy=BatchStrategy.SEQUENTIAL,
                max_batch_size=1
            )
            group.add_item(item)
            groups.append(group)
        
        return groups
    
    def get_stats(self) -> Dict[str, Any]:
        """Get batch processor statistics."""
        with self.lock:
            avg_batch_time = (self.total_processing_time / max(self.processed_batches, 1))
            avg_item_time = (self.total_processing_time / max(self.total_items_processed, 1))
            
            return {
                'processed_batches': self.processed_batches,
                'total_items_processed': self.total_items_processed,
                'total_processing_time': self.total_processing_time,
                'avg_batch_time': avg_batch_time,
                'avg_item_time': avg_item_time,
                'max_workers': self.max_workers,
                'default_strategy': self.default_strategy.value,
                'caching_enabled': self.enable_caching,
                'pooling_enabled': self.enable_pooling
            }


# Global batch processor instance
_global_batch_processor = None

def get_batch_processor() -> BatchProcessor:
    """Get or create the global batch processor."""
    global _global_batch_processor
    if _global_batch_processor is None:
        _global_batch_processor = BatchProcessor()
    return _global_batch_processor