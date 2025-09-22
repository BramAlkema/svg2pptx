#!/usr/bin/env python3
"""
Visual Validator Module

Compares and validates visual output between reference images and Google Slides screenshots.
Uses multiple comparison algorithms including structural similarity and perceptual hashing.
"""

import os
import io
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Union
from dataclasses import dataclass
from datetime import datetime
import json

# Image processing imports
try:
    from PIL import Image, ImageDraw, ImageFont, ImageChops
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# OpenCV for advanced image comparison
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

# Scikit-image for structural similarity
try:
    from skimage.metrics import structural_similarity as ssim
    from skimage.color import rgb2gray
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ComparisonMetrics:
    """Metrics from image comparison."""
    structural_similarity: float = 0.0
    pixel_difference_ratio: float = 0.0
    histogram_correlation: float = 0.0
    perceptual_hash_distance: int = 0
    mean_squared_error: float = 0.0
    peak_signal_noise_ratio: float = 0.0


@dataclass
class ValidationResult:
    """Result of visual validation."""
    success: bool
    similarity_score: float
    meets_threshold: bool
    reference_image: Path
    test_image: Path
    diff_image: Optional[Path] = None
    metrics: Optional[ComparisonMetrics] = None
    error_message: Optional[str] = None
    validation_time: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    total_comparisons: int
    successful_comparisons: int
    failed_comparisons: int
    average_similarity: float
    threshold_passed: int
    threshold_failed: int
    validation_threshold: float
    results: List[ValidationResult]
    generated_at: datetime
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class VisualValidator:
    """Compare and validate visual output."""

    def __init__(self, tolerance: float = 0.95, enable_debug_output: bool = True):
        """
        Initialize validator.

        Args:
            tolerance: Similarity threshold (0-1, higher is more strict)
            enable_debug_output: Whether to save debug diff images
        """
        if not PIL_AVAILABLE:
            raise ImportError("PIL (Pillow) is required for visual validation")

        self.tolerance = tolerance
        self.enable_debug_output = enable_debug_output

        # Check availability of optional libraries
        self.opencv_available = OPENCV_AVAILABLE
        self.skimage_available = SKIMAGE_AVAILABLE

        if not self.skimage_available:
            logger.warning("scikit-image not available - some comparison methods will be limited")

        if not self.opencv_available:
            logger.warning("OpenCV not available - some comparison methods will be limited")

        logger.info(f"VisualValidator initialized with tolerance: {tolerance}")

    def compare_images(self, image1_path: Path, image2_path: Path) -> float:
        """
        Compare two images using structural similarity.

        Args:
            image1_path: Path to first image
            image2_path: Path to second image

        Returns:
            Similarity score 0-1 (1.0 = identical)
        """
        try:
            if not image1_path.exists():
                raise FileNotFoundError(f"Reference image not found: {image1_path}")
            if not image2_path.exists():
                raise FileNotFoundError(f"Test image not found: {image2_path}")

            # Load images
            img1 = Image.open(image1_path).convert('RGB')
            img2 = Image.open(image2_path).convert('RGB')

            # Resize images to same dimensions if needed
            img1, img2 = self._normalize_image_sizes(img1, img2)

            # Use structural similarity if available
            if self.skimage_available:
                # Convert to numpy arrays
                img1_array = np.array(img1)
                img2_array = np.array(img2)

                # Convert to grayscale for SSIM
                img1_gray = rgb2gray(img1_array)
                img2_gray = rgb2gray(img2_array)

                # Calculate SSIM
                similarity, _ = ssim(img1_gray, img2_gray, full=True, data_range=1.0)
                return float(similarity)

            else:
                # Fallback to simpler comparison
                return self._calculate_pixel_similarity(img1, img2)

        except Exception as e:
            logger.error(f"Image comparison failed: {e}")
            return 0.0

    def compare_images_detailed(self, image1_path: Path, image2_path: Path) -> ComparisonMetrics:
        """
        Detailed comparison with multiple metrics.

        Args:
            image1_path: Path to first image
            image2_path: Path to second image

        Returns:
            ComparisonMetrics with detailed analysis
        """
        metrics = ComparisonMetrics()

        try:
            if not image1_path.exists() or not image2_path.exists():
                return metrics

            # Load images
            img1 = Image.open(image1_path).convert('RGB')
            img2 = Image.open(image2_path).convert('RGB')

            # Normalize sizes
            img1, img2 = self._normalize_image_sizes(img1, img2)

            # Convert to numpy arrays
            img1_array = np.array(img1)
            img2_array = np.array(img2)

            # 1. Structural Similarity (if available)
            if self.skimage_available:
                img1_gray = rgb2gray(img1_array)
                img2_gray = rgb2gray(img2_array)
                metrics.structural_similarity, _ = ssim(img1_gray, img2_gray, full=True, data_range=1.0)

            # 2. Pixel difference ratio
            metrics.pixel_difference_ratio = self._calculate_pixel_difference_ratio(img1_array, img2_array)

            # 3. Histogram correlation (if OpenCV available)
            if self.opencv_available:
                metrics.histogram_correlation = self._calculate_histogram_correlation(img1_array, img2_array)

            # 4. Perceptual hash distance
            metrics.perceptual_hash_distance = self._calculate_perceptual_hash_distance(img1, img2)

            # 5. Mean squared error
            metrics.mean_squared_error = self._calculate_mse(img1_array, img2_array)

            # 6. Peak signal-to-noise ratio
            if metrics.mean_squared_error > 0:
                metrics.peak_signal_noise_ratio = self._calculate_psnr(metrics.mean_squared_error)

            return metrics

        except Exception as e:
            logger.error(f"Detailed image comparison failed: {e}")
            return metrics

    def generate_diff_image(self, image1_path: Path, image2_path: Path, diff_path: Path) -> bool:
        """
        Generate visual diff highlighting changes.

        Args:
            image1_path: Path to reference image
            image2_path: Path to test image
            diff_path: Path for output diff image

        Returns:
            True if successful, False otherwise
        """
        try:
            if not image1_path.exists() or not image2_path.exists():
                return False

            # Load images
            img1 = Image.open(image1_path).convert('RGB')
            img2 = Image.open(image2_path).convert('RGB')

            # Normalize sizes
            img1, img2 = self._normalize_image_sizes(img1, img2)

            # Create difference image
            diff_img = ImageChops.difference(img1, img2)

            # Enhance visibility of differences
            diff_enhanced = self._enhance_differences(diff_img, img1, img2)

            # Save diff image
            diff_enhanced.save(diff_path)

            logger.info(f"Diff image generated: {diff_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to generate diff image: {e}")
            return False

    def validate_image_pair(self, reference_path: Path, test_path: Path,
                          output_dir: Optional[Path] = None) -> ValidationResult:
        """
        Validate a single image pair.

        Args:
            reference_path: Path to reference image
            test_path: Path to test image
            output_dir: Optional directory for diff images

        Returns:
            ValidationResult
        """
        import time
        start_time = time.time()

        result = ValidationResult(
            success=False,
            similarity_score=0.0,
            meets_threshold=False,
            reference_image=reference_path,
            test_image=test_path
        )

        try:
            # Calculate similarity score
            similarity = self.compare_images(reference_path, test_path)
            result.similarity_score = similarity

            # Get detailed metrics
            metrics = self.compare_images_detailed(reference_path, test_path)
            result.metrics = metrics

            # Check threshold
            result.meets_threshold = similarity >= self.tolerance

            # Generate diff image if requested
            if output_dir and self.enable_debug_output:
                output_dir.mkdir(parents=True, exist_ok=True)
                diff_filename = f"diff_{reference_path.stem}_{test_path.stem}.png"
                diff_path = output_dir / diff_filename

                if self.generate_diff_image(reference_path, test_path, diff_path):
                    result.diff_image = diff_path

            result.success = True
            result.validation_time = time.time() - start_time

            logger.info(f"Validation completed: {similarity:.3f} (threshold: {self.tolerance})")
            return result

        except Exception as e:
            result.error_message = str(e)
            result.validation_time = time.time() - start_time
            logger.error(f"Validation failed: {e}")
            return result

    def validate_presentation(self, reference_images: List[Path], test_images: List[Path],
                            output_dir: Optional[Path] = None) -> ValidationReport:
        """
        Validate entire presentation against references.

        Args:
            reference_images: List of reference image paths
            test_images: List of test image paths
            output_dir: Optional directory for diff images and reports

        Returns:
            ValidationReport
        """
        start_time = datetime.now()

        # Pair up images (assume they're in corresponding order)
        image_pairs = list(zip(reference_images, test_images))
        total_comparisons = len(image_pairs)

        results = []
        similarity_scores = []

        logger.info(f"Starting presentation validation: {total_comparisons} image pairs")

        for i, (ref_path, test_path) in enumerate(image_pairs):
            logger.info(f"Validating pair {i+1}/{total_comparisons}: {ref_path.name} vs {test_path.name}")

            result = self.validate_image_pair(ref_path, test_path, output_dir)
            results.append(result)

            if result.success:
                similarity_scores.append(result.similarity_score)

        # Calculate summary statistics
        successful = sum(1 for r in results if r.success)
        failed = total_comparisons - successful
        threshold_passed = sum(1 for r in results if r.meets_threshold)
        threshold_failed = total_comparisons - threshold_passed

        average_similarity = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0

        report = ValidationReport(
            total_comparisons=total_comparisons,
            successful_comparisons=successful,
            failed_comparisons=failed,
            average_similarity=average_similarity,
            threshold_passed=threshold_passed,
            threshold_failed=threshold_failed,
            validation_threshold=self.tolerance,
            results=results,
            generated_at=start_time
        )

        # Save detailed report if output directory provided
        if output_dir:
            self._save_validation_report(report, output_dir)

        logger.info(f"Presentation validation completed: {threshold_passed}/{total_comparisons} passed threshold")
        return report

    def create_reference_images(self, image_paths: List[Path], reference_dir: Path) -> bool:
        """
        Create reference image baseline from current test images.

        Args:
            image_paths: List of current test images
            reference_dir: Directory to store reference images

        Returns:
            True if successful
        """
        try:
            reference_dir.mkdir(parents=True, exist_ok=True)

            for image_path in image_paths:
                if not image_path.exists():
                    continue

                # Copy to reference directory
                reference_path = reference_dir / image_path.name

                # Load and save to ensure consistent format
                img = Image.open(image_path).convert('RGB')
                img.save(reference_path, 'PNG', optimize=True)

                logger.info(f"Reference image created: {reference_path}")

            logger.info(f"Created {len(image_paths)} reference images in {reference_dir}")
            return True

        except Exception as e:
            logger.error(f"Failed to create reference images: {e}")
            return False

    def _normalize_image_sizes(self, img1: Image.Image, img2: Image.Image) -> Tuple[Image.Image, Image.Image]:
        """Normalize image sizes for comparison."""
        if img1.size != img2.size:
            # Resize to the smaller dimensions to avoid upscaling artifacts
            target_width = min(img1.width, img2.width)
            target_height = min(img1.height, img2.height)

            img1 = img1.resize((target_width, target_height), Image.Resampling.LANCZOS)
            img2 = img2.resize((target_width, target_height), Image.Resampling.LANCZOS)

        return img1, img2

    def _calculate_pixel_similarity(self, img1: Image.Image, img2: Image.Image) -> float:
        """Simple pixel-based similarity calculation."""
        try:
            diff = ImageChops.difference(img1, img2)
            diff_array = np.array(diff)

            # Calculate percentage of identical pixels
            total_pixels = diff_array.size
            zero_pixels = np.count_nonzero(diff_array == 0)

            similarity = zero_pixels / total_pixels
            return similarity

        except Exception:
            return 0.0

    def _calculate_pixel_difference_ratio(self, img1_array: np.ndarray, img2_array: np.ndarray) -> float:
        """Calculate ratio of different pixels."""
        try:
            diff = np.abs(img1_array.astype(float) - img2_array.astype(float))
            different_pixels = np.count_nonzero(diff)
            total_pixels = img1_array.size
            return different_pixels / total_pixels
        except Exception:
            return 1.0

    def _calculate_histogram_correlation(self, img1_array: np.ndarray, img2_array: np.ndarray) -> float:
        """Calculate histogram correlation using OpenCV."""
        if not self.opencv_available:
            return 0.0

        try:
            # Convert to OpenCV format
            img1_cv = cv2.cvtColor(img1_array, cv2.COLOR_RGB2BGR)
            img2_cv = cv2.cvtColor(img2_array, cv2.COLOR_RGB2BGR)

            # Calculate histograms
            hist1 = cv2.calcHist([img1_cv], [0, 1, 2], None, [256, 256, 256], [0, 256, 0, 256, 0, 256])
            hist2 = cv2.calcHist([img2_cv], [0, 1, 2], None, [256, 256, 256], [0, 256, 0, 256, 0, 256])

            # Calculate correlation
            correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            return correlation

        except Exception:
            return 0.0

    def _calculate_perceptual_hash_distance(self, img1: Image.Image, img2: Image.Image) -> int:
        """Calculate perceptual hash distance."""
        try:
            # Simple perceptual hash implementation
            hash1 = self._perceptual_hash(img1)
            hash2 = self._perceptual_hash(img2)

            # Calculate Hamming distance
            distance = bin(hash1 ^ hash2).count('1')
            return distance

        except Exception:
            return 64  # Maximum possible distance for 8x8 hash

    def _perceptual_hash(self, img: Image.Image) -> int:
        """Simple perceptual hash implementation."""
        # Resize to 8x8
        img_small = img.resize((8, 8), Image.Resampling.LANCZOS).convert('L')

        # Get pixel values
        pixels = list(img_small.getdata())

        # Calculate average
        avg = sum(pixels) / len(pixels)

        # Create hash
        hash_bits = []
        for pixel in pixels:
            hash_bits.append('1' if pixel > avg else '0')

        return int(''.join(hash_bits), 2)

    def _calculate_mse(self, img1_array: np.ndarray, img2_array: np.ndarray) -> float:
        """Calculate mean squared error."""
        try:
            mse = np.mean((img1_array.astype(float) - img2_array.astype(float)) ** 2)
            return float(mse)
        except Exception:
            return float('inf')

    def _calculate_psnr(self, mse: float) -> float:
        """Calculate peak signal-to-noise ratio."""
        try:
            if mse == 0:
                return float('inf')
            return 20 * np.log10(255.0 / np.sqrt(mse))
        except Exception:
            return 0.0

    def _enhance_differences(self, diff_img: Image.Image, img1: Image.Image, img2: Image.Image) -> Image.Image:
        """Enhance visibility of differences in diff image."""
        try:
            # Create a composite image showing differences
            width, height = diff_img.size
            enhanced = Image.new('RGB', (width * 3, height))

            # Original images side by side with diff
            enhanced.paste(img1, (0, 0))
            enhanced.paste(img2, (width, 0))

            # Enhanced diff with colored differences
            diff_colored = Image.new('RGB', (width, height))
            for x in range(width):
                for y in range(height):
                    diff_pixel = diff_img.getpixel((x, y))
                    if sum(diff_pixel) > 30:  # Threshold for visible difference
                        diff_colored.putpixel((x, y), (255, 0, 0))  # Red for differences
                    else:
                        orig_pixel = img1.getpixel((x, y))
                        diff_colored.putpixel((x, y), orig_pixel)

            enhanced.paste(diff_colored, (width * 2, 0))
            return enhanced

        except Exception:
            # Fallback to simple diff
            return diff_img

    def _save_validation_report(self, report: ValidationReport, output_dir: Path) -> None:
        """Save validation report to JSON file."""
        try:
            report_path = output_dir / "validation_report.json"

            # Convert report to serializable format
            report_data = {
                'total_comparisons': report.total_comparisons,
                'successful_comparisons': report.successful_comparisons,
                'failed_comparisons': report.failed_comparisons,
                'average_similarity': report.average_similarity,
                'threshold_passed': report.threshold_passed,
                'threshold_failed': report.threshold_failed,
                'validation_threshold': report.validation_threshold,
                'generated_at': report.generated_at.isoformat(),
                'results': []
            }

            # Add individual results
            for result in report.results:
                result_data = {
                    'success': result.success,
                    'similarity_score': result.similarity_score,
                    'meets_threshold': result.meets_threshold,
                    'reference_image': str(result.reference_image),
                    'test_image': str(result.test_image),
                    'diff_image': str(result.diff_image) if result.diff_image else None,
                    'error_message': result.error_message,
                    'validation_time': result.validation_time
                }

                # Add metrics if available
                if result.metrics:
                    result_data['metrics'] = {
                        'structural_similarity': result.metrics.structural_similarity,
                        'pixel_difference_ratio': result.metrics.pixel_difference_ratio,
                        'histogram_correlation': result.metrics.histogram_correlation,
                        'perceptual_hash_distance': result.metrics.perceptual_hash_distance,
                        'mean_squared_error': result.metrics.mean_squared_error,
                        'peak_signal_noise_ratio': result.metrics.peak_signal_noise_ratio
                    }

                report_data['results'].append(result_data)

            # Save to file
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2)

            logger.info(f"Validation report saved: {report_path}")

        except Exception as e:
            logger.error(f"Failed to save validation report: {e}")