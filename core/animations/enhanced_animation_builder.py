#!/usr/bin/env python3
"""
Enhanced Animation Builder with Template-Based Generation

Replaces string interpolation animation XML generation with proper DOM manipulation
using lxml.etree and XML templates for namespace-aware, validated animation XML.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from lxml import etree as ET
from lxml.etree import Element, QName

from ..io.template_loader import TemplateLoader, get_template_loader
from .core import (
    AnimationDefinition, AnimationType, TransformType, CalcMode, FillMode
)

logger = logging.getLogger(__name__)

# DrawingML Animation Namespaces
A_URI = "http://schemas.openxmlformats.org/drawingml/2006/main"

class EnhancedAnimationBuilder:
    """
    Enhanced animation builder using template-based generation with lxml.etree DOM manipulation.

    Loads XML templates from core/io/templates/ and modifies them using proper
    DOM operations for namespace-aware, validated PowerPoint animation XML.
    """

    def __init__(self, template_loader: Optional[TemplateLoader] = None):
        """Initialize enhanced animation builder.

        Args:
            template_loader: Optional custom template loader.
                           Uses default loader if None.
        """
        self.animation_id_counter = 1
        self.logger = logging.getLogger(__name__)
        self._template_loader = template_loader or get_template_loader()

        # Validate animation templates are available
        self._validate_templates()

    def _validate_templates(self) -> None:
        """
        Validate that animation templates are available and well-formed.

        Raises:
            FileNotFoundError: If animation templates are missing
            ET.XMLSyntaxError: If templates contain invalid XML
        """
        animation_templates = [
            "animation_effect.xml",
            "animation_scale.xml",
            "animation_rotation.xml",
            "animation_color.xml",
            "animation_motion.xml",
            "animation_set.xml",
            "animation_generic.xml",
            "animation_timing_root.xml",
            "animation_sequence.xml"
        ]

        for template_name in animation_templates:
            try:
                self._template_loader.load_template(template_name)
                self.logger.debug(f"Animation template validated: {template_name}")
            except Exception as e:
                self.logger.error(f"Animation template validation failed: {template_name} - {e}")
                raise

    def get_next_animation_id(self) -> int:
        """Get next unique animation ID."""
        current_id = self.animation_id_counter
        self.animation_id_counter += 1
        return current_id

    def reset_animation_id_counter(self) -> None:
        """Reset animation ID counter for testing or new documents."""
        self.animation_id_counter = 1

    def generate_opacity_animation(self, animation: AnimationDefinition, anim_id: int,
                                 duration_ms: int, delay_ms: int) -> Element:
        """Generate opacity animation (fade effect) using template-based generation."""
        # Load animation effect template
        anim_effect = self._template_loader.load_template("animation_effect.xml")

        # Update common behavior attributes
        self._update_common_behavior(anim_effect, anim_id, duration_ms, delay_ms)
        self._update_target_element(anim_effect, animation.element_id)

        # Determine fade direction and set effect type
        if len(animation.values) >= 2:
            start_opacity = float(animation.values[0])
            end_opacity = float(animation.values[-1])
            is_fade_in = end_opacity > start_opacity
        else:
            is_fade_in = True

        effect_type = "fadeIn" if is_fade_in else "fadeOut"
        filter_elem = anim_effect.find('.//a:filter', {'a': A_URI})
        if filter_elem is not None:
            filter_elem.set('filter', effect_type)

        # Add easing and repeat attributes
        self._add_easing_attributes(anim_effect, animation)
        self._add_repeat_attribute(anim_effect, animation)

        return anim_effect

    def generate_scale_animation(self, animation: AnimationDefinition, anim_id: int,
                               duration_ms: int, delay_ms: int) -> Element:
        """Generate scale/grow/shrink animation using template-based generation."""
        # Load animation scale template
        anim_scale = self._template_loader.load_template("animation_scale.xml")

        # Update common behavior attributes
        self._update_common_behavior(anim_scale, anim_id, duration_ms, delay_ms)
        self._update_target_element(anim_scale, animation.element_id)

        # Parse scale values
        if len(animation.values) >= 2:
            start_scale = self._parse_scale_value(animation.values[0])
            end_scale = self._parse_scale_value(animation.values[-1])
        else:
            start_scale, end_scale = 1.0, 1.0

        # Update from/to scale values
        from_pt = anim_scale.find('.//a:from/a:pt', {'a': A_URI})
        if from_pt is not None:
            from_pt.set('x', str(start_scale))
            from_pt.set('y', str(start_scale))

        to_pt = anim_scale.find('.//a:to/a:pt', {'a': A_URI})
        if to_pt is not None:
            to_pt.set('x', str(end_scale))
            to_pt.set('y', str(end_scale))

        # Add easing and repeat attributes
        self._add_easing_attributes(anim_scale, animation)
        self._add_repeat_attribute(anim_scale, animation)

        return anim_scale

    def generate_rotation_animation(self, animation: AnimationDefinition, anim_id: int,
                                  duration_ms: int, delay_ms: int) -> Element:
        """Generate rotation/spin animation using template-based generation."""
        # Load animation rotation template
        anim_rot = self._template_loader.load_template("animation_rotation.xml")

        # Update common behavior attributes
        self._update_common_behavior(anim_rot, anim_id, duration_ms, delay_ms)
        self._update_target_element(anim_rot, animation.element_id)

        # Parse rotation values (convert degrees to PowerPoint's 60000ths of a degree)
        if len(animation.values) >= 2:
            start_rotation = self._parse_rotation_value(animation.values[0])
            end_rotation = self._parse_rotation_value(animation.values[-1])
        else:
            start_rotation, end_rotation = 0, 360

        # Convert to PowerPoint units (60000ths of a degree)
        rotation_delta = int((end_rotation - start_rotation) * 60000)

        # Update rotation value
        by_elem = anim_rot.find('.//a:by', {'a': A_URI})
        if by_elem is not None:
            by_elem.set('val', str(rotation_delta))

        # Add easing and repeat attributes
        self._add_easing_attributes(anim_rot, animation)
        self._add_repeat_attribute(anim_rot, animation)

        return anim_rot

    def generate_color_animation(self, animation: AnimationDefinition, anim_id: int,
                               duration_ms: int, delay_ms: int) -> Element:
        """Generate color change animation using template-based generation."""
        # Load animation color template
        anim_color = self._template_loader.load_template("animation_color.xml")

        # Update common behavior attributes
        self._update_common_behavior(anim_color, anim_id, duration_ms, delay_ms)
        self._update_target_element(anim_color, animation.element_id)

        # Parse color values
        if len(animation.values) >= 2:
            from_color = self._parse_color_value(animation.values[0])
            to_color = self._parse_color_value(animation.values[-1])
        else:
            from_color = to_color = "000000"

        # Update color values
        from_color_elem = anim_color.find('.//a:from/a:srgbClr', {'a': A_URI})
        if from_color_elem is not None:
            from_color_elem.set('val', from_color)

        to_color_elem = anim_color.find('.//a:to/a:srgbClr', {'a': A_URI})
        if to_color_elem is not None:
            to_color_elem.set('val', to_color)

        # Determine attribute name for PowerPoint
        ppt_attr = "fillColor" if animation.target_attribute == "fill" else "lineColor"
        attr_name_elem = anim_color.find('.//a:attrNameLst/a:attrName', {'a': A_URI})
        if attr_name_elem is not None:
            attr_name_elem.text = ppt_attr

        # Add easing and repeat attributes
        self._add_easing_attributes(anim_color, animation)
        self._add_repeat_attribute(anim_color, animation)

        return anim_color

    def generate_motion_animation(self, animation: AnimationDefinition, anim_id: int,
                                duration_ms: int, delay_ms: int) -> Element:
        """Generate motion path animation using template-based generation."""
        # Load animation motion template
        anim_motion = self._template_loader.load_template("animation_motion.xml")

        # Update common behavior attributes
        self._update_common_behavior(anim_motion, anim_id, duration_ms, delay_ms)
        self._update_target_element(anim_motion, animation.element_id)

        # Use the actual path from the animation values
        path_data = animation.values[0] if animation.values else "M 0,0 L 100,100"

        # Update motion path
        path_elem = anim_motion.find('.//a:path', {'a': A_URI})
        if path_elem is not None:
            path_elem.set('path', path_data)

        # Add easing and repeat attributes
        self._add_easing_attributes(anim_motion, animation)
        self._add_repeat_attribute(anim_motion, animation)

        return anim_motion

    def generate_set_animation(self, animation: AnimationDefinition, anim_id: int, delay_ms: int) -> Element:
        """Generate set animation (instant property change) using template-based generation."""
        # Load animation set template
        anim_set = self._template_loader.load_template("animation_set.xml")

        # Update common behavior attributes (duration is always 1 for set)
        self._update_common_behavior(anim_set, anim_id, 1, delay_ms)
        self._update_target_element(anim_set, animation.element_id)

        # Update attribute name
        attr_name_elem = anim_set.find('.//a:attrNameLst/a:attrName', {'a': A_URI})
        if attr_name_elem is not None:
            attr_name_elem.text = animation.target_attribute

        # Update value
        value = animation.values[0] if animation.values else ""
        str_val_elem = anim_set.find('.//a:to/a:strVal', {'a': A_URI})
        if str_val_elem is not None:
            str_val_elem.set('val', value)

        return anim_set

    def generate_generic_animation(self, animation: AnimationDefinition, anim_id: int,
                                 duration_ms: int, delay_ms: int) -> Element:
        """Generate generic property animation using template-based generation."""
        # Load animation generic template
        anim_generic = self._template_loader.load_template("animation_generic.xml")

        # Update common behavior attributes
        self._update_common_behavior(anim_generic, anim_id, duration_ms, delay_ms)
        self._update_target_element(anim_generic, animation.element_id)

        # Update attribute name
        attr_name_elem = anim_generic.find('.//a:attrNameLst/a:attrName', {'a': A_URI})
        if attr_name_elem is not None:
            attr_name_elem.text = animation.target_attribute

        # Update from/to values
        from_value = animation.values[0] if animation.values else ""
        to_value = animation.values[-1] if len(animation.values) > 1 else from_value

        # Update time/value list
        tav_list = anim_generic.findall('.//a:tavLst/a:tav', {'a': A_URI})
        if len(tav_list) >= 2:
            # Update from value (tm="0")
            from_str_val = tav_list[0].find('.//a:strVal', {'a': A_URI})
            if from_str_val is not None:
                from_str_val.set('val', from_value)

            # Update to value (tm="100000")
            to_str_val = tav_list[1].find('.//a:strVal', {'a': A_URI})
            if to_str_val is not None:
                to_str_val.set('val', to_value)

        # Add easing and repeat attributes
        self._add_easing_attributes(anim_generic, animation)
        self._add_repeat_attribute(anim_generic, animation)

        return anim_generic

    def generate_timing_root(self, sequence_id: int, animations: List[Element]) -> Element:
        """Generate complete timing root with animation sequence using template-based generation."""
        # Load timing root template
        timing_root = self._template_loader.load_template("animation_timing_root.xml")

        # Cache XPath expressions for performance
        if not hasattr(self, '_timing_xpaths'):
            self._timing_xpaths = {
                'seq_ctn': './/a:seq/a:cTn',
                'par_ctn': './/a:seq/a:cTn/a:childTnLst/a:par/a:cTn',
                'child_list': './/a:par/a:cTn[@fill="hold"]/a:childTnLst'
            }

        # Update sequence IDs in the nested structure
        seq_ctn = timing_root.find(self._timing_xpaths['seq_ctn'], {'a': A_URI})
        if seq_ctn is not None:
            seq_ctn.set('id', str(sequence_id))

        par_ctn = timing_root.find(self._timing_xpaths['par_ctn'], {'a': A_URI})
        if par_ctn is not None:
            par_ctn.set('id', str(sequence_id + 1))

        # Find the child list where animations should be inserted
        child_list = timing_root.find(self._timing_xpaths['child_list'], {'a': A_URI})
        if child_list is not None:
            # Clear the placeholder comment
            child_list.clear()
            # Add all animation elements in batch for performance
            if animations:
                child_list.extend(animations)

        return timing_root

    def generate_animation_sequence(self, sequence_id: int, animations: List[Element]) -> Element:
        """Generate animation sequence container using template-based generation."""
        # Load sequence template
        sequence = self._template_loader.load_template("animation_sequence.xml")

        # Cache XPath expressions for performance
        if not hasattr(self, '_sequence_xpaths'):
            self._sequence_xpaths = {
                'ctn': './/a:cTn',
                'child_list': './/a:childTnLst'
            }

        # Update sequence ID
        ctn = sequence.find(self._sequence_xpaths['ctn'], {'a': A_URI})
        if ctn is not None:
            ctn.set('id', str(sequence_id))

        # Find the child list where animations should be inserted
        child_list = sequence.find(self._sequence_xpaths['child_list'], {'a': A_URI})
        if child_list is not None:
            # Clear the placeholder comment
            child_list.clear()
            # Add all animation elements in batch for performance
            if animations:
                child_list.extend(animations)

        return sequence

    def generate_nested_timing_structure(self, sequence_id: int, animation_groups: List[List[Element]]) -> Element:
        """Generate nested timing structure with multiple animation groups."""
        # Load timing root template
        timing_root = self._template_loader.load_template("animation_timing_root.xml")

        # Update sequence IDs
        seq_ctn = timing_root.find('.//a:seq/a:cTn', {'a': A_URI})
        if seq_ctn is not None:
            seq_ctn.set('id', str(sequence_id))

        # Find the main child list
        main_child_list = timing_root.find('.//a:seq/a:cTn/a:childTnLst', {'a': A_URI})
        if main_child_list is not None:
            main_child_list.clear()

            # Create a sequence for each animation group
            for i, animation_group in enumerate(animation_groups):
                group_sequence = self.generate_animation_sequence(sequence_id + i + 1, animation_group)
                main_child_list.append(group_sequence)

        return timing_root

    def validate_timing_structure(self, timing_element: Element) -> bool:
        """Validate timing structure for proper nesting and IDs."""
        try:
            # Check that timing root has proper structure
            timing_list = timing_element.find('.//a:tnLst', {'a': A_URI})
            if timing_list is None:
                return False

            # Check for root par element
            root_par = timing_element.find('.//a:tnLst/a:par', {'a': A_URI})
            if root_par is None:
                return False

            # Check for tmRoot node
            root_ctn = root_par.find('./a:cTn[@nodeType="tmRoot"]', {'a': A_URI})
            if root_ctn is None:
                return False

            # Check for mainSeq node
            main_seq = timing_element.find('.//a:cTn[@nodeType="mainSeq"]', {'a': A_URI})
            if main_seq is None:
                return False

            return True
        except Exception as e:
            self.logger.error(f"Timing structure validation failed: {e}")
            return False

    def _update_common_behavior(self, animation_elem: Element, anim_id: int,
                              duration_ms: int, delay_ms: int) -> None:
        """Update common behavior attributes (id, duration, delay) in animation element."""
        ctn_elem = animation_elem.find('.//a:cBhvr/a:cTn', {'a': A_URI})
        if ctn_elem is not None:
            ctn_elem.set('id', str(anim_id))
            ctn_elem.set('dur', str(duration_ms))
            ctn_elem.set('delay', str(delay_ms))

    def _update_target_element(self, animation_elem: Element, element_id: str) -> None:
        """Update target element ID in animation element."""
        sp_tgt_elem = animation_elem.find('.//a:tgtEl/a:spTgt', {'a': A_URI})
        if sp_tgt_elem is not None:
            sp_tgt_elem.set('spid', str(element_id))

    def _add_easing_attributes(self, animation_elem: Element, animation: AnimationDefinition) -> None:
        """Add easing attributes to animation element based on animation definition."""
        # This would be implemented based on the animation's easing properties
        # For now, we'll leave the default easing from the template
        pass

    def _add_repeat_attribute(self, animation_elem: Element, animation: AnimationDefinition) -> None:
        """Add repeat attribute to animation element based on animation definition."""
        # This would be implemented based on the animation's repeat properties
        # For now, we'll leave the default repeat from the template
        pass

    def _parse_scale_value(self, value: str) -> float:
        """Parse scale value from animation definition."""
        try:
            return float(value)
        except (ValueError, TypeError):
            return 1.0

    def _parse_rotation_value(self, value: str) -> float:
        """Parse rotation value from animation definition."""
        try:
            # Remove 'deg' suffix if present and convert to float
            if isinstance(value, str) and value.endswith('deg'):
                return float(value[:-3])
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def _parse_color_value(self, value: str) -> str:
        """Parse color value from animation definition."""
        if isinstance(value, str):
            # Remove # prefix if present
            if value.startswith('#'):
                value = value[1:]
            # Ensure 6 character hex color
            if len(value) == 3:
                value = ''.join([c*2 for c in value])
            if len(value) == 6:
                return value.upper()
        return "000000"

    def element_to_string(self, element: Element, pretty_print: bool = False) -> str:
        """Convert animation element to XML string."""
        return ET.tostring(element, encoding='unicode', pretty_print=pretty_print)

    def validate_element(self, element: Element) -> bool:
        """Validate animation element for well-formedness."""
        try:
            # Check if element can be serialized
            ET.tostring(element)
            return True
        except ET.XMLSyntaxError as e:
            self.logger.error(f"Animation XML validation failed: {e}")
            return False


# Singleton instance for global access
enhanced_animation_builder = EnhancedAnimationBuilder()

def get_animation_builder() -> EnhancedAnimationBuilder:
    """Get the default enhanced animation builder instance."""
    return enhanced_animation_builder


# Factory functions for easier usage
def create_opacity_animation(animation: AnimationDefinition, anim_id: int,
                           duration_ms: int, delay_ms: int) -> Element:
    """Factory function for opacity animation creation."""
    return enhanced_animation_builder.generate_opacity_animation(animation, anim_id, duration_ms, delay_ms)


def create_scale_animation(animation: AnimationDefinition, anim_id: int,
                         duration_ms: int, delay_ms: int) -> Element:
    """Factory function for scale animation creation."""
    return enhanced_animation_builder.generate_scale_animation(animation, anim_id, duration_ms, delay_ms)


def create_rotation_animation(animation: AnimationDefinition, anim_id: int,
                            duration_ms: int, delay_ms: int) -> Element:
    """Factory function for rotation animation creation."""
    return enhanced_animation_builder.generate_rotation_animation(animation, anim_id, duration_ms, delay_ms)


def create_color_animation(animation: AnimationDefinition, anim_id: int,
                         duration_ms: int, delay_ms: int) -> Element:
    """Factory function for color animation creation."""
    return enhanced_animation_builder.generate_color_animation(animation, anim_id, duration_ms, delay_ms)


def create_motion_animation(animation: AnimationDefinition, anim_id: int,
                          duration_ms: int, delay_ms: int) -> Element:
    """Factory function for motion animation creation."""
    return enhanced_animation_builder.generate_motion_animation(animation, anim_id, duration_ms, delay_ms)


def create_set_animation(animation: AnimationDefinition, anim_id: int, delay_ms: int) -> Element:
    """Factory function for set animation creation."""
    return enhanced_animation_builder.generate_set_animation(animation, anim_id, delay_ms)


def create_generic_animation(animation: AnimationDefinition, anim_id: int,
                           duration_ms: int, delay_ms: int) -> Element:
    """Factory function for generic animation creation."""
    return enhanced_animation_builder.generate_generic_animation(animation, anim_id, duration_ms, delay_ms)


def create_timing_root(sequence_id: int, animations: List[Element]) -> Element:
    """Factory function for timing root creation."""
    return enhanced_animation_builder.generate_timing_root(sequence_id, animations)


def create_animation_sequence(sequence_id: int, animations: List[Element]) -> Element:
    """Factory function for animation sequence creation."""
    return enhanced_animation_builder.generate_animation_sequence(sequence_id, animations)


def create_nested_timing_structure(sequence_id: int, animation_groups: List[List[Element]]) -> Element:
    """Factory function for nested timing structure creation."""
    return enhanced_animation_builder.generate_nested_timing_structure(sequence_id, animation_groups)