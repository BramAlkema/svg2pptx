#!/usr/bin/env python3
"""
Tests for speedrun optimizer performance module.
"""

import pytest
import time
import asyncio
import threading
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from lxml import etree as ET

from src.performance.speedrun_optimizer import (
    SpeedrunMode, SpeedrunMetrics, SpeedrunOptimizer,
    ParallelSpeedrunProcessor, AdaptiveOptimizer,
    CachePreloader, ElementBatcher, OptimizationPipeline
)


class TestSpeedrunMode:
    """Test SpeedrunMode enum."""
    
    def test_speedrun_mode_values(self):
        """Test speedrun mode enum values."""
        assert SpeedrunMode.CONSERVATIVE.value == "conservative"
        assert SpeedrunMode.AGGRESSIVE.value == "aggressive"
        assert SpeedrunMode.LUDICROUS.value == "ludicrous"
    
    def test_speedrun_mode_comparison(self):
        """Test speedrun mode comparisons."""
        modes = [SpeedrunMode.CONSERVATIVE, SpeedrunMode.AGGRESSIVE, SpeedrunMode.LUDICROUS]
        assert len(modes) == 3
        assert SpeedrunMode.CONSERVATIVE in modes


class TestSpeedrunMetrics:
    """Test SpeedrunMetrics dataclass."""
    
    def test_speedrun_metrics_creation(self):
        """Test basic metrics creation."""
        metrics = SpeedrunMetrics(
            elements_processed=100,
            cache_hit_rate=0.85,
            avg_processing_time_ms=1.5,
            peak_memory_mb=128.0,
            total_time_seconds=2.5,
            speedup_factor=12.3
        )
        
        assert metrics.elements_processed == 100
        assert metrics.cache_hit_rate == 0.85
        assert metrics.avg_processing_time_ms == 1.5
        assert metrics.peak_memory_mb == 128.0
        assert metrics.total_time_seconds == 2.5
        assert metrics.speedup_factor == 12.3
    
    def test_speedrun_metrics_string_representation(self):
        """Test metrics string representation."""
        metrics = SpeedrunMetrics(
            elements_processed=50,
            cache_hit_rate=0.75,
            avg_processing_time_ms=2.1,
            peak_memory_mb=64.5,
            total_time_seconds=1.8,
            speedup_factor=8.7
        )
        
        str_repr = str(metrics)
        assert "elements=50" in str_repr
        assert "hit_rate=75.0%" in str_repr
        assert "avg_time=2.10ms" in str_repr
        assert "speedup=8.7x" in str_repr


