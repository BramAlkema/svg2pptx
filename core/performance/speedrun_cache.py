#!/usr/bin/env python3
"""
Speedrun cache enhancements for maximum SVG conversion performance.

This module extends the existing cache system with:
- Disk persistence for cross-session caching
- Advanced invalidation strategies
- Content-addressable caching
- Compression and serialization optimizations
- Cache warming and preloading
"""

import hashlib
import json
import logging
import pickle
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    import pyzstd as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False
    zstd = None

from lxml import etree as ET

from .cache import ConversionCache

logger = logging.getLogger(__name__)


@dataclass
class SpeedrunCacheEntry:
    """Enhanced cache entry with metadata for speedrun optimization."""
    data: Any
    content_hash: str
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_bytes: int = 0
    compression_ratio: float = 1.0
    dependencies: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)
    
    def bump_access(self):
        """Update access statistics."""
        self.last_accessed = datetime.now()
        self.access_count += 1


class ContentAddressableCache:
    """Content-addressable cache with deterministic keys."""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self._cache: dict[str, SpeedrunCacheEntry] = {}
        self._lock = threading.RLock()
        
    def generate_content_hash(self, content: Any, context: dict[str, Any] = None) -> str:
        """Generate deterministic hash for content + context."""
        hasher = hashlib.blake2b(digest_size=16)  # 128-bit hash
        
        # Hash the content
        if isinstance(content, ET._Element):
            content_str = ET.tostring(content, encoding='unicode')
        elif isinstance(content, str):
            content_str = content
        else:
            content_str = str(content)
        
        hasher.update(content_str.encode('utf-8'))
        
        # Hash the context if provided
        if context:
            context_str = json.dumps(context, sort_keys=True)
            hasher.update(context_str.encode('utf-8'))
        
        return hasher.hexdigest()
    
    def put(self, content_hash: str, data: Any, 
            dependencies: set[str] = None, tags: set[str] = None) -> None:
        """Store data with content hash key."""
        with self._lock:
            # Serialize and measure size
            serialized = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
            size_bytes = len(serialized)
            
            entry = SpeedrunCacheEntry(
                data=data,
                content_hash=content_hash,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                size_bytes=size_bytes,
                dependencies=dependencies or set(),
                tags=tags or set(),
            )
            
            self._cache[content_hash] = entry
    
    def get(self, content_hash: str) -> Any | None:
        """Retrieve data by content hash."""
        with self._lock:
            entry = self._cache.get(content_hash)
            if entry:
                entry.bump_access()
                return entry.data
            return None
    
    def exists(self, content_hash: str) -> bool:
        """Check if content hash exists in cache."""
        return content_hash in self._cache
    
    def invalidate_by_tags(self, tags: set[str]) -> int:
        """Invalidate all entries with any of the given tags."""
        with self._lock:
            to_remove = []
            for key, entry in self._cache.items():
                if entry.tags & tags:  # Intersection
                    to_remove.append(key)
            
            for key in to_remove:
                del self._cache[key]
            
            return len(to_remove)
    
    def invalidate_by_dependencies(self, dependency_hashes: set[str]) -> int:
        """Invalidate all entries that depend on given hashes."""
        with self._lock:
            to_remove = []
            for key, entry in self._cache.items():
                if entry.dependencies & dependency_hashes:
                    to_remove.append(key)
            
            for key in to_remove:
                del self._cache[key]
            
            return len(to_remove)
    
    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_size = sum(entry.size_bytes for entry in self._cache.values())
            total_accesses = sum(entry.access_count for entry in self._cache.values())
            
            return {
                'name': self.name,
                'entry_count': len(self._cache),
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'total_accesses': total_accesses,
                'avg_accesses_per_entry': total_accesses / max(len(self._cache), 1),
            }


