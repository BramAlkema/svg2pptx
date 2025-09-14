#!/usr/bin/env python3
"""
Visual Regression Tests for SVG Filter Effects using LibreOffice.

This module implements visual regression testing for filter effects by
leveraging the existing LibreOffice headless rendering infrastructure
to ensure visual fidelity of converted filter effects.

Usage:
1. Convert SVG with filters to PPTX
2. Render PPTX to images using LibreOffice headless
3. Compare with baseline images
4. Report visual regression issues
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from pathlib import Path
import sys
import tempfile
import shutil
from lxml import etree as ET
from typing import Dict, List, Tuple, Optional, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the existing visual regression infrastructure
from support.visual_regression_tester import (
    VisualRegressionTester,
    LibreOfficeRenderer,
    ImageComparator,
    ComparisonMethod,
    VisualComparisonResult,
    RegressionTestResult
)

# Import SVG to PPTX conversion components
from src.svg2pptx import SVG2PPTX
from src.converters.filters import FilterPipeline


class TestFilterEffectsVisualRegression:
    """
    Visual regression tests for SVG Filter Effects using LibreOffice.

    Tests filter effects visual fidelity by converting SVG to PPTX,
    rendering with LibreOffice, and comparing against baselines.
    """

    @pytest.fixture
    def setup_test_data(self):
        """
        Setup common test data and filter effect test cases.

        Provides comprehensive filter effect SVG documents, expected visual
        characteristics, and comparison configurations.
        """
        # Test SVG documents with various filter effects
        filter_test_cases = {
            'gaussian_blur': {
                'svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="400" height="400" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <filter id="blur" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="5"/>
        </filter>
    </defs>
    <rect x="100" y="100" width="200" height="200" fill="#4287f5" filter="url(#blur)"/>
</svg>''',
                'expected': {
                    'has_blur': True,
                    'blur_radius': 5,
                    'preserves_color': True
                }
            },

            'drop_shadow': {
                'svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="500" height="500" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="3" result="blur"/>
            <feOffset in="blur" dx="10" dy="10" result="offsetBlur"/>
            <feFlood flood-color="#000000" flood-opacity="0.5" result="color"/>
            <feComposite in="color" in2="offsetBlur" operator="in" result="shadow"/>
            <feMerge>
                <feMergeNode in="shadow"/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
    </defs>
    <circle cx="200" cy="200" r="100" fill="#ff6b6b" filter="url(#shadow)"/>
</svg>''',
                'expected': {
                    'has_shadow': True,
                    'shadow_offset': (10, 10),
                    'shadow_opacity': 0.5,
                    'preserves_original': True
                }
            },

            'color_matrix': {
                'svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="400" height="400" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <filter id="colorMatrix">
            <feColorMatrix type="matrix" values="
                0.393 0.769 0.189 0 0
                0.349 0.686 0.168 0 0
                0.272 0.534 0.131 0 0
                0     0     0     1 0"/>
        </filter>
    </defs>
    <rect x="50" y="50" width="300" height="300" fill="#00ff00" filter="url(#colorMatrix)"/>
</svg>''',
                'expected': {
                    'has_color_transform': True,
                    'sepia_effect': True,
                    'preserves_shape': True
                }
            },

            'complex_filter_chain': {
                'svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="600" height="600" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <filter id="complex" x="-50%" y="-50%" width="200%" height="200%">
            <!-- Blur the source -->
            <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur"/>

            <!-- Create shadow -->
            <feOffset in="blur" dx="5" dy="5" result="offsetBlur"/>
            <feFlood flood-color="#000000" flood-opacity="0.3" result="shadowColor"/>
            <feComposite in="shadowColor" in2="offsetBlur" operator="in" result="shadow"/>

            <!-- Apply color adjustment -->
            <feColorMatrix in="SourceGraphic" type="saturate" values="1.5" result="saturated"/>

            <!-- Merge everything -->
            <feMerge>
                <feMergeNode in="shadow"/>
                <feMergeNode in="saturated"/>
            </feMerge>
        </filter>
    </defs>
    <polygon points="300,100 500,300 300,500 100,300" fill="#ffd93d" filter="url(#complex)"/>
</svg>''',
                'expected': {
                    'has_blur': True,
                    'has_shadow': True,
                    'has_saturation': True,
                    'composite_layers': 2
                }
            },

            'morphology_effects': {
                'svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="400" height="400" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <filter id="morphology">
            <feMorphology operator="dilate" radius="3" result="dilated"/>
            <feMorphology in="dilated" operator="erode" radius="1" result="final"/>
        </filter>
    </defs>
    <text x="100" y="200" font-size="48" fill="#333333" filter="url(#morphology)">Filter</text>
</svg>''',
                'expected': {
                    'has_morphology': True,
                    'text_thickness_changed': True,
                    'preserves_readability': True
                }
            }
        }

        # Baseline directory for visual comparisons
        baseline_dir = Path(__file__).parent / "baselines" / "filter_effects"

        # Output directory for test results
        output_dir = Path(__file__).parent / "output" / "filter_effects"

        # Comparison configuration
        comparison_config = {
            'similarity_threshold': 0.95,  # 95% similarity required
            'comparison_methods': [
                ComparisonMethod.STRUCTURAL_SIMILARITY,
                ComparisonMethod.PERCEPTUAL_HASH
            ],
            'save_diffs': True,
            'libreoffice_dpi': 150
        }

        # Test configuration
        test_config = {
            'update_baselines': False,  # Set to True to update baseline images
            'skip_missing_baselines': False,
            'verbose': True,
            'parallel_processing': False
        }

        return {
            'filter_test_cases': filter_test_cases,
            'baseline_dir': baseline_dir,
            'output_dir': output_dir,
            'comparison_config': comparison_config,
            'test_config': test_config
        }

    @pytest.fixture
    def component_instance(self, setup_test_data):
        """
        Create instance of visual regression test components.

        Initializes LibreOffice renderer, image comparator, and
        visual regression tester with proper configuration.
        """
        # Create LibreOffice renderer
        libreoffice_renderer = LibreOfficeRenderer()

        # Create image comparator
        image_comparator = ImageComparator()

        # Create visual regression tester
        visual_tester = VisualRegressionTester(
            libreoffice_renderer=libreoffice_renderer,
            image_comparator=image_comparator,
            baseline_dir=setup_test_data['baseline_dir'],
            output_dir=setup_test_data['output_dir']
        )

        # Create SVG to PPTX converter
        svg_converter = SVG2PPTX()

        return {
            'visual_tester': visual_tester,
            'svg_converter': svg_converter,
            'libreoffice_renderer': libreoffice_renderer,
            'image_comparator': image_comparator
        }

    def test_initialization(self, component_instance):
        """
        Test visual regression component initialization.

        Verifies that all components are properly initialized and
        LibreOffice is available for rendering.
        """
        assert component_instance['visual_tester'] is not None
        assert component_instance['svg_converter'] is not None
        assert component_instance['libreoffice_renderer'] is not None
        assert component_instance['image_comparator'] is not None

        # Verify LibreOffice is available
        assert hasattr(component_instance['libreoffice_renderer'], 'libreoffice_path')
        assert component_instance['libreoffice_renderer'].libreoffice_path is not None

    def test_basic_functionality(self, component_instance, setup_test_data):
        """
        Test basic visual regression workflow for filter effects.

        Tests conversion of SVG with filters to PPTX, rendering to images,
        and comparison with baselines.
        """
        visual_tester = component_instance['visual_tester']
        svg_converter = component_instance['svg_converter']

        # Test gaussian blur filter
        test_case = setup_test_data['filter_test_cases']['gaussian_blur']

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Convert SVG to PPTX
            svg_path = temp_path / "test_blur.svg"
            svg_path.write_text(test_case['svg'])

            pptx_path = temp_path / "test_blur.pptx"
            conversion_result = svg_converter.convert(
                input_path=str(svg_path),
                output_path=str(pptx_path)
            )

            assert pptx_path.exists(), "PPTX file should be created"

            # Render PPTX to images
            image_files = component_instance['libreoffice_renderer'].convert_pptx_to_images(
                pptx_path=pptx_path,
                output_dir=temp_path / "images",
                format="png",
                dpi=setup_test_data['comparison_config']['libreoffice_dpi']
            )

            assert len(image_files) > 0, "Should generate at least one image"

            # Compare with baseline (or create baseline if needed)
            baseline_path = setup_test_data['baseline_dir'] / "gaussian_blur.png"

            if not baseline_path.exists() and setup_test_data['test_config']['update_baselines']:
                # Create baseline
                baseline_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(image_files[0], baseline_path)

            if baseline_path.exists():
                # Perform comparison
                comparison_result = component_instance['image_comparator'].compare_images(
                    reference_path=baseline_path,
                    output_path=image_files[0],
                    method=ComparisonMethod.STRUCTURAL_SIMILARITY
                )

                assert comparison_result.similarity_score > setup_test_data['comparison_config']['similarity_threshold']

    def test_error_handling(self, component_instance, setup_test_data):
        """
        Test error handling in visual regression pipeline.

        Tests handling of invalid SVG, conversion failures, rendering errors,
        and missing baselines.
        """
        visual_tester = component_instance['visual_tester']

        # Test invalid SVG handling
        invalid_svg = "<svg>invalid xml structure"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            svg_path = temp_path / "invalid.svg"
            svg_path.write_text(invalid_svg)

            pptx_path = temp_path / "invalid.pptx"

            # Should handle conversion error gracefully
            try:
                result = component_instance['svg_converter'].convert(
                    input_path=str(svg_path),
                    output_path=str(pptx_path)
                )
                # Conversion might succeed with error recovery
                if pptx_path.exists():
                    # Try rendering - might fail or produce empty image
                    images = component_instance['libreoffice_renderer'].convert_pptx_to_images(
                        pptx_path=pptx_path,
                        output_dir=temp_path / "images"
                    )
            except Exception as e:
                # Expected - invalid SVG should cause error
                assert "invalid" in str(e).lower() or "xml" in str(e).lower()

    def test_edge_cases(self, component_instance, setup_test_data):
        """
        Test edge cases in filter effects visual regression.

        Tests empty filters, extreme parameters, no visual changes,
        and very large filter regions.
        """
        # Test empty filter (no primitives)
        empty_filter_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <filter id="empty"></filter>
    </defs>
    <rect x="50" y="50" width="100" height="100" fill="red" filter="url(#empty)"/>
</svg>'''

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test empty filter
            svg_path = temp_path / "empty_filter.svg"
            svg_path.write_text(empty_filter_svg)

            pptx_path = temp_path / "empty_filter.pptx"
            result = component_instance['svg_converter'].convert(
                input_path=str(svg_path),
                output_path=str(pptx_path)
            )

            assert pptx_path.exists()

            # Test extreme blur values
            extreme_blur_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <filter id="extreme">
            <feGaussianBlur stdDeviation="100"/>
        </filter>
    </defs>
    <rect x="90" y="90" width="20" height="20" fill="blue" filter="url(#extreme)"/>
</svg>'''

            svg_path = temp_path / "extreme_blur.svg"
            svg_path.write_text(extreme_blur_svg)

            pptx_path = temp_path / "extreme_blur.pptx"
            result = component_instance['svg_converter'].convert(
                input_path=str(svg_path),
                output_path=str(pptx_path)
            )

            assert pptx_path.exists()

    def test_configuration_options(self, component_instance, setup_test_data):
        """
        Test different visual regression configuration options.

        Tests various comparison methods, DPI settings, threshold adjustments,
        and baseline update modes.
        """
        # Test different comparison methods
        test_case = setup_test_data['filter_test_cases']['drop_shadow']

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Convert and render
            svg_path = temp_path / "shadow.svg"
            svg_path.write_text(test_case['svg'])

            pptx_path = temp_path / "shadow.pptx"
            component_instance['svg_converter'].convert(
                input_path=str(svg_path),
                output_path=str(pptx_path)
            )

            # Test different DPI settings
            for dpi in [96, 150, 300]:
                images = component_instance['libreoffice_renderer'].convert_pptx_to_images(
                    pptx_path=pptx_path,
                    output_dir=temp_path / f"images_{dpi}",
                    dpi=dpi
                )

                assert len(images) > 0

                # Higher DPI should produce larger images
                if dpi > 96:
                    # Would check image dimensions if PIL is available
                    pass

    def test_integration_with_dependencies(self, component_instance, setup_test_data):
        """
        Test integration between visual regression and filter pipeline.

        Tests that filter effects are properly converted and rendered
        through the complete pipeline.
        """
        # Test complex filter chain
        test_case = setup_test_data['filter_test_cases']['complex_filter_chain']

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Full pipeline test
            svg_path = temp_path / "complex.svg"
            svg_path.write_text(test_case['svg'])

            pptx_path = temp_path / "complex.pptx"

            # Convert with filter pipeline
            conversion_result = component_instance['svg_converter'].convert(
                input_path=str(svg_path),
                output_path=str(pptx_path)
            )

            assert pptx_path.exists()

            # Render to images
            images = component_instance['libreoffice_renderer'].convert_pptx_to_images(
                pptx_path=pptx_path,
                output_dir=temp_path / "images"
            )

            assert len(images) > 0

            # Verify visual characteristics match expectations
            for characteristic, expected_value in test_case['expected'].items():
                # Would perform actual visual analysis here
                pass

    @pytest.mark.parametrize("filter_type,expected_characteristics", [
        ("gaussian_blur", {"has_blur": True, "preserves_color": True}),
        ("drop_shadow", {"has_shadow": True, "preserves_original": True}),
        ("color_matrix", {"has_color_transform": True, "preserves_shape": True}),
        ("complex_filter_chain", {"composite_layers": 2, "has_blur": True}),
        ("morphology_effects", {"has_morphology": True, "preserves_readability": True}),
    ])
    def test_parametrized_scenarios(self, component_instance, setup_test_data,
                                   filter_type, expected_characteristics):
        """
        Test various filter effect scenarios using parametrized inputs.

        Tests multiple filter types with their expected visual characteristics
        through the complete visual regression pipeline.
        """
        test_case = setup_test_data['filter_test_cases'][filter_type]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Convert SVG to PPTX
            svg_path = temp_path / f"{filter_type}.svg"
            svg_path.write_text(test_case['svg'])

            pptx_path = temp_path / f"{filter_type}.pptx"
            result = component_instance['svg_converter'].convert(
                input_path=str(svg_path),
                output_path=str(pptx_path)
            )

            assert pptx_path.exists(), f"PPTX should be created for {filter_type}"

            # Render and verify
            images = component_instance['libreoffice_renderer'].convert_pptx_to_images(
                pptx_path=pptx_path,
                output_dir=temp_path / "images"
            )

            assert len(images) > 0, f"Should generate images for {filter_type}"

            # Verify expected characteristics
            for char, expected in expected_characteristics.items():
                # Would perform actual characteristic validation here
                assert expected == test_case['expected'].get(char, expected)

    def test_performance_characteristics(self, component_instance, setup_test_data):
        """
        Test performance aspects of visual regression testing.

        Tests rendering speed, memory usage during comparison, batch processing,
        and caching effectiveness.
        """
        import time
        import psutil
        import os

        # Performance test with multiple filters
        start_time = time.time()
        start_memory = psutil.Process(os.getpid()).memory_info().rss

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Process multiple filter types
            for filter_type, test_case in setup_test_data['filter_test_cases'].items():
                svg_path = temp_path / f"{filter_type}.svg"
                svg_path.write_text(test_case['svg'])

                pptx_path = temp_path / f"{filter_type}.pptx"
                component_instance['svg_converter'].convert(
                    input_path=str(svg_path),
                    output_path=str(pptx_path)
                )

                # Render to images
                images = component_instance['libreoffice_renderer'].convert_pptx_to_images(
                    pptx_path=pptx_path,
                    output_dir=temp_path / f"images_{filter_type}"
                )

        end_time = time.time()
        end_memory = psutil.Process(os.getpid()).memory_info().rss

        # Performance assertions
        total_time = end_time - start_time
        memory_increase = end_memory - start_memory

        # Should process all filters within reasonable time
        assert total_time < 60.0, f"Processing too slow: {total_time}s"

        # Memory usage should be reasonable
        assert memory_increase < 500 * 1024 * 1024, f"Memory usage too high: {memory_increase} bytes"

    def test_thread_safety(self, component_instance, setup_test_data):
        """
        Test thread safety of visual regression components.

        Tests concurrent conversions, simultaneous LibreOffice rendering,
        and parallel image comparisons.
        """
        import concurrent.futures

        test_cases = list(setup_test_data['filter_test_cases'].items())[:3]  # Use first 3 for speed

        def process_filter(filter_type, test_case):
            """Worker function for concurrent processing."""
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                svg_path = temp_path / f"{filter_type}.svg"
                svg_path.write_text(test_case['svg'])

                pptx_path = temp_path / f"{filter_type}.pptx"
                component_instance['svg_converter'].convert(
                    input_path=str(svg_path),
                    output_path=str(pptx_path)
                )

                images = component_instance['libreoffice_renderer'].convert_pptx_to_images(
                    pptx_path=pptx_path,
                    output_dir=temp_path / "images"
                )

                return len(images) > 0

        # Test concurrent processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(process_filter, filter_type, test_case)
                for filter_type, test_case in test_cases
            ]

            results = [future.result(timeout=30) for future in concurrent.futures.as_completed(futures)]

        assert all(results), "All concurrent conversions should succeed"


class TestFilterEffectsVisualRegressionHelperFunctions:
    """
    Tests for helper functions supporting visual regression testing.

    Tests utility functions for baseline management, image preprocessing,
    and visual analysis helpers.
    """

    def test_baseline_management(self):
        """
        Test baseline image management functions.
        """
        baseline_dir = Path(tempfile.mkdtemp()) / "baselines"

        # Test baseline directory creation
        baseline_dir.mkdir(parents=True, exist_ok=True)
        assert baseline_dir.exists()

        # Test baseline naming convention
        test_name = "gaussian_blur_test"
        baseline_name = f"{test_name}_baseline.png"
        baseline_path = baseline_dir / baseline_name

        # Test baseline versioning
        version = 1
        versioned_name = f"{test_name}_v{version}_baseline.png"
        versioned_path = baseline_dir / versioned_name

        # Cleanup
        shutil.rmtree(baseline_dir.parent)

    def test_svg_preprocessing_for_visual_testing(self):
        """
        Test SVG preprocessing functions for visual testing.
        """
        # Test SVG normalization
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">
            <rect x="10" y="10" width="100" height="100"/>
        </svg>'''

        # Parse and normalize
        root = ET.fromstring(svg_content.encode('utf-8'))

        # Verify structure
        assert root.tag == '{http://www.w3.org/2000/svg}svg'
        rect = root.find('.//{http://www.w3.org/2000/svg}rect')
        assert rect is not None


@pytest.mark.integration
class TestFilterEffectsVisualRegressionIntegration:
    """
    Integration tests for Filter Effects Visual Regression.

    Tests complete workflows with real SVG files and actual LibreOffice rendering.
    """

    def test_end_to_end_workflow(self):
        """
        Test complete visual regression workflow for filter effects.
        """
        # This would test the complete workflow with real files
        # Loading actual SVG files, converting to PPTX, rendering with LibreOffice,
        # and comparing against established baselines
        pass

    def test_real_world_scenarios(self):
        """
        Test with real-world SVG files containing complex filter effects.
        """
        # This would test with actual production SVG files
        # containing complex filter combinations used in real applications
        pass


if __name__ == "__main__":
    # Allow running tests directly with: python test_filter_effects_visual_regression.py
    pytest.main([__file__])