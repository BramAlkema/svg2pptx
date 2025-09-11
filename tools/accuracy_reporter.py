#!/usr/bin/env python3
"""
Advanced accuracy reporting and analytics system.

This module provides comprehensive reporting capabilities for accuracy
measurements, including trend analysis, comparative reports, and
dashboard-style visualizations for conversion quality assessment.
"""

import json
import sqlite3
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import html as html_module
import logging

logger = logging.getLogger(__name__)


@dataclass
class AccuracyTrend:
    """Trend data for accuracy metrics over time."""
    dimension: str
    period: str
    scores: List[float]
    timestamps: List[datetime]
    trend_direction: str  # "improving", "declining", "stable"
    change_rate: float
    
    @property
    def average_score(self) -> float:
        """Calculate average score for the period."""
        return statistics.mean(self.scores) if self.scores else 0.0
    
    @property
    def score_range(self) -> Tuple[float, float]:
        """Get min and max scores for the period."""
        if not self.scores:
            return (0.0, 0.0)
        return (min(self.scores), max(self.scores))


class AccuracyReporter:
    """Advanced reporter for accuracy measurement results and analytics."""
    
    def __init__(self, database_path: Path):
        """Initialize reporter with database connection."""
        self.database_path = database_path
    
    def generate_summary_report(self, 
                               test_filter: Optional[str] = None,
                               days_back: int = 30) -> Dict[str, Any]:
        """Generate comprehensive summary report."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Base query with optional test filtering
                base_conditions = "WHERE datetime(timestamp) > datetime('now', '-{} days')".format(days_back)
                if test_filter:
                    base_conditions += f" AND test_name LIKE '%{test_filter}%'"
                
                # Get overall statistics
                cursor.execute(f'''
                    SELECT 
                        COUNT(*) as total_tests,
                        AVG(overall_score) as avg_score,
                        MIN(overall_score) as min_score,
                        MAX(overall_score) as max_score,
                        COUNT(CASE WHEN overall_level = 'excellent' THEN 1 END) as excellent_count,
                        COUNT(CASE WHEN overall_level = 'good' THEN 1 END) as good_count,
                        COUNT(CASE WHEN overall_level = 'acceptable' THEN 1 END) as acceptable_count,
                        COUNT(CASE WHEN overall_level = 'poor' THEN 1 END) as poor_count,
                        COUNT(CASE WHEN overall_level = 'failed' THEN 1 END) as failed_count,
                        AVG(processing_time) as avg_processing_time
                    FROM accuracy_reports {base_conditions}
                ''')
                
                stats = dict(cursor.fetchone())
                
                # Get dimensional breakdown
                cursor.execute(f'''
                    SELECT 
                        am.dimension,
                        AVG(am.score) as avg_score,
                        MIN(am.score) as min_score,
                        MAX(am.score) as max_score,
                        COUNT(*) as measurement_count
                    FROM accuracy_reports ar
                    JOIN accuracy_metrics am ON ar.id = am.report_id
                    {base_conditions}
                    GROUP BY am.dimension
                    ORDER BY avg_score DESC
                ''')
                
                dimensional_stats = [dict(row) for row in cursor.fetchall()]
                
                # Get recent test results
                cursor.execute(f'''
                    SELECT test_name, overall_score, overall_level, timestamp, processing_time
                    FROM accuracy_reports {base_conditions}
                    ORDER BY timestamp DESC
                    LIMIT 20
                ''')
                
                recent_tests = [dict(row) for row in cursor.fetchall()]
                
                # Calculate success rate
                total_tests = stats.get('total_tests', 0)
                if total_tests > 0:
                    success_rate = (stats.get('excellent_count', 0) + 
                                  stats.get('good_count', 0) + 
                                  stats.get('acceptable_count', 0)) / total_tests * 100
                else:
                    success_rate = 0.0
                
                return {
                    "period": f"Last {days_back} days",
                    "generated_at": datetime.now().isoformat(),
                    "filter": test_filter,
                    "overall_statistics": {
                        **stats,
                        "success_rate": success_rate
                    },
                    "dimensional_breakdown": dimensional_stats,
                    "recent_tests": recent_tests,
                    "quality_distribution": {
                        "excellent": stats.get('excellent_count', 0),
                        "good": stats.get('good_count', 0),
                        "acceptable": stats.get('acceptable_count', 0),
                        "poor": stats.get('poor_count', 0),
                        "failed": stats.get('failed_count', 0)
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to generate summary report: {e}")
            return {"error": str(e)}
    
    def analyze_accuracy_trends(self, dimension: Optional[str] = None) -> List[AccuracyTrend]:
        """Analyze accuracy trends over time by dimension."""
        try:
            trends = []
            periods = [
                ("daily", 1),
                ("weekly", 7), 
                ("monthly", 30)
            ]
            
            with sqlite3.connect(self.database_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                for period_name, days in periods:
                    if dimension:
                        # Specific dimension trend
                        cursor.execute('''
                            SELECT ar.timestamp, am.score
                            FROM accuracy_reports ar
                            JOIN accuracy_metrics am ON ar.id = am.report_id
                            WHERE am.dimension = ?
                            AND datetime(ar.timestamp) > datetime('now', '-{} days')
                            ORDER BY ar.timestamp ASC
                        '''.format(days * 2), (dimension,))
                    else:
                        # Overall accuracy trend
                        cursor.execute('''
                            SELECT timestamp, overall_score as score
                            FROM accuracy_reports
                            WHERE datetime(timestamp) > datetime('now', '-{} days')
                            ORDER BY timestamp ASC
                        '''.format(days * 2))
                    
                    rows = cursor.fetchall()
                    if len(rows) < 2:
                        continue
                    
                    scores = [row['score'] for row in rows]
                    timestamps = [datetime.fromisoformat(row['timestamp']) for row in rows]
                    
                    # Calculate trend direction
                    if len(scores) >= 2:
                        recent_avg = statistics.mean(scores[-max(1, len(scores)//2):])
                        earlier_avg = statistics.mean(scores[:max(1, len(scores)//2)])
                        change_rate = (recent_avg - earlier_avg) / earlier_avg if earlier_avg > 0 else 0
                        
                        if change_rate > 0.05:
                            trend_direction = "improving"
                        elif change_rate < -0.05:
                            trend_direction = "declining"
                        else:
                            trend_direction = "stable"
                    else:
                        trend_direction = "stable"
                        change_rate = 0.0
                    
                    trend = AccuracyTrend(
                        dimension=dimension or "overall",
                        period=period_name,
                        scores=scores,
                        timestamps=timestamps,
                        trend_direction=trend_direction,
                        change_rate=change_rate
                    )
                    
                    trends.append(trend)
            
            return trends
            
        except Exception as e:
            logger.error(f"Failed to analyze accuracy trends: {e}")
            return []
    
    def compare_test_suites(self, suite_names: List[str]) -> Dict[str, Any]:
        """Compare accuracy across different test suites."""
        try:
            comparisons = {}
            
            with sqlite3.connect(self.database_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                for suite_name in suite_names:
                    cursor.execute('''
                        SELECT 
                            COUNT(*) as test_count,
                            AVG(overall_score) as avg_score,
                            MIN(overall_score) as min_score,
                            MAX(overall_score) as max_score,
                            AVG(processing_time) as avg_time,
                            COUNT(CASE WHEN overall_level IN ('excellent', 'good') THEN 1 END) as success_count
                        FROM accuracy_reports
                        WHERE test_name LIKE ?
                    ''', (f'%{suite_name}%',))
                    
                    result = dict(cursor.fetchone())
                    
                    # Get dimensional breakdown for suite
                    cursor.execute('''
                        SELECT 
                            am.dimension,
                            AVG(am.score) as avg_score
                        FROM accuracy_reports ar
                        JOIN accuracy_metrics am ON ar.id = am.report_id
                        WHERE ar.test_name LIKE ?
                        GROUP BY am.dimension
                    ''', (f'%{suite_name}%',))
                    
                    dimensional_breakdown = {row['dimension']: row['avg_score'] 
                                           for row in cursor.fetchall()}
                    
                    result['success_rate'] = (result['success_count'] / result['test_count'] * 100 
                                            if result['test_count'] > 0 else 0)
                    result['dimensional_breakdown'] = dimensional_breakdown
                    
                    comparisons[suite_name] = result
            
            return {
                "comparison_date": datetime.now().isoformat(),
                "suites_compared": len(suite_names),
                "suite_comparisons": comparisons
            }
            
        except Exception as e:
            logger.error(f"Failed to compare test suites: {e}")
            return {"error": str(e)}
    
    def generate_html_report(self, 
                           output_path: Path,
                           test_filter: Optional[str] = None,
                           days_back: int = 30) -> Path:
        """Generate comprehensive HTML report."""
        try:
            # Get data for report
            summary = self.generate_summary_report(test_filter, days_back)
            trends = self.analyze_accuracy_trends()
            
            # Generate HTML content
            html_content = self._create_html_template(summary, trends)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")
            raise
    
    def _create_html_template(self, summary: Dict[str, Any], trends: List[AccuracyTrend]) -> str:
        """Create HTML template for accuracy report."""
        
        # Extract data for template with defaults
        stats = summary.get('overall_statistics', {}) or {}
        dimensional = summary.get('dimensional_breakdown', []) or []
        recent = summary.get('recent_tests', []) or []
        distribution = summary.get('quality_distribution', {}) or {}
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SVG to PPTX Accuracy Report</title>
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
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .header p {{
            margin: 10px 0 0;
            opacity: 0.9;
        }}
        .content {{
            padding: 30px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
        }}
        .metric-label {{
            color: #6c757d;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .section {{
            margin: 40px 0;
        }}
        .section h2 {{
            color: #343a40;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }}
        .table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .table th,
        .table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        .table th {{
            background-color: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }}
        .quality-bar {{
            display: flex;
            height: 30px;
            border-radius: 15px;
            overflow: hidden;
            background: #e9ecef;
            margin: 10px 0;
        }}
        .quality-segment {{
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 0.8em;
            font-weight: bold;
        }}
        .excellent {{ background-color: #28a745; }}
        .good {{ background-color: #17a2b8; }}
        .acceptable {{ background-color: #ffc107; }}
        .poor {{ background-color: #fd7e14; }}
        .failed {{ background-color: #dc3545; }}
        .trend-indicator {{
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        .trend-improving {{
            background-color: #d4edda;
            color: #155724;
        }}
        .trend-declining {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        .trend-stable {{
            background-color: #d1ecf1;
            color: #0c5460;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #6c757d;
            border-top: 1px solid #dee2e6;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SVG to PPTX Accuracy Report</h1>
            <p>Generated on {summary.get('generated_at', 'N/A')}</p>
            <p>Period: {summary.get('period', 'N/A')}</p>
        </div>
        
        <div class="content">
            <!-- Overall Metrics -->
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{stats.get('total_tests', 0)}</div>
                    <div class="metric-label">Total Tests</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{stats.get('avg_score', 0):.3f}</div>
                    <div class="metric-label">Average Score</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{stats.get('success_rate', 0):.1f}%</div>
                    <div class="metric-label">Success Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{stats.get('avg_processing_time', 0):.2f}s</div>
                    <div class="metric-label">Avg Processing Time</div>
                </div>
            </div>
            
            <!-- Quality Distribution -->
            <div class="section">
                <h2>Quality Distribution</h2>
                <div class="quality-bar">'''
        
        total = sum(distribution.values()) if distribution else 1
        for level, count in distribution.items():
            if count > 0:
                percentage = (count / total) * 100
                html += f'<div class="quality-segment {level}" style="width: {percentage}%">{count}</div>'
        
        html += f'''
                </div>
                <p>Distribution of test results by quality level</p>
            </div>
            
            <!-- Dimensional Breakdown -->
            <div class="section">
                <h2>Accuracy by Dimension</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Dimension</th>
                            <th>Average Score</th>
                            <th>Range</th>
                            <th>Measurements</th>
                        </tr>
                    </thead>
                    <tbody>'''
        
        for dim in dimensional:
            html += f'''
                        <tr>
                            <td>{dim.get('dimension', 'N/A').title()}</td>
                            <td>{dim.get('avg_score', 0):.3f}</td>
                            <td>{dim.get('min_score', 0):.3f} - {dim.get('max_score', 0):.3f}</td>
                            <td>{dim.get('measurement_count', 0)}</td>
                        </tr>'''
        
        html += '''
                    </tbody>
                </table>
            </div>
            
            <!-- Trends -->
            <div class="section">
                <h2>Accuracy Trends</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Period</th>
                            <th>Dimension</th>
                            <th>Average Score</th>
                            <th>Trend</th>
                            <th>Change Rate</th>
                        </tr>
                    </thead>
                    <tbody>'''
        
        for trend in trends:
            trend_class = f"trend-{trend.trend_direction}"
            html += f'''
                        <tr>
                            <td>{trend.period.title()}</td>
                            <td>{trend.dimension.title()}</td>
                            <td>{trend.average_score:.3f}</td>
                            <td><span class="trend-indicator {trend_class}">{trend.trend_direction.title()}</span></td>
                            <td>{trend.change_rate:+.2%}</td>
                        </tr>'''
        
        html += '''
                    </tbody>
                </table>
            </div>
            
            <!-- Recent Tests -->
            <div class="section">
                <h2>Recent Test Results</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Test Name</th>
                            <th>Score</th>
                            <th>Level</th>
                            <th>Timestamp</th>
                            <th>Processing Time</th>
                        </tr>
                    </thead>
                    <tbody>'''
        
        for test in recent[:10]:
            level_class = test.get('overall_level', 'unknown')
            html += f'''
                        <tr>
                            <td>{html_module.escape(test.get('test_name', 'N/A'))}</td>
                            <td>{test.get('overall_score', 0):.3f}</td>
                            <td><span class="trend-indicator {level_class}">{test.get('overall_level', 'N/A').title()}</span></td>
                            <td>{test.get('timestamp', 'N/A')}</td>
                            <td>{test.get('processing_time', 0):.2f}s</td>
                        </tr>'''
        
        html += f'''
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="footer">
            <p>SVG to PPTX Conversion Accuracy Report - Generated by AccuracyReporter</p>
        </div>
    </div>
</body>
</html>'''
        
        return html
    
    def export_data(self, 
                   output_path: Path, 
                   format_type: str = "json",
                   test_filter: Optional[str] = None) -> Path:
        """Export accuracy data in various formats."""
        try:
            if format_type.lower() == "json":
                return self._export_json(output_path, test_filter)
            elif format_type.lower() == "csv":
                return self._export_csv(output_path, test_filter)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
                
        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            raise
    
    def _export_json(self, output_path: Path, test_filter: Optional[str] = None) -> Path:
        """Export data as JSON."""
        summary = self.generate_summary_report(test_filter)
        trends = self.analyze_accuracy_trends()
        
        export_data = {
            "summary": summary,
            "trends": [
                {
                    "dimension": trend.dimension,
                    "period": trend.period,
                    "average_score": trend.average_score,
                    "trend_direction": trend.trend_direction,
                    "change_rate": trend.change_rate,
                    "score_range": trend.score_range
                }
                for trend in trends
            ],
            "export_metadata": {
                "generated_at": datetime.now().isoformat(),
                "format": "json",
                "filter": test_filter
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return output_path
    
    def _export_csv(self, output_path: Path, test_filter: Optional[str] = None) -> Path:
        """Export data as CSV."""
        import csv
        
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build query with optional filter
            query = '''
                SELECT ar.test_name, ar.svg_path, ar.pptx_path, ar.timestamp,
                       ar.overall_score, ar.overall_level, ar.processing_time,
                       am.dimension, am.score as dimension_score, am.weight
                FROM accuracy_reports ar
                LEFT JOIN accuracy_metrics am ON ar.id = am.report_id
            '''
            params = ()
            
            if test_filter:
                query += " WHERE ar.test_name LIKE ?"
                params = (f'%{test_filter}%',)
            
            query += " ORDER BY ar.timestamp DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            if rows:
                with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = rows[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for row in rows:
                        writer.writerow(dict(row))
        
        return output_path


def main():
    """Main function for standalone execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate SVG to PPTX Accuracy Reports")
    parser.add_argument("--database", required=True, help="Path to accuracy database")
    parser.add_argument("--output", required=True, help="Output path for report")
    parser.add_argument("--format", choices=["html", "json", "csv"], default="html",
                       help="Report format")
    parser.add_argument("--filter", help="Filter tests by name pattern")
    parser.add_argument("--days", type=int, default=30, help="Days to include in report")
    
    args = parser.parse_args()
    
    # Initialize reporter
    reporter = AccuracyReporter(Path(args.database))
    
    # Generate report
    output_path = Path(args.output)
    
    if args.format == "html":
        result_path = reporter.generate_html_report(
            output_path, args.filter, args.days
        )
    else:
        result_path = reporter.export_data(
            output_path, args.format, args.filter
        )
    
    print(f"Report generated: {result_path}")


if __name__ == "__main__":
    main()