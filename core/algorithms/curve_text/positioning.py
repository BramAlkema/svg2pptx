"""High-level curve text positioning orchestrator."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Iterable, Sequence

from ...ir.text_path import PathPoint
from .curve_sampling import (
    PathSamplingMethod,
    fallback_horizontal_line,
    parse_path_segments,
    sample_path_deterministic,
    sample_path_proportional,
)
from .bezier_utils import interpolate_angle


@dataclass
class CurveTextPositioner:
    sampling_method: PathSamplingMethod = PathSamplingMethod.ADAPTIVE
    default_samples_per_unit: float = 0.5

    def __post_init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def sample_path_for_text(
        self,
        path_data: str,
        num_samples: int | None = None,
    ) -> list[PathPoint]:
        try:
            segments = parse_path_segments(path_data)
            if not segments:
                return fallback_horizontal_line(num_samples or 2)

            total_length = sum(segment.length for segment in segments)
            if total_length == 0:
                return fallback_horizontal_line(num_samples or 2)

            if num_samples is None:
                estimated = int(total_length * self.default_samples_per_unit)
                if self.sampling_method == PathSamplingMethod.DETERMINISTIC:
                    num_samples = max(2, min(4096, estimated))
                else:
                    num_samples = max(20, min(200, estimated))

            if self.sampling_method == PathSamplingMethod.DETERMINISTIC:
                return sample_path_deterministic(segments, total_length, num_samples)
            return sample_path_proportional(segments, total_length, num_samples)

        except Exception as exc:  # noqa: BLE001
            self.logger.warning("Path sampling failed: %s", exc)
            return fallback_horizontal_line(num_samples or 2)

    def find_point_at_distance(
        self,
        path_points: list[PathPoint],
        target_distance: float,
    ) -> PathPoint | None:
        if not path_points:
            return None
        if target_distance <= path_points[0].distance_along_path:
            return path_points[0]
        if target_distance >= path_points[-1].distance_along_path:
            return path_points[-1]

        for i in range(len(path_points) - 1):
            curr_point = path_points[i]
            next_point = path_points[i + 1]
            if curr_point.distance_along_path <= target_distance <= next_point.distance_along_path:
                distance_range = next_point.distance_along_path - curr_point.distance_along_path
                if distance_range > 0:
                    t = (target_distance - curr_point.distance_along_path) / distance_range
                    x = curr_point.x + t * (next_point.x - curr_point.x)
                    y = curr_point.y + t * (next_point.y - curr_point.y)
                    angle = interpolate_angle(curr_point.tangent_angle, next_point.tangent_angle, t)
                    return PathPoint(x=x, y=y, tangent_angle=angle, distance_along_path=target_distance)
                return curr_point
        return None

    def calculate_path_curvature(
        self,
        path_points: list[PathPoint],
        point_index: int,
    ) -> float:
        if len(path_points) < 3 or point_index < 1 or point_index >= len(path_points) - 1:
            return 0.0
        p1 = path_points[point_index - 1]
        p2 = path_points[point_index]
        p3 = path_points[point_index + 1]
        v1 = (p2.x - p1.x, p2.y - p1.y)
        v2 = (p3.x - p2.x, p3.y - p2.y)
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        mag1 = math.hypot(*v1)
        mag2 = math.hypot(*v2)
        if mag1 * mag2 > 0:
            return abs(cross) / (mag1 * mag2)
        return 0.0


def create_curve_text_positioner(
    sampling_method: PathSamplingMethod = PathSamplingMethod.ADAPTIVE,
) -> CurveTextPositioner:
    return CurveTextPositioner(sampling_method=sampling_method)


__all__ = ["CurveTextPositioner", "create_curve_text_positioner"]
