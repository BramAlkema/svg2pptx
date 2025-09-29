# Animation System Test Fixes Specification

## Overview
The animation system has 15+ failing tests due to missing methods and API mismatches between the test expectations and the current AnimationConverter implementation. This specification outlines the required fixes to align the animation system with its test suite.

## Current Issues Analysis

### 1. Missing AnimationConverter Methods
**Tests Expect But Don't Exist:**
- `process_combined_transform_animation()` - Used in `test_combined_transform_animations.py`
- `convert_slide_animations()` - May exist but with wrong signature
- `get_animation_timeline()` - Expected by timeline tests
- `process_keyframe_animations()` - Expected by keyframe tests

### 2. AnimationDefinition Missing Methods
**Tests Expect But Don't Exist:**
- `get_value_at_time()` - Critical for animation interpolation tests
- `_apply_easing()` - Expected by easing tests in `test_advanced_timing_easing.py`

### 3. Enum Value Mismatches
**Fixed but Need Validation:**
- Tests expect `calc_mode.value == "spline"` but get enum objects
- Need to verify all enum comparisons use `.value` pattern

## Implementation Plan

### Phase 1: Core AnimationConverter Method Implementation

#### 1.1 Add Missing AnimationConverter Methods
```python
# In src/converters/animation_converter.py

def process_combined_transform_animation(self, element: ET.Element, context: ConversionContext) -> str:
    """Process combined transform animations (translate + rotate + scale)."""
    try:
        # Parse the animateTransform element
        animation_def = self.parser._parse_animation_element(element)
        if not animation_def:
            return ""

        # Handle combined transforms
        if animation_def.transform_type:
            timeline = self.timeline_generator.generate_timeline([animation_def])
            if timeline:
                return self.powerpoint_generator.generate_animation_sequence(timeline)

        return ""
    except Exception as e:
        if hasattr(self.services, 'logger'):
            self.services.logger.warning(f"Failed to process combined transform: {e}")
        return ""

def get_animation_timeline(self, svg_root: ET.Element) -> Optional[Timeline]:
    """Get complete animation timeline for SVG."""
    try:
        # Extract all animation elements
        animations = []
        for anim_tag in ['animate', 'animateTransform', 'animateColor', 'animateMotion']:
            for elem in svg_root.xpath(f".//{{{self.svg_ns}}}{anim_tag}"):
                anim_def = self.parser._parse_animation_element(elem)
                if anim_def:
                    animations.append(anim_def)

        return self.timeline_generator.generate_timeline(animations)
    except Exception:
        return None

def process_keyframe_animations(self, elements: List[ET.Element], context: ConversionContext) -> str:
    """Process multiple keyframe-based animations."""
    try:
        animations = []
        for element in elements:
            anim_def = self.parser._parse_animation_element(element)
            if anim_def:
                animations.append(anim_def)

        if animations:
            timeline = self.timeline_generator.generate_timeline(animations)
            return self.powerpoint_generator.generate_animation_sequence(timeline)

        return ""
    except Exception as e:
        if hasattr(self.services, 'logger'):
            self.services.logger.warning(f"Failed to process keyframes: {e}")
        return ""
```

