#!/usr/bin/env python3
"""
Unit tests for core IR shape types (Circle, Ellipse, Rectangle).

Tests validation, properties, and basic functionality of native shape
IR representations that enable PowerPoint fidelity.
"""

import pytest
from core.ir.shapes import Circle, Ellipse, Rectangle
from core.ir.geometry import Point, Rect
from core.ir.paint import SolidPaint
from core.ir.effects import ShadowEffect


class TestCircle:
    """Test Circle IR type."""

    def test_circle_initialization(self):
        """Circle initializes with valid parameters."""
        center = Point(x=100.0, y=200.0)
        circle = Circle(center=center, radius=50.0)

        assert circle.center == center
        assert circle.radius == 50.0
        assert circle.fill is None
        assert circle.stroke is None
        assert circle.opacity == 1.0
        assert circle.effects == []

    def test_circle_with_fill(self):
        """Circle accepts fill paint."""
        center = Point(x=100.0, y=200.0)
        fill = SolidPaint(rgb="ff0000")  # Red color
        circle = Circle(center=center, radius=50.0, fill=fill)

        assert circle.fill == fill

    def test_circle_with_opacity(self):
        """Circle accepts custom opacity."""
        center = Point(x=100.0, y=200.0)
        circle = Circle(center=center, radius=50.0, opacity=0.5)

        assert circle.opacity == 0.5

    def test_circle_with_effects(self):
        """Circle accepts effects list."""
        center = Point(x=100.0, y=200.0)
        shadow = ShadowEffect(blur_radius=10.0, distance=5.0, angle=45.0)
        circle = Circle(center=center, radius=50.0, effects=[shadow])

        assert len(circle.effects) == 1
        assert circle.effects[0] == shadow

    def test_circle_bbox_calculation(self):
        """Circle calculates bounding box correctly."""
        center = Point(x=100.0, y=200.0)
        circle = Circle(center=center, radius=50.0)

        bbox = circle.bbox
        assert bbox.x == 50.0  # 100 - 50
        assert bbox.y == 150.0  # 200 - 50
        assert bbox.width == 100.0  # 50 * 2
        assert bbox.height == 100.0  # 50 * 2

    def test_circle_is_closed(self):
        """Circles are always closed shapes."""
        center = Point(x=100.0, y=200.0)
        circle = Circle(center=center, radius=50.0)

        assert circle.is_closed is True

    def test_circle_invalid_radius(self):
        """Circle rejects non-positive radius."""
        center = Point(x=100.0, y=200.0)

        with pytest.raises(ValueError, match="Radius must be positive"):
            Circle(center=center, radius=0.0)

        with pytest.raises(ValueError, match="Radius must be positive"):
            Circle(center=center, radius=-10.0)

    def test_circle_invalid_opacity(self):
        """Circle rejects invalid opacity values."""
        center = Point(x=100.0, y=200.0)

        with pytest.raises(ValueError, match="Opacity must be 0.0-1.0"):
            Circle(center=center, radius=50.0, opacity=1.5)

        with pytest.raises(ValueError, match="Opacity must be 0.0-1.0"):
            Circle(center=center, radius=50.0, opacity=-0.1)


