#!/usr/bin/env python3
"""
Coverage trend analysis and visualization tools.

This module provides advanced analysis of coverage trends over time,
including regression detection, improvement tracking, and visualization.
"""

import argparse
import json
import matplotlib.pyplot as plt
import pandas as pd
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from coverage_utils import CoverageTrendTracker, CoverageAnalyzer


class CoverageTrendAnalyzer:
    """Advanced coverage trend analysis."""
    
    def __init__(self, db_path: str = "coverage_history.db"):
        """Initialize trend analyzer.
        
        Args:
            db_path: Path to coverage history database
        """
        self.db_path = db_path
        self.tracker = CoverageTrendTracker(db_path)
    
    def get_coverage_statistics(self, days: int = 90) -> Dict:
        """Get comprehensive coverage statistics.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary containing coverage statistics
        """
        conn = sqlite3.connect(self.db_path)
        
        # Get coverage data for specified period
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        query = '''
            SELECT 
                line_coverage, branch_coverage, timestamp,
                lines_covered, lines_valid, branches_covered, branches_valid
            FROM coverage_history 
            WHERE timestamp >= ? 
            ORDER BY timestamp
        '''
        
        df = pd.read_sql_query(query, conn, params=(cutoff_date,))
        conn.close()
        
        if df.empty:
            return {
                'no_data': True,
                'message': f'No coverage data found for last {days} days'
            }
        
        # Calculate statistics
        stats = {
            'period_days': days,
            'total_records': len(df),
            'line_coverage': {
                'current': df['line_coverage'].iloc[-1],
                'min': df['line_coverage'].min(),
                'max': df['line_coverage'].max(),
                'mean': df['line_coverage'].mean(),
                'std': df['line_coverage'].std(),
                'trend': self._calculate_trend(df['line_coverage'])
            },
            'branch_coverage': {
                'current': df['branch_coverage'].iloc[-1],
                'min': df['branch_coverage'].min(),
                'max': df['branch_coverage'].max(),
                'mean': df['branch_coverage'].mean(),
                'std': df['branch_coverage'].std(),
                'trend': self._calculate_trend(df['branch_coverage'])
            },
            'improvement_rate': self._calculate_improvement_rate(df),
            'stability_score': self._calculate_stability_score(df),
            'regression_periods': self._identify_regression_periods(df)
        }
        
        return stats
    
    def _calculate_trend(self, series: pd.Series) -> str:
        """Calculate trend direction (improving, declining, stable)."""
        if len(series) < 2:
            return 'insufficient_data'
        
        # Calculate linear trend
        x = range(len(series))
        slope = pd.Series(x).corr(series)
        
        if slope > 0.1:
            return 'improving'
        elif slope < -0.1:
            return 'declining'
        else:
            return 'stable'
    
    def _calculate_improvement_rate(self, df: pd.DataFrame) -> float:
        """Calculate rate of coverage improvement per day."""
        if len(df) < 2:
            return 0.0
        
        days_diff = (pd.to_datetime(df['timestamp'].iloc[-1]) - 
                    pd.to_datetime(df['timestamp'].iloc[0])).days
        
        if days_diff == 0:
            return 0.0
        
        coverage_diff = df['line_coverage'].iloc[-1] - df['line_coverage'].iloc[0]
        return coverage_diff / days_diff
    
    def _calculate_stability_score(self, df: pd.DataFrame) -> float:
        """Calculate coverage stability score (0-100)."""
        if len(df) < 2:
            return 100.0
        
        # Calculate coefficient of variation
        cv = df['line_coverage'].std() / df['line_coverage'].mean()
        
        # Convert to stability score (lower variation = higher stability)
        stability_score = max(0, 100 - (cv * 100))
        return stability_score
    
    def _identify_regression_periods(self, df: pd.DataFrame) -> List[Dict]:
        """Identify periods of coverage regression."""
        regressions = []
        threshold = 2.0  # 2% regression threshold
        
        for i in range(1, len(df)):
            current = df.iloc[i]
            previous = df.iloc[i-1]
            
            line_diff = previous['line_coverage'] - current['line_coverage']
            branch_diff = previous['branch_coverage'] - current['branch_coverage']
            
            if line_diff > threshold or branch_diff > threshold:
                regressions.append({
                    'timestamp': current['timestamp'],
                    'line_regression': line_diff,
                    'branch_regression': branch_diff,
                    'severity': 'high' if max(line_diff, branch_diff) > 5.0 else 'medium'
                })
        
        return regressions
    
    def generate_trend_report(self, output_file: str = "coverage_trends.html", 
                            days: int = 90) -> str:
        """Generate comprehensive trend analysis report.
        
        Args:
            output_file: Output HTML file path
            days: Number of days to analyze
            
        Returns:
            Path to generated report
        """
        stats = self.get_coverage_statistics(days)
        
        if stats.get('no_data'):
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head><title>Coverage Trends - No Data</title></head>
            <body>
                <h1>Coverage Trend Analysis</h1>
                <p>{stats['message']}</p>
            </body>
            </html>
            """
        else:
            html_content = self._generate_trend_html(stats)
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        return output_file
    
    def _generate_trend_html(self, stats: Dict) -> str:
        """Generate HTML content for trend report."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Coverage Trend Analysis</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .stat-box {{ 
                    display: inline-block; margin: 10px; padding: 15px; 
                    background: #f8f9fa; border-radius: 5px; min-width: 150px; 
                }}
                .improving {{ border-left: 5px solid #28a745; }}
                .declining {{ border-left: 5px solid #dc3545; }}
                .stable {{ border-left: 5px solid #ffc107; }}
                .metric {{ font-size: 1.5em; font-weight: bold; color: #007bff; }}
                .regression {{ background: #f8d7da; padding: 10px; margin: 5px 0; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <h1>📈 Coverage Trend Analysis</h1>
            <p><strong>Analysis Period:</strong> Last {stats['period_days']} days ({stats['total_records']} records)</p>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h2>📊 Current Coverage</h2>
            <div class="stat-box">
                <div>Line Coverage</div>
                <div class="metric">{stats['line_coverage']['current']:.2f}%</div>
            </div>
            <div class="stat-box">
                <div>Branch Coverage</div>
                <div class="metric">{stats['branch_coverage']['current']:.2f}%</div>
            </div>
            <div class="stat-box">
                <div>Improvement Rate</div>
                <div class="metric">{stats['improvement_rate']:.3f}%/day</div>
            </div>
            <div class="stat-box">
                <div>Stability Score</div>
                <div class="metric">{stats['stability_score']:.1f}/100</div>
            </div>
            
            <h2>📈 Trend Analysis</h2>
            <div class="stat-box {stats['line_coverage']['trend']}">
                <div>Line Coverage Trend</div>
                <div>{stats['line_coverage']['trend'].replace('_', ' ').title()}</div>
                <div><small>Range: {stats['line_coverage']['min']:.1f}% - {stats['line_coverage']['max']:.1f}%</small></div>
            </div>
            <div class="stat-box {stats['branch_coverage']['trend']}">
                <div>Branch Coverage Trend</div>
                <div>{stats['branch_coverage']['trend'].replace('_', ' ').title()}</div>
                <div><small>Range: {stats['branch_coverage']['min']:.1f}% - {stats['branch_coverage']['max']:.1f}%</small></div>
            </div>
            
            {self._generate_regression_section(stats['regression_periods'])}
            
            <h2>📋 Recommendations</h2>
            {self._generate_recommendations(stats)}
            
        </body>
        </html>
        """
    
    def _generate_regression_section(self, regressions: List[Dict]) -> str:
        """Generate HTML section for regressions."""
        if not regressions:
            return "<h2>✅ No Significant Regressions Detected</h2>"
        
        regression_html = "<h2>⚠️ Coverage Regressions Detected</h2>"
        
        for regression in regressions:
            regression_html += f"""
            <div class="regression">
                <strong>{regression['timestamp'][:10]}</strong> - 
                Severity: {regression['severity'].title()} |
                Line: -{regression['line_regression']:.2f}% |
                Branch: -{regression['branch_regression']:.2f}%
            </div>
            """
        
        return regression_html
    
    def _generate_recommendations(self, stats: Dict) -> str:
        """Generate recommendations based on trend analysis."""
        recommendations = []
        
        if stats['line_coverage']['current'] < 90:
            recommendations.append("🎯 <strong>Priority:</strong> Increase line coverage to reach 90% target")
        
        if stats['branch_coverage']['current'] < 85:
            recommendations.append("🌿 <strong>Focus:</strong> Improve branch coverage by testing edge cases")
        
        if stats['stability_score'] < 80:
            recommendations.append("📊 <strong>Stability:</strong> Coverage is fluctuating - establish consistent testing practices")
        
        if stats['improvement_rate'] < 0:
            recommendations.append("📈 <strong>Trend:</strong> Coverage is declining - investigate recent changes")
        
        if len(stats['regression_periods']) > 0:
            recommendations.append("🔍 <strong>Investigation:</strong> Recent regressions detected - review failing test coverage")
        
        if not recommendations:
            recommendations.append("✅ <strong>Excellent:</strong> Coverage trends look healthy - maintain current practices")
        
        return "<ul>" + "".join(f"<li>{rec}</li>" for rec in recommendations) + "</ul>"


def generate_coverage_charts(db_path: str = "coverage_history.db", 
                           output_dir: str = "coverage_charts"):
    """Generate coverage trend charts."""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        print("❌ matplotlib not available - install with: pip install matplotlib")
        return False
    
    conn = sqlite3.connect(db_path)
    
    # Get last 90 days of data
    cutoff_date = (datetime.now() - timedelta(days=90)).isoformat()
    
    query = '''
        SELECT timestamp, line_coverage, branch_coverage 
        FROM coverage_history 
        WHERE timestamp >= ? 
        ORDER BY timestamp
    '''
    
    df = pd.read_sql_query(query, conn, params=(cutoff_date,))
    conn.close()
    
    if df.empty:
        print("ℹ️ No coverage data available for charts")
        return False
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Generate trend chart
    plt.figure(figsize=(12, 6))
    
    plt.subplot(1, 2, 1)
    plt.plot(df['timestamp'], df['line_coverage'], label='Line Coverage', marker='o', linewidth=2)
    plt.plot(df['timestamp'], df['branch_coverage'], label='Branch Coverage', marker='s', linewidth=2)
    plt.axhline(y=90, color='r', linestyle='--', alpha=0.7, label='Target (90%)')
    plt.title('Coverage Trends Over Time')
    plt.xlabel('Date')
    plt.ylabel('Coverage (%)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.xticks(rotation=45)
    
    plt.subplot(1, 2, 2)
    plt.hist(df['line_coverage'], bins=20, alpha=0.7, label='Line Coverage', color='blue')
    plt.hist(df['branch_coverage'], bins=20, alpha=0.7, label='Branch Coverage', color='orange')
    plt.axvline(x=90, color='r', linestyle='--', alpha=0.7, label='Target (90%)')
    plt.title('Coverage Distribution')
    plt.xlabel('Coverage (%)')
    plt.ylabel('Frequency')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    chart_path = Path(output_dir) / "coverage_trends.png"
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"📊 Coverage charts generated: {chart_path}")
    return True


def main():
    """Main CLI interface for coverage trend analysis."""
    parser = argparse.ArgumentParser(description="Coverage trend analysis tools")
    parser.add_argument("--db", default="coverage_history.db", help="Coverage database path")
    parser.add_argument("--days", type=int, default=90, help="Number of days to analyze")
    parser.add_argument("--report", help="Generate HTML report to specified file")
    parser.add_argument("--charts", help="Generate charts to specified directory")
    parser.add_argument("--stats", action="store_true", help="Print coverage statistics")
    
    args = parser.parse_args()
    
    analyzer = CoverageTrendAnalyzer(args.db)
    
    if args.stats:
        print("📊 Coverage Statistics")
        print("=" * 50)
        stats = analyzer.get_coverage_statistics(args.days)
        
        if stats.get('no_data'):
            print(stats['message'])
            return 1
        
        print(f"Analysis Period: {stats['period_days']} days")
        print(f"Total Records: {stats['total_records']}")
        print(f"\nLine Coverage:")
        print(f"  Current: {stats['line_coverage']['current']:.2f}%")
        print(f"  Range: {stats['line_coverage']['min']:.2f}% - {stats['line_coverage']['max']:.2f}%")
        print(f"  Mean: {stats['line_coverage']['mean']:.2f}%")
        print(f"  Trend: {stats['line_coverage']['trend']}")
        print(f"\nBranch Coverage:")
        print(f"  Current: {stats['branch_coverage']['current']:.2f}%")
        print(f"  Range: {stats['branch_coverage']['min']:.2f}% - {stats['branch_coverage']['max']:.2f}%")
        print(f"  Mean: {stats['branch_coverage']['mean']:.2f}%")
        print(f"  Trend: {stats['branch_coverage']['trend']}")
        print(f"\nImprovement Rate: {stats['improvement_rate']:.3f}% per day")
        print(f"Stability Score: {stats['stability_score']:.1f}/100")
        print(f"Regressions Detected: {len(stats['regression_periods'])}")
    
    if args.report:
        report_path = analyzer.generate_trend_report(args.report, args.days)
        print(f"📈 Trend report generated: {report_path}")
    
    if args.charts:
        generate_coverage_charts(args.db, args.charts)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())