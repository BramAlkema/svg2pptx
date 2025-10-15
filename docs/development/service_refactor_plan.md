# Service Refactor Slicing Plan

## Font Embedding Engine
- Extract permission analysis and validation into `core/services/font_embedding_rules.py` with a focused `PermissionChecker`.
- Move subset option construction and raw subsetting into `core/services/font_subsetter.py`; expose a `FontSubsetter` orchestration class.
- Wrap cache storage and stats updates in `core/services/font_embedding_cache.py`; let the engine accept the cache as a dependency.
- Slim `FontEmbeddingEngine` to orchestrate helpers (subset creation, batch flows, PPTX packaging) and surface a clean public API.
- Update unit tests to target helpers directly and keep integration coverage for the engine facade.
- ✅ Added focused helper coverage (`tests/unit/core/services/test_font_embedding_cache.py`, `tests/unit/core/services/test_font_embedding_rules.py`) to guard cache stats and permission decoding.
- ✅ Packaging-level regression `tests/integration/pipeline/test_font_embedding_roundtrip.py` now exercises `PackageWriter` with an embedded font payload and validates the resulting PPTX `ppt/fonts` parts and presentation relationships.
- ✅ Clean Slate converter now produces embedded fonts end-to-end (`tests/integration/pipeline/test_font_embedding_roundtrip.py::test_clean_slate_converter_embeds_fonts`), confirming `FontEmbeddingEngine` output is packaged via the presentation composer.
- ✅ Converter wiring aggregates font usage per weight/style and records the variants in `AssetEmbedder` telemetry for slide-level analytics.
- Next: expand font coverage to handle external font discovery failures gracefully and surface warnings in debug data.

## Image Processor
- Split analysis logic into `ImageAnalyzer` under `core/elements/image_analysis.py` (href parsing, dimension handling, flag evaluation, stats tracking).
- Move optimization routines into `core/elements/image_optimization.py` with an `ImageOptimizer` responsible for mutations.
- Relocate shared utilities (unit parsing, cache key generation, file size estimation) to `core/elements/image_utils.py`.
- Keep `ImageProcessor` as a thin facade combining analyzer and optimizer while maintaining backwards-compatible imports.
- Refresh unit tests to cover analyzer and optimizer in isolation and verify the facade wiring.
- ✅ PPTX packaging verified in `tests/integration/pipeline/test_image_optimization_pipeline.py`, which writes a slide with media metadata and inspects the ZIP for `ppt/media/image1.png` alongside the slide relationship.
- ✅ Clean Slate converter now exercised in `tests/integration/pipeline/test_image_optimization_pipeline.py::test_image_pipeline_generates_real_media`, which runs the end-to-end pipeline, verifies packaged media, and checks that the asset embedder captured the processed image.

## Animation Builders
- Relocate `AnimationSequenceBuilder` and `TimingBuilder` to `core/animations/sequence_builder.py` and `core/animations/timing_builder.py`.
- Provide a small shared helper for time parsing to avoid duplication across builders.
- Keep `core/animations/builders.py` as a re-export layer to preserve existing import paths.
- Extend unit tests to exercise the new module boundaries and ensure the façade continues to behave as before.

## PPTX Builder
- Factor out static package scaffolding into a dedicated manifest helper that writes content types, relationships, theme, layout, and master parts.
- Extract media handling (image registration, copying, slide relationships) into a reusable component with explicit tests.
- Move slide XML rendering to a lightweight `SlideBuilder` so the main builder only orchestrates inputs and dependencies.
- Add regression tests around the new helpers and ensure `PPTXBuilder` simply composes them in `create_minimal_pptx`.
- Follow-up: graduate the conversion service API into layered presentation builders:
  - Introduce a `core/presentation/presentation_builder.py` module exporting a `PresentationComposer` that coordinates slide assembly and package writing for single- and multi-slide outputs.
  - Wrap `DrawingMLEmbedder` in a `SlideAssembler` façade that accepts IR scenes, mapped elements, and image/font dependencies, emitting `EmbedderResult` objects without exposing low-level counters.
  - Provide an `AssetEmbedder` abstraction that batches font/image ingestion so the composer can request embeddings ahead of packaging (supports reuse across slides).
    - ✅ Initial implementation in `core/presentation/composer.py` now collects font metadata (including variant weight/style) and image descriptors per slide, exposing `iter_tracked_fonts()` / `iter_tracked_images()` for downstream reporting.
  - Keep `PackageWriter` as the low-level packager but surface a slimmer `PackageAssembler` that handles manifest construction, media collation, and PPTX serialization targets (file vs. stream).
    - ✅ `PackageAssembler` introduced in `core/presentation/composer.py`, centralising manifest creation and providing `write_stream` / `write_path` hooks for orchestration layers.
  - Expose orchestration hooks so `CleanSlateConverter`, the multipage converter, and future batch APIs can request additional slide metadata (slide notes, thumbnails, analytics) before finalizing the package.

