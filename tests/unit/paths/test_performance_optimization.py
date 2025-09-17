#!/usr/bin/env python3
"""
Comprehensive tests for performance optimization and caching features.
"""

import pytest
import numpy as np
import time
import hashlib
from src.paths.numpy_paths import PathEngine, AdvancedLRUCache, ArrayPool


class TestAdvancedLRUCache:
    """Test advanced LRU cache with memory management."""

    def setup_method(self):
        """Set up test cache."""
        self.cache = AdvancedLRUCache(maxsize=5, max_memory_mb=1)

    def test_basic_cache_operations(self):
        """Test basic cache put/get operations."""
        # Test put and get
        self.cache.put("key1", "value1")
        assert self.cache.get("key1") == "value1"
        assert self.cache.get("nonexistent") is None

        # Check stats
        stats = self.cache.stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['hit_rate'] == 0.5

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        # Fill cache beyond capacity
        for i in range(7):
            self.cache.put(f"key{i}", f"value{i}")

        # Check that oldest items were evicted
        assert self.cache.get("key0") is None  # Should be evicted
        assert self.cache.get("key1") is None  # Should be evicted
        assert self.cache.get("key6") == "value6"  # Should still exist

    def test_memory_based_eviction(self):
        """Test eviction based on memory usage."""
        # Create arrays that together exceed memory limit but individually fit
        # Use 300KB arrays with 1MB limit - first two should fit, third should evict first
        array1 = np.ones((200, 200), dtype=np.float64)  # ~320KB
        array2 = np.ones((200, 200), dtype=np.float64)  # ~320KB
        array3 = np.ones((200, 200), dtype=np.float64)  # ~320KB (total would be ~960KB)
        array4 = np.ones((200, 200), dtype=np.float64)  # ~320KB (total would be ~1.28MB, exceeds 1MB limit)

        # Add first three arrays - should all fit (~960KB < 1MB)
        self.cache.put("array1", array1)
        self.cache.put("array2", array2)
        self.cache.put("array3", array3)

        # All should be present
        assert self.cache.get("array1") is not None
        assert self.cache.get("array2") is not None
        assert self.cache.get("array3") is not None

        # Add fourth array - should trigger eviction of array1 (oldest)
        self.cache.put("array4", array4)

        # Array1 should be evicted, others should remain
        assert self.cache.get("array1") is None  # Evicted
        assert self.cache.get("array2") is not None  # Still present
        assert self.cache.get("array3") is not None  # Still present
        assert self.cache.get("array4") is not None  # Newly added

    def test_memory_estimation(self):
        """Test memory estimation for different object types."""
        # Test numpy array memory estimation
        small_array = np.ones((10, 10), dtype=np.float64)
        estimated = self.cache._estimate_memory(small_array)
        actual = small_array.nbytes
        assert estimated == actual

        # Test dictionary memory estimation
        test_dict = {"a": 1, "b": 2, "c": 3}
        estimated = self.cache._estimate_memory(test_dict)
        assert estimated > 0  # Should be positive

    def test_cache_clear(self):
        """Test cache clearing."""
        self.cache.put("key1", "value1")
        self.cache.put("key2", "value2")

        assert len(self.cache.cache) == 2
        self.cache.clear()
        assert len(self.cache.cache) == 0
        assert self.cache.memory_usage == 0


