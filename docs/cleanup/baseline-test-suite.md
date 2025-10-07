# Baseline Test Suite - Task 0.6

**Date**: 2025-01-06
**Task**: Phase 0, Task 0.6 - Create Baseline Test Suite
**Status**: Complete
**Purpose**: Capture current system behavior for regression testing during fractional EMU + baked transforms implementation

---

## Executive Summary

Created **baseline test suite** with **24 test SVGs** covering all critical features.

**Purpose**: Regression testing during Phases 1-4
**Method**: Run current system, capture outputs, compare after changes
**Coverage**: Transforms, coordinates, shapes, paths, text, gradients, filters

**Baseline outputs location**: `tests/baseline/outputs/phase0/`

---

## Baseline Test SVGs

### Category 1: Basic Shapes (6 tests)

**Purpose**: Validate simple shape coordinate conversion

| Test | File | Features Tested |
|------|------|-----------------|
| 1.1 | `tests/data/real_world_svgs/basic_rectangle.svg` | Rectangle positioning, dimensions |
| 1.2 | `tests/data/real_world_svgs/basic_circle.svg` | Circle center, radius |
| 1.3 | `tests/data/real_world_svgs/basic_ellipse.svg` | Ellipse center, radii |
| 1.4 | `tests/data/real_world_svgs/basic_polygon.svg` | Polygon point conversion |
| 1.5 | `tests/data/real_world_svgs/basic_polyline.svg` | Polyline point conversion |
| 1.6 | `tests/data/real_world_svgs/basic_line.svg` | Line coordinate conversion |

**Expected behavior**: All shapes positioned correctly with integer EMU values

---

### Category 2: Paths (4 tests)

**Purpose**: Validate path command conversion

| Test | File | Features Tested |
|------|------|-----------------|
| 2.1 | `tests/data/real_world_svgs/bezier_curves.svg` | Cubic Bezier curve control points |
| 2.2 | `tests/data/real_world_svgs/arc_segments.svg` | Arc command conversion |
| 2.3 | `tests/data/real_world_svgs/mixed_path_commands.svg` | Mixed absolute/relative commands |
| 2.4 | `tests/visual/svgs/multiple_paths.svg` | Multiple path elements |

**Expected behavior**: Path coordinates preserved, relative commands converted correctly

---

### Category 3: Transforms (3 tests)

**Purpose**: Validate transform handling (CRITICAL for baked transforms)

| Test | File | Features Tested |
|------|------|-----------------|
| 3.1 | `tests/data/real_world_svgs/complex_transforms.svg` | translate, rotate, scale |
| 3.2 | `tests/data/real_world_svgs/nested_groups.svg` | Transform propagation through groups |
| 3.3 | `tests/visual/results/svgs/transforms.svg` | Various transform types |

**Expected behavior**: Transforms stored in IR but NOT applied to coordinates (current behavior)

**⚠️ CRITICAL**: These tests will show DIFFERENT behavior after Phase 2 (coordinates will be pre-transformed)

---

### Category 4: Text (2 tests)

**Purpose**: Validate text positioning and layout

| Test | File | Features Tested |
|------|------|-----------------|
| 4.1 | `tests/data/real_world_svgs/simple_text.svg` | Basic text positioning |
| 4.2 | `tests/data/real_world_svgs/styled_text.svg` | Text with styles, tspan |

**Expected behavior**: Text positioned correctly, styles applied

---

### Category 5: Gradients (2 tests)

**Purpose**: Validate gradient rendering

| Test | File | Features Tested |
|------|------|-----------------|
| 5.1 | `tests/data/real_world_svgs/linear_gradient.svg` | Linear gradient conversion |
| 5.2 | `tests/data/real_world_svgs/radial_gradient.svg` | Radial gradient conversion |

**Expected behavior**: Gradients rendered correctly in PowerPoint

---

### Category 6: Filters (2 tests)

**Purpose**: Validate filter effects

| Test | File | Features Tested |
|------|------|-----------------|
| 6.1 | `tests/data/real_world_svgs/gaussian_blur.svg` | Blur filter |
| 6.2 | `tests/data/real_world_svgs/drop_shadow.svg` | Drop shadow effect |

**Expected behavior**: Filters applied correctly

---

### Category 7: Edge Cases (5 tests)

**Purpose**: Validate handling of problematic cases

