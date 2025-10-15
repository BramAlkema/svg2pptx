#!/usr/bin/env python3
"""
Utilities for detecting archive/legacy imports in the svg2pptx codebase.

Shared by scripts and tests to keep guardrails consistent.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


DEFAULT_SCAN_ROOTS: Sequence[str] = (
    "core",
    "api",
    "cli",
    "pipeline",
    "presentationml",
    "tests",
    "adapters",
    "scripts",
)
EXCLUDED_SEGMENTS: set[str] = {
    "archive",
    "archive_old",
    "__pycache__",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "venv",
}


@dataclass(frozen=True)
class ImportHit:
    """Record of a Python file importing archive/legacy packages."""

    path: Path
    archive_imports: tuple[str, ...]
    legacy_imports: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path.as_posix(),
            "archive_imports": list(self.archive_imports),
            "legacy_imports": list(self.legacy_imports),
        }


def iter_python_files(root: Path, subroots: Sequence[str] | None = None) -> list[Path]:
    """Return repository-relative Python paths under the provided roots."""
    subroots = subroots or DEFAULT_SCAN_ROOTS
    files: list[Path] = []
    for relative in subroots:
        base = (root / relative).resolve()
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if any(segment in EXCLUDED_SEGMENTS for segment in path.parts):
                continue
            files.append(path.relative_to(root))
    return files


def _analyze_name(name: str | None) -> tuple[bool, bool]:
    if not name:
        return False, False
    segments = [segment for segment in name.split(".") if segment]
    return "archive" in segments, "legacy" in segments


def collect_imports(root: Path, relative: Path) -> ImportHit | None:
    """Return ImportHit for the given file if it imports archive/legacy modules."""
    path = root / relative
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    try:
        tree = ast.parse(source, filename=str(relative))
    except SyntaxError:
        return None

    archive_refs: set[str] = set()
    legacy_refs: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                has_archive, has_legacy = _analyze_name(alias.name)
                if has_archive:
                    archive_refs.add(alias.name)
                if has_legacy:
                    legacy_refs.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            has_archive, has_legacy = _analyze_name(node.module)
            if has_archive and node.module:
                archive_refs.add(node.module)
            if has_legacy and node.module:
                legacy_refs.add(node.module)
            for alias in node.names:
                if alias.name == "*":
                    continue
                qualified = f"{node.module}.{alias.name}" if node.module else alias.name
                has_archive, has_legacy = _analyze_name(qualified)
                if has_archive:
                    archive_refs.add(qualified)
                if has_legacy:
                    legacy_refs.add(qualified)

    if not archive_refs and not legacy_refs:
        return None

    return ImportHit(
        path=relative,
        archive_imports=tuple(sorted(archive_refs)),
        legacy_imports=tuple(sorted(legacy_refs)),
    )


def generate_report(root: Path, subroots: Sequence[str] | None = None) -> dict[str, object]:
    """Generate a dictionary summarizing archive/legacy import usage."""
    paths = iter_python_files(root, subroots)
    hits = [hit.to_dict() for path in paths if (hit := collect_imports(root, path))]
    return {
        "total_files_scanned": len(paths),
        "hits": hits,
    }