#### 1.2 Update AnimationDefinition Class
```python
# In src/animations/core.py

@dataclass
class AnimationDefinition:
    # ... existing fields ...

    def get_value_at_time(self, time: float) -> Any:
        """Get interpolated value at specific time."""
        # Handle time before animation starts
        if time < self.timing.begin:
            return self.values[0] if self.values else None

        # Handle time after animation ends
        duration = self.timing.duration
        if time >= self.timing.begin + duration:
            return self.values[-1] if self.values else None

        # Calculate relative time within animation
        relative_time = (time - self.timing.begin) / duration

        # Apply easing if calc_mode is spline
        if self.calc_mode == CalcMode.SPLINE and self.key_splines:
            relative_time = self._apply_easing(relative_time)

        # Interpolate between values
        return self._interpolate_value(relative_time)

    def _apply_easing(self, t: float) -> float:
        """Apply easing function based on calc_mode and key_splines."""
        if self.calc_mode == CalcMode.LINEAR:
            return t
        elif self.calc_mode == CalcMode.DISCRETE:
            # Discrete steps
            if not self.key_times:
                return t
            for i, key_time in enumerate(self.key_times[1:], 1):
                if t <= key_time:
                    return self.key_times[i-1]
            return 1.0
        elif self.calc_mode == CalcMode.SPLINE and self.key_splines:
            # Bezier easing using keySplines
            return self._apply_bezier_easing(t)
        else:
            return t

    def _apply_bezier_easing(self, t: float) -> float:
        """Apply cubic bezier easing from keySplines."""
        if not self.key_splines or not self.key_times:
            return t

        # Find the segment for this time
        for i in range(len(self.key_times) - 1):
            if t <= self.key_times[i + 1]:
                segment_start = self.key_times[i]
                segment_end = self.key_times[i + 1]
                segment_t = (t - segment_start) / (segment_end - segment_start)

                # Apply bezier curve from corresponding keySpline
                if i < len(self.key_splines):
                    spline = self.key_splines[i]
                    return self._cubic_bezier(segment_t, spline[0], spline[1], spline[2], spline[3])

        return t

    def _cubic_bezier(self, t: float, x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate cubic bezier curve value."""
        # Simplified bezier calculation for easing
        # This is a basic implementation - could be enhanced with more precision
        return 3 * (1 - t)**2 * t * y1 + 3 * (1 - t) * t**2 * y2 + t**3

    def _interpolate_value(self, t: float) -> Any:
        """Interpolate between animation values."""
        if not self.values:
            return None

        if len(self.values) == 1:
            return self.values[0]

        # Find values to interpolate between
        if self.key_times:
            # Use key_times for precise interpolation
            for i in range(len(self.key_times) - 1):
                if t <= self.key_times[i + 1]:
                    start_val = self.values[i] if i < len(self.values) else self.values[-1]
                    end_val = self.values[i + 1] if i + 1 < len(self.values) else self.values[-1]

                    segment_t = (t - self.key_times[i]) / (self.key_times[i + 1] - self.key_times[i])
                    return self._lerp_values(start_val, end_val, segment_t)
        else:
            # Linear interpolation across all values
            scaled_t = t * (len(self.values) - 1)
            index = int(scaled_t)
            fraction = scaled_t - index

            if index >= len(self.values) - 1:
                return self.values[-1]

            return self._lerp_values(self.values[index], self.values[index + 1], fraction)

        return self.values[-1]

    def _lerp_values(self, start: Any, end: Any, t: float) -> Any:
        """Linear interpolation between two values."""
        # Handle numeric values
        try:
            start_num = float(start)
            end_num = float(end)
            return start_num + (end_num - start_num) * t
        except (ValueError, TypeError):
            # Handle non-numeric values (colors, transforms, etc.)
            # For now, return discrete values
            return start if t < 0.5 else end
```

### Phase 2: Test Pattern Updates

#### 2.1 Update Enum Comparison Tests
```python
# Pattern to replace in all animation tests:
# OLD: assert animation_def.calc_mode == "spline"
# NEW: assert animation_def.calc_mode.value == "spline"
```

#### 2.2 Fix Test Data and Mocking
```python
# In test files, ensure proper AnimationDefinition construction:

def create_test_animation_def():
    return AnimationDefinition(
        element_id='test',
        animation_type=AnimationType.ANIMATE,
        target_attribute='opacity',
        values=['0', '1'],
        timing=AnimationTiming(begin=0.0, duration=2.0),
        calc_mode=CalcMode.SPLINE,  # Use enum, not string
        key_splines=[[0.25, 0.1, 0.25, 1.0]],
        key_times=[0.0, 1.0]
    )
```

### Phase 3: Integration and Timeline Fixes

#### 3.1 Ensure Timeline Generation Works
```python
# Verify TimelineGenerator can handle AnimationDefinition objects correctly
# Update tests to use proper Timeline objects
```

#### 3.2 PowerPoint Generator Integration
```python
# Ensure PowerPointAnimationGenerator produces non-empty output
# Fix any template or XML generation issues
```

## Testing Strategy

### 3.1 Test Execution Plan
1. **Run animation tests in isolation**: `pytest tests/unit/converters/test_animations.py -v`
2. **Run timing/easing tests**: `pytest tests/unit/converters/test_advanced_timing_easing.py -v`
3. **Run combined transform tests**: `pytest tests/unit/converters/test_combined_transform_animations.py -v`

### 3.2 Validation Checklist
- [ ] All AnimationConverter methods exist and return expected types
- [ ] AnimationDefinition supports time-based value interpolation
- [ ] Enum comparisons use `.value` pattern consistently
- [ ] Timeline generation produces valid Timeline objects
- [ ] PowerPoint generation produces non-empty XML strings
- [ ] Integration tests pass for complete animation sequences

## Implementation Priority

1. **High Priority**: Missing methods that cause AttributeError failures
2. **Medium Priority**: Enum comparison fixes
3. **Low Priority**: Complex easing and interpolation refinements

## Success Criteria

- All 15+ animation tests pass
- No AttributeError exceptions from missing methods
- Proper enum value comparisons throughout
- Generated PowerPoint animation XML is valid and non-empty
- Animation system integrates properly with converter pipeline

## Dependencies

- `src/animations/core.py` - Core animation data structures
- `src/animations/parser.py` - SMIL animation parsing
- `src/animations/timeline.py` - Timeline generation
- `src/animations/powerpoint.py` - PowerPoint XML generation
- `src/converters/animation_converter.py` - Main converter class

## Notes

This specification focuses on making the tests pass by implementing the expected API. The animation system appears to be well-architected with proper separation of concerns. The main issue is that the implementation is incomplete relative to the comprehensive test suite expectations.