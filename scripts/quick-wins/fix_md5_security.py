#!/usr/bin/env python3
"""
Fix MD5 security flags by adding usedforsecurity=False parameter.
"""
import re
import sys
from pathlib import Path


def fix_md5_in_file(filepath: Path) -> int:
    """Fix MD5 calls in a single file. Returns number of changes."""
    content = filepath.read_text()
    original = content

    # Pattern 1: hashlib.md5(data) → hashlib.md5(data, usedforsecurity=False)
    # Only match if there's no usedforsecurity already
    pattern1 = r'hashlib\.md5\(([^)]+)\)(?!\s*,\s*usedforsecurity)'

    def replace_md5(match):
        args = match.group(1).strip()
        # Check if args already has usedforsecurity
        if 'usedforsecurity' in args:
            return match.group(0)
        return f'hashlib.md5({args}, usedforsecurity=False)'

    content = re.sub(pattern1, replace_md5, content)

    if content != original:
        filepath.write_text(content)
        return content.count('usedforsecurity=False') - original.count('usedforsecurity=False')
    return 0


def main():
    """Main entry point."""
    core_dir = Path('core')

    print("=== Fixing MD5 Security Flags ===\n")

    # Find all Python files with hashlib.md5
    files_to_fix = []
    for py_file in core_dir.rglob('*.py'):
        if 'hashlib.md5' in py_file.read_text():
            files_to_fix.append(py_file)

    if not files_to_fix:
        print("✅ No MD5 calls found")
        return 0

    print(f"Found {len(files_to_fix)} files with MD5 calls:\n")
    for f in files_to_fix:
        print(f"  - {f}")
    print()

    # Fix each file
    total_changes = 0
    for py_file in files_to_fix:
        changes = fix_md5_in_file(py_file)
        if changes > 0:
            print(f"✅ {py_file}: {changes} changes")
            total_changes += changes

    print(f"\n✅ Total: {total_changes} MD5 calls fixed")
    return 0


if __name__ == '__main__':
    sys.exit(main())
