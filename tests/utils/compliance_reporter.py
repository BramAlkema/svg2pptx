#!/usr/bin/env python3
"""
Compliance reporting utilities for W3C test suite results.

This module generates comprehensive reports in multiple formats including
HTML, JSON, and Markdown for compliance test results.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import statistics
import logging

logger = logging.getLogger(__name__)


class ComplianceReporter:
    """Generate compliance test reports in multiple formats."""

    def __init__(self, reports_dir: Optional[Path] = None):
        """
        Initialize compliance reporter.

        Args:
            reports_dir: Directory for saving reports (default: reports/compliance)
        """
        self.reports_dir = reports_dir or Path('reports/compliance')
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(self, results: List[Dict], category: str) -> Dict:
        """
        Generate comprehensive compliance report.

        Args:
            results: List of compliance test results
            category: Test category name (e.g., 'w3c_shapes')

        Returns:
            Complete report dictionary
        """
        timestamp = datetime.now()

        report = {
            'category': category,
            'timestamp': timestamp.isoformat(),
            'summary': self._calculate_summary(results),
            'details': results,
            'visualizations': self._generate_visualizations(results),
            'recommendations': self._generate_recommendations(results)
        }

        # Save reports in multiple formats
        self._save_json_report(report, category, timestamp)
        self._save_html_report(report, category, timestamp)
        self._save_markdown_summary(report, category, timestamp)

        logger.info(f"Generated compliance report for {category}: {len(results)} tests")
        return report

    def _calculate_summary(self, results: List[Dict]) -> Dict:
        """
        Calculate summary statistics for test results.

        Args:
            results: List of test result dictionaries

        Returns:
            Summary statistics dictionary
        """
        if not results:
            return {
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'pass_rate': 0.0,
                'average_score': 0.0,
                'min_score': 0.0,
                'max_score': 0.0
            }

        scores = [r.get('score', 0.0) for r in results]
        passed = [r for r in results if r.get('passed', False)]

        return {
            'total_tests': len(results),
            'passed': len(passed),
            'failed': len(results) - len(passed),
            'pass_rate': len(passed) / len(results),
            'average_score': statistics.mean(scores),
            'median_score': statistics.median(scores),
            'min_score': min(scores),
            'max_score': max(scores),
            'std_deviation': statistics.stdev(scores) if len(scores) > 1 else 0.0
        }

    def _generate_visualizations(self, results: List[Dict]) -> Dict:
        """
        Generate visualization data for charts and graphs.

        Args:
            results: List of test result dictionaries

        Returns:
            Visualization data dictionary
        """
        # Group by category if available
        by_category = {}
        for result in results:
            cat = result.get('category', 'unknown')
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(result.get('score', 0.0))

        # Calculate category averages
        category_averages = {k: statistics.mean(v) for k, v in by_category.items()}

        # Score distribution
        scores = [r.get('score', 0.0) for r in results]
        score_distribution = self._calculate_distribution(scores)

        # Pass/fail by test ID (for detailed analysis)
        test_results = {
            r.get('test_id', 'unknown'): {
                'score': r.get('score', 0.0),
                'passed': r.get('passed', False),
                'category': r.get('category', 'unknown')
            }
            for r in results
        }

        return {
            'by_category': category_averages,
            'score_distribution': score_distribution,
            'test_results': test_results,
            'trends': self._calculate_trends(results)
        }

    def _calculate_distribution(self, scores: List[float]) -> Dict:
        """
        Calculate score distribution across ranges.

        Args:
            scores: List of score values

        Returns:
            Distribution dictionary
        """
        if not scores:
            return {}

        ranges = {
            '0-20%': 0,
            '20-40%': 0,
            '40-60%': 0,
            '60-80%': 0,
            '80-100%': 0
        }

        for score in scores:
            if score < 0.2:
                ranges['0-20%'] += 1
            elif score < 0.4:
                ranges['20-40%'] += 1
            elif score < 0.6:
                ranges['40-60%'] += 1
            elif score < 0.8:
                ranges['60-80%'] += 1
            else:
                ranges['80-100%'] += 1

        return ranges

    def _calculate_trends(self, results: List[Dict]) -> Dict:
        """
        Calculate trends and patterns in test results.

        Args:
            results: List of test result dictionaries

        Returns:
            Trends analysis dictionary
        """
        # Identify failing patterns
        failing_tests = [r for r in results if not r.get('passed', False)]
        failing_categories = {}

        for test in failing_tests:
            cat = test.get('category', 'unknown')
            failing_categories[cat] = failing_categories.get(cat, 0) + 1

        # Identify high-performing areas
        high_scores = [r for r in results if r.get('score', 0.0) >= 0.9]
        high_performing_categories = {}

        for test in high_scores:
            cat = test.get('category', 'unknown')
            high_performing_categories[cat] = high_performing_categories.get(cat, 0) + 1

        return {
            'failing_categories': failing_categories,
            'high_performing_categories': high_performing_categories,
            'total_errors': sum(len(r.get('errors', [])) for r in results)
        }

    def _generate_recommendations(self, results: List[Dict]) -> List[str]:
        """
        Generate recommendations based on test results.

        Args:
            results: List of test result dictionaries

        Returns:
            List of recommendation strings
        """
        recommendations = []
        summary = self._calculate_summary(results)

        # Overall performance recommendations
        if summary['pass_rate'] < 0.70:
            recommendations.append(
                "Overall pass rate is below 70%. Consider reviewing core conversion algorithms."
            )
        elif summary['pass_rate'] < 0.85:
            recommendations.append(
                "Pass rate is below target 85%. Focus on improving failing test categories."
            )

        # Score-based recommendations
        if summary['average_score'] < 0.75:
            recommendations.append(
                "Average score is below 75%. Review visual fidelity and structure preservation."
            )

        # Specific category recommendations
        visualizations = self._generate_visualizations(results)
        failing_cats = visualizations['trends']['failing_categories']

        if failing_cats:
            worst_category = max(failing_cats, key=failing_cats.get)
            recommendations.append(
                f"Focus improvement efforts on '{worst_category}' category "
                f"({failing_cats[worst_category]} failing tests)."
            )

        # Error-based recommendations
        error_count = visualizations['trends']['total_errors']
        if error_count > len(results) * 0.1:  # More than 10% of tests have errors
            recommendations.append(
                "High error rate detected. Review test infrastructure and conversion pipeline."
            )

        return recommendations

    def _save_json_report(self, report: Dict, category: str, timestamp: datetime):
        """Save report as JSON file."""
        filename = f"{category}_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        json_path = self.reports_dir / filename

        try:
            with open(json_path, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"JSON report saved: {json_path}")
        except IOError as e:
            logger.error(f"Failed to save JSON report: {e}")

    def _save_html_report(self, report: Dict, category: str, timestamp: datetime):
        """Save report as HTML file."""
        summary = report['summary']
        details = report['details']

        # Generate HTML content
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>W3C Compliance Report - {category}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .summary {{
            background: linear-gradient(135deg, #f0f0f0, #e0e0e0);
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px 10px 0;
            padding: 15px;
            background: white;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            min-width: 120px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .metric-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}
        .passed {{ color: #4CAF50; }}
        .failed {{ color: #f44336; }}
        .warning {{ color: #ff9800; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .status-badge {{
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .status-pass {{
            background: #4CAF50;
            color: white;
        }}
        .status-fail {{
            background: #f44336;
            color: white;
        }}
        .recommendations {{
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 20px;
            margin-top: 30px;
        }}
        .score-bar {{
            width: 100%;
            height: 20px;
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
        }}
        .score-fill {{
            height: 100%;
            background: linear-gradient(90deg, #f44336, #ff9800, #4CAF50);
            transition: width 0.3s ease;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>W3C Compliance Report</h1>
            <h2>{category.replace('_', ' ').title()}</h2>
            <p>Generated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="summary">
            <h2>Summary</h2>
            <div class="metric">
                <div class="metric-value">{summary['total_tests']}</div>
                <div class="metric-label">Total Tests</div>
            </div>
            <div class="metric">
                <div class="metric-value passed">{summary['passed']}</div>
                <div class="metric-label">Passed</div>
            </div>
            <div class="metric">
                <div class="metric-value failed">{summary['failed']}</div>
                <div class="metric-label">Failed</div>
            </div>
            <div class="metric">
                <div class="metric-value {'passed' if summary['pass_rate'] >= 0.85 else 'warning' if summary['pass_rate'] >= 0.70 else 'failed'}">{summary['pass_rate']:.1%}</div>
                <div class="metric-label">Pass Rate</div>
            </div>
            <div class="metric">
                <div class="metric-value">{summary['average_score']:.1%}</div>
                <div class="metric-label">Avg Score</div>
            </div>
        </div>

        <h2>Test Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Test ID</th>
                    <th>Category</th>
                    <th>Score</th>
                    <th>Status</th>
                    <th>Errors</th>
                </tr>
            </thead>
            <tbody>
                {''.join(f'''
                <tr>
                    <td>{r.get('test_id', 'unknown')}</td>
                    <td>{r.get('category', 'unknown')}</td>
                    <td>
                        <div class="score-bar">
                            <div class="score-fill" style="width: {r.get('score', 0) * 100}%"></div>
                        </div>
                        {r.get('score', 0):.1%}
                    </td>
                    <td>
                        <span class="status-badge {'status-pass' if r.get('passed', False) else 'status-fail'}">
                            {'Pass' if r.get('passed', False) else 'Fail'}
                        </span>
                    </td>
                    <td>{len(r.get('errors', []))}</td>
                </tr>
                ''' for r in details)}
            </tbody>
        </table>

        {'<div class="recommendations"><h2>Recommendations</h2><ul>' + ''.join(f'<li>{rec}</li>' for rec in report.get('recommendations', [])) + '</ul></div>' if report.get('recommendations') else ''}
    </div>
</body>
</html>
        """

        filename = f"{category}_report.html"
        html_path = self.reports_dir / filename

        try:
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"HTML report saved: {html_path}")
        except IOError as e:
            logger.error(f"Failed to save HTML report: {e}")

    def _save_markdown_summary(self, report: Dict, category: str, timestamp: datetime):
        """Save summary as Markdown file."""
        summary = report['summary']

        # Determine badge color based on pass rate
        pass_rate = summary['pass_rate']
        if pass_rate >= 0.85:
            badge_color = 'brightgreen'
        elif pass_rate >= 0.70:
            badge_color = 'yellow'
        else:
            badge_color = 'red'

        markdown = f"""# W3C Compliance Report - {category.replace('_', ' ').title()}

![W3C Compliance](https://img.shields.io/badge/W3C%20Compliance-{pass_rate:.0%}-{badge_color})
![Tests](https://img.shields.io/badge/Tests-{summary['passed']}/{summary['total_tests']}-blue)
![Average Score](https://img.shields.io/badge/Average%20Score-{summary['average_score']:.1%}-{'green' if summary['average_score'] >= 0.85 else 'yellow' if summary['average_score'] >= 0.70 else 'red'})

## Summary

- **Total Tests**: {summary['total_tests']}
- **Passed**: {summary['passed']} ({pass_rate:.1%})
- **Failed**: {summary['failed']}
- **Average Score**: {summary['average_score']:.1%}
- **Score Range**: {summary['min_score']:.1%} - {summary['max_score']:.1%}

## Results by Category

| Category | Tests | Pass Rate | Avg Score |
|----------|-------|-----------|-----------|
"""

        # Add category breakdown if available
        visualizations = report.get('visualizations', {})
        by_category = visualizations.get('by_category', {})

        for cat, avg_score in by_category.items():
            cat_tests = [r for r in report['details'] if r.get('category') == cat]
            cat_passed = len([r for r in cat_tests if r.get('passed', False)])
            cat_total = len(cat_tests)
            cat_pass_rate = cat_passed / cat_total if cat_total > 0 else 0

            markdown += f"| {cat} | {cat_total} | {cat_pass_rate:.1%} | {avg_score:.1%} |\n"

        # Add recommendations if available
        recommendations = report.get('recommendations', [])
        if recommendations:
            markdown += "\n## Recommendations\n\n"
            for i, rec in enumerate(recommendations, 1):
                markdown += f"{i}. {rec}\n"

        markdown += f"\n**Last Updated**: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"

        filename = f"{category}_summary.md"
        md_path = self.reports_dir / filename

        try:
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(markdown)
            logger.info(f"Markdown summary saved: {md_path}")
        except IOError as e:
            logger.error(f"Failed to save Markdown summary: {e}")

    def get_latest_report(self, category: str) -> Optional[Dict]:
        """
        Get the most recent report for a category.

        Args:
            category: Test category name

        Returns:
            Latest report dictionary or None if not found
        """
        # Find the most recent JSON report file
        pattern = f"{category}_*.json"
        report_files = list(self.reports_dir.glob(pattern))

        if not report_files:
            return None

        # Sort by modification time and get the latest
        latest_file = max(report_files, key=lambda p: p.stat().st_mtime)

        try:
            with open(latest_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load report {latest_file}: {e}")
            return None