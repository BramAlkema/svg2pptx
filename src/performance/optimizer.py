#!/usr/bin/env python3
"""
Main performance optimizer that orchestrates all optimization techniques.

This module integrates caching, pooling, batching, and profiling to provide
maximum performance for SVG conversion operations.
"""

import time
import threading
from typing import List, Dict, Any, Optional, Type, Callable
import xml.etree.ElementTree as ET
import logging
from dataclasses import dataclass
from enum import Enum

from .cache import get_global_cache, ConversionCache
from .pools import get_converter_pool, ConverterPool
from .batch import get_batch_processor, BatchProcessor, BatchStrategy
from .profiler import get_profiler, PerformanceProfiler

logger = logging.getLogger(__name__)


class OptimizationLevel(Enum):
    """Performance optimization levels."""
    NONE = "none"              # No optimization
    BASIC = "basic"            # Basic caching only
    STANDARD = "standard"      # Caching + pooling
    AGGRESSIVE = "aggressive"  # Caching + pooling + batching
    MAXIMUM = "maximum"        # All optimizations + profiling


@dataclass
class OptimizationConfig:
    """Configuration for performance optimization."""
    level: OptimizationLevel = OptimizationLevel.STANDARD
    
    # Caching configuration
    enable_caching: bool = True
    cache_ttl: Optional[float] = 300.0  # 5 minutes
    
    # Pooling configuration
    enable_pooling: bool = True
    max_pool_size: int = 10
    
    # Batching configuration
    enable_batching: bool = False
    batch_strategy: BatchStrategy = BatchStrategy.BY_ELEMENT_TYPE
    max_batch_workers: int = 4
    min_batch_size: int = 5
    
    # Profiling configuration
    enable_profiling: bool = False
    profile_memory: bool = True
    profile_cpu: bool = True
    
    # Auto-optimization
    enable_auto_optimization: bool = True
    optimization_interval: float = 60.0  # 1 minute
    
    @classmethod
    def from_level(cls, level: OptimizationLevel) -> 'OptimizationConfig':
        """Create config from optimization level."""
        if level == OptimizationLevel.NONE:
            return cls(
                level=level,
                enable_caching=False,
                enable_pooling=False,
                enable_batching=False,
                enable_profiling=False,
                enable_auto_optimization=False
            )
        elif level == OptimizationLevel.BASIC:
            return cls(
                level=level,
                enable_caching=True,
                enable_pooling=False,
                enable_batching=False,
                enable_profiling=False
            )
        elif level == OptimizationLevel.STANDARD:
            return cls(
                level=level,
                enable_caching=True,
                enable_pooling=True,
                enable_batching=False,
                enable_profiling=False
            )
        elif level == OptimizationLevel.AGGRESSIVE:
            return cls(
                level=level,
                enable_caching=True,
                enable_pooling=True,
                enable_batching=True,
                enable_profiling=False
            )
        elif level == OptimizationLevel.MAXIMUM:
            return cls(
                level=level,
                enable_caching=True,
                enable_pooling=True,
                enable_batching=True,
                enable_profiling=True,
                enable_auto_optimization=True
            )
        else:
            return cls()


