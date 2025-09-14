#!/usr/bin/env python3
"""
Base utilities for common tool functionality.

This module provides shared base classes and utilities used across multiple
tools in the SVG2PPTX project to reduce code duplication and ensure
consistent patterns.
"""

import json
import sqlite3
import logging
import html as html_module
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class BaseReport:
    """Base class for report data structures."""
    timestamp: datetime
    title: str
    summary: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'title': self.title,
            'summary': self.summary
        }


class DatabaseManager:
    """Shared database management functionality."""
    
    def __init__(self, db_path: Union[str, Path]):
        """Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[sqlite3.Row]:
        """Execute a SELECT query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of query results as Row objects
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
    
    def execute_insert(self, query: str, params: Tuple) -> int:
        """Execute an INSERT query and return row ID.
        
        Args:
            query: SQL INSERT statement
            params: Insert parameters
            
        Returns:
            ID of inserted row
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database.
        
        Args:
            table_name: Name of table to check
            
        Returns:
            True if table exists, False otherwise
        """
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        results = self.execute_query(query, (table_name,))
        return len(results) > 0


class HTMLReportGenerator:
    """Shared HTML report generation functionality."""
    
    @staticmethod
    def generate_html_template(title: str, content: str, css: str = "") -> str:
        """Generate a standard HTML report template.
        
        Args:
            title: Report title
            content: HTML content body
            css: Additional CSS styles
            
        Returns:
            Complete HTML document string
        """
        default_css = """
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
            .header { background: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
            .metric { margin: 10px 0; padding: 10px; background: #f9f9f9; border-left: 4px solid #333; }
            .success { border-left-color: #4CAF50; }
            .warning { border-left-color: #FF9800; }
            .error { border-left-color: #f44336; }
            .table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            .table th, .table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            .table th { background-color: #f2f2f2; }
            .chart { margin: 20px 0; padding: 20px; background: #f9f9f9; border-radius: 5px; }
            .timestamp { color: #666; font-size: 0.9em; }
        </style>
        """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{html_module.escape(title)}</title>
            <meta charset="utf-8">
            {default_css}
            {css}
        </head>
        <body>
            <div class="header">
                <h1>{html_module.escape(title)}</h1>
                <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            {content}
        </body>
        </html>
        """
    
    @staticmethod
    def format_metric_box(label: str, value: str, status: str = "info") -> str:
        """Format a metric display box.
        
        Args:
            label: Metric label
            value: Metric value
            status: Status class (success, warning, error, info)
            
        Returns:
            HTML for metric box
        """
        return f'<div class="metric {status}"><strong>{html_module.escape(label)}:</strong> {html_module.escape(str(value))}</div>'
    
    @staticmethod
    def format_table(headers: List[str], rows: List[List[str]]) -> str:
        """Format data as an HTML table.
        
        Args:
            headers: Table column headers
            rows: Table rows data
            
        Returns:
            HTML table string
        """
        header_html = "".join(f"<th>{html_module.escape(h)}</th>" for h in headers)
        rows_html = ""
        
        for row in rows:
            row_html = "".join(f"<td>{html_module.escape(str(cell))}</td>" for cell in row)
            rows_html += f"<tr>{row_html}</tr>"
        
        return f"""
        <table class="table">
            <thead><tr>{header_html}</tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        """


class BaseValidator(ABC):
    """Abstract base class for validators."""
    
    def __init__(self, name: str):
        """Initialize validator.
        
        Args:
            name: Validator name for logging and reporting
        """
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def validate(self, target: Any) -> Tuple[bool, Dict[str, Any], List[str]]:
        """Perform validation on target.
        
        Args:
            target: Object to validate
            
        Returns:
            Tuple of (is_valid, metadata, issues)
        """
        pass
    
    def log_validation_result(self, target: str, is_valid: bool, issues: List[str]) -> None:
        """Log validation results.
        
        Args:
            target: Name/path of validated target
            is_valid: Whether validation passed
            issues: List of validation issues
        """
        if is_valid:
            self.logger.info(f"Validation passed for {target}")
        else:
            self.logger.warning(f"Validation failed for {target}: {'; '.join(issues)}")


class TrendAnalyzer:
    """Shared trend analysis functionality."""
    
    @staticmethod
    def calculate_trend_direction(values: List[float], window_size: int = 5) -> str:
        """Calculate trend direction from a series of values.
        
        Args:
            values: List of numeric values in chronological order
            window_size: Size of moving window for trend calculation
            
        Returns:
            "improving", "declining", or "stable"
        """
        if len(values) < 2:
            return "stable"
        
        # Use recent window if available
        recent_values = values[-window_size:] if len(values) >= window_size else values
        
        if len(recent_values) < 2:
            return "stable"
        
        # Calculate simple linear trend
        x = list(range(len(recent_values)))
        y = recent_values
        
        # Simple slope calculation
        n = len(x)
        slope = (n * sum(x[i] * y[i] for i in range(n)) - sum(x) * sum(y)) / (n * sum(x[i]**2 for i in range(n)) - sum(x)**2)
        
        threshold = 0.01  # Minimum slope to consider as trend
        
        if slope > threshold:
            return "improving"
        elif slope < -threshold:
            return "declining"
        else:
            return "stable"
    
    @staticmethod
    def calculate_change_rate(current: float, previous: float) -> float:
        """Calculate percentage change rate.
        
        Args:
            current: Current value
            previous: Previous value
            
        Returns:
            Percentage change rate
        """
        if previous == 0:
            return 0.0
        return ((current - previous) / previous) * 100


class FileUtilities:
    """Shared file operation utilities."""
    
    @staticmethod
    def ensure_directory(path: Path) -> None:
        """Ensure directory exists, create if needed.
        
        Args:
            path: Directory path to ensure
        """
        path.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def save_json(data: Dict[str, Any], file_path: Path) -> None:
        """Save data as JSON file.
        
        Args:
            data: Data to save
            file_path: Output file path
        """
        FileUtilities.ensure_directory(file_path.parent)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    @staticmethod
    def load_json(file_path: Path) -> Dict[str, Any]:
        """Load data from JSON file.
        
        Args:
            file_path: JSON file path
            
        Returns:
            Loaded data dictionary
        """
        with open(file_path, 'r') as f:
            return json.load(f)
    
    @staticmethod
    def get_file_timestamp(file_path: Path) -> datetime:
        """Get file modification timestamp.
        
        Args:
            file_path: File path
            
        Returns:
            Modification datetime
        """
        return datetime.fromtimestamp(file_path.stat().st_mtime)


# Convenience imports for common functionality
__all__ = [
    'BaseReport',
    'DatabaseManager', 
    'HTMLReportGenerator',
    'BaseValidator',
    'TrendAnalyzer',
    'FileUtilities'
]