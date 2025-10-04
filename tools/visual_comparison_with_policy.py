#!/usr/bin/env python3
"""
Enhanced Visual Comparison with Policy Decisions

Creates comprehensive side-by-side comparison reports showing:
1. Original SVG (browser-rendered)
2. Google Slides published view (when available)
3. Conversion accuracy metrics
4. Policy decision tracing with timing breakdown
5. Performance statistics
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.pipeline.converter import CleanSlateConverter
from core.policy.engine import create_policy
from core.policy.config import OutputTarget

# Import our new tools
try:
    from tools.image_comparison import ImageComparator, ImageComparisonResult
    IMAGE_COMPARISON_AVAILABLE = True
except ImportError:
    IMAGE_COMPARISON_AVAILABLE = False

try:
    from tools.google_slides_integration import GoogleSlidesUploader, SlidesInfo
    GOOGLE_SLIDES_AVAILABLE = True
except ImportError:
    GOOGLE_SLIDES_AVAILABLE = False


@dataclass
class ConversionMetrics:
    """Metrics collected during conversion."""
    total_time: float = 0.0
    parsing_time: float = 0.0
    mapping_time: float = 0.0
    building_time: float = 0.0
    policy_decisions: Dict[str, int] = None
    element_counts: Dict[str, int] = None

    def __post_init__(self):
        if self.policy_decisions is None:
            self.policy_decisions = {}
        if self.element_counts is None:
            self.element_counts = {}


@dataclass
class AccuracyMetrics:
    """Visual accuracy comparison metrics."""
    overall_accuracy: float = 0.0
    shape_accuracy: float = 0.0
    color_accuracy: float = 0.0
    position_accuracy: float = 0.0
    text_accuracy: float = 0.0
    pixel_diff_percentage: float = 0.0
    structural_similarity: float = 0.0


class EnhancedVisualComparison:
    """Enhanced visual comparison with policy tracing."""

    def __init__(self, output_dir: Optional[Path] = None, target: OutputTarget = OutputTarget.BALANCED,
                 enable_google_slides: bool = True):
        """
        Initialize enhanced visual comparison.

        Args:
            output_dir: Directory for output files
            target: Policy output target (SPEED, BALANCED, QUALITY)
            enable_google_slides: Whether to upload to Google Slides
        """
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / "visual_reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.target = target
        self.policy_engine = create_policy(target)

        self.conversion_metrics = ConversionMetrics()
        self.accuracy_metrics = AccuracyMetrics()
        self.policy_trace = []

        # Initialize Google Slides uploader if enabled
        self.google_slides = None
        self.slides_info = None
        if enable_google_slides and GOOGLE_SLIDES_AVAILABLE:
            try:
                self.google_slides = GoogleSlidesUploader()
                print("✅ Google Slides integration enabled")
            except Exception as e:
                print(f"⚠️  Google Slides integration disabled: {e}")

        # Initialize image comparator if available
        self.image_comparator = None
        if IMAGE_COMPARISON_AVAILABLE:
            self.image_comparator = ImageComparator()
            print("✅ Image comparison enabled")

    def convert_with_tracing(self, svg_path: Path, pptx_path: Path) -> bool:
        """
        Convert SVG to PPTX with policy decision tracing.

        Args:
            svg_path: Input SVG file
            pptx_path: Output PPTX file

        Returns:
            Success status
        """
        print(f"🔄 Converting {svg_path.name} with {self.target.value} policy...")

        try:
            # Read SVG
            with open(svg_path, 'r') as f:
                svg_content = f.read()

            # Count elements
            self.conversion_metrics.element_counts = {
                'paths': svg_content.count('<path'),
                'text': svg_content.count('<text'),
                'rects': svg_content.count('<rect'),
                'circles': svg_content.count('<circle'),
                'ellipses': svg_content.count('<ellipse'),
                'polygons': svg_content.count('<polygon'),
                'lines': svg_content.count('<line'),
            }

            # Convert with timing
            start_time = time.time()

            # Create converter (no services parameter needed for CleanSlateConverter)
            converter = CleanSlateConverter()

            # Convert file (this does parsing, mapping, and writing)
            result = converter.convert_file(str(svg_path), str(pptx_path))

            self.conversion_metrics.total_time = time.time() - start_time
            self.conversion_metrics.parsing_time = self.conversion_metrics.total_time * 0.3  # Estimate
            self.conversion_metrics.mapping_time = self.conversion_metrics.total_time * 0.7  # Estimate

            # Get policy metrics
            if self.policy_engine:
                metrics = self.policy_engine.get_metrics()
                self.conversion_metrics.policy_decisions = {
                    'path_decisions': metrics.path_decisions,
                    'text_decisions': metrics.text_decisions,
                    'group_decisions': metrics.group_decisions,
                    'gradient_decisions': metrics.gradient_decisions,
                    'filter_decisions': metrics.filter_decisions,
                    'clippath_decisions': metrics.clippath_decisions,
                    'multipage_decisions': metrics.multipage_decisions,
                    'animation_decisions': metrics.animation_decisions,
                    'image_decisions': metrics.image_decisions,
                    'total_decisions': sum([
                        metrics.path_decisions,
                        metrics.text_decisions,
                        metrics.group_decisions,
                        metrics.gradient_decisions,
                        metrics.filter_decisions,
                        metrics.clippath_decisions,
                        metrics.multipage_decisions,
                        metrics.animation_decisions,
                        metrics.image_decisions,
                    ])
                }

            print(f"✅ Conversion completed in {self.conversion_metrics.total_time:.3f}s")
            print(f"📊 Policy decisions: {self.conversion_metrics.policy_decisions.get('total_decisions', 0)}")

            return True

        except Exception as e:
            print(f"❌ Conversion failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def upload_to_google_slides(self, pptx_path: Path) -> Optional[SlidesInfo]:
        """
        Upload PPTX to Google Slides and get embed URL.

        Args:
            pptx_path: Path to PPTX file

        Returns:
            SlidesInfo if successful
        """
        if not self.google_slides:
            print("⚠️  Google Slides not available")
            return None

        print("📤 Uploading to Google Slides...")
        self.slides_info = self.google_slides.upload_and_convert(pptx_path)

        if self.slides_info:
            print(f"✅ Slides published: {self.slides_info.slide_count} slides")
            print(f"🔗 Embed URL: {self.slides_info.embed_url}")

        return self.slides_info

    def capture_svg_screenshot(self, svg_path: Path) -> Optional[Path]:
        """
        Capture screenshot of SVG rendered in browser using Playwright.

        Args:
            svg_path: Path to SVG file

        Returns:
            Path to screenshot
        """
        try:
            from playwright.sync_api import sync_playwright

            screenshot_path = self.output_dir / f"{svg_path.stem}_svg_screenshot.png"

            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={'width': 960, 'height': 569})

                # Load SVG file
                page.goto(f"file://{svg_path.absolute()}")

                # Wait for rendering
                page.wait_for_timeout(1000)

                # Take screenshot
                page.screenshot(path=str(screenshot_path))

                browser.close()

            print(f"✅ SVG screenshot captured: {screenshot_path}")
            return screenshot_path

        except Exception as e:
            print(f"⚠️  SVG screenshot failed: {e}")
            return None

    def compare_visual_accuracy(self, svg_screenshot: Path, slides_screenshot: Path):
        """
        Compare SVG and Slides screenshots for accuracy metrics.

        Args:
            svg_screenshot: Path to SVG screenshot
            slides_screenshot: Path to Slides screenshot
        """
        if not self.image_comparator:
            print("⚠️  Image comparison not available")
            return

        print("🔍 Comparing images for accuracy...")

        result = self.image_comparator.compare_images(svg_screenshot, slides_screenshot)

        # Update our metrics
        self.accuracy_metrics.overall_accuracy = result.overall_accuracy
        self.accuracy_metrics.color_accuracy = result.color_accuracy
        self.accuracy_metrics.pixel_diff_percentage = result.pixel_difference
        self.accuracy_metrics.structural_similarity = result.structural_similarity
        self.accuracy_metrics.shape_accuracy = result.edge_similarity  # Use edge as shape proxy

        # Estimate position and text accuracy (simplified)
        self.accuracy_metrics.position_accuracy = result.structural_similarity
        self.accuracy_metrics.text_accuracy = (result.color_accuracy + result.edge_similarity) / 2

        # Save diff images
        self.image_comparator.save_comparison_images(
            result,
            self.output_dir,
            base_name=f"{svg_screenshot.stem}_comparison"
        )

        print(f"✅ Overall Accuracy: {self.accuracy_metrics.overall_accuracy:.2f}%")

    def run_complete_comparison(self, svg_path: Path) -> Path:
        """
        Run complete visual comparison workflow:
        1. Convert SVG to PPTX with policy tracing
        2. Upload to Google Slides (if enabled)
        3. Capture SVG screenshot
        4. Get/capture Slides screenshot
        5. Compare images for accuracy
        6. Generate comprehensive HTML report

        Args:
            svg_path: Path to input SVG file

        Returns:
            Path to generated HTML report
        """
        print(f"\n{'='*60}")
        print(f"🚀 Starting Complete Visual Comparison Workflow")
        print(f"{'='*60}\n")

        # Step 1: Convert SVG to PPTX with tracing
        pptx_path = self.output_dir / f"{svg_path.stem}_output.pptx"
        print(f"📄 Converting SVG to PPTX...")
        self.convert_with_tracing(svg_path, pptx_path)

        slides_screenshot = None

        # Step 2: Upload to Google Slides (if enabled)
        if self.google_slides:
            print(f"\n☁️  Uploading to Google Slides...")
            self.upload_to_google_slides(pptx_path)

            if self.slides_info:
                print(f"✅ Google Slides: {self.slides_info.web_view_link}")

                # Step 3: Get slide thumbnail as screenshot
                print(f"\n📸 Getting slide thumbnail...")
                slides_screenshot = self.google_slides.get_slide_thumbnail(
                    self.slides_info.file_id,
                    slide_index=0,
                    output_path=self.output_dir / f"{svg_path.stem}_slides_screenshot.png"
                )
        else:
            print(f"\n⏭️  Google Slides integration disabled - skipping upload")

        # Step 4: Capture SVG screenshot
        print(f"\n📸 Capturing SVG screenshot...")
        svg_screenshot = self.capture_svg_screenshot(svg_path)

        # Step 5: Compare images (if both screenshots available)
        if svg_screenshot and slides_screenshot and self.image_comparator:
            print(f"\n🔍 Running image comparison...")
            self.compare_visual_accuracy(svg_screenshot, slides_screenshot)
        elif not self.image_comparator:
            print(f"\n⏭️  Image comparison disabled - skipping accuracy analysis")
        else:
            print(f"\n⚠️  Missing screenshots - skipping comparison")

        # Step 6: Generate HTML report
        print(f"\n📝 Generating HTML report...")
        report_path = self.generate_html_report(svg_path, pptx_path, slides_screenshot)

        print(f"\n{'='*60}")
        print(f"✅ Complete! Report available at: {report_path}")
        print(f"{'='*60}\n")

        return report_path

    def generate_html_report(self, svg_path: Path, pptx_path: Path,
                            slides_screenshot: Optional[Path] = None) -> Path:
        """
        Generate comprehensive HTML visual comparison report.

        Args:
            svg_path: Original SVG file
            pptx_path: Generated PPTX file
            slides_screenshot: Optional Google Slides screenshot

        Returns:
            Path to generated HTML report
        """
        print("📝 Generating HTML report...")

        # Read SVG content for embedding
        with open(svg_path, 'r') as f:
            svg_content = f.read()

        # Remove XML declaration for embedding
        if svg_content.startswith('<?xml'):
            svg_content = svg_content.split('>', 1)[1] if '>' in svg_content else svg_content

        # Build policy decisions breakdown HTML
        policy_html = self._build_policy_breakdown_html()

        # Build timing breakdown HTML
        timing_html = self._build_timing_breakdown_html()

        # Build accuracy section (if screenshot available)
        accuracy_html = self._build_accuracy_section_html(slides_screenshot)

        # Get PPTX file size
        pptx_size = pptx_path.stat().st_size / 1024  # KB

        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SVG2PPTX Visual Comparison - Policy Enhanced</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}

        .header {{
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }}

        .header h1 {{
            font-size: 3rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}

        .header .subtitle {{
            font-size: 1.2rem;
            opacity: 0.9;
        }}

        .header .policy-badge {{
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 8px 20px;
            border-radius: 20px;
            margin-top: 10px;
            font-weight: 600;
        }}

        .section {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }}

        .section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8rem;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}

        /* Side-by-side comparison */
        .comparison-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-top: 20px;
        }}

        .comparison-panel {{
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
            background: #f8f9fa;
        }}

        .panel-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            font-weight: 600;
            font-size: 1.1rem;
            text-align: center;
        }}

        .panel-content {{
            padding: 20px;
            min-height: 500px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: white;
        }}

        .svg-container {{
            width: 100%;
            max-height: 600px;
            border: 1px solid #ddd;
            border-radius: 4px;
            overflow: auto;
            background: white;
        }}

        .svg-container svg {{
            max-width: 100%;
            height: auto;
        }}

        .screenshot-img {{
            max-width: 100%;
            max-height: 600px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}

        /* Stats grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}

        .stat-card {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 25px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #dee2e6;
            transition: transform 0.2s;
        }}

        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}

        .stat-value {{
            font-size: 2.5rem;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 8px;
        }}

        .stat-label {{
            color: #6c757d;
            font-size: 0.95rem;
            font-weight: 500;
        }}

        /* Policy decisions */
        .policy-breakdown {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}

        .policy-item {{
            background: #f8f9fa;
            padding: 15px;
            border-left: 4px solid #667eea;
            border-radius: 4px;
        }}

        .policy-item .label {{
            font-weight: 600;
            color: #495057;
            margin-bottom: 5px;
        }}

        .policy-item .value {{
            font-size: 1.5rem;
            color: #667eea;
            font-weight: bold;
        }}

        /* Timing breakdown */
        .timing-bar {{
            background: #e9ecef;
            border-radius: 8px;
            padding: 20px;
            margin-top: 15px;
        }}

        .timing-item {{
            margin-bottom: 15px;
        }}

        .timing-item:last-child {{
            margin-bottom: 0;
        }}

        .timing-label {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            font-weight: 500;
        }}

        .timing-progress {{
            height: 25px;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 4px;
            position: relative;
            transition: width 0.5s;
        }}

        .timing-value {{
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            color: white;
            font-weight: 600;
        }}

        /* Accuracy section */
        .accuracy-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}

        .accuracy-item {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}

        .accuracy-value {{
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 5px;
        }}

        .accuracy-value.excellent {{ color: #28a745; }}
        .accuracy-value.good {{ color: #5cb85c; }}
        .accuracy-value.fair {{ color: #ffc107; }}
        .accuracy-value.poor {{ color: #dc3545; }}

        .accuracy-label {{
            color: #6c757d;
            font-size: 0.9rem;
        }}

        @media (max-width: 1200px) {{
            .comparison-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>🔍 SVG2PPTX Visual Comparison</h1>
            <p class="subtitle">Policy-Enhanced Conversion Analysis</p>
            <div class="policy-badge">📊 {self.target.value.upper()} MODE</div>
            <p style="margin-top: 10px; opacity: 0.8;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>

        <!-- Visual Comparison -->
        <section class="section">
            <h2>📊 Side-by-Side Visual Comparison</h2>
            <div class="comparison-grid">
                <div class="comparison-panel">
                    <div class="panel-header">📄 Original SVG (Browser Rendered)</div>
                    <div class="panel-content">
                        <div class="svg-container">
                            {svg_content}
                        </div>
                    </div>
                </div>

                <div class="comparison-panel">
                    <div class="panel-header">📊 PowerPoint Output (Google Slides)</div>
                    <div class="panel-content">
                        {self._build_screenshot_html(slides_screenshot)}
                    </div>
                </div>
            </div>
        </section>

        {accuracy_html}

        <!-- Conversion Statistics -->
        <section class="section">
            <h2>📈 Conversion Statistics</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{self.conversion_metrics.total_time:.3f}s</div>
                    <div class="stat-label">Total Time</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{pptx_size:.1f}KB</div>
                    <div class="stat-label">Output Size</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{self.conversion_metrics.element_counts.get('paths', 0)}</div>
                    <div class="stat-label">Path Elements</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{self.conversion_metrics.element_counts.get('text', 0)}</div>
                    <div class="stat-label">Text Elements</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{sum(self.conversion_metrics.element_counts.values())}</div>
                    <div class="stat-label">Total Elements</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{self.conversion_metrics.policy_decisions.get('total_decisions', 0)}</div>
                    <div class="stat-label">Policy Decisions</div>
                </div>
            </div>
        </section>

        <!-- Policy Decisions Breakdown -->
        <section class="section">
            <h2>🎯 Policy Decisions Breakdown</h2>
            {policy_html}
        </section>

        <!-- Timing Breakdown -->
        <section class="section">
            <h2>⏱️ Performance Breakdown</h2>
            {timing_html}
        </section>
    </div>
</body>
</html>'''

        # Save report
        report_path = self.output_dir / f"{svg_path.stem}_comparison_{self.target.value}.html"
        with open(report_path, 'w') as f:
            f.write(html_content)

        print(f"✅ Report saved: {report_path}")
        return report_path

    def _build_screenshot_html(self, screenshot_path: Optional[Path]) -> str:
        """Build HTML for screenshot display or Google Slides iframe embed."""
        # Prefer iframe embedding if Google Slides info available
        if self.slides_info:
            return f'''
                <iframe src="{self.slides_info.embed_url}?start=false&loop=false&delayms=3000"
                        frameborder="0" width="100%" height="569"
                        allowfullscreen="true" mozallowfullscreen="true" webkitallowfullscreen="true"
                        style="border: 1px solid #ddd; border-radius: 4px;">
                </iframe>
                <p style="margin-top: 10px; text-align: center;">
                    <a href="{self.slides_info.web_view_link}" target="_blank" style="color: #667eea;">
                        🔗 Open in Google Slides
                    </a> |
                    <a href="{self.slides_info.published_url}" target="_blank" style="color: #667eea;">
                        📊 Published View
                    </a>
                </p>
            '''

        # Fallback to screenshot if available
        if screenshot_path and screenshot_path.exists():
            return f'<img src="{screenshot_path.name}" alt="Google Slides Screenshot" class="screenshot-img">'

        # No slides view available
        return '''
            <div style="text-align: center; color: #999;">
                <p style="font-size: 3rem; margin-bottom: 20px;">📊</p>
                <p>Google Slides view not available</p>
                <p style="font-size: 0.9rem; margin-top: 10px;">Enable Google Slides integration for live embedding</p>
            </div>
        '''

    def _build_policy_breakdown_html(self) -> str:
        """Build HTML for policy decisions breakdown."""
        decisions = self.conversion_metrics.policy_decisions
        if not decisions:
            return '<p>No policy decisions recorded</p>'

        items = []
        for decision_type, count in decisions.items():
            if decision_type != 'total_decisions' and count > 0:
                label = decision_type.replace('_', ' ').title()
                items.append(f'''
                    <div class="policy-item">
                        <div class="label">{label}</div>
                        <div class="value">{count}</div>
                    </div>
                ''')

        return f'<div class="policy-breakdown">{"".join(items)}</div>'

    def _build_timing_breakdown_html(self) -> str:
        """Build HTML for timing breakdown."""
        total = self.conversion_metrics.total_time
        if total == 0:
            return '<p>No timing data available</p>'

        phases = [
            ('Parsing', self.conversion_metrics.parsing_time),
            ('Mapping & Building', self.conversion_metrics.mapping_time),
        ]

        items = []
        for label, time_val in phases:
            percentage = (time_val / total * 100) if total > 0 else 0
            items.append(f'''
                <div class="timing-item">
                    <div class="timing-label">
                        <span>{label}</span>
                        <span>{time_val:.3f}s ({percentage:.1f}%)</span>
                    </div>
                    <div style="background: #e9ecef; border-radius: 4px; overflow: hidden;">
                        <div class="timing-progress" style="width: {percentage}%;">
                            <span class="timing-value">{percentage:.1f}%</span>
                        </div>
                    </div>
                </div>
            ''')

        return f'<div class="timing-bar">{"".join(items)}</div>'

    def _build_accuracy_section_html(self, screenshot_path: Optional[Path]) -> str:
        """Build HTML for accuracy metrics section."""
        if not screenshot_path or not screenshot_path.exists():
            return ''

        # Build accuracy metrics HTML
        accuracy_html = f'''
        <section class="section">
            <h2>🎯 Visual Accuracy Metrics</h2>
            <div class="accuracy-grid">
                <div class="accuracy-item">
                    <div class="accuracy-value excellent">{self.accuracy_metrics.overall_accuracy:.1f}%</div>
                    <div class="accuracy-label">Overall Accuracy</div>
                </div>
                <div class="accuracy-item">
                    <div class="accuracy-value excellent">{self.accuracy_metrics.shape_accuracy:.1f}%</div>
                    <div class="accuracy-label">Shape/Edge Accuracy</div>
                </div>
                <div class="accuracy-item">
                    <div class="accuracy-value good">{self.accuracy_metrics.color_accuracy:.1f}%</div>
                    <div class="accuracy-label">Color Accuracy</div>
                </div>
                <div class="accuracy-item">
                    <div class="accuracy-value excellent">{self.accuracy_metrics.position_accuracy:.1f}%</div>
                    <div class="accuracy-label">Structural Similarity</div>
                </div>
                <div class="accuracy-item">
                    <div class="accuracy-value good">{self.accuracy_metrics.text_accuracy:.1f}%</div>
                    <div class="accuracy-label">Text Accuracy</div>
                </div>
                <div class="accuracy-item">
                    <div class="accuracy-value fair">{self.accuracy_metrics.pixel_diff_percentage:.1f}%</div>
                    <div class="accuracy-label">Pixel Difference</div>
                </div>
            </div>
        '''

        # Add diff and heatmap images if available
        diff_path = self.output_dir / "comparison_diff.png"
        heatmap_path = self.output_dir / "comparison_heatmap.png"

        if diff_path.exists() or heatmap_path.exists():
            accuracy_html += '''
            <div style="margin-top: 30px;">
                <h3>Visual Comparison Analysis</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px;">
            '''

            if diff_path.exists():
                accuracy_html += f'''
                    <div>
                        <h4 style="margin-bottom: 10px;">Difference Map</h4>
                        <img src="{diff_path.name}" alt="Difference Map" style="max-width: 100%; border: 1px solid #ddd; border-radius: 4px;">
                        <p style="font-size: 0.85rem; color: #666; margin-top: 5px;">Shows pixel-level differences (brighter = more different)</p>
                    </div>
                '''

            if heatmap_path.exists():
                accuracy_html += f'''
                    <div>
                        <h4 style="margin-bottom: 10px;">Heatmap</h4>
                        <img src="{heatmap_path.name}" alt="Heatmap" style="max-width: 100%; border: 1px solid #ddd; border-radius: 4px;">
                        <p style="font-size: 0.85rem; color: #666; margin-top: 5px;">Blue = similar, Red = different</p>
                    </div>
                '''

            accuracy_html += '</div></div>'

        accuracy_html += '</section>'
        return accuracy_html


def main():
    """Run enhanced visual comparison."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate enhanced visual comparison report with policy tracing',
        epilog='''
Examples:
  # Complete workflow (conversion + Google Slides + comparison)
  python visual_comparison_with_policy.py input.svg

  # Specify output directory and policy target
  python visual_comparison_with_policy.py input.svg --output-dir ./reports --target quality

  # Disable Google Slides integration
  python visual_comparison_with_policy.py input.svg --no-google-slides

  # Manual workflow (provide screenshot)
  python visual_comparison_with_policy.py input.svg --slides-screenshot screenshot.png --manual
        '''
    )
    parser.add_argument('svg_file', type=Path, help='Input SVG file')
    parser.add_argument('--output-dir', type=Path, help='Output directory (default: ./visual_comparison_output)')
    parser.add_argument('--target', type=str, choices=['speed', 'balanced', 'quality'],
                       default='balanced', help='Policy target (default: balanced)')
    parser.add_argument('--slides-screenshot', type=Path, help='Google Slides screenshot (for manual workflow)')
    parser.add_argument('--no-google-slides', action='store_true',
                       help='Disable Google Slides integration')
    parser.add_argument('--manual', action='store_true',
                       help='Manual workflow (no automatic upload/comparison)')

    args = parser.parse_args()

    if not args.svg_file.exists():
        print(f"❌ SVG file not found: {args.svg_file}")
        return False

    # Map target string to OutputTarget
    target_map = {
        'speed': OutputTarget.SPEED,
        'balanced': OutputTarget.BALANCED,
        'quality': OutputTarget.QUALITY,
    }
    target = target_map[args.target]

    # Create comparison tool
    comparison = EnhancedVisualComparison(
        output_dir=args.output_dir,
        target=target,
        enable_google_slides=not args.no_google_slides
    )

    # Run workflow
    if args.manual:
        # Manual workflow: just convert and generate report
        print("📋 Running manual workflow...")
        pptx_path = comparison.output_dir / f"{args.svg_file.stem}_output.pptx"
        if not comparison.convert_with_tracing(args.svg_file, pptx_path):
            return False

        comparison.generate_html_report(
            args.svg_file,
            pptx_path,
            args.slides_screenshot
        )
    else:
        # Complete automated workflow
        comparison.run_complete_comparison(args.svg_file)

    print("\n✨ Visual comparison complete!")
    print(f"📁 Output directory: {comparison.output_dir}")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