class PerformanceOptimizer:
    """Main performance optimizer orchestrating all optimization techniques."""
    
    def __init__(self, config: OptimizationConfig):
        """Initialize the performance optimizer."""
        self.config = config
        self.lock = threading.RLock()
        
        # Initialize optimization components
        self.cache: Optional[ConversionCache] = None
        self.pool: Optional[ConverterPool] = None
        self.batch_processor: Optional[BatchProcessor] = None
        self.profiler: Optional[PerformanceProfiler] = None
        
        self._setup_components()
        
        # Auto-optimization thread
        self._auto_optimization_thread = None
        self._stop_auto_optimization = False
        
        if self.config.enable_auto_optimization:
            self._start_auto_optimization()
        
        # Performance statistics
        self.conversion_count = 0
        self.total_conversion_time = 0.0
        self.cache_hit_rate = 0.0
        self.pool_utilization = 0.0
        
        logger.info(f"Performance optimizer initialized with level: {self.config.level.value}")
    
    def _setup_components(self):
        """Setup optimization components based on configuration."""
        if self.config.enable_caching:
            self.cache = get_global_cache()
            logger.info("Caching enabled")
        
        if self.config.enable_pooling:
            self.pool = get_converter_pool()
            logger.info("Object pooling enabled")
        
        if self.config.enable_batching:
            self.batch_processor = get_batch_processor()
            self.batch_processor.max_workers = self.config.max_batch_workers
            self.batch_processor.default_strategy = self.config.batch_strategy
            logger.info(f"Batch processing enabled with {self.config.max_batch_workers} workers")
        
        if self.config.enable_profiling:
            self.profiler = get_profiler()
            logger.info("Performance profiling enabled")
    
    def convert_element(self, 
                       element: ET.Element,
                       context: Any,
                       converter_class: Type) -> str:
        """Convert a single element with optimization."""
        start_time = time.time()
        
        # Start profiling if enabled
        profile_context = None
        if self.profiler:
            profile_context = self.profiler.profile_operation(
                f"convert_{element.tag.split('}')[-1] if '}' in element.tag else element.tag}",
                metadata={'converter': converter_class.__name__}
            )
            profile_context.__enter__()
        
        try:
            # Try cache first
            if self.cache:
                context_hash = self._hash_context(context)
                cached_result = self.cache.get_drawingml_output(element, context_hash)
                if cached_result is not None:
                    return cached_result
            
            # Use pooled converter if available
            if self.pool:
                with self.pool.get_converter(converter_class) as converter:
                    result = converter.convert(element, context)
            else:
                # Fallback: create converter instance
                converter = converter_class()
                result = converter.convert(element, context)
            
            # Cache result
            if self.cache:
                context_hash = self._hash_context(context)
                self.cache.cache_drawingml_output(element, context_hash, result)
            
            return result
            
        finally:
            # End profiling
            if profile_context:
                profile_context.__exit__(None, None, None)
            
            # Update statistics
            with self.lock:
                self.conversion_count += 1
                self.total_conversion_time += time.time() - start_time
    
    def convert_elements(self,
                        elements: List[ET.Element],
                        contexts: List[Any],
                        converter_classes: List[Type],
                        use_batching: Optional[bool] = None) -> List[str]:
        """Convert multiple elements with optimization."""
        if not elements:
            return []
        
        start_time = time.time()
        
        # Decide whether to use batching
        should_batch = (
            (use_batching if use_batching is not None else self.config.enable_batching) and
            len(elements) >= self.config.min_batch_size and
            self.batch_processor is not None
        )
        
        # Start profiling session if enabled
        session_id = None
        if self.profiler:
            session_id = f"batch_conversion_{int(time.time())}"
            self.profiler.start_session(session_id)
        
        try:
            if should_batch:
                logger.debug(f"Using batch processing for {len(elements)} elements")
                results = self.batch_processor.process_elements(
                    elements=elements,
                    contexts=contexts,
                    converter_classes=converter_classes,
                    strategy=self.config.batch_strategy,
                    parallel=True
                )
            else:
                logger.debug(f"Using sequential processing for {len(elements)} elements")
                results = []
                for element, context, converter_class in zip(elements, contexts, converter_classes):
                    result = self.convert_element(element, context, converter_class)
                    results.append(result)
            
            return results
            
        finally:
            # End profiling session
            if self.profiler and session_id:
                self.profiler.end_session(session_id)
            
            # Update statistics
            processing_time = time.time() - start_time
            with self.lock:
                self.conversion_count += len(elements)
                self.total_conversion_time += processing_time
            
            logger.info(f"Converted {len(elements)} elements in {processing_time:.3f}s "
                       f"({'batched' if should_batch else 'sequential'})")
    
    def optimize_for_document(self, 
                             svg_root: ET.Element,
                             estimated_element_count: int) -> OptimizationConfig:
        """Optimize configuration for a specific document."""
        current_config = self.config
        
        # Analyze document characteristics
        analysis = self._analyze_document(svg_root, estimated_element_count)
        
        # Adjust configuration based on analysis
        optimized_config = OptimizationConfig.from_level(current_config.level)
        
        # Large documents benefit more from batching
        if estimated_element_count > 100:
            optimized_config.enable_batching = True
            optimized_config.min_batch_size = max(5, estimated_element_count // 20)
        
        # Complex documents benefit from more aggressive caching
        if analysis['complexity_score'] > 0.7:
            optimized_config.cache_ttl = 600.0  # 10 minutes for complex documents
        
        # High repetition documents benefit from larger pools
        if analysis['repetition_score'] > 0.5:
            optimized_config.max_pool_size = min(20, estimated_element_count // 10)
        
        logger.info(f"Optimized config for document: "
                   f"complexity={analysis['complexity_score']:.2f}, "
                   f"repetition={analysis['repetition_score']:.2f}, "
                   f"elements={estimated_element_count}")
        
        return optimized_config
    
    def _analyze_document(self, svg_root: ET.Element, element_count: int) -> Dict[str, float]:
        """Analyze document characteristics for optimization."""
        # Element type distribution
        element_types = {}
        complex_elements = 0
        
        for elem in svg_root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            element_types[tag] = element_types.get(tag, 0) + 1
            
            # Count complex elements
            if tag in ['path', 'text', 'image', 'use', 'g'] or len(elem.attrib) > 5:
                complex_elements += 1
        
        # Calculate scores
        complexity_score = complex_elements / max(element_count, 1)
        
        # Repetition score based on element type distribution
        if element_types:
            max_count = max(element_types.values())
            repetition_score = max_count / max(element_count, 1)
        else:
            repetition_score = 0.0
        
        return {
            'complexity_score': min(complexity_score, 1.0),
            'repetition_score': min(repetition_score, 1.0),
            'element_types': element_types,
            'unique_types': len(element_types)
        }
    
    def _hash_context(self, context: Any) -> str:
        """Create hash of context for caching."""
        # Simplified hash - in practice you'd want more robust implementation
        return str(hash(str(context)))
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        with self.lock:
            report = {
                'config': {
                    'level': self.config.level.value,
                    'caching_enabled': self.config.enable_caching,
                    'pooling_enabled': self.config.enable_pooling,
                    'batching_enabled': self.config.enable_batching,
                    'profiling_enabled': self.config.enable_profiling
                },
                'statistics': {
                    'total_conversions': self.conversion_count,
                    'total_time': self.total_conversion_time,
                    'avg_conversion_time': (
                        self.total_conversion_time / max(self.conversion_count, 1)
                    ),
                    'conversions_per_second': (
                        self.conversion_count / max(self.total_conversion_time, 0.001)
                    )
                }
            }
        
        # Add component-specific statistics
        if self.cache:
            cache_stats = self.cache.get_total_stats()
            total_requests = sum(stat.total_requests for stat in cache_stats.values())
            total_hits = sum(stat.hits for stat in cache_stats.values())
            
            report['cache'] = {
                'total_requests': total_requests,
                'total_hits': total_hits,
                'hit_rate': total_hits / max(total_requests, 1),
                'memory_usage': self.cache.get_memory_usage()
            }
        
        if self.pool:
            report['pooling'] = self.pool.get_all_stats()
        
        if self.batch_processor:
            report['batching'] = self.batch_processor.get_stats()
        
        if self.profiler:
            report['profiling'] = self.profiler.get_global_stats()
        
        return report
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get optimization recommendations."""
        recommendations = []
        
        # Basic performance analysis
        if self.conversion_count > 0:
            avg_time = self.total_conversion_time / self.conversion_count
            
            if avg_time > 0.1:  # Slower than 100ms per element
                recommendations.append(
                    f"Average conversion time is high ({avg_time:.3f}s) - consider enabling more optimizations"
                )
        
        # Cache recommendations
        if self.cache:
            cache_stats = self.cache.get_total_stats()
            total_requests = sum(stat.total_requests for stat in cache_stats.values())
            total_hits = sum(stat.hits for stat in cache_stats.values())
            
            if total_requests > 100:
                hit_rate = total_hits / total_requests
                if hit_rate < 0.3:
                    recommendations.append(
                        f"Cache hit rate is low ({hit_rate:.1%}) - consider optimizing cache keys or increasing cache size"
                    )
        
        # Pooling recommendations
        if self.pool:
            pool_stats = self.pool.get_all_stats()
            for pool_name, stats in pool_stats.get('converters', {}).items():
                if stats.get('utilization', 0) > 0.8:
                    recommendations.append(
                        f"High utilization in {pool_name} pool ({stats['utilization']:.1%}) - consider increasing pool size"
                    )
        
        # Batching recommendations
        if not self.config.enable_batching and self.conversion_count > 50:
            recommendations.append(
                "High conversion volume detected - consider enabling batch processing"
            )
        
        # Get profiler recommendations if available
        if self.profiler:
            profiler_recommendations = self.profiler.get_optimization_recommendations()
            recommendations.extend(profiler_recommendations)
        
        return recommendations
    
    def _start_auto_optimization(self):
        """Start auto-optimization thread."""
        def auto_optimize():
            while not self._stop_auto_optimization:
                try:
                    time.sleep(self.config.optimization_interval)
                    
                    if not self._stop_auto_optimization:
                        recommendations = self.get_optimization_recommendations()
                        if recommendations:
                            logger.info(f"Auto-optimization recommendations: {recommendations[:3]}")
                            
                        # Basic auto-adjustments
                        self._apply_auto_optimizations()
                        
                except Exception as e:
                    logger.error(f"Error in auto-optimization: {e}")
        
        self._auto_optimization_thread = threading.Thread(
            target=auto_optimize, 
            daemon=True
        )
        self._auto_optimization_thread.start()
        logger.info("Started auto-optimization thread")
    
    def _apply_auto_optimizations(self):
        """Apply automatic optimizations based on current performance."""
        # Auto-adjust cache TTL based on hit rate
        if self.cache:
            cache_stats = self.cache.get_total_stats()
            total_requests = sum(stat.total_requests for stat in cache_stats.values())
            total_hits = sum(stat.hits for stat in cache_stats.values())
            
            if total_requests > 100:
                hit_rate = total_hits / total_requests
                if hit_rate > 0.8:
                    # High hit rate - increase TTL
                    logger.debug("High cache hit rate - maintaining current settings")
                elif hit_rate < 0.3:
                    # Low hit rate - consider clearing cache
                    logger.debug("Low cache hit rate - clearing old cache entries")
                    self.cache.clear_all()
    
    def cleanup(self):
        """Clean up optimizer resources."""
        # Stop auto-optimization
        self._stop_auto_optimization = True
        if self._auto_optimization_thread:
            self._auto_optimization_thread.join(timeout=5.0)
        
        # Clean up profiler data
        if self.profiler:
            self.profiler.clear_old_data()
        
        logger.info("Performance optimizer cleanup completed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


# Factory functions for common configurations
def create_optimizer(level: OptimizationLevel = OptimizationLevel.STANDARD) -> PerformanceOptimizer:
    """Create a performance optimizer with the specified level."""
    config = OptimizationConfig.from_level(level)
    return PerformanceOptimizer(config)


def create_development_optimizer() -> PerformanceOptimizer:
    """Create optimizer for development with full profiling."""
    config = OptimizationConfig.from_level(OptimizationLevel.MAXIMUM)
    config.optimization_interval = 30.0  # More frequent optimization
    return PerformanceOptimizer(config)


def create_production_optimizer() -> PerformanceOptimizer:
    """Create optimizer for production with balanced performance."""
    config = OptimizationConfig.from_level(OptimizationLevel.AGGRESSIVE)
    config.enable_profiling = False  # Disable profiling in production
    config.cache_ttl = 1800.0  # 30 minutes
    return PerformanceOptimizer(config)


# Global optimizer instance
_global_optimizer = None

def get_optimizer() -> PerformanceOptimizer:
    """Get or create the global performance optimizer."""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = create_optimizer()
    return _global_optimizer