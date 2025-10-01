# Marker Converter Enhancement Specification

## Current State Analysis

### ✅ What Already Exists
- **Complete MarkerConverter class** in `src/converters/markers.py` with marker/symbol processing
- **Full Matrix class** in `src/transforms/core.py` with all required methods:
  - `Matrix.translate()`, `Matrix.scale()`, `Matrix.rotate()` ✅
  - `matrix.decompose()` returning translation/rotation/scale ✅
  - `matrix @ other` operator support ✅
- **Services architecture** with transform_parser accessible via `self.services.transform_parser`
- **Color system** in place with parsing capabilities

### 🔧 Required Fixes

#### 1. Import and Type Fixes
**Location**: `src/converters/markers.py` lines 27-35

**Current Issues**:
```python
from ..transforms import Matrix  # Wrong import path
```

**Fix**:
```python
from typing import List, Dict, Tuple, Optional, Any, TYPE_CHECKING
from ..transforms.core import Matrix
if TYPE_CHECKING:
    from ..color import Color
```

#### 2. Transform Composition
**Location**: Throughout marker positioning methods

**Current Issue**: Direct matrix manipulation without services integration

**Fix**: Use `self.services.transform_parser.parse_to_matrix()` and compose via Matrix operators

#### 3. DrawingML Generation Issues
**Current Problems**:
- Invalid `<a:rot>` child elements (should be `rot="..."` attribute)
- Invalid `<a:pathData d="...">` elements (not valid DrawingML)
- No preset geometry support for standard arrows

**Solution**:
- Implement `_xfrm_attrs_and_body()` helper returning `(attrs, body)` tuple
- Use DrawingML preset geometries: `triangle`, `ellipse`, `rect`, `diamond`
- Proper `<a:xfrm rot="60000units">` with `<a:off>` child structure

#### 4. Child Element Conversion
**Current Issue**: Raw SVG passthrough instead of proper DrawingML conversion

**Required**: Convert marker children through ConverterRegistry for full SVG→DrawingML conversion

#### 5. Color Extraction Robustness
**Current Issue**: Assumes specific Color API

**Required**: Support multiple Color APIs: `rgb()`, `to_hex()`, `hex` attribute

#### 6. Curve Tangent Calculation
**Current Issue**: Simple line-segment angles, no curve tangent support

**Required**: Proper tangent calculation for C/S/Q/T/A commands using Bezier derivatives

## Implementation Plan

### Phase 1: Core Infrastructure (2 hours)
1. **Fix imports** - Update to use correct transform/core paths
2. **Add xfrm helper** - Implement proper DrawingML transform structure
3. **Fix color extraction** - Robust color-to-hex conversion supporting multiple APIs

### Phase 2: DrawingML Compliance (3 hours)
1. **Replace invalid elements** - Remove `<a:pathData>`, use preset geometries
2. **Fix transform structure** - Proper `rot` attribute + `<a:off>` child pattern
3. **Standard arrow mapping** - Map arrow types to DrawingML presets

### Phase 3: Advanced Features (4 hours)
1. **Registry integration** - Convert marker children through ConverterRegistry
2. **Tangent calculation** - Implement curve tangent math for accurate arrow orientation
3. **Path analyzer service** - Optional integration with `services.path_analyzer.tangent_angles()`

## Detailed Fixes Required

### A. Transform Helper Method
```python
def _xfrm_attrs_and_body(self, matrix: Matrix, context: ConversionContext) -> Tuple[str, str]:
    """Build DrawingML transform with proper rot attribute and off child."""
    d = matrix.decompose()
    attrs = f' rot="{int(d["rotation"] * 60000)}"' if abs(d['rotation']) > 1e-9 else ''
    body = ''
    if abs(d['translateX']) > 1e-9 or abs(d['translateY']) > 1e-9:
        tx = context.to_emu(f"{d['translateX']}px")
        ty = context.to_emu(f"{d['translateY']}px")
        body = f'<a:off x="{tx}" y="{ty}"/>'
    return attrs, body
```

### B. Robust Color Conversion
```python
def _color_to_hex(self, color: "Color") -> Optional[str]:
    """Extract RRGGBB hex from Color object supporting multiple APIs."""
    # Try rgb() method
    if hasattr(color, "rgb") and callable(color.rgb):
        try:
            r, g, b = color.rgb()
            return f"{int(r):02X}{int(g):02X}{int(b):02X}"
        except: pass
    # Try to_hex() method
    if hasattr(color, "to_hex") and callable(color.to_hex):
        try:
            h = color.to_hex().lstrip("#")
            if len(h) >= 6: return h[:6].upper()
        except: pass
    # Try hex attribute
    if hasattr(color, "hex"):
        h = getattr(color, "hex", "").lstrip("#")
        if len(h) >= 6: return h[:6].upper()
    return None
```

### C. Curve Tangent Calculation
```python
def _compute_path_tangents(self, commands: List[Tuple]) -> List[float]:
    """Compute tangent angles using Bezier derivatives for curves."""
    # Priority 1: Use services.path_analyzer if available
    try:
        if hasattr(self.services, "path_analyzer"):
            return self.services.path_analyzer.tangent_angles(commands)
    except: pass

    # Priority 2: Compute from Bezier derivatives
    # C command: derivative = 3*(P3-P2) at end
    # Q command: derivative = 2*(P2-P1) at end
    # H/V: axis-aligned tangents
    # L: line segment angle
```

### D. Registry-Based Child Conversion
```python
def _generate_custom_marker_drawingml(self, marker_def, transform_matrix, color, context):
    """Convert marker children via ConverterRegistry instead of raw XML."""
    registry = context.converter_registry or self._get_child_registry()

    # Find original <marker> element and convert its children
    marker_elem = self._find_marker_element(marker_def.id, context.svg_root)
    child_xml_parts = []
    if marker_elem:
        child_ctx = context.create_child_context(marker_elem)
        for child in marker_elem:
            dml = registry.convert_element(child, child_ctx)
            if dml: child_xml_parts.append(dml)

    content_drawingml = ''.join(child_xml_parts)
    # ... wrap in <p:grpSp> with proper transform
```

## Success Criteria

1. **No Invalid DrawingML**: Remove all `<a:pathData>` and `<a:rot>` child elements
2. **Proper Transform Structure**: `<a:xfrm rot="..."><a:off.../></a:xfrm>` format
3. **Full Child Conversion**: Marker children converted through ConverterRegistry
4. **Accurate Orientation**: Curve tangents used for mid/end marker positioning
5. **Robust Color Support**: Works with any Color API (rgb/hex/to_hex)
6. **Standards Compliance**: Uses DrawingML preset geometries for standard arrows

## Risk Assessment

**Low Risk**: Import fixes, color extraction, preset geometry mapping
**Medium Risk**: Transform structure changes, registry integration
**High Risk**: Curve tangent calculation (mathematical complexity)

**Mitigation**: Implement tangent fallback to line-segment angles if Bezier derivatives fail

## Testing Requirements

1. **Unit Tests**: Each helper method in isolation
2. **Integration Tests**: Full marker→DrawingML pipeline with curves
3. **Visual Tests**: Arrow orientation on curved paths vs straight lines
4. **Compatibility Tests**: Multiple Color API flavors
5. **PowerPoint Tests**: Generated PPTX opens and renders correctly