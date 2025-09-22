#!/usr/bin/env python3
"""
LibreOffice Playwright Controller

Controls LibreOffice Impress in headless mode using Playwright for automated
visual testing of PPTX presentations. Provides screenshot capture and
presentation manipulation capabilities.
"""

import os
import asyncio
import logging
import subprocess
import psutil
import signal
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime

# Playwright imports
try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class LibreOfficeConfig:
    """Configuration for LibreOffice automation."""
    headless: bool = True
    port: int = 8100
    user_profile_dir: Optional[Path] = None
    accept_connection: str = "socket,host=127.0.0.1,port=8100;urp;StarOffice.ServiceManager"
    additional_args: List[str] = None
    startup_timeout: int = 30
    screenshot_delay: float = 2.0
    page_transition_delay: float = 1.0

    def __post_init__(self):
        if self.additional_args is None:
            self.additional_args = []


@dataclass
class PresentationInfo:
    """Information about a loaded presentation."""
    file_path: Path
    title: str
    slide_count: int
    current_slide: int = 1
    is_slideshow: bool = False
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ScreenshotResult:
    """Result of screenshot capture."""
    success: bool
    slide_number: int
    output_path: Optional[Path] = None
    file_size: int = 0
    dimensions: Tuple[int, int] = (0, 0)
    error_message: Optional[str] = None
    capture_time: float = 0.0


