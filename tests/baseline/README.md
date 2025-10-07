# Baseline Test Suite

Regression testing framework for fractional EMU + baked transform implementation.

## Overview

This baseline test suite captures coordinate snapshots across implementation phases to detect unintended changes and verify expected transformations.

## Test Structure

```
tests/baseline/
├── README.md                           # This file
├── generate_baseline.py                # Generate baseline PPTX files
├── extract_coordinates.py              # Extract coordinate metadata
├── compare_with_baseline.py            # Compare phases
└── outputs/
    ├── phase0/                         # Current system (baseline)
    │   ├── shapes/*.pptx
    │   ├── paths/*.pptx
    │   ├── transforms/*.pptx
    │   ├── text/*.pptx
    │   ├── gradients/*.pptx
    │   ├── filters/*.pptx
    │   ├── edge_cases/*.pptx
    │   └── metadata/
    │       ├── manifest.json           # Conversion metadata
    │       └── coordinates.json        # Coordinate snapshots
    ├── phase1/                         # After fractional EMU infrastructure
    ├── phase2/                         # After baked transforms
    ├── phase3/                         # After mapper updates
    ├── phase4/                         # After integration
    └── comparisons/
        ├── phase0_vs_phase1.json
        ├── phase0_vs_phase2.json
        └── ...
```

## Test Categories

The baseline suite includes 24 test SVGs across 7 categories:

### 1. Basic Shapes (6 SVGs)
- `basic_rectangle.svg` - Simple rectangle
- `basic_circle.svg` - Simple circle
- `basic_ellipse.svg` - Simple ellipse
- `polygon_simple.svg` - Basic polygon
- `polyline_simple.svg` - Basic polyline
- `line_simple.svg` - Simple line

**Purpose**: Verify basic shape coordinate handling

### 2. Paths (4 SVGs)
- `bezier_curves.svg` - Cubic and quadratic bezier curves
- `arc_segments.svg` - Elliptical arc segments
- `path_mixed_commands.svg` - Mixed path commands (M, L, C, Q, A, Z)
- `multiple_paths.svg` - Multiple path elements

**Purpose**: Verify complex path coordinate transformations

### 3. Transforms (3 SVGs)
- `complex_transforms.svg` - Matrix, translate, rotate, scale, skew
- `nested_groups.svg` - Nested groups with transform composition
- `transform_various.svg` - Various transform combinations

**Purpose**: **CRITICAL** - These will show different coordinates after Phase 2 (baked transforms)

### 4. Text (2 SVGs)
- `text_simple.svg` - Simple text element
- `text_styled.svg` - Styled text with transforms

**Purpose**: Verify text positioning and coordinate handling

### 5. Gradients (2 SVGs)
- `linear_gradient.svg` - Linear gradient
- `radial_gradient.svg` - Radial gradient

**Purpose**: Verify gradient coordinate transformations

### 6. Filters (2 SVGs)
- `filter_blur.svg` - Gaussian blur filter
- `filter_drop_shadow.svg` - Drop shadow filter

**Purpose**: Verify filter region coordinates

### 7. Edge Cases (5 SVGs)
- `extreme_coordinates.svg` - Very large/small coordinates
- `zero_dimensions.svg` - Zero width/height elements
- `many_elements.svg` - Large number of elements (performance)
- `tiny_values.svg` - Sub-pixel coordinate values
- `huge_values.svg` - Very large coordinate values

**Purpose**: Verify robustness and precision handling

## Usage

### Step 1: Generate Phase 0 Baseline

Before starting any implementation work, generate the baseline:

```bash
# Activate virtual environment
source venv/bin/activate

# Generate baseline PPTX files
PYTHONPATH=. python tests/baseline/generate_baseline.py --phase phase0

# Extract coordinate metadata
PYTHONPATH=. python tests/baseline/extract_coordinates.py --phase phase0
```

**Output**:
- `tests/baseline/outputs/phase0/{category}/*.pptx` - Baseline PPTX files (24 files)
- `tests/baseline/outputs/phase0/metadata/manifest.json` - Conversion metadata
- `tests/baseline/outputs/phase0/metadata/coordinates.json` - Coordinate snapshots

