"""Bézier evaluation helpers for curve text positioning."""

from __future__ import annotations

import math
from typing import List, TYPE_CHECKING

from ...ir.text_path import PathPoint

if TYPE_CHECKING:  # pragma: no cover
    from .curve_sampling import PathSegment


def evaluate_line_segment(
    segment: "PathSegment",
    t: float,
    distance: float,
) -> PathPoint:
    start, end = segment.start_point, segment.end_point
    x = start.x + t * (end.x - start.x)
    y = start.y + t * (end.y - start.y)
    dx = end.x - start.x
    dy = end.y - start.y
    angle = math.atan2(dy, dx) if (dx or dy) else 0.0
    return PathPoint(x=x, y=y, tangent_angle=angle, distance_along_path=distance)


def evaluate_cubic_segment(
    segment: "PathSegment",
    t: float,
    distance: float,
) -> PathPoint:
    p0 = segment.start_point
    p3 = segment.end_point
    p1, p2 = segment.control_points[0], segment.control_points[1]

    x = (
        (1 - t) ** 3 * p0.x
        + 3 * (1 - t) ** 2 * t * p1.x
        + 3 * (1 - t) * t**2 * p2.x
        + t**3 * p3.x
    )
    y = (
        (1 - t) ** 3 * p0.y
        + 3 * (1 - t) ** 2 * t * p1.y
        + 3 * (1 - t) * t**2 * p2.y
        + t**3 * p3.y
    )

    dx_dt = (
        3 * (1 - t) ** 2 * (p1.x - p0.x)
        + 6 * (1 - t) * t * (p2.x - p1.x)
        + 3 * t**2 * (p3.x - p2.x)
    )
    dy_dt = (
        3 * (1 - t) ** 2 * (p1.y - p0.y)
        + 6 * (1 - t) * t * (p2.y - p1.y)
        + 3 * t**2 * (p3.y - p2.y)
    )
    angle = math.atan2(dy_dt, dx_dt) if (dx_dt or dy_dt) else 0.0
    return PathPoint(x=x, y=y, tangent_angle=angle, distance_along_path=distance)


def evaluate_quadratic_segment(
    segment: "PathSegment",
    t: float,
    distance: float,
) -> PathPoint:
    p0 = segment.start_point
    p2 = segment.end_point
    p1 = segment.control_points[0]

    x = (1 - t) ** 2 * p0.x + 2 * (1 - t) * t * p1.x + t**2 * p2.x
    y = (1 - t) ** 2 * p0.y + 2 * (1 - t) * t * p1.y + t**2 * p2.y

    dx_dt = 2 * (1 - t) * (p1.x - p0.x) + 2 * t * (p2.x - p1.x)
    dy_dt = 2 * (1 - t) * (p1.y - p0.y) + 2 * t * (p2.y - p1.y)
    angle = math.atan2(dy_dt, dx_dt) if (dx_dt or dy_dt) else 0.0
    return PathPoint(x=x, y=y, tangent_angle=angle, distance_along_path=distance)


def sample_line_segment(
    segment: "PathSegment",
    num_samples: int,
    base_distance: float,
) -> List[PathPoint]:
    points: List[PathPoint] = []
    start = segment.start_point
    end = segment.end_point
    angle_rad = math.atan2(end.y - start.y, end.x - start.x)

    for i in range(num_samples):
        t = i / (num_samples - 1) if num_samples > 1 else 0
        x = start.x + t * (end.x - start.x)
        y = start.y + t * (end.y - start.y)
        distance = base_distance + t * segment.length
        points.append(PathPoint(x=x, y=y, tangent_angle=angle_rad, distance_along_path=distance))
    return points


def sample_cubic_segment(
    segment: "PathSegment",
    num_samples: int,
    base_distance: float,
) -> List[PathPoint]:
    points: List[PathPoint] = []
    for i in range(num_samples):
        t = i / (num_samples - 1) if num_samples > 1 else 0
        distance = base_distance + t * segment.length
        points.append(evaluate_cubic_segment(segment, t, distance))
    return points


def sample_quadratic_segment(
    segment: "PathSegment",
    num_samples: int,
    base_distance: float,
) -> List[PathPoint]:
    points: List[PathPoint] = []
    for i in range(num_samples):
        t = i / (num_samples - 1) if num_samples > 1 else 0
        distance = base_distance + t * segment.length
        points.append(evaluate_quadratic_segment(segment, t, distance))
    return points


def interpolate_angle(angle1: float, angle2: float, t: float) -> float:
    angle1 = angle1 % (2 * math.pi)
    angle2 = angle2 % (2 * math.pi)
    diff = angle2 - angle1
    if diff > math.pi:
        diff -= 2 * math.pi
    elif diff < -math.pi:
        diff += 2 * math.pi
    return angle1 + t * diff


__all__ = [
    "evaluate_line_segment",
    "evaluate_cubic_segment",
    "evaluate_quadratic_segment",
    "sample_line_segment",
    "sample_cubic_segment",
    "sample_quadratic_segment",
    "interpolate_angle",
]
