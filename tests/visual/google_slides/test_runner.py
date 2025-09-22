#!/usr/bin/env python3
"""
Google Slides Test Runner Module

Orchestrates the complete visual test workflow from SVG to Google Slides screenshots.
Provides comprehensive test reporting and integrates all components of the visual testing pipeline.
"""

import os
import time
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from datetime import datetime
import json

# Import our modules
from .authenticator import GoogleSlidesAuthenticator, AuthConfig
from .slides_converter import SlidesConverter, ConversionResult
from .publisher import SlidesPublisher, PublishedPresentation
from .screenshot_capture import SlidesScreenshotCapture, ScreenshotResult, CaptureMethod
from .visual_validator import VisualValidator, ValidationReport

# SVG2PPTX imports
try:
    from src.svg2pptx import convert_svg_to_pptx
    SVG2PPTX_AVAILABLE = True
except ImportError:
    SVG2PPTX_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class TestConfig:
    """Configuration for Google Slides testing."""
    # Authentication
    auth_method: str = 'service_account'
    credentials_path: Optional[str] = None

    # Conversion settings
    drive_folder_id: Optional[str] = None
    cleanup_after_test: bool = True

    # Screenshot settings
    screenshot_format: str = 'png'
    screenshot_quality: int = 100
    screenshot_method: str = CaptureMethod.HYBRID
    screenshot_timeout: int = 30

    # Validation settings
    validation_tolerance: float = 0.95
    generate_diffs: bool = True
    fail_on_mismatch: bool = True

    # Output directories
    screenshots_dir: Path = field(default_factory=lambda: Path("tests/visual/screenshots"))
    references_dir: Path = field(default_factory=lambda: Path("tests/visual/references"))
    reports_dir: Path = field(default_factory=lambda: Path("tests/visual/reports"))
    temp_dir: Path = field(default_factory=lambda: Path("tests/visual/temp"))


