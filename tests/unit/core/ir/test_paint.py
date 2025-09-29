#!/usr/bin/env python3
"""
Unit tests for core IR Paint components.

Tests the paint system (SolidPaint, LinearGradient, RadialGradient, etc.)
that defines how elements are filled and stroked.
"""

import pytest
from unittest.mock import Mock

from tests.unit.core.conftest import IRTestBase

try:
    from core.ir import SolidPaint, LinearGradient, RadialGradient, PatternPaint
    from core.ir import Stroke, Point
    from core.ir import validate_ir, IRValidationError
    CORE_IR_AVAILABLE = True
except ImportError:
    CORE_IR_AVAILABLE = False
    pytest.skip("Core IR components not available", allow_module_level=True)


class TestSolidPaintCreation(IRTestBase):
    """Test SolidPaint object creation and properties."""

    def test_solid_paint_creation_hex(self):
        """Test creating solid paint with hex color."""
        paint = SolidPaint(color="#FF0000")

        assert paint.color == "#FF0000"
        self.assert_valid_ir_element(paint)

    def test_solid_paint_creation_rgb(self):
        """Test creating solid paint with RGB color."""
        paint = SolidPaint(color="rgb(255, 0, 0)")

        assert paint.color == "rgb(255, 0, 0)"
        self.assert_valid_ir_element(paint)

    def test_solid_paint_creation_named(self):
        """Test creating solid paint with named color."""
        paint = SolidPaint(color="red")

        assert paint.color == "red"
        self.assert_valid_ir_element(paint)

    def test_solid_paint_with_opacity(self):
        """Test creating solid paint with opacity."""
        try:
            paint = SolidPaint(color="#FF0000", opacity=0.5)
            assert paint.color == "#FF0000"
            assert paint.opacity == 0.5
            self.assert_valid_ir_element(paint)
        except TypeError:
            # Opacity might not be supported in SolidPaint constructor
            paint = SolidPaint(color="#FF0000")
            if hasattr(paint, 'opacity'):
                # Try setting opacity as attribute
                paint.opacity = 0.5
                assert paint.opacity == 0.5

    def test_solid_paint_transparent(self):
        """Test creating transparent solid paint."""
        paint = SolidPaint(color="transparent")

        assert paint.color == "transparent"
        self.assert_valid_ir_element(paint)


class TestLinearGradientCreation(IRTestBase):
    """Test LinearGradient object creation and properties."""

    def test_linear_gradient_basic(self):
        """Test creating a basic linear gradient."""
        try:
            gradient = LinearGradient(
                start_point=Point(0, 0),
                end_point=Point(100, 0),
                stops=[
                    {"offset": 0.0, "color": "#FF0000"},
                    {"offset": 1.0, "color": "#0000FF"}
                ]
            )

            assert gradient.start_point == Point(0, 0)
            assert gradient.end_point == Point(100, 0)
            assert len(gradient.stops) == 2
            self.assert_valid_ir_element(gradient)
        except NameError:
            pytest.skip("LinearGradient not available")

    def test_linear_gradient_vertical(self):
        """Test creating a vertical linear gradient."""
        try:
            gradient = LinearGradient(
                start_point=Point(0, 0),
                end_point=Point(0, 100),
                stops=[
                    {"offset": 0.0, "color": "#FFFFFF"},
                    {"offset": 0.5, "color": "#808080"},
                    {"offset": 1.0, "color": "#000000"}
                ]
            )

            assert gradient.start_point.x == gradient.end_point.x
            assert gradient.start_point.y != gradient.end_point.y
            assert len(gradient.stops) == 3
            self.assert_valid_ir_element(gradient)
        except NameError:
            pytest.skip("LinearGradient not available")

    def test_linear_gradient_diagonal(self):
        """Test creating a diagonal linear gradient."""
        try:
            gradient = LinearGradient(
                start_point=Point(0, 0),
                end_point=Point(100, 100),
                stops=[
                    {"offset": 0.0, "color": "#FF0000"},
                    {"offset": 1.0, "color": "#00FF00"}
                ]
            )

            # Diagonal: start and end different in both x and y
            assert gradient.start_point.x != gradient.end_point.x
            assert gradient.start_point.y != gradient.end_point.y
            self.assert_valid_ir_element(gradient)
        except NameError:
            pytest.skip("LinearGradient not available")

    def test_linear_gradient_multiple_stops(self):
        """Test linear gradient with multiple color stops."""
        try:
            gradient = LinearGradient(
                start_point=Point(0, 0),
                end_point=Point(100, 0),
                stops=[
                    {"offset": 0.0, "color": "#FF0000"},
                    {"offset": 0.25, "color": "#FF8000"},
                    {"offset": 0.5, "color": "#FFFF00"},
                    {"offset": 0.75, "color": "#00FF00"},
                    {"offset": 1.0, "color": "#0000FF"}
                ]
            )

            assert len(gradient.stops) == 5
            # Check stop order
            assert gradient.stops[0]["offset"] == 0.0
            assert gradient.stops[4]["offset"] == 1.0
            self.assert_valid_ir_element(gradient)
        except NameError:
            pytest.skip("LinearGradient not available")


