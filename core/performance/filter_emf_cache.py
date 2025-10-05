#!/usr/bin/env python3
"""
EMF-based cache storage for complex filter operations.

This module provides specialized caching for filter results using EMF blobs,
enabling high-fidelity storage and retrieval of complex filter effects that
cannot be efficiently represented in pure vector format.
"""

import os
import pickle
import zlib
import hashlib
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
from lxml import etree as ET

try:
    from src.emf_blob import EMFBlob
except ImportError:
    # Handle import for testing
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))


@dataclass
class EMFCacheEntry:
    """Entry in the EMF-based filter cache."""
    cache_key: str
    emf_blob: bytes
    filter_chain_hash: str
    context_hash: str
    created_at: float
    complexity_score: float
    compression_ratio: float = 1.0
    access_count: int = 0
    last_accessed: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize metadata and timestamps."""
        if self.metadata is None:
            self.metadata = {}
        if self.last_accessed == 0.0:
            self.last_accessed = self.created_at


class EMFFilterCache:
    """EMF-based cache storage for complex filter operations."""

    def __init__(self,
                 cache_dir: str = None,
                 max_memory_size: int = 100 * 1024 * 1024,  # 100MB
                 max_disk_size: int = 1024 * 1024 * 1024,   # 1GB
                 compression_level: int = 6):
        """
        Initialize EMF filter cache.

        Args:
            cache_dir: Directory for persistent cache storage
            max_memory_size: Maximum memory cache size in bytes
            max_disk_size: Maximum disk cache size in bytes
            compression_level: zlib compression level (0-9)
        """
        self.max_memory_size = max_memory_size
        self.max_disk_size = max_disk_size
        self.compression_level = compression_level

        # Setup cache directory
        if cache_dir is None:
            cache_dir = os.path.join(os.path.expanduser("~"), ".svg2pptx_cache", "emf_filters")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache
        self._memory_cache: Dict[str, EMFCacheEntry] = {}
        self._memory_usage = 0

        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'disk_reads': 0,
            'disk_writes': 0,
            'compression_savings': 0
        }

    def cache_filter_result(self,
                          filter_chain: List[ET.Element],
                          context: Dict[str, Any],
                          emf_blob: bytes,
                          complexity_score: float = 1.0) -> str:
        """
        Cache EMF blob result for filter combination.

        Args:
            filter_chain: List of filter elements
            context: Filter processing context
            emf_blob: Generated EMF blob data
            complexity_score: Computational complexity score

        Returns:
            Cache key for the stored result
        """
        # Generate cache key
        cache_key = self._generate_cache_key(filter_chain, context)
        filter_chain_hash = self._hash_filter_chain(filter_chain)
        context_hash = self._hash_context(context)

        # Compress EMF blob
        compressed_blob = zlib.compress(emf_blob, self.compression_level)
        compression_ratio = len(compressed_blob) / len(emf_blob) if emf_blob else 1.0

        # Create cache entry
        entry = EMFCacheEntry(
            cache_key=cache_key,
            emf_blob=compressed_blob,
            filter_chain_hash=filter_chain_hash,
            context_hash=context_hash,
            created_at=time.time(),
            complexity_score=complexity_score,
            compression_ratio=compression_ratio,
            metadata={
                'original_size': len(emf_blob),
                'compressed_size': len(compressed_blob),
                'filter_count': len(filter_chain),
                'filter_types': [self._get_filter_type(f) for f in filter_chain]
            }
        )

        # Store in memory cache
        self._store_in_memory(entry)

        # Store on disk for persistence
        self._store_on_disk(entry)

        self.stats['compression_savings'] += len(emf_blob) - len(compressed_blob)

        return cache_key

    def get_cached_result(self,
                         filter_chain: List[ET.Element],
                         context: Dict[str, Any]) -> Optional[bytes]:
        """
        Retrieve cached EMF blob for filter combination.

        Args:
            filter_chain: List of filter elements
            context: Filter processing context

        Returns:
            Decompressed EMF blob if found, None otherwise
        """
        cache_key = self._generate_cache_key(filter_chain, context)

        # Check memory cache first
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]
            entry.access_count += 1
            entry.last_accessed = time.time()
            self.stats['hits'] += 1

            # Decompress and return
            return zlib.decompress(entry.emf_blob)

        # Check disk cache
        entry = self._load_from_disk(cache_key)
        if entry:
            # Move to memory cache
            self._store_in_memory(entry)
            entry.access_count += 1
            entry.last_accessed = time.time()
            self.stats['hits'] += 1
            self.stats['disk_reads'] += 1

            return zlib.decompress(entry.emf_blob)

        self.stats['misses'] += 1
        return None

    def _generate_cache_key(self, filter_chain: List[ET.Element], context: Dict[str, Any]) -> str:
        """Generate unique cache key for filter combination."""
        filter_hash = self._hash_filter_chain(filter_chain)
        context_hash = self._hash_context(context)

        # Combine hashes
        combined = f"{filter_hash}:{context_hash}"
        return hashlib.blake2b(combined.encode(), digest_size=16).hexdigest()

    def _hash_filter_chain(self, filter_chain: List[ET.Element]) -> str:
        """Generate hash for filter chain."""
        chain_data = []

        for element in filter_chain:
            element_data = {
                'tag': self._get_filter_type(element),
                'attributes': dict(element.attrib),
                'text': element.text or ''
            }
            chain_data.append(element_data)

        chain_str = str(sorted(chain_data, key=lambda x: x['tag']))
        return hashlib.md5(chain_str.encode()).hexdigest()

    def _hash_context(self, context: Dict[str, Any]) -> str:
        """Generate hash for context."""
        # Extract relevant context data
        context_data = {
            'viewport': context.get('viewport', {}),
            'coordinate_system': context.get('coordinate_system', {}),
            'transform_chain': context.get('transform_chain', []),
            'filter_parameters': context.get('filter_parameters', {})
        }

        context_str = str(sorted(context_data.items()))
        return hashlib.md5(context_str.encode()).hexdigest()

    def _get_filter_type(self, element: ET.Element) -> str:
        """Extract filter type from element."""
        tag = element.tag
        if '}' in tag:
            tag = tag.split('}')[1]
        return tag

    def _store_in_memory(self, entry: EMFCacheEntry):
        """Store entry in memory cache with size management."""
        entry_size = len(entry.emf_blob) + len(pickle.dumps(entry.metadata))

        # Evict if necessary
        while (self._memory_usage + entry_size > self.max_memory_size and
               len(self._memory_cache) > 0):
            self._evict_lru_memory()

        self._memory_cache[entry.cache_key] = entry
        self._memory_usage += entry_size

    def _evict_lru_memory(self):
        """Evict least recently used entry from memory cache."""
        if not self._memory_cache:
            return

        # Find LRU entry
        lru_key = min(self._memory_cache.keys(),
                     key=lambda k: self._memory_cache[k].last_accessed)

        entry = self._memory_cache.pop(lru_key)
        entry_size = len(entry.emf_blob) + len(pickle.dumps(entry.metadata))
        self._memory_usage -= entry_size
        self.stats['evictions'] += 1

    def _store_on_disk(self, entry: EMFCacheEntry):
        """Store entry on disk for persistence."""
        cache_file = self.cache_dir / f"{entry.cache_key}.emf_cache"

        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(entry, f, protocol=pickle.HIGHEST_PROTOCOL)
            self.stats['disk_writes'] += 1

            # Manage disk cache size
            self._manage_disk_cache_size()

        except (IOError, OSError) as e:
            # Log error but don't fail the operation
            print(f"Warning: Failed to write cache file {cache_file}: {e}")

    def _load_from_disk(self, cache_key: str) -> Optional[EMFCacheEntry]:
        """Load entry from disk cache."""
        cache_file = self.cache_dir / f"{cache_key}.emf_cache"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'rb') as f:
                entry = pickle.load(f)
                return entry
        except (IOError, OSError, pickle.PickleError) as e:
            # Remove corrupted cache file
            try:
                cache_file.unlink()
            except:
                pass
            print(f"Warning: Failed to load cache file {cache_file}: {e}")
            return None

    def _manage_disk_cache_size(self):
        """Manage disk cache size by removing old entries."""
        cache_files = list(self.cache_dir.glob("*.emf_cache"))

        # Calculate total size
        total_size = sum(f.stat().st_size for f in cache_files)

        if total_size <= self.max_disk_size:
            return

        # Sort by access time (oldest first)
        files_with_time = []
        for cache_file in cache_files:
            try:
                entry = self._load_from_disk(cache_file.stem)
                if entry:
                    files_with_time.append((cache_file, entry.last_accessed))
            except:
                # Remove corrupted file
                try:
                    cache_file.unlink()
                except:
                    pass

        files_with_time.sort(key=lambda x: x[1])

        # Remove oldest files until under limit
        for cache_file, _ in files_with_time:
            try:
                cache_file.unlink()
                total_size -= cache_file.stat().st_size
                if total_size <= self.max_disk_size * 0.8:  # Leave some headroom
                    break
            except:
                pass

    def invalidate_by_filter_type(self, filter_types: List[str]) -> int:
        """
        Invalidate cache entries containing specific filter types.

        Args:
            filter_types: List of filter types to invalidate

        Returns:
            Number of entries invalidated
        """
        invalidated = 0

        # Invalidate memory cache
        to_remove = []
        for key, entry in self._memory_cache.items():
            if any(ft in entry.metadata.get('filter_types', []) for ft in filter_types):
                to_remove.append(key)

        for key in to_remove:
            entry = self._memory_cache.pop(key)
            entry_size = len(entry.emf_blob) + len(pickle.dumps(entry.metadata))
            self._memory_usage -= entry_size
            invalidated += 1

        # Invalidate disk cache
        cache_files = list(self.cache_dir.glob("*.emf_cache"))
        for cache_file in cache_files:
            try:
                entry = self._load_from_disk(cache_file.stem)
                if entry and any(ft in entry.metadata.get('filter_types', []) for ft in filter_types):
                    cache_file.unlink()
                    invalidated += 1
            except:
                pass

        return invalidated

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        memory_entries = len(self._memory_cache)
        disk_files = len(list(self.cache_dir.glob("*.emf_cache")))

        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0.0

        return {
            **self.stats,
            'memory_entries': memory_entries,
            'disk_entries': disk_files,
            'memory_usage_bytes': self._memory_usage,
            'memory_usage_mb': self._memory_usage / (1024 * 1024),
            'hit_rate': hit_rate,
            'cache_dir': str(self.cache_dir)
        }

    def clear_cache(self, memory_only: bool = False):
        """Clear cache entries."""
        # Clear memory cache
        self._memory_cache.clear()
        self._memory_usage = 0

        if not memory_only:
            # Clear disk cache
            cache_files = list(self.cache_dir.glob("*.emf_cache"))
            for cache_file in cache_files:
                try:
                    cache_file.unlink()
                except:
                    pass

        # Reset stats
        self.stats = {key: 0 for key in self.stats}


class EMFFilterCacheManager:
    """Manager for EMF filter cache integration with the main cache system."""

    def __init__(self, cache_dir: str = None):
        """Initialize EMF filter cache manager."""
        self.emf_cache = EMFFilterCache(cache_dir)

    def cache_complex_filter_result(self,
                                  filter_chain: List[ET.Element],
                                  context: Dict[str, Any],
                                  result: Dict[str, Any]) -> str:
        """
        Cache complex filter result with EMF storage.

        Args:
            filter_chain: List of filter elements
            context: Processing context
            result: Filter processing result containing EMF blob

        Returns:
            Cache key for stored result
        """
        emf_blob = result.get('emf_blob')
        if not emf_blob:
            raise ValueError("Result must contain EMF blob data")

        complexity_score = result.get('complexity_score', 1.0)

        return self.emf_cache.cache_filter_result(
            filter_chain, context, emf_blob, complexity_score
        )

    def get_cached_filter_result(self,
                               filter_chain: List[ET.Element],
                               context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get cached filter result.

        Args:
            filter_chain: List of filter elements
            context: Processing context

        Returns:
            Cached result with EMF blob if found, None otherwise
        """
        emf_blob = self.emf_cache.get_cached_result(filter_chain, context)
        if emf_blob:
            return {
                'emf_blob': emf_blob,
                'cached': True,
                'cache_type': 'emf_storage'
            }
        return None

    def invalidate_filter_cache(self, filter_types: List[str] = None) -> int:
        """
        Invalidate cached filter results.

        Args:
            filter_types: Specific filter types to invalidate, or None for all

        Returns:
            Number of entries invalidated
        """
        if filter_types:
            return self.emf_cache.invalidate_by_filter_type(filter_types)
        else:
            stats_before = self.emf_cache.get_cache_stats()
            self.emf_cache.clear_cache()
            return stats_before['memory_entries'] + stats_before['disk_entries']

    def get_cache_performance_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        return self.emf_cache.get_cache_stats()


# Global EMF filter cache manager instance
_global_emf_cache_manager = None

def get_global_emf_cache_manager() -> EMFFilterCacheManager:
    """Get or create the global EMF filter cache manager."""
    global _global_emf_cache_manager
    if _global_emf_cache_manager is None:
        _global_emf_cache_manager = EMFFilterCacheManager()
    return _global_emf_cache_manager