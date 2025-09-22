"""
Google Slides Visual Testing Integration

This module provides automated visual testing capabilities by:
1. Converting PPTX files to Google Slides
2. Publishing presentations for viewing
3. Capturing screenshots for visual regression testing
4. Validating conversion accuracy between PPTX and Google Slides

Enables automated visual validation of the SVG to PPTX conversion pipeline
by leveraging Google Slides as a rendering engine for cross-platform verification.
"""

__version__ = "1.0.0"
__author__ = "SVG2PPTX Team"

from .authenticator import GoogleSlidesAuthenticator
from .slides_converter import SlidesConverter
from .publisher import SlidesPublisher
from .screenshot_capture import SlidesScreenshotCapture
from .visual_validator import VisualValidator
from .test_runner import GoogleSlidesTestRunner

__all__ = [
    "GoogleSlidesAuthenticator",
    "SlidesConverter",
    "SlidesPublisher",
    "SlidesScreenshotCapture",
    "VisualValidator",
    "GoogleSlidesTestRunner"
]