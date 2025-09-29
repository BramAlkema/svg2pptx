#!/usr/bin/env python3
"""
Advanced Animation Timing Converter for SVG2PPTX

This module handles complex SMIL timing features and converts them to
PowerPoint animation sequences with proper timing relationships.

Advanced Timing Features:
- Animation chains (begin="element.end")
- Negative begin times
- Complex timing expressions
- Duration constraints (min/max)
- Synchronization and coordination
"""

import re
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
from enum import Enum


class TimingEventType(Enum):
    """Types of timing events in SMIL."""
    ABSOLUTE_TIME = "absolute"      # begin="2s"
    ELEMENT_BEGIN = "element_begin" # begin="anim1.begin"
    ELEMENT_END = "element_end"     # begin="anim1.end"
    INDEFINITE = "indefinite"       # begin="indefinite"
    CLICK_EVENT = "click"           # begin="click"


@dataclass
class TimingReference:
    """Reference to another animation or timing event."""
    element_id: Optional[str]
    event_type: TimingEventType
    offset: float = 0.0  # Additional offset in seconds

    @classmethod
    def parse(cls, timing_str: str) -> 'TimingReference':
        """
        Parse SMIL timing string into TimingReference.

        Examples:
        - "2s" → TimingReference(None, ABSOLUTE_TIME, 2.0)
        - "anim1.end" → TimingReference("anim1", ELEMENT_END, 0.0)
        - "anim1.end + 0.5s" → TimingReference("anim1", ELEMENT_END, 0.5)
        """
        if not timing_str or timing_str.strip() == "":
            return cls(None, TimingEventType.ABSOLUTE_TIME, 0.0)

        timing_str = timing_str.strip()

        # Handle negative times
        negative = timing_str.startswith('-')
        if negative:
            timing_str = timing_str[1:]

        # Check for element references (but not decimal numbers)
        if '.' in timing_str and not re.match(r'^\d+\.\d+', timing_str):
            # Pattern: elementId.event [+ offset]
            parts = timing_str.split('+') if '+' in timing_str else [timing_str]
            element_event = parts[0].strip()
            offset_str = parts[1].strip() if len(parts) > 1 else "0s"

            if '.' in element_event:
                element_id, event = element_event.split('.', 1)
                element_id = element_id.strip()
                event = event.strip()

                # Only treat as element reference if event looks like an event name
                if event in ["end", "begin", "repeat", "click"]:
                    if event == "end":
                        event_type = TimingEventType.ELEMENT_END
                    elif event == "begin":
                        event_type = TimingEventType.ELEMENT_BEGIN
                    else:
                        event_type = TimingEventType.ABSOLUTE_TIME

                    offset = cls._parse_time_value(offset_str)
                    if negative:
                        offset = -offset

                    return cls(element_id, event_type, offset)

        # Handle special values
        if timing_str == "indefinite":
            return cls(None, TimingEventType.INDEFINITE, 0.0)
        elif timing_str == "click":
            return cls(None, TimingEventType.CLICK_EVENT, 0.0)

        # Parse as absolute time
        time_value = cls._parse_time_value(timing_str)
        if negative:
            time_value = -time_value

        return cls(None, TimingEventType.ABSOLUTE_TIME, time_value)

    @staticmethod
    def _parse_time_value(time_str: str) -> float:
        """Parse time value string to seconds."""
        if not time_str:
            return 0.0

        time_str = time_str.strip()

        # Handle different time units
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


@dataclass
class AnimationTimeline:
    """Timeline calculation for animation sequences."""
    animation_id: str
    start_time: float
    end_time: float
    dependencies: List[str]  # IDs of animations this depends on


