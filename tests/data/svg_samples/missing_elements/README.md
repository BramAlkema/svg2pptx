# SVG Sample Files for Missing Elements Testing

This directory contains comprehensive SVG sample files for testing the 10 critical missing SVG elements:

## Elements Covered:

1. **polyline** - Multi-point line elements
   - polyline_basic.svg - Simple polyline
   - polyline_complex.svg - Complex polyline with styling

2. **tspan** - Text span elements for rich text formatting
   - tspan_styling.svg - Basic tspan styling
   - tspan_nested.svg - Nested tspan elements

3. **image** - Embedded image elements
   - image_embedded.svg - External image reference
   - image_base64.svg - Base64 encoded image

4. **symbol + use** - Reusable graphics definitions
   - symbol_use_reusable.svg - Basic symbol and use
   - symbol_complex.svg - Complex symbol with transforms

5. **pattern** - Pattern fills and strokes
   - pattern_dots.svg - Dot pattern fill
   - pattern_stripes.svg - Stripe pattern fill

6. **feGaussianBlur** - Gaussian blur filter effect
   - filter_gaussian_blur.svg - Basic blur effect

7. **feDropShadow** - Drop shadow filter effect
   - filter_drop_shadow.svg - Drop shadow effect

8. **style** - CSS stylesheet elements
   - style_css_classes.svg - CSS classes and selectors

9. **svg** - Nested SVG elements
   - nested_svg.svg - SVG within SVG

10. **defs** - Definition containers (used in multiple samples above)

## Special Files:

- **comprehensive_missing.svg** - Combines multiple missing elements for integration testing
- **generate_samples.py** - This script for regenerating samples

## Usage:

These files are used by the test suite in `test_missing_svg_elements.py` to validate
parsing, conversion, and PPTX output generation for missing SVG elements.