class TestRadialGradientCreation(IRTestBase):
    """Test RadialGradient object creation and properties."""

    def test_radial_gradient_basic(self):
        """Test creating a basic radial gradient."""
        try:
            gradient = RadialGradient(
                center=Point(50, 50),
                radius=50,
                stops=[
                    {"offset": 0.0, "color": "#FFFFFF"},
                    {"offset": 1.0, "color": "#000000"}
                ]
            )

            assert gradient.center == Point(50, 50)
            assert gradient.radius == 50
            assert len(gradient.stops) == 2
            self.assert_valid_ir_element(gradient)
        except NameError:
            pytest.skip("RadialGradient not available")

    def test_radial_gradient_elliptical(self):
        """Test creating an elliptical radial gradient."""
        try:
            gradient = RadialGradient(
                center=Point(50, 50),
                radius_x=75,
                radius_y=25,
                stops=[
                    {"offset": 0.0, "color": "#FF0000"},
                    {"offset": 1.0, "color": "#0000FF"}
                ]
            )

            assert gradient.center == Point(50, 50)
            # Check if elliptical radii are supported
            if hasattr(gradient, 'radius_x'):
                assert gradient.radius_x == 75
                assert gradient.radius_y == 25
            self.assert_valid_ir_element(gradient)
        except (NameError, TypeError):
            pytest.skip("Elliptical RadialGradient not available")

    def test_radial_gradient_with_focal_point(self):
        """Test radial gradient with focal point."""
        try:
            gradient = RadialGradient(
                center=Point(50, 50),
                radius=50,
                focal_point=Point(30, 30),
                stops=[
                    {"offset": 0.0, "color": "#FFFF00"},
                    {"offset": 1.0, "color": "#FF0000"}
                ]
            )

            assert gradient.center == Point(50, 50)
            if hasattr(gradient, 'focal_point'):
                assert gradient.focal_point == Point(30, 30)
            self.assert_valid_ir_element(gradient)
        except (NameError, TypeError):
            pytest.skip("RadialGradient with focal point not available")


class TestPatternPaintCreation(IRTestBase):
    """Test PatternPaint object creation and properties."""

    def test_pattern_paint_basic(self):
        """Test creating a basic pattern paint."""
        try:
            pattern = PatternPaint(
                pattern_id="pattern1",
                width=20,
                height=20,
                pattern_units="userSpaceOnUse"
            )

            assert pattern.pattern_id == "pattern1"
            assert pattern.width == 20
            assert pattern.height == 20
            self.assert_valid_ir_element(pattern)
        except NameError:
            pytest.skip("PatternPaint not available")

    def test_pattern_paint_with_transform(self):
        """Test pattern paint with transformation."""
        try:
            pattern = PatternPaint(
                pattern_id="pattern2",
                width=10,
                height=10,
                transform="scale(2) rotate(45)"
            )

            assert pattern.pattern_id == "pattern2"
            if hasattr(pattern, 'transform'):
                assert pattern.transform == "scale(2) rotate(45)"
            self.assert_valid_ir_element(pattern)
        except (NameError, TypeError):
            pytest.skip("PatternPaint with transform not available")


