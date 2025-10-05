#!/usr/bin/env python3
"""
SMIL Animation Parser for SVG2PPTX

This module provides parsing functionality for SMIL animation elements in SVG,
converting them to structured AnimationDefinition objects. Following ADR-006
animation system architecture.

Key Features:
- SMIL element parsing (animate, animateTransform, animateColor, etc.)
- Attribute validation and normalization
- Timing calculation and keyframe extraction
- Error handling and validation reporting
"""

import re
from typing import List, Optional

from lxml import etree

from .core import (
    AnimationDefinition,
    AnimationSummary,
    AnimationTiming,
    AnimationType,
    CalcMode,
    FillMode,
    TransformType,
)


class SMILParsingError(Exception):
    """Exception raised during SMIL parsing."""
    pass


class SMILParser:
    """Parser for SMIL animation elements in SVG."""

    def __init__(self):
        """Initialize the SMIL parser."""
        self.animation_summary = AnimationSummary()
        self._namespace_map = {
            'svg': 'http://www.w3.org/2000/svg',
            'smil': 'http://www.w3.org/2001/SMIL20/',
            'xlink': 'http://www.w3.org/1999/xlink',
        }
        self.svg_namespace = self._namespace_map['svg']

    def parse_svg_animations(self, svg_element: etree.Element) -> list[AnimationDefinition]:
        """
        Parse all SMIL animations from an SVG element.

        Args:
            svg_element: Root SVG element containing animations

        Returns:
            List of parsed animation definitions
        """
        animations = []
        animation_elements = self._find_animation_elements(svg_element)

        for anim_elem in animation_elements:
            try:
                animation_def = self._parse_animation_element(anim_elem)
                if animation_def:
                    animations.append(animation_def)
                    self._update_summary(animation_def)
            except SMILParsingError as e:
                self.animation_summary.add_warning(f"Failed to parse animation: {e}")
                continue
            except Exception as e:
                continue

        # Calculate final complexity
        self.animation_summary.total_animations = len(animations)
        self.animation_summary.element_count = len(set(anim.element_id for anim in animations))
        self.animation_summary.calculate_complexity()

        return animations

    def _find_animation_elements(self, svg_element: etree.Element) -> list[etree.Element]:
        """Find all animation elements in the SVG."""
        animation_tags = [
            'animate', 'animateTransform', 'animateColor', 'animateMotion', 'set',
        ]

        elements = []
        for tag in animation_tags:
            # Search with and without namespace
            no_ns = svg_element.xpath(f'.//{tag}')
            with_ns = svg_element.xpath(f'.//svg:{tag}', namespaces=self._namespace_map)
            elements.extend(no_ns)
            elements.extend(with_ns)

        return elements

    def _parse_animation_element(self, element: etree.Element) -> AnimationDefinition | None:
        """
        Parse a single animation element.

        Args:
            element: Animation element to parse

        Returns:
            Parsed AnimationDefinition or None if invalid
        """
        # Determine animation type
        tag_name = etree.QName(element).localname
        animation_type = self._get_animation_type(tag_name)

        if not animation_type:
            raise SMILParsingError(f"Unknown animation type: {tag_name}")

        # Get target element ID
        element_id = self._get_target_element_id(element)
        if not element_id:
            raise SMILParsingError("Animation missing target element")

        # Parse target attribute
        # animateMotion doesn't have attributeName as it animates position
        if animation_type == AnimationType.ANIMATE_MOTION:
            target_attribute = 'position'  # Virtual attribute for motion
        else:
            target_attribute = element.get('attributeName', '')
            if not target_attribute:
                raise SMILParsingError("Animation missing attributeName")

        # Parse values
        values = self._parse_animation_values(element, animation_type)
        if not values:
            raise SMILParsingError("Animation missing values")

        # Parse timing
        timing = self._parse_timing(element)

        # Parse optional attributes
        key_times = self._parse_key_times(element)
        key_splines = self._parse_key_splines(element)
        calc_mode = self._parse_calc_mode(element)
        transform_type = self._parse_transform_type(element, animation_type)

        # Additional attributes
        additive = element.get('additive', 'replace')
        accumulate = element.get('accumulate', 'none')

        return AnimationDefinition(
            element_id=element_id,
            animation_type=animation_type,
            target_attribute=target_attribute,
            values=values,
            timing=timing,
            key_times=key_times,
            key_splines=key_splines,
            calc_mode=calc_mode,
            transform_type=transform_type,
            additive=additive,
            accumulate=accumulate,
        )

    def _get_animation_type(self, tag_name: str) -> AnimationType | None:
        """Map element tag to AnimationType."""
        type_map = {
            'animate': AnimationType.ANIMATE,
            'animateTransform': AnimationType.ANIMATE_TRANSFORM,
            'animateColor': AnimationType.ANIMATE_COLOR,
            'animateMotion': AnimationType.ANIMATE_MOTION,
            'set': AnimationType.SET,
        }
        return type_map.get(tag_name)

    def _get_target_element_id(self, element: etree.Element) -> str | None:
        """Extract target element ID from animation element."""
        # Check for href attribute (most common)
        href = element.get('href') or element.get('{http://www.w3.org/1999/xlink}href')
        if href and href.startswith('#'):
            return href[1:]

        # Check if animation is child of target element
        parent = element.getparent()
        if parent is not None:
            parent_id = parent.get('id')
            if parent_id:
                return parent_id

        # Check for explicit target
        target = element.get('target')
        if target and target.startswith('#'):
            return target[1:]

        return None

    def _parse_animation_values(self, element: etree.Element, animation_type: AnimationType) -> list[str]:
        """Parse animation values from various SMIL attributes."""
        # For animateMotion, get the path attribute
        if animation_type == AnimationType.ANIMATE_MOTION:
            path = element.get('path')
            if path:
                return [path.strip()]
            # Could also support mpath reference
            mpath = element.find('.//mpath')
            if mpath is not None:
                href = mpath.get('href', mpath.get('{http://www.w3.org/1999/xlink}href'))
                if href:
                    return [href]
            return ['M 0,0']  # Default path if none specified

        # Try 'values' attribute first (semicolon-separated)
        values_attr = element.get('values')
        if values_attr:
            return [v.strip() for v in values_attr.split(';') if v.strip()]

        # Try 'from' and 'to' attributes
        from_value = element.get('from')
        to_value = element.get('to')

        if from_value is not None and to_value is not None:
            return [from_value.strip(), to_value.strip()]

        # Try 'to' attribute only (from current value)
        if to_value is not None:
            return [to_value.strip()]

        # For 'set' animations, try 'to' attribute
        if animation_type == AnimationType.SET:
            set_value = element.get('to')
            if set_value is not None:
                return [set_value.strip()]

        return []

    def _parse_timing(self, element: etree.Element) -> AnimationTiming:
        """Parse timing attributes from animation element."""
        # Parse begin time
        begin = self._parse_time_value(element.get('begin', '0s'))

        # Parse duration
        dur = element.get('dur', '1s')
        if dur == 'indefinite':
            duration = float('inf')
        else:
            duration = self._parse_time_value(dur)

        # Parse repeat count
        repeat_count_attr = element.get('repeatCount', '1')
        if repeat_count_attr == 'indefinite':
            repeat_count = 'indefinite'
        else:
            try:
                repeat_count = int(float(repeat_count_attr))
            except (ValueError, TypeError):
                repeat_count = 1

        # Parse fill mode
        fill_attr = element.get('fill', 'remove')
        fill_mode = FillMode.FREEZE if fill_attr == 'freeze' else FillMode.REMOVE

        return AnimationTiming(
            begin=begin,
            duration=duration,
            repeat_count=repeat_count,
            fill_mode=fill_mode,
        )

    def _parse_time_value(self, time_str: str) -> float:
        """Parse a time value string (e.g., '2s', '1000ms') to seconds."""
        if not time_str:
            return 0.0

        time_str = time_str.strip().lower()

        # Handle numeric-only values (assume seconds)
        try:
            return float(time_str)
        except ValueError:
            pass

        # Parse with units
        if time_str.endswith('ms'):
            return float(time_str[:-2]) / 1000.0
        elif time_str.endswith('s'):
            return float(time_str[:-1])
        elif time_str.endswith('min'):
            return float(time_str[:-3]) * 60.0
        elif time_str.endswith('h'):
            return float(time_str[:-1]) * 3600.0

        # Default to 0 for unparseable values
        return 0.0

    def _parse_key_times(self, element: etree.Element) -> list[float] | None:
        """Parse keyTimes attribute."""
        key_times_attr = element.get('keyTimes')
        if not key_times_attr:
            return None

        try:
            key_times = [float(t.strip()) for t in key_times_attr.split(';') if t.strip()]
            # Validate range [0, 1]
            if all(0.0 <= t <= 1.0 for t in key_times):
                return key_times
            else:
                self.animation_summary.add_warning("keyTimes values outside [0,1] range")
                return None
        except (ValueError, TypeError):
            self.animation_summary.add_warning("Invalid keyTimes format")
            return None

    def _parse_key_splines(self, element: etree.Element) -> list[list[float]] | None:
        """Parse keySplines attribute."""
        key_splines_attr = element.get('keySplines')
        if not key_splines_attr:
            return None

        try:
            # Split by semicolon for multiple splines
            spline_groups = [s.strip() for s in key_splines_attr.split(';') if s.strip()]
            splines = []

            for group in spline_groups:
                # Parse 4 control point values
                values = [float(v.strip()) for v in re.split(r'[,\s]+', group) if v.strip()]
                if len(values) == 4 and all(0.0 <= v <= 1.0 for v in values):
                    splines.append(values)
                else:
                    self.animation_summary.add_warning("Invalid keySplines format")
                    return None

            return splines if splines else None

        except (ValueError, TypeError):
            self.animation_summary.add_warning("Invalid keySplines values")
            return None

    def _parse_calc_mode(self, element: etree.Element) -> CalcMode:
        """Parse calcMode attribute."""
        calc_mode_attr = element.get('calcMode', 'linear').lower()
        calc_mode_map = {
            'linear': CalcMode.LINEAR,
            'discrete': CalcMode.DISCRETE,
            'paced': CalcMode.PACED,
            'spline': CalcMode.SPLINE,
        }
        return calc_mode_map.get(calc_mode_attr, CalcMode.LINEAR)

    def _parse_transform_type(self, element: etree.Element, animation_type: AnimationType) -> TransformType | None:
        """Parse type attribute for animateTransform elements."""
        if animation_type != AnimationType.ANIMATE_TRANSFORM:
            return None

        type_attr = element.get('type', '').lower()
        type_map = {
            'translate': TransformType.TRANSLATE,
            'scale': TransformType.SCALE,
            'rotate': TransformType.ROTATE,
            'skewx': TransformType.SKEWX,
            'skewy': TransformType.SKEWY,
            'matrix': TransformType.MATRIX,
        }
        return type_map.get(type_attr)

    def _update_summary(self, animation: AnimationDefinition):
        """Update animation summary with characteristics from parsed animation."""
        # Update duration
        if animation.timing.duration != float('inf'):
            end_time = animation.timing.get_end_time()
            if end_time != float('inf'):
                self.animation_summary.duration = max(self.animation_summary.duration, end_time)

        # Update feature flags
        if animation.is_transform_animation():
            self.animation_summary.has_transforms = True

        if animation.is_motion_animation():
            self.animation_summary.has_motion_paths = True

        if animation.is_color_animation():
            self.animation_summary.has_color_animations = True

        if animation.key_splines:
            self.animation_summary.has_easing = True

        # Check for sequences (multiple animations with delays)
        if animation.timing.begin > 0:
            self.animation_summary.has_sequences = True

    def get_animation_summary(self) -> AnimationSummary:
        """Get the current animation summary."""
        return self.animation_summary

    def reset_summary(self):
        """Reset animation summary for new parsing session."""
        self.animation_summary = AnimationSummary()

    def validate_animation_structure(self, animations: list[AnimationDefinition]) -> list[str]:
        """
        Validate the overall structure of parsed animations.

        Args:
            animations: List of parsed animations

        Returns:
            List of validation warnings
        """
        warnings = []

        if not animations:
            return ["No animations found"]

        # Check for common issues
        element_ids = [anim.element_id for anim in animations]
        unique_elements = set(element_ids)

        # Warn about complex animation scenarios
        if len(animations) > len(unique_elements) * 3:
            warnings.append("Very high animation density - consider simplification")

        # Check for timing conflicts
        for element_id in unique_elements:
            element_animations = [a for a in animations if a.element_id == element_id]
            if len(element_animations) > 1:
                # Check for overlapping animations on same attribute
                attr_groups = {}
                for anim in element_animations:
                    attr = anim.target_attribute
                    if attr not in attr_groups:
                        attr_groups[attr] = []
                    attr_groups[attr].append(anim)

                for attr, attr_animations in attr_groups.items():
                    if len(attr_animations) > 1:
                        # Check for timing overlaps
                        for i, anim1 in enumerate(attr_animations):
                            for anim2 in attr_animations[i+1:]:
                                if self._animations_overlap(anim1, anim2):
                                    warnings.append(
                                        f"Overlapping animations on {element_id}.{attr} "
                                        f"may cause conflicts",
                                    )

        return warnings

    def _animations_overlap(self, anim1: AnimationDefinition, anim2: AnimationDefinition) -> bool:
        """Check if two animations have overlapping time ranges."""
        start1, end1 = anim1.timing.begin, anim1.timing.get_end_time()
        start2, end2 = anim2.timing.begin, anim2.timing.get_end_time()

        # Handle infinite animations
        if end1 == float('inf') or end2 == float('inf'):
            return start1 <= start2 or start2 <= start1

        return not (end1 <= start2 or end2 <= start1)