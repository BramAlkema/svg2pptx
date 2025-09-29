# ADR-007: DrawingML Coordinate System Standardization

## Status
Accepted

## Context
During Phase 5 bugfixing, we discovered a critical coordinate system mixing issue in DrawingML path generation that caused shapes to render at ~9.144× smaller scale than intended. This affected all path-based SVG elements including complex paths, polygons, and polylines.

### Problem Analysis
The issue stemmed from mixing two different DrawingML coordinate systems:

1. **Shape Bounding Box System**: Uses EMU (English Metric Units) for positioning shapes on slides
   - 1 inch = 914,400 EMU
   - Standard PowerPoint slide: 10" × 7.5" = 9,144,000 × 6,858,000 EMU
   - Used for `<a:off>` and `<a:ext>` elements

2. **Path Coordinate Space**: Internal coordinate system for path point definitions
   - Should use normalized 0-100000 scale
   - Path dimensions (`<a:path w="..." h="...">`) define this internal coordinate space
   - Path points (`<a:pt x="..." y="...">`) are expressed within this space

### Root Cause
The converters were incorrectly setting path dimensions to EMU values while using 0-100000 normalized coordinates for path points:

```xml
<!-- INCORRECT (caused ~9.144× scale-down) -->
<a:path w="914400" h="914400">  <!-- EMU dimensions -->
    <a:pt x="50000" y="0"/>     <!-- 0-100000 coordinates -->
</a:path>

<!-- CORRECT (proper coordinate system alignment) -->
<a:path w="100000" h="100000">  <!-- Normalized dimensions -->
    <a:pt x="50000" y="0"/>     <!-- 0-100000 coordinates -->
</a:path>
```

## Decision
We standardize on **Option A: Normalized Path Coordinate Space** for all DrawingML path generation:

- **Path Dimensions**: Always use `w="100000" h="100000"`
- **Path Points**: Continue using 0-100000 coordinate scale
- **Shape Positioning**: Maintain EMU system for bounding box (`<a:off>`, `<a:ext>`)

This creates a consistent coordinate system where:
1. Shape bounding box defines position/size on slide (EMU)
2. Path coordinate space is normalized (0-100000)
3. Path points are expressed within the normalized space

## Implementation

### Files Modified
1. **`src/svg2drawingml.py`** (Legacy converter - lines 566, 747, 820):
   ```diff
   - <a:path w="{emu_width}" h="{emu_height}">
   + <a:path w="100000" h="100000">
   ```

2. **`src/converters/paths.py`** (Modern converter - line 185):
   ```diff
   - <a:path w="{int(bounds['width'])}" h="{int(bounds['height'])}" fill="norm">
   + <a:path w="100000" h="100000" fill="norm">
   ```

### Architecture Impact
- **Backward Compatible**: Existing coordinate transformation logic unchanged
- **ViewportEngine Integration**: Bounding box calculations remain in EMU for proper slide positioning
- **Path Point Generation**: All relative coordinate calculations (0-100000) remain unchanged

## Consequences

### Positive
- **Correct Shape Scaling**: Shapes now render at intended sizes
- **Consistent Coordinate System**: Eliminates coordinate system mixing throughout pipeline
- **PowerPoint Compatibility**: Aligns with PowerPoint's expected DrawingML coordinate model
- **Architecture Cleanup**: Removes confusion between positioning and path coordinate systems

### Neutral
- **Template Changes**: Requires updating path generation templates across converters
- **Testing Requirements**: Need comprehensive testing with multiple path elements

### Negative
- **Legacy Code Impact**: Both legacy and modern converters needed updates
- **Debugging Complexity**: Mixed coordinate system was hard to diagnose initially

## Verification
Test case: SVG star path (40×40 SVG units) converts to 1" × 1" PowerPoint shape
- **Before**: Tiny star due to scale-down factor
- **After**: Correct 1-inch star properly positioned

## References
- PowerPoint DrawingML specification
- EMU coordinate system documentation (914,400 EMU = 1 inch)
- ViewportEngine coordinate transformation architecture