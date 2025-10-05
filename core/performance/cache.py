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
import json
import pickle
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple

from lxml import etree as ET


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
    
    def __init__(self, max_size: int = 1000, ttl: float | None = None):
        self.max_size = max_size
        self.ttl = ttl  # Time to live in seconds
        self._cache: dict[str, Any] = {}
        self._timestamps: dict[str, float] = {}
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
    
    def get(self, key: str) -> Any | None:
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
    
    def get_parsed_path(self, path_data: str) -> list[tuple[str, list[float]]] | None:
        """Get parsed path commands using modern PathSystem."""
        try:
            # Use PathSystem for modern path processing
            if not hasattr(self, '_path_system') or self._path_system is None:
                from ..paths import create_path_system
                self._path_system = create_path_system(800, 600, (0, 0, 800, 600))

            result = self._path_system.process_path(path_data)

            # Convert to legacy format for compatibility
            commands = []
            for cmd in result.commands:
                coords = []
                for pt in cmd.coordinates:
                    coords.extend([pt.x, pt.y])
                commands.append((cmd.command_type.value.upper(), coords))
            return commands

        except ImportError:
            # Fallback to cache-based approach
            key = f"parse:{self._generate_key(path_data)}"
            return self.get(key)
        except Exception:
            # Fallback to cache-based approach
            key = f"parse:{self._generate_key(path_data)}"
            return self.get(key)

    def cache_parsed_path(self, path_data: str, parsed_commands: list[tuple[str, list[float]]]):
        """Cache parsed path commands - PathSystem has built-in efficiency."""
        try:
            # PathSystem has optimized processing, so explicit caching is less needed
            # Just validate that PathSystem can parse this data
            if not hasattr(self, '_path_system') or self._path_system is None:
                from ..paths import create_path_system
                self._path_system = create_path_system(800, 600, (0, 0, 800, 600))

            self._path_system.process_path(path_data)  # This validates the path

        except ImportError:
            # Fallback to local caching
            key = f"parse:{self._generate_key(path_data)}"
            self.put(key, parsed_commands)
        except Exception:
            # Fallback to local caching
            key = f"parse:{self._generate_key(path_data)}"
            self.put(key, parsed_commands)
    
    def get_simplified_path(self, path_data: str, tolerance: float) -> str | None:
        """Get simplified path from cache."""
        key = f"simplify:{self._generate_key(path_data, tolerance)}"
        return self.get(key)
    
    def cache_simplified_path(self, path_data: str, tolerance: float, simplified: str):
        """Cache simplified path."""
        key = f"simplify:{self._generate_key(path_data, tolerance)}"
        self.put(key, simplified)
    
    def get_path_bounds(self, path_data: str) -> tuple[float, float, float, float] | None:
        """Get path bounding box from cache."""
        key = f"bounds:{self._generate_key(path_data)}"
        return self.get(key)
    
    def cache_path_bounds(self, path_data: str, bounds: tuple[float, float, float, float]):
        """Cache path bounding box."""
        key = f"bounds:{self._generate_key(path_data)}"
        self.put(key, bounds)
    
    def get_path_complexity(self, path_data: str) -> int | None:
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
    
    def get_parsed_color(self, color_str: str) -> tuple[int, int, int, float] | None:
        """Get parsed color (RGBA) from cache."""
        key = f"parse:{self._generate_key(color_str)}"
        return self.get(key)
    
    def cache_parsed_color(self, color_str: str, rgba: tuple[int, int, int, float]):
        """Cache parsed color."""
        key = f"parse:{self._generate_key(color_str)}"
        self.put(key, rgba)
    
    def get_gradient_definition(self, gradient_id: str) -> dict | None:
        """Get gradient definition from cache."""
        key = f"gradient:{self._generate_key(gradient_id)}"
        return self.get(key)
    
    def cache_gradient_definition(self, gradient_id: str, definition: dict):
        """Cache gradient definition."""
        key = f"gradient:{self._generate_key(gradient_id)}"
        self.put(key, definition)
    
    def get_powerpoint_color(self, svg_color: str) -> str | None:
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
    
    def get_parsed_transform(self, transform_str: str) -> list[list[float]] | None:
        """Get parsed transform matrix using canonical TransformEngine cache."""
        try:
            # Delegate to TransformEngine which has superior built-in caching
            from ..transforms import TransformEngine

            engine = services.transform_parser
            matrix = engine.parse_to_matrix(transform_str)

            # Convert Matrix to expected legacy format
            if hasattr(matrix, 'to_array'):
                return matrix.to_array()
            elif hasattr(matrix, 'a'):  # Matrix class format
                # Convert Matrix [a,b,c,d,e,f] to 3x3 array format
                return [
                    [matrix.a, matrix.c, matrix.e],
                    [matrix.b, matrix.d, matrix.f],
                    [0.0, 0.0, 1.0],
                ]
            else:
                return None

        except ImportError:
            # Fallback to cache-based approach
            key = f"parse:{self._generate_key(transform_str)}"
            return self.get(key)
        except Exception:
            # Fallback to cache-based approach
            key = f"parse:{self._generate_key(transform_str)}"
            return self.get(key)

    def cache_parsed_transform(self, transform_str: str, matrix: list[list[float]]):
        """Cache parsed transform matrix - now delegates to TransformEngine's superior caching."""
        try:
            # TransformEngine has built-in caching, so we don't need to cache here
            # Just validate that TransformEngine can parse this data
            from ..transforms import TransformEngine

            engine = services.transform_parser
            engine.parse_to_matrix(transform_str)  # This will cache internally

        except ImportError:
            # Fallback to local caching
            key = f"parse:{self._generate_key(transform_str)}"
            self.put(key, matrix)
        except Exception:
            # Fallback to local caching
            key = f"parse:{self._generate_key(transform_str)}"
            self.put(key, matrix)
    
    def get_combined_transform(self, *transforms: str) -> list[list[float]] | None:
        """Get combined transform matrix from cache."""
        key = f"combine:{self._generate_key(*transforms)}"
        return self.get(key)
    
    def cache_combined_transform(self, transforms: tuple[str, ...], matrix: list[list[float]]):
        """Cache combined transform matrix."""
        key = f"combine:{self._generate_key(*transforms)}"
        self.put(key, matrix)
    
    def get_applied_transform(self, transform_str: str, x: float, y: float) -> tuple[float, float] | None:
        """Get transformed coordinates from cache."""
        key = f"apply:{self._generate_key(transform_str, x, y)}"
        return self.get(key)
    
    def cache_applied_transform(self, transform_str: str, x: float, y: float, result: tuple[float, float]):
        """Cache transformed coordinates."""
        key = f"apply:{self._generate_key(transform_str, x, y)}"
        self.put(key, result)


