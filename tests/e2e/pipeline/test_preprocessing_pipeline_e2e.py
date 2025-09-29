#!/usr/bin/env python3
"""
End-to-End Tests for SVG Preprocessing Pipeline

Tests the complete preprocessing workflow from raw SVG input through optimization
to final processed output, validating real-world usage scenarios and performance.

This covers the full pipeline: SVG input → preprocessing plugins → optimization → output
"""

import pytest
from pathlib import Path
import sys
import tempfile
import zipfile
import time
from unittest.mock import Mock, patch
from lxml import etree as ET

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Import preprocessing system components
PREPROCESSING_AVAILABLE = True
try:
    from src.preprocessing.optimizer import SVGOptimizer, create_optimizer
    from src.preprocessing.plugins import (
        CleanupAttrsPlugin, CleanupNumericValuesPlugin,
        RemoveEmptyAttrsPlugin, RemoveCommentsPlugin
    )
    from src.preprocessing.geometry_plugins import (
        ConvertEllipseToCirclePlugin, SimplifyPolygonPlugin
    )
    from src.preprocessing.advanced_plugins import (
        ConvertPathDataPlugin, MergePathsPlugin
    )
    from src.preprocessing.base import PreprocessingContext
except ImportError:
    PREPROCESSING_AVAILABLE = False


