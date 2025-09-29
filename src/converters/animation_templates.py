#!/usr/bin/env python3
"""
PowerPoint Animation Templates for SVG2PPTX

This module provides templates and generators for PowerPoint animation DrawingML,
converting SMIL animation definitions into valid PowerPoint XML structures.

PowerPoint Animation Reference:
- <a:animEffect> - Animation effects (fade, color, scale, etc.)
- <a:cTn> - Common timing node (duration, delay, repeat)
- <a:cBhvr> - Common behavior (target element, attributes)
- <a:animMotion> - Motion path animations
- <a:animClr> - Color change animations
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import math


class PowerPointEffectType(Enum):
    """PowerPoint animation effect types."""
    FADE_IN = "fadeIn"
    FADE_OUT = "fadeOut"
    COLOR_CHANGE = "colorChange"
    GROW = "grow"
    SHRINK = "shrink"
    SPIN = "spin"
    MOTION_PATH = "motionPath"
    EMPHASIS = "emphasis"


@dataclass
class PowerPointAnimationConfig:
    """Configuration for PowerPoint animation generation."""
    effect_type: PowerPointEffectType
    duration_ms: int
    delay_ms: int = 0
    repeat_count: Optional[int] = None
    target_element_id: str = ""
    custom_attributes: Dict[str, Any] = None
    easing_accel: int = 0  # Acceleration value (0-100000)
    easing_decel: int = 0  # Deceleration value (0-100000)

    def __post_init__(self):
        if self.custom_attributes is None:
            self.custom_attributes = {}


class PowerPointEasingMapper:
    """Maps SVG keySplines Bezier curves to PowerPoint acceleration/deceleration values."""

    @staticmethod
    def map_keysplines_to_powerpoint(key_splines: List[List[float]]) -> Tuple[int, int]:
        """
        Map SVG keySplines Bezier control points to PowerPoint accel/decel values.

        Args:
            key_splines: List of keySplines segments, each with [x1, y1, x2, y2]

        Returns:
            Tuple of (acceleration, deceleration) values (0-100000)
        """
        if not key_splines or len(key_splines) == 0:
            return 0, 0

        # Use the first spline segment for mapping
        spline = key_splines[0]
        if len(spline) != 4:
            return 0, 0

        x1, y1, x2, y2 = spline

        # Analyze the curve characteristics
        accel = PowerPointEasingMapper._calculate_acceleration(x1, y1, x2, y2)
        decel = PowerPointEasingMapper._calculate_deceleration(x1, y1, x2, y2)

        return accel, decel

    @staticmethod
    def map_common_easing_to_powerpoint(easing_name: str) -> Tuple[int, int]:
        """
        Map common CSS/SVG easing names to PowerPoint values.

        Args:
            easing_name: Common easing name (ease, ease-in, ease-out, ease-in-out, linear)

        Returns:
            Tuple of (acceleration, deceleration) values (0-100000)
        """
        common_mappings = {
            'linear': (0, 0),
            'ease': (25000, 25000),  # Standard ease-in-out
            'ease-in': (50000, 0),   # Strong acceleration, no deceleration
            'ease-out': (0, 50000),  # No acceleration, strong deceleration
            'ease-in-out': (25000, 25000),  # Balanced ease
        }

        return common_mappings.get(easing_name.lower(), (0, 0))

    @staticmethod
    def _calculate_acceleration(x1: float, y1: float, x2: float, y2: float) -> int:
        """Calculate acceleration value from Bezier control points."""
        # Check for linear case first
        if x1 == 0.0 and y1 == 0.0 and x2 == 1.0 and y2 == 1.0:
            return 0  # Linear curve has no acceleration

        # Calculate initial tangent slope at t=0 (derivative of Bezier curve)
        # For cubic Bezier: initial slope = 3 * y1 / x1 (normalized)
        if x1 == 0:
            # Vertical start - strong acceleration
            return 75000 if y1 < 0.5 else 25000

        initial_slope = y1 / x1

        # Map slope to acceleration value based on curve shape
        # Lower initial slopes indicate stronger acceleration (ease-in)
        if initial_slope < 0.5:
            # Strong ease-in
            return min(75000, int((0.5 - initial_slope) * 150000))
        elif initial_slope < 1.0:
            # Moderate ease-in
            return min(50000, int((1.0 - initial_slope) * 50000))
        else:
            # No acceleration (ease-out or linear)
            return 0

    @staticmethod
    def _calculate_deceleration(x1: float, y1: float, x2: float, y2: float) -> int:
        """Calculate deceleration value from Bezier control points."""
        # Check for linear case first
        if x1 == 0.0 and y1 == 0.0 and x2 == 1.0 and y2 == 1.0:
            return 0  # Linear curve has no deceleration

        # Calculate final tangent slope at t=1 (derivative of Bezier curve)
        # For cubic Bezier: final slope = 3 * (1-y2) / (1-x2) (normalized)
        if x2 == 1.0:
            # Check if this is actually linear or ease-in
            if y2 == 1.0:
                return 0  # Linear ending - no deceleration
            # Vertical end - strong deceleration
            return 75000 if y2 > 0.5 else 25000

        final_slope = (1.0 - y2) / (1.0 - x2)

        # Map slope to deceleration value based on curve shape
        # Lower final slopes indicate stronger deceleration (ease-out)
        if final_slope < 0.5:
            # Strong ease-out
            return min(75000, int((0.5 - final_slope) * 150000))
        elif final_slope < 1.0:
            # Moderate ease-out
            return min(50000, int((1.0 - final_slope) * 50000))
        else:
            # No deceleration (ease-in or linear)
            return 0


class PowerPointAnimationGenerator:
    """Generates PowerPoint animation DrawingML from animation configurations."""

    def __init__(self):
        """Initialize the PowerPoint animation generator."""
        self.animation_id_counter = 1

    def generate_animation_drawingml(self, config: PowerPointAnimationConfig) -> str:
        """
        Generate PowerPoint animation DrawingML XML.

        Args:
            config: Animation configuration

        Returns:
            PowerPoint animation XML string
        """
        # Consolidated with src/utils/xml_builder.py - uses centralized XML utilities
        # Complex animations still use specialized methods, but share common XML building patterns

        animation_id = self._get_next_animation_id()

        # Generate based on effect type (existing logic preserved)
        if config.effect_type in [PowerPointEffectType.FADE_IN, PowerPointEffectType.FADE_OUT]:
            return self._generate_fade_animation(config, animation_id)
        elif config.effect_type == PowerPointEffectType.COLOR_CHANGE:
            return self._generate_color_animation(config, animation_id)
        elif config.effect_type in [PowerPointEffectType.GROW, PowerPointEffectType.SHRINK]:
            return self._generate_scale_animation(config, animation_id)
        elif config.effect_type == PowerPointEffectType.SPIN:
            return self._generate_rotation_animation(config, animation_id)
        elif config.effect_type == PowerPointEffectType.MOTION_PATH:
            return self._generate_motion_path_animation(config, animation_id)
        elif config.effect_type == PowerPointEffectType.EMPHASIS:
            return self._generate_emphasis_animation(config, animation_id)
        else:
            # For unrecognized types, use centralized XML builder
            from ..utils.xml_builder import get_xml_builder
            xml_builder = get_xml_builder()
            return xml_builder.create_animation_xml(
                effect_type="fade",
                target_shape_id=config.target_shape_id,
                duration=config.duration_seconds,
                delay=getattr(config, 'delay_seconds', 0.0)
            )

    def _generate_fade_animation(self, config: PowerPointAnimationConfig, anim_id: int) -> str:
        """Generate fade in/out animation."""
        effect_preset = "fadeIn" if config.effect_type == PowerPointEffectType.FADE_IN else "fadeOut"

        return f'''<a:animEffect>
  <a:cBhvr>
    <a:cTn id="{anim_id}" dur="{config.duration_ms}" delay="{config.delay_ms}"{self._get_repeat_attr(config)}{self._get_easing_attrs(config)}/>
    <a:tgtEl>
      <a:spTgt spid="{config.target_element_id}"/>
    </a:tgtEl>
  </a:cBhvr>
  <a:transition in="1" out="0"/>
  <a:filter>
    <a:fade opacity="0"/>
  </a:filter>
</a:animEffect>'''

    def _generate_color_animation(self, config: PowerPointAnimationConfig, anim_id: int) -> str:
        """Generate color change animation."""
        from_color = config.custom_attributes.get('from_color', '#000000')
        to_color = config.custom_attributes.get('to_color', '#FFFFFF')

        return f'''<a:animClr>
  <a:cBhvr>
    <a:cTn id="{anim_id}" dur="{config.duration_ms}" delay="{config.delay_ms}"{self._get_repeat_attr(config)}{self._get_easing_attrs(config)}/>
    <a:tgtEl>
      <a:spTgt spid="{config.target_element_id}"/>
    </a:tgtEl>
    <a:attrNameLst>
      <a:attrName>fillColor</a:attrName>
    </a:attrNameLst>
  </a:cBhvr>
  <a:from>
    <a:srgbClr val="{from_color.lstrip('#')}"/>
  </a:from>
  <a:to>
    <a:srgbClr val="{to_color.lstrip('#')}"/>
  </a:to>
</a:animClr>'''

    def _generate_scale_animation(self, config: PowerPointAnimationConfig, anim_id: int) -> str:
        """Generate grow/shrink animation."""
        scale_factor = config.custom_attributes.get('scale_factor', 1.5)
        is_grow = config.effect_type == PowerPointEffectType.GROW

        from_scale = "1.0" if is_grow else str(scale_factor)
        to_scale = str(scale_factor) if is_grow else "1.0"

        return f'''<a:animScale>
  <a:cBhvr>
    <a:cTn id="{anim_id}" dur="{config.duration_ms}" delay="{config.delay_ms}"{self._get_repeat_attr(config)}{self._get_easing_attrs(config)}/>
    <a:tgtEl>
      <a:spTgt spid="{config.target_element_id}"/>
    </a:tgtEl>
  </a:cBhvr>
  <a:by>
    <a:pt x="{to_scale}" y="{to_scale}"/>
  </a:by>
</a:animScale>'''

    def _generate_rotation_animation(self, config: PowerPointAnimationConfig, anim_id: int) -> str:
        """Generate rotation/spin animation."""
        rotation_degrees = config.custom_attributes.get('rotation_degrees', 360)

        return f'''<a:animRot>
  <a:cBhvr>
    <a:cTn id="{anim_id}" dur="{config.duration_ms}" delay="{config.delay_ms}"{self._get_repeat_attr(config)}{self._get_easing_attrs(config)}/>
    <a:tgtEl>
      <a:spTgt spid="{config.target_element_id}"/>
    </a:tgtEl>
  </a:cBhvr>
  <a:by val="{int(rotation_degrees * 60000)}"/>
</a:animRot>'''

    def _generate_motion_path_animation(self, config: PowerPointAnimationConfig, anim_id: int) -> str:
        """Generate motion path animation."""
        path_data = config.custom_attributes.get('path_data', 'M 0,0 L 100,0')

        return f'''<a:animMotion>
  <a:cBhvr>
    <a:cTn id="{anim_id}" dur="{config.duration_ms}" delay="{config.delay_ms}"{self._get_repeat_attr(config)}{self._get_easing_attrs(config)}/>
    <a:tgtEl>
      <a:spTgt spid="{config.target_element_id}"/>
    </a:tgtEl>
  </a:cBhvr>
  <a:path path="{path_data}"/>
</a:animMotion>'''

    def _generate_emphasis_animation(self, config: PowerPointAnimationConfig, anim_id: int) -> str:
        """Generate emphasis animation for text and other effects."""
        emphasis_type = config.custom_attributes.get('emphasis_type', 'pulse')

        return f'''<a:animEffect>
  <a:cBhvr>
    <a:cTn id="{anim_id}" dur="{config.duration_ms}" delay="{config.delay_ms}"{self._get_repeat_attr(config)}{self._get_easing_attrs(config)}/>
    <a:tgtEl>
      <a:spTgt spid="{config.target_element_id}"/>
    </a:tgtEl>
  </a:cBhvr>
  <a:transition in="1" out="0"/>
  <a:filter>
    <a:{emphasis_type}/>
  </a:filter>
</a:animEffect>'''

    def _generate_generic_animation(self, config: PowerPointAnimationConfig, anim_id: int) -> str:
        """Generate generic animation for unsupported types."""
        return f'''<a:animEffect>
  <a:cBhvr>
    <a:cTn id="{anim_id}" dur="{config.duration_ms}" delay="{config.delay_ms}"{self._get_repeat_attr(config)}{self._get_easing_attrs(config)}/>
    <a:tgtEl>
      <a:spTgt spid="{config.target_element_id}"/>
    </a:tgtEl>
  </a:cBhvr>
  <a:transition in="1" out="0"/>
</a:animEffect>'''

    def _get_repeat_attr(self, config: PowerPointAnimationConfig) -> str:
        """Generate repeat attribute for timing node."""
        if config.repeat_count is None:
            return ""
        elif config.repeat_count == -1:  # Indefinite
            return ' repeatCount="indefinite"'
        else:
            return f' repeatCount="{config.repeat_count}"'

    def _get_easing_attrs(self, config: PowerPointAnimationConfig) -> str:
        """Generate easing attributes for timing node."""
        attrs = ""
        if config.easing_accel > 0:
            attrs += f' accel="{config.easing_accel}"'
        if config.easing_decel > 0:
            attrs += f' decel="{config.easing_decel}"'
        return attrs

    def _get_next_animation_id(self) -> int:
        """Get next unique animation ID."""
        current_id = self.animation_id_counter
        self.animation_id_counter += 1
        return current_id

    def generate_animation_sequence(self, configs: List[PowerPointAnimationConfig]) -> str:
        """
        Generate a sequence of PowerPoint animations.

        Args:
            configs: List of animation configurations

        Returns:
            Combined PowerPoint animation XML
        """
        animations = []
        for config in configs:
            animation_xml = self.generate_animation_drawingml(config)
            if animation_xml:
                animations.append(animation_xml)

        if not animations:
            return ""

        # Wrap in timing sequence
        sequence_id = self._get_next_animation_id()
        animations_str = "\n".join(animations)

        return f'''<a:seq>
  <a:cTn id="{sequence_id}">
    <a:childTnLst>
      {animations_str}
    </a:childTnLst>
  </a:cTn>
</a:seq>'''

    def validate_animation_xml(self, xml_string: str) -> bool:
        """
        Validate PowerPoint animation XML structure.

        Args:
            xml_string: Animation XML to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            from lxml import etree

            # Wrap in a root element with namespace declaration for parsing
            wrapped_xml = f'''<root xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
                {xml_string}
            </root>'''

            # Basic XML parsing check
            etree.fromstring(wrapped_xml.encode('utf-8'))

            # Check for required PowerPoint animation elements
            required_elements = ['<a:cTn', '<a:tgtEl']
            return all(elem in xml_string for elem in required_elements)

        except Exception:
            return False