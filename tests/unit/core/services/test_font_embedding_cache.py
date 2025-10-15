import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.data.embedded_font import EmbeddedFont, EmbeddingPermission
from core.services.font_embedding_cache import FontEmbeddingCache


def make_embedded_font(
    font_name: str = "DemoFont",
    original_size: int = 2048,
    data: bytes = b"\x00\x01\x02\x03",
) -> EmbeddedFont:
    """Create a minimal EmbeddedFont for cache tests."""
    return EmbeddedFont.create_from_font(
        font_name=font_name,
        font_data=data,
        characters={"A", "B"},
        original_size=original_size,
        embedding_permission=EmbeddingPermission.INSTALLABLE,
        embedding_allowed=True,
        file_format="ttf",
    )


def test_record_success_caches_font_and_updates_stats():
    cache = FontEmbeddingCache()
    embedded = make_embedded_font(original_size=4096)

    cache.record_success("demo-key", embedded)

    assert cache.get("demo-key") is embedded

    stats = cache.get_stats()
    assert stats.total_fonts_processed == 1
    assert stats.successful_embeddings == 1
    assert stats.failed_embeddings == 0
    assert stats.total_original_size == 4096
    assert stats.total_embedded_size == len(embedded.font_data)

    cache_stats = cache.get_cache_stats()
    assert cache_stats["cached_subsets"] == 1
    assert cache_stats["successful_embeddings"] == 1
    assert cache_stats["failed_embeddings"] == 0


def test_record_failure_registers_failure_without_cache_entry():
    cache = FontEmbeddingCache()

    cache.record_failure("subset failure")

    assert cache.get("missing-key") is None

    stats = cache.get_stats()
    assert stats.total_fonts_processed == 1
    assert stats.successful_embeddings == 0
    assert stats.failed_embeddings == 1
    assert stats.notes == ["subset failure"]


def test_clear_resets_cache_and_statistics():
    cache = FontEmbeddingCache()
    cache.record_success("demo", make_embedded_font())
    cache.record_failure("another failure")

    cache.clear()

    assert cache.get("demo") is None

    stats = cache.get_stats()
    assert stats.total_fonts_processed == 0
    assert stats.successful_embeddings == 0
    assert stats.failed_embeddings == 0
    assert stats.total_original_size == 0
    assert stats.total_embedded_size == 0
