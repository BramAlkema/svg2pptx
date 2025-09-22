#!/usr/bin/env python3
"""
Google Slides Screenshot Capture Module

Captures screenshots of Google Slides presentations using both the Google Slides API
thumbnail endpoint and Playwright browser automation for high-quality visual testing.
"""

import os
import io
import time
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple
from dataclasses import dataclass
from datetime import datetime

# Google API imports
try:
    from googleapiclient.errors import HttpError
    import requests
    GOOGLE_APIS_AVAILABLE = True
except ImportError:
    GOOGLE_APIS_AVAILABLE = False

# Playwright imports
try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# PIL for image processing
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from .authenticator import GoogleSlidesAuthenticator

logger = logging.getLogger(__name__)


@dataclass
class ScreenshotResult:
    """Result of screenshot capture operation."""
    success: bool
    slide_id: str
    output_path: Optional[Path] = None
    file_size: int = 0
    dimensions: Tuple[int, int] = (0, 0)
    capture_time: float = 0.0
    method: str = "unknown"
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class CaptureMethod:
    """Screenshot capture methods."""
    API = "api"
    PLAYWRIGHT = "playwright"
    HYBRID = "hybrid"  # API first, fallback to Playwright


class ImageFormat:
    """Supported image formats."""
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"


class SlidesScreenshotCapture:
    """Capture screenshots of Google Slides."""

    def __init__(self, auth: GoogleSlidesAuthenticator):
        """
        Initialize screenshot capture.

        Args:
            auth: Authenticated GoogleSlidesAuthenticator instance
        """
        if not GOOGLE_APIS_AVAILABLE:
            raise ImportError("Google API libraries not available")

        if not auth.is_authenticated:
            raise ValueError("Authenticator must be authenticated before use")

        self.auth = auth
        self.drive_service = auth.get_drive_service()
        self.slides_service = auth.get_slides_service()

        # Browser instance for Playwright
        self._browser = None
        self._playwright = None

        logger.info("SlidesScreenshotCapture initialized")

    async def capture_slide_as_image(self, presentation_id: str, slide_id: str,
                                   output_path: Path,
                                   method: str = CaptureMethod.API,
                                   format: str = ImageFormat.PNG,
                                   size: str = "large") -> ScreenshotResult:
        """
        Capture individual slide as image.

        Args:
            presentation_id: Google Slides presentation ID
            slide_id: Specific slide ID to capture
            output_path: Output file path
            method: Capture method (api, playwright, hybrid)
            format: Image format (png, jpeg, webp)
            size: Image size (small, medium, large, xlarge)

        Returns:
            ScreenshotResult with capture details
        """
        start_time = time.time()
        result = ScreenshotResult(success=False, slide_id=slide_id, method=method)

        try:
            if method == CaptureMethod.API:
                success = await self._capture_via_api(
                    presentation_id, slide_id, output_path, format, size
                )
            elif method == CaptureMethod.PLAYWRIGHT:
                success = await self._capture_via_playwright(
                    presentation_id, slide_id, output_path, format
                )
            elif method == CaptureMethod.HYBRID:
                # Try API first, fallback to Playwright
                success = await self._capture_via_api(
                    presentation_id, slide_id, output_path, format, size
                )
                if not success:
                    logger.info("API capture failed, trying Playwright")
                    success = await self._capture_via_playwright(
                        presentation_id, slide_id, output_path, format
                    )
            else:
                raise ValueError(f"Unsupported capture method: {method}")

            if success and output_path.exists():
                result.success = True
                result.output_path = output_path
                result.file_size = output_path.stat().st_size

                # Get image dimensions if PIL is available
                if PIL_AVAILABLE:
                    try:
                        with Image.open(output_path) as img:
                            result.dimensions = img.size
                    except Exception as e:
                        logger.warning(f"Could not get image dimensions: {e}")

            result.capture_time = time.time() - start_time

            if result.success:
                logger.info(f"Screenshot captured: {slide_id} -> {output_path}")
            else:
                logger.error(f"Screenshot capture failed: {slide_id}")

            return result

        except Exception as e:
            result.error_message = str(e)
            result.capture_time = time.time() - start_time
            logger.error(f"Screenshot capture error: {e}")
            return result

    async def capture_all_slides(self, presentation_id: str, output_dir: Path,
                               method: str = CaptureMethod.API,
                               format: str = ImageFormat.PNG,
                               size: str = "large",
                               progress_callback: Optional[callable] = None) -> List[ScreenshotResult]:
        """
        Capture all slides in presentation.

        Args:
            presentation_id: Google Slides presentation ID
            output_dir: Output directory for screenshots
            method: Capture method
            format: Image format
            size: Image size
            progress_callback: Optional progress callback

        Returns:
            List of ScreenshotResult objects
        """
        try:
            # Get presentation structure
            presentation = self.slides_service.presentations().get(
                presentationId=presentation_id
            ).execute()

            slides = presentation.get('slides', [])
            total_slides = len(slides)

            if total_slides == 0:
                logger.warning(f"No slides found in presentation {presentation_id}")
                return []

            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)

            results = []
            logger.info(f"Capturing {total_slides} slides from {presentation_id}")

            for i, slide in enumerate(slides):
                slide_id = slide['objectId']

                if progress_callback:
                    progress_callback(i, total_slides, slide_id)

                # Generate output filename
                output_filename = f"slide_{i+1:03d}_{slide_id}.{format}"
                output_path = output_dir / output_filename

                # Capture screenshot
                result = await self.capture_slide_as_image(
                    presentation_id, slide_id, output_path, method, format, size
                )

                results.append(result)

                if result.success:
                    logger.info(f"Captured slide {i+1}/{total_slides}: {slide_id}")
                else:
                    logger.warning(f"Failed slide {i+1}/{total_slides}: {slide_id}")

            successful = sum(1 for r in results if r.success)
            logger.info(f"Slide capture completed: {successful}/{total_slides} successful")

            return results

        except Exception as e:
            logger.error(f"Failed to capture all slides: {e}")
            return []

    async def capture_with_playwright(self, published_url: str, output_path: Path,
                                    viewport_size: Tuple[int, int] = (1920, 1080),
                                    wait_time: float = 3.0,
                                    full_page: bool = False) -> ScreenshotResult:
        """
        Alternative: Use Playwright for high-quality screenshots.

        Args:
            published_url: Public URL of the presentation
            output_path: Output file path
            viewport_size: Browser viewport size
            wait_time: Time to wait for page load
            full_page: Whether to capture full page

        Returns:
            ScreenshotResult
        """
        start_time = time.time()
        result = ScreenshotResult(
            success=False,
            slide_id="playwright_capture",
            method=CaptureMethod.PLAYWRIGHT
        )

        if not PLAYWRIGHT_AVAILABLE:
            result.error_message = "Playwright not available"
            return result

        try:
            # Initialize Playwright if needed
            if not self._playwright:
                await self._init_playwright()

            page = await self._get_browser_page(viewport_size)

            # Navigate to presentation
            await page.goto(published_url, wait_until="networkidle")

            # Wait for content to load
            await asyncio.sleep(wait_time)

            # Additional wait for Google Slides specific elements
            try:
                await page.wait_for_selector('[data-id="presentation-viewer"]', timeout=10000)
            except:
                logger.warning("Could not find presentation viewer element")

            # Take screenshot
            screenshot_options = {
                'path': str(output_path),
                'full_page': full_page
            }

            await page.screenshot(**screenshot_options)

            if output_path.exists():
                result.success = True
                result.output_path = output_path
                result.file_size = output_path.stat().st_size

                # Get dimensions
                if PIL_AVAILABLE:
                    try:
                        with Image.open(output_path) as img:
                            result.dimensions = img.size
                    except Exception as e:
                        logger.warning(f"Could not get image dimensions: {e}")

            result.capture_time = time.time() - start_time
            logger.info(f"Playwright screenshot captured: {output_path}")

            return result

        except Exception as e:
            result.error_message = str(e)
            result.capture_time = time.time() - start_time
            logger.error(f"Playwright screenshot error: {e}")
            return result

    async def batch_capture_presentations(self, presentation_urls: List[Dict[str, str]],
                                        output_base_dir: Path,
                                        method: str = CaptureMethod.HYBRID,
                                        progress_callback: Optional[callable] = None) -> Dict[str, List[ScreenshotResult]]:
        """
        Capture screenshots from multiple presentations.

        Args:
            presentation_urls: List of {'id': str, 'url': str} dictionaries
            output_base_dir: Base output directory
            method: Capture method
            progress_callback: Optional progress callback

        Returns:
            Dictionary mapping presentation IDs to their screenshot results
        """
        results = {}
        total_presentations = len(presentation_urls)

        logger.info(f"Starting batch capture of {total_presentations} presentations")

        for i, presentation_info in enumerate(presentation_urls):
            presentation_id = presentation_info['id']

            try:
                if progress_callback:
                    progress_callback(i, total_presentations, presentation_id)

                # Create output directory for this presentation
                presentation_dir = output_base_dir / f"presentation_{presentation_id}"
                presentation_dir.mkdir(parents=True, exist_ok=True)

                # Capture all slides
                capture_results = await self.capture_all_slides(
                    presentation_id, presentation_dir, method
                )

                results[presentation_id] = capture_results

                successful = sum(1 for r in capture_results if r.success)
                logger.info(f"Batch {i+1}/{total_presentations}: {presentation_id} - {successful} slides captured")

            except Exception as e:
                logger.error(f"Batch capture failed for {presentation_id}: {e}")
                results[presentation_id] = []

        return results

    async def _capture_via_api(self, presentation_id: str, slide_id: str,
                             output_path: Path, format: str, size: str) -> bool:
        """Capture using Google Slides API thumbnail endpoint."""
        try:
            # Get slide thumbnail via API
            thumbnail_request = self.slides_service.presentations().pages().getThumbnail(
                presentationId=presentation_id,
                pageObjectId=slide_id,
                thumbnailProperties_thumbnailSize=size.upper(),
                thumbnailProperties_mimeType=f"image/{format}"
            )

            thumbnail_response = thumbnail_request.execute()
            content_url = thumbnail_response.get('contentUrl')

            if not content_url:
                logger.error("No content URL in thumbnail response")
                return False

            # Download image
            response = requests.get(content_url, timeout=30)
            response.raise_for_status()

            # Save image
            with open(output_path, 'wb') as f:
                f.write(response.content)

            logger.info(f"API screenshot saved: {output_path}")
            return True

        except HttpError as e:
            logger.error(f"API screenshot failed: {e}")
            return False
        except Exception as e:
            logger.error(f"API screenshot error: {e}")
            return False

    async def _capture_via_playwright(self, presentation_id: str, slide_id: str,
                                    output_path: Path, format: str) -> bool:
        """Capture using Playwright browser automation."""
        try:
            if not PLAYWRIGHT_AVAILABLE:
                logger.error("Playwright not available")
                return False

            # Initialize Playwright if needed
            if not self._playwright:
                await self._init_playwright()

            # Get direct slide URL
            slide_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit#slide=id.{slide_id}"

            page = await self._get_browser_page()

            # Navigate to specific slide
            await page.goto(slide_url, wait_until="networkidle")

            # Wait for slide to load
            await asyncio.sleep(2.0)

            # Try to select the slide canvas
            try:
                await page.wait_for_selector('[data-id="slide-canvas"]', timeout=10000)
                slide_element = await page.query_selector('[data-id="slide-canvas"]')

                if slide_element:
                    await slide_element.screenshot(path=str(output_path))
                else:
                    # Fallback to full page
                    await page.screenshot(path=str(output_path))

            except:
                # Final fallback
                await page.screenshot(path=str(output_path))

            logger.info(f"Playwright screenshot saved: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Playwright screenshot error: {e}")
            return False

    async def _init_playwright(self):
        """Initialize Playwright browser."""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright not available")

        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            logger.info("Playwright browser initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            raise

    async def _get_browser_page(self, viewport_size: Tuple[int, int] = (1920, 1080)) -> Page:
        """Get a browser page with specified viewport."""
        if not self._browser:
            await self._init_playwright()

        context = await self._browser.new_context(
            viewport={'width': viewport_size[0], 'height': viewport_size[1]}
        )
        page = await context.new_page()
        return page

    async def cleanup(self):
        """Cleanup Playwright resources."""
        try:
            if self._browser:
                await self._browser.close()
                self._browser = None

            if self._playwright:
                await self._playwright.stop()
                self._playwright = None

            logger.info("Playwright resources cleaned up")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def __del__(self):
        """Cleanup on deletion."""
        if self._browser or self._playwright:
            try:
                # Run cleanup in event loop if available
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.cleanup())
                else:
                    asyncio.run(self.cleanup())
            except:
                pass  # Ignore cleanup errors during deletion