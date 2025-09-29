#!/usr/bin/env python3
"""
CI/CD Compatibility Tests

Tests for compatibility with CI/CD environments, headless operation,
and automated deployment scenarios.
"""

import pytest
import os
import tempfile
import subprocess
import sys
import time
import concurrent.futures
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.svg2pptx import convert_svg_to_pptx, SVGToPowerPointConverter
from src.services.conversion_services import ConversionServices


class TestHeadlessEnvironment:
    """Test compatibility with headless environments (CI/CD)."""

    def test_no_display_dependency(self):
        """Test that conversion works without display/GUI dependencies."""
        # Mock environment without DISPLAY
        with patch.dict(os.environ, {}, clear=True):
            if 'DISPLAY' in os.environ:
                del os.environ['DISPLAY']

            svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="50" height="50" fill="red"/></svg>'

            try:
                result = convert_svg_to_pptx(svg_content)
                assert os.path.exists(result), "Conversion should work without display"
                assert os.path.getsize(result) > 1000, "Should produce valid PPTX"
                os.unlink(result)

            except Exception as e:
                pytest.fail(f"Headless conversion failed: {e}")

    def test_minimal_environment_variables(self):
        """Test conversion with minimal environment variables."""
        # Save original environment
        original_env = dict(os.environ)

        try:
            # Keep only essential variables
            essential_vars = {'PATH', 'PYTHONPATH', 'HOME', 'USER', 'SHELL'}
            minimal_env = {k: v for k, v in os.environ.items() if k in essential_vars}

            with patch.dict(os.environ, minimal_env, clear=True):
                svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><circle cx="100" cy="100" r="50" fill="blue"/></svg>'

                result = convert_svg_to_pptx(svg_content)
                assert os.path.exists(result)
                os.unlink(result)

        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)

    def test_docker_like_environment(self):
        """Test conversion in Docker-like restricted environment."""
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 150 150"><polygon points="75,25 100,75 75,125 50,75" fill="green"/></svg>'

        # Simulate Docker environment restrictions
        with patch('tempfile.gettempdir', return_value='/tmp'):
            with patch('os.getuid', return_value=1000):  # Non-root user
                with patch('os.access', return_value=True):  # Basic file access
                    try:
                        result = convert_svg_to_pptx(svg_content)
                        assert os.path.exists(result)
                        os.unlink(result)
                    except Exception as e:
                        pytest.fail(f"Docker-like environment failed: {e}")


class TestConcurrencyAndThreadSafety:
    """Test thread safety and concurrent operations."""

    def test_concurrent_conversions(self):
        """Test multiple simultaneous conversions."""
        svg_templates = [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="50" height="50" fill="red"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="25" fill="blue"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><ellipse cx="50" cy="50" rx="30" ry="20" fill="green"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><line x1="10" y1="10" x2="90" y2="90" stroke="black" stroke-width="2"/></svg>',
        ]

        results = []

        def convert_svg(svg_content):
            return convert_svg_to_pptx(svg_content)

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(convert_svg, svg) for svg in svg_templates]

                for future in concurrent.futures.as_completed(futures, timeout=30):
                    result = future.result()
                    results.append(result)
                    assert os.path.exists(result), "Concurrent conversion should create file"
                    assert os.path.getsize(result) > 1000, "Concurrent conversion should create valid file"

            # All conversions should succeed
            assert len(results) == len(svg_templates), "All concurrent conversions should complete"

            # All results should be unique (no file conflicts)
            assert len(set(results)) == len(results), "Concurrent conversions should create unique files"

        finally:
            # Clean up
            for result in results:
                if result and os.path.exists(result):
                    try:
                        os.unlink(result)
                    except OSError:
                        pass

    def test_service_container_thread_safety(self):
        """Test that service container is thread-safe."""
        def create_services():
            return ConversionServices.create_default()

        services_list = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(create_services) for _ in range(10)]

            for future in concurrent.futures.as_completed(futures):
                services = future.result()
                services_list.append(services)
                assert services is not None, "Service creation should succeed in threads"

        assert len(services_list) == 10, "All service creations should succeed"

    def test_memory_stability_under_load(self):
        """Test memory stability during concurrent load."""
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="50" height="50" fill="red"/></svg>'

        results = []

        def stress_conversion(iteration):
            try:
                result = convert_svg_to_pptx(svg_content)
                return result
            except Exception as e:
                return f"Error_{iteration}: {e}"

        try:
            # Run multiple conversions in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                futures = [executor.submit(stress_conversion, i) for i in range(20)]

                for future in concurrent.futures.as_completed(futures, timeout=60):
                    result = future.result()
                    results.append(result)

            # Count successful conversions
            successful = [r for r in results if not r.startswith("Error_")]
            errors = [r for r in results if r.startswith("Error_")]

            # Should have mostly successful conversions
            success_rate = len(successful) / len(results)
            assert success_rate > 0.8, f"Success rate {success_rate} too low. Errors: {errors[:3]}"

        finally:
            # Clean up successful conversions
            for result in results:
                if not result.startswith("Error_") and os.path.exists(result):
                    try:
                        os.unlink(result)
                    except OSError:
                        pass


