#!/usr/bin/env python3
"""
Reporting utilities for SVG2PPTX tools.

This module provides specialized reporting classes that extend the base
reporting framework for accuracy, coverage, and performance reporting.
"""

import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

import sys
sys.path.append('../../../')
from tools.development.base_utilities import (
    BaseReport, DatabaseManager, HTMLReportGenerator, 
    TrendAnalyzer, FileUtilities
)


@dataclass
class AccuracyMetrics:
    """Accuracy measurement metrics."""
    structural_accuracy: float
    content_accuracy: float
    visual_fidelity: float
    layout_preservation: float
    overall_score: float
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'AccuracyMetrics':
        """Create metrics from dictionary data."""
        return cls(
            structural_accuracy=data.get('structural_accuracy', 0.0),
            content_accuracy=data.get('content_accuracy', 0.0),
            visual_fidelity=data.get('visual_fidelity', 0.0),
            layout_preservation=data.get('layout_preservation', 0.0),
            overall_score=data.get('overall_score', 0.0)
        )
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'structural_accuracy': self.structural_accuracy,
            'content_accuracy': self.content_accuracy,
            'visual_fidelity': self.visual_fidelity,
            'layout_preservation': self.layout_preservation,
            'overall_score': self.overall_score
        }


@dataclass
class CoverageMetrics:
    """Coverage measurement metrics."""
    line_rate: float
    branch_rate: float
    lines_covered: int
    lines_valid: int
    branches_covered: int
    branches_valid: int
    
    @property
    def coverage_percentage(self) -> float:
        """Calculate overall coverage percentage."""
        return (self.line_rate + self.branch_rate) / 2
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CoverageMetrics':
        """Create metrics from dictionary data."""
        return cls(
            line_rate=float(data.get('line_rate', 0)),
            branch_rate=float(data.get('branch_rate', 0)),
            lines_covered=int(data.get('lines_covered', 0)),
            lines_valid=int(data.get('lines_valid', 0)),
            branches_covered=int(data.get('branches_covered', 0)),
            branches_valid=int(data.get('branches_valid', 0))
        )


