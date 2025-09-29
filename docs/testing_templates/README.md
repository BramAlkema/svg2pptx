# Enhanced SVG Test Generation with Template Patterns

This document describes the enhanced SVG test generation system that provides converter-specific template patterns for comprehensive testing of the svg2pptx conversion pipeline.

## Overview

The template pattern system extends the existing SVG test generators with:

- **Converter-specific test patterns** based on actual converter functionality
- **Comprehensive test coverage** including scenarios, edge cases, and performance variants
- **Automated test generation** using proven testing patterns
- **Integration** with existing test infrastructure

## Architecture

### Core Components

1. **ConverterPatternLibrary** (`tests/data/generators/converter_patterns.py`)
   - Defines test patterns for all converter types
   - Maps SVG elements to test scenarios
   - Specifies edge cases and performance variants

2. **TemplatePatternGenerator** (`tests/support/template_patterns.py`)
   - Generates SVG test content using template patterns
   - Creates comprehensive test suites for each converter
   - Supports customizable generation configuration

3. **TestPatternAnalyzer** (`tests/support/test_pattern_analyzer.py`)
   - Analyzes existing test files using AST parsing
   - Extracts common testing patterns and structures
   - Identifies imports, mock patterns, assertion patterns, and fixtures

4. **AutomatedTestGenerator** (`tests/support/automated_test_generator.py`)
   - Generates test files automatically based on analyzed patterns
   - Creates unit, integration, and performance tests for converters
   - Uses Jinja2 templates for consistent test structure generation

5. **Enhanced SVGTestCorpusGenerator** (`tests/support/generate_test_corpus.py`)
   - Integrates template patterns with existing corpus generation
   - Creates organized directory structures
   - Generates enhanced metadata

6. **Enhanced SVGGenerator** (`tests/data/generators/svg_generator.py`)
   - Provides template pattern integration
   - Maintains compatibility with existing interface
   - Supports converter-specific test generation

### Supported Converter Types

- **Shapes**: rect, circle, ellipse, polygon, polyline, line
- **Paths**: Complex path commands, Bezier curves, arcs
- **Text**: Simple text, styling, tspan elements, textPath
- **Gradients**: Linear, radial, mesh gradients with multiple stops
- **Filters**: Gaussian blur, drop shadow, color matrix, chains
- **Transforms**: Translate, rotate, scale, matrix, combinations
- **Groups**: Nested hierarchies, attribute inheritance
- **Images**: External references, embedded base64, transformations
- **Markers**: Arrow markers, custom shapes, path decorations
- **Masking**: Masks, clipPath operations, transparency
- **Symbols**: Symbol definitions, use elements, reuse optimization
- **Animations**: Property animations, transforms, motion paths

## Usage

### Basic Test Generation

```python
from tests.support.template_patterns import TemplatePatternGenerator, TestGenerationConfig
from tests.data.generators.converter_patterns import ConverterType

# Configure generation
config = TestGenerationConfig(
    width=200,
    height=200,
    seed=42,
    include_edge_cases=True,
    include_performance_variants=True
)

# Create generator
generator = TemplatePatternGenerator(config)

# Generate test suite for shapes converter
test_suite = generator.generate_converter_test_suite(ConverterType.SHAPES)

# test_suite contains dict of test_name -> svg_content
for test_name, svg_content in test_suite.items():
    print(f"Generated: {test_name}")
```

### Enhanced Corpus Generation

```python
from tests.support.generate_test_corpus import SVGTestCorpusGenerator

# Create enhanced corpus generator
generator = SVGTestCorpusGenerator(
    output_dir="tests/test_data/enhanced_corpus",
    use_template_patterns=True
)

# Generate enhanced corpus with converter-specific tests
generator.generate_enhanced_corpus()
```

### Using Enhanced SVG Generator

```python
from tests.data.generators.svg_generator import SVGGenerator, SVGGeneratorConfig

# Create generator with template patterns
config = SVGGeneratorConfig(width=200, height=200)
generator = SVGGenerator(config, use_template_patterns=True)

# Generate converter-specific test suite
output_dir = Path("test_output")
generated_files = generator.generate_converter_specific_test_suite(output_dir)
```

### Automated Test Generation

