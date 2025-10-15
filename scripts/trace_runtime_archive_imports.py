#!/usr/bin/env python3
"""
Trace runtime imports for archive/legacy modules when importing common entry points.

The script imports a configurable list of modules and records any loaded module names
containing the segments ``archive`` or ``legacy``. The resulting JSON report helps cross-check
static dependency findings.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_TARGET_MODULES: tuple[str, ...] = (
    "api.services.conversion_service",
    "cli.main",
    "core.services.conversion_services",
    "svg2pptx",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("reports/archive_runtime_imports.json"),
        help="Where to write the runtime import report.",
    )
    parser.add_argument(
        "--module",
        dest="modules",
        action="append",
        help="Additional module import targets. Repeatable.",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        help="Override default modules entirely and import only the provided module list.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print report to stdout instead of writing to disk.",
    )
    return parser.parse_args()


def has_segment(name: str, segment: str) -> bool:
    return segment in [part for part in name.split(".") if part]


def collect_loaded_modules(modules: Iterable[str]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for target in modules:
        snapshot_before = set(sys.modules)
        status: str
        error: str | None = None
        try:
            importlib.import_module(target)
            status = "imported"
        except Exception as exc:  # pragma: no cover - defensive
            status = "error"
            error = f"{type(exc).__name__}: {exc}"
        snapshot_after = set(sys.modules)
        newly_loaded = snapshot_after - snapshot_before

        archive_modules = sorted({name for name in newly_loaded if has_segment(name, "archive")})
        legacy_modules = sorted({name for name in newly_loaded if has_segment(name, "legacy")})

        results.append(
            {
                "target": target,
                "status": status,
                "error": error,
                "archive_modules": archive_modules,
                "legacy_modules": legacy_modules,
            }
        )
    return results


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root))
    module_targets = tuple(DEFAULT_TARGET_MODULES)
    if args.only:
        module_targets = tuple(args.only)
    elif args.modules:
        module_targets = module_targets + tuple(args.modules)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "targets": list(module_targets),
        "results": collect_loaded_modules(module_targets),
    }

    if args.dry_run:
        print(json.dumps(report, indent=2))
        return

    output_path = (repo_root / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