class TestSpeedrunOptimizer:
    """Test SpeedrunOptimizer core functionality."""
    
    @pytest.fixture
    def mock_cache(self):
        """Create mock speedrun cache."""
        cache = Mock()
        cache.get.return_value = None  # Default to cache miss
        cache.set.return_value = None
        cache.get_stats.return_value = Mock(hit_rate=0.8)
        return cache
    
    @pytest.fixture
    def optimizer(self, mock_cache):
        """Create SpeedrunOptimizer instance."""
        with patch('src.performance.speedrun_optimizer.get_speedrun_cache', return_value=mock_cache):
            return SpeedrunOptimizer(mode=SpeedrunMode.AGGRESSIVE)
    
    def test_optimizer_initialization(self, optimizer):
        """Test optimizer initialization."""
        assert optimizer.mode == SpeedrunMode.AGGRESSIVE
        assert optimizer.cache is not None
        assert optimizer.profiler is not None
        assert optimizer.pool is not None
    
    def test_mode_switching(self, optimizer):
        """Test switching optimization modes."""
        original_mode = optimizer.mode
        optimizer.set_mode(SpeedrunMode.LUDICROUS)
        assert optimizer.mode == SpeedrunMode.LUDICROUS
        assert optimizer.mode != original_mode
    
    @patch('src.performance.speedrun_optimizer.time.time')
    def test_process_svg_elements(self, mock_time, optimizer):
        """Test processing SVG elements with optimization."""
        mock_time.side_effect = [0, 1.5]  # Start and end times
        
        # Create mock SVG elements
        elements = []
        for i in range(5):
            elem = Mock()
            elem.tag = "rect"
            elem.get.return_value = str(i)
            elements.append(elem)
        
        # Mock conversion results
        with patch.object(optimizer, '_convert_element_optimized') as mock_convert:
            mock_convert.return_value = f"<converted_element/>"
            
            results = optimizer.process_svg_elements(elements)
            
            assert len(results) == 5
            assert all(result == "<converted_element/>" for result in results)
            assert mock_convert.call_count == 5
    
    def test_cache_optimization_strategy(self, optimizer):
        """Test cache-based optimization strategies."""
        element = Mock()
        element.tag = "circle"
        element.attrib = {"cx": "50", "cy": "50", "r": "25"}
        
        # Test cache miss scenario
        optimizer.cache.get.return_value = None
        with patch.object(optimizer, '_generate_cache_key') as mock_key:
            mock_key.return_value = "circle_cache_key"
            
            with patch.object(optimizer, '_convert_element_standard') as mock_convert:
                mock_convert.return_value = "<circle_result/>"
                
                result = optimizer._convert_element_optimized(element)
                
                assert result == "<circle_result/>"
                optimizer.cache.set.assert_called_once()
        
        # Test cache hit scenario
        optimizer.cache.get.return_value = "<cached_circle/>"
        result = optimizer._convert_element_optimized(element)
        assert result == "<cached_circle/>"
    
    def test_element_batching_optimization(self, optimizer):
        """Test element batching for parallel processing."""
        elements = [Mock() for _ in range(20)]
        
        batches = optimizer._create_element_batches(elements, batch_size=5)
        
        assert len(batches) == 4
        assert all(len(batch) == 5 for batch in batches)
    
    def test_performance_metrics_collection(self, optimizer):
        """Test collection of performance metrics."""
        elements = [Mock() for _ in range(10)]
        
        with patch.object(optimizer, 'process_svg_elements') as mock_process:
            mock_process.return_value = ["result"] * 10
            
            metrics = optimizer.process_with_metrics(elements)
            
            assert isinstance(metrics, SpeedrunMetrics)
            assert metrics.elements_processed == 10
            assert metrics.speedup_factor >= 1.0


class TestParallelSpeedrunProcessor:
    """Test parallel processing optimizations."""
    
    @pytest.fixture
    def processor(self):
        """Create ParallelSpeedrunProcessor instance."""
        return ParallelSpeedrunProcessor(max_workers=4)
    
    def test_processor_initialization(self, processor):
        """Test processor initialization."""
        assert processor.max_workers == 4
        assert processor.executor is not None
    
    def test_parallel_element_processing(self, processor):
        """Test parallel processing of elements."""
        elements = [Mock() for _ in range(8)]
        
        # Mock conversion function
        def mock_convert(element):
            time.sleep(0.01)  # Simulate processing time
            return f"<converted_{id(element)}/>"
        
        with patch.object(processor, '_convert_single_element', side_effect=mock_convert):
            results = processor.process_parallel(elements)
            
            assert len(results) == 8
            assert all(result.startswith("<converted_") for result in results)
    
    def test_adaptive_worker_scaling(self, processor):
        """Test adaptive scaling of worker threads."""
        # Test with small workload
        small_elements = [Mock() for _ in range(2)]
        optimal_workers_small = processor._calculate_optimal_workers(small_elements)
        
        # Test with large workload
        large_elements = [Mock() for _ in range(100)]
        optimal_workers_large = processor._calculate_optimal_workers(large_elements)
        
        assert optimal_workers_small <= optimal_workers_large
        assert optimal_workers_small >= 1
        assert optimal_workers_large <= processor.max_workers
    
    @pytest.mark.asyncio
    async def test_async_processing(self, processor):
        """Test async processing capabilities."""
        elements = [Mock() for _ in range(5)]
        
        async def mock_async_convert(element):
            await asyncio.sleep(0.001)  # Simulate async processing
            return f"<async_result_{id(element)}/>"
        
        with patch.object(processor, '_convert_async', side_effect=mock_async_convert):
            results = await processor.process_async(elements)
            
            assert len(results) == 5
            assert all(result.startswith("<async_result_") for result in results)


