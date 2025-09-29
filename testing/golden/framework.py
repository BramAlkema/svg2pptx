#!/usr/bin/env python3
"""
Golden Test Framework Core

Orchestrates A/B testing between legacy and clean architecture implementations.
"""

import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import tempfile
import shutil

from lxml import etree as ET


class TestResult(Enum):
    """Test outcome classification."""
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


class ComparisonType(Enum):
    """Types of comparison to perform."""
    PPTX_BINARY = "pptx_binary"      # Byte-level PPTX comparison
    XML_STRUCTURE = "xml_structure"  # DrawingML structure comparison
    VISUAL_RENDER = "visual_render"  # Visual appearance comparison
    PERFORMANCE = "performance"      # Speed and memory comparison
    METRICS = "metrics"             # Conversion metrics comparison


@dataclass
class ComparisonResult:
    """Result of comparing legacy vs clean implementations."""
    test_name: str
    comparison_type: ComparisonType
    result: TestResult
    legacy_output: Any
    clean_output: Any
    differences: List[str]
    metrics: Dict[str, Any]
    duration_sec: float
    error_message: Optional[str] = None

    @property
    def passed(self) -> bool:
        """Whether the comparison passed."""
        return self.result == TestResult.PASS

    @property
    def summary(self) -> str:
        """Human-readable summary."""
        if self.result == TestResult.PASS:
            return f"✅ {self.test_name} ({self.comparison_type.value}): PASS"
        elif self.result == TestResult.FAIL:
            diff_count = len(self.differences)
            return f"❌ {self.test_name} ({self.comparison_type.value}): FAIL ({diff_count} differences)"
        elif self.result == TestResult.SKIP:
            return f"⏭️  {self.test_name} ({self.comparison_type.value}): SKIP"
        else:
            return f"💥 {self.test_name} ({self.comparison_type.value}): ERROR - {self.error_message}"


