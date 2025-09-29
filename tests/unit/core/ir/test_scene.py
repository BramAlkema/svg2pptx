#!/usr/bin/env python3
"""
Unit tests for core IR Scene component.

Tests the Scene data structure which represents the top-level SVG scene graph
in the clean slate architecture.
"""

import pytest
from unittest.mock import Mock, patch
from typing import List, Optional, Union

from tests.unit.core.conftest import IRTestBase

try:
    from core.ir import Scene, Path, TextFrame, Group, Image
    from core.ir import Point, Rect, LineSegment, SolidPaint, Stroke
    from core.ir import validate_ir, IRValidationError
    CORE_IR_AVAILABLE = True
except ImportError:
    CORE_IR_AVAILABLE = False
    pytest.skip("Core IR components not available", allow_module_level=True)


class TestSceneCreation(IRTestBase):
    """Test Scene object creation and basic properties."""

    def test_empty_scene_creation(self):
        """Test creating an empty scene."""
        scene = Scene(
            elements=[],
            viewbox=(0, 0, 100, 100),
            width=100,
            height=100
        )

        assert scene.elements == []
        assert scene.viewbox == (0, 0, 100, 100)
        assert scene.width == 100
        assert scene.height == 100
        self.assert_valid_ir_element(scene)

    def test_scene_with_elements(self, sample_path, sample_textframe):
        """Test creating a scene with elements."""
        elements = [sample_path, sample_textframe]
        scene = Scene(
            elements=elements,
            viewbox=(0, 0, 200, 200),
            width=200,
            height=200
        )

        assert len(scene.elements) == 2
        assert scene.elements[0] == sample_path
        assert scene.elements[1] == sample_textframe
        self.assert_valid_ir_element(scene)

    def test_scene_with_optional_properties(self):
        """Test scene with optional properties like background color."""
        scene = Scene(
            elements=[],
            viewbox=(0, 0, 100, 100),
            width=100,
            height=100,
            background_color="ffffff"
        )

        assert scene.background_color == "ffffff"
        self.assert_valid_ir_element(scene)

    def test_scene_viewbox_validation(self):
        """Test that scene viewbox must be a 4-tuple."""
        with pytest.raises((ValueError, TypeError)):
            Scene(
                elements=[],
                viewbox=(0, 0, 100),  # Invalid - only 3 values
                width=100,
                height=100
            )

    def test_scene_negative_dimensions(self):
        """Test handling of negative width/height."""
        with pytest.raises(ValueError):
            Scene(
                elements=[],
                viewbox=(0, 0, 100, 100),
                width=-10,  # Invalid negative width
                height=100
            )


class TestSceneElementManagement(IRTestBase):
    """Test Scene element management and manipulation."""

    def test_scene_element_types(self, sample_path, sample_textframe, sample_group, sample_image):
        """Test that scene can contain all supported element types."""
        elements = [sample_path, sample_textframe, sample_group, sample_image]
        scene = Scene(
            elements=elements,
            viewbox=(0, 0, 200, 200),
            width=200,
            height=200
        )

        assert len(scene.elements) == 4

        # Verify element types
        assert isinstance(scene.elements[0], Path)
        assert isinstance(scene.elements[1], TextFrame)
        assert isinstance(scene.elements[2], Group)
        assert isinstance(scene.elements[3], Image)

        self.assert_valid_ir_element(scene)

    def test_scene_empty_elements_list(self):
        """Test scene with empty elements list."""
        scene = Scene(
            elements=[],
            viewbox=(0, 0, 100, 100),
            width=100,
            height=100
        )

        assert scene.elements == []
        assert len(scene.elements) == 0
        self.assert_valid_ir_element(scene)

    def test_scene_element_immutability(self, sample_path):
        """Test that scene elements are immutable after creation."""
        original_elements = [sample_path]
        scene = Scene(
            elements=original_elements,
            viewbox=(0, 0, 100, 100),
            width=100,
            height=100
        )

        # Try to modify the elements list (should not affect scene)
        original_elements.append(Mock())

        # Scene should still have only the original element
        assert len(scene.elements) == 1
        assert scene.elements[0] == sample_path

    def test_large_scene_performance(self):
        """Test performance with large number of elements."""
        # Create many simple path elements
        elements = []
        for i in range(1000):
            path = Path(
                segments=[LineSegment(Point(i, 0), Point(i+1, 0))],
                fill=SolidPaint(color="ff0000"),
                stroke=None,
                is_closed=False,
                data=f"M {i} 0 L {i+1} 0"
            )
            elements.append(path)

        import time
        start_time = time.time()

        scene = Scene(
            elements=elements,
            viewbox=(0, 0, 1000, 100),
            width=1000,
            height=100
        )

        creation_time = time.time() - start_time

        assert len(scene.elements) == 1000
        assert creation_time < 1.0  # Should create quickly
        self.assert_valid_ir_element(scene)


