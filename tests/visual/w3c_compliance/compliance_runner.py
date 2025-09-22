#!/usr/bin/env python3
"""
W3C Compliance Test Runner

Orchestrates comprehensive W3C SVG compliance testing using LibreOffice automation.
Manages the complete pipeline from test case selection to compliance reporting.
"""

import os
import asyncio
import logging
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Import our modules
from .w3c_test_manager import W3CTestSuiteManager, W3CTestCase
from .libreoffice_controller import LibreOfficePlaywrightController, LibreOfficeConfig
from .svg_pptx_comparator import SVGPPTXComparator, ComparisonResult, ComplianceLevel

# SVG2PPTX import
try:
    from src.svg2pptx import convert_svg_to_pptx
    SVG2PPTX_AVAILABLE = True
except ImportError:
    SVG2PPTX_AVAILABLE = False

logger = logging.getLogger(__name__)


class TestSuite(Enum):
    """Available test suites."""
    BASIC = "basic"                    # Basic compliance tests
    COMPREHENSIVE = "comprehensive"    # Full test suite
    FEATURES = "features"             # Feature-specific tests
    CUSTOM = "custom"                 # Custom test selection


@dataclass
class ComplianceConfig:
    """Configuration for compliance testing."""
    # Test selection
    test_suite: TestSuite = TestSuite.BASIC
    w3c_version: str = "1.1"
    custom_test_names: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    max_tests: Optional[int] = None

    # LibreOffice settings
    libreoffice_headless: bool = True
    libreoffice_port: int = 8100
    screenshot_delay: float = 2.0

    # Comparison settings
    comparison_tolerance: float = 0.85
    enable_detailed_analysis: bool = True
    reference_resolution: Tuple[int, int] = (1920, 1080)

    # Output settings
    output_dir: Path = field(default_factory=lambda: Path("tests/visual/w3c_compliance/results"))
    save_intermediate_files: bool = True
    generate_html_report: bool = True

    # Performance settings
    max_concurrent_tests: int = 1  # LibreOffice doesn't handle concurrency well
    test_timeout: int = 300  # 5 minutes per test


@dataclass
class ComplianceReport:
    """Comprehensive compliance test report."""
    session_id: str
    config: ComplianceConfig
    generated_at: datetime

    # Test execution summary
    total_tests: int = 0
    successful_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0

    # Compliance summary
    compliance_distribution: Dict[str, int] = field(default_factory=dict)
    overall_compliance_score: float = 0.0
    category_scores: Dict[str, float] = field(default_factory=dict)
    feature_scores: Dict[str, float] = field(default_factory=dict)

    # Test results
    results: List[ComparisonResult] = field(default_factory=list)

    # Performance metrics
    total_execution_time: float = 0.0
    average_test_time: float = 0.0

    # Issues and recommendations
    common_issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    metadata: Dict[str, any] = field(default_factory=dict)


