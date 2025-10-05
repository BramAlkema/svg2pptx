#!/usr/bin/env python3
"""
Example: Batch SVG to Slides conversion with OAuth

This example demonstrates how to use the batch processing API
with OAuth authentication to convert multiple SVG files directly
to Google Slides presentations.

Prerequisites:
1. OAuth credentials configured (GOOGLE_DRIVE_CLIENT_ID/CLIENT_SECRET)
2. User authenticated via CLI: `svg2pptx auth google`
3. SVG files to convert

Usage:
    python examples/batch_oauth_slides_export.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.auth import get_cli_token_store, get_system_username
from core.batch.coordinator import coordinate_batch_workflow_clean_slate
from core.batch.url_downloader import download_svgs_to_temp
from core.batch.models import CleanSlateBatchJob


def batch_convert_with_oauth(svg_urls: list[str], user_id: str = None, title_prefix: str = "Batch"):
    """
    Convert multiple SVGs to Google Slides using OAuth.

    Args:
        svg_urls: List of SVG URLs to convert
        user_id: User ID (defaults to system username)
        title_prefix: Prefix for Slides presentation titles

    Returns:
        Dictionary with conversion results and Slides URLs
    """
    # Get user ID
    if not user_id:
        user_id = get_system_username()

    # Verify OAuth authentication
    token_store = get_cli_token_store()
    if not token_store.has_token(user_id):
        print(f"❌ Error: User {user_id} not authenticated")
        print(f"   Run: svg2pptx auth google")
        return None

    # Verify OAuth credentials are configured
    if not os.getenv('GOOGLE_DRIVE_CLIENT_ID') or not os.getenv('GOOGLE_DRIVE_CLIENT_SECRET'):
        print("❌ Error: OAuth credentials not configured")
        print("   Set: GOOGLE_DRIVE_CLIENT_ID and GOOGLE_DRIVE_CLIENT_SECRET")
        return None

    print(f"🔐 Authenticated as: {user_id}")
    print(f"📥 Downloading {len(svg_urls)} SVG files...")

    # Download SVG files to temp directory
    job_id = f"batch_oauth_{os.urandom(4).hex()}"
    download_result = download_svgs_to_temp(urls=svg_urls, job_id=job_id)

    if not download_result.success:
        print(f"❌ Download failed: {len(download_result.errors)} errors")
        for error in download_result.errors:
            print(f"   - {error}")
        return None

    print(f"✅ Downloaded {len(download_result.file_paths)} files")

    # Create batch job for tracking
    batch_job = CleanSlateBatchJob(
        job_id=job_id,
        status="processing",
        total_files=len(download_result.file_paths),
        drive_integration_enabled=False,  # Using OAuth instead
    )
    batch_job.save()

    print(f"🔄 Converting to PPTX and exporting to Slides...")

    # Coordinate batch workflow with OAuth Slides export
    conversion_options = {
        'quality': 'high',
        'title': f'{title_prefix} Presentation',
        'folder_id': None,  # Can specify Drive folder ID here
    }

    result = coordinate_batch_workflow_clean_slate(
        job_id=job_id,
        file_paths=download_result.file_paths,
        conversion_options=conversion_options,
        user_id=user_id,
        export_to_slides=True,
    )

    # Handle Huey result wrapper
    if hasattr(result, '__call__'):
        result = result()

    # Display results
    if result.get('success'):
        print(f"\n✅ Success! Converted {len(svg_urls)} files to Google Slides")

        if result.get('slides_export'):
            slides_export = result['slides_export']
            print(f"\n📊 Google Slides URL:")
            print(f"   {slides_export.get('slides_url')}")
            print(f"\n📁 Slides ID: {slides_export.get('slides_id')}")

            if slides_export.get('web_view_link'):
                print(f"🔗 Web View: {slides_export.get('web_view_link')}")

        # Show conversion stats
        conversion = result.get('conversion', {})
        if conversion:
            print(f"\n📈 Conversion Stats:")
            print(f"   Pages: {conversion.get('page_count', 0)}")
            print(f"   Output Size: {conversion.get('output_size_bytes', 0)} bytes")

    else:
        print(f"\n❌ Conversion failed: {result.get('error_message')}")

    return result


def main():
    """Main entry point for example."""
    # Example SVG URLs (replace with your own)
    svg_urls = [
        "https://upload.wikimedia.org/wikipedia/commons/6/6b/Simple_Periodic_Table_Chart-en.svg",
        "https://upload.wikimedia.org/wikipedia/commons/0/02/SVG_logo.svg",
    ]

    print("=" * 60)
    print("Batch SVG to Google Slides Converter (OAuth)")
    print("=" * 60)
    print()

    # Get user ID from environment or use system username
    user_id = os.getenv('OAUTH_USER_ID') or get_system_username()

    # Run batch conversion
    result = batch_convert_with_oauth(
        svg_urls=svg_urls,
        user_id=user_id,
        title_prefix="Batch Demo"
    )

    if result:
        print("\n✨ Batch conversion completed successfully!")
        return 0
    else:
        print("\n❌ Batch conversion failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
