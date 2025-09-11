#!/usr/bin/env python3
"""
Real-time coverage monitoring dashboard.

This script provides a simple web-based dashboard for monitoring
coverage metrics and trends in real-time.
"""

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from tools.base_utilities import DatabaseManager, HTMLReportGenerator
from tools.reporting_utilities import CoverageMetrics, CoverageReporter
from tools.coverage_utils import CoverageAnalyzer, CoverageTrendTracker


class CoverageDashboard:
    """Simple coverage monitoring dashboard."""
    
    def __init__(self, db_path: str = "coverage_history.db"):
        """Initialize dashboard.
        
        Args:
            db_path: Path to coverage history database
        """
        self.db_path = Path(db_path)
        self.db_manager = DatabaseManager(self.db_path)
        self.html_generator = HTMLReportGenerator()
        self.tracker = CoverageTrendTracker(db_path)
    
    def get_dashboard_data(self) -> Dict:
        """Get current dashboard data.
        
        Returns:
            Dictionary containing dashboard metrics
        """
        # Get latest coverage using database manager
        latest_results = self.db_manager.execute_query('''
            SELECT * FROM coverage_history 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''')
        
        if not latest_results:
            return {'no_data': True}
        
        latest = latest_results[0]
        
        # Get trend data (last 30 days)
        cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
        cursor.execute('''
            SELECT timestamp, line_coverage, branch_coverage 
            FROM coverage_history 
            WHERE timestamp >= ? 
            ORDER BY timestamp
        ''', (cutoff_date,))
        trend_data = cursor.fetchall()
        
        # Get file-level coverage for latest run
        cursor.execute('''
            SELECT filename, package_name, line_coverage, branch_coverage
            FROM file_coverage_history 
            WHERE coverage_id = ?
            ORDER BY line_coverage ASC
        ''', (latest[0],))
        file_coverage = cursor.fetchall()
        
        conn.close()
        
        # Format data
        dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'latest_coverage': {
                'line_coverage': latest[4],
                'branch_coverage': latest[5],
                'lines_covered': latest[6],
                'lines_valid': latest[7],
                'branches_covered': latest[8],
                'branches_valid': latest[9],
                'test_count': latest[11] or 0,
                'commit_hash': latest[2] or 'unknown',
                'branch_name': latest[3] or 'unknown'
            },
            'trend_data': [
                {
                    'timestamp': row[0],
                    'line_coverage': row[1],
                    'branch_coverage': row[2]
                }
                for row in trend_data
            ],
            'low_coverage_files': [
                {
                    'filename': row[0],
                    'package': row[1],
                    'line_coverage': row[2],
                    'branch_coverage': row[3]
                }
                for row in file_coverage[:10]  # Bottom 10 files
                if row[2] < 90.0
            ],
            'statistics': self._calculate_statistics(trend_data)
        }
        
        return dashboard_data
    
    def _calculate_statistics(self, trend_data: List) -> Dict:
        """Calculate trend statistics."""
        if not trend_data:
            return {}
        
        line_coverages = [row[1] for row in trend_data]
        branch_coverages = [row[2] for row in trend_data]
        
        return {
            'line_coverage_avg': sum(line_coverages) / len(line_coverages),
            'branch_coverage_avg': sum(branch_coverages) / len(branch_coverages),
            'line_coverage_min': min(line_coverages),
            'line_coverage_max': max(line_coverages),
            'trend_direction': 'improving' if line_coverages[-1] > line_coverages[0] else 'declining',
            'data_points': len(trend_data)
        }
    
    def generate_dashboard_html(self, output_file: str = "coverage_dashboard.html") -> str:
        """Generate HTML dashboard.
        
        Args:
            output_file: Output HTML file path
            
        Returns:
            Path to generated dashboard
        """
        data = self.get_dashboard_data()
        
        if data.get('no_data'):
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Coverage Dashboard - No Data</title>
                <meta http-equiv="refresh" content="30">
            </head>
            <body>
                <h1>Coverage Dashboard</h1>
                <p>No coverage data available. Run tests with coverage to populate dashboard.</p>
            </body>
            </html>
            """
        else:
            html_content = self._generate_dashboard_html(data)
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        return output_file
    
    def _generate_dashboard_html(self, data: Dict) -> str:
        """Generate HTML content for dashboard."""
        latest = data['latest_coverage']
        stats = data['statistics']
        
        # Generate trend data for chart
        trend_json = json.dumps(data['trend_data'])
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SVG2PPTX Coverage Dashboard</title>
            <meta http-equiv="refresh" content="30">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background: #f8f9fa;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                .header {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .metrics {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 20px;
                }}
                .metric-card {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    text-align: center;
                }}
                .metric-value {{
                    font-size: 2em;
                    font-weight: bold;
                    margin: 10px 0;
                }}
                .metric-label {{
                    color: #666;
                    font-size: 0.9em;
                }}
                .high {{ color: #28a745; }}
                .medium {{ color: #ffc107; }}
                .low {{ color: #dc3545; }}
                .section {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .file-list {{
                    max-height: 300px;
                    overflow-y: auto;
                }}
                .file-item {{
                    display: flex;
                    justify-content: space-between;
                    padding: 8px 0;
                    border-bottom: 1px solid #eee;
                }}
                .status-indicator {{
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    display: inline-block;
                    margin-right: 10px;
                }}
                .status-good {{ background: #28a745; }}
                .status-warn {{ background: #ffc107; }}
                .status-poor {{ background: #dc3545; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 SVG2PPTX Coverage Dashboard</h1>
                    <p>Last updated: {data['timestamp'][:19].replace('T', ' ')}</p>
                    <p>Branch: <strong>{latest['branch_name']}</strong> | Commit: <strong>{latest['commit_hash'][:8]}</strong></p>
                    <div class="status-indicator {'status-good' if latest['line_coverage'] >= 90 else 'status-warn' if latest['line_coverage'] >= 75 else 'status-poor'}"></div>
                    <span>Coverage Status: {'Excellent' if latest['line_coverage'] >= 90 else 'Good' if latest['line_coverage'] >= 75 else 'Needs Improvement'}</span>
                </div>
                
                <div class="metrics">
                    <div class="metric-card">
                        <div class="metric-label">Line Coverage</div>
                        <div class="metric-value {'high' if latest['line_coverage'] >= 90 else 'medium' if latest['line_coverage'] >= 75 else 'low'}">
                            {latest['line_coverage']:.1f}%
                        </div>
                        <div class="metric-label">{latest['lines_covered']}/{latest['lines_valid']} lines</div>
                    </div>
                    
                    <div class="metric-card">
                        <div class="metric-label">Branch Coverage</div>
                        <div class="metric-value {'high' if latest['branch_coverage'] >= 85 else 'medium' if latest['branch_coverage'] >= 70 else 'low'}">
                            {latest['branch_coverage']:.1f}%
                        </div>
                        <div class="metric-label">{latest['branches_covered']}/{latest['branches_valid']} branches</div>
                    </div>
                    
                    <div class="metric-card">
                        <div class="metric-label">Test Count</div>
                        <div class="metric-value">{latest['test_count']}</div>
                        <div class="metric-label">tests executed</div>
                    </div>
                    
                    <div class="metric-card">
                        <div class="metric-label">Trend (30 days)</div>
                        <div class="metric-value {'high' if stats.get('trend_direction') == 'improving' else 'medium'}">
                            {stats.get('trend_direction', 'unknown').title()}
                        </div>
                        <div class="metric-label">{stats.get('data_points', 0)} data points</div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>📈 Coverage Trend (Last 30 Days)</h2>
                    <div id="trendChart" style="height: 300px;">
                        <p>Trend visualization would go here (requires charting library)</p>
                        <p><strong>Average Line Coverage:</strong> {stats.get('line_coverage_avg', 0):.1f}%</p>
                        <p><strong>Range:</strong> {stats.get('line_coverage_min', 0):.1f}% - {stats.get('line_coverage_max', 0):.1f}%</p>
                    </div>
                </div>
                
                {'<div class="section"><h2>⚠️ Files Below Coverage Threshold</h2><div class="file-list">' + ''.join([f'<div class="file-item"><span>{file["filename"]}</span><span>{file["line_coverage"]:.1f}%</span></div>' for file in data['low_coverage_files']]) + '</div></div>' if data['low_coverage_files'] else '<div class="section"><h2>✅ All Files Meet Coverage Threshold</h2><p>Great job! All source files have adequate test coverage.</p></div>'}
                
                <div class="section">
                    <h2>🎯 Coverage Goals</h2>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 5px;">
                        <p><strong>Target Line Coverage:</strong> 90% 
                           {'✅ Achieved' if latest['line_coverage'] >= 90 else f"❌ Need {90 - latest['line_coverage']:.1f}% more"}
                        </p>
                        <p><strong>Target Branch Coverage:</strong> 85% 
                           {'✅ Achieved' if latest['branch_coverage'] >= 85 else f"❌ Need {85 - latest['branch_coverage']:.1f}% more"}
                        </p>
                    </div>
                </div>
                
                <div class="section">
                    <h2>🔄 Quick Actions</h2>
                    <ul>
                        <li><a href="htmlcov/index.html" target="_blank">View Detailed Coverage Report</a></li>
                        <li><a href="coverage_enhanced.html" target="_blank">View Enhanced Analysis</a></li>
                        <li><a href="coverage_trends.html" target="_blank">View Trend Analysis</a></li>
                    </ul>
                </div>
            </div>
            
            <script>
                // Auto-refresh every 30 seconds
                setTimeout(function(){{ window.location.reload(); }}, 30000);
                
                // Simple trend data logging
                const trendData = {trend_json};
                console.log('Coverage trend data:', trendData);
            </script>
        </body>
        </html>
        """


