# Visual Comparison Testing for SVG2PPTX

## Overview

This visual testing system provides **before/after screenshot comparison** between SVG source files and their converted PPTX results. It's designed to help with:

- **Visual regression testing** - Detect when changes break existing functionality
- **Quality validation** - See exactly how well SVG2PPTX converts different elements
- **Development feedback** - Immediate visual confirmation of improvements
- **Documentation** - Visual proof of system capabilities

## What It Creates

The system generates a comprehensive visual testing suite with:

1. **SVG Screenshots** - Original SVG rendered in browser (Playwright)
2. **PPTX Screenshots** - Converted PowerPoint slides (LibreOffice)
3. **Side-by-Side Comparisons** - HTML pages showing both results
4. **Test Report** - Overview of all tests with links to individual comparisons

## Quick Start

### Run Visual Tests

```bash
# Standalone execution
python run_visual_tests.py

# Or via pytest
pytest tests/visual/test_visual_comparison.py -v
```

### View Results

The system creates several output files:

- **Main Report**: `tests/visual/results/visual_test_report.html`
- **Individual Comparisons**: `tests/visual/results/comparisons/{test_name}_comparison.html`
- **Source Files**: `tests/visual/results/svgs/{test_name}.svg`
- **Screenshots**: `tests/visual/results/{svg_screenshots,pptx_screenshots}/`

### Example Output Structure

```
tests/visual/results/
├── visual_test_report.html         # Main dashboard
├── comparisons/                     # Individual comparison pages
│   ├── basic_shapes_comparison.html
│   ├── gradients_comparison.html
│   └── ...
├── svgs/                           # Source SVG files
│   ├── basic_shapes.svg
│   └── basic_shapes.html          # Browser-rendered version
├── svg_screenshots/                # Browser screenshots
│   └── basic_shapes_svg.png
├── pptx_files/                    # Converted PowerPoint files
│   └── basic_shapes.pptx
└── pptx_screenshots/              # PowerPoint screenshots
    └── basic_shapes_pptx.png
```

## Test Cases Included

The system includes 5 sample test cases covering key SVG features:

### 1. Basic Shapes (`basic_shapes`)
- Rectangle, circle, ellipse, line
- Basic stroke and fill properties
- Simple text elements

### 2. Gradients (`gradients`)
- Linear gradients with multiple stops
- Radial gradients with transparency
- Gradient-filled shapes

### 3. Transforms (`transforms`)
- Translation, rotation, scaling
- Complex transform combinations
- Transform group nesting

### 4. Paths (`paths`)
- Curved paths with quadratic/cubic Bézier curves
- Complex path shapes
- Path fill and stroke

### 5. Text (`text`)
- Multiple font families and sizes
- Bold, italic, underlined text
- Text alignment and positioning

## Integration with Test Suite

### As Pytest Tests

```bash
# Run visual tests as part of test suite
pytest tests/visual/ -v

# Run only visual tests
pytest tests/visual/test_visual_comparison.py::test_visual_comparisons -v
```

### Before/After Validation

Use the system to validate changes:

```bash
# Before making changes
python run_visual_tests.py
mv tests/visual/results tests/visual/before_changes

# Make your improvements
# ... edit code ...

# After making changes
python run_visual_tests.py
mv tests/visual/results tests/visual/after_changes

# Compare the before/after results manually
```

## Customization

### Adding New Test Cases

Edit `tests/visual/test_visual_comparison.py` in the `create_sample_test_cases()` function:

```python
def create_sample_test_cases() -> List[VisualTestCase]:
    test_cases = []

    # Add your custom test
    test_cases.append(VisualTestCase(
        name="my_custom_test",
        description="Description of what this tests",
        svg_content="""
        <svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
            <!-- Your SVG content here -->
        </svg>
        """
    ))

    return test_cases
```

### Configuring Output Location

```python
# Change output directory
tester = VisualComparisonTester("my_custom_output_dir")
```

### Integration with CI/CD

The visual testing can be integrated into continuous integration:

```yaml
# Example GitHub Actions step
- name: Run Visual Regression Tests
  run: |
    python run_visual_tests.py
    # Upload artifacts for manual review

- name: Upload Visual Test Results
  uses: actions/upload-artifact@v3
  with:
    name: visual-test-results
    path: tests/visual/results/
```

## Technical Details

### Dependencies

- **Playwright** - Browser automation for SVG screenshots
- **LibreOffice** - PPTX to image conversion
- **PIL/Pillow** - Image processing (fallback placeholder creation)
- **python-pptx** - PPTX file creation (fallback)

### Screenshot Process

1. **SVG Rendering**: Playwright loads SVG in Chromium browser
2. **PPTX Conversion**: SVG2PPTX system converts to PowerPoint
3. **PPTX Screenshot**: LibreOffice headless converts PPTX to PNG
4. **Comparison Page**: HTML template combines both images

### Error Handling

- Graceful fallbacks when dependencies are missing
- Placeholder images for failed conversions
- Detailed error logging and reporting
- Partial test completion (individual test failures don't stop suite)

## Use Cases

### 1. Development Validation
- Run before/after making significant changes
- Quickly see if changes improve or break visual rendering
- Identify specific elements that need attention

### 2. Regression Testing
- Establish baseline "golden" screenshots
- Detect when future changes break existing functionality
- Integrate into CI/CD pipeline for automated regression detection

### 3. Quality Assessment
- Visual documentation of system capabilities
- Identify conversion quality issues
- Compare different SVG features and complexity levels

### 4. Bug Reporting
- Include visual comparison pages in bug reports
- Show expected vs actual rendering results
- Provide clear visual evidence of issues

## Future Enhancements

Potential improvements to the visual testing system:

- **Automated Comparison** - Image diff algorithms to detect changes
- **Threshold Configuration** - Acceptable difference levels
- **Baseline Management** - Save/restore reference screenshots
- **Performance Metrics** - Measure conversion time and file sizes
- **Batch Testing** - Process entire directories of SVG files
- **Integration Tests** - Test with real-world SVG files from various sources

## Troubleshooting

### Common Issues

**Playwright Not Found**
```bash
pip install playwright
playwright install chromium
```

**LibreOffice Not Found**
- Ensure LibreOffice is installed
- Check path in `_capture_pptx_screenshot()` method

**Permission Errors**
- Ensure write permissions to `tests/visual/results/` directory
- Check disk space for screenshot files

**Empty Screenshots**
- Verify SVG content is valid
- Check browser console for JavaScript errors
- Ensure SVG viewBox and dimensions are set correctly