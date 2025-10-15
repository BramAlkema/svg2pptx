import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.data.embedded_font import EmbeddingPermission
from core.services.font_embedding_rules import PermissionChecker


class TTFontStub:
    """Minimal TTFont stand-in exposing just the OS/2 lookup used by PermissionChecker."""

    def __init__(self, fs_type: int | None, has_table: bool = True, raises: bool = False):
        self.fs_type = fs_type
        self.has_table = has_table
        self.raises = raises
        self._os2 = SimpleNamespace(fsType=fs_type)

    def __contains__(self, item: str) -> bool:
        return item == "OS/2" and self.has_table

    def __getitem__(self, item: str):
        if item != "OS/2":
            raise KeyError(item)
        if self.raises:
            raise RuntimeError("OS/2 table broken")
        return self._os2


@pytest.mark.parametrize(
    ("fs_type", "expected_permission", "allowed"),
    [
        (0x0002, EmbeddingPermission.RESTRICTED, False),
        (0x0004, EmbeddingPermission.PREVIEW_PRINT, True),
        (0x0008, EmbeddingPermission.EDITABLE, True),
        (0x0100, EmbeddingPermission.NO_SUBSETTING, True),
        (0x0200, EmbeddingPermission.BITMAP_ONLY, True),
        (0x0000, EmbeddingPermission.INSTALLABLE, True),
    ],
)
def test_analyze_permission_decodes_fs_type_bits(fs_type, expected_permission, allowed):
    checker = PermissionChecker()
    font = TTFontStub(fs_type)

    permission = checker.analyze_permission(font)

    assert permission is expected_permission
    assert checker.is_embedding_allowed(font) is allowed


def test_analyze_permission_defaults_to_installable_when_table_missing():
    checker = PermissionChecker()
    font = TTFontStub(fs_type=None, has_table=False)

    permission = checker.analyze_permission(font)

    assert permission is EmbeddingPermission.INSTALLABLE
    assert checker.is_embedding_allowed(font) is True


def test_analyze_permission_falls_back_on_errors():
    checker = PermissionChecker()
    font = TTFontStub(fs_type=None, raises=True)

    permission = checker.analyze_permission(font)

    assert permission is EmbeddingPermission.INSTALLABLE
    assert checker.is_embedding_allowed(font) is True
