#!/usr/bin/env python3
"""
Coverage utilities for enhanced reporting and trend tracking.

This module provides utilities for analyzing coverage data, generating
enhanced reports, and tracking coverage trends over time.
"""

from lxml import etree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess
import sys

# Use new consolidated utilities
import sys
sys.path.append('../../../')
from tools.development.base_utilities import DatabaseManager, HTMLReportGenerator, FileUtilities
import sys
sys.path.append('../')
from reporting_utilities import CoverageMetrics, CoverageReporter


class CoverageAnalyzer:
    """Analyze and process coverage data."""
    
    def __init__(self, coverage_file: str = "coverage.xml"):
        """Initialize coverage analyzer.
        
        Args:
            coverage_file: Path to coverage XML file
        """
        self.coverage_file = coverage_file
        self.coverage_data = None
        
    def load_coverage_data(self) -> Dict:
        """Load coverage data from XML file.
        
        Returns:
            Dictionary containing coverage metrics
        """
        coverage_path = Path(self.coverage_file)
        if not coverage_path.exists():
            raise FileNotFoundError(f"Coverage file not found: {self.coverage_file}")
        
        tree = ET.parse(self.coverage_file)
        root = tree.getroot()
        
        # Create CoverageMetrics object
        metrics = CoverageMetrics(
            line_rate=float(root.get('line-rate', 0)) * 100,
            branch_rate=float(root.get('branch-rate', 0)) * 100,
            lines_covered=int(root.get('lines-covered', 0)),
            lines_valid=int(root.get('lines-valid', 0)),
            branches_covered=int(root.get('branches-covered', 0)),
            branches_valid=int(root.get('branches-valid', 0))
        )
        
        coverage_data = {
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics,
            'complexity': float(root.get('complexity', 0)),
            'packages': []
        }
        
        # Process package-level coverage
        for package in root.findall('.//package'):
            package_data = {
                'name': package.get('name'),
                'line_rate': float(package.get('line-rate', 0)) * 100,
                'branch_rate': float(package.get('branch-rate', 0)) * 100,
                'complexity': float(package.get('complexity', 0)),
                'classes': []
            }
            
            # Process class-level coverage
            for class_elem in package.findall('.//class'):
                class_data = {
                    'name': class_elem.get('name'),
                    'filename': class_elem.get('filename'),
                    'line_rate': float(class_elem.get('line-rate', 0)) * 100,
                    'branch_rate': float(class_elem.get('branch-rate', 0)) * 100,
                    'complexity': float(class_elem.get('complexity', 0))
                }
                package_data['classes'].append(class_data)
            
            coverage_data['packages'].append(package_data)
        
        self.coverage_data = coverage_data
        return coverage_data
    
    def get_coverage_summary(self) -> Dict:
        """Get coverage summary statistics.
        
        Returns:
            Dictionary containing summary statistics
        """
        if not self.coverage_data:
            self.load_coverage_data()
        
        return {
            'overall_line_coverage': self.coverage_data['line_rate'],
            'overall_branch_coverage': self.coverage_data['branch_rate'],
            'total_lines': self.coverage_data['lines_valid'],
            'covered_lines': self.coverage_data['lines_covered'],
            'uncovered_lines': self.coverage_data['lines_valid'] - self.coverage_data['lines_covered'],
            'total_branches': self.coverage_data['branches_valid'],
            'covered_branches': self.coverage_data['branches_covered'],
            'uncovered_branches': self.coverage_data['branches_valid'] - self.coverage_data['branches_covered'],
            'complexity': self.coverage_data['complexity'],
            'package_count': len(self.coverage_data['packages'])
        }
    
    def get_low_coverage_files(self, threshold: float = 90.0) -> List[Dict]:
        """Get files with coverage below threshold.
        
        Args:
            threshold: Coverage threshold percentage
            
        Returns:
            List of files with low coverage
        """
        if not self.coverage_data:
            self.load_coverage_data()
        
        low_coverage_files = []
        
        for package in self.coverage_data['packages']:
            for class_data in package['classes']:
                if class_data['line_rate'] < threshold:
                    low_coverage_files.append({
                        'filename': class_data['filename'],
                        'line_coverage': class_data['line_rate'],
                        'branch_coverage': class_data['branch_rate'],
                        'package': package['name']
                    })
        
        return sorted(low_coverage_files, key=lambda x: x['line_coverage'])


