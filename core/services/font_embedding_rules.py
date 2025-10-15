"""
Font embedding permission helpers.

Encapsulates the logic used to interpret OS/2 fsType bits and determine
whether embedding is allowed for a font.
"""

from __future__ import annotations

from typing import Protocol

from fontTools.ttLib import TTFont

from ..data.embedded_font import EmbeddingPermission


class PermissionAnalyzer(Protocol):
    """Protocol describing permission checker behaviour."""

    def analyze_permission(self, font: TTFont) -> EmbeddingPermission: ...
    def is_embedding_allowed(self, font: TTFont) -> bool: ...


class PermissionChecker:
    """Decode OS/2 fsType permissions for font embedding decisions."""

    def analyze_permission(self, font: TTFont) -> EmbeddingPermission:
        """
        Analyze font embedding permissions from the OS/2 fsType field.

        Returns the most restrictive permission flag present on the font.
        """
        try:
            if 'OS/2' not in font:
                return EmbeddingPermission.INSTALLABLE

            os2_table = font['OS/2']
            fs_type = getattr(os2_table, 'fsType', 0)

            if fs_type & 0x0002:
                return EmbeddingPermission.RESTRICTED
            if fs_type & 0x0004:
                return EmbeddingPermission.PREVIEW_PRINT
            if fs_type & 0x0008:
                return EmbeddingPermission.EDITABLE
            if fs_type & 0x0100:
                return EmbeddingPermission.NO_SUBSETTING
            if fs_type & 0x0200:
                return EmbeddingPermission.BITMAP_ONLY
            return EmbeddingPermission.INSTALLABLE
        except Exception:
            return EmbeddingPermission.INSTALLABLE

    def is_embedding_allowed(self, font: TTFont) -> bool:
        """Return True when the font is permitted to be embedded."""
        permission = self.analyze_permission(font)
        return permission != EmbeddingPermission.RESTRICTED


__all__ = ["PermissionAnalyzer", "PermissionChecker"]