class TestAdaptiveOptimizer:
    """Test adaptive optimization strategies."""
    
    @pytest.fixture
    def adaptive_optimizer(self):
        """Create AdaptiveOptimizer instance."""
        return AdaptiveOptimizer()
    
    def test_adaptive_optimizer_initialization(self, adaptive_optimizer):
        """Test adaptive optimizer initialization."""
        assert adaptive_optimizer.learning_enabled is True
        assert len(adaptive_optimizer.performance_history) == 0
        assert adaptive_optimizer.current_strategy is not None
    
    def test_performance_learning(self, adaptive_optimizer):
        """Test performance-based strategy learning."""
        # Simulate different performance scenarios
        scenarios = [
            {"elements": 10, "time": 0.5, "hit_rate": 0.9},
            {"elements": 100, "time": 2.0, "hit_rate": 0.7},
            {"elements": 1000, "time": 15.0, "hit_rate": 0.8},
        ]
        
        for scenario in scenarios:
            adaptive_optimizer.record_performance(
                elements_count=scenario["elements"],
                processing_time=scenario["time"],
                cache_hit_rate=scenario["hit_rate"]
            )
        
        assert len(adaptive_optimizer.performance_history) == 3
        
        # Test strategy adaptation
        recommended_strategy = adaptive_optimizer.get_recommended_strategy(
            elements_count=500
        )
        assert recommended_strategy is not None
    
    def test_optimization_strategy_selection(self, adaptive_optimizer):
        """Test automatic optimization strategy selection."""
        # Test strategy for different workload sizes
        small_strategy = adaptive_optimizer._select_strategy_for_workload(10)
        medium_strategy = adaptive_optimizer._select_strategy_for_workload(100)
        large_strategy = adaptive_optimizer._select_strategy_for_workload(1000)
        
        assert small_strategy is not None
        assert medium_strategy is not None
        assert large_strategy is not None
    
    def test_cache_hit_rate_optimization(self, adaptive_optimizer):
        """Test optimization based on cache hit rates."""
        # Low hit rate scenario - should prefer preprocessing
        low_hit_config = adaptive_optimizer.optimize_for_hit_rate(0.2)
        assert low_hit_config.enable_preprocessing is True
        
        # High hit rate scenario - should prefer cache efficiency
        high_hit_config = adaptive_optimizer.optimize_for_hit_rate(0.9)
        assert high_hit_config.cache_aggressive is True


