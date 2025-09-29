#!/usr/bin/env python3
"""
Integration tests for Enhanced IR structures.

Tests that EnhancedRun and TextPath components integrate correctly
with the existing IR architecture and validation systems.
"""

import pytest
from core.ir import (
    # Text components
    Run, EnhancedRun, TextAnchor,
    # TextPath components
    TextPathFrame, PathPoint, CharacterPlacement,
    TextPathMethod, TextPathSpacing, TextPathSide,
    create_text_path_frame, create_simple_text_path,
    # Font metadata
    FontMetadata, create_font_metadata,
    # Geometry
    Point
)


class TestEnhancedIRIntegration:
    """Test Enhanced IR components integration."""

    def test_enhanced_run_creation(self):
        """Test EnhancedRun creation and properties."""
        font_metadata = create_font_metadata("Arial", size_pt=12.0)

        enhanced_run = EnhancedRun(
            text="Hello World",
            font_family="Arial",
            font_size_pt=12.0,
            font_metadata=font_metadata,
            text_decorations=["underline"],
            letter_spacing=1.2
        )

        assert enhanced_run.text == "Hello World"
        assert enhanced_run.font_metadata == font_metadata
        assert enhanced_run.has_decoration is True
        assert enhanced_run.effective_font_family == "Arial"
        assert enhanced_run.is_transformed is False

    def test_enhanced_run_backward_compatibility(self):
        """Test EnhancedRun backward compatibility with Run."""
        basic_run = Run(
            text="Test",
            font_family="Arial",
            font_size_pt=14.0,
            bold=True
        )

        # Convert to enhanced
        enhanced_run = EnhancedRun.from_basic_run(basic_run)
        assert enhanced_run.text == "Test"
        assert enhanced_run.bold is True

        # Convert back to basic
        converted_back = enhanced_run.to_basic_run()
        assert converted_back.text == "Test"
        assert converted_back.bold is True
        assert converted_back.font_family == "Arial"

    def test_text_path_frame_creation(self):
        """Test TextPathFrame creation and validation."""
        runs = [Run(text="Curved Text", font_family="Arial", font_size_pt=12.0)]

        text_path = create_text_path_frame(
            runs=runs,
            path_reference="#path1",
            method=TextPathMethod.ALIGN,
            spacing=TextPathSpacing.AUTO
        )

        assert text_path.path_reference == "#path1"
        assert text_path.method == TextPathMethod.ALIGN
        assert text_path.text_content == "Curved Text"
        assert text_path.character_count == 11
        assert text_path.is_positioned is False

    def test_simple_text_path_factory(self):
        """Test simple text path factory function."""
        text_path = create_simple_text_path(
            text="Simple Path Text",
            path_reference="#curve",
            font_family="Helvetica",
            font_size_pt=14.0
        )

        assert text_path.text_content == "Simple Path Text"
        assert text_path.path_reference == "#curve"
        assert len(text_path.runs) == 1
        assert text_path.runs[0].font_family == "Helvetica"
        assert text_path.runs[0].font_size_pt == 14.0

    def test_character_placement_properties(self):
        """Test CharacterPlacement properties and calculations."""
        import math

        path_point = PathPoint(
            x=100.0,
            y=200.0,
            tangent_angle=math.pi / 4,  # 45 degrees
            distance_along_path=50.0
        )

        placement = CharacterPlacement(
            character="A",
            position=path_point,
            run_index=0,
            char_index=0,
            advance_width=8.0,
            rotation=10.0
        )

        assert placement.character == "A"
        assert placement.position.x == 100.0
        assert placement.position.y == 200.0
        assert abs(placement.position.tangent_degrees - 45.0) < 0.01
        assert placement.effective_rotation == 55.0  # 45 + 10

    def test_text_path_positioning(self):
        """Test TextPath with positioning information."""
        runs = [Run(text="ABC", font_family="Arial", font_size_pt=12.0)]

        # Create path points
        path_points = [
            PathPoint(x=0.0, y=0.0, tangent_angle=0.0, distance_along_path=0.0),
            PathPoint(x=10.0, y=0.0, tangent_angle=0.0, distance_along_path=10.0),
            PathPoint(x=20.0, y=0.0, tangent_angle=0.0, distance_along_path=20.0)
        ]

        # Create character placements
        placements = [
            CharacterPlacement("A", path_points[0], 0, 0, 8.0),
            CharacterPlacement("B", path_points[1], 0, 1, 8.0),
            CharacterPlacement("C", path_points[2], 0, 2, 8.0)
        ]

        text_path = create_text_path_frame(runs=runs, path_reference="#path")
        positioned_path = text_path.with_positioning(
            character_placements=placements,
            path_points=path_points,
            total_path_length=30.0
        )

        assert positioned_path.is_positioned is True
        assert positioned_path.total_path_length == 30.0
        assert len(positioned_path.character_placements) == 3
        assert positioned_path.path_coverage == pytest.approx(20.0 / 30.0)

    def test_text_path_complexity_scoring(self):
        """Test TextPath complexity scoring for policy decisions."""
        simple_path = create_simple_text_path(
            text="Hi",
            path_reference="#simple"
        )
        assert simple_path.complexity_score == 4  # Based on actual implementation

        complex_runs = [
            Run(text="Complex", font_family="Arial", font_size_pt=12.0),
            Run(text=" Text", font_family="Times", font_size_pt=14.0)
        ]
        complex_path = TextPathFrame(
            runs=complex_runs,
            path_reference="#complex",
            method=TextPathMethod.STRETCH,
            spacing=TextPathSpacing.EXACT,
            auto_rotate=True
        )

        # 12 chars + 2 runs + 1 (auto_rotate) + 1 (exact spacing) + 1 (stretch)
        assert complex_path.complexity_score == 17

    def test_ir_imports_work(self):
        """Test that all enhanced IR components can be imported."""
        # This test ensures our __init__.py exports work correctly
        from core.ir import (
            EnhancedRun, TextPathFrame, PathPoint, CharacterPlacement,
            TextPathMethod, TextPathSpacing, TextPathSide
        )

        # Basic instantiation test
        assert EnhancedRun is not None
        assert TextPathFrame is not None
        assert PathPoint is not None
        assert CharacterPlacement is not None

        # Enum values
        assert TextPathMethod.ALIGN == "align"
        assert TextPathSpacing.AUTO == "auto"
        assert TextPathSide.LEFT == "left"


if __name__ == "__main__":
    pytest.main([__file__])