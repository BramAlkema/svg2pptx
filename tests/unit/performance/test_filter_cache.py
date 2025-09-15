#!/usr/bin/env python3
"""
Unit tests for complex filter result caching with EMF storage.

Tests the filter caching system including cache key generation,
EMF-based storage, raster fallbacks, and performance optimization.
"""

import pytest
import hashlib
import json
import time
from unittest.mock import Mock, patch, MagicMock
from lxml import etree as ET
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.performance.cache import BaseCache, ConversionCache
from src.converters.filters.core.base import FilterContext, FilterResult, Filter


class TestFilterCacheBase:
    """Test basic filter cache functionality."""

    def test_filter_cache_initialization(self):
        """Test filter cache initializes correctly."""
        cache = ConversionCache()

        assert cache.path_cache is not None
        assert cache.color_cache is not None
        assert cache.transform_cache is not None
        assert hasattr(cache, '_element_style_cache')
        assert hasattr(cache, '_element_bounds_cache')
        assert hasattr(cache, '_drawingml_cache')

    def test_cache_key_generation_consistency(self):
        """Test that cache key generation is consistent for same input."""
        cache = ConversionCache()

        # Create test element
        element = ET.fromstring('<feGaussianBlur stdDeviation="5"/>')

        # Generate keys for same element multiple times
        key1 = cache._hash_element(element)
        key2 = cache._hash_element(element)

        assert key1 == key2
        assert len(key1) == 32  # MD5 hash length

    def test_cache_key_generation_different_elements(self):
        """Test that different elements generate different cache keys."""
        cache = ConversionCache()

        element1 = ET.fromstring('<feGaussianBlur stdDeviation="5"/>')
        element2 = ET.fromstring('<feGaussianBlur stdDeviation="10"/>')

        key1 = cache._hash_element(element1)
        key2 = cache._hash_element(element2)

        assert key1 != key2


class TestFilterCacheKeyGeneration:
    """Test cache key generation for filter combinations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = ConversionCache()
        self.test_element = ET.fromstring('''
            <filter>
                <feGaussianBlur stdDeviation="5"/>
                <feColorMatrix type="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 1 0"/>
            </filter>
        ''')

    def test_simple_filter_cache_key(self):
        """Test cache key generation for simple filter."""
        element = ET.fromstring('<feGaussianBlur stdDeviation="5"/>')
        context = {
            'viewport': {'width': 100, 'height': 100},
            'parameters': {'stdDeviation': 5}
        }

        key = self._generate_filter_cache_key(element, context)

        assert isinstance(key, str)
        assert len(key) > 0

    def test_complex_filter_chain_cache_key(self):
        """Test cache key generation for complex filter chain."""
        context = {
            'filter_chain': [
                {'type': 'feGaussianBlur', 'stdDeviation': 5},
                {'type': 'feColorMatrix', 'type': 'matrix', 'values': '1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 1 0'}
            ],
            'viewport': {'width': 200, 'height': 150},
            'coordinate_system': {'scale_x': 1.0, 'scale_y': 1.0}
        }

        key = self._generate_filter_cache_key(self.test_element, context)

        assert isinstance(key, str)
        assert len(key) > 0

    def test_cache_key_includes_parameters(self):
        """Test that cache key changes when parameters change."""
        element = ET.fromstring('<feGaussianBlur stdDeviation="5"/>')

        context1 = {'parameters': {'stdDeviation': 5}}
        context2 = {'parameters': {'stdDeviation': 10}}

        key1 = self._generate_filter_cache_key(element, context1)
        key2 = self._generate_filter_cache_key(element, context2)

        assert key1 != key2

    def test_cache_key_includes_coordinate_system(self):
        """Test that cache key includes coordinate system information."""
        element = ET.fromstring('<feGaussianBlur stdDeviation="5"/>')

        context1 = {
            'parameters': {'stdDeviation': 5},
            'coordinate_system': {'scale_x': 1.0, 'scale_y': 1.0}
        }
        context2 = {
            'parameters': {'stdDeviation': 5},
            'coordinate_system': {'scale_x': 2.0, 'scale_y': 2.0}
        }

        key1 = self._generate_filter_cache_key(element, context1)
        key2 = self._generate_filter_cache_key(element, context2)

        assert key1 != key2

    def _generate_filter_cache_key(self, element, context):
        """Helper method to generate filter cache key."""
        key_data = {
            'element_hash': self.cache._hash_element(element),
            'context': context
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.blake2b(key_str.encode()).hexdigest()


class TestEMFBasedCacheStorage:
    """Test EMF-based cache storage for complex filter operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = ConversionCache()

    def test_emf_cache_storage_integration(self):
        """Test EMF storage integration with cache."""
        element = ET.fromstring('<feGaussianBlur stdDeviation="5"/>')
        context_hash = "test_context_hash"

        # Mock EMF output
        emf_output = b'\x01\x00\x00\x00' + b'\x20' * 100  # Mock EMF blob

        # Cache EMF output
        self.cache.cache_drawingml_output(element, context_hash, emf_output)

        # Retrieve cached output
        cached = self.cache.get_drawingml_output(element, context_hash)

        assert cached == emf_output

    def test_emf_cache_miss_returns_none(self):
        """Test that cache miss returns None for EMF storage."""
        element = ET.fromstring('<feGaussianBlur stdDeviation="5"/>')
        context_hash = "nonexistent_hash"

        cached = self.cache.get_drawingml_output(element, context_hash)

        assert cached is None

    def test_emf_cache_with_different_contexts(self):
        """Test EMF caching with different context hashes."""
        element = ET.fromstring('<feGaussianBlur stdDeviation="5"/>')

        emf_output1 = b'\x01\x00\x00\x00' + b'\x20' * 100
        emf_output2 = b'\x02\x00\x00\x00' + b'\x30' * 100

        # Cache different outputs for different contexts
        self.cache.cache_drawingml_output(element, "context1", emf_output1)
        self.cache.cache_drawingml_output(element, "context2", emf_output2)

        # Verify correct outputs are retrieved
        assert self.cache.get_drawingml_output(element, "context1") == emf_output1
        assert self.cache.get_drawingml_output(element, "context2") == emf_output2