@dataclass
class TestResult:
    """Result of a complete visual test run."""
    success: bool
    test_name: str
    svg_path: Path
    pptx_path: Optional[Path] = None
    presentation_id: Optional[str] = None
    public_url: Optional[str] = None
    screenshot_results: List[ScreenshotResult] = field(default_factory=list)
    validation_report: Optional[ValidationReport] = None
    error_message: Optional[str] = None
    total_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class GoogleSlidesTestRunner:
    """Orchestrate the complete test workflow."""

    def __init__(self, config: Union[TestConfig, Dict[str, Any]]):
        """
        Initialize test runner.

        Args:
            config: TestConfig object or dictionary with configuration
        """
        if isinstance(config, dict):
            self.config = TestConfig(**config)
        else:
            self.config = config

        # Initialize components
        self.authenticator = None
        self.converter = None
        self.publisher = None
        self.screenshot_capture = None
        self.validator = None

        # Test state
        self._initialized = False
        self._test_session_id = datetime.now().strftime('%Y%m%d_%H%M%S')

        logger.info(f"GoogleSlidesTestRunner initialized - Session: {self._test_session_id}")

    async def initialize(self) -> bool:
        """
        Initialize all components and authenticate.

        Returns:
            True if initialization successful
        """
        try:
            # Check dependencies
            if not SVG2PPTX_AVAILABLE:
                logger.error("SVG2PPTX module not available")
                return False

            # Set up output directories
            self._setup_directories()

            # Initialize authenticator
            auth_config = AuthConfig(
                method=self.config.auth_method,
                credentials_path=self.config.credentials_path
            )

            self.authenticator = GoogleSlidesAuthenticator(self.config.auth_method)
            self.authenticator.configure(auth_config)

            # Authenticate
            if not self.authenticator.authenticate():
                logger.error("Authentication failed")
                return False

            # Test authentication
            auth_test = self.authenticator.test_authentication()
            if not auth_test['authenticated']:
                logger.error(f"Authentication test failed: {auth_test}")
                return False

            logger.info(f"Authenticated as: {auth_test.get('user_email', 'Unknown')}")

            # Initialize other components
            self.converter = SlidesConverter(self.authenticator)
            self.publisher = SlidesPublisher(self.authenticator)
            self.screenshot_capture = SlidesScreenshotCapture(self.authenticator)
            self.validator = VisualValidator(
                tolerance=self.config.validation_tolerance,
                enable_debug_output=self.config.generate_diffs
            )

            self._initialized = True
            logger.info("GoogleSlidesTestRunner initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    async def run_test(self, svg_path: Path, test_name: Optional[str] = None) -> TestResult:
        """
        Run complete visual test pipeline.

        Args:
            svg_path: Path to SVG file
            test_name: Optional test name (defaults to SVG filename)

        Returns:
            TestResult with complete pipeline results
        """
        start_time = time.time()

        if test_name is None:
            test_name = svg_path.stem

        result = TestResult(
            success=False,
            test_name=test_name,
            svg_path=svg_path
        )

        try:
            if not self._initialized:
                raise RuntimeError("Test runner not initialized. Call initialize() first.")

            if not svg_path.exists():
                raise FileNotFoundError(f"SVG file not found: {svg_path}")

            logger.info(f"Starting visual test: {test_name}")

            # Step 1: Convert SVG to PPTX
            pptx_path = await self._convert_svg_to_pptx(svg_path, test_name)
            result.pptx_path = pptx_path

            # Step 2: Upload and convert to Google Slides
            conversion_result = await self._convert_pptx_to_slides(pptx_path, test_name)
            result.presentation_id = conversion_result.presentation_id
            result.metadata['conversion'] = conversion_result.metadata

            # Step 3: Publish presentation
            published = await self._publish_presentation(conversion_result.presentation_id)
            result.public_url = published.public_url
            result.metadata['publication'] = published.metadata

            # Step 4: Capture screenshots
            screenshots = await self._capture_screenshots(conversion_result.presentation_id, test_name)
            result.screenshot_results = screenshots

            # Step 5: Validate against references (if they exist)
            validation_report = await self._validate_screenshots(screenshots, test_name)
            result.validation_report = validation_report

            # Step 6: Cleanup if requested
            if self.config.cleanup_after_test:
                await self._cleanup_test_resources(conversion_result.presentation_id, pptx_path)

            result.success = True
            result.total_time = time.time() - start_time

            logger.info(f"Visual test completed successfully: {test_name} ({result.total_time:.2f}s)")
            return result

        except Exception as e:
            result.error_message = str(e)
            result.total_time = time.time() - start_time
            logger.error(f"Visual test failed: {test_name}: {e}")
            return result

    async def run_batch_tests(self, svg_files: List[Path],
                            progress_callback: Optional[callable] = None) -> List[TestResult]:
        """
        Run visual tests for multiple SVG files.

        Args:
            svg_files: List of SVG file paths
            progress_callback: Optional progress callback

        Returns:
            List of TestResult objects
        """
        results = []
        total_files = len(svg_files)

        logger.info(f"Starting batch visual tests: {total_files} files")

        for i, svg_path in enumerate(svg_files):
            try:
                if progress_callback:
                    progress_callback(i, total_files, str(svg_path))

                test_name = f"batch_{i+1:03d}_{svg_path.stem}"
                result = await self.run_test(svg_path, test_name)
                results.append(result)

                if result.success:
                    logger.info(f"Batch {i+1}/{total_files}: SUCCESS - {svg_path.name}")
                else:
                    logger.warning(f"Batch {i+1}/{total_files}: FAILED - {svg_path.name}: {result.error_message}")

            except Exception as e:
                error_result = TestResult(
                    success=False,
                    test_name=f"batch_{i+1:03d}_{svg_path.stem}",
                    svg_path=svg_path,
                    error_message=str(e)
                )
                results.append(error_result)
                logger.error(f"Batch {i+1}/{total_files}: ERROR - {svg_path.name}: {e}")

        # Generate batch report
        await self._generate_batch_report(results)

        successful = sum(1 for r in results if r.success)
        logger.info(f"Batch visual tests completed: {successful}/{total_files} successful")

        return results

    async def create_reference_baseline(self, svg_files: List[Path]) -> bool:
        """
        Create reference images baseline from current test run.

        Args:
            svg_files: List of SVG files to create baseline for

        Returns:
            True if successful
        """
        try:
            logger.info(f"Creating reference baseline for {len(svg_files)} SVG files")

            # Run tests without validation
            original_cleanup = self.config.cleanup_after_test
            self.config.cleanup_after_test = False

            results = await self.run_batch_tests(svg_files)

            # Restore cleanup setting
            self.config.cleanup_after_test = original_cleanup

            # Collect all screenshots and copy to references directory
            reference_images = []
            for result in results:
                if result.success and result.screenshot_results:
                    for screenshot in result.screenshot_results:
                        if screenshot.success and screenshot.output_path:
                            reference_images.append(screenshot.output_path)

            # Create references
            success = self.validator.create_reference_images(reference_images, self.config.references_dir)

            if success:
                logger.info(f"Reference baseline created with {len(reference_images)} images")
            else:
                logger.error("Failed to create reference baseline")

            return success

        except Exception as e:
            logger.error(f"Failed to create reference baseline: {e}")
            return False

    async def cleanup(self):
        """Cleanup test runner resources."""
        try:
            if self.screenshot_capture:
                await self.screenshot_capture.cleanup()

            logger.info("Test runner cleanup completed")

        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    async def _convert_svg_to_pptx(self, svg_path: Path, test_name: str) -> Path:
        """Convert SVG to PPTX using SVG2PPTX library."""
        output_path = self.config.temp_dir / f"{test_name}.pptx"

        logger.info(f"Converting SVG to PPTX: {svg_path} -> {output_path}")

        # Use SVG2PPTX conversion
        convert_svg_to_pptx(str(svg_path), str(output_path))

        if not output_path.exists():
            raise RuntimeError(f"PPTX conversion failed: {output_path}")

        logger.info(f"PPTX created: {output_path}")
        return output_path

    async def _convert_pptx_to_slides(self, pptx_path: Path, test_name: str) -> ConversionResult:
        """Convert PPTX to Google Slides."""
        logger.info(f"Converting PPTX to Google Slides: {pptx_path}")

        result = self.converter.convert_pptx_full_workflow(
            pptx_path,
            folder_id=self.config.drive_folder_id,
            custom_name=f"Visual_Test_{test_name}_{self._test_session_id}",
            delete_original_pptx=True
        )

        if not result.success:
            raise RuntimeError(f"Slides conversion failed: {result.error_message}")

        logger.info(f"Google Slides created: {result.presentation_id}")
        return result

    async def _publish_presentation(self, presentation_id: str) -> PublishedPresentation:
        """Publish presentation for screenshot access."""
        logger.info(f"Publishing presentation: {presentation_id}")

        published = self.publisher.publish_presentation(presentation_id)

        logger.info(f"Presentation published: {published.public_url}")
        return published

    async def _capture_screenshots(self, presentation_id: str, test_name: str) -> List[ScreenshotResult]:
        """Capture screenshots of all slides."""
        output_dir = self.config.screenshots_dir / test_name

        logger.info(f"Capturing screenshots: {presentation_id}")

        screenshots = await self.screenshot_capture.capture_all_slides(
            presentation_id,
            output_dir,
            method=self.config.screenshot_method,
            format=self.config.screenshot_format
        )

        successful = sum(1 for s in screenshots if s.success)
        logger.info(f"Screenshot capture completed: {successful}/{len(screenshots)} successful")

        return screenshots

    async def _validate_screenshots(self, screenshots: List[ScreenshotResult],
                                  test_name: str) -> Optional[ValidationReport]:
        """Validate screenshots against reference images."""
        try:
            # Check if reference images exist
            reference_dir = self.config.references_dir / test_name
            if not reference_dir.exists():
                logger.info(f"No reference images found for {test_name}, skipping validation")
                return None

            # Get reference images
            reference_images = sorted(reference_dir.glob(f"*.{self.config.screenshot_format}"))
            if not reference_images:
                logger.info(f"No reference images found in {reference_dir}")
                return None

            # Get test images
            test_images = []
            for screenshot in screenshots:
                if screenshot.success and screenshot.output_path:
                    test_images.append(screenshot.output_path)

            test_images.sort()

            if len(reference_images) != len(test_images):
                logger.warning(f"Image count mismatch: {len(reference_images)} references vs {len(test_images)} test images")

            # Validate
            output_dir = self.config.reports_dir / test_name
            validation_report = self.validator.validate_presentation(
                reference_images, test_images, output_dir
            )

            logger.info(f"Validation completed: {validation_report.threshold_passed}/{validation_report.total_comparisons} passed")
            return validation_report

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return None

    async def _cleanup_test_resources(self, presentation_id: str, pptx_path: Path):
        """Cleanup test resources."""
        try:
            # Delete Google Slides presentation
            if presentation_id:
                self.converter.delete_presentation(presentation_id)
                logger.info(f"Deleted presentation: {presentation_id}")

            # Delete temporary PPTX
            if pptx_path and pptx_path.exists():
                pptx_path.unlink()
                logger.info(f"Deleted temporary PPTX: {pptx_path}")

        except Exception as e:
            logger.warning(f"Cleanup error: {e}")

    async def _generate_batch_report(self, results: List[TestResult]):
        """Generate comprehensive batch test report."""
        try:
            report_path = self.config.reports_dir / f"batch_report_{self._test_session_id}.json"

            # Ensure reports directory exists
            self.config.reports_dir.mkdir(parents=True, exist_ok=True)

            # Create report data
            report_data = {
                'session_id': self._test_session_id,
                'generated_at': datetime.now().isoformat(),
                'config': {
                    'validation_tolerance': self.config.validation_tolerance,
                    'screenshot_method': self.config.screenshot_method,
                    'cleanup_after_test': self.config.cleanup_after_test
                },
                'summary': {
                    'total_tests': len(results),
                    'successful_tests': sum(1 for r in results if r.success),
                    'failed_tests': sum(1 for r in results if not r.success),
                    'total_time': sum(r.total_time for r in results)
                },
                'results': []
            }

            # Add individual test results
            for result in results:
                result_data = {
                    'success': result.success,
                    'test_name': result.test_name,
                    'svg_path': str(result.svg_path),
                    'pptx_path': str(result.pptx_path) if result.pptx_path else None,
                    'presentation_id': result.presentation_id,
                    'public_url': result.public_url,
                    'error_message': result.error_message,
                    'total_time': result.total_time,
                    'screenshot_count': len(result.screenshot_results),
                    'successful_screenshots': sum(1 for s in result.screenshot_results if s.success)
                }

                # Add validation summary if available
                if result.validation_report:
                    result_data['validation'] = {
                        'total_comparisons': result.validation_report.total_comparisons,
                        'threshold_passed': result.validation_report.threshold_passed,
                        'average_similarity': result.validation_report.average_similarity
                    }

                report_data['results'].append(result_data)

            # Save report
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2)

            logger.info(f"Batch report saved: {report_path}")

        except Exception as e:
            logger.error(f"Failed to generate batch report: {e}")

    def _setup_directories(self):
        """Set up required directories."""
        directories = [
            self.config.screenshots_dir,
            self.config.references_dir,
            self.config.reports_dir,
            self.config.temp_dir
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Directory ensured: {directory}")

    def __del__(self):
        """Cleanup on deletion."""
        try:
            # Run async cleanup if possible
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.cleanup())
            else:
                asyncio.run(self.cleanup())
        except:
            pass  # Ignore cleanup errors during deletion