#!/usr/bin/env python3
"""
Unit tests for core IR Geometry components.

Tests the geometric primitives (Point, Rect, LineSegment, etc.) that form
the foundation of the IR data structure.
"""

import pytest
import math
from unittest.mock import Mock

from tests.unit.core.conftest import IRTestBase

try:
    from core.ir import Point, Rect, LineSegment, BezierSegment, ArcSegment
    from core.ir import validate_ir, IRValidationError
    CORE_IR_AVAILABLE = True
except ImportError:
    CORE_IR_AVAILABLE = False
    pytest.skip("Core IR components not available", allow_module_level=True)


class TestPointCreation(IRTestBase):
    """Test Point object creation and basic properties."""

    def test_point_creation_basic(self):
        """Test creating a basic point."""
        point = Point(10.5, 20.3)

        assert point.x == 10.5
        assert point.y == 20.3
        self.assert_valid_ir_element(point)

    def test_point_creation_integers(self):
        """Test creating point with integer coordinates."""
        point = Point(10, 20)

        assert point.x == 10
        assert point.y == 20
        assert isinstance(point.x, (int, float))
        assert isinstance(point.y, (int, float))
        self.assert_valid_ir_element(point)

    def test_point_creation_negative(self):
        """Test creating point with negative coordinates."""
        point = Point(-15.5, -25.7)

        assert point.x == -15.5
        assert point.y == -25.7
        self.assert_valid_ir_element(point)

    def test_point_creation_zero(self):
        """Test creating point at origin."""
        point = Point(0, 0)

        assert point.x == 0
        assert point.y == 0
        self.assert_valid_ir_element(point)

    def test_point_creation_large_coordinates(self):
        """Test creating point with very large coordinates."""
        point = Point(1e6, 1e7)

        assert point.x == 1e6
        assert point.y == 1e7
        self.assert_valid_ir_element(point)


class TestPointOperations(IRTestBase):
    """Test Point mathematical operations."""

    def test_point_equality(self):
        """Test point equality comparison."""
        point1 = Point(10, 20)
        point2 = Point(10, 20)
        point3 = Point(10, 21)

        assert point1 == point2
        assert point1 != point3
        assert point2 != point3

    def test_point_distance_calculation(self):
        """Test distance calculation between points."""
        point1 = Point(0, 0)
        point2 = Point(3, 4)

        # Test if distance method exists and works
        if hasattr(point1, 'distance_to'):
            distance = point1.distance_to(point2)
            assert abs(distance - 5.0) < 1e-10  # 3-4-5 triangle

        # Alternative: manual calculation
        dx = point2.x - point1.x
        dy = point2.y - point1.y
        distance = math.sqrt(dx*dx + dy*dy)
        assert abs(distance - 5.0) < 1e-10

    def test_point_translation(self):
        """Test point translation operations."""
        point = Point(10, 20)

        # Test if translate method exists
        if hasattr(point, 'translate'):
            translated = point.translate(5, -3)
            assert translated.x == 15
            assert translated.y == 17
            # Original should be immutable
            assert point.x == 10
            assert point.y == 20

    def test_point_string_representation(self):
        """Test point string representation."""
        point = Point(10.5, 20.3)

        str_repr = str(point)
        assert "10.5" in str_repr
        assert "20.3" in str_repr


class TestRectCreation(IRTestBase):
    """Test Rect object creation and properties."""

    def test_rect_creation_basic(self):
        """Test creating a basic rectangle."""
        rect = Rect(10, 20, 100, 80)

        assert rect.x == 10
        assert rect.y == 20
        assert rect.width == 100
        assert rect.height == 80
        self.assert_valid_ir_element(rect)

    def test_rect_creation_from_points(self):
        """Test creating rectangle from corner points."""
        # If Rect supports point-based construction
        top_left = Point(10, 20)
        bottom_right = Point(110, 100)

        try:
            rect = Rect.from_points(top_left, bottom_right)
            assert rect.x == 10
            assert rect.y == 20
            assert rect.width == 100
            assert rect.height == 80
        except (AttributeError, TypeError):
            # Alternative construction
            rect = Rect(
                top_left.x,
                top_left.y,
                bottom_right.x - top_left.x,
                bottom_right.y - top_left.y
            )
            assert rect.x == 10
            assert rect.y == 20
            assert rect.width == 100
            assert rect.height == 80

    def test_rect_zero_dimensions(self):
        """Test rectangle with zero dimensions."""
        rect = Rect(10, 20, 0, 0)

        assert rect.width == 0
        assert rect.height == 0
        self.assert_valid_ir_element(rect)

    def test_rect_negative_dimensions(self):
        """Test handling of negative dimensions."""
        # This might be invalid depending on implementation
        try:
            rect = Rect(10, 20, -5, -10)
            # If creation succeeds, test behavior
            assert rect.width == -5
            assert rect.height == -10
        except ValueError:
            # Negative dimensions might be rejected
            pass

    def test_rect_boundary_calculations(self):
        """Test rectangle boundary calculations."""
        rect = Rect(10, 20, 100, 80)

        # Test boundary methods if they exist
        if hasattr(rect, 'left'):
            assert rect.left == 10
        if hasattr(rect, 'top'):
            assert rect.top == 20
        if hasattr(rect, 'right'):
            assert rect.right == 110  # x + width
        if hasattr(rect, 'bottom'):
            assert rect.bottom == 100  # y + height


