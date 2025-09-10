# Spec Requirements Document

> Spec: Universal Utility Standardization
> Created: 2025-09-10

## Overview

Standardize the usage of universal utilities (ColorParser, UnitConverter, TransformParser, ViewportResolver) across all SVG converters to eliminate inconsistencies, reduce code duplication, and improve maintainability. This standardization will ensure all converters leverage the sophisticated utility system consistently, eliminating hardcoded values and duplicate implementations.

## User Stories

### Developer Consistency Story

As a developer working on SVG converter modules, I want all converters to use universal utilities consistently, so that I can confidently make changes without worrying about different implementations across modules.

When a developer needs to modify color parsing logic, they should only need to update the ColorParser utility rather than finding and fixing multiple hardcoded color implementations across different converter files.

### Code Maintenance Story

As a maintainer of the svg2pptx codebase, I want to eliminate duplicate utility implementations, so that bug fixes and improvements only need to be made in one place.

Currently, gradients.py has a duplicate HSL-to-RGB conversion function that should use the ColorParser utility instead, reducing maintenance burden and ensuring consistency.

### Quality Assurance Story

As a QA engineer testing SVG conversions, I want consistent color, unit, and transform handling across all element types, so that conversion behavior is predictable and reliable.

All converters should produce equivalent results when processing the same SVG attributes, regardless of which converter handles the element type.

## Spec Scope

1. **Remove Duplicate Implementations** - Eliminate custom HSL-to-RGB conversion in gradients.py and use ColorParser
2. **Replace Hardcoded Values** - Replace hardcoded color values (#000000, #FFFFFF, #808080) with ColorParser calls
3. **Standardize Transform Usage** - Ensure all converters use TransformParser consistently for matrix operations
4. **Integrate ViewportResolver** - Add viewport-aware coordinate mapping where missing
5. **Create Usage Guidelines** - Document clear patterns for when to use direct imports vs BaseConverter methods

## Out of Scope

- Creating new utility functionality (utilities are feature-complete)
- Changing the BaseConverter inheritance pattern
- Modifying the universal utility APIs themselves
- Performance optimizations beyond removing duplicate code

## Expected Deliverable

1. All 14 converter modules use utilities consistently with zero hardcoded color/unit/transform values
2. Comprehensive test coverage demonstrating equivalent behavior before and after standardization
3. Clear usage guidelines document for future converter development