class FilterCache(BaseCache):
    """Cache for complex filter result operations with EMF storage."""

    def __init__(self, max_size: int = 400):
        super().__init__(max_size, ttl=600)  # 10 min TTL for filter results
        self._filter_combination_cache = {}
        self._performance_stats = {
            'repeated_patterns': defaultdict(int),
            'optimization_applied': 0,
            'consistency_checks': 0,
            'consistency_failures': 0,
        }

    def generate_filter_cache_key(self, filter_chain: list[ET.Element], context: dict) -> str:
        """Generate unique cache key for filter combination."""
        key_data = {
            'filter_elements': [self._serialize_filter_element(f) for f in filter_chain],
            'input_hash': self._hash_input_data(context.get('input_data', {})),
            'parameters': context.get('filter_parameters', {}),
            'coordinate_system': context.get('coordinate_system', {}),
            'viewport': context.get('viewport', {}),
            'transform_chain': context.get('transform_chain', []),
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.blake2b(key_str.encode()).hexdigest()

    def _serialize_filter_element(self, element: ET.Element) -> dict:
        """Serialize filter element to deterministic dictionary."""
        return {
            'tag': element.tag.split('}')[-1] if '}' in element.tag else element.tag,
            'attributes': dict(element.attrib),
            'text': element.text if element.text else None,
            'children': [self._serialize_filter_element(child) for child in element],
        }

    def _hash_input_data(self, input_data: dict) -> str:
        """Generate hash for input data."""
        if not input_data:
            return "empty_input"

        # Create deterministic representation
        input_str = json.dumps(input_data, sort_keys=True)
        return hashlib.md5(input_str.encode()).hexdigest()

    def get_filter_result(self, filter_chain: list[ET.Element], context: dict) -> dict | None:
        """Get cached filter result for filter combination."""
        key = self.generate_filter_cache_key(filter_chain, context)
        return self.get(key)

    def cache_filter_result(self, filter_chain: list[ET.Element], context: dict, result: dict):
        """Cache filter result for filter combination."""
        key = self.generate_filter_cache_key(filter_chain, context)

        # Add metadata to result
        cached_result = {
            **result,
            'cache_key': key,
            'cached_at': time.time(),
            'filter_count': len(filter_chain),
            'complexity_score': self._calculate_complexity_score(filter_chain),
        }

        self.put(key, cached_result)

    def _calculate_complexity_score(self, filter_chain: list[ET.Element]) -> float:
        """Calculate complexity score for filter chain."""
        complexity = 0.0

        for element in filter_chain:
            tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag

            # Base complexity by filter type
            complexity_map = {
                'feGaussianBlur': 1.0,
                'feColorMatrix': 1.5,
                'feConvolveMatrix': 3.0,
                'feComposite': 2.0,
                'feMorphology': 2.5,
                'feOffset': 0.5,
                'feFlood': 0.3,
                'feTurbulence': 3.5,
                'feDisplacementMap': 4.0,
                'feDiffuseLighting': 3.5,
                'feSpecularLighting': 3.5,
            }

            base_complexity = complexity_map.get(tag, 2.0)

            # Adjust for parameters
            if tag == 'feGaussianBlur':
                std_dev = float(element.get('stdDeviation', '1'))
                base_complexity *= (1 + std_dev / 10)
            elif tag == 'feConvolveMatrix':
                kernel_matrix = element.get('kernelMatrix', '')
                kernel_size = len(kernel_matrix.split()) if kernel_matrix else 9
                base_complexity *= (kernel_size / 9)

            complexity += base_complexity

        return complexity

    def get_emf_cached_result(self, cache_key: str) -> bytes | None:
        """Get EMF blob from cache by key."""
        result = self.get(cache_key)
        if result and 'emf_blob' in result:
            return result['emf_blob']
        return None

    def cache_emf_result(self, cache_key: str, emf_blob: bytes, metadata: dict = None):
        """Cache EMF blob result."""
        cached_result = {
            'emf_blob': emf_blob,
            'cached_at': time.time(),
            'type': 'emf_fallback',
            'metadata': metadata or {},
            'checksum': hashlib.md5(emf_blob).hexdigest() if emf_blob else None,
        }
        self.put(cache_key, cached_result)

    # Subtask 3.2.5: Cache invalidation and update strategies
    def invalidate_by_filter_types(self, filter_types: list[str]) -> int:
        """Invalidate cache entries containing specific filter types."""
        invalidated = 0
        with self._lock:
            to_remove = []
            for key, entry in self._cache.items():
                if 'metadata' in entry and 'filter_types' in entry['metadata']:
                    entry_filter_types = entry['metadata']['filter_types']
                    if any(ft in entry_filter_types for ft in filter_types):
                        to_remove.append(key)

            for key in to_remove:
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)
                invalidated += 1

        return invalidated

    def invalidate_by_complexity(self, min_complexity: float) -> int:
        """Invalidate cache entries above complexity threshold."""
        invalidated = 0
        with self._lock:
            to_remove = []
            for key, entry in self._cache.items():
                complexity = entry.get('complexity_score', 0.0)
                if complexity >= min_complexity:
                    to_remove.append(key)

            for key in to_remove:
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)
                invalidated += 1

        return invalidated

    def invalidate_by_age(self, max_age_seconds: float) -> int:
        """Invalidate cache entries older than specified age."""
        current_time = time.time()
        invalidated = 0
        with self._lock:
            to_remove = []
            for key, entry in self._cache.items():
                cached_at = entry.get('cached_at', 0)
                if current_time - cached_at > max_age_seconds:
                    to_remove.append(key)

            for key in to_remove:
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)
                invalidated += 1

        return invalidated

    # Subtask 3.2.6: Cache size management and cleanup systems
    def cleanup_by_usage_pattern(self) -> int:
        """Clean up cache based on usage patterns and performance metrics."""
        cleaned = 0
        current_time = time.time()

        with self._lock:
            # Identify entries for cleanup
            to_remove = []

            for key, entry in self._cache.items():
                # Remove entries that haven't been accessed recently
                last_access = self._timestamps.get(key, 0)
                if current_time - last_access > 3600:  # 1 hour
                    to_remove.append(key)
                    continue

                # Remove low-complexity entries if cache is getting full
                if len(self._cache) > self.max_size * 0.8:
                    complexity = entry.get('complexity_score', 0.0)
                    if complexity < 2.0:  # Low complexity threshold
                        to_remove.append(key)

            for key in to_remove:
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)
                cleaned += 1

        return cleaned

    def optimize_cache_layout(self) -> int:
        """Optimize cache layout for better performance."""
        with self._lock:
            # Sort entries by access frequency and complexity
            entries_by_priority = []
            for key, entry in self._cache.items():
                last_access = self._timestamps.get(key, 0)
                complexity = entry.get('complexity_score', 1.0)
                priority = complexity * (1.0 / max(time.time() - last_access, 1.0))
                entries_by_priority.append((priority, key, entry))

            # Keep only high-priority entries if over capacity
            entries_by_priority.sort(reverse=True)

            if len(entries_by_priority) > self.max_size:
                # Keep top entries
                to_keep = entries_by_priority[:self.max_size]
                new_cache = {}
                new_timestamps = {}

                for _, key, entry in to_keep:
                    new_cache[key] = entry
                    new_timestamps[key] = self._timestamps[key]

                removed = len(self._cache) - len(new_cache)
                self._cache = new_cache
                self._timestamps = new_timestamps

                return removed

        return 0

    # Subtask 3.2.7: Optimize cache performance for repeated filter patterns
    def track_repeated_pattern(self, cache_key: str):
        """Track repeated access patterns for optimization."""
        pattern_key = self._extract_pattern_key(cache_key)
        self._performance_stats['repeated_patterns'][pattern_key] += 1

        # Apply optimization for frequently accessed patterns
        if self._performance_stats['repeated_patterns'][pattern_key] > 5:
            self._apply_pattern_optimization(cache_key)

    def _extract_pattern_key(self, cache_key: str) -> str:
        """Extract pattern identifier from cache key."""
        # Simplified pattern extraction - in practice, this would analyze
        # the filter chain structure
        return cache_key[:16]  # Use first 16 chars as pattern identifier

    def _apply_pattern_optimization(self, cache_key: str):
        """Apply performance optimization for repeated patterns."""
        with self._lock:
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                if 'optimized' not in entry:
                    # Mark as optimized and increase priority
                    entry['optimized'] = True
                    entry['optimization_applied_at'] = time.time()
                    # Refresh timestamp to keep in cache longer
                    self._timestamps[cache_key] = time.time()
                    self._performance_stats['optimization_applied'] += 1

    def get_performance_metrics(self) -> dict:
        """Get cache performance metrics."""
        total_patterns = sum(self._performance_stats['repeated_patterns'].values())
        optimized_percentage = (
            self._performance_stats['optimization_applied'] / max(total_patterns, 1) * 100
        )

        return {
            **self._performance_stats,
            'total_pattern_accesses': total_patterns,
            'optimization_percentage': optimized_percentage,
            'cache_efficiency': self._stats.hit_rate,
            'current_size': len(self._cache),
        }

    # Subtask 3.2.8: Verify cached results maintain visual consistency
    def verify_result_consistency(self, cache_key: str, expected_checksum: str = None) -> bool:
        """Verify cached result maintains visual consistency."""
        self._performance_stats['consistency_checks'] += 1

        with self._lock:
            if cache_key not in self._cache:
                return False

            entry = self._cache[cache_key]

            # Check data integrity
            if 'emf_blob' in entry:
                stored_checksum = entry.get('checksum')
                if stored_checksum:
                    # Verify stored checksum
                    emf_blob = entry['emf_blob']
                    current_checksum = hashlib.md5(emf_blob).hexdigest()
                    if stored_checksum != current_checksum:
                        self._performance_stats['consistency_failures'] += 1
                        # Remove corrupted entry
                        self._cache.pop(cache_key, None)
                        self._timestamps.pop(cache_key, None)
                        return False

                # Check against expected checksum if provided
                if expected_checksum:
                    if stored_checksum != expected_checksum:
                        self._performance_stats['consistency_failures'] += 1
                        return False

            # Verify metadata consistency
            if not self._verify_metadata_consistency(entry):
                self._performance_stats['consistency_failures'] += 1
                return False

            return True

    def _verify_metadata_consistency(self, entry: dict) -> bool:
        """Verify metadata consistency in cache entry."""
        required_fields = ['cached_at', 'type']

        for field in required_fields:
            if field not in entry:
                return False

        # Check timestamp validity
        cached_at = entry.get('cached_at', 0)
        if cached_at <= 0 or cached_at > time.time():
            return False

        # Check complexity score validity
        complexity = entry.get('complexity_score', 0)
        if complexity < 0 or complexity > 100:  # Reasonable bounds
            return False

        return True

    def audit_cache_consistency(self) -> dict[str, Any]:
        """Perform comprehensive cache consistency audit."""
        audit_results = {
            'total_entries': len(self._cache),
            'consistent_entries': 0,
            'inconsistent_entries': 0,
            'corrupted_entries': 0,
            'removed_entries': 0,
        }

        to_remove = []

        for key in list(self._cache.keys()):
            if self.verify_result_consistency(key):
                audit_results['consistent_entries'] += 1
            else:
                audit_results['inconsistent_entries'] += 1
                to_remove.append(key)

        # Remove inconsistent entries
        with self._lock:
            for key in to_remove:
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)
                audit_results['removed_entries'] += 1

        audit_results['consistency_rate'] = (
            audit_results['consistent_entries'] / max(audit_results['total_entries'], 1)
        )

        return audit_results


