#!/usr/bin/env python3
"""
Coverage Regression Prevention System

Checks for coverage regressions and enforces coverage standards in CI/CD pipeline.
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional, Tuple
import json
from datetime import datetime


class CoverageRegressionChecker:
    """Check for coverage regressions and enforce quality gates."""
    
    def __init__(self):
        self.baseline_coverage = 38.35  # Current baseline
        self.target_coverage = 90.0     # Target coverage
        self.regression_threshold = 2.0  # Allow 2% regression max
        
    def parse_coverage_xml(self, xml_file: Path) -> Dict[str, float]:
        """Parse coverage XML and extract metrics."""
        if not xml_file.exists():
            raise FileNotFoundError(f"Coverage file not found: {xml_file}")
        
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        return {
            'line_rate': float(root.get('line-rate', 0)) * 100,
            'branch_rate': float(root.get('branch-rate', 0)) * 100,
            'lines_covered': int(root.get('lines-covered', 0)),
            'lines_valid': int(root.get('lines-valid', 0)),
            'branches_covered': int(root.get('branches-covered', 0)),
            'branches_valid': int(root.get('branches-valid', 0))
        }
    
    def check_regression(self, current_coverage: float, baseline_coverage: float, 
                        threshold: float) -> Tuple[bool, str]:
        """Check if current coverage represents a regression."""
        regression = baseline_coverage - current_coverage
        
        if regression > threshold:
            message = f"❌ Coverage regression detected: {regression:.2f}% drop "
            message += f"(current: {current_coverage:.2f}%, baseline: {baseline_coverage:.2f}%)"
            return False, message
        elif regression > 0:
            message = f"⚠️  Minor coverage decrease: {regression:.2f}% "
            message += f"(current: {current_coverage:.2f}%, baseline: {baseline_coverage:.2f}%)"
            return True, message
        else:
            improvement = current_coverage - baseline_coverage
            message = f"✅ Coverage improved by {improvement:.2f}% "
            message += f"(current: {current_coverage:.2f}%, baseline: {baseline_coverage:.2f}%)"
            return True, message
    
    def generate_quality_report(self, metrics: Dict[str, float]) -> Dict[str, any]:
        """Generate comprehensive quality report."""
        current_coverage = metrics['line_rate']
        progress_to_target = (current_coverage - self.baseline_coverage) / (self.target_coverage - self.baseline_coverage) * 100
        
        # Quality gates
        gates = {
            'minimum_coverage': {
                'threshold': self.baseline_coverage - self.regression_threshold,
                'current': current_coverage,
                'passed': current_coverage >= (self.baseline_coverage - self.regression_threshold),
                'description': f"Coverage must not drop below {self.baseline_coverage - self.regression_threshold:.1f}%"
            },
            'regression_check': {
                'threshold': self.regression_threshold,
                'current': max(0, self.baseline_coverage - current_coverage),
                'passed': current_coverage >= (self.baseline_coverage - self.regression_threshold),
                'description': f"Coverage regression must not exceed {self.regression_threshold}%"
            },
            'improvement_trend': {
                'threshold': self.baseline_coverage,
                'current': current_coverage,
                'passed': current_coverage >= self.baseline_coverage,
                'description': "Coverage should improve over time"
            }
        }
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics,
            'baseline_coverage': self.baseline_coverage,
            'target_coverage': self.target_coverage,
            'progress_to_target': max(0, progress_to_target),
            'quality_gates': gates,
            'overall_status': all(gate['passed'] for gate in gates.values())
        }
        
        return report
    
    def format_report(self, report: Dict[str, any]) -> str:
        """Format report for console output."""
        lines = []
        lines.append("=" * 80)
        lines.append("📊 COVERAGE REGRESSION CHECK REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        # Current metrics
        metrics = report['metrics']
        lines.append(f"📈 Current Coverage: {metrics['line_rate']:.2f}%")
        lines.append(f"🎯 Baseline Coverage: {report['baseline_coverage']:.2f}%")
        lines.append(f"🚀 Target Coverage: {report['target_coverage']:.2f}%")
        lines.append(f"📊 Progress to Target: {report['progress_to_target']:.1f}%")
        lines.append("")
        
        # Quality gates
        lines.append("🚪 QUALITY GATES:")
        for gate_name, gate in report['quality_gates'].items():
            status = "✅ PASS" if gate['passed'] else "❌ FAIL"
            lines.append(f"  {status} {gate_name.replace('_', ' ').title()}: {gate['current']:.2f}%")
            lines.append(f"      {gate['description']}")
        lines.append("")
        
        # Overall status
        overall_status = "✅ PASSED" if report['overall_status'] else "❌ FAILED"
        lines.append(f"🎯 Overall Status: {overall_status}")
        lines.append("")
        
        # Coverage breakdown
        lines.append("📋 DETAILED METRICS:")
        lines.append(f"  • Lines: {metrics['lines_covered']}/{metrics['lines_valid']} ({metrics['line_rate']:.2f}%)")
        lines.append(f"  • Branches: {metrics['branches_covered']}/{metrics['branches_valid']} ({metrics['branch_rate']:.2f}%)")
        lines.append("")
        
        return "\n".join(lines)
    
    def save_report(self, report: Dict[str, any], output_file: Path):
        """Save report to JSON file."""
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"📄 Report saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Check coverage regression")
    parser.add_argument('--current-coverage', required=True, help='Path to current coverage.xml')
    parser.add_argument('--baseline-coverage', type=float, default=38.35, help='Baseline coverage percentage')
    parser.add_argument('--target-coverage', type=float, default=90.0, help='Target coverage percentage')
    parser.add_argument('--regression-threshold', type=float, default=2.0, help='Max allowed regression percentage')
    parser.add_argument('--output-report', help='Path to save JSON report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    checker = CoverageRegressionChecker()
    checker.baseline_coverage = args.baseline_coverage
    checker.target_coverage = args.target_coverage
    checker.regression_threshold = args.regression_threshold
    
    try:
        # Parse current coverage
        current_metrics = checker.parse_coverage_xml(Path(args.current_coverage))
        current_coverage = current_metrics['line_rate']
        
        # Check regression
        passed, message = checker.check_regression(
            current_coverage, 
            args.baseline_coverage, 
            args.regression_threshold
        )
        
        # Generate quality report
        report = checker.generate_quality_report(current_metrics)
        
        # Output results
        print(checker.format_report(report))
        print(message)
        print()
        
        # Save report if requested
        if args.output_report:
            checker.save_report(report, Path(args.output_report))
        
        # Exit with appropriate code
        if not report['overall_status']:
            print("💥 Coverage check failed! Please improve test coverage before merging.")
            sys.exit(1)
        else:
            print("🎉 Coverage check passed!")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Error during coverage check: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()