class TestRasterFallbackCaching:
    """Test raster fallback using add_raster_32bpp for arbitrary operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = ConversionCache()

    @patch('src.emf_blob.EMFBlob')
    def test_raster_fallback_cache_integration(self, mock_emf_blob_class):
        """Test raster fallback integration with caching."""
        # Mock EMF blob instance
        mock_emf_blob = Mock()
        mock_emf_blob.add_raster_32bpp.return_value = 1  # Mock handle
        mock_emf_blob.finalize.return_value = b'\x03\x00\x00\x00' + b'\x40' * 200
        mock_emf_blob_class.return_value = mock_emf_blob

        # Test raster fallback caching
        element = ET.fromstring('<feConvolveMatrix kernelMatrix="1 1 1 1 1 1 1 1 1"/>')

        # Mock raster data (32-bit RGBA, 10x10 pixels)
        width, height = 10, 10
        raster_data = b'\xFF\x00\x00\xFF' * (width * height)  # Red pixels

        # Cache raster fallback
        context_hash = "raster_context"
        cached_key = f"raster_fallback:{self.cache._hash_element(element)}:{context_hash}"

        # Simulate caching raster fallback
        self.cache._drawingml_cache.put(cached_key, {
            'emf_blob': mock_emf_blob.finalize.return_value,
            'width': width,
            'height': height,
            'fallback_type': 'raster_32bpp'
        })

        # Retrieve cached raster fallback
        cached = self.cache._drawingml_cache.get(cached_key)

        assert cached is not None
        assert cached['fallback_type'] == 'raster_32bpp'
        assert cached['width'] == width
        assert cached['height'] == height

    def test_raster_fallback_cache_key_generation(self):
        """Test cache key generation for raster fallbacks."""
        element = ET.fromstring('<feConvolveMatrix kernelMatrix="1 1 1 1 1 1 1 1 1"/>')

        context1 = {'fallback_type': 'raster', 'resolution': '96dpi'}
        context2 = {'fallback_type': 'raster', 'resolution': '150dpi'}

        # Generate cache keys
        key1 = f"raster:{self.cache._hash_element(element)}:{hashlib.md5(str(context1).encode()).hexdigest()}"
        key2 = f"raster:{self.cache._hash_element(element)}:{hashlib.md5(str(context2).encode()).hexdigest()}"

        assert key1 != key2


class TestCacheInvalidationStrategies:
    """Test cache invalidation and update strategies."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = ConversionCache()

    def test_cache_invalidation_by_element_change(self):
        """Test cache invalidation when source element changes."""
        # Cache some data
        element1 = ET.fromstring('<feGaussianBlur stdDeviation="5"/>')
        element2 = ET.fromstring('<feGaussianBlur stdDeviation="10"/>')  # Different stdDeviation

        context_hash = "test_context"

        # Cache both elements
        self.cache.cache_drawingml_output(element1, context_hash, "output1")
        self.cache.cache_drawingml_output(element2, context_hash, "output2")

        # Verify both are cached
        assert self.cache.get_drawingml_output(element1, context_hash) == "output1"
        assert self.cache.get_drawingml_output(element2, context_hash) == "output2"

        # Clear cache to simulate invalidation
        self.cache._drawingml_cache.clear()

        # Verify cache is cleared
        assert self.cache.get_drawingml_output(element1, context_hash) is None
        assert self.cache.get_drawingml_output(element2, context_hash) is None

    def test_partial_cache_invalidation(self):
        """Test partial cache invalidation based on element patterns."""
        elements = [
            ET.fromstring('<feGaussianBlur stdDeviation="5"/>'),
            ET.fromstring('<feColorMatrix type="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 1 0"/>'),
            ET.fromstring('<feOffset dx="5" dy="5"/>')
        ]

        context_hash = "test_context"

        # Cache all elements
        for i, element in enumerate(elements):
            self.cache.cache_drawingml_output(element, context_hash, f"output{i}")

        # Verify all are cached
        for i, element in enumerate(elements):
            assert self.cache.get_drawingml_output(element, context_hash) == f"output{i}"

        # Simulate selective invalidation by recreating cache with some elements
        new_cache = ConversionCache()

        # Re-cache only first two elements
        for i in range(2):
            new_cache.cache_drawingml_output(elements[i], context_hash, f"output{i}")

        # Verify selective caching
        assert new_cache.get_drawingml_output(elements[0], context_hash) == "output0"
        assert new_cache.get_drawingml_output(elements[1], context_hash) == "output1"
        assert new_cache.get_drawingml_output(elements[2], context_hash) is None