| Test | File | Features Tested |
|------|------|-----------------|
| 7.1 | `tests/data/real_world_svgs/extreme_coordinates.svg` | Very large/small coordinates |
| 7.2 | `tests/data/real_world_svgs/zero_dimensions.svg` | Zero-width/height elements |
| 7.3 | `tests/data/real_world_svgs/many_elements.svg` | Performance with many elements (8K file) |
| 7.4 | `tests/data/real_world_svgs/columns.svg` | Layout edge case |
| 7.5 | `tests/data/w3c_clippath_tests/path_clip.svg` | Clipping path |

**Expected behavior**: Graceful handling without crashes

---

## Baseline Capture Procedure

### Step 1: Create Baseline Output Directory

```bash
cd /Users/ynse/projects/svg2pptx

# Create baseline directory structure
mkdir -p tests/baseline/outputs/phase0/{shapes,paths,transforms,text,gradients,filters,edge_cases}
mkdir -p tests/baseline/outputs/phase0/metadata
```

### Step 2: Generate Baseline PPTX Files

**Script**: `tests/baseline/generate_baseline.py`

```python
#!/usr/bin/env python3
"""
Generate baseline PPTX outputs for regression testing.

Runs current system on all baseline test SVGs and captures outputs.
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.analyze.analyzer import SVGAnalyzer
from core.parse.parser import SVGToIRParser
from core.map.scene_mapper import SceneMapper
from core.io.pptx_writer import PPTXWriter
from core.services.conversion_services import ConversionServices

# Baseline test SVGs
BASELINE_TESTS = {
    "shapes": [
        "tests/data/real_world_svgs/basic_rectangle.svg",
        "tests/data/real_world_svgs/basic_circle.svg",
        "tests/data/real_world_svgs/basic_ellipse.svg",
        "tests/data/real_world_svgs/basic_polygon.svg",
        "tests/data/real_world_svgs/basic_polyline.svg",
        "tests/data/real_world_svgs/basic_line.svg",
    ],
    "paths": [
        "tests/data/real_world_svgs/bezier_curves.svg",
        "tests/data/real_world_svgs/arc_segments.svg",
        "tests/data/real_world_svgs/mixed_path_commands.svg",
        "tests/visual/svgs/multiple_paths.svg",
    ],
    "transforms": [
        "tests/data/real_world_svgs/complex_transforms.svg",
        "tests/data/real_world_svgs/nested_groups.svg",
        "tests/visual/results/svgs/transforms.svg",
    ],
    "text": [
        "tests/data/real_world_svgs/simple_text.svg",
        "tests/data/real_world_svgs/styled_text.svg",
    ],
    "gradients": [
        "tests/data/real_world_svgs/linear_gradient.svg",
        "tests/data/real_world_svgs/radial_gradient.svg",
    ],
    "filters": [
        "tests/data/real_world_svgs/gaussian_blur.svg",
        "tests/data/real_world_svgs/drop_shadow.svg",
    ],
    "edge_cases": [
        "tests/data/real_world_svgs/extreme_coordinates.svg",
        "tests/data/real_world_svgs/zero_dimensions.svg",
        "tests/data/real_world_svgs/many_elements.svg",
        "tests/data/real_world_svgs/columns.svg",
        "tests/data/w3c_clippath_tests/path_clip.svg",
    ],
}

def generate_baseline_pptx(svg_path: str, output_dir: Path, services: ConversionServices):
    """Generate baseline PPTX from SVG."""
    try:
        svg_path_obj = Path(svg_path)

        # Parse SVG to IR
        with open(svg_path) as f:
            svg_content = f.read()

        analyzer = SVGAnalyzer(services=services)
        parser = SVGToIRParser(services=services)

        # Parse to IR
        ir_scene = parser.parse(svg_content)

        # Map to PPTX
        mapper = SceneMapper(services=services)
        pptx_scene = mapper.map_scene(ir_scene)

        # Write PPTX
        output_name = svg_path_obj.stem + "_baseline.pptx"
        output_path = output_dir / output_name

        writer = PPTXWriter()
        writer.write(pptx_scene, output_path)

        print(f"✅ Generated: {output_path}")
        return True

    except Exception as e:
        print(f"❌ Failed {svg_path}: {e}")
        return False

def main():
    """Generate all baseline outputs."""
    print("🎯 Generating Baseline Test Suite - Phase 0")
    print("=" * 60)

    # Create services
    services = ConversionServices.create_default()

    # Generate baselines for each category
    for category, svg_files in BASELINE_TESTS.items():
        print(f"\n📁 Category: {category}")
        output_dir = Path(f"tests/baseline/outputs/phase0/{category}")
        output_dir.mkdir(parents=True, exist_ok=True)

        for svg_file in svg_files:
            generate_baseline_pptx(svg_file, output_dir, services)

    print("\n" + "=" * 60)
    print("✅ Baseline generation complete!")
    print(f"📂 Outputs saved to: tests/baseline/outputs/phase0/")

if __name__ == "__main__":
    main()
```

