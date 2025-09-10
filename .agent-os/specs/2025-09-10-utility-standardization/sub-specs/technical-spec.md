# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2025-09-10-utility-standardization/spec.md

## Technical Requirements

- **Remove duplicate HSL-to-RGB conversion** in `src/converters/gradients.py` lines 253-281 and replace with ColorParser.hsl_to_rgb() method
- **Replace hardcoded color values** in `src/converters/base.py` (gray: "808080") and `src/converters/filters.py` (black: "000000", white: "FFFFFF") with ColorParser.parse() calls
- **Standardize transform string building** in `src/converters/animations.py` lines 197-199 to use TransformParser methods instead of manual string concatenation
- **Integrate ViewportResolver** in coordinate-heavy converters that currently bypass viewport-aware coordinate mapping
- **Create usage pattern documentation** defining when to use direct utility imports vs BaseConverter wrapper methods
- **Implement comprehensive regression testing** to ensure existing functionality remains unchanged during standardization
- **Add utility usage validation tests** to prevent future inconsistencies in converter implementations
- **Update BaseConverter wrapper methods** to handle edge cases consistently across all inheriting converters
- **Performance optimization** by eliminating redundant utility instantiations and ensuring singleton patterns where appropriate