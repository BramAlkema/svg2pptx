"""
Cache and statistics helper for font embedding operations.
"""

from __future__ import annotations

from typing import Dict, Optional

from ..data.embedded_font import EmbeddedFont, FontEmbeddingStats


class FontEmbeddingCache:
    """Caches subset results while tracking embedding statistics."""

    def __init__(self):
        self._cache: Dict[str, EmbeddedFont] = {}
        self._stats = FontEmbeddingStats()

    def get(self, key: str) -> Optional[EmbeddedFont]:
        """Return a cached subset if available."""
        return self._cache.get(key)

    def record_success(self, key: str, embedded_font: EmbeddedFont) -> None:
        """Store a successful embedding and update statistics."""
        self._cache[key] = embedded_font
        self._stats.add_successful_embedding(embedded_font)

    def record_failure(self, message: str) -> None:
        """Record an embedding failure."""
        self._stats.add_failed_embedding(message)

    def clear(self) -> None:
        """Reset cache and statistics."""
        self._cache.clear()
        self._stats = FontEmbeddingStats()

    def get_stats(self) -> FontEmbeddingStats:
        """Expose the current embedding statistics."""
        return self._stats

    def get_cache_stats(self) -> dict[str, int]:
        """Provide cache-focused statistics."""
        return {
            'cached_subsets': len(self._cache),
            'total_fonts_processed': self._stats.total_fonts_processed,
            'successful_embeddings': self._stats.successful_embeddings,
            'failed_embeddings': self._stats.failed_embeddings,
        }


__all__ = ["FontEmbeddingCache"]
