#!/usr/bin/env python3
"""
Google Slides Visual Testing - Example Usage

Demonstrates how to use the Google Slides visual testing system for
automated screenshot capture and validation of SVG to PPTX conversions.
"""

import asyncio
import logging
from pathlib import Path

from test_runner import GoogleSlidesTestRunner, TestConfig
from authenticator import AuthConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def example_single_test():
    """Example: Run a single visual test."""
    print("=== Single Visual Test Example ===")

    # Configure test settings
    config = TestConfig(
        auth_method='service_account',
        credentials_path='~/.config/svg2pptx/google_credentials.json',
        validation_tolerance=0.95,
        cleanup_after_test=True,
        screenshot_method='hybrid'
    )

    # Create test runner
    runner = GoogleSlidesTestRunner(config)

    try:
        # Initialize (authenticate and setup)
        print("Initializing test runner...")
        success = await runner.initialize()
        if not success:
            print("❌ Failed to initialize test runner")
            return

        # Run test on sample SVG
        svg_path = Path("tests/visual/test_data/simple_shapes.svg")
        print(f"Running visual test on: {svg_path}")

        result = await runner.run_test(svg_path, "example_test")

        # Display results
        if result.success:
            print("✅ Test completed successfully!")
            print(f"   Presentation ID: {result.presentation_id}")
            print(f"   Public URL: {result.public_url}")
            print(f"   Screenshots: {len(result.screenshot_results)} captured")
            print(f"   Total time: {result.total_time:.2f}s")

            if result.validation_report:
                report = result.validation_report
                print(f"   Validation: {report.threshold_passed}/{report.total_comparisons} passed")
                print(f"   Average similarity: {report.average_similarity:.3f}")
        else:
            print(f"❌ Test failed: {result.error_message}")

    finally:
        # Cleanup
        await runner.cleanup()


async def example_batch_tests():
    """Example: Run batch visual tests on multiple SVG files."""
    print("\n=== Batch Visual Tests Example ===")

    # Configure for batch testing
    config = TestConfig(
        auth_method='service_account',
        credentials_path='~/.config/svg2pptx/google_credentials.json',
        validation_tolerance=0.90,  # Slightly lower threshold for batch
        cleanup_after_test=True,
        generate_diffs=True
    )

    runner = GoogleSlidesTestRunner(config)

    try:
        # Initialize
        print("Initializing for batch tests...")
        success = await runner.initialize()
        if not success:
            print("❌ Failed to initialize for batch tests")
            return

        # Prepare test SVG files
        test_svg_dir = Path("tests/visual/test_data/svg")
        svg_files = list(test_svg_dir.glob("*.svg"))

        if not svg_files:
            print("⚠️ No SVG files found in test data directory")
            return

        print(f"Found {len(svg_files)} SVG files for testing")

        # Progress callback
        def progress_callback(current, total, filename):
            print(f"  Progress: {current+1}/{total} - {Path(filename).name}")

        # Run batch tests
        results = await runner.run_batch_tests(svg_files, progress_callback)

        # Summary
        successful = sum(1 for r in results if r.success)
        print(f"\n📊 Batch Test Results:")
        print(f"   Total: {len(results)}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {len(results) - successful}")

        # Show failed tests
        failed_tests = [r for r in results if not r.success]
        if failed_tests:
            print("\n❌ Failed Tests:")
            for result in failed_tests:
                print(f"   - {result.test_name}: {result.error_message}")

    finally:
        await runner.cleanup()


