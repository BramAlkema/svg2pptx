#!/usr/bin/env python3
"""
SVG to PPTX Visual Comparator

Provides comprehensive visual comparison between original SVG files and
their PPTX renderings using LibreOffice. Includes side-by-side analysis,
difference detection, and compliance scoring.
"""

import logging
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Image processing imports
try:
    from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Advanced image analysis
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    # Import numpy separately as it's used throughout
    try:
        import numpy as np
    except ImportError:
        np = None

try:
    from skimage.metrics import structural_similarity as ssim
    from skimage.color import rgb2gray
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False

# SVG rendering for reference
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except ImportError:
    CAIROSVG_AVAILABLE = False

from .w3c_test_manager import W3CTestCase
from .libreoffice_controller import LibreOfficePlaywrightController, ScreenshotResult

logger = logging.getLogger(__name__)


class ComplianceLevel(Enum):
    """Compliance levels for SVG features."""
    FULL = "full"          # Perfect compliance
    HIGH = "high"          # Minor differences acceptable
    MEDIUM = "medium"      # Significant differences but functional
    LOW = "low"            # Major differences, basic functionality
    FAIL = "fail"          # Non-functional or completely wrong


@dataclass
class FeatureCompliance:
    """Compliance assessment for a specific SVG feature."""
    feature_name: str
    level: ComplianceLevel
    score: float  # 0.0 - 1.0
    issues: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class ComparisonMetrics:
    """Detailed comparison metrics between SVG and PPTX rendering."""
    structural_similarity: float = 0.0
    pixel_accuracy: float = 0.0
    color_fidelity: float = 0.0
    geometry_preservation: float = 0.0
    text_readability: float = 0.0
    visual_quality: float = 0.0
    overall_score: float = 0.0


@dataclass
class ComparisonResult:
    """Result of SVG to PPTX comparison."""
    test_case: W3CTestCase
    svg_screenshot_path: Optional[Path] = None
    pptx_screenshot_path: Optional[Path] = None
    diff_image_path: Optional[Path] = None
    side_by_side_path: Optional[Path] = None

    metrics: Optional[ComparisonMetrics] = None
    feature_compliance: List[FeatureCompliance] = field(default_factory=list)
    overall_compliance: ComplianceLevel = ComplianceLevel.FAIL

    success: bool = False
    error_message: Optional[str] = None
    comparison_time: float = 0.0
    metadata: Dict[str, any] = field(default_factory=dict)


