#!/usr/bin/env python3
"""
Unit Test for FontService

Tests the font loading and management service using the established
unit test template patterns for comprehensive coverage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from pathlib import Path
import sys
import os
import tempfile
from fontTools.ttLib import TTFont
from fontTools.ttLib.ttFont import TTLibError

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.services.font_service import FontService
from src.converters.result_types import ConversionError


class TestFontService:
    """
    Unit tests for FontService class.

    Tests font loading, discovery, validation, and caching functionality.
    """

    @pytest.fixture
    def setup_test_data(self):
        """
        Setup common test data and mock objects.

        Creates mock font directories and sample font files for testing.
        """
        return {
            'mock_font_directories': ['/test/fonts', '/test/system/fonts'],
            'sample_font_families': ['Arial', 'Times New Roman', 'Helvetica'],
            'font_file_extensions': ['.ttf', '.otf', '.woff', '.woff2'],
            'mock_font_file_paths': {
                'arial': '/test/fonts/arial.ttf',
                'times': '/test/fonts/times.ttf',
                'helvetica': '/test/fonts/helvetica.otf'
            }
        }

    @pytest.fixture
    def component_instance(self, setup_test_data):
        """
        Create instance of FontService under test.

        Uses mock font directories to avoid system dependencies.
        """
        return FontService(font_directories=setup_test_data['mock_font_directories'])

    @pytest.fixture
    def mock_ttfont(self):
        """Create mock TTFont object for testing."""
        mock_font = Mock(spec=TTFont)
        mock_font.__contains__ = Mock(return_value=True)  # For 'table' in font checks

        # Mock required tables
        mock_font.keys.return_value = ['cmap', 'head', 'hhea', 'hmtx', 'maxp', 'name', 'post', 'glyf']

        # Mock head table
        mock_head = Mock()
        mock_head.unitsPerEm = 1000
        mock_font.__getitem__ = Mock(return_value=mock_head)

        return mock_font

    def test_initialization(self, component_instance):
        """
        Test FontService initialization and basic properties.

        Verifies component initializes correctly with proper attributes.
        """
        assert component_instance is not None
        assert hasattr(component_instance, '_font_cache')
        assert hasattr(component_instance, '_font_directories')
        assert hasattr(component_instance, '_font_file_cache')
        assert isinstance(component_instance._font_cache, dict)
        assert isinstance(component_instance._font_directories, list)

    def test_initialization_with_default_directories(self):
        """Test initialization with system default font directories."""
        with patch.object(FontService, '_get_system_font_directories') as mock_get_dirs:
            mock_get_dirs.return_value = ['/default/fonts']
            service = FontService()
            assert service._font_directories == ['/default/fonts']
            mock_get_dirs.assert_called_once()

    @patch('platform.system')
    @patch('os.path.exists')
    def test_get_system_font_directories_macos(self, mock_exists, mock_system, component_instance):
        """Test system font directory detection on macOS."""
        mock_system.return_value = "Darwin"
        mock_exists.return_value = True

        directories = component_instance._get_system_font_directories()

        assert "/System/Library/Fonts" in directories
        assert "/Library/Fonts" in directories

    @patch('platform.system')
    @patch('os.path.exists')
    def test_get_system_font_directories_windows(self, mock_exists, mock_system, component_instance):
        """Test system font directory detection on Windows."""
        mock_system.return_value = "Windows"
        mock_exists.return_value = True

        directories = component_instance._get_system_font_directories()

        assert "C:/Windows/Fonts" in directories

    @patch('platform.system')
    @patch('os.path.exists')
    def test_get_system_font_directories_linux(self, mock_exists, mock_system, component_instance):
        """Test system font directory detection on Linux."""
        mock_system.return_value = "Linux"
        mock_exists.return_value = True

        directories = component_instance._get_system_font_directories()

        assert "/usr/share/fonts" in directories
        assert "/usr/local/share/fonts" in directories

    @patch('os.walk')
    @patch('os.path.exists')
    def test_find_font_file_success(self, mock_exists, mock_walk, component_instance, setup_test_data):
        """Test successful font file discovery."""
        mock_exists.return_value = True
        mock_walk.return_value = [
            ('/test/fonts', [], ['arial.ttf', 'times.ttf', 'other.txt'])
        ]

        # Mock the font matching method
        component_instance._matches_font_criteria = Mock(return_value=True)

        result = component_instance.find_font_file('Arial')

        assert result == '/test/fonts/arial.ttf'
        component_instance._matches_font_criteria.assert_called()

    @patch('os.walk')
    @patch('os.path.exists')
    def test_find_font_file_not_found(self, mock_exists, mock_walk, component_instance):
        """Test font file discovery when font not found."""
        mock_exists.return_value = True
        mock_walk.return_value = [
            ('/test/fonts', [], ['other.ttf'])
        ]

        component_instance._matches_font_criteria = Mock(return_value=False)

        result = component_instance.find_font_file('NonExistentFont')

        assert result is None

    def test_find_font_file_caching(self, component_instance):
        """Test that font file discovery results are cached."""
        with patch.object(component_instance, '_font_file_cache', {}) as mock_cache:
            # First call should search
            with patch('os.walk') as mock_walk, patch('os.path.exists', return_value=True):
                mock_walk.return_value = [('/test/fonts', [], ['arial.ttf'])]
                component_instance._matches_font_criteria = Mock(return_value=True)

                result1 = component_instance.find_font_file('Arial')
                result2 = component_instance.find_font_file('Arial')

                assert result1 == result2
                assert 'Arial:normal:normal' in mock_cache

    def test_matches_font_criteria_basic(self, component_instance):
        """Test basic font criteria matching."""
        # Test exact match
        assert component_instance._matches_font_criteria('/test/arial.ttf', 'Arial', 'normal', 'normal')

        # Test case insensitive
        assert component_instance._matches_font_criteria('/test/ARIAL.TTF', 'arial', 'normal', 'normal')

        # Test space handling
        assert component_instance._matches_font_criteria('/test/timesnewroman.ttf', 'Times New Roman', 'normal', 'normal')

    def test_matches_font_criteria_weight_style(self, component_instance):
        """Test font criteria matching with weight and style."""
        # Test bold weight
        assert component_instance._matches_font_criteria('/test/arial-bold.ttf', 'Arial', 'bold', 'normal')

        # Test italic style
        assert component_instance._matches_font_criteria('/test/arial-italic.ttf', 'Arial', 'normal', 'italic')

        # Test no match
        assert not component_instance._matches_font_criteria('/test/times.ttf', 'Arial', 'normal', 'normal')

    @patch('src.services.font_service.TTFont')
    def test_load_font_success(self, mock_ttfont_class, component_instance, mock_ttfont, setup_test_data):
        """Test successful font loading."""
        mock_ttfont_class.return_value = mock_ttfont

        with patch.object(component_instance, 'find_font_file') as mock_find:
            mock_find.return_value = setup_test_data['mock_font_file_paths']['arial']

            result = component_instance.load_font('Arial')

            assert result == mock_ttfont
            mock_ttfont_class.assert_called_once_with(setup_test_data['mock_font_file_paths']['arial'])

    def test_load_font_not_found(self, component_instance):
        """Test font loading when font file not found."""
        with patch.object(component_instance, 'find_font_file') as mock_find:
            mock_find.return_value = None

            result = component_instance.load_font('NonExistentFont')

            assert result is None

    @patch('src.services.font_service.TTFont')
    def test_load_font_invalid_file(self, mock_ttfont_class, component_instance, setup_test_data):
        """Test font loading with invalid font file."""
        mock_ttfont_class.side_effect = TTLibError("Invalid font")

        with patch.object(component_instance, 'find_font_file') as mock_find:
            mock_find.return_value = setup_test_data['mock_font_file_paths']['arial']

            result = component_instance.load_font('Arial')

            assert result is None

    def test_load_font_caching(self, component_instance, mock_ttfont, setup_test_data):
        """Test that loaded fonts are cached."""
        with patch('src.services.font_service.TTFont', return_value=mock_ttfont):
            with patch.object(component_instance, 'find_font_file') as mock_find:
                mock_find.return_value = setup_test_data['mock_font_file_paths']['arial']

                # Load same font twice
                result1 = component_instance.load_font('Arial')
                result2 = component_instance.load_font('Arial')

                assert result1 == result2 == mock_ttfont
                # find_font_file should only be called once due to caching
                assert mock_find.call_count == 1

    @patch('src.services.font_service.TTFont')
    def test_load_font_from_path_success(self, mock_ttfont_class, component_instance, mock_ttfont):
        """Test loading font directly from path."""
        mock_ttfont_class.return_value = mock_ttfont
        font_path = '/test/arial.ttf'

        result = component_instance.load_font_from_path(font_path)

        assert result == mock_ttfont
        mock_ttfont_class.assert_called_once_with(font_path)

    @patch('src.services.font_service.TTFont')
    def test_load_font_from_path_invalid(self, mock_ttfont_class, component_instance):
        """Test loading invalid font from path."""
        mock_ttfont_class.side_effect = TTLibError("Invalid font")

        result = component_instance.load_font_from_path('/test/invalid.ttf')

        assert result is None

    def test_validate_font_valid(self, component_instance, mock_ttfont):
        """Test validation of valid font."""
        errors = component_instance.validate_font(mock_ttfont)

        assert len(errors) == 0

    def test_validate_font_missing_tables(self, component_instance):
        """Test validation of font with missing tables."""
        mock_font = Mock(spec=TTFont)
        mock_font.__contains__ = Mock(side_effect=lambda x: x not in ['cmap', 'head'])
        mock_font.keys.return_value = ['glyf', 'hhea']  # Missing some required tables

        errors = component_instance.validate_font(mock_font)

        assert len(errors) > 0
        assert any("Missing required font tables" in error.message for error in errors)

    def test_validate_font_no_glyph_data(self, component_instance):
        """Test validation of font without glyph data."""
        mock_font = Mock(spec=TTFont)
        mock_font.__contains__ = Mock(side_effect=lambda x: x not in ['glyf', 'CFF ', 'CFF2'])
        mock_font.keys.return_value = ['cmap', 'head', 'hhea', 'hmtx', 'maxp', 'name', 'post']

        errors = component_instance.validate_font(mock_font)

        assert len(errors) > 0
        assert any("no glyph outline data" in error.message for error in errors)

    def test_validate_font_invalid_units_per_em(self, component_instance):
        """Test validation of font with invalid unitsPerEm."""
        mock_font = Mock(spec=TTFont)
        mock_font.__contains__ = Mock(return_value=True)
        mock_font.keys.return_value = ['cmap', 'head', 'hhea', 'hmtx', 'maxp', 'name', 'post', 'glyf']

        # Mock head table with invalid unitsPerEm
        mock_head = Mock()
        mock_head.unitsPerEm = 0
        mock_font.__getitem__ = Mock(return_value=mock_head)

        errors = component_instance.validate_font(mock_font)

        assert len(errors) > 0
        assert any("Invalid unitsPerEm" in error.message for error in errors)

    @patch('os.walk')
    @patch('os.path.exists')
    def test_get_available_fonts(self, mock_exists, mock_walk):
        """Test getting list of available fonts."""
        # Create FontService with single directory to avoid duplicates
        service = FontService(['/test/fonts'])

        mock_exists.return_value = True
        mock_walk.return_value = [
            ('/test/fonts', [], ['arial.ttf', 'times.otf', 'readme.txt'])
        ]

        fonts = service.get_available_fonts()

        assert len(fonts) == 2  # Only .ttf and .otf files
        assert fonts[0]['filename'] == 'arial.ttf'
        assert fonts[1]['filename'] == 'times.otf'

    def test_clear_cache(self, component_instance):
        """Test cache clearing functionality."""
        # Add some items to cache
        component_instance._font_cache['test'] = Mock()
        component_instance._font_file_cache['test'] = '/test/path'

        component_instance.clear_cache()

        assert len(component_instance._font_cache) == 0
        assert len(component_instance._font_file_cache) == 0

    def test_get_cache_stats(self, component_instance, setup_test_data):
        """Test cache statistics reporting."""
        # Add some items to cache
        component_instance._font_cache['font1'] = Mock()
        component_instance._font_file_cache['path1'] = '/test/path'

        stats = component_instance.get_cache_stats()

        assert stats['loaded_fonts'] == 1
        assert stats['font_file_paths'] == 1
        assert stats['font_directories'] == len(setup_test_data['mock_font_directories'])

    def test_error_handling_permission_denied(self, component_instance):
        """Test error handling when font directories are inaccessible."""
        with patch('os.walk', side_effect=PermissionError("Access denied")):
            with patch('os.path.exists', return_value=True):
                result = component_instance.find_font_file('Arial')
                assert result is None  # Should handle gracefully

    @pytest.mark.parametrize("font_family,weight,style,expected_cache_key", [
        ("Arial", "normal", "normal", "Arial:normal:normal"),
        ("Times New Roman", "bold", "italic", "Times New Roman:bold:italic"),
        ("Helvetica", "light", "normal", "Helvetica:light:normal"),
    ])
    def test_parametrized_cache_keys(self, component_instance, font_family, weight, style, expected_cache_key):
        """Test various font parameter combinations for cache key generation."""
        with patch('os.path.exists', return_value=False):  # No font directories exist
            component_instance.load_font(font_family, weight, style)
            # Verify cache key was used (will be None in _font_file_cache due to not found)
            assert expected_cache_key in component_instance._font_file_cache


class TestFontServiceHelperFunctions:
    """
    Tests for standalone helper functions in the font service module.
    """

    def test_font_matching_edge_cases(self):
        """Test font matching with edge case inputs."""
        service = FontService([])

        # Test empty inputs
        assert not service._matches_font_criteria('', '', 'normal', 'normal')

        # Test special characters
        assert service._matches_font_criteria('/test/font-name.ttf', 'font-name', 'normal', 'normal')


@pytest.mark.integration
class TestFontServiceIntegration:
    """
    Integration tests for FontService.

    Tests FontService with real file system operations and actual font files.
    """

    def test_end_to_end_font_loading_workflow(self):
        """Test complete workflow from font discovery to loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock font directory structure
            font_dir = Path(temp_dir) / "fonts"
            font_dir.mkdir()

            # Create a mock font file (just for file system testing)
            mock_font_file = font_dir / "test.ttf"
            mock_font_file.write_bytes(b"mock font data")

            service = FontService([str(font_dir)])

            # Test font discovery
            fonts = service.get_available_fonts()
            assert len(fonts) == 1
            assert fonts[0]['filename'] == 'test.ttf'

    def test_real_world_font_directory_scanning(self):
        """Test with real font directories if available."""
        service = FontService()  # Use system defaults

        # This should not crash even if no fonts are found
        fonts = service.get_available_fonts()
        assert isinstance(fonts, list)

        # Cache should be empty initially
        stats = service.get_cache_stats()
        assert stats['loaded_fonts'] == 0


if __name__ == "__main__":
    # Allow running tests directly with: python test_font_service.py
    pytest.main([__file__])