def run_dashboard_server():
    """Run a simple HTTP server for the dashboard."""
    import http.server
    import socketserver
    import threading
    import webbrowser
    from pathlib import Path
    
    PORT = 8080
    
    class DashboardHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/' or self.path == '/dashboard':
                # Generate fresh dashboard
                dashboard = CoverageDashboard()
                dashboard_file = dashboard.generate_dashboard_html()
                self.path = f'/{dashboard_file}'
            
            return super().do_GET()
    
    def update_dashboard():
        """Update dashboard every 30 seconds."""
        while True:
            try:
                dashboard = CoverageDashboard()
                dashboard.generate_dashboard_html()
                time.sleep(30)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Dashboard update error: {e}")
                time.sleep(30)
    
    # Start update thread
    update_thread = threading.Thread(target=update_dashboard, daemon=True)
    update_thread.start()
    
    # Start server
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"🌐 Coverage dashboard server starting on port {PORT}")
        print(f"📊 Dashboard URL: http://localhost:{PORT}")
        
        # Open browser
        webbrowser.open(f'http://localhost:{PORT}')
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Dashboard server stopped")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="Coverage dashboard tools")
    parser.add_argument("--generate", help="Generate static dashboard HTML file")
    parser.add_argument("--serve", action="store_true", help="Start dashboard server")
    parser.add_argument("--db", default="coverage_history.db", help="Coverage database path")
    
    args = parser.parse_args()
    
    dashboard = CoverageDashboard(args.db)
    
    if args.generate:
        output_file = dashboard.generate_dashboard_html(args.generate)
        print(f"📊 Dashboard generated: {output_file}")
    elif args.serve:
        run_dashboard_server()
    else:
        # Default: generate dashboard.html
        output_file = dashboard.generate_dashboard_html()
        print(f"📊 Dashboard generated: {output_file}")
        print("💡 Use --serve to start a live dashboard server")