#!/usr/bin/env python3
"""
Advanced caching system for SVG conversion operations.

This module provides specialized caches for expensive operations like:
- Path parsing and conversion
- Color parsing and computation
- Transform matrix calculations
- Element style resolution
"""

import hashlib
import pickle
from typing import Any, Dict, Optional, Union, Tuple, List
from functools import lru_cache, wraps
from dataclasses import dataclass
import xml.etree.ElementTree as ET
import time
import threading
from collections import defaultdict


@dataclass
class CacheStats:
    """Statistics for cache performance."""
    hits: int = 0
    misses: int = 0
    total_requests: int = 0
    memory_usage: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        return self.hits / max(self.total_requests, 1)
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        return self.misses / max(self.total_requests, 1)


class BaseCache:
    """Base cache implementation with statistics and size limits."""
    
    def __init__(self, max_size: int = 1000, ttl: Optional[float] = None):
        self.max_size = max_size
        self.ttl = ttl  # Time to live in seconds
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._stats = CacheStats()
        self._lock = threading.RLock()
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = f"{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired."""
        if self.ttl is None:
            return False
        
        timestamp = self._timestamps.get(key)
        if timestamp is None:
            return True
            
        return time.time() - timestamp > self.ttl
    
    def _evict_lru(self):
        """Evict least recently used entries if cache is full."""
        if len(self._cache) >= self.max_size:
            # Simple LRU: remove oldest timestamp
            oldest_key = min(self._timestamps.keys(), 
                           key=lambda k: self._timestamps[k])
            self._cache.pop(oldest_key, None)
            self._timestamps.pop(oldest_key, None)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            self._stats.total_requests += 1
            
            if key not in self._cache or self._is_expired(key):
                self._stats.misses += 1
                return None
            
            # Update timestamp for LRU
            self._timestamps[key] = time.time()
            self._stats.hits += 1
            return self._cache[key]
    
    def put(self, key: str, value: Any):
        """Put value in cache."""
        with self._lock:
            self._evict_lru()
            self._cache[key] = value
            self._timestamps[key] = time.time()
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            self._stats = CacheStats()
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            self._stats.memory_usage = len(pickle.dumps(self._cache))
            return self._stats


class PathCache(BaseCache):
    """Cache for SVG path parsing and conversion operations."""
    
    def __init__(self, max_size: int = 500):
        super().__init__(max_size)
        self._path_complexity_cache = {}
    
    def get_parsed_path(self, path_data: str) -> Optional[List[Tuple[str, List[float]]]]:
        """Get parsed path commands from cache."""
        key = f"parse:{self._generate_key(path_data)}"
        return self.get(key)
    
    def cache_parsed_path(self, path_data: str, parsed_commands: List[Tuple[str, List[float]]]):
        """Cache parsed path commands."""
        key = f"parse:{self._generate_key(path_data)}"
        self.put(key, parsed_commands)
    
    def get_simplified_path(self, path_data: str, tolerance: float) -> Optional[str]:
        """Get simplified path from cache."""
        key = f"simplify:{self._generate_key(path_data, tolerance)}"
        return self.get(key)
    
    def cache_simplified_path(self, path_data: str, tolerance: float, simplified: str):
        """Cache simplified path."""
        key = f"simplify:{self._generate_key(path_data, tolerance)}"
        self.put(key, simplified)
    
    def get_path_bounds(self, path_data: str) -> Optional[Tuple[float, float, float, float]]:
        """Get path bounding box from cache."""
        key = f"bounds:{self._generate_key(path_data)}"
        return self.get(key)
    
    def cache_path_bounds(self, path_data: str, bounds: Tuple[float, float, float, float]):
        """Cache path bounding box."""
        key = f"bounds:{self._generate_key(path_data)}"
        self.put(key, bounds)
    
    def get_path_complexity(self, path_data: str) -> Optional[int]:
        """Get path complexity score from cache."""
        key = f"complexity:{self._generate_key(path_data)}"
        return self.get(key)
    
    def cache_path_complexity(self, path_data: str, complexity: int):
        """Cache path complexity score."""
        key = f"complexity:{self._generate_key(path_data)}"
        self.put(key, complexity)


class ColorCache(BaseCache):
    """Cache for color parsing and conversion operations."""
    
    def __init__(self, max_size: int = 200):
        super().__init__(max_size)
    
    def get_parsed_color(self, color_str: str) -> Optional[Tuple[int, int, int, float]]:
        """Get parsed color (RGBA) from cache."""
        key = f"parse:{self._generate_key(color_str)}"
        return self.get(key)
    
    def cache_parsed_color(self, color_str: str, rgba: Tuple[int, int, int, float]):
        """Cache parsed color."""
        key = f"parse:{self._generate_key(color_str)}"
        self.put(key, rgba)
    
    def get_gradient_definition(self, gradient_id: str) -> Optional[Dict]:
        """Get gradient definition from cache."""
        key = f"gradient:{self._generate_key(gradient_id)}"
        return self.get(key)
    
    def cache_gradient_definition(self, gradient_id: str, definition: Dict):
        """Cache gradient definition."""
        key = f"gradient:{self._generate_key(gradient_id)}"
        self.put(key, definition)
    
    def get_powerpoint_color(self, svg_color: str) -> Optional[str]:
        """Get PowerPoint color conversion from cache."""
        key = f"pptx:{self._generate_key(svg_color)}"
        return self.get(key)
    
    def cache_powerpoint_color(self, svg_color: str, pptx_color: str):
        """Cache PowerPoint color conversion."""
        key = f"pptx:{self._generate_key(svg_color)}"
        self.put(key, pptx_color)