class DiskCache:
    """Persistent disk cache with compression."""
    
    def __init__(self, cache_dir: Path, max_size_gb: float = 2.0):
        """
        Initialize disk cache.
        
        Args:
            cache_dir: Directory for cache files
            max_size_gb: Maximum cache size in GB
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)
        self.db_path = self.cache_dir / "metadata.db"
        
        self._init_database()
        self._lock = threading.RLock()
    
    def _init_database(self):
        """Initialize SQLite database for metadata."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    content_hash TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    size_bytes INTEGER NOT NULL,
                    compression_ratio REAL DEFAULT 1.0,
                    tags TEXT DEFAULT '',
                    dependencies TEXT DEFAULT ''
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_accessed 
                ON cache_entries(last_accessed)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_size_bytes 
                ON cache_entries(size_bytes)
            """)
    
    def _get_file_path(self, content_hash: str) -> Path:
        """Get file path for content hash with directory sharding."""
        # Use first 2 chars for directory sharding
        dir_name = content_hash[:2]
        cache_subdir = self.cache_dir / dir_name
        cache_subdir.mkdir(exist_ok=True)
        return cache_subdir / f"{content_hash[2:]}.zst"
    
    def put(self, content_hash: str, data: Any, 
            tags: set[str] = None, dependencies: set[str] = None) -> bool:
        """Store data to disk with compression."""
        try:
            with self._lock:
                # Serialize data
                serialized = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)

                # Compress data
                if ZSTD_AVAILABLE:
                    compressed = zstd.compress(serialized, level=3)  # Fast compression
                    compression_ratio = len(compressed) / len(serialized)
                else:
                    compressed = serialized
                    compression_ratio = 1.0
                
                # Write to file
                file_path = self._get_file_path(content_hash)
                with open(file_path, 'wb') as f:
                    f.write(compressed)
                
                # Update database
                now = datetime.now().isoformat()
                tags_str = ','.join(tags) if tags else ''
                deps_str = ','.join(dependencies) if dependencies else ''
                
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO cache_entries 
                        (content_hash, file_path, created_at, last_accessed, 
                         size_bytes, compression_ratio, tags, dependencies)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (content_hash, str(file_path), now, now, 
                          len(compressed), compression_ratio, tags_str, deps_str))
                
                # Check if we need to evict old entries
                self._evict_if_needed()
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to store to disk cache: {e}")
            return False
    
    def get(self, content_hash: str) -> Any | None:
        """Retrieve data from disk cache."""
        try:
            with self._lock:
                # Check if entry exists in database
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("""
                        SELECT file_path, access_count 
                        FROM cache_entries 
                        WHERE content_hash = ?
                    """, (content_hash,))
                    
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    file_path, access_count = row
                    
                    # Update access statistics
                    now = datetime.now().isoformat()
                    conn.execute("""
                        UPDATE cache_entries 
                        SET last_accessed = ?, access_count = ?
                        WHERE content_hash = ?
                    """, (now, access_count + 1, content_hash))
                
                # Read and decompress file
                file_path = Path(file_path)
                if not file_path.exists():
                    # File missing, clean up database entry
                    self._remove_entry(content_hash)
                    return None
                
                with open(file_path, 'rb') as f:
                    compressed_data = f.read()

                # Decompress and deserialize
                if ZSTD_AVAILABLE:
                    serialized = zstd.decompress(compressed_data)
                else:
                    serialized = compressed_data
                data = pickle.loads(serialized)
                
                return data
                
        except Exception as e:
            logger.error(f"Failed to retrieve from disk cache: {e}")
            return None
    
    def exists(self, content_hash: str) -> bool:
        """Check if entry exists in disk cache."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 1 FROM cache_entries WHERE content_hash = ?
            """, (content_hash,))
            return cursor.fetchone() is not None
    
    def _evict_if_needed(self):
        """Evict old entries if cache is too large."""
        with sqlite3.connect(self.db_path) as conn:
            # Check total cache size
            cursor = conn.execute("SELECT SUM(size_bytes) FROM cache_entries")
            total_size = cursor.fetchone()[0] or 0
            
            if total_size > self.max_size_bytes:
                # Evict oldest entries (LRU)
                target_size = int(self.max_size_bytes * 0.8)  # Evict to 80% capacity
                bytes_to_remove = total_size - target_size
                
                cursor = conn.execute("""
                    SELECT content_hash, file_path, size_bytes
                    FROM cache_entries 
                    ORDER BY last_accessed ASC
                """)
                
                removed_bytes = 0
                for content_hash, file_path, size_bytes in cursor:
                    if removed_bytes >= bytes_to_remove:
                        break
                    
                    # Remove file and database entry
                    try:
                        Path(file_path).unlink(missing_ok=True)
                        conn.execute("DELETE FROM cache_entries WHERE content_hash = ?", 
                                   (content_hash,))
                        removed_bytes += size_bytes
                    except Exception as e:
                        logger.warning(f"Failed to remove cache file {file_path}: {e}")
                
                logger.info(f"Evicted {removed_bytes / (1024*1024):.1f}MB from disk cache")
    
    def _remove_entry(self, content_hash: str):
        """Remove entry from database and file system."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT file_path FROM cache_entries WHERE content_hash = ?
            """, (content_hash,))
            
            row = cursor.fetchone()
            if row:
                file_path = Path(row[0])
                file_path.unlink(missing_ok=True)
                
                conn.execute("DELETE FROM cache_entries WHERE content_hash = ?", 
                           (content_hash,))
    
    def invalidate_by_tags(self, tags: set[str]) -> int:
        """Invalidate entries by tags."""
        if not tags:
            return 0
        
        removed_count = 0
        with sqlite3.connect(self.db_path) as conn:
            # Find entries with matching tags
            tag_conditions = ' OR '.join(['tags LIKE ?' for _ in tags])
            query = f"SELECT content_hash, file_path FROM cache_entries WHERE {tag_conditions}"
            params = [f'%{tag}%' for tag in tags]
            
            cursor = conn.execute(query, params)
            for content_hash, file_path in cursor:
                try:
                    Path(file_path).unlink(missing_ok=True)
                    conn.execute("DELETE FROM cache_entries WHERE content_hash = ?", 
                               (content_hash,))
                    removed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to remove cache entry {content_hash}: {e}")
        
        return removed_count
    
    def get_stats(self) -> dict[str, Any]:
        """Get disk cache statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as entry_count,
                    SUM(size_bytes) as total_size,
                    AVG(size_bytes) as avg_size,
                    AVG(compression_ratio) as avg_compression,
                    SUM(access_count) as total_accesses
                FROM cache_entries
            """)
            
            row = cursor.fetchone()
            entry_count, total_size, avg_size, avg_compression, total_accesses = row
            
            return {
                'entry_count': entry_count or 0,
                'total_size_bytes': total_size or 0,
                'total_size_mb': (total_size or 0) / (1024 * 1024),
                'avg_size_bytes': avg_size or 0,
                'avg_compression_ratio': avg_compression or 1.0,
                'total_accesses': total_accesses or 0,
                'max_size_gb': self.max_size_bytes / (1024 * 1024 * 1024),
            }
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            # Remove all files
            for cache_file in self.cache_dir.rglob("*.zst"):
                try:
                    cache_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove cache file {cache_file}: {e}")
            
            # Clear database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache_entries")


class SpeedrunCache(ConversionCache):
    """Enhanced conversion cache with speedrun optimizations."""
    
    def __init__(self, 
                 cache_dir: Path | None = None,
                 enable_disk_cache: bool = True,
                 disk_cache_size_gb: float = 2.0,
                 enable_content_addressing: bool = True,
                 **kwargs):
        """
        Initialize speedrun cache.
        
        Args:
            cache_dir: Directory for disk cache (default: ~/.cache/svg2pptx)
            enable_disk_cache: Whether to enable persistent disk cache
            disk_cache_size_gb: Maximum disk cache size in GB
            enable_content_addressing: Use content-addressable caching
            **kwargs: Arguments passed to parent ConversionCache
        """
        super().__init__(**kwargs)
        
        # Set up cache directory
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "svg2pptx"
        self.cache_dir = Path(cache_dir)
        
        # Initialize enhanced caches
        self.enable_content_addressing = enable_content_addressing
        if enable_content_addressing:
            self.content_cache = ContentAddressableCache("main")
        
        self.enable_disk_cache = enable_disk_cache
        if enable_disk_cache:
            self.disk_cache = DiskCache(self.cache_dir, disk_cache_size_gb)
        
        # Cache warming state
        self._warming_enabled = False
        self._warm_cache_thread = None
        
        logger.info(f"SpeedrunCache initialized with cache_dir={self.cache_dir}")
    
    def get_with_content_addressing(self, content: Any, 
                                   context: dict[str, Any] = None,
                                   tags: set[str] = None) -> Any | None:
        """Get data using content-addressable caching."""
        if not self.enable_content_addressing:
            return None
        
        content_hash = self.content_cache.generate_content_hash(content, context)
        
        # Try memory cache first
        result = self.content_cache.get(content_hash)
        if result is not None:
            return result
        
        # Try disk cache if enabled
        if self.enable_disk_cache:
            result = self.disk_cache.get(content_hash)
            if result is not None:
                # Warm memory cache
                self.content_cache.put(content_hash, result, tags=tags)
                return result
        
        return None
    
    def put_with_content_addressing(self, content: Any, data: Any,
                                   context: dict[str, Any] = None,
                                   tags: set[str] = None,
                                   dependencies: set[str] = None,
                                   persist_to_disk: bool = True) -> str:
        """Store data using content-addressable caching."""
        if not self.enable_content_addressing:
            return ""
        
        content_hash = self.content_cache.generate_content_hash(content, context)
        
        # Store in memory cache
        self.content_cache.put(content_hash, data, dependencies, tags)
        
        # Store in disk cache if enabled and requested
        if self.enable_disk_cache and persist_to_disk:
            self.disk_cache.put(content_hash, data, tags, dependencies)
        
        return content_hash
    
    def invalidate_by_tags(self, tags: set[str]) -> dict[str, int]:
        """Invalidate entries across all cache layers by tags."""
        results = {}
        
        if self.enable_content_addressing:
            results['memory'] = self.content_cache.invalidate_by_tags(tags)
        
        if self.enable_disk_cache:
            results['disk'] = self.disk_cache.invalidate_by_tags(tags)
        
        return results
    
    def get_enhanced_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats = {
            'base_cache': super().get_total_stats(),
            'memory_usage': super().get_memory_usage(),
        }
        
        if self.enable_content_addressing:
            stats['content_cache'] = self.content_cache.get_stats()
        
        if self.enable_disk_cache:
            stats['disk_cache'] = self.disk_cache.get_stats()
        
        return stats
    
    def start_cache_warming(self, svg_patterns: list[str] = None):
        """Start background cache warming process."""
        if self._warming_enabled:
            return
        
        self._warming_enabled = True
        
        def warm_cache():
            """Background cache warming worker."""
            logger.info("Cache warming started")
            
            # Common SVG patterns to pre-compute
            common_patterns = svg_patterns or [
                '<rect>',
                '<circle>',
                '<path>',
                '<text>',
                '<g>',
                '<line>',
                '<polygon>',
            ]
            
            # Pre-warm with common geometric operations
            for pattern in common_patterns:
                if not self._warming_enabled:
                    break
                
                try:
                    # Simulate common operations
                    element = ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{pattern}</svg>')
                    
                    # Pre-compute common transformations
                    common_transforms = [
                        "translate(10,10)",
                        "scale(2,2)",
                        "rotate(45)",
                        "matrix(1,0,0,1,0,0)",
                    ]
                    
                    for transform in common_transforms:
                        if not self._warming_enabled:
                            break
                        
                        context = {'transform': transform}
                        content_hash = self.content_cache.generate_content_hash(
                            element, context,
                        ) if self.enable_content_addressing else None
                        
                        # Only warm if not already cached
                        if content_hash and not self.content_cache.exists(content_hash):
                            # Pre-compute result (simplified for warming)
                            result = f"cached_{pattern}_{transform}"
                            self.put_with_content_addressing(
                                element, result, context,
                                tags={'warmup'}, persist_to_disk=False,
                            )
                    
                    time.sleep(0.01)  # Small delay to avoid overwhelming
                    
                except Exception as e:
                    logger.warning(f"Cache warming error for {pattern}: {e}")
            
            logger.info("Cache warming completed")
        
        if self._warm_cache_thread is None or not self._warm_cache_thread.is_alive():
            self._warm_cache_thread = threading.Thread(target=warm_cache, daemon=True)
            self._warm_cache_thread.start()
    
    def stop_cache_warming(self):
        """Stop background cache warming."""
        self._warming_enabled = False
        if self._warm_cache_thread and self._warm_cache_thread.is_alive():
            self._warm_cache_thread.join(timeout=5.0)
    
    def clear_all(self):
        """Clear all cache layers."""
        super().clear_all()
        
        if self.enable_content_addressing:
            self.content_cache._cache.clear()
        
        if self.enable_disk_cache:
            self.disk_cache.clear()


# Global speedrun cache instance
_global_speedrun_cache = None

def get_speedrun_cache() -> SpeedrunCache:
    """Get or create the global speedrun cache."""
    global _global_speedrun_cache
    if _global_speedrun_cache is None:
        _global_speedrun_cache = SpeedrunCache()
    return _global_speedrun_cache


def enable_speedrun_mode(cache_dir: Path | None = None,
                        disk_cache_size_gb: float = 2.0,
                        start_warming: bool = True) -> SpeedrunCache:
    """Enable speedrun cache mode for maximum performance."""
    global _global_speedrun_cache
    
    _global_speedrun_cache = SpeedrunCache(
        cache_dir=cache_dir,
        enable_disk_cache=True,
        disk_cache_size_gb=disk_cache_size_gb,
        enable_content_addressing=True,
    )
    
    if start_warming:
        _global_speedrun_cache.start_cache_warming()
    
    logger.info("Speedrun cache mode enabled")
    return _global_speedrun_cache