#!/usr/bin/env python3
"""
Animation Timeline Generator for SVG2PPTX

This module generates animation timelines and scenes from animation definitions,
calculating keyframes and managing temporal relationships. Following ADR-006
animation system architecture.

Key Features:
- Timeline scene generation with time sampling
- Keyframe calculation and value interpolation
- Animation synchronization and sequencing
- Performance optimization with smart sampling
- Conflict resolution for overlapping animations
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .core import AnimationDefinition, AnimationScene, CalcMode
from .interpolation import InterpolationEngine


@dataclass
class TimelineConfig:
    """Configuration for timeline generation."""
    sample_rate: float = 30.0  # Samples per second
    max_duration: float | None = None  # Maximum timeline duration
    min_keyframes: int = 2  # Minimum keyframes per animation
    max_keyframes: int = 100  # Maximum keyframes per animation
    precision: float = 0.001  # Time precision in seconds
    optimize_static_periods: bool = True  # Skip unnecessary frames


class TimelineGenerator:
    """Generates animation timelines and scenes from animation definitions."""

    def __init__(self, config: TimelineConfig | None = None):
        """Initialize timeline generator with configuration."""
        self.config = config or TimelineConfig()
        self.interpolation_engine = InterpolationEngine()

    def generate_timeline(
        self,
        animations: list[AnimationDefinition],
        target_duration: float | None = None,
    ) -> list[AnimationScene]:
        """
        Generate timeline scenes from animation definitions.

        Args:
            animations: List of animation definitions
            target_duration: Optional target duration for timeline

        Returns:
            List of AnimationScene objects representing the timeline
        """
        if not animations:
            return []

        # Calculate timeline bounds
        timeline_duration = self._calculate_timeline_duration(animations, target_duration)

        # Generate time samples
        time_samples = self._generate_time_samples(animations, timeline_duration)

        # Generate scenes for each time sample
        scenes = []
        for time in time_samples:
            scene = self._generate_scene_at_time(animations, time)
            if scene.element_states:  # Only add non-empty scenes
                scenes.append(scene)

        # Optimize timeline if enabled
        if self.config.optimize_static_periods:
            scenes = self._optimize_timeline(scenes)

        return scenes

    def _calculate_timeline_duration(
        self,
        animations: list[AnimationDefinition],
        target_duration: float | None,
    ) -> float:
        """Calculate the total duration of the timeline."""
        max_end_time = 0.0

        for animation in animations:
            end_time = animation.timing.get_end_time()
            if end_time != float('inf'):
                max_end_time = max(max_end_time, end_time)

        # Handle infinite animations
        if target_duration is not None:
            return target_duration
        elif max_end_time > 0:
            return max_end_time
        else:
            # Default duration if no finite animations
            return 5.0

    def _generate_time_samples(
        self,
        animations: list[AnimationDefinition],
        duration: float,
    ) -> list[float]:
        """Generate time sample points for timeline."""
        time_samples = set()

        # Always include start and end times
        time_samples.add(0.0)
        time_samples.add(duration)

        # Add critical time points from animations
        for animation in animations:
            # Animation start and end times
            time_samples.add(animation.timing.begin)

            end_time = animation.timing.get_end_time()
            if end_time != float('inf') and end_time <= duration:
                time_samples.add(end_time)

            # Keyframe time points
            if animation.key_times:
                for key_time in animation.key_times:
                    # Convert relative time to absolute time
                    abs_time = animation.timing.begin + (key_time * animation.timing.duration)
                    if abs_time <= duration:
                        time_samples.add(abs_time)

        # Add regular sampling points
        sample_interval = 1.0 / self.config.sample_rate
        current_time = 0.0
        while current_time <= duration:
            time_samples.add(current_time)
            current_time += sample_interval

        # Sort and filter samples
        sorted_samples = sorted(time_samples)

        # Remove samples that are too close together
        filtered_samples = [sorted_samples[0]]
        for sample in sorted_samples[1:]:
            if sample - filtered_samples[-1] >= self.config.precision:
                filtered_samples.append(sample)

        return filtered_samples

    def _generate_scene_at_time(
        self,
        animations: list[AnimationDefinition],
        time: float,
    ) -> AnimationScene:
        """Generate animation scene at specific time."""
        scene = AnimationScene(time=time)

        # Group animations by element and attribute
        element_animations = self._group_animations_by_element(animations)

        for element_id, element_anims in element_animations.items():
            # Group by attribute to handle conflicts
            attribute_groups = self._group_animations_by_attribute(element_anims)

            for attribute, attr_animations in attribute_groups.items():
                # Get active animations for this time
                active_animations = [
                    anim for anim in attr_animations
                    if anim.timing.is_active_at_time(time)
                ]

                if active_animations:
                    # Resolve conflicts and calculate final value
                    final_value = self._resolve_animation_conflicts(
                        active_animations, time, attribute,
                    )
                    if final_value:
                        scene.set_element_property(element_id, attribute, final_value)

        return scene

    def _group_animations_by_element(
        self,
        animations: list[AnimationDefinition],
    ) -> dict[str, list[AnimationDefinition]]:
        """Group animations by target element ID."""
        groups = {}
        for animation in animations:
            element_id = animation.element_id
            if element_id not in groups:
                groups[element_id] = []
            groups[element_id].append(animation)
        return groups

    def _group_animations_by_attribute(
        self,
        animations: list[AnimationDefinition],
    ) -> dict[str, list[AnimationDefinition]]:
        """Group animations by target attribute."""
        groups = {}
        for animation in animations:
            attribute = animation.target_attribute
            if attribute not in groups:
                groups[attribute] = []
            groups[attribute].append(animation)
        return groups

    def _resolve_animation_conflicts(
        self,
        animations: list[AnimationDefinition],
        time: float,
        attribute: str,
    ) -> str | None:
        """
        Resolve conflicts when multiple animations target the same attribute.

        Args:
            animations: List of active animations for this attribute
            time: Current time
            attribute: Target attribute name

        Returns:
            Final computed value or None if no value
        """
        if not animations:
            return None

        if len(animations) == 1:
            # Single animation - straightforward calculation
            return self._calculate_animation_value(animations[0], time)

        # Multiple animations - resolve based on priority and additive behavior
        base_value = None
        additive_values = []

        for animation in sorted(animations, key=lambda a: a.timing.begin):
            value = self._calculate_animation_value(animation, time)
            if value is None:
                continue

            if animation.additive == 'replace' or base_value is None:
                base_value = value
            elif animation.additive == 'sum':
                additive_values.append(value)

        # Combine base value with additive values
        if base_value is None:
            return None

        if not additive_values:
            return base_value

        # For numeric attributes, sum the values
        if self._is_numeric_summable(attribute):
            return self._sum_numeric_values(base_value, additive_values)
        else:
            # For non-summable attributes, use the last additive value
            return additive_values[-1] if additive_values else base_value

    def _calculate_animation_value(
        self,
        animation: AnimationDefinition,
        time: float,
    ) -> str | None:
        """Calculate the value of a single animation at given time."""
        if not animation.timing.is_active_at_time(time):
            return None

        # Get local time within animation (0.0 to 1.0)
        local_time = animation.timing.get_local_time(time)

        # Handle discrete calculation mode
        if animation.calc_mode == CalcMode.DISCRETE:
            return self._calculate_discrete_value(animation, local_time)

        # Handle other calculation modes with interpolation
        return self._calculate_interpolated_value(animation, local_time)

    def _calculate_discrete_value(
        self,
        animation: AnimationDefinition,
        local_time: float,
    ) -> str | None:
        """Calculate value for discrete animation mode."""
        if not animation.values:
            return None

        if len(animation.values) == 1:
            return animation.values[0]

        # Use key_times if provided, otherwise uniform distribution
        if animation.key_times and len(animation.key_times) == len(animation.values):
            times = animation.key_times
        else:
            times = [i / (len(animation.values) - 1) for i in range(len(animation.values))]

        # Find the active value based on time
        for i, key_time in enumerate(times):
            if local_time <= key_time:
                return animation.values[i]

        # Return last value if time exceeds all key times
        return animation.values[-1]

    def _calculate_interpolated_value(
        self,
        animation: AnimationDefinition,
        local_time: float,
    ) -> str | None:
        """Calculate value using interpolation."""
        if not animation.values:
            return None

        # Use interpolation engine for value calculation
        result = self.interpolation_engine.interpolate_keyframes(
            values=animation.values,
            key_times=animation.key_times,
            key_splines=animation.key_splines,
            progress=local_time,
            attribute_name=animation.target_attribute,
            transform_type=animation.transform_type,
        )

        return result.value

    def _is_numeric_summable(self, attribute: str) -> bool:
        """Check if attribute values can be numerically summed."""
        summable_attributes = {
            'opacity', 'fill-opacity', 'stroke-opacity',
            'stroke-width', 'font-size', 'r', 'rx', 'ry',
            'x', 'y', 'cx', 'cy', 'width', 'height',
            'dx', 'dy', 'offset',
        }
        return attribute.lower() in summable_attributes

    def _sum_numeric_values(self, base_value: str, additive_values: list[str]) -> str:
        """Sum numeric values for additive animations."""
        try:
            # Parse base value
            base_num, unit = self._parse_numeric_with_unit(base_value)
            if base_num is None:
                return base_value

            # Sum additive values
            total = base_num
            for value in additive_values:
                num, val_unit = self._parse_numeric_with_unit(value)
                if num is not None and (val_unit == unit or not val_unit):
                    total += num

            # Format result
            if unit:
                return f"{total:.3f}{unit}".rstrip('0').rstrip('.')
            else:
                return f"{total:.3f}".rstrip('0').rstrip('.')

        except Exception:
            # Fallback to base value on any error
            return base_value

    def _parse_numeric_with_unit(self, value: str) -> tuple[float | None, str | None]:
        """Parse numeric value with optional unit."""
        import re
        if not value:
            return None, None

        match = re.match(r'^([-+]?(?:\d+\.?\d*|\.\d+))(.*)$', value.strip())
        if match:
            try:
                number = float(match.group(1))
                unit = match.group(2).strip()
                return number, unit if unit else None
            except ValueError:
                pass

        return None, None

    def _optimize_timeline(self, scenes: list[AnimationScene]) -> list[AnimationScene]:
        """Optimize timeline by removing redundant scenes."""
        if len(scenes) <= 2:
            return scenes

        optimized = [scenes[0]]  # Always keep first scene

        for i in range(1, len(scenes) - 1):
            current_scene = scenes[i]
            prev_scene = optimized[-1]
            next_scene = scenes[i + 1]

            # Check if current scene represents a significant change
            if self._is_significant_scene_change(prev_scene, current_scene, next_scene):
                optimized.append(current_scene)

        # Always keep last scene
        if len(scenes) > 1:
            optimized.append(scenes[-1])

        return optimized

    def _is_significant_scene_change(
        self,
        prev_scene: AnimationScene,
        current_scene: AnimationScene,
        next_scene: AnimationScene,
    ) -> bool:
        """Check if a scene represents a significant change worth keeping."""
        # Check for new or removed elements
        prev_elements = set(prev_scene.element_states.keys())
        current_elements = set(current_scene.element_states.keys())
        next_elements = set(next_scene.element_states.keys())

        if current_elements != prev_elements or current_elements != next_elements:
            return True

        # Check for significant value changes
        for element_id in current_elements:
            prev_props = prev_scene.element_states.get(element_id, {})
            current_props = current_scene.element_states.get(element_id, {})
            next_props = next_scene.element_states.get(element_id, {})

            # Check if current scene has different properties
            if set(current_props.keys()) != set(prev_props.keys()):
                return True

            # Check for non-linear changes (indicating keyframes or easing)
            for prop, current_value in current_props.items():
                prev_value = prev_props.get(prop)
                next_value = next_props.get(prop)

                if self._is_non_linear_change(prev_value, current_value, next_value):
                    return True

        return False

    def _is_non_linear_change(
        self,
        prev_value: str | None,
        current_value: str | None,
        next_value: str | None,
    ) -> bool:
        """Check if value change is non-linear (indicating keyframe importance)."""
        if not all([prev_value, current_value, next_value]):
            return True  # Missing values indicate significant change

        # For numeric values, check if change is non-linear
        try:
            prev_num = float(prev_value.split()[0] if ' ' in prev_value else prev_value.rstrip('px%em'))
            current_num = float(current_value.split()[0] if ' ' in current_value else current_value.rstrip('px%em'))
            next_num = float(next_value.split()[0] if ' ' in next_value else next_value.rstrip('px%em'))

            # Calculate expected linear interpolation value
            expected = (prev_num + next_num) / 2.0
            tolerance = abs(next_num - prev_num) * 0.1  # 10% tolerance

            return abs(current_num - expected) > tolerance

        except (ValueError, AttributeError):
            # For non-numeric values, any change is significant
            return current_value != prev_value or current_value != next_value

    def generate_keyframe_summary(self, animations: list[AnimationDefinition]) -> dict[str, Any]:
        """Generate summary of keyframe requirements for animations."""
        summary = {
            'total_animations': len(animations),
            'elements': set(),
            'attributes': set(),
            'duration': 0.0,
            'keyframe_density': 0.0,
            'complexity_factors': [],
        }

        for animation in animations:
            summary['elements'].add(animation.element_id)
            summary['attributes'].add(animation.target_attribute)

            end_time = animation.timing.get_end_time()
            if end_time != float('inf'):
                summary['duration'] = max(summary['duration'], end_time)

            # Analyze complexity factors
            if animation.key_splines:
                summary['complexity_factors'].append('Custom easing curves')
            if animation.key_times:
                summary['complexity_factors'].append('Custom timing')
            if len(animation.values) > 2:
                summary['complexity_factors'].append('Multi-keyframe animation')

        # Calculate keyframe density
        if summary['duration'] > 0:
            estimated_keyframes = len(animations) * 2  # Rough estimate
            summary['keyframe_density'] = estimated_keyframes / summary['duration']

        # Convert sets to counts
        summary['unique_elements'] = len(summary['elements'])
        summary['unique_attributes'] = len(summary['attributes'])
        summary['elements'] = list(summary['elements'])
        summary['attributes'] = list(summary['attributes'])

        return summary