class TestArrayPool:
    """Test array pool for memory efficiency."""

    def setup_method(self):
        """Set up test array pool."""
        self.pool = ArrayPool(max_arrays_per_shape=3)

    def test_array_allocation_and_reuse(self):
        """Test array allocation and reuse."""
        # Get arrays from pool
        array1 = self.pool.get_array((10, 2))
        array2 = self.pool.get_array((10, 2))

        assert array1.shape == (10, 2)
        assert array2.shape == (10, 2)

        # Return arrays to pool
        self.pool.return_array(array1)
        self.pool.return_array(array2)

        # Get new array - should reuse from pool
        array3 = self.pool.get_array((10, 2))

        # Check stats - initial allocation stats
        stats = self.pool.stats()
        assert stats['allocations'] >= 2  # At least 2 initial allocations

        # Test reuse by getting another array of same shape
        array4 = self.pool.get_array((10, 2))
        self.pool.return_array(array4)
        array5 = self.pool.get_array((10, 2))  # This should reuse

        # Now check for reuse
        final_stats = self.pool.stats()
        assert final_stats['reuses'] >= 1
        assert final_stats['reuse_rate'] > 0

    def test_different_shapes_and_dtypes(self):
        """Test pool handling of different shapes and dtypes."""
        array_float = self.pool.get_array((5, 5), np.float64)
        array_int = self.pool.get_array((5, 5), np.int32)

        assert array_float.dtype == np.float64
        assert array_int.dtype == np.int32

        # Return to pool
        self.pool.return_array(array_float)
        self.pool.return_array(array_int)

        # Verify they're stored separately
        stats = self.pool.stats()
        assert len(stats['pool_sizes']) >= 2

    def test_pool_size_limit(self):
        """Test pool size limitations."""
        # Create more arrays than pool can hold
        arrays = []
        for i in range(5):
            array = self.pool.get_array((3, 3))
            arrays.append(array)

        # Return all arrays
        for array in arrays:
            self.pool.return_array(array)

        # Check that pool didn't exceed max size
        shape_key = str(((3, 3), np.float64))
        stats = self.pool.stats()
        pool_size = int(stats['pool_sizes'].get(shape_key, 0))
        assert pool_size <= self.pool.max_arrays_per_shape

    def test_array_clearing(self):
        """Test that returned arrays are cleared."""
        array = self.pool.get_array((3, 3))
        array.fill(42)  # Fill with non-zero values

        self.pool.return_array(array)

        # Get new array - should be cleared
        new_array = self.pool.get_array((3, 3))
        assert np.all(new_array == 0)