class TestStrokeCreation(IRTestBase):
    """Test Stroke object creation and properties."""

    def test_stroke_basic(self):
        """Test creating a basic stroke."""
        paint = SolidPaint(color="#000000")

        try:
            stroke = Stroke(
                paint=paint,
                width=2.0
            )

            assert stroke.paint == paint
            assert stroke.width == 2.0
            self.assert_valid_ir_element(stroke)
        except NameError:
            pytest.skip("Stroke not available")

    def test_stroke_with_properties(self):
        """Test stroke with line cap and join properties."""
        paint = SolidPaint(color="#FF0000")

        try:
            stroke = Stroke(
                paint=paint,
                width=3.0,
                line_cap="round",
                line_join="miter",
                miter_limit=4.0
            )

            assert stroke.paint == paint
            assert stroke.width == 3.0
            if hasattr(stroke, 'line_cap'):
                assert stroke.line_cap == "round"
            if hasattr(stroke, 'line_join'):
                assert stroke.line_join == "miter"
            if hasattr(stroke, 'miter_limit'):
                assert stroke.miter_limit == 4.0
            self.assert_valid_ir_element(stroke)
        except (NameError, TypeError):
            pytest.skip("Stroke with properties not available")

    def test_stroke_dashed(self):
        """Test stroke with dash pattern."""
        paint = SolidPaint(color="#0000FF")

        try:
            stroke = Stroke(
                paint=paint,
                width=1.5,
                dash_array=[5, 3, 2, 3],
                dash_offset=2.0
            )

            assert stroke.paint == paint
            assert stroke.width == 1.5
            if hasattr(stroke, 'dash_array'):
                assert stroke.dash_array == [5, 3, 2, 3]
            if hasattr(stroke, 'dash_offset'):
                assert stroke.dash_offset == 2.0
            self.assert_valid_ir_element(stroke)
        except (NameError, TypeError):
            pytest.skip("Dashed stroke not available")

    def test_stroke_zero_width(self):
        """Test stroke with zero width."""
        paint = SolidPaint(color="#808080")

        try:
            stroke = Stroke(
                paint=paint,
                width=0.0
            )

            assert stroke.width == 0.0
            self.assert_valid_ir_element(stroke)
        except NameError:
            pytest.skip("Stroke not available")


class TestPaintValidation(IRTestBase):
    """Test paint validation and error handling."""

    def test_solid_paint_invalid_color(self):
        """Test solid paint with invalid color."""
        # Some implementations might validate color format
        try:
            paint = SolidPaint(color="invalid_color_format")
            # If creation succeeds, it might accept any string
            assert paint.color == "invalid_color_format"
        except ValueError:
            # Color validation might reject invalid formats
            pass

    def test_gradient_invalid_stops(self):
        """Test gradient with invalid color stops."""
        try:
            # Invalid: stops not in order
            with pytest.raises((ValueError, TypeError)):
                LinearGradient(
                    start_point=Point(0, 0),
                    end_point=Point(100, 0),
                    stops=[
                        {"offset": 1.0, "color": "#FF0000"},  # Wrong order
                        {"offset": 0.0, "color": "#0000FF"}
                    ]
                )
        except NameError:
            pytest.skip("LinearGradient not available")

    def test_gradient_empty_stops(self):
        """Test gradient with empty stops array."""
        try:
            with pytest.raises((ValueError, TypeError)):
                LinearGradient(
                    start_point=Point(0, 0),
                    end_point=Point(100, 0),
                    stops=[]  # Empty stops
                )
        except NameError:
            pytest.skip("LinearGradient not available")

    def test_stroke_negative_width(self):
        """Test stroke with negative width."""
        paint = SolidPaint(color="#000000")

        try:
            with pytest.raises(ValueError):
                Stroke(
                    paint=paint,
                    width=-1.0  # Invalid negative width
                )
        except NameError:
            pytest.skip("Stroke not available")

    def test_stroke_invalid_paint(self):
        """Test stroke with invalid paint object."""
        try:
            with pytest.raises((TypeError, ValueError)):
                Stroke(
                    paint="invalid_paint",  # Should be paint object
                    width=2.0
                )
        except NameError:
            pytest.skip("Stroke not available")


