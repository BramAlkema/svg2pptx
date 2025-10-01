#!/usr/bin/env python3
"""
Visual diff generation for CLI reports.

Integrates existing Pillow-based visual comparison infrastructure
to generate side-by-side visual diffs for HTML reports.
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import time

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from tests.support.visual_regression_tester import (
        ImageComparator, ComparisonMethod, VisualComparisonResult
    )
    VISUAL_DIFF_AVAILABLE = True
except ImportError:
    VISUAL_DIFF_AVAILABLE = False
    # Provide mock classes for graceful degradation
    class ComparisonMethod:
        STRUCTURAL_SIMILARITY = "structural_similarity"
    class VisualComparisonResult:
        pass

try:
    from PIL import Image, ImageDraw, ImageChops, ImageFilter
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


class CLIVisualDiffGenerator:
    """
    Generate visual diffs for CLI reports.

    Provides enhanced visual difference analysis with multiple comparison methods
    and detailed metrics for report generation.
    """

    def __init__(self, output_dir: Path):
        """
        Initialize visual diff generator.

        Args:
            output_dir: Directory for saving diff images
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.comparator = ImageComparator() if VISUAL_DIFF_AVAILABLE else None

    def is_available(self) -> bool:
        """Check if visual diff generation is available."""
        return VISUAL_DIFF_AVAILABLE and PILLOW_AVAILABLE

    def generate_visual_diff(self, svg_screenshot: Path, pptx_screenshot: Path,
                           method: str = "structural_similarity") -> Dict[str, Any]:
        """
        Generate visual diff between SVG and PPTX screenshots.

        Args:
            svg_screenshot: Path to SVG screenshot (reference)
            pptx_screenshot: Path to PPTX screenshot (output)
            method: Comparison method to use

        Returns:
            Dictionary with diff results and metrics
        """
        if not self.is_available():
            return {
                "available": False,
                "error": "Visual diff not available (Pillow required)"
            }

        if not svg_screenshot.exists() or not pptx_screenshot.exists():
            return {
                "available": False,
                "error": "Screenshot files not found"
            }

        try:
            # Map method string to enum
            method_map = {
                "pixel_perfect": ComparisonMethod.PIXEL_PERFECT,
                "structural_similarity": ComparisonMethod.STRUCTURAL_SIMILARITY,
                "perceptual_hash": ComparisonMethod.PERCEPTUAL_HASH,
                "histogram": ComparisonMethod.HISTOGRAM_COMPARISON,
                "edge_detection": ComparisonMethod.EDGE_DETECTION
            }
            comparison_method = method_map.get(method, ComparisonMethod.STRUCTURAL_SIMILARITY)

            # Run comparison
            result = self.comparator.compare_images(
                reference_path=svg_screenshot,
                output_path=pptx_screenshot,
                method=comparison_method,
                save_diff=True
            )

            # Generate enhanced diff visualization
            diff_image_path = self._generate_enhanced_diff(
                svg_screenshot, pptx_screenshot, result
            )

            # Calculate additional metrics
            metrics = self._calculate_detailed_metrics(result)

            return {
                "available": True,
                "similarity_score": result.similarity_score,
                "similarity_percentage": f"{result.similarity_score * 100:.1f}%",
                "pixel_difference_count": result.pixel_difference_count,
                "total_pixels": result.total_pixels,
                "different_pixels_percentage": f"{(result.pixel_difference_count / max(result.total_pixels, 1)) * 100:.2f}%",
                "comparison_method": result.comparison_method,
                "diff_image_path": str(diff_image_path) if diff_image_path else None,
                "metrics": metrics,
                "passed": result.similarity_score >= 0.95,  # Default threshold
                "metadata": result.metadata
            }

        except Exception as e:
            return {
                "available": False,
                "error": f"Visual diff generation failed: {str(e)}"
            }

    def _generate_enhanced_diff(self, svg_path: Path, pptx_path: Path,
                               result: VisualComparisonResult) -> Optional[Path]:
        """
        Generate enhanced difference visualization with annotations.

        Creates a three-panel image showing:
        1. SVG screenshot (reference)
        2. PPTX screenshot (output)
        3. Highlighted differences

        Args:
            svg_path: Path to SVG screenshot
            pptx_path: Path to PPTX screenshot
            result: Comparison result object

        Returns:
            Path to generated diff image or None if failed
        """
        if not PILLOW_AVAILABLE:
            return None

        try:
            # Load images
            svg_img = Image.open(svg_path)
            pptx_img = Image.open(pptx_path)

            # Normalize to same size
            width = max(svg_img.width, pptx_img.width)
            height = max(svg_img.height, pptx_img.height)

            if svg_img.size != (width, height):
                svg_img = svg_img.resize((width, height), Image.Resampling.LANCZOS)
            if pptx_img.size != (width, height):
                pptx_img = pptx_img.resize((width, height), Image.Resampling.LANCZOS)

            # Convert to RGB
            if svg_img.mode != 'RGB':
                svg_img = svg_img.convert('RGB')
            if pptx_img.mode != 'RGB':
                pptx_img = pptx_img.convert('RGB')

            # Create difference image
            diff = ImageChops.difference(svg_img, pptx_img)

            # Enhance differences with color coding
            enhanced_diff = self._colorize_differences(diff)

            # Create three-panel composite
            panel_width = width
            panel_height = height + 40  # Extra space for labels
            composite_width = panel_width * 3
            composite_height = panel_height

            composite = Image.new('RGB', (composite_width, composite_height), 'white')

            # Add panels with labels
            composite.paste(svg_img, (0, 40))
            composite.paste(pptx_img, (panel_width, 40))
            composite.paste(enhanced_diff, (panel_width * 2, 40))

            # Add labels and metrics
            draw = ImageDraw.Draw(composite)

            # Panel labels
            self._add_panel_label(draw, 0, "SVG (Reference)", (0, 128, 0))
            self._add_panel_label(draw, panel_width, "PPTX (Output)", (0, 0, 128))
            self._add_panel_label(draw, panel_width * 2,
                                f"Differences ({result.similarity_score:.1%} similar)",
                                (128, 0, 0))

            # Save composite image
            timestamp = int(time.time())
            diff_path = self.output_dir / f"visual_diff_{timestamp}.png"
            composite.save(diff_path, optimize=True)

            return diff_path

        except Exception as e:
            print(f"Warning: Could not generate enhanced diff: {e}")
            return None

    def _colorize_differences(self, diff_img: 'Image.Image') -> 'Image.Image':
        """
        Colorize difference image for better visibility.

        Args:
            diff_img: Raw difference image

        Returns:
            Colorized difference image
        """
        try:
            # Convert to grayscale to get difference intensity
            gray_diff = diff_img.convert('L')

            # Apply edge detection to highlight boundaries
            edges = gray_diff.filter(ImageFilter.FIND_EDGES)

            # Create colored version
            colored = Image.new('RGB', diff_img.size, (0, 0, 0))

            # Color mapping: differences in red, edges in yellow
            pixels = colored.load()
            gray_pixels = gray_diff.load()
            edge_pixels = edges.load()

            for y in range(diff_img.height):
                for x in range(diff_img.width):
                    intensity = gray_pixels[x, y]
                    edge_intensity = edge_pixels[x, y]

                    if intensity > 10:  # Threshold for differences
                        # Red channel based on difference intensity
                        r = min(255, intensity * 3)
                        # Green for edge highlighting
                        g = min(255, edge_intensity * 2)
                        # Blue for strong differences
                        b = min(255, intensity if intensity > 100 else 0)
                        pixels[x, y] = (r, g, b)

            return colored

        except:
            # Fallback to simple enhanced difference
            return ImageChops.multiply(diff_img, diff_img)

    def _add_panel_label(self, draw: 'ImageDraw.Draw', x: int, label: str, color: Tuple[int, int, int]):
        """
        Add label to panel in composite image.

        Args:
            draw: ImageDraw object
            x: X position for label
            label: Text to display
            color: RGB color tuple
        """
        try:
            # Add background rectangle for better readability
            draw.rectangle([(x, 0), (x + 300, 35)], fill=(240, 240, 240))
            # Add text (default font)
            draw.text((x + 10, 10), label, fill=color)
        except:
            # Skip if font issues
            pass

    def _calculate_detailed_metrics(self, result: VisualComparisonResult) -> Dict[str, Any]:
        """
        Calculate additional visual comparison metrics.

        Args:
            result: Comparison result object

        Returns:
            Dictionary with detailed metrics
        """
        metrics = {
            "quality_assessment": self._assess_quality(result.similarity_score),
            "pixel_accuracy": f"{(1 - result.pixel_difference_count / max(result.total_pixels, 1)) * 100:.2f}%",
            "recommendation": self._get_recommendation(result.similarity_score),
            "areas_of_concern": []
        }

        # Add areas of concern based on similarity
        if result.similarity_score < 0.99:
            metrics["areas_of_concern"].append("Minor visual differences detected")
        if result.similarity_score < 0.95:
            metrics["areas_of_concern"].append("Noticeable visual discrepancies")
        if result.similarity_score < 0.90:
            metrics["areas_of_concern"].append("Significant rendering differences")
        if result.similarity_score < 0.80:
            metrics["areas_of_concern"].append("Major conversion issues detected")

        return metrics

    def _assess_quality(self, similarity: float) -> str:
        """Assess conversion quality based on similarity score."""
        if similarity >= 0.99:
            return "Excellent - Near perfect conversion"
        elif similarity >= 0.95:
            return "Good - Minor differences only"
        elif similarity >= 0.90:
            return "Acceptable - Some visible differences"
        elif similarity >= 0.80:
            return "Poor - Significant differences"
        else:
            return "Failed - Major conversion issues"

    def _get_recommendation(self, similarity: float) -> str:
        """Get recommendation based on similarity score."""
        if similarity >= 0.99:
            return "Conversion successful, ready for production use"
        elif similarity >= 0.95:
            return "Conversion successful, review minor differences if critical"
        elif similarity >= 0.90:
            return "Review output carefully, some elements may need adjustment"
        elif similarity >= 0.80:
            return "Conversion has issues, consider manual adjustments"
        else:
            return "Conversion failed quality check, investigate issues"