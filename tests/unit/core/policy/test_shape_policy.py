#!/usr/bin/env python3
"""
Unit tests for shape policy engine

Tests ShapeDecision dataclass and decide_shape_strategy function with focus on:
- Simple shapes qualifying for native presets
- Complex features disqualifying shapes (transforms, filters, clipping)
- Transform complexity detection (rotation, skew vs translate/scale)
- Correct preset name mapping (ellipse, rect, roundRect)
"""

import pytest
import numpy as np
from unittest.mock import Mock

from core.policy.shape_policy import ShapeDecision, decide_shape_strategy, _is_simple_transform
from core.policy.targets import DecisionReason
from core.ir.shapes import Circle, Ellipse, Rectangle
from core.ir.geometry import Point, Rect


class TestShapeDecision:
    """Tests for ShapeDecision dataclass"""

    def test_preset_factory_method(self):
        """Test ShapeDecision.preset() creates correct decision"""
        decision = ShapeDecision.preset(
            'circle',
            'ellipse',
            [DecisionReason.SIMPLE_GEOMETRY],
        )

        assert decision.use_native is True
        assert decision.use_preset is True
        assert decision.shape_type == 'circle'
        assert decision.preset_name == 'ellipse'
        assert DecisionReason.SIMPLE_GEOMETRY in decision.reasons

    def test_custom_geometry_factory_method(self):
        """Test ShapeDecision.custom_geometry() creates fallback decision"""
        decision = ShapeDecision.custom_geometry(
            'circle',
            [DecisionReason.UNSUPPORTED_FEATURES],
            has_filters=True,
            complexity_score=10,
        )

        assert decision.use_native is True
        assert decision.use_preset is False
        assert decision.shape_type == 'circle'
        assert decision.preset_name is None
        assert decision.has_filters is True
        assert decision.complexity_score == 10

    def test_to_dict_serialization(self):
        """Test to_dict() serializes all decision metadata"""
        decision = ShapeDecision.custom_geometry(
            'ellipse',
            [DecisionReason.UNSUPPORTED_FEATURES],
            has_filters=True,
            complexity_score=20,
        )

        result = decision.to_dict()

        assert result['use_native'] is True
        assert result['use_preset'] is False
        assert result['shape_type'] == 'ellipse'
        assert result['preset_name'] is None
        assert result['complexity_score'] == 20
        assert result['has_filters'] is True
        assert 'unsupported_features' in result['reasons']


