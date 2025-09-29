#!/usr/bin/env python3
"""
Visual Comparison Generator for SVG2PPTX

This script creates actual visual comparisons:
1. SVG rendered in browser (left side)
2. PPTX opened in LibreOffice headless screenshot (right side)
3. Comprehensive debugging of the conversion pipeline
4. Side-by-side HTML report with actual visuals
"""

import sys
import json
import time
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.svg2pptx import convert_svg_to_pptx
from core.paths import create_path_system


class VisualComparisonGenerator:
    """Generates visual comparisons with debugging info."""

    def __init__(self, output_dir=None):
        self.output_dir = Path(output_dir) if output_dir else Path(__file__).parent
        self.debug_info = []
        self.conversion_stats = {}

    def log_debug(self, message, category="INFO"):
        """Log debug information with timestamp."""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        debug_entry = {
            "timestamp": timestamp,
            "category": category,
            "message": message
        }
        self.debug_info.append(debug_entry)
        print(f"[{timestamp}] {category}: {message}")

    def test_path_system_components(self):
        """Test PathSystem components with detailed debugging."""
        self.log_debug("Testing PathSystem components", "DEBUG")

        try:
            # Test component creation
            path_system = create_path_system(800, 600, (0, 0, 800, 600))
            self.log_debug("✅ PathSystem created successfully", "SUCCESS")

            # Test various path types
            test_paths = [
                ("Simple line", "M 100 100 L 200 200"),
                ("Cubic curve", "M 100 100 C 100 50 200 50 200 100"),
                ("Quadratic curve", "M 100 100 Q 150 50 200 100"),
                ("Arc command", "M 100 100 A 50 25 0 0 1 200 100"),
                ("Complex mixed", "M 100 100 C 100 50 200 50 200 100 A 50 25 0 0 1 300 100 Z")
            ]

            for name, path_data in test_paths:
                try:
                    start_time = time.time()
                    result = path_system.process_path(path_data)
                    processing_time = (time.time() - start_time) * 1000

                    self.log_debug(f"✅ {name}: {len(result.commands)} commands, "
                                 f"{len(result.path_xml)} bytes XML, "
                                 f"{processing_time:.1f}ms", "SUCCESS")

                except Exception as e:
                    self.log_debug(f"❌ {name} failed: {e}", "ERROR")

            return True

        except Exception as e:
            self.log_debug(f"❌ PathSystem test failed: {e}", "ERROR")
            return False

    def convert_svg_with_debugging(self, svg_file, output_file):
        """Convert SVG to PPTX with comprehensive debugging."""
        self.log_debug(f"Starting conversion: {svg_file} → {output_file}", "CONVERSION")

        try:
            # Read and analyze SVG
            with open(svg_file, 'r') as f:
                svg_content = f.read()

            self.log_debug(f"📄 SVG size: {len(svg_content):,} bytes", "INFO")

            # Count different elements
            path_count = svg_content.count('<path')
            text_count = svg_content.count('<text')
            rect_count = svg_content.count('<rect')
            circle_count = svg_content.count('<circle')

            self.log_debug(f"📊 Elements: {path_count} paths, {text_count} text, "
                         f"{rect_count} rects, {circle_count} circles", "INFO")

            # Perform conversion with timing
            start_time = time.time()
            result = convert_svg_to_pptx(str(svg_file), str(output_file))
            conversion_time = time.time() - start_time

            # Get output stats
            output_size = Path(output_file).stat().st_size

            self.conversion_stats = {
                "input_size": len(svg_content),
                "output_size": output_size,
                "conversion_time": conversion_time,
                "path_count": path_count,
                "text_count": text_count,
                "processing_rate": path_count / conversion_time if conversion_time > 0 else 0,
                "compression_ratio": output_size / len(svg_content)
            }

            self.log_debug(f"✅ Conversion completed in {conversion_time:.3f}s", "SUCCESS")
            self.log_debug(f"📁 Output: {output_size:,} bytes "
                         f"({self.conversion_stats['compression_ratio']:.1f}x ratio)", "INFO")

            return True

        except Exception as e:
            self.log_debug(f"❌ Conversion failed: {e}", "ERROR")
            import traceback
            for line in traceback.format_exc().split('\n'):
                if line.strip():
                    self.log_debug(line.strip(), "ERROR")
            return False

    def capture_libreoffice_screenshot(self, pptx_file):
        """Capture screenshot of PPTX using LibreOffice headless."""
        self.log_debug("Capturing LibreOffice screenshot", "SCREENSHOT")

        try:
            # Check if LibreOffice is available
            soffice_paths = [
                "/Applications/LibreOffice.app/Contents/MacOS/soffice",
                "/usr/bin/libreoffice",
                "/opt/libreoffice/bin/soffice",
                "soffice"
            ]

            soffice_cmd = None
            for path in soffice_paths:
                if Path(path).exists() or shutil.which(path if not path.startswith('/') else None):
                    soffice_cmd = path
                    break

            if not soffice_cmd:
                self.log_debug("❌ LibreOffice not found", "ERROR")
                return None

            self.log_debug(f"📋 Using LibreOffice: {soffice_cmd}", "INFO")

            # Create temp directory for screenshot
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Output PNG path
                screenshot_name = f"{Path(pptx_file).stem}_screenshot.png"
                screenshot_path = self.output_dir / screenshot_name

                # Convert PPTX to PNG using LibreOffice headless
                cmd = [
                    soffice_cmd,
                    "--headless",
                    "--convert-to", "png",
                    "--outdir", str(temp_path),
                    str(pptx_file)
                ]

                self.log_debug(f"🖼️  Running: {' '.join(cmd)}", "DEBUG")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    # Look for generated PNG
                    png_files = list(temp_path.glob("*.png"))
                    if png_files:
                        generated_png = png_files[0]
                        shutil.copy2(generated_png, screenshot_path)
                        self.log_debug(f"✅ Screenshot saved: {screenshot_path}", "SUCCESS")
                        return screenshot_path
                    else:
                        self.log_debug("❌ No PNG generated", "ERROR")
                else:
                    self.log_debug(f"❌ LibreOffice failed: {result.stderr}", "ERROR")

                return None

        except Exception as e:
            self.log_debug(f"❌ Screenshot capture failed: {e}", "ERROR")
            return None

    def generate_visual_comparison_html(self, svg_file, pptx_screenshot, debug_json):
        """Generate HTML with actual visual comparison."""
        self.log_debug("Generating visual comparison HTML", "HTML")

        # Read SVG content for embedding
        with open(svg_file, 'r') as f:
            svg_content = f.read()

        # Remove XML declaration for embedding
        if svg_content.startswith('<?xml'):
            svg_content = svg_content.split('>', 1)[1] if '>' in svg_content else svg_content

        # Screenshot section
        screenshot_section = ""
        if pptx_screenshot:
            screenshot_section = f"""
                <div class="comparison-panel">
                    <div class="panel-header">📊 PowerPoint Output (LibreOffice Screenshot)</div>
                    <div class="panel-content">
                        <img src="{pptx_screenshot.name}" alt="PowerPoint Screenshot"
                             style="max-width: 100%; max-height: 400px; border: 1px solid #ddd; border-radius: 4px;">
                    </div>
                </div>
            """
        else:
            screenshot_section = """
                <div class="comparison-panel">
                    <div class="panel-header">📊 PowerPoint Output</div>
                    <div class="panel-content">
                        <div style="text-align: center; color: #666; padding: 40px;">
                            ❌ LibreOffice screenshot failed<br>
                            <small>Check debug log for details</small>
                        </div>
                    </div>
                </div>
            """

        # Load debug info
        with open(debug_json, 'r') as f:
            debug_data = json.load(f)

        # Debug log HTML
        debug_html = ""
        for entry in debug_data['debug_log']:
            category_class = {
                'SUCCESS': 'success',
                'ERROR': 'error',
                'WARNING': 'warning',
                'DEBUG': 'debug',
                'INFO': 'info',
                'CONVERSION': 'conversion',
                'SCREENSHOT': 'screenshot',
                'HTML': 'html'
            }.get(entry['category'], 'info')

            debug_html += f'''
                <div class="debug-entry {category_class}">
                    <span class="timestamp">[{entry['timestamp']}]</span>
                    <span class="category">{entry['category']}</span>
                    <span class="message">{entry['message']}</span>
                </div>
            '''

        html_content = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SVG2PPTX Visual Comparison Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        .header {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }}

        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}

        .section {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}

        .comparison-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-top: 20px;
        }}

        .comparison-panel {{
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
        }}

        .panel-header {{
            background: #f8f9fa;
            padding: 15px;
            font-weight: 600;
            color: #495057;
            border-bottom: 2px solid #e0e0e0;
        }}

        .panel-content {{
            padding: 20px;
            min-height: 400px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .svg-container {{
            width: 100%;
            height: 400px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: white;
            overflow: auto;
        }}

        .svg-container svg {{
            width: 100%;
            height: auto;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}

        .stat-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #e0e0e0;
        }}

        .stat-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #495057;
            margin-bottom: 5px;
        }}

        .stat-label {{
            color: #6c757d;
            font-size: 0.9rem;
        }}

        .debug-log {{
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background: #f8f9fa;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.85rem;
        }}

        .debug-entry {{
            padding: 8px 12px;
            border-bottom: 1px solid #eee;
            display: flex;
            gap: 10px;
        }}

        .debug-entry:last-child {{
            border-bottom: none;
        }}

        .timestamp {{
            color: #666;
            font-weight: normal;
        }}

        .category {{
            font-weight: bold;
            min-width: 100px;
        }}

        .message {{
            flex: 1;
        }}

        .debug-entry.success .category {{ color: #28a745; }}
        .debug-entry.error .category {{ color: #dc3545; }}
        .debug-entry.warning .category {{ color: #ffc107; }}
        .debug-entry.debug .category {{ color: #6c757d; }}
        .debug-entry.info .category {{ color: #17a2b8; }}
        .debug-entry.conversion .category {{ color: #007bff; }}
        .debug-entry.screenshot .category {{ color: #6f42c1; }}
        .debug-entry.html .category {{ color: #e83e8c; }}

        @media (max-width: 768px) {{
            .comparison-container {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>🔍 SVG2PPTX Visual Comparison Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>

        <!-- Visual Comparison -->
        <section class="section">
            <h2>📊 Side-by-Side Visual Comparison</h2>
            <div class="comparison-container">
                <div class="comparison-panel">
                    <div class="panel-header">📄 Original SVG (Browser Rendered)</div>
                    <div class="panel-content">
                        <div class="svg-container">
                            {svg_content}
                        </div>
                    </div>
                </div>

                {screenshot_section}
            </div>
        </section>

        <!-- Conversion Statistics -->
        <section class="section">
            <h2>📈 Conversion Statistics</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{debug_data['conversion_stats']['path_count']}</div>
                    <div class="stat-label">Path Elements</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{debug_data['conversion_stats']['conversion_time']:.3f}s</div>
                    <div class="stat-label">Processing Time</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{debug_data['conversion_stats']['processing_rate']:.1f}</div>
                    <div class="stat-label">Paths/Second</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{debug_data['conversion_stats']['output_size'] / 1024:.1f}KB</div>
                    <div class="stat-label">Output Size</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{debug_data['conversion_stats']['compression_ratio']:.1f}x</div>
                    <div class="stat-label">Size Ratio</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{debug_data['conversion_stats']['text_count']}</div>
                    <div class="stat-label">Text Elements</div>
                </div>
            </div>
        </section>

        <!-- Debug Log -->
        <section class="section">
            <h2>🔧 Detailed Debug Log</h2>
            <div class="debug-log">
                {debug_html}
            </div>
        </section>
    </div>
</body>
</html>
        '''

        # Save HTML report
        html_file = self.output_dir / "visual_comparison_report.html"
        with open(html_file, 'w') as f:
            f.write(html_content)

        self.log_debug(f"✅ Visual comparison HTML saved: {html_file}", "SUCCESS")
        return html_file

    def run_complete_comparison(self, svg_file):
        """Run the complete visual comparison workflow."""
        self.log_debug("Starting complete visual comparison", "INFO")

        # Test PathSystem components first
        if not self.test_path_system_components():
            return False

        # Convert SVG to PPTX
        pptx_file = self.output_dir / f"{Path(svg_file).stem}_output.pptx"
        if not self.convert_svg_with_debugging(svg_file, pptx_file):
            return False

        # Capture LibreOffice screenshot
        screenshot_path = self.capture_libreoffice_screenshot(pptx_file)

        # Save debug information
        debug_file = self.output_dir / "debug_report.json"
        debug_data = {
            "timestamp": datetime.now().isoformat(),
            "svg_file": str(svg_file),
            "pptx_file": str(pptx_file),
            "screenshot_file": str(screenshot_path) if screenshot_path else None,
            "conversion_stats": self.conversion_stats,
            "debug_log": self.debug_info
        }

        with open(debug_file, 'w') as f:
            json.dump(debug_data, f, indent=2)

        self.log_debug(f"✅ Debug report saved: {debug_file}", "SUCCESS")

        # Generate visual comparison HTML
        html_file = self.generate_visual_comparison_html(svg_file, screenshot_path, debug_file)

        self.log_debug("🎉 Complete visual comparison finished", "SUCCESS")
        return True


def main():
    """Run the visual comparison generator."""
    print("=" * 80)
    print("🔍 SVG2PPTX Visual Comparison Generator")
    print("=" * 80)

    # Setup
    deliverables_dir = Path(__file__).parent
    svg_file = deliverables_dir / "test_complex_paths.svg"

    if not svg_file.exists():
        print(f"❌ SVG file not found: {svg_file}")
        return False

    # Generate comparison
    generator = VisualComparisonGenerator(deliverables_dir)
    success = generator.run_complete_comparison(svg_file)

    if success:
        print("\n🎉 Visual comparison completed successfully!")
        print(f"📋 Open visual_comparison_report.html to view results")
    else:
        print("\n❌ Visual comparison failed - check debug output")

    return success


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)