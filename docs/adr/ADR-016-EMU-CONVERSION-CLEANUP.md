# ADR-016: EMU Conversion Cleanup Plan

## Status
**PROPOSED** - 2025-10-10

## Context
- Clean Slate services now drive most EMU conversions through `ConversionServices.emu`, but several utilities still use hard-coded fallback constants such as `PX_TO_EMU_96DPI` and `EMU_PER_POINT`.
- `core/utils/ooxml_transform_utils.py`, `core/transforms/matrix_composer.py`, and `core/services/text_layout_engine.py` were partially adapted to accept `ConversionServices`, yet downstream adapters and CLI/API wiring continue to instantiate them without services.
- Text mapping shims (`TextProcessingAdapter`, `_legacy_available` guards, path outliner fallbacks) prevent the Clean Slate-only flow from owning EMU conversions end-to-end.
- Tests and goldens remain aligned with legacy constants, so tightening conversions will require coordinated fixture updates and coverage validation.

## Problem Statement
Residual EMU constants and shim layers create inconsistent coordinate conversions across the pipeline, hinder precision improvements (fractional EMU), and duplicate conversion logic that already lives in `ConversionServices`. Without a focused cleanup, the MVP cannot guarantee deterministic slide output or make reliable DPI- and axis-aware decisions.

## Goals
- Eliminate hard-coded EMU fallbacks from active (non-archived) modules in favor of `ConversionServices`.
- Remove legacy text processing shims so Clean Slate services own all EMU conversions and normalization paths.
- Ensure every public factory, pipeline entry point, and CLI/API surface injects shared `ConversionServices` instances into downstream utilities.
- Update targeted unit, integration, and visual regression tests to lock in the new conversion behavior with ≥60% coverage maintained.
- Document the new invariants and guidance for contributors.

## Non-Goals
- Migrating or restoring archived modules under `archive/` or `archive_old/`.
- Rewriting fractional EMU internals or adding new unit types beyond what `ConversionServices` already supports.
- Changing external API contracts for consumers outside the svg2pptx project.

## Decision
Standardize on `ConversionServices` as the sole authority for EMU conversions and remove redundant constants/shims across the active codebase. The cleanup will proceed in staged phases, each gated by automated tests and documentation updates, to minimize regression risk while retiring legacy pathways.

## Rationale
- Centralizing conversions removes drift between utilities and services and unlocks per-axis precision already available in `ConversionServices.emu`.
- Retiring shims simplifies debugging (single source of truth) and reduces the maintenance burden of keeping legacy code paths alive.
- Wiring shared services through the pipeline prevents accidental divergence between CLI, API, and batch workflows.
- A phased execution plan allows goldens and fixtures to be updated deliberately, keeping coverage intact.

## Plan

### Phase 0 — Audit & Instrumentation (0.5 day)
- Add lightweight `rg` audits to CI (`scripts/check_emu_constants.py`) to flag new uses of `EMU_PER_POINT`, `PX_TO_EMU_96DPI`, or `EMU_PER_INCH` outside of `core/fractional_emu` and `core/units`.
- Catalog active modules still instantiating utilities without services (text adapters, pipeline factories, CLI commands).
- Owners: Platform team.

### Phase 1 — Utility Modernization (1.5 days)
- `core/utils/ooxml_transform_utils.py`: Delete fallback caches once services are mandatory; move DPI resolution into `ConversionServices.unit_converter`.
- `core/transforms/matrix_composer.py`: Require services parameter, resolve slide metrics via services, and surface helpers for per-axis conversions.
- `core/utils/transform_utils.py` and `core/utils/coordinate_transformer.py`: Replace direct `UnitConverter` usage with injected services; add adapters as needed.
- Ensure all factories (`create_ooxml_transform_utils`, `create_matrix_composer`) demand services and raise clear errors when missing.
- Tests: `tests/unit/core/utils/test_ooxml_transform_utils.py`, `tests/unit/transforms/test_matrix_composer.py`, add new coverage for `transform_utils`.
- Owners: Core conversion team.