class TestSceneCoordinateSystem(IRTestBase):
    """Test Scene coordinate system and viewport handling."""

    def test_scene_coordinate_scaling(self):
        """Test coordinate scaling based on viewbox vs actual dimensions."""
        # Viewbox is 100x100, but actual size is 200x200 (2x scale)
        scene = Scene(
            elements=[],
            viewbox=(0, 0, 100, 100),
            width=200,
            height=200
        )

        # Calculate scale factors
        viewbox_width = scene.viewbox[2] - scene.viewbox[0]
        viewbox_height = scene.viewbox[3] - scene.viewbox[1]

        scale_x = scene.width / viewbox_width
        scale_y = scene.height / viewbox_height

        assert scale_x == 2.0
        assert scale_y == 2.0

    def test_scene_coordinate_offset(self):
        """Test coordinate offset with non-zero viewbox origin."""
        scene = Scene(
            elements=[],
            viewbox=(50, 50, 150, 150),  # 100x100 area starting at (50,50)
            width=100,
            height=100
        )

        viewbox_x = scene.viewbox[0]
        viewbox_y = scene.viewbox[1]

        assert viewbox_x == 50
        assert viewbox_y == 50

    def test_scene_aspect_ratio_preservation(self):
        """Test aspect ratio calculations."""
        # Different aspect ratios
        square_scene = Scene(
            elements=[],
            viewbox=(0, 0, 100, 100),
            width=100,
            height=100
        )

        wide_scene = Scene(
            elements=[],
            viewbox=(0, 0, 200, 100),
            width=200,
            height=100
        )

        tall_scene = Scene(
            elements=[],
            viewbox=(0, 0, 100, 200),
            width=100,
            height=200
        )

        # Calculate aspect ratios
        square_ratio = square_scene.width / square_scene.height
        wide_ratio = wide_scene.width / wide_scene.height
        tall_ratio = tall_scene.width / tall_scene.height

        assert square_ratio == 1.0
        assert wide_ratio == 2.0
        assert tall_ratio == 0.5


class TestSceneValidation(IRTestBase):
    """Test Scene validation and error handling."""

    def test_scene_validation_success(self, sample_ir_scene):
        """Test that valid scenes pass validation."""
        # Should not raise any exceptions
        self.assert_valid_ir_element(sample_ir_scene)

        # Additional validation checks
        assert hasattr(sample_ir_scene, 'elements')
        assert hasattr(sample_ir_scene, 'viewbox')
        assert hasattr(sample_ir_scene, 'width')
        assert hasattr(sample_ir_scene, 'height')

    def test_scene_validation_invalid_elements(self):
        """Test validation with invalid elements."""
        # Create scene with invalid element (not a proper IR element)
        invalid_element = Mock()  # Not a real IR element

        with pytest.raises((IRValidationError, TypeError, AttributeError)):
            scene = Scene(
                elements=[invalid_element],
                viewbox=(0, 0, 100, 100),
                width=100,
                height=100
            )
            self.assert_valid_ir_element(scene)

    def test_scene_validation_dimensions_mismatch(self):
        """Test validation when dimensions don't match viewbox."""
        # This might be allowed but should be noted
        scene = Scene(
            elements=[],
            viewbox=(0, 0, 100, 100),  # 100x100 viewbox
            width=200,  # Different actual size
            height=150
        )

        # Should still be valid (scaling is allowed)
        self.assert_valid_ir_element(scene)

    def test_scene_validation_edge_cases(self):
        """Test validation with edge case values."""
        # Very small scene
        tiny_scene = Scene(
            elements=[],
            viewbox=(0, 0, 1, 1),
            width=1,
            height=1
        )
        self.assert_valid_ir_element(tiny_scene)

        # Very large scene
        huge_scene = Scene(
            elements=[],
            viewbox=(0, 0, 10000, 10000),
            width=10000,
            height=10000
        )
        self.assert_valid_ir_element(huge_scene)


