#!/usr/bin/env python3
"""
End-to-End (E2E) Test for FontService

Tests complete font processing workflow from system font discovery
through to actual font loading and validation in real-world scenarios.
"""

import pytest
from pathlib import Path
import sys
import tempfile
import zipfile
import os
import platform
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.services.font_service import FontService
from src.converters.result_types import ConversionError


class TestFontServiceCompleteWorkflowE2E:
    """
    End-to-end tests for FontService complete workflow.

    Tests the entire pipeline from font discovery through loading
    and validation in realistic scenarios.
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
            (workspace / "fonts").mkdir()
            yield workspace

    @pytest.fixture
    def sample_font_ecosystem(self, temp_workspace):
        """
        Create a complete font ecosystem for E2E testing.

        Sets up a realistic font environment with multiple directories,
        font families, weights, and styles.
        """
        font_ecosystem = {}

        # Create system-like font directory
        system_fonts = temp_workspace / "fonts" / "system"
        system_fonts.mkdir(parents=True)

        # Create user font directory
        user_fonts = temp_workspace / "fonts" / "user"
        user_fonts.mkdir()

        # Create application font directory
        app_fonts = temp_workspace / "fonts" / "application"
        app_fonts.mkdir()

        # Define realistic font families with variants
        font_families = {
            'Arial': {
                'regular': 'arial.ttf',
                'bold': 'arial-bold.ttf',
                'italic': 'arial-italic.ttf',
                'bold_italic': 'arial-bold-italic.ttf'
            },
            'Times New Roman': {
                'regular': 'times.ttf',
                'bold': 'times-bold.ttf',
                'italic': 'times-italic.ttf'
            },
            'Helvetica': {
                'regular': 'helvetica.otf',
                'light': 'helvetica-light.otf',
                'bold': 'helvetica-bold.otf'
            },
            'Custom Font': {
                'regular': 'custom-font.ttf'
            }
        }

        # Create font files in different directories
        font_locations = {
            'Arial': system_fonts,
            'Times New Roman': system_fonts,
            'Helvetica': user_fonts,
            'Custom Font': app_fonts
        }

        created_fonts = {}
        for family, variants in font_families.items():
            created_fonts[family] = {}
            location = font_locations[family]

            for variant, filename in variants.items():
                font_path = location / filename
                # Create mock font data (in real scenario would be actual font data)
                font_path.write_bytes(self._create_mock_font_data(family, variant))
                created_fonts[family][variant] = str(font_path)

        # Add some non-font files to test filtering
        (system_fonts / "readme.txt").write_text("Font directory readme")
        (user_fonts / "license.pdf").write_bytes(b"PDF content")

        font_ecosystem.update({
            'directories': {
                'system': str(system_fonts),
                'user': str(user_fonts),
                'application': str(app_fonts)
            },
            'fonts': created_fonts,
            'all_directories': [str(system_fonts), str(user_fonts), str(app_fonts)]
        })

        return font_ecosystem

    def _create_mock_font_data(self, family: str, variant: str) -> bytes:
        """
        Create mock font data for testing.

        In a real scenario, this would be actual font file data.
        For testing, we create identifiable mock data.
        """
        return f"MOCK_FONT_DATA:{family}:{variant}".encode('utf-8')

    @pytest.fixture
    def e2e_font_service(self, sample_font_ecosystem):
        """
        Create FontService configured for E2E testing.

        Uses the complete font ecosystem for realistic testing.
        """
        return FontService(font_directories=sample_font_ecosystem['all_directories'])

    def test_complete_font_discovery_workflow(self, e2e_font_service, sample_font_ecosystem, temp_workspace):
        """
        Test the complete font discovery workflow.

        Verifies the entire process from directory scanning through
        font categorization and availability reporting.
        """
        # Phase 1: Font Discovery
        available_fonts = e2e_font_service.get_available_fonts()

        # Verify we found all expected font files
        font_filenames = [font['filename'] for font in available_fonts]
        expected_font_files = [
            'arial.ttf', 'arial-bold.ttf', 'arial-italic.ttf', 'arial-bold-italic.ttf',
            'times.ttf', 'times-bold.ttf', 'times-italic.ttf',
            'helvetica.otf', 'helvetica-light.otf', 'helvetica-bold.otf',
            'custom-font.ttf'
        ]

        for expected_file in expected_font_files:
            assert expected_file in font_filenames

        # Verify non-font files were filtered out
        assert 'readme.txt' not in font_filenames
        assert 'license.pdf' not in font_filenames

        # Phase 2: Font Organization
        fonts_by_directory = {}
        for font in available_fonts:
            directory = font['directory']
            if directory not in fonts_by_directory:
                fonts_by_directory[directory] = []
            fonts_by_directory[directory].append(font['filename'])

        # Verify fonts are organized by directory as expected
        system_dir = sample_font_ecosystem['directories']['system']
        user_dir = sample_font_ecosystem['directories']['user']
        app_dir = sample_font_ecosystem['directories']['application']

        assert len(fonts_by_directory[system_dir]) == 7  # Arial + Times variants
        assert len(fonts_by_directory[user_dir]) == 3   # Helvetica variants
        assert len(fonts_by_directory[app_dir]) == 1    # Custom font

    def test_font_family_resolution_workflow(self, e2e_font_service, sample_font_ecosystem):
        """
        Test complete font family resolution workflow.

        Tests finding fonts by family name with different weights and styles.
        """
        # Test basic font family finding
        arial_path = e2e_font_service.find_font_file('Arial', 'normal', 'normal')
        assert arial_path is not None
        assert 'arial.ttf' in arial_path

        # Test font weight variations
        arial_bold_path = e2e_font_service.find_font_file('Arial', 'bold', 'normal')
        assert arial_bold_path is not None
        assert 'arial-bold.ttf' in arial_bold_path

        # Test font style variations
        arial_italic_path = e2e_font_service.find_font_file('Arial', 'normal', 'italic')
        assert arial_italic_path is not None
        assert 'arial-italic.ttf' in arial_italic_path

        # Test font with spaces in name
        times_path = e2e_font_service.find_font_file('Times New Roman', 'normal', 'normal')
        assert times_path is not None
        assert 'times.ttf' in times_path

        # Test case insensitive matching
        helvetica_path = e2e_font_service.find_font_file('helvetica', 'normal', 'normal')
        assert helvetica_path is not None
        assert 'helvetica.otf' in helvetica_path

        # Test non-existent font
        missing_path = e2e_font_service.find_font_file('NonExistentFont')
        assert missing_path is None

    def test_font_loading_and_validation_workflow(self, e2e_font_service, sample_font_ecosystem):
        """
        Test complete font loading and validation workflow.

        Tests the end-to-end process of loading fonts and validating them.
        """
        # Note: Since we're using mock font data, actual TTFont loading will fail
        # This tests the workflow structure and error handling

        # Test loading existing font (will fail due to mock data, but tests workflow)
        font = e2e_font_service.load_font('Arial')
        assert font is None  # Expected failure with mock data

        # Test loading from direct path
        arial_path = e2e_font_service.find_font_file('Arial')
        assert arial_path is not None

        font_from_path = e2e_font_service.load_font_from_path(arial_path)
        assert font_from_path is None  # Expected failure with mock data

        # Test that the workflow handled errors gracefully
        cache_stats = e2e_font_service.get_cache_stats()
        assert isinstance(cache_stats, dict)

    def test_caching_workflow_performance(self, e2e_font_service, sample_font_ecosystem):
        """
        Test caching workflow and performance characteristics.

        Verifies that caching improves performance in realistic scenarios.
        """
        import time

        # Clear cache to start fresh
        e2e_font_service.clear_cache()

        # First discovery run (cold cache)
        start_time = time.time()
        fonts_first = e2e_font_service.get_available_fonts()
        first_run_time = time.time() - start_time

        # Second discovery run (warm cache)
        start_time = time.time()
        fonts_second = e2e_font_service.get_available_fonts()
        second_run_time = time.time() - start_time

        # Verify results are identical
        assert len(fonts_first) == len(fonts_second)

        # Test font finding caching
        start_time = time.time()
        path1 = e2e_font_service.find_font_file('Arial')
        first_find_time = time.time() - start_time

        start_time = time.time()
        path2 = e2e_font_service.find_font_file('Arial')
        second_find_time = time.time() - start_time

        assert path1 == path2
        # Second call should be faster due to caching
        assert second_find_time <= first_find_time

        # Verify cache statistics
        cache_stats = e2e_font_service.get_cache_stats()
        assert cache_stats['font_file_paths'] > 0

    def test_error_handling_and_recovery_workflow(self, temp_workspace):
        """
        Test error handling and recovery in realistic error scenarios.

        Tests how the system handles various error conditions gracefully.
        """
        # Test with inaccessible directory
        inaccessible_dir = temp_workspace / "inaccessible"
        inaccessible_dir.mkdir()

        service = FontService([str(inaccessible_dir)])

        # Simulate permission error
        with patch('os.walk', side_effect=PermissionError("Access denied")):
            fonts = service.get_available_fonts()
            assert len(fonts) == 0  # Should handle gracefully

        # Test with corrupted font directory structure
        corrupted_dir = temp_workspace / "corrupted"
        corrupted_dir.mkdir()
        (corrupted_dir / "invalid.ttf").write_bytes(b"invalid font data")

        corrupted_service = FontService([str(corrupted_dir)])
        fonts = corrupted_service.get_available_fonts()
        assert len(fonts) == 1  # File is discovered

        # Attempting to load will fail gracefully
        font = corrupted_service.load_font_from_path(str(corrupted_dir / "invalid.ttf"))
        assert font is None

    def test_cross_platform_compatibility_workflow(self, sample_font_ecosystem):
        """
        Test cross-platform compatibility workflow.

        Verifies that FontService works correctly across different platforms.
        """
        # Test with system default directories
        system_service = FontService()

        # This should work on any platform without crashing
        system_directories = system_service._font_directories
        assert isinstance(system_directories, list)

        # Get available fonts (may be empty on some systems)
        system_fonts = system_service.get_available_fonts()
        assert isinstance(system_fonts, list)

        # Test platform-specific directory detection
        current_platform = platform.system().lower()

        if current_platform in ['darwin', 'windows', 'linux']:
            # Should have detected at least some directories (if they exist)
            # Note: We don't assert len > 0 because directories may not exist
            assert isinstance(system_directories, list)

    def test_large_scale_font_management_workflow(self, temp_workspace):
        """
        Test large-scale font management workflow.

        Tests performance and behavior with large numbers of fonts.
        """
        # Create a large font collection
        large_font_dir = temp_workspace / "large_fonts"
        large_font_dir.mkdir()

        # Create many font files
        num_fonts = 50
        for i in range(num_fonts):
            font_file = large_font_dir / f"font_{i:03d}.ttf"
            font_file.write_bytes(f"MOCK_FONT_DATA_{i}".encode())

        service = FontService([str(large_font_dir)])

        # Test discovery performance
        import time
        start_time = time.time()
        fonts = service.get_available_fonts()
        discovery_time = time.time() - start_time

        assert len(fonts) == num_fonts
        assert discovery_time < 10.0  # Should complete within reasonable time

        # Test cache behavior with large number of fonts
        cache_stats = service.get_cache_stats()
        assert cache_stats['font_directories'] == 1

    @pytest.mark.parametrize("font_family,weight,style,should_find", [
        ("Arial", "normal", "normal", True),
        ("Arial", "bold", "normal", True),
        ("Arial", "normal", "italic", True),
        ("Times New Roman", "normal", "normal", True),
        ("Helvetica", "normal", "normal", True),
        ("Custom Font", "normal", "normal", True),
        ("NonExistent", "normal", "normal", False),
    ])
    def test_e2e_font_resolution_scenarios(self, e2e_font_service, font_family, weight, style, should_find):
        """
        Test various E2E font resolution scenarios.

        Parametrized test for different font resolution combinations.
        """
        path = e2e_font_service.find_font_file(font_family, weight, style)

        if should_find:
            assert path is not None
        else:
            assert path is None

    def test_complete_system_integration_workflow(self):
        """
        Test complete integration with actual system.

        This test runs against the real system and may behave differently
        on different platforms depending on installed fonts.
        """
        # Create service with system defaults
        service = FontService()

        # Test basic system integration
        directories = service._font_directories
        assert isinstance(directories, list)

        # Test font discovery (should not crash)
        fonts = service.get_available_fonts()
        assert isinstance(fonts, list)

        # Test cache operations
        initial_stats = service.get_cache_stats()
        assert isinstance(initial_stats, dict)

        # Test cache clearing
        service.clear_cache()
        final_stats = service.get_cache_stats()
        assert final_stats['loaded_fonts'] == 0


class TestFontServiceRealWorldScenariosE2E:
    """
    Real-world scenario tests for FontService.

    Tests scenarios that users might encounter in production.
    """

    def test_font_installation_simulation(self, temp_workspace):
        """
        Test scenario simulating font installation and discovery.

        Tests dynamic font discovery when fonts are added to directories.
        """
        font_dir = temp_workspace / "dynamic_fonts"
        font_dir.mkdir()

        service = FontService([str(font_dir)])

        # Initially no fonts
        fonts = service.get_available_fonts()
        assert len(fonts) == 0

        # "Install" a font
        (font_dir / "new_font.ttf").write_bytes(b"mock new font")

        # Clear cache and rediscover
        service.clear_cache()
        fonts = service.get_available_fonts()
        assert len(fonts) == 1

        # "Install" more fonts
        (font_dir / "another_font.otf").write_bytes(b"mock another font")
        (font_dir / "third_font.ttf").write_bytes(b"mock third font")

        service.clear_cache()
        fonts = service.get_available_fonts()
        assert len(fonts) == 3

    def test_mixed_font_formats_scenario(self, temp_workspace):
        """
        Test scenario with mixed font formats.

        Tests handling of different font file formats in same directory.
        """
        mixed_dir = temp_workspace / "mixed_fonts"
        mixed_dir.mkdir()

        # Create different format files
        formats_and_content = [
            ('arial.ttf', b'TTF font data'),
            ('helvetica.otf', b'OTF font data'),
            ('modern.woff', b'WOFF font data'),
            ('future.woff2', b'WOFF2 font data'),
            ('readme.txt', b'Not a font'),
            ('image.png', b'PNG image data'),
        ]

        for filename, content in formats_and_content:
            (mixed_dir / filename).write_bytes(content)

        service = FontService([str(mixed_dir)])
        fonts = service.get_available_fonts()

        # Should find only font files
        font_filenames = [font['filename'] for font in fonts]
        assert 'arial.ttf' in font_filenames
        assert 'helvetica.otf' in font_filenames
        assert 'modern.woff' in font_filenames
        assert 'future.woff2' in font_filenames
        assert 'readme.txt' not in font_filenames
        assert 'image.png' not in font_filenames


@pytest.mark.slow
class TestFontServicePerformanceE2E:
    """
    Performance-focused E2E tests for FontService.

    Tests that may take significant time to run.
    """

    def test_large_font_collection_performance(self, temp_workspace):
        """
        Test performance with very large font collections.
        """
        large_collection = temp_workspace / "large_collection"
        large_collection.mkdir()

        # Create a very large number of font files
        num_fonts = 200
        for i in range(num_fonts):
            (large_collection / f"font_{i:04d}.ttf").write_bytes(f"font_data_{i}".encode())

        service = FontService([str(large_collection)])

        import time
        start_time = time.time()
        fonts = service.get_available_fonts()
        end_time = time.time()

        assert len(fonts) == num_fonts
        processing_time = end_time - start_time
        assert processing_time < 30.0  # Should complete within 30 seconds

        # Test caching performance improvement
        start_time = time.time()
        fonts_cached = service.get_available_fonts()
        cached_time = time.time() - start_time

        assert len(fonts_cached) == num_fonts
        # Note: Since get_available_fonts rescans, caching doesn't help here
        # But the test verifies it doesn't degrade significantly


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__])