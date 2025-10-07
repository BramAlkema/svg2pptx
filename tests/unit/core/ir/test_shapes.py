#!/usr/bin/env python3
"""
Unit tests for native shape IR types

Tests Circle, Ellipse, and Rectangle IR dataclasses with focus on:
- Geometric parameter validation
- Bounding box calculation
- Edge cases (zero/negative dimensions, opacity bounds)
- Shape-specific methods (is_circle, is_rounded)
"""

import pytest
import numpy as np

from core.ir.shapes import Circle, Ellipse, Rectangle
from core.ir.geometry import Point, Rect
from core.ir.paint import SolidPaint


class TestCircle:
    """Tests for Circle IR type"""

    def test_create_simple_circle(self):
        """Test basic circle creation"""
        circle = Circle(
            center=Point(100, 50),
            radius=25.0,
        )

        assert circle.center.x == 100
        assert circle.center.y == 50
        assert circle.radius == 25.0
        assert circle.opacity == 1.0
        assert circle.fill is None
        assert circle.stroke is None

    def test_circle_with_fill(self):
        """Test circle with solid fill"""
        fill = SolidPaint(rgb="FF0000")
        circle = Circle(
            center=Point(0, 0),
            radius=10.0,
            fill=fill,
        )

        assert circle.fill == fill

    def test_circle_bbox_calculation(self):
        """Test bounding box is correctly calculated from center and radius"""
        circle = Circle(
            center=Point(300, 100),
            radius=40.0,
        )

        bbox = circle.bbox
        assert bbox.x == 260  # 300 - 40
        assert bbox.y == 60   # 100 - 40
        assert bbox.width == 80  # 40 * 2
        assert bbox.height == 80

    def test_circle_is_closed(self):
        """Test circles are always closed"""
        circle = Circle(center=Point(0, 0), radius=1.0)
        assert circle.is_closed is True

    def test_circle_zero_radius_rejected(self):
        """Test zero radius is rejected"""
        with pytest.raises(ValueError, match="Radius must be positive"):
            Circle(center=Point(0, 0), radius=0.0)

    def test_circle_negative_radius_rejected(self):
        """Test negative radius is rejected"""
        with pytest.raises(ValueError, match="Radius must be positive"):
            Circle(center=Point(0, 0), radius=-10.0)

    def test_circle_invalid_opacity_too_low(self):
        """Test opacity below 0.0 is rejected"""
        with pytest.raises(ValueError, match="Opacity must be 0.0-1.0"):
            Circle(center=Point(0, 0), radius=1.0, opacity=-0.1)

    def test_circle_invalid_opacity_too_high(self):
        """Test opacity above 1.0 is rejected"""
        with pytest.raises(ValueError, match="Opacity must be 0.0-1.0"):
            Circle(center=Point(0, 0), radius=1.0, opacity=1.5)

    def test_circle_opacity_boundary_values(self):
        """Test opacity boundary values are accepted"""
        # Opacity 0.0 (fully transparent)
        c1 = Circle(center=Point(0, 0), radius=1.0, opacity=0.0)
        assert c1.opacity == 0.0

        # Opacity 1.0 (fully opaque)
        c2 = Circle(center=Point(0, 0), radius=1.0, opacity=1.0)
        assert c2.opacity == 1.0


