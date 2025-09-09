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
import xml.etree.ElementTree as ET

from .base import BaseConverter
from ..context import ConversionContext
from ..utils.colors import UniversalColorParser
from ..utils.transforms import UniversalTransformEngine
from ..utils.units import UniversalUnitConverter
from ..utils.viewbox import ViewportHandler


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
    key_splines: Optional[List[str]]  # Cubic Bezier easing
    timing: AnimationTiming
    transform_type: Optional[TransformType]  # For animateTransform
    
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
                    return self._interpolate_values(self.values[i], self.values[i + 1], segment_t)
            
            return self.values[-1]
        else:
            # Linear distribution
            segment_size = 1.0 / (len(self.values) - 1)
            segment_index = min(int(t / segment_size), len(self.values) - 2)
            segment_t = (t - segment_index * segment_size) / segment_size
            
            return self._interpolate_values(self.values[segment_index], 
                                          self.values[segment_index + 1], segment_t)
    
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
    
    def _interpolate_colors(self, color1: str, color2: str, t: float) -> str:
        """Interpolate between two colors."""
        parser = UniversalColorParser()
        c1 = parser.parse(color1)
        c2 = parser.parse(color2)
        
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
            
            # Reconstruct transform string
            if self.transform_type == TransformType.TRANSLATE:
                if len(interpolated) >= 2:
                    return f"translate({interpolated[0]}, {interpolated[1]})"
                else:
                    return f"translate({interpolated[0]})"
            elif self.transform_type == TransformType.SCALE:
                if len(interpolated) >= 2:
                    return f"scale({interpolated[0]}, {interpolated[1]})"
                else:
                    return f"scale({interpolated[0]})"
            elif self.transform_type == TransformType.ROTATE:
                if len(interpolated) >= 3:
                    return f"rotate({interpolated[0]}, {interpolated[1]}, {interpolated[2]})"
                else:
                    return f"rotate({interpolated[0]})"
            else:
                return value1
                
        except (ValueError, IndexError):
            return value1 if t < 0.5 else value2


@dataclass
class AnimationScene:
    """Snapshot of all animated elements at a specific time."""
    time: float
    element_states: Dict[str, Dict[str, str]]  # element_id -> {attribute: value}


class AnimationConverter(BaseConverter):
    """Converts SVG animations to static representations or PowerPoint animations."""
    
    supported_elements = ['animate', 'animateTransform', 'animateColor', 'animateMotion', 'set']
    
    def __init__(self):
        super().__init__()
        self.animations: List[AnimationDefinition] = []
        self.color_parser = UniversalColorParser()
        self.transform_engine = UniversalTransformEngine()
        self.unit_converter = UniversalUnitConverter()
        self.viewport_handler = ViewportHandler()
        
        # Animation processing options
        self.max_keyframes = 30  # Maximum keyframes to extract
        self.frame_rate = 24     # Frames per second for analysis
        self.static_time = 0.5   # Time point for static extraction (seconds)
        
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert animation element."""
        # Animation elements don't generate direct output
        # They modify the rendering of their target elements
        animation_def = self._parse_animation_element(element)
        if animation_def:
            self.animations.append(animation_def)
        
        return ""
    
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
    
    def _parse_animation_element(self, element: ET.Element) -> Optional[AnimationDefinition]:
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
        
        # Get target attribute
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
            key_splines=None,  # TODO: Parse keySplines
            timing=timing,
            transform_type=transform_type
        )
    
    def _parse_animation_timing(self, element: ET.Element) -> AnimationTiming:
        """Parse animation timing attributes."""
        # Parse begin time
        begin_str = element.get('begin', '0s')
        begin = self._parse_time_value(begin_str)
        
        # Parse duration
        dur_str = element.get('dur', '1s')
        duration = self._parse_time_value(dur_str)
        
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