#!/usr/bin/env python3
"""
SVG2PPTX Demo Web Server

Serves the web demo interface and provides API endpoints for live conversion.
This demonstrates the complete CLI-to-web workflow with downloadable PPTX output.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import webbrowser

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.svg2pptx import convert_svg_to_pptx
from src.paths import create_path_system


class DemoHandler(SimpleHTTPRequestHandler):
    """Custom handler for the demo web server."""

    def __init__(self, *args, **kwargs):
        # Set the directory to serve files from
        self.directory = str(Path(__file__).parent)
        super().__init__(*args, directory=self.directory, **kwargs)

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/api/convert':
            self.handle_convert_api()
        elif parsed_path.path == '/api/status':
            self.handle_status_api()
        elif parsed_path.path == '/api/metadata':
            self.handle_metadata_api()
        else:
            # Serve static files
            super().do_GET()

    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/api/convert':
            self.handle_convert_post()
        else:
            self.send_error(404)

    def handle_convert_api(self):
        """Handle conversion API request."""
        try:
            print("🔄 API: Starting SVG conversion...")

            # Paths
            svg_file = Path(self.directory) / "test_complex_paths.svg"
            output_file = Path(self.directory) / "demo_output.pptx"

            if not svg_file.exists():
                self.send_json_error(400, "SVG file not found")
                return

            # Perform conversion
            start_time = time.time()
            result = convert_svg_to_pptx(str(svg_file), str(output_file))
            conversion_time = time.time() - start_time

            # Get file sizes
            input_size = svg_file.stat().st_size
            output_size = output_file.stat().st_size

            # Count paths
            with open(svg_file, 'r') as f:
                svg_content = f.read()
            path_count = svg_content.count('<path')

            # Prepare response
            response_data = {
                "success": True,
                "conversion_time": round(conversion_time, 3),
                "input_size": input_size,
                "output_size": output_size,
                "path_count": path_count,
                "processing_rate": round(path_count / conversion_time, 1),
                "output_file": "demo_output.pptx",
                "timestamp": datetime.now().isoformat()
            }

            self.send_json_response(response_data)
            print(f"✅ API: Conversion completed in {conversion_time:.2f}s")

        except Exception as e:
            print(f"❌ API: Conversion failed: {e}")
            self.send_json_error(500, f"Conversion failed: {str(e)}")

    def handle_convert_post(self):
        """Handle POST conversion with custom SVG data."""
        try:
            # Read request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            # Parse JSON data
            try:
                data = json.loads(post_data.decode('utf-8'))
                svg_content = data.get('svg_content', '')
            except json.JSONDecodeError:
                self.send_json_error(400, "Invalid JSON data")
                return

            if not svg_content:
                self.send_json_error(400, "No SVG content provided")
                return

            # Save SVG to temporary file
            temp_svg = Path(self.directory) / "temp_input.svg"
            temp_pptx = Path(self.directory) / "temp_output.pptx"

            with open(temp_svg, 'w') as f:
                f.write(svg_content)

            # Perform conversion
            start_time = time.time()
            result = convert_svg_to_pptx(str(temp_svg), str(temp_pptx))
            conversion_time = time.time() - start_time

            # Get results
            output_size = temp_pptx.stat().st_size
            path_count = svg_content.count('<path')

            response_data = {
                "success": True,
                "conversion_time": round(conversion_time, 3),
                "output_size": output_size,
                "path_count": path_count,
                "output_file": "temp_output.pptx"
            }

            self.send_json_response(response_data)

            # Clean up temp SVG
            temp_svg.unlink(missing_ok=True)

        except Exception as e:
            self.send_json_error(500, f"Conversion failed: {str(e)}")

    def handle_status_api(self):
        """Handle status API request."""
        try:
            # Test PathSystem components
            path_system = create_path_system(800, 600, (0, 0, 800, 600))
            test_path = "M 100 100 C 100 50 200 50 200 100 Z"
            result = path_system.process_path(test_path)

            status_data = {
                "status": "ready",
                "path_system_version": "2.0.0",
                "components_loaded": True,
                "test_conversion": {
                    "commands_processed": len(result.commands),
                    "xml_generated": len(result.path_xml),
                    "success": True
                },
                "timestamp": datetime.now().isoformat()
            }

            self.send_json_response(status_data)

        except Exception as e:
            self.send_json_error(500, f"System check failed: {str(e)}")

    def handle_metadata_api(self):
        """Handle metadata API request."""
        try:
            metadata_file = Path(self.directory) / "demo_metadata.json"

            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                self.send_json_response(metadata)
            else:
                self.send_json_response({"status": "no_metadata"})

        except Exception as e:
            self.send_json_error(500, f"Metadata error: {str(e)}")

    def send_json_response(self, data):
        """Send JSON response."""
        response_body = json.dumps(data, indent=2).encode('utf-8')

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response_body)

    def send_json_error(self, status_code, message):
        """Send JSON error response."""
        error_data = {
            "success": False,
            "error": message,
            "timestamp": datetime.now().isoformat()
        }
        response_body = json.dumps(error_data).encode('utf-8')

        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response_body)

    def log_message(self, format, *args):
        """Override to customize logging."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {format % args}")


def run_demo_server(port=8080):
    """Run the demo web server."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, DemoHandler)

    print("=" * 80)
    print("🚀 SVG2PPTX Demo Server Starting")
    print("=" * 80)
    print()
    print(f"🌐 Server running at: http://localhost:{port}")
    print(f"📂 Serving files from: {Path(__file__).parent}")
    print()
    print("🔗 Available endpoints:")
    print(f"   • Web Demo: http://localhost:{port}/web_demo.html")
    print(f"   • API Convert: http://localhost:{port}/api/convert")
    print(f"   • API Status: http://localhost:{port}/api/status")
    print(f"   • API Metadata: http://localhost:{port}/api/metadata")
    print()
    print("📋 Demo Features:")
    print("   • Live SVG to PowerPoint conversion")
    print("   • Side-by-side visual comparison")
    print("   • Downloadable PPTX output")
    print("   • Real-time conversion statistics")
    print("   • Path analysis and debugging")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 80)

    # Open browser after a short delay
    def open_browser():
        time.sleep(1)
        webbrowser.open(f'http://localhost:{port}/web_demo.html')

    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        httpd.shutdown()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='SVG2PPTX Demo Server')
    parser.add_argument('--port', type=int, default=8080,
                        help='Port to run the server on (default: 8080)')

    args = parser.parse_args()
    run_demo_server(args.port)