class TestEllipse:
    """Tests for Ellipse IR type"""

    def test_create_simple_ellipse(self):
        """Test basic ellipse creation"""
        ellipse = Ellipse(
            center=Point(200, 200),
            radius_x=60.0,
            radius_y=30.0,
        )

        assert ellipse.center.x == 200
        assert ellipse.center.y == 200
        assert ellipse.radius_x == 60.0
        assert ellipse.radius_y == 30.0
        assert ellipse.opacity == 1.0

    def test_ellipse_bbox_calculation(self):
        """Test bounding box uses both radii"""
        ellipse = Ellipse(
            center=Point(200, 200),
            radius_x=60.0,
            radius_y=30.0,
        )

        bbox = ellipse.bbox
        assert bbox.x == 140    # 200 - 60
        assert bbox.y == 170    # 200 - 30
        assert bbox.width == 120  # 60 * 2
        assert bbox.height == 60  # 30 * 2

    def test_ellipse_is_closed(self):
        """Test ellipses are always closed"""
        ellipse = Ellipse(center=Point(0, 0), radius_x=10.0, radius_y=5.0)
        assert ellipse.is_closed is True

    def test_ellipse_is_circle_detection_true(self):
        """Test is_circle() returns True when radii are equal"""
        ellipse = Ellipse(
            center=Point(0, 0),
            radius_x=50.0,
            radius_y=50.0,
        )

        assert ellipse.is_circle() is True

    def test_ellipse_is_circle_detection_false(self):
        """Test is_circle() returns False for different radii"""
        ellipse = Ellipse(
            center=Point(0, 0),
            radius_x=60.0,
            radius_y=30.0,
        )

        assert ellipse.is_circle() is False

    def test_ellipse_is_circle_with_tolerance(self):
        """Test is_circle() tolerance for nearly-equal radii"""
        # Within 1% tolerance (default)
        ellipse1 = Ellipse(
            center=Point(0, 0),
            radius_x=100.0,
            radius_y=100.5,  # 0.5% difference
        )
        assert ellipse1.is_circle() is True

        # Outside 1% tolerance
        ellipse2 = Ellipse(
            center=Point(0, 0),
            radius_x=100.0,
            radius_y=102.0,  # 2% difference
        )
        assert ellipse2.is_circle() is False

    def test_ellipse_is_circle_custom_tolerance(self):
        """Test is_circle() with custom tolerance"""
        ellipse = Ellipse(
            center=Point(0, 0),
            radius_x=100.0,
            radius_y=105.0,  # 5% difference
        )

        # Stricter tolerance
        assert ellipse.is_circle(tolerance=0.01) is False

        # Looser tolerance
        assert ellipse.is_circle(tolerance=0.10) is True

    def test_ellipse_zero_radius_x_rejected(self):
        """Test zero radius_x is rejected"""
        with pytest.raises(ValueError, match="radius_x must be positive"):
            Ellipse(center=Point(0, 0), radius_x=0.0, radius_y=10.0)

    def test_ellipse_zero_radius_y_rejected(self):
        """Test zero radius_y is rejected"""
        with pytest.raises(ValueError, match="radius_y must be positive"):
            Ellipse(center=Point(0, 0), radius_x=10.0, radius_y=0.0)

    def test_ellipse_negative_radius_rejected(self):
        """Test negative radii are rejected"""
        with pytest.raises(ValueError, match="radius_x must be positive"):
            Ellipse(center=Point(0, 0), radius_x=-10.0, radius_y=10.0)

    def test_ellipse_opacity_validation(self):
        """Test opacity validation"""
        with pytest.raises(ValueError, match="Opacity must be 0.0-1.0"):
            Ellipse(center=Point(0, 0), radius_x=1.0, radius_y=1.0, opacity=2.0)


class TestRectangle:
    """Tests for Rectangle IR type"""

    def test_create_simple_rectangle(self):
        """Test basic rectangle creation"""
        rect = Rectangle(
            bounds=Rect(x=50, y=50, width=100, height=80),
        )

        assert rect.bounds.x == 50
        assert rect.bounds.y == 50
        assert rect.bounds.width == 100
        assert rect.bounds.height == 80
        assert rect.corner_radius == 0.0
        assert rect.opacity == 1.0

    def test_rectangle_with_corner_radius(self):
        """Test rounded rectangle"""
        rect = Rectangle(
            bounds=Rect(x=0, y=0, width=200, height=100),
            corner_radius=10.0,
        )

        assert rect.corner_radius == 10.0
        assert rect.is_rounded is True

    def test_rectangle_bbox_same_as_bounds(self):
        """Test bbox property returns bounds"""
        bounds = Rect(x=10, y=20, width=30, height=40)
        rect = Rectangle(bounds=bounds)

        assert rect.bbox == bounds
        assert rect.bbox.x == 10
        assert rect.bbox.y == 20
        assert rect.bbox.width == 30
        assert rect.bbox.height == 40

    def test_rectangle_is_closed(self):
        """Test rectangles are always closed"""
        rect = Rectangle(bounds=Rect(x=0, y=0, width=10, height=10))
        assert rect.is_closed is True

    def test_rectangle_is_rounded_sharp_corners(self):
        """Test is_rounded is False for sharp corners"""
        rect = Rectangle(
            bounds=Rect(x=0, y=0, width=100, height=100),
            corner_radius=0.0,
        )

        assert rect.is_rounded is False

    def test_rectangle_is_rounded_with_radius(self):
        """Test is_rounded is True for non-zero radius"""
        rect = Rectangle(
            bounds=Rect(x=0, y=0, width=100, height=100),
            corner_radius=5.0,
        )

        assert rect.is_rounded is True

    def test_rectangle_zero_width_rejected(self):
        """Test zero width is rejected"""
        with pytest.raises(ValueError, match="Width must be positive"):
            Rectangle(bounds=Rect(x=0, y=0, width=0, height=10))

    def test_rectangle_zero_height_rejected(self):
        """Test zero height is rejected"""
        with pytest.raises(ValueError, match="Height must be positive"):
            Rectangle(bounds=Rect(x=0, y=0, width=10, height=0))

    def test_rectangle_negative_dimensions_rejected(self):
        """Test negative dimensions are rejected"""
        with pytest.raises(ValueError, match="Width must be positive"):
            Rectangle(bounds=Rect(x=0, y=0, width=-10, height=10))

    def test_rectangle_negative_corner_radius_rejected(self):
        """Test negative corner radius is rejected"""
        with pytest.raises(ValueError, match="corner_radius must be non-negative"):
            Rectangle(
                bounds=Rect(x=0, y=0, width=100, height=100),
                corner_radius=-5.0,
            )

    def test_rectangle_opacity_validation(self):
        """Test opacity validation"""
        with pytest.raises(ValueError, match="Opacity must be 0.0-1.0"):
            Rectangle(
                bounds=Rect(x=0, y=0, width=10, height=10),
                opacity=1.5,
            )


