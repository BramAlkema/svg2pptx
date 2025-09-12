#!/usr/bin/env python3
"""
Tests for speedrun cache performance module.
"""

import pytest
import tempfile
import sqlite3
import time
import hashlib
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.performance.speedrun_cache import (
    SpeedrunCacheEntry, SpeedrunCache, PersistentSpeedrunCache,
    ContentAddressableCache, CacheWarmer, CacheAnalyzer
)


class TestSpeedrunCacheEntry:
    """Test SpeedrunCacheEntry functionality."""
    
    def test_cache_entry_creation(self):
        """Test basic cache entry creation."""
        data = {"test": "data"}
        content_hash = "abc123"
        created_at = datetime.now()
        
        entry = SpeedrunCacheEntry(
            data=data,
            content_hash=content_hash,
            created_at=created_at,
            last_accessed=created_at
        )
        
        assert entry.data == data
        assert entry.content_hash == content_hash
        assert entry.access_count == 0
        assert entry.size_bytes == 0
        assert entry.compression_ratio == 1.0
        assert len(entry.dependencies) == 0
        assert len(entry.tags) == 0
    
    def test_bump_access(self):
        """Test access count and timestamp updates."""
        entry = SpeedrunCacheEntry(
            data="test",
            content_hash="hash",
            created_at=datetime.now(),
            last_accessed=datetime.now()
        )
        
        original_count = entry.access_count
        original_time = entry.last_accessed
        
        # Wait a tiny bit to ensure time difference
        time.sleep(0.001)
        entry.bump_access()
        
        assert entry.access_count == original_count + 1
        assert entry.last_accessed > original_time
    
    def test_cache_entry_with_metadata(self):
        """Test cache entry with full metadata."""
        dependencies = {"dep1", "dep2"}
        tags = {"tag1", "optimization"}
        
        entry = SpeedrunCacheEntry(
            data="complex_data",
            content_hash="complex_hash",
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            size_bytes=1024,
            compression_ratio=0.7,
            dependencies=dependencies,
            tags=tags
        )
        
        assert entry.dependencies == dependencies
        assert entry.tags == tags
        assert entry.size_bytes == 1024
        assert entry.compression_ratio == 0.7


class TestSpeedrunCache:
    """Test SpeedrunCache core functionality."""
    
    @pytest.fixture
    def cache(self):
        """Create a fresh SpeedrunCache instance."""
        return SpeedrunCache(max_size=100)
    
    def test_cache_initialization(self, cache):
        """Test cache initialization."""
        assert cache.max_size == 100
        assert len(cache.entries) == 0
        assert cache.stats is not None
    
    def test_basic_cache_operations(self, cache):
        """Test get/set operations."""
        key = "test_key"
        data = {"converted": "data"}
        
        # Test miss
        result = cache.get(key)
        assert result is None
        
        # Test set
        cache.set(key, data)
        
        # Test hit
        result = cache.get(key)
        assert result == data
    
    def test_content_hash_generation(self, cache):
        """Test content hash generation."""
        data1 = {"test": "data"}
        data2 = {"test": "data"}
        data3 = {"test": "different"}
        
        hash1 = cache._generate_content_hash(data1)
        hash2 = cache._generate_content_hash(data2)
        hash3 = cache._generate_content_hash(data3)
        
        assert hash1 == hash2  # Same content = same hash
        assert hash1 != hash3  # Different content = different hash
        assert len(hash1) == 64  # SHA-256 hex length
    
    def test_cache_eviction_lru(self, cache):
        """Test LRU eviction policy."""
        # Fill cache beyond capacity
        for i in range(cache.max_size + 10):
            cache.set(f"key_{i}", f"data_{i}")
        
        # Cache should be at max capacity
        assert len(cache.entries) == cache.max_size
        
        # Oldest entries should be evicted
        assert cache.get("key_0") is None
        assert cache.get("key_9") is None
        
        # Recent entries should still exist
        assert cache.get(f"key_{cache.max_size + 5}") is not None
    
    def test_cache_stats_tracking(self, cache):
        """Test cache statistics tracking."""
        initial_stats = cache.get_stats()
        assert initial_stats.hits == 0
        assert initial_stats.misses == 0
        
        # Generate some hits and misses
        cache.get("nonexistent")  # miss
        cache.set("key", "data")
        cache.get("key")  # hit
        cache.get("another_nonexistent")  # miss
        
        final_stats = cache.get_stats()
        assert final_stats.hits == 1
        assert final_stats.misses == 2