class AdvancedTimingConverter:
    """Converts SMIL timing to PowerPoint animation sequences."""

    def __init__(self):
        """Initialize the timing converter."""
        self.animation_registry: Dict[str, Dict[str, Any]] = {}
        self.timing_dependencies: Dict[str, List[str]] = {}

    def register_animation(self, animation_id: str, duration: float,
                          begin_reference: TimingReference, repeat_count: Union[int, str, None] = None):
        """
        Register an animation with the timing system.

        Args:
            animation_id: Unique identifier for the animation
            duration: Animation duration in seconds
            begin_reference: When the animation should start
            repeat_count: Number of repeats or "indefinite"
        """
        self.animation_registry[animation_id] = {
            'duration': duration,
            'begin_reference': begin_reference,
            'repeat_count': repeat_count,
            'resolved_start_time': None,
            'resolved_end_time': None
        }

        # Track dependencies
        if begin_reference.element_id:
            if begin_reference.element_id not in self.timing_dependencies:
                self.timing_dependencies[begin_reference.element_id] = []
            self.timing_dependencies[begin_reference.element_id].append(animation_id)

    def calculate_animation_timeline(self) -> List[AnimationTimeline]:
        """
        Calculate the complete animation timeline with resolved timing.

        Returns:
            List of AnimationTimeline objects with resolved start/end times
        """
        # Reset resolved times
        for anim_id in self.animation_registry:
            self.animation_registry[anim_id]['resolved_start_time'] = None
            self.animation_registry[anim_id]['resolved_end_time'] = None

        # Resolve timing in dependency order
        timeline = []
        resolved = set()

        while len(resolved) < len(self.animation_registry):
            progress_made = False

            for anim_id, anim_data in self.animation_registry.items():
                if anim_id in resolved:
                    continue

                # Try to resolve this animation's timing
                start_time = self._resolve_start_time(anim_id, anim_data, resolved)
                if start_time is not None:
                    end_time = self._calculate_end_time(start_time, anim_data)

                    anim_data['resolved_start_time'] = start_time
                    anim_data['resolved_end_time'] = end_time

                    # Create timeline entry
                    dependencies = self._get_animation_dependencies(anim_id)
                    timeline.append(AnimationTimeline(
                        animation_id=anim_id,
                        start_time=start_time,
                        end_time=end_time,
                        dependencies=dependencies
                    ))

                    resolved.add(anim_id)
                    progress_made = True

            if not progress_made:
                # Handle circular dependencies or unresolvable references
                for anim_id in self.animation_registry:
                    if anim_id not in resolved:
                        # Force resolution with default timing
                        anim_data = self.animation_registry[anim_id]
                        start_time = 0.0  # Default start
                        end_time = self._calculate_end_time(start_time, anim_data)

                        anim_data['resolved_start_time'] = start_time
                        anim_data['resolved_end_time'] = end_time

                        dependencies = self._get_animation_dependencies(anim_id)
                        timeline.append(AnimationTimeline(
                            animation_id=anim_id,
                            start_time=start_time,
                            end_time=end_time,
                            dependencies=dependencies
                        ))

                        resolved.add(anim_id)
                break

        # Sort timeline by start time
        timeline.sort(key=lambda x: x.start_time)
        return timeline

    def _resolve_start_time(self, anim_id: str, anim_data: Dict[str, Any],
                           resolved: set) -> Optional[float]:
        """Resolve the start time for an animation."""
        begin_ref = anim_data['begin_reference']

        if begin_ref.event_type == TimingEventType.ABSOLUTE_TIME:
            return begin_ref.offset

        elif begin_ref.event_type == TimingEventType.INDEFINITE:
            return None  # Will need manual trigger

        elif begin_ref.event_type == TimingEventType.CLICK_EVENT:
            return 0.0  # Start immediately on click

        elif begin_ref.element_id:
            # Check if referenced animation is resolved
            if begin_ref.element_id not in resolved:
                return None  # Can't resolve yet

            ref_anim = self.animation_registry.get(begin_ref.element_id)
            if not ref_anim:
                return 0.0  # Referenced animation doesn't exist

            if begin_ref.event_type == TimingEventType.ELEMENT_BEGIN:
                base_time = ref_anim['resolved_start_time']
            elif begin_ref.event_type == TimingEventType.ELEMENT_END:
                base_time = ref_anim['resolved_end_time']
            else:
                base_time = ref_anim['resolved_start_time']

            if base_time is None:
                return None

            return base_time + begin_ref.offset

        return 0.0  # Default

    def _calculate_end_time(self, start_time: float, anim_data: Dict[str, Any]) -> float:
        """Calculate end time based on start time and duration/repeat."""
        duration = anim_data['duration']
        repeat_count = anim_data['repeat_count']

        if isinstance(repeat_count, str) and repeat_count == "indefinite":
            return float('inf')  # Indefinite duration
        elif isinstance(repeat_count, int) and repeat_count > 1:
            return start_time + (duration * repeat_count)
        else:
            return start_time + duration

    def _get_animation_dependencies(self, anim_id: str) -> List[str]:
        """Get list of animations this animation depends on."""
        if anim_id not in self.animation_registry:
            return []

        anim_data = self.animation_registry[anim_id]
        begin_ref = anim_data['begin_reference']

        if begin_ref.element_id:
            return [begin_ref.element_id]

        return []

    def generate_powerpoint_timing_sequence(self, timeline: List[AnimationTimeline]) -> Dict[str, Any]:
        """
        Generate PowerPoint timing sequence from resolved timeline.

        Returns:
            Dictionary with PowerPoint timing configuration
        """
        sequence_config = {
            'animations': [],
            'total_duration': 0.0,
            'has_indefinite': False,
            'max_parallel': 1
        }

        current_parallel = 0
        max_parallel = 0

        for entry in timeline:
            # Calculate delay from sequence start
            delay_ms = int(entry.start_time * 1000)

            # Calculate duration
            if entry.end_time == float('inf'):
                duration_ms = -1  # Indefinite
                sequence_config['has_indefinite'] = True
            else:
                duration_ms = int((entry.end_time - entry.start_time) * 1000)

            animation_config = {
                'animation_id': entry.animation_id,
                'delay_ms': delay_ms,
                'duration_ms': duration_ms,
                'dependencies': entry.dependencies,
                'start_time': entry.start_time,
                'end_time': entry.end_time
            }

            sequence_config['animations'].append(animation_config)

            # Track parallel animations
            if entry.start_time == (timeline[max(0, len(sequence_config['animations']) - 2)].start_time
                                   if len(sequence_config['animations']) > 1 else -1):
                current_parallel += 1
            else:
                max_parallel = max(max_parallel, current_parallel)
                current_parallel = 1

        sequence_config['max_parallel'] = max(max_parallel, current_parallel)

        if timeline:
            max_end_time = max(t.end_time for t in timeline if t.end_time != float('inf'))
            sequence_config['total_duration'] = max_end_time

        return sequence_config

    def validate_timing_references(self) -> List[str]:
        """
        Validate all timing references and return list of issues.

        Returns:
            List of validation error messages
        """
        issues = []

        for anim_id, anim_data in self.animation_registry.items():
            begin_ref = anim_data['begin_reference']

            if begin_ref.element_id:
                if begin_ref.element_id not in self.animation_registry:
                    issues.append(f"Animation '{anim_id}' references unknown animation '{begin_ref.element_id}'")

        # Check for circular dependencies
        for anim_id in self.animation_registry:
            if self._has_circular_dependency(anim_id, set()):
                issues.append(f"Circular dependency detected involving animation '{anim_id}'")

        return issues

    def _has_circular_dependency(self, anim_id: str, visited: set) -> bool:
        """Check if animation has circular dependency."""
        if anim_id in visited:
            return True

        visited.add(anim_id)
        dependencies = self._get_animation_dependencies(anim_id)

        for dep_id in dependencies:
            if self._has_circular_dependency(dep_id, visited.copy()):
                return True

        return False

    def reset(self):
        """Reset the timing converter state."""
        self.animation_registry.clear()
        self.timing_dependencies.clear()


