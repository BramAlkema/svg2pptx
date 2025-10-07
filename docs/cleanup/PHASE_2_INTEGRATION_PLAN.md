# Phase 2: Baked Transforms - Integration Plan

**Date**: 2025-01-07
**Status**: In Progress (25% complete - CoordinateSpace done)

---

## Current Status

### Completed ✅
1. **CoordinateSpace class** - Full CTM stack management
   - File: `core/transforms/coordinate_space.py` (136 lines)
   - Tests: `tests/unit/transforms/test_coordinate_space.py` (21/21 passing)
   - Functionality: Push/pop transforms, matrix composition, point transformation

### Architecture Discovery ✅
Located where IR shapes are created:
- **File**: `core/parse/parser.py`
- **Method**: `_extract_recursive_to_ir()` at line 526
- **Shape creation**: Lines 541-583 (rect, circle, ellipse, path, etc.)
- **Current behavior**: Extracts raw SVG coordinates WITHOUT applying transforms

---

## Integration Points Identified

### 1. Parser Initialization (core/parse/parser.py:60)
**Current**:
```python
def __init__(self, enable_normalization: bool = True):
    self.enable_normalization = enable_normalization
    self.normalizer = SVGNormalizer() if enable_normalization else None
```

**Needed**:
```python
def __init__(self, enable_normalization: bool = True):
    self.enable_normalization = enable_normalization
    self.normalizer = SVGNormalizer() if enable_normalization else None
    
    # NEW: CoordinateSpace for baked transforms
    self.coord_space = None  # Will be initialized when svg_root is available
```

### 2. CoordinateSpace Initialization (core/parse/parser.py:344)
**Method**: `parse_to_ir()` at line 344

**Current**:
```python
def parse_to_ir(self, svg_content: str) -> tuple[list, 'ParseResult']:
    # Parse SVG content
    parse_result = self.parse(svg_content)
    
    if not parse_result.success:
        return [], parse_result
    
    # Convert DOM to IR
    ir_elements = self._convert_dom_to_ir(parse_result.svg_root)
    
    return ir_elements, parse_result
```

**Needed**:
```python
def parse_to_ir(self, svg_content: str) -> tuple[list, 'ParseResult']:
    # Parse SVG content
    parse_result = self.parse(svg_content)
    
    if not parse_result.success:
        return [], parse_result
    
    # NEW: Initialize CoordinateSpace with viewport matrix
    from ..transforms import CoordinateSpace, viewport_matrix
    from ..services.conversion_services import ConversionServices
    
    services = ConversionServices.create_default()
    vp_matrix = viewport_matrix(
        parse_result.svg_root,
        services.unit_converter,
        slide_width_emu=9144000,
        slide_height_emu=6858000
    )
    
    self.coord_space = CoordinateSpace(vp_matrix)
    
    # Convert DOM to IR
    ir_elements = self._convert_dom_to_ir(parse_result.svg_root)
    
    return ir_elements, parse_result
```

### 3. Transform Handling in Recursive Extraction (core/parse/parser.py:526)
**Method**: `_extract_recursive_to_ir()` at line 526

**Current**:
```python
def _extract_recursive_to_ir(self, element: ET.Element, ir_elements: list) -> None:
    """Recursively extract SVG elements and convert to IR"""
    
    # Extract tag name
    tag = self._get_local_tag(element.tag)
    
    # Convert specific element types to IR
    if tag == 'rect':
        ir_element = self._convert_rect_to_ir(element)
        if ir_element:
            ir_elements.append(ir_element)
    # ... other shapes
```

**Needed**:
```python
def _extract_recursive_to_ir(self, element: ET.Element, ir_elements: list) -> None:
    """Recursively extract SVG elements and convert to IR with baked transforms"""
    
    # Extract tag name
    tag = self._get_local_tag(element.tag)
    
    # NEW: Handle transform attribute
    transform_attr = element.get('transform')
    if transform_attr:
        # Parse transform string to Matrix
        from ..transforms import TransformEngine
        transform_engine = TransformEngine()
        transform_matrix = transform_engine.parse(transform_attr)
        
        # Push onto CTM stack
        self.coord_space.push_transform(transform_matrix)
    
    # Convert specific element types to IR (coordinates will be transformed)
    if tag == 'rect':
        ir_element = self._convert_rect_to_ir(element)
        if ir_element:
            ir_elements.append(ir_element)
    elif tag == 'g':
        # Groups need special handling - recurse into children
        for child in children(element):
            self._extract_recursive_to_ir(child, ir_elements)
    # ... other shapes
    
    # NEW: Pop transform when exiting element
    if transform_attr:
        self.coord_space.pop_transform()
```