class W3CComplianceTestRunner:
    """Orchestrates W3C SVG compliance testing."""

    def __init__(self, config: Optional[ComplianceConfig] = None):
        """
        Initialize compliance test runner.

        Args:
            config: Compliance testing configuration
        """
        self.config = config or ComplianceConfig()

        # Initialize components
        self.test_manager = W3CTestSuiteManager()
        self.libreoffice_controller = None
        self.comparator = SVGPPTXComparator(
            tolerance=self.config.comparison_tolerance,
            enable_detailed_analysis=self.config.enable_detailed_analysis,
            reference_resolution=self.config.reference_resolution
        )

        # State tracking
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.is_initialized = False

        logger.info(f"W3CComplianceTestRunner initialized - Session: {self.session_id}")

    async def initialize(self) -> bool:
        """
        Initialize test runner and dependencies.

        Returns:
            True if successful
        """
        try:
            if not SVG2PPTX_AVAILABLE:
                logger.error("SVG2PPTX module not available")
                return False

            # Ensure output directory exists
            self.config.output_dir.mkdir(parents=True, exist_ok=True)

            # Download and load W3C test suite
            logger.info(f"Loading W3C test suite version {self.config.w3c_version}")
            if not self.test_manager.download_test_suite(self.config.w3c_version):
                logger.error("Failed to download W3C test suite")
                return False

            if not self.test_manager.load_test_cases(self.config.w3c_version):
                logger.error("Failed to load test cases")
                return False

            # Initialize LibreOffice controller
            libreoffice_config = LibreOfficeConfig(
                headless=self.config.libreoffice_headless,
                port=self.config.libreoffice_port,
                screenshot_delay=self.config.screenshot_delay
            )

            self.libreoffice_controller = LibreOfficePlaywrightController(libreoffice_config)

            # Start LibreOffice and browser
            if not await self.libreoffice_controller.start_libreoffice():
                logger.error("Failed to start LibreOffice")
                return False

            if not await self.libreoffice_controller.start_browser():
                logger.error("Failed to start browser")
                return False

            self.is_initialized = True
            logger.info("W3CComplianceTestRunner initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    async def run_compliance_tests(self, progress_callback: Optional[callable] = None) -> ComplianceReport:
        """
        Run comprehensive compliance tests.

        Args:
            progress_callback: Optional progress callback

        Returns:
            ComplianceReport with results
        """
        start_time = time.time()

        if not self.is_initialized:
            raise RuntimeError("Test runner not initialized. Call initialize() first.")

        # Initialize report
        report = ComplianceReport(
            session_id=self.session_id,
            config=self.config,
            generated_at=datetime.now()
        )

        try:
            # Select test cases
            test_cases = self._select_test_cases()
            report.total_tests = len(test_cases)

            if not test_cases:
                logger.warning("No test cases selected")
                return report

            logger.info(f"Running compliance tests on {len(test_cases)} test cases")

            # Convert SVG files to PPTX
            pptx_files = await self._convert_svgs_to_pptx(test_cases, progress_callback)

            # Run comparisons
            results = await self._run_comparisons(test_cases, pptx_files, progress_callback)
            report.results = results

            # Analyze results
            self._analyze_results(report)

            # Generate detailed report
            if self.config.generate_html_report:
                await self._generate_html_report(report)

            report.total_execution_time = time.time() - start_time
            report.average_test_time = report.total_execution_time / max(len(test_cases), 1)

            logger.info(f"Compliance testing completed in {report.total_execution_time:.2f}s")
            logger.info(f"Overall compliance score: {report.overall_compliance_score:.3f}")

            return report

        except Exception as e:
            logger.error(f"Compliance testing failed: {e}")
            report.total_execution_time = time.time() - start_time
            return report

    async def run_single_test(self, test_case_name: str) -> ComparisonResult:
        """
        Run compliance test for a single test case.

        Args:
            test_case_name: Name of test case to run

        Returns:
            ComparisonResult
        """
        if not self.is_initialized:
            raise RuntimeError("Test runner not initialized")

        test_case = self.test_manager.get_test_case(test_case_name)
        if not test_case:
            raise ValueError(f"Test case not found: {test_case_name}")

        logger.info(f"Running single compliance test: {test_case_name}")

        # Convert SVG to PPTX
        pptx_path = await self._convert_single_svg(test_case)

        # Run comparison
        output_dir = self.config.output_dir / test_case_name
        result = await self.comparator.compare_test_case(
            test_case, pptx_path, self.libreoffice_controller, output_dir
        )

        logger.info(f"Single test completed: {result.overall_compliance.value}")
        return result

    async def cleanup(self):
        """Cleanup test runner resources."""
        try:
            if self.libreoffice_controller:
                await self.libreoffice_controller.cleanup()

            logger.info("Test runner cleanup completed")

        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    def _select_test_cases(self) -> List[W3CTestCase]:
        """Select test cases based on configuration."""
        if self.config.test_suite == TestSuite.BASIC:
            test_cases = self.test_manager.get_basic_compliance_suite()

        elif self.config.test_suite == TestSuite.COMPREHENSIVE:
            test_cases = self.test_manager.get_comprehensive_suite()

        elif self.config.test_suite == TestSuite.FEATURES:
            # Select tests for specific features
            test_cases = []
            for category in self.config.categories:
                category_tests = self.test_manager.get_test_cases(category=category)
                test_cases.extend(category_tests)

        elif self.config.test_suite == TestSuite.CUSTOM:
            # Select specific test cases
            test_cases = []
            for test_name in self.config.custom_test_names:
                test_case = self.test_manager.get_test_case(test_name)
                if test_case:
                    test_cases.append(test_case)

        else:
            test_cases = self.test_manager.get_basic_compliance_suite()

        # Apply limit if specified
        if self.config.max_tests:
            test_cases = test_cases[:self.config.max_tests]

        logger.info(f"Selected {len(test_cases)} test cases for compliance testing")
        return test_cases

    async def _convert_svgs_to_pptx(self, test_cases: List[W3CTestCase],
                                  progress_callback: Optional[callable] = None) -> Dict[str, Path]:
        """Convert SVG test cases to PPTX files."""
        pptx_files = {}
        total_cases = len(test_cases)

        logger.info(f"Converting {total_cases} SVG files to PPTX")

        for i, test_case in enumerate(test_cases):
            try:
                if progress_callback:
                    progress_callback(f"Converting SVG {i+1}/{total_cases}", i, total_cases)

                pptx_path = await self._convert_single_svg(test_case)
                pptx_files[test_case.name] = pptx_path

                logger.debug(f"Converted {test_case.name}: {pptx_path}")

            except Exception as e:
                logger.error(f"Failed to convert {test_case.name}: {e}")

        successful = len(pptx_files)
        logger.info(f"SVG conversion completed: {successful}/{total_cases} successful")

        return pptx_files

    async def _convert_single_svg(self, test_case: W3CTestCase) -> Path:
        """Convert single SVG file to PPTX."""
        output_path = self.config.output_dir / "pptx" / f"{test_case.name}.pptx"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Use SVG2PPTX conversion
        convert_svg_to_pptx(str(test_case.svg_path), str(output_path))

        if not output_path.exists():
            raise RuntimeError(f"PPTX conversion failed for {test_case.name}")

        return output_path

    async def _run_comparisons(self, test_cases: List[W3CTestCase],
                             pptx_files: Dict[str, Path],
                             progress_callback: Optional[callable] = None) -> List[ComparisonResult]:
        """Run visual comparisons for all test cases."""
        results = []
        total_cases = len(test_cases)

        logger.info(f"Running visual comparisons for {total_cases} test cases")

        for i, test_case in enumerate(test_cases):
            try:
                if progress_callback:
                    progress_callback(f"Comparing {i+1}/{total_cases}", i, total_cases)

                pptx_path = pptx_files.get(test_case.name)
                if not pptx_path or not pptx_path.exists():
                    logger.warning(f"PPTX file not found for {test_case.name}")
                    continue

                # Run comparison
                output_dir = self.config.output_dir / "comparisons" / test_case.name
                result = await self.comparator.compare_test_case(
                    test_case, pptx_path, self.libreoffice_controller, output_dir
                )

                results.append(result)

                if result.success:
                    logger.debug(f"Comparison completed: {test_case.name} - {result.overall_compliance.value}")
                else:
                    logger.warning(f"Comparison failed: {test_case.name} - {result.error_message}")

            except Exception as e:
                logger.error(f"Comparison error for {test_case.name}: {e}")

        successful = sum(1 for r in results if r.success)
        logger.info(f"Visual comparisons completed: {successful}/{total_cases} successful")

        return results

    def _analyze_results(self, report: ComplianceReport):
        """Analyze test results and populate report metrics."""
        try:
            # Basic counts
            report.successful_tests = sum(1 for r in report.results if r.success)
            report.failed_tests = sum(1 for r in report.results if not r.success)

            # Compliance distribution
            compliance_counts = {}
            category_scores = {}
            feature_scores = {}

            successful_results = [r for r in report.results if r.success]

            for result in successful_results:
                # Count compliance levels
                level = result.overall_compliance.value
                compliance_counts[level] = compliance_counts.get(level, 0) + 1

                # Category scores
                category = result.test_case.category
                if category not in category_scores:
                    category_scores[category] = []
                if result.metrics:
                    category_scores[category].append(result.metrics.overall_score)

                # Feature scores
                for feature_compliance in result.feature_compliance:
                    feature = feature_compliance.feature_name
                    if feature not in feature_scores:
                        feature_scores[feature] = []
                    feature_scores[feature].append(feature_compliance.score)

            report.compliance_distribution = compliance_counts

            # Calculate average scores
            for category, scores in category_scores.items():
                report.category_scores[category] = sum(scores) / len(scores) if scores else 0.0

            for feature, scores in feature_scores.items():
                report.feature_scores[feature] = sum(scores) / len(scores) if scores else 0.0

            # Overall compliance score
            all_scores = []
            for result in successful_results:
                if result.metrics:
                    all_scores.append(result.metrics.overall_score)

            report.overall_compliance_score = sum(all_scores) / len(all_scores) if all_scores else 0.0

            # Identify common issues
            report.common_issues = self._identify_common_issues(successful_results)

            # Generate recommendations
            report.recommendations = self._generate_recommendations(report)

            logger.info("Result analysis completed")

        except Exception as e:
            logger.error(f"Failed to analyze results: {e}")

    def _identify_common_issues(self, results: List[ComparisonResult]) -> List[str]:
        """Identify common issues across test results."""
        issues = []

        try:
            # Count feature compliance issues
            feature_issues = {}
            for result in results:
                for feature_compliance in result.feature_compliance:
                    if feature_compliance.level in [ComplianceLevel.LOW, ComplianceLevel.FAIL]:
                        for issue in feature_compliance.issues:
                            feature_issues[issue] = feature_issues.get(issue, 0) + 1

            # Report issues that occur in multiple tests
            common_threshold = max(2, len(results) * 0.1)  # At least 2 or 10% of tests
            for issue, count in feature_issues.items():
                if count >= common_threshold:
                    issues.append(f"{issue} (affects {count} tests)")

        except Exception as e:
            logger.error(f"Failed to identify common issues: {e}")

        return issues

    def _generate_recommendations(self, report: ComplianceReport) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        try:
            # Low overall score
            if report.overall_compliance_score < 0.7:
                recommendations.append("Overall compliance is low. Focus on basic shape and color rendering.")

            # Category-specific recommendations
            for category, score in report.category_scores.items():
                if score < 0.6:
                    recommendations.append(f"Improve {category} support - current score: {score:.2f}")

            # Feature-specific recommendations
            for feature, score in report.feature_scores.items():
                if score < 0.5:
                    recommendations.append(f"Critical: {feature} feature needs significant improvement")

        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")

        return recommendations

    async def _generate_html_report(self, report: ComplianceReport):
        """Generate HTML compliance report."""
        try:
            html_path = self.config.output_dir / f"compliance_report_{self.session_id}.html"

            html_content = self._build_html_report(report)

            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"HTML report generated: {html_path}")

        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")

    def _build_html_report(self, report: ComplianceReport) -> str:
        """Build HTML report content."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>W3C SVG Compliance Report - {report.session_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f5f5f5; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric {{ background-color: #e7f3ff; padding: 15px; border-radius: 5px; flex: 1; }}
        .results {{ margin: 20px 0; }}
        .test-case {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
        .success {{ border-left: 5px solid #4caf50; }}
        .failure {{ border-left: 5px solid #f44336; }}
        .compliance-full {{ color: #4caf50; }}
        .compliance-high {{ color: #8bc34a; }}
        .compliance-medium {{ color: #ff9800; }}
        .compliance-low {{ color: #ff5722; }}
        .compliance-fail {{ color: #f44336; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>W3C SVG Compliance Report</h1>
        <p>Session: {report.session_id}</p>
        <p>Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Test Suite: {report.config.test_suite.value}</p>
    </div>

    <div class="summary">
        <div class="metric">
            <h3>Overall Score</h3>
            <p style="font-size: 2em; margin: 0;">{report.overall_compliance_score:.3f}</p>
        </div>
        <div class="metric">
            <h3>Tests</h3>
            <p>Total: {report.total_tests}</p>
            <p>Successful: {report.successful_tests}</p>
            <p>Failed: {report.failed_tests}</p>
        </div>
        <div class="metric">
            <h3>Performance</h3>
            <p>Total Time: {report.total_execution_time:.1f}s</p>
            <p>Avg per Test: {report.average_test_time:.1f}s</p>
        </div>
    </div>

    <h2>Compliance Distribution</h2>
    <ul>
"""

        for level, count in report.compliance_distribution.items():
            html += f'<li class="compliance-{level}">{level.title()}: {count} tests</li>'

        html += """
    </ul>

    <h2>Category Scores</h2>
    <ul>
"""

        for category, score in report.category_scores.items():
            html += f'<li>{category}: {score:.3f}</li>'

        html += """
    </ul>

    <h2>Test Results</h2>
    <div class="results">
"""

        for result in report.results:
            if result.success:
                status_class = "success"
                status_text = f"✓ {result.overall_compliance.value.upper()}"
                score_text = f"Score: {result.metrics.overall_score:.3f}" if result.metrics else "No metrics"
            else:
                status_class = "failure"
                status_text = "✗ FAILED"
                score_text = f"Error: {result.error_message}"

            html += f"""
        <div class="test-case {status_class}">
            <h4>{result.test_case.name}</h4>
            <p><strong>Status:</strong> <span class="compliance-{result.overall_compliance.value}">{status_text}</span></p>
            <p><strong>Category:</strong> {result.test_case.category}</p>
            <p><strong>Result:</strong> {score_text}</p>
            {f'<p><strong>Description:</strong> {result.test_case.description}</p>' if result.test_case.description else ''}
        </div>
"""

        html += """
    </div>

    <h2>Common Issues</h2>
    <ul>
"""

        for issue in report.common_issues:
            html += f'<li>{issue}</li>'

        html += """
    </ul>

    <h2>Recommendations</h2>
    <ul>
"""

        for recommendation in report.recommendations:
            html += f'<li>{recommendation}</li>'

        html += """
    </ul>

</body>
</html>
"""

        return html

    def __del__(self):
        """Cleanup on deletion."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.cleanup())
            else:
                asyncio.run(self.cleanup())
        except:
            pass  # Ignore cleanup errors during deletion