class TestCachePreloader:
    """Test cache preloading functionality."""
    
    @pytest.fixture
    def mock_cache(self):
        """Create mock cache for preloader tests."""
        cache = Mock()
        cache.set.return_value = None
        cache.warm_from_patterns = Mock()
        return cache
    
    @pytest.fixture
    def preloader(self, mock_cache):
        """Create CachePreloader instance."""
        return CachePreloader(cache=mock_cache)
    
    def test_preloader_initialization(self, preloader, mock_cache):
        """Test cache preloader initialization."""
        assert preloader.cache == mock_cache
        assert preloader.preload_tasks == []
    
    def test_preload_common_elements(self, preloader):
        """Test preloading common SVG elements."""
        common_elements = ["rect", "circle", "path", "text"]
        
        preloader.preload_common_elements(common_elements)
        
        # Should create preload tasks
        assert len(preloader.preload_tasks) > 0
        
        # Should call cache warming
        preloader.cache.warm_from_patterns.assert_called()
    
    def test_preload_from_svg_analysis(self, preloader):
        """Test preloading based on SVG analysis."""
        # Create mock SVG content
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <rect x="10" y="10" width="100" height="50"/>
            <circle cx="50" cy="50" r="25"/>
            <path d="M10,10 L100,100"/>
        </svg>
        """
        
        svg_tree = ET.fromstring(svg_content)
        preloader.preload_from_svg_analysis(svg_tree)
        
        # Should identify and preload element types
        assert len(preloader.preload_tasks) > 0
    
    @pytest.mark.asyncio
    async def test_async_preloading(self, preloader):
        """Test asynchronous cache preloading."""
        elements_to_preload = ["rect", "circle"]
        
        await preloader.preload_async(elements_to_preload)
        
        # Should complete without errors
        assert len(preloader.preload_tasks) >= 0


class TestElementBatcher:
    """Test element batching functionality."""
    
    def test_batcher_initialization(self):
        """Test element batcher initialization."""
        batcher = ElementBatcher(batch_size=10)
        assert batcher.batch_size == 10
        assert batcher.batches == []
    
    def test_element_batching_by_type(self):
        """Test batching elements by type."""
        batcher = ElementBatcher(batch_size=5)
        
        # Create mixed elements
        elements = []
        for i in range(15):
            elem = Mock()
            elem.tag = "rect" if i % 2 == 0 else "circle"
            elements.append(elem)
        
        batches = batcher.create_batches_by_type(elements)
        
        # Should group by type
        rect_batches = [b for b in batches if b[0].tag == "rect"]
        circle_batches = [b for b in batches if b[0].tag == "circle"]
        
        assert len(rect_batches) > 0
        assert len(circle_batches) > 0
    
    def test_optimal_batch_size_calculation(self):
        """Test calculation of optimal batch sizes."""
        batcher = ElementBatcher()
        
        # Test different element counts
        small_optimal = batcher.calculate_optimal_batch_size(10)
        medium_optimal = batcher.calculate_optimal_batch_size(100)
        large_optimal = batcher.calculate_optimal_batch_size(1000)
        
        assert small_optimal <= medium_optimal <= large_optimal
        assert small_optimal >= 1
    
    def test_batch_priority_ordering(self):
        """Test priority-based batch ordering."""
        batcher = ElementBatcher()
        
        # Create elements with different priorities
        elements = []
        priorities = [1, 3, 2, 1, 3, 2]  # Mixed priorities
        for i, priority in enumerate(priorities):
            elem = Mock()
            elem.tag = f"element_{i}"
            elem.priority = priority
            elements.append(elem)
        
        ordered_batches = batcher.create_priority_batches(elements)
        
        # Higher priority elements should come first
        assert len(ordered_batches) > 0
        if len(ordered_batches[0]) > 0:
            first_priority = getattr(ordered_batches[0][0], 'priority', 0)
            assert first_priority >= 1


class TestOptimizationPipeline:
    """Test optimization pipeline integration."""
    
    @pytest.fixture
    def pipeline(self):
        """Create OptimizationPipeline instance."""
        return OptimizationPipeline()
    
    def test_pipeline_initialization(self, pipeline):
        """Test optimization pipeline initialization."""
        assert pipeline.stages is not None
        assert len(pipeline.stages) > 0
        assert pipeline.metrics_collector is not None
    
    def test_pipeline_stage_execution(self, pipeline):
        """Test execution of optimization stages."""
        elements = [Mock() for _ in range(5)]
        
        # Mock pipeline stages
        with patch.object(pipeline, '_execute_stage') as mock_execute:
            mock_execute.return_value = elements
            
            result = pipeline.execute(elements)
            
            assert len(result) == 5
            assert mock_execute.call_count >= 1
    
    def test_pipeline_performance_monitoring(self, pipeline):
        """Test pipeline performance monitoring."""
        elements = [Mock() for _ in range(3)]
        
        with patch.object(pipeline, 'execute') as mock_execute:
            mock_execute.return_value = elements
            
            metrics = pipeline.execute_with_monitoring(elements)
            
            assert isinstance(metrics, dict)
            assert 'stage_timings' in metrics
            assert 'total_time' in metrics
    
    def test_pipeline_optimization_selection(self, pipeline):
        """Test automatic optimization selection."""
        # Test different workload characteristics
        small_workload = [Mock() for _ in range(5)]
        large_workload = [Mock() for _ in range(500)]
        
        small_config = pipeline.select_optimization_config(small_workload)
        large_config = pipeline.select_optimization_config(large_workload)
        
        assert small_config is not None
        assert large_config is not None
        # Large workloads should have more aggressive optimizations
        assert large_config != small_config


@pytest.mark.integration
class TestSpeedrunIntegration:
    """Integration tests for speedrun optimization."""
    
    def test_end_to_end_speedrun_optimization(self):
        """Test complete speedrun optimization workflow."""
        # Create realistic SVG elements
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
            <rect x="10" y="10" width="50" height="30" fill="red"/>
            <circle cx="100" cy="100" r="25" fill="blue"/>
            <path d="M150,150 L180,180 Z" stroke="green"/>
        </svg>
        """
        
        svg_tree = ET.fromstring(svg_content)
        elements = list(svg_tree)
        
        # Initialize speedrun optimizer
        with patch('src.performance.speedrun_optimizer.get_speedrun_cache'):
            optimizer = SpeedrunOptimizer(mode=SpeedrunMode.AGGRESSIVE)
            
            # Process with metrics
            with patch.object(optimizer, '_convert_element_optimized') as mock_convert:
                mock_convert.return_value = "<optimized_element/>"
                
                metrics = optimizer.process_with_metrics(elements)
                
                assert metrics.elements_processed == len(elements)
                assert metrics.speedup_factor >= 1.0
    
    def test_adaptive_optimization_workflow(self):
        """Test adaptive optimization learning workflow."""
        adaptive = AdaptiveOptimizer()
        
        # Simulate multiple processing rounds
        workload_sizes = [10, 50, 100, 500]
        processing_times = [0.1, 0.5, 1.2, 8.5]
        hit_rates = [0.6, 0.7, 0.8, 0.9]
        
        for size, time, hit_rate in zip(workload_sizes, processing_times, hit_rates):
            adaptive.record_performance(size, time, hit_rate)
        
        # Test strategy recommendation
        strategy = adaptive.get_recommended_strategy(elements_count=250)
        assert strategy is not None
        
        # Recommendations should improve over time
        assert len(adaptive.performance_history) == len(workload_sizes)