class PowerPointTimingGenerator:
    """Generates PowerPoint-specific timing XML from timing sequences."""

    def __init__(self):
        """Initialize the PowerPoint timing generator."""
        pass

    def generate_sequence_xml(self, sequence_config: Dict[str, Any]) -> str:
        """
        Generate PowerPoint animation sequence XML.

        Args:
            sequence_config: Configuration from AdvancedTimingConverter

        Returns:
            PowerPoint sequence XML string
        """
        animations = sequence_config['animations']

        if not animations:
            return ""

        # Generate main sequence container
        sequence_xml = ['<a:seq>']
        sequence_xml.append('  <a:cTn dur="indefinite">')
        sequence_xml.append('    <a:childTnLst>')

        # Add each animation with proper timing
        for anim_config in animations:
            anim_xml = self._generate_animation_timing_xml(anim_config)
            sequence_xml.append(f'      {anim_xml}')

        sequence_xml.append('    </a:childTnLst>')
        sequence_xml.append('  </a:cTn>')
        sequence_xml.append('</a:seq>')

        return '\n'.join(sequence_xml)

    def _generate_animation_timing_xml(self, anim_config: Dict[str, Any]) -> str:
        """Generate timing XML for individual animation."""
        delay = anim_config['delay_ms']
        duration = anim_config['duration_ms']

        duration_attr = f'dur="{duration}"' if duration > 0 else 'dur="indefinite"'
        delay_attr = f'delay="{delay}"' if delay > 0 else ''

        return f'<a:cTn {duration_attr} {delay_attr}/>'

    def generate_parallel_group_xml(self, parallel_animations: List[Dict[str, Any]]) -> str:
        """Generate XML for parallel animation group."""
        if len(parallel_animations) <= 1:
            return self._generate_animation_timing_xml(parallel_animations[0]) if parallel_animations else ""

        group_xml = ['<a:par>']
        group_xml.append('  <a:cTn>')
        group_xml.append('    <a:childTnLst>')

        for anim_config in parallel_animations:
            anim_xml = self._generate_animation_timing_xml(anim_config)
            group_xml.append(f'      {anim_xml}')

        group_xml.append('    </a:childTnLst>')
        group_xml.append('  </a:cTn>')
        group_xml.append('</a:par>')

        return '\n'.join(group_xml)