### Step 2: Generate Phase Snapshots

After completing each implementation phase:

```bash
# Generate phase snapshot (e.g., after Phase 1)
PYTHONPATH=. python tests/baseline/generate_baseline.py --phase phase1
PYTHONPATH=. python tests/baseline/extract_coordinates.py --phase phase1

# Compare with baseline
PYTHONPATH=. python tests/baseline/compare_with_baseline.py \
    --baseline phase0 \
    --compare phase1 \
    --save
```

### Step 3: Interpret Results

**Phase 1 vs Phase 0** (Infrastructure - Fractional EMU):
- **Expected**: 100% exact match
- **Tolerance**: 0 EMU
- **Why**: Infrastructure changes only, no coordinate transformations

**Phase 2 vs Phase 0** (Baked Transforms):
- **Expected**: Transform tests will show DIFFERENT coordinates (this is correct!)
- **Tolerance**: ∞ for transform tests, 0 EMU for others
- **Why**: Transforms now baked into coordinates instead of stored separately

**Phase 3 vs Phase 0** (Mapper Updates):
- **Expected**: Minor precision improvements (<0.01 EMU difference)
- **Tolerance**: 1 EMU
- **Why**: Fractional EMU precision improvements

**Phase 4 vs Phase 3** (Integration):
- **Expected**: 100% match with Phase 3
- **Tolerance**: 1 EMU
- **Why**: Integration complete, no coordinate changes

## Expected Differences by Phase

### Phase 1: Infrastructure Only ✅

**All tests should match Phase 0 exactly.**

```
Files compared:       24
Exact matches:        24  ✅
Minor differences:    0
Major differences:    0
```

### Phase 2: Baked Transforms ⚠️

**Transform tests will show different coordinates (expected!).**

Example from `complex_transforms.svg`:

```
Before (Phase 0):
  Shape coordinates: x=100, y=100
  Transform stored: translate(50, 50) rotate(45)

After (Phase 2):
  Shape coordinates: x=135.36, y=135.36  (transform baked in)
  Transform: none
```

Expected comparison result:

```
Files compared:       24
Exact matches:        17  ✅ (non-transform tests)
Minor differences:    7   ⚠️  (transform tests - EXPECTED)
Major differences:    0
```

Transform-affected categories:
- `transforms/` - All 3 files will differ
- `paths/` - Some files may differ
- `shapes/` - Some files may differ

### Phase 3: Precision Improvements 📊

**Minor coordinate refinements (<0.01 EMU).**

```
Files compared:       24
Exact matches:        20  ✅
Minor differences:    4   📊 (precision improvements)
Major differences:    0
```

Example precision improvement:

```
Before: x=914400  (int: 72pt exactly)
After:  x=914400  (from float: 72.0000001pt → rounds to same int)
```

### Phase 4: Integration Complete ✅

**Should match Phase 3.**

```
Files compared:       24
Exact matches:        24  ✅
Minor differences:    0
Major differences:    0
```

## Troubleshooting

### Missing SVG Files

If baseline generation reports missing SVG files:

```
⚠️  Missing: tests/data/real_world_svgs/basic_rectangle.svg
```

**Solution**: Either create the missing SVG or remove it from the baseline list in `generate_baseline.py`.

### Unexpected Differences

If Phase 1 shows differences (should match Phase 0 exactly):

```
❌ basic_rectangle.pptx: 2 differences
```

**Investigation steps**:

1. Check the comparison report:
   ```bash
   cat tests/baseline/outputs/comparisons/phase0_vs_phase1.json
   ```

2. Identify affected coordinates (x, y, cx, cy, rot)

3. Review fractional EMU implementation - likely cause:
   - Rounding behavior changed
   - Precision mode incorrectly applied
   - EMU conversion bug

### Transform Tests Not Showing Differences in Phase 2

If transform tests match Phase 0 in Phase 2 (they should differ):

```
✅ complex_transforms.pptx: Exact match  ⚠️ WRONG!
```

**Problem**: Baked transforms not being applied!