@dataclass
class GoldenTestCase:
    """Single test case for golden testing."""
    name: str
    svg_content: str
    expected_elements: int
    description: str
    tags: List[str]
    complexity_score: int
    timeout_sec: float = 30.0

    @classmethod
    def from_file(cls, svg_path: Path) -> 'GoldenTestCase':
        """Create test case from SVG file."""
        with open(svg_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Estimate complexity
        element_count = content.count('<')
        complexity = min(100, element_count)

        # Extract tags from filename
        tags = []
        name_parts = svg_path.stem.split('_')
        if 'basic' in name_parts:
            tags.append('basic')
        if 'complex' in name_parts:
            tags.append('complex')
        if 'path' in name_parts:
            tags.append('paths')
        if 'text' in name_parts:
            tags.append('text')
        if 'gradient' in name_parts:
            tags.append('gradients')

        return cls(
            name=svg_path.stem,
            svg_content=content,
            expected_elements=element_count,
            description=f"Test case from {svg_path.name}",
            tags=tags,
            complexity_score=complexity
        )


class GoldenTestRunner:
    """
    Orchestrates golden testing between legacy and clean implementations.

    Runs identical SVG inputs through both systems and compares outputs
    using multiple comparison strategies.
    """

    def __init__(self,
                 legacy_converter: Callable[[str], Any],
                 clean_converter: Callable[[str], Any],
                 baseline_dir: Path = None):
        """
        Initialize golden test runner.

        Args:
            legacy_converter: Function that converts SVG string to output
            clean_converter: Function that converts SVG string to output
            baseline_dir: Directory for storing golden baselines
        """
        self.legacy_converter = legacy_converter
        self.clean_converter = clean_converter
        self.baseline_dir = baseline_dir or Path("testing/golden/baselines")
        self.baseline_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(__name__)
        self.temp_dir = None
        self.comparators: List[Any] = []

    def add_comparator(self, comparator):
        """Add a comparison strategy."""
        self.comparators.append(comparator)

    def run_test_case(self, test_case: GoldenTestCase) -> List[ComparisonResult]:
        """
        Run single test case through both implementations.

        Args:
            test_case: Test case to execute

        Returns:
            List of comparison results (one per comparator)
        """
        results = []

        try:
            # Setup temporary workspace
            with tempfile.TemporaryDirectory(prefix="golden_test_") as temp_dir:
                self.temp_dir = Path(temp_dir)

                # Run legacy implementation
                self.logger.debug(f"Running legacy converter for {test_case.name}")
                legacy_start = time.perf_counter()
                try:
                    legacy_output = self.legacy_converter(test_case.svg_content)
                    legacy_duration = time.perf_counter() - legacy_start
                    legacy_error = None
                except Exception as e:
                    legacy_output = None
                    legacy_duration = time.perf_counter() - legacy_start
                    legacy_error = str(e)
                    self.logger.error(f"Legacy converter failed: {e}")

                # Run clean implementation
                self.logger.debug(f"Running clean converter for {test_case.name}")
                clean_start = time.perf_counter()
                try:
                    clean_output = self.clean_converter(test_case.svg_content)
                    clean_duration = time.perf_counter() - clean_start
                    clean_error = None
                except Exception as e:
                    clean_output = None
                    clean_duration = time.perf_counter() - clean_start
                    clean_error = str(e)
                    self.logger.error(f"Clean converter failed: {e}")

                # Run comparisons
                for comparator in self.comparators:
                    try:
                        result = comparator.compare(
                            test_case=test_case,
                            legacy_output=legacy_output,
                            clean_output=clean_output,
                            legacy_duration=legacy_duration,
                            clean_duration=clean_duration,
                            temp_dir=self.temp_dir
                        )
                        results.append(result)

                    except Exception as e:
                        self.logger.error(f"Comparator {type(comparator).__name__} failed: {e}")
                        results.append(ComparisonResult(
                            test_name=test_case.name,
                            comparison_type=getattr(comparator, 'comparison_type', ComparisonType.METRICS),
                            result=TestResult.ERROR,
                            legacy_output=legacy_output,
                            clean_output=clean_output,
                            differences=[],
                            metrics={},
                            duration_sec=0.0,
                            error_message=str(e)
                        ))

        except Exception as e:
            self.logger.error(f"Test case {test_case.name} failed: {e}")
            # Return error result for each comparator
            for comparator in self.comparators:
                results.append(ComparisonResult(
                    test_name=test_case.name,
                    comparison_type=getattr(comparator, 'comparison_type', ComparisonType.METRICS),
                    result=TestResult.ERROR,
                    legacy_output=None,
                    clean_output=None,
                    differences=[],
                    metrics={},
                    duration_sec=0.0,
                    error_message=str(e)
                ))

        return results

    def run_test_suite(self, test_cases: List[GoldenTestCase],
                      max_failures: int = 10) -> Dict[str, Any]:
        """
        Run full test suite and generate comprehensive report.

        Args:
            test_cases: List of test cases to execute
            max_failures: Stop after this many failures

        Returns:
            Test suite results summary
        """
        all_results = []
        failure_count = 0
        start_time = time.perf_counter()

        self.logger.info(f"Starting golden test suite: {len(test_cases)} test cases")

        for i, test_case in enumerate(test_cases, 1):
            self.logger.info(f"Running test {i}/{len(test_cases)}: {test_case.name}")

            try:
                case_results = self.run_test_case(test_case)
                all_results.extend(case_results)

                # Check for failures
                case_failures = sum(1 for r in case_results if r.result == TestResult.FAIL)
                failure_count += case_failures

                if failure_count >= max_failures:
                    self.logger.warning(f"Stopping after {failure_count} failures")
                    break

            except Exception as e:
                self.logger.error(f"Test case {test_case.name} crashed: {e}")
                failure_count += 1

        total_duration = time.perf_counter() - start_time

        # Generate summary
        summary = self._generate_suite_summary(all_results, total_duration)

        self.logger.info(f"Golden test suite completed: {summary['pass_rate']:.1%} pass rate")
        return summary

    def _generate_suite_summary(self, results: List[ComparisonResult],
                               duration: float) -> Dict[str, Any]:
        """Generate comprehensive test suite summary."""
        total_tests = len(results)
        passed = sum(1 for r in results if r.result == TestResult.PASS)
        failed = sum(1 for r in results if r.result == TestResult.FAIL)
        skipped = sum(1 for r in results if r.result == TestResult.SKIP)
        errors = sum(1 for r in results if r.result == TestResult.ERROR)

        # Group by comparison type
        by_type = {}
        for result in results:
            comp_type = result.comparison_type.value
            if comp_type not in by_type:
                by_type[comp_type] = {'pass': 0, 'fail': 0, 'skip': 0, 'error': 0}
            by_type[comp_type][result.result.value] += 1

        # Performance metrics
        durations = [r.duration_sec for r in results if r.duration_sec > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Find worst failures
        failures = [r for r in results if r.result == TestResult.FAIL]
        worst_failures = sorted(failures, key=lambda x: len(x.differences), reverse=True)[:5]

        return {
            'total_tests': total_tests,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'errors': errors,
            'pass_rate': passed / max(1, total_tests),
            'duration_sec': duration,
            'avg_test_duration': avg_duration,
            'by_comparison_type': by_type,
            'worst_failures': [
                {
                    'name': f.test_name,
                    'type': f.comparison_type.value,
                    'difference_count': len(f.differences),
                    'error': f.error_message
                }
                for f in worst_failures
            ]
        }

    def create_baseline(self, test_case: GoldenTestCase,
                       implementation: str = "legacy") -> Path:
        """
        Create golden baseline from specified implementation.

        Args:
            test_case: Test case to create baseline for
            implementation: "legacy" or "clean"

        Returns:
            Path to created baseline file
        """
        if implementation == "legacy":
            output = self.legacy_converter(test_case.svg_content)
        elif implementation == "clean":
            output = self.clean_converter(test_case.svg_content)
        else:
            raise ValueError(f"Unknown implementation: {implementation}")

        baseline_path = self.baseline_dir / f"{test_case.name}_{implementation}.baseline"

        # Save baseline (format depends on output type)
        if isinstance(output, bytes):
            with open(baseline_path, 'wb') as f:
                f.write(output)
        else:
            with open(baseline_path, 'w', encoding='utf-8') as f:
                f.write(str(output))

        self.logger.info(f"Created baseline: {baseline_path}")
        return baseline_path

    def validate_against_baseline(self, test_case: GoldenTestCase,
                                implementation: str = "clean") -> ComparisonResult:
        """
        Validate implementation output against stored baseline.

        Args:
            test_case: Test case to validate
            implementation: Implementation to test

        Returns:
            Comparison result
        """
        baseline_path = self.baseline_dir / f"{test_case.name}_legacy.baseline"

        if not baseline_path.exists():
            return ComparisonResult(
                test_name=test_case.name,
                comparison_type=ComparisonType.PPTX_BINARY,
                result=TestResult.SKIP,
                legacy_output=None,
                clean_output=None,
                differences=["No baseline found"],
                metrics={},
                duration_sec=0.0,
                error_message="Baseline file missing"
            )

        # Load baseline
        try:
            if baseline_path.suffix == '.baseline':
                with open(baseline_path, 'rb') as f:
                    baseline_output = f.read()
        except Exception as e:
            return ComparisonResult(
                test_name=test_case.name,
                comparison_type=ComparisonType.PPTX_BINARY,
                result=TestResult.ERROR,
                legacy_output=None,
                clean_output=None,
                differences=[],
                metrics={},
                duration_sec=0.0,
                error_message=f"Baseline load failed: {e}"
            )

        # Generate current output
        start_time = time.perf_counter()
        try:
            if implementation == "legacy":
                current_output = self.legacy_converter(test_case.svg_content)
            else:
                current_output = self.clean_converter(test_case.svg_content)
            duration = time.perf_counter() - start_time
        except Exception as e:
            return ComparisonResult(
                test_name=test_case.name,
                comparison_type=ComparisonType.PPTX_BINARY,
                result=TestResult.ERROR,
                legacy_output=baseline_output,
                clean_output=None,
                differences=[],
                metrics={},
                duration_sec=time.perf_counter() - start_time,
                error_message=f"Conversion failed: {e}"
            )

        # Compare
        differences = []
        if baseline_output != current_output:
            if isinstance(baseline_output, bytes) and isinstance(current_output, bytes):
                # Binary comparison
                if len(baseline_output) != len(current_output):
                    differences.append(f"Size mismatch: {len(baseline_output)} vs {len(current_output)} bytes")
                else:
                    # Find first differing byte
                    for i, (a, b) in enumerate(zip(baseline_output, current_output)):
                        if a != b:
                            differences.append(f"Binary difference at byte {i}: {a:02x} vs {b:02x}")
                            break
            else:
                differences.append("Output format mismatch or text difference")

        result = TestResult.PASS if not differences else TestResult.FAIL

        return ComparisonResult(
            test_name=test_case.name,
            comparison_type=ComparisonType.PPTX_BINARY,
            result=result,
            legacy_output=baseline_output,
            clean_output=current_output,
            differences=differences,
            metrics={
                'baseline_size': len(baseline_output) if isinstance(baseline_output, bytes) else 0,
                'current_size': len(current_output) if isinstance(current_output, bytes) else 0
            },
            duration_sec=duration
        )