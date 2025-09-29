#!/usr/bin/env python3
"""
Test Path Generation Service

Comprehensive tests for text-to-path conversion, glyph outline processing,
and DrawingML path generation.
"""

import pytest
import re
from unittest.mock import Mock, patch
from core.services.path_generation_service import (
    create_path_generation_service,
    PathOptimizationLevel,
    PathGenerationResult,
    PathCommand,
    PathPoint,
    GlyphOutline
)
from core.ir.font_metadata import create_font_metadata


class TestPathGenerationService:
    """Test path generation service functionality."""

    @pytest.fixture
    def mock_font_system(self):
        """Create mock font system with glyph outline support."""
        font_system = Mock()

        # Mock glyph outline generation
        def mock_get_glyph_outline(char, font_metadata):
            if char == ' ':
                return GlyphOutline(
                    glyph_name=f"space_{ord(char)}",
                    path_data="",  # Empty for space
                    advance_width=250,
                    bbox=(0, 0, 250, 0)
                )
            else:
                # Simple rectangular glyph for testing
                width = 600
                height = 700
                path_data = f"M 50 0 L {width-50} 0 L {width-50} {height} L 50 {height} Z"
                return GlyphOutline(
                    glyph_name=f"glyph_{ord(char)}",
                    path_data=path_data,
                    advance_width=width,
                    bbox=(50, 0, width-50, height)
                )

        font_system.get_glyph_outline.side_effect = mock_get_glyph_outline
        return font_system

    @pytest.fixture
    def service_basic(self):
        """Create path generation service with basic optimization."""
        return create_path_generation_service(
            optimization_level=PathOptimizationLevel.BASIC
        )

    @pytest.fixture
    def service_with_font_system(self, mock_font_system):
        """Create path generation service with font system."""
        return create_path_generation_service(
            font_system=mock_font_system,
            optimization_level=PathOptimizationLevel.BASIC
        )

    def test_service_initialization(self, service_basic):
        """Test service initialization."""
        assert service_basic is not None

        stats = service_basic.get_service_statistics()
        assert stats['optimization_level'] == PathOptimizationLevel.BASIC.value
        assert stats['capabilities']['drawingml_generation'] is True
        assert stats['capabilities']['synthetic_glyphs'] is True

    def test_basic_text_path_generation(self, service_basic):
        """Test basic text path generation without font system."""
        result = service_basic.generate_text_path(
            text="Hello",
            font_families=["Arial"],
            font_size=12.0,
            x=0.0,
            y=0.0
        )

        assert isinstance(result, PathGenerationResult)
        assert result.character_count == 5
        assert result.drawingml_path is not None
        assert len(result.drawingml_path) > 0
        assert result.processing_time_ms > 0

        # Should contain DrawingML path structure
        assert '<a:path' in result.drawingml_path
        assert 'w=' in result.drawingml_path
        assert 'h=' in result.drawingml_path

    def test_text_path_generation_with_font_system(self, service_with_font_system):
        """Test text path generation with font system."""
        result = service_with_font_system.generate_text_path(
            text="Test",
            font_families=["Arial"],
            font_size=16.0,
            x=10.0,
            y=20.0
        )

        assert result.character_count == 4
        assert result.optimization_applied is True
        assert result.metadata['font_families'] == ["Arial"]
        assert result.metadata['font_size'] == 16.0

    def test_space_character_handling(self, service_with_font_system):
        """Test space character handling."""
        result = service_with_font_system.generate_text_path(
            text="A B",
            font_families=["Arial"],
            font_size=12.0
        )

        assert result.character_count == 3
        # Space should not contribute visible path commands but should advance position
        assert result.drawingml_path is not None

    def test_empty_text_handling(self, service_basic):
        """Test empty text handling."""
        result = service_basic.generate_text_path(
            text="",
            font_families=["Arial"],
            font_size=12.0
        )

        assert result.character_count == 0
        assert result.drawingml_path is not None

    def test_optimization_levels(self):
        """Test different optimization levels."""
        test_text = "Optimize"
        font_families = ["Arial"]
        font_size = 12.0

        # Test each optimization level
        for level in [PathOptimizationLevel.NONE, PathOptimizationLevel.BASIC, PathOptimizationLevel.AGGRESSIVE]:
            service = create_path_generation_service(optimization_level=level)
            result = service.generate_text_path(test_text, font_families, font_size)

            assert result.character_count == len(test_text)
            assert result.optimization_applied == (level != PathOptimizationLevel.NONE)

    def test_font_size_scaling(self, service_basic):
        """Test font size scaling in path generation."""
        text = "Scale"
        font_families = ["Arial"]
        sizes = [8.0, 12.0, 24.0]

        results = []
        for size in sizes:
            result = service_basic.generate_text_path(text, font_families, size)
            results.append(result)

        # Larger fonts should generally result in larger paths
        # (This is a rough check since we're using synthetic glyphs)
        for i in range(1, len(results)):
            current = results[i]
            previous = results[i-1]
            # Metadata should reflect font size increase
            assert current.metadata['font_size'] > previous.metadata['font_size']

    def test_position_offset_handling(self, service_basic):
        """Test position offset handling."""
        offsets = [(0.0, 0.0), (50.0, 25.0), (-10.0, -5.0)]

        for x, y in offsets:
            result = service_basic.generate_text_path(
                text="Pos",
                font_families=["Arial"],
                font_size=12.0,
                x=x,
                y=y
            )

            assert result.character_count == 3
            # Position should be reflected in the generated path
            assert result.drawingml_path is not None

    def test_unicode_text_support(self, service_basic):
        """Test unicode text support."""
        unicode_texts = [
            "ASCII",
            "你好",  # Chinese
            "🌟",    # Emoji
            "Mixed: ABC 你好 🌟"
        ]

        for text in unicode_texts:
            result = service_basic.generate_text_path(
                text=text,
                font_families=["Arial"],
                font_size=12.0
            )

            assert result.character_count == len(text)
            assert result.drawingml_path is not None

    def test_multiple_font_families(self, service_basic):
        """Test handling of multiple font families."""
        result = service_basic.generate_text_path(
            text="Multi",
            font_families=["NonExistent", "Arial", "Times"],
            font_size=12.0
        )

        assert result.character_count == 5
        assert result.metadata['font_families'] == ["NonExistent", "Arial", "Times"]

    def test_performance_requirements(self, service_basic):
        """Test performance requirements."""
        import time

        # Test with moderately long text
        text = "Performance test with moderate length text for timing validation"

        start_time = time.perf_counter()
        result = service_basic.generate_text_path(
            text=text,
            font_families=["Arial"],
            font_size=12.0
        )
        total_time = (time.perf_counter() - start_time) * 1000

        # Should complete reasonably quickly
        assert total_time < 100.0  # 100ms for complex text
        assert result.processing_time_ms < 100.0

    def test_error_handling_and_fallbacks(self, service_basic):
        """Test error handling and fallback mechanisms."""
        # Test with invalid inputs that should trigger fallbacks
        result = service_basic.generate_text_path(
            text="Fallback",
            font_families=[],  # Empty font families
            font_size=0.0      # Invalid font size
        )

        # Should handle gracefully and return fallback result
        assert result is not None
        assert result.character_count == len("Fallback")
        assert result.metadata.get('fallback', False) is True