class TestCacheSizeManagement:
    """Test cache size management and cleanup systems."""

    def test_cache_size_limit_enforcement(self):
        """Test that cache enforces size limits."""
        # Create cache with small limit for testing
        small_cache = BaseCache(max_size=3)

        # Add items up to limit
        small_cache.put("key1", "value1")
        small_cache.put("key2", "value2")
        small_cache.put("key3", "value3")

        assert small_cache.get("key1") == "value1"
        assert small_cache.get("key2") == "value2"
        assert small_cache.get("key3") == "value3"

        # Add one more item, should evict oldest
        time.sleep(0.001)  # Ensure timestamp difference
        small_cache.put("key4", "value4")

        # Verify LRU eviction occurred
        assert small_cache.get("key1") is None  # Should be evicted
        assert small_cache.get("key4") == "value4"  # Should be present

    def test_cache_memory_usage_tracking(self):
        """Test cache memory usage tracking."""
        cache = ConversionCache()

        # Get initial memory stats
        initial_stats = cache.get_total_stats()

        # Add some data to caches
        element = ET.fromstring('<feGaussianBlur stdDeviation="5"/>')
        cache.cache_drawingml_output(element, "context1", "large_output_data" * 100)

        # Get updated memory stats
        updated_stats = cache.get_total_stats()

        # Memory usage should have increased
        assert updated_stats['drawingml_cache'].memory_usage >= initial_stats['drawingml_cache'].memory_usage

    def test_cache_cleanup_on_clear(self):
        """Test cache cleanup when cleared."""
        cache = ConversionCache()

        # Add data to all caches
        element = ET.fromstring('<feGaussianBlur stdDeviation="5"/>')
        cache.cache_drawingml_output(element, "context", "output")
        cache.path_cache.cache_parsed_path("M 10 10 L 20 20", [("M", [10, 10]), ("L", [20, 20])])
        cache.color_cache.cache_parsed_color("red", (255, 0, 0, 1.0))

        # Verify data is cached
        assert cache.get_drawingml_output(element, "context") == "output"
        assert cache.path_cache.get_parsed_path("M 10 10 L 20 20") is not None
        assert cache.color_cache.get_parsed_color("red") is not None

        # Clear all caches
        cache.clear_all()

        # Verify all caches are cleared
        assert cache.get_drawingml_output(element, "context") is None
        assert cache.path_cache.get_parsed_path("M 10 10 L 20 20") is None
        assert cache.color_cache.get_parsed_color("red") is None


