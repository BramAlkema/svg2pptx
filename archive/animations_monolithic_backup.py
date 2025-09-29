#!/usr/bin/env python3
"""
SVG Animation Processor for SVG2PPTX

This module handles SVG animation elements (SMIL) - extremely rare in modern usage
but occasionally found in legacy SVG files and specialized graphics. Converts
animations to static states or PowerPoint animation sequences.

Key Features:
- Complete SMIL animation support: animate, animateTransform, animateColor
- Animation timeline calculation and keyframe extraction
- Static frame extraction for single-slide representation
- Multi-slide sequence generation for animation playback
- PowerPoint animation mapping where possible
- Smart static fallback for complex animations
- Animation performance analysis and optimization

SVG Animation Reference:
- <animate> elements animate attribute values over time
- <animateTransform> animates transform attributes
- <animateColor> animates color values (deprecated but still used)
- <animateMotion> animates position along paths
- Complex timing: begin, dur, repeatCount, fill modes
"""

import re
import math
from typing import List, Dict, Tuple, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
from lxml import etree as ET

from .base import BaseConverter
from .base import ConversionContext
from ..services.conversion_services import ConversionServices
from .animation_templates import PowerPointAnimationGenerator, PowerPointAnimationConfig, PowerPointEffectType, PowerPointEasingMapper
from .timing import AdvancedTimingConverter, TimingReference, PowerPointTimingGenerator, TimingEventType
from .animation_transform_matrix import (
    PowerPointTransformAnimationGenerator, AnimationTransformProcessor,
    TransformMatrix, MatrixOperation
)


class AnimationType(Enum):
    """SVG animation types."""
    ANIMATE = "animate"
    ANIMATE_TRANSFORM = "animateTransform"
    ANIMATE_COLOR = "animateColor"
    ANIMATE_MOTION = "animateMotion"
    SET = "set"


class FillMode(Enum):
    """Animation fill modes."""
    REMOVE = "remove"      # Remove effect after animation
    FREEZE = "freeze"      # Keep final value


class TransformType(Enum):
    """Transform animation types."""
    TRANSLATE = "translate"
    SCALE = "scale"
    ROTATE = "rotate"
    SKEWX = "skewX"
    SKEWY = "skewY"


@dataclass
class AnimationTiming:
    """Animation timing information."""
    begin: float           # Start time in seconds
    duration: float        # Duration in seconds
    repeat_count: Union[int, str]  # Number of repeats or "indefinite"
    fill_mode: FillMode
    
    def get_end_time(self) -> float:
        """Get animation end time."""
        if isinstance(self.repeat_count, str) and self.repeat_count == "indefinite":
            return float('inf')
        elif isinstance(self.repeat_count, int):
            return self.begin + self.duration * self.repeat_count
        else:
            return self.begin + self.duration


@dataclass
class AnimationKeyframe:
    """Animation keyframe with interpolated values."""
    time: float            # Time in seconds
    values: Dict[str, Any] # Attribute values at this time
    easing: str           # Easing function


