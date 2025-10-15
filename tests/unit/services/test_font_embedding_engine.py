#!/usr/bin/env python3
"""
Targeted tests for FontEmbeddingEngine decision paths.

These tests focus on character extraction, permission decoding, and the
subsetting workflow to provide coverage on the heaviest service module.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Set

import pytest

from core.data.embedded_font import EmbeddingPermission, FontSubsetRequest
from core.policy.font_embedding_policy import FontEmbeddingDecision
from core.services.font_embedding_cache import FontEmbeddingCache
from core.services.font_embedding_engine import FontEmbeddingEngine


@dataclass
class StubFontService:
    """Minimal stub for FontService used by the engine tests."""

    font: object
    load_calls: int = 0

    def load_font_from_path(self, font_path: str):
        self.load_calls += 1
        return self.font


class StubFont:
    """TTFont stand-in that exposes only what the engine inspects."""

    def __init__(self, fs_type: int | None):
        self._tables = {}
        if fs_type is not None:
            self._tables['OS/2'] = SimpleNamespace(fsType=fs_type)

    def __contains__(self, item: str) -> bool:
        return item in self._tables

    def __getitem__(self, item: str):
        return self._tables[item]


class StubSubsetter:
    """Track subsetting calls and return a configured payload."""

    def __init__(self, result: bytes | None = b"subset-bytes"):
        self.result = result
        self.calls = 0
        self.last_font = None
        self.last_request = None

    def create_subset(self, font, request):
        self.calls += 1
        self.last_font = font
        self.last_request = request
        return self.result


class FailOnCallSubsetter:
    """Subsetter that fails the test if invoked."""

    def create_subset(self, *args, **kwargs):
        pytest.fail("create_subset should not be called for this scenario")


class RecordingCache(FontEmbeddingCache):
    """Cache stub that records cache interactions for assertions."""

    def __init__(self):
        super().__init__()
        self.get_keys: list[str] = []
        self.success_calls: list[tuple[str, object]] = []
        self.failure_messages: list[str] = []

    def get(self, key: str):
        self.get_keys.append(key)
        return super().get(key)

    def record_success(self, key: str, embedded_font):
        self.success_calls.append((key, embedded_font))
        super().record_success(key, embedded_font)

    def record_failure(self, message: str):
        self.failure_messages.append(message)
        super().record_failure(message)


class AllowAllPolicy:
    """Policy stub that always allows embedding while recording calls."""

    def __init__(self):
        self.calls: list[tuple[object, object]] = []

    def evaluate(self, font, request):
        self.calls.append((font, request))
        return FontEmbeddingDecision(
            should_embed=True,
            permission=EmbeddingPermission.INSTALLABLE,
            reason=None,
        )


class ExplodingSubsetter:
    """Subsetter that raises to exercise failure telemetry."""

    def create_subset(self, *args, **kwargs):
        raise RuntimeError("subset explosion")


def build_subset_request(font_path: str, characters: Set[str], font_name: str = "StubFont") -> FontSubsetRequest:
    """Helper for building requests with minimal boilerplate."""
    return FontSubsetRequest(
        font_path=font_path,
        characters=characters,
        font_name=font_name,
        optimization_level="basic",
    )


def test_extract_characters_handles_iterables():
    engine = FontEmbeddingEngine()

    characters = engine.extract_characters_from_text(["ab", 1, "c "])

    assert characters == {"a", "b", "c", " "}


@pytest.mark.parametrize(
    ("fs_type", "expected"),
    [
        (None, EmbeddingPermission.INSTALLABLE),
        (0x0002, EmbeddingPermission.RESTRICTED),
        (0x0004, EmbeddingPermission.PREVIEW_PRINT),
        (0x0008, EmbeddingPermission.EDITABLE),
        (0x0100, EmbeddingPermission.NO_SUBSETTING),
        (0x0200, EmbeddingPermission.BITMAP_ONLY),
        (0x0000, EmbeddingPermission.INSTALLABLE),
    ],
)
def test_analyze_font_embedding_permission_interprets_bits(fs_type, expected):
    engine = FontEmbeddingEngine()
    font = StubFont(fs_type)

    permission = engine.analyze_font_embedding_permission(font)

    assert permission == expected


def test_create_font_subset_caches_results_and_tracks_success(tmp_path):
    font_path = tmp_path / "demo.ttf"
    font_path.write_bytes(b"placeholder font data")

    stub_font = StubFont(fs_type=0)
    font_service = StubFontService(font=stub_font)
    subsetter = StubSubsetter()
    engine = FontEmbeddingEngine(font_service=font_service, subsetter=subsetter)

    request = build_subset_request(str(font_path), {"A", "B"}, font_name="DemoFont")

    first_result = engine.create_font_subset(request)
    second_result = engine.create_font_subset(request)

    stats = engine.get_embedding_statistics()

    assert first_result is not None
    assert second_result is first_result  # cached object reused
    assert subsetter.calls == 1  # subsetting performed once
    assert subsetter.last_font is stub_font
    assert subsetter.last_request is request
    assert font_service.load_calls == 1  # font loaded once
    assert stats.successful_embeddings == 1
    assert stats.total_fonts_processed == 1


def test_create_font_subset_rejects_restricted_fonts(tmp_path):
    font_path = tmp_path / "restricted.ttf"
    font_path.write_bytes(b"restricted")

    restricted_font = StubFont(fs_type=0x0002)
    font_service = StubFontService(font=restricted_font)
    engine = FontEmbeddingEngine(font_service=font_service, subsetter=FailOnCallSubsetter())

    request = build_subset_request(str(font_path), {"X"}, font_name="RestrictedFont")

    result = engine.create_font_subset(request)
    stats = engine.get_embedding_statistics()

    assert result is None
    assert stats.failed_embeddings == 1
    assert stats.total_fonts_processed == 1
    assert stats.notes and "does not allow embedding" in stats.notes[0]


def test_create_font_subset_uses_injected_cache_and_policy(tmp_path):
    font_path = tmp_path / "policy.ttf"
    font_path.write_bytes(b"policy bytes")

    stub_font = StubFont(fs_type=0)
    font_service = StubFontService(font=stub_font)
    subsetter = StubSubsetter()
    cache = RecordingCache()
    policy = AllowAllPolicy()

    engine = FontEmbeddingEngine(
        font_service=font_service,
        subsetter=subsetter,
        cache=cache,
        font_policy=policy,
    )

    request = build_subset_request(str(font_path), {"P"}, font_name="PolicyFont")

    result = engine.create_font_subset(request)

    assert result is not None
    assert cache.get_keys and cache.get_keys[0] == request.get_cache_key()
    assert cache.success_calls and cache.success_calls[0][0] == request.get_cache_key()
    assert policy.calls and policy.calls[0][1] is request
    assert subsetter.calls == 1
    stats = engine.get_embedding_statistics()
    assert stats.successful_embeddings == 1


def test_create_font_subset_records_failure_when_subsetter_raises(tmp_path):
    font_path = tmp_path / "explode.ttf"
    font_path.write_bytes(b"boom")

    stub_font = StubFont(fs_type=0)
    font_service = StubFontService(font=stub_font)
    cache = RecordingCache()
    policy = AllowAllPolicy()

    engine = FontEmbeddingEngine(
        font_service=font_service,
        subsetter=ExplodingSubsetter(),
        cache=cache,
        font_policy=policy,
    )

    request = build_subset_request(str(font_path), {"Z"}, font_name="ExplodeFont")

    result = engine.create_font_subset(request)

    assert result is None
    assert cache.failure_messages
    assert "subset creation failed" in cache.failure_messages[0].lower()
    stats = engine.get_embedding_statistics()
    assert stats.failed_embeddings == 1
    assert font_service.load_calls == 1


def test_create_embedding_for_text_short_circuits_on_empty_text(tmp_path):
    engine = FontEmbeddingEngine(font_service=StubFontService(font=None))

    result = engine.create_embedding_for_text(str(tmp_path / "missing.ttf"), "")

    assert result is None


def test_create_embedding_for_text_delegates_to_create_font_subset(monkeypatch, tmp_path):
    font_path = tmp_path / "font.ttf"
    font_path.write_text("dummy")
    stub_font = StubFont(fs_type=0)
    engine = FontEmbeddingEngine(font_service=StubFontService(font=stub_font))

    called = {}

    def fake_create_font_subset(self, subset_request):
        called['font_path'] = subset_request.font_path
        called['characters'] = subset_request.characters
        return "embedded-font"

    monkeypatch.setattr(FontEmbeddingEngine, "create_font_subset", fake_create_font_subset)

    result = engine.create_embedding_for_text(str(font_path), ["AB", "C"], font_name="Fancy", optimization_level="aggressive")

    assert result == "embedded-font"
    assert called['font_path'] == str(font_path)
    assert called['characters'] == {"A", "B", "C"}


def test_batch_create_embeddings_handles_invalid_entries(monkeypatch):
    engine = FontEmbeddingEngine(font_service=StubFontService(font=None))
    created = []

    monkeypatch.setattr(
        FontEmbeddingEngine,
        "create_embedding_for_text",
        lambda self, font_path, text_content, font_name=None, optimization_level="basic": created.append((font_path, text_content, font_name)) or "ok",
    )

    mappings = [
        {'text': 'abc', 'font_path': '/tmp/font1.ttf'},
        {'text': '', 'font_path': '/tmp/font2.ttf'},  # invalid -> None
        {'text': 'xyz', 'font_path': '/tmp/font3.ttf', 'font_name': 'Fancy'},
        {'font_path': '/tmp/font4.ttf'},  # missing text -> None
    ]

    results = engine.batch_create_embeddings(mappings)

    assert results[0] == "ok"
    assert results[1] is None
    assert results[2] == "ok"
    assert results[3] is None
    assert created == [
        ('/tmp/font1.ttf', 'abc', None),
        ('/tmp/font3.ttf', 'xyz', 'Fancy'),
    ]


def test_estimate_subset_size_reduction_uses_font_metrics(monkeypatch, tmp_path):
    font_path = tmp_path / "metrics.ttf"
    font_path.write_bytes(b"x")

    class GlyphFont:
        def getGlyphSet(self):
            return {'a': None, 'b': None, 'c': None, 'd': None}

    font_service = StubFontService(font=GlyphFont())
    engine = FontEmbeddingEngine(font_service=font_service)

    monkeypatch.setattr(os.path, "getsize", lambda path: 1000)

    estimate = engine.estimate_subset_size_reduction(str(font_path), {'a', 'b'})

    assert estimate['estimated_reduction'] > 0
    assert estimate['original_size_bytes'] == 1000
    assert estimate['subset_glyphs'] == 2


def test_clear_cache_resets_state(tmp_path):
    font_path = tmp_path / "cached.ttf"
    font_path.write_bytes(b"cache")
    stub_font = StubFont(fs_type=0)
    font_service = StubFontService(font=stub_font)
    subsetter = StubSubsetter()
    engine = FontEmbeddingEngine(font_service=font_service, subsetter=subsetter)

    request = build_subset_request(str(font_path), {"X"})
    engine.create_font_subset(request)
    engine.clear_cache()

    cache_stats = engine.get_cache_stats()
    assert cache_stats['cached_subsets'] == 0
    stats = engine.get_embedding_statistics()
    assert stats.total_fonts_processed == 0
    assert stats.successful_embeddings == 0


def test_get_cache_stats_reports_latest_counts(tmp_path):
    font_path = tmp_path / "stats.ttf"
    font_path.write_bytes(b"font")
    stub_font = StubFont(fs_type=0)
    subsetter = StubSubsetter()
    engine = FontEmbeddingEngine(font_service=StubFontService(font=stub_font), subsetter=subsetter)

    request = build_subset_request(str(font_path), {"Z"})
    engine.create_font_subset(request)

    stats = engine.get_cache_stats()

    assert stats == {
        'cached_subsets': 1,
        'total_fonts_processed': 1,
        'successful_embeddings': 1,
        'failed_embeddings': 0,
    }