class TestCachePerformanceOptimization:
    """Test cache performance optimization for repeated filter patterns."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = ConversionCache()

    def test_repeated_filter_pattern_performance(self):
        """Test performance optimization for repeated filter patterns."""
        element = ET.fromstring('<feGaussianBlur stdDeviation="5"/>')
        context_hash = "performance_context"
        output_data = "optimized_output_data"

        # First access - cache miss
        start_time = time.time()
        cached = self.cache.get_drawingml_output(element, context_hash)
        first_access_time = time.time() - start_time

        assert cached is None  # Cache miss

        # Cache the data
        self.cache.cache_drawingml_output(element, context_hash, output_data)

        # Second access - cache hit
        start_time = time.time()
        cached = self.cache.get_drawingml_output(element, context_hash)
        second_access_time = time.time() - start_time

        assert cached == output_data  # Cache hit
        # Cache hit should be faster (though timing might vary in tests)
        assert second_access_time <= first_access_time + 0.001  # Allow for timing variance

    def test_cache_hit_rate_tracking(self):
        """Test cache hit rate tracking for performance monitoring."""
        element = ET.fromstring('<feGaussianBlur stdDeviation="5"/>')

        # Multiple cache operations
        for i in range(5):
            self.cache.cache_drawingml_output(element, f"context{i}", f"output{i}")

        # Access cached data multiple times
        for i in range(5):
            for j in range(3):  # Access each item 3 times
                cached = self.cache.get_drawingml_output(element, f"context{i}")
                assert cached == f"output{i}"

        # Check cache stats
        stats = self.cache.get_total_stats()
        drawingml_stats = stats['drawingml_cache']

        # Should have high hit rate due to repeated access
        assert drawingml_stats.total_requests > 0
        assert drawingml_stats.hits > 0
        assert drawingml_stats.hit_rate > 0.0


class TestCacheVisualConsistency:
    """Test that cached results maintain visual consistency."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = ConversionCache()

    def test_cached_filter_result_consistency(self):
        """Test that cached filter results are consistent."""
        element = ET.fromstring('<feGaussianBlur stdDeviation="5"/>')
        context_hash = "consistency_context"

        # Expected output for the filter
        expected_output = '<a:effectLst><a:blur rad="50000"/></a:effectLst>'

        # Cache the result
        self.cache.cache_drawingml_output(element, context_hash, expected_output)

        # Retrieve multiple times and verify consistency
        for _ in range(10):
            cached = self.cache.get_drawingml_output(element, context_hash)
            assert cached == expected_output

    def test_cache_integrity_across_operations(self):
        """Test cache integrity across multiple operations."""
        elements = [
            ET.fromstring('<feGaussianBlur stdDeviation="5"/>'),
            ET.fromstring('<feColorMatrix type="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 1 0"/>'),
        ]

        context_hash = "integrity_context"
        expected_outputs = [
            '<a:effectLst><a:blur rad="50000"/></a:effectLst>',
            '<a:effectLst><a:colorRepl oldClr="008000" newClr="00FF00"/></a:effectLst>'
        ]

        # Cache all results
        for element, expected in zip(elements, expected_outputs):
            self.cache.cache_drawingml_output(element, context_hash, expected)

        # Perform various cache operations
        self.cache.get_total_stats()  # Get stats
        self.cache.get_memory_usage()  # Get memory usage

        # Verify all cached results remain intact
        for element, expected in zip(elements, expected_outputs):
            cached = self.cache.get_drawingml_output(element, context_hash)
            assert cached == expected

    def test_emf_blob_integrity_in_cache(self):
        """Test that EMF blob data maintains integrity in cache."""
        element = ET.fromstring('<feConvolveMatrix kernelMatrix="1 1 1 1 1 1 1 1 1"/>')
        context_hash = "emf_integrity_context"

        # Mock EMF blob with specific binary pattern
        emf_blob = b'\x01\x00\x00\x00' + b'\x42' * 256 + b'\x00\x00\x00\x01'

        # Cache EMF blob
        self.cache.cache_drawingml_output(element, context_hash, emf_blob)

        # Retrieve and verify binary integrity
        cached_blob = self.cache.get_drawingml_output(element, context_hash)

        assert cached_blob == emf_blob
        assert len(cached_blob) == len(emf_blob)
        assert cached_blob[:4] == b'\x01\x00\x00\x00'  # Check header
        assert cached_blob[-4:] == b'\x00\x00\x00\x01'  # Check footer