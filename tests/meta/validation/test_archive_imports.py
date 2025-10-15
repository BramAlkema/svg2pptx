#!/usr/bin/env python3
"""Validation tests ensuring no runtime modules import the archive package."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.archive_scanner import DEFAULT_SCAN_ROOTS, generate_report


def test_no_archive_imports() -> None:
    """Fail if any active module imports archive.*."""
    report = generate_report(REPO_ROOT, DEFAULT_SCAN_ROOTS)
    offending = {
        hit["path"]: tuple(hit["archive_imports"])
        for hit in report["hits"]
        if hit.get("archive_imports")
    }
    assert not offending, (
        "Detected archive imports outside archive directories. "
        f"Review and remove references: {offending}"
    )