async def example_create_baseline():
    """Example: Create reference baseline from current test run."""
    print("\n=== Create Reference Baseline Example ===")

    config = TestConfig(
        auth_method='service_account',
        credentials_path='~/.config/svg2pptx/google_credentials.json',
        cleanup_after_test=False  # Keep presentations for baseline creation
    )

    runner = GoogleSlidesTestRunner(config)

    try:
        # Initialize
        print("Initializing for baseline creation...")
        success = await runner.initialize()
        if not success:
            print("❌ Failed to initialize")
            return

        # Get test SVG files
        test_svg_dir = Path("tests/visual/test_data/svg")
        svg_files = list(test_svg_dir.glob("*.svg"))[:3]  # Limit for example

        if not svg_files:
            print("⚠️ No SVG files found")
            return

        print(f"Creating baseline from {len(svg_files)} SVG files...")

        # Create baseline
        success = await runner.create_reference_baseline(svg_files)

        if success:
            print("✅ Reference baseline created successfully!")
            print(f"   Reference images saved to: {runner.config.references_dir}")
        else:
            print("❌ Failed to create reference baseline")

    finally:
        await runner.cleanup()


def example_configuration():
    """Example: Different configuration options."""
    print("\n=== Configuration Examples ===")

    # High-quality configuration
    high_quality_config = TestConfig(
        auth_method='service_account',
        credentials_path='~/.config/svg2pptx/google_credentials.json',
        screenshot_format='png',
        screenshot_method='playwright',  # Higher quality screenshots
        validation_tolerance=0.98,  # Very strict validation
        generate_diffs=True,
        cleanup_after_test=True
    )

    # Fast testing configuration
    fast_config = TestConfig(
        auth_method='service_account',
        credentials_path='~/.config/svg2pptx/google_credentials.json',
        screenshot_format='jpeg',
        screenshot_method='api',  # Faster API-based screenshots
        validation_tolerance=0.85,  # More lenient validation
        generate_diffs=False,
        cleanup_after_test=True
    )

    print("High-quality config:")
    print(f"  Method: {high_quality_config.screenshot_method}")
    print(f"  Tolerance: {high_quality_config.validation_tolerance}")
    print(f"  Format: {high_quality_config.screenshot_format}")

    print("\nFast config:")
    print(f"  Method: {fast_config.screenshot_method}")
    print(f"  Tolerance: {fast_config.validation_tolerance}")
    print(f"  Format: {fast_config.screenshot_format}")


async def example_validation_only():
    """Example: Validate existing screenshots against references."""
    print("\n=== Validation Only Example ===")

    from visual_validator import VisualValidator

    # Create validator
    validator = VisualValidator(tolerance=0.95, enable_debug_output=True)

    # Paths to images
    screenshots_dir = Path("tests/visual/screenshots/example_test")
    references_dir = Path("tests/visual/references/example_test")

    if not screenshots_dir.exists() or not references_dir.exists():
        print("⚠️ Screenshot or reference directories not found")
        return

    # Get image lists
    screenshot_images = sorted(screenshots_dir.glob("*.png"))
    reference_images = sorted(references_dir.glob("*.png"))

    if not screenshot_images or not reference_images:
        print("⚠️ No images found for validation")
        return

    print(f"Validating {len(screenshot_images)} screenshots against {len(reference_images)} references")

    # Run validation
    output_dir = Path("tests/visual/reports/validation_only")
    validation_report = validator.validate_presentation(
        reference_images, screenshot_images, output_dir
    )

    # Show results
    print(f"✅ Validation completed:")
    print(f"   Total comparisons: {validation_report.total_comparisons}")
    print(f"   Passed threshold: {validation_report.threshold_passed}")
    print(f"   Average similarity: {validation_report.average_similarity:.3f}")

    if validation_report.threshold_failed > 0:
        print(f"   ⚠️ {validation_report.threshold_failed} comparisons below threshold")


async def main():
    """Run all examples."""
    print("🎯 Google Slides Visual Testing Examples\n")

    # Show configuration options
    example_configuration()

    # Run examples (uncomment as needed)

    # Single test example
    # await example_single_test()

    # Batch tests example
    # await example_batch_tests()

    # Create baseline example
    # await example_create_baseline()

    # Validation only example
    # await example_validation_only()

    print("\n✅ Examples completed!")
    print("\n💡 Tips:")
    print("   - Set up Google Cloud credentials before running tests")
    print("   - Use 'hybrid' screenshot method for best results")
    print("   - Create reference baselines before running validation")
    print("   - Check generated reports in tests/visual/reports/")


if __name__ == "__main__":
    asyncio.run(main())