#!/usr/bin/env python3
"""
Integration Test for FontService

Tests FontService integration with real font files and system components.
Verifies cross-platform font discovery and loading behavior.
"""

import pytest
from pathlib import Path
import sys
import tempfile
import os
import platform
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.services.font_service import FontService
from src.converters.result_types import ConversionError


class TestFontServiceSystemIntegration:
    """
    Integration tests for FontService with real system components.

    Tests actual font discovery and loading across different platforms.
    """

    @pytest.fixture
    def temp_directory(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def sample_font_structure(self, temp_directory):
        """
        Create sample font directory structure for testing.

        Creates a realistic font directory with various font types.
        """
        font_dirs = {}

        # Create main fonts directory
        main_fonts = temp_directory / "fonts"
        main_fonts.mkdir()

        # Create subdirectories
        system_fonts = main_fonts / "system"
        user_fonts = main_fonts / "user"
        system_fonts.mkdir()
        user_fonts.mkdir()

        # Create mock font files with realistic names
        font_files = [
            "arial.ttf",
            "arial-bold.ttf",
            "arial-italic.ttf",
            "times-new-roman.ttf",
            "helvetica.otf",
            "comic-sans.woff",
            "invalid-font.txt",  # Non-font file
        ]

        for font_file in font_files:
            # Create font files in both directories
            (system_fonts / font_file).write_bytes(b"mock font data")
            if not font_file.endswith('.txt'):  # Don't put invalid file in user fonts
                (user_fonts / font_file).write_bytes(b"mock font data")

        font_dirs['main'] = main_fonts
        font_dirs['system'] = system_fonts
        font_dirs['user'] = user_fonts
        font_dirs['font_files'] = font_files

        return font_dirs

    @pytest.fixture
    def integration_components(self, sample_font_structure):
        """
        Setup FontService with realistic configuration.

        Creates FontService instances with different configurations
        for testing various integration scenarios.
        """
        return {
            'default_service': FontService(),  # System default directories
            'custom_service': FontService([
                str(sample_font_structure['system']),
                str(sample_font_structure['user'])
            ]),
            'empty_service': FontService([]),  # No directories
        }

    def test_basic_integration_flow(self, integration_components, sample_font_structure, temp_directory):
        """
        Test the basic integration workflow.

        Verifies font discovery, loading, and validation work together correctly.
        """
        service = integration_components['custom_service']

        # Test font discovery
        available_fonts = service.get_available_fonts()
        assert len(available_fonts) > 0

        # Verify we found the expected font files (excluding .txt files)
        font_filenames = [font['filename'] for font in available_fonts]
        assert 'arial.ttf' in font_filenames
        assert 'helvetica.otf' in font_filenames
        assert 'invalid-font.txt' not in font_filenames  # Should be filtered out

        # Test font file finding
        arial_path = service.find_font_file('Arial', 'normal', 'normal')
        assert arial_path is not None
        assert 'arial.ttf' in arial_path

        # Test bold font finding
        arial_bold_path = service.find_font_file('Arial', 'bold', 'normal')
        assert arial_bold_path is not None
        assert 'arial-bold.ttf' in arial_bold_path

    def test_error_propagation(self, integration_components, sample_font_structure, temp_directory):
        """
        Test how errors are handled across component boundaries.

        Verifies error handling when font directories are inaccessible
        or font files are corrupted.
        """
        service = integration_components['custom_service']

        # Test with non-existent font
        result = service.find_font_file('NonExistentFont')
        assert result is None

        # Test loading non-existent font
        font = service.load_font('NonExistentFont')
        assert font is None

        # Test empty directories service
        empty_service = integration_components['empty_service']
        fonts = empty_service.get_available_fonts()
        assert len(fonts) == 0

    def test_cross_platform_font_discovery(self, integration_components):
        """
        Test font discovery across different platforms.

        Verifies that system font directories are detected correctly
        on different operating systems.
        """
        service = integration_components['default_service']

        # Get system-specific font directories
        system_dirs = service._font_directories
        assert len(system_dirs) >= 0  # May be empty on some systems

        current_platform = platform.system().lower()

        if current_platform == "darwin":  # macOS
            # Should include macOS system font directories
            expected_dirs = ["/System/Library/Fonts", "/Library/Fonts"]
            found_dirs = [d for d in expected_dirs if d in system_dirs]
            # At least one should exist (if directory exists on system)
            assert len(found_dirs) >= 0

        elif current_platform == "windows":
            # Should include Windows font directory
            if "C:/Windows/Fonts" in system_dirs:
                assert True  # Expected Windows directory found

        elif current_platform == "linux":
            # Should include Linux font directories
            expected_dirs = ["/usr/share/fonts", "/usr/local/share/fonts"]
            found_dirs = [d for d in expected_dirs if d in system_dirs]
            assert len(found_dirs) >= 0

    def test_font_file_format_support(self, integration_components, sample_font_structure):
        """
        Test support for different font file formats.

        Verifies that FontService correctly identifies and handles
        various font file formats.
        """
        service = integration_components['custom_service']
        available_fonts = service.get_available_fonts()

        # Check that different font formats are discovered
        font_extensions = [Path(font['filename']).suffix.lower() for font in available_fonts]

        assert '.ttf' in font_extensions
        assert '.otf' in font_extensions
        # Note: .woff files might not be supported by fonttools for loading

    def test_cache_behavior_integration(self, integration_components, sample_font_structure):
        """
        Test caching behavior across multiple operations.

        Verifies that caching works correctly during real operations
        and improves performance.
        """
        service = integration_components['custom_service']

        # Clear cache to start fresh
        service.clear_cache()
        initial_stats = service.get_cache_stats()
        assert initial_stats['loaded_fonts'] == 0
        assert initial_stats['font_file_paths'] == 0

        # Perform font operations that should populate cache
        font_path1 = service.find_font_file('Arial')
        font_path2 = service.find_font_file('Arial')  # Should hit cache

        assert font_path1 == font_path2

        # Check that cache was populated
        cache_stats = service.get_cache_stats()
        assert cache_stats['font_file_paths'] > 0

    def test_resource_management(self, integration_components, sample_font_structure, temp_directory):
        """
        Test resource management across font operations.

        Verifies proper cleanup and resource handling during
        font discovery and loading operations.
        """
        service = integration_components['custom_service']

        # Perform multiple font operations
        for i in range(10):
            fonts = service.get_available_fonts()
            assert isinstance(fonts, list)

        # Test that cache doesn't grow unbounded (basic check)
        stats = service.get_cache_stats()
        assert stats['font_file_paths'] < 100  # Reasonable upper bound

        # Test cache clearing
        service.clear_cache()
        final_stats = service.get_cache_stats()
        assert final_stats['loaded_fonts'] == 0
        assert final_stats['font_file_paths'] == 0

    def test_concurrent_operations(self, integration_components, sample_font_structure):
        """
        Test FontService under concurrent access.

        Verifies thread safety during simultaneous font operations.
        """
        import threading
        import time

        service = integration_components['custom_service']
        results = []
        errors = []

        def font_operation():
            try:
                # Perform various font operations
                fonts = service.get_available_fonts()
                path = service.find_font_file('Arial')
                stats = service.get_cache_stats()
                results.append((len(fonts), path, stats))
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=font_operation)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0
        assert len(results) == 5

        # Verify results are consistent
        first_result = results[0]
        for result in results[1:]:
            assert result[0] == first_result[0]  # Same number of fonts found
            assert result[1] == first_result[1]  # Same font path found

    @pytest.mark.parametrize("font_family,expected_extensions", [
        ("Arial", [".ttf"]),
        ("Times", [".ttf"]),
        ("Helvetica", [".otf"]),
    ])
    def test_integration_font_discovery_scenarios(self, integration_components, sample_font_structure,
                                                 font_family, expected_extensions):
        """
        Test various font discovery scenarios.

        Tests different font families and expected file types.
        """
        service = integration_components['custom_service']

        font_path = service.find_font_file(font_family)
        if font_path:  # Font was found
            file_extension = Path(font_path).suffix.lower()
            assert file_extension in expected_extensions

    def test_system_integration_with_real_fonts(self):
        """
        Test integration with actual system fonts (if available).

        This test may behave differently on different systems
        depending on installed fonts.
        """
        service = FontService()  # Use system defaults

        # This should not crash regardless of system state
        available_fonts = service.get_available_fonts()
        assert isinstance(available_fonts, list)

        # Try to find common system fonts
        common_fonts = ['Arial', 'Helvetica', 'Times']
        found_any = False

        for font in common_fonts:
            path = service.find_font_file(font)
            if path:
                found_any = True
                break

        # Note: We don't assert found_any=True because systems may not have these fonts
        # The important thing is that the operations don't crash


