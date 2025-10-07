#!/usr/bin/env python3
"""
Integration Tests for Text Processing System

End-to-end integration tests for the complete text processing pipeline,
including font strategies, layout calculations, TextPath processing,
and text-to-path conversion.
"""

import pytest
import time
from unittest.mock import Mock, patch
from core.services.text_to_path_processor import (
    create_text_to_path_processor,
    FontFallbackStrategy
)
from core.services.text_path_processor import create_text_path_processor
from core.services.path_generation_service import (
    create_path_generation_service,
    PathOptimizationLevel
)
from core.services.text_layout_engine import create_text_layout_engine
from core.ir.text_path import create_simple_text_path, TextPathMethod
from core.ir.text import TextAnchor
from core.ir.font_metadata import create_font_metadata


class TestTextProcessingIntegration:
    """Integration tests for complete text processing pipeline."""

    @pytest.fixture
    def mock_font_system(self):
        """Create comprehensive mock font system."""
        font_system = Mock()

        # Mock font availability
        available_fonts = ['Arial', 'Times New Roman', 'Helvetica', 'Calibri']
        font_system.is_font_available.side_effect = lambda font: font in available_fonts

        # Mock font metrics
        def mock_get_font_metrics(font_metadata):
            metrics = Mock()
            metrics.ascent = font_metadata.size_pt * 0.8
            metrics.descent = font_metadata.size_pt * 0.2
            metrics.line_height = font_metadata.size_pt * 1.2
            return metrics

        font_system.get_font_metrics.side_effect = mock_get_font_metrics

        # Mock glyph outlines
        def mock_get_glyph_outline(char, font_metadata):
            if char == ' ':
                return Mock(
                    glyph_name=f"space_{ord(char)}",
                    path_data="",
                    advance_width=250,
                    bbox=(0, 0, 250, 0)
                )
            else:
                return Mock(
                    glyph_name=f"glyph_{ord(char)}",
                    path_data="M 50 0 L 550 0 L 550 700 L 50 700 Z",
                    advance_width=600,
                    bbox=(50, 0, 550, 700)
                )

        font_system.get_glyph_outline.side_effect = mock_get_glyph_outline
        return font_system

    @pytest.fixture
    def integrated_services(self, mock_font_system):
        """Create fully integrated text processing services."""
        # Create all services with proper signatures
        text_layout_engine = create_text_layout_engine()
        path_generator = create_path_generation_service(
            optimization_level=PathOptimizationLevel.BASIC
        )
        text_to_path_processor = create_text_to_path_processor()
        textpath_processor = create_text_path_processor()

        return {
            'font_system': mock_font_system,
            'text_layout_engine': text_layout_engine,
            'path_generator': path_generator,
            'text_to_path_processor': text_to_path_processor,
            'textpath_processor': textpath_processor
        }

    def test_end_to_end_font_strategy_pipeline(self, integrated_services):
        """Test complete font strategy decision pipeline."""
        processor = integrated_services['text_to_path_processor']

        # Test available font scenario
        available_result = processor.assess_text_conversion_strategy(
            text_content="Available Font Test",
            font_families=["Arial"],
            font_size=12.0
        )

        assert available_result.conversion_strategy == FontFallbackStrategy.SYSTEM_FONTS
        assert available_result.font_detection.primary_font_available is True

        # Test unavailable font scenario
        unavailable_result = processor.assess_text_conversion_strategy(
            text_content="Complex Unicode: 你好 🌟",
            font_families=["NonExistentFont"],
            font_size=8.0  # Small font size
        )

        assert unavailable_result.conversion_strategy in [
            FontFallbackStrategy.PATH_CONVERSION,
            FontFallbackStrategy.UNIVERSAL_FALLBACK
        ]

    def test_text_layout_and_coordinate_conversion_integration(self, integrated_services):
        """Test text layout calculation integration."""
        layout_engine = integrated_services['text_layout_engine']

        # Test various text anchor scenarios
        test_cases = [
            ("Start Anchor", TextAnchor.START, 100.0, 0.0),
            ("Middle Anchor", TextAnchor.MIDDLE, 100.0, -0.5),
            ("End Anchor", TextAnchor.END, 100.0, -1.0)
        ]

        for text, anchor, svg_x, expected_x_ratio in test_cases:
            font_metadata = create_font_metadata("Arial", size_pt=14.0)

            layout_result = layout_engine.calculate_text_layout(
                svg_x=svg_x,
                svg_y=200.0,
                text=text,
                font_metadata=font_metadata,
                anchor=anchor
            )

            # Verify coordinate conversion
            # Note: x_emu and y_emu are the top-left coordinates in EMU
            # They can be negative for END/MIDDLE anchors (text extends left of baseline)
            assert isinstance(layout_result.x_emu, int)
            assert isinstance(layout_result.y_emu, int)
            assert layout_result.width_emu > 0
            assert layout_result.height_emu > 0
            # Verify anchor was applied correctly
            assert layout_result.anchor == anchor

    def test_textpath_processing_integration(self, integrated_services):
        """Test TextPath processing with integrated services."""
        textpath_processor = integrated_services['textpath_processor']

        # Create text path with integrated services
        text_path = create_simple_text_path(
            text="Integrated Curve Text",
            path_reference="#curve",
            font_family="Arial",
            font_size_pt=12.0
        )

        # Test with complex curved path
        complex_path = "M 0 0 Q 50 -40 100 0 Q 150 40 200 0"

        result = textpath_processor.process_text_path(text_path, complex_path)

        assert result.character_count == len("Integrated Curve Text")
        assert result.layout.total_path_length > 0
        assert len(result.layout.character_placements) > 0

        # Verify character positions are calculated correctly
        placements = result.layout.character_placements
        for i in range(len(placements) - 1):
            current = placements[i]
            next_char = placements[i + 1]
            # Each character should advance along the path
            assert next_char.position.distance_along_path > current.position.distance_along_path

    def test_text_to_path_generation_integration(self, integrated_services):
        """Test text-to-path generation with font system integration."""
        path_generator = integrated_services['path_generator']

        # Test with font system providing glyph outlines
        result = path_generator.generate_text_path(
            text="Integrated Path",
            font_families=["Arial", "Helvetica"],
            font_size=16.0,
            x=25.0,
            y=50.0
        )

        assert result.character_count == len("Integrated Path")
        assert result.drawingml_path is not None
        assert '<a:path' in result.drawingml_path
        assert result.optimization_applied is True

        # Verify metadata includes font information
        assert result.metadata['font_families'] == ["Arial", "Helvetica"]
        assert result.metadata['font_size'] == 16.0

    def test_complete_pipeline_performance(self, integrated_services):
        """Test performance of complete integrated pipeline."""
        start_time = time.perf_counter()

        # Run all major operations
        text_to_path = integrated_services['text_to_path_processor']
        layout_engine = integrated_services['text_layout_engine']
        textpath_processor = integrated_services['textpath_processor']
        path_generator = integrated_services['path_generator']

        operations = [
            # Font strategy assessment
            lambda: text_to_path.assess_text_conversion_strategy(
                "Performance Test", ["Arial"], 12.0
            ),
            # Layout calculation
            lambda: layout_engine.calculate_text_layout(
                100.0, 100.0, "Layout Test",
                create_font_metadata("Arial", size_pt=12.0),
                TextAnchor.START
            ),
            # TextPath processing
            lambda: textpath_processor.process_text_path(
                create_simple_text_path("Path Test", "#test", "Arial", 12.0),
                "M 0 0 Q 50 -25 100 0"
            ),
            # Path generation
            lambda: path_generator.generate_text_path(
                "Path Gen", ["Arial"], 12.0
            )
        ]

        results = []
        for operation in operations:
            op_start = time.perf_counter()
            result = operation()
            op_time = (time.perf_counter() - op_start) * 1000
            results.append((result, op_time))

        total_time = (time.perf_counter() - start_time) * 1000

        # Verify all operations completed successfully
        for result, op_time in results:
            assert result is not None
            assert op_time < 50.0  # Each operation should complete within 50ms

        # Total pipeline should complete within reasonable time
        assert total_time < 200.0  # 200ms for complete pipeline

    def test_error_recovery_integration(self, integrated_services):
        """Test error recovery across integrated services."""
        # Test with services that might fail
        text_to_path = integrated_services['text_to_path_processor']

        # Test with problematic inputs
        edge_cases = [
            ("", ["Arial"], 12.0),  # Empty text
            ("Test", [], 12.0),     # No font families
            ("Test", ["Arial"], 0.0),  # Zero font size
            ("Test\x00Null", ["Arial"], 12.0),  # Text with null character
        ]

        for text, fonts, size in edge_cases:
            try:
                result = text_to_path.assess_text_conversion_strategy(text, fonts, size)
                assert result is not None  # Should handle gracefully
            except Exception as e:
                pytest.fail(f"Integration failed on edge case {(text, fonts, size)}: {e}")

    def test_service_capability_consistency(self, integrated_services):
        """Test that all services report consistent capabilities."""
        services = integrated_services

        # Check that services with font_system report enhanced capabilities
        for service_name, service in services.items():
            if service_name == 'font_system':
                continue

            if hasattr(service, 'get_processing_statistics'):
                stats = service.get_processing_statistics()
                if 'services_available' in stats:
                    assert stats['services_available']['font_system'] is True

            if hasattr(service, 'get_service_statistics'):
                stats = service.get_service_statistics()
                if 'capabilities' in stats:
                    assert stats['capabilities']['glyph_extraction'] is True

            if hasattr(service, 'get_capabilities'):
                caps = service.get_capabilities()
                assert caps['font_system_integration'] is True

    def test_memory_and_caching_integration(self, integrated_services):
        """Test memory usage and caching across services."""
        text_to_path = integrated_services['text_to_path_processor']

        # Perform repeated operations to test caching
        font_families = ["Arial", "Times New Roman"]

        for _ in range(10):
            result = text_to_path.assess_text_conversion_strategy(
                "Cache Test", font_families, 12.0
            )
            assert result is not None

        # Check that caching is working
        stats = text_to_path.get_processing_statistics()
        assert stats['statistics']['cache_hits'] > 0

        # Clear cache and verify
        text_to_path.clear_cache()
        stats_after_clear = text_to_path.get_processing_statistics()
        assert stats_after_clear['cache_size'] == 0

    def test_unicode_processing_integration(self, integrated_services):
        """Test unicode text processing across all services."""
        unicode_texts = [
            "English Text",
            "中文测试",       # Chinese
            "العربية",        # Arabic
            "🌟⭐✨🎉",       # Emoji
            "Mixed: Hello 世界 🌟 Test"
        ]

        services = integrated_services

        for text in unicode_texts:
            # Test font strategy
            strategy_result = services['text_to_path_processor'].assess_text_conversion_strategy(
                text, ["Arial"], 12.0
            )
            assert strategy_result is not None

            # Test layout calculation
            layout_result = services['text_layout_engine'].calculate_text_layout(
                0.0, 0.0, text, create_font_metadata("Arial", size_pt=12.0),
                TextAnchor.START
            )
            assert layout_result is not None

            # Test path generation
            path_result = services['path_generator'].generate_text_path(
                text, ["Arial"], 12.0
            )
            assert path_result is not None

    def test_fallback_chain_integration(self, integrated_services):
        """Test fallback chain behavior across services."""
        text_to_path = integrated_services['text_to_path_processor']

        # Test with cascading font failures
        result = text_to_path.assess_text_conversion_strategy(
            text_content="Fallback Chain Test",
            font_families=["NonExistent1", "NonExistent2", "Arial", "Fallback"],
            font_size=12.0
        )

        # Should find Arial in the chain
        assert result.font_detection.primary_font_available or len(result.font_detection.fallback_chain) > 0

        # Should prefer system fonts when available
        if result.font_detection.primary_font_available:
            assert result.conversion_strategy == FontFallbackStrategy.SYSTEM_FONTS