### Phase 2 — Pipeline & Service Wiring (1 day)
- Update `core/pipeline/factory.py`, `core/pipeline/converter.py`, `cli/main.py`, and `api` dependency wiring so every downstream consumer receives a shared `ConversionServices` instance.
- Remove ad-hoc instantiations in adapters or job runners; prefer constructors that accept services explicitly.
- Add integration test to `tests/integration/pipeline/test_conversion_pipeline.py` validating consistent conversions across CLI and API entry points.
- Owners: Pipeline team with CLI/API maintainers.

### Phase 3 — Text Layout & Mapping Cleanup (2 days)
- Refactor `core/map/text_adapter.py` to depend on Clean Slate services only; remove `_legacy_available` guards and legacy fallbacks.
- Update `core/text/path_outliner.py` to request services for EMU conversions instead of `PX_TO_EMU_96DPI`.
- Promote `conversion_services.create_default()` (or equivalent dependency injection) as the single way to obtain services across text modules.
- Update unit tests (`tests/unit/core/map/test_text_adapter.py`, `tests/unit/core/text/test_path_outliner.py`) and integration tests (`tests/integration/test_text_processing_integration.py`) to reflect new expectations; refresh golden assets under `testing/golden/text/` as needed.
- Owners: Text & layout team.

### Phase 4 — Fractional EMU Adoption & Validation (1.5 days)
- Route all distance conversions through `fractional_emu.PrecisionEngine` where higher precision is beneficial (bbox, clipping, precise text baseline).
- Ensure services expose axis-aware conversions consistently; add smoke tests in `tests/unit/core/fractional_emu` verifying pathways.
- Validate that clipping adapters and bbox computations still match expected tolerance.
- Owners: Precision working group.

### Phase 5 — Documentation, Tooling, and Rollout (1 day)
- Update contributor guides (`docs/cleanup/`, `docs/guides/`) to remove references to legacy constants and describe the services-first policy.
- Add lint rule or pre-commit hook that blocks new direct uses of EMU constants in active modules.
- Publish release notes summarizing the migration and any fixture changes.
- Owners: Developer experience team.

## Testing Strategy
- Phase-specific pytest slices (listed above) plus `python -m pytest tests/unit/core/map -m "unit and not slow"` after Phase 3.
- Full suite with coverage (`python -m pytest --cov=core`) before marking the cleanup complete.
- Visual regression runs for representative SVG fixtures once text mapping and fractional EMU updates land.

## Risks and Mitigations
- **Regression in coordinate math**: Mitigate with expanded unit/integration coverage and targeted golden updates.
- **Service wiring gaps**: Add assertion checks that constructors receive services and provide fallback diagnostics.
- **Timeline creep from golden updates**: Schedule review windows with design team; parallelize fixture regeneration.
- **Contributor friction**: Provide migration snippets and lint messages that point to services-based replacements.

## Success Criteria
- No direct `EMU_PER_POINT`, `PX_TO_EMU_96DPI`, or `EMU_PER_INCH` usage in active code paths outside `core/units` and `core/fractional_emu`.
- All text layout, mapping, and transform utilities accept `ConversionServices` and operate without legacy guards.
- CLI, API, and batch conversions share identical services wiring and produce consistent EMU values within tolerance.
- Test coverage remains ≥60%, with updated goldens reflecting the new conversions.
- ADR updated to **ACCEPTED** after verification sign-off.

## Timeline & Ownership
- Kickoff: 2025-10-13
- Target completion: 2025-10-24
- Weekly checkpoints with platform lead; each phase expects demo-ready artifacts (MRs/tests).

## Related Work
- [ADR-007: Legacy Patterns Cleanup Specification](./ADR-007-LEGACY-PATTERNS-CLEANUP-SPECIFICATION.md)
- [ADR-010: SVG Normalization Pipeline](./ADR-010-SVG-NORMALIZATION-PIPELINE.md)
- [ADR-015: Clipping Pipeline Refresh Evaluation](./ADR-015-CLIPPING-PIPELINE-REFRESH-EVALUATION.md)

## References
- `core/utils/ooxml_transform_utils.py`
- `core/transforms/matrix_composer.py`
- `core/map/text_adapter.py`
- `core/services/conversion_services.py`
- `docs/fractional-emu-architecture.md`
- `docs/fractional-emu-migration-guide.md`
