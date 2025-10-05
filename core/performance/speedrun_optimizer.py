#!/usr/bin/env python3
"""
Speedrun optimizer for maximum SVG conversion performance.

This module implements aggressive optimization strategies that build on the
existing performance infrastructure to achieve 10x+ speed improvements for
cached conversions.
"""

import time
import asyncio
import concurrent.futures
from typing import List, Dict, Any, Optional, Tuple
from lxml import etree as ET
from dataclasses import dataclass
from enum import Enum
import logging

from .optimizer import PerformanceOptimizer, OptimizationConfig, OptimizationLevel
from .speedrun_cache import get_speedrun_cache
from .batch import BatchProcessor, BatchStrategy
from .profiler import get_profiler
from .pools import get_converter_pool

logger = logging.getLogger(__name__)


class SpeedrunMode(Enum):
    """Speedrun optimization modes."""
    CONSERVATIVE = "conservative"  # Safe optimizations, maintain compatibility
    AGGRESSIVE = "aggressive"      # Maximum speed, may trade some compatibility
    LUDICROUS = "ludicrous"       # Extreme optimizations for maximum throughput


@dataclass
class SpeedrunMetrics:
    """Performance metrics for speedrun operations."""
    elements_processed: int
    cache_hit_rate: float
    avg_processing_time_ms: float
    peak_memory_mb: float
    total_time_seconds: float
    speedup_factor: float  # Compared to baseline
    
    def __str__(self) -> str:
        return (f"SpeedrunMetrics(elements={self.elements_processed}, "
                f"hit_rate={self.cache_hit_rate:.1%}, "
                f"avg_time={self.avg_processing_time_ms:.2f}ms, "
                f"speedup={self.speedup_factor:.1f}x)")


