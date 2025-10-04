#!/usr/bin/env python3
"""
Image Comparison Module for Visual Accuracy Metrics

Uses PIL (already available for colorspace work) to compare SVG screenshot
vs PowerPoint/Google Slides screenshot and calculate accuracy metrics.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageChops, ImageFilter
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from dataclasses import dataclass
import io


@dataclass
class ImageComparisonResult:
    """Results of image comparison analysis."""
    overall_accuracy: float = 0.0
    pixel_difference: float = 0.0
    structural_similarity: float = 0.0
    color_accuracy: float = 0.0
    edge_similarity: float = 0.0
    diff_image: Optional[Image.Image] = None
    heatmap_image: Optional[Image.Image] = None


class ImageComparator:
    """Compare two images and calculate visual accuracy metrics."""

    def __init__(self):
        """Initialize image comparator."""
        self.threshold = 10  # Pixel difference threshold for "same" color

    def compare_images(self, image1_path: Path, image2_path: Path) -> ImageComparisonResult:
        """
        Compare two images and return comprehensive metrics.

        Args:
            image1_path: Path to first image (SVG screenshot)
            image2_path: Path to second image (PowerPoint screenshot)

        Returns:
            ImageComparisonResult with all metrics
        """
        # Load images
        img1 = Image.open(image1_path).convert('RGB')
        img2 = Image.open(image2_path).convert('RGB')

        # Resize to match (use smaller dimensions)
        target_size = (
            min(img1.width, img2.width),
            min(img1.height, img2.height)
        )
        img1 = img1.resize(target_size, Image.Resampling.LANCZOS)
        img2 = img2.resize(target_size, Image.Resampling.LANCZOS)

        # Calculate metrics
        pixel_diff = self._calculate_pixel_difference(img1, img2)
        color_accuracy = self._calculate_color_accuracy(img1, img2)
        edge_similarity = self._calculate_edge_similarity(img1, img2)
        structural_sim = self._calculate_structural_similarity(img1, img2)

        # Overall accuracy (weighted average)
        overall_accuracy = (
            color_accuracy * 0.4 +
            (100 - pixel_diff) * 0.3 +
            edge_similarity * 0.2 +
            structural_sim * 0.1
        )

        # Generate diff visualizations
        diff_image = self._create_difference_image(img1, img2)
        heatmap_image = self._create_heatmap(img1, img2)

        return ImageComparisonResult(
            overall_accuracy=overall_accuracy,
            pixel_difference=pixel_diff,
            structural_similarity=structural_sim,
            color_accuracy=color_accuracy,
            edge_similarity=edge_similarity,
            diff_image=diff_image,
            heatmap_image=heatmap_image
        )

    def _calculate_pixel_difference(self, img1: Image.Image, img2: Image.Image) -> float:
        """
        Calculate percentage of pixels that differ.

        Returns:
            Percentage of different pixels (0-100)
        """
        # Convert to numpy arrays
        arr1 = np.array(img1)
        arr2 = np.array(img2)

        # Calculate absolute difference per channel
        diff = np.abs(arr1.astype(int) - arr2.astype(int))

        # Pixels differ if any channel differs by more than threshold
        different_pixels = np.any(diff > self.threshold, axis=2)

        # Calculate percentage
        total_pixels = different_pixels.size
        diff_count = np.sum(different_pixels)

        return (diff_count / total_pixels) * 100

    def _calculate_color_accuracy(self, img1: Image.Image, img2: Image.Image) -> float:
        """
        Calculate color accuracy using histogram comparison.

        Returns:
            Color accuracy percentage (0-100)
        """
        # Get histograms for each channel
        hist1_r = np.array(img1.split()[0].histogram())
        hist1_g = np.array(img1.split()[1].histogram())
        hist1_b = np.array(img1.split()[2].histogram())

        hist2_r = np.array(img2.split()[0].histogram())
        hist2_g = np.array(img2.split()[1].histogram())
        hist2_b = np.array(img2.split()[2].histogram())

        # Normalize histograms
        hist1_r = hist1_r / hist1_r.sum()
        hist1_g = hist1_g / hist1_g.sum()
        hist1_b = hist1_b / hist1_b.sum()

        hist2_r = hist2_r / hist2_r.sum()
        hist2_g = hist2_g / hist2_g.sum()
        hist2_b = hist2_b / hist2_b.sum()

        # Calculate correlation for each channel
        corr_r = np.corrcoef(hist1_r, hist2_r)[0, 1]
        corr_g = np.corrcoef(hist1_g, hist2_g)[0, 1]
        corr_b = np.corrcoef(hist1_b, hist2_b)[0, 1]

        # Average correlation as accuracy
        avg_corr = (corr_r + corr_g + corr_b) / 3

        # Convert to percentage (correlation is -1 to 1, we want 0 to 100)
        return max(0, min(100, (avg_corr + 1) * 50))

    def _calculate_edge_similarity(self, img1: Image.Image, img2: Image.Image) -> float:
        """
        Calculate edge similarity using edge detection.

        Returns:
            Edge similarity percentage (0-100)
        """
        # Convert to grayscale
        gray1 = img1.convert('L')
        gray2 = img2.convert('L')

        # Apply edge detection
        edges1 = gray1.filter(ImageFilter.FIND_EDGES)
        edges2 = gray2.filter(ImageFilter.FIND_EDGES)

        # Convert to numpy
        arr1 = np.array(edges1)
        arr2 = np.array(edges2)

        # Calculate similarity of edge maps
        diff = np.abs(arr1.astype(int) - arr2.astype(int))
        similarity = 1 - (np.mean(diff) / 255)

        return similarity * 100

    def _calculate_structural_similarity(self, img1: Image.Image, img2: Image.Image) -> float:
        """
        Calculate structural similarity (simplified SSIM).

        Returns:
            Structural similarity percentage (0-100)
        """
        # Convert to grayscale numpy arrays
        arr1 = np.array(img1.convert('L')).astype(float)
        arr2 = np.array(img2.convert('L')).astype(float)

        # Calculate means
        mean1 = np.mean(arr1)
        mean2 = np.mean(arr2)

        # Calculate variances
        var1 = np.var(arr1)
        var2 = np.var(arr2)

        # Calculate covariance
        covariance = np.mean((arr1 - mean1) * (arr2 - mean2))

        # SSIM formula (simplified)
        c1 = (0.01 * 255) ** 2
        c2 = (0.03 * 255) ** 2

        numerator = (2 * mean1 * mean2 + c1) * (2 * covariance + c2)
        denominator = (mean1**2 + mean2**2 + c1) * (var1 + var2 + c2)

        ssim = numerator / denominator

        return max(0, min(100, ssim * 100))

    def _create_difference_image(self, img1: Image.Image, img2: Image.Image) -> Image.Image:
        """
        Create a difference image showing where images differ.

        Returns:
            PIL Image with differences highlighted
        """
        # Calculate absolute difference
        diff = ImageChops.difference(img1, img2)

        # Enhance differences for visibility
        enhancer = diff.point(lambda p: p * 3)  # Amplify differences

        return enhancer

    def _create_heatmap(self, img1: Image.Image, img2: Image.Image) -> Image.Image:
        """
        Create a heatmap showing intensity of differences.

        Returns:
            PIL Image with heatmap overlay
        """
        # Convert to numpy
        arr1 = np.array(img1)
        arr2 = np.array(img2)

        # Calculate per-pixel difference magnitude
        diff = np.sqrt(np.sum((arr1.astype(int) - arr2.astype(int))**2, axis=2))

        # Normalize to 0-255
        diff_normalized = ((diff / diff.max()) * 255).astype(np.uint8)

        # Create heatmap (red = high difference, blue = low difference)
        heatmap = Image.fromarray(diff_normalized, mode='L')

        # Apply color map (create RGB from grayscale with color gradient)
        heatmap_rgb = Image.new('RGB', heatmap.size)
        pixels = heatmap.load()
        heatmap_pixels = heatmap_rgb.load()

        for y in range(heatmap.height):
            for x in range(heatmap.width):
                intensity = pixels[x, y]
                # Blue (low) -> Green -> Yellow -> Red (high)
                if intensity < 64:
                    # Blue to cyan
                    r, g, b = 0, intensity * 4, 255
                elif intensity < 128:
                    # Cyan to green
                    r, g, b = 0, 255, 255 - (intensity - 64) * 4
                elif intensity < 192:
                    # Green to yellow
                    r, g, b = (intensity - 128) * 4, 255, 0
                else:
                    # Yellow to red
                    r, g, b = 255, 255 - (intensity - 192) * 4, 0

                heatmap_pixels[x, y] = (r, g, b)

        # Blend with original image
        blended = Image.blend(img1, heatmap_rgb, alpha=0.5)

        return blended

    def save_comparison_images(self, result: ImageComparisonResult, output_dir: Path,
                               base_name: str = "comparison"):
        """
        Save diff and heatmap images to disk.

        Args:
            result: ImageComparisonResult with images
            output_dir: Directory to save images
            base_name: Base name for output files
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        if result.diff_image:
            diff_path = output_dir / f"{base_name}_diff.png"
            result.diff_image.save(diff_path)

        if result.heatmap_image:
            heatmap_path = output_dir / f"{base_name}_heatmap.png"
            result.heatmap_image.save(heatmap_path)


def main():
    """Test image comparison."""
    import argparse

    parser = argparse.ArgumentParser(description='Compare two images')
    parser.add_argument('image1', type=Path, help='First image (SVG screenshot)')
    parser.add_argument('image2', type=Path, help='Second image (PowerPoint screenshot)')
    parser.add_argument('--output-dir', type=Path, default=Path('.'), help='Output directory')

    args = parser.parse_args()

    comparator = ImageComparator()
    result = comparator.compare_images(args.image1, args.image2)

    print("📊 Image Comparison Results")
    print("=" * 50)
    print(f"Overall Accuracy:       {result.overall_accuracy:.2f}%")
    print(f"Pixel Difference:       {result.pixel_difference:.2f}%")
    print(f"Color Accuracy:         {result.color_accuracy:.2f}%")
    print(f"Edge Similarity:        {result.edge_similarity:.2f}%")
    print(f"Structural Similarity:  {result.structural_similarity:.2f}%")

    # Save comparison images
    comparator.save_comparison_images(result, args.output_dir)
    print(f"\n✅ Comparison images saved to {args.output_dir}")


if __name__ == "__main__":
    main()