class TestDecideShapeStrategy:
    """Tests for decide_shape_strategy decision logic"""

    def test_simple_circle_uses_preset(self):
        """Test simple circle qualifies for native ellipse preset"""
        circle = Circle(center=Point(100, 50), radius=25.0)

        decision = decide_shape_strategy(circle)

        assert decision.use_preset is True
        assert decision.preset_name == 'ellipse'
        assert decision.shape_type == 'circle'
        assert DecisionReason.NATIVE_PRESET_AVAILABLE in decision.reasons
        assert DecisionReason.SIMPLE_GEOMETRY in decision.reasons

    def test_simple_ellipse_uses_preset(self):
        """Test simple ellipse qualifies for native preset"""
        ellipse = Ellipse(center=Point(200, 200), radius_x=60.0, radius_y=30.0)

        decision = decide_shape_strategy(ellipse)

        assert decision.use_preset is True
        assert decision.preset_name == 'ellipse'
        assert decision.shape_type == 'ellipse'

    def test_simple_rectangle_uses_rect_preset(self):
        """Test simple rectangle uses rect preset"""
        rect = Rectangle(bounds=Rect(x=50, y=50, width=100, height=80))

        decision = decide_shape_strategy(rect)

        assert decision.use_preset is True
        assert decision.preset_name == 'rect'
        assert decision.shape_type == 'rectangle'

    def test_rounded_rectangle_uses_roundrect_preset(self):
        """Test rectangle with corner_radius uses roundRect preset"""
        rect = Rectangle(
            bounds=Rect(x=0, y=0, width=100, height=100),
            corner_radius=10.0,
        )

        decision = decide_shape_strategy(rect)

        assert decision.use_preset is True
        assert decision.preset_name == 'roundRect'
        assert decision.shape_type == 'rectangle'

    def test_circle_with_filters_uses_custom_geometry(self):
        """Test circle with filters falls back to custom geometry"""
        circle = Circle(center=Point(0, 0), radius=10.0)

        # Mock context with filters
        context = Mock()
        context.filters = ['blur', 'drop-shadow']
        context.clip = None

        decision = decide_shape_strategy(circle, context)

        assert decision.use_preset is False
        assert decision.has_filters is True
        assert DecisionReason.UNSUPPORTED_FEATURES in decision.reasons
        assert decision.complexity_score > 0

    def test_ellipse_with_clipping_uses_custom_geometry(self):
        """Test ellipse with clipping path falls back to custom geometry"""
        ellipse = Ellipse(center=Point(0, 0), radius_x=10.0, radius_y=5.0)

        # Mock context with clipping
        context = Mock()
        context.filters = None
        context.clip = Mock()  # Has clipping

        decision = decide_shape_strategy(ellipse, context)

        assert decision.use_preset is False
        assert decision.has_clipping is True
        assert DecisionReason.CLIPPING_COMPLEX in decision.reasons

    @pytest.mark.skip(reason="Phase 2: Transforms are baked during parsing - shapes never have transform fields")
    def test_rectangle_with_rotation_uses_custom_geometry(self):
        """Test rectangle with rotation transform uses custom geometry"""
        # 45-degree rotation matrix
        angle = np.pi / 4  # 45 degrees
        rotation = np.array([
            [np.cos(angle), -np.sin(angle), 0],
            [np.sin(angle), np.cos(angle), 0],
            [0, 0, 1],
        ])

        rect = Rectangle(
            bounds=Rect(x=0, y=0, width=100, height=100),
            transform=rotation,
        )

        decision = decide_shape_strategy(rect)

        assert decision.use_preset is False
        assert decision.has_complex_transform is True
        assert DecisionReason.COMPLEX_TRANSFORM in decision.reasons

    @pytest.mark.skip(reason="Phase 2: Transforms are baked during parsing - shapes never have transform fields")
    def test_circle_with_skew_uses_custom_geometry(self):
        """Test circle with skew transform uses custom geometry"""
        # Skew matrix (shear in x direction)
        skew = np.array([
            [1, 0.5, 0],  # Skew factor 0.5
            [0, 1, 0],
            [0, 0, 1],
        ])

        circle = Circle(
            center=Point(0, 0),
            radius=10.0,
            transform=skew,
        )

        decision = decide_shape_strategy(circle)

        assert decision.use_preset is False
        assert decision.has_complex_transform is True

    @pytest.mark.skip(reason="Phase 2: Transforms are baked during parsing - shapes never have transform fields")
    def test_shape_with_translate_uses_preset(self):
        """Test shape with translation only qualifies for preset"""
        # Pure translation matrix
        translate = np.array([
            [1, 0, 50],  # Translate x by 50
            [0, 1, 100],  # Translate y by 100
            [0, 0, 1],
        ])

        circle = Circle(
            center=Point(0, 0),
            radius=10.0,
            transform=translate,
        )

        decision = decide_shape_strategy(circle)

        assert decision.use_preset is True  # Translation is OK for native shapes

    @pytest.mark.skip(reason="Phase 2: Transforms are baked during parsing - shapes never have transform fields")
    def test_shape_with_scale_uses_preset(self):
        """Test shape with uniform scale qualifies for preset"""
        # Uniform scale matrix
        scale = np.array([
            [2, 0, 0],  # Scale x by 2
            [0, 2, 0],  # Scale y by 2
            [0, 0, 1],
        ])

        ellipse = Ellipse(
            center=Point(0, 0),
            radius_x=10.0,
            radius_y=5.0,
            transform=scale,
        )

        decision = decide_shape_strategy(ellipse)

        assert decision.use_preset is True  # Scaling is OK for native shapes

    def test_no_transform_uses_preset(self):
        """Test shape without transform qualifies for preset - Phase 2: all shapes have no transform"""
        circle = Circle(center=Point(0, 0), radius=10.0)

        decision = decide_shape_strategy(circle)

        assert decision.use_preset is True