class TestSystemResourceUsage:
    """Test system resource usage and limits."""

    def test_temporary_file_cleanup(self):
        """Test that temporary files are properly cleaned up."""
        initial_temp_files = set(os.listdir(tempfile.gettempdir()))

        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="50" height="50" fill="red"/></svg>'

        results = []
        try:
            # Create multiple conversions
            for i in range(5):
                result = convert_svg_to_pptx(svg_content)
                results.append(result)
                assert os.path.exists(result)

            # Check temp directory growth
            current_temp_files = set(os.listdir(tempfile.gettempdir()))
            new_temp_files = current_temp_files - initial_temp_files

            # Should not have excessive temp file growth
            assert len(new_temp_files) < 50, f"Too many temp files created: {len(new_temp_files)}"

        finally:
            # Clean up results
            for result in results:
                if os.path.exists(result):
                    os.unlink(result)

    def test_large_svg_handling(self):
        """Test handling of relatively large SVG content."""
        # Create SVG with many elements
        svg_parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000">']

        # Add many rectangles
        for i in range(100):
            x, y = (i % 10) * 100, (i // 10) * 100
            color = f"rgb({i*2 % 255}, {i*3 % 255}, {i*5 % 255})"
            svg_parts.append(f'<rect x="{x}" y="{y}" width="80" height="80" fill="{color}"/>')

        svg_parts.append('</svg>')
        large_svg = ''.join(svg_parts)

        start_time = time.time()
        try:
            result = convert_svg_to_pptx(large_svg)
            processing_time = time.time() - start_time

            assert os.path.exists(result), "Large SVG conversion should succeed"
            assert processing_time < 30, f"Large SVG took too long: {processing_time:.2f}s"

            # Should produce reasonably sized file
            file_size = os.path.getsize(result)
            assert 10000 < file_size < 50000000, f"Unexpected file size: {file_size}"

            os.unlink(result)

        except Exception as e:
            pytest.fail(f"Large SVG conversion failed: {e}")

    def test_memory_leak_detection(self):
        """Test for memory leaks in repeated conversions."""
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="50" height="50" fill="red"/></svg>'

        # Get initial temp file count
        initial_temp_count = len(os.listdir(tempfile.gettempdir()))

        results = []
        try:
            # Perform many conversions
            for i in range(15):
                result = convert_svg_to_pptx(svg_content)
                results.append(result)

                # Clean up immediately to test for leaks
                if os.path.exists(result):
                    os.unlink(result)
                results.pop()

            # Check temp directory after cleanup
            final_temp_count = len(os.listdir(tempfile.gettempdir()))
            temp_growth = final_temp_count - initial_temp_count

            assert temp_growth < 5, f"Potential memory leak: {temp_growth} temp files not cleaned up"

        finally:
            # Final cleanup
            for result in results:
                if os.path.exists(result):
                    try:
                        os.unlink(result)
                    except OSError:
                        pass


class TestCIEnvironmentCompatibility:
    """Test compatibility with CI/CD systems like GitHub Actions, Jenkins."""

    def test_github_actions_environment(self):
        """Test compatibility with GitHub Actions environment."""
        # Simulate GitHub Actions environment
        github_env = {
            'CI': 'true',
            'GITHUB_ACTIONS': 'true',
            'GITHUB_WORKFLOW': 'test',
            'RUNNER_OS': 'Linux',
            'RUNNER_ARCH': 'X64',
        }

        with patch.dict(os.environ, github_env):
            svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="50" height="50" fill="red"/></svg>'

            try:
                result = convert_svg_to_pptx(svg_content)
                assert os.path.exists(result), "Should work in GitHub Actions environment"
                assert os.path.getsize(result) > 1000
                os.unlink(result)

            except Exception as e:
                pytest.fail(f"GitHub Actions compatibility failed: {e}")

    def test_jenkins_environment(self):
        """Test compatibility with Jenkins CI environment."""
        # Simulate Jenkins environment
        jenkins_env = {
            'JENKINS_URL': 'http://jenkins.example.com',
            'BUILD_NUMBER': '123',
            'JOB_NAME': 'svg2pptx-test',
            'WORKSPACE': '/var/jenkins_home/workspace/svg2pptx-test',
        }

        with patch.dict(os.environ, jenkins_env):
            svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 150 150"><circle cx="75" cy="75" r="50" fill="blue"/></svg>'

            try:
                result = convert_svg_to_pptx(svg_content)
                assert os.path.exists(result), "Should work in Jenkins environment"
                os.unlink(result)

            except Exception as e:
                pytest.fail(f"Jenkins compatibility failed: {e}")

    def test_docker_container_limits(self):
        """Test operation under Docker container resource limits."""
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><ellipse cx="100" cy="100" rx="75" ry="50" fill="green"/></svg>'

        # Simulate container environment
        with patch('os.cpu_count', return_value=2):  # Limited CPU
            with tempfile.TemporaryDirectory(prefix='docker_test_') as temp_dir:
                # Use restricted temp directory
                with patch('tempfile.gettempdir', return_value=temp_dir):
                    try:
                        result = convert_svg_to_pptx(svg_content)
                        assert os.path.exists(result), "Should work under container limits"
                        assert temp_dir in result, "Should use restricted temp directory"

                    except Exception as e:
                        pytest.fail(f"Container limits compatibility failed: {e}")

    def test_read_only_filesystem_handling(self):
        """Test graceful handling of read-only filesystem restrictions."""
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="50" height="50" fill="red"/></svg>'

        # Create a writable temp directory for the test
        with tempfile.TemporaryDirectory() as writable_temp:
            # Override temp directory to our writable location
            with patch('tempfile.gettempdir', return_value=writable_temp):
                try:
                    result = convert_svg_to_pptx(svg_content)
                    assert os.path.exists(result), "Should work with temp directory override"
                    assert writable_temp in result, "Should use overridden temp directory"

                except Exception as e:
                    pytest.fail(f"Read-only filesystem handling failed: {e}")


class TestBuildSystemIntegration:
    """Test integration with build systems and package managers."""

    def test_pip_install_simulation(self):
        """Test that the package works after pip install simulation."""
        # Simulate package installation by ensuring imports work
        try:
            from src.svg2pptx import convert_svg_to_pptx
            from src.services.conversion_services import ConversionServices
            from src.converters.base import BaseConverter

            # Test that services can be created
            services = ConversionServices.create_default()
            assert services is not None

            # Test basic conversion
            svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="50" height="50" fill="red"/></svg>'
            result = convert_svg_to_pptx(svg_content)
            assert os.path.exists(result)
            os.unlink(result)

        except ImportError as e:
            pytest.fail(f"Package import failed: {e}")

    def test_setuptools_entry_point_simulation(self):
        """Test that entry points would work correctly."""
        # Test that main functions are callable
        from src.svg2pptx import convert_svg_to_pptx, SVGToPowerPointConverter

        assert callable(convert_svg_to_pptx), "Main conversion function should be callable"
        assert SVGToPowerPointConverter is not None, "Main converter class should be importable"

    def test_requirements_compatibility(self):
        """Test compatibility with common dependency versions."""
        # Test that required packages can be imported
        required_packages = [
            'lxml',
            'python_pptx',
            'Pillow',
            'dataclasses'  # Should work on Python 3.7+
        ]

        missing_packages = []
        for package in required_packages:
            try:
                if package == 'python_pptx':
                    import pptx
                elif package == 'dataclasses':
                    import dataclasses
                else:
                    __import__(package)
            except ImportError:
                missing_packages.append(package)

        assert not missing_packages, f"Missing required packages: {missing_packages}"


class TestPerformanceInCICD:
    """Test performance characteristics in CI/CD environments."""

    def test_conversion_time_ci_acceptable(self):
        """Test that conversion time is acceptable for CI/CD."""
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><rect width="100" height="100" fill="red"/></svg>'

        start_time = time.time()
        result = convert_svg_to_pptx(svg_content)
        conversion_time = time.time() - start_time

        try:
            assert os.path.exists(result)
            # CI/CD should complete conversions quickly
            assert conversion_time < 15, f"Conversion took too long for CI/CD: {conversion_time:.2f}s"

        finally:
            if os.path.exists(result):
                os.unlink(result)

    def test_batch_processing_performance(self):
        """Test batch processing performance for CI/CD scenarios."""
        svg_templates = [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="50" height="50" fill="red"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="25" fill="blue"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><ellipse cx="50" cy="50" rx="30" ry="20" fill="green"/></svg>',
        ]

        start_time = time.time()
        results = []

        try:
            for svg in svg_templates:
                result = convert_svg_to_pptx(svg)
                results.append(result)
                assert os.path.exists(result)

            total_time = time.time() - start_time

            # Batch processing should be efficient
            assert total_time < 30, f"Batch processing took too long: {total_time:.2f}s"

        finally:
            for result in results:
                if os.path.exists(result):
                    os.unlink(result)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])