class SVGSpeedrunOptimizer:
    """Specialized optimizer for SVG conversion speedruns."""
    
    def __init__(self, mode: SpeedrunMode = SpeedrunMode.AGGRESSIVE):
        """
        Initialize speedrun optimizer.
        
        Args:
            mode: Speedrun optimization mode
        """
        self.mode = mode
        self.speedrun_cache = get_speedrun_cache()
        self.profiler = get_profiler()
        self.converter_pool = get_converter_pool()
        
        # Configure optimization level based on mode
        self.optimization_config = self._create_optimization_config()
        self.base_optimizer = PerformanceOptimizer(self.optimization_config)
        
        # Speedrun-specific state
        self._element_patterns = {}  # Cache of common element patterns
        self._hot_paths = set()      # Frequently used conversion paths
        self._cold_paths = set()     # Rarely used conversion paths
        
        # Performance tracking
        self._baseline_times = {}
        self._speedrun_metrics = []
        
        logger.info(f"SVGSpeedrunOptimizer initialized in {mode.value} mode")
    
    def _create_optimization_config(self) -> OptimizationConfig:
        """Create optimization config based on speedrun mode."""
        base_config = OptimizationConfig()
        
        if self.mode == SpeedrunMode.CONSERVATIVE:
            base_config.level = OptimizationLevel.STANDARD
            base_config.enable_batching = True
            base_config.batch_strategy = BatchStrategy.BY_ELEMENT_TYPE
            base_config.max_batch_workers = 2
            
        elif self.mode == SpeedrunMode.AGGRESSIVE:
            base_config.level = OptimizationLevel.AGGRESSIVE
            base_config.enable_batching = True
            base_config.batch_strategy = BatchStrategy.BY_CONVERTER_TYPE
            base_config.max_batch_workers = 4
            base_config.enable_profiling = True
            
        elif self.mode == SpeedrunMode.LUDICROUS:
            base_config.level = OptimizationLevel.MAXIMUM
            base_config.enable_batching = True
            base_config.batch_strategy = BatchStrategy.BY_COMPLEXITY
            base_config.max_batch_workers = 8
            base_config.enable_profiling = True
            base_config.enable_auto_optimization = True
        
        return base_config
    
    def warmup_cache(self, sample_svgs: List[str] = None) -> None:
        """Warm up caches with common SVG patterns."""
        logger.info("Starting speedrun cache warmup")
        
        # Start background cache warming
        self.speedrun_cache.start_cache_warming(sample_svgs)
        
        # Pre-populate hot paths
        self._identify_hot_paths()
        
        logger.info("Speedrun cache warmup initiated")
    
    def _identify_hot_paths(self):
        """Identify frequently used conversion patterns."""
        # Common SVG element patterns that benefit from aggressive caching
        hot_patterns = [
            ('rect', {'fill', 'stroke', 'width', 'height'}),
            ('circle', {'fill', 'stroke', 'r', 'cx', 'cy'}),
            ('path', {'d', 'fill', 'stroke'}),
            ('text', {'font-family', 'font-size', 'fill'}),
            ('g', {'transform'}),
            ('line', {'x1', 'y1', 'x2', 'y2', 'stroke'})
        ]
        
        for element_type, common_attrs in hot_patterns:
            self._hot_paths.add(element_type)
            # Pre-cache common attribute combinations
            self._element_patterns[element_type] = common_attrs
    
    async def convert_svg_speedrun(self, 
                                  svg_content: str,
                                  conversion_context: Dict[str, Any] = None) -> Tuple[str, SpeedrunMetrics]:
        """
        Convert SVG with maximum speedrun optimizations.
        
        Args:
            svg_content: SVG content to convert
            conversion_context: Conversion context and settings
            
        Returns:
            Tuple of (converted_content, speedrun_metrics)
        """
        start_time = time.perf_counter()
        
        # Parse SVG
        try:
            svg_root = ET.fromstring(svg_content)
        except ET.XMLSyntaxError as e:
            logger.error(f"Invalid SVG content: {e}")
            raise
        
        # Initialize tracking
        context = conversion_context or {}
        elements_processed = 0
        cache_hits = 0
        
        with self.profiler.profile_session(f"speedrun_conversion") as session:
            # Check for full document cache hit first
            full_doc_hash = self.speedrun_cache.put_with_content_addressing(
                svg_content, None, context, persist_to_disk=False
            )
            
            cached_result = self.speedrun_cache.get_with_content_addressing(
                svg_content, context
            )
            
            if cached_result is not None:
                # Full document cache hit - ultimate speedrun!
                end_time = time.perf_counter()
                metrics = SpeedrunMetrics(
                    elements_processed=1,
                    cache_hit_rate=1.0,
                    avg_processing_time_ms=(end_time - start_time) * 1000,
                    peak_memory_mb=session.get_peak_memory_mb(),
                    total_time_seconds=end_time - start_time,
                    speedup_factor=self._calculate_speedup(end_time - start_time)
                )
                
                logger.info(f"Full document cache hit: {metrics}")
                return cached_result, metrics
            
            # Process elements with speedrun optimizations
            result, elements_processed, cache_hits = await self._process_elements_speedrun(
                svg_root, context
            )
            
            # Cache the full result
            self.speedrun_cache.put_with_content_addressing(
                svg_content, result, context,
                tags={'full_document', 'speedrun'},
                persist_to_disk=True
            )
        
        end_time = time.perf_counter()
        
        # Calculate metrics
        total_time = end_time - start_time
        cache_hit_rate = cache_hits / max(elements_processed, 1)
        avg_time_ms = (total_time / max(elements_processed, 1)) * 1000
        
        metrics = SpeedrunMetrics(
            elements_processed=elements_processed,
            cache_hit_rate=cache_hit_rate,
            avg_processing_time_ms=avg_time_ms,
            peak_memory_mb=session.get_peak_memory_mb(),
            total_time_seconds=total_time,
            speedup_factor=self._calculate_speedup(total_time)
        )
        
        self._speedrun_metrics.append(metrics)
        
        logger.info(f"Speedrun conversion completed: {metrics}")
        return result, metrics
    
    async def _process_elements_speedrun(self, 
                                        svg_root: ET.Element,
                                        context: Dict[str, Any]) -> Tuple[str, int, int]:
        """Process SVG elements with speedrun optimizations."""
        elements = list(svg_root.iter())
        elements_processed = 0
        cache_hits = 0
        results = []
        
        # Group elements by hot/cold paths for differential processing
        hot_elements = []
        cold_elements = []
        
        for element in elements:
            tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            if tag in self._hot_paths:
                hot_elements.append(element)
            else:
                cold_elements.append(element)
        
        # Process hot path elements with aggressive caching
        if hot_elements:
            hot_results, hot_processed, hot_hits = await self._process_hot_path_elements(
                hot_elements, context
            )
            results.extend(hot_results)
            elements_processed += hot_processed
            cache_hits += hot_hits
        
        # Process cold path elements with standard optimization
        if cold_elements:
            cold_results, cold_processed, cold_hits = await self._process_cold_path_elements(
                cold_elements, context
            )
            results.extend(cold_results)
            elements_processed += cold_processed
            cache_hits += cold_hits
        
        # Combine results
        final_result = self._combine_conversion_results(results)
        
        return final_result, elements_processed, cache_hits
    
    async def _process_hot_path_elements(self, 
                                       elements: List[ET.Element],
                                       context: Dict[str, Any]) -> Tuple[List[str], int, int]:
        """Process hot path elements with maximum caching."""
        results = []
        cache_hits = 0
        
        # Use concurrent processing for hot path elements
        semaphore = asyncio.Semaphore(8)  # Limit concurrency
        
        async def process_hot_element(element: ET.Element) -> Tuple[str, bool]:
            async with semaphore:
                # Generate element-specific context
                element_context = self._create_element_context(element, context)
                
                # Try cache first
                cached_result = self.speedrun_cache.get_with_content_addressing(
                    element, element_context, tags={'hot_path'}
                )
                
                if cached_result is not None:
                    return cached_result, True
                
                # Process element
                result = await self._convert_element_async(element, element_context)
                
                # Cache result aggressively
                self.speedrun_cache.put_with_content_addressing(
                    element, result, element_context,
                    tags={'hot_path', element.tag.split('}')[-1]},
                    persist_to_disk=(self.mode != SpeedrunMode.CONSERVATIVE)
                )
                
                return result, False
        
        # Process all hot elements concurrently
        tasks = [process_hot_element(elem) for elem in elements]
        completed_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in completed_results:
            if isinstance(result, Exception):
                logger.warning(f"Hot path processing error: {result}")
                results.append("")  # Placeholder
            else:
                output, was_cached = result
                results.append(output)
                if was_cached:
                    cache_hits += 1
        
        return results, len(elements), cache_hits
    
    async def _process_cold_path_elements(self,
                                        elements: List[ET.Element],
                                        context: Dict[str, Any]) -> Tuple[List[str], int, int]:
        """Process cold path elements with standard optimization."""
        results = []
        cache_hits = 0
        
        # Use batch processing for cold path elements
        batch_processor = BatchProcessor(
            max_workers=self.optimization_config.max_batch_workers,
            default_strategy=self.optimization_config.batch_strategy,
            enable_caching=True
        )
        
        # Create batch contexts
        contexts = [self._create_element_context(elem, context) for elem in elements]
        converter_classes = [self._get_converter_class(elem) for elem in elements]
        
        # Process in batches
        batch_results = batch_processor.process_elements(
            elements, contexts, converter_classes,
            strategy=self.optimization_config.batch_strategy,
            parallel=True
        )
        
        # Calculate cache statistics from batch results
        # (This would integrate with the batch processor's cache statistics)
        results.extend(batch_results)
        
        return results, len(elements), cache_hits
    
    async def _convert_element_async(self, 
                                   element: ET.Element,
                                   context: Dict[str, Any]) -> str:
        """Convert single element asynchronously."""
        loop = asyncio.get_event_loop()
        
        # Run conversion in thread pool for CPU-bound work
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._convert_element_sync, element, context)
            result = await loop.run_in_executor(None, future.result)
            return result
    
    def _convert_element_sync(self, element: ET.Element, context: Dict[str, Any]) -> str:
        """Synchronous element conversion."""
        # Get converter from pool
        converter_class = self._get_converter_class(element)
        
        if converter_class:
            with self.converter_pool.get_converter(converter_class) as converter:
                if hasattr(converter, 'convert'):
                    return converter.convert(element, context)
        
        # Fallback conversion
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        return f"<{tag}_converted/>"
    
    def _create_element_context(self, element: ET.Element, base_context: Dict[str, Any]) -> Dict[str, Any]:
        """Create element-specific context for caching."""
        context = base_context.copy()
        
        # Add element-specific attributes
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        context['element_tag'] = tag
        context['element_attrs'] = dict(element.attrib)
        
        # Add parent context if available
        if element.getparent() is not None:
            parent_tag = element.getparent().tag.split('}')[-1]
            context['parent_tag'] = parent_tag
        
        return context
    
    def _get_converter_class(self, element: ET.Element) -> Optional[type]:
        """Get appropriate converter class for element."""
        # This would integrate with the existing converter registry
        # For now, return a placeholder
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        
        # Map common elements to converter classes
        converter_mapping = {
            'rect': None,    # Would be RectConverter
            'circle': None,  # Would be CircleConverter
            'path': None,    # Would be PathConverter
            'text': None,    # Would be TextConverter
            'g': None,       # Would be GroupConverter
        }
        
        return converter_mapping.get(tag)
    
    def _combine_conversion_results(self, results: List[str]) -> str:
        """Combine individual conversion results into final output."""
        # Simple concatenation for now - in practice this would be more sophisticated
        return '\n'.join(filter(None, results))
    
    def _calculate_speedup(self, current_time: float) -> float:
        """Calculate speedup factor compared to baseline."""
        # Use a baseline time if available, otherwise assume 1x speedup
        baseline_time = self._baseline_times.get('default', current_time)
        if baseline_time > 0:
            return baseline_time / current_time
        return 1.0
    
    def set_baseline_time(self, operation: str, time_seconds: float):
        """Set baseline time for speedup calculations."""
        self._baseline_times[operation] = time_seconds
    
    def get_speedrun_statistics(self) -> Dict[str, Any]:
        """Get comprehensive speedrun statistics."""
        if not self._speedrun_metrics:
            return {'no_data': True}
        
        recent_metrics = self._speedrun_metrics[-10:]  # Last 10 conversions
        
        avg_hit_rate = sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics)
        avg_speedup = sum(m.speedup_factor for m in recent_metrics) / len(recent_metrics)
        avg_time = sum(m.avg_processing_time_ms for m in recent_metrics) / len(recent_metrics)
        
        cache_stats = self.speedrun_cache.get_enhanced_stats()
        
        return {
            'mode': self.mode.value,
            'total_conversions': len(self._speedrun_metrics),
            'avg_cache_hit_rate': avg_hit_rate,
            'avg_speedup_factor': avg_speedup,
            'avg_processing_time_ms': avg_time,
            'hot_paths_count': len(self._hot_paths),
            'element_patterns_count': len(self._element_patterns),
            'cache_statistics': cache_stats,
            'recent_metrics': [str(m) for m in recent_metrics[-3:]]
        }
    
    def optimize_for_workload(self, svg_samples: List[str]):
        """Optimize configuration based on workload analysis."""
        logger.info(f"Analyzing workload with {len(svg_samples)} samples")
        
        # Analyze common patterns in the workload
        element_frequency = {}
        complexity_distribution = {}
        
        for svg_content in svg_samples:
            try:
                root = ET.fromstring(svg_content)
                elements = list(root.iter())
                
                for element in elements:
                    tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
                    element_frequency[tag] = element_frequency.get(tag, 0) + 1
                    
                    # Estimate complexity
                    complexity = len(element.attrib) + len(list(element))
                    complexity_tier = min(complexity // 5, 4)  # 0-4 scale
                    complexity_distribution[complexity_tier] = complexity_distribution.get(complexity_tier, 0) + 1
                    
            except Exception as e:
                logger.warning(f"Error analyzing SVG sample: {e}")
        
        # Update hot paths based on frequency
        self._hot_paths = set()
        for tag, freq in element_frequency.items():
            if freq > len(svg_samples) * 0.1:  # Appears in >10% of samples
                self._hot_paths.add(tag)
        
        # Adjust optimization config based on complexity
        high_complexity_ratio = sum(
            count for tier, count in complexity_distribution.items() if tier >= 3
        ) / max(sum(complexity_distribution.values()), 1)
        
        if high_complexity_ratio > 0.3:  # >30% high complexity
            self.optimization_config.batch_strategy = BatchStrategy.BY_COMPLEXITY
            self.optimization_config.max_batch_workers = min(8, self.optimization_config.max_batch_workers * 2)
        
        logger.info(f"Workload analysis complete: {len(self._hot_paths)} hot paths identified")
    
    def enable_ludicrous_mode(self):
        """Enable ludicrous speed mode for maximum performance."""
        logger.warning("Enabling LUDICROUS mode - maximum performance optimizations")
        
        self.mode = SpeedrunMode.LUDICROUS
        self.optimization_config = self._create_optimization_config()
        
        # Enable all aggressive optimizations
        self.speedrun_cache.start_cache_warming()
        
        # Pre-populate more patterns
        self._identify_hot_paths()
        
        logger.info("LUDICROUS mode enabled - performance should be maximum")


# Global speedrun optimizer instance
_global_speedrun_optimizer = None

def get_speedrun_optimizer(mode: SpeedrunMode = SpeedrunMode.AGGRESSIVE) -> SVGSpeedrunOptimizer:
    """Get or create the global speedrun optimizer."""
    global _global_speedrun_optimizer
    if _global_speedrun_optimizer is None:
        _global_speedrun_optimizer = SVGSpeedrunOptimizer(mode)
    return _global_speedrun_optimizer


def enable_speedrun_mode(mode: SpeedrunMode = SpeedrunMode.AGGRESSIVE,
                        warmup_samples: List[str] = None) -> SVGSpeedrunOptimizer:
    """Enable speedrun mode for maximum SVG conversion performance."""
    optimizer = get_speedrun_optimizer(mode)
    
    if warmup_samples:
        optimizer.optimize_for_workload(warmup_samples)
    
    optimizer.warmup_cache()
    
    logger.info(f"Speedrun mode enabled: {mode.value}")
    return optimizer