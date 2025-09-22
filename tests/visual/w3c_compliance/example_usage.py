#!/usr/bin/env python3
"""
W3C SVG Compliance Testing - Example Usage

Demonstrates how to use the W3C SVG compliance testing system for
comprehensive standards validation using LibreOffice automation.
"""

import asyncio
import logging
from pathlib import Path

from .compliance_runner import W3CComplianceTestRunner, ComplianceConfig, TestSuite
from .w3c_test_manager import W3CTestSuiteManager
from .svg_pptx_comparator import ComplianceLevel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def example_basic_compliance_test():
    """Example: Run basic W3C compliance tests."""
    print("=== Basic W3C Compliance Test Example ===")

    # Configure for basic compliance testing
    config = ComplianceConfig(
        test_suite=TestSuite.BASIC,
        w3c_version="1.1",
        max_tests=10,  # Limit for demo
        comparison_tolerance=0.85,
        libreoffice_headless=True,
        enable_detailed_analysis=True,
        generate_html_report=True,
        output_dir=Path("compliance_results/basic_test")
    )

    runner = W3CComplianceTestRunner(config)

    try:
        # Initialize (downloads W3C test suite, starts LibreOffice)
        print("Initializing compliance test runner...")
        success = await runner.initialize()
        if not success:
            print("❌ Failed to initialize compliance test runner")
            return

        print("✅ Initialization completed")

        # Run compliance tests
        print("Running basic compliance tests...")
        report = await runner.run_compliance_tests(
            progress_callback=lambda msg, current, total: print(f"  Progress: {msg}")
        )

        # Display results
        print("\n📊 Compliance Test Results:")
        print(f"   Overall Score: {report.overall_compliance_score:.3f}")
        print(f"   Tests Run: {report.total_tests}")
        print(f"   Successful: {report.successful_tests}")
        print(f"   Failed: {report.failed_tests}")
        print(f"   Execution Time: {report.total_execution_time:.1f}s")

        # Show compliance distribution
        print("\n📈 Compliance Distribution:")
        for level, count in report.compliance_distribution.items():
            print(f"   {level.upper()}: {count} tests")

        # Show category performance
        if report.category_scores:
            print("\n📂 Category Scores:")
            for category, score in report.category_scores.items():
                print(f"   {category}: {score:.3f}")

        # Show recommendations
        if report.recommendations:
            print("\n💡 Recommendations:")
            for recommendation in report.recommendations:
                print(f"   • {recommendation}")

        print(f"\n📄 Detailed report saved to: {config.output_dir}")

    finally:
        # Cleanup
        await runner.cleanup()


async def example_comprehensive_testing():
    """Example: Run comprehensive W3C compliance testing."""
    print("\n=== Comprehensive W3C Compliance Testing ===")

    config = ComplianceConfig(
        test_suite=TestSuite.COMPREHENSIVE,
        w3c_version="1.1",
        max_tests=50,  # More comprehensive
        comparison_tolerance=0.80,  # Slightly more lenient
        enable_detailed_analysis=True,
        save_intermediate_files=True,
        output_dir=Path("compliance_results/comprehensive_test")
    )

    runner = W3CComplianceTestRunner(config)

    try:
        print("Initializing comprehensive testing...")
        success = await runner.initialize()
        if not success:
            print("❌ Initialization failed")
            return

        # Progress tracking
        def progress_callback(message, current, total):
            percentage = (current / total) * 100 if total > 0 else 0
            print(f"  {message} ({percentage:.1f}%)")

        print("Running comprehensive compliance tests...")
        report = await runner.run_compliance_tests(progress_callback)

        print(f"\n🎯 Comprehensive Test Results:")
        print(f"   Overall Compliance: {report.overall_compliance_score:.3f}")
        print(f"   Test Coverage: {report.successful_tests}/{report.total_tests}")

        # Detailed feature analysis
        if report.feature_scores:
            print("\n🔧 Feature Compliance Scores:")
            for feature, score in sorted(report.feature_scores.items()):
                status = "✅" if score >= 0.8 else "⚠️" if score >= 0.6 else "❌"
                print(f"   {status} {feature}: {score:.3f}")

    finally:
        await runner.cleanup()