class CoverageTrendTracker:
    """Track coverage trends over time."""
    
    def __init__(self, db_path: str = "coverage_history.db"):
        """Initialize coverage trend tracker.
        
        Args:
            db_path: Path to SQLite database for storing coverage history
        """
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for coverage history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS coverage_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                commit_hash TEXT,
                branch_name TEXT,
                line_coverage REAL NOT NULL,
                branch_coverage REAL NOT NULL,
                lines_covered INTEGER NOT NULL,
                lines_valid INTEGER NOT NULL,
                branches_covered INTEGER NOT NULL,
                branches_valid INTEGER NOT NULL,
                complexity REAL,
                test_count INTEGER,
                test_duration REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_coverage_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coverage_id INTEGER,
                filename TEXT NOT NULL,
                package_name TEXT,
                line_coverage REAL NOT NULL,
                branch_coverage REAL NOT NULL,
                complexity REAL,
                FOREIGN KEY (coverage_id) REFERENCES coverage_history (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def record_coverage(self, coverage_data: Dict, commit_hash: Optional[str] = None, 
                       branch_name: Optional[str] = None, test_count: Optional[int] = None,
                       test_duration: Optional[float] = None) -> int:
        """Record coverage data in history database.
        
        Args:
            coverage_data: Coverage data dictionary
            commit_hash: Git commit hash
            branch_name: Git branch name
            test_count: Number of tests run
            test_duration: Test execution duration
            
        Returns:
            ID of inserted record
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert main coverage record
        cursor.execute('''
            INSERT INTO coverage_history (
                timestamp, commit_hash, branch_name, line_coverage, branch_coverage,
                lines_covered, lines_valid, branches_covered, branches_valid,
                complexity, test_count, test_duration
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            coverage_data['timestamp'],
            commit_hash,
            branch_name,
            coverage_data['line_rate'],
            coverage_data['branch_rate'],
            coverage_data['lines_covered'],
            coverage_data['lines_valid'],
            coverage_data['branches_covered'],
            coverage_data['branches_valid'],
            coverage_data['complexity'],
            test_count,
            test_duration
        ))
        
        coverage_id = cursor.lastrowid
        
        # Insert file-level coverage records
        for package in coverage_data['packages']:
            for class_data in package['classes']:
                cursor.execute('''
                    INSERT INTO file_coverage_history (
                        coverage_id, filename, package_name, line_coverage,
                        branch_coverage, complexity
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    coverage_id,
                    class_data['filename'],
                    package['name'],
                    class_data['line_rate'],
                    class_data['branch_rate'],
                    class_data['complexity']
                ))
        
        conn.commit()
        conn.close()
        
        return coverage_id
    
    def get_coverage_trend(self, days: int = 30) -> List[Dict]:
        """Get coverage trend over specified number of days.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            List of coverage records
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT timestamp, line_coverage, branch_coverage, commit_hash, branch_name
            FROM coverage_history
            WHERE timestamp >= ?
            ORDER BY timestamp
        ''', (cutoff_date,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'timestamp': row[0],
                'line_coverage': row[1],
                'branch_coverage': row[2],
                'commit_hash': row[3],
                'branch_name': row[4]
            }
            for row in rows
        ]
    
    def detect_coverage_regression(self, threshold: float = 5.0) -> Optional[Dict]:
        """Detect significant coverage regression.
        
        Args:
            threshold: Regression threshold in percentage points
            
        Returns:
            Regression information if detected, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get last two coverage records
        cursor.execute('''
            SELECT timestamp, line_coverage, branch_coverage
            FROM coverage_history
            ORDER BY timestamp DESC
            LIMIT 2
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        if len(rows) < 2:
            return None
        
        current = rows[0]
        previous = rows[1]
        
        line_regression = previous[1] - current[1]
        branch_regression = previous[2] - current[2]
        
        if line_regression > threshold or branch_regression > threshold:
            return {
                'detected': True,
                'line_regression': line_regression,
                'branch_regression': branch_regression,
                'current_coverage': {'line': current[1], 'branch': current[2]},
                'previous_coverage': {'line': previous[1], 'branch': previous[2]},
                'current_timestamp': current[0],
                'previous_timestamp': previous[0]
            }
        
        return None


class CoverageReporter:
    """Generate enhanced coverage reports."""
    
    def __init__(self, analyzer: CoverageAnalyzer, tracker: CoverageTrendTracker):
        """Initialize coverage reporter.
        
        Args:
            analyzer: Coverage analyzer instance
            tracker: Coverage trend tracker instance
        """
        self.analyzer = analyzer
        self.tracker = tracker
    
    def generate_enhanced_report(self, output_file: str = "coverage_report.html") -> str:
        """Generate enhanced HTML coverage report.
        
        Args:
            output_file: Output file path
            
        Returns:
            Path to generated report
        """
        summary = self.analyzer.get_coverage_summary()
        low_coverage_files = self.analyzer.get_low_coverage_files()
        trend_data = self.tracker.get_coverage_trend()
        regression = self.tracker.detect_coverage_regression()
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SVG2PPTX Coverage Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background: white; border-radius: 3px; }}
                .high {{ background: #d4edda; color: #155724; }}
                .medium {{ background: #fff3cd; color: #856404; }}
                .low {{ background: #f8d7da; color: #721c24; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>SVG2PPTX Coverage Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="summary">
                <h2>Coverage Summary</h2>
                <div class="metric {'high' if summary['overall_line_coverage'] >= 90 else 'medium' if summary['overall_line_coverage'] >= 75 else 'low'}">
                    <strong>Line Coverage:</strong> {summary['overall_line_coverage']:.2f}%
                </div>
                <div class="metric {'high' if summary['overall_branch_coverage'] >= 85 else 'medium' if summary['overall_branch_coverage'] >= 70 else 'low'}">
                    <strong>Branch Coverage:</strong> {summary['overall_branch_coverage']:.2f}%
                </div>
                <div class="metric">
                    <strong>Lines:</strong> {summary['covered_lines']}/{summary['total_lines']}
                </div>
                <div class="metric">
                    <strong>Branches:</strong> {summary['covered_branches']}/{summary['total_branches']}
                </div>
            </div>
            
            {'<div style="background: #f8d7da; color: #721c24; padding: 15px; margin: 20px 0; border-radius: 5px;"><h3>Coverage Regression Detected!</h3><p>Line coverage decreased by {regression["line_regression"]:.2f}% and branch coverage by {regression["branch_regression"]:.2f}%</p></div>' if regression else ''}
            
            {self._generate_low_coverage_table(low_coverage_files)}
            
            {self._generate_trend_chart(trend_data)}
            
        </body>
        </html>
        """
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        return output_file
    
    def _generate_low_coverage_table(self, low_coverage_files: List[Dict]) -> str:
        """Generate table of files with low coverage."""
        if not low_coverage_files:
            return "<h2>All files meet coverage threshold! ✅</h2>"
        
        table_rows = ""
        for file_data in low_coverage_files:
            table_rows += f"""
            <tr>
                <td>{file_data['filename']}</td>
                <td>{file_data['package']}</td>
                <td>{file_data['line_coverage']:.2f}%</td>
                <td>{file_data['branch_coverage']:.2f}%</td>
            </tr>
            """
        
        return f"""
        <h2>Files Below Coverage Threshold</h2>
        <table>
            <tr>
                <th>File</th>
                <th>Package</th>
                <th>Line Coverage</th>
                <th>Branch Coverage</th>
            </tr>
            {table_rows}
        </table>
        """
    
    def _generate_trend_chart(self, trend_data: List[Dict]) -> str:
        """Generate simple trend visualization."""
        if not trend_data:
            return "<h2>No trend data available</h2>"
        
        # Simple text-based trend for now
        trend_text = "<h2>Coverage Trend (Last 30 Days)</h2><ul>"
        for record in trend_data[-10:]:  # Last 10 records
            trend_text += f"<li>{record['timestamp'][:10]}: Line {record['line_coverage']:.1f}%, Branch {record['branch_coverage']:.1f}%</li>"
        trend_text += "</ul>"
        
        return trend_text


def run_coverage_analysis():
    """Run complete coverage analysis and reporting."""
    print("🔍 Running coverage analysis...")
    
    try:
        # Run tests with coverage
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            '--cov=src',
            '--cov-report=xml:coverage.xml',
            '--cov-report=html:htmlcov',
            '--cov-report=term-missing'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Tests failed:\n{result.stdout}\n{result.stderr}")
            return False
        
        # Analyze coverage data
        analyzer = CoverageAnalyzer()
        coverage_data = analyzer.load_coverage_data()
        
        # Track coverage trends
        tracker = CoverageTrendTracker()
        
        # Get git information if available
        commit_hash = None
        branch_name = None
        try:
            commit_result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                         capture_output=True, text=True)
            if commit_result.returncode == 0:
                commit_hash = commit_result.stdout.strip()
            
            branch_result = subprocess.run(['git', 'branch', '--show-current'], 
                                         capture_output=True, text=True)
            if branch_result.returncode == 0:
                branch_name = branch_result.stdout.strip()
        except FileNotFoundError:
            pass
        
        # Record coverage
        coverage_id = tracker.record_coverage(
            coverage_data, 
            commit_hash=commit_hash,
            branch_name=branch_name
        )
        
        # Generate enhanced report
        reporter = CoverageReporter(analyzer, tracker)
        report_path = reporter.generate_enhanced_report("coverage_enhanced.html")
        
        # Print summary
        summary = analyzer.get_coverage_summary()
        print(f"✅ Coverage Analysis Complete!")
        print(f"📊 Line Coverage: {summary['overall_line_coverage']:.2f}%")
        print(f"🌿 Branch Coverage: {summary['overall_branch_coverage']:.2f}%")
        print(f"📝 Enhanced report: {report_path}")
        
        # Check for regressions
        regression = tracker.detect_coverage_regression()
        if regression:
            print(f"⚠️  Coverage regression detected!")
            print(f"   Line coverage: -{regression['line_regression']:.2f}%")
            print(f"   Branch coverage: -{regression['branch_regression']:.2f}%")
        
        return summary['overall_line_coverage'] >= 90.0
        
    except Exception as e:
        print(f"❌ Coverage analysis failed: {e}")
        return False


if __name__ == '__main__':
    success = run_coverage_analysis()
    sys.exit(0 if success else 1)