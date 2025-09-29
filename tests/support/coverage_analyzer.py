#!/usr/bin/env python3
"""
Coverage Analysis Tool for Test Suite Modernization

This tool validates test coverage quality and identifies tests that don't
actually execute target code (over-mocked tests).

Key Features:
- Line-by-line coverage validation for critical modules
- Mock vs real code execution analysis
- Coverage gap identification and reporting
- Integration with pytest-cov for detailed analysis
"""

import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
import re


@dataclass
class CoverageReport:
    """Detailed coverage report for a module."""
    module_name: str
    total_lines: int
    covered_lines: int
    missing_lines: List[int]
    coverage_percentage: float
    branch_coverage: Optional[float] = None
    executed_by_tests: Dict[str, Set[int]] = field(default_factory=dict)
    mock_only_tests: List[str] = field(default_factory=list)


@dataclass
class TestExecutionAnalysis:
    """Analysis of what a test actually executes."""
    test_name: str
    target_module: str
    lines_executed: Set[int]
    uses_mocks: bool
    mock_ratio: float  # Percentage of mocked vs real calls
    executes_business_logic: bool


class CoverageAnalyzer:
    """Analyze test coverage quality and identify non-executing tests."""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.src_dir = self.project_root / "src"
        self.test_dir = self.project_root / "tests"
        self.coverage_data = {}
        self.test_analyses = []

    def analyze_module_coverage(self, module_path: str, test_path: str = None) -> CoverageReport:
        """
        Analyze coverage for a specific module.

        Args:
            module_path: Path to the module to analyze (e.g., 'src.converters.base')
            test_path: Optional specific test file to run

        Returns:
            Detailed coverage report for the module
        """
        # Run pytest with coverage for specific module
        cmd = [
            "python", "-m", "pytest",
            "--cov=" + module_path,
            "--cov-report=json",
            "--cov-report=term-missing",
            "-q"
        ]

        if test_path:
            cmd.append(test_path)
        else:
            cmd.append("tests/")

        # Set PYTHONPATH environment variable
        env = {"PYTHONPATH": str(self.project_root)}

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                env={**subprocess.os.environ, **env}
            )

            # Parse coverage.json if it exists
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                return self._parse_coverage_json(coverage_file, module_path)
            else:
                # Fallback to parsing terminal output
                return self._parse_coverage_output(result.stdout, module_path)

        except Exception as e:
            print(f"Error analyzing coverage: {e}")
            return CoverageReport(
                module_name=module_path,
                total_lines=0,
                covered_lines=0,
                missing_lines=[],
                coverage_percentage=0.0
            )

    def _parse_coverage_json(self, coverage_file: Path, module_path: str) -> CoverageReport:
        """Parse coverage.json file for detailed coverage data."""
        with open(coverage_file, 'r') as f:
            data = json.load(f)

        # Find the module in the coverage data
        module_key = None
        for key in data.get('files', {}):
            if module_path.replace('.', '/') in key:
                module_key = key
                break

        if not module_key:
            return CoverageReport(
                module_name=module_path,
                total_lines=0,
                covered_lines=0,
                missing_lines=[],
                coverage_percentage=0.0
            )

        file_data = data['files'][module_key]
        executed_lines = file_data.get('executed_lines', [])
        missing_lines = file_data.get('missing_lines', [])

        total_lines = len(executed_lines) + len(missing_lines)
        coverage_pct = (len(executed_lines) / total_lines * 100) if total_lines > 0 else 0

        return CoverageReport(
            module_name=module_path,
            total_lines=total_lines,
            covered_lines=len(executed_lines),
            missing_lines=missing_lines,
            coverage_percentage=coverage_pct
        )

    def _parse_coverage_output(self, output: str, module_path: str) -> CoverageReport:
        """Parse terminal coverage output as fallback."""
        lines = output.split('\n')

        # Look for the module in the output
        for line in lines:
            if module_path in line or module_path.replace('.', '/') in line:
                # Parse coverage percentage
                match = re.search(r'(\d+(?:\.\d+)?)\%', line)
                if match:
                    coverage_pct = float(match.group(1))
                else:
                    coverage_pct = 0.0

                # Parse missing lines
                missing_match = re.search(r'Missing:\s*([\d,\s-]+)', line)
                missing_lines = []
                if missing_match:
                    missing_str = missing_match.group(1)
                    # Parse line ranges and individual lines
                    for part in missing_str.split(','):
                        part = part.strip()
                        if '-' in part:
                            start, end = part.split('-')
                            missing_lines.extend(range(int(start), int(end) + 1))
                        elif part.isdigit():
                            missing_lines.append(int(part))

                return CoverageReport(
                    module_name=module_path,
                    total_lines=100,  # Estimate
                    covered_lines=int(coverage_pct),
                    missing_lines=missing_lines,
                    coverage_percentage=coverage_pct
                )

        return CoverageReport(
            module_name=module_path,
            total_lines=0,
            covered_lines=0,
            missing_lines=[],
            coverage_percentage=0.0
        )

    def identify_mock_only_tests(self, test_file: Path) -> List[TestExecutionAnalysis]:
        """
        Identify tests that only execute mocks, not real code.

        Args:
            test_file: Path to test file to analyze

        Returns:
            List of test execution analyses
        """
        analyses = []

        with open(test_file, 'r') as f:
            content = f.read()

        # Parse the AST to find test methods and mock usage
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                mock_count = 0
                real_call_count = 0

                # Count mock vs real calls
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        call_str = ast.unparse(child.func) if hasattr(ast, 'unparse') else str(child.func)

                        if 'Mock' in call_str or 'mock' in call_str.lower():
                            mock_count += 1
                        elif 'assert' not in call_str.lower():
                            real_call_count += 1

                total_calls = mock_count + real_call_count
                mock_ratio = (mock_count / total_calls) if total_calls > 0 else 0

                analysis = TestExecutionAnalysis(
                    test_name=node.name,
                    target_module="unknown",  # Would need more analysis to determine
                    lines_executed=set(),
                    uses_mocks=mock_count > 0,
                    mock_ratio=mock_ratio,
                    executes_business_logic=real_call_count > 0
                )
                analyses.append(analysis)

        return analyses

    def find_coverage_gaps(self, module_path: str, min_coverage: float = 80.0) -> Dict[str, Any]:
        """
        Find coverage gaps in a module.

        Args:
            module_path: Module to analyze
            min_coverage: Minimum acceptable coverage percentage

        Returns:
            Dictionary containing gap analysis
        """
        report = self.analyze_module_coverage(module_path)

        gaps = {
            'module': module_path,
            'current_coverage': report.coverage_percentage,
            'target_coverage': min_coverage,
            'coverage_gap': max(0, min_coverage - report.coverage_percentage),
            'missing_lines': report.missing_lines,
            'lines_to_cover': len(report.missing_lines),
            'meets_target': report.coverage_percentage >= min_coverage
        }

        # Analyze the missing lines to identify patterns
        if report.missing_lines:
            gaps['missing_patterns'] = self._analyze_missing_patterns(
                module_path, report.missing_lines
            )

        return gaps

    def _analyze_missing_patterns(self, module_path: str, missing_lines: List[int]) -> Dict[str, Any]:
        """Analyze patterns in missing coverage."""
        patterns = {
            'error_handling': 0,
            'edge_cases': 0,
            'main_logic': 0,
            'initialization': 0
        }

        # This would require parsing the actual module to categorize missing lines
        # For now, return a simple analysis
        consecutive_gaps = []
        if missing_lines:
            current_gap = [missing_lines[0]]
            for line in missing_lines[1:]:
                if line == current_gap[-1] + 1:
                    current_gap.append(line)
                else:
                    consecutive_gaps.append(current_gap)
                    current_gap = [line]
            consecutive_gaps.append(current_gap)

        patterns['consecutive_gaps'] = len(consecutive_gaps)
        patterns['largest_gap'] = max(len(gap) for gap in consecutive_gaps) if consecutive_gaps else 0
        patterns['isolated_lines'] = sum(1 for gap in consecutive_gaps if len(gap) == 1)

        return patterns

    def generate_coverage_report(self, modules: List[str], output_file: str = None) -> Dict[str, Any]:
        """
        Generate comprehensive coverage report for multiple modules.

        Args:
            modules: List of module paths to analyze
            output_file: Optional file to save report to

        Returns:
            Comprehensive coverage analysis
        """
        report = {
            'summary': {
                'total_modules': len(modules),
                'modules_analyzed': 0,
                'average_coverage': 0.0,
                'modules_meeting_target': 0,
                'modules_below_target': 0
            },
            'modules': {},
            'recommendations': []
        }

        total_coverage = 0.0
        target_coverage = 80.0

        for module in modules:
            print(f"Analyzing {module}...")
            coverage = self.analyze_module_coverage(module)
            gaps = self.find_coverage_gaps(module, target_coverage)

            report['modules'][module] = {
                'coverage': coverage.coverage_percentage,
                'missing_lines': coverage.missing_lines,
                'gaps': gaps
            }

            total_coverage += coverage.coverage_percentage
            report['summary']['modules_analyzed'] += 1

            if coverage.coverage_percentage >= target_coverage:
                report['summary']['modules_meeting_target'] += 1
            else:
                report['summary']['modules_below_target'] += 1

        # Calculate average coverage
        if report['summary']['modules_analyzed'] > 0:
            report['summary']['average_coverage'] = (
                total_coverage / report['summary']['modules_analyzed']
            )

        # Generate recommendations
        report['recommendations'] = self._generate_recommendations(report)

        # Save report if output file specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"Report saved to {output_file}")

        return report

    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on coverage analysis."""
        recommendations = []

        # Overall coverage recommendation
        avg_coverage = report['summary']['average_coverage']
        if avg_coverage < 60:
            recommendations.append(
                "CRITICAL: Average coverage is below 60%. Focus on adding basic test coverage "
                "for main code paths before addressing edge cases."
            )
        elif avg_coverage < 80:
            recommendations.append(
                "Coverage is below target. Prioritize modules with lowest coverage first."
            )

        # Module-specific recommendations
        low_coverage_modules = [
            (name, data['coverage'])
            for name, data in report['modules'].items()
            if data['coverage'] < 80
        ]

        if low_coverage_modules:
            low_coverage_modules.sort(key=lambda x: x[1])
            worst_modules = low_coverage_modules[:3]

            recommendations.append(
                f"Priority modules for coverage improvement: "
                f"{', '.join(f'{m[0]} ({m[1]:.1f}%)' for m in worst_modules)}"
            )

        # Pattern-based recommendations
        for module, data in report['modules'].items():
            if 'gaps' in data and 'missing_patterns' in data['gaps']:
                patterns = data['gaps']['missing_patterns']
                if patterns.get('largest_gap', 0) > 20:
                    recommendations.append(
                        f"{module}: Large uncovered code block detected "
                        f"({patterns['largest_gap']} lines). May indicate untested feature."
                    )

        return recommendations


def main():
    """Main execution function for coverage analysis."""
    import argparse

    parser = argparse.ArgumentParser(description="Coverage Analysis Tool")
    parser.add_argument(
        "modules",
        nargs='+',
        help="Modules to analyze (e.g., src.converters.base)"
    )
    parser.add_argument(
        "--output", "-o",
        default="tests/support/coverage_analysis_report.json",
        help="Output file for report"
    )
    parser.add_argument(
        "--target", "-t",
        type=float,
        default=80.0,
        help="Target coverage percentage"
    )
    parser.add_argument(
        "--check-mocks", "-m",
        action="store_true",
        help="Check for over-mocked tests"
    )

    args = parser.parse_args()

    print("🔍 Starting Coverage Analysis...")

    analyzer = CoverageAnalyzer()

    # Generate comprehensive report
    report = analyzer.generate_coverage_report(args.modules, args.output)

    # Print summary
    print("\n" + "="*60)
    print("📊 COVERAGE ANALYSIS SUMMARY")
    print("="*60)

    summary = report['summary']
    print(f"📁 Modules analyzed: {summary['modules_analyzed']}")
    print(f"📈 Average coverage: {summary['average_coverage']:.2f}%")
    print(f"✅ Meeting target (≥{args.target}%): {summary['modules_meeting_target']}")
    print(f"❌ Below target: {summary['modules_below_target']}")

    if report['recommendations']:
        print("\n🎯 Recommendations:")
        for rec in report['recommendations']:
            print(f"  • {rec}")

    print(f"\n📄 Full report saved to: {args.output}")

    # Check for mock-only tests if requested
    if args.check_mocks:
        print("\n🔍 Checking for over-mocked tests...")
        test_files = list(Path("tests/unit").rglob("test_*.py"))

        total_tests = 0
        mock_only_tests = 0

        for test_file in test_files[:5]:  # Sample first 5 files
            analyses = analyzer.identify_mock_only_tests(test_file)
            for analysis in analyses:
                total_tests += 1
                if analysis.mock_ratio > 0.8:
                    mock_only_tests += 1
                    print(f"  ⚠️  {test_file.name}::{analysis.test_name} "
                          f"(mock ratio: {analysis.mock_ratio:.0%})")

        if total_tests > 0:
            print(f"\n📊 Mock Analysis: {mock_only_tests}/{total_tests} tests "
                  f"are primarily mocked ({mock_only_tests/total_tests:.0%})")


if __name__ == "__main__":
    main()