@pytest.mark.skip(reason="Phase 2: _is_simple_transform() deprecated - all transforms baked during parsing")
class TestTransformDetection:
    """Tests for _is_simple_transform helper function - OBSOLETE in Phase 2"""

    def test_identity_matrix_is_simple(self):
        """Test identity matrix (no transform) is simple"""
        identity = np.eye(3)
        assert _is_simple_transform(identity) is True

    def test_translation_is_simple(self):
        """Test pure translation is simple"""
        translate = np.array([
            [1, 0, 100],
            [0, 1, 200],
            [0, 0, 1],
        ])
        assert _is_simple_transform(translate) is True

    def test_scale_is_simple(self):
        """Test scaling (uniform or non-uniform) is simple"""
        scale = np.array([
            [2, 0, 0],
            [0, 3, 0],
            [0, 0, 1],
        ])
        assert _is_simple_transform(scale) is True

    def test_translate_and_scale_is_simple(self):
        """Test combined translate+scale is simple"""
        transform = np.array([
            [2, 0, 50],
            [0, 2, 100],
            [0, 0, 1],
        ])
        assert _is_simple_transform(transform) is True

    def test_rotation_is_complex(self):
        """Test rotation is complex"""
        angle = np.pi / 6  # 30 degrees
        rotation = np.array([
            [np.cos(angle), -np.sin(angle), 0],
            [np.sin(angle), np.cos(angle), 0],
            [0, 0, 1],
        ])
        assert _is_simple_transform(rotation) is False

    def test_skew_x_is_complex(self):
        """Test horizontal skew is complex"""
        skew = np.array([
            [1, 0.5, 0],  # Skew in x
            [0, 1, 0],
            [0, 0, 1],
        ])
        assert _is_simple_transform(skew) is False

    def test_skew_y_is_complex(self):
        """Test vertical skew is complex"""
        skew = np.array([
            [1, 0, 0],
            [0.3, 1, 0],  # Skew in y
            [0, 0, 1],
        ])
        assert _is_simple_transform(skew) is False

    def test_very_small_rotation_is_complex(self):
        """Test even tiny rotation is detected as complex"""
        # 1 degree rotation
        angle = np.pi / 180
        rotation = np.array([
            [np.cos(angle), -np.sin(angle), 0],
            [np.sin(angle), np.cos(angle), 0],
            [0, 0, 1],
        ])
        # Should be detected as complex (tolerance is 1e-6)
        # cos(1°) ≈ 0.9998, sin(1°) ≈ 0.0175
        assert _is_simple_transform(rotation) is False

    def test_none_transform_is_simple(self):
        """Test None (no transform) is simple"""
        assert _is_simple_transform(None) is True

    def test_invalid_matrix_shape_is_simple(self):
        """Test invalid matrix shape defaults to simple"""
        # 2x2 matrix instead of 3x3
        invalid = np.array([[1, 0], [0, 1]])
        assert _is_simple_transform(invalid) is True


class TestComplexityScoring:
    """Tests for complexity score calculation"""

    def test_simple_shape_has_zero_complexity(self):
        """Test simple shapes have zero complexity score"""
        circle = Circle(center=Point(0, 0), radius=10.0)
        decision = decide_shape_strategy(circle)

        assert decision.complexity_score == 0

    @pytest.mark.skip(reason="Phase 2: Transforms are baked during parsing - shapes never have transform fields")
    def test_complex_transform_adds_complexity(self):
        """Test complex transform increases complexity score"""
        rotation = np.array([
            [0, -1, 0],  # 90-degree rotation
            [1, 0, 0],
            [0, 0, 1],
        ])

        circle = Circle(center=Point(0, 0), radius=10.0, transform=rotation)
        decision = decide_shape_strategy(circle)

        assert decision.complexity_score > 0

    def test_filters_add_complexity(self):
        """Test filters contribute to complexity score"""
        # Shape with filters
        circle_with_filters = Circle(center=Point(0, 0), radius=10.0)
        context_filters = Mock()
        context_filters.filters = ['blur']
        context_filters.clip = None
        decision_filters = decide_shape_strategy(circle_with_filters, context_filters)

        # Filters should add complexity
        assert decision_filters.complexity_score > 0


class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_context_without_filters_attribute(self):
        """Test context without filters attribute doesn't crash"""
        circle = Circle(center=Point(0, 0), radius=10.0)
        context = Mock(spec=[])  # Empty context

        decision = decide_shape_strategy(circle, context)

        # Should qualify for preset (no filters detected)
        assert decision.use_preset is True

    def test_context_with_none_filters(self):
        """Test context with filters=None doesn't crash"""
        circle = Circle(center=Point(0, 0), radius=10.0)
        context = Mock()
        context.filters = None
        context.clip = None

        decision = decide_shape_strategy(circle, context)

        assert decision.use_preset is True

    def test_context_with_empty_filters_list(self):
        """Test empty filters list is treated as no filters"""
        circle = Circle(center=Point(0, 0), radius=10.0)
        context = Mock()
        context.filters = []  # Empty list = no filters
        context.clip = None

        decision = decide_shape_strategy(circle, context)

        # Empty list is falsy in Python, should qualify for preset
        assert decision.use_preset is True

    def test_no_context_defaults_to_preset(self):
        """Test None context (no filters/clipping) qualifies for preset"""
        circle = Circle(center=Point(0, 0), radius=10.0)

        decision = decide_shape_strategy(circle, context=None)

        assert decision.use_preset is True