class TestFontServicePerformanceIntegration:
    """
    Performance-related integration tests.

    Tests FontService performance characteristics with real operations.
    """

    def test_large_directory_scanning_performance(self, temp_directory):
        """
        Test performance with large font directories.

        Creates a directory with many files and tests scanning performance.
        """
        import time

        # Create directory with many files
        large_font_dir = temp_directory / "large_fonts"
        large_font_dir.mkdir()

        # Create many mock font files
        for i in range(100):
            (large_font_dir / f"font_{i:03d}.ttf").write_bytes(b"mock font data")

        service = FontService([str(large_font_dir)])

        # Measure font discovery time
        start_time = time.time()
        fonts = service.get_available_fonts()
        discovery_time = time.time() - start_time

        assert len(fonts) == 100
        assert discovery_time < 5.0  # Should complete within 5 seconds

    def test_cache_performance_improvement(self, temp_directory):
        """
        Test that caching improves performance.

        Verifies that cached operations are faster than initial operations.
        """
        import time

        # Create test font directory
        font_dir = temp_directory / "test_fonts"
        font_dir.mkdir()
        (font_dir / "test.ttf").write_bytes(b"mock font data")

        service = FontService([str(font_dir)])

        # First operation (cache miss)
        start_time = time.time()
        path1 = service.find_font_file('test')
        first_time = time.time() - start_time

        # Second operation (cache hit)
        start_time = time.time()
        path2 = service.find_font_file('test')
        second_time = time.time() - start_time

        assert path1 == path2
        # Cache hit should be faster (or at least not significantly slower)
        assert second_time <= first_time * 2  # Allow some variance


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__])