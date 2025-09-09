# Testing Conventions for Missing SVG Elements

This document outlines testing conventions, patterns, and best practices for the missing SVG elements test infrastructure.

## Table of Contents

- [Test Structure Overview](#test-structure-overview)
- [Test Categories and Markers](#test-categories-and-markers)
- [Naming Conventions](#naming-conventions)
- [Test Data Management](#test-data-management)
- [Fixtures and Validation](#fixtures-and-validation)
- [Mock Strategies](#mock-strategies)
- [Comparison and Assertion Patterns](#comparison-and-assertion-patterns)
- [Performance Testing](#performance-testing)
- [CI/CD Integration](#cicd-integration)

## Test Structure Overview

### Directory Structure
```
tests/
├── unit/
│   └── converters/
│       ├── test_missing_svg_elements.py    # Main test suite
│       ├── test_utilities.py               # Helper utilities
│       └── pptx_fixtures.py               # Expected output fixtures
├── data/
│   └── svg_samples/
│       └── missing_elements/
│           ├── generate_samples.py         # Sample generation script
│           ├── *.svg                      # SVG test samples
│           └── README.md                  # Sample documentation
└── TESTING_CONVENTIONS.md                 # This file
```

### Test Files Organization

1. **Main Test Suite** (`test_missing_svg_elements.py`)
   - Contains the primary test classes for each missing element
   - Uses pytest test class structure
   - Implements parametrized tests for comprehensive coverage

2. **Test Utilities** (`test_utilities.py`)
   - Helper classes and functions for common test operations
   - SVG parsing utilities
   - Content comparison helpers
   - Mock validation frameworks

3. **PPTX Fixtures** (`pptx_fixtures.py`)
   - Expected PPTX output structures for validation
   - Structured data classes for different shape types
   - Validation schemas and comparison functions

## Test Categories and Markers

### Primary Test Markers

Use these pytest markers to categorize and filter tests:

```python
@pytest.mark.missing_elements    # All missing elements tests
@pytest.mark.critical_missing    # Critical priority: image, feDropShadow, tspan
@pytest.mark.high_missing        # High priority: polyline, symbol, use, feGaussianBlur
@pytest.mark.medium_missing      # Medium priority: pattern, style, defs, svg
```

### Additional Markers

```python
@pytest.mark.unit               # Unit tests
@pytest.mark.converter          # Converter-specific tests
@pytest.mark.benchmark          # Performance benchmarks
@pytest.mark.slow              # Tests taking > 10 seconds
```

### Usage Example

```python
@pytest.mark.missing_elements
@pytest.mark.critical_missing
@pytest.mark.converter
class TestImageElementConversion:
    """Test image element conversion to PPTX"""
    
    def test_embedded_image_conversion(self):
        # Test implementation
        pass
```

## Naming Conventions

### Test Methods

Follow this naming pattern: `test_{element_name}_{scenario}_{expected_outcome}`

```python
def test_polyline_basic_conversion_success(self):
    """Test basic polyline converts successfully to PPTX freeform shape"""

def test_tspan_nested_styling_preserves_hierarchy(self):
    """Test nested tspan elements preserve text formatting hierarchy"""

def test_image_base64_data_extracts_correctly(self):
    """Test base64 image data is correctly extracted and processed"""
```

### Test Classes

Use descriptive class names: `Test{ElementName}Conversion`

```python
class TestPolylineConversion:
    """Tests for polyline element conversion"""

class TestTspanConversion:
    """Tests for tspan element conversion"""

class TestImageConversion:
    """Tests for image element conversion"""
```

### Test Data Files

SVG samples follow pattern: `{element_name}_{scenario}.svg`

```
polyline_basic.svg           # Basic polyline
polyline_complex.svg         # Complex polyline with styling
tspan_styling.svg           # Tspan with styling
tspan_nested.svg            # Nested tspan elements
image_embedded.svg          # External image reference
image_base64.svg            # Base64 encoded image
```

## Test Data Management

### SVG Sample Generation

Use `generate_samples.py` to create and update test SVG files:

```bash
# Generate all samples
python tests/data/svg_samples/missing_elements/generate_samples.py

# Verify samples exist
ls tests/data/svg_samples/missing_elements/*.svg
```

### Sample File Standards

Each SVG sample should:

1. **Be minimal but representative** - Test the specific element without unnecessary complexity
2. **Include proper XML declaration** - `<?xml version="1.0" encoding="UTF-8"?>`
3. **Use standard SVG namespace** - `xmlns="http://www.w3.org/2000/svg"`
4. **Have appropriate viewBox** - Sized reasonably for testing
5. **Be self-contained** - No external dependencies except for testing external references

### Test Data Loading

Use the `TestDataManager` utility:

```python
from test_utilities import TestDataManager

data_manager = TestDataManager()
svg_content = data_manager.load_svg_sample('polyline_basic')
expected_output = data_manager.load_expected_output('polyline_basic')
```

## Fixtures and Validation

### PPTX Fixture Structure

Use structured data classes from `pptx_fixtures.py`:

```python
from pptx_fixtures import PPTXFixtures, PPTXFixtureValidator

# Get expected output
expected = PPTXFixtures.polyline_basic()

# Validate actual output
validator = PPTXFixtureValidator()
validation_result = validator.validate_shape(expected, actual_output)
```

### Custom Fixtures

Create reusable fixtures for common setup:

```python
@pytest.fixture
def svg_parser():
    """Provide SVG parser instance"""
    return SVGElementParser

@pytest.fixture  
def mock_converter_registry():
    """Provide mock converter registry"""
    return MockConverterRegistry()

@pytest.fixture
def sample_svg_content():
    """Provide sample SVG content for testing"""
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
                <polyline points="10,10 50,25 90,10" stroke="blue" stroke-width="2" fill="none"/>
              </svg>'''
```

## Mock Strategies

### Mock Converter Pattern

Since actual converters don't exist yet, use consistent mock patterns:

```python
class MockConverterRegistry:
    """Mock registry for testing converter lookup and execution"""
    
    def __init__(self):
        self.converters = {}
        self.missing_elements = {
            'polyline': 'PolylineConverter',
            'tspan': 'TspanConverter',
            # ... other elements
        }
    
    def get_converter(self, element_name: str):
        """Return mock converter or None if missing"""
        if element_name in self.missing_elements:
            return None  # Simulate missing converter
        return Mock()
```

### Expected vs Actual Testing

Use structured comparison with tolerance:

```python
def test_position_accuracy(self):
    """Test that positions are accurate within tolerance"""
    expected = PPTXPosition(x=10, y=10)
    actual = {'position': {'x': 10.5, 'y': 9.8}}
    
    comparison = ContentComparisonHelpers.compare_pptx_shapes(
        expected.__dict__, 
        actual, 
        tolerance=1.0
    )
    
    assert comparison['overall_match'] is True
```

## Comparison and Assertion Patterns

### Standard Assertion Pattern

```python
def test_element_conversion(self):
    # 1. Load test data
    svg_content = load_svg_sample('element_sample.svg')
    expected_fixture = PPTXFixtures.element_sample()
    
    # 2. Parse SVG
    parser = SVGElementParser(svg_content)
    elements = parser.find_elements('element_name')
    
    # 3. Assert element found
    assert len(elements) > 0, "Element not found in SVG"
    
    # 4. Mock conversion
    mock_output = create_mock_output(elements[0])
    
    # 5. Compare with fixture
    comparison = compare_with_fixture(expected_fixture, mock_output)
    
    # 6. Assert success
    assert comparison['overall_match'], f"Conversion failed: {comparison}"
```

### Tolerance-Based Comparisons

Use appropriate tolerance levels for numeric comparisons:

```python
# Position/size comparisons - use pixel tolerance
comparison = compare_positions(expected, actual, tolerance=1.0)

# Color comparisons - exact match usually required
assert expected_color == actual_color

# Numeric attribute comparisons - small tolerance for floating point
assert abs(expected_value - actual_value) <= 0.1
```

### Error Testing Pattern

```python
def test_invalid_element_handling(self):
    """Test that invalid elements are handled gracefully"""
    invalid_svg = '<svg><invalid_element/></svg>'
    
    with pytest.raises(ConversionError) as exc_info:
        converter.convert(invalid_svg)
    
    assert "unsupported element" in str(exc_info.value).lower()
```

## Performance Testing

### Benchmark Pattern

Use `pytest-benchmark` for performance testing:

```python
@pytest.mark.benchmark
def test_parsing_performance(benchmark):
    """Benchmark SVG parsing performance"""
    svg_content = load_large_svg_sample()
    
    result = benchmark(SVGElementParser, svg_content)
    
    # Validate performance meets threshold
    assert result.stats.median < 0.1  # 100ms threshold
```

### Memory Usage Testing

```python
def test_memory_usage(self):
    """Test memory usage stays within bounds"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Perform test operation
    parser = SVGElementParser(large_svg_content)
    parser.get_element_tree_info()
    
    final_memory = process.memory_info().rss
    memory_used = final_memory - initial_memory
    
    assert memory_used < 50 * 1024 * 1024  # 50MB limit
```

## CI/CD Integration

### Running Tests Locally

```bash
# Run all missing elements tests
pytest -m missing_elements -v

# Run critical priority tests only
pytest -m critical_missing -v

# Run with coverage
pytest -m missing_elements --cov=src --cov-report=html

# Run performance benchmarks
pytest -m benchmark --benchmark-only
```

### GitHub Actions Integration

The CI pipeline includes:

1. **Missing Elements Test Job** - Runs all missing elements tests
2. **Critical Priority Tests** - Separate job for critical elements
3. **Coverage Reporting** - Specific coverage for missing elements
4. **Performance Monitoring** - Benchmark tracking over time

### Test Selection in CI

Tests are automatically selected based on markers:

- **Pull Requests**: Run critical and high priority tests
- **Main Branch Push**: Run all missing elements tests
- **Nightly Builds**: Include performance benchmarks

## Best Practices Summary

1. **Test Isolation** - Each test should be independent and atomic
2. **Descriptive Names** - Test names should clearly indicate what's being tested
3. **Comprehensive Coverage** - Test happy path, edge cases, and error conditions
4. **Performance Awareness** - Include performance assertions for critical paths
5. **Maintainable Mocks** - Use structured mock patterns that are easy to update
6. **Clear Assertions** - Use descriptive assertion messages
7. **Documentation** - Document complex test scenarios and expected behaviors
8. **Fixture Reuse** - Create reusable fixtures for common test setup
9. **Error Testing** - Always test error conditions and edge cases
10. **CI Integration** - Ensure tests run reliably in CI environment

## Example Complete Test

```python
@pytest.mark.missing_elements
@pytest.mark.critical_missing
@pytest.mark.converter
class TestImageElementConversion:
    """Test image element conversion to PPTX"""
    
    @pytest.fixture
    def image_svg_content(self):
        """Provide SVG with image element"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
                    <image x="10" y="10" width="100" height="80" href="test.jpg"/>
                  </svg>'''
    
    def test_embedded_image_conversion_success(self, image_svg_content):
        """Test embedded image converts to PPTX picture shape"""
        # Parse SVG
        parser = SVGElementParser(image_svg_content)
        images = parser.find_elements('image')
        
        # Verify image found
        assert len(images) == 1, "Expected exactly one image element"
        
        # Get expected output
        expected_fixture = PPTXFixtures.image_embedded()
        
        # Mock conversion
        validator = PPTXMockValidator()
        attrs = parser.get_element_attributes(images[0])
        mock_output = validator.create_mock_pptx_output('image', attrs)
        
        # Compare with fixture
        comparison = ContentComparisonHelpers.compare_pptx_shapes(
            expected_fixture.__dict__,
            mock_output,
            tolerance=1.0
        )
        
        # Assert success
        assert comparison['overall_match'], f"Image conversion failed: {comparison}"
        assert mock_output['shape_type'] == 'picture'
        assert mock_output['image_data'] == 'test.jpg'
```

This comprehensive testing framework ensures reliable, maintainable, and thorough testing of missing SVG elements as they are implemented.