## XML Builder
- Split `EnhancedXMLBuilder` responsibilities into dedicated modules: `shapes/`, `effects/`, `fluent.py`, `animation.py`, and `utils.py`, leaving `builder.py` as the orchestration layer.
- Kept the original string-based `XMLBuilder` available via the package root while exposing the new generator-driven builder as `EnhancedXMLBuilder`.
- Added targeted tests (`tests/unit/core/utils/test_enhanced_xml_builder_module_slicing.py`) to validate the refactored structure alongside the legacy coverage.

## Curve Text Positioning
- Created `core/algorithms/curve_text/` with sampling, Bézier utilities, positioning/rotation/collision helpers, and WordArt warp fitting modules.
- Replaced `core/algorithms/curve_text_positioning.py` with a shim that emits a deprecation warning and re-exports the new API for backward compatibility.
- Exercised curve-text consumers via `tests/unit/core/services/test_textpath_processing.py` and `tests/unit/core/policy/test_text_warp_classifier.py`.

## Parser Slice (Phase 2E)
- Split legacy `core/parse/parser.py` into helper modules under `core/parse_split/` (XML parsing, validation, clip extraction, style context, IR conversion).
- `SVGParser` now delegates to the sliced helpers while emitting a deprecation warning for direct imports.
- ✅ Added integration-focused unit coverage (`tests/unit/core/parse/test_svg_parser_integration.py`) to verify clip refs, hyperlink propagation, and IR conversion with the new stack.
- ✅ Updated e2e suites to reflect deterministic font services and current complex shape behaviour.
- Remaining follow-up: extend coverage for `core/parse_split/ir_converter.py` and resource manager hot paths.

## Phase 2D - Pipeline Converter
- Map the converter flow (SVG ingest, policy application, IR mapping, asset embedding, PPTX packaging) to discrete responsibilities ahead of the module split so cross-cutting hooks are identified early.
- Draft module boundaries for `core/pipeline/file_io.py`, `core/pipeline/policy_applier.py`, `core/pipeline/progress_tracker.py`, `core/pipeline/error_handler.py`, `core/pipeline/slide_manager.py`, and `core/pipeline/resource_manager.py`, leaving `converter.py` as orchestration glue.
- Plan the extraction order: finalize structure (Task 2D.1), generate modules (Task 2D.2), move I/O + policy wiring (Task 2D.3), peel off tracking/error surfaces (Task 2D.4), and isolate slide/resource management (Task 2D.5) before simplifying the coordinator (Task 2D.6).
- Testing cadence will mirror the spec: targeted unit runs via `pytest tests/unit/pipeline/ -v` after each extraction, culminating in a full suite pass `pytest tests/ -v` once the coordinator stabilizes.
- Converter now delegates progress/error reporting, file I/O, slide tracking, and resource management to dedicated helpers; multi-page packaging consumes recorded slide payloads so statistics aggregate across pages.
- Added unit and integration coverage for the new helpers (`tests/unit/pipeline/` and `tests/integration/test_multipage_tracing.py`) with scoped coverage commands to satisfy the 60% gate.
- Next: fold the remaining multi-slide orchestration hooks into the upcoming Task 2D.6 cleanup (ensuring batch/multipage call sites rely on `SlideManager` data rather than direct embedder access).
