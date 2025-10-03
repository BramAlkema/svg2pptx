#!/usr/bin/env python3
"""
PowerPoint Animation Generation for SVG2PPTX

This module provides PowerPoint-specific animation conversion, generating
DrawingML animation XML from animation definitions. Following ADR-006
animation system architecture and integrating with existing PowerPoint
generation infrastructure.

Key Features:
- PowerPoint DrawingML animation XML generation
- SMIL to PowerPoint animation mapping
- Timeline scene to PowerPoint sequence conversion
- Animation synchronization and timing
- Integration with existing PowerPoint generation
"""

from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
import math
import logging
from lxml import etree as ET
from lxml.etree import Element

from .core import (
    AnimationDefinition, AnimationScene, AnimationType,
    TransformType, CalcMode, FillMode
)
from .enhanced_animation_builder import EnhancedAnimationBuilder


@dataclass
class PowerPointAnimationSequence:
    """PowerPoint animation sequence containing timing and animations."""
    sequence_id: int
    animations: List[Element]
    total_duration_ms: int
    timing_root: str


class PowerPointAnimationGenerator:
    """
    Generates PowerPoint DrawingML animations from animation definitions.

    This class converts SMIL animations to PowerPoint's native animation format,
    creating the necessary DrawingML XML for integration into PPTX files.
    """

    def __init__(self):
        """Initialize PowerPoint animation generator."""
        self.animation_id_counter = 1
        self.sequence_id_counter = 1
        self.animation_builder = EnhancedAnimationBuilder()
        self.logger = logging.getLogger(__name__)

    def generate_animation_sequence(
        self,
        animations: List[AnimationDefinition],
        timeline_scenes: List[AnimationScene]
    ) -> str:
        """
        Generate complete PowerPoint animation sequence.

        Args:
            animations: List of animation definitions
            timeline_scenes: Timeline scenes for synchronization

        Returns:
            PowerPoint animation XML string
        """
        if not animations:
            return ""

        # Convert each animation to PowerPoint format
        pptx_animations = []
        for animation in animations:
            pptx_element = self._convert_animation_to_powerpoint(animation)
            if pptx_element is not None:
                pptx_animations.append(pptx_element)

        if not pptx_animations:
            return ""

        # Create timing sequence wrapper
        sequence = self._create_animation_sequence(pptx_animations, timeline_scenes)
        return self._generate_timing_root(sequence)

    def _convert_animation_to_powerpoint(self, animation: AnimationDefinition) -> Optional[Element]:
        """Convert single animation definition to PowerPoint XML."""
        # Map SMIL animation types to PowerPoint equivalents
        if animation.animation_type == AnimationType.ANIMATE:
            return self._generate_property_animation(animation)
        elif animation.animation_type == AnimationType.ANIMATE_TRANSFORM:
            return self._generate_transform_animation(animation)
        elif animation.animation_type == AnimationType.ANIMATE_COLOR:
            return self._generate_color_animation(animation)
        elif animation.animation_type == AnimationType.ANIMATE_MOTION:
            return self._generate_motion_animation(animation)
        elif animation.animation_type == AnimationType.SET:
            return self._generate_set_animation(animation)
        else:
            return None

    def _generate_property_animation(self, animation: AnimationDefinition) -> Element:
        """Generate animation for general property changes."""
        anim_id = self._get_next_animation_id()
        duration_ms = int(animation.timing.duration * 1000)
        delay_ms = int(animation.timing.begin * 1000)

        # Map common attributes to PowerPoint animation types
        attribute = animation.target_attribute.lower()

        if attribute in ['opacity', 'fill-opacity', 'stroke-opacity']:
            return self._generate_opacity_animation(animation, anim_id, duration_ms, delay_ms)
        elif attribute in ['width', 'height', 'r', 'rx', 'ry']:
            return self._generate_size_animation(animation, anim_id, duration_ms, delay_ms)
        elif attribute in ['x', 'y', 'cx', 'cy']:
            return self._generate_position_animation(animation, anim_id, duration_ms, delay_ms)
        else:
            return self._generate_generic_property_animation(animation, anim_id, duration_ms, delay_ms)

    def _generate_opacity_animation(self, animation: AnimationDefinition, anim_id: int, duration_ms: int, delay_ms: int) -> Element:
        """Generate opacity animation (fade effect) using enhanced animation builder."""
        return self.animation_builder.generate_opacity_animation(animation, anim_id, duration_ms, delay_ms)

    def _generate_transform_animation(self, animation: AnimationDefinition) -> Element:
        """Generate transform animation (scale, rotate, translate)."""
        anim_id = self._get_next_animation_id()
        duration_ms = int(animation.timing.duration * 1000)
        delay_ms = int(animation.timing.begin * 1000)

        if animation.transform_type == TransformType.SCALE:
            return self._generate_scale_animation(animation, anim_id, duration_ms, delay_ms)
        elif animation.transform_type == TransformType.ROTATE:
            return self._generate_rotation_animation(animation, anim_id, duration_ms, delay_ms)
        elif animation.transform_type == TransformType.TRANSLATE:
            return self._generate_translation_animation(animation, anim_id, duration_ms, delay_ms)
        else:
            return self._generate_generic_transform_animation(animation, anim_id, duration_ms, delay_ms)

    def _generate_scale_animation(self, animation: AnimationDefinition, anim_id: int, duration_ms: int, delay_ms: int) -> Element:
        """Generate scale/grow/shrink animation using enhanced animation builder."""
        return self.animation_builder.generate_scale_animation(animation, anim_id, duration_ms, delay_ms)

    def _generate_rotation_animation(self, animation: AnimationDefinition, anim_id: int, duration_ms: int, delay_ms: int) -> Element:
        """Generate rotation/spin animation using enhanced animation builder."""
        return self.animation_builder.generate_rotation_animation(animation, anim_id, duration_ms, delay_ms)

    def _generate_color_animation(self, animation: AnimationDefinition) -> Element:
        """Generate color change animation using enhanced animation builder."""
        anim_id = self._get_next_animation_id()
        duration_ms = int(animation.timing.duration * 1000)
        delay_ms = int(animation.timing.begin * 1000)

        return self.animation_builder.generate_color_animation(animation, anim_id, duration_ms, delay_ms)

    def _generate_motion_animation(self, animation: AnimationDefinition) -> Element:
        """Generate motion path animation using enhanced animation builder."""
        anim_id = self._get_next_animation_id()
        duration_ms = int(animation.timing.duration * 1000)
        delay_ms = int(animation.timing.begin * 1000)

        return self.animation_builder.generate_motion_animation(animation, anim_id, duration_ms, delay_ms)

    def _generate_set_animation(self, animation: AnimationDefinition) -> Element:
        """Generate set animation (instant property change) using enhanced animation builder."""
        anim_id = self._get_next_animation_id()
        delay_ms = int(animation.timing.begin * 1000)

        return self.animation_builder.generate_set_animation(animation, anim_id, delay_ms)

    def _generate_generic_property_animation(self, animation: AnimationDefinition, anim_id: int, duration_ms: int, delay_ms: int) -> Element:
        """Generate generic property animation using enhanced animation builder."""
        return self.animation_builder.generate_generic_animation(animation, anim_id, duration_ms, delay_ms)

    def _generate_size_animation(self, animation: AnimationDefinition, anim_id: int, duration_ms: int, delay_ms: int) -> Element:
        """Generate size animation (width, height, radius) using enhanced animation builder."""
        return self.animation_builder.generate_generic_animation(animation, anim_id, duration_ms, delay_ms)

    def _generate_position_animation(self, animation: AnimationDefinition, anim_id: int, duration_ms: int, delay_ms: int) -> Element:
        """Generate position animation (x, y, cx, cy) using enhanced animation builder."""
        return self.animation_builder.generate_generic_animation(animation, anim_id, duration_ms, delay_ms)

    def _generate_translation_animation(self, animation: AnimationDefinition, anim_id: int, duration_ms: int, delay_ms: int) -> Element:
        """Generate translation animation using enhanced animation builder."""
        return self.animation_builder.generate_generic_animation(animation, anim_id, duration_ms, delay_ms)

    def _generate_generic_transform_animation(self, animation: AnimationDefinition, anim_id: int, duration_ms: int, delay_ms: int) -> Element:
        """Generate generic transform animation using enhanced animation builder."""
        return self.animation_builder.generate_generic_animation(animation, anim_id, duration_ms, delay_ms)

    def _generate_easing_attributes(self, animation: AnimationDefinition) -> str:
        """Generate easing attributes from keySplines."""
        if not animation.key_splines or animation.calc_mode != CalcMode.SPLINE:
            return ""

        # Use first keySpline for acceleration/deceleration
        spline = animation.key_splines[0]
        if len(spline) != 4:
            return ""

        # Convert Bezier curve to PowerPoint acceleration/deceleration
        accel, decel = self._map_bezier_to_powerpoint_easing(spline)

        attrs = ""
        if accel > 0:
            attrs += f' accel="{accel}"'
        if decel > 0:
            attrs += f' decel="{decel}"'

        return attrs

    def _map_bezier_to_powerpoint_easing(self, spline: List[float]) -> Tuple[int, int]:
        """Map Bezier keySpline to PowerPoint acceleration/deceleration values."""
        x1, y1, x2, y2 = spline

        # Analyze curve characteristics for acceleration (ease-in)
        accel = 0
        if x1 > 0 and y1 / x1 < 1.0:  # Slow start
            accel = min(50000, int((1.0 - y1/x1) * 50000))

        # Analyze curve characteristics for deceleration (ease-out)
        decel = 0
        if x2 < 1.0 and (1.0 - y2) / (1.0 - x2) < 1.0:  # Slow end
            decel = min(50000, int((1.0 - (1.0 - y2)/(1.0 - x2)) * 50000))

        return accel, decel

    def _generate_repeat_attribute(self, animation: AnimationDefinition) -> str:
        """Generate repeat attribute for animation timing."""
        if animation.timing.repeat_count == 1:
            return ""
        elif animation.timing.repeat_count == "indefinite":
            return ' repeatCount="indefinite"'
        else:
            try:
                count = int(animation.timing.repeat_count)
                return f' repeatCount="{count}"'
            except (ValueError, TypeError):
                return ""

    def _create_animation_sequence(
        self,
        animations: List[Element],
        timeline_scenes: List[AnimationScene]
    ) -> PowerPointAnimationSequence:
        """Create PowerPoint animation sequence from individual animations."""
        sequence_id = self._get_next_sequence_id()

        # Calculate total duration from timeline scenes
        total_duration_ms = 0
        if timeline_scenes:
            total_duration_ms = int(timeline_scenes[-1].time * 1000)

        return PowerPointAnimationSequence(
            sequence_id=sequence_id,
            animations=animations,
            total_duration_ms=total_duration_ms,
            timing_root=""
        )

    def _generate_timing_root(self, sequence: PowerPointAnimationSequence) -> str:
        """Generate complete timing root with animation sequence using enhanced animation builder."""
        # Generate timing root using enhanced builder - no XML parsing needed!
        timing_root = self.animation_builder.generate_timing_root(sequence.sequence_id, sequence.animations)
        return self.animation_builder.element_to_string(timing_root)

    def _parse_scale_value(self, value: str) -> float:
        """Parse scale value from transform string."""
        try:
            # Extract numeric value from scale() transform
            import re
            match = re.search(r'scale\s*\(\s*([\d.]+)', value)
            if match:
                return float(match.group(1))
            return float(value)
        except (ValueError, AttributeError):
            return 1.0

    def _parse_rotation_value(self, value: str) -> float:
        """Parse rotation value from transform string."""
        try:
            # Extract numeric value from rotate() transform
            import re
            match = re.search(r'rotate\s*\(\s*([\d.-]+)', value)
            if match:
                return float(match.group(1))

            # Handle SVG animateTransform format: "angle cx cy"
            parts = value.strip().split()
            if parts:
                return float(parts[0])  # First part is the angle

            return float(value)
        except (ValueError, AttributeError):
            return 0.0

    def _parse_color_value(self, value: str) -> str:
        """Parse color value to hex format using canonical Color system."""
        if not value:
            return "000000"

        try:
            # Use canonical Color class for parsing
            from core.color import Color
            color = Color(value.strip())
            # Get hex without '#' prefix for PowerPoint compatibility
            hex_color = color.hex()
            return hex_color.lstrip('#').upper()
        except (ValueError, TypeError):
            # Fallback to black for invalid colors
            return "000000"

    def _get_next_animation_id(self) -> int:
        """Get next unique animation ID."""
        current_id = self.animation_id_counter
        self.animation_id_counter += 1
        return current_id

    def _get_next_sequence_id(self) -> int:
        """Get next unique sequence ID."""
        current_id = self.sequence_id_counter
        self.sequence_id_counter += 1
        return current_id

    def reset_counters(self):
        """Reset ID counters for new generation session."""
        self.animation_id_counter = 1
        self.sequence_id_counter = 1

    def generate_slide_animation_info(self, animations: List[AnimationDefinition]) -> Dict[str, Any]:
        """Generate metadata about slide animations for PowerPoint integration."""
        return {
            'has_animations': len(animations) > 0,
            'animation_count': len(animations),
            'animated_elements': list(set(anim.element_id for anim in animations)),
            'animation_types': list(set(anim.animation_type.value for anim in animations)),
            'total_duration': max(
                (anim.timing.get_end_time() for anim in animations if anim.timing.get_end_time() != float('inf')),
                default=0.0
            ),
            'requires_timing_root': True
        }