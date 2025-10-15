# Module Slicing Fixture Pack

This directory seeds focused fixtures for Phase 1 Task 1.3.

- `parser/basic_shapes.svg` – exercises gradients, clip paths, hyperlinks, and a `foreignObject` to validate `SVGParser`’s advanced feature handling during the refactor.
- `parser/malformed_gradient.svg` – intentionally malformed gradient definition used to assert XML syntax error handling in the parser.
- `parser/filter_error.svg` – includes a filter reference that forces the parser’s filter service integration to take the failure path.
- `viewbox/preserve_aspect_ratio.svg` – canonical viewport sample (`preserveAspectRatio="xMidYMid meet"`) for ViewportEngine regression tests.

Enhanced XML Builder tests rely on the built-in fallback templates provided by `core/io/template_loader.py`, which mirrors the critical template names validated by `_validate_templates`.