### 4. Rectangle Transformation (core/parse/parser.py:600)
**Method**: `_convert_rect_to_ir()` at line 600

**Current**:
```python
def _convert_rect_to_ir(self, element: ET.Element):
    # Extract rectangle attributes
    x = float(element.get('x', 0))
    y = float(element.get('y', 0))
    width = float(element.get('width', 0))
    height = float(element.get('height', 0))
    
    # Create Rectangle IR
    return Rectangle(
        bounds=Rect(x=x, y=y, width=width, height=height),
        corner_radius=corner_radius,
        fill=fill,
        stroke=stroke,
        opacity=opacity,
    )
```

**Needed**:
```python
def _convert_rect_to_ir(self, element: ET.Element):
    # Extract rectangle attributes
    x_svg = float(element.get('x', 0))
    y_svg = float(element.get('y', 0))
    width_svg = float(element.get('width', 0))
    height_svg = float(element.get('height', 0))
    
    # NEW: Apply CTM to transform coordinates
    # Transform top-left corner
    x, y = self.coord_space.apply_ctm(x_svg, y_svg)
    
    # Transform bottom-right corner
    x2, y2 = self.coord_space.apply_ctm(x_svg + width_svg, y_svg + height_svg)
    
    # Calculate transformed width/height
    width = x2 - x
    height = y2 - y
    
    # Create Rectangle IR with TRANSFORMED coordinates
    return Rectangle(
        bounds=Rect(x=x, y=y, width=width, height=height),
        corner_radius=corner_radius,
        fill=fill,
        stroke=stroke,
        opacity=opacity,
        # NO transform field - coordinates are already baked
    )
```

### 5. Circle Transformation (core/parse/parser.py:653)
**Method**: `_convert_circle_to_ir()` at line 653

**Current**:
```python
def _convert_circle_to_ir(self, element: ET.Element):
    # Extract circle attributes
    cx = float(element.get('cx', 0))
    cy = float(element.get('cy', 0))
    r = float(element.get('r', 0))
    
    return Circle(
        center=Point(cx, cy),
        radius=r,
        fill=fill,
        stroke=stroke,
        opacity=opacity,
    )
```

**Needed**:
```python
def _convert_circle_to_ir(self, element: ET.Element):
    # Extract circle attributes
    cx_svg = float(element.get('cx', 0))
    cy_svg = float(element.get('cy', 0))
    r_svg = float(element.get('r', 0))
    
    # NEW: Apply CTM to transform center
    cx, cy = self.coord_space.apply_ctm(cx_svg, cy_svg)
    
    # NEW: Handle radius with scale
    # Get scale factors from current CTM
    ctm = self.coord_space.current_ctm
    scale_x = (ctm.a ** 2 + ctm.c ** 2) ** 0.5
    scale_y = (ctm.b ** 2 + ctm.d ** 2) ** 0.5
    
    if abs(scale_x - scale_y) < 0.001:
        # Uniform scale - can use Circle
        r = r_svg * scale_x
        
        return Circle(
            center=Point(cx, cy),
            radius=r,
            fill=fill,
            stroke=stroke,
            opacity=opacity,
            # NO transform field
        )
    else:
        # Non-uniform scale - convert to Ellipse
        return Ellipse(
            center=Point(cx, cy),
            radius_x=r_svg * scale_x,
            radius_y=r_svg * scale_y,
            fill=fill,
            stroke=stroke,
            opacity=opacity,
            # NO transform field
        )
```

### 6. Ellipse Transformation (core/parse/parser.py:726)
**Method**: `_convert_ellipse_to_ir()` at line 726

**Similar pattern to Circle - transform center and apply scale to radii**

### 7. Path Transformation (core/parse/parser.py:819)
**Method**: `_convert_path_to_ir()` at line 819

**Needed**: Transform all path commands (M, L, C, Q, A, etc.)

---

## IR Shape Modifications

### Remove Transform Fields

**Files to modify**:
1. **core/ir/shapes.py** - Remove `transform` field from Circle, Ellipse, Rectangle

