# E2E Path Conversion Debug Specification

**Date**: 2025-09-23
**Status**: ACTIVE DEBUGGING
**Issue**: Multiple SVG paths rendering incorrectly in PowerPoint - wrong positions, shapes, and missing elements

## Current Problem Analysis

### Visual Evidence
- **SVG Source**: 5 complex paths (heart, star, curved line, polygon, bezier curves) at specific coordinates
- **PPTX Result**: Only 2 elements visible (blue line + yellow star), wrong positions, incorrect shapes
- **LibreOffice Rendering**: Successfully loads PPTX but shows path geometry/positioning issues

### Critical Success: Core Conversion Working
✅ **PPTX file loads in LibreOffice** (not corrupted)
✅ **Vector shapes render** (not pixelated/diagnostic text)
✅ **Colors are preserved** correctly
✅ **Complex paths parse** (Cython element.tag issue fixed)

## E2E Conversion Pipeline Analysis

### Phase 1: SVG Input Processing
**File**: `test_multiple_paths.svg`
```svg
<!-- 5 distinct paths with different geometries -->
1. Heart: Complex bezier with fills + strokes (M200,220 C...)
2. Star: 10-point polygon (M100,50 L105,65...)
3. Curved line: Quadratic bezier (M50,100 Q150,50...)
4. Polygon: 8-sided shape (M300,200 L320,180...)
5. Bezier curves: Smooth curves (M60,200 C60,180...)
```

**Coordinate System**: `viewBox="0 0 400 300"` (400x300 units)

### Phase 2: SVG Parsing & Element Detection
**File**: `src/svg2drawingml.py` (lines 113-122)

**Fixed Issue**: Cython element.tag function error
```python
# BEFORE (broken):
if '}' in element.tag:

# AFTER (fixed):
tag_str = str(element.tag) if hasattr(element.tag, 'split') else element.tag
if '}' in tag_str:
```

**Current Status**: ✅ All 5 paths correctly parsed and detected

### Phase 3: Path Data Processing
**Component**: Path converter system
**Location**: `src/converters/path_generator.py`, `src/paths/`

**Expected Flow**:
1. Parse SVG path `d` attribute string
2. Convert to intermediate path commands
3. Transform coordinates to EMU units
4. Generate DrawingML `<a:custGeom>` XML

**Potential Issues**:
- Path command parsing (M, L, C, Q, T, S, Z)
- Coordinate transformation accuracy
- Bezier curve approximation
- Relative vs absolute coordinates

### Phase 4: Coordinate System Transformation
**Component**: Units & viewport handling
**Location**: `src/units/`, `src/viewbox/`

**SVG Coordinate System**:
- ViewBox: `0 0 400 300` (400x300 SVG units)
- Path coordinates in SVG units (e.g., M200,220)

**PowerPoint Coordinate System**:
- Slide size: Default 10" × 7.5" = 9,144,000 × 6,858,000 EMU
- 1 inch = 914,400 EMU
- Coordinate origin: Top-left

**Critical Transformation**:
```
SVG (400×300) → PowerPoint (9,144,000×6,858,000 EMU)
Scale factor X: 9,144,000 / 400 = 22,860 EMU per SVG unit
Scale factor Y: 6,858,000 / 300 = 22,860 EMU per SVG unit
```

**Potential Issues**:
- Aspect ratio distortion
- Origin point mapping
- Scaling calculation errors
- EMU conversion precision

### Phase 5: DrawingML Generation
**Component**: XML generation
**Location**: `src/svg2drawingml.py`, DrawingML templates

**Expected Output Structure**:
```xml
<p:sp>
  <p:spPr>
    <a:custGeom>
      <a:pathLst>
        <a:path w="9144000" h="6858000">
          <a:moveTo><a:pt x="4572000" y="5074200"/></a:moveTo>
          <a:cubicBezTo>...</a:cubicBezTo>
          <a:close/>
        </a:path>
      </a:pathLst>
    </a:custGeom>
  </p:spPr>
</p:sp>
```

