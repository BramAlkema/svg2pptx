# SVG Test Corpus

This directory contains a comprehensive collection of SVG test files designed to validate the SVG2PPTX conversion system across all supported features and edge cases.

## Test Categories

### Basic Shapes (`basic_shapes/`)
- **basic_rectangle.svg** - Simple rectangle with basic styling
- **basic_circle.svg** - Simple circle with fill and stroke
- **basic_ellipse.svg** - Ellipse with various dimensions
- **basic_line.svg** - Single line with stroke properties
- **basic_polygon.svg** - Simple polygon with multiple points
- **basic_polyline.svg** - Polyline with stroke styling

### Complex Paths (`complex_paths/`)
- **bezier_curves.svg** - Cubic and quadratic Bézier curves
- **arc_segments.svg** - Elliptical arc segments
- **mixed_path_commands.svg** - Paths with multiple command types
- **self_intersecting_paths.svg** - Complex self-intersecting geometry

### Text Elements (`text/`)
- **simple_text.svg** - Basic text with font styling
- **text_on_path.svg** - Text following a curved path
- **multiline_text.svg** - Text with multiple lines
- **styled_text.svg** - Text with various font properties

### Gradients (`gradients/`)
- **linear_gradient.svg** - Simple linear gradient
- **radial_gradient.svg** - Radial gradient with color stops
- **complex_gradient.svg** - Multi-stop gradient with opacity
- **gradient_transforms.svg** - Gradients with transformations

### Transforms (`transforms/`)
- **translate_transform.svg** - Translation transformations
- **rotate_transform.svg** - Rotation transformations
- **scale_transform.svg** - Scaling transformations
- **complex_transforms.svg** - Multiple combined transformations

### Groups and Nesting (`groups/`)
- **simple_group.svg** - Basic grouping of elements
- **nested_groups.svg** - Multiple levels of nesting
- **transformed_groups.svg** - Groups with transformations
- **masked_groups.svg** - Groups with masks and clipping

### Filters and Effects (`filters/`)
- **drop_shadow.svg** - Drop shadow filter effect
- **gaussian_blur.svg** - Gaussian blur filter
- **color_matrix.svg** - Color matrix transformations
- **multiple_filters.svg** - Multiple filter effects combined

### Edge Cases (`edge_cases/`)
- **empty_elements.svg** - Elements with no content
- **zero_dimensions.svg** - Elements with zero width/height
- **extreme_coordinates.svg** - Very large or very small coordinates
- **malformed_syntax.svg** - Slightly malformed but recoverable SVG
- **unicode_content.svg** - Unicode characters in text and IDs

### Stress Tests (`stress_tests/`)
- **many_elements.svg** - Large number of elements
- **deep_nesting.svg** - Very deep element nesting
- **large_coordinates.svg** - Extremely large coordinate values
- **complex_paths.svg** - Paths with thousands of points

## Test Corpus Statistics

- **Total Files**: 32 SVG files
- **Coverage Areas**: 8 major feature categories
- **Complexity Levels**: Basic, Intermediate, Advanced, Stress
- **File Sizes**: Range from 1KB to 100KB+
- **Expected Conversion Rate**: 100% (with graceful degradation for unsupported features)

## Usage

Each SVG file includes:
- Embedded documentation in `<desc>` elements
- Feature complexity indicators
- Expected conversion behavior notes
- Reference visual descriptions

## Validation Criteria

For each test file, the conversion should:
1. **Parse successfully** - No fatal parsing errors
2. **Convert completely** - All supported elements converted
3. **Maintain fidelity** - Visual appearance preserved
4. **Handle gracefully** - Unsupported features degraded appropriately
5. **Perform adequately** - Conversion within acceptable time limits