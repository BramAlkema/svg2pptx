"""
Policy module governing font embedding decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fontTools.ttLib import TTFont

from ..data.embedded_font import EmbeddingPermission, FontSubsetRequest
from ..services.font_embedding_rules import PermissionAnalyzer, PermissionChecker


class FontEmbeddingPolicyProtocol(Protocol):
    def evaluate(self, font: TTFont, request: FontSubsetRequest) -> "FontEmbeddingDecision": ...


@dataclass(frozen=True)
class FontEmbeddingDecision:
    """Decision output for font embedding policy."""

    should_embed: bool
    permission: EmbeddingPermission
    reason: str | None = None

    @property
    def embedding_allowed(self) -> bool:
        return self.permission != EmbeddingPermission.RESTRICTED


class FontEmbeddingPolicy:
    """Evaluate whether a font should be embedded and surfaced to PPTX."""

    def __init__(self, permission_checker: PermissionAnalyzer | None = None):
        self._permission_checker = permission_checker or PermissionChecker()

    def evaluate(self, font: TTFont, request: FontSubsetRequest) -> FontEmbeddingDecision:
        permission = self._permission_checker.analyze_permission(font)

        if permission == EmbeddingPermission.RESTRICTED:
            return FontEmbeddingDecision(
                should_embed=False,
                permission=permission,
                reason=f"Font {request.font_name or request.font_path} does not allow embedding",
            )

        return FontEmbeddingDecision(
            should_embed=True,
            permission=permission,
            reason=None,
        )


__all__ = [
    "FontEmbeddingDecision",
    "FontEmbeddingPolicy",
    "FontEmbeddingPolicyProtocol",
]
