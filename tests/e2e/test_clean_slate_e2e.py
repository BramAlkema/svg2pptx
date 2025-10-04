#!/usr/bin/env python3
"""
Clean Slate E2E Integration Tests

Tests the complete Clean Slate architecture pipeline:
SVG → Preprocess → Parse → Analyze → Map → Embed → Package → PPTX

This validates the full integration of all Clean Slate components.
"""

import pytest
import tempfile
import time
import psutil
from pathlib import Path
from typing import Dict, Any
from zipfile import ZipFile
from lxml import etree as ET

# Clean Slate imports
from core.pipeline.converter import CleanSlateConverter, ConversionResult, ConversionError
from core.pipeline.config import PipelineConfig, OutputFormat, QualityLevel

# Legacy validation imports
from pptx import Presentation


class PerformanceMonitor:
    """Monitor performance metrics during conversion."""

    def __init__(self):
        self.process = psutil.Process()
        self.start_memory = None
        self.peak_memory = None
        self.start_time = None

    def start(self):
        """Start monitoring."""
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.start_memory
        self.start_time = time.perf_counter()

    def update(self):
        """Update peak memory usage."""
        current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = max(self.peak_memory, current_memory)

    def stop(self):
        """Stop monitoring and return metrics."""
        end_time = time.perf_counter()
        end_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        return {
            'duration_ms': (end_time - self.start_time) * 1000,
            'memory_start_mb': self.start_memory,
            'memory_end_mb': end_memory,
            'memory_peak_mb': self.peak_memory,
            'memory_delta_mb': end_memory - self.start_memory
        }


class PPTXValidator:
    """Validate generated PPTX files."""

    def validate_structure(self, pptx_path: Path) -> Dict[str, Any]:
        """Validate PPTX file structure."""
        validation = {
            'is_valid_zip': False,
            'has_required_files': False,
            'xml_well_formed': False,
            'openable_by_pptx': False,
            'slide_count': 0,
            'file_size_bytes': 0,
            'errors': []
        }

        try:
            # Check file exists and has content
            if not pptx_path.exists():
                validation['errors'].append("File does not exist")
                return validation

            validation['file_size_bytes'] = pptx_path.stat().st_size
            if validation['file_size_bytes'] == 0:
                validation['errors'].append("File is empty")
                return validation

            # Validate ZIP structure
            try:
                with ZipFile(pptx_path, 'r') as zip_file:
                    files = zip_file.namelist()
                    validation['is_valid_zip'] = True

                    # Check required OOXML files
                    required_files = [
                        '[Content_Types].xml',
                        '_rels/.rels',
                        'ppt/presentation.xml'
                    ]

                    missing_files = [f for f in required_files if f not in files]
                    if missing_files:
                        validation['errors'].append(f"Missing files: {missing_files}")
                    else:
                        validation['has_required_files'] = True

                    # Validate XML files are well-formed
                    xml_files = [f for f in files if f.endswith('.xml')]
                    xml_errors = []

                    for xml_file in xml_files:
                        try:
                            xml_content = zip_file.read(xml_file)
                            ET.fromstring(xml_content)
                        except ET.XMLSyntaxError as e:
                            xml_errors.append(f"{xml_file}: {e}")

                    if xml_errors:
                        validation['errors'].extend(xml_errors)
                    else:
                        validation['xml_well_formed'] = True

            except Exception as e:
                validation['errors'].append(f"ZIP validation failed: {e}")
                return validation

            # Try to open with python-pptx
            try:
                prs = Presentation(str(pptx_path))
                validation['openable_by_pptx'] = True
                validation['slide_count'] = len(prs.slides)
            except Exception as e:
                validation['errors'].append(f"python-pptx failed to open: {e}")

        except Exception as e:
            validation['errors'].append(f"Validation error: {e}")

        return validation


