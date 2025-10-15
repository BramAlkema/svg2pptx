#!/usr/bin/env python3
"""
Fail-fast guard to prevent archive modules from being imported in active code paths.

Intended for use in CI / pre-commit pipelines. Exits with status 1 if any Python file
imports ``archive`` packages outside the deprecated archive directories.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root. Defaults to project root inferred from script location.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress success output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.root.resolve()
    sys.path.insert(0, str(repo_root))

    from tools.archive_scanner import DEFAULT_SCAN_ROOTS, generate_report

    report = generate_report(repo_root, DEFAULT_SCAN_ROOTS)
    offending = [
        hit
        for hit in report["hits"]
        if hit.get("archive_imports")
    ]

    if offending:
        print("Detected archive module imports outside archive directories:")
        for hit in offending:
            imports = ", ".join(hit["archive_imports"])
            print(f"  - {hit['path']}: {imports}")
        print("\nRun `python3 scripts/generate_archive_dependency_report.py` for full details.")
        return 1

    if not args.quiet:
        print("No archive imports detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
