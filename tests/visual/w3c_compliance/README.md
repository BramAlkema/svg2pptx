# W3C SVG Compliance Testing with LibreOffice

Comprehensive W3C SVG compliance testing system using LibreOffice automation and Playwright. This system validates SVG to PPTX conversion against official W3C test cases and provides detailed compliance reports.

## Overview

This system provides:

1. **W3C Test Suite Management** - Downloads and manages official W3C SVG test cases
2. **LibreOffice Automation** - Controls LibreOffice Impress via Playwright for PPTX rendering
3. **Visual Comparison** - Advanced image comparison between SVG originals and PPTX renderings
4. **Compliance Scoring** - Multi-level compliance assessment with detailed metrics
5. **Comprehensive Reporting** - HTML and JSON reports with actionable insights

## Features

### 🎯 **Compliance Testing**
- Official W3C SVG 1.1, 2.0, and Tiny test suites
- Automated test case selection and categorization
- Multi-level compliance scoring (FULL, HIGH, MEDIUM, LOW, FAIL)
- Feature-specific compliance analysis

### 🖥️ **LibreOffice Integration**
- Headless LibreOffice automation
- Playwright-based browser control
- Automatic slideshow mode activation
- Screenshot capture with customizable quality

### 📊 **Visual Analysis**
- Structural similarity (SSIM) comparison
- Pixel-level accuracy assessment
- Color fidelity analysis
- Geometry preservation scoring
- Text readability evaluation

### 📈 **Reporting**
- HTML reports with visual comparisons
- JSON reports for programmatic analysis
- Side-by-side image comparisons
- Difference highlighting
- Performance metrics

## Setup

### 1. System Requirements

**LibreOffice Installation:**
```bash
# Ubuntu/Debian
sudo apt-get install libreoffice

# macOS
brew install --cask libreoffice

# Windows
# Download from https://www.libreoffice.org/
```

**Playwright Browser:**
```bash
playwright install chromium
```

### 2. Python Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `playwright>=1.40.0`
- `pillow>=10.0.0`
- `opencv-python>=4.8.0`
- `scikit-image>=0.22.0`
- `cairosvg>=2.7.0`
- `psutil>=5.9.0`

### 3. Configuration

Create or modify `config.yaml`:

```yaml
w3c_compliance:
  test_suite:
    type: basic  # basic, comprehensive, features, custom
    w3c_version: "1.1"
    max_tests: 50

  libreoffice:
    headless: true
    port: 8100
    screenshot_delay: 2.0

  comparison:
    tolerance: 0.85
    enable_detailed_analysis: true

  output:
    base_dir: tests/visual/w3c_compliance/results
    generate_html_report: true
```

## Quick Start

### Basic Compliance Test

```python
import asyncio
from compliance_runner import W3CComplianceTestRunner, ComplianceConfig, TestSuite

async def run_basic_test():
    # Configure
    config = ComplianceConfig(
        test_suite=TestSuite.BASIC,
        w3c_version="1.1",
        max_tests=10,
        comparison_tolerance=0.85
    )

    runner = W3CComplianceTestRunner(config)

    try:
        # Initialize (downloads W3C suite, starts LibreOffice)
        await runner.initialize()

        # Run tests
        report = await runner.run_compliance_tests()

        print(f"Overall Score: {report.overall_compliance_score:.3f}")
        print(f"Tests: {report.successful_tests}/{report.total_tests}")

    finally:
        await runner.cleanup()

# Run the test
asyncio.run(run_basic_test())
```

### Single Test Case

```python
async def test_single_case():
    config = ComplianceConfig(
        test_suite=TestSuite.CUSTOM,
        custom_test_names=["basic-shapes-rect"]
    )

    runner = W3CComplianceTestRunner(config)

    try:
        await runner.initialize()
        result = await runner.run_single_test("basic-shapes-rect")

        if result.success:
            print(f"✅ Compliance: {result.overall_compliance.value}")
            print(f"Score: {result.metrics.overall_score:.3f}")
        else:
            print(f"❌ Failed: {result.error_message}")

    finally:
        await runner.cleanup()
```

## Test Suite Types

### 1. Basic Compliance
Tests fundamental SVG features essential for basic compatibility:
- Basic shapes (rect, circle, ellipse, polygon)
- Simple paths and lines
- Basic text rendering
- Color specifications
- Simple transforms

```python
config = ComplianceConfig(test_suite=TestSuite.BASIC)
```

### 2. Comprehensive
Full W3C test suite for complete standards compliance:
- All basic features plus advanced capabilities
- Complex paths and curves
- Gradients and patterns
- Filter effects
- Advanced transforms
- Animations (where applicable)

