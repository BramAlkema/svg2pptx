# Multislide Test Data

This directory contains test data and fixtures for multislide system testing.

## Directory Structure

### `svg_samples/`
SVG test files for various multislide scenarios:
- `animation_sequences/` - SVGs with animation keyframes for slide detection
- `nested_documents/` - SVGs with nested elements and hierarchical structures
- `layer_groups/` - SVGs with layer-based grouping for slide generation
- `section_markers/` - SVGs with explicit slide boundary markers
- `edge_cases/` - Malformed or complex SVGs for error testing

### `expected_outputs/`
Expected conversion results and validation data:
- PPTX structure definitions
- Slide boundary detection results
- Performance benchmarks
- Error scenario expectations

### `templates/`
PPTX template files for document generation testing:
- Standard presentation templates
- Custom slide layouts
- Template validation data

## Usage

Test files follow naming conventions:
- `simple_*` - Basic test cases
- `complex_*` - Advanced scenarios
- `error_*` - Error condition testing
- `performance_*` - Large-scale testing

Each test file includes corresponding metadata in JSON format describing:
- Expected detection results
- Conversion parameters
- Performance expectations
- Validation criteria