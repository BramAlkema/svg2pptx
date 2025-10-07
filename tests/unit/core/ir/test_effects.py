#!/usr/bin/env python3
"""Unit tests for DrawingML Effect IR"""

import pytest
from core.ir.effects import (
    Effect,
    BlurEffect,
    ShadowEffect,
    GlowEffect,
    SoftEdgeEffect,
    ReflectionEffect,
)


class TestBlurEffect:
    """Tests for BlurEffect"""

    def test_blur_effect_creation(self):
        """Test creating BlurEffect"""
        blur = BlurEffect(radius=5.0)
        assert blur.radius == 5.0

    def test_blur_to_emu(self):
        """Test EMU conversion for blur"""
        blur = BlurEffect(radius=5.0)
        assert blur.to_emu() == 63500  # 5.0 * 12700

    def test_blur_zero_radius(self):
        """Test blur with zero radius"""
        blur = BlurEffect(radius=0.0)
        assert blur.to_emu() == 0

    def test_blur_large_radius(self):
        """Test blur with large radius"""
        blur = BlurEffect(radius=100.0)
        assert blur.to_emu() == 1270000

    def test_blur_fractional_radius(self):
        """Test blur with fractional radius"""
        blur = BlurEffect(radius=2.5)
        assert blur.to_emu() == 31750

    def test_blur_is_frozen(self):
        """Test that BlurEffect is immutable"""
        blur = BlurEffect(radius=5.0)
        with pytest.raises(AttributeError):
            blur.radius = 10.0


class TestShadowEffect:
    """Tests for ShadowEffect"""

    def test_shadow_effect_creation(self):
        """Test creating ShadowEffect"""
        shadow = ShadowEffect(
            blur_radius=3.0,
            distance=2.0,
            angle=45.0
        )
        assert shadow.blur_radius == 3.0
        assert shadow.distance == 2.0
        assert shadow.angle == 45.0
        assert shadow.color == "000000"  # default
        assert shadow.alpha == 0.5  # default

    def test_shadow_with_custom_color_alpha(self):
        """Test shadow with custom color and alpha"""
        shadow = ShadowEffect(
            blur_radius=1.0,
            distance=1.0,
            angle=0.0,
            color="FF0000",
            alpha=0.75
        )
        assert shadow.color == "FF0000"
        assert shadow.alpha == 0.75

    def test_shadow_to_emu(self):
        """Test EMU conversion for shadow"""
        shadow = ShadowEffect(blur_radius=3.0, distance=2.0, angle=0)
        blur_emu, dist_emu = shadow.to_emu()
        assert blur_emu == 38100  # 3.0 * 12700
        assert dist_emu == 25400  # 2.0 * 12700

    def test_shadow_to_direction_emu(self):
        """Test direction conversion to EMU"""
        # 0° = right
        shadow = ShadowEffect(blur_radius=1, distance=1, angle=0)
        assert shadow.to_direction_emu() == 0

        # 45°
        shadow = ShadowEffect(blur_radius=1, distance=1, angle=45)
        assert shadow.to_direction_emu() == 2700000  # 45 * 60000

        # 90° = down
        shadow = ShadowEffect(blur_radius=1, distance=1, angle=90)
        assert shadow.to_direction_emu() == 5400000  # 90 * 60000

        # 180°
        shadow = ShadowEffect(blur_radius=1, distance=1, angle=180)
        assert shadow.to_direction_emu() == 10800000  # 180 * 60000

    def test_shadow_angle_wrapping(self):
        """Test that angle wraps around 360°"""
        shadow = ShadowEffect(blur_radius=1, distance=1, angle=370)
        # 370° wraps to 10°
        assert shadow.to_direction_emu() == 600000  # 10 * 60000

        shadow = ShadowEffect(blur_radius=1, distance=1, angle=720)
        # 720° wraps to 0°
        assert shadow.to_direction_emu() == 0

    def test_shadow_to_alpha_val(self):
        """Test alpha conversion to DrawingML value"""
        shadow = ShadowEffect(blur_radius=1, distance=1, angle=0, alpha=0.5)
        assert shadow.to_alpha_val() == 50000  # 0.5 * 100000

        shadow = ShadowEffect(blur_radius=1, distance=1, angle=0, alpha=0.0)
        assert shadow.to_alpha_val() == 0

        shadow = ShadowEffect(blur_radius=1, distance=1, angle=0, alpha=1.0)
        assert shadow.to_alpha_val() == 100000

        shadow = ShadowEffect(blur_radius=1, distance=1, angle=0, alpha=0.25)
        assert shadow.to_alpha_val() == 25000


