#!/usr/bin/env python3
"""
SVG2PPTX CLI - Convert SVG to PPTX with visual comparison
Usage: python svg2pptx_cli.py input.svg
"""

import sys
import os
import subprocess
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.svg2pptx import SVGToPowerPointConverter

class VisualComparisonCLI:
    """CLI for SVG to PPTX conversion with visual validation"""

    def __init__(self):
        self.converter = SVGToPowerPointConverter()
        self.soffice_path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"

    def convert_svg_to_pptx(self, svg_file: str) -> tuple[str, bool]:
        """Convert SVG to PPTX and return (pptx_path, success)"""
        print(f"🔄 Converting {svg_file} to PPTX...")

        try:
            pptx_path = self.converter.convert_file(svg_file)
            print(f"✅ PPTX created: {pptx_path}")
            return pptx_path, True
        except Exception as e:
            print(f"❌ Conversion failed: {e}")
            return "", False

    def render_pptx_with_soffice(self, pptx_path: str) -> tuple[str, bool]:
        """Use LibreOffice to render PPTX to PNG"""
        print(f"🖼️  Rendering PPTX with LibreOffice...")

        if not os.path.exists(self.soffice_path):
            print(f"❌ LibreOffice not found at {self.soffice_path}")
            return "", False

        try:
            result = subprocess.run([
                self.soffice_path, '--headless', '--convert-to', 'png',
                '--outdir', '.', pptx_path
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                png_path = str(Path(pptx_path).with_suffix('.png'))
                if os.path.exists(png_path):
                    print(f"✅ PPTX rendered: {png_path}")
                    return png_path, True
                else:
                    print("❌ PNG file not created")
                    return "", False
            else:
                print(f"❌ LibreOffice failed: {result.stderr}")
                return "", False

        except subprocess.TimeoutExpired:
            print("❌ LibreOffice rendering timeout")
            return "", False
        except Exception as e:
            print(f"❌ LibreOffice error: {e}")
            return "", False

    def embed_svg_content(self, svg_file: str) -> tuple[str, bool]:
        """Read SVG content for direct HTML embedding"""
        print(f"📄 Reading SVG content for embedding...")

        try:
            with open(svg_file, 'r') as f:
                svg_content = f.read()

            # Parse SVG dimensions for display info
            svg_width, svg_height = self._parse_svg_dimensions(svg_file)

            print(f"✅ SVG content ready: ({svg_width}x{svg_height})")
            return svg_content, True

        except Exception as e:
            print(f"❌ SVG embedding failed: {e}")
            return "", False

    def _parse_svg_dimensions(self, svg_file: str) -> tuple[int, int]:
        """Parse SVG width and height attributes"""
        try:
            from lxml import etree as ET

            with open(svg_file, 'r') as f:
                svg_content = f.read()

            # Handle XML declaration
            if svg_content.strip().startswith('<?xml'):
                svg_bytes = svg_content.encode('utf-8')
                root = ET.fromstring(svg_bytes)
            else:
                root = ET.fromstring(svg_content)

            # Get width and height attributes
            width_str = root.get('width', '200')
            height_str = root.get('height', '200')

            # Parse numeric values (strip units like 'px')
            import re
            width_match = re.match(r'(\d+)', width_str)
            height_match = re.match(r'(\d+)', height_str)

            width = int(width_match.group(1)) if width_match else 200
            height = int(height_match.group(1)) if height_match else 200

            # Ensure reasonable screenshot dimensions
            if width > 1200:
                height = int(height * (1200 / width))
                width = 1200
            if height > 900:
                width = int(width * (900 / height))
                height = 900

            return width, height

        except Exception as e:
            print(f"Warning: Could not parse SVG dimensions, using defaults: {e}")
            return 400, 300

    def create_comparison_html_with_embedded_svg(self, svg_file: str, svg_content: str,
                                                pptx_screenshot: str, pptx_file: str) -> str:
        """Create side-by-side comparison HTML with embedded SVG"""
        print(f"📄 Creating visual comparison with embedded SVG...")

        # Get SVG dimensions for display
        svg_width, svg_height = self._parse_svg_dimensions(svg_file)

        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>SVG2PPTX Conversion Result</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                    margin: 0; padding: 20px; background: #f5f5f5;
                }}
                .header {{
                    text-align: center; background: white; padding: 30px;
                    border-radius: 10px; margin-bottom: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .comparison {{
                    display: grid; grid-template-columns: 1fr 1fr; gap: 30px;
                    max-width: 1200px; margin: 0 auto; margin-bottom: 30px;
                }}
                .panel {{
                    background: white; padding: 25px; border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .panel h3 {{
                    margin-top: 0; text-align: center; font-size: 1.4em;
                    padding: 15px; border-radius: 8px; color: white;
                }}
                .svg-panel h3 {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
                .pptx-panel h3 {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
                .svg-container {{
                    display: flex; justify-content: center; align-items: center;
                    border: 2px solid #ddd; border-radius: 8px; padding: 20px;
                    background: white; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    min-height: 200px;
                }}
                .svg-container svg {{
                    max-width: 100%; height: auto;
                }}
                img {{
                    max-width: 100%; height: auto; border: 2px solid #ddd; border-radius: 8px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    object-fit: contain; background: white;
                }}
                .download-section {{
                    background: white; padding: 30px; border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center;
                    max-width: 600px; margin: 0 auto;
                }}
                .download-btn {{
                    display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; padding: 15px 30px; text-decoration: none;
                    border-radius: 8px; font-weight: bold; font-size: 1.1em;
                    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
                    transition: transform 0.2s ease;
                }}
                .download-btn:hover {{ transform: translateY(-2px); }}
                .meta {{ color: #666; margin-top: 15px; font-size: 0.9em; }}
                .success {{ background: #d4edda; color: #155724; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎨 SVG2PPTX Conversion Result</h1>
                <p><strong>Source:</strong> {Path(svg_file).name}</p>
                <div class="success">
                    <strong>✅ Conversion Successful!</strong> Compare the original SVG with the PowerPoint rendering.
                </div>
            </div>

            <div class="comparison">
                <div class="panel svg-panel">
                    <h3>📄 Original SVG</h3>
                    <div class="svg-container">
                        {svg_content}
                    </div>
                    <div class="meta">
                        Vector SVG: {svg_width}×{svg_height}px<br>
                        Source: {Path(svg_file).name}
                    </div>
                </div>

                <div class="panel pptx-panel">
                    <h3>📊 PowerPoint Result</h3>
                    <img src="{pptx_screenshot}" alt="PowerPoint rendering">
                    <div class="meta">
                        LibreOffice rendering of converted PPTX file
                    </div>
                </div>
            </div>

            <div class="download-section">
                <h3>📥 Download Your PowerPoint File</h3>
                <a href="{pptx_file}" class="download-btn" download>
                    ⬇️ Download {Path(pptx_file).name}
                </a>
                <div class="meta">
                    <p>File size: {Path(pptx_file).stat().st_size:,} bytes</p>
                    <p>Open in Microsoft PowerPoint, LibreOffice Impress, or Google Slides</p>
                </div>
            </div>
        </body>
        </html>
        '''

        comparison_file = f"{Path(svg_file).stem}_comparison.html"
        with open(comparison_file, 'w') as f:
            f.write(html_content)

        print(f"✅ Comparison created: {comparison_file}")
        return comparison_file

    def create_comparison_html(self, svg_file: str, svg_screenshot: str,
                              pptx_screenshot: str, pptx_file: str) -> str:
        """Create side-by-side comparison HTML"""
        print(f"📄 Creating visual comparison...")

        # Get SVG dimensions for display
        svg_width, svg_height = self._parse_svg_dimensions(svg_file)

        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>SVG2PPTX Conversion Result</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                    margin: 0; padding: 20px; background: #f5f5f5;
                }}
                .header {{
                    text-align: center; background: white; padding: 30px;
                    border-radius: 10px; margin-bottom: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .comparison {{
                    display: grid; grid-template-columns: 1fr 1fr; gap: 30px;
                    max-width: 1200px; margin: 0 auto; margin-bottom: 30px;
                }}
                .panel {{
                    background: white; padding: 25px; border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .panel h3 {{
                    margin-top: 0; text-align: center; font-size: 1.4em;
                    padding: 15px; border-radius: 8px; color: white;
                }}
                .svg-panel h3 {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
                .pptx-panel h3 {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
                img {{
                    max-width: 100%; height: auto; border: 2px solid #ddd; border-radius: 8px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    object-fit: contain; /* Preserve aspect ratio */
                    background: white; /* Show any transparency */
                }}
                .comparison-container {{
                    display: flex;
                    align-items: flex-start;
                    justify-content: center;
                    min-height: 400px; /* Consistent minimum height */
                }}
                .download-section {{
                    background: white; padding: 30px; border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center;
                    max-width: 600px; margin: 0 auto;
                }}
                .download-btn {{
                    display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; padding: 15px 30px; text-decoration: none;
                    border-radius: 8px; font-weight: bold; font-size: 1.1em;
                    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
                    transition: transform 0.2s ease;
                }}
                .download-btn:hover {{ transform: translateY(-2px); }}
                .meta {{ color: #666; margin-top: 15px; font-size: 0.9em; }}
                .success {{ background: #d4edda; color: #155724; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎨 SVG2PPTX Conversion Result</h1>
                <p><strong>Source:</strong> {Path(svg_file).name}</p>
                <div class="success">
                    <strong>✅ Conversion Successful!</strong> LibreOffice rendered vector graphics from your SVG.
                </div>
            </div>

            <div class="comparison">
                <div class="panel svg-panel">
                    <h3>📄 SVG Source</h3>
                    <img src="{svg_screenshot}" alt="SVG source">
                    <div class="meta">
                        Original SVG: {svg_width}×{svg_height}px<br>
                        Source: {Path(svg_file).name}
                    </div>
                </div>

                <div class="panel pptx-panel">
                    <h3>📊 PowerPoint Result</h3>
                    <img src="{pptx_screenshot}" alt="PowerPoint rendering">
                    <div class="meta">
                        LibreOffice rendering of converted PPTX file
                    </div>
                </div>
            </div>

            <div class="download-section">
                <h3>📥 Download Your PowerPoint File</h3>
                <a href="{pptx_file}" class="download-btn" download>
                    ⬇️ Download {Path(pptx_file).name}
                </a>
                <div class="meta">
                    <p>File size: {os.path.getsize(pptx_file):,} bytes</p>
                    <p>Open in Microsoft PowerPoint, LibreOffice Impress, or Google Slides</p>
                </div>
            </div>
        </body>
        </html>
        '''

        comparison_file = f"{Path(svg_file).stem}_comparison.html"
        Path(comparison_file).write_text(html_content)

        print(f"✅ Comparison created: {comparison_file}")
        return comparison_file

    async def process_svg(self, svg_file: str) -> bool:
        """Complete SVG to PPTX conversion with visual comparison"""
        if not os.path.exists(svg_file):
            print(f"❌ SVG file not found: {svg_file}")
            return False

        print(f"\n🎯 SVG2PPTX CLI Processing: {svg_file}")
        print("=" * 50)

        # Step 1: Convert SVG to PPTX
        pptx_file, success = self.convert_svg_to_pptx(svg_file)
        if not success:
            return False

        # Step 2: Render PPTX with LibreOffice
        pptx_screenshot, success = self.render_pptx_with_soffice(pptx_file)
        if not success:
            print("⚠️  Continuing without LibreOffice rendering...")
            pptx_screenshot = ""

        # Step 3: Read SVG content for embedding
        svg_content, success = self.embed_svg_content(svg_file)
        if not success:
            print("⚠️  Continuing without SVG content...")
            svg_content = ""

        # Step 4: Create comparison HTML
        if svg_content and pptx_screenshot:
            comparison_file = self.create_comparison_html_with_embedded_svg(
                svg_file, svg_content, pptx_screenshot, pptx_file
            )

            print(f"\n🎉 Complete! Open: {comparison_file}")
            print(f"📥 Download: {pptx_file}")

            # Open the comparison in browser
            try:
                if sys.platform == "darwin":  # macOS
                    subprocess.run(["open", comparison_file])
                elif sys.platform == "linux":
                    subprocess.run(["xdg-open", comparison_file])
                elif sys.platform == "win32":
                    subprocess.run(["start", comparison_file], shell=True)
            except:
                print(f"💡 Manually open: {comparison_file}")
        else:
            print(f"\n✅ PPTX created: {pptx_file}")
            print("⚠️  Visual comparison unavailable")

        return True

async def main():
    """CLI entry point"""
    if len(sys.argv) != 2:
        print("Usage: python svg2pptx_cli.py input.svg")
        print("Example: python svg2pptx_cli.py my_drawing.svg")
        sys.exit(1)

    svg_file = sys.argv[1]
    cli = VisualComparisonCLI()
    success = await cli.process_svg(svg_file)

    if not success:
        sys.exit(1)

    print("\n" + "=" * 50)
    print("✅ SVG2PPTX CLI completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())