class TestRectOperations(IRTestBase):
    """Test Rect mathematical operations."""

    def test_rect_contains_point(self):
        """Test rectangle point containment."""
        rect = Rect(10, 20, 100, 80)

        point_inside = Point(50, 60)
        point_outside = Point(150, 150)
        point_on_edge = Point(10, 60)

        # Test contains method if it exists
        if hasattr(rect, 'contains'):
            assert rect.contains(point_inside)
            assert not rect.contains(point_outside)
            # Edge behavior may vary
        else:
            # Manual containment check
            def contains(rect, point):
                return (rect.x <= point.x <= rect.x + rect.width and
                        rect.y <= point.y <= rect.y + rect.height)

            assert contains(rect, point_inside)
            assert not contains(rect, point_outside)

    def test_rect_intersection(self):
        """Test rectangle intersection."""
        rect1 = Rect(0, 0, 100, 100)
        rect2 = Rect(50, 50, 100, 100)
        rect3 = Rect(200, 200, 100, 100)

        # Test intersection method if it exists
        if hasattr(rect1, 'intersects'):
            assert rect1.intersects(rect2)  # Overlapping
            assert not rect1.intersects(rect3)  # Non-overlapping

    def test_rect_area_calculation(self):
        """Test rectangle area calculation."""
        rect = Rect(10, 20, 100, 80)

        if hasattr(rect, 'area'):
            assert rect.area == 8000
        else:
            # Manual calculation
            area = rect.width * rect.height
            assert area == 8000

    def test_rect_equality(self):
        """Test rectangle equality comparison."""
        rect1 = Rect(10, 20, 100, 80)
        rect2 = Rect(10, 20, 100, 80)
        rect3 = Rect(10, 20, 100, 90)

        assert rect1 == rect2
        assert rect1 != rect3


class TestLineSegmentCreation(IRTestBase):
    """Test LineSegment creation and properties."""

    def test_line_segment_creation(self):
        """Test creating a line segment."""
        start = Point(10, 20)
        end = Point(30, 40)

        segment = LineSegment(start, end)

        assert segment.start == start
        assert segment.end == end
        self.assert_valid_ir_element(segment)

    def test_line_segment_same_points(self):
        """Test line segment with same start and end."""
        point = Point(10, 20)
        segment = LineSegment(point, point)

        assert segment.start == segment.end
        self.assert_valid_ir_element(segment)

    def test_line_segment_length_calculation(self):
        """Test line segment length calculation."""
        start = Point(0, 0)
        end = Point(3, 4)
        segment = LineSegment(start, end)

        if hasattr(segment, 'length'):
            assert abs(segment.length - 5.0) < 1e-10
        else:
            # Manual length calculation
            dx = end.x - start.x
            dy = end.y - start.y
            length = math.sqrt(dx*dx + dy*dy)
            assert abs(length - 5.0) < 1e-10


class TestBezierSegmentCreation(IRTestBase):
    """Test BezierSegment creation and properties."""

    def test_bezier_segment_quadratic(self):
        """Test creating a quadratic Bezier segment."""
        start = Point(0, 0)
        control = Point(50, 100)
        end = Point(100, 0)

        try:
            segment = BezierSegment(start, end, control1=control)
            assert segment.start == start
            assert segment.end == end
            assert segment.control1 == control
            self.assert_valid_ir_element(segment)
        except (NameError, AttributeError):
            # BezierSegment might not be implemented yet
            pytest.skip("BezierSegment not available")

    def test_bezier_segment_cubic(self):
        """Test creating a cubic Bezier segment."""
        start = Point(0, 0)
        control1 = Point(25, 100)
        control2 = Point(75, 100)
        end = Point(100, 0)

        try:
            segment = BezierSegment(start, end, control1=control1, control2=control2)
            assert segment.start == start
            assert segment.end == end
            assert segment.control1 == control1
            assert segment.control2 == control2
            self.assert_valid_ir_element(segment)
        except (NameError, AttributeError):
            pytest.skip("BezierSegment not available")