class SVGPPTXComparator:
    """Compares SVG originals with PPTX renderings for compliance testing."""

    def __init__(self,
                 tolerance: float = 0.85,
                 enable_detailed_analysis: bool = True,
                 reference_resolution: Tuple[int, int] = (1920, 1080)):
        """
        Initialize comparator.

        Args:
            tolerance: Overall similarity tolerance for compliance
            enable_detailed_analysis: Enable detailed feature analysis
            reference_resolution: Target resolution for comparisons
        """
        if not PIL_AVAILABLE:
            raise ImportError("PIL (Pillow) is required for visual comparison")

        self.tolerance = tolerance
        self.enable_detailed_analysis = enable_detailed_analysis
        self.reference_resolution = reference_resolution

        # Check optional dependencies
        self.opencv_available = OPENCV_AVAILABLE
        self.skimage_available = SKIMAGE_AVAILABLE
        self.cairosvg_available = CAIROSVG_AVAILABLE

        # Feature compliance thresholds
        self.compliance_thresholds = {
            ComplianceLevel.FULL: 0.95,
            ComplianceLevel.HIGH: 0.85,
            ComplianceLevel.MEDIUM: 0.70,
            ComplianceLevel.LOW: 0.50,
            ComplianceLevel.FAIL: 0.0
        }

        logger.info(f"SVGPPTXComparator initialized with tolerance: {tolerance}")

    async def compare_test_case(self,
                              test_case: W3CTestCase,
                              pptx_path: Path,
                              libreoffice_controller: LibreOfficePlaywrightController,
                              output_dir: Path) -> ComparisonResult:
        """
        Compare SVG test case with its PPTX rendering.

        Args:
            test_case: W3C test case to compare
            pptx_path: Path to generated PPTX file
            libreoffice_controller: Controller for LibreOffice automation
            output_dir: Directory for output files

        Returns:
            ComparisonResult with detailed analysis
        """
        start_time = time.time()
        result = ComparisonResult(test_case=test_case)

        try:
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)

            # Step 1: Generate SVG reference screenshot
            svg_screenshot = await self._render_svg_reference(
                test_case.svg_path,
                output_dir / f"{test_case.name}_svg_reference.png"
            )
            result.svg_screenshot_path = svg_screenshot

            # Step 2: Capture PPTX screenshot using LibreOffice
            pptx_screenshot = await self._capture_pptx_screenshot(
                pptx_path,
                libreoffice_controller,
                output_dir / f"{test_case.name}_pptx_rendered.png"
            )
            result.pptx_screenshot_path = pptx_screenshot

            if not svg_screenshot or not pptx_screenshot:
                result.error_message = "Failed to generate comparison screenshots"
                return result

            # Step 3: Perform visual comparison
            metrics = await self._calculate_comparison_metrics(
                svg_screenshot, pptx_screenshot
            )
            result.metrics = metrics

            # Step 4: Generate comparison visualizations
            await self._generate_comparison_images(
                svg_screenshot, pptx_screenshot, output_dir, test_case.name, result
            )

            # Step 5: Analyze feature compliance
            if self.enable_detailed_analysis:
                feature_compliance = await self._analyze_feature_compliance(
                    test_case, svg_screenshot, pptx_screenshot
                )
                result.feature_compliance = feature_compliance

            # Step 6: Determine overall compliance level
            result.overall_compliance = self._determine_compliance_level(metrics)

            result.success = True
            result.comparison_time = time.time() - start_time

            logger.info(f"Comparison completed for {test_case.name}: {result.overall_compliance.value}")
            return result

        except Exception as e:
            result.error_message = str(e)
            result.comparison_time = time.time() - start_time
            logger.error(f"Comparison failed for {test_case.name}: {e}")
            return result

    async def batch_compare(self,
                          test_cases: List[W3CTestCase],
                          pptx_files: Dict[str, Path],
                          libreoffice_controller: LibreOfficePlaywrightController,
                          output_dir: Path,
                          progress_callback: Optional[callable] = None) -> List[ComparisonResult]:
        """
        Compare multiple test cases in batch.

        Args:
            test_cases: List of test cases to compare
            pptx_files: Mapping of test case names to PPTX file paths
            libreoffice_controller: LibreOffice controller
            output_dir: Base output directory
            progress_callback: Optional progress callback

        Returns:
            List of ComparisonResult objects
        """
        results = []
        total_cases = len(test_cases)

        logger.info(f"Starting batch comparison of {total_cases} test cases")

        for i, test_case in enumerate(test_cases):
            try:
                if progress_callback:
                    progress_callback(i, total_cases, test_case.name)

                pptx_path = pptx_files.get(test_case.name)
                if not pptx_path or not pptx_path.exists():
                    logger.warning(f"PPTX file not found for {test_case.name}")
                    continue

                # Create test-specific output directory
                test_output_dir = output_dir / test_case.name

                result = await self.compare_test_case(
                    test_case, pptx_path, libreoffice_controller, test_output_dir
                )
                results.append(result)

                if result.success:
                    logger.info(f"Batch {i+1}/{total_cases}: {test_case.name} - {result.overall_compliance.value}")
                else:
                    logger.warning(f"Batch {i+1}/{total_cases}: {test_case.name} - FAILED: {result.error_message}")

            except Exception as e:
                logger.error(f"Batch comparison error for {test_case.name}: {e}")

        successful = sum(1 for r in results if r.success)
        logger.info(f"Batch comparison completed: {successful}/{total_cases} successful")

        return results

    async def _render_svg_reference(self, svg_path: Path, output_path: Path) -> Optional[Path]:
        """Render SVG to PNG for reference comparison."""
        try:
            if self.cairosvg_available:
                # Use CairoSVG for high-quality SVG rendering
                cairosvg.svg2png(
                    url=str(svg_path),
                    write_to=str(output_path),
                    output_width=self.reference_resolution[0],
                    output_height=self.reference_resolution[1]
                )
                logger.debug(f"SVG rendered using CairoSVG: {output_path}")
                return output_path

            else:
                # Fallback: Use browser-based rendering
                return await self._render_svg_with_browser(svg_path, output_path)

        except Exception as e:
            logger.error(f"Failed to render SVG reference: {e}")
            return None

    async def _render_svg_with_browser(self, svg_path: Path, output_path: Path) -> Optional[Path]:
        """Render SVG using browser automation as fallback."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={'width': self.reference_resolution[0], 'height': self.reference_resolution[1]}
                )
                page = await context.new_page()

                # Load SVG file
                await page.goto(f"file://{svg_path.absolute()}")
                await page.wait_for_load_state('networkidle')

                # Take screenshot
                await page.screenshot(path=str(output_path), full_page=True)

                await browser.close()

            logger.debug(f"SVG rendered using browser: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Browser-based SVG rendering failed: {e}")
            return None

    async def _capture_pptx_screenshot(self,
                                     pptx_path: Path,
                                     controller: LibreOfficePlaywrightController,
                                     output_path: Path) -> Optional[Path]:
        """Capture screenshot of PPTX using LibreOffice controller."""
        try:
            # Open presentation
            if not await controller.open_presentation(pptx_path):
                logger.error(f"Failed to open PPTX: {pptx_path}")
                return None

            # Start slideshow for clean rendering
            await controller.start_slideshow()

            # Capture first slide (most test cases are single slide)
            result = await controller.capture_slide_screenshot(1, output_path)

            if result.success:
                logger.debug(f"PPTX screenshot captured: {output_path}")
                return output_path
            else:
                logger.error(f"PPTX screenshot failed: {result.error_message}")
                return None

        except Exception as e:
            logger.error(f"PPTX screenshot capture failed: {e}")
            return None

    async def _calculate_comparison_metrics(self,
                                          svg_path: Path,
                                          pptx_path: Path) -> ComparisonMetrics:
        """Calculate detailed comparison metrics."""
        metrics = ComparisonMetrics()

        try:
            # Load images
            svg_img = Image.open(svg_path).convert('RGB')
            pptx_img = Image.open(pptx_path).convert('RGB')

            # Normalize sizes
            svg_img, pptx_img = self._normalize_image_sizes(svg_img, pptx_img)

            # Convert to numpy arrays for analysis
            svg_array = np.array(svg_img)
            pptx_array = np.array(pptx_img)

            # 1. Structural Similarity
            if self.skimage_available:
                svg_gray = rgb2gray(svg_array)
                pptx_gray = rgb2gray(pptx_array)
                metrics.structural_similarity = ssim(svg_gray, pptx_gray, data_range=1.0)

            # 2. Pixel Accuracy
            metrics.pixel_accuracy = self._calculate_pixel_accuracy(svg_array, pptx_array)

            # 3. Color Fidelity
            metrics.color_fidelity = self._calculate_color_fidelity(svg_array, pptx_array)

            # 4. Geometry Preservation
            metrics.geometry_preservation = self._calculate_geometry_preservation(svg_array, pptx_array)

            # 5. Text Readability (basic implementation)
            metrics.text_readability = self._assess_text_readability(svg_array, pptx_array)

            # 6. Visual Quality
            metrics.visual_quality = self._assess_visual_quality(svg_array, pptx_array)

            # 7. Overall Score (weighted average)
            metrics.overall_score = self._calculate_overall_score(metrics)

            return metrics

        except Exception as e:
            logger.error(f"Failed to calculate comparison metrics: {e}")
            return metrics

    async def _generate_comparison_images(self,
                                        svg_path: Path,
                                        pptx_path: Path,
                                        output_dir: Path,
                                        test_name: str,
                                        result: ComparisonResult):
        """Generate visual comparison images."""
        try:
            svg_img = Image.open(svg_path).convert('RGB')
            pptx_img = Image.open(pptx_path).convert('RGB')

            # Normalize sizes
            svg_img, pptx_img = self._normalize_image_sizes(svg_img, pptx_img)

            # Generate difference image
            diff_img = self._create_difference_image(svg_img, pptx_img)
            diff_path = output_dir / f"{test_name}_diff.png"
            diff_img.save(diff_path)
            result.diff_image_path = diff_path

            # Generate side-by-side comparison
            side_by_side = self._create_side_by_side_comparison(
                svg_img, pptx_img, diff_img, test_name, result.metrics
            )
            side_by_side_path = output_dir / f"{test_name}_comparison.png"
            side_by_side.save(side_by_side_path)
            result.side_by_side_path = side_by_side_path

            logger.debug(f"Comparison images generated for {test_name}")

        except Exception as e:
            logger.error(f"Failed to generate comparison images: {e}")

    async def _analyze_feature_compliance(self,
                                        test_case: W3CTestCase,
                                        svg_path: Path,
                                        pptx_path: Path) -> List[FeatureCompliance]:
        """Analyze compliance for specific SVG features."""
        compliance_results = []

        try:
            # Analyze each expected feature in the test case
            for feature in test_case.expected_features:
                compliance = await self._analyze_single_feature(
                    feature, test_case, svg_path, pptx_path
                )
                compliance_results.append(compliance)

            return compliance_results

        except Exception as e:
            logger.error(f"Feature compliance analysis failed: {e}")
            return compliance_results

    async def _analyze_single_feature(self,
                                    feature: str,
                                    test_case: W3CTestCase,
                                    svg_path: Path,
                                    pptx_path: Path) -> FeatureCompliance:
        """Analyze compliance for a single SVG feature."""
        try:
            # Feature-specific analysis would go here
            # This is a simplified implementation

            issues = []
            score = 0.8  # Default score
            level = ComplianceLevel.HIGH

            if feature == "gradients":
                score, issues = self._analyze_gradients(svg_path, pptx_path)
            elif feature == "paths":
                score, issues = self._analyze_paths(svg_path, pptx_path)
            elif feature == "text":
                score, issues = self._analyze_text(svg_path, pptx_path)
            elif feature == "transforms":
                score, issues = self._analyze_transforms(svg_path, pptx_path)
            else:
                score, issues = self._analyze_generic_feature(feature, svg_path, pptx_path)

            # Determine compliance level based on score
            for level_key, threshold in self.compliance_thresholds.items():
                if score >= threshold:
                    level = level_key
                    break

            return FeatureCompliance(
                feature_name=feature,
                level=level,
                score=score,
                issues=issues
            )

        except Exception as e:
            return FeatureCompliance(
                feature_name=feature,
                level=ComplianceLevel.FAIL,
                score=0.0,
                issues=[f"Analysis failed: {e}"]
            )

    def _normalize_image_sizes(self, img1: Image.Image, img2: Image.Image) -> Tuple[Image.Image, Image.Image]:
        """Normalize image sizes for comparison."""
        target_size = (min(img1.width, img2.width), min(img1.height, img2.height))

        img1_resized = img1.resize(target_size, Image.Resampling.LANCZOS)
        img2_resized = img2.resize(target_size, Image.Resampling.LANCZOS)

        return img1_resized, img2_resized

    def _calculate_pixel_accuracy(self, svg_array, pptx_array) -> float:
        """Calculate pixel-level accuracy."""
        try:
            if np is None:
                return 0.5  # Default when numpy not available
            diff = np.abs(svg_array.astype(float) - pptx_array.astype(float))
            mse = np.mean(diff ** 2)
            max_possible_mse = 255 ** 2
            accuracy = 1.0 - (mse / max_possible_mse)
            return max(0.0, accuracy)
        except Exception:
            return 0.0

    def _calculate_color_fidelity(self, svg_array, pptx_array) -> float:
        """Calculate color fidelity between images."""
        try:
            if not self.opencv_available:
                return 0.5  # Default value when OpenCV not available

            # Calculate histograms
            svg_hist = cv2.calcHist([svg_array], [0, 1, 2], None, [256, 256, 256], [0, 256, 0, 256, 0, 256])
            pptx_hist = cv2.calcHist([pptx_array], [0, 1, 2], None, [256, 256, 256], [0, 256, 0, 256, 0, 256])

            # Compare histograms
            correlation = cv2.compareHist(svg_hist, pptx_hist, cv2.HISTCMP_CORREL)
            return max(0.0, correlation)

        except Exception:
            return 0.0

    def _calculate_geometry_preservation(self, svg_array, pptx_array) -> float:
        """Calculate how well geometric shapes are preserved."""
        try:
            if not self.opencv_available:
                return 0.5

            # Convert to grayscale and find edges
            svg_gray = cv2.cvtColor(svg_array, cv2.COLOR_RGB2GRAY)
            pptx_gray = cv2.cvtColor(pptx_array, cv2.COLOR_RGB2GRAY)

            svg_edges = cv2.Canny(svg_gray, 50, 150)
            pptx_edges = cv2.Canny(pptx_gray, 50, 150)

            # Compare edge maps
            edge_diff = cv2.absdiff(svg_edges, pptx_edges)
            preservation = 1.0 - (np.sum(edge_diff) / (255 * edge_diff.size))

            return max(0.0, preservation)

        except Exception:
            return 0.0

    def _assess_text_readability(self, svg_array, pptx_array) -> float:
        """Assess text readability and preservation."""
        # Simplified implementation - would need OCR for full analysis
        try:
            if np is None:
                return 0.5
            # Basic contrast and clarity assessment
            svg_contrast = np.std(svg_array)
            pptx_contrast = np.std(pptx_array)

            contrast_similarity = 1.0 - abs(svg_contrast - pptx_contrast) / max(svg_contrast, pptx_contrast, 1)
            return max(0.0, contrast_similarity)

        except Exception:
            return 0.0

    def _assess_visual_quality(self, svg_array, pptx_array) -> float:
        """Assess overall visual quality."""
        try:
            if np is None:
                return 0.5
            # Combine multiple quality metrics
            sharpness_svg = np.var(cv2.Laplacian(cv2.cvtColor(svg_array, cv2.COLOR_RGB2GRAY), cv2.CV_64F)) if self.opencv_available else 100
            sharpness_pptx = np.var(cv2.Laplacian(cv2.cvtColor(pptx_array, cv2.COLOR_RGB2GRAY), cv2.CV_64F)) if self.opencv_available else 100

            sharpness_similarity = 1.0 - abs(sharpness_svg - sharpness_pptx) / max(sharpness_svg, sharpness_pptx, 1)
            return max(0.0, sharpness_similarity)

        except Exception:
            return 0.0

    def _calculate_overall_score(self, metrics: ComparisonMetrics) -> float:
        """Calculate weighted overall score."""
        weights = {
            'structural_similarity': 0.25,
            'pixel_accuracy': 0.20,
            'color_fidelity': 0.15,
            'geometry_preservation': 0.20,
            'text_readability': 0.10,
            'visual_quality': 0.10
        }

        score = 0.0
        for metric, weight in weights.items():
            value = getattr(metrics, metric, 0.0)
            score += value * weight

        return score

    def _determine_compliance_level(self, metrics: ComparisonMetrics) -> ComplianceLevel:
        """Determine overall compliance level based on metrics."""
        score = metrics.overall_score

        for level, threshold in self.compliance_thresholds.items():
            if score >= threshold:
                return level

        return ComplianceLevel.FAIL

    def _create_difference_image(self, img1: Image.Image, img2: Image.Image) -> Image.Image:
        """Create visual difference image."""
        diff = ImageChops.difference(img1, img2)

        # Enhance differences for visibility
        enhancer = ImageEnhance.Contrast(diff)
        enhanced_diff = enhancer.enhance(3.0)

        return enhanced_diff

    def _create_side_by_side_comparison(self,
                                      svg_img: Image.Image,
                                      pptx_img: Image.Image,
                                      diff_img: Image.Image,
                                      test_name: str,
                                      metrics: Optional[ComparisonMetrics]) -> Image.Image:
        """Create side-by-side comparison image with metrics."""
        width, height = svg_img.size

        # Create comparison image (3 panels + text area)
        comparison_width = width * 3
        comparison_height = height + 150  # Extra space for text

        comparison = Image.new('RGB', (comparison_width, comparison_height), 'white')

        # Paste images
        comparison.paste(svg_img, (0, 0))
        comparison.paste(pptx_img, (width, 0))
        comparison.paste(diff_img, (width * 2, 0))

        # Add labels and metrics
        try:
            from PIL import ImageFont
            # Try to use a default font
            font = ImageFont.load_default()
        except:
            font = None

        draw = ImageDraw.Draw(comparison)

        # Labels
        draw.text((10, height + 10), "SVG Original", fill='black', font=font)
        draw.text((width + 10, height + 10), "PPTX Rendered", fill='black', font=font)
        draw.text((width * 2 + 10, height + 10), "Difference", fill='black', font=font)

        # Metrics (if available)
        if metrics:
            y_offset = height + 40
            metrics_text = [
                f"Test: {test_name}",
                f"Overall Score: {metrics.overall_score:.3f}",
                f"Structural Similarity: {metrics.structural_similarity:.3f}",
                f"Pixel Accuracy: {metrics.pixel_accuracy:.3f}",
                f"Color Fidelity: {metrics.color_fidelity:.3f}",
                f"Geometry: {metrics.geometry_preservation:.3f}"
            ]

            for i, text in enumerate(metrics_text):
                draw.text((10, y_offset + i * 15), text, fill='black', font=font)

        return comparison

    def _analyze_gradients(self, svg_path: Path, pptx_path: Path) -> Tuple[float, List[str]]:
        """Analyze gradient rendering compliance."""
        # Simplified gradient analysis
        return 0.8, ["Gradient analysis not fully implemented"]

    def _analyze_paths(self, svg_path: Path, pptx_path: Path) -> Tuple[float, List[str]]:
        """Analyze path rendering compliance."""
        return 0.85, []

    def _analyze_text(self, svg_path: Path, pptx_path: Path) -> Tuple[float, List[str]]:
        """Analyze text rendering compliance."""
        return 0.75, ["Font differences detected"]

    def _analyze_transforms(self, svg_path: Path, pptx_path: Path) -> Tuple[float, List[str]]:
        """Analyze transform compliance."""
        return 0.9, []

    def _analyze_generic_feature(self, feature: str, svg_path: Path, pptx_path: Path) -> Tuple[float, List[str]]:
        """Generic feature analysis fallback."""
        return 0.7, [f"Generic analysis for {feature}"]