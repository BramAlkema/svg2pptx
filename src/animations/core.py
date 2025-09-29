#!/usr/bin/env python3
"""
Core Animation Types and Data Models

This module provides fundamental data types, enums, and data classes for the
SVG2PPTX animation system. Following ADR-006 animation system architecture.

Key Features:
- Core animation types and enums
- Animation timing and keyframe data models
- Clean data structures without business logic
- Type-safe animation definitions
"""

from typing import List, Dict, Optional, Union, Any
from dataclasses import dataclass, field
from enum import Enum


class AnimationType(Enum):
    """SVG animation types."""
    ANIMATE = "animate"
    ANIMATE_TRANSFORM = "animateTransform"
    ANIMATE_COLOR = "animateColor"
    ANIMATE_MOTION = "animateMotion"
    SET = "set"


class FillMode(Enum):
    """Animation fill modes."""
    REMOVE = "remove"
    FREEZE = "freeze"


class TransformType(Enum):
    """Transform animation types."""
    TRANSLATE = "translate"
    SCALE = "scale"
    ROTATE = "rotate"
    SKEWX = "skewX"
    SKEWY = "skewY"
    MATRIX = "matrix"


class CalcMode(Enum):
    """Animation calculation modes."""
    LINEAR = "linear"
    DISCRETE = "discrete"
    PACED = "paced"
    SPLINE = "spline"


@dataclass
class AnimationTiming:
    """Animation timing information."""
    begin: float = 0.0
    duration: float = 1.0
    repeat_count: Union[int, str] = 1
    fill_mode: FillMode = FillMode.REMOVE

    def get_end_time(self) -> float:
        """Calculate animation end time."""
        if self.repeat_count == "indefinite":
            return float('inf')
        try:
            count = int(self.repeat_count)
            return self.begin + (self.duration * count)
        except (ValueError, TypeError):
            return self.begin + self.duration

    def is_active_at_time(self, time: float) -> bool:
        """Check if animation is active at given time."""
        if time < self.begin:
            return False
        end_time = self.get_end_time()
        if end_time == float('inf'):
            return True
        return time <= end_time

    def get_local_time(self, global_time: float) -> float:
        """Convert global time to local animation time (0-1)."""
        if global_time < self.begin:
            return 0.0

        local_time = global_time - self.begin

        if self.repeat_count == "indefinite":
            # For indefinite animations, cycle within duration
            return (local_time % self.duration) / self.duration

        try:
            count = int(self.repeat_count)
            total_duration = self.duration * count
            if local_time >= total_duration:
                return 1.0 if self.fill_mode == FillMode.FREEZE else 0.0

            # Calculate position within current cycle
            cycle_time = local_time % self.duration
            return cycle_time / self.duration
        except (ValueError, TypeError):
            if local_time >= self.duration:
                return 1.0 if self.fill_mode == FillMode.FREEZE else 0.0
            return local_time / self.duration


@dataclass
class AnimationKeyframe:
    """Single keyframe with time, values, and easing."""
    time: float
    values: List[str]
    easing: Optional[str] = None

    def __post_init__(self):
        """Validate keyframe data."""
        if not 0.0 <= self.time <= 1.0:
            raise ValueError(f"Keyframe time must be between 0 and 1, got {self.time}")
        if not self.values:
            raise ValueError("Keyframe must have at least one value")


