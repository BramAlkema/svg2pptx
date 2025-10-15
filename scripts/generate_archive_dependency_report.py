#!/usr/bin/env python3
"""
Generate a JSON report listing Python modules that import archive or legacy packages.

The script walks key project directories (core/api/cli/pipeline/presentationml/tests/adapters/scripts),
parses import statements via the stdlib AST, and emits a machine-readable inventory.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("reports/archive_dependencies.json"),
        help="Path to write the dependency report JSON.",
    )
    parser.add_argument(
        "--roots",
        nargs="+",
        help="Top-level directories to scan for Python files. Defaults to core/api/cli/pipeline/presentationml/tests/adapters/scripts.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print report to stdout instead of writing to a file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root))
    from datetime import datetime, timezone

    from tools.archive_scanner import DEFAULT_SCAN_ROOTS, generate_report

    roots = tuple(args.roots) if args.roots else DEFAULT_SCAN_ROOTS
    report = generate_report(repo_root, roots)
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report.setdefault("total_files_scanned", 0)
    if args.dry_run:
        print(json.dumps(report, indent=2))
        return

    output_path = (repo_root / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