```python
from tests.support.test_pattern_analyzer import TestPatternAnalyzer
from tests.support.automated_test_generator import AutomatedTestGenerator

# Analyze existing test patterns
analyzer = TestPatternAnalyzer("tests/unit/converters")
patterns = analyzer.analyze_test_directory()

# Generate tests for specific converters
generator = AutomatedTestGenerator(analyzer)
generator.analyze_converter_interfaces(Path("src/converters"))

# Generate tests for a specific converter
generated_tests = generator.generate_tests_for_converter("RectangleConverter", ["unit", "integration"])

# Generate complete test file
test_file_content = generator.generate_complete_test_file("RectangleConverter", Path("output/test_rectangle.py"))
```

## Test Categories

### Test Scenarios
Standard functional testing scenarios for each converter:
- Basic element processing
- Element combinations
- Styling applications
- Transform integration
- Advanced features

### Edge Cases
Boundary condition testing:
- Zero dimensions
- Negative coordinates
- Extremely large/small values
- Invalid parameters
- Missing attributes
- Malformed data

### Performance Variants
Performance and scalability testing:
- Single element processing
- Batch processing (10, 100, 1000 elements)
- Complex styling combinations
- Deep nesting scenarios
- High-precision calculations

## Directory Structure

The enhanced system creates organized test directories:

```
tests/test_data/enhanced_corpus/
├── converter_specific/
│   ├── shapes/
│   │   ├── scenarios/
│   │   ├── edge_cases/
│   │   └── performance/
│   ├── paths/
│   │   ├── scenarios/
│   │   ├── edge_cases/
│   │   └── performance/
│   └── ... (other converters)
├── enhanced_corpus_metadata.json
└── converter_specific_metadata.json
```

## Metadata

The system generates comprehensive metadata for each test:

```json
{
  "corpus_info": {
    "generation_method": "enhanced_template_patterns",
    "total_files": 252,
    "converter_types": ["shapes", "paths", "text", ...],
    "total_converters": 12
  },
  "converter_breakdown": {
    "shapes": {
      "total_count": 21,
      "categories": ["scenarios", "edge_cases", "performance"],
      "tests": [...]
    }
  }
}
```

## Configuration Options

### TestGenerationConfig

- `width`, `height`: Canvas dimensions
- `seed`: Random seed for reproducible generation
- `element_count_range`: Range for number of elements
- `coordinate_range`: Range for coordinate values
- `size_range`: Range for element sizes
- `color_palette`: Colors to use in generated SVGs
- `include_edge_cases`: Enable edge case generation
- `include_performance_variants`: Enable performance test generation

## Integration with Existing Tests

The template pattern system is designed to complement, not replace, existing tests:

- **Backward compatibility**: Existing test generators continue to work
- **Gradual adoption**: Template patterns can be enabled selectively
- **Legacy support**: Original corpus generation methods remain available
- **Enhanced coverage**: Template patterns add systematic coverage for all converters

## Best Practices

1. **Use deterministic seeds** for reproducible test generation
2. **Organize tests by converter type** for maintainability
3. **Include all test categories** (scenarios, edge cases, performance)
4. **Validate generated SVG** using XML parsing
5. **Monitor test execution time** for performance variants
6. **Update patterns** when adding new converter functionality

## Extending the System

### Adding New Converter Types

1. Add new converter type to `ConverterType` enum
2. Create pattern in `ConverterPatternLibrary._create_patterns()`
3. Define SVG elements, test scenarios, edge cases, and performance variants
4. Add generation methods to `TemplatePatternGenerator`

### Adding New Test Scenarios

1. Update converter pattern's `test_scenarios` list
2. Add corresponding generation method to `TemplatePatternGenerator`
3. Follow naming convention: `_generate_{scenario_name}`

### Custom Generation Logic

```python
class CustomTemplateGenerator(TemplatePatternGenerator):
    def _generate_custom_scenario(self, pattern, scenario):
        # Custom SVG generation logic
        elements = ["<rect x='10' y='10' width='50' height='30' fill='blue'/>"]
        return self._wrap_svg(elements, f"Custom - {scenario}")
```

## Testing the Template System

Run the integration tests to validate the template pattern system:

```bash
# Run template pattern integration tests
source venv/bin/activate
PYTHONPATH=. pytest tests/unit/test_template_patterns_integration.py -v

# Run automated test generation tests
PYTHONPATH=. pytest tests/unit/test_automated_test_generation.py -v

# Generate test corpus for manual inspection
python tests/support/generate_test_corpus.py --enhanced
```

## Future Enhancements

- **Dynamic pattern learning** from existing successful tests
- **Cross-converter integration** testing
- **Performance baseline management**
- **Visual regression comparison**
- **Automated test case prioritization**