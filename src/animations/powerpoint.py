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

from .core import (
    AnimationDefinition, AnimationScene, AnimationType,
    TransformType, CalcMode, FillMode
)


@dataclass
class PowerPointAnimationSequence:
    """PowerPoint animation sequence containing timing and animations."""
    sequence_id: int
    animations: List[str]
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
            pptx_xml = self._convert_animation_to_powerpoint(animation)
            if pptx_xml:
                pptx_animations.append(pptx_xml)

        if not pptx_animations:
            return ""

        # Create timing sequence wrapper
        sequence = self._create_animation_sequence(pptx_animations, timeline_scenes)
        return self._generate_timing_root(sequence)

    def _convert_animation_to_powerpoint(self, animation: AnimationDefinition) -> Optional[str]:
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

    def _generate_property_animation(self, animation: AnimationDefinition) -> str:
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

    def _generate_opacity_animation(self, animation: AnimationDefinition, anim_id: int, duration_ms: int, delay_ms: int) -> str:
        """Generate opacity animation (fade effect)."""
        # Determine fade direction
        if len(animation.values) >= 2:
            start_opacity = float(animation.values[0])
            end_opacity = float(animation.values[-1])
            is_fade_in = end_opacity > start_opacity
        else:
            is_fade_in = True  # Default to fade in

        effect_type = "fadeIn" if is_fade_in else "fadeOut"

        # Generate easing attributes
        easing_attrs = self._generate_easing_attributes(animation)
        repeat_attr = self._generate_repeat_attribute(animation)

        return f'''<a:animEffect>
  <a:cBhvr>
    <a:cTn id="{anim_id}" dur="{duration_ms}" delay="{delay_ms}"{repeat_attr}{easing_attrs}/>
    <a:tgtEl>
      <a:spTgt spid="{animation.element_id}"/>
    </a:tgtEl>
  </a:cBhvr>
  <a:transition in="1" out="0"/>
  <a:filter>
    <a:fade opacity="{animation.values[0] if animation.values else '0'}"/>
  </a:filter>
</a:animEffect>'''

    def _generate_transform_animation(self, animation: AnimationDefinition) -> str:
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

    def _generate_scale_animation(self, animation: AnimationDefinition, anim_id: int, duration_ms: int, delay_ms: int) -> str:
        """Generate scale/grow/shrink animation."""
        # Parse scale values
        if len(animation.values) >= 2:
            start_scale = self._parse_scale_value(animation.values[0])
            end_scale = self._parse_scale_value(animation.values[-1])
        else:
            start_scale, end_scale = 1.0, 1.0

        easing_attrs = self._generate_easing_attributes(animation)
        repeat_attr = self._generate_repeat_attribute(animation)

        return f'''<a:animScale>
  <a:cBhvr>
    <a:cTn id="{anim_id}" dur="{duration_ms}" delay="{delay_ms}"{repeat_attr}{easing_attrs}/>
    <a:tgtEl>
      <a:spTgt spid="{animation.element_id}"/>
    </a:tgtEl>
  </a:cBhvr>
  <a:from>
    <a:pt x="{start_scale}" y="{start_scale}"/>
  </a:from>
  <a:to>
    <a:pt x="{end_scale}" y="{end_scale}"/>
  </a:to>
</a:animScale>'''

    def _generate_rotation_animation(self, animation: AnimationDefinition, anim_id: int, duration_ms: int, delay_ms: int) -> str:
        """Generate rotation/spin animation."""
        # Parse rotation values (convert degrees to PowerPoint's 60000ths of a degree)
        if len(animation.values) >= 2:
            start_rotation = self._parse_rotation_value(animation.values[0])
            end_rotation = self._parse_rotation_value(animation.values[-1])
        else:
            start_rotation, end_rotation = 0, 360

        # Convert to PowerPoint units (60000ths of a degree)
        rotation_delta = int((end_rotation - start_rotation) * 60000)

        easing_attrs = self._generate_easing_attributes(animation)
        repeat_attr = self._generate_repeat_attribute(animation)

        return f'''<a:animRot>
  <a:cBhvr>
    <a:cTn id="{anim_id}" dur="{duration_ms}" delay="{delay_ms}"{repeat_attr}{easing_attrs}/>
    <a:tgtEl>
      <a:spTgt spid="{animation.element_id}"/>
    </a:tgtEl>
  </a:cBhvr>
  <a:by val="{rotation_delta}"/>
</a:animRot>'''

    def _generate_color_animation(self, animation: AnimationDefinition) -> str:
        """Generate color change animation."""
        anim_id = self._get_next_animation_id()
        duration_ms = int(animation.timing.duration * 1000)
        delay_ms = int(animation.timing.begin * 1000)

        # Parse color values
        if len(animation.values) >= 2:
            from_color = self._parse_color_value(animation.values[0])
            to_color = self._parse_color_value(animation.values[-1])
        else:
            from_color = to_color = "000000"

        easing_attrs = self._generate_easing_attributes(animation)
        repeat_attr = self._generate_repeat_attribute(animation)

        # Determine attribute name for PowerPoint
        ppt_attr = "fillColor" if animation.target_attribute == "fill" else "lineColor"

        return f'''<a:animClr>
  <a:cBhvr>
    <a:cTn id="{anim_id}" dur="{duration_ms}" delay="{delay_ms}"{repeat_attr}{easing_attrs}/>
    <a:tgtEl>
      <a:spTgt spid="{animation.element_id}"/>
    </a:tgtEl>
    <a:attrNameLst>
      <a:attrName>{ppt_attr}</a:attrName>
    </a:attrNameLst>
  </a:cBhvr>
  <a:from>
    <a:srgbClr val="{from_color}"/>
  </a:from>
  <a:to>
    <a:srgbClr val="{to_color}"/>
  </a:to>
</a:animClr>'''

    def _generate_motion_animation(self, animation: AnimationDefinition) -> str:
        """Generate motion path animation."""
        anim_id = self._get_next_animation_id()
        duration_ms = int(animation.timing.duration * 1000)
        delay_ms = int(animation.timing.begin * 1000)

        # Use the actual path from the animation values
        path_data = animation.values[0] if animation.values else "M 0,0 L 100,100"

        easing_attrs = self._generate_easing_attributes(animation)
        repeat_attr = self._generate_repeat_attribute(animation)

        return f'''<a:animMotion>
  <a:cBhvr>
    <a:cTn id="{anim_id}" dur="{duration_ms}" delay="{delay_ms}"{repeat_attr}{easing_attrs}/>
    <a:tgtEl>
      <a:spTgt spid="{animation.element_id}"/>
    </a:tgtEl>
  </a:cBhvr>
  <a:path path="{path_data}"/>
</a:animMotion>'''

    def _generate_set_animation(self, animation: AnimationDefinition) -> str:
        """Generate set animation (instant property change)."""
        anim_id = self._get_next_animation_id()
        delay_ms = int(animation.timing.begin * 1000)

        value = animation.values[0] if animation.values else ""

        return f'''<a:set>
  <a:cBhvr>
    <a:cTn id="{anim_id}" dur="1" delay="{delay_ms}"/>
    <a:tgtEl>
      <a:spTgt spid="{animation.element_id}"/>
    </a:tgtEl>
    <a:attrNameLst>
      <a:attrName>{animation.target_attribute}</a:attrName>
    </a:attrNameLst>
  </a:cBhvr>
  <a:to>
    <a:strVal val="{value}"/>
  </a:to>
</a:set>'''

    def _generate_generic_property_animation(self, animation: AnimationDefinition, anim_id: int, duration_ms: int, delay_ms: int) -> str:
        """Generate generic property animation."""
        easing_attrs = self._generate_easing_attributes(animation)
        repeat_attr = self._generate_repeat_attribute(animation)

        from_value = animation.values[0] if animation.values else ""
        to_value = animation.values[-1] if len(animation.values) > 1 else from_value

        return f'''<a:anim>
  <a:cBhvr>
    <a:cTn id="{anim_id}" dur="{duration_ms}" delay="{delay_ms}"{repeat_attr}{easing_attrs}/>
    <a:tgtEl>
      <a:spTgt spid="{animation.element_id}"/>
    </a:tgtEl>
    <a:attrNameLst>
      <a:attrName>{animation.target_attribute}</a:attrName>
    </a:attrNameLst>
  </a:cBhvr>
  <a:tavLst>
    <a:tav tm="0">
      <a:val>
        <a:strVal val="{from_value}"/>
      </a:val>
    </a:tav>
    <a:tav tm="{duration_ms}">
      <a:val>
        <a:strVal val="{to_value}"/>
      </a:val>
    </a:tav>
  </a:tavLst>
</a:anim>'''

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
        animations: List[str],
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
        """Generate complete timing root with animation sequence."""
        animations_xml = "\n      ".join(sequence.animations)

        return f'''<a:timing>
  <a:tnLst>
    <a:par>
      <a:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">
        <a:childTnLst>
          <a:seq concurrent="1" nextAc="seek">
            <a:cTn id="{sequence.sequence_id}" dur="indefinite" nodeType="mainSeq">
              <a:childTnLst>
                <a:par>
                  <a:cTn id="{sequence.sequence_id + 1}" fill="hold">
                    <a:stCondLst>
                      <a:cond delay="0"/>
                    </a:stCondLst>
                    <a:childTnLst>
                      {animations_xml}
                    </a:childTnLst>
                  </a:cTn>
                </a:par>
              </a:childTnLst>
            </a:cTn>
          </a:seq>
        </a:childTnLst>
      </a:cTn>
    </a:par>
  </a:tnLst>
</a:timing>'''

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
            from ..color import Color
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