class LibreOfficePlaywrightController:
    """Controls LibreOffice Impress using Playwright automation."""

    def __init__(self, config: Optional[LibreOfficeConfig] = None):
        """
        Initialize LibreOffice controller.

        Args:
            config: LibreOffice configuration
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright not available. Install with: pip install playwright")

        self.config = config or LibreOfficeConfig()
        self.process = None
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        # State tracking
        self.current_presentation: Optional[PresentationInfo] = None
        self.is_running = False

        logger.info("LibreOfficePlaywrightController initialized")

    async def start_libreoffice(self) -> bool:
        """
        Start LibreOffice in headless mode.

        Returns:
            True if successful
        """
        try:
            if self.is_running:
                logger.info("LibreOffice already running")
                return True

            # Kill any existing LibreOffice processes
            await self._kill_existing_processes()

            # Prepare command line arguments
            soffice_cmd = self._build_soffice_command()

            logger.info(f"Starting LibreOffice: {' '.join(soffice_cmd)}")

            # Start LibreOffice process
            self.process = subprocess.Popen(
                soffice_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False
            )

            # Wait for startup
            startup_success = await self._wait_for_startup()

            if startup_success:
                self.is_running = True
                logger.info(f"LibreOffice started successfully (PID: {self.process.pid})")
                return True
            else:
                logger.error("LibreOffice startup failed")
                await self.stop_libreoffice()
                return False

        except Exception as e:
            logger.error(f"Failed to start LibreOffice: {e}")
            return False

    async def start_browser(self, headless: bool = True) -> bool:
        """
        Start Playwright browser for automation.

        Args:
            headless: Whether to run browser in headless mode

        Returns:
            True if successful
        """
        try:
            if self.browser:
                logger.info("Browser already running")
                return True

            self.playwright = await async_playwright().start()

            # Launch browser with LibreOffice web interface support
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-extensions',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding'
                ]
            )

            # Create context with presentation-friendly settings
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            )

            # Create page
            self.page = await self.context.new_page()

            # Set longer timeouts for presentation loading
            self.page.set_default_timeout(60000)  # 60 seconds

            logger.info("Browser started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            return False

    async def open_presentation(self, pptx_path: Path) -> bool:
        """
        Open PPTX presentation in LibreOffice.

        Args:
            pptx_path: Path to PPTX file

        Returns:
            True if successful
        """
        try:
            if not pptx_path.exists():
                raise FileNotFoundError(f"PPTX file not found: {pptx_path}")

            if not self.is_running:
                if not await self.start_libreoffice():
                    return False

            if not self.browser:
                if not await self.start_browser():
                    return False

            # Convert to LibreOffice web interface URL
            file_url = f"file://{pptx_path.absolute()}"

            logger.info(f"Opening presentation: {pptx_path}")

            # Navigate to LibreOffice web interface
            # Note: This assumes LibreOffice Online or similar web interface
            # For desktop LibreOffice, we'll use file protocol
            await self.page.goto(file_url)

            # Wait for presentation to load
            await self._wait_for_presentation_load()

            # Extract presentation information
            presentation_info = await self._extract_presentation_info(pptx_path)
            self.current_presentation = presentation_info

            logger.info(f"Presentation opened: {presentation_info.title} ({presentation_info.slide_count} slides)")
            return True

        except Exception as e:
            logger.error(f"Failed to open presentation: {e}")
            return False

    async def start_slideshow(self) -> bool:
        """
        Start slideshow mode.

        Returns:
            True if successful
        """
        try:
            if not self.current_presentation:
                raise RuntimeError("No presentation loaded")

            logger.info("Starting slideshow mode")

            # Press F5 to start slideshow
            await self.page.keyboard.press('F5')

            # Wait for slideshow to start
            await asyncio.sleep(self.config.screenshot_delay)

            # Update presentation state
            self.current_presentation.is_slideshow = True
            self.current_presentation.current_slide = 1

            logger.info("Slideshow started")
            return True

        except Exception as e:
            logger.error(f"Failed to start slideshow: {e}")
            return False

    async def navigate_to_slide(self, slide_number: int) -> bool:
        """
        Navigate to specific slide.

        Args:
            slide_number: Target slide number (1-based)

        Returns:
            True if successful
        """
        try:
            if not self.current_presentation:
                raise RuntimeError("No presentation loaded")

            if slide_number < 1 or slide_number > self.current_presentation.slide_count:
                raise ValueError(f"Invalid slide number: {slide_number}")

            current = self.current_presentation.current_slide

            if current == slide_number:
                logger.debug(f"Already on slide {slide_number}")
                return True

            logger.info(f"Navigating from slide {current} to slide {slide_number}")

            if self.current_presentation.is_slideshow:
                # In slideshow mode, use keyboard navigation
                if slide_number > current:
                    # Navigate forward
                    for _ in range(slide_number - current):
                        await self.page.keyboard.press('ArrowRight')
                        await asyncio.sleep(self.config.page_transition_delay)
                else:
                    # Navigate backward
                    for _ in range(current - slide_number):
                        await self.page.keyboard.press('ArrowLeft')
                        await asyncio.sleep(self.config.page_transition_delay)
            else:
                # In edit mode, use Ctrl+G to go to slide
                await self.page.keyboard.press('Control+g')
                await asyncio.sleep(0.5)
                await self.page.keyboard.type(str(slide_number))
                await self.page.keyboard.press('Enter')
                await asyncio.sleep(self.config.page_transition_delay)

            # Update current slide
            self.current_presentation.current_slide = slide_number

            logger.info(f"Navigated to slide {slide_number}")
            return True

        except Exception as e:
            logger.error(f"Failed to navigate to slide {slide_number}: {e}")
            return False

    async def capture_slide_screenshot(self, slide_number: int, output_path: Path) -> ScreenshotResult:
        """
        Capture screenshot of specific slide.

        Args:
            slide_number: Slide number to capture
            output_path: Output file path

        Returns:
            ScreenshotResult
        """
        start_time = time.time()
        result = ScreenshotResult(success=False, slide_number=slide_number)

        try:
            if not self.current_presentation:
                raise RuntimeError("No presentation loaded")

            # Navigate to slide
            if not await self.navigate_to_slide(slide_number):
                raise RuntimeError(f"Failed to navigate to slide {slide_number}")

            # Wait for slide to stabilize
            await asyncio.sleep(self.config.screenshot_delay)

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Take screenshot
            await self.page.screenshot(
                path=str(output_path),
                full_page=True,
                type='png'
            )

            if output_path.exists():
                result.success = True
                result.output_path = output_path
                result.file_size = output_path.stat().st_size

                # Get image dimensions if possible
                try:
                    from PIL import Image
                    with Image.open(output_path) as img:
                        result.dimensions = img.size
                except ImportError:
                    logger.warning("PIL not available for image dimension detection")

            result.capture_time = time.time() - start_time

            logger.info(f"Screenshot captured for slide {slide_number}: {output_path}")
            return result

        except Exception as e:
            result.error_message = str(e)
            result.capture_time = time.time() - start_time
            logger.error(f"Failed to capture screenshot for slide {slide_number}: {e}")
            return result

    async def capture_all_slides(self, output_dir: Path,
                               filename_template: str = "slide_{:03d}.png") -> List[ScreenshotResult]:
        """
        Capture screenshots of all slides.

        Args:
            output_dir: Output directory
            filename_template: Template for filenames

        Returns:
            List of ScreenshotResult objects
        """
        if not self.current_presentation:
            logger.error("No presentation loaded")
            return []

        output_dir.mkdir(parents=True, exist_ok=True)
        results = []

        slide_count = self.current_presentation.slide_count
        logger.info(f"Capturing screenshots for {slide_count} slides")

        for slide_num in range(1, slide_count + 1):
            filename = filename_template.format(slide_num)
            output_path = output_dir / filename

            result = await self.capture_slide_screenshot(slide_num, output_path)
            results.append(result)

            if result.success:
                logger.info(f"Captured slide {slide_num}/{slide_count}")
            else:
                logger.warning(f"Failed to capture slide {slide_num}/{slide_count}: {result.error_message}")

        successful = sum(1 for r in results if r.success)
        logger.info(f"Screenshot capture completed: {successful}/{slide_count} successful")

        return results

    async def close_presentation(self) -> bool:
        """
        Close current presentation.

        Returns:
            True if successful
        """
        try:
            if not self.current_presentation:
                logger.info("No presentation to close")
                return True

            logger.info("Closing presentation")

            # Exit slideshow mode if active
            if self.current_presentation.is_slideshow:
                await self.page.keyboard.press('Escape')
                await asyncio.sleep(1)

            # Close document
            await self.page.keyboard.press('Control+w')
            await asyncio.sleep(1)

            self.current_presentation = None

            logger.info("Presentation closed")
            return True

        except Exception as e:
            logger.error(f"Failed to close presentation: {e}")
            return False

    async def stop_libreoffice(self) -> bool:
        """
        Stop LibreOffice process.

        Returns:
            True if successful
        """
        try:
            if self.process:
                logger.info("Stopping LibreOffice process")

                # Try graceful shutdown first
                try:
                    self.process.terminate()
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    self.process.kill()
                    self.process.wait()

                self.process = None

            # Kill any remaining LibreOffice processes
            await self._kill_existing_processes()

            self.is_running = False
            logger.info("LibreOffice stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to stop LibreOffice: {e}")
            return False

    async def stop_browser(self) -> bool:
        """
        Stop Playwright browser.

        Returns:
            True if successful
        """
        try:
            if self.page:
                await self.page.close()
                self.page = None

            if self.context:
                await self.context.close()
                self.context = None

            if self.browser:
                await self.browser.close()
                self.browser = None

            if self.playwright:
                await self.playwright.stop()
                self.playwright = None

            logger.info("Browser stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to stop browser: {e}")
            return False

    async def cleanup(self) -> bool:
        """
        Cleanup all resources.

        Returns:
            True if successful
        """
        success = True

        try:
            await self.close_presentation()
        except Exception as e:
            logger.warning(f"Error closing presentation during cleanup: {e}")
            success = False

        try:
            await self.stop_browser()
        except Exception as e:
            logger.warning(f"Error stopping browser during cleanup: {e}")
            success = False

        try:
            await self.stop_libreoffice()
        except Exception as e:
            logger.warning(f"Error stopping LibreOffice during cleanup: {e}")
            success = False

        return success

    def _build_soffice_command(self) -> List[str]:
        """Build LibreOffice command line."""
        cmd = ['soffice']

        if self.config.headless:
            cmd.append('--headless')

        cmd.extend([
            '--nologo',
            '--nolockcheck',
            '--nodefault',
            '--norestore',
            f'--accept={self.config.accept_connection}'
        ])

        if self.config.user_profile_dir:
            cmd.append(f'--env:UserInstallation=file://{self.config.user_profile_dir}')

        cmd.extend(self.config.additional_args)

        return cmd

    async def _wait_for_startup(self) -> bool:
        """Wait for LibreOffice to start up."""
        start_time = time.time()

        while time.time() - start_time < self.config.startup_timeout:
            if self.process.poll() is not None:
                # Process exited
                stdout, stderr = self.process.communicate()
                logger.error(f"LibreOffice process exited with code {self.process.returncode}")
                logger.error(f"stdout: {stdout.decode()}")
                logger.error(f"stderr: {stderr.decode()}")
                return False

            # Check if LibreOffice is responding
            try:
                # Simple connection test - this would need UNO bridge in real implementation
                await asyncio.sleep(1)
                # For now, just check if process is running
                if self.process and self.process.poll() is None:
                    await asyncio.sleep(2)  # Give it more time to fully start
                    return True
            except Exception:
                pass

            await asyncio.sleep(0.5)

        return False

    async def _wait_for_presentation_load(self) -> bool:
        """Wait for presentation to load in browser."""
        try:
            # Wait for page to be fully loaded
            await self.page.wait_for_load_state('networkidle')

            # Additional wait for presentation-specific elements
            # This would be customized based on the actual LibreOffice web interface
            await asyncio.sleep(3)

            return True

        except Exception as e:
            logger.warning(f"Error waiting for presentation load: {e}")
            return False

    async def _extract_presentation_info(self, pptx_path: Path) -> PresentationInfo:
        """Extract presentation information."""
        try:
            # For now, use basic info
            # In a real implementation, this would extract slide count from PPTX
            slide_count = await self._detect_slide_count()

            return PresentationInfo(
                file_path=pptx_path,
                title=pptx_path.stem,
                slide_count=slide_count,
                current_slide=1,
                is_slideshow=False
            )

        except Exception as e:
            logger.warning(f"Error extracting presentation info: {e}")
            return PresentationInfo(
                file_path=pptx_path,
                title=pptx_path.stem,
                slide_count=1,  # Default fallback
                current_slide=1,
                is_slideshow=False
            )

    async def _detect_slide_count(self) -> int:
        """Detect number of slides in presentation."""
        try:
            # This would be implemented based on the actual LibreOffice interface
            # For now, return a default value
            return 1

        except Exception:
            return 1

    async def _kill_existing_processes(self):
        """Kill any existing LibreOffice processes."""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and 'soffice' in proc.info['name'].lower():
                    try:
                        proc.kill()
                        logger.debug(f"Killed existing LibreOffice process: {proc.info['pid']}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
        except Exception as e:
            logger.warning(f"Error killing existing processes: {e}")

    def __del__(self):
        """Cleanup on deletion."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.cleanup())
            else:
                asyncio.run(self.cleanup())
        except:
            pass  # Ignore cleanup errors during deletion