async def example_feature_specific_testing():
    """Example: Test specific SVG features."""
    print("\n=== Feature-Specific Compliance Testing ===")

    config = ComplianceConfig(
        test_suite=TestSuite.FEATURES,
        categories=["basic-shapes", "paths", "gradients", "text"],
        w3c_version="1.1",
        comparison_tolerance=0.85,
        output_dir=Path("compliance_results/feature_test")
    )

    runner = W3CComplianceTestRunner(config)

    try:
        print("Testing specific SVG features...")
        success = await runner.initialize()
        if not success:
            return

        report = await runner.run_compliance_tests()

        print("\n🎨 Feature-Specific Results:")
        for category, score in report.category_scores.items():
            compliance_level = "HIGH" if score >= 0.85 else "MEDIUM" if score >= 0.70 else "LOW"
            print(f"   {category}: {score:.3f} ({compliance_level})")

    finally:
        await runner.cleanup()


async def example_single_test():
    """Example: Test a single SVG file."""
    print("\n=== Single Test Case Example ===")

    config = ComplianceConfig(
        test_suite=TestSuite.CUSTOM,
        custom_test_names=["basic-shapes-rect"],  # Specific test
        output_dir=Path("compliance_results/single_test")
    )

    runner = W3CComplianceTestRunner(config)

    try:
        print("Running single test case...")
        success = await runner.initialize()
        if not success:
            return

        # Run specific test
        result = await runner.run_single_test("basic-shapes-rect")

        if result.success:
            print(f"✅ Test passed!")
            print(f"   Compliance Level: {result.overall_compliance.value}")
            if result.metrics:
                print(f"   Overall Score: {result.metrics.overall_score:.3f}")
                print(f"   Structural Similarity: {result.metrics.structural_similarity:.3f}")
                print(f"   Color Fidelity: {result.metrics.color_fidelity:.3f}")

            # Feature compliance details
            if result.feature_compliance:
                print("   Feature Compliance:")
                for feature in result.feature_compliance:
                    print(f"     {feature.feature_name}: {feature.level.value} ({feature.score:.3f})")
        else:
            print(f"❌ Test failed: {result.error_message}")

    finally:
        await runner.cleanup()


async def example_test_suite_management():
    """Example: W3C test suite management."""
    print("\n=== Test Suite Management Example ===")

    # Initialize test manager
    test_manager = W3CTestSuiteManager()

    try:
        # Download test suite
        print("Downloading W3C SVG test suite...")
        success = test_manager.download_test_suite("1.1")
        if not success:
            print("❌ Failed to download test suite")
            return

        # Load test cases
        print("Loading test cases...")
        success = test_manager.load_test_cases("1.1")
        if not success:
            print("❌ Failed to load test cases")
            return

        # Show suite information
        suite_info = test_manager.suite_info
        if suite_info:
            print(f"✅ Test Suite Loaded:")
            print(f"   Version: {suite_info.version}")
            print(f"   Total Tests: {suite_info.total_tests}")
            print(f"   Download Date: {suite_info.download_date.strftime('%Y-%m-%d')}")

        # Show categories
        categories = test_manager.get_categories()
        print(f"\n📁 Available Categories:")
        for category_name, info in categories.items():
            print(f"   {category_name}: {info['test_count']} tests ({info['difficulty']})")

        # Get basic compliance suite
        basic_suite = test_manager.get_basic_compliance_suite()
        print(f"\n🎯 Basic Compliance Suite: {len(basic_suite)} tests")

        # Export manifest
        manifest_path = Path("test_manifest.json")
        if test_manager.export_test_manifest(manifest_path):
            print(f"📄 Test manifest exported to: {manifest_path}")

    except Exception as e:
        logger.error(f"Test suite management error: {e}")


