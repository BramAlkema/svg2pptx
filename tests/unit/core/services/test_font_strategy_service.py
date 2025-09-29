#!/usr/bin/env python3
"""
Test Font Strategy Service

Comprehensive tests for font analysis, strategy decisions, and fallback chains.
Tests all discovered font processing capabilities integrated into Clean Slate.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from core.services.text_to_path_processor import (
    create_text_to_path_processor,
    FontFallbackStrategy,
    FontDetectionResult,
    TextToPathResult
)


class TestFontStrategyService:
    """Test comprehensive font strategy functionality."""

    @pytest.fixture
    def mock_font_system(self):
        """Create mock font system with predictable responses."""
        font_system = Mock()

        # Mock font availability
        def mock_is_font_available(font_family):
            available_fonts = ['Arial', 'Times New Roman', 'Helvetica', 'Calibri']
            return font_family in available_fonts

        font_system.is_font_available.side_effect = mock_is_font_available
        return font_system

    @pytest.fixture
    def mock_text_layout_engine(self):
        """Create mock text layout engine."""
        engine = Mock()

        # Mock text measurement
        def mock_measure_text(text, font_metadata):
            result = Mock()
            result.width_pt = len(text) * font_metadata.size_pt * 0.6
            result.height_pt = font_metadata.size_pt * 1.2
            return result

        engine.measure_text_only.side_effect = mock_measure_text
        return engine

    @pytest.fixture
    def mock_path_generator(self):
        """Create mock path generator."""
        generator = Mock()

        # Mock path generation
        def mock_generate_path(text, font_families, font_size):
            return f'<a:path w="100" h="50"><!-- {text} --></a:path>'

        generator.generate_text_path.side_effect = mock_generate_path
        return generator

    @pytest.fixture
    def processor(self, mock_font_system, mock_text_layout_engine, mock_path_generator):
        """Create text-to-path processor with mocked services."""
        return create_text_to_path_processor(
            font_system=mock_font_system,
            text_layout_engine=mock_text_layout_engine,
            path_generator=mock_path_generator
        )

    def test_font_strategy_initialization(self, processor):
        """Test processor initialization with services."""
        assert processor is not None

        stats = processor.get_processing_statistics()
        assert stats['services_available']['font_system'] is True
        assert stats['services_available']['text_layout_engine'] is True
        assert stats['services_available']['path_generator'] is True
        assert stats['capabilities']['font_detection'] is True

    def test_system_fonts_strategy(self, processor):
        """Test strategy selection for available system fonts."""
        result = processor.assess_text_conversion_strategy(
            text_content="Hello World",
            font_families=["Arial", "Helvetica"],
            font_size=12.0
        )

        assert result.conversion_strategy == FontFallbackStrategy.SYSTEM_FONTS
        assert result.font_detection.primary_font_available is True
        assert len(result.font_detection.available_fonts) >= 1
        assert result.should_convert_to_path is False

    def test_universal_fallback_strategy(self, processor):
        """Test fallback to universal fonts when primary unavailable."""
        result = processor.assess_text_conversion_strategy(
            text_content="Test Text",
            font_families=["NonExistentFont", "AnotherMissingFont"],
            font_size=12.0
        )

        # Should fallback to universal fonts if available, or path conversion
        assert result.conversion_strategy in [
            FontFallbackStrategy.UNIVERSAL_FALLBACK,
            FontFallbackStrategy.PATH_CONVERSION
        ]
        assert result.font_detection is not None

    def test_path_conversion_strategy(self, processor):
        """Test path conversion for complex scenarios."""
        # Small font size should trigger path conversion
        result = processor.assess_text_conversion_strategy(
            text_content="Complex Unicode Text: 你好 🌟",
            font_families=["NonExistentFont"],
            font_size=6.0  # Very small font
        )

        assert result.conversion_strategy == FontFallbackStrategy.PATH_CONVERSION
        assert result.should_convert_to_path is True
        assert result.path_data is None  # Not generated in assessment

    def test_font_detection_caching(self, processor):
        """Test font availability caching."""
        # First call
        result1 = processor.assess_text_conversion_strategy(
            text_content="Test",
            font_families=["Arial"],
            font_size=12.0
        )

        # Second call should use cache
        result2 = processor.assess_text_conversion_strategy(
            text_content="Another Test",
            font_families=["Arial"],
            font_size=14.0
        )

        stats = processor.get_processing_statistics()
        assert stats['statistics']['cache_hits'] > 0

    def test_complex_text_analysis(self, processor):
        """Test text complexity analysis."""
        # Simple text
        simple_result = processor.assess_text_conversion_strategy(
            text_content="Hello",
            font_families=["Arial"],
            font_size=12.0
        )

        # Complex text with unicode and special characters
        complex_result = processor.assess_text_conversion_strategy(
            text_content="Complex: 你好 World! @#$%^&*()",
            font_families=["Arial"],
            font_size=12.0
        )

        # Complex text should have higher complexity score
        simple_complexity = simple_result.metadata.get('text_complexity', {})
        complex_complexity = complex_result.metadata.get('text_complexity', {})

        assert complex_complexity.get('has_unicode', False) is True
        assert complex_complexity.get('has_special_chars', False) is True
        assert simple_complexity.get('has_unicode', False) is False

    def test_font_confidence_scoring(self, processor):
        """Test font detection confidence scoring."""
        # Available font should have high confidence
        good_result = processor.assess_text_conversion_strategy(
            text_content="Test",
            font_families=["Arial"],
            font_size=12.0
        )

        # Unavailable font should have low confidence
        bad_result = processor.assess_text_conversion_strategy(
            text_content="Test",
            font_families=["NonExistentFont"],
            font_size=12.0
        )

        assert good_result.font_detection.confidence_score > bad_result.font_detection.confidence_score

    def test_fallback_chain_construction(self, processor):
        """Test construction of font fallback chains."""
        result = processor.assess_text_conversion_strategy(
            text_content="Test",
            font_families=["NonExistentFont", "Arial", "Times New Roman"],
            font_size=12.0
        )

        # Should have fallback chain with available fonts
        assert len(result.font_detection.fallback_chain) > 0
        assert result.font_detection.fallback_chain[0] in ["Arial", "Times New Roman"]

    def test_processing_statistics_tracking(self, processor):
        """Test processing statistics tracking."""
        initial_stats = processor.get_processing_statistics()
        initial_assessments = initial_stats['statistics']['total_assessments']

        # Perform several assessments
        for strategy in [FontFallbackStrategy.SYSTEM_FONTS, FontFallbackStrategy.PATH_CONVERSION]:
            processor.assess_text_conversion_strategy(
                text_content="Test",
                font_families=["Arial"] if strategy == FontFallbackStrategy.SYSTEM_FONTS else ["NonExistent"],
                font_size=12.0 if strategy == FontFallbackStrategy.SYSTEM_FONTS else 6.0
            )

        final_stats = processor.get_processing_statistics()
        assert final_stats['statistics']['total_assessments'] > initial_assessments

    def test_error_handling(self, processor):
        """Test error handling for edge cases."""
        # Empty text
        result = processor.assess_text_conversion_strategy(
            text_content="",
            font_families=["Arial"],
            font_size=12.0
        )
        assert result is not None

        # Empty font families
        result = processor.assess_text_conversion_strategy(
            text_content="Test",
            font_families=[],
            font_size=12.0
        )
        assert result is not None

        # Invalid font size
        result = processor.assess_text_conversion_strategy(
            text_content="Test",
            font_families=["Arial"],
            font_size=0.0
        )
        assert result is not None

    def test_performance_requirements(self, processor):
        """Test performance requirements from specification."""
        import time

        start_time = time.perf_counter()

        # Test large text processing
        result = processor.assess_text_conversion_strategy(
            text_content="This is a longer text string to test performance requirements. " * 10,
            font_families=["Arial", "Times New Roman", "Helvetica"],
            font_size=12.0
        )

        processing_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

        # Should complete within performance requirements (10ms per text element)
        assert processing_time < 10.0
        assert result.processing_time_ms < 10.0

    def test_font_strategy_configuration(self, processor):
        """Test font strategy configuration options."""
        # Test configuration access
        stats = processor.get_processing_statistics()
        config = stats['configuration']

        assert 'font_detection_enabled' in config
        assert 'fallback_confidence_threshold' in config
        assert 'universal_fallback_fonts' in config

        # Test universal fallback fonts are available
        universal_fonts = config['universal_fallback_fonts']
        assert len(universal_fonts) > 0
        assert 'Arial' in universal_fonts


class TestFontStrategyEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_processor_without_services(self):
        """Test processor creation without external services."""
        processor = create_text_to_path_processor()
        assert processor is not None

        result = processor.assess_text_conversion_strategy(
            text_content="Test",
            font_families=["Arial"],
            font_size=12.0
        )

        # Should work with fallback implementations
        assert result is not None
        assert result.conversion_strategy is not None

    def test_mixed_font_availability(self):
        """Test scenarios with mix of available and unavailable fonts."""
        processor = create_text_to_path_processor()

        result = processor.assess_text_conversion_strategy(
            text_content="Mixed Font Test",
            font_families=["NonExistentFont", "Arial", "AnotherNonExistent"],
            font_size=12.0
        )

        # Should find the available font in the mix
        assert result.font_detection.primary_font_available or len(result.font_detection.fallback_chain) > 0

    def test_unicode_text_processing(self):
        """Test processing of various unicode text."""
        processor = create_text_to_path_processor()

        unicode_tests = [
            "English Text",
            "你好世界",  # Chinese
            "مرحبا بالعالم",  # Arabic
            "Здравствуй мир",  # Russian
            "🌟⭐✨",  # Emoji
            "Mixed: Hello 你好 🌟"
        ]

        for text in unicode_tests:
            result = processor.assess_text_conversion_strategy(
                text_content=text,
                font_families=["Arial"],
                font_size=12.0
            )

            assert result is not None
            assert result.conversion_strategy is not None

    def test_font_size_boundaries(self):
        """Test font size boundary conditions."""
        processor = create_text_to_path_processor()

        font_sizes = [0.1, 1.0, 6.0, 8.0, 12.0, 24.0, 72.0, 144.0]

        for size in font_sizes:
            result = processor.assess_text_conversion_strategy(
                text_content="Size Test",
                font_families=["Arial"],
                font_size=size
            )

            assert result is not None
            # Very small fonts should trigger path conversion
            if size < 8.0:
                assert result.conversion_strategy in [
                    FontFallbackStrategy.PATH_CONVERSION,
                    FontFallbackStrategy.UNIVERSAL_FALLBACK
                ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])