"""WordArt warp fitting routines for curve text positioning."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Dict, List

from ...ir.text_path import PathPoint
from .curve_sampling import PathSamplingMethod
from .positioning import CurveTextPositioner, create_curve_text_positioner


@dataclass
class WarpFitResult:
    preset_type: str
    confidence: float
    error_metric: float
    parameters: Dict[str, float]
    fit_quality: str


class PathWarpFitter:
    EXCELLENT_THRESHOLD = 0.95
    GOOD_THRESHOLD = 0.80
    FAIR_THRESHOLD = 0.60

    def __init__(self, positioner: CurveTextPositioner | None = None) -> None:
        self.positioner = positioner or create_curve_text_positioner(PathSamplingMethod.DETERMINISTIC)
        self.logger = logging.getLogger(__name__)

    def fit_path_to_warp(self, path_data: str, min_confidence: float = 0.60) -> WarpFitResult:
        samples = self.positioner.sample_path_for_text(path_data, num_samples=50)
        if len(samples) < 10:
            return self._no_fit_result("Insufficient path samples")

        arch_fit = self._fit_arch(samples)
        wave_fit = self._fit_wave(samples)
        bulge_fit = self._fit_bulge(samples)

        best_fit = max([arch_fit, wave_fit, bulge_fit], key=lambda f: f.confidence)
        if best_fit.confidence < min_confidence:
            return self._no_fit_result("Below confidence threshold")

        best_fit.fit_quality = self._classify_fit_quality(best_fit.confidence)
        return best_fit

    def _fit_arch(self, samples: List[PathPoint]) -> WarpFitResult:
        if len(samples) < 3:
            return WarpFitResult('arch', 0.0, float('inf'), {}, 'poor')
        try:
            points = [(p.x, p.y) for p in samples]
            circle_result = self._fit_circle(points)
            ellipse_result = self._fit_ellipse(points)
            if circle_result['confidence'] > ellipse_result['confidence']:
                params = {
                    'shape': 'circle',
                    'radius': circle_result['radius'],
                    'center_x': circle_result['center_x'],
                    'center_y': circle_result['center_y'],
                    'direction': self._determine_arch_direction(samples),
                }
                return WarpFitResult('arch', circle_result['confidence'], circle_result['error'], params, 'unknown')
            params = {
                'shape': 'ellipse',
                'radius_x': ellipse_result['radius_x'],
                'radius_y': ellipse_result['radius_y'],
                'center_x': ellipse_result['center_x'],
                'center_y': ellipse_result['center_y'],
                'direction': self._determine_arch_direction(samples),
            }
            return WarpFitResult('arch', ellipse_result['confidence'], ellipse_result['error'], params, 'unknown')
        except Exception as exc:  # noqa: BLE001
            self.logger.debug("Arch fitting failed: %s", exc)
            return WarpFitResult('arch', 0.0, float('inf'), {}, 'poor')

    def _fit_wave(self, samples: List[PathPoint]) -> WarpFitResult:
        if len(samples) < 5:
            return WarpFitResult('wave', 0.0, float('inf'), {}, 'poor')
        try:
            points = [(p.x, p.y) for p in samples]
            x_values = [p[0] for p in points]
            y_values = [p[1] for p in points]
            baseline = self._fit_linear_baseline(x_values, y_values)
            detrended = [y - (baseline['slope'] * x + baseline['intercept']) for x, y in points]
            wave_params = self._estimate_wave_parameters(x_values, detrended)
            predicted = [
                wave_params['amplitude'] * math.sin(2 * math.pi * wave_params['frequency'] * x + wave_params['phase'])
                + baseline['slope'] * x
                + baseline['intercept']
                for x in x_values
            ]
            rms_error = math.sqrt(sum((actual - pred) ** 2 for actual, pred in zip(y_values, predicted)) / len(y_values))
            y_range = max(y_values) - min(y_values)
            confidence = max(0.0, 1.0 - (rms_error / max(y_range, 1.0)))
            params = {
                'amplitude': wave_params['amplitude'],
                'frequency': wave_params['frequency'],
                'phase': wave_params['phase'],
                'baseline_slope': baseline['slope'],
                'baseline_intercept': baseline['intercept'],
            }
            return WarpFitResult('wave', confidence, rms_error, params, 'unknown')
        except Exception as exc:  # noqa: BLE001
            self.logger.debug("Wave fitting failed: %s", exc)
            return WarpFitResult('wave', 0.0, float('inf'), {}, 'poor')

    def _fit_bulge(self, samples: List[PathPoint]) -> WarpFitResult:
        if len(samples) < 3:
            return WarpFitResult('bulge', 0.0, float('inf'), {}, 'poor')
        try:
            points = [(p.x, p.y) for p in samples]
            x_values = [p[0] for p in points]
            y_values = [p[1] for p in points]
            params = self._fit_quadratic(x_values, y_values)
            predicted = [params['a'] * x ** 2 + params['b'] * x + params['c'] for x in x_values]
            rms_error = math.sqrt(sum((actual - pred) ** 2 for actual, pred in zip(y_values, predicted)) / len(y_values))
            y_range = max(y_values) - min(y_values)
            confidence = max(0.0, 1.0 - (rms_error / max(y_range, 1.0)))
            params_out = {
                'curvature': params['a'],
                'slope': params['b'],
                'offset': params['c'],
                'direction': 'up' if params['a'] > 0 else 'down',
            }
            return WarpFitResult('bulge', confidence, rms_error, params_out, 'unknown')
        except Exception as exc:  # noqa: BLE001
            self.logger.debug("Bulge fitting failed: %s", exc)
            return WarpFitResult('bulge', 0.0, float('inf'), {}, 'poor')

    @staticmethod
    def _fit_circle(points: List[tuple[float, float]]) -> dict[str, float]:
        n = len(points)
        cx = sum(p[0] for p in points) / n
        cy = sum(p[1] for p in points) / n
        radii = [math.hypot(p[0] - cx, p[1] - cy) for p in points]
        avg_radius = sum(radii) / n
        error = math.sqrt(sum((r - avg_radius) ** 2 for r in radii) / n)
        radius_variance = error / max(avg_radius, 1.0)
        confidence = max(0.0, 1.0 - radius_variance)
        return {
            'center_x': cx,
            'center_y': cy,
            'radius': avg_radius,
            'error': error,
            'confidence': confidence,
        }

    @staticmethod
    def _fit_ellipse(points: List[tuple[float, float]]) -> dict[str, float]:
        circle_fit = PathWarpFitter._fit_circle(points)
        return {
            'center_x': circle_fit['center_x'],
            'center_y': circle_fit['center_y'],
            'radius_x': circle_fit['radius'],
            'radius_y': circle_fit['radius'],
            'error': circle_fit['error'],
            'confidence': min(1.0, circle_fit['confidence'] * 1.1),
        }

    @staticmethod
    def _fit_linear_baseline(x_values: List[float], y_values: List[float]) -> dict[str, float]:
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        slope = (n * sum_xy - sum_x * sum_y) / max(n * sum_x2 - sum_x * sum_x, 1.0)
        intercept = (sum_y - slope * sum_x) / max(n, 1)
        return {'slope': slope, 'intercept': intercept}

    @staticmethod
    def _estimate_wave_parameters(x_values: List[float], y_values: List[float]) -> dict[str, float]:
        if not y_values:
            return {'amplitude': 0.0, 'frequency': 0.0, 'phase': 0.0}
        amplitude = (max(y_values) - min(y_values)) / 2
        zero_crossings = sum(1 for i in range(1, len(y_values)) if y_values[i - 1] * y_values[i] < 0)
        x_range = max(x_values) - min(x_values)
        if x_range > 0 and zero_crossings > 1:
            frequency = zero_crossings / (2 * x_range)
        else:
            frequency = 1.0 / max(x_range, 1.0)
        return {'amplitude': amplitude, 'frequency': frequency, 'phase': 0.0}

    @staticmethod
    def _fit_quadratic(x_values: List[float], y_values: List[float]) -> dict[str, float]:
        n = len(x_values)
        sum_x = sum(x_values)
        sum_x2 = sum(x * x for x in x_values)
        sum_x3 = sum(x * x * x for x in x_values)
        sum_x4 = sum(x * x * x * x for x in x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2y = sum(x * x * y for x, y in zip(x_values, y_values))
        denom = (n * sum_x2 * sum_x4 + 2 * sum_x * sum_x2 * sum_x3 - sum_x2 ** 3 - n * sum_x3 ** 2 - sum_x ** 2 * sum_x4)
        if denom == 0:
            return {'a': 0.0, 'b': 0.0, 'c': sum_y / max(n, 1)}
        a = (
            (sum_y * sum_x2 * sum_x4 + sum_x * sum_x3 * sum_xy + sum_x * sum_x2 * sum_x2y
             - sum_x2 * sum_x2 * sum_xy - sum_y * sum_x3 ** 2 - sum_x * sum_x4 * sum_x2y)
            / denom
        )
        b = (
            (n * sum_x3 * sum_x2y + sum_x * sum_x2 * sum_y + sum_x * sum_x3 * sum_xy
             - sum_x2 ** 2 * sum_y - n * sum_x4 * sum_xy - sum_x ** 2 * sum_x2y)
            / denom
        )
        c = (
            (n * sum_x2 * sum_xy + sum_x * sum_x3 * sum_y + sum_x * sum_x2 * sum_xy
             - sum_x2 ** 2 * sum_y - n * sum_x3 * sum_x2y - sum_x ** 2 * sum_xy)
            / denom
        )
        return {'a': a, 'b': b, 'c': c}

    @staticmethod
    def _determine_arch_direction(samples: List[PathPoint]) -> str:
        if len(samples) < 3:
            return 'up'
        start_y = samples[0].y
        end_y = samples[-1].y
        mid_y = samples[len(samples) // 2].y
        baseline_y = (start_y + end_y) / 2
        return 'up' if mid_y > baseline_y else 'down'

    def _classify_fit_quality(self, confidence: float) -> str:
        if confidence >= self.EXCELLENT_THRESHOLD:
            return 'excellent'
        if confidence >= self.GOOD_THRESHOLD:
            return 'good'
        if confidence >= self.FAIR_THRESHOLD:
            return 'fair'
        return 'poor'

    @staticmethod
    def _no_fit_result(reason: str) -> WarpFitResult:
        return WarpFitResult('none', 0.0, float('inf'), {'reason': reason}, 'poor')


def create_path_warp_fitter(positioner: CurveTextPositioner | None = None) -> PathWarpFitter:
    return PathWarpFitter(positioner)


__all__ = ["WarpFitResult", "PathWarpFitter", "create_path_warp_fitter"]