class TestSceneSerialization(IRTestBase):
    """Test Scene serialization and data exchange."""

    def test_scene_dict_representation(self, sample_ir_scene):
        """Test converting scene to dictionary representation."""
        # Check if scene can be converted to dict (for JSON serialization)
        scene_dict = {}
        try:
            import dataclasses
            if dataclasses.is_dataclass(sample_ir_scene):
                scene_dict = dataclasses.asdict(sample_ir_scene)
        except (ImportError, TypeError):
            # Fallback for non-dataclass implementation
            scene_dict = {
                'elements': sample_ir_scene.elements,
                'viewbox': sample_ir_scene.viewbox,
                'width': sample_ir_scene.width,
                'height': sample_ir_scene.height
            }

        assert 'elements' in scene_dict
        assert 'viewbox' in scene_dict
        assert 'width' in scene_dict
        assert 'height' in scene_dict

    def test_scene_equality_comparison(self):
        """Test scene equality comparison."""
        scene1 = Scene(
            elements=[],
            viewbox=(0, 0, 100, 100),
            width=100,
            height=100
        )

        scene2 = Scene(
            elements=[],
            viewbox=(0, 0, 100, 100),
            width=100,
            height=100
        )

        scene3 = Scene(
            elements=[],
            viewbox=(0, 0, 200, 200),  # Different viewbox
            width=100,
            height=100
        )

        # Test equality
        assert scene1 == scene2
        assert scene1 != scene3

    def test_scene_copy_behavior(self, sample_ir_scene):
        """Test scene copying behavior."""
        import copy

        # Shallow copy
        scene_copy = copy.copy(sample_ir_scene)
        assert scene_copy == sample_ir_scene
        assert scene_copy is not sample_ir_scene

        # Deep copy
        scene_deep_copy = copy.deepcopy(sample_ir_scene)
        assert scene_deep_copy == sample_ir_scene
        assert scene_deep_copy is not sample_ir_scene


class TestSceneIntegration(IRTestBase):
    """Test Scene integration with other IR components."""

    def test_scene_with_complex_elements(self):
        """Test scene containing complex nested elements."""
        # Create a complex nested structure
        inner_path = Path(
            segments=[LineSegment(Point(0, 0), Point(10, 10))],
            fill=SolidPaint(color="ff0000"),
            stroke=None,
            is_closed=False,
            data="M 0 0 L 10 10"
        )

        group = Group(
            children=[inner_path],
            transform="translate(20, 30) rotate(45)",
            clip_id=None
        )

        scene = Scene(
            elements=[group],
            viewbox=(0, 0, 100, 100),
            width=100,
            height=100
        )

        assert len(scene.elements) == 1
        assert isinstance(scene.elements[0], Group)
        assert len(scene.elements[0].children) == 1
        self.assert_valid_ir_element(scene)

    def test_scene_rendering_context(self):
        """Test that scene provides proper rendering context."""
        scene = Scene(
            elements=[],
            viewbox=(10, 20, 110, 120),  # 100x100 area with offset
            width=200,
            height=200
        )

        # Calculate rendering parameters
        viewbox_x, viewbox_y, viewbox_w, viewbox_h = scene.viewbox

        # Transform matrix calculation
        scale_x = scene.width / (viewbox_w - viewbox_x)
        scale_y = scene.height / (viewbox_h - viewbox_y)
        translate_x = -viewbox_x * scale_x
        translate_y = -viewbox_y * scale_y

        # Verify calculations make sense
        assert scale_x == 2.0  # 200/100
        assert scale_y == 2.0  # 200/100
        assert translate_x == -20.0  # -10 * 2
        assert translate_y == -40.0  # -20 * 2


# Performance and stress tests
class TestScenePerformance(IRTestBase):
    """Test Scene performance characteristics."""

    def test_scene_memory_usage(self):
        """Test scene memory usage with many elements."""
        import sys

        # Create scene with many elements
        elements = []
        for i in range(100):
            path = Path(
                segments=[LineSegment(Point(i, 0), Point(i+1, 0))],
                fill=SolidPaint(color="ff0000"),
                stroke=None,
                is_closed=False,
                data=f"M {i} 0 L {i+1} 0"
            )
            elements.append(path)

        scene = Scene(
            elements=elements,
            viewbox=(0, 0, 100, 100),
            width=100,
            height=100
        )

        # Check memory usage is reasonable
        scene_size = sys.getsizeof(scene)
        assert scene_size < 10000  # Arbitrary reasonable limit

    def test_scene_creation_performance(self):
        """Test scene creation performance."""
        import time

        elements = []
        for i in range(50):
            path = Path(
                segments=[LineSegment(Point(i, 0), Point(i+1, 0))],
                fill=SolidPaint(color="ff0000"),
                stroke=None,
                is_closed=False,
                data=f"M {i} 0 L {i+1} 0"
            )
            elements.append(path)

        # Time scene creation
        start_time = time.time()

        for _ in range(100):
            scene = Scene(
                elements=elements,
                viewbox=(0, 0, 100, 100),
                width=100,
                height=100
            )

        total_time = time.time() - start_time

        # Should create 100 scenes quickly
        assert total_time < 1.0
        assert scene  # Ensure last scene was created successfully


if __name__ == "__main__":
    pytest.main([__file__])