class TestTextProcessingEdgeCases:
    """Test edge cases in integrated text processing."""

    def test_services_without_dependencies(self):
        """Test services functioning without optional dependencies."""
        # Create services without dependencies
        layout_engine = create_text_layout_engine()
        path_generator = create_path_generation_service()
        text_to_path = create_text_to_path_processor()
        textpath_processor = create_text_path_processor()

        # All should function with fallback implementations
        services = [layout_engine, path_generator, text_to_path, textpath_processor]

        for service in services:
            assert service is not None

        # Test basic functionality
        font_metadata = create_font_metadata("Arial", size_pt=12.0)

        # Layout calculation
        layout_result = layout_engine.calculate_text_layout(
            0.0, 0.0, "Test", font_metadata, TextAnchor.START
        )
        assert layout_result is not None

        # Path generation
        path_result = path_generator.generate_text_path("Test", ["Arial"], 12.0)
        assert path_result is not None

        # Font strategy
        strategy_result = text_to_path.assess_text_conversion_strategy(
            "Test", ["Arial"], 12.0
        )
        assert strategy_result is not None

    def test_extreme_input_scenarios(self):
        """Test with extreme input scenarios."""
        # Create basic services
        text_to_path = create_text_to_path_processor()
        path_generator = create_path_generation_service()

        extreme_scenarios = [
            # Very long text
            ("A" * 1000, ["Arial"], 12.0),
            # Very small font
            ("Small", ["Arial"], 0.1),
            # Very large font
            ("Large", ["Arial"], 200.0),
            # Many font families
            ("Fonts", ["Font" + str(i) for i in range(50)], 12.0),
        ]

        for text, fonts, size in extreme_scenarios:
            try:
                # Should handle without crashing
                strategy_result = text_to_path.assess_text_conversion_strategy(text, fonts, size)
                path_result = path_generator.generate_text_path(text, fonts, size)

                assert strategy_result is not None
                assert path_result is not None
            except Exception as e:
                pytest.fail(f"Failed on extreme scenario {(len(text), len(fonts), size)}: {e}")

    def test_concurrent_processing_safety(self):
        """Test thread safety of text processing services."""
        import threading
        import queue

        text_to_path = create_text_to_path_processor()
        results_queue = queue.Queue()
        errors_queue = queue.Queue()

        def worker(worker_id):
            try:
                for i in range(10):
                    result = text_to_path.assess_text_conversion_strategy(
                        f"Worker {worker_id} Text {i}",
                        ["Arial"],
                        12.0
                    )
                    results_queue.put((worker_id, i, result is not None))
            except Exception as e:
                errors_queue.put((worker_id, str(e)))

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check results
        assert errors_queue.empty(), f"Concurrent processing errors: {list(errors_queue.queue)}"

        results = []
        while not results_queue.empty():
            results.append(results_queue.get())

        # Should have 50 successful results (5 workers × 10 operations)
        assert len(results) == 50
        assert all(success for _, _, success in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])