class TransformCache(BaseCache):
    """Cache for transform matrix calculations."""
    
    def __init__(self, max_size: int = 300):
        super().__init__(max_size)
    
    def get_parsed_transform(self, transform_str: str) -> Optional[List[List[float]]]:
        """Get parsed transform matrix from cache."""
        key = f"parse:{self._generate_key(transform_str)}"
        return self.get(key)
    
    def cache_parsed_transform(self, transform_str: str, matrix: List[List[float]]):
        """Cache parsed transform matrix."""
        key = f"parse:{self._generate_key(transform_str)}"
        self.put(key, matrix)
    
    def get_combined_transform(self, *transforms: str) -> Optional[List[List[float]]]:
        """Get combined transform matrix from cache."""
        key = f"combine:{self._generate_key(*transforms)}"
        return self.get(key)
    
    def cache_combined_transform(self, transforms: Tuple[str, ...], matrix: List[List[float]]):
        """Cache combined transform matrix."""
        key = f"combine:{self._generate_key(*transforms)}"
        self.put(key, matrix)
    
    def get_applied_transform(self, transform_str: str, x: float, y: float) -> Optional[Tuple[float, float]]:
        """Get transformed coordinates from cache."""
        key = f"apply:{self._generate_key(transform_str, x, y)}"
        return self.get(key)
    
    def cache_applied_transform(self, transform_str: str, x: float, y: float, result: Tuple[float, float]):
        """Cache transformed coordinates."""
        key = f"apply:{self._generate_key(transform_str, x, y)}"
        self.put(key, result)


class ConversionCache:
    """Main cache orchestrator for all conversion operations."""
    
    def __init__(self, 
                 path_cache_size: int = 500,
                 color_cache_size: int = 200,
                 transform_cache_size: int = 300):
        """Initialize all specialized caches."""
        self.path_cache = PathCache(path_cache_size)
        self.color_cache = ColorCache(color_cache_size)
        self.transform_cache = TransformCache(transform_cache_size)
        
        # Element-level caches
        self._element_style_cache = BaseCache(max_size=1000, ttl=300)  # 5 min TTL
        self._element_bounds_cache = BaseCache(max_size=800, ttl=300)
        self._drawingml_cache = BaseCache(max_size=400, ttl=600)  # 10 min TTL
    
    def cache_element_style(self, element: ET.Element, computed_style: Dict):
        """Cache computed style for an element."""
        element_hash = self._hash_element(element)
        key = f"style:{element_hash}"
        self._element_style_cache.put(key, computed_style)
    
    def get_element_style(self, element: ET.Element) -> Optional[Dict]:
        """Get cached computed style for an element."""
        element_hash = self._hash_element(element)
        key = f"style:{element_hash}"
        return self._element_style_cache.get(key)
    
    def cache_element_bounds(self, element: ET.Element, bounds: Tuple[float, float, float, float]):
        """Cache bounding box for an element."""
        element_hash = self._hash_element(element)
        key = f"bounds:{element_hash}"
        self._element_bounds_cache.put(key, bounds)
    
    def get_element_bounds(self, element: ET.Element) -> Optional[Tuple[float, float, float, float]]:
        """Get cached bounding box for an element."""
        element_hash = self._hash_element(element)
        key = f"bounds:{element_hash}"
        return self._element_bounds_cache.get(key)
    
    def cache_drawingml_output(self, element: ET.Element, context_hash: str, output: str):
        """Cache final DrawingML output for an element."""
        element_hash = self._hash_element(element)
        key = f"drawingml:{element_hash}:{context_hash}"
        self._drawingml_cache.put(key, output)
    
    def get_drawingml_output(self, element: ET.Element, context_hash: str) -> Optional[str]:
        """Get cached DrawingML output for an element."""
        element_hash = self._hash_element(element)
        key = f"drawingml:{element_hash}:{context_hash}"
        return self._drawingml_cache.get(key)
    
    def _hash_element(self, element: ET.Element) -> str:
        """Create a hash of an XML element for caching."""
        element_str = ET.tostring(element, encoding='unicode')
        return hashlib.md5(element_str.encode()).hexdigest()
    
    def get_total_stats(self) -> Dict[str, CacheStats]:
        """Get statistics for all caches."""
        return {
            'path_cache': self.path_cache.get_stats(),
            'color_cache': self.color_cache.get_stats(),
            'transform_cache': self.transform_cache.get_stats(),
            'element_style_cache': self._element_style_cache.get_stats(),
            'element_bounds_cache': self._element_bounds_cache.get_stats(),
            'drawingml_cache': self._drawingml_cache.get_stats(),
        }
    
    def clear_all(self):
        """Clear all caches."""
        self.path_cache.clear()
        self.color_cache.clear()
        self.transform_cache.clear()
        self._element_style_cache.clear()
        self._element_bounds_cache.clear()
        self._drawingml_cache.clear()
    
    def get_memory_usage(self) -> Dict[str, int]:
        """Get memory usage for all caches."""
        stats = self.get_total_stats()
        return {name: stat.memory_usage for name, stat in stats.items()}


def cached_method(cache_attr: str, key_func=None):
    """Decorator for caching method results."""
    def decorator(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            cache = getattr(self, cache_attr)
            
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = cache._generate_key(*args, **kwargs)
            
            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Compute and cache result
            result = method(self, *args, **kwargs)
            cache.put(key, result)
            return result
        
        return wrapper
    return decorator


# Global cache instance for singleton access
_global_cache = None

def get_global_cache() -> ConversionCache:
    """Get or create the global conversion cache."""
    global _global_cache
    if _global_cache is None:
        _global_cache = ConversionCache()
    return _global_cache