```python
config = ComplianceConfig(test_suite=TestSuite.COMPREHENSIVE)
```

### 3. Feature-Specific
Target specific SVG feature categories:

```python
config = ComplianceConfig(
    test_suite=TestSuite.FEATURES,
    categories=["gradients", "paths", "text", "transforms"]
)
```

### 4. Custom Selection
Test specific cases by name:

```python
config = ComplianceConfig(
    test_suite=TestSuite.CUSTOM,
    custom_test_names=["basic-shapes-rect", "paths-simple", "text-basic"]
)
```

## Components

### 1. W3CTestSuiteManager

Manages W3C SVG test cases:

```python
from w3c_test_manager import W3CTestSuiteManager

manager = W3CTestSuiteManager()

# Download official test suite
manager.download_test_suite("1.1")

# Load test cases
manager.load_test_cases("1.1")

# Get test cases by category
basic_tests = manager.get_test_cases(category="basic-shapes")

# Export test manifest
manager.export_test_manifest(Path("manifest.json"))
```

### 2. LibreOfficePlaywrightController

Controls LibreOffice automation:

```python
from libreoffice_controller import LibreOfficePlaywrightController, LibreOfficeConfig

config = LibreOfficeConfig(headless=True, port=8100)
controller = LibreOfficePlaywrightController(config)

# Start LibreOffice and browser
await controller.start_libreoffice()
await controller.start_browser()

# Open presentation
await controller.open_presentation(Path("presentation.pptx"))

# Start slideshow
await controller.start_slideshow()

# Capture screenshots
results = await controller.capture_all_slides(Path("screenshots"))

# Cleanup
await controller.cleanup()
```

### 3. SVGPPTXComparator

Performs visual comparison:

```python
from svg_pptx_comparator import SVGPPTXComparator

comparator = SVGPPTXComparator(tolerance=0.85)

# Compare test case
result = await comparator.compare_test_case(
    test_case, pptx_path, controller, output_dir
)

# Check compliance
print(f"Compliance: {result.overall_compliance.value}")
print(f"Score: {result.metrics.overall_score:.3f}")

# Feature analysis
for feature in result.feature_compliance:
    print(f"{feature.feature_name}: {feature.level.value}")
```

## Configuration Options

### LibreOffice Settings

```yaml
libreoffice:
  headless: true
  port: 8100
  startup_timeout: 30
  screenshot_delay: 2.0
  additional_args:
    - "--nolockcheck"
    - "--nodefault"
```

### Comparison Settings

```yaml
comparison:
  tolerance: 0.85
  enable_detailed_analysis: true
  reference_resolution: [1920, 1080]

  weights:
    structural_similarity: 0.25
    pixel_accuracy: 0.20
    color_fidelity: 0.15
    geometry_preservation: 0.20
    text_readability: 0.10
    visual_quality: 0.10
```

### Compliance Thresholds

```yaml
compliance_thresholds:
  full: 0.95    # Perfect compliance
  high: 0.85    # Minor differences
  medium: 0.70  # Acceptable differences
  low: 0.50     # Basic functionality
  fail: 0.0     # Non-functional
```

## Testing

### Unit Tests

```bash
# Run unit tests
pytest tests/visual/w3c_compliance/test_integration.py -v

# Test specific components
pytest tests/visual/w3c_compliance/test_integration.py::TestW3CTestSuiteManager -v
pytest tests/visual/w3c_compliance/test_integration.py::TestSVGPPTXComparator -v
```

### Integration Tests

```bash
# Requires LibreOffice installation
pytest tests/visual/w3c_compliance/test_integration.py -m integration -v
```

### Performance Tests

```bash
# Performance benchmarks
pytest tests/visual/w3c_compliance/test_integration.py -m performance -v
```

## CLI Usage

Create a command-line interface:

```python
#!/usr/bin/env python3
"""CLI for W3C compliance testing."""

import click
import asyncio
from compliance_runner import W3CComplianceTestRunner, ComplianceConfig, TestSuite

@click.command()
@click.option('--suite', type=click.Choice(['basic', 'comprehensive', 'features', 'custom']),
              default='basic', help='Test suite type')
@click.option('--max-tests', type=int, default=20, help='Maximum number of tests')
@click.option('--tolerance', type=float, default=0.85, help='Comparison tolerance')
@click.option('--output-dir', type=click.Path(), default='compliance_results',
              help='Output directory')
@click.option('--html-report/--no-html-report', default=True,
              help='Generate HTML report')
def run_compliance_tests(suite, max_tests, tolerance, output_dir, html_report):
    """Run W3C SVG compliance tests."""

    config = ComplianceConfig(
        test_suite=TestSuite(suite),
        max_tests=max_tests,
        comparison_tolerance=tolerance,
        output_dir=Path(output_dir),
        generate_html_report=html_report
    )

    async def run_tests():
        runner = W3CComplianceTestRunner(config)
        try:
            await runner.initialize()
            report = await runner.run_compliance_tests()

            click.echo(f"Overall Score: {report.overall_compliance_score:.3f}")
            click.echo(f"Tests: {report.successful_tests}/{report.total_tests}")

            if html_report:
                click.echo(f"Report: {output_dir}/compliance_report_*.html")

        finally:
            await runner.cleanup()

    asyncio.run(run_tests())

if __name__ == '__main__':
    run_compliance_tests()
```

