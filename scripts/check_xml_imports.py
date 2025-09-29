#!/usr/bin/env python3
"""
Pre-commit script to check for forbidden xml.etree.ElementTree imports.

This script ensures that only lxml.etree is used throughout the codebase,
preventing the reintroduction of ElementTree imports that cause compatibility issues.
"""

import os
import re
import sys
from pathlib import Path


def check_file_for_elementtree(filepath: Path) -> list[str]:
    """Check a single file for forbidden ElementTree imports."""
    forbidden_patterns = [
        r'import\s+xml\.etree\.ElementTree',
        r'from\s+xml\.etree\.ElementTree',
        r'xml\.etree\.ElementTree\s+as\s+ET',
    ]

    violations = []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                for pattern in forbidden_patterns:
                    if re.search(pattern, line):
                        violations.append(f"{filepath}:{line_num}: {line.strip()}")
    except (UnicodeDecodeError, FileNotFoundError):
        # Skip binary files or files that can't be read
        pass

    return violations


def main():
    """Main function to check all Python files in src/ directory."""
    src_dir = Path(__file__).parent.parent / "src"

    if not src_dir.exists():
        print("❌ src/ directory not found")
        return 1

    all_violations = []

    # Check all .py files in src/
    for py_file in src_dir.rglob("*.py"):
        violations = check_file_for_elementtree(py_file)
        all_violations.extend(violations)

    if all_violations:
        print("❌ FORBIDDEN: Found xml.etree.ElementTree imports:")
        print("=" * 60)
        for violation in all_violations:
            print(violation)
        print("=" * 60)
        print("🔧 Fix: Replace with 'from lxml import etree as ET'")
        return 1
    else:
        print("✅ No forbidden ElementTree imports found")
        return 0


if __name__ == "__main__":
    sys.exit(main())