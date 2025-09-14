#!/usr/bin/env python3
"""
Unified Test Runner for SVG2PPTX

🚨 MANDATORY: This script MUST be executed through the source venv only.

Usage:
    ./venv/bin/python tests/run_tests.py [options]

VENV REQUIREMENT:
    source venv/bin/activate
    ./venv/bin/python tests/run_tests.py [options]

Examples:
    ./venv/bin/python tests/run_tests.py --unit                 # Run only unit tests
    ./venv/bin/python tests/run_tests.py --integration         # Run only integration tests
    ./venv/bin/python tests/run_tests.py --e2e                 # Run only end-to-end tests
    ./venv/bin/python tests/run_tests.py --converters          # Run only converter tests
    ./venv/bin/python tests/run_tests.py --fast                # Run fast tests only
    ./venv/bin/python tests/run_tests.py --coverage            # Run with coverage reporting
    ./venv/bin/python tests/run_tests.py --parallel            # Run tests in parallel
    ./venv/bin/python tests/run_tests.py --all                 # Run all tests
"""

import argparse
import sys
import subprocess
from pathlib import Path
import os
import time


class TestRunner:
    """Unified test runner for SVG2PPTX testing system."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.tests_dir = self.project_root / "tests"
        self.venv_python = self.project_root / "venv" / "bin" / "python"

        # Check venv requirement
        self._check_venv_availability()

    def _check_venv_availability(self):
        """Check if venv is available and warn if not using it."""
        if not self.venv_python.exists():
            print("🚨 WARNING: venv/bin/python not found!")
            print("Please ensure virtual environment is set up:")
            print("  python -m venv venv")
            print("  source venv/bin/activate")
            print("  pip install -r requirements.txt")
            sys.exit(1)

        current_python = Path(sys.executable)
        if not str(current_python).endswith(str(self.venv_python)):
            print("🚨 ERROR: Must run through venv!")
            print(f"Current Python: {current_python}")
            print(f"Expected: {self.venv_python}")
            print("\nMandatory usage:")
            print("  source venv/bin/activate")
            print(f"  ./venv/bin/python tests/run_tests.py")
            print("\nVenv enforcement is now MANDATORY for all test execution.")
            sys.exit(1)

    def run_command(self, cmd, description="Running tests"):
        """Execute a command and handle output."""
        print(f"\n{'='*60}")
        print(f"{description}")
        print(f"{'='*60}")
        print(f"Command: {' '.join(cmd)}")
        print()

        start_time = time.time()
        result = subprocess.run(cmd, cwd=self.project_root)
        end_time = time.time()

        duration = end_time - start_time
        print(f"\nCompleted in {duration:.2f} seconds")

        return result.returncode == 0

    def run_unit_tests(self, extra_args=None):
        """Run unit tests."""
        cmd = [
            str(self.venv_python), "-m", "pytest",
            "tests/unit/",
            "-m", "unit or not (integration or e2e)",
            "-v"
        ]
        if extra_args:
            cmd.extend(extra_args)

        return self.run_command(cmd, "Running Unit Tests")

    def run_integration_tests(self, extra_args=None):
        """Run integration tests."""
        cmd = [
            str(self.venv_python), "-m", "pytest",
            "tests/integration/",
            "-m", "integration",
            "-v"
        ]
        if extra_args:
            cmd.extend(extra_args)

        return self.run_command(cmd, "Running Integration Tests")

    def run_e2e_tests(self, extra_args=None):
        """Run end-to-end tests."""
        cmd = [
            str(self.venv_python), "-m", "pytest",
            "tests/e2e/",
            "-m", "e2e",
            "-v"
        ]
        if extra_args:
            cmd.extend(extra_args)

        return self.run_command(cmd, "Running End-to-End Tests")

    def run_converter_tests(self, extra_args=None):
        """Run converter tests specifically."""
        cmd = [
            str(self.venv_python), "-m", "pytest",
            "tests/unit/converters/",
            "-m", "converter or shapes or text or paths or transforms",
            "-v"
        ]
        if extra_args:
            cmd.extend(extra_args)

        return self.run_command(cmd, "Running Converter Tests")

    def run_validation_tests(self, extra_args=None):
        """Run validation tests."""
        cmd = [
            str(self.venv_python), "-m", "pytest",
            "tests/unit/validation/",
            "tests/quality/",
            "-m", "validation",
            "-v"
        ]
        if extra_args:
            cmd.extend(extra_args)

        return self.run_command(cmd, "Running Validation Tests")

    def run_performance_tests(self, extra_args=None):
        """Run performance tests."""
        cmd = [
            str(self.venv_python), "-m", "pytest",
            "tests/performance/",
            "-m", "performance",
            "-v"
        ]
        if extra_args:
            cmd.extend(extra_args)

        return self.run_command(cmd, "Running Performance Tests")

    def run_fast_tests(self, extra_args=None):
        """Run fast tests only (exclude slow tests)."""
        cmd = [
            str(self.venv_python), "-m", "pytest",
            "tests/",
            "-m", "not slow",
            "-v"
        ]
        if extra_args:
            cmd.extend(extra_args)

        return self.run_command(cmd, "Running Fast Tests")

    def run_with_coverage(self, test_path="tests/", extra_args=None):
        """Run tests with coverage reporting."""
        cmd = [
            str(self.venv_python), "-m", "pytest",
            test_path,
            "--cov=src",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-report=xml",
            "--cov-branch",
            "--cov-fail-under=20",  # Adjusted for current coverage level
            "-v"
        ]
        if extra_args:
            cmd.extend(extra_args)

        success = self.run_command(cmd, f"Running Tests with Coverage: {test_path}")

        if success:
            print(f"\nCoverage report generated:")
            print(f"  HTML: {self.project_root}/htmlcov/index.html")
            print(f"  XML:  {self.project_root}/coverage.xml")

        return success

    def run_parallel_tests(self, test_path="tests/", extra_args=None):
        """Run tests in parallel."""
        cmd = [
            str(self.venv_python), "-m", "pytest",
            test_path,
            "-n", "auto",
            "-v"
        ]
        if extra_args:
            cmd.extend(extra_args)

        return self.run_command(cmd, f"Running Tests in Parallel: {test_path}")

    def run_all_tests(self, extra_args=None):
        """Run all tests in logical order."""
        print("\n" + "="*80)
        print("RUNNING COMPLETE TEST SUITE")
        print("="*80)

        success = True

        # Run tests in order of increasing scope and complexity
        test_suites = [
            ("Unit Tests", self.run_unit_tests),
            ("Integration Tests", self.run_integration_tests),
            ("Validation Tests", self.run_validation_tests),
            ("End-to-End Tests", self.run_e2e_tests),
        ]

        for suite_name, test_func in test_suites:
            print(f"\n{'*'*40} {suite_name} {'*'*40}")
            if not test_func(extra_args):
                print(f"❌ {suite_name} FAILED")
                success = False
                break
            else:
                print(f"✅ {suite_name} PASSED")

        return success

    def run_smoke_tests(self, extra_args=None):
        """Run smoke tests for basic functionality."""
        cmd = [
            str(self.venv_python), "-m", "pytest",
            "tests/",
            "-m", "smoke",
            "-v",
            "--maxfail=1"
        ]
        if extra_args:
            cmd.extend(extra_args)

        return self.run_command(cmd, "Running Smoke Tests")

    def run_regression_tests(self, extra_args=None):
        """Run regression tests."""
        cmd = [
            str(self.venv_python), "-m", "pytest",
            "tests/",
            "-m", "regression",
            "-v"
        ]
        if extra_args:
            cmd.extend(extra_args)

        return self.run_command(cmd, "Running Regression Tests")

    def check_test_structure(self):
        """Validate the test structure."""
        print("\n" + "="*60)
        print("CHECKING TEST STRUCTURE")
        print("="*60)

        # Count tests in each category
        categories = {
            "Unit Tests": self.tests_dir / "unit",
            "Integration Tests": self.tests_dir / "integration",
            "E2E Tests": self.tests_dir / "e2e",
            "Performance Tests": self.tests_dir / "performance",
            "Quality Tests": self.tests_dir / "quality",
        }

        total_tests = 0
        for category, path in categories.items():
            if path.exists():
                test_files = list(path.rglob("test_*.py"))
                count = len(test_files)
                total_tests += count
                print(f"{category:20}: {count:3d} test files")
            else:
                print(f"{category:20}: Directory not found")

        print("-" * 60)
        print(f"{'Total':20}: {total_tests:3d} test files")

        # Check for templates
        templates_dir = self.tests_dir / "templates"
        if templates_dir.exists():
            template_files = list(templates_dir.glob("*.py"))
            print(f"{'Templates':20}: {len(template_files):3d} template files")

        # Check configuration files
        config_files = [
            "conftest.py",
            "pytest_unified.ini",
            "__init__.py"
        ]

        for config_file in config_files:
            path = self.tests_dir / config_file
            status = "✅" if path.exists() else "❌"
            print(f"{config_file:20}: {status}")

        return total_tests > 0


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Unified test runner for SVG2PPTX",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Test selection options
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument("--unit", action="store_true", help="Run unit tests")
    test_group.add_argument("--integration", action="store_true", help="Run integration tests")
    test_group.add_argument("--e2e", action="store_true", help="Run end-to-end tests")
    test_group.add_argument("--converters", action="store_true", help="Run converter tests")
    test_group.add_argument("--validation", action="store_true", help="Run validation tests")
    test_group.add_argument("--performance", action="store_true", help="Run performance tests")
    test_group.add_argument("--fast", action="store_true", help="Run fast tests only")
    test_group.add_argument("--smoke", action="store_true", help="Run smoke tests")
    test_group.add_argument("--regression", action="store_true", help="Run regression tests")
    test_group.add_argument("--all", action="store_true", help="Run all tests")

    # Execution options
    parser.add_argument("--coverage", action="store_true", help="Run with coverage reporting")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--check-structure", action="store_true", help="Check test structure")

    # Pass-through options
    parser.add_argument("extra_args", nargs="*", help="Extra arguments to pass to pytest")

    args = parser.parse_args()

    runner = TestRunner()

    # Check test structure if requested
    if args.check_structure:
        runner.check_test_structure()
        return

    # Determine execution modifiers
    extra_args = args.extra_args or []

    if args.parallel:
        extra_args.extend(["-n", "auto"])

    if args.coverage:
        extra_args.extend([
            "--cov=src",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-report=xml",
            "--cov-branch"
        ])

    # Run requested tests
    success = True

    if args.unit:
        success = runner.run_unit_tests(extra_args)
    elif args.integration:
        success = runner.run_integration_tests(extra_args)
    elif args.e2e:
        success = runner.run_e2e_tests(extra_args)
    elif args.converters:
        success = runner.run_converter_tests(extra_args)
    elif args.validation:
        success = runner.run_validation_tests(extra_args)
    elif args.performance:
        success = runner.run_performance_tests(extra_args)
    elif args.fast:
        success = runner.run_fast_tests(extra_args)
    elif args.smoke:
        success = runner.run_smoke_tests(extra_args)
    elif args.regression:
        success = runner.run_regression_tests(extra_args)
    elif args.all:
        success = runner.run_all_tests(extra_args)
    else:
        # Default: run structure check and fast tests
        runner.check_test_structure()
        success = runner.run_fast_tests(extra_args)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()