Usage:
```bash
python compliance_cli.py --suite basic --max-tests 10
python compliance_cli.py --suite comprehensive --tolerance 0.90
python compliance_cli.py --suite features --output-dir results/features
```

## Compliance Metrics

### Overall Score Calculation

The overall compliance score is a weighted average of:

- **Structural Similarity (25%)** - SSIM comparison of image structure
- **Pixel Accuracy (20%)** - Pixel-level color accuracy
- **Color Fidelity (15%)** - Histogram-based color comparison
- **Geometry Preservation (20%)** - Edge detection and shape analysis
- **Text Readability (10%)** - Text clarity and contrast
- **Visual Quality (10%)** - Overall image quality metrics

### Compliance Levels

- **FULL (≥95%)** - Perfect or near-perfect compliance
- **HIGH (≥85%)** - Minor differences, excellent compliance
- **MEDIUM (≥70%)** - Acceptable differences, good compliance
- **LOW (≥50%)** - Major differences, basic functionality
- **FAIL (<50%)** - Non-functional or severely incorrect

### Feature-Specific Analysis

Individual SVG features are analyzed separately:

- **Basic Shapes** - Rectangle, circle, ellipse, polygon rendering
- **Paths** - Path command accuracy and curve rendering
- **Text** - Font rendering, positioning, and styling
- **Gradients** - Linear and radial gradient accuracy
- **Transforms** - Translation, rotation, scaling, skewing
- **Colors** - Color space accuracy and transparency
- **Filters** - Filter effects (where supported)

## Troubleshooting

### Common Issues

**LibreOffice not starting:**
```bash
# Check LibreOffice installation
soffice --version

# Check port availability
netstat -an | grep 8100

# Try different port
config.libreoffice_port = 8101
```

**Screenshot capture fails:**
```bash
# Increase delays
config.screenshot_delay = 3.0
config.page_transition_delay = 1.5

# Check browser installation
playwright install chromium
```

**Low compliance scores:**
- Verify SVG2PPTX converter implementation
- Check LibreOffice version compatibility
- Review test case selection and difficulty
- Adjust tolerance levels if appropriate

**Memory issues:**
```yaml
performance:
  memory_limit_mb: 4096
  cleanup_temp_files: true
  max_concurrent_tests: 1
```

### Debugging

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Component-specific logging
logging.getLogger('libreoffice_controller').setLevel(logging.DEBUG)
logging.getLogger('svg_pptx_comparator').setLevel(logging.DEBUG)
```

Check intermediate files:
```python
config.save_intermediate_files = True
# Files saved to: output_dir/comparisons/test_name/
```

## Best Practices

1. **Start Small** - Begin with basic test suite before comprehensive testing
2. **Monitor Performance** - LibreOffice automation can be resource-intensive
3. **Version Control** - Track compliance scores over time
4. **Regular Testing** - Integrate into CI/CD pipeline
5. **Custom Baselines** - Create project-specific test cases
6. **Error Analysis** - Review failed tests for patterns
7. **Hardware Requirements** - Ensure adequate memory and CPU for LibreOffice

## Integration with CI/CD

### GitHub Actions

```yaml
name: W3C Compliance Tests

on: [push, pull_request]

jobs:
  compliance:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Install LibreOffice
      run: |
        sudo apt-get update
        sudo apt-get install -y libreoffice

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r tests/visual/w3c_compliance/requirements.txt
        playwright install chromium

    - name: Run compliance tests
      run: |
        python -m pytest tests/visual/w3c_compliance/test_integration.py -v

    - name: Upload compliance report
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: compliance-report
        path: tests/visual/w3c_compliance/results/
```

## Support

For issues and questions:

1. Check LibreOffice installation and version
2. Verify Playwright browser installation
3. Review log files in output directory
4. Check example usage files
5. Run unit tests to verify setup

## Example Files

- `example_usage.py` - Complete usage examples
- `config.yaml` - Configuration template
- `test_integration.py` - Test suite
- `requirements.txt` - Dependencies