@pytest.mark.skip(reason="Phase 2: Shapes no longer have transform fields - transforms are baked during parsing")
class TestShapeTransforms:
    """Tests for transform support in shapes - OBSOLETE in Phase 2"""

    def test_circle_with_simple_transform(self):
        """Test circle can have transform matrix"""
        transform = np.eye(3)  # Identity matrix
        circle = Circle(
            center=Point(0, 0),
            radius=10.0,
            transform=transform,
        )

        assert circle.transform is not None
        assert np.array_equal(circle.transform, transform)

    def test_ellipse_with_transform(self):
        """Test ellipse can have transform matrix"""
        transform = np.array([
            [1, 0, 10],   # Translate x by 10
            [0, 1, 20],   # Translate y by 20
            [0, 0, 1],
        ])
        ellipse = Ellipse(
            center=Point(0, 0),
            radius_x=5.0,
            radius_y=3.0,
            transform=transform,
        )

        assert ellipse.transform is not None

    def test_rectangle_with_transform(self):
        """Test rectangle can have transform matrix"""
        transform = np.array([
            [2, 0, 0],  # Scale x by 2
            [0, 2, 0],  # Scale y by 2
            [0, 0, 1],
        ])
        rect = Rectangle(
            bounds=Rect(x=0, y=0, width=10, height=10),
            transform=transform,
        )

        assert rect.transform is not None


class TestShapeEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_very_small_circle(self):
        """Test circle with very small radius"""
        circle = Circle(center=Point(0, 0), radius=0.001)
        assert circle.radius == 0.001
        assert circle.bbox.width == 0.002

    def test_very_large_circle(self):
        """Test circle with very large radius"""
        circle = Circle(center=Point(0, 0), radius=10000.0)
        assert circle.bbox.width == 20000.0

    def test_ellipse_extreme_aspect_ratio(self):
        """Test ellipse with extreme aspect ratio"""
        ellipse = Ellipse(
            center=Point(0, 0),
            radius_x=1000.0,
            radius_y=1.0,
        )

        assert ellipse.is_circle() is False
        assert ellipse.bbox.width == 2000.0
        assert ellipse.bbox.height == 2.0

    def test_rectangle_very_thin(self):
        """Test very thin rectangle"""
        rect = Rectangle(bounds=Rect(x=0, y=0, width=1000, height=1))
        assert rect.bounds.width == 1000
        assert rect.bounds.height == 1

    def test_shapes_with_zero_opacity(self):
        """Test shapes can have zero opacity (fully transparent)"""
        circle = Circle(center=Point(0, 0), radius=10, opacity=0.0)
        assert circle.opacity == 0.0

        ellipse = Ellipse(center=Point(0, 0), radius_x=10, radius_y=5, opacity=0.0)
        assert ellipse.opacity == 0.0

        rect = Rectangle(bounds=Rect(x=0, y=0, width=10, height=10), opacity=0.0)
        assert rect.opacity == 0.0
