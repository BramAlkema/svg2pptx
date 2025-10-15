"""Path parsing and sampling helpers for curve text positioning."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List

from ...ir.geometry import Point
from ...ir.text_path import PathPoint
from .bezier_utils import (
    evaluate_cubic_segment,
    evaluate_line_segment,
    evaluate_quadratic_segment,
    sample_cubic_segment,
    sample_line_segment,
    sample_quadratic_segment,
)


class PathSamplingMethod(Enum):
    """Path sampling methods for different use cases."""

    UNIFORM = "uniform"
    ARC_LENGTH = "arc_length"
    ADAPTIVE = "adaptive"
    DETERMINISTIC = "deterministic"


@dataclass
class PathSegment:
    """Represents a single path segment."""

    start_point: Point
    end_point: Point
    control_points: list[Point]
    segment_type: str  # 'line', 'cubic', 'quadratic', 'arc'
    length: float


def parse_path_segments(path_data: str) -> list[PathSegment]:
    commands = _parse_path_commands(path_data)
    if not commands:
        return []

    segments: list[PathSegment] = []
    current_point = Point(0.0, 0.0)
    start_point = Point(0.0, 0.0)

    for cmd_tuple in commands:
        cmd = cmd_tuple[0]
        args = list(cmd_tuple[1:]) if len(cmd_tuple) > 1 else []

        if cmd.islower() and cmd.upper() != "Z":
            cmd = cmd.upper()
            for i in range(0, len(args), 2):
                if i + 1 < len(args):
                    args[i] += current_point.x
                    args[i + 1] += current_point.y

        if cmd == "M":
            if len(args) >= 2:
                current_point = Point(args[0], args[1])
                start_point = current_point
        elif cmd == "L" and len(args) >= 2:
            end_point = Point(args[0], args[1])
            segments.append(_create_line_segment(current_point, end_point))
            current_point = end_point
        elif cmd == "C" and len(args) >= 6:
            cp1 = Point(args[0], args[1])
            cp2 = Point(args[2], args[3])
            end_point = Point(args[4], args[5])
            segments.append(_create_cubic_segment(current_point, cp1, cp2, end_point))
            current_point = end_point
        elif cmd == "Q" and len(args) >= 4:
            cp = Point(args[0], args[1])
            end_point = Point(args[2], args[3])
            segments.append(_create_quadratic_segment(current_point, cp, end_point))
            current_point = end_point
        elif cmd == "A" and len(args) >= 7:
            end_point = Point(args[5], args[6])
            segments.append(_create_line_segment(current_point, end_point))
            current_point = end_point
        elif cmd == "Z":
            if current_point != start_point:
                segments.append(_create_line_segment(current_point, start_point))
                current_point = start_point

    return segments


def fallback_horizontal_line(num_samples: int) -> list[PathPoint]:
    points = []
    for i in range(num_samples):
        x = 100.0 * i / max(1, num_samples - 1)
        points.append(
            PathPoint(
                x=x,
                y=0.0,
                tangent_angle=0.0,
                distance_along_path=x,
            )
        )
    return points


def sample_path_deterministic(
    segments: list[PathSegment],
    total_length: float,
    num_samples: int,
) -> list[PathPoint]:
    cumulative_lengths = [0.0]
    for segment in segments:
        cumulative_lengths.append(cumulative_lengths[-1] + segment.length)

    path_points: list[PathPoint] = []

    for i in range(num_samples):
        s_target = (total_length * i) / (num_samples - 1) if num_samples > 1 else 0
        seg_idx = 0
        for j in range(len(cumulative_lengths) - 1):
            if cumulative_lengths[j] <= s_target <= cumulative_lengths[j + 1]:
                seg_idx = j
                break

        s_local = s_target - cumulative_lengths[seg_idx]
        segment = segments[seg_idx]
        path_points.append(sample_segment_at_distance(segment, s_local, s_target))

    return path_points


def sample_path_proportional(
    segments: list[PathSegment],
    total_length: float,
    num_samples: int,
) -> list[PathPoint]:
    path_points: list[PathPoint] = []
    cumulative_distance = 0.0

    for segment in segments:
        segment_ratio = segment.length / total_length if total_length > 0 else 0
        segment_samples = max(2, int(num_samples * segment_ratio))
        segment_points = sample_segment(segment, segment_samples, cumulative_distance)

        if not path_points:
            path_points.extend(segment_points)
        else:
            path_points.extend(segment_points[1:])

        cumulative_distance += segment.length

    return path_points


def sample_segment_at_distance(
    segment: PathSegment,
    local_distance: float,
    global_distance: float,
) -> PathPoint:
    if segment.length == 0:
        t = 0.0
    else:
        t = local_distance / segment.length

    t = max(0.0, min(1.0, t))

    if segment.segment_type == "line":
        return evaluate_line_segment(segment, t, global_distance)
    if segment.segment_type == "cubic":
        return evaluate_cubic_segment(segment, t, global_distance)
    if segment.segment_type == "quadratic":
        return evaluate_quadratic_segment(segment, t, global_distance)
    return evaluate_line_segment(segment, t, global_distance)


def sample_segment(
    segment: PathSegment,
    num_samples: int,
    base_distance: float,
) -> list[PathPoint]:
    if segment.segment_type == "line":
        return sample_line_segment(segment, num_samples, base_distance)
    if segment.segment_type == "cubic":
        return sample_cubic_segment(segment, num_samples, base_distance)
    if segment.segment_type == "quadratic":
        return sample_quadratic_segment(segment, num_samples, base_distance)
    return sample_line_segment(segment, num_samples, base_distance)


def _parse_path_commands(path_data: str) -> list[tuple]:
    commands = []
    pattern = r"([MmLlHhVvCcSsQqTtAaZz])([^MmLlHhVvCcSsQqTtAaZz]*)"

    for match in re.finditer(pattern, path_data):
        cmd = match.group(1)
        params_str = match.group(2).strip()

        if params_str:
            params = [
                float(num)
                for num in re.findall(
                    r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", params_str
                )
            ]
            if params:
                commands.append((cmd, *params))
            else:
                commands.append((cmd,))
        else:
            commands.append((cmd,))

    return commands


def _create_line_segment(start: Point, end: Point) -> PathSegment:
    length = math.hypot(end.x - start.x, end.y - start.y)
    return PathSegment(
        start_point=start,
        end_point=end,
        control_points=[],
        segment_type="line",
        length=length,
    )


def _create_cubic_segment(
    start: Point, cp1: Point, cp2: Point, end: Point
) -> PathSegment:
    length = (
        math.hypot(cp1.x - start.x, cp1.y - start.y)
        + math.hypot(cp2.x - cp1.x, cp2.y - cp1.y)
        + math.hypot(end.x - cp2.x, end.y - cp2.y)
    )
    return PathSegment(
        start_point=start,
        end_point=end,
        control_points=[cp1, cp2],
        segment_type="cubic",
        length=length,
    )


def _create_quadratic_segment(start: Point, cp: Point, end: Point) -> PathSegment:
    length = math.hypot(cp.x - start.x, cp.y - start.y) + math.hypot(
        end.x - cp.x, end.y - cp.y
    )
    return PathSegment(
        start_point=start,
        end_point=end,
        control_points=[cp],
        segment_type="quadratic",
        length=length,
    )


__all__ = [
    "PathSamplingMethod",
    "PathSegment",
    "parse_path_segments",
    "fallback_horizontal_line",
    "sample_path_deterministic",
    "sample_path_proportional",
    "sample_segment_at_distance",
    "sample_segment",
]