@dataclass
class AnimationDefinition:
    """Complete animation definition."""
    element_id: str
    animation_type: AnimationType
    target_attribute: str
    values: List[str]      # Animation values
    key_times: Optional[List[float]]  # Key time points
    key_splines: Optional[List[List[float]]]  # Cubic Bezier easing control points
    timing: AnimationTiming
    transform_type: Optional[TransformType]  # For animateTransform
    calc_mode: str = 'linear'  # Calculation mode: linear, discrete, paced, spline
    
    def get_value_at_time(self, time: float) -> Optional[str]:
        """Get interpolated value at specific time."""
        if time < self.timing.begin:
            return None
        
        # Calculate progress within animation
        if self.timing.duration <= 0:
            return self.values[-1] if self.values else None
        
        progress = (time - self.timing.begin) % self.timing.duration
        t = progress / self.timing.duration
        
        if not self.values:
            return None
        
        if len(self.values) == 1:
            return self.values[0]
        
        # Find interpolation segment
        if self.key_times:
            # Use specified key times
            for i in range(len(self.key_times) - 1):
                if self.key_times[i] <= t <= self.key_times[i + 1]:
                    # Interpolate between values
                    segment_t = (t - self.key_times[i]) / (self.key_times[i + 1] - self.key_times[i])
                    # Apply easing for this segment
                    eased_t = self._apply_easing(segment_t, i)
                    return self._interpolate_values(self.values[i], self.values[i + 1], eased_t)
            
            return self.values[-1]
        else:
            # Linear distribution
            segment_size = 1.0 / (len(self.values) - 1)
            segment_index = min(int(t / segment_size), len(self.values) - 2)
            segment_t = (t - segment_index * segment_size) / segment_size

            # Apply easing for this segment
            eased_t = self._apply_easing(segment_t, segment_index)
            return self._interpolate_values(self.values[segment_index],
                                          self.values[segment_index + 1], eased_t)
    
    def _interpolate_values(self, value1: str, value2: str, t: float) -> str:
        """Interpolate between two animation values."""
        # Handle different value types
        if self.target_attribute in ['fill', 'stroke', 'stop-color']:
            # Color interpolation
            return self._interpolate_colors(value1, value2, t)
        elif self.target_attribute in ['opacity', 'fill-opacity', 'stroke-opacity']:
            # Numeric interpolation
            try:
                num1 = float(value1)
                num2 = float(value2)
                result = num1 + (num2 - num1) * t
                return str(result)
            except ValueError:
                return value1
        elif self.animation_type == AnimationType.ANIMATE_TRANSFORM:
            # Transform value interpolation
            return self._interpolate_transform_values(value1, value2, t)
        else:
            # Default: use discrete values
            return value1 if t < 0.5 else value2

    def _apply_easing(self, t: float, segment_index: int = 0) -> float:
        """
        Apply easing function to interpolation parameter.

        Args:
            t: Interpolation parameter (0-1)
            segment_index: Index of the key spline segment to use

        Returns:
            Eased interpolation parameter
        """
        if self.calc_mode == 'discrete':
            # Discrete mode: snap to nearest keyframe
            return 0.0 if t < 0.5 else 1.0
        elif self.calc_mode == 'spline' and self.key_splines:
            # Use cubic Bezier easing
            if segment_index < len(self.key_splines):
                spline = self.key_splines[segment_index]
                return self._cubic_bezier_easing(t, spline[0], spline[1], spline[2], spline[3])

        # Linear mode (default)
        return t

    def _cubic_bezier_easing(self, t: float, x1: float, y1: float, x2: float, y2: float) -> float:
        """
        Calculate cubic Bezier easing curve.

        Args:
            t: Input parameter (0-1)
            x1, y1, x2, y2: Bezier control points

        Returns:
            Eased output value
        """
        # Simplified cubic Bezier calculation for timing functions
        # This implements a cubic Bezier curve with control points (0,0), (x1,y1), (x2,y2), (1,1)

        # Use Newton-Raphson method to find t value for given x
        def bezier_x(t_val):
            return 3 * (1 - t_val) ** 2 * t_val * x1 + 3 * (1 - t_val) * t_val ** 2 * x2 + t_val ** 3

        def bezier_y(t_val):
            return 3 * (1 - t_val) ** 2 * t_val * y1 + 3 * (1 - t_val) * t_val ** 2 * y2 + t_val ** 3

        # Binary search to find the t value that gives us the input x (which is our input t)
        t_min, t_max = 0.0, 1.0
        for _ in range(10):  # Sufficient iterations for timing curves
            t_mid = (t_min + t_max) / 2
            x_mid = bezier_x(t_mid)
            if abs(x_mid - t) < 0.001:
                return bezier_y(t_mid)
            elif x_mid < t:
                t_min = t_mid
            else:
                t_max = t_mid

        # Fallback to linear if convergence fails
        return t
    
    def _interpolate_colors(self, color1: str, color2: str, t: float) -> str:
        """Interpolate between two colors."""
        c1 = self.color_parser.parse(color1)
        c2 = self.color_parser.parse(color2)
        
        if not c1 or not c2:
            return color1
        
        # Linear RGB interpolation
        r = int(c1.red + (c2.red - c1.red) * t)
        g = int(c1.green + (c2.green - c1.green) * t)
        b = int(c1.blue + (c2.blue - c1.blue) * t)
        a = c1.alpha + (c2.alpha - c1.alpha) * t
        
        return f"rgba({r}, {g}, {b}, {a})"
    
    def _interpolate_transform_values(self, value1: str, value2: str, t: float) -> str:
        """Interpolate between transform values."""
        try:
            # Parse numeric values from transform
            nums1 = [float(x) for x in re.findall(r'[-+]?\d*\.?\d+', value1)]
            nums2 = [float(x) for x in re.findall(r'[-+]?\d*\.?\d+', value2)]
            
            if len(nums1) != len(nums2):
                return value1 if t < 0.5 else value2
            
            # Interpolate each numeric component
            interpolated = []
            for n1, n2 in zip(nums1, nums2):
                interpolated.append(n1 + (n2 - n1) * t)
            
            # Reconstruct transform string using standardized formatter
            if self.transform_type:
                return format_transform_string(self.transform_type, interpolated)
            else:
                return value1
                
        except (ValueError, IndexError):
            return value1 if t < 0.5 else value2


