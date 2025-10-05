#!/usr/bin/env python3
"""
Fluent API Builders for Animation System

This module provides fluent API builders for the animation system, following
ADR-005 fluent API patterns. Enables intuitive animation construction with
method chaining and progressive configuration.

Key Features:
- AnimationBuilder for constructing individual animations
- AnimationSequenceBuilder for creating animation sequences
- TimingBuilder for configuring animation timing
- Progressive configuration with validation
- Integration with core animation system
"""

from typing import List, Optional, Union

from .core import (
    AnimationDefinition, AnimationTiming, AnimationType, FillMode,
    TransformType, CalcMode
)
# AnimationConverter moved to src.converters.animation_converter


class AnimationBuilder:
    """
    Fluent builder for constructing individual animations.

    Example usage:
        animation = (AnimationBuilder()
            .target("rect1")
            .animate("opacity")
            .from_to("0", "1")
            .duration("2s")
            .with_easing("ease-in-out")
            .build())
    """

    def __init__(self):
        """Initialize animation builder."""
        self._element_id: Optional[str] = None
        self._animation_type: Optional[AnimationType] = None
        self._target_attribute: Optional[str] = None
        self._values: List[str] = []
        self._timing: Optional[AnimationTiming] = None
        self._key_times: Optional[List[float]] = None
        self._key_splines: Optional[List[List[float]]] = None
        self._calc_mode: CalcMode = CalcMode.LINEAR
        self._transform_type: Optional[TransformType] = None
        self._additive: str = "replace"
        self._accumulate: str = "none"

    def target(self, element_id: str) -> 'AnimationBuilder':
        """
        Set the target element ID.

        Args:
            element_id: ID of the element to animate

        Returns:
            Self for method chaining
        """
        self._element_id = element_id
        return self

    def animate(self, attribute: str) -> 'AnimationBuilder':
        """
        Set the attribute to animate.

        Args:
            attribute: Name of the attribute to animate

        Returns:
            Self for method chaining
        """
        self._target_attribute = attribute
        self._animation_type = AnimationType.ANIMATE
        return self

    def animate_transform(self, transform_type: Union[str, TransformType]) -> 'AnimationBuilder':
        """
        Set up transform animation.

        Args:
            transform_type: Type of transform (translate, scale, rotate, etc.)

        Returns:
            Self for method chaining
        """
        self._target_attribute = "transform"
        self._animation_type = AnimationType.ANIMATE_TRANSFORM

        if isinstance(transform_type, str):
            transform_map = {
                'translate': TransformType.TRANSLATE,
                'scale': TransformType.SCALE,
                'rotate': TransformType.ROTATE,
                'skewx': TransformType.SKEWX,
                'skewy': TransformType.SKEWY,
                'matrix': TransformType.MATRIX
            }
            self._transform_type = transform_map.get(transform_type.lower())
        else:
            self._transform_type = transform_type

        return self

    def animate_color(self, attribute: str = "fill") -> 'AnimationBuilder':
        """
        Set up color animation.

        Args:
            attribute: Color attribute to animate (fill, stroke, etc.)

        Returns:
            Self for method chaining
        """
        self._target_attribute = attribute
        self._animation_type = AnimationType.ANIMATE_COLOR
        return self

    def animate_motion(self) -> 'AnimationBuilder':
        """
        Set up motion path animation.

        Returns:
            Self for method chaining
        """
        self._animation_type = AnimationType.ANIMATE_MOTION
        return self

    def set_value(self, attribute: str) -> 'AnimationBuilder':
        """
        Set up set animation (instant value change).

        Args:
            attribute: Attribute to set

        Returns:
            Self for method chaining
        """
        self._target_attribute = attribute
        self._animation_type = AnimationType.SET
        return self

    def from_to(self, from_value: str, to_value: str) -> 'AnimationBuilder':
        """
        Set animation from and to values.

        Args:
            from_value: Starting value
            to_value: Ending value

        Returns:
            Self for method chaining
        """
        self._values = [from_value, to_value]
        return self

    def to(self, to_value: str) -> 'AnimationBuilder':
        """
        Set animation to value (animates from current value).

        Args:
            to_value: Target value

        Returns:
            Self for method chaining
        """
        self._values = [to_value]
        return self

    def values(self, *values: str) -> 'AnimationBuilder':
        """
        Set multiple keyframe values.

        Args:
            values: List of keyframe values

        Returns:
            Self for method chaining
        """
        self._values = list(values)
        return self

    def duration(self, duration: Union[str, float]) -> 'AnimationBuilder':
        """
        Set animation duration.

        Args:
            duration: Duration as string (e.g., "2s") or float (seconds)

        Returns:
            Self for method chaining
        """
        if self._timing is None:
            self._timing = AnimationTiming()

        if isinstance(duration, str):
            self._timing.duration = self._parse_time_value(duration)
        else:
            self._timing.duration = float(duration)

        return self

    def delay(self, delay: Union[str, float]) -> 'AnimationBuilder':
        """
        Set animation delay.

        Args:
            delay: Delay as string (e.g., "1s") or float (seconds)

        Returns:
            Self for method chaining
        """
        if self._timing is None:
            self._timing = AnimationTiming()

        if isinstance(delay, str):
            self._timing.begin = self._parse_time_value(delay)
        else:
            self._timing.begin = float(delay)

        return self

    def repeat(self, count: Union[int, str]) -> 'AnimationBuilder':
        """
        Set animation repeat count.

        Args:
            count: Repeat count (integer or "indefinite")

        Returns:
            Self for method chaining
        """
        if self._timing is None:
            self._timing = AnimationTiming()

        self._timing.repeat_count = count
        return self

    def fill_mode(self, mode: Union[str, FillMode]) -> 'AnimationBuilder':
        """
        Set animation fill mode.

        Args:
            mode: Fill mode ("freeze" or "remove")

        Returns:
            Self for method chaining
        """
        if self._timing is None:
            self._timing = AnimationTiming()

        if isinstance(mode, str):
            self._timing.fill_mode = FillMode.FREEZE if mode == "freeze" else FillMode.REMOVE
        else:
            self._timing.fill_mode = mode

        return self

    def with_easing(self, easing: Union[str, List[float]]) -> 'AnimationBuilder':
        """
        Set animation easing.

        Args:
            easing: Easing name or Bezier control points

        Returns:
            Self for method chaining
        """
        if isinstance(easing, str):
            # Map common easing names to Bezier curves
            easing_map = {
                'linear': [0.0, 0.0, 1.0, 1.0],
                'ease': [0.25, 0.1, 0.25, 1.0],
                'ease-in': [0.42, 0.0, 1.0, 1.0],
                'ease-out': [0.0, 0.0, 0.58, 1.0],
                'ease-in-out': [0.42, 0.0, 0.58, 1.0]
            }
            control_points = easing_map.get(easing.lower(), [0.25, 0.1, 0.25, 1.0])
        else:
            control_points = easing

        self._key_splines = [control_points]
        self._calc_mode = CalcMode.SPLINE
        return self

    def with_keyframes(self, times: List[float], splines: Optional[List[List[float]]] = None) -> 'AnimationBuilder':
        """
        Set explicit keyframe timing.

        Args:
            times: Keyframe times (0.0 to 1.0)
            splines: Optional easing curves for each segment

        Returns:
            Self for method chaining
        """
        self._key_times = times
        if splines:
            self._key_splines = splines
            self._calc_mode = CalcMode.SPLINE
        return self

    def additive(self, mode: str = "sum") -> 'AnimationBuilder':
        """
        Set animation as additive.

        Args:
            mode: Additive mode ("sum" or "replace")

        Returns:
            Self for method chaining
        """
        self._additive = mode
        return self

    def discrete(self) -> 'AnimationBuilder':
        """
        Set animation to discrete calculation mode.

        Returns:
            Self for method chaining
        """
        self._calc_mode = CalcMode.DISCRETE
        return self

    def build(self) -> AnimationDefinition:
        """
        Build the animation definition.

        Returns:
            Constructed AnimationDefinition

        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        if not self._element_id:
            raise ValueError("Target element ID is required")
        if not self._animation_type:
            raise ValueError("Animation type is required")
        if not self._target_attribute:
            raise ValueError("Target attribute is required")
        if not self._values:
            raise ValueError("Animation values are required")

        # Use default timing if not set
        if self._timing is None:
            self._timing = AnimationTiming()

        return AnimationDefinition(
            element_id=self._element_id,
            animation_type=self._animation_type,
            target_attribute=self._target_attribute,
            values=self._values,
            timing=self._timing,
            key_times=self._key_times,
            key_splines=self._key_splines,
            calc_mode=self._calc_mode,
            transform_type=self._transform_type,
            additive=self._additive,
            accumulate=self._accumulate
        )

    def _parse_time_value(self, time_str: str) -> float:
        """Parse time value string to seconds."""
        if not time_str:
            return 0.0

        time_str = time_str.strip().lower()

        if time_str.endswith('ms'):
            return float(time_str[:-2]) / 1000.0
        elif time_str.endswith('s'):
            return float(time_str[:-1])
        else:
            return float(time_str)


class AnimationSequenceBuilder:
    """
    Fluent builder for constructing animation sequences.

    Example usage:
        sequence = (AnimationSequenceBuilder()
            .add_animation(fade_in)
            .then_after("1s")
            .add_animation(scale_up)
            .build())
    """

    def __init__(self):
        """Initialize sequence builder."""
        self._animations: List[AnimationDefinition] = []
        self._current_time_offset: float = 0.0

    def add_animation(self, animation: AnimationDefinition) -> 'AnimationSequenceBuilder':
        """
        Add animation to sequence.

        Args:
            animation: Animation to add

        Returns:
            Self for method chaining
        """
        # Apply current time offset
        animation.timing.begin += self._current_time_offset
        self._animations.append(animation)
        return self

    def add_builder(self, builder: AnimationBuilder) -> 'AnimationSequenceBuilder':
        """
        Add animation from builder to sequence.

        Args:
            builder: Animation builder to build and add

        Returns:
            Self for method chaining
        """
        animation = builder.build()
        return self.add_animation(animation)

    def then_after(self, delay: Union[str, float]) -> 'AnimationSequenceBuilder':
        """
        Set delay before next animation.

        Args:
            delay: Delay as string or float (seconds)

        Returns:
            Self for method chaining
        """
        if isinstance(delay, str):
            delay_seconds = AnimationBuilder()._parse_time_value(delay)
        else:
            delay_seconds = float(delay)

        # Calculate when the last animation ends
        if self._animations:
            last_animation = self._animations[-1]
            last_end_time = last_animation.timing.begin + last_animation.timing.duration
            self._current_time_offset = last_end_time + delay_seconds
        else:
            self._current_time_offset += delay_seconds
        return self

    def simultaneously(self) -> 'AnimationSequenceBuilder':
        """
        Reset time offset so next animation starts simultaneously.

        Returns:
            Self for method chaining
        """
        if self._animations:
            # Set offset to start time of last animation
            self._current_time_offset = self._animations[-1].timing.begin
        return self

    def build(self) -> List[AnimationDefinition]:
        """
        Build the animation sequence.

        Returns:
            List of animation definitions
        """
        return self._animations.copy()


class TimingBuilder:
    """
    Fluent builder for animation timing configuration.

    Example usage:
        timing = (TimingBuilder()
            .duration("2s")
            .delay("0.5s")
            .repeat(3)
            .freeze()
            .build())
    """

    def __init__(self):
        """Initialize timing builder."""
        self._timing = AnimationTiming()

    def duration(self, duration: Union[str, float]) -> 'TimingBuilder':
        """Set animation duration."""
        if isinstance(duration, str):
            self._timing.duration = AnimationBuilder()._parse_time_value(duration)
        else:
            self._timing.duration = float(duration)
        return self

    def delay(self, delay: Union[str, float]) -> 'TimingBuilder':
        """Set animation delay."""
        if isinstance(delay, str):
            self._timing.begin = AnimationBuilder()._parse_time_value(delay)
        else:
            self._timing.begin = float(delay)
        return self

    def repeat(self, count: Union[int, str]) -> 'TimingBuilder':
        """Set repeat count."""
        self._timing.repeat_count = count
        return self

    def indefinite(self) -> 'TimingBuilder':
        """Set repeat to indefinite."""
        self._timing.repeat_count = "indefinite"
        return self

    def freeze(self) -> 'TimingBuilder':
        """Set fill mode to freeze."""
        self._timing.fill_mode = FillMode.FREEZE
        return self

    def remove(self) -> 'TimingBuilder':
        """Set fill mode to remove."""
        self._timing.fill_mode = FillMode.REMOVE
        return self

    def build(self) -> AnimationTiming:
        """Build the timing configuration."""
        return self._timing


class AnimationComposer:
    """
    High-level composer for creating complex animation scenarios.

    Example usage:
        composer = AnimationComposer()
        composer.fade_in("rect1", "1s")
        composer.scale_up("rect1", "0.5s", delay="1s")
        animations = composer.build()
    """

    def __init__(self):
        """Initialize animation composer."""
        self._sequence_builder = AnimationSequenceBuilder()

    def fade_in(self, element_id: str, duration: str, delay: str = "0s") -> 'AnimationComposer':
        """Add fade in animation."""
        animation = (AnimationBuilder()
                    .target(element_id)
                    .animate("opacity")
                    .from_to("0", "1")
                    .duration(duration)
                    .delay(delay)
                    .build())
        self._sequence_builder.add_animation(animation)
        return self

    def fade_out(self, element_id: str, duration: str, delay: str = "0s") -> 'AnimationComposer':
        """Add fade out animation."""
        animation = (AnimationBuilder()
                    .target(element_id)
                    .animate("opacity")
                    .from_to("1", "0")
                    .duration(duration)
                    .delay(delay)
                    .build())
        self._sequence_builder.add_animation(animation)
        return self

    def scale_up(self, element_id: str, duration: str, scale: str = "1.5", delay: str = "0s") -> 'AnimationComposer':
        """Add scale up animation."""
        animation = (AnimationBuilder()
                    .target(element_id)
                    .animate_transform("scale")
                    .from_to("1", scale)
                    .duration(duration)
                    .delay(delay)
                    .build())
        self._sequence_builder.add_animation(animation)
        return self

    def rotate(self, element_id: str, duration: str, degrees: str = "360", delay: str = "0s") -> 'AnimationComposer':
        """Add rotation animation."""
        animation = (AnimationBuilder()
                    .target(element_id)
                    .animate_transform("rotate")
                    .from_to("0", degrees)
                    .duration(duration)
                    .delay(delay)
                    .build())
        self._sequence_builder.add_animation(animation)
        return self

    def color_change(self, element_id: str, duration: str, from_color: str, to_color: str, delay: str = "0s") -> 'AnimationComposer':
        """Add color change animation."""
        animation = (AnimationBuilder()
                    .target(element_id)
                    .animate_color("fill")
                    .from_to(from_color, to_color)
                    .duration(duration)
                    .delay(delay)
                    .build())
        self._sequence_builder.add_animation(animation)
        return self

    def then_after(self, delay: Union[str, float]) -> 'AnimationComposer':
        """Add delay before next animation."""
        self._sequence_builder.then_after(delay)
        return self

    def simultaneously(self) -> 'AnimationComposer':
        """Make next animation start simultaneously."""
        self._sequence_builder.simultaneously()
        return self

    def build(self) -> List[AnimationDefinition]:
        """Build the complete animation sequence."""
        return self._sequence_builder.build()