class TestGlowEffect:
    """Tests for GlowEffect"""

    def test_glow_effect_creation(self):
        """Test creating GlowEffect"""
        glow = GlowEffect(radius=5.0)
        assert glow.radius == 5.0
        assert glow.color == "FFFFFF"  # default white

    def test_glow_with_custom_color(self):
        """Test glow with custom color"""
        glow = GlowEffect(radius=3.0, color="00FF00")
        assert glow.color == "00FF00"

    def test_glow_to_emu(self):
        """Test EMU conversion for glow"""
        glow = GlowEffect(radius=5.0)
        assert glow.to_emu() == 63500  # 5.0 * 12700

    def test_glow_zero_radius(self):
        """Test glow with zero radius"""
        glow = GlowEffect(radius=0.0)
        assert glow.to_emu() == 0


class TestSoftEdgeEffect:
    """Tests for SoftEdgeEffect"""

    def test_soft_edge_creation(self):
        """Test creating SoftEdgeEffect"""
        soft = SoftEdgeEffect(radius=2.5)
        assert soft.radius == 2.5

    def test_soft_edge_to_emu(self):
        """Test EMU conversion for soft edge"""
        soft = SoftEdgeEffect(radius=2.5)
        assert soft.to_emu() == 31750  # 2.5 * 12700

    def test_soft_edge_large_radius(self):
        """Test soft edge with large radius"""
        soft = SoftEdgeEffect(radius=10.0)
        assert soft.to_emu() == 127000


class TestReflectionEffect:
    """Tests for ReflectionEffect"""

    def test_reflection_creation_defaults(self):
        """Test creating ReflectionEffect with defaults"""
        refl = ReflectionEffect()
        assert refl.blur_radius == 3.0
        assert refl.start_alpha == 0.5
        assert refl.end_alpha == 0.0
        assert refl.distance == 0.0

    def test_reflection_creation_custom(self):
        """Test creating ReflectionEffect with custom values"""
        refl = ReflectionEffect(
            blur_radius=5.0,
            start_alpha=0.8,
            end_alpha=0.2,
            distance=10.0
        )
        assert refl.blur_radius == 5.0
        assert refl.start_alpha == 0.8
        assert refl.end_alpha == 0.2
        assert refl.distance == 10.0

    def test_reflection_to_emu(self):
        """Test EMU conversion for reflection"""
        refl = ReflectionEffect(blur_radius=3.0, distance=1.0)
        blur_emu, dist_emu = refl.to_emu()
        assert blur_emu == 38100  # 3.0 * 12700
        assert dist_emu == 12700  # 1.0 * 12700

    def test_reflection_to_alpha_vals(self):
        """Test alpha conversion for reflection"""
        refl = ReflectionEffect(start_alpha=0.5, end_alpha=0.0)
        start_a, end_a = refl.to_alpha_vals()
        assert start_a == 50000  # 0.5 * 100000
        assert end_a == 0  # 0.0 * 100000

        refl = ReflectionEffect(start_alpha=0.75, end_alpha=0.25)
        start_a, end_a = refl.to_alpha_vals()
        assert start_a == 75000
        assert end_a == 25000


class TestEffectInheritance:
    """Tests for Effect base class and inheritance"""

    def test_all_effects_inherit_from_effect(self):
        """Test that all effect types inherit from Effect"""
        assert issubclass(BlurEffect, Effect)
        assert issubclass(ShadowEffect, Effect)
        assert issubclass(GlowEffect, Effect)
        assert issubclass(SoftEdgeEffect, Effect)
        assert issubclass(ReflectionEffect, Effect)

    def test_effect_instances_are_effects(self):
        """Test that effect instances are Effect types"""
        blur = BlurEffect(radius=5.0)
        shadow = ShadowEffect(blur_radius=1, distance=1, angle=0)
        glow = GlowEffect(radius=2.0)
        soft = SoftEdgeEffect(radius=1.0)
        refl = ReflectionEffect()

        assert isinstance(blur, Effect)
        assert isinstance(shadow, Effect)
        assert isinstance(glow, Effect)
        assert isinstance(soft, Effect)
        assert isinstance(refl, Effect)


class TestEMUConversionConstants:
    """Tests to verify EMU conversion constant across all effects"""

    @pytest.mark.parametrize("points,expected_emu", [
        (0.0, 0),
        (1.0, 12700),
        (2.0, 25400),
        (5.0, 63500),
        (10.0, 127000),
        (100.0, 1270000),
    ])
    def test_blur_emu_conversions(self, points, expected_emu):
        """Test blur EMU conversions with various values"""
        blur = BlurEffect(radius=points)
        assert blur.to_emu() == expected_emu

    @pytest.mark.parametrize("points,expected_emu", [
        (0.0, 0),
        (1.0, 12700),
        (5.0, 63500),
    ])
    def test_glow_emu_conversions(self, points, expected_emu):
        """Test glow EMU conversions"""
        glow = GlowEffect(radius=points)
        assert glow.to_emu() == expected_emu

    @pytest.mark.parametrize("points,expected_emu", [
        (0.0, 0),
        (1.0, 12700),
        (2.5, 31750),
    ])
    def test_soft_edge_emu_conversions(self, points, expected_emu):
        """Test soft edge EMU conversions"""
        soft = SoftEdgeEffect(radius=points)
        assert soft.to_emu() == expected_emu
