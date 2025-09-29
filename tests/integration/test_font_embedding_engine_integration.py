#!/usr/bin/env python3
"""
Integration Test for FontEmbeddingEngine

Tests FontEmbeddingEngine integration with FontService and real font operations.
Verifies subsetting workflows and cross-component functionality.
"""

import pytest
from pathlib import Path
import sys
import tempfile
import os
from unittest.mock import Mock, patch, mock_open

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.services.font_embedding_engine import FontEmbeddingEngine
from core.services.font_service import FontService
from src.data.embedded_font import (
    EmbeddedFont, FontSubsetRequest, FontEmbeddingStats, EmbeddingPermission
)
from src.converters.result_types import ConversionError


class TestFontEmbeddingEngineSystemIntegration:
    """
    Integration tests for FontEmbeddingEngine with real system components.

    Tests actual font processing workflows and FontService integration.
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

        Creates a realistic font directory with mock font files.
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

        # Create mock font files with realistic names and content
        font_files = [
            ("arial.ttf", b"mock arial font data with more content for realistic size"),
            ("arial-bold.ttf", b"mock arial bold font data with content"),
            ("times-new-roman.ttf", b"mock times new roman font data"),
            ("helvetica.otf", b"mock helvetica opentype font data"),
            ("comic-sans.woff", b"mock comic sans webfont data"),
        ]

        for font_file, content in font_files:
            # Create font files in both directories
            (system_fonts / font_file).write_bytes(content)
            (user_fonts / font_file).write_bytes(content)

        font_dirs['main'] = main_fonts
        font_dirs['system'] = system_fonts
        font_dirs['user'] = user_fonts
        font_dirs['font_files'] = font_files

        return font_dirs

    @pytest.fixture
    def integration_components(self, sample_font_structure):
        """
        Setup FontEmbeddingEngine with realistic configuration.

        Creates integrated FontService and FontEmbeddingEngine instances.
        """
        font_service = FontService([
            str(sample_font_structure['system']),
            str(sample_font_structure['user'])
        ])

        embedding_engine = FontEmbeddingEngine(font_service=font_service)

        return {
            'font_service': font_service,
            'embedding_engine': embedding_engine,
            'sample_fonts': sample_font_structure
        }

    def test_basic_integration_flow(self, integration_components, temp_directory):
        """
        Test the basic integration workflow.

        Verifies FontEmbeddingEngine and FontService work together correctly.
        """
        engine = integration_components['embedding_engine']
        font_service = integration_components['font_service']
        sample_fonts = integration_components['sample_fonts']

        # Test font discovery through service
        available_fonts = font_service.get_available_fonts()
        assert len(available_fonts) > 0

        # Test character extraction
        test_text = "Hello World! 123"
        characters = engine.extract_characters_from_text(test_text)
        assert len(characters) > 0
        assert 'H' in characters
        assert ' ' in characters
        assert '!' in characters

        # Test embedding permission analysis with mock font
        with patch('fontTools.ttLib.TTFont') as mock_ttfont_class:
            mock_font = Mock()
            mock_font.__contains__ = Mock(return_value=True)
            mock_os2 = Mock()
            mock_os2.fsType = 0  # Installable
            mock_font.__getitem__ = Mock(return_value=mock_os2)
            mock_ttfont_class.return_value = mock_font

            permission = engine.analyze_font_embedding_permission(mock_font)
            assert permission == EmbeddingPermission.INSTALLABLE

    def test_error_propagation(self, integration_components, temp_directory):
        """
        Test how errors are handled across component boundaries.

        Verifies error handling when font operations fail.
        """
        engine = integration_components['embedding_engine']

        # Test with non-existent font path
        non_existent_path = str(temp_directory / "nonexistent.ttf")
        result = engine.create_embedding_for_text(
            font_path=non_existent_path,
            text_content="Test text",
            font_name="NonExistent"
        )

        assert result is None

        # Verify error was recorded in statistics
        stats = engine.get_embedding_statistics()
        assert stats.total_fonts_failed > 0

    def test_data_consistency(self, integration_components, temp_directory):
        """
        Test data consistency across the integration.

        Verifies data transformations maintain integrity.
        """
        engine = integration_components['embedding_engine']
        sample_fonts = integration_components['sample_fonts']

        # Test character extraction consistency
        test_texts = [
            "Hello World",
            ["Hello", "World"],
            "Testing 123",
            "Unicode: café naïve"
        ]

        for text in test_texts:
            characters = engine.extract_characters_from_text(text)
            assert isinstance(characters, set)

            # Verify characters are unique and contain expected content
            if isinstance(text, str):
                expected_chars = set(text)
            else:
                expected_chars = set(''.join(text))

            assert characters == expected_chars

    def test_configuration_integration(self, integration_components, temp_directory):
        """
        Test how configuration affects the integrated system.

        Verifies configuration propagation and validation.
        """
        engine = integration_components['embedding_engine']
        sample_fonts = integration_components['sample_fonts']

        # Test different optimization levels
        optimization_levels = ['none', 'basic', 'aggressive']
        test_characters = {'H', 'e', 'l', 'o'}

        font_path = str(sample_fonts['system'] / "arial.ttf")

        for level in optimization_levels:
            subset_request = FontSubsetRequest(
                font_path=font_path,
                characters=test_characters,
                font_name='Arial',
                optimization_level=level,
                preserve_hinting=True,
                preserve_layout_tables=True
            )

            # Verify configuration is properly stored
            assert subset_request.optimization_level == level
            assert subset_request.preserve_hinting is True
            assert subset_request.preserve_layout_tables is True

    def test_resource_management(self, integration_components, temp_directory):
        """
        Test resource management across components.

        Verifies proper cleanup and resource handling.
        """
        engine = integration_components['embedding_engine']

        # Test cache management
        initial_stats = engine.get_cache_stats()
        assert initial_stats['cached_subsets'] == 0

        # Perform operations that would populate cache
        test_text = "Sample text for caching"
        characters = engine.extract_characters_from_text(test_text)

        # Test cache clearing
        engine.clear_cache()
        cleared_stats = engine.get_cache_stats()
        assert cleared_stats['cached_subsets'] == 0
        assert cleared_stats['total_fonts_processed'] == 0

    def test_concurrent_operations(self, integration_components, temp_directory):
        """
        Test integration under concurrent access.

        Verifies thread safety of integrated components.
        """
        import threading
        import time

        engine = integration_components['embedding_engine']
        results = []
        errors = []

        def character_extraction_operation():
            try:
                text = f"Test text {threading.current_thread().ident}"
                characters = engine.extract_characters_from_text(text)
                results.append(len(characters))
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=character_extraction_operation)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0
        assert len(results) == 5

    @pytest.mark.parametrize("test_scenario,text_content,expected_outcome", [
        ("basic_text", "Hello World", "success"),
        ("unicode_text", "Café naïve résumé", "success"),
        ("numbers_symbols", "123!@#$%", "success"),
        ("empty_text", "", "no_characters"),
        ("large_text", "A" * 1000, "success"),
    ])
    def test_integration_scenarios(self, integration_components, test_scenario,
                                 text_content, expected_outcome, temp_directory):
        """
        Test various integration scenarios.

        Tests different text types and expected behaviors.
        """
        engine = integration_components['embedding_engine']

        characters = engine.extract_characters_from_text(text_content)

        if expected_outcome == "success":
            assert len(characters) > 0
            # Verify all characters from text are captured
            if text_content:
                expected_chars = set(text_content)
                assert characters == expected_chars
        elif expected_outcome == "no_characters":
            assert len(characters) == 0

    def test_performance_integration(self, integration_components, temp_directory):
        """
        Test performance characteristics of the integrated system.

        Measures processing time and resource usage.
        """
        import time

        engine = integration_components['embedding_engine']

        # Test character extraction performance
        large_text = "The quick brown fox jumps over the lazy dog. " * 100

        start_time = time.time()
        characters = engine.extract_characters_from_text(large_text)
        extraction_time = time.time() - start_time

        assert extraction_time < 1.0  # Should complete quickly
        assert len(characters) > 0

        # Test batch processing performance
        text_batches = [f"Batch {i} text content" for i in range(10)]

        start_time = time.time()
        for text in text_batches:
            engine.extract_characters_from_text(text)
        batch_time = time.time() - start_time

        assert batch_time < 2.0  # Should handle batches efficiently

    def test_external_dependency_integration(self, integration_components, temp_directory):
        """
        Test integration with external dependencies.

        Verifies FontService integration and file system operations.
        """
        engine = integration_components['embedding_engine']
        font_service = integration_components['font_service']

        # Test integration with FontService
        assert engine._font_service == font_service

        # Test that FontService methods are accessible through engine
        available_fonts = font_service.get_available_fonts()
        assert isinstance(available_fonts, list)

        # Test font file discovery integration
        font_path = font_service.find_font_file('Arial')
        # May be None if Arial not found, but should not crash

        # Test cache statistics integration
        service_stats = font_service.get_cache_stats()
        engine_stats = engine.get_cache_stats()

        assert isinstance(service_stats, dict)
        assert isinstance(engine_stats, dict)


class TestFontEmbeddingEngineSubsettingIntegration:
    """
    Integration tests for font subsetting workflows.

    Tests the complete subsetting pipeline with mock fonttools operations.
    """

    @pytest.fixture
    def mock_font_environment(self, tmp_path):
        """Setup mock font environment for subsetting tests."""
        # Create mock font file
        font_path = tmp_path / "test_font.ttf"
        font_path.write_bytes(b"mock font data for subsetting tests")

        return {
            'font_path': str(font_path),
            'font_data': b"mock font data for subsetting tests",
            'subset_data': b"mock subset font data"
        }

    def test_subsetting_workflow_integration(self, mock_font_environment):
        """Test complete font subsetting workflow."""
        engine = FontEmbeddingEngine()

        # Mock the font loading and subsetting pipeline
        with patch.object(engine._font_service, 'load_font_from_path') as mock_load:
            mock_font = Mock()
            mock_font.__contains__ = Mock(return_value=True)
            mock_os2 = Mock()
            mock_os2.fsType = 0  # Installable
            mock_font.__getitem__ = Mock(return_value=mock_os2)
            mock_load.return_value = mock_font

            with patch.object(engine, '_perform_font_subsetting') as mock_subset:
                mock_subset.return_value = mock_font_environment['subset_data']

                with patch('os.path.getsize', return_value=1000):

                    # Test the complete workflow
                    subset_request = FontSubsetRequest(
                        font_path=mock_font_environment['font_path'],
                        characters={'H', 'e', 'l', 'o'},
                        font_name='TestFont'
                    )

                    result = engine.create_font_subset(subset_request)

        # Verify successful integration
        assert result is not None
        assert isinstance(result, EmbeddedFont)
        assert result.font_name == 'TestFont'
        assert result.font_data == mock_font_environment['subset_data']

    def test_batch_subsetting_integration(self, mock_font_environment):
        """Test batch font subsetting integration."""
        engine = FontEmbeddingEngine()

        text_font_mappings = [
            {
                'text': 'Hello',
                'font_path': mock_font_environment['font_path'],
                'font_name': 'Font1'
            },
            {
                'text': 'World',
                'font_path': mock_font_environment['font_path'],
                'font_name': 'Font2'
            }
        ]

        with patch.object(engine, 'create_embedding_for_text') as mock_create:
            mock_font1 = Mock(spec=EmbeddedFont)
            mock_font2 = Mock(spec=EmbeddedFont)
            mock_create.side_effect = [mock_font1, mock_font2]

            results = engine.batch_create_embeddings(text_font_mappings)

        assert len(results) == 2
        assert results[0] == mock_font1
        assert results[1] == mock_font2

    def test_size_estimation_integration(self, mock_font_environment):
        """Test font size estimation integration."""
        engine = FontEmbeddingEngine()

        # Mock font loading for size estimation
        with patch.object(engine._font_service, 'load_font_from_path') as mock_load:
            mock_font = Mock()
            mock_font.getGlyphSet.return_value = {f'glyph_{i}': None for i in range(100)}
            mock_load.return_value = mock_font

            with patch('os.path.getsize', return_value=10000):

                estimate = engine.estimate_subset_size_reduction(
                    mock_font_environment['font_path'],
                    {'H', 'e', 'l', 'o'}  # 4 characters out of 100 glyphs
                )

        assert 'estimated_reduction' in estimate
        assert 'original_size_bytes' in estimate
        assert estimate['original_size_bytes'] == 10000
        assert 0 <= estimate['estimated_reduction'] <= 1


class TestFontEmbeddingEngineErrorIntegration:
    """
    Integration tests for error handling across components.

    Tests error propagation and recovery in integrated workflows.
    """

    def test_font_service_error_integration(self):
        """Test error handling when FontService operations fail."""
        # Create engine with mock font service that fails
        mock_font_service = Mock()
        mock_font_service.load_font_from_path.return_value = None

        engine = FontEmbeddingEngine(font_service=mock_font_service)

        # Test that font loading failure is handled gracefully
        result = engine.create_embedding_for_text(
            font_path="/nonexistent/font.ttf",
            text_content="Test text"
        )

        assert result is None

        # Verify error statistics were updated
        stats = engine.get_embedding_statistics()
        assert stats.total_fonts_failed > 0

    def test_subsetting_error_integration(self):
        """Test error handling when font subsetting fails."""
        engine = FontEmbeddingEngine()

        # Mock font service to return valid font
        with patch.object(engine._font_service, 'load_font_from_path') as mock_load:
            mock_font = Mock()
            mock_font.__contains__ = Mock(return_value=True)
            mock_os2 = Mock()
            mock_os2.fsType = 0
            mock_font.__getitem__ = Mock(return_value=mock_os2)
            mock_load.return_value = mock_font

            # Mock subsetting to fail
            with patch.object(engine, '_perform_font_subsetting', return_value=None):
                with patch('os.path.getsize', return_value=1000):

                    subset_request = FontSubsetRequest(
                        font_path="/test/font.ttf",
                        characters={'H', 'e', 'l', 'o'},
                        font_name='TestFont'
                    )

                    result = engine.create_font_subset(subset_request)

        assert result is None

        # Verify error was recorded
        stats = engine.get_embedding_statistics()
        assert stats.total_fonts_failed > 0


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__])