class AccuracyReporter:
    """Enhanced accuracy reporting with trend analysis."""
    
    def __init__(self, database_path: Path):
        """Initialize reporter with database connection."""
        self.database_path = database_path
        self.db_manager = DatabaseManager(database_path)
        self.html_generator = HTMLReportGenerator()
        self._ensure_tables()
    
    def _ensure_tables(self) -> None:
        """Ensure required database tables exist."""
        if not self.db_manager.table_exists('accuracy_measurements'):
            self.db_manager.execute_insert('''
                CREATE TABLE accuracy_measurements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    test_file TEXT NOT NULL,
                    structural_accuracy REAL,
                    content_accuracy REAL,
                    visual_fidelity REAL,
                    layout_preservation REAL,
                    overall_score REAL,
                    metadata TEXT
                )
            ''', ())
    
    def record_measurement(self, test_file: str, metrics: AccuracyMetrics, 
                          metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record accuracy measurement in database."""
        import json
        
        self.db_manager.execute_insert('''
            INSERT INTO accuracy_measurements 
            (timestamp, test_file, structural_accuracy, content_accuracy, 
             visual_fidelity, layout_preservation, overall_score, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            test_file,
            metrics.structural_accuracy,
            metrics.content_accuracy, 
            metrics.visual_fidelity,
            metrics.layout_preservation,
            metrics.overall_score,
            json.dumps(metadata or {})
        ))
    
    def generate_accuracy_report(self, output_path: Path, days: int = 30) -> str:
        """Generate comprehensive accuracy report."""
        # Get recent measurements
        cutoff_date = datetime.now() - timedelta(days=days)
        measurements = self.db_manager.execute_query('''
            SELECT * FROM accuracy_measurements 
            WHERE timestamp >= ? 
            ORDER BY timestamp DESC
        ''', (cutoff_date.isoformat(),))
        
        if not measurements:
            return self._generate_no_data_report(output_path)
        
        # Calculate summary statistics
        metrics_data = [AccuracyMetrics.from_dict(dict(m)) for m in measurements]
        summary_stats = self._calculate_summary_stats(metrics_data)
        
        # Generate trend analysis
        trend_data = self._analyze_trends(measurements)
        
        # Generate HTML content
        content = self._generate_accuracy_html_content(summary_stats, trend_data, measurements)
        
        # Save report
        html_content = self.html_generator.generate_html_template(
            f"Accuracy Report - Last {days} Days", content
        )
        
        FileUtilities.ensure_directory(output_path.parent)
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        return str(output_path)
    
    def _calculate_summary_stats(self, metrics: List[AccuracyMetrics]) -> Dict[str, float]:
        """Calculate summary statistics for metrics."""
        return {
            'avg_structural': statistics.mean(m.structural_accuracy for m in metrics),
            'avg_content': statistics.mean(m.content_accuracy for m in metrics),
            'avg_visual': statistics.mean(m.visual_fidelity for m in metrics),
            'avg_layout': statistics.mean(m.layout_preservation for m in metrics),
            'avg_overall': statistics.mean(m.overall_score for m in metrics),
            'total_measurements': len(metrics)
        }
    
    def _analyze_trends(self, measurements: List[Any]) -> Dict[str, str]:
        """Analyze accuracy trends over time."""
        if len(measurements) < 2:
            return {'overall': 'insufficient_data'}
        
        overall_scores = [float(m['overall_score']) for m in measurements]
        overall_trend = TrendAnalyzer.calculate_trend_direction(overall_scores)
        
        return {
            'overall': overall_trend,
            'structural': TrendAnalyzer.calculate_trend_direction(
                [float(m['structural_accuracy']) for m in measurements]
            ),
            'content': TrendAnalyzer.calculate_trend_direction(
                [float(m['content_accuracy']) for m in measurements]
            ),
            'visual': TrendAnalyzer.calculate_trend_direction(
                [float(m['visual_fidelity']) for m in measurements]
            )
        }
    
    def _generate_accuracy_html_content(self, stats: Dict[str, float], 
                                       trends: Dict[str, str], 
                                       measurements: List[Any]) -> str:
        """Generate HTML content for accuracy report."""
        content = "<h2>Accuracy Summary</h2>"
        
        # Summary metrics
        content += self.html_generator.format_metric_box(
            "Average Overall Score", f"{stats['avg_overall']:.2f}%", "info"
        )
        content += self.html_generator.format_metric_box(
            "Total Measurements", str(stats['total_measurements']), "info"
        )
        
        # Detailed metrics table
        metric_rows = [
            ["Structural Accuracy", f"{stats['avg_structural']:.2f}%", trends['structural']],
            ["Content Accuracy", f"{stats['avg_content']:.2f}%", trends['content']],
            ["Visual Fidelity", f"{stats['avg_visual']:.2f}%", trends['visual']],
            ["Layout Preservation", f"{stats['avg_layout']:.2f}%", trends.get('layout', 'stable')]
        ]
        
        content += "<h3>Detailed Metrics</h3>"
        content += self.html_generator.format_table(
            ["Metric", "Average", "Trend"], metric_rows
        )
        
        # Recent measurements
        if measurements:
            content += "<h3>Recent Measurements</h3>"
            recent_rows = []
            for m in measurements[:10]:  # Last 10 measurements
                recent_rows.append([
                    m['test_file'],
                    f"{m['overall_score']:.2f}%",
                    m['timestamp'][:19]  # Trim timestamp
                ])
            
            content += self.html_generator.format_table(
                ["Test File", "Overall Score", "Timestamp"], recent_rows
            )
        
        return content
    
    def _generate_no_data_report(self, output_path: Path) -> str:
        """Generate report when no data is available."""
        content = self.html_generator.format_metric_box(
            "Status", "No accuracy measurements found", "warning"
        )
        
        html_content = self.html_generator.generate_html_template(
            "Accuracy Report - No Data", content
        )
        
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        return str(output_path)


class CoverageReporter:
    """Enhanced coverage reporting with trend analysis."""
    
    def __init__(self, database_path: Path):
        """Initialize coverage reporter."""
        self.database_path = database_path
        self.db_manager = DatabaseManager(database_path)
        self.html_generator = HTMLReportGenerator()
        self._ensure_tables()
    
    def _ensure_tables(self) -> None:
        """Ensure required database tables exist."""
        if not self.db_manager.table_exists('coverage_history'):
            self.db_manager.execute_insert('''
                CREATE TABLE coverage_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    line_rate REAL NOT NULL,
                    branch_rate REAL NOT NULL,
                    lines_covered INTEGER NOT NULL,
                    lines_valid INTEGER NOT NULL,
                    branches_covered INTEGER NOT NULL,
                    branches_valid INTEGER NOT NULL,
                    metadata TEXT
                )
            ''', ())
    
    def record_coverage(self, metrics: CoverageMetrics, 
                       metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record coverage measurement in database."""
        import json
        
        self.db_manager.execute_insert('''
            INSERT INTO coverage_history 
            (timestamp, line_rate, branch_rate, lines_covered, lines_valid,
             branches_covered, branches_valid, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            metrics.line_rate,
            metrics.branch_rate,
            metrics.lines_covered,
            metrics.lines_valid,
            metrics.branches_covered,
            metrics.branches_valid,
            json.dumps(metadata or {})
        ))
    
    def generate_coverage_report(self, output_path: Path, days: int = 30) -> str:
        """Generate comprehensive coverage report."""
        # Get recent coverage data
        cutoff_date = datetime.now() - timedelta(days=days)
        coverage_data = self.db_manager.execute_query('''
            SELECT * FROM coverage_history 
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        ''', (cutoff_date.isoformat(),))
        
        if not coverage_data:
            return self._generate_no_data_report(output_path)
        
        # Calculate trends
        line_rates = [float(row['line_rate']) for row in coverage_data]
        branch_rates = [float(row['branch_rate']) for row in coverage_data]
        
        trend_analysis = {
            'line_coverage': TrendAnalyzer.calculate_trend_direction(line_rates),
            'branch_coverage': TrendAnalyzer.calculate_trend_direction(branch_rates)
        }
        
        # Generate HTML content
        content = self._generate_coverage_html_content(coverage_data, trend_analysis)
        
        # Save report
        html_content = self.html_generator.generate_html_template(
            f"Coverage Report - Last {days} Days", content
        )
        
        FileUtilities.ensure_directory(output_path.parent)
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        return str(output_path)
    
    def _generate_coverage_html_content(self, data: List[Any], 
                                       trends: Dict[str, str]) -> str:
        """Generate HTML content for coverage report."""
        if not data:
            return "<p>No coverage data available.</p>"
        
        latest = data[0]
        content = "<h2>Current Coverage</h2>"
        
        # Current metrics
        content += self.html_generator.format_metric_box(
            "Line Coverage", f"{latest['line_rate']:.1f}%", 
            "success" if latest['line_rate'] >= 80 else "warning"
        )
        content += self.html_generator.format_metric_box(
            "Branch Coverage", f"{latest['branch_rate']:.1f}%",
            "success" if latest['branch_rate'] >= 70 else "warning"
        )
        
        # Trend analysis
        content += "<h3>Trends</h3>"
        trend_rows = [
            ["Line Coverage", f"{latest['line_rate']:.1f}%", trends['line_coverage']],
            ["Branch Coverage", f"{latest['branch_rate']:.1f}%", trends['branch_coverage']]
        ]
        content += self.html_generator.format_table(
            ["Metric", "Current", "Trend"], trend_rows
        )
        
        # Historical data
        if len(data) > 1:
            content += "<h3>Recent History</h3>"
            history_rows = []
            for row in data[:10]:
                history_rows.append([
                    row['timestamp'][:19],
                    f"{row['line_rate']:.1f}%",
                    f"{row['branch_rate']:.1f}%"
                ])
            
            content += self.html_generator.format_table(
                ["Timestamp", "Line Coverage", "Branch Coverage"], history_rows
            )
        
        return content
    
    def _generate_no_data_report(self, output_path: Path) -> str:
        """Generate report when no coverage data is available."""
        content = self.html_generator.format_metric_box(
            "Status", "No coverage data found", "warning"
        )
        
        html_content = self.html_generator.generate_html_template(
            "Coverage Report - No Data", content
        )
        
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        return str(output_path)


class PerformanceReporter:
    """Performance metrics reporting."""
    
    def __init__(self, database_path: Path):
        """Initialize performance reporter."""
        self.database_path = database_path
        self.db_manager = DatabaseManager(database_path)
        self.html_generator = HTMLReportGenerator()
    
    def generate_performance_summary(self, metrics: Dict[str, Any]) -> str:
        """Generate performance summary HTML."""
        content = "<h2>Performance Summary</h2>"
        
        if 'conversion_time' in metrics:
            content += self.html_generator.format_metric_box(
                "Conversion Time", f"{metrics['conversion_time']:.3f}s", "info"
            )
        
        if 'memory_usage' in metrics:
            content += self.html_generator.format_metric_box(
                "Memory Usage", f"{metrics['memory_usage']:.1f} MB", "info"
            )
        
        if 'file_size_reduction' in metrics:
            status = "success" if metrics['file_size_reduction'] > 0 else "info"
            content += self.html_generator.format_metric_box(
                "File Size Change", f"{metrics['file_size_reduction']:+.1f}%", status
            )
        
        return content


# Convenience imports
__all__ = [
    'AccuracyMetrics',
    'CoverageMetrics', 
    'AccuracyReporter',
    'CoverageReporter',
    'PerformanceReporter'
]