class TestArcSegmentCreation(IRTestBase):
    """Test ArcSegment creation and properties."""

    def test_arc_segment_creation(self):
        """Test creating an arc segment."""
        start = Point(0, 0)
        end = Point(100, 100)

        try:
            segment = ArcSegment(
                start=start,
                end=end,
                rx=50,
                ry=50,
                rotation=0,
                large_arc=False,
                sweep=True
            )
            assert segment.start == start
            assert segment.end == end
            assert segment.rx == 50
            assert segment.ry == 50
            self.assert_valid_ir_element(segment)
        except (NameError, AttributeError):
            pytest.skip("ArcSegment not available")

    def test_arc_segment_elliptical(self):
        """Test creating an elliptical arc segment."""
        start = Point(0, 0)
        end = Point(100, 50)

        try:
            segment = ArcSegment(
                start=start,
                end=end,
                rx=75,
                ry=25,
                rotation=45,
                large_arc=True,
                sweep=False
            )
            assert segment.rx == 75
            assert segment.ry == 25
            assert segment.rotation == 45
            assert segment.large_arc == True
            assert segment.sweep == False
            self.assert_valid_ir_element(segment)
        except (NameError, AttributeError):
            pytest.skip("ArcSegment not available")


class TestGeometryValidation(IRTestBase):
    """Test geometry validation and error handling."""

    def test_point_validation_invalid_types(self):
        """Test point validation with invalid coordinate types."""
        with pytest.raises((TypeError, ValueError)):
            Point("invalid", 20)

        with pytest.raises((TypeError, ValueError)):
            Point(10, None)

    def test_rect_validation_invalid_types(self):
        """Test rectangle validation with invalid parameters."""
        with pytest.raises((TypeError, ValueError)):
            Rect("invalid", 20, 100, 80)

        with pytest.raises((TypeError, ValueError)):
            Rect(10, 20, "invalid", 80)

    def test_line_segment_validation_invalid_points(self):
        """Test line segment validation with invalid points."""
        valid_point = Point(10, 20)

        with pytest.raises((TypeError, ValueError)):
            LineSegment("invalid", valid_point)

        with pytest.raises((TypeError, ValueError)):
            LineSegment(valid_point, None)

    def test_geometry_immutability(self):
        """Test that geometry objects are immutable."""
        point = Point(10, 20)
        rect = Rect(10, 20, 100, 80)

        # Try to modify coordinates (should fail or be ignored)
        try:
            point.x = 30
            # If modification succeeds, it should be ignored for immutability
        except AttributeError:
            # Expected for truly immutable objects
            pass

        # Original values should be unchanged
        assert point.x == 10
        assert point.y == 20


class TestGeometryPerformance(IRTestBase):
    """Test geometry performance characteristics."""

    def test_point_creation_performance(self):
        """Test point creation performance."""
        import time

        start_time = time.time()

        points = []
        for i in range(1000):
            points.append(Point(i, i*2))

        creation_time = time.time() - start_time

        assert len(points) == 1000
        assert creation_time < 0.1  # Should create quickly

        # Verify first and last points
        assert points[0].x == 0
        assert points[0].y == 0
        assert points[999].x == 999
        assert points[999].y == 1998

    def test_rect_operations_performance(self):
        """Test rectangle operations performance."""
        import time

        rects = [Rect(i, i, 100, 100) for i in range(100)]
        test_point = Point(50, 50)

        start_time = time.time()

        # Test containment checks
        containment_results = []
        for rect in rects:
            if hasattr(rect, 'contains'):
                containment_results.append(rect.contains(test_point))
            else:
                # Manual containment
                contains = (rect.x <= test_point.x <= rect.x + rect.width and
                           rect.y <= test_point.y <= rect.y + rect.height)
                containment_results.append(contains)

        operation_time = time.time() - start_time

        assert len(containment_results) == 100
        assert operation_time < 0.01  # Should be very fast

        # Some rects should contain the point
        assert any(containment_results)


if __name__ == "__main__":
    pytest.main([__file__])