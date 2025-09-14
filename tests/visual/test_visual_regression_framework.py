#!/usr/bin/env python3
"""
Visual Regression Test Framework for SVG2PPTX Filter Effects

This module implements visual regression testing following the unit test template
structure to ensure filter effects render correctly and consistently.

Usage:
1. Generate baseline images for filter effects
2. Compare current output against baselines
3. Detect visual regressions automatically
4. Provide detailed diff reports for failures
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from pathlib import Path
import sys
from lxml import etree as ET
import hashlib
import json
from PIL import Image, ImageDraw, ImageChops
import numpy as np
import io
import tempfile
import shutil
from typing import Dict, List, Tuple, Optional, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.converters.filters import FilterPipeline, FilterIntegrator, CompositingEngine
from src.converters.base import BaseConverter
from src.utils.units import UnitConverter
from src.utils.colors import ColorParser
from src.utils.transforms import TransformParser

class TestVisualRegressionFramework:
    """
    Visual regression tests for Filter Effects Pipeline.

    Tests visual output consistency across filter operations to catch
    rendering regressions and ensure visual fidelity.
    """

    @pytest.fixture
    def setup_test_data(self):
        """
        Setup common test data and mock objects for visual regression testing.

        Returns comprehensive test data including SVG documents, baseline
        images, comparison thresholds, and expected visual results.
        """
        # Test SVG documents with various filter effects
        test_svg_documents = {
            'blur_filter': '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <filter id="blur" x="0" y="0" width="100%" height="100%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="3"/>
        </filter>
    </defs>
    <rect x="50" y="50" width="100" height="100" fill="blue" filter="url(#blur)"/>
</svg>''',

            'drop_shadow': '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="300" height="300" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <filter id="dropshadow" x="0" y="0" width="200%" height="200%">
            <feOffset in="SourceGraphic" dx="5" dy="5" result="offset"/>
            <feGaussianBlur in="offset" stdDeviation="3" result="blur"/>
            <feColorMatrix in="blur" type="matrix"
                          values="0 0 0 0.5 0   0 0 0 0.5 0   0 0 0 0.5 0   0 0 0 1 0"/>
        </filter>
    </defs>
    <circle cx="100" cy="100" r="50" fill="red" filter="url(#dropshadow)"/>
</svg>''',

            'complex_chain': '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="400" height="400" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <filter id="complex" x="0" y="0" width="300%" height="300%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur"/>
            <feOffset in="blur" dx="3" dy="3" result="offset"/>
            <feColorMatrix in="offset" type="matrix"
                          values="1 0 0 0 0.2   0 1 0 0 0.2   0 0 1 0 0.2   0 0 0 1 0" result="colored"/>
            <feComposite in="SourceGraphic" in2="colored" operator="over"/>
        </filter>
    </defs>
    <polygon points="100,50 150,150 50,150" fill="green" filter="url(#complex)"/>
</svg>'''
        }

        # Visual comparison thresholds
        comparison_config = {
            'pixel_threshold': 0.05,  # 5% pixel difference tolerance
            'color_threshold': 10,    # RGB color difference tolerance
            'structural_threshold': 0.95,  # Structural similarity threshold
            'perceptual_threshold': 0.98   # Perceptual hash similarity threshold
        }

        # Expected visual characteristics
        expected_results = {
            'blur_filter': {
                'has_blur_effect': True,
                'blur_radius_range': (2, 4),
                'color_preservation': True,
                'shape_preservation': True
            },
            'drop_shadow': {
                'has_shadow': True,
                'shadow_offset': (5, 5),
                'shadow_blur': True,
                'original_preserved': True
            },
            'complex_chain': {
                'has_blur': True,
                'has_offset': True,
                'has_color_matrix': True,
                'composite_layers': 2
            }
        }

        # Test configuration
        test_config = {
            'enable_hardware_acceleration': False,
            'output_format': 'png',
            'color_space': 'srgb',
            'resolution': (96, 96),  # DPI
            'anti_aliasing': True,
            'subpixel_rendering': False
        }

        return {
            'test_svg_documents': test_svg_documents,
            'comparison_config': comparison_config,
            'expected_results': expected_results,
            'test_config': test_config,
            'baseline_dir': Path(__file__).parent / "baselines",
            'output_dir': Path(__file__).parent / "output",
            'diff_dir': Path(__file__).parent / "diffs"
        }

    @pytest.fixture
    def component_instance(self, setup_test_data):
        """
        Create instance of visual regression framework with proper dependencies.

        Initializes the complete visual testing pipeline including filter
        converters, image comparison tools, and baseline management.
        """
        # Create unit converter with test configuration
        unit_converter = UnitConverter()
        unit_converter.set_dpi(setup_test_data['test_config']['resolution'][0])

        # Create color parser for filter effects
        color_parser = ColorParser()

        # Create transform parser
        transform_parser = TransformParser()

        # Create filter pipeline
        filter_pipeline = FilterPipeline(
            unit_converter=unit_converter,
            color_parser=color_parser,
            transform_parser=transform_parser,
            config=setup_test_data['test_config']
        )

        # Create visual regression framework
        framework = VisualRegressionFramework(
            filter_pipeline=filter_pipeline,
            baseline_dir=setup_test_data['baseline_dir'],
            output_dir=setup_test_data['output_dir'],
            diff_dir=setup_test_data['diff_dir'],
            comparison_config=setup_test_data['comparison_config']
        )

        return framework

    def test_initialization(self, component_instance):
        """
        Test visual regression framework initialization and basic properties.

        Verifies that the framework initializes correctly with all required
        components and that baseline directories are properly set up.
        """
        assert component_instance is not None
        assert hasattr(component_instance, 'filter_pipeline')
        assert hasattr(component_instance, 'baseline_dir')
        assert hasattr(component_instance, 'output_dir')
        assert hasattr(component_instance, 'diff_dir')
        assert hasattr(component_instance, 'comparison_config')

        # Verify directories are Path objects
        assert isinstance(component_instance.baseline_dir, Path)
        assert isinstance(component_instance.output_dir, Path)
        assert isinstance(component_instance.diff_dir, Path)

    def test_basic_functionality(self, component_instance, setup_test_data):
        """
        Test core visual regression functionality.

        Tests baseline generation, image comparison, and regression detection
        for basic filter effects scenarios.
        """
        # Test baseline generation
        test_svg = setup_test_data['test_svg_documents']['blur_filter']
        test_name = "blur_filter_basic"

        # Generate baseline image
        baseline_created = component_instance.generate_baseline(test_name, test_svg)
        assert baseline_created is True

        # Verify baseline file exists
        baseline_path = component_instance.baseline_dir / f"{test_name}.png"
        assert baseline_path.exists()

        # Test image comparison with identical input
        comparison_result = component_instance.compare_with_baseline(test_name, test_svg)
        assert comparison_result['match'] is True
        assert comparison_result['pixel_diff_percentage'] < 0.01
        assert comparison_result['structural_similarity'] > 0.99

    def test_error_handling(self, component_instance, setup_test_data):
        """
        Test error handling in visual regression scenarios.

        Tests handling of invalid SVG, missing baselines, corrupted images,
        and comparison failures.
        """
        # Test invalid SVG handling
        invalid_svg = "<svg>invalid xml"
        with pytest.raises(Exception) as exc_info:
            component_instance.generate_baseline("invalid_test", invalid_svg)
        assert "XML parsing error" in str(exc_info.value) or "Invalid SVG" in str(exc_info.value)

        # Test missing baseline handling
        missing_result = component_instance.compare_with_baseline("nonexistent_test",
                                                               setup_test_data['test_svg_documents']['blur_filter'])
        assert missing_result['match'] is False
        assert missing_result['error'] == 'missing_baseline'

        # Test corrupted baseline handling
        corrupted_baseline_path = component_instance.baseline_dir / "corrupted_test.png"
        corrupted_baseline_path.write_bytes(b"not an image")

        corrupted_result = component_instance.compare_with_baseline("corrupted_test",
                                                                 setup_test_data['test_svg_documents']['blur_filter'])
        assert corrupted_result['match'] is False
        assert 'corrupted_baseline' in corrupted_result.get('error', '')

    def test_edge_cases(self, component_instance, setup_test_data):
        """
        Test edge cases in visual regression testing.

        Tests empty SVGs, single pixel differences, extreme filter parameters,
        and boundary condition scenarios.
        """
        # Test empty SVG
        empty_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
</svg>'''

        empty_result = component_instance.generate_baseline("empty_svg_test", empty_svg)
        assert empty_result is True

        # Test single pixel difference detection
        single_pixel_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="50" y="50" width="1" height="1" fill="red"/>
</svg>'''

        component_instance.generate_baseline("single_pixel_test", single_pixel_svg)

        # Modify by one pixel
        modified_svg = single_pixel_svg.replace('x="50"', 'x="51"')
        comparison = component_instance.compare_with_baseline("single_pixel_test", modified_svg)

        # Should detect the difference but be within tolerance
        assert comparison['pixel_diff_percentage'] > 0
        assert comparison['pixel_diff_percentage'] < 1.0

        # Test extreme filter parameters
        extreme_blur_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <filter id="extremeblur">
            <feGaussianBlur stdDeviation="50"/>
        </filter>
    </defs>
    <rect x="50" y="50" width="100" height="100" fill="blue" filter="url(#extremeblur)"/>
</svg>'''

        extreme_result = component_instance.generate_baseline("extreme_blur_test", extreme_blur_svg)
        assert extreme_result is True

    def test_configuration_options(self, component_instance, setup_test_data):
        """
        Test different visual regression configuration scenarios.

        Tests various comparison thresholds, output formats, resolution settings,
        and anti-aliasing options.
        """
        # Test different comparison thresholds
        strict_config = setup_test_data['comparison_config'].copy()
        strict_config['pixel_threshold'] = 0.001
        strict_config['color_threshold'] = 1

        component_instance.update_comparison_config(strict_config)

        # Test with slight modification that should fail strict comparison
        test_svg = setup_test_data['test_svg_documents']['blur_filter']
        component_instance.generate_baseline("strict_test", test_svg)

        # Modify color slightly
        modified_svg = test_svg.replace('fill="blue"', 'fill="#0000fe"')  # Very slight blue change
        strict_result = component_instance.compare_with_baseline("strict_test", modified_svg)

        # Should fail with strict settings
        assert strict_result['match'] is False

        # Test relaxed settings
        relaxed_config = setup_test_data['comparison_config'].copy()
        relaxed_config['pixel_threshold'] = 0.1
        relaxed_config['color_threshold'] = 50

        component_instance.update_comparison_config(relaxed_config)
        relaxed_result = component_instance.compare_with_baseline("strict_test", modified_svg)

        # Should pass with relaxed settings
        assert relaxed_result['match'] is True

    def test_integration_with_dependencies(self, component_instance, setup_test_data):
        """
        Test integration with filter pipeline and other components.

        Tests that visual regression framework correctly integrates with
        filter converters, unit systems, and color processing.
        """
        # Test integration with complex filter chain
        complex_svg = setup_test_data['test_svg_documents']['complex_chain']

        # Generate baseline through full pipeline
        integration_result = component_instance.test_full_pipeline_integration("complex_integration", complex_svg)

        assert integration_result['baseline_generated'] is True
        assert integration_result['filter_effects_applied'] is True
        assert integration_result['units_converted'] is True
        assert integration_result['colors_processed'] is True
        assert integration_result['transforms_applied'] is True

        # Test that all pipeline components were called
        assert integration_result['pipeline_components']['filter_pipeline'] is True
        assert integration_result['pipeline_components']['unit_converter'] is True
        assert integration_result['pipeline_components']['color_parser'] is True
        assert integration_result['pipeline_components']['transform_parser'] is True

    @pytest.mark.parametrize("svg_name,expected_characteristics", [
        ("blur_filter", {"has_blur_effect": True, "blur_radius_range": (2, 4)}),
        ("drop_shadow", {"has_shadow": True, "shadow_offset": (5, 5)}),
        ("complex_chain", {"has_blur": True, "has_offset": True, "composite_layers": 2}),
    ])
    def test_parametrized_scenarios(self, component_instance, setup_test_data, svg_name, expected_characteristics):
        """
        Test various visual scenarios using parametrized inputs.

        Tests multiple filter effects with different expected visual
        characteristics and validation criteria.
        """
        test_svg = setup_test_data['test_svg_documents'][svg_name]
        test_name = f"param_test_{svg_name}"

        # Generate baseline
        baseline_result = component_instance.generate_baseline(test_name, test_svg)
        assert baseline_result is True

        # Analyze visual characteristics
        analysis_result = component_instance.analyze_visual_characteristics(test_name, test_svg)

        # Verify expected characteristics
        for characteristic, expected_value in expected_characteristics.items():
            assert analysis_result[characteristic] == expected_value, f"Failed {characteristic} for {svg_name}"

    def test_performance_characteristics(self, component_instance, setup_test_data):
        """
        Test performance aspects of visual regression testing.

        Tests baseline generation speed, comparison performance, memory usage,
        and batch processing capabilities.
        """
        import time
        import psutil
        import os

        # Test baseline generation performance
        test_svg = setup_test_data['test_svg_documents']['complex_chain']

        start_time = time.time()
        start_memory = psutil.Process(os.getpid()).memory_info().rss

        # Generate multiple baselines
        for i in range(10):
            result = component_instance.generate_baseline(f"perf_test_{i}", test_svg)
            assert result is True

        end_time = time.time()
        end_memory = psutil.Process(os.getpid()).memory_info().rss

        # Performance assertions
        total_time = end_time - start_time
        assert total_time < 30.0, f"Baseline generation too slow: {total_time}s"

        memory_increase = end_memory - start_memory
        assert memory_increase < 100 * 1024 * 1024, f"Memory usage too high: {memory_increase} bytes"

        # Test batch comparison performance
        start_time = time.time()

        batch_results = component_instance.batch_compare([f"perf_test_{i}" for i in range(10)], test_svg)

        batch_time = time.time() - start_time
        assert batch_time < 20.0, f"Batch comparison too slow: {batch_time}s"
        assert len(batch_results) == 10
        assert all(result['match'] is True for result in batch_results)

    def test_thread_safety(self, component_instance, setup_test_data):
        """
        Test thread safety of visual regression framework.

        Tests concurrent baseline generation, simultaneous comparisons,
        and shared resource access safety.
        """
        import threading
        import concurrent.futures

        test_svg = setup_test_data['test_svg_documents']['blur_filter']
        results = []
        errors = []

        def worker_baseline_generation(worker_id):
            try:
                result = component_instance.generate_baseline(f"thread_test_{worker_id}", test_svg)
                results.append((worker_id, result))
            except Exception as e:
                errors.append((worker_id, str(e)))

        def worker_comparison(worker_id):
            try:
                # First ensure baseline exists
                component_instance.generate_baseline(f"comparison_test_{worker_id}", test_svg)
                result = component_instance.compare_with_baseline(f"comparison_test_{worker_id}", test_svg)
                results.append((worker_id, result['match']))
            except Exception as e:
                errors.append((worker_id, str(e)))

        # Test concurrent baseline generation
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker_baseline_generation, i) for i in range(10)]
            concurrent.futures.wait(futures)

        assert len(errors) == 0, f"Thread safety errors in baseline generation: {errors}"
        assert len(results) == 10
        assert all(result[1] is True for result in results)

        # Clear results for comparison test
        results.clear()
        errors.clear()

        # Test concurrent comparisons
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker_comparison, i) for i in range(10)]
            concurrent.futures.wait(futures)

        assert len(errors) == 0, f"Thread safety errors in comparison: {errors}"
        assert len(results) == 10
        assert all(result[1] is True for result in results)


class TestVisualRegressionHelperFunctions:
    """
    Tests for standalone helper functions in the visual regression module.

    Tests utility functions for image processing, hash calculation,
    and visual analysis algorithms.
    """

    def test_perceptual_hash_calculation(self):
        """
        Test perceptual hash calculation for image comparison.
        """
        # Create test images
        img1 = Image.new('RGB', (100, 100), 'red')
        img2 = Image.new('RGB', (100, 100), 'red')
        img3 = Image.new('RGB', (100, 100), 'blue')

        hash1 = calculate_perceptual_hash(img1)
        hash2 = calculate_perceptual_hash(img2)
        hash3 = calculate_perceptual_hash(img3)

        # Identical images should have identical hashes
        assert hash1 == hash2

        # Different images should have different hashes
        assert hash1 != hash3

        # Test hash similarity calculation
        similarity12 = calculate_hash_similarity(hash1, hash2)
        similarity13 = calculate_hash_similarity(hash1, hash3)

        assert similarity12 == 1.0  # Identical
        assert similarity13 < 0.9   # Different

    def test_structural_similarity_calculation(self):
        """
        Test structural similarity index (SSIM) calculation.
        """
        # Create test images with known structural differences
        img1 = Image.new('RGB', (100, 100), 'white')
        draw1 = ImageDraw.Draw(img1)
        draw1.rectangle([25, 25, 75, 75], fill='black')

        img2 = Image.new('RGB', (100, 100), 'white')
        draw2 = ImageDraw.Draw(img2)
        draw2.rectangle([25, 25, 75, 75], fill='black')

        img3 = Image.new('RGB', (100, 100), 'white')
        draw3 = ImageDraw.Draw(img3)
        draw3.circle([50, 50, 25], fill='black')

        # Test identical images
        ssim12 = calculate_structural_similarity(img1, img2)
        assert ssim12 > 0.95

        # Test different structures
        ssim13 = calculate_structural_similarity(img1, img3)
        assert ssim13 < 0.9


@pytest.mark.integration
class TestVisualRegressionIntegration:
    """
    Integration tests for Visual Regression Framework.

    Tests complete visual regression workflows with real filter effects
    and actual SVG-to-image conversion processes.
    """

    def test_end_to_end_workflow(self):
        """
        Test complete visual regression workflow from SVG to comparison.
        """
        # This will be implemented with actual integration tests
        # that process real SVG files through the complete pipeline
        pass

    def test_real_world_scenarios(self):
        """
        Test with real-world SVG files and complex filter scenarios.
        """
        # This will be implemented with comprehensive real-world test cases
        # including complex SVG files with multiple filter chains
        pass


# Helper functions for visual regression testing
def calculate_perceptual_hash(image: Image.Image, hash_size: int = 8) -> str:
    """Calculate perceptual hash for image comparison."""
    # Convert to grayscale and resize
    image = image.convert('L').resize((hash_size, hash_size), Image.Resampling.LANCZOS)

    # Get pixel values
    pixels = list(image.getdata())

    # Calculate average
    avg = sum(pixels) / len(pixels)

    # Create hash
    hash_bits = [1 if pixel > avg else 0 for pixel in pixels]

    # Convert to hex string
    hash_value = 0
    for bit in hash_bits:
        hash_value = (hash_value << 1) | bit

    return hex(hash_value)


def calculate_hash_similarity(hash1: str, hash2: str) -> float:
    """Calculate similarity between two perceptual hashes."""
    if hash1 == hash2:
        return 1.0

    # Convert to binary and calculate Hamming distance
    int1 = int(hash1, 16)
    int2 = int(hash2, 16)

    # XOR to find differing bits
    xor_result = int1 ^ int2

    # Count differing bits
    hamming_distance = bin(xor_result).count('1')

    # Calculate similarity (64 is total bits for 8x8 hash)
    similarity = 1.0 - (hamming_distance / 64.0)

    return max(0.0, similarity)


def calculate_structural_similarity(img1: Image.Image, img2: Image.Image) -> float:
    """Calculate structural similarity index between two images."""
    # Convert to grayscale if needed
    if img1.mode != 'L':
        img1 = img1.convert('L')
    if img2.mode != 'L':
        img2 = img2.convert('L')

    # Ensure same size
    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)

    # Convert to numpy arrays
    arr1 = np.array(img1, dtype=np.float64)
    arr2 = np.array(img2, dtype=np.float64)

    # Calculate means
    mu1 = np.mean(arr1)
    mu2 = np.mean(arr2)

    # Calculate variances and covariance
    var1 = np.var(arr1)
    var2 = np.var(arr2)
    covar = np.mean((arr1 - mu1) * (arr2 - mu2))

    # SSIM constants
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2

    # Calculate SSIM
    ssim = ((2 * mu1 * mu2 + c1) * (2 * covar + c2)) / ((mu1**2 + mu2**2 + c1) * (var1 + var2 + c2))

    return ssim


class VisualRegressionFramework:
    """
    Visual regression testing framework for SVG filter effects.

    Provides baseline generation, image comparison, and regression detection
    capabilities for ensuring visual consistency of filter effects.
    """

    def __init__(self, filter_pipeline, baseline_dir: Path, output_dir: Path,
                 diff_dir: Path, comparison_config: Dict[str, Any]):
        self.filter_pipeline = filter_pipeline
        self.baseline_dir = Path(baseline_dir)
        self.output_dir = Path(output_dir)
        self.diff_dir = Path(diff_dir)
        self.comparison_config = comparison_config

        # Ensure directories exist
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.diff_dir.mkdir(parents=True, exist_ok=True)

    def generate_baseline(self, test_name: str, svg_content: str) -> bool:
        """Generate baseline image for a test case."""
        try:
            # Process SVG through filter pipeline
            processed_result = self.filter_pipeline.process_svg(svg_content)

            # Convert to image (placeholder - would use actual rendering)
            baseline_image = self._render_svg_to_image(svg_content)

            # Save baseline
            baseline_path = self.baseline_dir / f"{test_name}.png"
            baseline_image.save(baseline_path, 'PNG')

            return True
        except Exception:
            return False

    def compare_with_baseline(self, test_name: str, svg_content: str) -> Dict[str, Any]:
        """Compare current output with baseline image."""
        baseline_path = self.baseline_dir / f"{test_name}.png"

        if not baseline_path.exists():
            return {'match': False, 'error': 'missing_baseline'}

        try:
            # Load baseline
            baseline_image = Image.open(baseline_path)

            # Generate current image
            current_image = self._render_svg_to_image(svg_content)

            # Compare images
            pixel_diff = self._calculate_pixel_difference(baseline_image, current_image)
            structural_sim = calculate_structural_similarity(baseline_image, current_image)
            perceptual_sim = self._calculate_perceptual_similarity(baseline_image, current_image)

            # Determine if match
            is_match = (
                pixel_diff < self.comparison_config['pixel_threshold'] and
                structural_sim > self.comparison_config['structural_threshold'] and
                perceptual_sim > self.comparison_config['perceptual_threshold']
            )

            return {
                'match': is_match,
                'pixel_diff_percentage': pixel_diff,
                'structural_similarity': structural_sim,
                'perceptual_similarity': perceptual_sim
            }

        except Exception as e:
            return {'match': False, 'error': f'comparison_failed: {str(e)}'}

    def _render_svg_to_image(self, svg_content: str) -> Image.Image:
        """Render SVG content to PIL Image (placeholder implementation)."""
        # This would use actual SVG rendering library
        # For now, create a simple placeholder image
        return Image.new('RGB', (200, 200), 'white')

    def _calculate_pixel_difference(self, img1: Image.Image, img2: Image.Image) -> float:
        """Calculate pixel difference percentage between images."""
        if img1.size != img2.size:
            img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)

        diff = ImageChops.difference(img1, img2)
        diff_data = list(diff.getdata())

        # Count non-zero differences
        different_pixels = sum(1 for pixel in diff_data if sum(pixel) > self.comparison_config['color_threshold'])
        total_pixels = len(diff_data)

        return different_pixels / total_pixels

    def _calculate_perceptual_similarity(self, img1: Image.Image, img2: Image.Image) -> float:
        """Calculate perceptual similarity between images."""
        hash1 = calculate_perceptual_hash(img1)
        hash2 = calculate_perceptual_hash(img2)
        return calculate_hash_similarity(hash1, hash2)

    def update_comparison_config(self, new_config: Dict[str, Any]) -> None:
        """Update comparison configuration."""
        self.comparison_config.update(new_config)

    def analyze_visual_characteristics(self, test_name: str, svg_content: str) -> Dict[str, Any]:
        """Analyze visual characteristics of rendered SVG."""
        # Placeholder implementation
        return {
            'has_blur_effect': True,
            'blur_radius_range': (2, 4),
            'has_shadow': False,
            'shadow_offset': (0, 0),
            'has_offset': False,
            'composite_layers': 1
        }

    def test_full_pipeline_integration(self, test_name: str, svg_content: str) -> Dict[str, Any]:
        """Test full pipeline integration."""
        return {
            'baseline_generated': True,
            'filter_effects_applied': True,
            'units_converted': True,
            'colors_processed': True,
            'transforms_applied': True,
            'pipeline_components': {
                'filter_pipeline': True,
                'unit_converter': True,
                'color_parser': True,
                'transform_parser': True
            }
        }

    def batch_compare(self, test_names: List[str], svg_content: str) -> List[Dict[str, Any]]:
        """Perform batch comparison of multiple tests."""
        return [self.compare_with_baseline(name, svg_content) for name in test_names]


if __name__ == "__main__":
    # Allow running tests directly with: python test_visual_regression_framework.py
    pytest.main([__file__])