class ConversionCache:
    """Main cache orchestrator for all conversion operations."""

    def __init__(self,
                 path_cache_size: int = 500,
                 color_cache_size: int = 200,
                 transform_cache_size: int = 300,
                 filter_cache_size: int = 400,
                 enable_emf_cache: bool = True):
        """Initialize all specialized caches."""
        self.path_cache = PathCache(path_cache_size)
        self.color_cache = ColorCache(color_cache_size)
        self.transform_cache = TransformCache(transform_cache_size)
        self.filter_cache = FilterCache(filter_cache_size)

        # EMF-based filter cache for complex operations
        if enable_emf_cache:
            try:
                from .filter_emf_cache import EMFFilterCacheManager
                self.emf_filter_cache = EMFFilterCacheManager()
            except ImportError:
                self.emf_filter_cache = None
        else:
            self.emf_filter_cache = None

        # Element-level caches
        self._element_style_cache = BaseCache(max_size=1000, ttl=300)  # 5 min TTL
        self._element_bounds_cache = BaseCache(max_size=800, ttl=300)
        self._drawingml_cache = BaseCache(max_size=400, ttl=600)  # 10 min TTL
    
    def cache_element_style(self, element: ET.Element, computed_style: dict):
        """Cache computed style for an element."""
        element_hash = self._hash_element(element)
        key = f"style:{element_hash}"
        self._element_style_cache.put(key, computed_style)
    
    def get_element_style(self, element: ET.Element) -> dict | None:
        """Get cached computed style for an element."""
        element_hash = self._hash_element(element)
        key = f"style:{element_hash}"
        return self._element_style_cache.get(key)
    
    def cache_element_bounds(self, element: ET.Element, bounds: tuple[float, float, float, float]):
        """Cache bounding box for an element."""
        element_hash = self._hash_element(element)
        key = f"bounds:{element_hash}"
        self._element_bounds_cache.put(key, bounds)
    
    def get_element_bounds(self, element: ET.Element) -> tuple[float, float, float, float] | None:
        """Get cached bounding box for an element."""
        element_hash = self._hash_element(element)
        key = f"bounds:{element_hash}"
        return self._element_bounds_cache.get(key)
    
    def cache_drawingml_output(self, element: ET.Element, context_hash: str, output: str):
        """Cache final DrawingML output for an element."""
        element_hash = self._hash_element(element)
        key = f"drawingml:{element_hash}:{context_hash}"
        self._drawingml_cache.put(key, output)
    
    def get_drawingml_output(self, element: ET.Element, context_hash: str) -> str | None:
        """Get cached DrawingML output for an element."""
        element_hash = self._hash_element(element)
        key = f"drawingml:{element_hash}:{context_hash}"
        return self._drawingml_cache.get(key)
    
    def _hash_element(self, element: ET.Element) -> str:
        """Create a hash of an XML element for caching."""
        element_str = ET.tostring(element, encoding='unicode')
        return hashlib.md5(element_str.encode()).hexdigest()
    
    def get_total_stats(self) -> dict[str, CacheStats]:
        """Get statistics for all caches."""
        return {
            'path_cache': self.path_cache.get_stats(),
            'color_cache': self.color_cache.get_stats(),
            'transform_cache': self.transform_cache.get_stats(),
            'filter_cache': self.filter_cache.get_stats(),
            'element_style_cache': self._element_style_cache.get_stats(),
            'element_bounds_cache': self._element_bounds_cache.get_stats(),
            'drawingml_cache': self._drawingml_cache.get_stats(),
        }
    
    def clear_all(self):
        """Clear all caches."""
        self.path_cache.clear()
        self.color_cache.clear()
        self.transform_cache.clear()
        self.filter_cache.clear()
        self._element_style_cache.clear()
        self._element_bounds_cache.clear()
        self._drawingml_cache.clear()
    
    def get_memory_usage(self) -> dict[str, int]:
        """Get memory usage for all caches."""
        stats = self.get_total_stats()
        memory_usage = {name: stat.memory_usage for name, stat in stats.items()}

        # Add EMF cache memory usage if available
        if self.emf_filter_cache:
            emf_stats = self.emf_filter_cache.get_cache_performance_stats()
            memory_usage['emf_filter_cache'] = emf_stats.get('memory_usage_bytes', 0)

        return memory_usage

    def cache_complex_filter_result(self,
                                  filter_chain: list[ET.Element],
                                  context: dict,
                                  result: dict) -> str | None:
        """
        Cache complex filter result using EMF storage.

        Args:
            filter_chain: List of filter elements
            context: Processing context
            result: Filter result containing EMF blob data

        Returns:
            Cache key if successful, None if EMF cache unavailable
        """
        if not self.emf_filter_cache:
            return None

        try:
            return self.emf_filter_cache.cache_complex_filter_result(
                filter_chain, context, result,
            )
        except Exception as e:
            # Log error but don't fail the operation
            print(f"Warning: Failed to cache EMF filter result: {e}")
            return None

    def get_cached_filter_result(self,
                               filter_chain: list[ET.Element],
                               context: dict) -> dict | None:
        """
        Get cached complex filter result from EMF storage.

        Args:
            filter_chain: List of filter elements
            context: Processing context

        Returns:
            Cached result if found, None otherwise
        """
        if not self.emf_filter_cache:
            return None

        try:
            return self.emf_filter_cache.get_cached_filter_result(
                filter_chain, context,
            )
        except Exception as e:
            print(f"Warning: Failed to retrieve EMF filter result: {e}")
            return None

    def invalidate_filter_cache(self, filter_types: list[str] = None) -> int:
        """
        Invalidate cached filter results.

        Args:
            filter_types: Specific filter types to invalidate, or None for all

        Returns:
            Number of entries invalidated
        """
        invalidated = 0

        # Invalidate regular filter cache
        if filter_types:
            # For regular cache, we need to check each entry
            # This is a simplified approach - in practice, you might want
            # to add filter type tracking to the regular cache too
            pass
        else:
            self.filter_cache.clear()

        # Invalidate EMF filter cache
        if self.emf_filter_cache:
            try:
                invalidated += self.emf_filter_cache.invalidate_filter_cache(filter_types)
            except Exception as e:
                print(f"Warning: Failed to invalidate EMF filter cache: {e}")

        return invalidated


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