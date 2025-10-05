#!/usr/bin/env python3
"""
Analyze unmigrated test files to categorize them for cleanup.

Categories:
1. API tests - may need Google Drive setup
2. Integration tests - complex dependencies
3. Performance/Quality tests - may be obsolete
4. Unit tests - likely need import fixes
"""

import subprocess
from collections import defaultdict
from pathlib import Path

def get_unmigrated_tests():
    """Get list of tests that fail to collect."""
    result = subprocess.run(
        ["pytest", "tests/", "--collect-only", "-q"],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "."}
    )

    errors = []
    for line in result.stderr.split('\n'):
        if 'ERROR collecting' in line:
            # Extract path from "ERROR collecting tests/path/file.py"
            parts = line.split('ERROR collecting ')
            if len(parts) > 1:
                path = parts[1].split()[0]
                errors.append(path)

    return errors

def categorize_tests(test_files):
    """Categorize tests by type and purpose."""
    categories = defaultdict(list)

    for test_file in test_files:
        if '/api/' in test_file or test_file.endswith('_api_e2e.py'):
            categories['API Tests'].append(test_file)
        elif '/integration/' in test_file:
            categories['Integration Tests'].append(test_file)
        elif '/e2e/' in test_file:
            categories['E2E Tests'].append(test_file)
        elif '/performance/' in test_file or '/benchmarks/' in test_file:
            categories['Performance Tests'].append(test_file)
        elif '/quality/' in test_file or '/validation/' in test_file:
            categories['Quality/Validation Tests'].append(test_file)
        elif '/security/' in test_file or '/robustness/' in test_file:
            categories['Security/Robustness Tests'].append(test_file)
        elif '/meta/' in test_file:
            categories['Meta Tests'].append(test_file)
        elif '/architecture/' in test_file:
            categories['Architecture Tests'].append(test_file)
        elif '/unit/converters/' in test_file:
            categories['Unit Converter Tests'].append(test_file)
        else:
            categories['Other'].append(test_file)

    return categories

def analyze_import_errors(test_file):
    """Check what imports are failing for a test file."""
    result = subprocess.run(
        ["python3", "-c", f"import sys; sys.path.insert(0, '.'); exec(open('{test_file}').read())"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        error = result.stderr
        if 'ModuleNotFoundError' in error or 'ImportError' in error:
            # Extract module name
            for line in error.split('\n'):
                if 'from' in line or 'import' in line:
                    return line.strip()
    return None

def main():
    print("🔍 Analyzing unmigrated tests...\n")

    tests = get_unmigrated_tests()
    print(f"Found {len(tests)} tests with collection errors\n")

    categories = categorize_tests(tests)

    print("=" * 60)
    print("TEST CATEGORIZATION")
    print("=" * 60)

    for category, files in sorted(categories.items()):
        print(f"\n### {category} ({len(files)} files)")
        print("-" * 40)
        for f in sorted(files)[:10]:  # Show first 10
            print(f"  - {f}")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for category, files in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"{category:30s}: {len(files):3d} files")

    print(f"\n{'TOTAL':30s}: {len(tests):3d} files")

    # Sample import analysis for first few files
    print("\n" + "=" * 60)
    print("SAMPLE IMPORT ERRORS (first 5)")
    print("=" * 60)
    for test_file in list(tests)[:5]:
        error = analyze_import_errors(test_file)
        if error:
            print(f"\n{test_file}:")
            print(f"  {error}")

if __name__ == "__main__":
    main()