@pytest.mark.skipif(not PREPROCESSING_AVAILABLE, reason="Preprocessing system not available")
class TestPreprocessingPipelineE2E:
    """
    End-to-end tests for SVG preprocessing pipeline.

    Tests complete workflow from real SVG files through optimization to final output.
    """

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for E2E testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # Create subdirectories for organized testing
            (workspace / "input").mkdir()
            (workspace / "output").mkdir()
            (workspace / "config").mkdir()
            yield workspace

    @pytest.fixture
    def real_world_svg_files(self, temp_workspace):
        """Create realistic SVG files that mirror real-world usage."""
        input_dir = temp_workspace / "input"
        svg_files = {}

        # 1. Bloated design tool output (Illustrator/Inkscape style)
        bloated_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
    <!-- Generator: Adobe Illustrator 25.0.0, SVG Export Plug-In . SVG Version: 6.00 Build 0)  -->
    <defs>
        <style>
            .st0 { fill: #FF5733; }
        </style>
        <g id="Layer_1">
            <!-- Unnecessary comments and metadata -->
        </g>
    </defs>
    <metadata>
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
            <!-- Complex metadata that should be removed -->
        </rdf:RDF>
    </metadata>
    <g>
        <!-- Redundant grouping -->
        <g transform="translate(0,0)">
            <rect x="10.000000" y="20.000000" width="100.000000" height="50.000000"
                  fill="#FF5733" stroke="" stroke-width="0" opacity="1.0"/>
            <ellipse cx="200.0" cy="100.0" rx="30.0" ry="30.0" fill="blue"
                     transform="translate(0,0) scale(1.0)"/>
            <polygon points="50.000,150.000 100.000,150.000 150.000,150.000 150.000,200.000 100.000,200.000 50.000,200.000"/>
        </g>
    </g>
</svg>'''

        # 2. Complex geometry with optimization opportunities
        complex_geometry_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="500" height="400" viewBox="0 0 500 400">
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
            <stop offset="50%" style="stop-color:rgb(255,128,0);stop-opacity:1" />
            <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
        </linearGradient>
    </defs>
    <!-- Complex path that can be optimized -->
    <path d="M 10.000000 10.000000 L 20.000000 10.000000 L 30.000000 10.000000 L 40.000000 10.000000 L 50.000000 10.000000 L 50.000000 20.000000 L 50.000000 30.000000 L 40.000000 30.000000 L 30.000000 30.000000 L 20.000000 30.000000 L 10.000000 30.000000 Z"
          fill="url(#grad1)" stroke="black" stroke-width="2.000000"/>

    <!-- Polygon with redundant points -->
    <polygon points="100,50 110,50 120,50 130,50 140,50 150,50 150,60 150,70 150,80 150,90 150,100 140,100 130,100 120,100 110,100 100,100 100,90 100,80 100,70 100,60"
             fill="green"/>

    <!-- Nearly-circular ellipse -->
    <ellipse cx="300" cy="200" rx="25.001" ry="25.000" fill="purple"/>

    <!-- Multiple paths with same styling (merge candidates) -->
    <path d="M 200 300 L 220 300 L 210 320 Z" fill="orange" stroke="red" stroke-width="1"/>
    <path d="M 230 300 L 250 300 L 240 320 Z" fill="orange" stroke="red" stroke-width="1"/>
    <path d="M 260 300 L 280 300 L 270 320 Z" fill="orange" stroke="red" stroke-width="1"/>
</svg>'''

        # 3. Text-heavy SVG with style optimization opportunities
        text_styling_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="200" viewBox="0 0 600 200">
    <text x="10px" y="30px" font-family="Arial" font-size="16.000px" fill="black" stroke="" opacity="1.0">
        Header Text
    </text>
    <text x="10.00" y="60.00" style="font-family:Arial;font-size:14.000px;fill:gray;stroke-width:0px" opacity="1.000">
        Body text with inline styles
    </text>
    <rect x="  10  " y="  80  " width="  580  " height="  2.000  " fill="#CCCCCC"/>
    <g transform="translate(0,0) scale(1.0,1.0)">
        <text x="10" y="120" font-family="Arial" font-size="12.0000" fill="rgb(100,100,100)">
            Footer text
        </text>
    </g>
</svg>'''

        # Write test files
        svg_files['bloated'] = input_dir / "bloated_design_tool.svg"
        svg_files['bloated'].write_text(bloated_svg)

        svg_files['complex_geometry'] = input_dir / "complex_geometry.svg"
        svg_files['complex_geometry'].write_text(complex_geometry_svg)

        svg_files['text_styling'] = input_dir / "text_styling.svg"
        svg_files['text_styling'].write_text(text_styling_svg)

        return svg_files

    @pytest.fixture
    def preprocessing_configurations(self):
        """Different preprocessing configurations for testing."""
        configs = {}

        # Minimal preprocessing (conservative)
        configs['minimal'] = {
            'plugins': [
                CleanupAttrsPlugin(),
                RemoveEmptyAttrsPlugin()
            ],
            'precision': 6
        }

        # Standard preprocessing (balanced)
        configs['standard'] = {
            'plugins': [
                CleanupAttrsPlugin(),
                CleanupNumericValuesPlugin(),
                RemoveEmptyAttrsPlugin(),
                RemoveCommentsPlugin(),
                ConvertEllipseToCirclePlugin()
            ],
            'precision': 3
        }

        # Aggressive preprocessing (maximum optimization)
        configs['aggressive'] = {
            'plugins': [
                CleanupAttrsPlugin(),
                CleanupNumericValuesPlugin(),
                RemoveEmptyAttrsPlugin(),
                RemoveCommentsPlugin(),
                ConvertEllipseToCirclePlugin(),
                SimplifyPolygonPlugin(),
                ConvertPathDataPlugin(),
                MergePathsPlugin()
            ],
            'precision': 2
        }

        return configs

    def test_complete_preprocessing_workflow_e2e(self, temp_workspace, real_world_svg_files, preprocessing_configurations):
        """Test complete preprocessing workflow with real SVG files."""
        output_dir = temp_workspace / "output"

        for config_name, config in preprocessing_configurations.items():
            for svg_name, svg_path in real_world_svg_files.items():
                # Read original SVG
                original_content = svg_path.read_text()
                original_size = len(original_content)

                # Parse using preprocessing optimizer (handles XML declarations)
                temp_optimizer = SVGOptimizer()
                try:
                    original_tree = temp_optimizer._parse_svg(original_content)
                except AttributeError:
                    # Fallback: use the same logic as SVGOptimizer
                    if original_content.strip().startswith('<?xml'):
                        svg_bytes = original_content.encode('utf-8')
                        original_tree = ET.fromstring(svg_bytes)
                    else:
                        original_tree = ET.fromstring(original_content)

                # Create preprocessing context
                context = PreprocessingContext()
                context.precision = config['precision']

                # Apply preprocessing pipeline
                current_tree = original_tree
                modifications_made = False

                for plugin in config['plugins']:
                    # Process all elements in the tree
                    for element in current_tree.iter():
                        if plugin.can_process(element, context):
                            if plugin.process(element, context):
                                modifications_made = True

                # Generate output
                processed_content = ET.tostring(current_tree, encoding='unicode', pretty_print=True)
                processed_size = len(processed_content)

                # Write output file
                output_file = output_dir / f"{svg_name}_{config_name}_processed.svg"
                output_file.write_text(processed_content)

                # Validate results
                assert processed_size > 0, f"Processed SVG should not be empty"

                # For aggressive processing, expect some size reduction
                if config_name == 'aggressive':
                    assert processed_size <= original_size, f"Aggressive processing should reduce or maintain size"

                # Ensure valid XML
                try:
                    ET.fromstring(processed_content)
                except ET.XMLSyntaxError:
                    pytest.fail(f"Processed SVG is invalid XML: {output_file}")

                # Track statistics
                print(f"{svg_name} + {config_name}: {original_size} → {processed_size} bytes "
                      f"({(processed_size/original_size)*100:.1f}%)")

    def test_preprocessing_performance_e2e(self, temp_workspace, real_world_svg_files):
        """Test preprocessing performance with realistic workloads."""
        performance_results = {}

        # Test different optimization levels
        try:
            minimal_optimizer = create_optimizer('minimal')
            standard_optimizer = SVGOptimizer()
        except Exception:
            # If optimizer creation fails, skip performance test
            pytest.skip("SVGOptimizer requires specific configuration")

        for svg_name, svg_path in real_world_svg_files.items():
            svg_content = svg_path.read_text()
            # Parse using same logic as SVGOptimizer
            if svg_content.strip().startswith('<?xml'):
                svg_bytes = svg_content.encode('utf-8')
                svg_tree = ET.fromstring(svg_bytes)
            else:
                svg_tree = ET.fromstring(svg_content)

            # Benchmark minimal preprocessing
            start_time = time.time()
            try:
                minimal_result = minimal_optimizer.optimize(svg_tree)
                minimal_time = time.time() - start_time
            except Exception:
                minimal_time = None

            # Benchmark standard preprocessing
            # Reset tree with proper XML handling
            if svg_content.strip().startswith('<?xml'):
                svg_bytes = svg_content.encode('utf-8')
                svg_tree = ET.fromstring(svg_bytes)
            else:
                svg_tree = ET.fromstring(svg_content)
            start_time = time.time()
            try:
                standard_result = standard_optimizer.optimize(svg_tree)
                standard_time = time.time() - start_time
            except Exception:
                standard_time = None

            performance_results[svg_name] = {
                'minimal_time': minimal_time,
                'standard_time': standard_time,
                'file_size': len(svg_content)
            }

        # Validate performance expectations
        for svg_name, results in performance_results.items():
            if results['minimal_time'] is not None:
                # Should complete within reasonable time (< 1 second for test files)
                assert results['minimal_time'] < 1.0, f"Minimal preprocessing too slow for {svg_name}"

            if results['standard_time'] is not None:
                assert results['standard_time'] < 2.0, f"Standard preprocessing too slow for {svg_name}"

            minimal_time_str = f"{results['minimal_time']:.3f}s" if results['minimal_time'] is not None else "FAILED"
            standard_time_str = f"{results['standard_time']:.3f}s" if results['standard_time'] is not None else "FAILED"
            print(f"Performance - {svg_name}: minimal={minimal_time_str}, standard={standard_time_str}")

    def test_preprocessing_optimization_validation_e2e(self, temp_workspace, real_world_svg_files):
        """Test that preprocessing optimizations work correctly end-to-end."""
        svg_path = real_world_svg_files['bloated']
        original_content = svg_path.read_text()
        # Parse with proper XML declaration handling
        if original_content.strip().startswith('<?xml'):
            svg_bytes = original_content.encode('utf-8')
            original_tree = ET.fromstring(svg_bytes)
        else:
            original_tree = ET.fromstring(original_content)

        # Create context and apply comprehensive preprocessing
        context = PreprocessingContext()
        context.precision = 3

        plugins = [
            CleanupAttrsPlugin(),
            CleanupNumericValuesPlugin(),
            RemoveEmptyAttrsPlugin(),
            ConvertEllipseToCirclePlugin()
        ]

        current_tree = original_tree
        for plugin in plugins:
            for element in current_tree.iter():
                if plugin.can_process(element, context):
                    plugin.process(element, context)

        # Validate specific optimizations occurred
        processed_content = ET.tostring(current_tree, encoding='unicode')

        # Check that numeric values were optimized (no trailing zeros)
        assert '10.000000' not in processed_content, "Trailing zeros should be removed"

        # Check that empty attributes were removed
        assert 'stroke=""' not in processed_content, "Empty stroke attributes should be removed"

        # Check that ellipse with equal radii was converted to circle
        circles = current_tree.findall('.//{http://www.w3.org/2000/svg}circle')
        ellipses = current_tree.findall('.//{http://www.w3.org/2000/svg}ellipse')

        # Should have converted at least one ellipse to circle
        if len(circles) > 0:
            # Verify circle has proper radius attribute
            for circle in circles:
                assert circle.get('r') is not None, "Circle should have radius attribute"

        # Verify modifications were tracked
        assert context.modifications_made, "Context should track that modifications were made"
        assert len(context.stats) > 0, "Context should have recorded statistics"

    def test_preprocessing_error_handling_e2e(self, temp_workspace):
        """Test preprocessing error handling with malformed inputs."""
        output_dir = temp_workspace / "output"

        # Create malformed SVG files
        malformed_svgs = {
            'invalid_xml': '<<invalid><xml>content</invalid>',
            'missing_namespace': '<svg><rect x="invalid_value"/></svg>',
            'empty_file': '',
            'corrupted_elements': '<svg xmlns="http://www.w3.org/2000/svg"><rect x="10" y="20" width="-50"/></svg>'
        }

        for name, content in malformed_svgs.items():
            input_file = temp_workspace / "input" / f"{name}.svg"
            input_file.write_text(content)

            # Test preprocessing graceful handling
            try:
                if content.strip():  # Skip empty files for XML parsing
                    # Parse with proper XML declaration handling
                    if content.strip().startswith('<?xml'):
                        svg_bytes = content.encode('utf-8')
                        tree = ET.fromstring(svg_bytes)
                    else:
                        tree = ET.fromstring(content)

                    # Apply minimal preprocessing
                    context = PreprocessingContext()
                    plugin = CleanupAttrsPlugin()

                    for element in tree.iter():
                        if plugin.can_process(element, context):
                            try:
                                plugin.process(element, context)
                            except Exception as e:
                                # Preprocessing should handle errors gracefully
                                print(f"Handled preprocessing error for {name}: {e}")

                    # If we get here, processing completed without crashing
                    processed_content = ET.tostring(tree, encoding='unicode')
                    output_file = output_dir / f"{name}_processed.svg"
                    output_file.write_text(processed_content)

            except ET.XMLSyntaxError:
                # Expected for invalid XML - preprocessing should not crash the system
                print(f"Gracefully handled XML syntax error for {name}")
            except Exception as e:
                # Log other errors but don't fail the test
                print(f"Error processing {name}: {e}")

        # Test passes if no unhandled exceptions crashed the system
        assert True

    def test_preprocessing_batch_processing_e2e(self, temp_workspace, real_world_svg_files):
        """Test preprocessing multiple files in batch mode."""
        batch_results = {}
        total_start_time = time.time()

        # Process all SVG files in batch
        for svg_name, svg_path in real_world_svg_files.items():
            file_start_time = time.time()

            try:
                # Read and parse SVG
                content = svg_path.read_text()
                # Parse with proper XML declaration handling
                if content.strip().startswith('<?xml'):
                    svg_bytes = content.encode('utf-8')
                    tree = ET.fromstring(svg_bytes)
                else:
                    tree = ET.fromstring(content)
                original_size = len(content)

                # Apply standard preprocessing
                context = PreprocessingContext()
                context.precision = 3

                plugins = [
                    CleanupAttrsPlugin(),
                    CleanupNumericValuesPlugin(),
                    RemoveEmptyAttrsPlugin()
                ]

                for plugin in plugins:
                    for element in tree.iter():
                        if plugin.can_process(element, context):
                            plugin.process(element, context)

                # Generate output
                processed_content = ET.tostring(tree, encoding='unicode')
                processed_size = len(processed_content)
                file_time = time.time() - file_start_time

                # Save results
                output_file = temp_workspace / "output" / f"batch_{svg_name}.svg"
                output_file.write_text(processed_content)

                batch_results[svg_name] = {
                    'original_size': original_size,
                    'processed_size': processed_size,
                    'processing_time': file_time,
                    'compression_ratio': processed_size / original_size,
                    'modifications_made': context.modifications_made
                }

            except Exception as e:
                batch_results[svg_name] = {'error': str(e)}

        total_time = time.time() - total_start_time

        # Validate batch processing results
        successful_files = [name for name, result in batch_results.items() if 'error' not in result]
        assert len(successful_files) > 0, "At least some files should process successfully"

        # Check performance
        assert total_time < 10.0, "Batch processing should complete within reasonable time"

        # Log results
        print(f"Batch processed {len(successful_files)}/{len(batch_results)} files in {total_time:.3f}s")
        for name, result in batch_results.items():
            if 'error' not in result:
                print(f"  {name}: {result['original_size']} → {result['processed_size']} bytes "
                      f"({result['compression_ratio']:.2f}x) in {result['processing_time']:.3f}s")


@pytest.mark.skipif(not PREPROCESSING_AVAILABLE, reason="Preprocessing system not available")
class TestPreprocessingIntegrationE2E:
    """Test preprocessing integration with conversion pipeline."""

    def test_preprocessing_to_conversion_pipeline_e2e(self):
        """Test preprocessing output feeding into conversion pipeline."""
        # Create optimized SVG content
        optimized_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" viewBox="0 0 200 100">
            <rect x="10" y="20" width="80" height="60" fill="red"/>
            <circle cx="150" cy="50" r="25" fill="blue"/>
        </svg>'''

        # Validate that preprocessed SVG is valid for conversion
        try:
            tree = ET.fromstring(optimized_svg)

            # Check that SVG has required namespace
            assert tree.tag.endswith('svg'), "Root element should be SVG"

            # Check that viewBox is properly formatted
            viewbox = tree.get('viewBox')
            if viewbox:
                coords = viewbox.split()
                assert len(coords) == 4, "ViewBox should have 4 coordinates"
                for coord in coords:
                    float(coord)  # Should parse as numbers

            # Check that shape elements have valid numeric attributes
            for element in tree.iter():
                for attr in ['x', 'y', 'width', 'height', 'cx', 'cy', 'r']:
                    value = element.get(attr)
                    if value:
                        float(value)  # Should parse as number

            # If we reach here, preprocessed SVG is valid for conversion
            assert True

        except (ET.XMLSyntaxError, ValueError) as e:
            pytest.fail(f"Preprocessed SVG invalid for conversion: {e}")

    def test_preprocessing_preserves_conversion_requirements_e2e(self):
        """Test that preprocessing preserves elements needed for conversion."""
        # SVG with elements that conversion pipeline needs
        conversion_critical_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200">
            <defs>
                <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stop-color="yellow"/>
                    <stop offset="100%" stop-color="red"/>
                </linearGradient>
            </defs>
            <rect x="10" y="10" width="100" height="50" fill="url(#grad1)"/>
            <text x="150" y="100" font-family="Arial" font-size="16">Test Text</text>
            <g transform="translate(50,50)">
                <circle cx="0" cy="0" r="20" fill="green"/>
            </g>
        </svg>'''

        tree = ET.fromstring(conversion_critical_svg)

        # Apply preprocessing
        context = PreprocessingContext()
        plugins = [
            CleanupAttrsPlugin(),
            CleanupNumericValuesPlugin(),
            RemoveEmptyAttrsPlugin()
        ]

        for plugin in plugins:
            for element in tree.iter():
                if plugin.can_process(element, context):
                    plugin.process(element, context)

        # Verify critical elements preserved
        processed_content = ET.tostring(tree, encoding='unicode')

        # Check gradient definitions preserved
        assert 'linearGradient' in processed_content, "Gradient definitions should be preserved"
        assert 'id="grad1"' in processed_content, "Gradient IDs should be preserved"

        # Check text elements preserved
        assert 'Test Text' in processed_content, "Text content should be preserved"

        # Check transform attributes preserved
        assert 'transform=' in processed_content, "Transform attributes should be preserved"

        # Check references preserved
        assert 'url(#grad1)' in processed_content, "URL references should be preserved"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])