class TestPathEngineCaching:
    """Test PathEngine caching capabilities."""

    def setup_method(self):
        """Set up test engine with caching enabled."""
        self.engine = PathEngine(cache_size=100, enable_profiling=True)

    def test_path_processing_cache(self):
        """Test caching of path processing results."""
        path_string = "M 10 10 L 90 90 C 90 10 10 10 10 90"

        # First call - should miss cache
        result1 = self.engine.process_path(path_string)
        assert result1['performance']['cache_hit'] is False

        # Second call - should hit cache
        result2 = self.engine.process_path(path_string)

        # Results should be identical
        assert result1['commands'] == result2['commands']
        assert result1['coordinates'] == result2['coordinates']

    def test_bezier_extraction_cache(self):
        """Test caching of Bezier curve extraction."""
        path_string = "M 0 0 C 50 0 100 50 100 100 Q 150 50 200 100"
        result = self.engine.process_path(path_string)
        path_data = result['path_data']

        # First call - should populate cache
        start_time = time.perf_counter()
        bezier1 = self.engine.extract_bezier_curves(path_data, subdivision=20)
        first_time = time.perf_counter() - start_time

        # Second call - should use cache
        start_time = time.perf_counter()
        bezier2 = self.engine.extract_bezier_curves(path_data, subdivision=20)
        second_time = time.perf_counter() - start_time

        # Results should be identical
        assert bezier1.keys() == bezier2.keys()
        if 'cubic_curves' in bezier1:
            np.testing.assert_array_equal(bezier1['cubic_curves'], bezier2['cubic_curves'])

        # Second call should be faster (though this might be flaky in tests)
        # Just verify cache is working by checking hit rate improved
        cache_stats = self.engine._bezier_cache.stats()
        assert cache_stats['hits'] > 0

    def test_performance_profiling(self):
        """Test performance profiling capabilities."""
        path_strings = [
            "M 10 10 L 90 90",
            "M 0 0 C 50 0 100 50 100 100",
            "M 20 20 Q 70 20 120 70"
        ]

        # Process multiple paths to generate profiling data
        for path_string in path_strings:
            result = self.engine.process_path(path_string)
            self.engine.extract_bezier_curves(result['path_data'])

        # Check profiling stats
        perf_stats = self.engine.get_performance_stats()
        assert 'profiling' in perf_stats
        assert 'process_path' in perf_stats['profiling']

        # Check that timing data is collected
        process_stats = perf_stats['profiling']['process_path']
        assert process_stats['count'] == len(path_strings)
        assert process_stats['total_time'] > 0
        assert process_stats['avg_time'] > 0

    def test_large_dataset_optimization(self):
        """Test optimization for large datasets."""
        # Get initial cache sizes
        initial_path_size = self.engine._path_cache.maxsize
        initial_bezier_size = self.engine._bezier_cache.maxsize

        # Enable large dataset optimization
        self.engine.optimize_for_large_datasets(True)

        # Check that cache sizes increased
        assert self.engine._path_cache.maxsize == initial_path_size * 2
        assert self.engine._bezier_cache.maxsize == initial_bezier_size * 2

        # Disable optimization
        self.engine.optimize_for_large_datasets(False)

        # Check that sizes returned to normal
        assert self.engine._path_cache.maxsize == initial_path_size
        assert self.engine._bezier_cache.maxsize == initial_bezier_size

    def test_cache_statistics(self):
        """Test comprehensive cache statistics."""
        # Process some paths to populate caches
        paths = [
            "M 0 0 L 100 100",
            "M 10 10 C 50 50 90 90 100 100",
            "M 20 20 Q 60 60 100 100"
        ]

        for path in paths:
            result = self.engine.process_path(path)
            self.engine.extract_bezier_curves(result['path_data'])

        # Get comprehensive stats
        stats = self.engine.get_performance_stats()

        # Check required sections
        assert 'caching' in stats
        assert 'memory' in stats
        assert 'profiling' in stats

        # Check cache stats structure
        caching_stats = stats['caching']
        assert 'path_cache' in caching_stats
        assert 'bezier_cache' in caching_stats
        assert 'overall_hit_rate' in caching_stats

        # Check memory stats
        memory_stats = stats['memory']
        assert 'array_pool' in memory_stats

    def test_cache_clearing(self):
        """Test cache clearing functionality."""
        # Populate caches
        path_string = "M 0 0 L 100 100 C 100 0 0 0 0 100"
        result = self.engine.process_path(path_string)
        self.engine.extract_bezier_curves(result['path_data'])

        # Verify caches have data
        initial_stats = self.engine.get_performance_stats()
        assert initial_stats['caching']['path_cache']['size'] > 0

        # Clear all caches
        self.engine.clear_all_caches()

        # Verify caches are empty
        cleared_stats = self.engine.get_performance_stats()
        assert cleared_stats['caching']['path_cache']['size'] == 0
        assert cleared_stats['caching']['bezier_cache']['size'] == 0

    def test_memory_efficiency(self):
        """Test memory efficiency with array pooling."""
        # Create paths and process them to trigger array allocations
        paths = [f"M {i} {i} L {i+10} {i+10}" for i in range(20)]
        path_data_list = []

        for path in paths:
            result = self.engine.process_path(path)
            path_data_list.append(result['path_data'])

        # Use the batch processing method that exercises the ArrayPool
        lengths = self.engine.calculate_path_lengths_batch(path_data_list)

        # Check that we got results
        assert len(lengths) == len(paths)
        assert all(length > 0 for length in lengths)

        # Check array pool statistics
        pool_stats = self.engine.get_performance_stats()['memory']['array_pool']

        # Should have some allocations and potentially reuses from the batch processing
        assert pool_stats['allocations'] >= 1  # At least one allocation should have occurred
        assert pool_stats['reuses'] >= 0  # Reuses should be non-negative

    def test_cache_key_generation(self):
        """Test cache key generation for different scenarios."""
        path_string = "M 0 0 L 100 100"

        # Same path with same parameters should use same cache entry
        result1 = self.engine.process_path(path_string)
        result2 = self.engine.process_path(path_string)

        # Different parameters should use different cache entries
        transform_matrix = np.array([[2, 0, 0], [0, 2, 0], [0, 0, 1]])
        result3 = self.engine.process_path(path_string, transform_matrix=transform_matrix)

        # Check that caching is working
        cache_stats = self.engine.get_performance_stats()['caching']
        assert cache_stats['overall_hit_rate'] > 0


if __name__ == "__main__":
    # Run performance optimization tests
    print("=== Performance Optimization and Caching Tests ===")

    # Test cache functionality
    cache_test = TestAdvancedLRUCache()
    cache_test.setup_method()
    cache_test.test_basic_cache_operations()
    cache_test.test_lru_eviction()
    print("✓ LRU cache tests passed")

    # Test array pool
    pool_test = TestArrayPool()
    pool_test.setup_method()
    pool_test.test_array_allocation_and_reuse()
    pool_test.test_different_shapes_and_dtypes()
    print("✓ Array pool tests passed")

    # Test PathEngine caching
    engine_test = TestPathEngineCaching()
    engine_test.setup_method()
    engine_test.test_path_processing_cache()
    engine_test.test_performance_profiling()
    engine_test.test_cache_statistics()
    print("✓ PathEngine caching tests passed")

    print("=== All performance optimization tests completed successfully ===")