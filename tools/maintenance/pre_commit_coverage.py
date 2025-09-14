#!/usr/bin/env python3
"""
Pre-commit hook for coverage validation.

This script runs coverage analysis and validates that the coverage
threshold is met before allowing commits.
"""

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def run_coverage_check():
    """Run coverage check and validate threshold."""
    print("🔍 Running coverage check...")
    
    try:
        # Run tests with coverage
        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            '--cov=src',
            '--cov-report=xml:coverage.xml',
            '--cov-report=term-missing',
            '--cov-fail-under=90',
            '-x',  # Stop on first failure
            '--tb=short',
            '-q'  # Quiet mode
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print("❌ Tests failed or coverage below threshold!")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
            return False
        
        # Parse coverage results
        coverage_file = Path("coverage.xml")
        if not coverage_file.exists():
            print("❌ Coverage file not found!")
            return False
        
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        
        line_rate = float(root.get('line-rate', 0)) * 100
        branch_rate = float(root.get('branch-rate', 0)) * 100
        
        print(f"📊 Line Coverage: {line_rate:.2f}%")
        print(f"🌿 Branch Coverage: {branch_rate:.2f}%")
        
        if line_rate < 90.0:
            print(f"❌ Line coverage {line_rate:.2f}% is below 90% threshold!")
            return False
        
        if branch_rate < 85.0:
            print(f"⚠️  Branch coverage {branch_rate:.2f}% is below 85% threshold")
            print("   (Warning only - not blocking commit)")
        
        print("✅ Coverage threshold met!")
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Coverage check timed out after 5 minutes!")
        return False
    except Exception as e:
        print(f"❌ Coverage check failed: {e}")
        return False
    finally:
        # Cleanup coverage files
        for file_path in ["coverage.xml", ".coverage"]:
            try:
                Path(file_path).unlink(missing_ok=True)
            except:
                pass


def check_modified_files():
    """Check if any Python files were modified that require coverage check."""
    try:
        result = subprocess.run([
            'git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            return True  # Run coverage check if git command fails
        
        modified_files = result.stdout.strip().split('\n')
        python_files = [f for f in modified_files if f.endswith('.py') and f.startswith('src/')]
        
        if python_files:
            print(f"📝 Modified Python files requiring coverage check: {len(python_files)}")
            for file in python_files[:5]:  # Show first 5
                print(f"   - {file}")
            if len(python_files) > 5:
                print(f"   ... and {len(python_files) - 5} more")
            return True
        else:
            print("ℹ️  No source Python files modified - skipping coverage check")
            return False
            
    except Exception as e:
        print(f"⚠️  Could not check modified files: {e}")
        return True  # Run coverage check if unsure


def main():
    """Main entry point for pre-commit coverage check."""
    print("🚀 Pre-commit coverage validation")
    
    # Check if we need to run coverage check
    if not check_modified_files():
        print("✅ No coverage check needed")
        return 0
    
    # Run coverage check
    if run_coverage_check():
        print("✅ Pre-commit coverage check passed!")
        return 0
    else:
        print("❌ Pre-commit coverage check failed!")
        print("\n💡 Tips to fix coverage issues:")
        print("   1. Add tests for new/modified code")
        print("   2. Remove unused code")
        print("   3. Add # pragma: no cover for defensive code")
        print("   4. Run 'python tools/coverage_utils.py' for detailed analysis")
        return 1


if __name__ == '__main__':
    sys.exit(main())