def example_configuration_options():
    """Example: Different configuration options."""
    print("\n=== Configuration Examples ===")

    # High-precision configuration
    high_precision_config = ComplianceConfig(
        test_suite=TestSuite.BASIC,
        comparison_tolerance=0.95,  # Very strict
        enable_detailed_analysis=True,
        reference_resolution=(2560, 1440),  # High resolution
        libreoffice_headless=True,
        screenshot_delay=3.0,  # More time for rendering
        generate_html_report=True,
        save_intermediate_files=True
    )

    # Fast testing configuration
    fast_config = ComplianceConfig(
        test_suite=TestSuite.BASIC,
        max_tests=5,  # Fewer tests
        comparison_tolerance=0.75,  # More lenient
        enable_detailed_analysis=False,  # Skip detailed analysis
        reference_resolution=(1280, 720),  # Lower resolution
        screenshot_delay=1.0,  # Faster screenshots
        save_intermediate_files=False
    )

    # CI/CD configuration
    ci_config = ComplianceConfig(
        test_suite=TestSuite.BASIC,
        max_tests=10,
        comparison_tolerance=0.80,
        libreoffice_headless=True,
        generate_html_report=False,  # Skip HTML for CI
        save_intermediate_files=False,
        output_dir=Path("ci_compliance_results")
    )

    print("High-Precision Config:")
    print(f"  Tolerance: {high_precision_config.comparison_tolerance}")
    print(f"  Resolution: {high_precision_config.reference_resolution}")
    print(f"  Detailed Analysis: {high_precision_config.enable_detailed_analysis}")

    print("\nFast Config:")
    print(f"  Max Tests: {fast_config.max_tests}")
    print(f"  Tolerance: {fast_config.comparison_tolerance}")
    print(f"  Screenshot Delay: {fast_config.screenshot_delay}s")

    print("\nCI/CD Config:")
    print(f"  Headless: {ci_config.libreoffice_headless}")
    print(f"  HTML Report: {ci_config.generate_html_report}")
    print(f"  Save Intermediate: {ci_config.save_intermediate_files}")


async def example_error_handling():
    """Example: Error handling and troubleshooting."""
    print("\n=== Error Handling Example ===")

    config = ComplianceConfig(
        test_suite=TestSuite.BASIC,
        max_tests=3,
        output_dir=Path("compliance_results/error_test")
    )

    runner = W3CComplianceTestRunner(config)

    try:
        # Initialization with error handling
        print("Attempting initialization...")
        success = await runner.initialize()

        if not success:
            print("❌ Initialization failed. Common issues:")
            print("   • LibreOffice not installed or not in PATH")
            print("   • Network issues downloading W3C test suite")
            print("   • Insufficient disk space")
            print("   • Port conflicts (try different port)")
            return

        print("✅ Initialization successful")

        # Run tests with error monitoring
        report = await runner.run_compliance_tests()

        # Check for common issues
        if report.failed_tests > 0:
            print(f"⚠️ {report.failed_tests} tests failed")
            print("Common failure causes:")
            print("   • PPTX conversion errors")
            print("   • LibreOffice rendering issues")
            print("   • Screenshot capture timeouts")

        if report.overall_compliance_score < 0.6:
            print("⚠️ Low compliance score detected")
            print("Potential improvements:")
            print("   • Check SVG2PPTX converter implementation")
            print("   • Verify LibreOffice version compatibility")
            print("   • Review test case selection")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("Troubleshooting steps:")
        print("   1. Check LibreOffice installation")
        print("   2. Verify network connectivity")
        print("   3. Check file permissions")
        print("   4. Review log files")

    finally:
        await runner.cleanup()


async def main():
    """Run all examples."""
    print("🧪 W3C SVG Compliance Testing Examples\n")

    # Show configuration options
    example_configuration_options()

    # Run examples (uncomment as needed)

    # Basic compliance test
    await example_basic_compliance_test()

    # Comprehensive testing (uncomment for full test)
    # await example_comprehensive_testing()

    # Feature-specific testing
    # await example_feature_specific_testing()

    # Single test case
    # await example_single_test()

    # Test suite management
    # await example_test_suite_management()

    # Error handling
    # await example_error_handling()

    print("\n✅ Examples completed!")
    print("\n💡 Tips:")
    print("   - Ensure LibreOffice is installed and in PATH")
    print("   - Use basic test suite for quick validation")
    print("   - Check HTML reports for detailed analysis")
    print("   - Monitor compliance scores over time")
    print("   - Use feature-specific tests for focused development")


if __name__ == "__main__":
    asyncio.run(main())