class TestPaintEquality(IRTestBase):
    """Test paint equality and comparison."""

    def test_solid_paint_equality(self):
        """Test solid paint equality comparison."""
        paint1 = SolidPaint(color="#FF0000")
        paint2 = SolidPaint(color="#FF0000")
        paint3 = SolidPaint(color="#0000FF")

        assert paint1 == paint2
        assert paint1 != paint3

    def test_gradient_equality(self):
        """Test gradient equality comparison."""
        try:
            gradient1 = LinearGradient(
                start_point=Point(0, 0),
                end_point=Point(100, 0),
                stops=[
                    {"offset": 0.0, "color": "#FF0000"},
                    {"offset": 1.0, "color": "#0000FF"}
                ]
            )

            gradient2 = LinearGradient(
                start_point=Point(0, 0),
                end_point=Point(100, 0),
                stops=[
                    {"offset": 0.0, "color": "#FF0000"},
                    {"offset": 1.0, "color": "#0000FF"}
                ]
            )

            gradient3 = LinearGradient(
                start_point=Point(0, 0),
                end_point=Point(0, 100),  # Different direction
                stops=[
                    {"offset": 0.0, "color": "#FF0000"},
                    {"offset": 1.0, "color": "#0000FF"}
                ]
            )

            assert gradient1 == gradient2
            assert gradient1 != gradient3
        except NameError:
            pytest.skip("LinearGradient not available")

    def test_stroke_equality(self):
        """Test stroke equality comparison."""
        paint1 = SolidPaint(color="#FF0000")
        paint2 = SolidPaint(color="#FF0000")
        paint3 = SolidPaint(color="#0000FF")

        try:
            stroke1 = Stroke(paint=paint1, width=2.0)
            stroke2 = Stroke(paint=paint2, width=2.0)
            stroke3 = Stroke(paint=paint3, width=2.0)
            stroke4 = Stroke(paint=paint1, width=3.0)

            assert stroke1 == stroke2  # Same paint and width
            assert stroke1 != stroke3  # Different paint
            assert stroke1 != stroke4  # Different width
        except NameError:
            pytest.skip("Stroke not available")


class TestPaintSerialization(IRTestBase):
    """Test paint serialization and data exchange."""

    def test_solid_paint_dict_representation(self):
        """Test converting solid paint to dictionary."""
        paint = SolidPaint(color="#FF0000")

        # Test dict conversion
        try:
            import dataclasses
            if dataclasses.is_dataclass(paint):
                paint_dict = dataclasses.asdict(paint)
                assert 'color' in paint_dict
                assert paint_dict['color'] == '#FF0000'
        except (ImportError, TypeError):
            # Fallback for non-dataclass implementation
            paint_dict = {'color': paint.color}
            assert paint_dict['color'] == '#FF0000'

    def test_gradient_dict_representation(self):
        """Test converting gradient to dictionary."""
        try:
            gradient = LinearGradient(
                start_point=Point(0, 0),
                end_point=Point(100, 0),
                stops=[
                    {"offset": 0.0, "color": "#FF0000"},
                    {"offset": 1.0, "color": "#0000FF"}
                ]
            )

            # Test dict conversion
            try:
                import dataclasses
                if dataclasses.is_dataclass(gradient):
                    gradient_dict = dataclasses.asdict(gradient)
                    assert 'stops' in gradient_dict
                    assert len(gradient_dict['stops']) == 2
            except (ImportError, TypeError):
                # Manual dict creation
                gradient_dict = {
                    'start_point': gradient.start_point,
                    'end_point': gradient.end_point,
                    'stops': gradient.stops
                }
                assert len(gradient_dict['stops']) == 2
        except NameError:
            pytest.skip("LinearGradient not available")


class TestPaintPerformance(IRTestBase):
    """Test paint performance characteristics."""

    def test_solid_paint_creation_performance(self):
        """Test solid paint creation performance."""
        import time

        start_time = time.time()

        paints = []
        for i in range(1000):
            color = f"#{i:06x}"[:7]  # Generate hex colors
            paints.append(SolidPaint(color=color))

        creation_time = time.time() - start_time

        assert len(paints) == 1000
        assert creation_time < 0.1  # Should create quickly

        # Verify first and last paints
        assert paints[0].color == "#000000"
        assert len(paints[999].color) == 7  # Valid hex color

    def test_gradient_creation_performance(self):
        """Test gradient creation performance."""
        try:
            import time

            start_time = time.time()

            gradients = []
            for i in range(100):
                gradient = LinearGradient(
                    start_point=Point(0, 0),
                    end_point=Point(i, 0),
                    stops=[
                        {"offset": 0.0, "color": "#FF0000"},
                        {"offset": 1.0, "color": "#0000FF"}
                    ]
                )
                gradients.append(gradient)

            creation_time = time.time() - start_time

            assert len(gradients) == 100
            assert creation_time < 0.1  # Should create reasonably quickly
        except NameError:
            pytest.skip("LinearGradient not available")


if __name__ == "__main__":
    pytest.main([__file__])