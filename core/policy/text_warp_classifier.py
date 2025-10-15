#!/usr/bin/env python3
"""
Text Path → DrawingML Warp Classifier

Translates sampled SVG text-path geometry into DrawingML ``a:prstTxWarp`` presets.
Implements heuristic detection for the common WordArt/warp families used by
PowerPoint, Google Slides, and LibreOffice.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from ..algorithms.curve_text_positioning import (
    PathSamplingMethod,
    create_curve_text_positioner,
    create_path_warp_fitter,
)
from ..ir.text_path import PathPoint, TextPathFrame, TextPathMethod, TextPathSide


@dataclass(frozen=True)
class PathFeatures:
    """Derived metrics that describe the sampled baseline geometry."""

    is_closed: bool
    point_count: int
    x_range: float
    y_range: float
    slope: float
    intercept: float
    slope_degrees: float
    curvature_sign_changes: int
    peak_count: int
    trough_count: int
    corner_count: int
    zero_crossings: int
    arc_command_count: int
    line_command_count: int
    command_counts: Counter[str]
    orientation: str
    amplitude: float
    mean_y: float
    std_y: float
    x_variance: float
    y_variance: float

    def aspect_ratio(self) -> float:
        """Return width/height aspect ratio (guarding against zero height)."""
        return self.x_range / max(self.y_range, 1e-6)


@dataclass
class ClassificationCandidate:
    """Intermediate scoring record."""

    preset: str
    confidence: float
    parameters: dict[str, Any]
    reason: str


def classify_text_path_warp(
    text_path: TextPathFrame,
    path_points: list[PathPoint],
    path_data: str | None = None,
) -> Optional[dict[str, Any]]:
    """
    Classify a sampled SVG text path into a DrawingML warp preset.

    Args:
        text_path: TextPathFrame describing the source SVG <textPath>.
        path_points: Equal-arc-length samples along the baseline.
        path_data: Original SVG ``d`` attribute, if available.

    Returns:
        Dict with keys ``preset``, ``confidence`` and optional ``parameters``
        when a preset warp is identified. ``None`` when the path should fall
        back to EMF/text-to-path.
    """
    if not path_points or len(path_points) < 4 or text_path is None:
        return None

    features = _compute_path_features(path_points, path_data)
    candidates: list[ClassificationCandidate] = []

    # Run parametric fits (arch, wave, bulge) for high-level cues.
    warp_fit = None
    if path_data:
        try:
            positioner = create_curve_text_positioner(PathSamplingMethod.DETERMINISTIC)
            warp_fitter = create_path_warp_fitter(positioner)
            warp_fit = warp_fitter.fit_path_to_warp(path_data, min_confidence=0.55)
        except Exception:
            warp_fit = None

    # Circle / ring detection ---------------------------------------------
    if features.is_closed and features.point_count >= 16:
        circle_conf = _score_circle(features)
        if circle_conf > 0.55:
            preset, confidence = _select_circle_preset(text_path, features, circle_conf)
            candidates.append(ClassificationCandidate(
                preset=preset,
                confidence=confidence,
                parameters={},
                reason="Closed near-circular baseline",
            ))

    # Arch / Curve families ------------------------------------------------
    arch_disabled = (
        features.curvature_sign_changes >= 2 and
        features.peak_count >= 1 and
        features.trough_count >= 1
    )
    if not arch_disabled:
        if warp_fit and warp_fit.preset_type == 'arch' and warp_fit.confidence >= 0.55:
            candidates.extend(_classify_arch_family(text_path, features, warp_fit))
        else:
            candidates.extend(_classify_arch_family(text_path, features, None))

    # Wave families --------------------------------------------------------
    if warp_fit and warp_fit.preset_type == 'wave' and warp_fit.confidence >= 0.55:
        candidates.extend(_classify_wave_family(text_path, features, warp_fit))
    else:
        candidates.extend(_classify_wave_family(text_path, features, None))

    # Bulge / inflate / deflate -------------------------------------------
    if warp_fit and warp_fit.preset_type == 'bulge' and warp_fit.confidence >= 0.55:
        candidates.extend(_classify_bulge_family(text_path, features, warp_fit))
    else:
        candidates.extend(_classify_bulge_family(text_path, features, None))

    # Linear / slant detection --------------------------------------------
    candidates.extend(_classify_slant_and_plain(text_path, features))

    # Polygonal baselines (triangle / chevron / stop / cascade) -----------
    candidates.extend(_classify_polygonal_shapes(text_path, features))

    # Button / can families (rounded rectangles & cylindrical forms) ------
    candidates.extend(_classify_button_and_can(text_path, features, path_data))

    # Fade variants (monotonic skew + baseline) ---------------------------
    fade_candidate = _classify_fade(text_path, features)
    if fade_candidate:
        candidates.append(fade_candidate)

    if not candidates:
        return None

    # Choose best candidate by confidence, biasing toward higher confidence.
    best = max(candidates, key=lambda c: c.confidence)
    if best.confidence < 0.55:
        return None

    return {
        'preset': best.preset,
        'confidence': min(best.confidence, 0.99),
        'parameters': best.parameters,
        'reason': best.reason,
        'features': {
            'is_closed': features.is_closed,
            'point_count': features.point_count,
            'aspect_ratio': features.aspect_ratio(),
            'peak_count': features.peak_count,
            'trough_count': features.trough_count,
            'corner_count': features.corner_count,
            'orientation': features.orientation,
        },
    }


# ----------------------------------------------------------------------
# Feature extraction helpers
# ----------------------------------------------------------------------

def _compute_path_features(path_points: list[PathPoint], path_data: str | None) -> PathFeatures:
    xs = [p.x for p in path_points]
    ys = [p.y for p in path_points]

    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    x_range = x_max - x_min
    y_range = y_max - y_min

    slope, intercept = _linear_regression(xs, ys)
    slope_degrees = math.degrees(math.atan(slope)) if not math.isclose(slope, 0.0, abs_tol=1e-6) else 0.0

    slopes = _pairwise_slopes(xs, ys)
    curvature_sign_changes = _count_sign_changes(slopes)

    peak_count, trough_count = _count_extrema(ys)
    corner_count = _count_corners(xs, ys)
    zero_crossings = _count_zero_crossings([y - sum(ys) / len(ys) for y in ys])

    is_closed = False
    if path_data:
        is_closed = bool(re.search(r'[Zz]', path_data.strip()))
    # Numeric closure fallback
    if not is_closed and len(path_points) >= 3:
        first = path_points[0]
        last = path_points[-1]
        dist = math.hypot(first.x - last.x, first.y - last.y)
        is_closed = dist < max(x_range, y_range) * 0.05

    command_counts = Counter()
    arc_count = line_count = 0
    if path_data:
        commands = re.findall(r'[MmLlHhVvCcSsQqTtAaZz]', path_data)
        command_counts.update(commands)
        arc_count = command_counts.get('A', 0) + command_counts.get('a', 0)
        line_count = sum(command_counts.get(cmd, 0) for cmd in ('L', 'l', 'H', 'h', 'V', 'v'))

    orientation = _determine_orientation(xs, ys)
    amplitude = y_range
    mean_y = sum(ys) / len(ys)
    std_y = _std_dev(ys, mean_y)
    x_variance = _variance(xs)
    y_variance = _variance(ys)

    return PathFeatures(
        is_closed=is_closed,
        point_count=len(path_points),
        x_range=x_range,
        y_range=y_range,
        slope=slope,
        intercept=intercept,
        slope_degrees=slope_degrees,
        curvature_sign_changes=curvature_sign_changes,
        peak_count=peak_count,
        trough_count=trough_count,
        corner_count=corner_count,
        zero_crossings=zero_crossings,
        arc_command_count=arc_count,
        line_command_count=line_count,
        command_counts=command_counts,
        orientation=orientation,
        amplitude=amplitude,
        mean_y=mean_y,
        std_y=std_y,
        x_variance=x_variance,
        y_variance=y_variance,
    )


def _linear_regression(xs: list[float], ys: list[float]) -> tuple[float, float]:
    n = len(xs)
    if n < 2:
        return 0.0, ys[0] if ys else 0.0

    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)

    denominator = (n * sum_x2) - (sum_x ** 2)
    if math.isclose(denominator, 0.0, abs_tol=1e-6):
        return 0.0, sum_y / n

    slope = ((n * sum_xy) - (sum_x * sum_y)) / denominator
    intercept = (sum_y - slope * sum_x) / n
    return slope, intercept


def _pairwise_slopes(xs: list[float], ys: list[float]) -> list[float]:
    slopes: list[float] = []
    for i in range(1, len(xs)):
        dx = xs[i] - xs[i - 1]
        dy = ys[i] - ys[i - 1]
        if math.isclose(dx, 0.0, abs_tol=1e-6):
            slopes.append(float('inf') if dy > 0 else float('-inf'))
        else:
            slopes.append(dy / dx)
    return slopes


def _count_sign_changes(values: Iterable[float], tolerance: float = 1e-4) -> int:
    count = 0
    prev_sign = 0
    for value in values:
        if math.isinf(value):
            sign = 1 if value > 0 else -1
        elif abs(value) <= tolerance:
            continue
        else:
            sign = 1 if value > 0 else -1
        if prev_sign and sign != prev_sign:
            count += 1
        prev_sign = sign
    return count


def _count_extrema(values: list[float]) -> tuple[int, int]:
    peaks = troughs = 0
    for i in range(1, len(values) - 1):
        prev_val = values[i - 1]
        curr_val = values[i]
        next_val = values[i + 1]
        if curr_val > prev_val and curr_val > next_val:
            peaks += 1
        elif curr_val < prev_val and curr_val < next_val:
            troughs += 1
    return peaks, troughs


def _count_corners(xs: list[float], ys: list[float], threshold_degrees: float = 25.0) -> int:
    if len(xs) < 3:
        return 0
    count = 0
    cos_threshold = math.cos(math.radians(threshold_degrees))

    for i in range(1, len(xs) - 1):
        v1x = xs[i] - xs[i - 1]
        v1y = ys[i] - ys[i - 1]
        v2x = xs[i + 1] - xs[i]
        v2y = ys[i + 1] - ys[i]

        mag1 = math.hypot(v1x, v1y)
        mag2 = math.hypot(v2x, v2y)
        if mag1 < 1e-6 or mag2 < 1e-6:
            continue

        dot = v1x * v2x + v1y * v2y
        cos_angle = max(-1.0, min(1.0, dot / (mag1 * mag2)))
        if cos_angle < cos_threshold:  # Sharp change
            count += 1
    return count


def _count_zero_crossings(values: Iterable[float], tolerance: float = 1e-6) -> int:
    count = 0
    prev_sign = 0
    for value in values:
        if abs(value) <= tolerance:
            continue
        sign = 1 if value > 0 else -1
        if prev_sign and sign != prev_sign:
            count += 1
        prev_sign = sign
    return count


def _determine_orientation(xs: list[float], ys: list[float]) -> str:
    if len(xs) < 3:
        return 'unknown'
    area = 0.0
    for i in range(len(xs) - 1):
        area += xs[i] * ys[i + 1] - xs[i + 1] * ys[i]
    area += xs[-1] * ys[0] - xs[0] * ys[-1]
    if math.isclose(area, 0.0, abs_tol=1e-6):
        return 'unknown'
    return 'ccw' if area > 0 else 'cw'


def _std_dev(values: list[float], mean: float) -> float:
    if len(values) < 2:
        return 0.0
    return math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))


def _variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / (len(values) - 1)


# ----------------------------------------------------------------------
# Classification helpers
# ----------------------------------------------------------------------

def _score_circle(features: PathFeatures) -> float:
    aspect_ratio = features.aspect_ratio()
    aspect_score = max(0.0, 1.0 - abs(1.0 - aspect_ratio))
    curvature_score = 1.0 - min(1.0, features.corner_count / max(features.point_count / 4, 1))
    score = (aspect_score * 0.7) + (curvature_score * 0.3)

    if features.arc_command_count >= 1 and features.is_closed:
        score = max(score, 0.75)

    return score


def _select_circle_preset(text_path: TextPathFrame, features: PathFeatures, base_conf: float) -> tuple[str, float]:
    side = getattr(text_path, 'side', TextPathSide.LEFT)
    direction = features.orientation
    method = getattr(text_path, 'method', TextPathMethod.ALIGN)

    pour_bonus = 0.05 if method == TextPathMethod.STRETCH else 0.0

    if direction in ('unknown',):
        return ('textCircle', base_conf - 0.05)

    inside = (direction == 'ccw' and side == TextPathSide.LEFT) or (direction == 'cw' and side == TextPathSide.RIGHT)

    if inside:
        preset = 'textRingInside'
    else:
        preset = 'textRingOutside'

    # For pour variants prefer when stretch layout is requested.
    if method == TextPathMethod.STRETCH:
        if inside:
            preset = 'textCirclePour'
        else:
            preset = 'textButtonPour'
    elif features.aspect_ratio() < 1.2 and inside:
        preset = 'textCircle'

    return preset, min(0.95, base_conf + pour_bonus)


def _classify_arch_family(
    text_path: TextPathFrame,
    features: PathFeatures,
    warp_fit,
) -> list[ClassificationCandidate]:
    candidates: list[ClassificationCandidate] = []
    if features.y_range < 1e-3:
        return candidates

    height_ratio = features.y_range / max(features.x_range, 1e-6)
    method = getattr(text_path, 'method', TextPathMethod.ALIGN)
    pour = (method == TextPathMethod.STRETCH)

    direction_up = True
    if warp_fit and 'direction' in warp_fit.parameters:
        direction_up = warp_fit.parameters['direction'] == 'up'
    else:
        direction_up = features.mean_y >= min(features.mean_y, features.y_range / 2)
        mid_index = len(text_path.runs) // 2 if len(text_path.runs) else 0
        if mid_index and len(text_path.runs) > mid_index:
            direction_up = features.peak_count >= features.trough_count
        else:
            # Evaluate midpoint of the sampled path
            direction_up = True

    preset = None
    if height_ratio >= 0.35:
        preset = 'textArchUp' if direction_up else 'textArchDown'
    elif height_ratio >= 0.15:
        preset = 'textCurveUp' if direction_up else 'textCurveDown'
    else:
        preset = 'textPlain'

    confidence = 0.65 + min(0.2, height_ratio)
    if pour and preset.startswith('textArch'):
        preset = preset + 'Pour'
        confidence += 0.05

    if preset != 'textPlain':
        candidates.append(ClassificationCandidate(
            preset=preset,
            confidence=min(confidence, 0.9),
            parameters={},
            reason="Single-arch curvature detected",
        ))

    return candidates


def _classify_wave_family(
    text_path: TextPathFrame,
    features: PathFeatures,
    warp_fit,
) -> list[ClassificationCandidate]:
    candidates: list[ClassificationCandidate] = []
    cycles = max(min(features.peak_count, features.trough_count), features.zero_crossings // 2)
    if cycles == 0 and warp_fit:
        cycles = max(1, round(features.zero_crossings / 2))

    if cycles == 0 and (warp_fit is None or warp_fit.confidence < 0.55):
        return candidates

    if cycles >= 3:
        preset = 'textWave4'
    elif cycles == 2:
        preset = 'textWave2'
    else:
        preset = 'textWave1'

    confidence = 0.6 + min(0.25, cycles * 0.1)

    # Double wave heuristic: strong alternating amplitude with high zero crossings
    if features.zero_crossings >= 5 and features.std_y > 0 and features.std_y < features.y_range * 0.6:
        candidates.append(ClassificationCandidate(
            preset='textDoubleWave1',
            confidence=min(confidence - 0.05, 0.85),
            parameters={},
            reason="Alternating dual-rail wave profile",
        ))

    candidates.append(ClassificationCandidate(
        preset=preset,
        confidence=min(confidence, 0.9),
        parameters={},
        reason="Periodic wave curvature detected",
    ))
    return candidates


def _classify_bulge_family(
    text_path: TextPathFrame,
    features: PathFeatures,
    warp_fit,
) -> list[ClassificationCandidate]:
    candidates: list[ClassificationCandidate] = []
    if warp_fit is None or warp_fit.preset_type != 'bulge':
        # Heuristic fallback: strong quadratic curvature with zero sign changes.
        if features.curvature_sign_changes <= 1 and features.y_range > features.x_range * 0.2:
            direction_up = features.peak_count >= features.trough_count
            preset = 'textInflate' if direction_up else 'textDeflate'
            candidates.append(ClassificationCandidate(
                preset=preset,
                confidence=0.6,
                parameters={},
                reason="Monotonic bulge curvature",
            ))
        return candidates

    curvature = warp_fit.parameters.get('curvature', 0.0)
    direction = 'up' if curvature >= 0 else 'down'
    magnitude = abs(curvature)

    if magnitude < 1e-4:
        return candidates

    if direction == 'up':
        base_preset = 'textInflate'
    else:
        base_preset = 'textDeflate'

    # Determine top/bottom variants based on peak location.
    peak_variant = _peak_region(features)
    if peak_variant == 'top':
        preset = base_preset + 'Top'
    elif peak_variant == 'bottom':
        preset = base_preset + 'Bottom'
    else:
        preset = base_preset

    confidence = min(0.9, 0.6 + min(0.3, magnitude * 5))
    candidates.append(ClassificationCandidate(
        preset=preset,
        confidence=confidence,
        parameters={},
        reason="Quadratic bulge fit",
    ))

    # If we have alternating compression, expose combination presets.
    if features.curvature_sign_changes >= 2:
        combo = 'textDeflateInflate' if direction == 'down' else 'textDeflateInflateDeflate'
        candidates.append(ClassificationCandidate(
            preset=combo,
            confidence=confidence - 0.1,
            parameters={},
            reason="Multi-phase bulge curvature",
        ))

    return candidates


def _peak_region(features: PathFeatures) -> str:
    """Determine where the primary peak occurs (top/middle/bottom)."""
    if features.peak_count == 0 and features.trough_count == 0:
        return 'middle'
    if features.mean_y > 0:
        return 'top'
    if features.mean_y < 0:
        return 'bottom'
    return 'middle'


def _classify_slant_and_plain(
    text_path: TextPathFrame,
    features: PathFeatures,
) -> list[ClassificationCandidate]:
    candidates: list[ClassificationCandidate] = []
    if features.is_closed or features.arc_command_count > 0:
        return candidates

    slope_abs = abs(features.slope_degrees)
    y_variation_small = features.y_range <= features.x_range * 0.05

    if y_variation_small and slope_abs >= 5:
        if features.slope > 0:
            preset = 'textSlantUp'
        else:
            preset = 'textSlantDown'
        confidence = min(0.8, 0.6 + slope_abs / 40.0)
        candidates.append(ClassificationCandidate(
            preset=preset,
            confidence=confidence,
            parameters={},
            reason="Linear baseline with consistent slope",
        ))
    elif features.y_range <= features.x_range * 0.02:
        candidates.append(ClassificationCandidate(
            preset='textPlain',
            confidence=0.9,
            parameters={},
            reason="Nearly flat baseline",
        ))

    return candidates


def _classify_polygonal_shapes(
    text_path: TextPathFrame,
    features: PathFeatures,
) -> list[ClassificationCandidate]:
    candidates: list[ClassificationCandidate] = []
    if features.corner_count == 0:
        return candidates

    if features.corner_count in (2, 3) and not features.is_closed:
        # Likely triangle or chevron.
        if features.peak_count == 1 and features.trough_count == 0:
            preset = 'textTriangle'
            if features.mean_y < 0:
                preset = 'textTriangleInverted'
            candidates.append(ClassificationCandidate(
                preset=preset,
                confidence=0.7,
                parameters={},
                reason="Piecewise-linear apex baseline",
            ))
        else:
            preset = 'textChevron'
            if features.mean_y < 0:
                preset = 'textChevronInverted'
            candidates.append(ClassificationCandidate(
                preset=preset,
                confidence=0.65,
                parameters={},
                reason="Piecewise-linear chevron baseline",
            ))

    if features.is_closed and features.corner_count >= 6:
        candidates.append(ClassificationCandidate(
            preset='textStop',
            confidence=0.65,
            parameters={},
            reason="Closed polygonal baseline with many corners",
        ))

    if features.line_command_count >= 2 and features.zero_crossings <= 1 and features.corner_count >= 2:
        candidates.append(ClassificationCandidate(
            preset='textCascadeUp' if features.mean_y > 0 else 'textCascadeDown',
            confidence=0.6,
            parameters={},
            reason="Step-like baseline detected",
        ))

    return candidates


def _classify_button_and_can(
    text_path: TextPathFrame,
    features: PathFeatures,
    path_data: str | None,
) -> list[ClassificationCandidate]:
    candidates: list[ClassificationCandidate] = []
    method = getattr(text_path, 'method', TextPathMethod.ALIGN)
    pour = method == TextPathMethod.STRETCH

    if features.is_closed and features.arc_command_count >= 1:
        preset = 'textButtonPour' if pour else 'textButton'
        candidates.append(ClassificationCandidate(
            preset=preset,
            confidence=0.65,
            parameters={},
            reason="Closed rounded baseline",
        ))

    if not features.is_closed and features.arc_command_count >= 1 and features.y_range > features.x_range * 0.4:
        direction_up = features.peak_count >= features.trough_count
        preset = 'textCanUp' if direction_up else 'textCanDown'
        candidates.append(ClassificationCandidate(
            preset=preset,
            confidence=0.6,
            parameters={},
            reason="Cylindrical arc baseline",
        ))

    return candidates


def _classify_fade(
    text_path: TextPathFrame,
    features: PathFeatures,
) -> ClassificationCandidate | None:
    y_dominant = features.y_range > features.x_range * 0.5
    x_dominant = features.x_range > features.y_range * 0.5

    if not (y_dominant or x_dominant):
        return None

    if y_dominant and features.slope_degrees > 20:
        preset = 'textFadeUp'
    elif y_dominant and features.slope_degrees < -20:
        preset = 'textFadeDown'
    elif x_dominant and features.slope > 0:
        preset = 'textFadeRight'
    elif x_dominant and features.slope < 0:
        preset = 'textFadeLeft'
    else:
        return None

    return ClassificationCandidate(
        preset=preset,
        confidence=0.58,
        parameters={},
        reason="Monotonic baseline suitable for fade preset",
    )