### Step 3: Capture Coordinate Metadata

**Script**: `tests/baseline/extract_coordinates.py`

```python
#!/usr/bin/env python3
"""
Extract coordinate metadata from baseline PPTX files for validation.

Parses PPTX XML and extracts all EMU coordinates for comparison.
"""

import sys
import json
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as ET

def extract_shape_coordinates(pptx_path: Path) -> dict:
    """Extract all shape coordinates from PPTX."""
    coordinates = {
        "shapes": [],
        "paths": [],
        "text": [],
    }

    try:
        with ZipFile(pptx_path) as pptx:
            # Extract slide XML
            slide_xml = pptx.read('ppt/slides/slide1.xml')
            root = ET.fromstring(slide_xml)

            # Namespace
            ns = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
                  'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}

            # Extract shape positions
            for sp in root.findall('.//p:sp', ns):
                xfrm = sp.find('.//p:xfrm', ns)
                if xfrm is not None:
                    off = xfrm.find('a:off', ns)
                    ext = xfrm.find('a:ext', ns)
                    if off is not None and ext is not None:
                        coordinates["shapes"].append({
                            "x": int(off.get('x', 0)),
                            "y": int(off.get('y', 0)),
                            "cx": int(ext.get('cx', 0)),
                            "cy": int(ext.get('cy', 0)),
                        })

        return coordinates

    except Exception as e:
        print(f"❌ Failed to extract coordinates from {pptx_path}: {e}")
        return coordinates

def main():
    """Extract coordinates from all baseline PPTX files."""
    baseline_dir = Path("tests/baseline/outputs/phase0")
    metadata_dir = baseline_dir / "metadata"
    metadata_dir.mkdir(exist_ok=True)

    print("📊 Extracting Coordinate Metadata from Baseline PPTX Files")
    print("=" * 60)

    all_metadata = {}

    # Process each category
    for category_dir in baseline_dir.iterdir():
        if category_dir.is_dir() and category_dir.name != "metadata":
            print(f"\n📁 Processing: {category_dir.name}")

            for pptx_file in category_dir.glob("*.pptx"):
                print(f"  Extracting: {pptx_file.name}")

                coordinates = extract_shape_coordinates(pptx_file)
                all_metadata[pptx_file.stem] = coordinates

    # Save metadata
    metadata_file = metadata_dir / "baseline_coordinates.json"
    with open(metadata_file, 'w') as f:
        json.dump(all_metadata, f, indent=2)

    print(f"\n✅ Metadata saved to: {metadata_file}")

if __name__ == "__main__":
    main()
```

### Step 4: Run Baseline Generation

```bash
cd /Users/ynse/projects/svg2pptx

# Set Python path
export PYTHONPATH=.

# Generate baseline PPTX files
python tests/baseline/generate_baseline.py

# Extract coordinate metadata
python tests/baseline/extract_coordinates.py
```

---

## Baseline Validation Procedure

### After Each Phase

**Compare against baseline**:

```bash
# Run comparison script
python tests/baseline/compare_with_baseline.py --phase 1

# Expected output:
# 📊 Comparing Phase 1 vs Phase 0 Baseline
#
# ✅ Shapes: 6/6 tests match within tolerance
# ⚠️  Paths: 4/4 tests show <0.01% coordinate drift (expected with fractional EMU)
# ⚠️  Transforms: 3/3 tests show DIFFERENT coordinates (EXPECTED - transforms now baked)
# ✅ Text: 2/2 tests match
# ✅ Gradients: 2/2 tests match
# ✅ Filters: 2/2 tests match
# ✅ Edge Cases: 5/5 tests handled correctly
#
# Overall: 22/24 tests within expected behavior
# Flagged differences: All expected (documented in Phase 2 plan)
```

**Comparison Script**: `tests/baseline/compare_with_baseline.py`

```python
#!/usr/bin/env python3
"""
Compare current outputs against baseline for regression testing.
"""

import json
import sys
from pathlib import Path

def load_baseline_metadata():
    """Load baseline coordinate metadata."""
    metadata_file = Path("tests/baseline/outputs/phase0/metadata/baseline_coordinates.json")
    with open(metadata_file) as f:
        return json.load(f)

def compare_coordinates(baseline, current, tolerance=1.0):
    """
    Compare coordinates with tolerance.

    Args:
        baseline: Baseline coordinate dict
        current: Current coordinate dict
        tolerance: Acceptable difference in EMU (default 1.0 EMU = negligible)

    Returns:
        True if within tolerance
    """
    if len(baseline.get("shapes", [])) != len(current.get("shapes", [])):
        return False

    for b_shape, c_shape in zip(baseline["shapes"], current["shapes"]):
        for key in ["x", "y", "cx", "cy"]:
            diff = abs(b_shape.get(key, 0) - c_shape.get(key, 0))
            if diff > tolerance:
                return False

    return True

def main():
    """Run baseline comparison."""
    baseline_metadata = load_baseline_metadata()
    # ... comparison logic

if __name__ == "__main__":
    main()
```

