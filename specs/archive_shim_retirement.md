# Archive & Legacy Shim Retirement Plan

## Background

The Clean Slate architecture now drives the main conversion pipeline (UVBT conversions, color services, modern mapping). Archived modules (`archive/`, `archive_old/`) and scattering of "legacy" shims/fallbacks are still present for historical compatibility. To ship a self-contained version 1, we must remove runtime dependencies on archived code and rip out compatibility shims, ensuring all execution paths flow through the modern services.

## Goals

1. Zero runtime imports from `archive/` or legacy shim modules.
2. All transformation, color, clipping, text, and font logic use ConversionServices and Clean Slate utilities.
3. Pipeline diagnostics (EMU/color telemetry, cache reports) reflect only modern code paths.
4. Tests/documentation updated to reflect the simplified architecture.

## Constraints & Assumptions

- ConversionServices exposes stable `emu`, `color`, `normalize_color`, etc.
- The new ClipComputeResult/PathMapper pipelines are authoritative.
- Visual and end-to-end test suites must continue to pass; we cannot regress coverage or behavior.
- Some archived assets (sample SVGs) may remain as data but not as executable modules.

## Steped Plan

### Phase 1: Inventory & Guardrails

- [x] Generate definitive list of modules referencing `archive`/`legacy` from non-archive directories.
- [x] Add CI guard (lint/test) that fails if new runtime code imports `archive.*`.
- [x] Wrap existing shim entry points with `DeprecationWarning`/log alerts to track real usage.

**Detailed Tasks**

1. Run scripted search (`rg "archive\\."`, `rg "legacy"` etc.) excluding archive/venv to produce `reports/archive_dependencies.json`.
2. Cross-check dependency report with runtime import graph (e.g., `python -X importtime` or custom loader hook) to confirm live usage.
3. Create `tests/meta/validation/test_archive_imports.py` to assert no `archive.*` imports in core/api/cli/tests.
4. Introduce `scripts/check_legacy_usage.py` that fails on CI if warnings are emitted; document usage in README/CONTRIBUTING.

### Phase 2: Transform & Path Stack Cleanup

- [x] Refactor `core/transforms/engine.py` to remove "legacy Matrix" fallbacks; ensure all dependents use UVBT-friendly matrices.
- [x] Update `core/map/path_mapper.py` and adapters to remove `_drawingml_adapter` / legacy hooks; rely solely on new PathSystem.
- [x] Add regression tests that fail if legacy adapters are accessed (e.g., monkeypatch raising when fallback is hit).

**Detailed Tasks**

1. Add `core/transforms/matrix_utils.py` helpers if needed; migrate callers (map, path system) to new API, delete fallback branches.
2. Ensure `PathSystem` exposes required matrix operations; update `core/paths/path_system.py` tests accordingly.
3. Remove `set_drawingml_adapter` / `_emf_adapter` toggles in `PathMapper`; update integration tests to use real services.
4. Add targeted pytest guard (`tests/unit/core/map/test_path_mapper_shim_guard.py`) to fail when deprecated adapters are invoked.

### Phase 3: Clip & Parser Modernization

- [x] Update `core/groups/clipping_analyzer.py` to drop compatibility methods; ensure mapper tests use new structured results.
- [x] Refactor hyperlink parsing in `core/parse/parser.py` to emit modern structures; update tests accordingly.
- [x] Remove or migrate any archived clip helpers referenced by `clip_render`.

**Detailed Tasks**

1. Convert `ClippingAnalyzer` shim methods into thin wrappers around new services (or delete); update callers to use `ClipComputeResult`.
2. Rewrite hyperlink output builder to produce new schema; adjust downstream `DrawingMLEmbedder` expectations.
3. Remove references to archived clip XML utilities; ensure `clip_render` uses only `ClipComputeResult` structures.
4. Expand unit tests (`tests/unit/core/map/test_clipping_*`) to cover complex clip scenarios without legacy fallbacks.

### Phase 4: Text & Font Services Harmonization

- [ ] Audit `core/services/text_layout_engine.py`, `text_path_processor.py`, `text_to_path_processor.py` for legacy branches; replace with service-driven logic.
- [ ] Remove `legacy_kern` toggles in `core/services/font_embedding_engine.py`; expose clean configuration if still needed.
- [ ] Ensure fixtures/tests for text/font conversions target new services.

**Detailed Tasks**

1. Replace guard clauses referencing old APIs with ConversionServices lookups; remove duplicated caching layers.
2. Simplify or delete legacy compatibility methods (`anchor` conversion, return format) after updating consumers.
3. Update font embedding options to rely on modern pipeline configuration; remove `legacy_kern` toggles and adjust tests.
4. Refresh text-related fixtures in `tests/unit/core/services` to validate only the clean-slate behavior.

### Phase 5: Batch/API & Miscellaneous Cleanup

- [ ] Remove "legacy workflow" branches in `core/batch/coordinator.py` (drive uploads, logging) and ensure CLI/API rely only on new services.
- [ ] Clean up warnings/logs like `warn_legacy_emu_conversion` once all callers are updated.
- [ ] Verify remaining modules referencing legacy names (e.g., comments in `core/services/pattern_service.py`) are updated or trimmed.

**Detailed Tasks**

1. Audit CLI/API flows (`core/cli/main.py`, `api/services/conversion_service.py`) to ensure no `legacy` modes remain.
2. Delete deprecated env vars / configuration toggles tied to archive behavior; update docs accordingly.
3. Remove `warn_legacy_emu_conversion` once codebase is clean; ensure tests fail if invoked accidentally.
4. Perform final search for "legacy" strings; convert necessary references into historical notes or delete comments.

### Phase 6: Archive Removal & Documentation

- [ ] Delete executable modules under `archive/` and `archive_old/` after confirming no references remain.
- [ ] Update docs/specs to remove references to archived pipelines; highlight Clean Slate architecture.
- [ ] Add release notes summarizing the removal and any migration guidance.

**Detailed Tasks**

1. Move any required assets (SVG fixtures, docs) from `archive/` into `testing/golden` or `docs/legacy_reference`.
2. Remove archive paths from packaging/build scripts; ensure setup config ignores them.
3. Update README, architecture docs, ADRs to reflect final structure; note removal in CHANGELOG.
4. Delete archive directories and rerun inventory script to verify nothing remains.

### Phase 7: Validation & Guarding the Future

- [ ] Run full regression suite (unit/integration/e2e/visual) to confirm behavior stability.
- [ ] Instrument logging/telemetry to ensure `emu_trace`/`color_trace` remain populated.
- [ ] Add CI checks preventing reintroduction of `archive.*` imports.

**Detailed Tasks**

1. Execute `pytest`, integration, e2e, and visual tests with fractional mode enabled; capture baseline outputs.
2. Verify telemetry exports include EMU/color trace data in final pipeline configs.
3. Wire lint/CI job (e.g., `scripts/check_archive_usage.py`) to fail on `archive.*` usage; document developer workflow.

## Deliverables

- Updated core modules with legacy shims removed.
- Reduced codebase footprint (archive deletion).
- Updated specs/docs describing the modernized pipeline.
- Expanded tests covering new service paths and ensuring guardrails.