class E2ETestResults:
    """Collect and analyze E2E test results."""

    def __init__(self):
        self.results = []
        self.performance_stats = []

    def add_result(self, svg_file: str, success: bool, conversion_result: ConversionResult = None,
                   validation: Dict[str, Any] = None, performance: Dict[str, Any] = None,
                   error: str = None):
        """Add test result."""
        result = {
            'svg_file': svg_file,
            'success': success,
            'error': error,
            'conversion_result': conversion_result,
            'validation': validation,
            'performance': performance,
            'timestamp': time.time()
        }
        self.results.append(result)

        if performance:
            self.performance_stats.append(performance)

    def get_summary(self) -> Dict[str, Any]:
        """Get test summary statistics."""
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r['success'])

        # Performance statistics
        if self.performance_stats:
            durations = [p['duration_ms'] for p in self.performance_stats]
            memory_peaks = [p['memory_peak_mb'] for p in self.performance_stats]

            perf_stats = {
                'avg_duration_ms': sum(durations) / len(durations),
                'max_duration_ms': max(durations),
                'min_duration_ms': min(durations),
                'avg_memory_peak_mb': sum(memory_peaks) / len(memory_peaks),
                'max_memory_peak_mb': max(memory_peaks),
                'total_conversions_under_1s': sum(1 for d in durations if d < 1000)
            }
        else:
            perf_stats = {}

        return {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'failed_tests': total_tests - successful_tests,
            'success_rate': successful_tests / total_tests if total_tests > 0 else 0,
            'performance': perf_stats,
            'failed_files': [r['svg_file'] for r in self.results if not r['success']]
        }


@pytest.fixture
def svg_test_files():
    """Get list of SVG test files."""
    test_data_dir = Path(__file__).parent.parent / "data" / "real_world_svgs"
    visual_test_dir = Path(__file__).parent.parent / "visual" / "results" / "svgs"

    svg_files = []

    # Add real world SVGs
    if test_data_dir.exists():
        svg_files.extend(list(test_data_dir.glob("*.svg")))

    # Add visual test SVGs
    if visual_test_dir.exists():
        svg_files.extend(list(visual_test_dir.glob("*.svg")))

    # Ensure we have at least 20 diverse samples as specified
    return svg_files[:25]  # Take 25 to exceed the requirement


@pytest.fixture
def clean_slate_converter():
    """Create Clean Slate converter for testing."""
    config = PipelineConfig(
        output_format=OutputFormat.PPTX,
        quality_level=QualityLevel.BALANCED,
        verbose_logging=True,
        enable_debug=True
    )
    return CleanSlateConverter(config)


