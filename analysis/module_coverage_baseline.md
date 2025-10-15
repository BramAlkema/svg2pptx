# Module Slicing Coverage Baseline

## Core Parse (`core/parse/parser.py`)
- Current coverage: **~60%** (409/1163 lines missing, 114/506 partial branches). Target remains 100%, so additional work is needed around clip-path fallbacks, large IR conversion branches, and deferred cleanup paths.
- Gaps cluster around:
  - Error handling and fallback branches for unsupported SVG constructs (e.g., clip-path fallbacks, filter chains, animation parsing).
  - ForeignObject, gradient, and typography normalization paths that are only exercised in complex fixtures.
  - Batch-processing utilities for mask/path resolution and deferred resource cleanup.
- Existing tests hit the happy-path parsing flows; we lack fixtures targeting failure/recovery logic, advanced text features, and EMF fallbacks.

- Current coverage: **~17%** (519/660 lines missing). The new unit tests cover presentation creation, fluent builder wiring, and content-types overrides; remaining gaps include path/image generator helpers and lighting/filter effect utilities.
- No unit or integration tests currently instantiate the builder; legacy tests exercise `core.utils.xml_builder` instead.
- Key behaviors to validate:
  - Template-loader validation (`_validate_templates`) and ID counter lifecycle.
  - Presentation/slide element generation, shape insertion, and EMU positioning helpers.
  - Path/text/image shape generators plus lighting/filter effect helpers.
  - Fluent builder façade (`FluentShapeBuilder`) and convenience factory functions.

- Current coverage: **~41%** (325/560 lines missing). Batch viewport extraction, meet/slice scaling, and EMU transforms are now exercised; batch content-bound calculation and edge-case alignment branches still lack coverage.
- Coverage gaps span the entire module, including:
  - Vectorized parsing of `viewBox` and `preserveAspectRatio`.
  - Batch viewport extraction with unit conversion contexts.
  - Core mapping pipeline (`batch_resolve_svg_viewports`, `resolve_single`, clipping decisions).
  - Fluent API helpers (`for_svg`, `with_slide_size`, `complete_alignment_chain`).

## Next Steps (Task 1.3)
1. Build deterministic fixtures that exercise:
   - Complex SVG inputs with gradients, hyperlinks, and foreign objects (parser).
   - Template-driven slide/shape generation flows (enhanced XML builder).
   - Diverse `viewBox`/PAR combinations and unit conversion scenarios (viewport engine).
2. Layer unit tests for critical helpers plus integration-style smoke tests that stitch together the public APIs.
3. Target ≥95% line coverage for XML builder and viewbox modules, and incremental improvements toward 100% for the parser by covering failure branches and EMF fallbacks.