def format_transform_string(transform_type: TransformType, values: List[float]) -> str:
    """
    Format transform values into standardized SVG transform string.
    
    Uses consistent formatting that matches TransformEngine expectations.
    This replaces manual string concatenation with standardized formatting.
    """
    if transform_type == TransformType.TRANSLATE:
        if len(values) >= 2:
            return f"translate({values[0]}, {values[1]})"
        else:
            return f"translate({values[0]})"
    elif transform_type == TransformType.SCALE:
        if len(values) >= 2:
            return f"scale({values[0]}, {values[1]})"
        else:
            return f"scale({values[0]})"
    elif transform_type == TransformType.ROTATE:
        if len(values) >= 3:
            return f"rotate({values[0]}, {values[1]}, {values[2]})"
        else:
            return f"rotate({values[0]})"
    else:
        # Fallback for unsupported types
        return f"{transform_type.value}({', '.join(map(str, values))})"


@dataclass
class AnimationScene:
    """Snapshot of all animated elements at a specific time."""
    time: float
    element_states: Dict[str, Dict[str, str]]  # element_id -> {attribute: value}


class AnimationConverter(BaseConverter):
    """Converts SVG animations to static representations or PowerPoint animations."""
    
    supported_elements = ['animate', 'animateTransform', 'animateColor', 'animateMotion', 'set']
    
    def __init__(self, services: ConversionServices):
        """
        Initialize AnimationConverter with dependency injection.

        Args:
            services: ConversionServices container with initialized services
        """
        super().__init__(services)
        self.animations: List[AnimationDefinition] = []
        self.powerpoint_generator = PowerPointAnimationGenerator()
        self.timing_converter = AdvancedTimingConverter()
        self.timing_generator = PowerPointTimingGenerator()
        self.transform_generator = PowerPointTransformAnimationGenerator()
        self.transform_processor = AnimationTransformProcessor()

        # Animation processing options
        self.max_keyframes = 30  # Maximum keyframes to extract
        self.frame_rate = 24     # Frames per second for analysis
        self.static_time = 0.5   # Time point for static extraction (seconds)

    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the given element."""
        tag = self.get_element_tag(element)
        return tag in self.supported_elements

    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert animation element to PowerPoint animation XML."""
        # Parse the SMIL animation element
        animation_def = self._parse_animation_element(element, context.svg_root)
        if not animation_def:
            return ""

        # Store animation for later processing
        self.animations.append(animation_def)

        # Generate PowerPoint animation XML
        powerpoint_config = self._convert_to_powerpoint_config(animation_def)
        if powerpoint_config:
            return self.powerpoint_generator.generate_animation_drawingml(powerpoint_config)

        return ""

    def _convert_to_powerpoint_config(self, animation_def: AnimationDefinition) -> Optional[PowerPointAnimationConfig]:
        """
        Convert SMIL AnimationDefinition to PowerPoint animation configuration.

        Args:
            animation_def: Parsed SMIL animation definition

        Returns:
            PowerPointAnimationConfig or None if not convertible
        """
        # Convert duration from seconds to milliseconds
        duration_ms = int(animation_def.timing.duration * 1000)
        delay_ms = int(animation_def.timing.begin * 1000)

        # Convert repeat count
        repeat_count = None
        if isinstance(animation_def.timing.repeat_count, str):
            if animation_def.timing.repeat_count == "indefinite":
                repeat_count = -1  # Indefinite
        elif isinstance(animation_def.timing.repeat_count, int):
            repeat_count = animation_def.timing.repeat_count

        # Determine PowerPoint effect type based on SMIL animation
        effect_type = self._map_smil_to_powerpoint_effect(animation_def)
        if not effect_type:
            return None

        # Extract custom attributes based on animation type
        custom_attributes = self._extract_custom_attributes(animation_def)

        # Map SVG easing to PowerPoint acceleration/deceleration
        easing_accel, easing_decel = self._map_animation_easing(animation_def)

        return PowerPointAnimationConfig(
            effect_type=effect_type,
            duration_ms=duration_ms,
            delay_ms=delay_ms,
            repeat_count=repeat_count,
            target_element_id=animation_def.element_id or "unknown",
            custom_attributes=custom_attributes,
            easing_accel=easing_accel,
            easing_decel=easing_decel
        )

    def _map_smil_to_powerpoint_effect(self, animation_def: AnimationDefinition) -> Optional[PowerPointEffectType]:
        """
        Map SMIL animation to PowerPoint effect type.

        Args:
            animation_def: SMIL animation definition

        Returns:
            PowerPointEffectType or None if not mappable
        """
        if animation_def.animation_type == AnimationType.ANIMATE:
            if animation_def.target_attribute == "opacity":
                # Determine fade direction from values
                if animation_def.values and len(animation_def.values) >= 2:
                    try:
                        start_val = float(animation_def.values[0])
                        end_val = float(animation_def.values[-1])
                        if start_val < end_val:
                            return PowerPointEffectType.FADE_IN
                        else:
                            return PowerPointEffectType.FADE_OUT
                    except ValueError:
                        pass
                return PowerPointEffectType.FADE_IN  # Default

            elif animation_def.target_attribute in ["fill", "stroke"]:
                return PowerPointEffectType.COLOR_CHANGE

            elif animation_def.target_attribute in ["r", "width", "height", "font-size"]:
                # Determine grow/shrink from values
                if animation_def.values and len(animation_def.values) >= 2:
                    try:
                        start_val = float(animation_def.values[0])
                        end_val = float(animation_def.values[-1])
                        if start_val < end_val:
                            return PowerPointEffectType.GROW
                        else:
                            return PowerPointEffectType.SHRINK
                    except ValueError:
                        pass
                return PowerPointEffectType.EMPHASIS  # Default for size changes

        elif animation_def.animation_type == AnimationType.ANIMATE_TRANSFORM:
            if animation_def.transform_type == TransformType.SCALE:
                return PowerPointEffectType.GROW
            elif animation_def.transform_type == TransformType.ROTATE:
                return PowerPointEffectType.SPIN
            elif animation_def.transform_type == TransformType.TRANSLATE:
                return PowerPointEffectType.MOTION_PATH

        elif animation_def.animation_type == AnimationType.ANIMATE_MOTION:
            return PowerPointEffectType.MOTION_PATH

        # Default to emphasis for unhandled cases
        return PowerPointEffectType.EMPHASIS

    def process_combined_transform_animation(self, element: ET.Element,
                                            context: ConversionContext) -> str:
        """
        Process animation with combined transforms.

        Args:
            element: SVG animateTransform element
            context: Conversion context

        Returns:
            PowerPoint animation XML for combined transforms
        """
        # Check if this is a transform animation with multiple values
        animation_def = self._parse_animation_element(element, context.svg_root)
        if not animation_def or animation_def.animation_type != AnimationType.ANIMATE_TRANSFORM:
            return ""

        # Check for additive or accumulate attributes
        additive = element.get('additive', 'replace')
        accumulate = element.get('accumulate', 'none')

        # Get animation values
        if not animation_def.values or len(animation_def.values) < 2:
            return ""

        # Generate transform animation using matrix system
        from_transform = self._build_transform_string(
            animation_def.transform_type, animation_def.values[0]
        )
        to_transform = self._build_transform_string(
            animation_def.transform_type, animation_def.values[-1]
        )

        duration_ms = int(animation_def.timing.duration * 1000)

        # Generate PowerPoint animation XML
        xml = self.transform_generator.generate_transform_animation(
            from_transform, to_transform, duration_ms,
            animation_def.element_id or "unknown"
        )

        # Handle additive mode
        if additive == 'sum' and xml:
            # Wrap in additive behavior
            xml = f'''<a:animEffect additive="sum">
  {xml}
</a:animEffect>'''

        return xml

    def _build_transform_string(self, transform_type: TransformType, value: str) -> str:
        """
        Build SVG transform string from type and value.

        Args:
            transform_type: Type of transform
            value: Transform value string

        Returns:
            SVG transform string
        """
        if transform_type == TransformType.TRANSLATE:
            return f"translate({value})"
        elif transform_type == TransformType.SCALE:
            return f"scale({value})"
        elif transform_type == TransformType.ROTATE:
            return f"rotate({value})"
        elif transform_type == TransformType.SKEWX:
            return f"skewX({value})"
        elif transform_type == TransformType.SKEWY:
            return f"skewY({value})"
        else:
            return value

    def _extract_custom_attributes(self, animation_def: AnimationDefinition) -> Dict[str, Any]:
        """
        Extract custom attributes for PowerPoint animation.

        Args:
            animation_def: SMIL animation definition

        Returns:
            Dictionary of custom attributes
        """
        attributes = {}

        if animation_def.animation_type == AnimationType.ANIMATE:
            if animation_def.target_attribute in ["fill", "stroke"]:
                # Extract color values
                if animation_def.values and len(animation_def.values) >= 2:
                    attributes['from_color'] = animation_def.values[0]
                    attributes['to_color'] = animation_def.values[-1]

        elif animation_def.animation_type == AnimationType.ANIMATE_TRANSFORM:
            if animation_def.transform_type == TransformType.SCALE:
                # Extract scale factor
                if animation_def.values and len(animation_def.values) >= 2:
                    try:
                        scale_factor = float(animation_def.values[-1])
                        attributes['scale_factor'] = scale_factor
                    except ValueError:
                        attributes['scale_factor'] = 1.5  # Default

            elif animation_def.transform_type == TransformType.ROTATE:
                # Extract rotation degrees
                if animation_def.values:
                    try:
                        # Parse rotation values like "0 50 50;360 50 50"
                        rotation_str = animation_def.values[-1]
                        if ' ' in rotation_str:
                            rotation_degrees = float(rotation_str.split()[0])
                        else:
                            rotation_degrees = float(rotation_str)
                        attributes['rotation_degrees'] = rotation_degrees
                    except (ValueError, IndexError):
                        attributes['rotation_degrees'] = 360  # Default

            elif animation_def.transform_type == TransformType.TRANSLATE:
                # Convert translate values to path data
                if animation_def.values:
                    path_data = self._translate_values_to_path(animation_def.values)
                    attributes['path_data'] = path_data

        elif animation_def.animation_type == AnimationType.ANIMATE_MOTION:
            # Extract path data directly from values (stored there during parsing)
            if animation_def.values and len(animation_def.values) > 0:
                attributes['path_data'] = animation_def.values[0]
            else:
                attributes['path_data'] = 'M 0,0 L 100,0'  # Default path

        return attributes

    def _map_animation_easing(self, animation_def: AnimationDefinition) -> Tuple[int, int]:
        """
        Map SVG animation easing to PowerPoint acceleration/deceleration values.

        Args:
            animation_def: SMIL animation definition

        Returns:
            Tuple of (acceleration, deceleration) values (0-100000)
        """
        # Check for keySplines (Bezier easing)
        if animation_def.key_splines and len(animation_def.key_splines) > 0:
            return PowerPointEasingMapper.map_keysplines_to_powerpoint(animation_def.key_splines)

        # Check calcMode for basic easing types
        if animation_def.calc_mode:
            calc_mode = animation_def.calc_mode.lower()
            if calc_mode == "linear":
                return PowerPointEasingMapper.map_common_easing_to_powerpoint("linear")
            elif calc_mode == "discrete":
                # Discrete mode doesn't really have easing, but can map to step-like behavior
                return 0, 0
            elif calc_mode == "spline":
                # If spline mode but no keySplines, use default ease
                return PowerPointEasingMapper.map_common_easing_to_powerpoint("ease")

        # Default to linear (no easing)
        return 0, 0

    def _translate_values_to_path(self, translate_values: List[str]) -> str:
        """
        Convert translate values to SVG path data.

        Args:
            translate_values: List of translate values like ["0,0", "50,0", "0,0"]

        Returns:
            SVG path data string
        """
        if not translate_values:
            return 'M 0,0 L 0,0'

        path_parts = ['M 0,0']  # Start at origin

        for value in translate_values[1:]:  # Skip first value (assumed to be 0,0)
            try:
                if ',' in value:
                    x, y = value.split(',')
                    path_parts.append(f'L {float(x)},{float(y)}')
                else:
                    # Single value, assume X translation
                    path_parts.append(f'L {float(value)},0')
            except ValueError:
                continue

        return ' '.join(path_parts)

    def process_animation_sequence(self, context: ConversionContext) -> str:
        """
        Process all collected animations as a coordinated sequence with advanced timing.

        Args:
            context: Conversion context

        Returns:
            PowerPoint animation sequence XML
        """
        if not self.animations:
            return ""

        # Reset timing converter for new sequence
        self.timing_converter.reset()

        # Register all animations with timing converter
        for animation in self.animations:
            # Parse begin reference for advanced timing
            begin_str = context.svg_root.xpath(f'//*[@id="{animation.element_id}"]//animate/@begin')
            if begin_str:
                begin_reference = TimingReference.parse(begin_str[0])
            else:
                begin_reference = TimingReference(None, TimingEventType.ABSOLUTE_TIME, animation.timing.begin)

            # Register with timing converter
            self.timing_converter.register_animation(
                animation_id=animation.element_id or f"anim_{id(animation)}",
                duration=animation.timing.duration,
                begin_reference=begin_reference,
                repeat_count=animation.timing.repeat_count
            )

        # Validate timing references
        timing_issues = self.timing_converter.validate_timing_references()
        if timing_issues:
            # Log issues but continue processing
            self.logger.warning(f"Timing validation issues: {timing_issues}")

        # Calculate timeline
        timeline = self.timing_converter.calculate_animation_timeline()

        # Generate PowerPoint sequence
        sequence_config = self.timing_converter.generate_powerpoint_timing_sequence(timeline)
        sequence_xml = self.timing_generator.generate_sequence_xml(sequence_config)

        return sequence_xml

    def process_animated_elements(self, context: ConversionContext, 
                                conversion_mode: str = "static") -> Dict[str, str]:
        """Process all animated elements and return static or animated versions."""
        if not self.animations:
            return {}
        
        if conversion_mode == "static":
            return self._generate_static_representation(context)
        elif conversion_mode == "keyframes":
            return self._generate_keyframe_sequence(context)
        elif conversion_mode == "powerpoint_animation":
            return self._generate_powerpoint_animations(context)
        else:
            return {}
    
    def _parse_animation_element(self, element: ET.Element, svg_root: Optional[ET.Element] = None) -> Optional[AnimationDefinition]:
        """Parse SVG animation element."""
        tag = element.tag.split('}')[-1]  # Remove namespace
        
        try:
            animation_type = AnimationType(tag)
        except ValueError:
            return None
        
        # Get target element
        target_id = element.get('targetElement') or self._find_parent_id(element)
        if not target_id:
            return None
        
        # Get target attribute (not required for animateMotion)
        if animation_type == AnimationType.ANIMATE_MOTION:
            attribute_name = 'motion'  # Virtual attribute for motion path
            # For animateMotion, use the path attribute as the value
            path = element.get('path', '')
            if path:
                values = [path]
            else:
                # Check for mpath child element referencing a path
                mpath = element.find('{http://www.w3.org/2000/svg}mpath')
                if mpath is not None:
                    href = mpath.get('href', '')
                    resolved_path = self._resolve_mpath_reference(href, svg_root)
                    values = [resolved_path] if resolved_path else ['M 0,0']
                else:
                    values = ['M 0,0']  # Default path
        else:
            attribute_name = element.get('attributeName', '')
            if not attribute_name:
                return None

            # Parse animation values
            values = []
            values_attr = element.get('values')
            if values_attr:
                values = [v.strip() for v in values_attr.split(';')]
            else:
                # Use from/to/by values
                from_val = element.get('from')
                to_val = element.get('to')
                by_val = element.get('by')

                if from_val and to_val:
                    values = [from_val, to_val]
                elif to_val:
                    values = [to_val]  # Animate to specified value

            if not values:
                return None
        
        # Parse timing
        timing = self._parse_animation_timing(element)
        
        # Parse key times
        key_times = None
        key_times_attr = element.get('keyTimes')
        if key_times_attr:
            try:
                key_times = [float(t.strip()) for t in key_times_attr.split(';')]
            except ValueError:
                pass

        # Parse key splines for Bezier easing
        key_splines = None
        key_splines_attr = element.get('keySplines')
        if key_splines_attr:
            try:
                # Parse semicolon-separated spline definitions
                spline_segments = key_splines_attr.split(';')
                key_splines = []
                for segment in spline_segments:
                    # Each segment has 4 values: x1 y1 x2 y2
                    spline_values = [float(v.strip()) for v in segment.strip().split()]
                    if len(spline_values) == 4:
                        key_splines.append(spline_values)
            except ValueError:
                key_splines = None

        # Parse calculation mode
        calc_mode = element.get('calcMode', 'linear').lower()
        
        # Parse transform type for animateTransform
        transform_type = None
        if animation_type == AnimationType.ANIMATE_TRANSFORM:
            transform_type_str = element.get('type', '')
            try:
                transform_type = TransformType(transform_type_str)
            except ValueError:
                pass
        
        return AnimationDefinition(
            element_id=target_id,
            animation_type=animation_type,
            target_attribute=attribute_name,
            values=values,
            key_times=key_times,
            key_splines=key_splines,
            timing=timing,
            transform_type=transform_type,
            calc_mode=calc_mode
        )
    
    def _parse_animation_timing(self, element: ET.Element) -> AnimationTiming:
        """Parse animation timing attributes with advanced timing support."""
        # Parse begin time (now supports complex timing references)
        begin_str = element.get('begin', '0s')
        begin_reference = TimingReference.parse(begin_str)

        # For now, convert to simple float for backward compatibility
        # Advanced timing will be handled separately in timing converter
        if begin_reference.event_type.value == "absolute":
            begin = begin_reference.offset
        else:
            begin = 0.0  # Will be resolved later by timing converter

        # Parse duration with constraints
        dur_str = element.get('dur', '1s')
        duration = self._parse_time_value(dur_str)

        # Handle min/max duration constraints
        min_dur_str = element.get('min')
        max_dur_str = element.get('max')

        if min_dur_str:
            min_duration = self._parse_time_value(min_dur_str)
            duration = max(duration, min_duration)

        if max_dur_str:
            max_duration = self._parse_time_value(max_dur_str)
            duration = min(duration, max_duration)

        # Parse repeat count
        repeat_count = element.get('repeatCount', '1')
        if repeat_count == 'indefinite':
            repeat_count_val = 'indefinite'
        else:
            try:
                repeat_count_val = int(float(repeat_count))
            except ValueError:
                repeat_count_val = 1
        
        # Parse fill mode
        fill_str = element.get('fill', 'remove')
        fill_mode = FillMode.FREEZE if fill_str == 'freeze' else FillMode.REMOVE
        
        return AnimationTiming(
            begin=begin,
            duration=duration,
            repeat_count=repeat_count_val,
            fill_mode=fill_mode
        )
    
    def _parse_time_value(self, time_str: str) -> float:
        """Parse time value (supports s, ms, min, h)."""
        if not time_str:
            return 0.0
        
        time_str = time_str.strip().lower()
        
        if time_str.endswith('ms'):
            return float(time_str[:-2]) / 1000.0
        elif time_str.endswith('s'):
            return float(time_str[:-1])
        elif time_str.endswith('min'):
            return float(time_str[:-3]) * 60.0
        elif time_str.endswith('h'):
            return float(time_str[:-1]) * 3600.0
        else:
            # Assume seconds if no unit
            try:
                return float(time_str)
            except ValueError:
                return 0.0
    
    def _find_parent_id(self, element: ET.Element) -> Optional[str]:
        """Find the ID of the parent element being animated."""
        parent = element.getparent()
        if parent is not None:
            parent_id = parent.get('id')
            if parent_id:
                return parent_id
        return None

    def _resolve_mpath_reference(self, href: str, svg_root: ET.Element) -> Optional[str]:
        """
        Resolve mpath href reference to actual path data.

        Args:
            href: The href attribute value (e.g., "#complexPath")
            svg_root: The SVG root element to search in

        Returns:
            The resolved path data string, or None if not found
        """
        if not href.startswith('#'):
            return None

        # Remove the # prefix to get the element ID
        element_id = href[1:]

        # Find the referenced element by ID
        # Use XPath to find element with matching id attribute
        referenced_elements = svg_root.xpath(f'//*[@id="{element_id}"]')

        if not referenced_elements:
            return None

        referenced_element = referenced_elements[0]

        # Check if it's a path element
        if referenced_element.tag.endswith('path'):
            return referenced_element.get('d', '')

        return None
    
    def _generate_static_representation(self, context: ConversionContext) -> Dict[str, str]:
        """Generate static representation at specified time point."""
        element_modifications = {}
        
        for animation in self.animations:
            # Get value at static time point
            static_value = animation.get_value_at_time(self.static_time)
            if static_value:
                if animation.element_id not in element_modifications:
                    element_modifications[animation.element_id] = {}
                element_modifications[animation.element_id][animation.target_attribute] = static_value
        
        return element_modifications
    
    def _generate_keyframe_sequence(self, context: ConversionContext) -> Dict[str, str]:
        """Generate sequence of keyframes for animation."""
        if not self.animations:
            return {}
        
        # Find animation timeline bounds
        max_end_time = 0.0
        for animation in self.animations:
            end_time = animation.timing.get_end_time()
            if end_time != float('inf'):
                max_end_time = max(max_end_time, end_time)
        
        if max_end_time == 0.0:
            max_end_time = 5.0  # Default 5 second timeline
        
        # Generate keyframe times
        keyframe_times = []
        time_step = max_end_time / self.max_keyframes
        for i in range(self.max_keyframes + 1):
            keyframe_times.append(i * time_step)
        
        # Generate scenes for each keyframe
        scenes = []
        for time in keyframe_times:
            element_states = {}
            
            for animation in self.animations:
                value = animation.get_value_at_time(time)
                if value:
                    if animation.element_id not in element_states:
                        element_states[animation.element_id] = {}
                    element_states[animation.element_id][animation.target_attribute] = value
            
            scenes.append(AnimationScene(time=time, element_states=element_states))
        
        # Convert to output format
        return {
            'animation_type': 'keyframe_sequence',
            'scenes': scenes,
            'total_duration': max_end_time,
            'frame_count': len(scenes)
        }
    
    def _generate_powerpoint_animations(self, context: ConversionContext) -> Dict[str, str]:
        """Generate PowerPoint-compatible animation effects."""
        powerpoint_effects = []
        
        for animation in self.animations:
            # Map SVG animations to PowerPoint effects
            effect = self._map_to_powerpoint_effect(animation)
            if effect:
                powerpoint_effects.append(effect)
        
        if not powerpoint_effects:
            # Fallback to static representation
            return self._generate_static_representation(context)
        
        return {
            'animation_type': 'powerpoint_effects',
            'effects': powerpoint_effects
        }
    
    def _map_to_powerpoint_effect(self, animation: AnimationDefinition) -> Optional[Dict[str, Any]]:
        """Map SVG animation to PowerPoint effect."""
        
        if animation.animation_type == AnimationType.ANIMATE:
            if animation.target_attribute == 'opacity':
                # Fade in/out effect
                start_opacity = float(animation.values[0]) if animation.values else 1.0
                end_opacity = float(animation.values[-1]) if len(animation.values) > 1 else start_opacity
                
                if start_opacity < end_opacity:
                    return {
                        'type': 'fade_in',
                        'element_id': animation.element_id,
                        'duration': animation.timing.duration,
                        'delay': animation.timing.begin
                    }
                elif start_opacity > end_opacity:
                    return {
                        'type': 'fade_out',
                        'element_id': animation.element_id,
                        'duration': animation.timing.duration,
                        'delay': animation.timing.begin
                    }
        
        elif animation.animation_type == AnimationType.ANIMATE_TRANSFORM:
            if animation.transform_type == TransformType.TRANSLATE:
                # Motion path effect
                return {
                    'type': 'motion_path',
                    'element_id': animation.element_id,
                    'values': animation.values,
                    'duration': animation.timing.duration,
                    'delay': animation.timing.begin
                }
            elif animation.transform_type == TransformType.SCALE:
                # Grow/shrink effect
                return {
                    'type': 'scale',
                    'element_id': animation.element_id,
                    'values': animation.values,
                    'duration': animation.timing.duration,
                    'delay': animation.timing.begin
                }
            elif animation.transform_type == TransformType.ROTATE:
                # Spin effect
                return {
                    'type': 'spin',
                    'element_id': animation.element_id,
                    'values': animation.values,
                    'duration': animation.timing.duration,
                    'delay': animation.timing.begin
                }
        
        # Complex animations that don't map well to PowerPoint
        return None
    
    def get_animation_summary(self) -> Dict[str, Any]:
        """Get summary of animation complexity and recommendations."""
        if not self.animations:
            return {'has_animations': False}
        
        # Analyze animation complexity
        total_animations = len(self.animations)
        transform_animations = sum(1 for a in self.animations if a.animation_type == AnimationType.ANIMATE_TRANSFORM)
        color_animations = sum(1 for a in self.animations if a.animation_type == AnimationType.ANIMATE_COLOR)
        complex_animations = sum(1 for a in self.animations if len(a.values) > 2)
        
        # Calculate total timeline
        max_duration = 0.0
        for animation in self.animations:
            end_time = animation.timing.get_end_time()
            if end_time != float('inf'):
                max_duration = max(max_duration, end_time)
        
        # Determine complexity level
        if total_animations <= 3 and complex_animations == 0:
            complexity = 'simple'
            recommendation = 'PowerPoint animation mapping'
        elif total_animations <= 10 and complex_animations <= 2:
            complexity = 'moderate'
            recommendation = 'Multi-slide keyframe sequence'
        else:
            complexity = 'complex'
            recommendation = 'Static representation or rasterization'
        
        return {
            'has_animations': True,
            'total_animations': total_animations,
            'transform_animations': transform_animations,
            'color_animations': color_animations,
            'complex_animations': complex_animations,
            'max_duration': max_duration,
            'complexity': complexity,
            'recommendation': recommendation
        }