class TestPathCommandGeneration:
    """Test path command generation and DrawingML conversion."""

    def test_path_command_creation(self):
        """Test PathCommand creation and properties."""
        # MoveTo command
        move_cmd = PathCommand('moveTo', [PathPoint(10.0, 20.0)])
        assert move_cmd.command == 'moveTo'
        assert len(move_cmd.points) == 1

        # LineTo command
        line_cmd = PathCommand('lineTo', [PathPoint(30.0, 40.0)])
        assert line_cmd.command == 'lineTo'

        # CurveTo command
        curve_cmd = PathCommand('curveTo', [
            PathPoint(10.0, 20.0),  # Control point 1
            PathPoint(30.0, 40.0),  # Control point 2
            PathPoint(50.0, 60.0)   # End point
        ])
        assert curve_cmd.command == 'curveTo'
        assert len(curve_cmd.points) == 3

    def test_drawingml_conversion(self):
        """Test conversion to DrawingML format."""
        # MoveTo command
        move_cmd = PathCommand('moveTo', [PathPoint(10.0, 20.0)])
        drawingml = move_cmd.to_drawingml(scale=1.0)
        assert '<a:moveTo>' in drawingml
        assert 'x="10"' in drawingml
        assert 'y="20"' in drawingml

        # LineTo command
        line_cmd = PathCommand('lineTo', [PathPoint(30.0, 40.0)])
        drawingml = line_cmd.to_drawingml(scale=1.0)
        assert '<a:lnTo>' in drawingml
        assert 'x="30"' in drawingml
        assert 'y="40"' in drawingml

        # CurveTo command
        curve_cmd = PathCommand('curveTo', [
            PathPoint(10.0, 20.0),
            PathPoint(30.0, 40.0),
            PathPoint(50.0, 60.0)
        ])
        drawingml = curve_cmd.to_drawingml(scale=1.0)
        assert '<a:cubicBezTo>' in drawingml
        assert drawingml.count('<a:pt') == 3  # Three points

        # Close command
        close_cmd = PathCommand('closePath', [])
        drawingml = close_cmd.to_drawingml(scale=1.0)
        assert '<a:close/>' in drawingml

    def test_scaling_in_drawingml_conversion(self):
        """Test scaling during DrawingML conversion."""
        cmd = PathCommand('moveTo', [PathPoint(10.0, 20.0)])

        # Test different scales
        scales = [0.5, 1.0, 2.0, 10.0]
        for scale in scales:
            drawingml = cmd.to_drawingml(scale=scale)
            expected_x = int(10.0 * scale)
            expected_y = int(20.0 * scale)
            assert f'x="{expected_x}"' in drawingml
            assert f'y="{expected_y}"' in drawingml

    def test_empty_command_handling(self):
        """Test handling of commands with no points."""
        empty_move = PathCommand('moveTo', [])
        drawingml = empty_move.to_drawingml()
        assert drawingml == ""  # Should return empty string

        empty_line = PathCommand('lineTo', [])
        drawingml = empty_line.to_drawingml()
        assert drawingml == ""

    def test_invalid_command_handling(self):
        """Test handling of invalid commands."""
        invalid_cmd = PathCommand('invalidCommand', [PathPoint(0.0, 0.0)])
        drawingml = invalid_cmd.to_drawingml()
        assert drawingml == ""  # Should return empty string for unknown commands