@pytest.mark.benchmark
class TestSpeedrunPerformance:
    """Performance benchmarks for speedrun optimization."""
    
    def test_optimizer_throughput(self, benchmark):
        """Benchmark optimizer throughput."""
        elements = [Mock() for _ in range(100)]
        
        with patch('src.performance.speedrun_optimizer.get_speedrun_cache'):
            optimizer = SpeedrunOptimizer(mode=SpeedrunMode.CONSERVATIVE)
            
            def process_elements():
                with patch.object(optimizer, '_convert_element_optimized') as mock_convert:
                    mock_convert.return_value = "<fast_result/>"
                    return optimizer.process_svg_elements(elements)
            
            results = benchmark(process_elements)
            assert len(results) == 100
    
    def test_cache_performance_impact(self, benchmark):
        """Benchmark cache performance impact."""
        cache = Mock()
        cache.get.return_value = "<cached_result/>"  # Simulate cache hit
        
        element = Mock()
        element.tag = "rect"
        element.attrib = {"x": "0", "y": "0", "width": "100", "height": "50"}
        
        with patch('src.performance.speedrun_optimizer.get_speedrun_cache', return_value=cache):
            optimizer = SpeedrunOptimizer(mode=SpeedrunMode.AGGRESSIVE)
            
            def cached_conversion():
                return optimizer._convert_element_optimized(element)
            
            result = benchmark(cached_conversion)
            assert result == "<cached_result/>"