@pytest.fixture
def pptx_validator():
    """Create PPTX validator."""
    return PPTXValidator()


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory."""
    with tempfile.TemporaryDirectory(prefix="clean_slate_e2e_") as temp_dir:
        yield Path(temp_dir)


class TestCleanSlateE2E:
    """End-to-end tests for Clean Slate architecture."""

    def test_single_svg_conversion(self, clean_slate_converter, pptx_validator, temp_output_dir):
        """Test conversion of a single SVG file."""
        # Create a simple test SVG
        test_svg = temp_output_dir / "test.svg"
        test_svg.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100" width="200" height="100">
    <rect x="10" y="10" width="80" height="40" fill="blue"/>
    <circle cx="150" cy="50" r="30" fill="red"/>
    <text x="100" y="80" font-size="14" fill="black">Clean Slate Test</text>
</svg>''')

        # Convert using Clean Slate pipeline
        output_path = temp_output_dir / "test.pptx"

        monitor = PerformanceMonitor()
        monitor.start()

        try:
            result = clean_slate_converter.convert_file(str(test_svg), str(output_path))

            monitor.update()
            performance = monitor.stop()

            # Validate conversion result
            assert result is not None
            assert result.output_format == OutputFormat.PPTX
            assert result.total_time_ms > 0
            assert result.elements_processed > 0
            assert output_path.exists()

            # Validate PPTX structure
            validation = pptx_validator.validate_structure(output_path)
            assert validation['is_valid_zip'], f"Invalid ZIP: {validation['errors']}"
            assert validation['has_required_files'], f"Missing files: {validation['errors']}"
            assert validation['xml_well_formed'], f"Invalid XML: {validation['errors']}"
            assert validation['openable_by_pptx'], f"Not openable: {validation['errors']}"

            # Performance assertions
            assert performance['duration_ms'] < 5000, f"Conversion too slow: {performance['duration_ms']}ms"
            assert performance['memory_peak_mb'] < 500, f"Memory usage too high: {performance['memory_peak_mb']}MB"

            print(f"✅ Single SVG test passed:")
            print(f"   Duration: {performance['duration_ms']:.2f}ms")
            print(f"   Memory peak: {performance['memory_peak_mb']:.2f}MB")
            print(f"   Elements processed: {result.elements_processed}")
            print(f"   Output size: {validation['file_size_bytes']} bytes")

        except ConversionError as e:
            pytest.fail(f"Conversion failed: {e} (stage: {e.stage})")

    def test_diverse_svg_samples(self, svg_test_files, clean_slate_converter, pptx_validator, temp_output_dir):
        """Test conversion of diverse SVG samples."""
        if len(svg_test_files) < 10:
            pytest.skip("Not enough SVG test files available for comprehensive testing")

        results = E2ETestResults()

        for i, svg_file in enumerate(svg_test_files[:20]):  # Test 20 diverse samples
            print(f"\n🧪 Testing {i+1}/20: {svg_file.name}")

            output_path = temp_output_dir / f"{svg_file.stem}.pptx"

            monitor = PerformanceMonitor()
            monitor.start()

            try:
                # Convert with Clean Slate
                conversion_result = clean_slate_converter.convert_file(str(svg_file), str(output_path))

                monitor.update()
                performance = monitor.stop()

                # Validate output
                validation = pptx_validator.validate_structure(output_path)

                success = (validation['is_valid_zip'] and
                          validation['has_required_files'] and
                          validation['xml_well_formed'])

                results.add_result(
                    svg_file=svg_file.name,
                    success=success,
                    conversion_result=conversion_result,
                    validation=validation,
                    performance=performance
                )

                if success:
                    print(f"   ✅ Success: {performance['duration_ms']:.2f}ms, {validation['file_size_bytes']} bytes")
                else:
                    print(f"   ❌ Failed: {validation['errors']}")

            except Exception as e:
                performance = monitor.stop()
                results.add_result(
                    svg_file=svg_file.name,
                    success=False,
                    performance=performance,
                    error=str(e)
                )
                print(f"   ❌ Exception: {e}")

        # Analyze results
        summary = results.get_summary()

        print(f"\n📊 E2E Test Summary:")
        print(f"   Total tests: {summary['total_tests']}")
        print(f"   Successful: {summary['successful_tests']}")
        print(f"   Failed: {summary['failed_tests']}")
        print(f"   Success rate: {summary['success_rate']:.2%}")

        if summary['performance']:
            perf = summary['performance']
            print(f"   Avg duration: {perf['avg_duration_ms']:.2f}ms")
            print(f"   Max duration: {perf['max_duration_ms']:.2f}ms")
            print(f"   Conversions under 1s: {perf['total_conversions_under_1s']}/{summary['total_tests']}")
            print(f"   Avg memory peak: {perf['avg_memory_peak_mb']:.2f}MB")

        if summary['failed_files']:
            print(f"   Failed files: {summary['failed_files']}")

        # Assert success criteria
        assert summary['success_rate'] >= 0.8, f"Success rate too low: {summary['success_rate']:.2%}"
        assert summary['successful_tests'] >= 15, f"Not enough successful conversions: {summary['successful_tests']}"

        if summary['performance']:
            assert perf['avg_duration_ms'] < 2000, f"Average duration too slow: {perf['avg_duration_ms']:.2f}ms"
            assert perf['total_conversions_under_1s'] >= 10, f"Too few fast conversions: {perf['total_conversions_under_1s']}"

    def test_complex_svg_features(self, clean_slate_converter, pptx_validator, temp_output_dir):
        """Test complex SVG features through the pipeline."""
        # Create complex test SVG with various features
        complex_svg = temp_output_dir / "complex.svg"
        complex_svg.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     viewBox="0 0 400 300" width="400" height="300">
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
            <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
        </linearGradient>
        <pattern id="pattern1" patternUnits="userSpaceOnUse" width="20" height="20">
            <rect width="10" height="10" fill="blue"/>
            <rect x="10" y="10" width="10" height="10" fill="blue"/>
        </pattern>
    </defs>

    <!-- Basic shapes -->
    <rect x="10" y="10" width="100" height="60" fill="url(#grad1)" stroke="black" stroke-width="2"/>
    <circle cx="200" cy="50" r="40" fill="url(#pattern1)"/>
    <ellipse cx="320" cy="50" rx="60" ry="30" fill="green" opacity="0.7"/>

    <!-- Paths -->
    <path d="M 50 150 Q 100 100 150 150 T 250 150" stroke="purple" stroke-width="3" fill="none"/>
    <path d="M 20 200 L 50 180 L 80 200 Z" fill="orange"/>

    <!-- Text with transformations -->
    <g transform="translate(50, 250) rotate(15)">
        <text font-size="16" fill="darkblue">Transformed Text</text>
    </g>

    <!-- Groups and nested transforms -->
    <g transform="scale(0.8) translate(200, 180)">
        <g transform="rotate(30)">
            <rect width="60" height="40" fill="pink" stroke="navy"/>
            <text x="30" y="25" text-anchor="middle" font-size="12">Nested</text>
        </g>
    </g>
</svg>''')

        output_path = temp_output_dir / "complex.pptx"

        # Convert and validate
        result = clean_slate_converter.convert_file(str(complex_svg), str(output_path))
        validation = pptx_validator.validate_structure(output_path)

        # Assertions for complex features
        assert result.elements_processed >= 8, f"Not enough elements processed: {result.elements_processed}"
        assert validation['is_valid_zip'], f"Complex SVG produced invalid ZIP: {validation['errors']}"
        assert validation['openable_by_pptx'], f"Complex SVG not openable: {validation['errors']}"
        assert validation['file_size_bytes'] > 3000, "Complex SVG output too small"

        print(f"✅ Complex SVG test passed:")
        print(f"   Elements processed: {result.elements_processed}")
        print(f"   Total time: {result.total_time_ms:.2f}ms")
        print(f"   Output size: {validation['file_size_bytes']} bytes")

    def test_performance_benchmarks(self, clean_slate_converter, temp_output_dir):
        """Test performance benchmarks for simple SVGs."""
        # Create simple test SVG for performance testing
        simple_svg = temp_output_dir / "simple_perf.svg"
        simple_svg.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
    <rect x="10" y="10" width="80" height="80" fill="blue"/>
</svg>''')

        # Run multiple conversions to test performance consistency
        durations = []
        for i in range(5):
            output_path = temp_output_dir / f"perf_test_{i}.pptx"

            start_time = time.perf_counter()
            result = clean_slate_converter.convert_file(str(simple_svg), str(output_path))
            end_time = time.perf_counter()

            duration_ms = (end_time - start_time) * 1000
            durations.append(duration_ms)

        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)

        # Performance assertions
        assert avg_duration < 1000, f"Average duration too slow: {avg_duration:.2f}ms (target: <1000ms)"
        assert max_duration < 2000, f"Max duration too slow: {max_duration:.2f}ms (target: <2000ms)"
        assert all(d < 1500 for d in durations), f"Some conversions too slow: {durations}"

        print(f"✅ Performance benchmark passed:")
        print(f"   Average duration: {avg_duration:.2f}ms")
        print(f"   Max duration: {max_duration:.2f}ms")
        print(f"   All conversions: {[f'{d:.2f}ms' for d in durations]}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])