**Potential Issues**:
- Path coordinate scaling in `w` and `h` attributes
- Individual point coordinate calculation
- Bezier control point transformation
- XML namespace handling

### Phase 6: PPTX Assembly
**Component**: PowerPoint package creation
**Location**: `src/svg2pptx.py`, ZIP/OOXML handling

**Expected Result**: Valid `.pptx` file with embedded vector shapes

**Current Status**: ✅ PPTX file creation successful, LibreOffice loads correctly

## Specific Debug Points

### Debug Point 1: Path Command Parsing
**Test**: Verify each path's `d` attribute is correctly parsed

```python
# Test each path individually
paths = [
    "M200,220 C200,220 150,170 120,140...",  # Heart
    "M100,50 L105,65 L120,65...",           # Star
    "M50,100 Q150,50 250,100 T350,150",     # Curved line
    "M300,200 L320,180 L340,185...",        # Polygon
    "M60,200 C60,180 80,180 100,200..."     # Bezier
]
```

### Debug Point 2: Coordinate Transformation
**Test**: Verify SVG coordinates → EMU conversion

```python
# SVG heart start point: (200, 220) in 400×300 viewBox
# Expected EMU: (4572000, 5074200) in 9144000×6858000 slide
svg_x, svg_y = 200, 220
viewbox_width, viewbox_height = 400, 300
slide_width_emu, slide_height_emu = 9144000, 6858000

expected_x = (svg_x / viewbox_width) * slide_width_emu  # 4572000
expected_y = (svg_y / viewbox_height) * slide_height_emu  # 5074200
```

### Debug Point 3: DrawingML Path Generation
**Test**: Verify generated XML structure and coordinates

**Current Issue Analysis**:
- Blue line renders but wrong shape → Path command conversion issue
- Yellow star renders correctly → Simple polygon paths work
- Missing elements → Coordinate scaling or viewport issues
- Wrong positions → Origin/offset calculation errors

## Diagnostic Steps

### Step 1: Path-by-Path Analysis
Create individual SVG files for each path:
1. `debug_heart.svg` - Test heart path alone
2. `debug_star.svg` - Test star path alone
3. `debug_curve.svg` - Test curved line alone
4. `debug_polygon.svg` - Test polygon alone
5. `debug_bezier.svg` - Test bezier curves alone

### Step 2: Coordinate Logging
Add debug logging to track coordinate transformations:
```python
print(f"SVG point: ({svg_x}, {svg_y})")
print(f"EMU point: ({emu_x}, {emu_y})")
print(f"Scale factors: ({scale_x}, {scale_y})")
```

### Step 3: DrawingML Inspection
Examine generated XML for each path:
```bash
# Extract PPTX contents
unzip -q test_multiple_paths.pptx -d pptx_contents/
cat pptx_contents/ppt/slides/slide1.xml | python -m xml.dom.minidom
```

### Step 4: LibreOffice Comparison
Test with different rendering engines:
- LibreOffice Impress
- Microsoft PowerPoint (if available)
- PowerPoint Online
- Google Slides import

## Fix Strategy

### Priority 1: Coordinate System Fix
- Verify viewBox to slide scaling calculation
- Test origin point mapping (SVG top-left → PowerPoint top-left)
- Validate EMU conversion precision

### Priority 2: Path Geometry Fix
- Debug bezier curve control point transformation
- Verify smooth curve (S, T) command handling
- Test quadratic-to-cubic bezier conversion

### Priority 3: Multi-Path Rendering
- Investigate shape layering/z-order
- Check for coordinate overflow/clipping
- Verify each path gets separate `<p:sp>` element

## Expected Outcomes

After fixes, LibreOffice rendering should show:
- ❤️ Red heart shape at center-bottom (coordinates ~200,220)
- ⭐ Yellow star at top-left (coordinates ~100,50)
- 〰️ Blue curved line across middle (50,100 → 350,150)
- 🔷 Purple polygon at bottom-right (300,200 area)
- 🌊 Orange bezier curves at bottom-left (60,200 area)

All elements should be positioned correctly and maintain proper proportions within the PowerPoint slide dimensions.