@dataclass
class AnimationDefinition:
    """Complete animation definition."""
    element_id: str
    animation_type: AnimationType
    target_attribute: str
    values: List[str]
    timing: AnimationTiming
    key_times: Optional[List[float]] = None
    key_splines: Optional[List[List[float]]] = None
    calc_mode: CalcMode = CalcMode.LINEAR
    transform_type: Optional[TransformType] = None
    additive: str = "replace"
    accumulate: str = "none"

    def __post_init__(self):
        """Validate animation definition."""
        if not self.element_id:
            raise ValueError("Element ID is required")
        if not self.target_attribute:
            raise ValueError("Target attribute is required")
        if not self.values:
            raise ValueError("Animation must have at least one value")

        # Validate key_times if provided
        if self.key_times:
            if len(self.key_times) != len(self.values):
                raise ValueError("key_times length must match values length")
            if not all(0.0 <= t <= 1.0 for t in self.key_times):
                raise ValueError("All key_times must be between 0 and 1")
            if self.key_times != sorted(self.key_times):
                raise ValueError("key_times must be in ascending order")

        # Validate key_splines if provided
        if self.key_splines:
            calc_mode_value = self.calc_mode.value if isinstance(self.calc_mode, CalcMode) else self.calc_mode
            if calc_mode_value != "spline":
                raise ValueError("key_splines only valid with spline calc_mode")
            expected_count = len(self.values) - 1
            if len(self.key_splines) != expected_count:
                raise ValueError(f"Expected {expected_count} key_splines, got {len(self.key_splines)}")
            for spline in self.key_splines:
                if len(spline) != 4:
                    raise ValueError("Each key_spline must have exactly 4 values")
                if not all(0.0 <= v <= 1.0 for v in spline):
                    raise ValueError("All key_spline values must be between 0 and 1")

    def get_keyframes(self) -> List[AnimationKeyframe]:
        """Generate keyframes from animation definition."""
        if self.key_times:
            # Use explicit key times
            keyframes = []
            for i, (time, value) in enumerate(zip(self.key_times, self.values)):
                easing = None
                if self.key_splines and i < len(self.key_splines):
                    spline = self.key_splines[i]
                    easing = f"cubic-bezier({spline[0]}, {spline[1]}, {spline[2]}, {spline[3]})"
                keyframes.append(AnimationKeyframe(time, [value], easing))
            return keyframes
        else:
            # Generate evenly spaced key times
            if len(self.values) == 1:
                return [AnimationKeyframe(0.0, self.values)]

            keyframes = []
            for i, value in enumerate(self.values):
                time = i / (len(self.values) - 1)
                easing = None
                if self.key_splines and i < len(self.key_splines):
                    spline = self.key_splines[i]
                    easing = f"cubic-bezier({spline[0]}, {spline[1]}, {spline[2]}, {spline[3]})"
                keyframes.append(AnimationKeyframe(time, [value], easing))
            return keyframes

    def is_transform_animation(self) -> bool:
        """Check if this is a transform animation."""
        return self.animation_type == AnimationType.ANIMATE_TRANSFORM

    def is_motion_animation(self) -> bool:
        """Check if this is a motion animation."""
        return self.animation_type == AnimationType.ANIMATE_MOTION

    def is_color_animation(self) -> bool:
        """Check if this animates color properties."""
        return (self.animation_type == AnimationType.ANIMATE_COLOR or
                (self.animation_type == AnimationType.ANIMATE and
                 self.target_attribute in ['fill', 'stroke', 'stop-color']))

    def get_value_at_time(self, time: float) -> Any:
        """Get interpolated value at specific time."""
        # Handle time before animation starts
        if time < self.timing.begin:
            return self.values[0] if self.values else None

        # Handle time after animation ends
        duration = self.timing.duration
        if time >= self.timing.begin + duration:
            return self.values[-1] if self.values else None

        # Calculate relative time within animation
        relative_time = (time - self.timing.begin) / duration

        # Apply easing if calc_mode is spline or discrete
        calc_mode_value = self.calc_mode.value if isinstance(self.calc_mode, CalcMode) else self.calc_mode
        if (calc_mode_value == "spline" and self.key_splines) or calc_mode_value == "discrete":
            relative_time = self._apply_easing(relative_time)

        # Interpolate between values
        return self._interpolate_value(relative_time)

    def _apply_easing(self, t: float) -> float:
        """Apply easing function based on calc_mode and key_splines."""
        # Handle both enum and string values for calc_mode
        calc_mode_value = self.calc_mode.value if isinstance(self.calc_mode, CalcMode) else self.calc_mode

        if calc_mode_value == "linear":
            return t
        elif calc_mode_value == "discrete":
            # Discrete steps
            if not self.key_times:
                # For discrete mode without key_times, use threshold at 0.5
                return 0.0 if t < 0.5 else 1.0
            for i, key_time in enumerate(self.key_times[1:], 1):
                if t <= key_time:
                    return self.key_times[i-1]
            return 1.0
        elif calc_mode_value == "spline" and self.key_splines:
            # Bezier easing using keySplines
            return self._apply_bezier_easing(t)
        else:
            return t

    def _apply_bezier_easing(self, t: float) -> float:
        """Apply cubic bezier easing from keySplines."""
        if not self.key_splines or not self.key_times:
            return t

        # Find the segment for this time
        for i in range(len(self.key_times) - 1):
            if t <= self.key_times[i + 1]:
                segment_start = self.key_times[i]
                segment_end = self.key_times[i + 1]
                segment_t = (t - segment_start) / (segment_end - segment_start)

                # Apply bezier curve from corresponding keySpline
                if i < len(self.key_splines):
                    spline = self.key_splines[i]
                    return self._cubic_bezier(segment_t, spline[0], spline[1], spline[2], spline[3])

        return t

    def _cubic_bezier(self, t: float, x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate cubic bezier curve value."""
        # Simplified bezier calculation for easing
        # This is a basic implementation - could be enhanced with more precision
        return 3 * (1 - t)**2 * t * y1 + 3 * (1 - t) * t**2 * y2 + t**3

    def _interpolate_value(self, t: float) -> Any:
        """Interpolate between animation values."""
        if not self.values:
            return None

        if len(self.values) == 1:
            return self.values[0]

        # Find values to interpolate between
        if self.key_times:
            # Use key_times for precise interpolation
            for i in range(len(self.key_times) - 1):
                if t <= self.key_times[i + 1]:
                    start_val = self.values[i] if i < len(self.values) else self.values[-1]
                    end_val = self.values[i + 1] if i + 1 < len(self.values) else self.values[-1]

                    segment_t = (t - self.key_times[i]) / (self.key_times[i + 1] - self.key_times[i])
                    return self._lerp_values(start_val, end_val, segment_t)
        else:
            # Linear interpolation across all values
            scaled_t = t * (len(self.values) - 1)
            index = int(scaled_t)
            fraction = scaled_t - index

            if index >= len(self.values) - 1:
                return self.values[-1]

            return self._lerp_values(self.values[index], self.values[index + 1], fraction)

        return self.values[-1]

    def _lerp_values(self, start: Any, end: Any, t: float) -> Any:
        """Linear interpolation between two values."""
        # Handle numeric values
        try:
            start_num = float(start)
            end_num = float(end)
            return start_num + (end_num - start_num) * t
        except (ValueError, TypeError):
            # Handle non-numeric values (colors, transforms, etc.)
            # For now, return discrete values
            return start if t < 0.5 else end


@dataclass
class AnimationScene:
    """Snapshot of all animated elements at specific time."""
    time: float
    element_states: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def set_element_property(self, element_id: str, property_name: str, value: str):
        """Set property value for an element."""
        if element_id not in self.element_states:
            self.element_states[element_id] = {}
        self.element_states[element_id][property_name] = value

    def get_element_property(self, element_id: str, property_name: str) -> Optional[str]:
        """Get property value for an element."""
        return self.element_states.get(element_id, {}).get(property_name)

    def get_all_animated_elements(self) -> List[str]:
        """Get list of all elements that have animations."""
        return list(self.element_states.keys())

    def merge_scene(self, other: 'AnimationScene'):
        """Merge another scene into this one (other takes precedence)."""
        for element_id, properties in other.element_states.items():
            if element_id not in self.element_states:
                self.element_states[element_id] = {}
            self.element_states[element_id].update(properties)


def format_transform_string(transform_type: TransformType, values: List[float]) -> str:
    """Format transform values into SVG transform string."""
    if transform_type == TransformType.TRANSLATE:
        if len(values) == 1:
            return f"translate({values[0]})"
        elif len(values) == 2:
            return f"translate({values[0]}, {values[1]})"
        else:
            raise ValueError("translate requires 1 or 2 values")

    elif transform_type == TransformType.SCALE:
        if len(values) == 1:
            return f"scale({values[0]})"
        elif len(values) == 2:
            return f"scale({values[0]}, {values[1]})"
        else:
            raise ValueError("scale requires 1 or 2 values")

    elif transform_type == TransformType.ROTATE:
        if len(values) == 1:
            return f"rotate({values[0]})"
        elif len(values) == 3:
            return f"rotate({values[0]}, {values[1]}, {values[2]})"
        else:
            raise ValueError("rotate requires 1 or 3 values")

    elif transform_type == TransformType.SKEWX:
        if len(values) == 1:
            return f"skewX({values[0]})"
        else:
            raise ValueError("skewX requires 1 value")

    elif transform_type == TransformType.SKEWY:
        if len(values) == 1:
            return f"skewY({values[0]})"
        else:
            raise ValueError("skewY requires 1 value")

    elif transform_type == TransformType.MATRIX:
        if len(values) == 6:
            return f"matrix({', '.join(map(str, values))})"
        else:
            raise ValueError("matrix requires 6 values")

    else:
        raise ValueError(f"Unknown transform type: {transform_type}")


class AnimationComplexity(Enum):
    """Animation complexity levels for analysis."""
    SIMPLE = "simple"          # Basic single-property animations
    MODERATE = "moderate"      # Multi-property or timed sequences
    COMPLEX = "complex"        # Advanced easing, transforms, or paths
    VERY_COMPLEX = "very_complex"  # Multiple complex animations


@dataclass
class AnimationSummary:
    """Summary of animation complexity and characteristics."""
    total_animations: int = 0
    complexity: AnimationComplexity = AnimationComplexity.SIMPLE
    duration: float = 0.0
    has_transforms: bool = False
    has_motion_paths: bool = False
    has_color_animations: bool = False
    has_easing: bool = False
    has_sequences: bool = False
    element_count: int = 0
    warnings: List[str] = field(default_factory=list)

    def add_warning(self, message: str):
        """Add a warning message."""
        if message not in self.warnings:
            self.warnings.append(message)

    def calculate_complexity(self):
        """Calculate overall complexity based on features."""
        complexity_score = 0

        # Base score from animation count
        complexity_score += min(self.total_animations, 10)

        # Feature-based scoring
        if self.has_transforms:
            complexity_score += 5
        if self.has_motion_paths:
            complexity_score += 8
        if self.has_color_animations:
            complexity_score += 3
        if self.has_easing:
            complexity_score += 4
        if self.has_sequences:
            complexity_score += 6

        # Duration factor
        if self.duration > 10:
            complexity_score += 3
        elif self.duration > 5:
            complexity_score += 1

        # Element count factor
        if self.element_count > 10:
            complexity_score += 4
        elif self.element_count > 5:
            complexity_score += 2

        # Determine complexity level
        if complexity_score <= 5:
            self.complexity = AnimationComplexity.SIMPLE
        elif complexity_score <= 15:
            self.complexity = AnimationComplexity.MODERATE
        elif complexity_score <= 25:
            self.complexity = AnimationComplexity.COMPLEX
        else:
            self.complexity = AnimationComplexity.VERY_COMPLEX