class TestEllipse:
    """Test Ellipse IR type."""

    def test_ellipse_initialization(self):
        """Ellipse initializes with valid parameters."""
        center = Point(x=100.0, y=200.0)
        ellipse = Ellipse(center=center, radius_x=50.0, radius_y=30.0)

        assert ellipse.center == center
        assert ellipse.radius_x == 50.0
        assert ellipse.radius_y == 30.0
        assert ellipse.fill is None
        assert ellipse.stroke is None
        assert ellipse.opacity == 1.0

    def test_ellipse_bbox_calculation(self):
        """Ellipse calculates bounding box correctly."""
        center = Point(x=100.0, y=200.0)
        ellipse = Ellipse(center=center, radius_x=50.0, radius_y=30.0)

        bbox = ellipse.bbox
        assert bbox.x == 50.0  # 100 - 50
        assert bbox.y == 170.0  # 200 - 30
        assert bbox.width == 100.0  # 50 * 2
        assert bbox.height == 60.0  # 30 * 2

    def test_ellipse_is_circle_detection(self):
        """Ellipse detects when radii are equal (circle)."""
        center = Point(x=100.0, y=200.0)

        # Equal radii = circle
        circle_ellipse = Ellipse(center=center, radius_x=50.0, radius_y=50.0)
        assert circle_ellipse.is_circle() is True

        # Different radii = not circle
        ellipse = Ellipse(center=center, radius_x=50.0, radius_y=30.0)
        assert ellipse.is_circle() is False

    def test_ellipse_is_closed(self):
        """Ellipses are always closed shapes."""
        center = Point(x=100.0, y=200.0)
        ellipse = Ellipse(center=center, radius_x=50.0, radius_y=30.0)

        assert ellipse.is_closed is True

    def test_ellipse_invalid_radii(self):
        """Ellipse rejects non-positive radii."""
        center = Point(x=100.0, y=200.0)

        with pytest.raises(ValueError, match="radius_x must be positive"):
            Ellipse(center=center, radius_x=0.0, radius_y=30.0)

        with pytest.raises(ValueError, match="radius_y must be positive"):
            Ellipse(center=center, radius_x=50.0, radius_y=-10.0)


class TestRectangle:
    """Test Rectangle IR type."""

    def test_rectangle_initialization(self):
        """Rectangle initializes with valid parameters."""
        bounds = Rect(x=10.0, y=20.0, width=100.0, height=50.0)
        rect = Rectangle(bounds=bounds)

        assert rect.bounds == bounds
        assert rect.fill is None
        assert rect.stroke is None
        assert rect.opacity == 1.0
        assert rect.corner_radius == 0.0

    def test_rectangle_with_rounded_corners(self):
        """Rectangle accepts rounded corner radius."""
        bounds = Rect(x=10.0, y=20.0, width=100.0, height=50.0)
        rect = Rectangle(bounds=bounds, corner_radius=5.0)

        assert rect.corner_radius == 5.0
        assert rect.is_rounded is True

    def test_rectangle_bbox_calculation(self):
        """Rectangle bbox matches its bounds."""
        bounds = Rect(x=10.0, y=20.0, width=100.0, height=50.0)
        rect = Rectangle(bounds=bounds)

        bbox = rect.bbox
        assert bbox.x == 10.0
        assert bbox.y == 20.0
        assert bbox.width == 100.0
        assert bbox.height == 50.0

    def test_rectangle_is_closed(self):
        """Rectangles are always closed shapes."""
        bounds = Rect(x=10.0, y=20.0, width=100.0, height=50.0)
        rect = Rectangle(bounds=bounds)

        assert rect.is_closed is True

    def test_rectangle_invalid_dimensions(self):
        """Rectangle rejects non-positive dimensions."""
        with pytest.raises(ValueError, match="Width must be positive"):
            bounds = Rect(x=10.0, y=20.0, width=0.0, height=50.0)
            Rectangle(bounds=bounds)

        with pytest.raises(ValueError, match="Height must be positive"):
            bounds = Rect(x=10.0, y=20.0, width=100.0, height=-10.0)
            Rectangle(bounds=bounds)


class TestShapeComparison:
    """Test comparison and equality between shapes."""

    def test_circles_equal(self):
        """Two circles with same parameters are equal."""
        center1 = Point(x=100.0, y=200.0)
        center2 = Point(x=100.0, y=200.0)

        circle1 = Circle(center=center1, radius=50.0)
        circle2 = Circle(center=center2, radius=50.0)

        assert circle1 == circle2

    def test_circles_not_equal(self):
        """Circles with different parameters are not equal."""
        center1 = Point(x=100.0, y=200.0)
        center2 = Point(x=150.0, y=200.0)

        circle1 = Circle(center=center1, radius=50.0)
        circle2 = Circle(center=center2, radius=50.0)

        assert circle1 != circle2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