class TestGlyphOutlineProcessing:
    """Test glyph outline processing functionality."""

    def test_glyph_outline_creation(self):
        """Test GlyphOutline creation."""
        outline = GlyphOutline(
            glyph_name="test_glyph",
            path_data="M 0 0 L 100 0 L 100 100 L 0 100 Z",
            advance_width=120,
            bbox=(0, 0, 100, 100)
        )

        assert outline.glyph_name == "test_glyph"
        assert outline.path_data is not None
        assert outline.advance_width == 120
        assert outline.bbox == (0, 0, 100, 100)

    def test_synthetic_glyph_generation(self):
        """Test synthetic glyph generation for fallback."""
        # Test with service that doesn't have font system (will use synthetic glyphs)
        service_basic = create_path_generation_service()
        result = service_basic.generate_text_path(
            text="Synthetic",
            font_families=["NonExistentFont"],
            font_size=12.0
        )

        assert result.character_count == len("Synthetic")
        assert result.metadata.get('fallback_glyphs_used', 0) >= 0

    def test_space_glyph_handling(self):
        """Test space character glyph handling."""
        service = create_path_generation_service()

        result = service.generate_text_path(
            text=" ",  # Single space
            font_families=["Arial"],
            font_size=12.0
        )

        assert result.character_count == 1
        # Space should not contribute visible geometry but should advance position


class TestPathGenerationEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_small_font_sizes(self):
        """Test with very small font sizes."""
        service = create_path_generation_service()

        small_sizes = [0.1, 0.5, 1.0]

        for size in small_sizes:
            result = service.generate_text_path(
                text="Small",
                font_families=["Arial"],
                font_size=size
            )

            assert result.character_count == 5
            assert result.metadata['font_size'] == size

    def test_very_large_font_sizes(self):
        """Test with very large font sizes."""
        service = create_path_generation_service()

        large_sizes = [72.0, 144.0, 288.0]

        for size in large_sizes:
            result = service.generate_text_path(
                text="Large",
                font_families=["Arial"],
                font_size=size
            )

            assert result.character_count == 5
            assert result.metadata['font_size'] == size

    def test_very_long_text(self):
        """Test with very long text strings."""
        service = create_path_generation_service()

        # 100 character string
        long_text = "A" * 100

        result = service.generate_text_path(
            text=long_text,
            font_families=["Arial"],
            font_size=12.0
        )

        assert result.character_count == 100
        assert result.drawingml_path is not None

    def test_mixed_character_types(self):
        """Test with mixed character types."""
        service = create_path_generation_service()

        mixed_text = "Aa1!@# 你好🌟"

        result = service.generate_text_path(
            text=mixed_text,
            font_families=["Arial"],
            font_size=12.0
        )

        assert result.character_count == len(mixed_text)
        assert result.drawingml_path is not None

    def test_negative_coordinates(self):
        """Test with negative coordinate offsets."""
        service = create_path_generation_service()

        result = service.generate_text_path(
            text="Negative",
            font_families=["Arial"],
            font_size=12.0,
            x=-50.0,
            y=-25.0
        )

        assert result.character_count == len("Negative")
        assert result.drawingml_path is not None

    def test_zero_width_characters(self):
        """Test handling of zero-width characters."""
        service = create_path_generation_service()

        # Test with combining characters or zero-width characters
        text_with_zwj = "A\u200dB"  # Zero-width joiner

        result = service.generate_text_path(
            text=text_with_zwj,
            font_families=["Arial"],
            font_size=12.0
        )

        assert result.character_count == len(text_with_zwj)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])