class TestPersistentSpeedrunCache:
    """Test persistent cache functionality."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary directory for cache testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_persistent_cache_initialization(self, temp_cache_dir):
        """Test persistent cache initialization."""
        cache = PersistentSpeedrunCache(
            cache_dir=temp_cache_dir,
            max_size=50
        )
        
        assert cache.cache_dir == temp_cache_dir
        assert cache.db_path.exists()
        assert cache.max_size == 50
    
    def test_persistent_cache_save_load(self, temp_cache_dir):
        """Test saving and loading from persistent storage."""
        # Create cache and add data
        cache1 = PersistentSpeedrunCache(cache_dir=temp_cache_dir)
        cache1.set("persistent_key", {"important": "data"})
        cache1.save_to_disk()
        
        # Create new cache instance (simulating restart)
        cache2 = PersistentSpeedrunCache(cache_dir=temp_cache_dir)
        cache2.load_from_disk()
        
        # Data should be restored
        result = cache2.get("persistent_key")
        assert result == {"important": "data"}
    
    def test_cache_compression(self, temp_cache_dir):
        """Test data compression functionality."""
        cache = PersistentSpeedrunCache(
            cache_dir=temp_cache_dir,
            enable_compression=True
        )
        
        # Large data that should benefit from compression
        large_data = {"data": "x" * 10000, "repeated": ["item"] * 1000}
        cache.set("large_key", large_data)
        
        # Verify data integrity after compression/decompression
        result = cache.get("large_key")
        assert result == large_data
        
        # Entry should show compression ratio < 1.0
        entry = cache.entries["large_key"]
        assert entry.compression_ratio < 1.0
    
    def test_database_operations(self, temp_cache_dir):
        """Test SQLite database operations."""
        cache = PersistentSpeedrunCache(cache_dir=temp_cache_dir)
        
        # Add data
        cache.set("db_key", {"db": "data"})
        cache.save_to_disk()
        
        # Verify database contains the data
        with sqlite3.connect(cache.db_path) as conn:
            cursor = conn.execute(
                "SELECT key, content_hash FROM cache_entries WHERE key = ?",
                ("db_key",)
            )
            row = cursor.fetchone()
            
            assert row is not None
            assert row[0] == "db_key"
            assert len(row[1]) == 64  # SHA-256 hash


class TestContentAddressableCache:
    """Test content-addressable caching."""
    
    def test_content_addressable_storage(self):
        """Test content-addressable cache operations."""
        cache = ContentAddressableCache()
        
        data1 = {"content": "test"}
        data2 = {"content": "test"}  # Same content
        data3 = {"content": "different"}
        
        # Store same content twice
        hash1 = cache.store(data1)
        hash2 = cache.store(data2)
        hash3 = cache.store(data3)
        
        # Same content should generate same hash
        assert hash1 == hash2
        assert hash1 != hash3
        
        # Should be able to retrieve by hash
        assert cache.retrieve(hash1) == data1
        assert cache.retrieve(hash2) == data2
        assert cache.retrieve(hash3) == data3
    
    def test_content_deduplication(self):
        """Test that identical content is deduplicated."""
        cache = ContentAddressableCache()
        
        # Store same content multiple times
        data = {"dedup": "test"}
        hashes = [cache.store(data) for _ in range(10)]
        
        # All hashes should be identical
        assert len(set(hashes)) == 1
        
        # Cache should only contain one entry
        assert len(cache.content_store) == 1


class TestCacheWarmer:
    """Test cache warming functionality."""
    
    @pytest.fixture
    def mock_cache(self):
        """Create mock cache for warming tests."""
        return Mock(spec=SpeedrunCache)
    
    def test_cache_warmer_initialization(self, mock_cache):
        """Test cache warmer initialization."""
        warmer = CacheWarmer(cache=mock_cache)
        assert warmer.cache == mock_cache
        assert warmer.warming_tasks == {}
    
    @patch('src.performance.speedrun_cache.asyncio')
    def test_warm_from_patterns(self, mock_asyncio, mock_cache):
        """Test warming cache from file patterns."""
        warmer = CacheWarmer(cache=mock_cache)
        
        patterns = ["*.svg", "test_*.xml"]
        warmer.warm_from_patterns(patterns)
        
        # Should schedule warming tasks
        mock_asyncio.create_task.assert_called()
    
    def test_precompute_common_conversions(self, mock_cache):
        """Test precomputing common conversions."""
        warmer = CacheWarmer(cache=mock_cache)
        
        common_elements = ["rect", "circle", "path"]
        warmer.precompute_common_conversions(common_elements)
        
        # Mock cache should receive precomputed data
        assert mock_cache.set.called


class TestCacheAnalyzer:
    """Test cache analysis functionality."""
    
    @pytest.fixture
    def populated_cache(self):
        """Create cache with test data."""
        cache = SpeedrunCache(max_size=100)
        
        # Add entries with different access patterns
        for i in range(10):
            cache.set(f"key_{i}", f"data_{i}")
            # Simulate different access patterns
            for _ in range(i):
                cache.get(f"key_{i}")
        
        return cache
    
    def test_analyzer_initialization(self, populated_cache):
        """Test cache analyzer initialization."""
        analyzer = CacheAnalyzer(cache=populated_cache)
        assert analyzer.cache == populated_cache
    
    def test_hit_rate_analysis(self, populated_cache):
        """Test hit rate analysis."""
        analyzer = CacheAnalyzer(cache=populated_cache)
        stats = analyzer.analyze_hit_rates()
        
        assert "overall_hit_rate" in stats
        assert "hit_rate_by_key_pattern" in stats
        assert stats["overall_hit_rate"] >= 0
    
    def test_memory_usage_analysis(self, populated_cache):
        """Test memory usage analysis."""
        analyzer = CacheAnalyzer(cache=populated_cache)
        memory_stats = analyzer.analyze_memory_usage()
        
        assert "total_entries" in memory_stats
        assert "estimated_memory_bytes" in memory_stats
        assert "average_entry_size" in memory_stats
    
    def test_access_pattern_analysis(self, populated_cache):
        """Test access pattern analysis."""
        analyzer = CacheAnalyzer(cache=populated_cache)
        patterns = analyzer.analyze_access_patterns()
        
        assert "most_accessed_keys" in patterns
        assert "least_accessed_keys" in patterns
        assert "access_frequency_distribution" in patterns
    
    def test_optimization_recommendations(self, populated_cache):
        """Test cache optimization recommendations."""
        analyzer = CacheAnalyzer(cache=populated_cache)
        recommendations = analyzer.get_optimization_recommendations()
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        for rec in recommendations:
            assert "type" in rec
            assert "description" in rec
            assert "impact" in rec


class TestCacheIntegration:
    """Integration tests for cache components."""
    
    def test_full_cache_workflow(self):
        """Test complete cache workflow."""
        # Initialize cache system
        cache = SpeedrunCache(max_size=50)
        warmer = CacheWarmer(cache=cache)
        analyzer = CacheAnalyzer(cache=cache)
        
        # Simulate SVG conversion workflow
        svg_data = {"type": "rect", "x": 10, "y": 20, "width": 100, "height": 50}
        conversion_key = "rect_10_20_100_50"
        
        # Cache miss on first access
        result = cache.get(conversion_key)
        assert result is None
        
        # Store conversion result
        drawingml_result = "<p:sp>...</p:sp>"
        cache.set(conversion_key, drawingml_result)
        
        # Cache hit on subsequent access
        result = cache.get(conversion_key)
        assert result == drawingml_result
        
        # Analyze cache performance
        stats = analyzer.analyze_hit_rates()
        assert stats["overall_hit_rate"] >= 0
        
        memory_stats = analyzer.analyze_memory_usage()
        assert memory_stats["total_entries"] == 1
    
    def test_cache_persistence_integration(self, tmp_path):
        """Test persistent cache integration."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        
        # Create and populate persistent cache
        cache1 = PersistentSpeedrunCache(cache_dir=cache_dir)
        cache1.set("integration_key", {"complex": {"nested": "data"}})
        cache1.save_to_disk()
        
        # Verify persistence across sessions
        cache2 = PersistentSpeedrunCache(cache_dir=cache_dir)
        cache2.load_from_disk()
        
        result = cache2.get("integration_key")
        assert result == {"complex": {"nested": "data"}}
        
        # Analyze persistent cache
        analyzer = CacheAnalyzer(cache=cache2)
        recommendations = analyzer.get_optimization_recommendations()
        assert isinstance(recommendations, list)


@pytest.mark.benchmark
class TestCachePerformance:
    """Performance benchmarks for cache operations."""
    
    def test_cache_set_performance(self, benchmark):
        """Benchmark cache set operations."""
        cache = SpeedrunCache(max_size=1000)
        data = {"benchmark": "data" * 100}
        
        def set_operation():
            cache.set("benchmark_key", data)
        
        result = benchmark(set_operation)
        assert result is None  # set returns None
    
    def test_cache_get_performance(self, benchmark):
        """Benchmark cache get operations."""
        cache = SpeedrunCache(max_size=1000)
        cache.set("perf_key", {"performance": "data"})
        
        def get_operation():
            return cache.get("perf_key")
        
        result = benchmark(get_operation)
        assert result == {"performance": "data"}
    
    def test_content_hash_performance(self, benchmark):
        """Benchmark content hash generation."""
        cache = SpeedrunCache()
        large_data = {"data": "x" * 10000, "array": list(range(1000))}
        
        def hash_operation():
            return cache._generate_content_hash(large_data)
        
        result = benchmark(hash_operation)
        assert len(result) == 64  # SHA-256 hex length