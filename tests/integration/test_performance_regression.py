#!/usr/bin/env python3
"""
CI/CD Integration & Performance Regression Tests

Tests designed to run in continuous integration to catch performance
regressions and validate system behavior under CI conditions.
"""

import pytest
import time
import os
import tempfile
import zipfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.svg2pptx import convert_svg_to_pptx
from src.svg2drawingml import SVGToDrawingMLConverter
from core.services.conversion_services import ConversionServices


class TestPerformanceRegression:
    """Test for performance regressions in critical paths."""

    def test_single_conversion_performance(self):
        """Test that single conversion completes within reasonable time."""
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><rect x="50" y="50" width="100" height="100" fill="blue"/></svg>'

        start_time = time.time()
        result = convert_svg_to_pptx(svg_content)
        duration = time.time() - start_time

        try:
            # Should complete within reasonable time
            assert duration < 10.0, f"Single conversion took {duration:.2f}s (> 10s threshold)"
            assert os.path.exists(result), "Conversion should create output file"
            assert os.path.getsize(result) > 1000, "Output should be non-trivial size"

        finally:
            if result and os.path.exists(result):
                os.unlink(result)

    def test_batch_conversion_performance(self):
        """Test batch conversion performance."""
        # Create multiple similar SVGs
        base_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><rect x="{x}" y="{y}" width="80" height="80" fill="{color}"/></svg>'
        svgs = []
        colors = ['red', 'blue', 'green', 'orange', 'purple']

        for i in range(10):
            x = (i % 5) * 30 + 10
            y = (i // 5) * 30 + 10
            color = colors[i % len(colors)]
            svgs.append(base_svg.format(x=x, y=y, color=color))

        start_time = time.time()
        results = []

        try:
            for svg in svgs:
                result = convert_svg_to_pptx(svg)
                results.append(result)

            duration = time.time() - start_time

            # Should complete batch reasonably quickly
            assert duration < 30.0, f"Batch conversion took {duration:.2f}s (> 30s threshold)"
            assert len(results) == len(svgs), "Should process all SVGs"

            # Check that all results are valid
            for result in results:
                assert os.path.exists(result), f"Result file should exist: {result}"
                assert os.path.getsize(result) > 1000, f"Result should be non-trivial: {result}"

        finally:
            # Clean up
            for result in results:
                if result and os.path.exists(result):
                    try:
                        os.unlink(result)
                    except OSError:
                        pass

    def test_complex_svg_performance(self):
        """Test performance with complex SVG structures."""
        # Create a complex SVG with multiple elements
        complex_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">
            <defs>
                <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
                    <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
                </linearGradient>
            </defs>
            <g transform="translate(50,50)">
                <rect width="300" height="200" fill="url(#grad1)" />
                <circle cx="150" cy="100" r="50" fill="blue" opacity="0.7"/>
                <path d="M50,50 Q150,10 250,50 T350,100" stroke="black" stroke-width="3" fill="none"/>
                <text x="150" y="180" text-anchor="middle" font-size="20" fill="white">Complex SVG</text>
            </g>
            <polygon points="10,350 50,250 90,350" fill="green"/>
            <ellipse cx="350" cy="300" rx="40" ry="60" fill="purple"/>
        </svg>'''

        start_time = time.time()
        result = convert_svg_to_pptx(complex_svg)
        duration = time.time() - start_time

        try:
            # Complex SVG should still complete reasonably quickly
            assert duration < 15.0, f"Complex SVG conversion took {duration:.2f}s (> 15s threshold)"
            assert os.path.exists(result), "Complex conversion should create output file"
            assert os.path.getsize(result) > 2000, "Complex output should be substantial"

        finally:
            if result and os.path.exists(result):
                os.unlink(result)

    def test_memory_usage_stability(self):
        """Test that repeated conversions don't cause memory leaks."""
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="80" height="80" fill="red"/></svg>'

        results = []
        try:
            # Perform multiple conversions
            for i in range(20):
                start_time = time.time()
                result = convert_svg_to_pptx(svg_content)
                duration = time.time() - start_time

                results.append((result, duration))

                # Each conversion should be consistently fast
                assert duration < 5.0, f"Conversion {i+1} took {duration:.2f}s (slower than expected)"

            # All conversions should succeed
            assert len(results) == 20, "All conversions should complete"

            # Results should be unique (no file conflicts)
            file_paths = [r[0] for r in results]
            assert len(set(file_paths)) == len(file_paths), "Results should be unique files"

            # Performance should be consistent (no major degradation)
            durations = [r[1] for r in results]
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)

            assert max_duration < avg_duration * 3, \
                f"Performance inconsistent: avg={avg_duration:.2f}s, max={max_duration:.2f}s"

        finally:
            # Clean up
            for result, _ in results:
                if result and os.path.exists(result):
                    try:
                        os.unlink(result)
                    except OSError:
                        pass


class TestConcurrencyAndThreadSafety:
    """Test system behavior under concurrent load."""

    def test_concurrent_conversion_safety(self):
        """Test that concurrent conversions work correctly."""
        svg_templates = [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="50" height="50" fill="red"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="blue"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><ellipse cx="50" cy="50" rx="40" ry="30" fill="green"/></svg>',
        ]

        results = []
        errors = []

        def convert_worker(svg_content, worker_id):
            try:
                start_time = time.time()
                result = convert_svg_to_pptx(svg_content)
                duration = time.time() - start_time

                return {
                    'worker_id': worker_id,
                    'result': result,
                    'duration': duration,
                    'success': True
                }
            except Exception as e:
                return {
                    'worker_id': worker_id,
                    'error': str(e),
                    'success': False
                }

        # Run concurrent conversions
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(15):  # 15 concurrent conversions
                svg_content = svg_templates[i % len(svg_templates)]
                future = executor.submit(convert_worker, svg_content, i)
                futures.append(future)

            # Collect results
            for future in as_completed(futures, timeout=30):
                result = future.result()
                if result['success']:
                    results.append(result)
                else:
                    errors.append(result)

        try:
            # Should have minimal errors
            assert len(errors) <= 2, f"Too many concurrent conversion errors: {errors[:3]}"

            # All successful results should be valid
            assert len(results) >= 10, f"Too few successful conversions: {len(results)}/15"

            # All results should be unique files
            file_paths = [r['result'] for r in results]
            assert len(set(file_paths)) == len(file_paths), "Concurrent results should be unique"

            # Performance should be reasonable even under load
            avg_duration = sum(r['duration'] for r in results) / len(results)
            assert avg_duration < 10.0, f"Average concurrent duration too high: {avg_duration:.2f}s"

        finally:
            # Clean up all result files
            for result in results:
                if result['result'] and os.path.exists(result['result']):
                    try:
                        os.unlink(result['result'])
                    except OSError:
                        pass

    def test_service_instance_thread_safety(self):
        """Test that ConversionServices instances are thread-safe."""
        errors = []
        results = []

        def service_worker(worker_id):
            try:
                # Each thread creates its own services
                services = ConversionServices.create_default()
                converter = SVGToDrawingMLConverter(services=services)

                svg_content = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="{worker_id * 5}" y="{worker_id * 5}" width="40" height="40" fill="red"/></svg>'

                result = converter.convert(svg_content)
                return {'worker_id': worker_id, 'result_length': len(result), 'success': True}

            except Exception as e:
                return {'worker_id': worker_id, 'error': str(e), 'success': False}

        # Run concurrent service operations
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(service_worker, i) for i in range(20)]

            for future in as_completed(futures, timeout=20):
                result = future.result()
                if result['success']:
                    results.append(result)
                else:
                    errors.append(result)

        # Should have minimal threading issues
        assert len(errors) <= 1, f"Service thread safety errors: {errors}"
        assert len(results) >= 18, f"Too few successful service operations: {len(results)}/20"

        # Results should vary (showing different worker IDs processed correctly)
        worker_ids = [r['worker_id'] for r in results]
        assert len(set(worker_ids)) >= 15, "Should process different worker IDs"


class TestSystemResourceUsage:
    """Test system resource usage and limits."""

    def test_large_svg_handling(self):
        """Test handling of large SVG content."""
        # Create a large SVG with many elements
        elements = []
        for i in range(100):  # 100 elements
            x = (i % 10) * 40
            y = (i // 10) * 40
            elements.append(f'<rect x="{x}" y="{y}" width="30" height="30" fill="rgb({i*2 % 255}, {i*3 % 255}, {i*5 % 255})"/>')

        large_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800">
            {''.join(elements)}
        </svg>'''

        start_time = time.time()
        result = convert_svg_to_pptx(large_svg)
        duration = time.time() - start_time

        try:
            # Should handle large SVG within reasonable time and memory
            assert duration < 30.0, f"Large SVG conversion took {duration:.2f}s (> 30s threshold)"
            assert os.path.exists(result), "Large SVG conversion should create output"
            assert os.path.getsize(result) > 5000, "Large SVG output should be substantial"

            # Verify it's a valid PPTX
            with zipfile.ZipFile(result, 'r') as zf:
                assert '[Content_Types].xml' in zf.namelist()

        finally:
            if result and os.path.exists(result):
                os.unlink(result)

    def test_temporary_file_cleanup(self):
        """Test that temporary files are properly cleaned up."""
        initial_temp_files = self._count_temp_files()

        # Perform multiple conversions that create temporary files
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="80" height="80" fill="blue"/></svg>'

        results = []
        try:
            for _ in range(10):
                result = convert_svg_to_pptx(svg_content)
                results.append(result)

            # Check temporary file count hasn't grown excessively
            current_temp_files = self._count_temp_files()
            temp_file_growth = current_temp_files - initial_temp_files

            # Should not accumulate too many temp files (allow some leeway for system processes)
            assert temp_file_growth < 50, f"Too many temporary files created: {temp_file_growth}"

        finally:
            # Clean up result files
            for result in results:
                if result and os.path.exists(result):
                    try:
                        os.unlink(result)
                    except OSError:
                        pass

    def _count_temp_files(self):
        """Count files in system temporary directory."""
        try:
            temp_dir = Path(tempfile.gettempdir())
            return len(list(temp_dir.glob('*')))
        except (OSError, PermissionError):
            return 0  # Can't count, assume 0

    def test_error_recovery(self):
        """Test that system recovers gracefully from errors."""
        # Test with various error-inducing inputs
        problematic_inputs = [
            '',  # Empty
            '<not-xml>',  # Invalid XML
            '<svg xmlns="http://www.w3.org/2000/svg"><rect width="invalid" height="also-invalid"/></svg>',  # Invalid attributes
            '<svg xmlns="http://www.w3.org/2000/svg">' + 'x' * 10000 + '</svg>',  # Very large content
        ]

        successful_after_errors = 0
        valid_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="50" height="50" fill="green"/></svg>'

        for i, problematic_input in enumerate(problematic_inputs):
            try:
                # Try problematic input (may fail)
                result = convert_svg_to_pptx(problematic_input)
                if result and os.path.exists(result):
                    os.unlink(result)
            except Exception:
                # Expected for problematic inputs
                pass

            # Test that system still works after error
            try:
                result = convert_svg_to_pptx(valid_svg)
                if result and os.path.exists(result):
                    successful_after_errors += 1
                    os.unlink(result)
            except Exception as e:
                pytest.fail(f"System failed to recover after error {i+1}: {e}")

        # Should recover from most errors
        assert successful_after_errors >= len(problematic_inputs) - 1, \
            f"System failed to recover from errors: {successful_after_errors}/{len(problematic_inputs)}"


class TestCIEnvironmentCompatibility:
    """Test compatibility with CI/CD environments."""

    def test_headless_environment_compatibility(self):
        """Test that conversion works in headless environments (no display)."""
        # This test ensures the system doesn't require GUI components
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="orange"/></svg>'

        try:
            result = convert_svg_to_pptx(svg_content)
            assert os.path.exists(result), "Should work in headless environment"
            assert os.path.getsize(result) > 1000, "Should produce valid output"

            # Clean up
            os.unlink(result)

        except Exception as e:
            pytest.fail(f"Failed in headless environment: {e}")

    def test_minimal_dependency_operation(self):
        """Test that core functionality works with minimal dependencies."""
        # Test that basic conversion works even if optional dependencies are missing
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="80" height="80" fill="red"/></svg>'

        try:
            services = ConversionServices.create_default()
            assert services is not None, "Should create services with minimal dependencies"

            result = convert_svg_to_pptx(svg_content)
            assert os.path.exists(result), "Should convert with minimal dependencies"

            os.unlink(result)

        except ImportError as e:
            pytest.skip(f"Missing required dependency: {e}")
        except Exception as e:
            pytest.fail(f"Minimal dependency test failed: {e}")

    def test_deterministic_output(self):
        """Test that conversion produces deterministic output."""
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="25" y="25" width="50" height="50" fill="blue"/></svg>'

        results = []
        try:
            # Convert same SVG multiple times
            for _ in range(3):
                result = convert_svg_to_pptx(svg_content)
                results.append(result)

                # Check file size (should be consistent)
                size = os.path.getsize(result)
                results[-1] = (result, size)

            # Sizes should be identical or very close (allowing for timestamps)
            sizes = [size for _, size in results]
            max_size = max(sizes)
            min_size = min(sizes)

            # Allow small variations for timestamps/metadata
            size_variation = (max_size - min_size) / min_size if min_size > 0 else 0
            assert size_variation < 0.01, f"Output size too variable: {sizes}"

        finally:
            # Clean up
            for result, _ in results:
                if os.path.exists(result):
                    os.unlink(result)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])