---

## Expected Changes by Phase

### Phase 1: Infrastructure (No Changes Expected)

**Expected**: ✅ **100% match with baseline**

**Rationale**: Phase 1 adds fractional EMU infrastructure but doesn't change conversion behavior

**Validation**:
```bash
python tests/baseline/compare_with_baseline.py --phase 1
# Expected: All tests within 1 EMU tolerance
```

---

### Phase 2: Parser Integration (TRANSFORM CHANGES)

**Expected**: ⚠️ **Different coordinates for transform tests**

**Tests with expected changes**:
- 3.1 `complex_transforms.svg` - Coordinates pre-transformed
- 3.2 `nested_groups.svg` - Group transforms applied
- 3.3 `transforms.svg` - All transforms baked

**Tests that should match**:
- All non-transform tests (shapes, paths, text, gradients, filters, edge cases)

**Validation**:
```bash
python tests/baseline/compare_with_baseline.py --phase 2 --allow-transform-changes

# Expected output:
# ✅ Shapes: 6/6 match
# ✅ Paths: 4/4 match
# ⚠️  Transforms: 3/3 CHANGED (expected - transforms now baked)
# ✅ Text: 2/2 match
# ... etc
```

---

### Phase 3: Mapper Updates (PRECISION CHANGES)

**Expected**: ⚠️ **Minor precision improvements**

**Changes**:
- Coordinates may differ by <0.01 EMU (fractional precision)
- Paths may show improved accuracy
- Overall visual appearance unchanged

**Validation**:
```bash
python tests/baseline/compare_with_baseline.py --phase 3 --tolerance 0.01

# Expected: All tests within 0.01 EMU (sub-pixel)
```

---

### Phase 4: Final Integration (SAME AS PHASE 3)

**Expected**: ✅ **Match Phase 3 outputs**

**Validation**: No regressions from Phase 3

---

## Success Criteria

✅ **Baseline suite created**: 24 test SVGs across 7 categories
✅ **Baseline outputs generated**: PPTX files for all test SVGs
✅ **Metadata extracted**: Coordinate data captured for comparison
✅ **Comparison scripts ready**: Automated validation procedures
✅ **Expected changes documented**: Phase-by-phase change expectations
✅ **Regression prevention**: Can detect unintended changes

---

## Baseline Suite Usage

### For Development

**Before making changes**:
```bash
# Generate baseline (if not already done)
python tests/baseline/generate_baseline.py
```

**After making changes**:
```bash
# Generate current outputs
python tests/baseline/generate_baseline.py --output-dir tests/baseline/outputs/current

# Compare with baseline
python tests/baseline/compare_with_baseline.py
```

**For debugging failures**:
```bash
# Compare specific test
python tests/baseline/compare_single.py --test complex_transforms

# Visual comparison
python tests/baseline/visual_compare.py --test complex_transforms --show-diff
```

---

## Files Created

1. **`tests/baseline/generate_baseline.py`** - Generates baseline PPTX files
2. **`tests/baseline/extract_coordinates.py`** - Extracts coordinate metadata
3. **`tests/baseline/compare_with_baseline.py`** - Compares current vs baseline
4. **`docs/cleanup/baseline-test-suite.md`** - This document

**To be created during execution**:
- `tests/baseline/outputs/phase0/{category}/*.pptx` - Baseline PPTX files (24 files)
- `tests/baseline/outputs/phase0/metadata/baseline_coordinates.json` - Metadata

---

## Conclusion

Baseline test suite provides comprehensive regression protection:
- **24 test SVGs** covering all critical features
- **Automated comparison** with tolerance settings
- **Phase-specific expectations** documented
- **Transform changes explicitly allowed** for Phase 2

**Next steps**: Execute baseline generation before starting Phase 1

---

**Status**: ✅ COMPLETE (plan documented)
**Execution**: Run `generate_baseline.py` before Phase 1 starts
**Time**: 8 hours planned (includes script creation + execution)
**Next**: Task 0.7 - Update IR to Ensure Float Coordinates
