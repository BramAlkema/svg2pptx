#!/usr/bin/env python3
"""
Raster fallback system using add_raster_32bpp for arbitrary filter operations.

This module provides a raster fallback mechanism for complex SVG filter operations
that cannot be efficiently represented in vector format. Uses EMF's add_raster_32bpp
function to embed high-quality raster representations.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from lxml import etree as ET
import time

try:
    from src.emf_blob import EMFBlob
    from src.performance.cache import ConversionCache
except ImportError:
    # Handle import for testing
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from emf_blob import EMFBlob
    from performance.cache import ConversionCache


@dataclass
class RasterFallbackConfig:
    """Configuration for raster fallback operations."""
    default_dpi: int = 150
    max_width: int = 2048
    max_height: int = 2048
    quality_threshold: float = 0.8
    complexity_threshold: float = 5.0
    enable_caching: bool = True
    compression_quality: int = 90


class RasterRenderer:
    """Base class for rendering SVG filters to raster format."""

    def __init__(self, config: RasterFallbackConfig = None):
        """Initialize raster renderer."""
        self.config = config or RasterFallbackConfig()

    def render_filter_to_bitmap(self,
                              filter_chain: List[ET.Element],
                              input_data: Dict[str, Any],
                              context: Dict[str, Any]) -> bytes:
        """
        Render filter chain to 32-bit RGBA bitmap.

        Args:
            filter_chain: List of filter elements to render
            input_data: Input graphics data
            context: Rendering context

        Returns:
            32-bit RGBA bitmap data (width * height * 4 bytes)
        """
        # Calculate render dimensions
        width, height = self._calculate_render_dimensions(input_data, context)

        # Create mock bitmap for demonstration
        # In a real implementation, this would use a graphics library like Skia, Cairo, or PIL
        bitmap_data = self._create_mock_bitmap(width, height, filter_chain)

        return bitmap_data

    def _calculate_render_dimensions(self,
                                   input_data: Dict[str, Any],
                                   context: Dict[str, Any]) -> Tuple[int, int]:
        """Calculate optimal render dimensions."""
        # Get base dimensions from input or context
        base_width = input_data.get('width', context.get('viewport', {}).get('width', 100))
        base_height = input_data.get('height', context.get('viewport', {}).get('height', 100))

        # Calculate DPI scaling
        dpi = context.get('dpi', self.config.default_dpi)
        scale_factor = dpi / 96.0  # 96 DPI is standard

        # Apply scaling
        render_width = int(base_width * scale_factor)
        render_height = int(base_height * scale_factor)

        # Clamp to maximum dimensions
        render_width = min(render_width, self.config.max_width)
        render_height = min(render_height, self.config.max_height)

        # Ensure minimum dimensions
        render_width = max(render_width, 1)
        render_height = max(render_height, 1)

        return render_width, render_height

    def _create_mock_bitmap(self,
                          width: int,
                          height: int,
                          filter_chain: List[ET.Element]) -> bytes:
        """
        Create mock bitmap data for demonstration.

        In a real implementation, this would render the actual filter effects.
        """
        # Create a simple pattern based on filter types
        bitmap = bytearray(width * height * 4)

        for y in range(height):
            for x in range(width):
                pixel_offset = (y * width + x) * 4

                # Create different patterns based on filter types
                if any(self._get_filter_type(f) == 'feGaussianBlur' for f in filter_chain):
                    # Blur pattern - gradient from center
                    center_x, center_y = width // 2, height // 2
                    distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
                    max_distance = (width ** 2 + height ** 2) ** 0.5 / 2
                    intensity = int(255 * (1 - min(distance / max_distance, 1)))

                    bitmap[pixel_offset] = intensity      # Red
                    bitmap[pixel_offset + 1] = intensity  # Green
                    bitmap[pixel_offset + 2] = intensity  # Blue
                    bitmap[pixel_offset + 3] = 255       # Alpha

                elif any(self._get_filter_type(f) == 'feColorMatrix' for f in filter_chain):
                    # Color matrix pattern - checkerboard with color shift
                    checker = (x // 16 + y // 16) % 2
                    if checker:
                        bitmap[pixel_offset] = 255        # Red
                        bitmap[pixel_offset + 1] = 0     # Green
                        bitmap[pixel_offset + 2] = 128   # Blue
                    else:
                        bitmap[pixel_offset] = 128       # Red
                        bitmap[pixel_offset + 1] = 255   # Green
                        bitmap[pixel_offset + 2] = 0     # Blue
                    bitmap[pixel_offset + 3] = 255       # Alpha

                else:
                    # Default pattern - simple gradient
                    bitmap[pixel_offset] = int(255 * x / width)      # Red
                    bitmap[pixel_offset + 1] = int(255 * y / height) # Green
                    bitmap[pixel_offset + 2] = 128                   # Blue
                    bitmap[pixel_offset + 3] = 255                   # Alpha

        return bytes(bitmap)

    def _get_filter_type(self, element: ET.Element) -> str:
        """Extract filter type from element."""
        tag = element.tag
        if '}' in tag:
            tag = tag.split('}')[1]
        return tag


class RasterFallbackManager:
    """Manager for raster fallback operations with EMF integration."""

    def __init__(self,
                 config: RasterFallbackConfig = None,
                 cache: ConversionCache = None):
        """
        Initialize raster fallback manager.

        Args:
            config: Raster fallback configuration
            cache: Cache system for storing results
        """
        self.config = config or RasterFallbackConfig()
        self.cache = cache
        self.renderer = RasterRenderer(self.config)

        # Statistics
        self.stats = {
            'fallbacks_created': 0,
            'cache_hits': 0,
            'total_render_time': 0.0,
            'average_complexity': 0.0
        }

    def should_use_raster_fallback(self,
                                 filter_chain: List[ET.Element],
                                 context: Dict[str, Any]) -> bool:
        """
        Determine if raster fallback should be used for filter chain.

        Args:
            filter_chain: List of filter elements
            context: Processing context

        Returns:
            True if raster fallback should be used
        """
        # Calculate complexity score
        complexity = self._calculate_filter_complexity(filter_chain)

        # Check against threshold
        if complexity > self.config.complexity_threshold:
            return True

        # Check for specific filter types that benefit from raster fallback
        raster_preferred_filters = {
            'feConvolveMatrix',
            'feTurbulence',
            'feDisplacementMap',
            'feDiffuseLighting',
            'feSpecularLighting'
        }

        for element in filter_chain:
            filter_type = self._get_filter_type(element)
            if filter_type in raster_preferred_filters:
                return True

        # Check for complex filter combinations
        if len(filter_chain) > 3:
            return True

        return False

    def create_raster_fallback(self,
                             filter_chain: List[ET.Element],
                             input_data: Dict[str, Any],
                             context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create raster fallback for filter chain.

        Args:
            filter_chain: List of filter elements
            input_data: Input graphics data
            context: Processing context

        Returns:
            Dictionary containing EMF blob and metadata
        """
        start_time = time.time()

        # Check cache first
        if self.config.enable_caching and self.cache:
            cache_key = self._generate_cache_key(filter_chain, input_data, context)
            cached_result = self._get_cached_fallback(cache_key)
            if cached_result:
                self.stats['cache_hits'] += 1
                return cached_result

        # Render filter to bitmap
        bitmap_data = self.renderer.render_filter_to_bitmap(
            filter_chain, input_data, context
        )

        # Calculate dimensions
        width, height = self.renderer._calculate_render_dimensions(input_data, context)

        # Create EMF blob with raster data
        emf_blob = self._create_emf_with_raster(width, height, bitmap_data)

        # Calculate metadata
        complexity = self._calculate_filter_complexity(filter_chain)
        render_time = time.time() - start_time

        result = {
            'emf_blob': emf_blob.finalize(),
            'width': width,
            'height': height,
            'fallback_type': 'raster_32bpp',
            'complexity_score': complexity,
            'render_time': render_time,
            'bitmap_size': len(bitmap_data),
            'filter_types': [self._get_filter_type(f) for f in filter_chain],
            'created_at': time.time()
        }

        # Cache result
        if self.config.enable_caching and self.cache:
            self._cache_fallback(cache_key, result)

        # Update statistics
        self.stats['fallbacks_created'] += 1
        self.stats['total_render_time'] += render_time
        self.stats['average_complexity'] = (
            (self.stats['average_complexity'] * (self.stats['fallbacks_created'] - 1) + complexity)
            / self.stats['fallbacks_created']
        )

        return result

    def _create_emf_with_raster(self,
                              width: int,
                              height: int,
                              bitmap_data: bytes) -> EMFBlob:
        """
        Create EMF blob containing raster data.

        Args:
            width: Bitmap width in pixels
            height: Bitmap height in pixels
            bitmap_data: 32-bit RGBA bitmap data

        Returns:
            EMF blob with embedded raster data
        """
        # Create EMF blob
        emf_blob = EMFBlob(width, height)

        # Add raster data using add_raster_32bpp
        brush_handle = emf_blob.add_raster_32bpp(width, height, bitmap_data)

        # Create a filled rectangle using the raster brush
        emf_blob.fill_rectangle(0, 0, width, height, brush_handle)

        return emf_blob

    def _calculate_filter_complexity(self, filter_chain: List[ET.Element]) -> float:
        """Calculate complexity score for filter chain."""
        complexity = 0.0

        complexity_map = {
            'feGaussianBlur': 1.0,
            'feColorMatrix': 1.5,
            'feConvolveMatrix': 4.0,
            'feComposite': 2.0,
            'feMorphology': 2.5,
            'feOffset': 0.5,
            'feFlood': 0.3,
            'feTurbulence': 5.0,
            'feDisplacementMap': 6.0,
            'feDiffuseLighting': 4.5,
            'feSpecularLighting': 4.5,
            'feComponentTransfer': 3.0
        }

        for element in filter_chain:
            filter_type = self._get_filter_type(element)
            base_complexity = complexity_map.get(filter_type, 2.0)

            # Adjust complexity based on parameters
            if filter_type == 'feGaussianBlur':
                std_dev = float(element.get('stdDeviation', '1'))
                base_complexity *= (1 + std_dev / 5)
            elif filter_type == 'feConvolveMatrix':
                kernel_matrix = element.get('kernelMatrix', '')
                kernel_size = len(kernel_matrix.split()) if kernel_matrix else 9
                base_complexity *= (kernel_size / 9)
            elif filter_type == 'feTurbulence':
                octaves = int(element.get('numOctaves', '4'))
                base_complexity *= (octaves / 4)

            complexity += base_complexity

        # Add penalty for long chains
        if len(filter_chain) > 2:
            complexity *= (1 + (len(filter_chain) - 2) * 0.3)

        return complexity

    def _get_filter_type(self, element: ET.Element) -> str:
        """Extract filter type from element."""
        tag = element.tag
        if '}' in tag:
            tag = tag.split('}')[1]
        return tag

    def _generate_cache_key(self,
                          filter_chain: List[ET.Element],
                          input_data: Dict[str, Any],
                          context: Dict[str, Any]) -> str:
        """Generate cache key for raster fallback."""
        # Use the cache system's filter cache key generation
        if self.cache and hasattr(self.cache, 'filter_cache'):
            return self.cache.filter_cache.generate_filter_cache_key(filter_chain, context)
        else:
            # Fallback key generation
            import hashlib
            import json
            key_data = {
                'filters': [self._get_filter_type(f) for f in filter_chain],
                'input': str(input_data),
                'context': str(context)
            }
            key_str = json.dumps(key_data, sort_keys=True)
            return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cached_fallback(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached raster fallback result."""
        if not self.cache:
            return None

        # Check EMF cache first
        if hasattr(self.cache, 'emf_filter_cache') and self.cache.emf_filter_cache:
            try:
                emf_blob = self.cache.emf_filter_cache.emf_cache.get_emf_cached_result(cache_key)
                if emf_blob:
                    return {
                        'emf_blob': emf_blob,
                        'fallback_type': 'raster_32bpp',
                        'cached': True
                    }
            except:
                pass

        return None

    def _cache_fallback(self, cache_key: str, result: Dict[str, Any]):
        """Cache raster fallback result."""
        if not self.cache:
            return

        # Cache in EMF cache
        if hasattr(self.cache, 'emf_filter_cache') and self.cache.emf_filter_cache:
            try:
                metadata = {
                    'fallback_type': result['fallback_type'],
                    'complexity_score': result['complexity_score'],
                    'render_time': result['render_time'],
                    'filter_types': result['filter_types']
                }
                self.cache.emf_filter_cache.emf_cache.cache_emf_result(
                    cache_key, result['emf_blob'], metadata
                )
            except Exception as e:
                print(f"Warning: Failed to cache raster fallback: {e}")

    def get_fallback_stats(self) -> Dict[str, Any]:
        """Get raster fallback statistics."""
        return {
            **self.stats,
            'config': {
                'default_dpi': self.config.default_dpi,
                'max_dimensions': f"{self.config.max_width}x{self.config.max_height}",
                'complexity_threshold': self.config.complexity_threshold,
                'caching_enabled': self.config.enable_caching
            }
        }

    def clear_fallback_cache(self):
        """Clear raster fallback cache."""
        if self.cache and hasattr(self.cache, 'emf_filter_cache'):
            try:
                self.cache.emf_filter_cache.emf_cache.clear_cache()
            except:
                pass

        # Reset stats
        self.stats = {key: 0 if isinstance(val, (int, float)) else val
                     for key, val in self.stats.items()}


# Global raster fallback manager instance
_global_raster_fallback_manager = None

def get_global_raster_fallback_manager() -> RasterFallbackManager:
    """Get or create the global raster fallback manager."""
    global _global_raster_fallback_manager
    if _global_raster_fallback_manager is None:
        _global_raster_fallback_manager = RasterFallbackManager()
    return _global_raster_fallback_manager