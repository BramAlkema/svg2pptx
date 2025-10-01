#!/usr/bin/env python3
"""
Test Huey job queue with a simple SVG conversion task.
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.batch.tasks import convert_single_svg

# Simple test SVG
test_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
    <rect x="10" y="10" width="80" height="60" fill="blue" stroke="black" stroke-width="2"/>
    <circle cx="150" cy="40" r="30" fill="red"/>
    <text x="10" y="90" font-size="12">Test SVG</text>
</svg>'''

def test_push_job():
    """Push a job to Huey queue"""

    print("🚀 Pushing SVG conversion job to Huey queue...")
    print("=" * 70)

    # Prepare file data
    file_data = {
        'filename': 'test_huey.svg',
        'content': test_svg.encode('utf-8'),
        'metadata': {
            'test': True,
            'source': 'huey_test_script'
        }
    }

    conversion_options = {
        'slide_width': 10.0,
        'slide_height': 7.5,
        'quality': 'high'
    }

    # Push task to queue
    result = convert_single_svg(file_data, conversion_options)

    print(f"✅ Job pushed to queue")
    print(f"   Task ID: {result.id if hasattr(result, 'id') else 'N/A'}")
    print(f"   Task: {result}")
    print()

    # Wait and check result
    print("⏳ Waiting for job to complete...")
    max_wait = 30  # seconds
    start_time = time.time()

    while time.time() - start_time < max_wait:
        if result.is_revoked():
            print("❌ Job was revoked")
            break
        elif result() is not None:  # Result is ready
            print("✅ Job completed!")
            job_result = result()
            print()
            print("📊 Job Result:")
            print(f"   Status: {job_result.get('status', 'unknown')}")
            print(f"   Filename: {job_result.get('filename', 'N/A')}")
            if 'error' in job_result:
                print(f"   ❌ Error: {job_result['error']}")
            if 'output_path' in job_result:
                print(f"   ✅ Output: {job_result['output_path']}")
            if 'conversion_time' in job_result:
                print(f"   ⏱️  Time: {job_result['conversion_time']:.2f}s")
            return True

        time.sleep(0.5)

    print(f"⏰ Timeout after {max_wait}s - job may still be running")
    print()
    print("💡 TIP: Start Huey worker in another terminal:")
    print("   source venv/bin/activate && PYTHONPATH=. huey_consumer core.batch.huey_app.huey")
    return False

if __name__ == "__main__":
    success = test_push_job()
    sys.exit(0 if success else 1)
