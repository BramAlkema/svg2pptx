# Spec Tasks

These are the tasks to be completed for the spec detailed in @.agent-os/specs/2025-09-10-utility-standardization/spec.md

> Created: 2025-09-10
> Status: Ready for Implementation

## Tasks

- [ ] 1. Remove Duplicate HSL-to-RGB Implementation in Gradients Converter
  - [ ] 1.1 Write tests for HSL-to-RGB conversion using ColorParser in gradients.py
  - [ ] 1.2 Remove duplicate _hsl_to_rgb method (lines 253-281) from gradients.py
  - [ ] 1.3 Replace custom HSL conversion calls with ColorParser.hsl_to_rgb()
  - [ ] 1.4 Update gradient stop processing to use ColorParser methods
  - [ ] 1.5 Verify all gradient conversion tests pass with consistent ColorParser usage

- [ ] 2. Replace Hardcoded Color Values with ColorParser Integration
  - [ ] 2.1 Write tests for color parsing in base.py, filters.py, and gradients.py
  - [ ] 2.2 Replace hardcoded gray "808080" in base.py with ColorParser.parse('gray')
  - [ ] 2.3 Replace hardcoded black "000000" and white "FFFFFF" in filters.py with ColorParser calls
  - [ ] 2.4 Update color fallback handling to use ColorParser default colors
  - [ ] 2.5 Verify all color-related tests pass with dynamic color parsing

- [ ] 3. Standardize Transform String Building with TransformParser
  - [ ] 3.1 Write tests for transform string generation in animations.py
  - [ ] 3.2 Replace manual transform string concatenation (lines 197-199) with TransformParser methods
  - [ ] 3.3 Ensure consistent transform matrix handling across all converters
  - [ ] 3.4 Update transform application methods to use TransformParser.to_string()
  - [ ] 3.5 Verify all transform-related tests pass with standardized parser usage

- [ ] 4. Integrate ViewportResolver for Consistent Coordinate Mapping
  - [ ] 4.1 Write tests for viewport-aware coordinate conversion in coordinate-heavy converters
  - [ ] 4.2 Identify converters missing ViewportResolver integration (paths.py, shapes.py, text.py)
  - [ ] 4.3 Add ViewportResolver.resolve_coordinates() calls where coordinate mapping occurs
  - [ ] 4.4 Update coordinate transformation logic to be viewport-aware
  - [ ] 4.5 Verify all coordinate conversion tests pass with viewport resolution

- [ ] 5. Create Usage Guidelines and Comprehensive Testing
  - [ ] 5.1 Write comprehensive regression tests for all 14 converter modules
  - [ ] 5.2 Create usage pattern documentation defining utility integration patterns
  - [ ] 5.3 Add utility usage validation tests to prevent future inconsistencies
  - [ ] 5.4 Document BaseConverter wrapper methods vs direct import guidelines
  - [ ] 5.5 Update converter test suites to validate consistent utility usage
  - [ ] 5.6 Verify complete test suite passes with 100% utility standardization coverage