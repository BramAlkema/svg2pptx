#!/usr/bin/env python3
"""
Visual Comparison Test Runner
============================

Standalone script to run visual comparison tests for SVG2PPTX.
Creates before/after screenshots and comparison pages.

Usage:
    python run_visual_tests.py

Output:
    tests/visual/results/visual_test_report.html - Main report with all comparisons
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Import our visual testing system
from tests.visual.test_visual_comparison import VisualComparisonTester, create_sample_test_cases

async def main():
    """Run visual comparison tests and generate report."""
    print("🎨 SVG2PPTX Visual Comparison Testing")
    print("=" * 50)

    # Create tester
    tester = VisualComparisonTester("tests/visual/results")
    test_cases = create_sample_test_cases()

    print(f"📋 Running {len(test_cases)} visual comparison tests...")
    print()

    # Run each test
    for i, test_case in enumerate(test_cases, 1):
        print(f"[{i}/{len(test_cases)}] Testing: {test_case.name}")
        print(f"   Description: {test_case.description}")

        result = await tester.run_visual_test(test_case)
        tester.test_results.append(result)

        if result['status'] == 'completed':
            print(f"   ✅ Completed successfully")
            print(f"   📁 Comparison: {result['files']['comparison_page']}")
        else:
            print(f"   ❌ Failed: {'; '.join(result.get('errors', ['Unknown error']))}")

        print()

    # Generate comprehensive report
    print("📊 Generating comprehensive report...")
    report_path = await tester.generate_test_report()

    # Print summary
    total = len(tester.test_results)
    completed = len([r for r in tester.test_results if r['status'] == 'completed'])
    failed = len([r for r in tester.test_results if r['status'] == 'failed'])

    print()
    print("📈 VISUAL TESTING SUMMARY")
    print("=" * 50)
    print(f"   📊 Total tests: {total}")
    print(f"   ✅ Completed: {completed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📈 Success rate: {completed/max(1,total)*100:.1f}%")
    print()
    print(f"📄 Main Report: {report_path}")
    print(f"🌐 View report: file://{report_path.absolute()}")
    print()

    # List individual comparison pages
    print("🔍 Individual Comparisons:")
    for result in tester.test_results:
        if result['status'] == 'completed' and 'comparison_page' in result['files']:
            test_name = result['test_case']['name']
            comparison_path = Path(result['files']['comparison_page'])
            print(f"   • {test_name}: file://{comparison_path.absolute()}")

    print()
    print("🎯 Use these comparison pages to:")
    print("   • Validate visual accuracy of conversions")
    print("   • Identify areas needing improvement")
    print("   • Document before/after changes")
    print("   • Create visual regression test baselines")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Testing failed: {e}")
        sys.exit(1)