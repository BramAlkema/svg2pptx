#!/usr/bin/env python3
"""
Unit Test for FontEmbeddingEngine

Tests the advanced font embedding engine with comprehensive coverage
of subsetting, embedding validation, and performance tracking.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import sys
import os
import tempfile
from fontTools.ttLib import TTFont
from fontTools.ttLib.ttFont import TTLibError
from fontTools import subset

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.services.font_embedding_engine import FontEmbeddingEngine
from src.data.embedded_font import (
    EmbeddedFont, FontSubsetRequest, FontEmbeddingStats, EmbeddingPermission
)
from src.services.font_service import FontService
from src.converters.result_types import ConversionError


class TestFontEmbeddingEngine:
    """
    Unit tests for FontEmbeddingEngine class.

    Tests font embedding, subsetting, validation, and performance tracking.
    """

    @pytest.fixture
    def setup_test_data(self):
        """
        Setup common test data and mock objects.

        Creates mock fonts, character sets, and test configurations.
        """
        return {
            'mock_font_path': '/test/fonts/arial.ttf',
            'sample_text': 'Hello World! 123',
            'sample_characters': {'H', 'e', 'l', 'o', ' ', 'W', 'r', 'd', '!', '1', '2', '3'},
            'sample_font_data': b'mock font binary data',
            'large_text': 'The quick brown fox jumps over the lazy dog' * 10,
            'unicode_text': 'Hello 世界 🌍 Café naïve résumé',
            'empty_text': '',
            'optimization_levels': ['none', 'basic', 'aggressive'],
            'font_formats': ['ttf', 'otf', 'woff', 'woff2']
        }

    @pytest.fixture
    def mock_font_service(self):
        """Create mock FontService for testing."""
        mock_service = Mock(spec=FontService)
        mock_service.load_font_from_path = Mock()
        return mock_service

    @pytest.fixture
    def mock_ttfont(self):
        """Create mock TTFont object for testing."""
        mock_font = Mock(spec=TTFont)
        mock_font.__contains__ = Mock(return_value=True)
        mock_font.keys.return_value = ['cmap', 'head', 'hhea', 'hmtx', 'maxp', 'name', 'post', 'glyf', 'OS/2']

        # Mock OS/2 table for embedding permissions
        mock_os2 = Mock()
        mock_os2.fsType = 0  # Installable
        mock_font.__getitem__ = Mock(return_value=mock_os2)

        # Mock glyph set
        mock_font.getGlyphSet.return_value = {f'glyph_{i}': None for i in range(100)}

        return mock_font

    @pytest.fixture
    def component_instance(self, mock_font_service):
        """
        Create instance of FontEmbeddingEngine under test.

        Uses mock FontService to avoid system dependencies.
        """
        return FontEmbeddingEngine(font_service=mock_font_service)

    def test_initialization(self, component_instance, mock_font_service):
        """
        Test FontEmbeddingEngine initialization and basic properties.

        Verifies component initializes correctly with proper attributes.
        """
        assert component_instance is not None
        assert component_instance._font_service == mock_font_service
        assert hasattr(component_instance, '_embedding_stats')
        assert hasattr(component_instance, '_subset_cache')
        assert isinstance(component_instance._embedding_stats, FontEmbeddingStats)
        assert isinstance(component_instance._subset_cache, dict)

    def test_initialization_with_default_font_service(self):
        """Test initialization with default FontService when none provided."""
        with patch('src.services.font_embedding_engine.FontService') as mock_font_service_class:
            mock_service = Mock()
            mock_font_service_class.return_value = mock_service

            engine = FontEmbeddingEngine()

            assert engine._font_service == mock_service
            mock_font_service_class.assert_called_once()

    def test_extract_characters_from_single_string(self, component_instance, setup_test_data):
        """Test character extraction from single string."""
        characters = component_instance.extract_characters_from_text(setup_test_data['sample_text'])

        assert characters == setup_test_data['sample_characters']
        assert isinstance(characters, set)

    def test_extract_characters_from_list_of_strings(self, component_instance, setup_test_data):
        """Test character extraction from list of strings."""
        text_list = ['Hello', 'World', '123']
        expected_chars = {'H', 'e', 'l', 'o', 'W', 'r', 'd', '1', '2', '3'}

        characters = component_instance.extract_characters_from_text(text_list)

        assert characters == expected_chars

    def test_extract_characters_from_empty_input(self, component_instance):
        """Test character extraction from empty inputs."""
        # Empty string
        chars_empty_str = component_instance.extract_characters_from_text('')
        assert chars_empty_str == set()

        # Empty list
        chars_empty_list = component_instance.extract_characters_from_text([])
        assert chars_empty_list == set()

        # List with empty strings
        chars_empty_items = component_instance.extract_characters_from_text(['', ''])
        assert chars_empty_items == set()

    def test_extract_characters_unicode_support(self, component_instance, setup_test_data):
        """Test character extraction with Unicode characters."""
        characters = component_instance.extract_characters_from_text(setup_test_data['unicode_text'])

        # Should include Unicode characters
        assert '世' in characters
        assert '界' in characters
        assert '🌍' in characters
        assert 'é' in characters
        assert 'ï' in characters

    def test_analyze_font_embedding_permission_installable(self, component_instance, mock_ttfont):
        """Test embedding permission analysis for installable fonts."""
        # Default fsType = 0 (installable)
        permission = component_instance.analyze_font_embedding_permission(mock_ttfont)
        assert permission == EmbeddingPermission.INSTALLABLE

    def test_analyze_font_embedding_permission_restricted(self, component_instance, mock_ttfont):
        """Test embedding permission analysis for restricted fonts."""
        mock_os2 = Mock()
        mock_os2.fsType = 0x0002  # Restricted License bit
        mock_ttfont.__getitem__ = Mock(return_value=mock_os2)

        permission = component_instance.analyze_font_embedding_permission(mock_ttfont)
        assert permission == EmbeddingPermission.RESTRICTED

    def test_analyze_font_embedding_permission_preview_print(self, component_instance, mock_ttfont):
        """Test embedding permission analysis for preview & print fonts."""
        mock_os2 = Mock()
        mock_os2.fsType = 0x0004  # Preview & Print bit
        mock_ttfont.__getitem__ = Mock(return_value=mock_os2)

        permission = component_instance.analyze_font_embedding_permission(mock_ttfont)
        assert permission == EmbeddingPermission.PREVIEW_PRINT

    def test_analyze_font_embedding_permission_no_os2_table(self, component_instance, mock_ttfont):
        """Test embedding permission analysis when OS/2 table is missing."""
        mock_ttfont.__contains__ = Mock(side_effect=lambda x: x != 'OS/2')

        permission = component_instance.analyze_font_embedding_permission(mock_ttfont)
        assert permission == EmbeddingPermission.INSTALLABLE  # Default

    def test_validate_embedding_permission_allowed(self, component_instance, mock_ttfont):
        """Test embedding validation for allowed fonts."""
        # Default fsType = 0 (installable)
        is_allowed = component_instance.validate_embedding_permission(mock_ttfont)
        assert is_allowed is True

    def test_validate_embedding_permission_restricted(self, component_instance, mock_ttfont):
        """Test embedding validation for restricted fonts."""
        mock_os2 = Mock()
        mock_os2.fsType = 0x0002  # Restricted License bit
        mock_ttfont.__getitem__ = Mock(return_value=mock_os2)

        is_allowed = component_instance.validate_embedding_permission(mock_ttfont)
        assert is_allowed is False

    @patch('os.path.getsize')
    @patch('tempfile.NamedTemporaryFile')
    @patch('os.unlink')
    @patch('os.path.exists')
    def test_create_font_subset_success(self, mock_exists, mock_unlink, mock_tempfile,
                                      mock_getsize, component_instance, mock_font_service,
                                      mock_ttfont, setup_test_data):
        """Test successful font subset creation."""
        # Setup mocks
        mock_getsize.return_value = 1000  # Original size
        mock_exists.return_value = True
        mock_font_service.load_font_from_path.return_value = mock_ttfont

        # Mock temporary file
        mock_temp = Mock()
        mock_temp.name = '/tmp/subset.ttf'
        mock_tempfile.return_value.__enter__.return_value = mock_temp

        # Mock file operations
        with patch('builtins.open', mock_open(read_data=setup_test_data['sample_font_data'])):
            # Mock font save
            mock_ttfont.save = Mock()

            # Mock subsetting
            with patch.object(component_instance, '_perform_font_subsetting') as mock_subset:
                mock_subset.return_value = setup_test_data['sample_font_data']

                subset_request = FontSubsetRequest(
                    font_path=setup_test_data['mock_font_path'],
                    characters=setup_test_data['sample_characters'],
                    font_name='Arial'
                )

                result = component_instance.create_font_subset(subset_request)

        assert result is not None
        assert isinstance(result, EmbeddedFont)
        assert result.font_name == 'Arial'
        assert result.font_data == setup_test_data['sample_font_data']
        assert result.original_size == 1000
        assert result.embedding_allowed is True

    def test_create_font_subset_font_not_found(self, component_instance, mock_font_service, setup_test_data):
        """Test font subset creation when font file not found."""
        mock_font_service.load_font_from_path.return_value = None

        subset_request = FontSubsetRequest(
            font_path=setup_test_data['mock_font_path'],
            characters=setup_test_data['sample_characters'],
            font_name='Arial'
        )

        result = component_instance.create_font_subset(subset_request)

        assert result is None
        assert component_instance._embedding_stats.total_fonts_failed == 1

    def test_create_font_subset_embedding_not_allowed(self, component_instance, mock_font_service,
                                                    mock_ttfont, setup_test_data):
        """Test font subset creation when embedding is not allowed."""
        # Setup restricted font
        mock_os2 = Mock()
        mock_os2.fsType = 0x0002  # Restricted License bit
        mock_ttfont.__getitem__ = Mock(return_value=mock_os2)
        mock_font_service.load_font_from_path.return_value = mock_ttfont

        subset_request = FontSubsetRequest(
            font_path=setup_test_data['mock_font_path'],
            characters=setup_test_data['sample_characters'],
            font_name='Arial'
        )

        result = component_instance.create_font_subset(subset_request)

        assert result is None
        assert component_instance._embedding_stats.total_fonts_failed == 1

    def test_create_font_subset_caching(self, component_instance, mock_font_service,
                                       mock_ttfont, setup_test_data):
        """Test that font subset results are cached."""
        mock_font_service.load_font_from_path.return_value = mock_ttfont

        with patch.object(component_instance, '_perform_font_subsetting') as mock_subset:
            mock_subset.return_value = setup_test_data['sample_font_data']
            with patch('os.path.getsize', return_value=1000):

                subset_request = FontSubsetRequest(
                    font_path=setup_test_data['mock_font_path'],
                    characters=setup_test_data['sample_characters'],
                    font_name='Arial'
                )

                # First call
                result1 = component_instance.create_font_subset(subset_request)
                # Second call should hit cache
                result2 = component_instance.create_font_subset(subset_request)

                assert result1 == result2
                # Should only call subsetting once
                assert mock_subset.call_count == 1

    @patch('fontTools.subset.Subsetter')
    @patch('fontTools.subset.Options')
    def test_perform_font_subsetting_basic_optimization(self, mock_options_class, mock_subsetter_class,
                                                       component_instance, mock_ttfont, setup_test_data):
        """Test font subsetting with basic optimization level."""
        mock_options = Mock()
        mock_options_class.return_value = mock_options
        mock_subsetter = Mock()
        mock_subsetter_class.return_value = mock_subsetter

        with patch('tempfile.NamedTemporaryFile') as mock_tempfile:
            mock_temp = Mock()
            mock_temp.name = '/tmp/subset.ttf'
            mock_tempfile.return_value.__enter__.return_value = mock_temp

            with patch('builtins.open', mock_open(read_data=setup_test_data['sample_font_data'])):
                with patch('os.path.exists', return_value=True):
                    with patch('os.unlink'):

                        result = component_instance._perform_font_subsetting(
                            mock_ttfont,
                            setup_test_data['sample_characters'],
                            'basic',
                            True,
                            True
                        )

        assert result == setup_test_data['sample_font_data']
        mock_subsetter.populate.assert_called_once()
        mock_subsetter.subset.assert_called_once_with(mock_ttfont)

    @patch('fontTools.subset.Subsetter')
    @patch('fontTools.subset.Options')
    def test_perform_font_subsetting_aggressive_optimization(self, mock_options_class, mock_subsetter_class,
                                                            component_instance, mock_ttfont, setup_test_data):
        """Test font subsetting with aggressive optimization level."""
        mock_options = Mock()
        mock_options_class.return_value = mock_options
        mock_subsetter = Mock()
        mock_subsetter_class.return_value = mock_subsetter

        with patch('tempfile.NamedTemporaryFile') as mock_tempfile:
            mock_temp = Mock()
            mock_temp.name = '/tmp/subset.ttf'
            mock_tempfile.return_value.__enter__.return_value = mock_temp

            with patch('builtins.open', mock_open(read_data=setup_test_data['sample_font_data'])):
                with patch('os.path.exists', return_value=True):
                    with patch('os.unlink'):

                        result = component_instance._perform_font_subsetting(
                            mock_ttfont,
                            setup_test_data['sample_characters'],
                            'aggressive',
                            False,
                            False
                        )

        # Verify aggressive options were set
        assert mock_options.desubroutinize is True
        assert mock_options.hinting is False
        assert mock_options.legacy_kern is False

    def test_perform_font_subsetting_failure(self, component_instance, mock_ttfont, setup_test_data):
        """Test font subsetting failure handling."""
        with patch('fontTools.subset.Subsetter', side_effect=Exception("Subsetting failed")):

            result = component_instance._perform_font_subsetting(
                mock_ttfont,
                setup_test_data['sample_characters'],
                'basic',
                True,
                True
            )

        assert result is None

    def test_create_embedding_for_text_success(self, component_instance, setup_test_data):
        """Test creating font embedding optimized for specific text."""
        with patch.object(component_instance, 'create_font_subset') as mock_create_subset:
            mock_embedded_font = Mock(spec=EmbeddedFont)
            mock_create_subset.return_value = mock_embedded_font

            result = component_instance.create_embedding_for_text(
                font_path=setup_test_data['mock_font_path'],
                text_content=setup_test_data['sample_text'],
                font_name='Arial'
            )

        assert result == mock_embedded_font
        mock_create_subset.assert_called_once()

        # Verify subset request was created correctly
        call_args = mock_create_subset.call_args[0][0]
        assert isinstance(call_args, FontSubsetRequest)
        assert call_args.font_path == setup_test_data['mock_font_path']
        assert call_args.font_name == 'Arial'

    def test_create_embedding_for_text_empty_text(self, component_instance, setup_test_data):
        """Test creating font embedding with empty text content."""
        result = component_instance.create_embedding_for_text(
            font_path=setup_test_data['mock_font_path'],
            text_content='',
            font_name='Arial'
        )

        assert result is None

    def test_batch_create_embeddings_success(self, component_instance, setup_test_data):
        """Test batch creation of font embeddings."""
        mappings = [
            {'text': 'Hello', 'font_path': '/font1.ttf', 'font_name': 'Font1'},
            {'text': 'World', 'font_path': '/font2.ttf', 'font_name': 'Font2'},
        ]

        with patch.object(component_instance, 'create_embedding_for_text') as mock_create:
            mock_font1 = Mock(spec=EmbeddedFont)
            mock_font2 = Mock(spec=EmbeddedFont)
            mock_create.side_effect = [mock_font1, mock_font2]

            results = component_instance.batch_create_embeddings(mappings)

        assert len(results) == 2
        assert results[0] == mock_font1
        assert results[1] == mock_font2
        assert mock_create.call_count == 2

    def test_batch_create_embeddings_with_failures(self, component_instance):
        """Test batch creation with some failures."""
        mappings = [
            {'text': 'Hello', 'font_path': '/font1.ttf'},
            {'text': '', 'font_path': '/font2.ttf'},  # Empty text
            {'text': 'World'},  # Missing font_path
        ]

        with patch.object(component_instance, 'create_embedding_for_text') as mock_create:
            mock_font = Mock(spec=EmbeddedFont)
            mock_create.return_value = mock_font

            results = component_instance.batch_create_embeddings(mappings)

        assert len(results) == 3
        assert results[0] == mock_font  # Success
        assert results[1] is None       # Empty text
        assert results[2] is None       # Missing font_path

    def test_get_embedding_statistics(self, component_instance):
        """Test getting embedding statistics."""
        stats = component_instance.get_embedding_statistics()

        assert isinstance(stats, FontEmbeddingStats)
        assert stats == component_instance._embedding_stats

    def test_clear_cache(self, component_instance):
        """Test cache clearing functionality."""
        # Add items to cache
        component_instance._subset_cache['test'] = Mock()
        component_instance._embedding_stats.total_fonts_processed = 5

        component_instance.clear_cache()

        assert len(component_instance._subset_cache) == 0
        assert component_instance._embedding_stats.total_fonts_processed == 0

    def test_get_cache_stats(self, component_instance):
        """Test cache statistics reporting."""
        # Add items to cache and stats
        component_instance._subset_cache['test'] = Mock()
        component_instance._embedding_stats.total_fonts_processed = 10
        component_instance._embedding_stats.total_fonts_embedded = 8
        component_instance._embedding_stats.total_fonts_failed = 2

        stats = component_instance.get_cache_stats()

        assert stats['cached_subsets'] == 1
        assert stats['total_fonts_processed'] == 10
        assert stats['successful_embeddings'] == 8
        assert stats['failed_embeddings'] == 2

    def test_estimate_subset_size_reduction_success(self, component_instance, mock_font_service,
                                                   mock_ttfont, setup_test_data):
        """Test successful size reduction estimation."""
        mock_font_service.load_font_from_path.return_value = mock_ttfont
        mock_ttfont.getGlyphSet.return_value = {f'glyph_{i}': None for i in range(100)}

        with patch('os.path.getsize', return_value=1000):

            estimate = component_instance.estimate_subset_size_reduction(
                setup_test_data['mock_font_path'],
                setup_test_data['sample_characters']
            )

        assert 'estimated_reduction' in estimate
        assert 'original_size_bytes' in estimate
        assert 'estimated_subset_size_bytes' in estimate
        assert estimate['original_size_bytes'] == 1000
        assert 0 <= estimate['estimated_reduction'] <= 1

    def test_estimate_subset_size_reduction_font_not_found(self, component_instance, mock_font_service,
                                                          setup_test_data):
        """Test size reduction estimation when font not found."""
        mock_font_service.load_font_from_path.return_value = None

        estimate = component_instance.estimate_subset_size_reduction(
            setup_test_data['mock_font_path'],
            setup_test_data['sample_characters']
        )

        assert estimate['estimated_reduction'] == 0.0
        assert 'error' in estimate
        assert 'Font loading failed' in estimate['error']

    @pytest.mark.parametrize("optimization_level,expected_desubroutinize", [
        ("none", False),
        ("basic", False),
        ("aggressive", True),
    ])
    def test_parametrized_optimization_levels(self, component_instance, mock_ttfont,
                                            optimization_level, expected_desubroutinize,
                                            setup_test_data):
        """Test various optimization levels using parametrized inputs."""
        with patch('fontTools.subset.Options') as mock_options_class:
            with patch('fontTools.subset.Subsetter'):
                with patch('tempfile.NamedTemporaryFile'):
                    with patch('builtins.open', mock_open(read_data=b'test')):
                        with patch('os.path.exists', return_value=True):
                            with patch('os.unlink'):

                                mock_options = Mock()
                                mock_options_class.return_value = mock_options

                                component_instance._perform_font_subsetting(
                                    mock_ttfont,
                                    setup_test_data['sample_characters'],
                                    optimization_level,
                                    True,
                                    True
                                )

                                assert mock_options.desubroutinize == expected_desubroutinize

    def test_error_handling_subsetting_exception(self, component_instance, mock_font_service,
                                                mock_ttfont, setup_test_data):
        """Test error handling when subsetting raises exception."""
        mock_font_service.load_font_from_path.return_value = mock_ttfont

        with patch.object(component_instance, '_perform_font_subsetting', side_effect=Exception("Test error")):
            with patch('os.path.getsize', return_value=1000):

                subset_request = FontSubsetRequest(
                    font_path=setup_test_data['mock_font_path'],
                    characters=setup_test_data['sample_characters'],
                    font_name='Arial'
                )

                result = component_instance.create_font_subset(subset_request)

        assert result is None
        assert component_instance._embedding_stats.total_fonts_failed == 1


class TestFontEmbeddingEngineHelperFunctions:
    """
    Tests for standalone helper functions in the font embedding engine module.
    """

    def test_character_extraction_with_mixed_types(self):
        """Test character extraction with mixed input types."""
        engine = FontEmbeddingEngine()

        # Test with mixed list containing non-strings
        mixed_input = ['Hello', 123, 'World', None]
        characters = engine.extract_characters_from_text(mixed_input)

        # Should only process strings
        expected = {'H', 'e', 'l', 'o', 'W', 'r', 'd'}
        assert characters == expected


@pytest.mark.integration
class TestFontEmbeddingEngineIntegration:
    """
    Integration tests for FontEmbeddingEngine.

    Tests FontEmbeddingEngine with real dependencies and workflows.
    """

    def test_end_to_end_embedding_workflow(self):
        """Test complete workflow from text to embedded font."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a minimal mock font file for testing
            font_path = Path(temp_dir) / "test.ttf"
            font_path.write_bytes(b"mock font data")

            # Mock the font loading and subsetting
            with patch('src.services.font_embedding_engine.FontService') as mock_service_class:
                mock_service = Mock()
                mock_service_class.return_value = mock_service

                mock_font = Mock(spec=TTFont)
                mock_font.__contains__ = Mock(return_value=True)
                mock_os2 = Mock()
                mock_os2.fsType = 0
                mock_font.__getitem__ = Mock(return_value=mock_os2)
                mock_service.load_font_from_path.return_value = mock_font

                engine = FontEmbeddingEngine()

                # Test the workflow
                with patch.object(engine, '_perform_font_subsetting', return_value=b'subset data'):

                    result = engine.create_embedding_for_text(
                        font_path=str(font_path),
                        text_content="Hello World",
                        font_name="TestFont"
                    )

                assert result is not None
                assert isinstance(result, EmbeddedFont)

    def test_real_world_character_extraction(self):
        """Test character extraction with real-world text scenarios."""
        engine = FontEmbeddingEngine()

        # Test with realistic document content
        document_text = """
        Lorem ipsum dolor sit amet, consectetur adipiscing elit.
        Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
        Ut enim ad minim veniam, quis nostrud exercitation ullamco.

        Numbers: 1234567890
        Symbols: !@#$%^&*()_+-=[]{}|;':\",./<>?
        """

        characters = engine.extract_characters_from_text(document_text)

        # Should include various character types
        assert len(characters) > 50  # Rich character set
        assert ' ' in characters    # Spaces
        assert '\n' in characters   # Newlines
        assert '1' in characters    # Numbers
        assert '!' in characters    # Symbols
        assert 'L' in characters    # Uppercase
        assert 'l' in characters    # Lowercase


if __name__ == "__main__":
    # Allow running tests directly with: python test_font_embedding_engine.py
    pytest.main([__file__])