**Current (core/ir/shapes.py:42)**:
```python
@dataclass
class Circle:
    center: Point
    radius: float
    fill: Optional[Paint] = None
    stroke: Optional[Stroke] = None
    opacity: float = 1.0
    transform: Optional[np.ndarray] = None  # ❌ REMOVE THIS
    effects: list[Effect] = field(default_factory=list)
```

**Needed**:
```python
@dataclass
class Circle:
    center: Point
    radius: float
    fill: Optional[Paint] = None
    stroke: Optional[Stroke] = None
    opacity: float = 1.0
    # transform field REMOVED - coordinates are pre-transformed
    effects: list[Effect] = field(default_factory=list)
```

**Same changes needed for**:
- Ellipse (line 90)
- Rectangle (line 139)

---

## Implementation Checklist

### Core Changes
- [ ] Add `coord_space` field to SVGParser.__init__()
- [ ] Initialize CoordinateSpace in parse_to_ir() with viewport matrix
- [ ] Add transform handling in _extract_recursive_to_ir()
  - [ ] Parse transform attribute
  - [ ] Push/pop CTM stack
  - [ ] Handle nested groups
- [ ] Update _convert_rect_to_ir() to apply CTM
- [ ] Update _convert_circle_to_ir() to apply CTM
- [ ] Update _convert_ellipse_to_ir() to apply CTM
- [ ] Update _convert_path_to_ir() to apply CTM
- [ ] Update _convert_polygon_to_ir() to apply CTM
- [ ] Update _convert_line_to_ir() to apply CTM

### IR Changes
- [ ] Remove `transform` field from Circle
- [ ] Remove `transform` field from Ellipse
- [ ] Remove `transform` field from Rectangle
- [ ] Update any mappers that reference these fields

### Testing
- [ ] Run existing unit tests
- [ ] Generate Phase 2 baseline
- [ ] Compare with Phase 0
- [ ] Verify transform tests show differences (EXPECTED)
- [ ] Verify non-transform tests match Phase 0

---

## Expected Validation Results

### Phase 2 vs Phase 0 Comparison

```bash
PYTHONPATH=. python tests/baseline/compare_with_baseline.py \
    --baseline phase0 \
    --compare phase2 \
    --save
```

**Expected Output**:
```
Files compared:       12
Exact matches:        10  ✅ (shapes, paths without transforms, gradients, edge cases)
Minor differences:    2   ⚠️  (complex_transforms.pptx, nested_groups.pptx - EXPECTED!)
Major differences:    0
```

**CRITICAL**: The transform test files **SHOULD differ** - this proves transforms are being baked!

**If transform tests DON'T differ**: Bug - transforms are not being applied.

---

## Estimated Effort

| Task | Estimated Time | Complexity |
|------|---------------|------------|
| Add CoordinateSpace to parser | 1h | Low |
| Implement transform push/pop | 2h | Medium |
| Update _convert_rect_to_ir | 1h | Low |
| Update _convert_circle_to_ir | 2h | Medium (handle non-uniform scale) |
| Update _convert_ellipse_to_ir | 2h | Medium |
| Update _convert_path_to_ir | 3h | High (many commands) |
| Update other shapes | 2h | Medium |
| Remove transform fields from IR | 1h | Low |
| Update mappers if needed | 2h | Medium |
| Testing and validation | 2h | Medium |
| **Total** | **18h** | |

---

## Risk Assessment

### Low Risk
- CoordinateSpace already tested and working ✅
- Viewport matrix calculation already exists ✅
- TransformEngine parser already exists ✅

### Medium Risk
- Non-uniform transforms on circles (requires Ellipse conversion)
- Path transformation complexity (many command types)
- Existing tests may need updates

### Mitigation
- Start with simple shapes (rect, circle)
- Validate incrementally with baseline comparisons
- Keep transform field initially, mark as deprecated
- Remove transform field only after full validation

---

## Success Criteria

✅ Phase 2 will be considered complete when:

1. **No IR shapes have transform fields** - All coordinates pre-transformed
2. **Transform tests show differences** - complex_transforms.pptx, nested_groups.pptx differ from Phase 0
3. **Non-transform tests match** - Other 10 files identical to Phase 0
4. **All existing tests pass** - No regressions
5. **Code is clean** - No TODOs, proper error handling

---

**Status**: Architecture analyzed, implementation plan complete, ready for execution.
**Next Step**: Implement CoordinateSpace integration in parser.
**Estimated Time to Complete**: 18 hours
