#!/usr/bin/env python3
"""Unit tests for font embedding policy and helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.data.embedded_font import EmbeddingPermission, FontSubsetRequest
from core.policy.font_embedding_policy import FontEmbeddingDecision, FontEmbeddingPolicy


class StubFont:
    """Simple TTFont stub with configurable fsType."""

    def __init__(self, fs_type: int | None):
        self.fs_type = fs_type
        self._os2 = SimpleNamespace(fsType=fs_type)

    def __contains__(self, item: str) -> bool:
        return item == 'OS/2' and self.fs_type is not None

    def __getitem__(self, item: str):
        if item != 'OS/2':
            raise KeyError(item)
        return self._os2


class StubPermissionChecker:
    """Deterministic permission checker for policy tests."""

    def __init__(self, permission: EmbeddingPermission):
        self.permission = permission
        self.calls = 0

    def analyze_permission(self, font):
        self.calls += 1
        return self.permission

    def is_embedding_allowed(self, font):
        return self.permission != EmbeddingPermission.RESTRICTED


@pytest.mark.parametrize(
    (
        "fs_type",
        "expected_permission",
        "should_embed",
    ),
    [
        (0x0002, EmbeddingPermission.RESTRICTED, False),
        (0x0004, EmbeddingPermission.PREVIEW_PRINT, True),
        (0x0008, EmbeddingPermission.EDITABLE, True),
        (0x0100, EmbeddingPermission.NO_SUBSETTING, True),
        (0x0200, EmbeddingPermission.BITMAP_ONLY, True),
        (0x0000, EmbeddingPermission.INSTALLABLE, True),
        (None, EmbeddingPermission.INSTALLABLE, True),
    ],
)
def test_policy_evaluates_permissions(fs_type, expected_permission, should_embed):
    font = StubFont(fs_type)
    request = FontSubsetRequest(font_path="demo.ttf", characters={'A'})
    policy = FontEmbeddingPolicy()

    decision = policy.evaluate(font, request)

    assert decision.permission == expected_permission
    assert decision.should_embed is should_embed
    if not should_embed:
        assert "does not allow embedding" in (decision.reason or "")


def test_policy_uses_injected_permission_checker():
    checker = StubPermissionChecker(permission=EmbeddingPermission.RESTRICTED)
    policy = FontEmbeddingPolicy(permission_checker=checker)
    font = StubFont(fs_type=None)
    request = FontSubsetRequest(font_path="font.ttf", characters={'B'})

    decision = policy.evaluate(font, request)

    assert checker.calls == 1
    assert decision.permission is EmbeddingPermission.RESTRICTED
    assert decision.should_embed is False