**Investigation**:
- Check parser integration - are transforms being baked?
- Verify CoordinateSpace is applying CTM
- Check that transforms aren't being stored in IR

## Integration with CI/CD

Add baseline comparison to GitHub Actions:

```yaml
# .github/workflows/baseline-tests.yml
name: Baseline Regression Tests

on:
  pull_request:
    branches: [main]

jobs:
  baseline-comparison:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Generate current phase baseline
        run: |
          PYTHONPATH=. python tests/baseline/generate_baseline.py --phase current
          PYTHONPATH=. python tests/baseline/extract_coordinates.py --phase current

      - name: Compare with Phase 0 baseline
        run: |
          PYTHONPATH=. python tests/baseline/compare_with_baseline.py \
            --baseline phase0 \
            --compare current \
            --save

      - name: Upload comparison report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: baseline-comparison
          path: tests/baseline/outputs/comparisons/
```

## Metadata Format

### Manifest (`manifest.json`)

```json
{
  "phase": "phase0",
  "timestamp": "2025-01-06T12:00:00",
  "categories": {
    "shapes": [
      {
        "svg_path": "tests/data/real_world_svgs/basic_rectangle.svg",
        "pptx_path": "tests/baseline/outputs/phase0/shapes/basic_rectangle.pptx",
        "svg_size_bytes": 456,
        "pptx_size_bytes": 28432,
        "conversion_time_ms": 45,
        "element_count": 1,
        "success": true,
        "timestamp": "2025-01-06T12:00:01"
      }
    ]
  },
  "summary": {
    "total_svgs": 24,
    "successful": 24,
    "failed": 0
  }
}
```

### Coordinates (`coordinates.json`)

```json
{
  "phase": "phase0",
  "timestamp": "2025-01-06T12:05:00",
  "files": [
    {
      "pptx_path": "tests/baseline/outputs/phase0/shapes/basic_rectangle.pptx",
      "slides": [
        {
          "slide_file": "ppt/slides/slide1.xml",
          "shapes": [
            {
              "index": 0,
              "type": "shape",
              "coordinates": {
                "x": 914400,
                "y": 914400,
                "cx": 1828800,
                "cy": 1371600,
                "rot": 0
              }
            }
          ],
          "total_shapes": 1
        }
      ],
      "total_slides": 1
    }
  ],
  "summary": {
    "total_files": 24,
    "total_slides": 24,
    "total_shapes": 87
  }
}
```

## Development Notes

### Why Baseline Testing?

The fractional EMU + baked transform implementation makes **fundamental changes** to coordinate handling:

1. **Float precision throughout pipeline** - Subtle rounding changes
2. **Transform application at parse time** - Completely different coordinate values
3. **Precision mode support** - Multiple rounding strategies

**Risk**: Unintended coordinate changes that break visual fidelity

**Mitigation**: Baseline snapshots allow us to:
- Detect unintended changes immediately
- Verify expected transformations (Phase 2)
- Track precision improvements quantitatively
- Ensure integration doesn't break prior phases

### Coordinate Extraction Strategy

We extract DrawingML coordinates directly from PPTX XML:

```xml
<a:xfrm>
  <a:off x="914400" y="914400"/>
  <a:ext cx="1828800" cy="1371600"/>
</a:xfrm>
```

**Why not visual comparison?**
- More precise (EMU-level accuracy)
- Faster (no rendering required)
- Deterministic (no anti-aliasing/font rendering variations)
- Version-independent (no PowerPoint installation required)

**Limitation**: Doesn't catch visual bugs that don't affect coordinates (e.g., color, stroke width).

### Future Enhancements

**Potential additions**:
1. Visual regression testing (screenshot comparison)
2. Performance regression tracking (conversion time)
3. File size regression tracking (PPTX compression)
4. Path command validation (beyond coordinates)
5. Gradient stop position validation
6. Animation timing validation

## References

- Implementation plan: `docs/cleanup/baseline-test-suite.md`
- Fractional EMU spec: `.agent-os/specs/2025-01-06-fractional-emu-integration.md`
- Architecture evolution: `docs/cleanup/architecture-evolution.md`
- Test preservation plan: `docs/cleanup/test-preservation-plan.md`
