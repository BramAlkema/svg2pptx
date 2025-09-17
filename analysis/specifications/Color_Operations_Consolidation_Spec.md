# Color Operations Consolidation Specification

## Problem Statement

The SVG2PPTX codebase has architectural duplication in color operations:

1. **Main Color System** (`src/colors.py`): General color parsing, saturation adjustment, luminance calculations
2. **Filter Color System** (`src/converters/filters/image/color.py`): SVG filter effects with overlapping operations

This creates maintenance burden, code duplication, and potential inconsistencies.

## Current State Analysis

### Main Color System (`colors.py`) - 2,129 LOC
**Has:**
- Saturation adjustment: `adjust_saturation()` (line 2104)
- Luminance calculations: `calculate_luminance()` (line 1807)
- Color space matrices: XYZ transformation matrices (lines 274, 386)

**Missing:**
- Hue rotation operations
- 4×5 color matrix transformations
- Luminance-to-alpha conversion

### Filter Color System (`color.py`) - 823 LOC
**Has (Duplicated):**
- Saturation operations: `ColorMatrixType.SATURATE` (line 174)
- Hue rotation: `ColorMatrixType.HUE_ROTATE` (line 177)
- Luminance-to-alpha: `ColorMatrixType.LUMINANCE_TO_ALPHA` (line 180)
- 4×5 color matrices: Full matrix transformations (line 172)

## Solution Architecture

### Phase 1: Extend Main Color System
Add missing operations to `src/colors.py`:

1. **Hue Rotation Function**
   ```python
   def rotate_hue(color: ColorInfo, degrees: float) -> ColorInfo:
       """Rotate color hue by specified degrees."""
   ```

2. **4×5 Color Matrix Operations**
   ```python
   def apply_color_matrix(color: ColorInfo, matrix: List[float]) -> ColorInfo:
       """Apply 4×5 color transformation matrix."""
   ```

3. **Luminance-to-Alpha Conversion**
   ```python
   def luminance_to_alpha(color: ColorInfo) -> ColorInfo:
       """Convert luminance to alpha channel."""
   ```

### Phase 2: Refactor Filter System
Modify `src/converters/filters/image/color.py` to use main color system:

1. Import color operations from main system
2. Replace local implementations with main system calls
3. Keep filter-specific logic (DrawingML generation, parameter parsing)

### Phase 3: Consolidate NumPy Optimizations
Update `src/converters/filters/numpy_color_matrix.py` to use unified color operations.

## Technical Specifications

### API Design

#### 1. Hue Rotation
```python
def rotate_hue(color: ColorInfo, degrees: float) -> ColorInfo:
    """
    Rotate color hue by specified degrees.

    Args:
        color: Source color
        degrees: Rotation angle (-360 to 360)

    Returns:
        ColorInfo with rotated hue
    """
```

#### 2. Color Matrix Transform
```python
def apply_color_matrix(color: ColorInfo, matrix: List[float]) -> ColorInfo:
    """
    Apply 4×5 color transformation matrix.

    Args:
        color: Source color
        matrix: 20 values representing 4×5 matrix [R G B A offset] × 4 rows

    Returns:
        Transformed ColorInfo
    """
```

#### 3. Luminance to Alpha
```python
def luminance_to_alpha(color: ColorInfo) -> ColorInfo:
    """
    Convert color luminance to alpha channel.

    Args:
        color: Source color

    Returns:
        ColorInfo with luminance as alpha, RGB = (0,0,0)
    """
```

## Implementation Tasks

### Task 1: Extend Main Color System
- [ ] Add `rotate_hue()` function to `colors.py`
- [ ] Add `apply_color_matrix()` function to `colors.py`
- [ ] Add `luminance_to_alpha()` function to `colors.py`
- [ ] Add comprehensive tests for new functions

### Task 2: Refactor Filter Color System
- [ ] Import color operations from main system in `color.py`
- [ ] Replace `_generate_hue_rotate_dml()` to use main system
- [ ] Replace saturation logic to use `adjust_saturation()`
- [ ] Replace luminance-to-alpha to use main system
- [ ] Update matrix operations to use `apply_color_matrix()`
- [ ] Maintain DrawingML generation logic

### Task 3: Update NumPy Optimizations
- [ ] Modify `numpy_color_matrix.py` to use unified color operations
- [ ] Ensure vectorized versions maintain compatibility
- [ ] Update performance tests

### Task 4: Testing & Validation
- [ ] Unit tests for consolidated operations
- [ ] Integration tests for filter effects
- [ ] Performance benchmarks to ensure no regression
- [ ] Visual validation of PowerPoint output

## Success Criteria

1. **Single Source of Truth**: All color operations centralized in `colors.py`
2. **No Duplication**: Filter system uses main color system exclusively
3. **Maintained Performance**: NumPy optimizations still achieve 40-120x speedups
4. **Backward Compatibility**: All existing filter effects work unchanged
5. **Consistent Results**: Identical output for same color transformations

## Risk Mitigation

1. **Breaking Changes**: Maintain existing APIs during transition
2. **Performance Impact**: Validate no regression in color processing speed
3. **Output Differences**: Extensive visual testing of PowerPoint generation
4. **Integration Issues**: Gradual rollout with comprehensive testing

## Estimated Timeline

- **Task 1**: 2-3 hours (extend main color system)
- **Task 2**: 3-4 hours (refactor filter system)
- **Task 3**: 1-2 hours (update NumPy optimizations)
- **Task 4**: 2-3 hours (testing & validation)

**Total**: 8-12 hours

## Files Affected

1. `src/colors.py` - Add new color operations
2. `src/converters/filters/image/color.py` - Refactor to use main system
3. `src/converters/filters/numpy_color_matrix.py` - Update imports/calls
4. `tests/unit/utils/test_colors.py` - Add tests for new operations
5. `tests/unit/converters/filters/image/test_color.py` - Update integration tests