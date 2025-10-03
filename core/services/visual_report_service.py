#!/usr/bin/env python3
"""
Visual Report Service for SVG2PPTX Clean Slate Architecture.

Provides visual comparison and reporting functionality for evaluating
SVG to PowerPoint conversion quality and fidelity.
"""

import os
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import json
import tempfile

try:
    from PIL import Image, ImageChops
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class VisualReportService:
    """
    Service for generating visual comparison reports.

    Integrates with the clean slate architecture to provide comprehensive
    visual analysis and reporting capabilities.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize visual report service."""
        self.output_dir = output_dir or Path.cwd() / "visual_reports"
        self.output_dir.mkdir(exist_ok=True)
        self.comparisons: List[Dict[str, Any]] = []

    def add_comparison(self,
                      svg_file: Path,
                      pptx_file: Path,
                      metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a comparison to the report.

        Args:
            svg_file: Path to SVG input file
            pptx_file: Path to PowerPoint output file
            metadata: Additional metadata about the conversion

        Returns:
            Comparison ID for reference
        """
        comparison_id = f"comparison_{len(self.comparisons) + 1}"

        comparison = {
            "id": comparison_id,
            "svg_file": str(svg_file),
            "pptx_file": str(pptx_file),
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
            "conversion_success": pptx_file.exists() if pptx_file else False
        }

        self.comparisons.append(comparison)
        return comparison_id

    def generate_report(self, report_name: str = "visual_comparison") -> Path:
        """
        Generate HTML report with all comparisons.

        Args:
            report_name: Name for the report file

        Returns:
            Path to generated HTML report
        """
        report_path = self.output_dir / f"{report_name}.html"

        # Calculate summary statistics
        total_comparisons = len(self.comparisons)
        successful_conversions = len([c for c in self.comparisons if c.get("conversion_success", False)])

        summary = {
            "total_comparisons": total_comparisons,
            "successful_conversions": successful_conversions,
            "success_rate": round((successful_conversions / total_comparisons * 100), 2) if total_comparisons > 0 else 0,
            "generation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Generate HTML content
        html_content = self._get_html_template().format(
            title=f"SVG2PPTX Conversion Report - {report_name}",
            summary=json.dumps(summary, indent=2),
            comparisons=json.dumps(self.comparisons, indent=2)
        )

        # Write report file
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return report_path

    def open_report(self, report_path: Path) -> bool:
        """
        Open the generated report in the default browser.

        Returns:
            True if successfully opened, False otherwise
        """
        try:
            webbrowser.open(f"file://{report_path.absolute()}")
            return True
        except Exception:
            return False

    def _get_html_template(self) -> str:
        """Get HTML template for the report."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; margin: 0; background: #f8fafc; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 0 1rem; }}
        .title {{ font-size: 2rem; margin: 0; text-align: center; }}
        .summary {{ background: white; border-radius: 8px; padding: 1.5rem; margin: 2rem 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem; }}
        .stat {{ text-align: center; padding: 1rem; background: #f1f5f9; border-radius: 6px; }}
        .stat-value {{ font-size: 2rem; font-weight: bold; color: #1e293b; }}
        .stat-label {{ color: #64748b; font-size: 0.9rem; margin-top: 0.5rem; }}
        .comparison {{ background: white; border-radius: 8px; padding: 1.5rem; margin: 1rem 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .comparison-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }}
        .comparison-title {{ font-size: 1.1rem; font-weight: 600; color: #1e293b; }}
        .status {{ padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.8rem; font-weight: 600; }}
        .status-success {{ background: #dcfce7; color: #166534; }}
        .status-failed {{ background: #fecaca; color: #991b1b; }}
        .metadata {{ margin-top: 1rem; padding: 1rem; background: #f8fafc; border-radius: 6px; font-family: monospace; font-size: 0.85rem; }}
        .footer {{ text-align: center; padding: 2rem; color: #64748b; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1 class="title">SVG2PPTX Conversion Report</h1>
        </div>
    </div>

    <div class="container">
        <div class="summary">
            <h2>Summary Statistics</h2>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value" id="total-comparisons">-</div>
                    <div class="stat-label">Total Files</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="successful-conversions">-</div>
                    <div class="stat-label">Successful Conversions</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="success-rate">-</div>
                    <div class="stat-label">Success Rate</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="generation-time">-</div>
                    <div class="stat-label">Generated</div>
                </div>
            </div>
        </div>

        <div id="comparisons-container">
            <!-- Comparisons will be populated by JavaScript -->
        </div>
    </div>

    <div class="footer">
        <p>Generated by SVG2PPTX Clean Slate Architecture</p>
    </div>

    <script>
        const summary = {summary};
        const comparisons = {comparisons};

        // Populate summary
        document.getElementById('total-comparisons').textContent = summary.total_comparisons;
        document.getElementById('successful-conversions').textContent = summary.successful_conversions;
        document.getElementById('success-rate').textContent = summary.success_rate + '%';
        document.getElementById('generation-time').textContent = summary.generation_time;

        // Generate comparison HTML
        const container = document.getElementById('comparisons-container');

        comparisons.forEach((comp, index) => {{
            const statusClass = comp.conversion_success ? 'status-success' : 'status-failed';
            const statusText = comp.conversion_success ? 'Success' : 'Failed';

            const compHtml = `
                <div class="comparison">
                    <div class="comparison-header">
                        <div class="comparison-title">${{comp.svg_file.split('/').pop() || comp.svg_file}}</div>
                        <span class="status ${{statusClass}}">${{statusText}}</span>
                    </div>
                    <div><strong>SVG:</strong> ${{comp.svg_file}}</div>
                    <div><strong>PPTX:</strong> ${{comp.pptx_file}}</div>
                    <div><strong>Timestamp:</strong> ${{new Date(comp.timestamp).toLocaleString()}}</div>
                    ${{Object.keys(comp.metadata).length > 0 ?
                        `<div class="metadata">${{JSON.stringify(comp.metadata, null, 2)}}</div>` : ''
                    }}
                </div>
            `;

            container.innerHTML += compHtml;
        }});
    </script>
</body>
</html>'''